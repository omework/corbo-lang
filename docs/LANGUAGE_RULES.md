[Français](LANGUAGE_RULES-fr.md)

<a id="crust--règles-de-langage-retenues"></a>

# Corbo language rules

Enum variants use `Enum::Variant` in constructors, `match` and `if let`.
The older `Enum.Variant` form remains accepted for compatibility. Both forms
resolve to the same variant and preserve payload evaluation, copy/move,
borrowing and destruction semantics. `Type::method(...)` remains an associated
function call; the separator does not turn methods into variants.


The [inline assembly and File design](FILE.md) records `@unchecked`, explicit assembly operands, and target-sized `usize`.

The initial experimental design dates from November 1, 2026. The async and
multithreaded extension and the removal of public reset were recorded on
November 4, 2026. See the rules for [growing regions](GROWING_REGIONS.md),
[structures and methods](STRUCTURES_METHODS.md), and [UTF-8](UTF8_STRINGS.md)
for the associated decisions.

This document records the accepted design. The [project README](../README.md)
describes the implemented subset. Some examples use features beyond that
subset. The [memory safety status](SAFETY.md) records the obligations, the tests
that have run, and the guarantees still to be established.

The [core EBNF grammar](../CORE_GRAMMAR.ebnf) describes synchronous and async
syntax, including fixed-width primitives and transfers by value. The language
rules define typing, borrowing, cleanup, and obligations to wait.

An enum variant declared as `Pair(u32, i64)` takes all of its fields in
declaration order. Its constructor `E.Pair(first, second)` evaluates arguments
left to right. The pattern `E.Pair(a, b)` binds the same positions and accepts
`_` for an ignored field. The usual move and borrow rules for enum fields apply.

The [async and multithreaded rules](ASYNC_MULTITHREAD_RULES.md) are normative.
AS1–AS16, RT1–RT8, MT1–MT11, SL1–SL2, and PR1 supersede incompatible historical
passages below. The entry point remains synchronous. The compiler injects async
state pools. Public `reset()` was removed from the prototype. It is available
in the explicitly enabled historical compatibility profile. The verification
matrix tracks the extent of async support. Historical reset examples,
contracts, and proofs apply to that compatibility profile.

The historical prototype supported nonrecursive functions, allocators passed
by explicit borrow, moved arguments, and allocation returns. In that syntax,
`-> <- Int` returned an allocation and `-> Int` returned a copyable integer.
The memory checker analyzed function bodies with symbolic inputs and kept
specialization checks at concrete call sites. It summarized allocation and
reset effects, return provenance, and identity preservation using symbolic
sources. It inferred relations between sources from operation order. Call
verification used those contracts, while the C backend remained specialized.

[Package and module rules](MODULES.md) define source layout, visibility, and imports.

[Configurable package constants](CONFIGURATION_CONSTANTS.md) define the accepted
`#(configurable)` marker and lexical `#(override: ...)` blocks (CC1–CC7).
They select compile-time specializations, not runtime limits or verifier analysis
directives. The grammar and corboc implement these forms; the configuration specification
records the current bounded constant-expression support.
The [HTTP parsing design](HTTP.md) applies them to bounded request/response
parsing and records caller responsibility for request-dependent body semantics.
The synchronous HTTP API is implemented; its focused execution evidence and limits
are recorded in the [implementation cycle](cycles/HTTP_CONFIGURATION_IMPLEMENTATION_CYCLE.md).

The accepted [mutation-permission decision](MUTABLE_ACCESS.md) supersedes older
requirements that infer exclusivity merely from `&mut`. Lifetime, synchronization
and branch-completion obligations remain. Corboc implements the separation with focused validation; unresolved proofs still reject.

<a id="noyau-mémoire--grille-de-lecture"></a>

## Core memory invariants

N1–N8 group the rules already adopted. The normative sections and their
references define each obligation in detail.

| Rule | Invariant | References |
| --- | --- | --- |
| N1 | An accessible value is initialized and used according to its type. `T`, `A<T>`, `&T`, and `&mut T` denote distinct forms. | §2, ST1–ST5, H1 |
| N2 | A value that needs destruction has exactly one party responsible for cleanup at a time. A move transfers that responsibility. A borrow leaves it in place. | §3, §6, H1 |
| N3 | Syntax and type distinguish copying, borrowing, and moving; primitives and eligible enums copy implicitly by value (V3). An outgoing transfer takes effect when it has a receiver. Usage requirements and method-specific rules apply. | §0, §3, §4, ST17–ST18, ME1–ME4 |
| N4 | The target of a borrow and the source pool of an allocation must remain valid wherever the value is passed. Each transfer from a child scope to its parent is checked separately, without implicit promotion of the target. | §3–§5 |
| N5 | `&mut T` grants mutation permission, not uniqueness. Potentially concurrent overlapping accesses involving a write require established synchronization. Validity dependencies remain tracked. | MA1–MA6, §5 |
| N6 | Every path reaching a use must permit that use. The analysis tracks provenance, control-flow exits, and evaluation order, including evaluating a replacement before destroying the old value. | §1–§5, F3–F4 |
| N7 | A value is destroyed once before its storage is reclaimed. Dependencies constrain destruction order. Reusing a slot never reactivates a previous access. | §6–§8 |
| N8 | Type, provenance, borrowing, and cleanup obligations carry across boundaries. Calls are checked using the inferred contract. | §5, §10 |

The async rules apply these invariants to captures, suspension, results, and
waiting. Cursors, regions, and slot indices describe storage policies. Those
policies must preserve the lifetime and address stability of each value.

The [memory representation model](MEMORY_REPRESENTATION.md) describes the
objects and links the compiler uses to apply these rules.

<a id="grammaire-règles-et-directives-danalyse"></a>

## Grammar, rules, and analysis directives

- The grammar defines the forms a programmer can write.
- A rule defines an obligation and when the compiler must establish it.
- A primitive defines a language operation and its behavior.
- An analysis directive references a rule and describes how to establish a
  fact needed to check that rule in a particular situation.
- A test case exercises these obligations on a program.

The verifier starts with the facts already available. When a fact is missing,
it selects directives that match the rule, the program construct, and the
fact it needs. A directive can establish a fact, show a violation, or leave
the obligation unresolved. When a rule requires static proof, an unresolved
obligation causes rejection. Additional directives can establish the same
rule for more programs.

<a id="refus-et-arbitrage-de-la-grammaire"></a>

### Rejection and grammar decisions

The compiler rejects a syntactically valid program when it establishes a
violation or when an obligation that requires static proof remains unresolved.
The diagnostic distinguishes an established violation from a missing proof.

To investigate a rejection, first identify the rule and the fact needed to
check it. If the compiler can derive that fact from the source, the work belongs
in the analysis directives. If the developer can supply missing information,
decide how the grammar should express it and how the compiler should verify it.
Specific combinations of language constructs serve as test cases for the
existing rules.

For an execution branch, N4 governs the validity of its dependencies. The
`branch` annotation describes a point at which the compiler can establish
that their use has ended. RT7 governs runtime cleanup.

The following example shows the proposed format for an analysis directive.
Here, `g` is the group that the verifier must prove nonempty before
`select()`.

```yaml
règle: SL1
correspond_si:
  - Le fait recherché est « g est non vide » à la jonction d'un if.
  - Sur chaque chemin qui atteint cette jonction, le même groupe g est connu non vide.
établit: g est non vide après la jonction.
```

### Unconstrained type parameters and usage constraints

`#(type: V)` introduces a type parameter with no allowed-type restriction.
The former `#(type: V *)` spelling is rejected by the active core parser.

Allowed-type lists remain on uses inside a type contract, for example
`#(type: S<V: i64, bool> with { fn get(&self) -> V; })`.
The bare declaration does not restrict V; that use requires V to be one of the
listed types. Structural method contracts and their existing `with` behavior
are unchanged. There is no new standalone `#(type: V: ...)` declaration form.

## 0. Principe d'intention explicite

**I1 — Central ownership.** Memory management choices must be explicit
in the code: source of storage, borrowing, displacement, transfers and requests for
early destruction. The compiler verifies these intentions; it does not silently
replace them with another strategy.

**I6 — Intention legible and generation by IA.** The safety and clarification of
rules must reduce the gap between the developer's intent and the code generated,
notably by IA. Encourage refusals of inconsistent intentions rather than silent
changes of meaning; report hidden allocations, borrowings or transfers and close
ratings that can produce another valid program. Ergonomic exceptions must be
identified and arbitrated, such as automatic borrowing of the ME2 method receiver.
This objective is not evidence of equivalence between a natural language intent and a
program.

**I2 — Source of storage.** Any fixed size storage is placed on
The local values use the implicit data stack. The descriptor of a growing collection
and the area of a pool follow this rule. A pool allocation requires the explicit
choice of pool by
`pool.new(...)`. The compiler manages the placement on the data stack without
select a pool instead of the programmer. The passages that use
`stack(octets)`, `Allocator` ou `new(source)` describe the old API.

**I3 — Calculation of the investment.** The compiler calculates the locations, the
sliders and the cleaning of the implicit data stack and the pools chosen by the
programmer. These operations follow the lifetime rules.

