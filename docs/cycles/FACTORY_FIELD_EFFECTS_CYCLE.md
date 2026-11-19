[Français](FACTORY_FIELD_EFFECTS_CYCLE-fr.md)

<a id="effets-différés-des-fabriques-synchrones"></a>

# Delayed effects of synchronous plants

<a id="règles-et-portée"></a>

## Rules and scope

This batch connects AS2, AS5, AS12–AS16, B4/B5 and ST10/ST13. It does not change
No normative rule. A synchronous function can create and then return
an inactive task or its launched handle, whose body replaces a field
shared `&Int` of an injected carrier. The contract retains this amendment
without applying it to creation. Relays, waiting in a helper and
Handle factories called from an async or native state are connected.

`FunctionResult.task_field_updates` describes the relatively delayed fields
the factory parameters. Targets are saved at creation,
then substituted the arguments for each relay.
The holders of these changes also retain.
The contract distinguishes these fields from the other fields.
immediate changes `structure_fields` and the handles received in parameters.

An opaque call intrenches this information without re-tracing a synchronous body.
The call bridge from a state also transmits the effects to the handle descriptor.
The wait publishes the new dependencies; a failure to launch keeps
The initial state is possible. Destroying an inactive task does not apply any blinds.
Sync contracts and async termination effects are recalculated up to
stability before emission, since factories and waiting helpers
can intervene in both directions.

<a id="recherche-de-contre-exemples"></a>

## Search for Counter-Examples

Thirteen methods in `tests/test_factory_field_effects.py` couvrent :

- new task started, relay with arguments swapping, opaque expectation;
- new task expected in the helper who created it, then external reading;
- Inactive manufacture destroyed or launched, re-use of data pool slot;
- conditional choice of two targets, transfer by loop result;
- calling private all synchronous bodies, having only contracts;
- too short scope target, historical reset and then re-use after destruction;
- Manufacture called from an async state, suspension, success and failure of the child launch;
- reference from a field saved before replacing this field;
- mutable target retained by the field after the end of the child, mutation refused;
- alternatives combined and expected in one helper;
- helper waits from a native thread, and resets in the helper after waiting;
- model independent of eight cases: inactive/expected, live/destructive,
  5 programs implemented, 3 rejected in the
  two verification and compilation entries.

The abolition of the general refusal of factories also requires the connection of the
Async bridge: its former descriptor always made a list of effects empty.
The mutation test of this list now detects undue acceptance
a mutation of the new target while the carrier the reference.
No safety-related programs were implemented for the
cause indefinite behaviour.

The old test imposing the general refusal of a factory is replaced by
The following are the main reasons for the delay in the application of the Act:
maintained by new life tests and opaque call.

<a id="exécutions"></a>

## Implementation

The newspapers are in `validation/factory-field-effects-*.log`.
The first targeted selection succeeded seven methods in 7,429 s, then
the extended selection nine in 10,090 s and eleven in 12,112 s, at O0.

The first regression selection (`-regression-initial.log`) ends with
60 methods, two failures corresponding to the general refusal now obsolete,
and a command error: the requested module `test_async_completion_results`
This journal is kept; it is not a successful regression.

Final passes executed:

- `PYTHONPATH=tests python3 -m unittest test_factory_field_effects -v` :
  13 methods, 13.282 s, OK (`-final-o0.log`).
- `CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_factory_field_effects test_async_field_application test_sync_handle_field_effects test_async_child_field_effects test_async_structure_effects test_captured_cell_descriptors -v` :
  83 methods, 80.447 s, OK (`-complete-o2.log`) This selection precedes
  the addition of the last two methods of this lot; these also pass
  separately at O2 in 0.606 s and 0.917 s (`-native-final-o2.log`,
  `-direct-final-o2.log`) No change in the compiler between these passes.
- `CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_public_handle_contracts test_concrete_handle_relays test_sync_handle_bridges test_modular_calls -v` :
  77 methods, 72.588 s, OK (`-contract-regression.log`).
- Compilation of modified modules and new tests: successful.
  Differences since the start of the batch are kept in
  `validation/factory-field-effects-*.py.patch`.

These numbers include methods, sometimes composed of several programs.
Selections are overlapping and are not a total of separate programs.
Native programs are compiled in C11/pthreads, with warnings
Blockers and fatal UBSan. O0/O2 levels are explained in the newspapers.
The eight targeted mutations of the `tests/run_factory_field_mutations.py` are
detected: loss of contract returned, its composition, waiting effects,
of opaque instantization, native bridge, initial alternative,
direct waiting or recalculation until stability. The last mutation
causes an undue refusal of a valid program; others seek out the
The final log: `-final-mutations.log`.
This is not a general defect detection rate.

## Limites

Supported carriers and targets remain those of field replacements
Injected shared. Mutable fields, borrowed results of tasks
modifiers, general inline sources and writings on graphs of aggregates
The async bodies cannot be used as a means of reducing the risk of the disease.
not yet receive all the handle settings or all the signatures
Synchronous correlation. The exact correlation success/failure and the recurrences of blinds
through loop covers remain open.

The effects conservatively bring together the possibilities.
their models and UBSan do not prove general safety or all the
ordonnancements concurrents. Aucune nouvelle preuve ASan/TSan ou comparaison
The overall objective is not yet complete.
