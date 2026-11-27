//! Branch completion, transfer eligibility and lock re-entry are independent
//! obligations. All dispatch uses resolved contracts and function identities.
use super::facts::Target;
use super::*;
impl Checker<'_> {
    pub(super) fn concurrency_checks(&mut self) {
        // Body-level lock contracts are trusted implementation boundaries. Calls
        // within them must not reacquire the same object, including indirectly.
        for instance in &self.p.declarations.instances {
            if let Some(body) = instance.body {
                if instance
                    .contracts
                    .iter()
                    .any(|c| matches!(c, ResolvedContract::Lock(_)))
                {
                    let signature = &self.p.declarations.signatures[instance.signature.0 as usize];
                    if !matches!(signature.receiver, ReceiverMode::None) {
                        let scope = self.p.bodies[body.0 as usize].scope;
                        if let Some(binding) = self.p.scopes.entries[scope.0 as usize]
                            .bindings
                            .iter()
                            .find(|b| {
                                matches!(
                                    self.p.scopes.bindings[b.0 as usize].introduced,
                                    BindingIntroduction::Parameter { position: 0, .. }
                                )
                            })
                        {
                            let target = Target {
                                root: Root::External(*binding),
                                path: vec![],
                                through: vec![],
                                guard: Guard::yes(),
                            };
                            self.lock_calls(body, &HashMap::new(), &[target], &mut HashSet::new());
                        }
                    }
                }
            }
        }
    }
    pub(super) fn branch_dependencies_hold(
        &self,
        call: OperationId,
        task: ValueId,
        capability: CompletionCapabilityId,
    ) -> bool {
        let Some(operation) = self.facts.operations.get(&call) else {
            return false;
        };
        let site = operation.site();
        let completion = &self.p.contracts.completions[capability.0 as usize];
        let mut barriers = HashMap::new();
        for completed in &completion.established_at {
            let old = barriers
                .entry(completed.moment)
                .or_insert_with(Guard::default);
            *old = old.or(&self.flow.predicate(completed.guard));
        }
        self.facts
            .dependencies(task, site.execution_moments.first, &HashMap::new())
            .into_iter()
            .all(|target| {
                let Some(scope) = self.target_scope_for_branch(&target.root, site.body) else {
                    return true;
                };
                let guard = self.guard(site).and(&target.guard);
                self.p.scopes.exits.iter().all(|exit| {
                    exit.scope != scope
                        || self.p.execution.execution_moments[exit.event.0 as usize].body
                            != site.body
                        || !self.flow.path_avoiding(
                            site.execution_moments.first,
                            exit.event,
                            &guard.and(&self.flow.predicate(exit.guard)),
                            &barriers,
                        )
                })
            })
    }
    fn target_scope_for_branch(&self, root: &Root, body: BodyId) -> Option<ScopeId> {
        match root {
            Root::External(_) => Some(self.p.bodies[body.0 as usize].scope),
            _ => self.target_scope(root),
        }
    }
    pub(super) fn forbidden_transfer(&self, ty: TypeId, seen: &mut HashSet<TypeId>) -> bool {
        if !seen.insert(ty) {
            return false;
        }
        if self
            .p
            .contracts
            .threads
            .iter()
            .any(|c| c.ty == ty && c.declared_forbidden)
        {
            return true;
        }
        match &self.p.types.entries[ty.0 as usize].kind {
            TypeDefinition::Reference { .. } => false,
            TypeDefinition::Tuple(parts) => parts.iter().any(|t| self.forbidden_transfer(*t, seen)),
            TypeDefinition::Array { element, .. }
            | TypeDefinition::GrowingSequence { element }
            | TypeDefinition::Pool { element } => self.forbidden_transfer(*element, seen),
            TypeDefinition::Allocation { content } => self.forbidden_transfer(*content, seen),
            TypeDefinition::KeyedCollection { key, value } => {
                self.forbidden_transfer(*key, seen) || self.forbidden_transfer(*value, seen)
            }
            TypeDefinition::Closure { captures, .. } => self.p.contracts.captures
                [captures.0 as usize]
                .captures
                .iter()
                .any(|c| {
                    self.forbidden_transfer(self.p.values.entries[c.value.0 as usize].ty, seen)
                }),
            TypeDefinition::Future { state, .. } => self.forbidden_transfer(*state, seen),
            TypeDefinition::Nominal { .. } => {
                self.p
                    .declarations
                    .structs
                    .iter()
                    .find(|s| s.ty == ty)
                    .is_some_and(|s| {
                        s.fields.iter().any(|f| {
                            self.forbidden_transfer(
                                self.p.declarations.fields[f.0 as usize].ty,
                                seen,
                            )
                        })
                    })
                    || self
                        .p
                        .declarations
                        .enums
                        .iter()
                        .find(|e| e.ty == ty)
                        .is_some_and(|e| {
                            std::iter::once(e.variants.first)
                                .chain(e.variants.rest.iter().copied())
                                .any(|v| {
                                    self.p.declarations.variants[v.0 as usize]
                                        .fields
                                        .iter()
                                        .any(|f| {
                                            self.forbidden_transfer(
                                                self.p.declarations.fields[f.0 as usize].ty,
                                                seen,
                                            )
                                        })
                                })
                        })
            }
            _ => false,
        }
    }
    fn lock_calls(
        &mut self,
        body: BodyId,
        env: &HashMap<BindingId, ValueId>,
        held: &[Target],
        active: &mut HashSet<BodyId>,
    ) {
        if !active.insert(body) {
            return;
        }
        for op in &self.p.bodies[body.0 as usize].operations {
            let (function, args) = match op {
                Operation::DirectCall(x) => (
                    x.target,
                    x.arguments
                        .iter()
                        .map(|a| (a.parameter_index, a.value))
                        .collect::<Vec<_>>(),
                ),
                Operation::MethodCall(x) => {
                    let MethodTarget::Concrete(f) = x.target.target else {
                        continue;
                    };
                    (
                        f,
                        std::iter::once((0, x.target.receiver))
                            .chain(x.arguments.iter().map(|a| (a.parameter_index, a.value)))
                            .collect(),
                    )
                }
                _ => continue,
            };
            let instance = &self.p.declarations.instances[function.0 as usize];
            let mut additional = vec![];
            for c in &instance.contracts {
                if let ResolvedContract::Lock(c) = c {
                    let index = match self.p.contracts.locks[c.0 as usize].subject {
                        ResolvedSubject::Receiver => 0,
                        ResolvedSubject::Parameter(i) => i,
                        _ => continue,
                    };
                    if let Some((_, value)) = args.iter().find(|(i, _)| *i == index) {
                        let targets =
                            self.facts
                                .dependencies(*value, op.site().execution_moments.first, env);
                        if targets
                            .iter()
                            .any(|a| held.iter().any(|b| Facts::overlaps(a, b)))
                        {
                            self.reject_access_obligations_at(
                                op.site(),
                                "direct or indirect same-object lock re-entry",
                                vec![],
                            );
                        }
                        additional.extend(targets);
                    }
                }
            }
            if let Some(callee) = instance.body {
                let mut substitutions = env.clone();
                for b in &self.p.scopes.entries[self.p.bodies[callee.0 as usize].scope.0 as usize]
                    .bindings
                {
                    if let BindingIntroduction::Parameter { position, .. } =
                        self.p.scopes.bindings[b.0 as usize].introduced
                    {
                        if let Some((_, v)) = args.iter().find(|(i, _)| *i == position) {
                            substitutions.insert(*b, *v);
                        }
                    }
                }
                let mut next = held.to_vec();
                next.extend(additional);
                self.lock_calls(callee, &substitutions, &next, active);
            }
        }
        active.remove(&body);
    }
}
