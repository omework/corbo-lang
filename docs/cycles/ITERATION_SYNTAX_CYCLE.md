# Universal reference methods and for loops

Scope: grammar/core. The active corboc compiler normalizes the syntax described
in [Iteration syntax](../ITERATION_SYNTAX.md) into existing borrowing, indexing,
next/Option, scope cleanup and placement operations. STD/runtime code is unchanged.

Executed on macOS ARM64: five executable programs and five expected refusals,
plus sixteen focused compiler diagnostic regressions. Covered behavior includes
indexed mutation/shared reads, aggregates, nested loops, empty sources, one-time
source evaluation, mutable binders, break/continue, destructor cleanup, reference
levels, lifetime and mutation-permission refusals, moved iterators, intrinsic
arity and generated-name hygiene. Final compiler source was rebuilt using the new
compiler generation and the ten functional observations passed on that binary.

The compiler repository contains scripts/validate_iteration.py, recorded results
and docs/ITERATION_CYCLE.md. No broad corpus or adversarial campaign ran. Fresh
Linux/Windows execution was not performed; Windows ARM64 execution stays deferred.
