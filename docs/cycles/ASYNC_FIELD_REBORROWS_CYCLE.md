[Français](ASYNC_FIELD_REBORROWS_CYCLE-fr.md)

<a id="réemprunts-de-champs-dans-les-états-async"></a>

# Reborrowing fields in the async states

Next: the return of these projections from an async function is now
connected in [ASYNC_FIELD_REFERENCE_RETURNS_CYCLE.md](ASYNC_FIELD_REFERENCE_RETURNS_CYCLE.md).
The refusal described below is retained as a historical finding.

Cycle of 7 November 2026. Application of ST6–ST9, ST11–ST12, B1/B2/B4a,
V4, AS2/AS8/AS12/AS13; no amended normative rules.

Int projections and explicit reborrowing of fields &Int/&mut Int
keep their paths in the state, arguments and children async.
The projected results of synchronous aids and methods shall be maintained.
The separate fields remain accessible. Export of a
alias keeps the targets sustainable, without requiring the survival of its local liaison.
A real local target is still refused.

V4 also revealed an unjustified restriction: a link `let` contenant
a &mut can change its target. Only the reassignment of the link request
`let mut`The relevant historical tests have been corrected according to this rule.

<a id="résultats-exécutés"></a>

## Implemented

- `async-field-reborrows-complete-o0.log` 13 methods, 29.970 seconds, OK.
- `async-field-reborrows-complete-o2.log` 13 methods, 18.158 s, OK,
  before adding the two direct helper/method arguments.
- `async-field-reborrows-method-argument-o2.log` : complement, a method,
  3,072 s, OK.
- `async-field-reborrows-final-mutations-o2.log` : baseline final of 12 methods,
  17,504 s, OK; 21 C-executions and 29 invalid programmes controlled by
  The two entries (58 checks) Seven injected errors detected: booking
  of the whole bearer, loss of descent, suppression of conflict, loss of path
  helper, loss of child result, incorrect offset, restored V4 restriction.
  Some detections are unjustified refusals, not memory violations.
- Independent model: 32 field combinations, alias, operations and latest
  of which 24 C executions and eight expected refusals.
  take back the compiler's decisions.
- `async-field-reborrows-native-o2.log` 256 methods, 209,022 s, OK.
- `async-field-reborrows-contracts-o2.log` 76 methods, 82,161 s, OK.
- `async-field-reborrows-struct-mutations-o2.log` : six previous mutations
  Replayed and detected.

The two larger regressions were launched before the last enlargement
the arguments of methods; the targeted complement and the final mutations
cover this change. Clang C11 pthread, fatal UBSan, O0/O2 according to the newspaper.
No new results found; no formal proof.

<a id="échecs-conservés-et-limites"></a>

## Retention and limitations

`async-field-reborrows-initial-o0.log` retains two corrected errors:
Export of aliases and restriction V4. `async-field-reborrows-targeted-o0.log`
keeps two fixture failures (helper absent), corrected and then reverified
in `async-field-reborrows-fixture-recheck-o0.log` Two methods, okay.

The programme `validation/open-async-field-reference-return.crust` remaining
valid but refused: the return of a projection from the async function
The appellant's contract is not yet connected to the appellant's contract.
The reference fields and general graphs remain open.
do not close the seven drafts or the overall objective.

The newspapers are under `validation/`. Implementation diff is retained
in `validation/async-field-reborrows-async_lowering.patch`.
