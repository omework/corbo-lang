[Français](RESULTS-fr.md)

<a id="résumés-symboliques-des-résultats-alloués"></a>

# Symbolic summaries of the results allocated

The compiler infers the origins of the results allocated from the body of the
functions, without concrete call or annotation in the signature.
remain stable: new information belongs to the Python analysis,
not to the running representation of objects.

## Trois cas

| Function | Summary of result |
| --- | --- |
| Create and return an allowance via `new(memory)` | New allocation in parameter source `memory`. |
| Returns exactly its transferred parameter `data` | Same allowance as `data`, with its identity and provenance. |
| Choisit entre `a`, `b` or an allowance created | All alternatives, distinguishing incoming identities and new allocations. |

```rust
fn make(memory: &mut Allocator) -> <- Int {
    let mut data = new(memory) Int(42);
    return <- data;
}

fn forward(mut data: -> Int, n: Int) -> <- Int {
    let mut result = if n == 0 {
        -> data;
        <- data
    } else {
        -> data;
        <- data
    };
    return <- result;
}

fn choose(mut a: -> Int, mut b: -> Int, n: Int) -> <- Int {
    if n == 0 { return <- a; }
    return <- b;
}
```

`make` produces a new allowance; `forward` the same allowance is paid on
all returns; `choose` does not promise which of its entries will be returned.
Sources of `a` and `b` may be different.

The freshness is relative to the entry of the function. A wrapper that creates a
object then the pass to `forward` thus renders a new object from the point of view of its
A wrapper who transmits his entry retains this identity.
Two sites that create objects in the same source can be grouped together
under "new in this source": it does not promise a common identity between
objects or a number of allowances.

<a id="analyse-indépendante"></a>

## Independent analysis

[results.py](../results.py) The following are nominal values and symbolic sources:

- the allowances received are indicated by the index of their parameter;
- the new allowances are described by the symbolic source which provides them;
- the travel, reassignments and receptions transmit alternatives;
- the branches that continue to gather their results; explicit returns
  feed the summary of the function, even from blocks or arguments;
- loops travel through body returns and keep possible outputs;
- subcalls substitute their parameters with the values and sources of the
  context, by reusing their summaries.

Calls without normal return, based on the summary of effects, do not provide
The scalar and Void signatures are displayed with their own
mode/type, without alternative allowances. This step does not check them
completely independent of calls.

For functions returning an allowance, normal returns must be
provide the reported allocated type. A local source in a result
The contract is not accepted by the parties, including the right to appeal against the contract.
The return of loans remains outside the subset.
allowance keeps the requirement of `<-` ; no new syntax shortcut is
introduit.

<a id="substitution-et-contrôle-aux-appels"></a>

## Substitution and control of appeals

Compiler solves the summary with the actual arguments before specializing
The expected provenance is union:

- sources of incoming allocations that can be returned;
- real sources of parameters in which a new object can be created.

The results of the specialization must comply with this contract.
keeps a trace of the original physical allowances through the
selection descriptors. Creations by `new` have a symbolic root in their analysis context,
with a registered source; a selection brings together these roots without creating a
This is not based on the equality of pointers.

The check shall separately verify:

1. the possible sources of the result are announced;
2. an identity present at the entrance is allowed as returned entry;
3. a new root comes from a source authorized for new objects;
4. a guaranteed return of a parameter retains its roots exactly.

The third audit does not simply compare the union of sources:
an authorized source for an input cannot hide a new object created
Incoherence produces a refusal before C compilation.

The inspecified provenances are used for the appellant's result.
Each possible source remains protected against a reset incompatible with the
future uses in accordance with [PROVENANCES.md](PROVENANCES.md).

<a id="restitution-didentité-et-nettoyage"></a>

## Identity restitution and cleaning

An expression `if` internal can represent the same object with a new
selection descriptor. If the summary guarantees the return of an entry and
the origin control confirms it, the compiler retains the identity
This preserves import connections
and transfer markings already established, even through several wrappers.

The old names consumed remain invalid. The recipient receives access; in
the existing rules for returning an import restore the
The reception remains a new entry in order to
cleaning. Indicators do not reuse a function's C variable
finished, and the returned object is cleaned exactly once.

A move in a pool is not introduced. If a function destroys its
input then creates an object in the released slot, the new result is **neuf**,
even when its address is identical. It cannot restore the old access
or satisfy a guarantee of return of this entry.

## Inspection

```sh
python3 prototype/crust.py effects examples/results.crb
python3 prototype/crust.py run examples/results.crb
```

The command `effects` keeps effect information and adds a field
`result` for each function. Example for `forward` :

```json
{
  "mode": "owned",
  "type": "Int",
  "alternatives": [{"kind": "parameter", "parameter": "data"}]
}
```

For `make`, the alternative is :

```json
{"kind": "fresh", "source": {"kind": "parameter", "parameter": "memory"}}
```

For `choose`, alternatives designate `a` and `b`. There is no identifier
the number of days spent in the event of a loss of income or of a specific address in these summaries.

<a id="limites-et-validation"></a>

## Limitations and validation

The results of &Int field objects now describe the identities of the
Targets borrowed in `borrowed_fields` and variants built in
`fresh_variants`. These metadata are substituted through calls without
open their bodies. [Child verification → parent]](BORROWED_RETURNS.md)
refuses targets too short according to D1, without automatic promotion allowed.
The direct return of a loan remains outside the subset.

Backend C is still specialized in real calls.
[passing on the bodies]](FUNCTION_BODIES.md) also executes the memory verifier
with symbolic entries, even without a call.
The nominal analysis of the results is not a complete verifier of the movements,
permissions, references or uses after destruction; these controls are assured
by the passage on the bodies and maintained to the real calls. [Contraints between sources](SOURCE_CONSTRAINTS.md) are now inferred
and verified at calls.](MODULAR_CALLS.md)
are also checked without browsing the bodies. [direct &Int returns](DIRECT_BORROW_RETURNS.md)
extend the summary with `reference_targets`, without any candidate allocated or new source.
Constraint analyses keep the history of existing targets, without
treat them as new allowances received after a reset.

[tests/test_results.py](../tests/test_results.py) covers abstracts without calls,
substitutions, multiple selections and sources, reallocations,
returns in loops and arguments, refunds through a `if`, the
imports and cleaning, re-used enums, resets and slots.
intentionally false verify refusal of an incorrect identity or provenance
before issuing an executable program.

Final validation: 440 tests passed in standard mode and 440 with
`CRUST_SANITIZE=undefined`, including 25 new test results and their sub-cases.
The instrumentation limits of test binaries remain described in
[SAFETY.md](SAFETY.md). An additional check compared 18 abstracts generated
to an independent model, with parameter rotations and six levels of
the results and
destruction accounts were consistent.
