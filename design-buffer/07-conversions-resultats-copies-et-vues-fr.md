[English](07-conversions-resultats-copies-et-vues.md)

# Brouillon 07 — Conversions, résultats faillibles, copies et vues

Décisions validées dans l’atelier, à intégrer sur demande. Les exemples
décrivent la conception retenue et ont été examinés sur papier.

## Types primitifs du noyau

| Famille | Types retenus |
| --- | --- |
| Entiers signés | `i32`, `i64` |
| Entiers non signés | `u8`, `u16`, `u32`, `u64` |
| Booléen | `bool` |
| Flottants | `f32`, `f64` |

Ces types se copient par valeur. `Int` est le nom employé dans les
illustrations et le prototype actuel. Le noyau cible expose `i32` comme
entier signé sur 32 bits et ne définit pas de type ni d'alias `Int`.
Les règles déjà retenues pour `char` sont décrites avec
les [types texte](../docs/UTF8_STRINGS.md). La liste fixe les types numériques et
logiques du noyau. L'intégration au compilateur est reportée.

## Littéraux entiers

Un littéral entier sans type imposé est de type `i64`. Une annotation de
déclaration peut lui donner un autre type entier si la valeur est
représentable. Par exemple, `let taille: u64 = 9223372036854775808;` est
admis. `let taille = 9223372036854775808;` est refusé, car la valeur dépasse
`i64`.
Le compilateur demande alors un type explicite.

La signature donne son type à un littéral entier fourni directement en
argument ou en retour. Si le paramètre ou le retour est `u8`, le littéral
`7` est de type `u8` et `256` est refusé. La même règle s'applique au
littéral fourni comme valeur finale du corps de la fonction.

Quand le signe `-` précède directement un littéral entier, on applique
le signe avant de vérifier les bornes du type. Ainsi,
`let minimum: i32 = -2147483648;` et
`let minimum64 = -9223372036854775808;` sont admis. Prendre ensuite
l'opposé d'une valeur égale à cette borne minimale provoque un débordement.

## Littéraux flottants

Les formes décimales `1.5`, `1.` et `.5` sont admises. Un littéral
flottant contient un point et au moins un chiffre. Un littéral composé de
chiffres décimaux sans point est entier. La notation exponentielle
(`1e3`, `1.4e-3`) est refusée. `1..3` conserve le séparateur
d'intervalle `..`.

