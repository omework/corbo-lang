[Français](UTF8_STRINGS-fr.md)

<a id="crust--str-char-et-string-utf-8"></a>

# Corbo — str, tank and thong UTF-8

Decisions validated in discussion, recorded on November 5, 2026.

Normative extension of [LANGUAGE_RULES.md](LANGUAGE_RULES.md), in addition to the
[structures and methods](STRUCTURES_METHODS.md) and
[growing regions](GROWING_REGIONS.md). The initial recording was
The medium implemented since then and its limits are followed in the
[matrice](VERIFICATION_MATRIX.md) and cycle reports. Examples
Normative measures alone do not constitute proof of execution.

<a id="1-texte-octets-et-valeurs-unicode"></a>

## 1. Unicode text, bytes and values

**TX1 — str and static literals.** The name chosen is `str` tiny.
`&str` is an immutable view of a valid, representative UTF-8 byte sequence
by an address and a length in bytes. A literal as `"été"` is stored
in the program's static data: its bytes are immutable and live
He doesn't ask for pool slots or drop.
need for a null terminator to delimit the view; ABI detail remains to be defined.

The double quotes accept JSON exhausts
`\"`, `\\`, `\/`, `\b`, `\f`, `\n`, `\r`, `\t` and `\uXXXX`.
`XXXX` contains exactly four hexadecimal digits. Two exhausts
Unicode can form a pair of substitutes for an off-the-plane character
Multilingual basic. An isolated substitute, an unknown escapement or a character
Uncode characters can also be written
direct, for example `"é"` and `"\u00e9"` give the same UTF-8 bytes.

**TX2 — Separate Octet and tank.** `u8` is an unsigned integer of 8 bits.
`char` means a Unicode scalar value, not necessarily a character
A letter and a combined accent can be two `char`.
Reading an byte never realizes implicit conversion to `char`. Un `char`
decoded is a value independent of the bytes that were used to produce it.

**TX3 — Longueurs explicites.** `texte.byte_len()` provides the length used
In bytes of `str` or `String`. `caractere.utf8_len()` provides the number
bytes of the UTF-8 encoding of this `char`, 1 to 4. This is neither an account
of visual characters, or necessarily of the size of the representation of the
type `char` in memory. `"été"`, byte_len is 5 and the positions of the tanks
are 0, 2 and 3.

<a id="2-indexation-découpes-et-conversions"></a>

## 2. Indexation, cuttings and conversions

**TX4 — Explicit cut and loan.** A cutting expression means a
portion of `str` ; the hooks do not automatically create a reference.
We write `&texte[debut..fin]` to obtain a `&str` without copy, with purpose excluded.
Forms `&texte[..fin]`, `&texte[debut..]` and `&texte[..]` are authorized;
the omitted terminals are 0 and byte_len. The conditions are
`0 <= debut <= fin <= byte_len`, with two terminals on UTF-8 borders.
The view cannot survive the original bytes; the existing borrowing rules
a type annotation does not introduce the `&` manquant.

`&texte[..2]` for `"été"` a the type `&str`, not `&[u8]` : the type of receiver
and its API determine the output view. Internal storage in bytes does not allow
not to elude the UTF-8 borders from a text cut.

Statically established disability is denied. Otherwise, the control precedes
the construction of the view; a failure stops the program with a diagnosis.

`texte.try_slice(debut..fin)` applies the same checks and makes a `Result`.
An invalid beach gives `Err(OutOfBounds)` ; if the beach is valid but a
terminal cuts a character, it gives `Err(NotCharBoundary)`. Success gives
`Ok(&str)` without copying bytes. The omitted terminals use 0 and byte_len.
The result retains the borrowing constraints of the source; U1 imposes its
explicit use, even in case of known error. Decision of draft 07.

**TX5 — Index simple d'octet.** `texte[i]` returns the value `u8` at the position
in bytes; `&texte[i]` fournit `&u8`, not `&str`. Access requires
`0 <= i < byte_len`, but not a tank boundary : a byte of continuation
This access is retained on the `&str` and `String`. They do not decode
the text and remain subject to the terminal checks.

**TX6 — char_at.** `texte.char_at(index)` decode a tank starting at this index
in bytes and returns `Result<char, CharAtError>` :

- `OutOfBounds` if the index is negative or greater than or equal to byte_len;
- `NotCharBoundary` if the target byte is not the beginning of a tank.

The end of the text does not contain a tank, even if it is a valid border
for a cut. There is no rounding to any other heading or allocation.
The method was introduced for `&str` ; any additional shortcuts
on `String` shall not introduce a hidden conversion or copy.

**TX7 — Converting whole text to char.**
`char::from_str(texte)` retourne `Result<char, CharFromStrError>`. The text should
contain exactly a Unicode scalar value. Errors are `Empty` and
`MultipleChars`. `"é"` gives a chariot despite its two bytes; `"été"` fails.
This conversion never silently ignores the rest of the text.
does not allocate or retain any borrowing in the char result.

