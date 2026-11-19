[Français](POOL_REQUIREMENTS_VALIDATION-fr.md)

<a id="exigences-de-pools--correction-et-validation"></a>

# Pool Requirements: correction and validation

Cycle of November 2, 2026. References: [guidelines](VALIDATION_GUIDELINES.md),
[normative rules](LANGUAGE_RULES.md), [tracing matrix](VERIFICATION_MATRIX.md).

<a id="défaut-baseline-et-règles-concernées"></a>

## Default, baseline and relevant rules

No normative rules are added or modified.
B4 the types/modes of the parameters, B4b the propagation of the requirements and B4e
The default was for the compiler:

```rust
enum Message { Empty {} }
fn inspect(p: &Pool<Int>) {}
fn relay(p: &Allocator) { inspect(p); }
fn main() {
    let mut p = Pool<Message>::new(1);
    relay(&p);
}
```

Reproduit avant correction : `check` accepted, the backend refused with
`p attend une source Pool<Int>`. A signature without an allowance required a type
the actual control no longer opened the
called body; symbolic passage allowed a generic source.

The historical baseline of the previous cycle was 522 standard tests and UBSan.
It was not re-executed in full before modification; the counter-example
The above results were performed on the original statement.

## Correctif

`FunctionEffects.pool_requirements` contains couples (indice of parameter,
type of pool). The opaque interface `FunctionContract` carry this field, also
exported to the JSON of `effects`.

- A signature `&Pool<T>` ou `&mut Pool<T>` I want this pool, even if it's empty.
- The requirement is substituted in sub-calls, including at several levels
  and when parameters are reordered.
- A local source is locally controlled; its requirement is not exported
  like that of a masked outer parameter.
- Types of pools incompatible with the same source are refused, as well
  conflicts with the types of allowances in this source.
- Symbolic entries incorporate requirements, including if provenances
  are achieved by an equality imposed by `source.drop`.
- Opaque calls check the actual source without bodies or tables
  The backend retains the same control.

An Int allowance does not require a pool: existing explicit Int backends
A enum requires its typed pool. The required type does not grant any rights
Additional mutable.

An existing test detected a change in diagnosis: the wrong pool was
well refused but the word `incompatible` The message was corrected without
Weakening the waiting for the test. A first launch of the complete suites was
interrupted at this detection and then restarted after successful targeted tests.

<a id="réexamen-et-invariants"></a>

## Review and invariants

The 66 rules were reread and linked to their evidence/limit profiles in
The matrix. Future rules remain unverified; the rules implemented
This inventory is not a rule-by-rule proof.

Invariants examined: type of source retained, correct substitution of
arguments, allocation/pool requirement distinction, scope of local sources,
leaves readonly/mutable unchanged, provenance and identity retained,
unique cleaning and semantic order, capacity and reuse.

New interactions: literary branches, return, divergence, loop and
condition while, interlocking arguments, local masking, equal drop sources,
other type of allowance, identity restitution, re-used slot and reset.
The existing suites bring other combinations of transfers, borrowings,
sources, reassignments and outputs of telescopes. It is not a product
comprehensive Cartesian of all rules.

<a id="modèle-indépendant-et-génération"></a>

## Independent model and generation

[pool_requirement_model.py](../tests/pool_requirement_model.py) built
peaks (function, parameter), argument routes and terminal requirements.
It lists paths without reading the parser, compiler summaries or C.
The compiler uses recursively cached summaries; the model follows
roads to the typed declarations.

