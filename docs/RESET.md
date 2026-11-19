[Français](RESET-fr.md)

<a id="reset--destruction-collective-avant-réinitialisation"></a>

# Reset: collective destruction before reset

**Historical document of the existing implementation.** On 4 November 2026,
the user has validated the withdrawal of `pool.reset()`/`memory.reset()` prototype
Target: see [PR1](ASYNC_MULTITHREAD_RULES.md#6-retrait-de-reset-du-prototype).
The compiler, contracts and tests described here have not yet been
migrated, in accordance with the request not to implement anything during the consignment.
Past results are evidence of previous behaviour, not of past
the future absence of this API.

`memory.reset()` explicitly requests the destruction of all still existing allowances
This rule is to be used in the case of a new storage system.
replaces the old reset which required an already empty source.

<a id="vérification-et-ordre"></a>

## Verification and order

Before destruction, the compiler checks future uses of access
direct and borrowing, in active scopes and calling functions.
He refuses to reset if one of these accesses still needs to be used.
temporarily suspended during an appeal is also taken into account.

```rust
let mut memory = pool<Int>(2);
let mut a = new(memory) Int(10);
let mut b = new(memory) Int(20);
print(a);
memory.reset(); // Détruit b, puis a, et réinitialise le pool.
```

Ajouter `print(a)` The same applies to the rest of the family.
a subsequent use of a loan to `a`, or for a move or a `drop`.
The last use alone does not lead to destruction; `reset`
is the explicit request that triggers it here.

Cleaning only concerns this source. It runs through active telescopes
from the deepest to the most external, and their allocations in reverse order of
creation/reception. The order is not grouped by enum variant.
already destroyed allowances are ignored; access to destroyed allowances
are invalidated and the end-of-block cleaning does not destroy them again.

<a id="fonctions-et-c-généré"></a>

## Functions and C generated

Recevoir `&mut Allocator` ou `&mut Pool<T>` authorizes the real source reset,
(a) the amount of the loan, including allowances remaining in the calling scopes.
read source does not allow it. The prototype functions are already
The compiler checks the allocations and the number of calls.
the uses concerned at this site.

For example, for a function that only calls `memory.reset()`, deux
the appellant's living allowances, after renaming, produce:

```c
static void clear(Source *memory, Cell *a, Cell *b) {
    cell_drop(b);
    cell_drop(a);
    source_reset(memory);
}
```

Cleaning parameters are internal to the generated C. They avoid reference
variables C out of function and transmit the necessary pointers
The [summary of effects]](EFFECTS.md) now determine
sources that can actually undergo a reset, including transit.
allocations that may depend on these sources require these catches.
which only allocates them does not receive them for the old allowances of this
This does not change signatures written in Corbo.

The low level C function `source_reset` Keeps its source control empty:
The destructions were already issued before his appeal. On the job they make the
`free` ; on stacks and pools they release slots according to the mechanisms
The virtual mapping remains available until the source closes.
Reusing an address after reset does not reactivate old accesses.

<a id="exemple-et-tests"></a>

## Example and tests

[examples/reset.crb](../examples/reset.crb) returns an allowance from a
function, collectively destroys values via another function, and
reuse storage.

[tests/test_reset_transitions.py](../tests/test_reset_transitions.py) covers the
three sources, reassigned or transferred allocations, interlocked scopes,
the calls and reborrowings, future denials of access, repeated re-internets,
enum pools and address reuse.
references stored in memory effects objects and branches remain out
the current subset; these tests are not general evidence.
