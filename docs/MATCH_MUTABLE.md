[Français](MATCH_MUTABLE-fr.md)

<a id="validation-du-match-mutable"></a>

# Validation of the mutable match

`match &mut writer` reserves access to the carrier until the end of the arm.
field link `&mut Int` can write in his target with `.set()`. The bearer
then resumes protection of this target until its last use or
P9 specifies this extension of B1 and B2.

The auditor uses a reservation as part of the borrowings during the
The generated C load the pointer stored in the field and written in
The arms are exhaustive and allow readings,
scalar copies, blocks and projection writings.
do not add any transition of property or condition of the cleaning to be merged.

<a id="cas-et-limites"></a>

## Cases and limitations

- An allowance subject to a mutable match requires `let mut`. Un emprunt
  existing mutable, e.g. a parameter `&mut Writer`, suffit aussi.
- The test model places the original reading before or after two borders,
  the end of the arm and the last use of the wearer.
  fails even after the last `.set()`. After both borders, she reads
  the new value.
- A conditional return can change the targets of two fields.
  targets are distinct in each execution but their static sets
  The prototype refuses the two projections used in the
  The projection of a single field is checked and executed.
  The current representation of provenances is maintained by restriction of analysis.
- Shared fields and scalar copies remain legible.
  The arms keep a restricted grammar. The section on Void calls
  describes its subsequent extension.

<a id="observations-exécutées"></a>

## Observations implemented

The 10 dedicated tests include 9 separate sources admitted and performed as well
19 separate sources refused by `verify_program` and `compile_source`.
They also check the addresses of the carrier and the target, the transfer through
two successive calls, refusal of a drop or premature reset, cleaning
unique and variants present or absent at the execution.
The overall suite passes 739 tests in 309.930 s. The configuration
`CRUST_SANITIZE=undefined` passes 67 tests in 31.921 s with pattern
`test_mutable*.py`Both suites end without being ignored.

Three injections targeted at copies are detected.
reservation of the subject by an empty frame allows premature reading.
Replace the projection mode with `ref` refuses a valid handwriting.
Remove parameter `write=node.mutable` subject access control
admits entries without writing right and can trigger the invariant
exclusive in the presence of a shared alias.

Two programmes were implemented in C with Clang in `-O0`, `-O2`, `-Os` and
`-O2 -fsanitize=undefined -fno-sanitize-recover=all`The eight executions
confirm the values and destruction expected.
Use the target after the game, the second after the last access to the bearer.
[Gross sources and outputs](../validation/mutable-match-targeted.json).

<a id="réexamen-des-règles"></a>

## Review of the rules

I1–I5 and V1–V5 frame explicit borrowing, copies and writing on
place. S1–S6, T1–T11 and U1 frame the end of the scope and follow up receptions
D1–D4 and B1–B5 frame sustainability, target unions
and exclusive access during calls. L1–L7, A1–A6, P8–P9 and E1 frame
The main areas of concern are the pools, the release and cleaning.
existing rules for placement and storage. Both test models
The two-border model and the case of permutation of the
target, with expected results calculated from the order of uses
and the built variant.

The tests and injections sample these interactions.
between conditional targets, non-clause `.set()` in an arm
and the other C compilers remain outside this campaign. UBSan covers the
ASan, already unavailable on the host during the cycle
previous, was not replayed.

<a id="appels-void-dans-un-bras"></a>

## Calling Void in an arm

A projection can be provided by its name to a borrowing parameter
compatible. The call suspends the projection during the reborrowing and arm
may be used when returning. The holder remains reserved during the call and
until the arm exits. The interface of this step limits the arguments
the projections named and the result in Void. This limit allows the
function of using its own local storage while maintaining the
sources and cleaning of arm allocations.

The test model places the accesses to the target in the arm after return,
after the arm before the last use of the carrier, then after the end of the
protection. The return of the call restores the projection and leaves both
The tests combine a relay by sub-call, a
block in the arm, successive writings, control of the aliasage and
The use of the mode, the reset after use and the single destruction.
impossible arm is controlled on its types and modes from the
Field reporting. The specialized compiler does not generate any calls
for this projection without a target. A call that diverges ends only
his arm when another variant can continue.

The cycle adds 6 dedicated tests. They cover 4 separate sources allowed
and 11 rejected by both courses.
detected on copies, relating to the reservation of the holder, the mode
shared and the type's availability in an impossible arm.
for relay and post-call writing produces values and traces
expected under Clang in O0, O2, Os and O2 with UBSan. Substitutions and
observations are retained in
[gross results](../validation/mutable-match-calls.json).

