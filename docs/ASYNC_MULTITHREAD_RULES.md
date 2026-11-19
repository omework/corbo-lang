[Français](ASYNC_MULTITHREAD_RULES-fr.md)

<a id="crust--async-multithread-et-runtime"></a>

# Corbo — async, multithread and runtime

Decisions validated in the discussion, incorporating the latest version of the
draft 04 of `design-buffer`.

This document is a normative extension of [LANGUAGE_RULES.md](LANGUAGE_RULES.md).
It describes the design chosen. The compiler implements a subset of it; the normative
description is not worth a full implementation statement. The following identifiers
allow to follow the evidence in
[VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md).

<a id="1-syntaxe-création-et-suspension"></a>

## 1. Syntax, creation and suspension

**AS1 — Declaration and suspension points.** A suspendable function is
declare with `async fn`. The explicit suspension points are `.await` and
`yield;`. An ordinary function cannot or cannot wait with `.await`, ni utiliser
`yield;`. The keyword `routine` is replaced by `async`.

An async body cannot call directly a `fn` synchrone.
It composes work with the Futures and the existing primitives.
A calculation can be written in a `async fn` and expected with `.await`.
To run on a dedicated thread from this context, the developer
throws his Future with `runtime::spawn_blocking` And wait for the handle.

**AS2 — Inactive creation and immediate capture.** Calling an async function
creates an inactive instance: its body is not yet executed. The arguments are
evaluated from left to right and captured from this creation. Transfers and
borrowings become effective at this time, without waiting for its launch. The
arguments already prepared remain protected during the evaluation of the following,
including if it suspends.

**AS3 — Storeable tasks and value movements.** These two forms are
authorized:

```rust
let resultat = calculer(10).await;

let tache = calculer(20);
let autre = tache.await;
```

A task is no `Copy`. The value passage moves the task while keeping
its storage and catches.

The type of inactive task is written with the qualified or relative name of its
definition async, as `lire` in `fn preparer(data: &i32) -> lire`.
In the event of a name conflict, a relative path that refers to a single definition
is mandatory.
After launch, the public type of handle is `runtime::Handle<T>`where `T`
The contract retains the dependencies of the task.

**AS4 — Expecting an inactive task.** `tache.await` starts the instance and waits
its type result `T`. The expectation consumes the instance from the point of view of
program: it cannot be expected a second time. `yield;` makes it
The child advances on the thread that pollles the appellant; the suspension suspends
the thread. A migration of the appellant between two polllets can also cause the
child to retake on another thread, without moving their states.

**AS5 — Creative synchronous function.** An ordinary function can create and
return an inactive task by value. Storage dependencies and borrowings are kept in his
contract from the creation. The necessary implicit context is required to create, not
first
`.await`. An ordinary function cannot, however, suspend its execution.

<a id="2-stockage-des-instances-et-nettoyage"></a>

## 2. Storage of instances and cleaning

**AS6 — Type of state specific to each definition.** Each definition async
has a type of generated state, identified by its qualified name, the arrangement of
which is known to be in the compilation. Two functions of the same signature may have
different sizes. Annotations `@type`/`@frame` proposed during
the discussion is not retained.

**AS7 — Automatic state pools.** The compiler generates a pool typed by
state type and groups them into a super pool provided to the runtime. Async calls
automatically use the right context and pool; there is neither
pool parameter written at each call, nor construction `using`/`ctx.new` à
This injection is an explicit exception to I2/A1/P8 for storage of async states.
Standard data use the implicit data stack or the explicitly typed pool chosen
according to I2 and A1.

The context, the super pool and each original pool must survive their instances.
Cleaning follows the actual instance of the pool, not just its type. The compiler
dimensiones each pool with a static terminal of the simultaneously living instances
when it can establish it. Otherwise, an explicit capacity is required. Diagnosis
lists all unsized pools whose capacity is lacking, by qualified name, and explains
why the terminal is unknown. There is no single size pool builder.

The configuration at the program level is written:

```rust
#(directive: async_pool_sizes={
    reseau::lire: 4,
    calcul::somme: 12,
})
```

