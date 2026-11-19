[English](ASYNC_FIELD_LOOPS_CYCLE.md)

# Provenances de champs aux reprises de boucles async

## Implémentation

Ce lot raccorde ST10/ST11, B1/B2/B5, AS9/AS12/AS16 et les règles de
loop/while/break/continue sans modifier la sémantique normative.
Les cibles des champs stockées dans les états peuvent maintenant varier
entre deux itérations. La comparaison des obligations aux reprises distingue
ces cibles des autres obligations de nettoyage, qui restent comparées strictement.

Le backend réutilise son moteur de réanalyse des vues UTF-8. Chaque reprise
ajoute les cibles nouvelles à l'entrée abstraite de la boucle. L'émission
recommence avec un état neuf, puis le corps est revérifié avec l'ensemble
élargi. Les clés de champs sont distinctes des noms de vues ; chaque boucle
conserve sa propre identité. Le stockage initial reste une alternative, y
compris lorsque while n'exécute aucune itération.

Les données conservées entre essais sont des ensembles de cibles symboliques,
pas le code C, les frames ou les obligations de tâches d'un essai précédent.
Les cibles qui ne sont plus durables à l'entrée sont refusées. Les blocs de
nettoyage, les obligations d'attente et les autres emprunts ne sont pas effacés
pour rendre compatibles deux reprises.

## Scénarios et contre-exemples

Huit méthodes de `tests/test_async_field_loops.py` couvrent :

- while de zéro, une ou trois itérations, lecture avant remplacement et yield ;
- loop avec continue explicite, store direct, helper et enfant attendu ;
- accès au paramètre mutable avant le store : permis au premier passage
  seulement mais incompatible aux reprises, donc programme refusé ;
- boucles imbriquées, deux nouvelles cibles et retour anticipé ;
- permutation répétée de deux champs, avec conservation de leurs cellules
  d'origine malgré les changements successifs ;
- référence sauvegardée avant un store puis transmise à un helper qui la
  stocke dans un nouvel objet : l'ancienne cellule du premier passage et les
  nouvelles des suivants sont correctement sélectionnées ;
- reset historique refusé tant que le porteur externe retient la cible,
  réemploi après destruction du porteur ;
- modèle indépendant de douze traces : zéro/une/trois itérations et deux
  choix de valeur pour chaque cible. L'oracle exécute une transition de champ
  concrète, sans consulter les résumés du compilateur.

Le programme négatif de reprise est vérifié aux deux entrées, sans l'exécuter.
Les variantes valides avec entrée partagée exécutent la même séquence de
lectures. Les modèles de traces ne prouvent pas un nombre arbitraire d'itérations.

## Preuves exécutées

Journaux `validation/async-field-loops-*.log`.
La sélection initiale de sept méthodes passe en 10,309 s (`-initial`).
La sélection finale de huit méthodes passe à O0 en 10,737 s (`-final-o0`).
La sélection O2 suivante passe 40 méthodes en 42,611 s (`-final-o2`) :

```
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_async_field_loops test_mutable_field_completion test_borrowed_field_completion test_async_child_field_effects -v
```

La sélection de régression des vues et résultats de boucle passe 20 méthodes
à O2 en 16,589 s (`-view-regression`). Elle rassemble le module
`test_async_loop_references` et les méthodes de `AsyncRuntimeTests` contenant
`loop_carried`, plus les cinq méthodes suivantes :

- `test_async_while_carried_utf8_view_preserves_zero_iteration_source` ;
- `test_async_loop_resumes_and_cleans_each_iteration` ;
- `test_async_loop_exit_can_finish_a_worker_from_the_enclosing_scope` ;
- `test_async_mutable_utf8_view_replaced_before_continue` ;
- `test_async_shared_vector_slice_reassignment_and_loop_sources`.

Ces comptes sont des méthodes, parfois composées de plusieurs programmes ;
les sélections se recouvrent. Aucun changement du compilateur entre ces passes.

Quatre mutations sont détectées (`-mutations`) : oubli des cibles de reprise,
non-installation des ensembles élargis, oubli de la cible initiale et corruption
d'une clé de champ lors de la propagation. La troisième est détectée par la
valeur lue dans le helper après sauvegarde de l'ancien champ ; les mutations
qui empêchent la convergence sont détectées par le refus indu des voisins
valides. Ce n'est pas un taux global de détection des défauts.

Les programmes natifs sont compilés en C11/pthreads avec avertissements
bloquants et UBSan fatal. La compilation Python des modules/tests modifiés
réussit. Le patch du compilateur est conservé dans
`validation/async-field-loops-async_lowering.py.patch`.

## Limites

Ce lot couvre les cibles déjà représentées des porteurs injectés. L'ensemble
élargi est conservateur : une réaffectation exigeant une corrélation précise
entre compteur, cible actuelle et disponibilité exclusive d'un paramètre peut
rester refusée. Les nouvelles exécutions portent principalement sur les champs
partagés ; les champs mutables conservent leurs contrôles d'exclusivité et ne
sont pas considérés comme généralement résolus par cette extension.

Les états de nettoyage incompatibles aux reprises, les cibles inline générales
et les autres agrégats ne sont pas généralisés. Les tests n'établissent ni la
sûreté de tout programme ni tous les ordonnancements. Pas de nouvelle preuve
ASan/TSan, de comparaison entre compilateurs C indépendants ou de preuve formelle.
L'objectif global reste ouvert.
