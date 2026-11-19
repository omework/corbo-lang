[Français](SELECT_RESULTS_CYCLE-fr.md)

<a id="select--résultats-typés-et-effets-de-champs"></a>

# Select — typed results and field effects

<a id="portée-et-implémentation"></a>

## Scope and implementation

This batch completes [Select source](SELECT_SOURCE_CYCLE.md), without changing the
normative rules SL1, AS4/AS12/AS16, B1/B2/B4/B5, D1/D3 and U1.
AGENTS.md and VALIDATION_GUIDELINES.md are followed.

The programme `validation/open-select-owned-result-field.crust` was refused
by the two compiler entries: the effects of children's fields
The newspaper was not connected to their own results.
`validation/select-results-before.log` Keeps this refusal.
the program displays 9, 2, 17: winning result, field left by the loser,
then allocation in the recovered slot. Both allocations x are destroyed
Exactly once.

The analysis now retains the contract typed of the owner's result or
borrowed with field modifications. The composition common to expectations
direct, handle and Select bring together the sources of the allocations and targets
a failure of launch keeps the initial fields and does not provide
No successful result target. Scalar, simple tables and envelopes
error register without reference use their typed modes.
remains dynamic for envelopes recorded after import.

The backend accepts these effects only if the summary is complete.
unknown do not become empty effects. An incomplete summary diagnosis
Now includes its cause, including transfer from a local pool.

<a id="cas-exécutés-et-oracles"></a>

## Cases executed and oracles

The 12 methods of `tests/test_select_results.py` couvrent :

- Results allocated Int, String, Vector<Int> and Vector<u8>, back to the parent,
  Two possible sources, unique destruction and re-use of pools.
- Winner modifying a field before finishing; loser modifying a field
  These two situations have distinct oracles.
- &str views, &u8, &[Int], &mut [Int], &mut [u8], and Result<&str,SliceError>,
  still linked to their sources after drop of Select.
- Whole conversion results and fixed arrays with field effects.
- Direct relay of the borrowed result; owner result of handle with
  Two injection launch failure positions.
- Refusal of premature destruction or transfer, return from a pool
  local and results owners/bankruptcy left without explicit use.

An independent model lists nine pairs of numbers of yield (0 to 2).
Two meters determine the winner without consulting the compiler.
executions compare this winner, the destruction of branches actually
The contract claims
separate control the presence of possible sources.

The final targeted O0 has 27 native executions, two of which refuse to accept the
launch injected, and 20 programs rejected by each of the two entries
verify_program and compile_source (40 refusal checks).

Configuration native : Clang C11, pthread, Wall/Wextra/Werror,
Wno-unused-function, fatal UBSan, O0 or O2 depending on the newspaper.
no general evidence, comprehensive coverage or performance measurement
ASan and Tsan are not validated by this lot.

<a id="chronologie-des-vérifications"></a>

## Timeline of verifications

All newspapers are in `validation/` with the prefix `select-results-`.

| Journal | Result and version exercised |
| --- | --- |
| baseline-initial-o0.log | 80 methods, 22.757 s, OK; before the latest adjustments of the register and diagnostics |
| initial-o0.log | 31 methods, two diagnostic failures; 24 accidentally imported methods included, import corrected |
| owned-boundary-initial.log | Same refusal expected, diagnosis too general; cause of summary added then |
| targeted-o0.log | 7 methods, 7,410 seconds, OK |
| expanded-initial-o0.log | 9 methods, a fixture failure: mutable slice syntax not retained |
| collections-initial-o0.log | 10 methods, same fixture failed; proprietary collections pass |
| expanded-o0.log | 10 methods, 10,072 s, OK ; fixture using split_at_mut validated |
| views-o0.log | 11 methods, 22.481 s, OK |
| final-o0.log | 12 methods, 16,230 s, OK; U1 claims included |
| final-o2.log | 12 methods, 15.905 s, OK; U1 claims included |
| regression-o2.log | 122 methods, 120,627 s, OK; final code, ten new methods at this time |
| runtime-regression-o2.log | 275 methods, 510,653 s, OK; process completed with code 0 |

Extensions of the tests after the start of the two regressions did not
modified the compiler. Targeted final passages cover these extensions.

## Mutations

`tests/run_select_result_mutations.py` edit temporary copies: delete
sources, only keep the first source, lose the
targets of views, forget the writings of a proprietary termination, refuse
The two guards targeted by the
The last mutation is explicitly counted.

`select-results-mutations-initial-o2.log` : baseline ten methods, four
mutations detected and a survivor. Forgetting the ending scripts
owner survived because the test was only looking at a suspended loser,
whose prefix summary kept the writing. A winner test immediately
completed and an assertion of his contract was added, without modifying the oracle.

`select-results-mutations-final-o2.log` : baseline twelve methods, 24,222 s, OK,
five mutations detected. This campaign precedes only the two assertions
Additional U1, which pass in the final tests. Previous mutations
are detected: 11 of termination (`completion-mutations-o2.log`), huit
Select contracts (`contract-mutations-o2.log`) and eight suspensions
(`prefix-mutations-o2.log`Two anchors are now following the common union
targets; the errors injected and the oracles do not change.

<a id="limites-et-travail-restant"></a>

## Limitations and remaining work

General borrowed aggregates, suspended effects of the reference tables,
A<T> carriers, reference vectors and enums are not generalized here.
The unions remain conservative, without a general correlation between the winner and the
effects. Unknown recursive summaries remain unknown.
owner whose only LaunchFailed can continue still require an examination
Specific: lack of success must not become invented origin.
has since been dealt with in the [next cycle](ASYNC_FAILURE_ONLY_RESULTS_CYCLE.md),
with evidence of separate absence of an unknown summary.

The launch failure test is about an ordinary handle expected.
does not resolve the arbitration of a loser Select with a handle launched, nor the one
an inactive instance capturing such a handle. The public API of the scheduler
and other families of types remain open. This lot does not end the objective
global implementation.
