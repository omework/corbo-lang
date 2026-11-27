//! N1–N8 checking of a resolved logical PostAST. No source-name lookup, inference,
//! legacy verifier or backend is used. Missing producer facts never count as proof.
mod checks;
mod cleanup;
mod concurrency;
mod effects;
mod facts;
mod flow;
mod guards;
mod ledger;
mod locks;
mod safety;
use crate::post_ast::*;
use facts::{Facts, Root};
use flow::{Flow, State};
use guards::Guard;
use ledger::ObligationLedger;
use std::collections::{HashMap, HashSet};

/// Consume the semantic handoff. Only Established can enter physical planning.
pub fn verify(semantics: LogicalDestinationResult) -> RuleAnalysisResult {
    if let Err(errors) = crate::post_ast::integrity::validate_population(&semantics) {
        let p = &semantics.semantics.post_ast;
        let origin = p
            .origins
            .origins
            .first()
            .map(|o| o.id)
            .unwrap_or(SourceOriginId(0));
        let missing = errors
            .into_iter()
            .map(|e| SemanticGap {
                consumer: CoreRule::N1,
                operation: OperationId(0),
                missing: MissingFact::MalformedGraph(e.0),
                origin,
            })
            .collect::<Vec<_>>();
        return RuleAnalysisResult::MissingSemanticInput(IncompleteSemanticProgram {
            semantics,
            derived: ValidationResult {
                condition_nodes: vec![],
                cleanup: vec![],
                proofs: vec![],
                binding_states: vec![],
                ownership_states: vec![],
                checks: vec![],
            },
            evidence: vec![],
            missing: NonEmpty {
                first: missing[0].clone(),
                rest: missing[1..].to_vec(),
            },
        });
    }
    let (derived, evidence, diagnostics, gaps) = {
        let p = &semantics.semantics.post_ast;
        trace("building guarded execution flow");
        let flow = Flow::new(p);
        trace("guarded execution flow complete");
        let facts = Facts::new(p, &flow);
        let mut explicit_destructions: HashMap<(BodyId, EntityId), Vec<OperationSite>> =
            HashMap::new();
        for operation in p.bodies.iter().flat_map(|body| &body.operations) {
            let (value, site) = match operation {
                Operation::DropValue(drop) => (drop.value, &drop.site),
                Operation::DiscardResult(discard) => (discard.value, &discard.site),
                _ => continue,
            };
            let mut seen = HashSet::new();
            for identity in facts.identities_by_value.get(&value).into_iter().flatten() {
                if seen.insert(identity.entity.clone()) {
                    explicit_destructions
                        .entry((site.body, identity.entity.clone()))
                        .or_default()
                        .push(site.clone());
                }
            }
        }
        let mut checker = Checker {
            input: &semantics,
            p,
            flow: &flow,
            facts,
            explicit_destructions,
            derived: ValidationResult {
                condition_nodes: vec![],
                cleanup: vec![],
                proofs: vec![],
                binding_states: vec![],
                ownership_states: vec![],
                checks: vec![],
            },
            evidence: vec![],
            diagnostics: vec![],
            gaps: vec![],
            ledger: ObligationLedger::new(p),
        };
        checker.check();
        checker.close_obligation_ledger();
        trace("rule consumers complete");
        // Rejected artifacts do not carry derived proofs into physical planning;
        // exporting their temporary decision arena only duplicates unused data.
        if checker.diagnostics.is_empty() && checker.gaps.is_empty() {
            checker.derived.condition_nodes = flow
                .predicates
                .iter()
                .find(|g| g.graph().len() > 2)
                .map(Guard::graph)
                .unwrap_or_else(|| Guard::yes().graph());
        }
        (
            checker.derived,
            checker.evidence,
            checker.diagnostics,
            checker.gaps,
        )
    };
    if !gaps.is_empty() {
        return RuleAnalysisResult::MissingSemanticInput(IncompleteSemanticProgram {
            semantics,
            derived,
            evidence,
            missing: NonEmpty {
                first: gaps[0].clone(),
                rest: gaps[1..].to_vec(),
            },
        });
    }
    if !diagnostics.is_empty() {
        return RuleAnalysisResult::Rejected(RejectedSemanticProgram {
            semantics,
            derived,
            evidence,
            diagnostics: NonEmpty {
                first: diagnostics[0].clone(),
                rest: diagnostics[1..].to_vec(),
            },
        });
    }
    RuleAnalysisResult::Established(CheckedPostAst {
        semantics,
        derived,
        evidence,
    })
}
struct Checker<'a> {
    input: &'a LogicalDestinationResult,
    p: &'a PostAst,
    flow: &'a Flow,
    facts: Facts<'a>,
    explicit_destructions: HashMap<(BodyId, EntityId), Vec<OperationSite>>,
    derived: ValidationResult,
    evidence: Vec<RuleEvidence>,
    diagnostics: Vec<RuleDiagnostic>,
    gaps: Vec<SemanticGap>,
    ledger: ObligationLedger,
}
impl Checker<'_> {
    fn reject_access_obligations_at(
        &mut self,
        site: &OperationSite,
        message: impl Into<String>,
        related: Vec<SourceOriginId>,
    ) {
        let obligations = self
            .p
            .obligations
            .n5
            .iter()
            .filter(|obligation| obligation.site.operation == site.id)
            .map(|obligation| obligation.site.id)
            .collect::<Vec<_>>();
        if obligations.is_empty() {
            self.gaps.push(SemanticGap {
                consumer: CoreRule::N5,
                operation: site.id,
                missing: MissingFact::AccessObligation(site.id),
                origin: site.origin,
            });
            return;
        }
        let message = message.into();
        for obligation in obligations {
            if self.ledger.is_accounted(obligation) {
                continue;
            }
            self.reject_obligation(
                obligation,
                CoreRule::N5,
                site,
                message.clone(),
                related.clone(),
            );
        }
    }
    fn reject_destruction_obligations_at(
        &mut self,
        site: &OperationSite,
        message: impl Into<String>,
    ) {
        let obligations = self
            .p
            .obligations
            .n7
            .iter()
            .filter(|obligation| obligation.site.moment == site.execution_moments.first)
            .map(|obligation| obligation.site.id)
            .collect::<Vec<_>>();
        if obligations.is_empty() {
            self.gaps.push(SemanticGap {
                consumer: CoreRule::N7,
                operation: site.id,
                missing: MissingFact::ExecutionOrder(NonEmpty {
                    first: site.execution_moments.first,
                    rest: vec![],
                }),
                origin: site.origin,
            });
            return;
        }
        let message = message.into();
        for obligation in obligations {
            if self.ledger.is_accounted(obligation) {
                continue;
            }
            self.reject_obligation(obligation, CoreRule::N7, site, message.clone(), vec![]);
        }
    }
    fn reject_obligation(
        &mut self,
        obligation: ObligationId,
        rule: CoreRule,
        site: &OperationSite,
        message: impl Into<String>,
        related: Vec<SourceOriginId>,
    ) {
        if !self.ledger.account(obligation) {
            return;
        }
        self.diagnostics.push(RuleDiagnostic {
            message: message.into(),
            established_violation: true,
            rule,
            obligation,
            primary: site.origin,
            related,
        });
    }
    fn unproved_obligation(
        &mut self,
        obligation: ObligationId,
        rule: CoreRule,
        site: &OperationSite,
        message: impl Into<String>,
    ) {
        if !self.ledger.account(obligation) {
            return;
        }
        self.diagnostics.push(RuleDiagnostic {
            message: message.into(),
            established_violation: false,
            rule,
            obligation,
            primary: site.origin,
            related: vec![],
        });
    }
    fn prove_obligation(&mut self, obligation: ObligationId, facts: EvidenceFacts) {
        if !self.ledger.account(obligation) {
            return;
        }
        let id = EvidenceId(self.evidence.len() as u32);
        self.derived.proofs.push(Proof {
            id: ProofId(self.derived.proofs.len() as u32),
            obligation,
            premises: vec![],
        });
        self.evidence.push(RuleEvidence {
            id,
            obligation,
            premises: vec![],
            facts,
        });
    }
    fn close_obligation_ledger(&mut self) {
        for obligation in self.ledger.unresolved() {
            self.diagnostics.push(RuleDiagnostic {
                message: "the applicable rule obligation has no positive proof".into(),
                established_violation: false,
                rule: obligation.rule,
                obligation: obligation.id,
                primary: obligation.origin,
                related: vec![],
            });
        }
    }
    fn site_at(&self, m: ExecutionMomentId) -> OperationSite {
        let mut site = self.facts.operations
            [&self.p.execution.execution_moments[m.0 as usize].operation]
            .site()
            .clone();
        site.execution_moments = NonEmpty {
            first: m,
            rest: vec![],
        };
        site
    }
    fn guard(&self, s: &OperationSite) -> Guard {
        self.flow
            .reachable
            .get(&s.execution_moments.first)
            .cloned()
            .unwrap_or_default()
            .and(&self.flow.predicate(s.guard))
    }
    fn check(&mut self) {
        // Type identities have already been resolved. Verification compares IDs,
        // never names, overload sets or source spelling.
        for o in &self.p.obligations.n1 {
            if let InitializationAndTypeRequirement::TypeIdentity {
                value: _,
                expected,
                actual,
            } = o.requirement
            {
                if actual != expected {
                    let site = self.site_at(o.site.moment);
                    self.reject_obligation(
                        o.site.id,
                        CoreRule::N1,
                        &site,
                        "resolved operand type differs from the required type",
                        vec![],
                    );
                } else {
                    self.prove_obligation(
                        o.site.id,
                        EvidenceFacts::TypeIdentity { expected, actual },
                    );
                }
            }
        }
        self.check_transfer_obligations();
        self.check_path_obligations();
        trace("borrow_checks");
        self.borrow_checks();
        self.settle_lifetime_obligations();
        trace("ownership_checks");
        self.ownership_checks();
        self.settle_ownership_obligations();
        trace("cleanup_checks");
        self.cleanup_checks();
        self.settle_destruction_obligations();
        self.settle_boundary_obligations();
        trace("concurrency_checks");
        self.concurrency_checks();
        trace("synchronization_checks");
        self.synchronization_checks();
        trace("lock_interval_checks");
        self.lock_interval_checks();
        self.settle_access_obligations();
        trace("check_runtime_requirements");
        self.check_runtime_requirements();
    }
    fn settle_lifetime_obligations(&mut self) {
        for obligation in self.p.obligations.n4.clone() {
            if self.ledger.is_accounted(obligation.site.id) {
                continue;
            }
            let site = self.site_at(obligation.site.moment);
            match obligation.requirement {
                LifetimeProofRequirement::DependencyLink {
                    link: link_id,
                    lifetime,
                } => {
                    let Some(link) = self.p.objects.dependencies.get(link_id.0 as usize) else {
                        self.unproved_obligation(
                            obligation.site.id,
                            CoreRule::N4,
                            &site,
                            "the exact dependency link is missing from PostAST",
                        );
                        continue;
                    };
                    if link.id != link_id || link.established != obligation.site.moment {
                        self.reject_obligation(
                            obligation.site.id,
                            CoreRule::N4,
                            &site,
                            "the lifetime obligation does not identify its resolved dependency exactly",
                            vec![],
                        );
                        continue;
                    }
                    match lifetime {
                        Some(id) => {
                            let requirement = self
                                .input
                                .semantics
                                .lifetimes
                                .requirements
                                .get(id.0 as usize)
                                .filter(|requirement| requirement.id == id)
                                .cloned();
                            if let Some(requirement) = requirement {
                                if self.lifetime_requirement_holds(&requirement) {
                                    self.prove_obligation(
                                        obligation.site.id,
                                        EvidenceFacts::LiveTarget {
                                            requirement: requirement.id,
                                            uses: requirement.uses,
                                        },
                                    );
                                } else {
                                    self.reject_obligation(
                                        obligation.site.id,
                                        CoreRule::N4,
                                        &site,
                                        "the required target does not remain live for every resolved use",
                                        vec![requirement.origin],
                                    );
                                }
                            } else {
                                self.unproved_obligation(
                                    obligation.site.id,
                                    CoreRule::N4,
                                    &site,
                                    "the exact lifetime requirement is missing from PostAST",
                                );
                            }
                        }
                        None => self.prove_obligation(
                            obligation.site.id,
                            EvidenceFacts::DependencyPreserved { link: link_id },
                        ),
                    }
                }
                LifetimeProofRequirement::StoredValue { target, value } => {
                    let place = self.p.objects.evaluated_places[target.0 as usize].definition;
                    let destinations =
                        self.facts
                            .place(place, obligation.site.moment, &HashMap::new());
                    if self.stored_dependencies_hold(&destinations, value, &HashMap::new(), &site) {
                        self.prove_obligation(
                            obligation.site.id,
                            EvidenceFacts::StoredDependencies {
                                value,
                                destination: place,
                            },
                        );
                    } else {
                        self.reject_obligation(
                            obligation.site.id,
                            CoreRule::N4,
                            &site,
                            "stored value has a dependency that does not survive the receiving place",
                            vec![],
                        );
                    }
                }
                LifetimeProofRequirement::EscapingValue { value } => {
                    if self.escaping_dependencies_hold(value, &site) {
                        self.prove_obligation(
                            obligation.site.id,
                            EvidenceFacts::EscapingDependencies { value },
                        );
                    } else {
                        self.reject_obligation(
                            obligation.site.id,
                            CoreRule::N4,
                            &site,
                            "returned value has a dependency on local or confined storage",
                            vec![],
                        );
                    }
                }
                LifetimeProofRequirement::TransferDestination { transfer } => {
                    if self.transfer_destination_holds(transfer) {
                        self.prove_obligation(
                            obligation.site.id,
                            EvidenceFacts::TransferDestination { transfer },
                        );
                    } else {
                        self.reject_obligation(
                            obligation.site.id,
                            CoreRule::N4,
                            &site,
                            "transfer reaches a destination that outlives one of its dependencies",
                            vec![],
                        );
                    }
                }
                LifetimeProofRequirement::FinalDestination { destination } => {
                    if self.final_destination_holds(destination) {
                        self.prove_obligation(
                            obligation.site.id,
                            EvidenceFacts::FinalDestination { destination },
                        );
                    } else {
                        self.reject_obligation(
                            obligation.site.id,
                            CoreRule::N4,
                            &site,
                            "final destination outlives referenced or confined storage",
                            vec![],
                        );
                    }
                }
                LifetimeProofRequirement::OperationDependencies {
                    operation,
                    value,
                    source,
                } => {
                    let exact = operation == obligation.site.operation
                        && self.facts.operations.contains_key(&operation);
                    if exact && self.operation_dependencies_live(value, source, &site) {
                        self.prove_obligation(
                            obligation.site.id,
                            EvidenceFacts::DependenciesLiveAtOperation { operation },
                        );
                    } else {
                        self.reject_obligation(
                            obligation.site.id,
                            CoreRule::N4,
                            &site,
                            "operation uses a dependency whose explicit destruction already ended its lifetime",
                            vec![],
                        );
                    }
                }
                LifetimeProofRequirement::BranchDependencies {
                    call,
                    task,
                    capability,
                } => {
                    if call == obligation.site.operation
                        && self.branch_dependencies_hold(call, task, capability)
                    {
                        self.prove_obligation(
                            obligation.site.id,
                            EvidenceFacts::BranchDependencies { call, capability },
                        );
                    } else {
                        self.reject_obligation(
                            obligation.site.id,
                            CoreRule::N4,
                            &site,
                            "execution branch may outlive one of its borrowed dependencies",
                            vec![],
                        );
                    }
                }
            }
        }
    }
    fn lifetime_requirement_holds(&self, requirement: &LifetimeRequirement) -> bool {
        std::iter::once(&requirement.uses.first)
            .chain(&requirement.uses.rest)
            .all(|usage| {
                let use_site = self.site_at(usage.moment);
                let use_guard = self.flow.predicate(usage.guard);
                match &requirement.required {
                    LifetimeSubject::Target(place) => {
                        if !use_guard.possible() {
                            return true;
                        }
                        let targets = self
                            .facts
                            .place(place.place, usage.moment, &HashMap::new())
                            .into_iter()
                            .filter(|target| use_guard.and(&target.guard).possible())
                            .collect::<Vec<_>>();
                        !targets.is_empty()
                            && targets.iter().all(|target| {
                                self.target_survives_use(&target.root, use_site.scope)
                            })
                    }
                    LifetimeSubject::Reference {
                        reference,
                        instance: _,
                    } => {
                        if !use_guard.possible() {
                            return true;
                        }
                        let targets = self
                            .facts
                            .reference(*reference, usage.moment, &HashMap::new())
                            .into_iter()
                            .filter(|target| use_guard.and(&target.guard).possible())
                            .collect::<Vec<_>>();
                        !targets.is_empty()
                            && targets.iter().all(|target| {
                                self.target_survives_use(&target.root, use_site.scope)
                            })
                    }
                    LifetimeSubject::SourceStorage {
                        origin,
                        instance: _,
                    } => match self.p.storage_origins[origin.0 as usize].creation {
                        StorageCreation::Static(_) | StorageCreation::CallerResult(_) => true,
                        StorageCreation::Operation(operation) => self
                            .facts
                            .operations
                            .get(&operation)
                            .is_some_and(|created| {
                                self.ancestor(created.site().scope, use_site.scope)
                            }),
                    },
                    LifetimeSubject::UncheckedBoundary(boundary) => {
                        self.ancestor(*boundary, use_site.scope)
                    }
                    LifetimeSubject::GuardedLock(_) => true,
                }
            })
    }
    fn target_survives_use(&self, root: &facts::Root, use_scope: ScopeId) -> bool {
        self.target_scope(root)
            .is_none_or(|target| self.ancestor(target, use_scope) || self.target_escapes(root))
    }
    fn settle_access_obligations(&mut self) {
        for obligation in self.p.obligations.n5.clone() {
            if self.ledger.is_accounted(obligation.site.id) {
                continue;
            }
            match obligation.requirement {
                AccessCompatibilityRequirement::PlaceAccess { place, access, .. } => {
                    self.prove_obligation(
                        obligation.site.id,
                        EvidenceFacts::AccessCompatible {
                            place: PlaceOccurrence {
                                place,
                                instance: self.p.execution.execution_moments
                                    [obligation.site.moment.0 as usize]
                                    .instance,
                            },
                            access,
                            at: MomentOccurrence {
                                moment: obligation.site.moment,
                                context: self.p.execution.execution_moments
                                    [obligation.site.moment.0 as usize]
                                    .instance,
                            },
                            guard: obligation.site.guard,
                        },
                    );
                }
                AccessCompatibilityRequirement::LockAcquisition { call, contract } => {
                    self.prove_obligation(
                        obligation.site.id,
                        EvidenceFacts::LockAcquisition { call, contract },
                    );
                }
            }
        }
    }
    fn settle_boundary_obligations(&mut self) {
        for obligation in self.p.obligations.n8.clone() {
            if self.ledger.is_accounted(obligation.site.id) {
                continue;
            }
            let site = self.site_at(obligation.site.moment);
            match obligation.requirement {
                BoundaryContractRequirement::CallContract { call, effects } => {
                    let matching = self.facts.operations.get(&call).is_some_and(|operation| {
                        let concrete_arguments_match =
                            |function: FunctionInstanceId, arguments: &[CallArgument]| {
                                let instance = &self.p.declarations.instances[function.0 as usize];
                                let signature =
                                    &self.p.declarations.signatures[instance.signature.0 as usize];
                                arguments.iter().all(|argument| {
                                    signature
                                        .parameters
                                        .get(argument.parameter_index as usize)
                                        .is_some()
                                })
                            };
                        match operation {
                            Operation::AwaitValue(awaited) => awaited.effects == effects,
                            Operation::DirectCall(operation) => {
                                operation.effects == effects
                                    && concrete_arguments_match(
                                        operation.target,
                                        &operation.arguments,
                                    )
                            }
                            Operation::MethodCall(operation) => {
                                operation.effects == effects
                                    && match operation.target.target {
                                        MethodTarget::Concrete(function) => {
                                            concrete_arguments_match(function, &operation.arguments)
                                        }
                                        _ => true,
                                    }
                            }
                            Operation::ExternalCall(operation) => {
                                operation.effects == effects
                                    && concrete_arguments_match(
                                        operation.target.function,
                                        &operation.arguments,
                                    )
                            }
                            Operation::IntrinsicCall(operation) => operation.effects == effects,
                            Operation::CallableCall(operation) => operation.effects == effects,
                            Operation::NativeOperation(operation) => operation.effects == effects,
                            Operation::CompleteBranch(operation) => operation.effects == effects,
                            Operation::ForeignC(operation) => matches!(
                                operation.effects,
                                ForeignBoundaryEffects::Declared(found) if found == effects
                            ),
                            Operation::ForeignCpp(operation) => matches!(
                                operation.effects,
                                ForeignBoundaryEffects::Declared(found) if found == effects
                            ),
                            Operation::ForeignAssembly(operation) => matches!(
                                operation.effects,
                                ForeignBoundaryEffects::Declared(found) if found == effects
                            ),
                            _ => false,
                        }
                    });
                    if matching {
                        self.prove_obligation(
                            obligation.site.id,
                            EvidenceFacts::CallContract { call, effects },
                        );
                    } else {
                        self.unproved_obligation(
                            obligation.site.id,
                            CoreRule::N8,
                            &site,
                            "the boundary operation does not retain its resolved call contract",
                        );
                    }
                }
                BoundaryContractRequirement::ExecutionContext {
                    operation,
                    function,
                    actual,
                    required,
                } => {
                    if std::mem::discriminant(&actual) == std::mem::discriminant(&required) {
                        self.prove_obligation(
                            obligation.site.id,
                            EvidenceFacts::ExecutionContext {
                                operation,
                                function,
                                actual,
                                required,
                            },
                        );
                    } else {
                        self.reject_obligation(
                            obligation.site.id,
                            CoreRule::N8,
                            &site,
                            "operation is not permitted in this synchronous/async execution context",
                            vec![],
                        );
                    }
                }
                BoundaryContractRequirement::ThreadTransfer { call, task, ty } => {
                    let mut seen = HashSet::new();
                    if self.forbidden_transfer(ty, &mut seen) {
                        self.reject_obligation(
                            obligation.site.id,
                            CoreRule::N8,
                            &site,
                            "task owns a value whose thread-transfer contract forbids transfer",
                            vec![],
                        );
                    } else {
                        let effects_known =
                            if self.future_creation(task, &mut HashSet::new()).is_some() {
                                true
                            } else {
                                match self.p.types.entries[ty.0 as usize].kind {
                                    TypeDefinition::Closure { captures, .. } => {
                                        self.p.contracts.captures[captures.0 as usize]
                                            .call
                                            .and_then(|function| {
                                                self.p.declarations.instances[function.0 as usize]
                                                    .body
                                            })
                                            .is_some()
                                    }
                                    _ => self
                                        .facts
                                        .dependencies(task, obligation.site.moment, &HashMap::new())
                                        .is_empty(),
                                }
                            };
                        if !effects_known {
                            self.unproved_obligation(
                                obligation.site.id,
                                CoreRule::N8,
                                &site,
                                "cannot establish shared-access effects of this abstract task",
                            );
                            continue;
                        }
                        self.prove_obligation(
                            obligation.site.id,
                            EvidenceFacts::ThreadTransfer { call, task, ty },
                        );
                    }
                }
            }
        }
    }
    fn settle_ownership_obligations(&mut self) {
        for obligation in self.p.obligations.n2.clone() {
            if self.ledger.is_accounted(obligation.site.id) {
                continue;
            }
            let site = self.site_at(obligation.site.moment);
            let Some(link) = self.p.objects.ownership.get(obligation.link.0 as usize) else {
                self.unproved_obligation(
                    obligation.site.id,
                    CoreRule::N2,
                    &site,
                    "semantic resolution supplied no ownership transition for this obligation",
                );
                continue;
            };
            if link.entity != obligation.entity {
                self.unproved_obligation(
                    obligation.site.id,
                    CoreRule::N2,
                    &site,
                    "the N2 obligation does not reference its declared ownership transition",
                );
                continue;
            }
            let link_instance =
                self.p.execution.execution_moments[link.established.0 as usize].instance;
            let overlapping_unordered = self
                .facts
                .ownership_by_entity
                .get(&link.entity)
                .into_iter()
                .flatten()
                .any(|other| {
                    let other_instance =
                        self.p.execution.execution_moments[other.established.0 as usize].instance;
                    !std::ptr::eq(*other, link)
                        && other_instance == link_instance
                        && self
                            .flow
                            .predicate(other.guard)
                            .and(&self.flow.predicate(link.guard))
                            .possible()
                        && !self.flow.path_in_occurrence(
                            link.established,
                            other.established,
                            link.established,
                            &self.flow.predicate(other.guard),
                        )
                        && !self.flow.path_in_occurrence(
                            other.established,
                            link.established,
                            other.established,
                            &self.flow.predicate(link.guard),
                        )
                });
            if overlapping_unordered && std::env::var_os("CORBO_RULE_TRACE").is_some() {
                eprintln!(
                    "N2 unordered link={:?} entity={:?} owner={:?} at={:?} guard={:?}",
                    obligation.link, link.entity, link.owner, link.established, link.guard
                );
                for other in self
                    .facts
                    .ownership_by_entity
                    .get(&link.entity)
                    .into_iter()
                    .flatten()
                {
                    eprintln!(
                        "  candidate owner={:?} at={:?} guard={:?}",
                        other.owner, other.established, other.guard
                    );
                }
            }
            let cyclic = if let Owner::Entity(parent) = &link.owner {
                let mut visiting = HashSet::new();
                let mut stack = vec![parent.entity.clone()];
                let mut cyclic = false;
                while let Some(entity) = stack.pop() {
                    if entity == link.entity {
                        cyclic = true;
                        break;
                    }
                    if !visiting.insert(entity.clone()) {
                        continue;
                    }
                    for old in self
                        .facts
                        .ownership_by_entity
                        .get(&entity)
                        .into_iter()
                        .flatten()
                    {
                        if self
                            .flow
                            .predicate(old.guard)
                            .and(&self.flow.predicate(link.guard))
                            .possible()
                        {
                            if let Owner::Entity(parent) = &old.owner {
                                stack.push(parent.entity.clone());
                            }
                        }
                    }
                }
                cyclic
            } else {
                false
            };
            if overlapping_unordered || cyclic {
                self.reject_obligation(
                    obligation.site.id,
                    CoreRule::N2,
                    &site,
                    if cyclic {
                        "owning an ancestor would form a cleanup cycle"
                    } else {
                        "the entity has unordered overlapping cleanup owners"
                    },
                    vec![],
                );
            } else {
                self.prove_obligation(
                    obligation.site.id,
                    EvidenceFacts::Ownership {
                        entity: EntityOccurrence {
                            entity: obligation.entity,
                            instance: self.p.execution.execution_moments
                                [obligation.site.moment.0 as usize]
                                .instance,
                        },
                        at: MomentOccurrence {
                            moment: obligation.site.moment,
                            context: self.p.execution.execution_moments
                                [obligation.site.moment.0 as usize]
                                .instance,
                        },
                        owner: link.owner.clone(),
                    },
                );
            }
        }
    }
    fn settle_destruction_obligations(&mut self) {
        for obligation in self.p.obligations.n7.clone() {
            if self.ledger.is_accounted(obligation.site.id) {
                continue;
            }
            let site = self.site_at(obligation.site.moment);
            let (represented, evidence) = match obligation.requirement {
                DestructionRequirement::ExplicitDrop {
                    value,
                    destructor,
                    subject,
                    storage,
                } => {
                    let represented = self
                        .facts
                        .operations
                        .get(&obligation.site.operation)
                        .is_some_and(|operation| match (&subject, operation) {
                            (DestructionSubject::Value(expected), Operation::DropValue(drop)) => {
                                drop.value == *expected
                                    && drop.value == value
                                    && drop.destructor == destructor
                                    && self.p.contracts.destructors[destructor.0 as usize].ty
                                        == self.p.values.entries[value.0 as usize].ty
                            }
                            (DestructionSubject::Entity(entity), Operation::DropValue(drop)) => {
                                drop.value == value
                                    && drop.destructor == destructor
                                    && self.p.contracts.destructors[destructor.0 as usize].ty
                                        == self.p.values.entries[value.0 as usize].ty
                                    && self
                                        .facts
                                        .identities_by_value
                                        .get(&drop.value)
                                        .into_iter()
                                        .flatten()
                                        .any(|identity| identity.entity == *entity)
                            }
                            _ => false,
                        });
                    (
                        represented,
                        EvidenceFacts::DestructionSequence {
                            subject,
                            at: MomentOccurrence {
                                moment: obligation.site.moment,
                                context: self.p.execution.execution_moments
                                    [obligation.site.moment.0 as usize]
                                    .instance,
                            },
                            storage,
                        },
                    )
                }
                DestructionRequirement::CleanupCandidate {
                    candidate: candidate_id,
                    subject,
                    storage,
                } => {
                    let Some(candidate) = self
                        .input
                        .semantics
                        .lifetimes
                        .cleanup_candidates
                        .get(candidate_id.0 as usize)
                    else {
                        self.unproved_obligation(
                            obligation.site.id,
                            CoreRule::N7,
                            &site,
                            "the N7 obligation references no resolved cleanup candidate",
                        );
                        continue;
                    };
                    let DestructionSubject::Entity(entity) = &subject else {
                        self.unproved_obligation(
                            obligation.site.id,
                            CoreRule::N7,
                            &site,
                            "a scope-exit cleanup candidate has no resolved entity",
                        );
                        continue;
                    };
                    if candidate.entity.entity != *entity {
                        self.unproved_obligation(
                            obligation.site.id,
                            CoreRule::N7,
                            &site,
                            "the N7 obligation does not reference its declared cleanup candidate",
                        );
                        continue;
                    }
                    let exit = &self.p.scopes.exits[candidate.exit.0 as usize];
                    let mut remaining = self.flow.predicate(candidate.guard);
                    for operation in self.p.bodies.iter().flat_map(|body| &body.operations) {
                        let Operation::DropValue(drop) = operation else {
                            continue;
                        };
                        let drops_entity = self
                            .facts
                            .identities_by_value
                            .get(&drop.value)
                            .into_iter()
                            .flatten()
                            .any(|identity| identity.entity == *entity);
                        if drops_entity
                            && self.flow.path(
                                drop.site.execution_moments.first,
                                exit.event,
                                &self.guard(&drop.site),
                            )
                        {
                            remaining = remaining.and(&self.guard(&drop.site).not());
                        }
                    }
                    let represented = !remaining.possible()
                        || self.derived.cleanup.iter().any(|cleanup| {
                            cleanup.exit == candidate.exit
                                && cleanup.steps.iter().any(|step| {
                                    matches!(step, VerifiedDestructionStep::EndLifetime { entity: ended, candidates, .. } if ended == entity && candidates.contains(&candidate_id))
                                })
                        });
                    (
                        represented,
                        EvidenceFacts::DestructionSequence {
                            subject,
                            at: MomentOccurrence {
                                moment: obligation.site.moment,
                                context: self.p.execution.execution_moments
                                    [obligation.site.moment.0 as usize]
                                    .instance,
                            },
                            storage,
                        },
                    )
                }
                DestructionRequirement::DestructorContract { destructor } => {
                    let definition = &self.p.contracts.destructors[destructor.0 as usize];
                    let hook = &self.p.declarations.instances[definition.hook.0 as usize];
                    let signature = &self.p.declarations.signatures[hook.signature.0 as usize];
                    let valid = matches!(signature.execution, FunctionExecution::Synchronous)
                        && matches!(
                            self.p.types.entries[signature.result.0 as usize].kind,
                            TypeDefinition::Unit
                        );
                    (valid, EvidenceFacts::DestructorContract { destructor })
                }
                DestructionRequirement::ReservedDestructorCall { call, destructor } => {
                    self.reject_obligation(
                        obligation.site.id,
                        CoreRule::N7,
                        &site,
                        "destructor methods are reserved; request destruction with drop(value)",
                        vec![],
                    );
                    let _ = (call, destructor);
                    continue;
                }
                DestructionRequirement::PartialMoveCleanup { source, transfer } => {
                    let ty = self.p.values.entries[source.0 as usize].ty;
                    let has_custom_destructor = self
                        .p
                        .contracts
                        .destructors
                        .iter()
                        .filter(|destructor| destructor.ty == ty)
                        .any(|destructor| {
                            let function =
                                &self.p.declarations.functions[self.p.declarations.instances
                                    [destructor.hook.0 as usize]
                                    .definition
                                    .0
                                    as usize];
                            !matches!(
                                function.body,
                                FunctionImplementation::EmptyDestructor { .. }
                                    | FunctionImplementation::ParametricDestructor { .. }
                            )
                        });
                    let valid_transfer = matches!(
                        transfer,
                        TransferKind::Move | TransferKind::ByTypeParameter(_)
                    );
                    (
                        (!self.guard(&site).possible() || !has_custom_destructor) && valid_transfer,
                        EvidenceFacts::PartialMoveCleanup { source },
                    )
                }
            };
            if represented {
                self.prove_obligation(obligation.site.id, evidence);
            } else {
                self.unproved_obligation(
                    obligation.site.id,
                    CoreRule::N7,
                    &site,
                    "no verified destruction step closes this cleanup obligation",
                );
            }
        }
    }
    fn check_transfer_obligations(&mut self) {
        for obligation in self.p.obligations.n3.clone() {
            let site = self.site_at(obligation.site.moment);
            match obligation.requirement {
                TransferAndMutationRequirement::Transfer {
                    occurrence,
                    subject,
                    ty,
                    mode,
                } => {
                    let resolved = self.p.transfers.get(occurrence.0 as usize);
                    let exact = resolved.is_some_and(|resolved| {
                        resolved.id == occurrence
                            && resolved.operation == obligation.site.operation
                            && resolved.moment == obligation.site.moment
                            && resolved.subject == subject
                            && resolved.ty == ty
                            && resolved.mode == mode
                    });
                    let valid_mode = match &mode {
                        TransferKind::PrimitiveCopy => {
                            self.primitive(ty)
                                || matches!(
                                    self.p.types.entries[ty.0 as usize].kind,
                                    TypeDefinition::Reference {
                                        permission: ReferencePermission::Shared,
                                        ..
                                    }
                                )
                        }
                        TransferKind::EligibleEnumCopy => self.copy_enum(ty),
                        TransferKind::ByTypeParameter(expected) => *expected == ty,
                        TransferKind::Move => self.valid_move_source(obligation.site.operation),
                        TransferKind::SharedBorrow | TransferKind::MutableBorrow => true,
                    };
                    if exact && valid_mode {
                        self.prove_obligation(
                            obligation.site.id,
                            EvidenceFacts::TransferMode {
                                occurrence,
                                subject,
                                mode,
                            },
                        );
                    } else {
                        self.reject_obligation(
                            obligation.site.id,
                            CoreRule::N3,
                            &site,
                            "resolved transfer does not satisfy its declared mode and source constraints",
                            vec![],
                        );
                    }
                }
                TransferAndMutationRequirement::MutationPermission { target, access } => {
                    if let Some(message) = self.mutation_permission_error(target, &site) {
                        self.reject_obligation(
                            obligation.site.id,
                            CoreRule::N3,
                            &site,
                            message,
                            vec![],
                        );
                    } else {
                        let place = self.p.objects.evaluated_places[target.0 as usize].definition;
                        self.prove_obligation(
                            obligation.site.id,
                            EvidenceFacts::MutationPermission { place, access },
                        );
                    }
                }
                TransferAndMutationRequirement::StructuralReplication { plan } => {
                    if Self::replicable(&plan) {
                        self.prove_obligation(
                            obligation.site.id,
                            EvidenceFacts::StructuralReplication { ty: plan.ty },
                        );
                    } else {
                        self.reject_obligation(
                            obligation.site.id,
                            CoreRule::N3,
                            &site,
                            "array repetition requires a structurally replicable value without owned resources or a custom destructor",
                            vec![],
                        );
                    }
                }
            }
        }
    }
    fn check_path_obligations(&mut self) {
        for obligation in self.p.obligations.n6.clone() {
            let site = self.site_at(obligation.site.moment);
            match obligation.requirement {
                PathValidityRequirement::BindingAvailable { binding } => {
                    self.binding_use(binding, &site, obligation.site.id);
                }
                PathValidityRequirement::MatchExhaustive {
                    decision,
                    subject: _,
                    unmatched,
                } => {
                    let exact = decision == obligation.site.operation
                        && self.facts.operations.contains_key(&decision);
                    if exact
                        && !self
                            .guard(&site)
                            .and(&self.flow.predicate(unmatched))
                            .possible()
                    {
                        self.prove_obligation(
                            obligation.site.id,
                            EvidenceFacts::MatchExhaustive { decision },
                        );
                    } else {
                        self.reject_obligation(
                            obligation.site.id,
                            CoreRule::N6,
                            &site,
                            "match does not cover every possible variant and payload",
                            vec![],
                        );
                    }
                }
            }
        }
    }
    fn binding_use(&mut self, binding: BindingId, site: &OperationSite, obligation: ObligationId) {
        let guard = self.guard(site);
        let at = site.execution_moments.first;
        let states = self.flow.binding_states(binding, at);
        if states.is_empty() && guard.possible() {
            self.unproved_obligation(
                obligation,
                CoreRule::N6,
                site,
                "no reaching definition is established for this binding",
            );
            return;
        }
        let mut available = Guard::default();
        for (state, g) in &states {
            if !g.and(&guard).possible() {
                continue;
            }
            let state_for_output = match state {
                State::Available(v) => {
                    available = available.or(g);
                    BindingState::Available(*v)
                }
                State::Moved(at) => {
                    let related = vec![self.site_at(*at).origin];
                    self.reject_obligation(
                        obligation,
                        CoreRule::N6,
                        site,
                        "value was moved on a path reaching this use",
                        related,
                    );
                    BindingState::Moved {
                        at: *at,
                        destination: Owner::Scope {
                            scope: site.scope,
                            instance: self.p.execution.execution_moments[at.0 as usize].instance,
                        },
                    }
                }
                State::Destroyed(at) => {
                    self.reject_obligation(
                        obligation,
                        CoreRule::N6,
                        site,
                        "a path reaching this use has already destroyed the value",
                        vec![self.site_at(*at).origin],
                    );
                    BindingState::Destroyed { at: *at }
                }
                State::Uninitialized => {
                    self.reject_obligation(
                        obligation,
                        CoreRule::N6,
                        site,
                        "a path reaching this use has not initialized the value",
                        vec![],
                    );
                    BindingState::Uninitialized
                }
            };
            self.derived.binding_states.push(BindingStateAtMoment {
                condition: g.and(&guard).exported(),
                binding,
                at: MomentOccurrence {
                    moment: at,
                    context: self.p.execution.execution_moments[at.0 as usize].instance,
                },
                guard: site.guard,
                state: state_for_output,
            });
        }
        if !guard.implies(&available) && !states.keys().any(|s| !matches!(s, State::Available(_))) {
            if std::env::var_os("CORBO_RULE_TRACE").is_some() {
                let symbol = self.p.scopes.bindings[binding.0 as usize].symbol;
                eprintln!(
                    "N6 uncovered path binding={binding:?} name={} at={at:?} state_count={} all_states_available={}",
                    self.p.symbols.entries[symbol.0 as usize].spelling,
                    states.len(),
                    states
                        .keys()
                        .all(|state| matches!(state, State::Available(_))),
                );
                eprintln!(
                    "  required={:?} support={:?} available={:?} support={:?}",
                    guard.exported(),
                    guard.support(),
                    available.exported(),
                    available.support(),
                );
                for (state, state_guard) in &states {
                    eprintln!(
                        "  state={state:?} guard={:?} support={:?}",
                        state_guard.exported(),
                        state_guard.support(),
                    );
                }
                let mut atoms = guard.support();
                atoms.extend(available.support());
                for atom in atoms {
                    if let guards::Atom::Boolean(value) = atom {
                        let entry = &self.p.values.entries[value.0 as usize];
                        let operation = match entry.definition {
                            ValueDefinition::OperationResult { operation, .. }
                            | ValueDefinition::ConditionalResult { operation, .. } => {
                                self.facts.operations.get(&operation).copied()
                            }
                            _ => None,
                        };
                        let snippet = operation.and_then(|operation| {
                            let mut origin = operation.site().origin;
                            loop {
                                match &self.p.origins.origins[origin.0 as usize].role {
                                    OriginRole::Written { file, span, .. } => {
                                        let source = &self.p.origins.files[file.0 as usize].source;
                                        break source
                                            .get(span.start as usize..span.end as usize)
                                            .map(str::to_owned);
                                    }
                                    OriginRole::Synthesized { cause, .. } => origin = *cause,
                                    OriginRole::CompilerProvided { .. } => break None,
                                }
                            }
                        });
                        eprintln!(
                            "  predicate value={value:?} source={snippet:?} definition={:?} provenance={:?} operation={operation:?}",
                            entry.definition,
                            self.p.values.provenance[entry.provenance.0 as usize].kind,
                        );
                    }
                }
            }
            self.unproved_obligation(
                obligation,
                CoreRule::N6,
                site,
                "availability is not established on every reaching path",
            );
        } else if !self.ledger.is_accounted(obligation) {
            self.prove_obligation(
                obligation,
                EvidenceFacts::BindingAvailable {
                    binding,
                    at: MomentOccurrence {
                        moment: at,
                        context: self.p.execution.execution_moments[at.0 as usize].instance,
                    },
                    guard: site.guard,
                },
            );
        }
    }
    fn primitive(&self, ty: TypeId) -> bool {
        matches!(
            self.p.types.entries[ty.0 as usize].kind,
            TypeDefinition::Boolean | TypeDefinition::Numeric(_) | TypeDefinition::Unit
        )
    }
    fn copy_enum(&self, ty: TypeId) -> bool {
        self.p
            .declarations
            .enums
            .iter()
            .find(|e| e.ty == ty)
            .is_some_and(|e| {
                std::iter::once(e.variants.first)
                    .chain(e.variants.rest.iter().copied())
                    .all(|v| {
                        self.p.declarations.variants[v.0 as usize]
                            .fields
                            .iter()
                            .all(|f| self.primitive(self.p.declarations.fields[f.0 as usize].ty))
                    })
            })
    }
    fn replicable(plan: &StructuralReplicationPlan) -> bool {
        match &plan.strategy {
            StructuralReplicationStrategy::NoDuplication
            | StructuralReplicationStrategy::Primitive => true,
            StructuralReplicationStrategy::Struct(fields) => {
                fields.iter().all(|f| Self::replicable(&f.plan))
            }
            StructuralReplicationStrategy::Ineligible(_) => false,
        }
    }
    fn valid_move_source(&self, operation: OperationId) -> bool {
        match self.facts.operations.get(&operation).copied() {
            Some(Operation::MoveValue(moved)) => {
                let MoveSource::Place(place) = moved.source else {
                    return true;
                };
                let definition = self.p.objects.evaluated_places[place.0 as usize].definition;
                let place = &self.p.objects.places[definition.0 as usize];
                place.projections.is_empty() && !matches!(place.root, PlaceRoot::Reference(_))
            }
            Some(Operation::CaptureMove(capture)) => {
                self.p.contracts.captures[capture.record.0 as usize].moving
            }
            _ => true,
        }
    }
    fn mutation_permission_error(
        &self,
        target: EvaluatedPlaceId,
        site: &OperationSite,
    ) -> Option<&'static str> {
        if self.p.scopes.entries[site.scope.0 as usize]
            .unchecked_boundary
            .is_some()
        {
            return None;
        }
        let p = &self.p.objects.places[self.p.objects.evaluated_places[target.0 as usize]
            .definition
            .0 as usize];
        let targets = self
            .facts
            .place(p.id, site.execution_moments.first, &HashMap::new());
        if targets.iter().any(|t| {
            t.through.last().is_some_and(|r| {
                matches!(
                    self.p.objects.references[r.0 as usize].permission,
                    ReferencePermission::Shared
                )
            })
        }) {
            return Some("cannot write through a shared reference");
        }

        if let PlaceRoot::Binding(b) = p.root {
            let binding = &self.p.scopes.bindings[b.0 as usize];
            let dereferenced = p
                .projections
                .iter()
                .any(|p| matches!(p, PlaceProjection::Dereference));
            if dereferenced {
                if matches!(
                    self.p.types.entries[binding.ty.0 as usize].kind,
                    TypeDefinition::Reference {
                        permission: ReferencePermission::Shared,
                        ..
                    }
                ) {
                    return Some("cannot write through a shared reference");
                }
            } else if !binding.mutable {
                return Some("assignment requires a mutable binding");
            }
        }
        None
    }
}

/// Optional diagnostic progress; it does not affect any proof or verdict.
fn trace(phase: &str) {
    if std::env::var_os("CORBO_RULE_TRACE").is_some() {
        eprintln!("PostAST verifier: {phase}");
    }
}
