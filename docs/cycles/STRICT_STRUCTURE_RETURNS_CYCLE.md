[Français](STRICT_STRUCTURE_RETURNS_CYCLE-fr.md)

<a id="cycle--retours-nominaux-t-et-allocations-at"></a>

# Cycle — Nominal returns T and allowances A<T>

<a id="règles-et-périmètre"></a>

## Rules and scope

V1, T6, H1 and draft 05 distinguish the local value `T` of the allowance
`A<T>`This cycle applies this distinction to type-owner returns
Nominal (structures/enums known to compiler)
The old conventions of primitives, including the `-> <- Int`, are
Not redefined here.

The case recorded in
`validation/open-plain-structure-return-from-handle-result.crust` renvoyait
one charge `A<Point>` resulting from a `Vector.replace` under a signature
`Point`It is now refused by `verify_program` and `compile_source`.
The diagnosis performed is kept in
`validation/strict-structure-returns-recorded.log`. With the signature
`A<Point>`, the same program keeps the outputs `7, 9, 10, 11` and reuse
The C is kept in the
`validation/strict-structure-returns-exchange-point.c`.

<a id="implémentation"></a>

## Implementation

- The analysis of storage requirements processes each nominal return owner,
  including uncalled definitions and final return without semicolon. A bare signature requires storage
  local ; `A<T>` demande un pool.
- These requirements are extended to existing contracts and relays.
  continue to check contracts without re-tracing the body of the calle.
- The verification of C-retirement also rejects a source of
  pool under a local nominal signature.
- A pool requirement inferred from a nominal parameter indicates the type of its
  symbolic source. Otherwise, a copy helper correctly declared
  `A<Point>` was refused during the verification of his body.

The C representation and runtime do not change. No conversion of storage,
no additional copying and no implicit promotion is introduced.

<a id="tests-ciblés-et-migrations"></a>

## Targeted testing and migration

`tests/test_strict_structure_returns.py` adds six methods: nine programmes
In addition, the number of disabled people admitted to the labour market and 14 disabled programmes checked at both entrances.
local/pool, relay, forward/post transfer borrowing, branches, definition
unused, async and join return are exercised. Exits and re-use after
destruction are explicitly expected.

Historical tests that referred an allowance to a nude nominal type
are migrated to `A<T>` to keep their scenario. Local/pool couples
use separate signatures. Cases of internal copying to a task that
returns an Int keep both storages without a nominal return helper
ambiguous. The assertions of result/destruction remain in place; an assertion
The diagnostics can be adapted to the control now earlier.
historical fixeds remain preserved; program transformations
are visible in the archived tests and diffs.

<a id="exécutions"></a>

## Implementation

- First passage O0: 35 methods, 25.387 s, code 1; four scenario failures
  The helper promised Point but produced a copy of the pool.
  Log : `validation/strict-structure-returns-initial-o0.log`.
- O0-targeted after migration: 16 methods, 5.844 s, code 1; five failures due to type
  missing from the symbolic source of the pool copy. Log:
  `validation/strict-structure-returns-targeted-o0.log`.
- Targeted O0 after correction: 16 methods, 7,983 s, code 0. Log:
  `validation/strict-structure-returns-targeted-second-o0.log`.
- First regression O2: 227 methods, 165.714 s, code 1; 225 succeed.
  A test was waiting for the copy label of the helper replaced by an internal copy
  (`q` for `async copy`) ; the expected number of destructions remains two.
  Another used the same Point nominal return for both storages.
  He now has two explicit signature helpers, with the same
  The same co-existence of the original and copy during the evaluation.
  Log : `validation/strict-structure-returns-regression-o2.log`.
- The final return `<- valeur` still needed to spread the same requirement
  the explicit return. The valid case initially refused is retained in
  `validation/strict-structure-returns-implicit-before.crust/.log` ; a test of
  relays and invalid sound are added.
