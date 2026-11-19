[Français](PUBLIC_HANDLE_CONTRACTS_CYCLE-fr.md)

<a id="contrats-publics-des-handles"></a>

# Public contracts for the handl

<a id="règles-et-périmètre"></a>

## Rules and scope

Draft 04, AS2/AS13, RT5/RT7 and MT5 require a public type
`runtime::Handle<T>` independent of the frame, with conservation of catches,
There are no normative rules for storage sources and waiting requirements.
is modified by this lot.

Transferred parameters and returns transferred from synchronous functions
now accept this type for scalar results supported
and fixed Int/u8 arrays, including interlocked. Two async functions of
different frames can use the same auxiliary. Signatures
historiques `Execution<fonction>` The programme is still compatible.
in `validation/open-public-handle.crust` runs and displays 7 and 9.

Contracts combine shared, exclusive and re-borrowed catches
The main objective of the project is to:
The contract descriptors do not generate a pool or
The C retains its representation CrustExecution.

<a id="défauts-trouvés-et-corrigés"></a>

## Faults found and corrected

- A caller with only contracts, without a catalogue of async bodies,
  The protection of mutable catches was lost.
  the presence of definitions disabling these loans, they were withdrawn.
  Reproduction : `validation/public-handle-contracts-opaque-o2.log` ;
  correction : `validation/public-handle-contracts-opaque-fixed-o2.log`.
- A Vector shared reborrow created from a mutable parameter became
  All exclusive after switching to the public type. A shared reading
  The contract now retains the capacity separately
  reserved ancestor and the exposed shared mode. Reproduction:
  `validation/public-handle-contracts-opacity-o2.log` ; corrected check:
  `validation/public-handle-contracts-shared-capability-o2.log`.
- Empty sets of catches/sources of a public handle are not
  replaced by a fictional local provenance.

<a id="validation-exécutée-avant-le-complément-sur-les-jonctions"></a>

## Validation performed before the addition on junctions

Clang C11 with pthread, fatal warnings and fatal UBSan, O0/O2.
The 17 methods of `tests/test_public_handle_contracts.py` passent :

- O2, 15,508 s : `validation/public-handle-contracts-arrays-fixed-o2.log`.
- O0, 26,018 s : `validation/public-handle-contracts-arrays-final-o0.log`.
- Regression of 54 methods, 42,951 s:
  `validation/public-handle-contracts-arrays-regression-o2.log` ; contrats,
  Local annotations, opaque calls and pre-existing async tables.

These tests include factories and relays, shared catches and
mutables, pools injected and own captures, re-use after
wait, refusal of launch with single cleaning, results Bool/u8/
Void, Int/u8 and intertwined tables, bad result types even
when the recipient ignores the charge, as well as the prohibited abandonment of the handle.
Invalid programs are checked at verify_program and compile_source.

An independent model combines two targets with three permissions each
(absent, shared, mutable), then read or write on one of the targets:
36 scenarios, 18 of which were executed in C and 18 refused to both entries.
uses the permission table, not the contracts produced by the compiler.
Opaque callers are built without body or inference cards.

Seven errors injected into temporary copies are detected: loss
exclusive, excessive exclusivity, loss of the distinction between re-borrowing and
shared, source erased, deactivation of bodyless loans, absence
scalar load control and lack of form control of tables.
Journal : `validation/public-handle-contracts-arrays-mutations-o2.log`.

The source erasure mutation was initially surviving: the test used
a direct relay, without exercising the wrong substitution through a second
call. The test now keeps an additional string and a caller
opaque; the outdoor pool must be accepted and the block pool refused.
Initial results remain in `…-final-mutations-o2.log`, and the six
changes prior to the supplement tables in `…-chain-mutations-o2.log`.
Initial campaign `…-mutations-o2.log` also contains a fault
inconclusive load control: consumer body failed before
A consumer who ignores the load is isolated from this control.

Extended regressions completed with 312 native methods in 251.441 s
(`…-native-o2.log`) and 275 async methods in 454.787 s (`…-async-o2.log`).
They loaded the code before the last patch of catch groups
and the extension tables; they therefore do not replace the targeted controls
Finals. A previous close selection of 75 methods is passed in 57.287 s
(`…-regression-o2.log`) Series are overlapping and should not be added together.

Failure logs include fixed errors corrected without changing
rules: syntax bool, byte_len method, missing explicit uses and
The following are the main elements of the table:
results and safety are maintained.

