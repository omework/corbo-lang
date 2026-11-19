[Français](UTF8_TRY_SLICE_CYCLE-fr.md)

<a id="cycle--découpes-utf-8-faillibles-brouillon-07"></a>

# Cycle — FTU-8 cuts, fallible (Floor 07)

<a id="décision-et-périmètre"></a>

## Decision and scope

TX4 and E2 integrate the validated decision: the hooks refuse a disability
statically established, otherwise stop with diagnosis after dynamic control.
`try_slice` Returns a recoverable error and retains the source's borrowing.
The prototype calls the type `Result<&str,SliceError>` ; OutOfBounds and
NotCharBoundary are the variants prescribed by the draft.

The first step below connects the synchronous path, its contracts, function results,
Multiple provenances and explicit destruction. It does not close Lot 07:
the conservation of this Result in an async state and its transport by await/join
Two exploratory programmes confirm a diagnosis
"result ... required" or "expression utf8_try_slice not supported"
on these forms; no async acceptance is claimed.

<a id="implémentation-et-invariants-examinés"></a>

## Implementation and invariants examined

- The four forms of beach are analyzed directly.
  The receiver remains borrowed from the receiver.
  during their effects and their result is frozen before the operation.
- The validity of the entire range precedes the UTF-8 border control:
  one boundary-outlined terminal outweighs another character-cut.
- The view reuses existing bytes and their storage direction.
  Result inline does not consume pool slots.
- The contract transmits the dependencies of the text, without transforming the indices
  Two conditional origins remain reserved for the appellant.
- The link is U1. Its destruction ends the loan; a transfer,
  premature destruction or reset remains refused.
- The short patterns of the draft, Err(OutOfBounds) and Err(NotCharBoundary),
  are supported for cuts and char_at. Qualified shapes
  remain controlled by type; CharAtError does not treat a SliceError.

<a id="preuves-exécutées"></a>

## Evidence

`PYTHONPATH=tests:. python3 -m unittest test_utf8_try_slice -v`, with two
C compilation configurations: C11, O0, O2, UBSan and
`-fno-sanitize-recover=all`. Eight methods pass in each configuration,
journal `/tmp/crust-try-slice-optimizations.log`.

Nine admitted programmes/harnesses and eighteen rejected programmes are carried out by
These eight methods, each with a configuration.
then switch to O0 and O2 (`/tmp/crust-try-slice-result-alias.log`) : un programme
and three refusals verify the aka of Result, the return of the Result since
a function and replacement of its origin. Destroying a link does not
The oracle test explores the 144 couples
The expected boundaries are calculated in terms of the number of terminals from -1 to 10 on "summer".
Python by encoding prefixes of characters, regardless of the course of the
Bytes in the runtime. The expected substrings are decoded by Python.

Scenarios combine two function relays, loops, results
Thong, growth after last use, drop and
Reuse slots. A historical reset is tested only with the option of
compatibility, without re-introduce to the public API.
by a function called in a terminal is also refused.

A Harness C explicitly checks the addresses, lengths and directions of the
views for bytes in each direction, an empty view at the end of the text,
Int32 extremes and an empty text with NULL pointer. It completes the
Crust programmes and does not demonstrate the entire policy of regional placement.

Three mutations targeted in temporary copies are detected:

1. Omission of border control: invalid UTF-8 bytes arrive
   in the exit, whose decoding Python fails.
2. OutOfBounds replaced by NotCharBoundary: divergence with the oracle.
3. Offset ascending used in downward storage: Harness fails with
   code 80 on the identity of the view.

Journal `/tmp/crust-try-slice-mutations.log`, copies
`/var/folders/rs/ld5jvh_n6t92p1hhs2qrmt7w0000gn/T/crust-try-slice-mutations.gdua_qtx`.
These three errors do not give any overall rate of mutation detection.

<a id="régression-et-limites"></a>

## Regression and limitations

The selected regression of 124 methods (UTF-8, Thong, arithmetic,
comparisons, short circuit, associated async and whole conversions) is passed in
125,542 secondes, journal `/tmp/crust-try-slice-regression.log`.

The two pre-existing independent models of `test_utf8_runtime` passent
also at O0 and O2 in 1,684 seconds: decoding positions and return
Unicode (grain 1439), exhaustive validation of the 65536 byte pairs and
Additional samples (grain 2671), including downward storage.
Journal `/tmp/crust-try-slice-runtime-regression.log`. The Python compilation
modified modules and the new test file succeed.

