# Corbo

**Un langage de programmation système expérimental fondé sur l’intention du développeur, une gestion prévisible de la mémoire et la vérification statique.**

[English](README.md)

Langage, STD et runtime : [omework/corbo-lang](https://github.com/omework/corbo-lang).
Compilateur : [omework/corboc](https://github.com/omework/corboc).

<a id="contents"></a>

## Sommaire

- [Comment la philosophie de Corbo a évolué](#how-corbos-philosophy-evolved)
- [Les budgets mémoire en pratique](#memory-budgets-in-practice)
- [Démarrage](#getting-started)
- [Exemples du langage et de la STD](#language-and-std-examples)
- [Explorer la STD](#explore-the-std)
- [Organisation des sources et frontière du runtime](#source-layout-and-runtime-boundary)
- [Construire le compilateur à partir des sources](#build-the-compiler-from-source)
- [Documentation et état de la validation](#documentation-and-validation-status)
- [Références des API : STD](docs/STDLIB.md) · [runtime](docs/RUNTIME.md)

<a id="philosophy"></a>

<a id="philosophie"></a>

<a id="how-corbos-philosophy-evolved"></a>

## Comment la philosophie de Corbo a évolué

Corbo est né d’une expérimentation : concevoir un langage de programmation système principalement destiné au code généré par l’IA.

L’idée initiale était simple : **l’intention du développeur est une ressource que le compilateur devrait exploiter.**

Corbo privilégie les contraintes explicites et vérifiables par une machine plutôt que la facilité d’écriture, tout en cherchant à rendre le code produit compréhensible et auditable par des humains.

La gestion de la mémoire est devenue l’un des axes centraux de cette expérimentation.

**La mémoire est finie. Nous le savons, mais nous écrivons souvent nos programmes comme si elle était illimitée.**

Corbo explore ce qui se passe lorsque les programmes sont conçus autour de capacités mémoire explicites, de durées de vie prévisibles et de stratégies d’allocation bornées, sans dépendre d’un allocateur généraliste sur le tas.

Au départ, il s’agissait surtout d’une question de faisabilité : quelle quantité de logiciels pouvait-on raisonnablement construire sous ces contraintes ?

À mesure que le langage et sa bibliothèque standard se développaient, une autre possibilité a commencé à se dessiner.

**Et si l’IA pouvait exploiter les contraintes d’un système entier pour aider à déterminer comment ce système devrait être implémenté ?**

Les exigences métier, les limites de taille des données échangées, les schémas de communication, les limites de concurrence et les budgets de ressources pourraient guider non seulement les allocations individuelles, mais aussi des architectures logicielles entières.

Ces informations n’apportent pas toutes les mêmes garanties. Une charge attendue est une hypothèse ; une capacité effectivement imposée est une limite. Cette distinction compte : une implémentation peut être optimisée autour d’hypothèses, tandis que ses garanties doivent reposer sur des contraintes que le programme fait réellement respecter.

Des agents IA pourraient exploiter ces informations pour générer des implémentations spécialisées adaptées à des exigences connues. Des contrats explicites permettraient d’examiner ces choix, tandis que le compilateur vérifierait les propriétés qu’il peut établir et que les contrôles à l’exécution feraient respecter les limites qui ne peuvent pas être résolues statiquement.

Ce n’était pas la motivation initiale du modèle mémoire de Corbo. Cette idée est apparue au fil de l’expérimentation.

Elle reste une hypothèse, pas un résultat établi.

Une génération de code moins coûteuse ne supprime pas le coût de la validation, de la maintenance ou de la compréhension d’un système. Corbo cherche à déterminer si des contraintes explicites et la vérification par le compilateur peuvent rendre la spécialisation pratique sans rendre ses conséquences plus difficiles à évaluer.

Corbo tente d’explorer cette hypothèse : **que devient-il possible lorsque la génération de logiciels devient moins coûteuse, que les contraintes sont explicites et que la vérification fait partie du modèle de programmation ?**

<a id="memory-budgets-in-practice"></a>

## Les budgets mémoire en pratique

<a id="an-implicit-memory-budget-in-rust"></a>

### Un budget mémoire implicite en Rust

Ce programme Rust collecte 1 000 entiers et affiche le nombre d’éléments stockés :

<!-- corpus: rust-only -->
```rust
fn main() {
    let count: i64 = 1000;
    let mut numbers = Vec::new();
    for number in 0..count {
        numbers.push(number);
    }
    println!("{}", numbers.len());
}
```

Le vecteur grandit selon les besoins. Son budget de croissance et la conduite à tenir en cas de dépassement restent implicites dans ce programme. Rust permet au développeur d’ajouter des limites ; cet exemple n’en exprime aucune.

<a id="an-explicit-growth-budget-in-corbo"></a>

### Un budget de croissance explicite en Corbo

La même collection peut exprimer son budget de stockage directement dans le code. Ici, `count` vaut `1000` pour que les deux exemples restent exécutables ; sa valeur peut provenir d’une entrée sans modifier le budget déclaré :

<!-- example: budget -->
```rust
use std::Vector;

fn main() {
    let count: i64 = 1000;
    let mut vectors = Pool<Vector<i64>>::new(1);

    #(stack_region: max_size=64K, count=1) {
        let mut numbers = vectors.new();
        let mut number: i64 = 0;
        while number < count {
            numbers.push(copy(number));
            number += 1;
        }
        print(numbers.len());
    }
}
```

Sortie : `1000`. [Paquet complet](examples/features/budget/).

- `Pool<Vector<i64>>::new(1)` fournit un slot de vecteur. Le `1` compte les objets vecteurs, pas leurs éléments.
- `#(stack_region: max_size=64K, count=1)` fixe la taille d’une région à 64 Kio et réserve une région pour ce scope. Les données grandissantes du vecteur utilisent cette région.
- Un `i64` occupe huit octets : ce budget permet donc de stocker au plus 8 192 éléments. Augmenter le nombre d’entrées n’augmente pas la limite de la région.
- Avec `push`, dépasser cette limite arrête le programme avec un diagnostic. La sortie du scope détruit le vecteur avant de rendre le stockage de sa région réutilisable.

La limite porte sur le stockage des éléments ; le descripteur, le pool et les métadonnées du runtime disposent de leur propre stockage. Il ne s’agit pas d’une limite sur la mémoire totale du processus.

**L’annotation explicite est actuellement facultative.** Lorsqu’une taille est omise, Corbo utilise une borne déduite statiquement si elle est disponible, puis sa politique de régions configurée ou par défaut. Une valeur grandissante reste soumise à une limite de région finie. Cet exemple montre comment le développeur indique une limite précise directement dans le code.

<a id="getting-started"></a>

## Démarrage

Il faut un `corboc` compatible et une chaîne de compilation C11 sur la machine hôte. Pour construire le compilateur, suivez les [instructions de construction à partir des sources](#build-the-compiler-from-source) ci-dessous ; le compilateur actuel nécessite un compilateur auto-hébergé de départ déjà compatible.

Clonez le dépôt du langage, puis construisez et lancez le premier exemple :

```sh
git clone git@github.com:omework/corbo-lang.git
cd corbo-lang
```

Depuis ce dépôt du langage :

```sh
cd examples/features/hello
corboc build
./build/feature_demo
```

Il affiche `42`. Pour créer votre propre paquet, indiquez son nom dans `package.toml` :

<!-- example-file: modules/package.toml -->
```toml
[package]
name="feature_demo"
```

Enregistrez un programme complet dans `src/main.crb`, comme dans le [premier exemple](#hello). Depuis le répertoire contenant `package.toml`, lancez :

```sh
corboc build
./build/feature_demo
```

Le compilateur crée `build/` et nomme le binaire d’après `[package].name`. Pour choisir un autre nom de binaire, ajoutez cette section facultative à `package.toml` :

```toml
[bin]
name = "my-program"
```

Le fichier produit devient `build/my-program` ; omettre `[bin]` ou `[bin].name` conserve le nom du paquet. Ce nom est un nom de fichier, pas un chemin : les lettres, chiffres, `_`, `-` et `.` sont acceptés, avec au moins une lettre, un chiffre ou un `_`.

Un chemin de paquet explicite conserve la sortie par défaut dans ce paquet. `-o` remplace le nom configuré et écrit au chemin indiqué, relatif au répertoire courant :

```sh
corboc build ./my-package
corboc build -o my-program
corboc build ./my-package -o my-program
```

La convention de nommage ajoute `.exe` sous Windows. Le pilote natif de `build` prend actuellement en charge macOS ARM64 ; les autres pilotes natifs restent à implémenter. Le compilateur installé retrouve sa STD correspondante dans `share/corbo/stdlib/src`. Les [ressources pour éditeurs](ide/README.md) fournissent la coloration des fichiers `.crb` dans Vim, Neovim et VS Code.

<a id="language-and-std-examples"></a>

## Exemples du langage et de la STD

Commencez par les bases, puis suivez les valeurs à travers les emprunts, le stockage, la composition et l’exécution concurrente. Chaque programme est complet et possède un paquet dans [`examples/features/`](examples/features/README.md), y compris l’[exemple de budget mémoire](#an-explicit-growth-budget-in-corbo) ci-dessus. Les exemples sont synchronisés avec leurs sources et validés avec `corboc` ; l’[état de la validation](#documentation-and-validation-status) en précise la portée.

- [Bases](#basics) : [Point d’entrée synchrone](#hello), [Primitives et opérateurs vérifiés](#numbers), [Expressions et contrôle du flux](#control), [Fonctions, tuples et déstructuration](#tuples), [Structures, constantes et modes du receveur](#methods), [Énumérations et filtrage par motifs](#enums), [Result, Option et propagation anticipée](#errors).
- [Mémoire et durées de vie](#memory-and-lifetimes) : [Moves et copies explicites](#moves), [Emprunts partagés et réemprunts mutables](#borrows), [Tableaux fixes, répétition structurelle et tranches](#arrays), [Pools de capacité fixe et handles d’allocation](#pools), [Receveurs et placement entre scopes](#placement), [Destruction avant libération du stockage](#destruction), [Budgets de datastack, régions locales et restitution des pages](#regions).
- [Collections et pipelines](#collections-and-pipelines) : [Vecteurs et extraction](#vector), [Recherche, remplacement et suppression dans une HashMap](#map), [Texte UTF-8 et octets détenus par l’appelant](#text), [Chaînes inline bornées](#bounded-text), [Closures et passage explicite des fonctions](#closures), [Pipelines d’itérateurs de la STD](#iter).
- [Code générique et paquets](#generic-code-and-packages) : [Contrats sur les structures génériques](#generic), [Contrats de type structurels statiques](#contracts), [Paquets, modules, visibilité et alias](#modules), [Compilation conditionnelle](#target).
- [Asynchrone et threads](#async-and-threads) : [Futures, suspension et branches d’exécution](#async), [Threads natifs et emprunts capturés](#threads), [Travail bloquant depuis un contexte asynchrone](#blocking).
- [La STD en pratique](#std-in-practice) : [Fichiers, erreurs et tampons fournis par l’appelant](#file), [Entrées-sorties tamponnées et contrats structurels](#buffered), [Points de terminaison réseau typés et datagrammes](#network), [Hachage et encodage avec une sortie bornée](#encoding), [Binaire et endianness](#binary), [Temps monotone](#time), [Timers async](#async-time), [Compression avec un espace de travail explicite](#compression).
- [Interopérabilité native](#native-interop) : [C non vérifié, opérandes typées et assembleur natif](#foreign).

<a id="basics"></a>

### Bases

<a id="hello"></a>

<a id="a-synchronous-entry-point"></a>

#### Un point d’entrée synchrone

`main` est synchrone. Construisez un paquet avec `package.toml` et `src/main.crb`.

<!-- example: hello -->
```rust
fn main() {
    print(42);
}
```

Sortie : `42`. [Paquet complet](examples/features/hello/).

<a id="numbers"></a>

<a id="primitives-and-checked-operators"></a>

#### Primitives et opérateurs vérifiés

Les entiers ont le type `i64` par défaut, les littéraux décimaux à virgule flottante le type `f64`. Les variables utilisées dans une opération arithmétique doivent avoir des types compatibles. `as` autorise les conversions exactes pour toutes les valeurs du type source ; `try_from` peut échouer. L’arithmétique entière, les décalages et l’indexation conservent leurs contrôles.

<!-- example: numbers -->
```rust
fn main() {
    let byte: u8 = 21;
    let wide: u64 = byte as u64;
    let ratio: f32 = 1.5;
    let mut flags: u32 = 1;
    flags <<= 3;
    flags |= 2;
    print(wide * 2);
    print(flags & 8);
    print(ratio == 1.5);
}
```

Sortie : `42, 8, true`. [Paquet complet](examples/features/numbers/).

<a id="control"></a>

<a id="expressions-and-control-flow"></a>

#### Expressions et contrôle du flux

Les blocs, `if`, `match` et `loop` peuvent produire des valeurs. Le point-virgule distingue une instruction d’une valeur finale de bloc. `continue` et `break` nettoient les scopes dont ils sortent.

<!-- example: control -->
```rust
fn main() {
    let selected = if true { 40 } else { 0 };
    let mut total: i64 = 0;
    let mut index: i64 = 0;
    while index < 4 {
        index += 1;
        if index == 2 { continue; }
        total += index;
    }
    let result = loop {
        break selected + 2;
    };
    print(total);
    print(result);
}
```

Sortie : `8, 42`. [Paquet complet](examples/features/control/).

<a id="tuples"></a>

<a id="functions-tuples-and-destructuring"></a>

#### Fonctions, tuples et déstructuration

Les fonctions peuvent retourner des tuples de deux valeurs ou plus. Les types sont inférés par position lorsqu’aucune annotation de type n’est fournie sur la liaison.

<!-- example: tuples -->
```rust
fn measurements(value: i64) -> (i64, i64, bool) {
    (copy(value) + 1, copy(value) * 2, value > 0)
}

fn main() {
    let (next, doubled, positive) = measurements(21);
    print(next);
    print(doubled);
    print(positive);
}
```

Sortie : `22, 42, true`. [Paquet complet](examples/features/tuples/).

<a id="methods"></a>

<a id="structs-constants-and-receiver-modes"></a>

#### Structures, constantes et modes du receveur

La signature du receveur indique si une méthode l’emprunte, l’emprunte de manière mutable ou le consomme. Les constantes associées utilisent `Type::NAME`.

<!-- example: methods -->
```rust
struct Counter {
    value: i64
}

impl Counter {
    const STEP: i64 = 1;

    fn increment(&mut self) {
        let value = &mut (*self).value;
        *value += Counter::STEP;
    }

    fn finish(self: Counter) -> i64 {
        self.value
    }
}

fn main() {
    let mut counter = Counter { value: 41 };
    counter.increment();
    print(counter.finish());
}
```

Sortie : `42`. [Paquet complet](examples/features/methods/).

<a id="enums"></a>

<a id="enums-and-pattern-matching"></a>

#### Énumérations et filtrage par motifs

Les variantes peuvent contenir des données nommées ou positionnelles. Un `match` par valeur transfère les données de la variante sélectionnée selon leurs règles habituelles de possession.

<!-- example: enums -->
```rust
enum Reading {
    Value(i64),
    Missing
}

fn main() {
    let reading = Reading.Value(42);
    match reading {
        Reading.Value(value) => { print(value); },
        Reading.Missing => { print(0); },
    }
}
```

Sortie : `42`. [Paquet complet](examples/features/enums/).

<a id="errors"></a>

<a id="result-option-and-early-propagation"></a>

#### Result, Option et propagation anticipée

`?` retourne l’échec ou l’absence depuis la fonction englobante. Des erreurs de `Result` de types différents nécessitent un `Outer::from(Inner) -> Outer` résolu statiquement ; aucune conversion arbitraire implicite n’est effectuée.

<!-- example: errors -->
```rust
fn checked(value: i64) -> Result<i64, bool> {
    if value < 0 { return Err(false); }
    Ok(value)
}

fn calculate() -> Result<i64, bool> {
    let value = checked(21)?;
    Ok(value * 2)
}

fn main() {
    match calculate() {
        Ok(value) => { print(value); },
        Err(error) => { print(error); },
    }
}
```

Sortie : `42`. [Paquet complet](examples/features/errors/).


<a id="memory-and-lifetimes"></a>

### Mémoire et durées de vie

<a id="moves"></a>

<a id="moves-and-explicit-copies"></a>

#### Moves et copies explicites

Une affectation transfère une valeur. Appelez `copy` explicitement pour conserver la source d’une valeur primitive. Un move transfère la responsabilité du nettoyage ; il ne demande pas le déplacement de l’allocation en mémoire.

<!-- example: moves -->
```rust
struct Message {
    value: i64
}

fn consume(message: Message) {
    print(message.value);
}

fn main() {
    let original: i64 = 21;
    let duplicate = copy(original);
    print(original + duplicate);
    let message = Message { value: 7 };
    let received = message;
    consume(received);
}
```

Sortie : `42, 7`. [Paquet complet](examples/features/moves/).

<a id="borrows"></a>

<a id="shared-borrows-and-mutable-reborrows"></a>

#### Emprunts partagés et réemprunts mutables

Les références ne transfèrent pas la responsabilité du nettoyage. Leurs cibles doivent rester valides, et les emprunts mutables excluent les accès incompatibles jusqu’à leur dernière utilisation.

<!-- example: borrows -->
```rust
fn increment(value: &mut i64) {
    *value += 1;
}

fn show(value: &i64) {
    print(*value);
}

fn main() {
    let mut number: i64 = 41;
    increment(&mut number);
    show(&number);
    number += 1;
    print(number);
}
```

Sortie : `42, 43`. [Paquet complet](examples/features/borrows/).

<a id="arrays"></a>

<a id="fixed-arrays-structural-repetition-and-slices"></a>

#### Tableaux fixes, répétition structurelle et tranches

Le type d’un tableau contient son nombre d’éléments. Une tranche empruntée contient une adresse et une longueur. La répétition évalue l’initialiseur une seule fois et exige une valeur réplicable structurellement ; les tranches conservent les contrôles de bornes et de durée de vie.

<!-- example: arrays -->
```rust
struct Token {
    kind: u8
}

fn sum(values: &[i64]) -> i64 {
    let mut index: usize = 0;
    let mut result: i64 = 0;
    while index < values.len() {
        result += values[index];
        index += 1;
    }
    result
}

fn main() {
    let mut values: [i64; 3] = [10, 20, 30];
    values[1] = 2;
    let middle = &mut values[1];
    *middle += 1;
    print(sum(&values[..]));
    let tokens: [Token; 2] = [Token { kind: 7 }; 2];
    print(tokens[1].kind);
}
```

Sortie : `43, 7`. [Paquet complet](examples/features/arrays/).

<a id="pools"></a>

<a id="fixed-capacity-pools-and-allocation-handles"></a>

#### Pools de capacité fixe et handles d’allocation

`Pool<T>::new(n)` réserve des slots fixes. `new` retourne `A<T>` ; le pool doit survivre à cette allocation. Détruire une allocation vivante libère son slot après son nettoyage.

<!-- example: pools -->
```rust
fn main() {
    let mut numbers = Pool<i64>::new(2);
    let first: A<i64> = numbers.new(10);
    let second = numbers.new(20);
    print(*first);
    drop(first);
    let third = numbers.new(30);
    print(*second);
    print(*third);
}
```

Sortie : `10, 20, 30`. [Paquet complet](examples/features/pools/).

##### Allocation récupérable dans un pool

`Pool<T>::new(capacity)` crée un pool de capacité fixe. `pool.new(...)` arrête
le programme si aucun slot n'est disponible. `pool.try(...)` renvoie
`Result<A<T>, PoolError>`, avec `PoolError.Full` en cas de saturation. Les mêmes
formes d'initialisation sont acceptées. L'argument est déplacé même en cas
d'échec : sa valeur est détruite avant le retour de l'erreur.

Voir [l'API des pools](docs/COLLECTIONS_API.md).

<a id="placement"></a>

<a id="receivers-and-placement-across-scopes"></a>

#### Receveurs et placement entre scopes

Le résultat d’un bloc possède un receveur explicite. Le plan de placement post-AST suit les transferts jusqu’à leur destination finale tout en conservant des adresses d’allocation stables.

<!-- example: placement -->
```rust
fn main() {
    let mut numbers = Pool<i64>::new(1);
    let received = {
        let local = numbers.new(42);
        local
    };
    print(*received);
}
```

Sortie : `42`. [Paquet complet](examples/features/placement/).

<a id="destruction"></a>

<a id="destruction-before-storage-release"></a>

#### Destruction avant libération du stockage

`drop(value)` et la sortie de scope appellent `drop(&mut self)` une seule fois, avant le nettoyage des champs. Déplacer la valeur change qui effectue ce nettoyage. Les types sans destructeur personnalisé utilisent le destructeur vide par défaut.

<!-- example: destruction -->
```rust
struct Item {
    number: i64
}

impl Item {
    fn drop(&mut self) {
        print((*self).number);
    }
}

fn main() {
    let first = Item { number: 7 };
    let received = first;
    print(1);
    drop(received);
    { let scoped = Item { number: 9 }; }
}
```

Sortie : `1, 7, 9`. [Paquet complet](examples/features/destruction/).

<a id="regions"></a>

<a id="datastack-budgets-local-regions-and-page-reclamation"></a>

#### Budgets de datastack, régions locales et restitution des pages

L’annotation globale de datastack et ses propriétés sont facultatives. `stack_region` fournit un budget local pour les données grandissantes. `free_pages` demande au système de récupérer les pages entières inutilisées après le nettoyage, une opération distincte du déplacement d’un curseur.

<!-- example: regions -->
```rust
#(datastack: size=4M, region_stack_size=4M, region_size=64K)
use std::Vector;

fn main() {
    let mut vectors = Pool<Vector<i64>>::new(1);
    #(stack_region: max_size=64K, count=1) #(free_pages) {
        let mut values = vectors.new();
        let mut number: i64 = 0;
        while number < 3 {
            values.push(copy(number));
            number += 1;
        }
        print(values.len());
    }
}
```

Sortie : `3`. [Paquet complet](examples/features/regions/).


<a id="collections-and-pipelines"></a>

### Collections et pipelines

<a id="vector"></a>

<a id="vectors-and-extraction"></a>

#### Vecteurs et extraction

Le descripteur d’un vecteur a une taille fixe ; ses données contiguës grandissent dans le budget de sa région. Une insertion déplace un élément dans le vecteur. Une extraction le transfère au receveur.

<!-- example: vector -->
```rust
use std::Vector;

fn main() {
    let mut vectors = Pool<Vector<i64>>::new(1);
    let mut values = vectors.new();
    values.push(10);
    values.push(20);
    print(values[0]);
    match values.pop() {
        Some(value) => { print(value); },
        None => { print(0); },
    }
    print(values.len());
}
```

Sortie : `10, 20, 1`. [Paquet complet](examples/features/vector/).

<a id="map"></a>

<a id="hashmap-lookup-replacement-and-removal"></a>

#### Recherche, remplacement et suppression dans une HashMap

Les HashMap acceptent des clés entières ou booléennes. L’insertion déplace sa clé et sa valeur ; la recherche emprunte sa clé. Les valeurs restantes sont détruites avec la HashMap, tandis qu’une valeur extraite appartient à son receveur.

<!-- example: map -->
```rust
use std::HashMap;

fn main() {
    let mut values = HashMap<i64, i64>::new();
    let key: i64 = 7;
    drop(values.insert(copy(key), 42));
    match values.get(&key) {
        Some(value) => { print(*value); },
        None => { print(0); },
    }
    match values.remove(&key) {
        Some(value) => { print(value); },
        None => { print(0); },
    }
}
```

Sortie : `42, 42`. [Paquet complet](examples/features/map/).

<a id="text"></a>

<a id="utf-8-text-and-caller-owned-bytes"></a>

#### Texte UTF-8 et octets détenus par l’appelant

`String` détient des octets UTF-8 stockés dans une région ; un littéral fournit une vue statique `&str`. La longueur en octets diffère du nombre de caractères. Convertissez explicitement en tranche d’octets avec `as_bytes()`. `String` et `&str` proposent tous deux `split(separator)` : l’itérateur produit des morceaux empruntés de type `&str`, en conservant les morceaux vides sans allouer de chaînes.

`String<N>` conserve au contraire au plus `N` octets UTF-8 inline, avec une borne connue à la compilation. Une construction ou un remplacement trop long renvoie une erreur sans tronquer le texte. Voir les [API des chaînes bornées](docs/UTF8_STRINGS-fr.md).

<!-- example: text -->
```rust
use std::String;

fn main() {
    let mut strings = Pool<String>::new(1);
    let mut text = strings.new();
    text.push_str("été,soleil,");
    print(text.byte_len());

    let literal = "ok";
    let bytes = literal.as_bytes();
    print(bytes.len());

    // Each item is a borrowed &str; no String is allocated for a piece.
    let mut pieces = text.split(",");
    loop {
        match pieces.next() {
            Some(piece) => { print(piece.byte_len()); },
            None => { break; },
        }
    }
}
```

Sortie : `13, 2, 5, 6, 0`. [Paquet complet](examples/features/text/).

<a id="bounded-text"></a>

#### Chaînes UTF-8 inline avec un maximum en octets connu à la compilation

`String<N>` conserve ses octets UTF-8 inline. Dépasser la borne renvoie une erreur avant toute modification. Ici, deux caractères `é` occupent exactement quatre octets.

<!-- example: bounded_text -->
```rust
use std::String;

fn main() {
    // Two UTF-8 characters occupy four bytes, exactly our inline budget.
    let mut name = match String<4>::try_from("éé") {
        Ok(value) => { value },
        Err(error) => { drop(error); return; },
    };

    print(name.capacity());
    print(name.len());

    // Five bytes cannot fit. The previous content stays intact.
    match name.set("hello") {
        Ok(()) => { print(false); },
        Err(error) => { drop(error); print(true); },
    }

    print(name.len());
}
```

Sortie: `4, 4, true, 4`. [Paquet complet](examples/features/bounded_text/).

<a id="closures"></a>

<a id="closures-and-explicit-callable-passing"></a>

#### Closures et passage explicite des fonctions

Une closure est un objet concret contenant ses captures. Les paramètres sont typés et les accolades obligatoires. `fn(...) -> R`, `&fn(...) -> R` et `&mut fn(...) -> R` distinguent le passage par valeur de l’emprunt. Sans `move`, les captures de primitives et de références partagées sont copiées à la création. Un `move` explicite transfère les liaisons capturées ; les références conservent leurs dépendances vers leurs cibles.

<!-- example: closures -->
```rust
fn apply(f: fn(i64) -> i64, value: i64) -> i64 {
    f(value)
}

fn inspect(f: &fn(i64) -> i64, value: i64) -> i64 {
    f(value)
}

fn advance(f: &mut fn() -> i64) -> i64 {
    f()
}

fn main() {
    let offset: i64 = 2;
    let c = |value: i64| { value + offset };

    print(c(40));
    print(inspect(&c, 8));
    print(apply(c, 18));
    print(offset);

    let mut count: i64 = 0;
    let mut next = move || { count += 1; count };

    print(advance(&mut next));
    print(next());
}
```

Sortie : `42, 10, 20, 2, 1, 2`. [Paquet complet](examples/features/closures/).

<a id="iter"></a>

<a id="std-iterator-pipelines"></a>

#### Pipelines d’itérateurs de la STD

Seul `Iter` emprunte la source. Chaque adaptateur possède le maillon précédent. `collect(&mut destination)` consomme la chaîne et déplace ses résultats vers un stockage choisi par l’appelant.

<!-- example: iter -->
```rust
use std::iter::iter;

struct Counter {
    position: i64,
    end: i64
}

impl Counter {
    fn next(&mut self) -> Option<i64> {
        let value = (*self).position;
        if copy(value) >= (*self).end { return None; }
        let position = &mut (*self).position;
        *position = copy(value) + 1;
        Some(value)
    }
}

fn main() {
    let mut counter = Counter { position: 1, end: 7 };
    let mut storage = Pool<Vector<i64>>::new(1);
    let mut destination = storage.new();
    iter(&mut counter)
        .filter(|item: &i64| { *item % 2 == 0 })
        .map(|item: i64| { item * 10 })
        .reduce(|acc: i64, item: i64| { acc + item })
        .collect(&mut destination);
    print(destination.len());
    print(destination[0]);
    print(counter.position);
}
```

Sortie : `1, 120, 7`. [Paquet complet](examples/features/iter/).


<a id="generic-code-and-packages"></a>

### Code générique et paquets

<a id="generic"></a>

<a id="contracts-on-generic-structs"></a>

#### Contrats sur les structures génériques

Les paramètres de type et leurs contraintes s’appliquent également aux structures. Une instanciation concrète conserve les obligations habituelles de possession et d’emprunt de ses champs.

<!-- example: generic -->
```rust
#(type: T)
pub struct Holder<T> {
    value: T
}

fn main() {
    let holder: Holder<i64> = Holder { value: 42 };
    print(holder.value);
}
```

Sortie : `42`. [Paquet complet](examples/features/generic/).

<a id="contracts"></a>

<a id="static-structural-type-contracts"></a>

#### Contrats de type structurels statiques

Un contrat `with` exige les méthodes listées et autorise des méthodes supplémentaires. Le compilateur résout statiquement l’implémentation concrète ; aucun objet de trait ni dispatch dynamique n’est introduit.

<!-- example: contracts -->
```rust
#(type: V)
struct Boxed<V> {
    value: V
}

impl Boxed<V> {
    fn new(value: V) -> Boxed<V> {
        Boxed { value: value }
    }

    fn get(&self) -> V {
        (*self).value
    }
}

#(type: V)
#(type: S<V> with {
    fn get(&self) -> V;
})
struct Reader<S, V> {
    source: S
}

impl Reader<S, V> {
    fn new(source: S) -> Reader<S, V> {
        Reader { source: source }
    }

    fn get(&self) -> V {
        let source = &(*self).source;
        source.get()
    }
}

fn main() {
    let reader = Reader::new(Boxed::new(42));
    print(reader.get());
}
```

Sortie : `42`. [Paquet complet](examples/features/contracts/).

<a id="modules"></a>

<a id="packages-modules-visibility-and-aliases"></a>

#### Paquets, modules, visibilité et alias

Le nom d’un paquet est défini dans `package.toml`. Les fichiers sous `src` fournissent les composants. `pub`, les imports `use` groupés et `as` contrôlent l’accès et les noms locaux ; les dépendances peuvent être fixées à une révision précise dans les métadonnées du paquet.

<!-- example: modules -->
```rust
use feature_demo::math::{answer as result, twice};

fn main() {
    print(result());
    print(twice(21));
}
```

Sortie : `42, 42`. [Paquet complet](examples/features/modules/).

Le composant importé est `src/math/numbers.crb` :

<!-- example-file: modules/src/math/numbers.crb -->
```rust
pub fn answer() -> i64 {
    42
}

pub fn twice(value: i64) -> i64 {
    value * 2
}
```

Le répertoire ajoute `math` au chemin d’import ; le fichier du composant déclare ses fonctions publiques. Le [guide des modules et des dépendances](docs/MODULES.md) décrit les dépendances `path`, Git et les révisions immuables.

<a id="target"></a>

<a id="conditional-compilation"></a>

#### Compilation conditionnelle

La sélection de la cible précède la résolution des imports. Les branches exclues ne peuvent introduire ni import indisponible ni collision. Le `endif` correspondant termine la sélection ; il ne crée pas de scope à l’exécution.

<!-- example: target -->
```rust
#(if: target.family == "unix")
fn answer() -> i64 {
    42
}

#(endif)
#(if: target.family == "windows")
fn answer() -> i64 {
    42
}

#(endif)
fn main() {
    print(answer());
}
```

Sortie : `42`. [Paquet complet](examples/features/target/).


<a id="async-and-threads"></a>

### Asynchrone et threads

<a id="async"></a>

<a id="futures-suspension-and-execution-branches"></a>

#### Futures, suspension et branches d’exécution

Appeler une fonction asynchrone crée une Future inactive et capture immédiatement ses arguments. `yield;` suspend l’exécution de manière coopérative ; `.await` attend sans bloquer un worker de polling. Le `main` synchrone lance une exécution et attend son résultat par l’intermédiaire de son handle.

<!-- example: async -->
```rust
async fn twice(value: i64) -> i64 {
    yield;
    value * 2
}

async fn calculate() -> i64 {
    twice(21).await
}

fn main() {
    let execution = runtime::spawn(calculate());
    match execution.join() {
        Ok(value) => { print(value); },
        Err(error) => { drop(error); print(0); },
    }
}
```

Sortie : `42`. [Paquet complet](examples/features/async/).

<a id="threads"></a>

<a id="native-threads-and-captured-loans"></a>

#### Threads natifs et emprunts capturés

Une exécution native reçoit les captures de son bloc. La cible d’une référence capturée doit rester valide pendant son utilisation ; cet exemple effectue un `join` avant d’accéder à nouveau à la cible.

<!-- example: threads -->
```rust
fn main() {
    let mut number: i64 = 41;
    let view = &mut number;
    let execution = runtime::thread({
        move view;
        *view += 1;
    });
    drop(execution.join());
    print(number);
}
```

Sortie : `42`. [Paquet complet](examples/features/threads/).

<a id="blocking"></a>

<a id="blocking-work-from-an-async-context"></a>

#### Travail bloquant depuis un contexte asynchrone

`spawn_blocking` retourne un `AsyncHandle`, attendu dans du code asynchrone. Un `join()` bloquant appartient à un contexte synchrone. L’opération bloquante s’exécute sur un worker dédié.

<!-- example: blocking -->
```rust
async fn operation() -> i64 {
    42
}

async fn calculate() -> i64 {
    let execution = runtime::spawn_blocking(operation());
    match execution.await {
        Ok(value) => { value },
        Err(error) => { drop(error); 0 },
    }
}

fn main() {
    let execution = runtime::spawn(calculate());
    match execution.join() {
        Ok(value) => { print(value); },
        Err(error) => { drop(error); print(0); },
    }
}
```

Sortie : `42`. [Paquet complet](examples/features/blocking/).


<a id="std-in-practice"></a>

### La STD en pratique

<a id="file"></a>

<a id="files-errors-and-caller-provided-buffers"></a>

#### Fichiers, erreurs et tampons fournis par l’appelant

L’appelant choisit le mode d’ouverture, les permissions et la taille du tampon. Dans cette API, les chemins sont des tranches d’octets terminées par NUL. Ce programme crée un fichier dans son répertoire de travail, y effectue des entrées-sorties puis le supprime. Un déplacement ou une destruction de `File` entraîne une seule fermeture de son handle natif.

<!-- example: file -->
```rust
use std::io::{File, FileError, FileMode, FilePerm, SeekFrom};

fn run() -> Result<usize, FileError> {
    let path: [u8; 9] = [100, 101, 109, 111, 46, 98, 105, 110, 0];
    let mut file = File::create(&path[..], FileMode::READ_WRITE | FileMode::TRUNCATE, FilePerm.DefaultMode)?;
    let bytes: [u8; 2] = [111, 107];
    let written = file.write(&bytes[..])?;
    drop(written);
    drop(file.seek(SeekFrom.Start(0))?);
    let mut output: [u8; 2] = [0; 2];
    let count = file.read(&mut output[..])?;
    drop(file);
    File::delete(&path[..])?;
    Ok(count)
}

fn main() {
    match run() {
        Ok(count) => { print(count); },
        Err(error) => { drop(error); print(0); },
    }
}
```

Sortie : `2`. [Paquet complet](examples/features/file/).

<a id="buffered"></a>

<a id="buffered-io-through-structural-contracts"></a>

#### Entrées-sorties tamponnées et contrats structurels

Les wrappers tamponnés empruntent explicitement le flux et le tampon de travail. Appelez `flush()` pour envoyer les octets en attente ; la destruction abandonne la sortie en attente. Cet exemple crée un fichier local et le supprime après l’avoir fermé.

<!-- example: buffered -->
```rust
use std::io::{File, FileMode, FilePerm};
use std::io::buffered::BufWriter;

fn main() {
    let path: [u8; 9] = [100, 101, 109, 111, 46, 98, 105, 110, 0];
    let mut file = match File::create(&path[..], FileMode::READ_WRITE | FileMode::TRUNCATE, FilePerm.DefaultMode) {
        Ok(file) => { file },
        Err(error) => { drop(error); return; },
    };
    let mut scratch: [u8; 4] = [0; 4];
    {
        let mut writer = BufWriter::new(&mut file, &mut scratch[..]);
        let bytes: [u8; 2] = [111, 107];
        match writer.write(&bytes[..]) {
            Ok(count) => { print(count); },
            Err(error) => { drop(error); return; },
        }
        match writer.flush() {
            Ok(()) => {},
            Err(error) => { drop(error); return; },
        }
    }
    match file.stats() {
        Ok(stats) => { print(stats.size()); },
        Err(error) => { drop(error); return; },
    };
    drop(file);
    drop(File::delete(&path[..]));
}
```

Sortie : `2, 2`. [Paquet complet](examples/features/buffered/).

<a id="network"></a>

<a id="typed-network-endpoints-and-datagrams"></a>

#### Points de terminaison réseau typés et datagrammes

Les opérations `bind` et `connect` reçoivent des objets d’adresse IPv4. Le port zéro demande au système un port local. Cet échange UDP sur l’interface de boucle locale utilise des tampons fournis par l’appelant et aucun serveur externe ; les liens vers TCP et les API asynchrones figurent plus bas.

<!-- example: network -->
```rust
use std::net::ipv4::{Addr, SocketAddr};
use std::net::udp::{Listener, connect};
use std::net::SocketError;

fn exchange() -> Result<usize, SocketError> {
    let mut listener = Listener::bind(SocketAddr::new(Addr::new(127, 0, 0, 1), 0))?;
    let mut peer = connect(listener.addr())?;
    let input: [u8; 1] = [42];
    drop(peer.send(&input[..])?);
    let mut output: [u8; 1] = [0];
    let datagram = listener.recv(&mut output[..])?;
    print(output[0]);
    Ok(datagram.count())
}

fn main() {
    match exchange() {
        Ok(count) => { print(count); },
        Err(error) => { drop(error); print(0); },
    }
}
```

Sortie : `42, 1`. [Paquet complet](examples/features/network/).

<a id="encoding"></a>

<a id="hashes-and-encodings-with-bounded-output"></a>

#### Hachage et encodage avec une sortie bornée

La STD fournit des implémentations natives de hachage, de cryptographie, de TLS et de codecs, ainsi que des entrées-sorties propres aux plateformes. Les API qui produisent un nombre variable d’octets reçoivent des tampons détenus par l’appelant. Cet exemple hache deux octets et encode le condensat de taille fixe en hexadécimal sans allocation non bornée.

<!-- example: encoding -->
```rust
use std::crypto::sha256::Sha256;
use std::encoding::hex::encode;

fn main() {
    let input: [u8; 2] = [111, 107];
    let mut hash = Sha256::new();
    match hash.update(&input[..]) {
        Ok(()) => {},
        Err(error) => { drop(error); return; },
    }
    let digest = hash.finish();
    let mut encoded: [u8; 64] = [0; 64];
    match encode(&digest[..], &mut encoded[..]) {
        Ok(count) => { print(count); },
        Err(error) => { drop(error); print(0); },
    }
}
```

Sortie : `64`. [Paquet complet](examples/features/encoding/).

<a id="binary"></a>

#### Primitifs binaires avec un ordre des octets explicite

L’appelant fournit le tampon et choisit l’ordre little-endian ou big-endian. Les mêmes quatre octets donnent ici deux valeurs différentes selon l’ordre demandé.

<!-- example: binary -->
```rust
use std::encoding::binary::{write_u32_be, read_u32_be, read_u32_le, Error};

fn encode() -> Result<(), Error> {
    let mut bytes: [u8; 4] = [0; 4];

    // 0x01020304 becomes the four bytes 01 02 03 04.
    let written = write_u32_be(16909060, &mut bytes[..])?;
    print(written);

    let big = read_u32_be(&bytes[..])?;
    let little = read_u32_le(&bytes[..])?;
    print(big);
    print(little);

    Ok(())
}

fn main() {
    match encode() {
        Ok(()) => {},
        Err(error) => { drop(error); },
    }
}
```

Sortie: `4, 16909060, 67305985`. [Paquet complet](examples/features/binary/).

<a id="time"></a>

#### Temps monotone et échéances bloquantes

`Duration` exprime une durée, `Instant` lit une horloge monotone et `Timer` attend une échéance. Ces instants ne sont pas des dates calendaires.

<!-- example: time -->
```rust
use std::time::{Duration, Instant, Timer, sleep, Error};

fn wait() -> Result<(), Error> {
    let start = Instant::now()?;
    sleep(Duration::from_millis(2))?;

    let elapsed = start.elapsed()?;
    print(elapsed.as_nanos() >= 2000000);

    // A zero-duration deadline is already ready when waited.
    let timer = Timer::after(Duration::from_nanos(0))?;
    timer.wait()?;

    Ok(())
}

fn main() {
    match wait() {
        Ok(()) => { print(1); },
        Err(error) => { drop(error); },
    }
}
```

Sortie: `true, 1`. [Paquet complet](examples/features/time/).

<a id="async-time"></a>

#### Attentes asynchrones d’échéances

L’attente suspend la tâche appelante. Un worker bloquant existant effectue l’attente native ; cette première implémentation utilise un worker par attente active.

<!-- example: async_time -->
```rust
use std::time::{Duration, Error};
use std::time::asyn::{sleep, Timer};

async fn delayed_value() -> Result<i64, Error> {
    sleep(Duration::from_millis(2)).await?;

    let timer = Timer::after(Duration::from_nanos(0))?;
    timer.wait().await?;

    Ok(42)
}

fn main() {
    let execution = runtime::spawn(delayed_value());

    // Launch failures and the task's own errors remain distinct.
    match execution.join() {
        Ok(result) => {
            match result {
                Ok(value) => { print(value); },
                Err(error) => { drop(error); },
            }
        },
        Err(error) => { drop(error); },
    }
}
```

Sortie: `42`. [Paquet complet](examples/features/async_time/).

<a id="compression"></a>

<a id="compression-with-an-explicit-workspace"></a>

#### Compression avec un espace de travail explicite

Les API de compression empruntent l’entrée, la sortie et l’espace de travail détenus par l’appelant. L’exemple fournit l’espace de travail documenté pour les niveaux Gzip 1 à 9, effectue un aller-retour sur une trame et vérifie sa taille décodée grâce au nombre d’octets retourné.

<!-- example: compression -->
```rust
use std::compression::gzip::{Params, compress, decompress};

fn main() {
    let input: [u8; 3] = [65; 3];
    let mut encoded: [u8; 128] = [0; 128];
    let mut workspace: [u64; 36864] = [0; 36864];
    let params = Params::new();
    let count = match compress(&input[..], &mut encoded[..], &params, &mut workspace[..]) {
        Ok(count) => { count },
        Err(error) => { drop(error); return; },
    };
    let mut output: [u8; 3] = [0; 3];
    match decompress(&encoded[..count], &mut output[..]) {
        Ok(count) => { print(count); },
        Err(error) => { drop(error); return; },
    }
    print(output[0]);
}
```

Sortie : `3, 65`. [Paquet complet](examples/features/compression/).


<a id="native-interop"></a>

### Interopérabilité native

<a id="foreign"></a>

<a id="unchecked-c-typed-operands-and-native-assembly"></a>

#### C non vérifié, opérandes typées et assembleur natif

Le code externe appartient à un bloc `@unchecked`. `${name}` lie une opérande Corbo existante. Les chemins des en-têtes sont explicites. `addr` est réservé au bloc non vérifié, et son adresse ne doit pas en sortir. Le respect de l’ABI, des durées de vie et de la validité mémoire dans le code externe reste à la charge du développeur.

<!-- example: foreign -->
```rust
fn main() {
    let mut answer: i64 = 0;
    @unchecked {
        @c(includes={"stdint.h"}) {
            ${answer} = (int64_t)42;
        }
        @asm { nop }
    }
    print(answer);
}
```

Sortie : `42`. [Paquet complet](examples/features/foreign/).

Les [contrats du code externe](docs/FOREIGN_C.md) expliquent la sélection de cible avec annotations appariées, les chemins des en-têtes, les opérandes typées et les responsabilités dans le code non vérifié.

<a id="explore-the-std"></a>

## Explorer la STD

Importez les types natifs de collections avec `use std::{Vector, HashMap, String};`. Leurs noms publics sont déclarés dans [collections.crb](stdlib/src/collections.crb). Les algorithmes des collections natives se trouvent dans le runtime ; `String<N>` bornée est implémentée dans la STD. Le [guide de l’API des collections](docs/COLLECTIONS_API.md) décrit la construction, la possession des éléments, les emprunts et le nettoyage.

| Paquet | Fonctionnalités principales | Référence |
| --- | --- | --- |
| `std::{Pool, Vector, HashMap, String}` | Pools de capacité fixe, vecteurs, maps, chaînes UTF-8 grandissantes et `String<N>` inline avec un maximum en octets connu à la compilation | [Collections](docs/COLLECTIONS_API.md) · [Chaînes bornées](docs/UTF8_STRINGS-fr.md) |
| `std::iter` | Iter, Map, Filter, Reduce et méthode d’instance `collect` | [API](docs/STDLIB.md#stditer) |
| `std::io`, `std::io::asyn` | Lecture/écriture de fichiers, seek, métadonnées, renommage/suppression et flux tamponnés | [API](docs/STDLIB.md#stdio) · [Guide des fichiers](docs/FILE.md) |
| `std::net::{tcp, udp}` et `std::net::asyn` | Points de terminaison IPv4 typés, sockets, entrées-sorties TCP partielles et demi-connexions asynchrones empruntées | [Réseau](docs/NETWORKING.md) |
| `std::net::http` | Analyse des en-têtes de requêtes/réponses, limites statiques configurables et corps optionnels en flux via un contrat de lecture | [HTTP](docs/HTTP.md) |
| `std::net::tls` | Dérivation des clés, records, handshake et validation X.509 de TLS 1.3 en natif ; wrapper OpenSSL facultatif | [API](docs/STDLIB.md#stdnettls) |
| `std::crypto` | AES-GCM/CBC, familles SHA, HMAC/HKDF, Argon2id, aléa, P-256 et conteneurs de clés | [API](docs/STDLIB.md#stdcryptoaes) |
| `std::encoding` | Hex, Base64, DER et PEM avec sortie détenue par l’appelant | [API](docs/STDLIB.md#stdencodinghex) |
| `std::encoding::binary` | Lecture/écriture de primitifs, ordre little-endian/big-endian explicite et tampons fournis par l’appelant | [API binaire](docs/BINARY_AND_TIME_API-fr.md) |
| `std::time`, `std::time::asyn` | Duration/Instant monotones, sleep et timers réutilisables ; attentes async déléguées à des workers bloquants | [API temporelle](docs/BINARY_AND_TIME_API-fr.md) |
| `std::compression::{gzip, zstd}` | Codecs natifs bornés, traitement en flux et dictionnaires | [Compression](docs/COMPRESSION.md) |
| `std::env` | Arguments du processus tout en conservant un `main` sans paramètres | [API](docs/STDLIB.md#stdenv) |

La référence des API décrit les profils cryptographiques effectivement pris en charge et les contrats d’erreur. L’analyse et la sérialisation de clés RSA n’impliquent pas la prise en charge de la signature ou du chiffrement RSA. La disponibilité d’une API ne constitue pas une affirmation d’audit de sécurité indépendant.

<a id="source-layout-and-runtime-boundary"></a>

## Organisation des sources et frontière du runtime

| Emplacement | Responsabilité |
| --- | --- |
| [omework/corboc](https://github.com/omework/corboc) | Lexeur, parseur, représentations, vérificateur, placement et backend C11 auto-hébergés actifs |
| [stdlib/src](stdlib/src/) | API de la STD et implémentations portables ou propres aux plateformes |
| [runtime/corbo](runtime/corbo/README.md) | Algorithmes d’allocation, de collections, de nettoyage, d’ordonnancement et de réacteur du runtime en Corbo |
| [runtime](runtime/README.md) | ABI C canonique et implémentation C conservée pour comparaison |
| [ide](ide/README.md) | Prise en charge de `.crb` dans Vim/Neovim et VS Code |
| [rust_frontend](rust_frontend/README.md) / [prototype](prototype/README.md) | Implémentations de référence figées ou historiques |

`corboc` fixe ses entrées STD/runtime avec `corbo.lock`. Le backend actuel génère du C11. Les primitives machine/ABI du runtime conservent des liaisons explicites `@unchecked`/`@c` ; le portage des algorithmes ne supprime pas le C de la chaîne de compilation. La bibliothèque mémoire partagée est également accessible depuis le C grâce à [corbo_runtime.h](runtime/corbo_runtime.h).

Le [rapport du cycle runtime](docs/cycles/CORBO_RUNTIME_CYCLE.md) consigne les comparaisons d’exécution C/Corbo et les éléments de validation de la reconstruction du compilateur, avec les limites de plateforme.

<a id="build-the-compiler-from-source"></a>

## Construire le compilateur à partir des sources

Le compilateur auto-hébergé actif est maintenu dans [omework/corboc](https://github.com/omework/corboc). Ce dépôt du langage contient la grammaire, les règles, la STD, le runtime, les exemples et les ressources pour éditeurs. Le fichier `corbo.lock` du compilateur fixe sa révision exacte de la STD et du runtime.

Depuis ce dépôt du langage, clonez le compilateur à côté et fournissez un compilateur de départ déjà compatible :

```sh
CORBO_LANGUAGE_ROOT="$PWD"
git clone git@github.com:omework/corboc.git ../corboc
cd ../corboc
python3 scripts/corbo_sources.py --from-repo "$CORBO_LANGUAGE_ROOT"
python3 scripts/build.py --seed /absolute/path/to/corboc --verify-self
export PATH="$PWD/build/install/bin:$PATH"
cd "$CORBO_LANGUAGE_ROOT"
```

`--from-repo` fournit les objets Git au commit fixé, sans copier les fichiers non commités. Omettez cette option pour récupérer les sources fixées depuis GitHub. Le [guide de construction du compilateur](https://github.com/omework/corboc#build-and-self-rebuild) détaille les exigences du compilateur de départ, les prérequis et les options d’installation.

Depuis le dépôt du compilateur, reconstruisez le compilateur avec sa commande habituelle :

```sh
corboc build . -o build/install/bin/corboc-next
```

La [référence Rust](rust_frontend/README.md), figée, conserve une ancienne syntaxe et ne peut pas amorcer le compilateur actuel. Les paquets historiques Din/Crust nécessitent des fichiers source `.crb`, un point d’entrée dans `src/main.crb` et la STD installée correspondante.

<a id="documentation-and-validation-status"></a>

## Documentation et état de la validation

Corbo est expérimental. La grammaire, les règles acceptées, les chemins implémentés et les validations exécutées sont des sources d’information distinctes. Les exemples exécutables de ce README illustrent leurs chemins particuliers ; ils ne prouvent pas que toute composition est implémentée ou sûre du point de vue mémoire.

Les appels de fonctions et de closures, ainsi que leur passage explicite, fonctionnent indépendamment des adaptateurs d’itérateurs. Les dix formes refusées lors du premier travail de documentation sont désormais prises en charge, notamment les retours directs d’emprunts, les contrats structurels de fonctions, les opérations numériques et textuelles et les wrappers de branches. Le [suivi de couverture](docs/cycles/DOCUMENTATION_COVERAGE_CYCLE.md) consigne les programmes exécutés, les frontières de rejet et les limites de plateforme ; les [observations historiques](docs/DOCUMENTATION_LIMITS.md) restent disponibles.

La documentation dans les sources utilise `//!` pour les modules et `///` pour les déclarations et les membres, ainsi que des commentaires de style Doxygen pour l’ABI et la référence C. Le contrôle de couverture vérifie aussi les fonctions auxiliaires internes, pas seulement les API publiques.

```sh
python3 scripts/stdlib_docs.py > docs/STDLIB.md
python3 scripts/stdlib_docs.py --runtime > docs/RUNTIME.md
python3 scripts/stdlib_docs.py --check
python3 validation/check_documentation.py --corboc ../corboc/build/install/bin/corboc
```

La dernière commande nécessite un compilateur C11 sur la machine hôte et l’accès aux sockets de boucle locale. Les résultats et programmes générés sont conservés dans `build/documentation/`. Cette passe de documentation valide l’exécution sur la machine hôte macOS ARM64 ; elle ne répète pas la matrice complète des plateformes. L’exécution sous Windows ARM64 reste différée.

La documentation est en anglais par défaut. Les versions françaises utilisent le suffixe `-fr.md`.

<a id="project-references"></a>

## Références du projet

- [Grammaire du core](CORE_GRAMMAR.ebnf) et [règles du langage](docs/LANGUAGE_RULES.md)
- [État de la sûreté mémoire](docs/SAFETY.md)
- [Modèle des représentations](docs/MEMORY_REPRESENTATION.md)
- [Checklist d’implémentation](docs/IMPLEMENTATION_CHECKLIST.md) et [matrice de vérification](docs/VERIFICATION_MATRIX.md)
- [Consignes de validation](docs/VALIDATION_GUIDELINES.md) et [guide d’audit indépendant](docs/CORE_AUDIT_HANDOFF.md)
- [Frontière entre les dépôts du compilateur et du langage](docs/COMPILER_REPOSITORY.md)

<a id="license"></a>

## Licence

Corbo et sa bibliothèque standard sont disponibles, au choix, sous [licence MIT](LICENSE-MIT) ou sous [licence Apache, version 2.0](LICENSE-APACHE). Les parties dérivées conservent leurs [mentions tierces supplémentaires](stdlib/THIRD_PARTY_NOTICES.txt).
