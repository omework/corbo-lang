[English](ASYNC_DESIGN_CYCLE.md)

# Cycle de consignation — async et multithread

Date : 4 novembre 2026.

## Demande et portée

Consigner toutes les décisions validées pour async/multithread et le retrait de
reset, sans implémenter. La demande porte uniquement sur la documentation.
Les consignes AGENTS et VALIDATION_GUIDELINES ont été lues ; les nouvelles règles
ne sont pas présentées comme vérifiées. Aucun compilateur, runtime, test ou exemple
exécutable n'est modifié. Ce rapport n'est pas un cycle de validation exécutable
achevé au sens des critères des guidelines.

## Documents produits ou mis à jour

- ASYNC_MULTITHREAD_RULES.md : 32 identifiants normatifs AS1–AS16, RT1–RT7,
  MT1–MT8 et PR1, exemples de conception et questions reportées.
- LANGUAGE_RULES.md : rattachement de l'extension, priorité des décisions récentes,
  distinction conception/implémentation et statut historique de A5.
- README.md et RESET.md : avertissements sur le périmètre réellement implémenté
  et la migration de reset encore à effectuer.
- VERIFICATION_MATRIX.md : nouvelles obligations et scénarios, tous au statut N.

## Interactions recensées, sans preuve d'exécution

Les captures et résultats suivent les règles de transfert, provenance, emprunt,
dernière utilisation, frontière enfant → parent et absence de promotion implicite.
La terminaison d'une tâche n'est pas la fin d'un emprunt rendu dans son résultat.
Les états stables permettent des emprunts locaux à travers une suspension, sous
réserve de terminer les enfants avant la destruction des cibles. Les contrats
doivent distinguer création inactive, lancement et attente, et propager les
dépendances des handles sans réanalyser les corps appelés.

Contre-exemples de conception à convertir ultérieurement en tests :

1. Créer deux tâches capturant &mut vers la même cible, puis les attendre
   successivement : captures déjà incompatibles, refus attendu.
2. Retourner un handle empruntant une allocation locale : la source/cible
   disparaît avant le join de l'appelant, refus attendu.
3. Sortir après le premier join par un bras Err alors qu'un second enfant
   emprunte encore une donnée locale : refus attendu sur ce chemin.
4. Détruire un handle au lieu d'attendre puis fermer le bloc de la cible :
   aucune terminaison établie, refus attendu.
5. Détruire une cible après join mais avant l'usage d'un résultat emprunté,
   y compris enveloppé dans Result : refus attendu.
6. Reprendre une tâche sur un autre thread en déplaçant son état alors qu'une
   référence vers cet état existe : violation de l'adresse stable.
7. Libérer simultanément deux slots du même pool sans protéger ses métadonnées :
   défaut runtime potentiel, même avec allocations utilisateur disjointes.

Ces points ne sont pas des défauts observés dans un compilateur async : aucun
support async implémenté n'a été évalué ici.

## Décisions remplacées et limites

Les anciennes propositions monothread, async main, @type, annotations de
scheduler, contexte de construction obligatoire, await immédiat et annulation
ne sont pas conservées. `spawn` crée un nouveau thread selon la dernière
clarification, et ne signifie pas seulement soumettre à un worker existant.
Le scheduler est fourni par défaut et remplaçable par l'API du runtime.

L'installation avant le premier lancement était une proposition non explicitement
arbitrée séparément ; aucune restriction définitive supplémentaire n'est ajoutée.
JoinError, select, variantes de spawn, protocoles du scheduler et des pools
concurrents, capacités, contrats externes et grammaire des types générés restent
ouverts. La fermeture après abandon des handles et le sort des résultats non
récupérés doivent être précisés sans réintroduire une annulation implicite.

Le retrait de reset ne doit pas être traité comme une simple suppression de
tests : les futurs tests doivent vérifier le rejet de cette API et conserver les
interactions pertinentes via drop et sorties de scopes. Les anciennes preuves
restent historiques et ne prouvent aucune propriété multithread.

## Exécutions et limites des preuves

- Documentation lue et liens/inventaire contrôlés par une vérification locale
  de cohérence documentaire : 32 identifiants normatifs uniques, correspondance
  avec 32 lignes de matrice au statut N, 144 liens locaux vers des fichiers
  existants et délimiteurs de blocs de code équilibrés dans les six documents
  concernés. Ce contrôle ne vérifie ni les ancres Markdown ni la sémantique
  des snippets.
- Programmes compilés ou exécutés : aucun.
- Nouveaux cas acceptés/refusés observés : aucun ; ceux de ce rapport sont prévus.
- Tests de régression, modèles indépendants, génération, mutations, sanitizers :
  non exécutés dans cette passe documentaire.
- Aucune preuve formelle, aucune revendication de sûreté globale.

Une future passe d'implémentation devra suivre le processus global des guidelines,
mettre à jour cette matrice et produire ses propres résultats reproductibles.

## AS1 — Analyse syntaxique des suspensions

Le parseur produit des nœuds distincts pour `async fn`, `yield;`
et `.await`. Il reconnaît l’attente sur un nom et sur un appel,
dans une expression ou dans une instruction. La lecture d’un corps
asynchrone ne modifie pas le contexte de la fonction suivante.
`async fn main` est refusé.

Les deux tests ciblés d’AS1 passent. Ils vérifient l’AST, quatre
refus de suspension en contexte synchrone et le diagnostic de
`main`. Le scénario natif synchrone principal passe aussi. Désactiver
le contrôle de contexte fait accepter les quatre cas interdits.
Aucun C asynchrone n’a été exécuté. La vérification des captures,
les états de reprise et le runtime restent ouverts.

## AS9, AS10, AS14 et RT2 — Transitions C d’une instance

Le runtime C dispose d’un en-tête commun et de callbacks de reprise,
d’extraction et de nettoyage. La reprise réserve l’instance par
transition atomique. L’extraction d’un résultat terminé appelle le
nettoyage après avoir remis le résultat. Une instance inactive peut
être nettoyée sans exécuter son corps.

L’oracle C indépendant du compilateur passe sous Clang C11, `-O2`,
pthread et UBSan fatal. Il suspend une première reprise sur un thread,
provoque une tentative concurrente depuis un autre, puis reprend sur
ce second thread à la même adresse. Il vérifie le refus du nettoyage
d’une tâche démarrée, le nettoyage unique de l’instance inactive et
l’extraction unique du résultat. Inverser extraction et nettoyage
fait échouer l’oracle. L’en-tête doit rester valide tant qu’un appelant
peut encore utiliser son pointeur. Le scheduler, les pools et la
génération des états restent à intégrer.

## AS7 et MT7 — Slots stables des pools d’états

Le runtime C peut recevoir un tableau d’états de taille fixe et
un inventaire atomique des slots. Les acquisitions concurrentes
réservent des slots distincts. Le ticket d’une allocation contient
sa génération. Après réemploi, l’ancien ticket ne donne plus accès
au slot et ne peut pas le libérer.

Les deux oracles C passent sous Clang C11, `-O2`, pthread et UBSan fatal.
Le nouvel oracle remplit un pool de capacité deux avec deux threads,
récupère un résultat, réutilise son emplacement puis termine l’autre
tâche. Il vérifie les deux résultats et l’inventaire final vide.
Réinitialiser la génération à zéro à chaque libération fait
échouer le contrôle des anciens tickets.

Le pool prend son stockage du code appelant. La génération des
tableaux typés, du super pool et du scheduler reste ouverte.

## AS1, AS6 et AS8 — Génération des premiers états de reprise

Le compilateur vérifie les corps async linéaires avec captures `Int`
et résultat `Int` ou `Void`, puis génère un type C par fonction.
Les captures et variables scalaires sont stockées dans l’état.
Le code de reprise utilise un point enregistré avant chaque `yield;`
et la fabrique initialise une instance inactive dans un slot fourni.

Les quatre tests async passent. L’oracle du C généré crée deux
instances de fonctions de même signature mais de tailles différentes.
Il vérifie la création inactive, deux reprises avec état persistant,
les résultats `10` et `4`, le nettoyage et le réemploi d’un slot.
Les vérifications natives utilisent Clang C11, pthread et UBSan
fatal. Réinitialiser le point de reprise au premier état fait
échouer la seconde suspension. Les signatures de captures
empruntées ou transférées, les appels async dans Crust, le super
pool automatique et le scheduler restent à intégrer.

## AS7 et RT2 — Super pool généré

Le compilateur génère un tableau d’états et un inventaire de slots
distincts pour chaque définition async. Le contexte initialise les
pools avant l’entrée synchrone. Chaque fabrique choisit son pool.
La fermeture vérifie que les slots ont tous été rendus.

Les cinq tests async passent. L’oracle du C généré remplit deux
pools de capacité un avec des types d’état différents, exécute
les reprises, puis réutilise un slot. Un second oracle vérifie
le diagnostic de fermeture avec un slot vivant. Les essais
utilisent Clang C11, pthread et UBSan fatal. Rediriger la deuxième
fabrique vers le premier pool produit un échec de capacité.

La capacité provisoire est de seize slots par définition et peut
être surchargée à la compilation C. Le dimensionnement final,
les appels depuis Crust et l’attente des tâches au moment de la
fermeture restent ouverts.

## AS2 et AS14 — Création et destruction d’une instance inactive

Un appel Crust à une fonction async scalaire crée une instance
inactive dans le pool généré. Les arguments `Int` sont évalués
de gauche à droite puis capturés. Le corps reste inactif.
Le receveur local est non Copy. `drop` rend le slot et la fin
de scope rend aussi les slots des tâches restantes, avec diagnostic.

Les six tests async passent sous Clang C11, pthread et UBSan fatal
pour les exécutions natives. Le nouveau scénario affiche `1, 2, 3,
4, 7` sans afficher de valeur issue du corps async. Trois créations
successives réutilisent un pool de capacité un. Le vérificateur
refuse la copie et le second drop. Supprimer la restitution du slot
fait échouer la deuxième création. Les transferts de tâches,
les captures non Copy, l’attente et le scheduler restent ouverts.
La suite complète a été relancée avec arrêt au premier échec.

## AS3, AS4 et AS8 — Attente d’une instance inactive

Dans un corps async linéaire, `.await` peut consommer une
instance nommée ou créer puis attendre l’instance d’un appel.
Le parent conserve le pointeur de l’enfant et ses arguments
déjà évalués dans son état. Si l’enfant cède la main, le parent
se suspend. À sa prochaine reprise, il reprend le même enfant,
extrait le résultat et rend le slot avant de continuer.

Les sept tests async passent. L’oracle du C généré provoque
trois suspensions du parent, observe les deux exécutions enfants
dans l’ordre et obtient `15` après une attente Void. Le scénario
fonctionne avec une capacité de un par pool et le vérificateur
refuse une seconde attente de la même tâche. Réinitialiser le
point de reprise provoque une recréation et un échec de capacité.
Le C est exécuté sous Clang C11, pthread et UBSan fatal.

Le lancement depuis le main synchrone, les captures non Copy et
les transferts de tâches entre scopes ou fonctions restent ouverts.

## RT4 et RT5 — Lancement sur un nouveau thread et join natif

Le runtime C réserve l’instance inactive avant de créer un thread.
Le thread reprend la tâche jusqu’à sa terminaison. Le join attend
le thread, extrait le résultat et nettoie l’instance. Si le
système refuse de créer le thread, le runtime détruit l’instance
encore inactive. Un échec système du join qui ne prouve pas la
terminaison entraîne un arrêt fatal.

Les neuf tests async passent sous Clang C11, pthread et UBSan
fatal pour les exécutions natives. Deux tâches actives tournent
sur deux threads distincts de l’appelant et l’oracle vérifie
la reprise, la remise unique et le nettoyage de chacune.
Un autre oracle force l’échec de pthread_create et observe une
destruction sans reprise. Supprimer ce nettoyage fait échouer
l’oracle. La syntaxe Crust de spawn et join, le type de résultat
public et les handles abandonnés restent à intégrer.

## RT1, RT4 et RT5 — Spawn et join depuis le main synchrone

Le code Crust peut lancer une tâche scalaire nommée avec
`runtime::spawn(-> tache)` et consommer son handle avec
`join()`. Le résultat Int ou Void est accessible par `Ok`.
Une création de thread refusée produit la branche opaque `Err(_)`
après nettoyage de l’instance inactive.

Les dix tests async passent sous Clang C11, pthread et UBSan
fatal pour les exécutions natives. L’essai intégré affiche `9`,
ou `99` dans la branche d’erreur avec pthread_create simulé.
Le cas Void et le refus d’un second join sont vérifiés. Transformer
l’erreur en succès fait échouer le test de branche. La CLI
`run` a également exécuté le scénario Int.

À ce stade, le vérificateur exige un join avant la sortie du
scope du handle. Le suivi des handles abandonnés, l’attente
asynchrone de handles et les captures non Copy restent ouverts.

## RT7 — Handles abandonnés et fermeture du contexte

Le drop et la fin du scope d’un handle scalaire placent son
exécution dans un registre du contexte synchrone. Ils n’attendent
pas le thread. La fermeture attend les exécutions enregistrées,
écarte leurs résultats Int/Void et rend leurs slots avant de
vérifier la fermeture du super pool.

Les onze tests async passent sous Clang C11, pthread et UBSan
fatal pour les exécutions natives. Le scénario Crust observe
les sorties des deux tâches abandonnées, l’une par drop et
l’autre par fin de bloc. Dans l’oracle indépendant, le thread
attend un signal envoyé après l’abandon. L’appelant peut envoyer
le signal, puis le nettoyage se produit à la fermeture.
Supprimer l’attente de fermeture fait échouer le contrôle des
slots vivants.

Les slots abandonnés restent réservés jusqu’à la fermeture.
Les captures empruntées ou transférées et les résultats
abandonnés non scalaires restent ouverts.

## AS3 — Transfert explicite d’une tâche inactive entre scopes

Une instance inactive peut être reçue avec `<- tâche` et entrer
dans un scope enfant avec `tâche ->;`. Elle peut revenir à son
receveur d’origine à la sortie, ou sortir avec un nouveau receveur
par expression de bloc. La liaison précédente est invalidée.
Le transfert ne recrée pas l’état et garde le même slot. Dans un
corps async linéaire, une liaison déplacée peut être attendue.

Les douze tests async passent sous Clang C11, pthread et UBSan fatal
pour les exécutions natives. Le nouveau scénario monte une tâche,
la réimporte et la restitue, puis la renomme avant spawn et join
dans un pool de capacité un. Il affiche `8` sans avertissement
et refuse les usages des anciens receveurs. Omettre l’invalidation
fait échouer le contrôle d’unicité. Les signatures de tâches et les
captures empruntées ou transférées restent ouvertes.

## AS2, AS13–AS15 et MT2–MT3 — Captures partagées directes

Une tâche créée depuis du code synchrone peut capturer un `&Int`
direct. Son état conserve le pointeur et le vérificateur réserve la
cible jusqu’au nettoyage de l’instance inactive ou au join de son
exécution. Une instance transférée vers le parent conserve cette
réservation. Le mode historique refuse également un reset du pool
de la cible pendant la capture.

Les 14 tests async passent avec Clang 20.1.3, C11, `-O2`, pthread
et UBSan fatal pour les exécutions natives. Le scénario positif
combine un transfert enfant → parent, deux threads, un yield par
tâche et des lectures simultanément autorisées chez l’appelant.
Les cas négatifs couvrent l’écriture, le drop et l’emprunt mutable
avant spawn et après le premier join, ainsi que la fuite d’une cible
locale et la perte d’un handle emprunteur. Les variantes de nettoyage
inactif explicite et implicite autorisent toutes deux la mutation
après la sortie du bloc.

Deux mutations exécutées dans des copies temporaires ont été
détectées. Retirer la rétention de la capture lors du spawn autorise
des accès incompatibles après le premier join. Retirer la réservation
indépendante de la dernière utilisation autorise notamment une
écriture avant le nettoyage d’une instance inactive jamais utilisée.
Le scénario natif attend une trace fixe et les conflits statiques
sont contrôlés avec des variantes minimales. Le cycle n’ajoute pas de
modèle de concurrence, et UBSan ne vérifie pas les races.

La suite de référence précédant ces changements a exécuté 1 358 tests
avec succès. La suite complète après changement a été lancée.
Les réemprunts issus d’une capacité mutable, les captures transférées,
les appels avec emprunt entre tâches et les résultats empruntés
restent ouverts. Le prototype exige actuellement un join explicite
pour les handles à capture locale dans les formes prises en charge.

## AS2, AS15–AS16 et MT1 — Capture mutable directe

Une tâche créée depuis du code synchrone peut capturer `&mut n`
pour un Int. Le mode exclusif reste attaché à la capture quand
l’instance remonte au parent, puis quand spawn remet la réservation
au handle. Les tests couvrent la lecture et l’écriture après join,
ainsi que la lecture, l’écriture, le drop et la deuxième capture
refusés avant spawn et avant join. Un argument suivant ne peut ni
lire ni emprunter en partage la cible d’une capture mutable préparée.

Les 15 tests async passent. Le scénario natif compile avec Clang
20.1.3, C11, `-O2`, pthread et UBSan fatal. La cible initiale vaut 10,
puis 15 après le join réussi et 21 après une écriture de l’appelant.
Elle vaut encore 10 après échec simulé de pthread_create et après
drop de l’instance inactive. Traiter la capture mutable comme une
capture partagée dans une copie temporaire fait échouer les deux
variantes de lecture prématurée. Aucun modèle de concurrence ni
détecteur de races n’a été exécuté pour cette passe.

Les réemprunts mutables, les paramètres capturés depuis une autre
tâche et les résultats qui prolongent la réservation restent ouverts.
La suite complète lancée lors du cycle précédent est toujours suivie.

## AS2, AS15 et MT1 — Réemprunt d’un Int capturé

Le passage par nom d’un `&mut Int` ordinaire et le réemprunt
explicite `&mut *vue` conservent l’ascendance de la référence.
Une tâche qui reçoit une vue partagée issue de cet accès exclusif
réserve aussi la capacité d’origine. Le vérificateur traite les
réservations du handle comme actives indépendamment de sa dernière
utilisation textuelle.

Les 16 tests async passent avec Clang C11, `-O2`, pthread et UBSan
fatal pour les exécutions natives. Trois variantes remontent une
tâche au parent puis la lancent. Les deux formes mutables écrivent
13 dans l’Int initialisé à 10. La forme partagée lit 10. Les trois
autorisent à nouveau la référence après join et refusent toute
lecture prématurée par la référence ou par la liaison de l’Int.
Une quatrième exécution réutilise la référence après drop de la
tâche inactive. Les deux mutations testées sont détectées. Oublier
l’ascendance au spawn produit une double réservation dans le
vérificateur. Dégrader la réservation issue d’un parent mutable
autorise une lecture prématurée.

Les 99 tests synchrones ciblés sur les emprunts mutables avaient
réussi sur la passe précédente. Le présent cycle ne couvre pas les
parents projetés ni les emprunts retournés par les tâches. Aucun
modèle de concurrence ni détecteur de races n’a été exécuté.

## AS2, AS10, AS13–AS14 et MT8 — Capture transférée d’un Int

Une tâche accepte un `-> Int` depuis le code synchrone. Le receveur
initial devient immédiatement inutilisable. Le pointeur conserve son
adresse et la tâche suit statiquement le pool d’origine lors du
transfert de l’instance. Le callback de nettoyage détruit les captures
transférées dans l’ordre inverse de réception avant de rendre le slot
de la tâche. Pour le lancement par thread dans ce périmètre, ce
nettoyage s’exécute chez l’appelant au join ou en cas d’échec de
création. Les métadonnées du pool de données restent ainsi manipulées
sur le thread appelant.

Les exécutions Clang C11, pthread, `-O2` et UBSan fatal réallouent
dans un pool de capacité un après drop inactif, join réussi et échec
simulé de pthread_create. La destruction observe 10 sans exécution et
11 après le yield suivi de la mutation. Le vérificateur refuse la
lecture de l’ancienne liaison, la sortie de tâche avec un pool local,
la perte du handle et le reset historique de la source capturée.
Supprimer le nettoyage généré dans une copie temporaire est détecté
par le diagnostic d’épuisement du pool lors de la réallocation.

Le drop explicite de la capture depuis le worker, le retour par
transfert, les captures possédant des champs et la manipulation
concurrente des métadonnées des pools de données restent ouverts.
Aucun modèle de concurrence ni détecteur de races n’a été exécuté.

## AS10 et MT7 — Drop dans un worker et métadonnées de slots

Un corps async linéaire peut exécuter `drop(-> n)` sur une capture
`-> Int`. Le vérificateur refuse la lecture et le second drop après
cette instruction. Le C remet le slot au pool sur le thread du
worker et désarme le nettoyage final de cette capture.

Le C multithread protège l’allocation et la libération des slots de
données par un mutex global. Le calcul de réservation du curseur et
son utilisation sont dans la même section critique. Les destructeurs
imbriqués s’exécutent avant le verrouillage de la restitution du slot
courant. Les accès aux valeurs restent soumis aux emprunts de Crust.

Les 18 tests async passent avec Clang C11, `-O2`, pthread et UBSan
fatal. Un programme Crust combine le drop de la capture et
l’allocation et le drop d’un autre Int dans le même pool chez
l’appelant. La trace montre une seule destruction de la capture.
Un oracle C démarre quatre threads ensemble dans un pool de quatre
slots et exécute 4 000 cycles par thread. Il vérifie la valeur de
chaque cellule détenue et l’état final vide du curseur et de l’index.
Dans une copie temporaire sans verrou, le stress détecte un accès
via un pointeur nul dans la restitution d’un slot.

Les régions et vecteurs partagés entre tâches restent ouverts. Le
stress observe certaines interleavings et aucun détecteur de races
n’a été exécuté pour ce cycle.

Les 16 tests de régression de reset historique passent également.

## AS2, AS4, AS15 et MT4 — Captures entre tâches linéaires

Une tâche peut créer une instance enfant en lui transférant ou
en lui prêtant un Int qu’elle a capturé. Les réservations sont
actives pendant l’évaluation des arguments suivants et survivent
au renommage de l’instance et au yield du parent. L’attente ou la
destruction de l’instance inactive termine ses réservations. Une
écriture dont le membre droit se suspend vérifie de nouveau le
receveur après évaluation.

Les 19 tests async passent sous Clang C11, `-O2`, pthread et UBSan
fatal pour les exécutions natives. Le scénario assemble une attente
en argument, un réemprunt mutable, un renommage, un yield, un join
externe et un transfert à un deuxième enfant. Il affiche 24 puis
7 et détruit l’allocation d’origine une fois. La variante avec drop
avant démarrage affiche 20 puis 7. Les contre-exemples refusent un
accès avant la fin du réemprunt, un emprunt concurrent dans un
argument suspendu et la lecture ou l’écriture d’une cible transférée.
Le retrait du désarmement du pointeur transféré et la suppression
de réservation par égalité plutôt que par identité sont détectés
dans des copies temporaires.

La suite complète du cycle précédent a terminé avec 1 366 tests
réussis. Une nouvelle suite complète est lancée. Le spawn d’un
enfant sur son propre thread depuis async, les emprunts de locaux
scalaires du parent, les résultats empruntés et les corps async
avec contrôle de flux général restent ouverts.

## AS9 et MT4 — Emprunts de variables locales d’un parent async

Les captures empruntées Int du backend async pointent maintenant
directement sur le contenu Int. Une tâche peut donc emprunter
l’emplacement d’un scalaire local dans l’état stable du parent,
comme le contenu d’un Int alloué dans un pool. Un accès partagé
utilise un pointeur C vers une valeur const. Les transferts
d’allocations continuent à transporter le pointeur Cell.

Le scénario natif suspend parent et enfant, fait modifier un Int
local par l’enfant, puis fait lire la valeur par deux enfants
qui partagent l’emplacement. L’appelant peut lire en présence de
ces emprunts partagés, et une mutation après la première attente
reste refusée jusqu’à la seconde. La variante qui emprunte un
temporaire copié à la place du champ produit 41 au lieu de 45
et est détectée. Les emprunts mutables de liaisons immutables
et les lectures sous emprunt exclusif sont refusés.

Cette passe couvre les enfants attendus directement par `.await`.
Le lancement d’un enfant sur un autre thread depuis async et
les résultats empruntés restent ouverts.

Les 20 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives. La suite complète du cycle précédent est toujours en cours.

## RT4–RT5 et MT4 — Spawn et attente dans un corps async

Un corps async linéaire peut lancer une tâche inactive avec
`runtime::spawn(-> t)` puis attendre son handle avec `h.await`.
Le worker détaché publie la disponibilité après son dernier accès
au handle. Avant cette publication, le parent suspend son exécution
sans appeler pthread_join. Après publication, il extrait le résultat
et nettoie l’enfant avant de lever les réservations. Une erreur
de création détruit la tâche inactive et fournit Err.

Les variantes natives couvrent un résultat Int reçu puis lu par
match, un résultat Void attendu directement dans un match et
l’échec simulé de la création du worker enfant. Une barrière dans
l’oracle C vérifie que le worker s’exécute sur un autre thread et
que le premier essai de récupération rend la main avant qu’il puisse
terminer. Supprimer le test de disponibilité dans une copie
temporaire déclenche un arrêt lors d’une extraction prématurée.
Le vérificateur refuse la lecture sous emprunt, la seconde attente
et la sortie du parent avec handle actif.

Cette passe exige que les handles créés dans un corps async linéaire
soient attendus avant sa sortie, car ils sont stockés dans l’état
du parent. Les handles détachables de cet état, les résultats
non scalaires et les bras de match avec suspension restent ouverts.

Les 21 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal. La suite complète du cycle précédent est toujours en cours.

## AS4 et MT3 — Reprise dans un bras de match de handle

Le compilateur génère une table de reprise qui saute directement
à l’instruction suspendue. Un bras choisi avant la suspension
reprend au même endroit, avec ses variables scalaires conservées
dans l’état. Les bras produisant un Int peuvent contenir des
liaisons scalaires, des yield et des attentes. Le vérificateur
analyse les deux chemins à partir du même état et exige que leurs
obligations de nettoyage concordent à la jonction.

Le scénario natif couvre les bras Ok et Err avec un échec de
lancement simulé. Les deux bras exécutent yield puis consomment
la même tâche qui se suspend deux fois. Les résultats attendus
sont 8 et 95. Supprimer l’attente dans un seul bras est refusé,
tout comme tenter de réutiliser la tâche après le match. Le retrait
du contrôle de jonction dans une copie temporaire rend le premier
contre-exemple compilable et fait échouer le test.

Les branches avec retour anticipé, les obligations différentes
mais prouvées sûres par chemin et le contrôle de flux async général
restent ouverts.

Les 22 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives. La suite complète lancée au cycle des captures imbriquées reste en cours.

## MT3 — Retour anticipé avec preuve de terminaison par chemin

Un match de handle peut terminer un bras par un retour anticipé.
Le retour vérifie les handles encore actifs sur ce chemin après
évaluation de sa valeur. Seuls les bras continuants contribuent
à l’état de jonction. Un match instruction peut également se
terminer dans chacun de ses bras.

Le scénario lance deux enfants qui empruntent des locaux distincts.
Il donne 21 en cas de succès, et 114 quand le lancement du premier
enfant attendu échoue alors que l’autre a démarré. Le bras Err
attend ce second enfant avant le retour. Le retrait de cette
attente provoque un refus statique. Une mutation qui supprime
le contrôle des handles actifs rend le contre-exemple compilable.
La variante match instruction affiche 7 puis 14.

Les handles dans les contrats, les boucles async, les matchs
instructions imbriqués et les états de jonction distincts sur
des chemins continuants restent ouverts.

Les 23 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## AS1 et MT3 — Conditions suspendables

Les corps async acceptent if comme instruction ou comme expression
Int, avec comparaisons Int et conditions littérales. L’opérande
gauche est évalué et sauvegardé avant l’opérande droit. Les
branches utilisent la même vérification que les matchs de handle.
Un retour vérifie les obligations de son chemin et laisse le chemin
continuant déterminer l’état après la jonction.

Le scénario compare un scalaire à un résultat qui se suspend puis
modifie ce même scalaire. Il exécute les deux branches, avec yield,
affectation dans un if imbriqué et retour anticipé. Les résultats
attendus sont 10 et 89. Supprimer la sauvegarde de l’opérande gauche
dans une copie temporaire produit 89 dans les deux cas. Le
vérificateur refuse aussi un accès concurrent et l’attente d’une
tâche dans une seule branche continuante.

Les conditions composées et les boucles async restent ouvertes.

Les 24 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## AS1 et B4a — Conditions à court-circuit

Les conditions async composées emploient la même reprise que les
expressions if. Le C produit un branchement avant l’évaluation
de l’opérande droit. L’attente éventuelle reprend dans la branche
qui l’a démarrée. La jonction statique couvre aussi le chemin
qui saute cet opérande.

Le test natif combine `||` et `&&` avec une tâche qui se suspend
puis modifie un scalaire local. Trois entrées donnent 10, 17 et 0,
ce qui distingue les deux courts-circuits et le chemin qui évalue
l’attente. Inverser les branches des expressions logiques dans
une copie temporaire donne 17, 10 et 10. Le vérificateur refuse
aussi le cas où un court-circuit laisserait une tâche nommée
consommée sur un seul chemin.

La suite complète du cycle des captures imbriquées a terminé
avec 1 371 tests réussis. La suite complète incluant les récents
changements de contrôle de flux est lancée. Les boucles async
et les jonctions entre obligations différentes restent ouvertes.

Les 25 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## AS1, S4–S5a et MT3 — Boucles suspendables

Les corps async acceptent while et loop, ainsi que loop produisant
un Int par break. Le test de while peut se suspendre et s’exécute
à nouveau après continue. La reprise d’un yield ou d’une attente
dans le corps revient à l’instruction suspendue. Les tâches inactives
créées dans l’itération sont nettoyées à sa fin, sur break et sur
continue, avec l’avertissement de nettoyage implicite.

Les scénarios natifs combinent un test suspendable, un yield dans
le corps et une valeur de break qui se suspend. Ils vérifient la
sortie explicite et la sortie par test faux, avec des résultats
respectifs de 16 et 26. Un pool de capacité un vérifie la restitution
du slot à chaque itération. Supprimer ce nettoyage provoque un
diagnostic d’épuisement. Le vérificateur refuse une mutation sous
emprunt, un break sans valeur dans une boucle expression et un
continue qui consomme une tâche requise à l’entrée.

Les boucles de cette passe exigent des obligations stables pour
les valeurs extérieures. Les changements d’état mémoire transportés
entre itérations, les transferts non scalaires par break et les
handles lancés dans les blocs de boucle restent ouverts.

Les 26 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## MT3–MT4 — Workers dans les blocs de boucle

Un bloc async peut lancer un worker avec une capture vers un
Int mutable de l’itération. Les liaisons de handle et leurs
résultats ont une portée lexicale. La fin du bloc, break et
continue vérifient que chaque handle sortant a été attendu.
Return conserve son contrôle de tous les handles de la tâche.
Le compilateur accepte aussi un match instruction de handle
imbriqué dans le bloc.

Le test natif lance trois workers successifs dans un pool de
capacité un et observe leurs écritures avant la réutilisation
du même emplacement de frame. Il passe par fin d’itération,
continue et break, puis affiche 18. Les variantes refusent la
mutation pendant le prêt, le double lancement et les sorties
avant attente. Une mutation qui oublie le handle et son emprunt
à la sortie du bloc rend les break et continue invalides
compilables et fait échouer le test.

Le transfert d’un handle hors de son bloc et les états de
jonction différents restent ouverts.

Les 27 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## MT5 et RT5 — Déplacement explicite des handles

En contexte synchrone, un handle peut remonter au parent par
la valeur finale d’un bloc. Il peut aussi être injecté dans
un enfant puis rendu au parent. Le C garde un seul objet
d’exécution. Le vérificateur conserve ses emprunts et ses
dépendances aux pools pendant ces déplacements. Dans un corps
async, `let déplacé = <- handle` renomme le handle sans déplacer
son emplacement dans la frame.

Le scénario synchrone remonte un handle avec une capture mutable,
le renomme, le fait traverser un autre bloc et observe la valeur 7
après le join. Le vérificateur refuse l’usage de l’ancien nom,
l’accès à la cible avant join et la sortie avec une cible locale
au bloc quitté. Omettre l’invalidation dans une copie temporaire
déclenche l’invariant d’accès direct unique. Le scénario async
teste le renommage avant .await et le refus de l’ancien nom.

Les signatures interfonctions de handles, leurs contrats et la
sortie d’un bloc async avec un handle comme résultat restent ouverts.

Les 28 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives. La suite complète du cycle de contrôle de flux est encore en cours.

## AS3, AS13 et MT5 — Sortie d’un bloc async avec tâche ou handle

Un bloc async peut fournir une tâche inactive ou un handle avec
`<- nom` comme dernière instruction sans point-virgule. Le
transfert conserve l’emplacement de l’état et les réservations.
Le contrôle enfant → parent refuse toute capture visant un
scalaire qui appartient au bloc quitté. Le nettoyage ordinaire
continue pour les autres liaisons du bloc.

Le scénario natif remonte une tâche inactive, la lance dans le
bloc parent, puis remonte le handle. Après deux suspensions et
l’attente, il affiche 14. Déplacer la déclaration de la cible
dans le bloc intérieur ou dans le bloc intermédiaire provoque
un refus à la frontière correspondante. Une lecture avant
attente est également refusée. Retirer le contrôle de durabilité
dans une copie temporaire rend les deux contre-exemples compilables.

Les contrats interfonctions, l’injection descendante explicite
dans les blocs async et le transfert par break restent ouverts.

Les 29 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives. Le test ciblé passe aussi avec un bloc instruction suspendable avant l’attente.

## AS3 et T4–T8 — Injection descendante dans les blocs async

Un bloc async peut recevoir une tâche ou un handle avec `nom ->;`
à son entrée. L’accès reste attaché à l’état d’origine et le
compilateur suit son rattachement au bloc. Une remontée marquée
avec `<- nom;` rend l’accès au parent. Un transfert final avec
un nouveau receveur invalide l’ancien accès. Sans remontée,
une tâche inactive est nettoyée. Un handle actif doit être
attendu avant de quitter le bloc dans ce périmètre.

Le scénario natif descend une tâche sur deux niveaux, la remonte
par deux transferts successifs puis injecte le handle dans un
autre bloc. Il suspend les blocs et affiche 14 après attente.
Les contre-exemples retirent une remontée, sautent un parent
ou injectent après l’entrée. La mutation qui retire le nettoyage
de la tâche importée sans retour rend son ancien nom utilisable
et fait échouer le test.

Les transferts par résultat non scalaire de boucle et les
signatures interfonctions restent ouverts.

Les 30 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## AS3, S5a, AS13 et MT5 — Tâche ou handle renvoyé par break

`break <- nom` peut fournir une tâche ou un handle créé dans une
boucle async. Toutes les sorties fournissent le même mode et le
même type de tâche. Le résultat conserve l’adresse de l’état ou du
handle, et l’analyse réunit les réservations des sorties possibles.
Une cible déclarée dans une portée quittée ne peut pas sortir
avec ce résultat.

Le scénario natif choisit entre deux enfants qui empruntent des
Int extérieurs distincts. Les variantes avec tâche inactive et
handle lancé affichent toutes deux 42 puis 52. Le vérificateur
refuse toute lecture d’une cible possible avant l’attente, le
transfert d’une cible locale à la boucle et le mélange de modes
aux break. Remplacer l’union par la dernière réservation dans
une copie temporaire rend une lecture prématurée compilable.

La suite complète précédente a réussi ses 1 377 tests. La
suite complète incluant les nouveaux transferts est lancée.
Les contrats interfonctions et les changements d’obligation
transportés d’une itération à l’autre restent ouverts.

Les 31 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## RT7 et MT3 — Abandon de handles depuis async

Un corps async peut abandonner explicitement ou en fin de bloc
un handle dont les captures sont scalaires. Le worker ne conserve
aucun pointeur vers le handle. Il publie la fin de ses accès dans
son propre slot. Le registre de fermeture protège ses insertions
concurrentes et relâche son verrou avant d’attendre un worker,
qui peut alors y inscrire un enfant.

Le test natif abandonne un parent et un enfant, puis vérifie
que la fermeture récupère les deux tâches. Un oracle C bloque
le worker, détruit son handle, envoie le signal de fin, puis
vérifie une seule restitution pendant la fermeture. Supprimer
l’inscription du worker détaché dans une copie temporaire fait
échouer le contrôle des slots vivants. Les régressions conservent
le refus d’une sortie avec des captures empruntées locales.

Les captures transférées et les résultats non scalaires des
handles abandonnés restent ouverts. Aucun détecteur de races
n’a été exécuté pour cette passe.

Les 32 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## AS11–AS12 — Retour direct d’un emprunt partagé

Une fonction async peut retourner directement un paramètre &Int.
Le compilateur déduit les paramètres effectivement retournés,
avec union pour les chemins distincts. L’attente d’une tâche
inactive remet le pointeur au parent et ne conserve que les
réservations associées au résultat. Dans le bloc principal du
parent async, elles expirent après la dernière instruction
utilisant la référence. Le résultat est copié hors de l’état
avant la récupération du slot.

Le scénario natif fait suspendre un enfant avec deux captures.
Il permet la mutation de la capture indépendante après attente,
puis celle de la cible retournée après la dernière lecture.
Il affiche 20 puis 80. Une mutation de la cible avant cette
lecture est refusée, de même qu’un retour vers un local.
Lorsque le corps peut retourner l’autre paramètre, celui-ci
reste aussi protégé. Supprimer la réservation du résultat dans
une copie temporaire rend une mutation prématurée compilable.

Les résultats mutables, la propagation par relais, les
résultats reçus dans des sous-blocs et le transport dans
Result<T, JoinError> restent ouverts. Le compilateur refuse
actuellement le spawn d’une tâche à résultat emprunté.

Les 33 tests async passent sous Clang C11, `-O2`, pthread et
UBSan fatal. La suite complète précédente s’est arrêtée après
332 tests sur une assertion historique qui exigeait encore le
refus de loop dans un corps async. Cette assertion obsolète a été
retirée. Le test ciblé de refus de suspension en contexte synchrone
passe et une nouvelle suite complète est lancée.

## AS11–AS12 — Retour d’un emprunt mutable

Une fonction async peut rendre un paramètre &mut Int par nom ou
par réemprunt explicite. La liaison du résultat mutable exige
`let mut`. Un réemprunt partagé explicitement retourné depuis
un paramètre mutable conserve la réservation exclusive d’origine.
Le retour d’un emprunt vers une variable locale reste refusé.

Le scénario natif suspend l’enfant puis le parent. La référence
reçue modifie l’Int, et l’accès d’origine observe 4 après le dernier
usage de cette référence. Les contre-exemples refusent la lecture
et l’écriture prématurées, la liaison immutable et la fuite du local.
La variante partagée conserve l’interdiction de lire par l’accès
d’origine. Dégrader la réservation du résultat en emprunt partagé
dans une copie temporaire rend ces lectures prématurées compilables.

Les relais, les résultats reçus en sous-bloc et les résultats
empruntés dans un handle restent ouverts.

Les 34 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## AS12 et S4–S5 — Résultat emprunté reçu dans un sous-bloc

Un sous-bloc async peut recevoir un &Int ou &mut Int par .await.
Les réservations suivent les usages de la liaison dans ce bloc.
Break et continue libèrent les emprunts des porteurs locaux après
évaluation de la valeur de sortie. Les porteurs restent invisibles
dans le parent. Le suivi des usages d’un porteur extérieur à
travers une instruction composée reste conservateur.

