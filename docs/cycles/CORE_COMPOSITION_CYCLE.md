[Français](CORE_COMPOSITION_CYCLE-fr.md)

<a id="cycle-dintégration-des-compositions-du-core"></a>

# Cycle of integration of core compositions

<a id="comportements-intégrés"></a>

## Integrated behaviours

- A closure retains the source of a local scalar reference or a
  pool. A shared capture copy the reference. A mutable scalar capture
  by `move` invalidate the original connection. A closure can be passed to a
  specialized async function and keep a shared loan through `yield`.
- Un wrapper synchrone `branch` peut retourner un handle choisi entre plusieurs
  The public contract is used for the recognised scalar branches.
  the proof that allows the auditor to accept the abandonment.
  the slot at the end of the task, while the context is active.
- A function contract can relay insertions of scalar references
  shared in a `HashMap` by constant key. Upon appeal, the verifier
  updates the input dependencies and retains the alternatives of the
  Conditional writing.
- A ticket that wears a lock remains active in a proprietary field
  returned by a function, or in the result of `Vector.pop()`. The arm
  `Some` transfers ticket and arm `None` Turns off empty option.

<a id="vérification-ciblée"></a>

## Targeted verification

The pass to `-O0` completed 37 successful tests. `-O2` a
completed with 101 successful tests and also covers the capacity async, the
obligations of the handle, vector options, digital typing and
The native controls of these modules use UBSan. Cases of refusal include:
a writing before the end of a captured loan, a HashMap dependency that
He'd escape his target and a second lock from the same lock during life.
A C-witness waits for the task pool to become empty again before the
Close the context.

<a id="limites-observées"></a>

## Observed limits

- The follow-up to the `branch` covers recognized synchronous bodies and evidence
  scalar. Generalization of N4, ability with repeated abandonments
  and the distinction `Handle`/`AsyncHandle` in signatures remain open.
- Non-scalar mutable catches, composition between parameters
  the closure and type contracts, and verification of unused templates to
  signature non scalaire restent ouvertes.
- Other effects on HashMap inputs dependent, operations
  directly in async, nominal references per entry and acquisition
  direct from an async lock remain to be connected.
- `SelectGroup` is carried forward according to the perimeter decision.
  Targeted regressions and leaving the independent audit separate.

<a id="suivi-du-typage-des-handles"></a>

## Tracking of handling

RT4 confirme que `spawn` and `thread` retournent `Handle<R>` since both
contexts. The digital profile keeps the handle family launched during the
a displacement, a conditional result and a `break`. Branches
The historical profile keeps
its annotation `Handle` for `spawn_blocking`.

Scalar evidence can cross several annotated wrappers `branch`.
The link must lead to a known launch. A relay without known contract
The transport of a `AsyncHandle` by signature and calculation
capacity with repeated abandonments remain open.

The target regression of this monitoring is to `-O0` 8 tests) and `-O2`
(24 tests, including public contracts and the obligations of the handlers).
C-tests use UBSan. Negative checks include
the mixture of families in a `if`an incompatible annotation after
transfer, and the absence of a contract on the relayed launcher.

<a id="composition-entre-closures-et-contrats-de-type"></a>

## Composition between closures and type contracts

In a unit with type contracts, the compiler resolves calls
before specializing the closures and then recording their
structures generated. A closure called several times can transmit
its shared reference to a contract function of type.
valeur non `Copy` exige toujours `move`.

The pass to `-O0` covers 15 tests on closures and type contracts.
The pass to `-O2` The other forms of capture and the use of the data are:
Unused non-scalar signature templates remain open.

<a id="paramètres-asynchandle-et-tableaux-indépendants"></a>

## AsyncHandle settings and independent tables

The transfer of a `AsyncHandle<R>` stand-alone to a function parameter
async consumes the caller's connection. The handle is stored by value
in the status of the task and can be expected by the recipient.
is destroyed before its first poll, its destroyer resumes the cleaning
The failed launch case keeps the error until the wait.

Proof of autonomy also admits captured fixed digital arrays
by value. A borrowed table keeps the waiting obligation.
under repeated abandonments remains open, as the handle parameters to
dependencies and hand returns from async functions.

The targeted suite is now `-O0` (10 tests) and `-O2` (66 tests).
d'`AsyncHandle` covers success, `LaunchFailed` injected at launch
The auditor refuses to accept the
wrong type of handle, second consumption and capture of a handle
with borrowing in this perimeter.


<a id="capacité-des-boucles-et-lecture-de-hashmap-par-contrat"></a>

## Loop capacity and HashMap reading by contract

When a loop has a path back, the compiler compares the pools
in which it can create and abandon a task.
requires explicit capacity. The effects of synchronous auxiliaries
through their contract, and the contract `branch` keeps the pools
a loop block that immediately exits the backhand.
by `break` Keeps the ordinary terminal.

The tests cover sync and async loops, direct calls and
The diagnosis without directives and execution with four slots.
The targeted pass has succeeded in `-O2` 67 tests. Indirect calls
via an async task and AsyncHandle returns remain open.

A parameter `&HashMap<i64, &i64>` now allows to read an entry
and return its scalar value. The two entries of the compiler
refuse mutation through the shared parameter and write of the
The HashMap pass and lock has been used to help the bank to secure the loan.
successful in `-O2` 20 tests, native controls on UBSan.

<a id="relais-de-capacité-dans-les-tâches-async"></a>

### Capacity relay in async tasks

The auditor follows creations and abandonments through tasks
intermediates and their synchronous calls. A wrapper `branch` called
In async keeps the possible pools of the handle.
and may include a created task whose actual execution
is not demonstrated.

The targeted test is now `-O0`. The 36 tests to `-O2` cover capacity,
public contracts and the obligations of the handles.
UBSan uses. AsyncHandle returns and dependencies remain open.


<a id="signatures-nominales-des-closures"></a>

### Nominal signatures of closures

The compiler checks unused bodies whose closing parameter
receives a loan structure or returns a field structure
The nominal type of the result is treated as
The verification covers the refusal of an argument
incompatible, refusal of an unknown field in the result and execution
native of nominal return. 17 tests go to `-O2` on closures and
type contracts, with UBSan for native witnesses.

The minimum C-test with `cc -fsanitize=address -g` compile.
execution still exceeds the five seconds on this machine.
The ASan box remains open.


<a id="capture-mutable-dune-structure"></a>

### Mutable structure capture

Reusable closure can move a nominal mutable reference
In a synthetic field. The displacement invalidates the original link.
The call by shared loan projects a readback loan that keeps
The witness performs two readings, refuses the
re-use of the link and the concurrent mutation of the target, and
written in the target after destruction of the closure. Targeted test to `-O0`
and 28 tests at `-O2` on closures, type contracts and locks.

<a id="emprunt-retourné-par-une-closure"></a>

### Borrow returned by a closure

The unused body of a function receiving a closure is verified
with a cookie implementation when the borrowed result corresponds to
a parameter of the same unique type. The actual specialization uses the
the body of the closure. The native test checks the reading through a relay,
refusal of writing before the last reading and writing after.
29 tests go to `-O2` with UBSan on native witnesses.
of a scalar reference captured remains refused when calculating
from the synthetic field.

<a id="provenance-dune-référence-scalaire-capturée"></a>

### Source of a scalar reference captured

The contract classifies the result from a shared scalar field of closure
as a loan on the storage of the target. The witness reads after destruction
the closing and written after the last reading.
early writing and returning a local target from a function.
Two tests go to `-O0` and 30 to `-O2`, with UBSan on native witnesses.

<a id="vue-partagée-issue-dune-capture-exclusive"></a>

### Shared view from exclusive capture

The contracts for reusable closures represent the projection of a
The scalar result follows the
The nominal result keeps a reservation in the field of the
the closing and preventing its destruction before the last reading.
refuse early writing and allow to modify the target after
The targeted test is now moving to the end of the loan. `-O0` and 31 tests go to
`-O2`, with UBSan on native witnesses.

<a id="vue-nominale-après-destruction-de-la-closure"></a>

### Nominal view after destruction of the closure

The origin of the shared reborrowing retains the identity of the capacity
The witness reads after destruction.
the closure, including the return of a relay function.
Checker refuses to write on target before last reading
and direct access by the holder during the exclusive capture.

The targeted test is now `-O0`. À `-O2`41 tests pass on the closures,
type contracts, locks and core cases, and 13 on borrowings
Native witnesses use UBSan.

<a id="références-nominales-partagées-en-hashmap"></a>

### Shared nominal references in HashMap

A local table stores a shared reference to a nominal allocation.
Dependence is kept by key, including during transfer of the
The witness reads twice the target, pulls out an entry,
then modify its target. The auditor refuses the transfer of the other
target and storage of a reference that would survive its target.
Online projections, mutable nominal references and contracts
The targeted test passes the test
à `-O0` and 39 tests go to `-O2`, with UBSan on native witnesses.

<a id="projection-partagée-en-ligne-dans-une-hashmap"></a>

### Online shared projection in a HashMap

The entrances using a structure use a C view that carries
The result of a withdrawal keeps the projection.
The verifier allows the writing of the brother field, refuses the writing of the
target field during borrowing and maintain this protection after withdrawal
Two targeted tests go to the `-O0` and 45
tests go to `-O2`, with UBSan on native witnesses.

<a id="transfert-dune-référence-nominale-mutable-en-hashmap"></a>

### Transfer of a mutable nominal reference in HashMap

The table consumes the mutable bond to the insertion and canned
exclusive by entry and projection path. The withdrawal returns
the mutable reference, with the root and offset for a field in
line. The witness rejects access via the old link and via the target
during the loan, authorizes a brother field and written through the deleted reference.
A test is now `-O0` and 38 to `-O2`, with UBSan on the C-witnesses.
Reborrowing from a box and signature of functions remain open.

<a id="analyse-syntaxique-des-annotations-branch"></a>

### Syntaxic analysis of branch annotations

`Parser.parse_syntax()` delivers the tree before elaboration. Annotation
`branch` recognizes the naked form, `join=result.join()` and
`join=result.await`. Existing verification of the availability of
the waiting and the provenance is then carried out by the compiler.
Both syntactic tests and ten core regression tests pass.
The complete native module has a semantic control, two of which are
sub-cases also fail when the new annotation control is
neutralized. The program without annotation that abandons a native task
The sub-cases are accepted as a stand-alone solution.

<a id="analyse-syntaxique-des-contrats-de-type-empilés"></a>

### Syntax analysis of stacked type contracts

The parser keeps the order of annotations, free statements
and the presence of `with` The witness uses the
signature of `spawn`, then remove the free type marker, the
type parameter or semicolon of a requirement to test the
Five annotations tests and ten regressions of the core pass.
The development keeps its scope of a contract with `with`.

<a id="chemins-de-types-qualifiés"></a>

### Paths of qualified types

The parser keeps the segments `::` of a type name and refuses a
The witness combines a signature of closure,
The seven targeted annotations and analytic tests
syntax pass. Resolution of qualified names remains distinct from
l'analyse syntaxique.

<a id="directives-de-taille-au-parseur"></a>

### Size guidelines for parser

The numerical profile of the core requires the separator `:` after `directive`.
The syntaxic control covers binary factors K, M and G, capabilities
and refuses comma, Ki, zero and a hexadecimal literal
for a region size. The comma remains in the profile
historical. 16 tests of the annotations modules of the region and the
capacity pass.

<a id="séparateurs-de-bras-de-match"></a>

### Game arm separators

The core profile requires at least one arm and a comma between the
The final comma remains optional. The syntactic control covers
The targeted suite has 42 successful tests with the enum and Option
regressions of the core, HashMap and the closures.
The results parser is still in place.

<a id="motifs-de-match-dans-larbre-syntaxique"></a>

### Grounds for match in the syntactic tree

The syntactic entry point of the core keeps its arms in order,
including interlocking patterns, joker, unity and motifs of
fields. Completeness validations and translation of results
buildtin stay on the path of compilation.
refuse an argument of absent motive, a field without connection and a path
17 targeted tests are being conducted.

<a id="arguments-de-types-et-listes-de-closures"></a>

### Arguments of types and lists of closures

The parser only reads the generic arguments borrowed from Pool, A and
Mutex according to production `type`. It distinguishes the comma
final accepted in a literal closure of the list of types of a
signature of closure. The existing development route retains
The same forms of supported types. 34 targeted tests are performed.

<a id="tranches-empruntées-dans-les-types"></a>

### Borrowed bands in types

The parser only reads the slices with an arbitrary element type
sous `&` ou `&mut`. It refuses one tranche per value, including in
a generic argument or a type of closure. Types of slices
The 35 tests taken care of by the preparation remain the same.
Targeted pass.

<a id="signatures-asynchandle-et-littéraux-annotés"></a>

### Annotated Atypical Atypical Atypical Signatures

The syntax entry point keeps the AsyncHandle type borrowed in
a signature and the annotated integer value u8. The compilation path
applies existing restrictions on the passage of an AsyncHandle and
The target 18 tests pass.

<a id="déclarations-nominales-et-annotations-lock"></a>

### Nominal declarations and annotations lock

The parser reuses reading the qualified names for the types,
Impl blocks, patterns and abilities. Syntaxic controls
cover a qualified impl with two annotations lock, refuse
a truncated path and a poorly formed lock contract. An empty enum is
The targeted suite of 25 tests passes, then
the two syntactic tests were replayed after the addition of the refusal of a
empty enum in a handless file.

<a id="chemins-de-valeurs-qualifiés"></a>

### Qualified paths of values

The syntax entry point retains the paths of qualified values
in the links, standalone calls and expectations async. An absent segment,
The compilation path remains unchanged.
21 targeted tests pass. The syntactic test was then replayed with the
refusal of `runtime::select_group()` within the current perimeter.

<a id="littéraux-numériques-et-bornes"></a>

### Digital Literals and Terminals

The parser alone retains the lexim of an integer too large for the profile,
including a negative sign. The compilation path retains its
The witnesses check the decimals without exposing,
indexing by range and refusal of chained comparisons without
The 22 targeted tests are passed.

<a id="en-têtes-move-et-blocs-de-capture"></a>

### Move headers and capture blocks

Syntax analysis allows several move inputs at the beginning of the block,
including in a thread block. She refuses an entry named after
an ordinary instruction and keeps a move block with final value
The eleven targeted tests are taken.

<a id="expression-finale-de-bloc"></a>

### Final block expression

The parser alone recognizes a final expression in a block
instructional or function. It retains expression in the tree
without converting it to implicit return. The witness covers the blocks
nested, a return annotated function and control keywords
The 23 targeted tests are passed.

<a id="expressions-employées-comme-instructions"></a>

### Expressions used as instructions

The parser alone retains an expression followed by a semicolon as
instruction, including a digital or parenthesive expression.
distinguishes from a final expression without semicolon and refuses two
instructions without separator. 35 targeted tests pass.

<a id="places-daffectation-composées"></a>

### Composite assignment places

The syntactic tree retains the dereferences and order of the fields
and indices of a place. The witnesses cover the simple assignment and
composed and refused a call, a beach, an empty clue or three
The compilation path remains unchanged.
35 targeted tests are being conducted.

<a id="chaînes-de-suffixes-en-lecture"></a>

### Reading suffix strings

The parser only keeps the order of the fields, indices and calls of
method on a compound expression. It refuses a missing field,
arguments poorly separated and an empty clue. The compilation path
retains its forms supported. 35 targeted tests pass.

<a id="initialisation-de-pool-sur-un-receveur-composé"></a>

### Pool initialization on a compound receiver

The syntax input point recognizes the new suffix on a receiver
It keeps the named fields in order and distinguishes the
form and form to an expression. Mixed forms and
multiple positional expressions are refused.
compilation conserve ses formes d'initialisation. 34 tests passent.

<a id="niveau-racine-du-programme"></a>

### Program root level

The syntax entry point follows the program production.
nominal declarations, impl, synchronous functions, async and
The following are the main features of the training:
or a statement in a block is refused. The script mode of
The old course is always practiced. 32 targeted tests pass.

<a id="directives-de-région-sur-les-productions-de-bloc"></a>

### Regional guidelines on block production

The parser alone accepts the directive before a function body or a
control block and keeps its size in the tree. The body of a
closure directly requires the braces, in accordance with the production
_delimit block. The cookies cover a body, an if branch and a
All right, then refuse a blockless directive.

<a id="conditionnelle-à-branche-else-facultative"></a>

### Optional else branch conditioner

The parser alone accepts the absence of else in accordance with the production
conditional, including in a receiver or after else if.
compiler retains the diagnosis that requires an else branch for
An else without block or conditionality is refused to the parser.
25 targeted tests are being conducted.

<a id="déréférencement-unaire"></a>

### Unary de-reference

The parser alone reads recursive dereferences and operands
The witness checks the priority of the index
and addition and refusal of a missing or incorrect operand
The compilation path remains unchanged. 40 tests pass.

<a id="déclarations-et-appels-externes"></a>

### External declarations and appeals

The syntax entry point represents an external declaration without
synthetic body and reads his call as an ordinary call.
the final comma and refuses an ABI other than C, a borrowed parameter
or a statement with a body. Unsafe control remains on the
17 targeted tests pass.

<a id="profil-du-point-dentrée-syntaxique"></a>

### Syntactic Input Point Profile

The syntax input point selects the core profile even when
the source contains no explicit numerical type.
old transfer arrows and recognizes the arrow types of
The 48 targeted tests are passed. The witness has
was replayed without explicit numerical annotation to exercise the case
where the historical heuristic chooses the other profile.

<a id="expression-unité-et-appel-immédiat-de-closure"></a>

### Unit expression and immediate call for closure

The syntax entry point distinguishes `()` of an expression
Parenthesed and recognizes him as an argument. He also checks the call
immediate from a parenthesed literal closure with final comma.
Poorly formed parentheses and unit application are not allowed.
The compilation path remains unchanged. 50 targeted tests pass.

<a id="chemins-qualifiés-des-types-builtin"></a>

### Skilled paths of building types

The parser only retains qualified calls and error variants
before the member's resolution and the control of the inequality.
truncated path or whose shape does not correspond to the namespace
The compilation path retains existing diagnostics.
26 targeted tests are being conducted.

<a id="receveur-de-signature-de-méthode"></a>

### Method Signature Receiver

The parser alone requires the receiver self in first position.
&self, &mut self and mut self with explicit type.
A method without receiver, a late self and a self as parameter
25 targeted tests pass.

<a id="constructeur-denum-sans-champs"></a>

### Fieldless enum constructor

The parser alone represents a variant of enum declared without braces
as a manufacturer. The tell-tale covers the manufacturer with fields
and distinguishes access to a field on a variable. 34 targeted tests pass.
The syntax test was then replayed with a manufacturer without
Fields as a match.

<a id="tailles-dans-les-tableaux-et-les-pools"></a>

### Sizes in tables and pools

The parser alone recognizes the unsigned whole sizes of the types
Tableau, rehearsals and pool builders. It retains a length
without representation without premature conversion, and separates a capacity
None of the control that refuses to compile it. 35 targeted tests pass.

<a id="valeurs-des-directives-de-capacité-async"></a>

### Async Capacity Guidelines Values

The parser alone retains an entire capacity, including zero or
a value outside representation, and refuses a signed value or
The limits and positivity checks remain on the
The 18 targeted tests pass.

<a id="taille-de-région-hors-représentation"></a>

### Region size not shown

The parser alone retains a positive decimal size with K, M or G
even if it exceeds the representation of the compiler.
the refusal of zero. The compilation keeps its existing terminal.
19 targeted tests are being conducted.

<a id="identifiants-dans-les-déclarations"></a>

### Identifiers in statements

The parser alone refuses words reserved for declaration positions.
Witness accepts `self` as a method recipient and `_` in a
The 36 targeted tests pass. This check covers the declarations
and the exceptions exercised by the witness.

<a id="initialisation-de-pool-et-types-parenthésés"></a>

### Pool initialization and parenthesive types

The parser alone accepts `points.new(data::value)` and refuses a path
pointed as the initialization field name. In type position, it
accepte `()` and refuses the historical pair syntax of slices.
The 36 targeted tests pass. The historical path retains its forms.

<a id="type-du-constructeur-de-pool-et-motifs-denum"></a>

### Pool manufacturer type and d

The parser alone recognizes a type of full borrowing in `pool<type>(taille)`.
In a d-enum pattern, it requires ordinary identifiers for the variant,
fields and links, with `_` To ignore a field.
The eligibility of the pool type and the constraints of the match pass.
The auditor shall be responsible for the audit.

<a id="syntaxe-des-contrats-de-type-et-de-branche"></a>

### Syntax of type and branch contracts

The parser alone retains the alternatives borrowed and the methods of
prior to checking the distinction of names and type of recipients.
It requires at least one method and refuses the names reserved in the parameters
Type and after `result.` The 39 targeted tests
a witness confirms the refusal of identical names on the route of
compilation.

<a id="syntaxe-des-lancements"></a>

### Syntax of launches

`parse_syntax()` keeps the expression passed to `spawn` ou
`spawn_blocking` before the analysis of the type or context. L
The 41 targeted tests pass.
The extended suite of 51 tests indicates two failing assertions in the
`test_native_blocks_enforce_wait_before_drop_or_return`. `verify_program`
and `compile_source` accept a standalone thread that returns `7` without
The program does not contain a
no call to `spawn` ou `spawn_blocking`. The witness is to be reconciled
with RT7 during the check pass.

<a id="blocs-de-thread-et-suspensions"></a>

### Thread blocks and suspensions

The parser alone recognizes `yield;` and `.await` without deciding whether the context
allows a suspension. It keeps the catches named repeated in
A block of thread and rejects the reserved names. The 42 targeted tests pass,
of which refusals to suspend in a thread block on the course of
compilation. The divergence of the standalone thread indicator remains open.

<a id="appels-de-méthodes-et-plages"></a>

### Calling methods and beaches

The parser alone retains the arguments of an ordinary call even when
The inequality would be invalid for an integrated method. L
Rating `try_slice(début..fin)` already recorded for UTF-8 channels.
The 41 targeted tests pass. They cover parsing and regressions
directly linked to calls, without further checking of the situation.

<a id="constructeurs-intégrés"></a>

### Integrated constructors

The parser alone requires a unique expression without a final comma in
`Mutex::new` and `AsyncMutex::new`. He refuses the prefixed construction
`new(source) Int(...)`. `stack(...)` and `allocator(...)` follow the syntax
the standard calls at this stage. The witness also covers the construction
The 42 targeted tests pass.

<a id="chemins-qualifiés-et-types-intégrés"></a>

### Skilled and integrated types

The parser alone refuses the reserved names in the ordinary segments of a
The integrated types follow their dedicated productions. `A`
requires his type argument, `Execution<T>` remains historical and
`runtime::Future` The 44 targeted tests are being conducted.

<a id="emprunt-dune-découpe"></a>

### Borrowing of a cut

The parser only keeps the operator `&mut` and its operand in
`&mut text[1..3]`. A cut without index or separator `..` is refused.
The compilation path retains its diagnosis of mutability.
44 targeted tests are being conducted.

### Cibles d’affectation

The parser alone uses production `place` for simple assignments
and composed. He accepts `self.total += 1` and `total %= 2`, and refuses
cibles comme `bool` ou `table._`. The 45 targeted tests pass.
access and mutability of the target remain compilation controls.

<a id="formes-bloc-en-position-finale"></a>

### Block shapes in final position

The parser alone keeps the simple blocks, `move`, `unsafe`, `if`,
`match` and `loop` as results when they finish the block without
a semicolon. A block shape followed by an instruction may remain a
The 46 targeted tests pass. The assertions on the form of
tree have been updated for the `match` terminaux.

<a id="accolades-vides-après-une-variante"></a>

### Empty cladding after a variant

The parser alone recognizes `if Choice.First {} else {}` and
`while Choice.First {} {}`. If the interpretation of the first braces
as initialization leaves the condition without block, the parser resumes
When another block follows, it keeps the
The 47 targeted tests pass.

<a id="chemins-de-valeurs-et-champs"></a>

### Values paths and fields

The parser alone recognizes `self.champ`, `i64::try_from(...)` and
`runtime::Error::LaunchFailed`, and refuses `self::champ`, `packet._`
and the words reserved in a value position.
`runtime::select`, `runtime::start_poller` and `runtime::set_scheduler`
The 48 targeted tests pass.

<a id="chemins-de-valeurs-dans-les-motifs"></a>

### Patterns of values

The parser alone shares the reading of integrated paths between motives and
expressions. A motive recognizes `Err(runtime::Error::LaunchFailed)` and
`network::Ready(_)`. Incomplete paths and reserved segments
The 49 targeted tests are being tested.

<a id="type-cible-dune-conversion"></a>

### Target type of conversion

The parser alone recognizes production `type` complete after `as`,
y compris `&mut [network::Packet]`. Successive conversions are
The 61 tests are not supported.
The target is passed, including the digital suite with the existing controls.

<a id="déclarations-du-point-dentrée"></a>

### Declarations by the point of entry

Parser alone recognizes external and async statements named
`main`. The external declaration requires the semicolon provided for by the EBNF.
The compilation retains control of a synchronous Crust input point.
The 78 targeted and d-integration tests pass.

<a id="nombre-de-directives-de-région-par-bloc"></a>

### Number of region-specific guidelines per block

The parser alone refuses two regional directives on the same block,
in the expression position or after `move`. The interlocked blocks may
Two assertions of the future of growth
have been adjusted to read the annotations in the tree of expressions
The 57 targeted tests are completed after this adjustment.

<a id="liaisons-et-déclarations-héritées-dans-un-bloc"></a>

### Linkages and declarations inherited in a block

The parser alone refuses `let (mut left, mut right) = split();` and
`type feature` in a block of the core. It recognizes an import named followed
d-a closure bond `move`The 58 targeted tests are being conducted.
expanded to 80 tests shows a historical failure: `test_declaration_storage_and_signature_rejections`
waits for the refusal of `type feature Plain {fn a(self);}` on the course of
historical compilation, which accepts it. This pass does not alter this path.

<a id="séparateur-de-chemin-contigu"></a>

### Contiguous road separator

The parser alone recognizes `Option<A<network::Packet>>=value` and refuses
a separator `::` split by space, line jump or comment.
The same sequence confirms that these characters remain accepted in a string.
The 73 targeted tests are being conducted.

<a id="vérification-syntaxique-en-ligne-de-commande"></a>

### Syntactic command line verification

`check --syntax-only` Call the core parser. `yield;`
places this order and the `check` Ordinary refuses it in a body
Without a semicolon, the parser refuses the control.
refused with `emit-c`. Both modes accept `let_mutability.crust`
and the 50 targeted tests are being conducted.

<a id="nom-syntaxique-du-primitif-i32"></a>

### Syntactic name of primitive i32

L-tree of parser only preserved `i32`including in a signature
external and `HashMap<i32, &i32>`. The historical key `Int` is
refused in the syntax of a HashMap of the core. The compilation path
The 74 targeted tests are performed.

<a id="types-dans-les-signatures"></a>

### Types in signatures

The parser only keeps the full type `A<i32>` in parameters and
the result, and `bool`, `&[u8]` and `runtime::AsyncHandle<i64>` in
a signature async. Lowering signatures and recording of
Related types remain on the compilation track. The 76 targeted tests pass.

<a id="reprise-après-une-expression-refusée"></a>

### Resumed after an expression refused

The parser alone could accept `bool();`, `runtime();` ou `bool` in
end of block via historical productions after refusal of expression.
These forms are now being refused, and 63 targeted tests are being conducted.

<a id="appel-de-méthode-après-un-nom-denum"></a>

### Method call after a name d

The parser alone recognizes `Choice.read()` as a method call and
`Choice.await` comme expression d’attente, y compris lorsqu’un enum
`Choice` The 62 targeted tests pass. The resolution of the
The liaison and member shall be responsible for the audit.

<a id="bloc-vide-suivi-dun-opérateur-ou-dun-suffixe"></a>

### Empty block followed by operator or suffix

The parser alone recognizes `if Choice.First {} + 1` and
`if Choice.First {}.read()` by linking the rest to the `if`. Si un autre
block follows, as in `if Choice.First {} == 1 {}`, the first
The 64 targeted tests pass.

<a id="receveur-en-expression-et-périmètre-de-sl1"></a>

### Expression and perimeter receiver of SL1

L’EBNF exprime directement que `self` is a value and a base
d. The parser accepts `self.champ` and refuses `self()`.
The two target productions of SelectGroup bear the mention of the postponement.
The 54 targeted tests are being conducted.

<a id="programme-public-de-démonstration"></a>

### Public demonstration programme

`examples/main.crust` utilise `memory.new(Message.Value { ... })`,
the shape of the core to build a variant in a pool.
`check --syntax-only`, `check` and `run` pass. The execution produced `42`
and the existing witness confirms the trace of destruction and recovery.
The 55 targeted tests pass. Other historical examples still to be examined
according to the invariants they exercise.

<a id="exemple-de-retours-conditionnels"></a>

### Example of conditional returns

`conditional_returns.crust` utilise `Pool<i32>`, `A<i32>` and `drop`.
`check --syntax-only`, `check` and `run` passent. L’oracle d’exécution
check the results `10` and `20`, four identical addresses and the
destruction followed by recovery of each value.
`pool_requirements.crust` garde `Allocator` to show inference
historical. `effects` confirme que `relay` relays the same
pool requirement that`inspect`.

<a id="exemples-de-retour-dun-objet-contenant-un-emprunt"></a>

### Examples of return of an object containing a loan

Both examples use `A<View>`, `views.new(...)` and `data.vref()`.
Both pass `check --syntax-only`. `run` affiche `View.Item(42)`
for the valid relay. `check` refuses the return of the object that borrows
a local target with the diagnosis of durability in the parent scope.

<a id="appels-ordinaires-portant-le-nom-try_slice"></a>

### Regular calls bearing the name `try_slice`

The parser alone distinguishes `try_slice(..2)` d’un appel ordinaire tel que
`try_slice()` ou `try_slice(1, 2)`. The first argument is read once.
The 54 targeted tests pass. Method resolution remains at the stage of
the compilation.

<a id="rejeu-transversal-du-parseur-seul"></a>

### Cross-sectional parser game

The 57 methods calling directly for `parse_syntax` pass in the
travel, type contracts, digital, growth and thread.
They exercise the declarations, types, blocks, suffixes, operators,
Annotations and forms of launch. L-EBNF also indicates the priority of
production initialisation after `.new(` and the beach in
`try_slice` with `..`This game covers existing witnesses.
full equivalence between EBNF and the parser remains open.

<a id="fermetures-génériques-et-opérateurs-adjacents"></a>

### Generic closures and adjacent operators

The parser distinguishes `>` of the following operator in `value as A<i32>==other`,
`value as A<i32>>=other` and `value as A<i32>>>2`. Deux fermetures suivies
of the `=` the term "representative" is used in a statement. `4>>>1` and
Composite assignment `value>>=1` The 78 targeted tests are rejected.
pass, including the digital suite.

<a id="parenthèses-de-lappel-immédiat-dune-closure"></a>

### The immediate call for closure

The parser alone accepts `(move || {42})()` and consolidation
`((|| {42}))` in a position of value. `((|| {42}))()` and
`(read)()`, absent from production `appel_closure`The 54 tests
The historical path keeps its existing analysis.

<a id="usages-du-nom-pool"></a>

### Use of the name pool

The parser alone distinguishes `pool<Pool<[i32; 2]>>(4)`, `pool.new()`,
`pool < limit >> 1` and `pool()`. The manufacturer shall take priority when
arguments follow the type between chevrons. The test already has a name
The 70 targeted tests pass.

The parser also distinguishes `pool < (threshold > (0))` Construction
`pool<closure(Pool<i32>) -> i32>(4)`. The manufacturer ' s type closure
must be outside the parentheses and square brackets.
Targeted pass after this supplement.

<a id="échappements-des-littéraux-texte"></a>

### Text letter slashes

The parser decodes JSON exhausts and then encodes the string into UTF-8.
The witness checked the bytes of a direct literal, exhaust
Unicode, d
He confirmed four refusals: `\q`, `\u{e9}`, un
isolated replacement and a raw line jump. TX1 guarantees the UTF-8 without fixing
The exhaust list. L-EBNF indicates the condition of the parser and arbitration
The parser's behavior is unchanged.

<a id="accolades-après-un-nom-de-structure-en-condition"></a>

### Accolades after a structural name in condition

The parser alone distinguishes `if Packet { print(1); }`, `if Packet {} else {}`
and `if Packet { field: 1 } {}`. Reading the braces follows the same
The choice of link and the
The 65 targeted tests are performed.

<a id="diagnostic-dune-forme-bloc-mal-écrite"></a>

### Diagnosis of a badly written block form

The parser alone retains the internal error of a block shape instead of the
Return to reading as an instruction. A witness instrumentalized with twenty
`if` interlocked and one `match` empty counts 21 block readings and finds
diagnosis of the `match`The 66 targeted tests are being conducted.

The same treatment then retains the diagnosis of expression
`1 + ;`. Forms reserved for instructions, including `let` and `return`,
The 67 targeted tests are being carried out.

<a id="oracle-dattente-des-threads-natifs"></a>

### Oracle waiting for native threads

The witness that required a wait for any thread is replaced by a
case in core syntax. `verify_program` and `compile_source` acceptent
they refuse to give up explicit abandonment and the
without waiting for the thread to capture a local reference.
The 70 targeted tests pass. The deviation of the previous control is solved by
the update of the assertions according to N4 and RT7. The auditor's code and
the cleaning at run are not modified by this update.

<a id="régression-conjointe-du-core"></a>

### Joint regression of the core

`PYTHONPATH=tests python3 -m unittest test_numeric_core test_type_features.FunctionTypeContractTests test_value_moves test_growth_annotations test_native_thread_parser test_core_integration`
completed with 124 successful methods in 38.296 s. The selection covers the
parseur of the core and compilation routes already supported.
exemples `main`, `conditional_returns`, `borrowed_returns`,
`invalid_borrowed_return_escape` and `let_mutability` passent aussi
`check --syntax-only`. Refusal to `invalid_borrowed_return_escape` lors
the verification remains covered by the previous cycle tell-tale.
The standard list of exhausts remains open, as well as the work
for verification of closures, branch contracts, handles and compositions
HashMap and lock indicated in the checklist.

<a id="receveur-historique-de-type-feature"></a>

### Character type historical receiver

The parser of `type feature` applies the three forms of TF1 receiver:
`&self`, `&mut self` and `-> self`He now refuses `fn a(self);` in
This historic declaration. Core type contracts continue
use EBNF method signatures. 92 follow-up tests
type contracts, threads and travel pass. This resolves failure
historical record in the extended pass to 80 tests.

<a id="appel-de-copy-au-parseur-seul"></a>

### Copy call to parser alone

`copy([1, 2])` keeps the shape of an ordinary call in the tree
A witness instrumental with `Vector<i32>` in parameter and
`Result<i32, runtime::Error>` in return async confirms that the functions
d `parse_syntax`.
The 71 targeted tests are being conducted.

<a id="source-utf-8-invalide-dans-la-cli-syntaxique"></a>

### Invalid UTF-8 source in the syntactic LTC

`check --syntax-only` reads explicitly in UTF-8. A file containing
`"été"` is accepted. An invalid byte at position 20 results in a
Code 1 output with position and Python trace. `check`
and the `check` ordinaire acceptent `examples/main.crust`.

<a id="programmes-complets-de-la-suite-dintégration"></a>

### Full programmes of the integration suite

Next `test_core_integration` completed 30 tests successfully in
29.910 s. An instrumentation of its direct calls to `compile_source`
has collected 44 separate accepted sources. The parser alone accepts
the 42 sources of the core. Both sources with `experimental_scheduler=True`
are refused on `runtime::Future`, outside the EBNF of the core.
covers direct calls from the follow-up. Programmes launched only
by CLI subprocesses are not part of the count.

<a id="correspondance-entre-lebnf-et-le-parseur"></a>

### Correspondence between EBNF and parser

| Production families | Patch input | Witness continuation |
| --- | --- | --- |
| Programme, declarations, signatures, `type`, `branch` and `lock` | `parse_declarations`, `function`, `foreign_function`, `implementation`, `type_annotation`, `annotated_function`, `lock_annotation` | `FunctionTypeContractTests`, `NativeThreadParserTests` |
| Types, paths, links and targets | `type_name`, `type_argument`, `qualified_name`, `syntax_assignment` | `FunctionTypeContractTests`, `ValueMoveTests` |
| Directives, blocs, imports `move` and flow control | `async_pool_directive`, `region_annotation`, `block`, `branch_tail`, `statement` | `GrowthAnnotationTests`, `ValueMoveTests` |
| Operators, suffixes, literates, closures and manufacturers | `numeric_expr`, `postfix`, `primary` | `NumericCoreTests`, `ValueMoveTests`, `FunctionTypeContractTests` |
| Patterns, Launch, Wait and Thread Block | `syntax_match`, `syntax_pattern`, `primary`, `postfix` | `NativeThreadParserTests`, `FunctionTypeContractTests` |

The 61 methods that call directly `parse_syntax` in these five
The series has been replayed and passed. This review links productions to
It is not a general proof of equivalence.
The list of standards for exhausts is open.
SelectGroup are recorded as deferred.

<a id="exemples-de-champ-emprunté"></a>

### Examples of borrowed field

`reference_fields.crust` and `invalid_reference_field_drop.crust` passent
`check --syntax-only`. The first poster `42`. The second is refused by
`check` with `emprunt encore utilisé`Migration names `data.vref()`
before inserting into the field. The direct shape in the initializer
The auditor requests a named loan.
The case `match &*view` also passes the syntax analysis and remains refused by
the compilation course of this match. `match &view`.

<a id="exemple-de-match-non-exhaustif"></a>

### Example of a non-exhaustive match

`invalid_enum_match.crust` utilise `fn main`, `i32` and `memory.new(...)`.
The parser alone accepts the program. `check` refuse it on completeness.
Adding `Message.Empty => {},` in a temporary witness passes the
The four CLI calls confirmed the expected outcomes.

<a id="exemple-de-remplacement-entre-pools"></a>

### Example of pool replacement

