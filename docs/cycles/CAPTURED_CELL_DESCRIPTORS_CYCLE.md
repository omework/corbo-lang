[Français](CAPTURED_CELL_DESCRIPTORS_CYCLE-fr.md)

<a id="descripteurs-des-emprunts-int-capturés"></a>

# Descriptors of loans Int taken

<a id="règles-et-frontière-corrigée"></a>

## Rules and corrected border

No rule of law has been changed. This lot continues B4, ST8/ST11–ST13,
AS2/AS12/AS13 and RT6/RT8: a catch by borrowing retains its target, without
copy of the allocation or transfer of its destruction to the task.
of this loan in a local object must also function after suspension.

`validation/open-async-captured-stored-reference.crust` create an allowance,
capture in an async relay then in a child who calls an auxiliary
synchronous building a View. The earlier version refused both
compilation entries due to lack of descriptor in the state.
explicitly loads the three previous modules from an isolated copy:
`validation/captured-cell-descriptors-recorded-baseline.log`.
The program is now compiled and executed with value 7, destruction
From View then from n: `captured-cell-descriptors-recorded-final.log` and C neighbor.

Each task carries a set of parameters indices requiring a Cell.
This set increases when the body stores a captured reference, or
when a child requires this descriptor. The lowering is repeated until stability
All sets, which are finished. Synchronous contracts are recalculated
between the passes: a handle factory must publish the same requirement for
C signatures, calls and state members are the same as the one in the previous year.
The task declaration order must not be issued with the same stabilized list.
not determine the executable programs.

The catches concerned add a `Cell *` the existing content pointer.
Catches that do not store a reference do not receive this member.
The argument retains the original descriptor at creation, then through
The selection between the children, the reborrowing and synchronous factories.
multiple provenances use the measured pointer and the targets followed.
The descriptor is not an additional allowance and is not destroyed
by cleaning the borrowed catch. The life control and
of the existing loans remain exclusive.

<a id="validation-exécutée"></a>

## Validation executed

Targeted final orders:

```
CRUST_TEST_OPT=-O0 PYTHONPATH=tests python3 -m unittest test_captured_cell_descriptors test_cell_reference_bridges -v
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_captured_cell_descriptors test_cell_reference_bridges -v
```

The 27 methods go to O0 in 32,296 sec and O2 in 32,585 sec, newspapers
`validation/captured-cell-descriptors-complete-o{0,2}.log`. Elles comprennent
14 methods from the previous batch and 13 new methods.
is executed with Clang C11, pthread, fatal warnings and fatal UBSan.

The new cases cover shared and mutable catches, address identity,
five relays in both reporting orders, not first parameter,
target selection, synchronised factories relayed, launch refused, native thread,
Inactive destroyed task and re-use of slot. A recursion of four instances
with explicit capacity retains the descriptor and destroys only once n.
Shared and mutable results protect the target until the last use.

An independent model of eight scenarios distinguishes the scalar result from the
The result is the destruction before/after join, and drop/reset.
The resets are executed, six rejected by the two compiler entries.
emploient uniquement `allow_legacy_reset=True` to verify provenance
The public API remains withdrawn. The 16-scenario model of the
previous batch is also re-executed, without changing its expectations.

The regression O2 `test_sync_handle_bridges test_sync_borrow_calls
test_native_blocks test_async_capacity test_async_structure_effects` passe
72 methods in 67.036 s: `captured-cell-descriptors-regression.log`.
Selection O2 `test_function_bodies test_type_features test_buildin_features
test_nested_plain_results test_async_struct_captures test_async_struct_reference_fields`
passes 102 methods in 70,371 seconds: `captured-cell-descriptors-contract-regression.log`.
These selections are not a passage from the overall suite.
The Python compilation of modules and new tests succeeds.

`python3 tests/run_captured_cell_descriptor_mutations.py` detects five errors
isolated: loss of catch requirement, stop before stabilization, loss of
the requirement in a synchronous factory, descriptor null in condition and bad
The target of the conditional choice. `captured-cell-descriptors-mutations.log`.
The first three are observed by contract or compilation, the two
This does not prove the absence of other errors or the absence of
general correction of the scheduler.

<a id="erreurs-intermédiaires-et-distinction-normative"></a>

## Intermediate errors and normative distinction

A first generation test of the factory was extracted `*capture_cell_0` to
location of the parameter name C. The generated statement was corrected before the
Targeted follow-up. The first targeted journal retains eight sub-test failures:
six reset diagnoses not recognized by the reason for the test, and two tests
borrowing a local scalar earlier refused by grammar/semantics
existing. Inline representation tests now use boxes
valid tables; reset diagnoses are explicitly checked.

The mutable complement first included a pattern `Ok(mut v)` not taken in
After correcting this fixture, it revealed above all a bad
attente : retourner `&mut *w.data` from a local w porter violates ST12, which
The program remains tested as refused.
The admitted neighbour finishes the local reborrowing, destroys w then returns the parameter
original mutable. No carrier controls were removed.

Intermediate passes of 25 methods and complements are retained
The historical test that was waiting for
the refusal of any Int capture has been replaced by the acceptance tests of this
The refusal of inline pointers without descriptors remains in effect.

<a id="limites-et-prochaine-frontière"></a>

## Limits and next border

Inline targets without Cell, including table elements used in
These fields remain a limit of representation.
The replacements of field dependencies remain open.
The contract is still rejected by the foreign countries since the async states.
inferred, but its application to states, hands and callers after waiting
This lot doesn't lift that control.

No overall passage of all suites, no new ASan/TSan proof
The patches are under
`validation/captured-cell-descriptors-*.patch`. The overall objective remains open.
