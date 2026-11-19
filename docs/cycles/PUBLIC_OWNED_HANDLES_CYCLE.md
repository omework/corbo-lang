[Français](PUBLIC_OWNED_HANDLES_CYCLE-fr.md)

<a id="contrats-de-handles-à-résultat-alloué"></a>

# Contract of handles with allocated result

<a id="règles-et-changement"></a>

## Rules and change

RT5/RT6, MT5/MT6, AS13, D1/D3, T6 et U1 exigent que le contrat d'un
`runtime::Handle<T>` keeps dependencies of its result after waiting.
He must not then hold a pool that was only used for a destroyed capture.
This cycle applies these rules to Int, String, Vector, and
Vector<u8>. Normative rules do not change.

The parameters and returns transferred from synchronous functions accept
`runtime::Handle<A<T>>` for these four contents. The opaque contract distinguishes
storage of catches of the storage of the allowance returned.
relays and junctions between different frames retain this distinction.
The result continues to carry its original pool; the transfer keeps
The existing runtime extracts the Cell* before releasing the frame.

`runtime::Handle<Result<A<T>,runtime::Error>>` is also recognized as:
the result of the join has two distinct levels of error.
external launch is not confused with the child's launch of the task.

Public descriptors have a symbolic entry for the source of the
It is neither an additional actual capture nor a generated pool.
Its source is independent of the opaque group of other catches, including
When their pool types differ. Inference exploits this input
without inventing a task force or going through a caller's.

<a id="contre-exemple-et-correction"></a>

## Counter-example and correction

`validation/open-public-handle-owned-contract.crust`refused before,
compiles and displays 7 in the dedicated test. His old diagnosis is preserved.

Integration revealed a loss of type in the analysis of the effects: a
manufacture or relay made the only name of the frame/handle, instead of
internal form Task/Execution. After a join and a block exit, a
Thong became of indeterminate type, and byte_len was refused.
The results of the Task/Execution are now retained in this analysis, as well as in the
the envelope of an already deceivable allocated result.
`validation/public-owned-handle-string-block.crust` and
`validation/public-owned-handles-initial-o2.log`. The corrected check is
in `validation/public-owned-handles-effects-fixed-o2.log`.

A failed allocated result fix would omit the arrows on his signature
and his return. It was corrected in return explicitly transferred, without change
The Journal `…-nested-o2.log` garde ce refus.

<a id="validation-exécutée"></a>

## Validation executed

`tests/test_public_owned_handles.py` contains nine methods.
at O2 in 16,311 seconds: `validation/public-owned-handles-typed-helpers-o2.log`.
They exercise 31 compilations/executions C, 43 invalid variants checked
both verify_program/compile_source entries, as well as an opaque caller
admitted and an opaque caller refused, without async body or available functions.

The scenarios cover:

- The four types allocated, a separate Int capture pool, two relays and
  the release of a block that destroys this capture pool after the join.
- A waiting assistant who returns the allowance, with a rescue pool
  The two possible sources remain protective in the appellant.
- Refusal to receive allowances in a reserved pool, to escape an allowance from the pool
  The test of reset is based on the following criteria:
  exclusively executed with explicit historical profile.
- Address ID before transfer, after join and after re-use of the slot;
  a single destruction of the transferred allocation and capture.
- Cleaning after refusal to launch, re-use of pools and both
  error levels of an embedded result.
- Refusal of bad A<T>, even if the consumer only destroys
  the burden, and the mandatory use of proprietary results.

The independent model lists the lifespans of three pools and two phases.
Before join, the three pools that can be used must survive the handle.
Only the two pools that can provide the allowance must survive the result.
It does not read the summaries produced by the compiler. Its 16 configurations
are executed with the two branch choices: 32 scenarios, six executions
C and 26 programs refused both entries. These numbers are included in the
Total previous, not additional.

Clang C11, pthread, fatal warnings, fatal UBSan; O0 and O2.
of eight methods is increasing to O0 in 15.369 s (`…-final-o0.log`The final O0 pass
of the nine methods succeeds in 13.542 s (`…-complete-o0.log`) The extended regression ends with
104 methods in 105.851 s (`…-regression-o2.log`) : contracts for hands,
joint ventures, annotations, mixed contracts, home calls, U1 obligations,
Injected pools and local pools. It precedes the latest addition of tests of auxiliaries
The results of the study were based on the following:

## Mutations

Five errors injected into temporary copies are detected:

1. Clear symbolic provenance of opaque result: a valid auxiliary
   who returns his result is refused for lack of provenance.
2. Replace the results sources with the sources of all catches: the
   valid result that survives the temporary pool becomes refused.
3. Clear source of result when receiving the handle: the caller
   opaque wrongly accepts an allowance that survives his pool.
4. Remove control from load type: Bad A<T> is accepted.
5. Clear Task/Execution mode in effects: the rendered String becomes
   undetermined and a valid program is denied.

Journal : `validation/public-owned-handles-classified-mutations-o2.log`.
The first campaign classified fault 1 as inconclusive because the script
The journal's review was only expected to result in acceptance of an invalid program.
shows precisely the refusal of a valid program; this specific diagnosis
is now recognized as a detection of an acceptance regression.
The initial log is kept
in `validation/public-owned-handles-mutations-o2.log`.

<a id="limites-et-suite"></a>

## Limitations and follow-up

This cycle does not end contracts for borrowed results, signatures
async, other proprietary aggregates or arbitrary envelopes.
`validation/open-public-handle-borrow-contract.crust` conserve un programme
valid still refused, with his diagnosis. Refusal of public parameters
async remains retained in `validation/open-public-handle-async-parameter.crust`.
Examples are remaining implementation obligations, not rules
standards of refusal.

No new ASan/TSan passage or second compiler C; no evidence
formal and comprehensive coverage of the orders. Select, schedule
Customizable, mutex and other matrix deviations remain open.
Changes are retained in `validation/public-owned-handles-*.py.patch`.
The cycle is completed for this tested perimeter; the overall objective remains active.
