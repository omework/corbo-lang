[Français](STRUCTURES_METHODS_CYCLE-fr.md)

<a id="cycle-documentaire--structures-et-méthodes"></a>

# Documentary cycle — structures and methods

Date : 5 novembre 2026.

<a id="demande-et-périmètre"></a>

## Demand and scope

Record the last work before continuing the arbitration.
implementation, no modification of tests.
VALIDATION_GUIDELINES.md have been read. This report is not a complete cycle
validation executable within the meaning of the guidelines.

<a id="décisions-consignées"></a>

## Decisions recorded

STRUCTURES_METHODS.md brings together ST1–ST18 and ME1–ME4. LANGUAGE_RULES.md integrates
the extension and I6, the explicit objective of legibility of the intention for the
The README and the matrix distinguish design and behaviour
the actual implementation.

Important points of fidelity to the discussion:

- Final decision prohibits removal by moving non-Copy fields
  and partially initialized states.
  partial cleaning and junction after displacement are no longer normative.
- An omission to `pool.new` remains allowed if a defect of the type initializes
  Indeed, the field: this is not a partial state exposed to the program.
- The Int=0 default and the recursive deduction are retained; the return of the int=0 default is
  defect on the field has been rejected. Custom tags and defects are reported.
- Copies become `pool.copy(original)` ou `copy(original)` with
  The existing prototype of inline paintings is not modified.
- The division of a name between field and method was finally refused.
- The automatic borrowing of the receiver was accepted; a transfer from the receiver
  remains visible with `(-> valeur).methode()`.
- The UTF-8 proposal did not receive agreement: it was not added to the rules.

<a id="interactions-à-vérifier-ultérieurement"></a>

## Interactions to be verified at a later stage

Design scenarios not implemented:

1. Named construction: defaulted/undefaulted omissions, duplicates, unknown fields,
   incompatible types and arguments effects left → right.
2. Two mutable reservations of separate direct fields allowed; access to
   an incompatible covering refused; interlocking paths and indirect aliases.
3. Result pointing to a direct field: reserved holder; contract returning
   only a shared reference to an external target: free-carrier.
4. Reborrowing a mutable field: retain the target and the parent capacity,
   prevent use/replacement of the field before last use of the result.
5. Argument `&mut Struct` impossible during incompatible field loan,
   even if the body called only accesses a separate field.
6. Reference reallocation: old dependencies retained if there is
   Other loans; new target valid on all paths.
7. Non-Copy extraction refused directly, in a branch, by a call or
   through an interlocked path; no partial cleaning to be generated.
8. Full replacement: new allowance before destruction of the old,
   capacity pressure, refusal in the presence of a future borrowed use of the old.
9. Copy: new slot identities and independent content; fields
   shared references still dependent on targets; field not copyable.
10. Methods: automatic borrowing compatible with signature and loans;
    consommation sans flèche et collision de nom champ/méthode refusées.
11. Child contracts and transfers → parent, tables containing structures,
    champs tableaux et captures async : règles existantes à composer, sans
    assimiler leurs preuves antérieures à des preuves de ces nouveaux cas.

<a id="questions-et-limites"></a>

## Questions and limitations

Grammar and backend still have to be implemented. `copy` entre
Inline values and allocations with provenance must be integrated without changing
silently the rules already adopted for the tables. ABI details,
modules, visibility, overload and custom destroyers are not set
by these decisions. No increase in overall safety or generation reliability
IA is not shown by this single recording.

<a id="vérifications-de-cette-passe"></a>

## Checks of this pass

A document check checks the identifiers, their entries in the matrix,
files targeted by local links and code block delimiters.
He does not check Markdown anchors or semantics or execution of snippets.
Completed: 22 unique ST/ME identifiers and I6, 23 corresponding lines
A), 151 local links to existing files,
and balanced blocks of code in the five documents concerned.

Compiled/executed programs, language tests, independent models, generation,
mutations and sanitizers: none in this pass. ST1–ST18 and ME1–ME4 are
not implemented and not verified by execution; I6 is a design objective,
without general proof of intention/code correspondence.

<a id="st7-et-st10st13--déréférencement-explicite-dun-champ-partagé"></a>

## ST7 and ST10–ST13 — Explicit de-reference of a shared field

`print(*v.inner.target)` was refused for a field `&Int`.
The compiler treated him as a reborrowable field loan.
It now reuses the verified reading of the shared field to
get his target before loading the Int. Reading keeps the
The resolution of the path, possible targets and restrictions.
The scalar result is independent of the carrier and the target.

The test executes direct readings and via a function, changes
the target, destroy the old target, then use the scalar after
destruction of the carrier and the new target. Drop and reset of
the new target before its last reading are refused, as
The attempt to obtain a mutable reborrowing.
go under Clang C11, -O2 and fatal UBSan. Disabling of
the branch added, in a temporary copy, reproduces the
valid appeal refusal. No new independent model.
The following are the main projects under way:
entire inline substructure remains open.

<a id="réemprunt-partagé-explicite-et-contrat-détaché"></a>

