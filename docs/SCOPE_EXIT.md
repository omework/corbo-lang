[Français](SCOPE_EXIT-fr.md)

<a id="sortie-dun-bloc--contrat-et-traduction-en-c"></a>

# Release of a block: contract and translation into C

This step concerns the normal output of a block and `return`, in the
Corbo's current subset. It does not cover the process after a stop
on error, destroyers user or branches with memory effects.

<a id="règle-de-nettoyage"></a>

## Clean-up rule

P3–P4, L3–L4 and L7 specify the model of the implicit data stack.
receiver of a transfer has a location in a durable beach
The dependencies of the destroyer fix the order
destruction. After cleaning, the cursor of the child beach
the back to its entry position. For a typed pool, a destroyed slot can
The following examples are used independently of this setback.
use the historical syntax of explicit sources.

At each block exit, the compiler:

1. The parent is responsible for the explicitly transferred allowances.
   The reception adds them to the parent's order,
   maintaining the relative order of the allowances transferred together.
2. Destroyed the remaining living allocations attached to the block, in reverse order
   A benefit already consumed by the `drop` is ignored.
3. Closes the sources created in the block, in reverse order of declaration,
   after checking that they no longer provide any living allowance.
   A source received by borrowing is not closed here.

Un `return` successively leaves the blocks encompassing up to function.
Each block applies the same rule. If the return transfers an allowance,
It crosses these borders without being destroyed; the recipient of the call in
Then, the cleaning will be carried out. A scalar return retains its value during
The instructions after return are not issued.

<a id="exemple-vérifiable"></a>

## Verifiable example

The complete program is in [examples/scope_exit.crb](../examples/scope_exit.crb).

```rust
fn create(memory: &mut Allocator) -> <- Int {
    let mut outer = new(memory) Int(1);
    {
        let mut inner = new(memory) Int(2);
        {
            let mut result = new(memory) Int(3);
            return <- result;
        }
    }
}

fn main() {
    let mut memory = Pool<Int>::new(3);
    let mut received = create(&mut memory);
    print(received);
}
```

| Event | Nettoyage |
| --- | --- |
| Release of the block of `result` | `result` is transferred, he remains alive |
| Release of the block of `inner` | Destruction of `inner` |
| Output of `create` | Destruction of `outer`, return from `result` |
| Continue `main` | Viewing `3` |
| Output of `main` | Destruction of `result`, pool closing |

The C emitted follows this sequence. By renaming the generated variables and by
omiting intermediate variables:

```c
static Cell *create(Source *memory) {
    Cell *outer = cell_new(memory, 1, "outer");
    Cell *inner = cell_new(memory, 2, "inner");
    Cell *result = cell_new(memory, 3, "result");
    cell_drop(inner);
    cell_drop(outer);
    return result;
}

/* Dans le point d'entrée : */
Source memory = source_pool(3);
Cell *received = create(&memory);
printf("%d\n", received->value);
cell_drop(received);
source_close(&memory);
```

The transfer does not copy the object: the returned pointer keeps its address.
Cleanup calls are inserted before the `return` C; C does not add them
automatiquement.

<a id="destruction-et-récupération-du-stockage"></a>

## Destruction and recovery of storage

`cell_drop` first executes the destruction of demonstration (the trace `destroy`),
then mark the dead object and recover its storage according to its source:

| Source | After destruction |
| --- | --- |
| `allocator()` | Appeal `free` on the allowance |
| `stack(...)` | Back of cursor on dead suffix; inside holes wait |
| `Pool<T>::new(...)` | Reusable free slot; slider back on dead suffix |

In the example, `result` is physically above `inner` and `outer`.
Their destruction does not allow the cursor to be turned back.
`result` is destroyed in `main`, the three slots form a dead suffix :
the runtime recovers successively `result`, `inner`, then `outer`.
This recovery does not revive any destroyers.

`source_close` then release virtual mapping of stacks and pools via
`munmap`. It requires an empty source; it does not replace the destruction of
objects. Bytes do not need to be erased to make slots free.

## Validation

[tests/test_scope_exit.py](../tests/test_scope_exit.py) compares traces of C
compiled and executed at expected orders: normal outputs, Void returns,
scalar and allocations from interlocked blocks, `drop` order of
receipt, closure of a private source and refusal of a return from which the source
The main sequences are executed with the three sources.
A test also inspects the absence of an allowance located after `return`.

These tests link this rule to the C performed for specific cases; they do not
This is not evidence for all programs accepted.
global remains described in [SAFETY.md](SAFETY.md).
