[Français](ASYNC_ENUM_SUSPENSION_FIELDS_CYCLE-fr.md)

<a id="références-des-descendants-denums-aux-suspensions"></a>

# References of enum descendants to suspensions

<a id="raccordement-des-règles-existantes"></a>

## Connection of existing rules

This lot applies AS16 and SL1 to reference entries in a descendant
owned by enum: the suspension contract describes the entries already made,
independent of the result at the end. A loser of Select keeps
the writing done before his last yield; a finished task exposes
The rules of the rules do not change.

The analysis did not distinguish a reference change in a descendant
She compared the whole symbolic graph,
including the stored references, and rejected the suspension summary.
comparison now concerns the identity of the possessed storage; the scriptures
The reference methods use the flattened paths already produced by the common analysis.
Replacements of allowances without full representation remain reported
comme incomplets.

Backend now interprets prefixes `Variante.champ` to implement
The common analysis also retains the identity of the
local enum, its storage owner and graph when borrowed
mutablement, comme elle le faisait pour les structures. Cela raccorde les
effects of expected children and select branches on their actual bearer.

## Validation fonctionnelle

The target pass passes five methods to O0 in 1,127 s, code 0: the four methods
of the `tests/test_async_enum_suspension_fields.py` and the case already recorded in
`test_async_enum_match`. Two programmes are implemented natively, one programme
with premature drop is refused to both entries.
separately check suspension, termination, several yield and relays per wave.
Journal : `validation/async-enum-suspension-fields-third-o0.log`.

Historical case no longer demands incomplete status: it now demands
the exact path `Item.inner/.view` to the target parameter in the contract of
The former transfer point, which removed the conservative refusal,
has been removed from the historic campaign: it no longer corresponds to the property
No mutation campaign is carried out in this batch, according to
to the user priority.

The O2 regression passes 127 methods in 78,562 s, process completed with code 0.
It covers shared/mutable/consumer matches, suspension effects,
the structural effects, Select and contractual updates of descendants.
Journal : `validation/async-enum-suspension-fields-regression-o2.log`.
Native executions use Clang C11, pthread and UBSan without recovery.

<a id="limites-et-traces"></a>

## Limits and traces

The first two passages identified the uninterpreted enum path in
the backend, then the identity of the local holder lost in the analysis of the contracts.
Their diagnosis is kept in the newspapers `first-o0` and `second-o0`.
The reading aid of the test was also rewritten with a back in the arm,
already supported form: the result form of synchronous match included
a separate restriction. Direct field reading in this form is
now connected by [the next batch](SHARED_MATCH_FIELD_READS_CYCLE.md).
Other restrictions on appeals are not declared resolved here.

The coverage relates to Int references of a graph whose allowances
The replacement of the allowance of a descendant during the period of
suspension, recursive graphs and unrepresented carriers are not
This is not a general security audit.
The replacements without contained borrowings are now connected by the
[lot of fields possessed](ASYNC_OWNED_FIELD_WRITES_CYCLE.md), with its own limits.
The independent audit provided by the user shall not be deemed to be carried out.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_async_enum_suspension_fields test_async_enum_match.AsyncEnumMatchTests.test_changed_owned_graph_is_not_an_empty_suspension_contract -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_enum_suspension_fields test_async_enum_match test_async_consuming_enum_match test_suspension_effects test_async_structure_effects test_select_source test_nested_field_wrappers test_nested_field_choices -v
```

Snapshot : `/tmp/crust-before-async-enum-suspension-fields/`.
The patches of the three modules are archived in
`validation/async-enum-suspension-fields-*.py.patch`.
