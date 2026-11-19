[English](MODULES.md)

# Packages et modules

Le projet déclare son nom dans `package.toml` à la racine. Ses sources sont
dans `src/`. La fonction `main`, synchrone, se trouve dans `src/main.crb`.
L’extension pourra évoluer indépendamment des chemins d’import.

Chaque dossier source forme un module. Tous les fichiers directement dans
le dossier contribuent au même module. Le nom déclaré par le manifeste et
les dossiers déterminent le chemin d’un composant. Déplacer une déclaration
entre deux fichiers du même dossier conserve son chemin.

Une déclaration est privée à son module par défaut. `pub` la rend accessible
aux autres modules. Les imports sont propres au fichier. Ils peuvent désigner
un module ou un composant public. Le dernier segment donne le nom local,
sauf si `as` introduit un alias. Un groupe équivaut à plusieurs imports qui
partagent le même préfixe.

```rust
use server::http::{parse_request, health_status as health};
use server::config as configuration;
```

Le compilateur refuse les collisions sur les noms locaux après application
des alias, ainsi qu’un import en conflit avec une déclaration du module
courant. Un chemin qui désigne à la fois un module et un composant est ambigu.

Une dépendance locale utilise `path`, relatif au manifeste qui la déclare.
Une dépendance Git utilise `git` et `rev`. Le compilateur récupère le commit
exact dans un répertoire temporaire. `rev` doit être un identifiant de commit
complet. Un chemin vers un dépôt Git local est aussi accepté.

Le nom de la dépendance doit correspondre au nom déclaré par son package.
Chaque package peut accéder à ses dépendances directes. Le chargeur refuse
les cycles et deux sources pour un même nom de package. Les chemins locaux
depuis un checkout Git doivent rester dans ce checkout.

`std` est un nom réservé. Le compilateur d’amorçage Rust embarque les sources sous
`stdlib/src/` lors de sa construction. Chaque package peut importer ses
composants publics, par exemple `use std::num::min_i64;`. La bibliothèque
standard ne dépend d’aucun package Corbo.

Sur macOS ARM64, `corboc build PACKAGE -o OUTPUT` résout aussi ces
dépendances. Il utilise la copie installée de `std` et le binaire `git`
du `PATH`. Le lecteur de manifestes Corbo accepte le nom dans
`[package]` et les tables en ligne avec des clés nues et des chaînes
sans échappement sur une seule ligne. Le graphe est limité à 64 packages
en plus de `std`.

## Sélection de la cible

L’annotation `#(if: condition { ... })` sélectionne des imports et des
déclarations. La condition et les éléments sélectionnés figurent dans
les parenthèses. Le compilateur fournit les valeurs `target.os`, `target.family`
et `target.arch` à la compilation. Elles décrivent la cible du binaire
produit, y compris en compilation croisée.

Le compilateur évalue la condition avant de résoudre les imports. Si elle
est vraie, les éléments entrent dans la portée englobante à l’emplacement
de l’annotation. Les accolades ne créent aucune portée. Si elle est fausse, les
éléments sont écartés de la résolution des noms et des contrôles de collision.

```rust
#(if: target.family == "unix" {
    use std::sys::unix::FileHandle;
})

#(if: target.os == "windows" {
    use std::sys::win::FileHandle;
})
```

La condition compare une propriété à une chaîne avec `==`. Le frontend
utilise la cible hôte par défaut. Pour sélectionner une autre cible,
passez un triplet à `check` ou `emit-c`, par exemple :

```sh
corbo-frontend emit-c . --target x86_64-unknown-linux-gnu > program.c
```

Cette option sélectionne les éléments source. Pour produire le binaire,
utilisez une chaîne de compilation C pour la cible choisie.

Une condition de cible peut combiner plusieurs comparaisons avec `&&` et `||`. La conjonction est prioritaire.
Sur les cibles de largeur connue, `target.pointer_width` vaut `"32"` ou
`"64"`. La bibliothèque standard combine l’OS, l’architecture et la
largeur des pointeurs pour sélectionner l’ABI de `std::io::File`.