The interactions P9 and B1–B5 concern exclusivity, the resumption of the
projection and the result Void. S4 and S5 limit the arm and call, D1–D4
and T9–T11 frame possible targets, V4 and V5 frame writing in
L1–L7, A2 and A5 frame the cleaning after the end of the protection.
The other families of the previous review remain covered by the
The call for results and arguments other than the
The four executions were carried out in accordance with the provisions of the Convention.
cover a family of compilers and a single compound program.

Overall regression passes 745 tests and UBSan configuration targeted
passes 73 tests with pattern `test_mutable*.py`. The six injections
previous on mutable fields are detected after updating
The two suites finish with the injection point of the projection parent.
UBSan is the instrument of the binary tests involved.

<a id="résultat-int-reçu-dans-le-bras"></a>

## Int result received in the arm

`let valeur = lire(vue)` receives an Int copied into a local link.
The call keeps the rules of passage by name of projections.
Reuse projection on return. The copied value remains available after
a new writing through the projection, without prolonging his loan.
The carrier reservation always covers the arm.

Tests read 10 via projection passed to a parameter `&Int`, write
20 through the same projection, then observe 10 in the copy and 20 in the
Target. Local name is denied out of arm. Direct access to target remains
No one can use the arm after copying.
the result without executing the call and remains subject to verification of
The Int result follows the rules of copying V3 and calling B4
and the scope of the S4 block. The rules of exclusivity and cleaning
have the same application as for Void calls.

The overall suite passes 747 tests and the targeted suite under UBSan passes 75.
The target corpus consists of 6 distinct sources admitted and executed and
14 refused by both courses. The four C executions in O0, O2, Os and
O2 with UBSan confirm the values and destruction order of the case
copy. The injection that removes the result typed from the arm impossible
is detected. [Gross results]](../validation/mutable-match-int.json).

<a id="réemprunt-mutable-reçu-dans-le-bras"></a>

## Transferable loan received in the arm

A statement `let mut autre = reemprunter(vue)` receives a `&mut Int`.
The chain of borrowings of the result retains the parent projection and the
reservation of the holder. As long as a use of `autre` will be forthcoming, a
reading, writing or calling using `vue` is refused.
dernier usage, `vue` can be used again in the same arm.
The phone calls from the arm can take his name as
argument, with the same fashion and exclusive controls.

The scenarios contrast the same access to the parent placed before or after the
last use of the child, with a return relayed by a second function.
They also check that the original access to the target remains blocked and
the bond does not resolve out of the arm.
impossible, the type of result is kept to verify the operations
without inventing a target. The lifetime conflicts of the result y
rest on the impossibility of the path, while the executable paths
are verified on their actual or possible targets.

The B1, B2, B4 and B5 rules are combined with S4 and P9.
changes the life of the target or the responsibility for cleaning.
D1–D4 and V5 continue to apply to its provenance and identity.
The rules on transfer, destruction and pool are covered by the
The following section describes the extension that allows for the
receive this loan out of the arm.

The overall suite passes 749 tests and the targeted suite under UBSan passes 77.
The target corpus includes 8 accepted and executed sources and 19 refused by
four performances of the C generated in O0, O2, Os and O2 with UBSan
give the expected values and destruction trace.
who ignores the result that is still active when accessing the parent is detected.
[Gross results](../validation/mutable-match-return.json).

<a id="résultat-mutable-reçu-après-le-match"></a>

## Transferable result received after the match

```rust
let mut dehors = match &mut writer {
    Writer.Bound { data: vue } => {
        let mut autre = reemprunter(vue);
        autre
    }
};
dehors.set(30);
print(writer);
```

Inverting the last two instructions causes the reading of
`writer`. The result carries its possible targets and a reservation
The reservation also follows the reborrowings derived from the result.
C places the selected pointer in a local variable before leaving the
arms. The auditor controls the life of the wearer and the targets
The access, movement and movement controls are the most important of the types of controls in the receiving range.
reset consult this reservation, including for other fields
on which the bearer depends.

The test model distinguishes between remaining use and finished use.
exercises the reading of the bearer, his reassignment and destruction or resets
A conditional variant may be used to determine the number of people in the pool and the target.
Select separate targets. The result protects their union and the C
changes the only target selected at execution. An opaque call cannot
reset a source of the carrier or its dependencies when it receives
This historical restriction has been refined by the contracts of order
described in the last section.

This extension covers the reception by `let mut` and the passage of the result
The following section extends the reservation to all compatible calls:
function return for a borrowed carrier as a parameter. The last section
extends this perimeter to the storage of the result in a field. The arms require a final name and check its type.
Targets of statically impossible variants do not contribute
the result.

