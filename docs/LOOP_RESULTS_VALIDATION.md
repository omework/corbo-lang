[Français](LOOP_RESULTS_VALIDATION-fr.md)

<a id="validation-des-transferts-et-résultats-de-boucles"></a>

# Validation of transfers and loop results

Cycle of November 3, 2026. Decisions are recorded in
[LANGUAGE_RULES.md](LANGUAGE_RULES.md), in particular S5, S5a, V4, T6, T7,
T9–T11, D1, B2, A3, A5 and P8.
[verification matrix](VERIFICATION_MATRIX.md) linking the rules to the evidence
Part of this cycle.

The result of a `break` is materialized before cleaning.
transferred retains its address and changes the responsible person responsible for cleaning.
The connection keeps the modes, the
sources and possible targets, and source or target control
contracts spread the effects,
possible values and reset constraints through calls.
Un `continue` clean the iteration block and then return to the entrance.
`return` cleans the function's scopes without installing a result
The loop is interrupted.

The assessment of a replacement expression precedes the destruction of
the former allocation. Access to the recipient is verified from the beginning of the
branches that leave the function are excluded from the
a copyable copy provided by a `if` may change the content in
place. The semicolon distinguishes the marking `<- valeur;` value
finale `<- valeur`. The old examples and tests of block return have
was migrated to the final form.

In each stack of a pool, the allocation moves the cursor if it holds
A hole is taken in the index only at the limit.
The ordinary drop recovers the contiguous suffix already dead.
destroys first values in the semantic order of the blocks, then gives back
each cursor zero and emptys the indexes.
traverse slots in physical order after destruction.

<a id="contre-exemples-et-contrôles"></a>

## Counter-examples and controls

- A receiver moved on a single path is refused at the beginning of a
  later replacement. The valid neighbor leaves the function on the path
  A loan used for the last time in the
  right side is accepted, its neighbour who uses it after is refused.
- A local pool can provide a result to the internal loop and be too
  The second transfer is then refused.
  A value in a durable pool may also contain a loan to
  a local target already destroyed at the exit. The test uses the type
  concrete support, a field enum `&Int`.
- A reset before the last use is refused as soon as the result or a
  The borrowings it contains may depend on this pool.
  Two sources, opaque calls, reborrowing and use after junction.
- The prototype was historically accepted `<- valeur;` comme valeur finale
  The tests now distinguish the marking without receiver
  with warning and transfer that actually provides a result.
- The runtime used to favor the hole even when the cursor had
  One case with three slots checks that it is moving first, reuses
  the hole at the limit and returns to the first slot after reset.
  checks that an interlocked reset destroys the premises and then the receiver of the ancestor
  before you also recover the hole under the cursor.

<a id="exécutions"></a>

## Implementation

- Overall regression into four groups, 789 successful tests.
  the existing oracle C of 3,000 enum pool transitions and the model
  the spread of pool requirements through contracts.
- [test_loop_results.py](../tests/test_loop_results.py) contient 18 tests, dont
  22 programmes and 36 rejected cases tested by the
  The independent model
  build tracks from allocation lists by block.
  eight programs generated in their tracks and eight incompatible fashion neighbors
  The 18 tests also pass with seed 20261103.
  UBSan including with `-O2`The LTC `check` and `run` affiche
  warning on a transfer without receiver and binary ends with
  the following value in the re-used slot. An analysis of 233 prefixes
  of an example combining reborrowing and incompatible exits has not triggered
  no exceptions Python unmanaged.
- [Matrice C](../validation/loop-cycle-pool-c.json) of 12 executions, Homebrew
  Clang 20.1.3., C11 at O0, O2, Os and O2 levels with UBSan without recovery.
  It shall in particular verify the identity, the two selections of origin,
  variants and shutdown on exhaustion.
- [Mutations](../validation/loop-result-mutations.json), launched by
  [run_loop_result_mutations.py](../tests/run_loop_result_mutations.py).
  The four errors injected are detected.
  in iteration causes a crash, omission of durability control
  is later repeated by an internal invariant with another diagnosis,
  priority at the hole changes addresses and the decline too soon changes
  These results are only concerned with mutations
  choisies.
- ASan did not produce any usable evidence on this host.
  C minimal `int main(void) { return 0; }` compiled with
  `clang -fsanitize=address` He too is over three seconds.

Reproducible commands from the root.

```sh
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
CRUST_SANITIZE=undefined PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_loop_results.py -q
python3 tests/validate_pool_contract_c.py --output validation/loop-cycle-pool-c.json
python3 tests/run_loop_result_mutations.py
```

## Limites

The explicit reallocation of an ancestor works through blocks
The verifier still rejects branch junction or branch junction.
a loop is resumed if the connection of an ancestor has been replaced on the way.
The anticipated physical placement of transferred allowances remains a
optional optimization. Runtime follows the actual occupation of the
slots. The structured types of the prototype remain the fields enums taken
The cycle does not establish any general proof of the lifespans, nor does it provide any evidence of the
coverage of the user destroyers, or validity on another family
C.
