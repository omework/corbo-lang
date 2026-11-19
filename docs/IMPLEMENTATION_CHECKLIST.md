## Documentation coverage gaps (compiler/core)

- [x] Replay the nine historical failures without changing their sources or accepted rules.
- [x] Integrate function structural contracts and explicit returned-borrow arguments.
- [x] Integrate branch/lock signature metadata, temporary joins and aggregate lock-result dependencies.
- [x] Integrate and validate batched exact numeric try_from, typed text length, named slice comparison and C address operands.
- [x] Accept usize-bearing records in custom buffered adapters.
- [x] Execute 18 focused programs, seven refusals and the six/seven callable regressions.
- [x] Validate the compact resource representation, history wrap and runtime-only boundary.
- [x] Install the compiler; compare its own emitted C byte for byte.
- [x] Update historical observations, documentation replay and the [cycle report](cycles/DOCUMENTATION_COVERAGE_CYCLE.md).

No new language decision remains for these nine forms. Platform limits and
unexercised compositions are listed in the report.

[Français](IMPLEMENTATION_CHECKLIST-fr.md)

<a id="checklist-globale-dimplémentation"></a>

# Global implementation checklist

## Configurable constants and HTTP parsing (core + STD API)

- [x] Parse configurable constants and lexical override blocks.
- [x] Resolve/import aliases, visibility, types and duplicate targets.
- [x] Specialize helper calls and nominal layouts; preserve escaped configurations.
- [x] Implement bounded HTTP request/response heads and optional streaming bodies.
- [x] Preserve nested result and reader dependencies with existing value summaries.
- [x] Complete 37 focused checks: 25 UBSan executions and 12 expected refusals.
- [x] Reconstruct the optimized compiler with identical emitted C.
- [x] Regenerate/check API documentation and record scope/limits.

No open design decision. Working-tree STD selection and untested platforms are
explicit in the [cycle report](cycles/HTTP_CONFIGURATION_IMPLEMENTATION_CYCLE.md).


## General callable values (compiler/core)

- [x] Keep the existing closure grammar and explicit `fn` / `&fn` / `&mut fn` passing modes.
- [x] Materialize capture objects and invocation through ordinary concrete call contracts.
- [x] Preserve move/copy semantics, mutable captures, borrow roots and cleanup after transfer.
- [x] Execute six focused programs and reject seven invalid programs with corboc.
- [x] Execute the updated README closure example and former rejected fixture under fatal UBSan.
- [x] Remove the resolved callable limitation and record the [scope and evidence](cycles/GENERAL_CALLABLES_CYCLE.md).

## Bare type parameters and example readability (core/documentation)

- [x] Accept `#(type: V)` and reject the former star form in the active parser.
- [x] Align the grammar, current STD, normative examples and README packages.
- [x] Space declaration/method blocks and compact lists without changing example logic.
- [x] Build corboc once; validate the two forms, unchanged constraint syntax and Reader execution.
- [x] Keep the installed STD/source pin coherent and regenerate its runtime resources.
- [x] Record the [focused results](cycles/BARE_TYPE_ANNOTATION_CYCLE.md); no broad suite or self-reconstruction run.

## README memory-budget comparison and reading flow (documentation)

- [x] Pair the Rust collection example with a complete Corbo program using a 64 KiB region.
- [x] Distinguish vector-slot capacity, region reservation and element-storage limits; retain optional annotations.
- [x] Reorder the README into motivation, quick start, grouped examples, STD overview and source-build details.
- [x] Preserve the 32 existing executable examples and synchronize all 33 source blocks with their packages.
- [x] Execute the new Corbo example, the Rust comparison and the 8,192/8,193-element boundaries.
- [x] Check links and record the [focused validation report](cycles/README_BUDGET_FLOW_CYCLE.md).

No normative rule, API or compiler behavior changed. The documentation runner
also rejects an unknown `--only` name instead of reporting success for zero cases.

## Source documentation and executable README (documentation/tooling)

- [x] Document STD declarations and members, including private helpers and variant payloads.
- [x] Document active Corbo runtime functions, C ABI/reference types/fields/functions and runtime build helpers.
- [x] Generate STD/runtime references and add source coverage/freshness checks.
- [x] Add a collection API guide and documentation maintenance instructions.
- [x] Expand the README with 32 complete source-linked packages and verify source correspondence.
- [x] Compile and execute all 32 examples with corboc, O1 and fatal UBSan on the host.
- [x] Replay ten observed rejected forms and publish them as coverage observations, not rules.
- [x] Confirm documentation-only source changes and equivalent generated runtime code tokens.
- [x] Record the [cycle report](cycles/DOCUMENTATION_CYCLE.md) and verification matrix.

No language/API decision changed. Other-platform execution was not repeated;
Windows ARM64 remains deferred. Rejected forms are listed in
[documentation coverage limits](DOCUMENTATION_LIMITS.md).

## Corbo runtime implementation (compiler/runtime)

- [x] Inventory the C reference and preserve the existing C ABI/layouts.
- [x] Implement allocation-free, scalar runtime emission in corboc, retaining ordinary verification.
- [x] Port datastacks, VM/region policy, pool slots and cleanup algorithms to Corbo.
- [x] Port vector/map operations, task values, scheduling, native/blocking workers and reactor state transitions to Corbo.
- [x] Execute the first standalone library and aggregate/application smoke programs against compiled Corbo sections.
- [x] Complete the first four-target differential matrix, launch-failure and storage-boundary checks; fix the x86 callback-type discrepancy.
- [x] Connect Corbo sections to normal resource generation and standalone library builds; retain selectable C reference.
- [x] Complete the four-target differential matrix: 48 executions per target, including boundary failures.
- [x] Complete the pinned compiler self-rebuild and real reactor integration checks.
- [x] Record implementation boundaries, executed evidence and remaining platform gaps in the [cycle report](cycles/CORBO_RUNTIME_CYCLE.md).

The C implementation remains the comparison reference. Machine/ABI primitives
remain explicit unchecked bindings; algorithm/control policy is in Corbo.
Windows ARM64 execution remains deferred by the existing user decision.

## Compiler repository extraction (build/organization)

- [x] Move the active compiler to the root of `omework/corboc`; remove the in-tree copy.
- [x] Move focused compiler regression scripts and fixtures; retain historical command forwarders.
- [x] Pin STD/runtime/normative inputs to `cd7e97b3a0bf9f808fb27559705b11509d4e1a24` in `corbo.lock`.
- [x] Add verified source preparation and a build/install script with automatic STD discovery.
- [x] Rebuild two compiler generations, compare their C byte for byte, run normal package self-build and an external two-module program.
- [x] Complete the moved core-extension, generic/tuple/registry and C-bridge suites on the host, plus six source-lock checks.
- [x] Complete final developer-tool path checks and publish [extraction evidence](cycles/COMPILER_REPOSITORY_SPLIT.md).

No normative rule changed. The compiler checkout is normally `../corboc`, or
`CORBOC_SOURCE_ROOT`. See [the repository boundary](COMPILER_REPOSITORY.md).

## C runtime/type bridge (core integration)

- [x] Expose the canonical C11 layouts and memory API in `runtime/corbo_runtime.h`.
- [x] Package the existing datastack/pool/region/map implementation as a standalone C archive; keep generated-C helpers on the same embedded runtime instance.
- [x] Generate nominal C declarations, collision-free enum names, field aliases and local operand typedefs.
- [x] Support aggregate operands without copying their storage, including placed arrays and concrete generic types.
- [x] Preserve operand availability/mutability checks and the unchecked C ownership/lifetime boundary.
- [x] Execute 22 integration runs at O0/O2 on macOS ARM64, macOS x86-64, Linux x86-64 and Windows x86-64 through Wine; six expected host refusals.
- [x] Complete host core-extension and generic/tuple/registry regressions.
- [x] Complete the final `usize` scalar-operand correction, rerun it on all four targets and complete normal compiler package self-build with byte-identical generated C.
- [x] Publish the [cycle report](cycles/C_RUNTIME_BRIDGE_CYCLE.md), foreign-C/runtime documentation and verification matrix.
- Platform gap: Windows ARM64 remains deferred by user decision; Wine does not replace native Windows evidence.

<a id="placement-fixe-dans-le-compilateur-rust"></a>

## Current cycle: conditional annotations, foreign C and recorded compiler limits (core)

- [x] Integrate paired target selection and migrate 124 compiler/STD/example regions; reject the former parenthesized body.
- [x] Integrate opaque C lexing, explicit scalar operands and deduplicated header emission; validate a real custom header and immutable operands.
- [x] Execute nested/mixed tuple conditionals and scalar moves across alternatives, scalar pop, transient constructor inputs, slice forwarding and record-valued method-result regressions.
- [x] Execute borrowed-enum matching and slice-parameter forwarding with separate symbolic storage.
- [x] Integrate and execute `?`, exact static error conversion, scalar/record reference dependencies, `.await?` and partial-argument cleanup.
- [x] Complete the focused suite: 21 programs on four executable targets, 20 expected host refusals and package-selection/header checks.
- [x] Complete host structural-contract, STD iterator and borrowed-result regressions.
- [x] Reconstruct corboc, compare its self-generated C, and complete its normal package-build command with automatic STD discovery.
- [x] Publish the grammar, foreign-C contract, representation notes, verification matrix and limitation status.

