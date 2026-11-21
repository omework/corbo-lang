[Français](MUTABLE_REFERENCE_FIELDS-fr.md)

# Champs contenant un emprunt mutable

**Mutable-access update:** [MA1–MA6](MUTABLE_ACCESS.md) supersede exclusion
inferred from `&mut` alone. Exclusion examples and verdicts recorded in earlier
cycles below are historical evidence, not the current access-compatibility rule.
Permissions, validity, synchronization and branch completion are separate checks.


Cycle of 3 November 2026, after explicit validation of the rule. Procedure:
[guidelines](VALIDATION_GUIDELINES.md), [rules](LANGUAGE_RULES.md),
[matrice](VERIFICATION_MATRIX.md).

<a id="règle-et-périmètre"></a>

## Rule and scope

```rust
enum Writer { Bound { data: &mut Int } }

fn make(writers: &mut Pool<Writer>, data: &mut Int) -> <- Writer {
    let writer = new(writers) Writer.Bound { data: data };
    return <- writer;
}
```

The manufacturer shall receive `&mut nombre` from a mutable allocation, or name
an existing mutable loan. `&Int` does not provide this capability.
The field is fully initialized, without nested reference or conversion
silent. The object retains exclusivity on each possible target up to
its last use, including uses via a reference to this object.
read the target by its original access, modify it, move it,
The parents' restrictions and the
sources go through return contracts and successive transfers.
Each target must already live in the parent or an ancestor at each border;
no implicit promotion is added.

Several shared references to the same object retain one capacity
They do not create separate, mutable borrowings. `match &writer`
projects the field in reading, with a filiation to this capacity; this
projection does not make original access to the target available.
The transferable and reassignable fields are not implemented at this stage.

After last protective use, original access or parent reborrowing
becomes available according to its own rights. This does not destroy the object
porteur. Un `drop` explicit of the bearer counts as use; its destroyer
implied demonstrative does not read the field and does not extend this borrowing.
Destroyers reading their references would require control
additional L4 and remain outside the prototype.

<a id="vérificateur-contrats-et-c"></a>

## Auditor, contracts and C

Field statements distinguish between shared and exclusive modes.
contracts infer the identities of the targets and substitute them for calls,
maintaining the capacity required by each field. A returnable field must be mutable.
come from a mutable parameter or already mutable field. Alternatives
conditionals retain all targets and the strongest restriction
The opaque calls continue to be checked without reading the bodies.
Backend C remains specialized and maintains its consistency controls.

The calculation of loans includes aliases of the same holder by identity
The readings planned are children of this capacity; the
filiation retains the prohibitions of access by the original names.
arguments and fields already prepared remain protective during the evaluation
the following expressions, from left to right.

The two reference types are represented by `Cell *` in C, loaded and
stored via `memcpy`. The calculation of size and offset considers well &mut Int
as a pointer, including between Int fields. There is no new
Dynamic borrowing control: the capacity distinction is static.
The pool runtime and destruction order remain unchanged.

<a id="réexamen-global"></a>

## Global review

The 66 existing rules were reviewed by families:

- I1–I5/V1–V5: explicit intent, initialization, lack of copy
  of allocation, access mutability and stable identity.
- S1–S6/T1–T11/U1 : activations enfant → parent, transferts successifs,
  conditional returns, receptions, loops/continues and use of results.
- D1–D4/B1–B5/B4a–e: sustainable targets without promotion, target sets,
  exclusivity, last use, prepared arguments, types and opaque contracts.
- L1–L7/A1–A6/P8/P9/E1: destroyer before release, global order of
  cleaning, drop/reset, source, reuse and depletion of pools.
- P1–P7/E2 and future parts of other rules: no implementation
  new early placement, dynamic growth, two-slider ranges,
  macros, tables, recursion, competition or safe FFI.

New interactions are carried out on the aliases of the bearer,
shared projections, mutable reborrowing parents, returns and relays, variants
conditionals, interlocked transfers, drop/reset of both pools, replacement,
arguments and initializers with effects, loop recovery and re-used slots.
Previous tests remain applicable to compatibility backends.

<a id="contre-exemple-confirmé-et-correction"></a>

