# Rust parser stage: initial boundary audit

Scope: inspect the existing tokens → syntax implementation before changing it.
This is the initial source audit, not an executed parser conformance campaign.
The inspected implementation is now preserved as legacy_parser.rs; subsequent
reference-parser work is recorded in RUST_PARSER_STAGE.md. No parser
implementation changes or claims of parser completion are made by this report.

## Confirmed architectural inconsistency

`rust_frontend/src/legacy_parser.rs:38` accepts imported declaration names and pre-scans
struct/enum names. `Parser.names` stores them. `is_constructor` at line 1084
consults those names and capitalization when deciding whether braces construct
an object; package-discovery mode also changes that decision.

This is not a syntax-only boundary. The already approved control-flow header
parenthesis rule permits a syntactic distinction without declaration lookup.
Constructor syntax should preserve its path without deciding what it names.

## Confirmed grammar drift

- `declaration` at line 507 reads struct fields as a comma-separated field list;
  it does not parse the current mixed, semicolon-separated fields/constants/methods.
  Enum variants similarly use the old comma-separated list.
- `function` at line 640 only reads a return type after `->`.
- Closure parsing in `primary` at line 1103 also still checks `->`.
- The operator table at line 934 retains comparisons above bitwise operations;
  its special treatment of adjacent > tokens predates the lexer's longest-match
  >=, >> and >>= tokens.
- Foreign statements at line 795 handle assembly and reconstruct operand spans
  from source text, despite the lexer now supplying operand/header/body spans.
  C and C++ token categories are not integrated there.
- The bare type-annotation parser at line 256 still handles the obsolete star
  form; annotation and declaration coverage requires reconciliation with the
  current grammar, not acceptance inferred from existing source code.

These findings explain why the old parser cannot yet be treated as the current
reference. They are parser-stage work, not reasons to weaken semantic rules or
add library APIs.

## Required syntax handoff

The parser receives original source and its lexer token stream. It must preserve:

- Stable syntax-node identities, token ranges and original byte spans.
- Ordered declarations, fields, enum variants, methods, parameters and statements.
- Written type syntax as unresolved paths/arguments/references, not inferred types.
- Parameter/receiver syntax, visibility, mutability, async and move spelling.
- Each expression operator and its explicit operands in grammatical grouping.
- Distinct assignment target and value roles, call arguments, projections,
  construction fields/shorthand, patterns and control-flow bodies.
- Annotation syntax and its attached declaration/member/block. Target conditions
  are syntax here; evaluation and import resolution are not parser operations.
- Foreign-block kind and already-lexed header/body/operand spans. No foreign
  re-lexing or lookup of operand bindings.

It must not populate symbol resolutions, inferred types, ownership/lifetime state,
synchronization proofs, placement plans or generated-code operations. Those are
later-stage results and should not be reconstructed by code generation.

## Sequencing

1. Establish explicit AST node fields and the source/token ownership handoff.
2. Remove name-dependent constructor parsing rather than patching its symptoms.
3. Align declaration, statement, expression, type and annotation productions with
   validated grammar decisions. Report remaining grammatical ambiguities first.
4. Validate parser acceptance/rejection and inspectable AST grouping without
   calling `frontend`, the static-tree builder or verifier.

The lexer remains implemented and independently compared. The parser remains
open. This audit does not reopen normative ownership or borrowing decisions.
