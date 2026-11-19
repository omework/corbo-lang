[English](SELECT_RESULT_PLACEMENT_CYCLE.md)

# Destination extérieure d'un résultat local de Select

## Périmètre et règle

Le placement dans le scope receveur s'applique aux valeurs locales transférées
depuis un résultat de Select, comme aux résultats de blocs, de fonctions et
d'await déjà pris en charge. AS10–AS13 et SL1 conservent leurs obligations :
le résultat ne dépend pas d'un état détruit, et Select nettoie ses perdantes.
Aucune nouvelle règle normative ni promotion d'une cible empruntée.

Le cas `validation/open-async-result-factory-select-result.crust` était refusé
par « le pool local ne survit pas au receveur ». Deux fabriques produisent des
tâches retournant un Point local ; leur appelante sélectionne un résultat puis
le rend à son propre appelant. La destination extérieure était connue, mais
la recherche des constructeurs ne traversait pas Select.

## Implémentation

Le plan de placement reconnaît les instances de Select, rassemble les
constructeurs de leurs branches compatibles et transmet leur résultat à
l'expression await. Le stockage du receveur est ainsi fourni avant toute
construction. Les adresses ne sont pas déplacées après allocation.

Une provenance inconnue reste inconnue. Les allocations provenant d'un pool
explicite et les cibles empruntées ne sont pas déplacées vers une autre source
pour rendre un transfert acceptable. Les contrôles de type et de durée restent
indépendants de ce plan de placement.

## Cas ciblés

Cinq méthodes dans `tests/test_select_result_placement.py`, six exécutions
natives et deux programmes invalides aux deux entrées, soit quatre contrôles
de refus :

- Programme enregistré : le Point gagnant survit au retour de la tâche.
- Appels directs des branches et retour à travers un bloc intermédiaire puis
  une suspension de l'appelante.
- Deux sondes C : la destination injectée contient les deux constructions,
  le gagnant conserve son adresse après terminaison, les états sont rendus
  aux pools ; destruction suspendue et terminaison récupèrent tout le stockage
  après nettoyage des valeurs concernées.
- Une référence au résultat interdit toujours son drop avant lecture.
- Un résultat issu d'un pool explicite trop court ne bénéficie d'aucune
  promotion implicite.

La sonde de stockage existante ajoutait systématiquement le runtime Select,
même lorsqu'il figurait déjà dans le C généré. Elle ne l'ajoute désormais que
s'il est absent. Les premières erreurs de redéfinition C appartenaient à cette
sonde. Une fixture de copie a aussi été alignée sur l'auxiliaire synchrone déjà
pris en charge, au lieu de demander une copie de structure directement dans
le corps async. Les assertions de durée, d'adresse et de nettoyage sont conservées.

## Résultats exécutés

- Ciblé O0 : cinq méthodes, 2,165 s, processus terminé avec code 0 ; journal
  `validation/select-result-placement-o0-second.log`.
- Régression O2 : 94 méthodes, 82,859 s, processus terminé avec code 0 ; journal
  `validation/select-result-placement-regression-o2.log`. Les cinq méthodes
  ciblées sont incluses sur la version finale.

Clang C11, pthread, avertissements traités comme erreurs, UBSan sans récupération.
Aucun test sauté dans ces passages. La sonde adaptée est aussi exercée par la
suite existante de placement dans le parent. Ce n'est pas la suite entière.

## Limites et sélection du travail

Les tests portent sur Point local, des fabriques synchrones et les formes
de transfert décrites. Ils ne constituent pas une preuve de placement pour
tous les graphes, résultats enveloppés ou combinaisons de branches.
Pas de nouvelle campagne adversariale ou de mutations. Les modèles déjà
présents dans les suites liées sont rejoués, sans nouveau modèle revendiqué.

Le fichier `validation/open-cases-implementation-inventory.log` est un
inventaire préalable des 137 exemples existants nommés `open-*` : 117 étaient
acceptés par check, 20 refusés. Plusieurs de ces 20 sont des programmes
intentionnellement invalides. Ce décompte ne mesure ni les fonctionnalités
restantes ni la validation native ; il a servi à retrouver ce cas encore ouvert.

## Reproduction et artefacts

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_select_result_placement
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_select_result_placement test_async_local_parent test_async_result_relays test_async_result_storage test_async_result_factories test_select_source test_async_local_owned_result_graphs
```

Snapshot : `/tmp/crust-before-select-result-placement/`. Différences dans
`validation/select-result-placement-{async_local_placement,test_async_local_parent}.py.patch`.
Les journaux du passage initial sont conservés séparément des résultats finaux.
