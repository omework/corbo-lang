[Français](SHARED_MATCH_FIELD_READS_CYCLE-fr.md)

<a id="lectures-de-champs-dans-un-match-partagé"></a>

# Field readings in a shared match

The case already recorded in `validation/open-shared-enum-descendant-read.crust`
was refused by a syntactic filter of the match: he recognized `*nom`, mais
not `*nom.champ`. The F2 rules and the ordinary rules of reading and borrowing
No normative rules are amended.

The filter now recognizes field de-reference.
intermediates use the same predicate as the final expression, including
for arithmetic calculations. The normal verifier remains in charge of the type,
the existence of the scope and validity of references.

Three targeted methods are increasing to O0 in 1.622 seconds, code 0.
programs: direct reading, intermediate variable, calculation, then use
Int result after destruction of the bearer and its target. A field does not exist
remains refused by verify_program and compile_source. Journal:
`validation/shared-match-field-reads-o0.log`. Initial refusal of both entries
is kept in `validation/shared-match-field-reads-before.log`.

The regression directly related to O2 passes 64 methods in 28,099 s, process
completed with code 0. It covers borrowed fields, mutable matches and
their calls, async consumer matches and the suspended effects of enums.
Journal : `validation/shared-match-field-reads-regression-o2.log`.

Targeted native executions use Clang C11, pthread and UBSan without
Recovery. This pass concerns Int readings already supported;
it does not generalize all expressions and signatures of functions in
no adversarial campaign or mutations have been added.

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_shared_match_field_reads -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_shared_match_field_reads test_reference_fields test_mutable_match test_mutable_match_calls test_async_consuming_enum_match test_async_enum_suspension_fields -v
```

Snapshot : `/tmp/crust-before-shared-match-field-reads/`.
Patch : `validation/shared-match-field-reads-crust.py.patch`.
