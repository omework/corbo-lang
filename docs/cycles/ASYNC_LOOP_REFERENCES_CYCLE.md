[Français](ASYNC_LOOP_REFERENCES_CYCLE-fr.md)

<a id="cycle--résultats-empruntés-de-boucles-async"></a>

# Cycle — results of async loops

<a id="périmètre-et-règles"></a>

## Perimeter and rules

Application of S4/S5/S5a, B1–B5, D1, AS8/AS10/AS11/AS12 and RT5/RT6,
No change in the rules. AGENTS.md, VALIDATION_GUIDELINES.md and index
drafts were read, as well as flow control clauses,
d) borrowings and async results. Other open bonds of the matrix
The last exchange on the High setting had not done
progress the compiler; this cycle repeats the modifications present.

The initial test previously launched was completed: its journal contains
8 successful methods in 7,819 s. No replacement launch n
on the basis of a lack of message.
is forbidden in this environment; the terminal log established the end.

The programme `validation/open-async-reference-loop-result.crust` is now
compiled and executed: output 30 and then 20. The old refusal remains retained.
The break of the current loop provides pointers of the same type/mode.
The outputs of the interlocked loops belong to their own loop.
The contract brings together possible targets; the link of the result reserves their
access and parents of reborrowing until last use.
Local targets that disappear at the exit remain refused.

C keeps a result pointer in the async frame, without moving
The existing cleanings are carried out on the scopes
left by break/continue; the runtime was not changed in this lot.

<a id="contre-exemple-corrigé"></a>

## Corrected counter-example

`validation/async-loop-early-return-provenance.crust` contient :

```rust
return loop {
    yield;
    if flag == 1 { return a; }
    break &mut *b;
};
```

The contract only retained the source of the break, so b. He forgot the
early return to a in the expression of the external return.
`a = 3;` before the use of the mutable result was wrongly accepted.
is recorded in `async-loop-early-return-provenance-initial.log` ; ce
invalid program was not executed as a safe example.

The analysis now also visits the interlocked returns in the operand of a
The newspaper is back. `async-loop-early-return-provenance-fixed.log` contient :

```text
REJECTED: ligne 4: accès à 'a' incompatible avec un emprunt actif
```

Read, mutate and drop of both targets are refused before use
The two valid paths are executed, then their slots reused.

<a id="scénarios-exécutés-et-modèle"></a>

## Scenarios implemented and model

`tests/test_async_loop_references.py` has ten methods: 18 executions
The number of children who are born in the country is the same as the number of children who are born in the country.
count variants, not independent properties.

- Shared and mutable references, two outputs, several continuous and yield.
- Interlocking loops, local reborrowings that exit towards a sustainable target.
- Direct loop return and early loop return.
- Protection of both sources at the appellant and in the async framework.
- Table element chosen by index calculated, with suspension before writing.
- Cases Vector<Int/u8> obtained by wave and handle match: successful launch
  and EAGAIN failure injected, then borrowed out of loop and returned by relay.
- Denial of divergent modes/types, valueless break and local targets.
- Cleaning an inactive child with an allowance on both exits,
  after continuous destruction exactly once and reuse of pool
  one after join. Inactive child must not run his print.

The independent model of the table test selects one of the three boxes of a
list Python, replace this box with 99, then compare the three final values
The index 0, 1 and 2
all are executed; modification of the source before use is also refused.
This finished model does not prove the general correction of loop analyses.

<a id="validation-exécutée"></a>

## Validation executed

| Journal in validation/ | Result |
| --- | --- |
| async-loop-references-initial.log | 8 methods, 7,819 s, OK, before adding the counter example |
| async-loop-references-early-return-fix.log | 9 methods, 8,136 s, OK after correction of contract |
| async-loop-references-cleanup.log | Cleaning and re-use: 1 method, 0.969 s, OK |
| async-loop-references-O0.log | Final module: 10 methods, 8,501 seconds, OK |
| async-loop-references-O2-regression.log | 80 methods, 92,284 s, OK; final module, matches and links borrowed async, async returns, synchronous expressions and loop tests of runtime |

Native helpers use Clang C11, pthread, fatal UBSan and
-Wall/-Wextra/-Werrar. O0/O2 variants are explicit via CRUST_TEST_OPT.
The O2 regression does not involve any method leaps. `py_compile` I did it.
The compiler diff is kept in `validation/async-loop-references.patch`.
The initial fixture C is in `validation/async-loop-reference-result.c` :
the frame contains the injected pointers and the result pointer; each
The next yaeld keeps this
This inspection completes the executions, without any
Deduce general evidence from the generated C.

Controls of the module and the fault campaign:

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_async_loop_references -v
python3 tests/run_async_loop_reference_mutations.py
```

The regression uses CRUST_TEST_OPT=-O2, CRUST_SANITIZE=undefined and
PYTHONPATH=.:tests. It loads the five test_async_loop_references modules,
test_async_match_references, test_async_local_references,
test_async_reference_returns and test_reference_expressions, then all the
d-AsyncRuntimeTest methods whose name contains loop, continuous or break.
The journal keeps the exact names of the 80 methods executed.

## Mutations

Four errors in temporary copies, four detections, journal
`validation/async-loop-references-mutations.log` :

| Faute | Observation |
| --- | --- |
| Forget nested returns | Unacceptable access to the target of early return accepted |
| Keep only the first source of break | Incompatible access to the second accepted target |
| Clear reservations from loop result | Unacceptable access within accepted framework |
| Omit the cleaning of the telescopes | Unrefined child slot; capacity pool an exhausted |

These detections are based on the expected refusals and behaviours, not on the
Textual comparison of C. They do not measure an overall detection rate.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Another valid program remains denied:
`validation/open-async-loop-break-in-initializer.crust` contient un break
in an if used to initialize a loop variable.
initial is `branche de if async : résultat Int ou retour requis`. The shape
control is still not implemented; the variant
`validation/async-loop-nested-expression-provenance.crust` ajoute aussi un
incompatible access to seek a loss of provenance, currently hidden
by this syntactic/structural refusal. The valid neighbour will have to be executed and
verify this refusal of security after taking over the interlocked control.

Follow-up: the cycle [ASYNC_EXPRESSION_LOOP_EXITS_CYCLE.md](ASYNC_EXPRESSION_LOOP_EXITS_CYCLE.md)
supports this initialization and checks its invalid variant.
The above description therefore describes the state at the end of this cycle.

The general forms of aggregates, handles, Select, scheduler, native threads,
mutex and implicit storage remain followed in the matrix. Reset remains removed.
ASan was not restarted after the documented blocking of an empty C program.
No evidence ASan/TSan, second compiler, formal verification or security
The objective of the seven drafts remains active.
