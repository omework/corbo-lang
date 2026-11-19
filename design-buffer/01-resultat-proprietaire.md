[Français](01-resultat-proprietaire-fr.md)

<a id="brouillon-01--résultats-propriétaires"></a>

# Draft 01 — Owner results

Decisions validated in the workshop, ready to be integrated on request.

<a id="règles"></a>

## Rules

1. **Full result.** If the result type can have an allowance,
   the program must receive it, transmit it, treat it in a `match`
   consume or destroy it with `drop(-> opération(...));`. L'appel seul
   follow-up `;` and `let _ = opération(...);` This check is not allowed.
   on the type, even when the compiler knows the variant produced.
2. **Destruction explicite.** The operation is done first. `drop` consomme
   then the result with `->` and destroys once the content possessed
   The standard rules
   borrowing, destruction and provenance apply.
3. **Motif d'un match consommant.** Un motif `_` is refused if it rejects a
   The arm is the whole of the field or variant.
   link the owner's value to a name so that it can be used.
4. **Link used.** A proprietary value received by link must have
   at least one explicit use possible. Reading, borrowing, transfer
   ou un `drop` comptent comme usages. Un usage conditionnel suffit, selon U1.
   Unused link is refused, including a name such as `_retire`.
   A value still possessed after its last use follows the cleaning
   ordinary of its scope.

<a id="règles-à-compléter-lors-de-lintégration"></a>

## Rules to be completed when integrating

- U1 for the use of links and L6 for the destruction of the entire result.
  [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md)
- F2 for consumer reasons, H1 for cleaning responsibility,
  VE3 for `pop` and `replace`and VE4 for the return of the entry by
  `try_push`. [FOUNDATIONS_AND_VECTORS.md](../docs/FOUNDATIONS_AND_VECTORS.md)

The explicit use of the results that are bankrupt without an allowance is also
retenu. [Brouillon 07](07-conversions-resultats-copies-et-vues.md)

<a id="destruction-explicite-du-résultat-entier"></a>

## Explicit destruction of the entire result

```rust
fn main() {
    let mut nombres = pool<Int>(2);
    let mut vecteurs = pool<Vector<A<Int>>>(1);
    let mut valeurs = vecteurs.new();
    valeurs.push(-> nombres.new(7));
    let entrant = nombres.new(9);

    drop(-> valeurs.replace(0, -> entrant));

    let suivant = nombres.new(11);
    drop(-> suivant);
    let contenu = <- valeurs.remove(0);
    print(*contenu);
    drop(-> contenu);
}
```

On the index `0`, the replacement takes place, the former allowance containing `7`
is destroyed before the next instruction and the program displays `9`. With
un indice invalide, `drop` destroys the rendered input and program displays `7`.
In both cases, `-> entrant` makes the original name unusable. Both
The first is to be replaced by the following:
`nombres.new(11)` can reuse the slot returned in the pool of two slots.

<a id="traitement-explicite-par-variante"></a>

## Explicit treatment per variant

```rust
fn main() {
    let mut nombres = pool<Int>(2);
    let mut vecteurs = pool<Vector<A<Int>>>(1);
    let mut valeurs = vecteurs.new();
    valeurs.push(-> nombres.new(7));
    let entrant = nombres.new(9);

    match <- valeurs.replace(0, -> entrant) {
        Ok(ancien) => { drop(-> ancien); },
        Err(rendu) => {
            print(*rendu);
            drop(-> rendu);
        }
    }
}
```

On the index `0`, the vector supports the allocation containing `9` and
bras `Ok` destroys the one that contained `7`. With an invalid index, the vector
garde `7` and the arm `Err` displays and then destroys the allowance containing `9`.

<a id="usage-sans-destruction-anticipée"></a>

## Use without anticipated destruction

```rust
fn main() {
    let mut nombres = pool<Int>(1);
    let mut vecteurs = pool<Vector<A<Int>>>(1);
    let mut valeurs = vecteurs.new();
    valeurs.push(-> nombres.new(7));

    match <- valeurs.pop() {
        Some(retire) => { print(*retire); },
        None => {},
    }

    let suivant = nombres.new(11);
    drop(-> suivant);
}
```

Reading of `retire` satisfied U1. The arm `Some` then destroyed
The pool can reuse its only slot to make sure it is not used for the purpose of the allowance. `11`.
Replace the arm body with `drop(-> retire);` is also allowed.

<a id="cas-refusés"></a>

## Cases rejected

Chaque ligne ci-dessous remplace l'instruction `drop` or arm `Some` of the
l'exemple admis correspondant.

| Forme | Ground for refusal |
|---|---|
| `valeurs.replace(0, -> entrant);` | The owner's result is left out. |
| `let _ = valeurs.replace(0, -> entrant);` | The pattern excludes the entire owner's result. |
| `drop(valeurs.replace(0, -> entrant));` | Transfer of the result to `drop` exige `->`. |
| `Some(_) => {}` | The reason for this is to exclude the allowance paid by the `pop`. |
| `Some(retire) => {}` | The link has no explicit use. |
| `Some(_retire) => {}` | The prefix `_` the name does not count as use. |

Examples of design examined on paper, without execution.