### Current follow-up: generic identities, result graphs and reactor registrations

These are compiler/runtime integration fixes; the language rules are unchanged.
The Rust bootstrap remains frozen.

- [x] Intern complete concrete generic arguments and select dependencies by source occurrence.
- [x] Instantiate independent caller-side tuple/record dependency graphs and relay environments.
- [x] Preserve tuple graphs through moves, destructuring and deferred task captures.
- [x] Group Unix registrations by descriptor and generation, aggregate read/write interests and detach before waking.
- [x] Connect trusted Windows completion hooks to per-operation IOCP wakeups.
- [x] Execute nine targeted programs at O0/O2 with UBSan, seven host refusals and deterministic registry transitions.
- [x] Execute the TCP split scenario on macOS ARM64, macOS x86-64, Linux x86-64 and Windows x86-64 through Wine.
- [x] Complete compiler regressions and native simultaneous-interest witnesses on all four executable targets.
- [x] Complete self-reconstruction and normal package self-build.
- [x] Finish the normal build binary’s byte-identical C comparison and finalize the report/matrix.

[Executed follow-up report](cycles/GENERIC_TUPLE_REACTOR_CYCLE.md).

No open language decision. Windows ARM64 execution remains explicitly deferred;
Wine evidence does not replace native Windows execution.

[Executed report and precise boundaries](cycles/CORE_EXTENSIONS_CYCLE.md).
The Rust bootstrap is frozen and retains the former annotation spelling; current
sources require a seed supporting the active grammar. Windows ARM64 execution
remains explicitly deferred. No open language decision in this cycle.

## Previous cycle: compression API extensions (STD/API)

- [x] Add bounded streaming encoders and decoders for Gzip and Zstd with caller-owned storage, backpressure, EOF and reset.
- [x] Load raw and formatted Zstd dictionaries, preserve dictionary IDs, entropy tables and repeat offsets.
- [x] Add dynamic-Huffman Gzip and one/four-stream Huffman Zstd encoding candidates with fallback.
- [x] Validate host interoperability, dictionary failures, fragmented streams, checksums and frame budgets.
- [x] Measure encoded sizes before/after on the same deterministic weighted input; verify both with reference decoders.
- [x] Finish the focused macOS x86-64, Linux x86-64 and Windows x86-64 execution matrix.
- [x] Publish the completed matrix, API documentation and generated STD reference.

No core rule or grammar change. Streaming decoders have explicit whole-frame
budgets. Windows ARM64 remains deferred by prior decision. General FSE sequence
encoding and dictionary training remain separate encoder/tooling extensions.

## Previous cycle: native Gzip and Zstd (STD/API)

- [x] Implement Gzip encode/decode in Corbo with levels, bounded workspace and CRC validation.
- [x] Implement Zstd encode/decode in Corbo with levels, content checksums and bounded workspace.
- [x] Execute host interoperability: 24 Gzip and 30 Zstd encodings; 11 Gzip and 22 Zstd decoding fixtures, plus malformed-input and bounded-storage cases.
- [x] Document the APIs, encoder strategies, dictionary/streaming boundaries and third-party notices.
- [x] Complete the focused platform matrix, including the final canonical Gzip length-code adjustment.
- [x] Publish the final executed evidence and remaining platform limitations.

No compiler grammar or memory rule changes. Windows ARM64 remains explicitly deferred.

## Previous cycle: visible native runtime source separation

- [x] Extract readable datastack, pool, collection, task and thread implementations into `runtime/`.
- [x] Keep backend entry points and replace embedded implementations with a generated resource bridge.
- [x] Compare the bytes of all seven former emitter sections, including conditional locking; all preserved.
- [x] Document compiler/runtime/STD boundaries and resource regeneration.

This is a file-organization refactor. No language/API changes or runtime
algorithm changes; no full rebuild or behavioral test campaign was run.

## Previous cycle: root STD collection exports (API)

- [x] Declare native Vector, HashMap and String exports in `stdlib/src/collections.crb`.
- [x] Resolve root imports, grouped imports, aliases and qualified type calls to the existing native types.
- [x] Preserve reserved-name rejection outside the trusted STD declarations.
- [x] Execute four functional packages and four expected import/declaration refusals.
- [x] Update the generated STD reference and publish targeted evidence.

