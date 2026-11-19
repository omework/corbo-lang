[Français](ASYNC_MATCH_REFERENCES_CYCLE-fr.md)

<a id="cycle--emprunts-produits-par-match-dans-un-cadre-async"></a>

# Cycle — Match-produced borrowings in an async framework

<a id="règles-et-changement"></a>

## Rules and change

Application of B1/B2/B3/B5, D1, F2, AS8/AS11/AS12 and RT5/RT6, unchanged
The rules of the rules of the law.
The matrix was read out in drafts, draft 04 and AS11/AS12 clauses.
Keeps the other obligations open; this cycle does not conclude the construction site.

`validation/open-async-local-reference-match.crust` is now accepted and
executed: the reference produced by a match can be linked, kept during
A suspension then turned back. It exits 30 then 20. L-old log refusal
remains a historical trace.

L-inference follows calls behind spamn/spawn_blocking, named tasks,
The projection Ok transmits the provenances
Err transmits the results of his emergency expression.
The alternatives are combined in the contract, with mode and type control.
C uses the same pointer representation as existing borrowings.

The game processing now transmits the "borrowed result" mode to the
branches of the results of handle, conversion, vector and builtin errors.
The subject remains evaluated only once, before the chosen arm.
and early return branches are subject to existing scope controls.

<a id="contre-exemple-de-sûreté-découvert-et-corrigé"></a>

## Counter-example of security discovered and corrected

The programme `validation/async-match-overlapping-result-borrows.crust` faisait
Two games on the same Result. The first provided a loan
The relief branches were also used after the creation of the second.
separate targets, so as not to mask the duplication of the path Ok.

The auditor accepted this invalid program. The original log records this
acceptance; the program was not executed as a safe example.
was followed, but the mutable capacity carried by the Named Result was not
reserved during the use of the borrowed loan.

L'borrowing derivative now also keeps its carrier Result.
incompatible projection is refused until the last use of the first loan.
The corrected check produces:

```text
REJECTED: ligne 5: accès à 'outcome' incompatible avec un emprunt actif
```

The trace is in `validation/async-match-overlapping-result-borrows-fixed.log`.
The next program that ends the first use before the second game is
Two shared projections remain accepted and executed.
This correction applies the existing exclusivity; it does not add a rule
The result is a standard of continuous consumption.

<a id="autres-défauts-corrigés"></a>

## Other corrected defects

- A match on the constant runtime::Error::LaunchFailed produced a
  comparison of the constant with itself, refused by Clang with -Werrar.
  The subject is now placed in a temporary typed before the control.
  Initial trace is `async-match-references-other-families.log`.
- The control of the borrowed return now requires an effective reference.
  Return the entire Result container instead of its content is refused
  with a diagnosis, without access to an internal field that does not exist.

<a id="scénarios-modèle-et-limites-des-attentes"></a>

## Scenarios, Models and Expectations Limits

The final module `tests/test_async_match_references.py` has thirteen methods,
36 normal native executions and 32 refusals expected by complete passage.
These numbers count the variants executed, not independent guarantees.

- Shared/mutable modes, reverse arm order, yield in arms and after
  reception, direct or local returns.
- Task named before launch, result of handle stored, or spawn directly
  in the expected subject; branch Err with early return.
- Refusal to launch injected by EAGAIN: the body of the task does not execute,
  the emergency marker appears and the emergency reference is used.
- New Vector boxes<Int/u8>, normal and launch refused, then async relays;
  growth of each source refused as long as the returned reference serves.
- Premature transfer, reading or drop of both sources refused after return;
  access, drop and re-use of slots allowed after last use.
- Conversion results and pop vector, simple buildin errors and match
  nested error that chooses external borrowings. A vector used
  only to calculate the choice can be destroyed before use of the
  borrowed result: it is not arbitrarily added to its origin.
- Denial of incompatible modes, local targets, worthless arms, match
  incomplete and container Result taken for reference.
- Double mutable projection of the same Result refused; sequential variant
  and shared projections implemented.

An independent model chooses from three integers according to two decisions:
successful launch and membership of one integer to [0.255].
combinations determine a Python list box, the value of which is
The three final values of the program are compared to this list.
Each possible source is also tested against a mutation before use.
The model does not use contracts, internal provenance, or C issued. It remains finished.

<a id="exécutions"></a>

## Implementation

| Trace in validation/ | Actual |
| --- | --- |
| async-match-references-initial.log | 8 methods, 10.988 s, OK, O2 + UBSan |
| async-match-references-expanded.log | 9 methods, 11,086 s, OK, control of the container Result added |
| async-match-references-other-families.log | A C compilation error on the runtime::Error constant, corrected then |
| async-match-references-O2-regression.log | 59 methods, 80,483 s, OK before discovery of missing bearer; this passage did not cover the counter-example discovered afterwards |
| async-match-references-carrier.log | Refused counter-example and two valid neighbors executed, 1,235 s, OK |
| async-match-references-final-O0.log | Final module: 13 methods, 22.933 s, OK |
| async-match-references-final-O2-regression.log | 62 methods, 86,489 s, OK: final module, local async links, async conditional returns, buildtin errors and synchronous expressions |

Helpers of these passages use O0/O2 according to CRUST_TEST_OPT and UBSan
The final passage does not skip any method. `py_compile` and Verification
local links of the modified documents have been successful. The diff is retained in
`validation/async-match-references.patch`. Development failures and
Initial acceptance of the invalid program remains available for audit.

## Mutations

Four errors injected into temporary copies, four detections:

| Faute | Observation |
| --- | --- |
| Forget the bearer Result of the borrowed loan | Invalid mutable double projection accepted |
| Clearing the parents from the charge Ok | Incompatible access to the accepted target |
| Forget the source of the rescue in the contract | Premature access to the second accepted source at the appellant |
| Reverse the join status test | Bad mark/value or zero pointer reported by UBSan |

`validation/async-match-references-final-mutations.log` Keeps the results.
The initial campaign of three mistakes remains in `async-match-references-mutations.log`.
Detections are based on denial/exit claims and executions
native, not on an assumed coverage rate of all defects.

<a id="limites-et-suite"></a>

## Limitations and follow-up

The return of a loan produced by a loop remains refused:
`validation/open-async-reference-loop-result.crust` and its log. S5a/B5 allow
This program: both targets are injected and sustainable; breakes use
The expected release is 30 and 20.
d) Implementation, not a normative rule.

Follow-up: this lack is addressed in [ASYNC_LOOP_REFERENCES_CYCLE.md](ASYNC_LOOP_REFERENCES_CYCLE.md).
The above diagnosis describes the condition prior to this supplement.

General enums and aggregates, all calculated forms of handles and
Other syntaxic positions are not covered by these scenarios.
deviations of the seven drafts remain open, including scheduler, threads,
Select, mutex and implicit storage. Reset remains removed; no coverage
the additional reset n , is claimed in this lot.

Native tests use Clang C11, pthread, -Wall/-Wextra/-Werrar and UBSan
fatal. ASan was not restarted after blocking a blank C executable documented
No evidence of this was provided by ASan/TSan, second compiler, formal verification
or general language safety is affirmed.
