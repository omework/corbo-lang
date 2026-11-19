# README: explicit growth budgets and reading order

Date: 2026-11-18. Scope: documentation and a small documentation-runner guard.
No normative rule, API or compiler behavior changed.

## Changes

The Rust example and its new Corbo counterpart both collect 1,000 i64 values and
print their count. The Corbo program declares one vector slot and a local
`#(stack_region: max_size=64K, count=1)` scope. The explanation distinguishes:

- The pool's fixed number of simultaneous vector objects.
- The 64 KiB region size and one-region reservation.
- The vector's maximum element storage, separate from descriptor/runtime storage.
- Region-limit failure and cleanup before storage reuse.
- Explicit annotation versus the existing inferred/default sizing policy.

The annotations remain optional. This edit does not introduce mandatory
per-vector capacity syntax or a total-process memory cap.

The README now follows motivation/comparison, quick start, grouped examples,
STD overview, source architecture/build and validation references. The example
chapters group basics, memory, collections, generic code/packages, concurrency,
STD use and native interop. Source-build instructions are separated from the
first-program path and return the reader to the language checkout after building
corboc, so subsequent relative example paths remain valid.

The manifest and feature index follow the same sequence. The original 32
executable example blocks remain byte-for-byte unchanged. The new budget package
makes 33 synchronized complete programs.

## Executed evidence

Host: native macOS ARM64. Corbo compiler: installed self-hosted corboc from
compiler commit `4096abe`, using its existing Corbo runtime pin.

- The new budget package compiled and executed at O1 with fatal UBSan, printing
  `1000` with status zero and no stderr. The runner compared all 33 README source
  blocks and auxiliary package/module files to their source files.
- The Rust comparison compiled with the installed rustc and printed `1000`.
- Changing only the requested count to 8,192 succeeded and printed `8192`.
- Changing it to 8,193 compiled but execution returned status 1, no stdout and
  `corbo: limite de la datastack à régions` on stderr, without a UBSan diagnostic.
  This checks the particular region-limit explanation, not a general safety claim.
- The 32 old example bodies were compared to the previous committed README and
  retained exactly. Their previous executed results remain in the documentation
  cycle report; they were not rerun for a heading/order-only change.
- README section anchors and local links resolve.
- An unknown `--only` name now produces an argument error/status 2. During editing,
  a missing selection otherwise allowed a zero-case run; that was not counted as
  successful validation of the new example.

Commands for the maintained example:

```sh
python3 validation/check_documentation.py --corboc ../corboc/build/install/bin/corboc --keep build/readme-flow --only budget
python3 scripts/stdlib_docs.py --check
```

Generated C, stdout/stderr and the example report are retained in
`build/readme-flow/`. `comparison-report.json` records the Rust result and the
two Corbo boundary executions. Temporary boundary packages change only the
`count` initializer; they do not modify the maintained example.

This focused documentation validation does not repeat the compiler suite,
self-reconstruction, other platforms or an independent safety audit.
