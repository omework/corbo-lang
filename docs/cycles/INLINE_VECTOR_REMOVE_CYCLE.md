[Français](INLINE_VECTOR_REMOVE_CYCLE-fr.md)

<a id="cycle--extraction-de-structures-stockées-directement-dans-les-vecteurs"></a>

# Cycle — Extraction of structures stored directly in vectors

<a id="règles-et-portée"></a>

## Rules and scope

Suite of INLINE_STRUCT_VECTORS_CYCLE.md. VE1–VE4, ST17/ST18, T1/T6,
B1–B5/B4a, ME1/ME2, F2–F4 and TF1–TF5 remain unchanged.
The index of drafts have been read; VALIDATION_GUIDELINES.md has been read
The rules of extraction, storage and storage are all part of this continuous work.
the local, transfer and assessment of arguments were consulted.

`let point = <-v.remove(i)` removes a structure online, moves the boxes
The following results are not available:
A<Point>. The result can be released from a block, branch, loop or
d
does not have to survive this independent value in Int fields.

This lot retains the perimeter of the previous elements: Int sheets, structures
It does not end Vector's generalization<T>.

## Raccordements

- Reading/copying and extracting use the same local payload receipt.
  Remove requests mutable access and calls vector_remove, which preserves
  order; no modification of runtime C.
- Analysis of types, results and constraints know that extraction
  produces a fresh local structure, without dependence on the vector pool.
- Booking the result in the parent/appellant recognizes the producer
  removes, including behind a function, relay, if or break.
- Returns and direct drop keep consumption rating
  explicit. Static resolution of a feature type sees the Point type
  the result and refuses a incompatible signature.

<a id="défauts-et-corrections-pendant-le-lot"></a>

## Failures and corrections during the batch

The first connection had forgotten the result typed in the effects analysis
and used a bad field of abstract value of the results.
The direct break and direct return required
also explicitly retain the transferred transaction.

The second targeted pass did not complete the analysis of a function relay.
The process was confirmed alive, occupied the CPU and remained on that test;
it was explicitly interrupted (code 130). Its trace is preserved.
was the use of the identity of the tuple of operation rebuilt at each
The contract was constantly changing. The provenance is now
attached to the stable source node of the receiver of this call. The same relay ends
and runs in the next passes.

An initial test expectation was corrected according to ME1/ME2 and B4a:
`v.remove(v.len()-1)` tries to read the receiver while his loan mutable
The direct service is already provided to the external call. This program remains refused.
The test checks both the test and the test.
behaviors; no two-phase reservation is implicitly added.

<a id="tests-ciblés-exécutés"></a>

## Targeted tests performed

Eight methods, **15 executions C** (13 successes and two expected judgments on
index invalide), **8 programmes invalides** controlled by verify_program and
compile_source. The expected values are written independently of the compiler.

- Removal of the first element, length and order of the rest; result read after
  destruction of the vector.
- Take function and relay; local result is refused under signature
  A<Point>. A shared loan still used prevents the call from being mutable.
- Reception in a parent, both branches of the if, break with receiver, and
  output of a block containing the vector pool.
- Immediate consumption `drop(->v.remove(0))` and re-use at each iteration.
- Index prepared before the call, last use of a loan, refusal of access
  the recipient during his arguments and use after drop.
- Structures nestled on the second growth front and empty structure.
- Resolution remove via a feature type, incorrect signature refused.
- Index -1 and index equal to length: stopped diagnosed before reading.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_inline_vector_remove -v
```

Targeted final outcome: **8 methods, 5,127 s, code 0**, in
validation/inline-vector-remove-targeted-fifth.log. First log to fourth
are kept: first pass failed, second interrupted, third
still in failure, fourth successful on the first seven methods.

Native compilation: Clang C11, pthread, Wall/Wextra/Werrar and fatal UBSan.
The two terminal stops are expected and separate from a UBSan diagnosis.

<a id="régression-et-limites"></a>

## Regression and limitations

Regression O2/UBSan: **185 methods, 116,345 s, code 0**, selection in
validation/inline-vector-remove-test-selection.txt, journal
validation/inline-vector-remove-regression.log. The selection covers the
value carriers and handlers, contracts, functions, loops, copies and returns
local, features type and async extractions existing. Other families
unchanged are not systematically replayed.
The fingerprints of the compiler and targeted test remained unchanged during the period
The existing models of signatures and constraints of the
selected families are replayed; no new model of extraction
structurée n’est revendiqué.

The fields borrowed/owners, moving variables named in the
boxes, pop/replace/try_push, box and tranche borrowing, push_new and integration
Async of the online structures still to be connected.
keeps a pool source; this lot does not replace this semantics by
a copy online. No reset is reintroduced.

No new independent model, random campaign or mutations in
This lot. Native L-oracle controls the values and length of the sequence, the
refusal check the rules at both entries. UBSan and this selection does not prove
not the general safety of all compositions.

Reproduction: /tmp/crust-before-inline-vector-remove; patch and fingerprints
validation/inline-vector-remove.patch and validation/inline-vector-remove-changes.json;
fixture and C generated validation/inline-vector-remove.crust and .c.
