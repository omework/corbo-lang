[English](TASK_RESULT_STORAGE_CYCLE.md)

# Stockage du résultat d'une tâche dans les contrats

## Règles et défauts

Ce lot applique V1, T1/T6, les contrats, B1–B5, D1, L1/L2/L6,
AS9/AS12 et MT5/MT6. Il ne change pas les règles normatives. Une structure
locale T et une allocation A<T> restent distinctes, même lorsque le résultat
traverse une tâche opaque, un handle concret et plusieurs fonctions.

`validation/open-task-result-storage-contract.crust` était refusé aux deux
étapes : le contrat de consume ne pouvait exprimer que le résultat de la tâche
entrante devait être local. La baseline reproduit ce refus. L'annotation
Point est désormais une exigence transmise aux appelants ; elle ne convertit
pas le résultat. Un appel dont le résultat est en pool est refusé.

Deux autres contre-exemples valides ont été conservés et corrigés :

- `open-task-result-storage-copy.crust` : une tâche copie une structure
  empruntée. L'entrée symbolique ne décrivait pas le stockage de cette copie.
- `open-task-result-storage-graph.crust` : une tâche construit une racine
  locale contenant une allocation en pool. La description symbolique et le
  flot de contraintes confondaient la source du descendant avec celle de la
  racine ; le match ou l'appel rejetait le résultat local.

Les trois fixtures sont maintenant acceptées aux deux étapes et exécutées
par les tests. Le contrôle du stockage ne supprime ni les dépendances aux
pools descendants ni les emprunts du résultat.

## Implémentation

L'analyse complémentaire des exigences projette le résultat futur d'un
paramètre task/execution avant d'examiner ses sources. Chaque source inconnue
issue d'un paramètre impose une obligation local/pool à ce paramètre. Ces
obligations sont propagées jusqu'à stabilisation et publiées dans le contrat.
Les résultats déjà connus incompatibles sont refusés, même dans une fonction
sans appel : résultat frais local, allocation depuis un pool injecté, paramètre
explicitement A<T>, ou exigence déjà présente sur la source.

Le vérificateur des appels examine task_result_sources pour les tâches et
handles, distinctement des sources de leurs autres captures. Les entrées
symboliques utilisent les exigences déduites. Une copie issue d'un emprunt
reçoit une identité de résultat distincte de sa cible empruntée.

`async_result_storage.root_result_parameters` projette les seules sources de
la racine depuis le contrat de complétion. Les champs propriétaires restent
suivis séparément. Cette projection est partagée par le flot des contraintes
et les descriptions symboliques ; elle ne décide pas d'un nouveau placement.

Le raccordement du type public Handle<Structure> reste en cours. Les
préparations de registre présentes dans handle_types.py/async_lowering.py ne
sont pas activées par ce lot, et ne constituent pas un support de cette syntaxe.
Les nouveaux tests utilisent les tâches nominales et Execution<routine>.

## Vérification exécutée

Onze méthodes dans `tests/test_task_result_storage.py` couvrent :

- modèle indépendant des quatre combinaisons stockage local/pool demandé et
  fourni ; relais sur trois fonctions et inspection des contrats ;
- choix entre deux tâches, les deux branches et les deux sources possibles ;
- handles déjà lancés transmis par contrat, puis attendus explicitement ;
- stockage du résultat différent de celui d'une capture détruite sans retour ;
- copie d'une structure empruntée, locale ou en pool ;
- racine locale et descendant en pool, nettoyage et réemploi d'un pool de
  capacité un après destruction du résultat ;
- résultat contenant un emprunt, lecture après relais et refus d'un drop
  prématuré de sa cible ;
- refus d'une exigence incompatible avec une provenance déjà déterminée ;
- maintien de l'interdiction de cacher un join synchrone dans un appel async.

