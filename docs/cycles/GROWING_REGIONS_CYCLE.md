[Français](GROWING_REGIONS_CYCLE-fr.md)

<a id="cycle-documentaire--data-stacks-et-régions-grandissantes"></a>

# Documentary cycle — data stacks and growing regions

Date : 4 novembre 2026.

Documentary correction of 5 November 2026: the name chosen for the annotation
is `stack_region_max_size`The normative examples, P2 and line G6 of the
have been harmonized, without changes in behaviour, heritage or
no code or test modified by this renaming.

<a id="portée-demandée"></a>

## Scope requested

Record validated decisions, then resume the next project without
Implement. AGENTS.md and VALIDATION_GUIDELINES.md have been read. This cycle is
Documentary: No compiler, runtime, test or executable example modified.
It is not a complete cycle of language validation according to the guidelines.

<a id="résultat-documentaire"></a>

## Documentary result

- GROWING_REGIONS.md: 12 G1–G12 identifiers, decisions and open questions.
- LANGUAGE_RULES.md: normative integration and clarification P2/P5/P7.
- README.md: link and distinction between design and implementation.
- VERIFICATION_MATRIX.md: future obligations for each identifier, status N.

The choices are growth at the top when it suits, two opposite sliders,
regions of the same template under inherited annotation and the use of a stack
dedicated if current placement is not suitable. The maximum region is distinct
the maximum stack; the transfer keeps the template and does not move the value.
The regions re-use pool slots without re-introduce.

<a id="interactions-et-contre-exemples-à-vérifier-ultérieurement"></a>

## Interactions and counter-examples to be verified at a later stage

- Construction after early booking: do not advance its effects.
- Restore a child's cursors while a region has been transferred:
  would invalidate a living allowance and must be prevented.
- Transfer from a 4M configured scope to a 1M configured parent: do not reduce
  the region or move its content; maintain its storage dependency.
- Growth calculation including alignment: two cursors apparently separated
  However, they may not leave enough space; refuse before writing.
- Reuse a liberated inner region and reuse its entry
  index after cursor step: Never assign twice the same space.
- Annotation provides one size per region, not a population boundary
  living; not deducing sufficient total space without further analysis.
- A free space of a different template is not automatically reusable
  like a slot on the current template.
- Exceeding an existing area: do not bypass the limit by moving
  its content on a new stack; do not confuse this case with the choice
  initial of a dedicated stack.
- Access via a loan, reference object or task: preserve targets, sources,
  exclusivity and stability despite growth, transfer and re-use.
- Competitive allocations/liberations: regional/slot policy does not replace
  not the synchronization protocol required by MT7.

These scenarios are the result of the literature review.
a counter example executed on a region implementation.

<a id="questions-laissées-ouvertes"></a>

## Questions left open

M/G units, default sizes, alignment and metadata, representation
downhill, co-existence of templates, static/runtime investment decision,
creation and life of dedicated stacks, and API collections remain to
define. No performance gains are asserted; measures will be required.
The proposed initial rule for structures is not validated by this cycle.

<a id="vérifications-et-limites"></a>

## Verifications and limitations

A documentary check checks the identifiers, their correspondence
in the matrix, local links and balancing of the blocks of code.
Not valid for semantics, Markdown anchors, or snippet compilation.
Completed: 12 unique identifiers, 12 lines corresponding to status N,
145 local links to existing files and balanced code blocks in
the five documents concerned.

Programs executed, new acceptance/refusal tests, independent models,
random generation, mutations and sanitizers: none in this pass.
The twelve rules are not implemented and not verified by execution; the
historical proof of the fixed slot pool does not cover these extensions.

<a id="primitives-des-deux-fronts-dans-le-c-émis"></a>

## Primatives of both fronts in the C emitted

The runtime issued by Crust has `GrowthStack` and `GrowthSpan`.
A stack reserves its range with the existing mechanism of `source_stack`.
A front is associated with a C descriptor with a stable address.
checks alignment and reserves only the padding that holds in
l-space available. An extension checks the number of elements per
before calculating the number of bytes. An internal failure leaves
the sliders unchanged. The return of the front to its initial slider
preserves the other front. A closing with a living forehead or a
A copy of the descriptor returns a diagnosis.

