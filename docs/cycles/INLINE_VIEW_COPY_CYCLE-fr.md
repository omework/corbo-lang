[English](INLINE_VIEW_COPY_CYCLE.md)

# Copie explicite des vues de sous-structures

## Périmètre et résultat

Raccordement de ST17–ST18 et du brouillon 07 aux vues de sous-structures
déjà prises en charge, à champs terminaux Int. Aucune règle normative modifiée.

`copy(vue)` lit les octets de la sous-structure locale et construit une valeur
indépendante de son type sur la data stack du destinataire. `points.copy(vue)`
construit cette valeur dans un slot de `Pool<Point>`. La copie ne retient pas
la racine par le seul fait d'avoir lu ses champs Int ; la racine reste utilisable
et peut être détruite après le dernier usage de la vue. Le nettoyage de la copie
relève de sa propre source.

Une vue de Point intérieur à un slot de Pool<Segment> ne dispose pas d'un
Pool<Point> d'origine. La forme sans pool reste refusée avec un diagnostic
demandant un pool du type de la sous-structure ; aucun pool alternatif n'est
sélectionné silencieusement. La forme `points.copy(vue)` est exercée, y compris
à travers une fonction et après destruction du Segment d'origine.

## Implémentation

- Le backend copie depuis `structure_view_address`, avec la taille du layout
  Point, vers le stockage créé par les mécanismes existants de copie.
- L'analyse de placement reconnaît les projections contenues et les références
  retournées par contrat. Elle réserve la copie chez son receveur avant l'entrée
  du bloc, de la boucle ou de la fonction productrice. Une simple vue retournée
  ne provoque pas elle-même une allocation.
- L'analyse des résultats conserve séparément `copy_candidates`, les provenances
  de stockage utiles à une copie. Elles ne sont pas ajoutées aux cibles de
  l'emprunt : une vue de `s.debut` ne devient pas un emprunt alternatif de `s`.
- Les contrats de copies instancient ces provenances dans les relais, avec un
  type et une identité de nouvelle valeur locale propres à la copie.
- La forme `break <-copy(vue);` est raccordée au résultat propriétaire explicite.
  L'écriture sans flèche n'est pas rendue implicitement déplaçable.

## Cas et preuves exécutés

Six méthodes dans `tests/test_inline_view_copy.py` : sept programmes admis
exécutés en C, quatre programmes refusés aux deux entrées.

- Copie locale indépendante : adresse différente, source modifiée puis détruite,
  copie encore lisible, deux destructions.
- Copie dans un pool explicite : slot réutilisé après destruction de la copie ;
  source intérieure copiée sans demander un slot du mauvais type.
- Référence retournée à travers deux relais, puis copie par une fonction,
  puis retour de la copie après sortie des frames synchrones.
- Copie dans un pool injecté, résultat retourné ; pool du résultat trop court
  refusé malgré la survie éventuelle de l'original.
- Copies transférées à la sortie d'un bloc et par `break`, racine enfant nettoyée.
- Copie pendant un réemprunt mutable actif refusée, puis autorisée après son
  dernier usage.

| Passage | Résultat | Journal dans `validation/` |
| --- | --- | --- |
| Initial O0 | 5 méthodes, 3 échecs, 1,055 s, code 1 | `inline-view-copy-o0-first.log` |
| Deuxième O0 | 5 méthodes, 1 échec, 1,669 s, code 1 | `inline-view-copy-o0-second.log` |
| Troisième O0 | 5 méthodes, 1 échec, 1,655 s, code 1 | `inline-view-copy-o0-third.log` |
| Quatrième O0 | 5 méthodes, 1,984 s, code 0 | `inline-view-copy-o0-fourth.log` |
| Final O0 | 6 méthodes, 2,514 s, code 0 | `inline-view-copy-o0-final.log` |
| Régression O2 | 35 méthodes, 16,429 s, code 0 | `inline-view-copy-regression-o2.log` |

Les échecs intermédiaires concernaient le placement des copies sortantes, le
traitement du `break` explicite et la perte/confusion de provenance dans les
relais. Les programmes et résultats attendus ont été conservés pendant les
corrections. Les processus ont terminé et leurs codes ont été récupérés.

Clang C11/pthread, UBSan fatal, avertissements comme erreurs pour les tests
source ciblés. Les huit méthodes historiques de régression utilisent leur
harness O2/UBSan et le profil legacy-reset explicite. Aucun test sauté.

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_inline_view_copy
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_inline_view_copy test_inline_structure_borrows test_inline_structure_construction test_async_direct_copy test_foundation_rules.FoundationTests.test_local_structure_copy_is_independent_and_reuses_dead_storage test_foundation_rules.FoundationTests.test_local_structure_copies_transfer_without_moving test_foundation_rules.FoundationTests.test_local_structure_copy_keeps_shared_target_across_return test_foundation_rules.FoundationTests.test_local_structure_copy_from_parameter_uses_receiver_storage test_foundation_rules.FoundationTests.test_local_structure_copied_parameter_retains_target_without_original test_foundation_rules.FoundationTests.test_local_structure_copy_rejects_noncopy_fields_and_active_mutation test_foundation_rules.FoundationTests.test_local_structure_return_through_loop_preserves_reservation test_foundation_rules.FoundationTests.test_local_structure_loop_conditional_breaks_share_reservation
```

## Limites et prochaine étape

Les vues de sous-structures contenant des références ou des champs propriétaires
restent à raccorder. Le travail requis comprend la projection de leurs cibles,
la propagation des mutations vers la racine et les contrats correspondants.
Le stockage de vues dans d'autres valeurs, leur capture async et les résultats
mêlant vue intérieure et référence entière restent également incomplets.

Ce lot n'ajoute ni campagne de mutations, ni génération adversariale, ni modèle
indépendant. Les vérifications concernent les chemins cités et les régressions
directement liées ; elles ne prouvent pas la sûreté générale ni l'achèvement
de toutes les règles de structure.

Snapshot : `/tmp/crust-before-inline-view-copy/`.
Patches : `validation/inline-view-copy-{crust,results}.py.patch`.
