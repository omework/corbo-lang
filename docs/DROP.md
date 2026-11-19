[Français](DROP-fr.md)

<a id="destruction-explicite--appels-et-réutilisation-des-slots"></a>

# Explicit destruction: calls and re-use of slots

## Destructor method

`fn drop(&mut self)` is the destructor signature for a declared
type. The omitted return type is `Void`. Define it in the type's `impl`. The name `drop` is reserved for
destruction. User code requests destruction with `drop(object)`; the
compiler alone invokes the method.

Every declared type has an empty destructor by default. If the developer
defines a destructor, that definition takes the place of the empty default.
The compiler may omit a call to the empty default in generated code.

Explicit `drop(object)` and automatic destruction at scope exit follow
the same sequence:

1. Invoke the destructor once while the object and its fields are valid.
2. Destroy the owned fields in the order required by their dependencies.
3. Reclaim the object's storage.

A move transfers responsibility for destruction to the receiver. The moved
value is destroyed through that receiver. The Rust backend supports custom destructors for fixed values, including
pooled values. Inline vector elements and consuming matches on aggregates
with custom destructors remain outside the implemented subset.

This contract complements that of [block outputs]](SCOPE_EXIT.md), for the
current subset of the prototype.

<a id="transition-vérifiée"></a>

## Verified transition

`drop(-> data)` consumes direct access to a living allowance attached to the
The current scope. It is refused if a loan still has to serve.
`memory.drop(-> data)` check in addition that `memory` is the source of origin.

The compiler is issued `cell_drop`, marks the death benefit and invalids access
The release of the block does not destroy it a second time.

Lors d'un appel `release(-> data)`, the appellant's access is invalidated and
the allowance is transferred to the function. The function can destroy it directly
or transfer it to another function that destroys it. `&data`
ou `&mut data` does not give this capacity of consumption.

A loan whose last use is a call remains compatible with a
subsequent consumption:

```rust
let mut view = &data;
read(view);       // Dernière utilisation de view.
release(-> data);  // Autorisé.
```

Si un autre `read(&view)` then appears, the transfer to `release` is
The same rules apply to transferable loans and reborrowings.
transmitted through several functions.

<a id="réutilisation-physique-et-identité"></a>

## Physical reuse and identity

L'exemple [examples/drop_reuse.crb](../examples/drop_reuse.crb) remplit un pool
Two slots: `data = 42`, then `guard = 99`. A function consumes `data`,
destroyed it via another function and allocated `fresh = 43` in the same pool.

The test confirms that the address of `fresh` is that of `data`, tandis que
`guard` The destruction trace contains exactly:

```text
destroy data=42
destroy fresh=43
destroy guard=99
```

The compiler creates a new object of tracking allocation for each `new`.
He does not deduce his identity from the address obtained at the execution.
Reusing a slot does not reactivate old access or old borrowing.
Reading, borrowing, moving or destroying the old access remains denied.

The C issued for both functions corresponds to this, after renaming and
removal of intermediate variables:

```c
static void release(Cell *data) {
    cell_drop(data);
}

static Cell *replace(Source *memory, Cell *old) {
    release(old);
    Cell *fresh = cell_new(memory, 43, "fresh");
    return fresh;
}
```

The old pointer variables can remain in the generated C.
the auditor prevents the issuance of a new access through them;
runtime does not assign them a generation number and does not check each
read. Edit this C manually exits the verified perimeter.

## Validation

[tests/test_drop_transitions.py](../tests/test_drop_transitions.py) covers the
interlocked calls, the latest uses and future uses of shared borrowing
and mutable, the arguments aliased, the double consumption and the provenance.
Borrowing and then consumption cases are executed with pile, stack and pool.

Pool tests compare addresses when reusing a hole
and a recovered suffix. They also check 20 replacements
successively via functions, denials of old accesses and an enum pool of which
variants have different sizes. Reusing a variant
preserves the living values and addresses of the other variant.

These are executable regressions, not general proof of safety.
