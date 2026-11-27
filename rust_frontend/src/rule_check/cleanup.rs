//! Validate the ownership/dependency forest and retain logical release order.
//! No layout, byte offset, datastack or runtime reclamation is chosen here.
use super::*;
#[derive(Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
enum Step {
    Hook(u32),
    End(u32),
    Component(u32, u32),
}
impl Checker<'_> {
    fn entity_ty(&self, e: &EntityId) -> TypeId {
        match e {
            EntityId::Address(a) => self.p.objects.addresses[a.0 as usize].ty,
            EntityId::Reference(r) => self.p.objects.references[r.0 as usize].ty,
            EntityId::Collection(c) => self.p.objects.collections[c.0 as usize].ty,
        }
    }
    fn component_entity(&self, parent: &EntityId, position: &PositionSelector) -> Option<EntityId> {
        for value in self
            .facts
            .values_by_entity
            .get(parent)
            .into_iter()
            .flatten()
        {
            let value = &self.p.values.entries[value.0 as usize];
            let op = match value.definition {
                ValueDefinition::OperationResult { operation, .. }
                | ValueDefinition::ConditionalResult { operation, .. } => {
                    self.facts.operations.get(&operation).copied()
                }
                _ => None,
            };
            let components = match op {
                Some(Operation::ConstructStruct(x)) => Some(&x.components),
                Some(Operation::ConstructEnum(x)) => Some(&x.components),
                Some(Operation::ConstructTuple(x)) => Some(&x.components),
                Some(Operation::ConstructArray(x)) => Some(&x.components),
                _ => None,
            };
            if let Some(component) =
                components.and_then(|parts| parts.iter().find(|c| &c.position == position))
            {
                if let Some(child) = self
                    .facts
                    .identities_by_value
                    .get(&component.value)
                    .and_then(|identities| identities.first())
                {
                    return Some(child.entity.clone());
                }
            }
        }
        None
    }
    fn cleanup_entities(
        &self,
        exit: ScopeExitId,
    ) -> Vec<(EntityId, PredicateId, Guard, Vec<CleanupCandidateId>)> {
        let mut entities: Vec<(EntityId, PredicateId, Guard, Vec<CleanupCandidateId>)> = vec![];
        for candidate in self
            .input
            .semantics
            .lifetimes
            .cleanup_candidates
            .iter()
            .filter(|candidate| candidate.exit == exit)
        {
            if let Some((_, _, combined, candidates)) = entities
                .iter_mut()
                .find(|(entity, _, _, _)| *entity == candidate.entity.entity)
            {
                *combined = combined.or(&self.flow.predicate(candidate.guard));
                candidates.push(candidate.id);
            } else {
                entities.push((
                    candidate.entity.entity.clone(),
                    candidate.guard,
                    self.flow.predicate(candidate.guard),
                    vec![candidate.id],
                ));
            }
        }
        entities
    }
    fn cleanup_receipt(
        &self,
        entity: &EntityId,
        exit: ExecutionMomentId,
    ) -> Option<ExecutionMomentId> {
        let mut receipt = match entity {
            EntityId::Address(id) => match self.p.objects.addresses[id.0 as usize].creation {
                ObjectCreation::At(at) => Some(at),
                _ => None,
            },
            EntityId::Reference(id) => match self.p.objects.references[id.0 as usize].creation {
                ObjectCreation::At(at) => Some(at),
                _ => None,
            },
            EntityId::Collection(id) => {
                match self.p.objects.collections[id.0 as usize].descriptor {
                    CollectionDescriptor::Address(address) => {
                        match self.p.objects.addresses[address.0 as usize].creation {
                            ObjectCreation::At(at) => Some(at),
                            _ => None,
                        }
                    }
                    CollectionDescriptor::Place(_) => None,
                }
            }
        };
        for link in self
            .facts
            .ownership_by_entity
            .get(entity)
            .into_iter()
            .flatten()
        {
            if self
                .flow
                .path(link.established, exit, &self.flow.predicate(link.guard))
            {
                if receipt.is_none_or(|old| {
                    self.flow.path(old, link.established, &Guard::yes())
                        && !self.flow.path(link.established, old, &Guard::yes())
                }) {
                    receipt = Some(link.established);
                }
            }
        }
        receipt
    }
    pub(super) fn cleanup_checks(&mut self) {
        let mut drops_by_entity: HashMap<EntityId, Vec<&DropValue>> = HashMap::new();
        for operation in self.p.bodies.iter().flat_map(|body| &body.operations) {
            if let Operation::DropValue(drop) = operation {
                for identity in self
                    .facts
                    .identities_by_value
                    .get(&drop.value)
                    .into_iter()
                    .flatten()
                {
                    drops_by_entity
                        .entry(identity.entity.clone())
                        .or_default()
                        .push(drop);
                }
            }
        }
        for exit in &self.p.scopes.exits {
            let entities = self.cleanup_entities(exit.id);
            if entities.is_empty() {
                continue;
            }
            let indexes = entities
                .iter()
                .enumerate()
                .map(|(i, (e, _, _, _))| (e.clone(), i as u32))
                .collect::<HashMap<_, _>>();
            let mut edges: HashMap<Step, HashSet<Step>> = HashMap::new();
            let conditions = entities
                .iter()
                .map(|(entity, _, combined_guard, _)| {
                    let mut live = combined_guard.clone();
                    for drop in drops_by_entity.get(entity).into_iter().flatten() {
                        if self.flow.path(
                            drop.site.execution_moments.first,
                            exit.event,
                            &self.guard(&drop.site),
                        ) {
                            live = live.and(&self.guard(&drop.site).not());
                        }
                    }
                    live
                })
                .collect::<Vec<_>>();
            for (i, _) in entities.iter().enumerate() {
                edges
                    .entry(Step::Hook(i as u32))
                    .or_default()
                    .insert(Step::End(i as u32));
                edges.entry(Step::End(i as u32)).or_default();
            }
            // A hook is never the complete destruction procedure. Components
            // without separately materialized entity nodes still need teardown.
            for (i, (entity, _, _, _)) in entities.iter().enumerate() {
                if let Some(destructor) = self
                    .p
                    .contracts
                    .destructors
                    .iter()
                    .find(|d| d.ty == self.entity_ty(entity))
                {
                    for (j, component) in destructor.owned_components.iter().enumerate() {
                        if self
                            .component_entity(entity, &component.position)
                            .is_some_and(|child| indexes.contains_key(&child))
                        {
                            continue;
                        }
                        let step = Step::Component(i as u32, j as u32);
                        edges.entry(Step::Hook(i as u32)).or_default().insert(step);
                        edges.entry(step).or_default().insert(Step::End(i as u32));
                    }
                    let component_steps = (0..destructor.owned_components.len())
                        .map(|index| {
                            self.component_entity(
                                entity,
                                &destructor.owned_components[index].position,
                            )
                            .and_then(|child| indexes.get(&child).copied())
                            .map(Step::End)
                            .unwrap_or(Step::Component(i as u32, index as u32))
                        })
                        .collect::<Vec<_>>();
                    for (j, component) in destructor.owned_components.iter().enumerate() {
                        for needed in &component.dependencies {
                            if let Some(k) = destructor
                                .owned_components
                                .iter()
                                .position(|other| &other.position == needed)
                            {
                                let first = component_steps[j];
                                let after = component_steps[k];
                                if first != after {
                                    edges.entry(first).or_default().insert(after);
                                }
                            } else {
                                self.gaps.push(SemanticGap {
                                    consumer: CoreRule::N7,
                                    operation: self.site_at(exit.event).id,
                                    missing: MissingFact::MalformedGraph(
                                        "component cleanup dependency has no resolved position"
                                            .into(),
                                    ),
                                    origin: self.site_at(exit.event).origin,
                                });
                            }
                        }
                    }
                }
            }
            for link in entities.iter().flat_map(|(entity, _, _, _)| {
                self.facts
                    .ownership_by_entity
                    .get(entity)
                    .into_iter()
                    .flatten()
            }) {
                let Some(child) = indexes.get(&link.entity).copied() else {
                    continue;
                };
                if !self
                    .flow
                    .predicate(link.guard)
                    .and(&self.flow.predicate(exit.guard))
                    .possible()
                    || !self.flow.path(
                        link.established,
                        exit.event,
                        &self.flow.predicate(link.guard),
                    )
                {
                    continue;
                }
                if let Owner::Entity(parent) = &link.owner {
                    if let Some(parent) = indexes.get(&parent.entity).copied() {
                        // User hook runs before owned fields are cleaned. Storage
                        // lifetime ends only after every owned child's lifetime.
                        edges
                            .entry(Step::Hook(parent))
                            .or_default()
                            .insert(Step::Hook(child));
                        edges
                            .entry(Step::End(child))
                            .or_default()
                            .insert(Step::End(parent));
                    }
                }
            }
            // The resolved result recipes identify reference/storage dependencies;
            // cleanup may not reclaim a target still used by another destructor.
            for (i, (entity, _, combined_guard, _)) in entities.iter().enumerate() {
                let Some(destructor) = self
                    .p
                    .contracts
                    .destructors
                    .iter()
                    .find(|d| d.ty == self.entity_ty(entity))
                else {
                    continue;
                };
                let values = self
                    .facts
                    .values_by_entity
                    .get(entity)
                    .cloned()
                    .unwrap_or_default();
                for value in values {
                    for target in self
                        .facts
                        .destructor_reads(destructor.hook, value, exit.event)
                    {
                        if !combined_guard.and(&target.guard).possible() {
                            continue;
                        }
                        let targets = match target.root {
                            Root::Address(address) => vec![EntityId::Address(address)],
                            Root::Collection(collection) => vec![EntityId::Collection(collection)],
                            Root::Binding(binding) => self.p.objects.addresses.iter()
                                .filter(|a| matches!(a.initial_owner, Owner::Binding { binding: b, .. } if b == binding))
                                .map(|a| EntityId::Address(a.id)).collect(),
                            _ => vec![],
                        };
                        for target in targets {
                            if let Some(j) = indexes.get(&target) {
                                if *j != i as u32 {
                                    edges
                                        .entry(Step::Hook(i as u32))
                                        .or_default()
                                        .insert(Step::End(*j));
                                }
                            }
                        }
                    }
                }
            }
            let mut indegree = edges
                .keys()
                .map(|s| (*s, 0usize))
                .collect::<HashMap<_, _>>();
            for tos in edges.values() {
                for to in tos {
                    *indegree.entry(*to).or_default() += 1;
                }
            }
            let receipts = entities
                .iter()
                .map(|(entity, _, _, _)| self.cleanup_receipt(entity, exit.event))
                .collect::<Vec<_>>();
            // Choose reverse receipt among currently admissible steps. Never
            // mistake entity IDs or vector position for execution ordering.
            let mut ready = indegree
                .iter()
                .filter_map(|(s, n)| (*n == 0).then_some(*s))
                .collect::<Vec<_>>();
            let mut ordered = vec![];
            while !ready.is_empty() {
                let entity_index = |step: Step| match step {
                    Step::Hook(i) | Step::End(i) | Step::Component(i, _) => i as usize,
                };
                let mut preferred = 0;
                for candidate in 1..ready.len() {
                    let newer = receipts[entity_index(ready[candidate])];
                    let older = receipts[entity_index(ready[preferred])];
                    let later = match (older, newer) {
                        (Some(old), Some(new)) => {
                            self.flow.path(old, new, &Guard::yes())
                                && !self.flow.path(new, old, &Guard::yes())
                        }
                        (None, Some(_)) => true,
                        _ => false,
                    };
                    if later || (newer == older && ready[candidate] > ready[preferred]) {
                        preferred = candidate;
                    }
                }
                let step = ready.swap_remove(preferred);
                ordered.push(step);
                for next in &edges[&step] {
                    let n = indegree.get_mut(next).unwrap();
                    *n -= 1;
                    if *n == 0 {
                        ready.push(*next);
                    }
                }
            }
            if ordered.len() != edges.len() {
                self.reject_destruction_obligations_at(
                    &self.site_at(exit.event),
                    "ownership and destructor dependencies do not admit a safe cleanup order",
                );
                continue;
            }
            let mut steps = vec![];
            for step in ordered {
                if let Step::Component(index, component) = step {
                    let (entity, _, _, _) = &entities[index as usize];
                    let condition = &conditions[index as usize];
                    if !condition.possible() {
                        continue;
                    }
                    let destructor = self
                        .p
                        .contracts
                        .destructors
                        .iter()
                        .find(|d| d.ty == self.entity_ty(entity))
                        .unwrap();
                    let component = &destructor.owned_components[component as usize];
                    steps.push(VerifiedDestructionStep::OwnedComponent {
                        parent: entity.clone(),
                        position: component.position.clone(),
                        destructor: component.destructor,
                        component_guard: component.guard,
                        condition: condition.exported(),
                    });
                    continue;
                }
                let (index, hook) = match step {
                    Step::Hook(i) => (i, true),
                    Step::End(i) => (i, false),
                    Step::Component(..) => unreachable!(),
                };
                let (entity, representative_guard, _, candidates) = &entities[index as usize];
                let condition = &conditions[index as usize];
                if !condition.possible() {
                    continue;
                }
                if hook {
                    if let Some(destructor) = self
                        .p
                        .contracts
                        .destructors
                        .iter()
                        .find(|d| d.ty == self.entity_ty(entity))
                    {
                        steps.push(VerifiedDestructionStep::Hook {
                            entity: entity.clone(),
                            destructor: destructor.id,
                            guard: *representative_guard,
                            condition: condition.exported(),
                        });
                    } else {
                        self.gaps.push(SemanticGap {
                            consumer: CoreRule::N7,
                            operation: self.site_at(exit.event).id,
                            missing: MissingFact::MalformedGraph(format!(
                                "no resolved destructor for {entity:?}"
                            )),
                            origin: self.site_at(exit.event).origin,
                        });
                    }
                } else {
                    steps.push(VerifiedDestructionStep::EndLifetime {
                        entity: entity.clone(),
                        candidates: candidates.clone(),
                        guard: *representative_guard,
                        condition: condition.exported(),
                    });
                }
            }
            self.derived.cleanup.push(VerifiedExitCleanup {
                exit: exit.id,
                steps,
            });
        }
    }
}
