[Français](REFERENCE_VALUES-fr.md)

<a id="créer-un-emprunt-et-utiliser-une-référence-existante"></a>

# Create a loan and use an existing reference

Later extension: [back &mut Int](MUTABLE_BORROW_RETURNS.md) are
The restrictions and measures below describe the
Historical cycle perimeter, with raw and print sources retained.

User's decision of November 2, 2026: keep clear reading of
`&`, in calls and returns. This cycle corrects the shortcut that was processing
`&reference` as a reborrowing to the target without any additional level.
References: B4/B5 and I1/V2/V3/P9 in [LANGUAGE_RULES.md](LANGUAGE_RULES.md),
[guidelines](VALIDATION_GUIDELINES.md), [matrice](VERIFICATION_MATRIX.md).

<a id="écritures-retenues"></a>

## Writings

```rust
fn inspect(data: &Int) -> Int {
    return *data;
}

fn borrow(data: &Int) -> &Int {
    return data;
}

fn relay(data: &Int) -> &Int {
    let mut view = borrow(data);
    return view;
}

let mut memory = pool<Int>(1);
let mut data = new(memory) Int(42);
let mut view = &data;
let mut a = inspect(&data);           // Crée un emprunt depuis l'allocation.
let mut b = inspect(view);            // Fournit l'emprunt existant.
let mut c = inspect(borrow(view));    // Le sous-appel fournit déjà un emprunt.
print(a);
print(b);
print(c);
```

`inspect(&view)` and `return &data` lorsque `data` is already a &Int parameter
add a reference level. The prototype does not implement references
nested: these expressions are refused, without flattening or conversion
Pointer to target. `return data` transmits the loan received. A return
which creates a loan from a local allowance remains refused for its duration
Even if the pool survives.

The signature retains the type and mode of passage. An allowance requires
encore `&`, `&mut` ou `->` selon l'intention ; `inspect(data)` is refused if
`data` means the allowance. A loan received does not become a access having,
The returns allocated retain their `<-` explicite.
General assignments `let mut alias = view` between references are not
added by this clarification of calls/returns.

An existing mutable access is also via its name.
remain suspended while using by subcall; &Int result
prolongs the read restrictions until it is last used.
mutable can thus provide read access announced by `-> &Int`, without creating
a second mutable access. Climbing a shared loan to &mut is refused.

Pools follow the same rule:

```rust
fn make(memory: &mut Pool<Int>) -> <- Int {
    let mut data = new(memory) Int(42);
    return <- data;
}

fn forward(memory: &mut Pool<Int>) -> <- Int {
    let mut data = make(memory); // memory est déjà un emprunt de pool.
    return <- data;
}
```

Call from a local pool is still `forward(&mut pool)`. Reading capacity
does not become mutable by name transmission. &Int fields are consistent:
`field: &data` from an allowance, `field: view` from a named reference.
The pattern `match &value` remains the specific syntax for reading the current match;
This cycle does not redefine its grammar into general expressions.

<a id="vérifications-conservées"></a>

## Audits retained

Targets and their sources are not displaced. Children's borders →
parent remains controlled without implicit promotion. All alternatives
A conditional return is followed, as are their mutable parents.
A name-slide reference also protects its target when a next argument
is evaluated. A return reference remains linked to the history of its resets.
The target; it is not treated as a new allocation.

Before last use, drop, reset, displacement and mutation are incompatible
after this last use, drop/reset and re-use of the slot remain
The pointer format and runtime C
do not change; there is no new allocation or destruction for the only one
receipt of a reference.

The call verifier accepts the names of the already existing references and
&Int results of subcalls, while refusing the name of an allowance not
The source parameters now bear the fact that
The inference of the
effects also checks the local source/parameter distinction.
results and constraints refuse operators & on references.
Contextual Treatment `returning_reference` was deleted from the compiler.
The verification path remains modular; the backend C remains specialized.

<a id="validation-et-état-des-preuves"></a>

## Validation and status of evidence

The previous cycle had 632 successful methods in standard and UBSan.
Fifteen new methods deal with forms of call/return, references
The main objectives of the project are to:
Their perimeter includes **8 programs admitted to be executable** and **23 cases refused**
by the auditor then the compilation, plus an inference control only
on a function returning & reference. These accounts describe the fixtures
They do not include all programs within the overall suite.

The fixtures of the previous tests and their generators were migrated to the
The input graphs, set of expected targets, seeds,
values and traces of destruction expected have not been changed.
[migration](../validation/reference-values-fixture-migration.json) keep the
method names and second expressions of the comparisons of assertions
for 23 Python files saved before migration. This is not a
automatic proof of preservation of each oracle. An old diagnosis
`emprunter directement` was updated in `emprunt imbriqué`, keeping its
programme interdit.

Previous bounded models are reused: pool roads (40 seeds),
&Int field boundaries (32 scenarios), carrier returns (24 seeds) and
direct returns (24 seeds) and their program returns use
names of the parameters borrowed without changing the predictions of their oracles.
The cleaning models and the running C oracle are also part of the suites.

Five specific mutations are detected in temporary copies:
flatten a reference in the result inference, allow implicit borrowing
dismiss a valid named argument, reject a named return
valid and forget that a pool parameter is already borrowed.
previous changes in fields, carriers and direct returns are also
The four campaigns keep Python prints of the project.
This is not an overall detection rate.

Campaigns C direct returns, porters and pool contracts each have
12 performances: three programs in O0, O2, Os and O2+UBSan. **36 executions**
meet their defined observations (values, addresses, destructions, resets)
and burnout diagnoses), without UBSan diagnosis.
C compiler is available. The CLI example of direct returns is also available.
executed with `return data` and relays by name; this CLI execution is not
instrumented by `CRUST_SANITIZE`.

Rapports : [mutations nouvelles](../validation/reference-values-mutations.json),
[mutations retours directs](../validation/reference-values-direct-mutations.json),
[mutations porteurs](../validation/reference-values-holder-mutations.json),
[mutations champs](../validation/reference-values-field-mutations.json),
[C retours directs](../validation/reference-values-direct-c.json),
[C porteurs](../validation/reference-values-holder-c.json),
[C pools](../validation/reference-values-pool-c.json).
Both global suites are completed: **647 tests passed in mode
standard (420.021 s)** and **647 sous UBSan (420.331 s)**.
No test is jumped and no failure is left unresolved in these executions.
The [gross balance](../validation/reference-values-suites.json) conserve commandes,
Python outputs, durations, configurations and prints.

The gross reports of previous cycles retain their old sources and
fingerprints. Documentary examples have been migrated to the current syntax;
historical measures are not presented as executions of the code
During migration, a quick audit compiled the cases admitted and then
C; its jumps and meters of incomplete models are not
The final suites perform the entire tests.

## Limites

No &&Int support, reference to local scalar variable, return
&mut, reference references, transit graph or general assignment
The subset is synchronous, without recursion or FFI.
Life expectancy errors remain denied rather than compensated by a
promotion, a change in source or an implicit byte displacement.
Models and paths remain limited; inference, verifier and backend
are part of the trust base. Optimization levels C do not replace
not an independent family of compilers. ASan is not restarted, counts
held from the previous failure of this host even on an empty C program; see
[SAFETY.md](SAFETY.md). No general proof of security is claimed.