This choice of representation is internal. The C returns the address of the
added block, including the down front. The future collection
must define the logical order of its elements and call for restitution
after cleaning. The cycle does not fix ABI collection, or
auto placement policy, nor source API. It does not measure
the number of resident pages.

`test_growth_runtime` compares operations to a Python model by
intervals, with 180 transitions generated by seed 2219.
controls the addresses and live bytes, then the exact fit,
alignment, extreme claims, restitution and both
The test and the two oracles UTF-8 passed under Clang
C11 and UBSan blocking, at `-O0` and `-O2`. Three mutations in C
temporaire ont été détectées aux deux niveaux, refus erroné de
exact fit, no low cursor restitution and
acceptance of a descriptor copied to grow.

The 140 regressions of the previous UTF-8 cycle have been successful.
fixed tables, destruction and pool requirements are restarted
on the C which includes these primitives.
fixed-size substacks and their re-use indexes,
transfers and collections borrowings remain to be integrated.

The 103 tests of this regression fixed tables, destruction and
Pool requirements have successfully completed.

<a id="régions-bornées-dun-même-gabarit"></a>

## Regions bounded by the same template

Runtime C combines a slot beach with a class of regions.
Each region has a fixed capacity, a single length used
and a descriptor with a stable address. The limit counts bytes
The header and the placement padding remain outside the
the internal representation limit. The step is aligned with
`max_align_t`. The descriptor is associated with its slot, which prevents
a copy of the descriptor to extend or return the region.

The placement re-uses the slot logic of existing pools.
It prefers the cursor, consult the index when the beach is
full, then remove from the index the slots recovered by recoiling the
cursor. Content grows in its own region, without moving
the existing bytes. The code using the runtime should clean up the
elements before returning the slot. The class has its own range
virtual. Coexistence with other classes and with both
fronts, as well as automatic placement from a scope, remain
to be integrated.

Both tests `test_growth_runtime` have passed under Clang C11
and UBSan blocking to `-O0` and `-O2`. The regional model uses
220 generated transitions, seed 6077, and compares slots,
the cursor, addresses and bytes still alive.
deterministics cover the exact limit, the exceedance, the
premature closure and a copy of a descriptor. Three mutations of the C
temporary are detected at both optimizations, overuse too
early in a hole, suffix left in index and refusal of size
exact. Fixed array regression tests, destruction and
pool requirements are restarted after sharing logic
- I'm not.

The 103 tests of this regression were successfully completed.

<a id="configuration-lexicale-et-placement-de-secours"></a>

## Lexical configuration and backup placement

The parser recognizes `#(stack_region_max_size=4M)` avant un bloc
instruction or expression. The compiler transmits the limit to the
children's lexical telescopes, allows local replacement and restores
the limit after the block exit. A function retains its
lexical configuration when called from an annotated block.
The prototype temporarily interprets M and G in 1024 powers,
with a calculation terminal of 2^63−1 bytes. These implementation choices
do not set normative units or future accounting
metadata.

The issued C proposes two internal investment entries.
he tries the low forehead then the top if there is still enough to place a
element, then a dedicated stack whose capacity is provided by
The caller of the runtime. With a template, he tries a pool of regions
compatible, then a dedicated pool of only one region of the same size.
The choice is made before the content is opened.
later fails on the chosen range. Placement and annotation
The compiler still has to link the
configuration of the scope to the storage of the collections it emits.

Five targeted tests have been successful.
legacy, branches, block expression, isolation of call
and six invalid forms. `-O0` and `-O2`
check both fronts, the border of the dedicated region, the
Reuse of the pool and preservation of live addresses.
The test detects a mutation that allows reuse of a
incompatible template. The scope test also detects the legacy
wrong configuration of the appellant.
conditions, if expressions and destruction are reinvigorated.

The placement is now connected to the `String` and at the limit of
construction scope. The report [UTF8_STRINGS_CYCLE.md](UTF8_STRINGS_CYCLE.md)
details the provisional capacity choices, transfer and
destruction checks.

<a id="rétablissement-du-test-lexical-g6g7"></a>

### Re-establishing the G6–G7 lexical test

