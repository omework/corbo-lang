[Français](ASYNC_STRUCT_CAPTURES_CYCLE-fr.md)

<a id="cycle--références-de-structures-dans-les-états-async-et-natifs"></a>

# Cycle — Reference structures in async and native states

The [regional cycle] continued](ASYNC_REGIONS_CYCLE.md).
No normative changes. References: ST5/ST7/ST9, ME2/ME3, TF1–TF5,
B1/B2/B4/B4a, AS2/AS8–AS15, RT8 and MT1/MT2/MT3; drafts 04/05/06.
The overall objective and other obligations of the seven drafts remain open.

<a id="implémentation-et-portée"></a>

## Implementation and scope

Catches `&Point` and `&mut Point` are connected when the structure
contains only Int fields, possibly interlocked by value.
The state keeps a pointer to the existing location; it does not copy or
Moves the structure. The flattened layout is provided by the main auditor.
Field readings and scripts keep their offsets and type.
Writing requires mutable capacity; structure is not treated
implicitly as an Int by de-reference or `set`.

The named references and their re-borrowings are relayed between tasks.
can survive the block of its intermediate link while keeping the loan
The argument of a call reserves the bearer during the
the preparation of the following. The last use releases local loans,
but still active catch keeps them until waiting or dropping
d − an inactive task.

Synchronous helpers can receive these references and return directly
a borrowed parameter. Their bridge uses the existing Cell representation and
The methods named are statically resolved since the time of the synchronous verifier.
the type of receiver; their contracts remain those of the underlying functions.
The feature case Read → Item.read is thus executable without dispatch runtime.

The inference of native blocks recognizes the construction of structures, their
fields and signatures of their methods; it does not replace verification
no change in the C memory runtime.

<a id="contre-exemples-et-corrections"></a>

## Counter-examples and corrections

The [historical direct case]](../../validation/open-async-struct-reference.crb) and
[cas type feature](../../validation/open-feature-async-structure.crb) affichent 7.
The [C generated]](../../validation/async-struct-capture-basic.c) and one
[track executed](../../validation/async-struct-capture-artifact.log) are retained.
The old refusal newspapers remain historic.

The first targeted passage has two errors.
nested used a literal child that the current manufacturer takes
She now uses established defects and then write-ups.
fields before capture; the expected values and offsets are unchanged.
The second failure reveals the absence of inference of the type of structural loan
This inference has been connected, as well as the inference of the fields.

The rejected variants cover access of the parent before launching and during
execution, two exclusive catches, one writing during a shared loan,
a leak from the target's scope, incompatible nominal types,
read-only mutations and the arguments that are prepared that overlap.

Reusing a Point slot after drop retains the expected identity.
Traces require a single destruction of each structure, including
after an injected launch failure. The task that borrows the structure does not
The caller will return to his access after waiting.
shared from a mutable reference keeps the suspension of this
reference until waiting, or until the child is still inactive.

<a id="preuves-exécutées"></a>

## Evidence

Clang C11 pthread, warnings bloquants, UBSan fatal, O0/O2. Aucun nouveau
ASan/TSan result, second compiler or formal proof.

| Passage | Result | Journal |
| --- | --- | --- |
| Initial O0 | Ten methods, 2.945 s, two errors examined | [Initial](../../validation/async-struct-captures-initial-o0.log) |
| Scope O0 | Ten methods, 4.006 seconds, OK | [Extended]](../../validation/async-struct-captures-extended-o0.log) |
| Targeted O0 | Thirteen methods, 4,435 seconds, OK | [O0](../../validation/async-struct-captures-final-o0.log) |
| Supplementary destruction O0 | Two methods, 1,750 seconds, OK | [Nettoyage](../../validation/async-struct-captures-cleanup-o0.log) |
| Targeted O2 before last shared reborrowing | Thirteen methods, 8.087 s, OK; 13 C executions and 27 refusals | [O2 intermediate](../../validation/async-struct-captures-final-o2.log) |
| Shared reborrowing supplement O0 | One method, 0.678 seconds, OK | [Reborrowing](../../validation/async-struct-captures-shared-reborrow-o0.log) |
| Final target O2 | Fourteen methods, 5,952 s, OK; 15 C executions, including one rejected launch injected, and 29 static refusals | [Final](../../validation/async-struct-captures-complete-o2.log) |
| Model O0/O2 | 16 combinations, 11 executions and five refusals; 8,651 s / 8,607 s, OK | [O0](../../validation/async-struct-captures-model-o0.log), [O2](../../validation/async-struct-captures-model-o2.log) |
| Mutations O2 | Baseline 13 methods/6,776 s, OK; six detected errors, before additional destruction claims | [Mutations](../../validation/async-struct-captures-mutations-o2.log) |
| Features and references O2 | 76 methods, 62,071 s, OK | [Contrats](../../validation/async-struct-captures-contracts-o2.log) |
| Native regression O2 | 231 methods, 180,102 s, OK; before the additional destruction assertions and the last shared reborrow test | [Regression](../../validation/async-struct-captures-native-o2.log) |

The independent model lists a shared/exclusive loan, before/after waiting,
and an empty action/read/write/drop. He decides to admit by his table
It does not consult or consult with any of the parties.
the inferred contracts or compiler states. This finished model does not cover
Not the reference field dependencies.

The six mutations remove or corrupt the offset of a field, its writing,
the mutable control, the control of the writing loan, the root loan of a
child and refusal to assimilate a structure to an Int. Unchanged tests
detect each fault; no general rate is extrapolated.

Diffs preserved: [lowering](../../validation/async-struct-capture-async_lowering.patch),
[verifier and bridges](../../validation/async-struct-capture-crust.patch),
[native inference](../../validation/async-struct-capture-native_threads.patch).

Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_struct_captures test_async_struct_capture_model -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_struct_capture_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_struct_capture_model -v
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_type_features test_type_features test_builtin_features test_async_local_references test_async_match_references test_async_loop_references -v
```

<a id="écarts-restants"></a>

## Remaining differences

Structures containing references or proprietary fields, their
value capture/transfer, construction in a state and projections
The lot does not claim to be used from their fields.
the cover of ST6/ST8/ST10–ST15 in async. General signatures, Select,
The public scheduler and guards also remain open.

Next case is kept: a task reads the field `&Int` a borrowed View,
The target and pool were durable at the appellant's.
lowering : [programme](../../validation/open-async-struct-reference-field.crb),
[diagnostic](../../validation/open-async-struct-reference-field.log). Aucune nouvelle
rule n is necessary for this case; it requires connection of dependencies
The specification already provides for internal controls.

This refusal is now historic: see the
[Reference field cycle](ASYNC_STRUCT_REFERENCE_FIELDS_CYCLE.md) for
its connection, the defects found and the limits that remain.
