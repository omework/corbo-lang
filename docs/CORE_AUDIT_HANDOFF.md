[Français](CORE_AUDIT_HANDOFF-fr.md)

<a id="crust--guide-pour-laudit-indépendant-du-core"></a>

# Corbo — Guide to independent audit of the core

The language reference is the core of the **11 novembre 2026**. Ce guide sert
to an independent officer looking for programs that fail to apply the rules. For each
pass, indicate the exact version of the compiler reviewed, such as commit and local
changes.

<a id="documents-de-référence"></a>

## Reference documents

| Document | Usage |
| --- | --- |
| [Grammaire EBNF](../CORE_GRAMMAR.ebnf) | Determine whether the source form belongs to the core. |
| [Rules N1–N8](LANGUAGE_RULES.md#noyau-mémoire--grille-de-lecture) | Identify the invariant and read the normative clauses to which it refers. |
| [Async and multithread rules](ASYNC_MULTITHREAD_RULES.md) | Interpret catches, suspensions, branch contracts and expectations. |
| [Checklist](IMPLEMENTATION_CHECKLIST.md#vérification-sémantique-du-core) | Identify partial support and refusals already identified. |
| [Audit matrix](VERIFICATION_MATRIX.md) and [cycle report](cycles/CORE_COMPOSITION_CYCLE.md) | Find existing controls, results and limitations. |
| [Project records](../AGENTS.md) and [validation guidelines](VALIDATION_GUIDELINES.md) | Follow the reproduction and reporting process. |

Grammar and rules give the expected behavior. The checklist and matrix document the
status of the implementation. SelectGroup and custom scheduler are reported. Use the
core syntax and the
integrated runtime, in particular `A<T>`, value-based displacements and
the signatures of closure `fn(...) -> R`.

<a id="mission-à-donner-à-claude"></a>

## Mission to be given to Claude

> Seeks replicable counter-examples in the core Corbo. For
> each candidate, quotes the normative rule and deducts the expected outcome
> before consulting the compiler's result. Priorise a program
> accepted when a rule requires refusal. Also takes away a refusal
> unexpected, a generation C deviation or a specification ambiguity
> when the evidence justifies it. Reduce each case and provide a
> control variant that changes only one relevant condition.
> The integration of the corrective measures is
> The object of a separate pass.

<a id="axes-de-recherche"></a>

## Research areas

- **N1–N3** — type and initialisation, responsibility for cleaning, copying,
  borrowing and moving. Follow the old link and receiver.
- **N4–N5** — lifespan and access compatibility.
  through a closed, competing branch or a returned value.
  Identify target, area borrowed and last use.
- **N6** — paths and order of assessment.
  a replacement or waiting on some paths. Write the rest
  d
- **N7** — destruction and recovery.
  check that a re-used slot does not reactivate the old access.
- **N8** — frontiers.
  and compare the result to the direct case. Include the source,
  effects on fields or entries and, if applicable, waiting.

## Reproduction

From the root of the repository, on a standalone Corbo file with `main` :

```sh
python3 prototype/crust.py check cas.crb --syntax-only
python3 prototype/crust.py check cas.crb
python3 prototype/crust.py emit-c cas.crb -o /tmp/crust-audit-cas.c
```

The first command checks the syntax. The second one exercises the verifier.
The third is used to isolate a generation gap after acceptance.
a tell-tale that the specification allows, use also
`python3 prototype/crust.py run cas.crb` if the expected outcome is observable at
A prohibited program accepted by the `check` sufficient to
Report an auditor's defect. Run is not required.

Starting point to get acquainted with both entrances:
[invalid_reference_field_drop.crb](../examples/invalid_reference_field_drop.crb)
is a known control that passes the syntactic analysis and must be refused because of
a borrow still in use.

## Format d’un constat

1. **Rule and reasoning expected** — N1–N8, precise clause, path of execution
   or life-long obligation in question.
2. **Minimum Source and Control Variant** — complete files, with the
   change that explains the expected difference.
3. **Observed result** — version, commands, output codes and diagnostics.
   Add the output, trace or extract of C generated when establishing
   the finding.
4. **Nature of the finding** — programme not accepted, programme authorised
   rejected, generation or runtime deviation, or insufficiently regulated
   Indicate the limits and results not reproduced.
5. **Known State** — indicate whether the matrix or report already contains this case.
