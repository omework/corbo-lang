[Français](REASSIGNMENT-fr.md)

<a id="réaffectation--évaluer-détruire-remplacer"></a>

# Reassignment: assess, destroy, replace

For direct access mutable, if `expression` provides an allowance,
`data = expression` Replaces this access in the following order:

1. Fully evaluate the right expression and maintain its result.
2. Destroy the old allowance if it is still alive and distinct from
   the amount received as a result.
3. Install new access in `data`, with its own source.

Access to `data` must be valid on all paths that reach this
affectation. Si un `if` has been able to move `data` before, the replacement is
A branch that leaves the post before posting is excluded.

Un transfert explicite `data = <- local;` can target a mutable variable
The pool and the targets borrowed must be visible in an ancestor block.
survive in the scope of `data`. The prototype accepts this transfer in
a linear block and in a `if` when each branch that continues leaves
a valid recipient, that cleaning orders are compatible and that no
The C selects the remaining active loan only from a replaced identity.
pointer at the end of the branch executed and only a clean-up entry
The contracts shall retain the sources and the
possible dependencies. A receiver declared before a loop can also
be replaced during iteration. `continue` and the normal end of the body
transfer its new value to the next pass. `break` the transmission
on the exit, where it joins the other exits, including the false test
d'un `while`. The constraints of order and validity remain applicable.

Destruction remains followed by recovery of storage according to its source.
The old allowance is not destroyed again in a `drop`, d'un
The same rule replaces the decision of the Court of Justice of the European Communities on the question of the scope of the directive.
initial to keep the old allocations until the scope is cleaned.

<a id="mutation-du-contenu"></a>

## Content change

For an allocated Int, `data = 20` and `data.set(20)` modify the content of
the existing allocation. This case does not follow the destruction/replacement stages
above. The target keeps its address, source and cleaning order.
It requires direct access `let mut data`, ou un emprunt &mut via `.set`.
The variable containing the latter can be declared with `let`.

A scalar right part is evaluated before writing.
borrowing can end before writing; destroy/reset the target during
This evaluation makes the writing refuse. See [LET_MUTABILITY.md](LET_MUTABILITY.md).

<a id="lire-lancienne-valeur-pendant-lévaluation"></a>

## Read the old value during the evaluation

```rust
fn make(memory: &mut Pool<Int>, old: &Int) -> <- Int {
    print(old);
    let mut fresh = new(memory) Int(20);
    return <- fresh;
}

let mut memory = Pool<Int>::new(2);
let mut data = new(memory) Int(10);
data = make(&mut memory, &data);
print(data);
```

The function reads `10` and returns his new allowance before the destruction
of the `10`. The last instruction then displays `20`.

A loan stored in a variable can also be used for the last
The last use analysis distinguishes between the two.
the following uses of the new access installed in the `data`.
If a loan to the old allowance is still to be used after the
The compiler refused to reassign the operation.

<a id="déplacements-fonctions-et-provenance"></a>

## Travel, functions and provenance

- `data = <- data` or one round trip per function of the same allowance
  destroyed not: the identity of the allowance remains the same.
- If the function consumes the old allocation and destroys it, or resets it
  its source, the reassignment does not trigger a second destruction.
- If the new allocation comes from another source, the destruction of the
  the old one uses its origin; `data` then retain the new origin.
- Reassigning a loan changes the access borrowed without destroying the referenced object.
  Copy scalar retain an ordinary assignment.

In C, a separate allocation is made in this form,
After renaming the variables:

```c
Cell *replacement = make(&memory, data);
cell_drop(data);
/* Les accès Corbo suivants utilisent replacement. */
```

The temporary declaration materializes the right value before cleaning.
The issuer uses a new C name for the replaced access.
This access is linked to the new allocation; it is not based on the address.

<a id="capacité-des-pools"></a>

## Pool capacity

The new allowance exists before the old one is destroyed.
only slot does not allow `data = new(memory) Int(20)` quand `data` l'occupe.
Failure to do so stops the program before destroying the old allocation; the
prototype does not unfold the destroyers during this stop.

A pool of two slots allows for successive replacements of a single variable,
with alternating addresses and re-use of holes. For an enum, this
capacity is appreciated by variant: a pool of one slot per variant can replace
an allowance `A` by an allowance `B`, then reuse the slot `A`.

## Validation

[examples/reassignment.crb](../examples/reassignment.crb) illustrates a
reassignment via a function reading the old value, then an allocation
from another source.

[tests/test_reassignment.py](../tests/test_reassignment.py) checks these rules
on the job, stacks and pools, shared and transferable borrowing,
movements and transfers, the resets in right expression, the order
observable destruction, repeated reuse and variants
These cases do not constitute general proof of security.
