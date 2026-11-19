[Français](PUBLIC_LOCAL_ENUMS_CYCLE-fr.md)

<a id="enums-locaux-à-travers-les-handles-publics"></a>

# Local enums through public handles

<a id="périmètre"></a>

## Perimeter

Application of AS10–AS12, the public API of draft 04 and
local storage of draft 05 to local enums introduced in the previous batch.
No new normative rules. Contracts continue to distinguish T and A<T>,
sources of the fields owned and targets of the stored references.

The cases of factory, join relay and await already use public contracts
This lot adds their targeted coverage for local enums. It corrects
also a shared match filter that accepted `print(nom)` mais refusait
`print(*référence)`, whereas this expression is an already allowed reading.
The filter now accepts the expressions recognized by `match_read_expression`.
The ordinary auditor shall always monitor their type, validity and validity.
No analysis of the body of the task is added to the public contract.

<a id="correction-du-constat-sur-bool"></a>

## Correction of the finding on bool

The inspection of the compiler and the `tests/test_sync_bool_calls.py` showed that
synchronous Boolean calls are already connected to the type `bool` in
The tiny. `Bool` the first local d-enum test was a bad writing
for this signature, not an absence of functionality.
synchrone utilise maintenant `bool` and both branches pass.
No new Boolean implementation was introduced.
The previous batch report also corrects this finding.

<a id="cas-ciblés"></a>

## Targeted cases

Five methods in `tests/test_public_local_enums.py` : seven native executions
admitted, including one with failed injection submission, and five invalid programs
refused by `verify_program` and `compile_source`.

- Public and auxiliary factory providing output<Choice,runtime::Error>;
  Handle distinction<Choice>/Handle<A<Choice>> and LaunchFailed.
- Two different async functions return different variants of the same
  local enum, with only one public type of handle, await and resume after yield.
- Shared field: Target remains protected after extracting the result.
- Field mutable: writing in the arm, maintaining the reservation and then access
  allowed after destruction of the bearer; premature write/drop refused.
- Field A<Int>: Pool maintenance, single destruction and re-use of the slot.

The conditional test `bool` of the previous batch adds two native executions
The expectations are written in the tests.

<a id="résultats-exécutés"></a>

## Implemented

| Journal in validation/ | Result |
| --- | --- |
| public-local-enums-first-o0.log | 4 methods, 1 failure: print filter in the shared match |
| public-local-enums-second-o0.log | 4 methods, 3,525 s, code 0, of which the corrected bool test |
| public-local-enums-third-o0.log | 5 methods, 3,068 s, code 0 |
| public-local-enums-regression-o2.log | 67 methods, 40,076 s, code 0; configurations detailed below |

Targeted cases use the C11/pthread harness with error warnings and
UBSan fatal. Historical modules `test_mutable_match` and `test_reference_fields`
use the harness of `test_crust`, without explicit optimization or sanitizer
in this command. The other modules use O2/UBSan. The O2 suffix
The paper does not replace this distinction.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_public_local_enums test_local_enums test_shared_match_field_reads test_mutable_match test_reference_fields test_public_structure_handles -v
```

<a id="limites-et-traces"></a>

## Limits and traces

The results are for the listed cases, not all combinations of
No adversarial campaign or new changes.
Recursive types and other forms of unrepresented fields remain
The overall objective is not yet achieved.

Snapshot : `/tmp/crust-before-public-local-enums/`. Patch of `crust.py` archived
sous `validation/public-local-enums-crust.py.patch`.
