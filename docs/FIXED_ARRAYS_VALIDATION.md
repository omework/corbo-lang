[Français](FIXED_ARRAYS_VALIDATION-fr.md)

<a id="validation-des-tableaux-de-taille-fixe"></a>

# Validation of fixed size tables

<a id="cycle-du-4-novembre-2026--lignes-contenant-des-références"></a>

## Cycle of 4 November 2026 — lines containing references

This cycle implements the reference lines that are themselves accessible
by stored references: e.g. `[&[&Int;2];1]` and
`[&mut [&mut Int;2];1]`, with recursive composition. It applies the rules
No normative rules have been established for the E2–E7, B1–B5, D1, V4, S4–S5 and A2/A5.
amended. `mut()` remains explicitly excluded from the prototype.

<a id="implémentation-et-traduction-en-c"></a>

### Implementation and translation into C

The auditor keeps a tree of loans: the borrowing of the line, its
the internal references, then possible descendants.
are followed by path. An internal reference still used
protects its target and reservations, even if its original variable is not
The mutable reference tables remain uncopyable.

C retains the table structures and pointers of their exact type.
The allocations are not moved. A line pointer crossing
materializes its address before the following indices and effects; none
The terminal controls precede each access.
Pools and their slot strategy don't change.

The contracts describe the internal references by road, such as `0/1`.
They keep the returned targets, the aliases of the lines, the modifications
by box and source constraints. The auditor applies these contracts
without re-tracing the bodies called. Backend C retains its specialization
The tests include a verified call with only one of the functions
his contract and a forged contract trying to change a shared line, refused.

The contracts also separate the effects on the lines injected at the entrance to the
the function of those of the outer container. These effects remain known if this
container is consumed by transfer or replaces its pointer before finishing.
This follow-up is static: it does not add retention or allowance to the runtime.

Alias, projected lines and variables masked by a declaration
local keep their connection to the original storage. Branch outputs,
the results of the loop, continuous recoveries and returns bring together the
The transfer of the internal reference sources applies D1 to all the
levels, without implicit promotion of a local container.

<a id="contre-exemples-et-corrections"></a>

### Counter-examples and corrections

- An external reference could keep its line without keeping the loans
  active loans and allowances deducted are covered
  recursively, with reservations of enum carriers.
- A branch summary could keep the line pointer and lose its
  referenced content. The junctions and instants keep the contents and
  the latest indoor uses; the loop convergence key includes them.
- An internal reference update could only change the view
  The post-conditions are spread to the original line.
- The replacement of a line reference must make the old line with
  the content and install the new one with its own targets.
  pointer to a shared line does not mean changing that line.
- The route of a line should not count as reading all its
  The tests allow the reset of a target after its
  The last access, while maintaining access to another living box.
- A returned loan must keep the reservation of the inner box
  The projection of parameters does not
  must not erase this named capacity.
- **Confirmed difference between courses:** a function returning `&mut g[1]`
  lost the line's gap in contract analysis.
  wrote in this line assigned the writing to g[0]. `verify_program`
  then accepted an invalid reset before reading g[0], while
  `compile_source` The re-applying of the
  positions through the return corrects this gap. The invalid case is now
  refused both internships and the valid case produces the expected values.

- Another counter example concerned an external table consumed after
  writing in a borrowed line, then replacing its pointer.
  summary confused the writing of the referent and the change of the pointer.
  two separate allowances in the same pool, verify_program accepted a
  drop the target still used, while compile_source refused it.
  Effects now retain initial injection lines; replace
  their pointer does not rewrite their references. The counter example is retained
  in test_transferred_outer_container_preserves_writes_to_parent_rows.
- A global pass failed on ten diagnostic sub-cases related to the
  The programmes were refused, but the iteration of a
  sometimes chose a generic constraint before the carrier's.
  The order of verification is now deterministic, with priority to the
  The existing tests have been retained.

The counter example of projection is reproduced in
`test_returned_inline_row_projection_updates_only_its_actual_slots` of the
`tests/test_nested_reference_rows.py`. Regressions from previous cycles
remain executed: order of arguments, branches, returns, transfers,
replacements of recipients, temporary loans, stability of addresses,
cleaning and re-use of slots.

<a id="preuves-dexécution"></a>

### Evidence of enforcement

