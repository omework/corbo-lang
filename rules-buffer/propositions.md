[Français](propositions-fr.md)

<a id="propositions-de-règles-crust"></a>

# Proposals for Crust Rules

<a id="rb-01--résultat-dappel-qui-possède-une-allocation"></a>

## RB-01 — Appeal results that have an allowance

**Status — proposed, pending arbitration.** Resumption of the [workshop proposal]](../design-buffer/01-resultat-proprietaire.md).

A call whose type of return may have an allowance must be returned to the applicant.
a named link followed by explicit use,
a transfer or a consuming match can support the result.
ask for immediate destruction of the entire result, write
`drop(-> opération(...));`. The call is executed first. `drop` consomme ensuite
the result and destroys only once the allowances owned by the variant
The production of the product, according to their provenance and the ordinary rules of destruction.
cleaning before the following instruction.

One call only followed by `;` and shape `let _ = …;` are refused.
Control is based on the type of return, including if the variant produced
is known and has no allowance. The diagnosis must indicate the
responsibility abandoned at this place.

The rule extends U1 and L6 as well as H1 and VE3. Patterns that ignore a field
in a match arm and the results fallible without allocation possessed
remain separate issues.
[Language rules](../docs/LANGUAGE_RULES.md) · [Foundals and vectors](../docs/FOUNDATIONS_AND_VECTORS.md)

<a id="à-accepter--destruction-explicite"></a>

### To be accepted — explicit destruction

```rust
fn main() {
    let mut nombres = pool<Int>(2);
    let mut vecteurs = pool<Vector<A<Int>>>(1);
    let mut valeurs = vecteurs.new();
    valeurs.push(-> nombres.new(7));
    let entrant = nombres.new(9);

    drop(-> valeurs.replace(0, -> entrant));

    let suivant = nombres.new(11);
    print(*suivant);
}
```

On the index `0`, the vector is preserved `9` and `drop` destroys the allowance which
contient `7`. With an invalid index, the vector keeps `7` and `drop`
destroys the returned input, which contains `9`In both cases, the name
`entrant` was consumed and construction of `suivant` may reuse the
slot released. The program displays `11`.

<a id="à-refuser--résultat-jeté-par-une-liaison-anonyme"></a>

### To refuse — result thrown by anonymous link

```rust
fn main() {
    let mut nombres = pool<Int>(2);
    let mut vecteurs = pool<Vector<A<Int>>>(1);
    let mut valeurs = vecteurs.new();
    valeurs.push(-> nombres.new(7));
    let entrant = nombres.new(9);

    let _ = valeurs.replace(0, -> entrant);

    let suivant = nombres.new(11);
    print(*suivant);
}
```

The refusal is `let _`which does not express the support of the returned handle.
Replace this line with `valeurs.replace(0, -> entrant);` causes the same
refus.

These examples give the expected verdicts according to the proposal.
Paper examination.
