# Declaration publication/annotation order: resolved decision

The initial contradiction below was resolved by the user: annotations always
precede pub. The grammar and declaration oracle now follow that uniform order.

The written productions at CORE_GRAMMAR.ebnf:15 and :27 derive public functions
as `pub` followed by function contracts. Other declaration alternatives permit
contracts before `pub` for structs/enums. Method productions put contracts before
`pub`. The reference parser consistently reads contracts first, then `pub`, as do
the existing annotated public STD functions.

The independent LALRPOP oracle at
rust_frontend/tests/oracle/declaration_order.lalrpop now translates the approved
minimal declaration subset with contracts before pub. It recognizes functions, structs, enums
and methods with bare type contracts, empty signatures and empty bodies; it is
not claimed to cover complete declarations or full module grammar.

## Executed comparison

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --features parser-oracle \
  --test parser_lalrpop declaration_annotation_order -- --nocapture
```

Grammar generation succeeds without unresolved conflicts for this subset. The
initial comparison failed on 11 cases with four acceptance differences. After the
approved grammar/oracle update it passes: 11 cases, zero differences. The latest
comparison is recorded in the fixed-path artifact
rust_frontend/target/parser-lalrpop-declaration-order.json.

Historical observations before the decision:

| Context/source | Previous written grammar oracle | Rust parser |
| --- | --- | --- |
| `#(type: T) pub fn f() {}` | Reject | Accept |
| `pub #(type: T) fn f() {}` | Accept | Reject |
| `pub #(type: T) struct S {}` | Accept | Reject |
| `pub #(type: T) enum E { V; }` | Accept | Reject |

The other seven examples agree, including ordinary declarations and the method
annotation order. These four witnesses have one underlying design inconsistency:
there is no uniform normative order across declaration categories. Neither the
parser nor the oracle is automatically authoritative. Before the user decision, no publication-order rule, STD source or parser
behavior was changed to make this comparison agree. The subsequent approved
grammar change is recorded below.

## Applied decision and remaining work

Annotations always precede pub for every declaration category. The grammar moved
optional visibility into the annotation-bearing productions, removing the
contradictory public-first alternatives. The parser already followed this order;
no STD migration or parser widening was needed. The declaration oracle and all
106 STD files pass after the update.

The full production audit remains unfinished. Its next genuine syntax ambiguity
is recorded in RUST_PARSER_BLOCK_OPERATOR.md; no complete-parser claim is made.