Each recursive call creates a separate instance; the parent remains alive while
waiting. The suspended branches retained by Select are also among the living
instances.

**AS8 — Content of the state.** The state retains the point of recovery and values
The code is common to the instances. It is not necessary to store any variable until
the end, nor to embark a complete graph of borrows at the runtime: tracking remains
static. Internal re-use of a site requires the end of the corresponding usages and
borrowings.

**AS9 — Adresses stables.** An instance maintains stable storage, including
if it resumes on another thread. Borrowing its own variables through a suspension is
allowed if their locations remain valid and stable. The suspension does not release
the exclusivity of a mutable borrow.

**AS10 — Completion and return of the result.** As long as the handle can be
The condition of a completed task remains in its slot and counts in the capacity of
the pool. RT7 defines its cleaning if the handle is abandoned. The waiting extracted
or transfers the result out of the state before the recovery of the slot. The
remaining values are destroyed according to the applicable rules; the values
transferred to the result are not destroyed with the task. A return ensures that the
cleaning of the task is completed. An allowance received by transfer, not returned,
is therefore destroyed before that return; its slot is returned to its original pool.
Destroying an object containing a borrow does not destroy the object simply borrowed.

**AS11 — No borrowing to a destroyed state.** Return a loan to a
local variable of the state is refused if this variable disappears at the end. The
life of the pool does not prolong that of the instance. There is no implicit
promotion or retention of its state to save this borrow.

**AS12 — Results and provenances.** The dependencies of the result are deducted
by analysis, and not arbitrarily attached to all parameters. `Int`
A reference or object containing references retains the necessary targets and
reservations until its last use. An allowance returned by transfer retains its
address, provenance and dependence on its pool; the recipient takes responsibility
for the cleaning.
This rule covers in particular the `Result` TX4: sound `Ok(&str)` conserve
borrowing bytes through captures, suspensions, wait and join. Enveloping the view in
a fallible result does not prolong the life of the target.

<a id="3-frontières-de-scopes-et-instances-inactives"></a>

## 3. Inactivescope boundaries and instances

**AS13 — Child border → parent.** A task cannot get out of a block with a
Transfer the task does not implicitly transfer this target. A transfer capture can
come out with the task if the original pool survives long enough; transfer an
allocation never implicitly prolongs its pool.

**AS14 — Destruction before start-up.** `drop(tache)` on a case
Inactive destroys its transferred catches, terminates its borrowings and renders its
slot, without executing its body. The end of the scope performs the same automatic
cleaning. An inactive instance neither expected nor explicitly destroyed produces a
warning. This cleaning does not constitute a cancellation of a execution.

An inactive task can capture by value the handle of a task already launched subject
to N4. If the task that captures it is destroyed before starting, or if its launch
fails, the clean-up abandons the captured handle. The runtime then applies RT7 to the
task launched.

**AS15 — Captures incompatibles.** Two inactive instances cannot
simultaneously capture a mutable borrow from the same target. Then wait for them
successively does not correct the overlap created during the catches. The same
restriction applies to an incompatible shared borrow prepared after an argument
mutable, even if this shared argument is used for underexpression with `.await`.

**AS16 — Immediate and delayed effects.** The contracts distinguish between the
capture effects at the creation and those of the execution of the body. Creating a
task does not immediately perform the mutations or destructions written in its body.
The analysis nevertheless retains the required reservations from the moment of
capture and applies the effects executed at the relevant borders.
showing this distinction with `reset()` do not re-introduce this API,
removed by PR1 below.

<a id="4-runtime-scheduler-et-point-dentrée"></a>

## 4. Runtime, Scheduler and Port of Entry

**RT1 — Main synchrone.** `fn main() -> Int` is the point of entry. `main` remaining
toujours synchrone ; l'ancienne proposition d'un `async fn main` is replaced.
He can start a task and wait for his handle with `join()`.

