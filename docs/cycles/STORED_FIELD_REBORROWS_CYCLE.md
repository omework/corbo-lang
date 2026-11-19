[Français](STORED_FIELD_REBORROWS_CYCLE-fr.md)

<a id="cycle--stockage-des-réemprunts-de-champs-mutables"></a>

# Cycle — storage of reborrowing of mutable fields

<a id="règles-et-corrections"></a>

## Rules and corrections

Application of ST4, ST8, ST11–ST14, B1–B5, D1, AS12/AS13 and MT3.
AGENTS.md, VALIDATION_GUIDELINES.md and the index of drafts are read;
The rules retained do not change. The seven drafts remain partially
The overall objective remains open.

The programme retained in
`validation/open-struct-field-reborrow-stored-shared.crust` run now.
View porter contains a shared loan obtained through the capacity
mutable from a Writer. Destroy View after join does not invalidate the result;
destroy Writer or his target before last use remains refused.

Un réemprunt d’un champ `&mut Int` conserve désormais la représentation de
its actual allocation (`Cell *`), as with other references to allowances.
Int fields that are directly contained always use a content pointer
(`int *`) Contracts and join results maintain this distinction,
including after a helper, method, factory or handle received as a parameter.
The results mixing direct and indirect fields retain their
common representation of content pointers and the union of their reservations.

Field reservation is kept in the catch chain.
Projections typed through an enum have a single derived capacity
The contracts of the
returned structures also resolve the origins of indirect fields.
The typing passage of native blocks deduces the type of a `pool.new` appointed
from his pool, instead of producing a None type and a Python exception.

Runtime C is not changed. C of corrected counter example is retained
in `validation/stored-field-reborrow-fixed.c`. The compiler's diffs,
of the analysis of the results and the native passage are in
`validation/stored-field-reborrows-*.py.patch`.

<a id="scénarios-et-modèle"></a>

## Scenarios and Models

`test_stored_field_reborrows` covers shared and mutable references
stored from a field, named aliases, helpers/methods, relays,
the factory of a bearer, its copy, its async or native return, destruction
and the re-use of the original slot after last use. Invalid neighbors
modify/destruct the original carrier or its target too soon, or export
a reference linked to a local carrier. Two refusals to reset employ only
the historical profile. The rejected injection test checks the same cleaning
unique as the normal path: View, Writer, then Int.

The model `test_stored_field_reborrow_model` maintient un graphe logique
result → Writer field capacity → target, without consulting the objects of the
compiler. It examines sixteen combinations: independent or invalid access,
before/after last use, with/without helper. Ten programs run and six
The three previous models of the fields and the
detachment are also replayed.

<a id="preuves-exécutées"></a>

## Evidence

The following newspapers are in `validation/`.

- `stored-field-reborrows-complete-final-o0.log` : nine methods,
  12,669 s, OK, with the independent model.
- `stored-field-reborrows-complete-mutations-o2.log` : baseline finale of
  eight methods, 8,525 seconds, OK; fourteen C executions, including one launch refused
  Injected, and 28 invalid programs checked at both inputs (56 controls).
  Six injected errors detected.
- `stored-field-reborrows-models-o2.log` : nine methods, 22,323 s, OK,
  before the last manufacturing/copy/re-use supplements; three models
  The initial six methods of the batch were used.
- `stored-field-reborrows-final-model-o2.log` Two methods, 4,511 s, OK;
  new model and projection typed through an enum.
- `stored-field-reborrows-relays-o2.log` 35 methods, 24.486 seconds, OK;
  field returns, mixed contracts and separate references.
- `stored-field-reborrows-fields-resolved.log` 76 methods, 48,200 s,
  75 successes and a diagnosis of corrected historical fixture.
  `stored-field-reborrows-historical-last.log` : this method succeeds,
  1.596 s. The journal of 76 methods remains presented with its failure.
- `stored-field-reborrows-helper-mutations-final-o2.log` : baseline of eight
  methods, 4,140 s, OK; ten C executions, sixteen refusals to both entries,
  six mutations detected, including classification of inline result
  through the handle received as a parameter.

The expanded native regression `stored-field-reborrows-native-o2.log` termine
with 297 successful methods in 226,611 seconds. It started before connection
the return of the holder contract and the
latest tests of copying, re-use, launch refused and inline result of
These supplements are covered by the final targeted passages.

The new harnesses use Clang C11/pthread, fatal warnings,
UBSan fatal and O0/O2. Historical tests of `test_foundation_rules`
do not add explicit optimisation option, even in a log named O2.
No new ASan/TSan pass, second compiler or performance result.

<a id="mutations-et-contre-exemples-intermédiaires"></a>

## Intermediary transfers and counter-examples

The six targeted mutations withdraw the reference representation of allocation,
alter the classification of the result of helper, omit the reservation of the
field or its descent to the join, restore the refusal of the planned catches,
or omit the origin of the field in the returned carrier. All are detected,
This is not a universal rate.
The omission of ancestry, surviving from the previous batch, is detected
by the new program that has a separate external mutable carrier.

Previous field returns campaign retains seven detected mutations
and one survivor (`join_target_capability_omitted`) : its control changed
now concerns the representation of mixed results and the selected test
does not establish its general equivalence.
`stored-field-reborrows-return-mutations-o2.log`.
The first recovery of helpers mutations detects five errors and leaves
surviving the former classification mutation: the case selected did not include
more inline result. A neighbor returning a direct field via a handle
received has been added and anchor adapted to the new screening control.

The original newspapers remain kept:

- `initial` then `capture` : refusal of projected capture, corrected after connection
  the initial program then displays 7 and 7.
- `helper-probe` : result classification still incompatible with the field,
  corrected in analysis and contracts.
- `canonical-contracts-o2` : three errors and two failures exposed the unions
  Inline/indirect, the exclusive of the mutable parent and the relay of a handle.
  Corrections retain existing tests.
- `canonical-o0` : the first thread snippet had a non-compliant capture,
  then the native passage revealed the None type of a pool builder.
  capture named explicit and inference of type are corrected.
- `container-relay-o2` : target absent from the returned holder's contract; the
  connection of indirect origins corrects this refusal.
- `nested-probe` : double counting of a capacity through an enum; corrected
  without deleting the reservation of this enum or its target.

The five historical diagnostic failures were replicated on snapshots
before that lot (`stored-field-reborrows-historical-baseline.log`) Alternatives
disabled persons had removed the use of an allowance only and declared U1
before the desired memory control. Explicit readings have been added to
These alternatives alone; their expectations of refusal of memory remain unchanged.

## Limites

This lot does not generalize the storage of references to inline boxes of
tables/structures or all graphs of aggregates.
field dependencies from async states remain open.
The public runtime is not exhaustive.
The complete, Select, mutex guards and general placement remain to be realized.
