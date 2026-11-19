[Français](LOOP_DEAD_FIELD_VALIDATION-fr.md)

<a id="validation-du-dernier-usage-dun-champ-emprunté-sur-une-reprise"></a>

# Validation of last use of a field borrowed from a cover

This cycle refines the implementation of B2, B3, D4, L2 and V4.
The counter example declares the receiver in a block and the field bearer
The buckle is in the child's block.
is read before the loop, then the receiver is replaced on `continue`.
The old control refused to allow the live bearer to be present even if the
The separate blocks isolate this gap from the
destruction order L3.

The auditor invalidates access that retains a dependency that has become
Unusable when recovery brings together generations of the recipient.
The porter's cleaning inlet remains followed.
The current borrowings still have to be covered by the current reference field.
serve, access that could be restored by an ongoing transfer
and dependencies that the recipient would take to one of its generations
The prototype also retains its refusal to accept orders from the
destruction incompatibles.

[Regression test](../tests/test_loop_replacements.py) for fields
`&Int` and `&mut Int`. Both programs are accepted with the old
value via the holder and then the replacement value via the receiver.
The trace controls the single destruction of the old allocation, the
subsequent cleaning of the bearer and destruction of replacement.
clean the carrier by reset, the other at the exit of the block.
are refused by the auditor and compiler. They still use
the holder after the loop, at the next iteration or via an alias.

The overall regression passed its 819 tests. The 15 targeted tests
passent aussi sous Clang `-O2` and UBSan without recovery.

The trace model of the six replacement generated sequences remains
carried out with seed 20261103.
[mutations](../validation/loop-dead-field-mutations.json) restore the refusal
a field borrowed and replay the two previous mistakes
on the recovery pointer and the old imported access.
detected.

```sh
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
CRUST_SANITIZE=undefined PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_loop_replacements.py -q
python3 tests/run_loop_replacement_mutations.py
```

This validation covers the integrated destroyers.
destroyers who read the fields would require to model these readings
as protective uses, in accordance with L4. ASan remains unavailable
on this host according to the probe of the
[previous cycle](LOOP_RESULTS_VALIDATION.md).
