[English](INLINE_STRUCTURE_BORROWS_CYCLE.md)

# Emprunts source de sous-structures à champs Int

## Périmètre

Implémentation partielle de ST6–ST8, sans changement des règles normatives.
Le cas enregistré dans `validation/open-inline-structure-borrow.crust` est
désormais accepté par `verify_program` et `compile_source`, puis exécuté en C.
Le refus historique reste conservé dans `structure-view-source-gap.log`.

Une vue de sous-structure utilise `CrustStructureView` : racine, décalage,
taille et layout transmis par valeur. Elle ne consomme aucun slot indépendant.
Le vérificateur conserve une projection nominale et une réservation du préfixe
de chemin, rattachée à la racine. Les accès à ses champs composent ce chemin.
Les contrats de résultats conservent ces projections à travers les relais.
Les fonctions synchrones générées adaptent leur signature C à cette représentation.

Les accès et appels incompatibles restent interdits jusqu'au dernier usage.
Les frères prouvés distincts restent accessibles. La destruction ou la sortie
du scope de la racine ne peuvent laisser une vue encore utilisable.

## Cas exécutés

Sept méthodes dans `tests/test_inline_structure_borrows.py`, neuf programmes
admis exécutés nativement et dix programmes refusés aux deux entrées :

- Cas enregistré : mutation par fonction, lecture du frère, une seule destruction.
- Réservation mutable du sous-arbre, libération au dernier usage ; lecture,
  mutation, destruction et nouvel emprunt incompatibles refusés.
- Vue partagée, affichage nominal et deux vues mutables sur des frères distincts.
- Retour d'une sous-structure à travers deux fonctions ; racine protégée.
- Retour d'un emprunt Int depuis la vue ; mutation d'un champ frère autorisée,
  mutation du champ ciblé refusée.
- Sortie d'un bloc enfant permise lorsque la racine survit ; racine locale
  détruite à la sortie du bloc refusée.
- Résultats de `if` et `loop`, modification en place et adresse inchangée.

Le premier passage rencontrait un défaut du vérificateur : le prêt d'un champ
réemprunté et la réservation du sous-arbre étaient comptés comme deux capacités
mutables indépendantes. La collecte des prêts reconnaît maintenant leur filiation.
Les vérifications d'accès au champ restent actives ; le test de mutation
incompatible continue de refuser le programme. Aucun résultat attendu n'a été
affaibli pour obtenir le passage des tests.

## Preuves d'exécution

| Passage | Résultat | Journal dans `validation/` |
| --- | --- | --- |
| Ciblé initial O0 | 6 méthodes, 1 échec, 2,311 s | `inline-structure-borrows-o0-first.log` |
| Après correction O0 | 6 méthodes, 2,560 s, code 0 | `inline-structure-borrows-o0-second.log` |
| Ciblé final O0 | 7 méthodes, 3,171 s, code 0 | `inline-structure-borrows-o0-third.log` |
| Régression liée O2 | 61 méthodes, 38,277 s, code 0 | `inline-structure-borrows-regression-o2.log` |
| Champs historiques O2 | 5 méthodes, 2,551 s, code 0 | `inline-structure-borrows-fields-o2.log` |

Le code de sortie du premier processus n'a pas été récupéré dans le contexte
conservé ; le journal atteste explicitement `FAILED (failures=1)`.
Les codes des quatre passages suivants ont été récupérés à la fin des processus.
Clang C11/pthread, UBSan fatal et avertissements comme erreurs pour les tests
source ciblés ; les cinq tests historiques utilisent leur profil legacy-reset
explicite et leur harness O2/UBSan. Aucun test sauté dans ces passages.

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_inline_structure_borrows
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_inline_structure_borrows test_structure_view_runtime test_inline_structure_construction test_stored_field_reborrows test_async_field_reborrows test_async_direct_copy test_async_struct_pools
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_foundation_rules.FoundationTests.test_struct_int_fields_use_same_slot_and_respect_whole_borrows test_foundation_rules.FoundationTests.test_struct_int_field_loans_distinguish_siblings_and_keep_carrier_alive test_foundation_rules.FoundationTests.test_returned_struct_field_contract_preserves_exact_paths test_foundation_rules.FoundationTests.test_returned_reference_array_preserves_inline_field_path test_foundation_rules.FoundationTests.test_array_update_contracts_relay_inline_field_paths
```

## Limites et suite

- Les nouvelles vues source sont limitées aux sous-structures dont les champs
  terminaux sont Int. Les champs références et A<T> doivent encore être raccordés.
- La copie d'une sous-structure empruntée reste explicitement refusée.
- Le stockage d'une vue dans un champ référence et sa capture async restent
  explicitement refusés ; l'ABI interne seule ne valide pas ces fonctionnalités.
- Un résultat mêlant référence d'objet entier et vue intérieure est refusé
  avec un diagnostic de fonctionnalité non raccordée. Une représentation
  commune reste à implémenter ; ce n'est pas une nouvelle règle du langage.
- Le backend prépare le type de résultat des bras de match, mais ce lot ne
  contient pas de nouveau cas source de match retournant une sous-structure.
- Pas de nouvelle campagne adversariale, de mutations ou de génération de
  programmes. Les modèles existants des modules de régression ont exécuté
  leurs cas ; aucun modèle indépendant nouveau des vues source n'a été ajouté.

Ces exécutions vérifient les chemins cités ; elles ne prouvent pas la sûreté
générale et ne closent pas l'implémentation de ST7 ni l'objectif global.

Snapshot : `/tmp/crust-before-inline-structure-borrows/`.
Patches : `validation/inline-structure-borrows-{crust,results,constraints,structure_views}.py.patch`.
