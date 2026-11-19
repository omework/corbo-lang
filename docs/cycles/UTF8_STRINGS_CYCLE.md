[Français](UTF8_STRINGS_CYCLE-fr.md)

<a id="cycle-documentaire--utf-8-str-char-et-string"></a>

# Documentary cycle — UTF-8, str, char and String

Date : 5 novembre 2026.

<a id="demande-et-portée"></a>

## Application and scope

Record the rules of the String yard before taking over the first case of
Vector<T>, without implementation. AGENTS.md and VALIDATION_GUIDELINES.md were read.
This cycle is only documentary: no code, no runtime, no tests, no examples
Executables are not modified. It is not a complete validation according to the
guidelines.

<a id="documents-et-fidélité-aux-décisions"></a>

## Documents and decision fidelity

UTF8_STRINGS.md introduces TX1–TX20. LANGUAGE_RULES.md integrates them, README
stands out for design and executable support, STRUCTURES_METHODS.md updates its
former status of the UTF-8 yard and VERIFICATION_MATRIX.md inventory the
No case of generic Vector is declared validated.

The final decisions replace the following proposals:

- `Str` devient `str` ; a textual view is &str.
- `slice_bytes(...)` and the automatic cutting loan is replaced by
  `&texte[debut..fin]`. A simple index returns a byte, not a tank.
- The extraction name is char_at, with index in bytes.
- Iterators, tanks and char_indices are carried forward; utf8_len is retained.
- The tank replacement limited to the same encoding width was not retained.
  Byte replacements of constant length are then allowed under
  validation of the complete result, without any guarantee of the meaning of the text.
- The mid-ranges require a new Thong and a visible cost.
- truncate_bytes remains proposed, without explicit agreement; it is not added.
- The annotation selected is stack_region_max_size; intermediate names do not
  become not implicitly accepted aliases.
- &str print is finally validated: no prior conversion to char
  necessary to transmit UTF-8 text.

<a id="interactions-et-contre-exemples-prévus"></a>

## Interactions and counter-examples

Documentary analysis scenarios not implemented:

1. "summer": byte_len=5; valid char indices 0/2/3, readable continuation in u8
   but tank_at refused with NotCharBoundary; end and exceed OutOfBounds.
2. Cross-border clearance allowed; cut in the middle of a refused encoding before
   Exposure of a view. Do not turn a &str annotation into a hidden loan.
3. from_str on vacuum/multiple scalar values; case combining visually
   unique but composed of several tanks; independent result of storage.
4. from_utf8 on valid and invalid bytes; no automatic replacement;
   mutation/drop of rejected source bytes if a view still needs to be used.
5. push/push_str with exactly sufficient capacity and overtaking: none
   partial writing or moving of existing elements.
6. pop on vacuum and multi-byte tank: remove only a complete tank and only
   not to release the entire region prematurely.
7. valid continuation replace_byte, negative/end index, invalid result:
   Keep the text in full in case of error.
8. replace_bytes transforming C3 A9 into 61 62: a valid grouped result while
   unit steps would be invalid; number of chars variable, fixed size.
9. Off-limit block source, overflowing interval calculation and borrowing source
   the recipient: controls and restrictions on usual arguments to be composed.
10. &mut text[i] and text[i]=byte refused; no raw access to the Internal Vector
    ne doit permettre de casser l'invariant UTF-8.
11. Independent duplication of a thong, destruction of the original and survival of
    la copie ; copy générique refusé directement et dans un champ de structure.
12. Subviews, child transfers → parent and async captures: apply the
    provenances et réservations existantes sans considérer leurs anciennes
    preuves comme une couverture des nouveaux types.

These scenarios are not defects observed in a String compiler.

<a id="points-ouverts-et-limites"></a>

## Open points and limitations

Utf8Error, details ABI, regional protocol and definitive failure policy
The discussion confirmed the border controls
and notation, but the policy of stopping by cutting error was proposed
before notation correction without separate agreement then; it is retained
as a proposal, not as an additional decision invented here.

Vector's API<T> is the next construction site: its empty construction without defects
T is not approved by this only deposit.
additional String should not lead to replay all arbitrations
memory; only new decisions must be presented to the user.

