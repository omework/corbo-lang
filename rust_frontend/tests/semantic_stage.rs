//! These inspect populated semantic facts. They never invoke verify or a backend.
use corbo_frontend::{parse_source, post_ast::*, semantic};
fn resolve(source: &str) -> semantic::ResolvedProgram {
    semantic::resolve(parse_source(source.to_owned()).unwrap())
        .unwrap_or_else(|e| panic!("{e:#?}\n{source}"))
}
#[test]
fn resolves_types_calls_and_compound_assignment_phases() {
    let r = resolve(
        "fn add(a: u16, b: u16) u16 { a + b } fn main() { let mut count: u16 = 1; count += add(count, 2); }",
    );
    let p = &r.logical.semantics.post_ast;
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::DirectCall(_)))
    );
    let op = p
        .bodies
        .iter()
        .flat_map(|b| &b.operations)
        .find_map(|o| {
            if let Operation::AddAssign(a) = o {
                Some(a)
            } else {
                None
            }
        })
        .unwrap();
    assert_eq!(op.domain, NumericType::U16);
    assert!(matches!(
        p.execution.execution_moments[op.phases.read_previous.0 as usize].phase,
        ExecutionPhase::Read
    ));
    assert!(matches!(
        p.execution.execution_moments[op.phases.write.0 as usize].phase,
        ExecutionPhase::Write
    ));
    assert_eq!(op.site.execution_moments.rest.len(), 2);
    assert!(r.logical.semantics.lifetimes.requirements.is_empty());
}
#[test]
fn records_lifetime_obligations_without_running_a_checker() {
    let r = resolve(
        "fn main() { let mut value = 1; let first = &mut value; let second = &mut value; }",
    );
    let p = &r.logical.semantics.post_ast;
    assert_eq!(
        p.objects
            .references
            .iter()
            .filter(|reference| matches!(reference.formation, ReferenceFormation::Loan))
            .count(),
        2
    );
    assert_eq!(
        p.obligations
            .n4
            .iter()
            .filter(|obligation| matches!(
                obligation.requirement,
                LifetimeProofRequirement::DependencyLink {
                    lifetime: Some(_),
                    ..
                }
            ))
            .count(),
        4
    );
    assert_eq!(p.obligations.n5.len(), 2);
    assert_eq!(r.logical.semantics.lifetimes.requirements.len(), 4);
}
#[test]
fn retains_symbolic_hierarchical_loop_context() {
    let r = resolve("fn main() { let mut i = 0; while i < 3 { i += 1; } }");
    let p = &r.logical.semantics.post_ast;
    assert_eq!(p.execution.loops.len(), 1);
    assert!(p.execution.instance_domains.iter().any(|d| matches!(
        &d.definition,
        InstanceDomainDefinition::Iteration {
            moment: IterationMoment {
                iteration: IterationCoordinate::Symbolic(_),
                ..
            },
            ..
        }
    )));
    assert!(
        p.execution
            .edges
            .iter()
            .any(|e| matches!(e, ExecutionEdge::LoopBack(_)))
    );
}
#[test]
fn logical_destination_tracks_a_child_result_into_its_parent() {
    let r = resolve(
        "struct Boxed { value: i64; } fn main() { let outer = { let inner = Boxed { value: 42 }; inner }; }",
    );
    assert!(r.logical.physical_requirements.iter().any(|r| matches!(
        r.kind,
        PhysicalPlacementRequirementKind::ReserveBeforeScopeEntry(_)
    )));
    assert!(r.logical.semantics.destinations.transfers.len() >= 3);
}
#[test]
fn branch_results_keep_guards_and_merge_values() {
    let r = resolve("fn choose(flag: bool) i64 { if flag { 1 } else { 2 } }");
    let p = &r.logical.semantics.post_ast;
    assert!(
        p.execution
            .relationships
            .iter()
            .any(|r| matches!(r, BranchRelationship::Exclusive(_)))
    );
    assert!(
        p.values
            .provenance
            .iter()
            .any(|v| matches!(v.kind, ProvenanceKind::Merge(_)))
    );
}
#[test]
fn semantic_errors_are_explicit_and_never_return_partial_post_ast() {
    for (source, kind) in [
        (
            "fn main() { missing; }",
            semantic::DiagnosticKind::UnresolvedName,
        ),
        (
            "fn main() { let x: u8 = true; }",
            semantic::DiagnosticKind::TypeMismatch,
        ),
    ] {
        let error = semantic::resolve(parse_source(source.to_owned()).unwrap()).unwrap_err();
        assert_eq!(error[0].kind, kind);
        assert!(error[0].span.start < source.len());
    }
}

#[test]
fn short_circuit_right_operands_have_conditional_timelines() {
    let result = resolve("fn test(a: bool, b: bool) bool { a && b || a }");
    let p = &result.logical.semantics.post_ast;
    for operation in p.bodies.iter().flat_map(|b| &b.operations) {
        let branch = match operation {
            Operation::ShortCircuitAnd(o) => o.conditional_right,
            Operation::ShortCircuitOr(o) => o.conditional_right,
            _ => continue,
        };
        assert!(matches!(
            p.execution.branches[branch.0 as usize].kind,
            BranchKind::Conditional(_)
        ));
        let timeline = p.execution.branches[branch.0 as usize].timeline;
        assert_ne!(operation.site().timeline, timeline);
    }
    semantic::validate_population(&result.logical).unwrap();
}

#[test]
fn copied_primitive_and_mutated_place_do_not_alias_value_ownership() {
    let result = resolve("fn main() { let mut a = 1; let b = a; a += b; }");
    let p = &result.logical.semantics.post_ast;
    assert_eq!(
        p.objects.addresses.len(),
        2,
        "writing a primitive does not create a third allocation"
    );
    assert_ne!(p.objects.addresses[0].id, p.objects.addresses[1].id);
    assert_eq!(
        result.logical.semantics.type_derivations.len(),
        p.values.entries.len()
    );
}

#[test]
fn returned_aggregate_has_caller_destination_and_no_physical_reservation() {
    let result = resolve(
        "struct Boxed { value: i64; } fn make() Boxed { let inner = Boxed { value: 7 }; inner }",
    );
    assert!(
        result
            .logical
            .finals
            .iter()
            .any(|f| matches!(f.scope, LogicalScope::CallerResult(_)))
    );
    assert_eq!(
        result.logical.semantics.destinations.result_contracts.len(),
        1
    );
    assert!(
        !result
            .logical
            .semantics
            .post_ast
            .values
            .placement_summaries
            .iter()
            .all(|s| s.destinations.is_empty())
    );
    assert!(
        result
            .logical
            .semantics
            .post_ast
            .bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::MoveValue(_)))
    );
}

#[test]
fn function_dependency_application_retains_all_argument_origins() {
    let result = resolve(
        "fn identity(value: &i64) &i64 { value } fn main() { let a = 1; let view = identity(&a); }",
    );
    let p = &result.logical.semantics.post_ast;
    assert!(p.values.dependency_summaries.iter().flat_map(|s| &s.dependencies).any(|d| matches!(d, DependencyRequirement::InstantiatedResult { arguments, .. } if arguments.len() == 1)));
    assert!(
        p.execution
            .edges
            .iter()
            .any(|e| matches!(e, ExecutionEdge::Return(_)))
    );
    let call = p
        .bodies
        .iter()
        .flat_map(|b| &b.operations)
        .find_map(|o| match o {
            Operation::DirectCall(c) => Some(c),
            _ => None,
        })
        .unwrap();
    let ValueDefinition::OperationResult { produced_at, .. } =
        p.values.entries[call.result.0 as usize].definition
    else {
        panic!()
    };
    assert!(matches!(
        p.execution.execution_moments[produced_at.0 as usize].phase,
        ExecutionPhase::Receive
    ));
    assert!(
        p.effects
            .iter()
            .flat_map(|s| &s.effects)
            .any(|e| matches!(e.effect, Effect::Call(_)))
    );
}

