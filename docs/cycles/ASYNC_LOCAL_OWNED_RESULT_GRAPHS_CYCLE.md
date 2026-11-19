[Français](ASYNC_LOCAL_OWNED_RESULT_GRAPHS_CYCLE-fr.md)

<a id="résultats-locaux-async-contenant-des-champs-propriétaires"></a>

# Local results async containing proprietary fields

<a id="règles-et-portée"></a>

## Rules and scope

This lot applies drafts 03/04/05, L7, T1/T6, V5, D1, ST7/ST15 and
AS8–AS14. No normative rules are amended. The program retained in
`validation/open-async-result-storage-owned.crust` is now compiled and
executed: a local Holder root is built in the receiver storage,
with an A<Int> field whose pool remains separate and must survive the result.

The connection covers fresh local roots with fields coming from
of transferred parameters or injected pools, including interlocked finished graphs
The root retains its type T; it does not
no pool or local descendant unknown is promoted.

<a id="implémentation"></a>

## Implementation

- The contract of the result distinguishes the destination from the root and the sources
  of each proprietary path. A transferred parameter carrying a tree is
  developed in progeny paths when applying this contract.
- The termination inference accepts the captures of proprietary graphs
  finished without reference. It retains the suspension effects separately;
  borrowing aggregates do not implicitly become taken over.
- Local output producers are monitored through named tasks,
  relays, factories, spawn, join and extraction of the branch Ok. Only the root
  newly built receives the destination of the ancestor.
- The factories keep this destination in the sources of the task and
  The sources of the descendants remain independent.
- Backend contracts retain the pools of descendants after waiting.
  A result cannot come out of a block that closes one of these pools.

<a id="contre-exemples-et-étapes-intermédiaires"></a>

## Counter-examples and intermediate steps

The first connection accepted the direct case, but the tests found
refusal of transfers to the parent and the factories: the investment plan
It now recognizes the need for a result without source dependence.
fresh root of a complete graph, without moving the descendants.

The Root -> A<Leaf> -> A<Int> graph has two additional gaps:
the inference excluded all the aggregate parameters proprietary and the contract
applied did not develop grandchildren of an entire parameter.
connections are added. Another valid probe, turning the result of a
join out of a child block, revealed the absence of spawn/join/Ok follow-up in the
placement plan; this path is now followed.

The newspapers `initial-o0`, `expanded-o0`, `contracts-o0`, `source-model-o0` and
probes `nested-probe`/`nested-contract` keep the initial refusals.
Two fixeds were corrected according to the unchanged rules: a diagnosis
"unsustainable" accepted for the pool too short, and `a ->;` at the entrance of the arm
which consumes a parameter of his parent. No expected memory has been weakened.
No dangerous acceptance of the untransferled compiler was identified by
This lot; the first failures are refusals of admitted cases or fixes.

<a id="preuves-exécutées"></a>

## Evidence

- Suite finale O0 : **12 successful methods**, 15,103 s ; **19 native executions**,
  **19 invalid programs refused in both stages**38 checks.
  Journal : `validation/async-local-owned-result-graphs-counted-o0.log`.
- Final baseline O2: 12 successful methods, 15.279 s; **huit mutations
  detected**, aucune survivante/inconclusive.
  Journal : `validation/async-local-owned-result-graphs-mutations-o2.log`.
- Historical pool mutations: baseline of 15 successful methods, 18.092 s,
  then eight mutations detected. The anchors of the two projection calls of
  The contract has been updated; tests and oracles remain unchanged.
  Journal : `validation/async-local-owned-result-graphs-pool-mutations-o2.log`.
- Broad Regression: **180 successful methods**, O2, 136,500 s. Ce passage a
  loaded the code before the spawn/join supplement of the investment plan and the addition
  From destination to factory work sources.
  Journal : `validation/async-local-owned-result-graphs-regression-o2.log`.
- Final passage after these two supplements: **63 successful methods**, O2,
  49,275 s, covering storage, relays, factories, return owners and the
  This lot. Journal: `validation/async-local-owned-result-graphs-final-placement-o2.log`.

All the final processes mentioned are completed with code 0.
The last two complements are also included.
Native performances use Clang C11/pthread, Wall/Wextra/Werrar,
Wno-unused-function, fatal UBSan, O0/O2 according to the newspaper.
contained in temporary copies, without changing the oracles.

The life model lists the four provisions of the two pools
(ancestor/child), through a direct call, a factory and an async relay.
Only the provision where both pools survive the recipient is allowed.
Replacement sequences control the exact number of destructions
Two C probes observe the root address,
his pool distinct from that of the descendant, the pointer of the field, the liberation
child state slot and normal or suspended cleaning.
also branches, loans of the result, re-use of slots, tasks
Inactive and injected launch failure.

Injected faults remove dependencies of descendants, fields of
direct contract, the paths of the grandchildren, the destination in a factory,
placement to the parent and inference of the graph; another unduly firm the
External storage. Detections include improper refusals and safety errors.
These eight cases do not measure the general coverage of the compiler.

<a id="limites-conservées"></a>

## Limits retained

Further information: local roots containing borrowings are
now connected in the perimeter described by
[ASYNC_BORROWED_LOCAL_RESULTS_CYCLE.md](ASYNC_BORROWED_LOCAL_RESULTS_CYCLE.md).
The findings below describe the state at the close of this historic lot.

Both steps still refuse open examples of local root containing
a loan, projecting through several A<T>, and restitution after
replacement of a proprietary field. Findings reproduced in
`validation/async-local-owned-result-graphs-remaining.log`These are discrepancies
implementation, no new normative prohibitions.

Mixed graphs, local sources of unsolved descendants,
General signatures and the two decisions on the handle remain
ouverts. `reset()` remains absent from the prototype. No new ASan/TSan measurement,
or general proof of safety, lack of race or optimal placement.

Snapshot : `/tmp/crust-before-async-local-owned-result-graphs`.
Diffs : `validation/async-local-owned-result-graphs-*.py.patch`.
The full objective remains active and incomplete.
