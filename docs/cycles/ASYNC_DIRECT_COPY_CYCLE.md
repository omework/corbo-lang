[Français](ASYNC_DIRECT_COPY_CYCLE-fr.md)

<a id="copie-directe-de-structures-dans-un-corps-async"></a>

# Direct copy of structures in an async body

<a id="règles-et-écart-corrigé"></a>

## Rules and deviations corrected

ST17/ST18 applies in an async body: explicit and structurally copying
authorized, conservation of shared targets, distinction between local value
No rule of law amended.

The programme `validation/open-async-direct-structure-copy.crust` was refused
by "copy requires a row or table", while the same copy in a
auxiliary synchronized. The refusal of the initial version is reproduced
in `validation/async-direct-copy-baseline.log`.

<a id="implémentation"></a>

## Implementation

Lowering now distinguishes the structure copy from that of an array.
It initializes a new independent object and copies the authorized fields:

- `copy(local)` uses the recipient data stack; the investment plan
  also identifies this manufacturer before a block release or async return.
- `copy(allocation)` keeps the actual pool of the original.
- `pool.copy(original)` explicitly selects the recipient pool.
- A local reference to the structure retains the origins of its storage
  The copies do not extend the targets.
- The proprietary fields and the mutable references make the copy refused.

The C uses the existing building primitives and then a copy of the
fields. It does not move an already built allocation. Local layouts
remain static in order to survive the async state producing.

<a id="cas-exécutés"></a>

## Cases implemented

Six methods targeted in `tests/test_async_direct_copy.py` : six executions
In the first half of the year, the number of disabled people in the country was about 5 %.
refusal checks.

- Copy via local reference, suspensions and transfers to the parent.
- Copy of a capture and return to the appellant, for local or pool origin.
- Copy to an explicit pool, destroy the original and re-use the slot.
- Copy of a shared field: destruction of the original authorized, destruction
  the target before its last reading refused.
- Copy fields A<T> or &mut Int refused; pool too short refused.
- C probe: separate original and copy, created in the destination
  outer surface before suspension, same address after extraction, empty state pool
  and storage recipient without living allowance after drop.

<a id="résultats-terminés"></a>

## Completed

All the processes below have been completed with code 0, without any skip test.

| Passage | Result | Journal |
| --- | --- | --- |
| Initial target O0 | 6 methods, 2,780 s | `validation/async-direct-copy-o0-first.log` |
| O2 regression before local aliases adjustment | 69 methods, 63,783 s | `validation/async-direct-copy-regression-o2.log` |
| Final target O0 | 6 methods, 3,426 s | `validation/async-direct-copy-o0-final.log` |
| Copy and Storage of Results, Final O2 | 20 methods, 13.416 s | `validation/async-direct-copy-final-o2.log` |

Clang C11, pthread, warnings as errors, fatal UBSan. Regression
69 methods were not fully repeated after the adjustment of aliases;
the 20 directly related methods were replayed on the final version.

<a id="reproduction-et-limites"></a>

## Reproduction and limitations

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_async_direct_copy
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_async_direct_copy test_async_result_storage test_async_local_parent test_select_result_placement test_async_result_factories test_public_structure_handles
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_async_direct_copy test_async_result_storage
```

Snapshot initial : `/tmp/crust-before-async-direct-copy/`. Patches archived in
`validation/async-direct-copy-{async_lowering,async_local_placement}.py.patch`.

Targeted coverage of Int and &Int representative structures; this batch does not connect
not the nested inline structures still not supported. No new
independent model, adversarial audit or mutation campaign. Results
does not constitute general proof of security and does not close the whole
The arbitrations scheduler and capture of handle launched
restent ouverts.
