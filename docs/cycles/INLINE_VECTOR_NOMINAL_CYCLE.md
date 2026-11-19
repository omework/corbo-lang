[Français](INLINE_VECTOR_NOMINAL_CYCLE-fr.md)

<a id="cycle--références-nominales-dans-les-cases-de-vectort"></a>

# Cycle — Nominal references in Vector cells<T>

<a id="règles-et-périmètre"></a>

## Rules and scope

VE1–VE3, ST7/ST11–ST18, B1–B5, T4/T5/T6 and AS2/AS8/AS11–AS13
The validation instructions and the index of drafts have been kept unchanged.
was re-enacted in this continuation, as well as FOUNDATIONS_AND_VECTORS.md and
STRUCTURES_METHODS.md. The full specification was read in the work
no new normative choices or rule changes.

The previous batch connected the borrowing graphs in the online boxes.
This batch connects their existing representation for the nominal references,
In particular, the entire targets and substructures.
and other vector operations remain open.

<a id="implémentation-et-baseline"></a>

## Implementation and basic

validation/inline-vector-nominal.crust was refused by verify_program and
compile_source for explicit layout restriction: database retained
under the same prefix. The initial snapshot is in
/tmp/crust-before-inline-vector-nominal, without duplication of Python caches.

Both generators now accept the references fields already represented.
The path async also requires that the structure belongs to the recognized layouts.
The copy of the mutable references remains refused.
the previous batch of the catch contracts and graphs shall be reused.
No conversion between T and A<T>, no target allocation, no change
Runtime is introduced.

<a id="vérifications-exécutées"></a>

## Audits performed

Targeted O0/UBSan: **11 methods, 4,833 s, code 0**, i.e. 11 executions C
successful and 20 invalid variants checked at both entries.
Journal : validation/inline-vector-nominal-targeted.log.
The first crossing also discovered nine imported tests from the previous batch:
20 methods, 8,771 s, code 0. L-import of the module was corrected to ensure that the
new target n  , runs only its own classes, without changing the assertions.

Cases allowed: entire and internal nominal reference, copy/remove, destruction
carrier and vector before reading the target, separate mutable field,
Mutilable re-borrowing, construction in a child, nested structure, insertion
injected, copy/return and relays remove, async body with yield, capture
owner and result extracted by join, re-use of vector slot.

Denied cases: mutation/destruction of target before last use, destruction
bearer during a mutable reborrowing, copy of a mutable field, child target
too short, destruction of the target before join and before reading the result.

Regression O2/UBSan: **121 methods, 79,234 s, code 0**, in
validation/inline-vector-nominal-regression.log. The 44 fingerprints of the compiler
and tests are unchanged during the passage, check recorded in
-integrity.log. Selection and initial prints are kept in
-selection.txt and -start.json. The batch diff and the prints before/after
are in -nominal.patch and -nominal-changes.json.

Replayed families cover online vectors, contracts and captures,
stored nominal references, async returns and recursive projections.
No new failures in this selection.

<a id="inspection-de-la-traduction"></a>

## Translation inspection

C stored in validation/inline-vector-nominal.c uses
sizeof(CrustStructureView) for each nominal reference and field code
3. The descriptor keeps the root and the shift of an inner target.
boxes receive bytes of layout; removes them in a structure
local. Access to fields passes through existing memcpy primitives;
the boxes are not delisted as tables C of descriptors.
The cleaning of the carriers does not destroy the targets borrowed.
substructures check the offset and the reservation of paths.

## Limites

The evidence relates to the listed cases, without any general evidence of security.
The conservative tracking of positions after certain calls/branches remains the same
The recursive references and all nominal types are not
not declared covered by these examples. The proprietary fields, pop/replace,
try_push, slices and push_new of online structures remain to be connected.
Reset remains removed by default. No mutation campaign or search
extended adversary; no independent lab results are assumed.
C native C11/pthread, Wall/Wextra/Werrar and fatal UBSan via the existing harness.

<a id="prochain-écart-reproduit"></a>

## Next deviation reproduced

validation/inline-vector-owned.crust contient Item{value:A<Int>}, un push,
the removal, destruction of the vector and the subsequent re-use of the
pool Int. Both entries still explicitly refuse to do so:
validation/inline-vector-owned-baseline.log. This case remains open; cleaning
descendants will have to be transferred with the box, without destroying the children
when the local carrier is released from consumption.
