[Français](PUBLIC_STRUCTURE_HANDLES_CYCLE-fr.md)

<a id="handles-publics-de-structures--type-du-stockage-et-champs-empruntés"></a>

# Public management of structures: type of storage and borrowed fields

<a id="règles-et-périmètre"></a>

## Rules and scope

Ce lot applique V1, T1/T6, B1–B5, D1, L1/L2/L6, AS9/AS12,
MT5/MT6 and explicit waiting obligations. No normative rules are
amended. `runtime::Handle<T>` for a local structure and
`runtime::Handle<A<T>>` for a pool allowance are separate.
conversion of handle representation does not promote the storage of the result.

The Counter-Example `validation/open-public-local-structure-handle.crust`refused
by the registry of signatures in the previous cycle, is now accepted
This lot covers structures represented by the backend, their
Int shared/mutable borrowings, the finished owned graphs tested, and a
owner charge in an nested Result. It does not generalize all the
possible signatures of language.

<a id="implémentation"></a>

## Implementation

The public handle register receives the declared structures.
unknown nominal is not accepted by default. The public descriptor described
separate temporary catches, source of result and fields
borrowed after waiting. The result group carries the paths
complete, including references in the possessed descendants.

Conversions check the form of the result, then its local/pool source.
Public annotations and signatures produce storage requirements
a function called with an inactive task
may require local storage of its future result; its C bridge describes this
requirement, and its caller has the control before choosing the variant.
The decision is not based solely on the type of internal result `owned`.

Fields retained after join/wait are projected in the analysis of results,
the flow of constraints, the concrete verifier and the metadata of the backend.
Synchronous relays can only work from the public type,
without task definition or function body at their calling.
and proprietary fields also retain the dependencies of their pools.

The unification of two types of tasks uses the public type expected or the
The verifier now retains the storage and storage of the material.
the ancestry of the previous branch when it builds its representation
The backend also distinguishes branches with local results and
in pool, even if they run the same routine and the handle is not
The mixture is refused instead of being considered as a conversion.

<a id="vérification-exécutée"></a>

## Verification performed

Fourteen methods in `tests/test_public_structure_handles.py` :

- Initial fixture, return via incoming task or build from a
  structure transferred; refusal of drop before waiting and before last use.
- Two relays per public type and then return of the structure; verification of a
  calling without any function body or async definition.
- Local/pool matrix in synchronous and async annotations, arguments
  the results, even if the appellant destroys the result.
- Transferable and shared re-borrowing of a mutable parent: incompatible access
  refused during the use of the bearer, then admitted writing after his drop.
- Local root and descending graph possessed containing a reference;
  protection of the target and re-use of the down-to-down pool after cleaning.
- Refusal to export a handle dependent on a child pool destroyed when returned.
- Two types of routines combined under a public type, true/false branches,
  and local/pool mixture refused with or without annotation.
- Manufactured a task creating a new local root in a destination
  durable; result wrapped in Result and maintaining two levels of error.
- Injected launch failure at both levels, single destruction and reuse
  repeated capacity one pools (states and data).

`validation/public-structure-handles-final-count-o0.log` : **14 methods,
24 native executions, 26 invalid programmes and 52 refusal checks**, in
21.958 s. Added to the contract controls and the appellant isolated: a script
and its neighbour refused by `Compiler.block`, without autonomous execution C.

The native harness uses Clang C11/pthread, Wall/Wextra/Werrar,
Wno-unused-function and fatal UBSan at O0/O2. Submission failures are injected
in the generated C without changing the expected results. py_compile succeeds.
No new ASan/TSan results nor general safety evidence.

The first regression of 155 methods, in 173.953 seconds, contains 30 failures
on the formulation of annotation diagnostics: invalid programs
were refused but the prefix `annotation de handle` that prefix was gone.
The targeted complement of 21 methods is restored without weakening the assertions.
then move to O0 in 23.352 s, including the fourteen batch methods and the
Historical annotations. Newspapers are kept.

Final regression passes **157 methods in 180,070 s** O2 with
CRUST_SANITIZE=undefined :
`validation/public-structure-handles-final-regression-o2.log`. Elle inclut
public scalare, owners, borrowed and views, requirements
storage, task arguments, separate references, envelopes
local, returned local graphs and handset relays.
All validation processes cited are completed.
keep an exit code 1 because of their survivors, as detailed
below; the unmuted suites pass.

<a id="mutations--résultats-et-limites-explicites"></a>

## Changes: explicit results and limits

`validation/public-structure-handles-final-mutations-o2.log` contains a
The basic method of 14 O2 methods in 21922 s, then **six detected errors
and a survivor**. The runner ends with code 1 because of this survivor;
It is not a fully green campaign.

Are detected: loss of fields in the result contract, loss of their
concrete projection, public descriptor without fields, forgets local storage
of a task argument, omission of the local public requirement/pool and omission of the
The detections are assertions, often
incorrect rejection of a valid program; they do not represent six
memory corruptions executed.

The first campaign detected five mistakes and left two to survive.
The concrete projection was not carried out by the tested factory: its contract
The direct annotation test was already reconstructing the fields in the appellant.
This border is being exercised and this mutation is being detected.
with his refusal of the valid program.

Removal of field loans added to the list of post-suspense loans
The test is still in the target range and is also surviving the twelve methods.
in the suite, executed in a copy mutated in 12,598 s.
scenarios, metadata of the result fields retain protection.
This does not establish that the transfer is equivalent in all programs;
the sensitivity coverage of this representation remains partial.

`validation/public-structure-handles-historical-mutations-o2.log` detects
**five of the six historical mistakes** The removal of the
`projection_assets` for a vector index survives the selected test.
This survivor is kept as a limit; no historical result more
This campaign is not deduced from this campaign.
General coverage rate of security.

The first attempts also revealed two errors in fixings: a
writing via the mutable parent before the holder's yet to be dropped, and
a single script parser without structure name register. Fixed
now follow existing rules; intermediate newspapers remain
The actual lack of unification of branches is reproduced in
`open-public-structure-branch.crust`, then corrected.

<a id="état-restant"></a>

## Remaining State

`validation/public-structure-handles-remaining.log` confirms both stages
closing the five examples of public handles of the structures of this lot.
Deux cas valides restent explicitement ouverts :

- `open-public-structure-async-relay.crust` : passing a handle already launched to a
  synchronous function from an async state. The argument signature is not
  It is not a normative ban.
- `open-nested-field-replacement.crust` : replace the dependencies of a field
  down by call from async.

SL2 remains applied: `open-select-launched-handle.crust` is refused to both
The capture of a handle launched in an inactive task remains an arbitration
General placement, general signatures and the
public replacement of the scheduler is not completed. No reset is
The overall objective remains active.

The patches of the seven modules are archived under
`validation/public-structure-handles-*.py.patch`. The reference snapshot is
`/tmp/crust-before-public-structure-integration/`, except handle_types.py and
async_lowering.py whose preparation started before this lot is included since
`/tmp/crust-before-public-structure-handles/`.