Le type par défaut d'un littéral flottant est `f64`. L'annotation de
la déclaration précise le type. La syntaxe ne prévoit aucun suffixe.
La valeur décimale du littéral est convertie vers la valeur représentable
la plus proche dans le type retenu. En cas d'égalité, le dernier bit de
précision pair départage les deux valeurs, comme en Rust. Un littéral
comme `0.1` est donc admis, même si sa valeur décimale exacte ne tient
pas dans le format binaire.
Le compilateur rejette un littéral dont la conversion produirait un
infini, ou dont la valeur décimale non nulle deviendrait zéro.
[Référence Rust sur les littéraux flottants](https://doc.rust-lang.org/reference/expressions/literal-expr.html#floating-point-literal-expressions)

```rust
fn main() {
    let seuil: f32 = .5;
    let facteur = 1000.; // f64
}
```

[Grammaire du noyau](../CORE_GRAMMAR.ebnf)

## Opérateurs arithmétiques

Crust reprend les opérateurs arithmétiques usuels de C. Les entiers
acceptent `+`, `-`, `*`, `/` et `%`. Les flottants acceptent `+`,
`-`, `*` et `/`. Le reste `%` est réservé aux entiers.

La négation unaire `-x` s'applique aux entiers signés et aux flottants.
Le résultat garde le type de `x` et doit y être représentable.
Pour prendre l'opposé d'un entier non signé, on le convertit
explicitement vers un type signé, par exemple `-(octet as i64)`
pour un `u8`.

Une opération arithmétique entre deux variables exige le même type pour
les deux opérandes. Si les types diffèrent, une conversion explicite est
requise. Par exemple, pour `compteur: i32` et `octet: u8`, on écrit
`compteur + (octet as i32)`.

Dans une opération entre un entier déjà typé et un littéral entier,
l'opérande typé fixe le type du littéral, quel que soit son côté.
Si la valeur du littéral n'est pas représentable dans ce type,
le compilateur refuse l'expression. Par exemple, avec `octet: u8`,
`octet + 1` calcule en `u8`, tandis que `octet + 256` est refusé.
Un littéral qui tient dans le type ne dispense pas de vérifier le
résultat de l'opération.

Avec un opérande flottant déjà typé, un littéral flottant prend le type
`f32` ou `f64` de cet opérande. Le contexte d'une opération ne change
pas la famille d'un littéral. Pour `mesure: f32`, `mesure + 1.` est
admis en `f32` et `mesure + 1` est refusé.

Dans une expression arithmétique composée uniquement de littéraux
entiers, l'annotation du receveur fixe le type du calcul. Les littéraux
et les résultats intermédiaires doivent tenir dans ce type.
`let total: u8 = 200 + 55;` est admis.
`let trop: u8 = 200 + 56;` est refusé à la compilation.
Sans type imposé, le calcul entre littéraux entiers se fait en `i64`.

Le compilateur utilise les opérateurs C pour le calcul. Pour les entiers,
le résultat doit être représentable dans son type Crust, conformément
à [F5](../docs/FOUNDATIONS_AND_VECTORS.md#types-effets-et-contrôle).
Le compilateur diagnostique une erreur qu'il peut établir statiquement.
Sinon, il émet les vérifications nécessaires avant toute opération C
indéfinie ou toute conversion qui perdrait la valeur calculée. Cela couvre
notamment le débordement et un diviseur nul pour `/` et `%`.
Par exemple, si le résultat de `255 + 1` est de type `u8`, le calcul
échoue, même si C peut calculer `256` dans un type plus large.
Une vérification prouvée inutile à la compilation peut être omise.

Pour un entier signé à la borne minimale de son type, `minimum / -1`
est refusé, car le quotient ne tient pas dans ce type. En revanche,
`minimum % -1` donne zéro. Pour `%`, la représentabilité du reste
suffit. Le backend C doit produire ce zéro sans évaluer une opération
C indéfinie lorsque le quotient ne serait pas représentable.

La division par zéro est refusée pour les entiers et les flottants,
quel que soit le numérateur. Pour `f32` et `f64`, `0.0` et `-0.0`
sont tous deux des diviseurs nuls. Une division dont le diviseur nul
est connu à la compilation est diagnostiquée à ce moment-là. Sinon,
le contrôle intervient avant la division à l'exécution.

Comme en Rust, le résultat d'une opération flottante est arrondi à la
valeur représentable la plus proche dans le type de l'opération. En cas
d'égalité, le dernier bit de précision pair départage les deux valeurs.
En `f32`, `16777218.0 + 1.0` donne donc `16777220.0`. La division
`1.0 / 3.0` donne une approximation.

Crust conserve les erreurs de division par zéro, de débordement vers
l'infini et de résultat mathématiquement non nul qui s'arrondirait à
zéro. Un résultat exact nul, comme `0.5 - 0.5`, est admis.
[Arithmétique flottante de Rust](https://doc.rust-lang.org/core/primitive.f32.html)

Le compilateur rejette l'opération s'il peut établir l'erreur à la
compilation. Sinon, le programme s'arrête à l'exécution lorsqu'elle
survient. Cette règle s'applique indépendamment de la cible générée.
L'intégration est reportée.

## Affectations composées

`+=`, `-=`, `*=`, `/=`, `%=`, `&=`, `|=`, `^=`, `<<=` et
`>>=` appliquent les mêmes règles de typage et les mêmes contrôles que
les opérations correspondantes.
L'emplacement doit être modifiable. Il est évalué une seule fois, même
s'il contient un indice calculé, comme dans `tableau[index()] += 1`.
L'écriture à cet emplacement a lieu seulement si le calcul réussit.

L'ordre est fixé. On détermine l'emplacement et on vérifie sa validité,
puis on lit sa valeur actuelle. Ensuite, on évalue l'opérande droit et
on vérifie le calcul avant d'écrire le résultat au même emplacement.
Un accès hors limites pendant la détermination de l'emplacement arrête
le programme avant l'évaluation de l'opérande droit.

Pendant l'évaluation de la droite, l'emplacement reste réservé. La
droite peut le lire tant que ses emprunts se terminent avant l'écriture
finale. Elle ne peut ni le modifier, ni le déplacer, ni le détruire.
Un accès mutable à un autre emplacement reste possible si le
compilateur prouve que les deux emplacements sont distincts.

La droite d'une affectation composée peut suspendre son exécution.
Le compilateur doit prouver que l'emplacement et sa réservation
restent valides jusqu'à l'écriture. L'état de la tâche conserve
l'emplacement déjà déterminé et l'ancienne valeur déjà lue. À la reprise,
l'écriture cible ce même emplacement sans l'évaluer de nouveau.

## Comparaisons numériques

`==`, `!=`, `<`, `<=`, `>` et `>=` rendent un `bool`. Deux opérandes
déjà typés doivent avoir le même type. Une différence de type exige une
conversion explicite. Un littéral peut prendre le type de l'autre opérande
s'il appartient à la même famille et si sa valeur y est représentable,
selon les règles de typage des littéraux. Par exemple, `octet == 7`
type `7` en `u8` si `octet` est un `u8`, tandis que `octet < 256` est
refusé.

## Conditions et logique booléenne

Les conditions de `if` et de `while` exigent un `bool`. La négation
`!` et les opérateurs `&&` et `||` prennent des opérandes de type
`bool` et rendent un `bool`. Pour tester si un entier est non nul,
on écrit `n != 0`. Les règles de court-circuit de
[F4](../docs/FOUNDATIONS_AND_VECTORS.md#types-effets-et-contrôle) s'appliquent.

## Opérations bit à bit

`&` (ET), `|` (OU), `^` (OU exclusif) et `~` (complément) opèrent sur
les entiers. Le résultat conserve le type et la largeur des opérandes.
Les opérateurs binaires exigent le même type des deux côtés et suivent
les règles de typage des littéraux de l'arithmétique. Le complément
`~masque` d'un `u8` qui vaut 5 vaut 250.

En position préfixe, `&a` reste un emprunt. En position infixe,
`a & b` est une opération bit à bit. Les comparaisons lient plus fort
que `&`, puis `^` et `|`, qui lient à leur tour plus fort que `&&`
et `||`. Pour comparer le résultat d'un masque, on écrit
`(masque & 1) != 0`.

Les décalages `<<` et `>>` opèrent sur les entiers. Le nombre de
positions doit être compris entre zéro et la largeur du type de
l'opérande gauche moins un. Ainsi, pour un `u8`, `masque << 2` a un
nombre de positions valide et `masque << 8` est refusé. Le compilateur
rejette un nombre de positions invalide qu'il connaît à la compilation
et émet un contrôle à l'exécution sinon. Les additions et soustractions
lient plus fort que les décalages, qui lient plus fort que les comparaisons.

Le nombre de positions peut être de n'importe quel type entier,
indépendamment du type de l'opérande gauche. Le résultat conserve le
type de l'opérande gauche. Par exemple, un `u8` peut être décalé d'une
valeur de type `i64` si cette valeur est comprise entre 0 et 7.

`a << n` calcule `a` multiplié par deux à la puissance `n`. Le résultat
doit tenir dans le type de `a`. Même avec un nombre de positions valide,
un débordement est refusé à la compilation s'il est connu, sinon contrôlé
à l'exécution. Par exemple, en `u8`, `127 << 1` donne 254 et
`128 << 1` déborde.

`a >> n` conserve le type de `a`. Pour un entier signé, les bits
libérés à gauche sont remplis avec le bit de signe. Pour un entier non
signé, ils sont remplis avec des zéros. Ainsi, `-3 >> 1` donne `-2` sur
un entier signé et `5 >> 1` donne `2` sur un entier non signé.
[Référence Rust](https://doc.rust-lang.org/reference/expressions/operator-expr.html#arithmetic-and-logical-binary-operators)

## Littéraux dans les tableaux

Un élément déjà typé peut donner son type aux littéraux du tableau,
quelle que soit sa position. Les autres éléments déjà typés doivent
avoir ce même type. Les littéraux suivent les règles de compatibilité
de famille et de représentabilité. Avec `octet: u8`,
`[1, octet, 3]` a donc le type `[u8; 3]`, tandis que
`[1, octet, 256]` est refusé.

## Littéraux aux jonctions

Une valeur déjà typée peut donner son type aux littéraux des autres
chemins qui fournissent le même résultat, quel que soit leur ordre.
Cette règle s'applique aux branches de `if`, aux bras de `match` et
aux `break` qui fournissent la valeur d'une boucle. Les valeurs déjà
typées doivent avoir le même type. Les littéraux doivent appartenir à
la même famille et tenir dans ce type. Un chemin qui quitte le calcul
sans fournir de valeur ne participe pas au choix du type.

## Indices et longueurs

`len()` sur un tableau ou une tranche retourne un `u64`, quelle que soit
la cible. Un tableau ou une tranche vide a une longueur égale à zéro.
Par exemple, `let vide: [i64; 0] = [];` donne `vide.len() == 0`.

Un indice de tableau peut être de n'importe quel type entier. Sa valeur
doit être supérieure ou égale à zéro et strictement inférieure à la
longueur du tableau. Le contrôle porte sur la valeur d'origine, avant
toute conversion interne susceptible de la tronquer. Un indice hors
limites connu à la compilation est refusé. Sinon, le compilateur émet
un contrôle à l'exécution avant l'accès.

## Conversions entières

`as` est réservé aux conversions qui préservent toutes les valeurs du type
source. La règle s’applique au type, y compris pour une valeur connue à la
compilation. Un littéral représentable peut être directement typé, par exemple
`let octet: u8 = 42;`.

`try_from` effectue les autres conversions entières et rend un `Result`.
`u8::try_from(n)` réussit avec la valeur d’origine pour `0..=255` et
signale une erreur autrement.

## Conversions entre flottants

`f32 as f64` est admis. Chaque valeur du type source est représentable
exactement dans le type destination. Le même critère interdit
`f64 as f32`, y compris si la valeur est connue à la compilation et
pourrait être représentée en `f32`.

`f32::try_from(valeur_f64)` renvoie un `Result`. La conversion réussit
seulement si la valeur du `f64` est exactement représentable en `f32`.
Un arrondi nécessaire ou une valeur hors plage produit une erreur.

## Conversions entre entiers et flottants

Le même critère s'applique entre les deux familles. `as` est admis si
toutes les valeurs du type source sont exactement représentables dans
le type destination. `i32 as f64` est admis. `i64 as f64` est refusé,
même pour une valeur connue et petite. Un flottant ne peut pas être
converti en entier avec `as`, car les valeurs fractionnaires du type
source ne sont pas toutes représentables en entier.

Dans les deux sens, `Destination::try_from(valeur)` réussit seulement
si la valeur fournie est exactement représentable dans le type
destination. `i64::try_from(3.0)` réussit, tandis que
`i64::try_from(3.5)` échoue. `f64::try_from(9007199254740993)` échoue
également, car cet entier `i64` demanderait un arrondi en `f64`.

## Erreur publique des conversions numériques

`Destination::try_from(valeur)` renvoie
`Result<Destination, NumericConversionError>` pour toutes les conversions
numériques exactes. Si la valeur ne peut pas être représentée exactement,
le résultat est `Err(NumericConversionError::NotRepresentable)`. Ce cas
couvre une valeur hors des bornes, une partie fractionnaire lors d'une
conversion vers un entier et toute autre perte de précision.

## Usage d’un résultat faillible

Tout résultat faillible doit avoir un usage explicite, quel que soit son
contenu. Le traiter dans la logique du programme, le transmettre ou le
consommer avec `drop(-> ...)` satisfait la règle. L’appel seul suivi de
`;`, `let _ = ...;` et une liaison jamais utilisée sont refusés.
Dans un match, `Err(_)` peut ignorer le détail d’une erreur dépourvu de
valeur propriétaire tout en traitant la variante. Les règles du
[brouillon 01](01-resultat-proprietaire.md) s’appliquent quand un motif
écarte une allocation possédée.

```rust
fn main() {
    let n: Int = 300;
    match u8::try_from(n) {
        Ok(octet) => { print(octet); },
        Err(_) => { print("hors limites"); },
    }

    drop(-> u8::try_from(42));
}
```

## Copie d’une structure locale

`copy(original)` sur une structure locale produit une valeur indépendante
du même type sur la data stack par défaut. Tous les champs doivent être
copiables. Une référence partagée copiée conserve sa cible et ses
contraintes. Le contenu pointé reste partagé.

```rust
struct Point {
    x: Int,
    y: Int,
}

fn main() {
    let original = Point { x: 10, y: 20 };
    let mut copie = copy(original);
    copie.x = 30;
    print(original.x); // 10
    print(copie.x);    // 30
}
```

## Découpes UTF-8

`&texte[debut..fin]` construit une vue `&str` avec une fin exclue.
Les bornes sont des positions en octets. Il faut
`0 <= debut <= fin <= byte_len` et les deux bornes doivent être sur des
frontières UTF-8. Si l’invalidité est établie statiquement, le programme
est refusé. Sinon, le contrôle précède la création de la vue et un échec
arrête le programme avec un diagnostic.

`texte.try_slice(debut..fin)` applique les mêmes contrôles et rend un
`Result`. Une plage invalide donne `Err(OutOfBounds)`. Une plage valide
dont une borne coupe un caractère donne `Err(NotCharBoundary)`. Le
succès donne `Ok(&str)`, qui emprunte les octets d’origine sans copie.
Les formes à borne omise utilisent les mêmes bornes que les crochets.

```rust
fn afficher_prefixe(texte: &str, fin: Int) {
    match texte.try_slice(..fin) {
        Ok(vue) => { print(vue); },
        Err(OutOfBounds) => { print("borne hors limites"); },
        Err(NotCharBoundary) => { print("caractère coupé"); },
    }
}

fn main() {
    let texte = "été";
    print(&texte[..2]);            // é
    afficher_prefixe(texte, 1);   // caractère coupé
    afficher_prefixe(texte, 8);   // borne hors limites
}
```

## Cas refusés

| Cas | Motif du refus |
| --- | --- |
| `n as u8` avec `n: Int`. | Le type source contient des valeurs que `u8` ne représente pas. |
| `u8::try_from(n);`, `let _ = u8::try_from(n);` ou une liaison inutilisée. | Le résultat faillible exige un usage explicite. |
| `copy(original)` lorsque `original` contient un champ `&mut Int`. | La structure n’est pas copiable. |
| `&"été"[..1]`. | La borne coupe le premier caractère. |
| Conserver une vue issue de `try_slice` au-delà de la vie de ses octets. | Le résultat conserve l’emprunt de la source. |

## Règles à mettre à jour

- **F5 et I5** pour la conversion entière exacte et la conversion
  faillible. [FOUNDATIONS_AND_VECTORS.md](../docs/FOUNDATIONS_AND_VECTORS.md) ·
  [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md)
- **U1 et L6** pour l’usage explicite ou la destruction du résultat
  faillible. [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md)
- **ST17–ST18** pour la copie de structures locales et la source de la
  copie. [STRUCTURES_METHODS.md](../docs/STRUCTURES_METHODS.md)
- **TX4 et E2**, avec TX6 comme règle voisine, pour le contrôle des
  découpes directes et l’ajout de `try_slice`.
  [UTF8_STRINGS.md](../docs/UTF8_STRINGS.md) ·
  [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md)
