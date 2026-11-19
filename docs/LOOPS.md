[Français](LOOPS-fr.md)

<a id="loop-break-et-continue--un-scope-par-itération"></a>

# Loop, break and continuous: an iteration scope

`loop { ... }` repeats its block. Each passage is a new activation of
scope: local allocations and sources are cleaned before passing
suivant. `break;` leaves the loop closest to the current function.
`continue;` Close the same telescopes, then start its next iteration.

```rust
let mut memory = Pool<Int>::new(1);
loop {
    let mut temporary = new(memory) Int(42);
    print(temporary);
    break;
}
memory.reset();
```

`break` destroyed `temporary` before the exit. `memory` belongs to the parent and
The left-hand telescopes are closed from the
deeper to that of iteration, with destruction before recovery
storage and closure of local sources after allocation.

<a id="plusieurs-itérations"></a>

## Several iterations

Explicit reading `*data` copy the Int content of an allowance or of an allowance
It follows the restrictions on access and does not
transfers storage. It is limited to Int; it does not give access to
arbitrary pointers or pointer arithmetic.

```rust
let mut memory = Pool<Int>::new(1);
let mut controls = Pool<Int>::new(1);
let mut state = new(controls) Int(0);
loop {
    let mut temporary = new(memory) Int(42);
    if *state == 1 {
        break;
    }
    state.set(1);
}
```

This example performs two iterations in the same slot of `memory`.
`state.set(1)` remains the provisional syntax of the transfer of content.
The iteration completed does not leave any local access usable to its allocation.

Cleaning indicators are declared in their function C, but activated
the point where the living allowance is followed. This activation is repeated in
the body generated: an indicator set to zero during the first destruction
cannot prevent the next iteration. The functions do not use
indicators reported in context C or received by parameter.

<a id="vérification-de-la-reprise"></a>

## Verification of resumption

The compiler first analyses an iteration from the inlet state, then gathers
This state with the paths that come back at first. It reanalyses the body if
accesses or states of life change, until stabilization.
local indicators and returns recorded in an abandoned pass
are not kept in the final program.

So, consume a parent's allowance and then start a new iteration that
the application is refused:

```rust
let mut data = new(memory) Int(42);
loop {
    -> data;
    drop(-> data); // L'itération suivante ne peut plus importer data.
}
```

The accesses used again in the body are taken into account through the
The Bank's lending is mainly based on loans from banks, banks and banks.
allocation by incompatible access before the next iteration remains prohibited.

A parent's reset is possible when old accesses no longer serve:
the following iterations can reset an already empty source again,
The indicators keep these operations.
correct after the first destruction and after reuse of an address.

<a id="sorties-et-transferts"></a>

## Outputs and transfers

The roads leading `break` They're all in the same state.
to determine the available accesses after the loop.
`return` The loan is used to finance the loan.
after the loop remains protected on the paths that make `break`.

The existing explicit transfers are still necessary.
by `-> data` dies at the end of the iteration if none `<- data` does not return it to its
A return to the parent marked before `break` is applied by closing the
The result must keep a receipt order.
compatible with the paths analysed; conflicting orders are refused.

A function called from the loop cannot use `break` to leave
The loop of the caller. Embedded loops each have their own exit.
Un `break` during the evaluation of an argument also cleans up the
allowances already prepared in the iteration and prevents the call not yet launched.

<a id="reprise-explicite-avec-continue"></a>

## Explicit resumption with continuous

```rust
loop {
    let mut temporary = new(memory) Int(42);
    if *state == 0 {
        state.set(1);
        continue; // Détruit temporary avant de recommencer.
    }
    print(temporary);
    break;
}
```

Chaque chemin `continue` participate in the recovery analysis, as the normal end
The borrowings required for the next round of operations remain active, including
when all branches end with `continue`, `break` ou `return`.
Un transfert `<-` marqué est appliqué avant la reprise ; ses contraintes d'ordre
The pools can reuse the released slots.

`continue` is the closest loop in the current function. It can be
occur in a block, a branch of expression `if` or during the evaluation
an argument: the allowances already prepared are then cleaned and the call
The following instructions on this path are not issued.

<a id="traduction-en-c-et-divergence"></a>

## Translation into C and divergence

Backend issues loop `for (;;)`. Chaque `break` is translated into cleaning
the relevant telescopes, then jumping to a loop-specific label:

```c
for (;;) {
    Cell *temporary = cell_new(memory, 42, "temporary");
    cell_drop(temporary);
    goto loop_end;
}
loop_end: ;
```

Un `continue` also emits cleaning, then a jump to a label placed
at the end of body C, before the recovery of the `for`. Avoids any remaining code
in the iteration.
The normal exit of an iteration emits its cleaning before the return to the beginning.
A loop without a path `break` do not follow the instructions that follow.
It can return from the function or diverge. A call that can never be called
return does not receive a fictitious result; the corresponding sequence is not
The test programs are not executed on infinite paths.

<a id="boucle-avec-receveur"></a>

## Buckle with receiver

```rust
fn main() {
    let mut memory = Pool<Int>::new(2);
    let result = loop {
        let temporary = new(memory) Int(10);
        let kept = new(memory) Int(20);
        print(temporary);
        break <- kept;
    };
    print(result);
}
```

The C materializes the value of the `break` in a variable declared before the
`for`. Local allocations still attached to the lost telescopes are
The receiver then takes over responsibility for the
The analysis only joins the outputs.
`break`, detains all sources or borrowing targets and verifies their
durability at each exit. The result of a `break` without recipient is without
effect for explicit transfer and triggers a warning.

A loop used to the right of `=` peut utiliser l'ancien receveur pendant
evaluation. `continue` close the iteration and then resume. `return` leaving
function with its usual cleaning. Only one `break` providing a result
achieved replacement.

<a id="remplacer-un-receveur-déclaré-avant-la-boucle"></a>

## Replace a declared receiver before loop

```rust
fn main() {
    let mut memory = Pool<Int>::new(2);
    let mut result = new(memory) Int(10);
    while *result == 10 {
        let replacement = new(memory) Int(20);
        result = <- replacement;
        continue;
    }
    print(result);
}
```

The replacement destroys the old allowance during iteration.
the outcome of this iteration, the C shall keep the address of the new allowance
in a pointer declared before the loop. `continue` or the normal end of the
body update this pointer before the next test. `break` and the test
faux d'un `while` determine access after loop. An output `return`
cleans the function or transfers its result according to the usual rules.

The compiler reanalyses the recaptures from the sources and targets
access to the old allowance cannot be used
to access its replacement. After the last use of a loan
The carrier can remain in storage until it is cleaned.
are invalidated if recovery replaces target.
which may reactivate access, an addiction that the recipient
take to its own generation or destruction orders
incompatible with the law, the resumption of the proceedings is still refused.

<a id="périmètre-et-validation"></a>

## Perimeter and validation

[WHILE.md](WHILE.md) describes the loop provided that does not produce value.
`for` and user labels remain outside the scope.
if the safety depends on correlations between conditions or
The number of passes is limited.

[tests/test_loops.py](../tests/test_loops.py) and
[tests/test_continue.py](../tests/test_continue.py) cover exits and
reprises ordinaires. [tests/test_loop_results.py](../tests/test_loop_results.py)
exercises loop results, borrowings, functions, reassignments,
provenances, cursor and reset.
