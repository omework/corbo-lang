[Français](INLINE_VECTOR_POP_CYCLE-fr.md)

<a id="cycle--pop-des-structures-en-ligne-dans-vectort"></a>

# Cycle — Pop of online structures in Vector<T>

<a id="règles-et-portée"></a>

## Rules and scope

VE1–VE3, H1, T4/T5/T6, B1–B5, U1, ST15/ST17/ST18 and AS2/AS8/AS11–AS13
The following are the main features of the project:
were read; the full specification was read in the continuous work.
The perimeter of this lot is optional extraction of online structures,
with synchronous/async signatures and fields already represented.
Aucun nouvel arbitrage ni changement normatif.

<a id="baseline-et-réalisation"></a>

## Baseline and implementation

The snapshot `/tmp/crust-before-inline-vector-pop` keeps the initial modules.
`validation/inline-vector-pop.crust` was refused to both entrances;
`validation/inline-vector-pop-baseline.log` Keeps the diagnosis.

`pop()` now return `Option<T>` for Vector<T> local, distinct from
`Option<A<T>>` The Some has a carrier on the
implicit stack. The generated C prepares its storage and then copies the last box
and reduces the length; None does not build a carrier. Any slots
The objects designated are managed by the existing placement.
Field cleaning is not changed by fields A<T>.
transmitted to the result, which remains usable after destruction of the vector.

The sources and borrowings in the box are retained by the contracts.
signatures, annotations, wrappers Result and public handle distinguish the
local storage pool storage even if their ABI C uses a Cell *.
The extraction of each envelope transmits the field graph and the capabilities.

<a id="défauts-rencontrés"></a>

## Faults encountered

The newspapers `validation/inline-vector-pop-*` maintain intermediate steps:

- The first targeted failed on two scriptures through a pattern binding
  immutable and on the synchronous bridge called since async. Fixtures use
  now a receiver `let mut` explicit; the bridge retains local storage
  and field metadata.
- The second target still isolated a symbolic provenance in this bridge.
  The third pass: 14 methods, 7,724 seconds.
- The return of a task remained interpreted as Option<A<T>>.
  The opening of the Result lost the fields borrowed/owners.
  The reconstruction now takes over their full descriptor.
- Public contracts and their standardization lost the projection of the
  The corrections preserve this projection separately.
  The variations with premature mutation remain unchanged.
  The fourth to seventh passages document these differences and the
  wrong braid in the fixture await, corrected without changing the expected.

<a id="ciblé-exécuté"></a>

## Targeted executed

`validation/inline-vector-pop-targeted-final.log` : **20 methods, 9,770 s,
code 0**, O0/UBSan. **27 successful C executions**, **16 variantes invalides**
controlled by verify_program and compile_source.

Some/None, order LIFO, direct drop, empty structures, loop and re-use of the
pool, once cleaned home fields, shared and mutable references,
reservation of the remaining box, synchronous relays, calls from async,
returns by wait/join, wait async for an executed launched, public handle and
The refusals cover T/A<T>, use after drop,
Ignorance of a proprietary result and mutation before last use.
Reset remains removed from the current profile; this batch uses drop and the telescopes.

<a id="régression-et-intégrité"></a>

## Regression and integrity

Premier passage O2/UBSan : **361 methods, 246.143 s, code 1**,
349 hits, three failures and nine errors. 69 compiler/test prints
remain the same during the passage (`-integrity.log`).

The nine Select errors came from two modified signature destructures
too widely in this lot. They are restored; the added storage does not concern
the signature of the waiting that needs it. The three failures of public options
The new T/A<T> requirement applied to a set of sources was used to determine the
The verified return signature still retains this type.
The distinction is repeated in the common collection of the result, without inventing a source
It is used for normalizing the handle and controlling the load.
The first single replay retained three failures in the second point of
control; the second succeeds: **four methods, 3,689 s**, code 0.

Rejeu O2/UBSan : **173 methods, 155,584 s, code 0**, in
`validation/inline-vector-pop-replay.log`. It includes the modules of the 12
failures, the 20 targeted tests and the Select source tests, contracts, results,
The 46 replay prints remain unchanged.
The results of the 361 selected methods are available after correction,
but it is not a single passage of 361 green methods on the version
The amendments after the first passage concern only
the two Select destructures and the common control of the type of an empty option.
The main selection is
stored in `validation/inline-vector-pop-selection.json`, his prints in
`-start.json`, the diff in `validation/inline-vector-pop.patch` and his manifesto
in `-changes.json`. Selections/prints of the game use the prefix
`validation/inline-vector-pop-replay-`No existing test was weakened.

C retained in `validation/inline-vector-pop.c` and
`validation/inline-vector-pop-async-return.c`. The first shows the pop followed by the
drop the vector then read/destruction some. The second place the carrier
in `frame->result_storage`, transfers the result and gives NULL the pointer
The execution and traces complete the work.
This inspection does not replace dynamic checks.

## Limites

The results are based on the cases performed and the types represented; they do not
This is not a general proof of safety.
sources after some branches/calls remain conservative. Replace, try_push,
slices, push_new and general graphs of online structures remain
native tests use C11, pthread, Wall/Wextra/Werrar and UBSan
fatal via the project harness. No mutation or research campaign
The independent audit is not presumed.


<a id="suite-du-chantier"></a>

## Continuation of the construction site

The next VE3 gap is reproduced in `validation/inline-vector-replace.crust` :
replace a Point box must make the old Point (or enter in case of index)
The journal still refuses this program.
`validation/inline-vector-replace-baseline.log` Keeps the diagnosis.
This cycle ends its tested pop batch, not the overall target.
