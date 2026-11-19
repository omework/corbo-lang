[Français](HANDLE_OBLIGATIONS_CYCLE-fr.md)

<a id="cycle--attente-obligatoire-des-handles"></a>

# Cycle — Mandatory waiting for the handle

<a id="décisions-intégrées"></a>

## Integrated decisions

The latest version of draft 04 is integrated into the
`ASYNC_MULTITHREAD_RULES.md`It replaces the old decisions on the
spawn, hand-abandonment, public waiting types and capabilities
This normative integration does not take place in the context of the
does not mean that these features are all implemented.

This lot implements RT7: all handle must be explicitly expected.
synchronous auditors and async refuse its destruction and an exit that
The refusal no longer depends on the presence of loans,
The same applies to the
static captures and tasks without capture. Transfer retains
the obligation until the receiver is waiting.

The inactive instance remains destructible according to AS14; the result obtained
after waiting remains destructible according to its own type.
a handle already consumed remains an invalid use.
abandoning a living handle now receives the waiting diagnosis;
This does not yet generalize the reassignment of the prototype's handle.

<a id="vérifications"></a>

## Verifications

`test_handle_obligations` covers explicit destruction, scope purposes,
returns, break, continuous, down transfer, block/loop receiver,
manufactures and synchronous relays, as well as as async and synchronous branches.
The signature of the handle of these tests still uses the old notation
Internal exposure `Execution<fonction>` ; l'API `runtime::Handle<T>` remaining to
Implement.

The independent model combines an obligation, consumed, with each path
only by explicit expectation. It lists the two branches with the
Wait/drop/out actions: nine synchronous configurations and nine asyncs,
two admitted and sixteen refused. He does not question the compiler's statements
The two branches of the admitted case are executed.

The launch failure test injects EAGAIN to create the thread.
makes the error after unique destruction of the owner capture and slot
is reused at the same address. Public names `runtime::Error` and
`LaunchFailed` are not yet integrated into the parser; the test observes the
Arm Err of existing protocol.

The newspapers are kept under `validation/handle-obligation-*.log`.

- `CRUST_TEST_OPT=-O0 PYTHONPATH=tests:. python3 -m unittest
  test_handle_obligations -v` : 8 methods successful in 7,883 s,
  `handle-obligation-final-O0.log`. Both helpers respect this level,
  including the launch failure injection.
- O2 passage instrumented from the same module: 8 successful methods in 8.242 s,
  9 compiled sources, 10 native executions, 34 rejected programmes and one
  additional verification permitted to control the AS14 warning.
  Journal `handle-obligation-counted-O2.log`.
- C11, pthread, UBSan and `-fno-sanitize-recover=all` ; runtime oracles
  also use the C warnings processed in error.
- `PYTHONPATH=tests:. python3 -m unittest test_handle_obligations
  test_async_type_features test_utf8_try_slice_async test_owner_usage
  test_owned_results -v` : 44 methods successful in 63,768 s at O2,
  `handle-obligation-O2-regression.log`The eight new methods are:
  included in this account; it does not add as 44 independent properties.
- `CRUST_SANITIZE=undefined PYTHONPATH=tests:. python3 -m unittest
  test_async_runtime -v`: 275 methods performed in 465.478 s. First
  pass: 264 successful, 7 errors and 4 failures, all preserved in
  `handle-obligation-initial-regression.log`.
- The 11 methods were migrated and successfully re-executed:
  in `handle-obligation-final-migrations.log` 11.886 s), two in
  `handle-obligation-U1-migrations.log` (9,710 s). Names and assertions
  modified fixtures remain in `test_async_runtime.py`. Il s'agit
  a first pass followed by targeted corrections, not a new one
  passes monolithic of the 275 methods on a final frozen copy.
- Compilation of successful modified modules and tests.

The first version of the new replacement test was waiting for a diagnosis
but first met the general reassignment restriction.
The compiler now reports the handle still waiting precisely;
The general reassignment remains outside this lot.
test down, replace drop with await no longer tested the same displacement
explicit. The case now retains re-commission `<-` before waiting, with
the same refusal when the downward transfer is missing.
in failure are preserved (`first`, `migration`).

<a id="migration-des-preuves-historiques"></a>

## Migration of historical evidence

The old tests admitted to abandoning handles without local dependence,
In particular, with a table result or a static text capture.
programs become expected refusals according to RT7.
are explicitly waiting with join/wait; their assertions of result and of
cleaning is kept. Auxiliaries who abandoned a handle are kept
removed from the fixeds allowed and reintroduced only in the variants
refused, even when they are never called.

The C oracles of the historical register of abandonment remain exercised as tests
They no longer justify an operation admitted in Crust.
in this register does not replace the static requirement to wait for a Crust programme.

An earlier allowance return fix left its unused recipient
Before attempting to reuse the transferred name, it first triggered U1.
The test now explicitly destroys this receiver before checking the
The waiting for diagnosis is not weakened.

Two other U1 fixtures were corrected: the alias variant no longer allocates
a spare value that has become unused, and the variant of results of
incompatible branches destroys its owner's result before rendering a
Int. The game `Ok(_)` who did not know a nested owner result becomes
an explicit refusal; its accepted variant names and then destroys the payload.

## Mutations

`python3 tests/run_handle_obligation_mutations.py` works in copies
Three mutations detected:

1. Reauthorizing synchronous abandonment: Unsuspected paths are accepted
   wrongly by the branch model.
2. Reauthorize abandonment async: drop and unsuspected exits are accepted.
3. Omit cleaning after fail of launch: the capacity pool one
   The attempt to re-employ is still busy and the failure to re-employ is `pool capacity exceeded`.

The campaign is targeted; it does not measure general coverage of the
or evidence of safety.

<a id="écarts-restant-dans-le-brouillon-04"></a>

## Differences remaining in draft 04

- AS7: static limit/explicit capacity per pool, directive
  `async_pool_sizes` and recursion. The current fixed capacity C does not satisfy
  Not these rules alone.
- RT2–RT4: direct public installation in hand, Scheduler interface,
  queues/warnings/fairness, migration between poll and spamn_blocking.
  current create thread by spamn remains allowed, but does not show
  the capabilities of the target scheduler.
- RT5–RT6 : types publics `runtime::Handle<T>` and `runtime::Error`, variante
  LaunchFailed and overall results envelopes.
- RT8 : bloc synchrone `runtime::thread`, explicit catches and results
  Inferred.
- SL1 : Select, order of eligible branches, single result and conservation
  losers until they destroy.
- MT9: Thread-related synchronous guards and async-migrating guards.
  syntax of mutex manufacturers remains expressly postponed.
- Captures of structures and other boundaries of the already recorded backend async.

The overall batch remains open. Tests performed do not prove all the
combinations of paths, or the general absence of races; no new
TSan passage or formal evidence is not claimed.
