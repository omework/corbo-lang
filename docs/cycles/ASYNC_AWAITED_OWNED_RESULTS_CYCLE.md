[Français](ASYNC_AWAITED_OWNED_RESULTS_CYCLE-fr.md)

<a id="résultats-propriétaires-produits-directement-par-await"></a>

# Results owners produced directly by await

<a id="périmètre-et-règles"></a>

## Perimeter and rules

This lot applies U1, T1/T2/T6, B4a, D1/T11, L1/L2/L6 and
AS2/AS4/AS8/AS10/AS12 to expressions that produce an owner Result
Normative decisions do not change: an inactive task
makes T, a handle launched makes Result<T,runtime::Error>, and transfers
The drafts 01, 04 and 07 are concerned.

The types used are A<Int>, A<String>, A<Vector<Int>> and A<Vector<u8>>,
as well as two levels of Owners Result. The forms include a
named handle, direct launch, named task, direct async call
and a block expression returning a task or a handle.

<a id="contre-exemples-et-correction"></a>

## Counter-examples and correction

The minimum programme is
[open-awaited-owned-result-argument.crust](../../validation/open-awaited-owned-result-argument.crb).
Avant correction, `relay(->h.await)` was refused by verify_program and
compile_source with explicit "transfer -> required." A return
`return <-h.await;` was also refused with "explicitly required".
The markers were still present.
[The reproduction diary]](../../validation/awaited-owned-results-baseline.log).

Backend now uses common treatment of Result expressions
owners for synchronous arguments, async captures and returns.
It reuses existing waiting paths, retains the type of load and
the sources of storage, then leave the receiver the cleaning.
a task wait returning a Result is also connected, including
when the task comes from a block expression. The values prepared before
a suspended argument remains recorded for early outputs and
destruction at the suspension points.

The change does not add any hidden expectations or public cancellation.
a named return, the existing rules for the closure of the telescopes are retained;
the downward transfer to a call always requires local connection.

<a id="vérification-et-oracles"></a>

## Verification and oracles

The module `tests/test_async_awaited_owned_results.py` verify:

- The four families, the six forms of waiting, the observed values and the
  re-use of a pool at a slot;
- the absence of arrow, the second waiting of the handle, the owner pattern `_`,
  incompatible types and return from a pool too short;
- direct return, direct match and transfer to an async call;
- cleaning a first argument when the next one suspends and then leaves the
  function, even before the recipient's creation or call;
- errors injected at different Result levels, without successful result
  fictional and without double destruction;
- cleaning a losing Select branch with a prepared Result.

A separate finished model distinguishes three successive holders: the direct child,
the arguments prepared, then the receiver async. For each possible suspension
and for Ok/Err, it predicts a destruction of the present load or no charge.
Ten C probes exercise these stages, returning the slot, identity to re-employment
and the refusal of a second destruction. They have exclusively a root
not launched; they do not destroy a competing task.

Source programs pass through the parser, the verifier and the C generator.
The C probes are used only to inspect the suspension points and their
cleaning. Clang C11, pthread, Wall/Wextra/Werrar, Wno-unused-function and UBSan
fatal are used, at O0 and O2 depending on the passages.

<a id="résultats-exécutés"></a>

## Implemented

- `validation/awaited-owned-results-initial-o0.log` - six methods, 39,670 s, OK.
  This passage precedes the enlargement of the tests and the explicit maintenance of the
  Return behavior named through the telescopes.
- `validation/awaited-owned-results-cleanup-o2.log` Two methods, 10.168 s,
  OK; interlocked errors and ten suspended destruction probes.
- `validation/awaited-owned-results-select-o2.log` : one method, 1,255 s, OK;
  Two Select executions with charge present or refusal to launch the child.

- `validation/awaited-owned-results-final-o0.log` : nine methods, 64,613 s,
  OK on the final code; harness instrumentation: 110 native performances
  17 invalid programmes verified by both courses (34 checks).

- `validation/awaited-owned-results-regression-o2.log` 96 methods,
  111.724 seconds, OK on the final code. Selection: results without charge,
  suspension cleaning, Select results, Select source, calls
  proprietary synchronous and async structural effects.

- `validation/awaited-owned-results-mutations-o2.log` : baseline finale of
  nine methods, 64,482 s, OK; five injected errors detected: refusal of
  valid waiting, forgets a synchronous prepared argument, forgets a capture
  prepared async, omission of arguments during suspended destruction,
  premature destruction of the returned load.
  In particular, a fatal UBSan diagnosis in the mutant.
- `validation/awaited-owned-results-previous-mutations-o2.log` : baseline
  previous 12 methods, 35,063 s, OK; the eight mutations of the batch
  load-free results remain detected.

The two campaigns end with code 0, without surviving mutation or
Inconclusive of these thirteen selected errors. No process in this lot
The modified modules and the new tests/runners pass
py_compile. The full runtime suite of the previous cycle was not
Relaunched: this translation change is carried out by the programs
natives and the regression selection above.

## Limites

The sub-set of loads and the two Result levels above cover
not general signatures and containers. Diagnostics and contracts remain
The finished cleaning model is not a general model of the
no new ASan/TSan result or proof of general security
The arbitration of handles captured by an inactive task or
retained by a loser Select remain distinct and open.

The patch is stored in
[async_lowering-awaited-owned-results.patch](../../validation/async_lowering-awaited-owned-results.patch).
The overall objective remains ongoing.

The search for the next batch also reproduced the refusal of
`return <-leaf(p).await` when Leaf returns A<Int> directly, without envelope
Result. The program and both diagnostics are retained in
`validation/open-direct-awaited-allocation-return.crust` and
`validation/direct-awaited-allocation-return-baseline.log`. Connection
is treated separately in the
[direct benefit returns cycle](ASYNC_DIRECT_OWNED_RETURNS_CYCLE.md),
with his own evidence and limitations.
