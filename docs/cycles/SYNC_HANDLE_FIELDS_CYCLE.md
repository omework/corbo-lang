[Français](SYNC_HANDLE_FIELDS_CYCLE-fr.md)

<a id="résultats-de-handles-projetés-dans-les-champs"></a>

# Results of handls projected in the fields

<a id="périmètre-et-corrections"></a>

## Perimeter and corrections

AS12/AS13, ST8 and ST11–ST14, B1–B5, D1/D3 and RT5 require a distinction to be made between
capture during the execution of dependencies retained by its result.
Normative rules are not changed.

A synchronous factory called in an async state can now return
a handle whose result is a field Int inline, a nested field,
or the target of a field `&mut Int`. Un champ `&Int` returned as value
keeps its outer target without artificially holding its bearer.
The named reception and the direct expectation of the factory keep the paths.

The contract relay lost the path of an indirect mutable field and
He kept the whole structure. He now keeps the way, the real
The auditor counted the target allocation and the original mutable capacity.
also twice the same capacity: full capture of the handle, then projection
These representations are only collected when they are
The other loans continue to be counted.

The analysis of constraints did not know the public results borrowed from Int.
A source of capture symbol borrowed now links the result of
`join`, its uses and relay contracts. An indirect projection retains
the source of the field and the reservation of the carrier. The reset test is
exclusivement historique (`allow_legacy_reset=True`), in accordance with PR1.

<a id="contre-exemples-et-erreurs-de-tests"></a>

## Counterexamples and test errors

`validation/open-sync-handle-field-result.crust` is now accepted and
executed; his old error remains in the previous cycle.
The initial logs of this lot keep the road losses and the
violations of the exclusivity invariant caused by double counting.

The first extended model ended with 29 errors: 28 valid scenarios
rejected by double counting and interlocked initialization not taken in
load in a fixture. The latter now uses construction
default complete followed by explicit writings; its value assertions
The negative drop test also meant that the
value too late in the arm: the explicit import is placed at its entry.
The opaque caller harness was then corrected to install the types,
The intermediate failures remain visible.

<a id="exécutions"></a>

## Implementation

`tests/test_sync_handle_fields.py` : nine targeted methods go to O0
(24,138 s) and O2 (24,345 s), newspapers `validation/sync-handle-fields-complete-o*.log`.
Clang C11, pthread, fatal warnings, fatal UBSan ; compilation timeout
30 s and execution 10 s. These final passages include the supplementary call
opaque direct and exclude the diagnosis of internal invariant from the expected refusals.
The first single text and supplements remain in the newspapers
`sync-handle-fields-final-o*.log` and `sync-handle-fields-opaque-direct-o*.log`.

The independent model crosses three sets of returnable fields, three
fields written, the order before/after last use and two branch choices:
36 scenarios, 28 executed and eight refused the two compiler entries.
It does not consult the contracts or the C to decide the expected result.
The neighbouring tests cover independent catches, destruction of the
carrier and target, disjointed fields, suspension after receipt,
nested fields and an injected launch refusal.

The stress test explicitly requires a relationship of different sources
in contracts of `finish` and `route`. An appellant having only the
contracts accept the independent pool and refuse the target pool.
admitted is also executed in C. The bodies and definitions async are absent
of this test caller.

Regression handles: 43 methods O2, 63,180 s, all successful in
`validation/sync-handle-fields-contract-regression-o2.log`It precedes the
two last tests added, the opaque supplement and the last adjustment of the
the path of constraints, covered by the final targeted passages and the recovery
expanded below.

Wider regression of constraints, fields, borrowed calls, views, results
owners and obligations: 107 successful O2 methods in 77,799 s,
`validation/sync-handle-fields-expanded-final-o2.log`.
The first passage (`sync-handle-fields-expanded-o2.log`) has 107 methods
and six errors on invalid variants of a test. The new course of
contraintes tentait d'inférer les retours concrets, hors du périmètre public de
this patch, with an incorrect diagnostic callback.
Results groups now use the pre-established public contract.
the constraints of the concrete hands remain a gap to be dealt with with with the relay
below; no rule of refusal is added.

## Mutations

`tests/run_sync_handle_field_mutations.py` works on temporary copies.
The final campaign detects five errors: projection erasure, double
Inline counting, double indirect counting, erasing of result symbol
borrowed and erased the source of the indirect field.

A sixth mutation, which erases the concrete resolution of this symbol in
The other controls continue to refuse the control of sources, and the
The results of these tests do not prove the isolated effectiveness of this branch.
The script ends with status 1 to report this survivor. Both
and their diagnoses are preserved, including
`validation/sync-handle-fields-mutations-final-o2.log`No general rate of
detection is not claimed.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Update: the counter example of the relay below is corrected in
[CONCRETE_HANDLE_RELAYS_CYCLE.md](CONCRETE_HANDLE_RELAYS_CYCLE.md), with follow-up
The initial observation of the concrete sources and the historical order of the resets.
is kept for traceability.

Nouveau contre-exemple : `validation/open-concrete-borrowed-handle-relay.crust`.
A parameter `Execution<leaf>` relayed to a receiving function
`runtime::Handle<&mut Int>` loses the capture in his return contract again.
Both entries refuse to accept it: `contrat de retour : capture empruntée introuvable`.
The newspaper `validation/concrete-borrowed-handle-relay-probe.log` reproduit cet
deviation. The descriptor of the parameter is modified by the public conversion
during the internal call: the contract still seeks capture 0 while
The allocation now covers groups 2 and 4.
in `validation/concrete-borrowed-handle-relay-descriptor.log`.
It's a lack of implementation, not a new language rule.

The signatures and general aggregates, Select, the customizable scheduler and
the general static placement remain open. Arbitration on the capture of a
The handle already started by an inactive task is unchanged. No passage ASan/TSan,
no formal evidence or completeness of the orders are
The overall objective remains active.

Snapshot : `/tmp/crust-before-sync-handle-fields`. Changes retained
in `validation/sync-handle-fields-*.py.patch`.
