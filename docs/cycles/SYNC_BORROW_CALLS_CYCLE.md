[Français](SYNC_BORROW_CALLS_CYCLE-fr.md)

<a id="cycle--emprunts-des-auxiliaires-synchrones-dans-les-états"></a>

# Cycle — borrowings of synchronous auxiliary equipment in the states

<a id="portée-normative-et-implémentation"></a>

## Normative scope and implementation

Continue to [NATIVE_SYNC_CALLS_CYCLE.md](NATIVE_SYNC_CALLS_CYCLE.md), unchanged
AGENTS.md, VALIDATION_GUIDELINES.md and the index of the seven
drafts have been read; LANGUAGE_RULES.md and ASYNC_MULTITHREAD_RULES.md read
the previous cycle shall remain applicable.
MT1/MT6 and RT8 govern this lot.

Synchronous calls from a native block or async state now accept
&Int, &mut Int and &mut u8, in addition to scalar
The arguments can come from catches, local variables,
of tables and other synchronous results.
the type remains explicit; & on a reference is not flattened.

The existing synchronous backend receives symbolic seat parameters,
with their source, then generates a C function using pointers of the
No temporary Cell, copy of target or new allocation
substitutes the borrowing. L-ABI synchronous existing also uses C pointers
not for read-only loans: adaptation removes the qualifier C,
but does not change the Crust contract, which prohibits &Int's transfer.

The call check always uses FunctionContract. Backend n
called that after verify; a test intercepts its generation method and requires
that verify_program succeeds without calling upon. The results substitute the
reference_targets of the contract to the actual arguments, without reading the body at call.
A conditional result keeps all its possible targets.
who do not participate in the result are not arbitrarily reserved after
The parents of the loans retained remain protected.

<a id="préparation-suspension-et-durée-de-vie"></a>

## Preparation, suspension and life

Each argument is prepared from left to right. A loan provided to the call remains
active during the following arguments, even if one suspends.
A subcall that returns a scalar
may terminate the last use of a named loan before the following argument.
The analysis keeps external continuations and returns at the beginning of the
loops: future use prohibits such expiration.

A return during an argument cancels the preparation of the call.
temporary removal before cleaning out the owner-owned targets;
a pool of capacity one is then reusable. No call of the calle
no further destruction should appear on this path.

The borrowed result can be captured directly by a child task.
The reservation lasts for the child and, if the child returns, until the child
last use of the result received. Async return contracts also comprise
The results of synchronous auxiliaries. A local target or received by
transfer does not become sustainable because the return passes through an auxiliary.

<a id="écart-supplémentaire-corrigé"></a>

## Additional difference corrected

Drop tests revealed that backend states refused scalar
This refusal masked the
The loan control sought. According to L6 already retained, drop consumes now
Int, Bool, u8 and local tank connections, under exclusive access control.
He does not emit destroyers for these trivial values. Reading, writing
or second consumption after drop is refused. Drop before last
use of a loan is refused for this reason, rather than by absence
The views and other types are not considered covered by the application.
by this connection of the scalar.

<a id="scénarios-oracles-et-défauts-intermédiaires"></a>

## Scenarios, oracles and intermediate defects

`tests/test_sync_borrow_calls.py` contains sixteen methods: twenty-two executions
Crust/C and sixty-five refusals expected by full passage, with verification
The new system of separation between contracts and generation.

Cases cover reading and mutation of catches, local variables and boxes
Int/u8 ; aliases in arguments ; reading during a prepared mutable loan ;
mutual returns and shared reborrowing; last use in the middle of arguments;
future use in block, parent or subsequent iteration; yield in
an argument; return during preparation; conditional references since
two pools/targets; loans transported in join; failure to launch; passage
direct result borrowed from a child task; drop and reuse of the pool.

Oracles are explicitly traces of values, unique destructions,
Last-use constraints and target sets of functions
The first (only the first) is chosen (two targets).
contracts to decide expected outputs. Regression of synchronous returns
includes the existing model of generated targets; no new general model
No. of competition or random generator is claimed.

Initial probes found incorrect refusal of valid case
The continuation tracking between arguments on the
correct. Two first tests accidentally used the reserved name set
for a function; fixtures now use write_value.
initial also used .set(n), while the synchronous backend limits this
method in literal; it was expressed with writing *v = n already available.
These fixture problems are distinct from the drop implementation failure.

The first transfer log is not sufficient proof: the case of
alternative references still had failures not related to mutations, due to
The reinforced campaign now begins by demanding
a full green baseline. Injected errors relate to the reservation
arguments, loss of a possible target, forget about future uses,
the bad pointer rendered and the loss of the loan returned by the child.
live in temporary copies; tests and their expectations remain unchanged.

<a id="artefacts-et-limites"></a>

## Artifacts and limits

`validation/sync-borrows-example.crust` and the corresponding C keep a
actual probe: relay makes the pointer received, the native transmits it via join,
the target is 9, then the pool is reused for 10.
The C shows a parameter and an integrative result. *, then
direct assignment of this pointer to the result of the state.

Owner signatures, other aggregates and pools directly
created in states still to be connected. &u8 read uses another
family of types, still refused at this border; &mut u8 is covered.
General borrowed results from fields or containers are not covered
The limits are replaced by the direct scalar parameters only.
Bool synchronous signatures from the previous cycle remain open.

`sync-borrows-artifacts.log` keeps three probes: the first two
(transfer owner and &u8) remain open; the third, direct capture
of the synchronous result by a task, was then connected and tested in
test_returned_reference_is_captured_by_async_child. The initial log remains
The other obligations of the seven drafts remain active.

No formal evidence, TSan, second compiler or new validation
ASan. Previously recorded ASan blockages are not successful.

<a id="résultats-finaux-exécutés"></a>

## Final results achieved

| Configuration | Result | Journal |
| --- | --- | --- |
| Native Regression, Clang C11 pthread, O2, fatal UBSan | 109 methods, 117,219 s, OK | `validation/sync-borrows-final-regression-o2.log` |
| Borrowings, same checks, O0 | 16 methods, 18,946 seconds, OK | `validation/sync-borrows-final-o0.log` |
| Mutations O2 | Baseline 16 green methods, five detected errors | `validation/sync-borrows-validated-mutations.log` |
| Synchronous contracts O2, before the latest child drop/capture extensions | 130 methods, 64,240 s, OK | `validation/sync-borrows-contracts-o2.log` |

The five mutations are detected by unchanged test assertions.
The loss of reservation returned by the child accepts premature transfer;
for drop, it wrongly postpones the diagnosis on use after destruction.
This finished campaign does not give a general detection rate.

Continue: [&u8 shared and coming through calls](SYNC_BYTE_BORROW_CALLS_CYCLE.md). The &u8 limit above describes the beginning of this cycle and is lifted for the forms of the next cycle.
