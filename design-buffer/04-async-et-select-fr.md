[English](04-async-et-select.md)

# Brouillon 04 — Async, runtime et Select

Décisions validées dans l’atelier, à intégrer sur demande. Les exemples
décrivent la conception retenue et ont été examinés sur papier.

## Types, pools d’états et récursion

- Le type d’une tâche inactive est désigné par le nom qualifié de sa fonction
  async. Chaque définition a son propre type d’état. Après lancement, le type
  public du handle est `runtime::Handle<T>`, avec `T` le type de résultat.
  Le contrat de l’appel conserve les dépendances propres à la tâche.
- Le compilateur analyse le programme, génère un pool par type d’état async
  et regroupe leur initialisation dans une fonction générée qui fournit le
  super pool au runtime. Une borne statique sur les instances simultanément
  vivantes dimensionne le pool quand elle est disponible. Pour chaque
  pool dont il ne peut pas déduire la capacité, le compilateur exige une
  capacité explicite. Le diagnostic liste tous les pools non dimensionnés
  dont la capacité manque, identifiés par le nom qualifié de leur fonction
  async, et indique pourquoi la borne n’a pas été établie. Le constructeur
  de pool sans taille est écarté.
- Chaque appel récursif crée une instance distincte. L’instance parent
  reste vivante pendant l’attente de l’enfant. Une branche suspendue
  conservée par `Select` compte elle aussi parmi les instances vivantes.

Le programme indique les capacités manquantes dans une directive au
niveau du programme. Les valeurs ci-dessous sont des choix du programmeur.

```rust
#(directive, async_pool_sizes={
    reseau::lire: 4,
    calcul::somme: 12,
})
```

## Lancement, attente et résultats

- `runtime::spawn`, `runtime::spawn_blocking` et `runtime::thread`
  rendent tous un `runtime::Handle<T>`, y compris en cas d'échec du
  lancement. `T` est le type du résultat de la tâche ou du bloc natif.
  L'attente du handle restitue `Ok(valeur)` ou `Err(LaunchFailed)`.
- `spawn(-> tache)` prend possession de la tâche et rend un
  `runtime::Handle<T>`. Le scheduler peut utiliser un thread existant.
  Si le lancement échoue, l’état de la tâche est détruit et ses captures
  sont libérées avant que `join()` ou `.await` sur le handle rende l’erreur.
  Le handle doit être attendu dans les deux cas.
- `spawn_blocking(-> tache)` a la même signature et le même contrat de
  capture, de résultat et d’attente. Le scheduler prend en charge le
  caractère potentiellement bloquant de son exécution.
- L’attente directe d’une instance inactive la fait avancer sur le thread
  qui poll l’appelante. Si l’enfant se suspend, l’appelante se suspend avec
  lui. Une reprise de l’appelante sur un autre thread peut reprendre l’enfant
  sur ce thread. Cette attente consomme l’instance inactive et rend directement
  son résultat de type `T`.
- Tout handle lancé doit être attendu explicitement. `join()` est
  réservé au code synchrone, y compris à travers les appels de fonctions.
  Le code async attend le handle avec `.await`. L’obligation suit tout
  transfert du handle. Le compilateur refuse le `drop` du handle et une
  sortie qui abandonne l’obligation. Une instance inactive peut être détruite.
- Sur un `runtime::Handle<T>`, `join()` et `.await` rendent
  `Result<T, runtime::Error>`. Toute issue de l’attente garantit la fin et le
  nettoyage de la tâche. Si la tâche rend `Result<U, E>`, l’attente rend
  `Result<Result<U, E>, runtime::Error>`. Les résultats faillibles suivent la règle
  d’usage explicite du langage.
- `runtime::Error` expose `LaunchFailed` dans cette première version. Cette
  variante couvre un échec de lancement du scheduler ou l’échec système
  de création d’un thread natif. L’attente la rend après le nettoyage
  de l’état et des captures. Le runtime peut conserver le code système
  pour son diagnostic.

## Runtime, scheduler et pools

- Le runtime Crust prépare le super pool et la configuration. Les entrées
  `runtime::spawn` et `runtime::spawn_blocking` délèguent aux méthodes
  correspondantes du scheduler. `runtime::thread` est la primitive
  implémentée par le runtime pour créer explicitement un nouveau thread
  natif. Ces trois opérations forment l’API retenue. `spawn_task` est écarté.
