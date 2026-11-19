[Français](FOUNDATIONS_AND_VECTORS-fr.md)

<a id="fondamentaux-allocations-typées-et-vecteurs"></a>

# Fundamentals, typed allowances and vectors

Next String site decisions. The following identifiers are used for
link expected behaviour to the verification matrix.

<a id="types-effets-et-contrôle"></a>

## Types, effects and control

- **F1 — Taille finie.** A recursive definition is allowed if each cycle
  passes through a known size indirection, for example `A<T>` ou `&T`.
  A cycle of directly stored fields is refused.
- **F2 — Match.** One match covers each variant or remaining variants
  via `_`. Un match consommant exige `match (-> valeur)`. The arm receives
  values moved. A game by borrowing binds fields according to mode
  shared or mutable subject. The arms that provide a result
  an arm that leaves the function does not provide
  result at the junction. A consuming pattern `_` is refused if it does not
  an allowance owned, including when it hides an entire variant.
  The arm links the owner's content to a name with explicit use
  (U1, draft 01). The check is for type, even when
  the variant produced is known.
- **F3 — Junctions and exits.** A use after a junction is
  Allowed if valid on each path that reaches it.
  The following iteration shall be satisfied.
  exit joins other exit routes, including the possibility of
  zero iteration for one `while`. The result of a return is assessed and
  transferred before cleaning, from inside to outside, and then
  See S4, S5, S5a, T9 and T10.
- **F4 — Order and short circuit.** The arguments are evaluated from left to
  a right and a displacement takes effect before the next argument (B4a).
  `&&` evaluates his right operand only if the left is true. `||`
  the evaluation only if the left is false. The analysis of the effects follows the
  possible assessment paths.
- **F5 — Controlled arithmetic.** The whole operation gives a
  result representable or fail. An established failure to compile is
  Statically diagnosed. A division by zero or overflow
  determined at the execution stops the program with a diagnosis before
  Operation C dangerous.
  For entire conversions, `as` is reserved for conversions
  which preserves all source type values, even if the expression
  converted is a constant. A representative literal can receive
  directly a type, for example `let octet: u8 = 42;`.
  Other conversions use `try_from` and make a `Result` :
  `u8::try_from(n)` succeeds in `0..=255` and reports an error if not.
  The [scratch 07](../design-buffer/07-conversions-resultats-copies-et-vues.md#conversions-entre-entiers-et-flottants)
  applies the same criterion of accuracy between floating types and
  between whole and floating.
  For floating arithmetic, the
  [brouillon 07](../design-buffer/07-conversions-resultats-copies-et-vues.md#opérateurs-arithmétiques)
  defines the rounding of results and cases where the calculation fails.

## Allocation explicite

- **H1 — Representation.** `Pool<T>.new(...)` fournit un `A<T>`, one
  non-copy value that refers to the initialized object and its original pool.
  The move transmits both information and responsibility
  unique cleaning, with the same object address. The pool must
  survive any recipient of this responsibility.
- **H2 — Access.** `*a` reads by copy if `T` is Copy.
  content no Copy out of `A<T>` is refused. `ref()` and `mut_ref()`
  You can borrow the handle, `vref()` and `mut_vref()` borrow the content.
  Un `&mut A<T>` allows to replace the handle after evaluation of the
  replacement, with cleaning of the old allowance. `&mut T`
  allows to modify the content at the same address.
- **H3 — Methods.** Methods and hooks are used directly
  The type of an element read remains that of the variable of allocation.
  the declared element, including if it is another handle.
  receveur consommant distingue `self: -> A<T>` of the `self: -> T`.
  The consumer call is written `(-> a).methode()`. For content
  comparable, `a.vequals(b.ref())` compares the contents.

## Vecteurs

- **VE1 — Uniform storage.** Un `Vector<T>` contains a prefix
  initialised of type-type boxes `T` and starts empty, even if `T` n'a
  No default value. `Vector<Int>` stores values in its
  cases. `Vector<A<Int>>` Stores the handles. A vector of borrowings.
  Stores the loans and spreads their constraints.
  The type of cells is fixed without inference of pool or
  automatic conversion between value and handle.
- **VE2 — Insertion and destruction.** `push` copy a Copy element and
  receives an explicit transfer of a non-Copy element.
  un `A<T>` supports its cleaning from its original pool.
  Two boxes can therefore designate different pools. Move one
  Transferable borrowing in a box preserves its exclusivity. Destroy the
  vector cleans its present elements before recovering its storage.
- **VE3 — Extraction and replacement.** `pop` produit `Option<T>`.
  `remove` keeps the order of the remaining items and reports an index
  The adjustments are not valid.
  moving a box of handlers leaves their targets
  to the same address. `replace(index, -> valeur)` renvoie l'ancienne
  value in case of success, or entry in case of invalid index, without
  modify the vector in the latter case. The new value is ready
  before replacement. Each extract handle retains its origin and
  a result not Copy requires an explicit transfer. The result owner
  can be consumed directly with `drop(-> opération(...))` : the operation
  is evaluated first, and its content is destroyed once
  before the next instruction, regardless of the pool of origin.
- **VE4 — Bornes and publications.** `try_push(-> valeur)` returns the
  Incoming value if the vector is full. The Owner Result imposes U1
  even when success is known; drop only destroys content
  owned by the variant actually produced. For bytes, `try_extend`
  publishes the whole block or leaves the vector intact with
  `CapacityExceeded`. Writings beyond length do not become
  Once initialized, an external reading can fill
  space available and distinguish from received bytes, end of flow and
  space exhausted. An error leaves the length unchanged.
  the destination lasts as long as the reader can access it.
- **VE5 — Tranches.** `&v[debut..fin]` is a view `&[T]` on one
  semi-open interval checked. The two mutable slices of
  `split_at_mut(index)` access via the parent loan
  is suspended until one of the two slices is used.
- **VE6 — Initialization on site.** L'API retenue `push_new()`
  initialize a new box with the default value of `T` and
  Then return a transferable loan from this box.

<a id="placement-et-chaînes"></a>

## Placement and chains

- **GR1 — Placement.** The fixed descriptor occupies the data stack
  The content grows in a region of the data stack to
  regions. Each cursor has a single direction of growth.
  L’annotation `stack_region` fixe `max_size` and, optionally,
  `count`. Legacy, transfers and the use of a stack
  to dedicated regions follow G1–G12.
- **GR2 — Recovery.** A region is a substack with its own
  cursor. Its cleaning can pull this cursor back after destruction
  areas released from the end may be
  indexed for reuse. The external cursor moves back on one end
  The growth of a vector leaves the elements already free.
  in place at their address.
- **TX21 — Thong representation.** `String` provides its text API
  above a `Vector<u8>` online and keeps the UTF-8 invariant.
  A text view is contiguous in the direction of increasing addresses.
- **TX22 — Concatenation.** `push_str(&str)` borrows the source text.
  `destination.merge(-> source)` Concatenates and consumes the source Thong.
  Responsibility for cleaning the source is transferred to the operation.
  Storage limits remain applicable and API does not specify
  no saving of copy or memory peak.
