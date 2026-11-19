[Français](LOOP_REPLACEMENT_VALIDATION-fr.md)

<a id="validation-du-remplacement-dun-receveur-à-travers-une-boucle"></a>

# Validation of a receiver replacement through a loop

This cycle extends the implementation of S4, S5, T7, T9, T11 and V4 to
explicit replacements of recipients reported before a loop.
It applies the existing life, borrowing and borrowing premises
of the destruction of rules D1, B2, B3, L3 and A5.

The replacement evaluates its right side and then destroys the old allowance.
The receiver's C pointer is updated after the iteration is cleaned,
before resumption by `continue` or the normal end of the body.
`break`, including false test output of a `while`contribute to the
junction after loop. Sources, dependencies and possible variants
sont propagées aux reprises et aux contrats de fonctions. Un `return`
does not feed the junction of the loop.

## Contre-exemples

- Reseting a pool at the beginning of the iteration is dangerous if the recipient
  can now come from this pool and still needs to be read.
  reanalyze the loop with the source of the replacement and refuse this case.
- By carrying the abstract identity of the recipient from one iteration to another,
  an old imported access could become visible again in the grandparent
  with its former pointer C. The minimum case matters `r`, remplace `r`
  in a `while`, then mark `<- r;` in the import block.
  Original import is now detached when a recovery can replace
  The initial access after the block is denied.
- A loan formed before the loop does not follow the replacement. A neighbor
  valid borrows the value in the iteration and ends this loan before
  The conflicting acceptance orders between the
  The first passage and the recaptures remain refused.

<a id="vérifications"></a>

## Verifications

The overall regression passed its 818 tests, divided into four groups.

[Target test](../tests/test_loop_replacements.py) with 14 methods, 16 executions
The programme is based on the following criteria:
sequences generated with seed 20261103 are compared to a model
independent which replaces a value at each iteration and records the
Other cases include verification of address, cleaning,
nested loops, break values, function returns,
the enum variants and the reuse of a pool of two slots.
Three manual executions complete the targeted suite.
replaced at the same iteration display `1` then `11` and their
replacements are destroyed in order `11`, `1`. Un emprunt
provided by `break` after a resume `20`. A result of
function selected between two outputs `break` also displays `20`.

The 14 targeted tests pass under Clang with `-O2` and UBSan without
recovery. ASan remains unavailable on this host according to the minimum probe
of [previous cycle](LOOP_RESULTS_VALIDATION.md).
The two [targeted mutations]](../validation/loop-replacement-mutations.json)
are detected. They omit the C pointer update respectively
and the detachment of the old import.

```sh
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
CRUST_SANITIZE=undefined PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_loop_replacements.py -q
python3 tests/run_loop_replacement_mutations.py
```

The analysis remains conservative, and it refuses incompatible orders, orders, orders, and
already marked transfers that interfere with replacement and
dependencies of a living object towards a generation replaced by the recipient.
The convergence limits remain applicable.
not the validity of all loop programs.