<a id="vérifications-de-cette-passe"></a>

## Checks of this pass

Document check covers TX identifiers, their matrix entries,
files targeted by local links and code block delimiters.
He doesn't check Markdown anchors or snippet semantics.
Completed: 20 unique TX identifiers, 20 lines corresponding to the
N status, 162 local links to existing files and code blocks
in the six documents concerned.

Compiled or executed programs, language tests, independent models,
generation, mutations, sanitizers and performance measures: none in this
pass. TX1–TX20 remain unimplemented and unverified by execution.
O(1)/O(n) discussed are algorithmic objectives, not measured results.

<a id="littéraux-statiques-passage-de-vues-et-affichage"></a>

## Static literals, passage of views and display

The compiler encodes the UTF-8 literals in static tables C
immutable and represents them by address and length in bytes.
Viewing goes through parameters and &str returns, without
allocation in a pool. Length and print use size
The analysis refuses an implicit conversion to Int and
decoding of an isolated Unicode substitute. The prototype chooses
JSON escape sequences for the literals.

The C11 tests under UBSan cover the multibyte text, a
value on four bytes, a combining character, text
empty and a zero byte inside. The result of a branch and
the reassignment of a mutable link retains the view type.
The width model has exercised ten scalar boundaries
Unicode. The mutation that stops the display on the first byte
None is detected.

The cover covers TX1, TX3 and TX20 for static views.
Cuts, indexing bytes, tank and thong remain open.

<a id="indexation-doctets-dans-les-vues-statiques"></a>

## Indexing dss in static views

TX2 and TX5 move forward with `u8` and `&u8` for readings of literals,
of links `&str` and function returns `&str`. Both modes
The C uses the same criteria as those used in the contract.
`uint8_t` and a constant byte-by-by pointer. The view is evaluated and
The backend checks the terminals before any
pointer arithmetic, including to obtain a reference.
known negative index or outside of a known literal is refused before
The other accesses are kept in C.

The borrowings here are only on static bytes.
liaison `&str` retains the validity of the loan taken from its former
Bytes. Future dynamic storage borrowings will have to follow the
source and the life of the storage.

Five targeted tests have been successfully completed.
a valid path through several calls, ten programs refused
by the auditor and four native stops with the expected diagnosis
and without diagnosis UBSan. The other two check the literals, the
transmission of views and their diagnoses. The native test also validates
the order of assessment of the view and index with a trace of calls.

Tables `[u8; N]`, the general general and operational `u8`,
recipients of text composed directly of a `if`, `char`, the
cuts and cuts `String` The state of the
backend for `&u8` the static does not constitute proof for the
dynamic length views or borrowings in recyclable regions.

The three new tests also passed after the last adjustments
compiler. The following tables fixed, arguments, if expressions,
The 68 tests of fixed tables were launched.
The 97 tests of the other group were also successful.
ASan and UBSan and the transfer of the superior guard were launched
Their final result remains to be recorded.

<a id="décodage-de-char-dans-le-c-émis"></a>

## Decoding of tank in the C emitted

TX2, TX3, TX6, TX7 and TX20 now have primitives in runtime.
The scalar is represented by `uint32_t`. Both conversions produce
internal value and status, without pool. Decoding implies a view
UTF-8 valid. Checks the index and the border before reading the scalar,
and control that its width holds in the remaining bytes.
will be separately established for future entry `str::from_utf8`.

`PYTHONPATH=tests:. python3 -m unittest -v test_utf8_runtime` has passed under
Clang C11 and UBSan blocking, at `-O0` and `-O2`. The model encode 522 values
with Python, 12 of which are selected and a seed sample 1439 filtered for
It compares decoded values, their widths and the
Bytes printed. It exercises each continuation position, the terminals
negative and final, empty text and conversion of a multiscalar text.
The test directly calls the helpers in the C produced by
`compile_source("")`.

Four temporary C mutations were detected at both levels
d-optimization. They allow the index equal to the length,
a continuation position and multiscalar conversion, or truncate
High bits of a scalar of four bytes. Variants of l'oracle
are identical between executions.

The guy `char`, signatures `Result<char, E>` and their `match` restent
The success measures the C paths of this cycle.
The calling, return and connection paths of the future type in Crust
have to be verified by source programmes.

