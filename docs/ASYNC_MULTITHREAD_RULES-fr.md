[English](ASYNC_MULTITHREAD_RULES.md)

# Corbo — async, multithread et runtime

Décisions validées dans la discussion, intégrant la dernière version du
brouillon 04 de `design-buffer`.

Ce document est une extension normative de [LANGUAGE_RULES.md](LANGUAGE_RULES.md).
Il décrit la conception retenue. Le compilateur en implémente un sous-ensemble ;
la description normative ne vaut pas affirmation d'implémentation complète.
Les identifiants ci-dessous permettent de suivre les preuves dans
[VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md).

## 1. Syntaxe, création et suspension

**AS1 — Déclaration et points de suspension.** Une fonction suspendable se
déclare avec `async fn`. Les points de suspension explicites sont `.await` et
`yield;`. Une fonction ordinaire ne peut ni attendre avec `.await`, ni utiliser
`yield;`. Le mot-clé `routine` est remplacé par `async`.

Un corps async ne peut pas appeler directement une `fn` synchrone.
Il compose le travail avec les Futures et les primitives existantes.
Un calcul peut être écrit dans une `async fn` et attendu avec `.await`.
Pour l’exécuter sur un thread dédié depuis ce contexte, le développeur
lance sa Future avec `runtime::spawn_blocking` et attend le handle.

**AS2 — Création inactive et capture immédiate.** Appeler une fonction async
crée une instance inactive : son corps n'est pas encore exécuté. Les arguments
sont évalués de gauche à droite et capturés dès cette création. Les transferts
et les emprunts deviennent effectifs à ce moment, sans attendre son lancement.
Les arguments déjà préparés restent protégés pendant l'évaluation des suivants,
y compris si celle-ci se suspend.

**AS3 — Tâches stockables et déplacements par valeur.** Ces deux formes sont
autorisées :

```rust
let resultat = calculer(10).await;

let tache = calculer(20);
let autre = tache.await;
```

Une tâche est non `Copy`. Le passage par valeur déplace la tâche en conservant
son stockage et ses captures.

Le type d'une tâche inactive s'écrit avec le nom qualifié ou relatif de sa
définition async, comme `lire` dans `fn preparer(data: &i32) -> lire`.
En cas de conflit de noms, un chemin relatif qui désigne une seule définition
est obligatoire.
Après lancement, le type public du handle est `runtime::Handle<T>`, où `T`
est le résultat. Son contrat conserve les dépendances propres à la tâche.

**AS4 — Attente d'une tâche inactive.** `tache.await` démarre l'instance et attend
son résultat de type `T`. L'attente consomme l'instance du point de vue du
programme : elle ne peut pas être attendue une seconde fois. `yield;` rend la
main au runtime sans terminer la tâche, libérer ses captures ou fermer son scope.
Il ne démarre pas les instances encore inactives. L'enfant avance sur le thread
qui poll l'appelante ; sa suspension suspend celle-ci. Une migration de
l'appelante entre deux polls peut aussi faire reprendre l'enfant sur un autre
thread, sans déplacer leurs états.

**AS5 — Fonction synchrone créatrice.** Une fonction ordinaire peut créer et
retourner une tâche inactive par valeur. Les dépendances de
stockage et les emprunts sont conservés dans son contrat dès la création.
Le contexte implicite nécessaire est requis à la création, pas au premier
`.await`. Une fonction ordinaire ne peut cependant pas suspendre son exécution.

## 2. Stockage des instances et nettoyage

**AS6 — Type d'état propre à chaque définition.** Chaque définition async
possède un type d'état généré, identifié par son nom qualifié, dont la disposition
est connue à la compilation. Deux fonctions de même signature peuvent avoir des
états de tailles différentes. Les annotations `@type`/`@frame` proposées pendant
la discussion ne sont pas retenues.

**AS7 — Pools d'états automatiques.** Le compilateur génère un pool typé par
type d'état et les regroupe dans un super pool fourni au runtime. Les appels
async utilisent automatiquement le contexte et le bon pool ; il n'y a ni
paramètre de pool écrit à chaque appel, ni construction `using`/`ctx.new` à
imposer au programme. Cette injection est une exception explicite à I2/A1/P8
pour le stockage des états async. Les données ordinaires utilisent la
data stack implicite ou le pool typé explicitement choisi selon I2 et A1.

Le contexte, le super pool et chaque pool d'origine doivent survivre à leurs
instances. Le nettoyage suit l'instance réelle du pool, pas seulement son type.
Le compilateur dimensionne chaque pool avec une borne statique des instances
simultanément vivantes lorsqu'il peut l'établir. Sinon, une capacité explicite
est obligatoire. Le diagnostic liste tous les pools non dimensionnés dont la
capacité manque, par nom qualifié, et explique pourquoi la borne est inconnue.
Il n'y a pas de constructeur de pool sans taille.

