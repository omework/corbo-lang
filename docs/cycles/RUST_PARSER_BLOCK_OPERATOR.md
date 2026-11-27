# Resolved block-statement/operator ambiguity

The user-approved annotation/public order is implemented and validated. This is
the next language decision encountered while expanding grammar analysis to blocks
and control flow. The user chose: finish the inner block and return -2.

## Complete witness

```rust
fn sample() i64 {
    { 10 }
    -2
}
```

Two full-grammar derivations remain possible:

1. The outer block has one result expression: a binary subtraction whose left
   operand is the inner block. It means `({ 10 }) - 2` (8).
2. The outer block has a non-final block-form statement, then a unary-negation
   result expression. Its result is -2.

Both interpretations have i64 results, so even consulting types would not select
one. Parsing must not use types or evaluate the program to resolve this question.
Whitespace and comments are ignored by the existing lexer; the newline supplies
no syntactic boundary. This is not ordinary arithmetic-precedence ambiguity:
it is the boundary between a block-form statement and a continuing expression.

The applicable productions are bloc_delimite (statements plus optional final
expression), instruction/forme_bloc (bare blocks as statements), primaire
(blocks as expression operands), somme and unaire. The already stated rule that
a final bare block is a result is preserved in the reduced witness grammar.

## Independent grammar evidence

`validation/parser_oracle_conflicts/block_operator.lalrpop` is a reduced grammar
retaining these alternatives. It is analysis-only, not a completed control-flow
oracle and not claimed to represent the entire language.

```sh
CORBO_BLOCK_GRAMMAR_AUDIT=1 cargo check --offline \
  --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --features parser-oracle
```

Executed result: expected generation failure (exit 101). LALRPOP explicitly reports
`Local ambiguity detected` after Block with a following minus and prints the two
parse derivations. Complete output is preserved at
`rust_frontend/target/parser-oracle-block-conflicts.log`. This historical reproducer preserves the ambiguity before the user decision;
it is not the current approved grammar.

The analysis-only reproducer lives outside the normal oracle input directory and
requires the explicit environment switch. Ordinary declaration/expression oracle
builds remain usable; their scope does not claim control-flow coverage.

## Approved boundary and implementation

A bare block-form at the start of a statement ends before a following operator.
The witness now contains an inner block statement followed by unary `-2` as the
outer result. A final bare block without a semicolon remains a result expression.

Parentheses and explicit expression contexts preserve expression composition:

```rust
fn parenthesized() i64 { ({ 10 }) - 2 }
fn returned() i64 { return { 10 } - 2; }
fn assigned() i64 { let value = { 10 } - 2; value }
```

`CORE_GRAMMAR.ebnf` separates statement-start expressions from ordinary expressions.
`rust_frontend/src/parser.rs` recognizes the initial block-form before entering
its ordinary operator parser. This uses syntax only, without evaluating a block
or consulting names or types.

The independent `tests/oracle/blocks.lalrpop` models this boundary. Ten accepted
and rejected cases match the Rust AST structure, including parentheses, nested
blocks, semicolons and a following unary minus. The stage regression checks the
full function witness. All 106 STD files still parse with original source and
lexer tokens retained: 145,730 tokens and 91,901 reachable AST nodes.

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --features parser-oracle \
  --test parser_lalrpop --test parser_stage --test parser_stdlib -- --nocapture
```

The older `parser-block-operator-current.ast.txt` and `.json` files record the
pre-decision binary-subtraction observation. Current evidence is
`target/parser-lalrpop-blocks.json` and `target/parser-stdlib.json`.
This completes the boundary decision, not full grammar/oracle coverage.
