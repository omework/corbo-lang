[Français](CONDITIONAL_RETURNS-fr.md)

<a id="retours-conditionnels-dallocations-et-provenances-possibles"></a>

# Conditional returns of allowances and possible sources

A function can return a different allocation depending on the branch:

```rust
fn create(memory: &mut Pool<Int>, n: Int) -> <- Int {
    if n == 1 {
        let mut a = new(memory) Int(10);
        return <- a;
    } else {
        let mut b = new(memory) Int(20);
        return <- b;
    }
}
```

The contract for this stage requires:

- An explicit allocation return on all paths that complete the function.
- The type declared for each allowance returned.
- Follow-up of all possible sources of returned allowances.
- A source that survives return, according to existing transfer rules.

The sources can be different. The result keeps the finished set
the possible sources, deducted without additional annotation.
possible source must survive transfers and remain protected against a reset
Two separate pools remain two sources,
Even if they have the same guy.

For an enum, the returned variants may differ and come from pools
The private stacks of the variants are not different from the same enum.
independent public sources. See [PROVENANCES.md](PROVENANCES.md).

<a id="nettoyage-et-réception"></a>

## Cleaning and reception

Only the chosen branch is executed. A function that creates an allocation in
each exclusive branch can therefore work with a pool of a single slot,
If nothing else is holding him up at this moment.

The returned allowance crosses the telescopes to the caller.
allocations of this road are destroyed before return, in the order prescribed.
If the function chooses between two arguments transferred, the argument not returned
is cleaned; the caller's old access remains consumed in both cases.

Recipient gets access to the selected allowance and a new entry
This access retains the possible provenances and may be used in the order of receipt.
be borrowed, transferred, destroyed or affected by a reset of this source.
The rules for the last use of borrowings remain applicable.

A cleaning indicator attached to the old access is disarmed when returned,
If a return trip gives the same allocation to the scope
the junction restores its indicator on the paths where it remains
live. Local indicators at a completed function are not included
by a subsequent branch of the appellant.

<a id="représentation-du-résultat-et-c-émis"></a>

## Representation of the result and C issued

The C simply returns a pointer from each branch, after
After re-commandation:

```c
static Cell *create(Source *memory, int n) {
    if (n == 1) {
        Cell *a = cell_new(memory, 10, "a");
        return a;
    } else {
        Cell *b = cell_new(memory, 20, "b");
        return b;
    }
}
```

No additional allocation or copy of object is required to gather
returns. The address of the selected object remains unchanged.

For the purposes of the verification, the compiler shall bring together the candidates in a descriptor
The former results were the only result of the appellant, bringing together possible sources.
the identity of the returned candidates are removed from static cleaning without
It is a transfer, not an end of life of the
the object executed. The descriptor of the result then ensures its unique cleaning.
If all returns make exactly the same allowance known before the call,
his identity is preserved: his import correspondences and his markings of
transfer remains valid. Former accesses consumed are not reactivated
by this retention; only the receiver gets the access returned.
local or separate continue to use the selected descriptor described
ci-dessus. Voir [AUDIT_MEMORY.md](AUDIT_MEMORY.md).

The effects of other operations on each path, including a reset affecting
appellant's allowances, are kept in the meeting of statements.

A return may also select the original allowance of a reassignment or
If the function has already consumed the old allowance,
the reassignment does not trigger a second destruction.
is consumed, destroyed after evaluation of the new result, according to the
[reassignment contract](REASSIGNMENT.md).

<a id="limites-et-validation"></a>

## Limitations and validation

Applicants must keep the same type of declared; their sources may
The terms `if` with receiver are
now supported according to [IF_EXPRESSIONS.md](IF_EXPRESSIONS.md).
[direct returns &Int](DIRECT_BORROW_RETURNS.md) are now allowed with
conservative union of targets and child control → parent. [back &mut Int](MUTABLE_BORROW_RETURNS.md) are also accepted; each target
possible retains exclusive protection. The merger of reception orders
The total amount of the grant is not limited to the total amount of the grant.
The local government would be destroyed by leaving the office.

[examples/conditional_returns.crb](../examples/conditional_returns.crb) montre
Two branches, an intermediate function and the reuse of a pool of a slot.
[tests/test_conditional_returns.py](../tests/test_conditional_returns.py) covers the
piles, stacks, pools, enums, nested calls, argument selection
The tests check the number of loans, reassignments and reassignments.
addresses and traces of destruction, as well as refusals of type, type,
The data are not available from the source, of missing life and return.
General Safety.