La configuration au niveau du programme s'écrit :

```rust
#(directive: async_pool_sizes={
    reseau::lire: 4,
    calcul::somme: 12,
})
```

Chaque appel récursif crée une instance distincte ; le parent reste vivant
pendant l'attente. Les branches suspendues conservées par Select comptent
également parmi les instances vivantes.

**AS8 — Contenu de l'état.** L'état conserve le point de reprise et les valeurs
nécessaires à la poursuite de l'exécution : captures, variables, temporaires,
cibles locales encore empruntées, attentes en cours, résultat en attente de
remise et informations nécessaires au nettoyage. Le code est commun aux
instances. Il n'est pas nécessaire de stocker toute variable jusqu'à la fin,
ni d'embarquer un graphe complet d'emprunts au runtime : le suivi reste statique.
La réutilisation interne d'un emplacement exige la fin des usages et emprunts
correspondants.

**AS9 — Adresses stables.** Une instance conserve un stockage stable, y compris
si elle reprend sur un autre thread. Emprunter ses propres variables à travers
une suspension est autorisé si leurs emplacements restent valides et stables.
La suspension ne relâche pas l'exclusivité d'un emprunt mutable.

**AS10 — Terminaison et restitution du résultat.** Tant que le handle peut être
attendu, l'état d'une tâche terminée reste dans son slot et compte dans la
capacité du pool. RT7 définit son nettoyage si le handle est abandonné.
L'attente extrait ou transfère le
résultat hors de l'état avant la récupération du slot. Les valeurs restantes
sont détruites selon les règles applicables ; les valeurs transférées au résultat
ne sont pas détruites avec la tâche. Un retour d'attente garantit que le nettoyage
de la tâche est terminé. Une allocation reçue par transfert, non retournée, est
donc détruite avant ce retour ; son slot est rendu à son pool d'origine. Détruire
un objet contenant un emprunt ne détruit pas la cible simplement empruntée.

**AS11 — Aucun emprunt vers un état détruit.** Retourner un emprunt vers une
variable locale de l'état est refusé si cette variable disparaît à la terminaison.
La durée de vie du pool ne prolonge pas celle de l'instance. Il n'y a ni promotion
implicite, ni rétention implicite de son état pour sauver cet emprunt.

**AS12 — Résultats et provenances.** Les dépendances du résultat sont déduites
par analyse, et non attachées arbitrairement à tous les paramètres. Un `Int`
copié est indépendant. Une référence ou un objet contenant des références
conserve les cibles et réservations nécessaires jusqu'à son dernier usage.
Une allocation retournée par transfert conserve son adresse, sa provenance et
sa dépendance envers son pool ; le receveur prend la responsabilité du nettoyage.
Cette règle couvre notamment le `Result` de TX4 : son `Ok(&str)` conserve
l'emprunt des octets à travers captures, suspensions, await et join. Envelopper
la vue dans un résultat faillible ne prolonge pas la vie de la cible.

## 3. Frontières de scopes et instances inactives

**AS13 — Frontière enfant → parent.** Une tâche ne peut sortir d'un bloc avec un
emprunt vers une donnée locale qui y sera détruite. Transférer la tâche ne
transfère pas implicitement cette cible. Une capture par transfert peut sortir
avec la tâche si le pool d'origine survit assez longtemps ; transférer une
allocation ne prolonge jamais implicitement son pool.

**AS14 — Destruction avant démarrage.** `drop(tache)` sur une instance
inactive détruit ses captures transférées, termine ses emprunts et rend son slot,
sans exécuter son corps. La fin du scope réalise le même nettoyage automatique.
Une instance inactive ni attendue ni explicitement détruite produit un
avertissement. Ce nettoyage ne constitue pas une annulation d'une exécution.

Une tâche inactive peut capturer par valeur le handle d'une tâche déjà
lancée sous réserve de N4. Si la tâche qui le capture est détruite avant
de démarrer, ou si son lancement échoue, le nettoyage abandonne le handle
capturé. Le runtime applique alors RT7 à la tâche lancée.

**AS15 — Captures incompatibles.** Deux instances inactives ne peuvent pas
capturer simultanément un emprunt mutable de la même cible. Les attendre ensuite
successivement ne corrige pas le chevauchement créé lors des captures. La même
restriction vaut pour un emprunt partagé incompatible préparé après un argument
mutable, même si cet argument partagé sert à une sous-expression avec `.await`.