- Le runtime déplace la `Future` dans le scheduler lors de l'appel à sa
  méthode `spawn` ou `spawn_blocking`. Le scheduler prend en charge son
  nettoyage via le code généré. Il planifie la tâche et assure le
  nettoyage de l'état lorsque l'attente consomme le handle. Si le lancement échoue, il détruit
  l'état et libère les captures avant de signaler `LaunchFailed` au runtime.
- Le scheduler pilote l’exécution. Il gère les files, les réveils et les
  polls, et choisit quelle tâche prête reprendre et sur quel thread
  autorisé. Les files font partie de son état. Chaque implémentation
  choisit leur organisation et sa politique d’ordonnancement. Il peut
  reprendre une tâche sur un autre thread entre deux
  polls, à adresse d’état stable. Un seul poll de la tâche est actif à
  la fois. `spawn_blocking` lui signale qu’une tâche async peut occuper
  son thread avec une opération bloquante. Il organise son exécution
  de façon à laisser les autres tâches async progresser.
- Plusieurs threads peuvent demander un appel à `spawn`, `spawn_blocking`
  ou `wake(id)`. Le runtime place le scheduler dans un mutex et sérialise
  ces appels. Chaque méthode reçoit un emprunt mutable du scheduler.
  Les threads ou pollers dédiés, lancés par le scheduler, exécutent les
  polls en dehors de ce verrou. Un seul poll d'une même `Future` peut
  être actif à la fois.
- Le type commun manipulé par le scheduler s'appelle `runtime::Future`.
  Il masque le type concret de la tâche. Le handle remis à l'appelant
  conserve le type du résultat accessible par `join()` ou `.await`.
  `future.poll()` renvoie `Pending` si la tâche suspend son exécution et
  `Ready` si elle a terminé. Le slot reste occupé jusqu'à la consommation
  du handle par `join()` ou `.await`. L'attente extrait le résultat,
  termine le nettoyage de l'état et rend le slot avant de retourner.
  Ces deux états ne transportent aucune valeur métier.
