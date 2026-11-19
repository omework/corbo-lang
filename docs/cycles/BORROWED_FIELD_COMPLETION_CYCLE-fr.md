[English](BORROWED_FIELD_COMPLETION_CYCLE.md)

# Modifications de champs et résultats empruntés à la terminaison

## Implémentation

Ce lot raccorde AS12/AS16, B1/B2/B4/B5 et ST10/ST13 sans modifier la
sémantique normative. Une tâche peut remplacer un champ partagé `&Int`
puis retourner un emprunt Int. Le résultat peut désigner l'ancienne cible,
la nouvelle cible ou un autre paramètre. Les appels synchrones, les enfants
attendus et les fabriques conservent les deux informations : effets sur le
porteur et dépendances du résultat.

L'analyse des chemins du résultat utilise le contrat de terminaison lorsqu'il
contient des modifications de champs, au lieu de lire seulement la projection
syntaxique du return. Ainsi `return v.data` après remplacement désigne bien
la nouvelle cible. Le join synchrone projette l'instantané des captures avant
de publier les stores : un résultat sauvegardé avant remplacement garde sa
cible d'origine. Les champs et le résultat ne retiennent pas arbitrairement
les mêmes allocations.

Le backend accepte aussi l'affectation directe d'un champ partagé `&Int`
depuis un état : évaluation et sauvegarde du descripteur de la cible, contrôle
d'accès au porteur, store C, puis conservation du prêt dans l'état. Cette
opération utilise les mêmes restrictions de cibles durables que les helpers.
Les champs `&mut Int` à remplacer restent un chantier distinct.

Les contraintes de sources sont maintenant inférées après stabilisation des
contrats de résultats et des effets async. Les interfaces provisoires utilisées
uniquement pour cette inférence ont des contraintes absentes (`None`), jamais
présentées comme vérifiées aux appels ou au backend. Les contraintes réelles
sont calculées avant toute vérification des corps et émission.

## Contre-exemples et scénarios

Onze méthodes de `tests/test_borrowed_field_completion.py` vérifient :

- ancien et nouveau résultat distincts, destruction du porteur puis libération
  de la cible qui n'est plus retenue ; cible du résultat toujours protégée ;
- porteur encore vivant : protection de sa nouvelle cible même si le résultat
  désigne l'ancienne ; alternative initiale conservée en cas d'échec de lancement ;
- affectation directe ou helper, avec la même sortie et les mêmes refus ;
- trois niveaux de tâches avec permutation des captures ;
- fabrique et relais de handle public emprunté ;
- pools indépendants, reset historique du pool devenu inutile admis et reset
  du pool encore référencé refusé ;
- résultat mutable indépendant du champ partagé, usage exclusif et mutation ;
- mutation d'une cible encore stockée refusée dans l'état ;
- cible locale refusée. Ce dernier cas reste refusé au titre d'un contrat de
  terminaison non représentable, pas d'un diagnostic précis de durée de vie ;
- modèle indépendant de huit cas : ancien/nouveau résultat, porteur détruit
  ou vivant, cible détruite. Deux programmes exécutés, six refusés aux deux entrées.

Le programme consigné `validation/open-async-completion-result-and-write.crust`
est maintenant exécutable : `16`, `9`, `7`. Son enfant retourne l'ancienne
référence pendant qu'il remplace le premier champ ; le parent stocke ce retour
dans le second champ. Détruire ensuite l'une des deux cibles avant leur lecture
est refusé. Le fichier garde son nom historique pour la traçabilité.

La première passe a découvert le refus indu du reset d'un pool devenu inutile :
l'analyse initiale des contraintes utilisait encore la projection du champ
d'avant exécution. L'ordre des passes décrit ci-dessus le corrige. Le test
admis et son voisin refusé sont conservés.

## Validation exécutée

Journaux `validation/borrowed-field-completion-*.log`.
La première sélection de huit méthodes échoue sur ce refus indu (`-initial`).
Le voisin corrigé réussit en 1,030 s (`-reset`). L'élargissement à onze méthodes
expose deux erreurs de fixtures (`-expanded`) : un marqueur `BEFORE` non remplacé
dans un programme négatif et un motif de diagnostic trop étroit. Les sources
et le motif ont été corrigés sans changer les règles d'acceptation.

Passes finales exécutées :

- `PYTHONPATH=tests python3 -m unittest test_borrowed_field_completion -v` :
  11 méthodes en 21,608 s, OK (`-final-o0.log`).
- Même commande avec `CRUST_TEST_OPT=-O2` : 11 méthodes en 21,624 s,
  OK (`-targeted-final-o2.log`).
- `CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_async_structure_effects test_factory_field_effects test_public_borrowed_handles -v` :
  48 méthodes en 31,410 s, OK (`-contract-final-o2.log`).

La sélection antérieure combinée de 59 méthodes, malgré son nom
`-final-o2.log`, échouait sur les quatre assertions associées aux deux fixtures
corrigées. Les modules qui la composaient ont tous été réexécutés avec succès
par les deux dernières commandes ci-dessus. Ces comptes sont des méthodes,
parfois composées de plusieurs programmes ; les sélections se recouvrent.
La régression élargie exécute :

```
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_async_reference_returns test_async_local_references test_async_field_reference_returns test_async_detached_field_returns test_async_match_references test_async_loop_references test_captured_cell_descriptors -v
```

Elle réussit 85 méthodes en 105,922 s (`-reference-regression.log`). Aucun
changement du compilateur entre cette passe et les dernières passes ciblées.

Les programmes natifs sont compilés en C11/pthreads, avertissements bloquants,
UBSan fatal, à O0/O2. La compilation Python des modules et nouveaux tests réussit.
Les patches du lot sont conservés dans `validation/borrowed-field-completion-*.py.patch`.

Cinq mutations sont détectées : suppression des provenances de terminaison,
projection du résultat après publication des stores, suppression du store C,
oubli du prêt de la cible stockée, calcul prématuré des contraintes.
Certaines mutations provoquent le refus d'un voisin valide ; d'autres perdent
un contrôle d'emprunt ou produisent une valeur incorrecte. Aucun programme
potentiellement invalide n'a été exécuté pour provoquer de l'UB.

## Limites

Les champs remplacés sont partagés Int, sur des porteurs injectés et avec les
cibles durables déjà représentées. Les champs mutables, les cibles inline
générales, les résultats empruntés agrégés et les effets sur les reprises de
boucle restent à généraliser. La corrélation exacte entre succès/échec et les
états des champs n'est pas ajoutée. Les contraintes et résultats génériques
ne sont pas prouvés complets par ces cas finis.

Pas de preuve générale de sûreté, de concurrence ou de tous les
ordonnancements ; aucune nouvelle preuve ASan/TSan ni comparaison entre
compilateurs C indépendants. L'objectif global reste ouvert.