`reassignment.crust` utilise `A<i32>`, `pool.new(...)` And the end of the telescope.
The call that reads the old value produces a result named before the
first replacement. The second uses `second.new(30)` directement.
Syntactic analysis, verification and execution pass.
confirme `10`, `20`, `30` and the trace of destruction and recovery.
The witness `data = make(&mut first, view);` passe `parse_syntax` and fails
in compilation with `<- exige ici une valeur tableau`. This limit remains
Open on the compilation side.

<a id="emprunt-explicite-dans-les-exemples-de-retour-direct"></a>

### Explicit borrowing in direct return examples

Shared and mutable examples use `.vref()` and `.mut_vref()` for
borrowing the content of `A<i32>`. Both pass `check --syntax-only`
and `run`. Execution confirms the same address before and after the relay,
then exits `42`, `7` and `30`, `40` The two extracts respectively.
of README pass `parse_syntax` and `verify_program`.

<a id="exemples-de-contrôle-de-flux-et-de-sortie-de-bloc"></a>

### Examples of flow control and block output

The six examples `conditionals`, `if_expression`, `loop`, `continue`,
`while` and `scope_exit` passent `check --syntax-only` and `run`. The traces
The results of the two surveys show that the `temporary` in the examples
and the return of `3` from interlocked blocks of `scope_exit`.
The sources of these examples already use the syntax of the core.

<a id="exemples-de-drop-et-de-déplacement"></a>

### Examples of drop and move

`drop`, `drop_reuse`, `invalid_use_after_drop` and `invalid_borrow` passent
`check --syntax-only`. The first two execute. `drop_reuse` produit
`42`, deux adresses identiques, `43` and `99`, and its trace contains
`reuse fresh`. The verifier refuses to read after `drop` and
the loan is still to be used.

<a id="exemples-de-type-et-de-durée-de-vie-dun-pool"></a>

### Examples of the type and life of a pool

`invalid_pool_type.crust` and `invalid_function_allocator.crust` passent
`check --syntax-only`. `check` refused to build the `Message` in
`Pool<i32>` and the return of an allowance whose pool is local to the
function. The incompatibility diagnosis still shows the name of
Representation `pool<Int>`. The four CLI calls confirmed the issues
attendues.

<a id="exemple-dévaluation-des-arguments"></a>

### Example of assessment of arguments

`arguments.crust` utilise `A<i32>` and the passage by value.
parseur and compilation. `42`, `7`, `42`, `8`, `43`
and cleans both allocations. The witness also reverses the order of the
settings to keep their types. It passes the parser, then the
verifier refuses to move before reading the loan.

<a id="exemple-de-champ-emprunté-mutable"></a>

### Example of a mutable borrowed field

`mutable_reference_fields.crust` utilise `A<Writer>` and
`nombre.mut_vref()`. `check --syntax-only` passes and the execution produced
`Writer.Bound(10)` then `20`. The writing moved before `print(writer)`
pass the parser, then the verifier reports an active loan.

<a id="exemple-de-retour-depuis-deux-pools"></a>

### Example of return from two pools

`provenance.crust` receives and returns from `A<i32>`. The chosen branch
keeps the address of the returned value and the slot of the other value is
reused in its pool. The program and its temporary reverse variant
passent `check --syntax-only` and `run`. Both executions verify the
addresses and values `20`, `30` then `10`, `30`.

<a id="témoins-de-portée-et-de-déplacement"></a>

### Range and displacement witnesses

`invalid_child`, `invalid_transfer_alias`, `invalid_function_move` and
`invalid_allocator_escape` passent `check --syntax-only`. The three
first fail to `check` on the old name became unusable.
Fourth fails because the pool doesn't survive the block.
utilisent `move`, the value change and `pool<i32>`.

<a id="inventaire-final-des-exemples-pour-la-passe-syntaxique"></a>

### Final inventory of examples for the syntax pass

The 46 sources`examples` were analysed with `parse_syntax`.
31 pass, including witnesses who must fail the verification.
The 15 refusals concern `allocator`, `effects`, `enums`, `functions`,
`invalid_modular_reset`, `invalid_reset`, `modular_calls`, `pool`,
`pool_requirements`, `reset`, `results`, `source_constraints`, `stack`,
`valid` and the former form of `select`. `invalid_pool_requirement` passe
the parser because `Allocator` is read as a type name, whose resolution
The deviations identified on validated forms are as follows:
The system is processed in the syntactic pass.
the verification and migration of historical tests remain open.

The user then confirmed the postponement of arbitration on the
The grammar records the current behavior of the parser.

The report has been lifted. TX1 fixes JSON exhausts for chains
Crust. The witness covers 11 accepted forms with comparison of bytes
and 7 rejected forms.

<a id="passage-explicite-dune-closure"></a>

### Explicit passage of a closure

L-EBNF and the core parser use `fn(...) -> R` for signature
d
The former rating is rejected by the former rating.
`closure(...) -> R` in `check --syntax-only`. The historical path
the recognition still and the internal representation of the elaboration is
The 35 tests of the `FunctionTypeContractTests` passent. Ce lot
covers grammar, parseur and rule statement.
The semantics of new modes of passage remain to be integrated.

<a id="implémentation-partielle-de-n4-n5-n6-et-n8"></a>

### Partial implementation of N4, N5, N6 and N8

Road junctions use the same bond merger
a replacement receiver, an embedded value and a
maintained link. They keep the pools and result locks
and possible delayed entries.
this junction is described in [MEMORY_REPRESENTATION.md](../MEMORY_REPRESENTATION.md).

The same merger covers the results of the `match` and `break` and
loads extracted with several representations possible.
The comparison of the fixed point of the loops now includes the
sources and variants of the deferred load and its fields,
and the reported accuracy of the updates. It also compares
destinations of deferred entries, links and reborrowings
the position of the loads.
Fusion avoids copying the same effect from a shared state
by several paths.

The loop comparison also follows recursive projections
fields and results delayed. It reads each origin with
a table was read as
a single source, which could interrupt Python analysis.
Entwined receivers, results and loads junctions
keep the tables of their possible origins.

In the case of a deferred result, an explicit field of
contract replaces the projection inherited from the bearer, including
The other paths are recovered from the
all possible origins. L-inference of variants applies
the same priority and preserves the variants already established in
the contract.

The application of the scriptures kept waiting keeps the couple
lock and load. If multiple loads are possible, each
retains its previous condition and the writings that concern it.
The refinement by success or `LaunchFailed` always requires a
exact writing and a single load for the lock.

Returning a handle from a synchronous call takes back the pools
A contract that only returns a handle
argument also repeats its proof of autonomy and, without new
Deferred writing, the accuracy of its updates. If more
arguments are possible results, their effects are combined
Async lowering keeps the pools of the
autonomous handles transmitted by such a call to record a
possible abandonment after return.

When a synchronous launch, the execution handle takes over the
deferred obligations of inactive task via the same representation.
This transmits the pools and proof of autonomy received from a relay,
and delayed effects until waiting.

The downsizing publishes the concrete pools of autonomous handlers
This information is stabilized with the
other obligations of result, including when a task returns
a handlet received pending another task. `join()` and both
forms of `.await` recover these pools for static tracking
The perimeter covers pools of which origin is
known in the body, as well as explicit abandonments and
handle results ignored. When a task returns a handle
The contract identifies its parameter.
direct task substitutes the argument pools, in code
synchronous async. L í waiting and async junctions keep
The synchronous relays keep the pools of the
already established results on their arguments, including when the appeal
is lowered in one task. Loop outputs by `break`
The loans and effects of the loan are also included in the possible sources.
d-a returned dependent handle still to be integrated.
synchronous factories building a new task
publish the origins of the handluff pools that she can return.
The inference replaces the arguments to the catches during the
creation of the task, and then propagates these origins through the
calls and junctions. Lowering a synchronous call
from a task recovers the concrete pools of the contract.

The life control follows the values proposed by the
Deferred entries on the same path as the possessed loads.
He checks their borrowings, locks and effects
For a kept handwriting, he checks the bearer, the
protected load and target links that writing can
Install. Control is used for transfer and output of the telescope.

The replacement of a receiver by a receiver `if`, un `match` or
loop also uses this graph. Before changing the identity followed,
compiler checks that the branch result is holding
Not a dependency on this generation of receivers.
The same control applies to the transferred values.
The result of a `if` merges deferred bonds with the
The same rules as other junctions, in particular the pool of
returned handles and the accuracy of the effects.

A task inactive or launched keeps a reservation mutable on
each ordinary deferred writing destination.
access and travel use this reservation during
The duration of the task. For a kept writing, the
existing control continues to pass through the lock.

At the border of a synchronous call that receives a handle, the
Common writing destinations are compared to other
arguments. For a kept entry, the check also follows
transitive dependencies of installed targets.
handle are compared from their life graph,
which includes the destinations and targets of their own writings.

A task directly expected may make a `AsyncHandle` who
The lower rate of interest rates is the result of the
The Bank of Greece is the only country to have a fixed rate of interest on loans.
arguments at call and attach them to the handle received at time
where it releases other reservations from the external task.
control prohibits the abandonment of the handle received as long as these loans
This path covers shared borrowing and
mutables with target up to a parameter, with a load
In an async context, the
external task can also be launched.
the result reservations. `.await`, the result
can be preserved until `match` which transmits them to the handle of the arm
`Ok` or release them into the arm `LaunchFailed`. The paths
the abandonment and suspended cleaning control this obligation.
The connection to the `join()` Synchronous, Select and Effects
Delayed from the returned handle remains open.

Un `AsyncHandle` returned may also produce a loan
The contract publishes the parameters on which this
borrowing separately from those which the handle reserves during its
direct wait and direct launch preserve
The branches, the exits by `break` and
synchronous relays that re-establish their arguments bring together the
possible projections. For a path without projection
The analysis keeps its catches.
tasks called before their appellants to the extent permitted
by the creative graph.

The effects analysis separately publishes ordinary entries
The system is used to solve the mutable carriers.
and targets from the parameters of the external task.
External waiting and extraction in `Ok` transmettent
These effects in abstract analysis.
apply them with the possible initial state in case of
`LaunchFailed`The reduction in these entries at the
creation of the task and keeps them until the handle is waiting
The junctions and relays preserve the possibilities.
The analysis distinguishes the fields that each possible hand writes
fields written on some paths only. `Ok` affine
For the first, for the second, and for the paths, the
contract is incomplete, initial status is possible.
current owners or delivery systems still require a contract
adapted return.

For a returned handle that can write under lock, the contract
connects the injected mutex to the borrowed parameters that provide
targets. It distinguishes targets from each observable writing
the possible state at the end of the task. An unknown provenance
the publication of a partial contract.
the external task, the auditor reserves the mutex and
validate every possible writing.
effects to the inner handle and applies them to its own expectation.
This path covers the direct return of writing of a
The scriptures kept by all the children
possible handles refine the state after `Ok`. Writings
The effects of the intermediates are controlled independently.
conditional and `LaunchFailed` keep the initial state
When a task waits and then transmits the handle,
l-analysis transports observable entries in a field
The new contract resolves the problem of the
both sets in the relay task parameters.
Re-exported paths also retain proof of writing
A junction retains this evidence for a field
only if all possible results are carried out.

The contract of the returned handle carries replacements of
The compiler, when it is built,
solves sources and checks that a local pool survives the field
The effect remains deferred until the date of the grant.
I'm waiting for the inside handle. `Ok`, l’analyse affine
the provenance of the field for which replacement is guaranteed.
Lowering distinguishes the basic storage and the proprietary links
fields or entries for the buildings followed. At the junction,
the distinction remains available when each path provides its provenance
a loop recovery expands the possible sources before
The return of a handle also carries the
sources of the elements that it can install in a vector
d) Allowances. The contract expresses them in relation to the parameters
The new expectations followed by a new
This can be done by means of the following methods:
The effect is delayed until the end of the start-up period.
The follow-up keeps the old ones waiting for the hand which carries the mutation.
possible sources and does not deduce any exact position.
inline outbuildings remain open.

The HashMap insertion and removal routes are transported by
the result of a handle. The summary keeps the keys constant and
the parametric origin of the table and the inserted value.
A key whose value is not established joins the key entries
unknown. The waiting of the handle applies the paths to the graph
The launch result allows us to distinguish the state
the success of the one where the mutation did not take place.
The termination summary also publishes the paths of a table
Injected modified by waiting for a returned handle. The site
call applies them to the corresponding entries.
Keeps the exit without mutation if the launch fails.
direct and delayed transfers are summarized separately,
possible final sources of both orders are retained.
The refinement of these paths per arm remains to be connected.

Lexical async clean up checks remaining reservations
after the clean-up of tasks and the release of loans from the
block. A local scalar or tableau that still serves as a target for a
The surviving reservation results in a refusal.
borrowed parameters retain the controls of their targets.

Synchronous cleaning checks that a living task holds
the target of destruction. The abandonment of a handle consults
the graph's targets and pools, and the historical path of
The reset consults these same dependencies. `drop`
explicit from a borrowed scalar controls its loans before
d-invalidate the liaison.

From an async context, a synchronous relay can return a
The contract must return the documents which are kept.
the only hand passed without waiting.
parameters are scalar passed by value.
catch and entries pending, as the result of
`.await` apply and refine at the usual point of observation.
A pure relay without its own effect does not create a possibility
where the writing would not have taken place.

The compiler applies destination control to the built aggregates
with calculated borrowings. `match &*vue` access controls
and keeps the reservation of an entrance from HashMap when borrowing again
A local assignment whose result is a call-ownership
goes through the evaluation of the right part before cleaning the old one
value. `branch` Follows aliases and conditional exits.
The specialization of the closing parameters retains their borrowing mode,
and a constant key insertion contract can spread a nominal target.

The next batch connects the replacement of an ancestor receiver to the controls
The branch contracts also follow the match arms and
loop covers. HashMap integration contracts cover keys
The data are used to determine the number of blocks and the expected returns.
life of each reference recorded in the table.
re-borrow their nominal catch in mutable for the recognised entries.
The compiler refuses a second acquisition in async when a guard
living already retains the same instance, and transmits its reservation when
The guard is moved. An isolated synchronous call can relay
a handle with retained effects. If possible, the compiler
keeps the success and failure of the launch.
When transferring, it also monitors the life of the destinations,
borrowings and pools of deferred entries.
unused closures may represent a return shared by a capture
symbolique.

The synthetic body of an unused template now represents
all reference parameters the type of which corresponds to the
result. For a shared result, it also includes a capture.
Symbolic conditions give inference a path by
possible origin. When the receiver mode allows an invocation
a digital or nominal mutable loan may also be transferable
from the reborrowing of a capture. The template uses the same
field and the same source control as a concrete closure.
The nominal case keeps the field reservation and the target
Projected via the return contract.

For N6, the replacement identifies the receiver's scope before the part
straight, then reread its bond after the evaluation. Cleaning uses
thus the link from the paths that continue and save a
The right side has already moved.
When branches replace a receiver, the junction checks that
every path that continues has a living allocation.
takes the modification meters and uses the same fusion
the provenances by position that the junction of a preserved bond.
The convergence of a loop also compares the locks carried,
locks and pools of the result of a task and information
The merger of paths retains these obligations even if they are not
where the value concerned is intertwined with another allocation.
When a loop is resumed, the generation control follows the
transitive dependencies and receiver locks. For N4, the
destination check also includes the result pools
The delay was the delays in its fields and the instances of its locks.
Closing a scope determines the pools still required from
the ties of possession of living allowances and their
Delayed results. Pool closure control is common to
groupes d’allocations.
The destination control and the closing of a pool use the
same path of the storage links. Location of the allocation
root remains verified by the transfer itself.
This path also follows the values that a delayed update can
install. Control at the closure of the scope therefore retains their
pools as long as the effect is carried by a living value.
The control of loans when a block closes applies to the
values through their dependency relationships.
The projector shall verify the scope of the allocation containing it.
Destination Control also uses this root to check
The scope and validity of the policy includes direct targets, which are
a reference descriptor and those of a deferred update.
The closing of the scope and the transfer share this path of
Targets. References by interlocked descriptors are
taken into account with the group's borrowings, reservations and locks.
Access control validates the planned reservations on their
root allocation. It retains exclusive restriction when it does not
has no declaration to prove that a catch is
allows shared reading.
Controlling arguments during a hand-writing relay
The pool used by the same route.
also locked instances, including those carried by a
deferred result, to other arguments.

A direct expectation may be `AsyncHandle` autonomous with result
scalaire, tableau scalaire ou `Void`. The frame retains responsibility for this
until the result is transferred. If the finished frame is destroyed before the
transfer, runtime takes over the handle.

The results of the `join` keep the source of the updated data kept
to distinguish the success of the failure from the launch in the game.
monitoring covers scalar results, tables and charges
A view taken from the land or from the land represented by an allocation.
keeps the same information in addition to its descriptor.

Transferring an AsyncHandle to a frame erases the value
The calculation of the capacity takes account of the abandonment of the
If the frame is destroyed before it starts, it can be detected.
The following are also included in the list of the following:
explicit and mutable field methods.

A closure may re-borrow a mutable numerical reference in writing
The projection reserves the field of the closure
and follows the digital target. The contract for a return by this field retains
both reservations at the appellant.

The inference of `branch` collects the provenances of the returned handles
by the `break` d
fixed for paths that take over the loop and keep the constraint
existing on changes in links outside an expression.

An annotated body `branch` can start an inactive task received in
parameter. L
moving in a child's block, then attaching the handle
the body's auditor controls the
The connection concerns the types of the
In the case of specific tasks and the synchronous form of the contract.

Inference distinguishes the origin of an inactive task from that of the
d
the result of block, branch or loop, it gathers the
Inactive origins of paths that provide this value.
Alias and bonding joints preserve both
information separately.

The resolution of origins uses the type of concrete task of a
parameter from the control of annotation. It attaches a
manufactures synchronous to the inactive task that its signature returns.
For an auxiliary who returns the handle, it lowers the origin
from its body when building contracts, even in
absence of an annotation `branch` on the auxiliary.

The construction of the contract also follows a hand received and
The body analysis publishes the index
The call substitutes the origin of the argument to the parameter.
cet indice, y compris quand plusieurs branches peuvent fournir
The annotated statement must finally establish a
concrete launch in his body or in his calls.

The annotation check recognises that `join=result.await` for
an async function that returns a `AsyncHandle`. It establishes
the origin of the launch into the body, including after `yield`,
and transmits the pool found to the returned handle contract.
The lower control the type and the reservations of the handle.
The inference also follows a launch restored by waiting for a
Inactive task. For a direct call, it substitutes the origins
arguments when the body is waiting to relay a received handle.
For a task named or provided by a factory, it follows the
concrete launches of the type of task. For a task launched,
The analysis follows separately the origin of the outside handle and the
the load of its result.
`Ok` takes over the origin of the inner handle.
d , an injected handle, inference substitutes the argument for the
creation of the task then keeps this source until
The contract for a relay may be separately designated
The origin of the argument and the origin of its deferred result.
Inference replaces this second source when a
manufacture or synchronous relay returns task or handle
outside.

In async context, the result of waiting for a task to be launched can be
contain an autonomous AsyncHandle. `Ok` receives the handle.
result is destroyed or his handle ignored in the match, runtime
- I'm gonna take the cleaning back. `join` synchronous can also receive this
the arm `Ok` receives an AsyncHandle that can be abandoned or
transferred as an argument to an async task to be expected.

The public signature `Handle<AsyncHandle<R>>` identifies the result as
a separate handle. The conversion of a concrete handle to the signature
The public also maintains known information on autonomy and the
branch pool.

Waiting for an launched branch keeps the field targets separately
borrowed in case of success and failure of the launch. `match` affine
l , status from result. A later writing or replacement
d
ordinary and kept can touch the same field, analysis keeps
their union.

After `join`, the result also carries the success states and
d
establishes the effect. The analysis invalidates this information if the field is
rewritten or if the paths that join lead to results
different.

Synchronous tracking also distinguishes the installed proprietary fields
by the task and the pools that belong to them.
The launch results, the two states remain possible.
vectors also keep descriptions of possible elements
in this merged state.

In async, the source of a proprietary field whose initial pool
is monitored can be refined in the `match` of the result.
remains retained if it hosts the holder or if another link followed requires it.
When basic storage is unknown, the tracking keeps union of the
provenances possibles.

When the contract determines the state of a vector after `join`, the result
keep separately the positions, pools and source of the elements
for both exits. A subsequent mutation of the vector invalidates this
information.

A task directly expected can capture an AsyncHandle with dependencies
if its only parameter is expected from the first instruction and if
No returned borrowing or delayed field effect crosses this parameter.
The external expectation holds the loans from the handle until the end of the
receiver. The suspended path remains unavailable at the anticipated cleaning
As long as this expectation is in progress.

The effect analysis recognises the expectation of an AsyncHandle parameter.
It retains the recipient's termination contract and notes that the
cleaning of a losing Select arm can be blocked at this suspension.
An immediate call can thus transfer several handles
to dependencies when the receiver waits for them in its opening sequence.

The contract publishes the order of these expectations. The compiler applies the
regular updates of the handles captured in this order, then the
effects of the recipient body. It retains the possible states of failure
launch when the result of the internal wait does not pass
l’appel.

A delegated expectation also keeps updates kept on a
local mutex. The compiler applies them after outside waiting
keeping both the launch outcomes, then invalidating all
information about the outcome become obsolete for the fields concerned.

The borrowed result of a captured AsyncHandle can be used in
The compiler follows a local symbolic target
in this body and holds the actual target at the caller until the end
The external result remains scalar or Void.

If the recipient returns the digital loan, his contract identifies the
result of AsyncHandle parameter as origin. Lsappelant replaces
the origin of the hand actually transmitted, and
keeps the loan after waiting.

Tasks accept a shared loan from HashMap with scalar values
or with shared scalar references. The capture keeps the bearer and
The task can pass on the loan to another task.
or call a synchronous playback function from the existing deck.

The `match` direct on `HashMap.get` reads a numerical value in a
task async. The compiler checks the borrowing of the key and reserves the
table during the preparation of the search and then during use
the window view.

A mutable loan of HashMap with scalar values can pass through a
capture or call to synchronous function. `Some` of the
`get_mut` receives a writing view and reserves the table as much as it does
remains usable.

A task can build a scalar HashMap on its local stack.
Elle peut utiliser `insert` ou `remove` in a direct match. L'inclusion
prepare the key before the value and keep the mutable reservation of
the table during this evaluation. `Some` receives a copy of
l’ancienne valeur.

The results of the `get`, `get_mut`, `insert` and `remove` may be
appointed before `match`. A named search holds the table until
The final use of the result is extracted or used.
check-in takes over this reservation. The old scalar value of
`insert` ou `remove` can also be ignored.

`try_insert` with scalar value follows the same order of assessment as
`insert` The compiler connects its three exits to the
`match` Direct or appointed. `Err` extract the value refused by the table.
The analysis of contracts retains the type of this value and the old one
value, extracted by `Ok(Some)`.

A task that borrows a HashMap of shared scalar references
peut traiter `get` in a direct match or via a named result.
The arm `Some` Keeps a view of the box reading. `**` reads it
target. For borrowing types already supported, `*` copy the
reference and extend the reservation of the table until the last
use of copy.

A task can borrow a HashMap from `A<T>` Digital. `get` donne
read access to the target. `get_mut` autorise `**case = valeur` with
a reservation of the box and table during the evaluation of the
value. Writing retains the allocation and its pool. Calls
synchronous from a task with such a mutable table require
another contract for the transfer of the owner entries.

A proprietary table built in the task accepts `insert`,
`try_insert` and `remove` for digital allowances.
transfers the allowance and checks that his pool can survive at the table.
The result keeps the possible pools of the old separately
allocation et de l’allocation refusée. Le `match`, le `drop`, la sortie
The scope and destruction of a suspended frame connect the cleaning
The key tracking covers the literals and links
immutable initialized by a constant followed. `remove` on such a
key detachs pools from the known entrance, with maintenance of dependencies
common to other entries and unknown key entries.
`try_insert`The graph retains the two possible exits.
`match`, `Err` restores previous dependencies and `Ok` installe
a later mutation that may affect
the same entry invalidates this information. Unknown keys keep
a conservative union of provenances.

A local table with scalar shared references checks that the
targets survive his telescope. `insert`, `try_insert` and `remove`
The following are the key-based loans:
the possible values until their last use. `match` transmet
the recipient the dependencies of the extracted or refused reference.
When the task lends this table to a synchronous function, the contract
d
The possible paths are merged and the results of the
previous mutations are invalidated for keys that may be
recouvrir.

For a synchronous caller, a task that inserts a reference directly
in a table captured by mutable borrowing publishes the paths of sound
contract via the deferred effects mechanism. Creation controls the duration
The target life rate is the same as the table. `join` merges states
before the `match` Distinguishes success from `LaunchFailed`.
This route covers the insertions in instruction, the branches
on scalar expressions of parameters and `yield`.

The same integration contract spreads from a child task to a table
The local task of calling. `.await` direct publishes the entries of
for the end. `execution.await`, the compiler keeps the states
and refines the dependencies of the `match` of the outcome.

An intermediate task can relay table, key parameters
and reference to a synchronous function or child task
The compiler composes the paths and recaptures the
their parameters in the intermediate task contract.

The relay launched also follows both arms of a `match` on `.await`,
for a direct launch in the subject or a named handle.
of waiting can also be appointed before the `match`. `yield`
can separate launch, wait and observation from the result.
The successful arm adds the child's writings before his own
effects. The arm `LaunchFailed` starts with the pre-
launch. Other handling routes, the effects of branches
Select suspended and transfer of proprietary entries by a call
restent ouverts.

Reference table contracts represent the `remove(&clé)` in
instruction by an effect without incoming value.
input if key is known at call. A dynamic key keeps
the possible dependencies. Synchronous and asynchronous relays
keep this effect in their paths of termination.

For a table of `A<T>` digital borrowed by a task, `remove`
in instruction destroys the extracted value. The contract targets the graph
In the meantime, a known key allows for the
to remove the entrance and its pool dependencies. A failed launch
keeps both states until the result is observed.

The contract also covers `insert` in instruction when a task
transfers one of its parameters `A<T>` Digital at the table.
keeps the pool of origin, checks its lifespan in relation to the
table and replace the entry for a known key. Task code
destroys the old allowance when the instruction ignores the result.
For `try_insert` on a borrowed table, the compiler follows the
`match` with a direct or appointed result. `Ok(Some)`
and `Ok(None)` publient l’insertion. `Err` preserved the previous state of
the table and restores the input value to the arm.
of extracted values also applies to `insert` and `remove`.
The inter-processual return of extracted values remains open.

A task may call a synchronous method carrying a contract
`lock` direct and receive its owner's result in a link
local. The frame graph retains the origins of `self` until
destruction of the result. L'analyse refuses a new acquisition
on a common origin and a copy of the result.
on a task-bound body and the catches of this
instance while holding the lock remain conservative.
moving to a local receiver, including a block exit or
a replacement, keeps the reservation and controls its life.
A synchronous function can consume the value or restore it
directly to the task. Reservation remains active during the
The contract of origin links it to the
result if it returns the parameter. Copy effects inferred after
body verification is applied to calls that transmit or
The value of the data is used to determine the value of the data.
synchronous functions reveals an additional lock effect, the
compiler regenerates frames with inferred contracts.
indirect acquisitions, separate proceedings and
direct owner results are then checked at call.
A result with a lock can be transferred to a child task
With scalar result or `Void` whose body consumes the value locally.
The compiler extends the reservation during the construction of the
the task, then until its destruction or the end of the waiting.
body control accepts scalar connections and operations,
blocks, branches and local cleaning. When the child returns
directly the owner parameter, the contract of provenance
transmit the reservation to the result of `.await`On a handle launched,
arm `Ok` forward the reservation to the recipient and `LaunchFailed`
free it. L
return synchronous. The contract of the function must identify exactly
the parameter and exclude its copy and the acquisition effects or
d
return the parameter via a directly expected downside task.
The compiler tracks the provenance through this chain and checks
the body of each task that transmits the result.

A task can acquire a lock and then return the value that the
maintains if the instance comes from a borrowed parameter.
spreads this source until contracts are stabilised and the
The task or its result is linked to direct calls.
synchronous factory can also transmit the reservation if its
contract identifies the original capture.
the public shall retain a projection of this capture of results, even
when the signature erases the concrete task.
calling to reuse this provenance through erasure.
The relay via a handlance launched into the child remains open.

The inference of the initial waiting sequence of the `AsyncHandle` accepte
lexical blocks, literal links and `yield` before
She also counts the waiting in the subject
d’un `match`. The effects of the arms come after this expectation and
stop the initial sequence. L
Keeps reservations during suspensions.
following the handle can perform scalar calculations without calling
The receiver can also return a scalar board
by the existing table result path. After consumption
d
produce an allowance or a new one `AsyncHandle`. The return of
The allowance follows its contract of origin and the new handle must
satisfy the control of autonomy.

A synchronous call for a wait or relay contract may receive a
handle with effects kept with copyable arguments or other
The compiler checks the targets and effects of others
The following are the main points of the analysis:
They must remain disjointed from the mutex, its charge and targets that
The pool settings are compared to the
sources of the handle, its load and installed targets.
independent is allowed. A common pool remains admissible for reading
if the contract does not provide for any allowance or reset on it.

The compiler keeps the positions of a vector of values online
when a mutable capture is made if the task contracts establish
no change in the elements at termination and at termination
If the termination contract describes any
exact withdrawals without addition or replacement, direct expectation
reconstruct the remaining positions.
the compiler retains both states and distinguishes them in the
`match`. A subsequent transfer invalidates this information.
exact additions and replacements also rebuild positions
where the contract resolves the source of each value.
fields and pools of children owners are attached
a value re-inserted from a box of entry
The last element of the known case retains the dependencies of the case.
can be solved from the exclusions and the contract lag.
An indeterminate source keeps conservative follow-up.
positions are exact, compiler rebuild dependencies
For a vector created in the task, the pool
of its own storage is tracked separately. A known withdrawal may
so release the exclusive pools to the removed element as soon as its
Recipient is destroyed.

The recipient's inference of a closure follows the lexical aliases of a
The entries by de-reference, the
The number of assignments is as follows: `match` and calls for
mutable receiver or parameter request the mutable reborrowing of the
capture. A link that hides the capture stops transmitting
The results of blocks, `if`, of `match` and
`break` d-a loop is followed through their lexical connections.
The reassignments d
of the `if` and `match`. Origin is retained if present
on a path that continues. Branch-specific connections
are removed before this fusion. In loops, the covers
and the `continue` make the origins converge as they enter.
The state of the `break` and exits from `while` are merged
The result of a loop is the origin of the
value of `break` from this stabilized state of analysis.
Terminal expressions of blocks and arms use the same
path analysis to follow reassigned aliases before the result.
The call for a captured closure is analyzed from the signature
of its methodology `invoke`. For methods resolved on an alias,
The analysis examines the recipient and the explicit arguments.
The explicit reborrowings retain their origin of capture.
indexed projection uses the element type to track a
loan or an allowance stored in the table.
The selection of the method of borrowing also applies to allowances
A detected scripting results in a receiver
mutable and through the projection owner of the field.
The recipient's analysis recognises the mutable table borrowings in the
the signature and specialized operations of the parser.
Division into mutable views, replacement and exchange.
The preparation of the closures precedes the inference of the contracts.
stage, a known signature call that receives a loan from
d-a capture and return a loan propagates a possible origin.
The verifier then uses the sources of the contracts to
control borrowing.

HashMap transfer contracts substitute a constant key for a
key parameter when a synchronous or async relay. The table and the
inserted value keep a source of parameter.
absent from effect remain controlled by regular verification
- I'm sorry.

Other outbuildings handlries, returns are open
d’`AsyncHandle` by means of a task launched separately, indirect entries via the closure catches and the
Async compositions of lock access and HashMap operations.

No written tests or tests performed for these lots.
Python of modified modules does not validate Crust programs compiled
or the C generated.

<a id="revue-token-par-token-des-représentations"></a>

### Token review by token of performances

First pass from the four range and displacement cookies
already recognized by the syntax pass, then forms of closure of the
The reconstruction describes the facts of the tokens.
No parser, auditor or program was executed for this pass.

| Source | Relevant Tokens and Reconstructed Representation |
| --- | --- |
| [Enter block]](../../examples/invalid_child.crb) | `fn main` creates the declaration and its body scope. `let mut memory` creates the pool's mutable link. `pool<i32>(1)` wears the type and capacity. `memory.new(10)` creates the address and its link from where it comes to this pool. Internal hugs create a child and its entry point. `move data;` The two uses of the link between parent and child bonding and the address of the child are `*data` each have a point of execution and a fixed connection in their scope. |
| [Block with receiver](../../examples/invalid_transfer_alias.crb) | `let received =` means the destination. `move original;` makes the address accessible under the child-link. `original` connects the output to `received`. Names `original` and `received` After the block remain two separate links. |
| [Value pass](../../examples/invalid_function_move.crb) | `fn consume` defines the body and parameter. `A<i32>` bear the allocation form and the element type. `consume(data)` connects the argument to the activation parameter and retains the source of the pool. The following use keeps the identity of the original link. |
| [Pool declared in the child](../../examples/invalid_allocator_escape.crb) | `let result =` connects the block exit to a parent receiver. `local.new(42)`, in final position, connects the address produced to this receiver. `local` identifies the pool whose scope remains the child's. |
| [Closures](../LANGUAGE_RULES.md#closures) | Bars identify a callable value and its parameters. Annotations carry the types of parameters or result. The braces identify the body. `move` Each external occurrence in the body is connected to a source link and its capture field. The call parentheses create a separate operation from the creation. |

Judgment at arbitration on the capture of a reference shared with
`move`V3 reserves the copy to `copy` the primitives.
Closes describes both a global transfer with `move` and one
copy of the reference shared in this same context. L
carry the source, field and target in both cases.
effective capture link and availability of source link
Depending on the decision.

User confirmed that field captures shared reference
by displacement under `move`. Source link retains point
d − execution of the displacement, associated with the path which carried it out.

| Sources covered by recovery | Additional facts from the Tokens |
| --- | --- |
| [Retours conditionnels](../../examples/conditional_returns.crb), [if with receiver](../../examples/if_expression.crb), [provenances](../../examples/provenance.crb), [conditionnelles](../../examples/conditionals.crb) | `if`, comparison and `else` identify possible entries. Terminal expressions and `return` identify the destination of the value. `return` The other paths bring their state to the junction, with their original identities and pools. |
| [Boucle](../../examples/loop.crb), [continue](../../examples/continue.crb), [while](../../examples/while.crb) | `loop` and `while` identify the entry of iteration. `break` and `continue` Wear their destinations and the lost sights. `while` has a separate exit. `temporary` identifies a body bond, with an instance of the allowance for iteration. |
| [Reassignment](../../examples/reassignment.crb), [arguments](../../examples/arguments.crb)[mutability]](../../examples/let_mutability.crb) | `mut` carries the ability to modify the link. `=`, `.set` and `*` The orderly arguments of the `consume` keep the interlocked call of `read` before consumption of `data`. The replacement forms retain the old address and the address produced on the right. |
| [Retours d’emprunt](../../examples/direct_borrow_returns.crb), [retours mutables](../../examples/mutable_borrow_returns.crb), [borrowed fields](../../examples/borrowed_returns.crb), [champs mutables](../../examples/mutable_reference_fields.crb), [match nominal](../../examples/main.crb) | `&`, `&mut`, `.vref` and `.mut_vref` The arguments and returns link the parametric origin to the specific target. The variant and field names identify a position in the carrier. `match` and the patterns link the subject to the arms' entrances and connections. |
| [Drop](../../examples/drop.crb), [reuse](../../examples/drop_reuse.crb) | `drop` means the consumption operation. `.new` identifies a new allocation, even if the pool re-uses the slot. `address` designate the two allocation identities at the points where they are observed. |

New stop on the witness of [capture shared without move](../../tests/test_closures.py)
who writes `let read = || { *vue };`. Bars and use of `vue`
The grammar admits this form of the term "indulgence" and its connection to capture.
and noted that catches without `move` The witness is still to be specified.
history is waiting for a copy of the reference. With V3 and the transfer
confirmed under `move`, the mode of this link without marker remains to be fixed,
or the requirement to `move` for this capture.

<a id="parcours-du-corpus-sans-arrêt-darbitrage"></a>

#### The corpus journey without interruption of arbitration

The capture without marker retains the source link and its destination.
The actual mode of representation remains unknown.
continued on Rust/Crust document blocks, text blocks
identified as code, Crust sources d`examples` and
`validation`, and the Python literals of `tests` identified as
code Crust.

| Origine | Programmes or declarations | Block Fragments | Signature Fragments | Tokens represented |
| --- | ---: | ---: | ---: | ---: |
| Documentation | 23 | 9 | 2 | 1 420 |
| Fichiers Crust | 38 | 0 | 0 | 3 633 |
| Literals Python | 889 | 1 700 | 105 | 77 754 |
| Total | 950 | 1 709 | 107 | 82 807 |

The [corporeal constructor](../../validation/build_representation_corpus.py)
uses the syntactic input of the core. The fragments are read with a
block envelope or a synthetic signature body, marked as
fragments. Leurs tokens d’origine restent identifiables. L’inventaire
The report does not contain any information on the nature of the work, the nature of the work and the nature of the work.
sources generated by Python execution or informal examples
scattered in prose.

Each recognized occurrence has a structured and
The facts extracted from the tokens, the telescopes and the knots.
include links, catches, pools, constructions, projections,
calls and outputs. Sliders, some type links and
sources requiring semantic resolution remain symbolic
The journal has not exercised any rule and has not performed any
programme Crust.

<a id="frontend-rust-et-comparaison-du-corpus"></a>

### Frontend Rust and corpus comparison

The [Rust crater]](../../rust_frontend/README.md) reads the text, produces the tokens
with positions, parses statements and expressions and builds
static shaft with scope identifiers, links and points.
The construction distinguishes the declarations from the uses of name and
maintains links to catches, projections and destinations
The annotations are shown in the tree.

| Origine | Corpus | Rust recognizes | All the projections compared are consistent |
| --- | ---: | ---: | ---: |
| Documentation | 34 | 34 | 33 |
| Fichiers Crust | 38 | 38 | 37 |
| Literals Python | 2 694 | 2 686 | 2 620 |
| Total | 2 766 | 2 758 | 2 690 |

