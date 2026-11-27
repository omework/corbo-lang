//! Physical planning tests start from CheckedPostAst. They verify general
//! planning mechanisms and never invoke the legacy placement/backend pipeline.
use corbo_frontend::{memory_plan, parse_source, post_ast::*, rule_check, semantic};

fn plan(source: &str) -> PlannedPostAst {
    let syntax = parse_source(source.to_owned()).unwrap();
    let resolved = semantic::resolve(syntax)
        .unwrap_or_else(|diagnostics| panic!("semantic failure: {diagnostics:#?}"));
    let checked = match rule_check::verify(resolved.logical) {
        RuleAnalysisResult::Established(checked) => checked,
        RuleAnalysisResult::Rejected(rejected) => {
            panic!("rule rejection: {:#?}", rejected.diagnostics)
        }
        RuleAnalysisResult::MissingSemanticInput(incomplete) => {
            panic!("missing semantic facts: {:#?}", incomplete.missing)
        }
    };
    match memory_plan::plan(checked) {
        MemoryPlanningResult::Planned(planned) => {
            memory_plan::validate(&planned)
                .unwrap_or_else(|errors| panic!("invalid physical artifact: {errors:#?}"));
            planned
        }
        MemoryPlanningResult::Rejected(rejected) => {
            panic!("physical rejection: {:#?}", rejected.diagnostics)
        }
        MemoryPlanningResult::MissingPlanInput(incomplete) => {
            panic!("missing plan facts: {:#?}", incomplete.missing)
        }
    }
}

fn checked(source: &str) -> CheckedPostAst {
    let syntax = parse_source(source.to_owned()).unwrap();
    let resolved = semantic::resolve(syntax).unwrap();
    match rule_check::verify(resolved.logical) {
        RuleAnalysisResult::Established(checked) => checked,
        other => panic!("expected checked input, got {other:#?}"),
    }
}

#[test]
fn layouts_nested_fixed_values_and_reserves_child_result_in_parent() {
    let planned = plan(
        "struct Pair { left: i64; right: i64; } fn main(){let pair:Pair={let local=Pair{left:1,right:2};local};let n=pair.left;}",
    );
    let pair = planned
        .layouts
        .layouts
        .iter()
        .find(|layout| layout.fields.len() == 2)
        .unwrap();
    assert!(matches!(pair.size, LayoutSize::Fixed(16)));
    assert_eq!(pair.alignment, 8);
    assert!(
        planned
            .reservations
            .iter()
            .any(|assignment| matches!(assignment.issuer, ReservationIssuer::Parent { .. }))
    );
    assert_eq!(
        planned.realization.len(),
        planned.checked_flow.semantics.physical_requirements.len()
    );
}

#[test]
fn final_storage_is_available_when_its_value_is_initialized() {
    let planned = plan("fn main(){let left:i64=20;let right:i64=22;let result=left+right;}");
    let p = &planned.checked_flow.semantics.semantics.post_ast;

    for assignment in &planned.reservations {
        let final_ = &planned.checked_flow.semantics.finals[assignment.destination.0 as usize];
        let produced_at = match p.values.entries[final_.value.0 as usize].definition {
            ValueDefinition::OperationResult { produced_at, .. }
            | ValueDefinition::ConditionalResult { produced_at, .. } => produced_at,
            _ => assignment.construction_at,
        };
        assert_eq!(assignment.initialization_at, produced_at);
        if matches!(assignment.issuer, ReservationIssuer::ExistingStorage { .. }) {
            assert_eq!(assignment.reserved_at, produced_at);
        }
    }

    let first = &planned.storage.reservations[0];
    let scope_storage = p
        .scopes
        .storage
        .iter()
        .find(|storage| storage.scope == first.destination)
        .unwrap();
    assert_eq!(
        first.start, p.cursor_snapshots[scope_storage.entry.0 as usize].cursor,
        "physical planning must not allocate semantic cursor advances twice"
    );
}

#[test]
fn fixed_pool_slots_follow_the_descriptor_on_the_classic_stack() {
    let planned = plan("fn main(){let mut pool=Pool<i64>::new(4);let item=pool.new(1);}");
    let backing = planned.storage.backings.iter().find_map(|backing| {
        if let BackingStorageKind::PoolSlots {
            element,
            capacity,
            stack,
            slots_start,
            occupancy_end,
            ..
        } = backing.kind
        {
            Some((element, capacity, stack, slots_start, occupancy_end))
        } else {
            None
        }
    });
    let (_, _, stack, start, end) = backing.expect("pool slot backing");
    assert_ne!(start, end);
    assert!(matches!(
        planned.storage.stacks[stack.0 as usize].kind,
        DataStackKind::FixedValues
    ));
}

