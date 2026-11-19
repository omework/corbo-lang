[Français](SOURCE_CONSTRAINTS-fr.md)

<a id="contraintes-inférées-entre-sources"></a>

# Inferred constraints between sources

The compiler deduces the relationships between the sources of the parameters from the
the body operations, then substitutes them for calls.
added to signatures. Constraints complement summaries of effects and effects
results; the full memory verifier also remains executed at calls.

<a id="lire-avant-ou-après-un-reset"></a>

## Read before or after a reset

```rust
fn clear_then_read(memory: &mut Allocator, data: &Int) -> Int {
    memory.reset();
    return *data;
}
```

The contract contains `source(data) != memory`. Reading after reset requires
the allocation cannot depend on the reset source.
the totality of possible sources of `data` shall be distinct from `memory`.
Only one common possible source is sufficient to have the appeal refused.

```rust
fn read_then_clear(memory: &mut Allocator, data: &Int) -> Int {
    let mut value = *data;
    memory.reset();
    return value;
}
```

The body does not impose this distinction: the entire is copied before the reset.
It can work with `data` in `memory`, if no subsequent use of this
The appellant does not have any entitlement or loan.
in a wrapper, an additional constraint appears in its summary;
concrete controls on future uses are also active.

<a id="égalité-pour-une-destruction-avec-source-explicite"></a>

## Equality for destruction with explicit source

```rust
fn consume(memory: &mut Allocator, mut data: -> Int) {
    memory.drop(-> data);
}
```

The body imposes `source(data) == memory`. All possible sources of
parameter must be equal to this source. One result from two
separate pools do not meet this requirement.

`drop(-> data)` directly uses the origin of the object and does not impose
this equality with an allocator parameter.
or automatic cleaning is not considered as a collective reset.

<a id="analyse-symbolique-ordonnée"></a>

## Symbolic order analysis

[constraints.py](../constraints.py) distingue :

- a source received as a parameter, `source_parameter` ;
- the source of an allowance received as a parameter, `allocation_parameter` ;
- a local source created in the body.

The values allocated and borrowings are followed by symbolic assets.
active retains the potential resets that have occurred since its creation or reception.
A reading, mutation, borrowing creation, transmission or return requires that it
It produces the necessary distinctions from sources.
An allowance created after a reset begins with an empty history.
The amount of the allowance which she has read the value of does not remain dependent on scalar.

The branches are from separate states. Their historical records are only joined
on the paths that continue. A reset in a branch leaving the function
therefore does not automatically render a reading of the other branch incompatible.
A conditional reset before a common reading, however, requires a
The analysis remains conservative.

The loops combine the recovery states until stabilization. Read a
parameter then resets a source before `continue` also protects reading of the
next passage. A path that makes `break` do not repeat this reading.
The effects of the `while` are taken into account, as well as the exit path
before the first execution of the body and the use after the loop.

Local assets are removed when the telescopes are closed.
automatic does not create a false survival obligation after reset: running
and the generated code only cleans objects still alive.

<a id="sous-appels-et-réception-des-résultats"></a>

## Sub-calls and receipt of results

The constraints of a sub-call are substituted by the sources and values of the
calling body, including when parameters are reordered. A selection
of several provenances produces the obligations for each of the alternatives.
The reset effects of the sub-call then feed into the appellant's history.

An allocated result is received alive on each path that returns normally.
His reception history is therefore restored without blindly assigning to him
all possible resets of the sub-call. This preserves cases where a path
Returns the input without reset and another resets a source and returns
The constraints necessary for the survival of the entry are:
verified in the contract called. The old accesses consumed are not
Reactivated: Travel control remains with the full auditor.

The arguments are evaluated from left to right. An allocation or a loan
prepared must survive until the call begins, even if the parameter is unused.
A reset in a subsequent argument therefore requires a source distinction.
Int value already copied does not have this obligation.
prepared remain exclusive according to the rules of existing arguments.

<a id="simplifications-et-refus"></a>

## Simplification and refusal

The equality of a symbol with itself is true; its distinction with itself
is impossible. A fresh local source is distinct from the sources of entry
and other local creations. The exclusivity rules already imposed by the
source parameter modes also allow for the recognition of certain
sources comme distinctes.

An impossible obligation makes the body refuse, even without appeal.
in particular an allowance created in `memory`, followed by `memory.reset()` then
of a reading of this allowance.
The solver is not a general proof of the
the suitability of all types and sources of relationships.

Exported constraints only contain parameters, without identities of
The compiler compares the identities of the
sources before specializing and emitting the body. It does not add any
dynamic relationship control or object displacement.

## Inspection

```sh
python3 prototype/crust.py effects examples/source_constraints.crb
python3 prototype/crust.py run examples/source_constraints.crb
```

The command `effects` ajoute `constraints` The results of the project are presented in the following table:

```json
{
  "relation": "distinct",
  "left": {"kind": "allocation_parameter", "parameter": "data"},
  "right": {"kind": "source_parameter", "parameter": "memory"}
}
```

The contract for `read_then_clear` contains an empty list; that of `consume`
contains the equality of the same categories of symbols.

<a id="portée-et-validation"></a>

## Scope and validation

This analysis does not replace the verification of movements, aliases
The errors of the
names encountered during the course are now refused even without appeal,
and a [pass of the memory verifier](FUNCTION_BODIES.md) now controls
also every body with symbolic entrances, even without calling.
transitive graphs and returns other than &Int remain outside the subset.
[direct returns &Int](DIRECT_BORROW_RETURNS.md) now keep
the history of the original targets through the contracts, without the birth of a
new object at the time of receipt of the reference. &Int immutable fields now have source symbols
`allocation_field_parameter`, substituted for bodyless calls; see
[REFERENCE_FIELDS.md](REFERENCE_FIELDS.md). The rules and restrictions on transfer and scope
remain applicable to loop state analysis.

[tests/test_constraints.py](../tests/test_constraints.py) couvre l'ordre lecture/reset,
equal/differentiated and multiple sources, transitive substitutions,
local sources, branches, loops and `continue`, the guaranteed results alive,
prepared arguments, scalar copies, enum pools and JSON command.
The general instrumentation limits are described in [SAFETY.md](SAFETY.md).

Validation: 467 tests passed in the full standard suite and 467 with
`CRUST_SANITIZE=undefined`including the 27 new stress tests.
