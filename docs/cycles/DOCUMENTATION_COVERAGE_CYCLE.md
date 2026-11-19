# Documentation coverage follow-up

The active corboc compiler now accepts and executes all nine packages left
from the original documentation exercise. Together with the earlier callable
integration, all ten historical observations are resolved for their recorded
sources. The [historical diagnostics](../DOCUMENTATION_LIMITS.md) are preserved;
[resolved.json](../../validation/fixtures/documentation_limits/resolved.json)
records expected output. No language rule or grammar changed.

The compiler fixes cover explicit returned borrows, structural function
contracts and output inference, branch-wrapper signatures and temporary joins,
C address operands, exact numeric try_from, typed &str length, named byte-slice
comparison, mutable lock receivers/results and usize-bearing buffered sinks.
They reuse call contracts, dependency summaries and ordinary place checking.
Conversions are expanded in one batch, including a five-conversion program
that checks the f64-to-f32 range before casting.

Completed on macOS ARM64:

- 18 focused accepted packages executed at O1 with fatal UBSan, including the
  nine original sources; seven related invalid programs refused as expected.
- Six existing callable/iterator programs executed at O1 with fatal UBSan;
  seven existing ownership/borrowing/signature variants refused.
- The README closure package executed at O1 with fatal UBSan; all 33 README
  source blocks remained synchronized. The nine historical forms were also
  replayed through the language documentation command and all compiled.
- The packed-runtime decoder executed at O2 with fatal UBSan across a 64 KiB
  history wrap, with five independent packing round trips; runtime-only emission
  retained two accepts and six boundary refusals.
- The final compiler built and installed with its pinned inputs. It subsequently
  emitted byte-identical C for its own source (SHA-256
  `a60f0cbac11d8c4260655d4ad17a0cc97a8a2879af2049430726d0bebcd56154`). This is one reconstruction comparison, not the full
  multi-generation `--verify-self` campaign.

That is 26 executed programs, 20 expected refusals and two additional successful
runtime-only emissions. The compiler's full report and reproduction commands
are in `corboc/docs/DOCUMENTATION_COVERAGE_CYCLE.md` in the separate compiler
repository. Detailed results are retained in its `build/coverage-gaps/` and
related directories and this checkout's `build/coverage-gaps-docs/`.

The embedded runtime's source revision and decoded code did not change.
The compiler's resource generator uses a hex-string representation to avoid
one AST expression per packed byte during bootstrap. The existing decoder
regression retains its independent expected bytes.

Validation is scoped to the named observations and their directly affected
mechanisms. Other-platform execution and the full historical corpus were not
rerun. Windows ARM64 remains deferred. There was no independent audit or mutation
campaign here, and these results are not a general safety proof.
