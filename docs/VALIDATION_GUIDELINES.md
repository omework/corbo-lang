# Corbo — Validation, Safety & Verification Guidelines

## 1. Mission

Your responsibility is not merely to make Corbo pass tests.

Your responsibility is to systematically challenge the language specification, compiler, generated code, and runtime in order to discover violations of Corbo's declared guarantees.

Corbo aims to be a fast, memory-safe language without garbage collection or general-purpose dynamic allocation.

The language currently supports synchronous execution. Do not assume asynchronous execution, concurrency, or other unsupported features.

**The primary objective is to find counterexamples, not to confirm correctness.**

Treat every successful test as evidence of a specific property under specific conditions, never as proof of general correctness.

## 2. Establish a verification baseline

Before introducing or modifying tests:

1. Read the complete current language specification.
2. Identify all normative rules and their dependencies.
3. Identify the memory model, ownership model, lifetime rules, evaluation order, and destruction semantics.
4. Inspect the compiler, generated C, runtime, and existing test infrastructure.
5. Identify existing reference models, oracles, sanitizers, and generated-test mechanisms.
6. Identify ambiguities, undocumented assumptions, and guarantees that cannot currently be tested.

Do not infer intended language behavior solely from the compiler implementation.

When the specification is ambiguous, report the ambiguity rather than silently selecting a convenient interpretation.

Do not modify normative language rules without explicit approval.

## 3. Maintain a rule-to-verification matrix

Every normative language rule must be traceable to verification evidence.

For each rule, maintain:

- A stable rule identifier.
- Its precise expected behavior.
- The safety invariant it protects.
- Its preconditions and scope.
- Other rules with which it interacts.
- Valid programs exercising the rule.
- Invalid programs that must be rejected.
- Relevant runtime assertions.
- Reference-model coverage, where applicable.
- Mutation-test coverage, where applicable.
- Known limitations and untested scenarios.

Distinguish between:

- Verified by executable tests.
- Examined through specification analysis.
- Supported by a formal argument or proof.
- Partially covered.
- Not verified.

Never report a rule as fully verified merely because its existing tests pass.

## 4. Perform global validation after every rule change

Whenever a rule is added, modified, clarified, or removed, reassess the complete current rule system.

Do not limit validation to the changed rule.

The process must:

1. Identify the direct consequences of the change.
2. Identify interactions with every relevant existing rule.
3. Reconsider previously established invariants.
4. Search for new contradictions or ambiguities.
5. Generate valid and invalid interaction scenarios.
6. Execute the applicable regression suite.
7. Update reference models and verification mappings when justified.
8. Report newly introduced uncertainty or uncovered cases.

Pay particular attention to interactions involving ownership, borrowing, scope exit, reset, transfer, value identity, storage reuse, and destruction.

A rule that is safe in isolation may be unsafe when composed with another rule.

## 5. Validate both accepted and rejected programs

Every relevant language feature should be tested from both directions.

### Accepted programs

Verify that valid programs:

- Compile successfully.
- Produce the expected values.
- Preserve object identity where required.
- Respect ownership and borrowing constraints.
- Execute operations in the specified order.
- Produce the expected destruction trace.
- Preserve memory-safety invariants.

### Rejected programs

Verify that invalid programs:

- Are rejected by the appropriate compiler stage.
- Cannot bypass restrictions through nesting, aliasing, control flow, or function calls.
- Produce an appropriate diagnostic.
- Are not silently accepted through compiler simplification or optimization.

Whenever feasible, construct minimally different accepted and rejected programs to test exact rule boundaries.

## 6. Test rule interactions systematically

Maintain an interaction matrix covering the complete current language.

Explore combinations involving:

- Nested scopes and functions.
- Conditional branches and early returns.
- Loops, break, and continue.
- Ownership transfers and repeated transfers.
- Borrowing and aliasing.
- Assignment and reassignment.
- Reset and destruction.
- Function arguments and evaluation order.
- Multiple value provenances.
- Storage reuse and object identity.
- Values whose storage requirements can grow.
- Capacity boundaries and failure conditions.

Test interactions across multiple function-call levels and control-flow paths.

Use pairwise and higher-order combinations where useful, but do not assume pairwise coverage is sufficient for memory safety.

Prioritize combinations that affect object lifetimes, memory validity, ownership transitions, and destruction.

Do not introduce unsupported language features merely to expand the test suite.

## 7. Validate storage and memory safety

Treat memory safety as a collection of explicit invariants rather than a single boolean property.

Investigate:

- Out-of-bounds reads and writes.
- Use-after-lifetime and use-after-release.
- Double destruction or double release.
- Invalid aliasing.
- Dangling references.
- Invalid ownership transfers.
- Incorrect storage reuse.
- Incorrect object identity after reuse.
- Invalid pointer or address assumptions.
- Misalignment.
- Integer overflow affecting memory calculations.
- Capacity exhaustion.
- Growth beyond reserved capacity.
- Reference validity during and after storage growth.
- Incorrect cleanup during early returns or failures.

Distinguish language-level guarantees from implementation-specific properties.

For values that grow, explicitly verify the declared growth policy, capacity limits, address stability, reference invalidation rules, and failure behavior.

Never assume that successful execution proves memory safety.

## 8. Use independent reference models

Maintain small, conceptually simple reference models for important language behaviors.

Suitable targets include:

- Ownership transitions.
- Destruction ordering.
- Storage-pool bookkeeping.
- Slot allocation and reuse.
- Function-effect summaries.
- Lifetime and borrowing constraints.
- Value identity.

Reference models must compute expected outcomes without relying on the compiler's internal decisions or generated C.

Prefer alternative representations and algorithms to reduce correlated implementation errors.