**TX8 — Validation from bytes.** `str::from_utf8(&octets)` retourne
`Result<&str, Utf8Error>`. Success builds a view without copy, after
encoding validation; error does not automatically replace bytes
The details of the `Utf8Error` The reference obtained shall be kept open.
the constraints of duration and sharing of source bytes.

<a id="3-string-et-stockage-grandissant"></a>

## 3. Thong and growing storage

**TX9 — String encapsule Vector<u8>.** `String` has growing storage
based on a `Vector<u8>` and displays a text-oriented API, with a
Invariant: the accessible content is still valid UTF-8.
mechanisms with the vector does not automatically expose all its operations.
Its default construction produces empty text.

This architecture decision does not in itself approve the entire API
generic `Vector<T>`. The first case on its empty construction is only
proposed at the time of this check-in.

**TX10 — Pool, region and cleaning.** `Pool<String>` provides slots containing
fixed information; the growing associated storage uses strategies
data stacks/regions already retained. `textes.new()` construit un String vide.
The current annotation is `#(directive, stack_region_max_size=1M)` before a telescope; the
old names proposed are no longer to be used.
limits and stability remain those of G1–G12.

The destruction of String cleans up its associated storage and restores its slot,
without double cleaning. Subsights or dependent tasks can prevent
the destruction according to the existing rules. The exact internal protocol between
pool of descriptors and region still to be implemented; no hidden reallocation
on another allocator is not authorized by these decisions.

**TX11 — push(char).** `texte.push(caractere)` add the full tank encoding
at the end of the text. Before writing, all encoding must hold in the ability
available. No addition leaves an incomplete UTF-8 sequence and elements
The operation requires compatible mutable access
With the borrowings. An overrun follows the policy of limits already retained.

**TX12 — View from String.** `let vue: &str = &texte[..];` borrows the content
a Thong without copying or transferring its responsibility for cleaning.
subviews use the same cuts as TX4. Muter the String is refused if
the view must still be used after this mutation. The last rules
use and boundary of scope are inherited, not re-arbited here.

**TX13 — push_str.** `texte.push_str(source: &str)` copy the bytes of the text
source at the end of the content. The source remains available; its storage is not
not transferred. The capacity of the full addition is verified before any write.
The result remains valid UTF-8 and the already present items do not move.
Receiver and arguments follow the borrowing restrictions already established.

**TX14 — pop.** `texte.pop()` remove the last full tank and return
`Option<char>` : `Some(caractere)` ou `None` for an empty chain. None is a
In the case of enum, not a zero reference. Bytes retained are not moved.
The length decreases and the space removed becomes reusable in the region;
the region remains reserved for the String until its cleaning. The result is a
independent value.

<a id="4-mutation-doctets-et-stabilité"></a>

## 4. Byte Byte Mutation and Stability

**TX15 — replace_byte.** `texte.replace_byte(index, octet)` retourne
`Result<u8, ByteReplaceError>`. Success replaces the byte and restores its value
previous. Errors are `OutOfBounds` for a negative or at least equal index
at byte_len, and `InvalidUtf8` if the resulting text would have invalid encoding.
All checks before the modification; failure leaves content
The index can be a continuation byte. Length and length of the index can be the same.
addresses of other bytes remain unchanged.

**TX16 — replace_bytes.** `texte.replace_bytes(debut, source)` remplace un bloc
by the source bytes, without insertion or deletion. The replaced block contains
exactly as many bytes as the source. The interval must hold in the
current length, with calculations of valid sizes; the resulting text must
be valid UTF-8. Return is `Result<(), ByteReplaceError>` with the same
cas `OutOfBounds` and `InvalidUtf8`. Success does not provide a collective copy
old bytes; failure does not alter anything.

The source is consulted by borrowing (e.g. `&tableau_octets`) The result
the whole block is validated before modification: do not replace this operation
by a replace_byte suite that would require valid intermediate steps.
The number of floats can change, not the length in bytes or the addresses of the
Bytes retained. Replace C3 A9 (`é`) by 61 62 (`ab`) is thus authorised.

**TX17 — No raw mutable access.** Reading `texte[i]` and shared borrowing
`&texte[i]` are allowed. Get a `&mut u8` on the bytes of the thong is refused,
even with a mutable receiver; a function could otherwise bypass the
validation UTF-8. L'affectation directe `texte[i] = octet` is also refused.
The scripts go through the controlled methods of the String API.
The internal exposure is not mutably so as to circumvent this invariant.

**TX18 — UTF-8, text meaning and offsets.** The guy guarantees encoding, not
the meaning of the text or the retention of its characters when replacing
Bytes. Midrange changes that require shifting bytes
next build a new thong; old storage remains stable
The cost of new allocation and copying must remain at the disposal of the applicant.
visible; both storages may coexist during construction.

