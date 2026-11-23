# Postfix extraction and checked numeric casts

## Accepted scope

Core/compiler change requested by the user: postfix `!` unwraps Result/Option
or aborts; numeric `as` checks the actual value for exact representability,
including narrowing. Numeric `try_from` remains recoverable. Prefix boolean `!`
and early-return `?` retain their meanings. The Rust frontend stays frozen.

## Implementation

The postfix parser shares the existing extraction AST and value dependency
tracking with `?`, distinguishing its spelling at the operator source span.
Successful extraction transfers ordinary payload ownership and keeps borrow
provenance. The nominal-payload path now retains its existing target and loan
links instead of discarding them. Unit Result success produces unit.

Numeric casts and generated `try_from` helpers share `conversion_code`. Checks
run before unsafe native conversions; a proven exact integer widening keeps its
fast path. Constant folding does not bypass a failed narrowing conversion.
Operands are materialized once. Fatal diagnostics retain original source
locations even in raw C-emission mode; human diagnostics remain disabled there.
Failures abort without unwinding, as documented in the language decision.

## Executed validation

The compiler repository’s `scripts/validate_checked_extraction.py` passes 21 focused observations:
seven successful programs, six deliberately fatal programs, four static refusals
and four existing propagation/conversion regressions. Every executable is built
with `-fsanitize=undefined -fno-sanitize-recover=all`.

Successful programs cover prefix/postfix interaction, primitive and unit
payloads, an owning struct with exactly one destructor, an aggregate borrowing a
value, a mutable-reference Option, an async result, operand evaluation counts
and reuse of copyable wrappers. Fatal programs cover Err/None, integer overflow,
negative-to-unsigned conversion, fractional conversion and precision loss.
Refusals cover wrong operator types, reuse of a moved payload wrapper and a
borrow escaping its target. Fatal messages name the original file/location and
failed variant or numeric types.

The semantic-diagnostic site/history audit and 13 existing observations pass.
Nine diagnostic-category observations pass, including raw-protocol comparison
with the preceding installed compiler. No unrelated full corpus or adversarial
campaign was run. Host: macOS ARM64. No OS-specific runtime/STD source changed;
this report does not claim new Windows/Linux execution. Windows ARM64 execution
remains deferred.

Machine-readable focused evidence is retained in
`corboc/docs/CHECKED_EXTRACTION_RESULTS.json`. Reproduction:

```sh
python3 scripts/validate_checked_extraction.py --compiler /path/to/corboc
```

## Build and installation

A rebuild with the new compiler is required before replacing the existing PATH
binary. The shared-source pin is updated to the accompanying language revision.
Installation status is recorded in the implementation checklist.
