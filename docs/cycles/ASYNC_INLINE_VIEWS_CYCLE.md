[Français](ASYNC_INLINE_VIEWS_CYCLE-fr.md)

<a id="captures-async-de-sous-structures"></a>

# Async captures of substructures

<a id="périmètre-et-décisions"></a>

## Perimeter and decisions

Connection of existing rules AS2–AS4, ST7–ST14 and ST17–ST18: a task
can capture a view to a durable substructure, without copying or moving
The method of capture retains the borrowing obligations during the
the life of the task and its results borrowed. No rule of law changed.

This batch covers structures whose terminal fields are already represented
by the backend async : Int, Int references and descendants owners taken
The nominal references stored in these structures remain a
separate site; the existing explicit refusal is retained and tested.

<a id="implémentation"></a>

## Implementation

- Structure references cross the Async border with the same
  descripteur `CrustStructureView` for whole and inner objects.
  Catches, frame members, child tasks and synchronous calls
  keep the root, offset, size and layout.
- Synchronous bridges describe a symbolic view without target displacement.
  The empty path is an identity projection, and retains the variants,
  proprietary fields and outbuildings of its root cleaning.
- Copies use the storage designated by the view; field borrowings
  Int calculate their address from the same storage.
  descendants owners in a match adapt their representation.
- Implicitly copied parameters are inferred and propagated in the
  storage contracts. A view in a pool of another type cannot
  use this pool for its implicit copy. A local root or destination
  The restriction is also valid for relays.

<a id="cas-ciblés"></a>

## Targeted cases

`tests/test_async_inline_views.py` 9 methods, 9 programmes admitted
exécutés nativement, huit programmes invalides refusés par `verify_program`
and `compile_source`.

1. Reading the second substructure after yield and launching on a worker;
   root drop and competing writing refused before launch.
2. Mutable capture, child task wait, synchronous call and mutation
   observed by the appellant; concurrent reading refused.
3. Same routine called with an entire object and then a substructure.
4. Destroy an inactive task: unexecuted body and mutable access rendered.
5. Returning a &mut Int to a field of view, then using it after join;
   destruction of the refused root before this use.
6. Reborrowable loan returned by synchronous helper, suspension and local copy.
7. View containing A<Int> and &Int: downward mutation and target reading;
   premature destruction of the refused target.
8. Implicit copy from a view of Pool<Pair> refused, directly and by
   relay; copy to an explicitly injected Pool<Point>.

9. Synchronous factory creating a task from a structural loan: copy
   from Pool<Point> compatible executed, from a view of Pool<Pair> refused.

<a id="défauts-rencontrés-et-corrections"></a>

## Deficiencies encountered and corrections

The first regression revealed C-accesses `->fields`/`->source` still written
for Cell*, as well as assignments of integer pointers in a descriptor.
These accesses and conversions are connected. Bridges also lost fields
during an empty projection, then the variants of the canonical carrier: the
replacement contracts indicated missing provenances.
The historical records concerned pass after correction.

The case of Point copying to Pool<Pair> was accepted after introduction
The two entries are now statically refused.
The requirement is passed on by contract, without opportunistic reanalysis of the body to
each capture. The tests distinguish local copy, pool compatible for a
whole object, explicit destination and incompatible pool for a view.

Two fixture errors were also corrected: a match brace
deleted by mounting the snippet, then a re-declaration of the name `pair`.
The last copy connection retains the distinction between representation
in descriptor and real substructure: an entire object in a pool
compatible remains copyable, including through a synchronous task factory.

An additional fixture declared a value without explicit use; it
No expected results have been weakened.

<a id="exécutions"></a>

## Implementation

Commandes : `PYTHONPATH=.:tests CRUST_TEST_OPT=-O0|-O2 python3 -m unittest ... -v`.
The harness compiles in C11 with pthread, error warnings and fatal UBSan
(`-fsanitize=undefined -fno-sanitize-recover=all`).

| Journal in validation/ | Result |
| --- | --- |
| async-inline-views-o0-first.log | 4 methods, 3 fixture failures, 0.461 s; shell command finished with tail, unit code not captured separately |
| async-inline-views-o0-second.log | 4 methods, 1,741 s, code 0 |
| async-inline-views-regression-first.log | 54 methods, 18 failures/subcases, 24.205 s, code 1 |
| async-inline-views-regression-second.log | 54 methods, 11 failures/subcases, 28.545 s, code 1 |
| async-inline-views-o0-third.log | 22 methods, 2 failures, 11,111 s, code 1 |
| async-inline-views-o0-fourth.log | 7 methods, 3,075 s, code 0 |
| async-inline-views-regression-third.log | 127 methods O2, 93.036 s, code 0, before final addition of the copying requirement |
| async-inline-views-o0-fifth.log | 8 methods, 1 fixture failure, 3,069 s, code 1 |
| async-inline-views-o0-sixth.log | 8 methods, 3,426 s, code 0 |
| async-inline-views-final-o2.log | 58 methods, 7 failures/subcases and 1 error, 31,043 s, code 1 |
| async-inline-views-final-second-o2.log | 58 methods, 35,864 s, code 0 |
| async-inline-views-factory-final-o2.log | 32 methods, 18,647 s, code 0 |

The 127 method pass covers new cases, mixed structures,
replacements owners and borrowed async, copies, stored sync views,
mixed results sync, structural captures, reference fields and their returns,
helpers of local structures, synchronous calls owners and features type.
The final pass after the copy requirement is for copies, storage requirements,
local catches, helpers and methods directly concerned.

## Limites

- No general evidence of safety or coverage of all interlacing.
  The expected output is written in the tests independently of the C generator.
- No new adversary campaign, mutation or random generation.
  The independent audit planned with another officer is not performed in this lot.
- The capture of a bearer containing an internal nominal reference remains
  The captures of views do not end the whole of the
  Async support for typed references and their results.
- No reset extension: API always removed from the default prototype.
- The public interface of the scheduler and the already open arbitrations remain
  The overall objective is still in progress.

Snapshot avant modification : `/tmp/crust-before-async-inline-views/`.
The patches of the four modified Python files are archived in validation/.
