[Français](ENUM_CORE_VALIDATION_CYCLE-fr.md)

<a id="retour-dune-allocation-denum-dans-le-core"></a>

# Return of an enum allowance in the core

The test `test_enum_expression_transfers_preserve_arm_and_cleanup_order`
utilise `fn main()`, a result and parameters `A<E>`, un `return`
by value and manufacturers `pool.new(E.Variante { ... })`. The parser
lowers these manufacturers to the already used pool enum construction
the auditor and the backend. The expected trace remains
`E.A(42)` then `E.B()` on the standard output, followed in the trace
cleaning `destroy fresh=E.B` then `destroy a=E.A`. The test runs
the program without the historical reset profile.

<a id="validation-ciblée"></a>

## Target validation

- The 20 tests of `test_arguments` go with `CRUST_SANITIZE=undefined`.
  [Journal](../../validation/enum-core-arguments.log)
- Both forms of manufacturer produce the same C for this program.
  Both compiler entries refuse a variant `E` increased to
  `Pool<Other>`. [Journal](../../validation/enum-core-pool-typing.log)

<a id="validation-générale"></a>

## General validation

The discovery includes 3,724 tests. The 258 modules are divided into eight lots.
by process. `CRUST_SANITIZE=undefined` and
`CRUST_TEST_OPT=-O2` for benches that display these settings.

The eight batches have been completed. `test_core_integration` passent.
The general follow-up indicates 98 failures of assertion and 127 errors, including
The reports concern 145 separate tests.
[Journal of the proceedings](../../validation/enum-core-global.log)

The 145 tests concerned also failed during their replay on the
a copy of the same compiler with the change of the removed parser.
The comparison is based on the status of each test.
every diagnosis of sub-cases is the same. Failures remain open.
[Comparative Journal](../../validation/enum-core-baseline.log)

This pass exercises both the kernel and the historical profiles of the repository.
It does not include new ASan execution or independent audit.
