[Français](ASYNC_LOCAL_STRUCT_HELPERS_CYCLE-fr.md)

<a id="réception-locale-de-structures-depuis-un-helper-synchrone-en-async"></a>

# Local reception of structures from synchronous helper in async

<a id="règles-et-périmètre"></a>

## Rules and scope

This lot applies the rules already retained in drafts 03 and 05: a
local structure T uses the data stack implicit of the receiver; it retains
The ST17/ST18 copy rules of draft 07,
T1/T6 transfers, B1/B2/B4a borrowings and L1/L2/L6/L7 cleaning remain
No regulatory rules are amended.

The case `validation/open-async-local-owned-struct-helper.crust`, refused to cycle
The helper receives A<Int>, built a
Local Holder containing this allocation, then makes this Holder current
The task can keep it through yield, read its field and
The Holder's storage belongs to the receiver; the storage belongs to the field.
It's not a newly created A<Holder>
allocated in an implicit pool.

The structures allowed are the fixed families already represented by the
backend async, without any fields borrowed.
Int field structures; a proprietary field remains non-Copy.
This batch does not complete transfers of these values between telescopes or tasks.

<a id="implémentation"></a>

## Implementation

- A call for local results receives an internal argument `Source *` which designates
  the data stack of the receiver scope in the async state. The bridge reserves the cell
  the result before invoking the helper and reuse the existing mechanism of
  The helper does not destroy this storage.
- The stack is created during the first call in the scope. It uses
  the existing default of 16 Mio virtual range. The destruction of values
  before closing, on normal return as well as suspended cleaning.
  loop covers create/clean up storage of the actual iteration.
- The source of results and fields are kept in the local analysis.
  Borrowings and dropes follow the last use; a parameter A<T>
  explicit and an A<T> notation refuse a local value T.
- One helper has specialized bridges according to local parameters
  The control of the appeal remains based on the contract; the
  specialisation transmits the storage facts to the backend of the helper.
  also allows copying from a shared &Point parameter.
- Shared/mutable methods can be directly received by a Local Point.
  Their implicit borrowing of receiver respects `let mut`.
- A reassignment no longer converts a local value T to A<T>, nor the reverse.
  The recipient's provenance is retained prior to the assessment of the right member.

<a id="défauts-et-contre-exemples"></a>

## Deficiencies and Counter-Examples

The first reception passes in `validation/async-local-struct-helper-initial.log`.
The next copy probe produced the expected value 7 but destroyed the
copie comme un scalaire (`destroy q=0`) : the description of Point was lost.
The source specialization corrects this defect.
are kept in `async-local-struct-helper-copy-probe.log` and `copy-second.log`.
This probe was performed during the development of the batch, after opening the
path so far refused; it does not describe an executable program before the lot.

The first suite of eight methods had two failures: borrowing from a receiver
local still used scalar access, and a test was trying to create a
Pool<Point> in async, functionality still open. The first path is
correction. The double specialization test now builds the pool in hand
and transmits its allocation to the task, without claiming to cover the construction
The second suite of eight methods is 5.660 seconds.

The first version of the reassignment counter example was refused for
no explicit use of the old value; this refusal is retained in
`validation/async-local-struct-helper-replacement-counterexample.log`.
The programme is refined `validation/rejected-async-local-pool-replacement.crust`
reads both values before replacement. In a temporary copy of the code
Without the T/A<T> distinction, both courses accept it.
refuses it for the right reason, as well as the opposite substitution. No binary
The following are the main features of this poorly typed program:
`validation/async-local-struct-helper-replacement-counterexample-refined.log`.

<a id="vérifications-exécutées"></a>

## Audits performed

Native commands use Clang C11, pthread, Wall/Wextra/Werrar,
Wno-unused-function and UBSan blocking. The test files are
`tests/test_async_local_struct_helpers.py` and
`tests/run_async_local_struct_mutations.py`.