The proposal to replace the car limited to replacements of the same width has not been
The intermediate wording "any change in the environment requires
a new String" has been specified by the authorisation of bytes replacements
constant length with validation of the result.

<a id="5-copie-affichage-et-parcours"></a>

## 5. Copy, Display and Route

**TX19 — No structural copy of String.** String is not Copy because he
has its growing storage. A structure that contains a String is not
So not structurally Copy. `copy(original)` and `pool.copy(original)` are
refused for a Thong: duplicate its descriptor does not duplicate its storage.

Duplicating the text requires a new Thong with independent storage.
operations already retained are sufficient: build a destination, then
`destination.push_str(&original[..])`A future duplication method may be used
grouping these transactions, with explicit cost and source of allocation; its name
and its signature is not yet fixed.

**TX20 — Display by type.** The building print accepts a `&str` for
transmit UTF-8 text and one `char` to display a Unicode value, without
implicit conversion between these two types or creation of a temporary String.
Showing a &str containing a single tank does not require converting this text to
For a Thong, the loan is explicit: `print(&texte[..])` ; l'appel
`print(texte)` is not automatically converted into a loan.
already existing print are not withdrawn by this case.

Str storage is a sequence of bytes, but its type carries the
UTF-8 warranty. The display can transmit these bytes without building a
Char collection. The output API representation remains distinct from the
storage of String.

Generic iterators and methods `chars()`/`char_indices()` have been
The explicit loop course with char_at and utf8_len is sufficient for the
prototype design. On already valid UTF-8, check a border and then
decode a tank at a byte position requires up to four bytes: this
operation can be O(1), and a complete O(n) bytes course with O(1) of
Auxiliary memory. These are algorithmic objectives, not measurements or
performance of an already executed implementation.

<a id="6-exemples-de-conception"></a>

## 6. Design examples

<a id="extraction-explicite-et-frontière-invalide"></a>

### Explicit extraction and invalid border

```rust
fn main() -> Int {
    let texte: &str = "été";
    let premier: &str = &texte[..2];
    print(premier);

    match texte.char_at(1) {
        Ok(caractere) => { print(caractere); return 1; },
        Err(CharAtError::OutOfBounds) => { return 2; },
        Err(CharAtError::NotCharBoundary) => { return 0; }
    }
}
```

The text has five bytes. Position 1 is readable with text[1], but does not start
The types of errors used here are the numbers of the selected API,
not additional statements made by each programme.

<a id="remplacement-groupé-valide-sans-étape-intermédiaire-exposée"></a>

### Valid group replacement without exposed intermediate step

```rust
fn main() -> Int {
    #(directive, stack_region_max_size=1M)
    {
        let mut textes = Pool<String>::new(1);
        let mut texte: String = textes.new();
        texte.push_str("été");
        let octets: [u8; 2] = [0x61, 0x62];

        match texte.replace_bytes(0, &octets) {
            Ok(()) => {},
            Err(erreur) => { return 1; }
        }

        print(&texte[..]); // abté
        print(texte.byte_len()); // 5
        drop(-> texte);
    }
    return 0;
}
```

<a id="duplication-indépendante-pas-de-copie-de-descripteur"></a>

### Independent duplication, no copy of descriptor

```rust
fn main() -> Int {
    #(directive, stack_region_max_size=1M)
    {
        let mut textes = Pool<String>::new(2);
        let mut original: String = textes.new();
        original.push_str("é");

        let mut copie: String = textes.new();
        copie.push_str(&original[..]);
        copie.push('!');

        drop(-> original);
        print(&copie[..]); // é!
        drop(-> copie);
    }
    return 0;
}
```

<a id="7-propositions-reportées-et-statut"></a>

## 7. Deferred proposals and status

- `truncate_bytes` and its type of error were proposed, without validation
  explicit before reorientation to a classic String API; they do not
  are not added to the transactions retained in this document.
- The additional traditional methods are based on a text-oriented API.
  Re-arbitrate only new selections for allowances, offsets, indexing and
  UTF-8 invariant; the general rules already adopted apply automatically.
- The iterators and both methods of route remain deferred.
- Detail of Utf8Error, exact signatures of bytes views and ABI of types:
  The cutting policy is validated
  by draft 07 and recorded in TX4.
- Converting String/Vector consumers and dedicated duplication method:
  no additional APIs are deducted from the internal representation alone.
- The vector emptys even when T has no fault, the other rules of
  vector and complements to String are recorded in
  [FOUNDATIONS_AND_VECTORS.md](FOUNDATIONS_AND_VECTORS.md).