The five existing source tests on literals and static indexing
have again succeeded with these primitives present in the generated C.

<a id="appels-résultats-typés-et-match-depuis-crust"></a>

## Calls, typical results and match from Crust

TX2, TX3, TX6, TX7 and TX20 are now accessible from the language.
`char` is copyable and distinct from `Int`, of `u8` and `&str`.
`char_at` and `char::from_str` produce two distinct types of result
in annotations and contracts, with the same representation C internal.
The instruction match accepts recorded forms `Ok(c)`,
`Err(Type::Variante)` and the final arm `_`. The compiler checks
The completeness, the family of error and the duplicated arms.

The subject is evaluated once in the current scope.
lowers it in a synthetic block, which wrongly refused to
transfer of an allowance in the appeal which calculates the index.
now stays in the source scope and all arms have the same
The scalar of an Ok arm is copied, without prolonging
I'm borrowing from the view.

Five targeted source tests and model C of 522 scalars were successfully tested under
UBSan blocking. Native programs exercise all the variants,
widths from 1 to 4, zero scalar, passage and return by function,
and the destruction and reuse of a capacity pool 1.
The mutation that reintroduces a scope
synthetic for late arms is detected by the transfer test
with a diagnosis on the direct parent.

The regression suites arguments, conditions, effects, results and
The coverage covers both results.
UTF-8 and the training match. The expression match, the general capture
`Err(e)`, other results specializations and views from a
dynamic storage remains to be covered.

<a id="découpes-de-vues-statiques"></a>

## Static view cuts

TX4 supports `&texte[debut..fin]`, `&texte[..fin]`,
`&texte[debut..]` and `&texte[..]`. The receiver and the explicit terminals
The C checks the relationship between the two.
the terminals, then the UTF-8 borders, before forming the pointer.
The view keeps the address of the original bytes and a adjusted length.
The end is an authorized border, including for an empty cut.
The `&` is required and the view is immutable.

The provisional policy takes over E2. A literal pillar clearly
invalid is refused by compiler. An invalid dynamic terminal
causes a stop with diagnosis before any access.
découpe reste à arbitrer selon la note de TX4. La règle normative est
unchanged.

Seven targeted tests have been successfully completed, covering the old operations
UTF-8 and three new source tests with nine statically rejected cases,
five native judgments expected and the record of the orderly assessment.
interactions include visual reassignment, function return,
interlocking cutting and `char_at` on the result. L-oracle C under Clang and
UBSan blocking to `-O0` and `-O2` compared the address and length of the
91 explicit intervals and 13 suffixes from 13 calculated boundaries
Two temporary mutations omitting custody of the
The beginning or end were detected. Each made accept a view
truncated to the position of a continuation byte.

The fixed array suites and conditional expressions were
The views behind the `String` and tables
d-bytes remain to be dealt with with their own life-span constraints.

## Validation d’octets bruts

TX8 has the C validator `text_validate_utf8`. The bounded decoder shared
with `char_at` and `char::from_str` refuses truncated sequences,
bytes of continuation incorrectly placed, over-long encoding,
substitutes and scalar beyond U+10FFFF. Validator reads
only the bytes of the segment provided and advance one scalar at a time.
It does not allocate or correct the content.

L’oracle `test_validation_agrees_with_python_on_raw_bytes` compares C to
strict decoder Python on 65,536 two-byte sequences, 20 cases
Targeted and 1,024 sequences generated with seed 2671. Three tests
additional limit the same buffer inside a valid scalar,
with the following bytes still present in memory.
decoding, display and address of the cuts continues to run.
Both C tests passed on Clang C11 and UBSan blocking to `-O0` and
`-O2`. L-oracle detects four mutations at both levels of optimization
of the C emitted, removing the minimum length of the guards,
d) excluding substitutes and continuation d)

The predicate is internal to C. `str::from_utf8` remains to be exposed with a
typed result and a loan linked to the source of the table. As long as
The analysis does not propagate this source, integration should not
assimilate the obtained view to a static literal.`Utf8Error`
remains open in accordance with TX8.

The complete selection of the UTF-8 source tests and the two oracles C
also completed without failure.
tank and cuts remain in progress.

