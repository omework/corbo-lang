[Français](RECURSIVE_OWNED_REPLACEMENT_CYCLE-fr.md)

<a id="remplacement-dun-champ-propriétaire-derrière-des-liens-récursifs"></a>

# Replacement of a proprietary field behind recursive links

<a id="portée"></a>

## Scope

The existing replacement rules evaluate the new allowance before
to destroy the old, keep the source of the new value and demand
The transfer does not move the target allocated.
This cycle checks their application to an A<Int> field of a Leaf structure,
She herself held after two A<Node> bonds of a recursive enum.

This composition already worked: no change in the compiler was made
the missing test is added; it does not justify reworking
the replacement mechanism.

<a id="cas-exécutés"></a>

## Cases implemented

One method in tests/test_recursive_owned_replacement.py, two programs
native valids (synchronous call and call from a task), two invalids
both compiler entries.

The helper replaces Leaf.item from another pool. Deep reading produces
9, the old pool of capacity one accepts 11, then the destruction of the graph releases
the new slot that receives 12. The async state suspends after replacement.
old and new target is destroyed once. The pool provided to the helper in
A child block, shorter than the carrier, is refused in both variants.

The first trace assertions wrongly assumed the field name `item`.
Runtime keeps the name of the allowance `first` and appoints the new `champ`.
The oracle now checks the number of destructions of each single value,
The exit and re-use of capacity was a major factor in the development of the
The second journal has a regex failure (`surviv`
does not correspond to `survit`), corrected without changing semantic expectations.

| Journal in validation/ | Result |
| --- | --- |
| recursive-owned-replacement-first-o0.log | Trace wording failures only |
| recursive-owned-replacement-second-o0.log | Correct refusals, regex for misdiagnosis |
| recursive-owned-replacement-final-o0.log | Success, code 0 |
| recursive-owned-replacement-final-o2.log | Success, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_recursive_owned_replacement -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_recursive_owned_replacement -v
```

Both levels compile C11/pthread, error warnings, fatal UBSan.
No compiler changes since regression of 97 cycle methods
RECURSIVE_MUTABLE_RESULTS_CYCLE.md; this regression is not restarted.
No new independent model or adversary campaign or mutations.

## Limites

Replacement of terminal field A<Int> in constructed graphs, not
replacement of a complete A<Node> link or validation of all forms of
The guarantees are not general evidence.
The objective of global integration and its arbitrations remain open.
