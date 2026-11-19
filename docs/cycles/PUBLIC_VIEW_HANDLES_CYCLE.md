[Français](PUBLIC_VIEW_HANDLES_CYCLE-fr.md)

<a id="contrats-publics-des-handles-à-résultat-vue"></a>

# Public contracts of the handles with a view to the

<a id="périmètre-et-règles"></a>

## Perimeter and rules

Ce lot applique AS12/AS13, RT5/RT6, MT1/MT5/MT6, D1/D3, B1/B2/B4/B5,
TX4/TX5/TX12 and slice rules. It does not introduce any new rules.
Public synchronous signatures now accept &str results,
&u8, &[Int], &[u8], &mut [Int], &mut [u8] and Result<&str,SliceError>.
The same types were already available in concrete tasks; their
Public contract must not lose storage dependencies.

An opaque descriptor keeps active catches and groups separately
Join releases the first; the second still protects
targets up to last use. Alternatives of distinct functions
are combined, without attaching the result to a temporary unlinked capture.
Exclusive capacity may remain necessary behind a shared result.
Static data can provide a view without a dynamic target group.
Public descriptors do not produce any pool or fictitious execution status.

The actual auditor, results contracts and source constraints
The effects analysis also recognizes the type of view
extract from the Join Result: a defect prevented calling byte_len on this
value after a match. The change from a fixed table box u8 to a parameter
&u8 now recognizes its borrowing descriptor; before representation
interne array_ref faisait rejeter ce passage valide.

<a id="contre-exemples-et-exécutions"></a>

## Counter-examples and executions

The initial refusal of the public contract is retained in
`validation/public-view-handles-before.log`. The programme
`validation/open-public-handle-view-contract.crust` is now supported.
The first version of the scenario also contained a block expression at value
textual not connected; scenario now uses ordinary links
and an explicit drop of temporary capture.
not presented as corrected.

The ten methods of `tests/test_public_view_handles.py` passent :

- O0, 31,040 s : `validation/public-view-handles-final-o0.log`.
- O2, 31,337 s : `validation/public-view-handles-final-o2.log`.

C11 compilation by Clang, pthread, fatal warnings and fatal UBSan.
An additional assertion on the semantic constraint of sources is then
added to the test of the two relays: it increases to O0 (0.463 s) and O2 (0.757 s),
journaux `validation/public-view-handles-contract-check-o{0,2}.log`.
No change in the compiler occurs between these passages.

Scenarios include:

- Public relays, helper join, opaque callers without body or async catalogue.
- Destruction of temporary capture after join; destruction or mutation
  a target of the rejected result before its last use, admitted after.
- Shared and mutable bands Int/u8, reborrowing, reading from access
  of reserved origin, writing via view and shared result from a capture
  signatures keep their modes.
- Bytes borrowed from String or fixed table, and static views.
- UTF-8 cutting result wrapped in the Join Result; success, bad
  Border and overtaking; failure of launch injected at execution.
- Historical reset after join: independant pool admitted, target pool
  refused, through relays and conversion of concrete handle to public.
  Reset remains accessible only by explicit compatibility option.

The independent model lists the necessary sets of objects before and after the
after join, for two branches of tasks with interchanged parameters.
The two entries must be rejected.
verify_program and compile_source. The template does not refer to either abstracts or C.
The contract test also checks the obligation to distinguish between the pool
reset and source of the returned capture, regardless of refusal
redundant that can produce concrete backend.

Twelve pre-existing async methods on views, slices, results, fields of
The catch and disjunct parts are increased to O2 in 23.128 s:
`validation/public-view-handles-async-regression-o2.log`.
The extended regression ranged from 132 methods to O2 in 154.293 s:
`validation/public-view-handles-regression-o2.log`. It covers the types and
public contracts for hands, charges allocated and borrowed, cuts
UTF-8 sync/async, borrowed expressions, calculated entries,
It does not represent a performance of
the entire testing of the repository. The Python compilation of the six modules
modified and the three test files/campaigns concerned also succeed.

The intermediate newspapers remain preserved. The first fixtures used
a direct mutable cut that is not recognized; they now use the
slices from split_at_mut. A wait for diagnosis readonly was
aligned with the actual diagnosis, without changing the waiting for refusal.
on the type after match and on the &u8 table argument were flaws of the
compiler, corrected in this batch.

<a id="fautes-injectées"></a>

## Injected defects

Campagne finale : `validation/public-view-handles-mutations-contract-o2.log`,
runner `tests/run_public_view_handle_mutations.py`. Four detected errors:

1. Clearing of the Contract Result Group: the opaque appellant accepts a
   premature destruction.
2. Clearing of projection during concrete conversion to public:
   a valid slice no longer has recognized provenance.
3. Conservation of all catches after join: valid drop of the
   Temporary capture is refused.
4. Clearing the source returned in constraints: the constraint of
   necessary distinction lacks in the contract of the concrete relay.

A mutation survives: changing the exclusive result group to a shared group.
The loan descriptors of the boxes also retain their mutable capacity and
continue to block the accesses tested. No general equivalence of the mutant
is established; it is a limit of coverage, not proof of redundancy
universelle.

The first campaign detected two out of five errors.
It was initially called a factory whose result was already public:
The concrete refusal initially masked the
loss of constraint; the semantic obligation of the contract is now also
The newspapers of these campaigns remain available.

The previous &Int/&mut Int/&mut u8 campaign is replayed after
adaptation of two text anchors that have become ambiguous: five errors detected,
vector box source mutation still survives.
`validation/public-view-handles-borrowed-mutations-o2.log`.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Later update: [SYNC_HANDLE_BRIDGES_CYCLE.md](SYNC_HANDLE_BRIDGES_CYCLE.md)
connects synchronous factories of handles called from states, y
included in the counter example below. Initial limits are retained
to distinguish validation steps.


Public async signatures remain incomplete.
`validation/open-public-view-handle-async-helper.crust` is refused when the
Async body calls a synchronous factory of Handle<&str>; diagnosis
is in `validation/public-view-handles-async-helper-probe.log`.
The programme `validation/open-public-view-result-helper-precision.crust` was
also refused for a dynamic textual result of a synchronous helper in
un corps async (`validation/public-view-result-helper-precision.log`) This gap
is corrected in [SYNC_VIEW_BRIDGES_CYCLE.md](SYNC_VIEW_BRIDGES_CYCLE.md), with
an explicit correction of the drop fixture from a child.
the handle factory remains a limit of implementation.

The AS14/RT6/RT7 arbitration on the capture of a launched handle remains unchanged and in
wait. Select, customizable scheduler, mutex and other global variances
are not solved by this lot. No result new ASan/TSan, second
C compiler or formal proof. Tests cover finished compositions.
Previous Snapshots: `/tmp/crust-before-view-handles` ; diffs reproductibles
retained in `validation/public-view-handles-*.py.patch`.
The overall objective remains active and not completed.