## Tableaux fixes d’octets

Tables `[u8; N]` use boxes C `uint8_t`. A constant
decimal or hexadecimal can initialize a box in context `u8`
if it is between 0 and 255. `Int` obtained at
The execution remains distinct. The annotation also fixes the length.
Reads, scripts and replacements re-use controls
fixed tables. Calls and returns use the same modes
d , borrowing and transfer as the tables d , l , borrowing from a box
remains attached to its table and follows the existing last rule
utilisation.

Seventeen targeted tests were successfully tested.
literals, repetitions, empty tables, readings and writings
via calls, transfer of the returned table and nine rejection cases,
of which shrinkage, exceedance and writing
A probe from the C emitted checked the
`sizeof([u8; 2]) == 2` and observed bytes 195, 97, 97 and 98
under Clang C11 and UBSan to `-O0` and `-O2`. It detects a
mutation replacing the byte transmitted to write by zero.

92 cycle regression tests cut and 144 of the tank cycle
have successfully completed their respective versions.
fixed tables, constraints and effects are re-launched for this cycle.
The connection of `str::from_utf8` The signatures are still to be done.
d) borrowing to a local `u8` and tables of such
références restent aussi à couvrir. Le `&u8` de l’indexation d’un
`&str` The analysis of the static loan structure is still distinct from the local loans.

<a id="résultat-local-de-strfrom_utf8"></a>

## Local result of str::from_utf8

TX8 is accessible from Crust for a shared loan of `[u8; N]`.
Local result can be named or analyzed directly with `match`.
The arm `Ok(vue)` receives the address and length of validated bytes.
`Err(_)` treats failure without exposing a detail of error still open.
The status of the C is internal. The empty table uses the address of its
sentinel byte C with a zero length.

The verifier links the result, view, cuts and references
d-bytes derived from the routes of the table. A local alias keeps
The expression of indices and markers keep the borrowing
during their calls. The analysis allows a mutation after the last use
and refuses to mutate a source still in use. Static views keep
The parameters and cross-processual returns of the
the reassignment of such views and temporary tables
as source still to be covered.

The 19 targeted tests have been successful. The source program combines derived view,
mutation after last use, failure of validation, repair then new
validation, and borrowing an empty array passed by function.
The C-scanned invalids are rejected statically.
differential validation, pointer identity and length on success,
and a result without a view over failure, under UBSan to `-O0` and `-O2`. The mutation
the compiler who makes the borrowings associated with the profit and loss inactive
derived views have made accept two programs that the test requires to refuse.

The 115 regression tests of the d-bytes cycle were successful.
The extended suites were relaunched for the version with `str::from_utf8`.

<a id="relais-interprocédural-des-vues-utf-8"></a>

## Interprocessual relay of UTF-8 views

Calls accept views `&str` and references `&u8` issues d’un
validated table. Each borrowed argument reserves its source during
The two orders of conflict
between a view and a mutable loan of the table are checked.
C parameters retain the representation of the view or pointer.

A function that relays these arguments with a return `&str` ou `&u8`
keep the paths of borrowing on the calling side. In this pass,
The appeal takes the conservative union of all arguments UTF-8
borrowed, including for a result that depends on one
or which is static. L-inference of provenance by parameter
The contract for a return directly from the
validation of an array in the body of a function also remains
Out of this pass.

The 21 targeted tests have passed. The new native course combines
two cutting relays, a d-byte reference return and a mutation
after last use, under UBSan blocker. Five invalid variants
The transfer which withdraws the loan is rejected by the auditor.
the framework of arguments made accept the writing in an argument
and the passage of the source by mutable borrowing after the sight.
The 160 regressions of the previous cycle have been successful.
arguments, modular calls and fixed tables are restarted.

<a id="provenances-des-retours-utf-8"></a>

## Sources of returns UTF-8

Return contracts `&str` and `&u8` The parameters of the
The result may depend. Cuts, borrowings d
relays and junctions retain these dependencies.
has an empty set. The call solves the provenances on his arguments,
and C emission checks durability and roots when a view
The success of the loan is dismissed. `str::from_utf8` peut maintenant
be returned to `&str` when the table is borrowed from the parent.
A local or temporary target cannot come out by this return.

