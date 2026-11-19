[Français](FACTORY_SUSPENSION_CONTRACTS_CYCLE-fr.md)

<a id="préfixes-de-suspension-des-fabriques-synchrones-de-tâches"></a>

# Prefixes for suspension of synchronous task factories

Follow-up: the owner-in-house replacements mentioned as incomplete below
are connected for the forms tested in
[FACTORY_OWNED_EFFECTS_CYCLE.md](FACTORY_OWNED_EFFECTS_CYCLE.md).

<a id="périmètre"></a>

## Perimeter

AS3–AS5, AS14, AS16 and SL1 apply to a task returned by a function
The contract retains the effects visible to the suspensions separately
and those of its normal termination. Create or destroy an inactive instance
No normative rules are changed.

The programme recorded in
`validation/open-factory-suspended-field.crust` was refused with diagnosis
"Suspension effects of Select branch not connected". The child task writes
a new reference, suspends, then restores the old one at its termination.
When it loses in Select during its suspension, the restoration does not take place.
The program must therefore display `99`, `9`, then `1`.

<a id="implémentation"></a>

## Implementation

The contracts of the factories and the symbolic values of the tasks retain
the targets of the suspended entries and the possibility of suspension.
An unknown summary remains distinct from a known empty summary.
targets on actual parameters, including after permutation, relays and
transfer of a task already built.

The choices between tasks bring together the possible targets of the same field:
they are not treated as successive scriptures, of which only the last
The analysis of the async calls applies these prefixes to the waiting,
separately from termination effects. Select also accepts an instance
from a factory when its effects are represented.

Symbolic analysis uses published synchronous contracts with bodies
The test explicitly controls this boundary and the content of the
suspension and termination summaries. Generation C and execution
use existing recovery and cleaning mechanisms.

<a id="cas-ciblés"></a>

## Targeted cases

`tests/test_factory_suspension_contracts.py` contains five methods:

- Saved: suspended writing retained after cleaning Select;
  drop of target before reading refused to both compiler entries.
- Normal termination: restoration of the old target; destruction of the
  new target allowed, destruction of old rejected before reading.
  Creation followed by yield and inactive drop: no body writing.
- Relayed factory, interchanged parameters and transfer by an auxiliary.
- Manufactured directly in Select, spreading its effect to the appellant.
- Choice of catches in the factory and the caller async; both
  branches are running and the two possible targets remain protected.

Each targeted passage includes nine native executions and six rejected programmes
via `verify_program` and `compile_source`, i.e. 12 refusal checks.

<a id="résultats-exécutés"></a>

## Implemented

The target O0 passage ends with code 0: five methods in 5.375 s,
journal `validation/factory-suspension-contracts-o0.log`.
The O2 regression ends with code 0: 97 methods in 66,366 s, including
the five methods targeted on the same final implementation; journal
`validation/factory-suspension-contracts-regression-o2.log`.
Native performances use Clang C11, pthread and UBSan with
`-fno-sanitize-recover=all` ; compilation and execution errors make
No test is jumped in these two passages.

## Limites

This lot covers the fields borrowed Int represented in the contracts.
factories whose prefixes replace owned allowances remain
incomplete in this representation; they do not publish a false summary
empty. Competitor prefixes of tasks already launched are not connected
by this lot. The catches of the handle remain subject to open arbitration.

The contract `may_suspend` does not describe the exact order of the first yield by
The analysis of Select can therefore also be used to maintain the
the restored alternative, even when the tested execution selects the branch
This approximation retains the necessary protections.

The first passages of the new tests contained a text extraction
incorrect and an incompatibility between Bool/pool ratings in the
Synchronous and async parameters. The conditional test uses the Int selector
already supported; the Bool/Bool harmonisation is not corrected by this lot.
A contract check also required greater precision than the `may_suspend` ;
it has been corrected to check the two preserved origins, without modifying the
native values expected or to withdraw refusal checks.

No new adversary campaign or changes.
present in the linked suites are replayed; no new independent model
These executions are not a general proof of security.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_factory_suspension_contracts
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_factory_suspension_contracts test_suspension_effects test_async_result_factories test_select_source test_async_structure_effects test_async_owned_field_writes test_async_mutable_descendant_results
```

Snapshot avant modification : `/tmp/crust-before-factory-suspension-contracts/`.
Differences retained in
`validation/factory-suspension-contracts-{results,async_structure_effects}.py.patch`.
Intermediate newspapers are kept separately from the final passages.
