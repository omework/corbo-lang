[Français](NESTED_FEATURES_CYCLE-fr.md)

<a id="cycle--contraintes-de-méthodes-indépendantes-et-résultats-concrets"></a>

# Cycle — Constraints of independent methods and concrete results

<a id="règles-et-correction"></a>

## Rules and correction

TF2 imposes independent parameters even when they bear the same name
TF5 imposes a concrete deductible result, without imposing that it has
The previous comparison replaced all the
occurrences of the feature by the type of receiver: it introduced therefore
a type equality explicitly postponed by draft 06.

Contre-exemple reproduit avant correction :

```rust
type feature Visit { fn visit(&self, other: &Visit) -> Int; }
struct Left { value: Int }
struct Right { value: Int }
impl Left { fn visit(self: &Left, other: &Visit) -> Int { return self.value; } }
impl Right { fn visit(self: &Right, other: &Visit) -> Int { return self.value; } }
fn apply(a: &Visit, b: &Visit) -> Int { return a.visit(b); }
fn main() {
    let a = Left { value: 7 };
    let b = Right { value: 9 };
    print(apply(&a, &b));
}
```

The diagnosis was `type 'Left' : exigence de feature 'Visit' non garantie`.
The recipient alone is now substituted for this comparison.
other constraints are compared structurally; they do not become
the type of receiver. A method taking only `&Left` not satisfied
Independent constraint `&Visit`even if a particular call provides
un Left.

A forced result is checked against its own concrete type.
`test_method_feature_result_keeps_its_own_concrete_type` fait renvoyer un
`&Target` by the method of `Wrapper`, then by two relays forced.
The reference keeps its target: destroy this target before its use remains
refused. The modes of receiver, arguments and result remain checked.

Comparison keeps the current stress pairs to deal with their
recursive references. See exactly the same pair closes this comparison,
but don't ignore other names/modes/types. This does not allow recursion
This structural control is not a formal proof of the performance of the functions
the auditor's correction.

<a id="interactions-et-preuves"></a>

## Interactions and evidence

The six new synchronous tests cover: two-way independent types
relay; other feature in the signature; mutable argument and conflict
of borrowing; result of another concrete type; structural constraints
equivalent to separate names; check an incorrect sheet through
three types, even if the method is never called.
refuses an absent method, a bad recipient and a bad result.

`test_async_type_features` ajoute quatre programmes natifs :

- `Vector<Int>` and `Vector<u8>` independent specialists with two waits;
  mutation of the target during the execution refused.
- Thong cut returned by two async functions: the loan protects the
  target after join; mutation, drop and historical reset before last
  use are refused. Mutation and destruction and reuse after use allowed.
- Mutable capture reserving Vector from the creation of the task, before spawn;
  Inconsistent reading, mutation and destruction refused.
- Owner's catch of Thong: unique cleaning at completion, slot
  reused at the same address; former owner unusable.

This supplement represents 10 native programmes and 19 variants refused.
expectations come from TF1–TF5, borrowing, capture and transfer rules,
not the acceptance of the compiler.

Final execution (newspapers retained in `validation/`) :

- `CRUST_TEST_OPT=-O0 PYTHONPATH=tests:. python3 -m unittest
  test_async_type_features test_type_features test_builtin_features -v` :
  **42 successful methods in 19.830 s**, `nested-features-final-O0.log`.
- Same command at O2: **42 successful methods in 20.032 s**,
  `nested-features-final-O2.log`.
- The helper compiles in C11 with fatal UBSan, and `-pthread` for running
  threaded. Both pre-existing signature models (81 and 36 cases)
  are included in these suites, with their oracles unchanged.
- `CRUST_SANITIZE=undefined python3 tests/run_feature_regression.py` :
  **173 successful methods in 42.295 s**, `nested-features-regression.log`.
- Same script with `--inject` : **36 successful methods in 17,843 s**,
  `nested-features-injected.log`. Adding an unused feature to cases
  methods and structures for the new course;
  These cases cover part of the 173 previous cases.
- Compilation Python of modified modules and successful new tests.

## Mutations

`python3 tests/run_builtin_feature_mutations.py` detected the seven mutations
in temporary copies, with original assertions.
`validation/nested-features-mutations.log`.

The four mutations of the buildin cycle remain detected.

1. Reintroduce equality between receiver and other forced arguments:
   incorrect Left/Right program allowed.
2. Ignore the constraint of the result: the three incorrect sheets are
   accepted wrongly, even without any call from the method.
3. Accept any nested comparison instead of a pair already
   In progress: the same three violations are wrongly accepted.

No general detection rate or universal evidence from these errors.

<a id="écart-restant-et-limites"></a>

## Remaining deviation and limits

The programme `validation/open-feature-async-structure.crust` remains refused:
capture `&Item` a user structure is not supported by
the backend async. The executed diagnosis is kept in the file `.log`
It's a limit of implementation, not a new rule of refusal.
The specialisation of the feature is resolved before this restriction.

The building signatures not exercised, `char.utf8_len()` via a feature,
the more general projections and other boundaries of the backend async remain
The multithread scenarios used do not cover all the
interleavings; neither TSan nor formal evidence was used here.
The storage and scheduler deviations of the global perimeter remain open.
