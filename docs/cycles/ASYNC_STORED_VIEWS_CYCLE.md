[Français](ASYNC_STORED_VIEWS_CYCLE-fr.md)

<a id="références-typées-stockées-et-captures-async"></a>

# Typical references stored and async captures

<a id="périmètre"></a>

## Perimeter

Implementation of the already retained rules AS2–AS4, AS11–AS12 and ST7–ST18 for
structures containing references to other structures, in particular
No new semantics or implicit promotion.

Closing async layouts includes nominal references whose target
is represented. A reference uses the existing view descriptor; it
does not become an owner's allowance. Cycles of types which cannot be
not be closed by this calculation remain outside the perimeter represented.

## Modifications

- Reading and re-borrowing a &T/&mut T field with loading of the
  complete descriptor, including after yield and in a child task.
- Extension of monitoring of shared/exclusive fields and contracts for
  replacement to the type referenced, instead of limiting them to Int.
- Synchronous bridges: symbolic reconstruction of the reference graph
  typed and preserved roots, layouts and capacities.
- Construction and copying of porters in a task; capture by transfer
  and return of a carrier keeping its inner target.
- In the join, preservation of reservations by identity of the canonical root,
  and not by equality between identities of a view and its external object.

The test that documented the provisional refusal of the captured views
now check their creation and then inactive destruction.
implementation limit, not a normative ban.

<a id="tests-ciblés"></a>

## Targeted tests

`tests/test_async_stored_views.py` : eight methods, nine programmes admitted
and nine invalid programs refused both entries, in the version
final of the suite.

- Shared reference stored: read after suspension, destroy the holder
  or the competing root and mutation refused.
- Mutilable reference stored: reborrowing passed to a child task, mutation
  visible after join, competing writing refused.
- Link → View → Point chain, with a copy of the shared carrier.
- Extraction shared and then mutable by a synchronous helper called in the task.
- Direct or contract replacement: new targets retained after join.
  The old and new referent remain protected when the launch can
  fail and therefore leave the field unchanged.
- Capture owner of View then return to join: the reference extracted
  The substructure is still linked to the carrier after destruction.
  the target before its last use is refused.
- Building and local copying View in a task; shared reference
  extracted survives the destruction of both carriers.

Next `test_stored_inline_views` keeps synchronous cases and exercises
also newly admitted inactive destruction.

<a id="défauts-et-corrections"></a>

## Deficiencies and corrections

The passage of a mutable field by helper used an origin `field_parameter`
the async generator did not project for this result yet.
Now uses the same field contract as direct reading.
C also explicitly declare the use of descriptors necessary for the
static model, even when not read by the specialized C body.

The owner return revealed a real defect: a writing on `pair.b.x`
was accepted while a shared reference from the returned carrier was
The internal descriptor was present, but the selection of the
parents only kept the exact identities.
canonical now keeps the reservation of `pair.b`. The rejected test passes
by verify_program and compile_source.

The first replacement fixtures used a reference assignment
without explicit re-borrowing; they now use `&*p`. They destroyed
also the old reference before the last use of the field after join: this case
is actually invalid if the launch fails. The program allowed retains
the former target until then, and the initial program remains a rejected test.
The first drop test in an arm failed first on the parent transfer →
child required; mutation of the target in this arm directly tests the
the intended borrowing conflict, without this other prohibition.

<a id="exécutions"></a>

## Implementation

Commandes : `PYTHONPATH=.:tests CRUST_TEST_OPT=-O0|-O2 python3 -m unittest ... -v`.
Harness C11, pthread, error warnings, fatal UBSan. Expected values
are written in the tests independently of the generator C.

| Journal in validation/ | Result |
| --- | --- |
| async-stored-views-o0-first.log | 3 methods, 1,206 s, code 0 |
| async-stored-views-o0-second.log | 14 methods, 2 failures, 4.187 seconds, code 1 |
| async-stored-views-o0-third.log | 14 methods, 4.879 s, code 0 |
| async-stored-views-o0-fourth.log | 6 methods, 2 failures/subcases, 1,876 s, code 1 |
| async-stored-views-o0-fifth.log | 6 methods, 2 failures/subcases, 1.795 s, code 1 |
| async-stored-views-o0-sixth.log | 6 methods, 2.517 s, code 0 |
| async-stored-views-o0-seventh.log | 8 methods, 2 diagnostic failures expected, 3.348 s, code 1 |
| async-stored-views-o0-eighth.log | 17 methods, 2 refusals missing, 6,355 s, code 1 |
| async-stored-views-o0-ninth.log | 17 methods, 6,346 s, code 0, before adding the two refusals to destroy the former reference |
| async-stored-views-regression-o2.log | 118 methods O2, 74,459 s, code 0 |

The bound regression covers stored views, direct captures of views,
Int stored references and their returns, mixed structures, replacements
owners/borrowed, copies, local helpers, proprietary synchronous calls
and synchronous typed views.

<a id="limites-et-suite"></a>

## Limitations and follow-up

- No general evidence, no examination of all interlacings or graphs.
- No new mutation campaign, generation or adversarial audit.
- Direct async returns of nominal references, variants matches
  containing these references and certain interlocking projections remain to be
  This report does not state the validation.
- Recursive types and combinations of unrepresented graphs remain
  separate from the finished closure applied here.
- No change to default reset removal, public interface
  the scheduler left open or to other deferred arbitrations.
- The overall objective is not over.

Snapshot : `/tmp/crust-before-async-stored-views/`. Patches archived in
validation/ for the three modified modules and the old replacement limit test.
