[Français](STRUCTURES_METHODS-fr.md)

<a id="crust--structures-construction-et-méthodes"></a>

# Corbo — structures, construction and methods

Reference permissions follow [MA1–MA6](MUTABLE_ACCESS.md). Earlier exclusion
descriptions below do not reintroduce `&mut` uniqueness; storage-invalidating
effects remain constrained by dependencies.


Decisions validated in discussion, recorded on November 5, 2026.

This document is complete [LANGUAGE_RULES.md](LANGUAGE_RULES.md). It shall record the
The initial recording was documentary; the implementation cycles and the matrix
indicate from which behaviors were exercised. Normative examples alone do not
constitute evidence.

The [fundamental cycle]](cycles/FOUNDATIONS_CYCLE.md) has since added the case
`Pool<Int>.new()`, its defect `0` and the verification of the annotation
Int-field flat structures and Int-name references can now be built into a pool. The
omitted structure fields are initialized in the same slot when their terminal fields
all have a defect. The explicitly contained literals are also connected in this slot,
in sync and async, with written order:
[cycle of interlocked manufacturers](cycles/INLINE_STRUCTURE_CONSTRUCTION_CYCLE.md).
The paths to Int fields are legible and can be modified in place. Int direct or
interlocked field borrowings distinguish paths. Return contracts retain the paths of
Int field borrowings, including in return fixed tables. Int terminal field
substructure borrowings and references are connected for synchronous calls and
returns, including references to typed structures:
[view cycle with typed references](cycles/INLINE_TYPED_VIEWS_CYCLE.md). Their copies, when the fields are copyable, to the
local data stack or explicit pool are connected in the
[view copy cycle](cycles/INLINE_VIEW_COPY_CYCLE.md). [storage in reference fields](cycles/STORED_INLINE_VIEWS_CYCLE.md) is
connected for the synchronous routes tested: construction, copying, replacement,
return and match. [results combining whole and inner reference](cycles/MIXED_INLINE_RESULTS_CYCLE.md)
are also connected to the synchronous outputs tested.
[Async captures of views](cycles/ASYNC_INLINE_VIEWS_CYCLE.md) cover now the
Int fields, Int references and descendants already represented owners,
with suspension, calls, copies and returns of borrowed fields. [recorded nominal reference carriers]](cycles/ASYNC_STORED_VIEWS_CYCLE.md)
are also connected to catches, reborrowing, replacements, constructions,
copies and returns of porters exercised. [Direct async returns of references
nominales](cycles/ASYNC_NOMINAL_RESULTS_CYCLE.md) cross, wait, join, Select, the
The [reference field matches d
nominales](cycles/ASYNC_ENUM_NOMINAL_CYCLE.md) cover projections, reborrowing and
Targeted returns, with carrier cleaning. The recursive graphs remain open.
[Property view of fields](cycles/INLINE_OWNED_VIEWS_CYCLE.md) permettent aussi
accesses, reborrowings and synchronous replacements via the root, including
The cases are A<Int> and A<Leaf>.
Implicit copying from an injected pool is also partial. Methods on named receivers
use function contracts. Copying local structures on the implicit data stack is
connected for fields already supported, with placement of results in the recipient.
Evidence and limitations are contained in [STORAGE_DESIGN_CYCLE.md](cycles/STORAGE_DESIGN_CYCLE.md).

<a id="1-structures-et-construction-dans-un-pool"></a>

## 1. Structures and construction in a pool

**ST1 — Complete structure and contained fields.** A structure declares that
A usable instance is fully initialized. The fields directly contained, including
nested structures, are part of its allocation; they do not each require an
independent slot. A stored reference remains a reference to its target, not an
implicit allocation of this target.

**ST2 — Pool.new and type annotation.** `Pool<T>` is a building whose method
`new` construct an instance of `T` directly into a pool slot and returns
The compiler associates his source. Both entries are authorized and equivalent:

```rust
let point = points.new();
let point: Point = points.new();
```

The second performs a type check, without conversion or additional allocation. A type
incompatible with the pool type is refused. The source remains explicit in the
receiver; the call requires an available slot and the necessary access rights to the
pool. This notation does not delete the
anciennes constructions `new(source)` Outside the perimeter discussed.

**ST3 — Deducted defects.** The failure of`Int` is `0`. A structure has a
default construction when all its fields have one, recursively. A reference has no
implicit defects: neither invented target nor zero reference.
Un champ `A<T>` requires an explicit initializer that provides an allowance.
The possible failure of `T` does not determine any pool source.
The absence of a defect does not prohibit the type or its pool; it prohibits the
construction without sufficient initialization.