#[test]
fn recursive_dependency_graph_is_finite_and_reuses_the_instance() {
    let result = resolve("fn recurse(value: i64) i64 { recurse(value) }");
    let p = &result.logical.semantics.post_ast;
    assert_eq!(p.bodies.len(), 1);
    assert_eq!(
        p.declarations
            .instances
            .iter()
            .filter(|i| p.symbols.entries
                [p.declarations.functions[i.definition.0 as usize].symbol.0 as usize]
                .spelling
                == "recurse")
            .count(),
        1
    );
    assert!(
        p.execution
            .instance_domains
            .iter()
            .any(|d| matches!(d.definition, InstanceDomainDefinition::Call { .. }))
    );
    assert!(
        p.execution
            .edges
            .iter()
            .any(|e| matches!(e, ExecutionEdge::Return(_)))
    );
}

#[test]
fn structural_audit_rejects_a_broken_handoff_not_a_language_rule() {
    let mut result = resolve("fn main() { let value = 1; }");
    result
        .logical
        .semantics
        .post_ast
        .execution
        .execution_moments[0]
        .operation = OperationId(u32::MAX);
    let errors = semantic::validate_population(&result.logical).unwrap_err();
    assert!(errors.iter().any(|e| e.0.contains("operation")));
}

#[test]
fn concrete_generic_specializations_reuse_body_and_preserve_source_moments() {
    let result = resolve(
        "#(type: T) fn identity(value: T) T { let kept: T = value; kept } fn main() { let a: u8 = identity(1); let b: u16 = identity(2); let c: u8 = identity(3); }",
    );
    let p = &result.logical.semantics.post_ast;
    let instances = p
        .declarations
        .instances
        .iter()
        .filter(|i| {
            !i.substitutions.is_empty() && matches!(i.resolution, InstanceResolution::Concrete)
        })
        .collect::<Vec<_>>();
    assert_eq!(instances.len(), 2);
    assert_ne!(instances[0].body, instances[1].body);
    assert_ne!(instances[0].signature, instances[1].signature);
    let first = &p.bodies[instances[0].body.unwrap().0 as usize];
    let second = &p.bodies[instances[1].body.unwrap().0 as usize];
    assert_eq!(
        first.operations[0].site().lexical_moment,
        second.operations[0].site().lexical_moment
    );
    assert_ne!(
        first.operations[0].site().execution_moments.first,
        second.operations[0].site().execution_moments.first
    );
    assert_eq!(first.scope != second.scope, true);
    for body in [first, second] {
        assert!(!body.operations.is_empty());
        for binding in &p.scopes.entries[body.scope.0 as usize].bindings {
            assert!(!matches!(
                p.types.entries[p.scopes.bindings[binding.0 as usize].ty.0 as usize].kind,
                TypeDefinition::Parameter(_)
            ));
        }
    }
}

#[test]
fn loop_carried_values_and_nested_iteration_moments_are_explicit() {
    let result = resolve(
        "fn count() i64 { let mut x = 0; while x < 3 { let mut y = 0; while y < 2 { y += 1; } x += 1; } x }",
    );
    let p = &result.logical.semantics.post_ast;
    let loops = &p.execution.loops;
    assert_eq!(loops.len(), 2);
    let inner = &p.execution.instance_domains[loops[1].instance.0 as usize];
    assert!(
        matches!(inner.definition, InstanceDomainDefinition::Iteration { parent, .. } if parent == loops[0].instance)
    );
    let carried = p
        .bodies
        .iter()
        .flat_map(|b| &b.operations)
        .filter_map(|o| match o {
            Operation::LoopParameter(p) => Some(p),
            _ => None,
        })
        .collect::<Vec<_>>();
    assert!(carried.iter().any(|p| p.back_edges[0].value != p.result));
    assert!(
        p.execution
            .execution_moments
            .iter()
            .any(|m| m.instance == inner.id)
    );
    assert!(
        p.execution
            .edges
            .iter()
            .any(|e| matches!(e, ExecutionEdge::LoopBack(b) if b.to == loops[0].continue_target))
    );
}

#[test]
fn contextual_typing_checks_arrays_conditions_and_signed_literal_boundaries() {
    resolve("fn main() { let minimum: i64 = -9223372036854775808; let small: i32 = -2147483648; }");
    for source in [
        "fn main() { let array = [1, true]; }",
        "fn main() { let value = 1; if value { 1 } else { 2 }; }",
        "fn main() { let value: i32 = -2147483649; }",
        "fn main() { let value: f32 = 1; }",
    ] {
        let errors = semantic::resolve(parse_source(source.to_owned()).unwrap()).unwrap_err();
        assert_eq!(
            errors[0].kind,
            semantic::DiagnosticKind::TypeMismatch,
            "{source}: {errors:?}"
        );
    }
}

#[test]
fn string_literals_have_static_targets_and_runtime_reference_identities() {
    let result = resolve("fn text() &str { \"Corbo\" }");
    let p = &result.logical.semantics.post_ast;
    let literal = p
        .bodies
        .iter()
        .flat_map(|b| &b.operations)
        .find_map(|o| match o {
            Operation::TextLiteral(l) => Some(l),
            _ => None,
        })
        .unwrap();
    assert!(matches!(
        p.objects.addresses[literal.storage.0 as usize].creation,
        ObjectCreation::Static(_)
    ));
    let reference = &p.objects.references[literal.reference.0 as usize];
    assert!(
        matches!(p.objects.places[reference.origins.first.target.0 as usize].root, PlaceRoot::Address(a) if a == literal.storage)
    );
}

#[test]
fn constant_grammar_resolves_forward_associated_dependencies() {
    let result = resolve(
        "pub const DOUBLE: usize = BASE * 2; const BASE: usize = 8; struct Buffer { data: [u8; Self::SIZE]; const SIZE: usize = max(DOUBLE, 4) + min(2, 3); } fn main() { let capacity = DOUBLE; }",
    );
    let p = &result.logical.semantics.post_ast;
    assert!(
        p.types
            .entries
            .iter()
            .any(|t| matches!(t.kind, TypeDefinition::Array { length: 18, .. }))
    );
    assert!(
        p.declarations
            .constants
            .iter()
            .any(|c| matches!(c.value, ConstantValue::Integer(16)))
    );
    for source in [
        "const A: usize = B; const B: usize = A;",
        "const A: u8 = 256;",
        "const A: i64 = 1 / 0;",
    ] {
        assert!(
            semantic::resolve(parse_source(source.to_owned()).unwrap()).is_err(),
            "{source}"
        );
    }
    resolve("const TEXT: &str = \"Corbo\"; const MINIMUM: i64 = -9223372036854775808;");
}

#[test]
fn dynamic_slices_retain_bounds_places_references_and_lengths() {
    let result = resolve(
        "fn window(input: &[i64], start: u16, end: u16) &[i64] { &input[start..end] } fn first(input: &[i64]) i64 { input[0] } fn size(input: &[i64]) usize { input.len() }",
    );
    let p = &result.logical.semantics.post_ast;
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::SequenceLength(_)))
    );
    let slice = p
        .bodies
        .iter()
        .flat_map(|b| &b.operations)
        .find_map(|o| match o {
            Operation::SliceView(s) => Some(s),
            _ => None,
        })
        .unwrap();
    assert!(matches!(
        p.runtime_checks[slice.checks[0].0 as usize],
        RuntimeCheck::SliceBounds(_)
    ));
    assert!(matches!(
        p.objects.places[p.objects.references[slice.reference.0 as usize]
            .origins
            .first
            .target
            .0 as usize]
            .projections
            .last(),
        Some(PlaceProjection::Range { .. })
    ));
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::IndexPlace(_)))
    );
}

#[test]
fn foreign_operands_are_resolved_once_with_explicit_writebacks() {
    let result = resolve(
        "fn main() { let mut value = 1; @unchecked { let address = addr(value); @c(includes={\"stdint.h\"}) { ${value} = 2; } @c++ { ${value} = 3; } @asm { nop } } let after = value; }",
    );
    let p = &result.logical.semantics.post_ast;
    assert_eq!(p.foreign_regions.len(), 3);
    assert_eq!(p.foreign_regions[0].headers, vec!["stdint.h"]);
    let c = p
        .bodies
        .iter()
        .flat_map(|b| &b.operations)
        .find_map(|o| match o {
            Operation::ForeignC(c) => Some(c),
            _ => None,
        })
        .unwrap();
    assert_eq!(c.outputs.len(), 1);
    assert!(matches!(
        c.operands[0].mode,
        ForeignOperandMode::MutableStorage
    ));
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::AddressOf(_)))
    );
    assert!(
        p.foreign_regions[0]
            .fragments
            .iter()
            .any(|f| matches!(f, ForeignFragment::Operand(_)))
    );
    assert!(parse_source("fn main() { @asm { nop } }".into()).is_err());
    let error =
        semantic::resolve(parse_source("fn main() { let n=1; let a=addr(n); }".into()).unwrap())
            .unwrap_err();
    assert_eq!(error[0].kind, semantic::DiagnosticKind::InvalidCall);
}

