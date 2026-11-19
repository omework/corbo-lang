[Français](MODULAR_CALLS-fr.md)

<a id="appels-vérifiés-à-partir-des-contrats"></a>

# Audited calls from contracts

The memory checker no longer travels the body of a function when it
He's using a bodyless interface, `FunctionContract`,
defined in [contracts.py](../contracts.py). Examples of this step use
pools explicitly typed.

```rust
fn create(memory: &mut Pool<Int>) -> <- Int {
    let mut data = new(memory) Int(42);
    return <- data;
}

fn main() {
    let mut memory = pool<Int>(1);
    let mut data = create(&mut memory);
    memory.reset();
    print(data); // Refusé : data doit encore être utilisée.
}
```

The contract states that `create` allocates an Int in its first parameter and
returns a new allocation from this source.
result in the pool of `main`then refuse the reset before its last reading.

<a id="vérification-et-génération-séparées"></a>

## Separate verification and generation

`Compiler.verify` complete the following steps:

1. Validate signatures and infer effects, results and constraints.
2. Build the interfaces without body functions.
3. Check each body separately with its symbolic parameters.
   sub-calls use interfaces only.
4. Check the instructions at the program level in the same way, if they are
   there is no `main`.

A function declared after the call is covered in the same way.
The body must pass the audit before the program is accepted.
The inference analyses run through the bodies for the
build contracts; re-use subcall summaries.

`Compiler.compile` first launch this check, then the specialized backend
the backend still travels through the bodies to produce functions C,
their captures and accurate cleanings. Its consistency checks are
The order is kept. `check` and API `verify_program` stop before this
backend; they therefore check without this second generation path.

The body checker still builds temporary C fragments for
His own blocks, then throws them away. Separate these fragments from the tracking
memory is a separate work. Opaque calls do not produce any
definition C and do not read any called body.

<a id="contenu-de-linterface"></a>

## Interface content

- Parameter names, types and modes; result type and mode.
- Types allocated by each source and possibly reset.
- Types of pools required by signatures and subcalls, even without allocation.
- Possibility of normal return.
- Possible origins of the result: new entries received or allowances in
  sources received; guaranteed return of the same entry where it exists.
- Constraints of equality and distinction between the sources of parameters.

Enum settings with &Int fields also feature symbols
The contract protects these targets when a reset occurs.
before their reading; a wrapper replaces paths without opening the body.
The contracts for the allocated returns bearing these fields describe their targets
their resolution retains protection after the call,
without consulting the body of the calle. See [REFERENCE_FIELDS.md](REFERENCE_FIELDS.md)
and [BORROWED_RETURNS.md](BORROWED_RETURNS.md).

The interface does not contain body AST or runtime address.
separate inference are not necessary to apply an opaque call.

<a id="transition-à-lappel"></a>

## Transition to call

The arguments are prepared from left to right with the mode controls,
types, movements and borrowings. The arguments already prepared remain
The constraints are substituted for those of the following:
with all possible provenances and storage requirements are
checked against the pools actually supplied.

Allowances received with `->` temporary loans
end at the end of the call; they do not allow the consumption of a
parameter received by `&` ou `&mut` in the body, checked separately.

A possible reset protects all future uses on the calling side, including
its temporarily suspended borrowings and arguments for an inclusive appeal.
An external value potentially affected loses access.
Keeps a conditional cleaning for paths where it can survive:
a possible effect is not considered to be a certain runtime destruction.
The specialized C generation determines the actual cleaning on each path.

The allocated result is received alive on each path that normally returns:

- A guaranteed refund reuses incoming identity and retains its trademarks
  import/export, while consuming the old displaced access.
- A selection or a new object receives a descriptor bearing the union of the
  possible sources and roots of origin.
- A new object returned after a reset is alive. Similarly, a reset on a
  path does not destroy the result made alive by another path.

A scalar copy made before a reset is no longer dependent on the read storage.
A contract without normal return does not produce a path of continuation.

## Utilisation

```sh
python3 prototype/crust.py check examples/modular_calls.crb
python3 prototype/crust.py effects examples/modular_calls.crb
python3 prototype/crust.py run examples/modular_calls.crb
python3 prototype/crust.py check examples/invalid_modular_reset.crb
```

`check` does not request a C compiler and does not accept or `--run` ni `-o`.
`effects` also uses the verifier without running the backend, then displays
the effects, results and constraints inferred in JSON.

<a id="validation-et-limites"></a>

## Validation and limitations

[tests/test_modular_calls.py](../tests/test_modular_calls.py) check calls
with an empty body catalogue and without separate inference tables.
test counts body inputs: each function is checked separately and
subcalls never open the body of the caller.
enums, retours conditionnels, provenances multiples, resets, emprunts,
arguments, loops, divergence, re-use of slots and comparison with
the compilation and execution of C.

These tests are not proof of language safety.
Inference analyses and backend remain in the trust base.
current restrictions on transfers, references and types do not change.
The old storage backends remain available for compatibility;
this step does not introduce a new allocator or address shift.

Validation: 522 tests passed in the full suite standard and 522 with
`CRUST_SANITIZE=undefined`, including 28 new tests on modular calls.
