[Français](ASYNC_MIXED_STRUCTURES_CYCLE-fr.md)

<a id="structures-async-à-champs-possédés-et-empruntés"></a>

# Async structures with fields owned and borrowed

<a id="périmètre-et-règles"></a>

## Perimeter and rules

Ce cycle applique ST1/ST6–ST16, B1–B5, D1, T1/T6, P3/P4, AS2/AS8–AS15,
RT6/RT8 and SL1. No normative semantics are changed.
may have allowances in its fields A<T> while borrowing others
Transferring this structure retains separate obligations to
his pools and his targets; destroy the structure destroys his possessed children,
Never the targets she borrows.

The lot covers direct borrowed fields &Int/&mut Int and descendants
It does not end the construction of mixed recursive graphs.
PR1 remains unchanged: reset() is removed from normal profile.

<a id="contre-exemples-et-corrections"></a>

## Counter-examples and corrections

- `validation/open-mixed-owned-borrowed-capture.crust`previously refused,
  executes and produces 16. The families of authorized layouts were calculated
  separately in backend and effect analysis. `structure_shapes.py`
  now share the calculation of the representable graphs.
- A synchronous factory called from an async state could return a
  the work the contract mentioned `allocation_field_parameter`but the bridge
  He now retains the pools of the argument possessed,
  This layer retains a conservative union of these
  sources; it does not claim an individual accuracy of all fields.
- A loop replacement was refused when the new carrier
  The local job was going through a task that returned to him.
  fresh creations, but not these retransmissions. He now follows the
  parameters returned in async contracts and result sources of the
  The address is not moved.

Initial refusals are retained in
`validation/mixed-structures-before-storage-fix.log` and
`validation/mixed-structures-expanded-o2.log`. The tests also retain the
invalid neighbours: too short pools, loans destroyed prematurely, copying
ownership and implicit promotion of a target created in a child.

<a id="preuves-exécutées"></a>

## Evidence

`tests/test_async_mixed_structures.py` contains thirteen final methods.

- `validation/mixed-structures-final-count-o0.log` : 13 methods in 13.402 s,
  23 native executions, 32 invalid programmes and 64 refusal checks
  (verify_program and compile_source).
- The basis of the `validation/mixed-structures-audited-mutations-o2.log` pass the
  13 methods at O2 in 13.696 seconds.
- Harnais natif : Clang C11/pthread, Wall/Wextra/Werror, Wno-unused-function,
  Fatal UBSan, O0/O2. Denials of native launch and submission are injected.

The independent model of durability crosses three booleans: the porter pool,
pool of the field owned, target borrowed. The eight provisions are exercised
by direct call and by factory. Only the arrangement where the three survive
one additional case keeps the pool outside but creates its target
in the child block: it remains refused, in accordance with the absence of promotion.

The tests also cover the mutable fields, the return of the whole carrier,
the detachment of a view after the destruction of the bearer and his child,
synchronous helpers, re-use of capacity pools one, loops and
replacements, inactive tasks, launch failures, threads
The first is the first of the three three groups of the group.
A C probe observes the root, his child possessed and his target borrowed from
each suspension and after transfer: same addresses and values.

Two probe errors were corrected without changing the compiler:
un transfert descendant `a ->;` missing, then the probe read an Int scalar
with the payload structure drive. Initial logs
`mixed-structures-identity-o2.log` and `mixed-structures-identity-final-o2.log`
The corrected probe uses the scalar field `Cell.value` and
Go through both final suites.

<a id="mutations-et-audit-du-test-survivant"></a>

## Mutations and audit of the surviving test

`tests/run_mixed_structure_mutations.py` inject nine errors into copies
All are detected in the final passage: artificial refusal
a mixed layout, refusal of a source of field, escape of a child, destruction
a borrowed target, forgotten of an owner prepared during a suspension,
loss of loan returned directly or via factory, loss of investment via task
directe ou via fabrique.

Both loan losses mislead program to invalidate target
before use; tests detect the absence of error in both stages.
destruction mutations fail in traces, re-use or guards
The overly restrictive deployments fail on the valid programs.

The oblivion of a prepared owner had survived in the passages
`mixed-structures-final-mutations-o2.log` and
`mixed-structures-complete-mutations-o2.log`. The injection site was
the destroyer of a suspended state, while the selected test exercised a
a specific test now suspends the evaluation of the second
argument, loses this branch of Select and then re-uses the slots of the
The fault is detected in the
`mixed-structures-audited-mutations-o2.log`. No general detection rate
is deducted from these nine selected errors.

<a id="régressions-et-chronologie"></a>

## Regressions and chronology

- `mixed-captures-initial-regression-o0.log` : 46 successful methods before the
  source and placement patches of this cycle.
- `mixed-structures-regression-o2.log` : 161 successful methods in 134,650 s,
  with the source patch, before the placement. Modules: captures
  and returns, borrowing, contracts by field,
  local production, owner/borrowed and their
  envelopes, structural effects, structural pools and borrowing pools.
- `mixed-structures-placement-regression-o2.log` 33 successful methods in
  34,414 s after the placement patch: loops, parent placement and
  local results to descendants possessed.

Both O2 selections explicitly request CRUST_SANITIZE=undefined.
They overlap and are not added as unique tests.
The final targeted passages cover the latest additions.
no new ASan/TSan validation or formal evidence.

<a id="écarts-restants"></a>

## Remaining differences

Update: the [derived borrowing cycle]](NESTED_OWNED_BORROWS_CYCLE.md)
corrects the refusal to capture the graph below and adds its entire returns.
The limitations described here are those of the end of this batch.

`validation/open-nested-owned-borrowed-capture.crust` contains an Outer which
has an Inner containing &Int. Pools and target survive the wait,
But this programme is still being rejected in both stages:
`validation/mixed-structures-next-nested-probe.log`. We need to extend the roads
of the descendants owned. This
restriction does not become a normative rule.

General async signatures, the public API replacing the scheduler,
the general placement and the two arbitrations on the hands launched remain
The overall objective is not achieved or blocked by this batch.