#[test]
fn foreign_address_operands_write_back_to_their_referent() {
    let result = resolve(
        "fn main(){let mut frequency:u64=0;@unchecked{let address=addr(&mut frequency);@asm{mov rax, ${address}}}let after=frequency;}",
    );
    let p = &result.logical.semantics.post_ast;
    let assembly = p
        .bodies
        .iter()
        .flat_map(|body| &body.operations)
        .find_map(|operation| match operation {
            Operation::ForeignAssembly(assembly) => Some(assembly),
            _ => None,
        })
        .unwrap();
    assert_eq!(assembly.outputs.len(), 1);
    let output = &assembly.outputs[0];
    let place = &p.objects.places[p.objects.evaluated_places[output.place.0 as usize]
        .definition
        .0 as usize];
    assert!(matches!(place.root, PlaceRoot::Binding(_)));
}

#[test]
fn enum_equality_and_implicit_copies_retain_the_selected_plans() {
    let result = resolve(
        "enum Mark { Ready; Count(i64); } fn main() { let first = Mark::Count(7); let second = first; let same = first == second; }",
    );
    let p = &result.logical.semantics.post_ast;
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::CopyEligibleEnum(_)))
    );
    assert!(
        p.contracts
            .equality
            .iter()
            .any(|p| matches!(p.kind, EqualityKind::EnumTagAndPayload(_)))
    );
}

#[test]
fn unreachable_undefined_names_are_warnings_without_executable_placeholder_values() {
    let result = resolve("fn example() i64 { return 42; let value = missing_name + true; }");
    assert_eq!(result.warnings.len(), 2);
    assert!(
        result
            .warnings
            .iter()
            .any(|w| w.kind == semantic::DiagnosticKind::UnreachableStatement)
    );
    assert!(
        result
            .warnings
            .iter()
            .any(|w| w.kind == semantic::DiagnosticKind::UnresolvedName
                && w.message.contains("undefined name 'missing_name'"))
    );
    let p = &result.logical.semantics.post_ast;
    assert_eq!(p.unreachable_source.statements.len(), 1);
    assert!(p.unreachable_source.names.iter().any(|n|matches!(&n.resolution,UnreachableNameResolution::Undefined{spelling}if spelling=="missing_name")));
    assert!(
        !p.symbols
            .entries
            .iter()
            .any(|s| s.spelling == "missing_name")
    );
    let baseline = resolve("fn example() i64 { return 42; }");
    assert_eq!(
        p.values.entries.len(),
        baseline.logical.semantics.post_ast.values.entries.len()
    );
    assert_eq!(
        p.execution.execution_moments.len(),
        baseline
            .logical
            .semantics
            .post_ast
            .execution
            .execution_moments
            .len()
    );
    assert!(
        semantic::resolve(parse_source("fn example() i64 { missing_name }".into()).unwrap())
            .is_err()
    );
}

#[test]
fn unreachable_local_names_are_scoped_and_available_to_later_dead_statements() {
    let result = resolve(
        "fn example() { return; let first = unknown; let second = first; { let third = second; } let fourth = third; }",
    );
    let undefined = result
        .warnings
        .iter()
        .filter(|w| w.kind == semantic::DiagnosticKind::UnresolvedName)
        .collect::<Vec<_>>();
    assert_eq!(undefined.len(), 2, "{:?}", result.warnings);
    assert!(undefined.iter().any(|w| w.message.contains("'unknown'")));
    assert!(undefined.iter().any(|w| w.message.contains("'third'")));
    assert!(
        !undefined
            .iter()
            .any(|w| w.message.contains("'first'") || w.message.contains("'second'"))
    );
}

#[test]
fn terminating_if_arms_do_not_create_a_reachable_merge_or_dead_name_error() {
    let result = resolve(
        "fn choose(flag: bool) i64 { if flag { return 1; } else { return 2; } let unused = absent; }",
    );
    let p = &result.logical.semantics.post_ast;
    let decision = p
        .bodies
        .iter()
        .flat_map(|b| &b.operations)
        .find_map(|o| match o {
            Operation::IfDecision(i) => Some(i),
            _ => None,
        })
        .unwrap();
    assert!(decision.merge.is_none());
    assert!(result.warnings.iter().any(
        |w| w.kind == semantic::DiagnosticKind::UnresolvedName && w.message.contains("absent")
    ));
    for operation in p.bodies.iter().flat_map(|b| &b.operations) {
        if let Operation::ReturnControl(r) = operation {
            assert!(!r.outer_exits.is_empty());
        }
    }
    resolve("fn choose(flag: bool) i64 { if flag { return 1; } 2 }");
}

#[test]
fn break_and_continue_dead_tails_warn_without_normal_back_edges() {
    let result = resolve(
        "fn value() i64 { loop { break 7; let dead = missing; } } fn spin() { let mut i=0; while i < 2 { i+=1; continue; let dead = other; } }",
    );
    assert_eq!(
        result
            .warnings
            .iter()
            .filter(|w| w.kind == semantic::DiagnosticKind::UnresolvedName)
            .count(),
        2
    );
    let p = &result.logical.semantics.post_ast;
    let breaks = p
        .bodies
        .iter()
        .flat_map(|b| &b.operations)
        .filter_map(|o| match o {
            Operation::BreakControl(b) => Some(b),
            _ => None,
        })
        .collect::<Vec<_>>();
    for b in breaks {
        assert!(!p.execution.edges.iter().any(|e|matches!(e,ExecutionEdge::LoopBack(edge)if edge.from==b.site.execution_moments.first)));
        assert!(p.execution.edges.iter().any(|e|matches!(e,ExecutionEdge::Conditional(edge)if edge.from==b.site.execution_moments.first&&edge.to==p.execution.loops[b.region.0 as usize].break_target)));
    }
}

#[test]
fn conditional_breaks_and_continues_keep_their_distinct_transfer_paths() {
    let result = resolve(
        "fn main() { let mut i=0; while i < 4 { if i == 2 { break; } i+=1; if i < 3 { continue; } i+=1; } }",
    );
    let p = &result.logical.semantics.post_ast;
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::BreakControl(_)))
    );
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::ContinueControl(_)))
    );
    semantic::validate_population(&result.logical).unwrap();
}

#[test]
fn match_and_if_let_resolve_owned_and_borrowed_payload_patterns() {
    let result = resolve(
        "enum Event { Data { code: i64; }; Empty; } fn code(event: &Event) i64 { match event { Event::Data { code: value } => { *value }, Event::Empty => { 0 } } } fn owned(event: Event) i64 { if let Event::Data { code: value } = event { value } else { 0 } } fn make() Event { Event::Data { code: 7 } }",
    );
    let p = &result.logical.semantics.post_ast;
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::MatchDecision(_)))
    );
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::IfLetDecision(_)))
    );
    assert!(p.bodies.iter().flat_map(|b|&b.operations).any(|o|matches!(o,Operation::ExtractVariantField(e) if e.reference.is_some()&&matches!(e.transfer,TransferKind::SharedBorrow))));
    assert!(
        p.execution
            .branches
            .iter()
            .any(|b| matches!(&b.kind,BranchKind::MatchArm(a)if !a.bindings.is_empty()))
    );
    assert_eq!(p.match_coverage.len(), 1);
}

#[test]
fn terminating_match_arms_preserve_unreachable_policy_and_unwind_paths() {
    let result = resolve(
        "enum Flag { On; Off; } fn decide(flag: Flag) i64 { match flag { Flag::On => { return 1; }, Flag::Off => { return 2; } } let dead = unknown; }",
    );
    let p = &result.logical.semantics.post_ast;
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o,Operation::MatchDecision(d)if d.merge.is_none()))
    );
    assert!(
        result
            .warnings
            .iter()
            .any(|w| w.kind == semantic::DiagnosticKind::UnresolvedName)
    );
    resolve(
        "enum Flag { On; Off; } fn decide(flag: Flag) i64 { if let Flag::On = flag { return 1; } 2 }",
    );
}

