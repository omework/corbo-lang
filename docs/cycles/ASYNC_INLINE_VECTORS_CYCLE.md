[Français](ASYNC_INLINE_VECTORS_CYCLE-fr.md)

<a id="cycle--structures-en-ligne-dans-les-vecteurs-async"></a>

# Cycle — Online structures in async vectors

<a id="règles-et-portée"></a>

## Rules and scope

VE1–VE4, ST17/ST18, H1–H3, T1/T6, B1–B5/B4a, AS2–AS4,
AS8–AS15 and MT1–MT8 remain unchanged. AGENTS.md, complete guidelines
and the index of drafts were read, as well as the relevant rules.
This batch extends Vector<Point> storage already connected to async tasks in
Synchronous: The boxes contain Point fields, not A<Point>.

The perimeter of the layouts remains that of the synchronous lot: leaf structures
Int, including interlocked or empty. Specific tests for this lot are carried
on Two-field Point Int and Empty. Other fields and operations
Vector<T> missing items are not reported completed.

<a id="implémentation"></a>

## Implementation

- Local and injected pools, catches by mutable borrowing or transfer,
  parameters and results recognize vectors of online structures.
- Push of a local construction/copy feeds the bytes of the box and
  Cleans the temporary. Copy a box and removes produce a local value
  independent; remove requires explicit transfer and a mutable receiver.
- The borrowing of the vector remains active during the index assessment, even if
  The index is being evaluated and retained in the async state.
- The placement of local values extracted recognises the vectors and their
  pools. A result transmitted to the parent or the caller uses storage
  the recipient from its creation, without further relocation of address.
- The public contracts Handle and Result recognize A<Vector<Point>>.
  The synchronous relay retains the source of the pool after join.
- Both AST forms of len are connected. No change in runtime C.

<a id="tests-exécutés"></a>

## Tests performed

Eight targeted methods, **14 successful native executions**, **8 programmes
invalids checked at both entries** verify_program and compile_source.

- Two increasing values and region annotation; copy/extraction read
  after destruction of vectors and after yield.
- Captured mutable borrowing: read and drop calling side refused before join.
- Capture owner, wait or destroy inactive task, then
  Reuse of the capacity pool one. The old name transferred remains invalid.
- Return of Point by copy or extraction, with await and join; signature
  A<Point> is denied for these local values.
- Whole Vector built in an injected pool, public contract of handle,
  Relay of the Result, extraction and then reuse of the pool. A children's pool too
  short is refused.
- Index provided by a wave, direct consumption of removal per drop,
  result of a suspended if and empty structure.

Final Targeted Command:

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_inline_vectors -v
```

Outcome: **8 methods, 6,324 s, code 0**, journal
validation/async-inline-vectors-targeted-fifth.log. Compilation Clang C11,
pthread, Wall/Wextra/Werrar, fatal UBSan. Expected outputs are written
independently of implementation; invalids are not executed in C.

<a id="défauts-rencontrés-et-écart-conservé"></a>

## Faults encountered and deviation retained

The first passes identified the absence of len in its second form AST.
After correction, the eight initial methods passed.
by public contract first introduced a fixture error (helper placed
with a task returning Int), corrected without changing semantics.

The fixture added with `match (->next)` reveals a distinct general defect:
parse the needle to the results of replace/try_push, while next
is a Join Result. L-analysis then loses the type of content of Ok and
refuse to remove. The program is kept in
validation/open-async-inline-public.crust. **This case still needs to be implemented**.
The defect is also reproduced on a simple Result<Int,runtime::Error>:
validation/open-consuming-join-match.crust and consuming-join-match-baseline.log.
The final test exercises the same relay with `match next`, already taken in
load for join results. He does not claim to validate the notation
The first forth newspapers are kept, including
failures and intermediate success prior to the new public case.

<a id="régression-et-limites"></a>

## Regression and limitations

Regression O2/UBSan: **226 methods, 215,753 s, code 0**.
The 31 compiler/test files followed remained unchanged during the year
execution (async-inline-vectors-regression-integrity.log).
Selection: validation/async-inline-vectors-test-selection.txt; journal:
validation/async-inline-vectors-regression.log. The selection covers the
vecteurs synchrones/async, placement local, retours, contrats publics,
Result and storage requirements. It is not an execution of the whole suite.

Stay open: fields borrowed/owners of online structures,
named moves, pop/replace/try_push, box borrowings, slices,
push_new and general compositions. Reset is not reintroduced.
No new independent model or mutation/random campaign in
this lot, according to the priority given to implementation.
both native and UBSan are not general proof of safety.

Snapshot: /tmp/crust-before-async-inline-vectors. Patch and fingerprints:
validation/async-inline-vectors.patch and async-inline-vectors-changes.json.
Allowed Fixture and C: validation/async-inline-vectors.crust and .c.