The overall suite performed 909 separate tests without failure in four groups
of 229, 320, 178, 182 tests, in 247,446, 217,203, 190,072, 200,523
The total corresponds to the current discovery, with
909 identifiants uniques.

The 68 existing tests targeting tables pass without instrumentation in
12,305 seconds; the 22 new ones pass in 5,893 seconds. The 90 tests pass
also in UBSan at -O2 in 88,567 seconds, with
101 accepted invocations and 194 denied invocations of the auditor.

The diagnostic tests of reserved carriers were also replayed with
PYTHONHASHSEED=0 and PYTHONHASHSEED=1: 9 tests pass in each configuration,
In 12.397 and 12.488 seconds, these repetitions are not added to the number of
separate tests from the overall suite.

The accepted programs of the targeted suites compile the C with Homebrew Clang 20.1.3., C11 and the
warnings processed in error. They compare values and traces of
destruction. Refusals are checked with verify_program and compile_source
for new counter-examples, as well as directly from a contract
opaque for the readonly forged case. Meters are invocations of the
not unique programs; they exclude parser failures
and direct checks of opaque callers blocks.

UBSan uses -O2 and -fno-sanitize-recover=all. Sanitizer diagnostics
The test is unsuccessful. No new ASan success is claimed: the
probes from a previous cycle exceeded the time frame with Homebrew Clang and
Apple Clang, even for a limited-put independent program.

<a id="modèles-indépendants-et-mutations"></a>

### Independent models and changes

The nested destination model uses Python list indices:
24 deterministic operations with seed 20261107, including copy, replant,
swap and read. It calculates the expected values without consulting the compiler.
The drop window model lists 12 configurations: depths 1, 2 and 3,
Two liberable targets and two readable targets. It requires refusal if the target read
is freed: 6 admitted programmes are implemented and 6 are refused both courses.

Previous models remain executed: 90 transactions on values
(grain 20261104), scalar reference permutations/replacements
(grain 20261105), and 40 operations on value line references
(grain 2026106). The models of slots and historical destruction are
also present in the global suite.

The 15 controlled mutations are detected:

- 8 by undue acceptance of a prohibited program or contract;
- 6 by refusing a valid program;
- 1 by incorrect observable behaviour after access beyond limits.

They cover the boundaries, active and domestic loans, the separation of
boxes, provenances, aliases, old loans, post-conditions,
the content of contracts, latest uses, shared lines,
re-applying projections and effects after transfer.

A propagation mutation had first survived the chosen scenario: the effect
The same was true for the injection of the reference data.
mutation was replayed on the existing test that replaces the external pointer,
where this propagation is necessary. It is then detected by a false refusal
No oracle has been modified to make the continuation successful.

Substitutions, test names and diagnostics are retained in
`validation/fixed-array-current-mutations.json`. The reproducible launcher
`validation/run_fixed_array_mutations.py` works on temporary copies
and keeps the oracles unchanged. This sample of mutations chosen does not measure
Not a general detection rate.

Regression groups, meters and SHA-256 fingerprints from sources
are retained in `validation/fixed-array-current-global.json` and
`validation/fixed-array-current-suite.json`.

### Reproduction

```sh
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_fixed_arrays.py -q
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_nested_reference_rows.py -q
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
CRUST_SANITIZE=undefined CRUST_ARRAY_OPT=-O2 PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_fixed_arrays.py -q
CRUST_SANITIZE=undefined CRUST_ARRAY_OPT=-O2 PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_nested_reference_rows.py -q
python3 validation/run_fixed_array_mutations.py
```

<a id="limites-et-réexamen-des-interactions"></a>

### Limitations and Reconsideration of Interactions

The rules of intent and type (I/V), scope and control (S/T/U),
(B/D), destruction and source (L/A/P) were
The regresses are carried out in accordance with the provisions of the Directive.
together. The pool runtime retains its existing invariants and models;
This cycle modifies static tracking and C of tables, not its allocator.

Independent models do not constitute a complete oracle of the durations of the
Life: Drop model covers only its 12 configurations. Alias and
changes in contracts are carried out by selected programs.
arbitrary, all combinations of junctions, general convergence and
the completeness of refusals/admissions are not proven. The analysis remains
The extreme sizes of the backend
It is not exercised. The types and features outside prototype — traits,
FFI, competition and dynamic sizes in particular — remain outside the cycle.

These results are evidence limited to the scenarios being carried out.
constitute neither formal proof nor a general guarantee of language safety.
