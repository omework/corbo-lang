# Grammar-derived parser coverage

Historical executed snapshot: the results below precede the later structural-
contract OR grammar extension. Parser/oracle support for that addition is pending.

Scope: core grammar and syntax parsing only. No semantic resolution, rule
verification, target evaluation, STD changes or code generation.

## Implemented mechanism

`rust_frontend/tests/support/ebnf.rs` reads the actual `CORE_GRAMMAR.ebnf`:
terminals, references, sequences, alternatives, optionals, repetitions and groups.
It rejects duplicate productions and identifies undefined references. Lexical
symbols described in the grammar comments have explicit samples, rather than
invented syntax productions.

The generator computes finite minimal derivations and program contexts through
the production-reference graph. It constructs a minimal complete program for
all reachable productions, then forces each local alternative, optional
absence/presence, and repetition count 0/1/2. Cases and offsets are regenerated
from the grammar, not maintained as a handwritten snippet catalog. Terminal
fragments for tuple indices and foreign operands are rendered without internal
spaces. Foreign cases select a derivation context inside `@unchecked`, as the
existing normative comment requires. These contextual adjustments are explicit
in the generator and do not depend on parser acceptance.

A separate chart recognizer mechanically expands the EBNF to BNF and performs
prediction, scanning and completion. It recognizes terminal-fragment sequences,
not the Rust AST or lexer output. It does not reuse the derivation algorithm or
production parser. A small independent fixture checks nullable left recursion
and rejection. The recognizer uses the same specification and lexical samples,
so this is algorithmic independence, not an independent language specification.

`tests/grammar_coverage.rs` checks each derived program against the recognizer,
then lexes/parses the rendered source. It preserves source/tokens and reuses the
same AST integrity audit as the entire-STD suite. For negative neighbors, it
removes individual structural terminals from minimal witnesses; the recognizer
classifies the result *before* the production parser runs. Foreign-source
mutation is excluded because its opaque contents are not Corbo grammar tokens.

## Executed results

```sh
cargo test --offline --manifest-path rust_frontend/Cargo.toml \
  --target-dir rust_frontend/target --features parser-oracle \
  --test grammar_coverage --test parser_lalrpop \
  --test parser_stage --test parser_stdlib -- --nocapture
```

- 160 productions, all reachable from `programme`, after removal of three
  unused definitions approved by the user.
- 843 derived cases: 160 baseline witnesses and 683 local EBNF feature choices.
  These represent **443 distinct source programs**; repeated witnesses retain
  their separate production/feature mappings.
- All generated programs accepted with preserved source/tokens and valid AST
  spans, child links and reachability.
- 559 terminal-deletion comparisons: 557 rejected by both recognizer and parser,
  two still valid and accepted by both. No mismatch.
- Existing independent LALRPOP comparisons: 307 expressions, 10 block boundaries,
  11 declaration-order cases and 7 carrier contracts, zero differences.
- New range-call oracle: six cases, including malformed ranges, zero differences
  in acceptance and normalized AST structure.
- All 16 stage regressions pass. Broader corpus: 293 accepted / 346, with the
  same 53 previously reviewed syntax refusals.
- All 106 STD files still parse unchanged: 145,730 original tokens and 91,901
  reachable AST nodes.

The reusable JSON output is `rust_frontend/target/parser-grammar-coverage.json`.
It contains the grammar fingerprint, every production, each feature's grammar
byte offset, generated source, parser result and mutated source/verdict pair.
LALRPOP range evidence is `target/parser-lalrpop-range-call.json`.

## Differences investigated and corrected

The initial 49 differences comprised generator-context/rendering problems and a
real parser omission. Foreign cases had incorrectly selected the shorter path
without unchecked enclosure; `${name}` and repeated tuple-index digits had
incorrectly been separated by whitespace. Those were generator errors, not
language changes.

The remaining parser omission was the written `.try_slice(plage)` suffix.
`postfix` now selects a Range argument when `..` occurs in that call. Ordinary
arguments still use the ordinary call grammar. No receiver type/name resolution
is performed. The independent range-call LALRPOP subset compares the generated
Call → Projection / Range structure against the Rust AST.

## What remains unestablished

The initial inventory had 163 productions, including three unreachable definitions:
`champs_types`, `champ_type` and `place`. The user requested their removal.
They have been deleted: struct fields already use `champ_definition`, and
assignments already use `assignment_left_expression` directly. No accepted
program or parser behavior changes. All remaining 160 productions are reachable.
The regression now fails if a future edit introduces an unreachable production.

This is bounded **local production/feature coverage**, not exhaustive combination
or recursion coverage. Each lexical class has a representative sample here;
the lexer/Logos suite separately exercises lexical boundaries. The chart oracle
recognizes grammar fragments and does not independently validate lexical
classification, every prose restriction, all source-token regroupings, or
semantic properties.

AST integrity is not AST correctness. Independent expected AST structures remain
limited to the stated LALRPOP subsets. A full AST oracle, arbitrary-source grammar
parity, all contextual restrictions, retained historical grammar forms and the
broader specification audit remain open. No grammar production was relaxed or
STD source edited to obtain these results.
