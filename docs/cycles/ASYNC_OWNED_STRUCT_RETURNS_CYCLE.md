[Français](ASYNC_OWNED_STRUCT_RETURNS_CYCLE-fr.md)

<a id="retours-async-de-structures-propriétaires"></a>

# Async returns of proprietary structures

<a id="règles-et-périmètre"></a>

## Rules and scope

This lot applies existing rules T1/T6, D1/T11, B1/B2/B4, ST1/ST7/ST15,
L1/L2/L6 and AS5/AS8/AS9/AS10/AS12/AS13. Drafts 01, 03, 04 and 05 are
No normative rules are amended.

A task may make a proprietary structure received by transfer, including
a finite graph of fields A<Int>, A<String>, A<Vector<Int/u8>> and structures
The return shall keep the allowance and its addresses.
Then clean the complete graph. The same result can pass through expectations
a factory, a task relay, a Result returned by a
synchronous function, a Result transmitted to a task and an nested envelope.

The Async bodies do not yet freely construct these structures or their
pools. Graphs containing loans, general enums, signatures
public running::Handle<A<Structure>> and the passage of the proprietary structures
The synchronous auxiliary from async remain to be connected. This batch does not close
not the general construction of aggregates.

<a id="défaut-initial-et-implémentation"></a>

## Initial failure and implementation

The [minimum programme](../../validation/open-owned-async-struct-return.crb) was
The diagnosis is kept in the
`validation/owned-async-struct-return-baseline.log`. Runtime already had
representation and destruction required; static monitoring of the
The result was incomplete.

Each task and handle now, separately from its catches, keeps the
The contracts set out these paths and
The auditor reconstructs the graph possessed by the
after join and preserves it when extracting the Result, returns of
functions and junctions if, match or break. The task contract and the
source constraints retain the same distinction between root and
The concrete origins are preserved at the creation and the
symbolic reconstructions use the sources of the contract.

The Result<A<T>,runtime::Error> syntax is recognized for nominal types;
unknown types are refused. Enlargement does not allow to manufacture
a result whose source of the fields is absent. The backend keeps
its explicit restrictions on unsupported graphs.

<a id="scénarios-et-oracles"></a>

## Scenarios and oracles

The 12 methods of `tests/test_async_owned_struct_returns.py` exercent :

- normal return, rejected launch, absence of marker and unknown type;
- Direct waiting or named with reading then new transfer;
- factories, relays of instances, conditional choice of tasks;
- Result transmitted to a helper, another owner helper, then to a task,
  and two levels of Result waiting;
- output of Result by if and break, then projection of the possessed field;
- last use of a loan from the field before drop, with neighbour refused;
- life of the pool of a field independently of the root pool.

A finished model places each of the three pools of the graph Root → Child → Int dans
the outer scope or in the block producing the Result. The eight provisions
must accept only the one where the three pools survive the result.
The programme is therefore accepted and seven rejected.

Two C probes have an unlaunched task: destruction at its suspension,
or chased until reset. They check the root and field address,
one destruction of each, the order of the child before the parent and the re-use
They do not introduce any cancellation of an executed launch.

A contract oracle verifies two separate source obligations: the pool
provided to an old reset must be distinct from that of the result and the result
of its field `.value`. This test uses expressly `allow_legacy_reset=True` ;
restet remains removed from normal profile. The expected is for the inferred contract,
independent of the C generator control paths.

<a id="exécutions-et-corrections-intermédiaires"></a>

## Interim execution and corrections

Clang C11, pthread, Wall/Wextra/Werror, Wno-unused-function, UBSan fatal.

- `owned-async-struct-return-initial-o0.log` : four methods, one error
  a snippet without a receiver or marker at the exit of the snippet
  The snippet is corrected according to T1/T6, without relaxation.
- `owned-async-struct-return-second-o0.log` : four successful methods.
- The newspapers `third-o0`, `fourth-o0`, `helper`, `fifth-o0` and `helper-second`
  keep the refusals encountered during connection: downward import
  missing in branch test, missing Result return marker,
  Nominal signature not recognized, graph and variant absent from contract.
  The first two defects are in the snippets, the following in the
  compiler. `helper` and `fifth-o0` did not require O0;
  their suffix does not constitute proof of the level of optimization.
- `owned-async-struct-return-expanded-o0.log` Nine methods, 5.181 seconds, OK.
- `owned-async-struct-return-contract-o0.log` 18 methods, 11,913 s, OK,
  after linking stress analysis, including previous catches.
- `owned-async-struct-return-final-o0.log` 11 methods, 9.024 seconds, OK,
  before the additional Result relay and the if/break junctions.
- `owned-async-struct-return-final-counted-o0.log` : 12 methods,
  7,845 s, OK on the final code; 19 native executions and 11 programmes
  The two courses, 22 refusal checks, were rejected.

`validation/owned-async-struct-return-mutations-final-o2.log` : baseline finale
of 12 methods, 8,226 s, OK; five injected errors detected:
pool of the field with the root, omit the graph at the shed, lose
fields in factory contracts, destroy before delivery, omit the
field constraint. Pool mutation wrongly admits several cases of the model,
the denial claims detect.
temporary; neither the oracles nor the rules are changed.

The five mutations in the catches remain detected:
`validation/owned-async-struct-return-previous-mutations-o2.log`, baseline of
nine methods, 11.265 seconds. This passage precedes the last relay supplement.

Broad Regression: `validation/owned-async-struct-return-regression-o2.log`,
86 methods, 115,948 s, OK. Selection: capture/return of structures,
constraints, manufacturing, direct returns, Expected results and Select results.
The loaded code precedes the last connection of the owner Result relay.

Regression to Final Code:
`validation/owned-async-struct-return-final-regression-o2.log`54 methods,
29,324 s, OK: catches, constraints, rules for using proprietary results
and public owners already supported. The 12 targeted tests
final and final mutations cover the complement of relays and junctions.
All final campaigns are completed with code 0; selections overlap.

## Limites

Modified Python files and new tests pass `py_compile`.
The differences from the beginning of the batch are kept in
`validation/owned-async-struct-return-*.py.patch`.
The models and probes are finished and do not prove the overall safety of the
language. No new ASan/TSan result is claimed.
constructions and signatures still open above still to be implemented;
The arbitrations of captured and lost Select handlers are not changed.
