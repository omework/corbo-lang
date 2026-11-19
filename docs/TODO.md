# TODO

## Recorded compiler-composition limitations — resolved witnesses

The self-hosted core-extension cycle resolved the recorded scalar pooled-vector
`pop()`, nested/mixed primitive tuple conditionals, transient constructor inputs,
parameter-slice moves and borrowed-enum parameter matching. Simple local slice
moves and plain record-valued method results were already working and are now
retained as regressions. These are implementation corrections, not new rules.

The recorded `?` lexer/lowering gap is connected for the existing Result/Option
representations, including unit/nominal values, exact error conversion, partial
argument cleanup and `.await?`. See the [cycle report](cycles/CORE_EXTENSIONS_CYCLE.md)
for the exact executed envelopes and limitations; this is not a claim that every
possible generic envelope composition is implemented.

## Windows File validation

- [ ] Run the original and instrumented File witnesses on native Windows x86-64 at `-O0` and `-O2`. Both passed under Wine 11.21.
- [ ] Run the same witnesses on native Windows ARM64. Both optimization levels link. The local x86-64 Wine runtime reports `Bad format` for the ARM64 executable.

For both architectures, check the bounded read, empty buffer, EOF, malformed
path, missing file, and exactly 129 successful `CloseHandle` calls in the
instrumented witness, including 128 after moving the file.

See the [validation script](../validation/check_rust_file.py) and
[cycle report](cycles/CORE_COMPOSITION_CYCLE.md#windows-execution-under-wine).

## Bootstrap executable parity

- [x] Lower native worker frames and their captures, then propagate ownership and results through handles and waits.
- [x] Lower map entry storage and transfers, and complete vector removal and destruction of aggregate elements.
- [x] Match the explicit budgets, regional scope restoration and composite operations exercised by this corpus.
- [x] Pass the accepted-corpus replay with `--require-parity` in native and UBSan builds.

See the [executable comparison](../validation/check_crust_codegen.py) and
[cycle report](cycles/CORE_COMPOSITION_CYCLE.md#bootstrap-executable-comparison).

## Windows ARM64 execution status

Windows ARM64 remains unexecuted across the project, including STD iterator
adapters. The owner explicitly deferred providing a Windows ARM64 execution
host for this cycle. Linking an ARM64 PE does not count as execution validation;
x86-64 runs under Wine do not cover ARM64. Keep this limitation visible in
platform reports until real ARM64 execution is available.

## Generic/tuple/reactor follow-up

The three previously recorded integration gaps are implemented. Executed target
coverage and precise limits are in [the cycle report](cycles/GENERIC_TUPLE_REACTOR_CYCLE.md).
Windows ARM64 remains deferred, and Wine does not replace native Windows testing.
A separate existing verifier gap remains for consuming scalar payloads in a
borrowed enum match, including field-projected subjects. This is a compiler
coverage limit, not a new language rule. Arbitrary conditional borrow-bearing
tuple summary forms remain outside the executed follow-up coverage.
