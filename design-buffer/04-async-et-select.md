[Français](04-async-et-select-fr.md)

<a id="brouillon-04--async-runtime-et-select"></a>

# Draft 04 — Async, runtime and Select

Validated decisions in the workshop, to be included on request.
describe the design selected and were reviewed on paper.

<a id="types-pools-détats-et-récursion"></a>

## Types, state pools and recursion

- The type of inactive task is designated by the qualified name of its function
  Async. Each definition has its own state type. After launch, the type
  public of the east handle `runtime::Handle<T>`, with `T` the type of result.
  The contract of appeal retains the dependencies of the task.
- The compiler analyzes the program, generates a pool by type of state async
  and groups their initialization into a function generated that provides the
  Super pool at runtime. A static terminal on instances simultaneously
  live dimension the pool when available. For each
  The compiler requires a pool of which it cannot deduce capacity.
  explicit capacity. Diagnostic lists all unsized pools
  whose capacity is lacking, identified by the qualified name of their function
  async, and indicates why the terminal was not established.
  Pool without size is discarded.
- Each recursive appeal creates a separate instance.
  stays alive while waiting for the child. A hanging branch
  retained by `Select` It is also one of the living bodies.

The programme indicates the capacity gaps in a directive at the
The following values are selected by the programmer.

```rust
#(directive, async_pool_sizes={
    reseau::lire: 4,
    calcul::somme: 12,
})
```

<a id="lancement-attente-et-résultats"></a>

## Launch, wait and results

- `runtime::spawn`, `runtime::spawn_blocking` and `runtime::thread`
  rendent tous un `runtime::Handle<T>`, including in the event of failure of the
  lancement. `T` is the type of the result of the native task or block.
  The handl's waiting is returning `Ok(valeur)` ou `Err(LaunchFailed)`.
- `spawn(-> tache)` takes possession of the task and renders a
  `runtime::Handle<T>`. The scheduler can use an existing thread.
  If the launch fails, the task status is destroyed and its catches are taken
  are released before `join()` ou `.await` on the handle makes the mistake.
  The handle must be expected in both cases.
- `spawn_blocking(-> tache)` has the same signature and contract of
  The scheduler supports the capture, result and wait.
  Character potentially blocking its execution.
- Direct expectation of an inactive instance makes it move on thread
  The appellant is not entitled to the same treatment as the applicant.
  he. A repeat of the appellant on another thread may take the child back
  on this thread. This expectation consumes the inactive instance and makes directly
  its type result `T`.
- Any hand launched must be explicitly expected. `join()` is
  reserved for synchronous code, including through function calls.
  The async code is waiting for the handle with `.await`. L’obligation suit tout
  The compiler refuses the transfer of the handle. `drop` of the handle and one
  An inactive instance can be destroyed.
- On one `runtime::Handle<T>`, `join()` and `.await` rendent
  `Result<T, runtime::Error>`. Any outcome of the wait guarantees the end and the
  Clean up the task. If the task makes `Result<U, E>`, l’attente rend
  `Result<Result<U, E>, runtime::Error>`. The results are not reliable according to the rule
  explicit use of language.
- `runtime::Error` expose `LaunchFailed` in this first version.
  variant covers a failure to launch the scheduler or system failure
  creation of a native thread. L
  The runtime can keep the system code
  for his diagnosis.

<a id="runtime-scheduler-et-pools"></a>

## Runtime, Scheduler and Pools

- Runtime Crust prepares the super pool and configuration.
  `runtime::spawn` and `runtime::spawn_blocking` delegate to methods
  The corresponding scheduler. `runtime::thread` is the primitive
  implemented by runtime to explicitly create a new thread
  These three operations form the selected API. `spawn_task` is dismissed.
- Runtime moves the `Future` in the scheduler when calling for its
  method `spawn` ou `spawn_blocking`. The scheduler supports its
  clean up via the generated code. It plans the task and ensures the
  cleaning the state when waiting consumes the handle. If the launch fails, it destroys
  the state and release the catches before reporting `LaunchFailed` Runtime.
- The scheduler controls execution. It manages queues, alarms and alarms.
  poll, and choose which task is ready to resume and on which thread
  The files are part of its state. Each implementation
  He chooses their organization and policy of scheduling.
  resume a task on another thread between two
  The number of the test results is shown in Table 2.
  I'm not. `spawn_blocking` reports that an async task can take on
  his thread with a blocking operation. He organizes his execution
  so that other async tasks can progress.
