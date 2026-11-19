[Français](BUSINESS_RESULT_ENVELOPES_CYCLE-fr.md)

<a id="cycle-rt5rt6--enveloppes-des-résultats-métier"></a>

# Cycle RT5/RT6 — Envelopes of business results

<a id="règles-et-portée"></a>

## Rules and scope

Application of AS2/AS4/AS12, RT5/RT6, U1 and existing conversion rules
V3 and UTF-8 channels. No normative rules are amended.
AGENTS.md, VALIDATION_GUIDELINES.md, design-buffer index and clauses
The study has been reviewed.
The system has been continued since previous cycles, without inferring the
semantics of the only compiler.

The difference `validation/open-async-business-result-envelope.crust` is corrected:
an async function can now receive and return the envelope of the join
d-a return task `Result<u8,IntegerConversionError>`. His old log
remains historical; the program is run in the new module.

The same connection covers the six families already existing without borrowing:
`Result<u8,IntegerConversionError>`, `Result<char,CharAtError>`,
`Result<char,CharFromStrError>`, `Option<char>`, `Result<u8,ByteReplaceError>`
and `Result<(),ByteReplaceError>`. Joining adds `runtime::Error` and each
next wait can add a new envelope, without confusing error
trade with failure of launch.

<a id="implémentation-et-défauts-corrigés"></a>

## Implemented and corrected defects

Envelopes use already defined C representations for these values.
The type register matches explicit and inferred type of signature of the
join. The first level keeps its dedicated load field; the following
use the structural representation of the previous cycle. Annotations,
synchronous contracts, captures, async returns, reassignments, copies, branches,
loops and drop keep the type complete. The results containing a view,
notamment `Result<&str,SliceError>`, are excluded from the undebtable register; their
Existing source monitoring remains necessary.

Two additional defects were reproduced and corrected:

- Un `Ok(inner)` extract from a join async could bind a deceptive job result
  U1 is now applied to this extraction, as in the case of the
  other bankrupt connections. `drop(->inner)` Stay accepted.
- Creating a task from synchronous code did not control the type
  of certain catches of results and of the `runtime::Error`. One
  The common C representation is not sufficient to prove its compatibility.
  control now requires the exact Crust mode. This refuses to include
  capture a slice result borrowed from a parameter declared as
  full conversion result without borrowing.

This second defect was discovered by correcting the test itself: its first
version utilisait `try_slice(0,1)` and got a syntax error.
call is `try_slice(0..1)`. With this syntax, the incompatible program was
accepted, as shown by `validation/business-envelope-borrow-boundary.log`.
The final test first executes a valid neighbour displaying the slice, then requires
the diagnosis of the appropriate type for the incompatible capture.
syntax is not counted as proof of origin.

<a id="modèle-programmes-et-interactions"></a>

## Model, Programs and Interactions

An independent compiler table sets the results of six operations:
conversion 255/256, reading at the beginning/mid of a multibyte character,
conversion of one/two character text, pop of a full/empty string,
replacement d-byte and replacement of range at a valid index/out of limits.
It does not read any internal decisions or any C field generated.

The generator combines these two exits with one or three envelopes and one
synchronous or after copy/capture/suspension in another task:
48 native configurations. Six other configurations refuse to launch
The error must be recorded in the three levels, with the two observation modes.
find exactly at the refused level; the business calculation does not run when
its launch fails. Values calculated from a String are used
after the drop of this source.

Additional neighbors cover contracts, direct return of waiting,
if/loop, annotation, reassignment, use after drop and unused results.
Eight incompatible loads and two bad values `runtime::Error` doivent
be refused to capture. The final module counts **7 methods, 58 executions
native and 16 refused** by level of optimization.
mutations are counted separately.

<a id="mutations-et-correction-de-la-couverture"></a>

## Changes and correction of coverage

The mutants are executed in temporary copies:

1. Omission of type control when creating a task sync.
2. Failure to use the extracted business result.
3. Removal of the mining status in an async task.
4. Clearing of business status upon return of direct synchronous join.

The first campaign detects the first three but the fourth survives
(`validation/business-envelope-mutations.log`) Three-tiered channels
The first join was made in async.
The matrix is therefore extended to one envelope, without changing the
The four mutants are then detected.
by assertions of behaviour or acceptance
(`validation/business-envelope-mutations-final.log`) Corruption of the status
trades produced in particular `0` instead of the diagnosis expected `90`.

This campaign does not give an overall detection rate and does not constitute a
A proof of safety.

<a id="preuves-dexécution"></a>

## Evidence of enforcement

Clang Homebrew 20.1.3., arm64 macOS, C11 and pthread. New programs
natifs utilisent UBSan fatal (`-fsanitize=undefined -fno-sanitize-recover=all`)
At O0/O2. Runtime C oracles add strict warnings.
The old stress/effect helpers use their own optimization;
CRUST_SANITIZE activates UBSan, but CRUST_TEST_OPT does not prove that they are using O2.

| Verification completed | Result | Trace |
| --- | --- | --- |
| New Expanded Module O0 | 7 successful methods, 50,186 s | validation/business-envelope-O0-expanded.log |
| New Expanded Module O2 | 7 successful methods, 31,240 s | validation/business-envelope-O2-expanded.log |
| Module before enlargement, interlocked results, simple contracts, runtime::Error, constraints and effects | 86 successful methods, 112.195 s | validation/business-envelope-O2-regression.log |
| Incompatible capture of slice and ten other types | 2 successful methods | validation/business-envelope-capture-types.log |
| First regression of UTF-8 operations, before strengthening sync capture control | 15 successful methods, 33,318 s | validation/business-envelope-typed-regression.log |
| UTF-8 Final Regression after all corrections | 15 successful methods, 37,170 s | validation/business-envelope-typed-regression-final.log |
| ABI tasks, Bool/tables, loans and calculated expectations | 15 successful methods, 23.517 s | validation/business-envelope-abi-regression.log |
| Final transfer campaign | 4 detected | validation/business-envelope-mutations-final.log |

The first log `business-envelope-initial.log` conserve l’acceptation fautive
d `business-envelope-O0.log` above
the correction of the slice test and does not validate this border. Both
Final Extended Executions Include All Corrections and Tests
The Python compilation of modified modules and the
scripts did it.

<a id="limites-et-suite"></a>

## Limitations and follow-up

This cycle does not make all Results<T,E> generic: other loads of
carriers, containers, owners and general borrowings remain at
a further difference is shown in the
`validation/open-async-vector-value-result.crust` and its log:
`Result<(),u8>` exists and its synchronous relay runs, but its capture/sound
return async were still refused at the close of this cycle. This defect is
corrected in [ASYNC_VECTOR_RESULTS_CYCLE.md](ASYNC_VECTOR_RESULTS_CYCLE.md). Synchronous control displays `1` sous
UBSan. This async program is a valid case that remains to be implemented, not a
example of a disabled program.

The remaining obligations of the seven drafts are retained: API
runtime::Handle<T>, public scheduler, wake up/fairness, runtime::thread, Select,
The border C, the lines
the various methods and mutex manufacturers remain carried forward according to
There is no formal evidence here, no ASan/TSan campaign,
or the entire monolithic continuation of the project.

Commandes :

```sh
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_business_result_envelopes -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_business_result_envelopes test_nested_plain_results test_plain_join_contracts test_runtime_error_values test_constraints test_effects -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 python3 tests/run_business_envelope_regression.py
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 python3 tests/run_plain_join_regression.py
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 python3 tests/run_business_envelope_mutations.py
```
