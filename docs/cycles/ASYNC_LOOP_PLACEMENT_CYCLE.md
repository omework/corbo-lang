[Français](ASYNC_LOOP_PLACEMENT_CYCLE-fr.md)

<a id="provenances-des-structures-locales-après-les-boucles-async"></a>

# Source of local structures after async loops

<a id="règles-et-changement"></a>

## Rules and change

This lot applies T3/T5/T6, V4/V5, L1/L2/L7, B1/B2 and AS9/AS12,
and drafts 03 and 05. No normative rules are amended.

The programme retained in
`validation/open-async-local-loop-updated-parent-result.crust` is now
accepted and executed: it displays 1, 2, and then 3. His old refusal was a limit
implementation, not a language ban.

`async_local_placement.py` now calculates a fixed point of producers
The states of normal covers and of the
`continue` the next iteration; the `break` and the test of
`while` The test shall keep the path without any further delay.
The interlocked loops have their own exits and covers.
Intermediate telescopes propagate assignments and outputs.

Producers are building identities in the AST: their union
is finished. An unknown provenance remains unknown, distinct from a whole
The calculation uses the contracts of the functions, without reanalyzing their
Body. It also applies to result loops and assignment plan
to existing recipients.

This plan reserves parent storage before construction, without moving the
objects after initialization. Owner fields keep their own
pools; no target borrowed is promoted. The usual verifier controls
The code of the runtime is unchanged.

<a id="preuves-exécutées"></a>

## Evidence

`tests/test_async_loop_placement.py` contains seven methods:

- The case recorded with zero, one, two and five iterations.
- Outings by `break` after `continue`, with `while` and `loop`.
- Embedded loops and telescopes.
- A reading taken before replacement allowed, then its displacement after
  replacement refused; assignment from variable without move refused.
- A structure with a proprietary field whose pool is acceptable; the
  same source in the refused child block.
- A probe of the generated C: all versions occupy the parent source,
  the new cell differs from the old one still alive during its
  construction, the last object keeps its address after exiting the block,
  Then its storage is cleaned. Four destructions are expected.
- A three-producer propagation model: a relay chain
  requires several passages and must return to the three origins.
  The model must be different from the one used in the case of a given group.
  test the placement analysis, not the syntax validity of a Crust program.

The final O0 pass was achieved in 5,211 s; the final O2 baseline succeeded in
6.803 s. The tests consist of ten C-executions, including the probe, and three
invalid programs controlled by both steps.
Clang C11, pthread, Wall/Wextra/Werrar, Wno-unused-function and fatal UBSan.
The levels of optimization are explicitly defined by `CRUST_TEST_OPT`.
Journaux : `validation/async-loop-placement-final-o0.log` and
`validation/async-loop-placement-mutations-final-o2.log`.

The previous parental placement suite passes its fourteen tests to O0,
and then O2 in the previous mutation campaign.
proprietary synchronous calls pass separately to O2 in 13,778 seconds.
The extended selection performs 95 tests successfully in 123.130 s, but its
command fails for additional module loading error
(96 entries in total), detailed below.
108 separate regression tests were passed on the final code.
The initial log is not presented as a successful order:
`validation/async-loop-placement-regression-o2.log`. The corrected follow-up is
in `validation/async-loop-placement-sync-regression-o2.log`.
All the processes mentioned are completed and their results have been recovered.

<a id="mutations-et-essais-initiaux"></a>

## Initial mutations and tests

The five errors of `tests/run_async_loop_placement_mutations.py` are detected:
one passage, forgets the cover continues, forgets the break outs, forgets
and the unseen provenances were eliminated.
The oracles are not modified with the code tested. Some detections are
refusals of valid programs, others differences in the static model;
they are not presented as executed memory corruptions.

The previous eight mutations are also detected in the
`validation/async-loop-placement-previous-mutations-o2.log` ; their basic
14 tests passed in 16.975 seconds.
oblivion of the fields pools and the closure of the stacks.

Inconclusive trials remain archived:

- `parent-o0.log` : wrong compilation option (`0` for `-O0`),
  corrected in `parent-corrected-o0.log` no safety result is derived from this.
- `initial-o0.log` : fixture using the reserved word `pool` comme variable,
  and incorrect refusal waiting for a fresh manufacturer call without arrow.
  The final invalid neighbour moves an existing variable without an arrow.
- `corrected-o0.log` : fixture reusing the name `n` in a scope where the
  prototype forbids his masking; the second name is corrected in `next`.
- `mutations-o2.log` : the first mutation of unknown origin triggered
  an exception Python; result classified as inconclusive. The final mutation
  removes unknowns from the union and is detected by an assertion of the model.
- The first regression command contains a non-existent module name,
  `test_async_sync_owned_calls`. The real sequel `test_sync_owned_calls` is
  executed separately; the initial import error remains in the log.

`py_compile` successfully. The module diff is kept in
`validation/async-loop-placement-async_local_placement.py.patch`, with snapshot
initial in `/tmp/crust-before-async-loop-placement/`.

<a id="limites-et-suite"></a>

## Limitations and follow-up

This batch does not generalize the graphs of async states types.
local structures with child tasks, their exit from the state and the
restitution after replacement of a proprietary field remain open.
The fixed point conservatively unites the paths; it does not deduce their
correlations and does not seek an optimal memory placement.

The model and probes are finished. Tests performed do not prove safety
General. No new ASan or TSan results are claimed. The objective
The full integration of the seven drafts remains open.
