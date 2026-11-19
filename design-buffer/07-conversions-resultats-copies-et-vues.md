[Français](07-conversions-resultats-copies-et-vues-fr.md)

<a id="brouillon-07--conversions-résultats-faillibles-copies-et-vues"></a>

# Draft 07 — Conversions, Failed Results, Copies and Views

Validated decisions in the workshop, to be included on request.
describe the design selected and were reviewed on paper.

<a id="types-primitifs-du-noyau"></a>

## Primitive Kernel Types

| Famille | Types retenus |
| --- | --- |
| Signed by the parties | `i32`, `i64` |
| Unsigned third parties | `u8`, `u16`, `u32`, `u64` |
| Boolean | `bool` |
| Flottants | `f32`, `f64` |

These guys are copying by value. `Int` is the name used in the
illustrations and the current prototype. The target kernel displays `i32` comme
signed in whole on 32 bits and does not define type or alias `Int`.
The rules already adopted for `char` are described with
[text types](../docs/UTF8_STRINGS.md). The list sets the numerical and
The integration of the compiler is postponed.

<a id="littéraux-entiers"></a>

## Whole Literals

A whole literal without the required type is of type `i64`. Annotation of
declaration may give it another integer type if the value is
for example, `let taille: u64 = 9223372036854775808;` is
admis. `let taille = 9223372036854775808;` is refused, because the value exceeds
`i64`.
The compiler then asks for an explicit type.

The signature gives its type to an entire literal supplied directly in
argument or in return. If the parameter or return is `u8`, the literal
`7` is of type `u8` and `256` The same rule applies to the
literal provided as the final value of the body of the function.

When the sign `-` directly precedes an entire literal, apply
the sign before checking the terminals of the type.
`let minimum: i32 = -2147483648;` and
`let minimum64 = -9223372036854775808;` are allowed. Take then
the opposite of a value equal to this minimum limit causes overflow.

<a id="littéraux-flottants"></a>

## Floating Literals

Decimal forms `1.5`, `1.` and `.5` a literal
A literal composed of a number of
decimal numbers without point is entire. The exponential notation
(`1e3`, `1.4e-3`) is refused. `1..3` keeps the separator
d'intervalle `..`.

