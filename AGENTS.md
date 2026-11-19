[Français](AGENTS-fr.md)

# Working on Corbo

The active compiler is maintained separately in `omework/corboc`, normally the
sibling checkout `../corboc`. Use `CORBOC_SOURCE_ROOT` for another location.
This repository owns the specification, STD and readable runtime; the compiler
pins those inputs with `corbo.lock`. See `docs/COMPILER_REPOSITORY.md`.

For every Corbo-related repository, use `Jabar` as the user's Git author and
committer name. Preserve the configured email. Apply the name locally or through
the user's Corbo-specific conditional Git configuration, not as an unrelated
repository's default identity.

Before validating, auditing safety, or modifying tests, read and follow
the user-provided [Validation Guidelines](docs/VALIDATION_GUIDELINES.md).

The accepted language rules are recorded in [Language Rules](docs/LANGUAGE_RULES.md).
Consult the specification when interpreting the compiler's behavior. Obtain
explicit agreement before changing normative rules.

Look for counterexamples and report specific execution evidence, its limits,
and any unresolved discrepancies. A passing test suite does not constitute
a general safety proof.

Maintain the [Verification Matrix](docs/VERIFICATION_MATRIX.md). Record
executed results, counterexamples, and limitations in a cycle report.

At each significant step, show the updated checklist, including completed
and validated work, current work, remaining work, and open decisions.
Mark a validation complete once it has run to completion.

This chat focuses on implementing and integrating compiler features.
Maintain the necessary functional and regression tests, the matrix, and
the list of known limitations. A separate lab owns in-depth adversarial
analysis and mutation campaigns. Report the evidence produced here
separately from any independent audit and verify that audit's status
before making claims about it.

Cover the cases already listed and regressions directly related to the
changes. Fix and document defects encountered within that scope.

## Core versus API changes

Before each modification, explicitly classify its scope: core/grammar or
API/standard library. Keep language mechanisms separate from library APIs.

- Core/grammar changes affect syntax, language rules, or general compiler
  mechanisms. Validate the affected mechanisms and relevant regressions.
- API/standard-library changes affect library interfaces or implementations
  using existing language mechanisms. Use targeted functional tests and
  directly related regressions. Do not automatically rerun the full compiler
  suite, self-reconstruction, or a broad safety campaign for an API change.
- If an API change exposes a compiler limitation, identify the separate core
  fix explicitly and validate that mechanism proportionately. Do not expand
  the API task into unrelated compiler work.

Apply validation guidance proportionately to this classification. Retain the
agreed supported-platform coverage for affected platform-specific behavior;
an API change alone does not require rebuilding the compiler on every platform.
