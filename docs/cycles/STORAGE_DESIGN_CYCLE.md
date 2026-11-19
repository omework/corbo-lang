[Français](STORAGE_DESIGN_CYCLE-fr.md)

<a id="intégration-du-stockage-et-des-transferts"></a>

# Integration of storage and transfers

<a id="première-passe"></a>

## First pass

The decisions of drafts 02, 03 and 05 are carried over in
[LANGUAGE_RULES.md](../LANGUAGE_RULES.md), [GROWING_REGIONS.md](../GROWING_REGIONS.md),
[SCOPE_EXIT.md](../SCOPE_EXIT.md) and [ASYNC_MULTITHREAD_RULES.md](../ASYNC_MULTITHREAD_RULES.md).
Explicit arrows are kept according to the status of draft 02.
The executable changes in this pass relate to consumption
Local values by `drop(-> x)`. Pool cases also test
the behavior already supported by the typed creation and transfer.

<a id="exécutions"></a>

## Implementation

- Three targeted tests were performed in C11 with Apple Clang 17 and UBSan blocking,
  à `-O0` and to `-O2`. The two routes of `drop` local donnent
  respectivement `1\n2\n3\n` and `4\n`. The second passes through a suspension
  before consuming the table.
- A pool of two `Point` has moved to a function by `&mut Pool<Point>`.
  After two return `A<Point>`the destruction of the first frees a
  The third allocation is exactly the address
  of the first, while the second keeps its address and its value.
  the two live slots, the third allocation comes out with code 1 and
  diagnosis `pool capacity exceeded`.
- The auditor refuses to return an allowance from a local pool,
  the absence and the absence, the form `drop(a)` and consumption
  with borrowing still active. He also refuses readings, copies and
  double consumption tested after `drop`.
- The 68 regression tests of the `test_fixed_arrays` sont passés.
- Two isolated mutations deactivate synchronous invalidation, respectively
  and the async consumption of the table. Each fails three refusals.
  Mutants accept a reading and a second `drop`. The third case
  is a synchronous copy and a length reading in async.

<a id="emplacements-de-tailles-différentes"></a>

## Locations of different sizes

The runtime now remembers the size occupied by each cell.
the cursor uses the end of the last living cell.
impose their slot size and reject an incompatible size.

A time-independent model, seed 9081, generates 200 operations of
creation and destruction of different sizes in a bounded range. It compares
addresses, values stored, number of living cells and cursor
After each operation. `-O0` and `-O2` sous UBSan bloquant.
The targeted re-use test of the typed pool also passes. This primitive remains
to connect to the placement of local structures by the compiler.

<a id="limites-du-raccordement"></a>

## Connection limits

Runtime also distinguishes physical storage and field description
A test builds two types in the same range, one of which is a
The person responsible for the allocation from a pool.
the conservation of the living prefix, the decline after destruction of the temporary
and re-use of a location with another field description.
Normal, excessive size and incompatible source runs go to O0 and
O2 under UBSan blocking. The model test by intervals and pool test
typed also pass after this change.

Two temporary mutations are detected by testing local types.
The first uses the fixed source size to calculate the end of the last
object. The second uses the source description to clean the fields.
The regression of the 21 regional tests was successful before the addition of descriptions
A further decline in regions and fundamentals is in the region, which is the result of a decline in the number of people living in the same area.
course in the session 46923, journal `/tmp/crust-local-layout-regression.log`.

The primitive `local_cell_new` The previous tests are still internal to the runtime.
exercise the C emitted with an added harness. They do not yet demonstrate the
compilation of the literals `Point { ... }` or their stable transfer between telescopes.

<a id="raccordement-des-littéraux-de-structures"></a>

## Connection of structural letterings

Syntax `Point { x: 10, y: 20 }` now build a local structure
on an implicit data stack of the scope. Effects analyses, results and
constraints distinguish its local source from pools. Field descriptions
have a static storage time in the C emitted.

An internal reservation of 16 Mio is used by a telescope that builds a
local structure. This template is a provisional choice of backend. Its dimensioning
and its sharing with the rest of local values remains to be integrated.

