# Bare type parameters and readable examples

Scope: the requested core grammar/parser change, current source migration and
README formatting. No type-constraint enforcement or ownership rule was changed.

## Implemented

- `#(type: V)` introduces an unconstrained parameter.
- The active corboc parser rejects `#(type: V *)`.
- Usage-site constraints such as `S<V: i64, bool> with { ... }` retain their
  existing syntax; no standalone allowed-type-list declaration was added.
- Current STD declarations, README packages and active compiler fixtures use
  the bare form. The Rust reference and its historical comparison inputs remain
  frozen; their old syntax is not an accepted compatibility form in corboc.
- README examples have separated declaration/impl blocks and methods, expanded
  compact type/function bodies, and spaced comma-separated lists. Source
  packages and README code blocks remain synchronized.

## Focused validation

One successful compiler build was performed on the macOS ARM64 host. The old
seed could not parse the migrated STD on the initial normal-build attempt, so
bootstrap C emission used the seed's previous STD. The rebuilt compiler is
installed alongside the migrated, pinned STD. A full self-reconstruction or
platform matrix was not run.

The focused checks completed:

| Check | Result |
| --- | --- |
| Bare unconstrained annotation, `--ast` | Accepted, status 0 |
| Former star annotation, `--ast` | Rejected, status 7 |
| Bare declaration plus usage-site type list, `--ast` | Accepted, status 0 |
| Complete Reader example | Compiled and ran, printing 42 at O1 with fatal UBSan; no stderr |
| All 33 README source blocks and auxiliary files | Match their current source packages |
| Example reformatting | Code tokens preserved after accounting for the requested star removal |
| Generated references | Coverage and freshness checks passed |
| Pinned runtime resources | Freshness check passed with the rebuilt compiler |

Only the Reader program was executed for this change. The remaining examples
were checked for source correspondence and formatting/token preservation; the
broad compiler and safety suites were intentionally not run.

The STD/grammar source pin is `0e49415`. That local commit records the compatible
source migration; the compiler lock was updated deliberately. Runtime resources
were regenerated from that exact revision, not from a modified dependency cache.

Reproduce the executable check from the language checkout:

```sh
python3 validation/check_documentation.py --corboc ../corboc/build/install/bin/corboc --keep build/bare-type-annotations --only contracts
python3 scripts/stdlib_docs.py --check
```

The compiler checkout retains the three small parser inputs and results in
`build/bare-type-annotations/`. Its latest bootstrap report marks
`self_verified: false`; focused validation is not a general safety proof.