Le scénario natif utilise un pool de capacité un. Il reçoit un
emprunt par itération, l’utilise avant continue puis dans la
valeur de break, et reçoit ensuite un nouvel emprunt dans un if.
Il affiche 18. Une écriture prématurée et une lecture du porteur
hors de son bloc sont refusées. Supprimer la libération des
emprunts locaux sur l’arête de boucle fait rejeter le scénario
positif. Le premier essai de génération a révélé une collision
entre l’indice de bras et l’indice d’instruction, corrigée avant
l’exécution finale.

Le retour d’un emprunt à travers un relais async et son transport
dans un handle restent ouverts.

Les 35 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## AS11–AS12 — Relais de provenance par attente

Un relais async peut retourner directement le résultat emprunté
d’une attente ou le recevoir dans une liaison puis le retourner.
L’analyse résout les paramètres retournés par l’enfant et les
remappe vers les paramètres réels du relais. Une origine locale
ou une provenance récursive est refusée dans ce périmètre.

Le scénario natif traverse trois tâches, dont une réordonne les
paramètres. Il permet de modifier la cible qui a seulement servi
à une lecture et conserve l’exclusivité de la référence retournée.
La sortie attendue est 10 puis 27. Une lecture prématurée, une
origine locale indirecte et une provenance récursive sont refusées.
Appliquer un mauvais remappage aux deux relais s’annule dans ce
scénario. Appliqué à un seul relais dans une copie temporaire, le
défaut fait rejeter la mutation valide de la cible indépendante.

La transmission d’un résultat emprunté comme nouvelle capture
et son transport dans un handle restent ouverts.

Les 36 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## AS12 et AS15 — Capture d’un résultat emprunté

Un résultat &Int ou &mut Int peut servir de capture d’une nouvelle
tâche. L’analyse conserve la réservation du porteur et celles de
ses cibles. La réservation de l’enfant survit au dernier usage
textuel du porteur. L’inférence des relais remonte aussi cette
capture vers les paramètres d’origine.

Le scénario natif relaie un emprunt mutable puis le capture dans
un enfant. Il affiche 9 après attente, 1 si l’enfant est détruit
inactif et 11 si le parent reprend l’usage du porteur après attente.
Le vérificateur refuse la lecture prématurée de la cible, la
mutation via le porteur et une deuxième capture incompatible.
Retirer les réservations héritées dans une copie temporaire laisse
passer la lecture prématurée de la cible et fait échouer le test.

Le transfert hors du bloc d’un porteur local reste conservateur.
Le résultat emprunté enveloppé dans un handle reste ouvert.

Les 37 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## AS12 et MT6 — Emprunts dans le résultat d’un handle async

Un worker lancé depuis un corps async peut retourner &Int ou
&mut Int. Le runtime extrait le pointeur dans le champ typé du
Result avant de restituer le slot. Le vérificateur prolonge
les réservations du résultat avant match et dans Ok. Dans Err,
aucun emprunt n’a été remis. Pour un Result nommé, la jonction
rétablit les réservations possibles si le porteur doit encore
servir. Le match direct peut terminer sa réservation dans le bras.

Le scénario natif couvre une liaison Result nommée, un match
direct, les résultats partagés et mutables et un échec simulé
de lancement. Les chemins mutables affichent 16 en cas de succès
et 92 en cas d’échec. Une écriture prématurée avant match ou
dans Ok est refusée. Supprimer la réservation à la remise du
Result dans une copie temporaire laisse passer ces écritures.

Les résultats empruntés de join synchrone et les agrégats
contenant des références restent ouverts.

Les 38 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## AS12 et MT6 — Résultats empruntés de join synchrone

Le join synchrone peut fournir un Result contenant &Int ou &mut Int.
Les paramètres réellement retournés déterminent les dépendances du
Result, y compris quand un argument scalaire précède la capture.
Le match consomme le Result emprunté dans ce périmètre et transmet
la réservation au porteur de Ok. Err termine la réservation et
permet de réutiliser la cellule. Un drop explicite écarte le Result.

Le scénario Clang C11, `-O2`, pthread et UBSan fatal affiche 8 puis 8
après mutation dans Ok, 2 après échec simulé et 3 après drop du
Result. Le test couvre aussi le résultat partagé et le match direct.
Une lecture prématurée avant match ou dans Ok et un drop prématuré
de la cellule sont refusés. Dégrader le Result mutable en emprunt
partagé dans une copie temporaire laisse passer la lecture avant match.

La suite async a exécuté 39 tests avec succès. La suite complète
précédente a exécuté 1 385 tests avec succès. Une nouvelle passe
complète incluant le join emprunté est lancée. Un Result partagé
issu d’une capture exclusive est encore refusé en synchrone, et les
agrégats contenant des références restent ouverts.

## MT1 et MT6 — Résultat partagé issu d’une capture exclusive

Le join synchrone peut rendre le réemprunt partagé d’une capture
mutable. Le porteur dans Ok est en lecture seule. Le vérificateur
conserve l’ascendance exclusive du Result jusqu’au dernier usage
du porteur. Il refuse pendant cette période l’accès par la cellule
ou par la référence mutable d’origine.

Le scénario natif teste une capture directe et une capture par
référence mutable nommée. Dans les deux cas, la lecture par le
porteur et les lectures après son dernier usage donnent 1. Les
lectures prématurées et les écritures par la référence partagée
sont refusées. Omettre l’ascendance dans une copie temporaire
laisse passer une lecture prématurée.

La capture ultérieure de ce résultat depuis le code synchrone,
son retour par un contrat synchrone et les agrégats empruntés
restent ouverts.

Les 40 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## MT1 et MT6 — Recapture synchrone après join

Une référence partagée reçue par join et issue d’une capture
exclusive peut être capturée par une nouvelle tâche depuis du code
synchrone. La seconde tâche conserve l’ascendance et la réservation
effective de la cellule, y compris lorsqu’elle reste inactive
sans usage ultérieur. Si elle retourne la référence, la réservation
continue de protéger la cellule jusqu’au dernier usage du résultat.

Le scénario natif enchaîne deux workers et affiche 4 puis 5.
Le vérificateur refuse une lecture de la cellule avant le deuxième
spawn et avant le dernier usage du deuxième résultat. Il refuse
également une lecture pendant la vie d’une tâche inactive sans
usage ultérieur. Oublier l’exclusivité héritée dans une copie
temporaire laisse passer des lectures prématurées.

Le passage par un contrat synchrone et les agrégats empruntés
restent ouverts. Le suivi des captures reste conservateur quand
une même vue peut viser plusieurs cellules.

Les 41 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## AS12 et MT6 — Relais synchrone par contrat après join

Le résumé de résultat d’une fonction synchrone suit le type
de tâche, son handle et les cibles d’un résultat emprunté.
Lorsqu’un join retourne un &Int issu d’un paramètre mutable,
le contrat conserve la réservation exclusive en plus de la
provenance de la référence partagée. Un relais de fonction
transmet cette information à son appelant.

Le scénario natif fait passer la référence par deux fonctions
synchrones et affiche 3 deux fois. Le contrat du relais nomme
le paramètre dont l’exclusivité doit être conservée. La lecture
prématurée de la cellule ou de son emprunt mutable et le retour
d’une cible locale sont refusés. Retirer la restauration de la
réservation au site d’appel dans une copie temporaire laisse
passer une lecture prématurée.

Le retour interfonction d’un handle et les résultats agrégés
restent ouverts.

Les 42 tests async, les 27 tests de retours directs d’emprunt et les 28 tests d’appels modulaires passent. Les exécutions async natives utilisent Clang C11, `-O2`, pthread et UBSan fatal.

## AS3 et AS5 — Retour de tâche inactive par contrat synchrone

Une fonction synchrone peut déclarer `-> <- définition_async`
et remettre une instance inactive à son appelant. Le contrat
conserve les cibles de chaque capture et leur mode. Le backend
remet le pointeur d’état sans démarrer ni recréer la tâche.

Le scénario natif couvre un retour explicite dans un if, un
retour final implicite et un second relais synchrone. Le worker
modifie la cellule après lancement et le programme affiche 7
deux fois dans les deux variantes. Une lecture avant lancement
et le retour d’une tâche qui emprunte une cellule locale sont
refusés. Omettre les dépendances à la réception de la tâche
dans une copie temporaire laisse passer la lecture prématurée.

Ce périmètre couvre les captures scalaires et empruntées.
Le retour de tâches avec allocations transférées et les signatures
qui reçoivent une tâche ou retournent un handle restent ouverts.

Les 43 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## AS5, AS13 et MT8 — Provenance du pool d’une capture transférée

Une fonction synchrone peut retourner une tâche inactive qui
détient un Int transféré. Le contrat distingue le pool reçu
par paramètre et le pool d’une allocation reçue par transfert.
Un relais conserve cette provenance. Un pool local au callee
empêche la remise de la tâche.

Le scénario natif alloue dans un pool injecté, passe l’Int
par transfert à une deuxième fonction et reçoit la tâche.
Il affiche 4 puis 8 après join et réallocation dans un pool de
capacité un. Après drop inactif, la réallocation affiche 8.
La vérification refuse le reset historique tant que la capture
occupe le pool, l’abandon du handle et le retour avec pool local.
Omettre la source à la réception dans une copie temporaire laisse
passer le reset prématuré et fait échouer le test.

Les paramètres de type tâche et les handles renvoyés par
une fonction restent ouverts.

Les 44 tests async passent sous Clang C11, `-O2`, pthread et
UBSan fatal pour les exécutions natives. La suite complète
précédente a exécuté 1 391 tests avec succès. Une nouvelle suite
complète incluant les contrats de tâche a démarré.

## MT5 — Retour interfonction d’un handle lancé

Une fonction synchrone peut transférer son handle à l’appelant.
Le prototype emploie la notation provisoire
`-> <- Execution<définition_async>`, qui identifie le type exact
du worker. Le contrat transmet les captures et leurs pools.
Le C remet le handle par valeur, avec la même instance de tâche
et la même exécution sous-jacente.

Le scénario natif vérifie un relais synchrone, le join réussi
et l’échec simulé du lancement. Le worker mutable donne 7 puis
7 en cas de succès et 999 puis 4 en cas d’échec. Le scénario
avec capture transférée libère le slot au join et réalloue
dans un pool de capacité un. Le retour d’une cible locale,
l’accès prématuré et l’abandon du handle dépendant d’un pool
sont refusés. Omettre les dépendances reçues dans une copie
temporaire laisse passer une lecture prématurée.

La notation publique définitive des handles et les paramètres
qui reçoivent un handle restent ouverts.

Les 45 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## AS3 et MT5 — Paramètres synchrones de tâche et de handle

Une fonction synchrone peut recevoir par transfert une tâche de
type nominal async ou un handle `Execution<définition_async>`.
Le site d’appel exige -> et perd l’accès au receveur. Le callee
peut détruire la tâche, la lancer ou consommer le handle avec join.
Le C transmet le pointeur de tâche ou la valeur du handle.

Le scénario natif nettoie d’abord une instance inactive, réutilise
son slot dans un pool de capacité un, transmet la nouvelle tâche
à une fonction qui la lance puis transmet le handle à une fonction
qui joint. Il affiche 7. Les contre-exemples vérifient le refus de
la copie, de la réutilisation des deux anciens noms et d’un type
nominal différent. Omettre l’invalidation au transfert dans une
copie temporaire déclenche l’invariant de rattachement au scope.

Les signatures de cette passe portent sur les définitions à
captures scalaires et à résultat Int ou Void. Les paramètres de
tâche ou de handle qui transportent des emprunts ou des allocations
restent ouverts.

Les 46 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## AS3 et MT5 — Paramètres de tâche ou de handle avec capture détenue

Une fonction synchrone peut recevoir une tâche ou un handle qui
détient un Int transféré. Le contrat qui relaie la valeur conserve
les pools de ses captures via le paramètre de tâche ou de handle.
Le callee qui joint l’exécution consomme le handle et rend le slot
au pool d’origine.

Le scénario natif lance la tâche, relaie le handle et le joint
dans trois fonctions. Dans un pool de capacité un, il affiche
7 puis 8 après réallocation. L’analyse refuse l’abandon du handle
et le reset historique avant join, y compris lorsqu’une fonction
reçoit aussi le même pool par emprunt mutable. Omettre les pools
du paramètre dans une copie temporaire rend un reset prématuré
compilable. Le premier essai a exposé une consommation absente
du chemin de vérification par contrat, corrigée avant validation.

Les paramètres avec captures ou résultats empruntés restent ouverts.
En mode historique, un appel qui peut réinitialiser un pool de
capture transféré est refusé de façon conservatrice.

Les 47 tests async passent sous Clang C11, `-O2`, pthread et UBSan fatal pour les exécutions natives.

## AS3, AS12 et MT5 — Emprunt transporté par un paramètre async

Les contrats synchrones identifient une capture empruntée par le paramètre
de tâche ou de handle et par la position de la capture dans la définition
async. Au site d’appel, le vérificateur résout cette origine vers les
cibles effectives. Un retour partagé provenant d’une capture mutable
conserve la réservation exclusive jusqu’au dernier usage du retour.
Le changement conserve la notation expérimentale de type nominal des
cycles précédents.

Le scénario natif transfère une tâche inactive, lance puis relaie le
handle, joint la tâche et retourne la référence via deux fonctions. Il
affiche 7 puis 8 après mutation de la cible. Le vérificateur refuse la
lecture prématurée avant le join et après le join avant le dernier usage,
ainsi que les deux ordres de passage d’un alias incompatible. Le reset
historique du pool de capture est refusé avec un pool de secours distinct.
Une copie temporaire du compilateur qui omet la réservation au retour
accepte la lecture prématurée après join. Le test détecte ce défaut.

Les 48 tests async passent. L’oracle natif utilise Clang C11, -O2,
pthread et UBSan fatal. La suite complète du cycle précédent a terminé
avec 1 396 tests réussis. Une nouvelle suite complète est en cours.
Le cycle exerce des captures
Int et un résultat &Int. Les projections, résultats agrégés et les
compositions interfonction plus générales restent à examiner.

## RT2–RT4 — Lancement et attente derrière une interface C commune

Les lancements depuis une fonction synchrone et depuis une tâche async
utilisent une interface C interne commune. Le scheduler pthread par
défaut fournit le lancement de nouveaux threads et l’attente des
threads joignables. Le runtime conserve le callback d’attente associé
au lancement jusque dans le registre des handles abandonnés. Le callback
de lancement signale un échec sans démarrer la tâche, ce qui laisse au
runtime la responsabilité du nettoyage.

Un oracle natif injecte des callbacks instrumentés et vérifie join,
attente suspendable, drainage des deux catégories de worker et échec
d’un lancement détaché. Il vérifie que l’abandon ne déclenche pas une
attente et que l’extraction et la libération ne s’exécutent qu’une fois.
Dans une copie temporaire du runtime, substituer directement l’attente
pthread au callback lors du drainage déclenche l’assertion de l’oracle.

L’interface interne conserve les identifiants de thread pthread.
RT3 valide le principe d’un remplacement explicite et laisse le
protocole d’installation ouvert. Le point d’entrée Crust
`runtime::set_scheduler` et la politique de reprise restent ouverts.

Les 49 tests async passent. Les oracles natifs s’exécutent avec Clang
C11, -O2, pthread et UBSan fatal. L’essai ASan est non concluant sur
cet hôte : l’oracle a dépassé son délai, puis un binaire témoin qui
retourne immédiatement et l’oracle ont tous deux dépassé le délai
avec la même instrumentation.

## S5 et MT3 — Sorties de boucle distinctes des reprises

Un contre-exemple compilait le worker mais rejetait son attente dans
une boucle suivie d’un break. Le vérificateur exigeait l’état d’entrée
sur ce chemin, alors que l’attente avait consommé le handle et levé
la réservation. Après nettoyage des scopes quittés, break enregistre
désormais l’état de sortie. Le test faux de while fournit également
une sortie. Les reprises continuent d’exiger l’état d’entrée.

L’oracle exerce deux chemins de break avec attente du même worker
et pool de tâches de capacité un. Le parent peut ensuite modifier
la cible et affiche 8 sur chacun des deux chemins. Le vérificateur
refuse un break sans attente lorsqu’une autre sortie a consommé le
handle, le while qui peut éviter l’attente, une seconde attente
après la boucle et la mutation avant la première attente. Rétablir
l’état d’entrée à la sortie dans une copie temporaire reproduit le
refus erroné et fait échouer le test.

La jonction async exige encore le même état sur toutes les sorties
continuantes. L’analyse par union des obligations et les reprises
qui nécessitent un point fixe plus général restent ouvertes.

Le cas avec résultat de boucle Int passe également. Supprimer la
comparaison des sorties dans une copie temporaire laisse compiler
le chemin sans attente. Les 50 tests async passent sous Clang C11,
-O2, pthread et UBSan fatal pour le C. La variante avec résultat
ajoutée ensuite a été rejouée individuellement sous les mêmes options.

## T2, T4, T5 et AS3 — Consommation explicite au bon niveau

Le compilateur async acceptait trois formes de consommation qui
contournaient le rattachement au scope : renommage par <-, lancement
par spawn et destruction explicite. Il vérifie maintenant le scope
courant avant ces opérations. Les chemins d’attente conservent leur
traitement distinct. Les nettoyages implicites utilisent toujours
leurs points d’entrée internes.

Le scénario natif descend explicitement des tâches et des handles
avant de les consommer. Les deux tâches détruites avant démarrage
restent inactives et les trois tâches lancées affichent 3, 4 et 5.
Le vérificateur refuse l’omission de chacun des cinq transferts,
ainsi que le saut d’un niveau supplémentaire. Supprimer le contrôle
de portée de spawn dans une copie temporaire laisse passer ce cas
et fait échouer le test.

Contre-exemple restant pour L3. Dans un corps async, créer
`first = hold(-> a)`, puis `second = hold(-> b)`, et renommer
`let renamed = <- first;`. À la fin du corps, le C affiche
`destroy a=1` puis `destroy b=2`. L’ordre attendu est b puis a.
Le nettoyage suit actuellement l’ordre d’insertion des noms.
La récupération physique des slots reste distincte de cette trace.

Les 83 régressions synchrones des boucles du cycle précédent ont
terminé avec succès.

Les 51 tests async passent sous Clang C11, -O2, pthread et UBSan
fatal pour les exécutions du C généré.

## L3 et T2 — Ordre de destruction conservé au renommage async

Le compilateur suit l’ordre des entrées de destruction par scope.
Un renommage garde sa position, même lorsque le nom a été importé
du parent. Un groupe importé conserve l’ordre relatif du parent.
Le même parcours inverse s’applique à la fermeture normale du bloc,
aux sorties de boucle et au retour de la fonction. Les handles sans
dépendances restent enregistrés pour le drainage sans join caché.

L’oracle vérifie six traces natives : fin de fonction, retour
explicite, fin de bloc, retour imbriqué, import suivi d’une création
locale et break. Chaque trace détruit b avant a, ne lance pas les
tâches inactives et permet deux nouvelles allocations dans le pool
de capacité deux. Dans une copie temporaire, remettre le renommage
à la fin de l’ordre fait échouer les six traces.

Un second contre-exemple reste ouvert. Après création de first
puis second, la séquence `{ first ->; <- first; }` reçoit first
à nouveau dans le parent. La trace actuelle détruit second puis
first. La nouvelle réception devrait rendre first prioritaire.

Les 52 tests async passent sous Clang C11, -O2, pthread et UBSan fatal.
La suite complète du cycle des paramètres empruntés continue.

## L3, T8 et T9 — Nouvelle entrée pour un import retourné au parent

Lorsqu’un import est marqué pour retour, le bilan du bloc le
réinscrit à la fin de l’ordre de réception du parent. Les imports
renvoyés ensemble conservent leur ordre relatif. Le compilateur
sauvegarde l’ordre des noms vivants avec l’état des réservations
pour chaque chemin. Un bras qui termine la fonction ne fournit
pas d’ordre à la continuation. Une reprise de boucle exige encore
le même état qu’à l’entrée, ordre compris.

L’oracle suit les destructeurs après retour d’un import depuis un
bloc, depuis un break et depuis deux branches compatibles. Il
exerce aussi un bras qui retourne de la fonction, avec l’ordre
initial restauré après l’analyse de l’autre bras. Dans chaque
exécution le pool peut réallouer après le join. Deux chemins qui
imposent des ordres incompatibles sont refusés, ainsi qu’une
reprise qui les modifie.

L’ordre est suivi pour les tâches et handles gérés par cet
abaissement async. La jonction générale d’obligations différentes
reste ouverte.

Supprimer la réinscription dans une copie temporaire inverse à
nouveau les traces et rend compilables des branches incompatibles.
L’oracle détecte les deux écarts.

Les 53 tests async passent sous Clang C11, -O2, pthread et UBSan
fatal pour le C. La suite complète de cette révision est lancée.

## AS10 et AS12 — Allocation Int reçue par attente directe

Une tâche peut retourner une allocation Int par `return <- nom;`.
Le C extrait le pointeur original et désarme la destruction dans
l’état sortant. Une liaison recevant le résultat d’une tâche
inactive par .await prend en charge la destruction dans son scope.
Le receveur peut muter avec let mut, réemprunter, détruire ou
retourner l’allocation par transfert. Le pool d’origine reste
associé à la même cellule.

L’oracle natif vérifie deux relais, une suspension après réception
et le nettoyage sur retour, fin de bloc et drop explicite. Il
vérifie l’égalité des adresses, l’impossibilité d’allouer dans le
pool plein tant que le résultat est vivant et le réemploi du même
slot après destruction. Le vérificateur refuse la copie implicite
au retour, l’attente sans receveur, le drop sous emprunt et la
réutilisation d’un accès déplacé. Une mutation qui laisse l’ancienne
tâche détruire la cellule déclenche un accès invalide sous UBSan.

Le sous-ensemble couvre les allocations Int issues des captures.
Le résultat transféré via un handle lancé et les autres types
restent ouverts. Le compilateur refuse spawn pour ce résultat tant
que son transport par Result n’est pas disponible.

Les 54 tests async passent sous Clang C11, -O2, pthread et UBSan
fatal. Les variantes de fin de bloc et de drop explicite ont aussi
été rejouées individuellement. La suite complète du cycle des
paramètres empruntés a terminé avec 1 400 tests réussis. La suite
du cycle de l’ordre de réception est encore en cours.

## AS10 et RT5 — Allocation Int dans le résultat d’un handle async

Le C récupère le pointeur du worker dans le Result d’un handle
attendu par .await. Le bras Ok reçoit la responsabilité de
nettoyer la cellule, y compris lorsque le motif est Ok(_).
Un Result nommé peut survivre à une suspension. Son match le
consomme et sa destruction explicite ou implicite nettoie un
payload encore présent. Le chemin Err après échec du lancement
ne contient aucune allocation. Le handle garde l’obligation
d’attente tant que sa tâche est susceptible de détenir la capture.

L’oracle exerce la réception directe et nommée, la suspension,
le joker, le nettoyage du Result sans match et l’échec simulé du
lancement du worker détaché. La destruction intervient une fois
et le pool de capacité un peut réallouer ensuite. Le vérificateur
refuse l’abandon du handle, la lecture après destruction et le
match d’un Result déjà détruit. Omettre l’inscription du payload
dans l’ordre de nettoyage épuise le pool dans une copie temporaire.

Ce cycle couvre .await dans un corps async. Le join bloquant avec
allocation et le transfert d’un Result nommé entre receveurs
restent ouverts.

Une deuxième mutation retire l’inscription du Result nommé.
Le scénario sans match épuise alors le pool et détecte la fuite.

Le match utilisé comme expression scalaire a aussi été exécuté.
Il extrait le scalaire avant la destruction de la cellule du bras.

Les 55 tests async passent avec les oracles C sous Clang C11,
-O2, pthread et UBSan fatal. La suite complète du cycle de
l’ordre de réception est toujours en cours.

## AS10, AS12 et RT5 — Allocation Int remise par join bloquant

Le runtime extrait le pointeur de la cellule dans le Result
après le join pthread. Le vérificateur conserve les pools
possibles de la capture dans ce Result et arme son nettoyage
sur Ok uniquement. Le match consomme le Result. Le bras Ok
prend en charge la cellule, y compris avec le joker, et le
bras Err ne reçoit aucune allocation. Le Result nommé peut
aussi être détruit explicitement ou à la fin de son bloc.
Le pool ne peut pas être réinitialisé via l’ancien profil
pendant qu’un Result vivant y retient une cellule.

Les oracles couvrent succès, échec de lancement, match direct
et nommé, joker, destruction explicite ou implicite et remise
à une fonction synchrone. Le pool de capacité un réutilise le
slot après nettoyage. L’oracle C vérifie l’identité du pointeur
et l’occupation du slot jusqu’au drop. Supprimer l’extraction
implicite du joker dans une copie temporaire épuise le pool.
La copie du Result et son usage après drop sont refusés.

Ce cycle suit l’union des sources des captures transférées.
La restitution de l’allocation par le contrat d’une fonction
synchrone et le transfert du Result entier restent ouverts.

Les 56 tests async passent sous Clang C11, -O2, pthread et
UBSan fatal. Le cas à deux pools et le match utilisé comme
expression avec joker ont été exécutés séparément.

## AS12 et MT5 — Restitution synchrone de l’allocation extraite

Un contrat de retour d’Int alloué peut désigner une capture d’un
handle reçu. Le vérificateur résout cette origine en identités et
pools à chaque appel. Le contrat distingue cette alternative
d’une allocation reçue directement et retournée dans le bras Err.
Le code généré conserve le pointeur de la cellule.

Le test compose création du handle, join et restitution à travers
trois fonctions. Il vérifie les alternatives symboliques, les deux
chemins à l’exécution, les pools de capacité un et une allocation
créée dans un pool injecté. Le retour d’un handle capturant une
allocation d’un pool local est refusé. Retirer l’identité au
lancement ou à la réception par contrat fait échouer le test.
La première mutation a d’abord survécu au scénario avec relais,
car ce relais reconstruisait la provenance. Le scénario avec
lancement direct détecte désormais cette mutation.

La provenance du résultat couvre encore l’union des captures
transférées du worker. L’analyse du sous-ensemble effectivement
retourné et le transfert du Result entier restent ouverts.
La suite complète de l’ordre de réception a passé 1 405 tests.

Les 57 tests async passent sous Clang C11, -O2, pthread et UBSan
fatal. Le test ciblé a également vérifié qu’un callee peut détruire
la cellule via le bon pool et qu’un autre pool est refusé. La suite
complète du cycle précédent est toujours en cours.

## T2–T5 et RT5 — Déplacement du Result alloué entier

Le Result qui porte une allocation Int se déplace avec <- vers
une nouvelle liaison dans son scope. L’ancien nom devient
inutilisable et l’ordre de destruction ne change pas. Il peut
aussi être importé à l’entrée d’un bloc et retourné au parent.
Le code C synchrone conserve la variable du Result à l’échelle
de la fonction pour permettre son utilisation après la sortie du
bloc. Dans un corps async, le résultat peut aussi sortir d’une
boucle avec break <-.

Les scénarios natifs exercent le renommage, une remontée depuis
une expression bloc et un aller-retour descendant avant le match.
Le pool de capacité un réalloue après une seule destruction.
Les deux vérificateurs refusent l’utilisation de l’ancien nom
et le déplacement depuis un descendant sans import. Une mutation
qui laisse vivre l’ancien nom async provoque une double
destruction détectée par UBSan.

Les signatures synchrones transportant le Result entier et ses
sorties par boucle synchrone restent ouvertes.

Les 58 tests async passent sous Clang C11, -O2, pthread et UBSan
fatal. Deux oracles ciblés avec deux Result vivants ont aussi
confirmé la trace b puis a après renommage de a, en synchrone
et en async. La suite complète du cycle de join bloquant continue.

## S5a, L3 et RT5 — Result alloué restitué par une boucle synchrone

Un break <- transfère le Result entier vers le receveur de la
boucle. Le vérificateur désarme le nettoyage de l’itération et
reconstruit celui du receveur en conservant les identités et pools
possibles. Le nettoyage n’est armé que pour Ok. Le C place la
variable de réception dans la fonction, ce qui laisse le Result
transférable depuis un bloc englobant.

Le test exécute une reprise qui détruit un premier Result, puis
deux sorties qui remettent des allocations issues de pools de
capacité un distincts. Il vérifie les destructions et la
réallocation des deux pools. L’échec de lancement simulé rend
Err au receveur. Un break sans <-, une sortie de type incompatible
et la capture d’un pool local à un scope quitté sont refusés.
Dans une copie temporaire, conserver le nettoyage de l’itération
après le transfert provoque une double destruction détectée par
UBSan.

Les signatures synchrones transportant le Result entier et les
expressions conditionnelles qui le retournent restent ouvertes.

Les 59 tests async passent sous Clang C11, -O2, pthread et UBSan
fatal pour les oracles C. La remontée depuis un bloc englobant
et l’échec de lancement ont été rejoués individuellement.
La suite complète du cycle de join bloquant est encore en cours.

## T10, AS10 et RT5 — Result alloué sélectionné par une expression if

Chaque branche continuante transfère le Result par <-. Une
branche qui termine la fonction nettoie ses valeurs sur son
propre chemin. En synchrone, le vérificateur réunit les identités
et pools possibles puis réarme le nettoyage du receveur sur Ok.
En async, le receveur reste dans l’état stable du parent à
travers les suspensions.

Les tests natifs exercent les deux branches, le retour anticipé,
la remontée depuis un bloc englobant, l’échec de lancement et la
réallocation après nettoyage. Le scénario synchrone utilise deux
pools possibles. Celui en async vérifie que le Result reste vivant
après yield. Le vérificateur refuse un résultat sans transfert ou
incompatible, ainsi qu’un pool synchrone qui meurt avec sa branche.
Supprimer la consommation du Result sortant dans une copie
temporaire provoque une double destruction détectée par UBSan.
Un match synchrone retournant le Result a aussi été exécuté.

Les jonctions async avec obligations de nettoyage différentes
restent ouvertes, ainsi que les signatures transportant le Result
entier et le match expression async qui le restitue.

La suite complète du cycle de join bloquant a passé 1 408 tests.
Une nouvelle suite complète est lancée pour cette révision.

Les 61 tests async passent sous Clang C11, -O2, pthread et UBSan
fatal pour les oracles C.

## T10 et RT5 — Result alloué restitué par un match async

Un match expression sur un handle attendu ou sur un résultat
nommé peut remettre un Result alloué au receveur. Les bras qui
continuent transfèrent explicitement leur Result avec <-. Le
compilateur utilise le même bilan de branche que pour if.
Le receveur garde son Result dans l’état du parent pendant yield.

L’oracle emprunte les deux chemins du match en simulant l’échec
du premier lancement détaché uniquement. Les chemins affichent
7 et 8 respectivement puis réallouent dans le pool de capacité
un. Le retour anticipé détruit le Result de son bras. Le sujet
nommé survit à une suspension avant le match. Une branche qui
fournit un Int au lieu du Result transféré est refusée.
Une mutation qui omet de transmettre le mode de résultat au
bilan des branches réintroduit le refus d’un programme valide.

Les signatures transportant le Result entier et les jonctions
async avec obligations de nettoyage différentes restent ouvertes.

Les 62 tests async passent sous Clang C11, -O2, pthread et UBSan
fatal. L’ordre inversé des bras a également été rejoué séparément.
La suite complète du cycle des expressions if continue.

## T6, AS12 et RT5 — Result alloué transporté par signature synchrone

Le prototype reconnaît Result<A<Int>,JoinError> dans une signature
synchrone qui le reçoit avec -> ou le retourne avec <-. Le contrat
conserve les identités et les pools du payload éventuel. Le code
généré transmet le Result et désarme le nettoyage de l’ancien
receveur. Le nouveau receveur nettoie Ok seulement. Un retour
explicite ou une expression finale <- est accepté.

L’oracle couvre trois fonctions, une remontée depuis un bloc,
l’extraction du payload dans une fonction suivante, le drop
explicite et l’échec simulé du lancement. Le pool de capacité un
réalloue après une seule destruction. Le compilateur refuse
l’appel ou le retour sans transfert, la réutilisation de l’ancien
nom et la fuite d’un Result dont le pool est local.
Une mutation omettant l’invalidation de l’argument est détectée
par l’invariant du vérificateur sur un accès resté actif.

Les signatures async avec Result propriétaire et les Result
contenant un autre type d’allocation restent ouverts.

Les 63 tests async passent sous Clang C11, -O2, pthread et UBSan
fatal. Les variantes d’expression finale, d’extraction avec
retour et de pool local ont aussi été rejouées individuellement.
Les régressions synchrones de contrats et la suite complète du
cycle des expressions if sont encore en cours.

## T6, AS2, AS10 et RT5 — Result alloué dans une signature async

Une tâche peut recevoir un Result<A<Int>,JoinError> par transfert
et le restituer avec <-. Son état conserve le Result à travers
yield. L’attente directe récupère le Result métier. En cas de
retour ou de capture par une autre tâche, le pointeur du champ
d’origine est désarmé. Les captures encore présentes sont
détruites en ordre inverse après extraction du résultat, y
compris quand l’état mêle allocations et Result.

Les oracles couvrent la capture depuis des corps synchrones et
async, l’attente directe, l’échec de lancement du premier worker,
le drop de l’instance inactive et l’ordre inverse des captures
mixtes. Le pool de capacité un réalloue après nettoyage. Le
vérificateur refuse la capture et le retour implicites ainsi que
l’usage d’un nom déplacé. Omettre le désarmement au retour
provoque une double destruction sous UBSan dans une copie
temporaire du compilateur.

Le transport de Result<Result<A<Int>,JoinError>,JoinError>
via un handle lancé reste ouvert. Le compilateur refuse spawn
pour les tâches dont le type de résultat exigerait ce transport.
Les 27 tests synchrones de contrats du cycle précédent passent.

Un premier passage a signalé un changement de libellé dans le
diagnostic de capture incompatible. Le libellé précédent a été
conservé et le test concerné est repassé. Le C d’une définition
utilisant cette signature sans aucun spawn a aussi été compilé
et exécuté.

Les 64 tests async de la révision finale passent sous Clang C11,
-O2, pthread et UBSan fatal. La suite complète du cycle des
expressions if continue.

## RT5, RT6 et AS10 — Résultat métier imbriqué dans un handle

Un worker peut retourner Result<A<Int>,JoinError> par transfert.
Après lancement, join ou await transporte ce Result métier
dans le Result externe du handle. Le runtime conserve deux
statuts distincts. Le Result extérieur ne porte une cellule
à détruire que si les deux statuts valent Ok. Le match externe
consomme son receveur et remet le Result intérieur au bras Ok.
Le Result extérieur peut être déplacé et transféré entre blocs.

Les oracles exercent Ok(Ok), Ok(Err) et Err en synchrone et en
async. Ils simulent séparément l’échec du premier ou du second
lancement, puis vérifient le joker, le drop explicite et la
réallocation dans un pool de capacité un. Ils refusent le match
après drop et l’abandon du handle propriétaire. Supprimer le
test du statut intérieur provoque un accès à une cellule nulle
sous UBSan dans une copie temporaire du compilateur.

Ce cycle couvre cette imbrication précise. Les signatures et
les expressions de contrôle qui restituent le Result extérieur,
ainsi que les autres types d’erreur métier, restent ouverts.
La suite complète du cycle if a passé 1 413 tests.

L’oracle ciblé de la révision finale passe aussi à -O0 avec
UBSan fatal, en plus de -O2. La suite complète de cette
révision est lancée.

Les 65 tests async de la révision finale passent sous Clang C11,
-O2, pthread et UBSan fatal.

## S5a et T10 — Result imbriqué restitué par branche ou boucle

Le Result extérieur se transfère par <- depuis if et match,
ou par break <- depuis une boucle. Le C conserve ses deux
statuts et désarme le nettoyage dans le scope quitté. Le
receveur synchrone réarme le nettoyage seulement si les deux
statuts valent Ok. En async, les branches doivent fournir
le même niveau d’imbrication et les deux statuts restent
dans l’état du receveur.

Le scénario natif exerce if, match et loop dans les deux
contextes. Il vérifie la réutilisation du pool après une seule
destruction. Une branche qui fournit un Int est refusée.
Dans une copie temporaire, laisser l’itération synchrone
nettoyer le Result déjà transmis provoque une double
destruction détectée par UBSan.

Les signatures transportant le Result extérieur et les
imbrications plus générales restent ouvertes.

Les 65 tests async passent sous Clang C11, -O2, pthread et
UBSan fatal. Le scénario match a été ajouté puis rejoué
individuellement sous les mêmes options. La suite complète
du cycle des résultats imbriqués reste en cours.

## T6, AS2, AS12 et RT6 — Result imbriqué transporté par signature

Le type Result<Result<A<Int>,JoinError>,JoinError> est accepté
par transfert dans les signatures synchrones et async. Le
contrat synchrone conserve les pools et les identités possibles.
Le C transmet les deux statuts. Le retour async par attente
directe désarme le champ d’origine et transmet l’état au receveur
après suspension. Une tâche inactive qui détient cette capture
peut la détruire dans son callback de nettoyage.

Les oracles exercent les trois issues après passage dans une
fonction synchrone et après capture et retour async. Le pool de
capacité un réalloue après une seule destruction. Ils vérifient
également le drop d’une tâche inactive créée depuis le code
synchrone. Le compilateur refuse l’appel sans transfert.
Une mutation qui remplace le statut externe par Ok après la
copie du Result async fait diverger le scénario d’échec.

Le modèle C couvre deux niveaux de Result. Le lancement
d’une tâche dont le retour en produirait un troisième est
refusé. Les autres formes de Result métier restent ouvertes.

Les 66 tests async passent sous Clang C11, -O2, pthread et UBSan
fatal. Le scénario de drop inactif ajouté ensuite a aussi été
rejoué individuellement. La suite complète du cycle des résultats
imbriqués reste en cours.

## AS12 et MT5 — Provenances distinctes avant et après join

Les contrats suivent séparément les captures vivantes d’une tâche
et les allocations que le résultat peut transporter. Le compilateur
déduit le sous-ensemble lorsqu’il peut relier chaque retour direct
à un paramètre transféré. Les autres formes conservent l’ensemble
des captures propriétaires. Les fonctions qui créent ou relaient
un handle transmettent les deux ensembles indépendamment.

Le scénario natif transmet deux allocations issues de pools
distincts. Avant join le vérificateur protège les deux pools.
Après join, le profil historique permet de réinitialiser le pool
de l’allocation détruite par le worker. Il refuse toujours de
réinitialiser le pool de la cellule retournée. Si une autre branche
peut retourner la seconde allocation, son pool reste protégé.
L’appel à un callee qui détruit via le bon pool passe et un
autre pool est refusé. Une mutation qui remet toutes les captures
dans le résultat fait refuser le scénario valide.

L’inférence précise à travers les liaisons intermédiaires du
corps async reste ouverte. La suite complète du cycle des
résultats imbriqués continue.

La jonction de branches synchrones effaçait aussi les provenances
d’un handle relayé. Une copie temporaire qui reproduit cette perte
accepte un reset avant join pour un worker à résultat scalaire.
Le test minimal ajouté refuse désormais ce programme. Les deux
ensembles restent présents après une jonction sans effet.

Les 67 tests async ont passé sous Clang C11, -O2, pthread et
UBSan fatal avant la dernière correction de jonction. Les
scénarios ciblés de contrat et de reset sont passés avec cette
correction. La suite async de la révision finale est en cours.

