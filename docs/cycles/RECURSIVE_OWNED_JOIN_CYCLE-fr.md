[English](RECURSIVE_OWNED_JOIN_CYCLE.md)

# Résultats propriétaires à profondeur variable

## Règles et réalisation

RT6 ajoute un `Result<T, runtime::Error>` à chaque attente d'un handle.
AS8–AS14, H1–H2, B1–B5, U1, F3–F4 et SL1–SL2 continuent de protéger le
type, le stockage, les dépendances et le nettoyage de sa charge. Ce lot ne
modifie aucune règle normative.

`owned_join_types.py` décrit les niveaux de résultats propriétaires sans borne
fixe à deux niveaux. Le type de la charge et sa nature locale T ou allouée A<T>
restent dans la signature ; la profondeur détermine le layout C et le chemin
vers le handle. Les layouts historiques des deux premiers niveaux sont
conservés. `CrustNestedJoinResult` est désormais déclaré avec les types de
valeurs communs, avant les layouts plus profonds.

Parser, contrats, effets de champs, exigences de stockage, handles publics,
captures, retours et extractions consultent ces descriptions. Chaque extraction
retire un seul niveau et conserve les champs propriétaires et empruntés ainsi
que l'information d'absence prouvée d'une charge. Le nettoyage vérifie tous
les statuts runtime avant de détruire le contenu. Les allocations ciblées ne
sont pas déplacées.

## Validation ciblée

Sept méthodes nouvelles dans `tests/test_recursive_owned_join.py` :
19 exécutions natives et huit programmes invalides contrôlés aux deux entrées,
verify_program et compile_source.

- Trois et cinq enveloppes autour d'A<Int>, extraction et réemploi.
- Échec injecté à chacun des trois niveaux de lancement, destruction unique.
- Handle public, helper d'attente synchrone et relais du résultat.
- Extraction async, fabrique synchrone et instance inactive nommée.
- Int, String, Vector<Int> et Vector<u8> : type préservé, lecture, destruction
  puis réemploi du slot.
- Capture exécutée ou inactive ; argument préparé avant await, nettoyage par
  la branche perdante de Select.
- If et loop producteurs du résultat ; consommation et transfert explicites.
- Objet local View contenant un &Int : résultat à trois enveloppes, prêt
  conservé et distinction View/A<View> vérifiée.
- Refus du transfert absent, de la réutilisation après transfert, du résultat
  sans usage, de la double consommation, du motif ignorant une charge, du
  pool trop court, du drop d'une cible encore empruntée et d'une substitution
  implicite entre stockage local et allocation de pool.

La méthode historique
`AsyncRuntimeTests.test_nested_join_result_transfers_through_sync_and_async_signatures`
exécute huit programmes natifs et trois refus via verify_program. Elle conserve
ses scénarios sync/async et ses échecs injectés. L'ancien refus de principe du
troisième niveau est remplacé par son exécution avec une attente explicite ;
le retour abandonnant cette attente reste refusé.

## Défaut préexistant découvert et corrigé

Ce test historique a révélé un TypeError du lowering lors de `child.await` :
la tâche nommée était consommée avant la lecture de sa signature. Le défaut
est reproduit sur la sauvegarde antérieure au lot, dans
`recursive-owned-join-legacy-baseline-o0.log`. La signature est maintenant
capturée avant consommation. La nouvelle suite garde un cas déterministe
avec une instance nommée issue d'une fabrique.

Le premier passage historique relevait également son assertion devenue
obsolète sur le diagnostic « trois niveaux ». Le snippet de remplacement
attend réellement le troisième handle et traite chaque enveloppe ; ses
valeurs et destructions sont vérifiées. Les oracles précédents ne sont pas
affaiblis pour masquer le TypeError.

## Commandes et résultats

Les tests utilisent C11, pthread, Wall/Wextra/Werror, UBSan et
`-fno-sanitize-recover=all`. Les diagnostics sanitizer font échouer le test.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest \
  test_recursive_owned_join \
  test_async_runtime.AsyncRuntimeTests.test_nested_join_result_transfers_through_sync_and_async_signatures -v
```

Journaux sous `validation/` :

| Journal | Résultat |
| --- | --- |
| recursive-owned-join-first-o0.log | Reproduction initiale exécutée, code 0 |
| recursive-owned-join-second-o0.log | 7 méthodes, 8,059 s, code 0 ; avant le cas nommé supplémentaire |
| recursive-owned-join-legacy-o0.log | 1 méthode, 1,580 s, code 1 ; TypeError et diagnostic historique obsolète |
| recursive-owned-join-legacy-baseline-o0.log | Sauvegarde antérieure, 1 méthode, 1,568 s, code 1 ; même TypeError |
| recursive-owned-join-third-o0.log | 8 méthodes, 10,001 s, code 0 ; suites ciblée et historique corrigées |
| recursive-owned-join-regression-o2.log | 186 méthodes, 231,142 s, code 0 ; O2/UBSan |

Régression :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest \
  test_recursive_owned_join \
  test_async_runtime.AsyncRuntimeTests.test_nested_join_result_transfers_through_sync_and_async_signatures \
  test_async_nested_option_join test_async_nested_exchange_join \
  test_async_exchange_join test_async_option_join test_async_awaited_owned_results \
  test_async_failure_only_results test_local_result_envelopes \
  test_async_borrowed_local_results test_async_local_owned_result_graphs \
  test_async_structure_effects test_factory_owned_effects \
  test_public_handle_contracts test_select_source test_task_wakes -v
```

## Limites et traçabilité

Les profondeurs et types exécutés ne prouvent pas toutes les combinaisons. Les
limites générales de récursion du prototype restent applicables. Les suites
de régression ont exécuté avec succès les modèles existants de poll/nettoyage
de Select et de réveil ; aucun nouvel audit adversarial indépendant ni campagne de
mutation n'est revendiqué. ASan et les autres compilateurs C ne sont pas
exercés ici.

Ce travail ne généralise pas les feuilles Option et replace/try_push à tous
les types. Les autres restrictions de signatures, collections et captures
restent suivies dans la matrice. L'interface publique du scheduler, la
construction des mutex et les autres arbitrages reportés ne sont pas résolus.
L'objectif global reste actif.

Onze fichiers Python du compilateur/runtime et un fichier de test historique
sont comparés à `/tmp/crust-before-recursive-owned-joins`. Les diffs sont
conservés dans `validation/recursive-owned-join-*.py.patch` ; la nouvelle suite
est conservée avec le projet.

Le programme de profondeur trois et son C généré sont conservés dans
`validation/recursive-owned-join-depth3.crust` et `.c`. Le C utilise le layout
imbriqué attendu et vérifie les trois statuts avant le nettoyage du handle.
Le prochain écart de VE1–VE3 est reproduit aux deux entrées dans
`validation/open-vector-allocated-structure.crust` et `.log` :
`Vector<A<Point>>`, insertion puis pop et réemploi du pool. Le refus actuel
intervient dès la construction du vecteur, avec un diagnostic d'allocation Int
incompatible ; il ne s'agit pas d'une restriction normative sur T.