**AS16 — Effets immédiats et effets différés.** Les contrats distinguent les
effets de capture à la création et ceux de l'exécution du corps. Créer une tâche
ne réalise pas immédiatement les mutations ou destructions écrites dans son
corps. L'analyse conserve néanmoins les réservations requises dès la capture et
applique les effets exécutés aux frontières pertinentes. Les exemples historiques
illustrant cette distinction avec `reset()` ne réintroduisent pas cette API,
retirée par PR1 ci-dessous.

## 4. Runtime, scheduler et point d'entrée

**RT1 — Main synchrone.** `fn main() -> Int` est le point d'entrée. `main` reste
toujours synchrone ; l'ancienne proposition d'un `async fn main` est remplacée.
Il peut lancer une tâche et attendre son handle avec `join()`.

**RT2 — Répartition des responsabilités.** Le compilateur génère le super pool
et le code d'intégration. Le runtime est initialisé avec le super pool et expose
les mécanismes communs aux tâches. Le scheduler décide quand et sur quel thread
les exécuter. Son interface utilise le code généré pour reprendre, remettre le
résultat et détruire une instance sans connaître son type concret.
Le runtime prépare les pools et la configuration ; le scheduler gère les
files, réveils et polls. Il peut migrer une tâche entre deux polls, à adresse
stable, avec un seul poll actif par tâche. Un réveil reçu pendant un poll
reste pris en compte : si celui-ci rend Pending, la tâche est remise en file.
Plusieurs réveils peuvent être regroupés. Toute tâche qui reste prête doit
finir par être pollée, à condition que les polls en cours rendent la main.
Cette garantie n'impose ni ordre exact ni délai.

Le runtime intégré fournit un contexte interne à chaque poll. Il identifie
la tâche à réveiller si une opération rend `Pending`. Un `.await` direct
transmet cette cible à la future enfant, de sorte que le réveil rend la tâche
englobante prête. Le contexte peut être enrichi selon les besoins du runtime.
Une éventuelle information sur le thread courant vaut pour le poll en cours.
La cible de réveil reste valable si la tâche change de thread.

**RT3 — Runtime intégré.** Le noyau installe automatiquement le runtime
intégré et son scheduler. Les appels publics du noyau sont
`runtime::spawn`, `runtime::spawn_blocking` et `runtime::thread`, avec
les attentes de RT5. Le mécanisme de remplacement sera repris après
validation des invariants du runtime intégré.

Le contrat statique de `runtime::spawn` est attaché à sa signature.

```rust
#(type: R)
#(type: T<R> with {
    fn id(&self) -> i64;
    fn poll(&mut self, ctx: &mut runtime::Context) -> runtime::Poll<R>;
})
#(branch: join=result.join())
fn spawn(tache: T) -> runtime::Handle<R>
```

Les annotations se lisent de haut en bas. `R` introduit le type du résultat
sans restriction. `T<R> with` exige au moins les méthodes déclarées, avec
leurs signatures. À chaque appel, `T` est le type concret de la tâche
inactive et la signature de `poll` détermine `R`.
`Poll<R>` indique `Pending` ou `Ready(R)`. Le type du résultat détermine
celui du handle. Le passage par valeur déplace la tâche et le vérificateur
conserve les contraintes de ses captures et de ses emprunts.

**Annotation `branch`.** Le compilateur déduit du corps de la fonction
quelle instance est lancée et quelles dépendances elle emporte. Pour
`spawn`, il établit que le handle retourné représente la branche issue de
`tache`. Si ce lien ne peut pas être établi, le contrat est refusé.
Le compilateur suit l'identité de la branche à travers les déplacements
du handle et les appels.
Dans `join=result.join()` et `join=result.await`, `result` désigne le
handle retourné par la fonction annotée. Le compilateur vérifie que ce type
admet la forme d'attente déclarée. Sur chaque chemin
qui rend la main après cette attente, la branche et son nettoyage ont fini
d'accéder à leurs captures. Le compilateur établit cet effet depuis le corps
de la méthode ou depuis le contrat de l'opération interne du runtime.
Un emprunt transmis dans le résultat de l'attente garde ses propres
dépendances.

La forme `#(branch)` omet `join`. Le contrat ne fournit alors
aucun point où la fin des usages de la branche est établie. L'analyse
considère ces usages encore possibles tant qu'elle ne dispose pas d'une
autre preuve. Les deux formes sont soumises à N4 sur chaque chemin.

**Historique du prototype.** `runtime::set_scheduler(scheduler_override)` permet
d'en fournir un autre, développé par l'utilisateur ou une bibliothèque. Aucune
annotation de sélection ou de désactivation n'est retenue. Les appels du
programme restent `runtime::spawn()` et les variantes de l'API commune.

