[English](AWAIT_NOTIFICATIONS_CYCLE.md)

# RT2 — Notifications des attentes async

## Portée et implémentation

Ce lot applique RT2 et AS4 du brouillon 04, sans modifier les règles normatives.
L'attente d'un handle lancé inscrit un ticket vers la tâche qui pilote le poll.
Une chaîne d'attentes directes transmet ce ticket jusqu'à l'enfant qui attend
le handle. L'enfant direct demeure exécuté sur le thread de son appelante.

Une attente inscrite rend Pending ; elle ne se remet plus spontanément en file.
Yield conserve son comportement volontaire. Les entrées persistantes des
workers dédiés et des blocs natifs fournissent également les notifications.
Un harnais sans entrée ni ticket conserve son ancien comportement par Yield.

L'inscription et le retrait de l'enfant sont sérialisés par le mutex de son
entrée. La notification de son parent intervient hors de ce mutex, pour ne
pas imbriquer les verrous de deux entrées. Elle précède la publication finale
de `worker_done` : un thread détaché ne doit plus notifier un contexte après
avoir rendu observable sa propre fin. Si le parent reprend dans cet intervalle,
il rend Yield jusqu'à la publication ; il ne s'endort pas sans notification
future. Ce passage transitoire ne promet pas l'absence absolue de repoll.

Les tickets générationnels protègent le réemploi des frames. L'obligation
d'attendre les handles garantit que l'appelante conserve les états nécessaires.
Le protocole actuel comporte un seul consommateur par handle ; Select n'est
pas implémenté par ce lot.

## Contre-exemple corrigé

Une soumission C avec une entrée différente de celle préassociée à la frame
ne mettait pas à jour `task->queue_entry`. L'attente consultait donc la mauvaise
entrée, ou aucune entrée, et le parent pouvait tourner par Yield plutôt que
d'attendre. Le test d'ordre des événements, sans préassociation manuelle,
échoue sur l'assertion que seule la tâche enfant est prête. La soumission lie
maintenant la frame à l'entrée effectivement utilisée.

Reproduction antérieure :
`validation/await-notifications-submission-entry-before.log`.
Ce défaut concerne le protocole interne ; les fabriques normales utilisaient
déjà la même entrée lors de la soumission.

## Vérification ciblée

`tests/test_await_notifications.py` exerce trois scénarios :

- Programme Crust : un tableau local et son emprunt traversent deux attentes
  directes, puis un handle lancé. La feuille est suspendue par le harnais.
  Cent tentatives de retrait ne trouvent aucune tâche prête avant son réveil.
  Deux polls par fonction suffisent ensuite, le résultat vaut 9, et vingt
  réemplois rejettent les anciens tickets.
- Ordres imposés : fin avant inscription, pendant le poll du parent, après sa
  suspension, et reprise dans l'intervalle notification/publication. Les deux
  voies de fin (file et worker dédié) sont exercées, vingt-cinq fois chacune,
  soit 200 exécutions du scénario. L'oracle fixe les nombres de polls et de
  destructions depuis cet ordre d'événements, indépendamment des flags ready.
- Deux vrais workers réutilisent les états 200 fois, alternativement avec
  attente de la fin de l'enfant à l'intérieur du poll et retour immédiat de
  Pending. Chaque résultat vaut 42, chaque état est libéré une seule fois et
  les anciens tickets sont refusés.

Les tests utilisent Clang C11/pthread, avertissements fatals, UBSan fatal.
Résultats exécutés :

- Sélection initiale O2 : 21 méthodes, 16,267 s, réussite
  (`validation/await-notifications-initial-o2.log`).
- Sélection ciblée finale avec file et réveils : 12 méthodes réussies à O2
  en 14,580 s et à O0 en 11,256 s
  (`validation/await-notifications-final-o2.log`, `…-final-o0.log`).
- Le test concurrent a été ajouté ensuite : les trois méthodes spécifiques
  passent à O2 (`validation/await-notifications-concurrent-o2.log`) et O0
  (`validation/await-notifications-concurrent-o0.log`).

Les sélections se recouvrent. Elles ne mesurent pas une couverture générale
des programmes ni des ordonnancements.

## Mutations

Sept fautes détectées par des assertions comportementales : ticket racine non
transmis, inscription supprimée, notification supprimée, Pending changé en
Yield, sommeil dans l'intervalle de publication, fin publiée trop tôt et
entrée de soumission non associée. Journal :
`validation/await-notifications-corrected-mutations-o2.log`.

La première campagne modifiait `TASK_RUNTIME` pour la transmission du ticket,
alors que le compilateur assemble `TASK_RUNTIME_BODY`. Sa survie était une
mutation non exercée par le programme généré. Le script modifie désormais le
corps et reconstruit la constante du harnais ; la faute est détectée sans
changer l'oracle. Les journaux initiaux sont conservés.

Les six mutations de file et les six mutations de frontière native sont
également détectées après adaptation des ancres aux nouvelles fonctions :
`validation/await-notifications-queue-mutations-o2.log` et
`validation/await-notifications-native-mutations-o2.log`.
Les timeouts et erreurs de compilation ne comptent pas comme détection dans
la nouvelle campagne.

## Régressions et limites

Les campagnes élargies ont terminé avec succès : 275 méthodes async en
553,965 s (`validation/await-notifications-async-o2.log`) et 311 méthodes natives
en 293,694 s (`validation/await-notifications-native-o2.log`). Elles précèdent
la correction d'association d'entrée et le dernier test concurrent, couverts
par les passages ciblés finaux. Les deux sélections se recouvrent.
Le cycle de validation de cette étape est terminé ; le modèle async complet
et l'objectif global ne le sont pas.

Pas de nouvelle validation ASan/TSan, de deuxième compilateur C ou de preuve
formelle. Les tickets ne peuvent pas survivre au contexte qui porte leur entrée.
Le runner dédié conserve sa boucle de poll pour ses propres attentes ; ce lot
élimine la remise en file permanente des attentes sur workers coopératifs.
Le scheduler public, Select, les gardes de mutex et les formes générales de
captures/résultats restent des travaux distincts de l'objectif global.

Le prochain écart d'API est matérialisé dans
`validation/open-public-handle.crust` : deux fonctions async différentes rendent
Int et transmettent leurs handles à un même auxiliaire qui reçoit
`runtime::Handle<Int>`. Les deux entrées check/compile refusent actuellement
`type runtime non pris en charge : Handle`
(`validation/open-public-handle.log`). La règle du brouillon 04 impose ce type
public ; les signatures historiques `Execution<fonction>` ne suffisent pas.