## AS12 et MT5 — Provenance propagée dans les relais async

L’analyse retrouve les captures propriétaires qui atteignent un
retour via des liaisons locales. Elle remonte les appels attendus,
y compris quand la tâche est nommée, déplacée ou lancée. La
position de la capture dans le callee est appliquée à la liste
d’arguments du caller. Si une origine reste inconnue, le contrat
garde toutes les captures propriétaires possibles.

Le test natif compose trois définitions async, une permutation
d’arguments et une suspension après réception. Une variante
lance le relais sur un worker et retourne le Result imbriqué.
Dans les deux cas, le pool de la capture détruite peut être
réinitialisé dans le profil historique. Permuter le résultat vers
l’autre pool fait refuser ce reset. Une mutation qui prend
systématiquement le premier argument laisse passer le reset
interdit et est détectée par le test.

Les expressions de bloc et de boucle qui transportent des
provenances non résolues restent analysées de façon conservatrice.
La suite complète du cycle des résultats imbriqués a passé
1 417 tests. La suite async finale du cycle précédent a passé
67 tests.

Les deux variantes ciblées passent sous Clang C11, -O2, pthread
et UBSan fatal. La suite complète de cette révision est lancée.

Les 68 tests async passent sous Clang C11, -O2, pthread et UBSan
fatal. La variante avec lancement du relais a également été
rejouée individuellement.

## AS12, S5a et T10 — Provenance des résultats de bloc et de contrôle async

L’analyse suit les résultats à travers les blocs, if, match et
loop. Elle réunit les origines de chaque branche continuante
et de chaque break de la boucle concernée. Les sorties qui
terminent la fonction contribuent directement au contrat.
Si une expression échappe à l’analyse, le contrat conserve
toutes les captures propriétaires possibles.

Le scénario natif exerce les quatre formes avec un Result
retourné par le worker. Après join, le profil historique peut
réinitialiser le pool de la capture détruite. Il refuse ce reset
si une autre branche ou un autre break peut retourner la cellule
de ce pool. Une copie temporaire qui ignore la seconde branche
accepte à tort le reset. Le test détecte cette mutation.

Les 69 tests async passent sous Clang C11, -O2, pthread et
UBSan fatal. Les deux tests ciblés ont été rejoués après
l’ajout du repli conservateur pour les chemins imbriqués
dans des expressions inconnues. La suite complète du cycle
des relais reste en cours.

## RT7, AS8 et MT7 — Réutilisation des slots de workers abandonnés

Avec un pool de capacité un, abandonner un handle scalaire épuisait
le pool jusqu’à la fermeture du contexte, même après la fin du worker.
Le worker publie désormais la fin de ses accès au slot par une
écriture atomique release. Avant une création de tâche, le runtime
lit cet indicateur avec acquire et retire du registre synchronisé les
entrées récupérables. Pour un worker joignable, le scheduler pthread
par défaut détache le handle natif. Le résultat scalaire est ensuite
consommé et le slot libéré. La fermeture attend les entrées restantes,
dont les workers joignables des schedulers sans callback de détachement.

Les 70 tests async ont passé sous Clang C11, -O2, pthread et UBSan
fatal. Les trois tests ciblés ont également passé après ajout des
assertions sur le worker bloqué et sur le scheduler sans détachement.
L’oracle sur le C généré réutilise le même slot 32 fois en alternant
les lancements joignables et détachés. Sans l’appel de récupération
dans la fabrique, il échoue avec `task pool capacity exceeded`.
Sans la vérification de publication du worker, le test d’abandon
échoue sur un abort. Les mutations ont été exécutées sur des copies
temporaires distinctes.

La récupération est déclenchée par une création de tâche et
n’attend pas qu’un worker actif libère son slot. Une allocation
concurrente peut encore rencontrer une saturation transitoire.
Les oracles ne couvrent pas tous les entrelacements et ce cycle
n’a pas exécuté de détecteur de races ni ajouté de modèle indépendant.
La suite globale de cette révision a été lancée.

### Récupérateurs concurrents et instrumentation

L’oracle RT7 a passé sous UBSan avec une seconde phase de 32 cycles.
Dans chaque cycle, quatre threads tentent de retirer la même entrée
achevée. Après leurs joins, le registre et le pool d’états sont
vides. Les trois régressions ciblant le drainage imbriqué, la
réutilisation concurrente des états et celle des pools de données
ont également passé.

Sous ASan et UBSan combinés, les trois oracles RT7 dépassent le
délai de dix secondes. Un programme C témoin dont main renvoie
simplement zéro dépasse lui aussi le délai sous ASan, avec et sans
`detect_leaks=0`. Cette exécution ne fournit donc pas de résultat
ASan exploitable sur Crust dans cet environnement. Les tests
concurrents sous UBSan ne couvrent pas systématiquement les
entrelacements.

## RT6, AS14 et MT1 — Deux captures détenues sur échec de lancement

L’oracle exécute le même worker avec deux allocations issues de pools
distincts de capacité un et un emprunt mutable. Il couvre le join
synchrone et l’attente d’un worker lancé dans un corps async.
Pour chaque mode, le succès modifie la cible empruntée. Sur
`EAGAIN`, la cible garde sa valeur d’origine et le résultat
prend le bras Err. Dans les quatre exécutions sous UBSan, les deux
allocations sont détruites une fois et les deux slots réutilisés.
L’accès à la cible avant l’attente est refusé dans les deux modes.

Deux mutations sur des copies temporaires détectent une perte
de nettoyage. Omettre la libération de la première capture dans
le code généré fait échouer les chemins normaux. Omettre le drop
de la tâche inactive sur échec de lancement laisse les chemins
normaux passer, puis épuise un pool de données sur les deux
chemins Err. Aucun nouveau modèle indépendant. Les variantes
de JoinError restent reportées. La suite async actualisée est
en cours.

## AS5, AS12, MT5 et ST13 — Capture partagée détachée relayée

Une tâche créée depuis `&*v.target`, avec `target: &Int`, peut
être renvoyée par deux fonctions synchrones. Le contrat substitue
la cible extérieure du champ au porteur. Le receveur peut
détruire et réutiliser le porteur avant le spawn. Si le worker
retourne le même emprunt, le résultat protège encore la cible.
L’ascendance de la capacité est contrôlée comme à la création
directe. La capture d’un champ Int inline reste ouverte.

Sous UBSan fatal, le cas normal restitue la référence et
l’échec de lancement simulé donne Err. Mutation, drop et reset
prématurés sont refusés avant join et dans le bras Ok. Un
retour capturant la cible d’un pool local est également refusé.
Omettre la substitution du champ dans une copie temporaire
fait réserver le porteur à tort et bloque sa destruction.
Les tests ciblés passent. La suite async précédente termine
avec 71 tests réussis. Aucun nouveau modèle indépendant.

### Réaffectation du champ après capture et avant retour

Le contrat détaché nomme le champ d’entrée. Résoudre ce nom
après l’application des effets de l’appel protégeait la nouvelle
cible à la place de la cible capturée. Les chemins opaque et
de génération C résolvent maintenant les origines détachées
avant d’appliquer la mutation du porteur. Les contrôles de
durabilité utilisent ensuite les cibles ainsi conservées.

Le test exécute cinq cas sous UBSan. Avec capture avant mise
à jour, seul l’ancien Int reste réservé après le drop du
porteur. Avec capture après mise à jour conditionnelle, les
deux cibles possibles restent protégées. Drop et reset
prématurés sont refusés sur les chemins concernés.
Une copie temporaire qui résout de nouveau après la mutation
accepte le drop de l’ancienne cible puis la réutilisation de
son slot. Le worker lit alors 42 dans le slot recyclé au lieu
du 5 capturé. Le compilateur corrigé refuse ce drop.

La suite async de la révision précédente passe avec 72 tests.
La suite globale du cycle de récupération des slots passe
avec 1 422 tests. La suite async de cette révision est lancée.

### Handle lancé avant la réaffectation du porteur

La régression couvre aussi une fonction qui lance le worker,
réaffecte le champ puis retourne son `Execution<read>`. Un
second contrat relaie ce handle. Sous UBSan, le succès lit
l’ancienne cible et l’échec de lancement simulé renvoie Err.
Le programme valide détruit la nouvelle cible après le porteur
et avant le join. Drop suivi de recyclage et reset de l’ancienne
cible sont refusés. Dans la copie qui résout la provenance
après mutation, le vérificateur accepte le recyclage avec le
handle encore actif. Aucun modèle indépendant supplémentaire.

### Relais du résultat emprunté après join

Une fonction crée le worker avec l’ancienne cible d’un champ,
réaffecte ce champ puis joint le worker. Elle retourne la cible
capturée sur Ok et la cible de remplacement sur Err. Après un
second relais, le contrat contient précisément les deux origines.
Le porteur est destructible avant lecture du résultat. Le C
normal lit 5 et l’échec simulé EAGAIN lit 7 sous UBSan fatal.
Le compilateur refuse le drop de chaque cible avant lecture
et accepte les deux drops après. Ce test a été exécuté séparément.
La suite async de la révision précédente passe avec 73 tests.

Le profil historique refuse encore, à la frontière d’un appel,
un reset aliasé avec une capture d’un handle transféré même si
le corps joint le handle avant le reset. Cette restriction
conservative est distincte du profil par défaut où reset est retiré.

### Porteur consommé et ascendance exclusive

La variante où les deux fonctions reçoivent le porteur par
`-> View` passe sous UBSan. Le slot du porteur est réutilisable
avant spawn. Le drop de la cible est refusé pendant l’exécution
et pendant l’utilisation du résultat emprunté.

Un écart reste reproductible si le champ partagé est construit
avec `target: &*writer` depuis un `writer = &mut a` encore utilisé
après join. Avec `let t = prepare(&v); drop(-> v);` avant spawn,
la vérification interne compte le champ partagé et la barrière
exclusive de la tâche comme deux prêts incompatibles. Modifier
le seul contrôle d’invariant laisse un deuxième refus au drop.
Le suivi de la capacité suspendue doit distinguer la barrière
envers le writer du mode partagé de la capture elle-même.

### Réservation du writer et lecture partagée du porteur

Le vérificateur distingue le mode déclaré d’une capture de la
barrière qui suspend son ancêtre mutable. Un prêt de tâche
exclusif uniquement à cause de cette barrière peut coexister
avec la lecture du champ partagé. Une vraie capture mutable
continue de bloquer la lecture. L’accès direct à la cible et
l’accès par le writer restent bloqués par la barrière.

Les deux exécutions sous UBSan couvrent succès et EAGAIN.
Le porteur est lu et détruit pendant la période du handle.
Après le dernier usage du résultat, le writer peut écrire.
Six tentatives d’accès prématuré sont refusées. La mutation
qui supprime la distinction reproduit l’erreur interne.
Le test de capture directement mutable passe aussi. Une
nouvelle capture à travers le même champ pendant un worker
reste à examiner.

### Deux workers issus du même champ partagé

La lecture par un autre emprunt partagé peut franchir la barrière
async quand le vérificateur retrouve une ascendance commune.
Le Result partagé du premier join conserve la même distinction.
Un véritable prêt mutable et les accès par le writer gardent leurs
restrictions.

Quatre exécutions UBSan croisent la seconde capture directe ou
relayée et le succès ou l’échec simulé du premier lancement.
Les lectures via les deux résultats passent. Les six accès
prématurés entre les joins sont refusés. Supprimer le traitement
du Result partagé dans une copie temporaire reproduit le faux
conflit exclusif pour les deux modes de capture. Trois tests
ciblés passent. Les suites antérieures terminent avec 75 tests
async et 1 428 tests globaux. La suite globale actualisée est
lancée. La capture directe d’un champ Int inline reste ouverte.

### Deux résultats de join nommés

L’oracle exécute également les deux joins avant de lire leurs
résultats nommés, pour une seconde capture directe et pour une
capture relayée. Les deux lectures passent sous UBSan. Entre
les lectures, bien que les deux workers aient terminé, les
six tentatives d’accès par le writer ou l’accès direct sont
refusées. L’écriture par le writer après lecture du second
résultat est observée dans les deux exécutions. La suite globale
lancée précédemment précède cette extension de l’oracle.

## AS3, AS13, MT5 et S5a — Résultat async d’une boucle synchrone

`break <-` peut rendre une tâche inactive ou un handle au
receveur d’une boucle synchrone. La sortie invalide la liaison
d’origine et désarme son nettoyage. Le receveur conserve les
captures et l’union des provenances du résultat alloué que
join pourra restituer. Les pools doivent survivre au transfert.

Quatre exécutions sous UBSan croisent tâche ou handle et les
deux sorties de boucle, avec restitution puis réemploi des
deux pools de capacité un. Les resets prématurés sont refusés
pour les deux provenances possibles dans le profil historique.
Une source locale à l’itération est refusée. Omettre l’union des
pools du résultat dans une copie temporaire fait échouer les
quatre cas sur l’invariant de provenance. La suite async est
lancée. La capture d’un champ inline reste ouverte.

## AS3, AS13 et T10 — Tâches et handles issus d’un if synchrone

Chaque branche peut transférer une tâche ou un handle vers le
receveur du if. Les deux branches continuantes doivent fournir
le même type nominal et le même mode. Le receveur conserve
l’union des sources du résultat restituable par join.

L’oracle exécute les deux branches pour une tâche inactive
et un handle déjà lancé. En succès ou EAGAIN, le slot de
l’allocation choisie est détruit une fois et les deux pools
sont réutilisables après traitement du résultat. Le profil
historique refuse le reset prématuré de chaque pool possible.
Omettre l’union des sources du résultat dans une copie temporaire
fait échouer les quatre variantes sur l’invariant de provenance.

Trois tests ciblés passent, dont les régressions du if avec
un Result alloué et de la boucle avec une tâche ou un handle.
Le refus d’un transfert sans flèche et de tâches de types
nominaux distincts a été exécuté. La suite async précédente
passe avec 77 tests.

## AS3, AS13 et T10 — Tâches et handles issus d’un match synchrone

Les bras de match d’un enum peuvent transférer une tâche ou
un handle avec `<-`. Le receveur conserve les captures et les
provenances du résultat de join pour les bras possibles. Le
match d’un Result de join, abaissé en condition, accepte aussi
un transfert de tâche depuis Ok ou Err.

Douze exécutions sous UBSan croisent les deux variantes, les
trois modes du sujet et la restitution d’une tâche ou d’un
handle. Les deux pools de capacité un sont réutilisables après
traitement du résultat. Avec les deux variantes statiquement
possibles, leurs resets prématurés sont refusés dans le profil
historique. Supprimer l’union de provenance du match dans une
copie temporaire fait échouer les douze variantes. Deux autres
exécutions couvrent le choix depuis Ok et depuis Err après un
échec de lancement simulé. Les régressions du match retournant
une paire de tranches et du retour de champ prêté passent.

## AS5, AS12 et MT5 — Contrats des tâches choisies par contrôle synchrone

Le C savait restituer une tâche ou un handle depuis if, loop
et match. L’inférence des contrats refusait encore if ou
perdait les sources des captures et du résultat. Elle conserve
maintenant leur union à travers les trois constructions.

Douze exécutions UBSan couvrent les deux sorties, tâche ou
handle, puis un relais par une seconde fonction. Le contrat
identifie exactement les deux paramètres de pool et le C
rend les deux slots réutilisables après le résultat de join.
Le profil historique refuse les resets prématurés des deux
pools possibles. Omettre les métadonnées dans la jonction
symbolique du match fait échouer les quatre variantes de
match sur l’assertion du contrat. La suite async précédente
au changement de match est passée avec 78 tests. Le test
de contrat a été exécuté séparément sur cette révision.

## AS15, MT2 et B4a — Captures et ordre des arguments

Une première capture partagée suspendant un writer conserve
son mode partagé pendant la préparation du second argument.
Deux captures du même champ avec ascendance commune sont
admises. Repasser par le writer, même pour un autre emprunt
partagé, ou demander une capture mutable reste refusé.

L’oracle exécute une tâche lisant deux fois le champ puis
réutilise le writer après join. La mutation qui omet le mode
partagé pendant la préparation reproduit le refus du cas
valide. Un autre oracle passe une tâche choisie par if, loop
ou match à une fonction synchrone. La lecture scalaire avant
l’argument de tâche passe et garde la valeur lue, tandis
qu’une lecture des cibles possibles après cet argument est
refusée. Trois tests ciblés passent sous UBSan. La suite
async du cycle précédent termine avec 80 tests.

## RT4 et B4a — Transfert d’une tâche calculée à spawn

Le parseur et les analyses conservent l’opérande du transfert.
Le backend synchrone peut lancer directement la tâche fournie
par une expression du scope courant. Dans un corps async,
l’appel direct et le résultat d’une boucle utilisent la même
consommation que la tâche nommée. La flèche reste obligatoire.

Huit exécutions sous UBSan combinent appel ou if en synchrone,
appel ou boucle en async, succès ou EAGAIN du worker enfant.
Le parent conserve sa valeur en cas d’échec et observe la
mutation après attente en cas de succès. L’accès prématuré
et l’appel sans flèche sont refusés pour les quatre formes.
Trois régressions ciblées des appels nommés, du transfert du
résultat alloué et de l’ordre des arguments passent aussi.
La suite async est relancée pour le changement d’AST.
Les autres expressions de spawn calculé en corps async,
dont le if de tâche, restent ouvertes.

## AS3, AS13, MT4 et RT4 — Tâche ou handle choisi dans un corps async

La jonction qui recevait les Result alloués reçoit aussi une
tâche ou un handle transféré depuis if ou un match de join.
Le C garde le résultat de la branche exécutée. Le vérificateur
conserve les captures et les emprunts de résultat possibles
sur les branches continuantes. Le résultat de if peut être
reçu dans une liaison ou transféré directement à spawn.

Six exécutions sous UBSan croisent deux branches, un spawn
direct, une tâche nommée et un handle déjà lancé. Le test
exerce yield dans le bras et après la jonction, puis await.
Les accès aux deux cibles avant await sont refusés, ainsi
que le transfert d’une cible locale et les types nominaux
distincts. Deux autres exécutions couvrent le match de join,
y compris Err provoqué par EAGAIN. Omettre les captures du
second bras dans une copie temporaire laisse passer six
accès prématurés. Aucun nouveau modèle indépendant.

Les quatre tests ciblés passent, dont les deux régressions
de transfert de Result alloué. La suite de la révision des
arguments calculés termine avec 83 tests. La suite async
actualisée est lancée. Les matchs généraux d’enums dans
un corps async restent ouverts.

## AS4, AS10, AS12 — Attente directe d’une tâche calculée

Le backend résout la tâche transférée depuis bloc, if, boucle
ou match de join avant d’émettre son attente. Les liaisons
préparent cette tâche une seule fois. Elles suivent le mode
de son résultat pour conserver les emprunts ou recevoir
l’allocation transférée.

Quatre exécutions UBSan couvrent les résultats Int avec yield
avant la sortie du bloc ou de la branche. Deux autres couvrent
un résultat &mut Int choisi entre deux cibles. Les lectures
des deux cibles sont refusées avant dernier usage. Un résultat
<- Int traverse aussi un bloc puis un join, avec destruction
unique et réemploi de son slot. Un transfert qui capture un
local du bloc est refusé. Les tests ciblés et la régression
de signature avec Result alloué passent. La suite antérieure
de spawn calculé termine avec 84 tests. La suite async
actualisée est lancée. L’inférence d’un emprunt directement
renvoyé par une fonction async après une attente calculée
reste à étendre.

## AS11 et AS12 — Retour emprunté après attente calculée

L’analyse d’origine suit les tâches à travers leurs liaisons,
les blocs, les branches et les break. Chaque appel possible
contribue les paramètres de capture effectivement retournés.
Les liaisons gardent le contexte lexical de création. Une
cible locale ne peut pas devenir un emprunt de résultat.

Huit exécutions UBSan couvrent les deux cibles, retour direct
après if, relais par tâches et résultats nommés, loop et bloc.
La référence traverse un second appel async puis join. Les
écritures prématurées sur chaque cible possible sont refusées
et les écritures après usage passent. La mutation qui ignore
le second bras fait accepter six écritures prématurées.
Les suites précédentes passent avec 86 tests async et 1 434
tests globaux. La suite globale actualisée est lancée.

## RT5 et MT6 — Attente d’un handle calculé

Le backend async distingue une tâche inactive calculée d’un
handle calculé. L’attente du handle utilise la même extraction
de Result et les mêmes prêts que l’attente d’un handle nommé.
Le résultat peut être lié ou utilisé directement par match.

Huit exécutions UBSan croisent les branches du if, résultat
nommé ou direct, succès ou EAGAIN. Le bras Err retrouve les
deux valeurs intactes et peut les lire. Le bras Ok réserve
les deux cibles possibles jusqu’à la dernière utilisation
du résultat. Supprimer l’enregistrement du prêt de résultat
fait accepter huit accès prématurés. Trois tests ciblés
passent, dont les régressions d’attente d’une tâche calculée
et de match retournant un Result alloué. La suite précédente
d’attente calculée passe avec 88 tests.

### Spawn et await dans une même expression

Le lancement d’un handle temporaire utilise le même chemin
que le lancement vers une liaison. Le point de reprise est
placé après le lancement, avant la nouvelle interrogation
du handle.

Quatre exécutions UBSan croisent résultat nommé ou match
direct, et succès ou EAGAIN. L’oracle force une suspension
au premier poll et fait échouer tout deuxième lancement.
Déplacer le lancement après l’étiquette de reprise dans le
C de test déclenche un abort dans les quatre variantes.
Deux tests ciblés passent. L’emprunt mutable du résultat
reste protégé dans Ok.

### Join bloquant d’un handle temporaire

Le backend synchrone évalue le receveur calculé puis consomme
le handle du scope courant. Les contrats suivent la provenance
du résultat à travers cette évaluation et le retour du Result.
Le dispatch de la méthode join sur une structure nommée
continue de passer.

L’oracle UBSan couvre spawn suivi de join et un if suivi de
join, en succès et sur EAGAIN. Le slot d’origine est réutilisé
après traitement du Result. Le profil historique refuse son
reset prématuré. Une tâche encore inactive est refusée comme
receveur de join. Deux tests ciblés passent. La suite async
de la révision précédente termine avec 90 tests.

### Attente calculée comme instruction Void

Une expression parenthésée suivie de `.await;` peut consommer
une tâche Void choisie par bloc, if ou loop. Le parseur passe
l’attente au même vérificateur que l’instruction d’attente
sur une tâche nommée.

Quatre exécutions UBSan observent la mutation de la cible
choisie après suspension et attente. Une tâche produisant
un Int et un handle produisant un Result sont refusés dans
cette position sans receveur. La régression du receveur
consommant d’une méthode passe aussi. La suite async
actualisée est lancée.

## AS14 et T2 — Allocation transférée au bloc enfant async

Une allocation Int détenue par le parent async peut être
importée par `->` à l’entrée d’un bloc enfant. Le bloc
assume son nettoyage et peut rendre l’import explicitement.
Les captures détenues à la racine restent nettoyées par le
runtime après extraction du résultat.

Quatre exécutions sous UBSan couvrent les deux bras et
l’attente Void ou le drop de la tâche inactive. Les deux
allocations sont détruites une fois et leurs slots sont
réutilisables. Un cinquième cas restitue un import après
yield et le lit dans le parent. Sans restitution, la lecture
est refusée. La mutation qui détruit malgré la restitution
fait refuser le cas valide. Trois tests ciblés passent.

## T2, T9 et AS10 — Int détenu reçu depuis bloc, if ou loop async

Un bloc async peut restituer l’allocation Int elle-même par
`<-`. Le backend écrit le pointeur dans le receveur et désarme
le nettoyage de l’ancien accès. Les branches et les break
vérifient le même mode de résultat sur les sorties possibles.

Trois exécutions UBSan couvrent bloc, if et break, après une
première boucle qui importe l’allocation puis la restitue avant
continue. La cellule ressort par join, est détruite une fois
et son slot est réutilisé. Sans restitution avant continue,
les trois programmes sont refusés. Les régressions de
nettoyage des tâches Void et de reprise de boucle passent.
La suite async actualisée est lancée.

## L3 et T2 — Renommage d’un Int détenu dans une tâche

`let mut renamed = <- a` invalide l’ancien accès et garde
le champ de frame ainsi que la position de nettoyage.
Le renommage d’une capture ne la fait pas passer avant
les captures acquises plus tard dans l’ordre de destruction.
Une liaison créée dans un bloc peut être transférée au
receveur du bloc après yield.

Deux exécutions UBSan vérifient l’écriture via le nouveau
nom, le transfert depuis un bloc, la destruction unique et
le réemploi des slots. Le nom d’origine est refusé après
renommage. Inverser l’ordre de nettoyage des captures dans
une copie temporaire inverse la trace et le test échoue.
Deux tests ciblés passent. La suite antérieure aux changements
de résultats de bloc termine avec 94 tests async.

### Break sans receveur et restitution différée

Un `break <-` sans receveur avertit sans consommer l’Int.
Le nettoyage normal détruit un Int importé dans l’itération,
et l’Int resté au parent demeure disponible après la boucle.
Un prêt en cours ne rend pas le marquage sans effet illégal.
Pour une restitution d’import, le contrôle de l’emprunt
intervient à la sortie du bloc. Il est donc possible de
marquer la restitution puis d’attendre le dernier utilisateur.

Quatre exécutions UBSan couvrent ces distinctions. Une
lecture de l’import détruit et la consommation d’un import
déjà promis au parent sont refusées. Deux tests ciblés
passent. La suite précédente de contrôle des allocations
détenues termine avec 95 tests async. Le remplacement d’un
receveur détenu doit encore intégrer l’ordre de nettoyage
et la provenance des captures.

### Ordre des captures après restitution au parent

Le nettoyage après extraction du résultat sélectionne l’ordre des captures
détenues à partir du chemin de retour atteint. Un retour anticipé détruit
`b` puis `a`. Après import, suspension et restitution de `a` au parent,
la trace montre `a` puis `b`, conformément à L3. Le drop d’une tâche inactive
et un échec de lancement simulé par `EAGAIN` suivent l’ordre initial.

Le test ciblé passe avec quatre exécutions du C11 optimisé sous UBSan fatal.
L’oracle vérifie le résultat, la trace complète des destructions et la
réallocation des deux slots d’un pool de capacité deux. Une mutation dans
une copie temporaire qui impose l’ordre initial sur tous les chemins est
détectée sur le chemin de restitution. La suite de l’étape précédente
termine avec 96 tests async, et la suite du cycle de provenance précédent
avec 1 447 tests. La suite globale de cette révision est lancée.
Le test de restitution n’exerce pas l’ordre combiné des captures différées
et des allocations acquises dans le corps de la tâche.

### Nettoyage terminal commun aux captures et réceptions locales

Le code C exécutait le nettoyage des acquisitions locales dans la reprise
et celui des captures dans le callback de libération. Cette séparation
pouvait faire passer une acquisition locale avant une capture restituée
plus tard dans le même bloc. Le compilateur enregistre maintenant les
opérations du nettoyage terminal dans un plan associé au chemin de sortie.
Le callback exécute ce plan après extraction du résultat. Les sorties
ordinaires de blocs imbriqués continuent de nettoyer ces blocs sur place.
Le plan initial traite la destruction avant démarrage.

Deux tests ciblés passent, pour cinq exécutions C11 optimisées sous UBSan
fatal. Le nouveau cas restitue la capture `a` après la réception d’un Int
par await. Le résultat est `21`, les destructions suivent `a=5`, `c=9`,
`b=7` et le pool de capacité trois accepte ensuite trois allocations.
Une mutation qui inverse les paires destruction et effacement dans le plan
terminal donne `b=7`, `c=9`, `a=5` et le test la détecte. Les suites async
et globale de cette révision sont lancées. Le test cible les allocations
Int et le réemploi de slots. Il ne couvre pas les destructeurs utilisateur.

### Remplacement d’un receveur Int dans une tâche

Le générateur évalue la partie droite avant le remplacement. Il détruit
l’ancienne allocation si elle est encore détenue, puis installe le pointeur
produit. Le déplacement sur place et l’aller-retour par une tâche conservent
l’allocation. Un remplacement par un résultat d’await peut rendre un slot de
l’ancienne source disponible alors que la valeur retournée reste vivante
dans sa propre source. Le contrat suit la provenance d’un remplacement
linéaire résolu et conserve toutes les captures possibles lorsque les
affectations imbriquées ou une expression non résolue peuvent changer l’origine.

Le test ciblé passe avec neuf exécutions C11 sous UBSan fatal et trois
programmes refusés. Il couvre les déplacements, l’attente, le bloc, le if,
le break à résultat et le réemploi de deux pools de capacité un. Il vérifie
aussi la dernière lecture de l’ancienne allocation dans la tâche attendue.
Le même emprunt encore utilisé après le remplacement fait refuser le code.
Une mutation supprimant la destruction de l’ancienne allocation dans une
copie temporaire est détectée, notamment par saturation de son pool.
La suite async de cette révision est lancée. Les jointures de provenance
des remplacements imbriqués restent conservatrices et le test du break
couvre une boucle à résultat, avec la réaffectation après la boucle.

### Receveur de boucle et provenance après remplacement imbriqué

Le contrat d’un résultat détenu propage les remplacements depuis un bloc
enfant et réunit les provenances des branches qui continuent. Dans le
nouveau contre-exemple, les deux branches détruisent la valeur de `p` et
retournent une allocation de `q` ou de `r`. Les quatre exécutions du C sous
UBSan autorisent le réemploi de `p`, avec et sans reset hérité. Le vérificateur
refuse les quatre variantes qui tentent un reset de `q` ou de `r` avant le
dernier usage du résultat. Une mutation qui retient seulement la première
branche laisse passer un reset interdit et le test la détecte.

Deux exécutions supplémentaires couvrent le remplacement dans un bloc
enfant et dans les bras d’un if. Le test de boucle traverse un continue et
une fin normale d’itération avant le break. Une seconde boucle remplace
l’allocation du receveur extérieur juste avant son break, puis les deux
slots sont réutilisés. La variante while est refusée car la sortie sans
itération laisse des obligations de nettoyage différentes.

Les trois tests ciblés passent. La suite du nettoyage terminal précédente
termine avec 98 tests async. La suite globale de cette révision est lancée.
Le contrat conserve encore toutes les captures possibles quand un
remplacement se produit dans une boucle. Le test de boucle vérifie la
valeur et la destruction, sans établir la précision de cette provenance.

### Provenances de remplacement aux reprises et sorties de boucle

Le contrat d’une tâche réunit les provenances des reprises par continue
et par fin normale jusqu’à stabilisation. Il propage ensuite celles des
sorties par break et du test faux d’un while. Les expressions dont les
effets restent non résolus conservent le repli sur toutes les captures.

Deux tests ciblés passent. Leurs onze exécutions sous UBSan couvrent
les deux sources possibles après un break, le réemploi de la source
écartée et les sorties while après zéro ou trois itérations. Neuf
variantes sont refusées, dont les resets hérités des deux pools
qui peuvent encore fournir la valeur retournée. La mutation qui
supprime la propagation des provenances au break est détectée par
les deux variantes qui doivent autoriser le reset du pool écarté.

La suite async est lancée. Le test while reprend avec la même identité.
Il vérifie la propagation du contrat avec et sans itération. Le test
break vérifie séparément un changement de source à la sortie de boucle.

### Dernière lecture dans un remplacement situé dans un bloc enfant

Après l’évaluation de la partie droite, le générateur peut terminer
un prêt issu d’une vue déclarée dans un bloc englobant. Il vérifie la
suite de chaque bloc lexical traversé avant de libérer la protection.
Un prêt propre à une tâche inactive reste suivi indépendamment.

Le test ciblé exécute le C avec UBSan fatal. Une vue déclarée deux blocs
plus haut sert à lire la valeur 5 pendant l’attente. Le résultat 7 est
installé ensuite et les deux pools sont réutilisés. Quatre variantes sont
refusées. Trois prolongent l’usage de la vue à différentes profondeurs
et une le prolonge via une tâche encore inactive. La mutation qui
ignore les continuations englobantes refuse à tort le programme valide
et le test la détecte. La suite précédente sur le remplacement se termine
avec 100 tests async. Ce changement traverse les blocs lexicaux simples.
Il reste conservateur lorsqu’il rencontre une branche, une itération
ou un bloc utilisé comme expression.

### Dernier usage de la vue dans les bras d’un if async

Un if utilisé comme instruction transmet sa continuation aux deux bras.
Chaque bras peut terminer l’emprunt au dernier usage propre à son chemin.
À la jonction, le compilateur compare les états après avoir retiré les prêts
des vues dont aucun usage ne suit le if. Une tâche qui capture une vue reste
porteuse de son propre prêt.

Deux tests ciblés passent. Les deux exécutions ajoutées sous UBSan
couvrent le bras qui lit l’ancienne allocation dans la tâche attendue puis
la remplace, et le bras qui lit directement la vue et garde l’allocation.
Les deux variantes avec une lecture après le if sont refusées. Une mutation
qui omet de terminer les prêts morts à la jonction refuse les deux chemins
valides et le test la détecte. Ce changement couvre le if instruction.
Les branches produisant un résultat et les prêts d’une vue englobante
qui traverse une reprise de boucle restent à traiter séparément.

### Dernier usage dans les expressions de contrôle async

Les if, match et blocs à transfert qui constituent une partie droite
complète reçoivent la continuation de cette affectation ou déclaration.
Les expressions imbriquées qui ont encore des opérandes à évaluer
conservent la barrière de prêt, notamment pendant l’évaluation des
arguments d’un appel.

Le test ciblé passe. Quatre exécutions supplémentaires sous UBSan fatal
couvrent les deux résultats du if, un bloc qui transfère un autre Int
et le bras Ok d’un match de handle. Quatre variantes qui relisent la
vue après la jonction sont refusées, ainsi qu’un appel qui l’utilise
dans son argument suivant. Une mutation qui retire la continuation
du if à valeur reproduit le rejet des deux variantes valides.
Le test du match exécute uniquement Ok. Les continuations de boucles
et l’analyse précise des expressions imbriquées restent ouvertes.

### Dernier usage immédiatement avant un break async

Le compilateur prend en compte la continuation après la boucle lorsqu’un
remplacement est immédiatement suivi d’un break. Une lecture dans la valeur
du break ou après la boucle garde la protection. Les chemins de continue et
de fin normale conservent la protection des prêts englobants à la reprise.
Les sorties par break et par test faux comparent leurs états après
expiration des prêts qui n’ont plus d’usage après la boucle.

Le test ciblé couvre le break simple et le break qui fournit un scalaire,
avec exécution sous UBSan. Les variantes qui relisent la vue dans le
résultat du break, après la boucle ou lors d’une reprise sont refusées.
La suite async est lancée. La détection de sortie anticipée s’applique
au break immédiatement après le remplacement. Une suite de plusieurs
instructions menant nécessairement à un break reste conservatrice.
Trois tests ciblés passent. Retirer la reconnaissance du break immédiat
dans une copie temporaire reproduit le rejet du cas valide et le test
détecte la mutation.

### Dernier usage sur un chemin lexical menant au break

Le compilateur parcourt les instructions qui restent sur le chemin lexical
jusqu’au break. La sortie peut suivre plusieurs instructions ou se trouver
dans un bloc englobant. Un transfert de contrôle imbriqué, comme un continue
dans un if, empêche de conclure que ce chemin sort de la boucle.

Deux tests ciblés passent. Les deux exécutions ajoutées sous UBSan
suspendent puis lisent la nouvelle allocation avant le break. Une des deux
effectue le remplacement dans un bloc enfant. Trois variantes sont
refusées, avec lecture de l’ancienne vue avant le break dans le même bloc
ou dans le parent, ou avec continue conditionnel. Une mutation qui ignore
la continuation du bloc englobant reproduit le rejet erroné du deuxième
cas valide et le test la détecte. Une convergence vers une sortie par
plusieurs branches imbriquées reste conservatrice.

### Capture d’une case de tableau dans l’état du parent async

Un tableau fixe Int local réside dans l’état stable du parent. Un enfant
peut capturer l’adresse d’une case. Deux indices constants différents
désignent des cases disjointes. Un indice dynamique est évalué une fois,
contrôlé avant l’accès et traité comme un recouvrement possible. L’écriture
évalue et contrôle l’indice avant la partie droite, puis vérifie l’accès.
Le prêt peut se prolonger dans un résultat emprunté reçu par le parent.

Le test exécute le C11 sous UBSan fatal avec spawn et await, lecture
partagée, mutation exclusive, écriture disjointe et indice dynamique. La
variante hors limites s’arrête avec le diagnostic attendu. L’emprunt
retourné est exercé par mutation et par dernière lecture dans la partie
droite d’une écriture. Les accès incompatibles, le dépassement de portée
et la sortie sans attente sont refusés. Supprimer la réservation de la
case dans une copie temporaire fait accepter une écriture conflictuelle
et le test détecte la mutation. La suite async actualisée est lancée.
Le changement concerne le tableau Int fixe unidimensionnel de l’état
async. Les captures depuis un tableau d’une fonction synchrone, les
tableaux imbriqués et les champs inline restent ouverts.

### Projections imbriquées dans un tableau de l’état async

Les tableaux Int rectangulaires sont stockés dans l’état stable du parent.
Une capture suit le chemin complet de la case. Une différence constante
sur une seule coordonnée suffit à prouver la disjonction, même si une
autre coordonnée est dynamique. Chaque indice est évalué et contrôlé
avant l’indice suivant.

Les deux tests ciblés passent. Le nouveau test exécute deux chemins
valides et un chemin qui doit s’arrêter sous UBSan. Un indice extérieur
hors limites empêche l’exécution de la tâche qui calcule et affiche
l’indice intérieur. Trois variantes sont refusées à la compilation,
pour un recouvrement possible, un indice constant hors limites et une
forme irrégulière. Une mutation qui inverse l’ordre de projection
affiche 77 avant l’arrêt et le test la détecte. La suite async de
l’étape du if instruction termine avec 102 tests. Les captures de
lignes entières, de tableaux synchrones et de champs inline restent
à traiter.

### Capture d’une ligne entière entre tâches async

Un paramètre de tableau Int partagé ou mutable garde les dimensions
déclarées. La tâche reçoit l’adresse de la projection et le C accède
au stockage avec un pointeur vers le tableau de cette forme. Le prêt
réserve toutes les cases sous ce chemin. Une ligne disjointe reste
accessible. Le réemprunt d’une ligne mutable, y compris en lecture
seule, réserve la capacité d’origine pendant son utilisation.

Le test exerce sous UBSan une capture mutable, son relais par
réemprunt explicite et une capture partagée. Les quatre variantes
refusées couvrent une écriture dans une ligne réservée, une projection
de mauvaise dimension, un tableau local immutable et une écriture
via un paramètre partagé. Une mutation qui compare uniquement les
chemins de même longueur accepte une écriture conflictuelle et le
test la détecte. Une vérification ciblée confirme le diagnostic
pour la création depuis une fonction synchrone. Cette intégration
synchrone et le retour d’emprunts dérivés d’un paramètre de tableau
restent ouverts.

### Résultat emprunté dérivé d’un paramètre de tableau

Un retour explicite d’emprunt vers une case de paramètre de tableau
identifie le paramètre d’origine dans le contrat. L’origine est propagée
à travers un relais qui attend la tâche et à travers un appel qui
emprunte directement la case. Le receveur garde le prêt après await
jusqu’au dernier usage. Un tableau local à la tâche ne peut pas fournir
ce résultat.