<a id="complément--jonctions-de-frames-différentes"></a>

## Complement: junctions of different frames

Results of if, loop and match of distinct async functions can
Now share an identical public type. Unification compares the type
the result, then transforms the catch positions of each frame into
common permission groups before gathering their targets.
storage sources of all possible branches.
not inactive tasks and does not make two different loads compatible.

The programme `validation/public-handle-control-if.crust` was refused with
"same type required in all branches"; this result is reproduced
from the copy of the compiler prior to the junctions and kept in
`validation/public-handle-control-before.log`.

The five methods of `tests/test_public_handle_control.py` go to O2 in
10,547 s (`validation/public-handle-control-injected-pools-o2.log`). Elles
exercise 22 performances C: two branches for if, loop with continuous, match
consumption, shared and mutable, with taken catches then Thong
transferred from two pools plus two results of fixed tables.
The 20 invalid permission/type variants pass through both entries.
Additional opaque callers exercise fifteen refusals (active targets)
and pool too short) and ten acceptances, without any async body available.

Four specific errors are detected: omission of unification in the
contract, omission in the backend, loss of catches of the second branch
and loss of pools captured by an if. The last two make accept to
a wrong access or leak to the opaque caller.
`validation/public-handle-control-mutations-o2.log`.

Direct importation of a test class triggered its complete discovery
by unittest; this launch was interrupted and the module imported instead.
The initial newspaper keeps the interruption. The first match fixtures
consumption have been corrected in `match (-> choice)`. A capture test
owner omitted the T4/T5 intermediate progeny transfers:
the final scenario builds the Strings in the branch via injected pools,
The property tested remains the survival of the pools.

The O0 final pass succeeded: 22 methods, 36,457 seconds,
`validation/public-handle-contracts-control-final-o0.log`. The seven mutations
contracts remain detected after this addition in
`validation/public-handle-contracts-control-mutations-o2.log`.
The final joint regression O2 succeeds: 60 methods, 67,191 s,
`validation/public-handle-contracts-control-final-o2.log`. Elle inclut aussi
historical task/handling contracts, their flow control returns
The regression of loop results passes:
18 methods, 15.984 s, `validation/public-handle-control-loop-results-o2.log`.

An additional historical selection of 71 methods (conditions, loops,
(replacements) ends with 27 sub-case errors and two diagnostic failures,
all related to U1: no explicit use was made of the fixeds allocations.
Journal initial : `validation/public-handle-control-flow-regression-o2.log`.
Two representative methods reproduce these refusals on the front compiler
junctions (`validation/public-handle-control-loop-fixtures-before.log`).
Explicit scalar readings were added to the fixtures.
of exit, trace and order of destruction, re-use and diagnosis
The recovery succeeds: 71 methods in
60,942 s, `validation/public-handle-control-flow-fixtures-fixed-o2.log`.
The fixture diffs are kept in the files
`validation/public-handle-control-u1-*.patch` ; changes in the compiler
in `validation/public-handle-contracts-*.py.patch` and
`validation/public-handle-control-*.py.patch`. The new module
`handle_types.py` contains public descriptors and unification.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Update: Synchronous contracts with allocated results Int, Thong and
Vector<Int/u8>, along with their deceitful envelope, are now being processed
in [the cycle of results allocated](PUBLIC_OWNED_HANDLES_CYCLE.md).
The following limits describe the end of this scalar/table cycle.

- Public signatures of borrowed and proprietary results remain
  The local annotations of these handles are already working.
- Public parameters/returns in async signatures remain open.
  Two minimum programs are kept with their diagnostics in
  `validation/open-public-handle-owned-contract.crust` and
  `validation/open-public-handle-async-parameter.crust`These refusals are
  implementation limits, no new normative rules.
- General catches, replacement of field dependencies,
  Select, the public installation of the scheduler and the guards remain open.
- The historical profile reset refuses a reset in an auxiliary after
  the reset in the appellant after
  The return of the auxiliary is exercised successfully. The conservative refusal is
  retained in `validation/public-handle-contracts-reset-o2.log` ; it does not
  Reset remains removed from the normal profile.
- No new ASan/TSan control, second C compiler or formal evidence.
  Tests do not cover all types or schedules.

The cycle of scalar/table synchronous contracts and their junctions is
The overall objective is not completed; the
above signature limits remain implementation obligations
for the following lots.