Le prototype sérialise les callbacks `spawn`, `spawn_blocking` et `wake(id)`
sous le mutex du scheduler personnalisé. Les pollers exécutent les polls
hors de ce verrou.

Chaque scheduler gère ses propres files de tâches prêtes et choisit leur
organisation et leur ordre de service. Le runtime fournit les mécanismes
communs de lancement, d'attente et de réveil.

L'installation doit être écrite directement dans `main`, au démarrage et
avant le premier lancement. Elle est refusée dans un auxiliaire, même appelé
par `main`. Aucune migration de tâches actives entre schedulers n'est acquise.
Chaque chemin de `main` peut installer au plus un scheduler personnalisé.
Des branches exclusives peuvent installer des instances différentes. Le
runtime peut également vérifier cette limite à l'exécution.
À l'appel de `runtime::set_scheduler`, le compilateur vérifie que le type
concret de l'instance fournit les méthodes `spawn`, `spawn_blocking` et
`wake` du contrat. Il relie ces méthodes au runtime.

Pour un type concret `MonScheduler`, les signatures exigées sont les
suivantes.

```rust
fn spawn(self: &mut MonScheduler, future: runtime::Future);
fn spawn_blocking(self: &mut MonScheduler, future: runtime::Future);
fn wake(self: &mut MonScheduler, id: runtime::TaskId);
```

Le runtime associe le handle typé à la `Future` avant de la remettre au
scheduler. Les méthodes de lancement reçoivent la `Future` par valeur.
Le scheduler signale un éventuel `LaunchFailed` via cette association.
L'appelant reçoit l'issue du lancement ou le résultat de la tâche en
attendant le handle.

Lors de sa fermeture, le runtime demande l'arrêt au scheduler après le
nettoyage des tâches dont le handle a été abandonné, prévu par RT7. Le scheduler signale l'arrêt
à ses pollers et réveille ceux qui dorment sur une file vide. Le runtime
attend la sortie des pollers hors du mutex du scheduler, puis détruit
l'instance du scheduler.
Le scheduler choisit quand démarrer ses pollers et combien en lancer.
Il les démarre via une primitive dédiée du runtime. Le runtime enregistre
les threads créés et possède leurs handles internes pour les attendre
à l'arrêt.

**RT4 — Multithread et spawn.** Le runtime doit supporter le multithread.
`runtime::spawn(tache)` confie la tâche au scheduler, qui peut réutiliser
un thread existant. Pour `runtime::spawn_blocking(tache)`, le scheduler
tient compte des opérations potentiellement bloquantes pour laisser les
autres tâches progresser.
`runtime::thread` crée explicitement un nouveau thread natif selon RT8.
Chaque lancement rend un handle, y compris en cas d'échec.
`spawn` et `thread` retournent `runtime::Handle<R>` dans les deux
contextes d'appel, synchrone et async.

`spawn_blocking` s'appelle en contexte async. L'appel soumet immédiatement
la tâche au scheduler et retourne un `runtime::AsyncHandle<R>`.

```rust
#(type: R)
#(type: T<R> with {
    fn id(&self) -> i64;
    fn poll(&mut self, ctx: &mut runtime::Context) -> runtime::Poll<R>;
})
#(branch: join=result.await)
fn spawn_blocking(tache: T) -> runtime::AsyncHandle<R>
```

Les signatures consignées pour `spawn` et `thread` exposent leur forme
avec `runtime::Handle<R>`. Leurs contextes de lancement et la forme de
leur API pour un appelant async restent à arbitrer.

Le runtime déplace la `Future` dans le scheduler quand il appelle sa
méthode `spawn` ou `spawn_blocking`. Le scheduler devient responsable
du nettoyage de cette instance via le code généré. Il planifie la tâche
selon RT2 et assure le nettoyage de l'état selon AS10 et RT7. Si le lancement
échoue, il détruit l'état et libère les captures avant de signaler
`LaunchFailed` au runtime.

Un scheduler ne doit jamais exécuter simultanément deux reprises de la même
instance, ni la reprendre après sa destruction. Les réservations et obligations
de nettoyage ne dépendent pas de ses choix d'ordonnancement.

**RT5 — Attentes du handle.** Chaque handle peut être attendu une seule fois.

- `runtime::Handle<R>` expose `execution.join()` en contexte synchrone.
  L'attente bloque le thread appelant jusqu'à la terminaison.
- `runtime::AsyncHandle<R>` expose `execution.await` en contexte async.
  L'attente suspend la tâche appelante et laisse son thread disponible.

Les deux retournent `Result<R, runtime::Error>`. La restriction de `join()`
au contexte synchrone s'applique aussi à travers les fonctions auxiliaires. Ces deux
attentes ont les mêmes garanties de terminaison, nettoyage et visibilité des
écritures. Elles se distinguent de `tache.await`, appliqué à une instance inactive,
dont le résultat est directement le résultat de la tâche.

