[Français](CORE_ANNOTATIONS_CYCLE-fr.md)

<a id="directives-contrats-de-type-verrous-et-vecteurs-descendants"></a>

# Guidelines, type contracts, locks and progeny vectors

Source guidelines `#(directive: …)` are read by the parser.
`stack_region_max_size` accepte `K`, `M` and `G` and check the front size
conversion. `async_pool_sizes` requires at least one entry.
the old syntax remains accepted for the programs of the prototype.

The contract `#(type: T<R> with { … })` link names to the annotated function.
The solver checks the methods used in the body, even in the absence of
The appeal shall verify the signatures required, deduct the same signatures `R`
for all methods and control of possible alternatives.
The following is followed by the regular auditor and generation C.
For a Future from a `async fn`, the solver uses signatures
`id` and `poll` An auxiliary can transfer the task to the integrated runtime.
`runtime::spawn` and return one `runtime::Handle<R>`.

Both forms of `lock` and the orientation of the bands
The cycle replayed their existing tests.

<a id="vérifications-exécutées"></a>

## Audits performed

- **19 successful targeted tests** with `-O2` and UBSan on the executed C.
  Nominal contracts specialising in `i64` and `bool`, signatures incompatibles,
  alternatives, désaccord entre deux méthodes sur `R` et méthode non déclarée.
  Future contract until `join()`, with refusal of the `drop` premature target
  The three units are the source and boundary guidelines.
  `lock`, capture and launch failure. Order and address of slices
  in both directions, including a sub-tranche relayed by a task.
- **Expanded pass of 88 tests** 86 successes and two
  failures on programs without new contract. The historical test is waiting
  refusal of `fn a(self);` in a `type feature` while his parseur
  already admits this receiver. A historical async return `Handle<Bool>` produit
  access to `CrustJoinResult.bool_value` the C issued does not declare.

The compiler checks the operations of the specialized body with its types
The inference of the contract is based on a direct parameter of type `T` and
The direct manipulation of the required signatures. `Context` and
`Poll<R>` in a user poller remains out of the built-in runtime.
The adversarial campaign and the general follow-up remain distinct from this
passe.