The first tests identified two problems in the new tests:
`SliceError>=` was tokenized as the operator >=, and regular expression
expected for refusal of a reset did not recognize the precise diagnosis
"argument" has been used.
corrected; expected acceptance values and decisions are retained.

No general evidence of safety or comprehensive road cover is available
No new ASan execution in this cycle.
static validity of hooks retains the existing spread range;
it does not claim a constant assessment of any possible expression.


<a id="deuxième-étape--état-async-et-transport-du-résultat-emprunté"></a>

## Second stage — async state and transport of borrowed result

The Cutting Result has an inline field in the state and result
It is also a part of the modes that carry a loan.
is therefore not limited to copying its bits: contract analyses,
capture, waiting, extraction and last use retain its provenances.
Type C `CrustTextResult` is shared with the task runtime.

Rules AS8, AS10, AS11 and AS12 apply without any implied extension of the
a view to a String transferred to the task can be used in its
body, but can't go out with the Result if this thong is destroyed at the
end. Targets provided by borrowing remain reserved after waiting
until the last use of the result or its extracted views.

The preparation of the terminals now shares the path used by the
The temporary receiver and indices persist in the state
If a terminal is suspended. The origins of the result are those of the text, not
values only read to calculate its limits.

<a id="exécutions-ciblées"></a>

### Targeted execution

The first eight async methods and the nine synchronous methods pass
O0 and O2 set under UBSan blocker: 17 methods per configuration,
7,592 seconds and 8,942 seconds, `/tmp/crust-try-slice-async-optimizations.log`.
The eight async methods cover twelve permissible executions and eighteen refusals.

Three additional methods are used separately for both optimizations:

- `/tmp/crust-try-slice-async-capture-loop.log` : capture of a borrowed Result
  created in the caller, drop of the original link, loop result and
  refusal to transfer during the use of the result (two admitted, one refused).
- `/tmp/crust-try-slice-computed-await-usage.log` : task chosen by if and
  expected; explicit use by drop allowed, unused link and `_` rejected
  (un admis, deux refus).
- `/tmp/crust-try-slice-bound-provenance.log` : release of the reservation
  of a catch used only as a terminal after join, keeping
  the bytes actually returned (one admitted, one refused).

Interactions include await, yield-containing terminals before and after
construction, async function relays, Result captured by another
task, waiting for a handle from a task, local String sources in state
or borrowed, two conditional sources, reallocation of Result, alias,
re-use of slot after destruction, and historical reset refused before last
The expected values and errors are set independently of the
implementation; the synchronous oracle of beaches is replayed with the modified runtime.

<a id="contre-exemple-corrigé"></a>

### Corrected counter-example

A wait on a task chosen by if passed through a separate lowering which
omettait U1 : `let ignored = (if ... { let t = cut(); <- t } else { ... }).await;`
was accepted without the use of the Result. The path now applies the same
The program with explicit drop
The eight existing regressions targeting expectations and results are still accepted.
calculated go in 19.439 seconds (`/tmp/crust-computed-await-usage-regression.log`).

### Mutations

Three changes in the lifespan rules are detected:
source verification on return, loss of the loan descriptor after join,
and loss of local Result loans before copying and capturing. Each renders
at least one prohibited program accepted, and the negative test fails.
Journal `/tmp/crust-try-slice-async-mutations.log`, copies
`/var/folders/rs/ld5jvh_n6t92p1hhs2qrmt7w0000gn/T/crust-try-slice-async-mutations.own_fw4z`.
A fourth mutation removes the new U1 control in the calculated await;
it is detected (`/tmp/crust-computed-await-usage-mutation.log`).
No overall detection rate is derived from these four targeted mutants.

<a id="régression-et-limites-1"></a>

### Regression and limitations

The selected regression of 147 methods includes slices, UTF-8, String,
associated async catches and returns, entire conversions and both
independent UTF-8 runtime models.
`/tmp/crust-try-slice-async-regression.log` : **147 successful methods in
154,153 secondes**.
This execution loaded the compiler before the local U1 correction; the
Eight waiting regressions calculated above then validate this correction.
The Python compilation of the modified modules succeeds.

These executions do not prove the general safety of the async. No stress
additional multithread or TSAN/ASan is not executed in this step.
changes to scheduler, runtime::thread, runtime::Error, Select and mutex of
draft 04 remains a separate batch to be completed. Generic contracts for
nested results and all uses/motivations owners of draft 01
are not declared as fully covered by this cycle.
