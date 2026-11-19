[Français](ASYNC_OWNED_STRUCT_CAPTURES_CYCLE-fr.md)

<a id="captures-async-de-structures-propriétaires"></a>

# Async captures of proprietary structures

<a id="périmètre"></a>

## Perimeter

This lot applies existing rules T1/T6, D1/T11, B1/B2/B4a,
ST1/ST5/ST7/ST15, L1/L2/L6, AS2/AS5/AS8/AS9/AS13/AS14 and RT8.
Draft 01, 03, 04 and 05 are concerned. No normative decision
is not amended.

A task can receive a structure by transfer whose fields are
Int or allowances owned by Int, Thong, Vector<Int>, Vector<u8> or
other structures of this family. Inline nested fields use
the existing layout. The owner graph and addresses are kept.
Field readings Int and A<Int>, Int entries per mutable receiver,
local transfers, transmission to an async child and destruction
full are connected. Owner fields cannot be extracted
individual; no partial condition is introduced.

Own-owned catches containing borrowings, general sum,
async returns of proprietary structures and their transition to an auxiliary
Synchronous since async still to be integrated. This perimeter is not presented
the complete implementation of the rules on aggregates.

<a id="défauts-et-corrections"></a>

## Deficiencies and corrections

The [initial] case](../../validation/open-owned-async-struct.crb) was refused to the
signature async : [baseline](../../validation/owned-async-struct-baseline.log).
Translation now uses the Cell graph and its existing cleaning.
The types of structure remain available after renaming or transfer.
String/Vector fields cannot be read abusively as Ints.

After this first extension, a synchronous factory lost its provenance
The pool of a field possessed.
[contre-exemple](../../validation/open-owned-task-factory-short-pool.crb) was
accepted by both courses as the field pool finished before the task.
This acceptance is [conserved]](../../validation/owned-task-factory-counterexample.log) ;
the invalid program was not executed.

The practical capture now retains all the sources and origins of its
descendants possessed. The contract retains symbolic sources by way of
field, for example `.child/.value`. The relays make up these paths and
The callers are insistent on the real graph. Each pool must survive the
task, regardless of the root pool.

Two other refusals to valid programs were corrected: a synchronous return
direct `return <-fabrique(...)` used the processing of tables, and
the inference of a native block did not recognize the dereference of a field
A<Int>. The explicit return now uses the own lane before the
joint cleaning; type and source checks remain active.

<a id="vérifications"></a>

## Verifications

`tests/test_async_owned_struct_captures.py` There are nine methods.
independent finish places each of the three pools of a root graph → child → Int
The eight provisions are:
with a direct call, a factory and a relay: three programmes
21 refused. No body called is required to verify the source
of each field at the time of the instantiation of the contract.

Other cases check explicit transfers, mutability, readings,
the last use of a field loan before capture, the use after drop,
normal or refused launch, inactive destruction, preparation of
arguments before suspension and collections fields.

Four C probes have an unlaunched task only: initial status,
single suspension, termination and suspension during preparation of a
later argument. They check the addresses of the root and field,
destruction of children before their parent, one destruction and re-use
They do not add a public cancellation of a task launched.

Clang C11, pthread, Wall/Wextra/Werrar, Wno-unused-function and fatal UBSan.

<a id="chronologie-et-résultats"></a>

## Chronology and results

- `validation/owned-async-struct-initial-o0.log` : seven methods,
  seven sub-case failures and four errors; refusal of the calculated relays and
  Incomplete native inference. Journal retained.
- `validation/owned-async-struct-second-o0.log` : seven methods, two errors
  natives restantes ; `third-o0.log` : seven methods, OK after correction.
- `validation/owned-async-struct-final-o0.log` : eight methods, three failures
  UBSan from harness C: the second test object was destroyed without
  initialize its own field. The harness has been corrected to build
  a complete structure, in accordance with ST1/ST15. This result is not
  allocated to the compiler.
- `validation/owned-async-struct-final-fixed-o0.log` : eight methods,
  7.258 s, OK before adding the prepared argument suspension.
- `validation/owned-async-struct-complete-o0.log` : eight methods, 13,108 s,
  Okay with the four states. `owned-async-struct-borrow-o0.log` complete this
  passage with the ninth method on the successful field borrowing.
- `validation/owned-async-struct-counted-o2.log` : nine methods, 8,999 s,
  OK; 20 native executions and 32 invalid programmes controlled by the
  Two courses, 64 refusal checks.

The first five mutations campaign detected four of them.
cleaning a prepared capture survived, as the task was resumed until
the termination. The addition of the suspended probe detects this fault by the slot
The original journal is kept in
`validation/owned-async-struct-mutations-o2.log`.

`validation/owned-async-struct-mutations-final-o2.log` : baseline of eight
methods, 8,785 s, OK; five mutations detected: loss of concrete source,
loss of symbolic source, loss during instantization, refusal of field
native owner valid and forgets about prepared cleaning. Campaign completed
with code 0. The subsequent addition of the borrowing test does not change these oracles.

The initial regression O2 performs 67 methods in 109,161 s: 66 succeed,
a preserved two claims of refusal that have become obsolete.
reproduced on the copy of the compiler prior to the batch, in
`validation/owned-async-struct-boundary-baseline.log`.
The mutable field replacement is already covered by ST10/ST12 and the
[mutable termination cycle]](MUTABLE_FIELD_COMPLETION_CYCLE.md).
The test is updated with normal execution, failure of launch and refusal
access to the new target during execution. The corrected test and the ten
mutable termination methods go to O2 in 15.363 s:
`validation/owned-async-struct-boundary-final-o2.log`.

The consolidated regression in the
`validation/owned-async-struct-regression-final-o2.log` passes 76 methods to O2,
in 115.025 seconds, on the final code and the expected corrected. It includes the blocks
natives, structural catches by reference, reference fields, factories,
direct returns of allowances, Expected owner result and the nine
methods of this lot. Process completed with code 0. No process of this
lot is not active. Selections are overlapping; their numbers are not active
added as an independent cover.

## Limites

The next valid program refusal is retained in
[the return of proprietary structure](../../validation/open-owned-async-struct-return.crb),
with the diagnosis of the two internships in
`validation/owned-async-struct-return-baseline.log`. Modified Python files
and new tests pass `py_compile`. The diffs of the three main modules
are retained in `validation/owned-async-struct-*.py.patch`.

Models and probes are finished. Types and operations not connected
remain open, including returns of proprietary aggregates and catches
The calculated returns are not calculated in the form of a sum of
not checked for all possible compositions. No results ASan/TSan
no general proof of security is added. Arbitrations of captured handle
and select losers remain distinct from this lot.