Historical status at the editorial level: TX1–TX20 were **N: not implemented,
not verified by execution in this pass**. The current status is
in VERIFICATION_MATRIX.md; UTF8_TRY_SLICE_CYCLE.md cycle covers
synchronous integration of the fallible cut of draft 07. Evidence of fixed tables, fields and old pools does not
do not constitute evidence of UTF-8 validity or their interactions with
Thong. See the [matrix]](VERIFICATION_MATRIX.md) and
[rapport documentaire](cycles/UTF8_STRINGS_CYCLE.md).

## Borrowed splitting

`text.split(separator)` is available on `String` allocations and `&str` views.
The concrete STD iterator is `std::text::Split`; its method
`next(&mut self) -> Option<&str>` returns views into the original text.
The equivalent free function is `std::text::split(text, separator)`.

- Matching uses literal, non-overlapping separator occurrences.
- Leading, adjacent and trailing separators preserve empty pieces.
- Empty text produces one empty piece for a non-empty separator.
- An empty separator produces empty pieces at both ends and one piece per
  Unicode scalar value, rather than per grapheme cluster. Empty text then
  produces two empty pieces.
- Exhaustion is permanent: further `next()` calls return `None`.
- The text and separator storage must outlive matching. Yielded pieces borrow
  the original text independently of the iterator cursor. Advancing or dropping
  the iterator does not invalidate them. Mutation and destruction of their
  backing text remain subject to the ordinary borrowing rules.

The iterator is a fixed-size descriptor. It allocates no strings or piece list.
Literal matching uses a forward byte scan, with worst-case O(n × m) comparisons
for text length n and separator length m; no Unicode normalization is applied.

The implementation is in [the STD source](../stdlib/src/text/split.crb).

## Bounded inline UTF-8 strings

**TX23 — Compile-time byte bound.** `String<N>` is an inline UTF-8 string
whose maximum content length is `N` bytes, known at compile time. The accepted
syntax supplies an integer literal as the type argument, for example
`String<64>`. The bound counts encoded bytes, not Unicode characters or grapheme
clusters. It is part of the type: different bounds designate different types.

Storage contains the current byte length and a fixed `N`-byte payload, including
unused bytes when the content is shorter than its bound. The payload is inline:
it is not a descriptor pointing to growing storage. Its footprint is fixed and
known at compile time, including length metadata and alignment; it is not
necessarily exactly `N` bytes. A containing fixed-layout row can therefore have
statically determined field offsets and row width.

Every valid value satisfies `0 <= byte_length <= N`, and the used payload is
valid UTF-8. Content exceeding the bound is rejected, never silently truncated.
There is no implicit allocation of larger storage or fallback to growing
`String`. The STD provides the following explicit operations:

| Operation | Result |
| --- | --- |
| `String<N>::new()` | Empty inline value, without a pool or growing allocation. |
| `String<N>::try_from(text: &str)` | `Result<String<N>, BoundedStringError>`; copies complete UTF-8 or returns `TooLong`. |
| `value.set(text: &str)` | `Result<(), BoundedStringError>`; replaces content, preserving the prior value on `TooLong`. |
| `value.len()` / `value.capacity()` | Current byte length / fixed maximum, as `usize`. |
| `value.as_bytes()` | An immutable byte slice tied to the value's storage. |
| `value.as_str()` | `Result<&str, std::text::Utf8Error>`; validates and borrows a text view without copying. |

Use `std::String` through normal imports or qualified paths. The source template
is `std::BoundedString<N>`; the public `String<N>` spelling selects its concrete
layout. The API is implemented in [collections.crb](../stdlib/src/collections.crb).
`as_str` uses the existing checked UTF-8 conversion rather than adding an
unchecked text-construction primitive.

Plain `String` retains its existing growing, region-backed representation.
TX9–TX19 and TX21 describe that growing type; they do not impose its storage or
copy classification on `String<N>`. The existing general ownership, borrowing
and lifetime rules apply to bounded values and references to their content.
No new implicit conversion or copying rule is introduced.

Example schema (declarations only):

```rust
struct Customer {
    id: u64,
    email: String<254>,
    display_name: String<64>,
    country_code: String<2>,
    active: bool,
}
```

The bound alone does not enforce an exact length, ASCII-only content, or a
business format such as an email address. The current implementation stores a `usize` length followed by `[u8; N]`;
construction and replacement zero unused payload bytes. Native alignment/padding
still contributes to the footprint. This layout is not a portable, frozen disk
format, and padding bytes are not an encoding contract. Define disk fields and
byte order explicitly with [binary encoding](BINARY_AND_TIME_API.md).
General constant-generic declarations and named constant arguments are not
introduced by this literal syntax extension.

**Status:** implemented in corboc and the STD through ordinary fixed-layout
record specialization. Focused execution/refusal evidence and platform limits
are recorded in [the integration report](cycles/BINARY_TIME_BOUNDED_CYCLE.md).
This is not a general safety proof.