Le test ciblé exécute sous UBSan les retours mutable et partagé ainsi
qu’un relais qui emprunte la case. Il refuse l’accès à la case encore
empruntée, l’écriture dans la même ligne pendant la réservation et le
retour d’une case locale. Une mutation qui oublie de porter le prêt
dans le résultat accepte un accès interdit et le test la détecte.
Le contrat garde actuellement la ligne entière réservée après le
retour. La réduction du prêt au chemin exact et les créations depuis
une fonction synchrone restent à traiter.

### Réservation de la case effectivement retournée

Le contrat d’un résultat emprunté conserve le paramètre et le chemin
possible de chaque projection. Un relais compose ce chemin avec celui
de son argument. L’enfant réserve la ligne tant qu’il peut l’utiliser.
Après await, la protection suit les cases que le résultat peut désigner.
Un indice dynamique conserve toutes les cases compatibles à cette
coordonnée, et deux retours possibles conservent l’union de leurs chemins.

Deux tests ciblés passent sous UBSan fatal, avec retour direct,
relais, réemprunt de case, attente d’un handle et résultat partagé.
L’écriture d’une autre case de la même ligne est admise après l’attente.
La case retournée, un résultat dynamique et les alternatives d’un
retour conditionnel sont encore protégés. Omettre le suffixe dans une
copie temporaire refuse à tort l’écriture disjointe et le test détecte
la mutation. La création depuis une fonction synchrone reste ouverte.

### Capture d’un tableau local depuis une fonction synchrone

Une tâche créée en synchrone peut emprunter une case Int ou une ligne
Int. Le compilateur attache la réservation à la dépendance de la tâche
puis du handle. Elle reste active même sans nouvel usage du nom.
Un transfert vers un bloc qui survit au tableau est refusé. Le join et
le drop de la tâche inactive terminent la réservation. Le drop du
handle actif exige encore un join.

Deux tests ciblés couvrent cette capture et la régression des emprunts
ordinaires sur pool. Le nouveau test exécute sous UBSan une ligne,
une case et une tâche détruite avant démarrage. Quatre variantes sont
refusées, dont deux accès avant join et un transfert depuis un tableau
local au bloc enfant. Une mutation qui oublie les prêts portés par la
tâche accepte un accès prématuré et le test la détecte. En synchrone,
la réservation couvre encore le tableau entier. Le retour d’un
emprunt issu de ce tableau, la capture d’un tableau de rang supérieur
en entier et les contrats de passage à une autre fonction restent ouverts.

### Projections disjointes pendant une capture synchrone

Un emprunt de tâche issu d’une projection directe de tableau local
conserve le chemin de cette projection. La lecture, l’écriture et une
nouvelle capture directes sont admises si une coordonnée constante
distingue les chemins. Une coordonnée dynamique reste inconnue et
un emprunt à travers un alias sans chemin établi garde la protection
du tableau.

Trois tests ciblés passent sous UBSan fatal. Les ajouts couvrent une
écriture disjointe avant spawn, une lecture disjointe avant join et
deux workers qui écrivent dans des cases différentes de la même ligne.
Un indice dynamique qui peut désigner la ligne réservée est refusé.
Retirer la comparaison des chemins fait refuser l’écriture disjointe
et le test détecte la mutation. La suite globale de la révision des
tableaux imbriqués a signalé un échec et poursuit son exécution.
Le rapport détaillé de cette exécution est encore attendu. Les
résultats empruntés depuis un tableau synchrone et les chemins
issus d’alias restent ouverts.

### Résultat de join synchrone vers une case inline

Le join conserve le chemin projeté dans le résultat nommé. Son bras Ok
reçoit le pointeur de la case comme emprunt de tableau. Une écriture
disjointe est possible avant le match et dans le bras Ok. Le bras Err
termine le prêt, y compris après un échec de lancement.

Trois tests ciblés passent sous UBSan fatal. Les nouveaux scénarios
couvrent le résultat partagé ou mutable, le match direct ou différé
et le lancement échoué par EAGAIN. Les deux accès conflictuels avant
le dernier usage sont refusés. Une mutation qui oublie la réservation
du résultat nommé laisse passer l’accès avant le match et le test la
détecte. Une régression du libellé des signatures async non supportées,
repérée dans une suite antérieure, a été reproduite puis corrigée. Son
test ciblé passe. La suite async actualisée tourne. Les résultats
pouvant désigner soit une case inline soit une allocation de pool
restent refusés.

### Résultat de join à provenance inline ou pool

Quand un résultat peut désigner une case inline ou une allocation
Int, le bras Ok conserve le pointeur Int et réunit les deux chemins.
Le chemin pool garde son ascendance de prêt, y compris lorsqu’un
emprunt partagé dérive d’une capacité mutable. Une capture du tableau
entier peut réduire son prêt à la case retournée après join.

Trois tests ciblés passent pour le résultat mixte et les deux formes
homogènes. Le nouveau test exécute sous UBSan fatal les deux
destinations mutables et la lecture partagée depuis une capacité
exclusive. Neuf variantes refusées couvrent les accès aux deux
origines avant le match ou dans Ok, dont la lecture du pool pendant
l’emprunt partagé exclusif. Une mutation qui retire le chemin pool
à l’extraction rend l’écriture prématurée acceptable et le test la
détecte. Le passage à une fonction ordinaire d’une tâche qui capture
un tableau reste ouvert.

### Relais synchrone d’une tâche qui emprunte un tableau

Un contrat de fonction ordinaire représente désormais les emprunts
de tableau des tâches et handles reçus par transfert. Un relais peut
les retourner, les lancer, joindre le handle ou détruire la tâche
inactive. L’appelant conserve la projection concrète et le compilateur
vérifie la réservation pendant la préparation des arguments.

Le test ciblé exécute sous UBSan la chaîne relais, spawn et join,
la destruction avant démarrage et un appel avec un second argument
qui emprunte une case disjointe. Quatre variantes refusées couvrent
l’accès prématuré des deux côtés du relais, le conflit du second
argument et le drop du handle dans la fonction. Une mutation qui
omet les captures de tableau dans le contrat de relais accepte un
accès prématuré et le test la détecte. Les fonctions qui recevraient
une tâche à résultat emprunté depuis un tableau restent à traiter.

### Join d’un résultat de tableau dans une fonction synchrone

Le vérificateur représente un paramètre async déclaré comme emprunt
de tableau par une provenance symbolique de tableau. Le code de la
fonction qui joint le handle extrait le pointeur Int et peut lire
ou muter la case avant de rendre un scalaire. Un relais de tâche
garde la réservation concrète chez l’appelant.

Trois tests ciblés passent sous UBSan fatal. Les cas ajoutés couvrent
la lecture partagée, l’écriture mutable, EAGAIN et le refus d’une
écriture avant l’appel qui joint le handle. Supprimer la provenance
symbolique fait échouer la vérification du relais et le test détecte
la mutation. La suite précédente de 106 tests s’est terminée avec un
unique échec, le diagnostic de signature corrigé au cycle précédent.
Retourner l’emprunt à travers une fonction ordinaire ou faire passer
une case inline via un paramètre async déclaré simplement &Int
reste hors de cette intégration.

### Retour synchrone d’un emprunt obtenu par join

Le contrat d’une fonction synchrone peut maintenant restituer l’emprunt
d’un join quand le paramètre async à l’origine du prêt est un tableau
emprunté. Le compilateur compose la projection du résultat avec
la capture concrète chez l’appelant. Une alternative qui emprunte
une allocation de secours reste dans la même union de provenances.

Trois tests ciblés passent sous UBSan fatal. Le cas ajouté couvre
le retour de la case, le secours du pool après EAGAIN et un deuxième
relais synchrone. L’écriture dans une case disjointe passe. L’écriture
prématurée dans la case retournable ou dans le pool est refusée.
Une mutation qui omet le chemin de tableau du contrat refuse le
programme valide et le test la détecte. Le passage d’une case inline
via un paramètre async déclaré &Int ou &mut Int reste à traiter
pour les fonctions qui reçoivent ces handles.

### Relais synchrone d’un résultat de capture scalaire inline

La spécialisation du C utilise les provenances réelles à l’appel.
Le même relais d’un handle dont le paramètre async est &mut Int
accepte une case inline et une allocation de pool. Le vérificateur
opaque compose le chemin du résultat à partir du résumé enregistré
lors de la vérification des définitions async.

Trois tests ciblés passent sous UBSan fatal. Le cas ajouté exécute
les deux représentations dans le même programme et vérifie le
maintien du prêt de la case et du pool de secours. Une variante
au niveau du script passe aussi en vérification opaque. Une
mutation qui ne transmet pas le résumé à ce vérificateur échoue
sur cette variante et le test la détecte. La suite globale de la
révision précédente tourne encore.
L’exécution globale lancée sur le dossier de travail a ensuite signalé
des erreurs en série. La suite globale de la révision actuelle a été
lancée depuis une copie figée pour isoler la validation des modifications
suivantes. Le détail de l’exécution précédente reste attendu.

### Recapture synchrone d’une case déjà empruntée par join

Un résultat de join qui emprunte une case de tableau local peut
être passé à une autre tâche par son nom ou par réemprunt explicite.
Un chemin de case connu est conservé. La seconde tâche laisse une
case disjointe accessible et réserve la vue d’origine jusqu’à
son join, y compris lorsque la seconde capture est partagée mais
provient d’une capacité mutable.

Le test ciblé exerce sous UBSan les deux syntaxes mutables et la
recapture partagée. Les accès prématurés via la vue et le tableau
sont refusés. Omettre l’héritage du chemin refuse une écriture
disjointe et le test détecte la mutation. Le premier essai de
la capture partagée laissait lire la vue mutable avant le join.
La réservation active porte maintenant l’exclusivité et cette
variante est refusée. Les alias sans chemin de case établi
restent conservateurs. La recapture d’un résultat qui peut
aussi désigner une allocation de pool reste ouverte.

### Recapture d’un résultat mixte inline ou pool

La seconde tâche reçoit le pointeur Int du premier résultat.
Le compilateur garde une réservation distincte pour chaque origine.
Le chemin inline reste projeté et la provenance du pool continue
de protéger son stockage, y compris lorsque la première vue
n’a plus d’usage direct.

Deux tests ciblés passent sous UBSan fatal. Le scénario mixte
exécute les deux cibles possibles et écrit dans une case disjointe
pendant la seconde tâche et dans son bras Ok. Les variantes qui
écrivent sur une cible possible avant le second join ou réinitialisent
son pool par le mode hérité sont refusées. Supprimer le chemin pool
de la recapture rend une écriture prématurée acceptable et le test
détecte la mutation. Une suite async antérieure termine avec
108 tests réussis. La suite globale figée est encore en cours.

### Capture d’une case à travers une vue de ligne

Le compilateur conserve le chemin d’une vue de ligne et le compose
avec celui de la case empruntée par la tâche. Seules les réservations
de tâches et leurs résultats exploitent ce chemin pour autoriser les
accès disjoints. L’emprunt ordinaire conserve la protection du tableau
entier prévue par E6.

Trois tests async ciblés passent sous UBSan fatal. Le cas ajouté
modifie une case via une vue de ligne et permet au parent d’écrire
dans l’autre case avant join. La variante qui écrit dans la case
capturée est refusée. Omettre la composition du chemin fait
refuser la variante valide et le test détecte la mutation. Deux
tests ciblés des emprunts ordinaires passent également. La suite
des tableaux fixes tourne sur une copie figée. Les vues dont
la provenance n’établit pas un chemin unique restent conservatrices.

### Répétition, tableaux vides et longueur statique dans une tâche

Les tableaux Int locaux async acceptent la répétition et les formes
vides annotées. Le générateur évalue le motif une fois, avant de
dupliquer sa valeur, y compris pour une longueur nulle. Les dimensions
logiques restent distinctes des emplacements C réservés pour les
tableaux vides. La longueur statique reste disponible via len().

Deux tests async ciblés passent sous UBSan fatal. Le test ajouté
exerce une répétition imbriquée suspendable, une répétition de
longueur zéro, deux formes vides et un emprunt de tableau vide.
Trois variantes sont refusées. Une mutation qui saute l’évaluation
du motif pour une longueur nulle perd l’affichage attendu et le
test la détecte.

La suite figée de l’étape précédente a révélé une non-convergence
de l’analyse de boucle sur un tableau de références. Le chemin
d’emprunt est maintenant associé à un marqueur d’identité stable.
Le cas de boucle et le test d’emprunts ordinaires repassent.
Les suites tableaux fixes et async actualisées tournent sur une
copie figée.

### Replace et swap d’une case dans l’état async

Replace prépare et contrôle la place avant d’évaluer la nouvelle
valeur. Il vérifie le prêt au moment de l’écriture et rend l’ancienne
valeur. Swap évalue une fois la projection de ligne, puis les deux
indices dans l’ordre. Il vérifie les deux accès avant d’écrire et
deux indices identiques laissent la valeur en place.

Le test ciblé passe avec cinq exécutions sous UBSan fatal, dont deux
arrêts attendus sur indice hors limites. Il exerce aussi la dernière
lecture de la vue dans la partie droite de replace et un swap pendant
une capture disjointe. Deux accès conflictuels sont refusés. Une mutation
qui inverse les indices de swap inverse les effets visibles et le test
la détecte. Ce cycle couvre les cases Int. Replace et swap de lignes
entières et de valeurs contenant des références restent à traiter
dans les corps async.

### Copie explicite et échange de lignes Int

Une liaison async peut recevoir copy d’un tableau Int ou d’une
ligne. La copie est indépendante. Swap échange également des lignes
complètes sans réserver de tampon de la taille d’une ligne sur la
pile d’exécution. Les deux opérations vérifient la projection avant
de lire ou d’écrire.

Deux tests ciblés passent sous UBSan fatal. Le scénario ajouté
copie puis modifie une ligne et en échange deux autres pendant
un prêt disjoint. Quatre variantes refusent la copie ou l’échange
conflictuel, la mauvaise dimension et la copie implicite. Une
mutation qui altère les octets de la ligne échangée est détectée
par la comparaison de son contenu. Replace de lignes, transferts
de tableaux par valeur et lignes contenant des références dans
les corps async restent ouverts.

### Remplacement d’une ligne Int entière

Une liaison async peut recevoir l’ancienne ligne produite par
replace. Le générateur contrôle la destination, prépare une nouvelle
ligne de même forme, vérifie le droit d’écrire, puis copie l’ancienne
ligne au receveur et installe la nouvelle. La partie droite peut être
un littéral, une répétition ou une copie explicite, y compris de la
ligne remplacée.

Deux tests ciblés passent sous UBSan fatal. Le cas ajouté exerce un
indice suspendable, une partie droite suspendable, la copie de la
ligne remplacée et une dernière lecture empruntée dans la partie
droite. Un indice hors limites empêche le premier effet de la partie
droite. Les dimensions incompatibles et l’emprunt qui doit encore
servir sont refusés. Une mutation qui retourne la nouvelle ligne au
lieu de l’ancienne est détectée. Les transferts de tableaux par
valeur entre scopes et les lignes contenant des références restent
ouverts dans les corps async.

### Déplacements explicites de tableaux Int entre scopes async

Un tableau Int peut être déplacé par <- vers une nouvelle liaison,
ou exporté comme résultat d’un bloc, d’un if ou d’un break. Une
copie explicite peut aussi être suivie de son transfert. La forme
est conservée, le compilateur vérifie l’absence de prêt actif et
l’accès d’origine devient inutilisable. Les tableaux empruntés
en paramètre et les cases individuelles ne sont pas déplaçables.

Le test ciblé passe avec quatre exécutions sous UBSan fatal, couvrant
les deux chemins d’un if et deux break. Trois variantes refusent la
lecture de la longueur après déplacement, le déplacement pendant
un prêt et des branches de formes différentes. Une mutation qui
oublie d’invalider l’origine fait passer la lecture après déplacement
et le test la détecte. Les paramètres et retours de tableaux par
valeur entre fonctions async restent à traiter.

### Paramètres async de tableaux Int par valeur

Le tableau par valeur est préparé avant l’argument suivant, puis
copié dans l’état de la tâche dès sa création. Un tableau local
peut être copié explicitement ou déplacé. Un littéral ou une
répétition produit directement une valeur. Depuis un appelant
synchrone, le générateur adapte les tableaux imbriqués sans
supposer que leurs structures C ont la disposition du tableau
natif de l’état async.

Deux tests ciblés passent sous UBSan fatal. Le nouveau scénario
exerce la copie avant un argument suspendable qui mute la source,
le transfert explicite, le littéral et la capture d’une matrice
depuis main. La copie implicite et la lecture après déplacement
sont refusées. Une mutation qui attend la fin de tous les arguments
pour lire la source change 143 en 223 et le test la détecte.
Les retours de tableaux par valeur entre tâches restent ouverts.

### Retour d’un tableau Int entre tâches async

La tâche retourne un tableau Int par transfert explicite. Le
callback d’extraction copie la valeur dans le receveur avant la
libération du slot. Un relais peut attendre la tâche, copier
le tableau explicitement et retourner cette copie. La forme
déclarée est contrôlée aux deux extrémités.

Deux tests ciblés passent sous UBSan fatal. Le nouveau scénario
réutilise des pools de tâches de capacité un et modifie le premier
résultat après réception du second. Les deux valeurs restent
indépendantes. Cinq variantes refusent le retour implicite,
les dimensions incompatibles au retour ou à la réception,
l’attente sans receveur et le spawn de cette forme de résultat.
Une mutation remplaçant la copie d’extraction par des zéros
est détectée. La restitution par join après spawn reste ouverte.

### Résultat de tableau depuis un handle attendu dans une tâche

Un parent async peut lancer une tâche qui retourne un tableau Int.
L’attente transmet un emplacement dimensionné à l’extraction et
le match reçoit le tableau dans Ok. En cas d’échec de lancement,
Err peut fournir son propre tableau. Le handle doit être attendu.
Le chemin d’abandon actuel ne fournit pas de tampon dimensionné.

Deux tests ciblés passent sous UBSan fatal. Le nouveau scénario
attend successivement deux résultats dans un pool de capacité un,
avec un match direct et un résultat nommé. L’échec EAGAIN simulé
exerce les deux tableaux de secours. Le drop du handle actif est
refusé. Une mutation utilisant l’extraction scalaire à la place
du tampon tableau est détectée. Le join depuis une fonction
synchrone reste ouvert.

### Join synchrone d’un résultat de tableau

Le join bloquant extrait le résultat dans un tampon natif de la
forme déclarée. Le bras Ok le convertit dans la représentation
des tableaux synchrones. Le bras Err conserve son traitement
sans lire ce tampon. La tâche reste soumise à l’attente avant
destruction du handle.

Les tests ciblés exercent sous UBSan un résultat nommé dans une
fonction de collecte, un match direct et un match à valeur.
Le scénario réutilise le slot de tâche de capacité un et simule
EAGAIN. Détruire le handle actif est refusé. Une mutation qui
altère la conversion des cases est détectée. Les tableaux
contenant des références et l’abandon d’un handle à résultat
de tableau restent ouverts.

### Abandon d’un handle à résultat tableau

Un handle sans capture empruntée ou transférée peut être abandonné
même si son résultat est un tableau. Le runtime attend la terminaison
avant de consommer l’état complet et de libérer le slot. Il ignore
le résultat sans appeler l’extraction. Un handle avec capture encore
protégée ou résultat propriétaire exige toujours un join.

Quatre tests ciblés passent sous UBSan fatal. Ils couvrent la
fermeture après abandon synchrone et async, la récupération de
slots avant fermeture et les rejets d’abandon avec emprunt. Un
harnais vérifie que l’opération refuse un état inactif, libère
exactement une fois et ne déclenche pas le callback d’extraction.
La mutation qui omet le contrôle atomique est détectée. La suite
figée précédente, tableaux fixes et async, termine avec 182 tests
réussis.

### Capture directe d’un champ Int inline

Une tâche créée depuis une fonction synchrone peut emprunter un
champ Int inline d’une structure. La réservation suit le champ,
l’allocation porteuse et son pool. Un champ frère reste accessible
pendant la tâche et le résultat de join garde le prêt du champ
jusqu’au dernier usage.

Trois tests ciblés passent sous UBSan fatal. Le cas ajouté couvre
la mutation du champ par la tâche puis par le résultat, la mutation
du champ frère, le réemploi du slot et EAGAIN. Les accès prématurés
au champ, le drop du porteur et le reset hérité du pool sont refusés.
Une mutation qui omet la réservation de la capture de champ fait
accepter l’écriture prématurée et le test la détecte. Le cycle suivant étend cette vérification aux contrats de fonction.


### Retour par contrat d’une tâche empruntant un champ inline

Une fabrique et un relais synchrones transmettent la provenance du champ
Int inline. Le porteur reste protégé pendant la tâche. Le prêt du champ
survit au join si le résultat le restitue et dure jusqu’à son dernier
usage. Le champ frère reste accessible à chaque étape.

Quatre tests ciblés passent, avec compilation C à `-O2` et UBSan fatal
pour les exécutions. Le cas ajouté observe `9, 5` après un join réussi et
`99, 1, 4` quand `pthread_create` échoue avec EAGAIN. Les écritures
prématurées, le reset hérité et le retour d’une tâche qui emprunte un
porteur local sont rejetés. La mutation supprimant la propagation du champ
dans le contrat est détectée par le rejet injustifié de l’accès au champ
frère. Les tests existants de captures détachées et de modification du
porteur passent également.

La nouvelle suite async et tableaux fixes est lancée sur une copie figée.
Les fabriques avec porteur indirect et changement de provenance restent
à examiner. Ce cycle utilise des oracles déterministes et UBSan. Il
n’ajoute pas de modèle indépendant pour la composition des contrats.


### Champ inline atteint par un champ de référence partagé

Un remplacement du champ `View.target` après la création de la tâche
laisse la tâche liée au point d’origine. Si le relais effectue le
remplacement avant la création, la tâche capture le nouveau point.
Le contrat résout la projection détachée sur l’état d’entrée de
l’appel, ou sur la nouvelle provenance si le remplacement précède
l’appel dans le corps du relais. Un remplacement conditionnel
conserve les deux cibles possibles pour la vérification statique.

Le cas reproduit l’ancien diagnostic d’incompatibilité entre retour
mutable et champ partagé. Quatre tests ciblés couvrent la capture
directe et indirecte, le résultat emprunté et le remplacement du
champ partagé. Le C généré à `-O2` sous UBSan fatal affiche `5` ou
`7` selon le moment du remplacement. Le test peut détruire le
porteur intermédiaire et le point non capturé. Il rejette le drop
de la cible capturée avant spawn et avant le dernier usage du
résultat, ainsi que le reset hérité de son pool. Avec le
remplacement conditionnel, le drop de chaque cible possible est
rejeté et les deux exécutions sont observées.

La mutation qui résout la projection après l’appel est détectée
par le rejet injustifié du drop du point non capturé. Les
porteurs indirects mutables et les chaînes plus profondes restent
à examiner. L’oracle de ce cycle est déterministe.

La suite figée précédente a révélé que le harnais C du scheduler
attendait encore l’extraction des résultats abandonnés. L’oracle
vérifie maintenant une extraction pour join et await réussis, zéro
pour l’abandon et l’échec du lancement. Il vérifie aussi que les
workers abandonnés ont terminé et que leurs slots sont libérés une
fois. Le harnais corrigé et les deux régressions sur la récupération
des slots abandonnés passent sous UBSan fatal. La suite figée est
antérieure à cette correction. L’exécution ASan lancée pour le
relais indirect reste sans résultat exploitable pour ce cycle.


### Durée de vie des porteurs d’une capture mutable indirecte

Une tâche emprunte un champ Int inline à travers deux champs
`&mut` et ressort d’une fabrique synchrone puis d’un relais. Le
compilateur vérifie désormais la durée de vie de chaque porteur
réservé par le prêt au moment du transfert enfant → parent.
Avant la correction, le compilateur acceptait le transfert d’une
tâche à résultat scalaire même si le premier porteur était local
au bloc. La mutation qui retire la vérification reproduit cette
acceptation et le test la détecte.

Quatre tests ciblés passent sous UBSan fatal. Dans le nouveau cas,
le prêt restitué par join modifie la cible et le programme affiche
`9`. Même résultat après transfert si tous les porteurs survivent.
Le drop et le reset de chaque porteur ou de la cible sont refusés
avant spawn et avant le dernier usage du prêt rendu par join.

La suite figée précédente a exécuté 193 tests avec un seul échec,
l’assertion obsolète du harnais du scheduler documentée ci-dessus.
Le harnais corrigé passe en isolation. Une suite async et tableaux
fixes figée après correction est en cours. La couverture des
chaînes hétérogènes et de la composition de plusieurs captures
reste partielle. Les oracles ajoutés sont déterministes.


### Deux captures inline transmises par paramètres scalaires

Une fabrique qui reçoit deux `&mut Int` peut retourner une tâche
qui les capture quand les arguments de l’appel sont deux champs
inline distincts. Le contrat reconstruit les deux prêts à partir
des chemins des arguments. Avant la correction, il tentait de lire
l’identifiant d’une allocation absente et levait `AttributeError`.
Supprimer cette reconstruction reproduit l’erreur et le test la
détecte.

Le C à `-O2` sous UBSan fatal affiche `12, 9, 13`. Le second champ
redevient accessible dès le join et le résultat conserve le prêt
du premier. L’échec simulé EAGAIN laisse les deux champs intacts
et affiche `99, 1, 2`. Les tests rejettent la capture mutable
double du même champ, la modification du second avant spawn et
la modification du premier pendant que le résultat reste utilisé.
Les tests ciblés de captures directes, indirectes et de prêt
restitué restent au vert. Un essai de chaîne mêlant champ mutable
et champ partagé compile, mais la couverture systématique de ces
chaînes reste ouverte.


### Cases de tableaux passées à une fabrique synchrone

La reconstruction d’un prêt à partir d’un paramètre scalaire
respecte E6. L’appel ordinaire réserve le tableau entier et
refuse deux emprunts mutables vers le même tableau, même si les
indices sont distincts. Les captures issues de deux tableaux
distincts sont admises. Le C à `-O2` sous UBSan fatal affiche
`9, 13`. Le join libère le second tableau et garde le premier
réservé tant que son résultat sert.

L’accès prématuré à une case voisine et le transfert d’une tâche
qui capture une case locale sont rejetés. La mutation attribuant
au tableau local la portée de son parent rend le transfert
acceptable et le test détecte cette faute. Quatre tests ciblés
et les 68 tests de tableaux fixes passent sur la version corrigée.
La suite figée du cycle précédent compte 195 tests
réussis. Elle précède ce contrôle supplémentaire sur les
fabriques scalaires. La précision des projections dans les
captures async directes reste à comparer systématiquement
à la règle E6 des appels ordinaires.


### Ligne entière empruntée par une tâche créée dans une fabrique

Une fabrique synchrone et son relais peuvent retourner une tâche
qui capture une ligne Int injectée par `&` ou `&mut`. Le contrat
conserve l’origine du paramètre tableau. Une tâche qui emprunte
une ligne locale ne peut pas quitter son bloc.

Quatre tests ciblés passent. Le nouveau cas compile le C à `-O2`
sous UBSan fatal et observe `12, 13` après un join mutable, puis
`99, 10, 20` avec EAGAIN simulé. L’emprunt partagé autorise une
lecture concurrente et refuse la mutation tant que le prêt sert.
Le cas mutable conserve la réservation du tableau entier lors
du passage par l’appel ordinaire. La mutation qui omet l’origine
tableau dans le contrat reproduit le rejet du programme valide.

La suite générale figée plus ancienne a terminé avec 1 470 tests
réussis. La suite async et tableaux fixes intégrant cette
modification est en cours. Les captures de lignes contenant des
références restent ouvertes.


### Capture d’une référence partagée stockée en case

Le contrat d’une fabrique synchrone qui retourne une tâche
conserve la provenance de la référence lue dans une case.
L’appel fige cette provenance avant d’appliquer le remplacement
de la case. Si le relais remplace la référence avant d’appeler
la fabrique, la nouvelle cible est capturée.

Trois tests ciblés passent. Le C à `-O2` sous UBSan fatal affiche
`7, 7` quand la tâche capture l’ancienne cible et `7, 9, 9`
quand le relais a déjà remplacé la référence. Le drop de
l’allocation non capturée est admis. Le drop de la cible et
le reset hérité de son pool sont refusés, avec contrôle du drop
jusqu’au dernier usage du prêt restitué par join. La mutation
qui résout la case après l’appel refuse à tort le drop de la
nouvelle cible et le test la détecte.

Ce cycle couvre la lecture d’une référence partagée stockée.
Le réemprunt d’une référence mutable stockée et la capture du
conteneur de références entier restent ouverts.


### Réemprunt d’une référence mutable stockée

Une fabrique et un relais peuvent retourner une tâche qui
réemprunte la cible d’une référence mutable stockée. Le contrat
conserve le lien avec la capacité de la case. La seconde case
reste accessible, tandis que l’accès et le swap de la case prêtée
sont refusés jusqu’à la fin du prêt restitué par join. Un réemprunt
partagé issu de cette capacité maintient aussi la réservation
exclusive d’origine.

Quatre tests ciblés passent. Le C à `-O2` sous UBSan fatal couvre
le join mutable, EAGAIN et le join partagé. Le reset hérité est
refusé avant spawn et pendant l’usage du résultat. Une mutation
qui retire le parent du réemprunt fait refuser une écriture
valide à travers le résultat du join. Le test détecte cette
rupture de filiation. Les 69 tests du cycle précédent, tableaux
fixes et capture partagée stockée, sont passés. La capture du
conteneur de références entier et les combinaisons de projections
dynamiques restent à traiter.


### Réemprunt async d’une case sélectionnée à l’exécution

Le contrat conserve les deux origines possibles lorsque la
fabrique réemprunte une référence mutable avec un indice
dynamique. L’exécution sous UBSan fatal modifie uniquement
l’Int sélectionné, pour chaque indice valide, avec un tableau
simple et avec des lignes référencées. Les indices `-1` et `2`
du tableau simple déclenchent le diagnostic de bornes.

Avant spawn et avant le dernier usage du prêt issu du join,
le vérificateur refuse l’écriture par chacune des deux cases,
leur échange et le reset hérité de chacun des deux pools.
La mutation conservant seulement la première provenance fait
accepter une opération interdite et le test la détecte. Ce
cycle ajoute une régression pour un comportement déjà assuré
par la composition du contrat. Les 25 tests ciblés, dont la suite
des lignes imbriquées, passent. La suite figée async et tableaux
fixes antérieure aux captures de références stockées termine
avec 198 tests réussis. La capture du conteneur entier reste
ouverte.


### Capture directe d’un tableau plat de références partagées

Une tâche lancée depuis une fonction synchrone peut capturer
`&[&Int; N]`. Le C transmet le stockage du tableau à la tâche.
Le vérificateur suit le tableau et toutes les cibles. Dans la
tâche, l’indexation suivie du déréférencement explicite lit
l’Int, avec le contrôle de bornes habituel.

Le test sous UBSan fatal exerce deux indices après yield, une
lecture partagée côté appelant, la longueur et le diagnostic
hors limites. Le drop des cibles, le reset hérité de leur pool,
le remplacement d’une case et le transfert hors du bloc du
tableau sont refusés pendant le prêt. Supprimer les prêts des
cibles fait accepter un drop interdit et le test le détecte.
Les tests voisins de tableaux Int ont également été exécutés.
La suite async, tableaux fixes et lignes imbriquées tourne sur
une copie figée.

La capture d’un conteneur mutable, les conteneurs imbriqués,
les relais et les résultats empruntés issus du conteneur entier
restent à traiter. Ce cycle utilise un oracle déterministe.


### Tableau de références partagé transmis par fabrique et relais

Le contrat de retour reconstruit la capture du conteneur partagé
et les prêts de ses cibles. Si la fabrique remplace une référence
avant de créer la tâche, la reconstruction utilise les cases
mises à jour par l’appel. Un remplacement après création est
refusé, car la tâche emprunte le conteneur entier.

Le C généré à `-O2` sous UBSan fatal affiche `9, 12` après
lancement réussi et `9, 99` avec EAGAIN. Le drop de l’ancienne
cible est accepté avant lancement. Le drop des deux cibles
effectivement capturées est refusé. Une mutation qui relit
l’état d’entrée lors de la reconstruction refuse le drop de
l’ancienne cible et le test la détecte.

Le relais validé est synchrone et le résultat est scalaire.
Le passage du conteneur entre deux tâches, le conteneur
mutable et les résultats empruntés restent ouverts.


### Tableau partagé relayé par une tâche parent

Une tâche qui reçoit `&[&Int; N]` peut le transmettre à un enfant
de même type. Le parent conserve le prêt pendant l’attente,
que l’enfant soit exécuté par await direct ou sur un autre
thread. La sortie du parent avec le handle encore actif
est refusée. Un tableau de longueur incompatible est rejeté
avant émission du C.

Quatre tests ciblés passent. Le C généré à `-O2` sous UBSan
fatal affiche `16` pour les deux chemins d’attente. L’échec
simulé du lancement de l’enfant affiche `107` et le parent
peut encore lire le tableau. Le drop d’une cible côté main
avant join est refusé. La mutation qui omet le prêt de
l’enfant accepte une sortie sans attente et le test la détecte.
Les 94 tests du cycle précédent ont terminé avec succès.
Le conteneur mutable, les formes imbriquées et les résultats
empruntés restent à traiter.


### Tableau plat de références mutables prêté à une tâche

Une tâche peut recevoir `&mut [&mut Int; N]`, le réemprunter
pour un enfant et écrire dans l’Int ciblé après yield. Le
parent retrouve son accès après await. L’appelant retrouve
le tableau et observe la mutation après join.

Quatre tests ciblés passent sous UBSan fatal. Les deux chemins
observés affichent `14, 9` et `19, 12`. Un indice hors limites
est diagnostiqué. Pendant le prêt, une lecture prématurée
dans le parent et une lecture, une écriture ou un échange
dans l’appelant sont refusés. La mutation qui enregistre le
prêt enfant comme partagé fait accepter la lecture du parent
et le test la détecte. La suite figée du cycle précédent a
terminé avec 224 tests réussis.

L’écriture exercée vise les Int référencés. Le remplacement
des références dans le corps async, les formes imbriquées
et les résultats empruntés restent ouverts.


### Réemprunt d’une cible stockée par une tâche enfant

Une tâche parent peut transmettre `&mut *row[i]` à un enfant.
Le C vérifie l’indice puis transmet l’adresse de l’Int.
L’emprunt reste actif avant await et jusqu’au dernier usage
de la référence rendue par l’enfant. Le parent retrouve alors
l’accès au tableau.

Trois tests ciblés passent sous UBSan fatal. Les deux indices
valides modifient chacun la cible sélectionnée et l’indice
hors limites est diagnostiqué. Les accès prématurés au tableau
sont refusés avant et après await. La mutation qui supprime
le prêt du résultat permet un accès prématuré après await
et le test la détecte.

Le parent réserve le tableau entier quand la case porte une
capacité mutable. Le code du parent ne connaît pas la filiation
des références injectées dans les cases. Les projections
disjointes qui nécessitent cette preuve et le retour d’un
emprunt hors du parent restent à traiter.


### Retour d’un prêt issu d’un tableau de références

Une tâche peut retourner `&*row[i]` ou `&mut *row[i]` depuis
un paramètre tableau plat de références. Le relais par await
conserve le chemin. Au join, le résultat retient la cible et
la filiation de la référence stockée. L’indice constant
libère les autres cases. L’indice dynamique retient toutes
les cibles possibles.

Trois tests ciblés passent sous UBSan fatal. Les variantes
exercent la modification d’une cible voisine après join, le
remplacement d’une case partagée, l’écriture par le résultat
mutable et le rejet de l’accès à la case encore prêtée. Une
mutation qui ignore l’indice constant fait refuser l’écriture
valide sur la cible voisine et le test la détecte.

Le contrat d’une fonction synchrone qui reçoit le tableau,
joint elle-même le worker et retourne le prêt manque encore
de provenance par case. Le compilateur refuse explicitement
ce retour. Les tableaux imbriqués et ce contrat restent
ouverts.


### Retour synchrone après création directe et join

Une fonction synchrone peut créer une tâche à partir d’un
tableau plat de références, joindre le worker puis retourner
le prêt. Le contrat projette le résultat sur la case, et un
relais synchrone conserve cette provenance. L’indice constant
libère la cible voisine. L’indice dynamique conserve toutes
les cibles possibles. La référence de secours du bras Err
participe aussi aux provenances possibles.

Quatre tests ciblés passent sous UBSan fatal. Le nouveau test
observe `9` sur Ok et `12` avec EAGAIN, puis `15` lors de
l’écriture via le résultat mutable. Les accès prématurés à
la case sélectionnée et à la cible de secours sont refusés.
La mutation qui conserve toutes les cases pour l’indice
constant fait échouer l’accès valide à la cible voisine.
Les 93 tests élargis du cycle précédent ont terminé avec
succès. Le cas où une fonction crée la tâche via une fabrique
synchrone distincte avant de la joindre reste ouvert.


### Retour de prêt après join d’une tâche issue d’une fabrique distincte

Le contrat projette le résultat futur sur les cases possibles
d’un tableau de références transmis par une fabrique. Un relais
de la tâche par transfert conserve ces origines. Si la fabrique
remplace une case avant la capture, la projection utilise l’état
mis à jour. Le contrat conserve aussi la représentation du prêt
comme pointeur vers l’Int, y compris si la case mise à jour
provient d’un paramètre scalaire.

Quatre tests ciblés passent sous UBSan fatal. Le cas combiné
affiche `9, 12` et permet de modifier l’ancienne cible. Les
variantes d’indice constant et dynamique vérifient la réserve
de la cible ou de toutes les cibles possibles. La mutation
qui omet la mise à jour des cases fait échouer le test. Une
nouvelle suite async, tableaux fixes et lignes imbriquées
tourne sur une copie figée. Les conteneurs imbriqués capturés
en entier et les résultats agrégés restent ouverts.


### Tableau de références à lignes inline capturé en entier

Une tâche peut capturer un tableau imbriqué dont les lignes
sont stockées inline. Le C utilise les types de stockage du
compilateur à chaque dimension. Le contrat préserve les
coordonnées complètes au retour du prêt et les applique
aussi à travers une fabrique et un join synchrones.

Quatre tests ciblés passent sous UBSan fatal. Pour un indice
dynamique sur la première dimension et constant sur la
seconde, les deux exécutions affichent `9` et `13`. Les
cibles de l’autre colonne sont accessibles, celles de la
colonne empruntée restent protégées. Un indice hors limites
est diagnostiqué. La variante mutable écrit via le résultat
et affiche `21`. Une mutation qui ignore la seconde
coordonnée fait refuser l’accès valide à une cible voisine.

Les tableaux de pointeurs vers des lignes, le passage d’une
projection de ligne à une autre tâche et les agrégats
retournés restent à couvrir.


### Ligne inline transmise à une tâche enfant

Un parent peut prêter une ligne de son tableau imbriqué de
références. Le C vérifie l’indice avant de transmettre
l’adresse de la sous-structure. Le chemin du prêt renvoyé
par l’enfant compose le chemin de la ligne et celui de la
case. Cette provenance traverse await, la fabrique et join.

Quatre tests ciblés passent sous UBSan fatal. Le test étendu
observe `9` et `13` pour les deux lignes partagées et
diagnostique l’indice hors limites. La variante mutable
écrit via le résultat et affiche `21`. Elle refuse une
lecture du parent pendant le prêt. Une mutation qui omet
le préfixe du chemin fait échouer le test sur un accès
valide à une cible voisine.

