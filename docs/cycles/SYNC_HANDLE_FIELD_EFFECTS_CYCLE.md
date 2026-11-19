[Français](SYNC_HANDLE_FIELD_EFFECTS_CYCLE-fr.md)

<a id="contrats-synchrones-des-handles-portant-des-modifications-de-champs"></a>

# Synchronous contracts of handles with field changes

<a id="implémentation"></a>

## Implementation

No standard rule changed. This batch connects B4/B5, ST10/ST13, AS12/AS13
and RT7 for synchronous functions that receive a task or handle
carrying changes to already prepared fields. They can return it,
start the received inactive task, wait for the received handle or destroy the task
inactive. Creating a new task for modifying in a factory
synchronous remains distinct and unconnected.

Symbolic values now follow their original task parameters.
The contracts for profit and loss shall publish `task_wait_parameters` and
`task_forward_parameters`. These sets consist through calls,
conversions to a public handle, blocks, junctions and loops.
They describe the possibilities of paths; the body verification retains
separately the obligation to wait for each handle launched.

The opaque caller publishes the effects of parameters that can be expected before
control the destruction of sources of the contract.
keep delayed changes to their possible entries.
Inactive simply transmitted or destroyed does not publish any effect.
retains the initial alternative, as the launch may have failed.
A function that waits for one of the two handles and renders the other one according to one branch
retains both possibilities without pretending to have waited for both to be executed.

Functions with scalar result but with task parameters no longer pass
by the shortcut that produced an empty contract without browsing their instructions.
The calculation of the contract takes place at the definition; the opaque call does not run again
The dedicated test gives the caller synchronous contracts and the
Async descriptions necessary for creation, but no body catalog
synchronous, separate inferred results or auxiliary C definitions.
The call for `relay` do not enter the body of `finish`.

<a id="scénarios-et-écarts-corrigés"></a>

## Scenarios and Variance Corrected

Seven methods in `tests/test_sync_handle_field_effects.py` couvrent :

- public transfer then wait through three calls, with refusal of drop or
  mutation of targets, and failure of injected submission;
- transfer of inactive task, launch in helper and destruction
  inactive in another, with re-use of the slot;
- conditional transfer and loop result;
- calling using only synchronous contracts;
- historical reset after waiting, again refused if an external carrier must
  read the target; variant allowed after destruction of the holder and re-use;
- two handles to two separate carriers, one expected and the other returned
  according to the path, then final expectation and protection of the two new targets;
- model of eight cases (inactive/expected, carrier destroyed/living,
  (new target): five programs implemented and three rejected by the
  Two entrances.

The regression exposed a gap previously masked by the shortcut: the
summary refused to move a value array received from a join, so
the operation is already admitted by the rules and the backend. `Value` of the
mode `array` is now recognized in the explicit transfer.
cas historiques `[Int;2]`, `[[Int;2];2]` and `[u8;2]` pass again, with
Reuse of the capture pool after join. The expectations of these tests do not have
has been amended.

The first versions of the new tests used `Bool` in a signature
synchronous, corrected in `bool`, and had been passing hands from the parent scope since
an arm without a downward transfer. `a ->; b ->;` have been added
The rules have not been relaxed.
kept in newspapers `-initial` and `-expanded`.

<a id="preuves-exécutées"></a>

## Evidence

The O0 target pass succeeded in seven methods in 8.569 seconds:
`validation/sync-handle-field-effects-complete-o0.log`.
The target neighbour including the three returns of tables succeeds eight methods
in 7,709 s: `-expanded-final.log`.

The final additional orders are:

```
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_sync_handle_field_effects test_public_handle_contracts test_concrete_handle_relays test_sync_handle_bridges test_plain_join_contracts -v
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_fixed_arrays test_modular_calls -v
```

The first pass succeeds 67 methods in 67,906 s in `-complete-o2.log` ;
the second succeeds 96 methods in 34,122 s in `-array-regression.log`.
Async/child/contract regression passes
36 methods in 16.422 s in `-async-regression.log`, before the final addition of the mode
The first selection of 60 methods in the
`-regression.log` explained the three table errors described above.
These numbers are test methods; several execute families of
programs, others check contracts alone.

Native programs are compiled in C11 with pthreads, warnings
The Python compilation of the
modules and modified tests succeed. The patches from the beginning of the lot are
retained in `validation/sync-handle-field-effects-*.py.patch`.

The campaign `tests/run_sync_handle_field_mutations.py` withdraws separately the
Summary of waiting, its composition through a relay, the origin of the handle
returned, its delayed effects, opaque application or function analysis
task parameter scalar. The log of the final pass is
`validation/sync-handle-field-effects-complete-mutations.log`. Ces essais
In particular, seek a disagreement between the opaque call and the backend between
in the body to produce specialized C.
The six mutations are detected in this final pass.
is not a general rate of detection of compiler defects.

## Limites

Synchronous factories creating a new edit task remain refused.
Synchronous helpers called from an async state do not yet receive these
The effects are conservatively combined; a branch that returns
a handle rather than waiting for it can keep more reservations
the full correlation between branches, the result of the launch
The other boundaries of the batches of async fields, including the
mutable fields and the results of the editing tasks remain.

This selection is neither exhaustive validation nor evidence of
No new ASan/TSan evidence, comparison between
Independent C compilers and formal evidence. The overall objective remains active.
