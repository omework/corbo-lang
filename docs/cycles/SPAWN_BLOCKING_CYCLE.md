[Français](SPAWN_BLOCKING_CYCLE-fr.md)

<a id="cycle-rt4rt6--lancement-bloquant-et-erreur-de-lancement-publique"></a>

# Cycle RT4/RT6 — Blocking launch and public launch error

<a id="règles-et-portée"></a>

## Rules and scope

Application of draft 04 and RT4–RT7, without change of regulations.
`runtime::spawn_blocking(-> tâche)` is now recognized by the parser,
contracts and both launch backends. L
blockage until generation of `task_thread_start_blocking` ou
`task_async_start_blocking`.

The internal C interface of the scheduler displays a separate callback
`launch_blocking`. The default pthread scheduler creates an independent thread;
This choice is allowed by the rules and does not claim to implement a line of
reusable workers. An internal implementation that does not provide callback
blocking refuses this launch with ENOTSUP; it does not redirect it silently
The two tracks share the state transitions and the
The handle keeps its obligation to wait.

The public name `runtime::Error` replace experimental name `JoinError` in the
signatures of proprietary results already supported, including the
The corresponding sources of data are: `test_async_runtime.py`
have been migrated without changing their scenarios or their security claims.
`Err(runtime::Error::LaunchFailed)` is accepted in the games of join/wait.
The C now uses the constant named `CRUST_RUNTIME_LAUNCH_FAILED`.
Business errors remain in the inner result.

The recognition of this variant is typed: a UTF-8 result cannot be
be treated as a launch error, and a launch result cannot
not be treated as a CharAtError, even if internal codes are reused.
Runtime integration::Error remains **partielle** : see the limits below.

<a id="invariants-et-contre-exemples"></a>

## Invariants and counter-examples

- The blocking choice does not change the catches or their provenances. The task is
  transferred once and cannot be re-launched.
- A failure of launch destroys the catch before making the error waiting.
  The Int capture slot becomes available again; its address is reused and
  His destruction is not repeated when the parent leaves.
- The handle must be expected, even if the task has not been borrowed or if its
  Drop and exits without waiting remain refused.
- The booking of a &mut Int follows the handle through synchronous contracts.
  Reading, writing, drop and historical reset are refused before waiting;
  mutation after join is allowed.
- The nested owner result distinguishes Ok(Ok), Ok(Err) and Err. The result
  interior remains usable after cleaning the external task frame.
- A default worker blocked on a condition does not prevent a second worker
  The general requirement is that the person who is not in the public service is required to report this condition.
  the blocking section before starting the second worker, without delay
  This scenario does not prove the general fairness of the scheduler.

The independent delegation model covers eight configurations:
standard/blocker, calling synchronous/async, scheduler that accepts/refuses the
The expected result is fixed by this table, without reading the choice
The tests check the values, the re-used addresses and the
A second oracle C distinguishes the meters from the two callbacks,
refuses a blocking callback missing and observes four unique releases.

<a id="vérifications-exécutées"></a>

## Audits performed

Clang Homebrew 20.1.3 on arm64 macOS; C11, UBSan fatal
(`-fsanitize=undefined -fno-sanitize-recover=all`) Oracles C impose
`-Wall -Wextra -Werror -Wno-unused-function -pthread`.

| Implementation | Result | Trace |
| --- | --- | --- |
| New batch at O0 | 6 successful methods, 11,740 s | validation/spawn-blocking-O0.log |
| New batch + compulsory handles + async capabilities + features async to O2 | 28 successful methods, 31.516 s | validation/spawn-blocking-O2.log |
| Current scenarios concerned, regular spawn | 14 successful methods, 43.697 s | validation/spawn-blocking-regression.log |
| Same scenarios, Crust calls replaced by spamn_blocking | 14 successful methods, 43.890 s | validation/spawn-blocking-injected-regression.log |
| Final diagnosis of unknown variant | Successful approach | validation/spawn-blocking-diagnostic-final.log |
| Mutations | 5 detected | validation/spawn-blocking-mutations-final.log |

The six new methods execute 13 binarys per level of optimization and
check 15 rejected programs. The 14 replayed methods are selected
explicitly by `tests/run_spawn_blocking_regression.py` : results of the owners
and nested with the public name of error, mutable reservation, re-employment between
Iterations, conditional hand transfers, UTF-8 contracts and border
scheduler. L’option `--blocking` replaces only the launch calls of the
The results of the project are not changed.

Mutations made in temporary copies: loss of blocking marker
at synchronous backend; loss to backend async; ordinary callback called to the backend
blocking callback place; cleaning omitted after failure; confusion between
runtime::Error and UTF-8 errors. All are detected by failures
No overall detection rate is deducted from these five errors.

Main reproduction controls:

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_spawn_blocking -v
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_spawn_blocking test_handle_obligations test_async_capacity test_async_type_features -v
python3 tests/run_spawn_blocking_regression.py
python3 tests/run_spawn_blocking_regression.py --blocking
python3 tests/run_spawn_blocking_mutations.py
```

<a id="limites-et-suite-du-travail"></a>

## Limitations and continuation of work

Historical status of the lot. The next cycle [RUNTIME_ERROR_VALUES_CYCLE.md](RUNTIME_ERROR_VALUES_CYCLE.md)
resolves the first deviation below for the contexts tested.

- `runtime::Error` is not yet an autonomous value transmitted by a
  liaison `Err(error)` then by a function call. The program conforms to the
  cible normative `validation/open-runtime-error-value.crust` remains refused;
  his diagnosis is recorded in `validation/open-runtime-error-value.log`.
  This refusal is a deviation from implementation, not a rule retained.
- Generic signatures `runtime::Handle<T>` and all forms of
  `Result<T,runtime::Error>` The signatures of the owners have yet to be incorporated.
  This is not evidence for all types of results.
- L’installation publique `runtime::set_scheduler` directly in hand, the
  conservation of revivals and general policy of recovery/migration remain
  Open. The callback tested here is an internal C border, not an API of
  customisation of the scheduler already offered to the language.
- `runtime::thread`, Select and mutex remain open.
  mutex remain carried forward according to open points.md.
- The arbitrary C is not verified. The callbacks of the l'oracle respect their
  contract: a refusal to launch did not perform the task. This lot does not prove
  the security of a callback that would violate this contract.

The entire sequence of the deposit was not restarted in this cycle; the lots
and their interactions are listed above.
drafts remain open.
