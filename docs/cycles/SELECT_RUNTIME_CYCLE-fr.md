[English](SELECT_RUNTIME_CYCLE.md)

# SL1 / RT2 — Mécanisme interne de sélection et réveils par branche

## Portée et règles

Application de SL1 du brouillon 04, AS8–AS10, RT2/RT4 et L1/L2.
Aucune sémantique normative n'est modifiée. Ce lot fournit le mécanisme C
interne ; **`runtime::select` n'est pas encore raccordé au langage source**.
Il ne constitue donc pas une validation des programmes Select par le
vérificateur, ni une clôture du chantier async.

Le lot suivant, [nettoyages aux suspensions](SUSPENDED_CLEANUP_CYCLE.md), fournit
les callbacks générés pour les formes qu'il exerce. Les limites et preuves
ci-dessous décrivent l'état du présent lot lors de son exécution.

## Implémentation

`TASK_SELECT_RUNTIME` dans `async_runtime.py` possède les descripteurs de
branches, mémorise la gagnante et permet une seule extraction du résultat.
Les descripteurs sont fournis par l'état appelant : pas d'allocation heap
dans le mécanisme de sélection. Le nombre de branches est fixé par ce stockage.

Le premier poll rend toutes les branches éligibles. Les suivants ne pollent
que les branches prêtes, dans l'ordre d'écriture, et s'arrêtent au premier
résultat. Yield réarme la branche concernée. Une notification de branche ne
réarme pas ses voisines. Les perdantes restent possédées après extraction ;
leur destruction est effectuée seulement au drop de Select. Une branche
jamais pollée suit son nettoyage inactif.

Une entrée persistante de branche conserve désormais un ticket `forward`
vers l'appelante. Son propre ticket reste la cible des notifications des
attentes qu'elle effectue. Les réveils marquent donc la bonne branche puis
remontent vers le poll englobant, y compris dans une sélection imbriquée.
Le verrou d'une entrée est libéré avant de notifier la suivante. Aucun
pointeur de frame n'est conservé entre ces notifications. Les liens forment
l'arbre des états possédés ; construire un graphe cyclique par du C arbitraire
est hors contrat de cette interface interne.

La sélection d'un résultat détache les routes des branches : les notifications
retardées ne relancent pas une perdante. Le drop révoque les routes avant
toute libération. Les générations des entrées empêchent un ancien ticket
de réveiller une nouvelle instance dans le même emplacement. La durée de vie
des entrées doit dépasser celle de tous les producteurs de tickets.

Les opérations sur un même Select sont exclusives. Les producteurs de réveils
peuvent être concurrents ; ils ne peuvent poller ou détruire ses branches.
Le scheduler garde son protocole existant d'un seul poll actif de l'appelante.

## Nettoyage suspendu et frontière d'intégration

La libération générée actuelle contient le nettoyage de l'instance inactive
et les nettoyages de terminaison. Elle ne décrit pas encore tous les états
intermédiaires atteints à yield/await : il faut générer ces nettoyages avant
de rendre Select disponible dans le langage.

Chaque descripteur de branche du mécanisme interne exige donc explicitement
un callback de destruction suspendue. Il n'existe aucun repli silencieux
vers le destructeur inactif. Les sondes manuelles fournissent ces callbacks.
Le test de vraies frames générées utilise uniquement deux corps dont le seul
état possédé est une capture transférée ; pour le corps suspendu choisi,
le nettoyage de cette capture est encore celui de l'entrée. Son adaptateur
n'est pas présenté comme valable pour un corps général ou un pool local.

Une autre composition requiert un arbitrage : une perdante peut avoir lancé
une tâche et attendre son handle. Le programme et les choix sont consignés
dans [SELECT_LAUNCHED_HANDLE_DECISION.md](../SELECT_LAUNCHED_HANDLE_DECISION.md).
Aucun join caché ni restriction de langage supplémentaire n'est introduit ici.

## Scénarios et oracles

Sept méthodes de `tests/test_select_runtime.py` :

- Modèle Python indépendant : trois scripts de branches, 80 scénarios,
  graine 8112026, 3 280 opérations. Comparaison des branches réellement pollées,
  du gagnant, de la réponse aux réveils et de la rétention avant destruction.