`validation/task-result-storage-count-o0.log` : **11 méthodes, 14 exécutions
natives, 18 programmes invalides, 36 contrôles de refus**, en 8,301 s.
Les refus sont contrôlés par verify_program et compile_source. Les assertions
de contrats sont supplémentaires, sans exécution C.

`validation/task-result-storage-regression-o2.log` : **128 méthodes en
85,870 s**, incluant les tests nouveaux, les exigences de stockage historiques,
les arguments de tâches, les graphes locaux retournés, le placement des
résultats, les relais de handles concrets, les références détachées, les contrats
de handles publics et les contrats de Select. CRUST_SANITIZE=undefined et
CRUST_TEST_OPT=-O2 sont activés.

Le harnais natif utilise Clang C11/pthread, Wall/Wextra/Werror,
Wno-unused-function et UBSan fatal, à O0/O2. py_compile réussit pour les modules
modifiés et les nouveaux tests. Aucun nouveau résultat ASan/TSan.

## Mutations, échecs conservés et limites

`validation/task-result-storage-mutations-o2.log` contient une baseline de
11 méthodes en 6,444 s puis sept fautes détectées : oubli de la projection du
résultat, oubli de son exigence, conservation d'une seule source possible,
entrée symbolique toujours en pool, confusion des descendants avec la racine,
omission du stockage de copie et utilisation des sources de captures au lieu
de celles du résultat. Les détections sont des assertions, notamment des refus
incorrects de programmes valides ou des contrats incomplets. Elles ne sont
pas présentées comme sept corruptions mémoire observées.

Les six mutations historiques de `run_storage_requirement_mutations.py` sont
également détectées après une baseline de dix méthodes en 7,541 s :
`validation/task-result-storage-historical-mutations-o2.log`. Les deux
campagnes sont finies et ne donnent aucun taux général de couverture.

Les journaux initial/second O0 conservent deux erreurs de fixtures : un join
caché dans une fonction appelée depuis async, pourtant interdit, et l'absence
de transfert descendant avant une expression de résultat dans un bloc enfant.
La deuxième exécution avait suivi un script d'édition échoué et répétait les
mêmes fixtures. Ces cas ont été corrigés selon les règles existantes ; le join
caché est maintenant explicitement testé comme invalide. Le troisième passage
passe huit méthodes. Le quatrième révèle la confusion des sources dans le flot
de contraintes ; le cinquième passe onze méthodes après sa correction.
Les premières probes de copie/graphe avaient aussi des formes syntaxiques non
prises en charge ; les fixtures finales conservent les contre-exemples valides
ayant révélé les défauts, et les journaux intermédiaires ne sont pas supprimés.

`validation/task-result-storage-remaining.log` confirme :

- les trois contre-exemples de ce lot acceptés aux deux étapes ;
- Handle<View> encore refusé par le registre des signatures publiques ;
- le remplacement des dépendances d'un champ descendant depuis async encore
  refusé (`open-nested-field-replacement.crust`) ;
- le refus SL2 de `open-select-launched-handle.crust` aux deux étapes. La
  décision utilisateur « refuser ce cas dans le prototype » est déjà intégrée
  dans ASYNC_MULTITHREAD_RULES.md et SELECT_LAUNCHED_HANDLE_DECISION.md.

Le cas distinct d'une tâche inactive capturant un handle déjà lancé reste en
attente d'arbitrage. Les signatures générales, les effets descendants, le
placement général et le remplacement public du scheduler ne sont pas achevés.
Les sorties faillibles sans charge, les types récursifs et toutes les
combinaisons d'enveloppes ne sont pas couverts exhaustivement par ce lot.
Aucun reset n'est réintroduit. L'objectif global reste actif.

Les diffs des quatre modules de ce lot sont archivés dans
`validation/task-result-storage-*.py.patch`, depuis le snapshot
`/tmp/crust-before-task-result-storage/`. Tous les processus cités sont terminés.
Ces tests et modèles finis ne constituent pas une preuve générale de sûreté.