Custom defects are not part of the selected prototype.
`x: Int = 10` has been rejected; a possible tag notation is postponed.
No custom function `Type::default()` has been validated.

**ST4 — Explicit initialization appointed.** `pool.new(champ: expression, ...)`
A field omitted receives its defect if it exists; otherwise construction is refused.
An unknown field, repeated or supplied with an incompatible type is refused. The
expressions provided are evaluated from left to right in the written order.
References and transfers introduced by an argument remain protected during the
following arguments, according to the rules already used for calls.

For a recipient `Pool<T>` dont `T` is a structure, `pool.new({ field:
The type of pool gives the type of pool.
of the structure, as if its name appeared before the accolades.
`pool.new()` and `pool.new({})` are equivalent: each field is omitted and
must therefore have a defect.

```rust
struct Boite { nombre: A<i64> }

fn main() {
    let mut nombres = Pool<i64>::new(1);
    let mut boites = Pool<Boite>::new(1);
    let boite: A<Boite> = boites.new({ nombre: nombres.new(7) });
    drop(boite);
}
```

This form is retained for the building `Pool.new` ; she does not decide on a
General syntax of named arguments in all functions. The program-accessible instance
never has an uninitialized field.

<a id="2-champs-emprunts-et-contrats"></a>

## 2. Fields, borrowings and contracts

**ST5 — Change in place.** Writing a field requires a mutable access to the
structure. For a field `Int`, `point.x = 30` edit content without replacing
the allocation of `point`, moving its fields or consuming another slot.
restrictions d'emprunt restent applicables.

**ST6 — Reservation by field.** Deux champs `Int` may be
When the borrow is borrowed at the same time, since their storages are proven to be
separate. Each reservation ends at the last use of its borrow. Incompatible access to
the same field remains refused. Moving or destroying the entire structure requires
the end of the borrowings that block it.

**ST7 — Interlocked paths.** Follow-up is recursive: `segment.debut.x` and
`segment.fin.x` are distinct; a loan of `segment.debut` covers, however,
all fields of `debut`. A reservation prevents incompatible access to the
The physical distinction of fields does not alone prove the distinction between
targets.

**ST8 — Contract of returned field.** A function returning a loan to a
direct field keeps this path in its contract. After the call, only the fields that
can be targeted remain reserved; the distinct proven fields are accessible. The
structure remains alive as long as the result depends on its storage. If several
fields can be returned, all relevant possibilities remain followed. The calls exploit
the contract without retracing the called body.

**ST9 — The argument must first be borrowing.** A function requiring
`&mut Point` demands that this loan be created on all the `Point`, even if
His body only writes `y`. An active loan incompatible with the `x` bloque cet
argument. A function receiving `&mut Int` may on the contrary receive only
`&mut point.y`. The accuracy of the contract after the appeal does not legalise an argument
invalid at the time of preparation.

**ST10 — Reassignment of a reference field.** With mutable access to the porter,
`vue.cible = &second` changes the target of the field without changing or destroying the
The old target will cease to be reserved if no other borrow retains it; the new
target will be followed from the assignment and will have to live long enough. The
structure remains fully initialized.

**ST11 — Reborrowing from a mutable field.** `&mut *vue.cible` reborrows object
Targeted by a field `&mut`, without producing a `&mut &mut T`. Until last use
the reborrowing, the mutable access of origin, the replacement of the field and the
destruction of the bearer are refused. Other distinct proven fields remain
accessible.

**ST12 — Contract for indirect re-borrowing.** A function returning the loan
a mutable field keeps both the target and the reservation of the mutable capacity
stored in the field. Following only the target address is not enough. The contract
can nevertheless release the other separate paths after the call, like ST8.

**ST13 — Shared reference returned as value.** `return vue.cible`, for
a type field `&Int`restores the shared reference to its external target.
The result retains this dependence, not an artificial dependence on the holder's
slot. Therefore, the holder can be destroyed after the call if no other borrow blocks
it. The target remains protected until the last use of the result. This case does not
allow to copy a mutable reference.

**ST14 — Direct field storage borrowing.** `return &point.x` means
on the contrary part of the slot of `point`. The contract retains this dependence
The child's boundaries → parent, pools and the absence of implicit promotion continue
to apply, without any further specific arbitration for the structs.

<a id="3-transferts-remplacement-et-copie"></a>

## 3. Transfers, replacement and copying

**ST15 — No displacement extraction or partial condition.** The decision
finale prohibited to extract a non-Copy field by displacement. For example:

```rust
let mut sortie = <- vue.cible; // Refusé si cible est &mut Int.
```

A borrow/reborrow is used or the entire structure is transferred. Fields can be read
or copied when their type and reservations allow, and reassigned according to the
mutation rules, without leaving any field absent. Cleaning destroys the fields
present in a complete structure, then releases its entire slot. No zero reference is
introduced to represent a moved field.

This decision replaces the intermediate agreements allowing extraction, absent field
reset, partial destruction and junctions of roads with a potentially displaced field.
These agreements are no longer rules of the prototype. It does not require that an
object be exposed before the end of its construction.

**ST16 — Replacement of the entire allowance.** A mutable variable may
receive a new allowance by explicit transfer:

```rust
point = <- points.new(x: 30, y: 40);
```

The new structure is constructed completely before the old one is destroyed. The two
allocations coexist during this evaluation; two slots are therefore necessary in this
example. The old allocation is then destroyed and its slot rendered. The variable
refers to the new allocation, the storage of which is not copied in the old slot. A
borrow from the old allowance used after this replacement causes it to refuse. This
rule generalizes the reallocation already retained, without introducing a partial
state of structure.

**ST17 — Structural and explicit co-eligibility.** A structure value is
If his fields are, recursively, copyable. `Int`
and shared references are copyable; mutable references are not, so a structure that
contains them is not. The copied shared references retain their targets and
restrictions.

This property does not allow an implicit copy of the structure or a duplication of
access to an allocation by simple assignment. A copy reads the source and must
respect its active borrowings. It does not clone objects pointed by the reference
fields.

**ST18 — Storage of copy.** `copy(original)` on a local structure
produces an independent value of the same type on the implicit data stack of the
recipient scope. All fields must be copyable according to ST17. The copied shared
references retain their targets and constraints; the pointed content remains shared.
The transfer of this copy follows the same rules of placement and service life as
other local values. This precision incorporates the validated draft 07.

`pool.copy(original)` initialise un nouveau
slot of the recipient pool with the copy of the original content. The pool must have
the type expected and a slot available. On a pool allocation,
`copy(original)` uses the pool
real income, recovered from the source of the allowance, including after
The original remains usable.

These operations are special for the compiler: they create a new
allocation comme `pool.new`without silently choosing another pool or a pool
Heap allocator. The proposal `pool.new(-> copy(original))` is replaced
The local copy does not select any implicit pool.

Rating `copy(tableau)` already retained for fixed inline tables preserved
its status: this existing case must be distinguished from an allocated copy of the
structure with pool origin. The future integration of the two must keep their sources
and transfer rules, without silently changing the tables.

<a id="4-méthodes"></a>

## 4. Methods

The [Rules TF1–TF5](TYPE_FEATURES.md) complete ME1, ME2 and ME4: the
Feature recipients `&self`, `&mut self` and `-> self` exigent respectivement
the concrete read, write-permitted and consuming modes below. Static resolution retains
the effects and origins of the concrete method contract.

**ME1 — Signature of recipient.** A method is declared in `impl Type`.
Its first parameter is `&self`, `&mut self` or a recipient typed as
`self: &Type`, `self: &mut Type` ou `self: Type`.
The rules of the functions apply to arguments, contracts, results, reservations and
cleaning. A method that changes the content requires
mutable access; calculate `self.valeur + 1` without assignment does not change the
field and is not sufficient to justify a mutable signature.

**ME2 — Automatic borrowing of the receiver.** L'appel `point.somme()` can create
A transferable receiver requires the corresponding rights and the observance of
active reservations. This ergonomic exception applies to the recipient only. ME4
governs the transfer of the receiver by value.

**ME3 — Separate field names.** A method cannot have the same name
the type field. `compteur.valeur`/`compteur.valeur()` was rejected:
A parenthetical omission must not produce another valid access to this field. This
decision replaces the original proposal for coexistence of the two names. It does not
in itself define visibility, modules or overload.

**ME4 — By-value receiver.** The signature `fn terminer(self: Compteur)`
declares a by-value receiver. The call `compteur.terminer()` moves
`compteur` into the first parameter `self` under the ordinary argument
rules. The original binding becomes unavailable. Borrowing, provenance,
and cleanup follow the same rules as for any other by-value argument.

A supported primitive receiver follows V3’s implicit-copy rule; by-value passing does not make objects implicitly copyable.

<a id="5-exemples-de-conception"></a>

## 5. Design examples

<a id="construction-défauts-déduits-et-copies-indépendantes"></a>

### Construction, defects deducted and independent copies

```rust
struct Point {
    x: Int,
    y: Int,
}

