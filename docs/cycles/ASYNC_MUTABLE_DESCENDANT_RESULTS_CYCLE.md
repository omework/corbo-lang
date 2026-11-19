[Français](ASYNC_MUTABLE_DESCENDANT_RESULTS_CYCLE-fr.md)

<a id="retours-mutables-depuis-des-descendants-possédés"></a>

# Mutable returns from possessed descendants

<a id="périmètre"></a>

## Perimeter

Existing rules for mutable borrowing, last use, return
child → parent and AS16 apply to the result Int obtained in a
Downhill A<T>. The result reserves the target and the field access capacity.
The holder may be used again after the last use of the result.
No normative rules are amended.

The case recorded is
`validation/open-async-replaced-mutable-result.crust`. Before this lot, he was
refused in the analysis of the synchronous function which returned the loan:
"unsustainable borrowed target in the parent scope."

## Corrections

A re-borrowing of a possessed descendant now retains a projection of the
paramètre porteur, au lieu d'être décrit par les candidats d'allocation du
He keeps his graph and his way to the
The contract solver acknowledges this passage by
a field owned and reserves the corresponding capacity.

When creating a task modifying a possessed field, field effects
are prepared on the graph proposed after replacement. They are no longer
The exclusivity control had detected two different types of equipment.
artificial mutable loans to the same target due to this old routing;
This control remains unchanged.

The projection of the result through the graph also keeps the reservation
The first test refused showed a gap between the two
entries: check accepted premature reading via an auxiliary, while
The generation refused to accept it by walking through his body.
now this case since the capacity of the contract.

Finally, internal roads `.child/.view` and `.child/view` are standardized
In the same way by following up async loans, so that replacement of the
descendant is not considered disjunct from his returned reborrowing.

<a id="cas-exécutés"></a>

## Cases implemented

Five targeted methods include six native executions and nine programmes
In the case of disabled persons tested at both entrances, 18 refusal checks:

- Saved example and failed launch injected.
- Join, read/change via result and re-use of the holder after
  last use; premature reading of the wearer or writing of the refused target.
- Direct wait, drop of the bearer and direct replacement of his descendant refused
  as long as the result remains in use.
- Return from a synchronous function, with the same last-use border.
- Relais async then Select, conservation of reservations after drop of Select.

The expected values are 20 after mutation by result and 30 after
destruction of the carrier and further mutation of the target. Failed launch
does not run the body and the program only displays 30.

Targeted O0: five methods, 2,769 s, code 0; journal
`validation/async-mutable-descendant-results-relay-o0.log`.
The O2 regression passes 110 methods in 89,397 s, code 0 ; journal
`validation/async-mutable-descendant-results-regression-o2.log`. It includes the
Five methods targeted at the end state. Native executions use Clang
C11, pthread and UBSan without recovery. Models already included in the suites
linked have been replayed; no new independent model is claimed.

## Limites

The lot exercises &mut Int in structures with descendants followed. It does not prove
not all graph alternatives, recursive enums or other
Target types. Metadata remains conservative for alternatives
Security guarantees are not limited to these tests.
No new adversary campaign or deployments; independent audit
remains deferred according to user's instructions.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_async_mutable_descendant_results -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_mutable_descendant_results test_async_replaced_borrow_results test_async_owned_borrow_writes test_async_owned_field_writes test_mutable_field_completion test_borrowed_field_completion test_async_enum_match test_async_consuming_enum_match test_async_enum_suspension_fields test_nested_field_wrappers test_nested_field_choices -v
```

Snapshot : `/tmp/crust-before-async-mutable-descendant-results/`.
The three differences are archived under
`validation/async-mutable-descendant-results-{results,crust,async_lowering}.py.patch`.
The intermediate newspapers are kept, including the first passage which
exposes the check/generation gap.