**I4 — Dimensionnement.** L’annotation globale
`#(datastack: size=4G, region_stack_size=4G, region_size=100M)`
and each of its properties is optional. For each omitted size, static analysis uses
the maximum it can set, then the default value of G2 if this maximum is unknown. P2
defines the local configuration.

[TYPE_FEATURES.md](TYPE_FEATURES.md) complete I5, B4 and B5: TF1–TF5
introduce structural constraints to a method, their static resolution and the
preservation of concrete contracts.

**I5 — Reference for the core of language.** Rust is the basis for the
types, expressions, operators, flow control and pattern matching. We do not seek to
redraw these aspects without necessity. Explicit choices already
selected for Corbo, including memory management, remain priority: `new`
with explicit source, scopes, borrowings, `<-`/`->`Allocators and pools.

For numeric conversions, the checked-conversion decision in
[Checked extraction and conversions](CHECKED_EXTRACTION_CONVERSIONS.md) supersedes
the earlier draft-07 restriction on `as`. `value as T` checks the actual value
for exact representability and stops the program on failure. `T::try_from(value)`
remains the recoverable alternative. Postfix `!` extracts the successful payload
of Result/Option and stops on Err/None; prefix `!` remains boolean negation.

This reference refers to a minimalist kernel: legible syntax, simple types,
functions, blocks, expressions, conditions, loops, enums and pattern matching. It
does not involve reproducing all the features of Rust. Complex macros, procedural or
based on a rewrite language remain out of scope. Simple local memory configuration
directives in P2 remain compatible with this choice; they do not require a general
metaprogramming system.

This decision provides a design reference; it does not mean that
all Rust is implemented, or his library `core`/`std` is resumed, nor that
The features, threads and async were out of the original perimeter. The features with
several methods are carried forward; the features with one method have a static
support. Threads and async have a partial support followed in the matrix, which
distinguishes the cases executed from the rules still to be connected.

The old prototype notation used `new(source) Int(...)`, with
`allocator()` ou `stack(octets)` to report a local source. I2 described
The old examples below illustrate the local rules indicated; they do not replace
recent rating decisions.

<a id="1-blocs-et-exécution"></a>

## 1. Blocks and execution

**S1 — Syntaxe.** A block starts with `{` and ends up `}`. Rating
`scope A { ... }` was used for discussion; it is not part of the syntax.

