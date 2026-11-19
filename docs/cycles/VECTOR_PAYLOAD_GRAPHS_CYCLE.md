[Français](VECTOR_PAYLOAD_GRAPHS_CYCLE-fr.md)

<a id="cycle--graphes-des-éléments-de-vecteurs-locaux"></a>

# Cycle — Graphs of local vector elements

<a id="portée-et-règles"></a>

## Scope and rules

Application of H1–H3, VE1–VE4, F2–F4, B1–B5, D1–D3 and the rules of
transfer/cleaning by scope. No normative rules are amended.
AGENTS.md, VALIDATION_GUIDELINES.md, the decision index and the rules
The priority remains the implementation of the relevant cases.
The independent adversarial laboratory
is not executed or deemed to have been completed by this cycle.

This lot opens the vectors **locaux synchrones** Of handbags, of which the objects
contain references and/or allocations. It does not close the site
their parameters/function results and their
Async integration still to be connected. Functions can already build
a local vector and return the extracted object, with propagation of its fields
borrowed from the contract.

<a id="implémentation"></a>

## Implementation

- The vector keeps the graph of each element, indexed by identities
  The routes of dependencies and sources
  follow these graphs, including the progeny owners.
- Remove and pop transmit the borrowed fields, the parents of reborrow,
  the proprietary fields and possible variants of the new access.
  Options, loop outputs and junctions keep this data.
- Replace and try_push record the graphs of the two possible results.
  The extraction of a result selects the graph from his arm. The update
  a box via a mutable loan also records the incoming content.
- Branch states and the fixed point of loops include graphs.
  New identities created during a reanalysis are not mistakenly taken
  for a semantic change requiring infinite reanalysis.
- The symbolic analyses of results and constraints retain the
  complete values of the elements next to their storage identities.
  Extraction restores metadata from fields; contracts of object
  extract can be used by a caller and then by a relay.
- Signatures of complex vectors still incomplete retain refusal
  This is a deviation.
  temporary implementation, not a new language restriction.

The storage runtime and the addresses of the objects do not change.
the existing handles; the cleaning of the vector already calls that of the elements.

<a id="scénarios-et-défauts-rencontrés"></a>

## Scenarios and defects encountered

Eleven targeted methods: **20 executions C** with prior passage through
verify_program and compile_source, and **28 programmes invalides** controlled by
two entries (56 refusal decisions).

- Push/remove keeps a shared reference, allows reading content,
  then re-use of a capacity pool 1. The premature drop of the target and
  the use of the old displaced handle is refused.
- Pop direct, named option, if and loop option: content
  read and then destroyed; dependence remains active as long as the result is to serve.
- Item has Inner, which borrows Int: read through a function, clean
  unique of the two objects and reuse of their pools; drop of the refused target
  before extraction and before use of the extracted object.
- The &mut Int field prohibits reading, mutation and destruction of
  The six refusals cover the vector and the object extracted.
- Replaces with valid/invalid index returns the old object, respectively
  or enter, and preserve the dependencies of the two still possible objects.
- Try_push successful, direct consumption by drop of remove/pop, replacement
  &mut A<Item>: responsibility and cleaning retained.
- Remove from the first box distinguishes two objects from the same borrowing pool
  Two targets; the first target can be destroyed after its object is extracted.
- Re-use on three iterations and transfer vector from if/loop.
- Un constructeur utilisant un vecteur local rend l'objet extrait ; un relais
  The loan contract is retained.
  the appellant remains refused.
- The transfer refuses an element pool or a target that does not survive the
  No implicit displacement of these dependencies is introduced.

The first test revealed a loss of type/fields of the owner descendant
in the symbolic analysis: the local C could keep the graph, but a
call on this descendant was refused. Metadata are now stored
by analysing results and constraints, without circumventing their controls.

Three failures in the third trial were from the new test examples:
reborrowing pool with unsupported syntax (the parameter already borrowed
is by its name), missing downward transfer before insertion into the
child block, and text substitution missing a line jump.
have been corrected in accordance with existing rules; security expectations
have not been changed.

<a id="preuves-dexécution"></a>

## Evidence of enforcement

- Initial recorded case: output 7 and then 9 and traces of destruction in
  `validation/vector-payload-graphs-first-o0.log`. The newspaper is finished;
  the former process identifier was no longer available at the time of resumption.
- First target O0: six methods, 4.046 s, code 1, a metadata failure.
- Second target O0: six methods, 4,909 s, code 0.
- Third target O0: ten methods, 5.178 s, code 1, three fixture errors.
- Target 4 O0: 10 methods, 6.732 s, code 0.
- Target 5 O0: eleven methods, 7.082 s, code 0.
- Final target O0: eleven methods, 7.029 s, code 0,
  `validation/vector-payload-graphs-targeted-final-o0.log`.
- O2 regression: 135 methods, 113,766 s, code 1, seven subcases failed
  in five historical methods.
  `validation/vector-payload-graphs-test-selection.txt`, journal
  `validation/vector-payload-graphs-regression-o2.log`.
- Producing on snapshot before batch: 15 methods, 7,604 s, code 1,
  the same seven failures. `validation/vector-payload-graphs-nested-baseline-o2.log`
  explicitly indicates the path of the saved compiler.
- After updating the only annotations of the fixtures: fifteen methods,
  10,713 s, code 0, `validation/vector-payload-graphs-nested-final-o2.log`.

The seven former sub-cases returned pool allowances with an annotation
T local. They now announce A<T>, in accordance with the normative distinction
The assertions of destruction, identity and refusal remain in place.
The regression of 135 methods and this complement of 15 methods
on the **Same compiler** closes the observed failures; it is not a passage
monolithic of 135 methods entirely green.

Two existing models are replayed without changing their predictions:
the eight combinations of the external pool/downstream pool/target lifespans
(one program admitted and seven rejected), and the four local/pool combinations
They do not model to them.
only the operations of the new vectors.

The C11 harness compiles with pthread, Wall/Wextra/Werrar and fatal UBSan.
The original source is `validation/open-vector-handle-borrowed-fields.crust` ;
its current C is retained in `validation/vector-payload-graphs-remove.c`.
The initial failing newspapers remain present.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Valid case `validation/open-vector-payload-contract.crust` remains refused
both inputs: one function receives &mut Vector<A<Item>> and
Returns an extracted borrowing object. The associated journal keeps the diagnosis.
These metadata have yet to be formalized in container and
their mutations, then to transmit them to the catches/results async.

The deferred trade shall keep a conservative union of the possible elements of the
vector; this lot does not promise a new precision for all indices or
all the correlations between variants. Complex enums, loads of
recursive collections, readings by all forms of projections and
General async compositions are not validated here.
previous async routes do not establish their support for these graphs.

Reset remains absent from the normal profile. Mutations and adversarial research
The following are the results of the study:
does not provide any general proof of security or closure of the overall objective.

<a id="traçabilité"></a>

## Traceability

Snapshot avant lot : `/tmp/crust-before-vector-payload-graphs`.
Accurate tracks and forward/after prints:
`validation/vector-payload-graphs-changes.json`.
