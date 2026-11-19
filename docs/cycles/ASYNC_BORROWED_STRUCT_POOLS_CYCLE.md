[Français](ASYNC_BORROWED_STRUCT_POOLS_CYCLE-fr.md)

<a id="pools-async-de-structures-contenant-des-emprunts"></a>

# Pools async of structures containing borrowings

<a id="périmètre"></a>

## Perimeter

This lot applies ST1–ST4, ST6–ST14, T1/T6, B1/B2/B4a, D1, L1/L2 and
AS2/AS8–AS14 to Int/&Int/&mut Int structures supported by the layout
No regulatory rules are amended.
named manufacturers are connected; general owner catches
of these structures and their entire returns remain open.

<a id="implémentation-et-invariants"></a>

## Implementation and invariants

The fields borrowed use Cell descriptors without possessing the target.
Their provenance follows the bearer during transfers, branches, exits
The arguments already assessed remain reserved.
The contracts of auxiliaries
Synchronous and async children update the stored targets.

A shared reference extracted from the carrier retains its target independently of the
A mutable reborrowing also retains the reservation of the capacity of the
field. The return shared via an auxiliary uses the termination contract
In particular, when the porter was local and has already been destroyed.
No local targets are promoted.

The end of the loans stored at last use takes into account the borrowings still
The holder's assets, including those held by a task or a handle launched.
The disjointed paths remain distinct. The withdrawal of expired dependencies
is calculated until stabilization.

<a id="contre-exemple-corrigé"></a>

## Corrected counter-example

`validation/rejected-async-local-view-task-target.crust` Creates View containing
&n, then a task that borrowed View. An intermediate version accepted
`drop(->n)` before waiting for this task: the wearer no longer had any use
The two stages accepted the program.
invalid; it was not executed.
`validation/async-borrowed-struct-pools-task-counterexample.log` conserve ce constat.

The correction retains the targets stored as long as an active loan covers the
carrier field. The deterministic test checks refusal with task, handle launched
and alias, as well as the neighbors admitted after waiting or last use of alias.
The transfer that ignores the bearer's loans is detected.

<a id="preuves-exécutées"></a>

## Evidence

- Final Targeted Suite O0: 15 successful methods, 22.937 s; 28 executions
  In addition, 31 invalid programmes were rejected in both stages, i.e. 62 checks.
  Journal : `validation/async-borrowed-struct-pools-counted-o0.log`.
- Final baseline O2: 15 successful methods, 23.547 s. Ten mutations detected,
  No survivors or inconclusive. Chess displayed after each mutant
  are the expected detections, not the baseline failures.
  Journal : `validation/async-borrowed-struct-pools-final-mutations-o2.log`.
- Final Regression O2: 153 successful methods, 163.356 s.
  Journal : `validation/async-borrowed-struct-pools-final-regression-o2.log`.

All three processes are completed with code 0. C-executions use
Clang C11/pthread, Wall/Wextra/Werrar, Wno-unused-function, fatal UBSan and
O0/O2 according to campaign. No new evidence ASan/Tsan.

The finished loop model compares results for 0, 1 and 3 iterations.
Native probes control cleaning during suspension and replacement
This is not a complete independent auditor model.
The mutations aim at the destruction of the target borrowed, the transport/loss
or excessive maintenance of dependencies, mutable reservation, arguments
The oracles remain the same as the one used in the book.
These ten detections do not establish
a general coverage rate.

<a id="chronologie-et-limites"></a>

## Chronology and limitations

The intermediate newspapers are kept. The first passage had six failures
for eight methods: fixture diagnostics, loan rating and loan rating
kept beyond last use. `returns-o0` explained the refusal
in the case of a return shared via a local structure, corrected by the full contract.
The first mutation campaign was interrupted by a non-single anchor,
The first two years of the first year of the year were the first.
79 success and module import error; the final command fixes this name.
The fixedness of aliases required the connection of the loans named as porters.

The two synchronous/async probes of the newspaper `field-last-use-probe` refusent
conservatively destroy the target of a field if a brother field is used
No new field precision semantics are invented here.
Mixed graphs, other types borrowed, local returns of graphs and
general owner catches of borrowing structures remain open.
Decisions on the handles launched are not changed.
`reset()` remains removed from the prototype, without further testing of this historical API.

Snapshot : `/tmp/crust-before-async-borrowed-struct-pools`.
Diffs : `validation/async-borrowed-struct-pools-*.py.patch`.
The complete objective remains active; no general proof of security is claimed.
