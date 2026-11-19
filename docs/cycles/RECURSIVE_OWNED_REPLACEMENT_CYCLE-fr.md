[English](RECURSIVE_OWNED_REPLACEMENT_CYCLE.md)

# Remplacement d'un champ propriétaire derrière des liens récursifs

## Portée

Les règles existantes de remplacement évaluent la nouvelle allocation avant
de détruire l'ancienne, conservent la source de la nouvelle valeur et exigent
que son pool survive au porteur. Le transfert ne déplace pas la cible allouée.
Ce cycle vérifie leur application à un champ A<Int> d'une structure Leaf,
elle-même détenue après deux liens A<Node> d'un enum récursif.

Cette composition fonctionnait déjà : aucun changement du compilateur n'a été
nécessaire. Le test manquant est ajouté ; il ne justifie pas de retravailler
le mécanisme de remplacement.

## Cas exécutés

Une méthode dans tests/test_recursive_owned_replacement.py, deux programmes
valides natifs (appel synchrone et appel depuis une tâche), deux invalides
aux deux entrées du compilateur.

Le helper remplace Leaf.item depuis un autre pool. La lecture profonde produit
9, l'ancien pool de capacité un accepte 11, puis la destruction du graphe libère
le slot neuf qui reçoit 12. L'état async suspend après le remplacement. Chaque
ancienne et nouvelle cible est détruite une fois. Le pool fourni au helper dans
un bloc enfant, plus court que le porteur, est refusé dans les deux variantes.

Les premières assertions de trace supposaient à tort le nom de champ `item`.
Le runtime conserve le nom d'allocation `first` et nomme la nouvelle `champ`.
L'oracle vérifie désormais le nombre de destructions de chaque valeur unique,
et non ce libellé interne. La sortie et le réemploi de capacité un passaient
dès le premier essai. Le deuxième journal conserve un échec de regex (`surviv`
ne correspond pas à `survit`), corrigé sans changement d'attente sémantique.

| Journal dans validation/ | Résultat |
| --- | --- |
| recursive-owned-replacement-first-o0.log | Échecs de libellé de trace uniquement |
| recursive-owned-replacement-second-o0.log | Refus corrects, regex de diagnostic erronée |
| recursive-owned-replacement-final-o0.log | Succès, code 0 |
| recursive-owned-replacement-final-o2.log | Succès, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_recursive_owned_replacement -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_recursive_owned_replacement -v
```

Les deux niveaux compilent C11/pthread, warnings en erreurs, UBSan fatal.
Aucun changement du compilateur depuis la régression de 97 méthodes du cycle
RECURSIVE_MUTABLE_RESULTS_CYCLE.md ; cette régression n'est pas relancée.
Pas de nouveau modèle indépendant ni de campagne adversariale ou de mutations.

## Limites

Remplacement du champ terminal A<Int> dans les graphes construits, pas
remplacement d'un lien A<Node> complet ni validation de toutes les formes de
graphes ou de sources. Les garanties ne sont pas des preuves générales.
L'objectif d'intégration global et ses arbitrages restent ouverts.