The 23 targeted tests have been successful, including a relay from a
The change in the first two years of the transition from an independent argument to a table taken
l , display of result, a static return, and two refusals to write
on possible targets of a junction. The C emitted displays the
Bytes expected under UBSan. The mutation of the junction calculation which
guard only the provenance of the first arm has made accept
writing on the second table during his loan.

The 116 regression arguments, modular calls and fixed tables of the
The regressions of the analyses and the previous cycle have been successful.
calls are restarted for this cycle.
`Result<&str, Utf8Error>` and the reallocation of views
borrowed remain open.

<a id="transport-du-résultat-de-validation"></a>

## Transport of validation result

`Result<&str, Utf8Error>` can be received and returned by a function.
The contract spreads the paths of the picture or the result received.
d-an argument protects bytes until call. At the junction of a
expression `if`the auditor requires the same type and retains all
the paths of branches that provide a value. A view or a
result that depends on a local table on the arm cannot come out.

The 26 targeted tests were successfully tested under UBSan.
exercise the return validation, relay the entire result, its
treatment in another function and branches of success and failure
after modification of the bytes. The verifier refuses both entries
in possible tables before the last use of the result, both
output from a local array and mutation in the next argument.
The transfer abolishes the reservation of results during the
preparation of arguments has made the last program accept invalid.

The 124 regressions of the source cycle have been successful.
arguments, modular calls, conditional expressions and results
The re-allocation of views and results
borrowed as well as temporary table borrowings in this API
I'm sorry, but I'm not going to deal with it.

<a id="réaffectation-de-vues-et-de-résultats"></a>

## Reassignment of views and results

Mutable links `&str`, `&u8` and `Result<&str, Utf8Error>` peuvent
Change source without changing type. A link can pass from a
static view from a borrowed view or vice versa. The new provenance
is checked in the receiver's scope. The already created aliases continue
a junction keeps the loans from
each path that continues, including if the link was static before
the branch. A view used at the next iteration remains reserved
on the loop cover.

The 29 targeted tests were successful.
source changes of the three types, a junction, an old alias
and a loop. Counter-examples prohibit writings before the
last use and output of a view on a table declared in a
The mutation that fails to reach the provenances when
the connection was static made accepted two invalid writings.
The case of reassignment to a sustainable table, previously excluded from the
prototype, is now covered by acceptance tests.

The 97 regressions of the transport cycle of the result were successful.
fixed array suites, mutability, conditions and loops are restarted
for this cycle. Validation of a temporary table is still to be covered.

<a id="validation-dans-linstruction-qui-crée-le-tableau-temporaire"></a>

## Validation in the instruction that creates the temporary table

A temporary table can be validated in the subject of a `match` ou
in a chain of calls of the same instruction.
The result, the view and its derivatives. In the match, an internal receiver
allows use in arms while refusing assignment to a
The connection of the scope which contains the instruction. The storage C is created
in this scope. A temporary table created in a conditional arm
remains in the corresponding C block, and its view cannot come out.

The 31 targeted tests have been successful. The new native case with UBSan reads
the view directly in a match, in a nested call and after
Four illegal exits are refused, by liaison
persistent, reassignment from arm, return to function and
The transfer allowing any link to the
The first two programmes were accepted by the temporary staff.

The 149 regressions of the reallocation cycle have been successful.
fixed tables, arguments, modular calls and expressions
conditionals are being restarted for this cycle.

<a id="construction-croissance-et-destruction-de-string"></a>

## Construction, growth and destruction of String

`pool<String>` contains the stable descriptors. `p.new()` construit
un texte vide. `byte_len()`, `push_str(&str)` and `push(char)` are
available in Crust. The addition requires a mutable receiver and uses the
same scalar encoder as the display. Storage reserves the
full addition size before copying bytes. Destruction
restores growing storage before the descriptor slot, y
The following are the main features of the project:

Internal byte storage uses growth primitives.
Integration with a `Vector<u8>` generic remains to be done.
annotation, the prototype temporarily reserves 1 MiB, on the front
amount of pool storage if it is free, if not on a beach
The contiguousness and order of the bytes motivate this choice of
up front. With annotation, the first template is shared
by the pool and different templates use a dedicated region.
The transfer carries the descriptor by its address, with the
the same limit and the same bytes.