**RT6 — Erreurs et absence d'annulation.** Les erreurs métier appartiennent au
type de retour de la tâche. Une tâche retournant `Result<T, E>` donne ainsi un
join de type `Result<Result<T, E>, runtime::Error>`.

`runtime::Error` expose `LaunchFailed` si le scheduler échoue à lancer
une tâche ou si le système échoue à créer un thread natif. Le runtime
détruit l'état et ses captures lors de cet échec. L'attente éventuelle
rend ensuite l'erreur. Le code système peut être conservé pour diagnostic.
Tout retour de join, y compris `Err`, garantit que la tâche n'accédera plus
à ses captures. Un éventuel emprunt transmis comme résultat conserve ses propres
restrictions. Il n'y a pas d'annulation de tâche dans le prototype : une tâche
démarrée doit aller jusqu'à une sortie normale selon sa logique. La conversion
des erreurs fatales en erreurs récupérables n'est pas décidée.

**RT7 — Nettoyage des tâches dont le handle est abandonné.**
Lorsqu'un handle est abandonné, le runtime récupère la responsabilité
du nettoyage. À la terminaison de la tâche, il détruit le résultat et les
valeurs restantes, puis rend le slot au pool d'origine. Si la tâche a déjà
terminé, le nettoyage intervient à l'abandon du handle. L'abandon et la
terminaison doivent se coordonner pour effectuer ce nettoyage une seule fois.
La tâche continue selon sa logique jusqu'à sa terminaison. Après la fin de
`main`, le runtime reste actif jusqu'au nettoyage de ces tâches.

**RT8 — Bloc de thread natif.** `runtime::thread` reçoit un bloc synchrone et
crée un nouveau thread. `runtime::thread({ move a; ... })` nomme les captures
et `runtime::thread(move { ... })` les déduit du corps. Le bloc capture
par valeur lors de l'appel. Une capture empruntée se prépare avant l'appel,
avec contrôle de stabilité, durée de vie et compatibilité des accès.
Le compilateur infère `R`
depuis la valeur finale et les retours anticipés du bloc, tous de même type.
Un bloc sans valeur retourne Void. `return` termine ce bloc. Le résultat est
`runtime::Handle<R>` ; le bloc peut appeler join mais ni yield ni await.

Chaque expression bloc transmise directement à `runtime::thread` a son
propre type concret généré par le compilateur, comme une Future. Ce type
décrit les captures et le type du résultat. Deux blocs qui produisent le
même type de résultat peuvent donc avoir des types concrets différents.
Dans le noyau, seul l'argument direct de `runtime::thread` crée un bloc
synchrone destiné à une exécution différée. En position ordinaire,
`{ ... }` et `move { ... }` s'exécutent immédiatement et l'expression
produit le résultat du bloc. Cette distinction rend le moment d'exécution
lisible dans le code. L'appel à `runtime::thread` indique que le corps
s'exécutera sur le nouveau thread.

