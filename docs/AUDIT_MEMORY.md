[Français](AUDIT_MEMORY-fr.md)

<a id="audit-des-règles-du-vérificateur-et-du-c-généré"></a>

# Audit of Rules, Auditor and C generated

Targeted audit of November 2, 2026, on the subset actually implemented.
The reference rules are [LANGUAGE_RULES.md](LANGUAGE_RULES.md) and
related transactions contracts in [SAFETY.md](SAFETY.md). Cet audit conserve
These rules do not revalidate language choices and do not extend types of
or forms of borrowing accepted by the prototype.

<a id="écart-1--capture-trop-tardive-des-champs-denum"></a>

## Difference 1: too late capture of enum fields

Cross-example accepted before correction:

```rust
enum E { A { x: Int, y: Int } }
fn read(a: &Int) -> Int { return *a; }
let mut memory = pool<E>(1);
let mut temps = allocator();
let mut n = 10;
let mut e = new(memory) E.A {
    x: n,
    y: read(& {
        n.set(20);
        let mut a = new(temps) Int(1);
        <- a
    })
};
print(e);
```

The C was showing `E.A(20, 1)` for `E.A(10, 1)`. The auditor visited
initializers in the written order, but kept the name of variable C
for `x`. The actual reading of this variable was issued after the effects
of the initializer `y`. It is a deviation of valuation of values, without access to
a freed memory demonstrated by this counter example.

Each field value is now copied into a temporary C immediately
After his evaluation, before moving to the next initiator.
The sum of the fields is not shown in the table below.
allocated and made usable only after evaluation of the required fields; an output
pre-set in an initializer does not release partially initialized enum.

<a id="écart-2--identité-perdue-lors-dun-retour-conditionnel-uniforme"></a>

## Difference 2: Identity lost during uniform conditional return

Refused counter-example before correction:

```rust
fn forward(mut a: -> Int, n: Int) -> <- Int {
    if n == 0 { return <- a; }
    return <- a;
}
let mut memory = allocator();
let mut a = new(memory) Int(42);
{
    -> a;
    a = forward(-> a, 0);
    <- a;
}
print(a);
```

Without the `if` in `forward`The program was working. `if`, he was
The two paths did, however, make it possible to transfer them without a parent recipient.
the same allocation received as a parameter, without changing the address or source.

Reunion of conditional returns systematically removed identities
The appellant's selection of the descriptor was based on the following criteria:
uniform case, it broke correspondence with the import and access of the parent
This defect was an undue refusal, not an acceptance.
allowing access after destruction.

If all return routes make exactly the same allocation known
The auditor now retains his identity before the appeal.
other effects normally, then transfer the cleaning to the recipient.
The local allowances and candidates are not eligible for the allowance.
There is no copy of the selected descriptor.
no byte displacement, no runtime comparison of pointers to decide.

This storage also maintains the transfer markings already laid down and
The indicators of cleaning do not include the connections between interlocked imports.
keep no reference to a variable C of a finished function.

<a id="vérifications-ajoutées"></a>

## Checks added

[tests/test_audit_regressions.py](../tests/test_audit_regressions.py) comprend :

- The capture of fields before the following effects, including field order
  reverse, conditional branch and early return during initialization.
- The same identity returns for Int and enum, interlocking imports,
  Transfer markings, junctions and loop covers.
- The continued refusal of old names consumed and loans used after
  destruction; the candidates actually different remain cleaned once.
- A matrix of 30 attempts incompatible with a future loan, combining
  shared/mutable borrowing, transfer, transfer/destruct, reset, blocks,
  conditions and loops.
- An independent model of identity, values and orders of receipt: two
  deterministic seeds, three storage sources, 32 steps per program.
  Local movements, round-trips, appeals, destruction and destruction
  conditionals are compared to impressions and traces of the C executed.

The independent model does not read the auditor's statements or C to calculate
The existing oracle runtime of 3,000.
operations complete these checks for slots and sliders.

## Validation finale

371 tests pass in each of the two complete executions:

```sh
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
CRUST_SANITIZE=undefined PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
```

The 14 new tests are included, with their sub-cases and generated programs.
UBSan instrumentation covers binary data compiled by harness and oracle;
binaries built separately by CLI tests retain their options
as indicated in [SAFETY.md](SAFETY.md).

<a id="limites-du-constat"></a>

## Limitations of the finding

Searches for this pass did not produce a new confirmed example
after destruction or double destruction accepted. This does not demonstrate
The two corrected deviations relate respectively to the
the values executed and an undue refusal related to the identity of an allowance.

Features explicitly outside the sub-set (references in the
structures, returns of loans, recursions, external C calls, etc.) are not
The specialisation of functions at call sites
remains a known limit, not a modular verification guarantee.
ASan is still not validated in this environment; the limits of
the instrumentation is specified in [SAFETY.md](SAFETY.md).