**RT2 — Allocation of responsibilities.** The compiler generates the super pool
The runtime is initialized with the super pool and exposes the mechanisms common to
the tasks. The scheduler decides when and on which thread to execute them. Its
interface uses the generated code to resume, return the result and destroy an
instance without knowing its specific type. The runtime prepares the pools and
configuration; the scheduler manages the queues, alarms and poll. It can migrate a
task between two polls, with a stable address, with only one active poll per task. A
wake-up received during a poll remains taken into account: if the poll makes Pending,
the task is set back in line. Several alarms can be grouped together. Any task that
remains ready must end up being polluted, provided that the pollution in progress
makes the hand. This guarantee does not impose any exact order or delay.

The integrated runtime provides an internal context for each poll. It identifies
the task to wake up if an operation makes `Pending`. Un `.await` direct
This target is passed on to the future child, so that the wake-up makes the whole
task ready. The context can be enriched according to the needs of the runtime.
Possible information on the current thread is valid for the ongoing poll. The wake-up
target remains valid if the task changes thread.

**RT3 — Integrated Runtime.** The kernel automatically installs the runtime
The public calls of the kernel are integrated and its scheduler.
`runtime::spawn`, `runtime::spawn_blocking` and `runtime::thread`, with
RT5 expectations. The replacement mechanism will be resumed after validation of the
invariants of the integrated runtime.

The static contract of `runtime::spawn` is attached to his signature.

```rust
#(type: R)
#(type: T<R> with {
    fn id(&self) -> i64;
    fn poll(&mut self, ctx: &mut runtime::Context) -> runtime::Poll<R>;
})
#(branch: join=result.join())
fn spawn(tache: T) -> runtime::Handle<R>
```

The annotations read from top to bottom. `R` introduces the type of result
without restriction. `T<R> with` requires at least the methods reported, with
Each call, `T` is the concrete type of task
inactive and the signature of `poll` determines `R`.
`Poll<R>` indique `Pending` ou `Ready(R)`. The type of result determines
The value passage moves the task and the auditor retains the constraints of his
catches and borrowings.

**Annotation `branch`.** The compiler deduced from the body of the function
which body is launched and which dependencies it takes.
`spawn`, it establishes that the returned handle represents the branch resulting from
`tache`. If this link cannot be established, the contract shall be refused.
The compiler tracks the identity of the branch through the movements
And the phone calls.
In `join=result.join()` and `join=result.await`, `result` means the
The compiler verifies that this type admits the declared form of waiting. On each
path that renders the hand after this expectation, the branch and its cleaning have
finished accessing their catches. The compiler establishes this effect from the body
of the method or from the contract of the internal operation of the runtime. A borrow
transmitted in the result of the waiting keeps its own dependencies.

The shape `#(branch)` omet `join`. The contract does not provide
no point where the end of the uses of the branch is established. The analysis
considers these uses still possible until it has another proof. Both forms are
submitted to N4 on each path.

**Prototype history.** `runtime::set_scheduler(scheduler_override)` permet
The user or library has developed another one. No selection or deactivation
annotation is retained.
programme restent `runtime::spawn()` and variants of the common API.

The prototype serializes callbacks `spawn`, `spawn_blocking` and `wake(id)`
Under the mutex of the custom scheduler. The polluters execute the polluters
Get out of that lock.

Each scheduler manages its own ready-to-use lines of tasks and chooses their
organization and order of service. Runtime provides the common mechanisms for
launching, waiting and waking up.

The installation must be written directly in `main`, at start-up and
before the first launch. It is refused in an auxiliary, even called
by `main`. No active task migration between scedulators is acquired.
Each path of `main` can install at most a custom scheduler.
Exclusive branches can install different instances. Runtime can also verify this
limit to execution.
To the call of `runtime::set_scheduler`, the compiler checks that the type
concrete of the forum provides the methods `spawn`, `spawn_blocking` and
`wake` It links these methods to the runtime.

For a concrete type `MonScheduler`the signatures required are the
suivantes.

```rust
fn spawn(self: &mut MonScheduler, future: runtime::Future);
fn spawn_blocking(self: &mut MonScheduler, future: runtime::Future);
fn wake(self: &mut MonScheduler, id: runtime::TaskId);
```