#[test]
fn nominal_specializations_and_owner_method_substitutions_are_distinct() {
    let result = resolve(
        "struct Boxed<T> { value: T; fn new(value: T) Self { Self { value } } fn get(&self) T { self.value } } struct Pair { left: Boxed<i64>; right: Boxed<bool>; } fn main() { let pair=Pair { left: Boxed::new(7), right: Boxed::new(true) }; let number=pair.left.get(); let flag=pair.right.get(); }",
    );
    let p = &result.logical.semantics.post_ast;
    let specializations=p.declarations.structs.iter().filter(|s|matches!(&p.types.entries[s.ty.0 as usize].kind,TypeDefinition::Nominal{arguments,..}if !arguments.is_empty() && arguments.iter().all(|t| match t { TypeArgument::Type(t) => !matches!(p.types.entries[t.0 as usize].kind, TypeDefinition::Parameter(_)), TypeArgument::Integer(_) => true }))).collect::<Vec<_>>();
    assert_eq!(specializations.len(), 2);
    let left = specializations[0].fields[0];
    let right = specializations[1].fields[0];
    assert_ne!(left, right);
    assert_ne!(
        p.declarations.fields[left.0 as usize].ty,
        p.declarations.fields[right.0 as usize].ty
    );
    assert!(
        !p.declarations
            .instances
            .iter()
            .all(|i| i.substitutions.is_empty())
    );
}

#[test]
fn generic_enum_payloads_and_patterns_use_concrete_variants() {
    let result = resolve(
        "enum Choice<T> { Value(T); Empty; } fn choose(value: Choice<u16>) u16 { match value { Choice::Value(number) => { number }, Choice::Empty => { 0 } } } fn main() { let value: Choice<u16> = Choice::Value(7); let answer=choose(value); }",
    );
    let p = &result.logical.semantics.post_ast;
    let variant = p
        .declarations
        .variants
        .iter()
        .find(|v| v.template.is_some() && !v.fields.is_empty())
        .unwrap();
    assert!(matches!(
        p.types.entries[p.declarations.fields[variant.fields[0].0 as usize].ty.0 as usize].kind,
        TypeDefinition::Numeric(NumericType::U16)
    ));
    let construct = p
        .bodies
        .iter()
        .flat_map(|b| &b.operations)
        .find_map(|o| match o {
            Operation::ConstructEnum(c) => Some(c),
            _ => None,
        })
        .unwrap();
    assert!(
        p.declarations.variants[construct.variant.0 as usize]
            .template
            .is_some()
    );
}

#[test]
fn generic_named_constructors_infer_from_the_supplied_fields() {
    resolve(
        "struct Boxed<T> { value: T; } enum Message<T> { Data { value: T; }; Empty; } fn main() { let value=Boxed { value: 7 }; let message=Message::Data { value: true }; if let Message::Data { value: flag } = message { let copy=flag; } }",
    );
}

#[test]
fn propagation_and_unwrap_select_canonical_option_result_routes() {
    let result = resolve(
        "fn option(value: Option<i64>) Option<i64> { Some(value?) } fn result(value: Result<i64, u8>) Result<i64, u8> { Ok(value?) } fn unwrap(value: Option<&i64>) &i64 { value! }",
    );
    let p = &result.logical.semantics.post_ast;
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::PropagateResult(_)))
    );
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::PropagateOption(_)))
    );
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o,Operation::UnwrapOption(u)if u.reference.is_some()))
    );
    assert!(
        p.values
            .provenance
            .iter()
            .any(|p| matches!(p.kind, ProvenanceKind::Projection { .. }))
    );
}

#[test]
fn error_conversion_is_resolved_once_and_runs_only_in_the_failure_branch() {
    let result = resolve(
        "struct Inner { code: u8; } struct Outer { code: u8; fn from(error: Inner) Self { Self { code: error.code } } } fn lift(value: Result<i64,Inner>) Result<i64,Outer> { Ok(value?) }",
    );
    let p = &result.logical.semantics.post_ast;
    let propagation = p
        .bodies
        .iter()
        .flat_map(|b| &b.operations)
        .find_map(|o| match o {
            Operation::PropagateResult(p) => Some(p),
            _ => None,
        })
        .unwrap();
    let ErrorConversion::From(target) = propagation.conversion else {
        panic!()
    };
    let call = p
        .bodies
        .iter()
        .flat_map(|b| &b.operations)
        .find_map(|o| match o {
            Operation::DirectCall(c) if c.target == target => Some(c),
            _ => None,
        })
        .unwrap();
    assert_eq!(call.site.branch, propagation.failure_branch);
    assert!(!p.execution.edges.iter().any(|e|matches!(e,ExecutionEdge::Conditional(c)if c.from==p.scopes.exits[propagation.exit.0 as usize].event&&c.to==propagation.continuation)));
}

#[test]
fn from_overloads_resolve_by_exact_source_type_in_calls_and_propagation() {
    let result = resolve(
        "struct Outer { code: i64; fn from(value: i64) Self { Self { code: value } } fn from(value: u8) Self { Self { code: value as i64 } } } fn lift(value: Result<i64,u8>) Result<i64,Outer> { Ok(value?) } fn main() { let a=Outer::from(1); let small:u8=2; let b=Outer::from(small); }",
    );
    assert_eq!(
        result
            .logical
            .semantics
            .post_ast
            .declarations
            .overloads
            .len(),
        1
    );
    let error = semantic::resolve(
        parse_source(
            "struct Bad { fn from(value:i64) Self { Self{} } fn from(value:i64) Self { Self{} } }"
                .into(),
        )
        .unwrap(),
    )
    .unwrap_err();
    assert_eq!(
        error[0].kind,
        semantic::DiagnosticKind::DuplicateDeclaration
    );
    assert!(!error[0].related.is_empty());
}

#[test]
fn repetition_retains_nested_field_plans_and_evaluates_its_seed_once() {
    let result = resolve(
        "struct Inner { number: i64; } struct Outer { inner: Inner; flag: bool; } fn seed() Outer { Outer { inner: Inner { number: 7 }, flag: true } } fn main() { let repeated = [seed(); 3]; }",
    );
    let p = &result.logical.semantics.post_ast;
    let operations: Vec<_> = p.bodies.iter().flat_map(|b| &b.operations).collect();
    assert_eq!(
        operations
            .iter()
            .filter(|o| matches!(o, Operation::DirectCall(_)))
            .count(),
        1
    );
    let repetition = operations
        .iter()
        .find_map(|o| match o {
            Operation::RepeatArray(r) => Some(r),
            _ => None,
        })
        .unwrap();
    let StructuralReplicationStrategy::Struct(fields) = &repetition.replication.strategy else {
        panic!("missing resolved record plan")
    };
    assert_eq!(fields.len(), 2);
    assert!(
        matches!(&fields[0].plan.strategy, StructuralReplicationStrategy::Struct(inner) if inner.len() == 1 && matches!(inner[0].plan.strategy, StructuralReplicationStrategy::Primitive))
    );
    for field in fields {
        assert_eq!(
            p.declarations.fields[field.field.0 as usize].ty,
            field.plan.ty
        );
    }
}

#[test]
fn repetition_records_restrictions_without_running_a_rule_checker() {
    let result = resolve(
        "struct Resource { fn drop(&mut self) {} } fn main() { let repeated = [Resource{}; 2]; let number = 1; let empty = [&number; 0]; let once = [&number; 1]; }",
    );
    let p = &result.logical.semantics.post_ast;
    let repetitions: Vec<_> = p
        .bodies
        .iter()
        .flat_map(|b| &b.operations)
        .filter_map(|o| match o {
            Operation::RepeatArray(r) => Some(r),
            _ => None,
        })
        .collect();
    assert!(matches!(
        repetitions[0].replication.strategy,
        StructuralReplicationStrategy::Ineligible(
            StructuralReplicationRestriction::CustomDestructor(_)
        )
    ));
    assert!(matches!(
        repetitions[1].replication.strategy,
        StructuralReplicationStrategy::NoDuplication
    ));
    assert!(matches!(
        repetitions[2].replication.strategy,
        StructuralReplicationStrategy::NoDuplication
    ));
    let empty = &p.values.entries[repetitions[1].result.0 as usize];
    let dependencies = &p.values.dependency_summaries[empty.dependencies.0 as usize];
    assert!(dependencies.dependencies.is_empty());
    assert!(dependencies.guarded.is_empty());
}