The test `test_local_structure_literal_storage_and_borrows` compile and execute
a full Crust program at O0 and O2 under UBSan blocking. It performs a reading
borrowed followed by a mutation, a proprietary field from a pool,
the destruction in a child's block and the re-use of the pool slot.
is `10\n30\n9\n0\n0\n`Four variants are refused, for further borrowing
used after mutation, reading after destruction, annotation `A<Point>` on
a local structure and field initialized twice.

Two valid programs are explicitly not supported in this
The return of a local structure from a block is refused because of its
storage is not yet reserved in the parent. `copy(p)` on this structure
is refused pending the placement of the copy in the destination scope.
These refusals constitute deviations from the implementation of validated decisions.

<a id="transfert-à-travers-des-blocs-imbriqués"></a>

## Transfer through interlocked blocks

The compiler now reserves the local result location in the
receiver scope for direct result blocks. It follows the declarations that
provide the result through the nested blocks. The reservation precedes
execution of the block, while fields are evaluated and initialized to their
The structure retains the source of the receiver during its original position.
successive receipts.

The test program crosses two blocks, prints three times the same address
9. The traces destroy the temporary interior, the
then the result after its use. This program passes under
UBSan blocking O0 and O2. A variant that returns a field `&Point` to a
local child structure is refused. These results remove the refusal of return
block marked in the previous step for the directly covered forms.

Conditional branches, result loops and function returns remain
to connect to this local reservation. The local copy still needs to be included.
The targeted regression of the proprietary structures and fields is launched in
session 47022, journal `/tmp/crust-local-transfer-struct-regression.log`.

<a id="résultat-conditionnel-local"></a>

## Local conditional result

The branches of a `if` who build the same local type now share
a reservation in the receiver. This reservation can cross a block
enveloping. Only the branch executed initializes the object.
placement requires that the paths analysed continue normally for the time being.

Both paths are executed separately. Each keeps the observed address
in the branch, in the enveloping block and in the final receiver.
destroys only the temporary and the result of the chosen branch.
The other branch is refused. `Point`
local and `A<Point>` are refused in both directions, including when the type
connections are inferred.

The final pass runs three test methods at O0 and then O2 under UBSan blocking.
It covers four programmes admitted and eight variants refused per level.
The newspaper is `/tmp/crust-local-if-final.log`. The loops with result, outputs
The local placement is still to be connected to the pre-emptive and return functions.

<a id="sortie-terminale-de-boucle"></a>

## Terminal loop output

A loop including the `break <- valeur` final follows the construction of the result
now reserves this result before entering the loop.
previous `continue` keep the reservation unoccupied logically.
The variables of these iterations remain cleaned by their telescopes.

The test performs three iterations, two of which are repeated.
0, 1 and 2 of the temporary workers, then the value 9 of the result. L
before the break is the receiver's. After destruction of the result, a new one
structure receives the same address and contains 10. The trace has exactly the same
three temporary destructions, destruction of the result and destruction
the new structure. The break without arrow and the return of a field using
temporary iteration is refused.

The three targeted loop, condition and interlocked blocks tests are switched to O0
and O2 under UBSan blocking. `/tmp/crust-local-loop-tests.log`.
The regression of 64 proprietary structures and fields tests is complete
successfully. It started on the state before conditional extensions
and loops, which have the above targeted tests.

The loop placement covers here a terminal break whose construction follows
The break in several branches, a result already built
before a recovery, return outputs and function returns remain
The expanded regression of session 46923 is still ongoing.

<a id="breaks-dans-les-branches"></a>

## Breaks in branches

Collection of returned buildings now runs through branches `if`
local outputs supported share the reservation of the
parent. A path that resumes before these constructions keeps the reservation
for a subsequent iteration. The types of results shall be identical.

A test performs two branches of break separately after two continuous.
each branch, it observes three destructions of temporary, the address of the
identical result before and after break, and only one destruction of the result
The variant with two different types of structure is refused.
The four targeted methods of interlocked loops, condition and blocks pass
O0 and O2 under UBSan blocking. `/tmp/crust-local-loop-branches.log`.

The values built before a resumption remain, the other forms of control
and return of functions.
local and unsustainable sources and must distinguish between storage of
The results prepared by the appellant.

<a id="résultat-local-construit-par-une-fonction"></a>

## Local result built by a function

