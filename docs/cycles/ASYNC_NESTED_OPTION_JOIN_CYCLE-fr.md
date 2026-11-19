[English](ASYNC_NESTED_OPTION_JOIN_CYCLE.md)

# Enveloppes runtime imbriquées autour d'Option<A<Int>>

## Règles et réalisation

Application de RT6, AS8–AS14, H1–H2, VE3, U1, F3–F4 et SL1–SL2.
Aucune règle normative n'est modifiée. Attendre un handle ajoute toujours
`Result<T, runtime::Error>`, même lorsque T contient déjà des enveloppes runtime.
Le contenu de Some reste attaché à son pool ; None ne possède pas d'allocation.

Le compilateur décrit désormais récursivement les enveloppes autour
d'Option<A<Int>>. Le registre commun de dispositions se trouve dans
`result_envelopes.py` ; `option_join_types.py` et `exchange_join_types.py`
configurent les familles de feuilles, avec leurs conditions de présence
respectives. Les registres de provenance restent distincts : Option a une
charge possible ; replace/try_push gardent leurs provenances par bras.

Les descriptions donnent le type intérieur, le type C, le chemin du handle et
les conditions du nettoyage. L'extraction retire une seule enveloppe. Le C
contient un statut par enveloppe ; il nettoie la charge seulement si tous les
statuts runtime indiquent Ok et si la feuille est Some. Les adresses des
allocations ciblées ne sont pas déplacées. Les types sont enregistrés à partir
des signatures ; les caches évitent de reconstruire les mêmes descriptions.

Les contrats, signatures publiques, transferts, captures de résultats, retours
async et fabriques utilisent ces modes à profondeur variable. Le nettoyage des
arguments préparés et des branches perdantes de Select consulte les mêmes
conditions de présence.

## Cas exécutés

Sept méthodes de `tests/test_async_nested_option_join.py` : 25 exécutions natives
et sept programmes invalides, contrôlés par verify_program et compile_source.

- Some et None, deux, trois et cinq enveloppes runtime, extraction successive.
- Échec injecté à chacun des trois niveaux de lancement, avec et sans élément.
- Handle public, helper synchrone d'attente et relais du résultat.
- Extraction depuis async, await d'une instance inactive produite par fabrique.
- Capture exécutée ou détruite inactive ; résultat préparé avant suspension et
  nettoyé dans le perdant de Select. Comptage des destructions et réemploi.
- Résultat transféré par if ou loop, consommation explicite et nettoyage.
- Résultat conservé après disparition du vecteur, lorsque le pool de l'élément
  survit. La variante où ce pool disparaît est refusée.
- Refus du transfert absent, de la réutilisation après transfert, du résultat
  sans usage, de la double consommation, du motif ignorant la charge et d'un
  accès au vecteur encore réservé par son exécution.

Le C est compilé en C11 avec pthread, Wall/Wextra/Werror, UBSan et
`-fno-sanitize-recover=all`. Les diagnostics sanitizer font échouer le test.
La limite de profondeur de ces types n'est plus codée en dur ; seules les
profondeurs exécutées constituent une preuve expérimentale dans ce lot.

## Défauts et étapes

La reproduction `validation/open-async-nested-option-join.crust` était refusée
par le garde « trois niveaux de Result ». Elle s'exécute désormais et restitue
le slot du pool avant la nouvelle allocation.

Le premier passage de la nouvelle suite a révélé un filtre de signature du
lowering async resté limité aux modes connus précédemment. Le registre des
modes optionnels est maintenant pris en compte par ce filtre. Les attentes,
valeurs attendues et oracles de destruction n'ont pas été affaiblis.

Journaux dans `validation/` :

| Journal | Résultat |
| --- | --- |
| async-nested-option-join-first-o0.log | Reproduction initiale exécutée, code 0 |
| async-nested-option-join-second-o0.log | 7 méthodes, 0,822 s, code 1 ; filtre de signature incomplet |
| async-nested-option-join-third-o0.log | 7 méthodes, 9,689 s, code 0 ; 25 exécutions, sept refus |
| async-nested-option-join-regression-o2.log | 142 méthodes, 135,869 s, code 0 ; O2/UBSan |

La suite ciblée est lancée avec :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_nested_option_join -v
```

La régression utilise :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest \
  test_async_nested_option_join test_async_nested_exchange_join \
  test_async_exchange_join test_async_handle_exchange_results \
  test_async_handle_exchange_calls test_async_option_join \
  test_async_handle_option_results test_async_handle_option_calls \
  test_async_structure_effects test_factory_owned_effects \
  test_public_handle_contracts test_select_source test_task_wakes -v
```

## Portée et limites

La suite de régression a exécuté avec succès les modèles existants de
poll/nettoyage de Select et de réveil. Aucun nouveau modèle général, test de mutation ou audit adversarial
indépendant n'est revendiqué. ASan et d'autres compilateurs C ne sont pas
exercés ici. Les tests couvrent les programmes et chemins mentionnés, sans
prouver la sûreté générale ni toutes les profondeurs.

Les feuilles optionnelles couvertes portent A<Int>. La généralisation des
résultats d'allocations simples et d'autres types reste ouverte. Les arbitrages
publics scheduler/mutex et la capture de handles dans une instance inactive
ne sont pas résolus par ce lot. L'objectif global reste actif.

Les onze fichiers Python modifiés ou créés sont comparés à
`/tmp/crust-before-nested-option-joins`. Les diffs sont archivés sous
`validation/async-nested-option-join-*.py.patch`.

Le programme de profondeur trois et son C généré sont conservés dans
`validation/async-nested-option-depth3.crust` et `.c`. L'inspection confirme
que la condition de nettoyage combine les trois statuts runtime et le statut
Some de la feuille ; le programme est exécuté par la suite ciblée.
La prochaine restriction est reproduite aux deux entrées dans
`validation/open-async-nested-owned-join.crust` et `.log` : lancer une tâche
retournant déjà deux enveloppes autour d'A<Int> reste refusé.
