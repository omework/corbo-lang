[Français](NO_IMPLICIT_PROMOTION-fr.md)

<a id="décision--aucune-promotion-implicite-dune-cible-empruntée"></a>

# Decision: No implicit promotion of a borrowed target

Explicit decision of the user, recorded on November 2, 2026.

D1 in [LANGUAGE_RULES.md](LANGUAGE_RULES.md) replace previous proposal
automatic transfer of dependencies. Transferring an object does not transfer
its targets borrowed and does not prolong their lives. At every child border →
parent, all targets must already be durable enough in the destination
or one of its ancestors; otherwise, the transfer is refused. This remains true when
The pool is sustainable and in successive transfers.
implicit is prohibited, not a deferred functionality.

```rust
fn wrong(data_pool: &mut Pool<Int>, views: &mut Pool<View>) -> <- View {
    let mut data = new(data_pool) Int(42);
    let mut view = new(views) View.Item { data: &data };
    return <- view; // Refusé : data appartient à l'enfant.
}
```

The compiler already refuses this case. No implementation file, runtime or
The contract is not affected by this documentary decision.
to follow targets to protect their uses, without promoting them.

<a id="réexamen-et-validation"></a>

## Review and validation

The 66 rule identifiers are stored in the matrix.
partially covered for &Int fields; general graphs remain
The dependencies I1, T3/T5, B4c, D3/D4,
A2/A3, L2/L3 and P8/P9 were reconsidered.
transfer, borrowing, pool or destruction is not changed.

Regressions: `test_borrowed_returns`, `test_reference_fields`,
`test_scope_exit` and `test_reset_transitions`, standard and UBSan. They cover
already sustainable targets accepted, local targets refused, borders
successive, drop/reset and telescope outputs. They include models
12 valid cases, 12 invalids) and border roads
The number of fields is 19 valid, 13 invalid.
match the compiler: the decision retains the refusals already tested.

The last historical global suite was 605 standard tests and UBSan;
it is not presented as being re-executed for this documentary modification.
The optimized C mutations and campaigns of the previous cycle remain historical,
The targeted validation does not constitute a new execution here.
not formal evidence or exhaustive exploration of the graphs.

Performance on the unchanged code:

| Configuration | Result |
| --- | --- |
| Standard, four targeted modules | 85 tests, OK, 73,227 s |
| `CRUST_SANITIZE=undefined`, same modules | 85 tests, OK, 72,920 s |

The effects on other rules were examined in the matrix; the
Unimplemented features remain unverified. Targeted controls
are not presented as a new execution of the entire overall suite.
The [structured results]](../validation/no-implicit-promotion.json) conservent
the controls, limits and reference to the historical baseline.
