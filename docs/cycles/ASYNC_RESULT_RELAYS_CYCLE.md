[Français](ASYNC_RESULT_RELAYS_CYCLE-fr.md)

<a id="résultats-locaux-async--blocs-parents-et-relais-entre-états"></a>

# Local results async: parent blocks and relays between states

<a id="règles-et-implémentation"></a>

## Rules and implementation

This complete batch ASYNC_RESULT_STORAGE_CYCLE.md for T1/T6, V4/V5,
L1/L2/L7, B1/B2 and AS2/AS9–AS14. The normative rules remain unchanged.
A new local value for the parent must be built in its
storage; wait for an intermediate task should not move this value
The placement of the result does not promote the targets
borrowed by the catches.

`async_local_placement.result_constructors` now track async calls
and their expectation from full result contracts.
The analysis is a process that is not only a function of the task instance but also of the internal analysis.
the identity of the manufacturer through connections, branches, telescopes and the
fixed point of loops already existing. It does not re-route the body of the loops.
functions called. Unknown sources, results containing fields
unconnected and captured input returns remain outside this new plan.

The same follow-up feeds the placement of the result of a block, the replacement
an existing receiver and the external destination of a function result
Async. A child call can receive directly the destination of its
He's not responsible for his closing.

Sources external to the state (local captures and destination of the result)
are classified above the internal telescopes.
no longer shorten a previously established placement to this source.
The explicit form `receveur = <- enfant().await` is also connected to
the replacement branch by expected result. The old value remains
live during the assessment of replacement.

Snapshot : `/tmp/crust-before-async-result-relays`. Diffs retained in
`validation/async-result-relays-async_lowering.py.patch` and
`validation/async-result-relays-async_local_placement.py.patch`.

<a id="preuves-exécutées-et-chronologie"></a>

## Evidence and chronology

- `validation/async-result-relays-initial-o0.log` 23 methods implemented,
  of which the 14 methods of the previous batch discovered inadvertently via
  the import of a test class. A failure reveals the form `<- … .await`
  Not recognized in an assignment. Import is corrected for module import,
  without removing any scenario from the intended suite.
- `validation/async-result-relays-corrected-o0.log` : nine methods pass,
  6.888 seconds before the cases of transferred task and replacement in a relay.
- `validation/async-result-relays-expanded-o2.log` : nine methods, one failure.
  New replacement case in a relay reveals a shortening
  the external destination through the local assignment plan.
- `validation/async-result-relays-corrected-expanded-o2.log` : the nine methods
  pass after ranking external sources above internal telescopes.
- `validation/async-result-relays-counted-o0.log` : nine methods pass,
  **18 native executions**, **quatre programmes invalides** refused to both
  stages, soit **eight refusal checks**, 12,062 s. Aucun skip.
- `validation/async-result-relays-mutations-o2.log` : basic of the nine methods
  successful in 10.619 s, then **six mutations detected**.
- `validation/async-result-relays-regression-o2.log` : **130 methods** passent
  on the final code, 121.940 s, including the 14 methods of the previous batch.
  The finished propagation model of the producers after loop of the previous batch
  is part of this selection.

All the processes mentioned have observed terminal status.
`validation/async-result-relays-remaining.log` confirms the restrictions
The results of the analysis are shown in Table 2.

C-executions use Clang C11, pthread, Wall/Wextra/Werrar,
Wno-unused-function, fatal UBSan, at O0/O2 according to the newspaper.
initial failures are retained. There is no new result ASan/TSan.

The following covers the examples recorded: `open-async-result-storage-child_parent`
and `open-async-result-storage-relay`, successive transfers, named task or
transferred before waiting, branches, loop with continuous, calculated returns,
chain of three states, replacements, independent copy of an original of
child's scope. Invalid neighbors forbid the drop of a capture still
borrowed, the output of a task with taken capture too short, the result
dependent on a child pool and drop of a still borrowed result.

Two families of C probes control the result at selected stages
Independent of the compiler's plan. Closing the storage of a block
child leaves the cell of the living parent at the same address.
relay returns its two state slots before the last use of the result.
internal cleaning of an unlaunched suspended chain destroys its cell one
Once and close its source once, then the three pools are empty.
do not read a cell after the closure of its source.
loop awaits three constructions/destructions, including a value restored.

## Mutations

The errors shall, respectively, withdraw the recognition of an async producer,
the propagation by await, the local origin of a copied entry, the priority
The five main categories of the external destination and the explicit form of replacement are:
errors are detected as unexpected refusal of valid programs.
The sixth replaces the destination pointer in the state with NULL; it
is detected by failure of execution of the probe under fatal UBSan.
The oracles remain unchanged in the mutated copies.
not a general coverage of all possible errors.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Update: the factories described below are connected in
[the next cycle](ASYNC_RESULT_FACTORIES_CYCLE.md), with the limits which
This section maintains the end-of-batch record.

Synchronous task factories with new local value remain
to be connected (`validation/open-async-result-storage-factory.crust`) Storage
hidden from the future result must be transmitted from the recipient of the factory,
and not created in its temporary scope.

Graphs of results with proprietary or borrowed fields, returns
after replacing the owner field, and general signatures keep
The differences in the details of previous reports.
New result and returned parameter are not generalized by this plan.

These are finished paths, probes and targeted mutations; no evidence
the formality or coverage of all orders is not claimed.
obligations of the issued handlers and the already recorded arbitrations do not change
The overall objective remains open.