The overall follow-up reported an error reproduced by
`python3 -m unittest discover -s tests -p test_growth_annotations.py -v`.
The ScopeRecorder.statements test overload failed with
TypeError when the compiler was forwarding expected_array.
It now transmits the parameters of the basic method.
The assertions on boundaries, scopes and inputs
disabled persons have been retained.

`python3 -m unittest discover -s tests -p 'test_growth*.py' -v`
has passed 20 tests. Native tests of this suite use
C11 with fatal UBSan at -O0 and -O2. Both annotation tests
have also succeeded after the final alignment of the signature.
This correction restores a G6–G7 check of the compiler
without changing the investment policy.

<a id="alignement-des-régions-dans-une-réserve-de-capacité-impaire"></a>

### Alignment of regions in an odd capacity reserve

L-oracle G4/G8 sharing a reserve between a class of regions
and two fronts were replayed with increased logical capacity
d-a byte. Prior to correction, UBSan reported access to a Cell
misaligned to -O0 and -O2. The backend mmap rounds the pages, but
The research of the regions is based on logical capacity.
line its high terminal before calculating the address of the
The other classes remain aligned because their steps
And their limits are already. The test also checks the collision,
addresses still alive and re-use after cleaning.
The initial counter example detects the removal of this alignment.

The suite also reproduced a TypeError in the observer
Annotations. The test now transmits arguments
The auditor shall have the right to make a declaration of compliance with the requirements of the Act.
The assertions on the legacy and isolation of the telescopes are intact.

The native case G4/G8 and the filter of regions of fundamental rules
The odd capacity is exercised via the runtime C emitted.
The default capacity of the collections in Crust remains a multiple
page on the tested configurations.

Next `test_growth*.py` passed his 20 tests after correction.

<a id="réservation-anticipée-avec-des-trous-au-curseur-maximal"></a>

### Early booking with maximum cursor holes

G1/G8. The transfer reservation includes free places
of the descriptor pool and the class of regions, including
the holes in their indexes. It only anticipates if the number
space requirements remain available for temporary workers.
The ordinary allocation path continues to favour the
slider as long as there are slots beyond.

L-Oracle C fills a pool and its class of regions, then
free two indoor slots. A reservation that should
The one who has to leave two places is refused.
one uses the first hole, then the temporary uses
The test checks the addresses until the cleaning.
It passes under Clang C11 with fatal UBSan at -O0 and -O2.
Two mutations recalculating the available capacity from
of the slider alone cause the oracle to fail on both levels.
The selection of reservations issued by the compiler
passed five tests. The anticipated re-use of both holes
is exercised directly via the issued runtime C.

Next `test_growth*.py` passed 21 tests.

<a id="placement-anticipé-autour-dun-push_str-littéral"></a>

### Early placement around a literal push_str

G1/G8. Crust program with three Thongs and two holes
The reservation tested in the C
was not issued as soon as a construction was followed
d
a literal push_str on a String built in the
The operation remains in its place
The planner keeps the placement in the generated program.
ordinary for a push_str whose argument is a view.

The counter-example failed on the order of the holes' addresses
before correction. After correction, under Clang C11 to O2 and
UBSan fatal, temporary and transferred value occupy
each place expected. The value keeps its address
the transfer. The program displays the content transferred and
The case with a view taken
checks the order of allocation of the regular placement and the
The same content. L-oracle C of the previous cycle covers
separate address of content in the region.

The compiler reservation and growth filters have
passed 6 and 21 tests respectively.

<a id="réservation-anticipée-à-travers-un-match-nominal"></a>

### Early booking through a nominal match

G1/G8. A non-consumer match can share a reservation
The plan holds the manufacturers
and their temporary, and requires a common source.
The links of the fields of the arm hide the names of the outside
during this search. The construction remains in the chosen arm.

The source test executes both variants and verifies that the region
of String is anticipated, that the descriptor precedes the temporary
and that the address and content survive the transfer.
space available, temporary is built before diagnosis
on the next manufacturer. With different pools depending on the
the test executes the ordinary placement.
use clang C11 to O2 and fatal UBSan. On temporary copy,
ignoring the match in the plan makes the verification of the
Two variants. Mutation detected. The reservation filter of the
compiler passed seven tests.
out of this plan because they can free the slot from the subject.

