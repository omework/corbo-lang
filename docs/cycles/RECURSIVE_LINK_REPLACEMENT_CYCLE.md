[Français](RECURSIVE_LINK_REPLACEMENT_CYCLE-fr.md)

<a id="remplacement-dun-lien-propriétaire-récursif-complet"></a>

# Replacement of a complete recursive owner link

<a id="règles-et-modification"></a>

## Rules and amendments

Application of the rules for fields A<T>, borrowings,
The new allowance is assessed before the replacement and cleaning.
destruction of the old subtree; its pool must survive the bearer.
normative change, no copy of the contents of the displaced subtree.

The case alternates Node.Link { next: A<Link> } and Link { node: A<Node> }.
A helper replaces link.node with a new Node.End, destroying the old Node.Link
The writing was already implemented. The reading filter of the
match refusait ensuite `let child = &*link.node` and prevented the
The new sub-tree now transmits the type of this projection to the
General control, which checks the mode and the loans.
a precise diagnosis. A transferable loan through a shared carrier remains
refused.

<a id="cas-ciblés"></a>

## Targeted cases

Two methods in tests/test_recursive_link_replacement.py: two executions
The first is the first time that the programme has been completed.

- Subtree Replacement, reading the new value 9, destruction
  the five former allowances appointed.
- Reuse of a Node and Link slot before root destruction,
  then re-use the pool recipient capacity one with value 12.
- Same operation called from a task, with yield after replacement.
- Pool recipient created in a child block refused for both paths.
- Transferable borrowing from the readable field, and non-existent field,
  refused by both entrances.

<a id="résultats-exécutés"></a>

## Implemented

| Journal in validation/ | Result |
| --- | --- |
| recursive-link-replacement-first-o0.log | Two sub-cases refused by match filter |
| recursive-link-replacement-second-o0.log | One method, 1,036 s, code 0 |
| recursive-link-replacement-third-o0.log | Replacement pass; generic diagnosis for non-existent field |
| recursive-link-replacement-final-o0.log | Two methods, 0.916 s, code 0 |

Regression completed: 49 methods in 30.432 s, code 0, in
validation/recursive-link-replacement-regression-o2.log.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_recursive_link_replacement -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_recursive_link_replacement test_recursive_owned_replacement test_recursive_mutable_results test_recursive_borrow_results test_recursive_borrow_projections test_shared_match_field_reads test_async_owned_borrow_writes test_async_owned_nominal_writes test_async_enum_nominal test_mutable_match test_mutable_match_function_return -v
```

Targeted harnesses/async use C11/pthread, error warnings, fatal UBSan,
O0 then O2. The old synchronous harness activate UBSan without adding O2 and
use legacy-reset for their historical scenarios. No new model
the first two cases remain in the
regression selection.

## Limites

Cover of this finished substitution and the indicated paths.
new products in recursive job factory contracts remain to be
verify; neither this cycle nor the precedents prove a general security.
Integration of all features and open public arbitrations
are not declared completed.

Snapshot : /tmp/crust-before-recursive-link-replacement/.
Diff : validation/recursive-link-replacement-crust.py.patch.