The 46 targeted tests have been successful.
combine construction in a function, transfer by borrowing,
transfer from an annotated block, destruction and reuse.
invalid forms are rejected. Test C checks bytes,
exact limit, the diagnosis of exceedance, stable address and
the return of the slot, under UBSan to `-O0` and `-O2`. Deux mutations
temporary are detected, incomplete copying of an addition and
The 84 regressions of the cycle
of previous placements have succeeded.

The views of String, `pop`, replacement of bytes and the
explicit duplication still to be implemented.
The results of the survey were not measured.

The 107 regressions destruction, pool requirements and analysis
contracts in this cycle have been successfully completed.

<a id="vues-de-string-et-provenance-interprocédurale"></a>

## Thong Views and Inter-Procedural Origin

Cuts `&texte[..]`, d  , readings and references
shared `&texte[i]` use the bytes of the String in place.
The same border and terminal controls apply to
The view descriptor retains the allocation of the thong and
the reborrowing string. Functions can return a view or
a byte borrowed from a parameter `&String` ou `&mut String`.
Transfer, transfer and destruction are still denied
as long as such a loan is still to be used.

Contracts distinguish a static view from a view backed by a
an allowance when the actual source is known at the call.
They spread the dependencies to the pools for the views
and d-byte references. Tests refuse the reset followed
d) a reading and accept the reading followed by the reset.
mutation removing symbolic source of UTF-8 parameters
had two invalid programs accepted that read after
a reset in a function called.

Test C in UBSan checks the identity of the viewer on
content of a String. Crust programs exercise the return
by contract, last use, shared indexation, duplication
explicit towards another Thong and independent destruction.
Counter-examples also cover the copy from a view of the
receiver itself, the exit of a view of a local thong and
The operations `pop` and
controlled replacement remains to be covered.

The 49 targeted tests and 132 regressions arguments, effects,
constraints, results, modular calls and destruction have succeeded.

<a id="retrait-de-scalaire-et-remplacement-contrôlé-doctets"></a>

## Scalar withdrawal and controlled replacement d

`String.pop()` retourne `Option<char>`, with `Some(c)` ou `None`
The result is independent of the String.
Runtime decodes the last entire scalar and then backs the cursor
The bytes retained retain their
address and suffix can resvir.

`replace_byte` and `replace_bytes` check the terminals and then validate
the forward-looking text with the UTF-8 decoder, before writing.
Implementation currently runs the entire text and uses
a four-byte window. The old byte is returned for the
Unit version and success of the group replacement is `Ok(())`.
Constants from 0 to 255 are allowed in context `u8` for
`replace_byte`. The group replacement takes a fixed table
d    , no byte is moved and the length is kept,
including when the number of scalar changes.

The two oracles C under UBSan to `-O0` and `-O2` comparent 120
addition/retirement operations on each of the two storages and 183
Python models are replaced. They check the status,
the old bytes, length, address and wholeness of the
content after success and error. Both mutations
temporary, cursor not back after pop and validation omitted
before replacement, are detected.
exercise the typical results, destruction after pop,
group replacement of two bytes that changes the number of
scalar and conflicts with a still used view.

The result match accepts qualified error variants
of the `ByteReplaceError`. General patterns with error link
and the expression match remain open. The larger regressions
of this cycle have been launched.

The selection of 55 UTF-8, String and Growth tests was successful.

<a id="match-expression-sur-les-résultats-et-options-utf-8"></a>

## Match expression on UTF-8 results and options

The existing Result and Option patterns may provide a
value from their block. The junction requires the same type for the
branches that continue and retain their provenances.
can leave the function before providing a result.
is evaluated once in its source scope, which keeps
the transfer of permitted arguments.
One alias reassigned by one arm remains followed by another
in the continuation of the encompassing expression.

Four targeted tests were successful, including three native cases with UBSan.
They cover a transfer and re-use of his slot during the
match, early return, joker arm alone, junction of
views of String, and the refusal of a view on a temporary
The empty joker arm test first
detected an internal compiler failure. This case is now
The mutation that ignores the
After the match, the scope continues to accept a mutation
incompatible with a reassigned view in the arms.