P9, S4, B1, B2, B4 and B5 frame the scope and last use. D1–D4,
T9–T11 and V5 frame possible targets, their lifespan and their
identity. A2, A5 and L1–L7 frame the cleaning. The injection test
which withdraws the loan from the bearer detects the erroneous acceptance of
`print(writer)` before last use. Four Clang configurations
confirm the values and destruction in the accepted case.
[Cash, injection and raw outputs](../validation/mutable-match-escape.json).

The 7 dedicated tests cover 6 separate sources admitted and performed and
The overall regression passes 756 tests and the number of tests is
The suite targeted under UBSan passes 84, without any unknown test.
executed in O0, O2, Os and O2 with UBSan on a family of compilers.

<a id="retour-depuis-un-porteur-emprunté-en-paramètre"></a>

## Return from a borrowed carrier as a parameter

A function `ouvrir(writer: &mut Writer) -> &mut Int` peut retourner
The contract describes each origin by the number of the match.
the carrier parameter and the qualified field name. It retains these origins
through relay calls, even when the carrier changes position
The applicant's name is the name of the applicant.
the target and recreates the reservation of the carrier.
the actual allocation is ruled out. The backend checks that the targets and
the carriers observed in the body are included in the contract.

The last-use model distinguishes `print(writer); dehors.set(30);`,
which is refused, in reverse order, which displays `Writer.Bound(30)`.
The same reservation blocks the destruction of the carrier and the reset of the
The targets remain protected from these operations.
local is refused even if its field points to an allocation of
A carrier received by transfer is also refused.

The scenarios cover the modes and returns of B1–B5, the duration of the
the life and provenance of D1–D4, the variants of P9 and the effects of reset
and destruction of A5 and L1–L7. The result retains a static union
possible fields when the variant is unknown. The last section processes storage in a field and
composition with the resets.

The six dedicated tests cover five separate sources admitted and performed
and nine rejected by both courses. The overall suite passes 762 tests and
The suite targeted under UBSan passes 90, without any test ignored.
C in O0, O2, Os and O2 with UBSan give values and destructions
The injection which omits the reservation of the bearer in the contract
[Gross results are detected.](../validation/mutable-match-function-return.json).

<a id="réservations-transitives-et-ordre-des-resets"></a>

## Transit reservations and order of revenues

A field can keep a loan returned by `ouvrir`. Loans from the
carrier are rebuilt from the chain, including for an object
a transfer checks the life of the
The conditional returns all retain
possible carriers and execution only writes in the chosen target.
Object contracts distinguish a field that transmits a loan
an existing field that reserves a borrowed carrier as a parameter.

The contract of constraints distinguishes the sources from the parameters and
The analysis memorizes the potential resets
Two exclusive branches may be one of the following:
reset and write the other. After joining, use the view
requires disjunction with the sources reset on one of the paths.
The loop returns carry the same history.
substitutes sources for the constraints of sub-calls in order.
The call site auditor consults the contracts. Generation C
keeps his checks during specialization.

The contract retains the effect of reset to invalidate at
the appellants of the carriers that may have been destroyed.
protects the loans the appellant will reuse and the arguments already
These controls apply to transitory dependencies.

The test order model contrasts two sequences, then uses and resets
reset then use, in direct operations and sub-calls.
also controls the inferred contract independently of the performance of the C.
Separate scenarios exercise branch junction, return of
loop, the loan that is not an argument of the call, the argument already
The chain of carriers and the union of two origins.
preliminary revealed a double counting of a bearer's loan when
the relay was returned by an award contract.
removes the parent's loan for the benefit of the loan transferred in this case.

B1–B5 and P9 frame the loan chain. D1–D4, T5 and T9–T11 frame the loan chain.
life and provenance at each transfer. S4 and S5 frame
the paths and recaptures, B4a the preparation of arguments, A5 and L1–L7
reset and cleaning. Possible sources and paths reached
The contract may therefore refuse a combination of the two
which would require a correlation between two conditions
The comparison C is for a family of compilers.

The overall regression passes 771 tests and the targeted suite under UBSan in
99. The nine dedicated tests cover 12 separate sources allowed
and 20 rejected by both courses.
are detected. They omit the order constraints respectively
The eight are the only ones that have been used to make the call.
C-executions cover two programs in O0, O2, Os and O2 with UBSan,
with control of values and the trace of destruction.
[Sources and gross results](../validation/mutable-match-reservations.json).