#[test]
fn growing_vector_keeps_its_descriptor_fixed_and_payload_regional() {
    let planned = plan(
        "#(datastack:size=4M,region_stack_size=4M,region_size=1M) fn main(){let mut values=Vector<i64>::new();values.push(1);}",
    );
    assert_eq!(planned.storage.regions.len(), 1);
    assert!(matches!(
        planned.storage.regions[0].size,
        MemoryBudget::Explicit(1_048_576)
    ));
    assert!(planned.storage.reservations.iter().any(|reservation| {
        reservation.region == Some(planned.storage.regions[0].id)
            && matches!(
                planned.storage.stacks[reservation.stack.0 as usize].kind,
                DataStackKind::FixedValues
            )
    }));
}

#[test]
fn verified_destruction_precedes_cursor_recovery() {
    let planned = plan("fn main(){let mut pool=Pool<i64>::new(1);let item=pool.new(1);}");
    assert!(planned.cleanup.exits.iter().any(|exit| {
        let rewind = exit
            .actions
            .iter()
            .position(|action| matches!(action, CleanupAction::RewindCursor { .. }));
        let release = exit
            .actions
            .iter()
            .position(|action| matches!(action, CleanupAction::ReleaseAllocation { .. }));
        matches!((release, rewind), (Some(release), Some(rewind)) if release < rewind)
    }));
}

#[test]
fn ordinary_fixed_addresses_end_logically_without_releasing_pool_slots() {
    let planned = plan("enum Choice{Empty;Data(i64);} fn main(){let item=Choice::Data(1);}");
    assert!(planned.cleanup.exits.iter().all(|exit| {
        !exit
            .actions
            .iter()
            .any(|action| matches!(action, CleanupAction::ReleaseAllocation { .. }))
    }));
    assert!(planned.cleanup.exits.iter().any(|exit| {
        exit.actions
            .iter()
            .any(|action| matches!(action, CleanupAction::RewindCursor { .. }))
    }));
}

#[test]
fn async_state_has_a_target_layout_before_lowering() {
    let planned = plan("async fn work(value:i64) i64{yield;value} fn main(){}");
    let p = &planned.checked_flow.semantics.semantics.post_ast;
    assert!(!p.async_frames.is_empty());
    for frame in &p.async_frames {
        assert!(
            planned
                .layouts
                .layouts
                .iter()
                .any(|layout| layout.ty == frame.state_type)
        );
    }
}

#[test]
fn caller_reserves_new_aggregate_results() {
    let planned = plan(
        "struct Item{value:i64;} fn make() Item{Item{value:7}} fn main(){let item=make();let value=item.value;}",
    );
    assert!(
        planned
            .reservations
            .iter()
            .any(|assignment| matches!(assignment.issuer, ReservationIssuer::Caller { .. }))
    );
    let caller_requirements = planned
        .checked_flow
        .semantics
        .physical_requirements
        .iter()
        .filter(|requirement| {
            matches!(
                requirement.kind,
                PhysicalPlacementRequirementKind::CallerProvided { .. }
            )
        })
        .count();
    assert!(caller_requirements > 0);
    assert_eq!(
        planned.realization.len(),
        planned.checked_flow.semantics.physical_requirements.len()
    );
}

#[test]
fn enum_array_and_tuple_layouts_are_target_resolved() {
    let planned = plan(
        "enum Choice{Empty;Data([u16;3]);} struct Boxed{pair:(u8,u64);choice:Choice;} fn main(){let value=Boxed{pair:(1,2),choice:Choice::Data([3;3])};}",
    );
    assert!(
        planned
            .layouts
            .layouts
            .iter()
            .any(|layout| layout.variant.is_some())
    );
    assert!(
        planned
            .layouts
            .layouts
            .iter()
            .any(|layout| { matches!(layout.size, LayoutSize::Fixed(6)) && layout.alignment == 2 })
    );
    assert!(
        planned
            .layouts
            .layouts
            .iter()
            .all(|layout| layout.alignment > 0)
    );
}

#[test]
fn exclusive_branch_constructions_may_share_one_compatible_reservation() {
    let planned = plan(
        "struct Item{value:i64;} fn main(){let flag=true;let item:Item=if flag{Item{value:1}}else{Item{value:2}};let value=item.value;}",
    );
    assert!(
        planned.sharing.iter().any(|group| {
            1 + group.initializers.rest.len() >= 2
                && group.exclusivity_evidence.0 < planned.physical_proofs.len() as u32
                && group.compatibility_evidence.0 < planned.physical_proofs.len() as u32
        }),
        "finals={:#?}\npredicates={:#?}\nassignments={:#?}\nreservations={:#?}",
        planned.checked_flow.semantics.finals,
        planned
            .checked_flow
            .semantics
            .semantics
            .post_ast
            .execution
            .predicates,
        planned.reservations,
        planned.storage.reservations
    );
}

