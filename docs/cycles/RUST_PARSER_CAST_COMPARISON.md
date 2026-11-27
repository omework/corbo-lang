# Resolved cast/generic/comparison boundary

Scope: core grammar and syntax-only parsing. No semantic resolution, checking,
STD edits, or backend changes are involved.

## Historical ambiguity in the overly broad production

```rust
x as T < U >> y
```

Before correction, with the written `conversion = unaire, { "as", type }`, named generic types,
comparison precedence, right shifts and generic closing-bracket splitting, this
has two possible complete readings:

```rust
(x as T) < (U >> y)
(x as T<U>) > y
```

The first retains `>>` as right shift. The second uses its first `>` to close
`T<U>` and its second `>` as comparison. Neither requires a name lookup to
construct its syntax tree. Later semantic restrictions on conversions must not
be used to choose a syntax tree.

The old production parser selected the generic reading, while the expression
oracle covered only non-generic cast targets and selected comparison. Neither
observation established intended language behavior.

The analysis-only reduction `validation/parser_oracle_conflicts/cast_comparison.lalrpop`
records the competing grammar prefixes. LALRPOP reports a shift/reduce conflict
at `<`. This generated conflict demonstrates that the reduced grammar is not
LR(1); the two complete readings above additionally explain the language
ambiguity. A generator conflict alone would not establish that conclusion.

```sh
CORBO_CAST_GRAMMAR_AUDIT=1 cargo check --offline \
  --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --features parser-oracle
```

Executed: expected generation failure, exit 101. Log:
`rust_frontend/target/parser-oracle-cast-conflicts.log`.
The switch is opt-in and the reproducer is outside normal oracle generation.

## Approved restriction and implementation

The user confirmed that `as` has a numeric target, not an arbitrary type.
The grammar now declares:

```ebnf
type_numerique = "i32" | "i64" | "u8" | "u16" | "u32" | "u64"
               | "f32" | "f64" | "usize" ;
conversion = unaire, { "as", type_numerique } ;
```

The same restriction applies to statement-start expressions. Consequently:

```rust
x as u64 < y       // (x as u64) < y
x as u64 < U >> y  // (x as u64) < (U >> y)
x as T<U>         // syntax error: expected a numeric type after as
```

`numeric_cast_type` in `rust_frontend/src/parser.rs` consumes only the numeric
terminal and emits an ordinary TypeSyntax::Path node with its original TokenRef.
It performs no lookup, type inference, conversion evaluation or token rewriting.
Generic types remain supported in other type positions. Aliases, qualified names,
references, arrays and bool are not numeric cast-target productions.

The expression oracle independently distinguishes numeric spellings and restricts
its cast target production. The normal declaration/contract oracle token adapter
remains unchanged. No comparison precedence was altered.

## Executed validation

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --features parser-oracle \
  --test parser_lalrpop --test parser_stage --test parser_stdlib -- --nocapture
```

- Expressions: 307 cases, 280 accepted matches, 27 rejected matches, zero differences.
- Block, declaration and carrier-contract subsets: 10, 11 and 7 cases, zero differences.
- Stage regressions: all 16 pass, including each numeric target and rejected
  nonnumeric target forms.
- Entire STD: all 106 files pass unchanged, with 145,730 original tokens and
  91,901 reachable AST nodes.
- Broader source inventory: 293 accepted and 53 previously reviewed syntax
  rejections across 346 sources, no unexpected changes.

Reports are in the reused `rust_frontend/target/parser-lalrpop-expressions.json`,
`parser-stdlib.json` and `parser-corpus.json` files. No STD source changes were
needed. The analysis-only conflict fixture/log above preserve the old general
cast grammar; they do not describe the corrected language.

This resolves the cast boundary. Full grammar audit and whole-language oracle
coverage remain incomplete; semantic conversion checks and generated execution
were not part of this syntax-stage validation.
