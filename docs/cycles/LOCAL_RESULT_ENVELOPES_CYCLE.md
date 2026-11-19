[Français](LOCAL_RESULT_ENVELOPES_CYCLE-fr.md)

<a id="enveloppes-result-de-valeurs-locales"></a>

# Local Values Result Envelopes

<a id="périmètre-et-règles"></a>

## Perimeter and rules

Ce lot applique T1/T6, B1/B2/B4, D1, L1/L2/L6/L7, ST6–ST15,
AS9/AS12, RT6/RT7 and contract storage requirements, without new
The Committee is continuing its work on the implementation of the legislative decision.
The arrows remain explicit; no target promotion borrowed and no
The guidelines for the public reset are not introduced.
VALIDATION_GUIDELINES.md were followed.

The result `Result<T,runtime::Error>` retains the local root T;
`Result<A<T>,runtime::Error>` keeps pool allowance. The difference
is part of the signatures, even when no charge Ok is possible.
The two envelopes do not become interchangeable in an if, a loop,
a notation or a function type constraint.

<a id="défauts-reproduits-et-corrections"></a>

## Reproduced defects and corrections

- `validation/open-sync-join-local-payload-type.crust` : synchronous return of
  the envelope of a local structure containing a loan. The parser keeps
  now storage the load separately from the internal mode join_owned.
  The contracts for parameters, results and methods spread this information.
- The future results of the handles have a distinct identity from their own
  The recovery of the catch by a helper should not be analysed as a
  the new allocation. The entry identity and the symbolic assets of the result
  are now kept during the modular verification.
- The fields borrowed and reservations of the result are carried by the
  Contract verified calls, envelopes and their extraction. Targets
  remain protected after the production state is released.
- `validation/open-async-local-result-envelope.crust` : destination of the
  local root through an async envelope, then a second join.
  and the synchronous bridge now distinguish the shape of the envelope from that
  The failure status of each launch remains distinct.
- The resolution of feature-type methods used a catalogue without the
  Async functions; the valid case caused KeyError. The initial catalog and
  The specialized functions are now being transferred to the analysis.
- `validation/open-local-result-absent-payload.crust` : the child body
  Not normally finished, but its launch may fail.
  proves the absence of a charge; it never infers it from a list of sources
  empty. The envelope descriptor then receives no allocation identity
  This evidence goes through the following
  contracts, blocks, if and loops. A branch capable of finishing retains
  The type of storage remains separately verifiable.
- `validation/open-local-result-mixed-storage.crust` was accepted by the
  two inputs while its branches produce Result<Point>, respectively
  and Result<A<Point>>. Storage control at the junction now refuses
  this mixture, including two proven charges absent.

<a id="couverture-et-oracles"></a>

## Cover and oracles

`tests/test_local_result_envelopes.py` contains 19 methods.
final reports 29 native executions and 36 invalid programmes, each denied
by verify_program and compile_source (72 refusal checks).

The cases admitted check the printed values and, depending on the scenario, the
destruction, the absence of destruction of an unbuilt load and
Reuse of the pool. They cross synchronous relays, opaque contracts,
methods, shared/mutable catches, branches, loops, annotations, results
The programs are interlocked, directly waiting and failed to launch injected.
invalids include premature destruction, too short target, bad
storage, absent transfer and reuse after destruction.

The independent finite model crosses two sources (local/pool) and two signatures
(T/A<T>); he waits for acceptance exactly when they match.
do not consult the compiler's internal choices to define this expectation.
This model does not prove the entire type system.

The infinite bodies of the chargeless scenario are never launched by tests:
The harness injects the refusal at the first launch.
a final path and a path of failure of launch. Type controls
on infinite bodies are only compilations.

The native harness uses Clang C11, pthread, Wall/Wextra/Werrar,
Wno-unused-function, fatal UBSan and O0/O2 levels. Historical regression
also receives CRUST_SANITIZE=undefined when its harness requires this option.
ASan/TSan are not established by this lot.

<a id="chronologie-des-preuves"></a>

## Chronology of evidence

All the newspapers are under `validation/`, prefixed `local-result-envelopes-`.

- `baseline.log`, `initial.log`, `symbolic.log` : refus initiaux ; `identity.log`
  Then run the reproduced program and display 7.
- `tests-o0.log`, `constraints-o0.log`, `expanded-o0.log` : connection of the
  Assets and first cases (5 and then 8 methods).