Contracts now distinguish origin `local_value` of sources
local pools. Upon call, the compiler reserves the result in the data
caller stack. An internal C parameter transmits the location to the function.
The constructions followed by a return initialize this reservation, while
The opaque application of the contract links the
the result of the appellant's storage.

A test performs two paths of a function, a return in an if and a return
The two keep the address between construction and reception.
The term "temporary" is destroyed before the appellant uses the result.
An annotated result `A<Point>` from a local structure and structure
The test of the typed pools
is replayed and keeps the refusal of return from a local pool.
Both methods go to O0 and O2 under UBSan blocker, newspapers
`/tmp/crust-local-function-tests.log` and `/tmp/crust-local-function-O0.log`.

The selection of placement covers direct constructions that the collector
links to returns. Local results relays by several functions and
other forms of control still to be integrated.
of local functions and structures is currently in session 46660,
journal `/tmp/crust-local-function-regression.log`.

<a id="relais-du-résultat-local"></a>

## Local Outcome Relay

The investment collector now recognizes calls whose contract
returns a local structure. A call already associated with a reservation the
forwards to next call. The contract is used to identify the type
and the source of the result. The chain retains the location of the receiver
final until the manufacturer.

The first program performs two functions and one block, observes four times
the same address, reads 10 and destroys the structure exactly once.
program returns by two functions a structure containing a loan to
un `Point` The appellant destroys the reference structure and then uses the
The reverse order is refused for borrowing still active.

Relay, function and break tests
conditionals go to O0 and O2 under UBSan blocker.
`/tmp/crust-local-relay-tests.log`. The previous regression of 15 tests of
returns of local functions and structures successfully completed before
The extended regression 46923 continues to be implemented.

The pre-loop constructions, other forms of output and
copying of local structures remains to be included in the placement.

<a id="construction-avant-reprise-de-boucle"></a>

## Construction before loop recovery

The collector follows the local producers declared before the branches of the
exit. An active loop reservation retains its location when
The value of iteration is destroyed. The proprietary fields are destroyed
normally, then the reservation can receive the next construction.
The loop exit ends this storage retention.
then the result can recover the location.

The test uses an Int pool of capacity one and builds three times a Holder
Two continue to destroy each field and
Holder. Break transfers third value. The four addresses observed
The pool accepts an allowance of
99. The seven expected destructions are observed and the location of the
Holder is recovered only once.

The eight methods of local structures are transferred to O0 and O2 under blocker UBSan.
The two runtime tests of cells of different sizes and cleaning
Cross-pool also goes to both levels.
`/tmp/crust-local-repeat-tests.log` and `/tmp/crust-local-repeat-runtime.log`.
A mutation deactivating the reservation retention is detected at O2.
mutant program recovers the location to the first continuous then fails with
the reservation diagnosis incompatible with the following construction.

Returns via loop with active booking
The current collection avoids reserving these forms.

<a id="return-anticipé-pendant-une-réservation-de-boucle"></a>

## Early return during loop booking

The compiler tracks active bookings by receiver scope. When a return is made
leaves this scope, it finishes the reservation after the destruction of values
The runtime has an operation
recovery of the independent storage of destruction, which allows for
make a reservation empty without reading uninitialized fields.

The new test calls a function three times. The first path returns
11 The second one returns 22 after a re-run and a
the third is normally out of the loop and returns to the new construction.
33. A Holder holds an Int from a pool of capacity one.
Expected destructions on the two roads that build are observed.

The nine local structures and reservations tests go to O0 and O2 under
UBSan blocking. Both targeted runtime tests also pass on both levels.
Journaux `/tmp/crust-local-early-tests.log` and `/tmp/crust-local-early-runtime.log`.
A mutation that fails to make reservations empty is detected at O2,
with a closed source diagnosis while still containing storage
living. The tested return is an Int. The direct transfer of the reserved object by
a return through the loop remains to be connected to the local result contract.

The extended regression 46923 completed with 449 successful tests on its initial state,
The total regression of the
region after separation destruction/recovery is ongoing in session
85363, journal `/tmp/crust-local-reservations-growth-regression.log`.

<a id="transfert-direct-par-return-à-travers-une-boucle"></a>

## Direct transfer by return through a loop

