[Français](PUBLIC_HANDLE_TYPES_CYCLE-fr.md)

<a id="type-public-des-handles--annotations-de-liaisons"></a>

# Public type of handles — annotations of connections

<a id="règle-et-périmètre"></a>

## Rule and scope

Draft 04 refers to the public type of task initiated by
`runtime::Handle<T>`, where T is its result, regardless of the type of frame.
This step makes this type usable as annotation of a synchronous link
or async. It does not complete generic contracts for parameters and returns.
No normative rules are changed.

The parser accepts the qualified name and its load, including references,
The audit compares the results of the audit with the results of the audit.
The internal representation maintains the task's stated result.
the concrete type of frame and its dependencies: the annotation does not change
its sources, borrowings, and waiting obligations.

The catches are not deduced from T. `Handle<Int>` peut encore porter un
Transferable borrowing until its expectation; `Int` only describes the final result.
`Handle<&mut Int>` retains the protections of the result after waiting and
`Handle<A<Int>>` keeps the pool of the allocated amount.
The launch results are still distinct from the T-carried out business results.

Example now executable:

```rust
async fn calcul() -> Int {
    yield;
    return 7;
}

fn main() {
    let execution: runtime::Handle<Int> = runtime::spawn(-> calcul());
    match execution.join() {
        Ok(valeur) => { print(valeur); },
        Err(_) => { print(99); }
    }
}
```

<a id="interactions-et-défaut-corrigé-pendant-lintégration"></a>

## Interactions and default corrected during integration

The annotations also apply to hand movements, exits from the
blocks, if and loops, as well as spawn_blocking and runtime::thread.
The first passage accepted direct connections but refused the three
forms of transfer calculated in an async body: a second control of the
The receiver didn't know the handle.
also the public type, without bypassing the cleaning or transfers.
Reproduction retained: `validation/public-handle-types-control-o2.log`.

Initial fixes did not comply with existing rules: Int as u8
instead of a verified conversion, flip-table without arrow, pattern
`Ok(mut view)` absent grammar and print of a u8 without explicit conversion.
They have been corrected; no normative change is resulting from this.
`…-initial-o2.log` and `…-targeted-o2.log` Keep these failures.

## Validation

Next `tests/test_public_handle_types.py` comprend :

- A matrix of six types (Int, Bool, u8, Void, &str, fixed array) in the
  two sync/async contexts, with exact and close annotations incompatible.
- Two different frames producing Int, explicit renaming, consumption
  and refusal to abandon the waiting period.
- Mutable captures with scalar or borrowed result: access and drop too
  early denied, access after waiting allowed.
- Result allocated: single destruction, re-use of pool after waiting,
  concurrent allocation in the reserved pool refused.
- Six launch/transfer forms in both contexts, with exact type
  and incorrect.
- Business result Nestled result, distinct from external launch error.

Clang C11, pthread, fatal warnings, fatal UBSan, O0 and O2.
final `validation/public-handle-types-complete-o0.log` and
`validation/public-handle-types-complete-o2.log`.
The seven methods are: 32.507 s at O0 and 32,800 s at O2.
29 C compilations/executions and 35 variants refused to both entries
check/compile, i.e. 70 refusal checks per complete pass.
A regression of 50 methods goes to 85,552 s at O2
(`validation/public-handle-types-regression-o2.log`) : obligations d'attente,
mixed contracts, results and pools injected. It was launched before the
last additions to the flow control test and their corrections, covered
through the final targeted passages.

Three mutations detected: failure of sync control, omission of controls
async and erasing dependencies of a capture during annotation.
Journal : `validation/public-handle-types-final-mutations-o2.log`.
The first selection of the last mutation failed on a result
borrowed before reaching the prohibited access: classified as inconclusive in the
initial log. The test added with scalar result isolate the protection of
capture and detect the prohibited access accepted wrongly, to both entries.
The tests are not weakened to allow the mutation to pass.

<a id="écart-ouvert-et-suite-de-lintégration"></a>

## Open gap and further integration

Update: the scalar gap below is now addressed by the
[cycle of public contracts](PUBLIC_HANDLE_CONTRACTS_CYCLE.md), also
The in-use diagnosis describes the state at the time of the int/u8 fixed tables.
end of this cycle of annotations, not the current status of these signatures.

`validation/open-public-handle.crust` requires two different async functions
producing Int and a common auxiliary receiving `runtime::Handle<Int>`.
The parser now recognizes this type, but the two entries still refuse
`type de paramètre inconnu 'runtime::Handle<Int>'`
(`validation/open-public-handle-after-parser.log`Historical signatures
`Execution<fonction>` do not meet this general rule.

The type of result, active catches, and the
before waiting and the provenances retained by the result after waiting.
Generic signatures, handle junctions from functions
The results of the study should follow this separation.
Their current refusal is not a new normative restriction.

No general proof of safety, additional ASan/TSan or verification
The public batch Handle and the overall objective
restent ouverts.
