[Français](ANCESTOR_JOIN_VALIDATION-fr.md)

<a id="validation-des-remplacements-dun-receveur-ancêtre"></a>

# Validation of an ancestor recipient replacements

This cycle implements the junctions of `if` for the rules already adopted
T7, T9, T11, V4 and L3. Backend C writes the actual pointer in a
the temporary junction at the end of each branch that continues.
combines this temporary with a single cleaning entrance and brings together the
sources, origins and dependencies.
the candidate occupied on each path.
the receipt remains refused. The contracts of function follow the changes
variables visible outside the block and isolate the statements that
masquent.

The case `a ->; r = <- a;` highlighted a double listing of
the allowance when it was returned to another recipient of its scope
the original registration. The reception now withdraws the previous registration before
After the junction, the old guard is disarmed.
On the way that transferred his cleaning.

The contract does not keep the history of a candidate destroyed on the
and, without this distinction, a reset in this
the branch wrongly denied access to the candidate retained on the other
branch. The masking of a name records the external value at the point
after any replacement already made.

Targeted controls check both paths of replacement
conditional, the address selected, destruction exactly once,
direct reset or after a call, separate pools, name masks,
the exclusion of early return, the last use of borrowings, the order of
destruction and destruction `if` of which the recipient is local to an iteration.
independent compares the trace of six programs generated to that of a list
of inversely driven receptions, with seed 20261103.

The overall regression passed its 804 tests in four groups.
The 15 targeted tests are performed with Clang 20.1.3. `-O2` and UBSan without
Recovery. Both targeted mutations are detected.

[Results of mutations](../validation/ancestor-join-mutations.json).
Keeping the old guard triggers a second cleaning on a transfer
from a brother to the receiver. Omitting a provenance was not detected by
the only return of function scenario, as the contract retains both
a neighbour who resets each pool directly after the
`if` Now detects omission.

```sh
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
CRUST_SANITIZE=undefined PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_ancestor_join.py -q
python3 tests/run_ancestor_join_mutations.py
```

The auditor still refuses junctions where a branch leaves the
recipient unavailable, where a result of the `if` keeps a loan from a
identity that the junction must replace, or where destruction orders
The following link is declared before the date of entry into force of the
loop and replaced through its outputs or covers remains at
The analysis of the effects and sources is conservative and
does not establish any general proof. ASan remains unavailable on this host,
as noted on the minimum programme of the
[previous cycle](LOOP_RESULTS_VALIDATION.md).
