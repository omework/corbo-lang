[Français](INLINE_VECTOR_OWNED_CYCLE-fr.md)

<a id="cycle--champs-propriétaires-des-structures-en-ligne-dans-vectort"></a>

# Cycle — Fields of ownership of the online structures in Vector<T>

<a id="règles-et-périmètre"></a>

## Rules and scope

VE1–VE3, H1, ST1/ST15/ST17, B1–B5, T4/T5/T6 and AS2/AS8/AS11–AS13
The following are the main features of the project:
The rules of structures and vectors, as well as the rules of the
The following are the main points of reference:
nouveau ni modification normative.

The batch connects push/remove and destroys online structures containing
The synchronous contracts, their use since
async, catches and results are included.
and general compositions remain open.

<a id="baseline-et-changements"></a>

## Baseline and changes

validation/inline-vector-owned.crust was refused both entries for one
explicit restriction of proprietary fields. The journal -baseline.log keeps
ce constat. Snapshot initial : /tmp/crust-before-inline-vector-owned.

The vector runtime now keeps a pointer to the static layout
boxes with fields. Push copies the payload and transmits the cleanup
descendants in the box; only the storage of the local bearer consumed is
The objects designated by A<T> remain in their pools at the same addresses.
Cleaning an unempty vector runs through its present cells, then fields
owners according to the layout, before recovering his region.
borrowed are not destroyed. Remove transmits the fields to the extracted bearer;
Bytes outside the initialized prefix are not cleaned a second time.

The auditor shall retain the subgraphs which own the boxes and their
The copy of a structure containing A<T> remains refused.
The inference of contracts materializes the paths owners of parameters
The backend async keeps the sources of the descendants.
separate from the local storage of the consumed carrier.

<a id="défauts-rencontrés-et-corrections"></a>

## Deficiencies encountered and corrections

Targeted first: 12 methods, 2.929 seconds, two failures on contract return.
A restriction only recognized the boxes of handle vectors; the
recognition also applies to the boxes of securities.
then omitted the descendants of an unseen proprietary parameter
The field projections are now materialized.
The log -contract-first.log keeps the intermediate step (two methods,
The second target: 12 methods, 3,602 s, code 0.

The expanded target revealed an invalid acceptance in an async body: a
synchronous function inserted an item containing A<Int> from a child pool
both entries accepted this program;
-targeted-third.log retains both sub-failures, on 17 methods in 5,025 s.
The effects of the contract did not know any storage for the inline boxes, so
only the former slots of the carriers must be ignored.
proprietary fields are now preserved and verified against the scope of the
The negative test was not weakened. The fourth target passes:
17 methods, 5.164 s, code 0.

<a id="ciblé-final"></a>

## Final target

**19 methods, 5,963 s, code 0**, O0/UBSan, in -targeted-final.log.
This represents **16 successful C executions** and **14 variantes invalides**
examined at both verify_program/compile_source entries.

Allowed cases: name/cost transfer, removal, destruction of empty/non-empty vector,
re-use of slots from two distinct pools, nested, descending content fields
owned by a loan, insertion/extraction functions and relays, passages
successive between two vectors in a loop, cleanup of scope, async body with
Yield, proprietary capture, join return and destruction of an inactive task.
Traces are used to maintain the unique cleaning of children, with effective re-use.

Cases refused: old name after transfer, copy of owner, transfer of the
cible d’un emprunt descendant avant dernier usage, pool enfant trop court,
insertion via contract that would try to extend this pool.

<a id="traduction-c-et-régression"></a>

## Translation C and regression

C stored in validation/inline-vector-owned.c. Layout marks field
A<Int> by code 2 and sizeof(Cell *) The call vector_push_owned_value precedes
cell_release_storage of the only carrier; the result of vector_remove receives the
normal layout and its cell_drop cleans the descendant.
present operations; execution and trace checks the tested paths.
Packaged fields use memcpy in existing accesses.

Primary regression O2/UBSan: **236 methods, 138,586 s, code 1** :
232 hits, three failures and one error in test_async_recursive_owned.
The four defects are reproduced with the initial snapshot of the compiler:
-recursive-baseline.log, five methods, 0.821 s, same balance sheet.
The historical records used Node local for A-allocations.
Corrected to A<Node>, without changing the assertions.
**five methods, 3.361 s, code 0**, -recursive-corrected.log.

The compiler is unchanged from the main passage; only this fixture
has changed after its end. The fingerprints before/after are recorded in
-first-integrity.log and -final-integrity.log. The 236 selected methods
have their results available after fixing correction;
It is not a single global green passage.
Supplement regions/two sliders completed: **35 methods, 26.861 s, code 0**,
-control.log; 33 unaltered compiler/tests (-control-integrity.log).
Selection,
initial, diff and manifest fingerprints: validation/inline-vector-owned-*.
No changes in compiler/tests during execution.

## Limites

No proof of general safety. Positions after certain calls and branches
remain conservative; async tracking can keep sources longer
as required. Pop, replace, try_push, slices and push_new structures in
line remain open, as are unrepresented graphs/types.
Reset is removed by default; tests in this lot use drop and the telescopes.
The selected regression does not replace the final audit of all rules.
C11/pthread, Wall/Wextra/Werrar, fatal UBSan via the existing harness.
No mutation campaign or extensive adversarial research; no results
The intermediate logs are kept.

Next reprinted gap: pop Vector<Point>, expected Option<Point>, remains
refused both entries. Fixture validation/inline-vector-pop.crust and journal
-baseline.log. This case and other open operations are not covered
by the success of this lot.
