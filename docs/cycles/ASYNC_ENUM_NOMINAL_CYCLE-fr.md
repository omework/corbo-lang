[English](ASYNC_ENUM_NOMINAL_CYCLE.md)

# Références nominales dans les bras d’enums async

## Périmètre et règles

Raccordement des règles existantes AS8–AS12, ST7–ST14 et des matchs empruntés
et consommants. Aucune règle normative modifiée. Une référence partagée stockée
pointe vers une cible indépendante du porteur. Un réemprunt mutable réserve la
capacité du porteur jusqu’au dernier usage ; consommer le porteur transfère ses
références sans détruire leurs cibles. Les adresses intérieures restent stables.

## Implémentation

Le backend async infère le type nominal des alias de motifs et extrait le
`CrustStructureView` stocké dans le champ, au lieu de charger seulement sa racine
comme pour un pointeur vers Int. Le layout donne le décalage exact du champ,
y compris après un champ scalaire. La suspension conserve le descripteur dans
l’état existant de la tâche.

L’analyse des résultats détache les références partagées nominales comme elle
le faisait pour &Int. L’analyse des contraintes et la projection chez l’appelant
suivent la cible du champ et retiennent la réservation du porteur pour &mut T.
Le protocole d’attente, le runtime des slots et leur ordre de libération ne
changent pas.

## Cas exécutés

`tests/test_async_enum_nominal.py` contient cinq méthodes, six programmes admis
exécutés et six programmes invalides refusés aux deux entrées du compilateur.

- Deux variantes partagées retournent une référence intérieure après yield et
  destruction du porteur ; la cible reste lisible, le slot est réutilisable.
- Un bras mutable réemprunte via une fonction synchrone, suspend et modifie la
  cible. Réutiliser le premier emprunt avant le dernier usage du second échoue.
- Un résultat mutable sort du bras puis de la tâche ; la cible et le porteur
  restent réservés chez l’appelant jusqu’à son dernier usage.
- Un match consommant libère le porteur une fois ; réutiliser son slot n’altère
  pas la référence retournée. Modifier prématurément la cible est refusé.
- Une tâche construit l’enum dans un pool local, le transfère à un enfant attendu
  puis réutilise le slot après la fin de cet enfant.

Les sorties attendues et la destruction unique sont écrites dans les tests.
Les refus sont vérifiés avec `verify_program` et `compile_source`.

## Exécutions et corrections

Journaux dans `validation/async-enum-nominal-*` :

| Journal | Résultat |
| --- | --- |
| first-o0.log | 2 méthodes, 2 échecs : projection non représentée et provenance perdue |
| second-o0.log | 2 méthodes, 1 échec : inférence du type résultat de match encore limitée à Int |
| third-o0.log | 2 méthodes, 1,599 s, code 0 |
| fourth-o0.log | 5 méthodes, 1 échec de fixture : syntaxe de match consommant incorrecte |
| fifth-o0.log | 5 méthodes, 2,695 s, code 0 |
| regression-o2.log | 104 méthodes, 91,860 s, code 0 |

La fixture utilisait `match <-v` ; elle utilise maintenant la syntaxe déjà
retenue `match (->v)`. Aucun changement de grammaire pour contourner cet échec.
Commande de régression :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_enum_nominal test_async_nominal_results test_async_enum_match test_async_consuming_enum_match test_async_owned_enums test_async_enum_suspension_fields test_async_stored_views test_async_match_references test_public_borrowed_handles test_public_structure_handles -v
```

Le C est compilé avec Clang C11, pthread, warnings en erreurs et UBSan fatal.
La régression porte sur les enums propriétaires, matchs empruntés et consommants,
contrats de suspension, références stockées, retours nominaux et handles publics.

## Limites

Ces exécutions couvrent les cas listés, pas tous les graphes ou entrelacements.
Les types récursifs, les compositions non représentées et les interfaces publiques
encore à arbitrer ne sont pas déclarés terminés. Pas de nouvelle campagne de
mutations ni d’audit adversarial ; l’audit indépendant reste prévu séparément.
`reset` reste retiré par défaut. L’objectif global demeure en cours.

Snapshot : `/tmp/crust-before-async-enum-nominal/`. Les quatre patches de modules
sont archivés sous `validation/async-enum-nominal-*.py.patch`.
