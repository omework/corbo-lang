[Français](OWNED_RESULTS_CYCLE-fr.md)

<a id="résultats-propriétaires--cycle-du-7-novembre-2026"></a>

# Owners results — cycle of November 7, 2026

<a id="périmètre-et-statut"></a>

## Perimeter and status

Partial integration of draft 01, rules U1/L6/F2/H1/VE3/VE4.
The normative rules are updated in LANGUAGE_RULES.md and
FOUNDATIONS_AND_VECTORS.md. The lot and overall objective remain open.

The control is about the type: even a `pop` statically empty does not allow
not `Some(_)`, nor an unused proprietary link. An entire variant
masked by `_` cannot conceal an allowance.
`try_push` and the error details without allocation can be ignored.
The fields that own consumed enums follow the same control, even if they are not
if the specific variant is known. A conditional reading is sufficient;
the range cleaning remains performed if this reading does not occur.

`drop(-> v.pop())` and `drop(-> v.try_push(-> entrant))` are lowered to
temporary reception followed by destruction. Constraint analyses,
The C destroys only
the content possessed of the actual variant, before the next instruction.
The borrowing test checks the call through two functions and the ban
The addresses are compared when using an alias after destruction.
Reuse of a pool of a slot.

<a id="défauts-et-adaptations"></a>

## Failures and adaptations

- The evaluation check was not enough: one branch `Some` pouvait
  be eliminated on an empty vector. The pattern control now precedes
  This assessment.
- The path async accepted `Ok(_)` and `Ok(inutilise)` on a result of
  he is now controlling the reasons and
  explicit uses; unused link of waiting result is refused.
- This new control initially rejected a valid export at the end of the block
  async: the last `<- r` was removed from the body before the control.
  Exported is now transferred to the user control.
- Several old tests explicitly allowed the owner abandonment.
  They now use named links, readings or `drop`.
  The tests for the prohibition of copying and incompatible types use their
  link to avoid masking the diagnosis targeted by U1.
- A trace changes intentionally: when the two fields of an enum
  are extracted, its empty container is destroyed before the body of the arm; the
  `drop` The former pattern comes in the second field. `_`
  destroyed this field during the dismantling of the container.
  Waiting keeps an accurate record and re-use verification.
- New test fixtures have also been corrected: construction
  a field with `<-`, and comparison of a `&A<Int>` via `vequals` I'm not sure.
  that an attempt to read as a `&Int`.

<a id="preuves-exécutées"></a>

## Evidence

`tests/test_owned_results.py` : nine methods, eight native programmes admitted
and 58 configurations refused by passing. Cases combine presence/absence,
immediate/differentiated match, motives, calls, borrowings, destruction, ability,
source, re-employment and expectation async.

Implementation `-O0` and `-O2`, C11 clang, UBSan with
`-fno-sanitize-recover=all` : nine successful methods at each level,
4,963 s and 4,025 s at the final crossing respectively.
Journal : `/tmp/crust-owned-results-optimizations-final.log`.
This section also includes the case `Some(_)` on a Copy element.
Standard passage reproduction control:

```sh
PYTHONPATH=.:tests python3 -m unittest test_owned_results -v
```

The script `/tmp/crust_owned_optimizations.py` replaces only the level
`-O2` compile commands by the chosen level; it keeps the
sanitizer and his fatal mistakes.

Initial regression: 140 methods of FoundationTests whose name contains
`handle`, `consum` ou `owned_field`, 80,128 s, five failures and 25 errors.
Journal : `/tmp/crust-owned-result-initial-regression.log`.
After first migration: 147 methods (140 and seven new tests)
The causes were:
corrected: one remaining reason, order of the transfer of the scope input, a
The pattern of interlocked sum and the dismantling trace described above.
The four methods then go to 4.274 s
(`/tmp/crust-owned-migration-corrected.log`).

First regression async: 26 methods whose name contains `owned`,
64,909 s, two failures and five errors. She detected the old expectations
Abandonment, masked diagnostics and the above block export defect.
Journal : `/tmp/crust-owned-async-regression.log`.
Final re-launches after corrections:

- 140 successful synchronous methods in 115.324 s:
  `/tmp/crust-owned-foundation-final.log`.
- 26 successful async methods in 68,306 s:
  `/tmp/crust-owned-async-final.log`.
- Python compilation of the six modified modules and three test modules:
  successful (`python3 -m py_compile ...`).

Selections are reproducible with `unittest.defaultTestLoader` :
FoundationTests keeps names containing `handle`, `consum` ou `owned_field` ;
AsyncRuntimeTests keeps names containing `owned`. Sub-cases of tests
historical data are not confused with their number of methods.

## Mutations

Three temporary copies of the compiler, tests and expectations unchanged:

| Injected fault | Observation | Classification |
| --- | --- | --- |
| Remove the payload type control before evaluation | 18 invalid subcases accepted | Detected |
| Removal of the control of owner pattern in the arm async | Three invalid reasons accepted | Detected |
| Failure to `cell_drop` in conditional cleaning | The valid program can no longer reallocate its unique slot: `pool capacity exceeded` | Detected |

Journal : `/tmp/crust-owned-results-mutations.log` ; script reproductible
`/tmp/crust_owned_mutations.py`. The directories of mutants are entered
This small sample does not give an overall detection rate.

<a id="limites-et-travail-restant"></a>

## Limitations and remaining work

- U1 is not yet generalized to all proprietary links.
  Counter-examples accepted at the end of this first step, then corrected in
  [U1_RECEIPTS_CYCLE.md](U1_RECEIPTS_CYCLE.md) :

  ```rust
  let mut p = pool<Int>(1);
  let unused = p.new(1);
  ```

  ```rust
  async fn f(n: -> Int) -> <- Int { return <- n; }
  async fn g(n: -> Int) { let unused = f(-> n).await; }
  ```

  These differences have been corrected in the next cycle; they do not constitute a
  The Wrappers Displaced and the Async Integrated Results
  also require a systematic audit of each receiving path.
- No new formal evidence, ASan/TSan campaign or general model
  The new tests are the first to be carried out in the first stage.
  specified results, addresses, destruction events and pool limits
  directly; they do not deduct the expected C generated.
- Historical regressions of reset explicitly use the profile
  `allow_legacy_reset=True`. They check historical interactions,
  not the availability of this API in the public prototype.
- The validations are targeted. Crust's overall suite and the others
  lots (stockage complet, type features, dernier runtime/scheduler/Select/
  (mutex) are not declared completed by this cycle.