fn main() -> Int {
    let mut points = Pool<Point>::new(3);
    let original: Point = points.new(x: 10); // y = 0.
    let mut explicite: Point = points.copy(original);
    let abregee: Point = copy(original);

    explicite.x = 30;
    print(original.x);  // 10
    print(explicite.x); // 30
    print(abregee.x);   // 10

    drop(-> abregee);
    drop(-> explicite);
    drop(-> original);
    return 0;
}
```

<a id="référence-partagée-indépendante-du-porteur"></a>

### Shared reference independent of the holder

```rust
struct Vue {
    cible: &Int,
}

fn obtenir_cible(vue: &Vue) -> &Int {
    return vue.cible;
}

fn main() -> Int {
    let mut nombres = Pool<Int>::new(1);
    let mut vues = Pool<Vue>::new(1);
    let mut nombre: Int = nombres.new();
    nombre = 10;

    let vue: Vue = vues.new(cible: &nombre);
    let emprunt = obtenir_cible(&vue);
    drop(-> vue);

    // drop(-> nombre); // Refusé ici : emprunt doit encore servir.
    print(*emprunt);
    drop(-> nombre);
    return 0;
}
```

<a id="méthodes-mutables-et-receveur-par-valeur"></a>

### Mutilable methods and value-receiving

```rust
struct Compteur {
    valeur: i32,
}

