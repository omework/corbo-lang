[Français](SELECT_RUNTIME_CYCLE-fr.md)

<a id="sl1--rt2--mécanisme-interne-de-sélection-et-réveils-par-branche"></a>

# SL1 / RT2 — Internal selection mechanism and branch alarms

<a id="portée-et-règles"></a>

## Scope and rules

Application of SL1 of draft 04, AS8–AS10, RT2/RT4 and L1/L2.
No normative semantics are changed. This batch provides the mechanism C
interne ; **`runtime::select` is not yet connected to source language**.
It does not therefore constitute a validation of the Select programmes by the
auditor, no closure of the Async site.

The next batch, [suspension cleaning](SUSPENDED_CLEANUP_CYCLE.md), fournit
the callbacks generated for the forms it exercises.
below describe the status of this lot when it is executed.

<a id="implémentation"></a>

## Implementation

`TASK_SELECT_RUNTIME` in `async_runtime.py` has the descriptors of
branches, memorizes the winner and allows a single extraction of the result.
Descriptors are provided by the calling state: no heap allowance
The number of branches is fixed by this storage.

The first poll makes all branches eligible.
that the branches ready, in the order of writing, and stop at the first
Yield re-arms the branch concerned. A branch notification does not
The losers remain possessed after extraction;
their destruction is carried out only at the drop of Select.
Never polluted after her inactive cleaning.

A persistent branch entry now keeps a ticket `forward`
The caller's own ticket remains the target of notifications from the
The alarms thus mark the right branch and then the right one.
go back to the conceivable poll, including in an interlocked selection.
The lock of an entry is released before notifying the next.
frame pointer is not kept between these notifications. Links form
the tree of the possessed states; build a cyclic graph by arbitrary C
is out of contract with this internal interface.

Selecting a result removes routes from branches: notifications
The drop is revoking the roads before
The generations of the entrances prevent an old ticket
to wake up a new instance in the same location. The lifespan
The number of tickets must exceed that of all ticket producers.

The operations on the same Select are exclusive.
They cannot pollute or destroy their branches.
The scheduler retained his existing protocol of one active poll of the appellant.

<a id="nettoyage-suspendu-et-frontière-dintégration"></a>

## Suspension and integration border cleaning

The current generated release contains the cleaning of the inactive instance
and termination cleanups. It does not yet describe all the states
intermediates affected with yield/await: these cleanings must be generated before
make Select available in the language.

Each branch descriptor of the internal mechanism therefore explicitly requires
a callback of suspended destruction. There is no silent withdrawal
Manual probes provide these callbacks.
The real-world frame test uses only two bodies, the only one of which is
state possessed is a transferred capture; for the chosen suspended body,
the cleaning of this capture is still that of the entrance. Its adapter
is not presented as valid for a general body or a local pool.

Another composition requires arbitration: a loser may have launched
a task and wait for his handle. The program and the choices are recorded
in [SELECT_LAUNCHED_HANDLE_DECISION.md](../SELECT_LAUNCHED_HANDLE_DECISION.md).
No hidden joins or additional language restrictions are introduced here.

<a id="scénarios-et-oracles"></a>

## Scenarios and oracles

Seven methods of `tests/test_select_runtime.py` :

- Independent Python model: three branch scripts, 80 scenarios,
  seed 8112026, 3,280 operations. Comparison of the actually polluted branches,
  The winner, the response to awakenings and the retention before destruction.
- Cleaning in four situations: inactive, Pending, unextracted result,
  extract result. Separate suspended destroyer, inverse order of branches
  Independent, no double extraction or release.
- Synchronised wake-up during the poll of a branch: 24 turns, three workers,
  64 notifications combined. Two issues from the appellant and the branch
  Awoke, only one of her neighbor; the loser remains alive until the drop.
- Imbracées selections: alarms received right and left, priority retained
  left; only the chain concerned resumes and cleanings are inserted.
- Competitor ticket producer during detachment, actual release
  frame of the harness and re-use of the same three entries: 16 turns,
  5,000 pairs of late notifications per turn; replacements remain
  The malloc/free belongs only to this harness.
- End of a task started: its subscription awakens the right branch and then
  The winning branch consumes its child before being destroyed.
  This test does not destroy a loser with an active handle.
- Two real frames generated, capture `A<Int>` on each side, winner extracted
  with identical address, losing person retained, re-use of his slot only after
  Drop, eight towers and control all traces of destruction.

The refusals verified here are preconditions/transitions of interface C
(double extraction and expired tickets), not compiler diagnostics
on incorrect Select programs. These remain to be connected.

<a id="exécutions"></a>

## Implementation

Harnais Clang C11, pthread, Wall/Wextra/Werror, UBSan fatal, O0/O2.
Newspapers in `validation/` :

- `select-runtime-initial-o0.log` : five methods, four successful ; overflow
  signed from the track counter of the harness along the towers.
  now reset to zero between the turns. No change in runtime or
  rule to correct this oracle.
- `select-runtime-final-o0.log` Six methods, 1.955 seconds, OK.
- `select-runtime-complete-o0.log` Seven final methods, 2.532 s, OK.
- `select-runtime-complete-o2.log` Seven final methods, 2.732 s, OK.
- `select-runtime-regression-o2.log` 22 methods, 12,405 s, OK, with the
  Six first Select tests, the line ready, wake-ups and spawn_blocking.
- `select-runtime-await-native-o2.log` 26 methods, 25.266 s, OK, covering
  waiting notifications, native blocks and public hand-helds.
- `select-runtime-mutations-o2.log` : baseline of six methods, 2,531 s, OK;
  seven mutations detected by assertions to execution: unawakened pollution,
  reverse order, destruction of losers too soon, notification of parent
  lost, lost road preserved, generation ignored, destructive suspended
  omitted. Mutations only modify C-chains in processes
  separated; oracles are unchanged.
- Compilation Python of successful batch modules.
- `select-runtime-open-source.log` : the arbitration program is refused
  by the parser on `runtime::select` (`attendu ';', reçu ':'`, ligne 19).
  This refusal confirms the absence of a source connection; it does not verify
  the obligation to handle described by the example.

Selections overlap; their methods are not to be added in
The seventh test was added after the campaign of
mutations and selection of 22 methods; it is in both final passes.

## Limites

No formal evidence of competition or new evidence ASan/TSan.
and synchronised interlacings do not exhaust the schedules.
No performance measurement or second compiler C.

Remain: Select syntax/typing, contracts and duration requirements of losers,
general cleaning at each suspension, counting of the states retained in the
capabilities, results of all types, branches with mutex and bonds of
The public replacement of the scheduler is also open.
is a step in implementation, not the realization of all the rules.