The default type of a floating literal is `f64`. The annotation of
the declaration specifies the type. The syntax does not provide any suffix.
The decimal value of the literal is converted to the representable value
In the case of equality, the last bit of
precision pair sets both values, as in Rust. A literal
comme `0.1` is therefore allowed, even if its exact decimal value does not
not in binary format.
The compiler rejects a literal whose conversion would produce a
Infinite, or whose decimal value would not be zero.
[Rust reference on floating literals](https://doc.rust-lang.org/reference/expressions/literal-expr.html#floating-point-literal-expressions)

```rust
fn main() {
    let seuil: f32 = .5;
    let facteur = 1000.; // f64
}
```

[Speed of the kernel](../CORE_GRAMMAR.ebnf)

<a id="opérateurs-arithmétiques"></a>

## Arithmetic operators

Crust takes over the usual arithmetic operators of C. Integers
acceptent `+`, `-`, `*`, `/` and `%`. Floatings accept `+`,
`-`, `*` and `/`. The rest `%` is reserved for the whole.

Unary denial `-x` applies to signed integers and floating.
The result keeps the type of `x` and must be representative.
To take the opposite of an unsigned integer, we convert it
explicitly to a signed type, for example `-(octet as i64)`
for one `u8`.

An arithmetic operation between two variables requires the same type for
both operands. If the types differ, an explicit conversion is
for example, to `compteur: i32` and `octet: u8`, we write
`compteur + (octet as i32)`.

In an operation between an already typed integer and an entire literal,
The typed operand fixes the type of the literal, whatever its side.
If the literal value is not representative in this type,
the compiler refuses the expression. For example, with `octet: u8`,
`octet + 1` calculated in `u8`, tandis que `octet + 256` is refused.
A literal that fits in the type does not exempt from checking the
The result of the operation.

With a floating operand already typed, a floating literal takes the type
`f32` ou `f64` The context of an operation does not change
Not the family of a literal. `mesure: f32`, `mesure + 1.` is
admitted in `f32` and `mesure + 1` is refused.

In an arithmetical expression composed solely of literals
The recipient's annotation sets the type of calculation.
and intermediate results must be maintained in this type.
`let total: u8 = 200 + 55;` is allowed.
`let trop: u8 = 200 + 56;` is refused compilation.
Without the required type, the calculation between whole literals is done in `i64`.

The compiler uses the C operators for calculation. For integers,
the result must be representative in its Crust type, in accordance with
à [F5](../docs/FOUNDATIONS_AND_VECTORS.md#types-effets-et-contrôle).
The compiler diagnoses an error that can be statically established.
If not, it shall issue the necessary checks before any operation C
Indefinitely or any conversion that loses the calculated value.
in particular overflow and a null divider for `/` and `%`.
For example, if the result of `255 + 1` is of type `u8`, the calculation
fails, even if C can calculate `256` in a larger guy.
A proven check that is not necessary for the compilation may be omitted.

For a signed integer at the minimum terminal of its type, `minimum / -1`
is refused, because the quotient does not fit in this type.
`minimum % -1` Gives zero. `%`, the representativeness of the rest
The backend C must produce this zero without evaluating an operation.
C indefinite when quotient is not representative.

Zero division is refused for integers and floats,
Whatever the numerator. `f32` and `f64`, `0.0` and `-0.0`
both are null dividers. A division of which the null divider
is known to the compilation is diagnosed at that time. Otherwise,
the control takes place before the division at the execution.

As in Rust, the result of a floating operation is rounded to the
nearest representative value in the type of operation.
The last bit of precision pair sets the two values.
In `f32`, `16777218.0 + 1.0` donne donc `16777220.0`. Division
`1.0 / 3.0` gives an approximation.

Crust keeps errors of division by zero, overflowing to
the infinite and mathematically non-zero result that would round to
zero. An exact result zero, like `0.5 - 0.5`is allowed.
[Rust floating arithmetic](https://doc.rust-lang.org/core/primitive.f32.html)

The compiler rejects the transaction if it can establish the error at the
compilation. Otherwise, the program stops running when it
This rule applies regardless of the target generated.
Integration is postponed.

<a id="affectations-composées"></a>

## Composite assignments

`+=`, `-=`, `*=`, `/=`, `%=`, `&=`, `|=`, `^=`, `<<=` and
`>>=` use the same typing rules and checks as their corresponding
binary operators. The place must be mutable. It is evaluated once, even
if it contains a computed index, as in `array[index()] += 1`. The
result is written back only if the calculation succeeds.

The order is fixed, the location is determined and the validity is verified.
then we read its present value. Then we evaluate the right operand and
the calculation is checked before writing the result to the same location.
An off-limit access during location determination stops
the program prior to the assessment of the right operand.

During the right hand assessment, the location remains reserved.
right can read it as long as its borrowings end before writing
It cannot alter it, move it or destroy it.
A transferable access to another location is still possible if the
compiler proves that both locations are distinct.

The right of a composite assignment may suspend its execution.
The compiler must prove that the location and its reservation
remain valid until writing. The task status keeps
the location already determined and the old value already read.
the writing targets this same location without re-evaluating it.

<a id="comparaisons-numériques"></a>

## Digital comparisons

`==`, `!=`, `<`, `<=`, `>` and `>=` rendent un `bool`Two operands
The same type of difference is required for a type of difference.
One literal can take the type of the other operand
if he belongs to the same family and his value is representative there,
according to the rules of typing of the literals. `octet == 7`
type `7` in `u8` si `octet` is a `u8`, tandis que `octet < 256` is
refused.

<a id="conditions-et-logique-booléenne"></a>

## Boolean conditions and logic

The conditions for `if` and `while` exigent un `bool`. Negation
`!` and operators `&&` and `||` take type operands
`bool` and make a `bool`. To test if an integer is non-zero,
we write `n != 0`. Short circuit rules
[F4](../docs/FOUNDATIONS_AND_VECTORS.md#types-effets-et-contrôle) s'appliquent.

<a id="opérations-bit-à-bit"></a>

## Bit to bit operations

`&` (ET), `|` (OU), `^` (OR exclusive) and `~` (additional) operate on
The result retains the type and width of the operands.
The binary operators demand the same type on both sides and follow
the rules of typing the literals of arithmetic.
`~masque` d'un `u8` That's five worth 250.

In prefixed position, `&a` I'm still a loan.
`a & b` is a bit-to-bit operation. Comparisons bind stronger
que `&`, then `^` and `|`, which in turn bind stronger than `&&`
and `||`. To compare the result of a mask, we write
`(masque & 1) != 0`.

The mismatch `<<` and `>>` The number of integers is the number of integers.
positions shall be between zero and width of the type of
the left operand minus one. So, for a `u8`, `masque << 2` a un
number of valid positions and `masque << 8` The compiler is refused.
rejects a number of invalid positions he knows when compiling
and issues control to execution otherwise. Additions and subtractions
The difference between the two is more pronounced than the difference between the two.

The number of positions can be of any type integer,
independent of the type of the left operand.
type of the left operand. For example, a `u8` may be offset by a
type value `i64` if this value is between 0 and 7.

`a << n` calcule `a` times twice at power `n`. The result
must be within the type of `a`. Even with a number of valid positions,
an overflow is refused to compilation if it is known, if not controlled
for example, in the case of `u8`, `127 << 1` gives 254 and
`128 << 1` overflowing.

`a >> n` keeps the type of `a`. For a signed integer, bits
freed on the left are filled with the sign bit. For an integer not
signed, they are filled with zeros. `-3 >> 1` donne `-2` on
a signed integer and `5 >> 1` donne `2` on an unsigned integer.
[Rust reference](https://doc.rust-lang.org/reference/expressions/operator-expr.html#arithmetic-and-logical-binary-operators)

<a id="littéraux-dans-les-tableaux"></a>

## Literals in the tables

An already typed element can give its type to the literals of the table,
The other elements already typed must be
The literals follow the rules of compatibility.
family and representativeness. `octet: u8`,
`[1, octet, 3]` a the type `[u8; 3]`, tandis que
`[1, octet, 256]` is refused.

<a id="littéraux-aux-jonctions"></a>

## Literals at junctions

An already typed value can give its type to the literals of others
paths that provide the same result, whatever their order.
This rule applies to the branches of the `if`, with the arms of `match` and
to `break` which provide the value of a loop.
The lettering must be of the same type.
the same family and keep in this type. A path that leaves the calculation
without providing value does not participate in the choice of type.

<a id="indices-et-longueurs"></a>

## Indexes and lengths

`len()` on a table or slice returns a `u64`, quelle que soit
a table or an empty strip has a length equal to zero.
For example, `let vide: [i64; 0] = [];` donne `vide.len() == 0`.

An index of array can be of any type integer.
must be equal to or greater than zero and less than
The check is for the original value, before the
any internal conversion that could truncate it.
known limitations to compilation is refused. Otherwise, the compiler issues
a control at execution before access.

<a id="conversions-entières"></a>

## Whole conversions

`as` is reserved for conversions that preserve all values of the type
The rule applies to the type, including for a known value at the time of the
A representative literal can be directly typed, for example
`let octet: u8 = 42;`.

`try_from` perform other entire conversions and renders a `Result`.
`u8::try_from(n)` achieves with the original value for `0..=255` and
Report a mistake otherwise.

## Conversions entre flottants

`f32 as f64` is allowed. Each source type value is representative
exactly in the destination type. The same criterion prohibits
`f64 as f32`, including whether the value is known at compilation and
could be represented in `f32`.

`f32::try_from(valeur_f64)` renvoie un `Result`. Conversion succeeds
only if the value of the `f64` is exactly representative in `f32`.
A necessary rounding or an off-range value produces an error.

<a id="conversions-entre-entiers-et-flottants"></a>

## Conversions between integers and floating

The same criterion applies between the two families. `as` is allowed if
all source type values are exactly representative in
the destination type. `i32 as f64` is allowed. `i64 as f64` is refused,
even for a known and small value. A floating can't be
converted in full with `as`, because fractional values of the type
not all sources are fully representative.

In both directions, `Destination::try_from(valeur)` Only succeeds
if the value provided is exactly representative in the type
destination. `i64::try_from(3.0)` succeeds, while
`i64::try_from(3.5)` fails. `f64::try_from(9007199254740993)` fail
also, for this whole `i64` would require a rounding in `f64`.

<a id="erreur-publique-des-conversions-numériques"></a>

## Public Error in Digital Conversions

`Destination::try_from(valeur)` renvoie
`Result<Destination, NumericConversionError>` for all conversions
exact numbers. If the value cannot be represented exactly,
the result is `Err(NumericConversionError::NotRepresentable)`. Ce cas
covers a value outside the boundaries, a fractional part when a
conversion to an integer and any other loss of precision.

<a id="usage-dun-résultat-faillible"></a>

## Use of a failed result

Any fallible result must have explicit use, whatever its
content. Treat it in the logic of the program, transmit it or the
consume with `drop(-> ...)` met the rule. L-call alone followed by
`;`, `let _ = ...;` and a link never used is refused.
In a game, `Err(_)` can ignore the details of an error without
The rules of the
[brouillon 01](01-resultat-proprietaire.md) s’appliquent quand un motif
Removes a possessed allowance.

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

<a id="copie-dune-structure-locale"></a>

## Copy of a local structure

`copy(original)` on a local structure produces an independent value
of the same type on the default data stack. All fields must be
A copied shared reference retains its target and its
The content is still shared.

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

<a id="découpes-utf-8"></a>

## UTF-8 cuts

`&texte[debut..fin]` built a view `&str` with an excluded purpose.
The terminals are bytes positions.
`0 <= debut <= fin <= byte_len` and both terminals must be on
If disability is statically established, the programme
is refused. Otherwise, the control precedes the creation of the view and a failure
Stop the program with a diagnosis.

`texte.try_slice(debut..fin)` applies the same checks and makes a
`Result`. An invalid beach gives `Err(OutOfBounds)`. A valid range
of which a terminal cuts a character gives `Err(NotCharBoundary)`. The
success gives `Ok(&str)`, which borrows original bytes without copying.
The omitted terminal shapes use the same bounds as the hooks.

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

<a id="cas-refusés"></a>

## Cases rejected

| Cas | Ground for refusal |
| --- | --- |
| `n as u8` with `n: Int`. | The source type contains values that `u8` I'm not representing. |
| `u8::try_from(n);`, `let _ = u8::try_from(n);` or unused connection. | The result is bankrupt and requires explicit use. |
| `copy(original)` lorsque `original` contient un champ `&mut Int`. | The structure is not copyable. |
| `&"été"[..1]`. | The terminal cuts the first character. |
| Keep a view from `try_slice` beyond the life of his bytes. | The result keeps the source borrowing. |

<a id="règles-à-mettre-à-jour"></a>

## Rules to be updated

- **F5 and I5** for exact integer conversion and conversion
  faillible. [FOUNDATIONS_AND_VECTORS.md](../docs/FOUNDATIONS_AND_VECTORS.md) ·
  [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md)
- **U1 and L6** for explicit use or destruction of the result
  faillible. [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md)
- **ST17–ST18** for copying local structures and source of the
  copie. [STRUCTURES_METHODS.md](../docs/STRUCTURES_METHODS.md)
- **TX4 and E2**, with TX6 as the next rule, for the control of
  direct cuts and addition of `try_slice`.
  [UTF8_STRINGS.md](../docs/UTF8_STRINGS.md) ·
  [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md)
