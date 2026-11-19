[Français](ASYNC_BORROWED_LOCAL_RESULTS_CYCLE-fr.md)

<a id="résultats-locaux-async-contenant-des-emprunts"></a>

# Local results async containing borrowings

<a id="portée-et-règles"></a>

## Scope and rules

This lot applies drafts 01/03/04/05, B1/B2/B4a, D1, L1/L2/L6/L7,
T1/T6, ST6–ST15 and AS8–AS14. No normative rules are changed.
The programme `validation/open-async-result-storage-borrowed.crust` is
Now compiled and executed. The local root remains a T, built in
the data stack of the receiver, with its stable address.
have their targets and do not implicitly extend their lifespan.

The structures supported in this lot have Int, &Int and
&mut Int. The origins of their returned fields come from parameters
The contract for the termination of the task shall be drawn up in accordance with the provisions of the contract.
Catches owned by borrowing structures and mixed graphs
The main features of this connection are:

<a id="implémentation"></a>

## Implementation

- Each field of the result retains its targets and reservations through
  creation of a task, a factory, a transfer, await, spawn/join and
  Payload extraction Ok. Select branches bring together targets
  possible; catches of losers remain protected until clean-up.
- Monitoring of the loans stored distinguishes fields, targets and porters.
  The detachment of a shared field does not require keeping its bearer alive;
  the target remains protected until the last use of the detached reference.
- Synchronous functions that await an execution parameter retain
  the origins of the fields in their contract, including through a relay.
  Extracting a Result also retains its symbolic metadata.
- Symbolic verification distinguishes a local root produced by a
  The task of the pools of its catches. A cool local alternative is placed
  in the storage of the receiver; the root of the task already created is preserved.
  The slot of the fresh alternative is recovered if it has not been built.
- A direct local construction in the async body uses the same tracking
  The layout is static: the result
  does not keep any pointer to metadata in the status of the released task.

<a id="défauts-découverts-et-corrections"></a>

## Deficiencies discovered and corrections

The initial connection was losing dependencies when extracting Ok and
Some loans associated with temporary C were left in lieu of the recipient.
the first newspapers keep these refusals and the successive corrections.

The helper that returns the result of a wait or a rescue value
Three differences were revealed: missing local classification, loss of borrowing
in the contract after extraction and absence of recovery of the reserved slot
the branch not taken. This last defect compiled, then the runtime stopped
the programme with `source still has live allocations`. Both paths are
now executed, with an injected launch refusal for the Err branch.

The loop model initially mistook its initial target to be
released before the last use of the result while while may not iterate.
The fixture was corrected to destroy the carrier before this target, without
change the conservative rule at the junction. Two syntax errors in
fixtures are also kept in the intermediate logs.

A layout mutation first survived: it aimed at a pool builder
not exercised by the probe using synchronous helper. Direct construction
added to the test has displayed a valid form still refused. This connection is
The fault now targets its static layout and is detected by
the same oracles of identity and destruction, on both constructions.
Initial survival is not counted as detection.

<a id="preuves-exécutées"></a>

## Evidence

- Suite finale O0 : **17 successful methods**, 21,896 s ; **36 native executions**
  and **36 invalid programs refused in both stages**72 checks.
  Journal : `validation/async-borrowed-local-results-final-counted-o0.log`.
- Baseline finale O2 : **17 successful methods**, 22,075 s ; **neuf mutations
  detected**no survivors or inconclusive in this final campaign.
  Journal : `validation/async-borrowed-local-results-final-mutations-o2.log`.
- Extended regression prior to direct construction supplement:
  **239 methods, 238 successful and one error**, 216,031 s.
  Journal : `validation/async-borrowed-local-results-regression-o2.log`.
  Error is a historical fixture creating `old` without explicit use.
  It is reproduced with the compiler saved before the batch, preloaded
  from its temporary copy: `async-borrowed-local-results-historical-baseline-preloaded.log`.
  The first test without preloading was the current compiler via the
  path of the test module; it does not constitute proof of the old code.
  The fixture now reads old before the historic reset and keeps its assertion
  The public profile does not reintroduce reset.
- Regression on the final compiler: **98 successful methods**, 74,357 s.
  Storage of results, owners graphs, placement parent, helpers,
  pool of structures, storage requirements and runtime growth.
  Journal : `validation/async-borrowed-local-results-final-regression-o2.log`.
- The two historical modules after fixing pass:
  **49 successful methods**, 25,961 s, with UBSan explicitly requested.
  Journal : `validation/async-borrowed-local-results-legacy-fixture-regression.log`.

All the final processes cited are completed with code 0.
initial enlargement and the initial change campaign remain failures
historical details explained above, not successful passages relabelled.

Reproduction controls from the root:

```sh
CRUST_TEST_OPT=-O0 python3 validation/count_async_borrowed_local_results.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 tests/run_async_borrowed_local_result_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_local_owned_result_graphs test_async_local_parent test_async_local_struct_helpers test_async_result_storage test_async_struct_pools test_storage_requirements test_growth_runtime
PYTHONPATH=.:tests CRUST_SANITIZE=undefined python3 -m unittest test_borrowed_returns test_reassignment
```

Targeted suites and 98 methods use Clang C11/pthread harnesses,
with fatal UBSan for the native executions concerned and O0/O2 according to the
journal. The old reset modules use their historical profile;
their recovery explicitly demands `CRUST_SANITIZE=undefined`.

The independent model lists the four parent/child provisions of two
Targets: Both must survive the receiver.
the root and its target, the release of the child state slot, then the
normal or suspended cleaning. They only count one destruction of the target
The changes are derived from loans, origins, transport
after waiting or cleaning the reservation; the last one causes to destroy
a target borrowed as if it were possessed. Oracles remain unchanged
These are finite families, not a global security rate.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Explicit return `Result<View,runtime::Error>` by a helper stays no
connected to the signature system; the valid program is kept in
`validation/open-sync-join-local-payload-type.crust`. This lot covers the helper
which extracts and returns View itself, without removing the other requirement.
General origins by field projections, proprietary catches
of borrowing aggregates, mixed graphs, general signatures and the
Two arbitrations on the handles launched remain open.
No new ASan/Tsan measure or evidence
the general safety, absence of race or optimal placement.

Snapshot : `/tmp/crust-before-async-borrowed-local-results`.
Diffs : `validation/async-borrowed-local-results-*.py.patch`.
The full objective remains active and incomplete.
