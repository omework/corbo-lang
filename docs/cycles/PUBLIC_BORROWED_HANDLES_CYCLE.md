[Français](PUBLIC_BORROWED_HANDLES_CYCLE-fr.md)

<a id="contrats-publics-de-handles-à-résultat-emprunté"></a>

# Public contracts for handles with borrowed result

<a id="règles-et-périmètre"></a>

## Rules and scope

AS12/AS13, RT5, MT3/MT5, B1–B5 and D1 require that targets be retained
the result after join, without prolonging catches that no longer serve.
This cycle connects synchronous signatures `runtime::Handle<&Int>`,
`runtime::Handle<&mut Int>` and `runtime::Handle<&mut u8>` the rules.
Normative rules do not change.

The public contract separates active catches during the execution of the
The results of the project are available from the following sources:
The relays do not recalculate the capacity of the shared result.
not as if they were new catches.
additional, pool or result pointer is not added to the runtime.

The compiler projects dependencies before deleting the concrete name of
The callers then use the contract without going through the body.
An empty opaque group is ignored; it does not create a fictitious target.
The C still extracts from the
the result before the frame release, with the existing representation
reference (allocation or inline address).

<a id="contre-exemples-et-corrections"></a>

## Counter-examples and corrections

- `validation/open-public-handle-borrow-contract.crust`previously refused,
  is now executed and displays 7. His old diagnosis is kept.
- A shared waiter could meet an exclusive empty group
  and refuse a valid program. Optional public groups are treated
  without inventing from where.
- The connection of `&mut u8` revealed the absence of direct borrowing of a
  Vector box in synchronous backend, and loss of its source in
  stress analysis. Int/u8 access evaluates and verifies the index,
  reserve the vector during this evaluation and then display its address.
- Symbolic storage of an byte parameter had a different link name
  the name of its scope entry. The search for the scope now uses
  the identity of the affair.
- An auxiliary turning the byte after join treated his symbolic target
  As an Int. allocation. Byte target now retains its representation
  inline. Constraints also distinguish bytes from fixed tables
  without pool source. Reproduction preserved in
  `validation/public-borrowed-handle-byte-finish.crust`.

<a id="vérifications-exécutées"></a>

## Audits performed

`tests/test_public_borrowed_handles.py` contains ten methods.
à O2 (`validation/public-borrowed-handles-byte-helper-o2.log`, 14,043 s)
and O0 (`validation/public-borrowed-handles-complete-final-o0.log`, 15,159 s).
Configuration : Clang C11, pthread, avertissements fatals, UBSan fatal.
The final complement of shared references to a table box or a table box
field inline also passes to O2 (`…-shared-inline-o2.log`, 2,216 (s) and O0
(`…-shared-inline-o0.log`2.348 s), in addition to the initial mutable variants;
it does not modify the compiler.

Scenarios include:

- Manufacture, two relays, auxiliary join, then use the result.
- Shared and mutable references, fixed array boxes, Int fields,
  shared fields detachable and reborrowable fields keeping a mutable carrier.
- Captures destroyed after join while the result remains used; drop,
  premature writing and historical reset denied to verification entries
  and compilation; access restored after last use.
- Calling opaque with contracts only, without function catalog
  or async definitions: one variant allowed and two refusals of premature drop.
- Reuse of pools, single cleaning of values captured after
  their last use, and refusal to launch injected.
- Octet returned from a vector or array box, written through
  the result; launch error returning another valid target.
- Int/u8 vectors: readonly/mutable borrowing, competing growth refused,
  transfer during the evaluation of the refused index, out-of-limit index
  provoquant un diagnostic runtime.

The independent model lists the positions of three allocations in relation to the
before join, the three catches must survive; after join,
only the two possible targets of the result must survive.
32 scenarios: six executed and 26 rejected, with both branch choices.
The model does not read either C or compiler summaries.

Regression of contracts, handles, fields and borrowed calls passes
97 O2 methods in 126.951 s, in
`validation/public-borrowed-handles-regression-o2.log`. It precedes the last
Byte/Table Supplements and vector boundary tests.
The additional regression tables/bytes/
vectors pass 122 methods to O2 in 85,743 seconds, journal
`validation/public-borrowed-handles-arrays-regression-o2.log`.
The public contracts awarded and borrowed are replayed after the
last corrective: 36 methods at O2 in 50.827 s, in
`validation/public-borrowed-handles-contracts-final-o2.log`. The Supplement
inline shared, added then, has its two targeted passages above.

The original logs remain in place.
`Ok(mut view)` not recognized, incorrect test class name or use
after drop provided by default by a test generator. Others were waiting
a different diagnostic wording. These fixtures have been corrected without
modify the rules and life expectancy.
Bytes described above were, however, implementation defects.

## Mutations

Campagne finale : `validation/public-borrowed-handles-mutations-final-o2.log`.
Five errors are detected in temporary copies:

1. Clearing of profit groups in the contract: premature drop accepted
   by the opaque caller.
2. Conservation of all catches after join: valid program refused.
3. Projection erasing when converting to the public type: result
   without target, detected by the internal invariant on the valid program.
4. Loss of exclusive capacity behind a shared result: access
   premature accepted in the neighbour with direct capture.
5. Wrong representation of the symbolic byte result: valid auxiliary
   refused as if he were to return an Int allowance.

The mutation that erases the source of a vector box in the analysis of the
contraintes **survit** the test chosen in the final state. The backend keeps
its own targets and verifications; no general equivalence is
established. The first campaign detected this mutation by incorrect refusal
before the processing of fixed tables is added.
two results, without reusing the old result as proof of the final code.

The mutation 4 initially survived with a named parent loan, which kept
The next direct capture test detects the fault.
For mutation 1, a second destruction in the test initially masked
the absence of refusal of the first drop. This redundant cleaning was removed from the
invalid program; test always requires refusal before the view is used.

<a id="limites-et-suite"></a>

## Limitations and follow-up

Async public signatures, other types borrowed, arbitrary envelopes,
general aggregates, Select, customizable scheduler and mutex remain open.
C borders and other explicit deferrals remain outside this lot.
The public parameter async is still rejected in the counter example
`validation/open-public-handle-async-parameter.crust`. The CLI check performed
on the final state is kept in `…-next-async-gap.log` : this limit
implementation remains the next batch, not a new rule of refusal.
The reset is exercised only with the explicit historical option.

No new ASan/TSan result, second compiler C or formal evidence.
Tests do not establish all the schedules or compositions
The surviving transfer remains a limit of coverage.
The diffs are in `validation/public-borrowed-handles-*.py.patch`.
This cycle is completed for the tested forms, with its mutation limit
The overall objective remains active.
