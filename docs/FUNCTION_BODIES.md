[Français](FUNCTION_BODIES-fr.md)

<a id="vérification-mémoire-des-corps-sans-appel-réel"></a>

# Memory verification of bodies without real call

**Mutable-access update:** [MA1–MA6](MUTABLE_ACCESS.md) supersede exclusion
inferred from `&mut` alone. Exclusion examples and verdicts recorded in earlier
cycles below are historical evidence, not the current access-compatibility rule.
Permissions, validity, synchronization and branch completion are separate checks.


Each function is now covered by the memory verifier, even if
The rules of language don't change.

```rust
fn broken(mut data: -> Int) {
    drop(-> data);
    print(data); // Refusé même sans appel à broken.
}
```

Multiple consumption, travel during active borrowing, borrowing
mutable incompatible and mutations via read parameter are also
The control takes into account the latest uses: two mutable borrowings
successively, if the former has completed its uses, it remains possible.

<a id="procédé"></a>

## Process

After validation of signatures and inference of effects, results and constraints,
`Compiler.verify_function_bodies` creates an isolated auditor for each function:

1. Each assigned parameter receives a distinct abstract allocation identity.
   Its real mode (`&`, `&mut` ou `->`) is applied to the entry of the function.
2. Each source or source of parameter receives a storage identity
   The inferred equalitys bring together the identities concerned; the
   distinctions incompatible with these equalitys are refused.
3. A verification invocation prepares these parameters, then runs through the body
   with the same verifier as the actual calls: travel, borrowing,
   expressions, branches, loops, returns, reassignments and cleanings.
4. Subcalls are checked from their [opaque contracts](MODULAR_CALLS.md),
   without going through their bodies in this symbolic environment.
   The statements, allocations, indicators and texts C of this passage are discarded.

Separate incoming identities are not a new restriction
Two readable parameters may indicate the same actual allocation.
Other combinations with mutable or transferred access remain subject to the
exclusive controls on calls.
protect relations between sources, particularly in relation to the resources.

Sizes, values and physical addresses are not required for this passage.
Branches are not removed from the dummy value of a parameter.
Paths that become inaccessible after a return, loop or loop exit
The call differs according to the usual treatment of the auditor.

<a id="sources-et-backend"></a>

## Sources and backend

A Source `Pool<T>` Keeps his type. A generic source. `Allocator` remaining
abstract: the passage does not arbitrarily impose on him the pile, a stack or a
the actual pool. The allocation requirements are always inferred and verified
in the face of real call storage. Compatibility of a generic allocator
with an operation requiring a pool is therefore not deduced from this only passage.

The final program retains specialization and controls over actual calls.
Unused function does not produce any C definition in binary.
symbolic object or allocator does not reach the final C. Runtime and addresses
allowances do not change.

<a id="ce-que-cette-étape-ne-prouve-pas"></a>

## What this step does not prove

The body verification is no longer dependent on its use by the program.
Subcalls now only use an opaque contract. Backend C
travels the bodies for the specialized generation; `check` stops before
The block checker remains shared with the backend and its
temporary C fragments are thrown away: this is not evidence independent of the
verifier or translation into C.

The guarantees remain those of the current subset.
and transitive reference graphs remain outside the scope.
Unchangeable &Int fields are now processed in the subset of
[REFERENCE_FIELDS.md](REFERENCE_FIELDS.md), with sources of fields in the
The allocation of these types of returns has now been reduced to a level of
[contract of borrowed targets](BORROWED_RETURNS.md), controlled at each border
Direct returns of loans remain outside the perimeter.

<a id="régressions"></a>

## Regressions

[tests/test_function_bodies.py](../tests/test_function_bodies.py) check refusals
without appeal and their consistency with the functions called, the loans completed,
readable or mutable parameters, branches, loops, protection
the prepared arguments, the source equities, the enums and the absence of C
symbolic in the final result.

Validation: 494 tests passed in the full standard suite and 494 with
`CRUST_SANITIZE=undefined`, including 27 new body tests.
