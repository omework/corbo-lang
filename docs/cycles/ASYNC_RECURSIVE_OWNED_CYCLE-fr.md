[English](ASYNC_RECURSIVE_OWNED_CYCLE.md)

# Graphes propriétaires récursifs aux frontières async

## Périmètre et changements

Application des règles existantes de transfert explicite, d’adresses stables,
de durée de vie et de nettoyage aux valeurs finies d’un type récursif contenant
`A<T>`. Aucune règle normative nouvelle. Les arêtes propriétaires ont une taille
de handle connue ; elles ne doivent pas imposer un déroulement infini du type
pour représenter un état async. Les cycles de références nominales ne sont pas
élargis par ce lot.

- La classification des layouts accepte les cycles passant par des champs A<T>.
- Les métadonnées concrètes du résultat conservent la variante de chaque
  descendant. La restauration s’arrête ainsi sur la variante terminale.
- Les bridges synchrones cessent de dérouler les types récursifs ; les
  projections opaques utilisent le mécanisme symbolique des entrées synchrones.
- Le retour d’un propriétaire conserve les chemins empruntés concrets qui
  dépassent l’énumération finie des chemins du type. Les champs explicitement
  décrits par le contrat de complétion restent prioritaires. Les handles publics
  calculent le mode d’emprunt en parcourant le chemin effectivement présent.

## Défauts reproduits

Les premiers essais du lot refusaient les captures récursives ; après extension
la restauration cherchait un descendant inexistant dans la variante terminale.
Le helper synchrone provoquait un déroulement infini, converti par la CLI en
« programme trop imbriqué ». Ces deux raccordements sont corrigés.

Un programme renvoyant Link → Link → End{value:&number} autorisait `number=8`
alors que le résultat vivant contenait toujours la référence. Le test échouait
aux deux entrées du compilateur. La propagation des chemins concrets corrige
ce défaut. L’annotation du handle révélait ensuite un KeyError sur ce même
chemin ; le mode du champ est désormais obtenu par parcours du type.

Le premier test négatif utilisait drop depuis le bras enfant et était refusé
pour cette raison avant d’exercer l’emprunt. Il a été corrigé en mutation de la
cible depuis le bras, pour isoler la réservation réellement recherchée.

## Cas et preuves ciblées

`tests/test_async_recursive_owned.py` contient cinq méthodes, sept exécutions
natives et quatre programmes invalides vérifiés par les deux entrées.

- Retour d’un graphe de trois objets dans deux pools, destruction feuille avant
  porteurs, réemploi de tous les slots ; soumission normale et échec injecté.
- Lecture par matchs imbriqués séparés par yield ; drop du porteur refusé avant join.
- Pools locaux dans une tâche, destruction d’une tâche inactive et réemploi.
- Helpers synchrones d’inspection, de relais et de destruction du graphe.
- Référence stockée dans le descendant terminal, handle inféré ou annoté :
  résultat encore vivant protège la cible, puis destruction autorise son drop.

Les attentes de valeurs et de traces sont écrites dans les tests. Le harnais
async compile le C en C11/pthread, warnings en erreurs, UBSan fatal. Le niveau
d’optimisation est fixé par CRUST_TEST_OPT. Les tests historiques sélectionnés
utilisent leur harnais C11 à O2/UBSan et l’option legacy-reset.

## Exécutions

Le passage ciblé final O0 est dans
`validation/async-recursive-owned-public-second-o0.log` : cinq méthodes,
3,142 s, code 0. Les journaux précédents conservent les échecs décrits ci-dessus.

| Journal dans validation/ | Résultat terminal |
| --- | --- |
| async-recursive-owned-regression-o2.log | 120 méthodes, 98,500 s, code 0 |
| async-recursive-owned-sync-regression.log | 7 méthodes, 4,156 s, 1 erreur de provenance |
| async-recursive-owned-sync-baseline.log | Même erreur reproduite sur le snapshot avant lot, 1 méthode, 0,101 s |
| async-recursive-owned-storage-regression-o2.log | Après correction : 22 méthodes, 13,706 s, code 0 |
| async-recursive-owned-storage-boundary-o2.log | 11 méthodes, 1 échec de fixture : motif de structure non prévu |
| async-recursive-owned-storage-boundary-second-o2.log | Fixture corrigée en enum : 11 méthodes, 7,354 s, code 0 |

La correction historique reconnaît les sources de champs propriétaires A<T>
comme des allocations de pool indépendantes du porteur. Le test supplémentaire
extrait le même champ depuis un porteur local puis depuis un porteur en pool :
deux exécutions admises, deux annotations locales incompatibles refusées aux deux
entrées. Le test utilise un match consommant d’enum, sans introduire de déplacement
de champ de structure. La première fixture erronée est conservée dans son journal.

Commandes reproductibles (rediriger vers les journaux correspondants) :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_recursive_owned
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_recursive_owned test_async_owned_enums test_async_enum_match test_async_owned_struct_sync_calls test_async_owned_struct_returns test_async_owned_borrowed_captures test_async_owned_borrow_writes test_async_owned_nominal_writes test_async_stored_views test_public_structure_handles test_public_local_enums test_local_enums -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_storage_requirements test_async_recursive_owned test_foundation_rules.FoundationTests.test_recursive_handle_field_layout_is_pointer_sized test_foundation_rules.FoundationTests.test_recursive_owned_fields_drop_children_once_in_origin_pools test_foundation_rules.FoundationTests.test_function_returns_finite_value_of_recursive_owned_type test_foundation_rules.FoundationTests.test_recursive_owned_parameter_can_be_inspected_relayed_and_destroyed test_foundation_rules.FoundationTests.test_recursive_mutable_parameter_updates_deep_leaf_in_place test_foundation_rules.FoundationTests.test_consuming_match_extracts_recursive_owned_child_beyond_first_repeat test_foundation_rules.FoundationTests.test_function_returns_consumed_recursive_owned_projection_through_relay -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_storage_requirements -v
```

La commande à 22 méthodes précède l’ajout du dernier test : elle en sélectionne
23 dans l’état final. Les 120 méthodes précèdent la correction isolée dans
storage_requirements.py ; la seconde sélection et le module de stockage ont été
exécutés après cette correction. Ces nombres ne sont pas des comptes de tests
uniques à additionner. Les modèles déterministes déjà présents dans les modules
sélectionnés ont été rejoués ; aucun nouvel oracle indépendant n’a été ajouté.

## Limites

La couverture porte sur les graphes concrets et chemins énumérés ci-dessus.
Les projections empruntées profondément dans un helper, les fabriques opaques
et les remplacements à profondeur récursive ne sont pas déclarés couverts par
ces cinq méthodes. Une source symbolique de bridge décrit une obligation de
durée de vie ; ce n’est pas un nouveau pool d’allocation runtime.
La conservation de chemins hérités non explicités par le contrat peut être
conservatrice. Les autres règles encore ouvertes restent dans l’objectif global.
Pas de nouvelle campagne de mutations ou d’audit indépendant.

Snapshot avant lot : `/tmp/crust-before-async-recursive-owned/`.

Diffs des trois modules archivés dans `validation/async-recursive-owned-*.py.patch`.
