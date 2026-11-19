[Français](REFERENCE_FIELDS-fr.md)

<a id="champs-contenant-un-emprunt-en-lecture"></a>

# Fields containing a read-out loan

Later extension: [fields &mut Int](MUTABLE_REFERENCE_FIELDS.md) are now available; the measures below describe this historical cycle.

The prototype now accepts fields `&Int` in the enums.
implements the rule discussed: an object that still needs to read its reference
The examples use pools.

```rust
enum View { Item { data: &Int } }

fn use_view(view: &View) {
    match &view {
        View.Item { data: value } => { print(value); }
    }
}

fn main() {
    let mut data_pool = pool<Int>(1);
    let mut view_pool = pool<View>(1);
    let mut data = new(data_pool) Int(42);
    let mut view = new(view_pool) View.Item { data: &data };
    use_view(&view);
    drop(-> data); // Autorisé après le dernier usage du champ emprunté.
}
```

Placer `drop(-> data)` avant `use_view(&view)` has the program refused.
Mutation, displacement, reassignment or reset of the target are also refused
If a stocked loan is still to be used, the remaining pools will not make it possible to
not valid an allowance whose life is over.

## Sous-ensemble retenu

- Int scalar fields and immutable fields `&Int`mixed in a variant.
- Initialization by `&nom` explicit Int allowance; no reference
  to a scalar variable, field `&mut` or reference to another enum.
  An existing loan is provided by its name (`data: view`), without `&`
  Additional incompatible access of the mutable parent remains suspended
  until the last use of the field. See [REFERENCE_VALUES.md](REFERENCE_VALUES.md).
- Lecture via `print(view)` ou `match &view`. In the match, an Int field is
  copied; a &Int field becomes a read-out loan. `print`, `address` and
  copie `let mut n = *value` are allowed in the reading arm.
- Switching these objects to functions through existing modes, including
  receipt by `->` and returned allocated with life-time verification. Fields do not give
  no mutable rights on targets, even with a parameter `&mut View`.
- Local transfer of the holder, reallocation, branches and expressions if with
  conservative meeting of possible targets.
- Block transfer if targets already live in the destination scope or
  One of his ancestors, a target of the left telescope, refuses to transfer.

[Returns containing borrowings](BORROWED_RETURNS.md) are now taken
The contract describes the targets of each field and the audit
child → parent controls their life. D1 now prohibits any promotion
implicit local targets; the old proposal for automatic transfer
transitive graphs, cycles and references to other enums are abandoned.
The control of D1 is covered for &Int; fields
step does not implement a general graph and does not introduce any structurals.

Any use of the bearer is treated conservatively as a use of its fields
even a field ignored by a pattern or use that only observes
the address can extend the protection. Possible branches are combined;
We do not promise a minimum analysis of the last uses per field.

<a id="suivi-statique-et-contrats"></a>

## Static monitoring and contracts

Each allowance carries an immutable table: path `Variante.champ` → cibles
The move is still in place, the reassignments replace the move
the porter, the junctions bring together the alternatives. A reference is not
a new allocation or a transfer of its target.

The control of borrowing takes account of future access to the bearer and the
prepared arguments. A reference initialized in a field is protected during
the evaluation of the following fields, as an argument already prepared.
Therefore, a next initializer cannot move or reset its target.

Parameter constraints include a symbol `allocation_field_parameter`
with field path and parameter index. A body that resets a source then
The field produces the necessary distinction between this source and that of the
field. A wrapper replaces these paths. Upon call, all sources of targets
The auditor does not open the body
The opaque test explicitly removes this catalogue.

A known empty variant has no dependencies.
possible variants of manufacturers, movers and if. It checks the types
in the impossible arms of a match without inventing a living target; these arms
C remain inaccessible until variants change in place, such as
the current subset.

The destruction of the bearer does not destroy its targets.
targets can be destroyed before automatic cleaning of the carrier:
the current destructive demonstrative displays the variant name without reading the
Fields. Dependencies of user destroyers remain outside perimeter.

The conservative decision on the dissenting appeals remains unchanged:
any reset is possible to protect future uses, even if the path that resets
A dedicated regression keeps the refusal validated by the user.

<a id="traduction-en-c"></a>

## Translation into C

Un champ &Int stocke un `Cell *` in the payload of the slot; no handle or
The additional runtime allowance is not added. The size and offsets of the
champs utilisent `sizeof(int)` and `sizeof(Cell *)`. The metadata of each
variant stack contain the offsets and categories of the fields.

Access to fields use `memcpy` : a pointer placed after an Int can
be unaligned, and no cast to a `Cell **` non-aligned is not used.
slots remain aligned and arms keep clean sizes. Runtime oracle
historical, which uses payloads only Int, retains its representation.

`cell_print` reads Int targets only when the carrier is validated.
The cleaning of an expired carrier does not decode its fields. An address of
re-used slot does not reactivate the identity of the old object or its borrowings.

<a id="validation-exécutée-et-limites"></a>

## Validation and limitations

The [targeted tests](../tests/test_reference_fields.py) include 27 methods,
with calls, mixed fields, variant masking, reset, reassignment,
Limited transfers, arguments, loop and reuse. The independent model
list 32 scenarios, seeds 0–31, with three targets, two fields and operations
drop/mutation/reset before or after the next use of the carrier: 19 programs
The report does not read the decisions of the
a miscalculated initial count 18/14 in
the harness was corrected in 19/13; the expectations of each of the 32 programs
have not been modified.

Additional orders:

```sh
python3 tests/run_reference_field_mutations.py --output validation/reference-field-mutations.json
python3 tests/validate_reference_field_c.py --output validation/reference-field-c.json
```

The mutation campaign injects four errors in temporary copies: table de
omitted dependencies, field source absent from contract, loan prepared omitted and
incorrect pointer offsets. First fingerprint check was disturbed
by the concurrent addition of the C script to the project; it was relaunched on a set
stable files. The final result is in the
[transfer ratio](../validation/reference-field-mutations.json), without rate of
extrapolated overall detection of this sample.

Campaign C consists of three programmes × O0/O2/Os/O2-UBSan: eight executions
The values,
addresses and destructions are specified in the harness, regardless of the
compiler.](../validation/reference-field-c.json) keep the
results. Only one family C is available, Clang; ASan remains unavailable
on this host according to previous tests. UBSan controls do not prove
safety of all roads.

The [Rules Matrix]](VERIFICATION_MATRIX.md) is updated. The graphs
transitifs, collections, variants and changes
destroyers users remain unchecked. The model is a model of
The border of simple dependencies, not a general oracle of borrowing.

<a id="résultat-des-suites-complètes"></a>

## Result of full follow-up

Both full suites ended without fail:

| Commande | Actual |
| --- | --- |
| `python3 -m unittest discover -s tests -q` | 572 tests, OK, 386,082 s |
| `CRUST_SANITIZE=undefined python3 -m unittest discover -s tests -q` | 572 tests, OK, 385,870 s |

Cleaning models, pool type roads and runtime oracle
The 27 new methods and the
The four mutations were also the model of 32 scenarios.
detected during re-launch; the front/after prints are identical.
The twelve C-executions optimized are a separate campaign completed without
There is no open failure of this cycle.

The [structured results]](../validation/reference-field-suites.json) conservent
The total number of programmes
the total number of subvariants in the suite is not aggregated; the
account 19/13 relate exclusively to the field boundary model.
No formal evidence or general validation of all graphs is claimed.
