[Français](ASYNC_DIRECT_OWNED_RETURNS_CYCLE-fr.md)

# Retours directs d'allocations attendues

<a id="règles-et-défaut-reproduit"></a>

## Rules and default reproduced

This lot applies T1/T6, D1/T11, V5, L1/L2, AS4/AS8/AS10/AS12 and SL1.
No normative rules are amended.
[open-direct-awaited-allocation-return.crust](../../validation/open-direct-awaited-allocation-return.crb)
was refused by verify_program and compile_source to `return <-leaf(p).await;`,
despite the explicit marker. Diagnosis is kept in
[original journal](../../validation/direct-awaited-allocation-return-baseline.log).

An inactive task directly renders its type of result. A handle launched
makes a Result: this difference must remain visible in the type, including
Without intermediate variable. Returning an allowance does not extend its pool.

<a id="implémentation"></a>

## Implementation

The explicit owner return now uses the common treatment of
The latter also recognizes the expectation of a task
The results are calculated and then verified for the exact type of the result.
before export; the cleaning of the scope does not include the allocation
Transferred. The fields of the state and allocation are not moved.
Named returns retain their previous behaviour.

The same path now accepts an allowance produced by waiting for a
task calculated as transferred argument, with preservation of cleaning during
the evaluation of the following arguments.
They are not a direct result, but rather an A<T>.

<a id="scénarios-et-preuves"></a>

## Scenarios and evidence

`tests/test_async_direct_owned_returns.py` exercises the four A<Int> families,
A<String>, A<Vector<Int>> and A<Vector<u8>>. For each: direct expectation,
named task, task rendered by a block and conditional branch owner.
The exits are observed and the pool at a slot is reused after destruction.
An injected launch failure does not perform the task body.

The rejected neighbors omit the arrow, make an allocation of a local pool
too short, confuse the result of the handle with that of the task, or change
the type of allowance. Transfer of an allowance calculated to a call
synchronous or async is also interrupted by a return in the following argument,
after suspension: the call does not take place and the prepared result is destroyed.

The return of a Select result retains its winning charge and cleans up
selection. The ordered case tested makes 7 and does not build the charge 9
The two pools remain reusable afterward.

Two C probes have only one unlaunched root.
destroyed at the first point of suspension and observed a single destruction
The second continues until the child's allowance is handed over.
the result and check that the address obtained is the one of entry.
the same slot can be reused. These probes do not introduce cancellation
a task launched.

<a id="exécutions"></a>

## Implementation

Clang C11, pthread, Wall/Wextra/Werror, Wno-unused-function, UBSan fatal.

- `validation/direct-awaited-allocation-initial-o0.log` : six methods,
  16,060 seconds, OK on the lot code.

- `validation/direct-awaited-allocation-mutations-o2.log` : baseline finale
  of six methods, 21,993 s, OK; three injected errors detected (refusal of
  valid return, premature destruction of the returned allowance, forget the
  cleaning of the suspended child). Campaign completed with code 0, none
  Survivor or inconclusive in this sample.

- `validation/direct-awaited-allocation-regression-o2.log` 44 methods,
  102,279 s, OK on the final code. Select results, synchronous calls
  owners, suspended cleanings and the whole lot of the Results
  produced by await are replayed together.

All these processes are completed with code 0. The modified modules and the
new tests/runners pass py_compile. Reports links have been
The patch is kept in
[async_lowering-direct-awaited-allocation.patch](../../validation/async_lowering-direct-awaited-allocation.patch).

## Limites

Not all four families and syntactic forms tested cover
The identity and destruction probes carry the aggregates of the owners.
on finished roads, without general proof of safety or ASan/TSan result.
The running of the schedule has not changed.
owned by inactive tasks and Select losers remain open.
The overall objective is not over.
