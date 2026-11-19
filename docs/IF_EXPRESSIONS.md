[Français](IF_EXPRESSIONS-fr.md)

<a id="if-comme-expression--un-receveur-et-un-transfert-explicite"></a>

# If as an expression: a receiver and an explicit transfer

```rust
let mut result = if choice == 1 {
    let mut a = new(memory) Int(10);
    <- a
} else {
    let mut b = new(memory) Int(20);
    <- b
};
print(result);
```

Each branch that continues provides a value of the same type and mode.
An allowance requires a `<- a` Final without semicolon. Unintegible
may be provided by name, literal or reading `*data`. A value
branch final does not leave the function. The results borrowed are
out of this subset. `else` is mandatory, including in a chain
`else if`.

`<- a` provides the value of the branch to the recipient in his parent; he does not
The second is that the `return` explicit in a branch
leaves the whole function, after cleaning. This branch does not join
not the recipient and therefore should not provide value to the expression.
branches leave the function, the receiver and its suite are not produced.

<a id="nettoyage-et-stockage"></a>

## Cleaning and storage

The selected allocation is transferred to the receiver's scope.
the branch's allowances are destroyed when it is closed, in reverse order of
creation/receipt. The recipient then ensures the cleaning of the allowance
selected, exactly once. Its address remains unchanged.

Only the chosen branch runs: a pool of one slot is enough for the example
If no other allowance is in its possession, the compiler shall not create an allowance.
to collect branch values.

The provenance is preserved. Two variants of the same enum may come from
Two separate pools of the same type remain in the public pool.
sources, kept as possible sources of the result.
Each possible source is protected according to [PROVENANCES.md](PROVENANCES.md).
An allowance dependent on a source declared in its branch cannot be
Get out of this branch.

<a id="valeurs-du-parent-et-réaffectations"></a>

## Parent values and reallocations

A parent's allowance requires the transfer of the following previously defined downward:

```rust
let mut data = new(memory) Int(10);
let mut result = if choice == 1 {
    -> data;
    <- data
} else {
    let mut other = new(memory) Int(20);
    <- other
};
```

The old access `data` becomes unusable after junction: a path has it
On the path that keeps the old allocation, it remains followed
for cleaning its scope. On the path that transfers it, only the result
The independent indicators of slots distinguish these from those of the other slots.
If the pool is not a good place to use the address, the pool will use the address.

A reallocation can be expressed `if`. The recipient must be
The first assessment is that the
result selected, then destroys the old allowance if it is still
living and distinct from the result followed, according to the
[reassignment contract](REASSIGNMENT.md). Select the original allowance
by transfer does not cause further destruction.

<a id="fonctions-arguments-et-c-généré"></a>

## Functions, arguments and C generated

The result can be received in a function, transferred to a call with
`consume(-> if ... { ... } else { ... })` or borrowed temporarily with
`inspect(&if ... { ... } else { ... })`. The assessment of arguments remains the
A temporary borrowed one follows the cleaning of the calling telescope.

C simply keeps the selected pointer in a common variable, after
cleaning of each branch. After renaming and simplification:

```c
Cell *selected = NULL;
if (choice == 1) {
    Cell *a = cell_new(memory, 10, "a");
    selected = a;
} else {
    Cell *b = cell_new(memory, 20, "b");
    selected = b;
}
/* Utilisation du receveur, puis nettoyage de son scope : */
cell_drop(selected);
```

The auditor shall bring the candidates together in a selected descriptor, of type
known and bearing possible sources, as for the
[retours conditionnels d'allocations](CONDITIONAL_RETURNS.md). The old
Transferred Identities Leave Static Cleaning Without Destruction of Their
Other effects of branches continuing after expression remain
The branches that leave the function retain their effects in the
return to this function.

## Validation

[examples/if_expression.crb](../examples/if_expression.crb) Show the receiver,
the continuation of the function and stability of addresses in a pool of a slot.
[tests/test_if_expressions.py](../tests/test_if_expressions.py) check both
from the pile, the stacks and pools, the enums, the transfers of the parent,
reallocations, borrowings, arguments, anticipated returns and
interlocking expressions. Branches of no value or different types,
sources too short, old accesses and unused recipients are denied.
These tests are not a general proof of safety.