## Confirmed counter-example and correction

The audit found a gap between the actual type and a capacity descriptor.
The descriptor newly used to borrow a mutable field carrier
The program was in the Int type by default and was accepted:

```rust
enum W { Bound { data: &mut Int } }
// p: Pool<Int>, q: Pool<W>, n: allocation Int mutable.
let mut w = new(q) W.Bound { data: &mut n };
let x = new(q) W.Bound { data: &mut w }; // Doit être refusé : w est W.
print(x);
```

The reference was a w target, but the field type control was
Int. The descriptor now retains the type of its actual target.
&mut W to &mut Int and &W to &Int; a mutation that erases
this correction is part of the dedicated campaign. No rule change
was not necessary: V2, B4 and P9 already imposed this distinction.
Campaigns launched before this correction are not the final results.

<a id="validation-exécutée"></a>

## Validation executed

The dedicated suite includes **29 tests**. Its registered corpus contains **24
separate sources accepted and executed**, and **43 separate sources refused**
by `verify_program` and `compile_source`. An additional check built
an auditor with only contracts to test the reset of a
field target, without body table. [exact sources and results](../validation/mutable-field-corpus.json)
[Final global follow-up]](../validation/mutable-field-suites.json) passent
**729 standard tests (700.596 s)** and **729 in UBSan configuration
(701,048 s)**The two previous executions, launched before
correction of the type of descriptor, have been interrupted and are not
The results of the survey were counted as final results.

The **Six dedicated injections** are detected: exclusively degraded capacity,
lost exclusive parentage, wrong pointer offset, projection parent
forgotten, unprotected prepared field and actual type of descriptor erased.
The **29 previous injections replayed** are also detected.
35 injections selected on temporary copies, without overall rate
Inferred. Prints of all Python files from compiler and tests
The final version for the seven campaigns is the same.
[Measures and links to each campaign](../validation/mutable-field-summary.json).

Two first tests were not sensitive to injection: the
Reset remained refused by the source constraints despite the absence of a loan from
field prepared, and access to the original name remained protected by a second control
Despite the deterioration of a secondary loan. The first one is now confronted
in the case of two mutable fields, aliased; the second at readings by both
mutable parents of a conditional result, keeping the assertions
The initial reports and incidents are retained.
[separately](../validation/mutable-field-incidents.json) ; they are not counted
The new assertions on readings of the
The parents were also executed in the baseline of the corresponding campaign.

**48 executions C** The report also notes that the
three programs, each in O0, O2, Os and O2 with UBSan without recovery.
The new family exercises mixed layout, identity of addresses, return of
carrier, aliases, reset, reuse and exhaustion; the other three replay
shared fields, return of borrowing objects and direct mutable returns.
UBSan diagnostics fail these controls.
Stop the program without unfolding the destroyers, in accordance with E1.
Compiler available: Homebrew Clang 20.1.3. One family C.

The global configuration `CRUST_SANITIZE=undefined` Instruments binary
built by the harness of tests and runtime oracles. This variable
does not automatically instrument each binary produced by the LTC; the
campaign C dedicated directly passes UBSan options to compiler C.

The independent model uses a protective range: an operation on the
the target is allowed only after the last use of the bearer.
381 product 24 scenarios, 12 admitted and 12 refused, with reading, writing, drop
The oracle does not consult the contracts or the compiler's decisions.
This is a limited model, without general prediction of the borrowing graphs.

An old expectation refused any &mut Int field declaration.
is replaced, in accordance with user approval; the control that the
&Int fields remain readable in the tests.

## Limites

No formal proof of security or comprehensive coverage of compositions.
The stored references only target Int; no transitive graph of enums,
cycle, embedded reference or destructive user. Projections are in
reading and the match bodies keep their grammar restricted.
targets and variants remain conservative, without a general correlation of
paths. Selected scenarios generated and mutations do not constitute
an overall measure of coverage.

C executions use a single compiler family available on
This host; they do not compare independent C implementations.
remains unavailable on this environment, according to the previous failure even on
an empty C program; it was not presented as being executed in this cycle.
UBSan provides an observation of the instrumental paths, without general proof.
