# Configurable constants

Status: implemented in corboc, with focused host validation. This document specifies
a core grammar and specialization mechanism, not an HTTP-specific compiler API.

## CC1 — Explicit configuration defaults

`#(configurable)` immediately precedes a module-level or associated constant declaration,
before `pub` when present. The initializer supplies its default value:

```rust
#(configurable)
pub const HEADER_LINE_MAX_SIZE: usize = 8192;
```

Only marked constants may be overridden. Ordinary constants retain their
existing meaning. Normal name resolution and visibility apply; external callers
use public package constants. Associated constants use their qualified `Type::NAME` identity; they do not
introduce mutable global state. Both struct and enum definitions support them.

## CC2 — Lexical override block

```rust
#(override:
    std::net::http::HEADER_LINE_MAX_SIZE = 2048,
    std::net::http::HEADER_COUNT_MAX = 64
) {
    // Calls and constant uses here see the effective configuration.
}
```

The directive contains at least one path/value assignment and prefixes a normal
block. Its block can be used wherever the corresponding ordinary block is
allowed. The closing brace ends the override scope; no `endif` is involved.
Qualified paths identify constants through ordinary name resolution.

## CC3 — Constant values and rejection boundaries

Each replacement must be evaluable at compile time and valid for the declared
constant type under the existing numeric and constant-evaluation rules. Runtime
variables and runtime computations cannot supply configuration values.
The grammar admits an expression on the right; admission by the grammar is not
permission to evaluate arbitrary calls at compile time. This feature does not
itself add new constant-expression operations or constant function execution.

Unknown paths, inaccessible declarations, unmarked constants, invalid constant
expressions, incompatible values and duplicate assignments to the same resolved
constant in one directive are compilation errors. Aliases do not create distinct
constant identities. A trailing comma is permitted.

## CC4 — Inheritance and isolation

Omitted constants retain the inherited configuration, or their package defaults
when no override exists. Nested scopes inherit effective values; a nearer
explicit override replaces the inherited value for its block. On leaving the
block, the enclosing configuration applies again. An override never rewrites a
package globally or changes an unrelated caller's configuration.

## CC5 — Calls and derived constants

Calls under an override use implementations specialized for the effective
configuration, including internal helper calls. The compiler must carry the
configuration through those calls, rather than resolve package constants once
using their default declaration values. Derived constants, where supported by
constant evaluation, are evaluated under the effective configuration.

This is compile-time specialization, not a dynamically scoped parameter and not
a hidden runtime Limits object. The implementation may share identical code,
but must preserve the specified effective values.

## CC6 — Values crossing scopes

An object retains the configuration of the specialization that created it when
moved outside the override block. Its storage bounds and subsequent operations
do not switch to the receiving scope's defaults. Any configuration affecting
layout, behavior or analysis summaries must remain associated with that
specialization; representations with different layouts must not be conflated.

The existing N1–N8 obligations still apply. The directive grants no implicit
copy, borrow, promotion or exemption from cleanup. Placement analysis can use
the constant bounds; a bound does not require eagerly occupying its full size.

## CC7 — Static bounds, runtime enforcement

The selected limits are static. Code consuming unknown input must still enforce
them at runtime. A configured maximum does not guarantee that sufficient region
space is available; the API's resource-error behavior remains applicable.

Configuration directives are distinct from the verifier's analysis directives:
they select compile-time program parameters, rather than supply a proof strategy
for an invariant. The compiler mechanism is generic; packages define the
constants and their domain-specific meaning. See the complete
[HTTP example](HTTP.md#complete-scoped-example).

## Implementation scope

corboc specializes declarations before ordinary verification/lowering. Current
replacement expressions are literals or references to existing constants; this does
not add arithmetic constant initializers or compile-time function execution.
Named constants can supply fixed-array lengths and repetition counts.
The bounded implementation permits 256 marked constants and 256 environments per
unit; exceeding compiler workspace is a diagnostic, not dynamic configuration.
See [executed evidence](cycles/HTTP_CONFIGURATION_IMPLEMENTATION_CYCLE.md).