The growth suite passed 21 tests.

<a id="string-sur-les-deux-fronts"></a>

### String on both fronts

G2–G4, G9, G12 and TX. Thong now shares the placement
The views take up the two fronts of the other collections.
The text is already provided for by CrustText. The cut and readout follow
The pop decodes in this order.
first valid the forward-looking text, then write the bytes according to
the meaning of the destination. Early booking can be
use the down front for a String with a temporary.

L-placement oracle controls two Strings in the reserve
shared and a third on a dedicated beach.
the bytes and stable address of the first byte after addition.
The replacement Python model, seed 3581, replays its
183 cases on the region and on the down front, then exercises
an addition and a pop of a tank on four bytes. Both
oracles pass under C11 and fatal UBSan to O0 and O2.
Force the ascending direction in the view is detected at both
optimizations. Source test checks a transferred String
from the reserved front, its cutting, pop and content.
The basic growth suites, UTF-8 and String
passed 21, 27 and 15 tests respectively.
covers internal operations on views, independently
d) a possible representation exposed to native C.

### Emprunt async d’un String descendant

G12 and AS12. A test from end to end builds two Strings
without annotation in the same pool. A task receives the view
of the second thong, suspends his execution and returns a
cutting at the border of a UTF-8 character. The first
Thong can grow while borrowing is booked.
The growth of the second is refused before join and before
the last use of the cut. After this last use,
The drop then allows re-employment
from the second thong slot, with conservation of the first.

The target case is successful under C11 to O2 and fatal UBSan.
On temporary copy, delete the orientation of the view made
fail cutting while performing the worker. Mutation
The test exercises a view-sharing between threads.
It does not cover the competing transfer of two collections
A frozen copy executes the overall suite and records
its output in /tmp/crust-desc-string-regression.log.

The UTF-8 async filter passed 17 tests.

<a id="métadonnées-de-croissance-partagées-entre-threads"></a>

### Growth metadata shared between threads

MT7 and G10. In multithread mode, a lock protects the
reservation, placement, growth and release
which modify common cursors or classes of
The order is lock of growth then lock of
slots. Cleaning of the detained elements before taking
The bytes remain protected by the growth lock.
Crust's access rules, and lock is released before
copying bytes to an allocated range.

L-Oracle C repeats 30 fills of two fronts in a
The reserve of 257 bytes. Checks the exact total and absence
d
creation, growth and release by thread in two
regional templates. It passes under C11 clang with UBSan
The harness adds a yield between the
capacity control and cursor movement for
to promote interlacing. By removing the lock,
UBSan reported an overflow of the pointer calculation.
Mutation detected.

ThreadSanitizer has been tried. The binary instrumented
ends with SIGSEGV, including an empty hand.
There is therefore no exploitable ThreadSanitizer result.
L-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O-O-----------------------------------------------------------------------------------------------------------------
d    , a collection held by the author remains to be implemented on the language side.

The growth sequence passed 22 tests.
Crust borrowed from the downhill thong after join also succeeded.

<a id="correction-du-placement-de-string-selon-tx21"></a>

### Thong placement correction according to TX21

The rereading of FOUNDATIONS_AND_VECTORS.md revealed a deviation
with TX21. This rule requires adjacent Thong views in
the direction of the increasing addresses.
placed the second thong on the down front.
successful of this extension validated its internal behavior
but not its compliance with this normative requirement.

The String construction uses the up front again,
a region or a dedicated stack. Early booking chooses
a dedicated stack when its temporary uses the up front.
Placement L-oracle checks that two unannotated T-strings occupy
a shared up front and a dedicated up front.
the downward sense of the word continues to exercise Vectors and their
internal views, the orientation of which is explicitly represented.
The async test on the second String is renamed to reflect
its dedicated storage. Its borrowing obligations remain exercised.

Obsolete historical status of the matrix and document
async have been brought closer to their current lines and reports.
No standard rules for placement are amended.

After TX21 correction, the growth suite passed 22 tests.
The source of Thong's reservation scenario and the duration scenario
of his life async view also succeeded.
Reactivate the downward placement of String makes the oracle fail
At O0 and O2. Mutation detected. Downward model tests
Now explicitly use Vector<u8> in this case.
