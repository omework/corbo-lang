[English](SYNC_TASK_ARGUMENTS_CYCLE.md)

# Arguments de tâches depuis un état async

## Règles et décision intégrée

Ce lot applique T1/T6, B1–B5, D1, L1/L2/L6, AS2/AS8–AS15, RT6/RT7/RT8
et SL1 : une tâche inactive est transférable explicitement à une fonction
synchrone depuis un état async. Le passage ne lance pas son corps. Le callee
peut la rendre, la détruire ou la transmettre au lancement ; les captures,
les sources et les dépendances du résultat restent suivies par contrat.

Pendant ce cycle, l'utilisateur a tranché l'arbitrage de Select : **refuser
dans le prototype une branche pouvant perdre avec un handle lancé encore à
attendre**. Cette décision est devenue SL2 dans ASYNC_MULTITHREAD_RULES.md,
référencée dans LANGUAGE_RULES.md et le brouillon 04. Le document
SELECT_LAUNCHED_HANDLE_DECISION.md clôt cet arbitrage. Aucun join caché ni
abandon de handle n'est introduit. L'arbitrage distinct d'une tâche inactive
capturant un handle lancé reste ouvert.

## Implémentation

- La description symbolique d'un paramètre de tâche est partagée entre la
  vérification du corps et le pont C. La tâche reste opaque ; le pont décrit
  ses captures sans lire ni exécuter son état. Les sources des captures vivent
  dans le scope extérieur du pont, et le paramètre de tâche dans celui de l'appel.
- Le backend prépare le transfert de gauche à droite, invalide le nom d'origine
  et conserve les prêts pendant les arguments suivants. Une tâche préparée est
  un élément de nettoyage distinct d'une allocation Cell.
- Un retour, break/continue sortant de l'appel ou nettoyage d'un état suspendu
  détruit les tâches préparées avant les scopes dont elles dépendent. Les tests
  de capacité un et de répétition vérifient la restitution des états, pas seulement
  la trace de destruction qui pourrait être reproduite par la fermeture du pool.
- Les relais conservent séparément les prêts des captures et ceux du résultat.
  Un choix conditionnel réunit les possibilités. Les champs empruntés d'un graphe
  possédé retourné restent attachés à leurs cibles après attente.
- `task_forward_only` est inféré sur tous les chemins de retour. Une alternative
  qui construit une tâche rend ce fait faux, même si une autre branche rend un
  paramètre. Le contexte d'effets suspendus réutilise les captures connues d'un
  relais pur ; il ne transforme pas une fabrique inconnue en effet vide.
- Les helpers de lancement peuvent produire les handles publics déjà représentés
  et les handles concrets Execution<routine>. Pour ces derniers, le type de
  résultat et ses champs sont tirés de la définition de la routine, y compris
  pour une construction fraîche plutôt qu'un paramètre transmis.

La fixture `open-async-task-relay-argument.crust` était refusée aux deux étapes
pour signature non prise en charge. `sync-task-arguments-baseline.log` le reproduit
avec le snapshot `/tmp/crust-before-sync-task-arguments-current`. Elle compile
maintenant, imprime 1 et détruit Inner et Outer exactement une fois. Les patches
de source sont `validation/sync-task-arguments-*.py.patch`.

## Vérification exécutée

`tests/test_sync_task_arguments.py` comporte dix-huit méthodes finales. Le
comptage O0 de `sync-task-arguments-final-count-o0.log` passe en 8,475 s :
24 exécutions natives, 26 programmes invalides et 52 contrôles de refus
(verify_program et compile_source). Parmi ces méthodes, une examine directement
les contrats de trois fonctions, sans C natif.

Les tests croisent :

- Relais direct et captures imbriquées possédées, emprunts partagés/mutables,
  tableaux, destruction prématurée, dernier usage et ancien nom consommé.
- Refus du transfert implicite et d'une routine différente de même signature ;
  refus d'exporter une tâche dont la cible ne survit pas au receveur.
- Drop depuis un helper, réemploi répété d'un pool d'états de capacité un,
  évaluation gauche à droite et suspension dans un argument ultérieur.
- Retour anticipé pendant la préparation, deux tâches préparées détruites dans
  l'ordre inverse, Select perdant et réemploi des états après son nettoyage.
  Le complément distingue break/continue quittant l'appel et break interne
  au calcul d'un argument qui laisse cet appel continuer.