Si les threads lancés par un scope utilisent sa région, celle-ci
peut être récupérée par retour de son curseur à sa position d’entrée
après leur terminaison et leur nettoyage. Un thread autonome qui
peut survivre au scope doit disposer dès son lancement d’un stockage
qui lui survit. Voir [G10](GROWING_REGIONS.md#3-choix-de-la-stack-et-récupération).

Signature de `runtime::thread`

```rust
#(type: R)
#(branch: join=result.join())
fn thread(bloc: Block<R>) -> runtime::Handle<R>
```

`Block<R>` désigne dans cette signature la famille des types de blocs
synchrones que le compilateur génère pour `thread`. Le paramètre reçoit
par valeur le bloc concret et ses captures. Cette notation est réservée
à la signature du runtime.

La branche correspond à
l'exécution du bloc reçu et ses dépendances sont déduites de ses captures.
Le handle retourné représente cette branche. Le retour de `join()`
établit que la branche et son nettoyage ont fini d'accéder aux captures.
Les dépendances d'un résultat emprunté restent soumises à N4.
Le prototype conserve la tête historique `-> (a, b);` en attendant
l'intégration.

## 5. Sûreté mémoire entre threads

**MT1 — Emprunt mutable réservé.** Une tâche lancée peut capturer un emprunt
mutable local si le compilateur prouve que la cible et son pool survivent à tous
ses accès. L'accès d'origine reste réservé tant que la branche peut utiliser
la cible. L'effet de fin de branche de RT3 permet de lever cette réservation.
Si un résultat emprunté prolonge la réservation, celle-ci continue jusqu'au
dernier usage de ce résultat ou de ses descendants.

**MT2 — Lectures partagées.** Plusieurs tâches et leur appelant peuvent lire
simultanément un même `Int` avec des emprunts partagés. Mutation et destruction
restent interdites tant qu'un de ces emprunts doit servir. Attendre une seule
tâche ne termine pas les réservations des autres.

**MT3 — Vérification par chemin.** Chaque sortie doit établir la terminaison
des tâches qui dépendent des données détruites sur ce chemin. Cela comprend les
retours anticipés et les bras d'erreur. Attendre les tâches seulement à la
fermeture du runtime n'autorise pas la destruction antérieure d'une cible locale.
Détruire un handle ne fournit aucune preuve de terminaison.

**MT4 — Emprunts de l'état parent.** Une tâche peut lancer un enfant empruntant
ses propres variables locales, puis se suspendre, si ces variables restent
stables et si, sur tous les chemins qui détruisent ces variables, les usages
de l'enfant ont pris fin. Le parent respecte la réservation pendant cette période. Un
changement de thread d'exécution du parent ne déplace pas ses variables.

**MT5 — Contrats de handles.** Une fonction peut retourner par transfert le
handle d'une tâche lancée. Son contrat conserve les dépendances aux cibles et
aux sources ; les appels sont vérifiés depuis ce contrat sans reparcourir le
corps. Retourner un handle dépendant d'une allocation locale qui va être
détruite est refusé, même si l'appelant prévoit un join immédiat.

**MT6 — Résultat enveloppé.** Un résultat emprunté reste suivi à travers
`Result<T, runtime::Error>`, avant comme après le match. La fin de la tâche ne rend
pas sa cible destructible si le résultat doit encore l'utiliser. Un résultat
`Int` indépendant permet au contraire de terminer cette dépendance après join.

**MT7 — Pools concurrents.** Des tâches peuvent modifier des allocations
distinctes issues d'un même pool. Allouer exige un accès exclusif au pool ;
des threads peuvent allouer en parallèle chacun dans leur propre pool. Le
runtime synchronise la restitution concurrente de slots distincts issus du
même pool : curseur, index et métadonnées ne subissent pas de concurrence
non protégée. Chaque allocation libère son
slot après destruction ; les adresses des allocations vivantes restent stables.
Cette obligation s'applique aussi aux pools d'états générés. Le mécanisme
interne de synchronisation n'est pas encore choisi.

**MT8 — Déduction structurelle.** Le compilateur déduit récursivement les droits
de transfert et de partage entre threads, sans trait utilisateur obligatoire
pour le prototype. Les valeurs simples comme `Int` sont transférables. Un objet
contenant des références conserve leurs obligations de durée et d'exclusivité ;
une référence partagée exige une cible partageable sans mutation concurrente non
protégée. Une ressource liée à un thread empêche le transfert du contenant.
Les types externes sans contrat suffisant sont refusés par défaut. La notation
des contrats externes et les futurs mécanismes de mutation partagée restent
ouverts ; cette règle n'autorise pas arbitrairement tout type derrière `&`.

**MT9 — Mutex et gardes.** `Mutex::new(valeur)` construit un mutex
synchrone de type `Mutex<T>`, déduit du type de la valeur fournie. Un mutex
possède sa valeur T. Son partage entre
threads exige que l'accès exclusif à T puisse changer de thread, par déduction
structurelle. `lock()` sur un mutex synchrone bloque le thread et produit une
garde unique liée au thread acquéreur : elle ne peut être partagée avec un
autre thread et doit être détruite avant toute suspension.

`AsyncMutex::new(valeur)` construit un mutex asynchrone de type
`AsyncMutex<T>`, déduit du type de la valeur fournie.
`lock().await` sur un mutex async suspend si nécessaire. Sa garde unique est
liée à la tâche et peut survivre à yield/await, y compris après migration. Elle
garde le verrou pendant la suspension et peut réemprunter T en `&mut T` à une
fonction enfant. La garde demeure dans l'appelante. Sa destruction libère le
verrou, éventuellement sur le thread de reprise ; tous ses emprunts dérivés
doivent être terminés. Toutes les sorties de sa portée doivent la détruire.
L'acquisition suivante observe les écritures précédentes. Le compilateur
n'a pas à prouver qu'une attente finira.

**MT10 — Contrat de verrou sur le receveur.** `#(lock: on=self)` déclare
que l'appel prend un verrou exclusif associé à l'instance reçue et le libère
au retour. `#(lock: on=self, through_result=true)` déclare que le résultat
maintient ce même verrou après le retour, jusqu'à sa destruction effective.
Un déplacement du résultat prolonge le suivi jusqu'à la destruction chez
le nouveau receveur.

L'implémentation assure l'acquisition, le maintien et la libération du verrou
à l'exécution. Le compilateur utilise le contrat pour vérifier les usages
côté appelant. Il se fie à l'implémentation pour respecter le contrat.
L'effet décrit par MT10 vient de l'annotation, quel que soit le type qui
implémente le verrou. MT9 décrit les primitives intégrées et leurs gardes.

Avec le contrat suivant, deux appels successifs sur la même instance sont
refusés si le premier résultat est encore vivant au second appel.

```rust
#(lock: on=self, through_result=true)
fn ouvrir(&self) -> Object

// Dans un même bloc, sur la même instance m.
let a = m.ouvrir();
let b = m.ouvrir(); // Refusé. a maintient le verrou sur m.
```

Le second appel attendrait la libération du verrou. Sur ce chemin, la
destruction de `a` en fin de bloc ne peut être atteinte qu'après le retour
du second appel. En plaçant `drop(a)` entre les appels, le verrou est libéré
avant le second appel et le programme est accepté. Avec `#(lock: on=self)`
seul, le premier appel a déjà libéré le verrou à son retour.

Le compilateur traite les deux formes pour les méthodes synchrones et propage
leurs effets à travers les contrats des fonctions synchrones. Le passage
d'un résultat en argument conserve le verrou pendant l'emprunt ou le transfère
avec la valeur. Une capture async propriétaire garde le verrou pendant la
durée de vie de la capture. Si la tâche renvoie directement la valeur,
le résultat d'attente récupère le verrou avec elle. Sur `LaunchFailed`,
le nettoyage de la capture met fin à son effet. Le
[rapport d'intégration](cycles/HASHMAP_LOCK_INTEGRATION_CYCLE.md) précise le
périmètre exercé et les limites.

**SL1 — Groupe de sélection.** `runtime::select_group()` crée un
`runtime::SelectGroup<R>` vide. Le type de résultat `R` peut être annoté
ou déduit d'après les appels à `add`. Chaque tâche ajoutée doit produire
un résultat de type `R`, sur tous les chemins d'exécution.

```rust
let mut group: runtime::SelectGroup<i32> = runtime::select_group();
group.add(lire(&source));
group.add(calculer(41));
let resultat = group.select().await;
drop(group);
```

`group.add(tache)` vérifie le contrat statique de RT3 sur le type concret de
la tâche, avec le `R` du groupe. Il déplace la tâche inactive dans le groupe
et retourne `()`. Le vérificateur conserve les captures, les emprunts et les
obligations de nettoyage propres à chaque tâche.

Le groupe accepte un nombre de tâches déterminé à l'exécution, par exemple
par des ajouts dans une boucle. Chaque état reste dans son pool d'origine.
AS7 détermine la capacité de ce pool. Une entrée `async_pool_sizes` est
requise si le compilateur ne peut pas borner le nombre d'instances
simultanément vivantes.

`group.select()` exige au moins un `group.add(...)` déjà exécuté sur le
même groupe. Le vérificateur refuse l'appel si un chemin qui l'atteint
peut laisser le groupe vide. Ainsi, un `add` dans une seule branche
d'un `if` ne suffit que si les autres chemins ont déjà rempli le groupe
ou n'atteignent pas `select()`.

Dès l'appel à `group.select()`, le groupe se ferme et fixe la liste et
l'ordre de ses branches. Tout `add` ultérieur sur ce groupe est refusé,
y compris après la sélection. Les tâches commencent à s'exécuter au
premier poll déclenché par `.await`.

L'attente emprunte le groupe et obtient son unique résultat. Une deuxième
attente est refusée. Au premier tour toutes les branches sont éligibles,
puis seules les branches réveillées sont repollées. Le poll suit l'ordre
d'ajout parmi les branches éligibles et s'arrête au premier `Ready`.

Après sélection, les perdantes ne sont plus pollées. Leurs états et captures
restent dans le groupe jusqu'à sa destruction. Leurs emprunts gardent leurs
exigences de durée et d'exclusivité jusque-là. La destruction retire une
attente de mutex perdante et rend toute réservation du verrou. Une garde déjà
acquise reste dans l'état perdant et sa destruction libère le verrou.

**SL2 — Handles dans une branche perdante.** Une branche est refusée si elle
peut devenir perdante avec un handle dont l'abandon laisserait des usages
incompatibles avec N4.
Le corps de la branche ne reprend plus après la sélection, même si une
attente y est écrite plus loin. Si N4 reste satisfaite lors de l'abandon du
handle, le runtime applique le nettoyage de RT7.

## 6. Retrait de reset du prototype

**PR1 — Nettoyage par drop et fin de scope.** L'API `pool.reset()`/`memory.reset()`
est retirée de la conception du prototype. Les destructions explicites utilisent
`drop(-> valeur)` et le nettoyage automatique suit les scopes responsables.
La destruction rend le slot au pool selon sa politique ; une réutilisation du
stockage ne réactive jamais les anciens accès. La dernière utilisation d'un
emprunt peut terminer sa réservation, sans déclencher à elle seule la destruction
de sa cible.

La destruction du pool reste subordonnée au nettoyage de ses allocations et à
la fin des tâches dépendantes. Une optimisation interne peut récupérer plusieurs
slots par recul de curseur si elle respecte le comportement observable ; elle
n'exige pas d'API de reset exposée au programmeur.

Cette décision remplace A5 comme API visée du prototype. Les passages historiques
sur les effets de reset, les exemples et les tests existants décrivent encore
l'implémentation antérieure ; leur migration est explicitement différée. Elle
ne supprime pas l'obligation de fermer/libérer les plages au nettoyage du pool.

## 7. Exemples de conception

Ces snippets illustrent les décisions ; leur couverture exécutable doit être
établie séparément. Les exemples historiques utilisent encore certaines
anciennes notations d'allocation.

### Deux tâches empruntant la même cible : attendre avant tout retour

```rust
async fn lire(data: &Int) -> Int {
    yield;
    return *data;
}

fn main() -> Int {
    let mut memory = Pool<Int>::new(1);
    let nombre = new(memory) Int(10);

    let a = runtime::spawn(-> lire(&nombre));
    let b = runtime::spawn(-> lire(&nombre));
    print(nombre); // Lecture partagée autorisée.

    let resultat_a = a.join();
    let resultat_b = b.join();

    // Les deux attentes précèdent tout retour anticipé.
    match resultat_a {
        Ok(valeur) => { print(valeur); },
        Err(erreur) => { print(erreur); return 1; }
    }
    match resultat_b {
        Ok(valeur) => { print(valeur); },
        Err(erreur) => { print(erreur); return 1; }
    }
    return 0;
}
```

Déplacer le match de `resultat_a` avant `b.join()` rend son chemin `Err` invalide :
`b` peut encore lire `nombre` pendant sa destruction. De même, remplacer une
attente par `drop(-> handle)` ne prouve pas la terminaison correspondante.

### Un enfant emprunte le stockage stable de son parent async

```rust
async fn lire(data: &Int) -> Int {
    yield;
    return *data;
}

async fn parent() -> Int {
    let tableau = [10];
    let enfant = runtime::spawn(-> lire(&tableau[0]));
    yield;
    match enfant.await {
        Ok(valeur) => { return valeur; },
        Err(erreur) => { print(erreur); return 1; }
    }
}

fn main() -> Int {
    let execution = runtime::spawn(-> parent());
    match execution.join() {
        Ok(valeur) => { print(valeur); return 0; },
        Err(erreur) => { print(erreur); return 1; }
    }
}
```

Le tableau est conservé dans l'état stable du parent pendant l'emprunt. Un retour
du parent avant l'attente de l'enfant serait refusé.

## 8. Points expressément reportés et décisions remplacées

- Options supplémentaires d'ordonnancement de Select, si un besoin apparaît.
- Frontière avec le C et contrats externes insuffisants ; traits à plusieurs
  méthodes et contraintes entre types concrets, selon les points reportés de
  `design-buffer/points-ouverts.md`.

Le brouillon 04 remplace les anciennes décisions suivantes : thread nouveau
obligatoire pour spawn, `JoinError` non défini, Select
reporté et capacités des pools sans configuration arrêtée. Les règles RT2–RT8,
AS7, MT7, MT9 et SL1–SL2 ci-dessus prévalent. Elles constituent des obligations
d'implémentation, pas des propriétés déjà vérifiées.

Ne sont plus retenus : `routine fn`, `@type`/`@frame`, construction obligatoire
via `ctx` ou `using`, obligation d'attendre immédiatement toute création,
annulation de tâche, runtime uniquement monothread, `async fn main`, annotation
de scheduler et API publique `reset()` du prototype.

## 9. Statut de vérification

Lors de la consignation initiale, ces règles étaient au statut N.
Le compilateur et le runtime ont depuis reçu des implémentations partielles.
La couverture actuelle, les restrictions et les écarts sont détaillés dans
[VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md) et
[ASYNC_DESIGN_CYCLE.md](cycles/ASYNC_DESIGN_CYCLE.md). Les snippets de conception
restent des obligations dont l’exécution doit être établie séparément.
Le retrait de reset est appliqué au profil par défaut. Les tests historiques
qui utilisent reset exigent explicitement le profil de compatibilité.
