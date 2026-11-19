[English](HASHMAP_LOCK_INTEGRATION_CYCLE.md)

# Intégration de HashMap et transport des contrats de verrou

## Règles exercées

- HM1–HM6. `HashMap<K,V>::new()` et les opérations `insert`,
  `try_insert`, `get`, `get_mut` et `remove` passent par le vérificateur
  et la génération C. Les prêts partagés et exclusifs portent sur la table.
  Le prêt de la clé prend fin après la recherche. Pour une clé connue, le
  remplacement ou l'extraction ne modifie que la dépendance de son entrée.
- MT10. Un argument emprunté garde son porteur vivant. Le transfert direct
  par argument propage le verrou si la fonction restitue le porteur. Si la
  fonction le détruit, l'ordre déduit dans son contrat décide si elle peut
  réacquérir le verrou. Une capture propriétaire réserve le verrou de la
  création de la tâche à son nettoyage ou à la restitution du porteur.
  Le résultat propriétaire de `join()` garde le verrou jusqu'à la
  destruction de sa valeur. `LaunchFailed` nettoie la capture.

## Exécutions

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest -v \
  test_hashmap test_hashmap_runtime test_lock_contracts
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest -v \
  test_hashmap test_hashmap_runtime test_lock_contracts test_core_integration \
  test_loop_replacements test_async_owned_struct_returns test_async_owned_struct_sync_calls
```

Les cas natifs compilent le C généré avec UBSan et arrêtent l'exécution au
premier diagnostic. Les refus ciblés passent par `verify_program` et
`compile_source`. L'oracle Python compare la suite d'opérations de table
avec un dictionnaire indépendant. Les sondes natives observent la stabilité
d'adresse et le réemploi des emplacements. L'échec d'insertion est provoqué
en réduisant la capacité de la zone d'entrées dans le C généré. Les deux
branches vérifient la valeur rendue et le maintien de la table. L'échec
de lancement est injecté au point de soumission du runtime.

- 18 tests ciblés réussis sous UBSan à `-O0`.
  [Journal](../../validation/hashmap-lock-integration-o0.log)
- 89 tests réussis dans le lot de régression sous UBSan à `-O2`.
  Le cas de remplacement réussi par `try_insert`, ajouté pendant la passe,
  a été rejoué séparément au même niveau d'optimisation.
  [Journal de régression](../../validation/hashmap-lock-integration-o2.log) ·
  [Rejeu ciblé](../../validation/hashmap-lock-integration-o2-try.log)
- Quatre cas de grammaire ciblés réussis. Dans la passe historique,
  deux attentes visaient l'interface du scheduler personnalisable qui
  a depuis été écartée du noyau cible.
  [Cas ciblés](../../validation/hashmap-lock-integration-grammar.log)
- [Sondes ASan et UBSan](../../validation/hashmap-lock-integration-asan.log).
  Le témoin minimal et le C généré dépassent chacun le délai de cinq
  secondes dans cet environnement. Le résultat ASan est indéterminé.
- [Reproduction antérieure du test de retour d'enum](../../validation/hashmap-lock-integration-legacy-baseline.log).
  La découverte générale a été interrompue après un échec du test
  `test_enum_expression_transfers_preserve_arm_and_cleanup_order`.
  Le même programme échoue avec le même diagnostic dans la copie antérieure
  `/private/tmp/crust-before-inline-vector-replace-contracts`. La passe
  générale ne permet donc aucune conclusion sur l'ensemble du dépôt.

## Limites

- Les opérations source couvrent les valeurs scalaires, les valeurs nominales
  prises en charge, les allocations de pool et les références scalaires.
  Les signatures de fonctions exercées reçoivent des tables à charge scalaire
  par emprunt. Les contrats de mutation ou de retour d'une table à charge
  dépendante, les références nominales stockées et l'usage direct de la table
  dans les fonctions async restent ouverts. En présence d'une clé inconnue,
  le vérificateur conserve une union de dépendances et peut refuser un cas
  dont l'exécution aurait séparé les entrées.
- Le lot MT10 couvre le relais direct du porteur et l'attente par `join()`,
  dont le cas où la tâche relaie le porteur par un `.await` interne. Les
  résultats composés, le stockage indirect par un argument dans une autre
  charge, et les appels qui créent directement un résultat annoté depuis un
  corps async restent hors de ce périmètre. Le marqueur décrit un contrat
  statique. L'exclusivité réelle relève du corps annoté.
- Ces exécutions documentent le périmètre exercé. L'audit indépendant de
  sûreté reste distinct.
