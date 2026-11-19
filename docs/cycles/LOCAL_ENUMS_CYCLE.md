[Français](LOCAL_ENUMS_CYCLE-fr.md)

<a id="enums-sur-la-data-stack-implicite"></a>

# Enums on the implicit data stack

<a id="règles-et-périmètre"></a>

## Rules and scope

Draft 05 imposes the default data stack on the values outside pool.
This batch connects the enums to this synchronous and async storage, with
explicit transfers, parent reservations, AS8–AS12 and cleaning
existing fields owned and borrowed.
organisation by arm; no normative pool rule is replaced.

Local construction employs `Choice.Two { x: 9, y: 11 }`, with the designation
variant already used by pool constructions and matches.
Fields remain explicit and complete. A local value T does not become
An A<T> allowance.

<a id="implémentation"></a>

## Implementation

- The parser recognizes the qualified literals d
- The arm tag belongs to the layout of the value. Match, comparison and
  projections of synchronous bridges read it since `Cell.layout` ; `Cell.source`
  The two pointers are still the source of the release.
  already identify the same arm; for a local value they are distinct.
- Each local variant has static metadata with its name, its
  tag, its offsets and its types of fields. They survive the producing state.
- Synchronous reservations of an enum result have maximum size
  possible loads, calculated in C with the target sizes.
  then install the layout of the actually chosen arm.
- Async results destinations include enums, and manufacturers
  The data stack provided for in the existing investment plan is used by local companies.
- L-display of a possessed aggregate named in a state uses `cell_print`, with
  control of borrowings as for other uses.

<a id="cas-ciblés"></a>

## Targeted cases

Eight methods in `tests/test_local_enums.py` 10 programmes admitted implemented
and three invalid programs verified by the two compiler entries.

- Three variants, including a vacuum, synchronous playback and good arm display.
- Match async with yield and call a synchronous helper after suspension.
- Conditional synchronous return: both variants of different sizes.
- Synchronous helper construction, transfer via task and join.
- Direct async construction, conditional return and transfer to a child expected.
- Output of a child block, if with receiver and loop output by break.
- Local Enum with an allocation and borrowing a target: return, match
  consumption, the sole destruction of the descendant and the reuse of its slot.
- Refusal of missing field, too short local reference and a
  destruction of target before last use.

<a id="exécutions"></a>

## Implementation

| Journal in validation/ | Result |
| --- | --- |
| local-enums-first-o0.log | 5 methods, 3 failures: async display, return destination and Bool synchronous fixture |
| local-enums-second-o0.log | 5 methods, 2,199 s, code 0 |
| local-enums-third-o0.log | 8 methods, 4,281 s, code 0 |
| local-enums-regression-o2.log | 124 methods, 75 sub-case failures, 57.124 s, code 1: Out-of-range layout symbol |
| local-enums-regression-second-o2.log | 124 methods, 103.565 s, code 0 |
| local-enums-historical-o2.log | 23 methods, 6.510 s, code 0; historical harness without explicit optimization or sanitizer |

The first fixture used `Bool` in a synchronous signature.
The following inspection confirmed that the
Boolean parameters are already implemented with `bool` The test is tiny.
Now uses this writing, without new semantics or added alias.
See the lot of the local d-enums for re-execution. The regression then revealed a superfluous layout assignment for the
local structures with a reserved result: the symbol belonged to the appellant,
not to the generated helper C. Only the enums now install their arm when
a structure keeps its layout already reserved.
The other two targeted failures
have required the generation connections described above.

Targeted execution and async regression use Clang C11/pthread,
Error warnings and fatal UBSan. Expected outputs are written in the
The historical pass selects the methods `test_enum_*` of the
`test_crust.PrototypeTests`, with their own historic harness. This one
do not use `CRUST_TEST_OPT` : despite the suffix of the newspaper and the variable
This pass therefore does not claim O2 or UBSan.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_local_enums -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_local_enums test_async_owned_enums test_async_enum_match test_async_consuming_enum_match test_async_enum_nominal test_async_local_struct_helpers test_async_local_owned_result_graphs test_async_result_storage test_public_structure_handles test_async_local_parent test_async_loop_placement -v
```

## Limites

The support is checked on the layouts already represented and the paths listed.
This batch does not generalize all types of fields or recursive graphs.
No new adversarial campaign or changes; results do not
Reset remains removed by default,
historical cases that request it keep their dedicated option.
The overall objective remains active.

Snapshot : `/tmp/crust-before-local-enums/`. Patches archived under
`validation/local-enums-*.py.patch`.
