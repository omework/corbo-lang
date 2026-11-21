[Français](BORROWED_RETURNS-fr.md)

# Retours d'objets contenant un emprunt : enfant → parent

**Mutable-access update:** [MA1–MA6](MUTABLE_ACCESS.md) supersede exclusion
inferred from `&mut` alone. Exclusion examples and verdicts recorded in earlier
cycles below are historical evidence, not the current access-compatibility rule.
Permissions, validity, synchronization and branch completion are separate checks.


Later extension: [fields &mut Int](MUTABLE_REFERENCE_FIELDS.md) are now available; the measures below describe this historical cycle.

Cycle of 2 November 2026. Extension requested by the user; procedure according to
[VALIDATION_GUIDELINES.md](VALIDATION_GUIDELINES.md)rules and dependencies in
[LANGUAGE_RULES.md](LANGUAGE_RULES.md) and [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md).

## Comportement

```rust
enum View { Item { data: &Int }, Empty {} }

fn make_view(views: &mut Pool<View>, data: &Int) -> <- View {
    let mut view = new(views) View.Item { data: data };
    return <- view;
}
```

The Int allowance is injected by borrowing: it already belongs to the scope
The parameter variable disappears when the ancestor returns, but the
field contains the pointer to the original allocation, not to this variable.
The result keeps the loan until its last use.

```rust
let mut view = make_view(&mut view_pool, &data);
drop(-> data);   // Refusé si la lecture suivante reste possible.
print(view);
```

After last use of `view`, `data` can be destroyed or its pool reset,
the holder does not destroy its
target. A re-used slot address does not reactivate old accesses.

<a id="la-vérification-de-frontière"></a>

## Border verification

For each child passage → parent, all possible targets must be
live, valid on all roads and attached to the destination or to a
The result pool must also survive according to existing rules.
The successive borders are checked separately:

```rust
fn wrong(data_pool: &mut Pool<Int>, views: &mut Pool<View>) -> <- View {
    let mut data = new(data_pool) Int(42);
    let mut view = make_view(views, &data); // Valide : retour vers ce scope.
    return <- view; // Refusé : data n'est pas durable dans le parent de wrong.
}
```

The duration of the pool does not replace the life of the allowance.
Int by `->` sends down his attachment in the child; it is not a
Injection by borrowing. Returning a view the reference is therefore refused in this
D1 now prohibits automatic promotion of this target;
the previous proposal is abandoned, not merely postponed.

A target created as a temporary argument `&new(pool) Int(...)` belongs to the
a drawing scope: a view can hold it in this scope. On the other hand, a wrapper
who creates this temporary himself cannot return the sight to his own parent.

<a id="contrats-sans-corps"></a>

## Contracts without bodies

The summary of the result shall keep separately:

- Its candidate allowances and their sources of storage, as before.
- `borrowed_fields` : for each path `Variante.champ`, the identities of the
  Int parameters borrowed or fields of received objects on which it depends.
- `fresh_variants` : variants of the objects built, combined with the variants
  actual possibilities of returned entries.

Extract from `effects` for `make_view` :

```json
"borrowed_fields": [
  {"field": "Item.data", "targets": [{"kind": "parameter", "parameter": "data"}]}
]
```

A relay replaces the parameters; return a carrier received by `->` conserve
its fields by identity `field_parameter`. Analysis refuses to export a target
local, even without a call from the function and without memory backend. At the opaque call,
concrete identities are substituted and attached to the result: the auditor
does not open the body of the calle. A test explicitly removes body and tables
independent of inference.

The specialized backend keeps the addresses and checks that fields, origins and
observed variants comply with this contract. Abstracts are not an oracle
independent: inference and their application remain in the basis of trust.
Runtime C, slot representation and pointer format do not change
no mantle or runtime reference count is added.

The branches meet the possible targets, even if they share the same
pool. Empty variants do not invent targets.
renets is maintained: a possible reset protects future uses, even on a
There is no correlation of new path that makes this choice more flexible.

<a id="réemprunt-partagé-dun-parent-mutable"></a>

## Shared reborrowing from a mutable parent

A returned object can retain a shared reborrow from a mutable access:

```rust
let mut loan = &mut data;
let mut view = make_view(&mut view_pool, loan);
print(view);
loan.set(7); // Autorisé après le dernier usage de la vue.
```

Reverse the last two instructions is refused.
The parent's loan is suspended as long as this shared loan is still in use.
`read_parent` / `borrow_parents` are only static metadata; the
successive returns and movements of the bearer keep them. There is no
champ `&mut` and the &Int field does not give any additional mutable rights.
General reborrowings out of these fields remain restricted.

<a id="baseline-défauts-et-attentes-de-tests"></a>

## Baseline, defects and test expectations

The historical baseline was 572 standard tests and UBSan at the previous cycle.
It was not replayed in full before the patch; the initial snippet
was executed and refused by explicit restriction of returns containing
This restriction is lifted according to the approved application.

Deficiencies detected during implementation and corrected:

1. Normal return control was looking for an already depilated activation and could
   produire `StopIteration`. The destination is now registered in the
   Appeal framework and used for normal returns as conditional.