Pendant l’attente, le parent réserve le tableau entier
pour un prêt mutable, faute de preuve de la filiation des
capacités stockées. Les lignes elles-mêmes référencées
restent à traiter.


### Capture async d’un tableau de lignes référencées

Une tâche peut capturer un tableau dont les cases contiennent
des références vers des lignes. Le C suit les pointeurs entre
les dimensions. La capture conserve les prêts du conteneur,
des lignes intermédiaires et des Int. Après join, le résultat
ne garde que les cibles compatibles avec son chemin. Le
contrat de retour synchrone traverse aussi les lignes.

Trois tests ciblés passent sous UBSan fatal. Les deux indices
valides lisent `7` et `9`, l’indice hors limites est diagnostiqué
et le résultat mutable permet d’écrire `12`. Le drop de chaque
cible et le remplacement d’une case dans une ligne intermédiaire
sont refusés pendant la tâche. La mutation qui omet la réserve
des lignes intermédiaires accepte le remplacement interdit et
le test la détecte. La suite figée du cycle précédent a terminé
avec 230 tests réussis.

Les cas testés ont un mode homogène le long du chemin.
La composition de références partagées et mutables dans un
même chemin et les résultats agrégés restent ouverts.


### Chemins de références aux modes mixtes

Les tableaux empruntés par une tâche peuvent contenir un
chemin mêlant références partagées et mutables. Le compilateur
vérifie chaque lien avant une écriture ou un réemprunt mutable.
Un résultat partagé issu d’une capacité mutable garde la
réservation de cette capacité jusqu’au dernier usage.

Quatre tests ciblés passent sous UBSan fatal. Les deux formes
mixtes lisent la valeur avant et après la fin du prêt et
affichent `7, 7`. La lecture directe de la cible mutable est
refusée pendant l’usage du résultat. Le compilateur rejette
l’écriture et le prêt mutable à un enfant à travers une ligne
partagée. Retirer le contrôle des liens fait accepter une
écriture interdite et le test le détecte.

Une suite figée async, tableaux fixes et lignes imbriquées
tourne. La réaffectation des références dans un corps async
et les résultats agrégés restent ouverts.


### Tableaux vides prêtés et relayés entre tâches

Un `let` synchrone annoté fournit désormais le type de contexte
à `[]` pour les tableaux Int et les tableaux de références.
Le passage à une tâche accepte le stockage C vide, et un
relais ne construit pas de pointeur typé vers des éléments
absents. Les deux variantes affichent `0` sous UBSan fatal.
L’indexation et les annotations de longueur incompatible
sont refusées. Les 71 tests ciblés et de tableaux fixes passent.

Le contre-exemple initial produisait un accès au membre
`data` inexistant dans le C généré. La mutation qui rétablit
cet accès échoue à la compilation C et le test la détecte.
Le typage contextuel des littéraux vides imbriqués côté
synchrone reste partiel.


### Typage contextuel des lignes vides d’un littéral imbriqué

Le type attendu d’un tableau est propagé aux littéraux des
lignes qui le composent. Les formes `[[Int; 0]; 2]` et
`[[&Int; 0]; 2]` acceptent `[[], []]`. Une ligne projetée
peut être prêtée à une tâche puis relayée, et son `len()`
affiche `0` sous UBSan fatal. Si la ligne attendue a une
longueur non nulle, le compilateur refuse le littéral vide.

La mutation qui retire le contexte fourni aux sous-littéraux
reproduit le rejet injustifié du programme valide. La suite
des tableaux fixes et des lignes imbriquées exerce aussi
les littéraux existants. Les résultats agrégés async et les
effets de réaffectation async restent ouverts.


### Retour explicite de tableaux imbriqués à lignes vides

L’analyse des contrats propage désormais le type déclaré du
résultat jusque dans les lignes vides de `return <- [[], []]`.
Une variable locale annotée fournit le même contexte lorsqu’elle
est ensuite transférée. Le contre-exemple concernait les
tableaux de références, que le contrat classait comme des
tableaux de valeurs.

Les variantes Int et références retournées directement ou
via une variable sont prêtées à une tâche et affichent `0`
sous UBSan fatal. Le test vérifie aussi le refus d’une ligne
vide dont le type attendu a une longueur non nulle. Supprimer
le contexte de retour reproduit le rejet injustifié de la
variante à références. Les suites précédentes ont terminé
avec 91 et 233 tests réussis.


### Littéral imbriqué vide fourni en argument

La signature fournit le contexte à `[[], []]` passé par
valeur, ou par transfert explicite pour les tableaux de
références mutables. L’analyse des sources et le contrat
de résultat utilisent le même contexte que l’émission C.

Le test fait circuler les trois formes, Int, références
partagées et références mutables, à travers deux fonctions
puis une tâche. Chaque exécution affiche `0` sous UBSan fatal.
Une longueur incompatible ou l’absence de transfert pour
la forme mutable est refusée. Supprimer le contexte des
arguments dans l’analyse des sources reproduit le rejet
des programmes valides à références et le test le détecte.


### Emprunt temporaire d’un littéral imbriqué

La signature d’un appel synchrone donne le type aux lignes
vides de `&[[], []]` et de `&mut [[], []]`. Le vérificateur
utilise la représentation des emprunts temporaires existante.
Un résultat qui conserve ce prêt ne peut être stocké dans
une liaison après l’instruction.

Les quatre exécutions sous UBSan fatal, valeurs et références
en modes partagé et mutable, affichent `2`. Les longueurs
incompatibles et les deux tentatives de conserver le prêt
sont refusées. La mutation qui retire le contexte lors de
la construction du temporaire fait échouer le test.
La suite du cycle précédent a terminé avec 119 tests réussis.


### Littéraux imbriqués vides dans une expression if

Le type attendu d’une liaison ou d’un retour explicite est
transmis aux branches du if dans l’analyse de provenance,
l’analyse des sources et l’émission C. Chaque branche qui
fournit un tableau exige encore `<-`.

Les variantes Int et références passent sous UBSan fatal.
Le test exécute les deux branches pour la liaison annotée
et le retour direct, puis prête une ligne de chaque résultat
à une tâche. Les longueurs incompatibles et l’absence du
transfert sont refusées. La mutation qui retire le contexte
de branche reproduit le rejet du littéral valide.
Les 119 tests du cycle précédent ont terminé avec succès.


### Littéraux imbriqués vides dans les break d’une boucle

Le type attendu de la boucle est transmis à chaque `break`
qui fournit son résultat. L’analyse des sources et des
provenances utilise ce contexte à chaque itération. Un
`continue` conserve la reprise sans fournir de résultat.
Le transfert du tableau reste explicite.

Le test exerce les deux sorties après une reprise, pour des
tableaux Int et de références. La liaison annotée et le
retour direct produisent chacun deux lignes de longueur zéro
sous UBSan fatal. Les variantes avec une longueur différente
ou un transfert manquant sont refusées. Retirer le contexte
au moment d’émettre le break fait rejeter les programmes
valides et le test détecte la mutation.


### Littéraux imbriqués vides dans les bras de match

Le type attendu atteint les bras d’un match sur enum et sur
résultat de join. Il est transmis par l’analyse des sources,
les contrats et l’émission C, y compris quand le match est
abaissé en conditionnelles. Les bras qui fournissent un
tableau conservent le transfert explicite.

Le test sous UBSan fatal observe `7, 2` sur Ok et `9, 2`
avec EAGAIN. La variante enum affiche `2`. Une longueur
incompatible et un transfert manquant sont refusés.
Supprimer le contexte du match abaissé reproduit le rejet
du littéral valide. La suite élargie du cycle de boucle a
terminé avec 132 tests réussis.


### Littéral tableau transféré depuis un bloc enfant

Le receveur fournit le type au littéral `{ <- [[], []] }`
dans les analyses et dans le C généré. Le transfert direct
du littéral applique le même contrôle de durée de vie que
le transfert d’une variable tableau. Les cibles de toutes
les références doivent survivre dans le scope parent.

Le test sous UBSan fatal affiche `2` pour les formes Int et
références, et `7` quand une référence vise le tableau du
parent. Une longueur incompatible ou une référence vers
un tableau local au bloc est refusée. La mutation qui retire
le contrôle de durabilité laisse sortir la référence locale
et le test la détecte. La suite élargie du cycle match a
terminé avec 119 tests réussis.


### Tableau Int imbriqué prêté depuis une fonction synchrone

Le prêt accepte le tableau imbriqué entier. Le C reçoit
l’adresse du stockage et calcule les décalages en octets à
partir des dimensions. Une assertion C vérifie la taille
du stockage synchrone pour les formes non vides. Les
captures depuis un état async utilisent les mêmes
décalages sur leurs tableaux natifs.

Quatre tests ciblés passent sous UBSan fatal. Le nouveau
programme relaye le prêt, échange deux lignes, modifie une
case et restitue une autre case via join. Il refuse les
accès prématurés et autorise la ligne distincte après join.
Une première mutation du pas mémoire a survécu car le
programme écrasait la valeur observée. Le test renforcé
fait dépendre la sortie de la copie de la seconde ligne
et détecte la mutation. La suite figée élargie est en cours.


### Modèle indépendant du remplacement et de l’échange de lignes

Un modèle Python sur listes calcule l’ancienne ligne,
l’échange et les valeurs finales pour trois formes non
carrées. Le même worker reçoit le tableau depuis le C
synchrone puis depuis un état async. Les deux résultats
et chaque case observable côté synchrone sont comparés
au modèle sous UBSan fatal. Un indice hors bornes est
aussi exercé.

Trois tests ciblés passent. La mutation qui remplace la
largeur d’une ligne par la taille d’un seul Int produit
des sorties incompatibles avec le modèle et le test la
détecte. Ce modèle couvre ces opérations et ces formes.
Les résultats agrégés contenant des références et les
effets sur les références stockées restent ouverts.


### Capture scalaire Bool

Un paramètre Bool est copié lors de la création de la tâche.
Il peut être testé dans une condition et transmis à une
tâche enfant. L’analyse conserve la distinction avec Int,
même si les deux modes utilisent un scalaire C.

Deux tests ciblés passent. Sous UBSan fatal, la capture de
true affiche `7` malgré l’affectation de false à la variable
d’origine, et la capture de false affiche `9`. Int comme
argument Bool, Bool en arithmétique et comparaison ordonnée
de Bool sont refusés. La mutation qui permet à Int de
satisfaire le paramètre Bool est détectée. Les résultats
Bool et les liaisons Bool locales aux corps async restent
à traiter.


### Liaisons Bool locales à une tâche

Le corps d’une tâche peut déclarer un Bool local par
annotation ou inférence. La valeur est conservée à travers
yield. Une affectation à une liaison mutable conserve son
type. En sortie de bras, le type de la liaison locale est
retiré avec son nom.

Trois tests ciblés passent sous UBSan fatal. Le cas ajouté
réaffecte un Bool après suspension, le transmet à une tâche
enfant et réutilise un nom de bras pour un Int. Il affiche
`12`. Les annotations incompatibles, l’affectation d’un Int
et l’affectation à une liaison immuable sont rejetées.
La mutation qui laisse le type Bool attaché au nom après
la sortie du bras est détectée. Les résultats Bool par
await et join restent ouverts.


### Résultat Bool rendu par await

Une tâche inactive peut renvoyer un Bool à son parent.
Le parent peut relayer le résultat, le recevoir dans une
liaison ou le tester directement dans une condition. Le
compilateur conserve son type à travers la suspension.

Trois tests ciblés passent sous UBSan fatal. Les valeurs
true et false conduisent à `7` et `9`. Retourner un Int,
recevoir le Bool dans une liaison Int et comparer avec
un Int sont refusés. Une mutation qui remplace le résultat
par false fait échouer le test. Le lancement sur un thread
d’une tâche à résultat Bool est explicitement refusé en
attendant la prise en charge du Result de join.


### Résultat Bool après lancement sur un thread

Le runtime réutilise son transport scalaire. Crust conserve
le type Bool du résultat dans le bras Ok de join et de await
sur un handle. Un Result nommé dans le parent garde le type
jusqu’au match.

Trois tests ciblés passent sous UBSan fatal. Le programme
affiche `7, 9` en cas de succès et `7, 11` quand le lancement
de l’enfant échoue avec EAGAIN. L’usage arithmétique du Bool
et le motif Ok(()) sont refusés. Supprimer le type Bool du
bras Ok async fait échouer le test. La suite figée élargie
est en cours.


### Résultats Bool à travers if, match et await calculé

Un résultat attendu Bool est propagé aux branches d’un if
et aux bras d’un match de handle. Chaque branche qui fournit
une valeur est vérifiée. Une tâche à résultat Bool choisie
par if peut aussi être attendue dans un retour Bool.

Quatre tests ciblés passent sous UBSan fatal. Les deux
branches avec suspension conduisent à `7` et `9`.
Les variantes avec un Int dans une branche ou dans Err
sont rejetées. Omettre le contexte Bool dans l’émission
des branches fait échouer le test. Les expressions de
contrôle Bool de ce cycle utilisent le type attendu
d’une liaison ou d’un retour. Leur inférence sans contexte
reste à couvrir.


### Inférence des résultats scalaires des branches async

Une liaison async sans annotation déduit le type scalaire
de son if ou de son match. Les valeurs sont vérifiées dans
le scope de leur bras, ce qui permet de retourner un Bool
local au bras après await. Les branches qui continuent
doivent fournir le même type scalaire.

Trois tests ciblés passent sous UBSan fatal. Les variantes
sans annotation affichent `7` et `9`. Les jonctions entre
Bool et Int sont refusées pour if et match. Une mutation
qui retire le contrôle commun fait accepter un programme
interdit et le test la détecte.


### Boucle async à résultat Bool

Une boucle async peut produire un Bool dans une liaison
annotée ou inférée, ou directement dans un retour Bool.
Les break qui fournissent un résultat doivent conserver
le même type. Une reprise par continue ne fournit aucune
valeur.

Quinze tests ciblés passent. Le nouveau test sous UBSan
fatal exerce les deux sorties après continue, dont une
qui attend une tâche avant de produire son Bool. Il
refuse le mélange Bool et Int et une annotation Int.
Une mutation qui marque tous les break scalaires comme
Bool fait accepter le mélange interdit et le test la
détecte.


### Inférence du type des opérandes d’une condition async

Une comparaison peut recevoir des résultats Bool d’un if,
d’une boucle ou d’une tâche calculée. Les deux opérandes
sont évalués de gauche à droite. Le premier est sauvegardé
avant les suspensions du second. Bool accepte l’égalité et
l’inégalité, avec un type compatible sur les deux côtés.

Le test sous UBSan fatal observe les traces `1, 3, 7` et
`2, 4, 9`. La comparaison ordonnée de Bool et une branche
de type différent sont refusées. Une mutation qui évalue
le second opérande en premier inverse les deux premiers
événements et le test la détecte. La suite figée précédente
a terminé avec 273 tests réussis.

### Capture immédiate d’un octet par valeur

AS2 accepte une expression synchrone de type u8, notamment un
indice d’octet sur une chaîne. Le frame conserve cet octet dans un
champ C `uint8_t`. Une tâche peut relayer son paramètre u8 à une
autre tâche. Les appels synchrones et async exigent le type exact,
comme les appels synchrones existants à un paramètre u8.

`python3 -m unittest discover -s tests -p test_async_runtime.py -k async_byte`
a exécuté un test. Son oracle C11 à `-O2` sous UBSan fatal observe
169 dans le frame enfant après `yield`, après la réaffectation de
la vue source et le lancement sur un thread. Il vérifie aussi le
résultat Int du join. Quatre variantes sont refusées, dont la
capture par emprunt Int et l’utilisation de l’octet dans un calcul
Int. Dans une copie temporaire, remplacer la valeur relayée par
zéro déclenche l’assertion native. Mutation détectée.

Les liaisons locales u8 et les retours u8 dans les corps async
restent à couvrir. L’oracle lit le frame instrumenté parce que ce
sous-ensemble ne permet pas encore de retourner l’octet.

### Liaisons locales et sorties de boucle u8

Une liaison locale peut conserver une valeur u8 nommée, avec ou
sans annotation. Une liaison mutable accepte une autre valeur u8.
Les break qui produisent un résultat u8 conservent ce type à la
sortie de la boucle. Les expressions Int et les captures par
emprunt Int refusent ces liaisons.

`python3 -m unittest discover -s tests -p test_async_runtime.py -k async_local`
a réussi ses trois tests. Le scénario u8 vérifie sous UBSan fatal
qu’une liaison locale conserve son octet pendant yield, qu’une
réaffectation le propage au résultat de boucle puis au frame
enfant, et qu’un même nom peut redevenir Int hors du bloc.
Six variantes vérifient le typage, la mutabilité et la portée.
Une mutation temporaire qui omet d’effacer le type u8 en fin de
bloc fait échouer le programme valide à la compilation. Mutation
détectée.

Les retours u8 de fonctions async, leur réception via await ou
join et la couverture des expressions u8 composées restent à
traiter. La suite globale démarrée au cycle précédent porte sur
l’état antérieur à ces modifications.

`python3 -m unittest discover -s tests -p test_async_runtime.py -k loop`
a également réussi ses neuf tests.

### Résultat u8 par attente directe et par handle

AS10 utilise un emplacement C `uint8_t` pour extraire le résultat
avant de récupérer le slot du frame. Le même type est conservé
lors de l’attente directe, de l’attente suspendue sur un handle
et du join bloquant. Les branches scalaires inférées peuvent
produire un u8, avec vérification du type de chaque branche.

`python3 -m unittest discover -s tests -p test_async_runtime.py -k async_byte`
a réussi ses deux tests. Le scénario de retour exerce une chaîne
de trois fonctions async. L’oracle C11 à `-O2` sous UBSan fatal
observe 169 après le join. Avec EAGAIN simulé sur le lancement
interne, il observe l’octet de secours 97. Avec EAGAIN sur le
lancement externe, seul le bras Err s’exécute. Quatre variantes
vérifient le refus des confusions entre u8 et Int. Une mutation
temporaire qui met à zéro l’octet restitué par le join bloquant
est détectée par l’oracle natif.

`python3 -m unittest discover -s tests -p test_async_runtime.py -k bool`
a réussi ses sept tests. Ces vérifications ciblent les chemins
de restitution scalaires et les deux échecs de lancement.
La suite globale démarrée lors du cycle de capture u8 porte
sur une version antérieure.

### Un emprunt Int préserve le type de la cible

Deux contre-exemples ont été reproduits avant correction. Depuis
une fonction async, `read(&flag)` acceptait un paramètre Bool
comme &Int. De même, `write(&mut local)` acceptait une liaison
mutable inférée Bool comme &mut Int. Le champ C du Bool utilisait
le même type physique que le champ Int, ce qui permettait même
au second appel d’y écrire 42. La vérification de la capture
contrôle désormais le type Crust avant de prendre l’adresse.

`python3 -m unittest discover -s tests -p test_async_runtime.py -k bool`
a réussi ses huit tests. Le scénario ajouté exerce l’écriture
puis la lecture d’un Int local avec deux suspensions, sous
C11 à `-O2` et UBSan fatal. Les variantes Bool sont refusées
avant génération du C. Une mutation temporaire qui restaure le
contrôle réservé au u8 fait accepter les deux variantes.
Mutation détectée. La couverture concerne les captures
d’emprunts Int depuis des liaisons scalaires nommées.

### Retour u8 à travers un contrat de handle synchrone

`python3 -m unittest discover -s tests -p test_async_runtime.py -k byte_join`
a réussi le test de composition entre AS5, AS10 et MT5. Une
fonction lance la tâche et transfère son handle. Une seconde
consomme le handle et retourne l’octet. L’oracle C11 à `-O2` sous
UBSan fatal lit la valeur dans le frame d’un autre worker après
yield. Il observe 169 après un lancement réussi et 97 après
EAGAIN simulé sur le premier lancement uniquement.

Trois variantes sont rejetées. Elles exigent un Int du contrat
u8, donnent des types différents aux bras du match ou réutilisent
le handle transféré. Une mutation temporaire qui lit le statut
du join au lieu de l’octet fait échouer l’oracle. Ce scénario
ajoute une preuve de composition à l’implémentation existante
et ne couvre pas les autres types de résultat.

### Capture et relais d’un char Unicode

AS2, AS8 et TX2–TX3 sont exercées par un char décodé en
synchrone, capturé au lancement, relayé à une autre tâche et
utilisé après yield. Le frame et les arguments C conservent
le type CrustChar. Le corps async calcule la largeur UTF-8
avec utf8_len.

`python3 -m unittest discover -s tests -p test_async_runtime.py -k async_char`
a réussi. L’exécution C11 à `-O2` sous UBSan fatal observe les
quatre largeurs 1, 2, 3 et 4. Six variantes sont refusées,
dont la capture d’un octet comme char, l’emprunt comme Int et
la réaffectation d’un Int à un paramètre char. Une mutation
réduisant le type C à un octet produit 1, 2, 2 et 1 et le test
la détecte. Le test synchrone ciblé `-k char_at` dans
`test_foundation_rules.py` a également réussi.

L’oracle observe les largeurs, pas tous les points de code.
Les liaisons locales et la restitution async de char restent
à couvrir. Les suites élargies en cours couvrent des révisions
antérieures.

### Char dans les liaisons locales et les expressions de contrôle

Une valeur char peut être copiée dans une liaison locale annotée
ou inférée, traverser yield et être réaffectée dans une liaison
mutable. Les résultats de if, match et loop inférés gardent leur
type dans leur temporaire C. Le test char exerce if et loop et
la réutilisation du nom d’une liaison locale comme Int après son bloc.

Les filtres `-k async_local` et `-k condition` de
`test_async_runtime.py` ont réussi, respectivement quatre et
deux tests. L’oracle C11 à `-O2` sous UBSan fatal observe la
largeur UTF-8 de 4 et ajoute l’Int de la nouvelle liaison.
Cinq variantes testent le rejet de types incompatibles. Omettre
l’effacement du type char à la sortie du bloc dans une copie
temporaire fait rejeter le programme valide. Mutation détectée.

La suite async élargie lancée pendant le cycle des retours u8
s’est terminée avec 162 tests réussis sur sa révision de départ.
Les résultats char à travers await ou join restent ouverts.

### Restitution d’un char à travers les attentes

AS10 restitue le char depuis un emplacement du type CrustChar
pour await direct. Le résultat de handle transporte le point
de code dans un champ uint32_t. Le match le restitue comme char
dans le corps async ou dans la fonction synchrone.

Les filtres `-k async_char` et `-k async_byte` de
`test_async_runtime.py` ont réussi, deux tests chacun.
Le nouveau scénario C11 à `-O2` sous UBSan fatal observe
le caractère 🌍 après deux attentes directes, une attente de
handle et un join bloquant. Un échec simulé du lancement externe
emprunte le bras Err. Trois variantes sont refusées pour
confusion entre char, u8 et Int. Une mutation qui tronque le
résultat du join à uint8_t fait perdre le caractère et le test
la détecte. Les tests ciblés n’exercent pas la restitution char
à travers toutes les formes de transfert de handle.

Les 27 tests de `test_function_bodies.py` ont également réussi.
La suite globale lancée lors du cycle de capture u8 signale une
erreur intermédiaire. Son rapport détaillé est attendu en fin
d’exécution.

### Affichage d’un char dans un corps async

TX20 s’applique aux char dont la valeur est disponible après
une suspension. Le générateur choisit le même encodeur que pour
le print synchrone, à partir du type de l’expression. Les
formes instruction et expression utilisent la même vérification.

Les filtres `-k async_char` et `-k async_byte` de
`test_async_runtime.py` ont réussi, deux tests chacun. Sous
UBSan fatal, le test char imprime 🌍 depuis un bras de if,
directement depuis await, puis depuis le résultat de join.
Il refuse Bool comme argument de print et une seconde attente
du même receveur. Une mutation temporaire substituant l’affichage
numérique produit 127757 deux fois et est détectée. L’affichage
de vues &str depuis les corps async reste à couvrir.

### Vues de littéraux UTF-8 dans une tâche

TX1, TX3, TX20 et AS2 sont exercées pour les vues de littéraux.
Le frame garde le descripteur CrustText et peut le relayer à
une autre tâche. Le stockage des littéraux est statique, y
compris pour les littéraux écrits dans le corps async. Le
descripteur garde la longueur en octets et print conserve les
NUL incorporés.

`python3 -m unittest discover -s tests -p test_async_runtime.py -k async_static_text`
a réussi sous UBSan fatal à -O2. La trace vérifie deux chaînes
avec NUL, la seconde après yield, et une longueur de quatre octets.
Trois variantes sont refusées, dont une vue empruntée à un
String. Une mutation temporaire qui tronque le littéral async
au premier NUL est détectée. Les appels synchrones exigent un
littéral direct pour cette capture. La provenance statique
indirecte et les emprunts de vues dynamiques restent ouverts.

La suite globale de capture u8 s’est achevée avec 1 518 tests
et une seule erreur. Le rapport identifie ScopeRecorder,
corrigé au cycle G6–G7. La nouvelle suite globale figée est
en cours sur sa révision de départ, qui précède ce changement.

### Liaisons locales et découpes de vues statiques

Une tâche peut lier ou réaffecter une vue de littéral et en
capturer une découpe dans une autre tâche. Le descripteur est
sauvegardé avant l’évaluation des bornes. Les bornes sont
préparées de gauche à droite et le runtime vérifie la découpe.
Le compilateur partage les vérifications de bornes connues
avec le chemin synchrone.

Le filtre `-k async_static_text` de `test_async_runtime.py`
a réussi deux tests sous UBSan fatal. Le nouveau scénario
observe la trace 1, 3, é, 6 et provoque un arrêt diagnostiqué
sur une borne dynamique au milieu de é. Le compilateur
refuse la même frontière sur un littéral à borne connue, une
réaffectation Int et une capture du nom réutilisé comme Int.
Une mutation omettant la sortie lexicale du type &str est
détectée. Le filtre `-k utf8_slice` de
`test_foundation_rules.py` a réussi trois tests synchrones.

Les captures synchrones de vues indirectes et les emprunts
depuis un stockage dynamique restent ouverts.

### Capture d’une vue statique nommée depuis une fonction synchrone

La provenance statique est reconnue à partir d’un littéral,
d’une découpe ou d’une liaison immuable déjà reconnue.
La preuve est attachée à la liaison lors de sa déclaration.
Un paramètre synchrone &str ne porte pas cette preuve, car
l’appelant peut lui passer une vue empruntée.

Le filtre `-k static_text` de `test_async_runtime.py` a réussi
trois tests. La nouvelle fabrique retourne une tâche qui garde
une découpe à travers deux liaisons. Sous UBSan fatal à -O2,
le worker imprime 🌍 et restitue sa longueur de quatre octets
après la sortie de la fabrique. Trois variantes sont refusées,
dont un appel transmettant un emprunt à String via un
paramètre et deux alias. Une mutation qui prend le type text
pour preuve de provenance fait accepter ce cas et le cas
mutable. Mutation détectée.

Le suivi des liaisons mutables, des résultats de fonctions
synchrones et des emprunts à un stockage dynamique reste ouvert.

### Vues statiques comme résultat de if, loop et match async

Les expressions de contrôle peuvent produire une vue statique.
Le temporaire C garde le descripteur CrustText et chaque
sortie qui continue doit fournir le même type. Une vue de
littéral peut être sélectionnée dans Err sans dépendre du
stockage du handle consommé.

Les filtres `-k static_text` et `-k control_results`
de `test_async_runtime.py` ont réussi, quatre et deux tests.
Sous C11 à -O2 avec UBSan fatal, le nouveau scénario observe
🌍 puis la longueur 4, ou é puis 2 selon la branche. Avec
EAGAIN simulé au lancement interne, il observe ! puis 1.
Trois variantes mélangent des Int avec les vues dans if,
break et match. Une mutation qui conserve le type du premier
bras sans contrôler le second fait accepter les variantes
if et match. Mutation détectée.

Les signatures de retour &str async et les vues empruntées
à un stockage dynamique restent ouvertes.

### Restitution des vues &str statiques

AS10 et TX1 restituent le descripteur CrustText entier.
L’attente directe le copie depuis le frame. L’attente de
handle et le join bloquant utilisent un champ du même type,
avec un typedef partagé entre le runtime autonome et le C
émis par le compilateur. Le stockage de la vue reste celui
du littéral lorsque le frame est rendu au pool.

Le filtre `-k static_text` de `test_async_runtime.py` a réussi
cinq tests. Le scénario de restitution a aussi été rejoué
avec deux appels successifs au même type de tâche et deux
littéraux distincts. Sous C11 à -O2 et UBSan fatal, il
observe une longueur de 1 pour la seconde vue, puis imprime
la première découpe avec son NUL incorporé. EAGAIN simulé
pour le lancement interne sélectionne la vue de secours.
Trois variantes incompatibles sont rejetées. Une mutation
qui annule la longueur au join bloquant fait disparaître
le texte et le test la détecte. Le test autonome
`-k default_thread_runner` a également réussi.

Les retours de vues sur un stockage emprunté et leur
provenance à travers les contrats restent ouverts.

### Lecture d’un octet de vue statique dans une tâche

TX5 utilise le contrôle C partagé text_byte_address. Le
descripteur du receveur est sauvegardé avant de calculer
l’indice et la lecture produit un u8. Un octet de continuation
est lisible. Le contrôle d’une découpe reste distinct.

Le filtre `-k async_text_index` de `test_async_runtime.py`
a réussi sous C11 à -O2 et UBSan fatal. Il observe 10, 20,
puis é. Le dernier résultat vient d’un replace_byte
synchrone qui réutilise l’octet restitué par join pour changer
è en é. Une borne dynamique invalide provoque un arrêt
diagnostiqué. Une borne littérale hors plage, un indice Bool
et une liaison Int sont refusés. Une mutation qui évalue
l’indice avant le receveur inverse 10 et 20 et est détectée.
Les deux tests synchrones `-k utf8_index` ont aussi réussi.

La formation et le transport d’un &u8 async ainsi que
l’indexation de vues empruntées à un stockage dynamique
restent ouverts.

### Emprunt partagé d’un octet statique

TX5 permet de former &texte[i] sur une vue dont les octets
vivent pendant toute l’exécution. La lecture u8 et l’emprunt
partagent le contrôle de l’adresse. Une liaison &u8 peut être
relayée à une tâche enfant et se lit avec * dans son corps.
La réaffectation d’une liaison mutable change l’adresse
empruntée et exige un autre &u8 statique.

Le filtre `-k async_text_index` de `test_async_runtime.py`
a réussi. Le scénario emprunté forme l’adresse après deux
suspensions, la transmet à un enfant puis observe, sous UBSan
fatal, l’octet déréférencé après yield via une mutation de
String côté synchrone. La trace reste 10, 20, é. Les variantes
qui confondent l’octet et son adresse, omettent * ou capturent
directement l’octet d’un String sont rejetées. Une mutation
temporaire qui remplace le déréférencement par zéro provoque
le bras InvalidUtf8 et le test la détecte.

Le retour async d’un &u8 et la provenance de liaisons &u8
nommées côté synchrone restent ouverts, ainsi que les
emprunts vers le stockage dynamique.

### Retour d’un emprunt statique &u8

AS10 et TX5 restituent l’adresse de l’octet dans un champ
typé. Le receveur peut relayer cet emprunt ou le déréférencer
après la récupération du frame. Les résultats &u8, u8 et
&str sont distingués par leur type à l’attente, y compris
dans les expressions de contrôle.

Le filtre `-k static_` de `test_async_runtime.py` a réussi
six tests. Le nouveau scénario emprunte des octets dans deux
littéraux distincts. Sous UBSan fatal, le résultat du handle
permet de produire è après succès et é si le lancement
interne échoue. Trois variantes de type incompatible sont
refusées. Substituer l’adresse d’un autre littéral au join
bloquant déclenche le bras InvalidUtf8 et le test détecte
la mutation. Les références vers un stockage dynamique et
leur provenance au travers des contrats restent ouvertes.

### Recapture des vues et emprunts statiques reçus par join

L’extraction de join_text ou de join_byte_ref fournit une
preuve de stockage statique. Une liaison immuable propage
cette preuve, y compris lorsqu’elle reçoit une référence
d’octet formée directement sur un littéral. Une référence
d’octet issue d’un String reste refusée à la capture.

Le filtre `-k static_` a réussi six tests dans
`test_async_runtime.py`. Le scénario &u8 a aussi été rejoué
après l’ajout du rejet de la référence nommée issue d’un
String. Les exécutions sous UBSan fatal relayent les deux
types à un autre worker. Le scénario &u8 observe è, é sur
échec de lancement interne et ê avec un emprunt de littéral
nommé. Une mutation qui retire la preuve à l’extraction
du join fait rejeter la recapture valide. Mutation détectée.

La suite globale figée lancée après le rétablissement du
test G6–G7 a réussi ses 1 525 tests. Elle précède les ajouts
de vues statiques dans les corps async. Une nouvelle suite
async figée couvre ces ajouts. Les captures dynamiques et
la propagation de la preuve par les contrats synchrones
restent ouvertes.

### Preuve statique à travers un contrat de retour synchrone

Une expression d’appel retournant &str ou &u8 peut fournir une
preuve de stockage statique. Si le contrat ne retient aucune
cible, il s’agit d’un résultat indépendant. Sinon chaque cible
doit correspondre à un paramètre de vue dont l’argument possède
déjà la preuve. La décision se fonde sur le contrat et les
arguments, sans lire le corps à ce point de l’analyse.

Le filtre `-k static_` a réussi six tests. Après ajout du retour
à deux provenances, le filtre `-k immutable_static_text` a
également réussi. Sous UBSan fatal, une fabrique capture la
découpe rendue par une fonction synchrone et le worker affiche
🌍 après la sortie de la fabrique. Le test &u8 recapture aussi
un résultat qui emprunte un octet à un argument &str statique.
Un retour pouvant provenir d’un String est refusé même si
l’autre branche fournit une vue statique. Une mutation qui
ignore les cibles du contrat fait accepter une fabrique dont
l’argument provient d’un String. Mutation détectée.

Les paramètres synchrones de provenance inconnue restent
refusés pour ces captures. Les emprunts vers un stockage
dynamique restent à suivre jusqu’à la fin de la tâche et
des usages du résultat.

### Décodage UTF-8 et match dans un corps async

TX6 et TX7 prennent en charge le match direct de char_at et
char::from_str sur une vue statique. Le décodeur C synchrone
reste commun. Pour char_at, le descripteur est enregistré
avant l’évaluation de l’indice et le résultat est conservé
dans le frame. Le match contrôle la famille d’erreurs et
n’extrait le char que dans le bras Ok.

Le filtre `-k async_char` de `test_async_runtime.py` a réussi
trois tests. Sous C11 à -O2 et UBSan fatal, le nouveau scénario
exerce Ok, NotCharBoundary et OutOfBounds après suspension
de l’indice, ainsi que les trois issues de from_str. Trois
variantes sont rejetées pour indice Bool, motif unitaire ou
familles d’erreurs mélangées. Une mutation qui remplace
l’indice par zéro fait sélectionner Ok dans les deux cas
d’erreur et le test la détecte.

Le transport d’un Result de décodage dans une liaison nommée
ou au retour d’une tâche reste ouvert. Les vues empruntées
à un stockage dynamique restent également ouvertes.

### Résultat de décodage nommé dans un état async

Les résultats de char_at et de char::from_str peuvent être
liés, copiés et conservés dans le frame. Les deux types ont
la même représentation C mais gardent leur famille d’erreurs
dans le vérificateur. Une réaffectation et les motifs d’un
match doivent respecter cette famille.

Le filtre `-k async_char_at` de `test_async_runtime.py` a
réussi. La variante nommée réaffecte un résultat Ok avec
NotCharBoundary, copie le résultat et suspend la tâche
avant le match. L’oracle C11 à -O2 avec UBSan fatal observe
le bras NotCharBoundary. Trois variantes supplémentaires
sont refusées pour incompatibilité de type ou de famille.
La mutation qui omet la comparaison des familles lors de
la réaffectation est détectée.

La suite async figée lancée après les recaptures statiques
a terminé avec 174 tests réussis sur sa révision de départ.
La restitution et la capture de Result de décodage par
signature async restent ouvertes.

### Capture par valeur d’un résultat de décodage

Les paramètres Result<char,CharAtError> et
Result<char,CharFromStrError> conservent leur famille au
passage synchrone vers async et au relais entre tâches.
Le frame reçoit une copie du résultat à la création. Le
char décodé et le statut ne retiennent aucune vue du texte.

Le filtre `-k async_decode_result` a réussi. Sous C11 à -O2
avec UBSan fatal, le test capture un résultat obtenu depuis
un String, réaffecte le résultat original, détruit le
String puis lance la tâche. Les traces sont 🌍 puis 4 avec
un indice valide et 97 sur un octet de continuation. Deux
variantes qui mélangent les familles sont refusées.
Une mutation omettant le contrôle de famille au relais
async fait accepter la seconde et le test la détecte.
Le filtre `-k scalar_body` a également réussi.

Les signatures de retour de ces résultats et leur
restitution via les handles restent ouvertes.

### Restitution des résultats de décodage

AS10 transporte le résultat de décodage complet. Le statut
de lancement du handle reste distinct du statut de décodage.
L’extraction du bras Ok externe rend au receveur le Result
interne avec sa famille d’origine. L’attente directe, le
match de handle et le join partagent le type C CrustCharResult.

Le filtre `-k async_decode_result` a réussi deux tests. Sous
C11 à -O2 et UBSan fatal, le nouveau scénario exerce Ok,
NotCharBoundary, OutOfBounds et MultipleChars. Les échecs
de lancement interne et externe sont injectés séparément.
Deux confusions de famille sont refusées. Une mutation
remplaçant le statut interne par Ok au join déclenche
l’affichage du scalaire nul et est détectée.

Le filtre `-k static_` a réussi six tests. Un scénario &u8
a ensuite vérifié la liaison d’un résultat obtenu en
attendant une tâche choisie par if. Ce chemin classait
auparavant la référence selon le nom u8 de sa cible.
La liaison suit désormais le type complet du résultat.
Les captures et restitutions de vues dynamiques restent
à couvrir.

### Capture d’une vue empruntée à un String local

AS2, AS15 et TX5 réutilisent les réservations de stockage
pour les vues &str et &u8. La capture inscrit la source
locale dans les dépendances de la tâche, puis du handle.
Le compilateur autorise cette capture lorsque le corps
async ne retourne pas de vue UTF-8 et ne crée pas de tâche
qui en reçoit. Les transferts vers un paramètre de tâche
ou de handle synchrone restent refusés pour ces captures.

Les filtres `-k dynamic_text_capture` et `-k static_` de
`test_async_runtime.py` ont réussi un et six tests. Sous
UBSan fatal à -O2, les scénarios lisent une découpe et un
octet de continuation de String après yield. La mutation
du String redevient possible après join, EAGAIN simulé ou
drop de la tâche inactive. Le compilateur refuse la
mutation avant le lancement, le drop du String avant join,
l’abandon du handle et son transfert via un paramètre.
Une mutation supprimant la dépendance à la capture fait
accepter la mutation et l’abandon prématurés et est détectée.

La vérification porte sur des sources String locales. Les
sources injectées, les relais dynamiques et la restitution
d’une vue empruntée nécessitent encore le suivi de provenance
dans les contrats.

### Relais async d’une vue dynamique avec attente de l’enfant

Une tâche peut transmettre la vue empruntée à un enfant.
Une réservation dans le vérificateur oblige à terminer
l’enfant lancé avant de quitter le parent. Elle représente
la dépendance envers le stockage du premier appelant. Une
vue issue d’un littéral direct ou d’un alias immuable
prouvé statique ne demande pas cette réservation.

