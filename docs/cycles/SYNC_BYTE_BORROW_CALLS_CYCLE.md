[Français](SYNC_BYTE_BORROW_CALLS_CYCLE-fr.md)

<a id="cycle--appels-synchrones-avec-emprunts-partagés-u8"></a>

# Cycle — synchronous calls with shared borrowings u8

<a id="exigences-et-périmètre"></a>

## Requirements and scope

Continue to [SYNC_BORROW_CALLS_CYCLE.md](SYNC_BORROW_CALLS_CYCLE.md), unchanged
The index of the seven drafts,
B1–B5, D1/D3 and AS1/AS2 were reconsulted, as well as TX1/TX2/TX5/TX12 in
UTF8_STRINGS.md. The existing contract mechanism remains the source of control
at call; the bodies then serve for the generation of C.

Calls from async states and native blocks now take up
parameters and results `&u8`. L’ABI utilise un `const unsigned char *` direct,
with a symbolic space borrowed for synchronous generation. No byte
No allocation is copied to materialize the reference.

The arguments can be named references, bytes of literals,
of tables and string, a shared reborrowing of `&mut u8` (name passed directly to a shared parameter or `&*` explicit), a result
borrowed synchronous or a local variable u8 explicitly borrowed by `&`.
Access to a reference is not flattened by a second `&`. The pointer and the
ready are prepared before the following argument; suspension of an argument
a return interrupting the preparation does not call
not external function.

The result replaces the targets `utf8_parameter` of the contract to loans from
The two targets of the `choose` are preserved;
the second parameter of `first` The following information is not kept after the call.
Async results now composes these contracts, including through a child.
This clarification does not shorten catches during execution: it concerns
loans remaining attached to the result after its termination.

A loan from a local byte in the state cannot be returned. Dependencies
protect against drop, change and premature re-employment after
`join`. Reset control is only exercised in the historical profile
`allow_legacy_reset=True` Reset remains removed from the prototype API.

<a id="contre-exemples-et-raccordements-supplémentaires"></a>

## Additional counter-examples and connections

The probe stored in `validation/sync-byte-artifacts.log` revealed a refusal
valid: prepassing native blocks did not deduce `&u8` since `&a[0]`
lorsque `a` was a String. L'indexation de str, String et Vector<u8> est
now recognized as u8. Prepassing also preserves the `&` in
the type of join result for text and byte_ref modes. There is still one
prepassing of types: the ordinary memory check controls the catches.
The String case is executed and declined with premature drop refused.

The first fixtures had four separate compiler problems:
yield in a native block, direct print of a String, a BEFORE marker left
in the allowed case, and a drop of a parent variable in an argument block
The changes were corrected according to the existing rules.
A too wide edition then changed the print of an Int parameter to
String view; this fixture defect is also stored in the initial logs.
No semantic expectation has been changed to make implementation wrong
acceptable.

<a id="vérification-et-oracles"></a>

## Verification and oracles

`tests/test_sync_byte_borrows.py` contains twelve methods: 19 compilations
and C-delivery expected valid and 47 variants expected refused,
plus two positive checks without C (opaque contract and historical reset).
Expected values and constraints are written without consulting the abstracts
The 0/1 choices of `choose` doivent rendre 7/8 ; `first` garde uniquement
The sequences require a reading before release, a
transfer after last use and actual re-use of a pool of
ability one. L-failure of injected pthread_create must make Err and allow
Cleaning.

Interactions examined: B1–B5 × AS2/AS9/AS12/AS15 × L6 × MT6/RT8 × TX5;
arguments suspended and interrupted, interlocked calls, mutable parents,
loops, loops, capture and return of a child, join,
source of the result, drop/reset and re-use. Existing UTF-8 view tests
and loans Int/mutable are re-executed.
UTF-8 is included in the UTF-8 selection; no new model
No formal evidence is claimed.

Cs go through Clang, C11, pthread, `-Wall -Wextra -Werror`,
`-Wno-unused-function`, `-fsanitize=undefined -fno-sanitize-recover=all`,
No new ASan/TSan evidence or any other evidence
The ASan blockages of previous cycles remain limited.

<a id="mutations-et-artefacts"></a>

## Mutations and artifacts

