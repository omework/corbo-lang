[Français](CORE_LOCK_HASHMAP_CYCLE-fr.md)

<a id="contrats-de-verrou-et-stockage-natif-de-hashmap"></a>

# HashMap's native lock and storage contracts

[MT10](../ASYNC_MULTITHREAD_RULES.md#5-sûreté-mémoire-entre-threads) ajoute un
Lock contract on receiver. [HM1–HM6](../HASH_MAP.md) fix the keys,
operations, borrowings, storage and dependencies of the first
version of `HashMap`.

The parser accepts both forms of MT10 on synchronous methods.
The auditor associates the recipient's identity with the result and follows this
The use of the term "unsynchronous" is not a matter of the nature of the term "unsynchronous" and "unsynchronous" contracts.
providing a return or a return on acquisitions or results, keep the information.
parameters must designate separate objects, the contract has
The annotation is used for static analysis.
Real acquisition and liberation remain the body's responsibility.

The native storage of `HashMap` uses both ends of a data stack
dedicated. The entries grow at one end. The index grows at the other
and can be rebuilt in place. Free boxes are reused.
replacing an existing key does not consume any additional location.
Operations C distinguish between insertion, replacement and failure of
ability to publish a change.

Synchronous tests exert release by `drop`, by end of block,
moving to a new receiver and relaying by a function.
They check the refusal of a new acquisition after the last use of the
result, via an alias, via an auxiliary and after a single destruction
path. Refusals are verified in `verify_program` and `compile_source`.
The C probes check a collision, maintaining the address during the
reindexing, re-use of a box, restitution of old values,
cleaning the remaining values and both capacity paths.

The return of a method result through a relay exposed two defects.
The investment did not recognize certain methods as producers of a
The inference of provenance also used the identity of a call
This could prevent convergence.
Placement now recognizes these methods and inference retains identity
regressions include structural returns
and synchronous calls from async.

- [Selected UBSan-to- `-O0`](../../validation/core-lock-hashmap-o0.log).
- [Selected tests and regressions UBSan to `-O2`](../../validation/core-lock-hashmap-o2.log).

The passage of a result that carries an argument lock and its capture async
The tests are limited in the prototype.
and life, and rely on the contract provided by
implementation for effective locking.

Le code C de `HashMap` est exercé directement. Son raccordement aux
expressions, types and results Crust remains open, as well as monitoring of
borrowings and dependencies per input and order of cleaning of charges
The results are targeted functional tests.
