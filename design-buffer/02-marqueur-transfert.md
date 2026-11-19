[Français](02-marqueur-transfert-fr.md)

<a id="02--déplacements-et-captures"></a>

# 02 — Travel and catches

<a id="décision-validée"></a>

## Validated decision

- A value passed or received by value moves, including for a type
  For example, `let b = a`, `relayer(a)`, `return a`, the value
  finale `a` and `drop(a)` consomment `a`. An explicit call to `copy(a)`
  copy a primitive type value. In
  `fn relayer(n: A<Int>) -> A<Int>`, the arrow indicates the type of return.
- `move a;` in the head of a child block will enter the value named under
  the same name, with effect at the entrance of the block.
- `move { ... }` moves the parent's links used to the entrance
  in the block, including those of primitive type. `&a` in the block borrows the contents of
  capture. To capture a reference to `a`We're binding it before the O.R.
- A value that emerges from the block is provided by its final value and
  received in a new link visible in the parent. The old name
  The old return that reactivated this access remains unusable.
  no new receiver is removed.
- Life control of targets and pools, compatibility
  loans and validity on each path apply to these
  Travel. An displaced allowance keeps its address and transmits
  responsibility for its clean-up.

```rust
fn main() {
    let mut nombres = pool<Int>(1);
    let a = nombres.new(7);
    let recu = {
        move a;
        print(*a);
        a
    };
    print(*recu);
}
```

The replacement of `{ move a; print(*a); a }` by `move { print(*a); a }`
The same capture and return is expressed here.

The syntax is integrated into the kernel operations covered in the
[rapport](../docs/SAFETY.md#cycle-des-déplacements-par-valeur). Syntax
history remains available at file-wide for operations
and the suites that still use it.

<a id="historique--proposition-des-chevrons-seuls"></a>

## History — proposal of the horsemen alone

This proposal had been rejected in favour of the arrows in force at the time.
The following examples keep track of this.

At the head of a transferred argument, `>` remplace `->`. In `f(> valeur)`,
the preparation of the argument invalidates the old access before the evaluation of the
The following arguments are given: `f(a > b)`, `>` is between two expressions
and expresses a comparison. The position of the sign is sufficient to distinguish the two
shapes. The arrow back in `fn f() -> Int` The signature remains the signature.

The proposal first concerns the rating at the call site.
B4 and B4a of [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md), F4 and VE3 of
[FOUNDATIONS_AND_VECTORS.md](../docs/FOUNDATIONS_AND_VECTORS.md). The proposal
left open the notation of signatures and other positions of
transfert.

<a id="exemple-admis-si-les-propositions-01-et-02-sont-retenues"></a>

## Example accepted if proposals 01 and 02 are accepted

```rust
fn main() {
    let mut nombres = pool<Int>(2);
    let mut vecteurs = pool<Vector<A<Int>>>(1);
    let mut valeurs = vecteurs.new();
    valeurs.push(> nombres.new(7));
    let entrant = nombres.new(9);

    drop(valeurs.replace(0, > entrant));

    let contenu = <- valeurs.remove(0);
    if *contenu > 7 {
        print(*contenu);
    }
    drop(contenu);
}
```

<a id="exemple-refusé-par-la-proposition"></a>

## Example rejected by the proposal

```rust
fn main() {
    let mut nombres = pool<Int>(2);
    let mut vecteurs = pool<Vector<A<Int>>>(1);
    let mut valeurs = vecteurs.new();
    valeurs.push(> nombres.new(7));
    let entrant = nombres.new(9);

    drop(valeurs.replace(0, entrant));
}
```

The building `drop` indicates the consumption of its result argument according to the
proposal 01. It does not provide the transfer marker for `entrant` in
the call in `replace`. Examples examined on paper.

<a id="variante-symétrique-pour-un-résultat-de-bloc"></a>

## Symmetrical variant for block result

At the head of the result of a block, `< valeur` remplace `<- valeur` and transfer
the direct parent allowance. The block ends with this result without
The pool and targets
borrowed must survive the transfer according to T3, T6, D1 and A3.

```rust
fn main() {
    let mut nombres = pool<Int>(1);
    let resultat = {
        let local = nombres.new(9);
        < local
    };

    print(*resultat);
    drop(resultat);
}
```

In `if *resultat < 10`, the sign is a comparison between two expressions.
In the O.R., `local` The only remaining negative result was the lack of
Transfer marker. `return < valeur` is the symmetrical candidate
of the `return <- valeur`. The notation of the mode of return in a signature and
other uses of `<-` The following examples are available on paper.

<a id="argument-pour-conserver-les-flèches"></a>

## Argument for keeping arrows

Go uses the same arrow `<-` in both forms of communication.
`canal <- valeur` send to the channel and `recu := <-canal` received since the
channel. The tip visually indicates the direction of the flow. Crust applies
this visual marker to a transfer of property between telescopes, with `->` To
the person called and `<-` to the parent. Keep arrows also distinguish the
The chevrons earn a bonus of the same amount of money as the chevrons.
character by transfer and based on the position of the sign.
[Envoi](https://go.dev/ref/spec#Send_statements) and
[receipt](https://go.dev/ref/spec#Receive_operator) in the Go specification.
