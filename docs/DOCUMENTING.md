# Documenting the STD and runtime

Document source behavior where it is implemented. Keep comments in English and
preserve SPDX/third-party notices. Do not change a normative rule to match an
implementation limitation; link the rule and record the limitation separately.

## Source comments

- Start each Corbo source file with its SPDX line and a `//!` module summary.
- Attach `///` comments to types, functions, methods, constants, fields and enum
  variants, including private helpers and named variant payload fields.
- Describe purpose, input units, result meaning and side effects. Where relevant,
  describe source/receiver ownership, retained references, error behavior,
  resource budgets, cleanup order and required synchronization.
- For an unchecked primitive, state the required storage/lifetime/alignment and
  locking contract. An integer containing an address is not a checked reference.
- Use Doxygen-style `/** ... */` comments for C types/functions and an `@file`
  comment for C modules. Use docstrings for runtime build-adapter Python helpers.

A field accessor does not need a long essay, but its comment should say which
state it reads or changes and who must provide valid storage. Avoid comments
that merely expand an identifier into words. Keep implementation limits and
unchecked caller obligations visible.

## Generate the references

```sh
python3 scripts/stdlib_docs.py > docs/STDLIB.md
python3 scripts/stdlib_docs.py --runtime > docs/RUNTIME.md
python3 scripts/stdlib_docs.py --check
python3 -m unittest discover -s validation -p test_source_docs.py
```

The checker inventories all STD and Corbo-runtime declarations, including
private members; it skips required method signatures inside type contracts and
opaque native code. The runtime reference also inventories C types/functions
and checks Python helper docstrings. Generated Markdown must not be edited by
hand. Source links use the current declaration line numbers.

Compiler-backed collection methods do not have ordinary declarations in the
root export file. Maintain [the collection API guide](COLLECTIONS_API.md) alongside
their runtime comments; do not invent empty method bodies for documentation.

## README examples

Each complete README example has a package under `examples/features/` and an
expected stdout entry in its `manifest.json`. `<!-- example: name -->` associates
a README block with its exact `src/main.crb`. Auxiliary files use
`<!-- example-file: relative/path -->`. The Rust comparison in the philosophy
section is explicitly excluded from Corbo compilation.

```sh
python3 validation/check_documentation.py --corboc ../corboc/build/install/bin/corboc
```

The checker compiles this checkout's STD with the selected corboc, compiles the
resulting C at O1 with fatal UBSan, and executes it with exact status/stdout/stderr
checks. Each program has an isolated working directory. Local socket access is
required for the loopback example. A `--sources-only` run omits README matching
and is development feedback, not completed README validation.

`--check-limits` replays the recorded rejected forms in
[DOCUMENTATION_LIMITS.md](DOCUMENTATION_LIMITS.md). These are observations, not
normative rejection tests. When compiler support changes, update the observed
status and prose; do not preserve a rejection just to satisfy the record.

This documentation workflow is not an independent safety/security audit or a
replacement for compiler/platform validation. Record executed results and their
limits in a cycle report and the verification matrix.

## Offline HTML reference

`corboc doc` serves the installed HTML snapshot. Source-defined APIs use the same
inventory as the Markdown reference. Compiler-owned interfaces use
`corboc/docs/BUILTIN_REFERENCE.json`, including types whose STD export body is empty.
The compiler installation automatically invokes its HTML generator. See
[the offline guide](OFFLINE_REFERENCE.md) for generation and navigation.
