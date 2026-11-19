[Français](NATIVE_SYNC_CALLS_CYCLE-fr.md)

<a id="cycle--appels-synchrones-depuis-les-états-natifs-et-async"></a>

# Cycle — Synchronous calls from native and async states

Next: [parameters and results borrowed](SYNC_BORROW_CALLS_CYCLE.md).
The limitations below describe this first scalar lot; the borrowings
Int and mutable u8 are now connected in the next cycle.

<a id="règles-et-périmètre"></a>

## Rules and scope

This cycle continues RT8, B4/B4a/B4e, RT5, AS7 and L1/L2/L6 without changing
The rules of the rules of the law.
drafts, LANGUAGE_RULES.md and extension async were consulted.

The Counter-Example `validation/open-native-sync-helper.crust` is now
accepted and executed: the native block calls add(7), then join provides 8.
The new border covers the parameters and results Int/u8/char and the
Void result. The functions called can use their synchronous code
usual: other calls, local pools, borrowings, drop, methods, creations
and join when context allows. References and values
owners do not yet cross this new call frontier.

The call does not assign an intermediate task. The C calls a function
regular synchronous; its local resources are cleaned before it returns.
The parameters are evaluated and stored from left to right before call C.
A return while preparing an argument leaves the appellant and prevents
An Int named does not implicitly become u8.

<a id="contrats-et-traduction"></a>

## Contracts and translation

The collection of functions now precedes the generation of states.
The sources of the async results are calculated before the
the callers' checks. The generation of states keeps its validation
before synchronous bodies to diagnose invalid bodies
They themselves, and not only their consequences in the appellant.

The call from a state uses FunctionContract. It reserves a symbol C
without opening the body of the calle. The symbolic verification of each function
Keeps its opaque calls. The specialized backend produces auxiliary
once per function called, after verify, in Compiler.compile. A test
explicitly forbids this backend during verify_program and checks that
relay and hand are each visited once, without any nested call pile.

FunctionEffects transmits the blocking_join effect through calls and
Resolved methods. An async state refuses an auxiliary bearing this effect;
a native block allows. Creating and then destroying an inactive task does not constitute
The calls are still unsuspended.

FunctionContract also retains a conservative synchronous_task_slots,
obtained from the body locations verified and subcall contracts.
These terminals contribute to each calling state instance.
includes intermediate synchronous calls; for methods it includes
The cycles thus revealed are preserved with the same name.
This approximation may overestimate storage
and demand an additional configuration; it is not an optimal terminal.

<a id="scénarios-et-recherche-de-contre-exemples"></a>

## Scenarios and Counter-Examples

`tests/test_native_sync_calls.py` contains twelve methods: fourteen executions
Crust/C and 17 refusals expected in full passage, plus comments
contracts, capabilities and body visits.

- Entangled and Void calls: traces 1, 2, 30, 12, 14 in native appellants
  Two local allowances are destroyed exactly once,
  with values 12 then 13; the capacity pool one is reused.
- An auxiliary calls read(&Int), copies the result and then destroys the allowance.
  Drop before last reading, read after drop and reset public
  are refused.
- u8 and char are transmitted without confusion with Int; errors of type, of inarity,
  d , borrowing and overtaking of the literal u8 are refused.
- A target caught by borrowing remains protected at the caller during
  native execution, although the auxiliary receives only one copy of its value.
- Join behind two auxiliaries: success, failure of the child launch and failure
  native launch; refusal from an async state and refusal to abandon the handle.
- Eight parents can each retain three children.
  cover at least 24 children; the eight results are carried out.
  The capacity test does not claim to impose a scheduling where the twenty-four
  children are allocated simultaneously.
- Creation cycle through a function, then through a local method:
  refusal without configuration and execution with two slots explicitly configured.
- Return during an argument: trace 1 then 7, without executing the body pair.

The oracles are traces, types, life obligations and terminals
d.O.P. derived from the rules. There is no random generator added
The results of contracts and contracts and the
the existing running time is still necessary; the only tests of this module are
Not proving the safety of all interactions.

<a id="défauts-intermédiaires-et-mutations"></a>

