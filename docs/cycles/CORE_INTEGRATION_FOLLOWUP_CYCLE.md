[Français](CORE_INTEGRATION_FOLLOWUP_CYCLE-fr.md)

<a id="intégration-des-closures-des-branches-et-des-corrections-du-noyau"></a>

# Integration of core closures, branches and corrections

<a id="corrections-du-compilateur"></a>

## Builder corrections

- The projections of tables returned by a task retain the
  The compiler processes the data separately.
  the named field paths. The witnesses cover a constant projection
  via `join()`, a dynamic projection via `.await` and a failure of
  Injected launch followed by new access to the table.
- `match h.await` reads the Boolean field indicated by the recovery of the
  Outcome. `if` combining a boolean expected and a local boolean can be preserved
  the type in the branches exercised.
- The typing refuses the scalar annotation `i32` for an allowance
  `A<i32>`. An indexed entry in a borrowed table transmits the type
  from the element to the literal before the async lowering.

<a id="closures-et-branches"></a>

## Closes and branches

A closure may receive a local structure by `move`. The Shared Call
project read capture and its destruction cleans the structure
The reference catches to scalar
and other cases opened in [the cycle of closures](CLOSURES_CYCLE.md)
Keep on connecting.

Synchronous wrappers `#(branch)` and
`#(branch: join=result.join())` are checked when they return a
direct launch, possibly via an immediate local link.
verification of a general body and the propagation of evidence of abandonment
through a public handle remain open.

In the digital profile, the compiler allows the abandonment of a handle
the signature and dependencies followed establish a concrete
scalar catch launch and scalar or empty result. Runtime
Re-uses his abandoned line of tasks. He recovers completed tasks.
when abandonment, subsequent assignment or closure
The systematic recovery at termination and calculation of the
of capacity in the presence of successive abandonments still to be completed.
`spawn_blocking` is reserved for the async context in the target profile and
its local result accepts an annotation `AsyncHandle<R>` Checked.
The distinction of hands through signatures remains open.

<a id="exécutions"></a>

## Implementation

- The 13 tests of `test_core_pending` and `test_closures` passent sous
  UBSan to `-O0` and `-O2`.
- The 13 historical projection methods identified in the sorting pass
  under UBSan to `-O2`.
- The extended pass from 40 tests to `-O2` The matrix of the
  results of public handles, former Boolean cases, obligations
  The historical profile and digital regressions are waiting for this pass.
  before the latest additions of targeted tests.

These passes target the discrepancies identified.
independent remain to be played again.
