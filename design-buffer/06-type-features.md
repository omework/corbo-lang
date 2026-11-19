[Français](06-type-features-fr.md)

<a id="brouillon-06--type-features-et-résolution-statique"></a>

# Draft 06 — Feature type and static resolution

Decisions validated in the workshop, to be integrated on request.

<a id="déclaration-et-portée"></a>

## Declaration and scope

One `type feature` is a structural constraint named which declares
It is used in function signatures.
Structure fields and collections remain concrete types
in this first version.

```rust
type feature Tracer {
    fn trace(&self);
}

type feature Ajoutable {
    fn ajouter(&mut self, valeur: Int);
}

type feature Fermable {
    fn fermer(-> self);
}
```

The recipient of the concrete method is written according to ME1. For example,
`fn fermer(-> self);` requires a method `fn fermer(self: -> Journal)`
on `Journal`. Its calling consuming keeps the notation of ME4,
`(-> journal).fermer()`.

The declaration `type feature` replace the proposals for annotations
`#(type, ...)` and `#(types, ...)` The contracts to be awarded in the case of
The relationship between the two is a major factor in the development of the
require the same concrete type of argument to be deferred.

<a id="résolution-et-vérification"></a>

## Resolution and verification

- A type satisfies a feature when it provides the signature method
  The compiler selects the method at the compilation.
- Two arguments that bear the same feature may have types
  The compiler checks and solves each separately.
- Direct and indirect requirements must be guaranteed by the
  signature. Body can call the method declared on the value
  It can also change this value to a function whose
  The guarantee is already satisfied.
- The feature describes the signature of the method.
  d) borrowings and dependencies are deducted from the concrete method solved
  and integrated into the call contract.
- A feature may appear in a return type if the compiler
  can determine the specific type of result.
  borrowed retains its specific type and its original borrowing.

## Exemple admis

```rust
type feature Tracer {
    fn trace(&self);
}

struct Console {
    niveau: Int,
}

struct Journal {
    compteur: Int,
}

impl Console {
    fn trace(self: &Console) {
        print(self.niveau);
    }
}

impl Journal {
    fn trace(self: &Journal) {
        print(self.compteur);
    }
}

fn tracer(tracer: &Tracer) {
    tracer.trace();
}

fn tracer_deux(a: &Tracer, b: &Tracer) {
    tracer(a);
    tracer(b);
}

fn tracer_et_renvoyer(tracer: &Tracer) -> &Tracer {
    tracer.trace();
    return tracer;
}

fn main() {
    let console = Console { niveau: 1 };
    let journal = Journal { compteur: 2 };
    tracer_deux(&console, &journal);

    let resultat = tracer_et_renvoyer(&console);
    print(resultat.niveau);
}
```

`tracer_deux` solves each argument to its concrete method, to
through the relay `tracer`. `resultat` is a `&Console`.

<a id="cas-refusés"></a>

## Cases rejected

| Cas | Motif |
| --- | --- |
| Declare two methods in `type feature Tracer`. | A feature contains exactly one method. |
| Switch to `tracer` a value without method `trace` conforme. | Constraint requires the mode of the recipient and the signature declared. |
| Appeler `tracer.flush()` in a body that receives only `&Tracer`. | The method is missing from the available warranty. |
| Pass the same `&Tracer` a function that requires `flush`. | The indirect requirement is absent from the signature. |
| Declare a field `sortie: Tracer` ou `sortie: &Tracer`. | The features are reserved for signature of functions. |

<a id="directive-de-région"></a>

## Regional Directive

The rating for the Regional Directive is
`#(directive, stack_region_max_size=1M)`. The spaces around `=`
are optional. The first word after `#(` identifies the category
The features type has their own declaration.

<a id="règles-à-compléter-lors-de-lintégration"></a>

## Rules to be completed when integrating

- **I5, B4 and B5.** Introduce the named structural constraints
  in signatures. Keep track of modes, effects and
  sources by means of contracts of determined methods.
  [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md)
- **ME1, ME2 and ME4.** Link the three recipient modes reported in
  a feature of signatures and calls for concrete methods.
  [STRUCTURES_METHODS.md](../docs/STRUCTURES_METHODS.md)
- **G6 and P2.** Update the syntax of the region directives.
  [GROWING_REGIONS.md](../docs/GROWING_REGIONS.md) ·
  [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md)

Examples of design examined on paper.