#[test]
fn dereference_reads_the_descriptor_without_moving_the_reference() {
    let result = resolve("fn read_twice(reference: &i64) i64 { *reference + *reference }");
    let p = &result.logical.semantics.post_ast;
    assert_eq!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .filter(|o| matches!(o, Operation::Dereference(_)))
            .count(),
        2
    );
    assert!(
        !p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::MoveValue(_)))
    );
}

#[test]
fn wrapper_dereference_resolves_methods_once_with_read_or_write_permission() {
    let result = resolve(
        "struct Wrapper { value: i64; fn ref(&self) &i64 { &self.value } fn mut_ref(&mut self) &mut i64 { &mut self.value } } fn main() { let mut wrapper = Wrapper { value: 1 }; let number = *wrapper; *wrapper = 2; }",
    );
    let p = &result.logical.semantics.post_ast;
    let operations: Vec<_> = p.bodies.iter().flat_map(|b| &b.operations).collect();
    assert_eq!(
        operations
            .iter()
            .filter(|o| matches!(o, Operation::MethodCall(_)))
            .count(),
        2
    );
    let dereferences: Vec<_> = operations
        .iter()
        .filter_map(|o| match o {
            Operation::Dereference(d) => Some(&d.access),
            _ => None,
        })
        .collect();
    assert!(dereferences.iter().any(|d| matches!(
        d,
        ResolvedDereference::MethodResult {
            permission: ReferencePermission::Shared,
            ..
        }
    )));
    assert!(dereferences.iter().any(|d| matches!(
        d,
        ResolvedDereference::MethodResult {
            permission: ReferencePermission::Mutable,
            ..
        }
    )));
}

#[test]
fn universal_ref_on_a_reference_borrows_the_descriptor_itself() {
    let result =
        resolve("fn main() { let number = 1; let view = &number; let nested = view.ref(); }");
    let p = &result.logical.semantics.post_ast;
    let binding = p
        .scopes
        .bindings
        .iter()
        .find(|b| p.symbols.entries[b.symbol.0 as usize].spelling == "nested")
        .unwrap();
    let TypeDefinition::Reference { target, .. } = p.types.entries[binding.ty.0 as usize].kind
    else {
        panic!()
    };
    assert!(matches!(
        p.types.entries[target.0 as usize].kind,
        TypeDefinition::Reference { .. }
    ));
}

#[test]
fn for_sources_are_evaluated_once_and_items_keep_borrow_permissions_and_scopes() {
    let result = resolve(
        "fn source() [(i64, i64); 2] { [(1,2),(3,4)] } fn main() { let mut values = source(); for (left, right) in values.mut_ref() { *left += *right; if *left == 3 { continue; } break; } for item in values { let first = item.0; } }",
    );
    let p = &result.logical.semantics.post_ast;
    let operations: Vec<_> = p.bodies.iter().flat_map(|body| &body.operations).collect();
    assert_eq!(
        operations
            .iter()
            .filter(|op| matches!(op, Operation::DirectCall(_)))
            .count(),
        1
    );
    let loops: Vec<_> = operations
        .iter()
        .filter_map(|op| match op {
            Operation::ForControl(control) => Some(control),
            _ => None,
        })
        .collect();
    assert_eq!(loops.len(), 2);
    assert_eq!(loops[0].bindings.len(), 2);
    assert!(matches!(
        loops[0].iteration,
        ResolvedIteration::BorrowedSlice {
            permission: ReferencePermission::Mutable,
            ..
        }
    ));
    assert!(matches!(
        loops[1].iteration,
        ResolvedIteration::FixedArray { length: 2, .. }
    ));
    for binding in &loops[0].bindings {
        assert!(matches!(
            p.types.entries[p.scopes.bindings[binding.0 as usize].ty.0 as usize].kind,
            TypeDefinition::Reference {
                permission: ReferencePermission::Mutable,
                ..
            }
        ));
        assert_ne!(
            p.scopes.bindings[binding.0 as usize].scope,
            loops[0].site.scope
        );
    }
    assert_eq!(
        operations
            .iter()
            .filter(|op| matches!(op, Operation::IterationIndex(_)))
            .count(),
        2
    );
    for control in loops {
        let region = &p.execution.loops[control.region.0 as usize];
        assert!(matches!(
            p.execution.instance_domains[region.instance.0 as usize].definition,
            InstanceDomainDefinition::Iteration { .. }
        ));
    }
}

#[test]
fn for_next_protocol_retains_the_concrete_call_and_option_payload() {
    let result = resolve(
        "struct Counter { count:i64; fn next(&mut self) Option<i64> { if self.count == 0 { None } else { self.count -= 1; Some(self.count) } } } fn main() { for item in (Counter { count: 3 }) { let copied = item; } }",
    );
    let p = &result.logical.semantics.post_ast;
    let operations: Vec<_> = p.bodies.iter().flat_map(|body| &body.operations).collect();
    let control = operations
        .iter()
        .find_map(|op| match op {
            Operation::ForControl(control) => Some(control),
            _ => None,
        })
        .unwrap();
    let ResolvedIteration::NextMethod {
        method,
        some,
        option_type,
        ..
    } = control.iteration
    else {
        panic!()
    };
    assert!(operations.iter().any(|op| matches!(op, Operation::MethodCall(call) if matches!(call.target.target, MethodTarget::Concrete(target) if target == method))));
    assert!(
        operations
            .iter()
            .any(|op| matches!(op, Operation::ExtractVariantField(field) if field.variant == some))
    );
    assert_eq!(p.declarations.variants[some.0 as usize].owner, option_type);
    assert_eq!(control.bindings.len(), 1);
}

#[test]
fn named_child_capture_retains_both_bindings_and_the_move_moment() {
    let result = resolve(
        "struct Owned { number:i64; } fn main() { let value = Owned { number:1 }; let received = { move value; value }; }",
    );
    let p = &result.logical.semantics.post_ast;
    let bindings: Vec<_> = p
        .scopes
        .bindings
        .iter()
        .filter(|b| p.symbols.entries[b.symbol.0 as usize].spelling == "value")
        .collect();
    assert_eq!(bindings.len(), 2);
    assert_ne!(bindings[0].scope, bindings[1].scope);
    let moved = p.bodies.iter().flat_map(|body| &body.operations).find_map(|op| match op {
        Operation::MoveValue(moved) if matches!(moved.source, MoveSource::Place(place) if matches!(p.objects.places[p.objects.evaluated_places[place.0 as usize].definition.0 as usize].root, PlaceRoot::Binding(binding) if binding == bindings[0].id)) => Some(moved), _ => None,
    }).unwrap();
    assert_eq!(moved.site.scope, bindings[1].scope);
    assert!(p.values.provenance.iter().any(
        |v| matches!(v.kind, ProvenanceKind::Move { operation, .. } if operation == moved.site.id)
    ));
}

#[test]
fn structural_contracts_infer_arguments_and_retain_all_matching_alternatives() {
    let r = resolve(
        "struct Source { fn get(&self) i64 { 7 } } #(type: V) #(type: S<V> with { fn get(&self) V; } | { fn get(&self) V; }) fn read(source: &S) V { source.get() } fn main() { let source = Source{}; let value = read(&source); }",
    );
    let p = &r.logical.semantics.post_ast;
    let matched = p
        .contracts
        .matches
        .iter()
        .find(|m| m.matching.rest.len() == 1)
        .unwrap();
    assert_eq!(
        matched.matching.first.methods.first.implementation,
        matched.matching.rest[0].methods.first.implementation
    );
    assert!(
        p.declarations
            .instances
            .iter()
            .any(|i| i.contract_matches.contains(&matched.id))
    );
}

