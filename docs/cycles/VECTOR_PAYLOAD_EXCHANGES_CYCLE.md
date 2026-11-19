[Français](VECTOR_PAYLOAD_EXCHANGES_CYCLE-fr.md)

<a id="cycle--graphes-des-charges-dans-les-résultats-de-vecteurs"></a>

# Cycle — Graphs of loads in vector results

<a id="portée-et-règles"></a>

## Scope and rules

Suite of VECTOR_PAYLOAD_OPTIONS_CYCLE.md, according to H1–H3, VE2–VE4, B1–B5/B4c,
D1–D3, F2–F4 and U1. No normative change.
VALIDATION_GUIDELINES.md, the index of the seven drafts and the rules concerned
The tests remain focused on the cases selected.
and direct regressions; the independent adversarial campaign remains separate.

Synchronous signatures Result<A<Item>,A<Item>> and Result<(),A<Item>>>
now transport the borrowed/owner field graphs in the
The original pool and address of each object remain
Variations each retain their own dependencies.

<a id="implémentation"></a>

## Implementation

- FunctionResult porte `exchange_values`, static description of the load of
  each variant. This information is produced when a graph is required;
  simple trades continue to use their contract of origin.
- Analysis of results maintains internal paths `ok/…` and `err/…` in
  The parameters, relays and projections. These paths are not a
  new syntax of language.
- The stress analysis solves the fields and descendants of each load
  with the real sources, then restores the right load to the consuming match.
- The auditor shall terminate both contracts before publishing the transfer of the vector.
  It then composes the overall contract from the concrete graphs of these two
  variants, including descendants inherited from a transferred parameter.
- Symbolic parameters and call results keep prototypes
  The body control examines the actual load of each of the two
  variant, without assigning variants of an object to Ok(()) that contains nothing.
- The identity of the stored capacities is kept at the move of a load.
  When a conditional mutation retains the same charge as an alternative
  In the vector, this loan is not counted as a second independent loan.
  Field-derived access re-uses this identity; other borrowings
  and direct access to the target remains verified.

The runtime and C format of the results do not change.
connection of static metadata and their controls.

<a id="cas-ciblés"></a>

## Targeted cases

Seven methods: **14 executions C** after verify_program and compile_source,
and **18 programmes invalides** refused to go to both entrances.

- Replaces with valid/invalid index: output 7/9, two item cleanings in total.
- Back then relay; arrow required at call.
- Item owning Inner that borrows Int, directly and via a relay: the
  Two results are performed, with two destructions of each type.
- Drop each of the premature targets refused; the target of a descendant is
  also protected after return.
- Try_push in a 1 MiB area available or full; Ok(())/Err(Item), relay,
  re-use of pool d
  The filler allocates 131072 handles to this host.
- Load containing &mut Int: read by the allowed load, read/write
  Directly from the targets refused before consumption. Build a second loan
  independent mutable to the same target remains refused.
- Transfer of the result to a parent, with destruction of the vector child; a
  pool d'Item child too short is refused.
- Direct drop of the result of the operation, explicit use required, double
  - the consumption refused.

<a id="défauts-rencontrés"></a>

## Faults encountered

The first case was admitted after the direct contract was connected.
The following trials have shown three metadata losses:

1. The load of a Result was not rebuilt in stress analysis,
   which made a call to the descendant Inner impossible.
2. The overall contract lost the pool of a descendant inherited from the input parameter,
   while the charge from the vector retained its own.
   now after separate resolution of the two variants.
3. The verifier assigned a variant of the object to the empty Ok(()) branch,
   and had twice the mutable capacity moved during a replacement
   The controls now cover actual and actual costs.
   The identity of the loan retained; internal controls remain active.

The original logs and expectations are kept.
Intermediate `vector-payload-exchanges-nested-diagnostic.log` identifies both
sources of descendants, one of whom was missing from the contract.
control without removing its error; it is not a native test.

<a id="exécutions-et-traçabilité"></a>

## Executions and traceability

- Probe of the case recorded: C executed, output 7, code 0,
  `validation/vector-payload-exchanges-first-o0.log`.
- Initial O0 targets: three methods, 1.849 seconds and 1.903 seconds, one failure at each
  test; third test, three methods, 2,847 s, code 0.
- Fourth attempt: six methods, 3.287 seconds, two failures.
- Fifth, sixth, seventh: six methods, 4,659 s, 4,657 s,
  4,633 s, a mutable failure; eighth: six methods, 4,852 s, code 0.
- Final Target O0: **seven methods, 6,890 s, code 0**,
  `validation/vector-payload-exchanges-targeted-ninth-o0.log`.
- Regression O2: **159 methods, 158,585 s, code 0**, selection
  `validation/vector-payload-exchanges-test-selection.txt`, journal
  `validation/vector-payload-exchanges-regression-o2.log`.

C11, pthread, Wall/Wextra/Werrar and fatal UBSan. The program previously refused
`validation/open-vector-payload-exchange-contract.crust` is now executed
The C and the current contract
are archived in `validation/vector-payload-exchanges.c` and
`validation/vector-payload-exchanges-contract.json`.

Snapshot : `/tmp/crust-before-vector-payload-exchanges`. Patches and fingerprints
the three modules and the test: `validation/vector-payload-exchanges-changes.json`.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Unions of provenance remain conservative. This lot does not show all
correlations between variants, dynamic positions and recursive graphs.
General nominal references, returns of entire vectors using
and the integration of these burdens async still needs to be completed.
is `validation/open-vector-payload-container-contract.crust` : the manufacturing of
Vector<A<Item>> borrowing an Int injected remains explicitly refused to both
entries, associate log kept.

Reset remains removed from normal profile. No new independent model or
The previous models have been replayed: eight
combinations of lifespans (one admission and seven refusals), and four
storage combinations (four admissions and four refusals), no change
They do not model new exchange capabilities. Neither tests nor tests are possible.
UBSan is not a general proof of safety. The overall objective remains active.
