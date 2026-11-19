[Français](SYNC_VIEW_BRIDGES_CYCLE-fr.md)

<a id="vues-des-auxiliaires-synchrones-dans-les-états-async-et-natifs"></a>

# Synchronous auxiliaries in async and native states

<a id="périmètre"></a>

## Perimeter

This lot applies B1–B5, D1/D3, AS2/AS8/AS11/AS12, RT5/RT6 and U1 without
The synchronous calls from a state take in
&str, &u8, &[Int/u8], &mut [Int/u8] and Result<&str,SliceError> as
The arguments are evaluated in sequence; their
prepared borrowings protect targets during the following arguments, even
if a sub-expression suspends the appellant. The contract of the result retains
its possible targets, without holding back independent arguments after return.

The C representation of the views crosses a generated synchronous bridge. L
the results and constraints also consult the contracts
auxiliaries: otherwise she preserved a result for all
the arguments. The sub-views and references d
keep the valued recipient's borrowings, including during the valuation
Native blocks infer the type of a slice of
String or Vector captured without annotation. Finally, a failed synchronous call
isolated followed by `;` no longer bypasses U1 in an async body.

<a id="contre-exemples-et-corrections"></a>

## Counter-examples and corrections

`validation/open-public-view-result-helper-precision.crust` was refused:
an async function returned the view of a synchronous auxiliary.
The other argument was not sufficiently well understood.
The contract consultation corrects this dependency.
The initial fixture itself had a defect: the drop scratch from a
bras enfant exigeait `scratch ->;`. This explicit import is added;
the compiler continues to refuse the program without it.
intermediates are kept in the initial-probe, precision-probe logs
and correct-precision of the prefix `validation/sync-view-bridges-`.

The tests also highlighted the lack of follow-up of calculated views
by `&identity(&data[..])[..2]` and native capture inference of a
They now cover these paths and invalid neighbors: drop,
growth, incompatible writing, local non-sustainable result and mutation
No valid cases are reclassified invalid for
accommodate a backend restriction.

Two fixture corrections remain visible: a link had been made
re-declared; a trace of destruction was awaiting a text that is not the one
The final test requires exactly one destroy event and then one
event reclaim, and check that the body called after a return d
never executes. It does not depend on the diagnostic value printed by
Destroy for a Thong.

<a id="preuves-exécutées"></a>

## Evidence

`tests/test_sync_view_bridges.py` The first eleven methods are used.
go together with Clang C11, pthread, fatal warnings and fatal UBSan:

- O0: 11 methods, 11,673 s, `validation/sync-view-bridges-final-complete-o0.log`.
- O2: 11 methods, 12,787 s, `validation/sync-view-bridges-final-complete-o2.log`.

The supplement of native Vector slices<Int/u8> passes separately
at O0 (0,719 s) and O2 (0,869 s), native-slices-o0 and native-slices-o2.
No change in compiler occurs between the passages of the eleven
methods and this supplement. The Python compilation of the five modified modules
and three test/campaign files succeed.

The tests are carried out in both slice modes, two types of elements, two types of elements, and two types of elements.
synchronous relays, two branches of result, suspensions, the last
use, early returns and cleaning. The result of try_slice is passing through
a second auxiliary before the match: success, invalid UTF-8 border and
The result is an explicit drop in the fallible result.
is allowed; abandonment, unused link and `_` are refused.

An independent model lists the necessary sets before and after join:
32 scenarios, six executed and 26 rejected by verify_program and compile_source.
Before join the three catches are required; after join only the two
The expectations of the model are likely to be.
do not consult calculated contracts or the generated C.

The extended regression succeeded 99 O2 methods in 84.721 s:
`validation/sync-view-bridges-regression-o2.log`. Elle couvre appels synchrones
scalar/borrowed/owners, native blocks, public viewhandles,
try_slice async and expressions borrowed. This passage started before the
last U1 control; this control is covered by the final targeted passages.
It is not the whole sequence of the deposit.

After the last U1 control, the regression of owner use and cuttings
UTF-8 async also passes: 23 methods O2 in 36.935 s, journal
`validation/sync-view-bridges-usage-regression-o2.log`.

## Mutations

The final campaign `tests/run_sync_view_bridge_mutations.py` detects five
Errors in temporary copies of compiler:

1. Allowing the abandonment of the bankrupt call: an invalid program is accepted.
2. Clear loans from the result: premature destruction is accepted.
3. Clear loans from prepared arguments: a transfer competing with their
   logical use is accepted during a suspended argument.
4. Clear loans from a calculated subview: its target can be destroyed.
5. Ignore the helper's precise contract: the model is denied a valid drop.

Journal : `validation/sync-view-bridges-final-mutations-o2.log`.
The borrowing campaign d-bytes is also replayed: baseline of twelve
successful methods then five errors detected in
`validation/sync-view-bridges-byte-mutations-o2.log`. Two text anchors of the
Runners are adapted to the refactored code; the defects injected do not change.
The failures displayed in these journals are those of the mutated compilers.

<a id="mise-à-jour-documentaire"></a>

## Document update

The Limitations section of the README contained historical restrictions now
countered by the cycles executed: Bool, conditional borrowed results,
structures/collections, two-fronted regions and scalar async recursion.
These statements are replaced by the current boundaries and links, without
amending the normative rules or presenting a generalization as completed.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Further addition: the synchronous handle factories and their expectation
in a state are now connected in
[SYNC_HANDLE_BRIDGES_CYCLE.md](SYNC_HANDLE_BRIDGES_CYCLE.md), for parameters
and results listed in this report. The limit below describes the state during the
The general projections remain open.


Synchronous runtime::Handle<T> factories called from a state are not
not connected by this lot.
`validation/open-public-view-handle-async-helper.crust` I'm not going to let him go.
is reproduced on the compiler after this lot in
`validation/sync-view-bridges-next-handle-probe.log`. The
The views here are directly processed; the projections of all the
forms of aggregates and general references of collections are not
The arbitration on the capture of a handle already launched remains pending.

Select, public replacement of the scheduler, general static placement and the
other global bonds remain open. Reset remains a historical API,
no reintroduced into prototype. No results found. ASan/TSan, second compiler
The models and mutations concern the
finite compositions described here, without any overall claimed security rate.

Snapshot : `/tmp/crust-before-sync-view-bridges`. The differences in the five
modules and runner d
`validation/sync-view-bridges-*.py.patch`The overall objective remains active.