La capture dynamique demeure refusée si une tâche du
relais qui reçoit une vue peut restituer une vue UTF-8.
Le compilateur vérifie ce point dans les appels async
atteignables. La provenance de résultats empruntés reste
un chantier distinct.

Le filtre `-k dynamic_text_capture` a réussi. Sous UBSan
fatal, le scénario traverse un enfant lancé et une attente
directe avant d’afficher la découpe. Le drop du handle
enfant avant son attente et un appel transitif retournant
une vue sont refusés. Une mutation supprimant la réservation
interne fait accepter le drop prématuré et le test la
détecte. Le filtre `-k static_` a également réussi ses six
tests. Les transferts de handles dynamiques aux fonctions
synchrones restent ouverts.

### Vue UTF-8 partagée d’un tableau d’octets local

Une vue validée par str::from_utf8 sur un tableau u8
local peut être capturée. Le compilateur retrouve la
liaison qui détient le tableau et réserve son stockage
pour chaque tâche. Les temporaires et les tableaux dont
le détenteur local est absent restent refusés.

Le filtre `-k async_utf8_capture` a réussi. Sous C11 à
-O2 et UBSan fatal, deux workers partagent la vue. Le
programme observe leurs deux longueurs, puis écrit dans
le tableau et affiche è après les deux joins. Deux
variantes sont refusées quand une écriture précède le
premier ou le second join. Une mutation qui omet
uniquement la seconde réservation fait accepter le
second cas et le test la détecte. Le scénario de relais
depuis un String local a également réussi.

Le transfert de handles dynamiques à une fonction
synchrone reste ouvert. Son contrat doit distinguer une
capture statique d’une réservation locale et conserver
l’obligation d’attente lors d’un transfert.

### Contraintes de source d’une capture UTF-8 jusqu’au join

Un contre-exemple a été reproduit en mode historique reset.
Une fonction synchrone recevait un String par emprunt et un
pool par emprunt mutable. Elle lançait une tâche lisant la
vue du String, réinitialisait le pool et attendait le handle.
Le contrat autorisait les deux arguments à désigner la même
source. L’analyse des contraintes conserve désormais les
réservations UTF-8 dans la valeur tâche ou handle et contrôle
leurs sources au join.

Le filtre `-k disjoint_reset_source` a réussi. Le scénario
transfère la tâche hors d’un bloc avant le lancement et
appelle la fonction via un relais synchrone. Sous C11 à -O2
avec UBSan fatal, le reset d’un pool distinct puis le reset
du même pool après join sont admis. L’alias pendant
l’exécution est refusé. Une mutation supprimant le contrôle
des réservations au join fait accepter le contre-exemple.
Mutation détectée. Le reset reste réservé au mode historique.

Les transferts de handles avec capture UTF-8 dynamique vers
des fonctions synchrones et la restitution de vues dynamiques
restent à couvrir.

### Capture depuis un paramètre synchrone &str ou &u8

Une fonction synchrone peut transmettre à une tâche une vue
ou une référence d’octet reçue en paramètre immuable et
attendre son handle. Le descripteur de provenance reste
disponible pour la capture, y compris via un alias immuable
ou un relais synchrone. Le contrat suit la source éventuelle
du paramètre. Un littéral n’ajoute aucune source de pool
à l’appel.

Sous UBSan fatal, le filtre `-k disjoint_reset_source`
exerce une vue &str injectée à travers deux fonctions.
En mode historique, le reset d’un pool distinct est admis
et celui d’un pool contenant le texte est refusé avant
join. Le même appel avec un littéral réussit. Une mutation
supprimant la provenance symbolique du paramètre fait
accepter l’alias interdit et le test la détecte. Le filtre
`-k static_` a réussi six tests, dont le relais synchrone
d’un &u8 emprunté à un String. Le filtre synchrone
`-k utf8` de `test_foundation_rules.py` a réussi 27 tests.

Les paramètres mutables, les projections supplémentaires
de ces paramètres au sein d’un appel et le retour de tâche
avec cette capture restent à couvrir.

### Projection UTF-8 depuis un paramètre synchrone

Une découpe ou un emprunt d’octet à partir d’un &str injecté
reprend le descripteur de la source. Le compilateur vérifie
l’accès à cette source avant de construire la sous-vue.
Une tâche peut donc retenir la projection pendant que le
receveur synchrone attend son handle.

Les filtres `-k static_byte_reference`, `-k disjoint_reset_source`
et `-k async_text_index` ont réussi. Sous UBSan fatal, les
scénarios exercent l’octet projeté et la découpe obtenue via
un relais synchrone. Le mode historique refuse encore le
reset aliasé avant join. Supprimer la reprise du descripteur
fait rejeter la découpe valide. Mutation détectée. Les 27
tests synchrones `-k utf8` ont réussi.

La suite async figée précédente a exécuté 179 tests avec un
échec. L’ancien test exigeait encore le rejet d’un relais &u8
dynamique désormais autorisé. Il vérifie à présent la lecture
valide et le refus de détruire le String avant join. Les deux
cas réussissent en exécution ciblée. Une nouvelle suite
figée couvre cette correction et les projections.

### Tâche et handle retournés avec une capture UTF-8 injectée

Une fabrique synchrone peut restituer une tâche capturant
un paramètre UTF-8. Un relais peut aussi lancer cette tâche
et retourner le handle. Le contrat reconstruit la
réservation à partir du stockage de l’argument réel.
Lorsque l’argument est un littéral, il ne crée pas de
réservation locale. Un emprunt sur une valeur créée dans
la fabrique reste refusé au retour.

Le filtre `-k utf8_factory` a réussi sous C11 à -O2 et
UBSan fatal. Il transfère une tâche préparée à partir
d’une découpe de String, puis le handle à son appelant.
La mutation ou la destruction du String avant join et
le drop du handle sont refusés. Le même type de tâche
créé avec un littéral peut être lancé et abandonné.
Une mutation omettant la reconstruction de la
réservation fait accepter la mutation prématurée.
Le filtre `-k static_` a également réussi six tests.

Le passage d’un handle avec cette réservation en
paramètre d’une fonction synchrone et les résultats
de vue dynamique restent à couvrir.

### Passage d’un handle à capture UTF-8 dans un contrat synchrone

Le vérificateur représente les captures UTF-8 possibles
d’un paramètre tâche ou handle. Lorsqu’un corps peut
abandonner un handle, son contrat exige l’absence de
réservation UTF-8 dynamique pour ce paramètre. Cette
précondition se propage aux appelants. Un handle retourné
par transfert conserve ses réservations réelles. Le mode
historique propage également les sources jusqu’au join.

Les filtres `-k utf8_handle_transfer` et
`-k dynamic_text_capture` ont réussi. Sous C11 à -O2 et
UBSan fatal, le scénario relaie un handle puis l’attend
dans une autre fonction. La mutation du String est admise
après le retour. L’abandon indirect et le reset aliasé
avant join sont refusés. Un littéral autorise l’abandon.
Une mutation ignorant la précondition du contrat fait
accepter l’abandon dynamique et le test la détecte.
Les 28 tests de `test_modular_calls.py` ont réussi.

La restitution d’une vue UTF-8 dynamique depuis la tâche
reste à couvrir.

### Vue UTF-8 dynamique restituée au join bloquant

AS10 et AS12 conservent les réservations UTF-8 lorsque
le handle retourne &str ou &u8. Le résultat du join
transmet le descripteur à la liaison du bras Ok. Un
contrat synchrone peut restituer cette vue à son
appelant. Le stockage reste réservé jusqu’au dernier
usage. L’analyse retient pour l’instant toutes les
captures UTF-8 possibles de la tâche.

Les filtres `-k dynamic_utf8_result` et
`-k static_byte_reference` ont réussi. Sous UBSan fatal,
la découpe d’un String passe par une fonction synchrone
qui attend le handle et l’octet dynamique est relayé
après son join. Une mutation ou un drop avant le dernier
usage est refusé. L’échec simulé du lancement restitue
la vue de secours. Une mutation qui efface la projection
du contrat fait rejeter un retour valide, car le corps
et le contrat ne s’accordent plus sur sa provenance.

La suite async figée précédente a réussi 180 tests sur
sa révision de départ. Le retour de vues dynamiques
entre tâches par attente directe ou par handle async,
et la sélection précise des seules captures nécessaires
au résultat, restent ouverts.

### Sélection des captures retenues par le résultat UTF-8

AS12 suit les noms présents dans les retours à travers
leurs déclarations et réaffectations. Le join et les
contrats synchrones retiennent les captures UTF-8
atteignables par ce suivi. Les contraintes de source
du mode historique sont également indexées par capture.
L’analyse réunit les affectations et les branches. Elle
peut conserver une capture citée dans une expression
complexe même si elle ne fournit pas l’adresse finale.

Les six tests async sélectionnés par `-k utf8_` ont
réussi. Le scénario de précision, rejoué après ajout
du cas historique, vérifie sous UBSan fatal qu’un String
simplement lu par le worker peut être détruit après
join et que le String retourné reste protégé. Une
réaffectation conditionnelle de la vue retient les
deux sources. Le reset historique de la source écartée
est admis et celui de la source retournée est refusé.
Omettre les réaffectations dans l’analyse fait accepter
la destruction d’une cible possible. Mutation détectée.

La restitution de vues dynamiques entre deux corps
async reste ouverte.

### Retour d’une vue dynamique entre tâches

Les attentes intermédiaires peuvent restituer une vue
dynamique. Le stockage UTF-8 reçu par les tâches reste
celui de l’appelant initial. La réservation du parent
couvre les enfants qu’il attend et l’analyse du retour
propage les captures possibles au join final. La
réservation interne continue d’interdire l’abandon
d’un enfant susceptible d’utiliser ce stockage.

Les filtres `-k utf8_result`, `-k static_byte_reference`
et `-k dynamic_text_capture` ont réussi. Sous UBSan fatal,
ils exercent le retour direct à la tâche parente, le
retour via un handle async, et les secours distincts
lors d’un échec de lancement interne ou externe. Le
String reste protégé après le join tant que la vue est
utilisée. Une mutation retirant l’obligation d’attente
dans un parent qui retourne &str autorise l’abandon de
l’enfant et le test la détecte.

L’analyse des noms transitifs peut conserver davantage
de captures que le résultat du seul enfant n’en exige.
La vérification de la suite async complète sur cette
révision a été lancée sur une copie figée.

### Provenance d’un résultat relayé par await

L’analyse d’AS12 compose la provenance du résultat d’une
tâche enfant avec les arguments de son appel. Elle le fait
pour un appel attendu directement et pour une tâche nommée
dont les définitions sont des appels identifiables. Lorsqu’une
définition est ambiguë, le suivi conserve tous les noms
qu’elle mentionne. En cas de cycle, toutes les captures
UTF-8 de la définition revisitée sont retenues.

Le filtre `-k utf8_result` a réussi deux tests. Les variantes
du scénario de précision détruisent le String seulement lu
par l’enfant après le join final et affichent la vue restante
sous UBSan fatal. Lorsque l’enfant peut retourner cette
seconde source après une réaffectation, la destruction est
refusée. Une mutation qui conserve tous les arguments du
relais fait rejeter la destruction valide. Mutation détectée.

La projection précise via des handles async et certaines
formes de tâche calculée reste conservatrice.

### Projection de provenance à travers un handle async

AS12 suit désormais le lancement et les transferts nommés
qui permettent de retrouver l’appel ayant créé la tâche
attendue. Le résultat du handle applique la projection
de cette tâche. Les provenances des autres bras, dont
Err, restent dans l’union du résultat. Une construction
que l’analyse ne peut pas résoudre conserve ses noms.

Le filtre `-k utf8_result` a réussi deux tests. Le scénario
de précision a ensuite été rejoué avec EAGAIN simulé sur
le lancement interne. Sous UBSan fatal, le String seulement
lu peut être détruit après le join final, y compris quand
le bras Err retourne le premier String. Si ce bras ou la
tâche enfant peut retourner le second String, sa destruction
est refusée. Une mutation omettant de suivre le lancement
conserve inutilement la seconde source et fait rejeter le
programme valide. Mutation détectée.

Les formes calculées qui ne se ramènent pas à des appels
nommés restent suivies de manière conservatrice.

### Provenance des tâches calculées

AS12 peut suivre les tâches choisies par if, match, bloc
ou loop lorsque leurs sorties donnent des appels
identifiables. La projection réunit les captures qui
peuvent contribuer au résultat sur ces sorties. Les
break d’une boucle imbriquée ne fournissent pas de
tâche à la boucle extérieure. Les formes ambiguës
gardent le suivi conservateur.

Le filtre `-k utf8_result` a réussi ses deux tests sous
UBSan fatal. Les variantes if, match, bloc et loop
permettent de détruire la capture écartée après join.
Permuter les sources dans une branche de if fait
refuser la destruction. Une mutation qui ignore la
projection du if ou confond les break d’une boucle
imbriquée fait rejeter le programme valide. Les
deux mutations ont été détectées.

La suite async figée du cycle précédent s’est terminée
avec 184 tests réussis sur sa révision de départ.

### Réaffectation d’un paramètre UTF-8 avant capture

Le vérificateur représente les paramètres synchrones mutables `&str`
et `&u8` issus d’un emprunt par le même type de liaison que les vues
locales. Une réaffectation par le nom d’un autre paramètre conserve
son descripteur. La création de tâche capture la vue alors courante.
Un remplacement conditionnel maintient l’union des provenances.

Les filtres `disjoint_reset_source` et `reassigned_parameter_source`
ont réussi. Les variantes texte et octet renvoient une tâche depuis
une fabrique synchrone, la lancent, puis exercent le reset historique
avant join. Vider le pool initial après remplacement certain est
admis et le C lit la nouvelle source après yield. Vider le nouveau
pool est refusé. Après remplacement conditionnel, vider l’un ou
l’autre pool est refusé. Les exécutions acceptées utilisent clang
en C11 à O2 avec UBSan fatal. Les suites des corps de fonctions et
des contraintes ont chacune réussi 27 tests. Le filtre UTF-8
des règles fondamentales a réussi 27 tests.

Sur copie temporaire, omettre la liaison empruntée à l’entrée
est détecté par `disjoint_reset_source`. Omettre la provenance
du paramètre à droite de l’affectation est détecté par
`reassigned_parameter_source`. Les deux mutations rejettent
un programme valide. Le premier mutant survit au seul test
de réaffectation, puisque la provenance est reconstruite lors
de celle-ci.

Cette passe couvre les paramètres à provenance empruntée.
Le suivi des liaisons mutables dont la provenance peut alterner
entre stockage statique et stockage emprunté reste à vérifier.

### Réaffectation entre littéral et emprunt UTF-8

AS2 et AS15 utilisent la provenance de la vue au moment de la
capture. Un littéral n’ajoute aucun prêt. Une jonction où seul un
chemin garde une vue empruntée maintient ce prêt. Si tous les chemins
produisent des vues statiques, la jonction en conserve la preuve.
Le suivi des boucles tient compte de cette preuve à son point fixe.
Une liaison mutable initialisée avec un paramètre emprunté conserve
son descripteur, comme lors d’une réaffectation depuis ce paramètre.

Le filtre async UTF-8 a réussi neuf tests. Le filtre des alias de
littéraux a réussi un test, avec une variante mutable. Le filtre
UTF-8 des règles fondamentales a réussi 27 tests. Les cas ciblés
lisent la vue après yield sous clang C11 à O2 et UBSan fatal.
Le reset historique est admis quand chaque chemin a réaffecté un
littéral. Quand la vue empruntée reste possible, les deux valeurs
de la condition donnent le résultat attendu sans reset, et le
reset est refusé pour les deux. Une réaffectation après capture
laisse le prêt initial actif jusqu’au join. Le filtre des contrats
de reset a aussi été rejoué après l’ajout de l’alias mutable.

Sur copie temporaire, supprimer la propagation de la preuve
statique à la jonction fait rejeter la fabrique qui remplace
l’emprunt par un littéral dans chacun des bras. Mutation détectée.
Le scénario a aussi été rejoué avec une sortie obligatoire de
`loop` et un `while` dont le corps peut ne jamais s’exécuter.
Le reset est admis après le `loop` et refusé après le `while`.
Les cycles avec plusieurs reprises et des vues UTF-8 restent à
exercer dans cette combinaison.

### Capture d’une vue calculée et reprise par continue

Deux écarts corrigés. Un bras de if qui fournissait le nom
d’un paramètre immuable pouvait perdre sa provenance. Quand
l’autre bras fournissait un littéral, la capture était alors
refusée. La reconstruction des dépendances d’une tâche renvoyée
par contrat omettait aussi la vue passée comme paramètre mutable
canonique. L’ancien test par reset historique pouvait masquer
ce second défaut grâce à une contrainte de source distincte.
Le nouveau test effectue un drop sur le receveur pendant
l’exécution du worker.

Onze tests du filtre async UTF-8 et 27 tests de contraintes
ont réussi. Les scénarios exécutés sous clang C11 à O2 et UBSan
fatal vérifient les sorties des deux branches, la capture via
fabrique, les reprises par continue et le drop avant join.
Une sortie qui rétablit un littéral après les reprises permet
le drop. Avec deux sources empruntées possibles, leur drop
est refusé pour chacune. Cette dernière variante a été rejouée
séparément après le filtre.

Sur copie temporaire, supprimer la provenance du bras nommé
fait rejeter le programme valide. Omettre la reconstruction
de la réservation du paramètre mutable laisse passer un drop
interdit. Ignorer les métadonnées de provenance au point fixe
laisse passer le drop de la source introduite par continue.
Ce dernier mutant survivait au cas mêlant littéral et emprunt,
car la preuve statique suffisait à déclencher une réanalyse.
Le cas à deux sources empruntées détecte le défaut.

La copie figée du premier cycle de réaffectation async a terminé
avec 185 tests réussis. La copie du cycle sur les littéraux est
encore en cours. La preuve statique pour les vues calculées dont
tous les bras sont des littéraux reste à traiter en contexte
synchrone.

### Capture de vues statiques calculées

Pour AS2, chaque branche de if établit la provenance de la
vue finale avant la fermeture de son scope. Si toutes les
branches continuantes fournissent du stockage statique, le
temporaire de résultat conserve cette preuve. Les match sur
résultats UTF-8 utilisent les mêmes jonctions. Une découpe
sur un résultat prouvé statique propage la preuve au nouveau
temporaire avant de l’utiliser pour une capture.

Le filtre `proves_computed_static_storage` a réussi sous
clang C11 à O2 et UBSan fatal. Il exerce la capture directe
et celle par alias mutable d’un if avec alias local au bras,
d’un match UTF-8 et d’une découpe du if. Un if produisant
un `&u8` est également capturé, puis lu après yield. Les
scénarios précédents à provenance mixte continuent de
contrôler le drop avant join. La mutation qui omet de
conserver la preuve au résultat fait rejeter les quatre
variantes directes, y compris le `&u8`. Mutation détectée.

La suite async figée du cycle précédent a réussi 187 tests.
La suite async de cette révision est lancée sur copie figée.
Cette passe ne couvre pas encore toutes les formes de
résultat statique, dont les match sur enum utilisateur et
la composition avec certains retours synchrones.

Sur cette révision, le filtre UTF-8 async a réussi 12 tests
et le filtre UTF-8 des règles fondamentales en a réussi 27.

### Vues produites par match sur un enum utilisateur

Le vérificateur de bras du match nominal accepte les vues UTF-8
et vérifie que les bras continuants fournissent le même type.
Il réunit les chemins empruntés et contrôle leur durée jusqu’au
receveur. Quand tous les bras continuants produisent une vue
statique, le temporaire du switch C conserve cette preuve.

Le test `capture_from_nominal_match` exerce les deux variantes
d’un enum injecté dans une fabrique synchrone. Pour chaque
variante, le C sous clang C11 à O2 et UBSan fatal retourne la
longueur attendue après yield. Le drop de la source est admis
lorsque les deux bras produisent des littéraux. Si un bras
rend l’emprunt injecté, le drop avant join est refusé pour
les deux variantes. Un bras Int mêlé aux vues est refusé.
La mutation qui omet la preuve statique à la sortie du match
fait rejeter le programme valide. Mutation détectée.

Le cas d’octet `&u8` reste couvert par le if du cycle précédent.
La composition avec des retours synchrones de vues calculées
reste à approfondir.

Sur cette révision, le filtre des enums du compilateur a réussi
23 tests et le filtre UTF-8 async en a réussi 13.

### Composition avec les retours synchrones

Le vérificateur compose les provenances du contrat de retour
avec les arguments déjà évalués. Lorsque toutes les sources
du contrat sont statiques, le temporaire de l’appel garde la
preuve. Une source empruntée continue de produire le
descripteur utilisé pour la réservation. La preuve d’un
appel évalué provient de ses paramètres préparés.

Le test `composes_computed_view` traverse deux relais
synchrones entre la vue calculée et sa capture. Sous clang
C11 à O2 avec UBSan fatal, il observe le résultat après yield.
Le drop avant join est admis lorsque les deux bras produisent
des littéraux et refusé si un bras peut fournir un emprunt.
Sur copie temporaire, supprimer la preuve de retour d’appel
fait rejeter le premier scénario. Mutation détectée.
Les expressions loop qui produisent des vues sont à examiner
séparément.

Le filtre UTF-8 async a réussi 14 tests et celui des règles
fondamentales en a réussi 27 sur la révision avec composition
des contrats.

### Vues produites par break

Une boucle expression accepte les vues `&str` et `&u8`.
Chaque break contrôle la durée de vie jusqu’au receveur.
La jonction réunit les chemins empruntés et garde une preuve
statique lorsque tous les break fournissent du stockage statique.
Le temporaire C conserve le type de vue.

Le filtre `capture_from_loop_break_values` a réussi sous
clang C11 à O2 et UBSan fatal. Deux reprises précèdent le
break qui sélectionne la vue. Les deux sorties sont exécutées
pour la variante statique et pour celle mêlant un littéral
et un emprunt. Le drop de la source empruntée avant join
est refusé, de même qu’un break qui fournit une vue sur une
allocation de l’itération ou un Int à la place d’une vue.
La mutation supprimant les chemins empruntés à la jonction
fait rejeter un scénario valide. Mutation détectée.
Une variante `&u8` a ensuite confirmé la lecture après yield
et le refus du drop. Le filtre UTF-8 async a réussi 15 tests
avant cet ajout, et la suite des boucles a réussi 61 tests.

La copie figée du cycle sur les vues statiques calculées a
terminé avec 190 tests async réussis. Une nouvelle copie
figée exécute la suite avec le match nominal, les retours
synchrones et les valeurs de break.

### Réemprunt explicite d’un octet UTF-8

Le réemprunt partagé `&*octet` reprend le descripteur
du paramètre ou sa preuve de stockage statique. Le corps
async peut aussi réemprunter un `&u8` pour le retourner
ou le passer à un enfant. Le réemprunt mutable est refusé.

Le filtre `byte_reborrow_keeps` a réussi sous clang C11
à O2 et UBSan fatal. Il vérifie la lecture de l’octet de
continuation après yield, à travers une fabrique synchrone,
un relais async et une vue retournée par join. Le drop
de la source dynamique est refusé avant join et après join
si la vue reste à utiliser. Dans la variante littérale,
le drop du String indépendant est admis. Les deux mutations
temporaires qui suppriment la provenance synchrone ou le
réemprunt dans le corps async rejettent des programmes
valides. Mutations détectées.

Le filtre UTF-8 async complet a réussi 16 tests sur cette
révision. La suite async figée du cycle précédent était
encore en cours lors de cette vérification.

La suite figée du cycle sur les résultats de break s’est
terminée avec 193 tests réussis, avant l’ajout de la variante
octet de ce test et du réemprunt explicite.

### Capture par transfert d’un String détenu

AS2, AS14, MT7 et MT8. Un paramètre async `-> String`
conserve le pointeur vers son allocation et la source de
nettoyage. Le corps peut appeler push_str, push et byte_len.
Les liaisons mutables sont exigées pour les écritures.
La capture transmet ce type exact lors du relais vers un
enfant. Les chemins de cleanup existants libèrent le String
dans son pool d’origine.

Le test `owned_string_capture` lance deux Strings du même
pool via une fabrique synchrone qui retourne les handles.
Les workers écrivent avant et après yield, et les deux join
retournent les longueurs attendues. Après terminaison,
le pool de deux slots est réutilisé. Le même test simule
EAGAIN sur les lancements et détruit une instance inactive.
Les cas de déréférencement Int, de set Int et de seconde
consommation sont refusés. Le C passe sous clang C11 à O2
avec UBSan fatal. La mutation omettant le nettoyage inactif
épuise le pool et fait échouer le scénario. Mutation détectée.

Les retours détenus de String, leur remplacement et les
autres opérations de collection dans le corps async restent
à implémenter. Les refus correspondants sont des limites
du prototype. Les captures de Vector ne sont pas couvertes
par cette passe.

La régression de croissance a réussi 22 tests. Le filtre
async des captures est encore en cours.

### Capture détenue de Vector<Int> et Vector<u8>

AS2, MT7 et MT8. Les captures par transfert acceptent ces deux
collections avec le type exact de l’argument. Le corps peut
ajouter des valeurs du type d’élément et consulter len après
yield. Le nettoyage restitue les slots au pool d’origine.
Une lecture d’élément Int utilise le contrôle de borne runtime.
Les opérations Int sur le descripteur et les mélanges de types
restent refusés.

Le test owned_vector_capture lance deux workers du même pool
via un relais synchrone. Il vérifie les deux types d’éléments,
la longueur, la restitution du slot et son état vide au réemploi.
La variante Int lit les trois éléments dans leur ordre logique.
La lecture hors limites échoue avec le diagnostic prévu. Les
variantes sans mut, avec set et avec élément incompatible sont
refusées. Sous clang C11 à O2 et UBSan fatal, le test passe.
Remplacer les éléments ajoutés par zéro fait échouer la comparaison
des sommes attendues. Mutation détectée.

La sélection des captures précédente, figée avant les Vector,
a terminé avec 60 tests réussis. Le cas String a aussi été rejoué
sur cette révision. Les retours détenus de collections, leur
réaffectation et l’indexation u8 dans le corps async restent ouverts.

La régression de croissance a réussi 22 tests sur la révision
avec captures de Vector.

### Indexation des Vector détenus dans les corps async

AS8, MT8 et les règles d’indexation des Vector. Les lectures et
écritures Int/u8 utilisent la vérification de borne du runtime.
L’adresse de la case est matérialisée avant l’évaluation du RHS,
y compris quand l’indice ou le RHS suspend l’exécution. L’écriture
réutilise le contrôle d’accès final des tableaux fixes et exige
la liaison mutable ainsi que le type exact de l’élément.

Le test index_reads_writes observe l’ordre 0 puis 1 de deux
indices suspendus, le résultat Int modifié et l’octet u8 retourné
après yield. L’absence de mut et les confusions Int/u8 sont
refusées. L’indice de destination hors limites produit le diagnostic
runtime. Le scénario passe sous clang C11 à O2 avec UBSan fatal.
Une mutation remplaçant la lecture u8 par zéro compile mais donne
NUL au lieu de z et est détectée. Une première mutation remplaçant
la place entière par zéro était rejetée par le compilateur C et
n’apportait aucune preuve sur la valeur lue.

Les deux tests ciblés owned_vector ont réussi. La régression
async des tableaux est encore en cours sur cette révision.

### Transfert d’une collection détenue à un enfant async

AS3, AS14, MT3 et MT8. Le test forwarding_preserves_cleanup
transmet le Vector<Int> du parent à un enfant, suspend le parent,
lance l’enfant et l’attend. La longueur et le contenu sont lus dans
l’enfant après croissance, puis le slot d’origine est réutilisé par
l’appelant du parent. La destruction de l’enfant inactif exerce le
second chemin de nettoyage. L’abandon du handle lancé, l’usage de
la collection après transfert et le relais vers un type String sont
refusés. Le test passe sous clang C11 à O2 avec UBSan fatal.

Cette passe ajoute des scénarios de composition aux mécanismes de
transfert existants. La régression async des tableaux du cycle
précédent a réussi 26 tests.

Sur copie temporaire, retirer la condition qui exige l’attente
pour un enfant avec capture détenue laisse accepter l’abandon.
Le scénario de rejet détecte cette mutation. La sélection async
owned_ est encore en cours.

### Retour de collection détenue par join synchrone

AS10 et MT6. Une tâche peut retourner par <- un String,
un Vector<Int> ou un Vector<u8> détenu du type déclaré.
Le résultat de join conserve ce type dans les analyses de
provenance, de contraintes, d’effets et dans le descripteur de
nettoyage. L’extraction du Ok reçoit le pointeur existant et
la responsabilité de sa destruction. Le pool d’origine reste
la source de restitution du slot.

Le test result_keeps_type_pool exécute les retours Vector<Int>
et String sous clang C11 à O2 et UBSan fatal. Il contrôle les
adresses avant capture et après join, les éléments ou le texte,
la mutation après extraction et la restitution au pool de
capacité un. Le scénario String simule aussi EAGAIN et ignore
le Ok pour exercer le nettoyage implicite. Le retour Int avec
une collection est refusé. La réception détenue après await
dans un corps async reste explicitement refusée en attendant
la liaison typée correspondante. Les variantes exécutées ne
couvrent pas encore le retour Vector<u8>.

Une mutation qui omet de vider le membre du frame après
transfert survit au test. Le chemin de cleanup actif exclut
l’entrée consommée. Ce résultat ne valide pas la mutation
dans toutes les combinaisons.

La mutation qui remplace le pointeur retourné par NULL est
capturée par UBSan lors de l’accès au résultat. La sélection
async owned_ a réussi 23 tests, et la suite des effets a réussi
20 tests. Le filtre test_function_results.py ne sélectionne
aucun test dans ce dépôt et ne constitue pas une validation.

La suite test_results.py a ensuite réussi ses 27 tests.

### Réception détenue dans le parent async

AS10 et MT6. La réception après await conserve désormais le
type nominal d’une collection détenue. Le même suivi s’applique
au payload du Result d’un handle attendu, à sa liaison nommée,
à son extraction et au renommage de l’allocation extraite.
Le cadre de nettoyage reprend l’entrée détenue reçue.

Le test await_receives_exact passe sous clang C11 à O2 et
UBSan fatal. Il fait circuler Vector<Int> et String à travers
un enfant attendu directement, un parent qui retourne la
collection et un second parent qui attend un handle. Le
résultat attendu contrôle les contenus après mutations et
suspensions, puis l’appelant réutilise le slot du pool de
capacité un. Le Result nommé et le match immédiat sont
exercés. EAGAIN sur le lancement interne restitue aussi le
slot. Absence de mut, méthode Int et type d’élément incorrect
sont refusés. La mutation attribuant Int au payload du
handle fait rejeter le scénario valide. Mutation détectée.
Les retours de collections via les expressions bloc et loop
et leurs réaffectations restent à compléter.

Les sorties calculées conservent aussi ce type. L’export d’une
allocation inscrit son type dans le temporaire. Les signatures
des bras et des break comparent ce type avant de fournir leur
résultat commun. Le scénario Vector a été rejoué avec un bloc,
un if et un loop qui transmettent chacun la réception de leaf.
Les contenus, le nettoyage et le réemploi du slot restent ceux
attendus. Un if mêlant String et Vector est refusé. Ces variantes
font partie du test await_receives_exact, rejoué avec succès.
La sélection async owned_ lancée avant l’extension aux blocs
a terminé avec 24 tests réussis.

Le filtre async loop a réussi dix tests après la propagation
du type dans les sorties calculées.

### Réaffectation des collections détenues

V4 et AS8. La réaffectation réutilise la transition des Int
alloués en exigeant le type exact de la collection. Le RHS
est évalué entièrement avant le nettoyage du receveur ancien.
La réception depuis await utilise le type déclaré de la tâche.
Les résultats calculés par bloc, if ou loop gardent leur type.
Si le RHS a consommé le receveur puis le restitue, le nettoyage
ne détruit pas de nouveau l’allocation transférée.

Le test reassignment_evaluates_rhs exécute les cinq formes
pour Vector<Int>. Le RHS lit l’ancien élément avant yield,
puis retourne la nouvelle allocation. Le test vérifie ses
éléments et son adresse, la destruction unique de chaque
allocation et le réemploi du pool. Il couvre aussi la restitution
de la même allocation via await et un remplacement String.
Les valeurs scalaires et les moves implicites sont refusés.
Le C passe sous clang C11 à O2 et UBSan fatal. Omettre la
destruction ancienne conserve une allocation vivante à la
fermeture du pool et fait échouer six scénarios. Mutation détectée.
Les écritures sur receveur emprunté restent gouvernées par
les règles de mutation de contenu.

La sélection async owned_ a réussi 25 tests sur cette révision,
avant l’ajout du scénario de restitution du même receveur.
Ce scénario a ensuite réussi dans le test ciblé.

### Contrats synchrones des Result de collections

MT5–MT6. Les signatures de transfert reconnaissent
Result<A<T>,JoinError> pour Int, String, Vector<Int> et
Vector<u8>, ainsi que l’enveloppe imbriquée existante. Le
type du payload traverse les contrats et l’extraction.
L’analyse des effets représente ces types enveloppés pour
résoudre correctement les méthodes du contenu après match.

Le test join_result_crosses_sync transmet un Result à travers
un relais et une fabrique synchrones. Les variantes String et
Vector<Int> vérifient l’identité, le contenu et le réemploi du
slot. EAGAIN sur la variante String nettoie la capture et rend
le slot. L’appel à un contrat de Result<A<Int>,JoinError> avec
le Result de Vector est refusé au passage d’argument. Le C
passe sous clang C11 à O2 et UBSan fatal. Omettre le type à
la réception du contrat fait rejeter le retour valide. Mutation
détectée. Les suites des effets et résultats ont réussi 20 et
27 tests. Les enveloppes imbriquées de collections ne sont pas
exercées par ce scénario.

La suite globale figée avant les dernières extensions de captures
et de retours de collections a terminé avec 1 556 tests réussis
sur sa révision de départ. Son journal est conservé dans
/tmp/crust-desc-string-regression.log. Ce résultat ne couvre pas
les modifications postérieures de ces extensions.

Une nouvelle copie figée lance la suite globale avec les retours
et réaffectations de collections. Sa sortie est enregistrée dans
/tmp/crust-collections-async-regression.log. La sélection async
owned_ est également encore en cours.

### Result imbriqués de collections

AS10 et MT6. Les tâches acceptent et retournent le Result
transféré d’une collection avec son type exact. Le join
qui ajoute une enveloppe conserve ce type. Le cadre async
le transmet au Result interne lors de l’extraction et aux
signatures de sorties par if ou boucle. La capture d’un
Result et son retour comparent aussi le type du payload.

Le test nested_collection_join exécute un retour String
à travers un enfant lancé, un parent async et une fabrique
synchrone. Deux match extraient le String d’origine. Les
adresses, le texte et le réemploi du pool de capacité un
sont contrôlés sous clang C11 à O2 et UBSan fatal. EAGAIN
interne puis externe produisent les bras d’erreur attendus
et restituent le slot. Un relais async reçoit le Result
par -> et le retourne après yield. Une variante choisit
le relais dans les deux bras d’un if, avec import explicite
du Result dans chaque bloc. Le retour d’un Result<Int>
avec un String est refusé. Supprimer le type au join
imbriqué fait rejeter le retour valide. Mutation détectée.
Les scénarios exécutés de cette passe utilisent String.

La sélection owned_ précédente a terminé avec 26 tests
réussis sur sa révision figée de départ.

Une variante Vector<Int> du même retour imbriqué a ensuite
réussi. Elle vérifie l’identité, les deux éléments et le
réemploi du slot après double extraction.

Le filtre async nested reste en cours après les vérifications
ciblées. La suite globale figée poursuit sa régression.

### Captures de collections par emprunt

MT1, MT2 et MT8. Les paramètres & et &mut de String,
Vector<Int> et Vector<u8> utilisent le pointeur de collection,
avec le type exact dans les fabriques et les cadres async.
Le partage conserve une réservation de lecture, et l’emprunt
mutable réserve l’accès exclusif jusqu’au join. La mutation
requiert la capacité &mut ou une liaison détenue mutable.
Un mut sur un paramètre partagé ne donne pas la mutation du contenu.

Le test collection_borrows_reserve modifie le Vector par un
worker après suspension, puis reprend ses accès chez l’appelant.
Deux workers lisent le Vector et maintiennent la réservation
après le premier join. Un worker modifie aussi un String emprunté.
Le relais d’un &mut Vector vers un enfant attendu est exercé.
Mutation ou lecture incompatible avant join et drop après le
seul premier join sont refusés. Les variantes de signatures
partagées tentant d’écrire sont refusées. Le scénario ciblé
passe sous clang C11 à O2 avec UBSan fatal.

La régression globale figée a signalé un échec dans le test
scalar_body_verifies. Le sous-cas &mut u8 était correctement
refusé mais le préfixe du diagnostic avait changé lors de
l’extension des captures. Le diagnostic conserve désormais
ce préfixe et précise les emprunts de collections admis.
Le test ciblé rejoué passe. Aucun rejet attendu n’a été retiré.

La mutation qui remplace la réservation exclusive par une
réservation partagée laisse accepter la lecture incompatible
pendant l’exécution et est détectée. Les sept tests de la
sélection collection et le test mutable_capture ont réussi.
La variante Vector<u8> modifie un octet, suspend, ajoute
l’octet lu puis vérifie le texte zz chez l’appelant après join.
Elle a réussi dans le test ciblé rejoué. Le filtre nested du
cycle précédent a terminé avec 14 tests réussis.

### Lectures scalaires UTF-8 depuis un String async

TX5–TX6 et AS8. L’indexation d’un String dans le corps async
copie un u8 et char_at retourne son Result de char. Le corps
matérialise la vue du receveur avant l’indice et réserve son
accès pendant l’évaluation de cet indice, y compris quand elle
suspend l’exécution. Aucun prêt n’est transmis par l’octet ou
le char copiés.

Le test scalar_reads_copy_utf8 observe l’indice suspendu 2,
le char sur quatre octets retourné après yield et un octet de
continuation copié. Il modifie le String avant d’utiliser le
char et détruit le String avant d’utiliser l’octet dans une
nouvelle allocation. Le cas hors bornes produit le diagnostic
runtime. Un retour Int à la place du u8 est refusé. La mutation
via un enfant appelé pour calculer l’indice de char_at est aussi
refusée. Le scénario passe sous clang C11 à O2 et UBSan fatal.

Les vues &str ou &u8 persistantes issues d’une collection dans
le cadre async restent à raccorder au suivi des prêts locaux.
Cette passe expose les lectures scalaires indépendantes.

La mutation qui omet la réservation pendant le calcul de
l’indice laisse accepter le programme incompatible. Le test
la détecte. Les sélections UTF-8 et collections sont encore
en cours.

La sélection UTF-8 du cycle de lectures scalaires a terminé avec
18 tests réussis, puis celle des collections avec sept. Ces
sélections précédaient la correction TX21 décrite dans
GROWING_REGIONS_CYCLE.md. Le test de durée de vie du deuxième
String a ensuite été rejoué avec son stockage dédié et a réussi.

### Vues UTF-8 locales dans un cadre async

AS8 et B1–B5. Une découpe ou un emprunt d’octet sur String
peut être reçu dans une liaison locale immuable. La provenance
locale suit les alias et les captures UTF-8 d’enfants attendus.
La liaison rejoint le suivi du dernier usage des autres prêts.
Le receveur est aussi réservé pendant l’évaluation des bornes.
La sortie d’un bloc retire la provenance de ses noms locaux.