- Nettoyage dans quatre situations : inactif, Pending, résultat non extrait,
  résultat extrait. Destructeur suspendu distinct, ordre inverse des branches
  indépendantes, aucune double extraction ou libération.
- Réveil synchronisé pendant le poll d'une branche : 24 tours, trois workers,
  64 notifications regroupées. Deux polls de l'appelante et de la branche
  réveillée, un seul de sa voisine ; la perdante reste vivante jusqu'au drop.
- Sélections imbriquées : réveils reçus droite puis gauche, priorité conservée
  à gauche ; seule la chaîne concernée reprend et les nettoyages s'emboîtent.
- Producteur concurrent de tickets pendant détachement, libération réelle
  des frames du harnais et réemploi des trois mêmes entrées : 16 tours,
  5 000 paires de notifications tardives par tour ; les remplaçantes restent
  suspendues. Le malloc/free appartient uniquement à ce harnais de retrait.
- Fin d'une tâche lancée : son abonnement réveille la bonne branche puis
  l'appelante. La branche gagnante consomme son enfant avant d'être détruite.
  Ce test ne détruit pas une perdante possédant un handle actif.
- Deux vraies frames générées, capture `A<Int>` de chaque côté, gagnante extraite
  à adresse identique, perdante retenue, réemploi de son slot seulement après
  drop, huit tours et contrôle de toutes les traces de destruction.

Les refus vérifiés ici sont des préconditions/transitions de l'interface C
(double extraction et tickets périmés), pas des diagnostics du compilateur
sur des programmes Select incorrects. Ces derniers restent à raccorder.

## Exécutions

Harnais Clang C11, pthread, Wall/Wextra/Werror, UBSan fatal, O0/O2.
Journaux dans `validation/` :

- `select-runtime-initial-o0.log` : cinq méthodes, quatre réussies ; débordement
  signé du compteur de traces du harnais au fil des tours. Le compteur est
  désormais remis à zéro entre les tours. Aucun changement du runtime ni
  de la règle pour corriger cet oracle.
- `select-runtime-final-o0.log` : six méthodes, 1,955 s, OK.
- `select-runtime-complete-o0.log` : sept méthodes finales, 2,532 s, OK.
- `select-runtime-complete-o2.log` : sept méthodes finales, 2,732 s, OK.
- `select-runtime-regression-o2.log` : 22 méthodes, 12,405 s, OK, avec les
  six premiers tests Select, la file prête, les réveils et spawn_blocking.
- `select-runtime-await-native-o2.log` : 26 méthodes, 25,266 s, OK, couvrant
  les notifications d'attente, les blocs natifs et les handles empruntés publics.
- `select-runtime-mutations-o2.log` : baseline de six méthodes, 2,531 s, OK ;
  sept mutations détectées par assertions à l'exécution : poll sans réveil,
  ordre inversé, destruction trop tôt des perdantes, notification du parent
  perdue, route de perdante conservée, génération ignorée, destructeur suspendu
  omis. Les mutations modifient uniquement les chaînes C dans des processus
  séparés ; les oracles sont inchangés.
- Compilation Python des modules du lot réussie.
- `select-runtime-open-source.log` : le programme d'arbitrage est refusé
  par le parseur sur `runtime::select` (`attendu ';', reçu ':'`, ligne 19).
  Ce refus confirme l'absence de raccordement source ; il ne vérifie pas
  l'obligation de handle décrite par l'exemple.

Les sélections se recouvrent ; leurs méthodes ne sont pas à additionner en
programmes distincts. Le septième test a été ajouté après la campagne de
mutations et la sélection de 22 méthodes ; il est dans les deux passes finales.

## Limites

Pas de preuve formelle de concurrence ni nouvelle preuve ASan/TSan. Les modèles
finis et les entrelacements synchronisés n'épuisent pas les ordonnancements.
Pas de mesure de performance ni de deuxième compilateur C.

Restent : syntaxe/typage de Select, contrats et exigences de durée des perdantes,
nettoyage général à chaque suspension, comptage des états retenus dans les
capacités, résultats de tous types, branches avec mutex et obligations de
handles. Le remplacement public du scheduler reste également ouvert. Le lot
est une étape de l'implémentation, pas la réalisation de toutes les règles.
