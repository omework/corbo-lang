[Français](DIRECT_BORROW_RETURNS-fr.md)

# Retours directs d'emprunts &Int

Later extension: [back &mut Int](MUTABLE_BORROW_RETURNS.md) are
The restrictions and measures below describe the
Historical cycle perimeter, with raw and print sources retained.

Cycle of November 2, 2026, requested by the user. References:
[validation guidelines](VALIDATION_GUIDELINES.md), Rules B5/D1/B1–B3/A5 and
[Matrix of 66 rules](VERIFICATION_MATRIX.md). This cycle implements B5 in
a read-down subset; it does not allow any implicit promotion.

The examples have been updated for the [reference value rule]](REFERENCE_VALUES.md) :
`return data`, `borrow(data)` from a borrowed parameter.
of this cycle retain the old syntax state and their fingerprints; the new
validation is recorded separately. `&` on a reference is now
flattened in reference to his target.

<a id="comportement-et-frontières"></a>

## Behaviour and boundaries

```rust
fn borrow(data: &Int) -> &Int {
    return data;
}

fn relay(data: &Int) -> &Int {
    let mut view = borrow(data);
    return view;
}

let mut memory = Pool<Int>::new(1);
let mut data = new(memory) Int(42);
let mut view = relay(&data);
print(view);
drop(-> data); // Autorisé après le dernier usage de view.
```

A return does not create an allowance, does not use `<-`, does not receive the target
in a new order of destruction and does not alter its address or source.
Future uses of the result protect the target. Place the drop before the print
denied the program; the same applies to a reset, displacement or access
mutable incompatible. After last reading, drop/reset and reuse
slot are allowed, without reactivate the old access.

At each exited border, all targets must be alive, some of them
This control also applies to the blocks of the parent or ancestor.
The pool is not a durable tool that makes its allocations difficult to meet.
local loans exportable:

```rust
fn wrong(memory: &mut Pool<Int>) -> &Int {
    let mut local = new(memory) Int(42);
    let mut view = borrow(&local); // Retour valide vers le scope de wrong.
    return view;             // Refusé à la frontière suivante.
}
```

An Int Injection Allowance `->` descends into function and cannot
Get out of here by borrowing. `&mut Int` can give a shared result,
His mutable parent does not resume his incompatible access
only after the last use of the result. Access controls from the name
The original suspension shall remain active during this suspension.

Conditional returns bring together all possible targets, even with
a literal condition or multiple targets in the same pool. A reset of a
The only possible pool is therefore forbidden before future use of the result.
references can be passed to the following calls or stored in the fields
&In already available: alternatives and mutable parents follow these
no value-dependent analysis of the predicate is added.

<a id="contrats-et-traduction-c"></a>

## Contracts and translation C

`results.py` lower `reference_targets`, set of parameter identities
The relays substitute the parameters, without annotation of origin.
Inference alone refuses local targets and Int parameters transferred,
even in an unused function. `constraints.py` keeps the history of the
existing targets: a borrowed result is not a new one
The allocation would make a previous reset forget.

The auditor applies the opaque contract without opening the body called.
static descriptor gathers all possible targets; it is not entered
neither in the register of actual allowances nor in a cleaning list.
The existing active borrowings and arguments protect the entire
These targets. &Int porters manufacturers also keep this set.
The specialist backend checks that the targets observed meet the contract.
A voluntary false contract test controls this last guard.

C uses pointer `Cell *` existing, without handle, reference counter
or additional allocation. The result is a pointer to the Int slot,
and not to the parameter variable C. The allocation cleaning pointer
The pool runtime and the result descriptor are separated from the original result descriptor.
slot format has not changed.

<a id="validation-exécutée"></a>

## Validation executed

The 27 new test methods include accepted/refused couples and
sub-cases: contracts without call, local targets and received by transfer, parent and
ancestors, relays, conditional returns, re-borrowing of mutable parents, aliases
in arguments, &Int fields, reset history, reference reassignment,
loop with continuous, address and unique destruction, re-use of slot.
The opaque test removes the body and prohibits a block entry when calling.

The independent target model uses 24 seeds (0–23), permutations of
parameters, target unions and 1–4 relays. His oracle calculates the sets
of indices since the construction of the graph, without reading the inferred contracts.
It requires 12 programs admitted and 12 refused; admissions are also carried out
This model does not have the same value as the actual path.
Models not the entire auditor or all borrowing history.

Five selected mutations are detected in temporary copies: omission
the target of the contract, acceptance of a local target by inference, loss of the
alternatives to alias, loss of mutable parents and erroneous rejection of a target
the four field mutations and the five returns of the
The injection points of two old ones are replayed and detected.
changes have been adapted to the code preserving the alternatives; their assertions
The Python prints of the project are unchanged by
The three campaigns, no overall detection rates are deducted.

Three fixed C programs (relay/selection/reuse, mutable parent,
(O0, O2, Os, and O2+UBSan: 12 observations)
Conformity, including eight normal outputs and four expected capacity stops.
The assertions compare addresses, values, order/number of destructions and
UBSan stops first diagnosis; none is issued.
L'exemple [direct_borrow_returns.crb](../examples/direct_borrow_returns.crb)
is also executed by the CLI launcher.

Rapports bruts : [C](../validation/direct-borrow-c.json),
[mutations directes](../validation/direct-borrow-mutations.json),
[regression mutations fields](../validation/direct-borrow-field-regression-mutations.json),
(regression of the movement of workers](../validation/direct-borrow-holder-regression-mutations.json).
Suite globale standard : **632 tests passed in 417,129 s**.
Global suite with `CRUST_SANITIZE=undefined` : **632 tests passed in 416,912 s**.
The 27 new methods are in addition to the 605 of the previous cycle.
existing cleaning, provenance, pool, field and oracle runtime requirements
The names and contracts of the previous tests are included in the execution.
kept; no failure left unresolved. Count 12/12 above
is concerned with new generated programmes, and not with all the fixtures of the
632 methods (which have their own sub-cases).

The [gross balance of the follow-up](../validation/direct-borrow-suites.json) keep the
orders, outputs, durations, seeds and prints Python. A complementary case
[on temporary employment with the appellant](../validation/direct-borrow-temporary.json) has been
executed under UBSan: read the reference, reset, then new object in the
capacity pool one, with two destructions exactly. No divergence of
unsolved rule is not identified in this tested perimeter.

The initial development corrected the harness fixings: reassignment of the harness
scalar parent not supported in a loop, unused recipient after
rewrite a script and internal call not indexed in the opaque test.
These corrections did not change the language rules.

## Limites

Retours `&Int` only, in reading, with `return` explicit. Returns
`&mut`, to other types, references to local scalar and return
of a field extracted in a match arm remain outside the prototype.
If expressions that produce a reference and general stored reborrowings
are not added. However, a &Int call result can be received and
re-borrowed during another &Int field call, return or constructor.

Inference, contract enforcement and specialized audits remain
The first is the need to establish a common system of financial and financial services.
existing cleaning and running models are re-executed by the suites
global. General placement, transitive graphs, destructive user,
recursion, threads, async and external C border remain outside perimeter.
ASan is not restarted: previous tests of this position fail even with
an empty C program. Only one C family is available (Clang; the gcc name
Local also points towards Clang). UBSan instruments built binaries
by harness and oracles; CLI binarys are not instrumented by
the only variable `CRUST_SANITIZE`. Voir [SAFETY.md](SAFETY.md).
These restricted controls do not constitute proof of general security.