Le test local_string_views_hold exerce le String emprunté et
le String capturé par transfert. Il conserve une vue et son
alias après yield, les transmet à un enfant qui retourne la vue,
puis vérifie sa lecture avant mutation. La mutation antérieure
au dernier usage est refusée. Après dernier usage, elle est
admise, y compris depuis un bloc enfant. Un emprunt d’octet
est également conservé après yield. Le cas détenu restitue
son slot au pool. Le retour d’une vue vers une collection
détenue du cadre est refusé. Le C ciblé utilise clang C11
à O2 avec UBSan fatal.

Le suivi des vues locales mutables, de leurs résultats calculés
et du payload UTF-8 d’un handle reste ouvert. Le prototype les
refuse explicitement lorsqu’ils garderaient un prêt local non
encore représenté. La projection de ces vues retournées vers
les captures &String de l’appelant reste aussi à raccorder.

### Résultats calculés de vues UTF-8 — continuation

Aucune règle normative modifiée. AS8, AS11, AS12, TX4–TX5,
TX12 et B1–B5 sont les obligations examinées. La création de
liaison après un await calculé utilisait un autre chemin que
la liaison scalaire simple : elle perdait les prêts associés
au résultat UTF-8. Six programmes autorisaient alors une
mutation avant la lecture de la vue. Ils sont désormais refusés.
Le chemin commun de liaison restitue ces réservations.

Les expressions bloc, if et boucle peuvent maintenant fournir
une vue locale immuable &str ou &u8. La provenance du résultat
réunit les sources possibles, sans promotion implicite. Une
source détenue détruite à la sortie de l’expression interdit
le résultat, y compris depuis un break imbriqué. Une liaison
annotée ne masque pas cette provenance. L’indexation d’une
vue alias réserve aussi ses sources pendant le calcul d’indice.

Deux tests nouveaux déterministes :
- computed_utf8_await_preserves_local_source_loans : six programmes
  acceptés, six mutations précoces refusées ; tâche choisie via
  bloc, if et boucle, deux chemins exécutés.
- computed_local_utf8_views_reserve_each_possible_source : quinze
  programmes acceptés, vingt-quatre refus ; deux collections,
  deux chemins, texte ou octet, annotations, drop prématuré,
  réutilisation des deux slots après destruction des captures,
  vues sur sources détruites dans un bloc ou une boucle.

Ces programmes acceptés produisent puis exécutent du C11 avec
clang, pthreads, O2, Wall/Wextra/Werror et UBSan fatal. Les
sélections utf8 (20 tests) et computed (15 tests) ont réussi
avant les deux derniers cas annotés ; le test complet incluant
ces annotations a ensuite réussi. local_string_views_hold a
également réussi. La sélection utf8 antérieure aux vues locales
avait réussi avec 18 tests. Aucun modèle indépendant nouveau
n’est ajouté dans cette passe ; les sorties attendues et les
refus sont spécifiés dans les scénarios.

Mutations exécutées dans des copies temporaires : retirer la
réservation de la liaison locale fait manquer deux refus ;
retirer uniquement l’enregistrement des prêts après await
calculé fait manquer les six refus du nouveau test. Les deux
mutations sont détectées. Cette sélection ne donne aucun taux
global de détection.

La régression globale précédente, copie
/tmp/crust-collections-async-regression.TgL4fU, a terminé :
1565 tests en 1036.676 s, un échec de correspondance de diagnostic
pour une capture &mut u8 interdite. Le diagnostic préservant le
préfixe attendu est corrigé ; scalar_body_verifies réussit sur
la version courante. Il ne s’agit pas d’un bilan global vert.

Nouvelle régression lancée sur la copie figée
/tmp/crust-local-utf8-regression.b6x596bs ; journal
/tmp/crust-local-utf8-regression.log. Elle est encore en cours.
Une exécution des deux nouveaux tests à O0, également sous
UBSan fatal, est lancée séparément dans
/tmp/crust-local-utf8-O0.tgy49xmx ; résultat à consigner après
terminaison effective.

Limites restantes : liaisons de vues locales réaffectables,
payload UTF-8 de handle gardant un prêt local et projection des
vues retournées vers une capture &String chez l’appelant restent
à implémenter. Les refus provisoires ne satisfont pas ces cas
valides. Les vues calculées simples ne font plus partie des
restrictions restantes. Les sélections ciblées et UBSan ne
constituent ni une preuve générale ni la validation complète
async/multithread. L’objectif global reste ouvert.

Complément exécuté : les deux nouveaux tests ont également réussi
à O0 sous UBSan fatal, respectivement en 8.820 s et 3.469 s,
depuis la copie /tmp/crust-local-utf8-O0.tgy49xmx. Le test
complet computed_local_utf8 incluant les annotations a aussi
réussi à O2 en 7.500 s. La régression globale reste en cours.

Contre-exemple supplémentaire TX13/B1 : dans une routine,
let view = &a[..]; a.push_str(view); était accepté, alors que
le même appel synchrone était refusé. La libération des prêts
de dernier usage précédait l’appel et retirait trop tôt celui
de son argument. Le prêt de l’argument est maintenant réservé
séparément jusqu’après l’opération. Le test
push_str_keeps_argument_loan_through_call compare cinq formes
d’argument (nom, découpe, if, bloc, boucle), vers une autre
collection et vers la même. La copie globale b6x596bs a été
figée avant cette dernière correction ; son résultat ne la
couvrira donc pas. Le test ciblé et la sélection UTF-8 ont été
lancés sur cette dernière correction, résultats à consigner.

Complément TX13 exécuté : push_str_keeps_argument réussit à O2
(2.939 s) et à O0 (5.521 s), avec UBSan fatal. Cinq programmes
acceptés copient vers une autre collection ; les cinq variantes
qui empruntent et mutent la même collection sont refusées.
La mutation qui supprime la réservation propre à l’argument
est détectée : cinq refus manquent. Journal de mutation :
/tmp/crust-push-argument-mutation.o07tj04r/mutation.log.
La sélection local_string_views_hold rejouée réussit (2.555 s).

### Réaffectation des vues locales UTF-8 — continuation

Obligations inchangées : AS8–AS12, TX4–TX5/TX12–TX13, B1–B5.
let mut sur une liaison &str ou &u8 permet de remplacer la vue,
pas de modifier ses octets via cette vue. La nouvelle expression
est évaluée avant remplacement. Les alias et captures d’enfants
conservent leur provenance propre ; modifier la liaison ne les
invalide pas et ne lève pas leurs réservations.

Le suivi distingue maintenant les usages de l’ancienne valeur
et ceux d’une valeur qui sera affectée ensuite. Une affectation
sans lecture de l’ancienne vue termine son prêt ; une affectation
qui la lit conserve ce prêt pendant l’évaluation. Les vues mortes
sont libérées selon les continuations lexicales. Les snapshots
de contrôle incluent leurs provenances et les enregistrements
de prêts. Leur restauration copie les dictionnaires pour ne pas
modifier une branche déjà sauvegardée. Les branches et les
sorties break réunissent les sources possibles ; les obligations
des tâches, handles et allocations restent comparées séparément.

Une liaison extérieure peut temporairement recevoir une vue
sur un String enfant si son dernier usage précède la destruction
du String. Un usage ultérieur empêche cette destruction et fait
refuser le programme. Aucune allocation n’est promue implicitement.
Le test vérifie la réutilisation du slot après join.

Les reprises continue et implicites sont admises lorsque les
provenances et prêts des liaisons sont rétablis. La comparaison
ignore l’identité interne d’une liste de prêts et une liste vide
ne constitue pas une réservation. La jonction de deux sorties
break est distincte d’une reprise : élargir les provenances sans
réanalyser le corps ne suffirait pas à vérifier une boucle. Les
reprises changeant effectivement de provenance restent refusées
par une restriction du prototype, à lever par analyse de point
fixe. Ce refus ne constitue pas l’implémentation des cas valides
correspondants.

Cinq tests nouveaux, exécutés à O2 avec clang C11, pthread,
Wall/Wextra/Werror et UBSan fatal :
- mutable_local_utf8_bindings_replace_loans_without_losing_aliases :
  trois programmes acceptés et trois refus, dont vue &u8 réaffectée,
  enfant attendu et captures de String détenues avec slots réutilisés.
- mutable_utf8_views_merge_assignments_by_path : sept acceptés et
  quatorze refus, deux branches, sorties break et branche partielle.
- mutable_utf8_bindings_match_small_alias_model : modèle indépendant
  de labels de stockage, 16 combinaisons déterministes, huit acceptées
  et huit refusées. Remplacer une vue ne change jamais le label de sa
  copie sauvegardée. Le modèle ne lit pas l’analyse du compilateur.
- mutable_utf8_view_obeys_source_scope_and_loop_backedge : un accepté
  et trois refus, dont source enfant et mutation entre deux itérations.
- mutable_utf8_view_replaced_before_continue : deux acceptés, reprise
  explicite ou implicite après remplacement par une vue statique.

La sélection mutable_utf8 a réussi avec quatre tests en 24.031 s,
puis mutable_local_utf8 avec un test en 6.121 s. Les mêmes sélections
ont réussi à O0 sous UBSan fatal (24.849 s et 3.453 s) depuis
/tmp/crust-mutable-view-O0.jtlrftpa. Elles représentent 21 programmes
acceptés exécutés et 28 refus attendus par configuration.

Deux mutations exécutées : supprimer les prêts de la nouvelle valeur
fait manquer quatre refus du modèle fini ; ne conserver que la
première branche à la jonction fait manquer cinq refus. Elles sont
détectées. Journaux :
/tmp/crust-mutable-view-loan-mutation.uprnlgg6/small_alias_model.log
/tmp/crust-mutable-view-join-mutation.p3rfv_qt/mutable_utf8_views_merge.log
Aucun taux de mutation global n’est déduit de ces deux fautes choisies.

La sélection utf8 antérieure à cette passe a terminé avec 20 tests
réussis en 56.615 s. Après les premiers changements de réaffectation,
utf8 a réussi avec 22 tests (86.627 s), computed avec 15 (79.042 s).
Ces sélections précèdent les derniers ajustements de reprise et le
cinquième test ; elles ne couvrent pas exactement la dernière version.
Une suite async complète est en cours depuis la copie figée
/tmp/crust-mutable-view-async.ldal6xte, journal
/tmp/crust-mutable-view-async.log. Cette copie précède la comparaison
des listes vides et le test replaced_before_continue. La régression
globale b6x596bs est toujours en cours et porte sur la version
antérieure aux réaffectations ; elle n’a pas été redémarrée.

Les limites ASan/TSan déjà documentées restent inchangées. Aucune
preuve générale de sûreté, de concurrence ou de terminaison n’est
établie. Restent notamment l’analyse des provenances transportées
par des boucles, le payload UTF-8 de handle avec prêt local, et la
projection vers les captures &String de l’appelant. Les autres
écarts de la matrice ne sont pas clos par cette passe.

### Payload UTF-8 de handle avec provenance locale

AS8/AS10/AS12, B1–B5 et TX12. L’attente du handle peut restituer
un &str ou &u8 qui réserve un String du cadre appelant. Le Result
nommé conserve ses prêts ; la vue extraite dans Ok reçoit une
réservation propre, jusqu’à son dernier usage. Un second match du
même Result ne doit pas lire une source prématurément mutée.
La vue peut sortir du match si sa source survit ; le résultat
scalaire u8 copié ne conserve pas ce prêt.

Le traitement des match instructions reçoit maintenant leur
continuation lexicale réelle ; les retours scalaires reçoivent une
continuation vide. Sans cette information, le Result restait
réservé alors que son dernier usage et celui du payload étaient
terminés. La séparation des réservations est aussi appliquée aux
payloads &Int et &mut Int, pour éviter que la libération du Result
masque un payload encore utilisé dans le bras.

Deux nouveaux tests à O2/UBSan fatal ont réussi (4.178 s) :
joined_utf8_view_keeps_local_collection_until_payload_last_use et
joined_utf8_result_retains_independent_payload_and_result_loans.
Sept programmes acceptés exécutés, huit refus attendus : attente
directe ou Result nommé, deux match successifs, handle calculé,
capture détenue et réutilisation du slot, destruction anticipée,
vue sortant du bras, emprunt d’octet dont la valeur copiée devient
indépendante. Les deux tests ont aussi réussi à O0/UBSan fatal
(4.973 s), copie /tmp/crust-joined-utf8-O0.pjhcgac1.

La mutation supprimant la réservation du résultat UTF-8 au join
est détectée avec cinq refus manquants. Journal :
/tmp/crust-joined-utf8-loan-mutation.07u3l408/test.log.
La sélection borrowed (six tests) avait réussi après la séparation
des prêts de payload et avant le complément de continuation sur
return ; elle est relancée après ce complément. Ces tests et la
mutation ne prouvent pas tous les cas de handles ni la concurrence.

Cette extension ne clôt pas la projection des retours de vues
vers les captures &String chez l’appelant ni l’analyse des boucles
qui transportent des provenances différentes. Les suites figées
en cours restent attachées aux versions précédemment précisées.

Complément exécuté après la dernière correction : borrowed réussit
avec six tests en 30.865 s ; mutable_utf8 réussit avec quatre tests
en 20.573 s. Nouvelle régression globale figée sur la version
courante : /tmp/crust-view-handles-regression.6jab9flc, journal
/tmp/crust-view-handles-regression.log. Elle est en cours, sans
résultat global annoncé. Les processus des copies b6x596bs et
ldal6xte ont été interrogés et sont toujours actifs ; aucune
suite n’a été relancée à la suite d’un simple délai d’observation.

### Retour de vue depuis une capture String empruntée

Aucune règle normative modifiée : B5, AS11–AS12, MT1–MT2 et
TX4–TX5/TX12 exigent qu’une vue retournée conserve sa source
injectée et les restrictions correspondantes. Une capture &String
ou &mut String peut fournir &str ou &u8 ; une capture par transfert
ne peut pas retourner un emprunt vers une allocation détruite
avec l’état, même lorsque le pool subsiste.

L’inférence de paramètres contributeurs inclut les captures String
empruntées et les propage dans les attentes imbriquées. Le contrôle
de retour admet exclusivement les racines String injectées par
emprunt, pas les collections détenues par le cadre. Chez l’appelant,
les captures de String reconstituent les chemins vers le stockage
d’octets et la capacité d’origine. Les parents sont filtrés par
cible pour ne pas réserver des captures étrangères au résultat.
Les résumés de fonctions normalisent une origine de String en
provenance de stockage de String, y compris après transfert d’un
Execution vers une fonction qui le joint.

Trois tests nouveaux :
- string_capture_return_projects_storage_to_caller : quatre
  programmes acceptés, cinq refus ; alias après yield, relais await,
  relais par handle attendu, retour calculé de bloc, source &mut,
  capture non contributrice libérée, mutation/drop prématurés,
  refus de retour depuis une capture détenue.
- string_view_join_contract_projects_collection_capture : trois
  acceptés, six refus ; fabrique synchrone, contrat de join, parent
  exclusif, consommation du handle par une autre fonction. Les
  deux refus supplémentaires retournent une vue sur un String local,
  avec pool local ou injecté : la durée du pool ne sauve pas la valeur.
- string_byte_return_keeps_conditional_collection_provenances :
  deux acceptés, quatre refus ; deux chemins vers deux String,
  réservation des deux sources avant deref, puis mutations admises
  après copie de l’octet et remplacement UTF-8 observable.

Les trois tests ont réussi à O2/UBSan fatal avant les deux refus
supplémentaires (7.418 s). Le premier a été rejoué après avoir
renforcé le cas de destruction (1.753 s) ; le second incluant les
refus de sources locales a réussi (1.949 s). Le filtre string_
a réussi avec huit tests (15.511 s), utf8 avec 27 (75.766 s),
pendant cette passe. Tous les programmes acceptés passent par le
C11 généré, clang, pthread, Wall/Wextra/Werror et UBSan fatal.
Les versions O0 et mutations sont consignées ci-après après fin.

La première mutation supprime les captures String de l’inférence
de provenance. Le premier test amélioré la détecte avec un refus
manquant (mutation précoce acceptée). Un premier essai sur la version
antérieure du test avait aussi produit une différence de diagnostic
sur le drop depuis un enfant : ce n’était pas une acceptation
incorrecte. Le cas a été corrigé pour importer explicitement la
valeur à détruire et retirer les autres usages de cette valeur.
La seconde mutation supprime la restriction du retour vers une
collection détenue : le contre-exemple bad(s: -> String) -> &str,
sans appel réel, est accepté à tort et le test la détecte.
Journaux : /tmp/crust-string-projection-loss-mutation.mibk75d5/latest-test.log
et /tmp/crust-string-owned-return-mutation.r6d37fgw/test.log.

Régressions terminées, versions distinctes :
- /tmp/crust-local-utf8-regression.b6x596bs : 1571 tests réussis
  en 1330.599 s. Cette version précède le dernier correctif push_str,
  les liaisons réaffectables, les payloads et les projections String.
- /tmp/crust-mutable-view-async.ldal6xte : 214 tests async réussis
  en 446.840 s. Cette version précède la comparaison des listes de
  prêts vides, le test de continue et les retours via handles.
Ces succès ne sont pas attribués à la version courante.

Nouvelle régression globale en cours sur
/tmp/crust-string-projection-regression.acs7wg3i, journal
/tmp/crust-string-projection-regression.log. La régression
view-handles/6jab9flc précédente est toujours active et n’a pas
été redémarrée. Aucun bilan global vert courant n’est annoncé.

Limites : analyse de point fixe des provenances transportées
par les boucles, agrégats et autres écarts de la matrice restent
ouverts. Les scénarios de retour depuis des String injectés sont
implémentés ; leur couverture ne constitue pas une preuve générale
de toutes les projections ni de la sûreté multithread. Les limites
ASan/TSan de l’environnement restent celles déjà documentées.

Complément exécuté sur les trois tests complets : neuf programmes
acceptés et quinze refus attendus ont réussi à O0/UBSan fatal
(7.369 s), copie /tmp/crust-string-projection-O0.9gfkydh0,
journal latest-test.log. Le test de mutation amélioré n’annonce
plus de différence de diagnostic comme acceptation incorrecte :
il détecte directement une mutation source acceptée à tort.

Les trois tests complets ont aussi été rejoués à O2/UBSan fatal :
trois tests réussis en 7.974 s, mêmes neuf programmes acceptés et
quinze refus. py_compile a réussi sur async_lowering.py, crust.py,
results.py et tests/test_async_runtime.py.

### Point fixe des vues UTF-8 transportées par les boucles

Obligations inchangées : S4–S5/S5a, B1–B3, AS8–AS12/AS14 et
TX4–TX5/TX12. Chaque reprise est vérifiée pour les sources possibles
à toutes les itérations, pas seulement pour celles de la première.
Une lecture après reprise conserve son prêt avant cette reprise.
Une affectation qui remplace la vue peut terminer le prêt de son
ancienne valeur sans terminer ceux des alias déjà copiés.

La descente async peut maintenant demander l’élargissement de
l’entrée d’une boucle. Une nouvelle provenance déclenche une
revérification complète depuis un état de descente neuf. Seules
les unions finies de noms de sources sont conservées entre passes.
Les variables et allocations temporaires, étapes C et avertissements
d’une passe abandonnée ne sont pas émis une seconde fois. Les
obligations non UTF-8 de tâches, handles et allocations restent
contrôlées séparément à chaque reprise.

La vivacité des vues utilise aussi un point fixe booléen : lecture
avant remplacement, continuation normale, continue, break, return,
while sans itération et boucles imbriquées. Les sources de l’entrée
et celles des sorties sont distinctes ; une loop qui remplace la
vue avant chaque break ne retient pas artificiellement sa première
source après sortie. Les annotations ou transferts ne sont pas
modifiés. Une source locale à l’itération ne peut alimenter une vue
encore utilisée après sa destruction.

Six nouveaux tests déterministes :
- loop_carried_utf8_views_widen_before_verifying_reprises : deux
  programmes acceptés, quatre refus ; reprise explicite et implicite,
  mutation après dernier usage de l’ancienne vue, nouvelle source
  protégée après sortie, conflits directs ou via un alias à une
  itération ultérieure.
- while_carried_utf8_view_preserves_zero_iteration_source : deux
  acceptés et quatre refus ; limite zéro ou deux, conservation des
  sources d’entrée et de reprise jusqu’au dernier usage après while.
- nested_loop_carried_utf8_view_reaches_fixed_point : un accepté et
  un refus ; deux niveaux, yield aux reprises et provenance finale.
- loop_carried_byte_view_with_value_and_task_cleanup : un accepté
  et un refus ; &u8, valeur de break Int indépendante, tâche inactive
  nettoyée à chaque sortie, pool de capacité un. Le C ne contient
  qu’une instruction de création pour cette tâche. L’oracle initial
  supposait un seul avertissement ; il a été corrigé pour les deux
  sites de nettoyage légitimes, break et continue, calculés depuis
  le programme source. Ce n’était pas un défaut du compilateur.
- loop_carried_utf8_alias_chain_matches_concrete_trace_model : quatre
  acceptés et douze refus. Un modèle indépendant exécute deux valeurs
  de référence et produit les traces pour zéro à trois itérations.
  Il ne calcule pas les unions de provenance du compilateur. Une
  instrumentation ponctuelle a observé trois passes de descente sur
  le cas à trois itérations ; la dernière entrée inclut les trois
  sources possibles de la vue.
- loop_carried_utf8_view_rejects_iteration_local_storage : deux refus,
  reprise continue ou sortie break avec source détruite à l’itération.

Les cinq premiers tests ont réussi à O2/UBSan fatal (11.736 s),
puis à O0/UBSan fatal (11.403 s), dix programmes acceptés exécutés
et vingt-deux refus. Le sixième, ajouté ensuite, a réussi : deux
refus supplémentaires (0.002 s). Les six sont rejoués ensemble.
Clang C11, pthread, Wall/Wextra/Werror, UBSan fatal. La sélection
loop a réussi avec quinze tests (33.148 s), avant ajout du modèle
et des refus de stockage local. La sélection utf8 a réussi avec
trente tests (108.240 s) ; elle précède le sixième test.

Mutations exécutées dans des copies temporaires :
- supprimer la revérification après découverte d’une provenance :
  quatre refus manquants, mutation détectée ;
- déclarer les vues mortes à la tête : six refus manquants, mutation
  détectée.
Journaux : /tmp/crust-loop-view-no-recheck-mutation.5vi6b7mg/test.log
et /tmp/crust-loop-view-no-header-live-mutation.g18kxkey/test.log.
Ces fautes choisies ne définissent pas un taux global de détection.

La régression view-handles a terminé : 1579 tests réussis en
1382.973 s depuis /tmp/crust-view-handles-regression.6jab9flc.
Elle précède les projections String et cette analyse de boucles.
La régression String/projection reste active, sans redémarrage.
Nouvelle régression globale sur /tmp/crust-loop-view-regression.agml2erw,
journal /tmp/crust-loop-view-regression.log. La copie comprend les
cinq premiers tests et le code courant ; le sixième test a été
ajouté ensuite et est exécuté séparément. Aucun résultat global
courant n’est encore disponible.

Limites : les unions d’origines ne préservent pas toutes les
corrélations entre références. Les continuations d’expressions
non fournies restent conservatrices. Le point fixe de ces vues
n’étend pas automatiquement les transitions d’allocations ou de
handles qui étaient encore refusées par les autres contrôles.
Agrégats, autres écarts de la matrice et limites ASan/TSan restent
ouverts. L’analyse et les tests ne sont pas une preuve générale.

Complément exécuté : les six tests réunis ont réussi sur la version
courante à O2/UBSan fatal (7.399 s), puis à O0/UBSan fatal
(7.612 s, /tmp/crust-loop-view-O0.u0fukpxy/latest-test.log).
Dix programmes acceptés exécutés et vingt-quatre refus attendus
par configuration. La vérification py_compile des fichiers Python
modifiés a réussi. La copie de régression globale précédait le
sixième test ; son code de compilation est celui de cette passe.

### String.pop et Option<char> dans les cadres async

TX14, TX2, TX12 et AS8–AS12 : aucune règle normative changée.
Le runtime string_pop existant est maintenant accessible depuis
un corps async. La famille Option<char> conserve son identité
de type dans les captures, retours, attentes et contrats de join,
bien que son stockage C soit le même CrustCharResult que celui
d’autres résultats Unicode. Un Option<char> ne devient donc pas
un Result<char,CharAtError> ou CharFromStrError par identité de
représentation C.

pop exige un accès mutable, évalue l’opération une fois et garde
le résultat au travers des suspensions. La réservation des vues
encore utilisées interdit la mutation. Un appel sans receveur de
résultat exécute aussi l’effet. Les valeurs calculées dans les
arguments et les réaffectations de ces résultats utilisent leur
type inféré complet, sans réévaluation. Le char retourné est une
copie indépendante ; aucune référence vers les octets supprimés
ou le String n’est conservée.

Quatre tests ajoutés :
- string_pop_preserves_utf8_and_returns_independent_char_option :
  retrait de deux char multi-octets, None sur vide, stockage après
  yield et mutation de la source avant usage du résultat. Refus
  d’une vue active, d’un receveur partagé, d’un argument superflu,
  de mauvais patterns, d’une capture de vue encore nécessaire à
  un autre argument et d’un mauvais type de retour.
- string_pop_option_survives_source_drop_and_slot_reuse : Option
  passé à un enfant tandis qu’un autre reçoit puis détruit le
  String ; contrat synchrone de join, slot réutilisé avant usage
  du char, EAGAIN et fallback. Expression conditionnelle en argument
  et réaffectation conditionnelle de l’Option également exercées.
  Une capture de mauvaise famille est refusée.
- string_pop_discarded_result_still_mutates_once : le résultat
  ignoré ne fait pas disparaître l’opération.
- string_pop_sequence_matches_unicode_scalar_model : six textes,
  dont vide, ASCII, deux et quatre octets, accent combinant et
  mélange. Python fournit un modèle indépendant des scalaires
  retirés dans l’ordre inverse, du compte et du texte final vide.

Les quatre tests ont réussi sur la dernière version à O2/UBSan
fatal (13.396 s) et O0/UBSan fatal (12.765 s). Onze programmes
acceptés, douze exécutions avec la variante EAGAIN, sept refus
attendus par configuration. Clang C11, pthread, Wall/Wextra/Werror.
Copie O0 : /tmp/crust-async-pop-O0.87bauql3, journal test.log.
La sélection string du socle synchrone a réussi : quinze tests
en 11.597 s. La sélection utf8 async a réussi : trente-trois tests
en 80.227 s ; ces deux sélections précèdent le complément des
arguments calculés et des réaffectations, validé ensuite par les
quatre tests complets. Elles ne constituent pas une régression
globale de la dernière version.

Mutations exécutées dans des copies séparées :
- retrait du contrôle d’emprunt de pop : le programme qui garde
  une vue utilisable est accepté à tort, refus manquant détecté ;
- retrait runtime de vector_truncate : le texte n’est pas raccourci
  et le même char est restitué plusieurs fois, sortie incorrecte
  détectée pendant l’exécution.
Le premier essai de la mutation runtime était arrêté à la compilation
C par Werror pour une variable devenue inutilisée : le défaut n’était
pas exercé au runtime. Une conversion void conservant la mutation a
permis l’exécution et l’observation du résultat incorrect, sans
modifier l’oracle. Journaux :
/tmp/crust-async-pop-borrow-mutation.ujown61f/test.log
/tmp/crust-async-pop-runtime-mutation.ur3ief85/runtime-test.log
Aucun taux de détection général n’en est déduit.

La régression String/projection précédente a terminé : 1582 tests
réussis en 1259.733 s, copie acs7wg3i. Elle précède l’analyse de
point fixe des boucles et ce complément de String. La régression
des boucles reste active. Nouvelle régression globale sur
/tmp/crust-async-pop-regression.v49ognio ; journal
/tmp/crust-async-pop-regression.log. Les suites actives ne sont
pas redémarrées après une observation sans résultat nouveau.

Limites : cette passe n’ajoute pas automatiquement les autres
opérations de String ou Vector aux corps async. Les autres écarts
de la matrice, corrélations d’origines, agrégats et installation du
scheduler restent ouverts. Les limitations ASan/TSan précédemment
consignées restent applicables. Ni ces tests ni UBSan ne prouvent
la sûreté générale de Crust.

Complément de suivi : la régression des boucles a terminé avec
1587 tests réussis en 1134.387 s, copie agml2erw. Elle couvre le
code du point fixe et ses cinq premiers tests ; les deux refus de
stockage local ajoutés ensuite ont été exécutés séparément. Elle
précède String.pop async et la famille Option<char> de cette passe.
La régression async-pop/v49ognio est toujours active ; aucun
résultat global de cette version n’est encore annoncé.


### Remplacement transactionnel d’un octet depuis un corps async

Les règles TX15, TX17 et AS2/AS8/AS12 restent inchangées. Le corps async
peut désormais appeler String.replace_byte. Le receveur mutable est réservé
avant les arguments ; l’indice puis l’octet sont évalués de gauche à droite,
sauvegardés dans l’état avant les suspensions suivantes. La mutation finale
utilise ces sauvegardes et le validateur UTF-8 transactionnel existant.
Une vue encore utilisée interdit la mutation ; l’accès au même String dans
un argument reste refusé comme en synchrone. Copier l’octet au préalable
est accepté. Ignorer le résultat ne supprime pas l’effet.

Le Result<u8,ByteReplaceError> garde son type propre dans les captures,
retours, await, join et contrats synchrones. Son stockage C CrustByteResult
est défini dans le prologue partagé ; le résultat de join a un champ typé
replaced_value, distinct du CrustCharResult. Aucun cast entre ces types
n’est introduit. Les métadonnées communes décrivent type C, famille et champ.
Le payload ancien octet est une valeur u8 indépendante : destruction du
String puis réemploi d’un pool de capacité un exercés avant sa réutilisation.

Cinq tests string_replace ajoutés à test_async_runtime.py : quatorze sources
acceptées, quinze exécutions natives avec la configuration EAGAIN, huit
programmes refusés par configuration. Les cinq tests ont réussi à O2/UBSan
fatal en 9.099 s et à O0/UBSan fatal en 8.692 s (copie
/tmp/crust-async-replace-byte-O0.w4y_i9gj/latest-test.log). Clang C11,
pthread, Wall/Wextra/Werror. Ces premières exécutions précèdent le complément
sur les anciens tests de littéraux et les valeurs C inutilisées ci-dessous.
Le modèle indépendant construit sept transactions d’octets et utilise le
décodeur UTF-8 Python pour calculer succès ou InvalidUtf8, puis compare le
statut et le contenu final ; indices négatif, fin et texte vide inclus.

Mutations dans trois copies séparées, sans changer les oracles :
- réservation supprimée : deux programmes à emprunts conflictuels acceptés
  à tort, refus manquants détectés ; journal
  /tmp/crust-async-replace-reservation-mutation.wxege2v5/test.log ;
- indice non sauvegardé : l’autre argument modifie sa variable pendant await,
  sortie native incorrecte détectée ; journal
  /tmp/crust-async-replace-index-mutation.2as71084/test.log ;
- validation UTF-8 désactivée : deux exécutions produisent des octets invalides,
  UnicodeDecodeError dans la lecture des sorties détecte le défaut ; journal
  /tmp/crust-async-replace-validation-mutation.6v8phyfl/test.log.
Le dernier défaut est détecté par l’oracle de texte, pas par UBSan. Aucun taux
global de détection n’est calculé.

#### Régression et frontières des littéraux u8

La régression globale précédente, async-pop/v49ognio, est terminée :
1592 tests réussis en 1024.497 s. Elle précède replace_byte async.
La copie /tmp/crust-async-replace-byte-regression.aez9q0zh a ensuite signalé
des refus attendus manquants dans les anciens tests de littéraux u8.
Les tests antérieurs attendaient le refus de 169 dans une capture ou un retour
u8, de 3 dans une liaison explicitement u8 et de 4 dans une case Vector<u8>.
Le socle synchrone accepte déjà ces constantes dans un contexte u8 borné ;
I5 et TX2 ne définissent aucune interdiction différente pour async. Il ne
s’agit pas d’une conversion d’une variable Int : son type reste distinct.
Les anciennes attentes de sous-ensemble sont remplacées par des exécutions
qui observent exactement l’octet produit, et par des refus de 256. Le refus
préexistant du passage d’une variable Int est conservé. La norme n’est pas
modifiée. Cette divergence d’oracle est rapportée explicitement, sans
présenter le premier lancement global comme réussi.

L’exécution des variantes littérales a aussi révélé un défaut de C généré :
un &str local déclaré puis réaffecté, devenu sans lecteur, faisait échouer
Wall/Werror (unused-but-set-variable). Le backend émet désormais une
conversion void de la valeur Copy matérialisée. Cela ne crée aucun usage
dans l’analyse Crust, ne prolonge aucun emprunt et ne supprime aucune
évaluation. Le programme minimal concerné compile et s’exécute désormais
avec la vérification de l’octet capturé dans l’état suspendu.

La copie finale O0 /var/folders/rs/ld5jvh_n6t92p1hhs2qrmt7w0000gn/T/crust-async-replace-final.ienoc1_z a terminé avec
succès les cinq tests string_replace, puis les quatre sélections unitaires
byte_capture_copies, byte_result_crosses, local_byte et owned_vector_index.
Journal focused-O0.log dans cette copie. Elle inclut le correctif de C
inutilisé et les nouveaux oracles natifs de littéraux. Une régression globale
sur le compilateur et les tests courants est lancée dans la copie figée
/var/folders/rs/ld5jvh_n6t92p1hhs2qrmt7w0000gn/T/crust-async-replace-context-regression.af7f6oeg ; journal
/tmp/crust-async-replace-context-regression.log. Aucun résultat terminal de
cette copie n’est encore disponible à cette consignation. Les validations
non terminales sont suivies par leur processus existant, sans les relancer
sur la seule base d’une observation sans sortie.

Limites : replace_bytes et les autres opérations de String/Vector ne sont
pas ajoutées automatiquement aux corps async. Les résultats UTF-8 calculés directement comme sujets de match font l’objet
du complément ci-dessous ; les autres formes calculées, les agrégats, les
corrélations de provenances et l’installation du scheduler restent ouverts.
Les limites ASan/TSan consignées plus haut restent applicables. L’objectif
global reste ouvert ; ces exécutions ne constituent pas une preuve générale
de sûreté ni une couverture de toutes les règles consignées.


#### Sujet calculé d’un match UTF-8 dans un corps async

Contre-exemple confirmé : `match if flag { yield; s.replace_byte(1,170) }
else { yield; s.replace_byte(1,168) } { ... }` était refusé avec « résultat
de handle requis », alors que recevoir exactement ce résultat dans une
liaison intermédiaire était permis. Le défaut appartenait à l’abaissement
async, pas aux règles de typage ou de durée de vie. Le sujet de contrôle
est désormais abaissé par infer_scalar_value ; sa famille vérifiée et sa
valeur déjà calculée sont transmises au match. Aucune réévaluation du sujet
n’est nécessaire. Les familles char, Option<char> et Result<u8,...> restent
distinctes par leur type, indépendamment du stockage C.

Le nouveau test computed_match_subject_evaluates_once exécute huit sources
acceptées : if, bloc, loop et match imbriqué, chacun sur true et false,
avec suspension et trace visible du seul bras choisi. Trois refus vérifient
le mélange de familles dans les branches, les patterns d’une autre famille
et une vue du String utilisée après la mutation. Succès à O2/UBSan fatal en
9.108 s et O0/UBSan fatal en 11.271 s. La sélection async char a aussi réussi :
cinq tests en 16.014 s, sur ce code. La sélection byte précédente a terminé
avec quatorze tests réussis en 43.617 s ; elle précède seulement ce complément
de match. Les neuf tests du complément O0 précédent ont tous réussi ; journal
focused-O0.log de la copie ienoc1_z.

Attention aux versions : la régression globale af7f6oeg inclut replace_byte,
les littéraux et le correctif void, mais précède le sujet de match calculé.
Elle ne doit pas être présentée comme une régression globale de ce dernier
complément. La copie aez9q0zh emploie les anciens oracles de littéraux et ses
échecs connus ne sont pas effacés. Les résultats terminaux et la mutation
de double évaluation sont consignés au fur et à mesure de leur exécution.

La mutation de double évaluation a terminé : les huit variantes natives
impriment deux fois la trace de bras au lieu d’une, huit sorties incorrectes
détectées (10.420 s). La compilation C et l’exécution ont bien été atteintes.
Copie /tmp/crust-async-computed-utf8.28m5zpoi, journaux O0.log et mutation.log.
Aucun taux global de détection n’en est déduit.

La sélection finale string_replace sur le code courant a terminé : six tests
réussis en 27.157 s, O2/UBSan fatal, journal
/tmp/crust-async-replace-computed-final-O2.log. Elle réunit les cinq tests
transactionnels et le sujet calculé (vingt-deux sources acceptées, vingt-trois
exécutions avec EAGAIN, onze refus attendus). La suite async complète et les
deux régressions globales figées restent non terminales à ce point ; leurs
processus ont été revalidés vivants par write_stdin. La copie af7f6oeg ne
contient pas le dernier complément de sujet calculé ; une régression globale
de la toute dernière version reste donc à exécuter après ces validations.


### Concaténation consommante async et réservation des receveurs d’ajout

Règles inchangées : TX22, TX11, TX13, VE2, B4a et AS2/AS8–AS12.
Le programme async `destination.merge(-> source)` était refusé comme
instruction non prise en charge, malgré la spécification TX22 et le support
synchrone. L’opération est maintenant abaissée avec réservation mutable de
la destination avant préparation du transfert. La source est extraite avec
ses informations de type, concaténée par le runtime String existant, puis
détruite. Le pointeur du receveur source est désarmé : ni la fin de bloc ni
la fin de tâche ne le détruisent à nouveau. Aucune économie de copie ni de
pic mémoire n’est promise. La source peut être fournie par transfert nommé,
await d’un retour détenu, bloc, if ou loop à résultat transféré. Dans un bloc
enfant, la responsabilité doit toujours être injectée avec `source ->;` avant
sa restitution ; les premiers snippets de tests sans cette injection étaient
invalides et ont été corrigés sans affaiblir le vérificateur.

Trois tests string_merge : quinze sources acceptées, dix-sept exécutions
natives en comptant deux configurations EAGAIN, neuf refus attendus. Ils
vérifient les pools distincts et identiques, le relais par contrat synchrone
de join, les adresses de destination et du slot source réutilisé, les
transferts calculés et les emprunts actifs. Un compteur indépendant des
listes de slots observe une destruction avant le print de la tâche, puis
trois au total pour les trois String créées. Le retour détenu de destination
sort du bloc qui détruit le pool source ; sa provenance ne dépend pas de ce
pool consommé. Six couples de textes (vides, ASCII, scalaires multioctets,
combinaison) sont comparés à la concaténation Python. Le mauvais type de
source, l’absence de flèche, le réusage de source, l’auto-merge et les
emprunts encore utilisés sont refusés.

Les trois tests ont réussi à O2/UBSan fatal en 12.424 s, journal
/tmp/crust-async-string-merge-final-O2.log ; à O0 en 12.968 s dans
/tmp/crust-async-string-merge-final.db854yhf/O0.log, puis en 12.461 s dans
/tmp/crust-async-mutation-arguments.x9q0mf0m/O0.log sur le code comprenant
les contrôles des autres ajouts et du joker décrits ci-dessous.
Clang C11/pthread, Wall/Wextra/Werror, UBSan sans récupération.