### Explicit shared loan and secondment contract

`&*v.view.target` follows the same path of origin as the reference
shared stored in the field. L'analyse des contrats conserves the
external target with `detached_field_parameter`. The auditor
arguments also evaluate this reborrowing as a reference, including
for mutable nominal projections already supported.

Native L-oracle exercises the immediate passage into argument, the return via
Two functions, field reallocation, drop and re-use of the
carrying in a pool of capacity one. He then reads the old and the
new target. Writing on the old target, drop the new and
premature reset of the pool are refused. Writing after last use
pass. Four targeted tests pass UBSan fatal, including one mutation
d
a function. Disabling the inference of the detached contract
in a temporary copy reintroduces the refusal of the valid return.
The implementation of expanded field tests has been launched.
independent model. Integer inline substructure borrowings
restent ouverts.

<a id="réaffectation-conditionnelle-avant-retour-du-réemprunt"></a>

### Conditional reassignment before re-borrowing returns

The 72 field tests launched in the previous cycle pass.
extra executes both branches of a reassignment
conditional via synchronous relay. The contract contains exactly
The origin of the field before the call and the origin of the parameter affected.
The carrier is destroyed before reading the result.
the two distinct pools are protected until
reading and their reset is then allowed.
under UBSan and four static refusals passed.
large and still in progress cover earlier revisions.

<a id="réemprunts-mutables-de-champs-distincts-dans-un-appel"></a>

### Reborrowable borrowings from separate fields in a call

An oracle combines ST7, ST11–ST12 and B4a. It passes two fields
`&mut Leaf` from the same holder to a function that writes on
both targets and returns his first argument.
d- arguments pass in C under fatal UBSan. After the return, the
brother field is reborrowable and the returned target remains accessible
for each of the two orders, a duplicate in the
the arguments, a competing reborrowing of the reserved field and the
premature destruction of the bearer is refused.

A transfer replaces the field reservations by the only one
The carrier's descent. It changes the diagnosis of destruction
premature, but invalid cases remain rejected.
thus distinguish the diagnosis, without highlighting
difference in acceptance for this mutation.

<a id="résolution-de-la-méthode-join-selon-le-receveur"></a>

### Resolution of the join method according to recipient

Un `impl Point` could declare `join`, mais `p.join()` was
interpreted as waiting for a handle. The resolution uses the
type of receiver and his contract, including in an argument
borrowed. The last-use calculation includes the recipient
The real join of a handle remains covered by this syntax.
by async regression.

Under fatal UBSan, the oracle reads the result of `join` comme argument
direct and via a relay, then modify the field after the last
use. Premature drop and writing during loan are refused.
Disable typed resolution in a duplicate temporary copy
The diagnostics for the handlers. Targeted tests pass.
The overall continuation of the previous revision on async provenance
ends with 1,420 successful tests. The extended suite of methods
on this revision is in progress.
`split_at_mut` can still mask a homonymous method.

<a id="résolution-de-split_at_mut-selon-le-receveur"></a>

### Split_at_mut resolution according to recipient

The parser retains the cutting form at an argument like
method candidate. He accepts other italities as calls
and let the recipient type determine the signature.
The contracts thus distinguish the method of structure and the
Vector partition. A result of ignored partition remains refused.

Native L-oracle calls for a mutable method without argument, relayed
one loan obtained by the homonymous method to one argument from another
type, then exercises both halves of a Vector in the same
Program. Incompatible Inherities and Premature Change
The loan target is refused.
form to an argument in a temporary copy causes the
type of relay return and reproduces the refusal of the valid program.
The selection of the cutting tests is passed under fatal UBSan.
20 method tests and 416 fundamental tests are performed
the corresponding earlier revisions.
The review was launched.

<a id="méthodes-homonymes-dans-les-bras-de-match"></a>

### Homonymous methods in match arms

The Preliminary Auditor of Arms acknowledges appeals
`join` and `split_at_mut` on a projection of structure.
It uses the result of the contract, then the auditor
The normal application of access rights and the monitoring of reborrowing.

Five targeted match tests pass UBSan fatal. L-Oracle
parameterized compare `edit`, `join` and `split_at_mut` on the
same projection. It accepts the mutation after last use
and refuses a premature writing or a mutable call on a
read-only carrier. Restrict recognition
to the ordinary syntactic form in a temporary copy
Reintroduces the refusal of both homonyms.
match tests are underway. No new independent model.

<a id="réemprunt-de-méthode-retourné-par-le-match"></a>

### Reborrow method returned by the match

The test back from `match &mut` now has the three
formes `edit`, `join` and `split_at_mut`. In each case, the loan
towards the field crosses the arm exit then two contracts
synchronous. The modification via the result is observable under
UBSan. The drop of the carrier, the reset of the target pool in the
historical profile and a concurrent mutation of the target are
The three native and non-native variants
the nine refusals pass. The wider suites are always
on previous revisions.

The extended selection of the previous revision completed with
85 successful match tests. Additional variants of
return of the two homonyms were executed separately.
