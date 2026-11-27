# Independent Logos lexer comparison

Scope: lexical comparison only. No parsing, name resolution, type inference,
rule verification or generated-program execution.

## Implementations and independence

The production lexer is `rust_frontend/src/lexer.rs`. The comparison oracle is
`rust_frontend/tests/support/logos_oracle.rs`, generated from separate Logos rules.
It uses an additional generated foreign-text lexer and serde_json string decoding.
It does not import production token types, scanner routines, string decoding
helpers or diagnostics. Only the differential adapter in
`rust_frontend/tests/lexer_logos.rs` reads both representations.

Logos and serde_json are dev-dependencies, locked in Cargo.lock. They are not
compiler runtime dependencies. Headers and foreign delimiter nesting require
custom oracle state; a generated scanner does not make those definitions correct
by construction. Both implementations can still share a misunderstanding of the
specification. Handwritten expected tokens and UTF-8 payloads check the oracle too.

## Comparison contract

Accepted inputs compare every token category, half-open byte span, decoded string
payload, foreign header/body span, operand span and recursively tokenized header.
Exact spelling follows from equal spans over identical source input.

Rejected fixtures compare lexical error category and require the production byte
offset to lie in the failing lexeme independently located by the oracle. This is
not exact diagnostic-offset parity: the existing production unit tests separately
check specific expected byte offsets. Semantic errors are outside this comparison.

Every corpus-file mismatch is persisted before test failure, with its path,
source length, FNV-1a input fingerprint and first differing token/error. Neither
implementation is automatically authoritative. Investigate differences against
the specification; do not alter expectations merely to obtain agreement. Escalate
unsettled language decisions to the user.

## Executed evidence

Host: macOS ARM64.

```sh
CORBO_LEXER_CASE=/Users/jabarkarim/sources/subdb/src/dispatcher.crb \
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --test lexer_logos -- --nocapture
```

- SubDB dispatcher.crb: 2,879 source bytes; 608 tokens including EOF; exact
  accepted-token comparison passes. The source file is not modified.
- Handwritten oracle expectations and focused accepted/rejected fixtures pass.
- Corpus: 346 files, 3,596,044 source bytes, 795,136 tokens including each EOF.
  All 346 are lexically accepted by both implementations; zero differences.
- Corpus roots: language STD, runtime and examples; sibling corboc/src and
  subdb/src when present. The report explicitly lists the observed files.

Reused artifacts and inspectable JSON results:

- `rust_frontend/target/lexer-logos-dispatcher.json`: dispatcher token spellings,
  kinds and byte spans.
- `rust_frontend/target/lexer-logos-corpus.json`: per-file corpus outcomes and
  input fingerprints. This file is overwritten at the same path on each run.

Compilation initially required enabling Logos's explicit greedy-rule option for
line-comment patterns. This was an oracle build configuration issue, not a
production-vs-oracle token discrepancy. No production lexer changes were needed
by this comparison. Dependency compilation and tests reuse rust_frontend/target;
no per-run build trees are created.

These results establish agreement on the recorded input, not complete lexical
specification coverage, semantic correctness or architecture completion.
