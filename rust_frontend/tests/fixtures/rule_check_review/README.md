# PostAST rule-check review corpus

These complete programs reproduce suspected false rejections and nearby controls.
They are not new normative rules or acceptance assertions.

See [the review register](../../../../docs/cycles/POST_AST_REJECTED_ACCEPTANCE_CANDIDATES.md)
for the existing rules involved, observed diagnostics, and the rationale for each
candidate. In particular, case 09 has no presumed acceptance.

Run the collector from the repository root:

```sh
cargo run --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target \
  --example collect_rule_check_candidates \
  > validation/post_ast_rejected_review.json
```

No grammar, rule, STD implementation, or checker acceptance policy should be
changed merely to make this corpus pass. Both demonstrated violations and
unproved compliance require rejection.
