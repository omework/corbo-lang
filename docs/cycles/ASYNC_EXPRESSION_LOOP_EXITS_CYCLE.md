[Français](ASYNC_EXPRESSION_LOOP_EXITS_CYCLE-fr.md)

<a id="cycle--sorties-de-boucle-depuis-les-expressions-async"></a>

# Cycle — loop outputs from async expressions

<a id="règles-et-changement"></a>

## Rules and change

This cycle applies S4/S5/S5a, B1/B2/B3/B5, D1, AS8/AS10/AS11/AS12 and RT5/RT6.
Normative rules do not change. AGENTS.md, VALIDATION_GUIDELINES.md,
The seven drafts index and flow control clauses were read.
IF_EXPRESSIONS.md specifies that only branches that join a receiver
The previous cycle was a step forward.
The other draft obligations remain open.

A swing arm that performs break or continuous does not have to produce a
value for the expression interrupted. The check for the missing value is
now after analysis of the arm. A branch that continues worthless
The if/blocks with all routes leaving are rejected.
process as flow control, without producing an intermediate result.
The block region metadata is stored during this transformation.

L-analysis of the borrowed loop results also visits the expressions of the
initializations, assignments, arguments and output operations.
their lexical connections to find the provenances.
introduce their own break target: their exits are not confused
with those of the outer loop.

The continuing expressions keep their usual type and mode.
use the same life-time checks, reservations and cleanings
the other break/continue. Runtime has not been changed.

<a id="contre-exemples-et-défauts-de-développement"></a>

## Counter-examples and development defects

`validation/open-async-loop-break-in-initializer.crust`, valide mais auparavant
refused, is now accepted and executed: output 42, 20, 77.
`validation/async-loop-nested-expression-provenance.crust` tries to write in
a before using the mutable result. It is refused by the control
d) borrowing, not by limiting the form of expression.
The initial and corrected traces are kept.

The first extension of the course confused the lists of instructions and
Call argument lists: AttributeError on tuples. It distinguished
also insufficiently a if terminal without continuous path. These errors have
was corrected; the initial log is still available.
The import class tests were also discovered under an alias: l ́import
Now uses the module, which avoids this unintentional double run.

<a id="scénarios-et-observations"></a>

## Scenarios and observations

`tests/test_async_expression_loop_exits.py` contains eight methods:
23 native executions and 21 refusals expected in full passage.

- Break in an initialization if, a block, nested if or a match
  The two possible targets remain reserved after return.
- Continues in initialization or assignment: resume the correct one
  iteration, suspension, final counter and absence of execution of the rest of the arm.
- Internal loop that borrows b then returns its access before the loop
  external supply a; at the caller, b remains modifiable before use of a.
  This accepted neighbor checks that contracts do not arbitrarily retain
  all references encountered in the body.
- Break in the expression of a break or a return, with both paths
  execution and protection of each provenance.
- Break from Arm Ok from a game after await: spread of target of the
  result, suspension in arm, emergency branch after EAGAIN injected.
- Inactive child with an allowance in the scope left by the break:
  destruction once, no start of this child, then re-use
  the pool of capacity one after join.
- Denial of divergent types/modes, worthless break, destroyed local target,
  continuing branch with no value and recovery that would reuse a consumed task.

Expectations of exit and destruction are explicitly defined from
There is no new general independent model in this lot.
The regression includes the model of the three table indices of the previous cycle,
and the models for selecting the results borrowed.
finished coverage, without general evidence of flow control analysis.

<a id="exécutions"></a>

## Implementation

| Journal in validation/ | Result |
| --- | --- |
| async-expression-loop-exits-initial.log | Development errors described above; retained |
| async-expression-loop-exits-expanded.log | 16 methods, 14.295 s, OK: the first six new methods and the ten of the previous cycle |
| async-expression-loop-exits-operands.log | Two additional methods, 2,848 seconds, OK |
| async-expression-loop-exits-O0.log | Final module: 8 methods, 9,458 s, OK |
| async-expression-loop-exits-O2-regression.log | 89 methods, 88,707 s, OK, no jump |

The O2 regression is over. `py_compile` and local links to documents
modified have been checked. The compiler diff is kept in
`validation/async-expression-loop-exits.patch`.
Native helpers use Clang C11, pthread, -Wall/-Wextra/-Werrar and UBSan
The optimization levels are selected by CRUST_TEST_OPT.

Module and Targeted Mistake Controls:

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_async_expression_loop_exits -v
python3 tests/run_async_expression_loop_exit_mutations.py
```

The regression O2 + UBSan load test_async_expression_loop_exits,
test_async_loop_references, test_async_match_references,
test_async_local_references, test_async_reference_returns and
test_reference_expressions, then d-AsyncRuntimeTests methods including the
name contains loop, continuous, break or conditional. The log lists the names.

## Mutations

The initial campaign detected the oblivion of the initialisation and the
incorrect translation from continuous to break. Second fault triggers UBSan
on the result that was not provided before premature release.

The complete removal of the cleaning was initially classified as inconclusive
by script, because compiler refused the valid program before generation
C. The newspaper shows precisely the control of cleaning obligations
The script now recognizes this exact diagnosis.
for this fault as a separate invariant-detection of the compiler
A fourth fault only deletes the C call from the
cleaning the child, to also test the observation of the re-use of the slot.
The final campaign is over: four errors detected, one of which is
The deletion of call C causes the compiler to change.
The capacity pool one is exhausted. Traces:
`validation/async-expression-loop-exits-final-mutations.log` ; script :
`tests/run_async_expression_loop_exit_mutations.py`No overall rate of
The detection is derived from these four selected errors.

<a id="limites-et-suite"></a>

## Limitations and follow-up

`validation/open-async-diverging-initializer.crust` - The two arms are not allowed.
of its if initialization exit the loop: no intermediate receiver
must be produced, and the outer loop is well equipped with the break reference.
Diagnosis `utiliser if comme instruction quand toutes les branches retournent`
is still a lack of implementation. Support for these expressions
without continuation must be spread beyond the terminal arms only.

Suivi : [ASYNC_DIVERGING_EXPRESSIONS_CYCLE.md](ASYNC_DIVERGING_EXPRESSIONS_CYCLE.md)
processes this program and cleans arguments prepared before an output.
The above limit describes the state at the end of this cycle.

Tests do not cover all types of aggregates or positions
d-expression. Other matrix deviations, including scheduler, threads
natives, Select, mutex and implicit storage remain open. Reset remains removed.
ASan was not restarted after blocking the empty C program documented in
No evidence ASan/TSan, second compiler or proof
The overall objective is not achieved.
