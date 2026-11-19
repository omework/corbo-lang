[Français](ASYNC_OWNED_STRUCT_SYNC_CALLS_CYCLE-fr.md)

<a id="appels-synchrones-depuis-async-avec-structures-propriétaires"></a>

# Synchronous calls from async with proprietary structures

Follow-up: the refusal to refund after replacement reported below is
for cases described in
[RETURNED_OWNED_REPLACEMENT_CYCLE.md](RETURNED_OWNED_REPLACEMENT_CYCLE.md).

<a id="périmètre-et-règles"></a>

## Perimeter and rules

This lot applies existing rules T1/T6, D1/T11, B1/B2/B4/B4a,
ST1/ST7/ST15, L1/L2/L6 and AS5/AS8/AS9/AS12/AS13.
drafts 01, 03, 04 and 05 without changing their normative semantics.

Async states can transmit graphs to synchronous auxiliaries
finished owners already supported: fields Int and A<Int>, A<String>,
A<Vector<Int/u8>> or structures of this family.
consume or return them, directly or in both envelopes Result
Supported. Arrows are still needed; calls are checked
The backend separately emits the bridge body.

Addresses don't change. Fields don't become allocations
The pools of the descendants remain independently owned by the bridge.
The general construction of structures
in async states is not part of the finished support.

<a id="changements-et-contre-exemples"></a>

## Changes and counter-examples

- `validation/open-async-owned-struct-sync-call.crust` was refused to the
  The bridge now describes the proprietary fields and their
  sources, without moving or recording them as separate cleanings.
  A Error Result does not cause any field reading through NULL.
- Owner signatures admit String/Vector sheets<Int/u8>
  This does not activate Pools<Structure>
  in the async states: their construction requires a separate connection.
- The analysis of returns accepts explicit markers of calculated results,
  notamment `return <-identity(->h);`. Unmarked return owner remains
  refused. The storage monitoring also consults the candidates of the fields.
- The new borrowing test `let view=&*h.value` in async revealed a refusal
  The shared and mutable projections of the
  fields A<Int> are connected and also reserve the carrier against its
  consumption; the mutable variant reserves the target through `yield`.
- A helper can replace a proprietary field and then consume the carrier.
  The test exercises two distinct pools and finds the destruction of the old
  field, new field, then porter, each one once.

<a id="vérifications-exécutées"></a>

## Audits performed

Native commands use Clang C11, pthread, Wall/Wextra/Werrar,
Wno-unused-function and UBSan blocking (`-fno-sanitize-recover=all`).
Tests and mutations are in `tests/test_async_owned_struct_sync_calls.py`
and `tests/run_owned_struct_sync_mutations.py`.

- O0: thirteen methods go in 8,389 s in
  `validation/async-owned-struct-sync-call-complete-o0.log`The fourteenth,
  added then, passes separately in 1,264 s in
  `validation/async-owned-struct-sync-call-nested-o0.log`.
- O2 final: 14 methods pass in 10,294 s, with **23 executions
  natives**, **15 programmes invalides** in both courses
  (**30 refusal checks**), and a contract query in the profile
  reset historique. Journal :
  `validation/async-owned-struct-sync-call-final-counted-o2.log`.
- Regression to Final Code: **114 methods**, 76,035 s, O2, code terminal 0.
  It covers sync home calls, captures/returns of async structures,
  re-borrowing, field returns, storage of re-borrowing, constraints,
  Owners and owner-public handle results.
  `validation/async-owned-struct-sync-call-regression-o2.log`.
  The last two additions to the targeted test file are after this
  regression; they do not change the compiler.
- `py_compile` succeeds on the modified modules and both test files.
  The compiler's diffs are kept in
  `validation/async-owned-struct-sync-call-*.py.patch`, relative to copy
  previous `/tmp/crust-before-async-owned-struct-sync-call/`.

The lifespan model lists the eight placements of the pool's parents/child
root, child and leaf. Its expected is calculated by comparison of depths
of telescopes, regardless of the metadata of the compiler.
allows the result to be released; the other seven are refused by both courses.

Three C probes have an unlaunched task only: before call,
after restitution and during the suspension of a subsequent argument.
the identity of the two allowances, their sole destruction before the parent, and
The re-use of both slots. This harness does not introduce any public cancellation.

Launch failures are injected into the simple Result and
The last test distinguishes success, failure of the launch of the envelope
and failure of the launch of his child task: exits 7, 30 and 20 respectively,
with only one destruction of the graph in each case.

Control `reset` does not add the operation to the public language.
historical contract disjunction between the pool received, the source of the result and
the source of its field after relay. It does not replace the tests of durations of
life and drop executed in the normal profile.

<a id="mutations-et-échecs-conservés"></a>

## Changes and failures retained

The first campaign detected three mistakes and allowed two mutations to survive
in the selected methods:
`validation/async-owned-struct-sync-call-mutations-o2.log`.

- Without a graph of bridge fields, a simple opaque relay continued to
  function. Audit of the eleven methods of this version detects five
  failure of valid programs that inspect fields.
  `validation/async-owned-struct-sync-call-survivor-audit.log`.
  The final targeting uses this inspection path; it detects a lost support,
  Not an executed memory corruption.
- The anticipated destruction mutation targeted the return of a variable,
  The final fault is that the test returned a call directly.
  injected on the calculated return path actually exercised.
  result remains classified as a survivor in his campaign, with this lack of targeting.

The final campaign increased its baseline from 13 methods to O2 in 8,578 s and
detects the **cinq fautes** : omission of the graph, reading null in Err,
oblivion of the clean up of the prepared argument, premature destruction of the result
calculated and lost the loan of a proprietary field.
`validation/async-owned-struct-sync-call-mutations-final-o2.log`.
The test of the Double Result was then added and changed to O0/O2; it does not change
neither the mutations nor the five methods that detect them.

Initial failures are retained: eight sub-case failures in the first
pass (collection signatures, too restrictive control of the return marker,
omits "immutable" diagnosis, then the case of non-projection
connected in the extended pass. `initial-o0`, `second-o0`,
`expanded-o0`, `fields-o0` and `final-o0` with the same batch prefix.
The corrections to the expecteds did not change the properties allowed/refused.

<a id="écarts-encore-ouverts"></a>

## Differences still open

Two valid programs remain denied, with current evidence in
`validation/async-owned-struct-sync-call-open-limits.log` :

1. `validation/open-async-local-owned-struct-helper.crust` : a helper creates a
   structure on his data stack and returns it to async. Before explicit custody,
   `verify_program` acceptait mais `compile_source` refused to leave the
   local storage. No binary of this case was executed. Both courses
   now report storage of the unconnected receiver.
   The expected injection of this storage remains, not the normative refusal of the programme.
2. `validation/open-async-return-replaced-owned-field.crust` : un helper remplace
   the field by an allocation of another pool, then restore the bearer.
   The auditor still refuses restitution after replacement.
   propagate the graph after the call to the async results, without
   simply reuse the photograph of the graph at its initial capture.

General aggregates with borrowings, sum and constructions also remain
Async outside the families indicated. Field pools are followed in a manner
Curator; no general clarification of removal of old sources
After replacement is not claimed.

All the test processes cited are completed. The models and probes are
this lot does not prove general safety. No new ASan results
TSan is not claimed. Arbitrations of captured handle and branch
Select losers are not changed; the overall objective remains open.
