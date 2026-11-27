# Structural-contract OR: Rust syntax implementation

Scope: grammar, Rust syntax AST and parser only. No name resolution, type
inference, semantic contract matching, loop API change or code generation.

## Representation and parsing

`AnnotationSyntax::TypeContract` now retains the parameter, generic argument
syntax, one optional annotation-wide `with`, a list of alternative NodeIds and
the original `|` TokenRefs. An empty list represents the existing unconstrained
`#(type: T)` form. An explicit method contract has at least one branch.

Each `NodeKind::TypeContractAlternative` contains the opening/closing brace
TokenRefs and a nonempty list of Function signature nodes. It has its own source
span and token range. Return types remain unresolved TypeSyntax nodes, including
separate shared and mutable Reference nodes. Child/token visitors traverse the
new nodes, so the same retained-tree audit applies without a second AST model.

`annotation` parses the common mode before the first branch, then calls
`contract_alternative` for each method set separated by `|`. It rejects empty or
dangling branches, `with` after OR, and `||` in place of `|`. Requirements use the
existing signature/type parser; no semantic resolution is repeated.

Implementation: `rust_frontend/src/ast.rs` and `rust_frontend/src/parser.rs`.
The previous single-contract AST field `methods` is replaced by `alternatives`;
all syntax consumers/visitors in this stage have been updated. Legacy compiler
stages remain separate and are not claimed to support semantic OR matching.

## Generated cases and independent AST expectation

`tests/parser_lalrpop.rs::generated_or_contracts_match_the_parser` generates:

- Two one-branch controls, with and without `with`.
- Six OR forms with 2, 3 or 5 branches, alternating `Option<&T>` and
  `Option<&mut T>`, using either annotation-wide with or exact mode.
- Seven malformed forms: leading/trailing OR, empty branch, `||`, repeated with,
  with introduced after OR, and redeclaring the annotated type after OR.

The independent LALRPOP grammar `tests/oracle/contracts.lalrpop` returns its own
contract/method structures. These are compared with a normalized Rust AST:
parameter, common mode, branch/method order, method names, async modifier,
receiver mutability and written reference/generic return types. The comparison
also checks the retained braces, separators and AST integrity. This oracle is a
stated signature/type subset, not a full-language AST oracle.

## Executed validation

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --features parser-oracle \
  --test grammar_coverage --test parser_lalrpop \
  --test parser_stage --test parser_stdlib -- --nocapture
```

- 15 focused cases: eight accepted, seven rejected, zero differences.
  All eight accepted contract ASTs match the independent oracle.
- 161 productions, all reachable; 847 derived cases, zero differences.
- 566 syntax mutations: 564 refused, two still valid; zero differences.
- Existing oracle subsets: 307 expressions, 10 block boundaries, 11 declaration
  order cases, seven carrier-contract cases and six range calls still match.
- All 16 syntax-stage regressions pass.
- Entire STD: all 106 files parse unchanged, preserving 145,730 tokens and
  91,919 reachable AST nodes. The additional nodes are explicit method sets.
- Broader inventory: 293 accepted / 346 sources, same 53 reviewed refusals,
  502,748 syntax nodes; no unexpected acceptance/rejection changes.

The full command passed after parser integration. The six LALRPOP tests were
then rerun after adding independent expected contract ASTs; all passed.

Generated readable cases: `rust_frontend/target/parser-or-contract-cases/`.
`case-03-valid.crb` contains the two shared/mutable iterator alternatives.
Reports: `target/parser-lalrpop-or-contracts.json`,
`target/parser-grammar-coverage.json` and `target/parser-stdlib.json`.
All artifacts reuse `rust_frontend/target`.

## Historical discovery and limits

Before parser integration, six valid OR cases were rejected at the first |;
the general generator separately reported two shorter versions of that same
missing mechanism. Those were implementation gaps, not language-rule violations.
They are now accepted; the malformed cases remain rejected.

Semantic matching/selection is still pending. No first-matching-branch policy,
implicit conversion or merging of shared and mutable return permissions was
introduced. General full-AST oracle coverage and exhaustive nesting/combination
coverage remain outside the evidence above.
