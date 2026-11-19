[English](TYPE_FEATURES.md)

# Type features — règles retenues

Intégration du brouillon 06 validé. Ce document est normatif ; il décrit les
règles visées, pas une affirmation de couverture de l’implémentation.

**TF1 — Déclaration structurelle.** `type feature Nom { fn methode(&self); }`
déclare exactement une méthode. Les receveurs admis sont `&self`, `&mut self`
et `-> self`, correspondant aux signatures concrètes de ME1. Le nom et la
signature complète de la méthode doivent correspondre ; les noms des paramètres
ne font pas partie de cette correspondance. Les contraintes à plusieurs
méthodes restent reportées aux traits.

**TF2 — Portée.** Une feature est une contrainte dans une signature de fonction,
pas un type de stockage effacé. Les champs de structures et les éléments de
collections restent concrets. Deux paramètres portant la même feature sont
résolus indépendamment : ils peuvent recevoir des types concrets différents.
Les contraintes imposant une égalité de types entre paramètres sont reportées.

**TF3 — Garanties du corps.** Sur un paramètre contraint, le corps ne peut
appeler que la méthode garantie par sa signature. Il peut transmettre cette
valeur à un autre appel seulement si la garantie disponible satisfait
l’exigence de cet appel. Une méthode supplémentaire du type concret choisi
ne rend pas valide un corps qui exige une garantie absente de sa signature.
Cette vérification inclut les exigences indirectes et les relais de fonctions.

**TF4 — Résolution statique et contrats.** Le compilateur choisit la méthode
concrète à la compilation. Le passage par valeur et les règles d’emprunt
suivent B4 et ME1/ME2/ME4. Les effets, origines
d’emprunts et dépendances proviennent du contrat de la méthode concrète
résolue ; la feature seule n’invente pas un contrat d’effets neutre.

**TF5 — Résultat concret.** Une feature peut figurer dans le type de retour
lorsque le compilateur détermine le type concret du résultat. Le résultat
reste de ce type concret. Retourner un argument emprunté conserve son type
et son origine, avec les vérifications de B5. La feature n’autorise ni
promotion implicite ni prolongation de la durée de vie de sa cible.

```rust
type feature Tracer { fn trace(&self); }
struct Console { niveau: Int }
struct Journal { compteur: Int }
impl Console { fn trace(self: &Console) { print(self.niveau); } }
impl Journal { fn trace(self: &Journal) { print(self.compteur); } }
fn tracer(t: &Tracer) { t.trace(); }
fn tracer_deux(a: &Tracer, b: &Tracer) { tracer(a); tracer(b); }
fn restituer(t: &Tracer) -> &Tracer { t.trace(); return t; }
fn main() {
    let console = Console { niveau: 1 };
    let journal = Journal { compteur: 2 };
    tracer_deux(&console, &journal);
    let resultat = restituer(&console);
    print(resultat.niveau);
}
```

Les annotations historiques `#(type, ...)` et `#(types, ...)` ne déclarent
pas de feature. La directive de région relève de G6 et emploie la catégorie
`directive`.
