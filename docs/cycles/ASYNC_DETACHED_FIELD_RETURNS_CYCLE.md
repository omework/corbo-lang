[Français](ASYNC_DETACHED_FIELD_RETURNS_CYCLE-fr.md)

<a id="cycle--références-partagées-détachées-retournées-en-async"></a>

# Cycle — shared async-returned detached references

<a id="règles-et-périmètre"></a>

## Rules and scope

Application of ST13, ST11/ST12/ST14, B1–B5, D1, AS12/AS13 and MT3, without
AGENTS.md, VALIDATION_GUIDELINES.md, index of the
The project was consulted on the drafts and the field rules/results.
The overall seven drafts remain open.

Un champ `&Int` returned from a task keeps the external target and
He no longer artificially reserves the slot of the
The structure which contained this reference.
capacity `&mut Int` keep their carrier reservations. A junction
brings together the two kinds of dependencies when its branches mix them.

Async summaries and synchronous relay contracts distinguish these
projections. In states, a shared target origin does not block
a transfer independent of the carrier. The replacement of reference fields
in these states remains refused, in accordance with the restriction of implementation
This extension does not imply these already supported effects.

The bridge of synchronous helpers converts the `Cell *` d
address of its value before returning it to the ABI `int *` States.
A synchronous block can also provide an Int reference; its destination is
checked before cleaning, without promoting a local target.

<a id="scénarios-et-modèle"></a>

## Scenarios and Models

`tests/test_async_detached_field_returns.py` exercises direct writings,
appointed and `&*`, shared/mutable catches, children async, helpers,
methods, synchronous relays after join, independent mutations of the carrier,
destruction and reuse of its pool, last use of the target, ancestors
mutable results mixing external target and direct field.

Invalid neighbours destroy or alter the target prematurely,
destroy a still needed carrier, copy a mutable field or make
The control of the reset is to be carried out by the competent authority of the Member State in which the reset is located.
uniquement historique (`allow_legacy_reset=True`) ; the public API remains withdrawn.
A failure to launch is injected by EAGAIN, without changing expectations of
release of catches.

The independent model `test_async_detached_field_model` combines each result
to its logical storage (carrier or target), then compares an operation that
invalidate this storage before/after last use.
foretell eight executions and four refusals, verified at the two entrances of the
compiler. Expected values are calculated without consulting the contracts.
The two previous models of the field paths are also replayed.

<a id="preuves-exécutées"></a>

## Evidence

The newspapers quoted are in `validation/`.

- `async-detached-fields-block-o0.log` 11 methods, 7,662 s, OK,
  before additional block release and descent tests.
- `async-detached-fields-regression-o2.log` 61 methods, 51.261 s, OK;
  Async fields, reborrowing, contracts and expressions borrowed.
- `async-detached-fields-final-o0.log` 25 methods, 26.651 s, OK;
  The initial import of the model also rediscovered the twelve methods of its fixture.
  These repetitions are not new scenarios. L的import has been corrected.
- `async-detached-fields-models-o2.log` Three methods, 28.563 seconds, OK;
  12 combinations of the new model and 24 of each of the two previous models.
- `async-detached-fields-mutable-neighbor-o2.log` : the valid shared reborrowing
  d
- `async-detached-fields-complete-final-o0.log` 13 methods, 20.389 s,
  Okay, with the model and all the targeted supplements.
- `async-detached-fields-complete-mutations-o2.log` : baseline final of twelve
  methods, 16,652 s, OK; 27 C executions including an injected launch failure,
  32 invalid programs checked at both entries (64 checks).
  Four mutations detected, two survivors; expected output code 1
  for this balance sheet not fully detected.
- `async-detached-fields-destruction-o2.log` : one method, 2,593 s, OK;
  six variants check exactly `destroy v`, `reclaim v`, then
  `destroy data`, `reclaim data`without double destruction.

The expanded native regression `async-detached-fields-native-o2.log` termine
with 291 successful methods in 239,123 seconds. It started before the last two
additions of valid descent and mutable re-borrowing tests and
trace statements; these are covered by the final targeted passages.

The harnesses use Clang C11, pthread, fatal warnings and fatal UBSan,
with O0/O2 according to the newspaper. No results new ASan/TSan, second compiler,
performance measure or formal evidence is not claimed.

<a id="mutations-et-échecs-conservés"></a>

## Changes and failures retained

The first targeted campaign detects three mistakes and leaves three to survive.
Adding the valid neighbour of the mutable field then reveals the fault that was trying
to treat a mutable capacity as a copyable reference: control
The survivors of ancestry and of
Block border remain protected by other controls in the cases exercised;
No general equivalence is established.

The old campaigns have their anchors adapted to the factorization of the
projections, without changing their oracles: seven reborrowing errors and six
The campaign for field returns detects seven of the cases of the alleged breach of contracts.
errors; the omission of explicit target capacity remains as surviving as in the
Previous cycle. `async-detached-fields-reborrow-mutations-o2.log`,
`async-detached-fields-contract-mutations-o2.log` and
`async-detached-fields-return-mutations-o2.log`. An output code 1 of the
campaigns involving survivors is not presented as a global success.

The initial logs are kept:

- `initial-o0` - explicit destruction of a non-transferable source in the
  fixture; bridge C with incorrect pointer representation, corrected.
- `targeted-o0` and `complete-o0` : borrowed block result refused; two
  assertions of a test of mutable fields mistakenly placed in the test
  The fixture is corrected without softening memory expectations.
- The registered programme `open-async-detached-field-return.crust` omettait
  l’import `-> v;` necessary before drop in the child's arm. The test adds
  this explicit import; it does not remove the scope rule.

<a id="contre-exemple-encore-ouvert-et-limites"></a>

## Still open counter-example and limitations

Follow-up: the storage counter example below is now corrected and
tested in [STORED_FIELD_REBORROWS_CYCLE.md](STORED_FIELD_REBORROWS_CYCLE.md).
The defect and log below describe its state at the end of this cycle.

`open-struct-field-reborrow-stored-shared.crust` built a shared carrier
from a reborrowing of a mutable field of another carrier.
valid remains refused at the time of construction (`champ 'data' : &Int requis`),
before reaching the desired descent test.
`async-detached-fields-ancestry-o2.log` This case requires that the
the connection of reference representations when stored.

The coverage of this lot remains limited to fields Int/&Int/&mut Int and
The more general graphs, changes in the
field dependencies from the states, the full public runtime,
Select, mutex guards and general placement remain open.
The models are finished; the tests do not explore all the schedules.

The source and demonstration C are retained in
`validation/async-detached-field-fixed.crust` and `.c`. The differences with the
snapshots before the lot are `validation/async-detached-fields-*.py.patch`.
