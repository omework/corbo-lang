# Universal reference methods and for loops

## Reference spellings

Every type supports `place.ref()` and `place.mut_ref()` as compiler-provided
spellings of `&place` and `&mut place`. They take no arguments and follow the
ordinary place, mutation-permission, lifetime and synchronization rules. They do
not call a user-defined method or implicitly dereference a reference. If `r` is
`&mut T`, `r.mut_ref()` borrows the reference itself; `(*r).mut_ref()` borrows T.
These spellings do not alter allocation identity or cleanup responsibility.

## Iteration

```rust
fn main() {
    let mut values = [10, 20, 30];

    for item in values.mut_ref() {
        *item += 1;
    }

    for item in values.ref() {
        print(*item);
    }
}
```

The iterable expression is evaluated once, at loop entry. Borrowed arrays and
slices yield `&T` or `&mut T` according to the explicit source reference. Objects
with `next(&mut self) -> Option<T>` yield T using the ordinary move/copy rules.
There is no implicit mutable borrowing merely because an enclosing method has
`&mut self`. `for mut item in source` makes the binding mutable; it does not
change the source's reference type or confer mutation permission on its target.

Each iteration introduces a fresh binding and body scope. `continue` advances to
the next item; `break`, return and ordinary completion use existing scope cleanup.
The loop returns no value. An indexed by-value source transfers into loop-local
storage; its indexed reads remain governed by the ordinary element move/copy
rules. No permission to move fields out of a borrowed object is introduced.

The compiler normalizes these forms before ordinary verification, dependency
summaries and placement. Generated names must not capture source names; source
provenance must survive normalization. No runtime iterator protocol or trait is
introduced.