The 2,758 common occurrences are consistent with the standardized lexems,
the parents and lines of the scopes and the ordered list of names
The other 68 common projections diverge.
on the facts extracted or the links of displacement named.
Python omits constructions in particular `.new` with designated fields and
native thread moves. The eight refusals Rust
concerning pieces of Python littoral assembled with other
sources, including block ends and incomplete function beginnings.

The comparison is directional since the occurrences recognized by
The Python corpus and the projections listed.
neither the general grammatical equivalence nor the complete identity of the
Trees. No rule checker, C generator or Crust program
n , was executed.

<a id="vérificateur-rust-et-génération-c-du-sous-ensemble-scalaire"></a>

### Rust Auditor and Generation C of the scalar subset

The verifier reads the liaison identifiers and the uses of the
The resolute signatures determine the type of arguments.
The branches spread the state of the links on their roads of
continuation. For local borrowings, a reference shall be retained
The identity of its target through a displacement.
access takes account of active bookings and control of
destination compares the target and receiver scopes.
Generator C receives the typed instructions from the verifier.
Temporary workers materialize the order of the operands and arguments.

Four programs were compiled in C11 with Clang, the
warnings processed in error and UBSan without recovery.
The expected outputs were obtained for the loan transfer,
the displacement then drop a reference, the conditional return
and the rest of the minimum signed by less one. Six targeted refusals were
They cover the use after displacement,
consumption on a path, a conflict of borrowings, a result
mistyped, literal overflow and zero division.

This pass covers part of the eight rules. Reservations are
lexicales unless explicitly drop. Last use, borrowings
in signatures, reborrowings, loops, aggregates, pools,
destroyers and async effects remain open in the Rust.

<a id="graphe-de-contrôle-dernier-usage-et-boucles-dans-le-rust"></a>

### Control graph, last use and loops in the Rust

The graph links the condition to the branches, the covers at the entrance of the
loop, breaks at their continuation and returns at the end of the
function. A back analysis calculates the links that remain in use
The auditor consults these facts with access to a target.
For a simple scalar assignment, he checks the reservation at
point of writing after the right assessment.

Auditor merges the states entering the first iteration
and by the re-runs until stabilization.
combines the broken and the false outcome of the `while`. The C evaluates the
conditions for each recovery and issues `break` and `continue` natifs.

Six C11-compiled cookies with error warnings and UBSan
produced the expected outputs. They cover the last reading,
separate branch reservations, breaks and recoveries,
reset before restart, read during iteration
and the last use in the right side. Five targeted refusals
have been confirmed without C emission, including post-movement use
on recovery and two conflicts with one loan still in use.
The perimeter remains that of synchronous scalar and local references.

<a id="réemprunts-contrats-de-références-et-boucles-à-résultat-en-rust"></a>

### Reborrowings, reference contracts and result loops in Rust

The auditor retains the target and parent couple of each
from where. A re-borrowing still used reserves the parent, including
The arguments already evaluated
keep their reservations while preparing the next ones.
For a borrowed return, the contract lowers the parameters of
The call replaces the concrete origins.
recursive may keep a conservative approximation of the contract.

A result loop installs the value of the `break` in a
the temporary reception. The verifier retains the provenances
of all `break` who reach this receiver and refuse a target
or a parent created in the loop that must disappear at its exit.

Eight witnesses produced the expected C11 outputs under UBSan.
Eight refusals were confirmed without C emissions, including two aliases
d , two accesses to one parent reserved, two local targets
escaped, a writing incompatible with a possible source
and an incompatible loop result. This batch covers the
scalar references and synchronous functions.
Pools and l'async remain open.

<a id="placement-fixe-dans-le-compilateur-rust"></a>

## Fixed placement in the Rust compiler

Post-AST analysis links constructions, movements and receptions of
synchronous structures with scalar fields. It places the reservation in the
scope that covers the final destination, includes exclusive constructions
d
call. A result transmitted from a parameter keeps its address.

`cargo build --offline` and `cargo fmt --check` Four witnesses have passed.
were lowered to C11 and then compiled and executed with
`-Wall -Wextra -Werror -fsanitize=undefined -fno-sanitize-recover=all`.
The child block produces 7. The conditional produces 10 and 30 and each pair
The interfunction relay produces a common position.
42 and transmits the output location or the address of the parameter according to the
The two constructions which may coexist produce 41 and 42
and C contains two locations per call.

This validation covers the placement by automatic storage C. The calculation
sliders of the datastack, other fixed types and placement of the
values whose life span implies l

<a id="datastack-à-curseur-dans-le-backend-rust"></a>

### Slider Datastack in the Backend Rust

The post-AST plan provides bookings for structures, links,
The blocks and calls in position of the
The result can directly transmit the receiver slot.
the ranges aligned in an anonymous mapping and restores the cursor to the
output of telescopes and calls, including on `break`, `continue` and
`return`. The intended storage at the appellant is prior to the mark of the
callee.

`cargo build --offline` and `cargo fmt --check` On macOS, seven
compiler with `-std=c11 -Wall -Wextra -Werrar
-fsanitize=undefined -fno-sanitize-recover=all` à `-O0` et `-O2`. Ils couvrent
a structure up from a block, the arms of structure to a location
a call relay, two co-existing constructions, returns
scalar through blocks, a mutable loan returned and then used, and
a loop with `break` and `continue`. C confirms reservations
d `crust_out`.
Four additional witnesses to the `-O2` cover an empty hand, the code of
exit, a loan return shared from a mutable reference and
the exit of a while by its condition.

With the capacity reduced to 64 bytes in the C of the loop tell-tale, the
20,000 iterations are over. At 1 byte, the first reservation of eight
Bytes leaves with code 1 and the expected limit diagnosis.
The change was not implemented on the basis of the general and independent audit.

The backend covers fixed types already checked. Other fixed types,
the capacity resulting from static analysis, explicit configuration and
datastack to regions remain open.

<a id="extension-du-placement-des-types-fixes"></a>

### Extension of fixed type placement

The backend Rust lowers the primitive digital core, the paintings
The following are the main features of the project:
local pools. The post-AST plan recognises these aggregates as producers
d
The backend calculates the alignment
from type C storage and has nested fields online.
The d-enums pools reserve a payload area per variant.
cleaning records release slots before the recoil of the
a release inside is reusable at the limit.

Eight new C11 and seven previous controls are passing on macOS under
UBSan, at `-O0` and `-O2` with `-Wall -Wextra -Werror`. New witnesses
cover the six primitives added, conditional returns of tables
and d   , interlocked fields and local pools with re-use of
slots, end-of-block cleaning and separate areas by variant.
The four additional controls to be carried out `-O2` cover writing
indexed, a negative dynamic index, an empty table and an exhausted pool.

Eight refusals are confirmed for a recursive type online, an index
constant out of bound, a literal `u8` off-shore, a mixing operation
a whole literal and a floating, a floating zero division,
a non-exhaustive match, an immutable pool and a drop of pool still
The checks are for the synchronous sub-assembly Rust.
Pool and allocation signatures, dependency aggregates
and aggregate space borrowings remain open.
and the independent audit were not carried out.

<a id="dépendances-des-agrégats-et-transferts-de-pool"></a>

### Aggregate dependence and pool transfers

The auditor keeps the roots of borrowing in the structures, tables
and variants. It distinguishes the address of one parameter by value of the
dependencies brought by this parameter, checks block outputs and
collects the possible provenances before producing the post-AST plan.
The re-borrowing of a reference
mutable stored in a local aggregate also reserves its support.

The pool is borrowed without moving its area. `A<T>` transmitted by
value and keeps its payload address. Its metadata is in the
pool, with a cleaning mark that follows the receiver, including on
`break`, when a call is made and when it returns. The return distinguishes the roots
Payload's dependency pool. A match on an allowance reads its
tag and then payload the variant in the corresponding slot.

On macOS, `cargo build --offline` and `cargo fmt --check` passent.
`python3 validation/check_rust_placement_dependencies.py` confirme
14 witnesses C11 to `-O0` and `-O2` UBSan with warnings treated in
errors, and 10 refusals with diagnosis.
d , a box, borrowed aggregate returns, conflict of writing,
pooling on several calls, choices between two pools, the
read a pool variant, re-use after consumption and
refusal to escape a pool or local pointer.
witnesses of the two previous passes also pass to the two levels
d’optimisation.

The source is followed by union at the aggregate scale.
approximation may refuse valid programs that require proof
the distinction between two fields or two boxes.
a sum of the aggregates and the motifs borrowed from the aggregate fields
The general follow-up and independent audit are not yet complete.
were implemented.

<a id="provenances-par-position-et-match-emprunté"></a>

### Sources by position and borrowed match

The auditor keeps the path of each dependency in a value
and, for a return contract, the corresponding path in the argument.
The paths combine variant, field and index. The selection of an index
The control graph keeps the data in the
sites of use and separates the match arms. A direct loan from case
reserves the root according to E6. For a stored reference, the
reborrow reserves the selected position and suspends accesses which
may cover it, including through the reference to the aggregate.

A pattern on a borrowed enum binds an aggregated field by its address and
keeps the shared or mutable mode. For a pool enum, the address
means the payload of the slot of the variant. The post-AST placement plan
and the datastack runtime remain the same.

`cargo build --offline` and `cargo fmt --check` passent. Huit nouveaux
C11 controls go under UBSan to `-O0` and `-O2`. Covering provenance
fields and boxes in contracts, a result that changes the
positions, last use of a field, two separate borrowings via a
borrowed aggregate, reading a disjointed field and borrowed patterns
on a table and a pool field. Six targeted refusals cover the
dynamic recoveries, the reborrowable loan via a reference
shared, destruction of the parent or slot before the last use,
and the conservative provenance of a recursive result.
`python3 validation/check_rust_placement_dependencies.py` rejoue ces cas
and the fourteen witnesses and ten previous refusals.

An unsolved index and a recursive contract still unknown keep
all candidate sources. The verification is limited to the
Backend Rust synchronous and targeted functional cases.
and the independent audit were not carried out.

<a id="dimensionnement-de-la-datastack-classique"></a>

### Dimensioning of the classic datastack

The parser accepts optional global annotation and its properties.
The check converts positive decimal sizes into bytes,
controls overflow and transmits property `size` Backend.
It takes precedence over the terminal and the defect. A reservation that exceeds this
capacity stops the program according to the existing limit diagnosis.

Quand `size` is absent, the compiler extracted from the post-AST plan
real reservations, the portable porter brands and calls
since `main`. Both branches are measured from the same cursor.
An iteration includes the test and body, then returns to its mark.
The caller's anticipated locations, parameters and area
The aliases don't reserve any bytes.
The backend C calculates the terminal at start with `sizeof` and `_Alignof`,
without evaluating program expressions. Calculation and reservations
real share the arithmetical alignment verified. A call cycle
accessible triggers the capacity failure at runtime.
inaccessible since `main` Don't change the line.

On macOS, the script `validation/check_rust_datastack_capacity.py` execute
ten witnesses C11 to `-O0` and `-O2` under UBSan. L-instrument compares the
maximum capacity of the observed cursor. The alignment paths selected
The loop of 20,000 iterations reaches 144 bytes.
Witnesses also check calls, pools, 1 Kio priority
with a deduced or unknown terminal, the defect in recursion and stop
when an overrun of 1 Kio is made. Six annotations are refused for size
null, hexadecimal, invalid unit, repeat, overflow or position
The empty shape and a region property alone
37 witnesses of previous placements and borrowings
also go under UBSan to both levels of optimization.

The term may be conservative. The terms of the program are not
not evaluated to eliminate paths and no maximum number of calls
The regional datatack and the independent audit are deduced.
remain outside this cycle.

<a id="datastack-à-régions-dans-le-backend-rust"></a>

### Datastack to regions in the backend Rust

The descriptors for non-dependent fixed element vectors and non-dependent vectors
chains stay in their pool slots, on the classic datastack.
Their contents grow in a stable address range, with only one
cursor. The occupancy register reuses holes when the
cursor reaches the limit. Release of a suffix moves the cursor back.
Un transfert d’`A<T>` The area and its boundary are retained.
closed remain mapped until the last contents are released.

The overall configuration applies explicit priorities separately,
deducted, default for `region_stack_size` and `region_size`. The plan
post-AST increases slots by the capabilities of pools that can
coexist, and bytes by sum of bounded additions.
loop gives an unknown size without preventing the slots from being deduced.
The backend evaluates ABI-dependent sizes with `sizeof`. The
unknown template uses 100 Mio. The unknown global capacity uses the
The same memory estimate as the classic datatack.

A local annotation with different template or `count` explicite ouvre
a dedicated tape. An identical template without `count` re-use the
inherited configuration. When local number is omitted, estimate
static slots serve as a conservative terminal. If unknown, the
tape starts with a slot and can use dedicated tapes
The output of a telescope restores its configuration after
cleaning, including cleaning `break`, `continue` and `return`.

`python3 validation/check_rust_regions.py` C11 compile with
`-Wall -Wextra -Werror` and UBSan to `-O0` and `-O2`Seven witnesses cover
the deduced provision, UTF-8 and the null bytes, the re-use of a hole,
the overflow of the number of local slots to a dedicated band, the
transfer of a region, inheritance via call and loop covers.
Two exceedances trigger the expected diagnosis.
The 47 previous witnesses of placement,
d
niveaux d’optimisation.

The cycle covers the synchronous uses supported.
not the connection of `HashMap`, the vector elements bearing
dependencies, string views and async or multithread states.
The independent audit was not carried out.

<a id="collections-à-dépendances-et-régions"></a>

### Dependent collections and regions

Backend Rust places the HashMap descriptor with primitive values
Each table keeps a chained index and its contents.
The index has 16 compartments.
collisions are resolved by chaining and comparing the complete key.
The replacement keeps the address of the entry and the deletion
makes its location reusable. Post-AST computing limits a
statically inserted by an input plus the initial index.
cleanup follows the receiver even if the table keeps an address placed
In a more sustainable scope. `get` and `get_mut`
protect the table until their last use.

A vector can carry shared or mutable references and take
in charge of `A<T>` The integrations are based on several pools.
dependencies, including conditional exits and repeats
loop. An inserted handle leaves the cleaning list of its old one
The destruction of the vector returns to the vector's
the reverse order of insertion before returning the region.

On macOS, seven C11 and the 56 previous witnesses move to
`-O0` and `-O2` under UBSan. The script
`python3 validation/check_rust_region_collections.py` Replay the new ones
A supplementary loop-in tell-tale
in an area of 1 Kio comes out with code 1 and limit diagnosis.

HashMaps with dependent values, extraction operations of
vector handles and async and multithread connection remain
The witness is open. `async fn work(){yield;} fn main(){}` remains refused
by the Rust verifier before generation C. The Python prototype
has a separate runtime. Independent audit has not been carried out.

<a id="état-régional-des-threads-natifs"></a>

### Regional status of native threads

The backend Rust is down `runtime::thread({ ... }).join()` with a state C
separate by block and a worker pthread. Scalar catches
reported as the highest by `move nom;` are evaluated in order, displaced
in this state before launch, then received in worker settings.
The block returns a scalar or `Void`. The result of the join is lowered
in variant `Ok` ou `Err(LaunchFailed)`.

The post-AST plan reserves the result at the appellant and includes a
region for the launch state. It calculates separately the terminals of the
The caller and the workers' datatacks.
and the region metadata of the worker are isolated by local storage
The only state of launch is shared. L
before creation, the worker writes his result, and the caller reads this
result after `pthread_join`. The worker cleans his own values
The appellant released the area from the state after the
read directly if the launch fails.

`python3 validation/check_rust_native_regions.py` execute five witnesses
C11 with `-pthread -Wall -Wextra -Werror` under UBSan to `-O0` and `-O2`.
They cover the growth of a vector in the worker while a
the appellant's region remains alive, re-use of a slot after
40 joins, two interlocked workers, scalar catches and the
Reuse of the slot after an injected launch failure.
refusal cover implicit or dependent catches, use
after capture displacement and suspension in a block
The 63 previous controls also go under UBSan to the
deux niveaux d’optimisation.

ThreadSanitizer leaves with code 139 without diagnosis on the control
and on a minimum C programme calling only `pthread_create`
and `pthread_join`. It does not provide a workable result here.
The passage covers only the immediate join.
aggregate results and anticipated scalar returns of blocks,
the catch with dependencies and the async lowering remain open.

<a id="handles-et-contextes-async-en-région"></a>

### Regional async management and contexts

A native launch produces a moving handle.
block receipts and calls update responsibility
The runtime restores the area
after a join or co-ordinates the abandonment and termination of a task
A self-contained scope output will only abandon tasks whose
The end of hand awaits the tasks
The auditor monitors the borrowings of the
scalar in return contracts, blocks competing accesses
and refuses the exit of a dependent handle on a path that
I'd give up the job.

An async function creates an inactive Future in the region.
take effect at its creation. `runtime::spawn` consumes the Future
and publishes its state in the runtime line. Two polluters can
resume a task after `yield`. The recovery restores its context
of datatack, which keeps the address and the limit of its
The post-AST plan describes the links placed
in the state, its size and the storage terminals of the task.
Context exchange occurs after each poll, and cleaning
the context precedes the restitution of the region of the state.
taken catches remain active after spawn until join.
Over failure of running start, Future is cleaned and the
join restitue `LaunchFailed`.

`python3 validation/check_rust_task_regions.py` compile ten witnesses
C11 with pthread and UBSan to `-O0` and `-O2`Nine targeted refusals
confirm the reservations of the catches, the prohibition of the
abandoning the boundaries of the scope and the consumption of the handle.
The controls cover success, failure of injection start,
The self-reliant abandonment, the coexistence of a thread and a Future
using different targets and growing collections
The 68 previous witnesses pass through the suspensions.
also under UBSan at both levels of optimization.

The audit covers scalar borrowing and the
suspensions `yield` She doesn't force a
migration to a different polluter and does not cover `.await`, nor
interlocked suspensions, nor the catches and results aggregated with
ASan's attempt on a mixed witness did not provide any
A minimum C program under ASan, limited to create and
join a pthread, also exceeded its deadline.
The independent body was not executed.

<a id="attente-directe-et-agrégats-empruntés-dans-le-backend-rust"></a>

## Direct expectations and aggregates borrowed from the backend Rust

The post-AST plan numbers the suspension sites and associates them with the state
regional temporary and scope marks. `.await` direct consomme
a Future inactive and poll on the current worker. If the child suspends,
the parent keeps his condition and resumes the poll of the same child.
completion, the result is transmitted in a location of the parent before
The marks retained in the state of the child
allow blocks, branches, `break` and `continue` restore the right ones
sliders after resumption.

Fixed catches and results containing borrowings are stored in
The Future has two distinct sets: active dependencies
the contract of the result projected on the
The loop branches and outputs keep this information.
One witness returns only one of the two loans captured and writes on the other
target before last use of the result. Another crosses two levels
The first execution of the witness of the
loop revealed a shift of the index: the tell-tale now uses
`copy(i)`, in accordance with the value-by-value rule.

