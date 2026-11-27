[Français](README-fr.md)

<a id="frontend-rust-de-crust"></a>

# Corbo Frontend Rust

The reference syntax entry points are:

- `lexer::lex(&source)` → original tokens and decoded lexical payloads.
- `parser::parse(source, tokens)` → `ParsedUnit { source, tokens, ast }`.
- `parser::parse_expression(source, tokens)` → the same retained unit for an expression.
- `parse_source(source)` → convenience composition that lexes once and parses once.

The semantic-stage entry point is `semantic::resolve(parsed_unit)`. It populates
canonical `post_ast` types and returns logical destinations with source, type,
provenance and timeline facts. `semantic::validate_population` checks structural
handoff integrity. Neither entry point invokes the rule checker or backend.

The separate `rule_check::verify(logical_result)` consumes the resolved PostAST
and returns `RuleAnalysisResult`; it does not invoke semantic resolution or a
backend. This new verifier is **under implementation**; existing implicit-copy and
consuming-drop rules are preserved. Read the
[current verifier report](../docs/cycles/RUST_POST_AST_RULE_VERIFICATION.md)
before interpreting a verdict. The legacy `check` command is unchanged.


```sh
cargo run --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target -- resolve < example.crb
```

The semantic stage has a grammar-family coverage inventory and a whole-STD audit. Read the
[coverage and limitations report](../docs/cycles/RUST_SEMANTIC_POPULATION.md)
before using its output. The legacy `check`/`build` path still uses its old pipeline;
it has not been migrated to the new PostAST.

For parsed packages, `semantic::resolve_package_for_target(modules, target)`
selects imports/declarations using explicit target facts before resolution.
Generic source bodies have canonical parametric instances resolved from their
contracts, without enumerating concrete specializations. The permanent STD audit
covers Linux/macOS/Windows on x86-64 and ARM64 through semantic PostAST only:

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --test semantic_stdlib -- --nocapture
```

Per-target reports and `semantic-stdlib-matrix.json` reuse `rust_frontend/target`.
See the [STD semantic report](../docs/cycles/RUST_STDLIB_SEMANTIC_AUDIT.md).

The AST is defined in `src/ast.rs`. It records unresolved names, written type
syntax, annotations, declarations and expression/statement structure with source
spans. It contains no symbol resolutions, inferred types or rule proofs. Token
ranges and sub-token references preserve generic closers without changing the
original lexer stream. Parsed foreign includes point into the existing lexical
payload, so downstream code does not need to parse the header again.

```sh
cargo build --offline --manifest-path rust_frontend/Cargo.toml --target-dir rust_frontend/target
rust_frontend/target/debug/corbo-frontend parse < path/to/source.crb
```

`parse` is the default CLI mode and prints the retained source, tokens and AST for
inspection. It does not load imports, choose target branches, construct the legacy
static tree, verify rules or generate code.

### Parser validation

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --features parser-oracle \
  --test parser_stage --test parser_lalrpop --test lexer_logos -- --nocapture
```

The opt-in `parser-oracle` feature generates an independent LALRPOP expression
parser; normal parser builds do not need LALRPOP. The oracle covers expression,
block-boundary, declaration-order, structural-contract and range-call subsets,
not complete module-level grammar parity. The five-module random STD
sample uses recorded seed 20261126 in `validation/parser_std_sample.json`.
See [the parser report](../docs/cycles/RUST_PARSER_STAGE.md).

### Permanent entire-STD regression

`tests/parser_stdlib.rs` recursively discovers every STD `.crb` file. Every input
must parse and preserve its original source/tokens, with valid reachable AST nodes,
child references and token views. There are no expected-rejection exemptions.

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --features parser-oracle \
  --test parser_stdlib -- --nocapture
```

Per-file results reuse `rust_frontend/target/parser-stdlib.json`.
See [the whole-STD audit](../docs/cycles/RUST_STDLIB_PARSER_AUDIT.md).

### Structural-contract alternatives

The syntax parser accepts one annotation-wide `with` followed by nonempty method
sets separated by `|`. It retains explicit alternative nodes, signature/type
nodes, source spans, braces and separator TokenRefs. Bare `#(type: T)` remains
unconstrained. This does not implement semantic contract matching.