#[test]
fn nominal_type_contracts_and_exact_method_sets_are_resolved() {
    let r = resolve(
        "struct Source { fn get(&self) i64 { 7 } } #(type: V) #(type: S<V> with { fn get(&self) V; }) struct Reader<S,V> { source:S; fn read(&self) V { self.source.get() } } fn main() { let reader:Reader<Source,i64> = Reader { source:Source{} }; let value=reader.read(); }",
    );
    assert!(!r.logical.semantics.post_ast.contracts.matches.is_empty());
    let error = semantic::resolve(parse_source("struct Wrong { fn other(&self) i64 { 1 } } #(type: T with { fn get(&self) i64; }) fn read(source:&T) i64 { source.get() } fn main(){let s=Wrong{};let n=read(&s);}".into()).unwrap()).unwrap_err();
    assert!(error[0].message.contains("structural-contract"));
}

#[test]
fn closures_keep_capture_fields_inferred_returns_and_indirect_call_signatures() {
    let r = resolve(
        "fn call(f:fn(i64) i64) i64 { f(3) } fn shared(f:&fn(i64) i64) i64 { f(4) } fn mutable(f:&mut fn(i64) i64) i64 { f(5) } fn main() { let offset=2; let mut closure=|value:i64| { value+offset }; let a=shared(&closure); let b=mutable(&mut closure); let c=closure(1); let d=call(closure); }",
    );
    let p = &r.logical.semantics.post_ast;
    assert_eq!(p.contracts.captures.len(), 1);
    let record = &p.contracts.captures[0];
    assert!(matches!(
        record.captures[0].mode,
        CaptureMode::PrimitiveCopy
    ));
    let body = p.declarations.instances[record.call.unwrap().0 as usize]
        .body
        .unwrap();
    assert_eq!(p.bodies[body.0 as usize].environment, Some(record.id));
    assert!(
        p.scopes.bindings.iter().any(
            |b| matches!(b.introduced,BindingIntroduction::Capture{record:r,..} if r==record.id)
        )
    );
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::AdaptCallable(_)))
    );
}

#[test]
fn closure_capture_shadowing_and_shared_reference_identity_are_explicit() {
    let r = resolve(
        "fn main(){let number=2;let view=&number;let first=||{*view};let second=move ||{let number=3; number};let n=first();let m=second();}",
    );
    let p = &r.logical.semantics.post_ast;
    assert!(matches!(
        p.contracts.captures[0].captures[0].mode,
        CaptureMode::SharedReferenceCopy
    ));
    assert!(p.contracts.captures[1].captures.is_empty());
    assert!(p.contracts.captures[1].moving);
}

#[test]
fn async_creation_has_no_execution_call_and_await_retains_ready_pending_resume_paths() {
    let r = resolve(
        "async fn child(value:&i64) &i64 { yield; value } async fn parent(value:&i64) &i64 { let task=child(value); task.await } fn main() {let number=3;let task=parent(&number);}",
    );
    let p = &r.logical.semantics.post_ast;
    let creations: Vec<_> = p
        .bodies
        .iter()
        .flat_map(|b| &b.operations)
        .filter_map(|o| match o {
            Operation::CreateFuture(f) => Some(f),
            _ => None,
        })
        .collect();
    assert_eq!(creations.len(), 2);
    for creation in creations {
        assert!(!p.execution.edges.iter().any(
            |e| matches!(e,ExecutionEdge::Call(c)if c.call==creation.site.execution_moments.first)
        ));
    }
    assert_eq!(p.async_frames.len(), 2);
    assert_eq!(p.execution.suspensions.len(), 2);
    assert!(
        p.execution
            .edges
            .iter()
            .any(|e| matches!(e, ExecutionEdge::PollRetry { .. }))
    );
    assert!(
        p.execution
            .edges
            .iter()
            .any(|e| matches!(e, ExecutionEdge::AwaitBody { .. }))
    );
}

#[test]
fn anonymous_async_and_move_blocks_retain_their_environment_and_inferred_output() {
    let r = resolve(
        "async fn main() {let number=3;let view=&number;let task=async {yield; *view};let value=task.await;let result=move {number};}",
    );
    let p = &r.logical.semantics.post_ast;
    assert!(p.contracts.captures.iter().any(|r| r.call.is_some()));
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::EnterMoveBlock(_)))
    );
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::AwaitValue(_)))
    );
}

#[test]
fn parsed_packages_preserve_files_resolve_aliases_and_keep_excluded_imports_out() {
    let module = |path: Vec<&str>, file: &str, source: &str| semantic::ParsedModule {
        package: "app".into(),
        path: path.into_iter().map(str::to_owned).collect(),
        file_path: file.into(),
        syntax: parse_source(source.into()).unwrap(),
    };
    let result=semantic::resolve_package(vec![
        module(vec![],"main.crb","use app::helpers::{Boxed as Box, answer}; fn main(){let value=Box::new(answer());let n=value.get();}"),
        module(vec!["helpers"],"helpers/a.crb","pub struct Boxed {value:i64; pub fn new(value:i64) Self { Self {value} } pub fn get(&self) i64 {self.value}}"),
        module(vec!["helpers"],"helpers/b.crb","pub fn answer() i64 {42} #(if:target.os == \"not-an-os\") use missing::bad; #(endif)"),
    ]).unwrap();
    let p = &result.logical.semantics.post_ast;
    assert_eq!(p.origins.files.len(), 3);
    assert!(p.origins.origins.iter().any(|o| matches!(
        o.role,
        OriginRole::Written {
            file: SourceFileId(2),
            ..
        }
    )));
    assert_eq!(
        result.modules[0].syntax.original_source(),
        "use app::helpers::{Boxed as Box, answer}; fn main(){let value=Box::new(answer());let n=value.get();}"
    );
}

#[test]
fn memory_annotations_and_constant_overrides_retain_specialization_identity() {
    let r = resolve(
        "#(datastack:size=4M,region_size=1M) #(configurable) const SIZE:usize=4; const DOUBLE:usize=2*SIZE; fn make() [u8;DOUBLE]{[0;DOUBLE]} fn main(){let first=make(); #(override:SIZE=8) {let second=make();} let third=make(); #(stack_region:max_size=1M,count=2) { #(free_pages) {let n=1;} } }",
    );
    let p = &r.logical.semantics.post_ast;
    assert_eq!(p.contracts.environments.len(), 2);
    let lengths: Vec<_> = p
        .declarations
        .instances
        .iter()
        .filter_map(|i| {
            let ty = p.declarations.signatures[i.signature.0 as usize].result;
            match p.types.entries[ty.0 as usize].kind {
                TypeDefinition::Array { length, .. } => Some(length),
                _ => None,
            }
        })
        .collect();
    assert!(lengths.contains(&8) && lengths.contains(&16));
    assert_eq!(p.contracts.memory_configuration.len(), 3);
}

#[test]
fn lock_branch_and_thread_annotations_are_resolved_contracts_not_builtin_type_names() {
    let r = resolve(
        "struct End {fn join(self) i64 {3}} #(branch:join=result.join()) fn launch() End {End{}} #(thread:transfer=false) struct Local {} #(lock) struct Protected {pub fn read(&self) i64 {2}} fn main(){let value=Protected{};let n=value.read();let end=launch();let result=end.join();}",
    );
    let p = &r.logical.semantics.post_ast;
    assert_eq!(p.contracts.threads.len(), 1);
    assert!(!p.contracts.locks.is_empty());
    assert_eq!(p.contracts.branches.len(), 1);
    assert!(
        p.contracts
            .applications
            .iter()
            .any(|a| matches!(a, ContractApplication::Completion { .. }))
    );
    assert!(
        p.execution
            .branches
            .iter()
            .any(|b| matches!(b.kind, BranchKind::Concurrent(_)))
    );
}

#[test]
fn defaults_and_cleanup_are_recursive_resolved_recipes_not_backend_type_discovery() {
    let r = resolve(
        "struct Inner{number:i64;} struct Outer{inner:Inner;data:[u8;4];} fn main(){let value=Outer{};drop(value);}",
    );
    let p = &r.logical.semantics.post_ast;
    assert!(
        p.declarations
            .defaults
            .iter()
            .any(|p| matches!(p.kind, DefaultInitializationKind::Struct(_)))
    );
    assert!(
        p.declarations
            .defaults
            .iter()
            .any(|p| matches!(p.kind, DefaultInitializationKind::Array { count: 4, .. }))
    );
    assert!(
        p.contracts
            .destructors
            .iter()
            .any(|d| d.owned_components.len() == 2)
    );
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::DropValue(_)))
    );
}

