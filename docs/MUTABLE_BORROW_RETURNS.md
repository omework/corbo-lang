[Français](MUTABLE_BORROW_RETURNS-fr.md)

<a id="retours-demprunts-mutables--exclusivité-et-durabilité"></a>

# Transferable debt returns: exclusivity and sustainability

Later extension: [fields &mut Int](MUTABLE_REFERENCE_FIELDS.md) are now available; the measures below describe this historical cycle.

Cycle of 2 November 2026, validated by the user with writing `let mut vue`.
Rules B5/B1–B3/D1/D3 in [LANGUAGE_RULES.md](LANGUAGE_RULES.md),
[Matrix of 66 rules](VERIFICATION_MATRIX.md) and
[validation guidelines](VALIDATION_GUIDELINES.md).

## Comportement

```rust
fn borrow_mut(data: &mut Int) -> &mut Int {
    return data;
}

let mut memory = Pool<Int>::new(1);
let mut nombre = new(memory) Int(10);
let mut vue = borrow_mut(&mut nombre);
vue.set(30);
nombre = 40; // Après le dernier usage de vue.
```

The result uses the same allocation, at the same address. No new object
or location, attachment transfer, reception or destructive is not
The syntax does not add & to the reference
received. [Complete programme](../examples/mutable_borrow_returns.crb) shows the
addresses, relay, re-take of the original name and drop/reset.

Before last viewing use, access number directly, modify it, change the
move, drop or reset its pool is refused. The name of the reference can
be mutable as requested in the example; its writing ability comes from
However, according to the distinction already made with let mut, the type of the Int type is the same.
An &Int entry, even if declared mut, cannot provide a &mut Int result.

A child loan may be suspended by a child who is not a child.
exclusivity; a shared child suspends the parent's incompatible writings.
Chains are kept in relays and nested calls, even without
After the child's last use, the parent resumes
ses accès sous réserve des autres emprunts. Deux arguments mutables qui peuvent
The same allocation cannot be prepared together.

A conditional outcome holds all its possible targets.
be alive and attached to the parent scope or an ancestor at each border.
Their exclusive capabilities and sources are protected, even if the path
A local object or a transfer received by transfer
I don't want to get out of the way by borrowing, even if his pool survives.
or implicit promotion is not added.

<a id="analyse-et-traduction-c"></a>

## Analysis and translation C

The parser, symbolic results and contracts now distinguish
`mode: mut` shared result. Identities `reference_targets` are
The inference requires provenances from the
&mut Int; parameters the opaque verifier also refuses a forged contract
which promises a mutable result from a shared parameter.

The C remains a return of `Cell *` The descriptors of the
reference are purely static and are not recorded as allowances
or cleaning responsibilities. Mutable results can be provided
directly to parameters compatible with a call expression; a & added
a reference remains an unsupported nested reference, without flattening.
A mutable result can be restricted to reading by a &Int signature.

The calculation of loans shall identify a single binding for each possible target.
He keeps his mode on secondary targets and follows parents in the
This distinction avoids both the need to count
a double aliases and implicitly reduce an exclusive secondary loan to a
a result used directly as an argument also participates in the
suspension of his parents while he has no name in the scope.
The arguments already prepared remain protective during the next assessment.
The runtime, slot layout and cleaning pointers are unchanged.

<a id="écart-confirmé-corrigé-pendant-le-cycle"></a>

## Confirmed deviation corrected during cycle

The last-use control still dealt with any assignment of a name as
a replacement, despite the content mutation introduced in the previous cycle:

```rust
fn make(memory: &mut Pool<Int>) -> <- Int {
    let data = new(memory) Int(10);
    return <- data;
}

let mut memory = Pool<Int>::new(1);
let mut nombre = make(&mut memory);
nombre = 20;
```

This program was wrongly rejected as a result received without explicit use.
A content writing uses the object and does not replace binding.
The analysis now distinguishes this case from the mode of binding and the type of
RHS already available in the signature/contract, without opening a function body.
It continues beyond these scriptures to follow the following practices.
Replacements and reallocations of references remain the purpose of the binding
Previous. The regression covers literal RHS and scalar function result,
the unique destruction with content 20 and a future mutable loan that must
No rules have been released for this purpose.
The programme has been aligned with the already adopted V4/U1.

