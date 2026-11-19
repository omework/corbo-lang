[Français](INLINE_VECTOR_REPLACE_CONTRACTS_CYCLE-fr.md)

<a id="cycle--contrats-de-replace-des-structures-en-ligne"></a>

# Cycle — Online structure replacement contracts

<a id="périmètre-et-statut"></a>

## Perimeter and status

Synchronous extension of INLINE_VECTOR_REPLACE_CYCLE.md. VE1–VE3, H1, U1,
B1–B5, T4/T5/T6, F2–F4 and ST17/ST18 remain unchanged.
VALIDATION_GUIDELINES.md and design-buffer/decisions.md relus ; rules of
vectors and their dependencies are included in this continuous work.
No new normative semantics. The global construction site remains open.

Snapshot initial : `/tmp/crust-before-inline-vector-replace-contracts`.
Fixture `validation/inline-vector-replace-return.crust`refused before
batch, now renders 7 then 9 in the C executed with UBSan.

<a id="réalisation"></a>

## Implementation

The contract separates the identity of the local holder from the value of the fields in each
arm. Replaces reuse the porter of the input; Ok contains the old box,
Errating the entry unchanged. Two charges can share this bearer without sharing
The results and constraints analyses keep their graphs of fields.
these separate loads, including joints and relays.

The placement reserves the builder entering the appellant's storage
the local result. The reserved size is that of T, not
The result<T,T> syntax type. An input transmitted as a parameter retains
The vector box receives a separate identity,
linked to the storage of the vector; its fields keep their targets clean.
The enterr's local storage obligations are extended into the contract.
The join of a result retains the distinction T/A<T>.
The parameters and returns signatures Result<T,T> also bear this
distinction, including in the symbolic verification of bodies.

<a id="validation-ciblée"></a>

## Target validation

`-contract-targeted-fifth.log` 12 methods, 9.053 s, code 0, O0/UBSan
(the seven existing local methods and the first five methods of contracts).
`-contract-branches-second.log` : six methods of contracts, 4,534 s, code 0,
After adding conditional returns. This last module runs 11 programs
C allowed and four variants refused to both verify_program and
compile_source.

Cases allowed: fresh or named construction, return via relay, Ok and Err,
conditional returns, input transmitted by parameter, fields A<Int> or &Int,
read after drop of vector, single clean and re-use of two slots.
Reuse of the transferred input, transfer of targets before
the last use of the result, declaration A<T> for a local result T.
Reset is removed from the current profile.

The first newspapers keep the defects encountered: local porter
combined with a block allowance, merging the charges using a
representation specific to a single analysis, arrow of a returned call not
recognised, local obligation absent from the analysis filter and block identity
These defects are corrected in the target.
Three fixture errors were also corrected: harness method
missing, text replacement not corresponding to the spaces of the fixture,
and parameter A<Int> writes Int. The first conditional test used Bool,
while the language type is bool; the fixture uses an Int compared to 1.
The expected outputs and rules have not been changed.

The transfer of the local Result itself to a function revealed a final
deviation: the storage type of Result parameters was still implicitly
the allocation of a grant. Signatures, symbolic entries and obligations
now carry the declared storage type.
`validation/inline-vector-replace-result-parameter.crust` and its initial refusal
`-contract-result-parameter-baseline.log` are retained.

Final target: `-contract-graph-targeted.log`, **eight methods, 7,461 s, code 0**,
O0/UBSan ; **17 programmes C admis** and **six alternatives refused** both
entries. The supplements cover the Result transferred as a parameter, its fields
owners/borrowed and both arms, T/A<T> refusal and absence
Back arrow.
The C retained in `validation/inline-vector-replace-contract.c` montre que
the appellant reserves sizeof(int) for Point, that the callee constructs the inlet
in local_output then returns this carrier after vector_replace.

<a id="régression-et-limites"></a>

## Regression and limitations

Premier passage O2/UBSan : **169 methods, 129,800 s, code 0**. The 46 fingerprints
The two methods then added for the parameters are unchanged.
Result was not part of this first passage.
The final passage was interrupted at a resumed session: the handle
64303 was not found, the journal did not contain a balance sheet and the file
This incomplete passage, kept under the prefix
`validation/inline-vector-replace-contract-final`, is not counted as successful.

The full replay has ended: **171 methods, 160,035 s, code 0**, O2/UBSan.
The 46 prints are unchanged during execution.
Initial fingerprints and integrity result use prefix
`validation/inline-vector-replace-contract-replay`.
The selection covers the target, push/remove/pop and fields of online structures,
Async cases, typical trades and storage obligations.
Diff and manifest of change: `-contract.patch` and `-contract-changes.json`.
The initial selection uses the prefix `validation/inline-vector-replace-contract`.
The harness compiles in C11 with pthread, Wall/Wextra/Werrar and fatal UBSan.

The passage of this replacement in an async state remains open.
`validation/inline-vector-replace-async.crust` is refused both entries
(`-async-baseline.log`) : the lowering still awaits an A<T> element.
This is the next connection identified.
contracts executed here do not prove all compositions of graphs and graphs
The unknown positions remain conservative. No general evidence
or extensive adversary campaign; the state of the independent lab is not assumed.
