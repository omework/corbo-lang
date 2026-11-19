# General callable values

This compiler/core cycle implements the existing closure grammar and capture,
move and borrowing rules. No normative rule or STD/runtime API was added.

The implementation is in the separate `omework/corboc` checkout, primarily
`src/callables/callables.crb`. Its detailed report is
`docs/GENERAL_CALLABLES_CYCLE.md` in that repository. Concrete capture records,
constructors and invocation methods use the ordinary contracts, dependency
summaries, cleanup and post-AST placement machinery. Callable parameters
specialize while preserving value, shared-borrow or mutable-borrow passing.
Local record and scalar argument reborrows retain their target/parent metadata.

Completed on native macOS ARM64:

- Six compiler fixtures executed with expected stdout: direct/immediate calls,
  all parameter modes, forwarding, mutable capture state, explicit reference
  captures, cleanup after a move and composition with STD iterators.
- Seven invalid programs were rejected: wrong signature, missing move, consumed
  callable/capture reuse, shared mutation, early target mutation and target escape.
- The README closure example executed `42, 10, 20, 2, 1, 2`.
- The former rejected callable fixture executed `42, 2` and was removed from the
  active rejection list. The other nine historical observations were not replayed.

All eight distinct executables used O1 and fatal UBSan. The resource cleanup
fixture prints `9, 90, 9`, separating its single destructor marker from values
returned by calls. README/source synchronization also passed.

Language-checkout evidence is in `build/general-callables-docs/`; compiler
fixture evidence is in `build/general-callables/` in the corboc checkout.

```sh
python3 validation/check_documentation.py \
  --corboc ../corboc/build/install/bin/corboc \
  --keep build/general-callables-docs --only closures
```

Run `validation/check_callables.py` in the compiler checkout for its six accepted
and seven rejected fixtures. The installed compiler is the same binary used for
the recorded checks. Its STD/runtime source revision remains pinned by
`corboc/corbo.lock`.

No full corpus, new multi-generation self-reconstruction, ASan, mutation campaign
or independent safety audit ran. Other platforms were not rerun; Windows ARM64
execution remains deferred. These results cover the listed mechanisms and
regressions, not every callable composition or a general memory-safety proof.