The generated OR cases compare acceptance and normalized contract ASTs against
independent LALRPOP output. See [the implementation report](../docs/cycles/RUST_OR_CONTRACT_CASES.md).

### Grammar-derived coverage

`tests/grammar_coverage.rs` reads `CORE_GRAMMAR.ebnf` and generates complete
programs for reachable productions, alternatives, optional parts and bounded
repetitions. An independent chart recognizer checks derivations and classifies
terminal-deletion mutations before comparison with the Rust parser. Source/token
preservation and AST integrity are audited as well.

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --test grammar_coverage -- --nocapture
```

The JSON inventory and generated source reuse
`rust_frontend/target/parser-grammar-coverage.json`. This is bounded structural
coverage, not full AST or semantic conformance. See
[results and limitations](../docs/cycles/RUST_GRAMMAR_GENERATION.md).

### Typed PostAST architecture proposal

The next-stage data architecture is proposed in
[POST_AST_APPROACH.md](../docs/architecture/POST_AST_APPROACH.md), with the complete
[standalone Rust schema](../docs/architecture/post_ast.rs) and AST/operator mapping
inventories. It is not imported by this compiler and contains no resolution,
verification or code-generation engine. Timelines and both moment types are
explicit, including hierarchical loop/iteration occurrences. The retained order
is logical final destinations, rule checking, then physical memory planning.
[Pass contracts](../docs/architecture/POST_AST_PASS_CONTRACTS.md) describe the data
handoffs; no resolution engine is integrated.

### Legacy pipeline

The previous mixed parser is retained as `legacy_parser`. Existing `frontend`,
`parse_for_target`, `program`, `block`, `signature`, `check`, `emit-c`, `build` and
historical batch operations still use that legacy pipeline. They are not the
reference syntax-only entry points. Their old checker/backend behavior is not
established by the parser-stage results, and they must be migrated separately.

## Reference lexer: source → tokens

Rust is again the reference implementation for the staged compiler work.
The lexical and syntax-only parser stages have been revised. The older
legacy_parser, static-tree construction, verifier and C generator remain legacy stages;
they are not evidence of alignment with the current grammar or of a completed
typed PostAST. Their migration is separate work.

`lexer::lex(&str)` returns tokens with half-open UTF-8 byte spans and an explicit
EOF token. Each token retains its original spelling through `Token::text(source)`.
Strings carry decoded UTF-8 bytes in `Payload::Text`; numeric spelling is retained
without selecting a numeric type or checking a machine range. Identifier-shaped
words, including keywords, have `Kind::Name`; the parser matches keyword terminals
by spelling. There is no declaration lookup in the lexer.

Operators use longest matching, including `>>`, `>=` and `>>=`. The lexer does not
split generic closing brackets based on type context. Decimal floats, ranges and
numeric tuple projections remain distinct. The preceding token's lexical spelling
is used to distinguish a leading-dot float from a tuple-access dot; no binding or
type information is used. Scientific notation has no dedicated literal token.
Historical `->` can still be tokenized; whether syntax accepts it is a parser task.

`@c`, `@c++` and `@asm` preserve opaque foreign bodies, original-source header/body spans,
and the spans of `${name}` placeholders. Foreign header tokens are supplied with
absolute offsets, avoiding header re-lexing by the parser. Strings, raw C++ strings,
line comments and block comments shield braces and placeholders. This is lexical
boundary scanning, not validation of foreign instructions or C++ statements.
Whether a foreign block is enclosed in `@unchecked` is not checked here.

The lexer reports lexical errors with byte offsets. It does not resolve names,
infer types, enforce borrowing, select a compilation target, evaluate annotations,
or verify language rules. String payload consumption by legacy later stages has
not been migrated in this pass; those stages still contain decoding helpers.

Use the existing target directory for builds and focused validation:

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target lexer::tests
```

