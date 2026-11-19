[English](ASYNC_OWNED_BORROW_WRITES_CYCLE.md)

# Remplacement async de descendants contenant des emprunts

## Périmètre et règles

Ce lot raccorde les remplacements déjà retenus de champs A<T> lorsque T contient
des champs &Int ou &mut Int. Il applique les règles de durée de vie, de dernière
utilisation, de remplacement après évaluation, AS16 et SL1. Aucune règle normative
n'est changée ; reset reste retiré du prototype. Les tests portent sur les cas
énumérés et les régressions liées, conformément à la priorité utilisateur.

## Implémentation

Le backend async projette les dépendances du nouveau descendant depuis
`owned_field_writes` vers le suivi commun des champs empruntés. Une affectation
directe transmet de même les cibles du nouvel objet avant de nettoyer ses
métadonnées temporaires. Les sources des allocations et les cibles empruntées
restent deux obligations distinctes.

Un remplacement conditionnel conserve les cibles de l'ancien descendant lorsque
le contrat contient une alternative `owned_field_input`. Les contrats suspendus
et terminés restent distincts : une perdante de Select conserve la cible déjà
installée avant yield, pas celle qui serait installée plus tard.

Le résolveur commun des descendants frais conservait leurs pools mais omettait
leurs dépendances empruntées. Il les résout maintenant depuis les paramètres du
contrat, avec leur ascendance d'emprunt. Cette correction est nécessaire au join
depuis main et bénéficie également aux contrats synchrones concernés.

## Exécutions

- Ciblé final O0 : 8 méthodes, 5,826 s, code 0 ;
  `validation/async-owned-borrow-writes-conditional-o0.log`.
- Ce module comprend 12 exécutions natives et 13 programmes invalides vérifiés
  aux deux entrées, soit 26 contrôles de refus par passage complet.
- Régression O2/UBSan : 127 méthodes, 65,758 s, code 0 ;
  `validation/async-owned-borrow-writes-regression-o2.log`.
  Ce processus avait chargé les modules avant le dernier ajustement conditionnel.
- Vérification finale O2/UBSan après cet ajustement : 19 méthodes, 10,630 s,
  code 0 ; `validation/async-owned-borrow-writes-final-o2.log`. Elle comprend
  le nouveau module, les remplacements sans emprunts et les effets suspendus
  des descendants d'enums. La suite de 127 méthodes n'a pas été répétée.

Les exécutions natives utilisent Clang C11, pthread et UBSan sans récupération.
Sont exercés : appels auxiliaires et affectations directes, await, join, échec
du lancement injecté, Select perdant, remplacement successif et conditionnel,
réemploi des slots, emprunts partagés/mutables, drop prématuré et cible de scope
trop court. Un lancement échoué conserve la valeur initiale 7 ; le remplacement
réalisé expose 9 ; une seconde écriture après yield expose 11 seulement après
terminaison normale.

Le premier passage a révélé le défaut du résolveur commun décrit ci-dessus.
Le premier exemple de scope court était refusé pour une autre raison : une
allocation `next` inutilisée. Un drop explicite de cette allocation a corrigé
le test pour atteindre le contrôle de durée de vie attendu. Les journaux
intermédiaires sont conservés.

## Limites

Les cibles exercées dans ce lot sont Int. Le [lot des références
nominales](ASYNC_OWNED_NOMINAL_WRITES_CYCLE.md) prolonge ce support aux
cibles de structures représentées. Les graphes récursifs et toutes les
fabriques de tâches ne sont pas couverts ici. Les
unions de sources et d'alternatives restent conservatrices. Il ne fournit ni
preuve générale de sûreté ni résultat d'audit indépendant. Aucune nouvelle
campagne de mutations ou recherche adversariale n'est exécutée, selon la
consigne utilisateur ; aucun nouveau modèle indépendant n'est revendiqué.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_async_owned_borrow_writes -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_owned_borrow_writes test_async_owned_field_writes test_async_enum_suspension_fields -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_owned_borrow_writes test_async_owned_field_writes test_async_consuming_enum_match test_async_enum_suspension_fields test_suspension_effects test_async_structure_effects test_select_source test_async_owned_struct_returns test_task_result_storage test_owned_results test_foundation_rules.FoundationTests.test_owned_field_preserves_child_borrows_without_destroying_targets test_foundation_rules.FoundationTests.test_borrowed_owned_field_replacement_keeps_alternative_sources test_foundation_rules.FoundationTests.test_nested_owned_field_replacement_joins_child_metadata -v
```

Le dernier ordre exécutait 127 méthodes avant l'ajout du huitième test ; il en
comprend maintenant une de plus. Snapshot :
`/tmp/crust-before-async-owned-borrow-writes/`. Différences archivées :
`validation/async-owned-borrow-writes-async_lowering.py.patch` et
`validation/async-owned-borrow-writes-crust.py.patch`.
