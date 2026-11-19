[Français](SYNC_HANDLE_BRIDGES_CYCLE-fr.md)

<a id="fabriques-synchrones-de-handles-dans-les-états-async"></a>

# Synchronous handle factories in async states

<a id="règles-et-implémentation"></a>

## Rules and implementation

This lot applies AS8/AS10/AS12, RT4–RT8, B1–B5, D1/D3, U1 and obligations
No normative rules are added or modified.
Un corps async peut appeler un auxiliaire synchrone retournant un
runtime::Handle<T>, receive this handle then wait, or write directly
`launch(...).await`. The control of the appeal uses the contract of the auxiliary.
The backend generates a single C function of deck per auxiliary used.

The public contract distinguishes live catches during execution and the
the results targets that remain necessary after waiting.
prepared remain protected during the following arguments, including in the case of
The analysis of async results also recognizes the projections of the
The result of the handle in synchronous contracts; it does not attach the
The source of the catches transferred and the source of the catch
the allowances returned are followed separately.

Runtime receives the Synchronous Crust Execution and consumes it in a
CrustAsyncExecution. A successful thread is detached; a task of the
pool scheduler does not have individual thread to detach; launch
failed keeps his error without attempting to detachment.
The waiting uses the notifications of the state, then extracts the result
before making the slot. Thread no longer touches this state after its publication
As with the existing direct async launches, the handle is the same as the one used for the final release.
source is invalidated and its consumption marker activated.

The symbolic entries borrowed from the bridge are attached to the external storage
The bridge was linked to the local reach of the bridge and refused to provide them with the
wrong the transfer of the returned handle. The allowances possessed received remain
attached to the local scope with their cleaning obligations; this
change does not promote any local program data.

## Contre-exemples

`validation/open-public-view-handle-async-helper.crust` compile and run
Now, with the summer release. L-old refusal of signature is retained in
`validation/sync-view-bridges-next-handle-probe.log`. The first deck test
revealed the poor symbolic connection of borrowings: newspaper
`validation/sync-handle-bridges-initial-probe.log`. After correction, the programme
is executed in `validation/sync-handle-bridges-second-probe.log`.

A second case returned the first sight of two arguments.
The second catch after join was refused by early analysis.
precise projection of the contract corrects this deviation : accurate-probe newspapers
and precision-second of the prefix `validation/sync-handle-bridges-`.

The direct expectation of a factory was still refused while reception
appointed functioned: `validation/open-sync-handle-direct-await.crust`, journaux
direct-wait-probe and direct-wait-second. Both forms are now
The withdrawal of this expectation was refused with a diagnosis of
unknown async function; now receives U1 diagnosis of result
This case was not an accepted invalid program.

Initial &Int/&mut Int tests revealed that their source analysis
The contract of a synchronous factory was not consulted during a wait.
The first direct join tests were waiting for a more diagnostic
specific that the existing match diagnosis; their textual expectation is
The test of acceptance is not changed to refusal.
Intermediate newspapers, including the first two final passes with
incorrect U1 diagnosis, remain retained.

<a id="exécutions"></a>

## Implementation

`tests/test_sync_handle_bridges.py` : 16 methods go together with
Clang C11, pthread, fatal warnings and fatal UBSan:

- O0 : 20,822 s, `validation/sync-handle-bridges-complete-o0.log`.
- O2 : 21,022 s, `validation/sync-handle-bridges-complete-o2.log`.

The scope of the exercise shall include:

- Two synchronous relays, spawn, spamn_blocking and native thread, then wait
  hand in an async body; public annotations and direct expectation.
- Results Int, &str, &Int, &mut Int, Int/u8 shared/mutable bands,
  Result<&str,SliceError>, allocations Int/String/Vector<Int/u8>.
- Protected local captures up to waiting; protected result targets
  after waiting and until last use; unlinked catches released.
- Drop, early exit, double wait and result of abandoned handle
  Join since async remains refused. The order of arguments is observed,
  with mutable capture prepared before a suspended argument.
- Local capacity pools one re-used after waiting/destruction, catches
  owners cleaned on an injected launch refusal, results allocated
  with emergency path and refusal of escape from a local pool.
- Chain of six interlocking factories, seven async levels, two workers per
  default, twelve successive passages. It ends without blocking the workers
  on the waiting of a child and re-uses frames.
- Contract C d ́adoption: four successful/failed launch combinations and
  Pool/joinable execution; retention of pointer and error,
  consumption of the source handle, detachment only when required.

An independent model lists 32 combinations of catches destroyed before/after
wait and two result choices. Six valid scenarios are executed; 26
invalids are refused by verify_program and compile_source. The model calculates
the necessary sets without consulting the compiler's decisions.
Additional check refuses an allowance in the still borrowed pool
by the handle: `validation/sync-handle-bridges-pool-reservation-probe.log`.

Regressions carried out:

- 73 methods O2, 74,645 s: sync bridges, public contracts for hands and
  notifications d’attente, `validation/sync-handle-bridges-regression-o2.log`.
- 24 methods O2, 28.303 s: spawn_blocking and native threads,
  `validation/sync-handle-bridges-native-regression-o2.log`.
- 19 methods O2, 16,408 s: try_slice async and waiting obligations,
  `validation/sync-handle-bridges-await-usage-regression-o2.log`.

The first passage precedes the addition of direct waiting; the second precedes
the last U1 diagnosis; the third and sixteen final targeted tests
cover the last state of the compiler. These are not passages of any
the subsequent repository. The Python compilation of the three modified modules and the
two test files/campaign succeed.

<a id="mutations-et-limites-de-preuve"></a>

## Changes and limits of evidence

`tests/run_sync_handle_bridge_mutations.py` detects six errors: loss of
borrowings of catches, loss of borrowings of the result, omission of the projection
precise result, no detachment of the thread joinable, erasure of the
l , error in launch, lack of consumption of the source handle.
`validation/sync-handle-bridges-mutations-o2.log`This campaign precedes the
direct waiting supplements; its target paths remain unchanged.
The assertions that fail in this journal are those of the transferred copies.

No formal evidence, new result ASan/TSan or second compiler C.
Progress tests do not establish fairness for any program or program.
The mutations are a targeted sample.

<a id="écarts-restants"></a>

## Remaining differences

Update: The Int projections described below are connected in
[SYNC_HANDLE_FIELDS_CYCLE.md](SYNC_HANDLE_FIELDS_CYCLE.md). The following diagnosis
is kept as an historical observation; the new report specifies the limits.

Field projections in the result of a factory are not yet
The minimum program is:
`validation/open-sync-handle-field-result.crust`refusal reproduced in
`validation/sync-handle-bridges-field-result-probe.log`. It is a limit of
implementation, not a new language ban. Signatures
and general catches remain incomplete; this lot does not cover all the
charges accepted by the public syntax of Handle.

The capture of a handle already launched in an inactive instance remains arbitration
AS14/RT6/RT7 documented separately. A factory called during the execution of the
body does not change this point: its handle is created at this moment and must be
The other global topics, including Select, scheduler
Customizable, deferred mutex and general static placement remain open.
Reset remains out of the default prototype.

Snapshot : `/tmp/crust-before-sync-handle-bridges`. Differences retained in
`validation/sync-handle-bridges-*.py.patch`The overall objective remains active.
