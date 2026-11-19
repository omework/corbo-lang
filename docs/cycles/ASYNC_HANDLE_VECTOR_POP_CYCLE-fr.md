[English](ASYNC_HANDLE_VECTOR_POP_CYCLE.md)

# Pop de handles dans les états async

## Règles et implémentation

Application de H1–H2, VE1–VE3, U1, B1–B5, AS8–AS12 et SL1–SL2, sans changement
normatif. `pop` retire le dernier handle et produit `Some` ou `None`. Un handle
présent conserve son adresse et son pool. La responsabilité de nettoyage passe
au résultat, puis au receveur du bras Some si le programme le consomme.

La traduction async reconnaît le match direct avec `<-`, les options nommées,
le match consommant, le déplacement, le drop direct et le drop nommé.
VectorHandleResult, déjà utilisé par le backend synchrone, contient le statut
et le pointeur de l'élément. Les temporaires persistants de l'état conservent
cette enveloppe pendant une suspension. Le runtime de vector_pop reste inchangé.

Les chemins de destruction des résultats propriétaires, auparavant réservés aux
Result de join, prennent aussi en compte l'enveloppe Option. Les transferts
conditionnels et les sorties de boucle utilisent leur type C réel, conservent
les sources et consomment la liaison antérieure. Le nettoyage suspendu d'un
perdant de Select détruit le contenu de Some uniquement. La réception d'un move
conserve aussi les sources dans la nouvelle liaison.

## Cas ciblés

Huit méthodes dans tests/test_async_handle_vector_pop.py, dix-sept exécutions
natives et six programmes invalides contrôlés aux deux entrées :

- Match direct Some et None, destruction unique et réemploi du pool.
- Transfert manquant et vecteur partagé refusés.
- Option nommée conservée pendant yield, puis déplacée ou consommée.
- Annotation Option<A<Int>> admise ; annotation Int, absence d'usage et
  réutilisation après drop refusées.
- Drop direct et nommé, sur vecteur vide et non vide.
- Emprunt utilisé avant pop admis ; dernier usage après pop refusé.
- Receveur d'un bloc, d'un if et d'un break : transfert puis match consommant.
- Retour de l'élément extrait depuis async, via fabrique synchrone ; branche
  None créant un élément dans le pool injecté.
- Branche perdante de Select ayant extrait avant yield : option nettoyée une
  fois, vecteur vide observé après attente et réemploi du pool.
- Deux pools distincts : dernier élément 9 retiré depuis son pool, premier
  élément 7 conservé, nettoyage et réemploi indépendants.

## Exécutions

Journaux sous validation/ :

| Journal | Résultat |
| --- | --- |
| open-async-handle-vector-pop.log | Cas initial refusé aux deux entrées : array_handle_len non pris en charge |
| async-handle-vector-pop-first-o0.log | Exécutions ciblées réussies ; deux assertions de diagnostic en échec pour la flèche absente |
| async-handle-vector-pop-second-o0.log | Diagnostic précisé, sept méthodes, 6,822 s, code 0 |
| async-handle-vector-pop-third-o0.log | Huit méthodes, 7,658 s, code 0 |
| async-handle-vector-pop-regression-o2.log | 91 méthodes, 153,696 s, code 0 |
| async-handle-vector-pop-sync-regression.log | Cinq méthodes, 6,473 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_pop -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_pop test_async_handle_vector_remove test_async_handle_vector_push test_async_vector_operations test_async_awaited_owned_results test_async_owned_struct_returns test_select_source test_factory_owned_effects -v
PYTHONPATH=.:tests python3 -m unittest test_foundation_rules.FoundationTests.test_buffered_handle_pop_cleans_only_a_present_payload test_foundation_rules.FoundationTests.test_buffered_handle_pop_match_consumes_saved_result test_foundation_rules.FoundationTests.test_buffered_handle_pop_returns_through_block_receivers test_foundation_rules.FoundationTests.test_buffered_handle_pop_survives_break_and_cleans_continue test_foundation_rules.FoundationTests.test_handle_vector_pop_match_requires_transfer_and_exclusivity -v
```

C11/pthread, warnings en erreurs, UBSan fatal. Les méthodes Foundation emploient
leur harnais historique O2/UBSan avec legacy-reset. Reset reste exclu du profil
normal. Les oracles contrôlent les valeurs, les refus, les destructions et le
réemploi des slots. Aucun nouveau modèle indépendant ni campagne de mutations
ou recherche adversariale étendue. La régression rejoue le modèle de listes
existant (graines 37/91, 28 opérations) et le modèle d'ordre de poll/nettoyage
Select (neuf couples de suspensions). Ces modèles ne couvrent pas spécifiquement
l'ensemble des états d'Option<A<Int>>. L'audit croisé reste une étape séparée.

## Limites et suite

Le retour de l'élément A<Int> est testé ; ce lot ne raccorde pas les signatures
de fonctions qui reçoivent ou retournent l'Option<A<Int>> elle-même depuis
async. Le cas suivant est reproduit aux deux entrées dans
validation/open-async-handle-option-call.crust et .log : un helper synchrone
retourne l'option et la tâche la consomme. Signature encore non prise en charge.
Les retours/captures async de l'enveloppe restent également à compléter.

Les résultats testés n'établissent ni une preuve de sûreté générale ni une
couverture de tous les ordonnancements. Replace, try_push et les constructions
locales/retours de vecteurs restent ouverts, ainsi que les arbitrages publics
précédemment consignés.

Snapshot : /tmp/crust-before-async-handle-vector-pop/.
Diff : validation/async-handle-vector-pop-async_lowering.py.patch.