#[test]
fn configured_object_layout_and_method_keep_the_creation_environment_after_transfer() {
    let r = resolve(
        "#(configurable) const SIZE:usize=4; struct Buffer{data:[u8;SIZE];fn len(&self) usize {self.data.len()}} fn make() Buffer {Buffer{data:[0;SIZE]}} fn main(){let buffer= #(override:SIZE=8) {make()};let length=buffer.len();}",
    );
    let p = &r.logical.semantics.post_ast;
    let buffers: Vec<_> = p
        .declarations
        .structs
        .iter()
        .filter(|s| p.symbols.entries[s.symbol.0 as usize].spelling == "Buffer")
        .collect();
    assert!(buffers.iter().any(|s| s.fields.iter().any(|f| matches!(
        p.types.entries[p.declarations.fields[f.0 as usize].ty.0 as usize].kind,
        TypeDefinition::Array { length: 8, .. }
    ))));
    assert!(p.declarations.instances.iter().any(|i| {
        i.configuration == ConfigurationId(1)
            && p.symbols.entries
                [p.declarations.functions[i.definition.0 as usize].symbol.0 as usize]
                .spelling
                == "len"
    }));
}

#[test]
fn native_pool_allocations_and_collections_keep_typed_ownership_and_borrow_operands() {
    let r = resolve(
        "struct Point {value:i64;} fn update(pool:&mut Pool<Point>){let mut point=pool.new({value:3});let view=point.mut_ref();view.value=4;} fn main(){let mut pool=Pool<Point>::new(32);update(&mut pool);let point=pool.try({value:2})!;let number=(*point).value;let mut values=Vector<&i64>::new();values.push(&number);let old=values.pop();let mut map=HashMap<i64,&i64>::new();let previous=map.insert(7,&number);let key=7;let view=map.get(&key);let fixed:String<64>=String<64>::new();}",
    );
    let p = &r.logical.semantics.post_ast;
    assert!(
        p.types
            .entries
            .iter()
            .any(|t| matches!(t.kind, TypeDefinition::InlineUtf8 { maximum_bytes: 64 }))
    );
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::TryAllocatePoolSlot(_)))
    );
    assert!(
        p.runtime_checks
            .iter()
            .any(|c| matches!(c, RuntimeCheck::PoolCapacity { .. }))
    );
    assert!(!p.objects.collections.is_empty());
}

#[test]
fn runtime_launch_forms_have_concurrent_branches_and_join_or_await_completion() {
    let r = resolve(
        "async fn child(value:&i64) i64 {*value} async fn asynchronous(){let value=1;let child_result=child(&value).await;let blocking=runtime::spawn_blocking(move || {value});let blocking_result=blocking.await!;} fn main(){let value=2;let execution=runtime::spawn(child(&value));let result=execution.join()!;let worker=runtime::thread(move {value});let worker_result=worker.join()!;}",
    );
    let p = &r.logical.semantics.post_ast;
    assert_eq!(
        p.contracts
            .applications
            .iter()
            .filter(|a| matches!(a, ContractApplication::Branch { .. }))
            .count(),
        3
    );
    assert_eq!(
        p.contracts
            .applications
            .iter()
            .filter(|a| matches!(a, ContractApplication::Completion { .. }))
            .count(),
        3
    );
}

#[test]
fn callable_fields_and_temporary_receivers_use_resolved_places_once() {
    let r = resolve(
        "struct Holder { callback:fn(i64) i64; value:i64; fn make() Self {Self {callback:|v:i64| {v+1},value:3}} fn get(&self) i64 {self.value} } fn main(){let holder=Holder::make();let a=holder.callback(1);let b=Holder::make().get();let c=(Holder::make()).value;let d=([holder])[0].callback(2);}",
    );
    let p = &r.logical.semantics.post_ast;
    assert_eq!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .filter(|o| matches!(o, Operation::CallableCall(_)))
            .count(),
        2
    );
    assert!(p.values.provenance.iter().any(|v| matches!(
        v.kind,
        ProvenanceKind::PlaceRead {
            root_value: Some(_),
            ..
        }
    )));
}

#[test]
fn effective_constants_are_values_in_post_ast_not_default_declaration_lookups() {
    let r = resolve(
        "#(configurable) const SIZE:usize=4;fn main(){let first=SIZE;#(override:SIZE=8){let second=SIZE;}}",
    );
    let p = &r.logical.semantics.post_ast;
    assert!(p.values.entries.iter().any(|v| matches!(
        v.definition,
        ValueDefinition::ConfiguredConstant {
            configuration: ConfigurationId(1),
            value: ConstantValue::Integer(8),
            ..
        }
    )));
}

#[test]
fn async_function_items_and_named_task_types_share_the_resolved_future() {
    let r = resolve(
        "async fn child(number:i64) i64 {yield;number} async fn parent() i64 {let call=child;let task:child=call(3);task.await} fn main(){let task:parent=parent();}",
    );
    let p = &r.logical.semantics.post_ast;
    assert!(p.bodies.iter().flat_map(|b|&b.operations).any(|o|matches!(o,Operation::CallableCall(c) if matches!(p.types.entries[p.values.entries[c.result.0 as usize].ty.0 as usize].kind,TypeDefinition::Future{..}))));
}

#[test]
fn projected_references_retain_read_moments_and_descriptor_targets() {
    let r = resolve(
        "struct Views {view:&i64;} fn read(views:&Views) i64 {let view=views.view;*view} fn main(){let n=3;let views=Views{view:&n};let result=read(&views);let entries=[&n];let view=entries[0];let value=*view;let pair=(&n,1);let other=pair.0;let copied=*other;}",
    );
    let p = &r.logical.semantics.post_ast;
    assert!(
        p.values
            .dependency_summaries
            .iter()
            .flat_map(|s| &s.dependencies)
            .any(|d| matches!(d, DependencyRequirement::CarriedByPlace { .. }))
    );
    assert!(p.objects.references.iter().any(|r| {
        p.objects.places[r.origins.first.target.0 as usize]
            .projections
            .len()
            > 1
    }));
}

#[test]
fn contexts_are_retained_for_later_checking_not_verified_during_population() {
    let r = resolve("async fn child() i64 {yield;1} fn main(){let result=child().await;}");
    let p = &r.logical.semantics.post_ast;
    assert!(p.obligations.execution_context.iter().any(|r| matches!(
        r.required,
        FunctionExecution::Asynchronous
    ) && matches!(
        r.actual,
        FunctionExecution::Synchronous
    )));
}

#[test]
fn nested_literal_constraints_and_explicit_receiver_namespaces_compose() {
    let r = resolve(
        "fn pick(value:i64) i64{value} struct Holder{value:i64;fn pick(&self) i64 {pick(self.value)} } fn main(){let at:u64=3;let index=4096+at%32768;let object=Holder{value:2};let value=object.pick();}",
    );
    let p = &r.logical.semantics.post_ast;
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o,Operation::Add(a)if a.domain==NumericType::U64))
    );
}

#[test]
fn primitive_views_and_fallible_conversions_retain_typed_operands() {
    let result=semantic::resolve_package(vec![
        semantic::ParsedModule{package:"std".into(),path:vec!["text".into()],file_path:"text/utf8.crb".into(),syntax:parse_source(include_str!("../../stdlib/src/text/utf8.crb").into()).unwrap()},
        semantic::ParsedModule{package:"app".into(),path:vec![],file_path:"main.crb".into(),syntax:parse_source("fn main(){let bytes=\"text\".as_bytes();let text=str::from_utf8(bytes)!;let wide:u64=3;let small=u8::try_from(wide)!;}".into()).unwrap()},
    ]).unwrap();
    let p = &result.logical.semantics.post_ast;
    assert_eq!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .filter(|o| matches!(
                o,
                Operation::NativeOperation(NativeOperation {
                    kind: NativeOperationKind::Primitive(_),
                    ..
                })
            ))
            .count(),
        3
    );
}

