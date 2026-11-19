[English](INLINE_REFERENCE_VIEWS_CYCLE.md)

# Vues de sous-structures contenant des références Int

## Périmètre

Raccordement de ST7 et ST10–ST18 aux sous-structures dont les champs terminaux
sont Int, &Int ou &mut Int. Aucune modification normative. Les copies suivent
ST17 : les champs partagés sont copiables, les champs mutables ne le sont pas.

Les vues restent des descriptions non propriétaires du stockage de la racine.
Les références contenues désignent leurs cibles existantes ; aucun slot n'est
créé pour une sous-structure ou pour une cible simplement empruntée.

## Changements

Le vérificateur projette les dépendances de la racine sur le préfixe de la vue.
La projection est rafraîchie depuis la racine lors des accès et des vérifications
d'état. Une réaffectation via la vue préfixe le chemin modifié et met à jour
la racine. Les snapshots de contrôle de flux continuent donc de porter l'état
canonique de cette racine.

Les réservations d'un sous-arbre incluent les cibles des champs références
qu'il contient. Le réemprunt d'une capacité mutable intérieure est reconnu
comme dérivé de la capacité du porteur, sans double comptage. Les accès à
l'ancienne cible, au porteur ou à la capacité restent contrôlés séparément.

Les analyses de résultats et de contraintes conservent le chemin intérieur et
le porteur correspondant. Les effets d'un appel sur une vue sont traduits en
effets sur ce porteur. Une référence partagée retournée comme valeur garde sa
cible, sans ajouter une dépendance artificielle au slot de la sous-structure.
Les résultats de remplacement prennent en compte le nouvel état des champs.

La copie intérieure sans pool explicite infère maintenant l'exigence d'une
racine locale dans le contrat. Cette exigence se propage aux appels, comme les
exigences de stockage existantes. Une copie indépendante perd les métadonnées
de projection de son origine tout en conservant ses champs références.

## Cas exécutés

Neuf méthodes dans `tests/test_inline_reference_views.py` : neuf programmes
admis exécutés nativement, douze programmes refusés aux deux entrées.

- Lecture et copie d'une vue partagée ; copie encore utilisable après drop du
  porteur, cible retenue jusqu'au dernier usage de la copie.
- Référence partagée extraite par des relais, détachée du porteur ; drop trop
  tôt de la cible refusé.
- Copie retournée par fonction depuis une vue intérieure ; cible partagée
  conservée après destruction de la racine.
- Réaffectation d'un champ partagé, directe ou via un contrat ; nouvelle cible
  visible depuis la racine et ancienne cible libérable.
- Vue mutable retournée à travers deux fonctions puis utilisée pour modifier
  le champ ; modification concurrente via la racine refusée.
- Réaffectation suivie du retour de la référence ; la nouvelle cible reste
  protégée après destruction du porteur.
- Réemprunt du champ &mut Int via une fonction ; frère disjoint accessible,
  accès incompatibles à la capacité, à la cible et au porteur refusés.
- Remplacement d'un champ mutable ; ancienne cible libérable, nouvelle cible
  réservée jusqu'à destruction du porteur. Copie du champ mutable refusée.

Le passage final O0 inclut aussi les six méthodes du lot de copies de vues :
quinze méthodes, seize programmes admis exécutés et seize refusés aux deux
entrées. Clang C11/pthread, UBSan fatal et avertissements comme erreurs.

## Résultats et corrections intermédiaires

| Passage | Résultat | Journal dans `validation/` |
| --- | --- | --- |
| Initial O0 | 6 méthodes, 3 échecs, 1,232 s, code 1 | `inline-reference-views-o0-first.log` |
| Deuxième O0 | 6 méthodes, 2,547 s, code 0 | `inline-reference-views-o0-second.log` |
| Troisième O0 | 7 méthodes, 3,727 s, code 0 | `inline-reference-views-o0-third.log` |
| Première régression O2 | 70 méthodes, 54,232 s, code 0 | `inline-reference-views-regression-o2.log` |
| Quatrième O0 | 9 méthodes, 1 échec, 4,690 s, code 1 | `inline-reference-views-o0-fourth.log` |
| Cinquième O0 | 15 méthodes, 1 échec, 6,634 s, code 1 | `inline-reference-views-o0-fifth.log` |
| Sixième O0 | 15 méthodes, 2 sous-cas de diagnostic en échec, 6,763 s, code 1 | `inline-reference-views-o0-sixth.log` |
| Final O0 | 15 méthodes, 9,288 s, code 0 | `inline-reference-views-o0-final.log` |
| Régression finale O2 | 82 méthodes, 62,577 s, code 0 | `inline-reference-views-regression-o2-final.log` |
| Copies async O2 | 6 méthodes, 3,643 s, code 0 | `inline-reference-views-async-copy-o2.log` |

Défauts rencontrés : double comptage de la capacité mutable du sous-arbre,
référence partagée retournée classée à tort comme réservant un porteur mutable,
et perte du chemin intérieur dans la jonction des valeurs de l'analyse de
contraintes. Cette dernière empêchait d'inférer l'exigence de stockage de la
copie retournée. Ils ont été corrigés sans supprimer les vérifications d'accès.

Deux ajustements de fixtures sont explicites : l'affectation du paramètre
référence utilise désormais `v.data = &*n`, notation de réemprunt déjà retenue ;
le test historique de copie sans pool attend le diagnostic d'incompatibilité
de stockage désormais émis plus tôt. L'attente de refus est conservée aux deux
entrées. Les journaux d'échec restent disponibles.

Tous ces processus ont terminé ; leurs codes ont été récupérés. Aucun test
sauté dans ces passages. La régression finale inclut les deux cas ajoutés et
les dernières corrections de provenance et d'exigences de stockage.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_inline_reference_views test_inline_view_copy
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_inline_reference_views test_inline_view_copy test_inline_structure_borrows test_inline_structure_construction test_stored_field_reborrows test_async_field_reborrows test_nested_field_replacement test_nested_field_choices test_storage_requirements
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_async_direct_copy
```

## Limites et suite

Restent à raccorder : les vues contenant des références de types autres qu'Int
ou des champs A<T>, le stockage d'une vue comme champ référence, les captures
et retours async de vues, et les résultats mélangeant référence entière et
vue intérieure. Ces cas ne sont pas déclarés implémentés par ce lot.

Le reset public reste retiré du prototype. Les régressions historiques qui
exercent encore reset utilisent leur profil legacy explicite. Les tests source
de ce lot portent sur drop et les durées de vie ordinaires.

Pas de nouvelle campagne de mutations ou de génération adversariale. Les
modèles présents dans les modules de régression sont exécutés avec leurs cas
existants ; aucun modèle indépendant des nouvelles projections n'est ajouté.
Les résultats ne prouvent ni la sûreté générale ni l'achèvement de ST7 complet.

Snapshot : `/tmp/crust-before-inline-reference-views/`.
Patches : `validation/inline-reference-views-{crust,results,constraints,structure_views,array_syntax,storage_requirements}.py.patch`.
