[Français](ASYNC_CAPTURE_FIELD_CONTRACTS_CYCLE-fr.md)

<a id="contrats-de-capture-par-champ-et-restitution-du-porteur-empruntant"></a>

# Field capture contracts and refund of the holder of the loan

<a id="périmètre-et-règles"></a>

## Perimeter and rules

This lot applies existing rules T1/T6, B1/B2/B3/B4a, D1, ST6–ST15,
AS2/AS8–AS14 and MT8, as well as the T/A<T> storage distinction.
No normative rules are changed. Shared and mutable references
remain distinct after entering into a contract; the return of a bearer
does not promote its targets or pool. AS12 requires to maintain dependencies
the result, without arbitrarily attaching them to all parameters.

Executable perimeter covers Int/&Int/&mut Int field structures
local or pooled, their own catches,
the nominal relays of synchronous tasks, the full restitution, children
direct async and synchronous factories supported.
A<T> and references and general signatures are not declared completed.

<a id="défauts-corrigés"></a>

## Corrected defects

The two counter-examples of the previous cycle are now accepted:

- `validation/open-owned-borrowed-mixed-task-relay.crust` : the contract was grouped
  fields by capture number; the shared target became exclusive to
  contact of the mutable field. Shared reading passes, competing accesses
  Inconclusive are still denied.
- `validation/open-owned-borrowed-capture-result-owner.crust` : the result
  Integer could not project the targets of the fields from the moved parameter.
  It now keeps them after join, without asking for a borrowed parameter
  the finished state.

A third excessive refusal is corrected: after a direct return of a
The only field shared, the target of another field remained reserved.
`test_detached_result_releases_unrelated_field` releases this other target and
uses the returned reference. The variant that destroys its real target is
refused. The first probe attempted a drop from a child arm without transfer
the final test receives the reference in the parent and performs the
Drops, to isolate the property studied.

<a id="implémentation"></a>

## Implementation

`capture_paths.py` sets capture selectors: parameter number,
The contracts of the
results, symbolic sources and concrete dependencies use the
The prefix of shared/mutable capacity remains separate.

Backend async prepares loans by field before consuming the bearer.
The results of the children and factories re-link these loans to the bearer
received. Targets for a full result are projected from captures
The direct result paths filter the other fields.
Physical transfer code retains the existing pointer; no copy
or translation of an address is not introduced by this lot.

Previous snapshots of Python modules are in
`/tmp/crust-before-capture-field-contracts`. The diffs are kept under
`validation/capture-fields-*.patch`. The injection points of the eight mutations
historical proprietary catches have been adapted to the new name,
without changing the injected fault or the expectations of the tests.

<a id="preuves-exécutées"></a>

## Evidence

`tests/test_async_capture_field_contracts.py` contains thirteen methods.

- `validation/capture-fields-final-count-o0.log` : 13 methods, 20.833 s,
  24 native executions and 37 invalid programmes, each verified by
  `verify_program` and `compile_source`74 refusal checks.
- `validation/capture-fields-final-suite-o2.log` 13 methods, 21,121 s, success.
- Both suites use the Clang C11/pthread harness, Wall/Wextra/Werrar,
  Wno-unused-function and fatal UBSan; optimization varies between O0 and O2.
- `validation/capture-fields-first-regression-o0.log` : 47 successful methods
  before the last projection of the direct results.

The scenarios include successive relays, mutable return, and
independent shared projections, parent scopes, loops,
conditional returns, Select branches, inactive tasks and
Injected launch failures. Address test compares the pointer front
capture and after return, for a local carrier and a pool holder; with
a pool of a slot, a new allocation reuses this slot after drop.
The destruction of the bearer and target is counted separately.

Two small independent models set out expectations:

1. A table of six operations: reading/writing/drop shared target
   or mutable. Only reading the shared target is allowed as long as
   the task remains alive; two depths of relay are exercised.
2. The four inside/outside provisions of the carrier pool and the
   Only the provision where both survive the outside receiver
   The model does not consult the compiler's decisions.

<a id="mutations-et-essais-intermédiaires"></a>

## Intermediary mutations and tests

`validation/capture-fields-final-mutations-o2.log` : basis of 12 methods
successfully, then seven mutations detected. The address test was then added
and the 13 final methods are executed separately at both optimizations.
Mistakes merge fields, erase targets of the result, group together
loans async, erase these loans, lose a path of result, retain
a field not returned or lost loans in a factory.

The first passage (`capture-fields-mutations-o2.log`) detected two errors
only by a different diagnosis: a second drop of the same object masked
acceptance of the first. The final variants remove this second drop.
The final passage effectively detects undue acceptance at both stages
for the erasure of async loans and factory loans.
by refusal of a valid program is distinguished from a breach executed;
no overall detection rate is claimed.

`validation/capture-fields-historical-mutations-fixed-o2.log` : the eight
historical mutations are detected. The loss of concrete capture is still
detected by a change in diagnosis in this historical test; it does not
This is not in itself evidence of improper acceptance or wrongful execution.

Intermediate errors are retained: import before `__future__`, masquage
decoding helper by a local variable, two duplicate receiver names
in new tests, and quote error in adapting the script of
historical changes. `initial-probe`, `existing-o0`,
`new-initial-o0` and `historical-mutations-o2` allow for their examination.

<a id="écarts-ouverts"></a>

## Open deviations

`validation/open-owned-borrowed-detached-factory.crust` remains refused to both
steps (`validation/capture-fields-open-detached-factory.log`) The direct case
detaching a field works; a synchronous factory that creates the same task
causes premature inference of the borrowed result, before his contract of
This valid program is still to be connected; this is not
not a new regulatory restriction.

The mixed graphs A<T>/references, other projection families and
Async signatures, the public API of the scheduler and the general advance placement
The two arbitrations on the already launched handles remain open.
no new ASan/TSan result or general proof of security is
The closure of this lot does not mean the end of the overall objective.

<a id="régression-finale"></a>

## Final regression

`validation/capture-fields-regression-o2.log` : 195 successful methods in
199,572 s, with CRUST_TEST_OPT=-O2 and CRUST_SANITIZE=undefined. Modules:
async_owned_borrowed_captures, async_borrowed_local_results,
local_result_envelopes, async_local_captures, async_structure_effects,
select_source, suspended_cleanup, native_blocks, storage_requirements,
public_borrowed_handles, concrete_handle_relays, async_detached_field_returns,
async_borrowed_struct_pools.

The compiler did not change during or after this regression.
methods of the new batch are executed separately on the same compiler.
All the final processes mentioned are completed. The lot is closed in its
described perimeter, with the retained manufacturing gap and the overall active objective.


Next: the factory deviation detaching a shared field is corrected in the
[retailing cycle](DETACHED_TASK_FACTORIES_CYCLE.md), which corrects
also the loss of a child income loan after await.
above describe the condition prior to this supplement.