Cargo fingerprints decide when recompilation is needed. Do not make timestamped
build trees, clean the cache routinely, or build release/cross-target variants for
this source-only stage. See [the lexer cycle report](../docs/cycles/RUST_LEXER_STAGE.md).

### Independent Logos comparison

The test-only oracle is in `tests/support/logos_oracle.rs`; its generated rules
and serde_json decoding do not call the production scanner or its helpers.

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --test lexer_logos -- --nocapture
```

Set `CORBO_LEXER_CASE` to select a real source file for the dispatcher test.
Otherwise it uses the sibling SubDB checkout when present. The corpus test uses
STD/runtime/examples and sibling compiler/SubDB sources when available. Reports
reuse `rust_frontend/target/lexer-logos-{dispatcher,corpus}.json`. Every corpus
mismatch is recorded for investigation; agreement is not proof of correctness.
See [the comparison report](../docs/cycles/RUST_LEXER_LOGOS.md).

## Verification and generation C

`check` check the supported subset.
`emit-c` applies the same verifier before issuing C on
the standard output. The generator receives a `VerifiedProgram`.

```sh
rust_frontend/target/debug/corbo-frontend check < programme.crb
rust_frontend/target/debug/corbo-frontend emit-c < programme.crb > programme.c
cc -std=c11 -pthread programme.c -lm -o programme
```

The current scope covers `bool`, `i32`, `i64`, `u8`, `u16`, `u32`,
`u64`, `f32`, `f64` and their references
in synchronous functions. It includes blocks, branches,
`while`, `loop` with or without result, movement and
The Commission has already taken a number of decisions concerning the application of the Treaty to the Community.
possible source parameters and substitutes them for the call.
C uses Clang or CCG overflow intrinsics to
addition, subtraction and multiplication.
follows the future uses of local references through the branches,
The reference used in the course of a study is the following:
next iteration keeps its reservation.
may use an approximation of their provenances.

For synchronous fixed aggregates, post-AST analysis follows
travel to the destination scope and can share a location
between exclusive arms that feed the same recipient. When a function
built its result, the caller provides typed output locations.
A relay propagates these locations or keeps the address of a result
transmitted from a parameter.

The plan also places the links, parameters and results materialized by the
The scalar results of the study are
blocks, branches and calls can relay the address of the receiver.
temporary calculation remain expressions or temporary C.

The runtime reserves an anonymous virtual beach with `mmap` First
need. An inaccessible page protects the end of each data range. Each reservation advances an aligned cursor after checking for
the capacity. The block exits, returns, `break` and `continue` restaurent
The receiver's anticipated locations are reserved before
this brand and remain accessible after restoration.

Optional Ownership `#(datastack: size=...)` sets the capacity in units
binaires `K`, `M` ou `G`. Without it, the compiler composes the reservations
post-AST, their alignments, scope paths and accessible calls
since `main`. The C evaluates this terminal at start with sizes and
Target ABI alignments. Accessible recursive calls give a
unknown terminal. In this case, the runtime uses the available pages if
the platform exposes them by `sysconf`, or physical pages, divided
by the number of CPUs online.

`python3 validation/check_rust_datastack_capacity.py` compares capacity
maximum selection observed in C controls.

The tables, enums and nested structures can bear references.
The verifier tracks their provenance and last use by position.
A contract links the position of the argument to the position of the result.
A dynamic index keeps the sources of all possible boxes.
Direct borrowings keep the reservation of their storage root.
A re-borrowing of a stored reference may be limited to a field or a field of
box, including through a borrowed aggregate.

A local pool reserves its entire area in the datatack, with a cursor
and a register of separate slots per variant for enums.
`match &allocation` reads the tag and payload of the variant directly
a game borrowed binds the aggregated fields by reference,
with the transfer right of the match recipient. Functions receive pools by loan
and may consume or return `A<T>`. Un transfert d’`A<T>`
keeps the slot and associates its cleaning with the receiver, provided that
Pool and dependencies of value survive.