- Retours propriétaires locaux ou en pool, graphes contenant des emprunts,
  handles publics empruntés et handles concrets propriétaires, avec retour
  par paramètre ou construction fraîche.
- Choix entre deux tâches entrantes ou entre une tâche entrante et une tâche
  fraîche ; union des cibles possibles avant leur dernière utilisation.
- Refus SL2 de `open-select-launched-handle.crust` aux deux étapes. Les cas
  positifs utilisent des tâches inactives et ne contournent pas l'obligation
  d'attendre un handle lancé.

Les premières huit méthodes passent à O0, puis quatorze à O2. La campagne
finale de mutations inclut une baseline de quinze méthodes à O2 ; les deux
ajouts sont ensuite inclus dans la régression finale. La dix-huitième méthode
sur break/continue passe séparément à O2 dans
`sync-task-arguments-loop-exits-o2.log`. Les journaux
intermédiaires restent disponibles. Le premier test de choix conditionnel
omettait le transfert descendant `b ->;` avant son drop dans le if : cette
fixture a été corrigée selon la règle existante, sans changement normatif.

Le harnais C utilise Clang C11/pthread, Wall/Wextra/Werror,
Wno-unused-function, UBSan fatal à O0/O2. Aucun nouveau résultat ASan/TSan.

## Mutations et régressions

La campagne `sync-task-arguments-final-mutations-o2.log` détecte sept fautes :
six par assertion et une par plantage du compilateur sur un programme valide.
Cette dernière retire l'invalidation d'une tâche consommée et provoque un
KeyError au second nettoyage : elle n'est pas comptée comme un refus sémantique
correct d'un programme invalide.

Les six autres fautes retirent les prêts préparés, les captures après relais,
les prêts du résultat, le nettoyage des tâches préparées lors d'une suspension
ou d'une sortie anticipée, ou la preuve que tous les retours sont des relais.
Le réemploi de capacité un révèle les deux fuites d'états.

La première campagne, `sync-task-arguments-mutations-o2.log`, contient une
mutation survivante : retirer la capture d'une tâche retournant elle-même
cette référence était compensé par le prêt du résultat. Le test sélectionné
utilise désormais une tâche retournant Int ; la perte de capture fait accepter
un drop avant l'attente et est détectée aux deux étapes. Le plantage était
initialement classé inconclusif par le filtre du runner ; sa classification
finale est explicite. Aucun taux général de détection n'est revendiqué.

La première régression élargie passe 140 méthodes en 110,754 s à O2, avec
CRUST_SANITIZE=undefined, dans `sync-task-arguments-regression-o2.log`.
Elle couvre les contrats et retours de références imbriqués, les handles,
les appels synchrones, les nettoyages suspendus, les effets de structures
et Select. La régression finale passe 132 méthodes en 92,121 s, avec les mêmes
options, dans `sync-task-arguments-final-regression-o2.log`. Elle inclut les
dix-sept premières méthodes du nouveau lot et les contrats de Select et des
handles touchés par les derniers compléments. Les sélections se recouvrent ;
leurs comptes ne s'additionnent pas comme des tests uniques.

Les huit mutations historiques du nettoyage suspendu sont détectées après une
baseline de dix méthodes : `sync-task-arguments-historical-mutations-o2.log`.
Tous les processus finaux cités sont terminés.

## Limites et suites

`runtime::Handle<View>` pour une structure locale reste refusé par le registre
des signatures publiques. `open-public-local-structure-handle.crust` conserve
ce cas valide, sans le transformer en interdiction normative. Le test de
résultat propriétaire utilise Execution<own> et ne prouve donc pas la prise en
charge de cette signature publique.
Les refus finaux de cette fixture et du remplacement d'un champ descendant
sont reproduits aux deux étapes dans `sync-task-arguments-remaining-probes.log`.

Les préfixes de suspension de fabriques générales comportant une alternative
fraîche restent conservatifs. Les effets d'un helper attendant ou lançant une
tâche ne sont pas supposés vides. Le suivi général des handles lancés, des
signatures et des champs descendants reste à compléter.
La restriction SL2 a désormais une décision ; la capture d'un handle lancé
dans une tâche inactive reste en attente d'arbitrage. L'API du scheduler et
le placement général ne sont pas achevés. L'objectif global reste actif.

Ces tests finis ne constituent ni une preuve formelle ni une couverture
exhaustive des règles, des types ou de leurs compositions.
