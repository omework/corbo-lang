[Français](DETACHED_TASK_FACTORIES_CYCLE-fr.md)

<a id="fabriques-de-tâches-à-résultat-emprunté-détaché"></a>

# Tasks with detached borrowed result

<a id="règles-et-périmètre"></a>

## Rules and scope

This lot applies existing rules ST8/ST10/ST13/ST14, B1/B2/B4a,
T1/T6, D1, AS2/AS8–AS14, RT6 and SL1. It does not change any normative rules.
A returned shared reference retains its target; it does not retain
arbitrarily destroys the bearer or other fields. A reference to
the inline storage of the holder does not have this independence and remains refused.

The fields of the Int/&Int/&mut structures taken in
load, local proprietary catches or A<T>, synchronous mills,
their task relays, direct expectations, functions awaiting
nominal handle, public handle and select branches
This lot does not generalize graphs
and all the results borrowed, including mutable projections.

<a id="contre-exemples-et-corrections"></a>

## Counter-examples and corrections

1. `validation/open-owned-borrowed-detached-factory.crust` was refused
   at the initial inference: the factory asked for the source of the
   result before the availability of the termination contract.
   It is now compiled and executed, with the covered relays.
2. `validation/open-detached-child-target-dropped.crust` was accepted by
   `verify_program` and `compile_source` despite a drop in target followed
   a use of the reference after await. The newspaper
   `detached-factories-unsafe-baseline.log` conserve ces deux acceptations.
   The loans from the returned field were missing in the result of a child
   created directly from an async state. Both steps refuse
   maintenant ce programme (`detached-factories-unsafe-fixed.log`).
   The proof of defect is static; no native execution of this
   invalid version is not claimed.
3. The road through a factory kept all the fields after
   Await. The unturned target can now be destroyed; the real
   Target remains protected until last use.
4. The contract of a function receiving a nominal handle and then making join
   Also kept unreturned fields. His symbolic projection
   now follows the result path, including with a reference of
   assistance in the event of LaunchFailed.
5. A factory in a transferred argument from Select was not dispatched
   to task creation. It now uses the same path as
   The losers keep their loans until the drop.
6. Replace a shared field with another shared field of the structure
   The descriptor of the target already borrowed was refused.
   is durable through capture. This case passes; replace by a
   reference to a new local Int then return it remains refused.

<a id="implémentation"></a>

## Implementation

`ResultAnalyzer.async_definition` requests the necessary termination contract.
Async analysis receives synchronous signatures and requests summaries from the
Inference supplier. Synchronous bodies remain absent from this adapter.
Only full contracts are published; a cycle still in progress
The opaque public forms of handles are not explicitly incomplete.
The overall calculation of contracts
until stabilization and final verification remain in place.

Backend distinguishes between loans held during execution and those held
The owner catches project the shared fields
The factories filter their loans by the same paths.
The symbolic task/hand parameters also apply this projection.
Field replacement recognizes the targets already borrowed from a parameter
owner; it does not make a value inline or local sustainable.

No change in the C runtime or shift in the allowance is introduced.
The snapshots are in `/tmp/crust-before-detached-task-factories` and the differences
sous `validation/detached-factories-{results.py,async_lowering.py,async_structure_effects.py}.patch`.

<a id="validation-ciblée"></a>

## Target validation

`tests/test_detached_task_factories.py` contains thirteen methods:

- `validation/detached-factories-complete-count-o0.log` 13 methods in
  30.024 s; 21 native executions and 30 invalid programmes tested by
  the two stages, 60 refusal checks.
- The O2 base of `validation/detached-factories-complete-mutations-o2.log`
  succeeded in the same thirteen methods in 29.063 s.
- Clang C11/pthread, Wall/Wextra/Werrar, Wno-unused-function and fatal UBSan
  are used by the native harness, at O0 and O2.

An independent model crosses the left/right target, the moment before/after
wait and three call paths (direct, factory, factory relay).
Before waiting no target can be destroyed; after, only the target
The 12 scenarios are included in the accounts.

The other tests cover the helpers in three reporting orders,
conditional results that protect all possible targets,
the loss of the holder's pool before the last use of its reference,
refusal of a target too short, failure of launch injected,
Inactive task cleaning, public handles, Select,
replacing one field and three iterations reusing storage.
The expected values and destruction of the bearer are checked.

## Mutations

Eight errors are detected in temporary copies: refusal to replace
valid, no publication of the termination, analysis of a helper by its
empty stub, loss of loan of child result, improper preservation of all
production fields, loss of all loans of the result of manufacture, merger of the
fields in the contract of the waiter and selection of the wrong child field.

Loss of child loan is detected by undue acceptance of counter-example
invalid; the cancellation of factory loans is also detected after
The overrestrictive mutations are detected by the refusal of the
valid programs. The deployments only cover an explicit selection of
errors: no general detection rate is deducted.

<a id="chronologie-des-preuves-et-limites"></a>

## Timeline of evidence and limitations

The intermediate logs are kept. The first suite used
`Bool` in a synchronous signature waiting for the notation `bool` ; this
fixture has been corrected. The addition of the Select test revealed the missing dispatch:
the first bases of mutations/counting have thus failed and have been restarted
After the correction, two lines of the Select test were inserted into the
the wrong loop test; they were re-tested in the relevant test.
These fixture errors are not counted as compiler defects.

The newspaper `detached-factories-final-fields-o0.log` also preserves the true
refusal to replace a captured field, corrected afterwards.
contain the replacement test and its local invalid target neighbor.

Asan and Tsan are not newly established.
no general proof of safety, convergence of
all inferences or coverage of all scheduling.

<a id="écarts-restants"></a>

## Remaining differences

Update: the [mixed structures cycle]](ASYNC_MIXED_STRUCTURES_CYCLE.md)
corrects the direct case below. Borrowings in the possessed descendants
The refusal described here is the photograph of the end of this lot.

`validation/open-mixed-owned-borrowed-capture.crust` remains refused to both
steps (`validation/detached-factories-next-mixed-probe.log`). Sa structure
contains an A<Int> field and a &Int field; the two separate families are
Supported but their combination is not yet connected. Pools
and the target is, however, sufficiently long in this programme.

This counter-example becomes the next batch.
general async signatures, public scheduler API and general placement
remain open, as well as the two already documented arbitrations on the handle
None of these points are deleted from the overall objective.

<a id="régressions"></a>

## Regressions

`validation/detached-factories-first-regression-o0.log` 36 methods pass
before the loan retention supplements after await.
`validation/detached-factories-regression-o2.log` : 190 methods go through
263,624 s, after the corrective of child/manufacturer loans, before the supplements
final waiter, Select and field replacement.

`validation/detached-factories-final-regression-o2.log` : 107 methods pass
in 153.837 seconds, after the additions of the waiter and Select, before the last
add to field replacement. Modules: public_borrowed_handles,
concrete_handle_relays, select_source, select_contracts,
async_capture_field_contracts, async_detached_field_returns,
async_result_factories.

`validation/detached-factories-field-regression-o2.log` : 100 methods pass
in 104,697 seconds on the final compiler. Modules: async_structure_effects,
async_field_application, async_child_field_effects, factory_field_effects,
async_field_reborrows, stored_field_reborrows, async_borrowed_struct_pools.
The thirteen final targeted methods also go on this compiler.

The three O2 selections use CRUST_SANITIZE=undefined explicitly.
They are recouping and their accounts are not added as tests
All final processes are completed. The lot is closed in its
The scope and overall objective remains active.
