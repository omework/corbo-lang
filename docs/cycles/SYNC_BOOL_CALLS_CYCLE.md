[Français](SYNC_BOOL_CALLS_CYCLE-fr.md)

<a id="cycle--booléens-à-la-frontière-des-appels-synchrones"></a>

# Cycle — Booleans at the border of synchronous calls

Follow-up: The lack of injected pools described in this report
is treated for Int/String/Vector<Int/u8> in the
[cycle suivant](ASYNC_POOL_INJECTION_CYCLE.md). The other limits remain.

<a id="règles-et-portée"></a>

## Rules and scope

Continue to [SYNC_OWNED_CALLS_CYCLE.md](SYNC_OWNED_CALLS_CYCLE.md).
AGENTS.md, VALIDATION_GUIDELINES.md, index of the seven drafts, B4/B4a,
The rules of the telescopes, A1–A6 and AS2/AS8–AS16/MT1–MT8 were re-examined.
No regulatory decision is amended. The obligations of the seven drafts
remain open beyond this lot.

Pools connect to reveal the need to distinguish their booking
exclusive during a task and storage dependency of a result after
The first mechanism is not yet connected to the states.
this extension, this cycle corrects a family of missing signatures to the
same border: the Boolean parameters and results of synchronous functions.

The existing synchronous frontend writes these signatures `bool` and async states
utilisent `Bool`. This cycle adapts their internal representations; it does not change
not syntax and does not introduce public alias. A boolean is not an Int or
a u8, despite its full C representation. The selection of contracts must
keep this distinction until the result and the catches of a native block.

<a id="contre-exemples-et-corrections"></a>

## Counter-examples and corrections

`fn flag(b:bool)->bool{return b;}` called from a `async fn work()->Bool`
was refused, notably by "a Bool value is required" on a return
direct. Calls now provide a Bool-typed result in the
states and accept Boolean arguments without implicit conversion.
Links, existing annotations, reassignments, conditions, returns,
Child captures and returns of native blocks use the same adaptation.

A second counter example comes from the life test: a synchronous block
with local pool, join, Boolean copy and output returned this copy by its
he was refused as an arrowless transfer, although he did not
The initial results of these studies are in
blocks are now copied before cleaning. Owners continue
d) require an arrow and references keep their time checks.

Boolean copies do not hold any pool or loan after join.
read by a first subcall may end before the next transfer, while
that a prepared mutable argument remains exclusive during the other arguments.
A return in a subsequent Boolean argument cleans the owner already
prepared; the function not called produces no effect.

<a id="vérification"></a>

## Verification

`tests/test_sync_bool_calls.py` contains ten methods: 18 C programmes
implemented, 16 invalid programs refused, plus one verification without emission
Eight of the executions compare the table of truth of two booleans
the independent Python model `left and right`, in async and native block.
The other oracles set values, order of effects and traces of destruction.

Runtime/native regression adds this module to its existing selection.
`tests/run_sync_bool_regression.py` re-executes the five contract modules
and 119 methods of foundations targeting blocks, conditions, returns, booleans,
The existing models of provenance of these
modules remain included. This is neither the whole project nor evidence
general on language combinations.

Clang C11, pthread, O0/O2, `-Wall -Wextra -Werror -Wno-unused-function`, UBSan
with `-fno-sanitize-recover=all`. No new results found. ASan, TSan, second
Compilator C, fuzing or formal evidence is claimed.

<a id="mutations-et-limites-de-leurs-oracles"></a>

## Changes and limits of their oracles

Campaigns use temporary copies of the compiler and the same
four errors are detected: acceptance of a
Int. as Boolean argument, inversion of Boolean result, loss of type in
Inference of the native block, refusal of a valid primitive block result.

The first attempt to delete the snapshot left his C statement
unused: Clang rejected C with `-Werror`. It was not an observation
The corrected mutation also removes the declaration
The C inspected shows that the expressions of the chosen paths had
already produced `read`/`selected` or a scalar variable still in range C.
The final classification is "no behavioural effect on the paths
The papers are not "detected" or evidence of general equivalence.
initials remain retained; the final campaign adds a separate mutation
which reintroduces the real unjustified refusal of the release of the block.

<a id="artefact-et-suite"></a>

## Artifact and suite

[Program retained](../../validation/sync-bool-boundaries.crb) and
[C generated](../../validation/sync-bool-boundaries.c) : reading via Boolean auxiliary,
suspension, join, drop of 7, re-use of slot with 9, closure of pool then
read the independent result. `9`, `1` ; destruction of 7 and 9
Exactly once. `block_value` above `source_close` in C.

[Pool injected again open](../../validation/open-async-pool-helper.crb) conserve
the case valid for A1/A2/A4/AS12/AS13 which remains refused by the limitation
It is not a test that requires maintaining this refusal.
follow the exclusive loan until the end of the task, then only the source
the result, through contracts and translation `Source *`. Pools
state, general signatures, runtime/schedule/Select/mutex and
The overall goal remains active.

<a id="résultats-exécutés"></a>

## Implemented

| Campagne | Result | Journal in validation/ |
| --- | --- | --- |
| Premier lot O0 | Eight methods, seven green; Boolean block exit wrongly refused | `sync-bool-initial-o0.log` |
| Block output corrected O0 | Eight green methods, 5.573 s | `sync-bool-block-o0.log` |
| Final target batch O0 | Ten green methods, 5,902 s | `sync-bool-final-o0.log` |
| Native/runtime O2 | 144 green methods, 132,205 s | `sync-bool-regression-o2.log` |
| Contracts and scopes O2 | 249 methods: 248 green, a fixture not in accordance with U1 | `sync-bool-contracts-scopes-o2.log` |
| Reproduction on the previous compiler | Same refusal of the fixture for unused result | `sync-bool-baseline-fixture.log` |
| O2 corrected fixture | One green method, accepted case and two refusals | `sync-bool-fixture-fixed-o2.log` |
| Mutations finales O2 | Baseline ten green methods, 11,079 s; four detected errors, one omission without observed effect | `sync-bool-reviewed-mutations-o2.log` |
| Artefact C O2 | Values 9 and 1; two unique destructions; exit 0 | `sync-bool-artifact-run.log` |
| Injected pool | Refusal to capture still open | `sync-bool-open-pool-probe.log` |

Fixture `test_match_expression_early_return_has_function_result_type`
created `scratch` without explicit use. The compiler prior to the cycle,
The correction adds that the correction was not a temporary copy.
`print(scratch)` and adapts the expected output; cleaning remains automatic
The version without the rendition, and its unique destruction oracle is preserved.
use is now verified as U1 refusal. The selection of 249 was not
fully re-executed after this fixture correction only: its failure
initial remains visible, and the corrected method is re-executed separately.

The cycle compiler has not been modified since the selections were launched
O2. All the above processes are completed.
close this lot, not the work of integrating the remaining rules.
