[Français](MUTABLE_FIELD_COMPLETION_CYCLE-fr.md)

<a id="remplacement-de-champs-mutables-dans-les-états"></a>

# Replacement of mutable fields in states

<a id="implémentation"></a>

## Implementation

This batch connects ST10–ST12, B1/B2/B4/B5 and AS12–AS16 without change
The tasks may replace a field of `&mut Int` d'un porteur
Injected, directly or via helper, then read or re-borrow.
changes follow the expected children and synchronous factories.
The result can be scalar or a shared/mutable reborrowing of the field.

The state keeps reservations to the new target. A reborrowing of the field
the holder's field capacity: its replacement and its
access remains denied until the last use.
results include the new target of a modified field in addition to its carrier.
Calls and returns do not copy mutable references.

An unchanged alternative in a conditional blind represents the target
The new one is not an active reborrowing of its own capacity.
marqueur interne `stored_mut_target` makes this distinction.
The new banks are retained exclusively and the real re-borrowings are retained
field reservation. Branch junctions and failure to launch
keep the necessary initial alternatives.

<a id="recherche-de-contre-exemples"></a>

## Search for Counter-Examples

Ten methods in `tests/test_mutable_field_completion.py` couvrent :

- direct assignment and helper, suspension and then mutation via the field;
- the identity of the target by reading the two allowances after the holder has been destroyed;
- access and transfer of the new target refused from the original parameter;
- retours `&Int` and `&mut Int` : reserved carrier target and field;
- children expected and then re-borrowed, made hand and re-use;
- reborrowing named alive through yield, access to the forbidden field before its last use;
- conditional replacement, including conditional child followed by parental access;
- historical reset refused before last use, accepted after destruction of the bearer;
- return of the loan through a child and a relay;
- 8-case independent model: inactive/expected task, live carrier/destructive,
  Target a/b. Five programs implemented, three rejected by verification and compilation.

The first neighbour of a conditional child was denied by 'access to'v'
The contract had transformed the alternative
"Unchanged field" in active lending of the same field. The marker described above
corrects this undue refusal. The test exercises both branches and retains the refusal
direct access to the parameter of the new target.

<a id="mutations-et-amélioration-de-loracle"></a>

## Oracle mutations and improvement

The first campaign detects four mutations and allows one to survive:
the removal of the C blind. The test then borrowed the field and wrote
21 and then observed by the same field.
even when the field still referred to the old allocation.

The test now reads both allowances after the wearer has been destroyed.
The correct neighbor produces `21, 21, 7, 21`, while the deleted store modifies
the old target. The oracle is thus reinforced by the identity of the allocations;
the compiler has not been changed for this test defect.
Initial and final campaigns are kept separately.

The five mutations aim to forget the target reservation, the store C,
confusion between unchanged field and active loan, permission of readings
on a reserved target and loss of capacity of the reborrowed field.
These targeted mutations do not represent a general detection rate.

<a id="exécutions"></a>

## Implementation

Journaux `validation/mutable-field-completion-*.log`.
The first selection was successful in eight methods in 7,871 s (`-initial`).
After correction of the conditional neighbour, nine methods are changed to O0 in
8,617 s (`-final-o0`) A selection of 58 methods is selected in 29.031 s
(`-final-o2`) ; it includes the results borrowed, the factories and the
Async field contracts. Return of child reborrowing, then added,
passes separately in 0.525 seconds (`-child-result`).

The final passages of the module include the enhanced oracle of identity:

```
PYTHONPATH=tests python3 -m unittest test_mutable_field_completion -v
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_mutable_field_completion -v
```

The ten methods go from 14.451 s to O0 (`-complete-o0`) and 13.963 s at O2
(`-complete-o2`The final campaign of five mutations detects all of them.
(`-final-mutations`) ; the initial log keeps the surviving mutation.
The Python compilation of the module and new tests succeeds. No change in compiler
after the initial alternative marker has been added.

The final regression passed 56 methods in 57.734 s (`-reference-regression`) :

```
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_async_field_reference_returns test_async_field_reborrows test_stored_field_reborrows test_async_child_field_effects test_public_borrowed_handles -v
```

Accounts are methods, sometimes made up of families of programmes;
selections overlap.

C native C11/pthreads, blocking warnings, fatal UBSan and O0/O2 levels.
The patches from the beginning of the lot are kept in
`validation/mutable-field-completion-*.py.patch`.

## Limites

The carriers remain injected and the fields are Int.
general inline targets, more complex aggregate paths, some origins
reference data from other fields and blinds on loop covers
reservations are conservative; the result and
field conditions are not fully correlated with the success of the launch.
The old targets can therefore remain reserved longer than necessary.

The model is finished and the scenarios do not prove all the scheduling.
No general evidence of safety, new ASan/TSan evidence or comparison
The overall objective remains open.
