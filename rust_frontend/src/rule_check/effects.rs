//! Instantiate resolved effect applications. Substitution follows parameter IDs;
//! it is not method resolution, overload selection or type inference.
use super::facts::{Substitution, Target};
use super::*;
#[derive(Clone)]
struct Event {
    site: OperationSite,
    target: Target,
    write: bool,
    lock: Option<Target>,
}
impl Checker<'_> {
    fn argument_map(
        &self,
        function: FunctionInstanceId,
        args: &[(u32, ValueId)],
        parent: &Substitution,
    ) -> Substitution {
        let mut env = parent.clone();
        if let Some(body) = self.p.declarations.instances[function.0 as usize].body {
            for b in
                &self.p.scopes.entries[self.p.bodies[body.0 as usize].scope.0 as usize].bindings
            {
                if let BindingIntroduction::Parameter { position, .. } =
                    self.p.scopes.bindings[b.0 as usize].introduced
                {
                    if let Some((_, v)) = args.iter().find(|(i, _)| *i == position) {
                        env.insert(*b, *v);
                    }
                }
            }
        }
        env
    }
    fn events(
        &self,
        body: BodyId,
        env: &Substitution,
        inherited: Option<Target>,
        active: &mut HashSet<BodyId>,
    ) -> Vec<Event> {
        if !active.insert(body) {
            return vec![];
        }
        let mut out = vec![];
        let instance = match self.p.bodies[body.0 as usize].owner {
            BodyOwner::Instance(i) => Some(i),
            _ => None,
        };
        let mut lock = inherited;
        if let Some(instance) = instance {
            let instance = &self.p.declarations.instances[instance.0 as usize];
            for contract in &instance.contracts {
                if let ResolvedContract::Lock(c) = contract {
                    let position = match self.p.contracts.locks[c.0 as usize].subject {
                        ResolvedSubject::Receiver => 0,
                        ResolvedSubject::Parameter(p) => p,
                        _ => continue,
                    };
                    if let Some(b)=self.p.scopes.entries[self.p.bodies[body.0 as usize].scope.0 as usize].bindings.iter().find(|b|matches!(self.p.scopes.bindings[b.0 as usize].introduced,BindingIntroduction::Parameter{position:p,..} if p==position)){
                    if let Some(actual)=env.get(b){lock=self.facts.dependencies(*actual,self.p.execution.timelines[self.p.execution.branches[self.p.bodies[body.0 as usize].root_branch.0 as usize].timeline.0 as usize].entries.first,env).into_iter().next();}
                }
                }
            }
        }
        for op in &self.p.bodies[body.0 as usize].operations {
            let site = op.site();
            if !self.guard(site).possible() {
                continue;
            }
            let mut places = vec![];
            if let Operation::ReadValue(x) = op {
                places.push((
                    self.p.objects.evaluated_places[x.source.0 as usize].definition,
                    false,
                ));
            }
            for access in &self.p.obligations.n5 {
                if access.site.operation == site.id {
                    let AccessCompatibilityRequirement::PlaceAccess { place, access, .. } =
                        &access.requirement
                    else {
                        continue;
                    };
                    places.push((
                        *place,
                        matches!(
                            access,
                            AccessKind::Write
                                | AccessKind::Destroy
                                | AccessKind::Reclaim
                                | AccessKind::Move
                        ),
                    ));
                }
            }
            for (place, write) in places {
                for target in self.facts.place(place, site.execution_moments.first, env) {
                    out.push(Event {
                        site: site.clone(),
                        target,
                        write,
                        lock: lock.clone(),
                    });
                }
            }
            let call = match op {
                Operation::DirectCall(x) => Some((
                    x.target,
                    x.arguments
                        .iter()
                        .map(|a| (a.parameter_index, a.value))
                        .collect::<Vec<_>>(),
                )),
                Operation::MethodCall(x) => {
                    if let MethodTarget::Concrete(f) = x.target.target {
                        Some((
                            f,
                            std::iter::once((0, x.target.receiver))
                                .chain(x.arguments.iter().map(|a| (a.parameter_index, a.value)))
                                .collect(),
                        ))
                    } else {
                        None
                    }
                }
                _ => None,
            };
            if let Some((function, args)) = call {
                if let Some(callee) = self.p.declarations.instances[function.0 as usize].body {
                    let env = self.argument_map(function, &args, env);
                    let mut child = self.events(callee, &env, lock.clone(), active);
                    // Effects occur at the caller invocation interval. Callee source
                    // origins are preserved for secondary diagnostics.
                    for e in &mut child {
                        e.site = site.clone();
                    }
                    out.extend(child);
                }
            }
        }
        active.remove(&body);
        out
    }
    pub(super) fn future_creation(
        &self,
        value: ValueId,
        seen: &mut HashSet<ValueId>,
    ) -> Option<&CreateFuture> {
        if !seen.insert(value) {
            return None;
        }
        let v = &self.p.values.entries[value.0 as usize];
        if let ValueDefinition::OperationResult { operation, .. }
        | ValueDefinition::ConditionalResult { operation, .. } = v.definition
        {
            if let Some(Operation::CreateFuture(f)) = self.facts.operations.get(&operation) {
                return Some(f);
            }
        }
        match &self.p.values.provenance[v.provenance.0 as usize].kind {
            ProvenanceKind::Forward { source, .. } | ProvenanceKind::Move { source, .. } => {
                self.future_creation(*source, seen)
            }
            _ => None,
        }
    }
    pub(super) fn synchronization_checks(&mut self) {
        let mut launched = vec![];
        for app in &self.p.contracts.applications {
            let ContractApplication::Branch {
                call, capability, ..
            } = app
            else {
                continue;
            };
            let Some(op) = self.facts.operations.get(call) else {
                continue;
            };
            let launch_site = op.site().clone();
            let task = match op {
                Operation::NativeOperation(x) => {
                    if let NativeOperationKind::RuntimeLaunch { task, .. } = x.kind {
                        task
                    } else {
                        continue;
                    }
                }
                _ => continue,
            };
            let events = if let Some(future) = self.future_creation(task, &mut HashSet::new()) {
                let args = future
                    .arguments
                    .iter()
                    .map(|a| (a.parameter_index, a.value))
                    .collect::<Vec<_>>();
                let env = self.argument_map(future.function, &args, &HashMap::new());
                self.events(future.body, &env, None, &mut HashSet::new())
            } else if let TypeDefinition::Closure { captures, .. } =
                self.p.types.entries[self.p.values.entries[task.0 as usize].ty.0 as usize].kind
            {
                self.p.contracts.captures[captures.0 as usize]
                    .call
                    .and_then(|f| self.p.declarations.instances[f.0 as usize].body)
                    .map(|body| self.events(body, &HashMap::new(), None, &mut HashSet::new()))
                    .unwrap_or_default()
            } else {
                // N8 has already established that an abstract task with shared
                // dependencies exposes enough effects. No body means there are
                // no concrete events to expand here.
                vec![]
            };
            launched.push((launch_site, *capability, events));
        }
        for (site, capability, events) in &launched {
            let parent_events = self.events(site.body, &HashMap::new(), None, &mut HashSet::new());
            let mut stops = HashMap::new();
            for done in &self.p.contracts.completions[capability.0 as usize].established_at {
                stops.insert(done.moment, self.flow.predicate(done.guard));
            }
            for event in events {
                for other in &parent_events {
                    if other.site.id == site.id {
                        continue;
                    }
                    let guard = self
                        .guard(site)
                        .and(&event.target.guard)
                        .and(&other.target.guard);
                    if self.flow.path_avoiding(
                        site.execution_moments.first,
                        other.site.execution_moments.first,
                        &guard,
                        &stops,
                    ) {
                        self.compatible_events(event, other, site);
                    }
                }
            }
        }
        for (i, (site, capability, events)) in launched.iter().enumerate() {
            let mut stops = HashMap::new();
            for done in &self.p.contracts.completions[capability.0 as usize].established_at {
                stops.insert(done.moment, self.flow.predicate(done.guard));
            }
            for (other_site, _, other_events) in &launched[i + 1..] {
                if !self.flow.path_avoiding(
                    site.execution_moments.first,
                    other_site.execution_moments.first,
                    &self.guard(site),
                    &stops,
                ) {
                    continue;
                }
                for a in events {
                    for b in other_events {
                        self.compatible_events(a, b, other_site);
                    }
                }
            }
        }
    }
    fn compatible_events(&mut self, a: &Event, b: &Event, site: &OperationSite) {
        if !(a.write || b.write) || !Facts::overlaps(&a.target, &b.target) {
            return;
        }
        if !a.target.guard.and(&b.target.guard).possible() {
            return;
        }
        let same_lock = match (&a.lock, &b.lock) {
            (Some(a), Some(b)) => a.root == b.root && a.path == b.path,
            _ => false,
        };
        if !same_lock {
            self.reject_access_obligations_at(site,"potentially concurrent overlapping accesses are not protected by the same resolved lock",vec![a.site.origin,b.site.origin]);
        }
    }
}
