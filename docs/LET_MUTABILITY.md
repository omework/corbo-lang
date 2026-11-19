[Français](LET_MUTABILITY-fr.md)

<a id="déclarations-et-mutation-du-contenu"></a>

# Statements and changes in content

Later extension: [back &mut Int](MUTABLE_BORROW_RETURNS.md) are
The restrictions and measures below describe the
Historical cycle perimeter, with raw and print sources retained.

Cycle of November 2, 2026. Explicit decision of the user: replace `var`
by `let` / `let mut`, retirer `set(name, 20)`, and make `name = 20` and
`name.set(20)` content transfers preserving the allocation.
V4/B4 are specified in [LANGUAGE_RULES.md](LANGUAGE_RULES.md), leurs
interactions in the [ 66-rule matrix]](VERIFICATION_MATRIX.md).
The cycle follows [validation guidelines]](VALIDATION_GUIDELINES.md).

## Comportement

```rust
let mut memory = pool<Int>(1);
let mut nombre = new(memory) Int(10);

nombre = 20;
nombre.set(30);

let vue = &mut nombre;
vue.set(40);
print(vue);
```

The entries change the same Int, at the same slot and at the same address.
No allowance, receipt or destruction is in line with these records.
The final cleaning sees the contents 40 and is executed only once.
The [executable example]](../examples/let_mutability.crb) also displays addresses.

The variable and the reference type have two distinct rights:

| Statement | Writing in the target | Reassignment of variable |
| --- | --- | --- |
| `let nombre = new(memory) Int(10)` | Denied from access | Denied |
| `let mut nombre = new(memory) Int(10)` | Authorised, without incompatible borrowing | Allowed by supported expressions |
| `let vue = &mut nombre` | Authorised by `.set` | Denied |
| `let mut vue = &mut nombre` | Authorised by `.set` | Allowed by supported expressions |
| `let mut vue = &nombre` | Denied: reference in reading | Allowed by supported expressions |

The immutability is that of the name, not a promise of global freezing attached to
The allowance can be used to provide an unchangeable access with `drop(-> name)` or
explicitly transfer to a new mutable receiver. `&mut name`
from direct access requires its declaratory demutable.
continue to apply to all these cases.

A parameter received by value is immutable by default:

```rust
fn edit(mut data: -> Int) -> <- Int {
    data = 20;
    return <- data;
}

fn write(data: &mut Int) {
    data.set(20); // mut data n'est pas nécessaire pour sa cible.
}
```

`mut n: Int` allows to modify the received scalar copy, without changing the argument
chez l'appelant. `mut data: &Int` does not allow to modify the shared target.
The mutable names of the parameters are kept in contracts and when
normalization of a Void return. A call receiving an object by transfer
can therefore change it if its recipient parameter is mutable, even if the name
consumed in the appellant was immutable.

Local sources used to allocate/reset or to `source.drop`
exigent `let mut`. A &mut Pool parameter already provides writing capability,
without requiring a parameter `mut memory`; a &pool remains in play.
Automatic cleaning and `drop(-> value)` do not require to make mutable
the variable consumed.

<a id="mutation-référence-et-remplacement"></a>

## Change, Reference and Replacement

`data = scalar_expression` on a Direct Int mutable Access evaluates the HHR and
The HHR can use a loan for the purpose of
last time; a use after writing continues to cause it to be refused.
If the HHR consumes the target or resets its storage, the target is checked for
new and the writing is refused. A new allocation at the same location
don't reactivate this old access.

`data = new(memory) Int(20)` provides an allowance: the previous rules of
replacement remain active. The new object is created before destroying
The old, and the pool must allow for their temporary coexistence.
the same allowance does not destroy it. Replacement and reallocation
require a mutable variable. The replacement of access allocated or borrowed remains
limited to the scope of the variable in the prototype; the mutations in place of the
Int and scalar can use a mutable access of an ancestor, as
the old operation set allowed it.

`view = 20` does not implicitly dereference: view remains a variable of
reference, which this reassignment cannot convert to Int.
`view.set(20)` with an Int &mut. The method currently accepts a literal
Int32 signed, like the ancient primitive.
supported are available to the right of `=`. User methods and
l'affectation `*view = expression` are not added to this cycle.

<a id="vérificateur-contrats-et-c"></a>

## Auditor, contracts and C

Mutability is attached to declarations/parameters and bindings, without
The central access control distinguishes between the two types of allowance.
Direct writings from a mutable name of the scripts through &mut.
The temporary allocations still remain.
name can be borrowed mutably, in accordance with the behaviour
previous arguments.

A content mutation does not create new binding or cleaning input.
The result C is a writing in `Cell.value`; the source, identity and the
cleaning pointer remains unchanged. Scalar assignments in place
Write their variable C, including from the children's blocks and iterations.
Pool runtime and slot layout are unchanged.

