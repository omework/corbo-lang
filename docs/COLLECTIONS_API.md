# Compiler-backed collections and pool allocations

`use std::{Pool, PoolError, Vector, HashMap, String};` imports the public collection names. Their
export file declares those names; the compiler supplies their representations
and method lowering, and [the Corbo runtime](../runtime/corbo/README.md) implements
storage and operations. An empty export declaration does not mean an empty object.
This guide supplements the source-generated [STD reference](STDLIB.md).

The [complete examples](../examples/features/README.md) provide runnable programs
for the interfaces below. The normative rules remain in
[Language Rules](LANGUAGE_RULES.md); an API description does not establish that
all compositions have been executed.

## `Pool<T>` and `A<T>`

| Operation | Meaning |
| --- | --- |
| `Pool<T>::new(count)` | Reserve fixed slots for `T`; the pool's storage must outlive live allocations. |
| `pool.new(value)` | Initialize a free slot and return `A<T>`, moving the supplied value. |
| `pool.new({...})` | Contextual struct initialization in a slot, using the pool's element type. |
| `pool.new()` | Use the element type's valid default initialization; required non-defaultable fields cannot be fabricated. |
| `pool.try(value)` / `.try({...})` / `.try()` | The same initialization with `Result<A<T>, PoolError>`; `Full` recovers slot exhaustion. |
| `*allocation` | Access the stored value; this is distinct from the allocation descriptor itself. |
| `allocation.ref()` / `.mut_ref()` | Borrow its stored value as `&T` / `&mut T`. |
| `&allocation` / `&mut allocation` | Borrow the allocation descriptor as `&A<T>` / `&mut A<T>`. |
| `drop(allocation)` | Run value cleanup, release the slot, and consume the allocation. |

A move of `A<T>` transfers its cleanup responsibility and preserves its source
pool and stable payload address. It does not move the payload bytes into a
container that receives the descriptor. Dropping a container of allocations
cleans those elements before releasing its own storage. A freed slot is reusable;
it does not reactivate a former reference.

Pool capacity is a fixed number of simultaneous live slots per enum arm (one
slot set for an ordinary type). `new` stops on exhaustion; `try` returns
`PoolError.Full`. Neither requests a general-purpose heap allocation. A supplied
value moves and is evaluated once before the slot attempt; failure destroys it
before returning the error. An unexamined successful Result still owns and
cleans its allocation. Reservation/datastack failures remain terminating.
[Pool example](../examples/features/pools/src/main.crb).

## `Vector<T>`

A standalone `Vector<T>` owns a fixed-size descriptor on the datastack and a
region-backed payload. It does not require a user-facing pool:

```rust
use std::Vector;

struct GroupMetadata {
    compressed: bool;
    cursor: usize;
}

struct Table {
    groups: Vector<GroupMetadata>;

    fn new() Self {
        let groups = Vector::new();
        Self { groups }
    }
}

fn main() {
    let mut table = Table::new();
    table.groups.push(GroupMetadata { compressed: false, cursor: 0 });
    print(table.groups.len());
}
```

`new()` infers its element from a typed binding or receiving struct field;
`Vector<T>::new()` can specify it explicitly. Moves transfer cleanup. Dropping
the final owner releases the region, including after scope/async transfers.
`#(stack_region: ...)` supplies the growing-data limit; no capacity argument is
added. The ordinary STD implementation is in
[vector_value.crb](../stdlib/src/collections/vector_value.crb).

Standalone elements can be values, shared or mutable references, and owned
resources. `push` transfers ownership to the vector; `pop` transfers the extracted
value and its dependencies to its receiver. `clear` and destruction clean up all
remaining elements before releasing storage, including nested owners and custom
destructors. A vector needs no pool of its own. If an element is `A<T>`, its
original allocation pool must still outlive that allocation.

The compiler retains immutable element summaries alongside the descriptor's
checked value. Moves preserve this graph; field projections and helper calls
use the same summaries. Pushing a reference retains its target's lifetime and
access constraints. Thread-transfer restrictions propagate from element types.

