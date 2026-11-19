[Français](RETURNED_OWNED_REPLACEMENT_CYCLE-fr.md)

<a id="restituer-un-objet-après-remplacement-dun-champ-propriétaire"></a>

# Restore object after replacing a proprietary field

<a id="règles-et-cas-enregistré"></a>

## Rules and cases recorded

This lot applies the existing rules of replacement, explicit transfer,
stable identity and pool duration, as well as AS10–AS13 for the result
The replacement evaluates the new allocation, destroys the old one.
and keeps the new field. Return the carrier transmits this final graph.
No normative rules are amended.

`validation/open-async-return-replaced-owned-field.crust` was still refused
by "restitution with replacement of the owner field".
replace the field A<Int> of a Holder by 11 in another pool, then renders the
Even Holder. A task calls this auxiliary and transmits its result by join.
The program is now accepted and implemented.

## Corrections

Result contracts retain the replaced fields even when the root
is the input parameter. Resolution overlays these fields to the fields
the carrier's remains unchanged. The body validation checks the final graph against
the contract, instead of systematically refusing any difference in provision.
The restitution shall retain the nominal identity and the address of the root, without
restore its old field outbuildings.

The projection of the async result now distinguishes the pool from the root and the
the pools of its fields after replacement. A shortcut of the symbolic analysis
previously simply returned the photograph of the initial parameter: after
the first correction of restitution, it wrongly accepted a result
the new field was coming out of its pool. The duration test revealed this gap;
the shortcut no longer applies to a result containing modified fields.
The borrowed targets contained in these fields have been re-retrieved since the contract.

The first regression detected two refusals on unchanged interlocked graphs:
the calculation of the sources of the contract used only the descendant cache
direct and omited the pool of a symbolic grandchild.
the owner graph, while retaining the sources of elements of the sheets
The source checks are not disabled.

<a id="cas-testés"></a>

## Cases tested

Six methods in `tests/test_returned_owned_replacement.py` :

- Registered program, equal addresses before/after join, destruction
  unique from old field 7, new field 11, and Holder.
- Injected launch failure: destruction of initial capture, without
  implementation of replacement or creation of 11.
- Synchronous call and contract of return, same address, re-use of slot
  old before destruction of the result, then re-use of the new slot.
- Direct Await then suspended async relays keeping the pool of the new field.
- Refusal of results whose field survives a pool too short, synchronous
  and async; the necessary scope transfers are explicit.
- Property adjacent unchanged; down containing &Int
  keeping its target until last use, with premature drop refused.

The target passage includes six native executions and four invalid programmes
Checked both entries, i.e. eight refusal checks.
The expected values and cleaning traces are the oracles of the
tests; they are not inferred from the compiler's internal decisions.

<a id="résultats-exécutés"></a>

## Implemented

| Passage | Result | Journal in validation/ |
| --- | --- | --- |
| Six targeted methods O0 | Code 0, 2,587 s | `returned-owned-replacement-o0.log` |
| First regression O2 | 90 methods, two nested graph failures, code 1 | `returned-owned-replacement-regression-o2.log` |
| O0 check after correction of descendants | Eight methods, code 0, 4,831 s | `returned-owned-replacement-o0-final.log` |
| Final regression O2 | 90 methods, code 0, 78.048 s | `returned-owned-replacement-regression-o2-final.log` |

The last section includes the six targeted methods, the two regressions and the
preservation of the source of the leaves elements, on the final version.
Clang C11, pthread, warnings treated as errors and UBSan without
recovery; no test jumped. The models already present in the linked suites,
The pool depth model is replayed. No new model
This is neither the whole of the proceedings nor general evidence.

## Limites

Executed cases cover a returned root with fields A<Int> and a
Downbound containing &Int. They do not prove all recursive graphs,
variations changes, results wrapped and branch combinations.
The source analyses remain conservative.
of the scheduler, mutex manufacturers and handle captures remain
No new adversary campaign or changes.

The first logs keep an error of Python syntax of the new test,
then a fixture missing the explicit transfer of the holder in the
child block. The corrected fixture tests the duration of the pool rather than this first
The same passage exposed the incorrect acceptance async described
above; its refusal check is kept in the final test.

<a id="reproduction-et-artefacts"></a>

## Reproduction and artifacts

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_returned_owned_replacement
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_returned_owned_replacement test_async_owned_struct_sync_calls test_async_local_owned_result_graphs test_public_structure_handles test_nested_owned_borrows test_factory_owned_effects test_async_result_factories test_async_owned_field_writes
```

Snapshot : `/tmp/crust-before-returned-owned-replacement/`. Differences in
`crust.py`, `results.py` and `async_result_storage.py` archived in
`validation/returned-owned-replacement-*.py.patch`.
