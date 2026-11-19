[Français](GROWING_REGIONS-fr.md)

<a id="crust--data-stacks-valeurs-grandissantes-et-régions"></a>

# Corbo — data stacks, growing values and regions

Design decisions recorded on November 4, 2026, at the request of
This document completes [LANGUAGE_RULES.md](LANGUAGE_RULES.md),
In particular, P1–P8. The initial recording did not change the compiler. The
implementations and checks carried out since are described in
[GROWING_REGIONS_CYCLE.md](cycles/GROWING_REGIONS_CYCLE.md) and
[matrice](VERIFICATION_MATRIX.md), with their investment limits.
The [design document open to contributions](ALLOCATION_DESIGN_BRIEF.md)
presents the investment problem, the input of analysis and the
comparison case.

<a id="1-placement-et-croissance"></a>

## 1. Placement and growth

The prototype distinguishes a classic data stack and a data stack cut into regions.
Fixed-size locations are aligned in the scope range on the classic data stack. A
transferred local value is built in the durable range planned for its receiver. The
child's cleaning precedes the return of its beach to the entry position.

**G1 — Final destination and early placement.** After construction
The compiler tracks the identity of each local value in the run-up static tree. On
each path, it tracks transfers to the last receiver and identifies the clean-up
scope. The destinations that differ according to the path remain distinct in the
result of the analysis.

When a durable area can be reserved from the construction, the compiler places the
value directly in the area of its final destination. Thus, a successive climb can use
a single location. Each child → parent border remains checked. Intermediate links
indicate the same value at the same address. Initialization takes place at the
planned point of execution.

For a new local result built by a function called, the appellant reserves the
location in the area determined by the final destination analysis. The compiler
transmits the address reserved for the function called, which builds the result at
that address at the point provided. The contract distinguishes this construction from
the transfer of an already constructed value, which keeps its address.

When several end-scopes are known, the compiler treats the one receiving the most
values as a priority. It then places as many values as possible directly in their
final scope. This priority applies to investments compatible with the life and
stability of the address.

- **Path chosen before construction.** The plan may include
  one location in each possible destination. Only the path
  run initializes its location.
- **Path chosen after construction.** The plan will be selected from the
  construction of a single address in an area that survives to all
  The scope for cleaning depends on the
  path executed.

Constructions on mutually exclusive paths can share a location if they feed the same
receiver and if the range meets their requirements of size, alignment and life. The
plan reserves this location before entering the chosen path and keeps the site of
initialization unique to each path. Cases where the placement remains undetermined
follow other strategies compatible with the source, size and life.

**G2 — Deux data stacks.** The classic data stack receives the values
of a fixed size, including descriptors of `Vector<T>`, `String` and
`HashMap<K, V>` and pool areas. Data stack with regions
The descriptor is linked to the region where its content is built.

L’annotation globale `datastack` takes place at the beginning of the programme,
before the declarations.
are optional.

```rust
#(datastack: size=4G, region_stack_size=4G, region_size=100M)
```

| Ownership | Size configured |
| --- | --- |
| `size` | Total size of the classic data stack. |
| `region_stack_size` | Total data stack size to regions. |
| `region_size` | Default template for a region. |

Each size s written with a strictly positive decimal integer
follow-up `K`, `M` ou `G`, according to the binary units of G6.
each data stack size and for the region template, the choice
suit cet ordre :

1. Take the explicitly declared size, if provided.
2. Otherwise, take the maximum necessary static analysis
   may establish.
3. Otherwise, use the corresponding default.
   data stack, this is the available memory divided by the number of
   CPU hearts. For a region, it's `100M` (100 Mio).

The measurement of the available memory and rounding of the quotient remains to be
specified. The obtained size sets a reservation limit. The commitment of the pages
follows G11.

<a id="déduction-des-tailles-à-partir-de-larbre-statique"></a>

### Deduction of sizes from static shaft

