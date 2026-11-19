[English](propositions.md)

# Propositions de règles Crust

## RB-01 — Résultat d'appel qui possède une allocation

**Statut — proposée, en attente d'arbitrage.** Reprise de la [proposition de l'atelier](../design-buffer/01-resultat-proprietaire.md).

Un appel dont le type de retour peut posséder une allocation doit remettre son
résultat à un receveur explicite. Une liaison nommée suivie d'un usage explicite,
un transfert ou un match consommant peuvent prendre en charge le résultat. Pour
demander la destruction immédiate du résultat entier, écrire
`drop(-> opération(...));`. L'appel s'exécute d'abord. `drop` consomme ensuite
le résultat et détruit une seule fois les allocations possédées par la variante
produite, selon leur provenance et les règles ordinaires de destruction. Ce
nettoyage précède l'instruction suivante.

Un appel seul suivi de `;` et la forme `let _ = …;` sont refusés.
Le contrôle repose sur le type de retour, y compris si la variante produite
est connue et ne possède aucune allocation. Le diagnostic doit signaler la
responsabilité abandonnée à cet endroit.

La règle prolonge U1 et L6 ainsi que H1 et VE3. Les motifs qui ignorent un champ
dans un bras de match et les résultats faillibles sans allocation possédée
restent des questions distinctes.
[Règles du langage](../docs/LANGUAGE_RULES.md) · [Fondamentaux et vecteurs](../docs/FOUNDATIONS_AND_VECTORS.md)

### À accepter — destruction explicite

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

À l'indice `0`, le vecteur conserve `9` et `drop` détruit l'allocation qui
contient `7`. Avec un indice invalide, le vecteur garde `7` et `drop`
détruit l'entrant restitué, qui contient `9`. Dans les deux cas, le nom
`entrant` a été consommé et la construction de `suivant` peut réutiliser le
slot libéré. Le programme affiche `11`.

### À refuser — résultat jeté par une liaison anonyme

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

Le refus vise `let _`, qui n'exprime pas la prise en charge du handle rendu.
Remplacer cette ligne par `valeurs.replace(0, -> entrant);` entraîne le même
refus.

Ces exemples donnent les verdicts attendus selon la proposition. Ils ont été
examinés sur papier.