<a id="validation-exécutée"></a>

## Validation executed

The previous cycle had 672 successful methods in each configuration.
The 28 new methods pass their targeted controls.
[nouveau corpus](../validation/mutable-return-fixtures.json) recense **28 programmes
separate admissions and execution**, and **58 separate programmes refused** both
by `verify_program` and `compile_source`. Additional tests check
backend abstracts, opaque contracts and a deliberately false contract.
These accounts concern this corpus, not all programmes of global follow-up.

The independent model uses 24 seeds (0–23), sets of indices of
leaves, parameter permutations, unions and 1–4 relays. He reads
not the compiler's decisions or summaries. **12 programmes
valid executed and 12 invalids refused**, then compares the modified values
on the concrete path. Fixed tests cover in addition successive parents,
children shared, &Int fields, nested calls, prepared arguments, let mode /
let mut, local targets, drop/reset, re-used slot, loops/continue, history
of source and early return cancelling the call and releasing its prepared loans.

Five selected errors are detected in temporary copies: result
opaque read downgraded, secondary loan downgraded to read, loss of a
mutable parent, acceptance of a contract that can be transferred from a shared parameter,
and erroneous ending of binding on a content writing. Reading tests
prohibited use a subsequent reading of the result, without counting on a
The first is that the first step is to make sure that the
exclusive protection, even when operations C themselves would be
valid readings. No overall detection rate is deducted.

The 24 mistakes of the previous cycles are replayed.
omission of direct result targets had initially become inapplicable
with the expression now common to the ref and mut modes: the campaign has
The [incident]](../validation/mutable-return-initial-mutation-anchor.json)
The point has been adapted, without changing the fault or his assertion,
The campaigns were then re-launched with consistent prints.
finished results are referenced below; inapplicable injection status
is not counted as a detection.

Five C campaigns (mutable returns, content, shared returns, porters and pools)
each have three programs in O0, O2, Os and O2+UBSan: **60 executed in accordance with**.
They compare values, addresses, destruction, resets, reuse and failures
The end of a loan does not prematurely release the allowance: the case
exhaustion keeps the first slot alive and stops without unfolding the
The instrumental configurations stop at the first diagnosis
UBSan; none is issued. Only one family C is available. The example CLI is
also executed, without implicit instrumentation by CRUST_SANITIZE.

Rapports : [mutations nouvelles](../validation/mutable-return-mutations.json),
[let](../validation/mutable-return-let-mutations.json),
[reference values](../validation/mutable-return-value-mutations.json),
[shared returns](../validation/mutable-return-direct-mutations.json),
[porteurs](../validation/mutable-return-holder-mutations.json),
[champs](../validation/mutable-return-field-mutations.json),
[C mutable](../validation/mutable-return-c.json),
[C contenu](../validation/mutable-return-content-c.json),
[C shared](../validation/mutable-return-direct-c.json),
[C porteurs](../validation/mutable-return-holder-c.json),
[C pools](../validation/mutable-return-pool-c.json).
The overall suites are complete: **700 standard tests passed
(461.15 s)** and **700 sous UBSan (460.252 s)**,
Without any unsolved jump or failure, the previous models and oracles are part of the
The execution of these acts. **29 selected mutations detected** ; leurs
The prints correspond to the final Python of the project.
[bilan brut](../validation/mutable-return-suites.json) conserve commandes, sorties,
The repair of the injection site does not take place during the course of the injection.
changes neither the compiler nor the methods of testing the ongoing suites.

## Limites

Returns &mut Int only, without nested reference, field projection
mutable, stored field &mut, transit graph, user destroyer, recursion,
Async or FFI. The target model is limited and does not formalize all loans.
Inference, auditor and backend remain in the trust base.
ASan is not restarted: his previous failure on this host also occurred
with an empty C program. The configurations of the same family do not replace
The CLI launcher is not being used by the
seule variable CRUST_SANITIZE ; voir [SAFETY.md](SAFETY.md).
No general evidence of security is claimed.
