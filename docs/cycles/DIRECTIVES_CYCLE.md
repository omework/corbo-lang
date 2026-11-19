[Français](DIRECTIVES_CYCLE-fr.md)

<a id="cycle--directives-catégorisées-brouillon-06"></a>

# Cycle — Categorized guidelines (Brouillon 06)

<a id="décision-appliquée"></a>

## Decision implemented

The Regional Directive now reads:
`#(directive, stack_region_max_size=1M)`. The category and its comma are
compulsory; spaces around `=` The parser is not optional.
does not retain a silent alias for the old shape without category.
Categories `type` and `types` do not replace `type feature`.

G6, P2 and the normative examples of channels were updated before the
validation. Historical examples of reports and drafts of
The design is not rewritten. Active testing programs use
the validated syntax; the old form remains as explicitly refused case.

<a id="invariants-et-interactions-examinés"></a>

## Invariants and interactions examined

This change does not change the placement, size or life of the person
d) a region. The parser transmits the same whole value to blocks and blocks.
The controls concern the lexical heritage, the
overload in a child, restoration at his exit and absence
d) dynamic legacy in a function called.
String and Vector, parent/child transfers, match branches,
pre-construction reservation, retained addresses, limits
After transfer, re-used slots and cleaning of the possessed elements.

The numerical model of tests uses independent decimal constants
parser: 1048576 and 1073741824. The multiple binarys are always a
The model is not a standard-setting cycle for the
units. Numbers at the limit and immediately beyond check the terminal
of representation without trying to actually reserve exabytes.

<a id="preuves-exécutées"></a>

## Evidence

- `PYTHONPATH=tests:. python3 -m unittest test_growth_annotations -v` :
  4 successful methods; 13 programs admitted by compilation and
  26 configurations refused. Refusals cover category, separator,
  unknown/duplicated parameter, location, unit, zero, negative and overflow.
- `/tmp/crust_directive_cycle.py -O0` : 20 successful methods in 15,231 sec.
- `/tmp/crust_directive_cycle.py -O2` : the same 20 successful methods in
  16.575 sec. The script selects the methods containing the directive in
  `test_foundation_rules` and `test_owned_results`, plus `test_growth_annotations`.
  It only changes the level of optimization in native commands.
  The C is compiled with `-fsanitize=undefined -fno-sanitize-recover=all`.
- Journaux : `/tmp/crust-directive-O0.log` and `/tmp/crust-directive-O2.log`.
- Python compilation of successful modified files.

### Mutations

Three mutations of `crust.py` were executed in temporary copies,
with the original tests of `test_growth_annotations` :

1. Accepting the absence of category: detected by a historical program
   Wrongly accepted.
2. Accept the absence of comma: detected by a poorly trained program
   Wrongly accepted.
3. Interpret M/G with decimal factors: detected by limits
   The results of the survey were based on the results of the survey.

All cause test assertions, without error of loading or
syntaxe Python. Script : `/tmp/crust_directive_mutations.py` ; journal :
`/tmp/crust-directive-mutations.log`These three targeted errors do not measure
not a general compiler cover.

<a id="régression-et-migration-des-anciennes-fixtures"></a>

## Regression and migration of old fixtures

The extended regression exhibited pre-U1 fixations that created
an unused owner, sometimes crushed or destroyed by a resettling without
The compiler now refuses these programs before the
The test was designed to perform the behaviour.
by readings `print` before cleaning or replacement, with exits
The assertions of destruction and re-use are clearly stated.
The negative cases use other owners to isolate
the diagnosis of the old invalid access or incompatible pool type.
The historical profile `allow_legacy_reset` remains explicit in these tests.

Initial execution:
`PYTHONPATH=tests:. python3 -m unittest test_crust test_arguments test_if_expressions test_growth_runtime test_owner_usage -v` :
215 methods in 116,554 seconds, with 4 failures of assertion and 27 errors (several
The following are the main reasons for this:
`/tmp/crust-directive-regression.log`.

After fixing:
`CRUST_SANITIZE=undefined PYTHONPATH=tests:. python3 -m unittest test_crust test_arguments test_if_expressions -v` :
181 successful methods in 80.164 s, fatal UBSan activated for C programs.
Journal : `/tmp/crust-directive-fixtures-final.log`.
The 22 methods of `test_growth_runtime` and the 12 of `test_owner_usage`
all had already succeeded in the initial execution; their code and the
compiler did not change between these two executions.
is exercised at O0/O2 with fatal UBSan by its native helper; U1 cases use
the O2/UBSan helper. The independent U1 model with 64 configurations and models
The growth/slots modules were re-executed.
Thus the 215 regression methods have proof of success on the state
The final report, distributed between these two newspapers, is not a single passage.
The number of methods is not the same as the number of methods used in the repository.
number of programs: some tests generate multiple configurations.

<a id="limites-et-suite"></a>

## Limitations and follow-up

This cycle does not end draft 06.
`type feature Tracer { fn trace(&self); } fn main() {}` remains refused to
parseur (`attendu '=', reçu 'feature'`Declaration, structural constraints,
static resolution and contracts of resolved methods still need to be implemented.

An annotated block in an async function is also refused:

```rust
async fn f() -> Int {
    #(directive, stack_region_max_size=1M) { yield; }
    return 1;
}
fn main() { let t = f(); drop(-> t); }
```

Diagnosis observed: `Annotation of region not supported in this block
The support of the directive in the parser is therefore not a support
The point remains open with the async lot.
No formal evidence, no new ASan/Tsan passage and no exploration
The comprehensive compositions of rules are not claimed.
remains active, with storage gaps and async decisions still open.


Further addition: [TYPE_FEATURES_CYCLE.md](TYPE_FEATURES_CYCLE.md) integrity
the declaration and a first static resolution of the features.
syntactic `type feature` The historical state of the country is described above.
The catalogue is no longer a current gap.
the detailed interactions in the new report remain open.