`tests/run_sync_byte_mutations.py` First, a green baseline.
The loan of the prepared argument, the
second target of a return, the right pointer rendered, the precise selection of the
parameters in the result async, and loaning a local u8. The five faults
The ignorance of the contract produces a false refusal of the program
valid that destroys the unreturned source: it is a semantic detection,
The tests are not modified in these copies.
No general detection rate is derived from these five selected mutations.

The runner of mutations of the previous cycle stopped first on an anchor
not unique, after its green baseline. The new byte_ref connection contains
aussi `loans.extend(held)`. The anchor is now qualified by the call for
`sync_borrow_argument`. This judgment is an unexecuted campaign, not a
The initial log is kept separately.

`validation/sync-byte-native-return.crust` and its C are preserved.
`validation/sync-byte-native-artifacts.log` Shows exit 65 then B,
destruction/recovery of each pointer string a/b and ABI
shared. The test allocates b in the capacity pool one after destruction of a.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The parameters that own synchronous calls from states, states,
general aggregates, pools created directly in these and other states
deviations of the seven drafts remain open. This batch connects &u8; it does not
does not claim to generalize all signatures of views, fields or
The finished evidence does not demonstrate the general security.

<a id="diagnostic-de-régression-utf-8"></a>

## Regression Diagnosis UTF-8

The selection of eighty methods ended with failure to assert
The programme was not accepted.
`return &t[1]` → `return t[1]` in the fixture simultaneously changed leaf
(async) and byte (synchronous). The inference of the contract d
u8 instead of &u8 before the expected async diagnosis. The fixture modifies
now only the first occurrence, that of leaf, keeping
The log of this regression remains the same.
retained; the corrected test is re-executed in the final target batch.

Additional precision for named arguments u8 applies
when a &u8 is expected. It does not change the general inference of the type
d
(parent and &*The use of the latter, then the resumption of mutation, and conflicts
before last use.

<a id="résultats-exécutés"></a>

## Implemented

| Campagne | Result | Journal in validation/ |
| --- | --- | --- |
| Native O2 regression before last type/capacity connections named | 119 methods, 175,793 s, OK | `sync-byte-regression-o2.log` |
| Selection UTF-8 O2 | 80 methods, 167.596 s, a failure of fixture diagnosis described above | `sync-byte-utf8-regression-o2.log` |
| Lot u8 + native parser O0 then O2, after native type correction | 18 methods, 13.723 s / 18.248 s, OK | `sync-byte-final-o0.log`, `sync-byte-final-o2.log` |
| Union of the two pools through join, later addition | A method at O0 and O2, OK | `sync-byte-conditional-o0.log`, `sync-byte-conditional-o2.log` |
| Full u8 with mutable arguments named | 12 methods O0, 10.885 seconds, OK | `sync-byte-named-parent-o0.log` |
| U8 and Int/mutable packages combined | 28 methods O2, 20.755 s, OK | `sync-byte-named-parent-o2.log` |
| Final control after restriction of conversion to the expected context | 15 methods O2, 16,805 s, OK; shared parent test O0, 1,570 s, OK | `sync-byte-final-interactions-o2.log`, `sync-byte-final-shared-o0.log` |
| Mutations finales &u8 O2 | Complete Baseline 12 green methods, five detected errors | `sync-byte-final-mutations-o2.log` |
| Previous changes Re-executed int/mutables | Baseline 16 green methods, five detected errors | `sync-byte-borrow-final-mutations.log` |
| Inspection d’artefact natif O2 | 65 and B, destruction and re-use of the pool, pointers C const | `sync-byte-native-artifacts.log` |
| Python syntax and local links | Huit fichiers Python, aucun lien local manquant | `sync-byte-structural-checks.log` |

The final passage of fifteen methods contains the twelve current u8 methods,
the corrected UTF-8 test and two existing loan/enterprise tests u8. The others
methods of selection of eighty are not claimed to be re-executed
After these last connections. Intermediate newspapers and failures
remain available. The diff implementation and new tests are kept
in `validation/sync-byte-implementation.patch`.

The next identified connection remains the transfer of proprietary parameters
Synchronous auxiliaries from a state, with cleaning of prepared arguments
and possible restoration of identities.
d − integration of all seven drafts.

Follow-up implemented: [transfers of owners to auxiliaries](SYNC_OWNED_CALLS_CYCLE.md). The previous limits describe the state of this cycle.
