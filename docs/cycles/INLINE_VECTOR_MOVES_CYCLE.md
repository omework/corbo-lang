[Français](INLINE_VECTOR_MOVES_CYCLE-fr.md)

<a id="cycle--transferts-nommés-vers-vectort"></a>

# Cycle — Named transfers to Vector<T>

<a id="règles-et-périmètre"></a>

## Rules and scope

VE1/VE2, H1, T1/T4/T5, B1–B5 and AS2/AS8 remain unchanged.
AGENTS.md, VALIDATION_GUIDELINES.md and the index of the seven drafts were
read before validation, as well as the relevant rules
LANGUAGE_RULES.md, FOUNDATIONS_AND_VECTORS.md and STRUCTURES_METHODS.md.
The full specification was read in the previous continuous work.
No arbitration or normative change in this lot.

A named local value may be transferred by `v.push(->point)` in
A Vector, his old access becomes unusable.
is not implicitly converted into a Point; active borrowing prohibits
moving. Transfer from an external scope requires steps
the explicit provisions already adopted.

The perimeter remains that of Int, interlocked or empty leaf structures.
The other fields, operations and views remain open; this lot does not close VE1–VE6.

<a id="défauts-et-implémentation"></a>

## Failures and implementation

The two minimum sync/async programs were rejected because push
n , accepted that the AST form of constructions/copies, not transfer of a
The journal inline-vector-moves-baseline.log keeps these refusals.

The auditor and the async downsizing now recognize the transfer
appointed, check its local origin and invalidate its former access.
The vector receives the bytes of the fields, then the storage of the value
No change in runtime C.

The contract analysis deducts the local storage requirement from the argument of
Push from the actual Vector<T> receiver type. It re-uses values
No second assessment of the transferred argument.
requirements spread to synchronous relays and async captures.
also check the contents of the contracts and the refusal of an A<Point> calling.

The tests revealed two additional missing connections: the
explicit reborrowing `&mut *v` in the relay, and the representation of Cell
vector borrowed from the C bridge of a synchronous call from a task.
They are corrected without making borrowing implicit.

<a id="validation-ciblée"></a>

## Target validation

Seven test methods/test_inline_vector_moves.py: **15 executions C** and
**19 programmes invalides**, each checked with verify_program and
compile_source. Passage final O0/UBSan : **7 methods, 5.287 s, code 0**,
validation/inline-vector-moves-targeted-fourth.log.

- Former name read/destruct after transfer and missing arrow refused.
- Last use of the loan before push accepted; use after push refused.
- Synchronous relays called from hand or task; local requirements
  recorded in both contracts; A<Point> refused.
- Capture owner of a Point with borrowed vector mutably,
  suspensions before/after insertion; former Point and reserved vector refused.
- Explicit entry into a child block; value created in the child block;
  no downward transfer refused.
- Extraction and transfer between two vectors in a loop, cleaning
  and re-use of the pool; nested and empty structures.

The previous targeted passages are retained: first (two failures of
(re-borrowing refused), third (bridge C not connected).
The expectations of the programs were not changed to follow these refusals.

Native compilation by the existing harness: C11, pthread,
Wall/Wextra/Werrar, fatal UBSan; O0 optimization in target and O2 in regression.
Static refusals are not executed natively.

<a id="c-généré-et-traçabilité"></a>

## C generated and traceable

The validation/inline-vector-moves-sync.c and -async.c files are retained.
In the synchronous case, vector_push reads the fields before the source cell_drop;
the copy then extracted survives the vector drop. In the case async, the
the owner field of the state is returned to NULL before insertion; the temporary
is destroyed and then handed over to NULL, preventing its second cleaning at the end of
These inspections do not prove all possible paths.

Snapshot initial : /tmp/crust-before-inline-vector-moves.
Diff and fingerprints: validation/inline-vector-moves.patch and -changes.json.
Regression selection: validation/inline-vector-moves-test-selection.txt.
Pre-regression impressions: validation/inline-vector-moves-regression-start.json.

<a id="régression-et-limites"></a>

## Regression and limitations

The first O2/UBSan passage performed 126 methods in 77,308 s (code 1).
A test failed both entries only on the diagnostic text:
storage control correctly refused A<Point>, but displayed
T/A<T> generic names. The diagnosis now also indicates the nominal type.
The waiting for the existing test remains unchanged.
validation/inline-vector-moves-regression.log; prints unchanged during
this first passage in -first-integrity.log.

The same selection was successful after this diagnosis: **126 methods,
77,073 s, code 0**, validation/inline-vector-moves-regression-final.log.
The **44 empreintes** compiler and selected modules remained
unchanged during this passage (-regression-final-start.json, -integrity.log).
The selection covers the three previous batches of online structures, the
storage contracts, local async catches, carrier charges contracts,
sync/async handle vectors, feature type, T/A<T> strict returns and the
match consuming of join. Cartesian model independent of signatures of
type features, already present in this selection, also succeeded.
No mutation campaign or adversary research extended in this lot,
in accordance with the user priority. No new oracle independent of the
storage model; expected outputs, diagnostics and inspections C
No supposed results of the independent lab.
Successful passages are not a general proof of safety.