#[test]
fn classical_shadowing_preserves_old_binding_identity_and_borrow_targets() {
    let r = resolve(
        "struct Item{value:i64;} fn main(){let value=Item{value:1};let view=&value;let value=Item{value:2};let first=view.value;let second=value.value;let (base,extra)=(1,2);let (base,extra)=(base+extra,3);}",
    );
    let p = &r.logical.semantics.post_ast;
    let bindings: Vec<_> = p
        .scopes
        .bindings
        .iter()
        .filter(|b| p.symbols.entries[b.symbol.0 as usize].spelling == "value")
        .collect();
    assert_eq!(bindings.len(), 2);
    assert_ne!(bindings[0].id, bindings[1].id);
    assert_eq!(bindings[0].scope, bindings[1].scope);
    assert!(p.objects.references.iter().any(|r|matches!(p.objects.places[r.origins.first.target.0 as usize].root,PlaceRoot::Binding(b)if b==bindings[0].id)));
}

#[test]
fn mixed_integer_shift_counts_keep_the_shifted_domain() {
    let r = resolve(
        "fn main(){let mut byte:u8=255;let count:u64=2;let first=byte>>count;byte<<=count;let second:u16=1;let amount:u32=3;let shifted=second<<amount;}",
    );
    let p = &r.logical.semantics.post_ast;
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o,Operation::ShiftRight(s)if s.domain==NumericType::U8))
    );
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o,Operation::ShiftLeftAssign(s)if s.domain==NumericType::U8))
    );
}

#[test]
fn runtime_waits_share_poll_transition_and_namespace_exports() {
    let module = |package: &str, path: Vec<&str>, source: &str| semantic::ParsedModule {
        package: package.into(),
        path: path.into_iter().map(str::to_owned).collect(),
        file_path: "test.crb".into(),
        syntax: parse_source(source.into()).unwrap(),
    };
    let r = semantic::resolve_package(vec![
        module("std", vec!["runtime"], "pub fn ordinary() i64{1}"),
        module(
            "std",
            vec!["sync", "asyn"],
            "pub async fn wait(raw:usize) i64 {runtime::wait_mutex(raw)}",
        ),
    ])
    .unwrap();
    let p = &r.logical.semantics.post_ast;
    assert_eq!(p.declarations.native_namespaces.len(), 1);
    assert!(
        p.execution
            .predicates
            .iter()
            .any(|p| matches!(p.kind, PredicateKind::RuntimeReady { .. }))
    );
    assert!(
        p.execution
            .edges
            .iter()
            .any(|e| matches!(e, ExecutionEdge::PollRetry { .. }))
    );
}

#[test]
fn public_enum_payload_is_constructible_across_modules_with_private_struct_fields_preserved() {
    let module = |path: Vec<&str>, source: &str| semantic::ParsedModule {
        package: "app".into(),
        path: path.into_iter().map(str::to_owned).collect(),
        file_path: "test.crb".into(),
        syntax: parse_source(source.into()).unwrap(),
    };
    semantic::resolve_package(vec![
        module(vec!["errors"], "pub enum Error{Os{code:i64;};}"),
        module(
            vec![],
            "use app::errors::Error;fn main(){let e=Error::Os{code:3};}",
        ),
    ])
    .unwrap();
    let refused = semantic::resolve_package(vec![
        module(vec!["data"], "pub struct Secret{value:i64;}"),
        module(
            vec![],
            "use app::data::Secret;fn main(){let s=Secret{value:3};}",
        ),
    ]);
    assert!(refused.is_err());
}

#[test]
fn symbolic_error_enum_context_is_retained_through_result_construction() {
    resolve(
        "#(type:E) enum Failure<E>{Read(E);Bad;} #(type:E) fn sample() Result<Option<u8>,Failure<E>>{if true{return Err(Failure::Bad);}Ok(None)} fn main(){}",
    );
}

#[test]
fn symbolic_error_context_survives_contracted_receiver_calls() {
    resolve(
        "#(type:E) enum Failure<E>{Read{error:E;};Bad;} #(type:E) #(type:R<E> with {fn read(&mut self,output:&mut [u8]) Result<usize,E>;}) struct Reader<R,E>{source:&mut R;fn one(&mut self) Result<Option<u8>,Failure<E>> {let mut byte:[u8;1]=[0;1];let stream=&mut *self.source;let count=match stream.read(&mut byte[..]){Ok(n)=>{n},Err(error)=>{return Err(Failure::Read{error});}};if count!=1{return Err(Failure::Bad);}Ok(Some(byte[0]))}} fn main(){}",
    );
}

#[test]
fn unused_generic_bodies_have_resolved_contract_calls_and_no_sample_instances() {
    let r = resolve(
        "#(type:T with {fn get(&self) i64;}) fn read(source:&T) i64 {source.get()} fn main(){}",
    );
    let p = &r.logical.semantics.post_ast;
    let definition = p
        .declarations
        .functions
        .iter()
        .find(|f| !f.type_parameters.is_empty())
        .unwrap();
    let canonical = &p.declarations.instances[definition.parametric_body.unwrap().0 as usize];
    assert!(matches!(
        canonical.resolution,
        InstanceResolution::Parametric { .. }
    ));
    assert_eq!(
        p.declarations
            .instances
            .iter()
            .filter(|i| i.definition == definition.id)
            .count(),
        1
    );
    assert!(p.bodies[canonical.body.unwrap().0 as usize].operations.iter().any(|op|matches!(op,Operation::MethodCall(call) if matches!(call.target.target,MethodTarget::ContractAlternatives(_)))));
    semantic::validate_population(&r.logical).unwrap();
}

#[test]
fn symbolic_forwarding_retains_contract_entailment_evidence() {
    let r = resolve(
        "#(type:T with {fn get(&self) i64;}) fn read(source:&T) i64 {source.get()} #(type:U with {fn get(&self) i64;}) fn forward(source:&U) i64 {read(source)} fn main(){}",
    );
    let p = &r.logical.semantics.post_ast;
    assert!(!p.contracts.symbolic_requirements.is_empty());
    assert!(
        p.contracts
            .symbolic_requirements
            .iter()
            .all(|r| !r.evidence.is_empty())
    );
    semantic::validate_population(&r.logical).unwrap();
    let bad = semantic::resolve(parse_source("#(type:T with {fn get(&self) i64;}) fn read(source:&T) i64 {source.get()} #(type:U) fn forward(source:&U) i64 {read(source)} fn main(){}".to_owned()).unwrap());
    assert!(
        bad.is_err(),
        "an unconstrained parameter cannot satisfy a structural contract"
    );
}

#[test]
fn symbolic_async_contract_keeps_an_inactive_future_and_poll_protocol() {
    let r = resolve(
        "#(type:T with {async fn read(&mut self) i64;}) async fn run(source:&mut T) i64 {source.read().await} fn main(){}",
    );
    let p = &r.logical.semantics.post_ast;
    assert!(
        p.types
            .entries
            .iter()
            .any(|t| matches!(t.kind, TypeDefinition::ContractFuture { .. }))
    );
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::CreateContractFuture(_)))
    );
    semantic::validate_population(&r.logical).unwrap();
}

#[test]
fn symbolic_moves_and_closure_captures_retain_type_dependent_transfer() {
    let r = resolve("#(type:T) fn keep(value:T) {let f=move || {value};} fn main(){}");
    let p = &r.logical.semantics.post_ast;
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::ParametricTransfer(_)))
    );
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::CaptureParametric(_)))
    );
    semantic::validate_population(&r.logical).unwrap();
}

#[test]
fn abstract_enum_payload_copy_eligibility_is_not_prematurely_a_move() {
    let r = resolve(
        "enum Item<T>{Value(T);Empty;} #(type:T) fn relay(item:Item<T>) Item<T> {item} fn main(){}",
    );
    let p = &r.logical.semantics.post_ast;
    assert!(p.bodies.iter().flat_map(|b|&b.operations).any(|op|matches!(op,Operation::ParametricTransfer(t) if matches!(p.types.entries[t.ty.0 as usize].kind,TypeDefinition::Nominal{..}))));
    semantic::validate_population(&r.logical).unwrap();
}
