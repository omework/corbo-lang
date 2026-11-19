# STD/runtime documentation and executable README

Date: 2026-11-18. Classification: documentation and documentation tooling.
No language rule, runtime algorithm or STD API was changed. The compiler and
its locked runtime revision were not modified or rebuilt in this cycle.

## Completed work

- Retained the existing STD function/type comments and documented the remaining
  fields, variants and named variant payloads. Every Corbo source file has a
  module summary and declaration/member comments.
- Documented all 478 active Corbo-runtime functions, including raw field access,
  storage, collection cleanup, task scheduling, callback ABI and OS primitives.
- Added source-level Doxygen comments for C ABI/reference types, their field
  declaration groups and functions, with module summaries. Runtime Python build
  helpers now have purpose-specific docstrings.
- Reworked source extraction to recognize methods, nested generic types, function
  fields, variant payloads, target conditions and contracts, while skipping
  opaque foreign code and required contract signatures.
- Regenerated [STDLIB.md](../STDLIB.md) and [RUNTIME.md](../RUNTIME.md). The check
  covers 89 STD files / 1,374 declarations and members, plus 32 runtime files /
  775 entries. Counts include private helpers, C aliases/prototypes and field
  declaration groups; they are not counts of unique public functions. Runtime
  Python helper docstrings are checked in addition to the entry count.
- Added [documentation conventions](../DOCUMENTING.md) and a
  [compiler-backed collection guide](../COLLECTIONS_API.md), since native
  collection methods have no ordinary method declarations in the STD export file.
- Expanded the README with 32 complete package examples and source/README
  synchronization checks. Added an example index, expected outputs and a
  reproducible validation command.

## Executed validation

Compiler: self-hosted `corboc` from compiler commit `4096abe`, with the Corbo
runtime pin `6c16675e4073dd9778c1ac7c1c73d51ebe1a7199`.
Environment: native macOS ARM64 host, host C compiler, O1 and fatal UBSan.
The current checkout's STD was provided explicitly to the compiler.

| Check | Completed result |
| --- | --- |
| Source coverage and generated-reference freshness | 1,374 STD entries and 775 runtime entries documented; both references current. |
| Documentation inventory unit regressions | Five passed: contracts/native exclusion, nested payload/function field, missing member visibility, target conditions and C callback/function extraction. |
| Complete README programs | 32 compiled and executed successfully; exact exit status, stdout and stderr matched. |
| README/source correspondence | All main example blocks and the auxiliary package/module blocks matched their source files. |
| Coverage observations | Ten rejected complete packages replayed and matched their recorded diagnostic/status. These are not normative rejection tests. |
| Source preservation | Code tokens unchanged in 78 edited C/Corbo source files; Python ASTs unchanged in three runtime helpers after removing docstrings. |
| Runtime generation | Documented Corbo runtime sources compiled successfully; generated runtime resource tokens matched the previously validated implementation. |
| Python syntax and patch whitespace | py_compile and git diff --check completed. |

The examples cover primitives/operators, moves/copies, control flow, tuples,
structs/methods/constants, enum payloads, borrowing, arrays/slices, pools,
placement/destruction, vectors/maps/text, closures inside adapters, generic
contracts, pipelines, region budgets, Result propagation, async/native/blocking
execution, target selection, unchecked C/assembly, files, encoding/hashing,
modules, buffering, loopback UDP and compression.

Commands:

```sh
python3 scripts/stdlib_docs.py > docs/STDLIB.md
python3 scripts/stdlib_docs.py --runtime > docs/RUNTIME.md
python3 scripts/stdlib_docs.py --check
python3 -m unittest discover -s validation -p test_source_docs.py
python3 validation/check_documentation.py --corboc ../corboc/build/install/bin/corboc --keep build/documentation-final --check-limits
python3 runtime/corbo/build.py --compiler ../corboc/build/install/bin/corboc --out build/documentation-runtime
```

Results and generated C are retained in `build/documentation-final/report.json`,
its per-example directories, `limits-report.json` and `source-preservation.json`.
The source-change comparison used language commit `5affd2c` as the baseline.
The runtime token comparison used the retained Corbo-runtime generation from
the preceding runtime parity cycle; this is a code-preservation check, not a
new independent oracle for runtime correctness.

## Observations and corrections

The first draft example set had 20 passing programs and eight rejected forms.
The final examples use separately executed supported forms. Further probes
identified the ten coverage observations recorded in
[DOCUMENTATION_LIMITS.md](../DOCUMENTATION_LIMITS.md), with complete sources and
numeric diagnostics. Examples include standalone callable literals, direct
borrowed returns, some structural-contract and text/numeric operations,
raw-address C operands and custom branch/lock wrappers. A custom primitive-error
buffered sink was rejected; the documented File-backed wrapper executed correctly.
These observations do not establish a new language restriction or prove a checker
defect. They must remain visible rather than being hidden by the runnable subset.

The initial UDP run could not bind in the restricted sandbox. The same generated
program passed with local socket access, and the complete final run used that
access. The expected output was not weakened to accept the failed socket path.

During review, the legacy `take` helper was documented as a slot-bitmap claim,
not a byte allocation, and the C `swap_classic` adapter was documented as returning
the saved context rather than taking the Corbo implementation's out parameter.
These were documentation corrections, not code changes.

## Limits

This is host execution evidence for the exact examples. No platform-wide suite,
compiler self-reconstruction, ASan campaign, mutation campaign or independent
safety/security audit was repeated. Windows ARM64 execution remains deferred;
previous platform results retain their separate scope.

Passing examples do not prove general acceptance, soundness or memory safety.
Source comments and generated API signatures do not supersede the language
specification. Unchecked C/assembly retains its documented caller obligations.