Mutations exécutées dans /tmp/crust-async-string-merge.ap6gdto1 :
- suppression du drop de la source : neuf échecs détectés, dont compteur
  de destruction incorrect au runtime et capacité encore occupée lors du
  réemploi ; journal drop-mutation.log, 7.159 s ;
- suppression de la réservation de destination : un programme qui mute
  celle-ci pendant un argument await est accepté à tort ; refus manquant
  détecté, reservation-mutation.log, 8.059 s.
Ces deux journaux couvrent les deux premiers tests, avant ajout du retour
hors du pool source. Le défaut de nettoyage a bien été exercé au runtime.

#### Ajouts de String et Vector : contre-exemple de réservation

Contre-exemples confirmés avant correction :
`s.push_str(change(s).await)` où change reçoit &mut String, et
`v.push(change(v).await)` où change reçoit &mut Vector<Int>, étaient
acceptés en async alors que les formes synchrones équivalentes étaient
refusées avec « emprunt actif ». Les receveurs de String.push,
String.push_str et Vector<Int/u8>.push sont maintenant réservés avant
l’évaluation de leur argument, puis contrôlés à nouveau avant l’effet.
La réservation traverse les suspensions et n’empêche pas les effets sur
un autre objet. Elle ne transforme pas un accès partagé en accès mutable.

Le test mutating_method_reserves couvre quatre programmes exécutés et
huit refus (mutation ou lecture du receveur au cours de l’argument).
Succès sur la dernière version : O2/UBSan fatal en 2.525 s et O0 en
2.745 s ; journal /tmp/crust-async-arguments-final.7optcv_p/O0.log.
Mutation retirant les deux réservations, dans la copie
/tmp/crust-async-mutation-arguments.x9q0mf0m : quatre refus de mutations
manquent, défaut détecté en 2.492 s. Cette mutation précède seulement les
quatre refus supplémentaires de lectures partagées ; ils sont exécutés
séparément dans la sélection finale. Aucun taux général n’en est déduit.

#### Joker Err(_) et identité des résultats UTF-8

Un cas valide de préparation d’un char a révélé un autre refus injustifié :
le backend synchrone excluait Result<char,CharAtError>,
Result<char,CharFromStrError> et Result<u8,ByteReplaceError> de la famille
acceptant le pattern générique Err(_), alors que leurs erreurs pouvaient
être nommées ou ignorées dans les corps async. Le joker est désormais
accepté pour les types Result existants ; il n’ajoute ni variante ni
conversion. Un Option ne devient pas un Result et les signatures continuent
de distinguer les deux familles de décodage.

Le test foundation utf8_result_wildcard_error_preserves_declared_family
exécute les branches succès/erreur des trois familles et vérifie le texte
final après une erreur transactionnelle. Deux refus conservent la distinction
de signatures et interdisent Ok/Err sur Option<char>. Succès à O2 en
0.383 s et O0 en 0.512 s, UBSan fatal. Mutation rétablissant l’ancienne table
restrictive : le programme valide est refusé par le compilateur, défaut
détecté avant émission de C, journal wildcard-mutation.log dans x9q0mf0m.
Les quinze tests synchrones de sélection string passent sur le code final
en 10.327 s ; /tmp/crust-async-merge-final-sync-regression.log.

#### État des régressions globales

La copie aez9q0zh a terminé : 1595 tests en 1306.412 s, cinq échecs tous
sur les anciennes attentes de refus des littéraux u8, identifiés dans la
section précédente. Ce lancement est en échec ; les nouveaux tests natifs
et les refus hors intervalle sont validés séparément. La suite async lancée
avant la dernière mise à jour de son test Vector a terminé avec 183 tests
en 493.764 s et un échec sur ce même ancien refus de littéral dans une case
u8. Elle ne constitue pas un échec nouveau du correctif de réservation.
Les journaux historiques sont conservés, sans masquer les résultats rouges.

La régression af7f6oeg (code précédent, avant sujet de match calculé et merge)
reste en cours. Nouvelle copie globale figée
/tmp/crust-async-merge-regression.7drbnfyg ; journal
/tmp/crust-async-merge-regression.log. Cette copie comprend le compilateur
courant et tous les nouveaux tests, sauf les quatre refus supplémentaires
de lectures partagées ajoutés ensuite dans un test déjà présent. Ces refus
sont exécutés séparément à O0/O2. Le résultat global de cette copie est
encore non terminal. Les suites vivantes sont suivies par leur handle,
sans relance après une simple observation sans nouvelle sortie.

Limites : les opérations groupées replace_bytes, les vues de Vector dans
les corps async et d’autres opérations de collections restent à intégrer.
Les agrégats async, les corrélations de provenances, l’installation du
scheduler et les autres écarts ouverts de la matrice ne sont pas couverts
par cette passe. Aucun de ces résultats ne prouve la sûreté générale ou
l’implémentation complète des règles consignées ; l’objectif reste actif.


#### Régression de dernière utilisation corrigée avant réservation

Le premier lancement broad async string après ajout des réservations a
terminé avec un échec : vingt et un tests en 64.745 s, un programme valide
refusé dans local_string_views_hold_storage_until_last_use. Le programme
imprime, dans un bloc enfant, une vue déclarée dans son parent, puis ajoute
au String. La nouvelle réservation était contrôlée avant expiration de cet
emprunt parent déjà terminé. Deux scénarios existants de payload et Result
UTF-8 joint avaient la même difficulté dans la copie globale 7drbnfyg.

Correction : avant de réserver un receveur de collection, l’abaissement
expire les prêts arrivés à leur dernier usage, en incluant explicitement
l’instruction courante dans les usages encore requis. Un emprunt utilisé
pour préparer l’argument, ou après l’appel, reste donc actif. L’opération
ne supprime aucune réservation de tâche en cours. Les contrôles de mutation
et lecture du receveur pendant les suspensions restent en place.

Après correction, les vingt et un tests de sélection async string ont
réussi en 97.492 s : /tmp/crust-async-merge-string-fixed-regression.log.
Les deux tests joined_utf8 ont aussi réussi en 10.300 s, journal
/tmp/crust-async-merge-expiration-joins.log. Le test mutating_method_reserves
a été complété avec deux programmes valides où une vue externe est utilisée
pour la dernière fois dans le bloc enfant, puis deux refus voisins où elle
est encore lue après la mutation. Cette sélection finale représente donc
six programmes natifs et dix refus. Elle a réussi à O2 en 8.574 s ; les
résultats O0 et de mutation sont consignés après leur fin.

#### Correction du périmètre des copies de régression

Erreur de préparation découverte : les copies af7f6oeg et 7drbnfyg
contiennent les modules Python et tests, mais pas examples/. Les cinq tests
de démonstration test_enum_demo, test_explicit_main_demo,
test_functions_demo, test_pool_demo et test_real_demo y échouent sans lire
leurs fixtures. Cela invalide leur qualification de validation globale
complète ; ces erreurs d’environnement ne sont pas masquées ni interprétées
comme des erreurs du compilateur. Les cinq démonstrations ont été exécutées
dans le projet complet et passent en 5.157 s, journal
/tmp/crust-root-demo-verification.log. La copie 7drbnfyg précède également
la correction de fin d’emprunt ci-dessus ; ses trois erreurs async initiales
ont été reproduites et corrigées dans les tests ciblés.

Une nouvelle copie complète est créée dans
/tmp/crust-async-merge-complete-regression.yvymvvfk, avec les exemples,
modules, tests et autres fichiers du projet. La présence et l’identité des
cinq fixtures ont été vérifiées par comparaison d’octets avant lancement.
Il n’existe pas de module de tests imbriqué omis par la sélection. Les 1603
méthodes du projet courant sont réparties par module unittest dans deux
processus isolés, sans modifier l’ordre interne d’un module. Les journaux
sont dans cette copie ; results.json est écrit au fur et à mesure des
modules remis, avec terminal=false tant que tous ne sont pas terminés.
Le handle du processus et les sorties des journaux constituent le suivi ;
le fichier seul ne constitue pas une preuve de vie ni de réussite.
Ce lancement inclut la correction de durée de vie et tous les tests finaux.
Aucun résultat terminal de ce lancement n’est encore annoncé.

Complément terminal de la correction d’expiration : copie
/tmp/crust-async-expire-before-reserve.ljzxzyfs. O0/UBSan fatal :
mutating_method_reserves réussit en 7.770 s, local_string_views en 3.567 s,
et les deux joined_utf8 en 8.456 s. La mutation supprimant l’expiration
avant réservation est détectée par les deux programmes String valides,
refusés à tort au lieu d’être exécutés ; mutation.log, 5.016 s. Il s’agit
d’un défaut d’acceptation détecté au compilateur, pas d’un défaut runtime.
Le contrôle préserve également les dix refus voisins du test final.

À ce point, les processus de validation sur le projet courant (diagnostic
failfast) et sur la copie complète yvymvvfk ont été revalidés vivants par
write_stdin ; leurs résultats restent non terminaux. Les copies historiques
incomplètes continuent à produire des preuves partielles, mais ne peuvent
pas satisfaire le critère de validation globale complète. Aucune règle
normative n’a été modifiée pendant cette passe. L’objectif global reste
ouvert, y compris les opérations et obligations explicitement non couvertes.


### Remplacement groupé d’octets en async et résultat unitaire

Règles inchangées : TX15–TX17, B4a, VE5, AS2, AS8–AS12. Un corps async
abaisse maintenant `s.replace_bytes(debut, &bytes[a..b])` lorsque bytes est
un Vector<u8> reçu par emprunt partagé, mutable ou transfert. L’accès mutable
à la destination est réservé avant les arguments. La source de la tranche
est empruntée en partage pendant l’évaluation de ses bornes : lire sa
longueur est permis, la muter ou la transférer à un enfant est refusé.
L’indice et chaque borne sont sauvegardés au moment de leur évaluation, même
si la suite se suspend et modifie leur variable d’origine. Les crochets
vérifient la tranche avant la mutation ; le même runtime transactionnel que
le synchrone valide tous les octets du futur String, puis remplace le bloc.
Aucune écriture intermédiaire n’est publiée et le résultat ignoré exécute
quand même l’opération.

Result<(),ByteReplaceError> reçoit une identité de famille distincte de
Result<u8,ByteReplaceError>. La même structure C CrustByteResult et le
même champ replaced_value du join suffisent, sans modifier la disposition
ABI. Le type unitaire n’autorise pas l’extraction d’un u8. Les deux types
sont séparés à la capture, dans les retours et dans les patterns Ok. Le
résultat unitaire traverse la création d’une tâche, await direct, await de
handle et join bloquant, y compris par contrat synchrone. Il reste utilisable
après destruction et réemploi du Vector transféré ou emprunté, et après
sortie des pools et du tableau qui ont servi à un remplacement synchrone
produisant le résultat ensuite capturé. Le cas EAGAIN conserve le secours
unitaire fourni au contrat de join, sans mutation de la destination.

Modèle indépendant : la séquence candidate est formée par concaténation
Python de trois segments, puis décodée strictement en UTF-8. Dix situations
(vide, bornes négatives et positives, intervalle vide à la fin, échec UTF-8,
remplacement multioctet réussi) sont exécutées sur deux placements de la
source. Pour le front décroissant, un Vector vivant occupe le premier front
avant l’ouverture du Vector source du même pool. Le C instrumenté confirme
l’orientation passée par le descripteur pour chaque tranche non vide.
Le test compare le statut et le texte entier à l’oracle, y compris C3 A9
remplacé d’un bloc par 61 62, alors qu’une étape octet par octet serait
invalide. Les adresses ne sont pas mesurées par ce modèle async ; le runtime
commun de remplacement à taille constante garde sa couverture d’adresse
synchrone dans la matrice.

#### Défauts de fin d’emprunt reproduits et corrigés

Un programme sans receveur, `loop { s.replace_bytes(offset(view).await,
&bytes[..]); break; }`, était accepté alors que view empruntait s et était
encore lue pour préparer le premier argument. L’optimisation de fin de prêt
sur break garanti prenait le préfixe suivant l’instruction sans joindre
les usages dans l’instruction courante. Elle conserve maintenant les deux.
Un deuxième programme valide, qui lisait sa vue parent puis recevait le
résultat du remplacement dans un bloc enfant, était refusé. Le chemin des
expressions à valeur vérifie maintenant la fin d’emprunt avant réservation
avec l’expression courante incluse, comme pour une instruction. Les valeurs
finales de branches ont une continuation locale vide, et un break à valeur
prend en compte ses usages avant de fermer les prêts de sortie. Ce sont
respectivement un défaut d’acceptation trop permissive et un défaut de refus
excessif ; le premier contre-exemple ne démontre pas un accès hors durée au
runtime, car son enfant se termine avant la mutation.

Le test replace_bytes_respects exerce trois programmes valides (valeur
récupérée par break, retour de bloc et résultat de if), les trois refus
voisins où la vue est lue dans un argument suspendu et le refus du cas sans
receveur. La sélection loop entière a réussi : dix-sept tests en 104.244 s
à O2/UBSan fatal, /tmp/crust-async-replace-bytes-loops.log. Elle inclut les
cas antérieurs de provenance, transferts et reprises, et ce nouveau test.

#### Exécutions et mutations

Cinq tests replace_bytes passent à O2/UBSan fatal en 76.873 s
(/tmp/crust-async-replace-bytes-current-O2.log), et O0 en 77.389 s
(/tmp/crust-replace-bytes-current-O0.rsde4081/test.log). Le compilateur est
le même que celui du dernier complément de test, qui ajoute un Vector
capturé par transfert puis réutilise son slot et refuse son transfert
pendant les bornes de sa tranche. Ce complément a été exécuté avec la
sélection preserves à O2 en 15.302 s et à O0 en 11.823 s, journaux
/tmp/crust-async-replace-bytes-owned-O2.log et -O0.log. Couverture cumulée
par configuration : 33 sources acceptées et 34 exécutions, dont un échec de
lancement simulé supplémentaire et un arrêt attendu par garde de tranche ;
17 refus à la vérification. C11, pthread, Wall/Wextra/Werror, UBSan sans
récupération. Les quinze tests de sélection synchrone string passent en
33.701 s, /tmp/crust-async-replace-bytes-sync-regression.log ; ils précèdent
le complément de fin d’emprunt, propre au backend async.

Quatre mutations détectées dans des copies séparées, oracles inchangés :
- compatibilité de capture unitaire désactivée : le résultat avec u8 est
  accepté à tort, refus manquant ;
  /tmp/crust-replace-bytes-capture-type.vizokg58/test.log (13.050 s) ;
- indice non sauvegardé avant l’argument suspendu : le String reste `été`
  avec statut d’erreur au lieu du remplacement `abté` attendu, échec de
  sortie native ; /tmp/crust-replace-bytes-saved-index._kswazcc/test.log
  (7.472 s) ;
- prêt de la source pendant les bornes supprimé : mutation du Vector
  pendant le calcul de la tranche acceptée à tort, refus manquant ;
  /tmp/crust-replace-bytes-slice-reservation.b2ms3ubw/test.log (12.864 s) ;
- usages de l’instruction courante retirés du préfixe de sortie de boucle :
  le contre-exemple avant break est à nouveau accepté, refus manquant ;
  /tmp/crust-replace-bytes-current-O0.rsde4081/loop-mutation.log (5.974 s).
Les trois premières mutations précèdent le complément de fin d’emprunt,
la quatrième le couvre. Aucune couverture générale de mutations n’en
est déduite. Le premier lancement de tests a aussi détecté un mauvais
libellé attendu par le test de garde (la garde C arrêtait bien le programme
avec diagnostic) ; l’oracle a été rendu conforme au diagnostic français.

Limites : cette passe implémente l’argument de tranche directe de Vector<u8>.
Elle ne fournit pas encore les tableaux fixes u8 dans l’état async ni les
liaisons, paramètres et résultats de tranches de Vector dans les corps async.
Les sources tableau fixe restent utilisables en synchrone ; le résultat
unitaire synchrone peut maintenant traverser des tâches. Les autres
obligations ouvertes de la matrice demeurent. La copie complète yvymvvfk
couvre le code précédent à merge, sans cette dernière passe ; il faut
encore un résultat global complet sur le code courant. L’objectif reste
actif, sans prétention de sûreté générale.

Complément de suivi : sur le compilateur de cette passe, les six tests de
compatibilité replace_byte et sujet calculé ont réussi en 40.606 s à
O2/UBSan fatal, /tmp/crust-replace-bytes-scalar-compatibility.log. Dans la
copie complète précédente yvymvvfk, le module foundation est terminal :
424 tests réussis en 827.428 s (test_foundation_rules.log). Ce résultat
précède replace_bytes async et ne constitue pas la fin de la régression
complète. Le processus 4238 de cette copie et le processus 4344 du diagnostic
précédent ont été revalidés vivants ; aucun nouveau lancement global n’a été
fait sur la seule base de leur absence de résultat terminal.

### Tableaux fixes u8 dans les fonctions async

E2–E6, TX16, AS2, AS8–AS12, AS15 et MT6 s’appliquent à cette extension.
La forme et le type d’élément sont portés ensemble dans les captures et
les résultats transférés. Les tableaux par valeur occupent un membre
typé du cadre. Le pont synchrone convertit les représentations de tableau
sans conversion des éléments. Un tableau prêté passe par son adresse,
avec le pas de l’élément déclaré et la garde de chaque indice avant accès.
Le compilateur utilise le même type pour la copie, le remplacement, le
swap, le retour littéral et l’extraction du résultat. Une boucle annotée
vérifie le type de tableau fourni par chaque break.

TX16 accepte un tableau fixe d’octets emprunté dans le corps async.
Une ligne projetée après un indice suspendu, un tableau vide et une
copie temporaire sont couverts. Le descripteur du tableau fixe indique
un ordre croissant et la longueur exacte. Il n’ajoute pas de stockage
au-delà du tableau ni de rétention dans le résultat unitaire.

Un prêt partagé de case u8 peut traverser une suspension et un appel
enfant. Lorsqu’une fonction async retourne une case d’un tableau
emprunté en paramètre, son contrat retient la provenance du tableau
chez l’appelant. Un await direct, un handle attendu en async et un join
relayé par une fonction synchrone ont été exercés. La mutation voisine
est refusée avant le dernier usage du résultat et admise après celui-ci.
Un résultat emprunté dans un tableau local du cadre est refusé.

Les quatre tests async_byte_array ont exécuté dix variantes C dans
chaque configuration, dont un arrêt attendu sur borne dynamique.
Quatorze programmes voisins ont été refusés. Les sorties ab, cd, ba,
ac, bc et zc sont dérivées des valeurs sources et des opérations du
programme. Le test de transfert remplace la source chez l’appelant
entre la capture et le lancement pour vérifier l’indépendance de la
copie. Le scénario d’échec EAGAIN exerce le secours statique au join.
Les résultats à O2 et O0 sont consignés dans
/tmp/crust-u8-arrays-current-O2.log et /tmp/crust-u8-arrays-current-O0.log
avec quatre réussites en 10.308 s et 12.817 s. Les deux configurations
utilisent C11, pthread, Wall/Wextra/Werror et UBSan fatal.
Les 68 tests synchrones test_fixed_arrays passent en 66.528 s.
La sélection async array a réussi sur 30 tests en 118.085 s. Ce dernier
lancement précède le complément de retour littéral et d’annotation du
résultat de boucle, couvert par les quatre tests finaux.

Trois injections indépendantes ont été détectées dans
/tmp/crust-u8-arrays-validation.va4gw0iy.

- stride.log force un pas Int sur une ligne d’octets prêtée. Le test natif
  échoue avec un diagnostic de libération de mémoire virtuelle.
- result-loan.log supprime l’origine des résultats tirés des paramètres
  tableau u8. Le test détecte l’acceptation de l’écriture prématurée.
- break-type.log omet le type d’élément dans la comparaison des break.
  Le mélange de tableaux de même forme est accepté à tort et détecté.

Les mutations précèdent le complément de retour littéral et d’annotation
du résultat de boucle. La couverture E6 reste partielle pour les liaisons
de tableau emprunté et les emprunts mutables d’un octet isolé. Les
liaisons, paramètres et retours de tranches de Vector dans les corps
async restent à intégrer. Les valeurs de tableau traversant les scopes
par réception explicite, les prêts ordinaires et les réservations de
tâches projetées gardent les distinctions des cycles précédents.

La copie complète précédente yvymvvfk a terminé avec 1603 réussites
dans 43 modules. Cette version précède le remplacement groupé async
et les tableaux u8 async. La copie courante
/tmp/crust-u8-arrays-complete-regression.whhcsw5w contient les sources,
les tests et les exemples. La comparaison des cinq fixtures de
démonstration a réussi avant le lancement. La régression complète
courante est en cours dans le processus 53254.

### Tranches partagées de Vector en async

VE5, B4a, AS2, AS8–AS13, AS15, MT6 et TX16 ont été réexaminées dans le cas
des tranches partagées de `Vector<Int>` et `Vector<u8>`. Le descripteur C
conserve la base, la longueur et le sens. Sa copie entre cadres, à l’attente
et au `join` ne copie aucun élément. Le contrat de sortie conserve les sources
possibles du résultat et leurs prêts. Les données seulement consultées pendant
le calcul d’une borne restent réservées pendant la tâche et redeviennent
accessibles après `join`. Le dernier usage régit les réaffectations et les
reprises de boucle. Aucune règle normative n’a été modifiée.

Le test de réaffectation pendant le calcul d’une borne vérifie la distinction
entre la vue déjà préparée et la nouvelle valeur de la liaison. Une mutation
de la source déjà préparée est refusée pendant ce calcul et jusqu’à la lecture
de la sous-tranche. L’audit a aussi découvert deux captures d’entier acceptées
à tort. Dans `inspect(&vue)` et `inspect(&mut vue)`, la vue pouvait emprunter
le chemin de typage d’un `Int` local malgré son stockage C de type `VectorSlice`.
Le vérificateur refuse désormais ces deux appels au niveau de la capture.
La suppression du contrôle en copie temporaire reproduit l’acceptation.
Clang `-Werror -fsyntax-only` diagnostique alors l’affectation de
`VectorSlice *` à `const int *` dans le C généré (`type-guard.log`).

Les huit tests `async_shared_vector_slice` ont réussi aux deux niveaux
d’optimisation `-O2` et `-O0` avec Clang 20.1.3 et UBSan fatal. Pour chaque
configuration, ils vérifient 25 programmes refusés et 19 programmes traduits,
pour 20 exécutions natives dont deux arrêts par garde et un échec simulé de
`pthread_create` avec reprise sur la branche `Err`. Un oracle Python par listes
calcule les lectures attendues pour six combinaisons de sens et de borne,
deux résultats de réaffectation et trois nombres d’itérations. Les 15 tests
synchrones sélectionnés par `test_foundation_rules.py -k slice` et les
34 tests async sélectionnés par `test_async_runtime.py -k utf8` ont réussi.
Les cinq tests `replace_bytes` de la passe intermédiaire ont aussi réussi.
La première passe de quatre tests ciblés avait deux attentes de diagnostic
trop étroites pour le refus d’un `drop`. Elles couvrent désormais le message
spécifique « emprunt encore utilisé » sans changer la décision attendue.

Les cinq mutations en copie temporaire ont été détectées. Leurs journaux
sont sous `crust-async-slice-mutations.73ic5rey` dans le répertoire temporaire
de la session.

- `orientation.log` perd le sens descendant avant l’indexation. Deux
  résultats deviennent `40` au lieu de `20` et `30`.
- `snapshot.log` relit le receveur après calcul de la borne. La sortie
  devient `40` au lieu de `30` dans la branche qui réaffecte la vue.
- `loan.log` perd le prêt du résultat de l’attente. Une écriture
  prématurée dans le vecteur source est acceptée.
- `loop.log` omet l’élargissement des origines à la reprise. L’écriture
  prématurée de la source introduite par une itération est acceptée.
- `bound.log` attache le calcul de borne au résultat. Une écriture valide
  sur le vecteur qui fournit seulement la borne est refusée après `join`.

La tentative ASan avec UBSan à `-O1` a expiré au lancement. Le binaire de
contrôle instrumenté qui exécute seulement `return 0` a aussi expiré sans
sortie. Cette configuration ne fournit pas d’évidence exploitable ici.
La couverture des tranches mutables et de `split_at_mut` dans les cadres
async, ainsi que le prêt `&Int` d’une case de tranche, reste ouverte. Les
cas exécutés n’établissent pas une garantie générale de sûreté.

Un autre écart reste ouvert. Avec `v: &mut Vector<Int>`, le programme
`let first = &v[..]; let second = &v[..]; return first[0] + second[0];`
est refusé en synchrone comme en async. `v.len()` est aussi refusé si
`first` reste utilisé. Le suivi actuel garde une réservation exclusive
pour la vue partagée dérivée du paramètre mutable. B1 et la règle du
réemprunt partagé demandent de distinguer cette réservation envers
l’appelant des lectures compatibles par le parent lui-même. Le même
refus a été reproduit lorsque `first` est retourné par une fonction qui
reçoit `v` par `&mut`.

La régression complète de cette version a terminé avec 1620 réussites
dans 43 modules sur la copie figée
`/tmp/crust-shared-slices-complete-regression.txyhq_o1`. La régression
de la version précédente des tableaux u8 a terminé avec 1612 réussites
dans 43 modules sur `/tmp/crust-u8-arrays-complete-regression.whhcsw5w`.

### Réemprunt partagé par le parent mutable du vecteur

B1, B2, B4a, VE5, AS12 et AS15 ont été vérifiées autour de la séparation
entre un `&mut Vector<T>` et le propriétaire de son allocation. Le lecteur
qui utilise le même paramètre mutable peut lire la longueur et dériver une
deuxième vue partagée. Une écriture, y compris dans un argument suivant,
reste interdite jusqu’au dernier usage de la vue. Le retour d’un appel
synchrone rattache la tranche au parent nommé qui a fourni l’emprunt. Dans
un cadre async, le prêt de la tâche en cours reste exclusif si sa signature
reçoit `&mut`. Après `.await`, une tranche partagée ne bloque que les
écritures par ce même paramètre. Une tâche enfant qui reçoit `&Vector<T>`
peut lire la source en même temps qu’une autre tâche lit ses tranches.

Les deux nouveaux tests ont réussi avec Clang 20.1.3 et UBSan fatal à O0
et O2. Ils exécutent deux programmes et vérifient six refus à chaque niveau.
Les résultats natifs sont `32` puis `3` en synchrone et `52` puis `3` en async.
Les neuf tests async `async_shared_vector_slice` et les 16 tests synchrones
sélectionnés par `test_foundation_rules.py -k slice` ont réussi à O2.
Dans une première passe, un marqueur de test oublié provoquait une erreur
de syntaxe à la place du diagnostic d’emprunt attendu. La variante corrigée
atteint le contrôle d’emprunt et lève le diagnostic attendu.

Six mutations ont été détectées dans les copies de
`/tmp/crust-vector-shared-parent-final-mutations.eumewrgs`. Quatre mutations
refusent des lectures valides en gardant le parent temporaire du contrat,
en ignorant le parent lors de la lecture, en conservant le prêt exclusif
après `await` ou en classant la capture partagée comme exclusive. Deux
mutations acceptent un programme refusé par le vérificateur de référence.
L’une retire le prêt retourné par `await`. L’autre assimile le propriétaire
d’origine au parent mutable de la tranche. Les deux premières exécutions
de ces derniers mutants avaient échoué à la compilation C sous un
environnement incomplet. La passe finale hérite de l’environnement de
test et détecte les deux acceptations à tort.

Le lancement depuis une fonction synchrone d’une tâche qui reçoit son
paramètre `v: &mut Vector<Int>` par `tail(v)` reste refusé. Le vérificateur
des chaînes de captures signale « réemprunt async Int avec parent projeté
non pris en charge ». Les tranches mutables en async restent ouvertes.
Aucune règle normative n’a été modifiée.

La régression complète de cette version a démarré dans le processus 50523
sur la copie figée `/tmp/crust-shared-parent-complete-regression.zw89_f88`.

### Lancement synchrone avec un emprunt de Vector nommé

La capture d’un `&Vector<T>` ou d’un `&mut Vector<T>` dans une fonction
synchrone retient sa source et son parent par position. Le lancement et
le transfert d’un handle par contrat conservent cette provenance. Quand
le paramètre de la tâche est mutable, la réservation exclusive dure
jusqu’au `join`. Un résultat partagé reprend le parent existant et
permet de lire par ce parent. Le propriétaire d’origine et une autre
capacité d’accès restent distincts. La branche `Err` libère la réservation
sans exécuter le corps lors d’un échec de lancement simulé.

Les quatre tests ciblés combinent lancement direct et par contrat, capture
en lecture pendant des lectures concurrentes, sélection conditionnelle
de deux sources, passage enfant → parent, destruction et ordre des
arguments. Le modèle Python utilise deux listes et calcule la longueur
de chaque vecteur après la mutation de la seule source choisie. Il prédit
les sorties `16, 4, 3` et `26, 3, 4` pour les deux branches.
Sous Clang 20.1.3 et UBSan fatal, les quatre tests passent à O0 et O2.
Chaque niveau exerce sept programmes traduits, neuf exécutions C dont
deux échecs de lancement simulés, et dix-sept programmes refusés. Les
neuf tests existants `async_shared_vector_slice` passent aussi à O2.
Un essai séparé avec un contrat de lancement et un contrat de `join`
distincts produit `23` puis `4` sous UBSan à O2. Une écriture entre ce
second appel et le dernier usage de la tranche est refusée.

Quatre mutations ont été détectées dans les copies temporaires de
`/tmp/crust-sync-vector-launch-mutations.nb4wh9rr`.

- `exclusive-capture.log` transforme la capture mutable en réservation
  partagée. Deux lectures précoces, par lancement direct et via contrat,
  sont acceptées à tort.
- `contract-parent.log` retient le parent temporaire du contrat. Une
  lecture valide par le paramètre nommé est refusée après `join`.
- `one-result-origin.log` ne conserve qu’une des provenances du résultat.
  Une écriture avant le dernier usage sur l’autre source est acceptée.
- `owner-capability-final.log` traite le parent d’un `&mut v` frais comme
  partagé. La première version du test ne vérifiait ce cas que via le
  contrat. L’ajout du lancement direct détecte la lecture trop précoce
  par le propriétaire d’origine.

Les tranches mutables et le réemprunt explicite `&*v` dans une capture
depuis une fonction synchrone restent ouverts. Aucune règle normative
n’a été modifiée. La régression complète de cette version a démarré
dans le processus 84602 sur la copie figée
`/tmp/crust-sync-vector-launch-complete-regression.xjqzrkeg`.

### Réemprunts explicites de Vector et séparations locales async

B1–B2, B4, AS8–AS9, AS15, VE5, G12 et TX16 ont été réexaminées.
Un appel synchrone ou une capture de tâche peut réemprunter un paramètre
`Vector` avec `&*v` ou `&mut *v`. La cible et le parent sont identiques
au passage par nom. `&v` et `&mut v` sur une référence continuent de
demander un niveau supplémentaire. Un réemprunt d’un mode incompatible
avec la signature ou la référence est refusé.

Le contre-exemple `size(v)` lancé en tâche puis `length(v)` en synchrone
depuis le même `v: &mut Vector<Int>` était refusé par le contrôle interne
d’exclusivité. Les deux lectures dérivent de la même capacité. Le suivi
compte leur réservation commune et continue de bloquer un accès via une
capacité étrangère. Le test exécute deux tâches qui lisent cette source,
puis un sous-appel qui la reçoit par `&mut *v`. Une tentative d’écriture
après le premier `join` est refusée tant que le second handle reste actif.

Un corps async peut maintenant séparer localement `Vector<Int>` et
`Vector<u8>` en deux tranches mutables et subdiviser une moitié. Les
descripteurs et les adresses d’écriture préparées sont conservés dans
l’état C. Les prêts interdisent l’accès direct à la source et au parent
subdivisé tant qu’un enfant est utilisé. Un réemprunt partagé de la
moitié gauche bloque ses écritures et permet une écriture dans la moitié
droite. Ce réemprunt est exercé avec un relais `await` puis un remplacement
UTF-8. La croissance redevient possible après le dernier usage.

Les trois tests ciblés passent avec Clang 20.1.3 et UBSan fatal à O0 et
O2. Chaque configuration exerce cinq exécutions natives normales, deux
arrêts attendus et quinze refus. Un modèle par listes calcule la trace
de subdivision et d’écriture pour les placements ascendant et descendant.
La garde d’un indice invalide se déclenche avant l’effet observable du
RHS. La première sonde a trouvé une conversion implicite d’une tranche
mutable en Int. Le vérificateur rejette désormais cette copie et la
réaffectation d’une tranche mutable entière.
Les neuf tests de régression des tranches partagées en async et les
seize tests synchrones sélectionnés par `-k slice` ont réussi à O2.
Les 30 tests async sélectionnés par `-k array` ont aussi réussi sur
cette version. La régression complète 50523, antérieure au lancement
synchrone d’un réemprunt de Vector, a terminé avec 1622 réussites
dans 43 modules.

Les quatre mutations du réemprunt ont été détectées dans
`/tmp/crust-explicit-vector-reborrow-mutations.vbx9evu9`. Deux comptent
à tort des prêts compatibles comme concurrents. Deux autres acceptent
un mode explicite incompatible ou un déréférencement d’une allocation
qui n’est pas une référence. Les trois mutations de séparation dans
`/tmp/crust-async-local-vector-split-mutations.dqyqsevg` sont détectées.
Donner les mêmes descripteurs aux deux moitiés fait passer la somme
de `106` à `48`. Omettre la réservation du parent accepte des accès
prématurés à la source. Omettre le prêt relatif à une moitié accepte
son écriture alors qu’une vue partagée reste utilisée.

La construction autonome `let alias = &*v`, le passage de tranches
mutables aux tâches, les retours de vues issues des moitiés et les
résultats de séparation calculés par contrôle de flux restent à traiter.
Aucune règle normative n’a été modifiée. La régression complète de
cette version a démarré dans le processus 60971 sur la copie figée
`/tmp/crust-async-local-split-complete-regression.9n_2_bts`.

### Retours de vues après séparation et transfert de tâche

AS10–AS13, MT6, B3, D1, T3–T5 et VE5 ont été réexaminées. Une vue
partagée peut survivre à la liaison locale de la moitié dont elle est
issue lorsque son vecteur reste valide. Le compilateur retire les
réservations des liaisons de tranche qui quittent leur scope. Il garde
le prêt du stockage effectif dans les expressions de bloc, les sorties
de boucle, les affectations à un parent et les tâches transférées. Le
contrat conserve l’origine du vecteur et libère après `join` un autre
vecteur utilisé uniquement pour calculer la borne.

Une allocation importée par `v ->;` dans une itération ou une branche
pouvait être détruite alors qu’une tâche transférée l’empruntait encore.
La liste de cibles locales considérait les nouvelles liaisons et ignorait
le rattachement du vecteur importé. Le C de l’ancienne version pour
`/tmp/crust-split-escape-repro.crust` appelle `cell_drop` avant de reprendre
la tâche avec `task_poll`. L’exécution sous UBSan lisait encore `42` après
la destruction logique du vecteur. La trace montre le défaut de durée
de vie même si la zone restait lisible sur ce chemin. Le
vérificateur rejette maintenant la sortie de la tâche avec cette cible
et rejette aussi le transfert simultané de la cible encore empruntée.

Les trois tests ciblés passent à O0 et O2 sous Clang 20.1.3 et UBSan fatal.
Chaque configuration exerce quatorze programmes traduits et trente
et un refus. Les tests comparent la valeur de tranche, la longueur finale du
vecteur source, la reprise de l’accès à la borne, et la lecture d’un
octet via un résultat asynchrone. La séparation, la réaffectation et le
relais par tâche inactive ou handle sont couverts. Les cas invalides
incluent une source détenue par le cadre, une mutation de la source ou
de la borne avant la fin de son prêt et les transferts d’une cible à
travers les scopes quittés.

Six mutations ont été détectées dans
`/tmp/crust-split-shared-return-mutations.x_3_bkgb`. Deux laissent sortir
une capture dont la source doit mourir ou être transférée. Une garde
retient la borne à tort. Trois variantes confondent les réservations de
liaison et de stockage lors de la sortie d’un bloc, d’une affectation ou
du relais par tâche. Un septième mutant dans
`/tmp/crust-split-drop-backing.re6kgzm7` supprime toutes les origines à la
sortie du bloc. Il accepte à tort une croissance du vecteur avant le
dernier usage de la vue.

Les captures et retours de tranches mutables et de paires de séparation
restent ouverts. Aucune règle normative n’a été modifiée. La régression
complète de cette version a démarré dans le processus 45461 sur la copie
figée `/tmp/crust-split-shared-return-complete-regression.wgq2d12z`.
Les 29 tests sélectionnés par `-k transfer` ont réussi sur cette version.

### Captures asynchrones de tranches mutables disjointes

Les signatures async acceptent `&mut [Int]` et `&mut [u8]`. La
capture transporte le descripteur de la tranche. Les réservations
protègent la moitié et son stockage depuis la création, pendant les
suspensions et jusqu’à la fin de la tâche. Le passage par nom et
`&mut *vue` partagent ce contrôle. Les contrats synchrones préservent
le mode exclusif et la provenance. Un retour partagé conserve le prêt
de sa moitié à travers `await` et `join`. B1–B2, AS2, AS12–AS15,
MT1–MT6 et VE5 ont été réexaminées.

La lecture synchrone d’une tranche d’Int après un match a révélé un
défaut antérieur. La jonction lui affectait le type d’élément `uint8_t`
malgré son type déclaré. Elle conserve désormais l’élément Int ou u8
dans l’état vérifié et dans les accès C suivants. Le premier essai des
tests concurrents a également révélé deux marqueurs de test qui se
recouvraient. Les marqueurs corrigés font atteindre le contrôle d’emprunt
au programme refusé.

Les trois tests ciblés passent avec Clang 20.1.3 et UBSan fatal à O0
et O2. Chaque niveau exerce cinq programmes traduits, six exécutions
dont un échec de lancement simulé, et onze refus. Un rendez-vous atomique
dans l’oracle C exige que les deux workers soient entrés avant de les
laisser continuer. Les écritures `300` et `400` restent dans leur moitié.
Après le premier `join`, une lecture de la moitié libérée est admise et
une lecture de l’autre reste refusée avant son propre `join`. Le test
sur les octets combine écriture disjointe, retour partagé et validation
UTF-8. Le transfert de handle est admis depuis un bloc quand le vecteur
survit. Importer le vecteur dans ce bloc fait refuser le même transfert.
Les 16 tests synchrones et les 14 tests async sélectionnés par
`-k slice` ont aussi réussi à O2.

Quatre mutations sont détectées dans
`/tmp/crust-mutable-slice-capture-mutations.zck86w7o`. Omettre la
réservation de la moitié autorise une mutation ou une seconde capture
incompatible. Reclasser une capture contractuelle en lecture autorise
un accès prématuré. Perdre le prêt du résultat partagé laisse modifier
la moitié avant son dernier usage. Rétablir le type d’octet à la jonction
refuse la lecture valide de la tranche d’Int.

Les retours de tranches mutables et les résultats de séparation par
paire restent ouverts. Aucune règle normative n’a été modifiée. La
régression complète de la version du lancement synchrone nommé a
terminé avec 1626 réussites dans 43 modules. La régression de cette
version a démarré dans le processus 78890 sur la copie figée
`/tmp/crust-mutable-slice-capture-complete-regression.1b62snho`.