The 188 regressions of the pop cycle and replacements were successful.
The continuation of fundamentals and oracles C are revived.
The reasons that bind an error remain to be covered.

<a id="concaténation-avec-transfert"></a>

## Concatenation with transfer

`destination.merge(-> source)` prepare a mutable receiver,
receives the source by explicit transfer and adds its bytes.
After addition, the source is destroyed and its slot can reshrunk
in its original pool. The same capacity control precedes
copy. A view still used, a source identical to the
Receivable and re-use of the transferred name are denied.

The 14 Thong targeted tests were successful, including the concatenation of
Two different pool thongs and four invalid cases.
141 tests of the fundamentals and oracles of the previous cycle
successful. Regressions of destruction, effects and contracts are
The Thong storage now uses the same
kernel C that future vectors, described in
[FOUNDATIONS_CYCLE.md](FOUNDATIONS_CYCLE.md).

The 112 regressions of this cycle have been successfully completed.

<a id="validation-dune-tranche-de-vecteur-grandissant"></a>

## Validation of a growing vector slice

TX8 accepts a split tranche of `Vector<u8>` in
`str::from_utf8`. A view from a descending front keeps its
The validation and the operations of the
read through bytes in logical order. The decoder uses
not more than four temporary bytes for a scalar and continuous view
designate the original storage.

The Crust test covers the return of `Result<&str, Utf8Error>` through
a function, cutting, `char_at`, addition to a `String` and
rejection of a truncated scalar. An insertion in the vector is refused
as long as the view is still to be used and allowed after its last use.
The three targeted tests `from_utf8` go under Clang C11 to `-O2`
with fatal UBSan.

The independent model uses the strict decoder of Python. The C test
65,536 pairs of bytes on both orientations and checks the
original bytes addresses in case of downhill success. It tests
also 1,024 seed sequences 2671 and 20 fixed cases in both
The two tests runtime move to `-O0` and `-O2` sous
A mutation that erases the orientation of the view is fatal UBSan.
The extended regression ratio is currently being developed in the following areas:
`/tmp/crust-tx8-vector-regression.log`. The previous regression of
T6 has passed 338 tests.

<a id="remplacement-atomique-depuis-une-tranche-doctets"></a>

## Atomic replacement from a slice of bytes

TX16 accepts a split tranche of `Vector<u8>`, y compris
as a function parameter. The C validates the forward-looking text
in the logical order of source bytes before any writing.
The adjacent sources keep the consolidated copy.
descending, the C publishes the bytes in logical order after
the same validation.

The three targeted Crust tests pass with Clang C11 to `-O2` sous
UBSan fatal. New case checks for replacement of two
bytes, InvalidUtf8 and OutOfBounds errors, replacement
empty, stable address and refusal of a transfer during a
The independent Python model (grain 3581)
calculates the content and status expected after each of the
183 operations. Downward instalments alternate with the
historical paths, and the model also checks the length and
the address after each operation. It passes UBSan fatal to
`-O0` and `-O2`. A mutation that reads the descending source in
physical order fails on both levels.

The increase in the number of people in the EU is now in progress.
`/tmp/crust-tx16-slice-regression.log`.

<a id="contiguïté-des-string-dans-les-régions-hautes"></a>

## Contiguity of the Strings in the upper regions

The TX21 audit confirms that the existing implementation reserves the
annotated classes of `String` the top side of the datastack.
C checks the position of the classes, the contiguous bytes in the order
the stability of the beginning of the sight, re-use and refusal
the extended test also checks two Strings
The second uses a dedicated stack when the forehead is not marked.
amount of the common stack is occupied, and both texts remain
independent.

Test C passes Clang C11 with fatal UBSan at `-O0` and `-O2`.
Two mutations are detected at both levels, the placement of the
regions at the beginning of the free space and the authorisation of the front
The Crust scenario of transferring a
Annotated thong and re-use of his pool also passes.
adds coverage to existing behavior. TX8 regression
has passed 275 tests. The growth suite and UTF-8 is underway in
`/tmp/crust-tx21-placement-regression.log`.

The growth suite and UTF-8 passed 22 tests in 24.280 s.
