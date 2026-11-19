[Français](ASYNC_CONSUMING_ENUM_MATCH_CYCLE-fr.md)

<a id="match-consommant-denum-dans-un-corps-async"></a>

# Match consuming enum in an async body

<a id="règles-existantes-appliquées"></a>

## Existing rules applied

This batch connects explicit transfers, F2/U1 (use of owned fields),
D1 (destruction), the lifespans of the pools and AS8–AS15 at the consuming game.
It does not change normative semantics. The validation priority confirmed
by the user is the implementation and testing of the cases already listed;
In-depth adversarial research and mutations are postponed to a
separate audit. AGENTS.md keeps this statement.

<a id="implémentation"></a>

## Implementation

Backend async extracts fields from the active arm to stable limbs of the
the state, detach the fields possessed from their bearer and destroy the latter before
The extracted fields follow the normal cleaning, including the body of the arm.
after yield, break, continue, return and destroy a loser of Select.
The address of the transferred allowance remains unchanged.

Shared and mutable fields retain the necessary external targets.
A consuming match does not create a loan reservation on the destroyed bearer.
The reasons for excluding a field possessed and the links without explicit use are
refused in each variant, even if the known construction chooses another.

Two follow-up from source were corrected:

- Un candidat `owned_projection` describes the source of the field, with its path,
  instead of taking back the root. The contract of result async can
  return a descendant and his own descendants possessed.
- The backend keeps the sources by field during construction and construction
  local transfers. Extracting a field no longer imposes on it the life of the
  The metadata follows the same snapshots and the same data.
  control junctions that stored dependencies.

The return of loans contracts also recognise the `moved_field_parameter`,
already produced by the common analysis of the consuming match.

<a id="tests-exécutés"></a>

## Tests performed

Next `tests/test_async_consuming_enum_match.py` passes 10 methods to O0,
in 4,377 s, code 0. It contains 10 native executions and 10 programmes rejected,
controlled by both verify_program and compile_source (20 controls).
These entries share analyses; they are not two independent evidences.
Journal : `validation/async-consuming-enum-match-final-o0.log`.

Cases concern the bearer/field order, the single destruction, the identity
address, re-use of pools, shared and mutable reference returns,
nested fields, stored references, Select and outputs
The transfer from a shorter carrier pool is allowed; the transfer from a smaller carrier pool is allowed.
from a pool of the field too short is refused.

The binarys are compiled with Clang, C11, pthread, Wall/Wextra/Werrar and UBSan
no results are claimed.

The O2 regression passes 117 methods in 95,528 s, process completed with code 0.
It covers both match modes, the enums possessed, the structures returns
and their graphs, the storage of task results, the results of the owners,
Select and suspended cleaning.
`validation/async-consuming-enum-match-regression-o2.log`.

<a id="échecs-intermédiaires-et-limites"></a>

## Intermediate failures and limits

The case recorded `validation/open-async-consuming-enum-match.crust` was
explicitly refused by the backend; it now runs and displays 7.
The first passage noted the wrong source of the returned descendant and the
source of displaced loan unconnected. He also performed the Select tests
inadvertently imported: the import of the harness has been corrected.
the pool then reproduced the conservative refusal caused by the merger
porter and field sources, corrected by field tracking.

Two test preparations were corrected without changing their intent:
the transfer to the arm must be at its entrance; the case of terminal return
The intermediate newspapers must not keep an unreachable suffix.
retained in `validation/async-consuming-enum-match-*.log`.

This lot does not establish a general security.
The following by field of sources
local is accurate for the constructions and transfers tested; the producers
which do not provide these metadata retain the aggregate source.
general compositions of contracts, recursive graphs and unrepresented types
are not reported as covered by this subsequent audit.
the new mutation campaign was not carried out for this batch.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_async_consuming_enum_match -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_consuming_enum_match test_async_enum_match test_async_owned_enums test_async_owned_struct_returns test_async_local_owned_result_graphs test_async_result_storage test_task_result_storage test_owned_results test_select_result_storage test_suspended_cleanup -v
```

Snapshot from previous modules: `/tmp/crust-before-async-consuming-enum-match/`.
The initial copy command using `python` was unavailable; snapshot
was rebuilt immediately with `python3` and the patch archived from the previous batch
for async_lowering.py, the only module already modified at that time.
The three patches of the modules are archived under
`validation/async-consuming-enum-match-*.py.patch`. The injection site of the
the previous batch's transfer campaign has been adjusted to the new text, without
Relaunch this campaign.
