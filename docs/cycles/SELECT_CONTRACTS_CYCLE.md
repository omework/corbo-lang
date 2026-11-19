[Français](SELECT_CONTRACTS_CYCLE-fr.md)

<a id="sl1--parsing-et-composition-des-contrats-de-select"></a>

# SL1 — Parsing and composition of Select contracts

<a id="portée-réelle"></a>

## Actual scope

This lot continues the [suspension contracts]](SUSPENSION_EFFECTS_CYCLE.md).
Syntax `runtime::select(-> tache1, -> tache2, ...)` is now gone.
The analysis of the async effects consists of the contracts of the branches, without performing
their bodies to creation and without re-tracing the bodies of synchronous helpers.

The catch verifier, the single waiting, the storage transfers and the
the select backend source still to be connected. A complete source program
containing Select is therefore not **not yet compileable** : he receives the diagnosis
`prototype async : expression task_select non prise en charge`. The test of
This border is not a normative ban, but a gap in implementation.

AGENTS.md, VALIDATION_GUIDELINES.md and the design-buffer index were followed;
SL1 and draft 04 define the intended behaviour. No new rule
Nor is there any policy of destroying the handles launched here.

## Composition

- Each argument must bear `->`. The arguments are evaluated in sequence;
  their synchronous effects are performed symbolically at construction,
  while transferred tasks remain inactive.
- The branches must have the same result, including mode.
  symbolic selection retains this type and the capture alternatives.
- For a possible winner, the contract applies its termination effects.
  Previous losers have necessarily been polluted: their states
  The following branches may be unpolished,
  or suspended from a previous round if the winner could suspend.
- A branch that never suspends prevents the following from being polluted:
  Makes Ready, or she doesn't give back the hand. The following bodies are then
  not necessary to describe the effects of this expectation.
- The appellant may suspend if all branches can.
  suspension combines the prefixes of the branches, without adding any effects
  and a future restoration.
- The result is only from the possible winners.
  persistent losers are kept independently of this result.
- A composition requiring an unknown summary remains unknown, with diagnosis.
  A selection created and then destroyed without waiting does not require knowing the
  body effects that are never executed.

The composition describes the field states; it does not replace the verification
two branches do not simultaneously capture the same target in an exclusive manner.
The retention of the catch until the drop of Select remains to be connected to the backend.

<a id="contre-exemple-corrigé-pendant-lintégration"></a>

## Counter-example corrected during integration

The selection descriptor was not recognized as transferable value by
analysis of conditional expressions and moves. The calculated fields
Therefore, a selection from an if could not be made to the appellant.
Selections are now admitted in these symbolic transfers; their
type includes the result and their set of alternatives retains the catches.
The test also covers `break <- selection` Then an explicit renunciation.

Programme retained:
[select-contracts-conditional-selection.crust](../../validation/select-contracts-conditional-selection.crb).
Reproduction before correction uses a temporary copy of `results.py`
and the same final oracles:
`validation/select-contracts-transfer-counterexample.log`. Refusal of analysis
is confirmed. The complete program remains subject to backend limitation
Select indicated above; only this contract error is removed by this lot.

<a id="validation-exécutée"></a>

## Validation executed

`tests/test_select_contracts.py` contains sixteen methods: parsing allowed/refused,
effects before restoration, non-polished branches, non-ending loser,
appellant's suspensions, construction without performance, synchronous arguments,
incompatible types, unknown summaries, borrowed returns, saved catches,
nested selections, conditional and loop transfers.

An independent model runs 25 pairs of small programs, with two
separate external fields. Its positions of instructions, writings, pauses
and choice of the first Ready are calculated without the compiler's contracts or objects.
The target actually left in each field must belong to the union
This check checks an inclusion: it does not demonstrate that the union
The cases determined by an immediate branch are minimal.
have in addition accurate assertions about the targets and the result borrowed.

A C probe uses two states and destroyers generated: the loser modifies
a first field, the winner a second. The result is 9; the two scripts
remain observable after drop of Select. Eight re-employments are executed.
The Select of this probe is built in the C harness, not yet since
the source syntax of the language.

Journaux sous `validation/` ; C executions employ Clang C11/pthread,
Wall/Wextra/Werrar and fatal UBSan:

- `select-contracts-initial.log` 11 analytical methods, 0.037 s, OK.
- `select-contracts-final-15-o0.log` 15 methods, 0.486 seconds, OK.
- `select-contracts-final-16-o0.log` 16 methods, 0.636 seconds, OK.
- `select-contracts-final-mutations-o2.log` : final baseline of sixteen methods,
  0.650 s, OK; eight mutations detected. They remove the explicit marker,
  substitute the termination of a loser to its suspension, forget the state
  no pollution, lose the origin of the result or the catches, omit the
  parent suspension, accept incompatible results or falsely require
  the contract of a branch that has never been polluted.
- `select-contracts-regression-o2.log` 74 methods, 9.524 s, OK, with the
  suspensions, existing contracts, synchronous results and Select C.
- `select-contracts-final-regression-o2.log` 83 methods, 7.413 seconds, OK,
  after correction of conditional transfers: sixteen new methods,
  15 suspension, 25 async contracts and 27 synchronous results.
- `select-contracts-prefix-mutations-o2.log` and
  `select-contracts-completion-mutations-o2.log` : the eight mutations of the
  suspension and 11 previous terminations are detected.
  of children not ending explicitly targets ordinary waiting after addition
  of the Select course; no assertion is weakened.
- Compilation Python of successful batch files.

The first passages to thirteen and fourteen methods are also preserved.
These counts overlap; they do not designate separate programs.
The mutations take place on temporary copies, without changing the oracles.

<a id="limites-et-travail-suivant"></a>

## Limitations and Next Work

Current summaries say that a branch *peut* suspension, without distinguishing
all paths that necessarily suspend before their first return.
Therefore, the union can retain an impossible winner in an execution
and protect too many targets. The immediate restoration/winning test
makes this limit explicit. The order of branches always immediately ready
is already operating, without imposing a new rule on the programmer.

The recognized injected fields and scalar/borrowed returns are composed.
Aggregated returns, other reference containers, competing effects
The signature of the mutex guards and the handrails have to be completed.
unknown do not become empty contracts.

The next integration should link these descriptors to the monitoring of catches and
of the single waiting, to the cleaning by scope and suspension, to the reception of the
The results and dimensioning of the selected state pools.
loser who owns a launched handle remains open. This lot does not end SL1,
No formal evidence or new ASan/TSan result.