This API provides `new`, `len`, `is_empty`, `push`, `pop` and `clear`. The existing
indexed/sliced native-vector API is still the pooled path. Conditional and
repeated extraction may retain conservative dependency summaries when exact
membership cannot be proven; that can refuse otherwise valid programs.

A stable internal runtime registration accompanies the movable descriptor so
region lists do not retain the descriptor's former address. Its fixed metadata
mapping is runtime overhead; the configured region byte limit applies to element
data. The registration is released after the region at destruction.

### Pooled vectors (existing API)

A fixed-size descriptor identifies contiguous element storage growing in a
bounded region. The pooled form constructs an owned allocation through a vector pool, as in the
[vector example](../examples/features/vector/src/main.crb).

| Operation | Result and ownership |
| --- | --- |
| `values.len()` | Number of live elements. |
| `values.push(item)` | Move one item into the vector. Exhaustion follows the region-limit failure path. |
| `values[index]` | Access an element after checking the index's value. |
| `&values[index]`, `&mut values[index]` | Borrow an element, retaining the vector's storage dependency. |
| `values.remove(index)` | Move out an element and shift the remaining tail. |
| `values.pop()` | Return `Some(item)` from the last position, or `None` when empty. |
| `drop(values)` | Destroy elements still present before releasing their backing storage. |

Inline elements can change position during removal. An element borrow therefore
prevents incompatible structural mutation. A stored `A<T>` still targets its
original pool slot; a stored reference still targets its original value.
No iterator or container operation erases those dependencies.

The [fixed-array rules](FIXED_ARRAYS_VALIDATION.md) and [vector/ownership decisions](FOUNDATIONS_AND_VECTORS.md)
record the fuller language contracts. This table describes the basic interfaces
used in the executable documentation, not an exhaustive collection test matrix.

## `HashMap<K,V>`

Keys are `i32`, `i64`, `u8`, `u16`, `u32`, `u64` or `bool`. Floating-point and
arbitrary user-defined keys are outside this initial key interface.
Construct with `HashMap<K,V>::new()`. Entry payload addresses remain stable;
index changes do not relocate live payloads.

| Operation | Result and ownership |
| --- | --- |
| `map.insert(key, value)` | Move both inputs; return `Some(previous)` when replacing, otherwise `None`. |
| `map.get(&key)` | Return `Option<&V>`; lookup does not consume the key or stored value. |
| `map.get_mut(&key)` | Return `Option<&mut V>` with write permission and lifetime/synchronization obligations under MA1–MA6. |
| `map.remove(&key)` | Return `Option<V>` by move and make the old entry slot reusable. |
| `drop(map)` | Destroy the values still owned by the map before releasing storage. |

Primitive keys copy implicitly on insertion, so the caller may reuse them.
`copy(key)` remains an optional explicit spelling. Capacity failures and fallible insertion are specified in the
[HashMap rules](HASH_MAP.md). The [map example](../examples/features/map/src/main.crb)
executes basic insertion, borrowing and extraction.

## `String`, `&str` and bytes

`String` owns a region-backed UTF-8 byte sequence. `&str` is a borrowed view;
text does not gain ownership merely because a view was copied or returned.
Construct an owned string through a String pool. `push_str(&str)` appends bytes
while retaining the UTF-8 contract; `byte_len()` reports encoded bytes.
`as_bytes()` makes byte-level access explicit.

The [text example](../examples/features/text/src/main.crb) executes owned-string
append, byte length and a literal's byte view. The full
[UTF-8 specification](UTF8_STRINGS.md) includes character-boundary slicing and
conversion APIs. Consult the [observed documentation limits](DOCUMENTATION_LIMITS.md)
for forms not accepted by the current compiler snapshot; the specification and
executed subset are distinct.

## Budgets and failure

Descriptors and fixed pool storage use the fixed datastack. Growing payloads
use regions configured by `#(stack_region: max_size=..., count=...)` or the
applicable default. `count` is optional. Global datastack properties are optional
as well. Values retain applicable lifetime/budget obligations across moves.
Cleanup precedes storage reuse; page reclamation is a separate OS operation.
[Executable budget example](../examples/features/regions/src/main.crb).