The calculation uses the [Audit Representations](MEMORY_REPRESENTATION.md#scopes-et-data-stacks).
It follows the execution points and paths of the telescopes, the identities of the
values and the links that keep their storage occupied. Early reservations are counted
as soon as they are created. A transfer keeps the link to the area that survives.

- **`size`**The compiler determines the size and alignment of the
  The following are the fixed values, descriptors and pool areas.
  placement cursor on each path, counting spaces
  d
  The ability is the maximum achieved by the cursor.
  indoor clean space stays in occupied space until
  what a free suffix allows to move the cursor back.
  inherits the still occupied sites in the parent.
  maximum cannot be bounded, the omitted size takes the value
  available memory divided by the number of CPU cores.
- **`region_size`**. The link from the descriptor to the content allows
  the association of each growth operation with its region.
  compiler bounds busy bytes as the operations progress.
  The calculation follows the number and disposition of the items for the
  a vector, UTF-8 bytes for a chain and storage
  entries and index for a hash table. The template
  derived is the greatest need among the content that uses
  the overall template. If any of these needs remains unknown, the size
  omitted takes the value `100M`. Un gabarit local explicite suit G6.
- **`region_stack_size`**. The compiler follows reservations
  d) locations and their recovery in the area stack.
  It counts the reserved locations by a `count` explicite
  The first time they are booked, including those who remain empty.
  a loop, a clean area can be reused.
  retained by a task or thread still alive remains occupied.
  For a uniform template, the reserved peak of locations is
  multiplied by the pitch of a location, including alignment.
  The dedicated area stacks are dimensioned separately.
  the reservation peak remains unknown, the omitted size takes the
  available memory value divided by the number of CPU cores.

An unknown size retains the deductions established for the others. If the number of
locations is limited and the growth
d , a content is not, the calculation of `region_stack_size` utilise
that number with the explicit template or, failing that, `100M`. If the
the size of a region is known and the number of locations is not
can't be bounded, alone `region_stack_size` uses its value by
default.

**G3 — Single-way cutters.** Each data stack and region
has a single allocation front. The cursor moves towards the increasing addresses to
the allocation and can go back when recovering. The placement on two opposing fronts
is postponed.

**G4 — Remaining space and overtaking.** An allowance or an allowance
A request that goes beyond this limit stops the program with a diagnosis. Controls
include size calculation and overlap of locations.

<a id="2-régions-et-intention-du-développeur"></a>

## 2. Regions and developer's intention

**G5 — Region as substack.** A region is a space bounded in the data
An encapsulating stack, with its own growth management and internal cursor. A pool
slot is a block suitable for a type; a region is a substack for growing content. The
reserved size of the region does not vary with the length used of the value it hosts.

A pool of descriptors manages its slots in an area of the classic data stack. The
placement of the referenced content is a regional data stack. The descriptor and its
content keep their addresses when moving between links.

When content grows in a region, `max_size` borne
bytes of this data. Descriptor and metadata outside the region
occupent leurs propres espaces. `Vector<T>` n `capacity`.

**G6 — Setting up the regions of a scope.** L’annotation
`stack_region`, placed before a block, configures the cutting of the
data stack to regions in locations for this scope.

```rust
fn main() -> i32 {
    #(stack_region: max_size=4M, count=8)
    {
        // Huit emplacements de région de 4 Mio chacun.
    }

    #(stack_region: max_size=1G)
    {
        // Autre gabarit : 1G par région.
    }
    return 0;
}
```

`max_size` is mandatory. It sets the template and the maximum size of the
Each region. `count` is a strictly positive decimal integer
Optionally, it sets the number of reserved locations in the scope area. When omitted,
the placement determines the number of locations to be reserved. Locations can
accommodate the contents of several task states or threads simultaneously alive. Each
occupied area counts until its contents are cleaned.
The spaces around `=` are optional.

| Suffixe | Number of bytes per unit |
| --- | ---: |
| `K` | 1 024 |
| `M` | 1 048 576 |
| `G` | 1 073 741 824 |

A strictly positive decimal integer followed by `K`, `M` ou `G` fixes the
limite. Ainsi, `4M` limits the region to 4,194,304 bytes.
the content of the region according to G5 and follows the rules of inheritance and
transfer of G7.

**G7 — Legacy and transfers.** A child inherits the configuration of his/her
The scope uses the default template of the program. An already created region retains
its template and limit when its value is transferred: the receiver configuration does
not resize it and does not move its content. Storage must survive the transferred
value.

**G8 — Regions of the same template managed as slots.** Under one
configuration, each region reserves the same template. This choice makes their
locations interchangeable for this class, even if their contents have different
lengths used. So you can manage regions like slots of a pool:

- prioritise a new region with the cursor encompassing when it is relevant;
- at the limit, reuse a free region of the index of the same template;
- restore a region only after the required cleaning of its contents;
- recover a free suffix by backslide of the cursor including while maintaining
  the consistent index.

```text
Même configuration : 4M par région
[ région A ][ région libre ][ région B ][ espace disponible ]
     4M           4M            4M
                   ^
            index des régions libres
```

