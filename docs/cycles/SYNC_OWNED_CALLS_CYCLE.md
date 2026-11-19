[Français](SYNC_OWNED_CALLS_CYCLE-fr.md)

<a id="cycle--transferts-propriétaires-aux-auxiliaires-synchrones"></a>

# Cycle — proprietary transfers to synchronous auxiliaries

<a id="portée-et-règles"></a>

## Scope and rules

Continue to [SYNC_BYTE_BORROW_CALLS_CYCLE.md](SYNC_BYTE_BORROW_CALLS_CYCLE.md).
AGENTS.md, VALIDATION_GUIDELINES.md and the index of the seven drafts were
Reconsulted, as well as T1–T11, ARGUMENTS.md, AS7–AS9 and draft 01.
No regulatory rule is amended. This batch connects B4/B4a/B4c, T1/T6/T9/T11,
U1/L6, AS2/AS8/AS9/AS12 and RT8: synchronous calls from async or async states
native blocks, with parameters and results owners Int, String,
Vector<Int> and Vector<u8>.

`->` remains mandatory for the proprietary argument.
immediately the old access and saves the Cell pointer in the state.
The following arguments may be suspended, but may not reuse this access
The calle receives the pointer, without displacement
The parameters of the allowance shall keep their mutability declared.

The result is received, transmitted with an arrow or destroyed by `drop(-> call())`.
The call is isolated, `_` and a non-usable connection are refused.
The corresponding A<T> annotation; Int and A<Int> are not confused.
A result can replace a recipient after complete evaluation, be passed
to another auxiliary or captured directly by a child task.

<a id="implémentation-et-nettoyage"></a>

## Implementation and cleaning

Synchronous generation uses allocations and symbolic sources
The C receives real Cell*. The scope
outdoors is not cleaned by this adaptation: its pools belong
the calling context. The returned allowance is explicitly exported before
cleaning of the adaptor scope; other allocations follow the
Synchronous body cleaning checked.

Prepared transfers are included in the existing cleaning mechanism
d) arguments. A return during a subsequent argument destroys these allowances
Once, then clean the lost telescopes, without calling the call.
prepared are cleaned in reverse order of receipt. An internal break
to a calculation loop d
The general loop cases remain subject to follow-up.
This cycle does not purport to exhaust them.

The contract of results async consists of the candidates who own the
synchronous summaries. A parameter restitution retains its origin;
several candidates keep the union. A helper who only returns after
to have consumed b allows the pool to b end after join, before use of the
result a. The current handle nevertheless retains both catches and does not
can exit the b pool scope. Synchronous task factories keep
The analysis uses abstracts; a cyclical inference or
un candidat non direct garde l’approximation conservative existante.

<a id="défauts-et-précisions-trouvés"></a>

## Deficiencies and clarifications found

The first symbolic source connection was not included among the
external sources known to the auditor: it was refused by the invariant
The registration is corrected without issuing a closure.
from that outdoor pool.

The valid program that creates `let vue = &allocation` in a state, bed via
a helper, then transferred after the last use, remained refused as a
expression ref not supported. Int and mutable u8 seats can now
the existing controls of type, mutability, capacity
and last use are reused; cases with future use remain
The embedded references are not flattened.

Initial fixtures used `*a = n` for allocated proprietary access,
while the chosen writing is `a = n`The unused helper was therefore refused.
The results of the study were not available.
`match <-h.join()` ; the scenarios executed use the jogging match already
The exploratory probe `copy(a)` on an Int allowance is refused
by the table path; it is not counted as an obligation to copy
structure ST18 or as evidence of duplication of allocation in this cycle.

<a id="vérification"></a>

## Verification

`tests/test_sync_owned_calls.py` includes thirteen methods, twenty-two executions
Crust/C and 20 refusals expected by full passage, plus one verification
without generation C. Oracles are the outputs written independently of the
compiler, traces of destruction, equality of addresses before/after
and the actual re-use of capacity pools one or two.

Scenarios cross: explicit transfers, last use of named borrowing,
nested arguments, yield/wait during preparation, return anticipated, loop
internal, several proprietary arguments, conditional result and pools
real distinct, synchronous fabric, child async, join, failure of launch,
replacement of receiver, annotations of type and cleaning of collections.
Existing synchronous contracts and relevant native/runtime scenarios
are re-executed. No new random generator or general model of
competition is claimed; models of provenance of contract tests
The selection of existing ones remains included in this selection.

Clang C11, pthread, O0/O2, `-Wall -Wextra -Werror -Wno-unused-function`,
`-fsanitize=undefined -fno-sanitize-recover=all`. UBSan diagnostics fail
no new ASan/TSan validation or second compiler;
previous ASan blockages are not successes. No formal evidence.

## Mutations

The campaign starts with a green baseline and works in copies
The errors relate to the invalidation of the
the old name, the inclusion of the arguments prepared for the cleaning, the order of
their cleaning, export of the result out of adaptation, the source of the
Async result and rejection of an ignored proprietary result.

The first campaign also contained the omission of the NULL field
She survived, on the roads that were executed, `consumed` already excludes this
terminal cleaning field, and `cleanup_path` select this cleaning instead
The obsolete field is therefore no longer read.
Final classification is "no behavioural effect on the chosen paths",
no "detected fault" or general evidence of equivalence.
removing the invalidation of the name controls the real possibility of reuse
The original survival log is kept.

The anchors of the mutations of the previous cycles were adjusted to the insertion
the owner case in the generation, without changing the faults or oracles.
Their syntactic adaptation is not claimed as a re-execution of these
campagnes anciennes.

<a id="artefacts-et-limites"></a>

## Artifacts and limits

`validation/sync-owned-identity.crust` and its C keep a real return
by synchronous helper, async and join state. The initial address is the one of the result
and re-used slot; a=7 then b=9 are destroyed once. C retains an ABI
Cell * → Cell *, not applicable intermediate. The arguments are prepared before
Appeal C: the order of assessment C is not used to order the effects.

The general signatures of the aggregates, the pools injected with the
helpers from states, local pool creation in these and other states
The non-direct sources of income are still
This lot does not state that any factory or signature
The obligations still open of the seven drafts,
In particular, runtime/scheduler/Select/mutex and general placement remain active.

<a id="résultats-exécutés"></a>

## Implemented

| Campagne | Result | Journal in validation/ |
| --- | --- | --- |
| Owner lot O0 | 13 methods, 9,336 s, OK | `sync-owned-final-o0.log` |
| Native Regression and Runtime O2 | 134 methods, 153,121 seconds, OK | `sync-owned-regression-o2.log` |
| Contrats synchrones O2 | 130 methods, 66,683 seconds, OK | `sync-owned-contracts-o2.log` |
| Additional life O0, after adding two refusals | One method, 0.620 seconds, OK | `sync-owned-final-lifetimes-o0.log` |
| Final Change Campaign O2 | Current Baseline 13 green methods, six detected faults; one without observed effect on selected paths | `sync-owned-final-mutations-o2.log` |
| Artefact C O2 | Retained address, re-used slot, two unique destructions | `sync-owned-artifact-run.log` |

The thirteen methods of the final baseline include the two refusals added
after the start of the great regression: handle leaving the pool of a
still active, and loan returned from a transferred entry.
Initial logs with fixture errors and surviving mutation are
The success of campaigns is focused on these scenarios and configurations;
it does not terminate the proof of safety or the integration of the seven drafts.

Next: [Boolean calls and primitive block exits](SYNC_BOOL_CALLS_CYCLE.md).