To reproduce the targeted controls, execute
`python3 validation/check_rust_placement_dependencies.py` after
construction of the frontend. Unsolved recursive contracts retain
All candidate sources.

The `Vector<T>` With fixed elements without dependencies and `String` established
by `pool<T>.new()` place their descriptor in the pool slot and their
The transfer of the allowance shall be retained in a separate region.
the region and its limit. Cleaning restores the area before the slot of the
Pool. Frontend supports `push`, `len` and indexed reading of the
vecteurs ainsi que `push_str` on a UTF-8 literal and `byte_len` for
`String`.

`region_size` and `region_stack_size` above their deduced limits.
The post-AST composes the peak of occupation of the regions with the transfers
exclusive arms contribute by their maximum.
When coexistence remains undetermined, the plan directs acquisitions
The Commission has already taken the view that the Commission's proposal is not sufficient to ensure that the Commission's proposals are properly implemented.
Unbounded growth uses 100 Mio template in the absence
configuration.

`#(stack_region: max_size=..., count=...)` can reserve a dedicated area
The plan calculates a local capacity when
`count` is omitted. If the locations of the annotated area are occupied,
Runtime can open a dedicated region of the same template.
The template of a value triggers the limit diagnosis.

Optional thresholds `reclaim_threshold` and `region_reclaim_threshold`
enable automatic return of free pages. `#(free_pages)` the
also asks below the threshold, after cleaning the block.
virtual remain reserved.

The `HashMap<K,V>` with primitive, borrowed or allocated values place their descriptor via the
same post-AST plan. L-linked index and entries occupy a region.
The live entries keep their address and the table re-uses the
The backend lowers the locations removed. `insert`, `get`, `get_mut` and
`remove`, with a result `Option`. A borrowed result protects the
table until its last use.

The reference and reference vectors `A<T>` maintain the dependencies of
the elements. Cleaning releases the allowances possessed in order
Inverse integration before returning the region of the vector.
The auditor retains the union of dependencies at control junctions.
`pop` and `remove` extract the handles from `Vector<A<T>>`. The
sources of the table and vector remain conservative after
replacement or extraction.

`python3 validation/check_rust_regions.py` and
`python3 validation/check_rust_region_collections.py` exercent ces chemins
synchrones.

`runtime::thread({ ... })` lowers a synchronous worker pthread block.
His handle can cross telescopes and calls. The block captures by
`move nom;` fixed values, including those with slots
In case of failure of launch, the catches owned are
The results of the project can be used to finance loans or grants.
and dimension the worker's datatacks.

The call for a `async fn` creates an inactive Future. `runtime::spawn`
l , entered in the runtime line and returns a `Handle<R>` with
`join()`. `runtime::spawn_blocking` Launches Future on a thread
dedicated in async context and returns a `AsyncHandle<R>` with `.await`.
Ces deux formes produisent `Result<R, runtime::Error>`. Un `.await`
direct consumes an inactive Future and produces directly `R`.
The post-AST plan retains the recovery points, temporary and
The scope marks of blocks, branches and loops.

One `HashMap` can pass a task by value in
The fixed catch and results may be used for borrowing and borrowing purposes.
own slots `A<T>`. The result only retains the
the responsibility to clean up the
slots move from capture to status and then to receiver in case of transfer.
An aggregate placed in a pool or added to a vector transmits slots
The cleaning makes the children slots before the container.
the container.

One `async fn` Call the others `async fn` creating a Future.
She can wait directly with `.await` or throw it on a thread
dedicated with `runtime::spawn_blocking` Then wait for his handle.
Direct call from a `fn` synchronous from a `async fn` is prohibited
in the core.

Compile C programs that run a thread with `-pthread`.
`python3 validation/check_rust_native_regions.py` and
`python3 validation/check_rust_task_regions.py` Replay witnesses.

To compile a multi-file project, pass the package directory to `check` or
`emit-c`. See [packages and modules](../docs/MODULES.md).
