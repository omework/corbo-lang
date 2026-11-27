# Rust syntax-only parser and retained AST

Scope: source + existing lexer stream → syntax AST. No name resolution, type
inference, language-rule verification, target evaluation or code generation.

## Implemented handoff

- `rust_frontend/src/ast.rs` defines ParsedUnit, Ast, explicit NodeKind variants,
  written TypeSyntax/PatternSyntax/AnnotationSyntax and source TokenRef values.
- `rust_frontend/src/parser.rs` owns the new handwritten recursive-descent/Pratt
  parser. parse(source, tokens) retains both inputs. It does not invoke the lexer.
- `parse_source` in lib.rs is an optional convenience that composes lexing once
  and parsing once. The default CLI `parse` path prints ParsedUnit directly.
- No declaration-name pre-scan, imported-name list or type-name capitalization
  heuristic is used. Constructors retain unresolved paths or inferred-type syntax.
- Source/byte spans and ordered token ranges accompany nodes. Generic closing
  brackets and nested reference tokens use sub-token spans without rewriting the
  original lexer stream. Strings retain the lexer's decoded payloads.
- Foreign nodes retain the lexical token and parsed include-entry references;
  opaque text and operand spans stay in the lexer payload. Headers are not re-lexed.
- Type/member contracts, visibility, receiver spelling, mutability, closures,
  async move, annotations and target-condition branches remain syntax records.
- Separate assignment target/operator/value fields preserve the two roles. The
  assignment-left grammar review remains open; retaining a target expression is
  not evidence that all such targets are valid writable places. No write proof
  is made by this parser.

The previous mixed parser is preserved in legacy_parser.rs. Existing checker,
package and C-backend callers explicitly use it during staged migration. None is
presented as a new reference semantic/PostAST stage.

## Enum qualification and STD migration

The user chose :: exclusively for enum variants. CORE_GRAMMAR.ebnf and
LANGUAGE_RULES.md record the choice. Unresolved dotted value/member calls still
parse; resolution must reject them if they target enum variants. No such new
semantic resolver is claimed here. Variant patterns and named constructions use
qualified paths rather than a dot separator.

The migration utility `rust_frontend/examples/migrate_std_enum_paths.rs` used
actual enum declarations and imported aliases, refused shadowed candidates, and
changed 672 separators in 50 STD files. It did not edit foreign bodies, comments,
ordinary fields or the external SubDB project. The applied-edit report is
`rust_frontend/target/std-enum-separator-migration.md`.

## Executed validation

Host: macOS ARM64. Reused rust_frontend/target throughout.

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --features parser-oracle \
  --test parser_stage --test parser_lalrpop --test lexer_logos -- --nocapture
```

- Twelve syntax-stage tests pass, exercising retained source/tokens, unresolved
  names, syntax grouping, new declarations, generic closers, nested references,
  initializer shorthand, async/closures, headers, foreign islands and enum spelling.
- SubDB dispatcher.crb: 2,879 bytes, 608 original tokens, 287 AST nodes. No edits.
- Five randomly sampled STD modules (seed 20261126), seven source files: all parse.
  Modules: net::asyn::udp, net, compression::gzip, num, sync::asyn.
- All 106 current STD .crb files parse. The corpus includes 346 source files:
  293 parse successfully, producing 502,686 syntax nodes; 53 have individually
  reviewed syntax outside the current grammar, with no unexpected rejections.
- The 53 reviewed rejections comprise 37 return arrows, four script-level bindings,
  ten old enum/field separators, one old new(pool) Type constructor, and SubDB's
  EventType.Insert match pattern in src/event/event.crb:29. The latter must become
  EventType::Insert under the new syntax; external SubDB source was left unchanged.
- Expected refusals are pinned to source fingerprints, first-error offsets and
  tokens in validation/parser_known_syntax_rejections.json. Source changes or a
  refusal becoming acceptance fail the inventory and require investigation.
- Independent LALRPOP expression oracle: 285 cases, 264 accepted and 21 rejected,
  zero differences. It compares grouping, children, spelling and spans on its
  covered expression subset. It does not use production AST-building helpers.
- The Logos lexical comparison still matches all 346 files / 795,136 tokens after
  STD migration. Its JSON-decoding implementation remains independent.

Fixed-path reports in rust_frontend/target:

- parser-corpus.json
- parser-std-sample-results.json
- parser-lalrpop-expressions.json
- lexer-logos-corpus.json

## Investigations and limits

The initial parser inventory rejected 64 files. Twelve STD failures exposed missing
dot-qualified named enum construction in the previous syntax. That support was
initially added, then removed after the user chose :: exclusively; STD was migrated
instead. The final remaining SubDB dotted-pattern rejection follows that choice.
No parser acceptance expectation was changed merely to match output: each corpus
refusal is tied to the written syntax and the inspected source.

Initially LALRPOP covered expressions only; later declaration-order coverage
and block-conflict analysis are recorded below. It still does not cover the full
declaration, annotation and control-flow grammar. Full grammar-to-oracle translation and conflict analysis remain open. The
parser implementation and corpus acceptance do not establish complete grammar
conformance. In particular the written grammar still has known unfinished areas
from the assignment-expression review; these are not implicitly resolved here.

The first optional-oracle build exposed that its build-script edit had replaced
legacy STD embedding. That step was restored before validation; the optional
LALRPOP generation now coexists with it. Grammar generation reported no unresolved
conflicts for the covered expression subset. No silent conflict policy was added.

No native-program, TLS, platform runtime, rule-checking or self-hosting campaign is
part of this syntax stage. Those are separate stages and contracts.

CLI smoke check: the built `corbo-frontend parse` accepted dispatcher.crb and
wrote the retained source/tokens/AST to the fixed path
`rust_frontend/target/dispatcher.ast.txt`; the input remained unchanged.

## Assignment targets and subsequent declaration audit

The assignment-left review was resolved by user approval of call-based places.
The parser accepts dereferenced call results and indexed call results without
resolving their types; non-place syntactic shapes are rejected. Thirteen parser
regression tests and the entire-STD audit pass after this change.

The oracle is now extended beyond expressions with a minimal declaration/method
annotation-order grammar. Its eleven-case comparison finds four contradictions
with the Rust parser and remains failing pending the user's order decision.
See RUST_PARSER_DECLARATION_ORDER.md. This is not full declaration/oracle parity.

## Annotation order resolved; block-boundary decision pending

The user selected annotations before pub in every declaration category. Grammar
and declaration oracle now agree: eleven cases, zero differences. The entire STD
suite remains passing without source changes. Expression AST oracle parity stays
at 285 cases.

The subsequent reduced block grammar analysis found an actual ambiguity between
bare-block statements and an infix continuation. See RUST_PARSER_BLOCK_OPERATOR.md
for the full witness, generated derivations and pending user choice. No block
policy or full parser-conformance claim is made.