The runtime combines the typed handle with the `Future` before handing it to the
The launch methods receive the `Future` by value.
The scheduler reports a possible `LaunchFailed` through this association.
The appellant receives the outcome of the launch or the result of the task in
Waiting for the handle.

When the runtime is closed, the runtime asks for a stop at the scheduler after
cleaning the tasks whose handle has been abandoned, provided by RT7. The scheduler
reports the stop to its polluters and wakes up those who sleep on an empty line. The
runtime waits for the polluters to exit the mutex of the scheduler, then destroys the
instance of the scheduler. The scheduler chooses when to start the polluters and how
many of them to launch. It starts them via a dedicated primitive of the runtime. The
runtime records the threads created and has their internal handles to wait for them
at the stop.

**RT4 — Multithread and spam.** Runtime must support multithread.
`runtime::spawn(tache)` entrusts the task to the scheduler, who can reuse
an existing thread. `runtime::spawn_blocking(tache)`, the scheduler
takes into account potentially blocking operations to leave the
Other tasks progress.
`runtime::thread` explicitly creates a new native thread according to RT8.
Each launch returns a handle, including in case of failure.
`spawn` and `thread` retournent `runtime::Handle<R>` in both
call contexts, synchronous and async.

`spawn_blocking` is called in async context. The call immediately submits
the task to the scheduler and returns a `runtime::AsyncHandle<R>`.

```rust
#(type: R)
#(type: T<R> with {
    fn id(&self) -> i64;
    fn poll(&mut self, ctx: &mut runtime::Context) -> runtime::Poll<R>;
})
#(branch: join=result.await)
fn spawn_blocking(tache: T) -> runtime::AsyncHandle<R>
```

Signatures recorded for `spawn` and `thread` expound their form
with `runtime::Handle<R>`. Their launch contexts and the form of
their API for an async caller remain to arbitrate.

Runtime moves the `Future` in the scheduler when he calls his
method `spawn` ou `spawn_blocking`. The scheduler becomes responsible
clean up this instance via the generated code. It plans the task according to RT2 and
cleans the state according to AS10 and RT7. If the launch fails, it destroys the
state and releases the catches before reporting
`LaunchFailed` Runtime.

A scheduler must never simultaneously execute or resume twice the same instance after
its destruction. Reservations and cleaning obligations do not depend on his or her
choice of schedule.

**RT5 — Expectations of the handle.** Each handle can be expected once.

- `runtime::Handle<R>` expose `execution.join()` in synchronous context.
  Waiting blocks the thread calling until the end.
- `runtime::AsyncHandle<R>` expose `execution.await` in async context.
  The wait suspends the calling task and leaves its thread available.

Both return `Result<R, runtime::Error>`. The restriction of `join()`
The two expectations have the same guarantees of termination, clean-up and visibility
of the system.
They are distinct from the `tache.await`, applied to an inactive instance,
the result of which is the direct result of the task.

**RT6 — Errors and no cancellation.** Business errors are the responsibility of the
type of return of the task. A return task `Result<T, E>` donne ainsi un
Type join `Result<Result<T, E>, runtime::Error>`.

`runtime::Error` expose `LaunchFailed` if the scheduler fails to run
a task or if the system fails to create a native thread. The runtime destroys the
state and its captures during this failure. The eventual wait then makes the error.
The system code can be kept for diagnosis.
Any return of join, including `Err`, ensures that the task will no longer access
A possible borrow transmitted as a result retains its own restrictions. There is no
task cancellation in the prototype: a task started must go up to a normal output
according to its logic. The conversion of fatal errors into recoverable errors is not
decided.

**RT7 — Cleaning of tasks whose handle is abandoned.**
When a handle is abandoned, the runtime recovers the responsibility for cleaning. At
the end of the task, it destroys the remaining results and values, then returns the
slot to the original pool. If the task has already been completed, the clean-up takes
place at the end of the handle. The abandonment and termination must be coordinated
to perform this clean-up only once. The task continues according to its logic until
it is finished.
`main`, the runtime remains active until these tasks are cleaned.