**S2 — Initial model and extension.** The initial model is synchronous.
The async/multithread design is defined by AS1–AS16, RT1–RT8, MT1–MT11 and SL1–SL2 in
[l'extension normative](ASYNC_MULTITHREAD_RULES.md). It must not be
presented as fully verified by this compiler: its partial support and proof of
execution are followed in the matrix.

The features of several methods remain out of scope for the moment. Their absence
does not require a final decision on their subsequent addition.

**S3 — Appels.** Each function call creates a scope activation whose
parent is the calling scope, regardless of where the function is declared. Each
recursive call has its own activation.

**S4 — Buckles and branches.** Each iteration and branch block has
The transfer and cleaning rules apply to this.

**S5 — Early exits.** `return`, `break` and `continue` close the telescopes
Indeed left, from the most internal to the most external, with their transfer and
cleaning balance.

The prototype now implements `loop { ... }`, `while condition { ... }`,
`break;` and `continue;`. Each iteration
Close his scope before the next one. `break` cleans the crossed telescopes up to
Iteration, without closing the parent; it targets the loop closest to the current
function. The recovery states are analyzed until stabilization,
and exit status `break` determine the access available after the
boucle. `continue` cleans the lost telescopes and then resumes the next one
Iteration of the same loop. His paths participate in the analysis of recovery.
The borrowings used at the next iteration remain protective.

`return` retains its effect on the entire function. A loop without output
normal does not produce a fictitious continuation. `for`
and user labels remain delayed.
`*data` copy the Int content of an allocation or loan in accordance with
access restrictions. See [LOOPS.md](LOOPS.md).

`while` test its condition before each iteration, including before the first.
`continue` The test and the body share the iteration scope:
the temporary test is cleaned even when its condition is false.
The state after the loop gathers the outputs `break` and false test outputs,
conditions have the same format as those of `if`
and their operands are evaluated from left to right. See [WHILE.md](WHILE.md).

**S5a — Loop result.** Seul `loop` can provide a result.
`break` which reaches its receiver provides a value of the same type and of the same
mode. `break <- objet;` moves an allocation from a left scope, without changing
The pool and outbuildings must survive in the destination. The provenances, targets
and parents of possible reborrowings are
at the junction. A direct loan is written `break &objet;` ou
`break &mut objet;`, and an explicit reborrowing `break &mut *writer;`.
The reborrowing protects the parent until his last use.
receveur accepte `break <- objet;` with a warning.
then has no effect, and the ordinary cleaning applies. `break`
Targets his closest loop. `continue` does not provide any results.
Un `return` exits the function and cancels the current reception.

**S5b — Early propagation with `?`.**
`expression?` is a postfix operator on `Result` and `Option`. It
evaluates its operand once. Postfix operators compose in source order,
so `expression.await?` applies `?` to the value produced by `.await`.

- For an operand of type `Result<T, Inner>`, the enclosing callable
  must return `Result<U, Outer>`. `Ok(value)` yields `value` of type
  `T` and execution continues. `Err(error)` returns from the enclosing
  callable. When `Inner` and `Outer` are the same type, the return value
  is `Err(error)`. When they differ, the compiler checks that the
  associated function `Outer::from` is accessible at the call site and
  has the exact signature `Outer::from(Inner) -> Outer`. It resolves
  the call at compile time and reports a type error if this requirement
  fails. Only the error path calls the function, then returns
  `Err(Outer::from(error))`.
- For an operand of type `Option<T>`, the enclosing callable must
  return `Option<U>`. `Some(value)` yields `value` of type `T` and
  execution continues. `None` returns `None` immediately.

The success types `T` and `U` may differ. Propagation uses the same
scope cleanup and ownership rules as an explicit `return`.

A type can declare one associated `from` per source type. Each
overload takes a single parameter and returns the type that declares
it. The compiler rejects two declarations with the same source type,
including across separate `impl` blocks. Both `?` and an explicit
`Outer::from(value)` select the overload by the exact source type.
With multiple overloads, an untyped numeric literal uses the
language's default numeric type. A type annotation or explicit
conversion can select a different overload.

**S6 — Prototype entry point.** `fn main()` without parameter is the point
- A return `Void` gives a zero output code; a return
`Int` provides the output code. Resources are cleaned before return.
`main` With this entry point, only the
statements of functions and enums are accepted at the program level.
The old script mode without `fn main` is retained for existing examples.

<a id="2-valeurs-allocations-et-initialisation"></a>

## 2. Values, allocations and initialization

The [scratch 07](../design-buffer/07-conversions-resultats-copies-et-vues.md#types-primitifs-du-noyau)
sets the primitive numerical and logical of the target kernel.
historiques utilisent `Int` for the 32-bit signed integer of the prototype.
The name retained in the target kernel is `i32`.

**V1 — Local values and pool allocations.** A local structure is
built with `T { champ: valeur }` and remains of type `T`. Comme un tableau
local, it can be transferred with `<-`. A construction `pool.new(...)`
produit un `A<T>` which keeps its origin and address. A transfer
between telescopes does not change the type or storage of a `A<T>`.

**V2 — Full initialization.** `new` produces a value entirely
initialized. Each required field must be given a given value or a default value
defined by its type. A mandatory reference is provided to the creation; an incomplete
object is not created to inform it afterwards.

```text
let mut buffer = new Buffer;
let mut writer = new Writer { buffer: &buffer };
```

### EN1 — Conditional enum patterns and equality

`if let Pattern = expression { ... }` accepts the enum patterns of `match`,
including positional and named fields, Option and Result. It evaluates the
expression once. Pattern bindings exist only in the matching branch. An optional
`else` (including `else if let`) handles the other variants; omission means no
operation on a non-match. As an expression, all continuing branches must provide
the same result type, and an omitted else cannot provide a non-unit result.

Scrutinee ownership follows V3 and the existing match rules: an eligible enum
is copied; a move-only enum moves; an explicit borrow keeps the dependency on
the original value. Unmatched owned payloads are cleaned up, including before
an early exit from the else branch. A matched borrowed field cannot outlive its
target. No new implicit borrowing is introduced.

For enums whose variants are empty or contain only direct primitive fields,
`==` and `!=` compare the variant first, then the active fields using their
primitive equality. Both operands must have the same enum type. Different
variants are unequal. Each operand is evaluated once, in left-to-right order;
inactive fields and representation padding are never compared. Floating fields
retain primitive floating equality, including NaN behavior. No ordering operators
or recursive aggregate equality are introduced.

**V3 — Implicit primitive and primitive-payload enum copies.** The types `i32`, `i64`, `u8`, `u16`,
`u32`, `u64`, `usize`, `bool`, `f32` and `f64` copy when read by value.
Declarations, reassignment, arguments and returns leave the source binding
available. A primitive used to initialize a field or element is copied too.
`copy(x)` remains an optional explicit spelling for primitives and eligible enums.

An enum copies implicitly by value if every variant is empty or contains only
direct primitive fields. This depends on its complete definition, not its
current variant, and applies to eligible Option and Result instantiations too.
Structs, arrays and tuples retain their move rules even with primitive fields.
An enum containing a reference, allocation, struct, array, tuple or nested enum
payload remains move-only. This change does not implicitly copy references or duplicate
`A<T>` allocations. Existing capture rules are retained. Special `drop(x)` and
explicit scope-transfer directives retain their effects; destroyed bindings
remain unusable. Copies of an addr-derived `usize` retain its provenance and
remain confined to the original `@unchecked` block.

```rust
let a: i64 = 12;
let b = a;         // Copies a; a remains available.
let c = copy(a);   // The same copy, written explicitly.
let view = &a;    // Explicit borrowing is distinct from copying.
```

**V4 — Declarations, transfers and reallocations.** A declaration uses
`let name = expression` ; `let mut name = expression` authorizes the entries
on this variable. `var` The initialization is complete.
Direct access to an allowance or scalar is immutable by default:
modify or form `&mut name` exige `let mut`.

The mutability of the variable is distinct from that of the reference:
`let view = &mut data` permet `view.set(20)` without allowing the reallocation of `view`.
`let mut view = &data` allows to reallocate the reference according to the expressions
supported, but does not allow to modify its target while reading. Immutability is
that of the named access; it does not prohibit a move
to a new mutable receiver or its consumption by `drop(-> name)`.

For an Intmutable Allowance, `name = 20` and `name.set(20)` modify its
content, without new allocation, change of address, reception, transfer
destruction. The right-hand side of the `=` can be a scalar expression
The target must still be alive and accessible after writing, and the necessary
borrowings after writing remain protective. A mutable scalar is changed in place
according to the same rights. A reference does not implicitly dereference in
`view = 20` This reassignment changes its mode of operation.
his target goes through `view.set(20)`, subject to a &mut Int type.
The prototype accepts a signed Int letter to `.set(...)`.

If the right hand side provides an allowance, it is instead a replacement. The
right-hand expression is fully evaluated before destroying the old allowance and
installing the new access in the mutable variable. A borrow from the old allowance
can be used for the last time in this expression; a borrow to be used again will then
be refused reassignment. The old allowance is not destroyed again at the end of the
scope or by a subsequent reset.

A replacement requires that access to the receiver be valid on all paths that reach
the beginning of the assignment. A path that leaves the function before this
assignment is excluded. This condition is added to the checks on the effects of the
right side.

If the term has already consumed or destroyed the old allocation, the compiler
If she returns exactly the same allowance,
by moving or transferring round trip, this allowance remains alive.
Reassigning a loan does not destroy the object it refers to; reallocating a loan to another
scalaire copiable remplace simplement sa valeur.

The new allowance retains its own source, even if it differs from that of the old
one. A replacement allowance can therefore coexist briefly with the old one: the
capacity of the pool must allow it. A failure of allocation stops the prototype
before this destruction, according to E1. This decision replaces the delayed cleaning
initially chosen for the old one.
The contract is detailed in [REASSIGNMENT.md](REASSIGNMENT.md).

**V5 — Adresse stable.** An allowance keeps his address for his life,
Once your life is over, your location can be reused. Move access between variables
does not move bytes.

<a id="3-déplacements-et-transferts"></a>

## 3. Travel and transfers

For modern syntax, the [sweet 02](../design-buffer/02-marqueur-transfert.md)
sets the rating of the value movements and catches. By-value use copies primitives and eligible enums under V3; other values move. The receiver of a block result
is visible and the original access does not react. `move a;` transfer
A connection to the entrance to the child block. `move { ... }` value capture
The life, identity, borrowing and cleaning checks of this section also apply to these
forms.

Examples with transfer arrows below describe the historical syntax, which is still
accepted for compatibility.

**T1 — Intention explicite.** An assignment does not implicitly transfer a
The intention is expressed by the operators of the
The arrows are either moving/transferling or borrowing. `->` and `<-` restent
the rating of transfers. `>` and `<` - I'm not.

**T2 — Move in the same scope.** `let mut b = <- a` moves access to `a`
To `b`. `a` The allocation and its place are unusable.
in the order of destruction do not change.

**T3 — Transfert montant.** `<- value` indicates a transfer to the parent
This marking does not render the allocation unusable in its creation scope before the
release, subject to borrowing rules and other explicit movements.

**T4 — Transfert descendant.** `-> value` transfers to the direct child scope,
with effect at its entry. `value ->;` exprime ce transfert.
The parser also keeps the initial writing `-> value;`. The source scope cannot then reuse the allocation
if a return transfer makes it available again.

**T5 — Niveaux successifs.** Reaching an ancestor or a further descendant
requires to cross intermediate levels. Physically predicting storage in a sustainable
area does not remove these semantic steps.

**T6 — Return and receipt.** A value leaving a block expression must be
be returned and received explicitly in the parent. An implicit final return
the Rust is allowed; `return <- value` is the explicit form. A function
`fn creer() -> <- Point` can make a local structure with
`return <- point`. The recipient obtains a `Point` and D1 applies.

The `<-` final of a block or branch with receiver is written without semicolon.
`<- objet;` is a marking at the end of the block and does not provide a value of
A transfer attempt without receiver issues a warning and leaves the allocation
attached to its scope.

A reception in a new variable does not reactivate the old access moved to the child.
In an ordinary block without a new recipient, the return of an imported allowance
restores its initial access to the parent. This avoids creating two direct accesses
usable to the same allowance.

```text
let mut result = {
    let mut data = new Data;
    <- data
};
process(&result);
```

The compact shape `let <- y = new Data` expresses the intention to transfer from
the statement. It does not give the name `y` visible in the parent: a return
and a receiver remains necessary. The final return may then be `y`.

**T7 — Assignments to an ancestor.** A receiver located in an ancestor
determines the destination required; the change of connection must remain explicit.
The first proposal for an automatic promotion by assignment has been replaced by this
explicit operator requirement.

**T8 — Reuse after downward transfer.** A transfer of allowance
to a child may only be reused after the child has returned
guaranteed on all paths that reach this use. `if`
being themselves telescopes, `<-` in such a block does not jump his direct parent.

**T9 — Jonction conditionnelle.** Access is usable after a `if` seulement
if it remains valid on all paths that reach this use.
which make `return` are excluded from this continuation, but their effects remain
A living allowance on some paths only remains followed for its cleanup, without
reactivating its old access. Re-use of its address does not reactivate its cleanup.

The prototype implements the instructions `if / else`, Int comparisons,
Literal conditions `true`/`false`, Void/scalar returns and
Transfer-to-return transfers to compatible receiving order. Conditional returns of
allowances are now allowed if all paths explicitly return an allocation of the
declared type. Actual sources may differ: the result is the union of their possible
sources. Two separate pools remain two sources; variants of the same enum pool share
its public source. Each possible source must be fairly durable for the transfer.

The chosen allowance is transferred without copy, the other allowances of the path
performed are cleaned, and the recipient then ensures its sole destruction. The
compiler retains the effects of each path at the appellant.
is detailed in [CONDITIONAL_RETURNS.md](CONDITIONAL_RETURNS.md).

The prototype still refuses incompatible reception orders. General Bool conditions
remain to be extended. The prototype follows the reassignments
explicit receivers on branches of an ancestor `if` continuing,
with T7, V4 and L3 controls. See [CONDITIONALS.md](CONDITIONALS.md).

**T10 — If with receiver.** An expression `if / else` may provide an allowance
Each branch that continues provides the same type and the same
mode. An allowance requires `<- allocation`, without semicolon.
Integrable can be provided directly. Possible sources are gathered. `else` is mandatory; `else if` is
The temporary members of the branch are cleaned and the selected allowance is
received in the parent without copying or changing the address.

The `<-` final provides the branch value without leaving the function.
`return` explicit exits the function and excludes this path from receiving
the expression. The borrowed results remain outside this step. An old displaced
access is not reactivated by receiving in a new variable. The receiver must have
explicit use, like other results
See [IF_EXPRESSIONS.md](IF_EXPRESSIONS.md).

**T11 — Provenances multiples.** An allocated result may depend on several
As long as future use of the result or borrowing is necessary, each possible source
is protected from an incompatible reset. Cleaning uses the actual source of the
object; an authorized reset from one source does not destroy the object if it depends
on another. The potentially destroyed access is invalidated.
and the monitoring of the cleaning of survivors is preserved. `source.drop`
requires a single source equal to that source; `drop` uses provenance
See [PROVENANCES.md](PROVENANCES.md).

<a id="4-vérification-dusage-et-dépendances"></a>

## 4. Use verification and dependencies

**U1 — Result used.** A result received must be explicitly used
A conditional use is sufficient. A result without any explicit use is rejected in the
compilation.

Draft 01 and draft 07 specify that any result that is bankrupt, with or without an
allowance, requires explicit use: treatment, transmission or
`drop(-> expression)`. The expression alone followed by `;`, `let _ = ...` and
a link never used is refused, regardless of the variant
connue. `Err(_)` can ignore a detail error without proprietary value.
The entire type of result that may have an allowance also requires this use:
reception, transmission, consuming match or drop. A received proprietary link must be
read, borrowed, transferred or destroyed explicitly
at least on a possible path; a prefix `_` do not exempt from this rule.
After the last use, the ordinary range cleaning continues to apply.


This verification is in addition to the transfer: it does not render the life of the transfer
The initial proposal
"transfer without unused effect" has been replaced by this error of
compilation.

**D1 — Sustainability of targets without implicit promotion.** Transfer a value
does not transfer the allowances that she borrows and does not prolong their lives.
At each child border → parent, all the targets borrowed must already be alive and
connected to the destination or one of her ancestors. Otherwise, the transfer is
refused, even if their pools survive at the border.

This decision replaces the previous proposal where local dependencies automatically
accompanied the value. This promotion is not a deferred feature: it is prohibited.
The same control applies separately to each successive transfer, without a shortcut
to an ancestor.

**D2 — Sense of the graph.** An allowance does not survive only because it
The analysis follows dependencies from the values that come out to verify their
validity, without changing the attachment or life span of the referenced targets.

**D3 — Analyse conservative.** If a reference can be used `x` ou `y` based on a
The analysis does not distinguish the path performed, the two possible dependencies
are retained. Static accessibility can therefore retain more allocations than the
actual accessibility of one execution. This retention concerns the targets and
constraints of the analysis: it does not prolong their lives and does not promote
them in another scope. D1 applies to each possible target.

**D4 — Valid references.** No transfer, transfer or cleaning accepted
must allow access to destroyed value or invalidated storage. A situation whose
security cannot be established is rejected.

Dependencies on an allocator follow the specific rules of the section
7: they never authorize the implicit transfer.

<a id="5-emprunts-et-fonctions"></a>

## 5. Borrowing and functions

**B1 — Reading and mutation.** `&T` grants read access and `&mut T` grants
mutation permission without implicit uniqueness. MA1–MA6 govern coexistence,
synchronization of potentially concurrent conflicting accesses, and validity
dependencies.

**B2 — End of borrowing.** Last use can end a borrow dependency before block
exit. It does not end another active branch or a through-result lock contract
whose release depends on destruction.

**B3 — Borrowing and displacement.** For the prototype, a move is prohibited
as long as a loan is still to be used.

**B4 — Explicit parameters.** Signature and call indicate the mode of passage:

```text
fn inspect(buffer: &Buffer) { /* ... */ }
fn modify(buffer: &mut Buffer) { /* ... */ }
fn consume(mut buffer: -> Buffer) { /* ... */ }
fn count(value: Int) { /* ... */ }

inspect(&buffer);
modify(&mut buffer);
consume(-> buffer);
count(42);
```

A parameter without an indication of borrowing or transfer is allowed only for a
build-in type or for a table value provided according to E5. Passing a reference does
not transfer the allowance.

Parameters are also unchangeable variables by default.
`fn edit(mut data: -> Int)` allows to modify the direct access received by transfer;
`fn edit(mut n: Int)` allows to re-allocate its scalar copy. Receive a
allocation of immutable access by transfer remains possible: its mutability
local depends on the recipient parameter. `data: &mut Int` peut modifier
its target without `mut data`, since the right of writing comes from the type of reference.
`mut data: &Int` Don't grant that right.


On appeal, a loan is created from an allowance with `inspect(&data)` ou
`modify(&mut data)`. Si `view` is already a loan, we pass it by his name:
`inspect(view)` ; a function result already borrowed occurs directly,
comme `inspect(borrow(&data))`. Mode remains declared in the signature.
This passage does not transfer or copy the allocation. A mutable reference retains
its write permission and dependencies across calls. Coexisting accesses follow
MA1–MA6; a call does not imply uniqueness or automatic suspension of every alias.

`&view` adds a reference level; it is not a shortcut to its target.
The types of nested references are allowed, for example `&&mut i64`
and `&mut &mut i64`. Each level keeps its mode and life.
Writing across several levels requires mutable access to each level crossed.
The same distinction applies to pool parameters: `create(&mut pool)`
from a local source, then `create(memory)` si `memory` is already a parameter
`&mut Pool<Int>`. A reading pool loan never becomes mutable.
This rule of pass/return by name does not allow for an allocation shift without
operator or for general assignments between reference variables.
Voir [REFERENCE_VALUES.md](REFERENCE_VALUES.md).


**B4a — Expressions and order of arguments.** The arguments are assessed by
left to right, each expression ending before the next. A scalar result is copied into
a temporary before evaluating the next argument. The nested calls follow the same
order. The external call begins only after preparing all of its arguments.

A loan used only by a sub-call can end before the argument
suivant : `consume(read(&data), -> data)` is allowed if no other borrowing is permitted
a transfer immediately invalidates the old access:
a subsequent argument cannot use this access anymore.

A borrow provided directly to the external call remains active during the following
arguments and the call. The same applies to borrowings from sources. An allowance
prepared for being transferred must remain alive until it enters the function; a
reset in a subsequent argument cannot destroy it.

The expressions producing allowances retain an explicit mode:
`consume(-> new(memory) Int(42))`, `consume(-> create(&mut memory))` ou
`inspect(&create(&mut memory))`A temporary allowance borrowed remains
attached to the calling scope until it is cleaned or an authorized reset. Sources
must always be reported and passed by a named borrow.
The contract and the translation into C are described in [ARGUMENTS.md](ARGUMENTS.md).

**B4b — Inferred summaries of source effects.** The benefits and benefits are
Deducted from explicit operations and sub-calls, without annotations added. The
sources of the parameters are symbolic; their effects are substituted for calls.
Local effects are not attributed to an external parameter of the same name. A
conditional reset is a possible effect. The types that a source must be able to
allocate are preserved, even for temporary unreturned ones.

The prototype infers these summaries for all functions, including those not called,
and uses them for C cleaning captures and call storage requirements. Identifiers,
lifespans and results types are
controlled with symbolic inputs and then real calls. See [EFFECTS.md](EFFECTS.md).

**B4c — Inferred summaries of results allocated.** The compiler distinguishes between the
The summary retains the alternatives of each normal return and replaces those of the
sub-calls. A return of the same entry on all returns retains its identity; a
selection does not promise the identity of a particular candidate. The source of a
new object is symbolic, without annotation of provenance.

At calls, real sources and origins must respect this summary. A slot reused by a new
allocation does not satisfy an identity restitution, even with equal address. Old
moved references are not reactivated by receiving in another name. The addresses of
living objects remain fixed.
Controls on actual calls remain active. See [RESULTS.md](RESULTS.md).

An allocated result may contain &Int or &mut Int fields using loaned allocations in
the call. At each child border → parent, the targets must be alive and already
attached to the destination or one of its ancestors. The contract retains the
identity of these targets, directly from a borrowed Int parameter or from a field of
a received object. The borrow protects
future uses of the result after the return. A passage through `->` d'un Int
does not provide this guarantee: its connection goes down into the child. Automatic
promotion of a local target is prohibited by D1.
[BORROWED_RETURNS.md](BORROWED_RETURNS.md).

**B4d — Inferred constraints between sources.** Destruction
`source.drop(-> value)` demands equality of source and all provenances
Access to a value created or received before the reset of a source requires that its
sources be distinct from that source. Reading and copying a scalar before the reset
does not require this distinction for copying.

These obligations are deducted from the body and sub-calls, without annotations. The
loop branches and loop covers are taken into account. A living result follows its
reception history; future uses and prepared arguments remain protected. Each call
checks relations with sources
actual before emission of body C. See [SOURCE_CONSTRAINTS.md](SOURCE_CONSTRAINTS.md).

**B4e — Verification of bodies without real call.** The compiler applies the
existing rules of displacement, borrowing and output of telescopes to each body with
symbolic inputs. The parameters retain their type and mode; the storage identities
respect the inferred equities of sources. An unused function can therefore be refused
for use after destruction or incompatible borrowings. It is not issued in the final
C.

Controls on real calls remain active, especially for concrete sources and storage
compatibilitys. This passage reuses the block verifier and applies subcall contracts
without opening their bodies. The backend still travels the bodies to produce the
specialized C. See
[FUNCTION_BODIES.md](FUNCTION_BODIES.md) and [MODULAR_CALLS.md](MODULAR_CALLS.md).

**B5 — Returned loans.** A function can return a loan if the
compiler establishes that its target remains valid for all its uses.
This loan extends the corresponding access restrictions. `<-`
is not necessary when no allowance is transferred. Returning a reference to a local
variable destroyed upon return is prohibited.

The prototype implements `fn borrow(data: &Int) -> &Int { return data; }`.
The result is explicitly received without `<-`and does not create any allowances.
`return data` renvoie l'emprunt existant ; `return &data` would create a level
and is refused in this prototype. A mutable parameter can be
provide read access promised by `-> &Int`, without creating a mutable access
The restrictions of the mutable parent remain followed.
Contracts infer the identities of targets injected by `&` ou `&mut` and
A conditional return retains all possible targets. Each exited border applies D1: the
targets are already alive and attached to the parent or an ancestor, without
promotion.
A target created locally or received by `->` cannot therefore be taken out by borrowing.
The returned borrow preserves every target dependency until its last use.
Invalidating movement, drop and historical reset remain constrained by N4; content
mutation and concurrent accesses follow MA1–MA6. It remains readable, even if its original parameter is
mutable. &mut Int returns are now also implemented:

```rust
fn borrow_mut(data: &mut Int) -> &mut Int {
    return data;
}

let mut memory = Pool<Int>::new(1);
let mut nombre = new(memory) Int(10);
let mut vue = borrow_mut(&mut nombre);
vue.set(30);
nombre = 40; // Après le dernier usage de vue.
```

A mutable result retains write permission and its target dependencies after the
call. A reborrow carries those dependencies without automatically excluding the
parent reference. Sequential content accesses may coexist; storage invalidation
and concurrent access remain subject to the lifetime and synchronization proofs
of MA1–MA6. Successive calls preserve every relevant dependency chain.

A &mut Int result requires a provenance from &mut Int parameters. An &Int input does
not become mutable because its variable is declared mut. Local or transfer targets
remain unsustainable on return, even with a sustainable storage source. Conditional
returns retain all possible targets and their validity/synchronization obligations. There
is no allocation, destruction, receipt of property, or byte displacement when
returning this borrow. The existing name is used without & added. Returns to other
types remain out of the prototype. See
[DIRECT_BORROW_RETURNS.md](DIRECT_BORROW_RETURNS.md) and
[MUTABLE_BORROW_RETURNS.md](MUTABLE_BORROW_RETURNS.md).


<a id="6-destruction-et-récupération-du-stockage"></a>

## 6. Destruction and recovery of storage

[Destructor method](DROP.md#destructor-method) defines `fn drop(&mut self)` for declared types.

**L1 — Order of steps.** The destroyer performs before recovery of the
The value remains valid during its destroyer.

**L2 — Nettoyage automatique.** When a scope is closed, the allocations
The allowances transferred are cleaned in their final destination scope.

**L3 — Ordre retenu.** The dependencies necessary for cleaning require
The default order for independent values remains the opposite of the creation or
receipt. A transferred group retains its internal relative order within the limits of
these dependencies. The physical order is distinct.

**L4 — Access of the destroyers.** A target read by a destroyer remains alive
A stored reference that the destroyer does not read does not add a cleaning
dependency. Its target always respects D1. The compiler refuses the constraints that
prevent any safe order.

**L5 — Optimized early release.** A compiler mode can clean
earlier if it proves the preservation of observable, destructive behavior
The absence of future ordinary use alone is not sufficient.

**L6 — Destruction explicite.** Developer can ask for destruction
anticipée par un déplacement explicite vers `drop` :

```rust
drop(-> data);
```

This operation also ends the life of a local link, including when its value is
copyable. Borrowing controls apply.
`drop(-> expression)` evaluates the expression first, then consumes its result
A result that is bankrupt without allocation does not require a pool slot for this
operation.

For a `A<T>`, the compiler uses its provenance to return its slot
the original pool after the destroyer. Subsequent access required by a borrow or
other destroyer prevents consumption. The cleaning of the end of the scope ignores a
value already consumed.

The semantics chosen follow that of Rust: `drop` consumption by displacement and
The following conditions apply:
The loan must still be used, the move to `drop` is refused.
the last use of this loan, `drop` is authorized. After consumption,
Reuse of the displaced access is refused. `drop` is no exception
to invalidate borrowings still in use.

**L7 — Dead object and reserved storage.** Data stack recovers suffix
Free from the cursor. An inside hole is recovered when it joins this suffix. A free
pool slot can be reused inside the pool via its free slot index. The destruction
precedes recovery and ends permanently access to the value.

The addition of L6 replaces the old "destruction only at the end" restriction
The automatic cleaning remains the default behavior.

<a id="7-pools-typés"></a>

## 7. Typed pools

**A1 — Explicit storage source.** `Pool<T>::new(n)` creates a pool with an
explicit, strictly positive capacity. A local pool used for allocation requires
`let mut`; a function that allocates receives `&mut Pool<T>`. Its right to
mutate comes from that borrow. The datastack is not a public type and has no
public constructor. Consuming an `A<T>` uses the provenance it carries.

**A1a — Ordinary construction syntax.** `Pool<T>::new(capacity)` constructs
pool storage. It replaces the former lowercase contextual constructor; old
`pool<T>(capacity)` syntax is rejected by corboc. `Pool` is also exported by
`std`, including through normal import aliases.

**A1b — Recoverable slot exhaustion.** `pool.try(...)` accepts the same
initializers as `pool.new(...)` and returns `Result<A<T>, PoolError>`.
`PoolError.Full` reports that the selected slot set (enum arm, where applicable)
is full. `pool.new(...)` retains its terminating failure behavior.
An explicitly supplied value is evaluated once before attempting the claim.
Its ordinary move occurs regardless of success. On failure the supplied value
is destroyed exactly once before returning the error; it is not returned to its
former binding. Success transfers its cleanup to the allocation. A stored
successful Result retains the allocation's source-pool and field dependencies.
Dropping that Result cleans the allocation, as extracting its success would.
These operations do not promise recovery from OS/datastack reservation failure.

**A2 — Storage dependency.** An allowance cannot survive his pool.

**A3 — Aucun prolongement implicite.** Pool remains attached to its scope
de création et se passe par emprunt. Un transfert de `A<T>` est rejeté si
the original pool does not survive the recipient.

**A4 — Reuse.** Living allowances do not prevent new
The dependency on the pool is distinct from the mutable borrow which allows for an
allowance.

**A5 — Former collective reset, removed from the API covered by PR1.**
The following text describes the historical implementation to migrate, not an operation
The next prototype is selected.](ASYNC_MULTITHREAD_RULES.md#6-retrait-de-reset-du-prototype).

Historiquement, `source.reset()` demande
The compiler refuses the operation if access to these allowances is still to be used,
either directly or by borrowing. It invalidates the destroyed access and avoids its
subsequent destruction at the end of the period.
The benefits already consumed by the `drop` are ignored.

Active scopes are cleaned from deep to outer, and each scope follows the reverse
order of creation/receiving, selecting only allocations from this source. Allocations
from other sources remain valid. Destroyers must finish before the storage reset. For
a pool, once the destructions are completed, collective recovery returns the cursor
of each affected stack to zero and emptys its slot index.

The effect follows the actual source through the calls: receive `&mut Allocator`
ou `&mut Pool<T>` authorizes such collective destruction, including allowances
The function summary indicates this potential reset; the specialized audit controls
use and destruction on appeal and refuses future use in the duties as at the
appellant.
`&Allocator` ou `&Pool<T>` does not allow reset of the source.

This decision replaces the previous restriction requiring that all allowances be
already destroyed.
Still no destruction: this is the explicit call to `reset` who asks for it.
The contract and its translation into C are detailed in [RESET.md](RESET.md).

**A6 — End of life of the pool.** The remaining allowances are destroyed before
the closure of the pool and invalidation of its storage.

<a id="8-data-stacks-et-politique-de-placement"></a>

## 8. Data stacks and investment policy

The following are the orientation for storage: The complete placement algorithm and
its acceptance criteria remain to be defined.
L’extension normative [GROWING_REGIONS.md](GROWING_REGIONS.md), G1–G12,
defines the classic data stack, the region data stack, the one-way sliders and the
recovery after cleaning.
[Report of the regions](cycles/GROWING_REGIONS_CYCLE.md) described implementation
historique.

**P1 — Plusieurs plages virtuelles.** The reservation and commitment follow the
Goose model: large virtual ranges, pages made available on demand according to the
platform, stable addresses, end-of-range protection and overrun stop. This does not
mean immediately reserve as many RAMs.

**P2 — Configuration locale.** G2 sets the dimensioning at level
For the growing regions, G6/G7 retained a
annotation before the scope, e.g. `#(stack_region: max_size=4M, count=8)`,
inherited by his children and replaced locally. `max_size` sets the limit
of each region. `count`, optional, sets the number of locations
Each region retains its limit when transferring.
G6 defines multiple binarys `K`, `M` and `G`.

**P3 — Early placement.** The compiler follows the transfers of a
It can build it directly in a reserved location in the scope that will ensure its
cleanup. Exclusive paths can share the location of the same receiver. Successive
transfers preserve the address. Reservation alone does not construct any value and
trigger any destroyers. The placement preserves the order of the initialization
effects. For fixed sizes, last stacking the destroyed values first is an optimization
independent of the validity.

**P4 — Curve recovery.** After cleaning, the scope range
The values transferred already reside in a range that survives this retreat. No step
back makes the location of a living value reusable.

**P5 — Single-way cutters.** The classic data stack, the data
Each region has a regional stack, according to G3/G4. Allocations take into account
the boundary and alignment. The cursor moves back when recovering.

**P6 — Population vivante.** The criterion studied is the maximum number
A loop of unknown length may have a known living population boundary. A known
boundary alone does not demonstrate the compatibility of growth and life spans within
a range.

**P7 — Fallback local.** Where the static placement is not suitable, a
The local allocator explicitly provided can take over. This changes the strategy of
storage, not guarantees of borrowing, transfer and cleaning. This remedy is an
explicit choice of the programmer, never a silent substitution made by the compiler
to a data stack source.

G9 adds an internal recourse to a dedicated region data stack when the current region
stack does not allow placement. This does not constitute a fallback hidden to the
heap and does not allow to exceed an explicitly configured region limit.

**P8 — Typed pools.** A pool of type `T` accept only allowances from
For a fixed concrete type, its slots have a size and alignment
adapted to `T`. The choice for the enums is specified in P9: only one
public interface manages separate stacks per variant, rather than a uniform slot
sized for the larger variant.

The compiler places the pool area on a data stack. The pool manages slots within this
area with its available cursor and slot index. It moves the cursor as long as the
ability allows, then re-uses a free slot at the limit. Destroying an inner object
makes its slot reusable without moving others. A dead suffix is removed from the free
index before recovery by slider retreat. The physical order of the slots is distinct
from the semantic destruction order defined in L3.

In the prototype, `Pool<Int>::new(n)` reserves a strict capacity to `n` slots in
a virtual range, with a single cursor and an intrusive list of slots
Free. The parameter `&mut Pool<Int>` demands this
The pool is exhausted and the program is stopped with a diagnosis.
Reusing a slot preserves the end of life of the previous object.

Pools are a specialized implementation of a storage source, not a replacement of the
rules of borrowing, transfer, destruction and validity of the allocator. No pool is
implicitly chosen.

**P9 — Pool d'enum.** Un seul `Pool<E>` manages a data stack dedicated to each
variant of `E`. Each stack has slots adapted to its variant, cursor and
The pool interface selects the stack according to the built or destroyed variant.
Living values keep their address. The source of all variants remains the original
public pool.

In the prototype, `Pool<E>::new(n)` reservation `n` slots per variant. Enums are
have fields `Int`, `&Int` ou `&mut Int` fully initialised,
and are built only via a pool of the corresponding type. A reference points to the
slot, whose stack provides the discriminant. The functions can borrow, receive and
return these allowances with the operators
explicites existants. Le `match &value` est exhaustif. Les champs scalaires
are copied and the subject remains protected by a loan shared during the arm.
In a `match &value`, local constructions can
Calling functions subject to respecting this borrowing. Loop conditions and outputs
apply the usual cleaning of litters. Alternative replacements in place are not
supported.

Fields `&Int` are a first step in the storage of references: they
are immutable after construction and require a named loan to an allowance
Int. On fournit `field: &data` from an allowance, or `field: view` si
`view` is already an Int loan; none `&` Their addictions are flattened.
retain target dependencies against invalidating movement, destruction and
historical reset while the object or a borrow to it still needs the target.
Content mutation follows MA1–MA6. `match`
The prototype accepts their block transfer only if the targets are already long
enough in the destination, according to D1. The fields to other enums remain delayed.
Returns of functions containing these fields are allowed with the same child check →
parent; their contracts transmit the targets to the callers. A stored shared reborrow
retains dependencies and grants read permission through that field, without
creating mutable permission or automatically suspending parent content access. See [REFERENCE_FIELDS.md](REFERENCE_FIELDS.md)
and [BORROWED_RETURNS.md](BORROWED_RETURNS.md).

Fields `&mut Int` They also require a mutable capacity:
`field: &mut data` from a transferable allowance, or `field: view` si `view`
is already a mutable borrow Int. A read reference does not become mutable by its
storage. The field retains its reference after construction.

The object retains each possible target dependency and its field's write
permission. Moving or returning it preserves those obligations; D1 still applies
at every child-to-parent boundary without implicit target promotion. Multiple
references can coexist under MA1–MA6. `match &value` grants read projections.

`match &mut value` requires write permission to the carrier. Mutable projections
retain the carrier/place dependencies needed to keep their targets valid. Content
access does not automatically exclude other references. Structural replacement,
destruction and concurrent access must satisfy MA1–MA6; the end of an arm does not
end a dependency retained by a result escaping that arm.

The arms allow readings of the play match and `.set()` on the
mutable projections. They also admit calls `Void` of which the arguments
The mode of the parameters follow B4. A local arm statement can receive the result of
a call
`Int` The copied Int remains independent of the scriptures
and its connection is limited to its block.
A statement `let mut autre = reemprunter(vue)` peut aussi recevoir
un `&mut Int`. `vue` and `autre` retain permissions and dependencies under
MA1–MA6; their coexistence does not itself suspend content access through `vue`.
The holder remains protected against invalidation while required. After a Void or Int call, the
arm can re-use its projections upon return. The carrier's reservation covers the
whole call and the rest of the arm.
In an expression `match` by borrowing, one call `Void` peut aussi
receive the other arguments allowed by B4. An assignment in an arm follows the usual
transfer and replacement rules, whether the match provides a result or an
instruction.
the recipient's condition takes into account each continuing arm. `break`,
un `continue` ou un `return` follows the corresponding output path and
cleans the crossed litters.

A local statement `let mut dehors = match &mut writer { ... };`
Each arm ends with the name of a mutable projection of the bearer or a re-borrowing
derived from it. The verifier requires that the bearer and all possible targets be
alive within the scope of the result. Access to the bearer, its destruction and the
reset of its storage are blocked during the use of the result and its re-borrowings.
After their last use, the bearer is again accessible according to B2.

A function can return this loan if it receives the bearer
in parameter `&mut`. His contract identifies the parameter and fields
When the call is made, the verifier resolves them to the carrier and the actual
targets. The reservation accompanies the result until its last use at the caller,
including through relay functions. The carrier and the targets must survive the
return.

A field can store this result. The uses of the new object keep the reservation of the
field. A re-borrowing via this object keeps the entire chain of the porters. The last
use of the re-borrowing makes the immediate porter accessible. The remaining uses of
this porter continue to protect his own dependencies. At each transfer, the porters
and targets must already live in the destination or one of his ancestors. A
conditional return keeps the union of the porters and possible targets.

For the resets, the contract lowers the source constraints from the order of the
operations in the body and composes those of the sub-calls. If a path can use a
borrow after the reset, its target and the reserved allocations must have separate
sources from the pool reset. The analysis includes returns at the beginning of a
loop. The appellant applies these constraints to the actual allocations. He also
protects the other borrowings that will still have to be used and the arguments
already prepared during the evaluation of the next ones. After a call, a possible
reset invalidates access to the allowances it may have destroyed. Overlapping
possible targets do not themselves prohibit multiple mutable projections. The
compiler must establish validity and compatible actual effects on each path under
MA1–MA6; unresolved required facts still cause rejection.
Voir [MATCH_MUTABLE.md](MATCH_MUTABLE.md).

Un `reset` the pool destroys the living values of all its stacks before
reset them, according to A5. The destruction order defined in L3 remains global to
the scope; it does not become a grouping order by variant.

<a id="9-échecs-et-accès-aux-tableaux"></a>

## 9. Failed and access to tables

**E1 — Failure to provide benefits.** For the first prototype, a failure of allocation
stops the program with a diagnosis; it is not recoverable. The current prototype does
not unfold the destroyers on this stop.

**E2 — Limitations of Tables.** Proven access beyond limits is denied to the
compilation. A valid proven access does not require additional control. In other
cases, an execution control stops the program with a diagnosis in case of overtaking.
The text cut also applies these controls to the UTF-8 borders.
`try_slice` retains these checks but returns a recoverable error:
OutOfBounds for an invalid beach, NotCharBoundary for a cut border. Its result
borrows the original bytes (TX4 and draft 07).

**E3 — Fixed size values.** Length is part of the type `[T; N]`.
The literals evaluate their elements only once from left to right.
`[expression; N]` requires a copyable element and evaluates the expression once,
including zero. `[]` requires a type of context. `len()` on a variable
reads its static length without borrowing or reading its elements.
target, length has type `u64`, including the zero length of an empty table.

**E4 — Indexed places.** Each index is evaluated once.
In the target kernel, any whole type is accepted for the index. The control of the
terminals is based on its original value before conversion.
See [strip 07](../design-buffer/07-conversions-resultats-copies-et-vues.md#indices-et-longueurs).
A scalar reading copies the item. The writing evaluates and controls the destination
before the right-hand value, then checks the rights at the time of writing. A borrow
used for the last time in the right-hand part can end before it. The writing retains
the type of the box.

**E5 — Copies and transfers.** Copy of a table or line is
request with `copy`. A copy per value received as parameter is independent.
The table results that pass through a `return`, un `break` or exit
of a branch with receiver use `<-` explicitly. Each branch that
provides a result retains type and length. Move directly
a box is not allowed. `replace` checks the index, evaluates the new value
then installs it after the required validity/effect checks and returns the old value. `swap` evaluate
the indices from left to right and check them before writing. Two identical and valid
indices give an exchange without effect.

**E6 — Borrowings of tables and boxes.** Borrowing of cells, including
lines, protect the entire original table. `ref()` and `mut_ref()`
equivalent to `&` and `&mut`. `mut()` is excluded from the prototype by decision
A borrow from a temporary copy can be used in the instruction that created it. It
cannot survive it. The last use is followed on loop recovery paths. A borrow
that comes out `break` must have a sustainable target on each exit
The arguments of a call remain in the order of B4a. A direct box borrow remains
active during subsequent argument evaluation and the call. Multiple mutable
borrows are not rejected solely because they refer to the same table; preparation
and actual call effects must preserve their dependencies under MA1–MA6. A function can
return a borrow from a box injected by borrowing if its target and the parents
required are durable according to B5 and D1. Proof of terminals on a path can remove
a check if it still applies to the value used.

**E7 — References stored.** Each box shall retain the source of its
A dynamic index holds the sources of all possible boxes. Copying a shared reference
table keeps the targets and borrowings. A mutable reference table cannot be copied.
A mutable reborrow retains its place and target dependencies. It does not
automatically suspend content access through the stored reference; invalidating
replacement and concurrent access still require the MA1–MA6 proofs. `replace` makes the old reference with its loan
and refuses replacement if an active reborrower blocks it. Ignore the old mutable
reference terminates its borrowing. Any transfer checks D1 for possible targets. A
function contract retains the sources of the references returned by box.

Voir [FIXED_ARRAYS_VALIDATION.md](FIXED_ARRAYS_VALIDATION.md) for
The perimeter and cycle limits are implemented.

## 10. Extension async/multithread retenue, support partiel

The normative rules are grouped in
[ASYNC_MULTITHREAD_RULES.md](ASYNC_MULTITHREAD_RULES.md). The decisions replaced,
The AS7 automatic injection concerns the async states and does not imply the source
of the regular I2/A1/P8 data allocations.

<a id="11-structures-et-méthodes-retenues"></a>

## 11. Structures and methods used

[STRUCTURES_METHODS.md](STRUCTURES_METHODS.md) is part of the normative rules:
ST1–ST18 and ME1–ME4 record the complete construction, the defects deducted,
`pool.new`, `pool.copy`/`copy`, field paths and method recipients.
The intermediate agreements on field movements and partial states have been removed:
they are not features to be implemented. Methods and fields of a type cannot bear the
same name. Custom defects and tags are carried forward. The UTF-8 yard is now
recorded separately. The support includes local and pool structures, explicit copies,
methods and field contracts. The matrix and cycle reports define the types and
compositions actually supported.

### Constants

`const NAME: T = literal;` declares a typed value at module scope. Use
`pub const` to export a module constant. A constant inside `impl Struct`
belongs to the type and is accessed as `Struct::NAME`. It follows the
visibility of the type. The initializer is an integer, float, or boolean
literal. Numeric literals may have a leading minus. The compiler checks the
literal against the declared primitive type and inserts its value at each
use. A constant has no address of its own.

### Closures

The list of parameters of a closure is delimited by bars.
`||` opens a closure without parameter. Each parameter explicitly indicates
his type, as in `|x: i64|`. This marker makes creating an executable value
later visible in the code. An ordinary block `{ ... }` evaluates
Between two operands, `||` retains its sense of OR logic.
The body of a closure is always a block bounded by accolades. Its last expression
provides the result according to the semantics of the blocks.
The type of return may be indicated by `-> Type` After the bars.
In its absence, the compiler infers it from the body. All return paths, including
explicit returns and the final value of the block, must produce the same type. If a
type is declared, each return must correspond to this type.

A closure is an instance of a concrete type generated for its expression. This type
behaves as a structure that contains an internal field by external connection used.
Its body is the method executed by
`f(...)`where `f` is a named affair. An expression
closure in brackets can also be called directly, as
in `(|x: i64| { x * 2 })(21)`. Capture fields are initialized
the creation of the closure.
Without `move`, creating a closure automatically copies the primitive values and
eligible enums (V3) it captures. The outer binding remains available. Each capture is copied once,
when the closure is created. Other value captures require `move`; existing
shared-reference captures retain their dependency on the borrowed target.

The marker `move` applies to the entire closure. It transfers the links
external uses in its fields, according to the meaning of `move` at the entrance
Non-copyable source bindings become unavailable at declaration. Primitive and
eligible enum captures are copied into their fields, even with `move`, and
leave their source available. The closure cleans up the values it owns. The capture syntax does not provide a
list of individual modes.

```rust
fn main() {
    let a: i64 = 10;
    let b: i64 = 20;
    let additionner = move || { a + b };
    print(additionner()); // 30
}
```

Sous `move`a shared reference is transferred to the field of
capture like other values. `let vue = &nombre;`, the
establishment of `move || { *vue }` makes the external link `vue`
The reference retains its target. When a field contains a reference, the closure
carries the dependence of this field on its target, such as an ordinary structure. N4
requires that the target remain valid as long as the closure can use the reference,
including during its cleaning if it depends on it. Move the closure forwards the
reference and its dependence. Destroying the closure terminates the borrowing carried
by the field according to existing rules.

In type position, `fn(...) -> R` describes the signature of a call
The compiler retains the concrete type of its instance, its fields
and their dependencies. `f: fn(...) -> R` received
The case by value according to the ordinary rules of copying and moving.
`f: &fn(...) -> R` and `f: &mut fn(...) -> R` receive a
The prefix of the borrow relates to the closure, and a written borrow after the
termination of the borrow.
`->` The results are the subject of the report.

L’appel `f(...)` uses the instance as a receiver. An appeal that modifies its
or its condition requires a mutable access. With a value passage,
`mut f: fn(...) -> R` makes the received link mutable.
emprunt, `f: &mut fn(...) -> R` provides this access. `mut f` do not
requires no conversion at call point. Catches and call
apply N1 to N8.

<a id="12-utf-8-et-string-retenus-support-partiel"></a>

### Pipeline element types

`Iter` takes a mutable reference to the source, granting write permission and
retaining lifetime dependencies without an implicit uniqueness guarantee. Each `Map` takes ownership of
its predecessor. The instance method `collect(&mut destination)` consumes the
chain and appends its items to the destination vector. It is provided by `Iter`,
`Map`, `Filter`, and `Reduce`; it is not a package-level function.

`std::iter::iter(&mut source)` constructs an `Iter` using the same structural
`next(&mut self) -> Option<V>` contract as `Iter::new`. `Map`, `Filter`,
`Reduce`, and the `collect` implementation belong to `std::iter`.

`filter` owns its predecessor and predicate. The predicate takes `&V` and
returns `bool`; rejected items are destroyed by the ordinary cleanup rules.
`reduce(|acc: V, item: V| { ... })` owns its predecessor and reducer. The
first yielded item initializes the accumulator. Its `next()` consumes the
remaining source and yields the final accumulator once. An empty source, and
any subsequent `next()` after reduction, yield `None`. The reducer must return
`V`. Callback captures retain the existing closure capture semantics.

Any type admissible as the payload of `Option<T>` may be yielded by `next()`
or produced by a mapper. Collection additionally requires that the destination
accept that same element type. This includes numeric `usize`, references,
aggregates, and owned values wherever the ordinary rules allow them. Moving an
item through the pipeline preserves its dependencies and cleanup obligations.
A loan in a yielded or collected item stays subject to N4 and N5. In particular,
advancing the source again requires compatibility with any outstanding loan.

This is the accepted target for both compilers. The current [validation
report](cycles/CORE_COMPOSITION_CYCLE.md#iter-map-and-collect) describes the
subset implemented and tested.

## 12. UTF-8 and Thong retained, partial support

[UTF8_STRINGS.md](UTF8_STRINGS.md) is part of the normative rules: TX1–TX20
set str views, explicit conversions, byte indexing, String
based on Vector<u8> and invariant UTF-8 during mutations. String is not
The proposals are not yet fully implemented.
The following decisions on Vector and String are reported:
are recorded in [FOUNDATIONS_AND_VECTORS.md](FOUNDATIONS_AND_VECTORS.md).

**TX23 — Bounded inline strings.** `String<N>` adds a
compile-time byte bound and fixed inline payload with current-length metadata.
Plain `String` retains growing storage. See the normative
[bounded-string definition](UTF8_STRINGS.md#bounded-inline-utf-8-strings).
The grammar, corboc specialization and STD implementation are integrated; see
the verification matrix for scoped evidence.

<a id="13-fondamentaux-allocations-typées-et-vecteurs"></a>

## 13. Fundamentals, typed allowances and delivery systems

Voir [FOUNDATIONS_AND_VECTORS.md](FOUNDATIONS_AND_VECTORS.md) for F1–F5,
H1–H3, VE1–VE6, GR1–GR2 and TX21–TX22. The matrix distinguishes the executable parts
from the remaining decisions.

[HASH_MAP.md](HASH_MAP.md) HM1–HM6 for `HashMap`, with its
operations, its growing storage and monitoring of input dependencies.

<a id="14-inventaire-historique-du-travail-restant"></a>

## 14. Historical inventory of remaining work

The list below retains the work identified during the initial design. Several have
since been partially or fully connected within a given perimeter, including PR1,
contracts, structures and UTF-8. It does not constitute the current implementation
checklist: consult the
[README](../README.md) and the [audit matrix](VERIFICATION_MATRIX.md),
The most recent cycles of which specify the differences still open.

- Formalize the effects of signatures, the origins of returned references
  and monitoring dependencies in mutable structures.
- Specify the balance sheet of conditional transfers and the compact syntax of the
  returns/transfers in all contexts.
- Retirer l'ancienne API `reset` according to PR1 on the next pass requested,
  and then migrate its documents, examples, contracts and tests without weakening the
  life and destruction invariants.
- Formalize the effects of `drop` and Destroys, including
  groups of dependencies, cycles and displaced allocators.
- Set the placement algorithms of the two data stacks and the
  configuration of their size at the program level, according to G1–G12.
- Set the interface of allocators compatible with language guarantees.
- Define the mandatory source notation for `new`, as well for
  data stacks only for allocators, in accordance with principle I2.
- Define boundaries with unverified C. Backend C is retained for
  experiment; rules are checked before generation of C.
- Implement and validate the async/multithread rules subsequently recorded,
  after resolution of the interfaces still open; no change in the
  The compiler is not requested by the mere recording of these decisions.
- Implement and validate ST1–ST18/ME1–ME4 and their interactions
  with the existing memory model, without reintroducing the withdrawn partial states.
- Implement and validate TX1–TX20 after clarification of points
  open; the recording does not introduce any executable support of String.

Unimplemented parts shall not be presented as already verified by the compiler or
established by existing tests.

<a id="15-frontière-avec-le-c"></a>

## 15. Border with C

**FFI1 — Explicit appeal to C.** An external C function is declared with
`extern "C"` and a signature. Any call to this function is made in a
bloc `unsafe`Corbo checks the call from the signature declared.
The block `unsafe` indicates that the programmer ensures that the C code is in compliance
This rule also applies to compound signatures.
Only digital types.

```rust
extern "C" fn identite(n: i32) -> i32;

fn main() {
    let n = unsafe { identite(7) };
    print(n);
}
```

**FFI2 — Signatures scalaires.** In the first perimeter, a signature
`extern "C"` can take and make scalar types `i32`, `i64`,
`u8`, `u16`, `u32`, `u64`, `f32`, `f64` and `bool`. Ces valeurs passent
by copy. An external function may also render no value.
References, allowances `A<T>` and aggregates are refused
in these signatures.

**FFI3 — Flotants received from C.** When an external function makes a
`f32` ou un `f64`, Corbo checks that the value is finished before the
If the result is a NaN or an infinite of either sign, the program stops with a
diagnosis. A signed zero is allowed.

**FFI4 — Scope of the `unsafe`.** Authorization to call a function
`extern "C"` applies to the location of the call in the block.
Corbo checks in the block the types, borrowings, movements and destruction according
to normal rules.

**FFI5 — Correspondence of scalar.** The arguments and results
`extern "C"` follow the target's C Call Agreement.
The following are used at this border.

| Corbo | C |
| --- | --- |
| `i32`, `i64` | `int32_t`, `int64_t` |
| `u8`, `u16`, `u32`, `u64` | `uint8_t`, `uint16_t`, `uint32_t`, `uint64_t` |
| `bool` | `_Bool` |
| `f32`, `f64` | `float`, `double`, on targets where they correspond to binary32 and binary64 |
| No results | `void` |

The compiler adapts Corbo's internal representations to the call point. Definition C
must correspond to the external statement.

**FFI6 — Build with source C.** The command
`crust build main.crb --c-source identite.c -o programme` produit
the Corbo object with the active backend, compiles the source C provided by the C
compiler, then binds the objects in the same build.
resolves the symbols named in the declarations `extern "C"`. Un
external symbol could not be found makes the build fail at the link.

## Structural replication in fixed arrays

For `[value; N]`, the initializer is evaluated once. When `N > 1`, its
value must be primitive or a structure without a custom destructor whose
fields are all structurally replicable by the same rule. Each slot receives
an independent value. This syntax leaves the rules of `copy()` intact.

## Process arguments

The entry point remains `fn main()`. `std::env::args()` returns
`Result<&[&str], ArgsError>` and excludes the executable name. The immutable
argument storage lives for the duration of the process. Invalid Unicode
is reported as `InvalidUtf8`. Runtime acquisition failures are reported
as `Unavailable`.

## Constrained nominal templates

**SC1 — Structural contracts on records.** The `type` annotations also apply
to a struct declaration. Its type parameters are in scope in its field types
and in the corresponding `impl` blocks. An explicit parameter list can state
their order. When the list is omitted, the annotations introduce the parameters
in declaration order. Each concrete argument list identifies one concrete type.

```rust
#(type: V)
#(type: T<V> with {
    fn next(&mut self) -> Option<V>;
})
struct Cursor<T, V> {
    source: &mut T,
}

impl Cursor<T, V> {
    fn new(source: &mut T) -> Cursor<T, V> {
        Cursor { source: source }
    }

    fn next(&mut self) -> Option<V> {
        let source = &mut *(*self).source;
        source.next()
    }
}
```

**SC2 — Static substitution and inference.** Constructor argument types bind
the type parameters. The required concrete method signatures determine the
remaining parameters, including an item type inside `Option<V>` or an error
type inside `Result<usize, E>`. Explicit type arguments must agree with those
signatures. Receiver modes, argument types, return types and the `async`
modifier participate in the signature check. `with` permits additional methods.
The exact form requires the declared method set, with destruction handled by
the existing destruction rules.

**SC3 — Contract scope and ordinary memory rules.** An implementation can call
the methods guaranteed by a constrained parameter. Its concrete specialization
is subject to N1–N8 and to the ordinary placement and destruction analysis.
A field of type `&mut T` borrows its target. A field of type `T` receives its
value by move. A contract supplies no storage, hidden borrowing or lifetime
extension.

**SC4 — Parameterized error envelopes.** Nominal enums also accept type
parameters. This lets a constrained adapter retain its source's error in
`BufferedError<E>`, whose variants are `Stream { error: E }` and `WriteZero`.
The error type is part of the concrete adapter type. A variant pattern uses
the surrounding match type to select its specialization.


## Conditional annotations and foreign C

`#(if: condition)` opens a compile-time selection and `#(endif)` closes it.
The source lies between the annotations, outside their parentheses. Selections
can nest and introduce no scope. The existing `target.os`, `target.family`,
`target.arch` and `target.pointer_width` comparisons, `&&` and `||` retain their
meaning. Selection precedes import resolution and collision checks. Missing
and unmatched end markers are syntax errors. The former parenthesized-body
spelling is replaced in the active compiler and STD; historical Rust-reference
fixtures retain their old spelling.

Inside `@unchecked`, `@c { ... }` embeds opaque C statements. Its optional
parameter is `@c(includes={"stdint.h", "path/to/header.h"}) { ... }`. Entries
are nonempty literal header paths containing ASCII letters, digits, `_`, `.`,
`/`, `-` or `:`. There are no command-line flags or arbitrary preprocessor
text in this parameter. Selected headers are emitted once per translation
unit as quoted C includes. The native C toolchain resolves those paths using
its normal header search; absolute paths are permitted. Blocks selected out
by a target annotation contribute no includes.

`${name}` names an existing typed Corbo binding, including aggregates. Mutable
bindings expose their C storage; immutable scalars are C rvalues and immutable
aggregates are const C views of their storage. Assembly and C text
inside strings and comments is kept opaque. Corbo verifies the binding's type
and availability at the crossing; it does not verify C control flow, pointer
accesses, retained addresses or resource cleanup inside `@unchecked`.
The developer remains responsible for those effects and the target C ABI.
The braces of a foreign C block delimit its own C statement scope.

A trusted Corbo implementation may create a mutable borrow of a record field
through a shared reference inside `@unchecked`, for example after acquiring an
interior-mutability lock. The reference retains its ordinary target/provenance
and lifetime checks. This bypasses the shared-reference mutation-permission
check at that borrow only; it does not create synchronization. The implementer
must uphold the lock contract. The same borrow outside `@unchecked` remains
refused. Native addresses still cannot escape their unchecked block.

The compiler provides compatible C
representations of the relevant concrete Corbo types and access to the C runtime
library, including shared pools, datastacks and regions, automatically in `@c`.
The C runtime remains a library when the native Corbo backend is introduced.
This representation/access mechanism does not apply Corbo ownership or borrow
checking to C code. Within `@unchecked`, copies, aliases, transfers, lifetimes,
cleanup and stack cursor operations remain the developer's responsibility and
must be documented with the C interface. Checked ownership wrappers are not
required by this extension. The shared C11 layouts and memory-runtime API are
declared in `runtime/corbo_runtime.h`. Program-specific declarations and operand
type aliases are emitted before foreign statements; requested headers follow
the generated type declarations. See [the foreign-C interface](FOREIGN_C.md)
for naming, library linkage and the developer's responsibilities.

## Thread transfer eligibility (TR1)

See [thread transfer](THREAD_TRANSFER.md).

## Universal borrowing and iteration syntax

[Reference methods and for loops](ITERATION_SYNTAX.md) define the new spellings
using the existing move, lifetime, mutation and cleanup rules.

### Tuple patterns in for loops

`for (first, second) in source { ... }` uses the existing tuple destructuring
rules and requires the exact item arity. `mut` may qualify an individual binding.
Owned iterator items follow the existing move and primitive-copy rules. For
borrowed array/slice items, each binding is a reference to its original field;
its permission comes from the source borrow. Reading a primitive field uses
`*field`; mutation requires a mutable source and uses `*field = value`.
No field is moved out of borrowed storage. Target validity and branch/lock
obligations remain governed by N4–N8. The source is evaluated once and each
iteration keeps its ordinary cleanup scope.

A numeric tuple projection such as `item.0` is distinct from a leading-dot float
such as `.5` in operand position. Invalid field indices are diagnosed as tuple
projection errors rather than as a missing following block.

## Self type alias

Inside an `impl`, `Self` denotes the implemented type with its enclosing
generic arguments. It is accepted in signatures (`&Self`, `self: Self`),
constructor literals (`Self { ... }`) and associated calls (`Self::new(...)`).
It introduces no conversion, copy or move rule. `Self` outside an `impl` is
rejected; `Self<T>` is rejected because the implementation already fixes the
arguments. Lowercase `self` remains the receiver binding.
