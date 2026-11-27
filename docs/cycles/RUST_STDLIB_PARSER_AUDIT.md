# Entire STD parser regression audit

Scope: every `.crb` file discovered recursively under stdlib/src. The regression
has no allowlist, rejection exceptions, package-loader shortcut or target filter.
Future files are included automatically. A missing/empty STD is an error.

Implementation: rust_frontend/tests/parser_stdlib.rs. Syntax-only AST traversal
is exhaustive over NodeKind, TypeSyntax, PatternSyntax and AnnotationSyntax via
NodeKind::children and NodeKind::token_refs in rust_frontend/src/ast.rs.

The test audits every input independently and records all failures before failing:

- Source can be read as UTF-8 and tokenized.
- The reference Rust parser builds the AST without semantic stages.
- Source and the complete original token stream remain identical.
- All node and token-view spans are valid UTF-8 byte ranges.
- Child IDs and token references exist, and are contained in the owning node.
- The AST has no cycles, shared syntax nodes or disconnected arena nodes.
- The source file remains unchanged during its audit.

## Executed result

Host: macOS ARM64. All 106 STD sources pass: 145,730 original tokens and 91,863
reachable syntax nodes. Zero failures. This pass did not change STD source or
CORE_GRAMMAR.ebnf. The earlier, explicitly requested enum migration remains in
place; the audit does not perform any source normalization or migration.

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --features parser-oracle \
  --test parser_stdlib -- --nocapture
```

The test does not require the oracle feature; it is included in this command to
reuse the feature configuration already used by the parser-validation work.
The per-file report overwrites the fixed shared-artifact path
`rust_frontend/target/parser-stdlib.json`. Cargo's existing target cache is reused.

These are automated per-file parsing and AST-integrity observations. They are not
semantic verification, an external module-AST comparison or proof of full grammar
conformance. Unlike the separate mixed historical corpus, no STD source is
classified as an expected rejection.

## Subsequent assignment decision

The user approved both call-based target forms. The grammar now distinguishes
assignment_left_expression from assignment_right_expression. The parser checks
only the permitted place-like syntax, accepting call-containing dereferences,
fields and indexed elements while rejecting bare calls and arithmetic targets.
Subsequent parser/whole-STD regression passed unchanged: all 106 files, zero
failures, 145,730 tokens and 91,863 AST nodes. No STD source was edited.

The declaration/annotation order decision was subsequently resolved: annotations
precede pub, and its eleven-case generated-oracle comparison passes. The broader
audit now awaits the block-boundary decision in RUST_PARSER_BLOCK_OPERATOR.md.
The entire-STD regression remains passing.
