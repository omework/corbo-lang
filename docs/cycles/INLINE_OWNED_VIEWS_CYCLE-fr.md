[English](INLINE_OWNED_VIEWS_CYCLE.md)

# Champs propriétaires dans les vues de sous-structures

## Périmètre

Raccordement de ST7, ST8 et ST15–ST18 : une vue emprunte le stockage de sa
racine, y compris les champs A<T>. Elle ne devient pas propriétaire des objets
pointés. Le remplacement évalue la nouvelle allocation, détruit l'ancienne,
puis installe le nouveau handle dans le champ réel. Les transferts restent
explicites. Aucune modification normative.

Le cycle porte sur les cas fonctionnels et leurs régressions directement liées,
conformément à la priorité utilisateur. Il ne lance pas de nouvelle campagne
adversariale ou de mutations.

## Changements

Les projections du vérificateur incluent maintenant les champs propriétaires
de la racine. Les écritures directes et les effets d'appels sont normalisés en
chemins sur cette racine ; les vues ne sont pas ajoutées à l'inventaire de
nettoyage. Le code C utilise les accès existants à l'adresse du champ intérieur.

L'analyse des résultats conserve les champs propriétaires dans les vues et
dans les vues retournées. Les chemins alternent correctement les projections
intérieures et les indirections A<T>. Les arguments intérieurs directs sont
pris en compte dans les effets d'écriture. Les signatures de retour emprunté
vers une structure possédant des champs sont raccordées aux contrats existants.

L'extraction d'une référence partagée depuis un descendant conserve la cible
finale sans retenir artificiellement les porteurs. Une référence vers le
descendant lui-même conserve les réservations nécessaires à sa survie.

Diffs archivés : `validation/inline-owned-views-{crust,results,constraints}.py.patch`,
comparés à `/tmp/crust-before-inline-owned-views/`.

## Cas exécutés

`tests/test_inline_owned_views.py` : sept méthodes, huit programmes admis
exécutés nativement, sept programmes invalides refusés par `verify_program`
et `compile_source`.

- Lecture via une fonction, destruction unique du descendant avant la racine,
  puis réutilisation de son slot. Copie de la vue non Copy et drop précoce refusés.
- Mutation de l'Int possédé et accès au champ frère disjoint.
- Retour de &mut Int à travers la vue et un relais ; racine et cible réservées
  jusqu'au dernier usage, puis slot réutilisable.
- Remplacement direct par une allocation d'un autre pool : ancien et nouveau
  slots récupérables au bon moment ; absence de flèche refusée.
- Remplacement via contrat ; pool de remplacement trop court refusé.
- Remplacement depuis une vue retournée et depuis un argument `&mut s.inner`.
- Mutation d'une référence dans le descendant A<Leaf>, extraction de cette
  référence, destruction des porteurs et maintien de la nouvelle cible.

## Passages ciblés

| Passage | Résultat | Journal dans `validation/` |
| --- | --- | --- |
| Premier O0 | 5 méthodes, 3 échecs, 0,815 s, code 1 | `inline-owned-views-o0-first.log` |
| Deuxième O0 | 5 méthodes, 2 échecs de sous-cas, 2,222 s, code 1 | `inline-owned-views-o0-second.log` |
| Troisième O0 | 7 méthodes, 3 échecs de sous-cas, 1,889 s, code 1 | `inline-owned-views-o0-third.log` |
| Quatrième O0 | 7 méthodes, 1 échec, 3,123 s, code 1 | `inline-owned-views-o0-fourth.log` |
| Cinquième O0 | 7 méthodes, 3,218 s, code 0 | `inline-owned-views-o0-fifth.log` |
| Historique O2 | 6 méthodes, 4,824 s, code 0 | `inline-owned-views-historical-o2.log` |
| Régressions O2 | 84 méthodes, 46,476 s, code 0 | `inline-owned-views-regression-o2.log` |

Deux défauts de fixtures ont été corrigés sans modifier les attentes du langage :
un nom `n` redéclaré et un accès ultérieur à `q` dans le cas destiné à vérifier
que ce pool était trop court. Les autres échecs ont guidé le raccordement de la
racine, des contrats de retour et des chemins de descendant. La dernière
correction supprime une exigence &mut artificielle sur une référence partagée
extraite depuis un porteur partagé.

Les tests natifs utilisent Clang C11/pthread, UBSan fatal et les avertissements
comme erreurs. Les tests historiques activent explicitement legacy-reset et
imposent O2 ; ils ne réintroduisent pas reset dans l'API publique.

La régression O2 comprend `test_inline_owned_views`, `test_inline_typed_views`,
`test_inline_reference_views`, `test_inline_view_copy`, `test_inline_structure_borrows`,
`test_inline_structure_construction`, `test_nested_field_replacement`,
`test_nested_field_choices`, `test_returned_owned_replacement`,
`test_factory_owned_effects` et `test_async_owned_field_writes`. Elle inclut le
modèle existant d'ensembles de cibles de `test_nested_field_replacement`, sans
étendre ce modèle aux vues intérieures ni lui attribuer cette couverture.

## Limites

Ces résultats couvrent les parcours consignés, pas l'ensemble des combinaisons
de vues alternatives, de graphes récursifs et de projections mixtes. Le stockage
d'une vue dans un champ référence, les captures/résultats async de vues et les
résultats mêlant vue et allocation entière restent à raccorder. Aucun autre
compilateur C ni ASan n'a été exécuté pour ce lot. Le succès des tests n'est
pas une preuve générale de sûreté.