**RT8 — Native thread block.** `runtime::thread` receives a synchronous block and
creates a new thread. `runtime::thread({ move a; ... })` name the catches
and `runtime::thread(move { ... })` The block captures them from the body.
A borrowed capture is prepared before the call, with stability control, life and
access compatibility.
The compiler's inferior `R`
from the final value and the anticipated returns of the block, all of the same type.
A block without value returns Void. `return` ends this block. The result is
`runtime::Handle<R>` ; the block can call join but neither yield nor wait.

Each block expression transmitted directly to `runtime::thread` a its
This type describes the catches and the type of result. Two blocks that produce the
same type of result can therefore have different concrete types.
In the kernel, only the direct argument of `runtime::thread` creates a block
In the ordinary position,
`{ ... }` and `move { ... }` execute immediately and expression
produces the result of the block. This distinction makes the execution time
The call to the `runtime::thread` indicates that the body
run on the new thread.

If the threads launched by a scope use its region, it can be recovered by returning
from its cursor to its input position after they have been terminated and cleaned. An
autonomous thread that can survive the scope must have storage at its launch
who survives him. See [G10](GROWING_REGIONS.md#3-choix-de-la-stack-et-récupération).

Signature of `runtime::thread`

```rust
#(type: R)
#(branch: join=result.join())
fn thread(bloc: Block<R>) -> runtime::Handle<R>
```

`Block<R>` means in this signature the family of block types
synchronous that the compiler generates for `thread`. The parameter receives
by value the concrete block and its catches. This notation is reserved
at the signature of the runtime.

The branch corresponds to
the execution of the received block and its dependencies are deducted from its catches.
The returned handle represents this branch. `join()`
establishes that the branch and its cleaning have finished accessing the catches.
Dependencies of a borrowed result remain subject to N4.
The prototype retains the historic head `-> (a, b);` in the meantime
integration.

<a id="5-sûreté-mémoire-entre-threads"></a>

## 5. Memory security between threads

**MT1 — Reserved transferable borrowing.** A task started can capture a loan
local mutable if the compiler proves that the target and its pool survive all its
accesses. Original access remains reserved as long as the branch can use the target.
The end-of-branch effect of RT3 allows to lift this reservation. If a result borrowed
extends the reservation, it continues until the last use of this result or its
descendants.

**MT2 — Shared readings.** Several tasks and their callers can read
at the same time `Int` with shared borrowings. Mutation and destruction
remain prohibited as long as one of these borrows is to be used. Waiting for a single
task does not end the reservations of others.

**MT3 — Checking by road.** Each output must establish the termination
tasks that depend on the destroyed data on this path. This includes early returns and
arms of error. Waiting for tasks only when the runtime closes does not allow the
previous destruction of a local target. Destroying a handle provides no proof of
termination.

**MT4 — Borrowings of the parent state.** A task can start a child borrowing
If these variables remain stable and if, on all the paths that destroy these
variables, the child's uses have ended, the parent respects the reservation during
this period. A change in the parent's execution thread does not move its variables.

**MT5 — Handling contracts.** A function can return by transfer on
The contract retains the dependencies of the targets and sources; calls are checked
from this contract without re-routing the body. Returning a handle dependent on a
local allowance that is to be destroyed is refused, even if the appellant provides
for an immediate join.

**MT6 — Result wrapped.** A borrowed result remains followed through
`Result<T, runtime::Error>`, before as after the game. The end of the task does not make
not its destructible target if the result still needs to use it.
`Int` On the contrary, independent means that this dependency can be completed after join.

**MT7 — Pools concurrents.** Tasks may change allocations
Allouer requires exclusive access to the pool; threads can be allocated in parallel
to each in their own pool. The runtime synchronizes the competing return of separate
slots from the same pool: cursor, index and metadata are not subject to unprotected
competition. Each allocation releases its slot after destruction; the addresses of
living allocations remain stable. This obligation also applies to generated state
pools. The internal synchronization mechanism is not yet chosen.

**MT8 — Structural deduction.** The compiler recursively deducts the duties
transfer and sharing between threads, without user-related requirement
for the prototype. Simple values as `Int` are transferable.
With references, they retain their obligations of duration and exclusivity; a shared
reference requires a shared target without unprotected competing transfer. A thread
resource prevents the transfer of the container. External types without sufficient
contract are refused by default. Notation of external contracts and future shared
transfer mechanisms remain
open; this rule does not arbitrarily allow any type behind `&`.

**MT9 — Mutex and guards.** `Mutex::new(valeur)` construit un mutex
type synchronous `Mutex<T>`, deducted from the type of value provided. A mutex
has its value T. Its division between
Threads requires that exclusive access to T may change thread, by deduction
structurelle. `lock()` on a synchronous mutex blocks thread and produces a
single guard linked to the purchaser thread: it cannot be shared with another thread
and must be destroyed before any suspension.

`AsyncMutex::new(valeur)` built an asynchronous mutex of type
`AsyncMutex<T>`, deducted from the type of value provided.
`lock().await` on a mutex async suspends if necessary. Its sole guard is
related to the task and can survive Yield/await, including after migration.
keep the lock during suspension and can re-borrow T in `&mut T` at
Child function. Custody remains in the appellant. Its destruction releases the lock,
possibly on the recovery thread; all its derivative borrowings must be completed. All
exits from its range must destroy it. The following acquisition observes the previous
writings. The compiler does not have to prove that a wait will end.

**MT10 — Locking contract on receiver.** `#(lock: on=self)` declare
that the call takes an exclusive lock associated with the received proceeding and releases it
on the way back. `#(lock: on=self, through_result=true)` states that the result
Keeps the same lock after the return, until it is destroyed.
A shift in the result prolongs the follow-up until destruction in the
the new receiver.

The implementation ensures the acquisition, maintenance and release of the lock to
execution. The compiler uses the contract to verify the uses on the calling side. It
relies on the implementation to comply with the contract. The effect described by
MT10 comes from the annotation, regardless of the type that implements the lock. MT9
describes the integrated primitives and their guards.

With the next contract, two successive appeals on the same instance are refused if
the first result is still alive in the second appeal.

```rust
#(lock: on=self, through_result=true)
fn ouvrir(&self) -> Object

// Dans un même bloc, sur la même instance m.
let a = m.ouvrir();
let b = m.ouvrir(); // Refusé. a maintient le verrou sur m.
```

The second call would wait for the lock to be released.
destruction of `a` at the end of the block can only be reached after the return
of the second call. `drop(a)` between calls, lock is released
before the second call and the program is accepted. `#(lock: on=self)`
The first call alone has already released the lock on his return.

The compiler treats both forms for synchronous methods and propagates their effects
through synchronous function contracts. The passage of an argument result keeps the
lock during the borrowing or transfers it with the value. An async owner capture
keeps the lock during the lifetime of the capture. If the task returns the value
directly,
The waiting result recovers the lock with it. `LaunchFailed`,
the clean-up of the catch puts an end to its effect.
[Integration report](cycles/HASHMAP_LOCK_INTEGRATION_CYCLE.md) specify the
The scope and limits.

**SL1 — Selection group.** `runtime::select_group()` creates a
`runtime::SelectGroup<R>` empty. The type of result `R` may be annotated
or deducted from calls for `add`. Each added task must produce
a type result `R`, on all the tracks of execution.

```rust
let mut group: runtime::SelectGroup<i32> = runtime::select_group();
group.add(lire(&source));
group.add(calculer(41));
let resultat = group.select().await;
drop(group);
```

`group.add(tache)` checks RT3's static contract on the concrete type of
the task, with the `R` group. It moves the inactive task in the group
and returns `()`. The auditor shall keep the catches, borrowings and the
clean-up obligations specific to each task.

The group accepts a number of tasks determined at the execution, for example by
adding to a loop. Each state remains in its original pool.
AS7 determines the capacity of this pool. `async_pool_sizes` is
if the compiler cannot limit the number of instances
At the same time, they are alive.

`group.select()` requires at least one `group.add(...)` already executed on the
the same group. The auditor refuses the call if a path that reaches it
can leave the group empty. `add` in one branch
d'un `if` only if the other paths have already filled the group
or do not reach `select()`.

From the call to `group.select()`, the group closes and sets the list and
the order of its branches. `add` the subsequent on this group is refused,
The tasks begin to be performed at the
first pollution triggered by `.await`.

The waiting takes the group and gets its only result. A second waiting is refused. On
the first round all branches are eligible, then only the branches awakened are
re-pollinated. The poll follows the order
of the eligible branches and stops at the first `Ready`.

After selection, the losers are no longer polluted. Their states and catches remain
in the group until its destruction. Their borrowings keep their requirements of
duration and exclusivity until then. The destruction removes a waiting for losing
mutex and makes any reservation of the lock. An already acquired guard remains in the
losing state and its destruction releases the lock.

**SL2 — Handles in a losing branch.** A branch is refused if it
can lose with a handle whose abandonment would leave usages incompatible with N4. The
body of the branch no longer resumes after selection, even if a wait is written
further there. If N4 remains satisfied when the handle is abandoned, the runtime
applies the cleaning of RT7.

<a id="6-retrait-de-reset-du-prototype"></a>

## 6. Retrieving the prototype

**PR1 — Drop and end of scope cleaning.** L'API `pool.reset()`/`memory.reset()`
is removed from the design of the prototype. Explicit destructions use
`drop(-> valeur)` and automatic cleaning follows the responsible telescopes.
Destruction renders the slot to the pool according to its policy; a reuse of storage
never reactivates old accesses. The last use of a borrow can complete its
reservation, without triggering the destruction of its target alone.

The destruction of the pool remains dependent on the cleaning of its allocations and
the end of the dependent tasks. An internal optimization can recover multiple slots
by slide backwards if it respects the observable behavior; it does not require a
reset API exposed to the programmer.

This decision replaces A5 as the target API of the prototype. Historical passages on
reset effects, examples and existing tests still describe the previous
implementation; their migration is explicitly delayed. It does not remove the
obligation to close/freeze the beaches when cleaning the pool.

<a id="7-exemples-de-conception"></a>

## 7. Design examples

These snippets illustrate the decisions; their executable coverage must be
established separately. Historical examples still use some old allocation ratings.

<a id="deux-tâches-empruntant-la-même-cible--attendre-avant-tout-retour"></a>

### Two tasks with the same target: wait before returning

```rust
async fn lire(data: &Int) -> Int {
    yield;
    return *data;
}

fn main() -> Int {
    let mut memory = pool<Int>(1);
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

Move match from `resultat_a` avant `b.join()` Makes his way back `Err` invalide :
`b` peut encore lire `nombre` the destruction of the vessel.
waiting by `drop(-> handle)` does not prove the corresponding termination.

<a id="un-enfant-emprunte-le-stockage-stable-de-son-parent-async"></a>

### A child borrows stable storage from his or her parent async

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

The table is kept in the stable state of the parent during the borrow. A return of
the parent before the child's waiting would be refused.

<a id="8-points-expressément-reportés-et-décisions-remplacées"></a>

## 8. Items expressly deferred and decisions replaced

- Select additional scheduling options, if a need appears.
- Border with C and insufficient external contracts; several features
  methods and constraints between specific types, depending on the points carried over from
  `design-buffer/points-ouverts.md`.

Draft 04 replaces the following old decisions: thread new
compulsory for spawn, `JoinError` undefined, Select
The RT2–RT8, AS7, MT7, MT9 and SL1–SL2 rules above prevail. They are implementation
obligations, not already verified properties.

No longer retained: `routine fn`, `@type`/`@frame`, construction obligatoire
via `ctx` ou `using`, obligation to wait immediately for any creation,
task cancellation, runtime only monothread, `async fn main`, annotation
to scheduler and public API `reset()` Prototype.

<a id="9-statut-de-vérification"></a>

## 9. Verification status

At the time of the initial recording, these rules were in N status. The compiler and
runtime have since received partial implementations. The current coverage,
restrictions and deviations are detailed in
[VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md) and
[ASYNC_DESIGN_CYCLE.md](cycles/ASYNC_DESIGN_CYCLE.md). Design snippets
The rest of the reset is applied to the default profile. Historical tests that use
reset explicitly require the compatibility profile.
