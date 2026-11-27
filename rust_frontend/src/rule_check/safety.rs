//! All collection/aggregate safety queries use places, provenance and ownership.
//! No dispatch on a library type's name or source location is permitted here.
use super::facts::Target;
use super::*;
struct Access {
    place: PlaceId,
    site: OperationSite,
    targets: Vec<Target>,
    kind: AccessKind,
    obligation: Option<ObligationId>,
}
impl Checker<'_> {
    pub(super) fn stored_dependencies_hold(
        &self,
        destinations: &[super::facts::Target],
        value: ValueId,
        env: &HashMap<BindingId, ValueId>,
        site: &OperationSite,
    ) -> bool {
        let dependencies = self
            .facts
            .dependencies(value, site.execution_moments.first, env);
        destinations.iter().all(|destination| {
            let scope = self.target_scope(&destination.root);
            dependencies.iter().all(|target| {
                if !self
                    .guard(site)
                    .and(&target.guard)
                    .and(&destination.guard)
                    .possible()
                {
                    return true;
                }
                self.target_scope(&target.root).is_none_or(|target_scope| {
                    scope.is_some_and(|scope| self.ancestor(target_scope, scope))
                        || self.target_escapes(&target.root)
                })
            })
        })
    }
    pub(super) fn escaping_dependencies_hold(&self, value: ValueId, site: &OperationSite) -> bool {
        let targets = self
            .facts
            .dependencies(value, site.execution_moments.first, &HashMap::new())
            .into_iter()
            .filter(|target| self.guard(site).and(&target.guard).possible())
            .collect::<Vec<_>>();
        let live = targets.iter().all(|target| {
            self.target_scope(&target.root).is_none() || self.target_escapes(&target.root)
        });
        let confined = self.confined_value_holds(value, site, true);
        if std::env::var_os("CORBO_RULE_TRACE").is_some() && !(live && confined) {
            eprintln!(
                "N4 escape value={value:?} ty={:?} scope={:?} targets={:?} target_scopes={:?} provenance={:?}",
                self.p.values.entries[value.0 as usize].ty,
                site.scope,
                targets
                    .iter()
                    .map(|target| (&target.root, &target.path, &target.through))
                    .collect::<Vec<_>>(),
                targets
                    .iter()
                    .map(|target| self.target_scope(&target.root))
                    .collect::<Vec<_>>(),
                self.p.values.provenance
                    [self.p.values.entries[value.0 as usize].provenance.0 as usize]
                    .kind,
            );
        }
        live && confined
    }

    pub(super) fn target_scope(&self, root: &Root) -> Option<ScopeId> {
        match root {
            Root::Binding(b) => Some(self.p.scopes.bindings[b.0 as usize].scope),
            Root::Address(a) => match self.p.objects.addresses[a.0 as usize].creation {
                ObjectCreation::Static(_) => None,
                _ => Some(self.p.objects.addresses[a.0 as usize].created_in),
            },
            Root::Collection(c) => Some(self.p.objects.collections[c.0 as usize].created_in),
            Root::External(_)
            | Root::FormalContents(_)
            | Root::HeldLock(_)
            | Root::RequiredLock(_)
            | Root::Completion(_) => None,
            Root::Boundary(scope) => Some(*scope),
            Root::Value(v) => match self.p.values.entries[v.0 as usize].definition {
                ValueDefinition::Constant(_) | ValueDefinition::ConfiguredConstant { .. } => None,
                ValueDefinition::Parameter(b) => Some(self.p.scopes.bindings[b.0 as usize].scope),
                ValueDefinition::OperationResult { operation, .. }
                | ValueDefinition::ConditionalResult { operation, .. } => self
                    .facts
                    .operations
                    .get(&operation)
                    .map(|o| o.site().scope),
                _ => None,
            },
        }
    }
    pub(super) fn target_escapes(&self, root: &Root) -> bool {
        self.p.objects.addresses.iter().any(|a| {
            let same = match (&a.initial_owner, root) {
                (Owner::Binding { binding, .. }, Root::Binding(b)) => binding == b,
                (_, Root::Address(b)) => a.id == *b,
                _ => false,
            };
            same && self.input.finals.iter().any(|f| {
                matches!(f.scope, LogicalScope::CallerResult(_))
                    && self.p.values.placement_summaries
                        [self.p.values.entries[f.value.0 as usize].placement.0 as usize]
                        .origins
                        .contains(&a.storage)
            })
        })
    }
    pub(super) fn ancestor(&self, parent: ScopeId, mut child: ScopeId) -> bool {
        loop {
            if parent == child {
                return true;
            }
            match self.p.scopes.entries[child.0 as usize].lexical_parent {
                Some(p) => child = p,
                None => return false,
            }
        }
    }
    pub(super) fn borrow_checks(&mut self) {
        let mut accesses = vec![];
        let access_obligations = self
            .p
            .obligations
            .n5
            .iter()
            .filter_map(|obligation| {
                let AccessCompatibilityRequirement::PlaceAccess { place, access, .. } =
                    &obligation.requirement
                else {
                    return None;
                };
                (
                    (
                        obligation.site.operation,
                        *place,
                        std::mem::discriminant(access),
                    ),
                    obligation.site.id,
                )
                    .into()
            })
            .collect::<HashMap<_, _>>();
        let snapshots = self
            .p
            .bodies
            .iter()
            .flat_map(|b| &b.operations)
            .filter_map(|o| {
                if let Operation::Assign(x) = o {
                    Some(x.replacement.previous)
                } else {
                    None
                }
            })
            .collect::<HashSet<_>>();
        for operation in self.p.bodies.iter().flat_map(|b| &b.operations) {
            let site = operation.site();
            if !self.guard(site).possible() {
                continue;
            }
            let place = match operation {
                Operation::ReadValue(x) if !snapshots.contains(&x.result) => {
                    Some((x.source, AccessKind::Read))
                }
                Operation::BorrowShared(x) => Some((x.source, AccessKind::SharedBorrow)),
                Operation::BorrowMutable(x) => Some((x.source, AccessKind::MutableBorrow)),
                Operation::Assign(x) => Some((x.target, AccessKind::Write)),
                Operation::MoveValue(x) => match x.source {
                    MoveSource::Place(p) => Some((p, AccessKind::Move)),
                    _ => None,
                },
                Operation::ReborrowShared(x) => Some((x.source, AccessKind::SharedBorrow)),
                Operation::ReborrowMutable(x) => Some((x.source, AccessKind::MutableBorrow)),
                Operation::SliceView(x) => Some((
                    x.base,
                    if matches!(x.permission, ReferencePermission::Mutable) {
                        AccessKind::MutableBorrow
                    } else {
                        AccessKind::SharedBorrow
                    },
                )),
                _ => None,
            };
            if let Some((place, kind)) = place {
                let definition = self.p.objects.evaluated_places[place.0 as usize].definition;
                let obligation = access_obligations
                    .get(&(site.id, definition, std::mem::discriminant(&kind)))
                    .copied();
                accesses.push(Access {
                    place: definition,
                    site: site.clone(),
                    targets: self.facts.place(
                        definition,
                        site.execution_moments.first,
                        &HashMap::new(),
                    ),
                    kind,
                    obligation,
                });
            }
        }
        // Access obligations are operation-independent. In particular the write
        // half of every compound assignment uses its resolved write moment.
        let mut covered_accesses = accesses
            .iter()
            .map(|access| {
                (
                    access.site.id,
                    access.place,
                    std::mem::discriminant(&access.kind),
                )
            })
            .collect::<HashSet<_>>();
        for obligation in &self.p.obligations.n5 {
            let AccessCompatibilityRequirement::PlaceAccess { place, access, .. } =
                &obligation.requirement
            else {
                continue;
            };
            if !covered_accesses.insert((
                obligation.site.operation,
                *place,
                std::mem::discriminant(access),
            )) {
                continue;
            }
            let site = self.site_at(obligation.site.moment);
            accesses.push(Access {
                place: *place,
                targets: self
                    .facts
                    .place(*place, obligation.site.moment, &HashMap::new()),
                kind: access.clone(),
                obligation: Some(obligation.site.id),
                site,
            });
        }
        let mut uses: HashMap<ReferenceId, Vec<(ExecutionMomentId, Guard)>> = HashMap::new();
        for access in &accesses {
            for t in &access.targets {
                for r in &t.through {
                    uses.entry(*r).or_default().push((
                        access.site.execution_moments.first,
                        self.guard(&access.site).and(&t.guard),
                    ));
                }
            }
        }
        // A descriptor passed by value is itself a reference use, even when no
        // dereference occurs in the caller. Resolved call arguments supply it.
        for op in self.p.bodies.iter().flat_map(|b| &b.operations) {
            let arguments = match op {
                Operation::DirectCall(x) => x.arguments.iter().map(|a| a.value).collect::<Vec<_>>(),
                Operation::MethodCall(x) => std::iter::once(x.target.receiver)
                    .chain(x.arguments.iter().map(|a| a.value))
                    .collect(),
                Operation::ReturnControl(x) => vec![x.value],
                Operation::CreateFuture(x) => x.arguments.iter().map(|a| a.value).collect(),
                _ => vec![],
            };
            for value in arguments {
                for t in self.facts.dependencies(
                    value,
                    op.site().execution_moments.first,
                    &HashMap::new(),
                ) {
                    for r in &t.through {
                        uses.entry(*r).or_default().push((
                            op.site().execution_moments.first,
                            self.guard(op.site()).and(&t.guard),
                        ));
                    }
                }
            }
        }
        let mut accesses_by_body: HashMap<BodyId, Vec<&Access>> = HashMap::new();
        for access in &accesses {
            accesses_by_body
                .entry(access.site.body)
                .or_default()
                .push(access);
        }
        for reference in &self.p.objects.references {
            if matches!(reference.formation, ReferenceFormation::FlowAlias) {
                continue;
            }
            let ObjectCreation::At(created) = reference.creation else {
                continue;
            };
            let creation_site = self.site_at(created);
            let targets = self.facts.reference(reference.id, created, &HashMap::new());
            let mut reference_uses = uses.get(&reference.id).cloned().unwrap_or_default();
            reference_uses.push((created, self.flow.predicate(creation_site.guard)));
            for access in accesses_by_body
                .get(&creation_site.body)
                .into_iter()
                .flatten()
            {
                let at = access.site.execution_moments.first;
                if at == created {
                    continue;
                }
                if matches!(reference.permission, ReferencePermission::Shared)
                    && matches!(access.kind, AccessKind::Read | AccessKind::SharedBorrow)
                {
                    continue;
                }
                for a in &access.targets {
                    if a.through.contains(&reference.id) {
                        continue;
                    }
                    for b in &targets {
                        if !Facts::overlaps(a, b) {
                            continue;
                        }
                        let guard = self.guard(&access.site).and(&a.guard).and(&b.guard);
                        if !guard.possible() {
                            continue;
                        }
                        if self.flow.path_in_occurrence(created, created, at, &guard)
                            && reference_uses.iter().any(|(used, g)| {
                                self.flow
                                    .path_in_occurrence(created, at, *used, &guard.and(g))
                            })
                        {
                            if std::env::var_os("CORBO_RULE_TRACE").is_some() {
                                eprintln!(
                                    "N5 conflict reference={:?} created={:?} access={:?}@{:?} target_a={:?} path_a={:?} through_a={:?} target_b={:?} path_b={:?} through_b={:?} uses={:?}",
                                    reference.id,
                                    created,
                                    access.kind,
                                    at,
                                    a.root,
                                    a.path,
                                    a.through,
                                    b.root,
                                    b.path,
                                    b.through,
                                    reference_uses
                                        .iter()
                                        .map(|(moment, _)| moment)
                                        .collect::<Vec<_>>(),
                                );
                                eprintln!(
                                    "  reference_origins={:?}",
                                    std::iter::once(&reference.origins.first)
                                        .chain(&reference.origins.rest)
                                        .map(|origin| {
                                            let place =
                                                &self.p.objects.places[origin.target.0 as usize];
                                            (
                                                origin.target,
                                                &place.root,
                                                &place.projections,
                                                origin.parent,
                                            )
                                        })
                                        .collect::<Vec<_>>()
                                );
                                eprintln!(
                                    "  through_origins={:?}",
                                    a.through
                                        .iter()
                                        .map(|through| {
                                            let through =
                                                &self.p.objects.references[through.0 as usize];
                                            (
                                                through.id,
                                                std::iter::once(&through.origins.first)
                                                    .chain(&through.origins.rest)
                                                    .map(|origin| origin.parent)
                                                    .collect::<Vec<_>>(),
                                            )
                                        })
                                        .collect::<Vec<_>>()
                                );
                            }
                            if let Some(obligation) = access.obligation {
                                self.reject_obligation(
                                    obligation,
                                    CoreRule::N5,
                                    &access.site,
                                    "access overlaps an active incompatible borrow",
                                    vec![creation_site.origin],
                                );
                            } else {
                                self.gaps.push(SemanticGap {
                                    consumer: CoreRule::N5,
                                    operation: access.site.id,
                                    missing: MissingFact::MalformedGraph(
                                        "resolved place access has no N5 obligation".into(),
                                    ),
                                    origin: access.site.origin,
                                });
                            }
                        }
                    }
                }
            }
        }
    }
    fn confined_value_holds(&self, value: ValueId, site: &OperationSite, escaping: bool) -> bool {
        let summary = &self.p.values.dependency_summaries
            [self.p.values.entries[value.0 as usize].dependencies.0 as usize];
        summary.dependencies.iter().all(|requirement| {
            !matches!(requirement, DependencyRequirement::ConfinedToUncheckedScope(boundary) if escaping || !self.ancestor(*boundary, site.scope))
        })
    }
    pub(super) fn transfer_destination_holds(&self, index: u32) -> bool {
        let Some(transfer) = self
            .input
            .semantics
            .destinations
            .transfers
            .get(index as usize)
        else {
            return false;
        };
        let scope = match transfer.receiver {
            Owner::Scope { scope, .. } => Some(scope),
            Owner::Binding { binding, .. } => {
                Some(self.p.scopes.bindings[binding.0 as usize].scope)
            }
            _ => None,
        };
        let Some(scope) = scope else { return true };
        self.facts
            .dependencies(transfer.result, transfer.at, &HashMap::new())
            .into_iter()
            .all(|target| {
                !self
                    .flow
                    .predicate(transfer.guard)
                    .and(&target.guard)
                    .possible()
                    || self.target_scope(&target.root).is_none_or(|target_scope| {
                        self.ancestor(target_scope, scope) || self.target_escapes(&target.root)
                    })
            })
    }
    pub(super) fn final_destination_holds(&self, id: FinalDestinationId) -> bool {
        let Some(destination) = self.input.finals.iter().find(|entry| entry.id == id) else {
            return false;
        };
        let destination_scope = match destination.scope {
            LogicalScope::Local(scope) => Some(scope),
            LogicalScope::CallerResult(_) => None,
            LogicalScope::BorrowedTarget(_) | LogicalScope::ExecutionBranch(_) => return true,
        };
        let definition = &self.p.values.entries[destination.value.0 as usize].definition;
        let moment = match definition {
            ValueDefinition::OperationResult { produced_at, .. }
            | ValueDefinition::ConditionalResult { produced_at, .. } => *produced_at,
            _ => return true,
        };
        let site = self.site_at(moment);
        let dependencies_hold = self
            .facts
            .dependencies(destination.value, moment, &HashMap::new())
            .into_iter()
            .all(|target| {
                !self
                    .flow
                    .predicate(destination.guard)
                    .and(&target.guard)
                    .possible()
                    || self.target_scope(&target.root).is_none_or(|scope| {
                        destination_scope
                            .is_some_and(|destination| self.ancestor(scope, destination))
                            || self.target_escapes(&target.root)
                    })
            });
        dependencies_hold
            && (destination_scope.is_some()
                || self.confined_value_holds(destination.value, &site, true))
    }
    pub(super) fn operation_dependencies_live(
        &self,
        value: Option<ValueId>,
        source: Option<EvaluatedPlaceId>,
        site: &OperationSite,
    ) -> bool {
        let mut dependencies = value
            .into_iter()
            .flat_map(|value| {
                self.facts
                    .dependencies(value, site.execution_moments.first, &HashMap::new())
            })
            .collect::<Vec<_>>();
        if let Some(source) = source {
            for location in self.facts.place(
                self.p.objects.evaluated_places[source.0 as usize].definition,
                site.execution_moments.first,
                &HashMap::new(),
            ) {
                if let Root::Value(carrier) = location.root {
                    dependencies.extend(self.facts.dependencies(
                        carrier,
                        site.execution_moments.first,
                        &HashMap::new(),
                    ));
                }
                dependencies.push(location);
            }
        }
        dependencies.into_iter().all(|target| {
            self.facts
                .target_entities(&target)
                .into_iter()
                .all(|entity| {
                    self.explicit_destructions
                        .get(&(site.body, entity))
                        .into_iter()
                        .flatten()
                        .all(|destruction| {
                            destruction.id == site.id
                                || !self.flow.path_in_occurrence(
                                    destruction.execution_moments.first,
                                    destruction.execution_moments.first,
                                    site.execution_moments.first,
                                    &self
                                        .guard(site)
                                        .and(&self.guard(destruction))
                                        .and(&target.guard),
                                )
                        })
                })
        })
    }
    pub(super) fn ownership_checks(&mut self) {
        // Export the resolved ownership timeline. N2 proof and rejection are
        // attached to the exact source obligations in
        // `settle_ownership_obligations`.
        for link in &self.p.objects.ownership {
            let event = &self.p.execution.execution_moments[link.established.0 as usize];
            self.derived.ownership_states.push(OwnershipStateAtMoment {
                condition: self.flow.predicate(link.guard).exported(),
                entity: EntityOccurrence {
                    entity: link.entity.clone(),
                    instance: event.instance,
                },
                at: MomentOccurrence {
                    moment: event.id,
                    context: event.instance,
                },
                guard: link.guard,
                owner: link.owner.clone(),
                scope: link.scope,
            });
        }
    }
}
