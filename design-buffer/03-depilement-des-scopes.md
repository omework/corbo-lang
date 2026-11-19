[Français](03-depilement-des-scopes-fr.md)

<a id="brouillon-03--dépilement-des-scopes-et-placement-des-transferts"></a>

# Draft 03 — Removal of the scopes and placement of transfers

<a id="sources-de-stockage"></a>

## Sources of storage

- **Data stack classique.** Implicit source of local values. Each value occupies a
  location in a range of bytes, with the required alignment.
  cursor recovers a free suffix. An inside hole is recovered when it
  is in turn part of a free suffix. The depilation rule below
  This source is targeted.
- **Typed pool (`pool<T>(n)`).** The capacity is expressed in slots adapted to the
  `T`. After destruction, an inner slot is reusable via the index of
  free slots, even if subsequent allowances are still alive.
  pool cursor can also back off on a free suffix.

See L7 and P8 in [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md) and description
of both sources in [SCOPE_EXIT.md](../docs/SCOPE_EXIT.md#destruction-et-récupération-du-stockage).

<a id="règle-retenue-dans-latelier"></a>

## Rule adopted in the workshop

In a classic data stack, an allocation transferred to the parent scope
is built directly to the reserved location in the parent's beach.
She keeps her address while she's transferred.
the cleaning destroys the allowances which are still attached to it in
Respecting their addictions.
The cursor of the child beach then returns to its entry position.

The dependencies necessary for cleaning set the order constraints.
A destroyer reading a target must execute while it is
A stored reference that the destroyer does not read does not add
The target must nevertheless survive the reference
For example, a field of the parent that borrows a local value of
the child must be reassigned to a sustainable target before the child leaves the child.

For fixed size values, the compiler tries to stack last
The first one will be destroyed.
If the order cannot be established,
the normal depilation applies. The validity of the program is independent
The placement preserves the lifespans, the effects of this optimization.
initialization and stable addresses.

## Exemple admis

```rust
struct Point {
    x: Int,
}

fn main() {
    let resultat = {
        let temporaire = Point { x: 7 };
        print(temporaire.x);

        let conserve = Point { x: 9 };
        <- conserve
    };

    print(resultat.x);
    drop(-> resultat);
}
```

The location of `conserve` belongs to the beach of the parent from its
The removal of the child beach recovers the storage of the
`temporaire` and preserves the location and value of `resultat`.

## Placement interdit

For the same program, place `conserve` in the beach that will be recovered
on the return of the child cursor would make a living object reusable.
is a counter-example to this placement plan. The source program remains accepted
if booking in the parent is possible.

<a id="contre-exemples-à-chercher"></a>

## Counter-examples to be sought

- A conditional transfer from another branch without receiving
  Check the status of the reserved area and the balance sheet of the
  nettoyage.
- Successive transfers through interlocked telescopes.
  each step back preserves the address and storage of the living result.
- A loop that produces a transfer on one path and resumes on another.
  Check for re-use of reservations, capacity limits and absence
  recovery of a still alive result.
- Two paths destroying the same allocations in different orders.
  Check for suffix recovery, then return to the input cursor.

Example of design examined on paper. The above counter-examples
and to validate.

<a id="règles-à-relier-lors-de-lintégration"></a>

## Rules to be connected when integrating

- V5, T3, T5, L2–L4, L7, P3, P4 and P8 for address, transfers,
  the cleaning order based on dependencies and recovery methods.
  [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md)
- ST10 for the life of a reference stored after reassignment.
  [STRUCTURES_METHODS.md](../docs/STRUCTURES_METHODS.md)
- G10 and G12 for range recovery and stability of values
  vivantes. [GROWING_REGIONS.md](../docs/GROWING_REGIONS.md)