impl Compteur {
    fn incrementer(self: &mut Compteur) -> i32 {
        self.valeur = self.valeur + 1;
        return self.valeur;
    }

    fn terminer(self: Compteur) -> i32 {
        return self.valeur;
    }
}

fn main() {
    let mut compteur = Compteur { valeur: 10 };
    print(compteur.incrementer()); // 11
    let resultat = compteur.terminer();
    print(resultat); // 11. compteur a été déplacé.
}
```

<a id="6-principe-dintention-et-méthode-de-travail"></a>

## 6. Principle of intent and method of work

I6 in LANGUAGE_RULES.md records the generation objective by IA:
the intention of the readable code and encourage the refusal of an inconsistent
intention rather than another valid but unexpected interpretation. Mention should be
made of the implicit, fragile notations and effects that require reading a body to
understand a call. ME2 is an explicitly accepted exception; ME3 and ME4 reduce silent
changes of meaning at the site of use.

The existing memory rules apply to structures and methods without being subject to a
new design validation for each variant. Their combinations become test obligations.
Only present new arbitrations in the continuation of the discussion, with first rule
and complete snippet, and without implementing as long as this arbitration phase
remains in force.

<a id="7-points-reportés-et-statut"></a>

## 7. Deferred items and status

- Custom defaults, tags, and custom constructors remain deferred.
- The [destructor method](DROP.md#destructor-method) is implemented for fixed values. See the linked section for its limits.
- Visibility, modules, overload and other method extensions: not defined
  by this site and not necessary to re-arbitrate the common memory rules.
- Complete expression forms and field types of `copy` which does not
  are not yet supported; the distinction between local copy and copying
  in a pool is now defined by ST18.
- ABI, structure alignment, path summary algorithm, protocols
  copying and contract verification: to be implemented and validated at a later date.
- UTF-8 chains: at the time of initial recording, this site was
  The subsequent decisions of 5 November are now proposed only.
  in [UTF8_STRINDS.md](UTF8_STRINGS.md), with the name chosen `str` tiny.

The initial status of ST1–ST18 and ME1–ME4 was **N**. Current coverage
remains partial and is detailed in [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md).
References to already tested rules do not prove their extension to all
The [documentary report]](cycles/STRUCTURES_METHODS_CYCLE.md)
retains the scope of the initial record.

## Tuples

A tuple has two or more elements. Each position has its own type. The
expected tuple type guides inference at each position, including in a
binding, an argument, or a function return. Without an expected type, each
expression follows the usual inference rules. Elements evaluate left to right.

A tuple travels as a single value. A binding such as `let (left, right) = pair;`
consumes the whole tuple and moves its elements into fresh bindings. Each
binding then follows the ordinary lifetime and destruction rules. Grouping
`(x)` and the unit type `()` retain their existing meanings.
