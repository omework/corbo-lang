[English](01-resultat-proprietaire.md)

# Brouillon 01 — Résultats propriétaires

Décisions validées dans l'atelier, prêtes à intégrer sur demande.

## Règles

1. **Résultat entier.** Si le type du résultat peut posséder une allocation,
   le programme doit le recevoir, le transmettre, le traiter dans un `match`
   consommant ou le détruire avec `drop(-> opération(...));`. L'appel seul
   suivi de `;` et `let _ = opération(...);` sont refusés. Ce contrôle porte
   sur le type, même quand le compilateur connaît la variante produite.
2. **Destruction explicite.** L'opération s'exécute d'abord. `drop` consomme
   ensuite le résultat avec `->` et détruit une seule fois le contenu possédé
   de la variante produite, avant l'instruction suivante. Les règles ordinaires
   d'emprunt, de destruction et de provenance s'appliquent.
3. **Motif d'un match consommant.** Un motif `_` est refusé s'il écarte une
   allocation possédée, qu'il masque un champ ou la variante entière. Le bras
   lie la valeur propriétaire à un nom pour pouvoir l'utiliser.
4. **Liaison utilisée.** Une valeur propriétaire reçue par liaison doit avoir
   au moins un usage explicite possible. Une lecture, un emprunt, un transfert
   ou un `drop` comptent comme usages. Un usage conditionnel suffit, selon U1.
   Une liaison inutilisée est refusée, y compris avec un nom comme `_retire`.
   Une valeur encore possédée après son dernier usage suit le nettoyage
   ordinaire de sa portée.

## Règles à compléter lors de l'intégration

- U1 pour l'usage des liaisons et L6 pour la destruction du résultat entier.
  [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md)
- F2 pour les motifs consommateurs, H1 pour la responsabilité de nettoyage,
  VE3 pour `pop` et `replace`, et VE4 pour la restitution de l'entrant par
  `try_push`. [FOUNDATIONS_AND_VECTORS.md](../docs/FOUNDATIONS_AND_VECTORS.md)

L'usage explicite des résultats faillibles sans allocation est aussi
retenu. [Brouillon 07](07-conversions-resultats-copies-et-vues.md)

## Destruction explicite du résultat entier

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

À l'indice `0`, le remplacement a lieu, l'ancienne allocation contenant `7`
est détruite avant l'instruction suivante et le programme affiche `9`. Avec
un indice invalide, `drop` détruit l'entrant rendu et le programme affiche `7`.
Dans les deux cas, `-> entrant` rend le nom d'origine inutilisable. Les deux
allocations doivent encore pouvoir coexister avant le remplacement. Ensuite,
`nombres.new(11)` peut réutiliser le slot rendu dans le pool de deux slots.

## Traitement explicite par variante

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

À l'indice `0`, le vecteur prend en charge l'allocation contenant `9` et le
bras `Ok` détruit celle qui contenait `7`. Avec un indice invalide, le vecteur
garde `7` et le bras `Err` affiche puis détruit l'allocation contenant `9`.

## Usage sans destruction anticipée

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

La lecture de `retire` satisfait U1. Le bras `Some` détruit ensuite
l'allocation à sa sortie. Le pool peut réutiliser son unique slot pour `11`.
Remplacer le corps du bras par `drop(-> retire);` est également admis.

## Cas refusés

Chaque ligne ci-dessous remplace l'instruction `drop` ou le bras `Some` de
l'exemple admis correspondant.

| Forme | Motif du refus |
|---|---|
| `valeurs.replace(0, -> entrant);` | Le résultat propriétaire est laissé de côté. |
| `let _ = valeurs.replace(0, -> entrant);` | Le motif écarte le résultat propriétaire entier. |
| `drop(valeurs.replace(0, -> entrant));` | Le transfert du résultat à `drop` exige `->`. |
| `Some(_) => {}` | Le motif écarte l'allocation rendue par `pop`. |
| `Some(retire) => {}` | La liaison n'a aucun usage explicite. |
| `Some(_retire) => {}` | Le préfixe `_` du nom ne compte pas comme usage. |

Exemples de conception examinés sur papier, sans exécution.