2. A shared reborrowing retained after the call reactivated the parent too soon
   mutable, producing an error of invariant. The suspension links are
   now kept with the result, until the last use.
3. A complementary check after a successful first pass of 604 tests
   found a new alias unrelated to this reborrowing: original access
   The aim was to create a reference while the mutable parent still had to
   The program then failed on an invariant.
   is now refused in the right place; two regression variants cover
   The following are the cases of arguments already prepared.
   after this correction, without appropriating the first transition to final validation.

Two first valid rated test programs violated U1, as a view received
was crushed/reset without explicit use. The fixtures were corrected for
use these views; U1 has not been relaxed. The old test refusing a function
empty turning View now checks the absence of result, not a
type restriction that the user has just lifted.

<a id="validation-et-interactions"></a>

## Validation and interaction

[tests/test_borrowed_returns.py](../tests/test_borrowed_returns.py) contains 33 methods:
successive transfers of functions and blocks, local target/transferred parameter,
local pool, drop, transfer, reassignment, reset, empty variants, returns
conditionals and if expression, identity, mutable reborrowing, arguments,
re-use of slots and loops.
Comparisons; Eligible programs are compiled and executed in C.

The independent model of scope routes uses the levels of creation and
Target destination, without summaries or compiler decisions.
0–23, profondeur 1–4 : **12 valid expected programmes implemented** and **12 attendus
Invalids refused**. It does not model all the exclusive borrowings nor all
The interaction tests and models of the previous cycles
complete this exploration without making it an exhaustive cover.

The 66 rules were reviewed, with attention to S3/S5, T3/T5/T6/T9/T11,
V4/V5, B1/B2/B3/B4a–e, L1/L2/L3/L6, A2/A3/A5/A6 and P8/P9. The matrix retains
the rules not implemented as unverified. D1 was subsequently revised by
explicit decision: no implicit promotion, with the refusal already implemented.
No general graph support or direct return of a B5 loan is deducted
[direct returns &int]](DIRECT_BORROW_RETURNS.md) are
Implemented and validated in a separate subsequent cycle.

<a id="mutations-et-c-optimisé"></a>

## Optimised switching and C

```sh
python3 tests/run_borrowed_return_mutations.py --output validation/borrowed-return-mutations.json
python3 tests/run_reference_field_mutations.py --output validation/reference-field-mutations-current.json
python3 tests/validate_borrowed_return_c.py --output validation/borrowed-return-c.json
```

Five selected errors are detected: field absent from contract, dependency
lost to opaque call, local target accepted by inference alone, ancestor
valid refused and lost mutable parent. The four &Int field mutations
were also replayed and detected, following adaptation of an anchor to the
The tests/oracles have not been modified in the new internal signature.
Injected copies. Identical front/after prints for both campaigns.
These nine errors do not provide an overall detection rate.

[Report of new changes](../validation/borrowed-return-mutations.json) ·
[Regressions from previous changes](../validation/reference-field-mutations-current.json).

The [Report C](../validation/borrowed-return-c.json) holds 12 executions: three
programs × O0/O2/Os/O2-UBSan. Eight normal execution checks identities,
values and destruction; four stop on the expected depletion of the pool,
without unfolding the destroyers. Expectations specified without reading the decisions of the
C. One family available, Clang 20.1.3; no C.
compared to an independent family. ASan is not executed in this cycle,
previous host tests also failed for an empty C program.

## Limites

Enduring Fields Only, No Enum References or Transit Graphs,
cycles, user destroyers, async, threads or FFI. Direct returns
&Int now have their [Dedicated Cycle](DIRECT_BORROW_RETURNS.md). All uses of a carrier remain of
The precision is limited by the unions of the
targets/variants; sizes, paths and platforms are not exhaustive.
This is not a formal proof of security.
Automatic target promotion is not a delayed extension: it is
prohibited by [revised decision D1](NO_IMPLICIT_PROMOTION.md).

<a id="suites-complètes"></a>

## Full suites

The final sequels after the last patch ended without fail:

| Commande | Actual |
| --- | --- |
| `python3 -m unittest discover -s tests -q` | 605 tests, OK, 334,931 s |
| `CRUST_SANITIZE=undefined python3 -m unittest discover -s tests -q` | 605 tests, OK, 334,730 s |

The 33 new methods, the existing cleaning models and the types of
pools, the &Int field model and the runtime oracle of 3000 operations are
The number of programmes admitted/refused to be included in these two executions.
all sub-variants of the suite are not aggregated; accounts 12/12
The only model is the independent model of the telescope routes.

The nine mutations and the twelve C executions were relaunched on the code
and satisfied their controls, in campaigns distinct from the follow-up.
The fingerprints of Python files are identical before/after each injection.
The [structured balance sheet](../validation/borrowed-return-suites.json) keep the controls,
durations, first passage and additional counter example, and limits
UBSan instruments the harness C and the oracle; the CLI tests which
build their binaries without these options do not become instrumentalized by
the test variable. The three optimized C cases are explicitly instrumented
in their O2-UBSan configuration. No failure of this cycle remains open;
the above coverage limits shall remain applicable.