#[test]
fn value_built_before_later_exclusive_exits_has_one_causal_address() {
    let planned = plan(
        "struct Marker{value:i64;fn drop(&mut self){}} fn main(){let mut index:i64=0;while index<3 {let marker=Marker{value:index};index+=1;if index==1 {continue;}break;}}",
    );
    let post = &planned.checked_flow.semantics.semantics.post_ast;
    let marker = post
        .types
        .entries
        .iter()
        .find(|ty| {
            matches!(
                ty.kind,
                TypeDefinition::Nominal { definition, .. }
                    if post.symbols.entries[definition.0 as usize].spelling == "Marker"
            )
        })
        .unwrap()
        .id;
    let storage = planned
        .storage
        .values
        .iter()
        .find(|storage| {
            post.values.entries[storage.value.0 as usize].ty == marker
                && matches!(
                    storage.alternatives.first.kind,
                    ValueStorageKind::Reservation(_)
                )
        })
        .expect("Marker storage");
    assert_eq!(storage.alternatives.first.guard, PredicateId(0));
    assert!(storage.alternatives.rest.is_empty());
}

#[test]
fn local_region_classes_reserve_count_and_overflow_to_a_dedicated_stack() {
    let planned = plan(
        "fn main(){#(stack_region:max_size=4K,count=2){let a=Vector<i64>::new();let b=Vector<i64>::new();let c=Vector<i64>::new();}}",
    );
    assert_eq!(planned.storage.regions.len(), 3);
    assert_eq!(planned.storage.region_classes.len(), 2);
    let dedicated = planned
        .storage
        .stacks
        .iter()
        .filter(|stack| stack.id.0 >= 2)
        .collect::<Vec<_>>();
    assert_eq!(dedicated.len(), 2);
    assert!(
        dedicated
            .iter()
            .all(|stack| matches!(stack.capacity, MemoryBudget::Explicit(8_192)))
    );
}

#[test]
fn string_and_hash_map_descriptors_use_fixed_storage_with_regional_payloads() {
    let planned = plan("fn main(){let text=String::new();let map=HashMap<i64,i64>::new();}");
    assert_eq!(planned.storage.regions.len(), 2);
    assert!(
        planned
            .storage
            .regions
            .iter()
            .all(|region| matches!(region.size, MemoryBudget::PlatformDefault))
    );
    assert!(
        planned
            .storage
            .reservations
            .iter()
            .all(|reservation| matches!(
                planned.storage.stacks[reservation.stack.0 as usize].kind,
                DataStackKind::FixedValues
            ))
    );
}

#[test]
fn explicit_capacity_smaller_than_a_proven_fixed_plan_is_rejected() {
    let result = memory_plan::plan(checked(
        "#(datastack:size=1K) fn main(){let bytes:[u8;2048]=[0;2048];}",
    ));
    match result {
        MemoryPlanningResult::Rejected(rejected) => {
            assert!(rejected.diagnostics.first.requirement.is_none());
            assert!(
                !rejected
                    .diagnostics
                    .first
                    .conflicting_reservations
                    .is_empty()
            );
        }
        other => panic!("expected physical capacity rejection, got {other:#?}"),
    }
}

#[test]
fn planner_uses_each_supported_target_description() {
    for (os, family, architecture) in [
        ("linux", "unix", "x86_64"),
        ("linux", "unix", "aarch64"),
        ("macos", "unix", "x86_64"),
        ("macos", "unix", "aarch64"),
        ("windows", "windows", "x86_64"),
        ("windows", "windows", "aarch64"),
    ] {
        let source = "struct Pair{left:u8;right:u64;} fn main(){let pair=Pair{left:1,right:2};}";
        let modules = vec![semantic::ParsedModule {
            package: "sample".into(),
            path: vec![],
            file_path: "src/main.crb".into(),
            syntax: parse_source(source.into()).unwrap(),
        }];
        let resolved = semantic::resolve_package_for_target(
            modules,
            TargetDescription {
                os: os.into(),
                family: family.into(),
                architecture: architecture.into(),
                pointer_bits: 64,
                endian: Endian::Little,
                abi: AbiId(0),
            },
        )
        .unwrap();
        let checked = match rule_check::verify(resolved.logical) {
            RuleAnalysisResult::Established(checked) => checked,
            other => panic!("{os}-{architecture}: {other:#?}"),
        };
        let planned = match memory_plan::plan(checked) {
            MemoryPlanningResult::Planned(planned) => planned,
            other => panic!("{os}-{architecture}: {other:#?}"),
        };
        memory_plan::validate(&planned).unwrap();
        let pair = planned
            .layouts
            .layouts
            .iter()
            .find(|layout| layout.fields.len() == 2)
            .unwrap();
        assert!(matches!(pair.size, LayoutSize::Fixed(16)));
    }
}
