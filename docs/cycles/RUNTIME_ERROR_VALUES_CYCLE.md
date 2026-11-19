[Français](RUNTIME_ERROR_VALUES_CYCLE-fr.md)

# Cycle RT5/RT6 — Valeurs runtime::Error

<a id="portée-et-règles"></a>

## Scope and rules

Application of the rules already retained in draft 04 and
ASYNC_MULTITHREAD_RULES.md, without change of normative. `runtime::Error` devient
a typed value: construction of `runtime::Error::LaunchFailed`, extraction
with `Err(error)`, copying by link, annotation, reassignment, parameter and
Back synchronous. Tasks can also capture and return this
value, keep it after yield, receive it by direct or in the
a join/wait result from a handle.

Code C distinguishes the launch status from the returned value:
`CrustJoinResult.runtime_error_value` contains a type of business result
runtime::Error ; `status` describes the launch. The error extracted does not keep
no dependence on destroyed catches or on loans that have been completed by waiting.
The separation of types prohibits its use as Int, u8 or reference
To Int. The Elders `Err(valeur)` vectors retain their payloads
and their contracts.

The re-examined interactions are AS2/AS8/AS10/AS12, RT4–RT7, MT1/MT3/MT5/MT6,
U1, explicit transfers, loop outputs and drop.
The public renet remains unchanged; historical reset tests use the
This cycle does not attempt to verify the
other types of results or all the compiler paths.

<a id="défauts-trouvés-et-corrections"></a>

## Faults found and corrections

- The assignment async passed through the Int evaluator and rejected a valid error.
  It now uses the evaluation of the type runtime::Error.
- The Err arm of a proprietary result was invalidated before extraction of the
  his error. L-extraction now reads the tag saved by match, without
  reopen access to the consumed result or read its payload.
- A single joker match async refused a runtime subject::Error calculated
  by if. The subject is evaluated once and his type is controlled.
- The result of a synchronous break was treated as an allocation and caused
  An exception Python. The result runtime::Error now has its type C and
  its value representation without an allowance.
- Drop of a runtime link::Error is now recognized in both
  It invalidates this link, without invalidating its independent copy.

The first reassignment test omitted the first value received:
the U1 diagnosis was correct. The test now reads this value before its
The branch generator uses an Int discriminant in the
two contexts; the former name Bool was not accepted by signatures
This prototype is synchronous.

The enlargement to loop tests has found four historical scenarios
without explicit use of an allowance received (`old`, `temp`, `b` ou l’ancien
read-outs have been added in `test_loop_results.py`. The oracles
destruction, reuse, limits of scope and invalid neighbours
It is not a release of U1.

<a id="preuves-exécutées"></a>

## Evidence

Clang Homebrew 20.1.3., arm64 macOS, C11. The 10 new methods run
19 binarys per level of optimization and check 27 rejected programs.
UBSan is fatal (`-fsanitize=undefined -fno-sanitize-recover=all`) Oracles
C tasks also activate strict warnings and pthread.

| Verification | Result | Trace |
| --- | --- | --- |
| Nouveau lot final O0, UBSan | 10 methods, 10,525 s, success | validation/runtime-error-values-O0-final.log |
| New O2 + results owners and loops | 37 methods, 22.241 s, success | validation/runtime-error-values-O2-validated.log |
| Historical loops with UBSan explicitly activated | 18 methods, 11,121 s, success | validation/runtime-error-loop-ubsan.log |
| First batch O2 + spawn_blocking, handles, capabilities, features async | 34 methods, 36,639 s, success | validation/runtime-error-values-O2.log |
| Async Regressions, Selected Contracts and Scheduler | 14 methods, 46,189 s, success | validation/runtime-error-regression.log |
| Useful loads Vector error and proprietary results | 37 methods, 32.897 s, success | validation/runtime-error-vector-regression.log |
| Replayed previous batch changes | 5 detected | validation/runtime-error-blocking-mutations.log |
| Changes targeted at error values, final version | 4 detected | validation/runtime-error-values-mutations-validated.log |

In the group of 37 methods, new tests and results tests
owners use O2/UBSan. The historical loop helper ignores
CRUST_TEST_OPT; these were therefore also replayed separately with
CRUST_SANITIZE=undefined (default optimization). The first group of 34
methods precedes the additions of the loop, calculated joker and drop cases: it replaces
No tests were jumped in these executions.

Independent models include a four-path table
(synchronous/async × choice 0/1), the markers and the result of which are fixed without
The historical model of block destruction has been
was also replayed with seed 20261103 (eight programs and their neighbours)
The other oracles control the success and the refusal injected of the
The same address, the single destruction, the liberation
d
result after dropping its initial target.

The programme `validation/open-runtime-error-value.crust`previously refused,
is successfully maintained and executed (7) and failed launch injected (1).
The old diagnosis remains in `validation/open-runtime-error-value.log` comme
preuve historique.

<a id="mutations-et-limites-des-oracles"></a>

## Oracle mutations and limits

Four errors are injected only in temporary copies: status
Err replaced by zero; reading the Int field instead of the enum async result;
accept an error like Int; Err async status replaced by zero.

Two survived the first passage (`runtime-error-values-mutations.log`).
A synchronous single variant match did not observe the performance
The test programs have been enriched: error recapture in
a task after cleaning and match in the task before returning. These paths
now observe both corruptions; the four mutations are detected.
The initial defect of the løoracle is not hidden and no overall rate is deducted.

There is no formal evidence or random competition campaign here.
Injected scheduler refuses launch without performing the task, in accordance with
The security of Arbitrary C is not assessed.
richer than a single variant and all containers of this value
are not covered.

## Travail encore ouvert

`runtime::Handle<T>` public, the general signatures of Result<T,runtime::Error>,
public replacement of the scheduler, wake-ups, fairness, runtime::thread,
Select and mutex guards still need to be integrated or completed.
construction of mutex remains carried forward by open points.md. Other lots
of the seven drafts are not reported completed by this cycle.

Historical state at the close of this cycle (resolved in
[PLAIN_JOIN_CONTRACTS_CYCLE.md](PLAIN_JOIN_CONTRACTS_CYCLE.md)) :
the next deviation was reproduced by `validation/open-runtime-result-contract.crust` :
a received and relayed Int join in two explicitly annotated contracts
Result<Int,runtime::Error> is still refused. The diagnosis performed is kept
in `validation/open-runtime-result-contract.log`. This restriction does not come
Not rules validated.

Reproduction controls:

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_runtime_error_values -v
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_runtime_error_values test_loop_results test_owned_results -v
CRUST_SANITIZE=undefined PYTHONPATH=.:tests python3 -m unittest test_loop_results -v
python3 tests/run_runtime_error_regression.py
python3 tests/run_spawn_blocking_regression.py
python3 tests/run_runtime_error_mutations.py
python3 tests/run_spawn_blocking_mutations.py
```
