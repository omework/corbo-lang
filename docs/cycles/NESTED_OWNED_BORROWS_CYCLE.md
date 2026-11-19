[Français](NESTED_OWNED_BORROWS_CYCLE-fr.md)

<a id="emprunts-dans-les-descendants-possédés-dune-tâche"></a>

# Borrowing in descendants possessed of a task

<a id="règles-et-portée"></a>

## Rules and scope

Ce cycle applique ST6–ST15, H1/H2, B1–B5, D1, T1/T6, AS2/AS8–AS15,
RT6/RT8 and SL1. No normative rules are amended.
end can now contain &Int/&mut Int fields in their
The transfer and return of the entire graph shall retain the following:
sources and targets of these descendants.

The case `validation/open-nested-owned-borrowed-capture.crust`, auparavant
refused, is executed with exit 1. The neighbor who destroys number before
The initial log of the previous batch is refused at both stages.
The first decisions after correction are in the past.
`validation/nested-owned-borrows-first-probe.log`.

<a id="implémentation"></a>

## Implementation

- `owned_reference_paths` lists references via the possessed edges,
  with a complete path such as `.left/.view`. The homonymous fields of
  The crossing stops at the end of the
  first repeated type; cyclic type graphs are not generalized
  by this lot.
- Results contracts, storage constraints, symbolic parameters
  The backend keeps it alive.
  the loans of the children when building their bearer.
- After join, the returned dependencies are redistributed on children
  the reconstructed graph.
  overall lifespans but failed a child's reading with
  "receiving from missing borrowed field".
  `nested-owned-borrows-sync-explicit-read.log`, then covered by the test
  `test_sync_caller_result_keeps_nested_target`.
- The backend accepts the explicit borrowing of the contents of a field A<Structure>,
  for example `read(&*result.inner)`. It passes the descriptor of the child and
  Keeps the parent's reservation. `result.inner.view`
  is not added: the final tests use explicit de-reference.

The source patches are in `validation/nested-owned-borrows-*.py.patch`,
compared to the previous copy `/tmp/crust-before-nested-owned-borrows`.

<a id="validation-exécutable"></a>

## Executable validation

`tests/test_nested_owned_borrows.py` has 15 final methods.
The O0 count is in `validation/nested-owned-borrows-complete-count-o0.log`.
It is divided into 8,258 s: 23 native executions, 32 invalid programmes and
64 refusal checks, one per step for each program.
The O2 evidence is the basis of thirteen methods of
`nested-owned-borrows-final-mutations-o2.log`, then both additions
`nested-owned-borrows-mut-return-o2.log` and
`nested-owned-borrows-identity-o2.log`, executed separately.

The harness uses Clang C11/pthread, Wall/Wextra/Werrar,
Wno-unused-function and fatal UBSan at O0/O2. Invalid programs are
tested by verify_program and compile_source. No results found for ASan/TSan new.

Scenarios include:

- The independent model of the eight provisions of the three lifespans
  (Outdoor pool, indoor pool, target): only in case of all three
  survive allows to export the task.
- Direct calls, factories and a task relay called in context
  synchronous; whole returns by calling synchronous and async.
- The mutable targets before and after waiting, the child's re-borrowing and the
  refusal of access, replacement or drop incompatible before its last use.
- Two children with the same field name, two and four depths,
  conditional returns and conservation of the two possible targets.
- Drop of an inactive task, injection of launch failures, thread
  native, Select loser and immediate re-use of slots after cleaning.
- A C probe compares the addresses of the root, the child and its target
  The values and the
  unique destructions are also verified.

Log `nested-owned-borrows-first-tests-o0.log` contains the refusal of a relay
synchronous taking a task from an async body. This valid case remains open,
and has not been transformed into a normatively prohibited case to pass the
tests. The synchronous variant is tested; the async variant is kept in
a minimum file indicated below.

Exploratory reading trials intertwined with points, present in
`nested-owned-borrows-read-o0.log` and `nested-owned-borrows-nine-o2.log`, ont
prior to choosing to retain explicit access H2. The crossing code
The text of the text is not the evidence of the
syntaxe finale. `nested-owned-borrows-explicit-read-o0.log` and final follow-up
exercent `&*`.

## Mutations

Six errors are detected in temporary copies by
`tests/run_nested_owned_borrow_mutations.py` :

- Cut down the descent paths and omit the builder's loans make
  The absence of error is detected.
  both stages.
- Forget a descendant's prefix, dependence after restitution or
  symbolic target has valid programs denied.
- Sorting a possessed field as a simple reference causes a slot leak,
  detected by the re-use of a pool of two capacities (`pool capacity exceeded`).

The final passage is `nested-owned-borrows-final-mutations-o2.log`.
The nine mutations in the previous mixed batch are also detected in the
`nested-owned-borrows-historical-mutations-o2.log`. Their injection site on
the layout classification has been adapted to the new split calculation, with
the same objective to artificially refuse a valid mixed layout.
These selected errors are not a general detection rate.

<a id="régressions-et-limites"></a>

## Regressions and limitations

`nested-owned-borrows-regression-o2.log` 98 methods pass in 92,504 seconds,
after the catch has been propagated but before the refund corrective amount for
Dependencies on children. `nested-owned-borrows-final-regression-o2.log` :
96 methods pass in 91,087 s on the final code.
catch contracts by field, local envelopes, returns of
owner/borrowing structures, field handle bridges and
The two selections require a reference to be taken of structures.
CRUST_SANITIZE=undefined and overlap; their accounts do not add up
Not like a single test.

Synchronous Supplement `nested-owned-borrows-sync-regression-o2.log` passe
87 methods in 41,780 s: shared/mutable fields, reference tables
nested and proprietary results, with CRUST_SANITIZE=undefined. It tests
joint analyses affected by the spread of the descent paths.
All of the final processes cited are completed.

This evidence is over, and it does not demonstrate the overall safety of the model,
neither all compositions nor cyclic graphs. reset() remains removed
normal profile, without reintroduction into this cycle.

## Cas encore ouverts

- `validation/open-nested-detached-reference.crust` : to return only the
  shared field of a descendant via `read(&*value.inner)` remains refused as
  return is unsustainable, although the external target survives.
  the target regardless of the storage of both carriers.
- `validation/open-async-task-relay-argument.crust` : un appel synchrone
  taking a task as argument from an async state remains unconnected.
- Changes to the fields of a descendant via an auxiliary are not
  Probes `nested-owned-borrows-replacement-probe.log` and
  `nested-owned-borrows-sync-replacement-probe.log` record refusals
  The current situation, both for the old and the new target.
  `validation/open-nested-field-replacement.crust` keeps the valid neighbor
  which releases only the old target; its refusal to both stages is
  reproduced in `nested-owned-borrows-replacement-fixture.log`.

The first two refusals are reproduced in both stages in the
`nested-owned-borrows-next-probes.log`. The public API of the scheduler, the
General investment, other signatures and the two arbitrations on the
The overall objective remains active.
