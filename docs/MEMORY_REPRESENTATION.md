[Français](MEMORY_REPRESENTATION-fr.md)

<a id="représentation-mémoire-du-vérificateur-crust"></a>

# Presentation of the Corbo Auditor's Memorandum

This document describes the auditor's design model. It evolves with design decisions
and their integration.
are defined in the [core rules](LANGUAGE_RULES.md#noyau-mémoire--grille-de-lecture).

<a id="arbre-statique-dexécution"></a>

## Static tree d'execution

The tree interlocks the telescopes and carries their operations in the order of
evaluation. Links link the operations to their inputs, results and possible sequels.
A relevant token can be represented by the role it gives to a node or link.

A link has its own identity, name, scope of declaration, type and mutability. Its
state by path indicates the entity that it
means and its condition `Disponible | Déplacée(PointExécution)`. The point
The original scope retains this state after the child has left the home. At a
junction, each state and its point remain associated with the paths that produce
them. A link can also designate a pool. A name usage retains the identity of the
resolute link. A displacement keeps the identity of the displaced entity and connects
the source link to its destination. A new connection of the same name has its own
identity.

The placement analysis takes place after the AST and the resolution of the transfers
in the static tree. It links each value identity to its last possible destinations,
with the associated path and cleaning scope. The placement plan can link several
exclusive construction sites to the same location when they supply the same receiver.
The construction site remains unique to the path executed.

A statement of function bears its signature and its body scope. A call carries the
resolved target, the arguments in their order of evaluation, their correspondence
with the parameters and the destination of the result if it is received. The static
body is shared. The call link places the activation in the calling scope. An external
signature carries
ABI. `unsafe` carries the lexical context of its operations.

<a id="provenance-et-résumés-dans-le-post-ast-rust"></a>

### Source and summaries in the post-AST Rust

In a function, `Value.temp` identifies a value of the post-AST.
`Value.provenance` connects a reading to its link, a local displacement
the connection and the node that triggers it, and a receiver at its temporary source.
When a receiver can be fed by several paths, the
Bone `Receive` ou `Break` carry the sources.

The summary of dependencies of the `Value` reference of interned lists
It distinguishes the dependencies of the value and the dependencies that a future or
a handle transmits to its result. A block-to-single-source transition uses the same
summary identifiers. A junction of paths combines the origins of the possible
results.

The placement calculates its own abstracts by temporary. It propagates the sources of
storage along the links, receptions and call contracts. Each selected construction
origin refers to a reserved location in a post-AST scope or a location provided by
the caller. Exclusive paths can share the same destination. Both analyses re-use the
summaries already calculated through the telescopes.

The post-AST program also contains the aggregates possession plan. Each entry
describes the fields owned, the elements of an array or the fields of each variant in
the cleaning order. A link to an incorporated aggregate continues the course in its
plan. A link to a slot passes the relay to the children's registry of the runtime,
which renders the descendants before the parent slot. Generator C translates these
links into access to the fields and calls to the runtime. Adoption and transfer
consult the same plan to choose the possession route to be applied to the transmitted
value.

For scalars, the plan goes up the moved links to the initialization site.
Intermediate links can designate the same reservation as the final receiver. If
several paths transmit a value, they can share an address that remains accessible to
all their receivers. The selection of shared locations of aggregates deals first with
the telescopes that have the most candidate construction origins.

A Future result can be built in the result field of its frame. A scalar expectation
can write directly in the receiver's reservation in the current frame. The link
pointers thus placed stay in the frame during the suspension. The runtime follows the
logical scope of possession of pool slots regardless of the address chosen by the
placement.

<a id="identités-places-et-valeurs"></a>

## Identities, places and values

An operation carries a point of execution, its scope, its ordered operands and its
possible result. A fact still to be solved keeps its entries and its role. For
example, a method call carries the receiver, the method name and the arguments before
the concrete method and its effects are known.

A place describes a root and a series of projections. The projections identify an
indirection, a field, a variant, an index, a key or a range. Unresolved indices, keys
and bounds retain their expressions. An omitted terminal retains its implicit
terminal role. A reference to a part of the root retains the projection with the
target. A writing also retains the assessed place and, for a composite operation, the
operator and the operand on the right.

A literal retains its value and its category. For the text, the value is the sequence
of decoded UTF-8 bytes. For a type written in a signature, link or construction, the
path and its arguments remain distinct. A conversion carries the source value, the
type requested and the form of operation. A literal array carries its expressions in
the order, or an expression and its number of repetitions.

## Adresses

An address symbolically identifies a location. A borrowing location can receive an
identity even if the code generator determines its physical position later. Reusing a
slot creates a new identity for the new allocation.

```text
Adresse {
    id: AdresseId
    type_concret: TypeId
    pool_source: Option<PoolId>
}

ÉtatAdresse {
    scope: ScopeId
    owner: Option<ElementId>
    vivante: bool
}
```

The scope indicates the connection of the allowance for cleaning.
`owner` identifies the link or collection responsible for this cleaning.
For a live address without owner, this charge goes directly to the scope. A move can
change the owner and the scope. The allocation retains its original identity and
pool.

Un `ElementId` identifies an address, reference, collection or
a link, depending on the field that uses it. Each state describes the facts
established on the paths that reach the point analyzed.

<a id="références"></a>

## References

```text
Référence {
    id: RéférenceId
    type_concret: TypeId
    mode: Partagé | Mutable
}

ÉtatRéférence {
    scope: ScopeId
    owner: Option<ElementId>
    origines: Ensemble<Origine>
    active: bool
}

Origine {
    cible: AdresseId
    projection: Suite<Projection>
    parent: Option<RéférenceId>
}
```

A reference is a value in its own right. Its scope and owner describe its current
connection, regardless of the connection of its target. The reference may belong to a
link or to a capture field. A displacement retains its identity and origins, changes
its connection according to the destination and makes the source link unavailable.
The target keeps its own scope and its own owner.

The parent designates the borrow from which a reborrowing takes place. The auditor
follows this relationship to suspend the parent's incompatible uses. At the junction
of paths, he retains each target and parent couple.

## Collections

```text
Collection {
    id: CollectionId
    type_concret: TypeId
    adresse: Option<AdresseId>
}

ÉtatCollection {
    liens: Ensemble<Lien>
    contraintes: Ensemble<Contrainte>
}
```

A possession link links the collection to a value that it must clean. A borrowing
link retains the source of a reference received or places the area borrowed by a
reference from the collection. A linked element may designate an address, reference
or other collection.

The representation can be partial. The operations create the links useful for the
verification and specify their position when it is known. An index, key or field can
be solved in the internal position. An uncertain position represents the possible
areas. The length of a fixed table is sufficient to control its terminals, even with
an empty set of links.

A pool instance carries its identity, its scope, its element type and its capacity. A
construction via this pool links the initialization to the resolved instance and to
the new address. The displacement of the value leaves this link of origin in place.

A collection with variants carries the discriminant and fields of the
variant present on each path. `match` bear the motive,
The positions of a collection keep their source selector as long as they do not have
a resolute internal position.

<a id="scopes-et-data-stacks"></a>

## Scopes and data stacks

```text
Scope {
    id: ScopeId
    parent: Option<ScopeId>
    enfants: Liste<ScopeId>
    liaisons: Liste<LiaisonId>
    entrée_parent: Option<PointExécution>
    sorties: Liste<SortieScope>
    zones: Liste<ZoneStockage>
}

ZoneStockage {
    datastack: DataStackId
    région: Option<RégionId>
    borne_inférieure: Position
    borne_supérieure: Position
    curseur_parent_à_l_entrée: Position
    curseur_relatif: Décalage
}
```

The entry point places the scope in the order of execution of the parent. It
identifies an operation or a boundary between operations and can be reached by
several paths. The cursor mark retains the parent's theoretical position on the entry
path. A position can be symbolic. Each area carries its terminals and cursor mark.
The offset is zero at the entrance. At the exit, the marker allows the release zone
to be recovered. A still required location limits the step back. The anticipated
placement in the parent's area can allow the child to recover the entire area after a
transfer.

The fixed descriptor is attached to an area of the classic data stack. Its storage
link identifies the region of the content in the data stack to regions. An area used
by threads carries dependencies to their states until they are cleaned.

The [dimensioning]](GROWING_REGIONS.md#déduction-des-tailles-à-partir-de-larbre-statique)
uses three families of facts in this representation. The concrete type provides the
size and alignment of a fixed location. The descriptor link → region combines growth
operations with the storage they occupy. Reservations, outputs and life links
indicate when the locations of the regional stack are retained or recoverable.

The last expression of a block produces a value on the normal output. The semicolon
point of an expression instruction indicates an output without the result of this
instruction. Border operations describe the links and responsibilities that change
there.

## Valeurs appelables

A closure has a concrete type of instance, a signature, a body and capture links to
resolved external links. A capture identifies its source link, the destination field
and the entity placed in this field. Creation and call have execution points
distincts. Le marqueur `move` s’attache à la création de l’instance.
The field becomes the owner of the transferred value, including for a
shared reference. The source link goes to `Déplacée` at point
creation. The capture link bears the presence of the marker and the actual mode when
it is established. For an external occurrence without marker, it retains the source
and field even if the actual mode is still unknown.

<a id="tâches-attentes-et-contrats"></a>

## Tasks, expectations and contracts

An async definition carries a signature and a static body. An instance bears its
identity, definition, captures, source of storage and links to its result and
cleaning. A suspension point carries the point of recovery and the entities retained.
A launch connects the task to the branch and its handle. A wait carries the expected
entity, the point of recovery or continuation and possible outcomes. A result outcome
retains its discriminant and the effects associated with the corresponding path.

The annotations bear their target and their properties. A type contract retains its
parameters, the types allowed and the signatures of the required methods. A branch
contract connects the end to the operation expressed on the result, when it is
written. A lock contract carries the target of the exclusivity and, if indicated, the
link that extends the duration of the result. A capacity directive retains the path
of the definition and the declared value. A region annotation retains its scope, its
limit, its unit and the optional number of reserved locations.

<a id="exemple-de-transfert-de-responsabilité"></a>

## Example of transfer of responsibility

In a `HashMap<i64, A<i32>>`, we insert `a` with
`table.insert(copy(cle), a)` Then we take it off with
`table.remove(&cle)`. The explicit copy keeps the link `cle`.

| Moment | Scope of the allowance | Owner | Link of possession |
| --- | --- | --- | --- |
| Avant l'insertion | Scope principal | Liaison `a` | `a` holds the allowance. |
| After insertion | Scope principal | Collection | The collection holds the allocation under the key. |
| After withdrawal, in `Some(recu)` | Arm Scope | Liaison `recu` | `recu` holds the allowance withdrawn. |

The original pool must remain valid at all three stages. If the table is moved to
another link, its collection identity allows you to find the same possession links.

The basic storage identifies the pools needed for the holder himself. The proprietary
fields and entries add their own links. The removal of a link can remove its origin
from the carrier if the base storage is known and no other link holds this pool. An
unknown base source requires the possible pools to be kept.

<a id="jonction-de-chemins"></a>

## Junction of roads

A receiver may designate a different allocation depending on the path. A condition
links its expression to the possible inputs. A junction binds each input to the
result or state it brings. An early output indicates the function or loop it aims
for.
indicates its point of return and the telescopes left. `while`, ce
point is the evaluation of the test.

An assignment identifies the target place and the value evaluated on the right. Its
ordered operations distinguish writing from content and replacing a value. For a
replacement, they retain the old identity until the evaluation of the right result,
then connect the cleaning of the old value and the installation of the new one.

Cleaning uses the path allocation executed. The analysis retains the possible
dependencies of these allocations, including pools, locks and writings that a value
can transmit to a delayed result. When several paths carry updates, the junction
keeps their possible effects without treating them as a certain single effect.

This merger also applies to the value produced by a `match` ou
un `break` and representations of a charge extracted from a
collection. When a loop resumes, the compiler compares the sources and variants of
the deferred result, including those of its fields. For an origin created during
iteration, it compares its known source in order to remain independent of the
identifiers recreated by the analysis.

For a deferred writing, the comparison includes destination, dependency and
possession ties and parents borrowing. Locked writing also identifies the protected
load. When the positions of a collection are known, the comparison includes their
sources and sources. For effects whose exact execution is established, it retains
order and multiplicity.

The life control follows the value that a write can install, its descendants and its
delayed effects. A kept write keeps the lock, the protected load and the targets that
its new links must keep alive.


## Self-hosted summaries: parameter storage and constructor inputs

A slice parameter has two identities: the movable local binding and the
symbolic caller-owned storage it denotes. The latter is represented by the
parameter's unique type-annotation node. Moving the binding changes its local
state without killing that external storage identity. Return-contract analysis
normalizes the storage identity back to its formal parameter when mapping it to
an actual argument.

A constructor result keeps the constructor shape and the correspondence between
formals and actual arguments. Its argument-list marker separates evaluation
inputs from retained dependencies. All arguments are checked during the call;
only arguments moved into reference fields remain dependencies of the result.
A borrowed input used to compute a scalar field does not extend its borrow to
the result's lifetime. Liveness, scope survival and pool-dependency traversal
consult that same retained-field mapping, including after an async constructor.

During lowering, an expression-type cache records already evaluated temporaries.
An early `?` return walks the enclosing evaluation order backwards to clean up
owned earlier operands, then uses ordinary visible-binding cleanup and scope
unwinding. This cache is lowering metadata, not a substitute for the dependency
and placement summaries.

## Caller-owned result graphs

`Value` summaries are instantiated for each call. A tuple preserves its ordered
shape and points to an immutable field map; each map entry associates a template
field or position with its own caller-side value. Record fields recursively use
the same map. Moving the tuple or destructuring it changes binding availability,
while retaining those value/dependency identities. A second call cannot overwrite
the first call's referents by mutating the callee's field nodes.

A relay adds a formal-to-actual environment. Resolving a returned field follows
that environment and projected place back to caller storage. Borrow-bearing
owned parameters have distinct symbolic external roots for their reference
fields; borrowing the parameter's own inline storage still does not permit that
storage to escape. Deferred task captures retain the instantiated aggregate graph,
and ordinary loan, scope and cleanup walks follow its edges. Dependency-free
owned records do not create an external lifetime obligation merely because they
were passed into a task.

The current compact verifier stores these immutable maps/environments in a bounded
summary arena above the source-node range of `CheckedValue`. Arena entries use
explicit marker kinds and never alias source fields; exhaustion produces an
unsupported-analysis result. This is compiler storage, not runtime allocation.
Concrete generic nominal instances are separately interned by template and the
complete concrete argument list, including nested instance identities. Dependency
selection uses the source occurrence as well as the enclosing specialization.

## Literal bounds and bounded inline text

The active compiler preserves a literal generic argument as AST kind 94 with its
source span. It is a bound, not an i64 value expression. Generic specialization
substitutes that bound into the ordinary fixed-array member of the STD template
selected for `String<N>`. Equivalent integer spellings share type identity.
No new ownership entity is introduced: the specialized record uses the existing
Value provenance, placement and dependency summaries. A borrowed payload of A<T>
targets the allocation binding, preserving its source pool and lifetime; a text
view returned inside Result retains the same source root as a direct view.
Private generic-layout metadata is attached to each generated concrete declaration
and its implementation, rather than to an erased template’s output offset.

See [integration evidence](cycles/BINARY_TIME_BOUNDED_CYCLE.md).
