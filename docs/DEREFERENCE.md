# Dereferencing and reference methods

[Français](DEREFERENCE-fr.md)

## Reference targets

Explicit instance methods take precedence over the universal `ref()` and
`mut_ref()` shorthand. Both MutexGuard variants expose the protected value:

```rust
fn ref(&self) -> &T;
fn mut_ref(&mut self) -> &mut T;
```

The old `get()` / `get_mut()` guard methods are replaced. `let mut guard`
provides mutation permission; acquiring the mutex provides synchronization.
The returned reference remains dependent on the guard and its protected owner.
Destroying/moving them cannot invalidate a still-used reference.

For the allocation primitive `A<T>`, `allocation.ref()` means `&*allocation`
and `allocation.mut_ref()` means `&mut *allocation`. To borrow the allocation
handle itself, write `&allocation` or `&mut allocation`. Ordinary values without
these declared methods retain `value.ref() == &value` and
`value.mut_ref() == &mut value`. On an existing reference these default helpers
borrow the reference itself; there is no implicit recursive dereferencing.

## General wrapper dereferencing

Native dereferencing of `&T`, `&mut T` and `A<T>` is unchanged. For a nominal
wrapper, the compiler resolves `*` statically through explicitly declared
synchronous instance methods with the signatures above. There are no extra
arguments, both methods expose the same target type, and the method body is
checked like any other method. The universal helpers alone do not make a value
dereferenceable. The required method must exist for the selected access mode.

```rust
use std::sync::Mutex;

struct Point { x: i64 }

fn main() {
    let mutex = Mutex::new(Point { x: 1 });
    {
        let mut guard = mutex.lock();
        (*guard).x = 10;           // calls mut_ref(), then writes the target
        print((*guard).x);         // calls ref(), then reads the target
        let view = &*guard;        // shared reference to Point
        print((*view).x);
    }                             // guard unlocks here
}
```

Reads and shared borrows select `ref()`. Assignments (including compound
assignments), mutable borrows and mutable instance-method receivers select
`mut_ref()`. Resolving the method evaluates the operand once and reuses ordinary
call/borrow tracking and source provenance. `*object` denotes the referenced
place, not a move of ownership out of borrowed storage. Primitive reads copy;
non-copy payloads remain subject to the existing move restrictions.

The compiler does not synthesize a lock or a new ownership relationship. The
returned reference retains the method's existing dependency/lock contract.