- Third target: 41 methods, 20.631 s, code 1 (three failures and
  The 22 additional Foundation methods migrate feedback
  The four chess sets are reproduced, unchanged,
  in the compiler copy and tests taken before this batch: four methods,
  1,759 s, code 1. Logs `strict-structure-returns-targeted-third-o0.log` and
  `strict-structure-returns-foundation-baseline.log` sous validation/.
- Fourth targeted passage: 41 methods, 26.806 s, code 1; correction of
  masking and the three historical scenarios pass, except the expected name of
  destruction of the new field (`champ=8`, and not `item=8`) This assertion
  keeps the exact account of one; the label is corrected.
  Log : `validation/strict-structure-returns-targeted-fourth-o0.log`.
- Final target: 21 methods, 18.702 s, code 0. O0/UBSan for targeted tests
  and contracts, native O2/UBSan configuration historical for the four
  Foundation methods. Log: `validation/strict-structure-returns-targeted-final-o0.log`.
- Supplement after migration of historical signatures Holder/Root/View in
  the following repayments and reborrowings: 14 methods, 11.973 s, code 0,
  O2/UBSan. Log : `validation/strict-structure-returns-migrated-reborrows-o2.log`.
- The number of cases of accidents is 276, 233.082 s, code 1; 270 are successful,
  five failures and one error come from the old signatures in both
  The following are the reasons for the repayment/reborrowing of the loan before their migration:
  of 14 methods above fully reexecutes these two suites and closes these
  Six failures on the same compiler, without changing code between runs.
  This is not a green monolithic pass.
  `validation/strict-structure-returns-regression-final-o2.log` and
  `validation/strict-structure-returns-migrated-reborrows-o2.log`.
- The correspondence of the six identifiers failing with the success of the supplement,
  the 276 separate identifiers covered and the final fingerprints were
  Reviewed. `validation/strict-structure-returns-validation-summary.json`.
  No unresolved failure remains in this selection; this finding does not
  not on the entire deposit.

The harness passes through the two Crust inputs then compiles the C with pthread,
Wall/Wextra/Werrar and fatal UBSan. O0/O2 is transmitted by
`CRUST_TEST_OPT`. The selected Foundation tests use their
native historical configuration and explicit legacy-reset profile.

<a id="écarts-historiques-directement-rencontrés"></a>

## Historical differences directly encountered

Three assertions had become obsolete with already recorded extensions:

- Restitution after replacement of a proprietary field is permitted
  ([previous cycle](RETURNED_OWNED_REPLACEMENT_CYCLE.md)) The old refusal is
  replaced by an execution that checks the root identity, result 8,
  the destruction of the old and new fields and the re-use of the two pools.
- A shared reference copied from a field keeps the target, without remembering
  the holder ([previous cycle]](ASYNC_DETACHED_FIELD_RETURNS_CYCLE.md)) Destroy
  the former bearer or reset his pool is therefore accepted and executed; destroy the
  The case remains legacy only.

The fourth failure is a pre-existing contract default: a mutable reference
created before masking the owner variable updated the symbol
The analysis of the results and the results of the analysis of the results of the
The two are now reunited with the wearer masked by his identity.
branches of the existing test retain their values 1/3 and the two targets
potential remain protected against drop. The contract coverage variable
is not deleted or weakened.

## Limites

The finished local/pool models already present are preserved. No new
In-depth advertising campaign, mutation or adversarial research is not launched.
The withdrawal of reset from the normal profile remains unchanged.
loads of collections with nested dependencies, nor async envelopes
no Int, nor the general advance placement or public integration of mutex.
The results do not constitute general proof of security or a closure
the overall objective.

<a id="artefacts-et-suite"></a>

## Artifacts and sequels

The initial copy is `/tmp/crust-before-strict-structure-returns` (modules Python
The 20 exact diffs are archived under the following headings:
`validation/strict-structure-returns-*.patch` ; the manifest
`validation/strict-structure-returns-changes.json` contains prints
before/after. The final selection of the tests is recorded in
`validation/strict-structure-returns-final-test-selection.txt`.

Next concrete gap: `validation/open-typed-async-vector-option.crust/.log`.
The Async Signature `Option<A<Point>>` is explicitly refused both entries.
The corresponding synchronous behavior is connected; its async integration
The remaining requirements are not modified.

Replay extended selection on current state:

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 - <<'PYTEST'
import unittest
from pathlib import Path
names = Path('validation/strict-structure-returns-final-test-selection.txt').read_text().splitlines()
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
raise SystemExit(not result.wasSuccessful())
PYTEST
```
