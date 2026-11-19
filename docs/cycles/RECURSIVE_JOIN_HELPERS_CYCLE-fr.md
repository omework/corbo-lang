[English](RECURSIVE_JOIN_HELPERS_CYCLE.md)

# Helpers d’attente sur handles récursifs

## Périmètre

Application des règles existantes AS10–AS12, du résultat public
Result<T,runtime::Error>, des transferts et emprunts aux helpers synchrones
recevant Handle<A<Node>>. Aucun changement normatif ; les appels continuent
à employer les contrats. Le brouillon 04 interdit toujours join depuis du code
async, y compris indirectement par un helper.

## Implémentation et défauts corrigés

Le programme conservé dans validation/open-recursive-join-helper.crust
provoquait un déroulement infini dans ResultContext.async_owned_result_value.
L’analyse déroule désormais les chemins de stockage décrits par le contrat,
sans construire une valeur infinie à partir du seul type récursif.

Les entrées symboliques distinguent une feuille concrète d’une continuation
récursive encore opaque. Cette continuation garde des sources symboliques pour
les projections ultérieures ; elle ne réserve pas de nouveau stockage runtime.
Ses métadonnées traversent les descriptions de champs et les jonctions.

Le résultat attendu du helper retrouve les variantes de l’entrée réellement
attendue. Elles ne sont plus présentées comme des variantes fraîchement
construites par le helper. Les descendants obtenus depuis un champ du résultat
de tâche conservent leur identité, leur variante et leurs propres descendants.
Les cibles empruntées de l’entrée sont transmises jusqu’au résultat du helper.
La restauration ignore les champs des variantes prouvées absentes, sans
supprimer les vérifications sur les variantes possibles.

## Tests ciblés

Quatre méthodes dans tests/test_recursive_join_helpers.py : cinq exécutions
natives, trois programmes invalides aux deux entrées.

- Helper public renvoyant le Result du join ; trois objets dans deux pools,
  destruction feuille avant porteurs et réemploi du slot terminal.
- Référence stockée dans le descendant terminal : mutation refusée tant que le
  résultat reste utilisé, puis drop de la cible après destruction du résultat.
- Deux helpers successifs, graphe avec liens puis simple variante terminale ;
  échec de soumission injecté avec destruction unique et réemploi.
- Appel d’un helper bloquant depuis l’async refusé conformément au brouillon 04.

La fixture d’origine a été corrigée pour écrire match r sur le Result de join,
et non match (->r), qui désigne d’autres opérations dans le prototype. Après
la suppression du déroulement infini, cette erreur de fixture devenait visible.
Une autre fixture attendait à tort l’acceptation de join indirect depuis l’async :
le tableau des cas refusés du brouillon 04 confirme le refus attendu. Le test a
été corrigé, pas la règle ni le contrôle du compilateur.

## Journaux

| Journal dans validation/ | Résultat terminal |
| --- | --- |
| recursive-join-helpers-first-o0.log | 2 méthodes, 1 échec : provenance empruntée manquante |
| recursive-join-helpers-second-o0.log | 2 méthodes, même refus de provenance |
| recursive-join-helpers-third-o0.log | 2 méthodes, cible absente du contrat de résultat |
| recursive-join-helpers-fourth-o0.log | 2 méthodes, 0,914 s, code 0 |
| recursive-join-helpers-fifth-o0.log | 3 méthodes, 2,414 s, code 0 |
| recursive-join-helpers-sixth-o0.log | 4 méthodes, erreur d’attente de fixture sur join depuis async |
| recursive-join-helpers-seventh-o0.log | 4 méthodes, 2,230 s, code 0 |

La régression O2/UBSan termine 112 méthodes en 120,958 s, code 0 :
validation/recursive-join-helpers-regression-o2.log. Les trois cas synchrones
sélectionnés passent en 2,209 s, code 0 :
validation/recursive-join-helpers-sync-regression.log.

Le harnais ciblé compile le C11 avec pthread, warnings en erreurs et UBSan
fatal. La sélection de régression utilise également O2/UBSan ; le harnais des
résultats métier n’active pas les mêmes warnings et ajoute pthread lorsque le
C généré l’exige. Les trois tests historiques synchrones utilisent leur harnais
O2/UBSan avec legacy-reset.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_recursive_join_helpers -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_recursive_join_helpers test_recursive_task_factories test_async_recursive_owned test_public_structure_handles test_public_local_enums test_task_result_storage test_local_result_envelopes test_business_result_envelopes test_async_owned_struct_returns test_async_owned_borrow_writes test_async_result_factories test_async_stored_views -v
PYTHONPATH=.:tests python3 -m unittest test_foundation_rules.FoundationTests.test_function_returns_consumed_recursive_owned_projection_through_relay test_foundation_rules.FoundationTests.test_function_composes_two_owned_extractions_with_fresh_fallback test_foundation_rules.FoundationTests.test_recursive_owned_parameter_can_be_inspected_relayed_and_destroyed -v
```
Les valeurs, diagnostics, traces de destruction et réemplois sont les oracles
explicites des tests. Pas de nouvel oracle indépendant ni campagne de mutations.

## Limites

Ces tests ne couvrent pas tous les parcours de projections récursives, ni tous
les remplacements de descendants. La continuation symbolique donne une
représentation finie de l’entrée ; elle ne prouve pas que toutes ses opérations
possibles sont déjà raccordées. Les résultats de forme récursive neuve et
entièrement opaque restent à compléter. L’objectif global reste ouvert.

Snapshot : /tmp/crust-before-recursive-join-helpers/.
Diffs : validation/recursive-join-helpers-crust.py.patch et
validation/recursive-join-helpers-results.py.patch.
