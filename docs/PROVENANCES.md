[Français](PROVENANCES-fr.md)

# Plusieurs provenances possibles, adresses stables

A selected allocation may come from several different sources.
The compiler keeps a finite set of possible sources; execution
contains only one selected object, at its original address.

```rust
fn choose(mut a: -> Int, mut b: -> Int, n: Int) -> <- Int {
    if n == 0 { return <- a; }
    return <- b;
}
let mut first = pool<Int>(1);
let mut second = pool<Int>(1);
let mut a = new(first) Int(10);
let mut b = new(second) Int(20);
let mut result = choose(-> a, -> b, 1);
print(result);
drop(-> result);
first.reset();
second.reset();
```

The two old accesses are consumed. The unreturned candidate is destroyed
The recipient is subject to a single allowance, the sources of which are:
possible `{first, second}`. The selected allocation is not copied or
The same type is still required for candidates.

This contract replaces the previous restriction "same source in all the
It applies to conditional returns of functions and results
allocated expressions `if`. The interlocked calls and successive selections
group together the sets, deducing identical sources.
enum, a possible source is his public pool, not his armless stack.

<a id="protection-statique-des-sources"></a>

## Static source protection

As long as access to the result is still to be used, each possible source must be
remain sufficiently durable and cannot be reset:

```rust
let mut result = choose(-> a, -> b, n);
first.reset(); // Refusé : result peut dépendre de first.
print(result);
```

The protection covers direct access, shared/mutable borrowing,
The first is the re-borrowing of calls and arguments already prepared.
function has the same effect as a direct reset. The readings of the next iteration
A source external to the whole can be reset.
without invalidating the result.

A local source that is too short makes a transfer refuse as soon as it appears
The compiler does not extend its lifespan
and does not move the result to another source.

The analysis remains conservative: a literal condition or knowledge
human branch executed does not automatically reduce this set.
Road refinements and relocations are delayed.

<a id="drop-et-réaffectation"></a>

## Drop and reallocation

`drop(-> result)` destroys the selected object via its actual provenance, preserved
by the runtime in the cell since its allocation.
additional assignor or program inspection at the execution stage.

`source.drop(-> result)` requires that all possible sources of origin be
If the whole contains several, this is the only source of the
form is refused: the explicit receiver cannot be guaranteed correct.
Two candidates from the same pool create only one source and allow
this form of destruction.

Reassignment fully evaluates new result before destroying
the old object selected, if it is still alive and distinct.
the effects of the right member, including a reset of a source of the old member
value. The guarantee to return exactly an inward allowance retains
its identity, even if it has several possible sources.

<a id="reset-après-la-dernière-utilisation"></a>

## Reset after last use

The absence of future use allows a reset of a possible source.
not the right to destroy the result if it is in fact owned by another:

```rust
let mut result = choose(-> a, -> b, n);
print(result); // Dernière utilisation.
first.reset();
// Si result provient de second, son nettoyage reste à effectuer.
second.reset();
```

The compiler controls usages and organizes cleaning before issuing
C. For a result possibly in several sources, the cleaning emitted
for `first.reset()` destroys the result only if its actual source is
`first`The runtime already has this source; this selection of cleaning
is not a dynamic verification of borrowings.

After this reset, the named access to the result becomes invalid, since it can
the cleaning is only kept from the remaining sources
possible for paths where the allowance survives. The cleaning indicator
is zero on destroyed roads and remains armed on others.

A subsequent reset of `second` or the closure of the telescope cleans the survivor
exactly once. `first` can be reused in the meantime: sound
Old identity and old accesses are not reactivated. Repeated resets
and the junctions reconcile the states and assemblies of the paths still alive.

<a id="c-émis-et-pools-denum"></a>

## C issued and pools of enum

Return returns remain returns of `Cell *`. No additional storage for
the object or for a runtime set of provenances is not created.
A partial cleaning looks like this, after simplification:

```c
if (*live && cell_has_source(result, first)) {
    cell_drop(result);
    *live = 0;
}
source_reset(first);
```

The indicator test precedes any reading of the cell.
So, the catch can't be de-referenced by this control.
cleaning passed to the functions continue to provide `NULL` quand cet
indicator is zero, to also avoid charging the dead pointer.

For a single enum, `cell->source` - I mean, his private stack. `cell_has_source` recognizes
the arms belonging to the public pool requested. Reset another pool of the same
The reset remains preceded by the destroyers in the
the logical order of the scopes and creations/receptions, independently of the arms,
addresses and physical order of slots.

Function verification remains specialized in calling in this prototype.
The concrete sets of sources prepare the symbolic follow-up described in
[FUNCTION_CONTRACTS.md](FUNCTION_CONTRACTS.md), without implicitly implementing it.

<a id="exemple-et-validation"></a>

## Example and validation

```sh
python3 prototype/crust.py run examples/provenance.crb
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_provenances.py -q
```

The tests cover heap/stack/pool couples, transferred candidates and
created, addresses, too short sources, nested calls,
reallocations, prepared arguments, future borrowings, direct resets,
conditional and transitive, loop covers and enum pools.
The general limits of validation remain in [SAFETY.md](SAFETY.md).

Full validation: 395 tests passed in standard mode and 395 with
`CRUST_SANITIZE=undefined`, including the 24 new provenance tests and their
sub-cases. Binaries compiled by the harness are instrumented; tests
CLI keep the options of their usual compilation.
