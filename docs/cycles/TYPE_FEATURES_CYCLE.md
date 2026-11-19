[Français](TYPE_FEATURES_CYCLE-fr.md)

<a id="cycle--résolution-statique-des-type-features"></a>

# Cycle — Static function type resolution

<a id="règles-intégrées-et-architecture"></a>

## Integrated rules and architecture

Draft 06 is integrated under TF1–TF5 identifiers in
[TYPE_FEATURES.md](../TYPE_FEATURES.md), with cross-references from I5/B4/B5 and
ME1/ME2/ME4. The guidelines have their separate cycle.

The parser recognizes a feature containing exactly one method, with
receveur `&self`, `&mut self` ou `-> self`. Resolution in
`type_features.py` acts before inference of effects, results and
It produces functions with concrete signatures; it
n

Two audits remain separate:

- The forced body is travelled with its only declared guarantees, even
  without appeal. An additional method of the concrete type does not justify
  a direct or indirect requirement absent from the signature.
- Each specific specialization then passes through the auditors of the
  contracts, borrowings, transfers, origins and cleaning. The result
  d `&Console`, un `&mut Counter` ou un
  owner `Item`, without erasing its storage source.

The cache distinguishes the concrete types from the arguments.
The same feature can therefore be solved independently.
signatures includes modes, arguments, results and markers of
handle; parameter names and the mutability of their local link
are not additional requirements to the feature.

<a id="contre-exemples-et-frontières-examinés"></a>

## Counter-examples and boundaries examined

- Additional method directly called, by alias, in a branch
  false or conditional expression: refusal before specialization.
- Relay to another unsecured feature: refusal even when type
  The practical approach also has the additional method.
- Two features of different names but of the same requirement: relays allowed.
- Bad mode of receiver, argument or result, method absent: refusal.
  The requirement remains mandatory if the body does not use it.
- Feature used for a field, pool, collection or annotation
  local storage: refusal. Duplicated settings, absence of receiver,
  feature vide/multiple, `main` contraint : refus.
- Returnable mutable loan: direct access to the refused target before its last
  use and admitted after. Field borrowing returned by two relays: sound
  Target allocation remains protected against `drop`.
- Consumption of pool allocation by method: single cleaning,
  old invalid access, slot reused at the same address.
- Return owner through two functions: address and pool retained;
  transfer from a pool too short refused.
- Reset effect of a method propagated by two relays, in the profile
  history explicitly activated: later use refused; reset after
  read allowed, single cleaning. The public reset remains removed from the prototype.
- Conditional returns of a feature: a common concrete type is required.
  Two different types of parameters can be used together, but
  do not become a unique erased result.

An error in the new analysis was corrected before closing: the type
`None` d’un `break;` d-a loop was added to the candidates of the
function result. `test_statement_loop_break_does_not_become_a_function_result`
now preserves the minimum program allowed with a loop and then `return t`.
Breaks of a loop expression remain treated as its own results.

Initial fixtures used absent forms of current grammar
(`p.new(Item{...})`, `new(p) Item{...}`, direct structural borrowing
(if) they were replaced by a block/if) `p.new(value:...)` and by
These corrections do not establish a support for the forms
A proprietary relay also keeps a receiver before `return <-`.

<a id="preuves-exécutées"></a>

## Evidence

`tests/test_type_features.py` contains 16 methods. On the final state:

- `CRUST_TEST_OPT=-O0 PYTHONPATH=tests:. python3 -m unittest test_type_features -v` :
  success in 8,868 s; `/tmp/crust-features-O0-final.log`.
- At O2, same sequence executed by `/tmp/crust_features_counted.py` : success in
  12,342 s ; `/tmp/crust-features-O2-final.log`.
- The O2 meter records 21 compilations/natives and 115 programs
  a further compilation of the example inspects directly
  the concrete catalogue and its contracts, without any additional native execution.
- Programs C use `-std=c11 -fsanitize=undefined
  -fno-sanitize-recover=all` at both levels of optimization.
- The independent signature model compares the capacity expressed in
  the source, without calling the compiler's signature normalizer:
  81 Cartesian combinations, 9 admitted/executed and 72 refused. It is included
  in the above numbers, without randomity.
- `/tmp/crust_features_regression.py` : 173 successful methods in 50.543 s,
  `/tmp/crust-features-regression.log`. Opaque contracts, body of functions,
  requirements of pools, returned loans, guidelines, methods and structures
  locales. `CRUST_SANITIZE=undefined` activates fatal UBSan in helpers
  The helper Foundation already uses O2/UBSan fatal.
- `/tmp/crust_features_interactions.py` : 36 successful methods in 23,231 s,
  `/tmp/crust-features-interactions.log`. The script injects a feature and a
  generic relay not called in local method/structure tests,
  then preserves the original assertions. This also exercises the new
  journey on complex concrete bodies that do not involve the feature.
- Compilation of Python `crust.py`, `type_features.py` and the new module
  Successful tests.

The number of regression methods is not a number of programs.
The 36 tests injected cover part of the 173 previous tests; count them
as 209 independent properties would be incorrect.

<a id="mutations-exécutées"></a>

## Changes performed

`/tmp/crust_feature_mutations.py` edits temporary copies of the module
The tests and their expectations remain those of the deposit.
`/tmp/crust-feature-mutations.log`.

1. Abstract verification removal: detected, eight configurations
   Wrongly accepted bans.
2. Omission of result in comparison of signatures: detected.
   The case whose body does not call the method is wrongly accepted; another
   case is later refused by U1 with a different diagnosis.
3. Fusion of specialisations of different types: detected by
   incorrect rejection of an admitted program (Journal confused with Console).
4. Failure to comply with an indirect requirement when the argument is still abstract:
   detected by incorrect acceptance of a demanding relay `flush`.

These four errors do not constitute an exhaustive coverage of the mutations,
The models and tests do not prove that the
correction of all inferences of type or life.

<a id="écarts-restants--lot-non-terminé"></a>

## Remaining deviations — lot not completed

Update: the builtin counter example below is now corrected and
tested in [BUILTIN_FEATURES_CYCLE.md](BUILTIN_FEATURES_CYCLE.md)The passage
The following keeps the historical record of this first cycle.

The catalogue is closed and covers the methods of structures declared in the
programme. The building methods are not yet included.
by the structural intention, still refused to execute the auditor:

```rust
type feature Compter { fn len(&self) -> Int; }
fn count(v: &Compter) -> Int { return v.len(); }
fn main() {
    let mut p = pool<Vector<Int>>(1);
    let v = p.new();
    print(count(&v));
}
```

Diagnosis observed: `type 'Vector<Int>': feature requirement 'Compter' no
guarantee`. You must integrate signatures/contracts builtin, without neutralizing
their effects or their follow-up on borrowing.

The signature of reporting methods also remains to be tested and completed
other features, more general projections and interaction
The recursion remains refused by the prototype. The course
abstract controls guarantees, but does not replace universal proof
on all possible instantiations: memory controls run on
the actual concrete instantities actually produced.

Aucun nouveau passage ASan/TSan, aucune preuve formelle, aucune couverture
The overall objective and batch 06 remain the same.
The storage gaps and draft 04 remain within their perimeter.
