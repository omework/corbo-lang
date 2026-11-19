[Français](PLAIN_JOIN_CONTRACTS_CYCLE-fr.md)

<a id="cycle-rt5rt6--contrats-de-résultats-sans-emprunt"></a>

# Cycle RT5/RT6 — Undebted profit and loss contracts

<a id="règles-appliquées-et-portée"></a>

## Rules applied and scope

This lot applies RT5/RT6, AS2/AS8, V3/V4 and U1, without any change in the regulations.
The guys `Result<Int,runtime::Error>`, `Result<Bool,runtime::Error>`,
`Result<u8,runtime::Error>`, `Result<char,runtime::Error>`,
`Result<(),runtime::Error>` and `Result<runtime::Error,runtime::Error>` are
The results of the analysis are presented in the following table:
be copied, reassigned, rendered by if/loop, explicitly processed or consumed.

These same values can be captured by a task and retained during
a suspension. The simple result of a handle.await can be annotated; its
The first is the "re-allocation" of the child, his/her transfer to a child's task and his/her destruction.
This support does not yet include the return of a Result
whole from an async function: see the deviation reproduced below.

The full type of the result is retained in the effects, effects, and effects analyses.
types of borrowing or allocation
are not converted into these modes without dependance.
and their monitoring of sources remain separate.

The representation C uses `CrustJoinResult`, now declared in the
common types. A signature can be checked without an active instance of
runtime. Status and payload are copied together, without new
This representation is not a promise of size optimization.

<a id="contre-exemples-et-corrections"></a>

## Counter-examples and corrections

- The programme `validation/open-runtime-result-contract.crust` was refused to
  The wait statement. It is now compiled and executed: output 7.
  The old diagnosis is kept in the associated .log file.
- The parser was treating `Result<...>=...` Like a token of comparison.
  type closure now cuts this token into `>` then `=` and preserved
  both tokens for the back of the parser. `2>=1` remains a
  comparison. Versions with and without space produce the same result.
- A fallible result from an async loop could be ignored. U1 is
  now checked on this path, including for the results families
  already known.
- Local values without destruction entry could retain their
  Drop mark beyond the block. Cleaning now removes this brand
  for the connections of the exited block, without reactivate an external link.
  A copy of Result destroyed in a block and then an Int bearing the same name
  are exercised after suspension.
- The auxiliary analyses described some of the attachments by type of their
  payload, or even by an unknown type. They now use the same
  type Complete result for the six cases and extract the right type in Ok/Err.

Deux anciens tests (`test_constraints` and `test_effects`) were also
migrating to U1: read `old`/`a` The assertions on sources
and borrowing conflicts are preserved.
The historical profile of reset remains explicit; no public API reset
n is reintroduced.

<a id="vérifications-et-oracles"></a>

## Verifications and oracles

The 11 methods of `test_plain_join_contracts.py` cover 32 native executions
The 24 central configurations follow a table
independent: six payloads × launch success/refusal × relay
synchronous/capture async. Expected outputs are fixed by this table,
The cases complete this table by the
branches, loops, annotations, copies, drop, re-use of name and a
comparaison `>=`.

The refusal to launch is injected into the only blocking callback.
and the consumer can always start. The error must go through the same
a copied capture remains usable after drop of the
source link; destroyed link is no longer readable.
n- accepts neither a result of another type nor its use as integer or
reference to an integer.

The six neighbours with borrowed/owner charges are refused: calls
the simple contract is rejected on the grounds of incompatible type; the annotations on
These joints are rejected by their existing binding restriction.
therefore do not demonstrate the general ownership of the signatures borrowed.

Clang Homebrew 20.1.3., arm64 macOS, C11, UBSan fatal for native programs
The task oracles activate pthread and strict warnings.
The old effects/contraint helpers use their default optimization,
even when CRUST_TEST_OPT is O2; CRUST_SANITIZE=undefined activates their UBSan.

| Implementation | Result | Trace |
| --- | --- | --- |
| New final batch at O0 | 11 successful methods, 12,959 s | validation/plain-join-contracts-O0-current.log |
| New O2 lot, runtime::Error, constraints and effects | 67 successful methods, 30.243 s | validation/plain-join-contracts-validated.log |
| Frontier between simple results, borrowed and owners | 1 method, 6 refusals expected | validation/plain-join-contracts-borrow-boundary-final.log |
| Lots capacities and features async with the first 9 methods of the lot | 23 successful methods, 28.777 s | validation/plain-join-contracts-O2.log |
| runtime::Error, spawn_blocking and handling obligations | 24 successful methods, 25,069 s | validation/plain-join-contracts-regression.log |
| Old typed results, calculated expectations and ABI | 15 successful methods, 28.690 s | validation/plain-join-contracts-typed-regression.log |
| Async contracts, owner results and scheduler after harmonization of analyses | 14 successful methods, 40,153 s | validation/plain-join-contracts-runtime-final.log |
| Targeted changes | 4 detected | validation/plain-join-contracts-mutations-final.log |
| Running cycle changes::Error replayed | 4 detected | validation/plain-join-error-mutations.log |

The first ten methods are included in the final group of 67; the
11th, which produces only six refusals, was executed separately and then in the
Full O0 batch. Initial logs keep failures: tokenization error,
lack of U1 loop verification and non-migrated historical tests.
Regular diagnostic expression adjustments did not replace a
refusal expected by acceptance.

The four mutations are applied in temporary copies: delete
verification of payload type at a synchronous call; delete it
to an async capture; replace the error status received with a success; omit
mandatory use of the loop result. They are all detected.
overall detection rate and no evidence of safety is deducted.

<a id="limites-et-prochain-lot"></a>

## Limits and next batch

Difference at the end of this cycle, corrected since
[NESTED_PLAIN_RESULTS_CYCLE.md](NESTED_PLAIN_RESULTS_CYCLE.md) :
return `async fn wait() -> Result<Int,runtime::Error>` The
programme minimal `validation/open-async-plain-result-return.crust` and its
.log show this gap: its join should produce an nested result and
preserve the distinction between business error and launch error.

General signatures with borrowings, containers and
wider interlocks, runtime::Handle<T>, general manufacturers of
Result and other open running sites. The lot does not validate
Fairness, revivals, Select, explicit native threads or mutex.
Mutex manufacturers and border C remain carried forward according to the
consignes normatives. Il n’y a ici ni preuve formelle ni campagne ASan/TSan.

Validation targeted affected interactions and listed follow-up,
not the monolithic deposit set. The goal of the seven drafts remains
active and incomplete.

Commandes principales :

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_plain_join_contracts -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_plain_join_contracts test_runtime_error_values test_constraints test_effects -v
python3 tests/run_plain_join_regression.py
python3 tests/run_spawn_blocking_regression.py
python3 tests/run_plain_join_mutations.py
python3 tests/run_runtime_error_mutations.py
```
