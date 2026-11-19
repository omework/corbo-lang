[Français](TYPE_FEATURES-fr.md)

<a id="type-features--règles-retenues"></a>

# Type features — rules adopted

Integration of draft 06 validated. This document is normative; it describes the
rules, not an assertion of implementation coverage.

**TF1 — Structural declaration.** `type feature Nom { fn methode(&self); }`
declares exactly one method. `&self`, `&mut self`
and `-> self`, corresponding to the concrete signatures of ME1. The name and the
full method signature must match; parameter names
The constraints on the
methods remain carried over to the lines.

**TF2 — Scope.** A feature is a constraint in a function signature,
not a type of storage erased. Structure fields and elements of
collections remain concrete. Two parameters bearing the same feature are
independently resolved: they can receive different concrete types.
Constraints requiring a level playing field between parameters are deferred.

**TF3 — Body guarantees.** On a forced parameter, the body cannot
call that the method guaranteed by its signature. It can transmit this
value at another call only if the available guarantee satisfies
The requirement of this call. An additional method of the concrete type chosen
does not make valid a body that requires an absent guarantee of its signature.
This includes indirect requirements and function relays.

**TF4 — Static resolution and contracts.** The compiler chooses the method
The changeover by value and the borrowing rules
The effects, origins and
d) borrowings and dependencies are derived from the contract of the concrete method
resolve; the feature alone does not invent a neutral effect contract.

**TF5 — Concrete result.** A feature may be included in the return type
when the compiler determines the specific type of result.
The same is true of the real type.
and its origin, with the verifications of B5. The feature does not authorize
implicit promotion or extension of the life of its target.

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

Historical annotations `#(type, ...)` and `#(types, ...)` do not report
The regional directive falls under G6 and uses the category
`directive`.
