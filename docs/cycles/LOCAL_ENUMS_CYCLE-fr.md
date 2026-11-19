[English](LOCAL_ENUMS_CYCLE.md)

# Enums sur la data stack implicite

## Règles et périmètre

Le brouillon 05 impose la data stack par défaut aux valeurs hors pool.
Ce lot raccorde les enums à ce stockage en code synchrone et async, avec
les transferts explicites, les réservations du parent, AS8–AS12 et le nettoyage
existant des champs possédés et empruntés. Les pools d’enums gardent leur
organisation par bras ; aucune règle normative de pool n’est remplacée.

La construction locale emploie `Choice.Two { x: 9, y: 11 }`, avec la désignation
de variante déjà utilisée par les constructions en pool et les matchs.
Les champs restent explicites et complets. Une valeur locale T ne devient pas
une allocation A<T>.

## Implémentation

- Le parseur reconnaît les littéraux qualifiés d’enum sans source de pool.
- Le tag du bras appartient au layout de la valeur. Match, comparaison et
  projections des ponts synchrones le lisent depuis `Cell.layout` ; `Cell.source`
  conserve son rôle de source de libération. Pour les pools, ces deux pointeurs
  identifient déjà le même bras ; pour une valeur locale ils sont distincts.
- Chaque variante locale possède des métadonnées statiques avec son nom, son
  tag, ses offsets et ses types de champs. Elles survivent à l’état producteur.
- Les réservations synchrones d’un résultat de type enum ont la taille maximale
  des charges possibles, calculée en C avec les tailles de la cible. La
  construction installe ensuite le layout du bras effectivement choisi.
- Les destinations de résultats async incluent les enums, et les constructeurs
  locaux utilisent la data stack prévue par le plan de placement existant.
- L’affichage d’un agrégat possédé nommé dans un état utilise `cell_print`, avec
  contrôle des emprunts comme pour les autres usages.

## Cas ciblés

Huit méthodes dans `tests/test_local_enums.py` : dix programmes admis exécutés
et trois programmes invalides vérifiés par les deux entrées du compilateur.

- Trois variantes, dont une vide, lecture synchrone et affichage du bon bras.
- Match async avec yield et appel d’un helper synchrone après suspension.
- Retour synchrone conditionnel : les deux variantes de tailles différentes.
- Construction par helper synchrone, transfert via une tâche et join.
- Construction async directe, retour conditionnel et transfert à un enfant attendu.
- Sortie d’un bloc enfant, if avec receveur et sortie de boucle par break.
- Enum local possédant une allocation et empruntant une cible : retour, match
  consommant, destruction unique du descendant et réutilisation de son slot.
- Refus d’un champ manquant, d’une référence locale trop courte et d’une
  destruction de cible avant le dernier usage.

## Exécutions

| Journal dans validation/ | Résultat |
| --- | --- |
| local-enums-first-o0.log | 5 méthodes, 3 échecs : affichage async, destination de retour et fixture Bool synchrone |
| local-enums-second-o0.log | 5 méthodes, 2,199 s, code 0 |
| local-enums-third-o0.log | 8 méthodes, 4,281 s, code 0 |
| local-enums-regression-o2.log | 124 méthodes, 75 échecs de sous-cas, 57,124 s, code 1 : symbole de layout hors portée |
| local-enums-regression-second-o2.log | 124 méthodes, 103,565 s, code 0 |
| local-enums-historical-o2.log | 23 méthodes, 6,510 s, code 0 ; harnais historique sans optimisation explicite ni sanitizer |

La première fixture utilisait `Bool` dans une signature synchrone. Elle a
d’abord été réécrite avec Int ; l’inspection suivante a confirmé que les
paramètres booléens sont déjà implémentés avec `bool` en minuscule. Le test
utilise désormais cette écriture, sans nouvelle sémantique ni alias ajouté.
Voir le lot des handles d’enums locaux pour sa réexécution. La régression a ensuite révélé une affectation de layout superflue pour les
structures locales à résultat réservé : le symbole appartenait à l’appelant,
pas au helper C généré. Seuls les enums installent maintenant leur bras lors
de la construction ; une structure conserve son layout déjà réservé.
Les deux autres échecs ciblés
ont nécessité les raccordements de génération décrits ci-dessus.

Les exécutions ciblées et la régression async utilisent Clang C11/pthread,
warnings en erreurs et UBSan fatal. Les sorties attendues sont écrites dans les
tests. La passe historique sélectionne les méthodes `test_enum_*` de
`test_crust.PrototypeTests`, avec leur propre harnais historique. Celui-ci
n’utilise pas `CRUST_TEST_OPT` : malgré le suffixe du journal et la variable
d’environnement, cette passe ne revendique donc ni O2 ni UBSan.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_local_enums -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_local_enums test_async_owned_enums test_async_enum_match test_async_consuming_enum_match test_async_enum_nominal test_async_local_struct_helpers test_async_local_owned_result_graphs test_async_result_storage test_public_structure_handles test_async_local_parent test_async_loop_placement -v
```

## Limites

Le support est vérifié sur les layouts déjà représentés et les chemins listés.
Ce lot ne généralise pas tous les types de champs ou les graphes récursifs.
Pas de nouvelle campagne adversariale ou de mutations ; les résultats ne
constituent pas une preuve générale de sûreté. Reset reste retiré par défaut,
les cas historiques qui le demandent gardent leur option dédiée.
L’objectif global reste actif.

Snapshot : `/tmp/crust-before-local-enums/`. Patches archivés sous
`validation/local-enums-*.py.patch`.
