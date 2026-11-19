[Français](ASYNC_STRUCT_POOLS_CYCLE-fr.md)

<a id="pools-de-structures-dans-les-états-async"></a>

# Pools of structures in async states

<a id="portée-et-règles"></a>

## Scope and rules

This lot continues the drafts 03/04/05 and ST1–ST4, ST15–ST16 rules,
A1–A4/P8, D1, AS8–AS14. Normative documents are not modified.
The case retained in `validation/open-async-result-factory-local_struct_pool.crust`
The backend was only creating Int/String/Vector pools.
It is now compiled and executed with result 7.

Local and injected pools now accept structures whose graph
finished contains Int fields and A<T> proprietary fields of families already
The Intrusive fields are those of the existing flattened layout.
Structures containing references are not added by this lot.

<a id="implémentation"></a>

## Implementation

- The Pool Source, its unique slot stack and the resident field tables
  The addresses of the cells remain valid between two polls.
  use the same layout and destroyers as the synchronous backend.
- Named fields are evaluated in the written order. Each value is saved
  before the next argument, even if it suspends.
  zero; no absent proprietary field is invented.
- Field transfers remain the responsibility of a temporary group
  until complete construction. An early return or cleaning of a
  instance not launched suspended destroys fields already prepared once.
- The source preserved includes the root pool and the sources of the descendants.
  A structure cannot come out of a block that closes one of these pools.
- A newly constructed result in an injected pool keeps in its
  contracts the sources of its own fields, separately from the source of the
  This is going through synchronous factories and their relays.
- An attempt to move a local pool is now diagnosed
  explicit; previously it failed on the form of unconnected expression.

<a id="contre-exemples-et-corrections-intermédiaires"></a>

## Counter-examples and intermediate corrections

The first probes included physical closures such as calls to
`source_close`. A pool of structures closes its envelope and then its stack of slots:
The probe counter sees two calls. Expectations have been corrected, without
change the cleaning. One case of exhaustion had also deleted the use only
explicit allowance by withdrawing the drop; a reading was added before
the attempt to allocate which must fail.

The new case of a return of a structure built in an injected pool revealed
the contract and its application have been
The neighbors whose pool of descendants is too short are refused.

Two shapes tested during the construction of the graph fixture remain
outside perimeter: a helper using the general owner graph, and access
`*t.left.n` The latter is kept in two fields A<T>.
`validation/open-async-struct-pool-owned-projection.crust`. The cleaning test
recursive reads an Int field of the root and controls separately destruction
The exactness of each of the descendants; he does not claim the projection absent.

The first extended regression was recorded in the following two countries:
completed 126 entries with import error (`test_async_collection_creation`,
the other 125 entries have been successful. The corrected command uses
`test_async_collection_new`. Two attempts at the final sequel did not start
because of a module name masked by a method in the test class; this
harness error is corrected, logs `final-*` restent historiques.

<a id="preuves-exécutées"></a>

## Evidence

- First comprehensive targeted suite: 14 methods, 22 native and
  19 invalid programs tested in both stages, O0, 13.285 s.
  Journal : `validation/async-struct-pools-counted-o0.log`.
- First O2 campaign: 14 successful methods baseline, then eight mutations
  Journal: `validation/async-struct-pools-mutations-o2.log`.
- Final suite with inactive/launch failure/lose Select: **15 methods
  successful at O0 in 14,810 s**25 native executions (including expected exhaustion),
  19 invalid programs and 38 refusal checks.
  Journal : `validation/async-struct-pools-complete-counted-o0.log`.
- Final campaign O2: baseline of 15 successful methods in 14.945 s, then
  **eight mutations detected**, aucune survivante ou inconclusive.
  Journal : `validation/async-struct-pools-complete-mutations-o2.log`.
- Broad Regression: **174 successful methods at O2 in 121.929 s**.
  Journal : `validation/async-struct-pools-regression-o2.log`. Ce processus
  had loaded the code before the last Conservative guard which excluded the
  candidates from fields other than `parameter`/`fresh` the new summary.
  Both targeted campaigns include this guard.
- Supplementary transition of the four contract suites/state results
  final : **51 successful methods at O2 in 41.556 s**.
  Journal : `validation/async-struct-pools-result-contracts-o2.log`.

All the processes cited are over. The diffs of the four Python files
amended are retained in `validation/async-struct-pools-*.py.patch`.

The loop model calculates independently the sums and number of
cleanings for 0, 1 and 4 iterations. A native probe checks the values,
the re-use of the address of the destroyed slot, the preservation of its living neighbour,
The destruction suspended and the closure. These are finished models, not a
Full independent auditor model.

Mutants remove or corrupt the offsets, the destroyer of the possessed field,
the dependence on the downhill pool, cleaning a prepared field, the defect
the contract for direct profit, the contract propagated to a factory and
The tests and oracles are unchanged in the
The eight detections do not measure a global coverage.

Native performances use Clang C11, pthread, Wall/Wextra/Werrar,
Wno-unused-function and fatal UBSan, at O0/O2 according to the newspaper. No new
ASan/TSan result, performance measurement or general safety proof.

<a id="écarts-conservés"></a>

## Variations retained

Subsequent updates: Local borrowed field pools are covered
by [this cycle](ASYNC_BORROWED_STRUCT_POOLS_CYCLE.md)and local results to
fields owned by [the cycle of local graphs](ASYNC_LOCAL_OWNED_RESULT_GRAPHS_CYCLE.md).
The list below maintains the historical record of the end of the batch.

The four current refusals are reproduced in
`validation/async-struct-pools-remaining.log` ; no invalid code is executed.
Pools/builders async of borrowed field structures, results
new premises containing proprietary or borrowed fields, projections
through interlocked handles, mixed graphs and other restrictions
The result is fresh in an injected pool covered here.
does not generalize local returns or replacements of proprietary fields.
The arbitrations on the handles launched remain unchanged.

Snapshot modified files: `/tmp/crust-before-async-struct-pools`.
The objective of the seven drafts remains active and incomplete.
