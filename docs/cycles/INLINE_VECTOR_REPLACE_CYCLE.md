[Français](INLINE_VECTOR_REPLACE_CYCLE-fr.md)

<a id="cycle-en-cours--replace-des-structures-en-ligne"></a>

# Current cycle — Replacement of online structures

<a id="règles-et-périmètre"></a>

## Rules and scope

VE1–VE3, H1, U1, B1–B5, T4/T5/T6, ST15/ST17/ST18 remain unchanged.
AGENTS.md, VALIDATION_GUIDELINES.md and the index of drafts were read.
The full specification has been read in continuous work; the rules of
vectors and relevant memory interactions are included for this batch.
No new semantics or normative decisions.

This historical checkpoint connects synchronous local operations and functions
who perform the replacement then consume the result. It does not close
Replaces: contract return and async integration remain open.

<a id="baseline-et-réalisation"></a>

## Baseline and implementation

Snapshot initial : `/tmp/crust-before-inline-vector-replace`.
`validation/inline-vector-replace.crust` is the case VE3 minimum, kept with
his refusal to both entries in `-baseline.log`. It now runs with
the expected release 7 then 9.

An input value T must be explicitly transferred and must no longer be
A<T> does not implicitly replace T. L
The C uses the following:
local porter of the input: vector_replace exchanges its bytes with those of the
If the index is invalid, the result has the following:
The targets of fields A<T> keep their addresses; only their
cleaning responsibilities change carrier.

The result is typed Result<T,T>. Its success carries the fields of the old
The old input variable is
invalidated without destroying the transmitted fields. The vector cleaning layout
is kept for proprietary fields. A known constant position is
Update precisely; unknown positions remain conservative.

The results types distinguish Result<T,T> and Result<A<T>,A<T>.
recognition also prepares their identification in typed wrappers,
But this recognition does not prove their full integration into contracts.
Sharing the code of evaluation of an incoming one between push and replace avoids a
second implementation of their transfer constraints.

<a id="défauts-rencontrés-et-ciblé"></a>

## Faults encountered and targeted

The first target performed six methods and reported six failures/sub-failures:
the arrowless diagnoses were generic, and the success branch of a
statically invalid index was not marked without load.
then tried to use a graph of fields absent.
The transfer diagnosis is explicit.
Second target: six methods, 3.924 s, code 0.

A function call to build the entrant then revealed two reservations
temporary mutables from the same vector. Replace keeps its reservation for
The assessment of the index and the input; the joint assessment does not add any
The third target keeps this failure; the fourth pass.

`validation/inline-vector-replace-targeted-fourth.log` : **seven methods,
4,737 s, code 0**, O0/UBSan. **13 successful C executions**, **huit variantes
invalides** controlled at both verify_program/compile_source entries.

Cases admitted: success, negative/outside indices, annotated result, transfer
name/fresh, own and borrowed fields, read after the vector drop,
single cleaning of descendants, re-use of two slots, empty structures,
direct drop, result consuming function and observable order of evaluation.
Cases refused: T/A<T>, missing arrows, old name after transfer, incoming
still borrowed, owner's motif ignored and transferred a target before the
Reset remains removed from the current profile.

<a id="régression"></a>

## Regression

Selected regression completed: **142 methods, 111.163 s, code 0**,
O2/UBSan, in `validation/inline-vector-replace-regression.log`. The 43 fingerprints
compiler/tests are unchanged during the pass.
pop, push/remove and fields of online structures, their existing async uses,
as well as synchronous/async typed owner exchanges.
Selection and fingerprints: `validation/inline-vector-replace-selection.json`
and `-start.json`. Diff : `validation/inline-vector-replace.patch` ; manifeste :
`-changes.json`. This success does not close the gaps in the placement below.
The minimum fixture C is retained in `validation/inline-vector-replace.c`.
The harness uses C11, pthread, Wall/Wextra/Werrar, fatal UBSan and O0/O2.

<a id="suite-du-checkpoint"></a>

## Checkpoint continuation

Synchronous returns and Result<T,T> parameters have since been connected and
[the cycle of contracts](INLINE_VECTOR_REPLACE_CONTRACTS_CYCLE.md).
The fixture -replace-return.crust below therefore describes the initial refusal,
The async integration remains open.

<a id="écarts-au-moment-du-checkpoint-et-limites"></a>

## Checkpoint deviations and limits

`validation/inline-vector-replace-return.crust` The candidates of the
the old box does not yet describe the local holder of the returned result,
and the placement of its roads must be connected.
`validation/inline-vector-replace-contract-baseline.log` shall retain this refusal and
the consumer, since corrected by the follow-up of the identity of the box.
The corrected consumer is now tested; the return is not like
feature acquired. L的async remains to be processed in this batch.

No general proof of safety. Unions after unknown clues and
The target regression is not reported as complete.
does not replace the final audit of all rules. No adversarial campaign
The results of the independent lab are not available here.
The global construction site remains active.
