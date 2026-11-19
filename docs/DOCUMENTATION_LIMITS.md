# Documentation coverage follow-up


## Current status

All ten forms rejected during the original documentation exercise are now
supported in the active corboc compiler. General callable support was completed
first; the nine remaining packages were compiled and executed in the
[coverage follow-up](cycles/DOCUMENTATION_COVERAGE_CYCLE.md).

This is scoped implementation evidence, not a claim that every program in the
grammar is accepted or that the compiler has been independently audited.
The [resolved manifest](../validation/fixtures/documentation_limits/resolved.json)
records the nine packages' expected output. The historical diagnostics below
remain unchanged for traceability. `--check-limits` now expects these resolved
forms to compile; execution and rejection boundaries are covered by
`corboc/validation/check_coverage_gaps.py` in the compiler repository.

## Historical observations

This is a record of compiler coverage observations, **not additional language
rules** and not a verdict that every source below violates the specification.
The compiler snapshot below rejected these complete packages. A diagnostic
alone does not establish whether the cause is an unsupported lowering shape,
an analysis limit or a real rule violation; that work belongs to a focused
compiler follow-up. No normative rule was changed during this documentation pass.

The executable README uses separately validated forms and links this record
rather than claiming that the whole grammar is accepted. Existing tests and
self-hosting establish their exercised paths, not universal feature coverage.

Compiler snapshot: `omework/corboc` commit `4096abe`, macOS ARM64 host.
All cases use `--emit-package-c` and this checkout's STD explicitly. The final
recorded stdout contains the compiler's numeric diagnostic, not generated C.

| Observed form | Process exit | Compiler stdout | Complete package |
| --- | ---: | --- | --- |
| Direct shared-reference return | 9 | `9 / 68 / 9 / 45` | [source](../validation/fixtures/documentation_limits/reference_return/src/main.crb) |
| A non-generic candidate under a function structural contract | 9 | `9 / 0` | [source](../validation/fixtures/documentation_limits/scalar_contract/src/main.crb) |
| Custom branch wrapper around spawn | 8 | `1 / 35` | [source](../validation/fixtures/documentation_limits/branch_wrapper/src/main.crb) |
| An addr-derived pointer used by a C operand | 8 | `4 / 31` | [source](../validation/fixtures/documentation_limits/address_operand/src/main.crb) |
| Narrowing numeric try_from | 8 | `8 / 30` | [source](../validation/fixtures/documentation_limits/numeric_try_from/src/main.crb) |
| byte_len on an explicitly typed borrowed text view | 9 | `9 / 10 / 9 / 0` | [source](../validation/fixtures/documentation_limits/borrowed_text_len/src/main.crb) |
| content_eq on array-backed borrowed byte slices | 9 | `9 / 74 / 9 / 0` | [source](../validation/fixtures/documentation_limits/byte_content_eq/src/main.crb) |
| Lock annotations on a mutable receiver | 8 | `8 / 108` | [source](../validation/fixtures/documentation_limits/exclusive_receiver/src/main.crb) |
| A custom sink with a primitive error type | 9 | `9 / 251 / 9 / 174` | [source](../validation/fixtures/documentation_limits/buffered_custom_sink/src/main.crb) |

The source/diagnostic record is [observed.json](../validation/fixtures/documentation_limits/observed.json).
Replay it with:

```sh
python3 validation/check_documentation.py --corboc ../corboc/build/install/bin/corboc --check-limits
```

The replay distinguishes resolved entries from their historical diagnostics.
Preserving an old rejection is not a language requirement.

## Resolved: general callable values

The [original callable package](../validation/fixtures/documentation_limits/callable/src/main.crb)
now compiles and executes with stdout `42, 2`. General direct/immediate calls and
`fn`, `&fn` and `&mut fn` arguments are implemented in corboc. The updated README
closure package executes `42, 10, 20, 2, 1, 2`. Both ran on macOS ARM64 at O1
under fatal UBSan. The callable entry was removed from the active rejection list.

The original callable cycle did not replay the other nine forms. They were
subsequently resolved in the [coverage follow-up](cycles/DOCUMENTATION_COVERAGE_CYCLE.md).

## Working forms shown in the README

- Direct/immediate anonymous function calls, explicit callable passing and STD iterator adapters.
- Structural contracts on generic structs and their methods.
- Parameter borrowing without a returned loan.
- Direct `runtime::spawn`, nested `.await` and native thread execution.
- Typed C operands and a native assembly block without raw-pointer operands.
- Guaranteed-exact widening with `as`.
- Owned String append/byte length and a literal's explicit byte view.
- File-backed BufWriter using an explicitly borrowed scratch buffer.

The [README examples](../examples/features/README.md) are complete programs with
checked outputs. They are not semantic substitutes for every rejected form.
The [cycle report](cycles/DOCUMENTATION_CYCLE.md) separates these observations
from successful executions and records the limits of the validation.
