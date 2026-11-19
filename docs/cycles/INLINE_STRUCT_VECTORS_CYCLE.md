[Français](INLINE_STRUCT_VECTORS_CYCLE-fr.md)

<a id="cycle--structures-stockées-directement-dans-les-cases-des-vecteurs"></a>

# Cycle — Structures stored directly in vector boxes

<a id="règles-et-portée"></a>

## Rules and scope

Application of VE1/VE2, ST17/ST18, T1/T6, B1–B5, G9/G12 and GR1/GR2,
The following are the main indicators of the impact of the change in the economic performance of the Union industry:
seven drafts and the rules of representation/copying have been read. The rest
The overall objective remains open.

`Vector<Point>` stores Point fields in its cells; it is not a
`Vector<A<Point>>`. This first connection concerns leaf structures
Int, including interlocked and empty, inserting a construction or copying
The copies can be released from a block or be
returned by synchronous functions and relays. An independent copy does not
Don't hold the vector pool.

The historical file open-inline-struct-vector.crust also had a reading
implicite `let point=v[0]`, prohibited by ST17. It is preserved with its former
log; the valid program of this cycle uses `copy(v[0])` in
validation/inline-struct-vector.crust. L’ancien refus « allocation Int »
However, Vector's lack of recognition<Point> was highlighted.

<a id="implémentation"></a>

## Implementation

- Registration of nominal vectors, distinct from digital vectors,
  d) borrowing and handling; control of the type of fields in the program.
- Size of the squares calculated on flattened layout. The existing generic runtime
  receives this size and an appropriate alignment; no allocation per element
  n is hidden in the boxes. The temporary construction/copying is cleaned
  After inserting its fields.
- Copy a box to a local structure, with index control and ready
  The results of the evaluation are linked to the results analyses,
  constraints and types, and booking the result in the parent.
- Vector Settings<Point> borrowed/transferred recognized. Returning a copy
  local uses the storage provided by the appellant.
- Vector booking planner keeps the generic path
  placement to execution for regions of structures; optimisation
  The increase in the number of people in the EU is still to be achieved.

No modification of the runtime C or deactivation of its assertions.

<a id="défauts-rencontrés"></a>

## Faults encountered

The first pass exposed the missing reservation of `copy(v[i])` in the
The parent was connected to the existing planner.
failed with a fixed table diagnosis; she now explains the copy
The return from a Vector parameter<Point> also required
communicate its type to the local return planner.

The case of empty structure then detected an invalid size/alignment torque
(size 1, int alignment), rejected by the runtime. It now uses a
size(int) aligned box with a neutral buffer for reading and
scripts, without reading out of empty payload.

The first passes also included test errors: English name
d-index diagnostic, directive placed before fn instead of a block and without its
current rating, too restrictive pattern for C names generated.
were corrected; no acceptance rule was relaxed for testing.

<a id="exécutions"></a>

## Implementation

Eight targeted methods: **10 executions C**, including 8 successes and 2 expected stops
for negative/outside length index; **7 programmes invalides**, each subject to
verify_program and compile_source. Print values are written in the
The generated layout is also tested independently of the compiler.
representational control, complementary to execution.

- Insertion, copying and destruction of the vector before reading the copy.
- Copy received by the parent after the end of the local pool.
- Embedded structures and explicit copy of a variable still usable.
- Two vectors growing in parallel on both fronts, then with
  region notation; re-use of pool after destruction.
- Refusal of an implied copy, missing arrow, of an A<Point> provided to
  a Point box, a drop-in use and a mutation without let mut.
- Shared loan: Push refused before its last use and accepted afterwards.
- Insert by function, copy returned by relay, drop then read.
- Empty structures, growth and re-employment.

Targeted command:

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_inline_struct_vectors -v
```

Targeted final outcome: **8 methods, 4,477 s, code 0**, in
validation/inline-struct-vectors-targeted-fifth.log. The first four logs
are preserved. Native configuration: Clang C11, pthread, Wall/Wextra/Werrar,
UBSan with diagnostic stop. Two terminal stops are expected and tested.

Regression O2/UBSan: **373 methods, 340,917 s, code 1: one error**.
Reproducible selection in validation/inline-struct-vectors-test-selection.txt
and output in validation/inline-struct-vectors-regression.log. The 372 others
methods, including existing models of lifespans and
signatures. The compiler no longer changed after the launch of this pass.

The error concerns the old result test owner of a feature type:
his method required `self: -> Item`but his call provided `p.new()`, donc
A<Item>. It is reproduced on the initial snapshot in
validation/inline-struct-vectors-preexisting-feature-failure.log (code 1),
independent of this lot. H1/H3 and draft 06 do not allow this
The test now retains this program as refused to the
two entries and checks the identity, value and re-use on a structure
The local pool is also refused to the local pool in accordance with the method.
T/A<T> control; therefore, it does not prove a pool life check
through this feature.

Supplement after this fixture correction only:

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_type_features test_inline_struct_vectors -v
```

**30 methods, 16.386 s, code 0**, in
validation/inline-struct-vectors-complement.log. The global pass of 373 n
not presented as a single green run: his only error was explained,
reproduced before modifications and covered by this supplement.
source files checked unchanged during execution. No failure
Unexplained is not left in this selection.

<a id="complément--trois-exemples-précédemment-vérifiés-seulement-à-la-compilation"></a>

### Supplement: three examples previously verified only at compilation

During the regression, the three fixeds already recorded from the previous cycle
were executed with the same harness O0/UBSan:
open-async-vector-result-consumer.crust, open-vector-nominal-reference-payload.crust
and open-async-vector-nominal-reference-payload.crust. Each prints 7 and
destroy Item once; the last two also destroy Point once.
Output: validation/vector-upplemental-native.log, code 0. These three executions
add to the ten targets above; they are not general evidence
nominal references in all containers.

Reproduction :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 - <<'PY'
from pathlib import Path
import test_select_source as harness
case = harness.SelectSourceTests()
for name in ('open-async-vector-result-consumer',
             'open-vector-nominal-reference-payload',
             'open-async-vector-nominal-reference-payload'):
    run = case.run_source(Path('validation', name+'.crust').read_text())
    case.assertEqual(run.stdout, '7\n')
    case.assertEqual(run.stderr.count('=Item\n'), 1)
    if 'nominal' in name:
        case.assertEqual(run.stderr.count('=Point\n'), 1)
    print(name, run.stdout, run.stderr)
PY
```

<a id="limites-et-suite"></a>

## Limitations and follow-up

This cycle does not end VE1–VE6: borrowed/owner fields, moving a
structure named in a box, extraction/replacement/removal/removal results are bankrupt,
borrowings and slices of these boxes, push_new, container returns and integration
Async still has to be connected. The current refusal of these forms is a limit
d
vectors of existing handlers do not prove these forms online.

No new independent model, random campaign, mutation or ASan in
this lot, in accordance with the priority given to implementation and cases
The tests and UBSan are not a general proof of safety.

Reproducibility: initial snapshot /tmp/crust-before-inline-struct-vectors,
patch and fingerprints validation/inline-struct-vectors.patch and
validation/inline-struct-vectors-changes.json, C generated
validation/inline-struct-vectors.c.