A transferred region remains occupied until its value at destination is cleaned.
Configurations of different sizes give different templates; no arbitrary
interchangeability is assumed. Alignment and metadata should allow a consistent no
reservation in each class. The exact class coexistence protocol remains to be
defined.

<a id="3-choix-de-la-stack-et-récupération"></a>

## 3. Picking and Recovery

**G9 — Choice of data stack with regions.** Before construction,
The compiler determines whether the current area stack can accommodate the content
while leaving room for allocations that coexist with it. If placement is possible,
this stack is used according to G8. If coexistence cannot be established or if the
scope requires another template, a dedicated area stack is used. The fixed values of
this scope continue to fall under the classic data stack.

When all the reserved locations by `count` are busy,
A new content can use a dedicated region stack by keeping the same limit per region.
Once the content is built, its address remains stable. A growth that exceeds the
limit of its region triggers the diagnosis of G4.

**G10 — Destruction, sliders and pools.** The destroyer executes before the
Recovery of storage. A scope can restore the positions of its cursors after cleaning
only if no living value is recovered. Transfers prevent blind restoration. A free
area or free slot never reactivates old accesses.

The pool remains a data stack of typified slots with holes, possibly with an index of
free locations. The policy of preference to cursor, re-use at the limit and recovery
of suffixes is retained. The regions take over this organization on the scale of
substacks of the same template. They do not change the rules of destruction and
dependence on the pool.

When a scope launches several threads that use its region, the output of the scope
can bring the cursor from that region back to its position of entry into an
operation, once these threads are completed and their cleaning is completed. Areas
that contain a necessary state, result or data remain reserved. An autonomous thread
that can survive the scope uses a storage that survives it from the start. Recovery
follows the guarantees of RT7 and RT8.

Cleaning uses `drop(valeur)` or the end of the scope responsible.
In multithread context, MT7 requires secure metadata management
shared.

**G11 — Reservation, commitment and performance.** Reserve the capacity of a
The regions and their indexes are a strategy to be measured, without any perceived
gain in performance. Their disposition and policy can be adjusted on the basis of
measurements, without silently changing the explicit limits or observable memory
rules.

`#(datastack: reclaim_threshold=64M, region_reclaim_threshold=16M)`
Configures the thresholds of the classical datastack and the region datastack,
respectively. Each threshold is optional. An absent threshold disables the
corresponding automatic restitution. The units are those of G6. After cleaning and
recoiling the cursor, the runtime restores the free whole pages that it can group if
their volume reaches the threshold. Pages kept below the threshold can be repeated at
a later release.

`#(free_pages)` is written before the braces of a block.
also an annotation `#(stack_region: ...)`This one comes first.
At each exit of the block, after cleaning the values and the retreat of the
curseurs, `free_pages` requests the return of the pages system
The virtual address range remains reserved. Any page that still contains part of a
living value remains accessible, including if this value has been transferred out of
the block.

**G12 — Stability and borrowing.** Neither growth nor transfer nor
Re-use of other regions must not move living elements whose addresses are guaranteed
stable. This stability does not exempt borrowing rules: it does not allow a transfer
incompatible with an active reservation. Contracts must retain dependencies on the
original contents, regions and stacks, including via reference objects and tasks.

<a id="4-limites-et-travaux-reportés"></a>

## 4. Limitations and deferred work

Still to be defined, without changing the above choices:

- the default size calculation details of a data stack;
- the metadata, alignment and page count within the limits;
- the placement algorithm, static/runtime choices and conditions
  triggering the creation of a dedicated stack;
- binary representation of the instalments and the contract of their possible
  interface C ;
- cohabitation of templates from interlocked and transfer telescopes;
- the concrete protocol of regions shared between threads;
- the API of the growing collections and their grammar. `Vector`, `push` and
  `growing_stack` were used as illustrations, no API validated by this discussion;
- cost measures, reserved/committed memory and fragmentation to be performed.

`count` limits the number of reserved locations in the area of
scope. The limit of the number of values simultaneously living is deduced separately,
especially when some use dedicated stacks.

## 5. Statut

The two-data stacks model, one-way placement, recovery after thread cleaning and
annotations
`datastack` and `stack_region` are decisions of specification.
compilateur historique conserve l’annotation
`#(directive: stack_region_max_size=4M)` and its storage routes
existants.

G1–G12 are design decisions, **not implemented and not verified by
execution in this pass**. Historical tests of fixed slots do not prove
not the recovery of regions after the threads clean up.
future validation are in [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md),
and the documentary scope of the cycle in
[GROWING_REGIONS_CYCLE.md](cycles/GROWING_REGIONS_CYCLE.md).
