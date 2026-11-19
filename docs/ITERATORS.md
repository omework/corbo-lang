# STD iterator adapters

`std::iter` contains the source implementations of `Iter`, `Map`, `Filter`,
`Reduce`, the `iter` factory, and their consuming `collect` methods. The Rust bootstrap compiler is
frozen; these adapters target the self-hosted `corboc`.

```rust
use std::iter::iter;

struct Counter { position: i64, end: i64 }
impl Counter {
    fn next(&mut self) -> Option<i64> {
        let value = (*self).position;
        if copy(value) >= (*self).end { return None; }
        let position = &mut (*self).position;
        *position = copy(value) + 1;
        Some(value)
    }
}

fn main() {
    let mut source = Counter { position: 1, end: 7 };
    let mut memory = pool<Vector<i64>>(1);
    let mut destination = memory.new();
    iter(&mut source)
        .filter(|item: &i64| { *item % 2 == 0 })
        .map(|item: i64| { item * 10 })
        .reduce(|acc: i64, item: i64| { acc + item })
        .collect(&mut destination);
    print(destination[0]); // 120
}
```

The source satisfies the structural contract
`fn next(&mut self) -> Option<V>`. Both `iter(&mut source)` and
`Iter::new(&mut source)` explicitly borrow that source. Each following adapter
owns its predecessor and its callback. Borrowed items and captures retain their
normal lifetime constraints; the factory introduces no implicit borrowing.

- `map` transforms one item on demand.
- `filter` calls its predicate with `&V`, destroys rejected items, and yields the
  next accepted item.
- `reduce` uses the first item as accumulator. Its first `next()` consumes the
  remainder and returns the result, or `None` for an empty source. Later calls
  return `None`. Both reducer parameters and its result have type `V`.
- `collect(&mut destination)` consumes the chain and appends its items to the
  destination. It is an instance method on `Iter`, `Map`, `Filter`, and
  `Reduce`; there is no package-level `std::iter::collect` function.

`next()` remains available for explicit consumption instead of collection.

## Compiler boundary

The algorithms are authored in
[`stdlib/src/iter/iter.crb`](../stdlib/src/iter/iter.crb). `corboc` currently has a
specialization pass for these STD templates. It resolves item types, instantiates
their bodies, and materializes concrete callback captures. It may elide an empty
adapter wrapper or reduce a captureless identity callback to forwarding. These
layout reductions preserve ownership of the predecessor.

This is a source-library migration, not the removal of all adapter-specific
specialization from the compiler. Ordinary ownership and borrowing checks still
run on the specialized program. `Vector` and `HashMap` storage algorithms have
not been moved by this iterator cycle.

See the [cycle report](cycles/CORE_COMPOSITION_CYCLE.md#std-owned-iterator-adapters)
for executed checks and platform limitations. Windows ARM64 remains unexecuted.
