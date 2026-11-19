[Français](CONDITIONALS-fr.md)

<a id="if--else--chemins-qui-continuent-et-nettoyage"></a>

# If / else: paths that continue and clean up

The prototype accepts the instructions `if`, `else` and `else if`. Conditions
are `true`, `false` or a comparison of two uncopyable expressions:
`==`, `!=`, `<`, `<=`, `>`, `>=`. Both operands are evaluated from left to
right before the branch choice. This first subset does not add any
Bool variables and logical operators.
[expressions `if` Allocation](IF_EXPRESSIONS.md) are now supported
with a receiver and a `<-` final in each branch that continues.
Both branches are checked, even for a literal condition.

<a id="portée-et-disponibilité"></a>

## Scope and availability

Each pair of branch accolades opens a child's scope. Reading and reading
transfer by borrowing may target the parent; consuming his or her allowance requires
the downward transfer already defined:

```rust
let mut data = new(memory) Int(42);
if stop == 1 {
    -> data;
    drop(-> data);
}
print(data); // Refusé : un chemin a consommé l'accès.
```

Access is only available after a condition if it remains valid on all
the paths that reach this instruction. `return`
does not join the following:

```rust
if stop == 1 {
    -> data;
    drop(-> data);
    return;
}
print(data); // Autorisé : seul le chemin conservant data arrive ici.
```

The compiler analyses each branch from the same input state.
then the states of the branches that continue. Names and sources declared
in a branch does not become visible after it.

The last use of loans is adjusted to the path analysed: a loan
used only in `else` does not block destruction in `if`. Un
borrowing used after junction remains protective on the paths which the
the arguments already prepared for an inclusive call also retain
leurs protections.

<a id="nettoyage-sans-double-destruction"></a>

## Cleaning without double destruction

An allowance can be alive on some paths only.
access is then unusable after junction, but cleaning still has to
destroy the allocation on the paths that kept it.

The compiler uses an indicator C per allocation concerned, independent
the storage slot. After renaming and simplification:

```c
int live_data = 1;
Cell *data = cell_new(memory, 42, "data");
if (stop == 1) {
    cell_drop(data);
    live_data = 0;
}
/* Nettoyage à la sortie du scope : */
if (live_data) {
    cell_drop(data);
    live_data = 0;
}
```

This indicator is not based on `Cell.alive` : a pool may have reused the
The cleaning of the old one must not be carried out by the same slot for a new allowance.
So not destroy the news. A collective reset at the junction uses the
the same indicators before reset the storage.

Indicators are local to functions C and their addresses are transmitted
internal parameters when cleaning is done through another function.
The cleaning pointer is replaced by `NULL` when the indicator is zero,
so that you don't load a former heap pointer after you're released.
remains separately transmitted and prevents any call for `cell_drop` in that case.
A local indicator does not escape with a return allowance without
condition: only a return of certainly living allowance is allowed.
This implementation favours verifiability; it does not yet minimize
the number of indicators and internal parameters.

<a id="retours-et-effets-chez-lappelant"></a>

## Return and Effects of the Appellant

Void, scalar and allowance returns are supported in the branches,
The return of allowances must share the type declared
with follow-up of possible sources: see [CONDITIONAL_RETURNS.md](CONDITIONAL_RETURNS.md).
Each return first emits the cleaning of the crossed telescopes, excluding
the allowance returned, if applicable, and
on `return` C. If all paths return, the rest is not issued.
A scalar function or returning an allowance must provide a return on
All the way.

The branches that return are excluded from the continuation of the function,
the appellant's allowances remain in the
The call is dismissed. A conditional reset cannot therefore leave the appellant
access to a potentially destroyed allocation. Its final destruction remains
the appellant no longer uses it.

<a id="limites-de-cette-étape"></a>

## Limitations of this stage

Conditional returns and expressions `if` with receiver keep
the potential sources of the same type of allocation. Direct reallocation is limited to the current scope:
a branch cannot directly reassign a variable from its parent.
Return transfers are still possible when roads which
The same is true of the fact that the number of workers in the labour force is still very high.
on a path no longer compel his order; a difference of subset
This is not a conflict alone, therefore.
coexisting on each path must be preserved. If they impose a cycle
The prototype produces a diagnosis.

[examples/conditionals.crb](../examples/conditionals.crb) shows both
departure and re-use of an address after conditional destruction.
[tests/test_conditionals.py](../tests/test_conditionals.py) check both
from the conditions on heaps, stack and pool, borrowings, calls,
nested returns, resets, successive junctions and enum pools.
This perimeter does not include loops or user destroyers and
does not constitute general proof of safety.
