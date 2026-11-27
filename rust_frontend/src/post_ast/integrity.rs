//! Structural PostAST handoff validation. This does not decide N1–N8.
//! It checks that consumers can dereference populated IDs without going back to AST.
use crate::post_ast::*;
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IntegrityError(pub String);

pub fn validate_population(result: &LogicalDestinationResult) -> Result<(), Vec<IntegrityError>> {
    let p = &result.semantics.post_ast;
    let mut failures = Vec::new();
    macro_rules! require {
        ($condition:expr, $message:expr) => {
            if !$condition {
                failures.push(IntegrityError($message.into()));
            }
        };
    }
    for link in &p.objects.value_entities {
        require!(
            (link.value.0 as usize) < p.values.entries.len(),
            "entity/value link has no value"
        );
        require!(
            (link.guard.0 as usize) < p.execution.predicates.len(),
            "entity/value link has no guard"
        );
        let valid = match link.entity {
            EntityId::Address(id) => (id.0 as usize) < p.objects.addresses.len(),
            EntityId::Reference(id) => (id.0 as usize) < p.objects.references.len(),
            EntityId::Collection(id) => (id.0 as usize) < p.objects.collections.len(),
        };
        require!(valid, "entity/value link has no entity");
    }
    let mut operations = HashMap::new();
    for body in &p.bodies {
        require!(
            (body.scope.0 as usize) < p.scopes.entries.len(),
            "body scope is missing"
        );
        for operation in &body.operations {
            let foreign = match operation {
                Operation::ForeignC(o) => Some((o.region, &o.operands, &o.outputs)),
                Operation::ForeignCpp(o) => Some((o.region, &o.operands, &o.outputs)),
                Operation::ForeignAssembly(o) => Some((o.region, &o.operands, &o.outputs)),
                _ => None,
            };
            if let Some((region, operands, outputs)) = foreign {
                require!(
                    (region.0 as usize) < p.foreign_regions.len(),
                    "foreign region is missing"
                );
                for operand in operands {
                    require!(
                        (operand.place.0 as usize) < p.objects.evaluated_places.len(),
                        "foreign operand place is missing"
                    );
                    require!(
                        (operand.value.0 as usize) < p.values.entries.len(),
                        "foreign operand value is missing"
                    );
                    if let Some(value) = p.values.entries.get(operand.value.0 as usize) {
                        require!(
                            value.ty == operand.ty,
                            "foreign operand type disagrees with its resolved value"
                        );
                    }
                }
                for output in outputs {
                    require!(
                        (output.place.0 as usize) < p.objects.evaluated_places.len(),
                        "foreign write-back place is missing"
                    );
                    require!(
                        (output.result.0 as usize) < p.values.entries.len(),
                        "foreign write-back value is missing"
                    );
                }
            }
            match operation {
                Operation::NativeOperation(native) => {
                    for argument in &native.arguments {
                        require!(
                            (argument.value.0 as usize) < p.values.entries.len(),
                            "primitive argument value is missing"
                        );
                    }
                    if let NativeOperationKind::Primitive(primitive) = &native.kind {
                        match primitive {
                            PrimitiveOperation::View { source, target, .. } => {
                                require!(
                                    (source.0 as usize) < p.objects.evaluated_places.len(),
                                    "primitive view source place is missing"
                                );
                                require!(
                                    (target.0 as usize) < p.types.entries.len(),
                                    "primitive view target type is missing"
                                );
                            }
                            PrimitiveOperation::ValidateUtf8 { bytes, error } => {
                                require!(
                                    (bytes.0 as usize) < p.values.entries.len(),
                                    "UTF-8 input value is missing"
                                );
                                require!(
                                    (error.0 as usize) < p.types.entries.len(),
                                    "UTF-8 error type is missing"
                                );
                            }
                            PrimitiveOperation::TryNumericConversion { source, target } => {
                                require!(
                                    (source.0 as usize) < p.values.entries.len(),
                                    "numeric conversion source is missing"
                                );
                                require!(
                                    (target.0 as usize) < p.types.entries.len(),
                                    "numeric conversion target is missing"
                                );
                            }
                            PrimitiveOperation::Runtime {
                                suspension: Some(id),
                                ..
                            } => {
                                require!(
                                    (id.0 as usize) < p.execution.suspensions.len(),
                                    "runtime wait suspension is missing"
                                );
                                require!(p.execution.edges.iter().any(|edge|matches!(edge,ExecutionEdge::PollRetry{suspension,..}if suspension==id)),"runtime wait has no resume-to-poll path");
                            }
                            PrimitiveOperation::Runtime { .. } => {}
                        }
                    }
                }
                Operation::RepeatArray(repetition) => {
                    validate_replication(p, &repetition.replication, &mut failures);
                    require!(
                        (repetition.seed.0 as usize) < p.values.entries.len(),
                        "repetition seed is missing"
                    );
                    require!(
                        (repetition.result.0 as usize) < p.values.entries.len(),
                        "repetition result is missing"
                    );
                }
                Operation::IterationIndex(index) => {
                    require!(
                        p.execution
                            .iteration_variables
                            .get(index.coordinate.0 as usize)
                            .is_some_and(|coordinate| coordinate.region == index.region),
                        "iteration index does not reference its region's coordinate"
                    );
                }
                Operation::ForControl(control) => {
                    require!(
                        (control.region.0 as usize) < p.execution.loops.len(),
                        "for-loop region is missing"
                    );
                    for binding in &control.bindings {
                        require!(
                            (binding.0 as usize) < p.scopes.bindings.len(),
                            "for-loop pattern binding is missing"
                        );
                    }
                }
                Operation::Dereference(dereference) => {
                    if let ResolvedDereference::MethodResult { function, .. } = dereference.access {
                        require!(
                            (function.0 as usize) < p.declarations.instances.len(),
                            "dereference method instance is missing"
                        );
                        require!(p.bodies.iter().flat_map(|body| &body.operations).any(|operation|
                            matches!(operation, Operation::MethodCall(call) if call.result == dereference.source
                                && matches!(call.target.target, MethodTarget::Concrete(target) if target == function))),
                            "dereference result is not linked to its already-emitted method call");
                    }
                }
                _ => {}
            }
            let site = operation.site();
            require!(
                operations.insert(site.id, site).is_none(),
                "operation ID has multiple definitions"
            );
            require!(
                site.body == body.id,
                "operation belongs to a different body"
            );
            require!(
                (site.scope.0 as usize) < p.scopes.entries.len(),
                "operation scope is missing"
            );
            require!(
                (site.origin.0 as usize) < p.origins.origins.len(),
                "operation source origin is missing"
            );
            for id in
                std::iter::once(&site.execution_moments.first).chain(&site.execution_moments.rest)
            {
                match p.execution.execution_moments.get(id.0 as usize) {
                    Some(moment) => {
                        require!(
                            moment.operation == site.id
                                && moment.body == site.body
                                && moment.timeline == site.timeline
                                && moment.branch == site.branch,
                            "operation and execution moment disagree"
                        );
                    }
                    None => failures.push(IntegrityError("operation event is missing".into())),
                }
            }
        }
    }
    let mut obligation_ids = HashSet::new();
    macro_rules! validate_obligations {
        ($items:expr) => {
            for obligation in $items {
                let site = &obligation.site;
                require!(
                    obligation_ids.insert(site.id),
                    "rule obligation ID has multiple definitions"
                );
                require!(
                    operations.contains_key(&site.operation),
                    "rule obligation has no semantic operation"
                );
                require!(
                    p.execution
                        .execution_moments
                        .get(site.moment.0 as usize)
                        .is_some_and(|moment| moment.operation == site.operation),
                    "rule obligation moment disagrees with its operation"
                );
                require!(
                    (site.guard.0 as usize) < p.execution.predicates.len(),
                    "rule obligation guard is missing"
                );
                require!(
                    (site.origin.0 as usize) < p.origins.origins.len(),
                    "rule obligation source origin is missing"
                );
            }
        };
    }
    validate_obligations!(&p.obligations.n1);
    validate_obligations!(&p.obligations.n2);
    validate_obligations!(&p.obligations.n3);
    validate_obligations!(&p.obligations.n4);
    validate_obligations!(&p.obligations.n5);
    validate_obligations!(&p.obligations.n6);
    validate_obligations!(&p.obligations.n7);
    validate_obligations!(&p.obligations.n8);
    let n1_values = p
        .obligations
        .n1
        .iter()
        .filter_map(|obligation| match obligation.requirement {
            InitializationAndTypeRequirement::TypeIdentity { value, .. } => Some(value),
            InitializationAndTypeRequirement::RuntimeCheck { .. } => None,
        })
        .collect::<HashSet<_>>();
    for obligation in &p.obligations.n2 {
        require!(
            p.objects
                .ownership
                .get(obligation.link.0 as usize)
                .is_some_and(|link| link.entity == obligation.entity),
            "N2 obligation does not reference its exact ownership link"
        );
    }
    let n4_links = p
        .obligations
        .n4
        .iter()
        .filter_map(|obligation| match obligation.requirement {
            LifetimeProofRequirement::DependencyLink { link, .. } => Some(link),
            LifetimeProofRequirement::StoredValue { .. }
            | LifetimeProofRequirement::EscapingValue { .. }
            | LifetimeProofRequirement::TransferDestination { .. }
            | LifetimeProofRequirement::FinalDestination { .. }
            | LifetimeProofRequirement::OperationDependencies { .. }
            | LifetimeProofRequirement::BranchDependencies { .. } => None,
        })
        .collect::<HashSet<_>>();
    require!(
        n4_links.len() == p.objects.dependencies.len(),
        "N4 obligations do not identify dependency links uniquely"
    );
    for (index, dependency) in p.objects.dependencies.iter().enumerate() {
        require!(
            dependency.id.0 as usize == index,
            "dependency link ID disagrees with its arena position"
        );
        require!(
            n4_links.contains(&dependency.id),
            "resolved dependency link has no N4 obligation"
        );
    }
    let n3_occurrences = p
        .obligations
        .n3
        .iter()
        .filter_map(|obligation| match &obligation.requirement {
            TransferAndMutationRequirement::Transfer { occurrence, .. } => Some(*occurrence),
            TransferAndMutationRequirement::MutationPermission { .. }
            | TransferAndMutationRequirement::StructuralReplication { .. } => None,
        })
        .collect::<HashSet<_>>();
    require!(
        n3_occurrences.len() == p.transfers.len(),
        "N3 obligations do not identify transfers uniquely"
    );
    for (index, transfer) in p.transfers.iter().enumerate() {
        require!(
            transfer.id.0 as usize == index,
            "transfer occurrence ID disagrees with its arena position"
        );
        require!(
            n3_occurrences.contains(&transfer.id),
            "resolved transfer occurrence has no N3 obligation"
        );
    }
    for obligation in &p.obligations.n7 {
        if let DestructionRequirement::CleanupCandidate { candidate, .. } = &obligation.requirement
        {
            require!(
                result
                    .semantics
                    .lifetimes
                    .cleanup_candidates
                    .get(candidate.0 as usize)
                    .is_some(),
                "N7 obligation has no exact cleanup candidate"
            );
        }
    }
    for (index, value) in p.values.entries.iter().enumerate() {
        require!(
            value.id.0 as usize == index,
            "value ID disagrees with arena position"
        );
        require!(
            (value.ty.0 as usize) < p.types.entries.len(),
            "value type is missing"
        );
        require!(
            (value.dependencies.0 as usize) < p.values.dependency_summaries.len(),
            "value dependency summary is missing"
        );
        require!(
            (value.placement.0 as usize) < p.values.placement_summaries.len(),
            "value placement summary is missing"
        );
        require!(
            (value.provenance.0 as usize) < p.values.provenance.len(),
            "value provenance is missing"
        );
        if let ValueDefinition::OperationResult {
            operation,
            produced_at,
        }
        | ValueDefinition::ConditionalResult {
            operation,
            produced_at,
            ..
        } = value.definition
        {
            require!(
                n1_values.contains(&value.id),
                "operation-produced value has no declared N1 obligation"
            );
            match operations.get(&operation) {
                Some(site) => require!(
                    std::iter::once(&site.execution_moments.first)
                        .chain(&site.execution_moments.rest)
                        .any(|m| *m == produced_at),
                    "result availability is outside its operation"
                ),
                None => failures.push(IntegrityError(
                    "value's producing operation is missing".into(),
                )),
            }
        }
    }
    for (index, moment) in p.execution.execution_moments.iter().enumerate() {
        require!(
            moment.id.0 as usize == index,
            "execution moment ID disagrees with arena position"
        );
        require!(
            operations.contains_key(&moment.operation),
            "execution moment has no semantic operation"
        );
        match p.execution.timelines.get(moment.timeline.0 as usize) {
            Some(timeline) => require!(
                timeline.execution_moments.contains(&moment.id),
                "timeline does not contain its execution moment"
            ),
            None => failures.push(IntegrityError(
                "execution moment timeline is missing".into(),
            )),
        }
        require!(
            (moment.lexical.0 as usize) < p.execution.lexical_moments.len(),
            "execution moment lexical anchor is missing"
        );
        require!(
            (moment.guard.0 as usize) < p.execution.predicates.len(),
            "execution moment predicate is missing"
        );
    }
    for timeline in &p.execution.timelines {
        for id in std::iter::once(&timeline.entries.first)
            .chain(&timeline.entries.rest)
            .chain(&timeline.exits)
        {
            require!(
                timeline.execution_moments.contains(id),
                "timeline entry/exit belongs to a different timeline"
            );
        }
    }
    for reference in &p.objects.references {
        for origin in std::iter::once(&reference.origins.first).chain(&reference.origins.rest) {
            require!(
                (origin.target.0 as usize) < p.objects.places.len(),
                "reference target place is missing"
            );
        }
    }
    for scope in &p.scopes.entries {
        require!(
            (scope.lexical_scope.0 as usize) < p.origins.lexical_scopes.len(),
            "semantic scope has no source scope"
        );
        if let ScopeStorageLink::Runtime(storage) = scope.storage {
            require!(
                (storage.0 as usize) < p.scopes.storage.len(),
                "runtime scope storage facts are missing"
            );
        }
    }
    for transfer in &result.semantics.destinations.transfers {
        require!(
            operations.contains_key(&transfer.operation),
            "transfer has no semantic operation"
        );
        require!(
            (transfer.source.0 as usize) < p.values.entries.len()
                && (transfer.result.0 as usize) < p.values.entries.len(),
            "transfer value is missing"
        );
    }
    for final_ in &result.finals {
        require!(
            (final_.requirement.0 as usize) < result.semantics.destinations.finals.len(),
            "final destination has no requirement"
        );
    }
    // Validate retained semantic identities only. Do not rerun lookup, typing,
    // contract matching, borrowing analysis or destruction-order verification.
    for value in &p.values.entries {
        if let ValueDefinition::ConfiguredConstant {
            constant,
            configuration,
            ..
        } = value.definition
        {
            require!(
                (constant.0 as usize) < p.declarations.constants.len(),
                "configured constant declaration is missing"
            );
            require!(
                (configuration.0 as usize) < p.contracts.environments.len(),
                "constant configuration is missing"
            );
        }
    }
    for provenance in &p.values.provenance {
        if let ProvenanceKind::PlaceRead {
            place,
            root_value,
            operation,
        } = provenance.kind
        {
            require!(
                (place.0 as usize) < p.objects.evaluated_places.len(),
                "read provenance place is missing"
            );
            require!(
                operations.contains_key(&operation),
                "read provenance event is missing"
            );
            if let Some(value) = root_value {
                require!(
                    (value.0 as usize) < p.values.entries.len(),
                    "read provenance root value is missing"
                );
            }
        }
    }
    for namespace in &p.declarations.native_namespaces {
        require!(
            (namespace.module.0 as usize) < p.declarations.modules.len(),
            "native namespace module is missing"
        );
        require!(
            (namespace.compiler_scope.0 as usize) < p.scopes.entries.len(),
            "native namespace source scope is missing"
        );
        for symbol in &namespace.symbols {
            require!(
                (symbol.0 as usize) < p.symbols.entries.len(),
                "native namespace export is missing"
            );
        }
    }
    for capture in &p.contracts.captures {
        require!(
            (capture.ty.0 as usize) < p.types.entries.len(),
            "capture environment type is missing"
        );
        if let Some(function) = capture.call {
            require!(
                (function.0 as usize) < p.declarations.instances.len(),
                "capture callable instance is missing"
            );
        }
        for field in &capture.captures {
            require!(
                (field.field.0 as usize) < p.declarations.fields.len(),
                "capture field is missing"
            );
            require!(
                (field.source.0 as usize) < p.scopes.bindings.len(),
                "capture source binding is missing"
            );
            require!(
                (field.value.0 as usize) < p.values.entries.len(),
                "capture source value is missing"
            );
            require!(
                (field.creation.0 as usize) < p.execution.execution_moments.len(),
                "capture creation event is missing"
            );
        }
    }
    for frame in &p.async_frames {
        require!(
            (frame.function.0 as usize) < p.declarations.instances.len(),
            "async frame instance is missing"
        );
        require!(
            (frame.body.0 as usize) < p.bodies.len(),
            "async frame body is missing"
        );
        require!(
            (frame.state_type.0 as usize) < p.types.entries.len(),
            "async frame state type is missing"
        );
        for slot in &frame.slots {
            require!(
                (slot.binding.0 as usize) < p.scopes.bindings.len(),
                "async slot binding is missing"
            );
            require!(
                (slot.field.0 as usize) < p.declarations.fields.len(),
                "async slot field is missing"
            );
        }
        for suspension in &frame.suspensions {
            require!(
                (suspension.0 as usize) < p.execution.suspensions.len(),
                "async suspension is missing"
            );
        }
    }
    for environment in &p.contracts.environments {
        if let Some(parent) = environment.parent {
            require!(
                parent.0 < environment.id.0,
                "configuration parent must precede its child"
            );
        }
    }
    for definition in &p.declarations.functions {
        if let Some(id) = definition.parametric_body {
            if let Some(instance) = p.declarations.instances.get(id.0 as usize) {
                require!(
                    instance.definition == definition.id,
                    "symbolic body belongs to another definition"
                );
                require!(
                    instance.body.is_some(),
                    "symbolic body has not been populated"
                );
                require!(
                    matches!(instance.resolution, InstanceResolution::Parametric { .. }),
                    "symbolic body is classified as concrete"
                );
                for parameter in &definition.type_parameters {
                    require!(instance.substitutions.iter().any(|s| s.parameter == *parameter && matches!(p.types.entries[s.actual.0 as usize].kind, TypeDefinition::Parameter(id) if id == *parameter)), "symbolic body does not retain its declared parameter identity");
                }
            } else {
                require!(false, "canonical symbolic body is missing");
            }
        }
    }
    for requirement in &p.contracts.symbolic_requirements {
        require!(
            !requirement.evidence.is_empty(),
            "symbolic contract requirement has no resolved evidence"
        );
        require!(
            (requirement.actual.0 as usize) < p.types.entries.len(),
            "symbolic contract argument is missing"
        );
        for evidence in &requirement.evidence {
            require!(
                (evidence.provided.0 as usize) < p.contracts.types.len(),
                "provided contract is missing"
            );
            for method in &evidence.methods {
                require!(
                    (method.signature.0 as usize) < p.declarations.signatures.len(),
                    "contract method signature is missing"
                );
                if let Some(alternative) =
                    p.contracts.alternatives.get(method.alternative.0 as usize)
                {
                    require!(
                        (method.requirement_index as usize)
                            < 1 + alternative.requirements.rest.len(),
                        "contract method requirement is missing"
                    );
                } else {
                    require!(false, "contract alternative is missing");
                }
            }
        }
    }
    for instance in &p.declarations.instances {
        require!(
            (instance.configuration.0 as usize) < p.contracts.environments.len(),
            "function configuration is missing"
        );
        require!(
            (instance.signature.0 as usize) < p.declarations.signatures.len(),
            "function signature is missing"
        );
    }
    for requirement in &p.obligations.execution_context {
        require!(
            operations.contains_key(&requirement.operation),
            "context requirement operation is missing"
        );
        require!(
            (requirement.function.0 as usize) < p.declarations.instances.len(),
            "context requirement function is missing"
        );
        // Deliberately no comparison of actual/required here: that belongs to N8.
    }
    let mut dependencies = vec![];
    for summary in &p.values.dependency_summaries {
        dependencies.extend(summary.dependencies.iter());
        for guarded in summary.guarded.iter().chain(&summary.deferred_result) {
            require!(
                (guarded.guard.0 as usize) < p.execution.predicates.len(),
                "dependency condition is missing"
            );
            dependencies.push(&guarded.requirement);
        }
    }
    while let Some(requirement) = dependencies.pop() {
        let values: Vec<ValueId> = match requirement {
            DependencyRequirement::CarriedByParameter { binding } => {
                require!(
                    p.scopes
                        .bindings
                        .get(binding.0 as usize)
                        .is_some_and(|b| matches!(
                            b.introduced,
                            BindingIntroduction::Parameter { .. }
                        )),
                    "dependency formal parameter is missing"
                );
                vec![]
            }
            DependencyRequirement::When { guard, requirement } => {
                require!(
                    (guard.0 as usize) < p.execution.predicates.len(),
                    "nested dependency condition is missing"
                );
                dependencies.push(requirement);
                vec![]
            }
            DependencyRequirement::CarriedByPlace { place, at } => {
                require!(
                    (place.0 as usize) < p.objects.evaluated_places.len(),
                    "dependency read place is missing"
                );
                require!(
                    (at.0 as usize) < p.execution.execution_moments.len(),
                    "dependency read moment is missing"
                );
                vec![]
            }
            DependencyRequirement::LiveTarget(place) => {
                require!(
                    (place.0 as usize) < p.objects.places.len(),
                    "dependency target place is missing"
                );
                vec![]
            }
            DependencyRequirement::LiveReference(reference) => {
                require!(
                    (reference.0 as usize) < p.objects.references.len(),
                    "dependency reference is missing"
                );
                vec![]
            }
            DependencyRequirement::LiveStorage(storage) => {
                require!(
                    (storage.0 as usize) < p.storage_origins.len(),
                    "dependency storage is missing"
                );
                vec![]
            }
            DependencyRequirement::ActiveLock(lock) | DependencyRequirement::HoldsLock(lock) => {
                require!(
                    (lock.0 as usize) < p.contracts.lock_identities.len(),
                    "dependency lock identity is missing"
                );
                vec![]
            }
            DependencyRequirement::BranchCompletion(capability) => {
                require!(
                    (capability.0 as usize) < p.contracts.completions.len(),
                    "dependency completion capability is missing"
                );
                vec![]
            }
            DependencyRequirement::ConfinedToUncheckedScope(scope) => {
                require!(
                    (scope.0 as usize) < p.scopes.entries.len(),
                    "dependency boundary scope is missing"
                );
                vec![]
            }
            DependencyRequirement::CapturedField { record, field } => {
                require!(
                    (record.0 as usize) < p.contracts.captures.len(),
                    "dependency capture record is missing"
                );
                require!(
                    (field.0 as usize) < p.declarations.fields.len(),
                    "dependency capture field is missing"
                );
                vec![]
            }
            DependencyRequirement::InstantiatedResult {
                function,
                arguments,
            } => {
                require!(
                    (function.0 as usize) < p.declarations.instances.len(),
                    "dependency function instance is missing"
                );
                arguments.clone()
            }
            DependencyRequirement::FutureResult { function, future } => {
                require!(
                    (function.0 as usize) < p.declarations.instances.len(),
                    "dependency future function is missing"
                );
                vec![*future]
            }
            DependencyRequirement::ContractFutureResult { future, .. } => vec![*future],
            DependencyRequirement::ContractResult { arguments, .. } => arguments.clone(),
            DependencyRequirement::CallableResult {
                callable,
                arguments,
            } => std::iter::once(*callable)
                .chain(arguments.iter().copied())
                .collect(),
            DependencyRequirement::CarriedByProjection { source, .. } => vec![*source],
            DependencyRequirement::NativeResult {
                operation, source, ..
            } => {
                require!(
                    operations.contains_key(operation),
                    "native dependency operation is missing"
                );
                vec![*source]
            }
        };
        for value in values {
            require!(
                (value.0 as usize) < p.values.entries.len(),
                "dependency source value is missing"
            );
        }
    }
    if failures.is_empty() {
        Ok(())
    } else {
        Err(failures)
    }
}

// Validate retained links only. Eligibility remains a later rule obligation.
fn validate_replication(
    p: &PostAst,
    plan: &StructuralReplicationPlan,
    failures: &mut Vec<IntegrityError>,
) {
    if p.types.entries.get(plan.ty.0 as usize).is_none() {
        failures.push(IntegrityError("replication type is missing".into()));
    }
    match &plan.strategy {
        StructuralReplicationStrategy::Struct(fields) => {
            for component in fields {
                if !p
                    .declarations
                    .fields
                    .get(component.field.0 as usize)
                    .is_some_and(|field| field.ty == component.plan.ty)
                {
                    failures.push(IntegrityError(
                        "replication field/type link is inconsistent".into(),
                    ));
                }
                validate_replication(p, &component.plan, failures);
            }
        }
        StructuralReplicationStrategy::Ineligible(
            StructuralReplicationRestriction::CustomDestructor(function),
        ) => {
            if p.declarations.functions.get(function.0 as usize).is_none() {
                failures.push(IntegrityError(
                    "replication destructor declaration is missing".into(),
                ));
            }
        }
        _ => {}
    }
}
