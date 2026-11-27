# Rust reference lexer stage

Scope: core/compiler implementation of source text → tokens only.

## Implemented boundary

- The existing `rust_frontend/src/lexer.rs` remains the single Rust lexer.
- `Token`, `Payload` and `ForeignBlock` preserve original-source byte spans,
  string bytes, foreign text, header tokens and operand-name spans.
- Multi-character operators use longest matching. Tuple projections, ranges and
  decimal floats stay distinct. JSON escapes and surrogate pairs are validated.
- Foreign bodies shield delimiters in comments, quoted literals and C++ raw strings.
- Lexical errors carry source offsets; the isolated-surrogate offset was corrected.
- No symbol table, type environment, target selection, ownership checks or rule
  verification is invoked. Out-of-context foreign blocks and undeclared names
  deliberately remain lexically acceptable.
- The CLI token-category summary gains C++ category 7. Parser support is not added.

## Focused evidence

Command, from the language repository root:

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target lexer::tests
```

Twelve focused lexer tests cover operator matching, tuple fields, floats/ranges,
JSON decoding, error byte positions, foreign headers/nested delimiters/operands,
foreign lexical errors, preservation of original spans, and acceptance independent
of name/type/rule validity. The library and CLI are compiled by this command;
unrelated test cases are filtered out. These are lexical observations, not proof
of the complete grammar or architectural compliance of later stages.

The first run exposed a wrong isolated-surrogate error offset, corrected before
rerunning. Builds reuse the pre-existing `rust_frontend/target` directory. No
release builds, self-hosting builds, target-platform builds or generated programs
are part of this cycle.

## Remaining stage work

- Reconcile and audit the parser against the agreed grammar.
- Make later stages consume token payloads rather than decoding strings again.
- Define and implement the typed PostAST handoff independently of this lexer work.
- Foreign C++/assembly content is not parsed or validated by Corbo's lexer. Target
  assemblers may have additional dialect-specific lexical conventions; they are
  not established by the exercised quoted/comment forms.

## Restored C-source regions

The user clarified that rewriting existing implementation C blocks did not remove
`@c` from the language. The grammar and reference Rust lexer now retain distinct
C, C++ and assembly regions. Two additional tests exercise C headers/payloads,
comments/nesting/interpolation spans, marker distinction and malformed C islands.
The CLI token summary assigns category 8 to C without changing previous IDs.
Unchecked enclosure is still not a lexer check. Parser/backend integration and
C-versus-C++ source compatibility remain later-stage work.
