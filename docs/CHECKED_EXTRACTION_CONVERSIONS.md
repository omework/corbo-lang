# Checked extraction and numeric conversions

[Français](CHECKED_EXTRACTION_CONVERSIONS-fr.md)

This accepted decision supersedes the earlier restriction that `as` must succeed
for every possible value of its source type. It does not introduce traits,
implicit error conversions, allocation, or a new ownership model.

## Postfix `!`

`expression!` evaluates its operand exactly once. On `Result<T, E>`, it extracts
`T` from `Ok`; on `Option<T>`, it extracts `T` from `Some`. `Err` and `None` stop
the whole program with a diagnostic naming the failed wrapper variant and source
location. Error payloads are not automatically formatted: there is no formatting
contract implied by this operator.

Extraction uses ordinary move/copy rules. A moved wrapper cannot be reused; a
copyable wrapper retains ordinary implicit-copy behavior. Borrowed payloads keep
their target dependencies. Allocation/aggregate payloads keep their source and
cleanup dependencies and are destroyed once after successful extraction.
`Result<(), E>!` checks success and produces unit.

`!` is a postfix operator at the same precedence as calls, indexing, `.await` and
`?`; postfix operators apply left to right. Prefix `!condition` remains boolean
negation. `!=` remains inequality. `future.await!` unwraps the completed result;
`future!` is rejected because a Future is not a Result or Option.

`?` keeps its existing early-return behavior. `!` does not require an enclosing
Result/Option return type or an error-conversion method.

## Numeric `as`

`value as T` evaluates its numeric operand once. It succeeds only when that
actual value is exactly representable in `T`; otherwise it stops the program
with the conversion types and source location. Supported numeric primitives are
the existing integer types, `usize`, `f32` and `f64`. Boolean/reference conversion
and arbitrary nominal conversion methods are not introduced.

The check is the same one used by numeric `T::try_from(value)`. In particular,
narrowing integers are range-checked; signed-to-unsigned checks reject negative
values; floating-to-integer checks require a finite integral value in range;
integer-to-float and float narrowing reject precision loss. Existing numeric
`try_from` checks reject nonfinite floating conversions. There is no truncation,
rounding-as-success, saturation, or wrapping conversion.

`try_from` continues returning a recoverable Result. For these numeric
conversions, `value as T` is the aborting counterpart of
`T::try_from(value)!`. Conversions proven exact for all source values may omit
redundant runtime checks without changing behavior.

## Fatal failures

Both operators report the failure and abort the process. They do not unwind
scopes, propagate an error, or guarantee running destructors on the failing
path. Successful paths retain normal scope cleanup. Original source paths and
coordinates are retained across compiler rewrites; a generated-source anchor is
identified explicitly when an exact location is unavailable.
