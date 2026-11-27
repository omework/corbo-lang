# Rejected programs for later rule-check work

The grammar and N1–N8 are fixed. These are implementation-review cases, not new
rules and not requests to reinterpret the specification. A program remains
rejected whenever compliance cannot be proven. A checker diagnostic is evidence
of its behavior, not independent proof that the program violates a rule.

This is a bounded collection of cases encountered in the current verification
work. It is not an exhaustive false-rejection search. No compiler acceptance
behavior was changed to make these fixtures pass.

## Suspected valid rejections

All six sources parse and resolve into PostAST. Their current rejection was
reproduced with the Rust PostAST verifier. The acceptance arguments below are
review hypotheses; complete N1–N8 proofs remain to be established.

| ID | Complete source | Observed refusal | Why acceptance appears justified | General mechanism to review |
| --- | --- | --- | --- | --- |
| C01 | [Mutable enum reborrow](../../rust_frontend/tests/fixtures/rule_check_review/01_mutable_enum_reborrow.crb) | N5: active incompatible borrow, at the payload read | The method has one mutable receiver. The pattern borrows its payload, the parent is not accessed while that child is used, and the method returns an integer. Parent suspension and child reborrowing should account for the accesses. | Preserve the parent/child reference chain through borrowed pattern extraction. |
| C02 | [Join through a helper](../../rust_frontend/tests/fixtures/rule_check_review/02_join_through_helper.crb) | N4: branch may outlive its target, at the caller's exit | The helper unconditionally calls `join()` and returns only after completion. The borrowed integer remains alive for the entire call. Launch failure also returns through that wait. | Instantiate completion effects at the caller under N8; do not require the completion event to be written in the caller's body. |
| C03 | [Replaced reference target](../../rust_frontend/tests/fixtures/rule_check_review/03_replaced_reference_target.crb) | N5 at `drop(first)`, then N4 at the read of `view.target` | Assignment replaces the first reference with a reference to `second`. No later read uses the old reference. The read after `drop(first)` concerns the still-live second target. | Track reaching contents of a place, including replacement of old dependencies, rather than retaining constructor dependencies indefinitely. |
| C04 | [Deferred replacement after join](../../rust_frontend/tests/fixtures/rule_check_review/08_deferred_write_after_join.crb) | N5 at the drop and N4 at the subsequent read | The single worker replaces the reference and is joined before the caller accesses the object again. The resulting reference targets `second`, which remains alive. | Apply inferred write effects at completion, then use the updated place contents and loan endpoints. |
| C05 | [Trusted interior borrow](../../rust_frontend/tests/fixtures/rule_check_review/10_trusted_interior_borrow.crb) | N3: cannot write through a shared reference | The frozen specification explicitly permits creating a mutable borrow through a shared reference inside `@unchecked`; only mutation-permission checking is bypassed. The target remains alive and the caller uses the one returned mutable reference. | Consume the resolved unchecked boundary in mutation-permission analysis, without special treatment of Mutex or other named types. |
| C06 | [Initialized counter across loops](../../rust_frontend/tests/fixtures/rule_check_review/11_initialized_counter_loops.crb) | N6, explicitly unproved: availability at the second loop condition | The `u64` counter is initialized before either loop and explicitly reset before the second. All assignments and reads are by-value primitive operations; no path moves or destroys it. This isolates the STD entropy-loop report without collection APIs. | Establish loop-carried initialization and short-circuit reaching definitions using hierarchical moments. |

These fixtures must not become filename-specific compiler conditions. Address
missing representations or general analyses, and retain the programs as
regressions only after their expected outcomes have been established from the
existing rules.

## Controls that are not currently rejected

The collector currently observes `Established` for:

- [Allocation through a pool helper](../../rust_frontend/tests/fixtures/rule_check_review/04_pool_allocation_through_helper.crb).
- [Borrowed array iteration](../../rust_frontend/tests/fixtures/rule_check_review/05_borrowed_array_iteration.crb).
- [Closure capturing a shared reference](../../rust_frontend/tests/fixtures/rule_check_review/06_shared_reference_closure.crb).
- [Tuple return carrying two references](../../rust_frontend/tests/fixtures/rule_check_review/07_borrowed_tuple_return.crb).

They are excluded from the false-rejection list. `Established` is the current
checker's operational verdict; the missing complete obligation inventory/proof
links mean it is not an independent full-compliance certificate.

## Destruction review, with no presumed acceptance

[Consuming a custom-destructor payload](../../rust_frontend/tests/fixtures/rule_check_review/09_consuming_custom_drop_review.crb)
is retained separately. The checker rejects it as an unproved N7 obligation. It
is **not** listed as a program that should be accepted. Apply N1/N2/N7 to determine
whether a compliant destruction sequence is established. Do not introduce an
alternative destructor ordering or a new language policy to accommodate it.
The earlier request to choose new hook timing has been withdrawn.

## Reproduction and limits

```sh
cargo run --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target \
  --example collect_rule_check_candidates \
  > validation/post_ast_rejected_review.json
```

[Observed diagnostics](../../validation/post_ast_rejected_review.json) retain
rule identifiers, source lines, messages and related locations. The collector
resolves each fixture once and passes that PostAST to the verifier. It does not
invoke the legacy checker, generate C++, execute programs or assert that a
candidate must be accepted. Exit success means collection completed.

## Concrete STD observations from the restarted audit

The first completed macOS ARM64 selection parses and resolves all 107 sources,
then reports 816 diagnostics. These are checker reports, not 816 independently
proven violations. The package is rejected; 43 files without diagnostics are not
therefore certified compliant.

- **Additional suspected N6 precision gap:**
  [entropy.crb](../../stdlib/src/compression/gzip/entropy.crb), `entropy_lengths`,
  line 13: `i = 0; while i < count && weights[i] != 0 { i = i + 1; }`.
  `i` was initialized as `u64`, then explicitly assigned zero before this loop.
  It is never moved by a non-copy operation. The checker nevertheless reports
  availability unproved. Preserve this as a reaching-definition/loop review,
  not permission to suppress N6. C06 is the smaller, self-contained reproduction
  collected from this observation and also returns an unproved N6 refusal.
- **STD refusals not classified as false rejections:**
  [HTTP Header.name](../../stdlib/src/net/http/http.crb), line 63, returns
  `(*self).field_name` by value from a borrowed Header. The field is a shared
  reference; V3 does not implicitly copy references. Its N3 refusal needs to be
  evaluated as a possible source violation, not automatically a checker defect.
- Likewise, [Argon2 segment processing](../../stdlib/src/crypto/argon2id/argon2id.crb),
  line 249, passes the non-implicitly-copyable `segment: &Segment` by value to
  `segment_reference` repeatedly in a loop. The reported move/use refusal is
  consistent with a potential V3/N6 source violation. Explicit reborrowing is
  already expressible in the fixed grammar; no implicit-copy rule should be
  invented to admit this code.
- The N3 refusals in both STD Mutex implementations occur at the trusted mutable
  borrow inside `@unchecked`. C05 isolates that mechanism using an ordinary
  `Cell` type. The relevant normative paragraph is
  [Language Rules](../LANGUAGE_RULES.md)
  immediately before TR1. It explicitly preserves target/provenance and lifetime
  checking; this is not a general exemption from N1–N8.

No STD source was changed during this baseline collection.
