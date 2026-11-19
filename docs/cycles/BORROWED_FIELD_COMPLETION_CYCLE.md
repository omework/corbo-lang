[Français](BORROWED_FIELD_COMPLETION_CYCLE-fr.md)

<a id="modifications-de-champs-et-résultats-empruntés-à-la-terminaison"></a>

# Field changes and results borrowed from the termination

<a id="implémentation"></a>

## Implementation

This batch connects AS12/AS16, B1/B2/B4/B5 and ST10/ST13 without changing the
normative semantics. A task can replace a shared field `&Int`
then return an Int loan. The result may designate the old target,
the new target or another parameter. Synchronous calls, children
and the factories keep the two information: effects on the
The result is carried out by the user and the dependencies of the result.

The analysis of the paths of the result uses the termination contract when it
contains field changes, instead of just reading the projection
The syntactic of the return. `return v.data` after replacement means well
The synchronous join projects the snapshot of the catches before
to publish the blinds: a saved result before replacement keeps its
The fields and result do not arbitrarily retain
the same allowances.

Backend also accepts direct assignment of a shared field `&Int`
from a state: assessment and backup of the descriptor of the target, control
The loan is not a loan.
operation uses the same sustainable target restrictions as helpers.
Fields `&mut Int` The replacement remains a separate project.

Source constraints are now inferred after stabilization of the
results contracts and async effects. Provisional interfaces used
Only for this inference have no constraints (`None`), jamais
presented as verified to calls or backend.
are calculated before any body and emission verification.

<a id="contre-exemples-et-scénarios"></a>

## Counter-examples and scenarios

Eleven methods of `tests/test_borrowed_field_completion.py` verify:

- old and new separate result, destruction of the bearer and then release
  the target that is no longer retained; target of the result that is still protected;
- still alive carrier: protection of its new target even if the result
  means the old; initial alternative retained in case of failure of launch;
- direct assignment or helper, with the same exit and refusal;
- three levels of tasks with catch rotation;
- Manufacture and relay of borrowed public handle;
- independent pools, pool's historical reset became useless and reset
  the pool still referenced refused;
- mutable result independent of the shared field, exclusive use and mutation;
- mutation of a still stored target refused in the state;
- The latter case remains refused under a contract of
  non-representable termination, not a precise life-span diagnosis;
- model independent of eight cases: old/new result, carrier destroyed
  Two programs, six refused to both entrances.

The programme recorded `validation/open-async-completion-result-and-write.crust`
is now executable: `16`, `9`, `7`. His child returns the old
reference while replacing the first field; the parent stores this return
in the second field. Destroy one of the two targets before reading
The file keeps its historical name for traceability.

The first pass discovered the undue refusal of the reset of a pool that had become useless:
initial stress analysis still used field projection
pre-execution. The order of the passes described above corrects it.
and its neighbour refused are preserved.

<a id="validation-exécutée"></a>

## Validation executed

Journaux `validation/borrowed-field-completion-*.log`.
The first selection of eight methods fails on this undue refusal (`-initial`).
The corrected neighbour succeeds in 1,030 s (`-reset`) Enlargement to 11 methods
shows two fixture errors (`-expanded`) : un marqueur `BEFORE` not replaced
in a negative program and a pattern of diagnosis too narrow.
and the reason was corrected without changing the acceptance rules.

Final passes executed:

- `PYTHONPATH=tests python3 -m unittest test_borrowed_field_completion -v` :
  11 methods in 21,608 s, OK (`-final-o0.log`).
- Same command with `CRUST_TEST_OPT=-O2` : 11 methods in 21,624 s,
  OK (`-targeted-final-o2.log`).
- `CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_async_structure_effects test_factory_field_effects test_public_borrowed_handles -v` :
  48 methods in 31.410 s, OK (`-contract-final-o2.log`).

The previous combined selection of 59 methods, despite its name
`-final-o2.log`, failed on the four assertions associated with the two fixtures
The modules that composed it were all successfully re-executed
by the last two orders above. These accounts are methods,
sometimes composed of several programs; selections overlap.
The extended regression executes:

```
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_async_reference_returns test_async_local_references test_async_field_reference_returns test_async_detached_field_returns test_async_match_references test_async_loop_references test_captured_cell_descriptors -v
```

It has 85 methods in 105,922 s (`-reference-regression.log`). Aucun
change the compiler between this pass and the latest targeted passes.

Native programs are compiled in C11/pthreads, blocking warnings,
UBSan fatal, at O0/O2. The Python compilation of modules and new tests succeeds.
The patches of the lot are kept in `validation/borrowed-field-completion-*.py.patch`.

Five mutations are detected: suppression of termination sources,
projection of the result after publication of the blinds, removal of the C blind,
forgotten the loan of the stored target, premature calculation of constraints.
Some mutations cause a valid neighbour to refuse; others lose
borrowing control or produce an incorrect value. No program
potentially invalid was not executed to cause UB.

## Limites

The replaced fields are shared Int, on injected carriers and with the
Sustainable targets already represented.
the aggregate borrowed results and effects on the recovery of
The exact correlation between success/failure and the
field statements are not added. Generic constraints and results
are not fully proven by these finite cases.

No general proof of security, competition or all the
ordonnancements ; aucune nouvelle preuve ASan/TSan ni comparaison entre
Independent C compilers. The overall objective remains open.
