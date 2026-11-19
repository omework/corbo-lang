[Français](CELL_REFERENCE_BRIDGES_CYCLE-fr.md)

<a id="emprunts-stockés-par-les-auxiliaires-synchrones-des-tâches"></a>

# Borrowings stored by synchronous task auxiliaries

<a id="périmètre-et-changement"></a>

## Perimeter and change

No amended normative rules. B1/B2/B4, ST8/ST10–ST13, AS12/AS13 and
L1/L2 require that the target, its dependencies and identity be retained when a
auxiliary stores a loan in an object. The program kept in
`validation/open-async-local-stored-reference.crust` was accepted by the
but refused C: his assistant received a pointer
Int raw while the reference field was waiting for the target's Cell descriptor.
The newspaper `cell-reference-bridges-recorded-baseline.log` reproduces this difference
with the previous compiler. `cell-reference-bridges-recorded-final.log`
now shows the value 7 and the cleanup of the view and then the target.

The result contract now includes `stored_reference_parameters`.
This requirement also applies to temporary blinds in local objects,
even if no field is changed when you return. It crosses the relays
synchronous, methods and functions that never return. Inference
do not confuse this representation requirement with a final effect on the fields.

The bridges concerned receive the existing Cell. The async state finds it
from a local allocation, a transferred catch or a reference field of a
carrier. Several provenances are selected by comparing the pointer already
There is no copy of the target, no movement, no movement, and no other information is available.
artificial descriptor built around a raw pointer. Other arguments
Loans borrowed retain their previous ABI.
during the evaluation of the following arguments.

Two additional counter-examples have exposed an incorrect C for the
divergent auxiliaries: the non-return property was missing on the bridge,
then on the specialized synchronous function declaring an Int result. Both
declarations now use `_Noreturn`; a fatal guard ends the body
If this property was violated, the test compiles the bodies that differ with a
empty substitution C input: it does not claim to run their infinite loop.

<a id="vérification-exécutée"></a>

## Verification performed

Final Targeted Orders:

```
CRUST_TEST_OPT=-O0 PYTHONPATH=tests python3 -m unittest test_cell_reference_bridges -v
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_cell_reference_bridges -v
```

Fourteen methods succeed at O0 (14.271 s) and O2 (14.470 s), newspapers
`validation/cell-reference-bridges-final-o{0,2}.log`. The harness compiles the C11
with Clang, pthread, fatal warnings and fatal UBSan. Cases include
address identity before/after suspension, mutable target, reborrowed names,
conditional choices, non-first argument, returned references, destruction
premature refusal, re-use of a capacity pool one, native thread and refusal of
Injected launch. References to a non-representable target remain
diagnosed as a backend limit, not as a normative rule.

An independent model lists sixteen scenarios: last use before or
After the destruction, four sets of destroyed targets and two branches.
Ten programmes are implemented with the expected value, six are refused by the
`verify_program` and `compile_source`. The model uses target sets
The results of the analysis are available from the compiler.

The test of an external field replacement performs a bridge generated since
a C caller already checked synchronous. It proves this C precise border; it
does not prove that the same replacement is being taken over in a complete task.

Regressions of the lot, overlapping selections:

- 111 native/bridge methods, 111.037 s, before final corrective
  divergence : `cell-reference-bridges-regression-o2.log`.
- 159 synchronous methods: an old test violated U1 by never using
  `old`The other 158 succeed. Same error reproduced on the compiler
  previous preloaded from its isolated copy, journal
  `cell-reference-bridges-provenance-baseline-confirmed.log`. The first test
  The breeding industry did not properly isolate imports and is not evidence.
- The test adds the explicit reading of `old`, waits for its release 99 and then 20,
  and retains the assertions of one-time destruction.
  from the source pass in 34,563 s : `cell-reference-bridges-provenance-final.log`.
- 76 contract/function/feature/interlocked results, 46,143 s,
  before the last C patch: `cell-reference-bridges-final-contract-regression.log`.
- After the last patch, 45 function methods and expressions
  The difference is 32,641 seconds: `cell-reference-bridges-divergence-regression.log`.
- Compilation Python of modified modules and successful new tests.

Intermediate logs keep initial fixture errors
(address directly printed in the state and compilation reusing the same
Compile object), then the two faults C of divergence.
were not deleted to obtain the final passages.

`python3 tests/run_cell_reference_bridge_mutations.py` detects eight errors
in temporary copies: three loss of contract requirements, selection
wrong target, removal of the Cell parameter from bridge, incorrect ABI
the argument, no return to the bridge and to the ordinary function.
Journal final : `cell-reference-bridges-final-mutations-eight.log`. Stages
are distinguished: contract, rejection of a valid program, C compilation or value
This is not eight memory violations observed at the runtime,
or a general measure of the detection rate.

<a id="restant-et-limites"></a>

## Remaining and limitations

Update: Int catches of allocations are now connected by
the lot [descriptors captured](CAPTURED_CELL_DESCRIPTORS_CYCLE.md). The paragraph
the border reached at the end of this cycle.

Int references captured as a raw pointer and inline elements
do not yet have the durable descriptor required for storage in these fields.
Generalisation to other types and aggregates remains open.
auxiliaries modifying the dependencies of external fields remain active: it
must connect the effects to the states, handles and caller after waiting.
The previous cycle of inference was not an implementation of this propagation.

No new ASan/TSan evidence, no comparison with C compiler
There is no passage of the whole global suite.
The patches in the lot are stored under `validation/cell-reference-bridges-*.patch`.
The implementation objective of all rules remains open.
