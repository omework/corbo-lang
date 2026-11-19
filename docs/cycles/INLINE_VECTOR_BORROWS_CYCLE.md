[Français](INLINE_VECTOR_BORROWS_CYCLE-fr.md)

<a id="cycle--champs-empruntés-des-structures-dans-vectort"></a>

# Cycle — Fields borrowed from Vector structures<T>

<a id="règles-et-périmètre"></a>

## Rules and scope

VE1–VE3, H1, T1/T4/T5/T6, B1–B5, ST17/ST18 and AS2/AS8/AS11–AS13
The following are the main indicators of the overall performance of the EU-15:
drafts were read, as well as the relevant rules; the specification
In the course of its work, no new arbitration or arbitration had been carried out.
Reset remains excluded by default according to PR1.

This batch extends the online structures to Int, &Int and &mut Int fields,
including interlocking structural sheets.
General nominal references, other transactions and tranches remain open.

<a id="défaut-initial-et-implémentation"></a>

## Initial failure and implementation

Inline-vector-borrows-sync.crust and -async.crust fixtures were refused
both entries; baseline in validation/inline-vector-borrows-baseline.log.

The boxes contain the bytes of the fields and the pointers borrowed, without
take over the destruction of targets. Representation and primitives
C are reused. The transfer invalidates the source and cleans its
old storage; its physical life does not become a dependence of the
However, the targets borrowed must survive the receiver.

The verifier follows the borrowing graphs by box. Remove transmits these
borrowings from the new bearer; copy copies shared references and refuses
the mutable references. The analyses of results and constraints retain
fields, insertion/extraction effects and vector reborrowing.
The C-bridge of synchronous calls since async builds the same symbolic graph.

The async lowering also keeps the borrowings stored.
The branches which are known to release only the box extracted.
do not establish the same positions, as well as mutator calls,
Back to the conservative set of targets. Control snapshots
keep this state; an expired inventory is not used after a call.
This loss of accuracy may still deny some valid programs.

<a id="défauts-rencontrés-pendant-limplémentation"></a>

## Deficiencies encountered during implementation

The first tests showed the loss of graphs in relays
by borrowing, then in the parameters of Bridge C. These paths are connected.
A negative async case via a relay was masked by direct use of the name
after drop. By removing this independent use, the wrong program was
accepted at both entries (inline-vector-borrows-contract-second.log).
The path of vector argument was treated as a scalar pointer by
metadata extractor; the path to borrowing d
The negative expectation was retained.

Two fixed amounts have been corrected: mutation via an explicit reborrowing named
rather than a field method not supported, and explicit readings
`*number` in the async code. The child target test also uses the variable
These adjustments do not affect the overall overall overall performance of the Union industry.
Not the expected memory behaviors.

<a id="tests-ciblés-exécutés"></a>

## Targeted tests performed

19 methods, **20 successful C executions** and **32 variantes invalides** to
Two entries verify_program/compile_source. Passage O0/UBSan:
**19 tests, 8,776 s, code 0**, inline-vector-borrows-targeted-twelfth.log.
The latest diagnostic details are included in the final regression
completed successfully.

Case: shared copies after vector destruction, mutable extraction,
prohibition on copying a mutable field, two cells and separate release,
child-scope targets, insert/take/relay, suspensions after vector drop,
branches and loops with re-use, nested fields, result received in the parent,
owner capture and local result obtained by join with shared or mutable field.

Refusal: destruction/mutation of targets before last use, concurrent access
to the mutable target, copy forbidden, target too short, target destroyed before
before use of the extracted result.

## Inspection C

C preserved for sync, async and capture fixtures.
use field code 1 and sizeof(Cell *) Vector receives directly the
fields via vector_push; local Cell is cleaned after. Remove written in
the new local Cell; the vector can be destroyed before reading the pointer
borrowed from this result. cell_drop only recursively destroys fields
The targets remain cleaned separately by their scope.
This inspection completes the executions without proving all the paths.

<a id="régression-traçabilité-et-limites"></a>

## Regression, traceability and limitations

The first passage O2/UBSan executed **192 methods in 148,300 s**, with two
chess: fresh local construction in an injected vector and local capture
async. The propagation of the scriptures wrongly treated the local slot of origin
like a pool to hold. The inline slot now keeps its own storage;
the fields borrowed are kept separately.
represent the fresh constructions of these boxes in the call effects.
The isolated reproduction is inline-vector-borrows-regressions-minimal.log.
Both cases are retained in existing tests; a new test covers
fresh borrowed construction injected, then two copies via function.

The first supplement has been completed **85 methods in 94,817 s**, with a failure of
compilation of a C fixture from Select. His call passed Cell * where ABI
Current is waiting for CrustStructureView. The same failure is reproduced with the files
Initial snapshot python: inline-vector-borrows-control-baseline.log.
Both arguments are adapted by structure_reference_for; all arguments are
selection, field and cleaning claims are kept.
reconstructed initial of this fixture has the same print as the recorded one
The first two passages have retained their
compiler/test prints, recorded in the newspapers -first-integrity.log.

Additional target after corrections: **20 tests, 9,245 s, code 0** in
-targeted-eleventh.log (17 batch tests at this stage and three regressions).
The 19 batch-specific tests were then passed in -targeted-twelfth.log.
The intermediate -targeted-tenth.log passage retains the resolution defect
a new local origin corrected thereafter.

Final O2/UBSan games completed, both code 0:
- Main selection: **194 methods, 151,310 s**, -regression-final.log ;
- Supplement: **85 methods, 95,054 s**, -control-final.log.

The compiler/test prints of the two selections are unchanged between
their launch and end; newspapers -regression-final-integrity.log and
-control-final-integrity.log. The corrections were made between the passes,
Never while they're being executed.

Snapshot initial /tmp/crust-before-inline-vector-borrows ; diff and fingerprints
in validation/inline-vector-borrows.patch and -changes.json.
selection and prints before execution are kept in the same folder.
C native compiled by the existing harness in C11, pthread, Wall/Wextra/Werrar,
Fatal UBSan. Static refusals are not executed natively.
No mutation campaign or adversary research extended in this lot,
according to the user priority; no supposed result of the external lab.
The tests do not demonstrate the general safety or completeness of VE1–VE6.
