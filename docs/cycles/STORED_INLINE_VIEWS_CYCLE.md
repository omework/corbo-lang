[Français](STORED_INLINE_VIEWS_CYCLE-fr.md)

<a id="stockage-de-références-vers-des-sous-structures"></a>

# Storage of references to substructures

<a id="périmètre-et-représentation"></a>

## Perimeter and representation

Connection of ST7, ST10–ST14 and ST17–ST18 to stored references with target
is a substructure contained. No change in the normative rules.
The reference retains the physical root and its path; it does not possess
this root and does not create a new slot for the substructure.

The field C of a nominal reference now contains a `CrustStructureView`
by value: root, offset, size and static description of type.
increases the size of these fields, including when they target an entire object.
The &Int and A<T> fields retain their existing pointer representation.
Field sizes and categories are shared between generators
sync and async. Writings of an entire reference also initialize
descriptor metadata; readings are specialized according to the targets
The data are not available for the purposes of this Directive.
producteur.

Copies of structures copy the descriptor. The destruction of the bearer does not
The returns use existing contracts,
by keeping the internal paths and the mutable reservations.
removes old domestic bookings that have become untargeted.
cycles compare the physical root of a view, and not just its identifier
Projection.

<a id="cas-ciblés"></a>

## Targeted cases

`tests/test_stored_inline_views.py` 9 methods, 8 programmes admitted
The number of disabled programmes that have been completed is five.
is an explicit implementation limit: the async capture of a carrier
containing a view still to be connected and is not presented as prohibited by
language.

- Shared reference copied in another structure, Int fields preserved,
  destruction of authorized porters, early destruction of the refused root.
- Construction and return of the carrier, extraction of its reference by two relays,
  then use after the end of the producer.
- Reborrowable mutable stored and returned by function; transfer and read-out of the
  good substructure, competing access and early drop of the refused holder.
- Replacement of an entire reference by a view, then vice versa; old
  freed after its last use.
- Writing the descriptor through a view of the carrier itself.
- Enum projections per borrowed and consuming match.
- Copy to pool and retain descriptor after re-use of slot
  of its original carrier.
- Reference from a root to its own substructure refused by the prohibition
  already retained the cycles of allowances borrowed.

<a id="exécutions"></a>

## Implementation

Clang C11/pthread, warnings as errors, fatal UBSan. Programs
first pass through `verify_program`, then `compile_source`, then execute
C generated with an expected result. Refusals pass to both entries.

| Passage | Result | Journal in `validation/` |
| --- | --- | --- |
| Premier O0 | 5 methods, 4 failures, 0.964 s, code 1 | `stored-inline-views-o0-first.log` |
| Second O0 | 5 methods, 1 failure, 2,037 s, code 1 | `stored-inline-views-o0-second.log` |
| Third O0 | 5 methods, 2,299 s, code 0 | `stored-inline-views-o0-third.log` |
| Fourth O0 | 8 methods, 4 sub-case failures, 2,757 s, code 1 | `stored-inline-views-o0-fourth.log` |
| Fifth O0 | 8 methods, 2 sub-case failures, 2.728 s, code 1 | `stored-inline-views-o0-fifth.log` |
| Sixth O0 | 8 methods, 1 failure, 3,526 seconds, code 1 | `stored-inline-views-o0-sixth.log` |
| Seventh O0 | 8 methods, 3,891 s, code 0 | `stored-inline-views-o0-seventh.log` |
| Final O0 | 9 methods, 3,625 s, code 0 | `stored-inline-views-o0-final.log` |
| O2 regression before normalization of cycles | 90 methods, 58,614 s, code 0 | `stored-inline-views-regression-o2.log` |
| O2 typed references before normalization of cycles | 12 methods, 10.671 s, code 0 | `stored-inline-views-typed-o2.log` |
| Final O2 after normalization of cycles | 33 methods, 17.997 s, code 0 | `stored-inline-views-final-o2.log` |

The first failures revealed the loss of the inner path in the result
built, the old reservations kept after replacement and
the missing ancestry of the mutable reborrowing returned. A type declaration
local incorrect has been moved to program level in fixture.
The following passages corrected the enum fixtures: manufacturer with
pool, notation existante `match (->c)` and field reading in a link
before print, compatible with the current arm validation. The limit test
async checks the diagnosis of the implementation encountered, without changing the wait
of refusal or claim that this case is now implemented.

The wide regression includes the modules of views, of the structures contained,
storage of reborrowing, mixed async structures and owner replacements.
The twelve historical tests of typed references are listed in full in
log; those using reset activate the compatibility profile.
Final normalisation of cycles is followed by O2 validation targeted at
stored views, proprietary field views, ABI views and the twelve
typed historical cases.

## Limites

The async catches and results containing these views remain open.
typed unconnected capture are always refused; creation control
tasks also refuse graphs containing views, instead of transmitting
their root as an ordinary target pointer. The results mixing
whole and internal references remain to be connected.

No new campaign of mutations or adversary generation; no
The suite is based on existing ABI C probes.
ASan and a second compiler C were not executed. These results do not prove
not the safety of all compositions.

Diffs : `validation/stored-inline-views-*.py.patch`, compared to the previous copy
`/tmp/crust-before-stored-inline-views/`.
