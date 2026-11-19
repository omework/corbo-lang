[Français](ASYNC_TYPED_DIVERGENCE_CYCLE-fr.md)

<a id="cycle--initialisations-async-typées-sans-continuation"></a>

# Cycle — Async typed initializations without continuation

<a id="règles-et-changement"></a>

## Rules and change

Application of S5/S5a, B1–B5, D1, E3/E5/E6/E7 and AS10/AS11/AS12, without
ENGINEERING.md, VALIDATION_GUIDELINES.md, index of the seven
The results of the work were based on the following:
rel. The previous cycle had corrected the expressions without continuation
and a leak of prepared catches; this batch completes the typed reception.

The programme `validation/open-async-diverging-typed-initializer.crust` is
Now accepted and executed: 42, 20, 77. `[Int;1]` does not create
not a table when all paths leave the initialization by break.

Before the specialized treatment of an annotated bond, the compiler examines
the known control expressions without continuation.
Async directory recognized, it checks and generates their actual outputs before
d) require a value for the receiver. It does not materialize any connection on these
paths. A continuing branch must always provide the declared type.

This control does not skip the analysis of the outputs: break modes, targets,
The same checks are carried out on sources, transfers and cleanings.
The types of tables recognized include:
interlocking dimensions and Int shared/mutable references; types
scalar and recognized building results are also exercised.
API is not introduced or copy or transfer rule is not introduced.

The processing is placed at both variable reception points: in the
main body of the function and in branches/blocks. An initial placement
in scalar treatment alone would have left annotations of tables of
references fail too early in specialized loop processing.

<a id="scénarios"></a>

## Scenarios

`tests/test_async_typed_divergence.py` has six methods, 25 executions
and 27 refusals expected in full passage:

- Empty table, nested table u8, tables of &Int and &mut Int, Boool, char,
  runtime::Error and Result<char,CharFromStrError> as types of receivers
  The two outputs are executed.
- Premature change of each of the two sources of the rejected borrowed result
  for each annotation, then use and reuse of slots after use.
- Block, match, return, loop without intermediate result and continues, with
  suspension; no marker of inaccessible suite is executed.
- One arm comes out by break and the other actually provides a picture: the neighbor
  valid is executed, while bad size, bad type of element or
  Bool annotation is refused.
- Local target not sustainable, different reference modes, worthless break,
  continuing branch of a bad type and unknown types remain refused.
- Typical output during preparation of arguments for a call: allocation
  already moved is destroyed exactly once, and its capacity pool one
  is reused after join. The missed task is not started.

Expectations are explicitly defined from branches and rules
No new general independent model is added for this
Receipt correction. Flow control models from previous cycles
No universal safety reasoning is derived
of these finished scenarios.

<a id="exécutions"></a>

## Implementation

| Journal in validation/ | Result |
| --- | --- |
| async-typed-divergence-initial.log | 6 methods, 10.723 s, OK; before moving the control to both receptions and adding the annotated loop case with references |
| async-typed-divergence-O0.log | Final module: 6 methods, 13.290 s, OK |
| async-typed-divergence-mutations.log | Four targeted errors detected |
| async-typed-divergence-O2-regression.log | 96 methods, 114,353 s, OK, no jump |

The O2 regression is over. It loads test_async_typed_divergence,
test_async_diverging_expressions, test_async_expression_loop_exits,
test_async_loop_references and test_async_match_references, then methods
d’AsyncRuntimeTests contenant array, conditional, typed ou cleanup.
The newspaper keeps their names accurate. Native helpers use Clang C11,
pthread, -Wall/-Wextra/-Werrar and fatal UBSan.

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_async_typed_divergence -v
python3 tests/run_async_typed_divergence_mutations.py
```

`py_compile` and local links of the modified documents were verified.
The compiler diff is kept in
`validation/async-typed-divergence.patch`. Runtime has not changed.

## Mutations

| Error in temporary copy | Detection |
| --- | --- |
| Disable typed treatment without continuation | Valid program refused |
| Accepter toute annotation comme connue | Unknown Types Wrongly Accepted |
| Clear source of result | Premature change of accepted target |
| Omit cleaning of prepared catches | Pool of capacity one out of stock |

Tests distinguish expected refusals from compilations of valid programs
and check native outputs. No overall detection rate is extrapolated
of these four selected errors.

<a id="limites-et-prochain-chantier"></a>

## Limitations and future construction

This lot concerns the directory of types already recognized by the backend async.
It does not materialise new aggregates and does not generalise all the
Annotations of external handles, structures or types.
The goal of the seven drafts is not achieved.

The next identified project is RT8: the synchronous block `runtime::thread`.
`validation/open-native-thread-basic.crust` takes back this validated primitive
with a block without capture returning 7, then an explicitly treated join.
The compiler still refuses this program to parsing:

```text
REJECTED valid RT8 program: ligne 2: attendu ';', reçu ':'
```

This lack is already noted N in the matrix. Draft 04 then imposes the
explicit catches, anticipated returns, the native thread distinct from the
scheduler, failure LaunchFailed, lifespans and waiting obligations.
The minimum fixture is not presented as a cover for these requirements.

Follow-up: the [native border cycle]](NATIVE_THREAD_BOUNDARY_CYCLE.md)
adds from parsing and internal launch primitives.
and the block generation remain open; the current matrix passes RT8 to P
The parsing diagnosis cited here is historical.

The rules of scheduler, select, mutex and implicit storage also remain
Reset remains removed. ASan was not restarted after the documented blockage
Program C empty. No evidence ASan/TSan, second compiler, formal evidence
or general security is claimed.
