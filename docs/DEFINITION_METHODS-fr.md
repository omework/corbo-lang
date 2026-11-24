[English](DEFINITION_METHODS.md)

# Méthodes dans les définitions et receveurs explicites

Les méthodes et constantes associées sont déclarées dans la définition du
`struct` ou de l’`enum`, après les champs ou variantes. Chaque champ et chaque
variante se termine par `;`. Les initialiseurs, paramètres et bras de `match`
conservent leurs virgules.

```rust
struct Compteur {
    valeur: i64;

    pub fn lire(&self) i64 {
        self.valeur
    }

    pub fn incrementer(&mut self) {
        self.valeur += 1;
    }
}
```

Le type de retour suit directement les paramètres, sans `->`. Son absence
signifie le résultat unité ; `()` peut être écrit explicitement. Cette notation
s’applique aussi aux contrats structurels, aux types appelables et aux retours
explicites des closures. Un tuple de retour s’écrit `fn paire() (i64, bool)`.

Dans `Container<T>`, `fn doubler(self: &Container<i64>) i64` réserve la méthode à
la spécialisation `Container<i64>`. Le corps est vérifié dans cette spécialisation,
sans nouveau paramètre générique ni résolution dynamique. `&mut` permet de muter ;
un receveur par valeur transfère sa responsabilité de nettoyage. Le type du
receveur doit être le type englobant. `&self` et `&mut self` restent disponibles.

Le compilateur abaisse ces méthodes vers sa représentation interne existante.
Les règles de possession, d’emprunt, de visibilité et de destruction ne changent
pas. Les diagnostics conservent leurs liens vers le fichier source.

Les anciens blocs `impl` et les retours fléchés restent acceptés pour amorcer le
compilateur et lire ses recettes internes. La STD, les exemples et la grammaire
de référence utilisent la nouvelle syntaxe. Les anciens rapports ne constituent
pas une référence de syntaxe actuelle.
