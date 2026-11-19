[Français](ASYNC_OWNED_FIELD_WRITES_CYCLE-fr.md)

<a id="remplacement-de-champs-possédés-en-async"></a>

# Replacement of fields possessed in async

<a id="fonctionnalité-raccordée"></a>

## Connected functionality

This lot applies the existing rules of replacement, origin and
destruction in fields A<T> in async, as well as AS16, RT6 and SL1. No rule
The cases are the result of the replacements already exercised in the
synchronous with expectations/suspensions already retained.

The suspension contract now uses the common representation
`owned_field_writes`, collected at the suspension points.
termination remains separate. A previous replacement yield belongs to the
first; a subsequent replacement may belong only to the second.
Snapshots are carried out through the same sustainable source checks as the
writings at the end.

The effects are connected to the backend after a synchronous call, a wait or
Select. Field source tracking retains the required pools.
the caller synchronises, the waiting of the handle also applies the modifications of the
The graph is owned, with the initial alternatives required by LaunchFailed.

Direct assignment of an A<T> field is generated in the async state: the new
value is evaluated, its type and provenance are verified, the field receives
the new pointer and the old allocation is destroyed.
the new allowance remains stable. The cleaning after suspension follows the
content actually owned by the aggregate.

<a id="validation-ciblée"></a>

## Target validation

Seven methods go to O0 in 3.603 seconds and O2 in 4.373 seconds: eight executions
The first is the first time that the programme has been completed.
`validation/async-owned-field-writes-scope-final-o0.log` and
`validation/async-owned-field-writes-scope-final-o2.log`. Both passages
end with OK; O2 process was observed completed with code 0.

The controls include the separate sources of suspensions and suspensions.
terminaison, join, await direct, affectation directe, fonction auxiliaire,
pool re-use, failed launch, replaced by loser
Select and descend enum. Launch failure retains initial value
7 ; normal termination exposes 11 ; a loser stopped after yield
conserve 9.

The first passage contained an incorrect expectation of refusal: the pool court
provided only an interim allowance already destroyed before its end.
This program is now explicitly expected to be valid and executed.
refused to place the last allowance in the pool court: she would survive
The original log is kept; no rule has been changed for
accept the first case.

The regression directly related to O2 passes 109 methods in 64,053 s, code 0:
`validation/async-owned-field-writes-regression-o2.log`. It precedes a last
fit: the source control looks for the closest scope to a
The two targeted passages of seven methods
above check this adjustment, with a dedicated case; complete regression
was not repeated after this amendment.

Native executions use
Clang C11, pthread and UBSan without recovery. No mutation campaign or
additional adversarial search is not launched, according to user's instructions.

## Limites

The replacement descendants containing themselves loans remain explicitly
not connected in this historic lot. &Int and &mut Int fields are now
covered by the [Next lot](ASYNC_OWNED_BORROW_WRITES_CYCLE.md).
Aggregated storage sources may retain
old sources by caution; lot does not claim precision
maximum for all branches, factories and projections.
and other open families are not covered by these results.
The independent audit remains separate and is not deemed to be conducted.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_async_owned_field_writes -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_owned_field_writes test_async_consuming_enum_match test_async_enum_suspension_fields test_suspension_effects test_async_structure_effects test_select_source test_async_owned_struct_returns test_task_result_storage test_foundation_rules.FoundationTests.test_owned_struct_field_replacement_preserves_disjoint_borrow test_foundation_rules.FoundationTests.test_borrowed_owned_field_replacement_keeps_alternative_sources -v
```

Snapshot : `/tmp/crust-before-async-owned-field-writes/`.
Implementation differences are archived in
`validation/async-owned-field-writes-{async_lowering,async_structure_effects,crust}.py.patch`.
