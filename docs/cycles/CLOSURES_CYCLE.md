[Français](CLOSURES_CYCLE-fr.md)

<a id="closures-réutilisables"></a>

# Reusable closures

The digital profile lowers the encloseds to a local structure
by expression and a method called by shared borrowing.
and the call use the ordinary initialization,
transfer, borrowing and cleaning. For a parameter
`closure(...) -> R`, the compiler checks the signature and specializes
the synchronous function for the specific type transmitted.

<a id="exécutions"></a>

## Implementation

- Five successful test methods to `-O0` and to `-O2` sous UBSan fatal.
  They cover six native executions and seven static refusals per level.
  They check in particular the copy at creation, two calls on a
  the same body, two specific specializations, the conservation of
  the rejection of a target destroyed too much
  early and re-use of the slot after destruction of a proprietary catch.
- The pass to `-O2` with numerical regressions, native blocks and
  Function type contracts have 31 successful tests. A first pass
  had also discovered the historical tests of `type feature` by
  the import of their aid class. It finds the failure already recorded in
  [CORE_ANNOTATIONS_CYCLE.md](CORE_ANNOTATIONS_CYCLE.md) for
  `type feature Plain { fn a(self); }`.

<a id="périmètre-restant"></a>

## Remaining Perimeter

The current structure representation can store references
a reference to a local scalar uses
another representation and its capture remains to be connected.
mutables and the values composed by value are also partial.
Function signatures with closing parameter are specialized in
The independent verification of a function
never called, recursive specialization, async closing parameters
and coexistence with annotated type contracts remain open.
This cycle focuses on targeted cases, without independent audit or
mutations.
