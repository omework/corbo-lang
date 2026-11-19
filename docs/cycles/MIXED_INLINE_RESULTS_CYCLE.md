[Français](MIXED_INLINE_RESULTS_CYCLE-fr.md)

<a id="résultats-mêlant-références-entières-et-intérieures"></a>

# Results combining whole and inner references

<a id="périmètre"></a>

## Perimeter

Connection of ST7–ST14 with existing branch-specific performance rules:
a reference may refer to an entire object or substructure of the same type.
The split/mutable mode remains the same between branches.
No life-span promotion,
additional allocation or normative change.

<a id="implémentation"></a>

## Implementation

When a possibility is inside, result C uses the descriptor
The other branches convert their entire pointer to the existing view.
a descriptor of the same target, without moving its storage.
is selected by types C; it evaluates the value only once.

The connection concerns explicit and terminal feedback of functions,
the results of if and match, and loop outs by break. Accesses,
copies and parameters take into account all the referents of a link,
instead of choosing their representation from the first only.
The loading of a stored mutable field also uses the descriptor when
His targets mix both representations.

Diagnostic operation `address` keeps the previous target address
the entire storage and the storage inside for a substructure.
Therefore, the representational address does not change that observable address.

<a id="cas-exécutés"></a>

## Cases implemented

`tests/test_mixed_inline_results.py` : seven methods, twelve programmes admitted
and 11 invalid programmes refused by `verify_program` and
`compile_source`.

- Relay and Relay: both branches executed, address and
  The value compared, drop of each of the possible targets rejected before the last use.
- If returning a mutable loan: writing in the right target for both
  branches and competing access denied.
- Two break outputs of different representations, with expected value
  for each branch.
- Match with one branch returns an entire reference and the other one a view.
- Copy of the target value, storage of the reference in a structure,
  extraction and destruction of the bearer.
- Mutable result of a function, storage in a Writer, reborrowing returned
  then transition to a transfer function; destruction and access to competing denied.
- Branch returning a view of a local allowance too short refused.

<a id="exécutions-et-corrections"></a>

## Implementation and corrections

Clang C11/pthread, fatal UBSan, warnings as errors; O0 and O2.
Expectations are about values, observed identity and refusals, but
only on the success of the compilation.

| Passage | Result | Journal in `validation/` |
| --- | --- | --- |
| Initial O0 | 5 methods, 2 sub-case failures, 3.736 s, code 1 | `mixed-inline-results-o0-first.log` |
| Second O0 | 5 methods, 4,542 s, code 0 | `mixed-inline-results-o0-second.log` |
| Third O0 | 7 methods, 5,489 s, code 0 | `mixed-inline-results-o0-third.log` |
| Match historique O2 | 6 methods, 5,794 s, code 0 | `mixed-inline-results-match-o2.log` |
| Regression O2 | 98 methods, 62,352 s, code 0 | `mixed-inline-results-regression-o2.log` |
| Final O2 | 13 methods, 10.060 s, code 0 | `mixed-inline-results-final-o2.log` |

The first passage revealed a bad choice of representation during a copy:
the liaison had a first whole referent and another interior, but the backend
read the descriptor as a Cell*. Representation is now chosen
The expectations of the tests remained unchanged.
After the regression, the choice of the type of anticipated returns was simplified in
a local C-type def to the generated function, without text substitution in its
The final passage takes up the seven targeted methods and the six methods
match history on this version.

The bound regression takes over the view modules, stored references, constructions
contained, reborrowed, mixed async structures and owner replacements.
The six historical methods target typical match returns, returns
The newspapers give the full names.

## Limites

The lot covers the synchronous paths indicated; catches and results async
The common choice of representation does not prove that the view is still to be connected.
the coverage of all recursive graphs and combinations of
No new campaign of mutations, of adversary generation
ASan and a second C compiler were not executed.
These tests are not a general proof of safety.

Diffs : `validation/mixed-inline-results-{crust,structure_views}.py.patch`,
compared to `/tmp/crust-before-mixed-inline-results/`.
