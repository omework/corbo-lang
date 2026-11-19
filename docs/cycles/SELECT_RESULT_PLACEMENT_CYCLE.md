[Français](SELECT_RESULT_PLACEMENT_CYCLE-fr.md)

<a id="destination-extérieure-dun-résultat-local-de-select"></a>

# External destination of a local result of Select

<a id="périmètre-et-règle"></a>

## Perimeter and rule

The investment in the receiver scope applies to the transferred local values
from a Select result, as with the results of blocks, functions and
Await has already been taken over. AS10–AS13 and SL1 retain their obligations:
the result does not depend on a destroyed state, and Select cleans its losers.
No new normative rules or promotion of a borrowed target.

The case `validation/open-async-result-factory-select-result.crust` was refused
The local pool does not survive the recipient.
tasks returning a local Point; their caller selects a result and then
The outside destination was known, but the destination was not known.
The search for the builders did not cross Select.

<a id="implémentation"></a>

## Implementation

The investment plan recognises the authorities of Select, brings together the
manufacturers of their compatible branches and transmit their results to
the expression await. Storage of the receiver is thus provided before any
The addresses are not moved after allocation.

An unknown source remains unknown.
explicit and borrowed targets are not moved to another source
to make a transfer acceptable. Type and duration checks remain
independent of this investment plan.

<a id="cas-ciblés"></a>

## Targeted cases

Five methods in `tests/test_select_result_placement.py`, six executions
and two invalid programmes at both entrances, i.e. four checks
refusal:

- Registered program: The Winning Point survives the return of the task.
- Direct calls from branches and back through an intermediate block then
  a suspension of the appellant.
- Two C probes: the injected destination contains both constructions,
  the winner keeps his address after termination, the statements are returned
  at pools; suspended destruction and termination recover all storage
  after cleaning the values concerned.
- A reference to the result always forbids its drop before reading.
- A result from an explicit pool too short does not benefit from any
  promotion implicite.

The existing storage probe systematically added the runtime Select,
even when it was already in the generated C. It now only adds it to
The first errors of redefinition C were in this case the first errors of redefinition C.
probe. A copy fixture has also been aligned to the synchronous auxiliary already
supported, instead of requesting a copy of the structure directly in
Async body. Claims of duration, address and cleaning are kept.

<a id="résultats-exécutés"></a>

## Implemented

- O0 Targeted: five methods, 2,165 s, process completed with code 0; journal
  `validation/select-result-placement-o0-second.log`.
- O2 regression: 94 methods, 82,859 s, process completed with code 0; journal
  `validation/select-result-placement-regression-o2.log`The five methods
  Targeted are included in the final version.

Clang C11, pthread, warnings treated as errors, UBSan without recovery.
No test jumped in these passages. The appropriate probe is also exercised by the
The existing suite of placements in the parent. This is not the whole suite.

<a id="limites-et-sélection-du-travail"></a>

## Limitations and selection of work

The tests are about local point, synchronous factories and forms
The information provided in this section is not evidence of an investment in the
all graphs, results wrapped or combinations of branches.
No new adversary campaign or mutations. Models already
present in the linked suites are replayed, without new model claimed.

The file `validation/open-cases-implementation-inventory.log` is a
preliminary inventory of 137 existing examples `open-*` : 117
20 rejected by check.
intentionally invalid. This count doesn't measure the functionality
The results of the study were not available.

<a id="reproduction-et-artefacts"></a>

## Reproduction and artifacts

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_select_result_placement
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_select_result_placement test_async_local_parent test_async_result_relays test_async_result_storage test_async_result_factories test_select_source test_async_local_owned_result_graphs
```

Snapshot : `/tmp/crust-before-select-result-placement/`. Differences in
`validation/select-result-placement-{async_local_placement,test_async_local_parent}.py.patch`.
The logs of the initial passage are kept separately from the final results.
