[Français](ASYNC_REFERENCE_RETURNS_CYCLE-fr.md)

# Cycle — retours conditionnels d’emprunts async

<a id="portée-et-règles"></a>

## Scope and rules

This cycle applies B1/B2/B3/B5, D1, AS8–AS12 and RT5/RT6, without changing the
Standardised semantics. AGENTS.md, VALIDATION_GUIDELINES.md and index of the seven
drafts were read; clauses U1, B5, AS11/12 and draft 01 were read
The overall objective of the seven drafts remains to be achieved.
Other unverified capacities of the matrix are not covered
by this cycle.

The Counter-Example `validation/open-async-reference-if-expression.crust` is
corrected: `return if ...` peut rendre un &Int, &mut Int ou &mut u8 durable.
The registered program now displays 30 and 20.
refusal is kept as a historical record.

Internal expansion replaces the return of an if expression with returns
Inference of provenances and
the generation of the frame uses the same form.
The suspension points and their telescopes are kept. No target copy,
additional allowance or extension of its life is not introduced.
Every return requires regular fashion, type, durability and
The contracts retain the union of the
possible targets, regardless of the path actually chosen.

This mechanism concerns the return position. It does not claim to solve all
contexts where an expression can produce a loan.

<a id="scénarios-et-oracles"></a>

## Scenarios and oracles

`tests/test_async_reference_returns.py` has ten methods: 23 executions
natives normales et 24 vérifications de refus par passage complet. Les nombres
count the variants executed, not independent properties.

- Both arms and modes shared/mutable, with yield in arms, are
  executed; writing only reaches the target chosen.
- Else-if, early return to an arm and condition with meter: one
  calculation of the condition is observed.
- Boxes of a fixed table, new boxes of Vector<Int/u8>, were in a
  arm and local result from the other; an additional relay
  retains the source and type of element.
- The transfer of both sources of array or vector remains refused before the
  last use of the result. In the synchronous caller, read, mutation and
  destruction of each target is refused as long as the result is to be used.
- Local sources, owner received by transfer, bad fashion,
  In place of a reference and branch without result are refused.
- Cleaning a proprietary capture precedes the return of join.
  d-a single slot can be reused in the arm Ok, while borrowing
  A read but not returned catch can be destroyed.
- An inactive child task created before conditional return and with
  The allowance to be cleaned, is destroyed before the same re-use.
  The trace counts exactly a destruction of the capture.
- An independent model chooses from three integers and replaces only
  the selected value: 0/1/2 indices and two seed prints 2041.
  Three final program values are compared to this Python list.

The expected outputs and tracks are defined from these rules, without consulting
the compiler's internal decisions. The model remains complete; it does not constitute a
not a general proof of the control or d-aliasing combinations.

<a id="exécutions"></a>

## Implementation

| Trace in validation/ | Actual |
| --- | --- |
| async-reference-returns-initial.log | 8 methods, 9,448 s, OK, Clang O2 + fatal UBSan |
| async-reference-returns-cleanup-fixed.log | 1 method, 1,077 s, OK, direct cleaning and unturned capture |
| async-reference-returns-O0.log | 9 methods, 17,467 s, OK, Clang O0 + fatal UBSan |
| async-reference-returns-regression.log | 43 methods, 85,039 s, OK; the 9 initial methods, push_new, buildin errors and five adjacent async scenarios |
| async-reference-returns-child-cleanup.log | Tenth method added after the surviving mutation, 1.461 s, OK, O2 + fatal UBSan |
| async-reference-returns-child-cleanup-O0.log | This same method, 1,962 s, OK, O0 + fatal UBSan |

The first nine methods and the supplement cover together the final module
both optimizations; the above durations come from separate passages.
The helper inspection `AsyncRuntimeTests.run_c_oracle` confirme qu’il utilise
CRUST_TEST_OPT and fatal UBSan: the 43 methods of this regression
native have the O2 + UBSan configuration, unlike the helper
historical synchronous used in the previous cycle.
`py_compile` also succeeded on modified sources and scripts; links
The four modified documents were verified.

<a id="préparation-des-tests-et-mutations"></a>

## Preparation of tests and mutations

The first test of destruction of an unreturned capture attempted a drop
parent → child without transfer of entry. This program was invalid.
of the `-> ignored;` complies with the existing rule; initial and corrected traces
are kept in `async-reference-returns-cleanup*.log`. No rules n
was relaxed for the test.

Three errors are injected into temporary copies of the compiler:

| Faute | Observation |
| --- | --- |
| Switch arms when expanding | Incorrect final value in native tests, detected |
| Keep only one provenance in the contract | No access to accepted second source, detected |
| Force the cleaning path to that of an inactive task | Capture of unreleased child task, pool of an exhausted slot, detected after scenario strengthening |

The third mutation survived first: the scenario had only one
direct capture, for which cleaning of an inactive task and that of
the completed task were equivalent. The added scenario creates a child task
Inactive who receives the capture. The terminal cleaning must destroy this child,
The initial cleaning does not know the existence.
normal passes; mutant fails with `pool capacity exceeded` both
arm. L的oracle was not modified to align with the mutant.

Traces : `validation/async-reference-returns-mutations.log` (two detected,
initial survival) and `validation/async-reference-returns-cleanup-mutation.log`
(targeted detection after addition). No overall detection rate is deducted.

<a id="limites-et-contre-exemple-suivant"></a>

## Limitations and counter-example next

Local liaison of a conditional result remains refused:
`validation/open-async-local-reference-if.crust` and its log.
`let mut selected = if ...`, suspend and then return selected.
Injected and durable; refusal is not normative.
terminals do not deal with this context and analysis of local aliases should be
extended. The games producing a loan in the frames async, enums
and aggregates, as well as other N/P bonds remain open.

Reset is not reintroduced. The previous batch covers its public ban
and two controls in the historical profile; this async lot does not claim
a new reset validation.

ASan was not restarted after the boot block reproduced by an empty C
the previous cycle. New native tests use Clang C11, pthread,
-Wall/-Wextra/-Werrar, fatal UBSan. No hits ASan/TSan, second compiler,
formal proof or general security guarantee is not claimed.

## Suivi

The above-mentioned conditional local link is corrected and tested in
[ASYNC_LOCAL_REFERENCES_CYCLE.md](ASYNC_LOCAL_REFERENCES_CYCLE.md).
The game producing a loan in the async frame remains a separate gap.
