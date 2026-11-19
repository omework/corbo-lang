[Français](EFFECTS-fr.md)

<a id="résumés-inférés-des-effets-sur-les-sources"></a>

# Inferred summaries of effects on sources

The compiler analyzes functions before concrete calls to deduce
their external effects of allocation and reset. No additional marker
is required in signatures.

```rust
fn clear(memory: &mut Allocator) { memory.reset(); }
fn relay(memory: &mut Allocator) { clear(memory); }
fn make(memory: &mut Allocator) -> <- Int {
    let mut fresh = new(memory) Int(42);
    return <- fresh;
}
```

The summary of the `clear` and `relay` indicates a possible reset of the parameter
`memory`. The `make` indicates an Int allocation in this parameter and none
a temporary allowance also counts, even if it is destroyed before
Return. Have a parameter `&mut Allocator` therefore no longer sufficient to classify
a function as being able to reset the source.

<a id="symboles-et-propagation"></a>

## Symbols and propagation

[effects.py](../effects.py) represents the sources of parameters by their indices
The analysis does not create any concrete allocation, C cell, or
a constant summary of effects contains:

- `resets` : source parameters that can be reset;
- `allocations` : couples (source parameter, type allocated);
- `pool_requirements` : couples (source parameter, type of pool required),
  even when a sub-call signature requires it without an allowance;
- `may_return` : abstract possibility of returning normally to the appellant.

The symbols of the abstract called are substituted for each sub-call by the
local parameters or sources actually named in the calling body.
The order or names of the parameters may differ. The results are set
cache by function for the current non-recursive call graph.

Signatures `&Pool<T>` and `&mut Pool<T>` require a pool of the type indicated,
even with an empty body. This requirement is spread through the parameters
generics and successive substitutions, and controlled for local sources.
Alloating an Int only does not mean `Pool<Int>` ; construire un enum exige
The contradictions are refused even without a concrete call.
[POOL_REQUIREMENTS_VALIDATION.md](POOL_REQUIREMENTS_VALIDATION.md).

Local sources are followed for their types and permissions, but their
effects are not presented as a resource from an appellant's source.
The masking of names respects the blocks: a local pool named `memory` do not
does not implicitly reset the external parameter bearing this name.

The destruction of a transferred argument, including `source.drop(-> data)`,
The cleaning of this allowance is not a collective reset of its source.
remains governed by its transfer, provenance and existing rules.

<a id="branches-boucles-et-expressions"></a>

## Branches, loops and expressions

The possible effects of the branches are combined, even with `if false`, comme
In the current conservative analysis, a conditional reset is therefore a reset.
I can't promise he'll execute every call.

The effects of conditions, arguments from left to right, initializers,
Enum fields and expression blocks are covered. An early output
in an argument prevents the addition of the effects of the body of the call not started.
Instructions after a `return`, `break`, `continue` or a call without return
normal do not contribute to the effects of this path.

The loops combine the effects of the body and the test, including before `continue`.
A loop without normal output allows to deduce `may_return: false`. `while`
keeps its abstract path of false test, even with `while true`, in accordance with
the current contract. `may_return: true` is neither a guarantee of termination nor
a validation of the returned type: there is an abstract continuation.

The recursion remains refused. An unknown sub-call or a cycle necessary to
Inference produces a diagnosis, including in an uncalled function.
Inaccessible calls after a non-continuous output are ignored.

<a id="utilisation-par-le-compilateur-actuel"></a>

## Use by the current compiler

Once the arguments are prepared and checked, the compiler replaces the arguments
concrete sources in the summary:

1. Allocate type requirements are verified on the actual sources.
   An enum pool cannot satisfy an Int allowance requirement.
2. Reset sources determine cleaning catches
   The function is to provide the necessary information in specialized C functions.
   only no longer receives the pointers and indicators of the old ones
   appellant's allowances for this source.
3. Specialized memory verification and C-emission remain in place.
   They control future uses, borrowings and possible sources of revenue
   and produce conditional destruction and indicators.
4. The external resources and allowances encountered during this specialisation,
   including sub-calls, are compared to the summary.
   produces an internal refusal before any compilation or execution of the C.

The comparison is an inclusion: the summary can be conservative.
possible sources of allocation are all considered for catches
if one can be reset. The partial reset protocol of the
[provenances multiples](PROVENANCES.md) remains applicable.

<a id="fonctions-inutilisées-et-limite-de-cette-étape"></a>

## Unused functions and limit of this step

Abstracts are also inferred for non-called functions.
sources are monitored during this analysis.

```rust
fn wrong(memory: &Allocator) {
    memory.reset(); // Refusé, même si wrong n'est pas appelée.
}
```

The effect analysis alone does not check movements or borrowings.
A [Memory Checker Pass](FUNCTION_BODIES.md) now also travels
Each body with symbolic inputs, even without calling.
allocations, borrowings and types of results remain active at the sites
real call.

The [summary of results](RESULTS.md) the effects of the
les origines symboliques des allocations retournées. Les [contraintes de sources](SOURCE_CONSTRAINTS.md) complètent également ces
The full contracts described in
[FUNCTION_CONTRACTS.md](FUNCTION_CONTRACTS.md) now feed the
[checking bodyless calls](MODULAR_CALLS.md)Backend C remains specialized and no annotation of
source or effect is not added to the language.

## Inspection

```sh
python3 prototype/crust.py effects examples/effects.crb
python3 prototype/crust.py effects examples/effects.crb -o /tmp/crust-effects.json
python3 prototype/crust.py run examples/effects.crb
```

The command `effects` produces a JSON object by function name, without compiling
or perform the C. It performs the usual effects analysis and controls
The program's concrete calls. She does not certify all bodies
Unused. `--run` is not accepted with this order.

Extract from the effects for `make` (field `result` is described in
[RESULTS.md](RESULTS.md)) :

```json
{
  "resets": [],
  "allocations": [{"source": "memory", "type": "Int"}],
  "may_return": true
}
```

`main` may have an empty external summary while using sources
local: effects on sources received in parameters, not a
meter for all program memory operations.

## Validation

[tests/test_effects.py](../tests/test_effects.py) covers direct effects,
transitive, parameter permutations, masked names, sources
private, branches, loops and early outputs, calls without return,
nested initializers and arguments, enums, source permissions
C catches and the maintenance of call loan guarantees.
The JSON command is checked without execution of a `main` infini.

Final validation: 415 tests passed in standard mode and 415 with
`CRUST_SANITIZE=undefined`, including the 20 new effects summary tests.
The instrumentation perimeters of the harness and the tests of CLI remain those
described in [SAFETY.md](SAFETY.md). An additional check compared
18 generated summaries of three seeds and several parameter permutations,
an independent propagation model; the sets were consistent.
