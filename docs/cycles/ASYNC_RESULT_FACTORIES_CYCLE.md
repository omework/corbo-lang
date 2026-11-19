[Français](ASYNC_RESULT_FACTORIES_CYCLE-fr.md)

<a id="fabriques-synchrones-de-tâches-et-destination-du-résultat"></a>

# Synchronous task factories and destination of result

<a id="règles-et-résultat"></a>

## Rules and results

This lot applies AS2/AS3/AS5/AS9–AS14, T1/T6, V5, L1/L2/L7, B1/B2 and
ST10/ST15, as well as the T/A<T> distinction of drafts 03/04/05/07.
No normative rules are amended.

A synchronous factory can now return a task that will build
a new local structure. The destination of the future result comes from the
The result is that the factory receives and survives on its return.
address; it is not allocated at the time of inactive task creation.
Examples recorded `open-async-result-storage-factory.crust`,
`open-async-result-factory-async-caller.crust` and
`open-async-result-factory-relay.crust` are now being tested.

<a id="implémentation-et-invariants"></a>

## Implementation and invariants

Contracts distinguish two internal origins from future results: a
nouvelle destination locale (`task_output`) and a copy of which storage
depends on the parameter (`task_output_parameter`) The latter uses a
new destination if the entry is local, or the pool of the entrance if it
These markers are not new notations.
and do not promote a borrowed local catch.

Origins cross factory calls, contracts without bodies,
alternatives and the transfer of an already built instance.
static constraints distinguish the destination of copying from the allowance
original. The junctions of the result do not mix local T and A<T>.

Synchronous backend transmits hidden source to identified producers
The placement also follows a task returned by blocks
The source is not closed in the factory.
remain distinct from the targets borrowed, which must always survive the task.

The factory call from an async state uses a turning C bridge
`CrustTask *`. It transmits the destination, the dependencies captured, those
The bridge exports the task instead of the result and the delayed effects.
destroy in its local cleaning. &mut Int and &str results keep
their reservations after waiting. Inactive creation and waiting remain
separate operations.

The analysis of the termination effects now knows how to apply the contract
The company re-uses the join analysis for the
origins of the result, then restores the direct signature and the entries
Final exact: a direct wave has no branch LaunchFailed. The effects
intermediate suspensions are not invented; this suspension contract
remains explicitly unknown for factories not represented by their
captures originales. Cela peut encore refuser certaines compositions Select.

<a id="défaut-trouvé-pendant-le-raccordement"></a>

## Default found during connection

`open-async-factory-field-valid.crust` update `View.data` To `b` in
a task created by a factory and then expected by an external task.
His neighbor `open-async-factory-field-invalid.crust` destroyed `b` after join
before reading `View.data` - it must be refused.

Before the termination effects were connected, both programs were
The newspaper refused as unsupported.
`async-result-factories-completion-before.log` reproduces this result with
the previous effects module and other files in the current batch.

A first attempt at adaptation called for a form that the analysis
synchronous symbolism did not process. It produced an unknown value and
lost the field writings: the invalid neighbor was accepted.
`async-result-factories-completion-initial.log` retains this acceptance
intermediate. **This invalid program was not implemented.**

Corrected connection applies final effects and rejects result
symbolique inconnu. `async-result-factories-completion-corrected.log` montre
the valid program accepted and its neighbour refused to borrow still used.
The final suite executes the valid, checks the refusal in both courses and
requires that the final contract of the field only targets the parameter `n`.

<a id="vérifications-exécutées"></a>

## Audits performed

The paths are related to `validation/` :

- `async-result-factories-initial.log` : first example executed, output 7.
- `async-result-factories-suite-initial-o0.log` : eight successful methods,
  9.866 s, before the bridge from async.
- `async-result-factories-regression-initial-o2.log` 88 successful methods,
  76,140 s, before the factory connections to the async states.
- `async-result-factories-async-initial.log` keeps an error Python of
  the inference adapter (missing cache argument), corrected then.
- `async-result-factories-expanded-o0.log` : **douze** The scenario introduced a local pool<Point>
  in an async state, still not connected independently of the factories.
  The minimum programme is retained in
  `open-async-result-factory-local_struct_pool.crust`. The interaction test
  with a pool now uses a Point created in the synchronous pool and
  transferred to the task; this is not a validation of the missing local pool.
- `async-result-factories-corrected-expanded-o0.log` 13 methods pass,
  9.815 s; control of conditional sources follows in the O2 type journal.
- `async-result-factories-regression-final-o2.log` 191 successful methods,
  165,260 s, **avant** the addition of termination effects and UTF-8 views.
  The name of the newspaper is historical and does not indicate the last state of the lot.
- `async-result-factories-counted-final-o0.log` : **16 methods**, **35 executions
  natives**, **neuf programmes invalides** refused both courses, i.e.
  **18 refusal checks**, 20,660 s. Aucun skip.
- `async-result-factories-mutations-final-o2.log` : baseline of the sixteen methods
  successful in 21,041 s, then **eight mutations detected**.
- Regression after completion supplement: **216 successful methods in
  166,544 s à O2**, terminal result `OK` in
  `validation/async-result-factories-completion-regression-o2.log`.

Native compilations use Clang C11, pthread, Wall/Wextra/Werrar,
Wno-unused-function and fatal UBSan, at O0/O2 according to newspaper. No results
ASan/Tsan new and no general proof of security is claimed.

Scenarios include chain mills, transfer of proceedings,
conditional and loop returns, local and pool copies,
transfers to parents, callers sync/async, Select, results
borrowed, inactive cleaning, injection rejection and two tasks
The copy branches use a simple oracle: 7 for entry A,
9 for B; both inputs may have local or pool storage but
not different storage types for the same result.

The C probe itself provides an external source to the factory.
No cell is created and no source is closed. After suspension, the cell
The source of the information is the same as the one in the previous page.
The state pool is empty. After normal destruction or internal cleaning of a
instance not launched suspended by poll, the cell is destroyed once,
the cursor returns to zero and only the probe closes the source. It is not
a task cancellation API launched.

## Mutations

The eight errors remove the origin of the future result, its preservation at the
transfer of a task, the source distinction of a local copy, the
destination transmission, export of the task of the bridge, pointer of the
destination to runtime, accuracy of final field writings and
reservation of a UTF-8 view returned.

The first mistakes are detected by unexpected refusals or assertions on
the contracts. The task destroyed in the bridge fails to perform with
`invalid async await`. The NULL destination is detected by fatal UBSan.
The visual mutation is detected by the acceptance of an invalid neighbour.
No oracle is altered in mutated copies. The eight targeted detections
do not constitute an overall estimate of coverage.

<a id="limites-et-suite"></a>

## Limitations and follow-up

- The pools of structures created directly in an async state remain open.
- The graph of a new local result with proprietary or borrowed fields and
  the refund after replacing a proprietary field has yet to be completed.
- Analysis of prefixes suspended from tasks created by the factory is not
  Some Select compositions remain generally refused.
- The more general signatures/captures and arbitrations already recorded on
  The handles are still open, and no rules are changed to bypass them.

Snapshot : `/tmp/crust-before-async-result-factories` ; diffs preserved in
`validation/async-result-factories-*.py.patch`. Tests, probes and mutants
The full goal of the seven drafts remains open.
