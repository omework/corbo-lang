[Français](ASYNC_ENUM_NOMINAL_CYCLE-fr.md)

<a id="références-nominales-dans-les-bras-denums-async"></a>

# Nominal references in the d-enums async arms

<a id="périmètre-et-règles"></a>

## Perimeter and rules

Connection of existing AS8–AS12, ST7–ST14 and borrowed games
No rule of law changed. A shared reference stored
point to a target independent of the bearer. A mutable reborrowing reserves the
capacity of the holder until last use; consumption the holder transfers its
The internal addresses remain stable.

<a id="implémentation"></a>

## Implementation

The backend async infers the nominal type of pattern aliases and extracts the
`CrustStructureView` stored in the field, instead of only loading its root
as for a pointer to Int. The layout gives the exact offset of the field,
The suspension retains the descriptor in the
the existing status of the task.

The analysis of the results detachs the nominal shared references as it does
The analysis of constraints and projection at the appellant did so for &Int.
follow the field target and retain the carrier reservation for &mut T.
The waiting protocol, running of the slots and their release order do not
Don't change.

<a id="cas-exécutés"></a>

## Cases implemented

`tests/test_async_enum_nominal.py` contains five methods, six programmes admitted
executed and six invalid programs refused to both compiler entries.

- Two shared variants return an inner reference after yield and
  destruction of the carrier; the target remains legible, the slot is reusable.
- A mutable arm re-borrows via synchronous function, suspends and modifies the
  Reuse the first loan before the last use of the second fails.
- A mutable result comes out of the arm and then out of the task; the target and the carrier
  remain reserved at the caller until its last use.
- A consuming match releases the bearer once; reuse his slot n
  not the returned reference. prematurely changing the target is refused.
- A task built l'enum in a local pool, transfers it to a child expected
  then re-use the slot after the end of this child.

The expected outputs and the single destruction are written in the tests.
Refusals are verified with `verify_program` and `compile_source`.

<a id="exécutions-et-corrections"></a>

## Implementation and corrections

Newspapers in `validation/async-enum-nominal-*` :

| Journal | Result |
| --- | --- |
| first-o0.log | 2 methods, 2 failures: unrepresented projection and lost provenance |
| second-o0.log | 2 methods, 1 failure: inference of the match result type still limited to Int |
| third-o0.log | 2 methods, 1.599 s, code 0 |
| fourth-o0.log | 5 methods, 1 fixture failure: match syntax consuming incorrect |
| fifth-o0.log | 5 methods, 2.695 s, code 0 |
| regression-o2.log | 104 methods, 91,860 s, code 0 |

The fixture used `match <-v` ; it now uses the syntax already
retenue `match (->v)`. No change in grammar to circumvent this failure.
Regression control:

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_enum_nominal test_async_nominal_results test_async_enum_match test_async_consuming_enum_match test_async_owned_enums test_async_enum_suspension_fields test_async_stored_views test_async_match_references test_public_borrowed_handles test_public_structure_handles -v
```

The C is compiled with Clang C11, pthread, error warnings and fatal UBSan.
The regression is about the enums owners, borrowed and consuming matches,
suspension contracts, stored references, nominal returns and public handles.

## Limites

These executions cover the listed cases, not all graphs or interlacings.
Recursive types, unrepresented compositions and public interfaces
yet to arbitrate are not declared completed. No new campaign of
The independent audit is still planned separately.
`reset` The overall objective remains in progress.

Snapshot : `/tmp/crust-before-async-enum-nominal/`. The four patch modules
are archived under `validation/async-enum-nominal-*.py.patch`.
