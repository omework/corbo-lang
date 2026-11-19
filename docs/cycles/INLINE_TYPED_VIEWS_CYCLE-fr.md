[English](INLINE_TYPED_VIEWS_CYCLE.md)

# Vues de sous-structures contenant des références typées

## Périmètre et règles

Extension du raccordement de ST7 et ST10–ST18 aux vues contenant des références
vers des structures typées. Aucune modification normative. La vue ne possède
pas de stockage indépendant : son adresse et ses champs restent ceux de la
racine. Une référence partagée extraite conserve sa cible ; un réemprunt mutable
conserve aussi la réservation de la capacité dont il dérive.

La validation suit le périmètre demandé : cas fonctionnels convenus et
régressions directement liées. Pas de nouvelle campagne de génération,
de mutations ou d'audit adversarial. Aucune preuve générale de sûreté.

## Implémentation

- Autorisation des champs références typées dans les projections intérieures.
- Composition du chemin intérieur dans les contrats de réemprunt typé.
- Comparaison des effets de mutation avec les snapshots de la racine réelle,
  projetés sur le sous-arbre concerné ; les vues ne sont pas des allocations.
- Normalisation des porteurs des capacités mutables lors de la comparaison
  entre le résultat contractuel et celui du corps vérifié.
- Distinction entre un effet sur un descendant propriétaire et les dépendances
  transitives mises en cache à travers un champ référence. Remplacer `link.leaf`
  ne modifie pas le champ `data` de la feuille pointée. Ces dépendances restent
  dans le contrat symbolique ; elles ne deviennent pas des écritures physiques.

Les modifications de `crust.py` et `results.py` sont archivées dans
`validation/inline-typed-views-*.py.patch`, par comparaison avec la copie
`/tmp/crust-before-inline-typed-views/` antérieure au lot.

## Cas ciblés

`tests/test_inline_typed_views.py` contient six méthodes : six programmes admis
exécutés nativement et dix programmes invalides refusés par `verify_program`
et `compile_source`.

1. Retour partagé vers Point à travers deux fonctions et une vue intérieure ;
   destruction du porteur autorisée, destruction/mutation précoce de Point refusée.
2. Copie de Link puis extraction de Point ; destruction des deux porteurs autorisée,
   destruction précoce de la cible refusée.
3. Remplacement du champ référence par un appel sur une vue ; ancienne cible
   libérable et nouvelle cible protégée, lecture depuis la racine mise à jour.
4. Réemprunt mutable typé retourné par relais ; champ frère accessible, destruction
   du porteur et accès incompatibles à la cible ou à la capacité refusés.
5. Extraction transitive de &Int ; destruction des porteurs intermédiaires autorisée,
   destruction de la cible refusée.
6. Remplacement du champ mutable suivi du retour de la nouvelle cible ; ancienne
   cible libérable, nouvelle cible et porteur retenus jusqu'au dernier usage.

## Exécutions et corrections

| Passage | Résultat | Journal dans `validation/` |
| --- | --- | --- |
| Initial O0 | 5 méthodes, 2 échecs, 1,320 s, code 1 | `inline-typed-views-o0-first.log` |
| Deuxième O0 | 5 méthodes, 1,704 s, code 0 | `inline-typed-views-o0-second.log` |
| Troisième O0 | 6 méthodes, 1 échec, 2,048 s, code 1 | `inline-typed-views-o0-third.log` |
| Quatrième O0 | 6 méthodes, 1 échec, 1,763 s, code 1 | `inline-typed-views-o0-fourth.log` |
| Cinquième O0 | 6 méthodes, 2,102 s, code 0 | `inline-typed-views-o0-fifth.log` |
| Régression initiale O2 | 40 méthodes, 2 échecs et 4 erreurs de sous-cas, 17,179 s ; statut terminal non récupéré | `inline-typed-views-regression-o2.log` |
| Ciblé final | 9 méthodes, 4,247 s, code 0 | `inline-typed-views-o0-sixth.log` |
| Régression finale O2 | 40 méthodes, 20,156 s, code 0 | `inline-typed-views-regression-o2-final.log` |
| Régression propriétaires O2 | 19 méthodes, 9,989 s, code 0 | `inline-typed-views-owned-regression-o2.log` |

Les deux premiers échecs venaient d'une fixture comportant une allocation `b`
inutilisée : elle a été déplacée dans le seul cas qui l'utilise, sans relâcher
la règle d'usage explicite. Les deux suivants ont révélé la perte du chemin
intérieur dans le contrat, puis la comparaison d'un porteur vue à sa racine.

La première régression a ensuite révélé le traitement erroné des dépendances
transitives comme des écritures indirectes. Le test historique
`test_replace_shared_typed_field_updates_nested_provenance` a aussi été exécuté
sur la copie antérieure au lot : même erreur, une méthode, 0,096 s, code 1
(sortie de l'outil, pas de journal séparé). Le défaut précédait donc ce lot pour
ce cas. Les attentes des tests historiques sont conservées.

Les six tests nouveaux utilisent Clang C11/pthread, UBSan fatal, avertissements
comme erreurs, à O0 puis O2. Le passage ciblé final ajoute trois tests historiques
dont le harness impose O2 et active explicitement le profil legacy-reset.
La régression principale reprend les modules `test_inline_typed_views`,
`test_inline_reference_views`, `test_inline_view_copy`, `test_inline_structure_borrows`
et douze méthodes typées de `test_foundation_rules` (noms complets dans le journal).
La régression propriétaire reprend `test_returned_owned_replacement`,
`test_factory_owned_effects` et `test_async_owned_field_writes`.

## Limites

Les cas exécutés couvrent des structures ciblées ; ils ne démontrent pas tous
les graphes récursifs ou les combinaisons d'enums. Les champs propriétaires A<T>
dans une vue, le stockage d'une vue dans un champ référence, ses captures et
résultats async ainsi que les résultats mêlant vue et allocation entière restent
à raccorder. Les projections portant déjà un `carrier_kind` ne sont pas étendues
par ce lot. Aucun modèle indépendant, ASan ou autre compilateur C n'a été exécuté
pour ce lot. Reset reste une API historique retirée du prototype par défaut.