## Intermediate defects and mutations

The first regression found KeyError on reference sources
async: they were read before they were calculated.
This is the case with the following errors: Move the synchronous bodies check before the one of the
states also changed the diagnosis of an unsustainable slice; the final order
diagnostics again the async body faultless without modifying the test.
Intermediate newspapers are kept, including native-sync-regression-o2.log
and native-sync-regression-o2-final.log; despite its name, it contains
This failure of diagnosis is not the final validation.

Mutations use temporary copies of the compiler, without changing
tests: order of the arguments reversed, hidden join accepted since async,
Indirect creation edges omitted, contribution of auxiliary slots omitted.
The first three were detected in the first passage.
survivors of the initial case of two parents: other over-evaluations masked
The case of eight parents now detects a capacity to
The initial and the initial journal
the reinforcement is retained; no general detection rate is claimed.

<a id="résultats-exécutés"></a>

## Implemented

| Journal in validation/ | Result |
| --- | --- |
| native-sync-initial.log | Three first probes: 8, 9 with 7/8 destruction, then 7 with child launch |
| native-sync-o0-initial.log | First batch: 9 methods, 7,126 s, OK |
| native-sync-regression-o2.log | First regression: errors of source and diagnosis, retained before correction |
| native-sync-reference-fix.log | Two methods of borrowed returns: 2,371 s, OK |
| native-sync-contracts-o2.log | First contract regression with the 9 new methods: 114 methods, 34.741 s, OK |
| native-sync-regression-o2-final.log | Second intermediate regression: 90 methods, a diagnosis still different; this journal is not a final pass |
| native-sync-order-fix-o0.log | Corrected diagnostic and first batch: 10 methods, 10,526 s, OK |
| native-sync-separated-o0.log | Separate verification/generation: 11 methods, 6,010 s, OK |
| native-sync-final-o0.log | Final version: 12 methods, 11,017 s, OK |
| native-sync-final-contracts-o2.log | Effects, modular contracts, body, capabilities, arguments: 105 methods, 34,059 s, OK |
| native-sync-final-regression-o2.log | Native/async regression: 93 methods, 105,309 s, OK, no jump |
| native-sync-mutations.log | Three mutations detected, initially surviving slots omitted |
| native-sync-slots-mutation.log | Enhanced test: slot omission detected |
| native-sync-final-mutations.log | Four mutations detected on the final version |

```sh
PYTHONPATH=tests CRUST_TEST_OPT=-O0 python3 -m unittest -v test_native_sync_calls
PYTHONPATH=tests CRUST_TEST_OPT=-O2 python3 -m unittest -v test_effects test_modular_calls test_function_bodies test_async_capacity test_arguments
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
CRUST_TEST_OPT=-O2 python3 tests/run_native_sync_mutations.py
```

New native executions and runtime regression use Clang C11,
pthread, strict warnings, UBSan and `-fno-sanitize-recover=all`.
The old synchronous modules retain their own configurations;
The 105 method pass does not mean that each executes C under UBSan.
This is not all the tests of the deposit.
selected modules and paths, not on all Crust programs.
Modified modules pass py_compile and local document links
modified are checked in `validation/native-sync-final-artifacts.log`.
The diff of implementation and new tests is kept in
`validation/native-sync-implementation.patch`.

## Limites restantes

RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2 RT2
of tables and aggregates to these auxiliaries remain to be connected with their
Source and Exclusive Contracts. Bool synchronous signatures are
The local pools are still refused, regardless of this new connection.
direct in async/native bodies, general catches and type
public runtime::Handle<T> restent ouverts. Trois programmes valides encore
refused and their diagnoses are kept in native-sync-artifacts.log.

`validation/native-sync-helper.c` is the C actually generated since the
The second example is the "Study of the "A" model, which shows the prototype of the "A" and the "Study of the "A" model.
The argument in a temporary, the call from the summary, then the scalar return
and task_native_start. The other obligations of the seven drafts remain
no formal evidence, validation of TSan, second
compiler or new ASan validation: ASan blockages already recorded
were not presented as passes.