Where possible, compare:

1. The reference model's prediction.
2. The compiler's acceptance or rejection decision.
3. The generated program's observable behavior.

Reference models are themselves fallible. Test their assumptions and maintain independently specified examples.

## 9. Use property-based and generated testing

Generate programs and operation sequences from the actual supported language grammar and rules.

Test both valid and intentionally invalid programs.

Vary:

- Nesting depth.
- Number and order of operations.
- Control-flow paths.
- Function-call depth.
- Argument evaluation sequences.
- Ownership-transfer patterns.
- Borrowing relationships.
- Reset and destruction points.
- Storage capacities and boundary values.

For runtime structures, generate long randomized operation sequences and compare each relevant state transition against an independent model.

Record random seeds and configurations to make failures reproducible.

When a failure occurs, minimize the generated program or operation sequence to the smallest useful counterexample.

Add every confirmed defect as a deterministic regression test.

## 10. Perform mutation testing

Periodically introduce controlled faults into temporary copies of the compiler or runtime.

Target mutations such as:

- Reversing destruction order.
- Omitting cleanup operations.
- Incorrectly accepting forbidden ownership transitions.
- Incorrectly rejecting valid transitions.
- Reusing live storage.
- Corrupting free-list bookkeeping.
- Violating capacity limits.
- Invalidating references unexpectedly.
- Altering evaluation order.
- Omitting lifetime checks.

Verify that relevant tests detect these faults.

Classify each mutation as:

- Detected.
- Survived.
- Not exercised.
- Equivalent or behaviorally irrelevant.
- Inconclusive.

Investigate surviving non-equivalent mutations and add meaningful coverage where appropriate.

Do not modify both the implementation and its oracle to preserve a passing result.

Never extrapolate a global mutation-detection rate from a small, hand-selected sample.

## 11. Validate generated C and runtime behavior

Because Corbo generates C, validate both language semantics and generated-program execution.

Use the available compiler toolchains and appropriate sanitizers, including UBSan and ASan where supported.

Where feasible, test multiple optimization levels and compiler configurations.

Distinguish:

- Errors in the Corbo compiler.
- Errors in generated C.
- Errors in the Corbo runtime.
- Violations of Corbo language semantics.
- Undefined behavior under C semantics.

Ensure sanitizer diagnostics fail the relevant test run rather than being silently ignored.

A sanitizer-clean execution is evidence about the exercised paths, not proof of complete memory safety.

Where useful, compare behavior across independent C compiler implementations.

## 12. Audit the specification itself

Do not assume that a well-tested implementation implies a sound language specification.

For every memory-safety guarantee:

1. Identify the invariant being claimed.
2. Identify the rules intended to preserve it.
3. Examine how each permitted operation affects it.
4. Examine how permitted operations compose.
5. Search for a valid program that violates it.
6. Identify missing premises, ambiguous definitions, and unsupported assumptions.

When a counterexample is found, determine whether the defect belongs to the specification, compiler, runtime, or test oracle.

If a general guarantee cannot be established, explicitly state the limitation.

Consider formalizing critical rules using operational semantics, state-transition models, or machine-checkable properties when the complexity justifies it.

Do not claim formal verification unless an actual formal verification method has been applied.

## 13. Keep the validation system independent and auditable

Do not weaken tests to make the suite pass.

Do not silently change expected behavior to match compiler output.

Do not interpret compiler acceptance as evidence that a program is valid.

Do not interpret compiler rejection as evidence that a program is invalid.

Do not conceal unresolved failures, flaky tests, or unsupported scenarios.

Separate the implementation under test from the mechanisms determining expected behavior.

Preserve enough information to reproduce failures and inspect verification results.

## 14. Report evidence, not confidence theater

After each global validation cycle, report:

- Rules added or changed.
- Specification ambiguities discovered.
- Invariants examined.
- Interaction scenarios tested.
- Accepted and rejected program counts.
- Reference-model results.
- Property-based or generated-test results.
- Mutation-test results, when performed.
- Sanitizer configurations and outcomes.
- Defects found and corrected.
- Remaining unverified properties.
- Known limitations of the verification process.

Clearly distinguish executed checks from proposed checks.

Never describe a result as verified unless the corresponding verification was actually performed.

Avoid unqualified statements such as "Corbo is memory safe" or "all combinations are covered."

Prefer precise statements describing the properties tested, the conditions examined, and the remaining uncertainty.

## 15. Preserve the development workflow

Verification must support language design, not silently replace it.

When a new rule introduces an unresolved design decision:

1. Explain the problem.
2. Identify the competing constraints.
3. Present viable approaches.
4. Explain their safety and implementation implications.
5. Ask for a decision when the language's intended semantics are not established.

Do not invent new language semantics merely to satisfy a test.

Do not autonomously expand Corbo's feature set.

Keep verification infrastructure proportional to the complexity and maturity of the language.

Prioritize high-value safety invariants over test counts.

## 16. Completion criteria

A validation cycle is complete only when:

- The complete current rule system has been reconsidered.
- Relevant regression tests have executed.
- New interactions have been examined.
- Applicable reference-model checks have executed.
- Relevant safety checks have executed.
- Failures and ambiguities have been reported.
- The rule-to-verification matrix has been updated.
- Remaining gaps have been explicitly documented.

Completion does not mean that Corbo has been proven safe.

It means that the defined validation process has been executed and its evidence is available for inspection.

---

## Governing principle

**Do not optimize for the number of passing tests. Optimize for the ability to discover violations of Corbo's declared guarantees.**

Your job is not to demonstrate that Corbo works.

Your job is to try systematically to demonstrate where Corbo does not work, and to provide reproducible evidence whenever you succeed.