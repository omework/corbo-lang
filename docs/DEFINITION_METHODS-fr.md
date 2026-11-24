[English](DEFINITION_METHODS.md)

# Méthodes dans les définitions et receveurs explicites

Les méthodes et constantes associées sont déclarées dans la définition du
`struct` ou de l’`enum`, sans ordre imposé entre les membres. Chaque champ et chaque
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

## Annotations dans les définitions

Dans une struct ou une enum, les annotations gardent leur cible et leur sens.
Elles précèdent `pub`/`async` et la déclaration concernée. `type` s'applique aux
méthodes et aux fonctions associées génériques ; `branch` et `lock` gardent leurs
contrats d'effets. `configurable` marque une constante associée, ciblée par son
nom qualifié (`Settings::LIMIT`). Un override lexical spécialise le type et ses
méthodes puis restaure l'environnement précédent à la sortie du bloc.
Les sélections `if`/`endif` sont effectuées avant la résolution des noms.
Les annotations de bloc restent devant des blocs dans les corps des méthodes.
Les annotations d'objet restent devant la déclaration du type. Une annotation
sur une cible incompatible est refusée. Voir les exemples dans la
[référence anglaise](DEFINITION_METHODS.md#annotations-inside-definitions).

## Ordre des membres et bornes de tableau

Les champs/variantes, constantes associées et méthodes peuvent être intercalés.
Une borne de tableau
fixe ou de répétition peut utiliser `Type::CONSTANTE` ou `Self::CONSTANTE` dans
son type propriétaire. La résolution utilise l'environnement de configuration
lexical actif ; une valeur runtime ne devient pas une borne fixe.