- Several threads can request a call to `spawn`, `spawn_blocking`
  ou `wake(id)`. Runtime places the scheduler in a mutex and serialise
  Each method receives a mutable loan from the scheduler.
  The dedicated threads or pollers, launched by the scheduler, perform the
  One single poll of the same `Future` peut
  be active at once.
- The common type handled by the scheduler is called `runtime::Future`.
  He masks the concrete type of the task. The handle handed over to the appellant
  keeps the type of result accessible by `join()` ou `.await`.
  `future.poll()` renvoie `Pending` if the task suspends its execution and
  `Ready` If she's done, the slot stays busy until she's consumed.
  by the `join()` ou `.await`. The expectation extracts the result,
  completes the state cleanup and returns the slot before returning.
  Both states do not carry any trade value.
- The custom scheduler installs directly in `main`, in
  start, before the first launch. The compiler refuses
  installation elsewhere, including in an auxiliary called by `main`.
  `runtime::set_scheduler(scheduler)` moves the instance into the runtime.
  Runtime keeps it during execution and destroys it after stopping
  of his workers.
  Each path of `main` can install at most a custom scheduler.
  Exclusive branches can choose different scalers.
  runtime can also check this limit to execution.
  At installation, the compiler checks that the concrete type provides
  methods `spawn`, `spawn_blocking` and `wake` of the contract and linking
  They take the scheduler by mutable borrowing.
  The first two take one `runtime::Future` by value. `wake`
  prend un `runtime::TaskId`This contract belongs to the history of the
  prototype. The [perimeter retained for the kernel](../docs/ASYNC_MULTITHREAD_RULES.md#4-runtime-scheduler-et-point-dentrée)
  uses the built-in runtime and postpones its replacement.
  The runtime combines the typed handle with the `Future` before it was handed over to the scheduler.
- Quand `main` the programme's handlers have been expected,
  The runtime asks the stop to the scheduler. The scheduler reports the stop
  to his pollers and wakes those who sleep on an empty line. Runtime
  wait for them to exit the mutex of the scheduler, then destroy the instance.
  The scheduler chooses when to launch its pollers and how many to launch.
  It passes through a primitive dedicated runtime, which records the
  threads created and kept their internal handles until the stop.
- Runtime signals a wake-up to the scheduler with `wake(id)`where `id`
  identifies the task. The scheduler keeps the `Future` pendant l'attente.
  A wake-up event received during a poll remains taken into account.
  `Pending`, the task is set in motion. Several alarms can be
  grouped into a series of re-runs.
  An ID is a task instance. A late alarm for a
  instance completed is ignored, even if a new instance is reused
  The slot of the old one.
- All scheduler, by default or custom, must eventually pollute a
  the remaining task, provided that the ongoing pollution makes the
  This guarantee leaves the exact order and the time limit free.
- Allouer requires exclusive access to the pool. Threads can use
  Each their own pool to allocate in parallel.
  synchronizes concurrent return of slots when tasks
  destroy separate allocations from the same pool.

## Thread natif

`runtime::thread` receives a synchronous block and creates a new native thread.
`runtime::thread({ move a; ... })` Names the catches in the head of the block.
`runtime::thread(move { ... })` captures the external links used
In both forms, the capture takes place during the call.
Values not `Copy` are moved and values `Copy` are copied.
A borrowed capture is prepared before the call, then the link that carries
The compiler checks the stability, the duration of the loan
and the compatibility of access to borrowed targets.
[Capture rules](02-marqueur-transfert.md)

Un `return` in the block ends the block. The final value and returns
must have the same type `T`. A block without value gives
`Void`. The result of the `thread` is a `runtime::Handle<T>`. The block may
appeler `join()` In synchronous. `yield` ou un `.await` in this block is
refused. L'appellant async can wait for the handle with `.await`.

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

The shape `runtime::thread(move { *vue })` The same capture is expressed here.
The prototype still uses the historical head `-> (vue);`The passage
both forms `move` is postponed.

<a id="mutex-et-gardes"></a>

## Mutex and guards

- `Mutex::new(valeur)` built a synchronous mutex of type `Mutex<T>`.
  The guy `T` is deducted from the type of value provided.
- `AsyncMutex::new(valeur)` built an asynchronous mutex of type
  `AsyncMutex<T>`. The type `T` is deduced in the same way.
- A mutex has its value `T`. Several threads can borrow the
  even mutex if the compiler establishes that exclusive access to `T` peut
  This control follows the structure of the `T`.
- `lock()` on a synchronous mutex waits by blocking thread and makes a
  single guard, linked to the thread that has acquired the lock. The guard cannot be
  shared with another thread and must be destroyed before a suspension.
- `lock().await` on an asynchronous mutex suspends the task if the lock is
  The task of single custody is a matter of responsibility once acquired.
  surviving a `yield` or to a `.await`, including if the task resumes
  another thread. The task keeps the lock during suspension and can
  Reborrow `T` in `&mut T` for a child function.
  in task and destruction can release lock on thread
  (c) the resumption rate.
- The destruction of the guard releases the lock.
  The compiler demands this
  destruction on all paths that leave the range of the guard.
  He doesn't have to prove that a wait will end.
  even mutex observes the scriptures made in the previous custody.

With a `compteur` Asynchronous mutex type, the guard remains in
The appellant while waiting for `modifier`.

```rust
let mut garde = compteur.lock().await;
yield;
modifier(&mut *garde).await;
yield;
drop(-> garde);
```

## Select

- `runtime::select(-> tache1, -> tache2, ...)` receive by transfer the
  instances async and has their states. All branches return
  the same type, chosen by the programmer. This type can be an enum
  It is a logic.
- `selection.await` waits for the result by borrowing `Select`. Un
  `Select` provides a single result. `.await` is refused.
- In the first round, all branches are eligible.
  Only the branches awakened are re-polished. The poll follows the order
  d í writing among the eligible branches and stopping at the first
  `Ready`. The order of arrival of alarms does not change this order.
- After selection, the losing branches are no longer polluted.
  Their states and catches remain under the responsibility of the
  `Select`. The end of the scope or `drop(-> selection)` destroy these states.
  A reference kept in a losing branch keeps its requirements
  of life and exclusivity until the destruction of this state.
- Validated complementary decision: in the prototype, refuse a branch
  which can lose with a handle thrown whose waiting is not over.
  No hidden join or hand-hand abandonment is introduced to the cleaning (SL2).
- If a losing branch waits for a mutex, its expectation is withdrawn
  and any reservation of the lock is returned.
  already acquired a guard, it remains in its state and destruction
  of the `Select` Free the lock.

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

In the first round, `gauche` suspends its execution, and `droite` rend
`9`. The `drop` of the `selection` destroys the losing state. `main` attend
explicitly the task started and deals with the `Result<Int, Error>` of the `join()`.

<a id="cas-refusés"></a>

## Cases rejected

The following variations relate to the programme admitted or to the Directive
of the given capacity as an example.

| Variante | Ground for refusal |
| --- | --- |
| Appeler `runtime::select(gauche(), -> droite())`. | The first task must be explicitly transferred. |
| Add a second `selection.await` before `drop`. | The first has already achieved the only result. |
| Replace `match execution.join()` by `drop(-> execution);`. | The task handle launched must be expected. |
| Effectuer un `join()` in `choisir`, directly or via an auxiliary function. | The async code is waiting with `.await`. |
| Install the scheduler in an auxiliary function called by `main`. | The installation shall take place directly in `main`. |
| Omettre `reseau::lire` of the `async_pool_sizes` when its terminal cannot be deduced. | The compiler reports the pool and requires explicit capacity. |
| Write `yield` ou `.await` in a block `runtime::thread`. | The native thread block is synchronous. |
| Keep synchronous guard during a `yield`. | A thread-related guard must be destroyed before a suspension. |
| Share between threads a mutex whose content is linked to a thread. | The exclusive lock does not make the content usable on another thread. |

<a id="intégration-et-points-ouverts"></a>

## Integration and open points

- Confirm AS3 and AS6, complete AS4 for direct waiting and AS7 for
  generation, dimensioning, `async_pool_sizes` and recursion.
- Update RT2–RT4 for the Scheduler Delegation, its installation,
  the guarantees and the separation between `spawn` and `thread`. Completing MT7
  for exclusive access to allowances and competing refund
  slots.
- Align RT4–RT6 and MT6 with `Result<T, runtime::Error>` for the handls,
  including the delayed reporting of a failed launch,
  and distinguish this return from the `T` the subsequent decision
  links the validity of dependencies to N4 and reserves RT7 to cleaning
  by the runtime. See the contract `branch` RT3
- Replace deferred item on `select` of Section 8 by the rules
  validated above.
- Completing AS8–AS9 and MT1–MT4, MT8 for migration between pollutants,
  The catches of the thread block and the guards of both types of mutex.

The syntax of the manufacturers of both mutex types remains deferred.
The options for scheduling `Select` may be addressed if a
need appears.

[Async and multithread rules](../docs/ASYNC_MULTITHREAD_RULES.md)
