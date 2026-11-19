# Compiler moved to its own repository

Date: 2026-11-18. Scope: repository/build organization; no language-rule change.

The active compiler and focused compiler regression suites moved from
`compiler/corboc/` to the root of [omework/corboc](https://github.com/omework/corboc).
The language checkout retains STD/runtime/specification ownership and historical
reference tools. See [the boundary and development commands](../COMPILER_REPOSITORY.md).

The compiler locks shared inputs to `cd7e97b3a0bf9f808fb27559705b11509d4e1a24`.
The source resolver, generator and build script verify that pin and reject
modified inputs. Installed STD discovery retains its existing layout.

Executed on macOS ARM64:

- Three compiler generations emitted byte-identical C; normal package self-build
  succeeded from the new repository.
- A separate two-module package with an import compiled and printed `42`.
- The moved core-extension suite passed 21 programs and 20 refusals; the
  generic/tuple suite passed nine O0/O2 programs, seven refusals and its registry
  witness; the C bridge passed 22 O0/O2 executions and six refusals.
- Six source-lock tests passed, including wrong revision and modified-input
  refusal. An initial temporary-path spelling error in a test fixture was fixed
  and the complete six-test run repeated.
- The language-repository mechanism forwarder passed. Source inventories resolve
  80 compiler source files and 119 external compiler/fixture candidates.
- The moved target-emitter helper built successfully with the pinned STD.
- Runtime-resource freshness, STD documentation freshness, Python syntax and
  whitespace checks completed.

The detailed [compiler report](https://github.com/omework/corboc/blob/main/docs/REPOSITORY_SPLIT.md)
records build commands, source comparison and generated-C hash. Logs were retained
under `/tmp/corboc-extraction/`; binaries/report are under the compiler's `build/`.
This is integration evidence, not a new independent audit or safety proof.

The migration did not rerun the full platform matrix or broaden native compiler
host coverage. Native Windows execution remains a gap; Windows ARM64 remains
deferred. A compatible existing seed is still required. Extraction and validation preceded coordinated publication in the two repositories.
