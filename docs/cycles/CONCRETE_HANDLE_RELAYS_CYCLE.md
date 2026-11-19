[Français](CONCRETE_HANDLE_RELAYS_CYCLE-fr.md)

<a id="relais-de-handles-concrets-vers-leur-contrat-public"></a>

# Relays of concrete hands to their public contract

<a id="règles-et-correctifs"></a>

## Rules and remedies

AS12/AS13, RT5/RT7, B1–B5, ST11–ST14 and D1/D3 remain unchanged.
A transfer of `Execution<leaf>` To `runtime::Handle<T>` must not lose
the targets of the result, or the mutable capabilities from which they derive.
The reset is tested exclusively in the historical profile authorized by PR1.

The programme `validation/open-concrete-borrowed-handle-relay.crust` failed
with "borrowed catch not found". Public conversion renumbered
the catches of the descriptor consumed. The result check then used
the concrete signature of entry with these new numbers. It now retains
a copy of the input descriptor, without duplicated cleaning responsibility.
The program is run and displays 9.

The conversion of shared results also retains exclusive capacity
An optional empty public group no longer creates a local false target.
The tests cover Int, u8 inline, Int inline fields, &mut Int fields
reborrowed and detachable fields.

The stress model distinguishes the sources necessary to execute the
the parameters necessary for the result borrowed.
of the result; public conversions also retain the other
The sources cross factories, joiners and other
a shared field projection does not add dependence on its
The projections of tables are consistent with the constant and
All possible boxes for a dynamic index are combined.

Historical control also prohibited any re-set in a call receiving
a task, even after its expectation and the last use of its result.
This overall refusal is replaced by orderly constraints.
The opaque application
the contract excludes from the loans still active the tasks consumed by this call,
but keeps those of other living tasks.
last use are not allowed. No reset APIs are reintroduced by default.

A task launched remains likely to access its catches even on a path
The model therefore keeps the executions in progress.
separate from the last ordinary uses: creation at the spawn or reception
a handle, meeting by road, consumption at the join or transfer to a
A reset meets these catches
This also covers a temporary spawn, one of which is an argument that follows.
reset a source.

<a id="preuves-exécutées-et-chronologie"></a>

## Evidence and chronology

The harness executes C11 with Clang, pthread, fatal warnings and UBSan
Compilation limited to 30 seconds and execution to 10 seconds.

`tests/test_concrete_handle_relays.py` contains sixteen methods. The first fourteen pass
at O0 in 13,201 s and O2 in 13,417 s in
`validation/concrete-handle-relay-pending-final-o0.log` and
`validation/concrete-handle-relay-pending-final-o2.log`.
Both complements are for loop convergence with wait/reset
and the distinction between divergent path and continuing path.
16 methods (`concrete-handle-relay-state-final-o*.log`) succeeds fifteen
methods; the remaining fixture used `Bool` for `bool` synchronous and
omits the explicit downward transfer of h into his arm.
corrected entries, the method is changed to O0 (0.541 s) and O2 (0.744 s),
in `concrete-handle-relay-divergent-branch-final-o*.log`. The two failures of
fixture remains recorded; they are not presented as a green cluster.
Cases admitted that differ voluntarily are verified and translated into C,
but are not executed. The ending cases are executed under UBSan.

The life model examines 32 scenarios: waiting or not, eight
destruction sets and two branches. Before join, three catches must be taken
survival; after join, only the two possible targets of the result must be
Six scenarios are executed and 26 rejected at both entrances.
does not use contracts or C to calculate expected permissions.

The other tests check the sources of the contracts independently of the
the execution, then exercise a caller without any body of functions.
the reset after last use, an unreturned catch, an allocation captured
by transfer, another task still active, a refusal to launch injected,
the pool slots reused, and possible backup targets of the result.
The six variants of table sources cross constant/dynamic index
and direct creation/concrete manufacturing.

The first targeted passages revealed a fixture with unused allowance
(deleted only in inline cases), empty public groups taken for
local targets, sources absent from constraints, and both refusals
The overall resets described above. All intermediate logs are
The security statements have not been withdrawn.

The initial regression of 44 methods is then 66.732 s, followed by a selection of
88 methods go in 101,968 s. These passages precede several correctives.
The enlarged campaign (`concrete-handle-relay-regression-final-o2.log`) termine
with 122 methods and an error due to the opaque refusal of the historical reset after
The 122 methods passed in 185,547 s after correction in
`concrete-handle-relay-regression-complete-o2.log`These passages precede the
explicit monitoring of ongoing executions; regression is monitored separately
in `concrete-handle-relay-pending-regression-o2.log` : 122 successful methods
in 125,725 seconds. This last passage precedes the addition of the executions in progress in
the criterion for the convergence of loops, covered by the targeted loop complement.
The table complements 11 pre-existing methods in 53.805 s in
`concrete-handle-relay-array-regression-o2.log`, after projection of the coordinates
and before the monitoring of ongoing executions.

## Mutations

Six errors were detected in temporary copies by
`tests/run_concrete_handle_relay_mutations.py` : no copy of the descriptor
input; empty public group transformed into local target; source of result
concrete erased; owner catches ignored at the join; unjustified retention
of the holder of a shared field; loss of unreturned catches during the
conversion publique. Journal `validation/concrete-handle-relay-mutations-o2.log`.
This campaign precedes the latest opaque application supplements of the reset
and coordinates of tables; it does not cover these new paths.
The final campaign adds two mistakes targeting the ongoing executions: seven
mutations detected and a survivor, recorded in
`validation/concrete-handle-relay-mutations-complete-o2.log`. The script ends
The removal of the control of the
Owner catches at the join is now masked by immediate protection
a first active monitoring campaign targeted the wrong method
to test the release with the join; the direct join scenario followed by reset
detects this second mistake. All the newspapers remain available. No rates.
The general detection method is not derived from these injections.

## Limites

These tests do not establish any general proof of safety or comprehensiveness of the
no errors on all signatures.
ASan/TSan pass or independent C compiler is not claimed.
General async signatures, aggregate owners, Select, replacement
The public of the scheduler and general static placement remain open.
on a launched handle captured by an inactive task is not modified.
Prochain contre-exemple : `validation/open-async-sync-field-replacement.crust`.
Synchronous auxiliary replaces &Int field of a captured structure and then
The two entries refuse this program with
"replacement of field dependencies by a call from an unconnected state".
The diagnosis is kept in `validation/async-sync-field-replacement-probe.log`.
The overall objective remains active.

Snapshot : `/tmp/crust-before-concrete-handle-relay`. Patches preserved in
`validation/concrete-handle-relay-*.py.patch`.