The analysis of the results retains the identity assigned after a scalar writing.
The analysis of constraints keeps the assets of this allowance and checks
the history after the effects of the HHR. Otherwise, an opaque contract could
forget a reset when writing, even if the specialized backend rejected
then the code. A test with Void function consuming the target force this
control over the writing itself, without depending on a usage in a return.

<a id="validation-exécutée"></a>

## Validation executed

The previous cycle included 647 successful methods in standard and UBSan.
The 25 new methods passed their targeted controls.
on this corpus **33 separate programmes admitted and implemented**, and
**50 separate programmes refused** by `verify_program` then `compile_source`.
The [sources and accounts](../validation/let-fixture-corpus.json) are preserved;
they do not count all sub-cases of global suites.

The independent content model uses 12 seeds (0–11), 12 writings per
graine, choisies entre `=` and `.set`. The oracle is a list of Int values,
without reading the verifier or C. It compares each displayed state, the address
The Declaratory Matrix of Capabilities
owner list, shared reference and exclusive reference, with/without mut,
for allocation, method and creation of a &mut: **18 cases, 5 admitted/13 refused**.
The other cases cover functions, returned identity, scalar parameters by
copy, mutable parent, imports, branches and continuous, HHR with loan/drop/reset,
Re-allocation of references, replacement, sources, re-used slot and &Int returns.

Previous fixtures have been migrated: old var → let mut to preserve
their previous rights, set → method, assigned parameters → mutable bindings.
The [migration control]](../validation/let-fixture-migration.json) notes the
same method names and second expressions of comparison assertions
for the previous 25 test files. It does not constitute proof of
The seeds, graphs and traces expected from the
previous models are retained; new tests also include Let
This is not just a conservative migration.

Five selected mutations are detected in temporary copies: ignore
immutability, require mut on variable containing &mut, allocate instead
write the content, lose the identity in the summary after writing, forget
the reset history of the target. The last one is detected at the opaque stage,
The 19 changes in the
previous references, fields and returns are replayed and detected.
The project's Python footprints are retained.
The detection of this is not inferred.

The four C campaigns (content, direct returns, porters and pools) each have
12 executions: three programs in O0, O2, Os and O2+UBSan, i.e. **48 executions
conformes**. The required observations include stable addresses, values,
destruction, resets, reuse and failure on capacity. Simple mutation
does not consume a second slot in a pool of capacity one; a replacement
which exceeds its capacity stops before the destruction of the old object.
instrumental tests stop at the first UBSan diagnosis; none is issued.
Only one C family is available. The example CLI is also executed, without
Implicit instrumentation by CRUST_SANITIZE.

Rapports : [mutations nouvelles](../validation/let-mutations.json),
[references](../validation/let-reference-value-mutations.json),
[retours directs](../validation/let-direct-mutations.json),
[porteurs](../validation/let-holder-mutations.json),
[champs](../validation/let-field-mutations.json),
[C contenu](../validation/let-content-c.json),
[C retours directs](../validation/let-direct-c.json),
[C porteurs](../validation/let-holder-c.json), [C pools](../validation/let-pool-c.json).
The overall suites are complete: **672 standard tests passed
(484.091 s)** and **672 UBSan tests passed (484.634 s)**,
Without any unsolved jump or failure. Previous models of provenance, cleaning,
contracts, fields, scopes and runtime are included.](../validation/let-suites.json)
keeps Python commands, outputs, durations, configurations and prints.

During the development, the new rule of immutability initially refused to
a valid old case of temporary allocation borrowed mutably in an argument.
The treatment of expressions still without name has been corrected and the case is
The results/contraints were monitored in the full regression.
adapted before the final suites to distinguish a content writing from the
creation of a new scalar value.

## Limites

The tests and models are limited, without any general proof of safety.
mutable allocations in place remain Ints; changes in enum variant,
mutable fields, nested references and &mut returns remain outside perimeter.
User destroyers, collections and transitive graphs are not
added. The sources are not moveable and execution is synchronous.
The C is not used to enforce the unmistakable lettuce: the auditor is not
pre-emission control, and modification of C bypasses its guarantees.
Inference, auditor and backend remain in the trust base.
ASan is not restarted, given the previous failure of this host even with a program
C vide ; voir [SAFETY.md](SAFETY.md). CLI programs do not become
The configurations of a single variable CRUST_SANITIZE
family C does not replace an independent compiler.

Previous raw reports keep their syntax and fingerprint versions.
The documentary examples have been migrated; these changes are not
The rapid audit of the
migration that compiled and then jumped the executions C is not a green suite:
His jumps prevented the completion of some model meters.
final execute the entire methods.
