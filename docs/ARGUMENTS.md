[Français](ARGUMENTS-fr.md)

<a id="arguments--évaluation-de-gauche-à-droite"></a>

# Arguments: left-to-right assessment

Each argument is fully evaluated before the next.
retains its value in a temporary C. The external function is not executed
the following is the first time that all of his arguments have been prepared.
recursively the same rule.

<a id="emprunt-temporaire-puis-transfert"></a>

## Temporary borrowing and transfer

```rust
fn read(data: &Int) -> Int {
    print(data);
    return 7;
}

fn consume(n: Int, mut data: -> Int) {
    print(n);
    print(data);
}

let mut memory = Pool<Int>::new(1);
let mut data = new(memory) Int(42);
consume(read(&data), -> data);
```

`read` affiche `42`, then produces the entire copyable `7`. His loan is over
prior to the transfer of `data`. `consume` affiche ensuite `7`, then `42`, and destroyed
the allowance when leaving the scope.

A loan stored in a variable can also end after its last
use in the first argument. Subsequent use, after the call, maintains
The analysis distinguishes between active borrowing and the refusal to transfer.
positions of sub-expressions within an instruction.

The reverse order, with a corresponding signature, is refused:

```rust
consume(-> data, read(&data)); // Ancien accès déjà transféré.
```

<a id="arguments-préparés-et-encore-nécessaires"></a>

## Prepared and still necessary arguments

A loan provided directly to the external call must remain valid for
the assessment of the following arguments and the appeal:

```rust
outer(&data, edit(&mut data)); // Refusé : emprunt partagé déjà préparé.
```

Several shared borrowings are still possible.
prevents competing access to the same allocation.
the same restrictions: `outer(&mut memory, create(&mut memory))` is refused.
The result of the `create` before taking this loan from source.
The prototype does not introduce a deferred reservation of mutable loans.

An allowance passed by transfer becomes inaccessible by the old access
the preparation of this argument. It nevertheless remains attached to the scope
the evaluation of the remaining arguments, and then enter into the
function called. A reset in a following argument cannot destroy a
already prepared for the appeal, even if it no longer has a named access.

<a id="expressions-allouées-et-modes-explicites"></a>

## Expressions and explicit modes

Modes remain visible for expressions:

```rust
consume(-> new(memory) Int(42));
consume(-> create(&mut memory));
inspect(&create(&mut memory));
modify(&mut new(memory) Int(42));
```

An allocated result is never implicitly passed to a transferred parameter.
A temporary allocated and borrowed stays in the calling scope until cleaning
automatic or at an authorized reset; it is not automatically destroyed at
The sources remain local statements named and
are neither transferable nor created temporarily in an argument.

Blocks returning an allocation can also provide an argument.
`return` anticipated in such a block leaves the whole function: the external call
does not occur and its already prepared allocations follow the cleaning of the telescopes.

<a id="traduction-en-c-et-validation"></a>

## Translation into C and validation

For the first example, after renaming, the transmitter essentially produces:

```c
Cell *read_argument = data;
int result = read(read_argument);
int first_argument = result;
Cell *second_argument = data;
consume(first_argument, second_argument);
```

No subcall effect is left in the argument list C. The result
therefore does not depend on the order of assessment of the arguments chosen by the
compiler C. Internal parameters required for the resets also remain
pointers in this list with no effects.

[examples/arguments.crb](../examples/arguments.crb) is an executable program.
[tests/test_arguments.py](../tests/test_arguments.py) check the observable order,
shared and transferable borrowings, transfers, temporary allocations,
Resets and re-uses of pools, enums, blocks and returns
The errors of modes and types produce a diagnosis before
These regressions are not a general proof of safety.


<a id="valeur-de-référence-déjà-existante"></a>

## Existing reference value

```rust
fn read(data: &Int) -> Int { return *data; }
let mut memory = Pool<Int>::new(1);
let mut data = new(memory) Int(42);
let mut view = &data;
let mut n = read(view);
print(n);
```

`read(&data)` creates a loan; `read(view)` provides the one already received.
`read(&view)` is refused: the nested references are not supported.
&Int function results are performed directly without `&`
added. Pool settings are also transmitted by their name.
prepared arguments, their order of assessment and drop/reset controls
See [REFERENCE_VALUES.md](REFERENCE_VALUES.md).
