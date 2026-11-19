[Français](FACTORY_OWNED_EFFECTS_CYCLE-fr.md)

<a id="remplacements-propriétaires-dans-les-contrats-des-fabriques"></a>

# Owner replacements in factory contracts

<a id="périmètre-et-règles"></a>

## Perimeter and rules

Continue `FACTORY_SUSPENSION_CONTRACTS_CYCLE.md`. The AS3–AS5, AS14 rules,
AS16, SL1 and existing pool replacement and duration rules
also apply when a task created by a synchronous function replaces
field A<T>. No new semantics or normative changes.

The case retained in `validation/open-factory-owned-suspension.crust` reprend
the replacement already tested for direct async calls: value 7 at the start,
9 before yield allowance, 11 after take-over allowance.
Select must keep 9 and its pool; normal termination retains 11.

<a id="implémentation"></a>

## Implementation

Contracts distinguish between replacements at termination and at points of
The task values keep the carrier, the field path,
the possible sources of the new object and its borrowings contained.
The effects do not affect the results of the analysis.
are not executed when creating an inactive instance.

The analysis applies the replacements before the reference updates of the
fields. The effects of a join retain the alternative without execution in case of
LaunchFailed; direct waiting for an inactive task applies its termination.
Select summaries use suspended replacements of losers.
The auditor and the preparation of effects for the generated C receive the
same source information since the contract.

The first passage revealed a related defect: an injected pool transmitted by
another factory was described as a local target. Remapping retains
now its source parameter identity. The permutation of arguments
also re-applies the borrowings contained in a new allocation.

<a id="cas-exécutés"></a>

## Cases implemented

Six methods in `tests/test_factory_owned_effects.py` :

- Factory and relay contracts examined without synchronous bodies; pool
  separate intermediate from the final pool.
- Normal Join and Injected Launch Failure; Unique Destruction of the Old
  element and re-use of slots after cleaning.
- Await via relayed factory, interchanged parameters and task transfer.
  Drop an inactive instance after yield without replacing its field.
- Select loser, relay and directly from a factory.
- Pool intermediate short admitted after normal termination; pool final too
  short refused, waited and in join.
- &Int-Containing Descendant, manufactures with permuted parameters: read after
  Select, drop the target refused before reading, re-use after cleaning.

Targeted passage includes eight native executions and three invalid programmes
The values and traces expected
are written in the tests, regardless of the calculated contracts.

<a id="résultats-exécutés"></a>

## Implemented

- Targeted O0: six methods, 3,579 s, process completed with code 0; journal
  `validation/factory-owned-effects-o0-third.log`.
- Related O2: 117 methods, 80.867 s, process completed with code 0; journal
  `validation/factory-owned-effects-regression-o2.log`. It includes the six
  methods targeted at the final implementation.

Native executions use Clang C11, pthread, treated warnings
and UBSan without recovery. No test jumped in those passages.
This is not the whole project.

## Limites

This lot has A<Int> and A<Leaf> containing &Int. It does not demonstrate the graphs
recursive, all enum variants or all combinations of mutations.
Unions of origin and launch effects remain conservative.
The prefixes of tasks already launched remain distinct from those of tasks
Inactive arbitrations/mutex constructors
and capture of a launched handle are not modified.

No new or in-depth adversarial research campaign.
Models present in the linked suites are replayed, without claiming a
new independent model or general proof of safety.

<a id="reproduction-et-artefacts"></a>

## Reproduction and artifacts

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_factory_owned_effects
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_factory_owned_effects test_factory_suspension_contracts test_async_result_factories test_async_owned_field_writes test_async_owned_borrow_writes test_async_replaced_borrow_results test_async_mutable_descendant_results test_suspension_effects test_select_source test_async_structure_effects
```

Snapshot : `/tmp/crust-before-factory-owned-effects/`. Differences in
`results.py`, `async_structure_effects.py`, `async_lowering.py` and `crust.py`
are archived in `validation/factory-owned-effects-*.py.patch`.
The initial newspapers keep the refusal of the relayed pools.
passage also detected a test link re-declared in the same scope;
it is renamed without change of the expected effects.
