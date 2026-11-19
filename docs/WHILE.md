[Français](WHILE-fr.md)

<a id="while--tester-avant-chaque-itération"></a>

# While: test before each iteration

`while` accepts the same conditions as `if` : `true`, `false` or
comparison of Int values (`==`, `!=`, `<`, `<=`, `>`, `>=`) Operands
are evaluated from left to right, once per test.

```rust
let mut memory = pool<Int>(1);
let mut controls = pool<Int>(1);
let mut state = new(controls) Int(0);
while *state == 0 {
    let mut temporary = new(memory) Int(42);
    print(temporary);
    state.set(1);
}
```

The condition precedes the body at every passage. So the body can never
to execute. `break` exits from the nearest loop; `continue` nettoie
Iteration then resumes its test, without performing the rest of the body.
`return` leaves the function with the cleaning already set for returns.
None of these jumps cross the border of a function.

<a id="scope-du-test-et-du-corps"></a>

## Test and body scale

The test and the body share an iteration scope. There is no block
between the body and the parent of the loop: transfers
`-> data` At the entrance of the body, the direct parent is well targeted.

Temporary allowances allocated directly during the evaluation of the test are
They are destroyed when it is closed, including when the condition
is false, when `continue`, `break` ou `return`. They remain present during
the body when the test succeeds. We must count these temporary ones in the
simultaneous pool capacity. Explicit blocks in condition retain
their own transfer and cleaning rules.

The body allocations are destroyed before the test, according to the order
Inverse creation/receipt. An allowance `<-` marked follows the rules
The local sources are closed after the parent has been transferred.
The released slots may be used for testing or for the body of the
next passage; this does not reactivate any old access.

<a id="vérification-des-chemins"></a>

## Road checks

The analysis of the recovery of `loop` is reused. Reads the condition
The following is the use of the iteration:
next test prevents incompatible destruction before resumption.
The roads `break` do not take up this test; the borrowings still used
However, after the buckle remain protective.

The state after the loop gathers the outputs `break` and exits by condition
false, after the effects and cleaning of the test. This includes the first test,
when the body has never executed. Access must be available on all
These paths for use next. A call in the condition can mutate
or reset a source: its effects are checked even if the body does not
Don't do it.

Conditions are not statically evaluated to prove correlations
even between branches. `while true` preserves an abstract path of condition
false: a function returning a value must provide a return after the
loop if its suite remains accessible for analysis. To express a loop without
output by condition, use `loop`.

<a id="traduction-en-c"></a>

## Translation into C

Backend uses the same C loop `for (;;)` for `loop`. At the beginning of the
body generated, it evaluates the test operands in temporary variables,
then emits the iteration clean and a jump out if the test fails.
The Corbo body is following this control. `continue` jumps at the end of body C after
cleanup; the next passage therefore re-evaluates the test.

Initial control is an internal instruction of the compiler, without a scope
its terms are indexed for the monitoring of loans,
the effects of the functions and the expected returns or jumps during the test.

<a id="exemple-et-validation"></a>

## Example and validation

```sh
python3 prototype/crust.py run examples/while.crb
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_while.py -q
```

The regressions cover zero iteration, comparisons, effects and
test allocations, transfers, cyclical borrowings, functions,
jumps during the test, private sources and slots of Int/enum pools.
The limits of the prototype remain described in [SAFETY.md](SAFETY.md).
