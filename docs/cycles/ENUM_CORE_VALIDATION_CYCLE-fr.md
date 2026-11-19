[English](ENUM_CORE_VALIDATION_CYCLE.md)

# Retour d'une allocation d'enum dans le core

Le test `test_enum_expression_transfers_preserve_arm_and_cleanup_order`
utilise `fn main()`, un résultat et des paramètres `A<E>`, un `return`
par valeur et les constructeurs `pool.new(E.Variante { ... })`. Le parseur
abaisse ces constructeurs vers la construction d'enum en pool déjà utilisée
par le vérificateur et le backend. La trace attendue reste
`E.A(42)` puis `E.B()` sur la sortie standard, suivie dans la trace
de nettoyage de `destroy fresh=E.B` puis `destroy a=E.A`. Le test exécute
le programme sans le profil de réinitialisation historique.

## Validation ciblée

- Les 20 tests de `test_arguments` passent avec `CRUST_SANITIZE=undefined`.
  [Journal](../../validation/enum-core-arguments.log)
- Les deux formes de constructeur produisent le même C pour ce programme.
  Les deux entrées du compilateur refusent une variante `E` passée à
  `Pool<Other>`. [Journal](../../validation/enum-core-pool-typing.log)

## Validation générale

La découverte compte 3 724 tests. Les 258 modules sont répartis en huit lots
par processus. L'exécution utilise `CRUST_SANITIZE=undefined` et
`CRUST_TEST_OPT=-O2` pour les bancs qui exposent ces réglages.

Les huit lots ont terminé. Les 30 tests de `test_core_integration` passent.
La suite générale signale 98 échecs d'assertion et 127 erreurs, dont des
sous-cas d'un même test. Ces signalements concernent 145 tests distincts.
[Journal de la suite](../../validation/enum-core-global.log)

Les 145 tests concernés ont également échoué lors de leur rejeu sur
une copie du même compilateur avec le changement du parseur retiré.
La comparaison porte sur le statut de chaque test. Elle n'établit pas
que chaque diagnostic de sous-cas est identique. Les échecs restent ouverts.
[Journal de comparaison](../../validation/enum-core-baseline.log)

Cette passe exerce à la fois le noyau et les profils historiques du dépôt.
Elle ne comprend pas de nouvelle exécution ASan ni d'audit indépendant.