Validation performed: `cargo build --offline` the Rust frontend;
`python3 validation/check_rust_task_regions.py` (15 programmes implemented,
13 refusals) and the follow-up `check_rust_{datastack_capacity,native_regions,
placement_dependencies,region_collections,regions}.py` (53 programmes
C11 with UBSan to `-O0` and
`-O2`They are used, among other things, for the consumption of children, for the
re-use of a regional slot and refusal of a result to a target
Local migration between pollers is not imposed by the witness.
ASan and the independent audit were not carried out in this pass.

Limits: aggregates with a resource to clean, dependent results
via `join()`, synchronous calls from the async body and
`runtime::AsyncHandle.await` Stay open in this backend.

<a id="ressources-et-complétions-de-tâches-dans-le-backend-rust"></a>

## Resources and task complements in the backend Rust

The post-AST plan remains responsible for the results locations and the
brands that survive suspensions. For a fixed aggregate that has
`A<T>`, the generated code transfers responsibility for each slot to
through the task cleaning register, without moving the data from
pool. The cleaning of the state distinguishes the catches of an inactive Future
a successful transfer connects the slots
before he can use them; a abandonment or failure
destroys what the state still has. The consuming game transfers the
load to the field bound by `Ok` or destroy it if the motive ignores.

Contracts distinguish between the dependencies of performance and the
The latter pass through a signature
typed and are attached to the path `Ok` of the `Result<R, runtime::Error>`.
The way `Err(LaunchFailed)` does not carry any result dependence.
Native threads can also make a fixed value to borrowing.

`spawn_blocking` launches the Future on a thread dedicated to async context.
Waiting records the root polluter before hanging, even if it
The transition to the
sleep and notification of completion share the same lock.
notification arrived before sleep is kept; after sleep
it puts the polluter back in line. The completion publishes the result
before the alarm clock. `LaunchFailed` cleans the catches before
Hand back.

Validation: compilation Rust offline; cookies for
`check_rust_task_regions.py` (27 programmes, 18 refus) sous C11/pthread/UBSan
à `-O0` and `-O2`, and the five Rust suites of placement, capacity, regions,
native collections and threads (53 additional C-witnesses). Witnesses force both orders between alarm clocking and putting
in sleep, inject both launch failures, read a result at
borrowing after a typed relay, and reuse the catch slots and
The first execution of the two slot aggregate revealed a
confusion between pool dependence and its exclusive borrowing;
contracts now retain this distinction.

Limitations: a pool slot or an aggregate vector element cannot be used
containing `A<T>`. Native threads do not transfer
No proprietary slots. Migration between pollers, ASan, TSan and
The independent audit is not part of this evidence.

<a id="nettoyage-composé-des-slots-possédés"></a>

## Cleaning composed of slots owned

Backend reuses the path of the home-owner fields when inserting
in a pool or vector. It links the slots found to the register.
The scope register contains no data on the number of children in receipt of the allowance.
the roots. The displacement of a root, including in a
Future, take its subtree without moving the data.
travels through the children before returning the area and the parent's slot.
He reuses the ties of the children removed to resume the journey,
without increasing the depth of the C pile. The post-AST plan keeps the
same locations and brands. L'analyse of exclusive borrowings
memorizes the types visited when a type refers via `A<T>`.

Validation under UBSan to `-O0` and `-O2` with the six suites
`check_rust_*.py` 84 programmes C implemented, of which four were implemented
New witnesses, 54 confirmed refusals, three new ones.
at the point of refund twice the same order in a pool
recursive. The terminal slot is returned, then the two link slots of the
The other controls cover the active field
d
transmission of a subtree through `.await`. Refusals cover
the release of a too short source pool, its explicit destruction and
The loan is stored in a vector that would survive.
remain usable after cleaning if their target still lives.

This cycle checks the cleaning generated by the compiler for slots
Crust does not support the defined destroyers
ASan, TSan and the independent audit are not part of the
of this validation.

<a id="provenance-et-résumés-du-post-ast-rust"></a>

## Source and summaries of the post-AST Rust

The post-AST keeps the link from the temporary received to its source and the point
the displacement of a local link. The dependency summary re-uses
The placement summary spreads the lists interned through the telescopes.
the origins by edges and keeps the results of the last calculation of the
This cycle covers the representation of the compiler.
normatives restent identiques.

Two Rust tests inspect the post-AST. The first checks the movement
of the `boite` To `recu` through two blocks, the same summary identifier
The path from the field to its pool and the reservation in
The second check that both branches keep the function scope.
their respective pools and storage origins and share the
destination of placement.

Commands executed from the root of the project.

```sh
CARGO_TARGET_DIR=build/rust_frontend cargo test --offline --manifest-path rust_frontend/Cargo.toml
CARGO_TARGET_DIR=build/rust_frontend cargo build --offline --manifest-path rust_frontend/Cargo.toml
python3 validation/check_rust_placement_dependencies.py
python3 validation/check_rust_datastack_capacity.py
python3 validation/check_rust_regions.py
python3 validation/check_rust_region_collections.py
python3 validation/check_rust_native_regions.py
python3 validation/check_rust_task_regions.py
```

| Suite C | Successful Witnesses | Confirmed refusal |
| --- | ---: | ---: |
| Placement and outbuildings | 22 | 16 |
| Dimensioning of the datatack | 10 | 6 |
| Regions | 9 | 3 |
| Collections in regions | 10 | 7 |
| Threads natifs | 5 | 4 |
| Tasks and recoveries | 28 | 18 |
| Total | 84 | 54 |

The suites use C11 and UBSan fatal to `-O0` and `-O2`. Witnesses
include controlled error outputs, including explicit exhaustion of
The datatack. No new failures were observed. Internal tests
inspect a specific transfer and a two-branch junction.
ASan, TSan, the deployments and independent audit remain outside this cycle.
No performance measurement was performed.

<a id="mesure-du-coût-des-résumés"></a>

### Measurement of the cost of abstracts

The two instrumental binaries were compiled with `cargo build --offline
--release`, Rust 1.99.1, macOS arm64. The front version was reconstituted to
from the sources and modifications of the previous cycle.
scanning to the fixed point, the second calculation of the origins for the
placement, former dependency unions and representation
of the `Value`. Checkout does not contain the old commit.

Each program is read and run once per process.
entoure `verify`, which includes verification, lowering and placement.
The measure of placement surrounds `placement::plan`. The generation of C,
the launching of processes and destruction of the result are outside
of total timing. On each case, seven batches of 35 measurements per version
follow eight heat passages per process.
The time columns give the median
The gains are the medians of matched reductions.
The 11 programs are accepted by both binary and produce
C identical byte for byte.

| Cas | Placement before → after (μs) | Gain placement | Verification and placement before → after (μs) | Gain total |
| --- | ---: | ---: | ---: | ---: |
| 4 interlocked blocks | 8,75 → 5,21 | 40,4 % | 14,83 → 11,33 | 23,6 % |
| 16 interlocked blocks | 21,00 → 11,25 | 46,2 % | 30,58 → 20,88 | 31,5 % |
| 48 interlocked blocks | 47,38 → 26,42 | 44,2 % | 66,38 → 46,04 | 30,6 % |
| 4 chain transfers | 13,33 → 5,38 | 59,7 % | 20,83 → 13,04 | 38,0 % |
| 16 chain transfers | 69,46 → 13,58 | 80,3 % | 85,96 → 30,54 | 64,4 % |
| 48 chain transfers | 477,79 → 28,33 | 94,0 % | 516,62 → 68,04 | 86,7 % |
| 4 jonctions successives | 24,25 → 15,75 | 34,8 % | 47,96 → 39,46 | 17,3 % |
| 16 jonctions successives | 101,42 → 67,42 | 33,6 % | 210,83 → 174,21 | 16,5 % |
| 48 jonctions successives | 487,42 → 389,17 | 21,1 % | 1 100,42 → 1 003,71 | 8,7 % |
| 4 interlocked junctions | 15,67 → 10,92 | 30,2 % | 28,42 → 23,96 | 15,5 % |
| 16 interlocked junctions | 59,92 → 37,42 | 37,7 % | 96,21 → 74,46 | 22,3 % |

The seven lots give a total gain between 83.7 and 87.0% for
48 chain transfers, and between 0.3 and 9.6% for 48 junctions
These synthetic programmes measure the combined effect of the
The isolated contribution of dependency unions and the
memory consumption of compiler still to be measured.

<a id="plan-de-possession-des-agrégats-dans-le-post-ast"></a>

## Aggregate possession plan in the post-AST

The post-AST selects the projections that lead to a owned slot.
The generator of cleaning routes consumes this representation
for structures, tables and variants. It translates links
internal in aggregate path and links to slots in calls
The order of the journey and the return of the children before
their parents follow the same paths as in previous witnesses.

Both Rust tests pass.
`check_rust_placement_dependencies.py`, `check_rust_datastack_capacity.py`,
`check_rust_region_collections.py` and `check_rust_task_regions.py`
confirm 70 C-controls on UBSan at `-O0` and `-O2`, ainsi que 47 refus.
Cookies cover the placement of recipients and reservations
by the caller, then the compound cleaning in a pool, vector and
Async state. Adoption and transfer sites still select
the action from the type of value.

<a id="adoption-et-transfert-selon-le-plan-de-possession"></a>

## Adoption and transfer according to possession plan

Generator C consults the possession plan to select the
value at adoption and transfer, including
The type of the call and in the catches and results async.
identifies the plan entry. This entry determines the course of the plan
fields owned.

The two Rust tests pass. The placement and outbuilding suites,
regional collections and tasks confirm 60 C-witnesses under UBSan to
`-O0` and `-O2`41 refusals. The witness is being used in a pool
recursive checks the return of the terminal slot, then the link
and finally from the root. He observes this sequence a
first time, then again after re-use of the same slots and
transfer from the root by a block exit and a call.
async exercises the transfer of a tree by `.await` and reuse
The slot-by-slot trace is about the synchronous tell-tale.

<a id="placement-des-scalaires-dans-leur-destination-finale"></a>

## Placement of scalar in final destination

G1 plan reuses the reservation of the result of a block or call
for its connection. A synchronous scalar moved directly to a
receiver or to the result of the function can also be initialized
in the final reservation. The plan verifies that this reservation is
accessible from the construction, that the displacement is unique and that
source link is not reassigned. Entangled calls receive
final address. Constructions located in exclusive arms
The other sources keep their own
own location when they could crush a living value.

Two Rust tests, 75 C and 47 refusals pass in the suites
dimensioning, placement dependencies, regional collections and
tasks. The five new cookies instrument the cursor under UBSan
à `-O0` and `-O2`. They observe a single 8 byte location after
interlocked block exits, for a return built at
the appellant, for a nested call and for two exclusive arms.
Two-source live control simultaneously observed two locations
and checks the value returned.

This pass covers direct promotions of synchronous scalar.
The links reassigned or to several movements keep a
The async states use their frame and the
Overall choice between several final telescopes remains open.

<a id="g1--chaînes-de-déplacements-destinations-multiples-et-frames"></a>

## G1 — travel chains, multiple destinations and frames

The plan follows the successive links to the final reservation.
For a value built before the choice of the path, it shares a
address when the external receiver or caller covers all the
The route and that the recipients redirected do not have independent entry.
For shared aggregate locations, it first examines the scopes
with the most origin of construction candidates and keeps the
groups already formed when the following candidates do not cover them
that's part of it.

The scalar received by a Future may be written in their own
final location in the frame. The pointers of the moved links
remain in the frame during suspensions.
aggregate compatible with result booking can write in
The proven co-existence candidates keep this result directly.
separate locations.

The conditional return witness of an owner aggregate exhausted the
pool. His address was reserved for the appellant and the path that kept
the local aggregate left a slot occupied after the return.
runtime now have a depth of independent possession of
physical address. Reception or return transfers possession
Only on the path executed. The witness covers both paths and
Then re-use both slots.

Two Rust tests and six backend C suites are completed, confirming
95 C-controls under UBSan at `-O0` and `-O2`54 refusals.
witnesses check the unique reservation through several links,
choices between two recipients or between a recipient and the appellant,
restitution on the local road and recovery after `await` and
`yield`. The C generated for the return tell-tale owner async contains
a construction directly in `frame->result`.

The plan remains conservative for reassigned sources and roads
the classification of the telescopes
applies to compatible candidates calculated by the plan and the
selection is gluttonous.

<a id="g9--placement-des-régions-à-partir-du-post-ast"></a>

## G9 — Placement of regions from post-AST

The plan includes the acquisition of growing content and state of
It composes their peaks through the telescopes, branches and the
Synchronous calls. It retains the potentially transferred regions
and withdraw local acquisitions whose release is identified.
Exclusive arms contribute by maximum to the peak and terminal of the
growth by type. The number of slots is calculated independently
the size of a region.

Repeated acquisitions with undetermined coexistence
and those in the graph of recursive calls take a dedicated region.
The template is inherited from the construction site. Another template opens
a separate area, the number of which can be deducted in the
scope si `count` is omitted. A full annotated area may overflow to
a dedicated region of the same template. The explicit global limit and the
limit of growth of a region trigger their existing diagnosis
in the event of overtaking.

The two Rust tests and the six C suites of the backend pass, with
100 witnesses on UBSan to `-O0` and `-O2` 54 confirmed refusals.
The five new controls cover exclusive growth under a
global limit, a conditional call that transmits a single region
while another remains alive, the content held by a loop,
isolation of a recursive call and local inference for another
template. Async suite always checks for the re-use of a single slot
on four successive expectations.

The calculation keeps conservative boundaries when the identities of the
regions cannot be followed after a join or call.
Calls that inherit an annotated area check its capacity
effective at the time of acquisition.

<a id="g10--recul-groupé-du-curseur-régional"></a>

## G10 — grouping of the regional cursor

Liberation marks each free slot under the lock of the regions.
The scope output then recalculates the free suffix after cleaning
threads, collections and pools. Runtime writes the cursor
at least once per zone at this stage.
may trigger the same setback before reusing the area.

Two native witnesses instrument the slider's writings.
throws two threads into an annotated area, waiting for them in reverse order
of their creation and observed a single retreat from 2 to 0 at the exit of the block.
The second keeps a vector between the two frames and transfers it out
The cursor moves back from 3 to 2. The test creates another vector, then
checks the address of the first person by making him grow and rereads his content.

Two Rust tests and six backend C suites pass, with 102
witnesses under UBSan to `-O0` and `-O2` 54 confirmed refusals.
The two native witnesses are the subject of the letter of birth and the address check.

Before the first commit, the two Rust tests, the six C suites of the backend
and the 20 Python tests of `test_arguments.py` were replayed.
C-Suite confirmed 102 witnesses under UBSan and 54 refusals.
Building and local caches were removed after this verification.

<a id="g12--collection-transférée-à-une-tâche"></a>

## G12 — Collection transferred to a task

Backend Rust already accepts the transfer of a `A<Vector<i64>>` created in
a block region towards a task. The post-AST dependencies summary
keeps the pool dependency and distinguishes dependencies from the task of
celles du résultat attendu. Dans le C généré, le transfert conserve le
descriptor of the collection's storage and its region of origin.

Next `check_rust_task_regions.py` now implements a vector that
come out of his block, move on to a task, grow up after `yield` and returns by
`.await`. The witness compares the address of the data before and after growth
and during readings of the result. The program prints 7 then 9 under UBSan
à `-O0` and `-O2`. A second program confirms the refusal of a handle that
The entire suite ran out of the original pool's scope.
30 witnesses and confirmed refusal. No change in compiler was made.
This pass does not cover exhaustively
collections and launch modes.

<a id="g12--stabilité-emprunts-et-provenance"></a>

## G12 — Stability, borrowing and provenance

The pass covers the three G12 obligations on the routes used by the
Backend Rust. It complements previous witnesses, including the subsequent hindrance
Thread cleaning and re-use of regional slots.

- **Stability.** The data address of a vector remains the same
  after transfer from the original block, growth after suspension
  and receipt by `.await` or by `spawn` then `join()`. The witness
  String compares the address before and during growth on thread
  of the `spawn_blocking`, then check the length after `AsyncHandle.await`.
  A HashMap cookie compares the address of an entry before and after the entry
  Table transfer, addition of other entries and re-use of a
  box released.
- **Emprunts.** A reference stored in a vector survives the return and return journey
  Async. Writing the target passes after last use and drop
  The variant that writes before reading is refused for
  The regional suite also refuses to remove the existing loan
  a still borrowed entry.
- **Provenance.** The output of a handle carrying a vector out of the
  The scope of his pool is refused. The dependencies distinct from the task
  and the result are represented by the summary of the existing post-AST.

Both suites performed 33 task witnesses and 12 collections witnesses
under UBSan to `-O0` and `-O2`and confirmed respectively 20 and 7 refusals.
The pass adds regressions to the existing backend.
partial status. Backend currently refuses catches and results
`HashMap` by value in an async function, and catches
having pool slots in `runtime::thread`These limitations are
implementation restrictions. The runtime of the table combines its
descriptors to a context cleaning list and generation of the
native thread must have a cleanup of the catches owned on
failure to launch before opening these paths.

<a id="g12--transferts-à-travers-les-tâches-dans-le-backend-rust"></a>

### G12 — Transfers through tasks in the backend Rust

The possession plan now also represents the area of a HashMap.
When the table enters a Future, the descriptor is detached from the list
the appellant's cleaning and then entered in the context of the Future at
first poll. One output per value detachs the result before closing
The expectation records the result in the recipient.
table of `Ok` The entries remain in their
region of origin during these operations.

Un bloc `runtime::thread` may receive an allowance or an aggregate
The launch detachs the catches from the context
The worker links them to his context, and the path of failure
destroyed them before making the slot of the handle. The result possessed is
The man is separated and remains under the responsibility of the handle until the join.
Pool lock is also active in multithread programs without
fonction async.

New witnesses cover a HashMap by direct wave, by
spawn/join and by spawn_blocking/waait, with an instrumented comparison
address through both await. Spawn_blocking failure test
Reuses table space. The native test compares the vector address
before launch, during growth and after join.
pthread_create makes the slot of the aggregate and that of his child.
program is refused if the native handle comes out of the block of its source pool.

The two Rust tests and the six C suites of the backend pass.
There are 112 witnesses to the `-O0` and `-O2` under UBSan and 57 refusals.
The matrix status reflects a control validation. ASan remains
blocked on the minimum witness documented in G11 report.

<a id="p1--pages-de-garde"></a>

## P1 — Watch pages

The backend Rust reserves the data ranges of the two datatacks in
`PROT_NONE`, then makes their part accessible usable with `mprotect`.
The final page remains inaccessible. If the capacity is less than a
page marker or falls between two pages, running keeps the limit
The limits of the system are the following:
between regions are controlled by runtime. Disassembly releases the beach
In the end, async contexts and threads are included.

On macOS arm64, `python3 validation/check_rust_datastack_guard.py` confirmed
16 scenarios at each level `-O0` and `-O2` UBSan. Both
datastacks and both alignments, the last authorized byte is accessible,
a logical exceedance emits Crust diagnosis, and a reading or a reading
The six C suites are interrupted by the system.
The backend also passes, with 112 witnesses and 57 confirmed refusals.
Both G11 benches start with the new runtime. Flows and times
The number of reservations published in G11 were measured prior to this addition.

<a id="seuils-de-restitution-free_pages-et-initialiseurs-de-pool"></a>

## Restitution thresholds, free_pages and pool initializers

Backend Rust applies optional thresholds `reclaim_threshold` and
`region_reclaim_threshold` cleaning of the telescopes. `#(free_pages)` force
treatment below the threshold. A classic datastack recovers
the entire pages of the free suffix. The datastack to regions group together the
freed slots adjacent under his mutex, leaving pages on horseback
on a living accessible area. Anonymous remapping retains the
virtual addresses and guard. If the remapping fails, the runtime keeps
The range and can be retentated later. Thresholds are absent by default.

Named, contextual and nominal initializers of `Pool.new` partagent
the construction of fields in the post-AST. The explicit fields are
assessed in the written order. The omitted fields receive the available defect,
recursively for structures. A field `A<T>` requires an allowance
explicit. The backend uses the existing PoolNew lowering, which initializes
the slot from the built value.

On macOS arm64, `python3 validation/check_rust_reclaim_constructors.py`
confirms five witnesses under UBSan to `-O0` and `-O2` And four refusals.
instruments remappling to control the threshold, explicit demand,
the region transferred between two holes and the exits continues and returns
After suspension. The pass does not measure the runtime flow with this
policy activated.

<a id="placement-direct-dans-poolnew-et-extraction-des-vecteurs"></a>

## Direct placement in Pool.new and vector extraction

The post-AST plan recognises the structure literal immediately consumed
by `Pool.new`. Field expressions remain evaluated before taking
The generator writes the fields in the slot and uses the route
of possession to adopt the allowances they bear.
Values already built continue to go through the transfer path
existant.

`Vector<A<T>>` Supports `pop` and `remove` in the backend Rust.
The runtime links the extracted value to its new receiver.
Statically maintains a union of possible sources of its elements.
The witness extracts allocations from two pools and then reuses both pools
slots. The absence of intermediate reservation for the literal Box is
checked in the manufacturer's tell-tale.

The two Rust tests and the eight C suites passed the first pass.
The collection suite is replayed after tightening the summary of
source to exclude the pool from the vector from the extracted value.
V3 was replayed with four programs by `check`. ASan seul reproduit
the period exceeded on the macOS minimum witness. The refund measure
integrated is recorded in G11.

HM6 allows table values `&mut T` and specifies results
`&&mut T` and `&mut &mut T`. The reference passage rule and the
production `type` These nested types are currently excluded from the core.
The choice of syntax and scope of their support remains open.

<a id="références-imbriquées-et-hashmap-à-dépendances"></a>

### Interlocked and HashMap Dependent References

After arbitration, grammar accepts `&&mut i64` and `&mut &mut i64`.
The type checked keeps each mode.
at the corresponding level. Writing through both levels
requires that both borrowings be transferable.

Backend Rust accepts table values `A<T>`, `&T` and `&mut T`.
Owned entries are separated from the list of local allowances
and destroyed with their table.
connects to the receiver. A direct replacement of reference via `get_mut`
add new provenance to table summary and refuse a target
The results follow the conservative dependencies of the
table through a synchronous relay. Key precision and effects
replacement through calls remain open.

The first pass performed both the Rust tests and the eight C suites.
The collection suite was replayed with direct replacement,
two additional witnesses and UBSan to `-O0` and `-O2`.

<a id="dépendances-par-clé-et-contrats-de-remplacement-synchrones"></a>

### Key Dependencies and Synchronous Replacement Contracts

The auditor links the input dependencies to the position
`MapEntry` A literal key, or deduced from a link
Unchangeable initialized by a literal, selects its entry.
or a certain replacement removes its previous dependency.
dynamics and potentially conditional call effects maintain
the union of compatible provenances.

A synchronous function contract indicates which argument can provide the
The new loan and what argument is the written entry.
substitutes the actual provenances and checks their life before
add them to the table summary. The relays transmit the same
The delayed effects of this form are currently denied.

The two Rust tests and the eight C suites pass.
collections has 20 programs under UBSan to `-O0` and `-O2` and 13
The new witnesses cover the separation of two keys and
a replacement relay. Refusals cover the transfer of a target
borrowed by another key and too short a target installed
by call.

<a id="remplacements-différés-dentrées-de-hashmap"></a>

### Delayed replacements of HashMap entries

Catches bear the obligations of the target and reference
Incoming before the task is performed.
is recorded on the Future or handle and life of the
new target is checked at capture.
The summary keeps the initial origin
for paths that can fail to launch or avoid writing.

Witnesses execute the native transfer followed by join, launch
Blocking followed d-wawait and an injected launch failure.
d
Target that does not survive at the table.
The passages and returns concerned do not yet carry these effects.
are explicitly refused.

Public contracts now transmit replacement via helper
synchronous that joins the handle, a helper async waiting for the AsyncHandle and
a native factory that returns the handle directly. The summary remains
conservative for conditional effects and LaunchFailed. Results
interlocked contracts with an effect and unsolved recursive contracts remain
The following tasks have been completed with 42 programs
under UBSan to `-O0` and `-O2` 21 refusals.

The result contract represents the position of the handle and retains
effects during relaying a native factory. A synchronous call
recursive uses an approximation of possible scriptures from
The recursive control is passed on UBSan.
Both Rust and the eight C suites were completed on this lot.
The collection and tasks suites confirmed 21 and 42 respectively.
The witness ASan minimum
remains blocked on the host. The forms of handles nested or recursive
Outside the backend perimeter remain open.

<a id="handles-imbriqués-et-récursifs-dans-le-backend-rust"></a>

### Embedded and recursive hands in the backend Rust

Fixed aggregates retain the dependencies of each handle to the position
The dependencies of the expected result
keep a separate path. The possession path follows the same positions
to move the handles between the scopes and the running contexts.
completes the effects of the handle consumed. If the result contains another
The effects of this process remain tied to this result until its own expectation.

The analysis orders the bodies by their calls. In a call cycle, a relay
of handle is checked with a hypothesis of conservation of the paths that its
The final contract must comply. For recursive entries, the summary
conservative combines target parameters with compatible source types.
Waiting for an async call applies this summary, and uncertainty of launch
keeps the initial provenance alongside those which writing can
installer.

The following tasks cover the return of a handle from a native worker or a native worker.
Future, the recursive expectations sync and async, mutual recursion, a
handle board, a recursive enum by hand indirection and capture
d-a handle autonomous by a thread.
Injected launch failure control repeats original target. Refusals
check the abandonment of a dependent interlocked handle and access to a target
reserved after the handl's back.

Backend retains limits for pools and handle vectors,
recursive relays that rebuild paths or combine wait and
return, and capture of a handle dependent by a launch that
The results are based on the following:
The status of an independent audit remains distinct.

Validation of this lot: two Rust tests and eight successful C suites.
of tasks includes 53 programmes executed under UBSan to `-O0` and `-O2` and
No ASan results were obtained for this batch.

<a id="handles-en-collection-et-contrats-des-cycles-récursifs"></a>

### Collection and contract handles of recursive cycles

Pools and vectors adopt the handle of the values they receive.
Their extraction operations transfer resources to the scope that they
The value de-reference of a pool allowance containing a
handle consumes the entire allocation and makes its slot. For vectors,
`remove` also shifts the paths of dependence of the following elements.
Destruction removes the autonomous handles outside the pool lock,
Because the result of a handle can in turn require this lock.

The verifier analyses the call graph cycles until stabilization
contracts for return, waiting and writing. The paths of result
If a branch is waiting for a handle and a branch is waiting for a handle, the branch is not able to use the argument.
the summary adds the possible entries of
The result continues to reserve the catches on the way
where it contains the handle. `LaunchFailed` retains the original provenance.

The analysis requires a proven position to remove a handle dependent on a
and rejects cycles whose contracts do not stabilize in
the terminal d'analyse. The displacement test in the vector removes first
a brother element then waits for the handle staggered. Both paths of the relay
recursive are executed, as well as the passage of handles async by the pool
and the vector with suspension.
Dependent handle is refused.

The two Rust tests and the eight C suites have been completed.
confirmed 58 programs and 25 refusals. Two witnesses added at the end of the pass,
on the async handles and extraction of an enum in collection, then
completed with the same executable and the same options. Total: 60 programs
under UBSan to `-O0` and `-O2` and 25 refusals. No results ASan
n

<a id="déduction-de-la-case-unique-et-vidage-dun-vecteur-de-handles"></a>

### Deduction of the single box and emptying of a handle vector

With a proven length of one, the continuation of `remove(index)`
transfers dependencies from the zero box. The generated code keeps the calculation
The index and its terminal control.

Un `match handles.pop()` refines the state of the vector in the arm `None` :
the length is zero and the dependencies of the cells are removed.
the vector can still contain an element, the analysis retains the
possible dependencies of the remaining cells. The fixed point of the loop
combines the states of each exit. `break` in `Some` peut donc
keep an active loan despite the `join()` Handle extract.

The controls cover a parameter-based index, a length that depends on
d , a branch and a `break` after the first `join()` which leaves
a handle that is dependent on the vector.
applies to a `pop()` Directly scrutinized by `match`.

The two Rust tests and the eight C suites pass.
confirms 62 programs under UBSan to `-O0` and `-O2` 26 refusals.
The single case tell-tale call with index 1 stops at execution
with the diagnosis "indicator out of vector".

<a id="types-nommés-et-appels-qualifiés-dans-le-parseur-rust"></a>

### Named types and qualified calls in the Rust parser

The parser shares the list of arguments between named types and calls
on a type set. `MonType::new()`,
`HashMap<i64, Point>::new()` and `geo::Boite<Option<Point>>::new()` on
The comparisons keep their syntax.

Three Rust tests and the regression suite of the collections pass.
The user-type cookies check the AST. Resolution and
typing these calls is the responsibility of the existing auditor.

<a id="régression-du-parseur-sur-le-corpus"></a>

### Parseur's Regression on the corpus

The corpus regenerated from documentation, Crust files and the
Python tests have a total of 2,763 known occurrences
The Python reference. The parser Rust accepts 2,755. The eight refusals
were already present in the previous report and correspond to the
chains that require assembly by testing.

A second pass compares the parseur of `fdb71ff` to the parser modified on
10 311 candidate occurrences, including the literals of the scripts of
Rust validation. Each is tried as a program, block or signature.
Both versions recognize 3,110 occurrences and no occurrences
This comparison covers the
sources present in the repository and syntax modes executed.

The eight validation suites of the Rust compiler also pass,
including their assembled programmes.

### Documentation layout and README examples

The main README is in English, with a French version in `docs/README.fr.md`.
Each README contains four Din examples and one Rust example. The four Din
examples in each version were emitted as C, compiled and executed. The
Rust example was compiled with `rustc` and run against an assertion for
three elements.

The corpus skips blocks explicitly marked as Rust-only. After rebuilding
the corpus, the Rust parser accepted 34 documentation snippets, 38 Crust
files and 2,686 Python literals. The eight historical partial Python
literals still produce the same parser refusals.

### English documentation and French source copies

The default Markdown paths now open the English versions. French source
copies use the `-fr.md` suffix and link back to the English versions.
Machine translation was run locally, with a manual pass on the core
invariants and repository instructions. The remaining translations have
not been reviewed rule by rule.

The language switch links and fenced code blocks were checked against the
previous tree. Corpus generation skips translated copies to avoid
counting the same example twice. The Rust comparison accepted 32
documentation snippets, 38 Crust files and 2,686 Python literals. The
eight historical partial Python literals still produce the same refusals.

### README fixed-capacity pool example

Both README versions compiled to C and printed 10, 20, and 30. The
third allocation succeeded after the first was dropped, while the second
remained live. Keeping both allocations alive caused the third call to
terminate with the pool-exhaustion diagnostic.

### Single-package modules

The Rust CLI accepts a package directory for `check` and `emit-c`.
It resolves file-local imports and module visibility before passing a
single program to the existing verifier. The package test compiled and ran
under UBSan at `-O0` and `-O2`. Nine negative cases covered collisions,
private components, an unknown path, an external package, an ambiguous
module path, and a missing entry point. Standard-input compilation still
works. The parser corpus reported only its eight historical refusals.

The current loader supports the current package. External dependencies and
standard library loading are reserved for a later implementation lot.

### Package dependencies and bundled std

A single executable loaded a local package with its own path dependency,
a Git package pinned to an earlier commit, and a public function from the
embedded standard library. The emitted C printed 42 at `-O0` and `-O2`
under UBSan. Seven additional refusals covered undeclared transitive access,
an invalid or unavailable revision, a package name mismatch, a reserved
dependency name, incompatible manifest keys, and a dependency cycle.
The Git test used a local repository.

### Custom destructors

Three programs emitted by the Rust compiler ran under UBSan at `-O0` and
`-O2`. The inline and pooled witnesses printed 1, 2, 3, 4, covering parent
before child, explicit destruction, scope exit, and ownership transfer.
The inline witness also dropped a type with the empty default. The async
witness printed 8 once after transferring a capture across suspension.
Four invalid destructor declarations or direct method calls were rejected.

The backend currently uses the default fixed datastack capacity when a
custom destructor makes the inferred call footprint incomplete. An explicit
capacity still takes precedence. Inline vector elements and consuming matches
on aggregates with custom destructors remain outside the implemented subset.

### Tuples and destructuring

The tuple witness compiled to C and ran under UBSan at `-O0` and `-O2`.
It covered inferred and returned pairs, heterogeneous triples typed by
an argument or a return signature, and the move of a triple through a
function before destructuring. Its two owned elements were destroyed once,
one explicitly and one at scope exit. Four refusals covered arity mismatch,
duplicate binding names, use after destructuring, and a literal outside
the expected element type. The custom destructor suite also passed.

### Target selection before imports

The package test selected x86-64 Linux and AArch64 Windows explicitly.
Both portable C outputs ran under UBSan on the host. They selected different
imports under the same alias and different declarations under the same
name. An excluded import from an unknown package and an excluded function
with an unresolved call were ignored. Activating both imports produced a
collision. An unknown target property and the old brace placement were
rejected. The parser corpus retained its eight historical refusals.

The target flag selects sources before parsing and resolution. The test
exercises source selection, and native binary production still depends
on the C toolchain for the intended target.

## Inline assembly and usize

`validation/check_rust_assembly.py` checked eleven refusals and the i686 and
x86-64 `usize` limits. It compiled the direct-source witness at `-O0` and
the package witness at `-O2` with x86_64-linux-musl GCC and
`-Wall -Wextra -Werror`. Both ELF executables ran in an isolated local
Linux x86-64 container. With stdin set to `AB`, the output was `0`, `2`,
`65`: the original first byte, the syscall result after register restoration,
and the first byte after the syscall. This run used no sanitizer on the
assembly witness. The Rust unit tests and the existing package, destructor,
and tuple regressions also passed. The latter scripts ran their C witnesses
with UBSan.

The regenerated historical corpus comparison accepted 2,757 of 2,765
reference snippets and reported eight parser refusals. These counts describe
the current comparison with the historical Python parser.

The test exercises bounded writes via `read`, stable operand slots during
`push` and `pop`, and conservative memory effects across the generated
assembly call. It covers Linux x86-64 assembly and compile-time i686 width
checks. The assembly body and any effects extending past the block remain
the author's responsibility. The complete `File` sketch still requires
slice and associated method support. Indirect assignment of a tracked
address through a reference is outside this implementation subset.

## Standard-library file I/O

`validation/check_rust_file.py` compiled a package using the bundled
`std::io::File` at `-O0` and `-O2` with x86_64-linux-musl GCC and
`-Wall -Wextra -Werror`. Both ran in the local Linux x86-64 container.
The exact output was `0, 2, 65, 66, 0, 10, -2`, covering an empty buffer,
a bounded read, the two bytes observed in Crust, EOF, invalid-path
classification, and the missing-file error. With a limit of 32 descriptors,
128 sequential opens succeeded after moving the file into a new binding
and letting its scope end. The seven compile-time refusals covered
representation privacy, platform visibility, unsupported ABIs, and
invalid mutable slice access. The Linux witness was run without a sanitizer.
Rust unit tests and the package, tuple, and destructor regressions passed.
The latter C witnesses used UBSan.

The implemented platform is Linux x86-64 with 64-bit pointers. The slice
entry points used here cover full fixed byte-array slices. File privacy is
enforced specifically for the standard-library resource while the package
compiler still flattens modules. The OS close result is discarded by
`drop`.

The File facade now owns a platform File field. The Unix File owns the
descriptor and implements its destructor. Both Linux witnesses were rerun
after the change and produced the same output, including 128 opens under
the 32-descriptor limit. The seven compile-time refusals still pass.

### macOS and Windows File

The same File witness ran on macOS ARM64 at `-O0` and `-O2` with UBSan.
Linux x86-64 ran both configurations again. The expected output in both
cases was `0, 2, 65, 66, 0, 10, -2`, with 128 reopens under a
32-descriptor limit. All seven refusals passed. Zig 0.14.1 compiled and
linked the Windows x86-64 and ARM64 witnesses at both optimization levels.
No Windows runtime was available for execution. Windows uses a CRT
descriptor and the synchronous fixed datastack uses VirtualAlloc.

### Assembly-backed macOS and Windows File

The File C bridge was removed. The macOS backend calls libSystem and reads
errno in the same assembly routine. The Windows backend calls
MultiByteToWideChar, CreateFileW, ReadFile, GetLastError and CloseHandle.
The Windows File owns the returned HANDLE. Windows error codes in FileError
are negative Win32 codes, with ERROR_HANDLE_EOF mapped to a zero-byte read.

The shared witness passed at -O0 and -O2 on macOS ARM64 with UBSan and on
macOS x86-64 through Rosetta. Linux x86-64 ran both optimization levels in
a local container with the 32-descriptor limit. Zig linked Windows x86-64
and ARM64 executables at both optimization levels. Windows runtime
execution remains unverified.

### Windows execution under Wine

The original Windows x86-64 PE witnesses ran under Wine 11.21 on macOS
with Rosetta at `-O0` and `-O2`. Each produced `0, 2, 65, 66, 0, 10, -2`
with exit status zero. The output covers a zero-byte budget, a bounded
read of `AB`, EOF, an invalid path and a missing file.

A second build of the same witness redirected its generated assembly
call to a validation shim. The shim invokes `CloseHandle` and verifies
that `GetHandleInformation` immediately reports `ERROR_INVALID_HANDLE`.
Both optimization levels reported exactly 129 successful closes, one
for the initial read and 128 after moves and scope exits. The shim is
only present in the validation binary.

The original and instrumented Windows ARM64 witnesses linked at both
levels. The local x86-64 Wine runtime rejected the ARM64 executable with
`Bad format`. Native Windows execution on either architecture remains
unverified.

### Bootstrap lexer and bounded byte prefixes

The Rust frontend accepts borrowed fixed byte-array prefixes `&buffer[..count]`
and `&mut buffer[..count]`. The upper bound is exclusive. It can equal the
array length. Known invalid bounds produce a compile-time diagnostic. The C
backend checks dynamic bounds before constructing the slice descriptor.

On macOS ARM64, four generated C witnesses ran at `-O2` with UBSan. Dynamic
bounds zero and the array length succeeded. A negative bound and a bound
above the length both exited with the bounds diagnostic. Three compile-time
refusals covered a known out-of-range bound, a noninteger bound, and an
unsupported lower bound.

The early self-hosted lexer, now in [compiler/corboc](../../compiler/corboc), read `fn main() {}\n` from a
real file and emitted seven token spans including EOF. Those spans matched
the Rust frontend for this input. The witness reads one chunk from a fixed
path and covers the token kinds used in the sample. The next missing compiler
operation found during lexer work was short-circuit boolean `&&` for guarded
lookahead.

### Short-circuit boolean operators and lexer lookahead

The verifier lowers boolean `&&` and `||` to a branch with a common
result and joins the binding state across the evaluated and skipped
paths. The control-flow graph includes both paths. On macOS ARM64,
generated C passed UBSan at `-O0` and `-O2` for skipped out-of-bounds
lookups, required right-hand side calls, and nested operators. Two
non-boolean operand cases were refused. The Crust lexer recognized
`//` comments and a trailing single slash without overreading.
Writing a Token struct into a fixed array slot is the next blocker
for handing a token buffer to the parser.

### Fixed token-array writes

The lexer stores tokens and EOF in an explicitly initialized eight-element
array. On macOS ARM64, the generated C passed UBSan at `-O2` for a dynamic
index replacement preserving the neighboring slot and for an out-of-range
index that exited with the bounds diagnostic. The lexer emitted the
expected identifier, punctuation, trailing slash, and EOF spans on its
comment witness. Rust unit tests passed. Repeated initialization of
aggregate elements is the next blocker. Types that own resources remain
outside this array replacement path.

### Structural array replication and lexer capacity

On macOS ARM64, a nested Token initializer with a visible side effect ran
once per array expression at `-O0` and `-O2` under UBSan, including a
zero-length array. Replacing one replicated slot preserved its neighbor.
Structures with a borrowed field or a custom destructor were refused when
repeated twice. Rust unit tests passed. The lexer ran with 257 token slots
and preserved its comment, trailing slash and EOF output. A borrowed
prefix of a `Token` array is the next blocker.

### Typed borrowed prefixes and parser handoff

The bootstrap lexer now hands the initialized Token prefix, including EOF,
to a parser entry point accepting `&[Token]`. On macOS ARM64, generated C
used the Token stride and respected the prefix length under UBSan at
`-O0` and `-O2`. An access to the excluded slot trapped. Dropping an
array while its slice was live was rejected. The comment witness retained
the same token output. File regressions passed under UBSan at both levels.
Borrowing an individual token from the slice is the next unsupported operation.

### Slice element reborrows

Indexed shared and mutable reborrows from named slices use the checked
element address and carry the slice's origin and parent binding. macOS
ARM64 UBSan confirmed mutation and the dynamic bounds trap at `-O2`.
Three refusals covered an early array drop, an exclusive reborrow from a
shared slice, and use of the parent during an active exclusive reborrow.
The bootstrap parser passed each token to its helper by shared reference
and preserved the token stream. A subrange of the source slice with a
nonzero-capable lower bound remains unsupported.

### Two-bound slice reborrows

On macOS ARM64, six generated C witnesses ran under UBSan at `-O2`.
They checked typed offsets, an empty range at the end, and runtime traps
for negative, reversed, and oversized bounds. Two static refusals cover
reversed constant bounds and dropping a backing array during a live
subslice. The bootstrap parser now uses each token's span to form a
byte view of its spelling. Direct equality of borrowed byte views is
outside the current verifier subset.

### Slice identity and byte content equality

On macOS ARM64 the slice comparison witness passed under UBSan at
`-O0` and `-O2`. Identity uses the starting address and element count.
The std Crust method checks byte contents, including distinct backing
arrays, differing lengths and mismatched bytes. Both slices remain usable
after the comparison. Three type refusals covered ordering, mismatched
element types and nonbyte content comparison. The bootstrap lexer
recognized `fn` and scanned a decimal token to its end. Widening `u8`
to `u64` with `as` is unsupported by the verifier.

### Exact numeric casts and decimal tokens

The verifier checks `as` over the entire numeric source type. Generated C
ran under UBSan on macOS ARM64 at `-O0` and `-O2`, with exact integer and
floating widening. Six inexact conversions were refused. The frontend
accepted `usize as i64` on i686 and refused it on x86-64. The bootstrap
lexer decoded 123 and the maximum `u64` and returned status 5 for the next
integer. Bitwise AND for classifying UTF-8 continuation bytes is the next
unsupported operation encountered.

### Integer bitwise AND and UTF-8 strings

On macOS ARM64, seven integer types passed runtime AND checks under UBSan
at `-O0` and `-O2`, including signed operands and a folded negative mask.
Boolean, float, and mixed integer operands were refused. The bootstrap
lexer accepted a string containing valid two-, three-, and four-byte
sequences and rejected overlong, surrogate, out-of-range and truncated
sequences. Strings with escapes remain open. The next compiler diagnostic
encountered while preparing code-point assembly was the unsupported
left-shift operator.

### Checked left shifts

On macOS ARM64, generated C passed UBSan at `-O0` and `-O2` for
all seven integer types, including `-1 << 63` on i64. Four dynamic
failures covered negative and oversized counts and overflow with both
unsigned and signed inputs. Three invalid constant or typed expressions
were rejected. The bootstrap lexer assembled UTF-8 scalar values and
the valid, surrogate, and truncated string witnesses passed. Right
shift remains unsupported by the verifier, which currently treats
the first `>` token as a comparison.

### Checked right shifts

The verifier recognizes both tokens of `>>` and shares count checking with
`<<`. The C backend shifts unsigned values and reconstructs the signed
result for negative operands. On macOS ARM64 with UBSan at `-O0` and
`-O2`, all seven integer types passed, including i64 minimum shifted by
zero and 63. Two invalid dynamic counts trapped and three invalid static
expressions were refused. The lexer classified UTF-8 lead and continuation
bytes using right shifts and passed four string witnesses. Bitwise OR
remains unsupported when combining disjoint UTF-8 payload bits.

### Remaining bitwise operators and lexer escapes

The Rust backend accepts integer OR, XOR and complement. On macOS ARM64
the generated C passed UBSan at `-O0` and `-O2`, including the narrow
complement `~5 == 250` for u8 and a negative signed OR. Three noninteger
expressions were refused. The bootstrap lexer passed seven string cases
covering direct UTF-8, JSON escapes, surrogate pairs and malformed input.
It still takes its input from a fixed path and reads one chunk. The entry
point currently rejects parameters. The interface for passing a CLI input
path to the bootstrap compiler remains a design decision.

### Process arguments for the bootstrap compiler

The public entry point remains parameterless in Crust. The generated C
entry point receives the process arguments and exposes immutable UTF-8
views through the standard library. Unix validates argv bytes, while
Windows obtains the UTF-16 command line and converts its arguments.

macOS ARM64 passed no-argument, empty, Unicode and invalid UTF-8 cases
at `-O0` and `-O2` under UBSan. The lexer opened a Unicode filename with
a space on macOS and Windows x86-64 under Wine. Linux x86-64 was compiled
and linked. The bootstrap still reads one source chunk of at most 256
bytes and uses a 4096-byte path buffer including the NUL terminator.

### Bootstrap parser signatures and statements

The Crust bootstrap parser now recognizes typed parameters, optional
return types, and simple let, return, and expression statements. Five
witnesses matched the Rust syntax projection on macOS ARM64 at `-O2`
under UBSan. The comparison included node kinds, parent links, byte
spans and name spans. Nested scope edges were normalized because the
bootstrap omits the wrapper node on those edges. Six malformed
signatures or statements exited with status 7. Type syntax is limited
to simple names and expressions to individual names or literals.

### Bootstrap AST self-parse

The bootstrap executable now reads up to 64 KiB in chunks and reports a
capacity error if bytes remain beyond that budget. Its syntax subset covers
imports, nominal declarations and methods, nested types, control flow, calls,
operators, destructuring, arrays and ranges. It emits a flat syntax tree with
parent links and byte spans. The Rust compiler now lowers indexed writes
through mutable slices for primitives and structurally replicable aggregates
whose types carry no dependencies. Bounds are checked before evaluating the
replacement, and the selected place remains reserved through that evaluation.

On macOS ARM64, `validation/check_crust_bootstrap.py` passed 13 AST comparisons,
including the bootstrap source itself and `std::env`, under UBSan at `-O2`.
Nine malformed inputs exited with status 7, and the 65536/65537-byte cases
exited with status 0/4. A separate generated C witness printed 3 and 9 after
changing only the second aggregate in a borrowed slice, trapped an out-of-range
write, and obtained a static diagnostic for a write through a shared slice.
The Rust frontend's three unit tests passed.

The comparison covers node kinds, parent and child order, byte spans and
name spans. It does not project visibility or verify ownership rules.
Target-conditional items, assembly and other grammar forms absent from the
self-parse corpus still need coverage. The bootstrap is built by the Rust
compiler and does not emit an executable.

### Bootstrap comparison against standard library and examples

The Crust frontend now projects visibility, opaque assembly blocks and operand
positions. It selects target-conditional items before parsing and handles
closures, named moves, contracts, regional annotations and pool initializers.
The bootstrap was built for the host target. It uses a 128 KiB source budget
and checks UTF-8 before tokenizing, including bytes in comments.

On macOS ARM64, the comparison script passed 65 AST comparisons under UBSan
at `-O2`. The inputs include the bootstrap's own source, every Crust file in
`stdlib/src` filtered for the host target, and 32 root-level examples accepted
by the Rust frontend. Twelve malformed programs were refused, including
assembly outside `@unchecked`. Invalid UTF-8 in a comment was refused.
The input size boundaries were checked at 131072 and 131073 bytes. The Rust
frontend's three unit tests also passed.

The comparison projects syntax, including node kind, child order,
byte positions, visibility and assembly operand spans. Host execution does
not exercise other platform branches. This milestone does not include the
crate loader, static scope and binding construction in Crust, rule checking,
or executable generation.

### Bootstrap lexical scopes and binding resolution

The Crust bootstrap walks the AST in child order and emits the containing
scope, the parent at scope entry, declaration flags and links from uses
to their visible declarations. It visits initializers before introducing
the binding and keeps nested declarations local. Named moves resolve the
original declaration before introducing the new one. Assembly operands
also resolve against the current lexical environment.

The host UBSan comparison passed 69 inputs, including the existing corpus,
shadowing, named moves, closure references, match bindings and tuple
bindings in a loop. Twelve syntax refusals, invalid UTF-8 and both source
budget boundaries still passed. The parser now also accepts empty
`try_slice()` at the syntax stage, matching Rust's treatment of method
arity at that stage.

The static projection covers lexical scopes and binding resolution.
Capture sets, control-flow exits and memory facts are outside this
comparison. Platform execution remains limited to the host.

### Bootstrap static tree

The Crust bootstrap now emits an AST-indexed static tree with lexical
scopes, scope entries and ends, declarations, ordered point operands,
resolved bindings and named moves, control-flow destinations, and
deduplicated closure captures. It classifies the syntax-derived facts for
borrows, pools, allocation candidates, collections, calls, writes, branches,
projections, awaits and suspension. Fact operands reuse the ordered AST
edges so that both representations refer to the same node IDs.

The macOS ARM64 comparison under UBSan matched 70 source inputs against
the Rust frontend, including nested closures with repeated uses and
nested loops with return, break and continue. The comparison projects
capture sets and scope ends by syntax identity. The twelve syntax refusals,
invalid UTF-8 refusal and two source-budget boundaries also passed.
This pass covers the pre-verification tree. Type and memory-rule checking,
post-AST placement, and execution on other hosts are outside this pass.

### Bootstrap rule checker

The Crust bootstrap accepts `--check <file>` and consumes the resolved
static tree. It checks a synchronous subset with i32, i64 and bool bindings,
explicit copies and drops, named moves, direct replacements, lexical blocks,
and calls with scalar signatures. The checker reports status 8 followed by a
rule number and a byte offset on a violation. Status 9 means coverage is
missing for the encountered construct. The original AST command continues
to emit the same AST and static tree format.

On macOS ARM64 with UBSan at `-O2`, the runner passed 12 checker witnesses
(three accepted, seven rule violations and two coverage refusals), 70
existing AST and static tree comparisons, 12 syntax refusals, the UTF-8
refusal and the two source-size boundaries. This is partial rule coverage.
The checker still needs provenance and a borrow model for N4 and N5,
control-flow state joins for N6, cleanup over owned resources for N2 and
N7, and inferred boundary effects for N8. The three scalar types and the
supported operations also cover only part of N1 and N3.

### Bootstrap branch states and direct loans

The bootstrap checker now forks the state at a statement-level conditional,
checks both successors, excludes successors that return, and joins the
states of existing bindings. It tracks direct shared and exclusive scalar
loans by binding identity and uses later syntactic uses to bound their
reservation. It checks dereference and direct writes through an exclusive
reference. Ambiguous overlaps return coverage status 9. Integer literal
checking now includes all fixed-width core integers and checks the bound
after applying a unary minus.

The macOS ARM64 UBSan run passed 25 checker witnesses, 70 AST and static
graph comparisons, 12 syntax refusals, invalid UTF-8 and both input-size
boundaries. Remaining coverage includes path-sensitive loan provenance,
loops and value-producing branches, resource cleanup, and inferred
contracts with dependency effects.

### Bootstrap loop and loan checks

The bootstrap checks scalar comparisons, explicit reference destruction,
and while loops whose back edge preserves incoming binding states. Direct
loan conflicts in a straight-line statement sequence produce N5. The checker
keeps coverage status 9 for cases requiring more control-flow information.
On macOS ARM64 under UBSan, 30 checker witnesses and 70 AST/static tree
comparisons passed. The 12 syntax refusals, UTF-8 refusal and both size
boundaries also passed.

Remaining work includes a loop fixed point with abrupt edges, control-flow
liveness, reference transfer and reborrow provenance, owned resource
destruction and inferred dependency effects across calls.

### Bootstrap loop edges and reference transfers

The bootstrap distinguishes fallthrough, return, break, and continue.
Scalar while loops widen availability at back edges and merge the state
carried by break with the condition-false case. A join of identical abrupt
edges uses both states. Distinct loop edges at a single join still require
separate accumulators. Scalar reference declarations and moves preserve
the originating binding and exclusivity, including named moves into a
child block. The checker is now in a separate Crust module, and the
representation comparison includes all of its source files.

On macOS ARM64 under UBSan, 41 checker witnesses and 72 AST/static tree
comparisons passed, along with 12 syntax refusals, the UTF-8 refusal and
both input-size boundaries. Reborrows, conditional values, pool
provenance, owned resources and inferred call effects remain open.

### Host executable build and bootstrap checker

The Rust frontend now builds a host executable with `build [package-dir] -o
<executable>`. It verifies the program before invoking the host C compiler
(`CC`, default `cc`), and supports stdin when no package directory is given.
The README pool example built and printed 10, 20, 30. The bootstrap package
also built with the new command. The regression runner confirms that
a refused use after drop produces no executable.

The Crust checker now handles scalar conditional initializers with a result
and direct scalar pool allocations, including element type checks and
access after explicit drop. On macOS ARM64 under UBSan, 47 checker
witnesses and 72 AST/static graph comparisons passed, with 12 syntax
refusals, the UTF-8 refusal and both input-size boundaries. The Rust
frontend's three unit tests passed. The Crust checker remains partial,
and the executable build command still uses the Rust frontend.

### Bootstrap scalar results, pool ownership and reborrows

The bootstrap checker validates scalar conditional initializers and joins
the availability state of their two value-producing arms. Direct scalar
pool allocations keep the source pool identity when moved by assignment
or by a named move. Scalar reborrows record both the target and the parent
reference. A live reborrow reserves its parent chain for incompatible access.

The macOS ARM64 UBSan runner passed 56 checker witnesses, 72 AST/static graph
comparisons, 12 syntax refusals, invalid UTF-8 and both source budget bounds.
The new cases cover incompatible conditional results, conditional moves,
moves of scalar pool allocations, and access through a parent before and
after the last use of a nested reborrow. Returned loans, path-sensitive
reborrow effects and cleanup of composed resources remain outside this
pass. The executable build command still uses the Rust frontend.

### Bootstrap executable and mixed loop exits

The Crust checker records separate availability states for break and
continue edges. The loop merges continue into its back edge and break
into its exit. A conditional with a continuing sibling preserves that
sibling's state for subsequent statements. Each nested while owns its
edge accumulator.

The macOS ARM64 build produced `build/crust-bootstrap`. The comparison
runner passed against this exact binary using `--bootstrap`. The same
59 checker witnesses and 72 AST/static tree comparisons passed under
UBSan. The checker witnesses include a branch that drops a binding and
breaks while its sibling continues, a use on the continuing path, and
a drop carried into the next iteration. Twelve syntax refusals, invalid
UTF-8 and both input-budget edges also passed.

The executable is produced with the Rust compiler. Coverage is still
partial for N1 through N8. Outstanding work includes loop-carried loans,
returned borrows, composed resource cleanup and inferred dependency
effects at call boundaries.

### Bootstrap returned scalar loans

The checker validates direct shared and exclusive reference returns,
including explicit reborrows through a reference parameter. It rejects
returns rooted in local storage, including a by-value parameter. For calls
to a function whose body directly returns its sole reference parameter,
the caller binds the result to the argument's target and parent loan.
The parent remains reserved until the last use of the returned reborrow.
This implementation recognizes the direct return from the syntax at
call checking time. It does not yet store a general inferred contract.

The rebuilt macOS ARM64 executable and the UBSan build each passed
71 checker witnesses and 72 AST/static graph comparisons, along with
12 syntax refusals, invalid UTF-8 and both source-size bounds.
Multiple return origins, general inferred effects, and composed
resource cleanup remain open.

### Bootstrap conditional scalar loan origins

The checker recognizes a scalar shared-reference selector with a boolean
parameter, two matching reference parameters, and one explicit parameter
return per arm. With a boolean literal and two direct named loans at the
call site, the result reserves both possible argument origins. Its later
dereference checks both roots. A returned loan with alternate provenance
cannot yet be passed to the identity-loan path, reborrowed, or written through.

The rebuilt macOS ARM64 executable and the UBSan build each passed 73
checker witnesses, 72 AST/static graph comparisons, 12 syntax refusals,
invalid UTF-8 and both input budget bounds. The new witnesses reject
mutation of the second possible target before the last use and accept
mutation of both targets afterward. Contracts still need general
inference and propagation across calls.

### Bootstrap conditional loan relay

The scalar selector accepts a named boolean and consumes it in argument
order. A direct identity call carries both selector origins into its
result. Scalar reference annotations on receivers are checked against the
inferred referent and mutability. These paths still recognize specific
callee shapes and use a representation bounded to two origins.

The rebuilt macOS ARM64 executable and the UBSan build each passed 78
checker witnesses and 72 AST/static representation comparisons. The
new witnesses check a moved boolean, both origins across a relay and
explicit receiver types. Twelve syntax refusals, invalid UTF-8 and the
source budget boundaries also passed.

### Bootstrap variable-width loan provenance

The bootstrap replaces the second-origin field with a provenance edge to
the call's ordered reference arguments. Shared scalar calls with an initial
boolean and homogeneous reference parameters conservatively reserve all
reference arguments. Relay calls traverse the edges transitively. The
callee's returns are checked separately. This removes the two-origin
limit for that signature family. The checker still needs precise
contract inference for general signatures and effects.

The macOS ARM64 host executable and UBSan build each passed 80 checker
witnesses, including before/after last-use checks on a third possible
target. Both builds also passed 72 AST/static tree comparisons, 12 syntax
refusals, invalid UTF-8 and both source-size boundaries.

### Bootstrap return provenance from function bodies

The bootstrap now traces direct returns, explicit reborrows and local aliases
to parameters in the callee body. At calls it matches those parameters to the
actual arguments in declaration order. The previous selector requiring a
leading boolean and homogeneous reference arguments was removed. Returns
that cannot be traced use a conservative set of compatible parameters.
Argument nodes mark which loans contribute to the result. The supported
scalar operands cannot move a storage root reserved by a reference argument.

The rebuilt macOS ARM64 binary and the UBSan build each passed 83 checker
witnesses and 72 AST/static tree comparisons. A mixed signature with
interleaved scalars and references allowed mutation of a reference parameter
that never reaches the return, and rejected mutation of one that can.
Another witness refused moving the target as a scalar argument in the same
call. The twelve syntax refusals, invalid UTF-8 refusal and both source-size
bounds passed. General call effects, multiple exclusive reference arguments
and exact inference through arbitrary returned call expressions remain open.

### Bootstrap differential rule checks

The host executable and UBSan build each matched ten Rust checker verdicts
covering returned call expressions, loop-carried scalar loans, pairs of
exclusive arguments, nested scalar call arguments, and a plain structure
owning one scalar pool allocation. The same runs passed 83 existing rule
witnesses, 72 syntax/static tree comparisons, 12 syntax refusals, invalid
UTF-8 and both input budget boundaries.

The comparison is per witness. Calls beyond the supported forms can still
return coverage status 9. In particular, nested argument effects on reserved
places, arbitrary aggregate ownership, recursive contract inference and
general cleanup effects are not established by this pass. Return-origin
traversal conservatively falls back after 32 expansion steps. Aggregate
checking in this pass follows a single owned pool field and emits no cleanup
code from the Crust checker.

### Bootstrap ownership across structure fields

The checker keeps ownership edges on constructor fields and traverses
them to verify that each source pool is still live. The aggregate keeps
those edges when moved. Constructors can combine allocations from
different pools, nested constructors, and existing allocation bindings
moved into fields. The checker rejects a mismatched allocation element
type and a later use of a binding moved into a field.

The macOS ARM64 host binary and UBSan build each passed 15 verdict
comparisons against Rust, including five new structure witnesses, plus
83 checker witnesses, 72 AST/static tree comparisons and 12 syntax
refusals. This checks static ownership for the supported constructor
forms. Ownership across all aggregate forms, generated cleanup, and
recursive call contracts remain open.

### Bootstrap nested owner moves and argument effects

A structure field can adopt an already constructed owned structure and
retain its constructor's pool dependency edges. The former binding becomes
unavailable. Nested scalar call arguments are checked against reference
reservations after evaluation. A shared reservation permits a copy of its
target and rejects a move.

The host macOS ARM64 executable and the UBSan build passed 19 Rust/Crust
verdict comparisons, including four new cases, 83 checker witnesses, 72
representation comparisons and 12 syntax refusals. Exclusive reservations
still require finer argument effect tracking. General recursive contracts
and generated cleanup are outside this evidence.

### Bootstrap recursive return contracts

The Crust verifier computes reference-return contracts to a fixed point
before checking calls. It detects direct and indirect call cycles and
conservatively retains compatible parameters for recursive functions,
matching the reference verifier on the recursive witnesses. A nested
operand that reads the root of an exclusive argument now produces N5.

The macOS ARM64 executable and UBSan build each passed 23 Rust/Crust
verdict comparisons, 83 checker witnesses, 72 AST/static tree comparisons
and 12 syntax refusals. The separate Rust backend destructor runner
executed three programs at -O0 and -O2 under UBSan and confirmed four
refusals. The Crust verifier does not yet generate cleanup or executable
code. The destructor execution evidence comes from the Rust backend.

### Crust-generated pool cleanup executable

The Crust bootstrap accepts `--emit-c <file>`. It verifies the source,
checks backend coverage before emitting C, and lowers a single synchronous
main with i64 pools, positive decimal initializer values, allocation moves,
dereference printing, explicit drop and lexical scope cleanup. It keeps pool
slot ownership across moves. The generated C currently tracks occupancy in
a local array and keeps scalar payloads in separate C locals. It uses the
existing target-specific assembly boundary to write output.

On macOS ARM64, the host and UBSan bootstrap runs each built and executed
C emitted by the Crust code generator. A capacity-one pool printed
10, 20, 30 after slot reuse following a move and scope exit, and following
an explicit drop. A repeated drop returned status 8 before emitting C.
An unsupported u64 pool returned 9 with empty output. The same runs passed
23 differential verdicts, 83 checker witnesses, 73 representation
comparisons and 12 syntax refusals.

Aggregate destruction, user-defined destructors, the datastack and the
full lowering remain outside the Crust code generator. The compiler used
to build the bootstrap executable is still Rust.

### Crust-generated nested aggregate cleanup

The Crust backend walks the constructor's ownership edges in reverse
field initialization order. An owner can be a nested constructor or a
scalar pool slot. Assignment and named moves transfer that identity
and clear the original owner. Explicit drop and scope exit use the
same cleanup traversal. Scalar payloads now reside in the indexed pool
storage, alongside the separate occupancy array.

On macOS ARM64, both bootstrap builds emitted and ran two C programs
under UBSan. The nested aggregate witness moved its owner into a child
scope and reused two capacity-one pools after leaving that scope. It
then adopted the new allocations and reused a slot again after an
explicit drop. Both programs printed 10, 20, 30. The runs also passed
23 Rust/Crust verdict comparisons, 83 checker witnesses, 73 AST/static
graph comparisons, 12 syntax refusals and two source budget boundaries.

The Crust backend still covers a single synchronous main and positive
decimal i64 pool initializers. It supports aggregates made of those
owned allocations, including nested aggregates. Custom destructor
methods and virtual-memory datastack lowering remain outside its
coverage. The generated pool storage currently uses local C arrays.

### Bootstrap virtual storage and destructor execution

The bootstrap emits a bounded virtual address range, commits pages on
demand, and rewinds a single cursor after scope cleanup. It places scalar
pool payloads and occupancy tables in that range. The generated code
handles nested scope rewinds and releases the range at program exit.
This path computes a conservative budget from pool capacities and scalar
fields. The general placement plan and region datastack remain open.

The bootstrap supports inline destructors of the form
`fn drop(&mut self) { print((*self).field); }` for an explicitly initialized
positive decimal i64 field. It emits the field read before recursively
cleaning the owned fields. The checker and emitter share a preflight for
this destructor subset. General destructor bodies and pooled nominal
types remain unsupported.

On macOS ARM64 the host and UBSan bootstrap builds each passed four
generated execution trace comparisons against Rust, four coverage or
verification refusals, 23 rule verdict comparisons, 83 checker witnesses,
73 representation comparisons, 12 syntax refusals and both budget
boundaries. Other operating systems were not executed.

### Bootstrap destructor sequences and early exit

The Crust backend now accepts empty custom destructors and ordered
sequences of scalar field prints, including the explicit Void signature.
The destructor reads its fields while their storage is live. An early
void return unwinds each entered scope, performs its cleanup, and rewinds
the cursor. Code after that return is excluded from emission.

The host and UBSan bootstrap builds on macOS ARM64 each matched six
generated execution traces with the Rust backend. The additions cover an
ordered destructor body after a move, and an early return from a nested
scope after explicit drop. Both runs also passed four emission refusals,
23 rule verdict comparisons, 83 checker witnesses, 73 representation
comparisons, 12 syntax refusals, invalid UTF-8 and both size boundaries.

The backend still supports a single synchronous main, a limited statement
set for custom destructors, positive decimal scalar values, and scalar
pools. General destructor bodies, nominal pooled objects, region placement
and self-hosting remain open.

### Bootstrap destructors, nominal pools and region storage

The Crust emitter now lowers a synchronous subset of destructor bodies
with scalar fields and locals, branching, loops, early return and calls
to void helpers with i64 parameters. The destructor completes before the
same ownership traversal cleans up its fields. The initializer order
witness exposed a discrepancy when the fields were listed in a different
order from their declarations. Cleanup now follows reverse declaration
order within the supported ownership graph.

The supported named pool layouts store scalar payloads in indexed slots
and retain ownership links to nested resources. The emitter handles
named, shorthand, and empty scalar constructors, partial scalar defaults,
and explicit scalar field reads. Enum variants reserve separate slot
ranges in the pool, and cleanup follows the selected variant's fields.

The vector descriptor is stored in its pool slot on the classic datastack.
A region reservation supplies the growing payload and remains live if
the descriptor is transferred across the end of an annotated block.
The synchronous runtime supports explicit global and local bounds, local
counts, fallback to a dedicated region on local saturation, and an
inferred default region size for straight-line scalar growth. A scalar
while loop can grow a vector using the default region size, and growth
after a block transfer continues to use the source region's limit.

The evidence is limited to macOS ARM64. The bootstrap has a restricted
C emitter. Full destructor body lowering, general nominal field types
and access, and async/thread state placement and cleanup have further
coverage gaps. Local region metadata and pages use the platform virtual
memory APIs. The bootstrap's region search and commit strategies differ
from those of the Rust runtime. This comparison does not establish
identical layouts, footprints, or timing.

The macOS ARM64 host and UBSan runs matched 25 emitted program traces
and four expected region failures with Rust. They passed nine emission
refusals, 23 checker verdict comparisons, 83 checker witnesses, 74 AST/static
graph comparisons, 12 syntax refusals and both source budget boundaries.
The separate Rust destructor suite passed three programs at both
optimization levels and four refusals. The Rust region suite passed 14
runtime cases at both optimization levels and three annotation refusals.

Running the bootstrap emitter over the 14 Rust region witnesses returned
status 9 for eight inputs. The remaining cases include String and aggregate
vector payloads, interprocedural transfer (including recursive calls),
and region cleanup on loop edges. Six inputs reached C emission and
matched the Rust executable's exit status, stdout, and stderr in a
separate differential run.

### Bootstrap regional fixture and destructor parity

The bootstrap executes all 14 Rust region fixtures on macOS ARM64. The
differential test builds emitted C with UBSan at `-O0` and `-O2` and compares
exit status, stdout and stderr. It also inspects generated allocation calls
for dedicated placement in the recursive and retained-in-loop witnesses.
The fixtures include UTF-8 byte lengths, inline aggregate elements, owned
string slots, loop exit cleanup, and results returned from a borrowed pool.

All three programs in the Rust destructor suite reach C emission and
match the Rust executable. The verifier checks destructor bodies.
Synchronous coverage includes nested defaults, scalar fields, a pool local
to a destructor, and adoption of a previously constructed named value.
A pool slot that escapes a block can own inline fields allocated in the
child. The new regression exposed a cursor rewind that changed the child's
destructor output from `7` to `9` after the next allocation. The emitter now
follows the ownership edges before rewinding and the trace is `7, 9`.

For the supported async calls, the generated frame occupies a dedicated
region. The scheduler requeues the frame at each `yield`. A join waits
for completion before releasing the frame. On exit, the scheduler drains
any remaining autonomous tasks before their frames are reclaimed.
Additional execution comparisons cover multiple captures, two suspensions,
and an abandoned handle. For all three async cases, a shim makes
`pthread_create` fail in both outputs and checks the destruction traces.
The bootstrap rejects a second join on the same handle.

Scope limits remain in the bootstrap emitter. Async lowering is limited
to top-level spawn sites, void tasks with inline aggregate literal captures,
and straight-line suspension and cleanup. The current join lowering
supports discarding the result. The synchronous emitter restricts
general function signatures and nominal field and destructor operands.
For example, it checks a pure identity relay for a named aggregate but
has no general calling convention for owned aggregates. Region sizing uses
conservative local bounds rather than the complete Rust placement pass.
The bootstrap validation suite also executed 33 generated execution
traces, four additional region-limit comparisons, ten existing emission
refusals and the additional duplicate-join refusal. Its frontend checks
covered 74 AST and static-graph comparisons, 12 syntax refusals, two
source-size boundaries, 83 checker witnesses, and 23 verdict comparisons
against Rust. The results establish parity for these fixtures on this
host. No language rule changed.

### Bootstrap lexer parity

`validation/check_crust_lexer.py` compares the raw lexer outputs before
conditional target selection or parsing. On macOS ARM64, the native
bootstrap build and the `-O2` UBSan build matched the Rust lexer on 488
token streams (class, byte span and EOF) and 311 rejected inputs
(diagnostic category and byte offset). Inputs include the repository's
Crust files, shared syntax fixtures, boundary cases and 384 deterministic
compositions using seed 20261114. Additional file-level checks rejected
five malformed UTF-8 inputs and exercised the 128 KiB input limit,
including a maximum-density token stream and an assembly token at EOF.

The bootstrap now accepts Unicode whitespace before the opening
brace of an assembly block. It preserves the Rust lexer's precedence
between unterminated and invalid assembly operands and matches byte
offsets on malformed numeric and text literals. Unicode outside an
assembly prefix or a token that can contain it follows the reference
lexer's existing behavior. In particular, the two lexers keep adjacent
`>` tokens separate so the parser can resolve operators and generic closers
in context. The regular frontend still uses its internal operand tokens.
The differential stream exposes each assembly block as a single token,
matching Rust. This cycle changes no language rule and needs no std API.
The input budget remains a bootstrap file-loading limit.

### Bootstrap parser parity

`validation/check_crust_parser.py` compares ASTs at the parser boundary.
Both invocations use host target selection and return before building the
static execution tree. The comparison preserves child order, node and name
byte spans, visibility and the parent relationship. It runs on distinct
program inputs from Crust files, documentation, and Python test and validation
fixtures. Historical fragments in those sources may be rejected as standalone
programs. The Rust fragment entry points are outside this comparison.

The fixes distinguish a lexical name from a permitted declaration name,
preserve precedence when parsing a condition before a block, and apply the
reference parser's retry when an empty constructor and the following block
compete for the same braces. They also cover chained variant constructors,
postfix expressions following an `else if`, ranges in each `try_slice`
argument, annotations on move blocks, the legacy region directive still
accepted by Rust, and the exact `"C"` ABI spelling. No grammar or std API
changed. The file limit remains 128 KiB.

On macOS ARM64, both the native bootstrap and its `-O2` UBSan build
matched **1,506 ASTs** and **3,415 rejection verdicts**. The final corpus
had no input above 128 KiB. The lexer differential and the wider bootstrap
regression also passed, including 74 previously tracked AST and static-tree
comparisons. The rejection comparison checks the verdict. The Crust
parser currently returns status 7 for a syntax error, while Rust reports a
message and a byte offset.

### Bootstrap static tree corpus parity

`validation/check_crust_static_tree.py` uses the validated program AST
corpus and compares the representations before rule checking. The first
pass matched all 1,506 trees from that corpus. Focused cases found two
discrepancies. Rust previously installed external signature parameters in
the enclosing environment, making them visible to later functions and
eligible for closure capture. Both implementations now give each
external signature its own lexical scope. The bootstrap previously
attached a named-move fact to `move _;` with no destination binding.
It now preserves the AST node and matches Rust's plain syntax fact.

The Crust representation now retains the fact tag, mutability, declared
type and initializer links in its node table. The differential test checks
these fields along with scope membership and parentage, declaration and use
links, ordered operands, capture sets, exit targets, and scope ends. On
macOS ARM64, **1,512 trees** matched in both the native bootstrap and its
`-O2` UBSan build. The bootstrap integration regression and the three Rust
unit tests passed. The assembly suite's frontend checks and C emission
ran, but its Linux x86-64 execution witnesses could not be built with
the macOS ARM64 host compiler. The comparison covers program ASTs and
syntax-derived facts. It does not cover post-analysis lifetimes or Rust's
standalone block and signature parse modes. No std API or normative rule
changed.

### Bootstrap verifier corpus comparison

The verifier-only command consumes the resolved static tree and returns
before C generation. Its whole-program comparison uses the Rust verifier
on the validated program AST corpus. Status 8 is a rule diagnostic and
status 9 is incomplete coverage. The harness can write the unresolved
cases as JSON lines and can require full parity with `--require-parity`.
The previous `--check` command still accepts standalone function witnesses.

The baseline on the 1,512 ASTs had 149 false accepts, two false rejections,
and 1,178 unsupported inputs. The pass added declaration checks for
unknown field and parameter types, missing generic arguments, inline
layout cycles, destructor signatures, the program entry point, and
pool and region capacities. Scalar blocks and conditional results now
preserve moves and availability. Arithmetic reads its operands, and
the checker handles a single borrowed scalar call argument and writes
through a mutable reference parameter. A declaration is still allowed
to be recursive through an allocation or a reference. The verifier
uses the static mutability field at the updated initialization sites.

On macOS ARM64, the native and `-O2` UBSan bootstrap runs matched 104
acceptances and 967 rule rejections out of 1,530 ASTs. Neither run
produced a contradictory verdict. **459 cases remain unsupported**.
Of these, Rust accepted 144 and rejected 315. Coverage gaps include
arrays and aggregate projections, structured and async results,
and contracts for calls with multiple dependent arguments. Compound
constant integer evaluation remains partial. A matching rejection
counts as verdict agreement regardless of the exact diagnostic. These
results neither establish language-wide soundness nor include target
platforms beyond the host. No language rule or std API changed.

#### Fixed places, scalar tasks and collection verdicts

The Crust verifier now checks fixed scalar arrays, nested literal shapes,
scalar projections of inline aggregates, and scalar array arguments and
borrows. Assignments check the projected place before evaluating the
right-hand side, then check the write after it. The same flow pass checks
scalar loop results and joins the availability states of `match` arms.
Integer constants use sign and magnitude, and the checker handles ordinary
floating literals and exact numeric casts. Decimal literals at the rounding
boundaries remain unsupported.

The task pass distinguishes a Future, a synchronous handle, an async handle
and its completion result. It checks scalar results, scalar and fixed scalar
array captures, and isolated thread bodies with scalar named moves. The pool
pass checks scalar allocations forwarded through an injected pool, and refuses
destroying a pool that is still held by a checked owner. The collection pass
covers scalar `HashMap` values, with an origin on options returned by lookup.

On macOS ARM64, the native comparison and the UBSan bootstrap run
matched all verdicts issued by Crust. The UBSan run covered 1,565 ASTs:
164 joint acceptances and 1,106 joint rejections. The native comparison
covered 1,564 ASTs with one fewer joint rejection because a split module
added an input to the subsequent corpus. Neither run contradicted Rust. It resolved 164 of the original 459 unsupported
inputs. **295 inputs remain unsupported**, including 97 accepted by Rust
and 198 rejected by Rust. `--require-parity` still exits with status 1.
The complete bootstrap execution regressions also passed, including 33
generated traces, 14 regional witnesses at two optimization levels, and
three async destructor traces.

Remaining gaps include stored references and allocations in collections,
their projections and argument contracts, tasks with borrowed or owning
captures and results, and several forms the reference rejects before
dataflow. These results measure verdict parity on the corpus; they do
not establish language-wide soundness. No normative rule or std API changed.

#### Stored dependencies and task captures

The Crust verifier records a referent for each supported fixed-array cell
and retains candidate referents for a dynamic selector. Reborrows through
an array view retain both the selected referent and the parent view.
The map pass tracks payload dependencies across constant-key insertion,
replacement, lookup and removal. It checks whether an entry keeps its
pool live and whether an extracted loan still depends on its target.
Mutation histories that cross control-flow joins remain open.

Task summaries retain capture roots and exclusive access through creation,
launch, movement and completion. Supported worker returns substitute the
caller's bindings for symbolic parameters. The verifier also checks
growing scalar allocations returned to the caller and direct waits in a
synchronous helper. A helper that conditionally waits, deferred effects
that change stored references, nested handles and general aggregate outputs
remain open.

Focused comparisons exposed two false acceptances during integration:
two exclusive loans of the same target stored in one initializer, and a
caller writing through a reference that had been reborrowed by a launched
task. Both witnesses are now verifier regressions.

On macOS ARM64, the UBSan run matched 201 acceptances and 1,155
rejections across 1,582 ASTs. It produced no contradictory verdict.
226 cases remain unsupported, including 65 accepted and 161 rejected by
Rust. The strict parity command returned status 1. Direct await and a
synchronous relay preserve the stored referents of supported vectors.
A direct entry replacement in an immediately matched lookup retains the
previous and replacement roots across the merge. A targeted comparison
caught a false acceptance when the old root was erased at that merge.
A direct synchronous helper and a positional relay propagate the
entry replacement effect, including rejection of a shorter target.

An intermediate native build passed the bootstrap integration suite with
83 checker witnesses, 23 differential verdicts, 33 execution traces,
14 regional cases at both optimization levels and three async destructor
traces. No independent audit was run in this cycle.


#### Deferred entry effects and returned handles

The bootstrap binds the target entry and the incoming reference to the
launched task. It retains the previous and incoming referents across
completion because launch can fail. The caller cannot access the captured
entry before completion. The effect crosses a direct synchronous wait,
a direct asynchronous wait, and a native factory that returns the handle.
Awaiting an async factory that returns a blocking handle leaves the inner
effect pending until that handle is awaited.

A handle carried by a supported enum retains its effect through a move or
a recursive relay. A single-variant recursive consumer establishes that its
handle is awaited with a synchronous join. An autonomous handle can also
be captured inside an enum in a native worker. For supported aggregate
identity tasks, the checked constructor remains linked to the result
across direct await and a successful join or async-handle await.

The first envelope implementation produced four false rejections because
scope-exit checking visited the outgoing value as if it were an abandoned
local binding. Starting the exit walk at the declared bindings corrected
that discrepancy. Two focused fixtures check the same entry access on
either side of the await.

On macOS ARM64, the UBSan corpus run covered 1,587 ASTs, with 216 matching
acceptances, 1,163 matching rejections and zero contradictory verdicts.
208 cases still reported unsupported (51 Rust acceptances, 157 Rust
rejections). Strict parity exited with status 1. The bootstrap integration
suite, run on the preceding relay build, also passed 83 checker witnesses,
23 differential verdict comparisons, 33 generated traces, 14 regional
comparisons at both optimization levels and three async destructor traces.

Coverage is still partial for effect paths through collections, composite
branches and aggregate result construction. The corpus comparison checks
verdicts. No independent audit was run in this cycle.

A subsequent native comparison also classified closure expressions as
outside the Rust verifier's expression coverage. It matched 216
acceptances and 1,179 rejections across 1,585 ASTs, with no contradictory
verdicts and 190 unsupported cases. This is reference-verifier behavior;
it does not change the closure grammar or language rules.

The next UBSan run covered 1,590 ASTs. It matched 219 acceptances and
1,184 rejections with zero contradictory verdicts. There were 187
unsupported cases (48 Rust acceptances and 139 Rust rejections).
This run covers recursive async waits, single-element vector removal
with a dynamic index, and a deferred effect that remains attached to its
handle when an earlier vector entry is removed. A targeted comparison on
the following build also matched extraction of an async handle from a
pool and refusal to destroy a pool while a Future captures an aggregate
containing one of its allocations.

A native comparison after pooled handle extraction and aggregate return
validation matched 221 acceptances and 1,185 rejections across 1,587 ASTs.
There were no contradictory verdicts. 181 cases remained unsupported
(46 Rust acceptances and 135 Rust rejections). The added result check
rejects references or pool allocations that originate in a local of the
returning function. A targeted follow-up also rejected access to a
mutable referent still borrowed by an aggregate returned from an await.

The latest completed UBSan comparison covered 1,591 ASTs and matched 221
acceptances and 1,190 rejections with no contradictory verdict. The 180
unsupported cases split into 46 Rust acceptances and 134 Rust rejections.
A subsequent native run also covered cleanup in the LaunchFailed arm
of aggregate completions, leaving 178 unsupported cases across 1,587 ASTs.
The corpus discovers syntactically valid Crust sources added under the
bootstrap package, so its denominator varies between builds.

The following UBSan comparison covered 1,590 ASTs. It matched 224
acceptances and 1,190 rejections, with 176 unsupported cases (43 Rust
acceptances and 133 Rust rejections) and no contradictory verdict.
The comparison covers call-site substitution for a returned field
holding a scalar loan or an allocation from a caller-supplied pool.
Strict parity still exits with status 1.

The next native run preserved the field tree of a pooled value across
await and reproduced the Rust verifier's rejection of bare map operations
that return a value. It matched 225 acceptances and 1,193 rejections
across 1,587 ASTs, with 169 unsupported cases and no contradictory
verdict. The earlier vector false rejection came from applying the
map's wider scope to an entry descriptor whose arm shares the vector's
scope. The scope check now uses the captured descriptor's scope.

The next UBSan run matched 225 acceptances and 1,194 rejections across
1,587 ASTs, with 168 unsupported cases and no contradictory verdict.
A subsequent focused witness confirmed that awaiting a task that returns
one borrowed field of its input preserves that field's referent while
releasing the other input field's reservation.

The UBSan run including that field projection matched 226 acceptances and
1,194 rejections across 1,587 ASTs, with zero contradictory verdicts and
167 unsupported cases (41 Rust acceptances, 126 Rust rejections).
Strict parity exited with status 1.

The native comparison covering a vector drain and its early-exit
counterpart matched 228 acceptances and 1,195 rejections across 1,587
ASTs, with no contradictory verdicts. 164 cases remained unsupported
(39 Rust acceptances and 125 Rust rejections). The full drain releases
all tracked reservations. With an early break and an optional autonomous
handle at the top, the original dependent handle remains reachable and
its referent cannot be accessed.

Extending constructor-result substitution to synchronous functions
exposed a false rejection when reborrowing a mutable field of a returned
aggregate. Its parent is a live aggregate descriptor with a field
dependency. Following that descriptor instead of treating it as a scalar
reference restored the accepted verdict in the focused run.

The ensuing UBSan run matched 230 acceptances and 1,195 rejections
across 1,587 ASTs on macOS ARM64. It found no contradictory verdicts.
162 cases remained unsupported (37 Rust acceptances and 125 Rust
rejections), and strict parity exited with status 1.

Type positions now reproduce the reference verifier's rejection of
unimplemented builtin types, including mutexes and numeric conversion
errors. This classification does not add or change language rules.
The latest UBSan run matched 230 acceptances and 1,204 rejections across
1,587 ASTs. It had zero contradictory verdicts and 153 unsupported
cases (37 Rust acceptances and 116 Rust rejections). Strict parity exited
with status 1.

An owned array embedded in a returned struct now keeps the dependencies
of its inline elements across await. The verifier resolves constant
indices through the array and follows ownership to the scalar pool slots.
The final run for this cycle matched 231 acceptances and 1,204
rejections across 1,587 ASTs under UBSan on macOS ARM64. There were zero
contradictory verdicts and 152 unsupported cases (36 Rust acceptances
and 116 Rust rejections). Strict parity remained incomplete.

#### Native results, conditional waits and aggregate provenance

A native worker can return an enum containing a pending handle. The outer
join transfers the enum and its dependency records. Only completion of
the inner handle applies its entry update. Discarding the outer result
while it still contains a dependent handle is rejected.

A recursive relay that waits on one path and transfers the handle on
the other retains the alternatives until the caller matches the enum.
The empty arm accounts for the completed effect, while the populated
arm receives the pending handle. This covers extraction from a pool,
removal from a vector and refusal to abandon a vector with a pending
dependent handle.

A match can return an owned aggregate from two arms when its fields
have equivalent dependencies. A conditional future returning a shared
borrow now keeps the two possible roots through await and field
projection. A regression verifies refusal to write the second root
before the projected reference's last use.

A struct returned by a native thread retains its field dependencies
through a typed completion relay. Passing a handle by value into an
identity relay preserves its payload and captures. A direct async
consumer keeps those captures until await and then projects the shared
field on the success path. A decreasing recursive worker forwards the
entry and incoming referent unchanged to the base case. Its enclosing
async factory exports the deferred entry effect in the returned handle.

The macOS ARM64 UBSan comparison matched 241 acceptances and 1,212
rejections across 1,593 ASTs, with no contradictory verdicts. 140 cases
remained unsupported, including 26 Rust acceptances and 114 Rust
rejections. Strict parity exited with status 1. The comparison confirms
verdicts on the corpus and does not establish general safety.

The subsequent native run matched 241 acceptances and 1,226 rejections
on 1,590 ASTs. It mirrored the reference's resolution errors for
qualified calls outside the supported standalone surface. The remaining
123 unsupported programs include 26 accepted and 97 rejected by Rust.

A second native run added receiver validation for methods unavailable
in the reference's standalone verifier. It matched 241 acceptances
and 1,246 rejections across 1,590 ASTs. It left 103 unsupported cases
(26 Rust acceptances and 77 Rust rejections). An additional focused
test validated the same entry effect through a synchronous decreasing
recursive relay.

The next UBSan comparison on macOS ARM64 matched 242 acceptances and
1,248 rejections on 1,592 ASTs. It reported no contradictory verdicts
and 102 unsupported cases (25 Rust acceptances and 77 Rust rejections).
This run includes the synchronous recursive relay and still exits with
status 1 in strict mode. Open families include recursive nominal
handles, tuples, and projections and transfers through collections.

The next UBSan checkpoint included temporary native handle destruction,
its scope-escape refusals, typed branch destinations and two checks for
tuple patterns. Across 1,592 ASTs, 243 acceptances and 1,255 rejections
matched. The 94 remaining unsupported cases comprised 24 Rust
acceptances and 70 rejections. There were no contradictory verdicts.

The following UBSan comparison matched 243 acceptances and 1,259
rejections across 1,591 ASTs. 89 cases remained unsupported, including
24 Rust acceptances and 65 Rust rejections. There were no contradictory
verdicts. Strict parity continued to exit with status 1.

Checks for invalid pool element types and moving a pool reduced the
next UBSan run to 87 unsupported cases on 1,592 ASTs (243 matched
acceptances and 1,262 matched rejections). The latest native run
also covered missing value alternatives and contextual pool element
types. On 1,590 ASTs it matched 243 acceptances and 1,263 rejections
and left 84 unsupported cases, including 24 Rust acceptances and
60 Rust rejections. Neither run found contradictory verdicts.

Field-use analysis now compares canonical field names in the static
tree. An unrelated field of the same name length no longer keeps a
borrow active. A later read of the same field still blocks a write to
its root. The static-tree comparison matched 1,588 trees, and the
verifier's UBSan checkpoint matched 244 acceptances and 1,264
rejections among 1,591 ASTs, leaving 83 unsupported with no
contradictory verdicts.

A function returning a shared field from an aggregate passed by value
now transfers only the selected provenance. The caller can mutate an
unrelated referent after the call. Under UBSan, the verifier matched
245 acceptances and 1,267 rejections on 1,594 ASTs, and 82 cases remained
unsupported (22 Rust acceptances and 60 Rust rejections).

Array element returns now propagate one origin for a constant selector
and every origin for a dynamic selector. The verifier accepts the
constant projection witness and refuses mutation of an alternate root
before the last reference use in the dynamic witness. Native and
UBSan comparisons each matched 246 acceptances and 1,265 rejections
over 1,591 ASTs. They left 80 unsupported cases (21 Rust acceptances
and 59 Rust rejections) and no contradictory verdicts.

The bootstrap regression suite passed 83 checker witnesses, 23 verdict
comparisons, 92 AST and static graph comparisons, and 12 syntax refusals.
It also passed 33 generated traces, 14 regional comparisons under UBSan
at both optimization levels, and three async destructor traces including
injected launch failure. The print-reference witness now expects a
type rejection because the checker diagnoses this input directly.

### Verifier parity on the remaining Rust rejections

This pass focused on the 59 inputs that the Rust reference rejected and
the Crust verifier had previously reported as unsupported. The static
tree checks now diagnose additional invalid places, effect contexts,
numeric constraints, and borrow escapes. The verifier also tracks
fixed-array slice roots, scalar tuple moves, and the possible borrow
roots of the supported recursive array relay. Appending a pool-backed
allocation to a vector records an ownership edge across branch joins.
Shared-reference appends in loops preserve the possible dependency on
each source. The native checks cover tracked local addresses used by an
assembly operand and AArch64 register classes. Crust still relies on
the reference backend for wider assembly and collection lowering.

The native and UBSan comparisons on macOS ARM64 each covered 1,602
program ASTs. Both verifiers accepted 251 and rejected 1,330. The two
runs produced identical reports, with no contradictory verdicts.
All 59 rejections in the original report now receive a rejection from
Crust. The remaining 21 unsupported inputs are all accepted by Rust,
so strict parity still exits with status 1. Seven focused regressions
cover slice liveness, tuple moves, collection cleanup, and an accepted
recursive array relay. The rejection comparison checks the verdict
and the shape of the diagnostic. It does not require matching the
reported rule or byte offset against Rust.

The bootstrap regression suite also passed 83 checker witnesses,
23 rule comparisons, 96 AST and static graph comparisons, 12 syntax
refusals and two input-size boundaries. Generated programs passed
33 execution traces, 14 region comparisons under UBSan at both
optimization levels and three async destructor paths including a
forced launch failure. The newly handled verifier cases establish
verdict parity only for the exercised inputs. They do not establish
code generation parity for those capabilities.

### Verifier parity on the remaining Rust acceptances

The Crust verifier now retains the dependencies that were missing in the
last 21 Rust-accepted inputs. The covered flows include fixed array and
tuple moves, projection and reborrowing of aggregate fields, conditional
pool results, pool-backed nominal values transferred through calls, and
nested ownership in vectors. Native worker results can carry autonomous
handles through nominal enum variants and a recursively forwarded fixed
array. The Rust verifier remains the independent implementation used as
the verdict reference for this corpus.

On macOS ARM64, the strict native and `-O2` UBSan comparisons each matched
272 acceptances and 1,331 rejections across 1,603 parsed programs. There were zero
contradictory verdicts and zero unsupported cases. Both reports of
differences were empty and `--require-parity` exited with status 0. A
replay of the original 21 inputs confirmed that each was accepted. The
full comparison caught a regression where the result of `join()` lost
the source pool of a transferred vector; the final native run accepted
that program again.

The bootstrap suite also passed 83 checker witnesses, 23 rule verdict
comparisons, 97 AST and static graph comparisons, 12 syntax refusals and
two input-size boundaries. It matched 33 execution traces, 14 regional
cases under UBSan at both optimization levels, and three async
destructor traces including a forced launch failure.

The strict comparison measures acceptance and rejection on the checked
corpus. It does not establish diagnostic equivalence, general safety,
or code generation parity for all programs newly accepted by the
verifier. It is separate from the adversarial audit.

### Bootstrap executable comparison

`validation/check_crust_codegen.py` selects the distinct sources accepted by
the Rust verifier from the existing comparison corpus. It asks each compiler
to emit C, builds each output separately and compares exit status, stdout,
stderr and the bytes of files produced in isolated working directories.
`--require-parity` fails for unsupported input, build failure, unexpected
timeout, sanitizer diagnostics or a difference in execution. The two
intentional infinite loops are compared for one second and counted separately.

The first full replay on macOS ARM64 matched 66 terminating programs and
two bounded traces, with 204 unsupported emitters. An intermediate replay
after expanding scalar expressions, calls, fixed arrays, slices, named
aggregates, fixed-capacity pools and scalar async task frames matched
158 terminating programs and two bounded traces in both the native
`-O0` and UBSan `-O2` builds. The other 112 programs still failed at
Crust emission. There were no C build failures or observed execution
differences among the programs emitted by both backends in that replay.

The regression suite at that checkpoint passed 33 execution traces,
14 regional comparisons under UBSan at both optimization levels, three
async destructor traces including an injected launch failure, 83 checker
witnesses, 23 verifier comparisons and 98 AST and static graph comparisons.
Focused UBSan replays also matched the two programs that read a pooled
allocation through a struct field, including a borrowed enum projection
and constructor overrides. A reference to an async local targets the
frame field before and after a yield.

These runs cover the selected host and witnesses. They do not establish
general safety or take the place of the independent adversarial audit.

The next full replay matched 163 terminating programs and the same two
bounded traces in native and UBSan builds. The 107 remaining differences
were unsupported Crust emissions. This replay included named pool
constructors, nested pooled fields, direct Future waits and reuse of a
region after destroying an inactive Future. One focused run had exposed
an uninitialized worker page size when a Future allocated its first
child region. Initializing the worker's datastack before its first poll
fixed the incorrect region-limit diagnostic.

Separate focused replays cover two levels of scalar borrowing and pooled
vectors carrying references and primitive allocations. A vector consuming
allocation owners cleans those entries before releasing its region.
Native workers, nested and blocking waits, task handles with aggregate
results, maps with entry dependencies, collection removal, additional
regional combinations and parts of aggregate cleanup still need
lowering. The fallback lowering keeps fixed scalar values in C locals
and uses its own classic datastack reservation for pooled storage. Exact
classic datastack sizing and placement parity are open.

The final replay of this cycle matched 168 terminating programs and two
bounded traces out of 272 Rust-accepted sources, in both native `-O0`
and fatal UBSan `-O2` builds. The same 102 sources returned unsupported
from Crust emission in each run. Every source emitted by both compilers
built and matched its reference run. Strict parity returned status 1
in both builds. Twelve focused UBSan executions matched, including
reuse of both source pool slots after a vector carrying their allocations
is consumed. Ten examples compiled with warnings treated as errors.

The bootstrap regression suite passed 33 execution traces, 14 regional
comparisons at both sanitizer optimization levels, three async destructor
traces, 83 checker witnesses, 23 verdict comparisons, 99 AST and static
graph comparisons, 12 syntax refusals and two input-size boundaries.
The strict verifier replay separately passed with 272 shared acceptances
and 1,333 shared rejections across 1,605 ASTs.

Reproduce the executable comparison with
`python3 validation/check_crust_codegen.py --require-parity`; add
`--ubsan` to compare optimized, instrumented executions and
`--report path.jsonl` to retain the remaining sources and diagnostics.

### Native workers, aggregate results, maps and regional cleanup

The bootstrap now emits a native worker frame with its capture fields
initialized before launch. A detached worker and its handle agree under
the runtime lock on who releases the frame. Native and async results use
their typed layout at handoff. Async continuations retain their locals,
pattern bindings and pending waits in the frame. A blocking worker wakes
its registered waiter on completion.

The map implementation keeps a hash index and stable entry addresses
inside the backing region. A move carries the map descriptor and its
entries across a scope or task. A removed entry can be reused, and
destroying the map destroys the entries it still holds. Scope cleanup
also covers owning arrays and tuples. Explicit fixed stack budgets and
page reclamation use the active stack and region marks.

The intermediate native-worker replay matched 186 terminating programs
and two bounded traces in both configurations, with 84 unsupported.
A subsequent replay surfaced two lifetime defects in the generated C.
A resumed match read an automatic C pattern binding left behind by the
previous poll, and a pool slot retained an enum payload that had already
been moved, allowing a completed handle to be released twice. Both
defects were reproduced with the existing corpus. The regenerated
executables passed the focused sanitizer replay after pattern bindings
moved into their frames and pool extraction relinquished the source slot.

The 28 focused replays also covered nested array projections, UTF-8 byte
counts, tuple destructor order, a fixed-stack capacity diagnostic and
reclamation with a surviving region. Both backends produced the same
outputs for three launch-failure injections under fatal UBSan. The failed
native worker freed its frame before a retry, a failed native launch
released an owned capture, and a failed blocking launch allowed reuse of
the captured allocation's slot. The checks compare execution on macOS
ARM64. They do not establish general memory safety or target coverage.

The differential harness uses the existing line expectations for the two
witnesses with independent native writers. It requires the exact lines
and multiplicity from both backends, while still comparing exit status,
stderr and output files. A repeat observed both print orders in Crust
for the abandoned-thread witness. The remaining finite traces retain
byte-for-byte comparison.

The bootstrap regression suite passed 107 AST and static graph
comparisons, 12 syntax refusals, both input-size boundaries, 83 checker
witnesses, 23 verdict comparisons, 33 generated execution traces, 14
region comparisons at both sanitizer optimization levels and three async
destructor paths. A separate strict verifier replay matched 272
acceptances and 1,341 rejections over 1,613 ASTs. Nine C samples from the
final build also compiled with warnings treated as errors.

The final strict comparison passed in native `-O0` and fatal UBSan
`-O2` builds on macOS ARM64. Each run covered all 272 Rust-accepted
sources, with 268 exact finite traces, two independent-writer traces
matching their existing unordered oracle, and two intentional infinite
loops matching up to the one-second deadline. Both difference reports
were empty and `--require-parity` exited with status 0. Exact internal
placement and capacity inference outside the exercised programs remain
outside this evidence.

## Crust package bootstrap

The Rust-built `crustc` now reads a package manifest and the files under
`src/`, retains their module and file identities, and rewrites resolved
symbols before passing the result to its existing parser, verifier and C
backend. The native directory adapter uses the host C ABI from Crust
assembly. The package source buffer has a 2 MiB limit. The bootstrap
command takes the standard library source directory explicitly when a
package imports it.

On macOS ARM64, one two-module package with a grouped aliased import
emitted C that printed `42` in native `-O0` and fatal UBSan `-O2` builds.
A second package used a named type from the imported module and called a
function through a module alias. Its fatal UBSan build also printed
`42`. Both compilers refused a private import, a duplicate alias and an
import that collided with a local declaration. Directory adapters on
other targets were outside this run. At this point the Crust path supported
same-package imports and explicitly supplied std sources. Embedded std
and path and Git dependency loading were handled by the Rust bootstrap.

The actual compiler package exposed an incorrect N5 diagnostic for a
mutable subslice borrowed through a parameter. The projection now uses
the slice's referent mutability. Both compilers refused writing through
a shared slice with a mutable binding and writing through a parent
slice while its mutable reborrow was live. A repeated `Cell` initializer,
subslice reborrow and whole-element replacement matched the trace
`42, 42` under fatal UBSan. A packaged byte-slice comparison printed
`true`, an `else if` witness printed `10, 20, 30`, and the scalar
conditional inside a comparison printed `true, false` under fatal UBSan.
The linker carries the identity of the standard argument wrapper's
runtime call into verification.

A nontrivial ARM64 assembly program emitted by `crustc` called
`putchar` with a Crust operand in both native and fatal UBSan builds.
Another fatal UBSan run matched Rust's four-width trace `40, 41, 42, 43`,
including a binding written and read within one assembly block. UBSan
covers the generated C in these runs. The assembler instructions were
checked by their observed effects.

Run the package comparisons with the Rust-built bootstrap:

```sh
python3 validation/check_crust_packages.py --bootstrap /path/to/crustc
python3 validation/check_crust_packages.py --bootstrap /path/to/crustc --self-host
```

The self-host check invokes the Crust package path on the actual compiler
package and supplies `stdlib/src`. The first result witness originally
stopped verification at status 9. General results now keep their two
payload types in the verifier and use a tagged union in C. The same
code handles typed arguments and returns, early returns, moves through
forwarding functions and exhaustive matches for the supported payload
types. The package regression exercises `Result<i64, Failure>` and
`Result<(), Failure>`. The Rust-built reference and the generated native
and fatal UBSan executables printed `42, 17, 1`. Both verifiers rejected a
wrong payload type, a second move of the same result and an incomplete
match. Another witness used a record with a destructor as both payload
types. The native and fatal UBSan traces matched Rust through forwarding,
explicit destruction, a wildcard and a scope exit. The C wrapper marks
the old result inactive on a move and destroys only the active arm.

The self-host replay then exposed unsupported internal expressions.
Focused comparisons cover a scalar moved by a conditional argument,
destructuring a tuple produced by a conditional, a function return from
inside a value-producing branch, shared record arguments including
borrows of slice elements, a scalar function called from a loop
condition and reinitialisation of a mutable scalar after a move. The corresponding refusal cases cover a maybe-moved
binding, a duplicate tuple move, an incompatible reference argument and
a mismatched early return type. The scalar loop admits only calls
whose arguments cannot consume bindings. The borrowed record
support covers shared synchronous arguments of dependency-free records.

The next passes added forwarding of named slice descriptors, moving a
record into a slice element, and shared slice arguments in conditions.
The focused fatal UBSan runs printed `42, 42` for forwarding,
`42` for record replacement and `2` for a shared-slice loop. Both
verifiers refused a use after passing the named mutable slice. A
Darwin ARM64 assembly witness read `42` through an address derived
from the first element of a slice. The verifier retains the backing
binding through assembly operand evaluation.

A package importing `std::env::args` from the complete standard library
matched the Rust reference for an empty argument list, `hello`, and an
invalid UTF-8 argument. This borrowed result uses process-lifetime
storage and the linker restricts the underlying runtime call to the
standard wrapper. Arbitrary borrowed result payloads remain outside the
bootstrap coverage. The linker emits standard modules referenced by
the package and preserves the private platform namespace.

The bootstrap now verifies and lowers associated functions, methods
with borrowed receivers, borrowed record fields, and `usize` payloads.
A nested mutable receiver witness returned `2, 42` in the Rust reference
and generated C under fatal UBSan. The `std::io::File` package regression
matched the reference in native and fatal UBSan builds for a three-byte
file, an empty file and a missing file. Both package paths refused
importing private platform functions. The enlarged bootstrap package
exceeded the old 262,145-node table, which was reproduced with a bounds
diagnostic in the generated bootstrap parser. Its parser, static graph
and node-indexed analysis tables now hold 524,289 entries.

The Rust-built bootstrap replayed 273 accepted programs in native
`-O0` and fatal UBSan `-O2` builds. Both strict runs exited zero with
269 exact traces, two unordered traces and two bounded infinite loops.
The bootstrap regression suite also passed 115 AST and graph
comparisons, 12 syntax refusals, both input-size boundaries, 83 checker
witnesses, 23 verdict comparisons, 33 generated execution traces, 14
region comparisons and three async destructor traces. The two largest
source modules were split into files in their existing directories to
preserve standalone input limits.

Full package emission exposed one final type inference mismatch in the C
backend: the verifier inferred `bool` for an unannotated repeated
boolean array, while lowering guessed `i64`. The regression now reads
the first and last elements of a 524,289-element array after writing the
last element; the Rust reference and both generated builds print
`false, true`.

On macOS ARM64, the Rust-built `crustc` emitted 9,889,275 bytes of C
from its own package and `stdlib/src`. That C compiled both natively
at `-O0` and with fatal UBSan at `-O2`. The native second-generation
binary passed the package regressions. Both builds compiled their own
package again and produced C byte-for-byte identical to the second
generation, with no sanitizer diagnostic.

`check_crust_codegen.py --require-parity` exited zero with each
second-generation binary, in native mode and with `--ubsan` respectively.
Each run covered 273 accepted programs: 269 exact traces, two unordered
traces, and two intentionally infinite loops compared up to the deadline.
Both discrepancy reports were empty. This establishes executable parity
on the corpus and a bootstrap fixed point on macOS ARM64 only.

## Installed package build

On macOS ARM64, `crustc build PACKAGE -o OUTPUT` finds the standard
library at `../share/crust/stdlib/src` relative to the resolved compiler
binary. It reuses the package verifier and C emitter and passes separate
arguments to `cc` from `PATH`. The driver places the temporary C and
executable in a private directory beside the requested output and
publishes the executable by renaming it after the C compiler succeeds.

The installation witness invokes `crustc` through a symlink from a
separate working directory. Its external package has two modules and
imports `std::num::min_i64`. It builds to the relative output name
`-external program` and prints `42`. A wrong argument type, a missing
standard library and a C compiler exiting with status 37 are reported
on stderr. Each failure preserves the previous output, and the package
and C compiler failures leave no temporary build directory.

The installed compiler rebuilt its own package with the same command.
That second-generation binary built and ran the external package again
with output `42`. The package regression suite and the external build
witness also passed using a compiler generated by the previous
self-hosted compiler and built with fatal UBSan at `-O2`.
The new build driver currently targets macOS ARM64.

```sh
python3 validation/check_crust_packages.py --rebuild
```

## Dependencies in crustc build

The package graph stores the canonical path or Git URL and full commit
ID for each package. It checks declared names and tracks visibility from
direct dependencies. The Git loader fetches into a private temporary
directory, checks both `FETCH_HEAD` and the object type, and reads sources
from the detached checkout. Canonical paths for inputs inside a checkout
must stay within that checkout, including when traversing symlinks.

The macOS ARM64 build witness combines `std`, transitive path dependencies
and a pinned local Git repository with a path dependency inside its
checkout. The repository's current commit returns `999`; both Crust and
the Rust frontend built programs that returned `42` from the pinned
commit. Nine refusals covered imported and qualified access to a
transitive dependency, an invalid pin, a missing commit, a mismatched
package name, reserved `std`, mixed dependency fields, a cycle and a
symlink escaping the checkout. A failed build preserved the executable.
The package suite completed with the native compiler and with fatal
UBSan at `-O2`. A separate local Git repository with SHA-256 object IDs
built and printed `64` using its 64-digit commit ID. The Git witnesses
used local repositories. A separate graph with two parents sharing a
path dependency built and printed `42`. Pointing one parent at a second
source for the same package name failed and preserved that executable.

The larger compiler package exposed a C lowering bug. A record
declaration's destructor node ID was interpreted as an array type while
collecting C definitions. A focused program with a destructor after 3,517
scalar calls reproduced the invalid typedef with the old emitter. After
the fix the generated C built with fatal UBSan and printed `17` once.
The installed compiler then rebuilt itself with `crustc build`. Its
successor built the external two-module package and printed `42`.

## Compound assignments in both compilers

The Rust frontend and `crustc` accept the five arithmetic, three
bitwise and two shift assignments. The lowering prepares the place,
checks its bounds if needed and reads the old scalar before evaluating
the RHS. It runs the same checks as the corresponding binary operation
and writes the result to the prepared place only on success. If the RHS
suspends, the prepared address and old value survive in the task frame.
The parser recognizes adjacent `>>=` in assignment position without
changing the interpretation of nested generic closers followed by `=`.

On macOS ARM64 the targeted suite matched the expected results in both
compilers: eight successful executions, six expected runtime traps and
fourteen compile-time refusals. The generated programs were built with
fatal UBSan. The index trace shows one evaluation before the RHS, and an
out-of-bounds index stops execution before the RHS prints. The async
witness changes the index during the suspension and still writes the
original array element. A second async witness updates a distinct cell
before suspending and then writes back a floating-point result. Other
witnesses exercise fields, slices, double dereferences, reads of the
reserved place and distinct fields or indices. The alias checks can
reject places whose disjointness the frontend cannot prove.

The lexical corpus matched 606 token streams and 311 diagnostics. The
parser matched 1,684 ASTs and rejected 3,420 inputs in both compilers.
The executable comparison passed `--require-parity --ubsan` on all
290 accepted programs: 286 exact traces, two unordered traces and two
intentionally infinite loops compared up to the deadline.
The package regression suite passed. The updated `crustc` rebuilt
itself with `build`, and its successor built and ran the external
two-module package with output `42`.

The broader verifier comparison still reports four discrepancies outside
compound assignment. The Rust frontend rejects a synchronous call from
an async body that `crustc` accepts; the discrepancy reproduces with a
plain assignment on the previous compiler. Three other inputs have
unsupported verdicts in `crustc` and are rejected by Rust: a by-value
method, an unresolved qualified function and `addr(12)`. Their
`crustc` verdicts also match the previous compiler.

```sh
python3 validation/check_compound_assignments.py
```

## By-value method receivers and diagnostics

Both compilers pass the receiver of `fn read(self: Packet)` as their first
by-value argument. The call marks the original binding moved before later
arguments are evaluated. On macOS ARM64, the generated programs built with
fatal UBSan and matched the expected trace `40, 42, 6, 5`. The first
destructor runs on return from the scalar method, while the other record
is returned to its caller and cleaned once by the final consuming method.
Both checkers reject using the original binding again, reading it in a
later argument, passing a reference as the owned receiver, and consuming
the record with an active loan. They also reject a direct method call to
the reserved destructor `drop`.

Crust's general by-value record parameter support covers records made of
primitive fields and nested records whose lifetime checks fit that model.
A receiver with a stored borrow is outside that coverage and gets a
specific unsupported-type message. `addr(12)` reports an invalid argument,
and a qualified call in a standalone file reports an unknown function.
The numeric diagnostic stream retains its rule and byte offset.

The package test rejects both `use leaf::value` and `leaf::value()` from
`app` when only `middle` declares `leaf`. The error identifies `leaf` as
missing from the direct dependencies. Declaring `leaf` in the manifest of
`app` makes the same call build and print `45`. Human-readable diagnostics
were checked on macOS ARM64.

The executable comparison under fatal UBSan matched 290 programs before
the final change that restored the rejection of direct destructor calls.
The final receiver regression checks that rejection alongside the
successful generated programs. The final package suite and the 28
compound-assignment regressions passed.

The final verifier comparison still reports two discrepancies. Rust
rejects the synchronous call in an async body that Crust accepts. Crust
reports an unsupported receiver type for the diagnostic witness with a
stored borrow, while Rust rejects the dereference in its body.

## TCP and UDP sockets

The standard library exposes blocking IPv4 `Connection` and `Listener`
types for TCP and UDP. The public wrappers each contain one owned
socket. Target selection uses Linux syscalls, macOS system functions,
or Windows Winsock from inline assembly. The Windows implementation
balances Winsock startup and cleanup across successful opens, accepts,
and failures.

The peer in `validation/check_rust_net.py` uses Python's socket API. It
observed TCP accept, a connection still usable after its listener was
dropped, outbound TCP connect, and EOF. It observed UDP truncation,
sender address and port, a datagram reply, and a zero-length datagram.
Each run also moved and closed 128 UDP listeners, checked that duplicate
binds failed, and then rebound each port. The Unix and Linux runs used
a 32-descriptor limit. Three external attempts at direct construction,
pool default construction, and nested pool default construction were
rejected by both compilers on macOS ARM64.

| Target | Result at `-O0` and `-O2` |
| --- | --- |
| macOS ARM64 | Rust frontend and rebuilt `crustc` matched under fatal UBSan. |
| macOS x86-64 | Rust frontend matched under fatal UBSan, with Rosetta. |
| Linux x86-64 | Rust frontend matched in Docker with Rosetta, using a static musl build. Rosetta rejected the first ELF before execution with `bss_size overflow`; the test executable linked with `-Wl,-z,norelro` ran successfully. |
| Windows x86-64 | Rust frontend matched under Wine. Native Windows execution remains open. |
| Windows ARM64 | Rust frontend linked both PE binaries. Execution remains open. |

The `crustc` package regression suite also passed on macOS ARM64.
These executions exercise the blocking IPv4 API and the listed resource
paths. They do not constitute an independent memory-safety audit.

```sh
python3 validation/check_rust_net.py --ubsan
python3 validation/check_rust_net.py --crustc /path/to/crustc --ubsan
```

## Typed socket addresses and async method captures

The blocking wrappers now use typed IPv4 endpoints, an `Option<i32>` TCP
backlog, and protocol-specific operation names. The receiver of an empty
UDP datagram still reports the remote endpoint. The first macOS witness
failed this check when the native buffer length was zero. The corrected
path uses one scratch byte and classifies any nonempty datagram as too large.

The updated Python loopback peer checked the address parser, TCP I/O and
EOF, empty TCP slices, UDP empty and oversized datagrams, and reuse of
128 UDP ports after moving and destroying their listeners. The traces
matched at `-O0` and `-O2` on macOS ARM64 and x86-64 with fatal UBSan and
on Windows x86-64 under Wine. Windows ARM64 linked at both levels.
The Linux container launch produced a listener port, but the macOS peer
could not reach the container's loopback listener. A same-process Linux
x86-64 witness exchanged TCP and UDP traffic inside an isolated container
at both levels and checked that the next datagram arrived after a truncation.

The rebuilt `crustc` passed the two-module package and File witnesses.
Importing the new `SocketAddr` module still fails with status 9 during
self-hosted compilation. Removing its associated parser, or replacing the
parser's `&str` parameter with `&[u8]` in a minimal witness, allows the import.

An async method captured `&mut self` and a mutable byte slice, yielded,
wrote through the slice, and printed the new byte after `.await`. The
compiler refused an early receiver destruction and an early write to the
slice. The Rust task-region suite completed with 63 accepted programs
and 28 refusals. The native async socket wait and completion paths and
the borrowed `split()` remain pending.

## Postfix propagation with question mark

S5b adds a postfix operator. The Rust compiler evaluates the operand
once, tests its variant, and emits an ordinary return on the failure
branch. A `Result` with different input and output error types resolves
an associated `from` function with an exact signature. The success path
extracts the payload and preserves its borrow and ownership information.
`Option` uses the same control flow, with an empty `None` return.

Two generated-C programs ran on macOS ARM64 under fatal UBSan at `-O0`
and `-O2`. The traces covered both outcome branches, unit success,
`.await?`, conversion only on failure, cleanup of earlier arguments,
owned error propagation, a pooled payload and slot reuse, a moved
handle, and an extracted borrow. A package built and ran with a
conversion resolved through an imported type alias. Ten static refusals
covered invalid operands and return families, missing or incorrectly
typed conversion functions, use after move, a returned local borrow,
and an early exit that would skip a required join.

The Rust compiler unit tests, destructor and tuple witnesses, and
package regression suite passed. The package suite now uses a missing
child of `std::net` for its unknown standard-module case, since the
networking change made `std::net` available. The self-hosted compiler
still needs support for S5b.

The UBSan executable comparison with the existing `crustc` matched
290 programs. Its three discrepancies all come from the new fixtures.
The self-hosted compiler rejects the two programs using `?` during
lexing and cannot emit the standalone test helper that constructs
`Option::None`.

```sh
python3 validation/check_rust_propagation.py
```

The overload follow-up exercised two `from` functions on one type.
Their traces distinguished selection through `?`, `.await?`, and a
direct call through an imported alias. Numeric calls exercised both
the default type with multiple overloads and contextual typing with
a single overload. The four added refusals covered duplicate source
types across `impl` blocks, an unmatched source type, a duplicate
under an ordinary method name, and a second `from` with an
incompatible return type.

## Async TCP, UDP and socket wakeups

This cycle implements the existing networking design. The platform
bindings are written in Crust with `@asm`. Linux and macOS use
nonblocking sockets and one-shot readiness notifications through epoll
and kqueue. Windows submits overlapped Winsock operations to IOCP,
including `ConnectEx` and `AcceptEx`. A pending operation keeps its
dependencies until it returns. The runtime synchronizes registration,
the poller's transition to parked, and wakeup under the same lock.

The TCP witness connects to an async listener, moves the read and write
halves of the accepted connection into separate tasks, exchanges a byte
in both directions, and checks immediate success on empty slices. The
peer observes EOF after the two joins and the owner's destruction.
Connecting to the closed listener yields `ConnectionRefused`. Moving
the destruction before either half's join is refused by the verifier.
An external package's import of the platform reactor is also refused.

The UDP witness checks that a datagram larger than the destination is
consumed, that an empty datagram into an empty slice returns its sender
with a count of zero, and that a reply fitting the destination exactly
is received intact. The address witness checks a valid address, a port
overflow, and an embedded NUL.

| Environment | Final executable witnesses at `-O0` and `-O2` |
| --- | --- |
| macOS ARM64 | TCP, UDP, and address parsing passed with fatal UBSan. The address witness also passed with the rebuilt `crustc`. |
| macOS x86-64 under Rosetta | TCP, UDP, and address parsing passed with fatal UBSan. |
| Linux x86-64 in a local Docker container | TCP, UDP, and address parsing passed with fatal UBSan. The peers ran in the same container. |
| Windows x86-64 under Wine | TCP, UDP, and address parsing passed. |
| Windows ARM64 | TCP, UDP, and address parsing cross-linked. Execution remains open. |

The first Windows run returned error 87 on repeated association of a
socket with IOCP. Registration now happens exactly once for each
listener or connection, independently of which tasks submit operations.
The Windows async build also exposed Unix-only mappings in the regional
runtime. Regions now reuse the existing target-specific guarded mapping
and page-size helpers.

The bootstrap verifier and emitter now accept a shared `&str` parameter
and give UTF-8 literals a static, length-delimited representation.
The standard library can call its typed parser from a package built by
`crustc`. The bootstrap package regression suite passed. At the end of
this cycle, the blocking network witness and a minimal
`Option<i32>` parameter both returned status 9 in `crustc`. See
[the follow-up](#scalar-option-and-blocking-network-with-crustc) for the fixes.
The network async executable witnesses use the Rust compiler.

The Rust task and region regression suite ran 63 accepted scenarios and
28 refusals. The blocking loopback suite also passed with fatal UBSan
on macOS ARM64. Native Windows execution, fault injection for reactor
errors, and independent adversarial or mutation validation were outside
this cycle.

## Scalar Option and blocking network with crustc

`crustc` now uses its existing scalar Option representation for annotated
parameters, bindings and results. In a value-producing match, an earlier
typed arm supplies the expected type to the fallback literal, and a
function return leaves the match before the join. A shared borrow of a
value record with a destructor keeps cleanup with the owner. These
compiler changes implement N1–N3, N5–N6 and N8 without changing the
language rules.

The focused `Option<i32>` program printed a signed payload, an early
return from the None arm, and the signed 32-bit maximum from the
inferred fallback. It ran unoptimized and with fatal UBSan at `-O2`.
Both compilers refused an incompatible payload, reuse after a move,
and a match missing the None arm.

The shared blocking network witness uses explicit matches for error
propagation. The independent Python peers exercised both compilers
with fatal UBSan at `-O0` and `-O2` on macOS ARM64. Checks covered
address parsing, both TCP backlog forms, accept, connect, empty
slices, EOF, empty and oversized UDP datagrams, sender identity,
and 128 move, drop and rebind sequences. Three private socket
construction cases remained refused. The bootstrap package regression
suite also passed. This run covers the host build of `crustc`.

## Blocking and async File operations

The existing `File.read` API now has a counterpart in
`std::io::asyn::File`. Both variants expose `write`, `stats`, and
`delete`. `open_readwrite` preserves existing data, and `create` opens
a new file exclusively. The `stats` result contains the size in bytes.
The async API uses the existing blocking workers and maps launch failure
to `FileError.LaunchFailed`. No language rules changed.

`validation/check_rust_file_io.py` exercises both APIs using files with
a Unicode path. The witness checks exclusive creation, writes to a
read-only handle, empty writes, byte counts, file size, unchanged contents
after reopening, EOF, deletion, and missing and invalid paths. It moves
the file before closing it. The Python harness also checks that deletion
removed the file from the test directory.

| Environment | Evidence at `-O0` and `-O2` |
| --- | --- |
| macOS ARM64 | Both variants passed with fatal UBSan. `crustc` also built and ran the blocking witness with fatal UBSan. |
| macOS x86-64 | Both variants passed with fatal UBSan. |
| Linux x86-64 in Docker | Both variants passed with fatal UBSan. |
| Windows x86-64 under Wine | Both variants passed. |
| Windows ARM64 | Both variants cross-linked. Native Windows execution remains open. |

The verifier refused an early close and a destination write while a read
was pending. It also refused external construction of the private async
File. The existing macOS ARM64 File and bootstrap package regressions
passed. The host SDK and Linux target headers were used to verify the
`fstat` output layout and the Darwin symbol names. This cycle did not
inject worker launch failures into the file wrappers or run a separate
adversarial audit.

## File open modes and creation permissions

Both APIs use the named `FileMode` access modes and accept
`FilePerm.DefaultMode` or `FilePerm.Perm(mask)` at exclusive creation.
The witness covers append, truncate, read-only handles, invalid mask bits,
exclusive creation, and the descriptor lifecycle.

| Target | Results at `-O0` and `-O2` |
| --- | --- |
| Linux x86-64 in Docker | Sync and async witnesses passed under fatal UBSan. The two policies yielded `0644` and `0600` with a creation mask of `022`. |
| macOS ARM64 and x86-64 | Sync and async witnesses passed under fatal UBSan with the same mode results. The harness installed a file-inheritable read ACE on the test directory. Only the default file inherited it. |
| Windows x86-64 under Wine | Sync and async witnesses passed for default creation and for rejection when Wine substituted the ACL. A separate optimized witness inspected the owner, group, Everyone, access masks and protection flag on the descriptor passed to Win32 for `0600`. |
| Windows ARM64 | Sync and async builds linked. |

Wine reported a different ACL when queried on the actual file. The library
closed the handle and returned `-50` before handing it to the caller.
The rejected path left an empty file. Native Windows ACL persistence and
filesystems beyond the test environments remain unverified.

On macOS ARM64, the synchronous witness also passed under fatal UBSan
when emitted by `crustc`. The bootstrap package regression suite passed.
The `crustc` backend still returned status 9 for a minimal async
`File::open(...).await` program. The same program returned status 9
against the earlier scalar permission API in a temporary std tree.
No independent adversarial audit was run.

## Positional enum fields

`FilePerm` now declares `Perm(u32)`. The Rust-built compiler and `crustc`
accept positional enum declarations, constructions and match patterns in
packages. They resolve imported aliases and reuse enum storage and cleanup.

The two compilers produced the same trace for an imported variant with two
differently typed fields. The trace showed that both arguments were evaluated
left to right and that the pattern bound them in declaration order. Both
refused a missing argument, reversed argument types, a missing pattern
position, and a named pattern on the positional variant.

On macOS ARM64 the Rust-built compiler ran the synchronous and asynchronous
File witnesses under fatal UBSan at `-O0` and `-O2` with the new constructor.
The synchronous File witness emitted by `crustc` also passed at `-O2` under
fatal UBSan. These are results for package entry points.
The `crustc` package regression suite passed. A standalone program emitted
with `crustc --emit-c` also constructed and matched a two-field variant.

## File seek and rename

The synchronous and async facades expose `seek` and `rename`. The seek
witness exercised absolute, current and end-relative positions, a read
after repositioning, negative positions, and a position above 4 GiB with
the file length intact. The rename witness replaced an existing entry,
reopened it under the new name, rejected a missing source and an invalid
destination, then restored the original name.

Both optimization levels passed for synchronous and async files under
fatal UBSan on macOS ARM64, macOS x86-64, and Linux x86-64. The Windows
x86-64 builds passed under Wine and Windows ARM64 linked. The Rust
verifier refused closing a file while a seek was pending and mutating
either path while a rename was pending. Cross-filesystem renames and
native Windows ACL persistence remain untested.

A synchronous package emitted by `crustc` passed the same I/O witness
under fatal UBSan on macOS ARM64. Async parity remains open. An instrumented
`crustc` reported a verifier coverage failure before lowering a package
that awaits `File::open`. A separate package using only an async
`Result<u64, i64>` reproduced status 9 in `crustc` and printed 42 with the
Rust compiler. The Crust verifier's task result encoding and the separate
code generator's task payload encoding both need to carry `Result` types
to support this path.

## Async File parity on macOS ARM64

`crustc` now carries the full ordinary `Result` type through a future,
its handle and its completion. The verifier retains receiver, record
reference and slice loans when building these futures. The C backend
initializes the frame for associated functions and methods. Discarding
a successful completion destroys its owned result payload.

Both compilers ran the same sync and async File program on macOS ARM64.
The `crustc` output passed at `-O0` and at `-O2` with fatal UBSan, including
read, write, stats, seek, rename and delete. Both verifiers refused closing
the file during a pending read or seek, changing the pending read's
destination and changing either pending rename path.

The installed compiler rebuilt its own package with `crustc build`.
Its successor built the external package and passed the same File and
async Result checks in native and fatal UBSan builds.

Strict executable comparison with that successor matched 291 of 295
Rust-accepted programs in both modes. The other four returned their
pre-change statuses on the earlier compiler. They cover two `?` fixtures,
a by-value receiver with a reference field, and an async method returning
a plain scalar while borrowing a receiver and a slice.

The direct await, join and blocking await witness matched the Rust output
for scalar and owned results. The three owned payloads printed their
destructor traces once each. Both compilers refused a boolean in an
integer success arm. Cross-platform runs of this change and worker launch
failure injection remain open. A separate `match` inference limitation
also remains when a branch returns a record and the other uses a bare
`return;` in a void function. It reproduces with an ordinary synchronous
`Result` as well.

## Scalar constants

Both frontends produced the same syntax and static tree for a module
constant and a constant inside `impl`. The package test imported a public
constant and accessed associated constants through an imported type alias.
The Rust frontend and `crustc` produced the expected native and fatal UBSan
traces on macOS ARM64. Both rejected out-of-range and mismatched literals,
duplicate members, a constant and method with the same name, an import of a
private constant, calling or assigning a constant, an implicit conversion
and division by a constant zero.

The package File regression exercised the constants through the existing
`FileMode` methods in sync and async programs. The full AST comparison
stopped when the corpus reader encountered the positional enum nodes in
`stdlib/src/io/file.crust`. The same reader failure reproduced with that
file from the preceding commit. The constant fixture matched directly.

## Blocking TLS 1.3 on macOS ARM64

`std::crypto::tls` wraps an established blocking Din TCP connection and
calls OpenSSL 3 through Darwin ARM64 assembly. Its client takes a PEM
trust file and hostname. Its server takes a PEM chain and private key. The
TLS session holds a non-owning reference to the socket descriptor, while the
Din connection owns both the session and the TCP socket.

With OpenSSL 3.6.3, the native and fatal UBSan runs negotiated TLS 1.3
with Python TLS peers and transferred bytes in both client and server
roles. The client rejected an incorrect hostname, an untrusted certificate
and a TLS 1.2 peer. It observed zero after `close_notify` and a transport
error after the peer dropped its TCP connection. The compiler refused TLS
connection fabrication and direct or aliased access to the TCP descriptor.
The ordinary TCP and UDP witnesses also passed with UBSan at `-O0` and `-O2`.

The self-hosted compiler still refuses the consuming `close` receiver.
This cycle covered macOS ARM64 and used loopback connections. It did not
measure OpenSSL's allocation budget or run an independent audit.

## Native SHA-256

`std::crypto::sha256` implements the message schedule, padding, portable
rounds and output conversion in Din. The assembly kernels receive the
same round schedule and mutate the eight context words. The one-shot
executable on macOS ARM64 linked only libSystem.

Fifteen inputs matched Python's `hashlib.sha256` in one-shot mode, portable
streaming and CPU-selected streaming. The test exercised empty input,
incremental updates and lengths around both padding and block boundaries.
It passed at `-O0` and at `-O2` with fatal UBSan on macOS ARM64, on macOS
x86-64 under Rosetta and on Linux x86-64 in Docker. ARM64 selected SHA
instructions. The x86-64 binaries assembled and linked their SHA-NI
kernels and selected the fallback because neither test environment
exposed SHA-NI. Execution on a SHA-NI CPU remains open.

The Rust verifier refused external construction of the private context
and use of a context moved into `finish`. The self-hosted compiler
reported status 9 for that consuming receiver. This cycle did not
measure throughput or assess side channels.

## SHA-256 with crustc

The self-hosted compiler now uses normal argument-move semantics for
named receivers with fixed scalar-array fields. It carries the element
type and length of compact scalar arrays through function returns and
`Result` payloads. Calls also reserve explicitly borrowed fixed arrays
through the evaluation of their remaining arguments.

The by-value receiver regression mutates a fixed-array field, returns an
array in `Result`, and observes one destructor call. Both compilers
refused a mismatched result shape, receiver reuse and a move during an
active loan. A separate witness transferred a distinct array's byte into
an exclusively borrowed array under fatal UBSan and refused overlapping
arguments. The package regression suite passed on macOS ARM64.

The SHA-256 witness compared 15 inputs against Python's `hashlib.sha256`
in one-shot, portable streaming and CPU-selected streaming modes.
`crustc build` rebuilt the compiler's own package. Its successor selected
ARM64 SHA instructions and passed at `-O0` and at `-O2` under fatal UBSan.
The successor also built and ran a standalone SHA-256 package with
`crustc build`. Its executable matched the digest of `abc` and linked
only libSystem. The compiler rejected use of a context after
`finish()` with violation 6. The Rust-built frontend rejected an
explicit external construction of the context. The same complete
construction exposed a remaining privacy gap in `crustc` and emitted C
successfully there. This follow-up was executed on macOS ARM64 only.

## Private standard-library layouts in crustc

Package linking records the resolved layout declaration and its defining
file's byte range in the linked source. The verifier uses this metadata
when checking field operations and construction. The C backend also
checks it before lowering record and pool initialization. Import aliases
refer to the same layout.

On macOS ARM64, both compilers refused explicit external construction of
`Sha256` with all four fields, including through an alias or a qualified path. They also refused
external field reads, mutable field borrows, and direct default construction
in a pool. A local structure with the same name and fields compiled.

The updated compiler was rebuilt with `crustc build`. Its executable and
the Rust-built frontend matched the same 15 SHA-256 inputs against Python
`hashlib.sha256` in one-shot, portable streaming and CPU-selected streaming
modes at `-O0` and under fatal UBSan at `-O2`. The automatic path selected
ARM64 SHA instructions. These checks exercise the current private
standard-library layouts. The grammar and visibility rules are unchanged.

## Native AES-GCM

`std::crypto::aes` exports `Aes128Gcm` and `Aes256Gcm`. They share fixed-size
key expansion, message bounds and authenticated open in Din. The portable path computes the
AES S-box and polynomial multiplication with fixed field operations.
Both hardware paths accelerate AES and the carryless product in
`@asm`. The Linux ARM64 assembler lowering uses the existing ARM64
operand layout with ELF symbol spelling.

The [NIST CAVP GCM archive](https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Algorithm-Validation-Program/documents/mac/gcmtestvectors.zip)
has SHA-256 `f9fc479e134cde2980b3bb7cddbcb567b2cd96fd753835243ed067699f26a023`.
The default harness takes one case per supported group and verdict, for
150 cases with 96-bit IVs and 128-bit tags. For each key size it covers
25 encryption cases, 25 accepted decryptions and 25 rejected decryptions.
Every accepted vector also exercises a corrupted tag. Each rejection
checks the error variant and compares the entire destination with its
sentinel. Separate length-error checks cover both seal and open.

| Target and compiler | Executed coverage |
| --- | --- |
| macOS ARM64, Rust-built frontend and self-hosted `crustc` | Hardware AES and PMULL plus forced portable at `-O0` and `-O2` with fatal UBSan. Both private key layouts rejected external construction. Both compilers repeated the 150-case suite after the package moved to `std::crypto::aes`. |
| macOS x86-64, Rust-built frontend under Rosetta | AES-NI and PCLMULQDQ plus forced portable at `-O0` and `-O2` with fatal UBSan. |
| Linux ARM64 and x86-64, Rust-built frontend and local containers | Hardware dispatch selected on both architectures. Automatic and forced portable runs passed at `-O0` and `-O2` with fatal UBSan. |
| Windows ARM64 and x86-64 | The emitted assembly assembled to COFF objects. Linking and execution remain open. |

The macOS ARM64 SHA-256 regression also passed, and the AES-GCM probe
built through `crustc` linked only libSystem. The vectors cover
correctness and rejection for the tested messages. They do not measure
side channels or execute buffers near the GCM length limits.

The Rust unit tests passed. The separate Linux x86-64 assembly regression
stopped at the strict GCC warning for a missing return in the generated
`crust_socket_worker` stub. The same package and C flags reproduced that
failure with the pre-change compiler.

## Native HMAC-SHA-256 and HKDF-SHA-256

The new operations are exported from `std::crypto::sha256`. HMAC reuses
the incremental SHA-256 context and feeds its message fragments without
concatenation. HKDF Expand derives directly into the caller's slice and
checks the PRK and output bounds before writing.

The Rust-built frontend and self-hosted `crustc` passed all seven
[HMAC-SHA-256 cases](https://www.rfc-editor.org/rfc/rfc4231.html#section-4)
and the three [HKDF-SHA-256 cases](https://www.rfc-editor.org/rfc/rfc5869.html#appendix-A)
on macOS ARM64 at `-O0` and under fatal UBSan at `-O2`. HMAC case 5
checks the published 16-byte prefix of the full tag. HKDF checks both
the extracted PRK and expanded output. A separate Python HMAC oracle
also checks that a 64-byte PRK works for lengths 0, 31, 32, 33, and
8,160. A 31-byte PRK and an 8,161-byte output produce distinct errors
and preserve all destination bytes.

This cycle covers functional behavior and checked output bounds. The
generated code's timing behavior and inputs near the SHA-256 byte-count
limit remain unmeasured.

## Native SHA-384 and SHA-512

`std::crypto::sha512` shares one update, compression, padding, and
digest serialization path between SHA-384 and SHA-512. The two opaque
contexts choose independent initial words and different digest lengths.
Each update checks the two-limb byte count before it changes the hash
state. Compression uses explicit modulo-2^64 addition within Din's
checked arithmetic.

The [NIST byte-oriented SHA archive](https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Algorithm-Validation-Program/documents/shs/shabytetestvectors.zip)
has SHA-256 `929ef80b7b3418aca026643f6f248815913b60e01741a44bba9e118067f4c9b8`.
The Rust-built frontend and self-hosted `crustc` matched all 514 short
and long message records and 12 additional block and padding cases
on macOS ARM64 at `-O0` and under fatal UBSan at `-O2`. Every message
was hashed one-shot and with 73-byte streaming updates. Python
`hashlib` independently matched all NIST outputs.

Both compilers refused external access to the two private layouts and
reuse after a consuming finish. A test-only seeded state confirmed the
counter's carry into the high limb and rejection without mutating either
limb, the buffered block or the digest state. SHA-256 and HMAC/HKDF regressions also
passed with the Rust-built frontend. The NIST Monte Carlo files were
outside this run.

## Native HMAC-SHA-384 and HKDF-SHA-384

`std::crypto::sha384` exposes the SHA-256 API shape over the existing
incremental SHA-384 implementation. HMAC uses SHA-384's 128-byte block
and returns 48 bytes. HKDF Extract returns a 48-byte PRK. Expand
accepts a PRK of at least 48 bytes and writes at most 255 blocks directly
to the caller's slice.

Both compilers passed all seven [RFC 4231 HMAC-SHA-384 cases](https://www.rfc-editor.org/rfc/rfc4231.html#section-4),
including the 16-byte prefix in case 5. They passed all 83 cases of the
[pinned Wycheproof HKDF-SHA-384 corpus](https://github.com/C2SP/wycheproof/blob/b61843a9a5115bb758134b6a1f5d5e502d445342/testvectors_v1/hkdf_sha384_test.json),
SHA-256 digest `69ff6ea3657bb9c1b8cdffbbb4e7832353d08fd15c0d9997b03f7a6b180e3678`.
The suite exercised 80 valid cases and three 12,241-byte outputs that
were rejected with every sentinel byte preserved. A 47-byte PRK was
also refused without changing the output. An independent Python
HMAC oracle checked the extracted keys and Expand lengths 0, 47, 48,
49, and 12,240 with a 129-byte PRK.

These runs used macOS ARM64 at `-O0` and under fatal UBSan at `-O2`,
including self-hosted `crustc`. The SHA-256 HMAC/HKDF suite also passed
with both compilers after sharing the test runner. Timing behavior
remains unmeasured.

## Native SHA-3

`std::crypto::sha3` uses a single Keccak-f[1600] permutation, byte
absorption, FIPS 202 padding, and digest serialization path for
SHA3-224, SHA3-256, SHA3-384, and SHA3-512. Each private context records
its lanes and position within the current absorption block. The output
is a fixed byte array, and calling `finish()` consumes the context.
[FIPS 202](https://csrc.nist.gov/pubs/fips/202/final)

The [NIST byte-oriented SHA-3 archive](https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Algorithm-Validation-Program/documents/sha3/sha-3bytetestvectors.zip)
has SHA-256 digest
`cd07701af2e47f5cc889d642528b4bf11f8b6eb55797c7307a96828ed8d8fc8c`.
On macOS ARM64 with Apple Clang 17, the Rust-built frontend and rebuilt
self-hosted `crustc` matched the full digest for all 860 short and long
messages and 24 additional absorption-boundary cases at `-O0` and under
fatal UBSan at `-O2`. Every one of those messages was exercised one-shot
and with streaming updates of up to 31 bytes, including an empty update.
Python `hashlib` independently matched the short, long, and boundary
digests. Both compilers also matched all 400 Monte Carlo checkpoints
after running the four 100,000-hash chains.
[NIST SHA3VS](https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Algorithm-Validation-Program/documents/sha3/sha3vs.pdf)

Both compilers refused external access to the private state, including
through an import alias, and use after `finish()` for all four contexts.
The SHA-384 and SHA-512 regression suite passed with both compilers
after sharing the vector reader. The harness writes the next Monte Carlo
digest into its fixed buffer byte by byte because whole-array
reassignment is outside the verified compiler subset. The evidence
covers byte-aligned messages on macOS ARM64. Timing and other targets
remain unmeasured, and no independent audit was run.

## Native SHAKE128 and SHAKE256

Both one-shot functions write exactly the number of bytes in the
caller's mutable slice. A zero-length slice is valid and leaves its
backing storage untouched. The four fixed-length SHA-3 functions and
both SHAKE functions share absorption, Keccak-f[1600], padding, and
byte extraction. The SHAKE domain suffix is `0x1f`, with rates of 168
bytes for SHAKE128 and 136 bytes for SHAKE256. Once an output block is
exhausted, another permutation produces the next block.
[FIPS 202](https://csrc.nist.gov/pubs/fips/202/final)

The [NIST byte-oriented SHAKE archive](https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Algorithm-Validation-Program/documents/sha3/shakebytetestvectors.zip)
has SHA-256 digest
`debfebc3157b3ceea002b84ca38476420389a3bf7e97dc5f53ea4689a16de4c7`.
The Rust-built frontend and self-hosted `crustc` matched all 3,182
short, long, and variable-output samples and all 200 Monte Carlo
checkpoints across the two 100,000-iteration chains. Both compilers
matched 128 additional combinations of input and output lengths at and
around absorption and output block boundaries, including empty slices.
The harness checked sentinels on both sides of each output slice in the
message and boundary cases. Python `hashlib` independently matched the
short, long, variable-output, and boundary samples.

Both compilers refused a shared output and overlapping input and output.
`crustc` returned exit status 9 without a diagnostic for the overlapping
borrow. The full SHA-3 suite also passed with the shared output path.
Execution evidence covers byte-aligned input and output on macOS ARM64
with Apple Clang 17 at `-O0` and with fatal UBSan at `-O2`.
Timing and other targets were outside this run.

## Native Argon2id

`std::crypto::argon2id` implements Argon2id v1.3 in Din with private
BLAKE2b and Argon2 compression functions. The public entry point
uses the caller's contiguous mutable block slice for memory and its
mutable byte slice for the tag. The optional secret and associated
data are empty in the public API. The RFC fixture calls the same
derivation with the specified values for those fields.
[RFC 9106](https://www.rfc-editor.org/rfc/rfc9106.html#section-5.3) ·
[RFC 7693](https://www.rfc-editor.org/rfc/rfc7693.html)

The Rust frontend and self-hosted `crustc` passed on macOS ARM64 at
`-O0` and with fatal UBSan at `-O2`:

- The full tag from the RFC 9106 Argon2id example with 32 KiB,
  three passes and four lanes.
- The 32-byte tag for three passes and four lanes with a 64 MiB local
  region, using 65,536 initialized vector blocks of 1 KiB each.
  The tag was read after the region's scope ended.
- The 73-byte tag at 33 KiB with three passes and four lanes. The
  implementation uses 32 blocks and includes the requested 33 in
  the initial hash.

OpenSSL 3.6.3 independently produced the 64 MiB and 33 KiB reference
tags. The tests read every word on return. All used blocks were zero,
and the one unused block in the 33 KiB case kept its sentinel. Both
compilers rejected growing or dropping a vector while its mutable
view was live. A push after filling a one-block region failed with
the region limit diagnostic.

The region and region-collection regression suites passed with the
Rust frontend. The SHAKE byte-vector suite passed with the rebuilt
`crustc` after the slice changes.

The self-hosted compiler path supports whole-vector views of nonempty
inline scalar arrays. This cycle uses the regional vector through an
allocation obtained from a local pool. Execution covered macOS ARM64.
General runtime overhead, side-channel behavior, and clearing of
temporary data outside the supplied work slice were outside this run.

## System randomness

The public package adds `std::crypto::random::fill` with a caller-owned
mutable slice and a fallible result. The platform files invoke
`getrandom` with flags zero on Linux, `getentropy` on macOS, and
`BCryptGenRandom` with the system-preferred RNG on Windows through
`@asm`. The wrapper requests at most 256 bytes per call, retries Unix
interruptions, and advances only by the count returned on success.
A later error may leave a partially filled slice.

The live witness requested 513 bytes inside a larger buffer, checked
both adjacent sentinel bytes, and observed different outputs on two
fills. The deterministic backend witnessed retry, short reads,
completion without a call for an empty slice, preservation of the
OS error code after a partial write, and rejection of zero and
oversized successful counts. The compilers also refused a shared
destination slice.

| Target | Executed evidence |
| --- | --- |
| macOS ARM64 | Rust frontend and self-hosted `crustc` passed the live and deterministic witnesses at `-O0` and under fatal UBSan at `-O2`. |
| macOS x86-64 | Rust frontend passed the same witnesses under Rosetta, including fatal UBSan. |
| Linux ARM64 and x86-64 | Rust frontend passed the same witnesses in local containers, including fatal UBSan. |
| Windows x86-64 | Rust frontend linked against BCrypt. Both witnesses passed under Wine at `-O0` and `-O2`. |
| Windows ARM64 | Rust frontend linked both live witness builds against BCrypt. Execution remains open. |

The runtime samples exercise delivery and buffer boundaries. They
provide no measurement of the OS generators' entropy. Native Windows
execution remains open. The unmodified `crustc` bootstrap ran the
package on macOS ARM64. Temporary x86-64 bootstrap builds also passed a
513-byte package smoke test on Linux under UBSan and the standalone
buffer witness on Windows under Wine. These builds used a checked-value
assignment in place of an existing regional-vector field borrow that
the Rust frontend refused. The Linux build also preselected the
package loader's nested target conditionals and used a 1 GiB fixed
datastack reservation for the compiler process in the container.
The temporary bootstrap changes are outside the delivered implementation.
The standard Linux ARM64 bootstrap lacks its character output function.

## Native P-256

`std::crypto::p256` shares fixed-width Montgomery arithmetic and
Jacobian point operations between ephemeral agreement and signing.
It samples private keys with rejection sampling over OS-generated
bytes. Signing derives nonces with HMAC-SHA-256 per RFC 6979.

The two compilers emitted executables on macOS ARM64. With each
compiler, the same 28 runtime checks passed at `-O0` and under fatal
UBSan at `-O2`:

- [RFC 5903 §8.1](https://www.rfc-editor.org/rfc/rfc5903.html#section-8.1)
  matched both SEC1 public keys and the 32-byte shared secret in
  both agreement directions. The harness injected the fixed scalars
  through a private function in a test copy of the Din module.
- [RFC 6979 Appendix A.2.5](https://datatracker.ietf.org/doc/html/rfc6979#appendix-A.2.5)
  matched the SHA-256 signatures for `sample` and `test` byte for
  byte in DER. Verification accepted both signatures with the
  published key and returned false for the wrong message. The
  71-byte signature preserved the last byte of its 72-byte output.
- Eight SEC1 cases covered infinity, compressed and hybrid encodings,
  incorrect length, off-curve points, and each coordinate equal to the
  modulus. Two scalar imports covered zero and the group order.
  Eleven DER cases covered framing, negative and nonminimal integers,
  zero values, and each signature scalar equal to the order.
- OS-generated ephemeral keys agreed on the same bytes, and an
  OS-generated signing key signed and verified an empty message.

Both compilers rejected direct construction and default pool
construction of `EphemeralKey`, `SigningKey`, and `PublicKey`
from the calling package. Verification used `validation/check_p256.py`
and a self-hosted `crustc` build with the P-256 layout restrictions.
The existing Rust and `crustc` package suites also passed, including
import visibility, standard library loading, and path and Git
dependencies.

These results cover functional behavior on macOS ARM64. They provide
no constant-time or erasure guarantee. Byte serialization includes
source-level conditionals, and the generated instructions and timings
were outside this cycle. Cross-platform execution and independent
cryptographic review remain open.

## Native TLS 1.3 key derivation

`std::crypto::tls13::keys` adds the SHA-256 transcript, HKDF-Expand-Label,
and the initial full-handshake schedule. SHA-256 can snapshot an active
hash. The native module links without OpenSSL.

The Rust frontend and self-hosted `crustc` both passed 50 checks on
macOS ARM64 at `-O0` and under fatal UBSan at `-O2`.

- The exact serialized handshake messages and published checkpoints
  come from [RFC 8448 §3](https://www.rfc-editor.org/rfc/rfc8448.html#section-3).
  The replay supplies the trace's shared secret as input. The test
  exercises the schedule independently of the curve that produced it.
- The transcript is read at multiple stages and continues across
  snapshots and fragments. The hash immediately before the server
  Finished is independently calculated with Python SHA-256.
- The trace matches the early, derived, handshake, and master secrets,
  both directions of the handshake and application traffic secrets,
  their four key/IV pairs, both Finished keys and verification values,
  and the exporter and resumption checkpoints. A resumption label
  expansion also matches the trace's ticket PSK.
- A changed first or last Finished byte and a truncated value are
  rejected. Expand-Label accepts a 249-byte label and a 255-byte
  context. Zero, 256, and 8160 output bytes match the independent
  Python HKDF oracle. Empty or oversized labels, oversized contexts,
  short secrets, and oversized output leave sentinel buffers intact.

The SHA-256 regression suite passed with both compilers. The existing
OpenSSL-backed TLS client and server passed their native and UBSan
loopback tests with the Rust frontend.

The witness uses published key-schedule inputs and exercises no TCP
record handling, certificate validation, PSK negotiation, or handshake
state machine. Finished comparison accumulates differences across all
32 bytes in Din. Timing of the generated code and secret erasure
remain unverified.

## Native TLS 1.3 record layer

`std::crypto::tls13::record` implements cleartext framing and
AES-128-GCM record protection with caller-owned buffers. Separate reader
and writer instances own the directional counters. The writer uses a
conservative `2^24` record limit per key.

The Rust frontend and self-hosted `crustc` each passed 68 in-memory
checks on macOS ARM64 at `-O0` and under fatal UBSan at `-O2`.
They reproduced and parsed the nine selected [RFC 8448 §3](https://www.rfc-editor.org/rfc/rfc8448.html#section-3)
records byte for byte: both hellos, the server handshake flight, the
client Finished, the server ticket, both application records, and both
`close_notify` alerts. The server ticket advances the server's
application sequence before its first application record. The client
direction has its own sequence.

The same compiler and optimization combinations passed loopback
tests with fragmented input. A test copy capped individual TCP reads
at two bytes and writes at three bytes to force both retry loops.
The witnesses checked EOF before any alert and in the middle of the
header and ciphertext. The sender refused an oversized header before
writing. In-memory cases also exercised the full 16 KiB content size,
zero-length application data, padding around content ending with zero,
retry after an undersized caller buffer, and authentication failure
with an unchanged plaintext buffer.

The record-cipher layout is private. Both compilers rejected attempts
to take a mutable reference to its nonce counter. The original
self-host parser token capacity was exceeded when scanning the full
compiler package and bundled standard library. The package scanner
now reserves a larger token buffer and reports capacity exhaustion
before accessing a token outside that buffer. Self-hosted
`crustc build` rebuilt the compiler with the full standard library.
The existing RFC 8448 key schedule suite also passed with both compilers.

This cycle covers the AES-128-GCM record layer on macOS ARM64. The
handshake still owns record-type sequencing, traffic-key changes,
certificate authentication, and fatal-alert teardown of both
directions. Timing, erasure, and other platform executions remain open.

## Native TLS 1.3 handshake

`std::crypto::tls13::handshake` adds the blocking client and server
paths for `secp256r1`, `ecdsa_secp256r1_sha256`, and
`TLS_AES_128_GCM_SHA256`. It uses the existing transcript, record
layer, randomness, and P-256 primitives. The bounded handshake-message
buffer assembles fragments across records. A cursor retains additional
handshake messages carried in the same record.

The Rust frontend and the rebuilt self-hosted `crustc` each passed
the following on macOS ARM64 at `-O0` and under fatal UBSan at `-O2`:

- Din client to OpenSSL 3.6.3 through Python's SSL socket API. The
  peer used a generated P-256 certificate and disabled tickets. The
  witness exchanged PING and PONG and verified an authenticated close.
- OpenSSL 3.6.3 `s_client` to Din server. The peer constrained the
  suite, group, and signature algorithm and verified the fixture
  certificate and the hostname. The witness exchanged PING and PONG
  and sent an authenticated closure from Din.
- The Din server rejected a cleartext Finished sent in place of
  ClientHello. The Din client rejected a changed certificate pin and
  independently rejected a valid certificate with a different provisioned
  public key. Both compilers refused external access to the session's
  record state.

Validation used `validation/check_tls13_handshake.py`. OpenSSL was
used only as the independent test peer and to generate test identities.
The Din witness binaries linked without OpenSSL. Both compilers also
passed the existing key-schedule and record witnesses. The rebuilt
`crustc` passed the fragmented TCP record regression as well.

The protocol profile uses a single preprovisioned certificate and key.
PKIX validation, SNI, client authentication, HelloRetryRequest,
resumption, KeyUpdate, and fatal-alert mapping are open. After an error,
the caller must close the TCP connection. Executable evidence covers
macOS ARM64, and the cycle does not establish timing or erasure guarantees.

## Native X.509 path and DNS verification

`std::crypto::x509` validates a leaf-first P-256/ECDSA-SHA-256 path
against an explicit DER CA certificate and caller-provided Unix time.
The leaf key is returned only after certificate path and DNS SAN
verification. TLS uses that key for `CertificateVerify` and sends the
reference DNS name in SNI. The server can send the leaf and intermediates
through `server_handshake_chain`.

The Rust frontend and self-hosted `crustc` each passed the same
24 certificate and hostname checks on macOS ARM64 at `-O0` and under
fatal UBSan at `-O2`. The fixtures came from OpenSSL 3.6.3, which also
independently verified the main root/intermediate/leaf path. Cases
covered:

- The ordered path, an optional copy of the anchor in the chain, UTC
  and generalized validity dates, and case-insensitive DNS SAN matching.
- A single-label wildcard, rejection of a multi-label match or bare
  suffix, a mismatched name, and a certificate using only Common Name.
- Expired and not-yet-valid certificates, a wrong root with the correct
  distinguished name, a missing intermediate, a damaged signature, and
  incorrect chain ordering.
- Basic Constraints and path length, missing signing permissions, EKU
  policy, unknown critical extensions, unsupported Name Constraints,
  truncated TLS certificate entries, trailing DER bytes, and IP literals.

The TLS tests exchange encrypted application data in both roles against
OpenSSL 3.6.3. The Din client checks the presented intermediate and leaf
against the root and the OpenSSL server observes the requested SNI.
The Din server presents its intermediate and leaf to `openssl s_client`,
which verifies the path and hostname. The client rejects the wrong
hostname, untrusted anchor, and expired leaf on the wire.
The rebuilt `crustc` also passed the previous pinned-certificate TLS
suite at both optimization levels, including the session privacy check.

This is an ordered path validator for the current ECDSA profile.
Alternative path building, operating system trust stores, IP SAN
matching, revocation, and additional PKIX algorithms and policy
constraints remain open. The cycle provides no new timing evidence.

## TLS module and certificate types

The native TLS API moved to `std::net::tls`, with record and key
operations in submodules. The OpenSSL-backed API is available under
`std::net::tls::openssl`. Both AES types now use the public names
`AES128GCM` and `AES256GCM`.

`tls::Certificate` decodes the handshake envelope and exposes its
request context, DER ranges, and entry extension ranges. The X.509
standalone validator takes concatenated DER. TLS passes the DER
ranges from its own message parser directly to the path validator.
`x509::Certificate` owns parsed metadata and an encoded key. Operations
that need the caller's backing DER check its SHA-256 fingerprint.
`x509::PublicKey` exposes the ECDSA verification used by CertificateVerify.

The Rust frontend and rebuilt self-hosted `crustc` passed the new typed
certificate tests at `-O0` and fatal UBSan at `-O2` on macOS ARM64.
The tests checked TLS context and extension ranges, truncated messages,
issuer verification, DNS matching, incorrect backing DER, and signature
verification with the extracted key. Both compilers refused external
access to the three new types' layouts.

The 24 X.509 cases, 50 RFC 8448 key schedule checks, 68 record checks,
and 150 NIST AES-GCM vectors passed with both compilers. AES vectors
ran through automatic hardware selection and the portable backend.
Native TLS interoperation with OpenSSL passed in both roles with both
compilers. The renamed OpenSSL backend passed its client, server, and
privacy checks with the Rust frontend. The Rust package loader regression
suite passed.

## Caller-owned encoding and PEM

Hex and Base64 write into caller-owned slices and preserve the output on
invalid input or insufficient capacity. Base64 checks canonical pad bits.
Its wrapped decoder is used for PEM, which requires one labelled block.
P-256 key import covers unencrypted PKCS#8, traditional SEC1 and SPKI.
X.509 certificate import decodes PEM and calls the existing DER parser.
The P-256 and X.509 modules share DER framing and SPKI parsing.

The Rust frontend and rebuilt `crustc` passed `check_encoding_pem.py` on
macOS ARM64 at `-O0` and with fatal UBSan at `-O2`. Comparisons used
Python's Hex and Base64 codecs and key and certificate fixtures made
with OpenSSL. Malformed encodings and insufficient buffers were checked
with sentinels. DER/PEM imports agreed on the public point and exercised
signature verification, DNS matching, and both CRLF and CR line endings.
Rejected inputs included an encrypted key, wrong curve, wrong envelope
label, multiple blocks, an inconsistent embedded public key, trailing
DER bytes, and an expired certificate.

The package regression suites passed after `crustc` was fixed to resolve
module members of grouped imports. Both compilers also passed the P-256
SEC1 and RFC 5903 regressions and layout privacy checks. The validation
here covers macOS ARM64. The caller's scratch slice retains the decoded
DER and can contain private key material. Encrypted keys, other curves,
and multiple PEM blocks in one input are outside the supported profile.

The X.509 regression suite also passed 24 certificate and hostname
cases with each compiler. The PEM witness verified that `der_len()`
exposes the exact decoded prefix and used it for DNS verification.
Both TLS roles interoperated with OpenSSL 3.6.3 over loopback at `-O0`
and with fatal UBSan at `-O2` for each compiler, including SNI and
rejection of an incorrect hostname, an untrusted root and an expired
leaf.

## Standard library documentation

The standard library sources gained `//!` file summaries and `///`
declaration documentation. `python3 scripts/stdlib_docs.py --check`
verified the headers and comments for 802 declarations across 67 files
and confirmed that `docs/STDLIB.md` matches the generator output. The
reference uses source links and shows the target conditions of the
documented public API. The generator checks internal declarations as
well and leaves the `std::sys` backends out of the public reference.
Each generated source link was checked against its declaration line.
A temporary source file with an undocumented function was rejected.

After removing the added comments and the header separator, all 67
`.crust` files matched the preceding revision byte for byte. On macOS
ARM64, `check_rust_packages.py` and `check_crust_packages.py` passed.
`check_encoding_pem.py` passed at `-O0` and under fatal UBSan at `-O2`
with both compilers. This cycle did not change the language rules or
extend platform execution coverage.

## MD5, PBKDF2 and key serialization

The standard library added streaming and one-shot MD5 for legacy
checksums and PBKDF2-HMAC-SHA-256 for interoperability. The runtime
witnesses matched seven MD5 RFC 1321 vectors with nine additional
padding and block boundary inputs. The PBKDF2 comparisons used the
64-byte RFC 7914 vector and Python `hashlib`. The cases exercised
repeated rounds, empty and binary inputs, a long HMAC key, partial
output blocks, and the counter carry past block 255. Zero iterations
and empty output were refused. Both frontends refused external
construction of the opaque MD5 state.

The same witnesses produced DER and PEM byte-for-byte identical to
OpenSSL 3.6.3 for P-256 PKCS#8 and SEC1 private keys, SPKI public keys,
and an existing X.509 certificate. Short outputs, an invalid PEM label
and substituted certificate bytes returned errors with the sentinel
buffer intact. A package importing only `SigningKey` generated and
reparsed PKCS#8 DER. Its associated methods are in the same source file
as the key type so `crustc` loads them with that import.

`check_crypto_serialization.py` and the previous `check_encoding_pem.py`
passed with both compilers at `-O0` and with fatal UBSan at `-O2` on
macOS ARM64. The existing P-256 and X.509 suites passed with both
compilers at the same optimization levels. The bootstrap package source
budget grew from 2 MiB to 3 MiB to fit the compiler and the documented
standard library. `crustc` rebuilt its own package with that library and
the rebuilt binary passed `check_crypto_serialization.py`. RSA keys,
encrypted private key containers and certificate issuance remain open.

## RSA and password-protected PKCS#8

The RSA codecs import two-prime PKCS#1, SPKI public keys and unencrypted
PKCS#8 private keys. Exports preserve the canonical PKCS#1 bytes and
produce the appropriate DER or PEM container using caller-owned storage.
The PKCS#8 protection API uses PBES2, PBKDF2-HMAC-SHA-256, a fresh salt
and IV, and AES-256-CBC with PKCS#7 padding. Decryption checks a
caller-supplied iteration limit before running the KDF.

On macOS ARM64 the Rust frontend and self-hosted `crustc` passed
`check_rsa_pkcs8.py` at `-O0` and under fatal UBSan at `-O2`. RSA-2048
and RSA-4096 DER and PEM outputs matched the OpenSSL 3.6.3 fixtures.
Din decrypted the RSA and P-256 fixtures produced by OpenSSL. OpenSSL
recovered the original keys from the DER and PEM written by Din.
Separate CBC comparisons against OpenSSL exercised empty input, full
padding blocks and partial blocks. Both compilers also passed the
prior MD5, PBKDF2 and P-256/X.509 serialization suite and 150 NIST
AES-GCM vectors in the automatically selected and portable paths.

The negative cases exercised mismatched labels, trailing key data,
the wrong key kind, short buffers, an unsupported PRF, an iteration
count over the caller's ceiling, a wrong password and an altered IV.
The altered IV preserved valid padding while corrupting the decrypted
DER. Both password and DER failures cleared the written output region
and preserved the sentinel beyond it. The RSA codec validates structure.
RSA arithmetic, encrypted-key profiles beyond this combination, and
side-channel and secret-erasure analysis remain open.

## Linux and Windows crypto stack

| Executed target | Rust frontend | Self-hosted `crustc` | OpenSSL interoperability |
| --- | --- | --- | --- |
| Linux x86-64 in a Debian Bookworm container | 17/17 | 17/17 | Din client and server, OpenSSL 3.0.22 |
| Windows x86-64 PE binaries under Wine 11.21 on macOS ARM64 | 17/17 | 17/17 | Din client and server, host OpenSSL 4.0.3 CLI and Python SSL linked to OpenSSL 3.6.3 |

The suites cover system randomness, SHA-256, SHA-384/512, SHA-3,
SHAKE128/256, MD5, HMAC, HKDF, PBKDF2, Argon2id, AES-GCM, AES-CBC,
P-256, encodings, DER/PEM and encrypted PKCS#8, the TLS 1.3 key
schedule and record layer, both handshake roles, and X.509 path and DNS
verification. They ran at `-O0` and with each suite's optimized checks.
Where configured, those checks used fatal UBSan on Linux and UBSan
instrumentation in trap mode on Windows. This includes the TLS suites.

On each target and with each compiler, the AES suite matched 150 NIST
vectors through the portable and CPU-selected implementations. Invalid
tags and sizes left caller buffers intact. The RFC 8448 key and record
checks passed, including partial TCP transfers and authenticated closure.
Both TLS roles exchanged application data with OpenSSL. Rejection cases
covered out-of-sequence Finished, incorrect pins or verification keys,
wrong DNS names, untrusted anchors and expired leaf certificates.
SHA-256 used the portable fallback in both environments.

The bootstrap now enumerates and canonicalizes Windows x86-64 package
paths using the wide Win32 APIs. A Windows binary compiled a package in
a Unicode directory with the bundled standard library. The cycle also
fixed the Linux x86-64 package loader's target branches, reserved the
compiler's fixed datastack budget on Linux and Windows, and enabled
private-layout diagnostic text on both targets. The macOS ARM64
self-hosted package regression suite passed after the loader changes.

Both compilers now complete SHA-384/512, SHA-3 and SHAKE with the
standard Windows file API. See the follow-up below for the file
borrow regression and the fixture checks.

The [crypto validation runner](../../validation/check_crypto_stack.py)
records one result per suite. Native Windows, full Linux and Windows
ARM64 runs, x86-64 SHA-NI execution, and independent side-channel and
secret-erasure analysis remain open.

### Windows File borrows in crustc

The self-hosted verifier previously returned status 9 for an
`&mut File` parameter because its record check excludes `usize`
fields. The Windows backend now stores the opaque Win64 HANDLE as a
`u64`. Its private helpers pass borrowed path and ACL buffers as
slices. The assembly uses ABI-sized output slots for token handles and
Win32 read and write counts. The public `File` API and ownership rules
are unchanged.

Under Wine 11.21, the Windows x86-64 `crustc` passed SHA-384/512,
SHA-3, and SHAKE with the standard API at `-O0` and `-O2` with UBSan
traps. The suites checked 514 SHA-384/512 vectors, 860 SHA-3 messages
and 400 Monte Carlo checkpoints, and 3,182 SHAKE vectors and 200 Monte
Carlo checkpoints, plus their boundary and refusal cases. The test-only
fixture transport was removed.

The existing synchronous file lifecycle witness returned 42 when
compiled by Windows `crustc` at `-O2` with UBSan traps. It exercised
creation, explicit permission rejection on the Wine volume, reading,
writing, seeking, renaming and cleanup after a move. A separate witness
was rejected under rule 5 when it dropped the file before its mutable
borrow's last use. The Rust frontend passed the existing synchronous
and asynchronous File regression at both optimization levels under Wine.
The Windows ARM64 witness compiled and linked with the Rust frontend.
Execution on native Windows and on Windows ARM64 remains open.

## Iter, Map and collect

Both compilers resolve the source's `next(&mut self) -> Option<V>` and each
mapper's signature statically. `Iter` borrows the source in `&mut`. Each
`Map` consumes its predecessor and calls its mapper only when the predecessor
yields `Some`. `collect(&mut destination)` consumes the chain and appends to
the caller's vector using the existing regional capacity check.

The Rust frontend represents each stage as an aggregate. The self-hosted
compiler lowers the state of the captureless chain to its source reference and
generates statically typed functions to advance each stage. The ordinary
verifier checks the resulting moves and loans. A scalar regional vector's
whole slice reserves its storage against growth while the slice remains live.

[check_rust_pipelines.py](../../validation/check_rust_pipelines.py) compared the
two compilers on eight accepted source files, seven refusals and one region
exhaustion case. Generated executables ran under fatal UBSan at `-O0` and
`-O2` on macOS ARM64. The package alias case ran with both build commands and
with `crustc --emit-package-c` under UBSan. The compiler emitted its own package,
the generated C linked into a second compiler, and that compiler passed the
same pipeline suite. Fourteen pipeline ASTs matched before specialization. The Rust frontend unit tests, regional suite and crustc package
suite passed. The broader parser comparison halted because its kind table
does not list the Rust parser's positional field kind.

### Generic items and raw address confinement

The Rust frontend now checks the type of a pipeline item with the same
admissibility check as `Option<T>`. It applies the source and mapper
contracts when advancing a stage. A returned borrow retains its origin
through the mapper. A subsequent `next()` conflicts with that loan while
it is live. Collection attaches the item's dependencies to the vector
and rejects retaining a borrow of source storage across another advance.

The self-hosted compiler now specializes the chain for additional scalar
vector types, flat fixed arrays and supported nominal values. It uses the
ordinary verifier for the generated calls and moves. The two compilers
agreed on 24 successful programs, seven refusals, and the regional limit
failure. The successful programs cover every primitive scalar, mapped
records, enums and flat fixed arrays. The `Option<Item>` cleanup witness ran the destructor once for each mapped item. The
witness exercises explicit `drop` and scope exit.

At this stage, the self-hosted compiler supported the scalar and aggregate
cases above. The dependency-carrying cases are recorded in the follow-up
below. The Rust frontend requires a known vector binding when collection
carries dependencies or needs ownership adoption.

Both compilers now check that raw addresses created with `addr()` stay
within their `@unchecked` block. The targeted regression includes
assignment outside the block, return, copy followed by a cast and
aggregate wrapping, and passing the address to a function with a mutable
output. The standard library and the self-hosted compiler's system
helpers take addresses in the blocks that use them. OpenSSL wrappers
receive typed slices, and IOCP calculates the request address in its
system wrapper. The Windows socket request writes its opaque pointer
through assembly and the requesting operation retains the buffer.

On macOS ARM64 the File suite passed for both sync and async operations
under fatal UBSan at `-O0` and `-O2` using the Rust frontend. SHA-256
matched 15 vectors in three modes with the hardware path active using
both compilers, with native and UBSan executions. The Rust frontend
checked the migrated standard library and emitted C for representative
Linux and Windows packages on x86-64 and ARM64. Execution of the migrated
Windows and Linux backends remains unverified in this cycle.

### Pipeline payloads with dependencies

Both compilers now execute the shared and exclusive scalar reference
cases and a reference to a record field. Moving the `Option` retains the
referent and the reservation on the pipeline. A second `next()` is
rejected while an earlier loan is used later. An `Option` pointing into
the callee's local storage and reuse of a moved `Option` are rejected.

For the pooled collection witness, the source holds an explicit
`&mut Pool<i64>` and yields allocations from that pool. The mapper moves
each allocation into the destination vector. An indexed read observes
the second value. Destruction of the destination returns both slots to
their original pool. Both slots are acquired again in the same execution.
Both compilers reject destroying the source pool while the vector still
holds either allocation. A separate witness exercises moving an
`Option<A<i64>>` through an ordinary call, matching it, and reusing its slot.

A mapper can start a native worker using the reference yielded by the source.
The returned handle retains that reservation through `Option` and until
`join()`. A mutable capture updates the caller's value, and a read
before joining that worker is rejected. Both compilers reject a second
advance before the wait and abandoning the handle. A separate collection
witness drains autonomous handles after collecting them in a vector.

The paired pipeline witnesses cover 32 successful programs, 15 rejected programs,
and one regional capacity failure on macOS ARM64. Successful programs ran
under fatal UBSan at `-O0` and `-O2`. The `crustc` binary built by the Rust
frontend passed the pipeline and package suites. A second-generation
binary built from C emitted by `crustc` passed the same pipeline suite.
The targeted cases exercise a single symbolic source for borrowed
results and a record with one stored scalar pool for collected
allocations. Slices, nested dependency envelopes,
collection of references whose independence from the source must be
proven, nominal pool payloads, and async handle compositions remain open
in the self-hosted compiler at that point. The mapper specialization
required a literal closure without captures and an explicit result type
for dependent items. No independent adversarial analysis or cross-platform
runtime validation was run for this follow-up.

### Pipeline slices and forwarded contracts

Both compilers can now form a prefix slice from an array field and pass that
slice through `Option`, a mapper, and a move. The verifier retains the
original target and the parent reborrow. The paired cases read a shared
slice, shorten it in the mapper, and write through a mutable slice. They
reject a second advance while the prior slice is still used and reject
a statically out-of-bounds slice of the field. An unknown upper bound
is checked at runtime, before constructing the slice descriptor.

The native pipeline specializer uses an existing parameter, local type
or direct callee result declaration to infer a mapper's result where
available. It then checks the generated mapper as an ordinary function.
The tests infer a reference through a call and an allocation forwarded
into a vector. A synchronous handle returned through two forwarding
functions still reserves the captured value until `join()`. The test
also rejects abandoning that handle. Each forwarding call in this
implementation passes the same formals in order and has the same signature
as its callee.

The package lexer buffer increased to 655360 tokens plus three sentinels
after the new compiler source exhausted the previous package capacity
during the first scan.

On macOS ARM64, the frontend and `crustc` agreed on 37 successful
programs, 18 compile-time refusals, and two expected runtime failures
for a dynamic slice bound and regional capacity. The emitted programs
ran under fatal UBSan at `-O0` and `-O2`. Package regressions and the
three Rust unit tests passed. `crustc` emitted C for its own package.
The resulting second-generation compiler passed the same pipeline
checks. The dynamic bound check was run separately for both generations.

The remaining native gaps are non-scalar slice elements, nested dependency
envelopes, collective retention of references independent of the source,
nominal pools, async handle compositions and mappers with captured state.
Dependent result inference still needs a supported, statically known
type. No language rule changed.

### Aggregate slices in pipelines

The verifier carries the declared element shape through the same slice loan
descriptor used for scalars. For a record element the shape identifies its
declaration. For a fixed-array element it includes the element type and
row length. Selecting a subslice preserves both the storage root and the
parent loan.

The paired cases cover reading a moved subslice of records, replacing an
element through a moved mutable record slice, and reading a two-dimensional
array through a slice of its rows. The compilers reject advancing while a
prior slice is still needed and reject an incompatible row length in the
mapper. The compiler package self-hosted on macOS ARM64 and the resulting
binary ran the same pipeline suite under fatal UBSan.

### Shared references collected from outside the source

The Rust frontend distinguishes the receiver's storage from the target of
a shared reference already held in a field. A return contract selecting
that field can preserve the target without reserving the receiver itself.
`collect` still checks for exclusive access and validates the target's
lifetime against the destination.

`crustc` resolves this dependency when every `Some` forwards the same
shared field and it can establish that the method leaves that field in
place. The pipeline's forwarding functions preserve the field selection.
The vector records the shared target at each append site and uses the
runtime bound when execution determines how many items were appended.

Both compilers collected two shared references, destroyed the source and
read through the second entry. Both rejected destroying the target before
that read. The paired suite passed 41 programs, 21 refusals and both
expected runtime failures on macOS ARM64 under fatal UBSan.

### Named pooled allocations and nested optional pipeline items

Both compilers mapped named pool allocations into a vector, removed an allocation
and recovered the pool's slots. The destructor witness observed each destruction
once. Both refused closing the pool while the destination still held an
allocation.

The Rust C backend initially failed the witness under UBSan. A destructor called
during scope rewind could start another rewind at the new depth and clean an
outer slot that the first rewind still planned to visit. The runtime now
detaches the expired slot and destructor lists before running callbacks. The
destructor regression suite also passed after this change.

Both compilers propagated dependencies through nested `Option` payloads for
a borrowed reference and a worker handle. The verifier rejected advancing before
the nested borrow's last use and abandoning a nested handle that reserved a target.
The self-hosted build passed 44 programs, 24 static refusals and both expected
runtime failures on macOS ARM64 under fatal UBSan at `-O0` and `-O2`.
These witnesses cover nominal allocations of plain records and nested optional
envelopes. They do not establish support for arbitrary dependent generic shapes.

### Mapper captures and asynchronous handles in pipelines

A mapper stores its captures alongside the previous stage. Each call uses
that stored state. A captured primitive is copied at construction when
`move` is absent, as specified for closure capture. Explicit `move` transfers the binding.
The paired cases verify that changing the outside primitive after construction
leaves the captured copy alone, and that successive mappers have independent
state. Both compilers preserve a captured mutable reference through its last
use and run the destructor of a moved record exactly once during collection.

Both compilers take an `AsyncHandle<i64>` from a vector field in the iterator
source, carry it through mapping and `Option`, and wait for it through
`.await`. A handle returned by a separate task can also reach that pipeline
through `join()`. Collection also transfers autonomous handles to the
destination vector and leaves the runtime to finish those tasks.
The two-handle case establishes that waiting for the
selected handle releases only its capture. Both compilers refuse a read or
abandonment while the corresponding capture remains active. With a blocking
launch failure injected in the emitted C, both executables observe the error
and the captured target retains its original value.

The Rust verifier stores known vector lengths for direct record fields. A
guaranteed tail extraction specializes its return dependency by that length
and updates the returned handle and the source separately. The storage
edge identifies which cached borrow summaries refer to the same container.
`crustc` uses the tracked vector entry chain when it can prove an unconditional
tail extraction through the source method and forwarding calls.

The first nested-handle implementation let a factory return a blocking handle
that borrowed storage in its own frame. `crustc` now checks the returned
handle's roots. Both compilers refuse an escaping borrow into a local
variable or a parameter passed by value before emitting C.

The executed cases cover direct tracked collection fields, supported captures
and known aggregate shapes. More general conditional extraction contracts and
arbitrary capture and envelope layouts in `crustc` remain outside this evidence.

### Paired validation of the six pipeline changes

On macOS ARM64, the Rust frontend and the freshly self-hosted `crustc` agreed
on 54 valid programs and 31 expected static refusals. Both emitted executables
passed the bounds and region exhaustion checks and both injected blocking
launch failure scenarios. The harness compiled the emitted C with fatal UBSan
at `-O0` and `-O2`. `cargo test`, the destructor regression suite and the
package integration suite also passed. This cycle reports compiler and
runtime tests on the host target.

## Corbo naming and editor support

The Rust bootstrap is named `corbo-frontend` and produces the self-hosted
`corboc` executable. The package loaders and the bundled standard library use
`.crb` sources and `src/main.crb` as the executable entry point. The installed
compiler locates the standard library under `share/corbo/stdlib/src`.

On macOS ARM64, both package loaders rejected a package with only
`src/main.crust`. After adding `src/main.crb`, the two loaders accepted the
package and the resulting program printed the value from the new entry point.
The installed `corboc` resolved the standard library and path and pinned Git
dependencies. It rebuilt itself with `build`, and the rebuilt compiler
compiled and ran the external two-module package.

Cargo tests and the generated standard library reference check passed.
The pipeline suite agreed on 54 valid programs and 31 static refusals after
the rename, with the bounds checks and forced launch failures exercised
under fatal UBSan.

Vim and Neovim detected existing and new `.crb` files and applied syntax
groups for the main lexical forms. A jump into a 250-line assembly block
also preserved its syntax region. The VS Code extension packaged as a VSIX,
installed successfully in an isolated VS Code profile, and its TextMate
grammar tokenized the shared lexical fixture with the expected scopes.

## Python prototype relocation

The 39 Python compiler modules moved to [prototype](../../prototype/README.md)
with identical contents. The historical suite now adds that directory to
`PYTHONPATH`. Standalone validation scripts locate it from their own path.
Mutation runners still patch isolated copies. The older runners now copy all
compiler modules, and their subprocesses ignore the caller's Python import
path so they execute the patched copy.

On macOS ARM64 with Python 3.14, the original checkout and the relocated
prototype discovered the same 3,826 unittest cases. All 15 tests that launch
the prototype CLI and all 48 tests in the ancestor join, loop result and loop
replacement suites passed in both layouts. The 15 loop replacement tests also
passed with UBSan after the move. The async vector insertion, plain join and
blocking spawn regressions passed 44, 15 and 14 tests respectively. The
representation builder produced the same 10,180 records when compared without
source line numbers. The Select runtime baseline passed and its seven
mutations were detected in both layouts.

The feature, runtime error, synchronous Boolean and native thread regression
suites failed on the same seven, one, eleven and eight cases respectively in
both layouts. The native thread suite ran 320 tests in each layout. The three
standalone generated-C validators stopped at the same compilation diagnostics
in both layouts. Some older mutation anchors have drifted from the current
prototype. The full discovered suite was interrupted after observing existing
failures, so the comparison covers the completed checks listed here.

## Embedded C and assembly highlighting

The VS Code extension uses the built-in C grammar inside `@c` and recognizes
ARM64 and x86-64 mnemonics, registers, directives, labels, numbers, and Corbo
operands inside `@asm`. This change covers editor tokenization. The compiler
still accepts only `@asm` among these two forms.

On macOS ARM64, TextMate with Oniguruma passed 35 scope checks and verified the
embedded C language ID. The checks exercised nested C braces, closing braces
in comments and strings, block delimiters on separate lines, and return to
Corbo after either block. Assembly checks also used the actual ARM64 and
x86-64 kernels from the standard library. The previous lexical smoke check
passed, and VS Code installed and listed `omework.corbo@0.1.1` in an isolated
profile. The token checks establish scopes independently of theme colors.

## Self-hosted compiler relocation

The self-hosted package moved to [compiler/corboc](../../compiler/corboc). Its
69 Corbo sources and manifest were byte-identical after the move. The lexer,
parser and representation corpus discovery checks each found all 69 sources
at their new paths.

On macOS ARM64, the Rust frontend built the relocated package into a temporary
installation with its own copy of the standard library. The installed
`corboc` then rebuilt the same package using `corboc build compiler/corboc`.
From outside the repository, the second-generation executable built a
two-module package that imported `std::encoding::hex::encode`. The resulting
program printed `2`, `50` and `97`, matching the Rust frontend and the
first-generation compiler. These checks cover the relocation and rebuild path
on the host platform.

## Caller-buffered blocking I/O

`std::io::buffered` provides `BufReader` and `BufWriter` for files and TCP
connections. The caller lends the transport and the storage. A zero-length
storage slice selects direct I/O. Read-ahead advances the transport and
dropping the reader discards buffered bytes that the caller did not consume.
A writer reports the accepted prefix and sends pending bytes with an explicit
`flush()`. It advances its pending range after each successful underlying
write. A write that accepts zero bytes with data pending returns
`BufferedError.WriteZero`. Dropping the writer discards pending bytes.

The Rust frontend now applies stored-reference reborrowing rules to slice
fields. It refuses moving an exclusive slice directly out of a field.
`validation/check_rust_buffered_io.py` exercised file buffering, empty
operations and buffers, read-ahead, EOF, dropped pending bytes, and repeated
write failure on a read-only file. It also checked five borrow refusals.
With `--tcp`, the same script verified a buffered TCP read and flushed write
against an independent loopback peer. Both runs executed on macOS ARM64 at
`-O0` and `-O2` with fatal UBSan. The Rust frontend checked the file source for
Linux x86-64, macOS x86-64, and Windows x86-64 and ARM64. Execution on those
targets remains unverified.

The self-hosted compiler can still build File programs with the updated
standard library. The buffered witness and a standalone constructor that
returns a record containing an input `&mut [u8]` both return status 9 in
`corboc`. Buffered adapters are usable through the Rust frontend. The
self-hosted verifier and its lowering still need support for this shape.

## Borrowed slice returns and buffered async I/O

The self-hosted compiler now checks stored slices using its slice argument
rules and rebinds a returned record's borrow to the caller. The exercised
constructor takes a single slice parameter and returns a record with the
slice and a scalar field. C lowering preserves the slice descriptor when
reborrowing the field. The same result can cross an inline `.await`.
Two independent calls printed `42`, `11` and `23` on both compilers at
`-O0` and `-O2` with fatal UBSan on macOS ARM64. Both compilers refused writes
while a loan was live and return of a slice of local storage. The executable
witness is `validation/check_rust_buffered_io.py --slice-result`, with
`--async` and `--corboc PATH` selecting the additional paths.

`std::io::asyn::buffered` implements File and TCP adapters with explicitly
awaited constructors, reads, writes and flushes. The Rust frontend ran the
File and TCP buffered witnesses under fatal UBSan at `-O0` and `-O2` on macOS
ARM64. File checks included eight borrow refusals. Three of those exercise
conflicts before awaiting a pending read. Both async witnesses also passed
the Rust frontend's checks for Linux x86-64, macOS x86-64, and Windows x86-64
and ARM64. Those additional targets were checked without executing C.

The complete buffered witnesses still fail to compile with `corboc`.
Both synchronous packages returned status 9. A standalone two-slice
constructor also returned status 9 in `corboc` and passed the Rust frontend.
The shared async module imports the TCP reactor even when an application
uses only File. Both async witnesses returned rule 8 at
`runtime::wait_socket(socket, write)` in the linked source. The two-module
package regression and the unbuffered synchronous and async File tests
continued to pass with the self-hosted compiler.

## Constructors with multiple borrowed slices

The self-hosted checker previously recognized a single borrowed slice
argument and attached it to the whole result. It now records the mapping
from returned fields to the actual arguments of each call when a synchronous
constructor directly returns a record with multiple slice parameters.
Projected uses select the corresponding argument. Uses of the whole record
retain all of its dependencies.

On macOS ARM64, both compilers built the returned-record witness with
temporary reborrows and with named slice arguments. The fields were
initialized in reverse parameter order. After moving the record, the
program reused the first array after its field's last use while keeping
the second field live. Both variants printed `42`, `11` and `23` at
`-O0` and `-O2` under fatal UBSan. Both compilers refused a conflicting
write to either array, two mutable arguments targeting the same array,
and a return that would carry a local array through the second field.
The existing single-slice regression also passed with the rebuilt
`corboc` through an inline `.await`. Generated constructors with 3, 4, 5
and 16 mutable slice fields also ran with `corboc` at `-O2` under fatal
UBSan. They checked which array each field reached and direct reuse of
the array after that field's last use. In each case, a write to the last
array before its borrowed field was used was refused.

Run `validation/check_rust_buffered_io.py --slice-result` for the Rust
frontend and add `--corboc PATH` for the self-hosted compiler. This pass
covers direct synchronous constructors with multiple slice arguments.
Mixed record-reference and slice arguments, multiple slice parameters
across an async boundary, and the full File and TCP adapter packages
were outside this check.


## Struct contracts and generic STD adapters

This cycle implements the approved type-contract extension on nominal
structures, with Corbo's self-hosted compiler as the implementation target.
The Rust compiler is frozen as requested. Its existing executable provides
the initial bootstrap; it is not being extended to match subsequent Corbo
fixes. The `--native-only` validation modes make that boundary explicit.

The frontend specializes constrained structs and their `impl` blocks before
ordinary checking and post-AST placement. It supports explicit type arguments,
constructor inference, required method signatures, receiver modes, `async`,
`with`, exact method sets and listed result-type alternatives. Dependent error
enums retain the stream's error type. This is static specialization: it adds
no dynamic dispatch or hidden source ownership.

`std::iter::Iter<T, V>` contains an actual `&mut T` and calls `T.next()` through
its contract. Package linking preserves its declaration and implementation.
The existing Map/collect lowering owns that concrete Iter as its predecessor;
this cycle does not move Map or the collection implementations out of the
compiler. Both buffered I/O modules now use `BufReader<T, E>` and
`BufWriter<T, E>`. They borrow the stream and caller-provided buffer separately,
and return `BufferedError<E>` (`Stream { error: E }` or `WriteZero`). The
`from_tcp` constructor remains as a compatibility alias to the same generic
construction. Flush remains explicit; dropping a writer discards pending
bytes.

Integration corrections include per-field constructor argument mappings,
disjoint field loans, preservation of reborrow parents in stored references,
transitive task reservations, and forwarding the source pool, shared-reference
origin and handle-extraction effect through the adapter. The generated
specializations go through the existing checker and backend. No N1–N8 rule
was relaxed for an adapter.

The async TCP check also exposed an existing missing runtime hook. The package
linker now carries non-forgeable metadata for the standard reactor's readiness
entry and queue functions. The backend connects the existing assembly queue
implementation to scheduler parking and waking. The registration and wake
transition share the scheduler lock, including the event-before-park case;
a one-shot registration is removed before publishing readiness. This cycle's
executable network evidence is macOS ARM64, not a Linux or Windows runtime
validation.

Validation commands and final results are recorded below once their runs
finish. The scope is functional coverage of these adapters and directly
related regressions. No independent adversarial audit or mutation campaign
is claimed for this cycle.

Completed functional runs on macOS ARM64:

- `validation/check_generic_structs.py --native-only --corboc PATH`:
  12 accepted programs executed at `-O0` and `-O2` under fatal UBSan,
  and 11 expected refusals. These include a tuple carrying borrowed records,
  rejection of a local referent hidden in such a return, incompatible
  contracts, type alternatives and a forged reactor hook.
- `validation/check_rust_pipelines.py --native-only --std-iter --corboc PATH`:
  52 accepted programs and 31 refusals, plus recursive use and an imported
  alias in a package (54 successful programs overall). The generated C ran
  at both optimization levels with fatal UBSan. Both regional/slice runtime
  failures and both simulated blocking-launch failures matched expectations.
- `validation/check_rust_buffered_io.py --corboc PATH`, with `--async`,
  `--memory`, `--memory --async`, `--tcp`, and `--tcp --async`: all six
  combinations executed at both optimization levels under fatal UBSan.
  File runs included five synchronous and eight asynchronous borrow refusals.
  TCP used a separate Python socket peer. Custom streams retained `bool`
  errors and distinguished `WriteZero`.
- The sync and async `--slice-result` runs passed. They cover independent
  calls, moves, separate field roots, overlapping mutable arguments and
  escaping local slices.
- `python3 scripts/stdlib_docs.py --check` checked 75 source files and
  904 documented declarations after regenerating the reference. The generator
  now distinguishes required signatures in type contracts from methods.

The Rust bootstrap binary was left unchanged. A temporary debug-file dump
was removed from its source as cleanup; no further Rust language support or
checker behavior was developed after the freeze. The paired mode remains
available, but this cycle's final runs deliberately use `--native-only`.
The frozen Rust implementation still rejects the fluent temporary regression
with the new concrete STD Iter; that discrepancy was not hidden or fixed.

Limits: specialization currently uses bounded workspace tables (32 type
parameters, 4,096 instances and a 3 MiB rewritten source budget). Multiple
incompatible specializations of one dependent nominal type inside a single
outer specialization remain unsupported. Buffered errors were exercised with
`bool`, `FileError` and `SocketError`; this is not exhaustive coverage of
all possible error payloads. The new reactor bridge was executed on macOS
ARM64. It does not establish Linux/Windows parity or support for overlapping
readiness registrations on one descriptor. Calls returning tuples of borrowed
records still require further caller-side instantiation support; validating
the existing unused split definition does not claim that support.

Self-reconstruction completed: the updated `corboc --emit-package-c
compiler/corboc --stdlib-dir stdlib/src` generated its own C (12,634,090
bytes). That output compiled at `-O2` both normally and with fatal UBSan.
The normal binary is available at `build/corboc-contracts/bin/corboc`; the
local build tree points its standard-library installation to this checkout.
The UBSan-instrumented self-rebuilt compiler then passed the full generic,
actual-STD Iter, File, TCP, custom-stream and borrowed-slice suites listed
above, including both TCP modes. This instruments the compiler itself as
well as the generated test executables. No sanitizer diagnostic occurred in
these runs.

The self-rebuilt normal compiler also used its `build` command and automatic
STD lookup to compile `validation/fixtures/struct_contracts`, a two-module
external package combining a user-defined stream, Iter/Map/collect and both
buffered adapters. Its output was exactly `5`, `6`, `1`, `7`, each on its own
line. The package is retained as a reproducible witness. No new discrepancy
remains in the listed functional checks; the limits above still apply.

Cycle checklist:

- [x] Struct-contract grammar, parser and static specialization in corboc.
- [x] Actual constrained Iter and generic buffered adapters in STD.
- [x] Functional and directly related rejection/runtime regressions.
- [x] Corboc self-reconstruction and reruns using the resulting compiler.
- [x] External two-module build using automatic STD resolution.
- [x] Generated STD reference, verification matrix and cycle report updated.

## STD-owned iterator adapters

The Rust compiler remains frozen. The implementation target is `corboc` and the
standard library. The approved Reduce API uses the first yielded item as its
accumulator and yields its final result once; an empty input yields `None`.
The package factory `std::iter::iter(&mut source)` uses the existing structural
`next(&mut self) -> Option<V>` contract.

### Implementation

- STD now contains the bodies of Map, Filter, Reduce and collect, alongside Iter.
  Reduce's remaining-item fold is a separate STD method; no default accumulator
  is invented. `collect` accepts either fluent or package-function notation.
- The compiler specializes these STD bodies and callback captures. It no longer
  contains the emitted Map algorithm or the emitted collect loop. The current
  pass still recognizes the STD adapter templates; this is not a claim that all
  adapter-specific specialization has been removed.
- Empty wrapper layout and captureless identity-call reductions preserve logical
  moves. Real captured state retains ownership of its predecessor. The source
  bodies are checked after specialization, using the normal post-AST pipeline.
- Shared-reference summaries now follow forwarding through stored owned records;
  dependency lookup can descend through their constructor mappings.
- Scalar reference arguments can coexist with another reserved argument, subject
  to the existing lifetime and exclusive-alias checks. A captured Filter predicate
  exercises a mutable callback state and a separate shared item borrow.
- Nominal struct reassignment now checks matching shape and surviving dependencies.
  Lowering evaluates the replacement before destroying the old value. If the RHS
  moved the old record, its cleared representation prevents a second destructor
  invocation. The owned-item Reduce regression checks the complete trace.
- The combined package token budget increased from 640 Ki to 768 Ki, with the same
  checked exhaustion behavior. The frozen Rust lexer counted 655,105 raw tokens
  before the final small source changes; corboc also represents ASM operands as
  tokens. The old 655,360-token package limit was no longer sufficient.

### Executed functional coverage

`validation/check_std_iter.py` covers nine accepted package programs: fluent
composition; empty and singleton reductions; predicate and reducer captures;
cleanup of rejected owned structs; reduction of owned structs; package-level collect; and replacement-before-cleanup order. Five syntactically valid programs must be refused for source use during
an active loan, incompatible predicate and reducer parameters, predecessor use after move, and replacement under an active aggregate loan. Refusals check the expected diagnostic rule identifier.

| Executed program target | Nine programs at O0/O2 | Sanitizer |
| --- | --- | --- |
| macOS ARM64, host | Passed | fatal UBSan |
| macOS x86-64, Rosetta | Passed | fatal UBSan |
| Linux x86-64, Docker `rust:1.94-bookworm` | Passed | fatal UBSan |
| Windows x86-64 PE, Wine 11.21 | Passed | UBSan with fatal traps |
| Windows ARM64 | Not executed; explicitly deferred by the owner | None |

The compiler producing these cross-target C witnesses runs on macOS ARM64. This
matrix executes the generated programs; it does not claim that corboc itself was
rebuilt or run on each target. Wine execution does not replace a native Windows
audit. Five refusals were checked by the host corboc, not by four independent
platform compilers.

The existing pipeline regression suite also completed: 54 successful programs,
31 rejected programs, two expected runtime errors and two injected blocking-launch
failures, at O0/O2 with fatal UBSan on macOS ARM64. It includes reference, allocation,
handle, cleanup, recursion and package-alias paths. Structural-contract regressions
completed separately. No independent adversarial audit or mutation campaign was
performed in this cycle.

### Reconstruction and remaining limits

Corboc generated its complete package C (12,780,576 bytes). Compiling this C with
`cc -std=c11 -pthread -O2 -fsanitize=undefined -fno-sanitize-recover=all ... -lm`
produced `build/corboc-std-iter/bin/corboc`. This reconstructed compiler completed
all nine STD programs and five refusals, the full historical pipeline suite, and
the structural-contract suite (12 accepted programs and 11 refusals). Its
STD-generated C matched the already executed platform witnesses byte for byte.

The reconstructed compiler then generated C for its own package again. Both
outputs are byte-identical and have SHA-256
`17f766c9aa5e34edbb215e2974c65c814ad64148f8ec5529f56c669de8fc5bde`.
Its normal `build` command also compiled the retained iterator package using
automatic STD discovery; execution printed `1`, `120`, `7`.

Reproduction:

```sh
python3 validation/check_std_iter.py --corboc build/corboc-std-iter/bin/corboc
python3 validation/check_rust_pipelines.py --native-only --std-iter --corboc build/corboc-std-iter/bin/corboc
python3 validation/check_generic_structs.py --native-only --corboc build/corboc-std-iter/bin/corboc
build/corboc-std-iter/bin/corboc --emit-package-c compiler/corboc --stdlib-dir stdlib/src > /tmp/corboc-next.c
python3 scripts/stdlib_docs.py --check
```

The platform script accepts `--cc`, `--runner` and `--keep`. A Windows compiler
wrapper translated the fatal-recovery option to `-fsanitize-trap=undefined`.
The final reference check used `--reference-c` to compare the reconstructed
compiler's C with the programs actually executed across the platform matrix.
Documentation checks completed for 75 STD source files and 913 declarations;
`git diff --check` also passed.

During reconstruction, nested tuple-valued `else if`, mixed tuple-literal/call
conditional results, and a forwarded byte-slice binding exposed existing verifier
limitations. Internal dispatch now uses explicit returns, scalar assignments and
a direct source view. Those general limitations remain recorded in TODO; no new
language prohibition was introduced to justify a compiler rejection.

`Vector` and `HashMap` implementation migration is outside this iterator lot.
The compiler still has dedicated STD adapter specialization and callback layout
handling. This is not a claim that arbitrary user-defined callable-field templates
are now supported. Reduce's executed payloads are scalars and owned plain structs;
other payload compositions are not claimed as validated by these new tests.
These checks are execution evidence for the programs and environments listed,
not a general memory-safety proof or a claim that every composition has been
verified. No independent adversarial audit or mutation campaign was run here.


## Correction: collect belongs to the STD objects

The preceding iterator cycle exposed a package-level `std::iter::collect`
function without user approval. That API is removed. `collect` is a consuming
method declared in the STD on Iter, Map, Filter and Reduce; the `iter` factory
remains public. This corrects API placement without changing ownership rules.

The current compiler still specializes these adapter templates. Method-local
type parameters must remain uninstantiated until destination inference; the
generic pass now preserves the original Iter collection method as a private
source recipe rather than substituting an element reference into a parameter
declaration. This is existing compiler/API coupling, not an additional language
rule. General removal of adapter-specific specialization is outside this fix.

Executed on macOS ARM64 using the corrected bootstrap-built corboc:
`validation/check_std_iter.py` completed ten accepted programs at O0 and O2
with fatal UBSan, six rule refusals and rejection of the removed qualified
package function. Source documentation checks passed for 75 files and 916
declarations; `git diff --check` passed.

The earlier cycle's cross-platform and self-reconstruction results apply to
that earlier implementation. Full self-reconstruction and cross-platform
execution have not been repeated on this final method-recipe correction.
Windows ARM64 remains explicitly unexecuted. No independent audit is claimed.


## Root STD collection exports

Scope: API/STD exports and package-name resolution. The owner accepted retaining
the existing native implementation while exposing `std::Vector`, `std::HashMap`
and related existing types. `stdlib/src/collections.crb` declares Vector,
HashMap and String as root STD export bindings. Files directly in `stdlib/src`
belong to `std`; the filename does not introduce a `std::collections` module.

The package loader permits the reserved names in these trusted public STD export
declarations only. The linker removes the declarations before nominal layout
analysis and resolves references, aliases and qualified calls to the original
native type identities. User packages cannot redeclare the native names.
No grammar production, storage algorithm, lifetime rule or allocation primitive
was added. Existing unqualified type spellings remain supported. This does not
claim that collection implementations have moved out of the compiler.

Executed with a compiler built from the frozen Rust bootstrap on macOS ARM64:

```sh
python3 validation/check_std_collection_imports.py --corboc /tmp/corbo-std-exports/corboc
python3 scripts/stdlib_docs.py --check
git diff --check
```

Four accepted packages produced their expected output at O2 with fatal UBSan:
grouped root imports; aliases moving an allocation from a vector to a map and
returning its pool slot; fully qualified types and a qualified map constructor;
and imports in another package module. Four expected refusals completed:
duplicate import and alias/declaration collision (exit 14), unknown root export
(exit 13), and reserved native type redeclaration in the user package (exit 7).
Documentation checks cover 76 source files and 919 documented declarations.

Exploratory programs using scalar `A<Vector<i64>>.pop()` exposed an existing
unsupported verifier path in both the imported and original unqualified form;
this unrelated backend limitation was not expanded into an API-routing fix.
The retained accepted tests use supported indexing and owned-item extraction.
The String API uses `byte_len()`, not `len()`.

Validation is limited to these imports and related operations on macOS ARM64.
The native platform implementations were unchanged; neither full compiler
self-reconstruction nor a cross-platform campaign was repeated for this API
change. Windows ARM64 remains unexecuted by prior explicit decision. No new
independent audit, mutation campaign or general safety proof is claimed.


## Visible native runtime source separation

Scope: file organization only, as requested. No language rule, API or algorithm
was changed. The actual readable C fragments now live under `runtime/memory/`,
`runtime/collections/` and `runtime/async/`. Compiler parsing, representations,
analysis and lowering remain under `compiler/corboc/src/`. Native type mapping
and program-specific generated cleanup remain compiler responsibilities.

`target_c`, `lowering_runtime` and `lowering_maps` retain their existing backend
entry points and call generated resource functions. `scripts/runtime_sources.py`
embeds the readable runtime in `runtime_sources.crb`; installed compilers do not
need external source files at execution time. That file is generated, not an
independent implementation to maintain. See [runtime/README.md](../../runtime/README.md).

Executed checks: reconstructed each of the seven generated emitter payloads
and compared its bytes to the former arrays captured immediately before
extraction. Base runtime, task runtime, pool/vector runtime, task values, native
threads, reclamation and HashMap all matched. The two conditional reclamation
lock/unlock branches were checked separately. `python3 scripts/runtime_sources.py
--check` and `git diff --check` passed. No compiler rebuild, behavioral test suite
or platform campaign was run for this source separation, per the owner's scope.


## Native Gzip and Zstd

Scope: STD/API implementation, with native Corbo requested by the owner. No
compiler grammar, normative memory rule or primitive was added. The Rust
frontend remained frozen and the existing corboc binary compiled the codecs.
No general compiler suite or self-reconstruction was run for this addition.

### Implementation

`std::compression::gzip` implements Gzip headers and trailers, CRC-32, stored
blocks and fixed-Huffman/LZ77 encoding. Its decoder accepts all three DEFLATE
block types, optional headers and concatenated members. Search levels are 0–9;
zero uses stored blocks and can use an empty workspace.

`std::compression::zstd` implements frame headers, raw/RLE/compressed decoding,
Huffman literals, normalized and predefined FSE tables, repeat tables and
repeat offsets. Its encoder produces raw literals with LZ77 sequences and RLE
sequence tables, using raw blocks where compression would expand the input.
Levels 1–22 control search effort; zero selects level three. XXH64 content
checksums, concatenated frames and skippable frames are supported. Nonzero
dictionary IDs return `DictionaryRequired`; dictionary loading and streaming
APIs remain outside this initial interface. Native level numbers do not promise
reference-library compression ratios or byte-for-byte output.

Both compressors take caller-owned output and 36864 u64 workspace words
(288 KiB). Zstd decoding takes 131072 caller-owned bytes for literals; entropy
tables have fixed local sizes. Gzip decoding uses fixed local tables and the
output as its history. The implementations retain no buffers and call no
external compression library or command-line program. Errors may leave an
output prefix, as documented. The C backend still compiles Corbo normally;
there is no handwritten C compression bridge.

Zstd entropy decoding was adapted with Go 1.24.3 internal/zstd as reference.
The BSD notice is retained in docs/third-party and shipped with the STD;
affected sources carry the combined SPDX expression. The documentation checker
accepts that additional license expression without weakening comment checks.

### Targeted evidence

Each target uses the same codec validation programs compiled by corboc:

- 24 Gzip encodings across six inputs and four levels, decoded independently by
  Python Gzip/zlib. Cases include empty input, all byte values, incompressible
  data and a 256 KiB input spanning multiple stored blocks.
- 11 Gzip decoding fixtures: reference stored/fixed/dynamic trees,
  Huffman-only data, concatenated members and all optional header fields,
  including header CRC.
- Seven Gzip failure cases: empty/malformed/truncated input, altered checksum,
  undersized output and undersized compression workspace.
- 30 Zstd encodings across six inputs and five levels, decoded independently
  by libzstd 1.5.7. Repeated input must actually shrink.
- 22 Zstd decoding fixtures: reference and previously reference-validated native
  frames, weighted data exercising entropy coding, multiple reference levels,
  checksums, raw/RLE blocks, unknown content size, concatenation and skippable
  frames. Two manually constructed frames were independently accepted by
  libzstd. Six fixtures come from the independently validated native encoder;
  not all fixtures were produced by the reference encoder.
- Eight Zstd failure cases: malformed/truncated input, altered checksum,
  dictionary requirement, undersized output and undersized workspace.

| Generated executable target | Gzip | Zstd | Configuration |
| --- | --- | --- | --- |
| macOS ARM64 | Passed | Passed | O2, fatal UBSan |
| macOS x86-64 through Rosetta | Passed | Passed | O2, fatal UBSan |
| Linux x86-64 in Docker | Passed | Passed | O2, fatal UBSan |
| Windows x86-64 under Wine | Passed | Passed | O2, UBSan fatal traps |
| Windows ARM64 | Not executed by prior explicit decision | Not executed | No execution claim |

The compiler runs on macOS ARM64 and emits the programs for these target C
compilers. This does not claim that corboc itself was rebuilt on each target.
Wine execution is separate from native Windows validation. A missing Zig
installation payload interrupted the first Windows attempt; it was restored
from the official Zig 0.14.1 archive before the final run.

The documented Gzip example compiled and executed under fatal UBSan, printing
12. STD documentation checks passed for 83 source files and 977 declarations.
Whitespace checks and the unrelated runtime-resource freshness check passed.

Two implementation issues were corrected before completion: XXH64 rotations
mask discarded bits before Corbo's checked left shift, and a 258-byte Gzip
match uses the dedicated canonical length symbol. The final encoder revision
was repeated on the target matrix. Reference-library interoperability checks
are functional evidence, not an independent adversarial audit or a general
safety proof. No compiler mutation campaign was run.

Internal entropy helper metadata uses packed bounded scalar fields. This avoids
unsupported tuple-returning helper compositions encountered in corboc without
changing the public Result API or introducing a language restriction. Explicit
matches likewise avoid relying on the question-mark lexer path in the compiler
binary used here. These compiler limits were not expanded into this STD task.

Reproduction:

```sh
python3 validation/check_compression.py --corboc /path/to/corboc
python3 validation/check_compression.py --only gzip --encode-only --corboc /path/to/corboc
python3 scripts/stdlib_docs.py --check
```

The script accepts `--cc`, `--runner` and `--keep` for the target toolchains.
The reference libraries are test dependencies only. See [COMPRESSION.md](../COMPRESSION.md)
for the API and memory budgets.


## Compression API extensions

Classification: **STD/API**, with native Corbo implementations. No grammar,
normative memory rule, Rust bootstrap source or compiler mechanism was changed
in this cycle. Existing one-shot signatures are preserved. Reference libraries
remain test dependencies, not codec implementation dependencies.

### Implemented behavior

- Gzip and Zstd `Encoder` / `Decoder`, `process`, `consumed`, `finished` and
  `reset`. Callers provide all retained storage. Encoders split arbitrary total
  input into independent standard frames; decoders validate and buffer one
  whole frame before releasing it. Frame budgets, lack of implicit flush on
  destruction and loss of cross-frame compression history are documented.
- Zstd raw-content and formatted dictionaries, formatted IDs, dictionary
  entropy tables and repeated offsets. The encoder borrows dictionary history;
  the decoder can consume reference frames using dictionary-provided tables.
  Missing, mismatched and malformed dictionaries are distinguished.
- Gzip compares a dynamic-Huffman literal block with its existing candidate.
  Zstd can emit one or four Huffman literal streams with direct weights.
  Unsupported/unprofitable entropy trees fall back to the existing paths.
  General FSE sequence/weight encoding and dictionary training are not added.

### Evidence

`validation/check_compression_extensions.py` generates seven focused programs:
Gzip/Zstd streaming, raw/trained dictionary interop, dictionary errors and
Gzip/Zstd entropy encoding. It uses the active self-hosted compiler, native C
compilation at O2 with fatal UBSan, and Python Gzip/libzstd 1.5.7 as independent
format oracles. It does not rebuild the compiler or run a general rule campaign.

- Streams: three-byte input/five-byte output encoder fragments and two-byte
  input/seven-byte output decoder fragments; 100 source bytes span four frames.
  Native output is independently decoded. Zstd streaming uses raw dictionary
  history. Cases exercise EOF, reset, empty-stream encoding, empty encoded
  input rejection, encoded-frame budget exhaustion, altered checksums and
  sticky terminal errors. Callers drain output and re-submit unconsumed input.
- Dictionaries: both native-to-reference and reference-to-native exchanges
  with a raw dictionary and a 1024-byte dictionary trained by the reference
  implementation. Exact error variants are checked for absent, wrong-ID and
  malformed dictionaries. This does not constitute a dictionary-training API.
- Entropy: a deterministic weighted 4096-byte fixture, independently decoded
  and also decoded natively. The additional 511-byte Zstd round trip exercises
  the single-stream Huffman format. Four-stream encoding is exercised at 4096.
- One-shot regressions on macOS ARM64: all 24 Gzip and 30 Zstd native encodings,
  11 Gzip / 22 Zstd decoding fixtures and the existing seven/eight codec error
  cases ran to completion under fatal UBSan after the implementation changes.

The same fixture and level six were encoded with the pre-extension STD snapshot
and the new implementation, using the same compiler:

| Codec | Previous bytes | New bytes | Reduction on this fixture |
| --- | ---: | ---: | ---: |
| Gzip | 1297 | 1000 | 22.9% |
| Zstd | 4110 | 874 | 78.7% |

Both versions were decoded independently. This is a measured fixture result,
not a throughput claim, universal compression-ratio guarantee, safety proof or
independent adversarial audit. No mutation campaign was performed.

### Platform execution

All seven extension programs ran to completion on the four executable targets:

| Generated executable target | Streaming | Dictionaries | Entropy/native round trips | Configuration |
| --- | --- | --- | --- | --- |
| macOS ARM64 | Passed | Passed | Passed | O2, fatal UBSan |
| macOS x86-64 through Rosetta | Passed | Passed | Passed | O2, fatal UBSan |
| Linux x86-64 in Docker | Passed | Passed | Passed | O2, fatal UBSan |
| Windows x86-64 under Wine | Passed | Passed | Passed | O2, UBSan fatal traps |
| Windows ARM64 | Not executed | Not executed | Not executed | Explicitly deferred |

The compiler itself ran on macOS ARM64. The other targets compile and execute
its generated fixture C; no compiler rebuild on those systems is claimed.
Wine evidence is not native Windows validation. Current documentation checks
passed for 89 source files and 1018 declarations; runtime-resource freshness,
Python syntax and whitespace checks passed. The documented streaming example
also compiled and executed under fatal UBSan.

### Boundaries and reproduction

The streaming decoder needs storage for a complete maximum-sized encoded and
decoded frame. It is not a constant-window decoder for arbitrarily large
single frames. Gzip may reparse a growing prefix, so very small input fragments
can increase CPU work. No speed benchmark was added. A codec error can leave
that call's output partially written; discard it. Retained buffers and the
Zstd dictionary follow the existing ordinary borrowing semantics.

The implementation uses explicit matches and primitive progress accessors to
stay within the available self-hosted generator's lowering paths. Known
lowering limitations around some record-valued method results, mixed borrowed
constructor arguments and borrowed-enum matches were not broadened into this
API task. They do not define new language restrictions.

```sh
python3 validation/check_compression_extensions.py --corboc /path/to/corboc --keep /tmp/compression-extensions
python3 validation/check_compression.py --corboc /path/to/corboc
python3 scripts/stdlib_docs.py --check
```

`--cc` and `--runner` select a target. `--reuse-c` compiles the already-generated
fixture C for another target without repeating frontend compilation; these
codecs contain no target-selected Corbo branches. `--only` can select streaming,
dictionaries or entropy tests (and can be repeated). The explicit-frame budget,
API signatures and remaining encoder limits are in [COMPRESSION.md](../COMPRESSION.md).


## Recorded compiler limits: follow-up

The conditional-annotation, foreign-C and recorded composition follow-up is now
tracked in [CORE_EXTENSIONS_CYCLE.md](CORE_EXTENSIONS_CYCLE.md). It supersedes the
open implementation status of the specific nested/mixed primitive tuple,
scalar pooled-pop, transient constructor input, parameter-slice forwarding and
borrowed-enum witnesses cited above. Simple local slice moves and plain
record-valued method results were already accepted and were retained as
regressions. The report records the completed platform executions and the
remaining scope boundaries separately from historical results.