Campaign carried out: seeds **0 à 39**, **7 fonctions** and **3 parameters of
source** by function, int/message int/message int/send. **20 programmes
valid expected accepted**, **40 invalid expected refused** (contrats
The abstracts of the eligible graphs
are compared to independently predicted bonds.

Limitations: readonly model without allocation, reset, loop or mutable alias.
These interactions have separate tests. The rendering of the graph is itself
a hypothesis, challenged by deterministic examples of reordering and
the minimal counter-example; it does not prove all grammar. **23 methods
Targeted** contain several sub-cases; the overall number of programmes
accepted/refused from the whole suite is not aggregated.

<a id="mutations-en-copies-temporaires"></a>

## Changes in temporary copies

```sh
python3 tests/run_pool_requirement_mutations.py --output validation/pool-requirement-mutations.json
```

The target baseline passes before injection; tests and oracles remain unchanged.

| Selected fault | Result | Witness |
| --- | --- | --- |
| Omit an empty signature requirement | Detected | Summary of signature |
| Omit transitive propagation | Detected | Independent road model |
| Replace the wrong parameter | Detected | Multi-level reordering |
| Omit Opaque Call Control | Detected | Call without body or inference tables |
| Refuser un pool correspondant | Detected | Valid program executed |

The front/after prints confirm the absence of any change in the checkout
The [JSON report]](../validation/pool-requirement-mutations.json)
keeps results, diagnoses and prints. Five errors selected give
No runtime mutations have been re-executed here.

<a id="c-généré-et-instrumentation"></a>

## C generated and instrumentation

```sh
python3 tests/validate_pool_contract_c.py --output validation/pool-requirement-c.json
```

**12 executions C** : trois programmes × `-O0`, `-O2`, `-Os` and
`-O2 -fsanitize=undefined -fno-sanitize-recover=all`. Deux programmes couvrent
the two paths of a selection with transitive requirement, identity, re-used slot,
enums, returns and resets; the third must stop on excess capacity
without the destruction process. Values/traces expected specified without reading
the compiler state or the generated C. **Eight normal executions and four judgments
attendus** have met these tests. No UBSan diagnosis was observed
on these paths.

Only one family C available: **Homebrew Clang 20.1.3**. L'alias `gcc` pointant
To Clang is not counted as an independent implementation.
[rapport JSON](../validation/pool-requirement-c.json) keeps configurations and results.

Full suites include existing models: independent cleaning
(32 operations, seeds 17 and 83, three backends) and runtime oracle
(3,000 operations, seed 12345, two variant sizes).
The results of their execution are recorded together with the results of the complete follow-up.

ASan not performed in this cycle: previous tests on this host failed
also on an empty C program. In the UBSan suite, the C harness and the oracle
are instrumented; binary built by the LTC keeps its options
The dedicated campaign explicitly instruments its three cases to the `-O2`.

<a id="limites-et-ambiguïtés-conservées"></a>

## Limits and ambiguities retained

- No formal evidence or comprehensive coverage of all combinations.
- Cursion, growing collections, reference graphs, destructive
  user, returned references, competition and FFI remain outside the scope.
- The mission aims to ensure that there is no overall dynamic allocation, but the prototype
  and P7 maintain explicit compatibility backends. Their withdrawal is not
  The new examples focus on pools.
- The historical examples and future rules are not interpreted as
  features implemented or verified.
- The obligations of the abstractly possible branches are combined, even
  with a literal condition. After a return without continuation, they do not
  This behavior comes from the existing rules.
- Not all OS errors, sizes and mapping platforms are explored.
  No comparison of distinct C families was possible.

<a id="résultat-global"></a>

## Overall result

Both suites ended without fail:

| Commande | Actual |
| --- | --- |
| `python3 -m unittest discover -s tests -q` | 545 tests, OK, 281,060 s |
| `CRUST_SANITIZE=undefined python3 -m unittest discover -s tests -q` | 545 tests, OK, 281,265 s |

The existing cleaning model and running oracle are included in these two
The 23 new regression methods, the campaign generated and
Targeted interaction scenarios are also included.
12 C-exes at multiple levels of optimization are separate campaigns,
The number of tests does not measure the number of tests performed according to previous orders.
comprehensiveness or a global level of safety.

The [structured results of the follow-up](../validation/pool-requirement-suites.json)
maintain the controls, durations and restrictions of instrumentation.
failure of this cycle remains open. Unverified properties and limits
The method remains the same as in this report and in the matrix.
