## Mutex API namespaces

- [x] Move Mutex/MutexGuard to `std::sync` and `std::sync::asyn`.
- [x] Update private compiler bindings, docs and examples.
- [x] Run three fatal-UBSan programs and ten existing refusal checks.

[Evidence](cycles/MUTEX_NAMESPACE_CYCLE.md). Runtime unchanged; platform results retained.

## Synchronous defaults / shared-reference mutexes

| Rules / mechanism | Executed evidence | Limits |
| --- | --- | --- |
| API paths / N1 | Six README programs and async buffered File/TCP | Existing signatures retained; no async TLS |
| N4/N5/N8 | Per-field async results; three shared writers, scalar/aggregate guards, lifetime/re-entry refusals | Conservative cases remain; no safety proof |
| N2/N6/N7 | Guard move, payload destruction, terminal compound/indexed cleanup; FIFO waiter detach/handoff | Focused observations only |
| TR1 | Native guard transfer and suspension refused; async guard survives yield | Windows ARM64 compile-only |
| Runtime / ABI | Both queue implementations and existing metrics ABI checks | macOS, Linux Docker, Windows Wine |

[Evidence](cycles/SYNC_DEFAULT_MUTEX_CYCLE.md).

## Mutable references as mutation permission — focused compiler validation

MA1–MA6 revise N5: `&mut` does not establish uniqueness. Corboc separates
permission, content-effect/protection facts and retained dependencies. Nine
fatal-UBSan executions and ten refusals cover aliasing, same-lock sharing,
completion/lifetime boundaries and related cleanup. The native three-thread case
also executes on macOS x86-64, Linux x86-64 and Windows x86-64 under Wine;
Windows ARM64 is compile-only. See `corboc/docs/MUTABLE_ACCESS_CYCLE.md` and the
retained result snapshots there for exact scope and conservative limits.

## Documentation coverage follow-up

| Rules / mechanism | Executed evidence | Scope and limits |
| --- | --- | --- |
| N1/N8: structural contracts and numeric/text typing | Concrete function candidates, inferred output, forwarding, numeric bounds/exactness and descriptors executed. | Nine historical observations resolved; bounded expansion remains. |
| N4/N5/N6: returned loans, native boundary and lock lifetime | Explicit borrowed returns and relays, C operands, persistent aggregate lock results, drop release and expected invalid variants. | Targets and reservations checked through existing dependency graphs; arbitrary result shapes not claimed. |
| N7 and composition regressions | Buffered sink flush, callable cleanup/iterator composition and actual resource decoder all execute under fatal UBSan. | 26 executions, 20 expected refusals, two runtime-only accepts and five packing round trips on macOS ARM64. |
| Bootstrap and traceability | Final compiler installed; self-emitted C byte-identical; all 33 README blocks synchronized. | One reconstruction comparison, no full historical/platform campaign or independent audit. [Report](cycles/DOCUMENTATION_COVERAGE_CYCLE.md). |

## HTTP and configuration overrides — executed integration evidence

| Mechanism / rules | Evidence | Limits |
| --- | --- | --- |
| CC1–CC7 / N1 | Scoped defaults, transitive helpers/layouts, escaped values, aliases and type/visibility refusals | Literal/constant-reference evaluation; bounded specialization |
| N4/N5/N6 | Reader lifetime refusal, wrapper provenance and mutable reference/aggregate regressions | Recorded shapes; no independent audit |
| HTTP parsing / bounds | Both roles, partial reads, fixed/chunked bodies, trailers, EOF/errors, four budgets and repeated header views | Synchronous in-memory reader on macOS ARM64 |

37 checks complete (25 UBSan executions, 12 refusals); self-emitted compiler C
matches. [Evidence and limits](cycles/HTTP_CONFIGURATION_IMPLEMENTATION_CYCLE.md).

## Bare unconstrained type declarations

| Property | Executed evidence | Scope and limits |
| --- | --- | --- |
| Declaration syntax | Bare form accepted; star form rejected; existing usage-site type-list form accepted by the rebuilt parser. | Three small parser checks on the host; constraint enforcement unchanged. |
| Reader integration and documentation | Reader compiled and printed 42 at O1 with fatal UBSan. README/source correspondence and formatting-token checks passed. | One program executed; no broad suite, self-reconstruction or other-platform run. [Report](cycles/BARE_TYPE_ANNOTATION_CYCLE.md). |

## README memory-budget comparison

| Property | Executed evidence | Scope and limits |
| --- | --- | --- |
| Explicit vector growth limit | New Corbo example prints 1000 at O1 with fatal UBSan. A 64 KiB region holds 8,192 i64 values; the 8,193rd push exits with the region-limit diagnostic. Rust comparison also compiled and printed 1000. | Native macOS ARM64. The bound applies to this vector payload, not all process memory. |
| Reading flow and example preservation | All 32 existing executable blocks retained verbatim; all 33 blocks and auxiliary files match their packages. Section anchors and local links resolve. Unknown `--only` names fail with status 2. | Documentation/tooling change; no full compiler or platform matrix repeated. [Report](cycles/README_BUDGET_FLOW_CYCLE.md). |

## Documentation and runnable feature examples

| Contract / property | Executed evidence | Scope and limits |
| --- | --- | --- |
| Source documentation coverage | 89 STD files / 1,374 entries and 32 runtime files / 775 entries checked; private members, C ABI/reference declarations and Python runtime helper docstrings included. | Coverage/freshness evidence, not validation of every stated semantic property. |
| README example integrity | 32 complete packages compiled with corboc and executed at O1 with fatal UBSan; outputs/status/stderr and README source blocks matched. | Native macOS ARM64; loopback socket access enabled. No new platform-wide safety claim. |
| Documentation-only implementation edits | Unchanged code tokens in 78 C/Corbo files, unchanged Python helper ASTs excluding docstrings, equivalent generated runtime resource tokens. Five documentation extraction regressions passed. | Source/code-preservation evidence; compiler and pinned runtime were unchanged. |
| Current compiler coverage | Ten complete rejected forms replayed with recorded diagnostics; published separately from accepted examples. | Observations, not new normative rejection requirements. [Report](cycles/DOCUMENTATION_CYCLE.md), [limits](DOCUMENTATION_LIMITS.md). |

## Runtime algorithms implemented in Corbo

| Contract / rules | Executed evidence | Scope and limits |
| --- | --- | --- |
| Runtime ABI and operational parity | All 114 reference definitions represented; 48 differential executions per target across storage, tasks, failures, reactors and boundaries; 192 executions matched in total. | P · macOS ARM64 native, macOS x86-64/Rosetta, Linux x86-64/Docker, Windows x86-64/Wine. Fatal UBSan or UB traps; not every interleaving. |
| G1/G2/G9/G10, N4–N6 cleanup/placement integration | Normal integrated compiler passed core-extension, generic/tuple, C ABI and STD iterator regressions. C memory archive client passed on host, Linux and Windows. | P · Corbo algorithms with typed unchecked C ABI/platform bindings; C baseline retained. |
| Wakeup/registration contract | TCP/UDP O0/O2 and production multi-wait registry passed on all four targets, including real kqueue/epoll/IOCP. Connection destruction with live split tasks refused. | P · Windows ARM64 remains deferred; Wine is not native Windows hardware. |
| Runtime bootstrap boundary | Two accepts, six refusals, packing round trips and actual Corbo decoder/history-wrap execution passed. | P · Scalar-only runtime emission; ordinary ownership rules unchanged. Three compiler generations emitted identical C; normal self-build and external two-module execution passed. [Cycle report](cycles/CORBO_RUNTIME_CYCLE.md). |

## Compiler repository extraction

| Property | Executed evidence | Scope and limits |
| --- | --- | --- |
| Source/build identity | 81 compiler/package files compared before move; three self-hosted compiler generations emit identical C; normal package self-build and an external two-module program passed. | Repository/build change on macOS ARM64; no new language-rule guarantee. |
| Locked STD/runtime | Full revision check, clean input check, runtime-resource freshness and six isolated Git source-lock checks passed. | Shared inputs pinned to `cd7e97b3a0bf9f808fb27559705b11509d4e1a24`. |
| Regression/path integration | Moved core-extension, generic/tuple/registry and C-bridge suites completed; historical entry point, corpus discovery and target-emitter build paths checked. | Host evidence; earlier platform results remain separately scoped. [Report](cycles/COMPILER_REPOSITORY_SPLIT.md). |

## C runtime and type bridge

| Contract / rules | Executed evidence | Scope and limits |
| --- | --- | --- |
| Foreign C boundary, N1/N6 at operand crossing | Nine Corbo fixtures plus a C-only archive client and a separately compiled C helper: 22 executions per target at O0/O2; three Corbo refusals and three C mutability refusals on the host. | P · macOS ARM64, macOS x86-64/Rosetta, Linux x86-64/Docker and Windows x86-64/Wine. Fatal UBSan on Unix and UB traps on Windows. No Corbo ownership analysis inside C. |
| Shared layouts, G1/G2/G10 and cleanup | Struct/enum/tuple/array operands, indirect arrays, generic layouts, slices, pools/A, vectors/maps, Option/Result and task operands; offset/size checks, slot reuse, callback before release, stack marks/rewind and shared external-C runtime state. | P · Experimental version-matched C11 ABI; active descriptor stability and resource/alias correctness remain C caller obligations. Public standalone library is the memory runtime; no standalone scheduler ABI introduced. [Cycle report](cycles/C_RUNTIME_BRIDGE_CYCLE.md). |

## Core compositions

| Rules | Cases implemented | Status and limitations |
| --- | --- | --- |
| S5b, S5, N4–N6 | `Result` and `Option` propagation, overload resolution by exact source type, `.await?`, cleanup and ownership transfer. Two generated-C programs ran under fatal UBSan at `-O0` and `-O2`. One package executed and fourteen static refusals were checked. | P · Historical Rust execution; the self-hosted path now has the scoped evidence recorded in the core-extension cycle below. [Report](cycles/CORE_COMPOSITION_CYCLE.md#postfix-propagation-with-question-mark). |
| N4–N6, AS1–AS4, RT6–RT8, G2–G12, handles and async states in the region | Ten C-witnesses under UBSan at `-O0` and `-O2`nine targeted refusals. | P · Preserved native hand, scalar catch or scalar borrowing, Futures to `yield` at the level of the body. [Report](cycles/CORE_COMPOSITION_CYCLE.md#handles-et-contextes-async-en-région). |
| RT2–G12, regional state of a native thread Rust | Five C-witches with pthread under UBSan to `-O0` and `-O2`, including an injected launch failure. Four targeted refusals. | P · Immediate waiting, scalar catches named and datastacks isolated by worker. [Report](cycles/CORE_COMPOSITION_CYCLE.md#état-régional-des-threads-natifs). |
| G2–G12, HM1–HM5, VE1–VE2, Rust Collection Regions | Seven C-witnesses under UBSan at `-O0` and `-O2`, four targeted refusals and a region overtaking. | P · Primary value tables and reference vectors or allocations. [Report](cycles/CORE_COMPOSITION_CYCLE.md#collections-à-dépendances-et-régions). |
| G2–G12, datatack to Rust regions | Seven C witnesses, two controlled overtakings and three refusals of annotation. | P · `Vector<T>` with fixed elements without dependencies and `String` in pool in synchronous backend. [Report](cycles/CORE_COMPOSITION_CYCLE.md#datastack-à-régions-dans-le-backend-rust). |
| G2, G6, G10–G11, dimensioning of the classic datatack | Ten C-witnesses instrumented under UBSan to `-O0` and `-O2`, six refus d’annotation. | P · Explicit size, post-AST terminal and default. Accessible recursive calls processed conservatively. [Report](cycles/CORE_COMPOSITION_CYCLE.md#dimensionnement-de-la-datastack-classique). |
| N4–N6, E6–E7 and G1, provenances by position | Eight new C-witnesses under UBSan at `-O0` and `-O2` and six targeted refusals. | P · Synchronous contracts, fields and boxes, reborrowing and aggregates. Dynamic indices and unsolved recursion treated conservatively. [Report](cycles/CORE_COMPOSITION_CYCLE.md#provenances-par-position-et-match-emprunté). |
| N4–N6, A1–A4, E6–E7, G1 and G10 in the backend Rust | Fourteen C-tests under UBSan to `-O0` and `-O2` and ten static refusals. | P · Aggregated conservative sources and transfer of cleaning responsibility for a `A<T>`. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#dépendances-des-agrégats-et-transferts-de-pool). |
| G1, G2, G10 and Rust fixed type placement | Eight new C-witnesses under UBSan at `-O0` and `-O2`eight static refusals and four targeted enforcement checks. | P · Agregates without internal borrowings and local pools. [Report](cycles/CORE_COMPOSITION_CYCLE.md#extension-du-placement-des-types-fixes). |
| G1, fixed placement in the Rust compiler | Four C-witnesses under UBSan and inspection of the reservations issued. | P · Synchronous scalar field structures and automatic storage C. [Report](cycles/CORE_COMPOSITION_CYCLE.md#placement-fixe-dans-le-compilateur-rust). |
| G1, G2, G10–G12, classic datastack in the Rust compiler | Seven C-witnesses under UBSan at `-O0` and `-O2`, plus two controls with reduced capacity. | P · Fixed types currently lowered by the synchronous backend. [Report](cycles/CORE_COMPOSITION_CYCLE.md#datastack-à-curseur-dans-le-backend-rust). |
| Scope, Liaison, Call and Capture Representations | Aucun. | Syntactic projection of 2,766 programs and fragments on 82,807 tokens. [Perimeter and limits](cycles/CORE_COMPOSITION_CYCLE.md#parcours-du-corpus-sans-arrêt-darbitrage). |
| Frontend Rust | Comparison of representations, without program executed. | 2,758 common occurrences, 2,690 fully consistent projections. [Perimeter and deviations](cycles/CORE_COMPOSITION_CYCLE.md#frontend-rust-et-comparaison-du-corpus). |
| Auditor Rust and C, N1–N8 | Four C witnesses under UBSan, six refusals targeted. | P · Synchronous scalar sub-assembly and local lexical borrowing. [Report](cycles/CORE_COMPOSITION_CYCLE.md#vérificateur-rust-et-génération-c-du-sous-ensemble-scalaire). |
| Auditor Rust, N5–N6 | Six C-witnesses under UBSan, five targeted refusals. | P · Last use of local references and re-use of scalar loops. [Report](cycles/CORE_COMPOSITION_CYCLE.md#graphe-de-contrôle-dernier-usage-et-boucles-dans-le-rust). |
| Auditor Rust, N4–N6 and N8 | Eight C witnesses under UBSan, eight refusals targeted. | P · Scalar reborrowing, parameters, returns and loops with result. [Report](cycles/CORE_COMPOSITION_CYCLE.md#réemprunts-contrats-de-références-et-boucles-à-résultat-en-rust). |
| N4, N5, N6, N8 | No cases executed for the latest compiler changes. | Validation carried forward at user request. Progress and limitations in [cycle report](cycles/CORE_COMPOSITION_CYCLE.md#implémentation-partielle-de-n4-n5-n6-et-n8). |
| N2, N4–N6 | Scalar references captured, mutable reference transfer, closure call after `yield`, handwriting before and after `join`. | P · Scalar Perimeter. |
| N4, RT7–RT8 | Aborted a conditional wrapper result, cleaning and recycling before closing the context. | P · Scalar captures and results. |
| HM1–HM6, N4 | HashMap scripts propagated on constant keys, relays, conditional alternatives and refusal of a target too short. | P · Shared scalar references. |
| MT10 | Lock relayed in a proprietary field or vector option, refusal to resume during the ticket's life. | P · Synchronous trajectories. |
| RT4–RT5, RT7–RT8 | `spawn` and `thread` called in async, local distinction with `AsyncHandle` through displacement, `if` and `break`, relays of annotated wrappers. | P · 8 tests to `-O0` and 24 to `-O2`. Passage d'`AsyncHandle` via a signature still open. |
| N2, N4–N6 | A closure captures a shared reference and calls twice a contract function type. Refusal of capture not Copy without `move`. | P · Targeted regression, C-control under UBSan. |
| N4, RT5, RT7 | Transfer from an autonomous AsyncHandle to an async parameter, expectation, LaunchFailed and inactive destruction. Abandon with copied digital array, refusal with borrowed array. | P · 10 tests to `-O0`, 66 à `-O2`. Handles with outbuildings and open returns. |
| AS7, RT7 | Repeated drop-offs in sync and async loops, direct calls and via a sync auxiliary, with and without explicit capacity. | P · 67 tests to `-O2`Relays via async tasks still open. |
| HM1–HM6, N4 | Play a scalar reference entry via a table borrowed by a function. No changes until the end of the loan. | P · 20 HashMap and lock-to-lock tests `-O2`, native witnesses under UBSan. |
| AS7, RT7 | Abandoned by an async task or a branch wrapper called in async. | P · Targeted test at `-O0` and 36 tests at `-O2`. Analyse conservative. |
| N1, N2, N4 | Signatures of closures with structure borrowed as input or structure with scalar fields as result. Unused bodies verified and return executed in C. | P · 17 tests at `-O2`. Returns to still open outbuildings. |
| N2, N4–N6 | Capture of a nominal mutable reference and re-borrowed in reading in the closure. Two readings, refusal of the old link and writing, resumed after drop. | P · Witness to `-O0` and 28 tests at `-O2`. |
| N1, N4–N6 | Borrow returned from the parameter of a closure, via a function. Last read and mutate after it. | P · 29 tests to `-O2`. The origin of a still open scalar reference. |
| N4–N6 | Shared scalar reference captured and returned, reading after destruction of the closure, refusal of early writing and a local target escaped. | P · 2 tests to `-O0` and 30 to `-O2`. Capture exclusive encore ouverte. |
| N4–N6 | Shared view returned from a scalar or nominal exclusive capture. Refusal of writing and protection of the nominal holder until the last reading. | P · Witness to `-O0`31 tests to `-O2`. |
| N4–N6 | Nominal reborrowing returned from an exclusive capture, then reading after destruction of the closure or return of a relay function. | P · Witness to `-O0`41 and 13 tests at `-O2`. |
| HM1–HM6, N4–N6 | Nominal reference shared by input, reading, withdrawal, key independence and refusal of a local target escaped. | P · Witness to `-O0`39 tests to `-O2`. |
| HM1–HM6, N4–N6 | HashMap shared references to online structures. Dependence of the projected field, modifiable brother field, retention after removal. | P · 2 tests to `-O0`, 45 à `-O2`. |
| HM3–HM4, N2, N4–N6 | Nominal mutable reference transferred to an input and then returned to the withdrawal. Control of the old link, target and brother field. | P · Witness to `-O0`38 tests at `-O2`. |
| EBNF, RT3, RT8 | Annotation of the naked branch, method call and await. Refusal of forms badly written to parser alone. | P · 2 syntactic tests, 10 core regressions. A pre-existing native semantic control fails. |
| EBNF, RT3 | Free and structural annotations stacked, with or without `with`, on the signature of spawn. | P · Validated syntax. 5 annotations tests and 10 regressions of the core pass. |
| EBNF, type paths | Qualified names in a signature of closure, HashMap and AsyncHandle, and refusal of incomplete paths. | P · 7 targeted tests. Solving names out of this pass. |
| EBNF, G6, AS7 | Splitter of core guidelines, K/M/G sizes and qualified pool name. | P · 16 targeted tests. |
| EBNF, arms lists | `match` enum and Option with mandatory separators, optional final comma and refusal of empty list. | P · 42 targeted tests. |
| EBNF, match patterns | Syntaxic tree of intertwined patterns, unity, joker and fields. Refusal of poorly formed patterns. | P · 17 targeted tests. |
| EBNF, interlocked and closed types | Generic arguments borrowed and separators of the enclosure lists. | P · 34 targeted tests. |
| EBNF, types of slices | Shared and mutable bands with numerical or nominal element, and refusal of a loan-free tranche. | P · 35 targeted tests. |
| EBNF, types and literals | Syntax of AsyncHandle signatures and u8 annotated integers before typing checks. | P · 18 targeted tests. |
| EBNF, declarations and lock | Qualified impl, lock forms, empty enum and refusal of poorly formed syntax. | P · 25 targeted tests and two replayed syntactic tests. |
| EBNF, value paths | Qualified appeal, qualified value and qualified appeal followed by .await. Refusal of poorly formed paths. | P · 21 targeted tests and replayed syntactic control. |
| EBNF, digital literals | Decimals, range, comparison and conservation of an integer off-limits to parser alone. | P · 22 targeted tests. |
| EBNF, moving headers | Entries named at the head of block, capture block with value and refusal of entry after instruction. | P · 11 targeted tests. |
| EBNF, final block expression | Final expressions in interlocked blocks and functions, before checking the return. | P · 23 targeted tests. |
| EBNF, instructions d'expression | Digital, parenthesive and nominal expressions with semicolon in a block. | P · 35 targeted tests. |
| EBNF, places | Fields, indices and de-references combined in a assignment, with refusal of poorly trained places. | P · 35 targeted tests. |
| EBNF, suffixes | Fields, clues and method calls chained to an expression. | P · 35 targeted tests. |
| EBNF, pool initialization | Suffixe .new on call or field, named or positional values and rejection of mixed forms. | P · 34 targeted tests. |
| EBNF, programme | Root-level declarations and capacity guidelines. Refusal of root and interlocking statements. | P · 32 targeted tests. |
| EBNF, G6, blocs | Region directive on a body, if branch or match arm. Refusal outside an authorized block. | P · 34 targeted tests. |
| EBNF, conditionnelle | Optional branch else to parser alone, including after else if. | P · 25 targeted tests. |
| EBNF, unaire | Dereference of parenthesed or postfixed expression, priority and refusal of poorly trained operands. | P · 40 targeted tests. |
| EBNF, extern C | External signature and ordinary call before unsafe context verification. | P · 17 targeted tests. |
| EBNF, profil core | Syntax of the core with str and without explicit numerical type. Refuse of old transfer arrows. | P · 48 targeted tests and replayed control. |
| EBNF, expressions primaires | Unity and immediate appeal of parenthesed closure, with refusal of ill-written forms. | P · 50 targeted tests. |
| EBNF, chemins builtin | Qualified conversions and error variants before member and integer checks. | P · 26 targeted tests. |
| EBNF, receveur | Forms borrowed and by value, refusal of an absent or ill-placed recipient. | P · 25 targeted tests. |
| EBNF, construction enum | Variation with or without fields and disambiguation of the game block. | P · 34 targeted tests and replayed syntactic control. |
| EBNF, tailles | Unsigned whole size in a table type, a repeat and a pool, before representation checks. | P · 35 targeted tests. |
| EBNF, AS7 | Unsigned third parties of capacity directives before representation check. | P · 18 targeted tests. |
| EBNF, G6 | Positive region size beyond representation and zero refusal to parser. | P · 19 targeted tests. |
| EBNF, identifiants | Refusal of the names reserved in the declaration position and acceptance of `self` as a recipient and `_` in a pattern. | P · 36 targeted tests. |
| EBNF, initialization and unit | Qualified expression in `.new(...)`, refusal of qualified or reserved fields and of the pair syntax of slices in type position. | P · 36 targeted tests. |
| EBNF, pool and patterns | `Pool<&mut i64>::new(4)` recognised to the parser, incomplete type refused; reserved identifiers refused in the reasons for variants, `_` recognized as a field pattern. | P · 39 targeted tests. |
| EBNF, type and branch contracts | Accepted borrowed alternatives, list of empty methods and reserved identifiers refused. Distinction of name and type of recipient verified on the compilation path. | P · 39 targeted tests, including one witness of the separation of routes. |
| EBNF, lancement | An expression required for `spawn` and `spawn_blocking`, including synchronous synchronous syntactic context. | The extended suite of reports indicates two assertions related to the expectation of an independent thread, detailed in the report. |
| EBNF, RT8 | Named catch identifiers, analysis of `yield` and `.await` independent of context. | P · 42 targeted tests, including refusal of suspensions in a thread block when compiling. |
| EBNF, suffixes, TX4 | Arguments of ordinary calls kept before the random check, range of `try_slice` described in EBNF. | P · 41 targeted tests. |
| EBNF, integrated manufacturers | Mutex with a commaless expression, HashMap with eligible key and refusal of `new(source) Int(...)` To the parser alone. | P · 42 targeted tests. |
| EBNF, paths and types | Standard segments of skilled roads, integrated types recognized in their positions and refusal of `A` seul, `Execution<T>` and `runtime::Future`. | P · 44 targeted tests. |
| EBNF, single operators | `&mut text[1..3]` kept at parser alone, empty index refused and diagnosis of mutability kept in compilation. | P · 44 targeted tests. |
| EBNF, affectation | Simple target, projection since `self`, compound operators and refusal of designated identifiers in targets. | P · 45 targeted tests. |
| EBNF, block result | Bloc simple, capture `move`, `unsafe`, `if`, `match` and `loop` recognized as a result at the end of the block. | P · 46 targeted tests. |
| EBNF, inum construction and block | Empty accolades recognized as block of `if` ou `while` when a block is required, and kept as initialization when another block follows. | P · 47 targeted tests. |
| EBNF, value paths | `self.champ` and recognized integrated paths, names reserved in value or field position and runtime calls out of core refused. | P · 48 targeted tests. |
| EBNF, pattern paths | Recognised ordinary and integrated qualified grounds, reserved segments and incomplete runtime paths denied. | P · 49 targeted tests. |
| EBNF, conversions | Complete borrowed type after `as`, priority of successive conversions and refusal of poorly trained types. | P · 61 targeted tests. |
| EBNF, point of entry | External statements and async of `main` recognised syntaxically, external form with body refused, control of `main` external storage in compilation. | P · 78 tests, including subsequent integration of the core. |
| EBNF, G6 | A block-by-block regional directive, annotations of interlocked blocks and retained terminals. | P · 57 tests, including subsequent growth annotations. |
| EBNF, links and catches | Pair and `type feature` historical refusals to parser alone, import named followed by a closure `move` reconnu. | P · 58 targeted tests. A historical assertion fails in the expanded suite. |
| EBNF, terminaux | `::` adjacent to a nested type, closing `>>` followed by `=`, split separator by space, line jump or rejected comment. | P · 73 targeted tests. |
| EBNF, CLI | `check --syntax-only` accepte `yield;` in synchronous body, refuses `yield` without semicolon and does not combine with `emit-c`. | P · 4 witness's CLI calls, 2 calls on `let_mutability.crust` and 50 targeted tests. |
| EBNF, primitive and key | `i32` stored in ordinary and external signatures, annotations and nested types. Key `Int` history refused to parser alone. | P · 74 targeted tests. |
| EBNF, signatures | `A<i32>`, `bool`, `&[u8]` and `runtime::AsyncHandle<i64>` kept before lowering and recording the types of compilation. | P · 76 targeted tests. |
| EBNF, instructions | Appels `bool()` and `runtime()` and terminal values `bool` and `_` refused even when the parser returns to reading an instruction. | P · 63 targeted tests. |
| EBNF, constructions and suffixes | Appeal and `.await` The link shall be recognised when the link has the same name as a declared enum. | P · 62 targeted tests. |
| EBNF, compound empty block | Operator and suffix attached to the `if` when the interpretation of the braces as initialization leaves the `if` - No block. | P · 64 targeted tests. |
| EBNF, Receiver and SL1 | `self` documented as value and assignment base, nude call `self()` SelectGroup productions identified as deferred. | P · 54 tests targeted at parser and displacement. |
| EBNF, demonstration | Public example with `Pool<Message>`, `memory.new`, retour `A<Message>` and `match` on loan. | P · 3 CLI calls and 55 targeted tests, including the existing destruction and recovery trace. |
| EBNF, retours conditionnels | Example migrated to `A<i32>` with returns by value and `drop`. | P · syntax, verification and execution by CLI. Oracle on four addresses, two results and four cleaning events. |
| EBNF, returns with loan | Two examples migrated to `A<View>` and `data.vref()`. | P · two successful syntactic analyses, valid execution `View.Item(42)` and refusal to return a local target. |
| EBNF, suffixe `try_slice` | Range, ordinary call without argument and ordinary call to two distinguished arguments to parser alone. | P · 54 targeted tests. |
| EBNF, parser regression | Cross-sectional replay of witnesses calling directly `parse_syntax` in the five suites concerned. | P · 57 successes. |
| EBNF, generic closures | `A<i32>==other`, `A<i32>>=other`, `A<i32>>>2` and three generic levels recognized in their context. `>>>` and `>>=` Isolated are refused. | P · 78 targeted tests. |
| EBNF, immediate call for closure | `(move \|\| {42})()` accepted, grouping without appeal accepted, appeal of an interlocked grouping or of a parenthesed name refused. | P · 54 targeted tests. |
| EBNF, nom `pool` | Builder with nested or closed type, ordinary call `pool()`, method, comparison with distinguished parenthesis and comparison. | P · 71 targeted tests. |
| EBNF, TX1 | JSON slashes of text literals, standard in TX1. | P · 11 accepted forms with bytes checked and 7 confirmed refusals. |
| EBNF, N1 and N3 | Closing signatures `fn`, `&fn`, `&mut fn` and liaison received `mut f`. | P · 35 targeted tests. Syntactic assertions distinguish the mode of the parameter and the borrowing of the result. |
| EBNF, structural construction | Name shared by a structure and a link in condition. Empty block, instruction block and initialization with distinguished field. | P · 65 targeted tests. |
| EBNF, diagnostics d’expression | Un `match` vide sous 20 `if` keeps his diagnosis and each block is read only once. `1 + ;` reports the semicolon received in place of the operand. | P · witness instrumented 21 readings and 67 targeted tests. |
| N4, RT7–RT8 | Modernized witness: abandonment of the accepted autonomous handle, taken capture refused to exit or to abandon explicitly without waiting. | P · 70 targeted tests, control and generation C on all four variants. |
| EBNF, regression of integration | Joint digital, contract, travel, direction, threads and integration. | P · 124 successful methods and 5 examples accepted via `check --syntax-only`. |
| TF1, historical regression | `type feature` refuse `fn a(self);` and keeps the receiving modes documented. | P · 92 successful methods, including full follow-up of type contracts. |
| EBNF, call and async types | `copy([1, 2])` No Vector or Result records in the parser's async witness. | P · 71 targeted tests and one instrumented control. |
| EBNF, CLI, TX1 | Valid UTF-8 source accepted, invalid byte located and refused without exception Python displayed. | P · 4 CLI calls, two of which are on the main example. |
| EBNF, integration programmes | Programs compiled later `test_core_integration` read the parser alone. | P · 30 successful tests, 42 programs accepted to parser and 2 expected refusals of experimental scheduler. |
| EBNF, production review | Correspondances between productions, parser methods and controls in the cycle report. | P · 61 successfully syntactic tests. Slashes and SelectGroup reported separately. |
| EBNF, borrowed fields | Examples in `i32`, `pool.new`, `.vref()` and `drop`. | P · two successful syntactic analyses, output `42`, refusal of the `drop` The auditor's limitations in the report. |
| EBNF, game completeness | Incomplete core program and missing arm variant added. | P · 4 CLI calls: both go to parser, only the comprehensive program passes the audit. |
| EBNF, N6 | Replacement between pools with named result, then by `second.new(...)`. | P · syntaxe, compilation, sortie `10`, `20`, `30` and trace verified. Direct assignment of a call result accepted by the parser, then refused. |
| EBNF, retours d’emprunt | Shared and mutable returns with explicit borrowing of the content of `A<i32>`. | P · 2 CLI analyses, 2 executions with verified address identity and 2 README extracts analysed and verified. |
| EBNF, flow control | `conditionals`, `if_expression`, `loop`, `continue`, `while` and `scope_exit`. | P · 6 syntactic analyses and 6 successful executions. |
| EBNF, Drop and Displacement | Four examples of core with borrowing content by `.vref()`destruction and re-use of slot. | P · 4 syntactic analyses, 2 successful executions and 2 expected semantic refusals. |
| EBNF, P8 and provenance | Construction d’un `Message` in a `Pool<i32>`, return of an allowance from a local pool. | Both pass to the parser and are refused with the expected diagnosis. |
| EBNF, order of arguments | Reading before transfer and allocation passed directly as argument. | P · execution with verified values and destruction, reverse order accepted to parser and refused to auditor. |
| EBNF, mutable borrowed field | Retour `A<Writer>`, capture of `.mut_vref()` and access to the target. | P · successful syntactic analysis and execution, writing before last use refused by the verifier. |
| EBNF, provenance conditionnelle | Two pools, return per value from one of the two and re-use the other slot. | P · 2 syntactic analyses and 2 executions with oracle of addresses and values. |
| EBNF, N3–N4 | Move to a block, new receiver, argument consumption and back from a local pool. | P · 4 successful syntactic analyses and 4 expected refusals of verification. |
| EBNF, named types and qualified calls | The parser shares the arguments of type and keeps comparisons with `<`. | P · AST Structure Rust Test and Syntax Refused, 3,110 occurrences recognized before and after, eight successful Rust validation suites. [Report](cycles/CORE_COMPOSITION_CYCLE.md#régression-du-parseur-sur-le-corpus). |
| Single-package modules | File-local grouped imports, aliases, visibility and collision diagnostics. | P · One package executed under UBSan at `-O0` and `-O2`, nine refusals confirmed. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#single-package-modules). |
| Crust bootstrap package loading | Resolve file-local imports and preserve their visibility when emitting a package through `crustc`. | P · The native self-hosted binary passed package regressions on macOS ARM64. The native and fatal UBSan binaries both reproduced their own C byte for byte and passed `--require-parity` on all 273 accepted programs. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#crust-package-bootstrap). |
| Installed `crustc build` | Resolve `std` relative to the installed binary, build a package, and preserve the previous executable on failure. | P · Native and fatal UBSan compiler builds exercised the external two-module package and three failure cases on macOS ARM64. The installed compiler rebuilt itself with `build`, and the resulting binary ran the external package again. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#installed-package-build). |
| Package dependencies and bundled std | Local and transitive paths, pinned Git commit, explicit std import, and direct-dependency visibility. | P · Package executed under UBSan at `-O0` and `-O2`, seven additional refusals. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#package-dependencies-and-bundled-std). |
| Dependencies in `crustc build` | Resolve local and pinned sources, enforce direct dependency visibility, and keep local paths inside a Git checkout. | P · The native and fatal UBSan compilers matched Rust on macOS ARM64 and passed nine refusals. A separate local SHA-256 repository built successfully. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#dependencies-in-crustc-build). |
| Target selection | `#(if: ... { ... })` filters imports and declarations before resolution. | P · Linux and Windows selections executed as portable C under host UBSan; active collision, invalid property and malformed annotation rejected. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#target-selection-before-imports). |
| N7 — Custom destructors | Explicit drop and scope exit after transfer, parent before owned fields, empty default, and async capture cleanup. | P · Three programs under UBSan at `-O0` and `-O2`; four refusals. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#custom-destructors). |
| N1–N3, N7 — Tuples | Positional inference, function returns and consuming destructuring of pairs and triples. | P · One program under UBSan at `-O0` and `-O2`; four refusals. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#tuples-and-destructuring). |
| README examples | Four Din programs per language version compile and run. The Rust vector example runs with an assertion. | P · Corpus rebuilt, 34 documentation snippets accepted. [Report](cycles/CORE_COMPOSITION_CYCLE.md#documentation-layout-and-readme-examples). |
| README fixed-capacity pool | The third allocation reuses the first slot while the second allocation remains live. | P · Both README snippets compiled and printed 10, 20, 30. Keeping the first slot occupied caused the expected pool exhaustion. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#readme-fixed-capacity-pool-example). |
| EBNF, inventory of examples | The 46 files `.crust` d’`examples` read the parser alone. | P · 31 accepted, 14 historical refusals and a refusal of the old `runtime::select`. |

[Report and limitations](cycles/CORE_COMPOSITION_CYCLE.md)

<a id="écarts-reproduits-en-syntaxe-du-noyau"></a>

## Reproduced kernel syntax deviations

| Rules | Cases implemented | Status and limitations |
| --- | --- | --- |
| N4–N6, N8, E6 | Return of `&mut i32` projected from an array by a task and then recovered by `join()`, and projections of rows of references. | Replicated deviation · Python exception to both compiler inputs for the minimum control. |
| N1, AS4 | `bool` sent back by `join()`, by `match h.await`, then by a `if` combining a expected result and a boolean. | Replicated deviation · The first witness passes into C. The other two reveal an absent field C and a refusal to type. |
| N1, V1 | Liaison `i32` initialised with a `A<i32>`. | Replicated deviation · Accepted at both entries and still deferencable in the generated program. |
| N1, E4 | Writing async in a box `i32` with a literal, then with an annotated variable. | Replicated deviation · Literal rejected. Annotated witness produced `12` C under UBSan. |

[Strike of failures and witnesses](CORE_FAILURE_TRIAGE.md)

<a id="retour-dune-allocation-denum-dans-le-core"></a>

## Return of an enum allowance in the core

| Rules | Cases implemented | Status and limitations |
| --- | --- | --- |
| N1, N2, N6–N7, B4a, B4c, L1–L3, P9 | Construction of two variants with `Pool<E>.new`, retour `A<E>`, passage of the two arguments by value, trace of destruction, refusal of the wrong type of pool. | P · Migrant and module cases `test_arguments` executed under UBSan. |

[Report and newspapers](cycles/ENUM_CORE_VALIDATION_CYCLE.md)

<a id="contrats-de-verrou-et-hashmap-depuis-le-code-source"></a>

## Locking contracts and HashMap from source code

| Rules | Cases implemented | Status and limitations |
| --- | --- | --- |
| MT10, N2, N4, N6–N7 | Reacquisition according to the order of destruction of an argument, synchronous relay, transfer capture, abandoned task before launch, success and `LaunchFailed` of the `join()`, conflit pendant l'attente. | P · Compilation and execution tests under UBSan. The transport tested returns a direct owner result. The implementation provides the real lock. |
| HM1–HM2, HM4–HM5 | Comparison to reference dictionary, replacement, extraction, reindexing, address stability, re-use of locations and capacity exhausted without modification. | P · Tests from Crust and native probes under UBSan. The failure test injects a reduced capacity into the generated C. |
| HM3, HM6 | Shared or exclusive loans on the table, last-use release, search-limited key loan, nominal values, separate pools and replacement of a stored reference. | P · The known keys isolate the dependencies by input. An indeterminate key retains a prudent union. The passage of dependent tables by contract remains to be integrated. |
| HM6, N4–N6, N8 — backend Rust | The known keys isolate their dependencies. A synchronous replacement contract transmits the new provenance to the appellant. | P · 21 programs and 13 refusals in the collections suite. Dynamic keys and conditional effects treated by union. Local delayed effects exercised on thread/join and spawn_blocking/await, including LaunchFailed. Synchronous waiting contracts and async and native factory exercised. Synchronous replacement recursion exercised. 42 programs and 21 refusals in the tasks suite. See the batch dedicated to the hands below. |
| N4–N6, AS3–AS4, RT5–RT8 — interlocked and recursive handles | Recursive expectations and sync and async relays, back from a worker, mutual recursion and recursive enum type via a handle. Injected launch failure and premature access denied. | P · 53 C programmes under UBSan to `-O0` and `-O2`, 24 refusals. Limitations in [report](cycles/CORE_COMPOSITION_CYCLE.md#handles-imbriqués-et-récursifs-dans-le-backend-rust). |
| N4–N6, AS3–AS4, RT5–RT8 — Collection and recursive contracts | Extraction from pools and vectors, path shift after `remove`, async suspension and recursive relays that wait or return. Refusal to abandon the dependent vector. | P · Two Rust tests, eight C. 60 programs of the post-work in UBSan to `-O0` and `-O2` and 25 refusals. [Report](cycles/CORE_COMPOSITION_CYCLE.md#handles-en-collection-et-contrats-des-cycles-récursifs). |
| N4–N6, RT5 — emptying of handle vectors | Dynamic index on a single box, emptying of unknown length by `pop()` and `join()`, refusal of access after an early exit. | P · Two controls targeted under UBSan at `-O0` and `-O2`, a static refusal and an out-of-bound index stoppage. [Report](cycles/CORE_COMPOSITION_CYCLE.md#déduction-de-la-case-unique-et-vidage-dun-vecteur-de-handles). |

[Report and newspapers](cycles/HASHMAP_LOCK_INTEGRATION_CYCLE.md) ·
[Initial circle of native probes and marker](cycles/CORE_LOCK_HASHMAP_CYCLE.md)

<a id="annotations-demprunt-et-littéraux-à-travers-mut_vref"></a>

## Borrowing and literal annotations through mut_vref

| Rules | Cases implemented | Status and limitations |
| --- | --- | --- |
| N1, N3–N5, H1, brouillon 07 | `let vue: &i32 = nombre.vref()`, writing of `20` via `mut_vref()`, mutable annotation or inference. Refusal for bad fashion, bad type, a `drop` premature or a literal out-of-bound. | P · Native execution under UBSan and refusal to both source inputs. A direct borrowing annotation async is also exercised after `yield`. |

[Report and newspapers](SAFETY.md#annotations-demprunt-et-littéraux-à-travers-mut_vref)

<a id="effets-de-dépendance-après-executionawait"></a>

## Effects of dependency after execution.await

| Rules | Cases implemented | Status and limitations |
| --- | --- | --- |
| N4–N5, AS8, MT9 | Local mutex and targets reserved for capture, then while waiting. Refuse to destroy one of the targets or mutex, to have it read by another call and to hold a target too short. | P · Shared field `&i32` written by a Void task, access to the reserved mutex until the end of the waiting. |
| N4–N5, RT5–RT6 | Direct match and result named immutable. `2` and `1` on the first failed child submission. Unique destruction and refusal to destroy the still stored target or to reuse an outdated status. | P · Native execution under UBSan and refusal to both source entries. |

[Report and newspapers](SAFETY.md#effets-de-dépendance-après-executionawait)

<a id="effets-de-dépendance-des-tâches-sous-garde"></a>

## Dependence effects of custodial duties

| Rules | Cases implemented | Status and limitations |
| --- | --- | --- |
| N4–N5, AS8, MT9 | A task replaces a `&i32` The contract names the field and target, and the appellant controls its life. Target too short, destruction before join and concurrent reading refused. | P · Mutex locally owned by the synchronous caller, reserved up to the join. |
| N4–N5, RT5–RT6 | Success and failure of injected submission. Destruction of the old or new target on the arm, reading the remaining field, refusal of inverse destruction. A conditional writing or an ignored status retains the possible provenances. | P · Void Task, shared field `&i32`, direct match or on a result named immutable. |

[Report and newspapers](SAFETY.md#effets-de-dépendance-des-tâches-sous-garde)

<a id="clôture-du-lot-dintégration-du-noyau"></a>

## Close the kernel integration batch

| Rules | Cases implemented | Status and limitations |
| --- | --- | --- |
| N3–N5, N7, MT9 | Remplacer `&i32` and `A<Item>` under sync/async custody on assignment or via sync auxiliary. Reuse the old slot and observe a single destruction of the new field. Refuse the drop before next reading as well as a target or too short pool. | P · Local mutex without further borrowing. Change of origin of a shared mutex or by a child-like task refused. |
| RT3, RT4–RT8 | Check default refusal and option success for `check`, `effects`, `emit-c`, `build` and `run`. Exercise the launch and wake-up integrated into the regression suites. | P · Custom scheduler without target grammar and exposed only in experimental mode. |
| Drafts 02 and 07, N2–N4, AS2, AS8, RT7 | Examples without transfer arrows. Defaults `i64` and `f64` without annotation. Return and consumption of `A<Holder>` via a task with re-use of the slot. Separate replay of historical assertions. | P · Historical compatibility retained for scenarios that exercise this syntax or `reset()`. |

[Report and newspapers](SAFETY.md#clôture-du-lot-dintégration-du-noyau)

<a id="retours-async-charges-gardées-et-placement-local"></a>

## Async returns, guarded charges and local placement

| Rules | Cases implemented | Status and limitations |
| --- | --- | --- |
| N3–N5, AS4, AS11–AS12, RT5, MT6 | `&mut u64` by `.await` direct, `.await` on handle and `join()`, including return by auxiliary. Projection of a field `&f64`. Refusal of access before the end of the loan and refusal of a local target. | P · C pointers typed and source retained in the cases executed. |
| N4–N5, MT1, MT7–MT9 | Borrowing load and proprietary field by mutex sync/async. Two tasks mutate the target of a mutable borrowed field under the same lock. Refuse to destroy the target or guard too early, then single destruction and reuse of the possessed allocation. | P · Structures represented. Change in the source of a field of dependency in custody remains open. |
| L7, brouillon 03 | Return of a local structure with a `if` read before or after its creation. C builds the value in the parent reservation and recovers the temporary before the result. | P · Two valid refusals reproduced and corrected. |

[Report and newspapers](SAFETY.md#cycle-des-retours-async-et-charges-gardées)

<a id="runtime-intégré-du-noyau"></a>

## Integrated kernel runtime

| Rules | Invariant and executed cases | Status and limitations |
| --- | --- | --- |
| RT2, AS4, AS8–AS9 | Exclusive recovery and stable condition. Competitor wake-ups during a poll, no active second poll, resumed on another thread with preservation of a local loan. | P · Independent model of availability and synchronised C performances. |
| RT2, AS4, MT9, SL1 | Useful wake-up after `Pending`. A mutex expected behind two `.await` Directly receives the ticket from the root task. Alarm during a poll, nested selection, waiting for a handle, late tickets and re-use of an entry. | P · Exercised chains and FIFO and Select models, without general proof of fairness. |
| AS10, AS14, RT5–RT8, MT7, SL1–SL2 | Upon completion, direct children are released. The root state and the owner capture remain alive until the `join`. Extraction, single destruction, re-use of the slot and second waiting refused. Re-start of the failures of launch and the cleaning of losers. | P · C-runtime claims and source refusal for waiting obligations. |

[Report and newspapers](SAFETY.md#cycle-du-runtime-intégré--9-novembre-2026)

<a id="dernier-lot-du-noyau"></a>

## Last kernel batch

| Rules | Cases implemented | Status and limitations |
| --- | --- | --- |
| RT3, RT8 | Two installations in exclusive branches, installation after a native launch via a function, after another installation or on a loop resumption. | P · Check and compile checks paths, and the runtime keeps its control. The effect of auxiliary functions is conservatively summarized. |
| N3–N5, AS2, AS8, brouillon 07 | Emprunt mutable d'un champ `u64` after `u8`, borrowed return from a sync auxiliary, sync call transfer after `yield`, loaning a local scalar to a task. Rejection of access to the target before the join. | P · The fields of the digital profile have a step in line. Wide-borrowing returns from an async function remain open. |
| MT9 | A scalar field structure is transferred to a `AsyncMutex`, borrowed by his custody and transferred by a child suspended. The charge is destroyed once. `i64` and refusal to destroy custody during a loan. | P · Scalar loads and scalar-field structures. Loads containing references or allocations and more general compositions remain open. |
| L7, drafts 03 and 05 | Parent reservation for a `if` of which only the branch that continues provides a value. `return` and cleaning check in both cases. | P · The plan remains limited to the builders and paths identified by the compiler. |

[Batch report](SAFETY.md#dernier-lot-du-noyau--9-novembre-2026)

<a id="intégration-du-noyau"></a>

## Kernel Integration

| Rules | Cases implemented | Status and limitations |
| --- | --- | --- |
| Brouillon 07, N2/N4, AS2/AS8 | Default `i64`, mixed fields, alignment of `i32` after `u8`, reservation of a compound place, exact conversion through `yield` and `.await`, pool `u64` local and allocated catch. | P · Historical profile always available. Direct borrowings of wide fields and general async signatures open. |
| Brouillon 02, RT8 | `move a;` and `move { ... }` The original scalar is still accessible. The original owner is no longer accessible. | P · Comparison of output C and refusal to both entries. |
| RT2–RT5 | Installation in `main`, signatures of callbacks, future consumption, start of a polluter, alarm clock `yield` and `LaunchFailed` observed in the join. | P · File C provided. Public Poll and file written in Crust open. |
| MT9 | Resumed sync verrou after exit of range, refusal of drop with a guard, refusal of a sync guard on suspension, two competing increments, reborrowing async of `i32`. | P · Scalar constructors and borrowings in the tested perimeter. |
| FFI1–FFI6 | Scalar types, multiple sources C, call after suspension, absent symbol, NaN and infinite rejection, conservation of `-0`, call out unsafe and use after drop refused. | P · Backend C and ABI native to this execution. |

[Report of the cycle](SAFETY.md#cycle-dintégration-du-noyau--9-novembre-2026)

<a id="grammaire-du-noyau-cible"></a>

## Target kernel grammar

| Rules | Cases verified | Limites |
| --- | --- | --- |
| S1, S4–S6, drafts 02 and 07 | Blocs, `move` In the head, capture by value, primitive retained expressions, branches and loops. The old transfer arrows are rejected by the target grammar. | Checking the syntax on a selection of sources. Typing and memory security followed separately. |
| AS1, AS3–AS4, AS7, RT4–RT8, SL1 | `async fn`, `yield;`, suffixe `.await`, two forms of launch, native thread, `join()`, `runtime::select` The two modern forms of thread capture are recognized. | Modern thread catches are checked syntacticly. The sync/async context and waiting obligations are the responsibility of the auditor. |
| Draft 07, floating literals | Forms `1.5`, `1.` and `.5` and annotation `f32` are recognized. `1..3` The exponential notation and type suffixes are rejected. | Typing and performances in the digital cycle below. |
| F4, brouillon 07, logique | Four cases of syntax distinguish `!`, `!=` and conditions of `if` ou `while`. [Journal](../validation/core-grammar-boolean.log) | Grammar recognizes `if 7 {}`. The requirement for `bool` is the target type. |
| Draft 07, bit-to-bit operations | Five cases of syntax exercise `&`, `\|`, `^`, `~` and the distinction between borrowing and binary AND. [Journal](../validation/core-grammar-bitwise.log) | The type and width are exercised in the digital cycle. |
| Draft 07, offsets | Five cases of syntax distinguish `<<`, `>>`, comparisons and interlocking type closures. [Journal](../validation/core-grammar-shifts.log) | Static and dynamic controls are exercised in the digital cycle. |
| Draft 07, compound assignments | The lexer and parser agree on all ten compound operators. The parser distinguishes adjacent `>>=` from separated tokens and from nested generic closers followed by `=`. | Rust and Crust corpus comparison; see the [cycle report](cycles/CORE_COMPOSITION_CYCLE.md#compound-assignments-in-both-compilers). |
| RT3, MT9, FFI1–FFI5, brouillon 07 | 53 replayed syntax cases, 15 new cases for `set_scheduler`, `Future`, `TaskId`, mutex, digital error and calls C. No deviation. [Journal](../validation/core-grammar-interfaces.log) | The scope of the `unsafe`, the installation site and the contract of the scheduler are the responsibility of the verifier. `--c-source` is under the responsibility of the LTB. |

[Grammaire](../CORE_GRAMMAR.ebnf) · [Report and newspapers](SAFETY.md#cycle-de-la-grammaire-du-noyau)

<a id="noyau-numérique"></a>

## Digital core

| Rules | Cases verified | Status and limitations |
| --- | --- | --- |
| 07 · Primitives, literals and context | The strings and the sign, the same families and widths, parameters, returns, homogeneous table and results of the `if`, `match` and `break`. | P · Digital profile. Fields and compatibility detailed in the integration cycle. |
| 07 · F4/F5, arithmetic and logical | Overflow, null divider, quotient and remains signed at the terminal, rounded even, null floating result, subflux, short circuit, binary operations and signed offset. | P · Diagnosis of native C constants and controls under UBSan in cases exercised. |
| 07 · Conversions, indices and lengths | `as` checked on the source type, `try_from` exact value, indices checked before conversion, `len()` Table and slice typed in `u64`. | P · Synchronous conversions, fixed tables and async conversions within the perimeter of the integration cycle. |
| 07 · Compound assignments, N4–N5, AS8 | One evaluation of a computed index, bounds check before the RHS, reads and disjoint writes during the reservation, signed shifts, checked arithmetic, and resumption after `.await` even when the index changes. | Rust and Crust: 8 executions, 6 expected runtime traps under fatal UBSan, and 14 compile-time refusals on macOS ARM64. [Witnesses](../validation/check_compound_assignments.py) · [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#compound-assignments-in-both-compilers). |
| N2/N7, AS2/AS8, RT7 | Address and type kept through a transfer of `A<u64>`, mutations and re-use of slot. `f32` and `bool` on `yield`, `.await` And join. | P · Synchronous digital pools. Contracts and digital async allocation captures still need to be generalised. |

[Sources and executions](SAFETY.md#cycle-du-noyau-numérique)

<a id="déplacements-par-valeur-et-captures"></a>

## Movements by value and catches

| Rules | Invariant verified | Executions and limitations |
| --- | --- | --- |
| Brouillon 02, N2–N3, H1 | Link, argument, return and drop move access by keeping identity and a single clean. | Same address before and after call, re-used slot, old names refused both entries. |
| Brouillon 02, N4–N6, F3/F4 | The block captures at the entrance. A copied scalar remains independent. A loan or a too short pool prevents the movement. | Import named and capture lexical, masking range, visible receiver, branch and loop return, preparation of arguments from left to right. |
| AS2/AS8/AS11, RT5/RT7 | The transfer of a task and its result preserves the cleaning and waiting. | Owner capture and scalar copy through `yield`, spawn and join. General migration of other open catches. |

Status P. The [report](SAFETY.md#cycle-des-déplacements-par-valeur) distingue
successful passes and historical failures found.

<a id="noyau-mémoire-n1n8"></a>

## Memory core N1–N8

The markers refer to the [core grilt]](LANGUAGE_RULES.md#noyau-mémoire--grille-de-lecture).
The pass [test_core_memory](../tests/test_core_memory.py) couvre dix programmes
C-based and 19 invalid variants controlled by `verify_program`
and `compile_source` with their default settings. The details of the passes and
of their limits is contained in the [cycle report](SAFETY.md).

| Benchmark and related rules | Targeted Pass Case | Additional coverage |
| --- | --- | --- |
| N1 · V1–V5, ST1–ST5, H1 | Complete construction accepted. Missing field, bad type of field and confusion between local value and pool refused. | Embedded constructions, enums, signatures and storage requirements. |
| N2 · T1–T6, H1, L2/L6 | A return to duty keeps the address and only one destruction. The old name is refused. | State transfers, captures and cleaning of Select losers. |
| N3 · U1, T1, ST17–ST18 | Independent explicit copy. Implicit assignment and unused results refused. A hidden receiver in a block can be read after this block, if the path succeeds. | The methods and their own syntax remain followed by the ME1–ME4 entries. |
| N4 · D1–D4, A2/A3 | Return of a structure borrowing the accepted parent. Local target to the child and too short pool refused. | Storage requirements through multiple calls and catches. |
| N5 · B1–B5, ST6 | Disjunct fields and mutation after last use accepted. Same field, premature access and drop before last use refused. | Borrowers sent back by call, wait and join. |
| N6 · S4–S5, T9–T10, F3–F4 | Divergent branch and break/continue paths. The same case without early exit is refused. | Alternative sources and arguments evaluated in the presence of borrowings. Replacement of an external receiver also replayed in the historical profile. |
| N7 · L1–L7, A4 | New allocation built before drop of the old, then destruction at the end of the scope. Reuse of slot with case N2. Reset refused in the current profile. | C inspection and destruction traces. Storage and cleaning models within their respective perimeters. |
| N8 · B4–B5, ST8/ST12, AS11–AS15, MT3/MT5/MT6 | Relay of a transferable loan via two contracts. Access before its last use and return of a refused local target. | Contracts checked without rereading the bodies in the cases tested, including storage, captures and join results. |

Status P for the eight markers. Cases performed overlap with entries
The results under reset compatibility remain distinct.
After correcting the masking follow-up, the four final passes total
208 successful methods. Details of profiles and configurations are in the
[manifeste](../validation/core-memory-final.json)Asan remains inconclusive.

Synchronous extension validated in its perimeter: [online replacement contracts](cycles/INLINE_VECTOR_REPLACE_CONTRACTS_CYCLE.md).
Eight targeted methods O0/UBSan: 17 C executions and six invalid variants
Two entries. First passage O2/UBSan: 169 successful methods. After the supplement
Result<T,T> parameters, **171 methods pass in 160,035 s**, with the 46
The passage interrupted without balance sheet is not counted as
a success. Final log: validation/inline-vector-replace-contract-replay-regression.log.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, T6, ST17/ST18 | Local carrier separate from the box; fields separated by arm | Fresh/named returns, parameter input, relays and branches; C retained | P — synchronous exercises, async open |
| B1–B5, U1, L1/L6 | Borrowed/owners fields retained after transfer of Result | Result settings, vector drop, single clean, reused slots, rejected premature mutations | P — graphs used, no general evidence |
| H1, F2–F4 | Declared storage T/A<T> and explicitly respected arrows | Parameter/return signatures, bad storage and return without an arrow refused | P — Successful O2/UBSan regression in this area |

Checkpoint in progress: [replaces structures online](cycles/INLINE_VECTOR_REPLACE_CYCLE.md).
Seven targeted methods O0/UBSan: 13 C executions and eight invalid variants
The two entries. **142 methods, 111.163 s, code 0**,
43 unaltered prints. The synchronous complement is shown above; async remains open.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, H1, ST17/ST18 | Local repositioning makes the old T or repositioning it; A<T> remains separate | Success, invalid indices, annotations, Empty, C retained | P — local checkpoint; contract connected in the above supplement |
| B1–B5, T4/T5/T6 | Field graphs are transmitted to the result or to the box | Reading after vector drop, active borrowing refused, premature mutation refused | P — fields represented; unknown conservative positions |
| U1, L1/L6, VE2 | Unique cleaning of proprietary fields and reuse of slots | Two descendants, two branches, direct drop and consuming function | P — no general evidence; reset withdrawn |
| F2–F4 | Index order and then input and explicit transfer | Two functions with trace 1 then 2, old name/arrows refused | P — initial refusal of the corrected return in the above supplement |


Last batch completed in its perimeter: [pop of online structures](cycles/INLINE_VECTOR_POP_CYCLE.md).
20 targeted methods O0/UBSan: 27 C-executions and 16 invalid variants
First passage O2/UBSan: **361 methods, 349 successes, 12 failures**.
The two causes are corrected; re-set of the modules concerned, the target and the
Select : **173 methods, 155,584 s, code 0**. Marks unchanged during
No single passage of 361 green methods claimed.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, H1, ST17/ST18 | Pop d'une box locale makes Option<T>, distinct d'Option<A<T>> | Some/None, annotations, relays, T/A refusal<T>, loop and Empty | P — structures represented; other open operations |
| B1–B5, T4/T5/T6 | Borrowed/owner fields remain linked to their targets and sources | Reading after vector drop, premature mutation refused, mutable field, descend cleaned once | P — Conservative union after certain calls/branchs |
| AS2/AS8/AS11–AS13, F2–F4 | Contracts, catches, wrappers and public handles transmit the result graph | Direct and launched Await, join, Result relay, public borrowing, controls at both entrances | P — families exercised; sources of empty options distinguished by their type verified |
| U1, L1/L6 | A proprietary result is explicitly consumed and cleaned once | Drop direct, refus Some(_), use after drop refused, traces and re-use | P — UBSan O0/O2, no general evidence or alleged independent audit |

The local case replaced after this lot is connected in the checkpoint above.
The initial refusal of return by contract is corrected in the above supplement.

Previous lot completed within its perimeter: [owners' fields in Vector<T>](cycles/INLINE_VECTOR_OWNED_CYCLE.md).
19 targeted methods O0/UBSan: 16 C executions, 14 invalid variants
O2/UBSan regression: 236 methods, 232 success and four fixtures
Incorrect historical records, reproduced before this lot. Node/A signatures<Node>
The five replayed methods are corrected and passed.
**35 methods, 26.861 s, code 0**. No single green global passage claimed.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, H1, ST15/ST17 | The box has its fields A<T>; remove restores the cleaning, copy is refused | Unique destruction tracks, empty/non-empty vector, two pools, re-used slots | P — Push/remove and layouts represented; other open operations |
| T4/T5/T6, B1–B5 | Descendant pools and borrowed targets survive the recipient | Scope children, contracts, descendant borrowing, refusal transfer and pool too short | P — async default of the corrected contract, negative log retained |
| AS2/AS8/AS11–AS13, L1/L6 | The states/captures transmit fields without moving pointed objects | Yield, join, inactive capture, C inspected | P — targeted cases, conservative monitoring of sources after extraction |
| G1–G12, GR1/GR2 | The enriched descriptor keeps the storage functioning | 35 region methods and two sliders | P — UBSan executions, no general evidence |

The initial refusal of pop is kept in validation/inline-vector-pop-baseline.log;
the above pop cycle connects this case. Other operations remain open.


Previous batch completed: [nominal references in Vector<T>](cycles/INLINE_VECTOR_NOMINAL_CYCLE.md).
Targeted O0/UBSan: **11 methods, 11 C executions, 20 variants refused** to
Two entries. **121 methods, 79,234 s, code 0**,
No change in the rules.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, ST7/ST17/ST18 | The descriptors of the entire/inner targets are retained by copy/remove | Read after drop of porters/vector, nested fields, C kept | P — nominal references shown; not all recursions |
| B1–B5, ST11/ST12 | Exclusiveness and last use relate to target and capacity | Premature transfers/drops refused, mutable copy refused, separate field accepted | P — cases listed sync/async |
| T4/T5/T6, F2–F4, AS2/AS8/AS11–AS13 | Contracts and catches shall retain the life of the references | Injection insert, remote relays, copies via function, yield and join | P — too short targets refused, no generalisation to all graphs |

Previous batch completed: [fields borrowed in Vector<T>](cycles/INLINE_VECTOR_BORROWS_CYCLE.md).
19 targeted methods: 20 C executions and 32 variants refused to both entries.
Final Regressions O2/UBSan: **194 methods, 151,310 s**, then supplement
**85 methods, 95,054 s**, codes 0 and fingerprints unchanged.
The ratio retains intermediate defects and the pre-existing Select fixture corrected.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, H1, T1/T4/T5 | Inline storage keeps the loans, without holding the slot of the consumer | Push named/fresh, copy/remove, child scope, C preserved | P — Int/&Int/&mut Int-int-bridged; owners and nominal references open |
| B1–B5, ST17/ST18 | Shared copies and mutable extraction keep reserved targets | Drop/mutation refused before last use; separate release of two cells | P — Conservative union after calls and certain branches |
| F2–F4, T6 | Insertion/retirement contracts and return transmit fields | Relay, freshly injected construction, copies via function | P — signatures tested, no proof of completeness |
| AS2/AS8/AS11–AS13, L1/L6 | Capture, Join and Cleaning Keep Targets and Re-use | Sync/async, yield, vector drop before reading the result, pool reused | P — UBSan O0/O2; independent audit not assumed |


Previous batch completed within its perimeter: [transfers named to Vector<T>](cycles/INLINE_VECTOR_MOVES_CYCLE.md).
Seven targeted methods: 15 C executions, 19 invalids at both entrances.
Final regression O2/UBSan: **126 methods, 77,073 s, code 0** ;
44 prints unchanged. The report retains the first passage including a test
failed on diagnosis, despite the correct refusal of the program.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1/VE2, H1, T1 | Explicit transfer of a local value; T remains distinct from A<T> | Named Push, old name/refusal, direct and contract-based errors | P — Int, interlocked or empty leaf structures |
| B1–B5, T4/T5 | Last use of loans and passage of preserved telescopes | Borrowing before/after push, explicit child entry, relay with re-borrowing | P — fully reserved vector |
| AS2/AS8, F2–F4 | Capture and relay keep the required storage | Local requirements of contracts inspected, capture with yield, synchronous C bridge | P — signatures of the lot, without generalisation to the fields borrowed/owners |
| L1/L6, VE3 | Cleaning of the value consumed, independent extraction and reuse | Transfer loops between vectors, pool reused, C stored | P — unchanged runtime, UBSan O0/O2; no general evidence |

Previous batch finished in its perimeter: [match consuming join results](cycles/CONSUMING_JOIN_MATCH_CYCLE.md).
Seven new methods: 12 C executions, including three launch failures
Injected, seven invalids at both entrances. Targeted O0 final with an existing test:
8 successful methods. **216 successes before ENOSPC**, then
**7 methods successfully replayed** (11.103 s, code 0), i.e. the 223 methods
The 31 prints are unchanged; the report keeps the stop
initial code 120 and the resumption, without presenting them as a single green passage.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| F2, AS11, MT7 | The consuming match solves the real type of Result | Int and A Fixtures<Vector<Point>>, Public Handle and Relay, now executed | P — previous rating difference corrected in the tested forms |
| U1, H1, L6 | The former owner is invalidated and the proprietary motives cannot be ignored | Resumption/drop of Result refused, reasons `_`destruction and re-use of the slot | P — branches of success and failure, running unchanged |
| B1–B5, AS13/AS15 | The borrowed payload keeps its target reserved | Transfer/drop before last use refused; transfer then accepted | P — Int reference and existing regression graphs |
| T1/T6, ST18 | Local value extracted or constructed remains local | Back Alternate point in Err, successful/failed launch, A<Point> refused | P — investment of fresh manufacturers, not promotion of existing storage |
| VE3/VE4, F2 | Replace/try_push keep both sources and unit case | Synchronous/async contracts, mutable references, wildcards, existing regressions | P — selected families; does not close Vector<T>general |

Previous batch in its perimeter: [online structures in async vectors](cycles/ASYNC_INLINE_VECTORS_CYCLE.md).
Eight targeted methods O0/UBSan: 14 successful C executions, eight invalids in the
Two entries. **226 methods, 215,753 s, code 0** ;
31 compiler/test prints unchanged during execution.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, ST17/ST18, AS8/AS9 | Online Point Cases, independent copies/extractions despite yield | Local/injected pools, two fronts and region, copy/remove and then drop vector | P — Int and Empty leaf point; other open fields |
| AS2/AS10–AS15, B1–B5 | Capture protects the recipient until waiting; cleaning and re-use | Emprunt mutable, transfert, drop inactif, refus lecture/drop avant join | P — listed cases, without general evidence of order |
| T1/T6, H1–H3, AS11 | Local result and pool result keep their category and lifespan | Point returned by wait/join; A<Vector<Point>> by Handle public and relay Result | P — A<Point> signature and pool too short refused |
| B4a, AS4 | The recipient remains reserved during the suspensionable valuation of the index | remove(index().await), result read after yield | P — borrowing of the whole vector |
| F2 | Match that consumes explicit a Join Result | Two minimum fixtures and consuming-join-match-baseline.log | Historical deviation corrected in CONSUMING_JOIN_MATCH_CYCLE.md; this line retains the initial observation |

Previous lot in its perimeter: [removal of online structures](cycles/INLINE_VECTOR_REMOVE_CYCLE.md).
Eight successful O0/UBSan targeted methods: 15 C executions (13 successes, two stops
The following are the main reasons for this:
**185 methods, 116,345 s, code 0**, prints unchanged.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE4, ST17/ST18 | Independent T extraction, order and length preserved | Removal and copying of the rest, destruction of the vector, two fronts, empty structure | P — Int sheets, without borrowed fields/owners |
| T1/T6, F2–F4 | The extract result survives its producer scope and vector pool | Block, if true/false, break, function and relay | P — reservation in the recipient; no promotion to A<T> |
| B1–B5, ME1/ME2 | Receiver remains protected during arguments and active loans | Last use accepted, access during argument and after drop refused | P — whole vector borrowing |
| TF1–TF5 | Abstract method keeps the type Point extracted | Remove.remove product Point; signature Int refused | P — static resolution and synchronous contract |
| Inference | A source operation has a stable source between the passes | Relays that did not converge, corrected and executed | P — deterministic test, no general evidence of termination |
| Suite | Vector Generalization<T> | Limitations of the report | Open: other fields/operations and async integration |

Previous batch: [structures directly in vectors](cycles/INLINE_STRUCT_VECTORS_CYCLE.md).
Eight successful O0/UBSan targeted methods: 10 C natives (8 successes, 2 stops of
The number of invalids in both entries is 7 and the number of invalids is 373.
a pre-existing fixture error reproduced on the initial snapshot;
supplement after correction: **30 methods, 16.386 s, code 0**. No failure
unexplained in this selection; details and limitations in the report.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1/VE2, H1 | Point-type boxes containing its fields, distinct from A<Point> | Insertion of constructions/copies, layout C, rejection of A<Point> | P — Int, interlocked or empty leaf structures |
| ST17/ST18, T1/T6, F2–F4 | Independent explicit copy received in parent/appellant | Copy after drop, end of the child pool, return and relay | P — early storage of local result |
| B1–B5, D1–D3 | No mutation during loan still in use, no reading after drop | Seven invalids at both entries, last use accepted | P — borrowing of the whole vector; borrowing of the boxes to be connected |
| GR1/GR2, G9/G12 | Correct size/alignment on two fronts and in region | Growth of two vectors, re-use, empty structure | P — Targeted paths, without early optimisation of regions |
| VE4 | L-index is checked before reading | Two native stops for -1 and length | P — UBSan fatal ; aucun index invalide lu |
| Suite VE1–VE6 | Generalisation of elements and operations | Limitations in the report | Open: references, owners, named travels, extraction, slices, async |
| AS8–AS12, H1–H3, B1–B5 | Consumer async of Result and wearer elements &Point | Three front fixtures, vector-upplemental-native.log: three outputs 7 and single cleaning | P — three performances O0/UBSan, without generalisation to all graphs |

Previous batch: [Records and nested receivers of Vector Result](cycles/ASYNC_VECTOR_RESULT_CAPTURES_CYCLE.md).
Seven new targeted methods: 9 natives including an injected launch failure,
9 invalids at both entries. **296 methods, 244.806 s, code 0**.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| AS8–AS12, H1–H3, VE1–VE4 | Successive captures and unpackages retain the elements and their loans | Two levels of tasks, interlocked receptions, descending Inner | P — nine C-species targeted |
| F2–F4, T4 | Loop connections and outputs keep the result graph | Match, if and break; explicit downlink in blocks | P — Targeted paths, without general index/branch correlation |
| B1–B5/B4c, D1–D3 | Target protected after receipt and during inactive capture | Nine invalids, including concurrent mutable access and premature drop | P — two compiler entries |
| AS10, nettoyage | Unique destruction and re-use after inactive capture or rejected launch | Two item destructions with re-use, one over-failure, one successful Inner | P — fatal UBSan, no new change campaign |
| Regression / Models | Contracts, collections, structures, async and Select | 296 methods, existing models and unchanged prints | P — no general evidence |
| Suite VE1 (historique) | Direct storage of structured values in Vector<T> | open-inline-struct-vector.crust/.log : ancien refus « allocation Int » | First connection above; valid example corrected requires copy(v[0]) according to ST17 |

Previous batch: [Relay of Results containing an async vector](cycles/ASYNC_VECTOR_RESULT_RELAYS_CYCLE.md).
Five new targeted methods: 6 native C including an injected launch failure,
7 invalids at both entries. Fourteen previous replayed methods.
Regression O2/UBSan: **289 methods, 240,778 s, code 0**.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| F2–F4, H1–H3, VE1–VE4, AS12 | The Result envelope keeps the type, elements and their loans during relays | Direct and successive relay, mutable target and descendant owned | P — Six C-executions targeted |
| B1–B5/B4c, D1–D3 | Target still borrowed protected after transfer of Result | Premature drop, mutable reading/writing competing refused | P — seven invalids at both entries, of which missing arrow |
| AS10, nettoyage | The load is destroyed once in the launch failure | Injected Err, An Item Destruction; Empty Case; Successful Inner Destruction | P — targeted cases, without new mutation campaign |
| Regression / Models | Contracts, graphs, storage, async and Select retained | 289 methods, prints unchanged and existing replayed models | P — no general evidence or new model of the Result |
| Suite | Capture of Result in another task and then receive nested | open-async-vector-result-capture.crust/.log | Lost items at reception; correction to come |

Previous batch: [public contracts for vectors handle](cycles/ASYNC_VECTOR_PUBLIC_HANDLES_CYCLE.md).
Four new targeted methods O0 successful: 4 C natives, 6 invalids in both
input; ten replayed previous batch methods. O2/UBSan regression:
**284 methods, 277,479 s, code 0**.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| AS10–AS12, F2–F4, H1–H3 | A public contract retains the sources and loans of its result | Function Wait, handle relay, named reception and extraction | P — four targeted C executions |
| B1–B5/B4c, D1–D3 | The result keeps its targets reserved after waiting | Six invalids at both entrances; shared/mutable and descending loans Inner | P — no general evidence of composition |
| Auditor / C | Both paths retain metadata [] | Symbolic contracts and minimum programme generation | P — verified sources of elements, internal invariant maintained |
| Regression / Models | Collections, contracts, structures, async and Select | 284 methods, existing models replayed, compiler unchanged | P — no new independent model |
| Suite | Transfer of the already received Result to a relay function | open-async-vector-result-relay.crust/.log | Internal refusal reproduced in both entries; correction to come |

Previous batch: [back async vectors](cycles/ASYNC_VECTOR_PAYLOAD_RETURNS_CYCLE.md).
Ten targeted methods O0: 9 C executions and 9 invalids at both entries.
Regression O2/UBSan: **280 methods, 236,594 s, code 0**.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| AS8–AS12, H1–H3, VE1–VE4 | The returned vector retains its elements after cleaning the state | Await, join, manufacture, two async transfers, empty and A<Int> | P — nine C-species targeted |
| B1–B5/B4c, D1–D3 | Targets and pools survive the result; mutable exclusivity | Nine invalids, drop after join, concurrent reading/writing, pool short | P — Borrowing and descendants graphs Inner |
| F2–F4, graphes | Receipt and extraction restore storage and loans | Named result and graph embedded in stress analysis | P — conservative monitoring by road [] |
| Regression / Models | Collections, contracts, async, cleaning and Select suites | 280 methods; existing replayed models | P — no new model independent of the graph |
| Suite | Fonction recevant runtime::Handle<A<Vector<A<Item>>>> | open-async-vector-payload-handle-return.crust/.log | Reproduced deviation at both entries; correction to come |

Previous lot: [vector contracts since async](cycles/ASYNC_VECTOR_PAYLOAD_CONTRACTS_CYCLE.md).
Six successful O0 targeted methods: 8 C executions, 11 invalids at both entries.
Regression O2/UBSan: **270 methods, 269,141 s, code 0**.
Insertion and extraction by contract, owned descendants and symbolic C bridge.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| F2–F4, VE1–VE4, AS8–AS12 | The effects of insertion are published in the async state | Direct calls, relays and &mut extraction or transfer | P — Eight C-specifications targeted |
| B1–B5/B4c, D1–D3 | Targets and pools survive the load returned | Eleven invalids at both entrances, of which pool of the descendant too short | P — Int graphs and interlocking loads |
| H1–H3, nettoyage | The bridge keeps the graph symbol without reading an absent box | Empty Vector, Some/None, Descending Inner and Re-employment | P — no borrowing graph added to runtime |
| Regression / Models | Contracts, structures, collections, async and Select preserved | 270 methods, existing models replayed | P — no new model independent of graphs |
| Suite | Retour async d’un conteneur entier | open-async-vector-payload-return.crust/.log, refusal to both entries | Implementation gap remaining |

Previous batch: [graphs of async vectors](cycles/ASYNC_VECTOR_PAYLOAD_GRAPHS_CYCLE.md).
Twelve successful O0 targeted methods: 15 C executions, 18 invalids in both
O2 regression of 264 methods: two historical methods to be corrected,
then complement 14 successful methods on the compiler unchanged.
These executions are distinguished from a green monolithic pass.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| AS2/AS5/AS8/AS9, H1–H3 | Catches keep loans and pools of items | Direct, factory, inactive relay, parent async and descendant possessed | P — Int graphs and tested loads |
| B1–B5/B4c, D1–D3 | Targets survive capture and extraction | 18 invalids, mutable exclusivity and too short pool | P — Local roads attached in a conservative manner |
| VE1–VE4, AS10 | The results of the operations keep their loans until cleaning | Push/remove/pop/replace/try_push, re-use, None and empty vector | P — 15 targeted C executions |
| Regression | Captures, contracts, Select and previous models | 264 methods + supplement O2 of 14; initial failures documented | P — compiler unchanged during both passes |
| Next deviation | Synchronous call insertion effects from async | open-async-vector-payload-sync-call.crust/.log | Default reproduced: early drop accepted; correction required |

Previous batch: [complex vector returns](cycles/VECTOR_PAYLOAD_CONTAINERS_CYCLE.md).
Nine successful O0 targeted methods: 12 C executions, 18 invalids in both
enter; regression O2/UBSan: **168 methods, 164,706 s, code 0**. Fabriques, relais, branches, suppressions,
replacements of borrowing/owner elements and graphs.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1–H3, VE1–VE4, F2–F4 | Returns keep the active graphs of the elements | Manufactures, relays, branches, removal and replacement before return | P — 12 performances C, graphs attached by provenance |
| B1–B5/B4c, D1–D3 | Pools and targets survive; mutable loans remain exclusive | 18 invalids refused both entries | P — Int references and descendants exercised |
| Cleaning and storage | The extracted elements destroy once and the slots are reusable | Traces Item/Inner, capacity re-use 1 | P — Targeted configurations |
| Regression / Models | Previous contracts, options, exchanges, async and storage | 168 methods; existing life and storage models | P — no new independent model of containers |
| Suite | Capture async d’un vecteur empruntant | open-async-vector-payload-graph.crust/.log | Explicit difference remaining |

Previous batch: [vector exchanges graphs](cycles/VECTOR_PAYLOAD_EXCHANGES_CYCLE.md).
Seven targeted methods O0, 6.890 s, code 0: **14 C and 18 invalid executions
both entries**Regression O2/UBSan: **159 methods, 158,585 s, code 0**.
No normative change; metadata of variants and displaced capacities
connected to contracts and their controls.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1, VE3–VE4, B4c | Each variant retains its load and dependencies | Replace valid/invalid index, try_push available/full, returns and relays | P — Borrowed and descendants charges |
| B1–B5, D1–D3 | Residual targets and pools, exclusive and preserved | Premature drop, short pool, concurrent reading/writing and second mutable capture refused | P — identity of capacity retained during displacement |
| U1, F2–F4, L1/L6 | Explicit use and destruction according to actual variant | Drop direct, Ok()/Err(Item), tracks Item/Inner and re-use | P — 14 executions C ; no general evidence |
| Regression and models | Previous contracts, options, async results and storage retained | 159 methods; replayed life models and storage | P — no new independent model of trade |
| Suite | Returns of whole delivery systems containing borrowings | open-vector-payload-container-contract.crust/.log: explicit refusal of both entries | Implementation gap; general integration still open |

Previous batch: [options of borrowing elements](cycles/VECTOR_PAYLOAD_OPTIONS_CYCLE.md).
Seven targeted methods O0, 5.724 s, code 0: **13 C and 13 invalid executions
both entries**Regression O2/UBSan: **152 methods, 150,976 s, code 0**.
The incorrect refusals of the nested None case were corrected without any change in standards.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1–H3, VE3, B4c | The option keeps the dependencies of its load through a call | Some/None, return and relay, consumer with fallback | P — Int references and descendants tested |
| B1–B5, D1–D3 | Targets and pools survive transferred results | Premature drop, mutable capture and too short pool refused | P — 13 invalid programmes at both entrances |
| U1, F2–F4, L1/L6 | Explicit consumption and single cleaning according to variant | Arrow/Use/Dual Consumption, Item/Inner Traces; None in Match Instruction/Expression | P — no fictitious dependencies for None established |
| Regression and models | Simple options, contracts, async and storage preserved | 152 methods; existing models with eight and four combinations | P — no new independent model of options |
| Suite | Result of borrowing elements, whole vectors and async | open-vector-payload-exchange-contract.crust/.log: explicit refusal of both entries | Implementation deviations; overall objective active |

Previous batch: [contracts of vector elements](cycles/VECTOR_PAYLOAD_CONTRACTS_CYCLE.md).
Ten targeted methods: 15 C executions, 22 invalids at both entrances and two
Checks without duty, after correction of two refusals
incorrect variants: 19 methods O0, 19.768 s, code 0; final regression
O2/UBSan : **145 methods, 144,001 s, code 0**. Aucun changement normatif.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1–H3, VE1–VE4 | Sources and graphs of items retained in calls | Fresh/transferred insertion, extraction, relays, replacement | P — contrats synchrones directs |
| B1–B5, D1–D3 | The targets and pools of descendants survive the receiver | Shared/mutable borrowings, descendants, conditional insertions; 22 invalids | P — Conservative Road Unions [] |
| B4c, F2–F4 | Caller verified from contracts only | Isolated auditor without body or inference tables; admission and refusal | P — cases of insertion/extraction |
| L1/L6 | Single cleaning and re-use | Item/Inner tracks, capacity pools 1, C11/UBSan | P — scenarios implemented |
| Regression and models | Preserved previous contracts and variants | 145 methods; existing models with eight and four combinations | P — no new independent model of vectors |
| Suite | Options, Result, whole vectors and async with complex loads | open-vector-payload-option-contract.crust/.log | Implementation deviations, active overall objective |

Previous batch: [graphs of local vector elements](cycles/VECTOR_PAYLOAD_GRAPHS_CYCLE.md).
Final target O0/UBSan: eleven methods, 7.029 s, code 0; 20 performances C,
28 invalid programs at both entrances.
113,766 s, code 1, seven failed historical sub-cases, reproduced before the batch.
After correction of their T/A<T> annotations: 15 methods, 10.713 s,
Code 0 on the same compiler. Combined proof, not a green monolithic passage.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE4, H1 | Displaced elements retain their fields and responsibilities | Push/remove/pop, valid/invalid, try_push successful, box-borrow replacement | P — synchronous local vectors, loads |
| B1–B5, D1–D3 | A carrier keeps its targets and pools of its descendants | Shared/mutable references, two proprietary levels, too short transfers refused | P — 28 invalids at both entries; no general evidence |
| F2–F4, B4c | The joins and contracts do not lose the dependencies of the object extracted | If/loop, loop re-use, constructor and relay of an extract object | P — contracts for complex container still open |
| L1/L6, VE2–VE3 | Unique cleaning and re-use of slots | Item/Inner tracks and capacity pools 1 ; direct drop of extractions | P — C11/UBSan O0/O2, combined evidence of the report |
| Regression and models | Contract retention, proprietary graphs and storage | 135 methods then complement of fifteen; models with eight and four replayed combinations | P — seven historical annotations corrected, predictions of unchanged models |
| Suite | Vector parameters/results<A<Item>> with borrowed fields | open-vector-payload-contract.crust/.log: valid according to rules, explicit refusal current | Implementation gap; overall active objective |

Previous batch : [typed async exchanges](cycles/TYPED_ASYNC_EXCHANGES_CYCLE.md).
Targeted O0/UBSan: nine methods, 12,541 s, code 0. 26 performances C of which five
LaunchFailed injected; fifteen invalid programs at both entrances.
Final regression O2/UBSan: 135 methods, 183.427 s, code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1, VE1–VE4, AS8/AS12, MT6 | Type and origin of each load kept in envelopes | Valid/invalid index, two pools, depths 1/3, captures and relays sync/async/public | P — Tested point and increasing loads |
| B4c, AS12 | Storage and alternative contracts follow | Adjusted loss of charge and variants; internal contracts maintained | P — transitory dependencies still open |
| VE2–VE4, AS10/AS14, SL1–SL2 | Ok(()) does not destroy accepted item; Err cleans rejected item | Region 1 Full/Not Full, Inactive Drop, Loser Select, Five LaunchFailed | P — deterministic cases |
| U1, B1–B5, D1, AS13 | Transferts explicites, types exacts, sources survivantes | Fifteen invalids at both entrances; re-use of both pools after cleaning | P — not general evidence |
| Regression | Options, Int exchanges, envelopes, storage and previous handles | 135 O2/UBSan methods; replayed storage models and permissions | P — recorded selection, no general evidence |
| Suite | Vector elements with borrowed fields/owners | open-vector-handle-borrowed-fields.crust/.log: explicit refusal of both entries | Incomplet ; objectif global actif |



Previous batch: [allocation options typed in async](cycles/TYPED_ASYNC_OPTIONS_CYCLE.md).
Targeted O0/UBSan: eight methods, 11,610 s, code 0. 26 performances C of which eight
Injected launch failures; 17 invalids at both inputs.
119 methods, 163.268 s, code 0. No normative change.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1, VE1–VE3, AS8/AS12, MT6 | Type and provenance survive envelopes and expectations | Option<A<Point>>; depths 1/3; public handles and relays; String and digital vectors | P — Types and depths of use |
| B4c, AS10/AS12 | Contracts follow the sources of the result and possible variants | Int envelope defects and corrected variants; case and C before/after retained | P — charges without transitory dependencies |
| AS10/AS14, L1/L6 | Unique cleaning in Some/None, inactive drop and failed launch | Eight LaunchFailed injections; trace Point and re-use of capacity pools 1 | P — deterministic paths tested |
| U1, B1–B5, D1, AS13 | Explicit transfer, strict types and surviving pool | Bad guys even on None, double usage, too short source, prior access join and ignored result refused | P — 17 invalid programmes, two entries |
| Regression | Int envelopes, proprietary results and previous contracts remain applicable | 119 O2/UBSan methods, including the interlocked holding model (seven admitted, five refused) | P — recorded selection, not general evidence |
| Suite | Async signatures of trades replace/try_push typed | Former refusal in TYPED_ASYNC_EXCHANGES_CYCLE.md | Implemented within the perimeter of this lot; overall active objective |


Previous batch: [handle vectors typed in async states](cycles/TYPED_ASYNC_HANDLE_VECTORS_CYCLE.md).
Nine targeted methods: 16 native programs and 17 disabled people controlled
O0/UBSan: 7.286 s, code 0. Final regression O2/UBSan:
84 methods, 80.216 s, code 0. No normative change.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, H1, AS2/AS8 | The container retains the type of its cells and their pools during a suspension | Shared/mutable/transferred captures; push/remove, length, synchronous relays | P — Point, String and digital vectors |
| VE2, L1/L6, AS10/AS14 | Destroy vector destroys remaining elements once only | Failure to correct manufacturer; re-use of both pools; inactive task drop | P — charges without transitory dependencies |
| F2–F4, U1 | Option/Local Result retains its type and responsibility after yield | Some/None, annotations, replace valid/invalid; Vector's refusal<A<Point>> receiving A<Int> | P — Async signature of these results still open |
| B1–B5, D1 | Catches and sources remain protected until waiting | Premature and dual use re-use after transfer refused to both entries | P — cases executed |
| Limit of load | The fields borrowed/owners require additional metadata | Explicit refusal on async parameters and local pools | Incomplet ; aucune nouvelle restriction normative |
| Regressions | Int course and previous synchronous typed tracks retained | 84 methods, options and exchanges, relays, outputs and cleaning | P — documented selection |
| Suite | Return of Option<A<Point>> from a task, join and typed parameters | Former refusal in TYPED_ASYNC_OPS_CYCLE.md | Open; overall objective unchanged |

Previous batch: [nominal returns T/A<T>](cycles/STRICT_STRUCTURE_RETURNS_CYCLE.md).
Six new methods: nine native programs and fourteen disabled
Final target: 21 methods, 18.702 s, code 0 (O0/UBSan and four)
Foundation to their historical O2 configuration). Extended regression O2:
276 methods, 233.082 s, code 1; 270 succeed and six former snippets remain
The supplement re-executes both migrant suites:
14 methods, 11.973 s, code 0. All six failures are closed in this
The 276 distinct methods have proof of success on the code
final. These are combined results, not a green monolithic pass.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| V1, T6, H1, brouillon 05 | A nominal return T remains local; A<T> remains in his pool | Fabrics, relays, explicit/final return implicit; return load of place under Point refused both inputs | P — Nominal returns, not redefinition of historical primitives |
| B4c–B4e, F3 | Storage requirements transmitted by contract | Symbolic settings, copy helpers, uncalled functions, branches, async/join | P — scenarios implemented |
| B1–B5, D1, L1/L6 | Transfer respects latest uses and cleaning | Borrowing before transfer accepted, use after refusal; drop and reuse of slots | P — not general evidence |
| ST11–ST14, B4c | The masking of a name does not change the holder of a pre-existing loan | Default reproduced on initial snapshot; values 1/3 and drop of both targets checked after correction | P — updating of the local holder by identity |
| Restitution and secondment | The rules already extended must not remain refused by old tests | Three obsolete oracles migrated; identity, destruction and re-use executed; shared target still protected | P — only reset in the legacy profile of historical tests |
| Regressions | Returns, copies, typed vectors, tasks, Select, fields and envelopes | 276 distinct methods with combined proof of success; log and manifest in report | P — documented selection, not all the rest |
| Suite | Async-typed options/results and complex loads | open-typed-async-vector-option.crust/.log: signature async Option<A<Point>> refused both entries | Ouvert ; objectif global actif |

Previous batch: [Synchronous contracts Option<A<T>>](cycles/TYPED_VECTOR_OPTIONS_CYCLE.md).
Eight targeted methods, 21 native executions and 11 invalids at both entrances.
O0/UBSan: eight methods, 7,113 s, code 0. Regression O2/UBSan: 87 methods,
100,393 s, code 0 (three Foundation methods with their native configuration).

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| VE3, H1, types | Some and None retain the type T of Option<A<T>> | Annotations, arguments, relays; bad guy refused even on None | P — Point, String, digital vectors, synchronous |
| F3, U1 | Result received/transferred/ explicitly consumed | If, loop/break, parameters, drop direct and named; eleven invalids at both entries | P — cases executed |
| Life and cleaning | The option only has its load, without unnecessarily retaining the emptied vector | Vector survivor result; load pool too short refused; re-use after Some/None | P — charges without transitory dependencies |
| B1–B5 | Pop respects last use of box borrowings | Borrow used before pop allowed, use remaining after refused | P — literal box Point |
| Regressions | The absence of load remains respected in historical options and envelopes | 87 O2/UBSan methods, empty options, existing branches, loops and async states | P — new async envelopes not connected |
| Suite | T/A<T> returns, complex loads and async typed | Deviations listed in the global checklist and reports | Open; no global fence |

Previous batch: [typed results of replace/try_push](cycles/TYPED_VECTOR_EXCHANGES_CYCLE.md).
Nine targeted methods, 30 native executions and nine invalids at both entrances.
O0/UBSan: nine methods, 11.012 s, code 0. O2/UBSan regression: 78 methods,
86,134 s, code 0. A T/A<T> return typing gap remains explicitly open.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| VE3–VE4, H1 | The result is the handle and the source corresponding to its variant | replace success/indice invalid; try_push success/region of 1 Mio full | P — Point; Thong loads and digital vectors for replacement |
| F3–F4, contrats | Type of load and provenance of arms retained | Functions, relays, injected consumption, if and loop/break; long-lasting arm return | P — synchronous, nine targeted methods |
| U1, F2, L6 | Explicit transfer, use and destruction of the only content possessed | 30 native executions, traces and re-use; nine invalid programs at both entrances | P — not general evidence |
| V1/T6, H1 | Local T and A<T> are not interchangeable | Local annotation of the denied charge; return A<Point> explicitly verified | P — signature historique Point encore trop permissive, voir ligne suivante |
| Signature difference | The public type of return must retain the T/A distinction<T> | open-plain-structure-return-from-handle-result.crust/.log : A<Point> accepted under return Item | History: corrected in STRICT_STRUCTURE_RETURNS_CYCLE.md ; initial fixture and log retained |
| Regressions | Historical results and envelopes maintain their behaviour | 78 O2/UBSan methods, existing injected runtime errors | P — enveloppes async A<Int> seulement |
| Suite | Typed pop contract | open-typed-vector-option-contract.crust/.log: Option<A<Point>> refused both entries | History: Synchronous contract connected in TYPED_VECTOR_OPS_CYCLE.md |
| Dependencies/async suite | Complex loads and runtime envelopes | Not covered by this lot; newly typed async signatures explicitly refused | Ouvert |

Previous batch: [typed handle vectors](cycles/TYPED_HANDLE_VECTORS_CYCLE.md).
Seven targeted methods, nine native executions and nine invalids at both entrances.
O0/UBSan: seven methods, 3.782 s, code 0. Final state: regression of 59 methods,
45,216 s, code 0; O2/UBSan for harness async and five Foundation tests with
their native historical configuration.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1–H3, VE1–VE3 | Type of target and source retained in boxes and extractions | Point, Thong, Vector<Int/u8>, remove, pop local, cleaning and re-use | P — nine native programmes; not all T |
| VE2, F3, stockage | The pool of each target survives to the receivers | Two pools, producer block, parameters and explicit relays; local T refused for A<T> | P — synchronous operations tested |
| B1–B5, H2 | Typical case borrowing, exclusive replacement and single cleaning | Comparison, replacement via &mut A<Point>, extraction during loan refused | P — literal box, field structure Int |
| U1, F4 | Explicit transfers and single consumption | Nine invalid programs at both entrances | P — listed cases |
| Regressions | Retention of A<Int> behaviors and storage requirements | 59 methods, native outputs and existing models | P — no independent audit or general evidence |
| Suite VE3–VE4 | replace/try_push returns a handle of the type of the boxes | open-typed-vector-exchange.crust/.log: explicit refusal of both entries | History: connected in TYPED_VECTOR_EXCHANGES_CYCLE.md for synchronous cases tested |
| Dependencies Suite | Target fields carry their lifespans | Owned/borrowed targets explicitly not connected | Open; async and typed envelopes also remain to be integrated |

Previous batch: [owners results with varying depth](cycles/RECURSIVE_OWNED_JOIN_CYCLE.md).
Seven new methods: 19 native executions and eight invalids
An updated historical method adds eight native and
three refusals via verify_program. Targeted O0/UBSan: eight methods, 10,001 s,
Code 0. Regression O2/UBSan: 186 methods, 231,142 s, code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| RT6, H1–H2, AS10 | Each expectation adds an envelope; each extraction takes one | A<Int> at three/five levels, failure of each launch, single destruction and re-use | P — executable depths |
| Types and storage, AS12–AS13 | Type of load and distinction T/A<T> retained | Int, String, digital vectors, View local; too short storage and pool refused | P — tested types, not all possible loads |
| B1–B5, AS12 | The dependencies of the result survive expectations and extractions | View with &Int, premature drop of the rejected target; regressions of proprietary/borrowed graphs | P — cases executed |
| U1, F3–F4, RT7 | Consumption and explicit expectations | Helpers, public handle, factories, if/loop; eight new invalids and three historical ones | P — the three historical records are checked only by verify_program |
| AS8–AS14, SL1–SL2 | Captures and temporary suspensions remain cleanable | Active/Inactive and Losing Capturing Select, Single Destruction | P — Targeted scenarios |
| Expectation appointed | Type is determined before the instance is consumed | TypePreexisting Eror reproduced on backup, corrected and kept in regression | P — body appointed and manufactured |
| Regressions | Other envelopes and effects keep their behaviour tested | 186 methods, fatal UBSan, existing models Select/awaken | P — separate independent audit, no general evidence |
| Suite | VE1–VE3: homogeneous vector of other types of handles | open-vector-allocated-structure.crust/.log : Vector<A<Point>> refused both entries | History: manufacturer connected in TYPED_HANDLE_VECTORS_CYCLE.md, family still partial |

Previous batch: [interlocked Runtime envelopes of Option<A<Int>>](cycles/ASYNC_NESTED_OPTION_JOIN_CYCLE.md).
Seven targeted methods: 25 native executions and seven invalids at both entrances.
O0/UBSan: 9,689 s, code 0. Regression O2/UBSan: 142 methods in 135,869 s,
Code 0. No normative change; family-like recursive description
optional and replace/try_push results.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| RT6, VE3 | Each expectation adds a Result; Option remains a separate charge | Some/None with 2/3/5 envelopes, sync/async extraction, manufacture | P — Option<A<Int>>, executed depths |
| AS10/AS14, RT6 | Only Some is destroyed; LaunchFailed cleans her catch | Injection at each of the three levels, with/without element; traces and re-use | P — roads used |
| AS12–AS13, H1–H2 | The result keeps the pool of the element without holding the vector | Result outside the accepted vector block; local source too short refused | P — test scope boundary |
| U1, F3–F4, MT1 | Explicit transfers, single consumption and booking before waiting | Public handle helper, relay, if/loop; seven invalid programs | P — targeted cases |
| AS8–AS14, SL1–SL2 | Conditional cleaning of catches and suspended arguments | Active/Inactive Capture, Pre-prepared and Losing Select argument | P — Some/None executed |
| Common description and regressions | Shared register keeps behaviors of other sheets | 142 methods, including replace/try_push envelopes and Select/awakener models | P — fatal UBSan; no thorough audit or general evidence |
| Suite | Additional interlocking of simple allocation results | open-async-nested-owned-join.crust/.log: refusal of depth at both entrances | Open; overall objective not closed |

Previous lot: [envelopes runtime nested with replace/try_push](cycles/ASYNC_NESTED_EXCHANGE_JOIN_CYCLE.md).
Eight targeted methods: 21 native executions and six invalids at both entrances.
O0/UBSan: 8,848 s, code 0. Regression O2/UBSan: 135 methods in 121,391 s,
code 0. Recursive description; two, three and five envelopes executed.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| RT6, VE3–VE4 | Each expectation adds a separate Result; only the content present is possessed | Depths 2/3/5, success/refusal of replacement; try_push with available/full region | P — two sheets A<Int>, no evidence for any depth |
| RT6, AS10/AS14 | Failed launch cleans his catch and does not create a business result | Injection at each of the three levels, single destruction of the input | P — Injected paths |
| AS12–AS13, H1–H2 | Provenances per arm kept through the envelopes | Extraction after disappearance of the incoming pool; source of the old allowance too short refused | P — Separate pools, target addresses not displaced by representation |
| U1, F3–F4 | Explicit transfers and consumption in helpers and junctions | Public handle, relay, if/loop; use absent, dual consumption, ignorant motive and absent transfer refused | P — targeted cases |
| AS8–AS14, SL1–SL2 | Conditional cleaning after suspension or inactive destruction | Capture executed/inactive, argument prepared and losing Select; re-use | P — tested traces |
| Contracts and Issue C | The types registered after import are recognized at all stages | Fixed table failure corrected; successive depths in the same process | P — signatures and C of programmes implemented |
| Regressions | Existing behaviour after generalisation | 135 methods, Select and alarm models, fatal UBSan | P — separate detailed audit, no general evidence |
| Suite | Option envelopes<A<Int>> and other charges | open-async-nested-option-join.crust/.log: depth refusal reproduced at both entries | Open; this lot does not close the overall goal |

Previous batch: [replace/try_push results wrapped by spawn/join](cycles/ASYNC_EXCHANGE_JOIN_CYCLE.md).
Eleven targeted methods: 33 native executions and seven invalids at both entrances.
O0/UBSan: 15.461 s, code 0. Regression O2/UBSan: 127 methods in 127,747 s,
code 0. Intermediate errors and correction of targeting of an injection
The report shall be kept in the submission.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| RT6, VE3–VE4, U1 | Error launching separate from the result of the operation | Join and wait for handle; success, internal error and failed submission | P — enveloppes portant A<Int> |
| H1–H2, AS10–AS13 | The provenance accompanies each arm possessed | Public handle, helpers, capture, return async and manufacture; separate pools, short source refused | P — cases executed |
| F3, transferts | The junctions retain the result and its obligations | Block, if and loop; absent transfer, unused result, double consumption and reason ignoring a charge refused | P — lost to corrected if |
| AS14, SL1–SL2, F4 | Cleaning limited to the actual load | Drop, inactive task, argument prepared then await, losing Select; try_push full/not full | P — single destruction and re-use tested |
| Contracts and Bridge C | Incoming identities remain in the relay summary | Corrected provenance defect, functions performed via bridge | P — no change in normative invariants |
| Regressions | Previous modes remain | 127 methods, public contracts, Select and alarm models | P — separate detailed audit, no general evidence |
| Suite reproduite | Launching a task already returning this envelope adds a Result | open-async-nested-exchange-join.crust/.log, explicit refusal to both entries | Additional interlocks to be generalized |

Previous batch: [replace/try_push results async captures and returns](cycles/ASYNC_HANDLE_EXCHANGE_RESULTS_CYCLE.md).
Ten targeted methods: 28 native executions and seven invalids at both entrances.
O0/UBSan : 13.515 s, code 0. Regression O2/UBSan : 109 methods in 105,405 s,
Code 0. Double inactive capture cleaning was detected and corrected.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE3–VE4, U1, AS2–AS5 | Capture and Return move the envelope with the content owned by its variant | Success/error, catch, direct/named returns; arrow and double consumption verified | P — A<Int>, was an inactive instance |
| AS10–AS13, contrats | The sources of the result survive, regardless of the vector | Manufacture, async relay, synchronous helper, separate pools; short source refused | P — provenances by arm |
| AS14, RT6 | Cleaning an inactive or unlaunched state only destroys its own catches | Inactive destruction and failure of submission; reuse; UBSan detected double dry_push cleaning | P — corrected defect, retained reproduction |
| F4, AS8–AS10, SL1–SL2 | A prepared capture remains cleanable during the wait of the following argument | Continuity and loser Select; capacity available/reach; single destruction | P — Targeted paths |
| B1–B5 | The task keeps the reservation until it waits | Access to the front vector has been denied | P — cases executed |
| Regressions | Existing contracts, options, captures and cleaning preserved | 109 methods; existing Select pollution/cleaning model | P — no new model or in-depth audit |
| Suite reproduite | Spawn outer envelope/join of these results | open-async-handle-exchange-join.crust/.log explicitly refused both entries | Not connected; implementation restriction, not normative |

Previous Lot: [replace/try_push results in calls from async](cycles/ASYNC_HANDLE_EXCHANGE_CALLS_CYCLE.md).
Eight targeted methods: 19 native executions and 5 invalids in both
0/UBSan: 7.466 s, code 0. Regression: 131 methods in
87.844 s, code 0. Async and three Foundation tests in O2/UBSan; fixed tables
with their default settings, without explicit optimization/sanitizer.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE3–VE4, U1 | Transfer of the result retains the content owned by each variant | Success/error, return and relay; arrow, type, use and double consumption verified | P — helpers synchrones, A<Int> |
| F4, AS8–AS10 | The prepared argument remains alive during the evaluation of the next | Named, interlocked, direct, block and wait arguments; drop/consumer Void | P — cases executed |
| SL1–SL2 | The loser only destroys the content still at his expense | Select with reposition and try_push, available/achieved capacity; single destruction and reuse | P — roads used |
| AS12–AS13, contrats | The provenance remains distinct by arm | Former allowance retained after destruction of the incoming pool; short source refused | P — two pools, relays tested |
| Regressions | Common syntax, existing contracts and cleaning preserved in the cases covered | 131 methods; tables/select suites and existing models | P — separate independent audit, no general evidence |
| Suite reproduite | Return async from Result<A<Int>,A<Int>> via await | open-async-handle-exchange-result.crust/.log, refusal to both entries | Captures and returns of unconnected envelopes |

Previous batch : [inclusion of hands in async](cycles/ASYNC_HANDLE_VECTOR_TRY_PUSH_CYCLE.md).
Seven targeted methods: 14 native executions and 9 invalids
O0/UBSan: 6,981 s, code 0. Regression O2/UBSan: 72 methods in
75,217 s, code 0, including three historical synchronous methods.
region of 1 MiB is actually reached in cases of failure.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE4, U1 | Ok(()) has nothing; Err keeps the input | Success, limit reached, direct/named match and continuation; unused results refused | P — Vector<A<Int>>, local envelope at async |
| Transfers and cleaning | Only one destination cleans the allowance | Displacement, annotation, direct drop/named; single re-use and destruction | P — tested paths |
| B1–B5, AS8–AS12 | The recipient remains reserved; the source must survive insertion | Loan granted, active loan and short source refused; incoming via await | P — reservation of the entire vector |
| SL1–SL2 | The destruction of a loser respects the status of integration | Select suspended after try_push, empty or full vector | P — retained contents, cleaned rejection |
| Regressions | Local operations already connected remain | 72 methods and existing Select pollution/cleaning model | P — separate detailed audit, no general evidence |
| Suite reproduite | Switching the result of the replace by synchronous helper called from async | open-async-handle-exchange-call.crust/.log refused both entries | Signature not connected; try_push envelope also to be completed |

Previous batch: [vector handle replacement in async](cycles/ASYNC_HANDLE_VECTOR_REPLACE_CYCLE.md).
Seven targeted methods: 14 native executions and 7 invalids
entry. O0/UBSan: 5,466 seconds before adding direct drop. Final reduction O2/UBSan:
72 methods in 77,334 s, code 0, including both direct drop cases and three
historical synchronous methods. No normative changes.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE3, U1 | The result has the old or the inward refused | Invalid success/indice; result named, moved and destroyed directly; single destruction and re-use | P — Vector<A<Int>>, local result at async |
| B1–B5, order of assessment | The receiver is reserved during arguments | Last use before/after, shared receiver refused; index then input produced by await | P — targeted cases |
| AS8–AS12, provenance | Sources of each charge remain known | Former returned via task/manufacture after destruction of incoming vector and pool; too short pool refused | P — union conservative si position inconnue |
| SL1–SL2, nettoyage | The loser destroys the old, the vector preserves the new | Select suspended after replacement, single destruction and re-use | P — deterministic path |
| Related Regressions | Operations and contracts already connected remain in operation | 72 methods; existing Select pollution/cleaning model | P — no general evidence, detailed deferred audit |
| Suite reproduite | try_push from handle in async | open-async-handle-vector-try-push.crust/.log refused both entries | Unconnected, like async signatures of the repositioning envelope |

Previous lot: [Option owner in the envelope of a handle](cycles/ASYNC_OPTION_JOIN_CYCLE.md).
Seven targeted methods: 19 native executions and 5 invalids
O0/UBSan: 8,415 s, code 0. Regression O2/UBSan: 83 methods in
152,442 s, code 0, before moving definition C. Final validation:
11 targeted/runtime methods in 11.856 s, code 0. Intermediate failures
and the corrections to the test snippets are recorded in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE3, AS10–AS12, RT6 | The result distinguishes presence, absence and failure of launch | Some/None/Err via join and handlewright, single destruction and re-use | P — Option<A<Int>> |
| Contrats, transferts, U1 | The source and cleaning follow the envelope | Public handle, helpers, capture, block/if/break, missing uses refused | P — no additional envelope around this Result |
| Lifespan | The element pool survives the result; the vector can disappear | Accepted program with outdoor pool, refusal with indoor pool | P — targeted cases |
| AS8–AS10, SL1–SL2 | Prepared argument remains cleanable during suspension | Relay then await; losing branch of Select, single destruction | P — the way used |
| Runtime autonome | Generic runtime does not depend on a generated envelope type | Four alarm regressions/model after correction | P — existing replayed model, in-depth deferred audit |
| Suite reproduite | Replacement of a vector handle in async | open-async-handle-vector-replace.crust/.log, refusal to both entries | array_handle_exchange not connected |

Previous Lot: [captures and returns async of proprietary options](cycles/ASYNC_HANDLE_OPTION_RESULTS_CYCLE.md).
Eight targeted methods: thirteen native executions and seven invalid programmes
O0/UBSan: 4.734 s, code 0. O2/UBSan regression: 74 methods
in 113,097 s, code 0. Perimeter: Option<A<Int>> via await of an inactive instance
and explicit capture; the envelope of spawn/join remains open.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE3, U1, AS2–AS5 | The option transfers its possible content to the capture or receiver | Some/None, arrows, factories, relays and synchronous helper | P — Option<A<Int>>, usage explicite requis |
| B1–B5, AS12–AS13 | Loans end with waiting, sources of result remain | Reading the vector after await allowed, during the refused capture; pool short refused | P — Short catch is refused from the outside |
| AS8–AS10, AS14, SL1–SL2 | Unique destruction of unremitted content | Inactive, failed launch and child suspended from a select loser; re-use of pool | P — Targeted paths, no new adversary campaign |
| Related Regressions | Contracts, results of owners and cleaning retained | 74 methods; existing replayed pollution/cleaning model | P — no general evidence |
| Suite | Result<Option<A<Int>>,runtime::Error> after launch | Explicit diagnostic for join/wait de handle | Unconnected; corresponding public handles also open |

Previous batch: [owner options in synchronous calls from async](cycles/ASYNC_HANDLE_OPTION_CALLS_CYCLE.md).
Seven targeted methods: 15 native executions, 7 invalids in both
O2 regression: 61 methods in 99.319 seconds before final corrections.
Final O2 validation: seven targeted methods and four synchronous methods, eleven methods
in 10,245 s, code 0. Intermediate errors and their limits are recorded.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE3, U1 | The contract transports optional content and cleaning | Some/None, relay, Void, direct drop; no transfer or use refused | P — helpers synchrones, Option<A<Int>> |
| Order of Evaluation, AS8–AS12 | The prepared argument remains protected during the next wave | Four forms of argument, sequence 4/7/8 | P — targeted cases |
| SL1–SL2, destruction | Loser clears the argument prepared before the call | Select, helper uncalled, single destruction and reuse | P — the way used |
| Source, lifespans | The result depends on the pool of the element, not the vector | Return after destruction of vector; source too short refused | P — Union of possible sources |
| None and contracts | No allocation field read if content is missing | Pre-existing replicated plantation, minimum case retained, four successful synchronous tests after correction | P — no general evidence |
| Suite reproduite | Option returned by task and received via await | open-async-handle-option-result.crust/.log refused both entries | Unconnected async signature |

Previous batch: [handles pop in async states](cycles/ASYNC_HANDLE_VECTOR_POP_CYCLE.md).
Targeted O0/UBSan completed: eight methods in 7,658 s, seventeen executions
The first step is to make the transition to a new system of social security systems.
In 6,473 sec. Regression async O2/UBSan: 91 methods in 153,696 sec., code 0.
Existing replayed lists and pollution/cleaning templates; no general evidence.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE1–VE3 | The last handle is extracted without changing its target or pool | Some/None, two pools, single cleaning and reuse | P — A<Int> |
| U1, transferts | The option has its content and requires explicit consumption | Move, match, drop direct/named, annotation; use absent and second consumption refused | P — local options in the async states |
| B1–B5 | Pop waits for the end of the loan and demands a mutable receiver | Last use before/after and shared vector | P — entire reservation of the vector |
| AS8–AS12, blocs | The option survives to yield and transfers to a receiver | Block, if, break; return of the element via factory | P — option signatures not connected |
| SL1–SL2, nettoyage | A suspended loser destroys his Some once | Select after extraction, zero length and reuse of pool | P — deterministic path |
| Suite reproduite | Synchronous Helper Returning Option to Task | open-async-handle-option-call.crust/.log refused both entries | Signature not supported |

Previous batch: [extraction of vector handles in async](cycles/ASYNC_HANDLE_VECTOR_REMOVE_CYCLE.md).
Eight methods: thirteen native executions (a controlled stop off-limits),
7 invalids at both entrances. Targeted O0/UBSan: 5.864 s; regression
O2/UBSan: 77 methods in 60.691 s; five synchronous methods in 6.278 s,
all completed with code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE3, U1 | Explicit extraction, pool and cleaning responsibility retained | Link, direct return, helper, direct drop; no arrow refused | P — A<Int> |
| VE1–VE3, nettoyage | Order of the remaining cells and single destruction | Extraction of the medium, two pools, vector cleaning and re-use | P — cas finis |
| B1–B5, evaluation | Extraction protected until last use of loans | Loan granted; extraction/replacement during loan refused; index suspended and terminals | P — entire reservation of the vector |
| AS8–AS12, contrats | Independent result of the wearer, durable in his pool | Join, factory, relays await ; exit of the pool of the accepted vector, short target pool refused | P — conservative pool union |
| Regressions | Retention of previous cases | 77 async/contract/result methods; five synchronous methods; existing Int/u8 replayed | P — no general evidence, detailed deferred audit |
| Stay | Other vector-owner operations in async | Pop, replace, try_push, local constructions and vector returns | Not fenced by this lot |

Previous batch: [inserting handles in a vector from async](cycles/ASYNC_HANDLE_VECTOR_PUSH_CYCLE.md).
Nine methods: thirteen native executions, twelve invalids at both entrances.
O0/UBSan : 4.878 s; regression O2/UBSan : 68 methods in 55,594 s and
five synchronous methods in 5.353 s, codes 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE1–VE2 | Box explicitly receives handle and clean it | New variables and allowances, two pools, vector owned; refusal of incompatible types and modes | P — push of A<Int> |
| B1–B5 | The loan protects the transfer and the receiver until last use | Borrowing before transfer, use after transfer and loan beyond the rejected push | P — Targeted scenarios |
| AS8–AS12, contrats | New sources remain known after waiting | Manufacture, relay and synchronous helper; pool short refused; re-use after join | P — union of possible sources, precision of limited positions |
| SL1–SL2, provenance | The insertions before suspension of a loser remain observable | Select direct and via factory; defect of aliases reproduced and corrected | P — two executions and two refusals, not general proof |
| Nettoyage, RT6 | One destruction, no insertion if the body does not start | Inactive, EAGAIN and termination; capacity pools one re-employed | P — Thirteen executions |
| Next deviation | Explicitly extract a handle from async | open-async-handle-vector-remove.crust/.log, refusal to both entries | Not implemented in this case |

Previous batch: [async returns of vector target borrowings](cycles/ASYNC_HANDLE_VECTOR_BORROW_RETURNS_CYCLE.md).
Six methods: seven native executions (one controlled termination), ten invalids
O0/UBSan: 3,248 s; regression O2/UBSan: 49 methods,
41,046 s, codes 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS11–AS12, H2 | The result borrowed retains a durable external carrier | Returns ref/mut, relay expected, refusal from vector owned by the task | P — Vector<A<Int>>, full reservation |
| B1–B5, last use | The holder becomes accessible after the last use | Changes after use allowed; premature access, drop and replacement refused | P — targeted cases after join and wait |
| VE4, order of effects | Sync Writing of Content: Target before RHS, without invalidation during RHS | RHS shared admitted, MRT refused, out of bounds before effect | P — no replacement of handle |
| Cleaning and re-use | Unique destruction of targets, reusable slots | Results 7/11/13/14 according to scenario and re-use with 8; 49 regression methods | P — not general evidence |
| Next deviation | Insert a handle into a vector from async | open-async-handle-vector-push.crust/.log refused both entries | Not implemented in this case |

Previous batch: [borrows named vector targets in async](cycles/ASYNC_HANDLE_VECTOR_BORROWS_CYCLE.md).
Five methods: six native executions (one controlled termination), seven invalids
O0/UBSan: 2.726 s; regression O2/UBSan: 41 methods,
35,948 s, codes 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H2, VE1/VE4, AS9 | Reference to stable content, checked before use | Reading/mutation after yield, suspended index and off-bound | P — cibles Int |
| B1–B5, last use | Parent reserved during loan and his descendants | Mutation after last use allowed; premature access denied; child expected | P — reservation of the entire vector |
| Nettoyage, transfert | The loan does not survive the destruction of its owner bearer | Drop after use, refusal before use, single destruction and reuse | P — Six native executions |
| Next deviation | Return the loan to the async result | open-async-handle-vector-borrow-return.crust/.log, refusal to both entries | Not implemented in this case |

Previous batch: [access to the contents of the handles from async](cycles/ASYNC_HANDLE_VECTOR_ACCESS_CYCLE.md).
Four methods: four native executions, including a controlled termination,
Three invalids at both entries. O0/UBSan: 1,708 s, code 0.
O2/UBSan: 50 methods in 48,365 s; three methods Foundation O2/UBSan
in 2,469 s, codes 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| H1/VE1, B1–B5 | Lire/modifier *v[i] acts on the Int without copying or replacing A<Int> | Reading after yield, writing then reading after join; shared capture and concurrent access denied | P — Int content, not ready for items |
| VE4, order of effects | Check the index before assessing the inward value | Expected index/RHS; out of bounds without RHS marker impression | P — four targeted executions |
| Capture and cleaning | Reuse after termination and single destruction | Regression of 50 methods and three synchronous cases | P — not general evidence |
| Next difference | Conserver &*values[0] during suspension | open-async-owned-vector-borrow.crust/.log refused both entries | Not implemented; next feature |

Previous batch : [Async captures of handlender vectors](cycles/ASYNC_HANDLE_VECTOR_CAPTURES_CYCLE.md).
Five methods: five native executions and six invalids at both entrances.
O0/UBSan: 1.787 s, code 0. Regression O2/UBSan: 57 methods, 73.554 s, code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE2/H1, AS2/AS8–AS12 | A captured Vector<A<Int>> retains its elements and its pools | Ref, mut, owned, child expected, yield, length reading | P — capture/length; API of unconnected elements |
| B1–B5, typage | No incompatible access or confusion Vector<Int>/Vector<A<Int>> | Six invalid programs at both entries | P — targeted cases |
| Nettoyage, pools, RT6 | Transfer of the cleaned vector once on each exit | Finish, inactive task, EAGAIN; capacity pool one re-used | P — five executions and 57 regression methods |
| Next difference | Reading a proprietary element in the state | open-async-owned-vector-read.crust/.log refused both entries | Not implemented; no new normative restrictions |

Previous batch: [new recursive graphs in factories](cycles/FRESH_RECURSIVE_FACTORIES_CYCLE.md).
Three methods: five native programs and seven invalids at both entries.
O0/UBSan : 2,554 s, code 0. Final regression O2/UBSan : 83 methods,
119,547 s, code 0 (first pass before final junction: 82 successful methods).

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS8–AS12, contrats, T1/T6 | New construction keeps all its pools and deep fields through the factory | Two links A<Node>, separate terminal source, direct/relayed and from async | P — concrete paths, metadata of published variants |
| B1–B5, ST13 | The graph references remain protected after waiting | Premature target mutation refused; read after yield and clean then write allowed | P — fields tested; not general proof |
| Contracts by road | An absent branch is distinct from an unknown variant | End direct or two Link, two executions and refusal; union of forms by way | P — jonctions opaques potentiellement conservatrices |
| Pools, nettoyage | Sources last and slots returned | Drop of pool before waiting refused; single destruction and reuse; 83 methods pass | P — independent audit carried over |
| AS2/VE1–VE2, next deviation | A task should be able to borrow a Vector<A<Int>> | open-async-owned-vector-capture.crust/.log: refusal to both entries, length reading only | Not implemented on this case; next feature |

Previous Lot: [full recursive link replacement](cycles/RECURSIVE_cycles/SYNC_DEFAULT_MUTEX_CYCLE.md_REPLACEMENT_CYCLE.md).
Two methods: two native programs and four invalids at both entries.
0/UBSan: 0.916 s, code 0. Regression: 49 methods, 30.432 s, code 0,
fatal UBSan (O2 on the async harnesses, without O2 explicit on the former sync harnesses).

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| A<T>, remplacement, nettoyage | The old subtree is destroyed once; new pool durable | Field A<Node> replaced by helper sync and since suspended; child pool refused | P — graphe fini alternant struct/enum |
| B1/B2, match | Field projection remains typed and controlled | Lecture &*link.node after replacement; mutation via shared carrier and absent field refused | P — corrected filter, general check retained |
| Pools, AS8–AS12 | Old and new slots remain reusable | Re-use before and after root cleaning; 49 methods pass | P — New graphs in the factories still to be checked |

Previous Targeted Check: [Deep Owner Replacement](cycles/RECURSIVE_OWNED_REPLACEMENT_CYCLE.md).
One method: two native programs and two invalids at both entries,
successful at O0 and O2 with fatal UBSan. The compiler was already taking care of this case;
only tests and documentation are added.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| Replacement, T1/T6, lifespan of pools | The new source survives on the bearer; old allowance destroyed once | A<Int> behind two links A<Node>, helper sync, async state suspended, child pool refused | P — terminal field; no replacement of full A<Node> link |
| Cleaning, re-use | Old and new slots are returned to their pools | Pools of capacity one, values 9/11/12, single destruction | P — two programmes at O0/O2; no change in compiler |

Previous batch: [recursive mutable returns](cycles/RECURSIVE_MUTABLE_RESULTS_CYCLE.md).
Two methods: three native executions and seven invalids at both entrances.
O0/UBSan : 1,206 s, code 0. Regression : 97 methods in 42,486 s, code 0,
fatal UBSan (O2 on the async harnesses, without O2 explicit on the former sync harnesses).

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST11–ST12, B1–B5 | The mutable return retains the target and the capabilities of its carriers | Two links A<Node>, return &mut Int, carrier drop/target and direct write refused before use | P — trois programmes valides, sept invalides |
| Contrats, AS8–AS12 | The path remains valid after relay and suspension | Renumbered relay parameter, yield after helper call, write and clean | P — Targeted graphs, replacement of still open links |
| Shared and mutable returns | The ST13/exclusive capacity distinction remains | 97 regression methods pass | P — no overall evidence or new independent audit |

Previous batch: [recursive shared returns](cycles/RECURSIVE_BORROW_RESULTS_CYCLE.md).
Two targeted methods: two native executions and four invalids in both
0/UBSan: 1,077 s, code 0. Regression: 81 methods, 48,141 s,
code 0; async harness O2/UBSan, historical synchronous harness C without sanitizer.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST13, B1/B5 | Shared return keeps the external target without artificially reserving the carrier | Return after two links A<Node>, drop the holder then read; mutation and drop of the target early refused | P — &Int shared, two paths of call |
| AS8–AS12, contrats | The helper loan survives in yield | Read after suspension, access to the target allowed after last use | P — Synchronous return called from a task; not all async returns |
| Match and contracts | The proprietary projections and the results of nested matches keep their way | 81 methods pass; mutable returns exist in regression | P — deep mutable returns and replacement of still open links |

Previous batch: [projections borrowed recursive](cycles/RECURSIVE_BORROW_PROJECTIONS_CYCLE.md).
Four targeted methods: six native executions and six invalid programmes
O0: 4,615 s, code 0. Regression O2/UBSan: 86 methods in
70,513 s, code 0; five synchronous O2/UBSan cases pass in 3,417 s.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST7–ST14, emprunts | The fields borrowed remain accessible behind recursive links | &Int and Writing via &mut Int, sync helpers and async states | P — symbolic projection; full undeclared deep loan returns |
| AS8–AS12, T1/T6 | Moving a descendant keeps all its concrete references | Premature drop now refused without further parasitic use; fixed retained | P — loss of loans corrected, six programmes invalid at both entries |
| Nominal references | An inner target keeps its descriptor and offset | Field before target 99, read expected 7, mutation blocked and then allowed | P — six targeted executions, not all forms |
| Contracts and cleaning | No regression on existing graphs and references | 86 async/contract methods and five synchronous cases pass | P — no general evidence; replacement of recursive links still open |

Previous batch: [waiting helpers on recursive handles](cycles/RECURSIVE_JOIN_HELPERS_CYCLE.md).
Four targeted methods: five native executions and three invalids
O0: 2.230 s, code 0. Regression O2/UBSan: 112 methods in 120,958 s,
code 0; three additional O2/UBSan synchronous cases pass in 2,209 seconds.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS10–AS12, contrats publics | Delegated expectation returns the finished graph and its variants | Handle<A<Node>>, Result returned, two helpers, terminal variant | P — previously refused corrected, other projections opened |
| B1–B5, AS12 | The descendant retains his reference after the helper returns | Premature mutation refused; target released after cleaning | P — Targeted shared reference, not all recursive forms |
| Nettoyage, RT5–RT6 | Unique destruction of descendants, including LaunchFailed | Traces and re-use in successful/injected failure | P — Five targeted native executions |
| Brouillon 04, attente non bloquante | Helper doesn't allow you to hide a join in the async | Refusal to both entries | Executed on case; no normative change |
| Model contract | Symbolic recursive continuations are not concrete leaves | 112 methods and three synchronous cases pass | P — finite representation, not proof of all operations |

Previous batch: [recursive task builders](cycles/RECURSIVE_TASK_FACTORIES_CYCLE.md).
Three targeted methods: five native executions and five invalid programmes
O0: 2.282 s, code 0. The regression O2/UBSan ends
99 methods in 77,697 s, code 0. A join helper on Handle<A<Node>> remains
The report does not contain any information on the programme and its minimum programme.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS8–AS12, contrats | Concrete graphs and variants cross factories and relays | Two successive calls, restoration after join, single destruction and re-use | P — paths inherited from parameters; recursive result nine opaque uncovered |
| B1–B5, AS12 | The descendants references remain reserved after waiting | Change refused after join, direct creation and manufacture before relay | P — conservation parfois conservatrice |
| Storage sources, cleaning | Each pool captured survives even without a proprietary result | Consumer Int, protected terminal pool, slot re-used after waiting | P — five targeted executions, 99 regression methods |
| Contrat d’attente public | A helper should be able to wait for a recursive handle | open-recursive-join-helper.crust, trace of the type | Not implemented on this case; next correction |

Previous batch: [property async recursive graphs](cycles/ASYNC_RECURSIVE_OWNED_CYCLE.md).
Five targeted methods, seven native executions and four invalids in both
O0 passes. O2/UBSan regression: 120 methods, 98,500 s, code 0.
A historical error of extraction A<T> is reproduced on the snapshot and then
corrected: 22 methods pass in 13,706 s; the storage module completed
Then 11 methods are passed in 7,354 s. Selections are repeated.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS8–AS12, champs A<T> | Finished recursive-type graphs without infinite unfolding; variants and sources per path | Capture, join, helper sync, inactive/failure cleaning, re-use | P — concrete graphs listed, opaque non-generalised factories |
| Emprunts, contrats publics | The living result keeps the references of its descendants | Premature mutation refused after join, inferred and annotated handle | P — corrected lack of dependency loss; potentially conservative legacy |
| Stockage T / A<T> | The field possessed has its pool independently of the carrier | Extraction from local/pool enum; local incompatible annotation refused | P — corrected historical error, targeted follow-up completed |
| Cleaning and source contract | Descendants avant porteurs, destruction unique | Traces leaf/middle/root and re-use, regression of 120 methods | P — no general evidence, independent audit deferred |

Previous batch: [local public handles](cycles/PUBLIC_LOCAL_ENUMS_CYCLE.md).
Five targeted methods go to O0: seven native executions and five programmes
The related regression passes 67 methods in
40,076 s, code 0; target cases and async modules at O2/UBSan, two historical modules
with their harness without explicit optimization or sanitizer.
The synchronous conditional test of the previous batch now uses `bool` ;
Boolean calls were already implemented, no new type or alias added.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS10–AS12, Handle API | The public contract retains local T and its variant | Manufacture, two distinct routines, join, wait, failure of submission | P — Handle<A<T>> not accepted, targeted cases |
| Borrowing and sources | The result captures its targets and pools of its descendants | Shared, mutable, and A<Int> fields, single destruction, re-use; premature drop refused | P — seven executions, five invalids at both entries |
| F2, play in match | print(*reference) follows regular checks | Fixed syntax filter, split and mutable match regressions | P — 67 methods, no general evidence |

Previous batch: [enums on data stack implicit](cycles/LOCAL_ENUMS_CYCLE.md).
Eight targeted methods: 10 admitted programmes implemented and 3 disabled people refused
O0 is changed to 4.281 s. After correction of a regression of
symbol range C, 124 methods move to O2/UBSan in 103.565 s; 23 tests
historical pool enums also pass with their harness without optimization
All final processes are completed with code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| Data stack implicite, transferts enfant → parent | The storage source is separate from the layout and active arm | Literal sync/async, if, block, break, conditional returns | P — layouts represented; synchronous reservation at the maximum of the arms |
| AS8–AS12, local results | Durable metadata, result placed in recipient before release of state | Synchronous, wait, join and transfer helpers to a child | P — 10 targeted programmes, not all compositions |
| Nettoyage, champs A<T>, emprunts | Unique destruction of the descendant; no target promotion borrowed | Match consuming, re-use of slot, too short target and premature drop refused | P — three invalids at both entries |
| Pools d'enums and existing placement | Pool arms and local structures keep their behavior | 124 O2/UBSan and 23 historical methods; corrected regression C | P — no general evidence or independent audit |

Previous batch: [replacements of descendants with nominal references](cycles/ASYNC_OWNED_NOMINAL_WRITES_CYCLE.md).
Six targeted methods: nine native executions (including a failure to submit
Injected), 12 invalid programs refused both entries.
4,079 s; the O2/UBSan regression passes 101 methods in 82,937 s, code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| Remplacement, AS12/AS16 | New target remains linked to descendant after await/join | Direct and auxiliary writing, internal target, failed launch | P — graphs represented, no new reference cycles |
| SL1, contracts per path | Old and new possible targets remain | Select suspended and two conditional branches; conflicts refused | P — nine targeted executions, not all interlacing |
| Life, exclusivity | L-borrowing does not survive a local target and blocks its mutations | Scope too short child and premature writing refused | P — 12 invalids at both entries, independent audit deferred |
| Contracts and cleaning | Compatibility of existing possessed graphs | 101 methods: descendants, views, enums, synchronous calls, public handles | P — no general evidence |

Previous batch: [nominal references of d-enums async arms](cycles/ASYNC_ENUM_NOMINAL_CYCLE.md).
Five targeted methods cover six admitted programmes and six rejected invalids
The target O0 passage is 2.695 s; the O2/UBSan regression
passes 104 methods in 91,860 s, code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS8–AS12, ST13–ST14 | Projections keep the inner target after suspension and destruction of the carrier | Two variants, shared return, consuming, reusing slot | P — descriptors of structures represented, recursive graphs open |
| ST10–ST12, dernier usage | The Mutilable Reborrowing Target Reserve and Capacity | Synchronous helper, conflict between reborrowing and calling access denied | P — Targeted cases, no new adversarial audit |
| Construction, transfert, nettoyage | Pools remain valid and each wearer is destroyed once | Async construction, expected child, destruction count and re-use | P — 104 regression methods, no general evidence |

Previous batch: [direct async returns of nominal references](cycles/ASYNC_NOMINAL_RESULTS_CYCLE.md).
Eleven targeted methods cover 12 admitted programmes and eight disabled people refused
The first ten methods go to O0, the regression passes
116 methods at O2/UBSan, then the eleven methods and public handles pass
42 methods after last connection: codes 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS8–AS12, ST7–ST14 | The result borrowed retains its target after release from the state | Await, join, substructure, stored reference, relays, two branches and Select | P — 12 targeted programmes, recursive graphs not covered |
| Exclusive, lifetime | The reservation follows the result until the last use | Transfer conflicts and local returns refused to both entrances | P — listed cases; no new adversarial campaign |
| Contrats publics, ABI | The handle retains the nominal type and its mutability | Handle parameter, notation not compatible refused, 42 regression methods | P — public interface of the ever-open scheduler |
| Cleaning and slots | Restitution before release of state, reusable slots | Regression of 116 methods including five autonomous runtime tests | P — UBSan executions, no general evidence |

Previous batch: [typed references stored in async](cycles/ASYNC_STORED_VIEWS_CYCLE.md).
Eight new methods cover nine admitted programs and nine disabled
The targeted and historical passage passes 17 methods
at O0; the final regression passes 118 methods to O2/UBSan: codes 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS2–AS4, ST7–ST12 | Internal descriptor and capacity stored in stored references | Shared/mutable capture, yield, child task, chain and synchronous helpers | P — closure of the layouts represented, no cycles of general type |
| AS12, ST10–ST14 | A replacement retains each possible target, including if the launch fails | Direct/contract replacement; old and new protected reference after join | P — route and refusal |
| AS11–AS12, ST13–ST18 | Returning homeowner does not release the borrowing of his inner target | Capture/transfer/return View, carrier drop, target transfer refused; local copying and construction | P — canonical reservation corrected; direct async returns of nominal &T still open |
| Nettoyage, ABI, contrats | Regressions of sync/async retained | 118 methods, including replacements, Int references, mixed structures and copies | P — no general proof or new adversarial campaign |

Previous batch: [Async substructure captures](cycles/ASYNC_INLINE_VIEWS_CYCLE.md).
Nine targeted methods: nine admitted programs and eight disabled people refused both
Intakes. Seven and then eight methods go to O0. The general regression passes
127 methods to O2; after connection of copying requirements, 58 methods
pass, then 32 after the final correction of the factories: codes 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS2–AS4, ST7–ST12 | Capture keeps the inner address, root and exclusivity | Yield, worker, child task, synchronous helper, competitor access denied, inactive destruction | P — Int fields, Int references and descendants represented owners |
| AS11–AS12, ST13–ST14 | A returned borrowed field remains linked to the root after join | &mut Int return and premature drop of the rejected root | P — results of async nominal references still partial |
| ST17–ST18, P8 | Copying a view does not use a pool of another type | Local copy, explicit destination, Pool refusal<Pair> for Point, relay and factory | P — inferred requirements; nominal references stored still refused in async |
| Replacement contracts and ABI | Bridges keep proprietary fields, variants and provenances | Regressions on replacements async, Select, copies and methods | P — 127 and 58 and 32 methods, no general evidence |

Previous batch: [results combining whole and inner references](cycles/MIXED_INLINE_RESULTS_CYCLE.md).
Seven targeted methods go to O0: 12 admitted programmes and 11 programmes
The O2 regression passes 98 methods, then
the final pass after simplified returns passes 13 methods: codes 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST7–ST14, contracts by branch | Same type/mode, all possible targets remain protected | Conditional returns, relay, if, match, break, local branch too short refused | P — synchronous routes tested |
| Adresses stables, ST17–ST18 | Common descriptor does not move target | Comparative addresses in both branches, copying and storing the result | P — 12 targeted executions |
| Last use, exclusive | The mutable result remains derived from its targets and capabilities | Storage in Writer, Reborrow and Call, Concurrent Destruction/Writing Refusals | P — async views still open |

Previous batch: [stored internal references](cycles/STORED_INLINE_VIEWS_CYCLE.md).
Nine targeted methods go to O0: eight admitted programs, five rejected invalids
both inputs plus an explicit refusal to capture async still unconnected.
The O2 regression passes 90 methods and then 12 historical; after normalization
Final cycle, 33 related methods go to O2: codes 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST7, ST13–ST14 | Stored descriptor keeps the inside address and root | Construction, local copy/pool, returns, re-use of porter slot, root drop refused | P — synchronous routes tested |
| ST10–ST12 | Derivative Mutilable Reborrowing and Replacement Released the Old Target | Transferable return, transfer, access refused competitors, full reference | P — mixed results and async still open |
| Cycles, nettoyage, ST17 | No destruction of the target by the carrier, no self-reference to the root | Match borrowed/consumer, copy, cycle via substructure refused | P — Extended nominal BIT, no general evidence |

Previous lot: [owners' fields in the views](cycles/INLINE_OWNED_VIEWS_CYCLE.md).
Seven targeted methods are moved to O0/UBSan: eight admitted programmes are implemented and
seven invalid programs refused both entries.
84 methods at O2, plus six historical replacement methods: codes 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST7–ST8, ST15 | The view borrows its handles, the root keeps their cleaning | Reading, mutation, borrowing return, single destruction and re-use of slots | P — Synchronous paths tested |
| Remplacement, pools, contrats | Effect on the real field; former slot released, new pool fairly durable | Direct replacement, relay, back view, inside argument and short pool refused | P — A<Int> and descendant A<Leaf> exercised |
| ST13, ST17 | Shared target retained after destruction of porters; no copy of handles | &Int extract, target destroyed too early and copy of the rejected view | P — storage and async of still open views |

Previous batch: [views containing typed references](cycles/INLINE_TYPED_VIEWS_CYCLE.md).
Six new methods: six admitted programmes implemented and ten invalid programmes
The final target passage consists of nine methods; the
Related regressions pass 40 then 19 methods to O2/UBSan, output codes 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST7, ST10–ST12 | Effects on canonical root, target and mutable capacity retained | Reassignment typed via view, return of new target, access refused competitors | P — Synchronous calls and tested paths |
| ST13, ST17–ST18 | Shared reference/copy detached from the holder, always protected target | Relay, copy, drop of intermediate carriers, drop of the refused target | P — references to typed structures |
| Contrats, provenance transitive | A dependency through a reference is not a writing in its target object | Three historical regressions corrected; sync/async owner replacements retained | P — reset tested only in historical compatibility |

Previous batch: [views containing Int references](cycles/INLINE_REFERENCE_VIEWS_CYCLE.md).
Nine new functional cases, plus six view-copy tests, pass
at O0/UBSan: 16 admitted programmes implemented and 16 invalid programmes
The final regression is 82 methods to O2, then
Six methods of async copying: code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST7, ST10–ST12 | The path and the targets of the subtree remain attached to the root | Direct reassignments/contracts, transferable re-borrowing, incompatible access denied | P — champs terminaux Int/&Int/&mut Int |
| ST13, ST17–ST18 | A shared reference or copy keeps its target without artificially holding the holder | Relay returns and copies, drop of the accepted carrier, drop of the refused target | P — synchronous routes tested |
| Draft 07, storage sources | Inner copy without explicit pool requires a local root | Inferred and propagated requirement, copy return and incompatible pool | P — fields A<T>, storage and async of unconnected views |

Previous batch: [explicit copies of substructure views](cycles/INLINE_VIEW_COPY_CYCLE.md).
Six targeted methods are moved to O0/UBSan: seven admitted programs are implemented and
four invalid programs refused both entries.
35 methods to O2, code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST17–ST18, brouillon 07 | Independent copy in correct source, original retained | Local copy, explicit pool, destroyed source, re-use of slot | P — terminal field views Int |
| Transfert enfant → parent | Storage of the copy survives the producer | Blocks, explicit break, functions and relays | P — source paths tested |
| Last use, typed pools | Authorized copying and a fairly durable destination | Active re-borrowing, incompatible pool and too short pool refused | P — Async catches and reference fields not connected |

Previous batch : [ source borrowings of Int field substructures](cycles/INLINE_STRUCTURE_BORROWS_CYCLE.md).
Seven targeted methods are moved to O0/UBSan: nine admitted programmes are implemented and
10 invalid programs refused both entries.
61 methods at O2, then five historical methods of field paths: code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST6–ST7, dernier usage | The reserved prefix protects its subtree, not its brothers | Calls on two brothers, incompatible access denied, loan int | P — terminal field views Int |
| ST8, enfant → parent | Return keeps the way and the living root | Relay, block exit, drop and local root refused | P — Synchronous calls and tested paths |
| Adresses stables, nettoyage | View without independent allocation, result keeping address | Registered cases, if/loop results and destruction trace | P — copies, reference fields and async still to be connected |

Previous batch: [representation of substructure views](cycles/STRUCTURE_VIEW_RUNTIME_CYCLE.md).
Five targeted methods are switched to O0/UBSan and 34 O2-related methods, code 0.
Targeted tests check metadata and six C-exes of the internal BIT.
At the close of this internal lot, `open-inline-structure-borrow.crust` was
The above source lot then deals with this case.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST1, ST7, adresses stables | A view is the root bytes, without separate allocation | Metadata, return and re-use probe C, unchanged neighbour | P — internal representation only |
| AS10–AS13, MT | The description can be kept in a state and then transmitted between threads | Suspension/resumption on pthread, waiting before root drop | P — Manual ABI; unconnected source capture |
| ST6–ST8, borrowing and contracts | Prefix reserved, root duration and statically verified returns | Registered source case, currently refused as unsupported | N — raccordement requis avant validation source |

Last functional batch: [Inline inline constructors interlocked](cycles/INLINE_STRUCTURE_CONSTRUCTION_CYCLE.md).
Eight targeted methods are being moved to O0/UBSan: nine native executions and eight
programs that are invalid at both inputs. The final regression passes 62 methods
Three historical fixeds migrated to A<T> pass also
on the compiler of the initial snapshot; previous failures are preserved.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST1, ST3, ST4 | Single slot, recursive defects, nominal type and written order | Local littérals, injected/discharged pools, named paths, duplicates and rejected types | P — literal contents; values named/calculated off-batch |
| ST6–ST8, ST17–ST18 | Separate paths and shared targets preserved | Returns, copies, disjointed loans, premature drop refused | P — Int fields and representative references |
| AS10–AS14, nettoyage | Prepared fields cleaned before publication if suspended | Await in a field, local return, field A<Int>, suspended destruction probe | P — Finished paths, no general evidence |

Previous batch: [direct copies of async structures](cycles/ASYNC_DIRECT_COPY_CYCLE.md).
Six targeted methods go to O0/UBSan on the final version: six executions
The first step was to reduce the number of disabled students and to reduce the number of disabled students.
passes 69 methods to O2; after adjusting local references, 20 methods
directly linked to O2 on the final version. All processes: code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST17, emprunts | Explicit structural copy, shared targets retained | &Int copied, premature drop and copies A<T>/&mut refused | P — tested representative fields |
| ST18, V1, placement parent | New local value or slot of the chosen pool, without source promotion | Local/captured copies, explicit pool, alias and successive transfers | P — Inline structures interlocked outside lots |
| AS10–AS13, nettoyage | Result created in recipient, stable address after release of state | C probe, identity, empty state pool, destruction and reuse | P — Finished paths, without general proof |

Previous batch: [external destination of Select results](cycles/SELECT_RESULT_PLACEMENT_CYCLE.md).
Five targeted methods are being moved to O0: six native executions and two programmes
The regression is not the same as the previous one.
Final passes 94 methods to O2/UBSan, code 0, including the targeted methods.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| Placement parent, AS10–AS13, SL1 | Branch manufacturers use the destination of the result received | Manufactures, direct branches, intermediate block and task return | P — Local point tested; general forms to be completed |
| Adresses stables, nettoyage | The winner keeps his address; other values and states are cleaned | C-suspension and termination probes, storage meters and empty pools | P — Finished paths, no general evidence |
| Duration of pools and borrowings | The placement does not promote explicit pool or borrowed target | Pool short and drop before last reading refused | P — Targeted cases and related regressions |

Previous lot: [restitution after replacement owner](cycles/RETURNED_OWNED_REPLACEMENT_CYCLE.md).
Six targeted methods go to O0: six native executions and four programmes
In the case of both entries, i.e. eight refusal checks.
two regressions on intertwined descendants, the 90 related methods pass
on the final version in O2/UBSan, code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| Remplacement, transferts, adresses stables | The result returns the root and its final graph | Same address before/after call and join, old and new fields destroyed once | P — tested roots and fields |
| AS10–AS13, duration of sources | The result keeps the new pool and the fields unchanged | Relay await, pool short refused in sync/async, neighbour unchanged, depth model | P — General graphs and headings to be completed |
| Emprunts, nettoyage | The replaced descendant retains its targets; the failure of launch does not replace anything | Descendant &Int, premature drop refused, LaunchFailed, re-use of slots | P — Targets and paths tested, without general evidence |

Previous lot: [replacements owners of factories](cycles/FACTORY_OWNED_EFFECTS_CYCLE.md).
Six targeted methods are being moved to O0: eight native executions and three programmes
The final regression
passes 117 methods to O2/UBSan, including the six targeted methods, code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS3–AS5, AS16, contrats | A delayed replacement keeps its wearer and pool at each phase | Separate intermediate/final pools; relay and permutation without synchronous bodies | P — graphs represented, A<Int> and descending containing &Int tested |
| AS14, SL1, D1 | Creation inactive without writing; loser preserved and cleaned | Drop inactive, await, join, LaunchFailed and Select, re-use slots | P — no general evidence on all alternatives |
| Pools, borrowings | The field received and its targets survive the last access | Pool final court refused in await and join, target borrowed protected | P — Competitor prefixes of off-batch hands |

Previous batch: [synchronous factory suspension prefixes](cycles/FACTORY_SUSPENSION_CONTRACTS_CYCLE.md).
Five methods go to O0: nine native executions and six invalid programs
The final regression passes through the two entries, i.e. twelve refusal checks.
97 methods at O2/UBSan, including the five targeted methods, code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS3–AS5, contrats | A factory retains the effects of suspension of the transferred task | Relay, rotation, transfer and control of contracts without synchronous bodies | P — borrowed fields Int represented |
| AS14, AS16 | Inactive creation, suspension and termination have distinct effects | Drop inactive without writing; restoration only at termination | P — Replacements owned by non-connected mills |
| SL1, emprunts, branches | A loser keeps her writings suspended and their addictions | Select direct or via relay, choice between two catches, premature drop refused | P — Conservative unions, competing prefixes of off-batch handles |

Previous lot: [mutable returns from a possessed descendant](cycles/ASYNC_MUTABLE_DESCENDANT_RESULTS_CYCLE.md).
Five targeted methods go to O0: six native executions and nine programmes
The following are the final steps in the process of determining the number of persons who are disabled at both entries, i.e. 18 refusal checks.
110 methods at O2/UBSan, including the five targeted methods, code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| Retours enfant → parent, emprunts mutables | The borrowed descendant retains a sustainable provenance and its capacity | Synchronous return then async, example previously refused now executed | P — &mut Int and graphs represented |
| Last use, AS16 | The wearer and the target remain reserved until last use | Reading, target writing, drop and replacement refused before; access allowed after | P — check and generation agree on the cases tested |
| Remplacement, SL1 | The effects are aimed at the new descendant and the result is going through expectations | Join, LaunchFailed, relays await, Select; exclusivity control unchanged | P — Other forms of graphs and types to be completed |

Previous lot: [returns of loans after replacement of a descendant](cycles/ASYNC_REPLACED_BORROW_RESULTS_CYCLE.md).
Six targeted methods are increased to O0 and O2: 10 native executions and 10 programmes
Inactive at both entrances by passage. Regression linked: 125 methods to O2/UBSan,
on the same implementation, before adding the last two targeted tests.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| Retours d'emprunts, AS16 | The result keeps the target read at the time of its creation | Old snapshot and new reading distinguished by contracts and execution | P — shared references Int |
| Transfers, last use, D1 | The carrier can be destroyed; the external target of the result must survive | Drops admitted/refused after join and relay; failure to launch | P — descendants followed and external targets |
| Branches, SL1 | Alternatives remain protected and the result survives Select cleaning | Two branches executed, winning result after drop of Select and the carrier | P — no generalization to all mutable results |

Previous batch : [Internal mechanism of mutex](cycles/MUTEX_RUNTIME_CYCLE.md).
Four targeted methods run six probes C to O0; the bound regression passes
26 methods to O2. Clang/pthread/UBSan, processes completed with code 0.
The manufacturer and static guard control are not connected.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| MT9 sync | Thread-related guard; next acquisition observes the scriptures | Two threads, drop the wrong thread refused, single destruction | P — runtime; suspension ban not implemented |
| MT9 async, RT2 | Keeps stored through yield and free after migration | First poll in hand, release on another thread, waiter Pending awakening | P — C mechanism; type-setting and derivative loans to be connected |
| SL1, MT9 | Drop loser withdraws waiting/reservation or destroys custody | Three losing states in Select, booking forwarded to next | P — manual probe callbacks; mutex source generation absent |

Previous lot: [replaced downcendants containing borrowings](cycles/ASYNC_OWNED_BORROW_WRITES_CYCLE.md).
Eight targeted methods are increased to O0: 12 native executions, 13 programmes
The O2/UBSan regression passes 127 methods
before the last conditional adjustment, then 19 related methods pass on
the final state at O2/UBSan. All these processes are completed with code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS16, SL1, contrats | The replaced descendant retains its targets according to the state actually reached | Await, join, LaunchFailed, Select, pre/post yield scripts | P — &Int and &mut Int fields |
| Borrowing, lifespan, transfers | The received field protects its target until last use | Premature drop and mutation refused, short scope target refused | P — cibles Int suivies |
| Branches, remplacement, D1 | The absence of replacement retains the old target; slots remain reusable | Two branches executed, protected alternatives, cleaning and reuse | P — Conservative unions; in-depth deferred audit |

Previous batch: [field replacement owned in async](cycles/ASYNC_OWNED_FIELD_WRITES_CYCLE.md).
Seven targeted methods are being moved to O0 and O2: eight native executions and one
program refused to both entries by way of passage.
109 methods to O2 with UBSan before the last scope fit, then
The two targeted passages cover no new adversarial campaign.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS16, field contracts | The sources of suspensions are distinct from those at termination | Contrats, await, join, Select perdant, descendant d'enum | P — descendants replaced without borrowings contained |
| Transferts, pools, D1 | The receiver retains the source and destroys its old field once | Direct assignment, auxiliary, re-use of slots, LaunchFailed | P — unions of sometimes conservative sources |
| Child life → parent | Pool survives last allocation received | Pool intermediate short accepted, pool final short refused, recipient transferred to child | P — listed cases; independent audit deferred |

Previous Lot: [fieldslectures in a shared match](cycles/SHARED_MATCH_FIELD_READS_CYCLE.md).
Three targeted methods are being moved to O0, with four native executions and one
The related regression is made from 64 methods to O2
with UBSan, code 0. The case recorded `open-shared-enum-descendant-read.crust`
is now executed. No additional adversary campaign.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| F2, readings and copies Int | The field is read through its shared projection; the copied result does not hold its carrier | Direct reading, variable, calculation and destruction before using the result | P — Int-tested expressions |
| Typage, emprunts | Syntax filter does not replace field and target control | Unknown field refused, field regressions and mutable matches | P — no generalization to all expressions |

Previous batch: [references of enum descendants to suspensions](cycles/ASYNC_ENUM_SUSPENSION_FIELDS_CYCLE.md).
Five targeted methods go to O0: three analytical checks, two executions
The first is the first time that the new system has been introduced.
passes 127 methods to O2 with UBSan, code 0. No adversarial or campaigning
additional mutations are not performed, according to the user's instructions.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS16, field contracts | The suspended state keeps the entries already made | Separate targets for suspensions and termination, union of several yields | P — Int references in a storage graph unchanged |
| AS8–AS15, SL1 | The effects reach the appellant's descendant after await or Select | Two native executions, contract relay, drop of the new target refused | P — Forms tested; replacement of separate allocation |
| Contracts, local identity | The mutable borrowing of an enum keeps the bearer and his graph | Application of contracts to local enums, regressions of descendants and alias | P — no independent audit or coverage of recursive graphs |

Previous batch : [match consuming enums in async](cycles/ASYNC_CONSUMING_ENUM_MATCH_CYCLE.md).
Ten targeted methods go to O0: 10 native executions, 10 invalid programmes
The directly related regression passes 117 methods to O2
with UBSan, code 0. According to the last user's instructions, this lot implements and
tests the cases already listed; it does not add adversarial campaign or
The independent audit is not deemed to have been carried out.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| Transferts, F2/U1, D1 | The fields possessed are received, the carrier destroys once before the body | Explicit use of each motive, bearer/field destruction, address retained, re-use | P — Enums and fields represented |
| Pools, contracts of provenance | The result extracted retains its own sources | Downhill return, nested graph, pool holder accepted and pool target refused | P — producers without detailed metadata remain conservative |
| B1–B5, AS8–AS15 | Borrowings extracted retain their targets and capacities | Shared/mutable returns, reference stored in a field, premature drop refused | P — tested forms |
| D1, SL1, loop outputs | Suspension and exit clean the transferred fields without double destruction | Yield, loser Select, break, continues and returns | P — functional tests and regressions, without independent audit |

Previous batch: [match of enums per async loan](cycles/ASYNC_ENUM_MATCH_CYCLE.md).
Seventeen targeted methods go to O0/O2: 20 native executions, 16 programmes
The six mutations are detected.
synchronous regression passes 125 methods and final async regression passes
173 methods, at O2 with UBSan. All final processes are completed with
code 0. The ratio distinguishes the corrected defects, a historical assertion
updated on proof of snapshot, and compositions still open.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| P9, AS8/AS9, branches | Good arm, stable projections and correctly received result | Three reordered variants, yield, alias, Int/Bool, nested branches and returned allocations | P — match by loan, not consuming |
| B1–B5, ST13, AS12, match returns | The bearer is reserved during the arm; outgoing loans keep their targets and capabilities | Reborrowing, child async, caller's mutable return, split result detached and exclusive parent | P — Projections and contracts represented |
| D1, SL1, RT6 | Exits and losers clean without releasing a target still required | Return/break/continue, failure to launch, re-use, mutable loser and pre/post drop uses | P — finished graphs tested |
| AS16, SL1 | An incomplete contract is not published as a lack of effect | Accurate termination summary, explicitly incompletely possessed graph suspension, detected mutation | P — valid composition still to be implemented |

Previous batch: [enums allocated in async](cycles/ASYNC_OWNED_ENUMS_CYCLE.md).
Twelve targeted methods go to O0/O2: 24 native executions, 14 programmes
The five final mutations are detected,
of which an inactive arm reading initially surviving; the report describes
the strengthening of the oracle and its limits.
200 async methods and 235 synchronous methods at O2 with UBSan. All
Final processes are completed with code 0. Intermediate failures and
corrections are retained in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS2, AS8–AS10, transferts, pools d'enums | Capture and return keep allocation, arms and source | Await, join, relays, pools by different arms and sizes, re-use | P — representable finished aggregates; direct match async still open |
| AS11–AS15, contrats, emprunts | Loans and necessary sources survive returns | Public handles, opaque contract without body, drop and pool short refused, choice of arms | P — root variants; precision of the descendants to be tested |
| SL1, D1, RT6 | Selection and launch failure clean each capture once | Independent model of four suspension orders, fields owned, re-use | P — not all graphs or envelopes |
| Active layout and border C | An auxiliary does not read fields of an inactive arm | Three arms with separate offsets, C readings, mutation detected | P — oracle depends on layout metadata; UBSan alone insufficient |

Previous batch: [type and storage of Select result](cycles/SELECT_RESULT_STORAGE_CYCLE.md).
Ten targeted methods go to O0/O2: 17 native executions, 18 programmes
The five mutations are detected by the
The extended regression is 167 methods at O2 with UBSan.
All final processes are completed with code 0; report retains
intermediate failures and their causes.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| SL1, V1, T1/T6 | The result type distinguishes local T from A<T>, even without pollution | Previously accepted counter-example, refusal to both stages; eight storage/suspension combinations | P — storage classes of the structures represented |
| Branches, boucles, contrats | If, break and task relays do not hide the result storage | Allowed programs executed and mixtures rejected; four mutations of the comparisons detected | P — finite compositions tested |
| D1, AS8–AS15, RT6, L1/L2/L6 | The origins concern the result; loans and cleanings remain | Unreturned captures, pool descendants, shared result, premature drop, launch failure and re-use | P — no generalisation to all aggregates |

The type and public signatures of `runtime::set_scheduler` restent
explicitly to arbitrate, according to the user's response.
validated guarantees are not carried forward. `design-buffer/points-ouverts.md`.
`validation/open-async-owned-enum.crust` is now accepted and executed in
The remaining limits are detailed in the associated report.
`validation/open-async-enum-match.crust` is now executed in the lot
suivant. `validation/open-async-consuming-enum-match.crust`initially refused,
is now executed by the above consuming game lot.

Previous lot : [choose between borrowed descendants](cycles/NESTED_FIELD_CHOICES_CYCLE.md).
Eleven targeted methods go to O0/O2: 17 native executions, 15 programmes
The independent model covers 12 combinations of invalids and 30 refusal checks.
7 admitted executed, 5 refused in both stages.
are detected; a survivor in the first targeted test is detected by the case
whole object/descending in the complete suite. Regressions pass
178 contract/async methods and 90 table methods at O2 with UBSan.
All final processes are completed with code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| Branches, ST6–ST15, B1–B5 | Writing by chosen aliases certainly does not replace all candidates | Field effects inspected, two choices observed in C, identical branches, target model | P — Conservative unions, all unrepresented correlations |
| Contrats, D1 | The opaque appellant retains the possible old targets of descendants | Counter example verify/compile diverge corrected; refusal to both steps; mutation detected | P — covered roads and finished types |
| Reborrowable loans, T1/T6, AS8–AS15 | Capacity and targets through projections, loops and transfers | Mutable target, additional projection, whole/descending object, expected destruction denied | P — General signatures still to be audited |

`open-nested-field-choice.crust` is now accepted and executed.
The precise public contract of the scheduler remains to be clarified; the question has been
addressed to the user without suspending the independent work.

Previous lot: [contracts borrowing the parent of a descendant](cycles/NESTED_FIELD_WRAPPERS_CYCLE.md).
Ten methods go to O0/O2: 17 native executions, 16 invalid programs
The five mutations are detected, including the mutation
child fields surviving the previous cycle: a new scenario reads
the descendant modified before updating his brother. The regression passes
153 methods at O2 with UBSan; the last three tests pass in the
Final baselines. All processes are completed with code 0.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST6–ST15, contrats, B1–B5 | The contract applied to the parent updates the exact descendant | Contract inspected, sync/async callers, successive relays, alias, external source | P — conditional choice between descendants still unconnected |
| D1, affectations conditionnelles | Lack of replacement preserves old possible target | Contra-example accepted during the corrected connection; independent model with 12 combinations | P — Finished model, no general evidence |
| AS8–AS15, RT6 | Transfer to a task keeps new targets until cleanup | Anticipated drop refused, mutable target, injected failure, re-use of slot | P — families of signatures tested |

`open-nested-field-wrapper.crust` and its synchronous variant are executed.
`open-nested-field-choice.crust` was then a valid program refused,
processed by the above lot.

Previous lot: [references replaced in descendants]](cycles/NESTED_FIELD_REPLACEMENT_CYCLE.md).
Eleven methods go to O0/O2: 18 native executions, 18 invalid programs
The independent model covers 12 combinations of the two models.
7 admitted executed, 5 refused both stages.
The fourth one also survives the entire targeted sequence, without
The regressions pass 144 async methods
and 46 synchronous O2 with UBSan. All processes are complete.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST6–ST15, B1–B5, D1 | Replace a field only changes its dependencies; the new target remains valid | Shared/mutable fields, two homonymous brothers, two levels, conditional, target model | P — finite graphs; mutation of child surviving metadata |
| T1/T6, AS2/AS8–AS15 | Transfer/return graph keeps updated targets | Direct projection/alias, task modification, return owner, premature drop refused | P — relays using the entire unconnected parent |
| RT6, contrats | Launch failed to destroy once catches have been taken, even after replacement | Injected failure, Inner/Outer traces, manufactures without delayed write-offs | P — no generalisation of prefixes suspended from factories |

`open-nested-field-replacement.crust` is accepted and executed after correction
its explicit borrowing rating. `open-nested-field-wrapper.crust` demeure
a valid case then refused, now processed by the above lot.

Previous batch: [handles launched in arguments from async](cycles/ASYNC_EXECUTION_ARGUMENTS_CYCLE.md).
Nineteen methods go to O0/O2: 26 native executions, 25 programmes
50 refusal checks. Six targeted mutations are detected;
The seven historical records are also, including one by crash of the compiler.
Three finished models pass, with 53 admitted cases executed and 19 rejected cases.
The extended regression passes 214 methods to O2 with UBSan; the last two
added tests pass separately in the final baselines O0/O2. All the
lot process is completed.
Intermediate tests and their limits are kept in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, contrats, AS9/AS12, MT5/MT6 | A handle relay keeps catches, storage and dependencies of the result | Public/Concrete Relays, References, T/A structures<T>, Tables, str, short pools, re-use | P — signatures represented; no generalisation to all forms |
| RT5–RT7, SL2, order of arguments | No reviving, hidden join or abandoning prepared handle | Bid counter, launch failure, native block, return/break/continue, loser Select refused both stages | P — capture of a handle launched in an inactive task remains separate |
| B1–B5, D1, field effects, RT6 | After waiting, possible targets include successful writings and initial status of LaunchFailed | Counter example accepted drop corrected; local and injected fields; two separate mutations detected | P — auxiliaries waiting without proper writings and with scalar result; other compositions conservatively incomplete |

`open-public-structure-async-relay.crust` is now accepted and executed.
The replacement of dependencies of a descending field was still open;
the above lot processes direct projections and their aliases.

Previous batch : [public handle of structures](cycles/PUBLIC_STRUCTURE_HANDLES_CYCLE.md).
Fourteen targeted methods go to O0/O2: 24 native executions, 26 programmes
the number of invalids and 52 refusal checks, plus the control of a private caller
Six of the seven new mutations and five of the six historical ones are
detected; both survivors are documented, without general equivalence
The final regression is 157 methods at O2 with UBSan.
All the processes mentioned are completed; the two campaigns of change
keep their code 1 for survivors, without masking this limit.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| V1, T1/T6, contrats, AS9/AS12, MT5/MT6 | Handle<T> does not convert storage to A<T>, nor does it convert storage to A<T> | Sync/async annotations, factory obligations, two types of routines, mixed branches refused with/without annotation | P — structures represented; general signatures still open |
| B1–B5, D1, MT5/MT6 | Public type retains the targets and capabilities of returned fields | Shared/mutable borrowings, mutable ancestor, descendants owned, relays and calling without any body | P — finite graphs tested; list transfer of surviving loans, protection of fields still active in these cases |
| A2, L1/L2/L6, AS8/AS12, RT6/RT7 | Pool survives result and cleaning returns each slot once | Pool short refused, ability a re-employed, failures of two-level launch, traces of destruction | P — native scenarios O0/O2 UBSan, no general evidence or new ASan/TSan result |

`open-public-local-structure-handle.crust` is now accepted and executed.
`open-public-structure-async-relay.crust` was then valid but not connected,
and is treated by the above lot.
a descending field also remains open. SL2 remains applied.

Previous batch: [storage of job results in contracts](cycles/TASK_RESULT_STORAGE_CYCLE.md).
Eleven targeted methods go to O0/O2: 14 native executions, 18 programmes
The regression O2 passes 128 methods with
UBSan; seven targeted errors and six historical ones are detected.
The public types of structures are still to be connected.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| V1, T1/T6, contrats, AS9/AS12, MT5/MT6 | The result keeps its local T or A<T> storage through an opaque task/handle | Local matrix/pool, three relays, two conditional sources, Concrete execution; contracts inspected, false calls denied | P — concrete tasks and handles; Handle<Structure> remains open |
| V1, A2, L1/L2/L6, AS12 | Root, descendants and unreturned catches remain distinct | Copy from a loan; local root/pool down; re-use of capacity one; changes in projections | P — finished graphs supported, no generalisation to recursive types |
| B1–B5, D1, MT6 | A profit or loss notation does not release its borrowings | Return of a structure containing a reference, relay and then premature drop refused | P — finite interactions, no general evidence |
| RT7, SL2 | No hidden join or abandonment of a handl thrown into a loser | Hidden Join refused since async; SL2 counter-example refused both stages | P — capture of a handle launched in an inactive task still to be arbitrated |

Previous batch: [task arguments from an async state](cycles/SYNC_TASK_ARGUMENTS_CYCLE.md).
Eighteen targeted methods are moving to O0/O2 (seventeen in the O2 regression).
then the separate break/continue supplement). The O0 count counts 24 executions
7 transfers, 26 invalid programmes and 52 refusal checks.
Targeted are detected, including one by crashing the compiler on a program
valid; eight historical mutations are detected.
passes 140 methods and final 132, covering selections. All processes
The final report is completed; chronology and limitations in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, B1–B5, D1, AS2/AS9/AS12 | The task relay keeps catches, sources and loans of the result | Shared/mutable borrowings, tables, interlocking graphs, local/pool results, conditional choices, public/concrete handles | P — signatures represented; Handle<local structure> remains open |
| AS8/AS13/AS14, L1/L2/L6, SL1 | Prepared tasks are cleaned before their sources, without throwing their bodies | Suspension, early return, break/continue, Select loser, ability to re-employed, reverse order; leak mutations detected | P — Covered constructions/routines; prefixes of general factories still conservative |
| Contrats, SL1 | A pure relay keeps the effects suspended, without masking a fresh alternative | task_forward_only inferred on all paths; new task in a branch, mutation of the inferred fact | P — static contract analysis, no general evidence of convergence |
| SL2, RT7, MT3/MT4 | A loser can't give up a handle thrown still to wait | Explicit decision of the integrated user; open-select-launched-handle.crust refused both steps with SL2 diagnosis | P — conservative restriction; capture of handle in an inactive task still to be arbitrated |

The relay `validation/open-async-task-relay-argument.crust` is now
Executable. `validation/open-public-local-structure-handle.crust` and
`validation/open-nested-field-replacement.crust` SL2 closes
the arbitration of Select; the arbitration notices pending in the former
reports are historical.

Previous batch: [Removed references of the descendants possessed](cycles/NESTED_DETACHED_REFERENCES_CYCLE.md).
Fourteen targeted methods go to O0/O2. The final count O0 takes over
22 native executions, 27 invalid programmes and 54 refusal checks.
Seven targeted errors and six historical records are detected. The lot has been reopened
After discovery of a double projection losing the loan in an async caller;
this defect is corrected and its counter-example retained.
pass 110 async/bridge methods and 56 synchronous field methods to O2 with
UBSan. The 110 async/bridge methods are passed again after the last patch.
Selections overlap; accounts do not add up as tests
All processes cited are completed.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST13/ST14/ST15, H1/H2, B1–B5 | A returned shared reference keeps the target, without holding the holder possessed | Direct/manufacturer, helper chain, public handle, waiter, end of intermediate pools; refusal of own storage and mutable copying | P — finished graphs with sheets & Int ; no generalization to cyclic graphs |
| D1, AS2/AS9/AS12, T1/T6 | The loan returned remains after waiting/join; the union of possible paths is protected | Target model × instant × path; two invalid acceptances after await corrected; conditional returns and loan loss transfer | P — provenance by road, finished cover; updating of open progeny fields |
| AS8/AS13/AS14, RT6/RT8, SL1, L1/L2/L6 | Single carrier cleaning and re-use without invalidating the target | Inactive, launch failures, native thread, Select loser, loop with re-used slot; seven mutations and UBSan O0/O2 | P — issued handls subject to existing arbitrations; no ASan/TSan or general evidence |

The case `validation/open-nested-detached-reference.crust` is corrected in this
perimeter. `validation/open-async-task-relay-argument.crust` and
`validation/open-nested-field-replacement.crust` The old ones stay open.
the following are historical and are replaced by this lot when they
concern the shared detachment of descendants.

Previous lot: [borrowing in the descendants possessed](cycles/NESTED_OWNED_BORROWS_CYCLE.md).
Fifteen targeted methods are switched to O0/O2 (thirteen to O2 and then two separate additions).
The final count O0 shows 23 native executions, 32 invalid programmes and
64 refusal checks. Six targeted errors and nine errors from the previous batch are
Async regressions pass 98 methods before restitution
field complete, then 96 on the final code; overlay selections.
A synchronous complement of 87 methods passes on the final code for the
fields, nested references and proprietary results. All
The final processes cited are completed; newspapers and chronology in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST6–ST15, B1–B5, D1, AS2/AS9/AS12 | The targets of the possessed descendants are preserved by their complete path | Model of the eight provisions, homonymous fields, depths two and four, factories, conditional returns and full restitution | P — finished type graphs, &Int/&mut Int ; detachment of a still open downward loan |
| H1/H2, T1/T6, AS8/AS12 | Explicit access to content does not move allocations or their targets | `read(&*result.inner)`, C probe of three addresses, child reborrowing after mutable return, refusal of drop and early access | P — readings and borrowings of covered content; modifications of progeny fields via non-generalised helper |
| L1/L2/L6, AS10/AS13/AS14, RT6/RT8, SL1 | Unique destruction of descendants, never borrowed targets; no living re-employment | Inactive, LaunchFailed and native failure injected, Select losing, one/two re-used capacity pools; six mutations including two invalid acceptances detected | P — UBSan O0/O2, no ASan/TSan evidence or completeness |

The refusal of the Outer → A<Inner> → &Int graph announced below is corrected.
The next valid rejected counter-examples are recorded in
`validation/open-nested-detached-reference.crust` and
`validation/open-async-task-relay-argument.crust`. Aucun arbitrage normatif
is deducted from these compiler restrictions.

Previous batch : [mixed async structures](cycles/ASYNC_MIXED_STRUCTURES_CYCLE.md).
Thirteen methods go to O0/O2; the final count O0 counts 23 executions
The first phase of the programme is the first of its kind.
are detected after correction of a test that did not exercise its point
Injection Regressions: 161 methods after the source patch and
33 methods after the placement; selections covering all the
processes cited are completed. No normative changes.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST1/ST6–ST16, B1–B5, D1, AS2/AS9/AS12 | A possessed bearer keeps his children's pools and borrowed targets | Independent model of 8 provisions × direct/manufacturer; child target not promoted; mutability, copy not Copy refused, descendant possessed in a separate pool | P — Direct borrowing Int ; borrowings in descendants still open |
| T1/T6, P3/P4, AS8/AS12 | The placement follows the returns by parameter without moving an address | Loop replacement per task or factory; probe of three addresses on suspension and transfer; two placement mutations detected | P — local origins followed by contracts; general placement not completed |
| L1/L2/L6, AS10/AS13/AS14, RT6/RT8, SL1 | Single cleaning of children only; loan loans retained | Inactive, injected failures, native thread, early return and Select losing during a suspended argument; slots immediately reusable; nine detected errors, UBSan O0/O2 | P — no new ASan/TSan evidence; issued under existing arbitrations |

The direct mixed deviation from the previous batch is corrected.
`validation/open-nested-owned-borrowed-capture.crust` remains refused: a field
A<Inner> of which Inner contains a loan requires additional projections.

Current batch: [manufacturing tasks with borrowed result detached](cycles/DETACHED_TASK_FACTORIES_CYCLE.md).
Thirteen methods go to O0/O2: 21 native executions and 30 programmes
In the two stages of O0 counting, eight mutations were detected.
Regressions pass 190 methods and then 107 after the additions of the waiter
and Select; 100 field methods pass on the final compiler.
These selections overlap. Timeline and limitations in the report; all
the final processes are completed.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST8/ST13/ST14, AS10/AS12, B1/B2/B4a | The detached result keeps its real target, without holding the other fields or the carrier's storage | Counter-example of drop after was previously accepted at both stages then refused; target model × instant × three paths, loan loss transfer | P — Int shared fields; mutable projections and open general graphs |
| ST10, D1, T1/T6, AS2/AS9 | Manufacturers and helpers have a termination contract available; targets remain sustainable even after replacement | Three orders of declarations, conditional returns, completed porter pool, local target refused, waiter and public Handle | P — inference to demand and then stabilization; no general evidence of convergence |
| L1/L2/L6, RT6, AS8/AS13/AS14, SL1 | Unique cleaning and loan of loser kept until Drop Select | Injected, inactive, manufacturing refusal in Select, loop re-use, eight mutations and UBSan O0/O2 | P — no outstanding outstanding handle obligation; ASan/TSan not established |

The difference in the mill's distance from a field reported in the historical cycle
below is corrected within this perimeter.

Current lot: [field capture contracts and bearer restitution](cycles/ASYNC_CAPTURE_FIELD_CONTRACTS_CYCLE.md).
Thirteen methods go to O0/O2: 24 native executions, 37 invalid programs
rejected in both stages of counting O0. Seven new mutations and eight
The nature of the detections is detailed in the
The extended regression is reduced to 195 methods to O2 under UBSan.
final processes are completed.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| B1/B2/B3/B4a, AS2/AS9, MT8 | Each field keeps its target and its capacity in relays | Six-access model × two relays, symbolic contract per field, fusion mutations | P — Int/&Int/&mut Int ; graphes mixtes ouverts |
| T1/T6, D1, ST6–ST15, AS10/AS12 | The returned carrier retains exactly its targets, without promotion or displacement | Integer return shared/mutable, factories, parent, loops, conditions, model of the four arrangements, addresses and slot reused | P — direct cases and manufactures of the covered bearer; manufacture detaching a field still refused |
| L1/L2/L6, AS8/AS13/AS14, RT6, SL1 | Unique cleaning, loans kept after await and for the loser Select | Inactive, LaunchFailed injected, Select, drop counterexamples, seven mutations and UBSan O0/O2 | P — no abandoned launch handle, no new ASan/TSan evidence or general evidence |

The two mixed relay and full return deviations mentioned in the batch
history below are corrected in this new perimeter.

Current Lot: [captures owners of borrowing structures](cycles/ASYNC_OWNED_BORROWED_CAPTURES_CYCLE.md).
Eleven methods go to O0/O2: 19 native executions and 24 invalid programs
The two steps were rejected at O0 counting. Eight mutations were detected; the
155 methods are used. All final processes are completed.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, B1/B2/B3/B4a, D1, MT8 | The transfer of the bearer keeps the loans of his fields | Direct, factory, task relay, mutable and two-way model | P — Int/&Int/&mut Int; shared/mutable mixed relays too restrictive |
| AS2/AS5/AS8/AS9/AS13/AS14, RT6/RT8, L1/L2/L6 | Cleaning the single carrier, never destroying its target | Inactive task, failed launch, native thread, prepared argument and Select loser | P — without unsolved join obligation; eight transfers, UBSan O0/O2 |
| ST6–ST15, AS12 | The target of a detached reference survives the bearer | Shared result used after join, premature target drop refused | P — return of whole structure still refused; mixed graphs open |

Current Lot: [Envelopes Result of local values](cycles/LOCAL_RESULT_ENVELOPES_CYCLE.md).
Nineteen methods go to O0/O2: 29 native executions and 36 programmes
The 14 final mutations and the
eight historical records are detected; a redundant anterior mutation and a
The final regression is verified in the report.
The process is completed.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, ST6–ST15, AS9/AS12, B1/B2/B4 | The envelope retains its targets and reservations after the end of the state | Opaque relays, method, mutable, interlocking branches/loops and extractions | P — Int/&Int/&mut Int families tested; general graphs open |
| D1, L7, storage requirements | Result<T> and Result<A<T>> remain distinct in signatures and junctions | Model 2×2, annotations, feature and mixed counter example refused | P — distinction also without charge; finished cover |
| L1/L2/L6, RT6/RT7, AS12 | A mistake without charge creates no fictitious identity or destruction | Injected failures, relays and three forms of control, closed branch preserved | P — proven absence distinct from unknown; UBSan O0/O2, no general evidence |

Current batch: [local results async containing borrowings](cycles/ASYNC_BORROWED_LOCAL_RESULTS_CYCLE.md).
Seventeen targeted methods go to O0/O2: 36 native executions and 36
Invalid programs refused in both stages. Nine final mutations are
detected; the initial survival of an unexercised fault and its audit are retained.
The final regression of 98 methods passes.
has 238 successes and an erroneous historical fixture, reproduced before
the lot and corrected; the 49 methods of the two historical modules pass
Then with UBSan. All the final processes mentioned are completed.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST6–ST15, B1/B2/B4a, AS9/AS12 | Fields borrowed from the result retained after release of the state | Await/join, factories, sync/async relays, disjointed fields, mutable and Select, nine mutations | P — Int/&Int/&mut Int fields, sustainable parametric targets; open mixed graphs |
| D1, T1/T6, L7, AS5/AS13 | Local root in recipient, targets never promoted | Independent model of the four provisions of two targets, successive parent transfers, conditional results | P — sources represented; general local outcome<T> signatures open |
| L1/L2/L6, V5, AS8/AS14 | Stable addresses and single cleaning including booking not used | Normal/suspendable C probes, direct/helper construction, injected failure, re-use of slots | P — UBSan O0/O2; unused reserve corrected; no general evidence |

Current Lot: [local results async to proprietary fields](cycles/ASYNC_LOCAL_OWNED_RESULT_GRAPHS_CYCLE.md).
Twelve targeted methods go to O0/O2: 19 native executions and 19 programmes
Eight new mutations and eight historical changes
The extended regression passes 180 methods; 63 methods pass after
the latest placement and source of factory. Chronology
The report states that all the processes cited are completed.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| L7, V5, T1/T6, AS9/AS12 | Root built in the recipient, descendants left in their pools | Direct returns, factories, relays, parent after join, identity C through two poll | P — finished graphs without borrowings, fresh roots |
| D1, ST7, AS5/AS13 | Each downhill pool survives the result | Model of four provisions × three paths of appeal, contracts for grandchildren, refusal in both stages | P — sources represented; general local sources open |
| B1/B2, L1/L2/L6, AS8/AS14 | Loan of respected result, single cleaning and reuse after destruction | Loop replacements, injected failure, inactive task, suspended probes, eight mutations | P — UBSan O0/O2 finished tests; no general evidence |

Current batch: [pools async of borrowing structures](cycles/ASYNC_BORROWED_STRUCT_POOLS_CYCLE.md).
Fifteen targeted methods are being moved to O0/O2: 28 native executions and 31 programmes
The final regression
goes 153 methods to O2. All processes cited are completed.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST1–ST4/ST10, AS8/AS9, T1/T6 | Initialized, transported and updated borrowed fields without having the target | Constructeurs, arguments suspendus, branches/boucles, remplacements directs/sync/async | P — Int/&Int/&mut Int ; graphes mixtes ouverts |
| ST6–ST14, B1/B2/B4a, D1 | Target protected as long as the holder remains borrowed; separate shared detachment and mutable reservation | Counter-example task corrected, handle/alias variants, disjointed paths and ten mutations | P — Loans of the types represented; general accuracy open |
| AS10/AS12, L1/L2 | Shared return independent of the wearer; single cleaning without local promotion | Return via helper, local target refused, probes suspended, UBSan O0/O2 | P — whole returns/captures of open borrowing structures |

Current batch: [pools of async structures](cycles/ASYNC_STRUCT_POOLS_CYCLE.md).
Local/injected pools and named manufacturers are connected for
Int/A<T> finished structures supported. Fresh return from a pool
Injected transmits the sources of the fields in the contracts.
Fifteen targeted methods are switched to O0/O2: 25 native executions and 19 programmes
The number of disabled people who were refused both stages.
extended 174 methods; 51 additional methods of contracts/results
go over the final state. All the processes mentioned are completed.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| A1–A4/P8, ST1–ST4, AS8 | Durable source and layout between pollutants; values initialized before exposure | Defaults, named fields, order with await, injected pools and alias, slot probe | P — Int/A<T> finished; borrowed fields open |
| ST15/ST16, D1, T1/T6, AS10/AS12 | Cleaning of prepared fields; dependence on sources of all descendants | Early return, suspension, nested graph, direct/manufacture result and pool neighbor too short | P — new result in injected pool; general open local result |
| B1/B2, L1/L2, AS14, SL1 | Secured re-borrowing; closure after destruction, re-use without moving neighbour | Drop allowed/refused, continuous/break, suspended probe, eight targeted mutations | P — UBSan finished coverage; Select supplement followed in report |

Current Lot: [tasks and destination of the result](cycles/ASYNC_RESULT_FACTORIES_CYCLE.md).
Sixteen targeted methods go to O0/O2: 35 native executions and nine
disabled programs refused in both stages. Eight mutations detected,
including an undue acceptance of drop after returning from a UTF-8 view.
Regression after completion complement is complete: 216 methods
successful in 166,544 s at O2, newspaper
`validation/async-result-factories-completion-regression-o2.log`.
The previous passage of 191 methods remains a historical evidence of the past
the latter supplement.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS5/AS9/AS10/AS12, L7, V5, T1/T6 | The destination of the future result survives at the factory, without displacement or conversion T/A<T> | Chains, instance transfer, branches and loop, contracts and two modes of probe C | P — Root structures covered; general graphs open |
| B1/B2, D1, AS2/AS13 | Captures and results keep their dependencies distinct; no pool or target borrowed is promoted | Local/pool copies, parents, nine invalid neighbors, result &mut Int and &str, eight mutations | P — bridge signatures supported; prefixes of non-general factories |
| ST10/ST15, AS10/AS12 | Field writings at the end of the process cross the factories and remain visible to the appellant | Counter-example accepted by an intermediate version and then refused both courses; final contract is exact and transfer is made | P — normal end followed; agreement of suspension unknown retained explicitly |
| L1/L2, AS8/AS14, RT6 | The bridge returns a living task; unique destruction and closure | Inactive/drop, refusal to launch, two native tasks, probes, assertion runtime and UBSan on mutants | P — O0/O2 finished paths, no cancellation API or general proof |

Current batch: [parent transfers and local results relay async](cycles/ASYNC_RESULT_RELAYS_CYCLE.md).
Nine targeted methods go to O0/O2: 18 native executions and four
invalid programs refused in both stages. Six mutations are detected.
The final regression passes 130 methods. All processes are complete.
The two corrected defects (explicit form of assignment expected and priority)
The external destination) and the intermediate newspapers are kept.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| L7, V5, T1/T6, AS9/AS10/AS12 | New results go back to the scopes and states in the destination of the ancestor | Named/transferred tasks, chain of three states, branches and loops, C identity probes | P — independent results without proprietary/borrowed fields; sync and alternative open source factories |
| V4, B1/B2, D1, AS2/AS13 | Former allowance held while waiting; no promotion of a borrowed catch or pool | Direct loop replacements, independent local copy, four invalid neighbours, six mutations | P — Forms and sources represented; no general evidence |
| L1/L2, AS8/AS14 | Unique destruction of the state chain before closure of the destination | End and internal destruction of suspended unlaunched cases, empty slots and once closed source | P — O0/O2 finished probes under UBSan, no public cancellation |

Current Lot: [destination of new local results async](cycles/ASYNC_RESULT_STORAGE_CYCLE.md).
Fourteen methods go to O0/O2: 20 native executions and three programs
Six mutations detected (five on contracts)
The final regression is equal to 116
methods. Initial errors, a surviving mutation then covered and two
Inconclusive initial rankings are retained. All processes are completed.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| L7, V5, T1/T6, AS9/AS10/AS12 | The new result survives the recovery of the state without changing address | Hidden destination, copies, conditional/calculated returns, loops, two C probes | P — structures without covered proprietary/borrowed fields; relays, factories and transfers of parents |
| B1/B2, D1, AS2/AS13 | The copy releases the original but retains its pool; the loans remain protected | Three invalid neighbours, reference table, pool copy, transfer of source and table of catches | P — known root parameters; general open graphs |
| L1/L2, AS8/AS14, RT6 | Single clean-up in case of failure, normal end or internal abandonment of an unlaunched instance | Denied launch, inactive instance, suspended child probe, two native tasks and UBSan mutation | P — Finished scenarios O0/O2; no public cancellation or proof of all the arrangements |

Current Lot: [Contract Storage Requirements](cycles/STORAGE_REQUIREMENTS_CYCLE.md).
Ten targeted methods go to O0/O2: 12 native executions and nine programmes
In the case of the two stages, six mutations are detected.
108 and 97 methods pass before the last Select supplement; a selection
The initial errors, corrections and corrections are all the more important.
The report also provides details of the limitations.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, ST17/ST18, distinction T/A<T>, AS9/AS12 | Annotations impose local origin or pool; obligations pass through contracts | Annotated copy previously refused, helpers, factories, async relays, two possible sources, model of four combinations and invalid neighbours | P — root parameters of the structures covered; general projections not connected |
| L7, V5, B1/B2/B4 | Local results are built in the intended destination, without weakening the loans | Calculated returns of copies in two branches, drop before/after waiting, Select and conversion, six mutations | P — conservative stream; new result coming out of a still open state; UBSan finished, no general evidence |

Current batch: [local structures captured by child tasks](cycles/ASYNC_LOCAL_CAPTURES_CYCLE.md).
Thirteen methods go to O0/O2: 14 native executions and 11 programmes
In addition, six mutations are detected after the addition of the
a storage probe for two initial survivors.
passes 97 methods; a previous selection passes 67 before the guard of
back A<T>. Initial tests, harness error and corrected counting
All the processes mentioned are completed.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, V5, L7, AS2/AS9/AS12 | Local provenance passes through the catch and relays without moving or converting to A<T> | Sync/async callers, copies, parameter return, return/capture A<T> rejected, mutations | P — existing families of structures; bodies valid exclusively for local origin still refused in certain cases |
| AS8/AS10, L1/L2, ST17/ST18 | Independent local copies, sources closed by their scope, state capacity common to variants | Normal/suspend C probe, rejected launch, four re-uses of a slot between variants, slot step control | P — union C by function and finished scenarios UBSan O0/O2; no new evidence ASan/TSan |
| B1/B2/B4, D1, AS12 | The result borrowed protects the target after the child's end; the source survives the capture | Last use, mutation and drop refused neighbors, capture out of a block too short refused | P — graphs and general signatures remain open |

Current batch: [comes after the loops async](cycles/ASYNC_LOOP_PLACEMENT_CYCLE.md).
Seven targeted methods go to O0/O2: ten C executions and three programmes
5 new mutations and 8 of the
The extended regression passed 95 tests but was not detected.
its command fails on an incorrect module name; the thirteen tests of the module
The first tests were carried out separately, i.e. 108 separate tests were passed.
and the command error remains documented. All processes are completed.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| T3/T5/T6, V5, L7, AS9/AS12 | Potential producers after loop build in the storage of parent receiver | Five-point iteration zero, continuous/break, interlocked telescopes and loops, multi-way propagation model | P — families of local structures covered; unknown conservative origin, children's states still open |
| V4, L1/L2, B1/B2, D1 | Old living value during construction; new address kept; field pools and secure loans | C probe of successive versions, destruction counter, loan and source too short refused, thirteen mutations detected | P — UBSan O0/O2 finished tests; no general evidence or new ASan/TSan measure |

Current Lot: [parental placement of local structures async](cycles/ASYNC_LOCAL_PARENT_CYCLE.md).
Fourteen targeted methods go to O0/O2: 29 native executions and five
Invalid programmes refused at both courses. Eight final changes were made to the
The selection of 51 methods passes on the final code; regression
The new system of time-frames and the new system of time-frames is extended by 148 methods.
Initial failures are retained in the report. All processes are complete.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| T3/T5/T6, V5, L7, AS9/AS12 | Producer built in the parent's stack, without moving the result or holding the temporary storage child | Successive blocks, if/match, break/continue, existing/nominal receivers, identity probe and cursors | P — coming after buckle to be generalised ; transfer to open child tasks |
| ST17/ST18, D1/T11, B1/B2 | A local copy is independent of its original; the fields owned keep their pools | Owned/shared copies and method, child pool refused, loan/drop refused; copy/field mutations detected | P — families of cared structures, without promoting targets |
| V4, L1/L2/L6, AS8 | Old living value during evaluation, unique cleaning and recovery of free suffix | Direct/named/conditional replacement, three iteration model, two recipients, eight final mutations | P — UBSan O0/O2 finite probes, no public cancellation or general evidence |

Current batch: [local reception of structures from an async helper](cycles/ASYNC_LOCAL_STRUCT_HELPERS_CYCLE.md).
Eleven targeted methods are switched to O0/O2, five mutations are detected.
The extended regression passes 120 methods before the final T/A<T>; a
The selection of 50 methods and the target baseline pass on to the final code.
Inconclusive initial tests and their chronology are retained.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| L7, T1/T6, V5, ST17/ST18, AS9/AS12 | The local result is built in the data stack of the receiver; local copy is separate from that of a pool | Previously rejected program, bridge variants, proprietary/shared copies, storage probe and metadata | P — reception in the current scope; transfer to the parent and open states children |
| B1/B2/B4a, ST15, L1/L2/L6, AS8/AS9 | Loans respected through yield; values destroyed before the stack closes | Last use/drop allowed/refused, model of three loop prefixes, suspension and normal cleaning, closed mutation detected | P — families represented, UBSan O0/O2; no public cancellation |
| Draft 05, V4 T/A<T> Rules | A parameter, annotation or reassignment does not convert local T to A<T> | Fine-tuned counter-example and temporary audit, refusal of both substitutions, detected standard mutations | P — local origin in the current state; signatures of unconnected children states |

Current batch: [proprietary structures in synchronous calls from async](cycles/ASYNC_OWNED_STRUCT_SYNC_CALLS_CYCLE.md).
Fourteen targeted methods go to O0/O2, of which 23 are native executions and 15 are native executions.
invalid programs refused in both final O2 placements.
The regression of 114 methods is based on the final code.
detected after audit of two survivors due to initial targeting; newspapers
All processes cited are completed.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, ST1/ST7, D1/T11, AS12/AS13 | An auxiliary receives/replaces the graph explicitly, keeping the pools of descendants | Successive relays, eight placement model, single/double result and injected failures, historical contract questioning | P — finished graphs without borrowings; local creation and refund after replacement opened |
| B1/B2/B4/B4a, ST15, AS9 | A landholder loan reserves the bearer until last use, including through yield | Accepted reading and mutation, rejected concurrent consumption and reading, loan loss detected by mutation | P — Projections Int in the structures supported |
| L1/L2/L6, AS8, T6 | Same address at the rebate, single cleaning after consumption, failure or suspension of an argument | Three C probes, replacement then consumption, re-use, mutations Err/cleaning/destruction detected | P — UBSan O0/O2, finite probes; no public cancellation or general evidence |

Current Lot: [returns of proprietary structures](cycles/ASYNC_OWNED_STRUCT_RETURNS_CYCLE.md).
Twelve targeted methods succeed at O0/O2; final pass O0: 19 executions
The two courses have been rejected by the national authorities and 11 invalid programmes.
The study found that the number of new and five previous methods detected was increased by 86 before the survey.
the last relay supplement; 54 methods on the final code, plus the twelve
Final targeted tests. Timeline and limitations in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| D1/T11, ST1/ST7, AS5/AS12/AS13 | The result retains the pool of each field, distinct from the root | Model of eight provisions, factory contracts and helpers, source constraints; pool/contract mutations detected | P — finished graphs without borrowings of the types listed |
| T1/T6, B1/B2/B4 | Explicit transfer and field protection after remission | Direct/named wait, nested result, if/break, loan and then drop allowed/refused | P — open general signatures and constructions |
| AS8/AS9/AS10, L1/L2/L6 | Same address and destruction, before or after delivery | Two C probes, rejected launch, re-use, premature destruction mutation | P — UBSan, finished paths, no public cancellation |

Current Lot: [captures of proprietary structures](cycles/ASYNC_OWNED_STRUCT_CAPTURES_CYCLE.md).
Nine targeted methods succeed in O2: 20 native executions and 32 programmes
The two courses were rejected. Coverage of the nine methods in two passages.
Five mutations detected after adding a probe for a surviving mutation.
The initial regression returns an obsolete historical expectation, reproduced before
the lot then corrected; eleven control methods pass. Consolidated regression
O2 of 76 methods succeeds in 115.025 s on the final code. All processes
of this lot are completed; chronology and limits in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| D1/T11, AS5/AS13, ST1/ST7 | Each pool of the possessed graph survives the task and passes through the contracts | Counter-example of the factory, model of 24 arrangements/calls, interlocking symbolic paths, three source mutations | P — Graphs without loans and types listed |
| T1/T6, ST5/ST15, B1/B2/B4a | Explicit transfer, mutable access, loan completed before capture | Renaming, child async, Int/A fields<Int>, collection families, refusal of incompatible readings and post-consumer usage | P — no return of owner aggregate async |
| AS8/AS9/AS14, L1/L2/L6, RT8 | Addresses preserved, single child destruction before parent, retake of slots | Four states C, rejected launch, native thread, prepared argument; surviving mutation and detected | P — probes without competing root execution, UBSan only |

Lot courant : [retours directs d'allocations attendues](cycles/ASYNC_DIRECT_OWNED_RETURNS_CYCLE.md).
Six targeted methods are moved to O0 and O2; three mutations are detected.
The extended regression of 44 methods is now O2 on the final code.
process of the lot are completed; the chronology and limits are included in
the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, AS4/AS10/AS12, D1/T11 | Explicit return of A<T>, distinction with the Result of a handle, sustainable source | Four types, named/calculated tasks and branches, too short pool and incompatible types refused | P — general open aggregates |
| V5, L1/L2, AS8/AS14, SL1 | Same address after delivery, destruction, cleaning of a suspended child and prepared arguments | Identity/destruction probes, Select owner, return in next argument, re-use; mutations in destruction and forgetfulness of children detected | P — Finished paths, no public cancellation |

Current Lot: [Results owners produced by await](cycles/ASYNC_AWAITED_OWNED_RESULTS_CYCLE.md).
Nine targeted methods are being moved to O0: 110 native executions and 17 programmes
The cleaning probes in the two training courses (34 controls) were rejected.
The reduction of 96
methods and the final baseline of nine methods go to O2. Five mutations
the eight of the previous batch are detected; the two campaigns
are completed with code 0. Chronology and limitations in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS4/AS10/AS12, T1/T2/T6, U1 | Direct Expectation consumed once, explicit transfer, type and source retained | Synchronous and async arguments, returns and match, six forms of waiting, four charges, two levels of Result, rejected neighbors | P — open general signatures and containers |
| AS2/AS8/AS14, B4a, L1/L2/L6, SL1 | An argument already received remains possessed during the continuation; single cleaning if the call does not take place | Return to the following argument, ten suspension probes based on a finished model, losing Select, identity at re-use; mutations of preparations and cleaning detected | P — Finished model, no task cancellation started |

Current batch: [no charge and relay results](cycles/ASYNC_FAILURE_ONLY_RESULTS_CYCLE.md).
Nine targeted methods go to O0 (38 native executions, 12 rejected programmes)
in both courses), then twelve to O2 on the final code.
and interlocked are connected and tested. The selection of 149 methods passes
before these last connections; 42 methods pass after the direct forms.
Eight new mutations and five of the Select results are
The extended runtime regression passes 275 methods on the version
before the direct and interlocking expressions, covered separately.
The chronology of the versions, the first campaign and its limitations are
retained in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS4/AS12/AS16, RT6 | Proven non-terminal distinct from an unknown effect; only LaunchFailed can continue | Nine result families, direct expectation, recursive unknown, injected errors | P — General unrefined variants |
| B1/B2, D1/D3, U1 | A loadless envelope does not receive a fictitious pool; a possible charge keeps its source | Returns and transfers, five-issue finite model, no result pool, eight mutations detected | P — completed cases, detailed versions of the report |
| T1/T2/T11, L1/L2, RT7 | Explicit import/break; responsibility for bridge arguments and exports | Result Int/String/Vector, next argument waiting, return anticipated, re-employment, nested result | P — types listed, choice of handle in if, not all compositions |

Current Lot: [Select results and field effects](cycles/SELECT_RESULTS_CYCLE.md).
Twelve targeted methods go to O0 and O2; passage O0 has 27 executions
The programme is being implemented in the form of a programme of training for young people and 20 programmes rejected in both courses.
are detected after strengthening a termination oracle; eleven mutations
Eight contracts and eight suspensions remain detected.
The selection of 122 methods and the expanded async regression of 275 methods
The chronology and limitations are detailed in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| SL1, AS4/AS12/AS16, ST10/ST13 | Keep typed result set and fields modified at termination or suspension | Winning and losing, returning owner/view, model of nine orders, five mutations | P — general aggregates and open correlations |
| B1/B2/B4/B5, D1/D3, L1/L2 | Sources and targets still protected after waiting and drop of Select; unique cleaning | Int/String/Vector, shared/mutable views, re-use, drop/mutation refusal and local source | P — families represented, not all reference containers |
| RT6, U1 | LaunchFailed does not create a successful result; explicit use of results | Two injected failures, initial fields retained, owners and unused results rejected | P — ordinary handle expected, losing with unarbitrated handle |

Current Lot: [Select from source language](cycles/SELECT_SOURCE_CYCLE.md).
Twenty-four targeted methods are switched to O0 and in the baseline of mutations O2.
The final O0 pass runs 56 admitted programs and checks 49 programs
The two courses (98 checks) were rejected, including an independent model of the
12 new mutations, eight mutations of the
previous cleanups, eight of Select contracts and seven of the runtime are detected.
Regression selections pass 76, 95 and then 97 methods; the ratio is precise
the versions exercised and the coverage defects corrected during the batch.
The extended runtime regression passes 292 methods on the code before the
two last additions, then the selection of 97 methods exercises the final code.
The following sections describe the batch chronology
and limitations at the time of their passage.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| SL1, B1/B2/B4/B5, AS2/AS12 | Immediate capture, lost, still lasting loan result after drop | Reading/mutations/drops admitted or refused, two possible targets, loan and source changes | P — Conservative unions, general types open |
| SL1, T1/T2/T11, AS8/AS9 | Stable status, explicit transfers, same type of result and single expectation retained | Blocks, if, break, renames, calculated branches; corrected mutability counter example | P — conservatory external state junctions |
| SL1, L1/L2, S4/S5, AS10/AS14 | Unique destruction and reuse after cleaning of losers | Two owner pools, loop of eight re-employments, early exits, suspended construction, Select nested, model nine orders | P — orders under UBSan; no general evidence |
| SL1, ST10/ST13, AS4/AS12 | The writings of the loser are not restored by his destruction | Field modified before yield, result 9 then target 2, refusal of drop of this target | P — Prefixes, hands to arbitrate |
| SL1, AS4/AS12 | The poll order belongs to each selection alternative; a body never polluted does not require a summary | Accepted recursive counter-example, if/break with separate effects, detected border and flattening mutations | P — possible suspension contracts, without general correlation of the winners |
| SL1, B4/B5, AS10/AS12 | The finished catches of a certain winner are released; its results and losers remain protected | Previously refused program admitted, adjacent mutation refused, equivalent expectations per path, two mutations detected | P — families represented, general aggregate results still open |

Previous lot: [parsing and composition of Select contracts](cycles/SELECT_CONTRACTS_CYCLE.md).
Sixteen targeted methods go to O0/O2; model independent of 25 pairs
Select C branch and probe with two modified fields and eight re-uses.
Eight new mutations and the previous nineteen are detected.
Regression selections pass 74 and then 83 methods, according to the chronology
The catch verifier and the backend source remain open:
A complete Select program is not yet compileable.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| SL1, AS2/AS4/AS9/AS12, B4/B5 | Winner finished, losers suspended or not polluted; no fictitious restoration | Model 25 pairs, priority assertions, fields and results, probe C | P — conservative union; source not executable |
| SL1, T1/T2, I1/I6 | Explicit transfers, type of common result, catches retained in choices | Parsing, inactive construction, if/break/move, counter-example and eight mutations | P — symbolic contract; control of the single waiting to be connected |
| B1/B2, ST10/ST13, AS8–AS10 | Dependencies left by the loser persist after destruction | Prefixes via children, opaque helpers and nested selections; fields C after drop | P — retention of loans on the backend side still open, contracts to be arbitrated |

Current batch: [field effects at suspensions](cycles/SUSPENSION_EFFECTS_CYCLE.md).
The states of the yield and suspensions of direct children are summarized
15 targeted methods are being moved to
O0/O2; model independent of 64 sequences and eight mutations detected.
Contract regression passes 94 methods, then 52 after final custody
The extended runtime regression passes 292 methods.
The report shall specify the versions loaded and the perimeters of such executions;
the 11 previous changes in contracts remain detected.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| SL1, AS4/AS9/AS12, ST10/ST13, B4/B5 | A restoration after yield does not hide the target left by a loser | Separate states, three calls, saved catches, branches, loops, suspended RHS, 64 sequence model | P — Injected fields represented; composition Select source not connected |
| B1/B2, D1/D3, AS12 | Accurate complete expectation; unknown summary separate from an empty summary | Drop-in/refused neighbours, mutable fields, child diverging, unknown spread, eight mutations | P — Competitor effects of open general handles and aggregates |
| SL1, AS8–AS10 | Destroy a loser does not execute its continuation | C probe with generated callbacks, eight re-uses, field identity and value after destruction | P — harness C ; not yet a refusal of the Select source programme |

Current batch: [cleaning generated at suspensions](cycles/SUSPENDED_CLEANUP_CYCLE.md).
States have destruction paths per recovery point, with
prevalidation of children directly and without hidden waiting of the hands launched.
The explicitly marked async replacement of a construction is corrected.
Ten targeted methods are moving to O0/O2, with a model of 22 scenarios and eight
mutations detected; selection pools/regions/notifications passes 47 methods.
The field selection passes 42 methods. The complete async suite passes 274
methods on 275; his instrumentation anchor failure is corrected and the method
The chronology is detailed in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| SL1, AS8–AS10, L1/L2, S4/S5 | Destroy resources really alive at suspension, child before its targets | Prepared captures, three-level waiting, pools, branches, loops, rename, re-use | P — generated callbacks operated by harness C; Select source not connected |
| V4, B1/B2, D1 | New allowance assessed before destruction of old; loan retained during await | Construction and call explicitly marked, model 22 scenarios, neighbours refused | P — forms of replacement exercised; no general evidence |
| RT6/RT7, SL1 | Prevalidation without destruction of a tree bearing a waiting obligation | Handle in a child, normal recovery after internal refusal, result of join Ok/Err, eight mutations | P — arbitration of loser with always open handle |

Current batch: [Select internal mechanism](cycles/SELECT_RUNTIME_CYCLE.md).
Branches have separate wake-up tickets that notify their caller.
The scan respects the order of the eligible branches; losers are retained
Seven final methods are moved to O0/O2, including a model of
3,280 operations and a probe of generated frames. Seven mutations are detected.
Source syntax and general suspended cleanings are not yet
connected; a loser with a launched handle asks for arbitration.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| SL1, RT2/RT4, AS4 | Only the ready branches advance; priority writing and awakening of the appellant | 80-scenario model, wake-up during pollution, interlocked selection and end of handle | P — internal mechanism C ; auditor/source not connected |
| SL1, AS8–AS10, L1/L2 | Result extracted once, losers retained, slots reused after destruction | Four clean states, eight towers of generated frames and A<Int>, seven mutations | P — suspended callbacks provided to harness; general cleaning to be generated |
| RT2/RT4, AS9, D4 | Late notification without access to a free frame or wake-up of a replacement | Concurrent producer, 16 withdrawal/re-use rounds, 5,000 late notification pairs per turn | P — persistent entries until producers stop; no general evidence or TSan |

Current batch: [fields from async repos](cycles/ASYNC_FIELD_LOOPS_CYCLE.md).
The loops reanalyze their entries with the new field targets,
The initial identities and the
source of the covers are kept separately from UTF-8 views.
Eight targeted methods go to O0, forty to O2 with lots of fields,
then twenty on loop views and results. The four targeted mutations
The logs are detected; they are referenced in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST10/ST11, B1/B2/B5, AS9/AS12/AS16 | Company checked with all possible targets, backup of the old cell | while 0/1/3, continuous, children, interlocking loops, field exchanges, storage helpers | P — targets represented by injected carriers; general open exclusive correlations |
| L1/L2, D1/D3 | Preserved cleaning and protected sources until last use | 12 trace model, historical reset/re-use, four mutations detected | P — finished models; configuration and chronology in the report |


Current Lot: [replacement of mutable fields in states](cycles/MUTABLE_FIELD_COMPLETION_CYCLE.md).
Direct blinds and helpers transmit new field targets
`&mut Int` ; the reborrowing also retains the capacity of the field. An alternative
unchanged no longer creates a loan of the field on itself. The oracle of identity was
reinforced after a surviving mutation; both campaigns are recorded.
Ten final methods go to O0/O2; contract selection passes 58 methods
The five final mutations are detected.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST10/ST11/ST12, B1/B2/B4/B5, AS12/AS16 | New exclusive target and reserved field capacity until last use | Store/helper, mutation, shared/mutable result, child and fabricator, conditional field | P — Int injected; general open origins |
| D1/D3, AS13/AS14/AS15, RT6 | Inactive cleaning without blind, after-waiting or failure reservations | Model 8 cases (5 executed, 3 refused), injected failure, historical reset/re-employment, identity oracle | P — Conservative alternatives; results and changes in the report |


Current batch: [modified fields and borrowed results](cycles/BORROWED_FIELD_COMPLETION_CYCLE.md).
The termination sources distinguish the saved reference from the
The direct assignment of a shared field Int is
The source constraints are verified after stabilization of the
The historical boundaries of the previous lots are preserved.
Eleven targeted methods are moved to O0/O2; final selections of contracts and
The number of loans returned is 48 and 85 methods, respectively, to O2.
The first changes in the number of times the system is in place.
failure is kept and explained in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS12/AS16, B4/B5, ST10/ST13 | Separate effects and results, catches saved before publication | Old/new field, children, factory and public handle; recorded program executed | P — Int shared, Int borrowed result; general open aggregates |
| B1/B2, D1/D3, AS13/AS15 | Target retained without prolonging any other allowance unnecessarily | Model 8 cases (2 executed, 6 rejected), historical drop/reset, rejected mutation, five mutations detected | P — finite cases, local diagnosis still general ; chronology of passes in the report |


Current batch: [retarded effects of synchronous mills](cycles/FACTORY_FIELD_EFFECTS_CYCLE.md).
Manufacturers now retain changes to shared fields Int
The wait publishes them through the
relays and async/native bridges; inactive destruction does not apply them.
Previous reports retain their historical boundaries.
Thirteen targeted methods go to O0; selection O2 passes 83 methods,
then the two final additions go separately to O2. The regression of the contracts
77 methods. Eight targeted mutations are detected; chronology and limitations
in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS2/AS5/AS16, B4/B5, ST10/ST13 | Separate termination creation; opaque factory contract | Relays, saved fields, branches, loop, waiting helper, async and native bridge | P — Injected shared fields; general open types |
| AS12/AS13/AS14, B1/B2, D1/D3, RT6/RT7 | Sustainable target and still protected after waiting, no effects if inactive | Model 8 cases (5 executed, 3 refused), injected failure, historical reset, re-use; eight mutations detected | P — conservative union, finite models; final results in the report |


Current batch: [synchronous contracts of changing handle](cycles/SYNC_HANDLE_FIELD_EFFECTS_CYCLE.md).
Contracts retain expected entries and return with their effects
The opaque test does not have any
synchronous body. Shortcut of scalar results was removed for the
task parameters; returns of transferred tables are connected to this
The previous reports indicate their historical boundaries.
Seven targeted methods go to O0, 67 to O2 with the handle contracts, and
96 in the modular tables/calls selection. Six targeted mutations are
The log and chronology of the other selections are included in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| B4/B5, ST10/ST13, AS12 | Opaque waiting publishes dependencies and transfer retains delayed effects | Three calls, no synchronous bodies, branches and loop, two handles | P — task input/handles; new open amending factories |
| B1/B2, D1/D3, AS14, RT6/RT7 | Inactive without writing, pool and targets still protected after waiting | Model 8 cases (5 executed, 3 rejected), historical reset, re-use, injected failure | P — conservative road assemblies, full open correlation |

Common Lot: [field modifications through child tasks](cycles/ASYNC_CHILD_FIELD_EFFECTS_CYCLE.md).
Direct and handlable expectations publish the dependencies of children in the
The parent; the inactive statements do not apply any effect.
instructions have been Void, previously ignored, are fixed with a
The previous reports below
keep their historical limits; this lot lifts their general refusal of children.
Eleven targeted methods go to O0; fifty-two to O2 with contracts and
the previous batch. The final regression selection passes 48 methods, and the
Nine targeted mutations are detected. Previous selection of 75 methods
and its chronology are detailed in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST10/ST13, B4/B5, AS4/AS12 | The effects follow catches through waiting, choosing and transferring | Three relays, twelve transfer/waiting variants, old borrowing and field exchanges | P — shared fields Int and scalar/Void results; open synchronous relays |
| B1/B2, D1, AS13/AS14, RT6 | Inactive without effect; sustainable targets after termination or failure of launch | Model 12 cases (7 executed, 5 refused), rejected injected, child target and Void counter example | P — conservative union success/failure, no general evidence of competition |

Current Lot: [application of field changes after join](cycles/ASYNC_FIELD_APPLICATION_CYCLE.md).
Field blinds `&Int` via synchronous helpers in async/native states
are executable for the injected carriers and targets described in the report.
Sixteen targeted methods go to O0; forty-one with contracts to O2.
The final regression passes 112 methods. Eight mutations are detected and one
survival, offset by subsequent control in the chosen scenario.
The counter example of loss of effects per enum match is corrected.
distinguishes the surviving mutation from the destination control, regressions
The boundaries of older lots
below describe their condition on their date; this lot removes part of their refusal.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST10/ST13, B4/B5, AS12/AS13 | The join publishes the dependencies of the task; creation inactive without effect | Native, model 8 cases, choice of handle, match enum/buildin, loop/break/continue | P — Injected shared fields; children and synchronous relays open |
| B1/B2, ST10/ST13 | Initial detached target distinct from the current target; junction retains all alternatives | Helpers storing loans, conditional blinds, drop/mutation/historical reset | P — recurrence of blinds through open backedge |
| D1/D3, AS14, RT6/RT8 | Launch failure and inactive destruction without writing or double cleaning | Injected launch refusal, re-use of slot, native method and block | P — conservative union success/failure; no general proof multithread |

Step in progress: [borrowed results and termination effects](cycles/ASYNC_COMPLETION_RESULTS_CYCLE.md).
The contracts of the expected children together retain the modified fields and
The independent model of sixteen scenarios discovered and
corrects a loss of modification through the holder's aliases.
Twenty-five methods are moved to O0/O2: twenty-three analysis, two C neighbours executed.
Eleven mutations are detected and a regression selection passes 73 methods;
the chronology of the tested versions is specified in the report.
Replacement of external fields in an async program remains refused.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST10/ST13, B4/B5, AS12/AS13 | Effects and results share saved catches, without confusing old and new target | Model 16 cases, relays, hand selection, recorded counter example | P — Contracts; application to open real appellants |
| ST11/ST12, B1/B2 | A mutable result keeps the reservation of its holder | Indirect contract and target/capacity changes | P — types of scalar results taken from treated |
| S5, AS2/AS14, RT6 | No effect on creation or continuation after divergence; launch refused without payload | 125-case model regression, direct wait and handle envelope | P — general correlation Ok/Err not connected |

Last batch: [descriptors of the borrowed funds](cycles/CAPTURED_CELL_DESCRIPTORS_CYCLE.md).
Cell requirements go through tasks and synchronous factories to
stabilité, indépendamment de leur ordre de déclaration. Vingt-sept méthodes
Targeted O0/O2 pass, including thirteen new; model of eight scenarios and five
Inline targets and effects
Post-waiting field replacements remain open.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| B4, ST8/ST13, AS2/AS12/AS13 | A capture keeps the descriptor of the allocation stored in a field | Five relays/two orders, synchronous factories, identity, bounded recursion | P — Int Cell; unconnected inline targets |
| B1/B2, ST11/ST12, D1/D3 | Derivatives and mutable capacity remain protected until last use | Model eight drop/reset/join cases, mutable return, local carrier refused | P — tested forms; historical reset only |
| L1/L2, RT6/RT8 | A borrowed catch does not destroy its target | Inactive/drop, rejected launch, native thread and re-use slot | P — UBSan, no general evidence of competition |

Last batch: [borrows stored by bridges](cycles/CELL_REFERENCE_BRIDGES_CYCLE.md).
Fourteen targeted methods go to O0/O2, with an independent model of sixteen
The descriptor is a model of the type of activity that is the most common in the world.
actual is kept for the allocations and fields followed.
raw and the spread of external replacements after join remain open.
The final regression of functions/divergence passes 45 methods; the others
The report includes the selections and their chronology.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| B4, ST8/ST10–ST13, AS12/AS13 | Temporary blinds retain descriptor and targets even without final effect | Relayed contracts, conditional choices, method, identity and bridge C | P — known Cell targets; raw captured pointers and open post-expectancy effects |
| B1/B2, D1/D3, L1/L2, RT6 | Last use, single cleaning and re-use without pending target | Model 16 scenarios, pool capacity one, refusal of launch and native thread | P — finished scenarios, not general multithread proof |
| S5, B4 | The divergence retains the representation requirements and does not produce a return C | Two different variants compiled, mutations and regressions | P — Differing bodies compiled but not executed |

Step in progress: [deferred contracts for async fields](cycles/ASYNC_STRUCTURE_EFFECTS_CYCLE.md).
Inference retains the replaced targets through synchronous auxiliaries
Sixteen methods of contracts and one synchronous neighbour
executed at O0/O2, independent model of 125 scenarios and seven mutations detected.
The connection to the states, to the bridge
C and to the appellant after join remains open: the backend's refusal is retained.
An unsolved analysis is distinct from an empty contract.
312 methods and synchronous of 56 methods pass, as well as the 17 methods
of public hands after the last corrective. Their chronology and their
The report contains limitations; these selections overlap.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST10, B4, ST13 | Contracts present new targets since saved arguments | Auxiliaries without body, detached origins, alias, order and two exchanged fields | P — inference of effects; async replacement still not executable |
| AS2/AS4/AS14, RT6 | Create does not run; wait applies effects; launch refused retains old status | 125 scenario model, interlocked children, if/loop choice, inactive destruction | P — contracts, no proof of application to the runtime |
| S5, AS12/AS13 | No invented continuation or lost effect at an unresolved border | Divergence, while/continue/break, incomplete status and deployments | P — recursion, general aggregates, child-supplied results and relays via unconnected hand helper |

Last batch: [concrete handle relays](cycles/CONCRETE_HANDLE_RELAYS_CYCLE.md).
The input descriptor and the sources of the results are retained when the
public conversion. Orderly constraints replace historical refusal
The other tasks remain protected, even without any future join.
Fourteen targeted methods O0/O2 plus two complements, model of 32 cases,
The results of the study were presented in the following sections:
The report distinguishes between the tested versions, the errors of the
fixtures and final supplements; he does not claim a grouped passage
16 methods without failure.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS12/AS13, RT5, ST11–ST14 | The result keeps its target and the original ability after conversion | Executing cross-example, inline/indirect/unmarked fields, Int/u8 | P — signatures exercised |
| B1/B2, D1/D3, RT7 | Protected captures up to join, targets up to last use | 32-case independent model, three forms of capture, refusal to launch | P — Finished scenarios |
| B4d, PR1 | Reading/join/reset order propagated in contracts | Callers without bodies, sources of fields and boxes, other active task, divergent paths | P — historical profile only; mutation masked by redundant control |

Last batch: [results of handls projected in the fields](cycles/SYNC_HANDLE_FIELDS_CYCLE.md).
Nine targeted methods O0/O2, independent model of 36 scenarios and regression
The final extended regression is carried out by 107 O2 methods.
Five mutations detected, one survivor explained.
intermediate failures and distinguish the chronology of passages.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS12, ST8/ST11–ST14, B1/B2/B5 | Captures released after waiting, paths and capacity of result retained | 36 scenarios, inline/indirect/unmarked fields, relays and nested fields | P — Fields used; relays Concrete execution covered by the following lot |
| RT5, D1/D3 | A handle capacity does not become two loans; independent loans protected | Two double counting errors detected, second capture and premature drop refused | P — graphs tested, not general proof |
| B4d, PR1 | Sources of the result go through contracts | Relationships required, calling without body, disjunct pool admitted and target refused | P — historical reset only; change of concrete resolution surviving |


Last batch: [synchronous handle fabric in states](cycles/SYNC_HANDLE_BRIDGES_CYCLE.md).
Sixteen successful targeted methods at O0/O2; 32-case independent model; six
O2 regressions of 73, 24 and 19 methods, with their chronology
The report states that the waiting for a direct factory and the reception is
The field projections of the result remain open.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS12, B1/B2/B5, D1/D3 | Catches required until waiting; only targets of the result after | Model 32 cases, two relays, views and references Int, mutations of both groups | P — direct parameters, no field projections |
| RT4/RT5/RT8, AS8 | Suspended waiting for a handle produced in sync code | Three launches, direct wait/named, seven async levels and twelve repeats of the program | P — finished cases, not general proof of fairness |
| RT6/RT7, L1/L2 | Resources transferred once and cleaning before error/re-use | Four-state contract C, refusal injection, capacity one, secondment/error/consumption mutations | P — no new ASan/TSan proof |
| U1, RT5/RT7 | Explicit result and single expectation, no abandonment | Drop, early exit, double wait and abandoned result refused; 19 usage/wait regressions | P — tested signatures |


Previous batch: [viewed synchronous auxiliaries in states](cycles/SYNC_VIEW_BRIDGES_CYCLE.md).
Twelve methods covered by eleven combined passages and a native supplement,
at O0/O2 under UBSan; 32-scenario independent model, five mutations
Increased regression: 99 O2 methods, before the last U1 control
The public handling plant known as the "handle factory" is covered by the final targeted passages and 23 regression methods U1/UTF-8.
from a state remains open; the types of direct views below are connected.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| B1/B2/B4/B5, AS2/AS8 | Prepared loans protected during the following arguments and suspensions | Observable order, mutation of an argument refused, suspended index, mutation detected | P — direct views and textual projections |
| AS12, D1/D3, RT5 | Result keeps its targets, releases unlinked catches after join | Two relays, model 32 cases, subviews and native thread; loan/contract transfers | P — signatures of views listed in the report |
| U1 | Explicitly used fallible result | Call abandoned, unused link and `_` refused; drop allowed; mutation detected | P — auxiliaire retournant Result<&str,SliceError> |
| L1/L2, AS10 | Early return of argument cleans once and prevents call | Trace destroy then reclaim and absence of the auxiliary marker | P — Local String scenario |


Previous lot: [public contracts of hands with result seen](cycles/PUBLIC_VIEW_HANDLES_CYCLE.md).
Synchronous signatures for &str, &u8, &[Int/u8], &mut [Int/u8] and
Result<&str,SliceError>. Ten successful O0/O2 methods, independent model of
32 scenarios, calling opaque and injected launch failures. Twelve methods
pre-existing async and 132 extended regression methods are increasing to O2.
Four mutations detected and one survivor
(exclusive capacity also retained in the descriptor of the loan).
The report distinguishes between targeted passages, regressions and limits.
The old public view statements are replaced by the old open view
for these synchronous forms only.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS12, RT5, MT5/MT6, D1/D3 | Result keeps its targets; temporary catches released after waiting | Model 32 cases, two frames, relay, calling without body | P — listed synchronous signatures, general aggregates open |
| B1/B2/B5, TX4/TX5/TX12 | Modes and origins of views after join | Thong, tables u8, Int/u8 tranches, readily, re-borrowing and latest uses | P — mutation of surviving capacity, no general evidence |
| B4d, PR1 | Sources distinctes si reset historique avant lecture | Two relays plus concrete/public conversion, controlled obligation and detected transfer | P — profil historique uniquement |
| RT6, L1/L2 | Launch failed to clean up catches before result | Failure Injection, Traces and Rescue Results | P — roads under UBSan O0/O2 |


Arbitrage pending: [capture async of a handle already launched](ASYNC_HANDLE_CAPTURE_DECISION.md).
AS14 destroys inactive body; RT6 destroys its catches in case
RT7 prohibits the destruction or implicitly waiting of launch failure
the captured handle. The two minimum programs and the current refusal of the backend
no new normative behaviour is chosen before response.

Independent batch: [expressions calculated in set](cycles/SET_EXPRESSIONS_CYCLE.md).
Nine O0/O2 targeted methods, independent model of 36 Int mutations and three
Injected errors detected. Calls in the HHR contribute to contracts;
the target is reverified before writing. The initial regression of 150 methods
finds six old U1 fixtures: the same three failures of assertions and
12 errors are reproduced with the compiler's sources before this batch.
Scenarios are corrected by explicitly reading the old value, without
remove their claims of destruction, identity or refusal.
The second pass succeeds 149 methods out of 150; the last negative scenario
is corrected to use its new receiver.
Two modified modules then pass. Complete timeline in the report.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| V4/B4a | Full Int calculation before writing, identity unchanged | Ordered calls, scalar copy, table, match, address and re-employment | P — Int expressions already supported |
| B1/B2/B3, D1 | Living and accessible after HHR | Drop, transfer, future reading and read-only refused; last use allowed | P — roads used, no general evidence |
| B4c/B4e, L6, PR1 | Effects of RHS propagated in contracts | Two relays, disjointed historical reset admitted/dangling refused; mutation of effect detected | P — reset only by historical option |

Last batch: [handles with borrowed result](cycles/PUBLIC_BORROWED_HANDLES_CYCLE.md).
Public synchronous contracts for &Int, &mut Int and &mut u8; active captures
separated from the results targets, relays and opaque callers, projections of
10 methods go to O0/O2, independent model of
32 scenarios; five mutations detected, one survivor in the final campaign.
97 O2 methods successfully reduced before the last bytes complements,
covered by final targeted tests, 122 table/byte/vector methods
and 36 methods of public contracts to O2. Shared inline projections
then pass their O0/O2 target supplement.
Chronology, initial logs and limitations in the report.
historical charges borrowed entirely open are replaced for
These three forms only; the Async signatures remain open.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| AS12/AS13, RT5, MT5, D1 | Targets of the result kept after join, other catches released | Two relays, waiting auxiliary, two branches, model 32 scenarios, calling without bodies | P — three synchronous signatures |
| B1/B2/B5, ST11–ST14, MT3 | Original mutable capacity retained, distinguished detachable target of the carrier | Premature rejected drop/access, last use, stored fields, direct capture; capacity mutation detected | P — graphs used, not all aggregates |
| B4a, VE1/VE3, E1, AS2 | Box Int/u8 stable and bounded, reserved during index evaluation | Tables/vectors, helper byte, readonly, growth and transfer prohibited, overtaking runtime | P — source mutation in surviving constraints; backend controls retained |
| L1/L2, RT6, P8 | Cleaning and re-use, start error after task completion | Traces, re-used pools, refusal to launch, O0/O2 UBSan | P — no new ASan/TSan or formal evidence |

Previous batch: [handles with allocated result](cycles/PUBLIC_OWNED_HANDLES_CYCLE.md).
Int, String and Vector "Int/u8" synchronous contracts,
results allocated to fallible, sources of separate catches of sources of
result, connections and opaque calls. Nine successful O2 methods; model
In addition, the project will be able to identify the following factors:
104 successful O2 methods; the nine targeted methods also go to O0.

| Rules | Invariant / interactions | Evidence of the stage | Statut / limites |
| --- | --- | --- | --- |
| RT5 / MT5 / AS13 / D1 / D3 | Pools of the result survive after join, the other catches are released | Two relays, waiting auxiliary, backup pool, opaque callers, 32-scenario model | P — four contents allocated, sync signatures |
| RT6 / T6 / U1 | Separate result and error, explicit consumption and single cleaning | Two levels of error, rejected launch, addresses before/after transfer and re-use, refusal of wrong A<T> | P — excavated envelopes, not all aggregates |

Previous lot: [public contracts of the handlers](cycles/PUBLIC_HANDLE_CONTRACTS_CYCLE.md).
Synchronous Scalar Load Handle or Fixed Table Parameters and Returns
Int/u8, catches and sources retained without body available to the caller.
17 targeted methods O0/O2, regression of 54 methods and seven mutations detected.
The permission model covers 36 scenarios. The junctions of separate frames
by if/loop/match pass five targeted methods and four mutations; passes
Final commons: 22 O0 and 60 O2 methods. 18 loop test results
pass; additional historical selection revealed fixings
without explicit U1, corrected with maintained assertions: 71 methods
successful at the recovery.
charges borrowed/owners remain open. Detail and chronology in the report.

| Rules | Invariant / interactions | Evidence of the stage | Statut / limites |
| --- | --- | --- | --- |
| RT5 / MT5 / brouillon 04 | Public type independent of the frame, contract without body | Fabrics, relays, two frames, shapes of paintings and bad types refused | P — synchronous signatures, supported charges |
| AS2 / AS13 / MT3 / RT7 | Live-to-waiting captures and pools, transferable obligation | Model 36; opaque callers; denied drop and early access; mutations | P — tested catches, general graphs open |
| D1 / RT6 / E1 | Single cleaning, detached table, storage reuse | Refusal to launch, drop after waiting, re-use of slots, O0/O2 UBSan | P — no general evidence or TSan |
| D3 / T6 / S5 / MT5 | Handluffs: same load, union of catches and pools | if, loop/continue, three matches; 22 performances C, opaque contracts, four mutations | P — scalar/table loads supported; async bodies opened |

Previous batch : [public type of handles](cycles/PUBLIC_HANDLE_TYPES_CYCLE.md).
Annotations `runtime::Handle<T>` sync/async, calculated transfers and variants
Next step: 50 successful methods; three mutations
The generic signatures remain open, with a counter example
The final target logs O0/O2 are indicated in the report.
Seven methods go to O0/O2: 29 C executions and 35 invalid variants
The two entrances are checked by full passage.

| Rules | Invariant / interactions | Evidence of the stage | Statut / limites |
| --- | --- | --- | --- |
| Brouillon 04 / RT5 | The public type describes the result, not the frame | Six charges in two contexts; two different functions producing Int; bad types refused | P — Local annotations; generic open signatures |
| AS2 / AS13 / MT3 / RT7 | L'annotation n'efface ni capture, ni source, ni attente | Drop and premature access denied, borrowed/allocated results, re-use; erasure mutation detected | P — families exercised, not all aggregates |
| D1 / RT4 / RT8 | Transfers and launches keep their behaviour | Bloc, if, boucle, rename, spawn/blocking/thread, essais C | P — junctions between different definitions still open |

Previous batch: [notifications of expectations async](cycles/AWAIT_NOTIFICATIONS_CYCLE.md).
RT2/AS4: parent registration, ticket transmission in direct expectations,
notification by co-operative, dedicated and native workers. Targeted tests O0/O2,
200 orders, 200 re-employments on two workers and 20 generated chains.
Seven specific mutations detected, six in the queue and six native border.
The extended regressions pass: 275 async and 311 native methods.
They precede the last entry association patch and the test
The report is for the chronology.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| RT2 / AS4 | Sleeping registered waiting, wake up the whole chain | Program generated with local table and loan, poll meters, 20 re-uses | P — one consumer per handle; Select open |
| RT2 / AS8 / MT7 | No alarm clock lost between registration, poll and end | Four orders, two ends, 200 competing re-runs; mutations | P — orders exercised, no TSan or formal evidence |
| RT2 / AS14 | End visible after notification, single release | Forced intermediate publication, release meters, obsolete tickets | P — Sustainable context required; loop of the dedicated runner retained |

Previous batch: [ready wire and re-used workers](cycles/READY_QUEUE_CYCLE.md).
RT2–RT4/RT8: inputs generated outside frames, generation tickets,
file FIFO, two re-used default workers, separate blocking and native.
Nine targeted methods go to O0; baseline from five methods to O2 and six
File mutations detected. Independent model: 40 scenarios, 5,440 operations.
Initial native regression ends with 308 methods and 16 failures
d) pthread injections that are not suitable for the reuse of workers.
The results are expected to be maintained and injections migrated to the
logical submissions. Async campaign ends with 275 methods: 273 successes
and two old injections loaded before correction, successfully re-executed
separately. The two methods outside the async module that had failed are
The original newspapers have been successfully re-executed.
A sixth method forces the migration of a generated frame carrying a loan
The report is based on a local and child-friendly approach, which is now O0/O2.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| RT2 / AS8–AS9 | A planned entry, grouped alarms, FIFO and reused workers | Model of the system, poll meters, eight tasks and three workers, six mutations | P — no evidence of OS scheduling; expectations generated in Yield |
| RT2 / AS7 / MT7 | Former ticket without access to a free/reused frame | Generations, twenty re-employments, producer after free ; inputs generated by location | P — producers must stop before their context is destroyed |
| RT4–RT6 / AS14 | Refusal to launch after cleaning; reusable pool | Refusal of the second worker and condition, three successive tasks and traces | P — selected OS errors, not all system failures |
| RT4 / RT8 | Independent native block, blocking operations outside cooperative workers | Native tests and spawn_blocking; mutations of the native border | P — Public replacement of the still open scheduler |

Previous batch: [runtime awakenings]](cycles/TASK_WAKES_CYCLE.md).
RT2 : internal distinction Pending/Yield, permission to pollle coalescée,
conservation of alarms during the body and exclusion of competing polluters.
Four methods go to O0/O2; model independent of 2,401 sequences
(9,604 transitions), 20 competition/migration trials and two hundred
Races alarm/publication. Six mutations of the protocol are detected.
Native regression passes: 302 methods, 312.219 s. The initial async campaign
ends with 278 methods, 276 successes and two expectations of corrected tests
then re-executed; his failures remain visible in the report. RT2 remains
partial: neither file the scheduler nor public wake-up entries in this lot.

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| RT2 / AS8–AS9 | One active body; alarms during a conservatory and regrouped poll | `test_task_wakes.py`, finished model, races and six mutations | P — Internal C protocol; open public lines, equity and API |
| RT2 / AS4 / MT8 | Resumed on another thread with a stable address | Twenty essays with first thread still alive | P — migration at runtime level; no mutex guards covered |
| RT4–RT6 / AS14 | Result extracted before release, single cleaning | Launch joinable/detached after Pending; native border changes | P — life of wake-up pointers provided by the harness; future unmanaged entries |
| V4 / AS12 | An immutable reference link can write its target | V4 corrected historical fixture, failure replicated with the old runtime; program executed | P — no change in norms or generalisation of reassignments |

Previous lot : [stocking of reborrowing fields](cycles/STORED_FIELD_REBORROWS_CYCLE.md).
ST4/ST8/ST11–ST14, B1–B5, D1 and AS12/AS13: representation of the true
allowance retained by indirect references, ancestry reserved in
the carriers and the results. Fourteen performances C (including one launch refused),
28 programs refused both entries; six targeted mutations detected.
Independent model: sixteen combinations, ten executions and six refusals.
Contract Regression: 35 successful methods; historical fields:
75 successes and a U1 fixture corrected and re-executed separately.
The Counter-Example `open-struct-field-reborrow-stored-shared.crust` is corrected.
The helpers' final campaign also detects its six mistakes after adding the
Inline neighbour; a previous mutation of field returns remains surviving.
Extended native regression: 297 successful methods in 226,611 s.
The report is based on the following sections:

| Rules | Invariant / interactions | Proof of batch | Statut / limites |
| --- | --- | --- | --- |
| ST4/ST8/B5 | The field stored and returned keeps its target and its type | Shared/mutable construction, helper, method, manufacture, copy; representational and original mutations | P — references to Int allocations; general open inline storage |
| ST11/ST12/D1/AS13 | The original capacity survives all its borrowings | Historical drop/reset, block output, async/native result, d-enums chains; model 16 cases | P — finished models; updating of open async fields |
| ST13/ST14/B1/B2/AS12 | Scope of the shared carrier distinct from the original mutable capacity | Join, handle received, mixed results, independent mutation; descent mutation now detected | P — graphs used, not all aggregates |
| L1/L2/L6/P8/AS14 | Single cleaning and reuse after last use | Trace View → Writer → Int, EAGAIN injected, original pool capacity a re-used | P — UBSan, no ASan/TSan result added |

Previous batch: [shared returns detached](cycles/ASYNC_DETACHED_FIELD_RETURNS_CYCLE.md).
ST13, ST11/ST12/ST14, B1–B5, D1, AS12/AS13 and MT3: the external target
survives the destruction of the bearer; the mutable field retains its capacity.
Partial coverage: 27 C executions (including a rejected launch injected),
32 programmes refused to enter both, model independent of 12 cases
(eight executions/four refusals) Four mutations detected, two survivors
Final target O0: 13 successful methods;
near regression O2: 61 successful methods before the last additions of tests.
The extended native regression ended with 291 successful methods in 239,123 s.
The final additions of descent and traces of destruction also have their own
targeted passages; see report for exact timeline.
Storage of a reborrowable field loan, then wrongly refused, is treated
in the next batch above.

| Rules | Invariant and interactions | Evidence of the detached lot | Statut / limites |
| --- | --- | --- | --- |
| ST13/B5/AS12 | Shared result keeps its external target without holding the holder | Direct return, alias, helper, method, child, relay after join; closed/re-employed porter pool | P — champs &Int ; autres graphes ouverts |
| ST11/ST12/ST14/B1/B2 | Direct field and mutable capacity keep their reservations | Mixed results, premature destruction and transfer denied, valid mutable shared reborrowing | P — conservative union of paths; transfer of previous surviving capacity |
| B3/D1/AS13/MT3 | Sustainable forefathers and targets up to last use | Historical drop/reset, mutable ancestor, local block result refused; model 12 cases | P — two mutations in the lot survive; storage of a reborrowing of open field |
| L1/L2/L6/P8/AS14 | Destruction and recovery once; reuse of the slot | Accurate trace, capacity one, injection launch error | P — chemins finis sous UBSan |

Previous lot: [mixed contracts sync/async](cycles/ASYNC_HELPER_RESULT_CONTRACTS_CYCLE.md).
B4c/B4e, ST8/ST12/ST14, AS12/AS13 and MT3: summaries of available helpers
during the async inference, paths preserved by the handle factories
and functions that await a received handle. Partial coverage: nine
C and 15 programs refused both entries; model of 24 cases
(18 executions/six refusals); six mutations detected. Regression of 67 methods
with a pre-existing U1 fixture corrected and then re-executed separately, and
56 successful field methods. Limits, profiles and logs fail
The report does not contain any general safety statement.
The native selection of 278 methods was also successfully completed; it was
before the last addition on the handle parameter, covered by the
final targeted passages.

Next addition: [returns from async fields](cycles/ASYNC_FIELD_REFERENCE_RETURNS_CYCLE.md).
Final update of the batch: contracts for synchronous relays after join and
connected ancestry; baseline of 23 C executions and 58 rejected programs
in two courses; seven mutations detected, one survivor.
269 methods and then final complement of 42 successful methods (perimeters and
No general evidence of safety.
ST8/ST12/ST14, AS12, B1/B2 and MT3: contracts restore roads
Direct and Int borrowing, including after relays, branches and joins.
Accessible disjunct fields, carrier and protected target until last use.
Partial coverage: independent model of 24 cases (18 executions/six refusals),
21 executions and 50 invalid programmes monitored in two courses,
five mutations detected and one survivor (redundant transitive protection)
in cases exercised; general equivalence not established).
recapture adds one execution and four refusals. ST13 detached and graphs more
The report for the errors retained,
configurations and extended regression.
The synchronous relay of a join whose child async returns a result of
synchronous helper remains refused; counter-example retained in
`validation/open-async-helper-result-sync-contract.crust`.

Previous addition: [reborrowing async fields](cycles/ASYNC_FIELD_REBORROWS_CYCLE.md).
ST6–ST9/ST11–ST12, B1/B2/B4a and AS12/AS13: partial road cover
field, durable aliases, prepared arguments and auxiliary results
V4: mutation via an unchangeable &mut link; its
Reassignment remains denied. 32-case independent model, final baseline
of 21 C executions and 29 programmes rejected in two courses, seven transfers
The report for the report for the first time, which is based on the results of the study, is based on the results of the study.
the timeline of the last change. The return projected from a function
Async itself and changing field dependencies remain open.

Normative reference: [LANGUAGE_RULES.md](LANGUAGE_RULES.md). Inventory of the
November 2, 2026, drawn up after reading all the rules.
The following are from this specification; no new normative statement is
introduced here. A rule amendment requires a review of its dependencies.

Async supplement: AS1–AS16, RT1–RT8, MT1–MT9, SL1 and PR1 are inventoried
at the end of the document. Their lines specify the current partial coverage; the historical inventory
of the 67 identifiers above does not include this extension.
The historical situation concerning A5/reset still describes the old behaviour: they
do not check the removal of API decided by PR1.

This matrix distinguishes **P** (partial coverage by executable tests),
**A** (design/specification review, without dedicated executable evidence) and
**N** (unaudited, unaudited, intended behaviour) No rule is declared
The result of the cycle of the pool types is formally proven or fully verified.
in [POOL_REQUIREMENTS_VALIDATION.md](POOL_REQUIREMENTS_VALIDATION.md). The field cycle
&Int is detailed in [REFERENCE_FIELDS.md](REFERENCE_FIELDS.md).

Each line inherits the profile indicated: it gives the examples admitted/refused,
Invariants, common preconditions, runtime assertions, models,
The interaction column adds the own dependencies
The line restrictions prevail over the profile.
referenced is not an exhaustive coverage of each variant of the rule.

Preconditions for historical synchronous profiles: functions without recursion,
Int32 and field enums Int/&Int/&mut Int, without user destroyer,
source and sources not available. `allocator()` and
`stack(...)` remain explicit compatibility backends, without fallback
The new cases of this cycle favour pools.

| Rule | Expected behaviour / protected invariant | Profil | Interactions | Status and specific limit |
| --- | --- | --- | --- | --- |
| I1 | Explicit intent of memory operations | INTENT | I2,T1,B4,L6 | P — sources and operations covered only |
| I2 | Implicit local storage and pool named for pool allocations | INTENT,POOL | V1,A1,P8 | P — typified and literal pool of local structures exercised. Mutation after last borrowing, drop and owner cross-pool field tested at O0/O2. Placement of local transfers, other local values and removal of historical syntaxes to be integrated. [Storage circle](cycles/STORAGE_DESIGN_CYCLE.md) |
| I3 | Calculation of storage without reordering effects | STORAGE | B4a,L3,P3 | P — general advance investment not implemented |
| I4 | Default locally reported values | FUTURE | P2 | N — local configuration not defined |
| I5 | Rust-inspired minimum core, Crust priority rules | DESIGN | I1,B4 | A — design choice, not equivalence to Rust |
| S1 | Blocks bounded by accolades | INTENT | S4,T4 | P — grammaire actuelle seulement |
| S2 | Synchronous execution | DESIGN | S3,S4 | A — threads and async outside perimeter |
| S3 | Child activation of the calling scope | CALLS | S5,T3,T4 | P — non-recursive calls; delayed recursion |
| S4 | Scope specific to branches and iterations | FLOW,LOOP_CARRY | S5,T9,L2 | P — loop/while/if ; not for |
| S5 | Clean the lost telescopes exactly | FLOW | T3,L2,L3 | P — return/break/continue without labels |
| S5a | Loop result and cleaning before output; types, modes and durability | LOOP_RESULT | S5,T6,T11,V4,D1,B2,A3 | P — no value of while; labels absent |
| S6 | hand without parameter, Void/Int output and cleaning | ENTRY | S5,L2 | P — script mode retained |
| V1 | Explicit transfer retains local type `T` or the type of pool `A<T>` | INTENT | T1,T2,T6,P3 | P — transfer of `A<Point>` The following are the main features of the project: - the use of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the system of the](cycles/STORAGE_DESIGN_CYCLE.md) |
| V2 | Full initialization before use | ENUM | B4a,P9 | P — Int/&Int/&mut Int; Named borrowings, Controlled capacity |
| V3 | Implicit copies limited to copyable building materials | INTENT | V1,B4 | P — Int only in prototype |
| V4 | Let immutable / let mut; Int transfer without allowance, replacement after RHS | ASSIGN,LET_MUT | B1,B2,B4,L6,A5,P8 | P — Int and existing modes; expressions Int in .set (SET_EXPRESSIONS_CYCLE.md), no collections. In async, receiver Int held replaced by displacement, await, block, if and loop to result. Retention of identity and last reading of the former content exercised, including with a view declared two blocks higher. Later use in each block or by a task retains protection. Each arm of an if instruction or value can complete the loan separately. Additional exercises with value match and transfer block. A reading after the junction or in an argument evaluated then preserves protection. A replacement on a path leading to a direct break can complete the loan, including from a child block and |
| V5 | Stable address for the end of life | STORAGE | T11,L7,P8 | P — stability of fixed allocations and of the growing collection elements; see G12 and growth tests |
| T1 | No implicit transfer per assignment | INTENT | I1,B4 | P — Transfer syntaxes implemented only |
| T2 | Move local invalids old access without new reception | TRANSFER | L3,B3 | P — no displacement of sources. Async renaming tested with preservation of the destruction order, including after import and early exit. |
| T3 | Transfer to the balance sheet to direct parent | TRANSFER | S5,A3 | P — Marking valid until exit, except for consumption |
| T4 | Transfer down to the entrance to direct child | TRANSFER | T8,B3 | P — explicit imports only. Return of an import re-registers its destruction in the parent async. |
| T5 | Crossing the intermediate telescopes | TRANSFER | T3,T4,A3 | P — limited depths in tests |
| T6 | Explicit return and receiver, identity without former alias | TRANSFER | U1,T2,B4c | P — explicitly received replaced object, without re-activateing imported access; let <- followed by the final name verified in block, if and function, stable address, refusal of a local pool and warning without receiver |
| T7 | Destination ancestor without implicit promotion | TRANSFER | I1,T5 | P — compatible blocks and junctions, including loop outputs and loop repeats. 818 regression tests, 14 targeted under UBSan and two detected mutations. [Conditional joins](ANCESTOR_JOIN_VALIDATION.md), [ring cycle](LOOP_REPLACEMENT_VALIDATION.md) |
| T8 | Return guaranteed before re-use of an import | FLOW | T4,T9 | P — refund after replacement controlled by revision of the handle; order of receipt compatible required |
| T9 | Validity on all paths that continue | FLOW | S5,T11,L2 | P — conservative analysis, not all predicates |
| T10 | if expression receives an Integrable or an allocation; common type and mode | FLOW,LOOP_RESULT | T6,U1,T11,V4 | P — synchronous borrowed results and async terminal returns exercised; see REFERENCE_EXPRESSIONS_CYCLE.md and ASYNC_REFERENCE_RETURNS_CYCLE.md |
| T11 | All provenances protected, clean up the real source | PROVENANCE | A5,P9,L6 | P — finished sets; &Int fields, without transit graphs |
| U1 | Explicit use of the required result received, including unallocated results | INTENT | T6,B4c,F5,L6 | P — conditional use and permissible transmission; abandonment, `_`, unused link and direct crash rejected for tested inline results, sync/async. Mutation of detected control. Possible use, no guaranteed execution; families owners and junctions to complete. The bypass by await on a task chosen by if is corrected, tested at O0/O2 and detected by mutation (UTF8_TRY_SLICE_CYCLE.md). INTEGER_CONVERSIONS_CYCLE.md Supplement draft 01: proprietary pattern checks and explicit consumption, O0/O2, borrowings and re-use; three mutations detected. Partial coverage and counter-examples still opened in [OWNED_RESULTS_CYCLE](cycles/OWNED_RESULTS_CYCLE.md). Regular and wait receptions, renamings, replacements and controlled continuations; 21 methods dedicated to O0/O2 with fatal UBSan, 154 synchronous regressions and 37 successful async/UTF-8, independent model of 64 cases and five mutations detected. Always partial coverage: [U1_RECEIPTS_CYCLE.md](cycles/U1_RECEIPTS_CYCLE.md). |
| D1 | Targets already sustainable at each border, no implicit promotion | RETURN_FIELD | I1,T3,T5,D2,D3,A3 | P — Targets Int; General graphs not implemented |
| D2 | Follow references without extending targets | FIELD | D1,D3 | P — fields Int/&mut Int; transit graphs not implemented |
| D3 | Hold all possible dependencies | PROVENANCE | T11,D4 | P — finite sets of sources and targets Int/&mut Int ; future general graphs |
| D4 | No access to invalidated value/stocking | BORROW | A2,T9,L6 | P — limited evidence, no general evidence of safety |
| B1 | Shared readings or exclusive transfer | BORROW | B2,B3,B4a | P — direct references and shared and exclusive fields (MUT_FIELD), mutable projections limited to the arm (MUT_MATCH) |
| B2 | End of borrowing after last use | BORROW,LOOP_CARRY | V4,B3,L2,L6 | P — conservative analysis of paths. [Last use of a field on a recovery](LOOP_DEAD_FIELD_VALIDATION.md) |
| B3 | No move with loan still used | BORROW | T2,L6 | P — returns covered by RETURN_REF |
| B4 | Explicit modes and types of parameters preserved | POOL | B4a,P8 | P — read/mut pools; existing loans by name (REF_VALUE), runtime capacity |
| B4a | Arguments evaluated from left to right and protected | ARGS | B1,A5,V4 | P — named sources, sub-assembly expressions; reset in a contract-checked argument with cross-reference tables copied, borrowed and interlocked |
| B4b | Abstracts of propagated sources without local effect exported | POOL | B4,B4e,P8 | P — Non-recursive call graph |
| B4c | Origins and identity refunds of the result | RESULT | T6,T11,L7 | P — no reference returned |
| B4d | Drop equality and distinctions after reset | CONSTRAINT | A5,L6,T11 | P — no general solver of types/provenances |
| B4e | Check each body, calls by opaque contracts | POOL | B4b,B4c,B4d | P — still specialised backend; no proof of C |
| B5 | Borrowings returned valid during use | RETURN_REF | D1,D3,B1,B2,B3,B4a,A3,A5,L6 | P — &Int and &mut Int ; other unimplemented types |
| L1 | Destruction before storage recovery | CLEANUP | L2,L6,P4 | P — Demonstrative destroyers and proprietary fields. Heterogeneous cells of runtime exercised with a cross-pool, live prefixed and re-used detained field. Two cleaning and recoil mutations detected at O0/O2. Connection of local structures to the remaining compiler. [Storage circle](cycles/STORAGE_DESIGN_CYCLE.md) |
| L2 | Unique cleaning in the final scope | CLEANUP | S5,T3,A6 | P — stop over failure without progress |
| L3 | Inverse order of creation/receipt, separate physical order | CLEANUP | T2,T9,P8 | P — incompatible reception orders refused. In async, downhill group and local re-re-command exercised. Receipt of a downhill return at the end of the block, on break and in the branches exercised. Incompatibility orders between branches and on a re-command are refused. C async selects the order of the catches according to the return path, exercised under UBSan with restitution, early return, inactive drop and failure of launch. Combined order verified after restitution of a capture and receipt of an Int by await. Terminal cleanings follow the same lexical order in the release callback after extraction. |
| L4 | Dependencies of still alive destroyers | FUTURE | D1,D2,L3 | N — User destroyers and unimplemented cycles |
| L5 | Pre-cleaning only if preserved effects | FUTURE | L1,L3 | N — method of optimising destruction not implemented |
| L6 | `drop(-> x)` consumes the connection and respects the borrowings and sources; drop(-> expression) evaluates and consumes the result | DROP | B3,L7,T11,U1 | P — Int and synchronous local tables, local tables async; inline inline sync/async results consumed and expression effects executed only once before the next instruction. Two validity mutations detected in the storage cycle. Owner cover to continue. [Storage circle](cycles/STORAGE_DESIGN_CYCLE.md), INTEGER_CONVERSIONS_CYCLE.md Draft Supplement 01: proprietary and explicit consumption checks, O0/O2, borrowings and re-use; three mutations detected. Partial coverage and counter-examples still open in [OWNED_RESULTS_CYCLE.md](cycles/OWNED_RESULTS_CYCLE.md). |
| L7 | Logical death independent of physical reservation | STORAGE | L6,P4,P8 | P — storage can remain reserved. Cells of different sizes exercised by 200 transitions of the model at intervals, seed 9081, under UBSan at O0 and O2. Connection to the remaining local structures. [Storage circle](cycles/STORAGE_DESIGN_CYCLE.md) |
| A1 | Implicit local storage or explicitly named pool, transmitted by `&mut Pool<T>` for the allowance | SOURCE | I2,B4,P8 | P — creation and transfer via `&mut Pool<Point>` Migration of old syntaxes to be integrated. |
| A2 | Valid lifetime storage of the allowance | SOURCE | A3,A5,V5 | P — fields Int/ &mut Int; bounded transfers |
| A3 | No implicit transfer from a source too short | SOURCE | T3,T5,A6 | P — no sources returned or stored |
| A4 | Allocate without permanent borrowing of source | SOURCE | B1,P8,E1 | P — Strict capacity required |
| A5 | Reset destroyed before reset and protects future uses | RESET | B4a,T11,L3 | P — effets conditionnels conservatifs |
| A6 | Objects destroyed before source is closed | SOURCE | L2,A3,A5 | P — no moving sources |
| P1 | Stable, bounded and guarded virtual ranges | STORAGE | V5,E1 | P — backend Rust, end guard of the two datatacks. 16 scenarios under UBSan at -O0/-O2 on macOS arm64. [Report](cycles/CORE_COMPOSITION_CYCLE.md#p1--pages-de-garde) |
| P2 | Explicit local configuration of reservations | DIRECTIVES | I4,P1,G6,G7 | P — syntax categorised and lexical inheritance exercised; addresses and limits after transfer under UBSan O0/O2. Blocks annotated async still refused. [Cycle directives](cycles/DIRECTIVES_CYCLE.md) |
| P3 | Prepare local durable storage on the receiver side by keeping address and order of assessment | STORAGE | I3,L3,T6,V2 | P — early reservation on historical sources and in G1 forms. Reservation of structures in the implicit data stack to be integrated. |
| P4 | Only get dead suffixes from the cursor | STORAGE | L7,P8,V5 | P — fixed model without growth |
| P5 | Two growth fronts without overlap | STORAGE | P1,P6,E1 | P — two Vector fronts and collisions; String follows TX21 |
| P6 | Borning the living population, not the successive total | FUTURE | P3,P5,E1 | N — general static analysis not implemented |
| P7 | Explicit local fallback retaining guarantees | SOURCE | I1,A1,P8 | P — explicit backends; automatic static selection absent |
| P8 | Pool typed, slots adapted, type kept for calls | POOL | B4,B4b,P4,L7 | P — Int and enums; no lines or collections |
| P9 | Public enum pool, stack by variant, global order | ENUM | P8,L3,A5 | P — Int/&Int/&mut Int fields, complete match and mutable projections (MUT_MATCH) |
| E1 | Exhaustion: Diagnosed stoppage without progress | FAILURE | V4,P1,P8 | P — failure of forced OS not exhaustive |
| E2 | Tables: Static or runtime terminal control | FUTURE | D4,E1 | N — tables outside scope |

<a id="profils-de-vérification"></a>

## Audit profiles

For all profiles: tests are limited; no argument
The above mutations are not established.
below only designate the five faults of this cycle.
historical runtime are not presented as reexecuted here.
The [cycle of loop results](LOOP_RESULTS_VALIDATION.md) ajoute
four targeted mutations, two of which are for pool recovery.
The overall cycle regression has 789 successful tests.

| Profil | Examples admitted and refused / executable evidence | Assertions runtime pertinentes | Independent model / mutations | Limites propres |
| --- | --- | --- | --- | --- |
| INTENT | [test_crust.py](../tests/test_crust.py) : `test_move_and_primitive_copy` admis ; `test_implicit_alias_rejected`, `test_source_required`, `test_uninitialized_new_rejected`, `test_unused_receiver_rejected` rejected | Python status validation; no runtime control replacing missing intent | No complete model or mutation dedicated to grammar | syntaxes actually implemented; not all buildins |
| ENTRY | [test_crust.py](../tests/test_crust.py) : Void/Int hand, wrong parameters/returns, script/hand mixture; outputs and cleanings | binary return code, tracks before output | No model or hand mutation | stop and platform-dependent codes |
| LOOP_RESULT | [test_loop_results.py](../tests/test_loop_results.py) : interlocked results, recovery and return, multi-provenance reset, borrowing and bad types/duration | traces of destruction, identity by address and limited capacity | block and variant destruction model generated with seed 20261103 | see [cycle report](LOOP_RESULTS_VALIDATION.md) |
| LOOP_CARRY | [test_loop_replacements.py](../tests/test_loop_replacements.py) : break/continue, normal end, false test, returns, enum, pools and refusal of loans/rest/order | identity by address, single destruction, cleaning guard and source of each alternative | 6 sequence trace model, seed 20261103; two targeted mutations | compatible order required, active or reactivated access refused, inactive field retained for cleaning. [Last used](LOOP_DEAD_FIELD_VALIDATION.md). [Rapport](LOOP_REPLACEMENT_VALIDATION.md) |
| FLOW | [test_conditionals.py](../tests/test_conditionals.py), [test_if_expressions.py](../tests/test_if_expressions.py), [test_loops.py](../tests/test_loops.py), [test_continue.py](../tests/test_continue.py), [test_while.py](../tests/test_while.py) : exits with reception allowed; uses after conditional consumption refused | cleaning guards, living value meters | Cleaning model on part of the branches, `test_audit_regressions.py` ; no flow control mutations this cycle | exploration, not all predicates or for |
| CALLS | [test_function_bodies.py](../tests/test_function_bodies.py), [test_modular_calls.py](../tests/test_modular_calls.py) : opaque calls and valid bodies; incompatible double consumption and borrowing refused | access check, status invariants | Pools only model; signature/propagation/call mutations | no contract for recursion, FFI or returned references |
| TRANSFER | [test_crust.py](../tests/test_crust.py) : `test_nested_transfer_preserves_address`, `test_reception_and_child_cleanup_order` ; `test_use_after_move`, `test_downward_transfer_requires_direct_parent` refused; [test_results.py](../tests/test_results.py) | no runtime control allowing an old name; traces of destruction | Independent model movings/receptions in `test_audit_regressions.py` ; no mutation transfer this cycle | Direct imports and current types |
| ASSIGN | [test_reassignment.py](../tests/test_reassignment.py) : RHS using last admitted loan, future loan refused; address returned and pool replacement | destroyer before recovery; shutdown capacity | partial cleaning model, no general reassignment model | simultaneous RHS + old value capability; no fields |
| PROVENANCE | [test_provenances.py](../tests/test_provenances.py) : stable selection and partial reset after last use; reset before use or leak from local source refused | `cell_has_source`, gardes conditionnelles | partial cleaning model; no mutation from this cycle | no user reference graph |
| BORROW | [test_crust.py](../tests/test_crust.py) : `test_multiple_read_borrows`, `test_last_use_ends_borrow` ; `test_live_borrow_blocks_move`, `test_exclusive_mutable_borrow` refused; [test_function_bodies.py](../tests/test_function_bodies.py) | exclusive and last statically controlled uses | No complete independent borrowing model or dedicated transfer this cycle | last conservative use; restricted re-borrowing |
| ARGS | [test_arguments.py](../tests/test_arguments.py) : copy before reset allowed, loan prepared invalidated refused; [test_modular_calls.py](../tests/test_modular_calls.py) | C sequenced; validation of prepared arguments | case specified independently, no complete model; no mutation order this cycle | arguments from named sources |
| POOL | [test_pool_requirements.py](../tests/test_pool_requirements.py) : correct pool allowed, other type/tas/stack refused; [test_effects.py](../tests/test_effects.py), [test_modular_calls.py](../tests/test_modular_calls.py) | static type verification; `source_check_empty`, capacity controls do not establish the type-taking alone | Road model `pool_requirement_model.py` 5 mutations in `validation/pool-requirement-mutations.json` | readonly model without branches; interactions covered by separate tests, not exhaustive |
| RESULT | [test_results.py](../tests/test_results.py), [test_conditional_returns.py](../tests/test_conditional_returns.py) : guaranteed identity admitted, former access and local source refused | Summary/Racist correspondence observed in the backend | partial reception/cleaning model; no mutation resulting in this cycle | no results taken |
| CONSTRAINT | [test_constraints.py](../tests/test_constraints.py) : read and reset admitted, reset then read from the same source refused; equality of `source.drop` | static source comparisons, no dynamic relationship test | independent route model for pool requirement only; no solver mutation | no general satisfaction |
| CLEANUP | [test_scope_exit.py](../tests/test_scope_exit.py) : `test_normal_exit_closes_only_inner_scopes`, `test_explicit_drop_is_not_repeated_during_unwinding` ; source too short refused | `source_check_empty`, `source->live`, guards and traces | model of 32 operations × 2 seeds × 3 backends in `test_audit_regressions.py` ; no mutation cleanup this cycle | Destructive Demonstration; No Failure to Run |
| DROP | [test_drop_transitions.py](../tests/test_drop_transitions.py) : last re-borrowing then consumption allowed ; future borrowing, old access and bad receiver refused | `cell_drop`, free list removal and suffix recovery | oracle runtime + model cleaning; no mutation drop this cycle | no destroyer user |
| SOURCE | [test_scope_exit.py](../tests/test_scope_exit.py), [test_crust.py](../tests/test_crust.py) : source externe durable admise ; `test_transfer_from_child_allocator_rejected`, `test_stack_allocator_cannot_escape` rejected | `source_close` requires zero living object | oracle storage, no full life model of sources; pool mutations only | sources not moving |
| RESET | [test_reset_transitions.py](../tests/test_reset_transitions.py) : `test_last_reborrow_does_not_prevent_reset_in_same_or_nested_function` admis ; `test_future_direct_or_borrowed_access_rejects_reset` refused | destruction avant `source_reset` and `source_check_empty` | independent cleaning model and oracle pool; no mutation reset this cycle | possible sources analysed conservatively |
| STORAGE | [test_safety.py](../tests/test_safety.py) oracle 3000 operations; [test_crust.py](../tests/test_crust.py) stable addresses, suffixes, invalid reservations, rejected overflows/rests | alignment, sizes and capabilities, live/free-list, terminal guard | oracle runtime independent of generator; no runtime mutation this cycle | a platform, no growth or double cursor; ASan unavailable |
| ENUM | [test_crust.py](../tests/test_crust.py), [test_provenances.py](../tests/test_provenances.py), [test_pool_requirements.py](../tests/test_pool_requirements.py) : correct variants/pools allowed; incompatible fields, variants and pools refused | `enum_new` check arms; source public root | oracle with two arm sizes; model of typical roads; pool mutations | Int/&Int/&mut Int, match readonly, no variant change in place |
| FAILURE | [test_crust.py](../tests/test_crust.py) : valid and invalid abilities; `tests/validate_pool_contract_c.py` : two successful programs, expected exhaustion | `fail`, controlled overflows before calculation/addressing | oracle of the terminals; no mutation capacity this cycle | no exhaustive OS error simulation or sequence |
| FUTURE | No valid program of general functionality in the subset; a syntax refusal does not prove its memory rule | Not applicable to an absent feature | No model/proof/mutation validates the general rule | not implemented / not verified |
| DESIGN | Reading the specification and boundaries of the sub-assembly; no test proves a choice of design | Non applicable | No formal evidence | do not equate refusal of future functions with their validation |

<a id="matrice-des-interactions-et-réexamen-global-du-cycle"></a>

## Interaction matrix and overall cycle review

Each domain of the current system has been reread. "Regression" means that the
existing domain suites are executed in the cycle; this does not cover
the Cartesian product of the rules. The new interactions are detailed
below; future features remain N, without invented tests.

| Domaines | Effect sought / counter example | Cycle evidence and limitations |
| --- | --- | --- |
| B4/B4b/B4e × P8/P9 | Signature requirement lost without allowance | Initial case, opaque contracts without body, model of 40 graphs and mutations |
| P8 × S3/B4a | Reordered settings, interlocked calls and depth | Route model + deterministic tests of wheel/argument; depth generated 7 functions |
| P8 × T9/S4/S5 | Literal branch, divergence, return and inaccessible obligations | Contradictions of the rejected branches ; after return ignored ; loops and condition tested ; not any logical equivalence |
| P8 × V1/V2 | Do not confuse allocate Int with receiving Pool<Int> | Int admitted on heap/stack/pool; enum imposes its pool; fields/init regression |
| P8 × B1/B2/B3 | The required type does not grant an additional transfer | readonly/mut tested; borrowings and movements in global regression |
| P8 × B4d/A3 | Equal sources and duration of storage | Type of pool/input event conflict tested; hidden local sources; regression durations |
| P8 × T2/T6/B4c/V5 | Re-identification after re-use of a slot | New address/restitution/destruct test; other regression returns/provenances |
| P8 × A5/L1/L2/L3/L6 | Reset and clean up exactly once, semantic order | New scenario and existing cleanup model; oracle runtime; C O0/O2/Os/UBSan |
| P8/P9 × P4/L7/E1 | Reused slot, dead suffix, exhaustion | Oracle 3000 operations, regression and three C-programmes bounded |
| I1–I5, U1, S1/S2/S6, T1/T4/T5/T7/T8/T10/T11, A1/A2/A4/A6 | Intention, range, aliases, reception, exits | Specification review and corresponding full follow-up; no invariant is declared to be globally established |
| L4/L5/P2/P3/P5/P6/E2 | Future rules | Not verified; no added functionality to test them |

No change in normative semantics is allowed by this matrix.
The contradictions in specification, coverage limits and differences not
the cycle report, without changing the
expectations for green tests.


<a id="extension-des-preuves--champs-int"></a>

## Extension of evidence: &Int fields

The FIELD profile below completes V2/V5, T2/T6/T9/T10/T11, D3/D4,
B1/B2/B3/B3/B4/B4a/B4d/B4e, L1/L2/L3/L6/L7, A2/A3/A5/A6 and P8/P9.
D1/D2 are now partially covered for &Int fields, without promotion
implicit. The general graph remains unverified; B5 is now partially covered by RETURN_REF.

| Profil | Expectations and examples accepted/refused | Preconditions and invariant | Runtime / model / mutations | Limites |
| --- | --- | --- | --- | --- |
| FIELD | [test_reference_fields.py](../tests/test_reference_fields.py) : read and then drop allowed; drop/mutation/reset before read refused; transfers to target already sustainable allowed; local target refused; function returns to sustainable targets covered by RETURN_FIELD | &Int immutable to named allocation; all future uses of the bearer protect its targets; no new mutable right | Payload memcpy and offsets per variant; 32 scenarios model, 19 invalids/13 invalids; four mutations; [reports](REFERENCE_FIELDS.md) | a level of dependencies, no enum references, cycles, automatic or destructive user promotion; known variant or static union |

Interactions exercised: FIELD × B4a (next reset/consumption initializer),
FIELD × B4d/B4e (derived from substituted fields without body), FIELD × T9/T10
(target union), FIELD × V4/P8/L7 (replaced and re-used slot), FIELD ×
S4/B2 (next loop use), FIELD × A5 (target or carrier rest),
FIELD × L1/L2/L3 (target destroyed after last use, carrier cleaned without
The 66 rules were
Reconsidered under the restrictions of this extension; the complete follow-up
repeat existing models and other interactions.
The results achieved and the limitations of the
The cycle report shall be distinguished.


<a id="extension-des-preuves--retours-avec-champs-empruntés"></a>

## Extension of evidence: returns with borrowed fields

The RETURN_FIELD profile complements the 66 existing rules without claiming the
establish. Reference: [BORROWED_RETURNS.md](BORROWED_RETURNS.md). The rules
D1/D2 are partially covered for &Int fields; general graphs
The &Int B5 direct returns are partially covered by RETURN_REF.

| Profil | Expectations and cases admitted/refused | Preconditions and invariant | Models, assertions and mutations | Limites |
| --- | --- | --- | --- | --- |
| RETURN_FIELD | [test_borrowed_returns.py](../tests/test_borrowed_returns.py) : target borrowed from the admitted parent; local target or Int injected by transfer refused; drop/reset before use refused, after last use allowed | &Int immutable ; all targets already alive in destination/ancestors ; identity of fields kept in opaque contracts ; mutable parent suspended during shared reborrowing | destination verification and contract/observed correspondence; model 24 scope routes, 12 admitted/12 refused; five new mutations and four previous replayed; C O0/O2/Os/UBSan | no local promotion, transitive or destructive user graphs; no general oracle of borrowings or formal proof |

Interactions examined: RETURN_FIELD × S3/S5/T3/T5/T6 (sequence borders),
RETURN_FIELD × B4c/B4d/B4e (parameter/field identity and bodyless substitution),
RETURN_FIELD × B1/B2/B3 (shared re-borrowing and re-suming of the mutable parent),
with refusal of an alias not related since the original access during this re-borrowing,
RETURN_FIELD × A3/A6 (length of target distinct from pool),
RETURN_FIELD × T9/T11 (target unions and variants), RETURN_FIELD × V4/V5/L6
(reassignment, drop and identity), RETURN_FIELD × A5/L2/L3/P8/P9 (rest, cleaning)
and capacity), RETURN_FIELD × B4a (argument already prepared), RETURN_FIELD × S4
(next use in a loop). Future rules are not added for
increase testing; limits and results are recorded in the report.


<a id="décision-d1--pas-de-promotion-implicite"></a>

## Decision D1: No implicit promotion

The user has explicitly replaced the proposal to promote targets
by their refusal to transfer if they are not already sustainable enough.
D1/D2 move from future rule to partial coverage
for existing &Int fields; no general graph is announced.
interactions I1/T3/T5/B4c/D3/D4/A2/A3/L2/L3/P8/P9 were reconsidered:
no connection, destruction order, pool or borrowing mechanism is
as amended by that decision, which corresponds to the behaviour already implemented.
Tests refuse a local target even when its pool is durable, including
See [Decision and Targeted Validation]](NO_IMPLICIT_PROMOTION.md).

<a id="extension-des-preuves--retours-directs-int"></a>

## Extension of evidence: direct &Int returns

The RETURN_REF profile covers partially B5, with the premises D1/D3/D4 and
interactions B1/B2/B3/B4a/B4c/B4d/B4e, S3/S4/S5, T2/T5/T9, U1,
The 66 rules were:
Reconsidered: no change in investment, transfer of allowance or
I1/I2/B4 remain explicit; the rules
The extension does not implement future L4/L5/P2/P3/P5/P6/E2.

| Profil | Cases allowed/refused | Preconditions and invariant | Observations, models and mutations | Limites |
| --- | --- | --- | --- | --- |
| RETURN_REF | [test_direct_borrow_returns.py](../tests/test_direct_borrow_returns.py) : parent/ancestor and relay allowed; local target/transferred parameter refused; drop/reset/mutation before use refused, after last use allowed | &Int read result; each target already alive and attached to parent/ancestor; no promotion, no allocation of result; all protected alternatives | contrat `reference_targets`, border verification and contract/observed; 24 permutation seeds and unions (12 invalid/12 invalids), addresses and destructions; five new mutations, nine previous replayed; 12 executions C O0/O2/Os/UBSan | no return or enum, no field output via match; limited model without general proof of borrowing |

Specific interactions: conditional result × separate sources × reset;
reference returned × field &Int × drop of alternatives; argument prepared ×
secondary aliases mutable/reset in the following argument; relay × historical
previous reset; shared reborrowing × resuming of the mutable parent; reassignment
without destruction of targets; loops/continues and cleaning without destruction of the
parent; re-use of slot after last reading. Opaque effects remain
Checked without reading the bodies. See [cycle report](DIRECT_BORROW_RETURNS.md)
for the results and instrumentation limits.


<a id="clarification--création-et-utilisation-dun-emprunt"></a>

## Clarification: creating and using a loan

Explicit decision of the user: `inspect(&data)` creates a loan from
an allowance; `inspect(view)` and `return view` use a reference
existante. Un `&` Additional references are not flattened.
The REF_VALUE profile completes B4/B5
and V2/P9 for consistency of &Int fields, without new normative identifier.

| Profil | Valid and invalid cases | Invariant and premise | Models / runtime / mutations | Limites |
| --- | --- | --- | --- | --- |
| REF_VALUE | [test_reference_values.py](../tests/test_reference_values.py) : calls/returns by name, subcall result, pool and field settings; refusal of reference, owner passed without &, escalation readonly→mutable, drop/reset before use | no implicit loan of allowance; type/reference method retained, targets and mutable parents followed; arguments prepared protected; source readonly remains readonly | 8 admitted programs executed, 23 cases rejected by check and compilation, 1 inference control alone; previous models migrated without changing their oracles; five specific mutations + 14 previous; C optimized and UBSan | no &&Int, general assignment of aliases, return &mut or new type; a family C, no general evidence |

The 66 rules were reviewed: I1/T1/V3 (intention and lack of copying)
(Borders and cleaning), D3/T9/T11 (Unions of
B1–B3/B4a (exclusiveness, last use and order of arguments),
B4b–e/A1/A2/A3/A5/A6/P8/P9 (contracts and capacity of sources),
V4/V5/L1–L3/L6/L7 (identity, replacement and single destruction) are exercised
The rules for future investment,
collections, user destroyers and competition remain outside the perimeter.
The C pointer format and runtime do not change.
cycle limits are in [REFERENCE_VALUES.md](REFERENCE_VALUES.md).


<a id="extension-v4--let--let-mut-et-mutation-du-contenu"></a>

## Extension V4: let/let mut and content mutation

User's decision: declarations `let` immutables, `let mut` for
direct entries; `name = 20` and `name.set(20)` modify the content of an Int
The replacement with an allocated result keeps
its cleaning after RHS. The 67 normative identifiers are kept: V4 is
specified, B4 distinguishes the mut from the variable of the &mut capacity.

| Profil | Expectations/cases admitted and refused | Premises and Invariant | Observations, models, mutations | Limites |
| --- | --- | --- | --- | --- |
| LET_MUT | [test_let_mutability.py](../tests/test_let_mutability.py) : stable address for = and .set ; immutable owner refused to write, &mut via let allowed, let mut &Int refused; drop/reset before use refused, after use and reuse allowed | mutation without creation/reception/destruction; target still alive after RHS; mutability of name distinct from pointer; explicit consumption of an immutable name allowed; sources and contracts retained | 33 new programs admitted and 50 rejected at both stages; model 12 seeds ×12 writings, matrix reportable 18 cases (5 admitted/13 refused); five new mutations and 19 previous replayed; C O0/O2/Os/O2-UBSan | .set on variable and literal Int; interlocking references, return &mut and general assignments of non-destricted aliases; no general evidence |

Review of 66 rules: I1/I2/V1/V3/T1 (intent, source and lack of copy
V2/V4/V5/L1–L3/L6/L7/P8 (initialization, identity, destruction and
(capacity, last use, contracts, provenances)
and order of assessment), S3–S5/T2–T11/U1 (functions, branches, imports, loops
A1–A6/P9/E1 (pools, mutable source, reset and exhaustion) remain
The tests check a HHR that reads the target before writing and
a HHR that consumes or restores its pool; opaque contracts must
keep its history after writing. A mutation of the latter followed
is detected even when the specialized backend still refuses the code.
Alternative placements and other future rules remain unimplemented.
See [Report and limitations]](LET_MUTABILITY.md).


## Extension B5 : retours d'emprunts mutables

Explicit decision of the user: `-> &mut Int` returns capacity
The example uses the following:
`let mut vue = borrow_mut(&mut nombre)`. 67 identifiers are retained;
B5 receives the RETURN_MUT profile in addition to previous cycles.

| Profil | Cases allowed/refused | Invariant and premise | Observations/models/ mutations | Limites |
| --- | --- | --- | --- | --- |
| RETURN_MUT | [test_mutable_borrow_returns.py](../tests/test_mutable_borrow_returns.py) : mutation via result, parent recovery after last use, relays, unions, children shared, direct passage into argument; refusal of other readings/writes, drop/reset before use and local targets | each candidate has an entry & transfer capacity and already lives in parent/ancestors; an exclusive loan by binding and target, parents suspended as long as the descendant requires; addresses and source kept | 28 admitted programs executed and 58 refused both courses; model 24 seeds, 1–4 relays, permutations and unions, 12 invalids/12 invalids; 5 specific mutations and 24 previous replayed; C O0/O2/Os/UBSan | Int returns only; no nested reference, field mutable projection, user destructive or formal proof |

Overall review: B1/B2/B3/B4/B4a–e/B5 (capacity, type, arguments, last use)
and opaque contract), D1/D2/D3/D4/T5/T9/T11 (sustainability and unions), S3/S4/S5
(scopes, boucles, continue, return annulant un appel), V3/V4/V5/U1/L1–L3/L6/L7
(no copy, identity, explicit use and single cleaning), A1–A6/P8/P9/E1
(source, reset, re-used slot and exhaustion) are exercised or reviewed.
The last-use follow-up was also corrected for V4/U1: a
content on an allocated Int is not a binding purpose and is a use.
Future rules on collections, FFIs, investment and competition remain outside the scope of the
The evidence and boundaries are in [MUTABLE_BORROW_RETURNS.md](MUTABLE_BORROW_RETURNS.md).

<a id="extension-p9b1--références-mutables-stockées"></a>

## Extension P9/B1: mutable references stored

User decision: a &mut Int field retains the exclusive capacity on its
The target until the last use of the wearer or a reference to him.
standard identifiers remain unchanged; MUT_FIELD complete FIELD and RETURN_FIELD.

| Profil | Cases allowed/refused | Invariant and premise | Observations/models/ mutations | Limites |
| --- | --- | --- | --- | --- |
| MUT_FIELD | [test_mutable_reference_fields.py](../tests/test_mutable_reference_fields.py) : shared aliases of the holder, projected reading, relays, transfers, conditional returns, parent recovery; refusal of accesses of origin/drop/reset premature, aliased fields and readonly entry | mutable entry capacity; targets already durable at each border; a field capacity per porter and target, preserved via shared aliases and projections | 24 accepted sources executed, 43 refused both courses; seed model 381, 24 scenarios (12/12); 6 specific mutations and 29 previous detected; global suites 729/729; C O0/O2/Os/O2-UBSan; [report and artifacts](MUTABLE_REFERENCE_FIELDS.md) | Int only, non-retrievable fields, reading projections, conservative contracts; no user destroyers or formal evidence |

Re-examined interactions for the 66 rules: I1–I5/V1–V5 (intent, types,
mutability, identity), S1–S6/T1–T11/U1 (scopes, receptions, branches and loops),
D1–D4/B1–B5/B4a–e (sustainability, capabilities, contracts and arguments), L1–L7/A1–A6/
P8/P9/E1 (sources, cleaning, reset, slots, exhaustion).
collections and other future features retain their previous status.
The interactions performed do not cover all possible combinations.

<a id="extension-p9b1b2--projections-mutables-dans-un-bras"></a>

## Extension P9/B1/B2 — mutable projections in one arm

| Profil | Cases admitted and refused | Invariant | Observations | Limites |
| --- | --- | --- | --- | --- |
| MUT_MATCH | [Tests](../tests/test_mutable_match.py) with projected writing, shared alias, out-of-arm projection, successive calls, reset and drop | exclusive access to the wearer during the arm, then protection of the targets until the last use of the wearer or a reference to him | 9 sources admitted and executed, 19 rejected by both courses, two-border model, 3 injections detected, 8 C executions, 739 global tests and 67 tests targeted under UBSan | Int by `.set()` and Void calls with named projections (MATCH_CALL). The analysis refuses field projections whose target sets can be covered |

S4 and S5 define the re-borrowing. V4 and V5 frame the writing on site.
D1–D4, T9–T11 and B4–B5 frame the targets obtained by transfer or call.
L1–L7, A2, A5 and P8 retain their role in cleaning and reuse.
[Report of the cycle](MATCH_MUTABLE.md).

<a id="extension-p9b4--appels-avec-projections-du-bras"></a>

## Extension P9/B4 — calls with arm projections

| Profil | Cases admitted and refused | Invariant | Observations | Limites |
| --- | --- | --- | --- | --- |
| MATCH_CALL | [Tests](../tests/test_mutable_match_calls.py) with successive calls, rejected aliasing, restoration of projection, impossible variant and divergence | the call borrows the projection and returns it to the arm. The carrier continues to protect the target | 4 admitted sources executed, 11 rejected by both courses, 3 dedicated injections and 6 replayed detected, 4 C executions, 745 global tests and 73 under targeted UBSan | calls Void and arguments limited to the names of the projections of the arm |

S4–S5, B1–B5, D1–D4, T9–T11, V4–V5, L1–L7, A2 and A5 are reviewed
in [the report](MATCH_MUTABLE.md#appels-void-dans-un-bras).

| Extension of MATCH_CALL | Invariant | Target validation |
| --- | --- | --- |
| Result Int in an arm statement (S4, V3, B4, P9) | independent copy, reusable projection on return, carrier reserved during arm | copy before writing, rejection of original access and connection out of the arm, type and integer in an impossible variant |
| &mut Int received by `let mut` in the arm (B1, B2, B4, B5, S4, P9) | the parent resumes after the last use of the result, the reservation of the holder covers the arm | relayed return, writing after last use, rejection of reading, premature writing and calling, local scope, impossible variant |
| &mut Int received after the match (S4, B1, B2, B4, B5, P9) | carrier reservation and life of targets until the last use of the result or descendant | read the porter before/after, reset and drop, relayed returns, conditional variants, injection of the porter's loan, 4 performances C, 756 global tests and 84 under targeted UBSan |
| Return of a projection via a carrier parameter &mut (B1, B2, B4, B5, D1, P9) | the contract transports the targets and the holder to the last use at the appellant | read the carrier before/after, life and reset, known variants, relay reindexation, contract inspection, 762 global tests, 90 targeted on UBSan and one injection detected |
| Reservations stored and transitory (B1–B5, D1–D4, T9–T11, P9) | each descendant protects the possible carriers and targets, each transfer checks their lifespan | opaque storage and return, chain, transfer refused if the holder does not survive, union of the carriers |
| Resets contracts (S4, S5, B4a, B4d, A5) | no invalid use after reset on the same path and no invalidation of a future loan or prepared argument | direct and compound order, branches, caller junction, other active borrowing, prepared argument, loop return, 771 global tests, 99 targeted on UBSan, 2 detected injections and 8 C executions |

<a id="tableaux-de-taille-fixe"></a>

## Fixed-size tables

| Rule | Invariant and interactions | Cycle evidence |
| --- | --- | --- |
| E2, E4 | A valid index precedes access C. Control of the line precedes the assessment of the column and the value to be written. Calculation of an index may have source effects. | Cases performed for negative indices and upper bound, static rejection of invalid constants, mutation of the detected bound and case of reset via call in an index. |
| E3 | An orderly and complete initialization. A repetition evaluates its value once, including for zero. | Trace executed, sequence mutation detected, context return of an empty array and access to the rejected empty array. Partial coverage for other typing contexts. Int local async arrays also cover suspended repetition, empty and static context. |
| E5 | No implicit line copy. The box keeps its type and initialized value. The transfer of values and transfers retain the type and length. | Perform returns and copies through functions, branches and loops. Rejections for incompatible types or operators. Model by list of 90 operations. Replaces and swaps Int boxes in an async task, with suspendable indices, control before effect and respect for loans. Explicit copy and swap of Int lines exercised during a disjointed loan. Replaces Int line prepares the new line, makes the old independent and respects the last use of the loan in the right part. Explicit moves of Int tables between links, block, if and break async worked with form control and borrowing. Int table async parameters receive an independent value prepared in the order of arguments. An explicit return of Int table |
| E6, E7 | The borrowing of tables and stored references protect sustainable targets through usage, replacements and calls. | Initial state of the cycle; see the evidence of the current cycle below. |

Voir [FIXED_ARRAYS_VALIDATION.md](FIXED_ARRAYS_VALIDATION.md).


<a id="tableaux-fixes-doctets-dans-les-cadres-async"></a>

### Fixed bytes tables in async frames

| Rules | Invariant | Evidence and limitations |
| --- | --- | --- |
| E2–E5, AS2, AS8–AS10 | The shape and type of element are kept in storage C and the control results. | Entwined tables prepared before launch, independent copy, read and write typed, no memory of one byte, case replacement, swap, transfer into an annotated loop, literal return, await and join. Indices suspended and dynamically exercised. Mix with Int with identical shape refused. Changes of step and type to the break detected. Partial coverage of transfer expressions and types of leaves. |
| E6, AS12, AS15, MT6 | A borrowed byte retains its source, including after extraction of a result. | Local loan transmitted to a child, transfer and displacement refused before last use. Return of a box of a table parameter borrowed by await, handle and join relayed in synchronous. Change of provenance detected. Return of a view to an array of the rejected frame. Partial coverage of mutable scalar u8 borrowings and local table links borrowed. |

Executions at O0 and O2 under fatal UBSan and their mutations are recorded
in [the async report](cycles/ASYNC_DESIGN_CYCLE.md#tableaux-fixes-u8-dans-les-fonctions-async).

<a id="tranches-partagées-de-vector-en-async"></a>

### Vector splits in async

| Rules | Invariant | Evidence and limitations |
| --- | --- | --- |
| VE5, AS8–AS10, B4a | The descriptor retains its boundaries, its step and its meaning through the suspensions. The prepared source remains protected during the calculation of the terminals and index. | `&[Int]` and `&[u8]` local, sub-tranches, indexing, capture and return by `await` ou `join`. Oracle by lists on two directions of placement and three terminals. Dynamic terminals out of bounds and indexation of an empty slice stopped by guards C. Reassignment during the calculation of the terminals keeps the descriptor prepared and protects its source. Changes in sense and backup detected. |
| AS2, AS11–AS13, AS15, MT6 | The loan protects the source from the moment of capture and until the last use of the result. The termination releases the catches used only for calculation. | Synchronous start-up and start-up contracts `join`, choice between two sources with simulated launch failure, source of an index made accessible after `join`, an extended origin to the recovery of a loop. Exit from a view to a local collection and premature modification refused. Mutations of provenance, loop and terminal detected. |
| VE5, TX16, B4, AS12 | A d-byte slice can be used for UTF-8 replacement or provide a `&u8` The slice descriptor has a distinct type of `Int`. | Replacement with relayed and sub-tranche slice, return of a d-byte reference through `await` then `join`, growth allowed after last use. `&Int` and `&mut Int` The loan is for a tranche refused. `&Int` d-a sliced box remains open in the async bodies. |

See [cycle report](cycles/ASYNC_DESIGN_CYCLE.md#tranches-partagées-de-vector-en-async)
for configurations, counter-examples and results executed.

| Rules | Invariant | Evidence and limitations |
| --- | --- | --- |
| B1–B2, B4a, AS12, AS15, VE5 | A split slice lets read through the same `&mut Vector<T>`It prohibits handwriting and new mutable catches until the last use. Access by the original owner remains separate. | Synchronous test with contract return and readback during the preparation of an argument. Async test with return by `await`, child task on another thread and shared capture from the same source. Two native programs and six refusals checked under UBSan at O0 and O2. Six mutations detected. |
| AS2, AS12–AS13, AS15, MT5–MT6, VE5 | The synchronous launch keeps the parent of each capture. A mutable capture excludes access during execution. The split slice from the `join` allows reading through the same parent and keeps all its possible sources. | Direct and contract launch, hand transfer, simulated launch failure, result from two sources, refusal to read during execution and write before last use, order of arguments, block release and `drop` Four mutations detected. |
| B1–B2, B4, AS15 | `&*v` and `&mut *v` A read call via the same parent can coexist with shared catches. | Two tasks in reading, synchronous call with the parent, then exclusive task via contract. Imbricated references, mode change and writing before the end of the second loan refused. Four mutations detected. The autonomous construction of a link by `let alias = &*v` remains separate. |
| VE5, G12, B1–B2, AS8–AS9, TX16 | Local mutable halves remain disjointed despite suspensions. A shared reborrowing reserves its half and the necessary ancestors. | Int and u8 separation, right half subdivision, writings, custody before the HHR, up and down placement, relay view by `await` and growth recovery after last reading. Three mutations detected. |
| B3, D1, T3–T5, AS10–AS13, MT6, VE5 | The shared result of a separation retains the vector that contains its elements. An exported task cannot borrow an allocation destroyed or moved at the exit. | Slice and byte returns, block, if, break, assignment to a parent, transfer of inactive task and handle. The terminal is released at the `join` and the vector remains protected. Counter-example of reading after destruction reproduced on an old version. Variants of output d-iteration and branch refused and mutations detected. |
| B1–B2, AS2, AS12–AS15, MT1–MT6, VE5 | One capture `&mut [T]` reserves the half concerned from the creation. A task on the other half can progress independently. | Two workers synchronized by an atomic appointment, since `main` and from an async frame, with direct launch and handle contract. Re-use after inactive drop, return shared by `await` and `join`, simulated launch failure and local target refused transfer. Four mutations detected. Mutable returns and pairs async results remain open. |

<a id="emprunts-locaux-de-tableaux-et-paramètres-empruntés"></a>

### Local borrowings of borrowed tables and parameters

| Rule | Invariant and interactions | Cycle evidence |
| --- | --- | --- |
| E3 | The type of parameter or destination determines the shape of the parameter or destination. `[]`. | The execution of the passage of an empty array, the writing and the replacement of an empty line. Synchronous annotation of Int tables and empty references, the transition to a task and the relay by await under UBSan. Incompatible length and the indexation refused. Mutation of access to the unexposed field C detected. Propagation of the expected type to the empty lines of an nested literal. Projection and relay of line under UBSan, empty line of expected length not null refused. Mutation that omits the propagation detected. The return contract also provides the context to an imbricated litteral transferred, directly or via an annotated local variable. Omission |
| E6 | A box loan protects the entire board until the last use. A reborrowing retains the inherited reservation. | Programs accepted and refused for the end in the right side, the loop resumption, the reborrowing and the moving of a borrowed table. `mut_ref()` d-a reference table retains its type and the updates of boxes pass through a function relay. Two mutable boxes of separate tables can be captured via a task factory. Two boxes of the same table are refused. A task cannot take a local box out of its block. Mutation of the detected range. |
| E6 and B4a | A borrowed argument protects the table during the following arguments. The temporary copy lent to the call cannot be retained in a link. | Execution of shared and mutable passages, call with temporary copy and rejection of conflict in the following argument. |
| E6 and E7 | Durability of references when leaving and coming from by box. | Initial cycle limit, lifted in the current cycle below. |

<a id="cycle-courant-des-tableaux-et-références-stockées"></a>

### Current cycle of the tables and references stored

The historical lines above describe the previous cycles.
The remaining deviations are recorded in the following table:
FIXED_ARRAYS_VALIDATION.md.

| Rule | Invariant and interactions | Current evidence | Limite |
| --- | --- | --- | --- |
| E2 and E4 | Pre-access control and sequence of effects | Negative indices, interlocked indices, dynamic bounds, immutable guard, static terminal on immutable let, reset effect on index, terminal mutation | Extreme sizes not covered |
| E3 and E5 | Explicit copies and type retention, including zero | Ordered literals, shared repetition, typed empty tables, mutable copy refused, list templates | mut() explicitly excluded from the prototype |
| E6, B4a and D1 | Sustainable parents and targets during calls and transfers | Local, temporary reborrowing, ordered arguments, function and loop returns, multiple provenances | Verified reallocation for types and modes retained; more complex paths still partially covered |
| E7 and B4 | Suspension until last use and distinction of boxes | Re-borrowing of stored reference, dynamic exchange, dynamic replacement, old capacity rendered, replacement by a re-borrowing of another box. Re-borrowing async relayed, mutable and shared re-borrowing of a stored mutable capacity, join and EAGAIN. Accessible neighbouring case, competing access and swap of the reserved box refused. Omission of the re-borrowing link detected. Dynamic index via relays with two possible pools, discharges on both boxes and pools, terminal control and native selection for single and interlocked lines. Omission of a detected origin | No independent model of lifespans of reference tables |
| E7 and B4 | The reborrowing relationship survives at a junction | Accepted program and rejected variant after conditional replacement between two boxes | Generation of partial junctions |
| E7 and D1 | Transferred reference tables retain sustainable targets | Branch and loop outputs, replacement of an ancestor receiver, local targets refused, continuous recovery | Recursively followed reference containers; depth and combinations generated still limited |
| E7 and contracts | Sources of results, source requirements and post-conditions by box | Table and reference return, relays, opaque calls private to bodies and tables of inference, replacement via alias and projected line. Capture shared by an async factory relayed, before or after replacing the box. Join, drop, reset and mutation of the order of resolution exercised | Large interactions not covered |
| E7, B1, B2 and B4 | A line lent does not suspend the capacities of other lines | Refusal to borrow the mutable target of an unloaned line; modification of a line retained by two calls | Dynamic conservative projection; no independent life-span model |
| E4, B4a and A5 | Destination remains valid after the effects of the right side | Writing contract via container and via &mut Int; result of the rejected target even without following use | Paths chosen; no formal evidence |
| E6, V4 and D1 | Reassigning a loan changes the variable target and keeps old reborrowings | Mandatory mutation, identical type/mode, local and temporary target refused, old reborrowings usable, containers and resets, reassigned parameters, branches and continuous/break, self-reborrowing loop | Static conservative checks; no general evidence of convergence |
| E4, E6 and E7 | A reference stored to a line keeps its type, its terminals and the borrowing of the whole table | Reading/writing, shared copy, replace/swap, relayed returns and opaque contracts, local refusal, indices evaluated once, model of 40 seed operations 20261106 | Values or reference lines; see recursive cycle below, without complete general lifespan model |
| E7, reset and enums | A field loan also keeps the reservation of the bearer | References stored after call, mixed result box/field, access to the porter, drop and resets refused before last use | Historical models without reference tables |

<a id="cycle-des-lignes-contenant-des-références"></a>

### Cycle of lines containing references

| Rule/profile | Invariant, Premises and Interactions | Evidence executed | Limites |
| --- | --- | --- | --- |
| E7_TREE — E4, E6, E7, B1–B3 | Domestic borrowing remains active with its capacity, even when only an external reference is named | Reading and writing tests, mutable reborrowing, original reference suspended, separate access after last use, checking of indices before effects; mutation removing detected domestic loans | Synchronous model, prototype types |
| E7_TREE_CONTRACT — B4, B5, E7 | The contract retains the container and each internal reference; the modifications reach the storage actually targeted | Opaque return and relay, update via alias and shadwing, line reference replacement and return of the old, contract readonly forged refused; inline field borrowing installed by relay in an injected box or line; content mutations and propagation detected | No formal evidence of completion of contracts |
| E7_TREE_PROJECT — E4, E7, B4, D1 | A returned line retains its positions in the source container | Counter example where verify_program accepted a reset that compile_source refused, corrected remapping, refused both internships and detected mutation | Ambiguous projections gathered in a conservative manner |
| E7_TREE_DROP — A2, A5, B1–B5, D1 | Drop/reset does not destroy any target or carrier still used by a descendant | Separate pools, last use per inner path, enum and target carrier, reset effect in the right, dynamic targets; independent model of 12 drop windows, depths 1 to 3 | 6 admitted cases executed and 6 refused; no general evidence for all depths |
| E7_TREE_EFFECT — B4, D1, T5–T11, E7, A2/A5 | Consumption of the outer container does not lose the modifications of its borrowed lines | Explicit transfer, replacement of pointer after writing, relay and temporary argument; separate allocations in the same pool, premature drop refused to both courses; specific mutations detected | Contract conservative, no complete proof of all transitive effects |
| E7_TREE_FLOW — S4, S5, T5–T11, D1, E7 | Transfers, branches and recoveries retain all possible targets | Branch results and loop with receiver, continuous/break, local return refused, conditional targets and source union | Convergence and arbitrary paths remain partially covered |
| E7_TREE_VALUES — E3–E7 | Copy shared, replaced and swap keep the destination graph without duplicated mutable capacity | Independent index model: 24 operations, seed 20261107, plus models from previous cycles | This model compares values, not all lifespans |

The current global suite passes: 909 separate tests. The 90 targeted tests
go under UBSan to -O2 (101 accepted invocations and 194 refused).
Fifteen mutations are detected: 8 undue acceptances, 6 false refusals and
1 incorrect runtime behavior. The propagation mutation first survived
the redundant scenario; the pointer replacement exposes its necessary effect.
The 9 tests of the reservation diagnostics are taken under PYTHONHASHSEED=0 and 1.

The FIXED_ARRAYS_VALIDATION.md report describes the two confirmed differences between
verify_program and compile_source, corrections, templates and limits.
The sources, groups and results achieved are identified in
validation/fixed-array-current-{global,suite,mutations}.json. Substitutions
are replayable with validation/run_fixed_array_mutations.py. No template
no claim is made for complete independence from lifespans or general proof of security.


<a id="conception-asyncmultithread-et-retrait-de-reset--4-novembre-2026"></a>

## Async/multithread design and reset withdrawal — November 4, 2026

Reference: [ASYNC_MULTITHREAD_RULES.md](ASYNC_MULTITHREAD_RULES.md).
Rapport : [ASYNC_DESIGN_CYCLE.md](cycles/ASYNC_DESIGN_CYCLE.md).
Lines P distinguish the executed scenarios from known limits.
Historical synchronous profiles do not constitute evidence for
The async extension PR1 is checked on the default profile, with a
separate historical profile for tests that perform reset.

| Rule | Behaviour and Invariant Targeted | Interactions | Scenarios to be checked / limits | Statut |
| --- | --- | --- | --- | --- |
| AS1 | explicit async fn, .await and yield | S1–S5, I5 | Declarations, yield and .await executed, including in the Int-comparable yew and the handle matches. Suspension refused in ordinary fn. Short circuit of && and || with waiting and effects on the verified right operand. while and loop suspendable with break, continuous and result Int, task or handle exercised. Memory state transported between iterations still restricted. | P |
| AS2 | Inactive creation and immediate capture | B4a, AS15, AS16 | The initial sub-assembly refused dynamic captures. Their current take-up is detailed in AS15. The mutation confuses type and provenance detected. The contract-recognized &str & &u8 synchronous returns after all possible targets are reduced to static arguments. The first check limited to static storage refused mixed sources. The mutation ignoring targets is detected; the current dynamic captures are di-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d-d- | P |
| AS3 | Instance stockable, non Copy, transfert explicite | T1–T11, D1 | Scalar task named non-Copy, consumed by drop or await; explicit transfers between receivers and tested telescopes, down injection in async and <- tested restitution. Renaming, spawn and drop from a descendant require explicit transfer to each level. Synchronous loop outputs by break <- and if branches or synchronous match transferring a task or handle. Consumed, shared and mutable d-enum match, and playful Join Result match. Source of the attached allocated results, rejected local pools and failed launch tested on both branches of if. Transferred task synchronous parameters exercised for scalar captures and Int transferred allocations. Task parameter with mutable | P |
| AS4 | Start by wave and single consumption | S4, B1–B5 | Waiting for a direct call or task named Int/Void, including in both arms of a handle match. Resumption of the chosen arm and single consumption verified. Direct expectation of a task calculated by block, if or loop. Results Int, &mut Int, <- Int and Void verified, including union of the returned catch and re-use of the slot. Calculated void expected as instruction; implied abandonment of an Int or Result refused. Result Bool by waved from an inactive task, relay and condition. Inference in an unannotated connection from the continuing arms, including via a local Bool to an arm. Bool/Int Join results expected in if | P |
| AS5 | Creation from ordinary fn and task return | B4, D1, AS7 | Nominal return <- definition async from synchronous fn, with scalar or borrowed catches followed by contract. Two forms of return and relay tested, including catches transferred from an injected pool or parameter allocation. Local pool refused. Capture of a &int detached from a shared field relayed by contract, with destruction or consumption of the carrier before spawn. The capture taken before re-allocation keeps the old target; after conditional re-allocation, the two possible targets are protected. Mutation of the tracking detected by re-use of the slot. | P |
| AS6 | Type generated specific to the async definition | I5, P8 | Two distinct C states of the same signature and different sizes executed under UBSan; Int/Void linear functions. | P |
| AS7 | Super pool and automatic injection of state pools | I2, A1–A3, P8 | Super pool C initialized before hand. Crust synchronous and async calls go through the factories of the type of task. L-reuse calls the C factory generated for a pool of capacity one. Conservative Borne from synchronous locations and parent states; directive async_pool_sizes; explicitly bounded cycles. Indirect creations through auxiliaries and methods contribute to the graph and terminals by contract; configured cycles and eight parents of three children exercised. Omission of this contribution detected after reinforcement of a first test that masked it. See ASYNC_CAPACITY_CYCLE.md and NATIVE_SYNC_CALLS_CYCLE.md for | P |
| AS8 | Persistent status and static monitoring | B1–B5, E2–E7 | Int, &Int and &mut Int and temporary scalar captures kept through the repeats. The capture pointer is reread after yield from the thread launched. The sources of the reassignable views in the loops are expanded until stabilization; the generated state is issued once. Validation repeats do not repeat task creations in the C. | P |
| AS9 | Stable storage through suspension and thread change | B1–B5, P3 | ABI C checked on separate threads. A child borrows the Int field of the parent state and modifies it after yield. Mutation replacing the address with a detected copy. | P |
| AS10 | Result extracted and then cleaned before waiting back | L1–L7, T1–T11 | The registrant is the registrant of the registrant, the registrant is the registrant of the registrant, the registrant is the registrant of the registrant, the registrant is the registrant of the registrant, the registrant is the registrant of the registrant, the registrant is the registrant of the registrant is the registrant of the registrant is the registrant of the registrant is the registrant is the registrant is the registrant is | P |
| AS11 | No reference returned to destroyed state | D1, B5, L2 | Direct return or re-borrowing of an accepted &Int or &mut Int parameter after yield. Return of a reference to a rejected room. Relays by waiting and by link followed up to the parameters of the first call, including after block, if or loop that chooses a borrowing task. &str and &u8 views returned from the &String or &mut String catches with retained provenance from the caller; return from captured refused. Return after join on a local string refused even when his pool is injected. Agregates still open. | P |
| AS12 | Source of income deducted and retained | B4–B5, D1, T5 | The rendend & &u8 by direct wait, wait for an async and join blocking handle. UTF-8 captures that can contribute to the return remain reserved after join, including via a synchronous contract. Capture only read released after join, conditional rendends stored, targeted historical reset and detected mutation. The rendend selection is relayed by a direct call or by a task named by call. Projection also verified via a launched and expected drive, with union of the provenances of the Ok and Err arms. Projection via a task calculated by if, match, block or loop. The rendends are separated by an exclusive rendend & regist | P |
| AS13 | Scope boundary and pool duration | A2–A3, D1 | Task output with borrowed target or transferred capture pool from the exercised parent. Output with local target or pool refused. Capture of an inline field via two mutable reborrowings and a synchronous relay. Child transfer → accepted parent if the porters survive and refused if an intermediate porter is local, even if the result of the task is scalar. Omission of control of these porters detected. | P |
| AS14 | Destruction before start-up | L1–L7, AS10 | Drop and end of the scope clean up inactive instances. Re-use of a capture slot -> Int after drop and simulated failure of the launch. Omission of the detected cleanup. Int capture imported into an async arm and then returned to a Void task: unique destruction to wait or inactive drop. Explicit return of import to the verified parent. Int held by block, if or break <- async, with mandatory return on continuous and re-use of the slot after join. Break <- without receiver issues a warning; the marked return is controlled at the exit, after the last uses of the loan. Explicit re-introduction of an Int held in the frame | P |
| AS15 | Incompatibility of the captures prohibited from creation | B1–B4a | The defaulted &st view has been validated from a local or a shared random-debt array. The defaulted output is a local or a shared output. The defaulted output is a local or a shared output. The defaulted output is a local or a shared output. The defaulted output is a second-debt array. The defaulted output is a second-debt array. The defaulted output is a second-reservation mutablity. The defaulted output is a local or a local-debt array is a single-debt array. The defaulted output is a direct-debt array is a child-debt array is a child-deb* The drop is refused before join and during the use of the returned view. Two mutations of the reborrowing detected. A borrowed arm keeps its reservation until join and the mutation that erases the proof of return is detected. The deactivation of the proof at the junction is detected. The return of a task reconstitutions the reservation of a canonical mutable parameter. Drop forejoin and continuous resumption with two sources borrowed exercised. Mutations of the contract and fixed point detected. Constraints d-d-alias d-a-str propagated, mutation of its provenance detected. Cut and borrow d-byte projected from the synchronous parameter and reset by continuous resus | P |
| AS16 | Separating capture effects of body effects | B4, L6, AS2 | The mutable capture immediately reserves the target. The body does not execute to the inactive drop or in case of simulated launch failure; the successful join makes visible the mutation. | P |
| RT1 | Main toujours synchrone | S2, RT5 | synchronous hand can launch and join an Int/Void task; async hand refused. | P |
| RT2 | Generic Runtime and Scheduler interface generated | AS6–AS10, MT7 | Super pool and built-in recovery, extraction and cleaning callbacks. Internal C-interface of launch and waiting on join, await, closure and launch error. Contouring of callback to closure detected by mutation. Public installation and policy of recovery open. | P |
| RT3 | Default Scheduler, Explicit Replacement | RT2, RT4 | Automatic pthread controller. Injection tested via internal C input points. Direct installation in hand before validated launch, not implemented. | P |
| RT4 | Spawn delegates to the scheduler; only one execution per instance | AS9, MT1–MT8 | Current policy: a new thread per launch (permitted but not imposed by RT4). runtime::spawn from hand and from a linear async body, with creation of thread verified by oracle pthread. Direct transfer of a task calculated by call, loop, if or jawn match depending on the context. If async keeps the union of the catches, including through yield; join match test Ok and Err. spawn_blocking is propagated up to the separate callback of the scheduler in both backends; see SPAWN_BLOCKING_CYCLE.md for tests and limits. | P |
| RT5 | Handle consumed by join blocking or wassuant | AS4, AS10, MT6 | Join blocker and waiter integrated for Int, Bool and Void, with single consumption. Bool kept in Ok direct and Named Result, including after suspension. Mutation of detected type. Oracle of availability, success and simulated failure of launch. Expectation of a handle chosen by if in an async body, result named or directly analyzed by match, mutable capture retained on Ok. Spawn and wait chain: single launch verified after forced suspension, mutation that restarts detected. Synchronous join on temporary handle from spawn or if, with contract-allocated return and re-use of slot. Blocking_join effect transmitted by contract: accepted behind auxiliaries in a native block, refused | P |
| RT6 | No cancellation; business error in T | AS10, MT3 | Simulated EAGAIN failed for join and await. Two transferred catches destroyed once, reused in two pool capacity one, mutable capture intact. Omission of the detected cleaning. Imbricated result loom tested under AS10. runtime::Error and the LaunchFailed pattern are integrated into the covered homeowner matches and signatures; the standalone values are integrated into the sync/async, loop and drop links, calls and returns. See RUNTIME_ERROR_VALUES_CYCLE.md: 19 binary and 27 refusals per level, four targeted mutations detected after strengthening oracles. The general forms of Result remain open. | P |
| RT7 | Each handle must be explicitly expected; transferable obligation; drop/abandon refusals | AS14, MT3, MT5, U1 | Sync/async controls and path tests in `test_handle_obligations` See HANDLE_OBLIGATIONS_CYCLE.md. The former oracles of abandonment no longer test a Crust operation admitted; they remain historical internal C tests. | P — cases executed and cycle limits |
| MT1 | Reserved mutable borrowing until established termination | B1–B5, AS2, RT5 | The registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of the registration of | P |
| MT2 | Shared readings and multiple reservations | B1–B5, RT5 | Two tasks read the same Int with the caller under UBSan. Writing, drop and mutable borrowing refused after a single join and writing allowed after both. Two mutations of the verifier detected. Two workers also share a target from the same writer via a detached field. The first join, including on Err, does not make the writer accessible. Two results of named join extend the reservation beyond the two joins until the last use. | P |
| MT3 | Evidence by road before destruction of addictions | S4–S5, L1–L4, RT6–RT7 | Loss of handle with local capture refused. Early return of the Err arm accepted after waiting for the other child and refused without this expectation. The only continuing paths of the hand games and the IFs to compare Int participate in the junction. Async loops with cleaning at each iteration. Stable company and separate exit states of the entrance. Expect an outside worker on two exercised break outputs, unattached exit and false test of unattached while refused. Break, continue and return before waiting for a local worker refused. Open more general contracts and connections. | P |
| MT4 | Children with stable parent status | D1, AS9, MT3 | The registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of the registrant of | P |
| MT5 | Contract of handle retained targets and sources | B4, D1, A2–A3 | A reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, a reverse-action, | P |
| MT6 | Result keeps the returned loans | B4–B5, AS12, RT5 | &Int and &mut Int transported in the .await Result in async context. Premature script rejected before match and in Ok. Simulated Err releases target on this path. Synchronous join tested with direct match, Named Result, Drop and Simulated Err. Result &Int or &mut Int d'un table plate de références, transmitted by await and then join. Precise constant projection, conservative dynamic index. Mutation that keeps all boxes for a constant index detected. Return and relay synchronous after direct creation then join, shared and mutable. Dynamic index and backup target on EAGAIN kept. Mutation of projection in the detected contract | P |
| MT7 | Metadata from competitive safe pools | P8–P9, L1, AS7, RT7 | Atom tickets for task states. Cursor, index and mutex-protected data slot links in the C multithread. Int capture drop competing and 16,000 native four thread cycles under UBSan. Growth fronts and region classes are protected by a lock taken before slots. Oracle C with two threads on a reserve of 257 bytes and competing recycling of regions. Mutation detected by cursor overflow. ThreadSanitizer not available in the environment. Removal of the detected lock. L-Loricle RT7 also exercises four competing recoverers for a single abandoned slot, over 32 cycles. Vectors and regions shared between open tasks. | P |
| MT8 | Transfer and sharing deducted structurally | B1–B5, P9, E7, D1 | The following are the following: absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing absorbing | P |
| PR1 | Reset removal, drop cleaning and scope | A5 historique, L1–L7, P8–P9 | CLI and API Python refuse reset by default; Drop and Clean at the end of the scope executed; C default without reset functions and direct oracle of slots executed under UBSan. The historical profile requires an explicit option. | P |


<a id="data-stacks-et-régions-grandissantes--4-novembre-2026"></a>

## Data stacks and growing regions — 4 November 2026

Normative reference: [GROWING_REGIONS.md](GROWING_REGIONS.md).
Cycle report: [GROWING_REGIONS_CYCLE.md](cycles/GROWING_REGIONS_CYCLE.md).
G2–G12 have partial coverage in the compiler or C emitted.
G1 remains N. Historical evidence from fixed pools does not
This is not evidence of the regions or both fronts.

| Rule | Behaviour and Invariant Targeted | Interactions | Scenarios to be checked / limits | Statut |
| --- | --- | --- | --- | --- |
| G1 | Early booking without advancing the construction or moving the value | P3, T1–T11, D1, A2–A3 | Rectilinear climbs, branches of if and nominal match and loop suffixes that end with transfer break, with Int on data stack; String and Vector descriptors, structures and arms d'enum reserved in their pools; an early annotated region in an active or created class if the temporary ones have the same template, cold opening with return to the ordinary placement in case of failure, anticipated down front with a single temporary Vector unannotated and early dedicated range if the temporary ones occupy the necessary fronts; construction effects tested. Non-consumption match with String region and even pool on both arms, different sources and lack of space exercised. | P |
| G2 | Growth at the top and restoration only after cleaning | P4, L1–L5, S4–S5 | Restitution of the cursor reserved by the front, under model C; placement of scope and open transfers. | P |
| G3 | Two opposite sliders, one permitted front | P1, P5, P6 | Two active C fronts, stable addresses and logical order of the exercised Vector descendants, including slice subdivision. TX21 imposes String views in ascending physical order. String uses a rising front or region, then a dedicated range if the rising front is occupied. Vector views<u8> can use the descending direction. | P |
| G4 | Collision = out of space, alignment controls and calculations | P1, P5, E1 | Accurate adjustment, alignment, collision and extreme size demands tested. Unfair logical capacity with co-existence region and fronts exercised under UBSan at O0 and O2. Without alignment of the region boundary, poorly aligned Cell access replicates. | P |
| G5 | Substack region separate from block slot and descriptor | P8, G3 | Internal Cursor and Fixed Capacity by Region. Integrated String and Vector Descriptors, including pre-construction reservation and re-use after cleaning. | P |
| G6 | `#(directive, stack_region_max_size=1M)` front scope, boundary by region and not by stack | P2, I1–I4, G7, U1 | Mandatory categorised syntax, inheritance and limits after transfer exercised at O0/O2 with UBSan; 3 mutations detected. Provisional binary M/G; blocks annotated async still refused. [Cycle guidelines](cycles/DIRECTIVES_CYCLE.md). | P |
| G7 | Replaceable inheritance; limit retained at transfer | P2, T1–T11, D1, A2–A3 | Lexicon inheritance and substitution performed by the annotation test, with call isolation and restoration after block release. Observer re-in compliance with Compiler.statements. Thong transfer without storage change. | P |
| G8 | Regions of the same template managed as pool slots | P4, P8–P9, G6–G7 | Model C checks the cursor preference, the re-use of a hole at the limit and the removal of the suffix from the index; classes in a common reserve, recycling of the empty classes and dedicated fold tested. At the limit, the transfer reservation counts the holes in the pool of descriptors and in the class of regions. It leaves the necessary number of places to temporary ones. Two mutations detected. A Crust program with construction and push_str literal reuses these holes before the transfer. The case with borrowed view exercises the ordinary placement. | P |
| G9 | Current and dedicated stack, without hidden heap or terminal overrun | I2–I3, P7, A2–A3 | C placement on compatible front or class, then dedicated range; limit and verified addresses. Thong uses a rising front or region and folds on a dedicated range when the rising front is occupied. Vector can exploit both fronts. | P |
| G10 | Destruction before reuse; no recovery of living value | L1–L7, P4, P8, PR1, MT7 | The runtime refuses a closed with live front and a false descriptor; content cleaning and scope integration open. | P |
| G11 | Separate reservation of commitment; performance to be measured | P1–P2, G8–G9 | Measurements on macOS arm64 of the mmap, page defects, RSS, recoil and reuse with or without regions. Comparison of mutex overall and mutex by datastack from 1 to 8 threads, with distinct bands. Closure and interthread return performed under UBSan. ASan blocked on a minimum witness with both Clang. Thresholds and free_pages exercised on the two datastacks under UBSan, including restitution around a region transferred and async outputs. Integrated measurement of the fixed restitution on a programme of 300 iterations. Integrated regional flow rate to be measured. [Report](G11_DATASTACK_BENCHMARK.md). | P |
| G12 | Stability does not exempt from verifying borrowings and sources | B1–B5, D1, E7, AS9, MT1–MT8 | Growth model and Rust controls used under UBSan: vector by await and spawn/join, string by spawn_blocking/await, entry by HashMap after transfer, growth and re-employment. Borrows carried by result and life of pool controlled by refusals. HashMap async by value and captures possessed of runtime::thread validated under UBSan, with stability, refusal of life and re-use after failure of launch. [Report](cycles/CORE_COMPOSITION_CYCLE.md#g12--stabilité-emprunts-et-provenance) | P |


<a id="structures-et-méthodes--5-novembre-2026"></a>

## Structures and methods — 5 November 2026

Standardisation reference: [STRUCTURES_METHODS.md](STRUCTURES_METHODS.md), and I6
in [LANGUAGE_RULES.md](LANGUAGE_RULES.md). Rapport :
[STRUCTURES_METHODS_CYCLE.md](cycles/STRUCTURES_METHODS_CYCLE.md).
The initial record classified ST1–ST18 and ME1–ME4 as N. The following lines give the current partial cover.
I6 is a design objective examined (A), without general evidence.
Examples of design remain obligations with evidence of
indicated by the lines below. Cases of field displacement and partial cleaning have been removed
by the final decision ST15; they are not acceptance objectives.

| Rule | Behaviour and Invariant Targeted | Interactions | Scenarios to be checked / limits | Statut |
| --- | --- | --- | --- | --- |
| I6 | Bringing intent and readable code together; reporting fragile implicits and notations | I1–I5, ME2–ME4 | Design objective; no general evidence of intent/code or IA generation evaluation. | A |
| ST1 | Complete structure and fields directly contained in a slot | V1, P8, D1 | Construction, transfer and destruction of a flat structure with a single slot in `test_foundation_rules.py`. | P — structures nested in a single slot, defects and named initialization of verified terminal fields |
| ST2 | Pool.new built T, type inferred or annotation verified | I2, A1–A4, P8 | Transfer, re-use of slot, C identical with compatible annotation, incompatible type refused before generation in `test_foundation_rules.py`. | P — Pool<Int> and flat structures, annotation of allocation links |
| ST3 | Int=0, recursive defect; no default reference | V1, B1–B5 | `Pool<Int>.new()` given 0; fields Int omitted initialized to zero and defaulted in `test_foundation_rules.py`. | P — recursive defect Int, refusal of a nested reference without a target |
| ST4 | Named fields, omissions with default and left arguments → right | B4a, ST1–ST3 | Written order, duplicates, unknown names and reset during the evaluation tested in `test_foundation_rules.py`. | P — Int fields and Int references, direct or pathnamed, written order and defaulted interlocked omissions. Backend Rust: new(), new({}), contextual and nominal fields, recursive defects and refusal of an omitted A<T>. Direct construction of the immediately consumed literal verified in the generated C. |
| ST5 | Int in place mutable access is required | V4, B1–B5, L1–L6 | Stable address, embedded write via &mut, global loan and reset of the holder in `test_foundation_rules.py`. | P — Int direct and interlocked fields, Int field loans and bearer loans |
| ST6 | Independent reservations of separate Int fields | B1–B5, L6 | Call with two disjointed mutable loans, same conflicting fields, shared aliases and premature destruction in `test_foundation_rules.py`. | P — champs terminaux Int |
| ST7 | Reservations by interlocking and conglomerate road | B1–B5, E7 | Interlocked, disjointed paths, access to the refused bearer in `test_foundation_rules.py`. | P — borrowing of substructures and indirect targets to be covered |
| ST8 | Contract of returned field targets | B4–B5, D1 | Union of paths via opaque relays, fixed table return and updating of boxes injected in `test_foundation_rules.py`. | P — champs terminaux Int |
| ST9 | Borrowing of the compatible argument before the contract is put into effect | B4a, B4, ST6–ST8 | &mut call to the refused bearer during a field shared loan in `test_foundation_rules.py`. | P — bearer and return of fields Int |
| ST10 | Reference field reassignment without destruction of targets | B1–B5, D1 | Copy of the old target, stable address, union of return targets and local target refused in `test_foundation_rules.py`. | P — direct carriers and local borrowings, shared and mutable fields reassigned by contract, relay, junction and verified life; re-debt of the reassigned mutable field verified in direct result and fixed table; selection of several relay-propagated carriers, with direct or call-assignment, and distinguished local carriers in the same pool, including under lexical masking |
| ST11 | Reborrowable loan reserves the capacity field | B1–B5, ST7 | Two disjunct fields reborrowed, accessible brother, same path and premature drop/reset refused in `test_foundation_rules.py`. | P — Int &mut fields and &mut projections to structures. Two projected fields are eligible in both orders, two projections of the same field are refused. |
| ST12 | Contract retains target and reservation of the mutable field | B4–B5, ST8–ST11 | Conditional return by relay, return table, brother Int accessible and reservation of the carrier and target in `test_foundation_rules.py`. | P — direct or table return after reassignment of the covered field, reset interprocedural of the targets of still conservative brother fields. A call returning the first of two nominal reborrows releases the brother field and keeps the reservation of the returned field. |
| ST13 | Shared reference returned detached from the holder storage | B4–B5, D1 | Drop and re-use of the holder slot, direct return and fixed array, protected external target and rejected &mut copy in `test_foundation_rules.py`. | P — fields of borrowed or consumed porters, relays and re-use of slot. Explicit scalar reading via an interlocked field before and after re-allocation, including via contract. Drop, reset and re-borrowing of premature mutables refused. Explicit shared re-borrowing followed up to its initial target after re-allocation, destruction and re-use of the porter. After conditional re-allocation, the two possible targets remain protected by the relayed contract. |
| ST14 | Reference to inline field keeps the carrier | B4–B5, D1, A2–A3 | Drop of the holder and return after transfer of the holder refused in `test_foundation_rules.py`. | P — champs terminaux Int |
| ST15 | Non-Copy extraction and partial initialization prohibited | T1–T11, L1–L6, ST1 | Dismissed direct &mut field displacement, whole transfers and reborrowings in `test_foundation_rules.py`. | P — initialization interlocked by tested terminal fields, conditional variants to cover |
| ST16 | Complete replacement: build before destroy | V3, L1–L6, P8 | Two addresses, re-use of the old slot, diagnosis with capacity one and future loan refused in `test_foundation_rules.py`. | P — direct replacement by manufacturer transferred |
| ST17 | Copiability deduced recursively, explicit copy | E3, E7, MT8 | Independent interlocked fields, shared reference retained and nested field refused in `test_foundation_rules.py`. | P — types of fields currently supported |
| ST18 | Local copy on the recipient data stack; Pool.copy explicit or copy via pool of origin for pool allocation | I2, B4, P8, E3, ST17, D1 | Separate slots, explicit recipient pool, conditional origin and capacity in `test_foundation_rules.py`. Independent local copy, re-use, block transfer, continuous/break, return and copy of a parameter borrowed via two calls. | P — local copy executed at O0/O2 with blocker UBSan; shared references retained, premature drop/reset and non-copy fields refused; two targeted mutations detected. Copy of existing replayed pool. See STORAGE_DESIGN_CYCLE.md for exact range and remaining shapes. |
| ME1 | Recipient signature in impl, inherited function rules | B4, V4, L1–L6 | Qualified contracts, three self modes and effects resolution after if, match and loop in `test_foundation_rules.py`. | P — methods of structures and integrated homonyms distinguished by type for named recipients, including join and split_at_mut. Axiety by type, contract of return and native cut of the verified vector. Both homonyms are also checked in a mutable match arm on a projection, with return of loan out of the match and relay by contract. |
| ME2 | Automatic borrowing of receiver without implicit consumption | I1, I6, B1–B5, V4 | Reading, mutation and reborrowing via relay or result directly in argument in `test_foundation_rules.py`. | P — named recipients, reservations of tested arguments |
| ME3 | Method name distinct from each type field | I6, ME1–ME2 | Field/method and duplicate method collision rejected, name shared between types accepted in `test_foundation_rules.py`. | P — structures |
| ME4 | A method declared with `self: T` moves the receiver as its first argument. | I1, I6, T1–T11, ME1 | Both compilers pass the named receiver, its return, and its destruction under fatal UBSan. They reject reuse, use in a later argument, a borrowed receiver, and movement during an active loan. | P · Crust also handles records with fixed scalar-array fields and compact scalar-array results. [Array receiver evidence](cycles/CORE_COMPOSITION_CYCLE.md#sha-256-with-crustc). [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#by-value-method-receivers-and-diagnostics) |


<a id="utf-8-str-char-et-string--5-novembre-2026"></a>

## UTF-8, str, tank and thong — 5 November 2026

Normative reference: [UTF8_STRIINGS.md](UTF8_STRINGS.md).
Cycle report: [UTF8_STRIINGS_CYCLE.md](cycles/UTF8_STRINGS_CYCLE.md).
TX1–TX20 have partial coverage. The ratio separates the tests
The first is the introduction of a new system of information technology.
The evidence from the historical tables/pools does not check the UTF-8 invariant.
The open points are reported; the first case of Vector remains only
proposed and not added as a normative decision.

| Rule | Behaviour and Invariant Targeted | Interactions | Scenarios to be checked / limits | Statut |
| --- | --- | --- | --- | --- |
| TX1 | tiny str, UTF-8 view and static literals | I2, D1, L2 | Returns and calls, static C data, explicit length and internal zero byte in `test_foundation_rules.py`. | P — vues statiques |
| TX2 | u8 separate from the independent Unicode tank | ST17, E3 | Readable continuation octet; passage and return of u8; Int coercions and loan/value refused. char circulates independently of its view in parameters and returns. Fixed tables of u8 with bounded constants, calls and reborrows. Async u8 contexts (capture, annotated link, return, Vector writing and replace_byte) accept a bounded literal; an Int variable remains refused without conversion. Native execution of values and refusal of terminals outside 0–255. | P — byte arrays and static views; contextual literals exercised at O0/O2 with fatal UBSan |
| TX3 | explicit byte_len and utf8_len | E1, G4 | summer = 5 bytes; widths of tank 1 to 4 compared to the independent model. | P — byte_len and utf8_len tested from Crust |
| TX4 | Text cut explicitly borrowed on UTF-8 borders | B1–B5, D1, E2, I6 | Four forms of terminals, function return, order of effects, views without copy and mutations of both guards; invalid terminals refused or diagnosed. Static async cutting with two suspendable terminals, verified in order. Static view produced by if, loop and handle match. Ok and Err paths exercised, Int branch refused and mutation of detected type control. | P — static storage, d-byte and string tables; failure policy validated by draft 07. try_slice synchronous: oracle of 144 beaches, multi-source contracts, drop/reset, identity of ascending and descending views, O0/O2 UBSan and three mutants detected. UTF8_TRY_SLICE_CYCLE.md : 124 regressions and the two UTF-8 models pass; aka Result and replacement of provenance exercised. Async extension: catch of Result, suspendable terminals, wait relay, synchronous join and hold of handle async, conditional origin and exclusion of catches used only as bounds. See second stage of |
| TX5 | Index simple retourne u8 ; &index donne &u8 | E2–E3, B1–B5 | Value, shared borrowing and visual re-allocation; order of effects; literal disability denied; native custody before dynamic access. Async reading after suspension of receiver and index. Continuity octet returned by join, dynamic guard and mutation inverting the effects exercised. Static borrowing &u8, re-allocation of receiver and relay to a task that de-references after yield. Mutation suppressing reading and capture of a dynamic target exercised. | P — static views and borrowings at [u8; N] or String |
| TX6 | char_at from index in bytes with typed error | TX1–TX5, E1 | 522 scalar values and all their bytes of continuation; empty text, negative index and end; mutations of detected guards; typed match, transfers and re-use of pool executed. Direct async match on static view, suspendable index and three verified exits. Decoding result named, copied and re-assigned, then read after yield. Capture by value and async relay verified after re-allocation of the original result and drop of decoded String. Incompatible families refused calls. Err(_) on both families is also allowed in synchronous; Option and Result remain distinct, removal of the support of the joker detected by mutation. Returns of both families via direct await, waiting for handle and join. Decoding status separate from the failure of launch, mutation of the internal status detected. Change of family refused and mutation of the detected control. Mutation ignoring the detected index. | P — instruction match and expression of UTF-8 results; reset aliased in a bound or argument verified by contract and transfer |
| TX7 | from_str requires exactly a Unicode scalar value | TX1–TX3 | Empty, multiscalar text and successful conversion for each scalar of the model; mutation of the detected length control; match and passage of the tank by function exercised. Direct async match of char::from_str with empty text, single scalar and several scalar. | P — Matching instruction and expression of UTF-8 results |
| TX8 | from_utf8 validates bytes and produces a view without copy | B1–B5, D1 | Validation C compared to the strict decoder of Python; identity of the view; local result, last uses and conflict writing verified. | P — fixed tables and slices of Vector<u8> in logical order, view without copy verified by address, return with source, refusal of mutation and Python model under UBSan; other forms of storage growing to be checked |
| TX9 | String encapsule Vector<u8> and guarantees valid UTF-8 | G1–G12, ST1 | Empty construction and UTF-8 additions in growing storage bytes; integration with open generic Vector. | P |
| TX10 | Thong slot and growing storage associated cleaned | P8, G1–G12, L1–L7, PR1 | Placement by annotation, transfer, destruction of storage before re-enactment of the slot and re-use performed. Cleaning and sub-views tested in synchronous context. | P |
| TX11 | push encode a complete tank after capacity control | G4, G12, B1–B5 | Shared encoder checked on widths 1..4; complete append, exact limit and exceedance exercised in the C. Async receiver reserved before a suspended char argument: other String modifiable, read and mutate the same String refused; mutation removing the detected reservation. | P |
| TX12 | Explicit &str view from String without copy | B1–B5, D1, TX4, AS8, AS11 | View and byte returned by contract, identity C, transfer after last use, refusal of transfer, transfer, destruction and early reset. In an async setting: immutable local view and byte, aliases, expected relay and calculated task; block results, if and loop keeping all possible sources. Refused early mutations and drop, re-used slots, returned to local string, rejected exit to destroyed local string. Re-assigned links, retained aliases, branches, break and last use within the exercised source scope. Projection to the caller from &String or &mut String, relays and synchronous contracts, handle transferred and byte from two sources exercised. Point fixes sources of | P |
| TX13 | push_str copies source text after full control | B4a, G4, G12 | Copy of &str, mutable access, capacity and identity of the content tested; copy from another admitted Thong, alias of the recipient refused. &str retained during push_str async, including block/if/coffee: auto-borrow refused, copy to other admitted Thong. Reservation from the beginning of the evaluation of a suspended argument: transfer and readback of the recipient refused, effects on a separate allowed source. Mutation omitting the detected reservation. A view of the parent whose last use is in a child block expires before the next reservation; use of view in the argument or after the protected addition. | P |
| TX14 | pop removes a full tank and returns Option<char> | L1–L7, G10, TX2, AS8–AS12 | None on vacuum, Independent Some, expression match, model of 120 transitions on front and region, reused suffix and blocking borrowing. In async: result preserved after yield, captures and returns Option<char>, join via contract, destruction then re-use of slot, failure of launch, result ignored and model Unicode of six texts. Condition in an argument and reallocation of results exercised. Family confusion and transfer under loan are refused; omission of control of borrowing and omission runtime of trunk detected. | P |
| TX15 | reset_byte validated before mutation, error without change | TX5, G12, B1–B5, AS2, AS8, AS12 | Continuation replaced if valid result; old u8, typed errors and unchanged content compared to the model. Async body: receiver reserved during suspended arguments, index saved before the second argument, result ignored executed once. Result<u8,ByteReplaceError> and payload u8 kept by yield, await, join and synchronous contract; independence after drop of the String and re-use of the slot. Seven transactions compared to the UTF-8 Python decoder. Direct match subject calculated by if, block, loop or nested match: unique type and evaluation exercised on both paths; bad branch type, bad pattern and active view refused. Changes in loan, backup and validation | P; O0/O2 with fatal UBSan; historical aliased reset in a terminal or argument verified by contract and transfer. Grouped replacement async: see TX16. |
| TX16 | replace_bytes validates the entire block at constant size | TX15, E1, B4a, G12, AS2, AS8, AS12 | In synchronous, fixed or relayed array, empty interval, terminals, UTF-8 errors, stable address and protected active view. In async, direct Vector slice<u8> and fixed table borrowing u8, including projected line, temporary copy and empty array. Indication and suspended terminals saved in order. Destination and reserved source with appropriate access. Ten Python transactions on two directions of the verified source natively, error without writing and atomic replacement of the block. Result<(),ByteReplaceError> distinct from the result u8 through captures, wait, join and contracts; re-use of the source pool before using the result, EAGAIN failure and typed match. Re | P — O0/O2 UBSan fatal. Slice links in the async bodies remain open. |
| TX17 | No u8 or index writing on String | TX9, TX15–TX16, ME2 | Gross and &mut d'octet script refused on String; read and shared borrowing executed. | P |
| TX18 | UTF-8 warranty without any guarantee of meaning; offset imposes new String | G12, ST16, I6 | Change in the number of fixed size scalar and stored address checked; insertion and offset out of API. | P |
| TX19 | String non Copy ; duplication in independent storage | ST17–ST18, TX9–TX13 | Copy of String refused; explicit duplication and independent destruction executed; integration with open aggregates. | P |
| TX20 | print accepts &str and char without implicit conversion | I6, B4, ME2 | &str and char display in `test_foundation_rules.py`, including the null scalar. Display of the tank in an async arm and directly after await. Display of littrals and static views captured after yield, with incorporated NUL. Mutation truncated the view to the detected NUL. Local connection and static cut relayed after yield. Suspended terminals evaluated from left to right. Invalid UTF-8 border refused by compiler or runtime depending on the source of the terminal. Confusion with Bool refused and mutation of the detected display format. | P — explicit display of static and borrowed views, including String |

<a id="fondamentaux-allocations-typées-et-vecteurs"></a>

## Fundamentals, typed allowances and vectors

Voir [FOUNDATIONS_AND_VECTORS.md](FOUNDATIONS_AND_VECTORS.md) and
[cycle report](cycles/FOUNDATIONS_CYCLE.md).

| Rule | Invariant | Interactions and evidence | Status and limit |
| --- | --- | --- | --- |
| F1 | Taille statique finie, indirections explicites | H1, ST1–ST18 | A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. A. |
| F2 | Comprehensiveness and coherent link mode | B1, B2, re-use of slot, source of references, possible call variants and join of values in `test_foundation_rules.py` | P — match consuming or by borrowing with Int results, tables, transfers and borrowings. Match expressions by borrowing also allow calls in local constructions, direct Void calls, explicit replacements of receivers, conditions and loops. Borrowing matches without result also allow explicit replacements and loop outputs. Void methods calls, reborrowing received in the arm and Int and &mut Int results to storage or target of a field via a typed projection method, with composition of reserved or detached paths in relays are verified under UBSan and transfer. Direct calls out of projection remain restricted in this form. An advance return is controlled by the function contract and excluded from the junction of the continuing arms, with cleaning](cycles/OWNED_RESULTS_CYCLE.md). |
| F3 | No use after invalidation on a path reaching junction | S4, S5, S5a, T9, T10, FLOW and LOOP_RESULT profiles. Masking, front break and continuous replacement, and return contract after assignment of references in `test_foundation_rules.py` | P — existing control forms, recovery and output after replacement of an embedded proprietary field of the same pool verified under UBSan and by mutation |
| F4 | Conditional assessment and orderly invalidation | B4a, B2, pool transfers, temporary cleaning and re-use of slots in `test_foundation_rules.py` | P — operators under Bool conditions and expressions, declaration, argument, return and possible displacement verified under UBSan; comparisons as parenthesed values and conditions followed by access by verified method or index; short circuit and comparison result mutations detected; conservative junction; construction of reference table with reset in a later element and line projection after evaluation of the index verified under UBSan and mutation |
| F5 | Int32 result representable or diagnosis before dangerous operation; as exact by type, try_from bankrupt | V3, B4a, mutable borrowing, pool, C under UBSan and division model; AS1, contracts, U1, L6 | P — as u8→Int and identities Int/u8 to O0/O2 under UBSan; 256 bytes compared to an independent oracle; Int→u8 refused even constant. u8::try_from checked on -2.257 and extremes Int32, relay, drop, re-use, await/join and targeted mutants. See INTEGER_CONVERSIONS_CYCLE.md. Other integer types not covered. |
| H1 | Stable address and unique cleaning from the original pool | T1, D1, A3 | A. absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; absorbing; a |
| H2 | Borrowing of the handle or its target, always initialized target | B1, B2, V4, H1 | P — vref and mut_vref on A<Int>, A<Point>, A<Vector<Int>> and A<String> verified under UBSan, with calls, drop, reset and mutation; ref and mut_ref of the typed handle with borrowing and replacement of A<Point>, relay, bad type refused and mutation detected, stable address and tested conflicts; replacement via &mut A<Int> tested; replacement via: remnants dered and remnants dered and remnants dered and remnants dered in the abstract, mutation of the unchanged branch detected, remnants dered and |
| H3 | Receiver modes and explicit element type | ME1–ME4, H2 | P — vectors on A<Int>, structures and field enums Int compares the content, verified under UBSan with rejection of another type and mutation of the tag; String, Vector<Int> and Vector<u8> compared on the initialized prefix; logical order between opposing fronts checked in C to -O0 and -O2 with UBSan and mutation detected; refusal of different types and reset with borrowing still used; consuming receivers -> A<Point> and -> Distinguished point by contract, relay, stable address and re-use under UBSan, mutated marker detected; order of vectors and protection of receiver during the effects |
| VE1 | Uniform and initialized boxes before reading | V2, H1, VE4 | P — VECTOR<Int> and remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; remob; |
| VE2 | A responsibility by hand, destruction before recovery | D1, L2, H1, VE1 | P — Pash of A<Int>, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb, remb |
| VE3 | Source preserved during rearrangement or extraction | V4, H1, VE1, VE2 | ab; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd; abd](cycles/OWNED_RESULTS_CYCLE.md). |
| VE4 | Aucune publication partielle ou hors borne | VE1, G4, B2 | P — local Vector try_push<&mut Int> verified under UBSan, Ok and Err with region C returned to a box, carrier reservation up to match and transfer; try_push local Vector<&Int> verified under UBSan on Ok with exact capacity, unchanged length on Err, loan return, reset refusal and transfer; try_push Copy and try_extend dun &[u8; N] or a direct Vector slice<u8>; region threshold, failure without publication, restitution and downward front exercised; bounded external reading in C with POSIX tubes; try_push A<Int> in match consuming verified with exact](cycles/OWNED_RESULTS_CYCLE.md). |
| VE5 | Tranches disjointes, emprunt parent suspendu | B2, VE1 | P — shared slice of direct or named bytes, reallocation and last use; transfer, drop, reset and local source output refused if view remains used; parameters and returns &[u8] via contracts, two sources, index bounded by the slice, copy of u8 or box loan; Int slices, contracts and indexation verified; split_at_mut Int and u8, local link, C partition and static suspension of the tested parent; mutable parameters and returns Int and u8, disjointed reborrowing and duplicates refused; explicit reborrowing of Int/u8 halves verified with return UTF-8, disjointed writing and transfer of provenance; chain of reborrow |
| VE6 | Initialization on the spot before borrowing | V2, B2, VE1, AS9 | P — Vector<Int/u8> sync/async, zero default, returns and relays Int/u8, yield/await/join, capacity, last use and re-use; see ASYNC_VECTOR_PUSH_NEW_CYCLE.md; other types and general expressions open |
| GR1 | No collision or change of address | G1–G12, H1 | P — two fronts from Vector and region boundary retained after transfer; annotated classes and unannotated fronts in the same range, collision, dedicated fold and delayed recovery verified |
| GR2 | Recovery after cleaning, without moving live objects | L2, G1–G12, VE2 | P — suffix and addresses on both fronts; Vector<A<Int>> destroys its elements before recovery and returns their slots to the original pools; stable opposite front, shared region and mutations detected under UBSan; other non-Copy elements not covered |
| TX21 | Continuous bytes and still UTF-8 | TX1–TX20, GR1, VE1 | P — String uses Vector kernel with contiguous bytes in ascending order; regions on the top, stability and re-use checked under UBSan; dedicated stack without annotation if the rising front is occupied, placement mutations detected |
| TX22 | Concatenation and explicit transfer of responsibility | TX13, TX21, H1, AS2, AS8–AS12 | P — merge executed between two pools; alias, missing transfer and reuse refused. Async body: source consumed and then destroyed once before the next suspension, re-used source slot, destination address retained. Argument obtained by await, block, if or loop transferred; source explicitly attached to the block. Destination returned out of the destroyed source pool, content compared to six Python concatenations. Success, EAGAIN and join contract exercised at O0/O2 with fatal UBSan. Mutations of cleaning and reservation detected. |


<a id="complément--directives-catégorisées-brouillon-06"></a>

## Supplement — Categorized guidelines, draft 06

Profil **DIRECTIVES** : `tests/test_growth_annotations.py`, methods of
`test_foundation_rules.py` and `test_owned_results.py` containing the directives.
Twenty targeted methods executed at O0 and O2 with fatal UBSan; three mutations
syntactic/digital. Lexicon inheritance, expression blocks,
The transfer and re-employment of T6, P3/P4 and U1 is carried out by P2/G6/G7.
The resolution of the features type was not implemented during this cycle;
its first implementation and its limitations are now described in
[TYPE_FEATURES_CYCLE.md](cycles/TYPE_FEATURES_CYCLE.md)Evidence of guidelines alone
do not cover I5/B4/B5 or ME1/ME2/ME4 for features.
Details, regression and limits: [DIRECTIVES_CYCLE.md](cycles/DIRECTIVES_CYCLE.md).

Additional U1 regression of the GUIDELINE cycle: 181 historical methods
(hand, calls/arguments and conditional expressions) successful after migration
fixtures to explicit use of owners; 34 unchanged methods
(growth runtime and proprietary uses) successful in the initial execution.
The traces of destruction/re-use remain checked.
not U1 and does not constitute general evidence of monitoring of usage.

<a id="type-features--brouillon-06-première-résolution-statique"></a>

## Type features — draft 06, first static resolution

Normative reference: [TYPE_FEATURES.md](TYPE_FEATURES.md). Evidence and limitations:
[TYPE_FEATURES_CYCLE.md](cycles/TYPE_FEATURES_CYCLE.md)The statutes are partial; the
catalogue of building methods and async interactions still to be completed.

| Rule | Behaviour and Invariant | Interactions | Evidence | Statut / limites |
| --- | --- | --- | --- | --- |
| TF1 | A structural method, complete signature and conforming receiver mode | I5, ME1 | `test_type_features` : declarations/modes/results; model independent of 81 combinations, 9 admitted and 72 refused; mutation of the detected result | P — structural methods; building catalogue remaining |
| TF2 | Constraint signatures, concrete storage; arguments resolved independently | B4, P8, ME2 | Refusal of fields/collections/pools/abstract annotations; Console/Journal accepted simultaneously; cache mutation detected | P — interlocked projections and signatures to be extended |
| TF3 | Direct and indirect requirements guaranteed by signature | B4e, ME2 | Alias, false branch, expression, equivalent/non-equivalent relay, uncalled function; abstract and indirect control mutations detected | P — Separate abstract controls of concrete memory checks |
| TF4 | Static resolution maintaining concrete modes, effects and contracts | B1–B4, L6, P8, ME4 | Shared/mutable/consumer recipients; single cleaning, re-use, historical reset after reading and refusal before future use; catalogue checked without abstract residual type | P — 21 native programmes under UBSan O0/O2, no general evidence |
| TF5 | Concrete result and origin retained, no implicit promotion | B2, B5, T6, A2, A3 | Shared/mutable/owner return, two relays, branches, address stored, pool too short refused, target reserved until last use | P — cases in which there is no concrete evidence; recursion and async not covered |

Regression of this cycle: 173 successful methods, then 36 of the cases of methods and
structures re-executed with injection of a feature and a generic relay
four targeted mutations detected. `Vector.len`
was opened at the end of this first cycle; it is corrected in the supplement
The draft 06 is not fully implemented.

<a id="complément-builtin-et-retours-concrets"></a>

### Building complement and concrete returns

Preuves : [BUILTIN_FEATURES_CYCLE.md](cycles/BUILTIN_FEATURES_CYCLE.md).

| Rules | Invariant / interactions | Evidence | Limites |
| --- | --- | --- | --- |
| TF1, TF4 | Full signature of integrated methods; no neutralization of effects | `test_builtin_features` : 36 signatures according to an independent source model, 2 admitted / 34 refused; mutation ignoring detected signatures | P — Catalogue wider than the operations carried out; `char.utf8_len` restant |
| TF3 | The operations already transformed by the parser require abstract guarantee | `try_slice` and `char_at` unsecured refused on name and function return; mutation of detected control | P — no exhaustive evidence of all forms of AST |
| TF4, TF5, B5 | Origins, mutable reservation, last use and source retained | `&String`, `&mut Vector<Int>`, tableau, `push_new`, cutting result, two relay pool; premature drop/mutation/reset of history rejected; mutation of origin detected | P — concrete cases only, no general async evidence |
| TF4, TX, VE, P8 | Cleaning, slot identity and UTF-8 result invalid atomic | `merge` cleans once, reuses at same address; pool builder keeps source; bad replacement keeps `é` | P — deterministic examples, not all the methods in the catalogue |

32 successful feature-type methods under UBSan fatal at O0 and O2; buildin module
Only: 18 native programs and 57 refusals. Targeted attacks: 173 methods,
Then 32 cuts/conversions. Four targeted mutations detected.
The independence of concrete types in the signatures of methods using
a feature was a reproduced TF2 deviation; correction below.

<a id="contraintes-imbriquées-et-premières-interactions-async"></a>

### Interlocking constraints and early async interactions

Preuves : [NESTED_FEATURES_CYCLE.md](cycles/NESTED_FEATURES_CYCLE.md).

| Rules | Invariant / interactions | Evidence | Limites |
| --- | --- | --- | --- |
| TF1, TF2, TF3 | Only the recipient is specialized; other arguments are forced to be independent; complete signatures | Left/Right in the same method by two relays; other features and mutable arguments; equivalent recursive constraints; restrictive signature refused; substitution and guard mutations detected | P — no equal relationship of type added; no universal proof |
| TF5, B5 | The forced result keeps its own type and origin | Wrapper returns Target via two relays; premature destruction refused; three incorrect sheets refused even without method use; mutation of demand detected result | P — concrete results tested; executable recursion not added |
| TF4–TF5, AS8, AS11–AS12 | From creation, transfers, effects and loans after preserved join | `test_async_type_features` : four native programs, eight variants refused; Vector Int/u8 independent, String borrowed and consumed, re-use at the same address | P — still refused structure capture, archived counter example; no TSan |

Final state: 42 methods under UBSan fatal at O0/O2; 173 regression methods
and 36 reexecuted with a single feature injection. Seven mutations detected.
New synchronous and async cases represent 10 native and
The package 06 and the overall objective are not closed.

<a id="brouillon-04--nouvelle-référence-normative-et-obligation-dattente"></a>

## Draft 04 — new normative reference and waiting obligation

The integrated version of [ASYNC_MULTITHREAD_RULES.md](ASYNC_MULTITHREAD_RULES.md)
replace the old incompatible statements, including the abandonment of handle.
The [cycle of obligations]](cycles/HANDLE_OBLIGATIONS_CYCLE.md) distinguishes this
integration of the implementation and validations executed.

| Rules | Obligation actuelle | Evidence/implementation status | Statut |
| --- | --- | --- | --- |
| RT7, MT3, MT5 | Wait for each handle, by path; transfer of obligation; no drop or implied abandonment | `test_handle_obligations` : 10 native executions, 34 refusals to O0/O2; sync/async models of 18 configurations; two abandoned mutations detected; 44 successful interaction methods; async regression: 264 methods initially successful and 11 migrated and successfully re-executed | P |
| AS10, RT6 | Cleaned launch failed before Err and re-use of slot | EAGAIN simulation with single cleaning and re-used address; mutation omitting the detected cleaning; runtime pattern::Error::LaunchFailed and integrated proprietary signatures; standalone error value retained after destruction, recaptured and relayed; see RUNTIME_ERROR_VALUES_CYCLE.md | P |
| AS14 | Destruction of an inactive instance always possible | Drop allowed, end of scope with warning, body not executed in new batch | P |
| AS7 | Static or explicit capacity by qualified name; counted recursion; async_pool_sizes | Directive and conservative parameters implemented in the current subset: 9 methods O0/O2 + 1 method of exceedance Int32, 13 native executions per level including controlled exhaustion, 12 refusals, model of four parent/child configurations, four mutations detected. Regression: 274 methods async + 22 successful features initially and 1 successfully migrated diagnosis separately; 239 initially successful synchronous methods, then 28 conditionals after migration U1 of 4 cases. See ASYNC_CAPACITY_CYCLE.md; Select and declared namspaces remain open | P |
| RT2–RT4 | Spawn/spawn_blocking delegation; installation directly in hand; alarms kept and equity; migration between polls | spawn_blocking delegates to a separate callback; model of 8 configurations, progress of one pair during blocking and failure cleaning performed at O0/O2. Five mutations detected, 14 methods replayed with both modes; see SPAWN_BLOCKING_CYCLE.md. Public installation, alarms and general equity remain open | P |
| RT5 | runtime::Handle<T>, join synchrone ou await async, Result<T,runtime::Error> | Motif runtime::Error::LaunchFailed and embedded proprietary results; standalone error values integrated in the tested contexts (RUNTIME_ERROR_VALUES_CYCLE.md); synchronous contracts and async captures of six Integrated Non-borrowing Result (PLAIN_JOIN_CONTRACTS_CYCLE.md); async returns and interlocks of these six integrated loads (NESTED_PLAIN_RESULTS_CYCLE.md); runtime::Handle<T> and other general forms still to be integrated | P |
| RT8 | Runtime synchronous block::thread with transferred catches and inferred result | Parsing, typed states, first captures and connected results; 29 Crust native executions, 40 refusals and four mutation mechanisms detected in NATIVE_BLOCK_LOWERING_CYCLE.md. The Int/u8/char/Void auxiliaries are now callable since the states: 14 executions, 17 refusals, opaque contracts during check, order of arguments, cleaning of internal pools and transitive join. Four targeted mutations detected, including one reinforced case after initial survival. The parameters and results &Int, &mut Int and &mut u8 are connected: order of loans prepared, conditional results, last uses, scalar drop and child capture. See SYN | P |
| MT9 | Synchronous custody linked to thread; async custody conservable during suspension and migration; release after end of borrowing | Internal Sync/async Primitives and Select Cleaning Exercised in MUTEX_RUNTIME_CYCLE.md: six C probes, migration and alarm, related regressions. Static control of unconnected guards; manufacturers expressly postponed | P |
| SL1 | Select owns branches; order of eligible; single expectation; losers retained and then destroyed | Internal C mechanism, branch alarms and retention tested in SELECT_RUNTIME_CYCLE.md; cleaning callbacks to the suspensions generated and exercised in SUSPENDED_CLEANUP_CYCLE.md. Source and contracts not connected; arbitration of losing handle on hold. | P |

The C oracles of the abandonment register remain historical and do not constitute
plus proof of acceptance of abandonment at the language level.

Supplement RT8 — [native border](cycles/NATIVE_THREAD_BOUNDARY_CYCLE.md) : cinq
runtime methods, ten probes C to O0 and O2 (nine normal outputs and one SIGABRT
expected for internal suspension prohibited), seven parsing methods,
Six detected targeted faults and 68 successful O2 regression methods.
In this first cycle, only parsing and l-ABI were connected; the
contracts/generation remained open and the minimum programme was rejected.
The NATIVE_BLOCK_LOWERING_CYCLE.md cycle below has been bringing since the first
end-to-end executions; previous refusal logs are historical.

<a id="complément-rt5rt6--valeurs-derreur"></a>

### Supplement RT5/RT6 — Error values

The cycle [RUNTIME_ERROR_VALUES_CYCLE.md](cycles/RUNTIME_ERROR_VALUES_CYCLE.md) trace them
interactions executed with U1, drop, branches, loops, catches and contracts.
The status remains P: the overall results and the public runtime are incomplete.
The two initially surviving mutations and the four historical scenarios
The loops migrated to U1 are documented, with the final traces.

<a id="complément-rt5rt6u1--contrats-de-résultats-simples"></a>

### Supplement RT5/RT6/U1 — Simple results contracts

[PLAIN_JOIN_CONTRACTS_CYCLE.md](cycles/PLAIN_JOIN_CONTRACTS_CYCLE.md) trace the catch in
load of the six Int/Bool/u8/char/()/runtime loads::Error in signatures
synchronous, annotations and async catches, and harmonisation
The independent table covers 24 configurations of type,
launch and context; the other cases bring the lot to 32 native executions
Four targeted mutations detected. U1 verification of results
Async loop and readings added to two historical tests are detailed.
The status remains P. The return async of a simple Result is a reproduced deviation
in validation/open-async-plain-result-return.crust and its log.


<a id="complément-rt5rt6--retours-async-et-imbrication-des-résultats-simples"></a>

### Supplement RT5/RT6 — Async returns and imbrication of simple results

[NESTED_PLAIN_RESULTS_CYCLE.md](cycles/NESTED_PLAIN_RESULTS_CYCLE.md) update the deviation
`open-async-plain-result-return` His old log of refusal is kept.

| Rules | Invariant and scope | Preuves | Limites / statut |
| --- | --- | --- | --- |
| AS4, RT5, RT6 | Await inactive makes T; waiting for a handle adds an envelope; each status remains independent | Six primary loads, depths 2 and 4, async capture and suspension; depth chain 7; failure injected at each of the four levels; three status mutations detected | P — Runtime envelopes::Error around these six loads; not all Result<T,E> |
| RT5, U1, B5 | Contracts keep type, including depth and load; explicit use of interlocked results | Sync/async contracts, direct returns, if/loop, copies, reassignments and drop; incompatible types and link after drop refused; type and use shift detected | P — deterministic coverage, no universal evidence |
| AS2, AS10, AS11, P8 | Simple results do not prolong catches; waiting before release and re-use | Capture destroyed once, success and failure of launch; same address reused; mutable capture reserved until join, drop of target allowed before reading the simple result; premature historical reset refused | P — three executions and three capture conflicts; reset is not reintroduced |
| RT5 / C generated | Typed copy by level, separate status and independent statements of compiler history | fatal UBSan O0/O2; shallow compilation identical before/after deep program; deep signature without running instance; regressions results/borrows/tables/ABI | P — Clang arm64 ; ni preuve formelle ni TSan |

The new module contains 11 methods: 52 native executions and 23 refusals
five targeted mutations are detected.
The controls, terminal tracks and limits are recorded in the report.
The overall objective and the other N/P lines remain open.

Variances (RT5/RT6)
`validation/open-async-business-result-envelope.crust` and his log show
que l’enveloppe `Result<Result<u8,IntegerConversionError>,runtime::Error>`
remains refused as a return async. It is a valid normative composition
The programme is not classified as invalid.


<a id="complément-rt5rt6v3txu1--enveloppes-des-résultats-métier"></a>

### Supplement RT5/RT6/V3/TX/U1 — Envelopes of business results

[BUSINESS_RESULT_ENVELOPES_CYCLE.md](cycles/BUSINESS_RESULT_ENVELOPES_CYCLE.md)
update the deviation `open-async-business-result-envelope` above.
historical refusal is retained; the program now runs.

| Rules | Invariant and interactions | Preuves | Limites / statut |
| --- | --- | --- | --- |
| RT5/RT6, V3, TX | The business load retains its type and status independently of the launch errors | Conversion u8, char_at, char::from_str, pop, replace_byte and replace_bytes; one/three envelopes, two business issues, sync/capture async read; refusal to launch at each level | P — six existing families without loans, not all Results<T,E> |
| U1 | The result of the fallible extract must be used | Unused Ok(inner) acceptance default reproduced and then corrected; neighbour with accepted drop; mutation detected | P — case of tested results, not universal proof |
| AS2/AS12, B5, RT5 | A common C representation does not allow conversion between Crust types or erasure of a provenance | Job sync creation: eight bad load types and two bad runtime values::Error refused; result of incompatible borrowed slice refused, valid neighbour executed; mutation of detected type control | P — Sync creation paths and batch captures; general signatures still open |
| RT5/TX, L6 | Calculated results independent of source storage; copy, returns, branches, drop | Thong results used after drop of source; sync/async contracts, reassignments and alias; former UTF-8/transaction/re-use checks replayed | P — targeted executions under fatal UBSan |

The final module has 58 native executions and 16 refusals expected by level
O0/O2. The first campaign of mutation revealed an unexercised path; the
The matrix has been extended to synchronous direct extraction.
the final traces, classifications and results.
l’objectif global restent ouverts.

<a id="complément-ve3--as8--remove-dans-les-corps-async"></a>

### Supplement VE3 × AS8 — Remove into async bodies

[ASYNC_VECTOR_REMOVE_CYCLE.md](cycles/ASYNC_VECTOR_REMOVE_CYCLE.md) corrige
`validation/open-async-vector-remove.crust`. Aucune modification normative.

| Rules | Invariant / interactions | Executable evidence | Limites / statut |
| --- | --- | --- | --- |
| VE3/VE1, GR1/GR2, AS8 | Extraction of the right value, order and length retained, even on the downline | Four Int/u8 × two front combinations, actual C-based orientation; 64 operations from two independent Python lists; index mutations, offset and length detected | P — Copy Int/u8 elements; async handles/borrowings not covered |
| B1/B2, F4/B4a, AS2/AS15 | Receivable booking during suspended index; no reuse of invalidated view | Three aliases refused and separated neighbour executed; last view usage, three prohibited continuations; reservation transfer detected | P — forms of the lot |
| F3, AS8/AS10, D1/P8 | Continue/break and extraction before cleaning; re-use only after join | Loop with local view, yield, continuous and break; captured, two-destruct meter and address reused on success/EAGAIN | P — scenarios performed, no general proof of cleaning |
| VE3/VE4, F5/B5 | Off-limit index diagnosed before access; width and mutability retained | Six controlled stops, Int/u8 × three invalid indices; u8=255 by wait/join, bad types/arity/receivers and reuse after drop refused | P — fatal UBSan, no exhaustive analysis of terminals |

Twelve methods, 15 successful native executions, six controlled judgments and
15 expected rejections by complete passage. Four mutations detected; see
the ratio for O0/O2 traces and regressions.
`validation/open-async-vector-push-new.crust`, is now corrected for
Int/u8; see cycle below. Other obligations of the seven drafts
restent ouvertes.

<a id="ve6--as9--emprunts-de-nouvelles-cases-yield-await-et-join"></a>

### VE6 / AS9 — borrowing of new boxes, yield, wait and join

Preuves : [ASYNC_VECTOR_PUSH_NEW_CYCLE.md](cycles/ASYNC_VECTOR_PUSH_NEW_CYCLE.md),
`tests/test_async_vector_push_new.py` and its logs in validation/.
No rule of law changed; partial executable coverage.

| Rules | Invariant and interactions | Executable evidence | Limites |
| --- | --- | --- | --- |
| VE6/V2, VE1/GR1 | Box initialized before exposure, good address on both fronts | Zero then write, intact neighbors, C orientation checked; independent lists seeds 817/810; detected defect and address mutations | P — Int/u8, autres types ouverts |
| B1/B2/B4a, AS2/AS9/AS15 | Vector and parent reserved for last use | Inactive captures, yield, two relays, branches/loops/continue/break; premature access denied; reservation mutation detected | P — forms executed; general expressions of open borrowing |
| F5/B5, AS8, RT6 | Type and provenance retained by await/join and contracts | dedicated u8 pointer, sync/async joins, synchronous relays, shared reborrowing with mutable ancestor; provenance mutation detected | P — return synchronous match corrected in REFERENCE_EXPRESSIONS_CYCLE.md; form in an async frame still open |
| D1/P8, VE4, AS10 | Sustainable source, re-use after waiting, no exposure outside capacity | Owned sources, drop after copy, even re-used slot; premature drop/exhaust refused; two capacity stops before use | P — deterministic scenarios, no general proof of cleaning |

Fifteen methods: 24 normal executions, two controlled judgments and 31 refusals
Four mutations detected. UBSan fatal; the ASan trial
is inconclusive (also time-bound with an empty C program).
The difference `validation/open-join-element-match-expression.crust` is now
The general obligations of the seven drafts
restent ouvertes.

<a id="b5--d1--emprunts-produits-par-les-expressions-conditionnelles-synchrones"></a>

### B5 / D1 — borrowings produced by synchronous conditional expressions

Preuves : [REFERENCE_EXPRESSIONS_CYCLE.md](cycles/REFERENCE_EXPRESSIONS_CYCLE.md),
`tests/test_reference_expressions.py`, journaux reference-expressions-*.
No change in norms. Fourteen methods: thirty native executions
and 63 refusals expected in passing, including two of the historical reset profile.

| Rules | Invariant / interactions | Executable evidence | Limites |
| --- | --- | --- | --- |
| B5, B1/B2, D1 | All provenances and ascendings remain protected until last use | Two pools, nested branches, if in loop, mutable match holder, drop refusal and early access | P — synchronous expressions; if async returns added in ASYNC_REFERENCE_RETURNS_CYCLE.md |
| F5/B5, E6, VE6 | Only one reference, from the right type, to the chosen branch | Int/u8, pool/table in both orders, structural references, three-value model seed 1771 | P — finished scenarios, not proof of all the provisions |
| D1/D2, P8, PR1 | No local target promotion, cleaning after use | Local targets refused before arm closure; re-use of pools after drop; public reset refused | P — historical reset tested separately, not reintroduced |
| B4a, AS8, RT6 | Condition then only selected arm, coming after join and contract | Observable effects, join success/EAGAIN, separate rescue, anticipated returns | P — Synchronous integration with tasks |

Three mutations are detected by the output/refusal assertions or UBSan;
a fourth triggers an internal compiler guard on a program
valid. Output L-oracle alone is not credited with this fourth detection.
The Counter-Example `validation/open-async-reference-if-expression.crust` a ensuite
was corrected in ASYNC_REFERENCE_RETURNS_CYCLE.md. Conditional result
received by local link in an async frame remains open.
The specific logs and limits are included in the cycle reports.

The following deviation AS2/RT5/RT6 is reproduced:
`validation/open-async-vector-value-result.crust` capture and return
`Result<(),u8>`, already accepted in the synchronous neighbour executed.
The log keeps this refusal and the exit of the valid neighbour.
The latest UTF-8 and ABI regressions of the business cycle each performed
15 methods successfully after the corrections.


<a id="complément-as2rt5rt6u1--résultats-scalaires-de-vecteurs"></a>

### Supplement AS2/RT5/RT6/U1 — Scalar vector results

[ASYNC_VECTOR_RESULTS_CYCLE.md](cycles/ASYNC_VECTOR_RESULTS_CYCLE.md) corrects refusal
`open-async-vector-value-result` His old log remains historical.

| Rules | Invariant and interactions | Preuves | Limites / statut |
| --- | --- | --- | --- |
| AS2/AS4, RT5/RT6 | Captures and returns keep the type complete and distinguish the result of the job from the errors of launch | Eight families: Int/u8, replace Int/u8, try_push Int/u8, capacity and read; two variants each; sync/async observation, direct join and interlock; four rejections of launch injected | P — synchronous produced values; async production methods still open |
| U1, L6, V3 | Explicit use, invalidation after drop, pattern shape and load width | Copy, if/loop, reassignment, direct returns, value denied -23/255; bad types and uses after drop refused; targeted mutations | P — not all containers/enums |
| RT6 / C | Status and values copied in the correct field C without incompatible pointer aliases | Three common representations moved in the shared header; UBSan fatal O0/O2; ABI/table/borrow controls and regressions from previous results | P — Clang arm64, not ASan/Tsan or universal proof |
| Limited growth, PR1 | Output independent of the source after drop; ability and reading keep their outcome | Real saturation of 1M region, try_push/try_extend refused; separate EOF, Io and CapacityExceeded; Vector source destroyed before capture of result | P — synchronous production and async transport tested; reset remains absent from prototype |

The final module comprises 11 methods: 56 native executions and 13 refusals
O0 is covered by the first ten methods and then the method of
direct join; O2 executes the complete module. Traces and mutations are
The overall objective remains open.

The next gap is reflected in the
`validation/open-async-vector-result-producer.crust` and its log: an operation
`try_push` directly in the body async remains refused, despite signatures
and results now supported. It is a valid program to
implement, not a negative example of semantics.

<a id="complément-ve3ve4--as2as8--opérations-de-vecteurs-dans-les-corps-async"></a>

### Supplement VE3/VE4 × AS2/AS8 — Vector operations in async bodies

[ASYNC_VECTOR_OPERATIONS_CYCLE.md](cycles/ASYNC_VECTOR_OPERATIONS_CYCLE.md) corrige
the lack of direct production reported in the preceding paragraph.
changement normatif ; `reset()` remains withdrawn according to PR1.

| Rules | Invariant / interactions | Executable evidence | Limites / statut |
| --- | --- | --- | --- |
| VE3/VE4, AS4/AS8, RT5/RT6 | Pop, replacement and insertion keep status and value; failure does not publish new elements | Eight families and two exits, pre/post-yield states, old value or inward refused, 1M region actually saturated, atomic extension, EOF/Io/capacity | P — Int/u8; own and borrowed containers not covered by this lot |
| F4/B4a, AS2/AS15 | Receiver reserved before arguments; instant of each argument before the next, even suspended | Two suspended arguments, index modified by the following argument, aliasing calls refused and disjointed call executed; two mutations detected | P — operations and forms of the consignment, not arbitrary |
| B1/B2, VE5, AS12/MT6 | Last viewing use releases the reservation; join precedes access and drop at caller | Re-use after last reading, three conflict continuations refused, slice/byte returned by await, self-extension refused, three access before join refused | P — no general evidence of vivacity analysis |
| AS10, D1, P8, H1 | The possessed capture is destroyed once; the scalar result survives re-use | Success and EAGAIN injected, pool of a slot, re-used address and independent meter of destroyer inputs | P — two Vector allocations of the scenario, not all cleaning graphs |
| U1, F5, VE1 | Explicitly used and retained types of fallible results | drop expression executed once, four missing uses refused, seven incompatible types/receivers refused; mutation of U1 control detected | P — scalar forms tested |
| VE3/VE4, AS8 | Sequence of mutations in accordance with the independent list template | 56 operations generated, seeds 37/91, value and length observed after each transition; load and status mutations detected | P — 56 transitions, not exhaustive exploration |

The final batch consists of 15 methods, 35 native executions and 21 expected refusals
O0/O2, fatal UBSan, five injected errors detected.
The log, regression and limit are detailed in the cycle report.

Separate F2 counter example retained in
`validation/open-read-error-residual-pattern.crust` : `Err(_)` after a variant
ReadError's precise is still refused by the parser. This refusal is not
The general errors, the public handles, scheduler, threads,
Select, mutex and other recorded deviations still to be implemented; the objective
The overall rate is not reached.

<a id="complément-f2--couverture-résiduelle-des-erreurs"></a>

### Supplement F2 — Residual error coverage

[RESIDUAL_ERROR_PATTERNS_CYCLE.md](cycles/RESIDUAL_ERROR_PATTERNS_CYCLE.md) corrige
ReadError counter example noted above. The original log remains historical.

| Rules | Invariant / interactions | Preuves | Limites / statut |
| --- | --- | --- | --- |
| F2, VE4, TX4 | Err(_) after a specific variant retains the type and covers only the remaining errors | Success, EOF, Io, sync/async capability; Empty/MultipleChars/success decoding; OUT/CUT/view cutting; three mutations detected | P — Building families, not arbitrary summation |
| F2/F3, AS8 | Residual bodies run once and can provide a value after suspension | Counter and yield in the arm; regressions on transfers, views, owners and early returns | P — paths executed, no proof of any AST duplication |
| F2/B5 | Exhaustivity and exact type remain required | Five refusals: Ok absent, double-double, two inaccessible arms, family incompatible | P — finished test sets |

Six new methods, 19 native executions and five refusals by way of passage.
General liaison `Err(error)` from ReadError en async remains open:
`validation/open-async-read-error-binding.crust` and its log reproduce this
missing, separate from the wildcard correction. See the report for the traces,
validation options and limitations.

<a id="complément-f2b5as8--valeurs-derreurs-builtin"></a>

### Supplement F2/B5/AS8 — Building error values

[BUILTIN_ERROR_VALUES_CYCLE.md](cycles/BUILTIN_ERROR_VALUES_CYCLE.md) corrects the
refusal of `Err(error)` No new normative rules.

| Rules | Invariant / interactions | Evidence | Limites / statut |
| --- | --- | --- | --- |
| F2/B5, RT5/RT6 | The error type and variant are retained; the start error remains distinct from the business error | Seven types, thirteen variants; sync contracts, catches, direct and handle wait, join and interlocked envelopes; EAGAIN injected | P — Buildin Copy values; not arbitrary sum, nor borrowings of these values |
| F2, VE4, TX4, F5 | Err extracts status and not the success load | Thirteen operations, UTF-8 errors and vector, real capacity 1M; link after precise variant, complete match; three extraction mutations detected | P — APIs and variants of the lot |
| B1/B5, AS10/AS12, D1/P8 | An error without borrowing does not hold the Result or its source storage | Copy and drop the Result and Yield, drop the vector/String then re-use the slot, read the error after join | P — roads carried out, not all containers |
| B5/F5, F2, V3 | No silent conversion between errors, wholes, borrowings or other types | Matrix of 42 incompatible nominal pairs; async captures and sync contracts; incompatible annotations/returns/motivations, usage after drop and incomplete matches refused | P — 61 refusal in the final module; two guard mutations detected |
| AS8/F4 | The results of the checks and the errors calculated are materialised once | If, loop, reassignment, copy, drop, yield, subject calculated with counter; result transported in dedicated C fields | P — no proof of any combination of control |

The final module consists of 14 methods, 60 native executions and 61 refusals
The O0/O2 passes, complements, regressions and
The report details the changes.
capture type is updated to target extended control, without
modify his oracle.

The following deviation is reproduced: `validation/open-async-vector-remove.crust` remaining
refused for expression not supported in the async body.
is valid according to VE3; refusal is not normative.
l’objectif global restent ouverts.

<a id="complément-b5as11as12--retour-conditionnel-dun-emprunt-async"></a>

### Supplement B5/AS11/AS12 — Conditional return of an async loan

Preuves : [ASYNC_REFERENCE_RETURNS_CYCLE.md](cycles/ASYNC_REFERENCE_RETURNS_CYCLE.md).
No normative changes. Ten methods, 23 native and
24 refusals expected in the final module; detailed scope in the report.

| Rules | Invariant / interactions | Preuves | Status and limitations |
| --- | --- | --- | --- |
| B5, AS8/AS12 | Each terminal branch transmits the right address and keeps all provenances | Two modes, Int/u8, array/vector boxes, await, relay, three target model; selection mutations and provenance detected | P — return if ; conditional local link still refused |
| B1/B2/B3, D1, AS11 | Durable sources and exclusivity until last use | Refusal of premises, captured owners, bad fashion and premature access to alternatives; access after use allowed | P — finished cases, not all aggregate |
| AS10, P8, RT6 | Cleaning completed before join and re-use of slot | Direct capture then child inactive owner, exact traces and pool of a slot; cleaning path mutation detected after adding the child case | P — three targeted mutations, initial survival retained in the report |

Contre-exemple suivant : `validation/open-async-local-reference-if.crust`
with a diagnosis kept. The conditional result received in a connection and then
returned after yield should be allowed; this lack is not a rule of refusal.
The remaining deviations from the seven drafts remain; overall target not achieved.

Final validation of the previous synchronous cycle: 158 methods, 188.023 s, OK,
UBSan activated; fourteen new methods in O2, historical helper to
default optimization. The 18 initial errors of three old methods
were reproduced with the previous compiler: they contradicted U1.
The fixtures now include explicit reading, with assertions of
unchanged cleaning. See REFERENCE_EXPRESSIONS_CYCLE.md for traces.

Validation of the async supplement: 43 methods O2 + UBSan, 85,039 s, OK, then
Child cleaning test added, OK to O0 and O2. The first nine methods
also go to O0 (17.467 s).Report: ASYNC_REFERENCE_RETURNS_CYCLE.md.

<a id="complément-b2b4b5as12--liaisons-empruntées-conditionnelles-async"></a>

### Supplement B2/B4/B5/AS12 — Async conditional borrowed links

[ASYNC_LOCAL_REFERENCES_CYCLE.md](cycles/ASYNC_LOCAL_REFERENCES_CYCLE.md) corrige
`open-async-local-reference-if.crust`, without change in normative. Eleven methods,
23 native executions and 34 refusals by complete passage. The first ten methods
and the drop/transfer supplement were executed at O0 and O2, fatal UBSan.
Regressions of 39 and 10 successful methods; traces and durations in the report.

| Rules | Invariant / interactions | Preuves | Status and limitations |
| --- | --- | --- | --- |
| B5/AS8/AS12 | Selection and provenance preserved through link, yield, relay and return | Int/u8, two branches, await and push_new, independent seed model 2097; pointer mutations and contract detected | P — if and blocks; async match still open |
| B1/B2/B3, D1/AS11 | All necessary targets and parents remain reserved; no local promotion | Reborrowing out of the block, child loan, last use, loop/continue/break, refusal of premature drop/transfer; target mutations and descent detected | P — scalar tables/vectors and injected references |
| B4/V3 | Explicit Writing, Type and Mode | Implicit Alias maintained refused, explicit reborrowing allowed, bad annotation/mode/type and writing without let mut refused | P — no general allocations between references |
| AS10/P8/RT6 | Re-use after end of borrowing and cleaning | Drop then pool reused; previous cycle of child-owner cleaning reexecuted | P — unchanged runtime, not exhaustive proof |

The following counter-example is retained: `validation/open-async-local-reference-match.crust`
The current refusal of a game result in a frame
Async is not a normative rule. Other N/P lines remain open.

<a id="complément-b1b5f2as12--matchs-empruntés-async"></a>

### Supplement B1/B5/F2/AS12 — Matches borrowed async

[ASYNC_MATCH_REFERENCES_CYCLE.md](cycles/ASYNC_MATCH_REFERENCES_CYCLE.md) corrige
`open-async-local-reference-match.crust` without normative change.
Thirteen methods: 36 normal native executions and 32 refusals by complete passage.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| B5/AS12, RT5/RT6 | Source of Ok and rescue preserved after wait, yield and return | Results stored/direct, ref/mut modes, Int/u8, EAGAIN, model independent of three targets; contract mutation detected | P — Building families, not all aggregate |
| B1/B2/B3 | A Result carrier does not provide two mutable capabilities used simultaneously | Previously accepted counter-example, now refused; second projection after last use and two shared projections allowed; transfer of the holder detected | P — direct reference in Handle result |
| D1/AS11 | No implicit extension of a local target | Arm target refused; wrong mode/type/Integer result refused | P — programmes finis |
| F2/B4a/AS8 | Subject evaluated before the right arm; suspension and early return preserved | Success/fail marker, inverted branches, nested match, conversion/pop and buildin errors; status mutation detected | P — families and forms executed |

The invalid double projection program is retained in
`validation/async-match-overlapping-result-borrows.crust`, with logs before/after.
His refusal no longer rests on an accidental conflict between two relief branches.
The next shortfall reproduced is the borrowed result of loop async:
`validation/open-async-reference-loop-result.crust`Other obligations
Open to the public remain unchanged; overall target not achieved.

Final evidence of the match async cycle: 13 methods at O0 (22,933 s) and
62 methods at O2 (86,489 s), all successful, fatal UBSan; four mutations
The detailed numbers and limits are shown in the
ASYNC_MATCH_REFERENCES_CYCLE.md. The initial passage of 59 methods did not cover
not the double projection counter example, added to the final regression.

<a id="complément-s5ab5as12--résultats-empruntés-de-boucles-async"></a>

### Supplement S5a/B5/AS12 — Results of async loops

[ASYNC_LOOP_REFERENCES_CYCLE.md](cycles/ASYNC_LOOP_REFERENCES_CYCLE.md) traite
`open-async-reference-loop-result.crust`without any change in the normative framework.
Ten methods: 18 native executions and 28 refusals by complete passage.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| S5a/B5/AS12 | Each break and return is expected to contribute to the outcome targets | Ref/mut modes, interlocking loops, two branches, async relays; corrected nested return counter example; detected contract mutations | P — forms executed, break in conditional initialisation still refused |
| B1/B2/B3/D1/AS11 | Targets and parents protected after exit, without local storage extension | Premature transfer/reading/drop refused; non-sustainable premises refused; access and re-use after use allowed | P — Int/u8 and tables/scalar vectors |
| S4/S5/AS8/AS10/RT6 | Suspension and cleaning preserve result and storage | Repeats continuous, break, child inactive owner cleaned once, pool capacity a re-used ; cleaning mutation detected | P — no general proof of cleaning |
| S5a/RT5/B4a | Correct pointer selection and homogeneous modes/types | Independent model of the three indices; normal launch/EAGAIN; type/mode missing or divergent refused | P — Finished model |

The original invalid counter example is retained in
`validation/async-loop-early-return-provenance.crust`, with traces before/after.
The final module is changed to O0 + UBSan (10 methods, 8,501 s); four mutations
The O2 + UBSan regression is complete: 80 methods,
92,284 s, OK, no jump. Report and controls available in the cycle.
The next repeated lack is `validation/open-async-loop-break-in-initializer.crust`.
The other obligations of the seven drafts remain open.

<a id="complément-s5s5aas12--sorties-depuis-les-expressions-async"></a>

### S5/S5a/AS12 Supplement — Outputs from Async Expressions

[ASYNC_EXPRESSION_LOOP_EXITS_CYCLE.md](cycles/ASYNC_EXPRESSION_LOOP_EXITS_CYCLE.md)
traite `open-async-loop-break-in-initializer.crust`without any change in the normative provisions.
Eight methods: 23 native executions and 21 refusals by complete passage.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| S5/S5a/B5/AS12 | The nested outputs contribute to the contract of the right loop | If, blocks, match, break/return operands, internal loops; all protected targets and internal target not retained without reason; provenance mutation detected | P — initialization without any continuing branch still open |
| S4/AS8/B2 | Continue resumes the right iteration without providing a fictitious result | Initialization and assignment, yield, counter and markers; task consumed before resumption refused; continuous mutation→break detected by UBSan | P — Types and paths carried out |
| D1/AS10/AS11/RT6 | The lost telescopes are cleaned and the targets remain sustainable | Inactive child owner, destruction once and slot reused after join; local target refused; cleaning mutations detected by invariant and native execution | P — no general proof of cleaning |
| B1/B3/RT5 | The expected match result keeps its dependencies through break | Success and EAGAIN injected, then use the borrowed result; mutation of the two targets refused | P — direct result &mut Int |

The module goes to O0 + UBSan: 8 methods, 9,458 s. Four errors are detected,
one by the compiler control; the initial inconclusive classification
and its explanation are kept in the report.
completed: 89 methods, 88,707 s, OK, no jump.
The next repeated lack is `validation/open-async-diverging-initializer.crust`.
The remaining open bonds of the seven drafts remain unchanged.

<a id="complément-s5b4aas12--expressions-async-sans-continuation"></a>

### Supplement S5/B4a/AS12 — Async expression without continuation

[ASYNC_DIVERGING_EXPRESSIONS_CYCLE.md](cycles/ASYNC_DIVERGING_EXPRESSIONS_CYCLE.md)
traite `open-async-diverging-initializer.crust`without any change in the normative framework.
Twelve methods: 42 native executions and 33 refusals by complete passage.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| S5/S5a/B5/AS12 | No receiver or fictitious source after a non-continuous expression | Initialization, assignment, print, loop, return, expected match; two protected sources; counter-example of inaccessible return c corrected | P — Table notation without continuation still open |
| B4a/AS10/RT6 | A prepared transfer remains responsible for its cleaning if the call is interrupted | Reproduced leak with capacity pool one, now re-used; branches interrupted/normal, Result owner and EAGAIN; cleaning mutation detected | P — Scalar proprietary catch/Result, not all aggregate |
| S4/S5/AS8 | An internal loop to an argument does not destroy the external call catches | Suspension and internal break before task creation; depth mutation detected by UBSan after refinement | P — first fault too large classified as inconclusive and retained |
| B1/B3/D1/AS11 | Outbound paths keep fashion rules, exclusivity and service life | Premature shifts, local targets, old displaced access and no value denied break; last use and then re-use allowed | P — programme fini |
| S5/B4a | Short circuit and continuous keep the paths that continue | &&/||, two paths ; arithmetic model of 1, 2 and 4 iterations | P — no general evidence of flow control |

The first eleven methods are changed to O0 + UBSan (25,569 s).
short circuit changes to O0 (2.461 s) and O2 (2.250 s). The regression O2 + UBSan
expanded is completed: 176 methods, 247,789 s, OK, without jump; it precedes
Adding the short circuit complement executed separately.
Four errors are detected; one has been refined after a first
The traces and two corrected defects are shown in the table below.
The next gap is in the report.
`validation/open-async-diverging-typed-initializer.crust`.
The other obligations of the seven drafts remain open.

<a id="complément-s5e3as12--réceptions-typées-sans-continuation"></a>

### Supplement S5/E3/AS12 — Typed receptions without continuation

[ASYNC_TYPED_DIVERGENCE_CYCLE.md](cycles/ASYNC_TYPED_DIVERGENCE_CYCLE.md) traite
`open-async-diverging-typed-initializer.crust`without any change in the normative framework.
Six methods: 25 native executions and 27 refusals by complete passage.

| Rules | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| S5/S5a/E3/E7 | No materialization of a receiver that no path is reached | Scalar types, buildin results, empty/enbricated/reference arrays; if, block, match, loop, return, continuous; deactivation of detected treatment | P — recognized async directory, not all aggregates |
| V3/E3/E5 | Each path continuing retains the declared type | Neighborhood with array actually provided; incorrect types/dimensions and unknown annotations refused; validation mutation of detected type | P — scenarios implemented |
| B1/B3/B5/D1/AS11/AS12 | The annotation does not remove targets or restrictions | Local targets, divergent modes and mutations before last use refused; erasure of provenance detected | P — Int/u8 and references Int |
| B4a/AS10/RT6 | The interrupted call cleans up the prepared transfers | Reuse of a capacity pool one, destruction once; lack of cleanup detected | P — capture Int in this supplement |

The final module goes to O0 + UBSan: 6 methods, 13.290 s. Four errors are
The O2 + UBSan regression is complete: 96 methods,
114,353 seconds, okay, no jump.
At the end of this cycle of typed initializations, RT8 was still N: the
programme minimal `validation/open-native-thread-basic.crust` was refused
in spite of its normative validity.

Follow-up: this is a historical observation. The minimum program now runs
with output 7, and RT8 is P in the current table.
[native block cycle](cycles/NATIVE_BLOCK_LOWERING_CYCLE.md) includes 13 methods,
29 native executions and 40 refusals; identities and traces of destruction
were reinforced and re-executed at O0/O2. The O2 regression of 81 methods
is successful. A first complete erasure from the source is inconclusive
in the mutation protocol; the refined loss of one origin is
The program is still valid and is not accepted by the user.
refused with sync auxiliary and local pool async remain preserved.

<a id="appels-synchrones-empruntés-dans-les-états-async-et-natifs"></a>

### Synchronous calls borrowed in async and native states

See [cycle](cycles/SYNC_BORROW_CALLS_CYCLE.md) for configurations, logs and boundaries.

| Rules | Invariant exercised | Preuves | Statut |
| --- | --- | --- | --- |
| B1/B2/B4a, AS2/AS15 | Prepared loans protected during arguments, whether or not suspended; end of last use with continuations and loops | Cases allowed/refused and booking and liveness transfers | P — Int and mutable u8 |
| B5/D1/D3, AS9/AS12, MT6 | Union of contract targets, until last use after await/join; no local target leak | Two targets/one target, relay and child capture; pointer and target mutations | P — direct parameters |
| L6, B3, RT8 | Drop scalar invalidates the link after checking loans | Int/Bool/u8, read/write/double drop rejected; pool reused after call interrupted | P — Forms executed |

<a id="appels-synchrones-partagés-u8-depuis-les-états"></a>

### U8 shared synchronous calls from states

Rapport : [SYNC_BYTE_BORROW_CALLS_CYCLE.md](cycles/SYNC_BYTE_BORROW_CALLS_CYCLE.md).

| Rules | Invariant and interactions | Evidence | Limites |
| --- | --- | --- | --- |
| B4/B4a, TX5, AS2/AS15 | &u8 keeps its target during arguments, even suspended; no & implied | Literal, table, local, reborrowing, nested call, yield/return; loan transfer prepared | P — signatures and expressions of the consignment |
| B5/D1, AS9/AS12, MT6 | Targets of exact result since contracts, no space leak | choose/first, child, join, source not returned released; mutations of targets, contract and pointer | P — direct parameters |
| B2/B3/L6, TX12 | Last use allows drop/reuse; future use prohibited | Loop, mutable parent, pool String capacity one, launch failure; reset only historical | P — Finished scenarios |
| RT8, TX5 | Type of capture d | Capturing &String native block, back via auxiliary and then join, premature drop refused | P — Other catches/general types opened |

Executions of this supplement: 119 native O2 methods successful before the last
connections, then 15 successful O2 final targeted methods (including UTF-8 fixture)
12 u8 to O0 and final baseline green O2; five mutations
u8 detected. UTF-8 selection of 80 methods had a diagnostic failure
linked to the double transformation of the fixture, corrected and reexecuted; this journal
see the chronological table of the report for the
checks after each modification and the limits of each passage.

<a id="transferts-propriétaires-aux-helpers-synchrones-depuis-les-états"></a>

### Owner transfers to synchronous helpers from states

Rapport : [SYNC_OWNED_CALLS_CYCLE.md](cycles/SYNC_OWNED_CALLS_CYCLE.md).

| Rules | Invariant exercised | Preuves | Limites |
| --- | --- | --- | --- |
| B4/B4a/T1, B1/B2 | -> mandatory, old name invalidated from preparation, last use of loan before transfer | Orders admitted/refused, named view, mutable loans, subcalls; transfer d | P — types Int/String/Vector<Int/u8> |
| AS8/AS12/L6 | Arguments moved alive through yield; single cleaning if argument comes out | One/two arguments prepared, early return, internal loop, re-use; transfer of registration and order | P — Forms executed |
| T6/T9/T11, AS9/RT8 | Address and actual source retained upon return; other candidate destroyed | Two pools, choice 0/1, addresses, join, re-employment; export transfer | P — candidats directs |
| B4c/AS7/MT6 | Live captures before join; only the pools of the result selected then | Synchronous factory, helper first, child pool destroyed after join, leak of the refused handle; mutation of provenance | P — conservative approximation of other candidates |
| U1/L6/V4 | Result received, transmitted or dropped; replacement after evaluation | Appel seul/_Unused binding refused; drop(expression), replacement and annotations A<T> | P — signatures of the consignment |

Owner cycle performance: 13 O0 methods, 134 regression methods
native/runtime O2 and 130 successful O2 contract methods.
green update; six injected errors detected and one remission omission
NULL without effect on the routes examined (field excluded by consumed and
cleanup_path), explicitly not counted as detection.
pool/target leak checks are included in the final baseline
and Supplement O0. No general proof of safety.

<a id="booléens-des-helpers-et-copies-primitives-en-sortie-de-bloc"></a>

### Booleans of helpers and primitive copies out of block

Rapport : [SYNC_BOOL_CALLS_CYCLE.md](cycles/SYNC_BOOL_CALLS_CYCLE.md).

| Rules | Invariant exercised | Preuves | Limites |
| --- | --- | --- | --- |
| I5/B4/B4a, AS2/RT8 | Separate Boolean type d  ,int/u8 through contract, native status and result | Independent Truth Table, interlocking calls, capture and annotations; type and value changes | P — signatures `bool` synchronous and `Bool` of existing statements |
| B4a/B1/B2 | Left to right order and reservation of prepared arguments | Short circuit, boolean copied before mutation/transfer, prepared mutable incompatible refused | P — chemins finis |
| S4/S5/L6/AS10/AS12 | Original copy before cleaning; independent of source | Pool local closed after join, re-use, early return during preparation ; unique traces | P — Int/pool/u8/char; no general evidence |
| U1/B4e | Owner result used even in a path that returns | Corrected historical fixture, original without use refused, destruction preserved at return | P — fixture error reproduced on previous compiler |
| A1/A2/A4/AS12/AS13 | Separate pool loan from the result | Historically refused `validation/open-async-pool-helper.crust`, now executed in ASYNC_POOL_INJECTION_CYCLE.md | P — Int/String/Vector<Int/u8> injected; local pools and other open types |

Ten targeted methods O0: 18 executions C, 16 refusals, verification without
Bridge generation. Native/runtime O2 regression: 144 green methods.
Contracts/scopes: 249 methods, 248 green and a U1 fixture corrected and
reexecuted separately; the first journal is not presented as green.
Final O2 green baseline and four injected errors detected; omission of the
additional snapshot without effect on the chosen paths, not counted as
detection. fatal UBSan, Clang C11 pthread; no new results ASan/TSan.

<a id="pools-injectés-dans-les-états-async-et-natifs"></a>

### Pools injected into async and native states

Rapport : [ASYNC_POOL_INJECTION_CYCLE.md](cycles/ASYNC_POOL_INJECTION_CYCLE.md).

| Rules | Invariant and interactions | Evidence | Limites |
| --- | --- | --- | --- |
| A1/A2/A3/A6, AS2/AS13, MT3 | Durable source and active loan from capture until waiting; no closure of injected pool | Inactive task, child, handle factory, native block, rejected leak and EAGAIN; reservation and consumption mutations detected | P — four types of pools injected |
| B1/B2/B4/B4a | Accurate mode/type, left-right order, last use of aliases | Named loans, simultaneous shared, suspended arguments, refusal to promote mutable; three mutations detected | P — no local pools in the states |
| B4c/T11/A4, AS12 | The result keeps the possible sources without extending the exclusive loan | Two candidates, unreturned source closed, new allowance after join; mutation of provenance detected | P — contracts of the sub-unit covered |
| V4/V5/L1/L6/S5, AS8/AS10 | Typed creation, stable address, single destruction and re-use after output | Replacement, return/yield/break/continue, pool capacity one, artifact C d'identité; mutation of the nominal type detected | P — Direct creation Int ; String/Vector via helper |

Final module: 19 methods at O0 and O2; baseline O2 of 28 C executions,
36 refusal and one single check. Seven injected errors detected.
O2 regressions: 162 native/runtime methods and 153 successful contracts,
before the last type guard and, for 162, before the added loop test.
The final targeted controls cover these additions.
General proof added. All seven drafts remain partially
Implemented.

<a id="création-directe-de-collections-dans-les-états"></a>

### Direct creation of collections in the states

Rapport : [ASYNC_COLLECTION_CREATION_CYCLE.md](cycles/ASYNC_COLLECTION_CREATION_CYCLE.md).

| Rules | Invariant and interactions | Preuves | Limites |
| --- | --- | --- | --- |
| A1/A2/A3/A4, H1, AS12 | Injected pool typed, source of durable result, separate storage loan | Direct creation, named/calculated return, child, disjointed source closure, leak refused; type/provenance mutations detected | P — String/Vector<Int/u8> |
| B1/B2/B4a, VE1, G12 | Box borrowed protected before index assessment and until last use | Yield in index, shared/mutable loans, child and reborrowed earnings; change in reservation/mutability/indice detected | P — conservative protection of the collection |
| V4/V5/L1/L6, AS10, RT8 | Single cleaning, stable address, recovery and reuse | Replacement, continuous, return, temporary transfer interrupted, native block, EAGAIN; mutation cleaning detected | P — types of lot, no local pool in states |
| E1/TX9/TX10/VE1 | Typed empty construction, terminals before publication | Three pools full before destruction and four indices out of bounds; empty defect and UTF-8 content | P — annotated regions async open |

Final targeted crossings O0/O2: 14 methods, 34 normal executions, seven
6 errors detected.
The results of the extended regressions are recorded in the cycle report.
Final Regressions O2: 177 native/runtime methods and 97 interactions
The seven mutations of the batch of the
pools are also replayed and detected. No ASan/TSan results added.

<a id="pools-locaux-dans-les-états-async-et-natifs"></a>

### Local pools in async and native states

Rapport : [ASYNC_LOCAL_POOLS_CYCLE.md](cycles/ASYNC_LOCAL_POOLS_CYCLE.md).
Targeted validation and native regression executed. Async_runtime module:
275 methods, two differences in historical diagnoses corrected and
reexecuted separately; see report, without considering the original green journal.

| Rules | Invariant and interactions | Targeted evidence | Limites |
| --- | --- | --- | --- |
| A1/A2/A3/A6, AS8, RT8 | Source with stable address in the state, created at execution and closed after its allocations | Pool local Int/String/Vector<Int/u8>, yield, native thread, scalar return, EAGAIN and inactive status | P — Loans named from sources and other open types |
| T6/T9/T11, B4c, AS12 | All durable origins at each exit, including after replacement and junction | Returns, helpers, wait/join, blocks and break; model of 12 cases of descent; mutations of origin and border detected | P — Finished model, no general evidence |
| A4/MT7, B4 | Storage dependence separate from exclusive pool borrowing | Child owner and new competing allowance admitted; child borrowing the pool and then premature allowance refused | P — tested schedules only |
| S4/S5/L1/L2, AS10/AS14 | Cleaning and then closing, once, even on continuous/return/discontinued argument | Independent meter of four openings/closures; traces of destruction; mutation of closure detected | P — UBSan, not ASan/TSan |

Targeted final baseline O2: 18 methods, 21 normal executions, one stop
Diagnosis and 20 refusals; six mutations detected. Separate O0/O2 model:
nine executions and three refusals. The report retains the errors of fixings
and the end of the first campaign on its ambiguous anchor.
the complete module async_runtime are 273 successes and two assertions of
diagnostics corrected and then re-executed to O2 (two successes).
Native/runtime O2 regression is complete: 195 methods, 175,346 s, OK.

<a id="emprunts-nommés-de-pools-dans-les-états"></a>

### Borrowings named pools in states

Rapport : [ASYNC_POOL_ALIASES_CYCLE.md](cycles/ASYNC_POOL_ALIASES_CYCLE.md).

| Rules | Invariant and interactions | Preuves | Limites |
| --- | --- | --- | --- |
| B1/B2/B4/B4a | Mode, explicit level, last use and prepared arguments | Shared/mutable aliases, reborrowing, sync/async/native calls; level/mode/conflict mutations detected | P — four types of pools |
| A1/A4, D1/T11, AS12 | The result keeps the pool effective, even via alias and helper | Refused returns, disjunct source released, model of 12 cases; origin/summary mutations detected | P — finite descent model |
| AS2/AS13, RT8 | The capture keeps the pool loan after exiting the block of l'alias | Task exported and then premature access refused; initially surviving fault detected after adding this case | P — tested schedules |
| L1/L2/L6, G12 | Cleaning and re-use without displacement | Four types, suspensions, continuous/break, drop, pool recovery; regression of six local mutations | P — not ASan/Tsan or general evidence |

Final target O2: 14 methods, 15 C executions and 27 refusals, seven mutations
Targeted + model O0: 15 successful methods. Model O2: nine
The native O2 regression of 209 methods is
completed successfully; see report for durations and newspapers.

<a id="régions-annotées-dans-les-blocs-async-et-natifs"></a>

### Annotated regions in async and native blocks

Rapport : [ASYNC_REGIONS_CYCLE.md](cycles/ASYNC_REGIONS_CYCLE.md).

| Rules | Invariant and interactions | Targeted evidence | Limites |
| --- | --- | --- | --- |
| G5/G6/G7 | Lexical configuration, inherited, replaced and restored | Three collections, instructions/scalar/borrowed/owner blocks, oracle of physical classes; inheritance/restoration mutations detected | P — Async buildings supported |
| G4/G7/G12, AS8/AS12 | Limit retained after suspension/transfer/return | Conditional returns, receipt in another template, exhaustion at 1M without partial publication; Thong/Vector mutations detected | P — finished cases, without performance measurement |
| G10, S4/S5, L1/L2 | Cleaning of areas on exit routes | Continue/break, return, drop and re-use; two trees model, 28 regions | P — no general evidence |
| A1/A4, D1, B1/B2 | Annotation without source promotion or loan easing | Pool too short and access during a refused loan | P — pools and types already supported |

Nine successful O0/O2 targeted methods, 14 C executions and three O2 refusals.
Four mutations detected; model generated with seeds 19 and 73.
O2 regressions completed: 102 pool/collection/region methods and
36 methods of flow control, all successful.
cover with other cycles and do not constitute general evidence.

<a id="références-de-structures-dans-les-états-async-et-natifs"></a>

### References to structures in async and native states

Rapport : [ASYNC_STRUCT_CAPTURES_CYCLE.md](cycles/ASYNC_STRUCT_CAPTURES_CYCLE.md).

| Rules | Invariant and interactions | Targeted evidence | Limites |
| --- | --- | --- | --- |
| ST5/ST7, AS8/AS9 | Stable pointer and field offsets, mutation in place | Embedded structures, pool capacity one, identity after waiting and re-use; offset/write mutations detected | P — champs Int uniquement |
| B1/B2/B4/B4a, ST9, AS2/AS15, MT1/MT2 | Reservation from capture and prepared arguments, last use | Alias, children, root loan after block release; model 16 combinations and mode/loan mutations detected | P — no graph of reference fields |
| AS13/AS14, MT3, L1/L6 | Sustainable target, unique destruction by its scope, mandatory waiting | Refusal of flight, inactive drop, rejected launch injected, traces of destruction | P — Statutory arrangements |
| ME2/ME3, TF1–TF5, B4c | Nominal resolution of helper methods and contracts | Type of historical feature, direct returns of structures references, incompatible types refused | P — projections of still open borrowed results |

Final target O2: 14 methods, 15 C executions, one with failed launch
Injected, 29 static refusals. Model O0/O2: 11 executions and five refusals.
Six mutations detected; O0 addition on destruction.
The number of people who are not able to use the same methods is very high.
The native regression precedes the last shared test and assertions of
Additional destruction; final targeted passages cover these additions.

<a id="captures-de-structures-contenant-des-références"></a>

### Captures of structures containing references

Rapport : [ASYNC_STRUCT_REFERENCE_FIELDS_CYCLE.md](cycles/ASYNC_STRUCT_REFERENCE_FIELDS_CYCLE.md).

| Rules | Invariant and interactions | Targeted evidence | Limites |
| --- | --- | --- | --- |
| ST5/ST7, AS8/AS9 | Record pointers and correct mixed offsets | Int/&Int/&mut Int, helpers, native methods, loops and blocks; offset/reading mutations detected | P — interlocked construction with unexecuted reference |
| B1/B2/B4/B4a, AS2/AS13/AS15, MT1–MT4/MT8 | Capture → carrier → target remains protective | 16 model cases, alias, separate/disabling arguments, rejected leaks; bridge/capture mutations detected | P — direct projections, replacement effects and more general open graphs |
| AS10/AS14, L1/L6, MT7 | Inactive waiting or drop releases loans without destroying targets | LaunchFailed injected, unique traces, re-use of slot after drop, access allowed after last use | P — arrangements and types of arrangements |
| PR1, ancien A5 | Historical Reset sees transitive dependencies | Counter example wrongly admitted corrected in check and compilation; mutation first link detected | P — API always removed from normal profile |
| U1, B1/B2, ancien A5 | Historical Fixtures actually reach their memory properties | 20 failures and 39 errors reproduced before change; explicit uses added, destruction oracles and model unchanged; 72 successful methods under fatal UBSan | P — no comprehensive evidence |

Final target O2: 12 methods, 16 C executions and 25 programmes rejected in
The two courses (50 checks) are targeted + model O0: 13 successful methods.
Model O0/O2: 11 executions and five refusals. Five behavioral mutations
detected; another creates a divergence between check (acceptance) and compilation
(refused by another control), without memory detection at execution. The six previous mutations are replayed with
Success. O2 regressions: 244 native methods and 76 contracts/references,
The revalidation of the 72 historical methods does not use
Explicit optimization option. Failed initial logs retained in the report.

<a id="directives-et-contrats-du-noyau"></a>

## Guidelines and contracts of the core

| Rule | Invariant | Verification performed | Limites |
|---|---|---|---|
| G6–G7, AS7 | The directive configures the right scope or definition and checks the terminals before conversion | Two-point, K/M/G templates, overflows, lexical heritage, empty, duplicated and out-of-limit capacity | P — the historical comma remains accepted |
| TF4–TF5, RT3, RT5 | Each specialization meets all requirements and retains its results and borrowings | Two-method contracts, choice of R, signatures and method not declared refused, Future and capture until join | P — integrated runtime, body checked with concrete types |
| MT10 | Exclusiveity persists until the end of the call or the destruction of the result, depending on the form | The two annotations, relays, capture async, join and LaunchFailed under UBSan | P — scope of direct results |
| G3 | The elements keep their addresses and logical order on the down front | Oracle C of addresses, front and direction of slices, including the async relay of a sub-tranche | P — cases in the [report](cycles/CORE_ANNOTATIONS_CYCLE.md) |

<a id="closures-réutilisables"></a>

## Reusable closures

| Rules | Invariant | Verification performed | Limites |
|---|---|---|---|
| N1–N3, N6 | The creation initializes the catches according to their mode and the return has a common type | Copy to creation, scalar move, refusal of non-Copy without move and heterogeneous returns | P — scalar and pool allowances exercised |
| N4–N5, N7 | A catch retains the dependence of the loan or the responsibility to clean up the allocation | Retained pool reference, premature destruction and rejected range exit, single destruction and re-used slot | P — borrowing to local scalars outside the implemented perimeter |
| N8 | Repeat calls and parameter passage retain the concrete type and its captures | Immediate appeal, repeated calls, two specialized types and refusal of incompatible signature | P — voir [CLOSURES_CYCLE.md](cycles/CLOSURES_CYCLE.md) |

<a id="intégration-du-noyau-après-le-tri-des-échecs"></a>

## Integration of the kernel after sorting of failures

| Rules | Invariant | Verification performed | Limites |
|---|---|---|---|
| N4–N6, N8, E6 | A projection returned by a task keeps its target and access | Constant and dynamic projections, blocking and async wait, injected launch failure, 13 projection regressions | P — cases identified in the sorting |
| N1, V1, E4, AS4 | The type remains consistent between value and storage, before and after suspension | Boolean result and suspensionable branches, refusal of `i32` on `A<i32>`, contextual writing and refusal of overflow | P — targeted controls |
| N2, N4, N7, RT3–RT7 | Dropping requires proof of durability and runtime recovers the result | Direct Wrapper, typical waiting, abandonment without local dependency, refusal with local borrowing and cleaning at closing | P — proof limited to concrete scalar branches, open public propagation |
| N2, N7 | Cleaning a structure transferred to a closure is unique | Two shared calls, invalidated source and one destruction of the structure | P — [cycle report](cycles/CORE_INTEGRATION_FOLLOWUP_CYCLE.md) |

<a id="backend-rust--attente-directe-et-agrégats-empruntés"></a>

### Backend Rust — Direct expectation and borrowed aggregates

See [cycle report](cycles/CORE_COMPOSITION_CYCLE.md#attente-directe-et-agrégats-empruntés-dans-le-backend-rust).
Witnesses executed via [check_rust_task_regions.py](../validation/check_rust_task_regions.py)
with C11, pthread and UBSan to `-O0` and `-O2`.

| Rule | Ownership | Evidence and limitation |
| --- | --- | --- |
| AS4, N6 | A future inactive is consumed once. The parent takes back the child's poll and finds his temporary and marks. | P — several levels, block, branch, loop and `continue` executed; double waiting and waiting in `main` Migration between workers not imposed. |
| AS12, AS13, N4, N5, N8 | The capture keeps its targets and the result retains only the dependencies deducted from the contract. | P — aggregate with relayed borrowing, two-field capture and projection of one, choice of receiver by branch; local target and mutable conflict refused. `AsyncHandle` and dependent results via `join()` non couverts. |
| AS14, N7 | The child's region is recoverable after transfer of its result. | P — four successive expectations with an assertion C excluding overflowing to a dedicated area; the witness of destruction before starting remains green. ASan and independent audit not executed. |

<a id="backend-rust--propriétaires-et-complétions-de-tâches"></a>

### Backend Rust — owners and task completions

[ Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#ressources-et-complétions-de-tâches-dans-le-backend-rust).
`validation/check_rust_task_regions.py` : 27 programmes `-O0` and `-O2`
Under UBSan, 18 refusals. Five close follow-up: 53 witnesses C.

| Rule | Ownership | Evidence and limitation |
| --- | --- | --- |
| N2, N4, N7, AS10, AS12, AS14 | The responsibility of slots `A<T>` follows the aggregate between the appellant, the Future and the result. | P — aggregate interlocked with two slots, injected pool, destruction before start-up, transfer and reuse, pattern `Ok(_)`, local pool too short refused. Owners in another slot or vector off perimeter. |
| N5, N8, RT5, RT6 | `join()` frees execution reservations and keeps borrowings from the result only `Ok`. | P — aggregat with a mutable borrowing via a handle relay, a native borrowing result via a handle relay `Result`, access before last use denied. |
| AS4, RT2, RT5, RT6 | `AsyncHandle.await` suspend without losing completion and consume the handle once. | P — forced wake up before and after sleep, indirect wait by a Future, success with borrowing or slot owner and `LaunchFailed` injected; second await and launch blocking in `main` No migration required, no ASan/Tsan, or independent audit. |

<a id="backend-rust--nettoyage-composé-des-slots-possédés"></a>

### Backend Rust — cleaning of owned slots

[ Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#nettoyage-composé-des-slots-possédés).

| Rules | Ownership | Evidence and limitation |
| --- | --- | --- |
| N2, N4, N7, L3, L7 | An adopted slot follows the recipient and is returned to his pool after his descendants. | P — struct and enum in pool, vector structure, chain in same pool with trace of refunds, transfer by `.await`. Three refusals for the life of the source pool. C11 under UBSan to `-O0` and `-O2`. |
| N4, N5, L4 | Cleaning follows only the proprietary fields. | P — reference stored and slot owner in the same vector element, target still accessible after cleaning the container. Crust does not offer custom destroyers. |

<a id="post-ast-rust--provenance-et-résumés"></a>

### Post-AST Rust — source and abstracts

[ Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#provenance-et-résumés-du-post-ast-rust).

| Rules | Ownership | Evidence and limitation |
| --- | --- | --- |
| N2–N4 | An interlocked reception retains the source of the displacement and dependencies of the possessed field. | P — direct assertion of the link, re-used summary and original pool on two block outputs. |
| N4, N6–N8 | A junction retains both sources and the placement may reserve a common location for exclusive branches. | P — direct assertion of origin and destination, then 84 C and 54 refusal witnesses in six suites. Targeted verification of the Rust sub-assembly. |

Post-AST performance measurement on 11 synthetic programs. Both
binary accept each case and emit the same C. The medians, the
The protocol and the limits of the reconstituted reference are given in the
[measurement report](cycles/CORE_COMPOSITION_CYCLE.md#mesure-du-coût-des-résumés).

<a id="post-ast-rust--plan-de-possession"></a>

### Post-AST Rust — possession plan

| Rules | Ownership | Evidence and limitation |
| --- | --- | --- |
| G1, N2, N4, N7, L3, L7 | The placement covers the recipient and the generated route makes the seed slots before their parent. | P — two Rust tests, 70 C-witnesses under UBSan and 47 refusals.](cycles/CORE_COMPOSITION_CYCLE.md#plan-de-possession-des-agrégats-dans-le-post-ast) |

<a id="post-ast-rust--adoption-et-transfert"></a>

### Post-AST Rust — Adoption and Transfer

| Rules | Ownership | Evidence and limitation |
| --- | --- | --- |
| N2, N4, N7, L3, L7 | The transferred root takes the adopted slots, returned from leaves to the root. | P — exact trace after block release and call, re-use of slots, async transfer exercised, 60 C-witches under UBSan and 41 refusals. [Report](cycles/CORE_COMPOSITION_CYCLE.md#adoption-et-transfert-selon-le-plan-de-possession) |

<a id="g1--scalaires-synchrones-et-destination-finale"></a>

### G1 — Synchronous scalar and final destination

| Rule | Ownership | Evidence and limitation |
| --- | --- | --- |
| G1 | The building uses the reservation of the receiver or caller when available and compatible with the path. | P — five witnesses instrumented from the cursor, 75 C-witnesses total under UBSan and 47 refusals. Promotions to multiple movements and the overall choice between telescopes remain open. [Report](cycles/CORE_COMPOSITION_CYCLE.md#placement-des-scalaires-dans-leur-destination-finale) |

<a id="g1--chaînes-destinations-multiples-et-frames"></a>

### G1 — chains, multiple destinations and frames

| Rule | Ownership | Evidence and limitation |
| --- | --- | --- |
| G1, N2, N7 | Compatible transfers reuse a durable address and the path executed determines the cleaning scope. | P — 2 Rust tests, 95 C-controls under UBSan and 54 refusals. Targeted cases with channels, competing receivers, calling and suspension. [Report](cycles/CORE_COMPOSITION_CYCLE.md#g1--chaînes-de-déplacements-destinations-multiples-et-frames) |

<a id="g9--choix-de-la-datastack-à-régions"></a>

### G9 — choice of regional datatack

| Rules | Ownership | Evidence and limitation |
| --- | --- | --- |
| G4, G6–G10 | The post-AST limits simultaneous acquisitions, directs indeterminate acquisitions to a dedicated region and respects the limits of the template. | P — 5 new witnesses and 100 C witnesses in total under UBSan, 54 refusals. Conservative terminals at junctions and calls. [Report](cycles/CORE_COMPOSITION_CYCLE.md#g9--placement-des-régions-à-partir-du-post-ast) |

<a id="g10--recul-groupé-du-curseur-régional"></a>

### G10 — grouping of the regional cursor

| Rules | Ownership | Evidence and limitation |
| --- | --- | --- |
| G8, G10, G12 | The cleaning precedes the retreat and a transferred slot stops the retreat at its border. | P — two native cursor tracks, address control after transfer, 102 C-witnesses under UBSan and 54 refusals. [Report](cycles/CORE_COMPOSITION_CYCLE.md#g10--recul-groupé-du-curseur-régional) |

### Inline assembly and target-sized integers

| Contract | Evidence and limitation |
| --- | --- |
| `@unchecked` preserves ordinary Crust checks. `addr` carries its source dependency into a later assembly use. | P — targeted refusals cover use after move, dropping an address target before assembly, an escaping local address, and invalid operands. |
| `usize` uses the target pointer width. | P — maximum values accepted for i686 and x86-64, overflow refused for i686. Generated C asserts the configured pointer width. |
| Explicit `mov` transfers use stable slots across stack changes. The backend observes indirect memory writes. | P — Linux x86-64 `read` witness passed at `-O0` and `-O2`. The full `File` sketch still needs slice and method support. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#inline-assembly-and-usize) |

### Standard-library file I/O

| Contract | Evidence and limitation |
| --- | --- |
| The target selects the platform module before imports are resolved. | Linux x86-64 with 64-bit pointers passed. Imports on Linux AArch64 and Linux x32 were refused. |
| The Unix file owns its descriptor. Destroying the public wrapper closes it through the inner field after a move. | Both optimized and unoptimized executions reopened a real file 128 times with a 32-descriptor limit. Direct descriptor construction and external access to platform calls were refused. |
| Reading respects the mutable byte slice budget and returns EOF or an error. | A two-byte read, an empty slice, EOF, an unterminated path, and a missing file passed. Two invalid borrow cases were refused. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#standard-library-file-io) |

| macOS and Windows File contract | Evidence and limitation |
| --- | --- |
| One facade selects the target's File and destroys the platform descriptor with the wrapper. | macOS ARM64 ran both optimization levels under UBSan, including 128 moves and reopens with 32 descriptors. Linux x86-64 was rerun. Windows x86-64 and ARM64 linked both PE witnesses. Windows runtime execution remains open. |

| Assembly-backed File | Evidence and limitation |
| --- | --- |
| The selected backend owns the platform resource and calls its native API from assembly. | Linux x86-64 and both macOS architectures ran the File witness at -O0 and -O2. Windows x86-64 and ARM64 linked both optimization levels. Execution on Windows remains unverified. |

| Windows x86-64 execution | Evidence and limitation |
| --- | --- |
| Reads and errors match the common File witness. The owned HANDLE closes after a move and scope exit. | Wine 11.21 passed at `-O0` and `-O2`. The instrumented witness observed exactly 129 successful `CloseHandle` calls and checked that every handle became invalid. Native Windows and ARM64 execution remain open. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#windows-execution-under-wine) |

### Blocking and async File operations

| Contract | Evidence and limitation |
| --- | --- |
| `read` and `write` are bounded by the caller's slice. `stats` reports the size of the open file. Creation is exclusive and deletion removes the path. | The common witness checked actual byte counts, file contents, EOF, a Unicode path, exclusive creation, write permission, invalid paths, and a missing file after deletion. Both APIs ran at `-O0` and `-O2` on macOS ARM64 and x86-64 and Linux x86-64 under fatal UBSan, and on Windows x86-64 under Wine. Windows ARM64 cross-linked. The blocking macOS ARM64 witness also passed with `crustc`. |
| N2, N4–N5, N7–N8. Pending file operations retain the owner and buffer loans. | The compiler refused early destruction of the owner, a write to the destination of a pending read, and external construction of the private async File. The executable witness also moved the file before closing and reopening it. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#blocking-and-async-file-operations) |

### Standard-library networking

| Contract | Evidence and limitation |
| --- | --- |
| TCP listeners accept independent connections. UDP listeners receive the sender's endpoint, preserve message boundaries, and report truncation. Connected sockets exchange bytes using caller-provided buffers. | Loopback traces matched at `-O0` and `-O2` on macOS ARM64 and x86-64 under UBSan, Linux x86-64 in Docker with Rosetta, and Windows x86-64 under Wine. `crustc` matched under UBSan on macOS ARM64. Windows ARM64 linked at both levels. |
| A moved socket retains one owner and its destructor releases the socket. External packages cannot construct a socket from an implicit default. | The same witnesses moved, dropped, and rebound 128 UDP listeners after a failed duplicate bind. Both compilers rejected direct and nested default construction on macOS ARM64. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#tcp-and-udp-sockets) |
| Typed IPv4 blocking sockets use caller-provided buffers. An oversized UDP datagram is consumed and an empty UDP slice still receives a datagram. | The updated Rust compiler witness ran at `-O0` and `-O2` on macOS ARM64 and x86-64 under UBSan and on Windows x86-64 under Wine. A Linux x86-64 witness exchanged traffic inside one container at both levels. Windows ARM64 linked at both levels. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#typed-socket-addresses-and-async-method-captures) |
| An async method's Future retains the receiver and mutable slice. | The targeted witness wrote through the slice after yielding and read the updated byte after `.await`. The compiler rejected an early receiver drop and an early write to the destination. |
| The async reactor wakes the awaiting task and preserves its socket and buffer loans. | TCP and UDP loopback witnesses exercise epoll, kqueue and IOCP. The TCP witness moves each half into a separate task and observes EOF after dropping the connection. An early drop is refused. The UDP witness checks truncation consumption, the sender of an empty datagram, and a reply received into an exactly sized buffer. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#async-tcp-udp-and-socket-wakeups) |
| `crustc` can call `SocketAddr::parse(&str)`. | The two compilers agree on a valid IPv4 address, a port overflow and an embedded NUL at `-O0` and `-O2` under UBSan on macOS ARM64. |
| N1, N3, N6, N8: scalar `Option` carries its payload type across calls and `match`. | `crustc` executed a signed `Some`, a `None` arm with an early return, and an inferred `i32` fallback. Both compilers refused an incompatible payload, reuse after a move, and a missing arm. |
| `crustc` builds the complete typed blocking network witness. | The independent TCP and UDP peers matched both compilers at `-O0` and `-O2` with fatal UBSan on macOS ARM64. The witness exercises explicit and default TCP backlog, TCP EOF, UDP datagram boundaries, and 128 port reuses after moving and destroying the owner. Three attempts to construct a socket through its private representation were refused. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#scalar-option-and-blocking-network-with-crustc) |

### Borrowed byte-array prefixes

| Contract | Evidence and limitation |
| --- | --- |
| The prefix length is checked before constructing the borrowed slice. | macOS ARM64 UBSan accepted dynamic bounds zero and full length and trapped negative and oversized bounds. Three compile-time diagnostics checked. The Crust bootstrap witness matched Rust token spans on a 13-byte file. |

### Short-circuit boolean expressions

| Contract | Evidence |
| --- | --- |
| The right operand runs only when required. Both operands are boolean. | Skipped slice lookups, observed right-hand calls and nested logic passed under UBSan at both optimization levels. Two invalid operand types refused. |

### Fixed token-array writes

| Contract | Evidence and limitation |
| --- | --- |
| A checked assignment replaces the complete token in a fixed array slot. | macOS ARM64 UBSan confirmed dynamic replacement, preservation of the neighboring slot, and a bounds failure. Resource-owning elements remain outside this path. |

### Structural array replication

| Contract | Evidence |
| --- | --- |
| One initializer evaluation produces independent structurally replicable elements. | macOS ARM64 UBSan at `-O0` and `-O2` checked nested fields, zero length and independent writes. Two nonreplicable structures refused. |

### Typed borrowed prefixes

| Contract | Evidence |
| --- | --- |
| The parser reads typed elements within the borrowed prefix, which keeps the array live. | macOS ARM64 UBSan confirmed correct Token stride and an excluded-slot trap at both optimization levels. An early array drop was refused. |

### Slice element reborrows

| Contract | Evidence |
| --- | --- |
| An indexed reborrow is bounded and retains the parent dependency. | UBSan execution, bounds trap, three borrow refusals, and the bootstrap token walk. |

### Two-bound slice reborrows

| Contract | Evidence |
| --- | --- |
| A subslice preserves the parent dependency and checks both bounds before computing the new address. | Six UBSan executions on macOS ARM64, two static refusals, and the bootstrap token walk with spelling views. |

### Slice equality

| Contract | Evidence |
| --- | --- |
| Slice identities compare by address and length. Byte contents compare through the std method. | macOS ARM64 UBSan at both optimization levels, three type refusals, and the bootstrap keyword witness. |

### Exact numeric casts

| Contract | Evidence |
| --- | --- |
| `as` preserves every value of the numeric source type. | macOS ARM64 UBSan at both optimization levels, six refusals, pointer-width comparison for i686 and x86-64, and the bootstrap decimal witness. |

### Integer bitwise AND

| Contract | Evidence |
| --- | --- |
| `&` preserves the common integer type and width. | All seven integer types under macOS ARM64 UBSan at both optimization levels, three type refusals, and five lexer UTF-8 witnesses. |

### Checked left shifts

| Contract | Evidence |
| --- | --- |
| `<<` preserves the left integer type and checks both count and result. | All seven integer types under macOS ARM64 UBSan at both optimization levels, four dynamic failures, and three static refusals. |

### Checked right shifts

| Contract | Evidence |
| --- | --- |
| `>>` preserves the type of the left operand, checks the count and extends the sign for signed values. | macOS ARM64 UBSan at both optimization levels, seven integer types, two dynamic traps, three static refusals and four UTF-8 witnesses. |

### Integer OR, XOR and complement

| Contract | Evidence |
| --- | --- |
| Bitwise operators preserve the integer type and reject noninteger operands. | macOS ARM64 UBSan at both optimization levels, three invalid operand cases, and seven lexer string witnesses. |

### Process arguments

| Contract | Evidence |
| --- | --- |
| `std::env::args()` excludes the executable name and returns process-lifetime UTF-8 views or an error. | Four macOS UBSan cases at both optimization levels. Unicode path executed on macOS and Wine x86-64. Linux x86-64 compiled and linked. |

### Bootstrap AST and mutable slice writes

| Contract | Evidence |
| --- | --- |
| The bootstrap emits the same projected syntax tree for supported inputs. | 13 comparisons against the Rust frontend on macOS ARM64 under UBSan, including the bootstrap's own source. Nine malformed inputs refused. |
| The bootstrap detects source files that exceed its input budget. | 65536 bytes accepted, 65537 bytes refused. |
| Indexed replacement through a mutable slice changes the selected structurally replicable aggregate. | UBSan witness printed 3 and 9 for the two-element array. Out-of-range write trapped. Shared slice write refused statically. Dependency-bearing replacements remain outside this lowering. |

### Bootstrap extended syntax comparison

| Contract | Evidence |
| --- | --- |
| Supported Crust syntax projects to the Rust frontend's AST, including visibility and assembly operand spans. | 65 comparisons under macOS ARM64 UBSan, including the bootstrap itself, target-filtered stdlib and 32 Rust-accepted examples. |
| Syntax and source-budget failures produce explicit refusal. | Twelve syntax refusals, a malformed UTF-8 refusal and acceptance/refusal at 131072/131073 bytes. |
| Excluded target declarations are removed before parsing. | Host-target differential comparison with a malformed excluded declaration and the target-filtered standard library. Other targets were not executed in this cycle. |

### Bootstrap scope and binding projection

| Contract | Evidence |
| --- | --- |
| The Crust bootstrap links names to visible declarations and records lexical scope membership and parentage. | 69 AST and static graph comparisons against Rust under host UBSan. The inputs include nested shadowing, named moves, match and tuple bindings, closure references and assembly operands. Capture sets and memory facts are outside this comparison. |

### Bootstrap static tree facts

| Contract | Evidence |
| --- | --- |
| The bootstrap preserves ordered operands, syntactic memory facts, control-flow destinations, scope ends and closure capture sources. | 70 comparisons against the Rust frontend under macOS ARM64 UBSan, including nested closures and loops. Capture sets and scope ends were compared by syntax identity. |

### Bootstrap rule checker

| Contract | Evidence |
| --- | --- |
| The bootstrap checks the supported scalar subset from resolved bindings and ordered operands. | Twelve macOS ARM64 UBSan witnesses cover scalar typing, explicit copy, use after move, repeated drop, immutable replacement and call arity. An unsupported borrow and conditional return status 9. This is partial coverage of the core rules. |

### Bootstrap branch states and direct loans

| Contract | Evidence |
| --- | --- |
| Every reaching branch must permit a scalar use. | The checker refused a use after a conditional drop and accepted the same use when the dropping branch returned. Value-producing branches and loops remain outside this pass. |
| Direct scalar loans require a live target and compatible access. | UBSan witnesses exercised shared and exclusive loans, direct writes through a reference, and mutations before and after its last use. Ambiguous overlaps return status 9. |
| Fixed-width integer literals fit their contextual type after applying the sign. | Witnesses exercised the signed 32-bit minimum, the unsigned 64-bit maximum and out-of-range signed and unsigned literals. |

### Bootstrap loops and direct loan conflicts

| Contract | Evidence |
| --- | --- |
| A while loop preserves incoming availability on the supported back edge. | UBSan witnesses cover state-preserving loops and an explicit coverage refusal for a state-changing loop. |
| A direct loan blocks an incompatible access before its last reachable use in the supported straight-line subset. | UBSan witness checks N5 before the later use and accepts after the last use or explicit destruction. |

### Bootstrap loop edges and reference transfers

| Contract | Evidence |
| --- | --- |
| Scalar loop back edges and breaks preserve availability obligations. | UBSan witnesses include continue, repeated drop, and use after a break that can carry a destroyed binding. |
| Moving a scalar reference preserves the target and exclusivity. | UBSan witnesses cover named moves, assignment at declaration and type mismatch for annotated direct loans. |

### Host executable build and bootstrap checker

| Contract | Evidence |
| --- | --- |
| A checked host program builds to a runnable executable. | The README pool example prints 10, 20, 30. The bootstrap package builds. A refused use after drop produces no output executable. |
| Scalar conditionals and direct scalar pool allocations preserve supported type and availability obligations. | 47 total bootstrap checker witnesses under macOS ARM64 UBSan. The bootstrap checker still has partial coverage. |

### Bootstrap scalar results, pool ownership and reborrows

| Contract | Evidence |
| --- | --- |
| Conditional scalar values preserve type and availability at the join. | UBSan witnesses exercise contextual type, mismatched arm results and a conditional move before a later use. |
| Moving a direct scalar pool allocation preserves its provenance and invalidates the previous binding. | UBSan witnesses exercise a named move, an assignment move and rejection of a drop through the old binding. |
| A live scalar reborrow reserves its parent chain for incompatible access. | UBSan witnesses cover writes and drop before the last use, reuse after the last use and a nested reborrow. Returned loans remain open. |

### Bootstrap executable and mixed loop exits

| Contract | Evidence |
| --- | --- |
| A break contributes to loop exit availability and a continue contributes to the back edge. | Three new mixed-edge witnesses passed, including a valid use on the path that continues through the body and two invalid uses after a drop. |
| The generated host checker runs the regression corpus directly. | macOS ARM64 `build/crust-bootstrap` passed 59 checker witnesses and 72 representation comparisons. The UBSan build also passed. |

### Bootstrap returned scalar loans

| Contract | Evidence |
| --- | --- |
| A scalar loan returned from a function must originate outside its local storage. | Host and UBSan witnesses accept direct parameter returns and explicit parameter reborrows and reject returns into local storage or a by-value parameter. |
| A direct identity call propagates its argument's loan to the result. | Host and UBSan witnesses reject a parent write before the returned loan's last use and accept it afterward. General inferred contracts remain open. |

### Bootstrap conditional scalar loan origins

| Contract | Evidence |
| --- | --- |
| A scalar loan returned by a supported conditional call reserves both possible targets. | macOS ARM64 host and UBSan witnesses refuse mutation of the second possible target before the last use and accept writes to both targets afterward. General contracts remain open. |

### Bootstrap conditional loan relay

| Contract | Evidence |
| --- | --- |
| A supported relay preserves both possible loan origins and checks the receiver type. | macOS ARM64 host and UBSan witnesses accept writes after last use, refuse a write to the second possible target before last use, and reject a mismatched receiver annotation. |
| A named selector condition is moved into the call. | The checker refuses a later use of the boolean in both builds. |

### Bootstrap variable-width loan provenance

| Contract | Evidence |
| --- | --- |
| Supported shared scalar calls reserve each possible origin, including through relay edges. | Host and UBSan runs passed 80 checker witnesses. A third origin is protected before the last use and writable afterward. The checker conservatively uses all matching reference arguments for the supported signature family. |

### Bootstrap return provenance from function bodies

| Contract | Evidence |
| --- | --- |
| Supported return sites select the caller's reserved origins by parameter identity. | 83 checker witnesses on macOS ARM64 host and UBSan builds. Mixed-signature witnesses distinguish a returned reference from an unused reference argument. |
| Scalar argument moves respect the roots reserved by reference arguments. | The host and UBSan checker reject moving the target into the same call. Nested argument effects remain outside this check. |

### Bootstrap differential rule checks

| Contract | Evidence |
| --- | --- |
| The Rust and Crust checkers agree on supported loan and ownership witnesses. | Ten verdict comparisons passed on the macOS ARM64 host binary and UBSan build, including returned calls, loop-carried scalar loans and a single owned pool field. General aggregate cleanup and call effects remain open. |

### Bootstrap ownership across structure fields

| Contract | Evidence |
| --- | --- |
| A checked structure retains each field's pool dependency through construction and move. | Five additional Rust/Crust verdict comparisons under macOS ARM64 with and without UBSan cover separate pools, nested constructors, element mismatch, adoption of an existing allocation and invalid reuse of its moved binding. |

### Bootstrap nested owner moves and argument effects

| Contract | Evidence |
| --- | --- |
| A field adopting an owned structure preserves its resource dependencies and invalidates the original binding. | Two new Rust/Crust verdict comparisons pass on macOS ARM64 with and without UBSan. |
| A nested scalar argument respects a shared reservation on the target. | Rust and Crust both accept copying the target and reject moving it. |

### Bootstrap recursive return contracts

| Contract | Evidence |
| --- | --- |
| Recursive return contracts conservatively preserve source dependencies. | The host and UBSan comparisons cover direct and mutual recursion. The verifier computes the contract before checking calls. |
| A nested scalar read conflicts with an exclusive call reservation. | Both Rust and Crust refuse the nested copy witness. |
| The existing backend executes composed destruction. | The separate Rust backend suite passed three destructor programs at both optimization levels under UBSan and confirmed four static refusals. |

### Crust-generated pool cleanup executable

| Contract | Evidence |
| --- | --- |
| A moved scalar pool allocation releases its slot at explicit drop or scope exit under the supported Crust code generator. | The macOS ARM64 host and UBSan bootstrap runs compiled and executed the emitted C under UBSan. A capacity-one pool printed 10, 20, 30 across a move, scope exit and explicit drop. |
| Backend coverage and verification failures prevent C emission. | The repeated-drop witness returned 8 with a diagnostic and no C. The unsupported u64 pool returned 9 with empty output. |

### Crust-generated nested aggregate cleanup

| Contract | Evidence |
| --- | --- |
| Destroying a supported nested aggregate releases its owned slots after a move, scope exit or explicit drop. | Both macOS ARM64 bootstrap builds emitted C that compiled with warnings as errors and ran under UBSan. The two capacity-one pools were reused and the program printed 10, 20, 30. |

### Bootstrap virtual storage and destructor execution

| Contract | Evidence |
| --- | --- |
| The supported inline destructor runs before its owned fields and runs once after a move. | The Crust-generated and Rust-generated executables both printed 10, 20, 30 for explicit destruction of a moved parent and implicit destruction after scope exit. Generated Crust C ran under UBSan. |
| The supported pool storage commits pages on demand and rewinds after cleanup. | The generated execution tests covered adjacent scopes and 4096-slot pools on macOS ARM64. The backend computes a conservative bound from the supported syntax. |

### Bootstrap destructor sequences and early exit

| Contract | Evidence |
| --- | --- |
| A supported custom destructor observes the fields in its body order after a move. | Host and UBSan bootstrap builds emitted executables matching the Rust trace for an empty destructor and a three-print destructor with explicit Void. |
| A void return cleans up all entered scopes and skips later instructions. | The generated executable matched the Rust trace for an explicit drop followed by a return from a nested block. |

### Bootstrap destructors, named pools and region storage

| Contract | Evidence |
| --- | --- |
| A moved object is destroyed once before its fields, and destructor control flow completes before cleanup resumes. | macOS ARM64 execution traces compare the Crust and Rust backends for explicit drop, scope exit, conditionals, loops, early return, and scalar helper calls. C emitted by Crust runs under UBSan. |
| Named pool slots retain their payload and ownership through moves and can be reused after cleanup. | Differential executions cover positional ownership by field, named and shorthand constructors, partial and empty defaults, and projections of scalar fields. The reordered initializer witness exposed and caught the former discrepancy in field destruction order. |
| A pool reserves independent capacity for each supported enum arm. | A capacity-one pool held a unit variant and a resource-bearing variant simultaneously. Dropping and reallocating the latter matched the Rust destruction trace. |
| Region storage honors explicit capacity, transfers a live value out of a local configuration, and reuses released space. | Differential executions cover global saturation, local growth saturation, explicit count and dedicated fallback, inferred region size, and continued pushes after a block transfer. The checker and reference reject a transfer that would outlive its pool. |

### Bootstrap region fixture parity and nominal destruction

| Contract | Evidence |
| --- | --- |
| Regional growth, transfer and cleanup maintain observable behavior on the Rust regional suite (N4, N7, G6–G10). | All 14 existing Rust fixtures matched exit status, stdout and stderr on macOS ARM64 at `-O0` and `-O2` under UBSan. Generated calls exercise dedicated placement for recursive and retained allocations. |
| Named values preserve their cleanup after being adopted into a pool (N2, N7). | Differential traces cover a named input with an owned slot, nested default constructors, scalar field formatting and a pool local to a destructor. |
| A destructor executes before cleaning its fields, including after a call or transfer (N7, N8). | All three Rust destructor fixtures passed, including the moved capture destroyed after a yield. Additional differential cases cover inline fields surviving a pool move out of a block, implicit cleanup after two suspensions, exit with an abandoned handle, and injected launch failure. |

### Bootstrap lexical parity

| Contract | Evidence |
| --- | --- |
| Lexical terminals and TX1 produce matching token classes and byte spans, including EOF. | `validation/check_crust_lexer.py` matched 488 raw token streams before target selection or parsing, with a native and a UBSan build on macOS ARM64. |
| Malformed text, numbers and assembly produce the expected lexical error at the same byte. | 311 differential refusals matched Rust by diagnostic category and byte offset. Five malformed UTF-8 files and the 128 KiB budget were checked separately at the input boundary. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#bootstrap-lexer-parity). |

### Bootstrap parser parity

| Contract | Evidence |
| --- | --- |
| The bootstrap produces the same program AST as the Rust parser after host target selection. | 1,506 ASTs and 3,415 rejection verdicts matched in native and UBSan runs on macOS ARM64. The comparison checks node kind, ordered children, parent, byte spans and visibility before constructing the static execution tree. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#bootstrap-parser-parity). |

### Bootstrap static tree corpus parity

| Contract | Evidence |
| --- | --- |
| Syntax-derived scope, binding, operand and control-flow links agree across compilers. | 1,512 program trees matched in native and UBSan builds on macOS ARM64. The comparison includes declared type and initializer links, mutability, captures, exit destinations and scope ends. |
| External signature parameters remain local and a placeholder move creates no destination binding. | Both focused regressions match after isolating each external signature scope and recording `move _;` as a syntax fact. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#bootstrap-static-tree-corpus-parity). |

### Bootstrap verifier corpus comparison

| Contract | Evidence |
| --- | --- |
| N1–N8 verdict comparison at the static-tree boundary | The UBSan comparison matched 201 acceptances and 1,155 rejections across 1,582 ASTs, with no contradictory verdicts. 226 cases remain unsupported (65 accepted and 161 rejected by Rust). Strict parity exits with status 1. |
| N4, N5, N7 and HM6: stored dependencies and task transfers | Differential fixtures cover disjoint stored reborrows, an active reborrow blocking destruction of its parent, a map entry retaining a source pool until removal, and access before and after completion of a task with an exclusive capture. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#stored-dependencies-and-task-captures). |
| E2–E6, N4–N8: fixed places, control flow, task results and scalar map entry loans | Executed verdict regressions cover nested array bounds, a loan ending in an assignment RHS, a loan retained after a write, moves and typed array arguments, pooled enum matches, scalar task completions and a map entry loan blocking removal. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#fixed-places-scalar-tasks-and-collection-verdicts). |
| N1, N4, N6, N7 and N8 focused regressions | Cases cover bounded pool and region capacity, fixed layout cycles and indirect recursive types, destructor signatures, intermediate moves, and mutable scalar loans passed to calls. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#bootstrap-verifier-corpus-comparison). |


#### Deferred entry effects and returned handles

| Contract | Evidence |
| --- | --- |
| N4 and N5: a launched task reserves a captured entry until completion. | Focused accepted and rejected witnesses distinguish access after and before await. The corpus also exercises a shorter incoming referent and the launch-failure path. |
| N4, N6 and N7: movement preserves deferred effects and result dependencies. | Corpus witnesses cover a native factory, synchronous and asynchronous waits, recursive enum relays, and an async handle carrying an aggregate with a pooled allocation. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#deferred-entry-effects-and-returned-handles). |
| N1–N8 verdict parity | The UBSan comparison matched 231 acceptances and 1,204 rejections across 1,587 ASTs on macOS ARM64, with zero contradictory verdicts and 152 unsupported cases (36 Rust acceptances and 116 Rust rejections). Strict parity exited with status 1. |
| N4–N7: native result transfer, conditional waits and aggregate provenance | The macOS ARM64 native and UBSan comparisons matched 246 acceptances and 1,265 rejections over 1,591 ASTs, with zero contradictory verdicts and 80 unsupported cases (21 Rust acceptances and 59 Rust rejections). Targeted regressions refused abandonment of a nested handle and mutation of an alternate borrow root before its last use. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-results-conditional-waits-and-aggregate-provenance). |
| N1–N8: remaining Rust rejections | In native and UBSan runs on macOS ARM64, both verifiers accepted 251 and rejected 1,330 of 1,602 ASTs, with no contradictory verdicts. Crust now rejects all 59 previously unsupported inputs that Rust rejects. The 21 unsupported inputs accepted by Rust still prevent strict parity. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#verifier-parity-on-the-remaining-rust-rejections). |
| N1–N8: remaining Rust acceptances | On macOS ARM64, the strict native and UBSan verifier comparisons both passed: 272 shared acceptances, 1,331 shared rejections and zero unsupported or contradictory verdicts over 1,603 parsed programs. The 21 formerly unsupported acceptances include aggregate loans, pool provenance, and autonomous handles in native results. This is verdict evidence on the corpus. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#verifier-parity-on-the-remaining-rust-acceptances). |

### Bootstrap executable comparison

| Contract | Evidence |
| --- | --- |
| Independently emitted executables reproduce the accepted corpus behavior. | The initial replay matched 66 terminating executions and two bounded traces. An intermediate macOS ARM64 comparison matched 158 terminating executions and two bounded traces in native `-O0` and UBSan `-O2`, with 112 inputs still unsupported by Crust emission. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#bootstrap-executable-comparison). |
| Pooled projections and task frame references preserve behavior through moves and suspension. | Focused UBSan comparisons matched pooled constructor overrides, reads through a borrowed enum arm and a mutable reference into a suspended task frame. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#bootstrap-executable-comparison). |
| Final accepted-corpus executable coverage for this cycle. | Both macOS ARM64 runs matched 168 terminating executions and two bounded traces out of 272. The same 102 sources remain unsupported by Crust emission. Strict parity returned 1 in native `-O0` and fatal UBSan `-O2`. The bootstrap regressions and the strict verifier replay passed. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#bootstrap-executable-comparison). |

### Native workers, aggregate results, maps and regional cleanup

| Contract | Evidence |
| --- | --- |
| RT7–RT8, N4–N7: a native worker owns its moved captures and exposes its result once. | Targeted fatal UBSan comparisons exercise borrowed captures, recursive handle results, a moved vector and failed launches. The injected native launch failures match the reference outputs and permit reuse of the frame or captured pool slot. |
| AS10, RT7, N4–N5: frame values and entry loans remain live through suspended waits. | The corpus reproduced a stale pattern binding after resume and a duplicate release after moving a native result out of a pooled enum. Focused UBSan replays passed after preserving the binding in the frame and removing the moved payload from the source slot. An injected blocking launch failure produced the same cleanup trace. |
| Map entries and owning sequence elements retain ownership across relocations. | Focused comparisons exercise replacement, removal, entry reborrowing, transfer across tasks and reuse of an underlying pool slot after destruction. |
| G9–G12: explicit budgets, scoped regions and page reclamation. | Matching witnesses include a fixed-stack limit failure, a worker using its own region budget, repeated thread frame reuse and a region that survives scope cleanup. Coverage is limited to the exercised host and scenarios. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-workers-aggregate-results-maps-and-regional-cleanup). |
| Strict executable parity of the accepted corpus. | Native `-O0` and fatal UBSan `-O2` each passed all 272 programs on macOS ARM64. Each run produced 268 exact finite traces, two independent-writer traces matching the existing output oracle, and two intentional infinite loops matching for one second. Both difference reports were empty and strict mode exited with status 0. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-workers-aggregate-results-maps-and-regional-cleanup). |


### Package bootstrap and general results

| Contract | Evidence |
| --- | --- |
| Package emission resolves public names and preserves module boundaries. | Two-module execution matches and three refused imports on macOS ARM64. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#crust-package-bootstrap). |
| N4–N6: supported results preserve payload types and move state across function and match boundaries. | Native and fatal UBSan runs matched a scalar success, a nominal error and a unit success. Both verifiers refused a mismatched payload, a result reused after a move and an incomplete match. A separate native and fatal UBSan trace matched single destruction of the active payload after forwarding, explicit drop, wildcard match and scope exit. Borrowed or pool-backed payloads remain outside this evidence. |
| Conditional moves, early returns and shared record arguments preserve the incoming and outgoing states. | Focused native and fatal UBSan comparisons exercised conditional scalar arguments, tuple destructuring, inner returns and a borrow of a record slice element. Both compilers rejected the accompanying invalid sources. |
| N5–N6: slice moves, receiver borrowing and record replacement preserve availability and alias constraints. | On macOS ARM64, focused fatal UBSan runs matched forwarding of a mutable slice, replacement of record elements and the result of a method through a nested mutable receiver. A later use of the forwarded mutable slice was refused by both compilers. |
| Standard package calls preserve process-argument and file behaviour. | Native and fatal UBSan package traces matched empty and valid arguments, invalid UTF-8, successful file reads, EOF and a missing file. Direct access to the process primitive and imports of private platform functions were refused. Coverage is for the exercised macOS ARM64 paths. |
| The Crust-written compiler emits its own executable and the emitted compiler passes strict parity. | The package loads, but the compilation still stops in the Crust verifier. Second-generation native and UBSan runs are pending. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#crust-package-bootstrap). |

| File creation policy | Evidence and limitation |
| --- | --- |
| `FilePerm.DefaultMode` preserves native creation policy. An explicit mask is applied during exclusive creation. | Sync and async witnesses passed at `-O0` and `-O2` under fatal UBSan on Linux x86-64 and both macOS architectures. The harness observed `0644` for the default and `0600` for the explicit mask. The macOS default inherited the parent ACE and the explicit file had no inherited ACE. |
| Windows creates with a protected ACL and checks the resulting handle before handing it to the caller. | Windows x86-64 ran under Wine at both optimization levels. The default path succeeded. When Wine replaced the requested ACL, the API returned error `-50` and the file remained empty. An instrumented witness checked the five ACEs in the descriptor passed to Win32 for `0600`. The ARM64 builds linked. Acceptance on native Windows remains unverified. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#file-open-modes-and-creation-permissions) |
| Compiler coverage for File | The synchronous witness also passed under fatal UBSan when emitted by `crustc` on macOS ARM64. The Rust compiler ran the asynchronous matrix above. The `crustc` backend returned status 9 on an async open with both the scalar and enum permission APIs. |

| Positional enum fields | Evidence |
| --- | --- |
| Core enum syntax and N6. Construction and matching use declaration order. | Both package compilers produced the same trace for an imported two-field variant. They refused a missing constructor argument, reversed argument types, a short pattern, and a named pattern for positional fields. The updated File witness passed under fatal UBSan. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#positional-enum-fields) |

| File cursor and path operations | Evidence and limitation |
| --- | --- |
| `seek` returns the absolute byte position. `rename` replaces an existing file when permitted. | The Rust-built compiler passed both File API witnesses on macOS and Linux under fatal UBSan and on Windows x86-64 under Wine, at `-O0` and `-O2`. Windows ARM64 linked. `crustc` passed both File API witnesses in native and fatal UBSan builds on macOS ARM64. |
| N4 and N5. Pending File operations retain receiver, path and buffer loans. | Both verifiers rejected closing the file during a pending read or seek, writing into a pending read's buffer, and writing either path during a pending rename. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#async-file-parity-on-macos-arm64) |
| N2 and N8. An async result preserves its active variant and transfers its payload once. | On macOS ARM64, both compilers produced the same scalar and destructor traces for direct await, join and blocking await. Both refused a boolean in the integer success arm. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#async-file-parity-on-macos-arm64) |

| Scalar constants | Evidence |
| --- | --- |
| Module constants retain their declared type. Associated constants use the owning type's namespace. | The Rust frontend and `crustc` agreed on module imports, an alias of the owning type, local shadowing, bitwise use, signed minimum, boolean and float constants. Both refused nine cases covering type and range, visibility, name collisions, calls, assignment and division by zero. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#scalar-constants) |

| TLS 1.3 | Evidence |
| --- | --- |
| TLS authenticates the peer and uses caller-provided buffers for application I/O. | On macOS ARM64, blocking client and server exchanges with Python negotiated TLS 1.3 and transferred bytes in native and fatal UBSan builds. The Din client rejected a hostname mismatch, an untrusted certificate and a TLS 1.2 peer. A clean close returned zero and an unannounced TCP closure produced an error. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#blocking-tls-13-on-macos-arm64) |
| The TLS connection owns the underlying TCP connection. | The Rust verifier refused external construction of the TLS connection and direct or aliased access to the internal TCP descriptor. The native and UBSan witnesses exercised consuming close. The self-hosted compiler currently refuses the by-value receiver. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#blocking-tls-13-on-macos-arm64) |

| SHA-256 | Evidence |
| --- | --- |
| One-shot and streaming calls produce the same digest with fixed state and a bounded partial block. | Fifteen inputs matched Python's `hashlib.sha256` for one-shot, portable streaming and CPU-selected streaming at `-O0` and `-O2` with fatal UBSan. macOS ARM64 selected SHA instructions. macOS and Linux x86-64 selected the portable fallback. The Rust verifier refused construction of the private state and use after consuming `finish`. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-sha-256) |
| Consuming `finish` in `crustc`. | On macOS ARM64, the same 15 vectors passed through the Crust compiler at `-O0` and under fatal UBSan at `-O2`. Reuse of the consumed context was refused. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#sha-256-with-crustc) |
| Private SHA-256 layout. | Both compilers refuse complete external construction, the same construction through an import alias, field reads, mutable field borrows, and default construction in a pool. A local homonym remains usable. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#private-standard-library-layouts-in-crustc) |

| AES-GCM | Evidence |
| --- | --- |
| AES-128 and AES-256 produce the expected ciphertext and detached tag. | 150 NIST CAVP cases across 25 message/AAD length groups per operation and key size. Hardware and portable paths passed at `-O0` and under fatal UBSan, including self-hosted `crustc` on macOS ARM64. |
| Authentication precedes output writes. | Invalid NIST tags and independently corrupted valid tags returned `AuthenticationFailed` and preserved the entire sentinel buffer. Length mismatches also preserved seal and open destinations. |
| Expanded keys have private layouts and CPU dispatch guards target instructions. | Both compilers refused external construction. Hardware dispatch ran on macOS and Linux ARM64 and x86-64. Windows kernels assembled to COFF. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-aes-gcm) |

| HMAC and HKDF | Evidence |
| --- | --- |
| HMAC-SHA-256 and HKDF extract and expand match their reference outputs. | Both compilers passed seven RFC 4231 cases and three RFC 5869 SHA-256 cases on macOS ARM64 in native and fatal UBSan builds. An independent Python oracle also checked the HKDF block boundaries and maximum length. |
| HKDF validates the caller's output and PRK length before writing. | 31-byte PRK and 8,161-byte output rejected with distinct errors. Both destinations retained their sentinels. The valid 8,160-byte output matched the complete independent reference. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-hmac-sha-256-and-hkdf-sha-256) |

| SHA-384 and SHA-512 | Evidence |
| --- | --- |
| Both shared-kernel variants produce the expected digest across message and padding boundaries. | Both compilers passed all 514 NIST short and long byte vectors plus 12 boundary cases, one-shot and streaming, on macOS ARM64 in native and fatal UBSan builds. |
| Incremental contexts are private and consumed by finish. | External layout access and use after finish were refused for each type. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-sha-384-and-sha-512) |
| The byte count carries and rejects overflow before updating. | Both compilers passed the seeded low-limb carry and the unchanged-state rejection at the highest byte count under fatal UBSan. |

| HMAC-SHA-384 and HKDF-SHA-384 | Evidence |
| --- | --- |
| HMAC, Extract, and Expand return the expected bytes. | Both compilers passed seven RFC 4231 cases and the pinned Wycheproof HKDF suite on macOS ARM64 in native and fatal UBSan builds. Python HMAC independently checked intermediate keys and the 255-block output. |
| HKDF rejects invalid output and PRK lengths before writing. | All three 12,241-byte Wycheproof outputs returned `OutputTooLong` and preserved every sentinel byte. A 47-byte PRK returned `InvalidPrkLength` and left the destination unchanged. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-hmac-sha-384-and-hkdf-sha-384) |

| SHA-3 | Evidence |
| --- | --- |
| All four fixed-output variants match the byte-oriented reference outputs. | Both compilers matched 860 NIST short and long messages, 24 additional boundary cases, and 400 NIST Monte Carlo checkpoints on macOS ARM64 at `-O0` and under fatal UBSan at `-O2`. One-shot and streaming APIs were checked against the full digest for each short, long, and boundary message. |
| Incremental contexts have private state and are consumed by `finish`. | Both compilers refused external field access and update after `finish` for all four contexts. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-sha-3) |

| SHAKE128 and SHAKE256 | Evidence |
| --- | --- |
| The caller's slice sets the output length (N1, N8, E2). | Both compilers matched 3,182 NIST short, long, and variable-output vectors and all 200 NIST Monte Carlo checkpoints on macOS ARM64 at `-O0` and under fatal UBSan at `-O2`. They matched 128 additional input/output boundary cases, with sentinels on both sides of every output slice. |
| The output requires an exclusive mutable borrow (N5, N8). | Both compilers refused a shared output slice and overlapping input and output. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-shake128-and-shake256) |

| Argon2id | Evidence |
| --- | --- |
| The caller limits workspace with a local region and lends the vector's contiguous contents (N4, N5, N8, G4–G6). | Both compilers derive a tag with 65,536 initialized 1 KiB blocks in a single 64 MiB region. Both refuse push and drop while a mutable view is still used and trap on growth past a full region. |
| The derived bytes and workspace cleanup follow the declared sizes. | Both compilers matched RFC 9106 §5.3 and two OpenSSL reference outputs, including a nonmultiple workspace size with a 73-byte tag. The used blocks were zero on return and the trailing block was unchanged. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-argon2id) |

| System randomness | Evidence |
| --- | --- |
| A fill writes only within the caller's mutable slice (N5, N8, E2). | Both compilers passed a 513-byte subslice witness on macOS ARM64 with intact sentinels and rejected a shared destination. The Rust frontend also exercised Linux ARM64 and x86-64, macOS x86-64, and Windows x86-64 under Wine. |
| The empty slice completes without requesting bytes. Short reads advance the offset, interrupted reads retry, and failures propagate. | Both compilers passed the deterministic backend checks on macOS ARM64 in native and fatal UBSan builds. The checks exercise a partial fill followed by an OS error, and reject zero and excessive returned counts. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#system-randomness) |

| P-256 | Evidence |
| --- | --- |
| ECDHE exports a 32-byte shared x-coordinate into caller-provided storage. Public key import checks point encoding, field bounds, and curve membership. | Both compilers matched RFC 5903 §8.1 in both directions on macOS ARM64 at `-O0` and under fatal UBSan at `-O2`. They also passed generated-key agreement and rejected eight invalid SEC1 encodings. |
| ECDSA signs deterministically, checks canonical DER, and distinguishes malformed signatures from mismatches. | Both compilers matched the two RFC 6979 Appendix A.2.5 SHA-256 vectors byte for byte and rejected eleven malformed or out-of-range signatures. The 71-byte signature left the final output byte unchanged. |
| Private key and point layouts are inaccessible to callers. | Both compilers rejected direct construction and default pool construction of each of the three key types. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-p-256) |

| TLS 1.3 key derivation | Evidence |
| --- | --- |
| The SHA-256 transcript includes the encoded handshake headers and can be snapshotted between fragments. | Both compilers matched the RFC 8448 §3 transcript checkpoints on macOS ARM64 at `-O0` and under fatal UBSan at `-O2`. The replay split ClientHello inside its header and Certificate inside its body. |
| The schedule derives the expected client and server secrets, keys, IVs, and Finished values. | Both compilers matched the published RFC secrets byte for byte and accepted both Finished values. They rejected a first- or last-byte modification and a truncated Finished. |
| Expand-Label honors the caller's output slice and checks length fields before writing (N5, N8, E2). | Both compilers matched an independent Python HKDF oracle for zero, 256, and 8160 output bytes with maximal label and context. Invalid inputs returned their specific errors with the full sentinel buffer intact. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-tls-13-key-derivation) |

| TLS 1.3 record layer | Evidence |
| --- | --- |
| The record header is authenticated and each direction advances its own nonce counter. The payload is written into caller-owned storage (N5, N8, E2). | Both compilers matched all nine selected RFC 8448 §3 wire records byte for byte in native and fatal UBSan builds on macOS ARM64. Both refused external access to the nonce counter. The 16 KiB plaintext boundary, padding, empty application records, oversized records, and rejected tags were exercised. |
| TCP reads and writes complete the record across partial transfers. An authenticated closure is distinct from TCP EOF. | Both compilers passed loopback tests with fragmented input and forced short reads and writes. They rejected TCP EOF before closure, in the header, and in the encrypted body. Both closure alerts matched the RFC and a second TLS receive returned `Closed`. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-tls-13-record-layer) |

| Native TLS 1.3 handshake | Evidence |
| --- | --- |
| Both roles negotiate the P-256 profile and install directional application keys after Finished. | Rust frontend and self-hosted `crustc` completed both roles against OpenSSL 3.6.3 on macOS ARM64 at `-O0` and under fatal UBSan at `-O2`. Exchanged records carried PING and PONG, with authenticated closure. |
| The handshake rejects incorrect transitions and failed peer authentication. | Both compilers rejected an initial out-of-sequence Finished, an altered certificate pin, and a different verification key with the exact certificate retained. External access to session record state was refused. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-tls-13-handshake) |

| Native X.509 validation | Evidence |
| --- | --- |
| The presented P-256 path binds the leaf to a caller-configured anchor and enforces certificate constraints. | Both compilers passed the certificate fixtures for signatures, ordering, validity, Basic Constraints, path length, Key Usage, and EKU. A different root with the same distinguished name, a missing intermediate, an altered signature, and unsupported critical extensions were rejected. |
| The TLS client checks its reference DNS name against DNS SAN entries. | Both compilers exercised case folding, one-label wildcard matching, and rejection of Common Name fallback. OpenSSL loopback tests exercised the leaf/intermediate chain and SNI, plus rejection of a wrong hostname, untrusted anchor, and expired leaf. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-x509-path-and-dns-verification) |

| TLS and certificate module boundaries | Evidence |
| --- | --- |
| The TLS wire format and DER path validation use distinct public certificate types. | Both compilers decoded a TLS Certificate with a request context and entry extension, checked its ranges, and rejected truncation. Both parsed a DER certificate, checked its issuer and DNS identity, rejected a substituted backing DER, and verified an OpenSSL-generated signature using the extracted X.509 public key. |
| The renamed AES contexts and moved opaque types preserve their compilation and runtime behavior. | Both compilers matched 150 NIST AES-GCM vectors in portable and automatically selected modes and rejected external access to the AES, TLS Certificate, X.509 Certificate, and X.509 PublicKey layouts. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#tls-module-and-certificate-types) |

| Caller-owned encoding and PEM | Evidence |
| --- | --- |
| Hex and Base64 write only the reported prefix of the caller's output and leave it unchanged on error. | Both compilers passed empty and partial groups, all 256 byte values, uppercase Hex, invalid characters, noncanonical padding, and buffer sentinels in native and fatal UBSan builds. |
| P-256 and X.509 accept the supported PEM labels and validate the decoded DER. | Both compilers imported OpenSSL PKCS#8, SEC1, SPKI and certificate files in native and fatal UBSan builds. The cases checked key equality, signature verification, DNS identity, and rejection of wrong curves, incorrect labels, encrypted keys, mismatched embedded public keys, trailing data and expired certificates. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#caller-owned-encoding-and-pem) |

| Standard library documentation | Evidence |
| --- | --- |
| Header and declaration comments generate the current public API reference. | The generator checked 67 source files and 802 documented declarations and reproduced the checked-in Markdown. The source bytes matched the previous revision after removing the added comments and their header separator. Package, encoding and PEM regressions passed with both compilers. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#standard-library-documentation) |

| MD5, PBKDF2 and key serialization | Evidence |
| --- | --- |
| MD5 handles arbitrary byte chunks, and PBKDF2 applies the caller's salt, iteration and output parameters. | Both compilers matched the MD5 RFC vectors and padding boundaries, and matched PBKDF2-HMAC-SHA-256 reference outputs through the block index carry. Zero iterations and empty output were refused without writing, and external MD5 state construction was rejected. |
| DER and PEM serialization write the expected prefix or return an error with the output intact. | Both compilers matched OpenSSL's PKCS#8, SEC1, SPKI, and X.509 outputs in native and fatal UBSan builds on macOS ARM64. Tests exercised short buffers, altered backing DER, invalid PEM labels and standalone P-256 round trips. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#md5-pbkdf2-and-key-serialization) |

| RSA and password-protected PKCS#8 | Evidence |
| --- | --- |
| RSA key conversion preserves canonical PKCS#1 contents across standard and traditional containers. | Both compilers matched OpenSSL DER and PEM bytes for 2048- and 4096-bit RSA keys and refused a wrong label, trailing bytes, the wrong key kind, and an undersized output. |
| The supported PKCS#8 profile interoperates in both directions and checks input before consuming the requested work. | Both compilers recovered RSA and P-256 keys produced by OpenSSL. OpenSSL recovered the original keys from the generated DER and PEM containers. The cases rejected an unsupported PRF, an excessive iteration count, a wrong password, a changed IV with valid padding, and insufficient output. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#rsa-and-password-protected-pkcs8) |

| Linux and Windows crypto validation | Evidence |
| --- | --- |
| Reference crypto vectors, caller-buffer boundaries, key formats and native TLS interoperability (N4, N5, N6, N8, E2). | Both compilers passed 17 suites on Linux x86-64 and with Windows x86-64 executables under Wine. Both TLS roles exchanged application data with OpenSSL and exercised authenticated closure, fragmentation, and rejection of invalid certificates and DNS names. Linux used fatal UBSan and Windows used UBSan instrumentation in trap mode where the suites request it. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#linux-and-windows-crypto-stack) |
| Pass a Windows `File` by mutable reference and read into a caller-owned buffer (N4, N5, N6). | With `crustc` under Wine, SHA-384/512, SHA-3, and SHAKE passed using `std::io::File` at `-O0` and `-O2` with UBSan traps. A separate file lifecycle witness passed with UBSan traps. The verifier rejected a `drop(file)` followed by use of its mutable borrow. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#windows-file-borrows-in-crustc) |
| Remaining target coverage. | Native Windows and full Linux and Windows ARM64 runs are open. The Windows ARM64 File witness linked with the Rust frontend. |

| Iterator pipeline | Evidence |
| --- | --- |
| Moving a stage moves its source loan, and the chain cannot outlive the source (N3, N4, N5). | Both compilers rejected use of a moved predecessor, reading the source before the last pipeline use, and moving the pipeline out of the source's scope. Both ran successfully when the source was used after the last `next()` or after `collect()`. |
| Collection respects the destination's element type, borrow and capacity (N4, N5, N6). | Both compilers rejected shared destinations, wrong element types and a live slice of the destination. The generated programs appended past existing contents and hit the normal region limit when exhausted under fatal UBSan at `-O0` and `-O2`. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#iter-map-and-collect) |

| Generic pipeline items and scoped raw addresses | Evidence |
| --- | --- |
| `addr()` requires `@unchecked`; a Crust value cannot carry the raw address out of its block. | Both compilers accepted the local address witness with a numeric result and rejected five misplaced or escaping uses. The Rust frontend passed the assembly refusal cases and emitted C for Linux and Windows on x86-64 and ARM64 with the migrated standard library. File and SHA-256 executed on macOS ARM64. |
| Move and clean mapped items through the same rules as ordinary values (N3, N6, N7). | Both compilers executed the scalar, nominal and flat fixed-array witnesses under fatal UBSan at `-O0` and `-O2`. Two mapped records with destructors, one dropped explicitly and one at scope exit, each cleaned exactly once through `Option`. |
| Preserve the lifetime of yielded references across mapping (N3, N4, N5, N8). | Both compilers executed shared and exclusive scalar references and a loan of a record field through a mapped `Option`. Moving the envelope preserves the loan. Both rejected advancing before the earlier loan's last use, returning a local borrow and using a moved envelope. |
| Preserve the source pool across mapping, collection and cleanup (N3, N4, N7, N8). | Both compilers moved two `A<i64>` from their source pool into a vector, read the second item and recovered both slots after dropping the vector. Both rejected dropping the pool while either an `Option` or the vector held an item. |
| Preserve the worker's reservation across mapping and `join()` (N4, N5, N7, N8). | Both compilers joined a mapped handle carrying a shared or mutable loan from the source. They rejected abandonment, advancing before the wait, and reading while the worker held a mutable loan. Autonomous handles were collected and drained. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#pipeline-payloads-with-dependencies) |
| Rebuild `crustc` with the dependent pipeline changes. | `crustc` compiled its own package, and the resulting compiler passed the same 32 successful programs, 15 refusals, and regional capacity failure on macOS ARM64. |
| Preserve a slice's storage and reborrow across a mapped result (N4, N5, N6, N8). | Both compilers executed shared slices, a mapped subslice, and an exclusive slice moved through `Option`. Both refused a second advance with a live slice and a known out-of-bounds slice of an array field. Both generated a runtime bound check for the same projection with a dynamic upper bound. |
| Infer pipeline results and preserve a forwarded worker contract (N1, N3, N4, N8). | Both compilers executed inferred reference, allocation and handle mappers. Both refused abandonment of the handle returned through two forwarding functions. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#pipeline-slices-and-forwarded-contracts) |
| Rebuild the pipeline compiler after extending slices and calls. | The second-generation compiler passed 37 executions, 18 compile-time refusals and both expected runtime failures on macOS ARM64. |
| Preserve aggregate shape and borrowing across a pipeline slice (N1, N4, N5, N6, N8). | Both compilers ran record subslicing, replacement through a mutable record slice, and indexing a slice of fixed-array rows under fatal UBSan. Both rejected a live previous slice at `next()` and an incompatible row length. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#aggregate-slices-in-pipelines) |
| Collect shared references to an external target (N4, N5, N8). | Both compilers collected two shared references through a stored field and read the second entry after destroying the iterator source. Both refused destruction of the external target before that read. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#shared-references-collected-from-outside-the-source) |
| Transfer a named pooled allocation through a pipeline (N3, N4, N7, N8). | Both compilers collected, removed and destroyed pooled records and reused the slots. Both rejected closing the pool while the destination still held the allocation. Fatal UBSan caught reentrant cleanup in the Rust C runtime before the fix. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#named-pooled-allocations-and-nested-optional-pipeline-items) |
| Track nested optional dependencies (N4, N5, N8). | Both compilers preserved a tracked reference and worker handle through nested `Option` values. Both rejected advancing with a live nested borrow and abandoning a dependent worker. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#named-pooled-allocations-and-nested-optional-pipeline-items) |
| Keep a mapper's internal state, capture dependencies and cleanup through moves (N3–N5, N7, N8). | Both compilers observed one primitive copy per mapper construction, persistent and independent state for consecutive mappers, and one destructor call for a moved record. Both refused reuse of a moved binding and reading a mutable capture before the last mapper call. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#mapper-captures-and-asynchronous-handles-in-pipelines) |
| Transfer asynchronous worker effects through a projected vector extraction and mapping (N4, N5, N7, N8). | Both compilers preserved the two distinct worker reservations until their respective awaits. Injected launch failure released the corresponding reservation with the target unchanged. Both refused early read, abandonment and a returned handle whose task borrowed a factory local. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#mapper-captures-and-asynchronous-handles-in-pipelines) |
| Paired pipeline validation after self-hosting. | On macOS ARM64, both compilers agreed on 54 valid programs, 31 static refusals, two expected runtime errors and two simulated blocking launch failures. Emitted C ran at `-O0` and `-O2` with fatal UBSan. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#paired-validation-of-the-six-pipeline-changes) |

| Corbo migration | Evidence |
| --- | --- |
| Package loading and self-hosting with `.crb`. | Both compilers require `src/main.crb` and omit legacy `.crust` package sources. Installed `corboc` found `std`, resolved path and pinned Git dependencies, rebuilt itself, and its successor ran an external two-module package on macOS ARM64. |
| Self-hosting from `compiler/corboc`. | The Rust frontend built the relocated package on macOS ARM64. The resulting `corboc` rebuilt itself and its successor built an external two-module package that imported `std::encoding::hex`. The executable output matched Rust. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#self-hosted-compiler-relocation) |
| Editor detection and highlighting. | Vim and Neovim recognized new and existing `.crb` files and passed syntax checks, including a jump into a long assembly block. The VSIX installed in an isolated VS Code profile and the TextMate grammar passed tokenization checks. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#corbo-naming-and-editor-support) |
| Embedded C and assembly highlighting in VS Code. | TextMate passed 35 scope checks and the embedded C language ID check. The checks included nested C braces, ARM64 and x86-64 examples, and return to Corbo after each block. The 0.1.1 VSIX installed in an isolated profile. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#embedded-c-and-assembly-highlighting) |

| Historical Python prototype | Evidence |
| --- | --- |
| Preserve module loading, the CLI and corpus generation after relocation. | Both layouts discovered the same 3,826 tests and produced identical representation records apart from source line numbers. The 15 CLI, 48 cleanup and 44 async vector insertion tests passed in both layouts. |
| Preserve isolated mutation execution. | The Select runtime baseline passed and all seven mutations were detected in both layouts. Legacy failures and retired mutation anchors remain. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#python-prototype-relocation) |

| Buffered blocking I/O | Evidence |
| --- | --- |
| Keep the stream and caller-provided buffer exclusively borrowed while an adapter uses them (N4, N5, N8). | The Rust frontend passed file and TCP programs that reused the stream and buffer after scope exit. It refused reuse of either while the reader was live, moving a stored mutable slice, overlapping its reborrows and dropping its holder during a live reborrow. |
| Preserve byte counts, read-ahead and write errors. | On macOS ARM64, file and TCP witnesses ran at `-O0` and `-O2` with fatal UBSan. They covered partial acceptance, empty slices, EOF, explicit flush, read-ahead, dropped pending bytes and a retry after a file write error. The Rust frontend also checked the file witness for Linux x86-64, macOS x86-64 and Windows x86-64 and ARM64. |
| Verify support in the self-hosted compiler. | Existing File code built and ran with the updated standard library. `corboc` returned status 9 for the buffered package and for a constructor returning a record with a borrowed slice. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#caller-buffered-blocking-io) |

| Returned borrowed slices and buffered async I/O | Evidence |
| --- | --- |
| Rebind a returned record’s borrowed slice to the caller, including through inline `.await` (N4, N5, N8). | Both compilers exercised two calls to the same constructor with independent arrays and checked last-use release under fatal UBSan at `-O0` and `-O2`. They refused mutation during a live loan and return of a local slice. The `corboc` case covers a single slice parameter and additional scalar fields. |
| Rebind multiple borrowed slice fields independently (N4, N5, N6, N8). | Both compilers preserved two distinct mutable slice targets after a record move, including with named arguments and fields initialized in reverse order. On macOS ARM64, the witnesses ran at `-O0` and `-O2` with fatal UBSan. Both compilers refused conflicting writes for each field, two mutable arguments targeting the same array, and escape through the second field. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#constructors-with-multiple-borrowed-slices) |
| Read, write and flush a caller-buffered async stream. | The Rust frontend ran File and TCP witnesses at `-O0` and `-O2` with fatal UBSan on macOS ARM64. File checks also refused closing the reader or altering either buffer with a read pending. |
| Validate buffered packages with `corboc`. | Historical result, superseded by the struct-contract cycle below: the synchronous packages returned status 9. Both async packages reached the existing unsupported `runtime::wait_socket` call through their TCP dependency and fail with rule 8. Unbuffered File continued to match Rust in both modes. [Cycle report](cycles/CORE_COMPOSITION_CYCLE.md#borrowed-slice-returns-and-buffered-async-io) |


| Struct contracts and generic STD adapters | Evidence |
| --- | --- |
| Infer and statically enforce structural contracts on structs (SC1–SC3, N1). | `corboc` ran the 12 accepted and 11 refused generic regressions. Required methods, receiver modes, async modifiers, exact/extended sets, explicit arguments and result alternatives were covered. Generated C ran at `-O0` and `-O2` with fatal UBSan. |
| Preserve dependencies through the concrete STD Iter (N3–N8). | The native-only suite passed 54 successful programs overall, 31 static refusals, two expected runtime failures and two simulated launch failures, including references, slices, resources, pools and handles. The real Iter declaration and next method remain in the linked package. |
| Preserve both borrowed inputs of generic buffered streams (N4, N5, N8; SC4). | Sync/async File, TCP and custom streams ran under fatal UBSan at both optimization levels on macOS ARM64. Five sync and eight async File conflicts were refused; pending reads reserved both buffers and their stream. Error payloads retained their concrete types. |
| Preserve reborrow parents and reject escaping tuple referents (N4–N6). | Returned borrowed records in a tuple compiled; a tuple concealing a local referent was refused. Existing separate slice-result and multi-slice-field regressions passed. Borrowed-tuple calls remain outside the executed support. |
| Connect the trusted STD readiness hook to scheduler parking. | The async TCP program read from and wrote to an independent local peer. A user-defined function named ready could not invoke the private hook. This evidence is macOS ARM64; other platform reactor paths and concurrent registrations were not validated here. |
| Self-rebuild and execute the resulting compiler. | The updated corboc generated and compiled its own package. The resulting compiler, itself instrumented with fatal UBSan, passed the same contract, Iter, File/TCP/custom-buffer and slice suites. Its normal build compiled the retained external two-module fixture with automatic STD lookup; output was `5`, `6`, `1`, `7`. |
| Keep generated STD documentation current. | The source-comment checker passed for 75 files and 904 declarations, including constrained types. |

See the [cycle report](cycles/CORE_COMPOSITION_CYCLE.md#struct-contracts-and-generic-std-adapters)
for commands, implementation limits, the Rust freeze boundary and the final
self-reconstruction result.


### STD-owned iterator algorithms

| Property | Executed evidence and limits |
| --- | --- |
| STD Map/Filter/Reduce and collection preserve moves and cleanup (N3, N4, N5, N7, N8). | Nine package programs at O0/O2 with fatal UBSan on macOS ARM64, macOS x86-64, Linux x86-64 in Docker and Windows x86-64 under Wine. Five distinct refusals check the host corboc's expected rule identifier. Windows ARM64 is explicitly deferred. |
| Pipeline dependency and capture regressions remain enforced. | Historical suite completed on macOS ARM64: 54 successful programs, 31 refusals, two expected runtime errors, two injected failed launches. No independent audit performed here. |
| Final compiler can reconstruct itself. | The self-generated compiler was compiled with fatal UBSan, completed the STD, historical pipeline and structural-contract suites, and regenerated identical C for its own package (SHA-256 in the cycle report). Its normal build command produced the retained iterator example with automatic STD discovery. |

[Detailed report](cycles/CORE_COMPOSITION_CYCLE.md#std-owned-iterator-adapters).


| STD collect API correction | Executed evidence and limits |
| --- | --- |
| Collection is a consuming STD instance method, with no package-level collect export. | Corrected bootstrap-built corboc completed ten accepted programs at O0/O2 with fatal UBSan on macOS ARM64, six rule refusals and one missing-export refusal. Final self-reconstruction and platform repetitions remain unexecuted; earlier-cycle evidence is separate. [Correction report](cycles/CORE_COMPOSITION_CYCLE.md#correction-collect-belongs-to-the-std-objects). |

| Root STD collection exports (API) | Executed evidence and limits |
| --- | --- |
| Root imports, aliases and qualified native collection types retain existing behavior. | Four package programs executed on macOS ARM64 at O2 with fatal UBSan: grouped Vector/HashMap/String imports, aliases with allocation transfer and pool-slot reuse, qualified types/constructors, and another package module importing the same exports. Four refusals covered duplicate imports, alias/declaration collision, unknown export and user redeclaration of a reserved native type. Native storage algorithms were unchanged; full compiler and cross-platform suites were not rerun for this API routing change. [Report](cycles/CORE_COMPOSITION_CYCLE.md#root-std-collection-exports). |

| Native runtime source organization | Executed evidence and limits |
| --- | --- |
| Separate runtime implementations from compiler analysis and lowering. | Extracted all seven former emitter payloads into readable `runtime/` fragments and compared generated payload bytes to the originals; all matched, including both conditional reclamation-lock branches. Resource freshness and whitespace checks passed. Per the requested scope, no compiler rebuild or behavioral suite was run for this separation. [Report](cycles/CORE_COMPOSITION_CYCLE.md#visible-native-runtime-source-separation). |

| Native compression (STD/API) | Executed evidence and limits |
| --- | --- |
| Gzip bounded compression/decompression and format interoperability. | 24 native encodings, 11 decoding fixtures and seven malformed/capacity failures passed with corboc-generated executables on macOS ARM64, macOS x86-64, Linux x86-64 and Windows x86-64 under Wine, at O2 with fatal UBSan (fatal traps on Windows). The final canonical length-symbol adjustment was checked by repeating encoder cases. No general compiler suite was rerun. |
| Zstd bounded compression/decompression and format interoperability. | 30 native encodings, 22 decoding fixtures and eight error cases passed on macOS ARM64, macOS x86-64, Linux x86-64 and Windows x86-64 under Wine, at O2 with fatal UBSan (fatal traps on Windows). Fixtures include reference-validated native frames and manually constructed frames, not exclusively reference-produced data. Dictionary loading and streaming are outside the initial API; Windows ARM64 remains explicitly deferred. |

[Compression cycle report](cycles/CORE_COMPOSITION_CYCLE.md#native-gzip-and-zstd).


| Compression API extensions | Executed evidence and limits |
| --- | --- |
| Caller-buffered streaming Gzip/Zstd | Fragmented input/output, backpressure, concatenation, dictionary history, EOF/reset, frame budgets, checksums and terminal state errors passed on macOS ARM64, macOS x86-64 through Rosetta, Linux x86-64 in Docker and Windows x86-64 under Wine, with fatal UBSan (traps on Windows). Whole-frame decode storage is required. |
| Zstd dictionaries | Raw and reference-trained dictionaries passed in both interoperability directions on all four executable targets above. Exact errors for missing, mismatched and malformed dictionaries were executed. No training API or independent adversarial audit is claimed. |
| Entropy encoder candidates | Reference decoding and native round trips passed on all four executable targets above; Gzip 1297→1000 and Zstd 4110→874 bytes on the same weighted fixture. One/four-stream Zstd Huffman paths are covered. General FSE sequence/weight encoding remains an optimization extension. [Report](cycles/CORE_COMPOSITION_CYCLE.md#compression-api-extensions). |


| Conditional annotations, foreign C and compiler compositions | Executed evidence and limits |
| --- | --- |
| Paired source selection and C crossings (grammar, N1, N6, unchecked boundary). | Nested selections, excluded imports/declarations/headers, malformed markers, literal header paths, deduplication, raw comments/strings and primitive operands. Twenty host refusals across the full targeted suite checked expected stage exit statuses; a real custom header executed and C assignment to an immutable operand was rejected. Native C effects remain trusted inside `@unchecked`. |
| Tuple joins, scalar pop, constructor and slice summaries (N1, N4–N6, N8). | Mixed/nested primitive tuple alternatives and scalar moves, pooled-vector pop and loan refusal, transient versus retained constructor inputs, borrowed-enum parameter matches, slice parameter moves and borrowed-result regressions completed. Constructor summaries retain direct reference-field inputs rather than every evaluated argument. |
| Propagation and cleanup (S5b, N4–N8). | Result/Option, unit/nominal payloads, scalar and record references, exact error conversion, `.await?`, scope cleanup and prior owned argument cleanup executed. The existing envelope payload representations delimit this evidence; arbitrary generic compositions are not claimed. |
| Platform and reconstruction evidence. | 21 focused programs executed at O2 with fatal UBSan on macOS ARM64, macOS x86-64 through Rosetta, Linux x86-64 in Docker and Windows x86-64 under Wine (fatal traps). Structural contracts, STD iterators and returned slices passed host regressions. Self-generated compiler C was identical between generations and normal package self-build completed. Other-platform compiler binaries, native Windows and Windows ARM64 were not executed. No independent audit was performed. |

[Core-extension cycle report](cycles/CORE_EXTENSIONS_CYCLE.md).


| Generic identities, result graphs and reactor integration | Executed evidence and limits |
| --- | --- |
| N1: distinct nested concrete nominal identities and structural contracts. | Nested records, constructors, inferred results, deeper instances and distinct nested enum layouts: targeted programs passed at O0/O2 on all four executable targets. Incompatible specialization refused; host structural-contract regressions completed. |
| N4/N5/N6: caller result graphs, moves and deferred captures. | Direct scalar/slice/nominal references, borrow-bearing records, tuple relays, independent calls, tuple moves/destructuring and async captures passed. Early target drop/write and local escape refused. TCP split tasks preserve connection roots until completion. No arbitrary conditional tuple-summary coverage is claimed. |
| N4/N8 and runtime wakeup/cleanup: simultaneous network waits. | TCP/UDP O0/O2 and a production queue witness passed on macOS ARM64, macOS x86-64/Rosetta, Linux x86-64/Docker and Windows x86-64/Wine. Unix: three readers plus a blocked writer on one descriptor. Windows: three reads plus one write with independent OVERLAPPED requests. Deterministic stale-token/park/error transitions passed with UBSan. |
| Reconstruction and bounds. | Byte-identical self-generated compiler C and normal package self-build completed. Arena storage remains bounded. Native Windows and Windows ARM64 were not executed; the optional host ASan witness stalled and is inconclusive. No independent audit or mutation campaign was performed here. |

[Follow-up cycle report, reproduction and remaining limits](cycles/GENERIC_TUPLE_REACTOR_CYCLE.md).

## General callable values in corboc

| Rules | Executed evidence | Status and limits |
| --- | --- | --- |
| N1/N8: callable signatures and contracts | Direct/immediate calls, `fn`, `&fn`, `&mut fn`, owned mutable parameters and forwarding; wrong signature refused. | P — native macOS ARM64, O1 with fatal UBSan |
| N2/N3/N6/N7: captures, moves and cleanup | Capture copy, explicit move, persistent capture state, destructor marker `9, 90, 9`; missing move and consumed-binding reuse refused. | P — six focused compiler programs |
| N4/N5: reference dependencies | Shared/exclusive captures and record reborrows; target escape, premature mutation and shared mutation refused. | P — seven refusals overall; normal loan/constructor metadata reused |
| Documentation and composition | Updated README closure package, former rejected fixture and callback/STD pipeline composition executed. | P — eight distinct executables overall; no broad corpus or other-platform rerun |

[Cycle report and reproduction](cycles/GENERAL_CALLABLES_CYCLE.md). No independent safety audit is claimed.

## Borrowed UTF-8 splitting (STD API and compiler integration)

| Rules / mechanism | Executed evidence | Scope and limits |
| --- | --- | --- |
| TX1/TX4: UTF-8 views | Literal/owned text, Unicode separators, empty scalar splitting, actual byte contents and named views execute. | P — macOS ARM64, O1 with fatal UBSan |
| N4/N5: backing-storage lifetime and access | Premature text/separator destruction and text mutation refused; pieces survive iterator advancement/destruction; separator is independent of returned pieces. | P — four refusals, existing dependency graphs reused |
| N1/N6: result types and descriptor transfers | `Option<&str>`, text-bearing constructors and `Iter::next` forwarding execute; the original String remains usable. | P — twelve successful focused programs |
| Documentation / related regressions | README text package, seven related compiler cases and generated reference inventories pass. | No general safety proof or independent audit claimed |

[Cycle report and commands](cycles/TEXT_SPLIT_CYCLE.md).

## Package-root build defaults (CLI / manifest)

| Mechanism | Executed evidence | Limits |
| --- | --- | --- |
| Defaults, configuration and overrides | Package name, optional [bin].name, package-relative build outputs and explicit -o paths execute. | macOS ARM64 native build driver |
| Dependency and failure behavior | Module/path/STD imports, section order, malformed manifests, directory conflicts and preservation of the prior binary pass. | 18 focused compiler checks; no language-rule change |
| Documentation | README example/source synchronization and generated-reference inventories pass. | Other native build drivers remain unimplemented |

[Cycle report](cycles/PACKAGE_BUILD_DEFAULTS_CYCLE.md).


## Initial corbo-lang snapshot (repository organization)

The initial snapshot copies all 5,083 tracked files from din-lang at
`f905f1afd8c462f633e0ae09d5f058ad9de6c321`; files were byte-compared before
repository-link updates. Language and runtime implementations remain unchanged.
Historical evidence is retained with its original scope and limitations.
See the [migration record](cycles/REPOSITORY_MIGRATION_CYCLE.md) for boundaries
and handoff validation. This is not a new language-rule or safety validation.

## Pool construction and recoverable allocation

| Mechanism / rules | Executed evidence | Scope and limits |
| --- | --- | --- |
| A1/A1a/A1b: explicit Pool construction and recoverable exhaustion | Default/contextual/value initialization, alias imports, scalar/enum/vector slots and slot reuse. | P — 11 focused O1/UBSan programs overall |
| N4/N5/N6: dependencies, moves and cleanup | Pool/borrowed-target lifetime refusals; moved input refusal; Result/? extraction and exactly-once failed/successful cleanup. | P — nine expected refusals overall |
| Runtime and integration | C-reference claim/full/reuse, byte-identical stage2/stage3 compiler output, generated references and explicit-override runtime freshness. | macOS ARM64; published lock unchanged; complex owned-Result signatures remain limited |

[Cycle report](cycles/POOL_CONSTRUCTION_TRY_CYCLE.md) records the baseline iterator
failure and the absence of other-platform execution or an independent audit.

## TX23 — bounded inline UTF-8 strings (specification only)

| Mechanism | Recorded contract | Evidence / status |
| --- | --- | --- |
| `String<N>` | Compile-time byte maximum, fixed inline payload plus length; UTF-8 invariant; no silent truncation or growing fallback. | Implemented; scoped executable evidence below. |
| Existing `String` | Growing representation retained; no new implicit conversions or Copy classification. | No change to existing implementation or prior validation scope. |

See the historical [specification record](cycles/BOUNDED_STRINGS_SPEC_CYCLE.md) and current integration evidence below.


## Bounded strings, binary encoding and time — executed integration

| Mechanism / rules | Executed evidence | Limits |
| --- | --- | --- |
| TX23 fixed inline UTF-8 | Capacity, literal/qualified identity, UTF-8 boundaries, TooLong unchanged, zero capacity, moves and pool borrows | Native padding is not a portable disk layout |
| N4 / N5 / N6 dependencies and moves | Rejected byte/text/pooled view escape, conflicting mutation, moved reuse and private construction; Result text source retained | Scoped probes, not a general proof |
| Explicit binary endianness | LE/BE integer/float reads and writes, extrema, short buffers and bool errors | 64-bit supported targets; no exhaustive bit campaign |
| Time API | Monotonic blocking/async deadline probes on macOS/Linux ARM64+x86-64 and Windows x86-64 | Wine Windows execution; Windows ARM64 compile-only; worker-per-wait |
| Core reconstruction | Byte-identical stage2/stage3 with updated STD; constant and generic regressions pass | Published STD pin remains unchanged until publication |

Nine focused host UBSan executions, ten expected refusals and two related UBSan
regressions completed. Three API and three bounded-layout probes per non-host
target completed as detailed in the report. No independent audit claimed.

[Cycle evidence](cycles/BINARY_TIME_BOUNDED_CYCLE.md).

README follow-up: the four new bounded_text/binary/time/async_time packages
pass individually under O1/fatal UBSan. Their English README source blocks
match the tracked packages; the French README carries the same code blocks.
This documentation check does not extend the platform evidence above.

## Async-default API organization

No new normative rule. Existing resource/borrow checks are exercised through the
new default async and explicit sync imports. Buffered File borrow refusals,
TCP split lifetime refusal and TLS privacy/refusal regressions are retained.
Targeted executions cover macOS ARM64/x86-64, Linux x86-64 (timers also ARM64),
Windows x86-64 under Wine; Windows ARM64 is compile-only. Runtime primitives
are unchanged. [Cycle report](cycles/ASYNC_DEFAULT_API_CYCLE.md).

File example follow-up: sync/async inner-block cleanup before path deletion
passes in two focused macOS ARM64 O1/fatal-UBSan executions. No new core rule.

## Example readability review

No new rule or checker behavior. Fourteen changed example programs pass at O1
with fatal UBSan on macOS ARM64; all 38 EN/FR source blocks are synchronized.
The bare map insert statement refusal is recorded and the example uses an
explicit `_previous` receiver. Spacing-only and unchanged examples were not
re-executed. [Cycle evidence](cycles/EXAMPLE_CLEANUP_CYCLE.md).

## File persistence APIs required by Subdb

API-only addition, with no change to normative rules. Sync/async File cursor
preservation, shrink/zero-fill extension, zero length, oversized length and
read-only failure execute on macOS ARM64/x86-64, Linux x86-64 and Windows x86-64
under Wine. Windows ARM64 is compile-only. No power-loss or directory-entry
durability proof is claimed. [Evidence](cycles/FILE_DURABILITY_SUBDB_CYCLE.md).

## Object lock contracts (MT11)

Corboc derives lock contracts from struct annotations and public instance methods,
preserves them through specialization/imports, and rejects checked same-object
re-entry through helper calls and aliases. Six accepted executions with fatal
UBSan, ten rejections and three retained-lock regressions are recorded in the
compiler repository (`docs/OBJECT_LOCK_CYCLE.md`). The actual-lock three-thread
fixture executes on macOS ARM64/x86-64, Linux x86-64 and Windows x86-64 under Wine.
Windows ARM64 compiles only. No automatic locking code or general safety proof.

## Thread transfer eligibility (TR1)

Five accepted executions under O1/fatal UBSan cover ordinary moves, local closure
calls, default transfer eligibility, fresh worker-local resources and cleanup
before async suspension. Fourteen static refusals cover direct/structural moves,
closures, generic wrappers, arrays, selected fields, nested async state/results
and malformed annotation placement. The existing object-lock runner also passes
(six executions, ten refusals). Evidence is retained in the compiler repository
under `validation/thread-transfer-results.json` and `docs/THREAD_TRANSFER_CYCLE.md`.
This changes target-independent analysis; platform runtime backends are unchanged
and were not replayed. Windows ARM64 execution remains deferred.

## Runtime metrics API

[Evidence and limits](RUNTIME_METRICS.md). Eight Corbo observations plus
C/Corbo ABI concurrent-counter witnesses pass with fatal UBSan. API executes on
macOS ARM64/x86-64, Linux x86-64 and Windows x86-64; Windows ARM64 compile-only.
