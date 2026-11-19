[Français](ASYNC_OWNED_ENUMS_CYCLE-fr.md)

<a id="enums-alloués--captures-retours-async-et-pools-par-bras"></a>

# Enums allocated: catches, async returns and pools per arm

<a id="périmètre-et-règles"></a>

## Perimeter and rules

This lot applies AS2, AS8–AS15, SL1, contracts of origin, transfers
The distinction between local T and T<T> does not change any rule
The counter-example `validation/open-async-owned-enum.crust`refused
before this lot but admitted in its synchronous pendant, is now executed.

The forms covered are allocated enums whose arms contain Int,
&Int, &mut Int and the descendants supported by the analysis of
A pool keeps a source and a layout per arm. Transfer
the enum retains its allowance; the return restores its possible arm, its
A synchronous auxiliary may borrow or receive this loan.
public handlers keep type A, Enum.

<a id="défauts-rencontrés-et-corrections"></a>

## Deficiencies encountered and corrections

- Classifications of catches, results and public signatures shall not
  The structure was recognized as the structure, and now includes the enums
  The local pools async build each source of arms
  with its size, offsets and field categories.
- The bridge to a synchronous auxiliary handled some enum references
  as table references. It now rebuilds metadata
  fields only when the corresponding arm is active at execution.
- The roads used retain their prefix of arms.
  fields also accept explicit reborrowing `&*n`, with verification of
  The borrowing of temporary workers is still refused: too much cancellation
  The historical test of the syntactic filter had inadvertently admitted them.
  `test_reference_field_requires_explicit_named_int_borrow` detected this
  Regression, corrected by allowing only the additional named reborrowing.
- The results of the tasks were losing the possible variants.
  now passes through captures, transfers, branches, relays and joins.
  unknown alternative cannot be eliminated by a known alternative.
  A contract field is not known if its arm is proven
  impossible; lack of information is not proof of impossibility.
- Regression of opaque contracts revealed an outdated register of types
  when the client installed his statements without any function body.
  Indexing resynchronises the register of public descriptors.
  Always check that the async bodies and definitions are missing.

<a id="preuves-ciblées-exécutées"></a>

## Targeted evidence executed

`tests/test_async_owned_enums.py` passed 12 methods to O0 in 17,243 s :
24 native executions, 14 invalid programmes and 28 refusal checks.
Journal : `validation/async-owned-enum-final-instrumented-count-o0.log`.
Check_program and compile_source controls share components and
not constitute two independent auditors.

The cases allowed cover: direct, spawn/join, factories and relays, several
arms, a vacuum, shared and mutable fields, descendants possessed, creations
from an injected pool, inactive destruction, failure to launch and re-use.
Refusals shall include, in particular, implicit transfers, use after transfer,
premature drop, too short pools, missing fields and confusion
between local result and pool allocation.

An independent model crosses zero or a suspension for each of the two
Select branches: four combinations. He calculates the first Ready according to
The execution compares the order of the poll, without consulting the compiler.
the single destruction of both catches and the re-use of
two sources of arms after cleaning. These four cases are included in the accounts.

<a id="mutations-et-limite-révélée-par-loracle"></a>

## Mutations and limit revealed by the oracle

The final campaign increased its baseline from 12 methods to O2 in 21,092 s and
detects five mutations by assertions: wrong number of arms at creation,
reading inactive arms, loss of variants to join, loss of public variants
and omission of the paths taken from the enum.
`validation/async-owned-enum-gate-mutations-o2.log` process completed with
code 0, internal failures of the expected mutated compilers.

The reading mutation of an inactive arm survived in the second campaign
(`async-owned-enum-second-mutations-o2.log`) A correct output and UBSan does not
were not enough: unnecessary reading could remain in a mapped page or
The test of the bridge thus instruments the C for the
require that each reference reading designate an active layout field and
This control causes observable failure before memcpy.
It does not change the runtime delivered and does not deduct the winner from it.
It depends however on the layout metadata produced by the implementation;
This is not independent evidence of the correction of these metadata.

<a id="régressions"></a>

## Regressions

The first regression of 200 methods ended with a failure and an error
211.375 s: field of an arm impossible in a public handle and register
expired of the opaque customer. `async-owned-enum-regression-o2.log`.
These two defects have been corrected; the targeted tests pass, including the opaque case
in 0.014 seconds (`async-owned-enum-opaque-contract-fix.log`).
The first synchronous regression passes 234 of the 235 methods; the method
The remaining part of the loan is detected in 96,842 s.
Journal : `async-owned-enum-sync-regression-o2.log`. Synchronous regression
final passes the 235 methods in 113,717 s, with code 0, in
`async-owned-enum-final-sync-regression-o2.log`.
Intermediate async regression passes 200 methods in 230.667 s
(`async-owned-enum-final-regression-o2.log`, code 0), before the last
Syntactic restriction of fields. Its new execution on sources
The finals also pass the 200 methods in 199.338 seconds, with code 0:
`async-owned-enum-gate-regression-o2.log`.
All final processes are complete. This lot is closed for its perimeter
It does not close the global project.

After the refusal of temporary loans was reinstated, the 12 targeted methods
in 19.996 s (`async-owned-enum-final-gate-o0.log`).
The previous marketing year at O2, before this last syntactic restriction,
had already detected the five errors (`async-owned-enum-final-mutations-o2.log`,
The final campaign detects them again.

Targeted executions use clang C11, pthread, O0/O2, warnings
No new results are claimed.

<a id="traces-intermédiaires-et-limites"></a>

## Intermediate tracks and limits

The newspapers `async-owned-enum-first-o0.log`, `second-o0.log`, `third-o0.log`
maintain intermediate failures in classification, diagnosis, paths and
The suites enriched with ten and then twelve methods pass in
`fourth-o0.log` and `fifth-o0.log`, before the second arm is added using the
public handle test. This addition revealed the defect retained in
`async-owned-enum-count-o0.log`. The first campaign of mutations stops
on this failing baseline: it is not counted as an executed campaign.

This lot does not yet cover the direct match of a user enum in the
Async body, its local construction without pool, recursive graphs or all
The interlocking compositions of variants. Display tests in the bodies
Async passes through a synchronous auxiliary. Accuracy of progeny variants
None of these refusals become a normative rule.
Minimum case `validation/open-async-enum-match.crust` confirms this difference:
both entries refuse `match_expr` in the async body, while they
accept its synchronous pendant (`validation/open-async-enum-match.log`).
Reset remains removed from the public API; possible historical cases of the
synchronous regression explicitly use the compatibility profile.

The overall construction site remains incomplete: other compositions async, guards of
The type and the
public signatures of the scheduler remain explicitly to be arbitrated.

<a id="reproduction-et-archive"></a>

## Reproduction and archive

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_owned_enums -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 tests/run_async_owned_enum_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_owned_enums test_select_result_storage test_select_source test_select_results test_public_structure_handles test_task_result_storage test_async_owned_struct_captures test_async_owned_struct_returns test_async_struct_pools test_async_borrowed_struct_pools test_async_borrowed_local_results test_async_local_owned_result_graphs test_async_execution_arguments test_sync_task_arguments -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_crust test_reference_fields test_mutable_reference_fields test_owned_results test_mutable_match_function_return test_direct_borrow_returns -v
```

The six Python diffs are archived in `validation/async-owned-enum-*.py.patch`
since snapshot `/tmp/crust-before-async-owned-enum/`. User instructions
display of the checklist at each step is kept in AGENTS.md.
