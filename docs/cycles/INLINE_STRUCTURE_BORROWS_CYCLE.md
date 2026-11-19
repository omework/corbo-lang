[Français](INLINE_STRUCTURE_BORROWS_CYCLE-fr.md)

<a id="emprunts-source-de-sous-structures-à-champs-int"></a>

# Source borrowings of field substructures Int

<a id="périmètre"></a>

## Perimeter

Partial implementation of ST6–ST8, without changing the normative rules.
The case recorded in `validation/open-inline-structure-borrow.crust` is
accepted by the `verify_program` and `compile_source`, then executed in C.
Historical refusal remains in `structure-view-source-gap.log`.

A view of substructure uses `CrustStructureView` : root, offset,
Size and layout transmitted by value. It does not consume any independent slot.
The verifier keeps a nominal projection and a prefix reservation
The accesses to its fields make up this path.
Results contracts keep these projections through relays.
The synchronous functions generated adapt their C signature to this representation.

Incompatible access and calls remain prohibited until the last use.
The distinct proven brothers remain accessible.
The root scope cannot leave a view still usable.

<a id="cas-exécutés"></a>

## Cases implemented

Seven methods in `tests/test_inline_structure_borrows.py`, neuf programmes
admitted to be executed natively and ten programs refused to both entries:

- Registered case: mutation by function, reading the brother, only one destruction.
- Reserving the subtree mutable, releasing at last use; reading,
  transfer, destruction and new loan incompatibility refused.
- Shared view, nominal display and two mutable views on distinct brothers.
- Return of a substructure through two functions; protected root.
- Return of Int borrowing from sight; transfer of a licensed brother field,
  mutation of the targeted field refused.
- Release of a child block allowed when root survives; local root
  destroyed at the exit of the refused block.
- Results of `if` and `loop`, change in place and address unchanged.

The first passage encountered a defect of the auditor: the loan of a field
reborrowed and subtree reservation were counted as two capacities
The collection of loans now recognizes their filiation.
Field access checks remain active; mutation test
The program is still not compatible with the program.
weakened to get the tests passed.

<a id="preuves-dexécution"></a>

## Evidence of enforcement

| Passage | Result | Journal in `validation/` |
| --- | --- | --- |
| Initial target O0 | 6 methods, 1 failure, 2,311 s | `inline-structure-borrows-o0-first.log` |
| After correction O0 | 6 methods, 2.560 s, code 0 | `inline-structure-borrows-o0-second.log` |
| Final target O0 | 7 methods, 3,171 s, code 0 | `inline-structure-borrows-o0-third.log` |
| Related regression O2 | 61 methods, 38.277 s, code 0 | `inline-structure-borrows-regression-o2.log` |
| Champs historiques O2 | 5 methods, 2,551 s, code 0 | `inline-structure-borrows-fields-o2.log` |

The output code of the first process was not retrieved in context
kept; the journal explicitly attests `FAILED (failures=1)`.
The following four passages were retrieved at the end of the process.
Clang C11/pthread, fatal UBSan and warnings as errors for testing
target source; the five historical tests use their legacy-reset profile
and their O2/UBSan harness. No test jumped in these passages.

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_inline_structure_borrows
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_inline_structure_borrows test_structure_view_runtime test_inline_structure_construction test_stored_field_reborrows test_async_field_reborrows test_async_direct_copy test_async_struct_pools
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_foundation_rules.FoundationTests.test_struct_int_fields_use_same_slot_and_respect_whole_borrows test_foundation_rules.FoundationTests.test_struct_int_field_loans_distinguish_siblings_and_keep_carrier_alive test_foundation_rules.FoundationTests.test_returned_struct_field_contract_preserves_exact_paths test_foundation_rules.FoundationTests.test_returned_reference_array_preserves_inline_field_path test_foundation_rules.FoundationTests.test_array_update_contracts_relay_inline_field_paths
```

<a id="limites-et-suite"></a>

## Limitations and follow-up

- New source views are limited to substructures whose fields
  Int. The reference fields and A<T> still need to be connected.
- The copy of a borrowed substructure remains explicitly refused.
- Storage of a view in a reference field and its async capture remain
  explicitly refused; the internal ABI alone does not validate these features.
- A result mixing whole object reference and interior view is refused
  with a non-connected functional diagnosis. A representation
  This is not a new rule of language.
- Backend prepares the type of match arms result, but this lot does
  contains no new match source case returning a substructure.
- No new adversarial campaign, mutations or generation of
  Existing models of regression modules have been implemented
  their cases; no new independent model of source views has been added.

These executions check the roads cited; they do not prove safety
and do not close the implementation of ST7 or the overall objective.

Snapshot : `/tmp/crust-before-inline-structure-borrows/`.
Patches : `validation/inline-structure-borrows-{crust,results,constraints,structure_views}.py.patch`.
