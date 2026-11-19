[Français](STRUCTURE_VIEW_RUNTIME_CYCLE-fr.md)

<a id="emprunts-de-sous-structures--représentation-interne"></a>

# Substructure borrowings — internal representation

<a id="état-du-chantier"></a>

## State of the site

Stage of implementation of ST7, without any change in the standard.
This batch prepares storage and metadata; it does not yet return the
Substructure borrowing syntax usable in Crust.

`validation/open-inline-structure-borrow.crust` Describes the valid expected case:
emprunter `segment.debut`transmit it to `modifier(&mut Point)` and access
in the disjunct field `segment.fin.x`. Both compiler entries refuse it
still with "unknown field 'begin' in Segment"; observed in
`validation/structure-view-source-gap.log`. This refusal is a deviation of implementation,
Not proof of compliance with a rule of refusal.

<a id="représentation-ajoutée"></a>

## Representation added

The compiler now keeps `inline_structures` in addition to its layout
flattened. Each entry holds the path, nominal type and field range
The offsets remain expressed in indices until backend C: the
Python host machine pointer sizes are not assumed.

`CrustStructureView` is a description transmitted by value: root `Cell *`,
offset, size and layout. An additional projection consists of offsets
on the same root. A return thus does not retain any pointer to a variable
The local description of the callee. It does not allocate any slot or additional object and
does not offer any independent destruction operation.

The reading/writing primitives use the bytes of the existing root,
with `memcpy` to maintain processing of potentially non-aligned fields.
The limits of the view are checked before access. Shared/mutable permissions
and the lifespan must still be imposed by the source auditor.
The possibility of copying the description in C does not constitute an authorisation
copy a mutable loan into the language.

<a id="vérifications-exécutées"></a>

## Audits performed

Five methods in `tests/test_structure_view_runtime.py` : a verification of the
compiler metadata and six C executions. Three executions succeed;
three trigger the diagnosis of expected limits.

- Embedded nominal paths, consistent flattened beaches and layout.
- Return of the description through two functions C, modification in the slot
  of origin, similar field unchanged, one living allowance and then re-employment.
- Shared reference stored: target identical and not destroyed with the carrier.
- View kept in one task state, suspension, resume on another pthread,
  extraction then explicit destruction of the root after waiting.
- Offset off-allocation, out-of-parent projection and out-of-view field diagnosed
  before access.

| Passage | Result | Journal in `validation/` |
| --- | --- | --- |
| Initial target O0 | 5 methods, 1 probe failure, 1,925 s, code 1 | `structure-view-runtime-o0.log` |
| Final target O0 | 5 methods, 2,096 s, code 0 | `structure-view-runtime-o0-final.log` |
| Final regression O2 | 34 methods, 19.798 s, code 0 | `structure-view-runtime-regression-o2.log` |

Clang C11/pthread, warnings as errors, fatal UBSan; no test jumped.
The first probe added definitions of common values a second time.
Elle utilise maintenant `TASK_RUNTIME_BODY` with the guys already issued.
The 34 methods include tests
nested constructors, async copies and pools of async structures.

<a id="suite-requise-et-limites"></a>

## Required action and limitations

Still need to be connected before declaring this implemented feature:

1. Borrowing expressions and typing substructures.
2. The reservation of a path prefix and its re-borrowing until the last use.
3. Parameters, returns and contracts, including references received after appeal.
4. Async catches/returns and references stored in other values.
5. Accepted/refused source tests for destruction and transfers.

These tests of ABI do not prove these static obligations or general safety.
Multithread test directly manipulates the internal ABI; it does not demonstrate
a Crust program using a compile substructure view.
No new adversary campaign, mutations or independent model.

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_structure_view_runtime
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_structure_view_runtime test_inline_structure_construction test_async_direct_copy test_async_struct_pools
```

Snapshot initial : `/tmp/crust-before-inline-structure-views/`.
Patches in `validation/structure-view-runtime-{crust,structure_views}.py.patch`.