The collection of returned constructions now follows the contained blocks
in expressions and instructions. The loops that build the result
The position also retains the location provided by the appellant.
Return keeps built value, ends loop retention
and leave its destruction to the receiver.

Two programs perform a function that builds and then resumes twice.
The first spell either by turning back in the loop or by break and then back.
The second uses a instruction loop with direct return. Both calls
of each program keep addresses, produce value 2, destroy
Six total values and retrieve the location twice.
reuse the location rendered by the first. A structure returned from
loop with a field using a local target is refused.

The ten methods of local structures are switched to O0 and O2 under blocker UBSan.
The additional refusal is replayed in O2 with both programs.
`/tmp/crust-local-loop-return-tests.log` and `/tmp/crust-local-loop-return-final.log`.
The 85363 regression was completed with 22 tests of successful regions on the state
the runtime preceding this collector extension.

Local copying, other syntactic forms of results and application
This placement to other local types still needs to be integrated.

The pool test uses a trace of addresses and expected values.
This pass n-adds no independent data stack model.
The C emitted still uses local variables and async states for
the above sections exercise physical depilation
and the reservation parent local structures; their generalization to
Other types, general outbuilding cleaning and migration of
anciennes syntaxes restent ouverts.

<a id="copie-des-structures-locales--intégration-de-st17st18-du-brouillon-07"></a>

## Copy of local structures — integration of draft 07 ST17/ST18

The normative rule now distinguishes local copying, which uses data
stamp recipient, copy of an allowance in his original pool.
The generator reserves the place of the result before crossing the telescopes
children. A copy retains the values of the fields, but has its own
The fields used keep their location and clean up.
The proprietary fields and mutable references remain non-Copy.

A counter-example was accepted by the auditor and then refused by the backend:
`fn duplicate(p: &Point) -> <- Point { let r = copy(p); return <- r; }`, called
with a local Point. The copy contract is now solved according to the
storage of the argument; the backend receives the location of the caller for
Two relays and one block output perform this connection.
The copy in a pool, including from a borrowed parameter, is kept.

Evidence completed:

- 19 targeted methods go to O0 and then O2 under UBSan blocking: copies
  local, previous reservations and four pool copy regressions.
  Journal `/tmp/crust-local-copy-regression.log`.
- New scenarios exercise field independence, two addresses
  the re-use after drop, the retention of the address after
  transfer, three iterations with continuous, return from a function and
  copying from a parameter through two calls.
  The shared references survive in the
  The original; a local target too short and premature drop/reset are
  Refused resets use only the historical profile.
- Two isolated mutants are detected at O2: the omission of memcpy produces
  incorrect fields; omission of result reservation makes reject
  the three valid transfer programs.
  `/tmp/crust-local-copy-mutations.log`, copies in
  `/var/folders/rs/ld5jvh_n6t92p1hhs2qrmt7w0000gn/T/crust-local-copy-mutations.sj71lyjh`.

The first execution of the new tests revealed two errors in the
test: the existing format is `View(10)` and the diagnosis says "still be
These expectations have been corrected without changing the properties of the
copy or life required.

The wider regression of structures, contracts, provenances, pools and runtime
completed 189 tests successfully in 107,972 s, journal
`/tmp/crust-local-copy-interactions.log`. It includes runtime models
by intervals and destruction/re-use scenarios.
An additional copy scenario of View received as a parameter, which survives
to its original but still protects its target, goes to O0/O2, newspaper
`/tmp/crust-local-copy-shared-relay.log`. It adds an admitted program with
trace of three destroyed and two rejected programs (drop and reset).

Limitations: New tests are not an independent model of the
check. The runtime model by intervals is replayed with regression
The coverage remains that of the syntactic fields and forms taken in the
the general placement of other local values, other decisions
Draft 07 and subsequent lots are not completed.

Additional execution of the copy program of Relayed View, compiled
with `-O2 -fsanitize=address,undefined -fno-sanitize-recover=all`, n’a produit
no exits and remained active during successive observations.
test process was stopped by SIGTERM after more than 30 seconds.
Sampling of his battery with `sample` was refused for lack of privileges.
This ASan control is **inconclusif** The same cause is not established.
program has normally finished under UBSan alone. No ASan result successful
is claimed for this pass.