- **11 targeted methods** go to O0 in 15,507 s, journal
  `validation/async-local-struct-helper-corrected-o0.log` ; the final baseline
  O2 passes the same eleven methods in 15.780 seconds in the mutation campaign.
  They run 18 native programmes/sounds and audit seven programmes
  In each of the two courses, the number of disabled persons (14 refusal checks).
- The cleaning model compares three prefixes independent of a loop:
  k iterations completed involve closures; cleaning of the iteration
  The C counters and destructions match.
  Other tests cover 0/1/3 iterations, continuous, break and return.
- Two additional probes check the termination and the suspended cleaning
  They control the non-pool storage, the living cell,
  value, Point metadata, single destruction and closure.
  The harness has only one unlaunched task: no operation
  public cancellation is not added.
- The source programmes cover two simultaneous results, replacement,
  the owner and shared copy, the local/pool bridges of the same helper,
  methods, annotations and loans through yield.
- A larger regression of **120 methods** passes in 97,758 seconds before the last
  T/A<T> reassignment custody:
  `validation/async-local-struct-helper-regression-o2.log`.
- On the final code, **50 methods** Switch to O2 in 50.733 s: calls
  synchronous owners, proprietary structures in async bridges,
  local reception and async returns of structures. Journal:
  `validation/async-local-struct-helper-final-regression-o2.log`.
  The minimum reassignment programme was refined during this implementation;
  the final baseline separated from the eleven methods then checks the two senses
  substitution with the final version of the test.

The first newspapers `suite-initial-o0`, `suite-second-o0`, `suite-third-o0`,
`model-o0` and `final-o0` are retained. `final-o0` and the first marketing year
`mutations-complete-o2` contain the expected failures caused by the first
reassignment snippet, prior to refining; they are not presented as
successful passes.

## Mutations

The first four-error campaign detects three mutations and leaves one
inconclusive: clear local origin first produces a warning C
unused reservation, rendered blocking by Werror. Journal:
`validation/async-local-struct-helper-mutations-o2.log`.
In the mutant only, an expression `(void)` neutralise cet avertissement
To achieve his wrong runtime behavior.
incorrect copy/unused reservation. The intermediate campaign of four
errors succeed in `mutations-final-o2.log`.

Final campaign detects **cinq fautes** after successful baseline: absence of
reservation at the caller, loss of local origin, forget closure
The result of the change in the number of Ts is that the number of Ts is not the same as the number of Ts.
T/A<T> distinction in replacement. Copies are isolated, oracles are not
Journal:
`validation/async-local-struct-helper-mutations-corrected-o2.log`.
The failure to book is detected by refusal of a valid program; this
detection is not presented as an executed memory corruption.

<a id="écarts-et-limites"></a>

## Variations and limits

The current results of the two courses are recorded in the
`validation/async-local-struct-helper-open-limits.log` :

- `open-async-local-helper-parent-transfer.crust` : a result built in
  A child block must be able to join his parent.
  that the storage of the parent receiver is not reserved by this path async.
  The diagnosis currently speaks of a local pool while the source is a
  data stack; the program is valid according to rules, not normatively prohibited.
- `open-async-local-helper-child-capture.crust` : forwarding the Local Point to
  a child task and waiting for it is valid. This path remains explicitly
  refused, because the local/pool distinction does not yet pass through the signatures
  It is necessary for a copy in the child.

The return of a local object from the task also requires injection of the
The structure containing borrowings, the storage of the external receiver, the
direct constructions and pools of structures in the states remain
The return after replacement of a proprietary field in a
helper remains the difference recorded in the previous cycle.

The current placement covers reception in the current scope, without claiming
carry out the general placement parent/child of draft 03. The probes are
no general safety evidence or new ASan/TSan result.
All processes cited are completed. Modified modules and tests
passent `py_compile`; diffs are archived in
`validation/async-local-struct-helper-*.py.patch` in relation to
`/tmp/crust-before-async-local-struct-helper/`. The overall objective remains open.