The storage algorithms remain compiler-backed. This is an API/resolution change,
not a migration of those algorithms or a new memory primitive.
[Executed evidence](cycles/CORE_COMPOSITION_CYCLE.md#root-std-collection-exports).

## Previous cycle: collect is an instance method

- [x] Restore the approved API: consuming methods on Iter, Map, Filter and Reduce.
- [x] Remove the unrequested package-level collect export and call lowering.
- [x] Execute method collection, move and absent-export regressions: 10 accepted programs at O0/O2 with fatal UBSan, six rule refusals and one absent-export refusal.
- [x] Build the corrected corboc with the frozen bootstrap and run the targeted host suite.
- [ ] Repeat full self-reconstruction and the platform matrix on the final correction; previous-cycle evidence is recorded separately.
- [x] Publish the correction and its executed evidence, keeping unexecuted validation explicit.

## Previous cycle: STD iterator adapters

The Rust compiler remains frozen. Implementation targets the [compiler repository](https://github.com/omework/corboc)
and `stdlib/src/iter/`.

- [x] Locate the compiler-owned Map and collect algorithms.
- [x] Confirm Reduce uses the first item as accumulator and yields once.
- [x] Move Map, Filter, Reduce and collect algorithms into `std::iter`.
- [x] Specialize STD bodies and closure captures without embedding their algorithms.
- [x] Execute nine functional programs and five expected refusals on the host, plus the historical pipeline and structural-contract regressions.
- [x] Compile the self-generated C with fatal UBSan; execute the reconstructed corboc and repeat its own C generation byte for byte.
- [x] Execute the platform matrix and publish precise limitations; Windows ARM64 is deferred by explicit decision.

[Iterator documentation](ITERATORS.md) ·
[Completed cycle evidence](cycles/CORE_COMPOSITION_CYCLE.md#std-owned-iterator-adapters).

## Previous cycle: struct contracts in corboc

The Rust compiler is frozen. The active implementation target is
the [compiler repository](https://github.com/omework/corboc).

- [x] Parse structural type contracts on structs and their generic `impl` blocks.
- [x] Infer and specialize concrete types; check required signatures, receiver
  modes, async methods, exact/extended method sets and result alternatives.
- [x] Preserve the real STD Iter and its borrowed source through Map/collect.
- [x] Implement generic sync and async BufReader/BufWriter with caller storage
  and source-specific errors.
- [x] Run the functional and related borrowing/move/cleanup regressions.
- [x] Complete validation using the final self-rebuilt compiler.
- [x] Publish the completed cycle evidence and remaining limitations.

[Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#struct-contracts-and-generic-std-adapters).

## Packages and modules

- [x] Load one package from `package.toml` and compile its `src/main.crb`
  entry point with directory modules, `pub`, aliases, and grouped imports.
  Confirm collisions and private access are rejected.
  [Validation](cycles/CORE_COMPOSITION_CYCLE.md#single-package-modules)
- [x] Load external packages by local path or pinned Git commit.
- [x] Load the bundled standard library.


## Fixed placement in the Rust compiler

- [x] Synchronous structures with scalar fields. Final destination deducted
  after theAST, shared location between exclusive arms and reserved storage
  Four C witnesses under UBSan.
- [x] Place scalar and backend reference links and results
  Rust and connect their reservations and those of the structures to the datatack
  7 C-wipe controls under UBSan to `-O0` and `-O2`.
- [x] Lower the other primitives, the paintings with literal length,
  nominal enums, interlocking structures and pool storage
  The eight new witnesses are passing UBSan to `-O0` and `-O2`.
- [x] Transfer pool by loan and allocations `A<T>` by
  value, in signatures and between scopes. Read the variants of enums
  right in their pool slot.
- [x] Spread out the dependencies of the reference aggregates and borrow the
  Fourteen witnesses and ten refusals
  [Report](cycles/CORE_COMPOSITION_CYCLE.md#dépendances-des-agrégats-et-transferts-de-pool).
- [x] Track provenances by field and box, reborrow through
  a borrowed aggregate and link the aggregated fields of a borrowed match.
  Eight new witnesses and six refusals. [Report](cycles/CORE_COMPOSITION_CYCLE.md#provenances-par-position-et-match-emprunté).
- [x] Dimension the classic datastack according to the explicit size, the terminal
  Ten C witnesses and six refusals of annotation.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#dimensionnement-de-la-datastack-classique).
- [x] To grant the datastack to regions to the `Vector<T>` With fixed elements
  and `String` created in pool. Global sizes and
  The transfer and recovery are carried out.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#datastack-à-régions-dans-le-backend-rust).
- [x] Reconciling the `HashMap` with primitive values and vectors which
  store references or have `A<T>`. Seven witnesses C and
  four targeted refusals.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#collections-à-dépendances-et-régions).
- [x] Build a structure literal directly in the slot of
  `Pool.new` when the post-AST plan establishes that the literal is consumed
  The possession route adopts children from this slot.
- [x] Raccorder `pop` and `remove` for `Vector<A<T>>`. L’extraction
  attach the allowance to its recipient and keep its original pool.
  Static vector tracking maintains a conservative union of provenances.
- [x] Admit the nested reference types and results of the
  `get` and `get_mut` for values `A<T>`, `&T` and `&mut T`.
  The backend validates readings and borrowings on two levels.
- [x] Follow HashMap dependencies by known key. A dynamic key
  maintains a union of possible provenances.
- [x] Propprove HashMap's loan replacements by contracts
  The conditional effects preserve the synchronous effects, including relays.
  possible sources.
- [x] Keep the replacement effects delayed until waiting
  in the same context of analysis. `join()` and `.await` update
  summary with possible provenances, success or failure of launch.
- [x] Forward deferred effects in suspense contracts
  The first is the synchronous and async and the direct return of a native factory.
- [x] Encode the handle's position in the result contract and
  approximate the entries of synchronous recursive calls.
- [x] Transport the handles and their effects in fixed aggregates,
  the return of workers and the relays that preserve the paths.
  Validate the recursive expectations sync and async, success and failure of launch.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#handles-imbriqués-et-récursifs-dans-le-backend-rust).
- [x] Resolve contracts for recursive cycles that rebuild roads
  or combine waiting and restitution. Store and extract the handles in
  pools and vectors, with spread of delayed effects.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#handles-en-collection-et-contrats-des-cycles-récursifs).
- [x] Deduct the unique box from `remove(index)` and the end of dependencies
  on the arm `None` of the `match handles.pop()`. Check an early exit.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#déduction-de-la-case-unique-et-vidage-dun-vecteur-de-handles).
- [x] Measure the integrated restitution on a Corbo program with repeated peaks.
  [Mesures](G11_DATASTACK_BENCHMARK.md#restitution-intégrée-sur-un-programme-crust).
- [x] Place native threads states with `join()` immediate in a
  region. Named scalar catches and datastacks specific to the
  worker are exercised on success and failure of launch.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#état-régional-des-threads-natifs).
- [x] Keep thread handles and transfer them between telescopes or
  calls. Follow the catch of scalar borrowings to join and
  clean up abandoned autonomous tasks.
- [x] Place the Futures of the Rust sub-unit in the region.
  variable, pool and increasing content between pollution `yield`.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#handles-et-contextes-async-en-région).
- [x] Abaisser `.await` d − an inactive Future and `yield` in the scopes
  The post-AST plan retains the recovery points, temporary
  and scope marks. Fixed catch and borrowing results
  Fifteen C witnesses and thirteen targeted refusals.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#attente-directe-et-agrégats-empruntés-dans-le-backend-rust).
- [x] Transfer fixed aggregates that have slots `A<T>` entre
  The caller, the async state and the receiver. Clean the catches and
  results on exits that abandon them.
- [x] Spread dependencies of the result of `join()` through the
  signatures, then in the arm `Ok`.
- [x] Abaisser `spawn_blocking` and `AsyncHandle.await` with sleep,
  alarm clock and cleaning on `LaunchFailed`. The lot has 27 C witnesses,
  18 targeted refusals and 53 regression controls.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#ressources-et-complétions-de-tâches-dans-le-backend-rust).
- [x] Compose cleaning of structs, pool slots and elements of
  vector. The same path links the slots owned, then runtime
  You can return the children before their parents.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#nettoyage-composé-des-slots-possédés).

<a id="checklist-actuelle--grammaire-et-règles"></a>

## Current checklist — grammar and rules

The 11 November 2026 version serves as the reference of the core.
EBNF grammar, its integration into parser and the statement of rules N1 to N8,
including closure signatures `fn(...) -> R`.

The [resumption guide for the independent audit](CORE_AUDIT_HANDOFF.md)
group the core references and the reproductive protocol.

- [x] **Grammar and parser.** Validated forms of core are recorded
  in [l-l-ebnf](../CORE_GRAMMAR.ebnf) and integrated into the parser.
  `check --syntax-only` TX1 sets the JSON exhausts.
- [x] **Statement of Rules.** Invariants N1 to N8 are recorded in
  [LANGUAGE_RULES.md](LANGUAGE_RULES.md#noyau-mémoire--grille-de-lecture),
  with their normative references.

### Closures

- [x] **Grammaire.** `|…| { … }` creates a closure and `fn(...) -> R`
  describes his signature of call. `&fn` and `&mut fn` indicate the mode of borrowing.
- [x] **Parseur.** `check --syntax-only` recognizes these forms and
  `mut f: fn(...) -> R`. Il distingue l’emprunt de l’instance de celui du
  result and refuses the old rating `closure(...) -> R`.
- [x] **Rules.** The value passage follows the ordinary rules of copying
  The borrowing of the proceeding is explicit at the appeal point.
  A call that changes the state of the closure requires a mutable access, provided
  by `mut f` on the parameter received by value or by `&mut fn`.

SelectGroup remains postponed. Semantic verification and validation
are part of a later pass.

The remaining work on the auditor is shown in
[Semantic verification of the core](#vérification-sémantique-du-core).
The migration of tests and ASan are followed in
[Core alignment and validation](#alignement-et-validation-du-core).

<a id="grammaire-et-parseur"></a>

## Grammar and parser

- [x] Share the production of type arguments between named types
  and qualified calls set. Check the names defined by the
  programmeur, `MonType::new()` and `HashMap<i64, Point>::new()` To the parser.

- [x] Write the signatures of closure with `fn(...) -> R`. Recognize
  the value-by-value transition, `&fn`, `&mut fn` and `mut f: fn(...) -> R`.
  The core parser keeps these forms before the elaboration.

- [x] Check four shapes at the parser.
  without type, whole or floating key in a HashMap.
- [x] Explain the syntax analysis before development and recognize the
  three forms of annotation `branch`, y compris `result.await`.
- [x] Parse stacked type annotations, free declaration
  `#(type: R)` and contracts for methods with or without `with`.
- [x] Keep qualified type paths in signatures,
  including in the types of closures, HashMaps and handles.
- [x] Exiger `#(directive: …)` in the core profile and check the
  suffixes binaires `K`, `M` and `G` and the names of qualified pools.
- [x] Align the arms lists with `match` on the EBNF of the core.
  At least one arm, comma between arms and optional final comma.
- [x] Recognition of the reasons for `match` in the front syntactic tree
  completeness checks and translation of building results.
- [x] Parse references in nested type arguments and
  check the separators of the enclosures' parameter lists.
- [x] To recognize the dynamic tranches under borrowing in the
  signatures, interlocking types and liaison annotations.
- [x] Read signatures `AsyncHandle` and annotated literals `u8`
  before their typing checks.
- [x] To set the course for qualified roads in `impl`, both forms of
  `lock` and statements of non-empty enums.
- [x] Parse paths of qualified values as values, calls and
  operands of an async wait.
- [x] Distinguish the syntax from the entire literals of their terminals of
  representation. Check for decimals, ranges and comparisons.
- [x] Distinguish entries `move a;` Blocks `move { … }` and
  refuse an entry named after an ordinary instruction.
- [x] Recognize the final expression of a parser block alone,
  regardless of the type of function return.
- [x] Recognize the expression instructions completed by `;`
  in the parser blocks alone.
- [x] Parse assignment places combining fields, indices and
  de-references, with simple or compound assignment.
- [x] Parse suffix strings with fields, indices
  and method calls on a compound expression.
- [x] Parse the suffix `.new()` on a compound receiver, with
  empty, positional or by named fields initialization.
- [x] Limit root level to capacity statements and directives
  in the syntactic parser of the core and refuse the intertwined declarations.
- [x] Recognize regional guidelines on the functions
  and control blocks, including arms of `match`.
- [x] Recognize a `if` without `else` before verification of the values
  of branches, including after `else if`.
- [x] Parse the de-reference of un fixed and postfixed expressions,
  maintaining priority over binary operators.
- [x] Recognizing signatures and calls `extern "C"` avant
  translation of the external body and context control `unsafe`.
- [x] Apply the syntactic profile of the core independently of the
  Heuristic prototype and refuse the old transfer arrows.
- [x] Recognize `()` as a primary expression and check
  the parentheses of an immediate call for closure.
- [x] Read qualified conversions and error variants before
  the control of the member's inactivity and existence.
- [x] Require recipient `self` at the top of method signatures and
  check the forms borrowed and by value.
- [x] Recognize enum manufacturers with or without fields,
  including as a subject of `match`.
- [x] Recognize the unsigned whole sizes of the tables and
  pools before terminal and capacity controls.
- [x] Read the unsigned integers of `async_pool_sizes` avant
  verification of their capacity.
- [x] Keep a positive decimal region size at parser,
  even if it exceeds the compiler representation terminal.
- [x] Refuse the reserved identifiers in the reporting position in
  the parser alone, with `self` as recipient and `_` in the reasons.
- [x] Accepting a qualified expression in `.new(...)`, require
  simple names for its fields and limit parenthesed types to `()`.
- [x] Parse borrowing types in `pool<type>(taille)` and implementation
  the syntax of the identifiers to the variants and fields of the d的enum patterns.
- [x] Parse type alternatives in contracts, including
  borrowings, prior to separate name and type checks of the recipient.
- [x] Parser `runtime::spawn` and `runtime::spawn_blocking` with exactly
  an expression, before the async type and context checks.
- [x] Parse named catches and suspensions in blocks of
  `runtime::thread` before context and capture checks.
- [x] Parse arguments of ordinary methods before checks
  d `try_slice` in EBNF.
- [x] Apply the EBNF form of mutex manufacturers and remove the
  Prefixed historical buildings of parser alone.
- [x] Check the segments of the skilled paths and refuse the forms
  historical or experimental type outside the EBNF of the core.
- [x] Keep the borrowing operator applied to a cut before the
  mutability control.
- [x] Apply the same production of assignment to simple names and to
  projections, with control of the reserved identifiers.
- [x] Keep final block forms without semicolon as
  Result expressions in parser alone.
- [x] Disambigulate empty braces after d
  the entire production awaits a block.
- [x] Applying lexical constraints to value paths and
  field names, and discard the old runtime calls from the parser alone.
- [x] Applying production `chemin_valeur` on the grounds of `match`, y
  included in integrated paths and their identifiers.
- [x] Parse the complete type after `as` before the conversion control.
- [x] Recognition of external declarations and async of `main` before
  check of the point of entry.
- [x] Denied two consecutive region directives on the same block and
  check the annotations on the terminal blocks.
- [x] Refuse pair and `type feature` in the blocks of the
  and distinguish import `move` closure `move`.
- [x] Require a separator `::` contiguous, including in the
  nested generics whose closure touches `=`.
- [x] Show syntactic verification of the core by `check --syntax-only`.
- [x] Keep Name `i32` in the syntactic tree and apply the
  HashMap key list provided by EBNF.
- [x] Keep the types written in signatures before lowering
  allocations, borrowing and handling.
- [x] Prevent the resumption by historical educational productions
  after the refusal of a name reserved in the position of expression.
- [x] Distinguish the construction of a variant of a method call or
  d’un suffixe `.await` which follows a name d
- [x] Recognize a `if` With an empty block followed by an operator or suffix,
  even if the condition ends with a variant d-enum.
- [x] Expliciter `self` as a value and base of allocation in EBNF,
  and identify the productions of SelectGroup whose integration is postponed.
- [x] Align the demonstration programme `examples/main.crb` on
  the syntax of the core and replay its existing witness.
- [x] Migrer `examples/conditional_returns.crb` To `A<i32>` and verify
  the return by branch, relay and re-use of the slot.
- [x] Migrate examples of return of an object containing a loan to
  `A<View>` and check both of their compilation issues.
- [x] Distinguish the beach suffix `try_slice(..)` d
  ordinary with the same name.
- [x] Replay 57 witnesses calling directly `parse_syntax`
  and explain the context suffixes in the EBNF.
- [x] Distinguish generic closures from `==`, `>=` and `>>` when
  operators directly follow a target type of conversion.
- [x] Recognize the immediate call of a closure with the pair of
  parentheses provided for by `appel_closure`.
- [x] Distinguish the manufacturer `pool<T>(taille)` of Ordinary Uses
  Name `pool` in expressions, including interlocked comparisons.
- [x] Check the exhausts recognized by the current sprinkler and pick up
  the missing normative list in TX1.
- [x] Fix JSON exhausts in TX1 and EBNF, then check
  decoded bytes and refusal of invalid forms.
- [x] Disambiguize the braces after a structural name in condition,
  for empty blocks and blocks containing instructions.
- [x] Keep the internal syntax error of an expression, including
  d-a block form, without rereading the same form as instruction.
- [x] Update native thread tell-tale according to N4 and RT7, with and without
  borrowed dependency.
- [x] Replay the six syntax and core integration suites together
  and check the five core examples via `check --syntax-only`.
- [x] Realign the recipient of the historical return `type feature`
  on TF1 and replay the failed denial assertion.
- [x] Conserver `copy(...)` as a call to parser alone and check
  The absence of registration of the types of an async witness.
- [x] Diagnosis the invalid UTF-8 source bytes in `check --syntax-only`.
- [x] Play the parser alone the complete programs accepted by the
  The test shall be carried out after integration and check the refusal of the experimental scheduler.
- [x] Record correspondence between EBNF families and points
  The parser's entrance, with the replay of 61 syntactic controls.
- [x] Migrate sample fields and verify refusal of the
  `drop` placed before the last use of the field.
- [x] Migrating the witness of `match` not exhaustive and verify acceptance
  syntactic as well as refusal of completeness.
- [x] Migrate the replacement indicator between pools with a named result
  and record the refusal to assign a result of appeal directly.
- [x] Align the README examples and extracts from direct returns
  d `.vref()` and `.mut_vref()`.
- [x] Check the parser and the execution of the six core examples
  dedicated to flow control and block outputs.
- [x] Align examples of `drop` and travel under borrowing on
  `A<i32>` and verify the auditor's refusals.
- [x] Migrating examples of incompatible pool type and return
  d) allowance from a local pool.
- [x] Migrate example to order arguments to pass by value
  of the `A<i32>` and check the reverse order with the same call type.
- [x] Migrating sample borrowed field mutable to `A<Writer>` and
  check the writing before and after the last use of the loan.
- [x] Getting the example of two sources to `A<i32>` and verify
  identity and re-employment for each of the two branches.
- [x] Migrate the four range and displacement witnesses that
  used the old arrows or `allocator()`.
- [x] To identify and correct the differences between EBNF and
  parseur on validated forms of the core. The review and the witnesses are
  in [the report](cycles/CORE_COMPOSITION_CYCLE.md).

For competition, the kernel uses the built-in runtime.
Runtime and its public interfaces are postponed after validation
Invariants of the integrated runtime.
The first `HashMap` is subject to HM1–HM6 rules. Other extensions
APIs of data structures are carried over. Cases that use an API
existing can be used to check a kernel invariant.

<a id="revue-des-représentations"></a>

## Review of representations

- [x] Rebuild the four range and displacement cookies and
  map tokens from the forms of closure to the stop point.
- [x] Update the liaison identities, scope points,
  link call, origin and capture in the model.
- [x] Record the transfer of a shared reference under `move` and
  keep the point of displacement in the state of its source bond.
- [x] Mapping the return, junction, loop, and
  allocations, borrowings and projections reviewed at the time of recovery.
- [x] Browse the corpus extracted from the repository and build a graph by
  program or fragment recognized, with the link of each token to
  His scope and knots.
- [x] Record projections, controls, operations, annotations and
  facts not specified in the definition of representations.
- [x] Build the lexor chain, parser and static shaft in Rust.
- [x] Compare Rust projection to 2,766 occurrences of the corpus.
  The report retains the differences in representation and parsing.
- [x] Resign the Rust auditor and issue C for the
  synchronous scalar subset and local borrowing.
- [x] Build the control graph and track the last use
  To stabilize the financial statements at the time of the takeover of local loans.
  `while` and `loop` and connect `break` and `continue` in C.
- [x] Reconciling scalar reborrowing, parameters and returns
  scalar reference loops and scalar result loops or
  To keep the possible provenances and parents.
- [ ] Extend the Rust verifier to the entire N1–N8,
  In particular, contracts for aggregate effects, storage
  owner and l ́async.
- [ ] To assign these representations to semantic analysis in a batch
  The data already available are still usable even if
  a capture or provenance has not yet been resolved.

[Revue token by token](cycles/CORE_COMPOSITION_CYCLE.md#revue-token-par-token-des-représentations).

<a id="vérification-sémantique-du-core"></a>

## Core semantic verification

The [N1–N8 invariants](LANGUAGE_RULES.md#core-memory-invariants) define the
obligations tracked here. The open items describe guarantees still to be
established. Compare any rejection with the relevant rule before changing
the compiler.

- [ ] **N4 — Lifetime of targets and pools.** Prove on every path that a
  captured target outlives its uses in the branch, including when an
  operation on a handle establishes the end of those uses. Exercise closure
  captures and returns that carry dependencies, as well as transferred handles.
- [ ] **N5 — Access compatibility.** Track the reserved place and reborrows
  through their last use. Exercise mutable nonscalar closure captures,
  reborrows from a mutable HashMap entry, and access under a lock acquired
  in async code. Replay the `match &*view` witness.
- [ ] **N6 — Paths, provenance, and evaluation order.** Preserve path-specific
  facts through launches and waits until the point of use. Check that a
  replacement evaluates its right-hand side before destroying the old value.
  Regression witness: `data = make(&mut first, view);`.
- [ ] **N8 — Obligations across boundaries.** Carry provenance, borrowing, and
  cleanup effects into callers through contracts. Exercise general bodies
  annotated with `branch`, transfers of handles with dependencies, returns of
  `AsyncHandle`, returns with dependencies from unused closure templates,
  and call effects on HashMap entries.
  [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md) ·
  [Async contracts](ASYNC_MULTITHREAD_RULES.md#4-runtime-scheduler-et-point-dentrée)

Compilator side advance for all four rules. Validation not executed.

- **N6 and N8.** The join shall retain the deferred obligations of the
  nested values and receivers replaced by the same merger
  This merger also serves the needs of the
  results of `match` and loops and loads extracted from which
  The point of the
  loops also compares sources and variants of
  deferred result, destinations and contents of entries
  and the accuracy of the effects.
  The recursive projections retain their provenance in the
  junctions. Comparison of loops reads their pool table
  by type within each origin.
  The instantiation of a result contract preserves the fields
  finals which he describes and recovers the other projections since
  the arguments.
- **N4 and N8.** After waiting, the effects kept are applied
  The result of the wait refines the
  dependencies when one exact writing is aimed at a single load.
- **N6 and N8.** A synchronous relay that returns a single handle
  without adding d í ger keeps its effects accurate
  The pool and the proof of autonomy of a relay are
  spread from his arguments.
- **N4 and N8.** Synchronous launch takes over all obligations
  delayed from the inactive task in its execution handle.
- **N6 and N8.** The concrete pools of a `AsyncHandle` autonome
  The task is carried out to the extent of expectations and
  for a self-contained handlance returned from a
  parameter, direct creation replaces the argument pools.
  Synchronous calls that relay the task and outputs of
  Async loop keep the pools already solved.
  The factory inference also publishes the handling pools
  the task created can return.
  Transport via a `join()` Synchronous remains open.
- **N4, N5 and N8.** A task expected in an async context can restore
  un `AsyncHandle` borrowings from parameters
  The handle received maintains the reservations of the arguments
  until its own expectation. For a launch followed by `.await`,
  arm `Ok` resumes the reservations and `LaunchFailed` Free them.
  A returned handle can itself produce a scalar loan
  The junctions and the pure relays
  The contract and the
  The lowing carry the ordinary field entries
  until the inner handle is waiting. `Ok` affine
  fields written by all possible handle.
  The data are stored in a parametric contract for the
  the intermediate and final targets.
  transports to waiting for the inner handle and refines
  State after `Ok` when each path guarantees writing.
  A task that waits and then transmits this handle keeps
  intermediate and final targets and entries
  guarantees on all paths. Field replacements
  owners also carry their storage sources.
  Success refines the source of the field when replacement
  is guaranteed. For structures, enums and tables built in
  Async lowering, the graph distinguishes the base storage from the
  Field storage links or entries. A replacement removes
  The former provenance if none of these ties holds it.
  The junctions and loop covers retain the provenances
  For a vector of allowances, the contract of a handle
  returned propagates pools of elements that it can install up to
  The internal waiting. This follow-up is aggregated.
  for inline value vectors remains open.
  HashMap effects of a returned handle follow paths
  The constant keys remain the same.
  A dynamic key retains the possible dependencies.
  The termination contract relays the mutations of an injected table
  It also keeps the path without mutation.
  in case of failure of launch. The precise follow-up of interlacing with
  direct mutations and refinement by arm remain open.
- **N4 and N8.** Destination control passes through values
  carried out by the deferred writings and their descendants.
  a kept handwriting, it also checks the protected charge and the
  transitive dependencies of installed targets.
- **N4 and N5.** At the exit of an async block, the control checks
  that the surviving reservations do not include a scalar, or
  a local picture of this block.
- **N4 and N5.** Synchronous destruction of a target checks
  the dependencies of living tasks.
  consult the selected targets and pools. A digital scalar
  borrowed is also protected against `drop` explicite.
- **N4, N6 and N8.** Replacement of a receiver at a junction
  checks transitive dependencies, including delayed effects
  The results of the `if` conservent ces obligations
  in the same representation as those of `match` and loop.
- **N5 and N8.** Common deferred destinations
  participate in access control as long as the task or its
  handle is alive, even after the last mention of his affair.
  The check of a call also compares them to the graphs of the
  other arguments, in particular the dependencies of other handlers.
  A synchronous call from a task can relay a handle to
  if the contract returns that only hand without
  The other arguments are scalar.

- [x] Backend Rust, V3. Declaration and value passage move
  un primitif. `copy(x)` keeps the initial bond and refuses a painting.
  These four forms were replayed with `check`.

Destination check also checks the pool of deferred result
and the instances associated with the locks that this result can carry.
When a telescope is closed, the pools still required are calculated in
travelling through the ties of possession of living allowances.
also serves for destination control of transfers and updates
The pools of values that these updates can install
remain required as long as the handle has effect.
The closure of a block also follows the borrowing links of the groups
survivors and checks the life of the root of a projection.
Destination control applies the same verification to targets
and projections carried by a delayed update.
Closing a block and transfers use the same route
targets, including those of an embedded descriptor.
For N5, the validity of a planned reservation is read on its root.
Exclusive capture remains exclusive if its origin is not sufficient to
establish the split reading derogation.
For N5 and N8, the control of arguments of a call that transmits a
Handle with kept write uses these same storage links and the
locks worn by the handle and its result.

- **N4.** Field initializer dependencies go through control
  The AsyncHandle standalone parameters
  also admit a scalar array result. A synchronous call can be made
  receive a guarded effects handle if his contract describes the waiting
  Other handles, loans and proprietary securities
  must remain disjunct from the guarded bodies and their charges.
  A pool can also be passed if its contract preserves storage
  The transfer also controls the duration of the transfer.
  The transfer of the target and the pool of deferred entries.
  d-a standalone handle to inactive task erases source copy and
  records the possible abandonment if the frame is destroyed before starting.
  The direct expectation of an async call can transfer several handles to
  dependencies if the receiver waits for them in its opening sequence and
  if the preparation of the following arguments is completed immediately.
  The uncalled scalar calculations are part of this preparation.
  This sequence can cross blocks, blocks, and `yield` and links
  It can end with a `match` direct from waiting.
  This journey keeps the reservations until the end. It covers the
  scalar results, scalar tables or `Void` and updates
  deferred on captured handlets, including those on a mutex
  local. The receiver can use or return the digital loan
  in the second case, the appellant retains the target
  beyond the outside waiting. If the handle load is copied,
  the recipient may also return an allowance or another
  `AsyncHandle` the autonomy of which is verified.
  Other outbuilding handlines remain open.
- **N5.** The compiler recognises `match &*vue` and follows the re-borrowing of a
  nominal reference stored in an entry of HashMap.
  Directly detected via a nominal mutable closure capture use
  the mutable reborrowing of a field. A second acquisition in async is
  refused if the first custody retained the same instance.
  The reservation is sent by the guard.
  the mutable receiver also follows local aliases and projections
  to a mutable writing or calling. The results of blocks, `if`,
  `match` and `break` also carry the origin of the catch.
  The reassignments d
  and blocks. The loop covers propagate the origins up to
  stabilization. Exits resume the origins present at the
  `break` or at the end of the `while`. The value carried by a `break`
  is analysed with stabilized origins, including those
  propagated by a previous iteration. A terminal expression
  Block uses the merged origins after branches that
  The following conditions are met, including in an annotated storage block.
  Calls to a captured closure use sound mode
  Recipient. Resolved methods on aliases also use
  modes of their explicit parameters.
  The capture aliases also follow explicit re-borrowing and the
  Reference projections in the tables, with the type of element.
  Digital proprietary catches use this analysis to
  choose the mutable reborrowing of the field in case of detected d'écriture.
  The selection of the mutable receiver also takes into account signatures
  d) Transferable table borrowing and table operations which
  reserve or modify the captured projection.
  Before the inference of contracts, a borrowed return is considered
  as a possible alias if the call receives a borrowed argument
  The choice of the receiver uses this approximation.
  A task can receive locally the result of a
  annotated synchronous method `lock`. The compiler keeps the
  reservation until the destruction of the link and check the
  reacquisition on the same instance. The move to another
  local link or to a parent block keeps the reservation and
  requires the instance to survive the new receiver. A synchronous function
  called from task can consume this result or return it
  directly. The compiler follows the reservation and checks the effects
  The indirect contracts of synchronous functions apply to the
  They describe acquisitions,
  separate authorities and reservations carried by a
  Direct owner result. A result with a lock can be
  be transferred to a child task that consumes it locally and
  retourne un scalaire ou `Void`. The reservation follows the task until
  If the child returns directly to the
  The owner parameter, the reservation follows the result of the waiting.
  The same follow-up covers a synchronous return call whose contract
  restores the argument without copying or additional lock effect.
  A return via a directly expected downside task can also be
  forward the reservation if the contract of origin follows the
  A task can also return a value that
  maintains a newly acquired lock on a borrowed instance
  The contract sends this source to the appellants
  and to factories whose original capture is determined.
  A public handle keeps this result capture when its type
  Clears the concrete task. The relay via a hand thrown into the child
  Stay open.
  A mutable numerical reference transferred into a closure may be
  reborrowed in writing. The contract keeps the field reservation
  and the source of its target if the reborrowing is returned.
- **N6.** The assignment of which the right part is a result owner
  through the replacement after evaluation, including for an appeal,
  a control method or expression and an ancestor recipient.
  Replacement rereads the link in its scope after evaluation
  and destroys the old allowance only if she is still detained there.
  The junctions require a living allocation on each path that
  They merge provenances by position when the
  paths give a compatible provision.
  The convergence of loops takes into account the lock obligations
  and storage carried, including in an interlocked value.
  A Possible Wait
  as a result of a contract, the effects retained by the two parties are propagated
  Results of the `join` the state kept until
  the arms that distinguish the success of the launch failure, including
  when the charge is a view borrowed from a capture. `.await`, the
  regular updates of the borrowed fields also keep their states
  separate to `match`. The same follow-up exists after `join` lorsque
  the branch contract determines the changes. The synchronous monitoring
  includes the proprietary fields and their pools. In async, the `match`
  refines pools by field when the initial source of the field is
  Follow-up. `join`, the result also allows to find the positions
  and the sources of the vector elements when the contract
  determines. In async, a mutable loan retains the positions already
  if the termination and suspension contracts establish
  the task does not alter the elements. A direct expectation
  also reconstruct positions after exact withdrawals without addition
  After a fallible expectation, the `match` distingue
  the initial and after-removal positions.
  exact replacements reconstruct positions if contract
  identifies values and their dependencies. A value derived from a
  box followed takes the dependencies of this box, including for a
  the last element calculated by the contract.
  Indeterminate remain open. For a vector created in the task,
  the exact positions also rebuild the borrowings and the
  pools of its elements, keeping the vector pool itself.
- **N8.** The inference of branch contracts follows local aliases, the
  match results, loop covers and handles provided by
  on `break` d
  start a concrete task parameter moved into a block
  child, or to an inactive task provided by a child `if`, un
  `match` ou un `break`. Inference also solves factories
  task synchronous and launch auxiliary without
  redundant annotation. A relay that returns a parameter
  The origin of the corresponding argument shall be preserved by hand.
  The shape `join=result.await` also checks the functions
  Async who throw and then return a `AsyncHandle`, y compris
  via direct waiting for an inactive task or arm `Ok`
  d) a task wait launched.
  the creation of the task survives the launch and waiting.
  Synchronous task and handle relays also retain
  the source of their deferred result.
  The settings of closure
  The use of an unused template may represent the
  shared result of a closure by a symbolic capture and
  includes all parameters of the same type among the provenances
  If the mode of passage allows to invoke the closure
  with a mutable receiver, the template also represents the
  Re-borrowing a mutable digital or nominal capture.
  HashMap integration contracts may
  forward nominal targets, reference a key parameter and track
  A relay call can provide a constant key.
  Only arguments whose source is used by the contract must be
  go back to a relay parameter. A task directly expected can return
  un `AsyncHandle` autonomous with scalar result, scalar table or `Void`.
  The wait for a task launched separately can also deliver this handle
  in `Ok`, in async or via `join` in synchronous context.
  Synchronous can transfer it to an async task. Public signature
  `Handle<AsyncHandle<R>>` keeps the type of the inner handle through
  The dependencies and other effects at the borders
  restent ouverts.

L’emprunt `.vref()` directly in a field is a building witness
The HashMap operations in async remain asynch-typed and serviceable (N1 and N4).
the integration to be performed under N4, N5, N6 and N8 depending on the operation.
A shared loan of HashMap with scalar values or scalar references
shared can now be captured, transferred to another task or
transition to synchronous playback function. A task can also do
un `match` direct on `get` ou `get_mut` to read or change a value
Digital view holds the table in the arm `Some`. A table to
scalar values can be constructed locally or captured in mutable.
`insert` and `remove` return the old scalar value.
of these four operations may be received in a connection before the
`match`. A named search reserves the table as soon as it is evaluated.
The scalar result of `try_insert` can also be treated in a
`match` direct or named. `Ok(Some)`, `Ok(None)` and `Err`
the former value, the absence of the old value and the value
refused. `get` on a table of shared scalar references is
connected to `match` Async. `Some` can read the target with `**`.
It can also copy the reference with `*` for borrowing types
already supported. `A<T>` digital, `get` lit
the target and `get_mut` allows you to modify its content.
keep the source of the allowance stored.
the task also accepts insertion, replacement and extraction
d í digital allowances. The compiler keeps the original pools
results and connects their cleaning. For a known key,
`remove` remove the specific dependency on the graph input from the table
and preserves it in the result. `match` of the `try_insert` distingue
update in `Ok` of the table intact in `Err`, as a
later mutation did not render the effect obsolete. Dynamic keys
keep conservative provenances.
Local tables with scalar shared references also follow the
borrowings per entry for `insert`, `try_insert` and `remove`.
The `match` transfers the dependencies of the extracted reference to the receiver.
A synchronous function called by the task can insert references
in a local table received by mutable borrowing. The compiler applies
the paths of his contract at the table. A synchronous caller can also
recover from `join` effect of direct reference insertion
in a table captured by a mutable loan. The contract follows the
branches and suspensions `yield` the body being taken care of.
A calling task also applies these effects to its local table at the
terme d’un `.await` direct ou d’un `execution.await`. For a handle
launched, the `match` Distinguishes success from `LaunchFailed`. A task
intermediate can relay its injected table to a synchronous function
or a child task expected directly. Contracts remapply
the parameters from end to end. The relay via a handle launched
covers the `match` direct, the named handle and the waiting result
name, with `yield` The paths between these steps are possible.
`Ok` and `LaunchFailed` The handles relayed by expressions
The new system is now being developed and is being implemented.
The transfer contracts of the reference tables also cover
`remove(&clé)` If the key is known at call, the effect
of termination removes the corresponding dependency from the table.
A task can also insert a parameter `A<T>` digital transfer,
or remove and destroy in instruction a proprietary digital input
The contract publishes these effects in the graph of the
Allowances to `join` or `.await`, with control of the entrance pool.
The `match` of the `try_insert` on a borrowed table publishes the insertion
for `Ok` and preserves previous dependencies for `Err`. Values
Extracts can be cleaned in the arms.
values extracted remain open.
The journal found no stand-alone work sites for N1, N2, N3 or N7.
This observation is not valid for the full validation of these rules.

- [x] **Source guidelines and function type contracts.** Deux-points
  after `directive`, gabarits `K/M/G`, specialisation of `#(type: T<R> with {...})`
  on the nominal types and on the Futures of the integrated runtime.
  The target groups also cover both forms of `lock` and the downslopes.
  [Rapport](cycles/CORE_ANNOTATIONS_CYCLE.md)
- [x] **Back from a pool.** migrated to `A<E>` and validated
  Under UBSan. The general suite has finished. Its 145 failed tests fail
  also on the compiler before this patch.
  [Rapport](cycles/ENUM_CORE_VALIDATION_CYCLE.md)
- [x] **Marqueur `lock` (MT10).** Synchronous contracts and argumentation
  by borrowing or direct transfer. Capture async owner, cleaning of a
  task not started, waiting by `join()`direct and indirect `LaunchFailed`.
- [x] **HashMap V1.** HM1–HM6 connected to perimeter source operations
  loans on the table, replacement and extraction, key dependencies
  The data are not available.
- [x] **Returns of digital loans from async.** Shared returns and
  wide types, by `.await` Direct and via the handle.
  Source, local target and reservations in the target lot.
- [x] **Mutex charges with dependencies.** Structures represented
  containing a loan and an allowance owned, re-borrowing,
  mutex sharing, transfer of the target borrowed in custody and cleaning.
- [x] Propagating changes in source when replacing a
  field borrowed or owned by the guard of a local mutex without further borrowing.
  Sync and async cover, in direct assignment and via a sync auxiliary.
- [x] Propagating Field Replacement `&i32` by a Void to the
  and to the `join()` Synchronous. Success and `LaunchFailed` injected,
  with checking of dependencies of each arm.
  [Rapport](SAFETY.md#effets-de-dépendance-des-tâches-sous-garde)
- [x] Apply the same effect to `execution.await`. Check success,
  `LaunchFailed` and the reservations of the mutex and its targets.
  [Rapport](SAFETY.md#effets-de-dépendance-après-executionawait)
- [x] **Early placement on the datatack.** Correct refusal of return
  of local value where a `if` read before or after its creation.
  Future investment changes are limited to valid cases
  reproduced which still fail.
- [x] Replay regressions for this lot under UBSan. 24 targeted methods
  à `-O0` and 190 to `-O2` pass, as well as the placement supplements
  and returns of loans. [Report](SAFETY.md#cycle-des-retours-async-et-charges-gardées)

<a id="alignement-et-validation-du-core"></a>

## Core alignment and validation

- [x] Sort 145 tests in failure of the general pass by first block.
  [Inventory by test](CORE_FAILURE_TRIAGE.md)
- [x] Correct the projection coordinates of table borrowings
  Returned to Async. Validate `.await`, `join()`, the reservation and
  `LaunchFailed`.
- [x] Reconciling the result `bool` through `match h.await` and type the
  boolean branches of a `if` with suspension.
- [x] Refuse a scalar annotation `i32` on a value `A<i32>`.
- [x] Apply the type of element to the literal assigned to a box of
  tableau `i32` in an async function.
  [Report of the four corrections](cycles/CORE_INTEGRATION_FOLLOWUP_CYCLE.md)
- [ ] Migrating historical fixtures with current invariants,
  correct oracles, then replay variants and mixed cases.
- [x] Accepting borrowing annotations in `let` and type a literal
  affected via `mut_vref()`. Check the mode, type and life
  (Report on the](SAFETY.md#annotations-demprunt-et-littéraux-à-travers-mut_vref)
- [x] Align thirteen kernel examples on value displacements and
  the primitive targets. `i64` and `f64` without annotation and add
  modern variants of the two async aggregate fixtures.
  The original syntax for the historical profile tests is retained.
- [x] Distinguish the runtime embedded in grammar and entry points
  compiler. `--experimental-scheduler` activates prototype entries
  The public replacement of the runtime remains postponed.
- [x] Rejouer `test_async_owned_struct_returns` and
  `test_async_owned_struct_sync_calls` After correction of the signatures of
  fixtures to `A<T>`. The 26 tests go to `-O0`.
- [x] Replay the kernel cases after integration and check their traceability.
  UBSan and native oracles pass 29 tests targeted at `-O0`,
  170 tests to `-O2` and 137 tests of the historical profile.
  [Matrice](VERIFICATION_MATRIX.md#clôture-du-lot-dintégration-du-noyau) ·
  [Rapport](SAFETY.md#clôture-du-lot-dintégration-du-noyau)
- [ ] Take ASan back to an environment where the witness ends.
  machine the minimum tell-tale compiles and exceeds the five seconds delay.

<a id="intégré-et-exercé"></a>

## Integrated and exercised

The [core cycle report](SAFETY.md#cycle-de-validation-du-noyau-mémoire--8-novembre-2026)
separates the results of the current profile from those of the historical profile with reset.

- [x] Link N1–N8 to the accepted rules and to admitted and refused cases.
- [x] Run the 10 C programmes targeted and check the 19 variants
  invalid at both ports of entry.
- [x] Correct the masked receiver tracking in a child block and check
  the paths that reach its external use.
- [x] Replay storage, suspension, native thread and alarms suites.
- [x] Exercise recovery, wake-up and cleaning of the built-in runtime.
  The passes of 70 methods to `-O0` and 124 to `-O2`, plus the test
  Chain `.await` on both levels, go under UBSan.
  [Report of the integrated runtime](SAFETY.md#cycle-du-runtime-intégré--9-novembre-2026)
- [x] Replay contract, flow control and usage regressions
  The four final passes total 208 successful methods.
- [x] Integrate and exercise value displacements and blocks `move`
  in the perimeter of the kernel. See [report of displacements](SAFETY.md#cycle-des-déplacements-par-valeur).
- [x] Define the primitive numerical and logical of the target kernel in the
  [brouillon 07](../design-buffer/07-conversions-resultats-copies-et-vues.md#types-primitifs-du-noyau).
- [x] Exercise primitive digital, contextual typing and
  arithmetic checks in the profile `--numeric-core`.
- [x] Perform exact conversions, selection of a box and
  Composite assignments on variables and fixed tables, including
  travers `.await`, as well as the re-use of digital pool slots.
- [x] Reconnecting digital fields, allocations and async conversions
  and the field and de-referenced assignments in the
  [perimeter tested](SAFETY.md#cycle-dintégration-du-noyau--9-novembre-2026).
- [x] To grant direct borrowing from large digital fields, their
  synchronous returns and borrowed task parameters.
- [x] Write the [EBNF kernel grammar](../CORE_GRAMMAR.ebnf) with the forms
  async, then check a selection of accepted and refused syntaxes.
- [x] Record and check in grammar the floating lettering and
  both forms of native thread capture.
- [x] Integrate floating literals into the digital profile.
- [x] Integrate and exercise modern forms of native thread capture.
- [x] Arrange public manufacturers of synchronous and asynchronous mutexes.
- [x] Connect and verify new source forms in the kernel EBNF.
- [x] Reconnecting the manufacturers of scalar charge mutex, destruction
  of the guards and the re-borrowing async of `i32`.
- [x] Reconnect structurally charged mutex consisting of scalar and
  the reborrowing of large digital guards.
- [x] Reserve in the parent the local result of a `if` dont l'autre
  branch leaves function.
- [x] Validate this lot on 19 methods to `-O0`, and then 219 methods to `-O2`
  and the additions to the investment and borrowing.
  also the failures of the two historical async aggregates.
- [x] To reconnect the C scalar border and the build with `--c-source`.
- [x] Replay the integration pass and the regression of the kernel. 13 methods
  Targeted `-O0` and 213- `-O2` pass, with UBSan for oracle C.

Historical condition after lot [owners' fields in Vector<T>](cycles/INLINE_VECTOR_OWNED_CYCLE.md).
19 successful targeted methods; regression of 236 methods with four fixtures
Historical corrected and replayed, complementing regions with 35 successful methods.
This synthesis brings together the construction sites; detailed evidence and limitations remain
included in [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md) and reports.
"In place" means implemented and tested within a recorded perimeter, not that
All compositions are covered. The overall objective remains open.

<a id="état-par-chantier"></a>

## State by site

| Chantier | Already in place | Travail encore ouvert |
| --- | --- | --- |
| Compilation and Heart | CLI, verification, C generation, synchronous hand, binary; flow control, functions, expressions | Generalization of types/signatures in the remaining compositions |
| Transfers and destruction | Movements by value and blocks `move`, reception, drop, scope cleaning, return/break/continue | Compatibility fixtures still exert historical arrows |
| Borrowing and contracts | Last use, exclusivity, multiple sources, undercut contracts and call verification | Dependencies of complex aggregates/collections and some async interactions |
| Tableaux fixes | Entwined tables, referenced references and lines, explicit copies, entries and returns | See the perimeter and deviations of FIXED_ARRAYS_VALIDATION.md; not a promise for any type of element |
| Structures, enums, methods | Complete construction, defects, methods, copies, borrowed fields and owners, several recursive graphs | T/A<T> connected nominal returns; general compositions with remaining collections and async |
| UTF-8 and conversions | str, char, string, views/cuts, UTF-8 mutations verified, as/try_from, failed results | Forms and types not yet connected, general interactions with collections |
| Vecteurs | Int/u8 and reference vectors in the tested perimeter; Int and several other loads | Handlographs and online structures with represented fields, including owners, connected in the recorded lots; other fields/operations and general integration remaining |
| Results of typed vectors | Push/remove, pop Option<A<T>>, replace and try_push synchronous; captures, push/remove/pop and replaces local in async states; options and exchanges typed through parameters, returns and join tested | Local dependence of connected and tested loads; synchronous returns of connected containers; async and general compositions remaining |
| Stockage | Implicit data stack, typed pools, free slots, stable addresses and regions in the historical prototype | Two-data stacks target model and single-way recorded sliders. Placement, region recovery after cleaning threads and performance measures to be integrated. |
| Type features and guidelines | Historical form to one method, local type contracts to one function with several methods, static resolution, two-point source directives | Type contracts with an associated parameter in the area exercised |
| Async and Select | Typed frames and pool of states, yield/wawait, catches and transfers, suspension contracts, results, cleaning of losers | Signatures/captures, new collection loads, some complex field effects and graphs |
| Runtime and threads | Integrated Runtime, `spawn`, `spawn_blocking`, native thread, handles, wide digital borrowed returns, internal pollution context, recovery, alarms and cleaning in the cases executed | The replacement of the runtime is postponed. |
| Mutex | Scalar constructors, outbuilding structures, local guard replacement and shared field propagation `&i32` after `join()` and `execution.await` | Competitor access during replacement and other projections or types for this effect |
| Border C | Scalar and Void signatures, unsafe lexical block, type and end-of-life checks, build with multiple C sources | Other BITs and types outside this border |
| Validation | Accepted/refused, native C and UBSan, regressions, matrix and batch ratios | ASan Replay and Independent Audit |

<a id="lots-récents-terminés-dans-leur-périmètre"></a>

## Recent lots completed within their perimeter

- [x] Online structures owners fields : push/remove, destruction
  of boxes, contracts and async — INLINE_VECTOR_OWNED_CYCLE.md.
  16 targeted executions and 14 invalids; downsizing of 236 methods with
  correction/replay of old Node/A signatures<Node>, supplement of 35.

- [x] Nominal references in online structures: entire targets and
  internal, shared copies, mutable reborrowing, contracts and async —
  INLINE_VECTOR_NOMINAL_CYCLE.md. 11 targeted executions, 20 invalids;
  121 successful O2/UBSan regression methods.

- [x] &Int and &mut Int fields of online structures : push/copy/remove,
  synchronous contracts, reserved targets, catches and async results —
  INLINE_VECTOR_BORROWS_CYCLE.md. 20 targeted executions and 32 invalids;
  Final regressions of 194 and 85 successful methods.

- [x] Named transfers to Vector<T> with Int sheets: scopes, borrowings,
  synchronous relays, async captures and undercut storage requirements —
  INLINE_VECTOR_MOVES_CYCLE.md. 15 targeted executions, 19 invalids in both
  enter; 126 successful O2/UBSan regression methods.

- [x] Extraction of online structures — INLINE_VECTOR_REMOVE_CYCLE.md:
  removes, drop direct, parent/if/break receptions, synchronous returns and feature type;
  eight successful targeted methods, 185 successful O2/UBSan regression methods.

- [x] First perimeter of structures directly online in Vector<T> — INLINE_STRUCT_VECTORS_CYCLE.md:
  insertion/copying of Int leaf structures, block outputs and synchronous returns;
  eight successful targeted methods; regression of 373 methods, a fixture
  preexisting corrected, complement of 30 successful methods. Generalization still open.

- [x] Results owners with varying depth — RECURSIVE_OWNED_JOIN_CYCLE.md.
- [x] Synchronous operations on typed handle vectors — TYPED_HANDLE_VECTORS_CYCLE.md.
- [x] Typed results replace/try_push synchronous — TYPED_VECTOR_EXCHANGES_CYCLE.md.
- [x] Synchronous contracts Option<A<T>>, including None typed — TYPED_VECTOR_OPTIONS_CYCLE.md.
- [x] Explicit and implicit T/A<T> returns, contracts and relays — STRICT_STRUCTURE_RETURNS_CYCLE.md.
- [x] Follows updating of a field when the bearer name is hidden — same cycle.
- [x] Local captures, pools, push/remove/pop and local repositions of vectors typed in async — TYPED_ASYNC_HANDLE_VECTORS_CYCLE.md.
- [x] Async-typed options, interlocking envelopes, captures and public handles — TYPED_ASYNC_OPTIONS_CYCLE.md; eight targeted methods, 119 in regression.

- [x] Typed async exchanges replace/try_push, envelopes, captures, public handles and cleaning Select — TYPED_ASYNC_EXCHANGES_CYCLE.md; nine targeted methods, 135 regression.

- [x] Graphs of local vector elements, extractions and return of the extracted object — VECTOR_PAYLOAD_GRAPHS_CYCLE.md; eleven targeted methods and recorded regression.

- [x] Contracts for borrowing/owner vector elements — VECTOR_PAYLOAD_CONTRACTS_CYCLE.md; ten targeted methods, 145 in regression O2/UBSan.

- [x] Options for Borrowing/Owner, Returns and Relays — VECTOR_PAYLOAD_OPTIONS_CYCLE.md; seven targeted methods, 152 in regression O2/UBSan.

- [x] Graphs of the loads of replace/try_push, variants, relays and mutable capabilities — VECTOR_PAYLOAD_EXCHANGES_CYCLE.md; seven targeted methods, 159 in regression O2/UBSan.

- [x] Retracts of complex vectors, manufactures, relays and transformations — VECTOR_PAYLOAD_CONTAINERS_CYCLE.md; nine targeted methods, 168 in regression O2/UBSan.

- [x] Graphs of local async vectors, captures and operations — ASYNC_VECTOR_PAYLOAD_GRAPHS_CYCLE.md; 12 targeted methods, 264 regression and 14 additions.

- [x] Integration/extraction contracts from async, progeny graphs and C bridge — ASYNC_VECTOR_PAYLOAD_CONTRACTS_CYCLE.md; six targeted methods and 270 regression O2/UBSan.

- [x] Async returns of vectors, wait/join, successive manufactures and transfers — ASYNC_VECTOR_PAYLOAD_RETURNS_CYCLE.md; ten targeted methods and 280 regression O2/UBSan.

- [x] Public contracts runtime::Handle returning vectors and handle relays — ASYNC_VECTOR_PUBLIC_HANDLES_CYCLE.md; four new targeted methods and 284 regression O2/UBSan.

- [x] Results synchronous relays containing an async vector — ASYNC_VECTOR_RESULT_RELAYS_CYCLE.md; five new targeted methods and 289 O2/UBSan regression.

- [x] Entwined vector output captures and receptions — ASYNC_VECTOR_RESULT_CAPTURES_CYCLE.md; seven new targeted methods and 296 regression O2/UBSan.

- [x] Online leaf structures Int in the tasks async: creation, capture, copy/remove and returns by wait/join; public contracts Handle and relay Result — ASYNC_INLINE_VECTORS_CYCLE.md.

- [x] `match (-> résultat)` for the result of join: scalar, Void, allowances,
  borrowings and local values; trades replace/try_push preserved —
  CONSUMING_JOIN_MACH_CYCLE.md. 223 regression methods covered after ENOSPC recovery.

- [x] Pop of online structures, option<T> distinct d
  public functions, expectations/join and public handles — INLINE_VECTOR_POP_CYCLE.md.
  20 targeted methods; initial regression of 361 and then corrected replay of 173.

<a id="écarts-hors-du-lot-courant-du-core"></a>

## Deviations from the current lot of the core

- [ ] Elements of hand-held vectors containing borrowed fields or
  owners: local operations, synchronous integration/extraction contracts
  and Result options/exchanges connected within the reporting perimeters above.
  Synchronous returns of connected containers within the perimeter of the dedicated cycle.
  Nominal references, general consumers and async integration remain to be completed.
  Local async captures and operations connected within the perimeter of the dedicated cycle.
  Synchronous calls from async connected and tested in perimeter
  ASYNC_VECTOR_PAYLOAD_CONTRACTS_CYCLE.md. Async returns of entire containers
  connected to ASYNC_VECTOR_PAYLOAD_RETURNS_CYCLE.md.
  Public contracts for connected handle in ASYNC_VECTOR_PUBLIC_HANDLES_CYCLE.md.
  Result synchronous relays connected to ASYNC_VECTOR_RESULT_RELAYS_CYCLE.md.
  Capture/Restitution of Result, interlocking receipts and successive catches
  connected in ASYNC_VECTOR_RESULT_CAPTURES_CYCLE.md.
  The three minimum cases of &Point reference and consumption of the Result by a
  C O0/UBSan: complement recorded in
  INLINE_STRUCT_VECTORS_CYCLE.md. This does not close the general compositions.
- [ ] Structured Values Vectors Directly Online (VE1), Separate
  handle vectors: first connection of Int sheets and copies
  explicit in INLINE_STRUCT_VECTORS_CYCLE.md. Other extractions/replacements,
  Async's general integration and tranches remain open.
  Transfer named to Vector<T> connected and tested in INLINE_VECTOR_MOVES_CYCLE.md,
  with propagation of local requirements in sync/async contracts.
  &Int and &mut Int fields, interlocked included, connected in
  INLINE_VECTOR_BORROWS_CYCLE.md: insertion/extraction, shared copies,
  contracts and catches/async results. Nominal references shown
  connected in INLINE_VECTOR_NOMINAL_CYCLE.md: entire targets and
  substructures, copy/extraction, contracts, catches and joins.
  Accuracy of positions after calls and still conservative branches.
  Landowners' fields and cleaning of connected descendants in
  INLINE_VECTOR_OWNED_CYCLE.md: insertion/extraction, contracts and catches/join
  The field of testing. Graphs/types not shown are still open.
  Pop and Option<T> connected in INLINE_VECTOR_POP_CYCLE.md, with fields,
  functions, expectations/join and public handles within the area executed.
  Local synchronous re-place connected in the INLINE_VECTOR_REPLACE_CYCLE checkpoint.md:
  seven targeted methods, 142 in regression. Synchronous returns and parameters
  Result<T,T> connected to INLINE_VECTOR_REPLACE_CONTRACTS_CYCLE.md:
  eight successful targeted methods, 17 C executions and six invalid variants.
  Final regression: 171 successful O2/UBSan methods, 46 unchanged prints.
  Async integration remains open, with the fixed object refused
  validation/inline-vector-replace-async.crb.
  Try_push, slices and push_new remain to be connected.
  Remove Int leaf structures is connected to INLINE_VECTOR_REMOVE_CYCLE.md,
  with 185 successful regression methods in this batch.
  Creation, capture and extraction of Int leaves async: successful target in
  ASYNC_INLINE_VECTORS_CYCLE.md; 226 successful regression methods.
  The historical file open-inline-struct-vector.crb also used a copy
  implicit forbidden; the valid fixed corrected is inline-struct-vector.crb.
- [ ] Additional async compositions of types, catches, graphs of
  Fields and results. Reports indicate the perimeter of each family.
- [ ] Full project verification, rule by rule, on the whole
  of the seven drafts and the recorded rules.

This list of deviations is an inventory of the pilotage of known works.
not replace the full audit; do not deduct a percentage of the audit audit
reliable or a complete number of remaining cases.

Direct calls from a `fn` synchronous from a `async fn` are excluded
The old lots that mention them describe the Python prototype.

<a id="décisions-ouvertes-et-éléments-reportés"></a>

## Open decisions and deferred items


- Integration of `SelectGroup` postponed.

- Replacement of runtime in `main` and public interface of
  `runtime::Future` for custom runtimes. The compiler
  still contains the prototype `set_scheduler` And his callbacks.
- Enrichment of collections APIs.
- Features of several methods and relationships between types: carried forward.
- Select scheduling options: postponed.

See [the items carried over from the design](../design-buffer/points-ouverts.md).

Iterators and `mut()` remain out of prototype according to decisions
a loser of Select keeping an unanticipated launched handle must
be refused; this refusal is not a missing feature.

<a id="correspondance-avec-les-sept-brouillons"></a>

## Correspondence with the seven drafts

| Brouillon | Buildings concerned / condition |
| --- | --- |
| 01 — Own results | Explicit use and destruction in place; extension of typed results and still partial compositions |
| 02 — Transfer markers | Movements by value, forms `move` and return with new receiver integrated into the kernel perimeter. Arrows remain available for the historical code. [Draft 02](../design-buffer/02-marqueur-transfert.md) |
| 03 — Sweeping | Local cleaning and storage in place; general advance placement incomplete |
| 04 — Async, runtime and Select | Integrated runtime and wide borrowed returns in recorded cases. Open general compositions and replacement of the deferred runtime. |
| 05 — Data stack and pools | Storage, typed pools and nominal returns T/A<T> in place; general placement still to be completed |
| 06 — Type features | Static historical resolution to a method and multi-method functional contracts in the tested perimeter |
| 07 — Conversions, copies and views | Operations retained in place; composition coverage and partial types |