- Le scheduler personnalisé s’installe directement dans `main`, au
  démarrage, avant le premier lancement. Le compilateur refuse
  l’installation ailleurs, y compris dans un auxiliaire appelé par `main`.
  `runtime::set_scheduler(scheduler)` déplace l'instance dans le runtime.
  Le runtime la conserve pendant l'exécution et la détruit après l'arrêt
  de ses workers.
  Chaque chemin de `main` peut installer au plus un scheduler personnalisé.
  Des branches exclusives peuvent choisir des schedulers différents. Le
  runtime peut également vérifier cette limite à l'exécution.
  À l'installation, le compilateur vérifie que le type concret fournit
  les méthodes `spawn`, `spawn_blocking` et `wake` du contrat et relie
  ces méthodes au runtime. Elles prennent le scheduler par emprunt mutable.
  Les deux premières prennent une `runtime::Future` par valeur. `wake`
  prend un `runtime::TaskId`. Ce contrat appartient à l'historique du
  prototype. Le [périmètre retenu pour le noyau](../docs/ASYNC_MULTITHREAD_RULES.md#4-runtime-scheduler-et-point-dentrée)
  utilise le runtime intégré et reporte son remplacement.
  Le runtime associe le handle typé à la `Future` avant sa remise au scheduler.
- Quand `main` termine et que les handles du programme ont été attendus,
  le runtime demande l'arrêt au scheduler. Le scheduler signale l'arrêt
  à ses pollers et réveille ceux qui dorment sur une file vide. Le runtime
  attend leur sortie hors du mutex du scheduler, puis détruit l'instance.
  Le scheduler choisit quand lancer ses pollers et combien en lancer.
  Il passe par une primitive dédiée du runtime, qui enregistre les
  threads créés et conserve leurs handles internes jusqu'à l'arrêt.
- Le runtime signale un réveil au scheduler avec `wake(id)`, où `id`
  identifie la tâche. Le scheduler conserve la `Future` pendant l'attente.
  Un réveil reçu pendant un poll reste pris en compte. Si le poll rend
  `Pending`, la tâche est remise en file. Plusieurs réveils peuvent être
  regroupés en une remise en file.
  Un identifiant désigne une instance de tâche. Un réveil tardif pour une
  instance terminée est ignoré, même si une nouvelle instance réutilise
  le slot de l'ancienne.
- Tout scheduler, par défaut ou personnalisé, doit finir par poller une
  tâche qui reste prête, à condition que les polls en cours rendent la
  main. Cette garantie laisse libres l’ordre exact et le délai.
- Allouer exige un accès exclusif au pool. Des threads peuvent utiliser
  chacun leur propre pool pour allouer en parallèle. Le runtime
  synchronise la restitution concurrente des slots lorsque des tâches
  détruisent des allocations distinctes issues du même pool.

## Thread natif

`runtime::thread` reçoit un bloc synchrone et crée un nouveau thread natif.
`runtime::thread({ move a; ... })` nomme les captures en tête du bloc.
`runtime::thread(move { ... })` capture les liaisons externes utilisées
dans le bloc. Dans les deux formes, la capture a lieu lors de l'appel.
Les valeurs non `Copy` sont déplacées et les valeurs `Copy` sont copiées.
Une capture empruntée se prépare avant l'appel, puis la liaison qui porte
l'emprunt est capturée. Le compilateur vérifie la stabilité, la durée
de vie et la compatibilité des accès aux cibles empruntées.
[Règles de capture](02-marqueur-transfert.md)

Un `return` dans le bloc termine le bloc. La valeur finale et les retours
anticipés doivent avoir le même type `T`. Un bloc sans valeur donne
`Void`. Le résultat de `thread` est un `runtime::Handle<T>`. Le bloc peut
appeler `join()` en synchrone. Un `yield` ou un `.await` dans ce bloc est
refusé. L’appelant async peut attendre le handle avec `.await`.

```rust
async fn lire() -> Result<i32, runtime::Error> {
    let valeurs = [7];
    let vue = &valeurs[0];
    let execution = runtime::thread({
        move vue;
        return *vue;
    });
    return execution.await;
}
```

La forme `runtime::thread(move { *vue })` exprime ici la même capture.
Le prototype utilise encore la tête historique `-> (vue);`. Le passage
aux deux formes `move` est reporté.

## Mutex et gardes

- `Mutex::new(valeur)` construit un mutex synchrone de type `Mutex<T>`.
  Le type `T` est déduit du type de la valeur fournie.
- `AsyncMutex::new(valeur)` construit un mutex asynchrone de type
  `AsyncMutex<T>`. Le type `T` est déduit de la même façon.
- Un mutex possède sa valeur `T`. Plusieurs threads peuvent emprunter le
  même mutex si le compilateur établit que l’accès exclusif à `T` peut
  passer d’un thread à l’autre. Ce contrôle suit la structure de `T`.
- `lock()` sur un mutex synchrone attend en bloquant le thread et rend une
  garde unique, liée au thread qui a acquis le verrou. La garde ne peut être
  partagée avec un autre thread et doit être détruite avant une suspension.
- `lock().await` sur un mutex asynchrone suspend la tâche si le verrou est
  occupé. Une fois acquise, la garde unique est liée à la tâche. Elle peut
  survivre à un `yield` ou à un `.await`, y compris si la tâche reprend sur
  un autre thread. La tâche garde le verrou pendant la suspension et peut
  réemprunter `T` en `&mut T` pour une fonction enfant. La garde demeure
  dans la tâche et la destruction peut libérer le verrou sur le thread
  de reprise.
- La destruction de la garde libère le verrou. Les emprunts qui en dérivent
  doivent se terminer avant sa destruction. Le compilateur exige cette
  destruction sur tous les chemins qui quittent la portée de la garde.
  Il n’a pas à prouver qu’une attente finira. La prochaine acquisition du
  même mutex observe les écritures effectuées sous la garde précédente.

Avec un `compteur` de type mutex asynchrone, la garde reste dans
l’appelante pendant l’attente de `modifier`.

```rust
let mut garde = compteur.lock().await;
yield;
modifier(&mut *garde).await;
yield;
drop(-> garde);
```

## Select

- `runtime::select(-> tache1, -> tache2, ...)` reçoit par transfert les
  instances async et possède leurs états. Toutes les branches retournent
  le même type, choisi par le programmeur. Ce type peut être un enum
  propre à sa logique.
- `selection.await` attend le résultat en empruntant `Select`. Un
  `Select` fournit un seul résultat. Un deuxième `.await` est refusé.
- Au premier tour, toutes les branches sont éligibles. Après un réveil,
  seules les branches réveillées sont repollées. Le poll suit l’ordre
  d’écriture parmi les branches éligibles et s’arrête au premier
  `Ready`. L’ordre d’arrivée des réveils ne change pas cet ordre.
- Après la sélection, les branches perdantes ne sont plus pollées.
  Leurs états et leurs captures restent sous la responsabilité de
  `Select`. La fin de scope ou `drop(-> selection)` détruit ces états.
  Une référence conservée dans une branche perdante garde ses exigences
  de durée de vie et d’exclusivité jusqu’à la destruction de cet état.
- Décision complémentaire validée : dans le prototype, refuser une branche
  qui peut perdre avec un handle lancé dont l'attente n'est pas terminée.
  Aucun join caché ni abandon du handle n'est introduit au nettoyage (SL2).
- Si une branche perdante attendait un mutex, son attente est retirée
  et toute réservation éventuelle du verrou est rendue. Si elle avait
  déjà acquis une garde, celle-ci reste dans son état et la destruction
  de `Select` libère le verrou.

## Exemple admis

```rust
async fn gauche() -> Int {
    yield;
    return 7;
}

async fn droite() -> Int {
    return 9;
}

async fn choisir() -> Int {
    let mut selection = runtime::select(-> gauche(), -> droite());
    let choix: Int = selection.await;
    drop(-> selection);
    return choix;
}

fn main() {
    let execution = runtime::spawn(-> choisir());
    match execution.join() {
        Ok(choix) => { print(choix); },
        Err(_) => { print("échec de l’attente"); },
    }
}
```

Au premier tour, `gauche` suspend son exécution, puis `droite` rend
`9`. Le `drop` de `selection` détruit l’état perdant. `main` attend
explicitement la tâche lancée et traite le `Result<Int, Error>` de `join()`.

## Cas refusés

Les variantes ci-dessous portent sur le programme admis ou sur la directive
de capacité donnée en exemple.

| Variante | Motif du refus |
| --- | --- |
| Appeler `runtime::select(gauche(), -> droite())`. | La première tâche doit être transférée explicitement. |
| Ajouter un deuxième `selection.await` avant le `drop`. | Le premier a déjà obtenu l’unique résultat. |
| Remplacer le `match execution.join()` par `drop(-> execution);`. | Le handle de la tâche lancée doit être attendu. |
| Effectuer un `join()` dans `choisir`, directement ou via une fonction auxiliaire. | Le code async attend avec `.await`. |
| Installer le scheduler dans une fonction auxiliaire appelée par `main`. | L’installation doit avoir lieu directement dans `main`. |
| Omettre `reseau::lire` de `async_pool_sizes` quand sa borne ne peut pas être déduite. | Le compilateur signale le pool et exige une capacité explicite. |
| Écrire `yield` ou `.await` dans un bloc `runtime::thread`. | Le bloc du thread natif est synchrone. |
| Conserver une garde synchrone pendant un `yield`. | Une garde liée à un thread doit être détruite avant une suspension. |
| Partager entre threads un mutex dont le contenu est lié à un thread. | L’exclusivité du verrou ne rend pas le contenu utilisable sur un autre thread. |

## Intégration et points ouverts

- Confirmer AS3 et AS6, compléter AS4 pour l’attente directe et AS7 pour
  la génération, le dimensionnement, `async_pool_sizes` et la récursion.
- Mettre à jour RT2–RT4 pour la délégation au scheduler, son installation,
  ses garanties et la séparation entre `spawn` et `thread`. Compléter MT7
  pour l’accès exclusif lors des allocations et la restitution concurrente
  des slots.
- Aligner RT4–RT6 et MT6 sur `Result<T, runtime::Error>` pour les handles,
  y compris le signalement différé d’un échec de lancement,
  et distinguer ce retour du `T` direct d’AS4. La décision ultérieure
  rattache la validité des dépendances à N4 et réserve RT7 au nettoyage
  par le runtime. Voir le contrat `branch` de RT3.
- Remplacer le point reporté sur `select` de la section 8 par les règles
  validées ci-dessus.
- Compléter AS8–AS9 et MT1–MT4, MT8 pour la migration entre polls,
  les captures du bloc de thread et les gardes des deux types de mutex.

La syntaxe des constructeurs des deux types de mutex reste reportée.
Les options d’ordonnancement de `Select` pourront être abordées si un
besoin apparaît.

[Règles async et multithread](../docs/ASYNC_MULTITHREAD_RULES.md)