- `branches-o0.log` : two failures, including a fixture using Bool in context
  synchronous. The fixture uses bool and required transfers; the default
  Result annotation is corrected in `annotations-o0.log` (10 methods).
- `async-probe-initial.log`, `async-placement.log`, `async-tests-o0.log` :
  destination of corrected async envelope (12 methods).
- `bridge-o0.log`, `bridge-contract-o0.log`, `full-o0.log` : requirements of
  storage of the results of propagated handles (14 methods).
- `feature-o0.log`, `feature-catalog-o0.log` : Async catalogue corrected.
- `final-counted-o0.log` 16 methods, 19 executions, 23 invalids/46 refusal.
  `final-mutations-o2.log` detects the ten mutations of this version.
- `regression-o2.log` : 163 methods, a failure of diagnosis expected in
  test_plain_join_contracts; refusal remains correct. The test now recognizes
  the precise diagnosis of charge Result incompatible. `final-regression-o2.log`
  then pass 94 methods, before the correction of the case without charge.
- `absent-probe.log` retains the initial internal refusal. `absent-fixed-probe.log`
  shows 99 and destruction of n after failure injection.
- `absence-tests-o0.log`, `absence-contracts-o0.log`, `absence-storage-o0.log`,
  `absence-relays-o0.log`, `absence-control-fixed-o0.log` keep defects
  intermediates of relays and junctions. `absence-branches-o0.log` pass the
  two dedicated methods, after corrections.
- `completed-count-o0.log` 18 methods, 26 executions, 31 invalids/62 refusals.
  `absence-mutations-o2.log` detects the 14 mutations of this version.
  `absence-regression-o2.log` passes 106 methods in 133.658 s; this process
  had loaded the compiler before the local/pool mixture was corrected.
- `mixed-storage-probe.log` maintain incorrect acceptance at both stages.
  `control-loans-probe.log` checks the three blocks/if/loop shapes with ready.
- `storage-final-o0.log` 19 methods in 17.994 s, 29 native and
  36 invalids/72 refusal, on version including join control.

<a id="audit-des-mutations"></a>

## Audit of deployments

`storage-mutations-o2.log` has a basis of 19 successful methods at O2, then
13 mutations detected and one survivor: suppression of early control
from storage to return. The newspaper `redundant-guard-audit.log` demonstrates on a
minimum program that the construction control of Result still refuses the
It's a redundancy on this scenario, not a bad guy in both stages.
proof of general equivalence of the mutant.

The final runner replaces this redundant injection with the removal of the
the cross-link compatibility check, applied to the counter-example which
The tests and their expectations are not weakened.
The signature mutation of the feature type is detected by the poor diagnosis
Phase: A subsequent storage control still refuses the program.
It does not, therefore, alone demonstrate a dangerous acceptance.

`historical-mutations-o2.log` detects seven historical mutations, then stops
on an expired injection site: the export condition now includes task.
The point is updated by keeping the same fault (forget the Exported Result)
The initial logs are kept.

Final results on the final version:

- `final14-mutations-o2.log` : basis of 19 methods successful in 18,427 s at O2,
  14 mutations detected.
- `historical-mutations-final-o2.log` : basis of 12 successful methods in
  35,657 s, then eight historical mutations detected.
- `final-regressions-o2.log` : 138 successful methods in 149.861 s, modules
  plain_join_contracts, storage_requirements, type_features, async_type_features,
  builtin_features, async_result_storage, async_borrowed_local_results,
  async_failure_only_results, async_local_owned_result_graphs, owned_results and
  nested_plain_results. CRUST_TEST_OPT=-O2 and CRUST_SANITIZE=undefined.

All processes cited in these final results are completed.
closed in the perimeter described; the overall objective remains open.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The scope concerns the families represented in these tests; the catches
owners of borrowing structures, mixed general graphs, signatures
and recursive projections async remain open.
The captured and the losers of Select are waiting for arbitration.
The public scheduler and other open lots are not declared completed.
The finished tests, UBSan and mutations do not constitute general proof of the
The batch differences are kept under the security `validation/`.

The next case is reproduced in
`validation/open-owned-borrowed-structure-capture.crust` : transfer a
local View structure containing &Int to a task that reads its target after
yield. `owned-borrowed-structure-capture-baseline.log` shall retain the refusal to grant
Two steps through the current catch signature restriction.
valid remains to be connected; this lot does not claim to support it.
