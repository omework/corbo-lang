[Français](ASYNC_LOCAL_CAPTURES_CYCLE-fr.md)

<a id="structures-locales-capturées-par-les-tâches-enfants"></a>

# Local structures captured by child labour

<a id="périmètre-et-règles"></a>

## Perimeter and rules

This lot applies drafts 03/04/05/07, T1/T6, V5, L1/L2/L7,
B1/B2/B4, AS2/AS8/AS9/AS12 and ST17/ST18 rules for copying.
The European Council has set up a European Centre for the Development of Vocational Training in the European Community.
load by the backend async; it does not make all aggregates compileable.

The case retained in `validation/open-async-local-helper-child-capture.crust`
is now accepted by both stages and executed: a built structure
local in the parent is borrowed by the child, who suspends and reads his/her
The shared, mutable and proprietary catches, their relays, a
copy in the child and return of the owner parameter are tested.
Calls from synchronous code use the same storage distinction.

<a id="implémentation"></a>

## Implementation

The compiler memorizes one variant by async function and set of
parameters from a local data stack. Source signature and contract
calls statically choose the variant; the
runtime does not guess the type of storage at the time of execution.

In one variant, the parameters concerned have an external origin of the
data stack. This origin follows relays and selects synchronous bridges
adapted, in particular to `copy`. It is not added to the sources that the child
must close: the parent retains responsibility for storage.
created in the child use his own beach and are cleaned with his scope.
Loans and sources retained by the results remain monitored separately.

The variants are generated until the new applications are exhausted.
Synchronous bridges discovered during their generation are also emitted.
The number of internal slots takes into account the maximum between variants.

**Only one pool of states is kept by nominal function.** Lorsque plusieurs
exist, each slot uses a union C containing the states
The size and alignment are therefore suitable for all variants.
They share the capacity, generations and wake-up entrances of the same
pool. Creating a variant does not multiply the capacity specified by the user.

The border `T` / `A<T>` remains explicit. A declared parameter `->A<Point>` do not
is not receiving a local structure. An additional counter example announcing
`-> <- A<Point>` while returning its local parameter was found and corrected:
direct and calculated returns now control this distinction.

<a id="preuves-exécutées"></a>

## Evidence

`tests/test_async_local_captures.py` contains thirteen methods.
O0 succeeds in 6.010 s: **14 native executions**, **11 programmes invalides**
control at both stages (**22 refusal checks**).
The final baseline O2 succeeds in 8.149 s. The compilations use Clang C11,
pthread, Wall/Wextra/Werrar, Wno-unused-function and fatal UBSan.

- Shared recording and relay through two children.
- Mutable capture: mutation after admitted waiting; reading, writing or drop
  The parent's competitors refused.
- Transfer of ownership, relay and destruction of inactive task; use
  After transfer refused.
- Same routine called with a local structure and pool structure,
  with independent copies and original values preserved.
- Explicit capacity of a slot reused for four turns alternating the
  local variants and pool.
- Return of the owner parameter to the parent without double destruction.
- Returnable mutable reference: the parent remains reserved until the last use.
- Local source too short and implicit substitutions of `T` in `A<T>` - No, I'm not.
- Refusal to launch injected: the owner's catches are destroyed once.
- Probes C to suspension, then normal termination or exclusive destruction
  They control cells, separate sources, and
  the original and its copy, the values, the closing of the two beaches and
  the return of the state pools to empty state. They also check the steps of the
  slots in relation to state representation.

The probes do not add any public cancellation: they hold exclusively
Once a beach is closed, they don't read its cells anymore.

Journaux finaux :

- `validation/async-local-captures-counted-o0.log` ;
- `validation/async-local-captures-mutations-final-o2.log` ;
- `validation/async-local-captures-regression-final-o2.log` : **97 methods**
  pass in 94,989 s on the final code, covering captured structures, fields
  Borrowing, borrowing, home calls, capabilities and Select;
- `validation/async-local-captures-regression-initial-o2.log` : **67 methods**
  pass in 62,120 s before the addition of the return guard `A<T>`, covering the
  local results, parent/loop placements, captures and returns owners.

`py_compile` succeeds. `crust.py` and `async_lowering.py` are
archived under `validation/async-local-captures-*.py.patch`, relative to the
snapshot `/tmp/crust-before-async-local-captures/`All processes cited
are completed and their results have been recovered.

<a id="mutations-et-échecs-conservés"></a>

## Changes and failures retained

`tests/run_async_local_capture_mutations.py` detects six final errors:

1. Forget the variant chosen by a call from async.
2. Forget the one chosen from a synchronous caller.
3. Lose local origin at the child's entrance.
4. Use the size of the ordinary state as no slot despite a variant
   plus grande.
5. Allow the return of a room under a type `A<T>` explicite.
6. Allow capture under a parameter `A<T>` explicite.

Source oracles and C remain unchanged in mutated copies.
missing and representation/stocking claims are distinguished from
memory corruption; this small set does not measure a general coverage.

Two mutations first survived: oblivion of variant choice since async
and the original loss at the input. The test checked the correct values displayed,
but not the storage of the copy. The probe C was applied to these mutations:
the storage must be separate and closed with the child.
The first newspaper is coming in. `mutations-o2.log` remain preserved.

The newspaper `expanded-o0.log` contains a UBSan failure in the harness: it read
`copy->alive` After closing the copy range. Control has been moved
on the meters of the source, which reside in the still observable state.
The oracle keeps the closing check and no longer de-references a
cell released. `corrected-o0.log` and the final passages pass.

An intermediate meter (`complete-o0.log`) counted twice the calls
passing through `run_native`, which delegates to `run_c_oracle`. The final passage does not
the latter border and establish the **14** actual executions.
Initial and intermediate newspapers are not deleted.

<a id="écarts-encore-ouverts"></a>

## Differences still open

The results are kept in `validation/async-local-captures-remaining.log`.

- `open-async-local-only-copy-annotation.crust` is valid but still refused:
  `leaf(&Point)` copy its parameter in `let q:Point`. The local variant
  The system of validation of the ordinary body requires a
  source of pool and refuses this annotation before selecting the
  variants actually usable. We must treat storage requirements
  without allowing an incompatible pool call or removing annotation.
- A newly built result in the task still requires a destination
  the State for transfer from it.
  already durable parameter covered here does not resolve this case.
- `open-async-return-replaced-owned-field.crust` remains refused: the update
  the owner graph returned after replacing a field remains to be connected.
- General aggregates with borrowings, signatures of general and
  the cleaning arbitrations with a handle launched remain the limits of the
  previous cycles.

Multithread models, probes and scenarios are finished. No new
ASan/TSan result or general proof of security is not claimed.
The seven drafts remain open.
