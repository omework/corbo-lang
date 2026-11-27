//! Alias and dependency queries over resolved identities. No names or type inference.
use super::{flow::Flow, guards::Guard};
use crate::post_ast::*;
use std::{
    cell::{Cell, RefCell},
    collections::{HashMap, HashSet},
};
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub(super) enum Root {
    Binding(BindingId),
    Address(AddressId),
    Collection(CollectionId),
    External(BindingId),
    FormalContents(BindingId),
    Boundary(ScopeId),
    HeldLock(LockIdentityId),
    RequiredLock(LockIdentityId),
    Completion(CompletionCapabilityId),
    Value(ValueId),
}
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub(super) enum Selector {
    Field(FieldId),
    Tuple(u32),
    Variant(VariantId),
    Index(Option<u64>),
    Range(Option<u64>, Option<u64>),
    Content,
    Dereference,
}
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub(super) struct Target {
    pub root: Root,
    pub path: Vec<Selector>,
    pub through: Vec<ReferenceId>,
    pub guard: Guard,
}
pub(super) type Substitution = HashMap<BindingId, ValueId>;
/// A query is context-sensitive: execution moment and actual argument bindings
/// are part of its identity, rather than reusing a callee result at another call.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
struct DependencyQuery {
    value: ValueId,
    at: ExecutionMomentId,
    substitutions: Vec<(BindingId, ValueId)>,
}

pub(super) struct Facts<'a> {
    pub p: &'a PostAst,
    pub flow: &'a Flow,
    pub references: HashMap<ValueId, ReferenceId>,
    pub operations: HashMap<OperationId, &'a Operation>,
    pub identities_by_value: HashMap<ValueId, Vec<&'a ValueEntityIdentity>>,
    pub values_by_entity: HashMap<EntityId, Vec<ValueId>>,
    pub ownership_by_entity: HashMap<EntityId, Vec<&'a OwnershipLink>>,
    entities_by_binding: HashMap<BindingId, Vec<EntityId>>,
    dependency_cache: RefCell<HashMap<DependencyQuery, Vec<Target>>>,
    dependency_solving: Cell<bool>,
    dependency_current: RefCell<Option<DependencyQuery>>,
    dependency_consumers: RefCell<HashMap<DependencyQuery, HashSet<DependencyQuery>>>,
    dependency_dirty: RefCell<HashSet<DependencyQuery>>,
}
impl<'a> Facts<'a> {
    pub fn new(p: &'a PostAst, flow: &'a Flow) -> Self {
        let mut references = HashMap::new();
        let operations = p
            .bodies
            .iter()
            .flat_map(|b| &b.operations)
            .map(|o| {
                match o {
                    Operation::BorrowShared(x) => {
                        references.insert(x.result, x.reference);
                    }
                    Operation::BorrowMutable(x) => {
                        references.insert(x.result, x.reference);
                    }
                    Operation::ReborrowShared(x) => {
                        references.insert(x.result, x.reference);
                    }
                    Operation::ReborrowMutable(x) => {
                        references.insert(x.result, x.reference);
                    }
                    Operation::SliceView(x) => {
                        references.insert(x.result, x.reference);
                    }
                    _ => {}
                }
                (o.site().id, o)
            })
            .collect();
        for r in &p.objects.references {
            if let Owner::Binding { binding, .. } = r.initial_owner {
                if matches!(
                    p.scopes.bindings[binding.0 as usize].introduced,
                    BindingIntroduction::Parameter { .. }
                ) {
                    if let Some(v) = p.values.entries.iter().find(
                        |v| matches!(v.definition,ValueDefinition::Parameter(b) if b==binding),
                    ) {
                        references.insert(v.id, r.id);
                    }
                }
            }
        }
        for identity in &p.objects.value_entities {
            if let EntityId::Reference(reference) = identity.entity {
                let value = &p.values.entries[identity.value.0 as usize];
                if matches!(
                    p.values.provenance[value.provenance.0 as usize].kind,
                    ProvenanceKind::Projection { .. } | ProvenanceKind::PlaceRead { .. }
                ) {
                    references.entry(identity.value).or_insert(reference);
                }
            }
        }
        let mut identities_by_value: HashMap<ValueId, Vec<&ValueEntityIdentity>> = HashMap::new();
        let mut values_by_entity: HashMap<EntityId, Vec<ValueId>> = HashMap::new();
        for identity in &p.objects.value_entities {
            identities_by_value
                .entry(identity.value)
                .or_default()
                .push(identity);
            values_by_entity
                .entry(identity.entity.clone())
                .or_default()
                .push(identity.value);
        }
        let mut ownership_by_entity: HashMap<EntityId, Vec<&OwnershipLink>> = HashMap::new();
        let mut entities_by_binding: HashMap<BindingId, Vec<EntityId>> = HashMap::new();
        for link in &p.objects.ownership {
            if let Owner::Binding { binding, .. } = link.owner {
                entities_by_binding
                    .entry(binding)
                    .or_default()
                    .push(link.entity.clone());
            }
            ownership_by_entity
                .entry(link.entity.clone())
                .or_default()
                .push(link);
        }
        Self {
            identities_by_value,
            values_by_entity,
            ownership_by_entity,
            entities_by_binding,
            p,
            flow,
            references,
            operations,
            dependency_cache: RefCell::new(HashMap::new()),
            dependency_solving: Cell::new(false),
            dependency_current: RefCell::new(None),
            dependency_consumers: RefCell::new(HashMap::new()),
            dependency_dirty: RefCell::new(HashSet::new()),
        }
    }
    pub fn place(&self, place: PlaceId, at: ExecutionMomentId, env: &Substitution) -> Vec<Target> {
        self.place_inner(place, at, env, &mut HashSet::new())
    }
    fn place_inner(
        &self,
        id: PlaceId,
        at: ExecutionMomentId,
        env: &Substitution,
        seen: &mut HashSet<(PlaceId, ExecutionMomentId)>,
    ) -> Vec<Target> {
        if !seen.insert((id, at)) {
            return vec![];
        }
        let p = &self.p.objects.places[id.0 as usize];
        let mut projections = p.projections.as_slice();
        let mut result = match p.root {
            PlaceRoot::Binding(b) => {
                if projections
                    .first()
                    .is_some_and(|p| matches!(p, PlaceProjection::Dereference))
                {
                    projections = &projections[1..];
                    let values = env
                        .get(&b)
                        .copied()
                        .map(|v| vec![v])
                        .unwrap_or_else(|| self.flow.values(b, at));
                    let parameter = matches!(
                        self.p.scopes.bindings[b.0 as usize].introduced,
                        BindingIntroduction::Parameter { .. }
                    );
                    let mut targets = if parameter && !env.contains_key(&b) {
                        vec![]
                    } else {
                        values
                            .iter()
                            .flat_map(|v| self.dependencies(*v, at, env))
                            .collect::<Vec<_>>()
                    };
                    if targets.is_empty() && parameter {
                        let through = values
                            .iter()
                            .filter_map(|value| self.references.get(value).copied())
                            .collect();
                        targets.push(Target {
                            root: Root::External(b),
                            path: vec![],
                            through,
                            guard: Guard::yes(),
                        });
                    }
                    targets
                } else {
                    vec![Target {
                        root: Root::Binding(b),
                        path: vec![],
                        through: vec![],
                        guard: Guard::yes(),
                    }]
                }
            }
            PlaceRoot::Reference(r) => self.reference(r, at, env),
            PlaceRoot::Address(a) => vec![Target {
                root: Root::Address(a),
                path: vec![],
                through: vec![],
                guard: Guard::yes(),
            }],
            PlaceRoot::Collection(c) => vec![Target {
                root: Root::Collection(c),
                path: vec![],
                through: vec![],
                guard: Guard::yes(),
            }],
            PlaceRoot::Value(v) => {
                if let Some(index) = projections
                    .iter()
                    .position(|p| matches!(p, PlaceProjection::Dereference))
                {
                    let values = self.component_values(
                        v,
                        &projections[..index],
                        at,
                        env,
                        &mut HashSet::new(),
                    );
                    projections = &projections[index + 1..];
                    values
                        .into_iter()
                        .flat_map(|v| self.dependencies(v, at, env))
                        .collect()
                } else {
                    vec![Target {
                        root: Root::Value(v),
                        path: vec![],
                        through: vec![],
                        guard: Guard::yes(),
                    }]
                }
            }
        };
        for projection in projections {
            let selector = match projection {
                PlaceProjection::Field(f) => Selector::Field(*f),
                PlaceProjection::TupleElement(i) => Selector::Tuple(*i),
                PlaceProjection::Variant(v) => Selector::Variant(*v),
                PlaceProjection::Index(v) => Selector::Index(self.integer(*v)),
                PlaceProjection::Key(v) => Selector::Index(self.integer(*v)),
                PlaceProjection::AllocationContent => Selector::Content,
                PlaceProjection::Dereference => {
                    result = result
                        .into_iter()
                        .flat_map(|target| self.dereference_target(target, at, env))
                        .collect();
                    continue;
                }
                PlaceProjection::Range { start, end } => {
                    Selector::Range(self.integer(*start), self.integer(*end))
                }
            };
            for target in &mut result {
                target.path.push(selector.clone());
            }
        }
        seen.remove(&(id, at));
        result
    }
    fn projection_path(path: &[Selector]) -> Option<Vec<PlaceProjection>> {
        path.iter()
            .map(|selector| {
                Some(match selector {
                    Selector::Field(f) => PlaceProjection::Field(*f),
                    Selector::Tuple(i) => PlaceProjection::TupleElement(*i),
                    Selector::Variant(v) => PlaceProjection::Variant(*v),
                    Selector::Content => PlaceProjection::AllocationContent,
                    Selector::Dereference => PlaceProjection::Dereference,
                    _ => return None,
                })
            })
            .collect()
    }
    fn dereference_target(
        &self,
        mut target: Target,
        at: ExecutionMomentId,
        env: &Substitution,
    ) -> Vec<Target> {
        let values = match target.root {
            Root::Binding(binding) => self.flow.values(binding, at),
            Root::Value(value) => vec![value],
            Root::Address(_) | Root::Collection(_) => self
                .p
                .objects
                .value_entities
                .iter()
                .filter(|identity| {
                    matches!((&identity.entity, &target.root),
                    (EntityId::Address(a), Root::Address(b)) if a == b)
                        || matches!((&identity.entity, &target.root),
                    (EntityId::Collection(a), Root::Collection(b)) if a == b)
                })
                .map(|identity| identity.value)
                .collect(),
            _ => vec![],
        };
        if let Some(path) = Self::projection_path(&target.path) {
            let mut result = vec![];
            for value in values {
                for content in self.component_values(value, &path, at, env, &mut HashSet::new()) {
                    for mut pointee in self.dependencies(content, at, env) {
                        pointee.guard = pointee.guard.and(&target.guard);
                        pointee.through.extend(target.through.clone());
                        result.push(pointee);
                    }
                }
            }
            if !result.is_empty() {
                return result;
            }
        }
        if let Root::Binding(binding) = target.root {
            if matches!(
                self.p.scopes.bindings[binding.0 as usize].introduced,
                BindingIntroduction::Parameter { .. }
            ) {
                target.root = Root::FormalContents(binding);
            }
        }
        target.path.push(Selector::Dereference);
        vec![target]
    }
    fn apply_target_path(
        &self,
        mut target: Target,
        path: &[Selector],
        at: ExecutionMomentId,
        env: &Substitution,
    ) -> Vec<Target> {
        let mut targets = vec![];
        if let Some((first, rest)) = path.split_first() {
            if matches!(first, Selector::Dereference) {
                for target in self.dereference_target(target, at, env) {
                    targets.extend(self.apply_target_path(target, rest, at, env));
                }
            } else {
                target.path.push(first.clone());
                targets.extend(self.apply_target_path(target, rest, at, env));
            }
        } else {
            targets.push(target);
        }
        targets
    }
    pub fn reference(
        &self,
        r: ReferenceId,
        at: ExecutionMomentId,
        env: &Substitution,
    ) -> Vec<Target> {
        let reference = &self.p.objects.references[r.0 as usize];
        let mut out = vec![];
        for origin in std::iter::once(&reference.origins.first).chain(&reference.origins.rest) {
            for mut t in self.place_inner(
                origin.target,
                match reference.creation {
                    ObjectCreation::At(m) => m,
                    _ => at,
                },
                env,
                &mut HashSet::new(),
            ) {
                if let Some(parent) = origin.parent {
                    self.push_reference_lineage(parent, &mut t.through, &mut HashSet::new());
                }
                t.through.push(r);
                t.guard = t.guard.and(&self.flow.predicate(origin.guard));
                out.push(t);
            }
        }
        out
    }

    fn push_reference_lineage(
        &self,
        reference: ReferenceId,
        through: &mut Vec<ReferenceId>,
        seen: &mut HashSet<ReferenceId>,
    ) {
        if !seen.insert(reference) {
            return;
        }
        let definition = &self.p.objects.references[reference.0 as usize];
        for origin in std::iter::once(&definition.origins.first).chain(&definition.origins.rest) {
            if let Some(parent) = origin.parent {
                self.push_reference_lineage(parent, through, seen);
            }
        }
        through.push(reference);
    }
    pub fn dependencies(
        &self,
        value: ValueId,
        at: ExecutionMomentId,
        env: &Substitution,
    ) -> Vec<Target> {
        self.all_dependencies(value, at, env)
            .into_iter()
            .filter(|target| {
                !matches!(
                    target.root,
                    Root::HeldLock(_) | Root::RequiredLock(_) | Root::Completion(_)
                )
            })
            .collect()
    }
    pub fn holds_lock(&self, value: ValueId, lock: LockIdentityId, at: ExecutionMomentId) -> bool {
        self.all_dependencies(value, at, &HashMap::new())
            .iter()
            .any(|target| {
                matches!(target.root, Root::HeldLock(found) if found == lock)
                    && target.guard.possible()
            })
    }
    fn all_dependencies(
        &self,
        value: ValueId,
        at: ExecutionMomentId,
        env: &Substitution,
    ) -> Vec<Target> {
        if !self.dependency_solving.get() {
            let mut substitutions = env.iter().map(|(b, v)| (*b, *v)).collect::<Vec<_>>();
            substitutions.sort_unstable();
            let query = DependencyQuery {
                value,
                at,
                substitutions,
            };
            if let Some(result) = self.dependency_cache.borrow().get(&query) {
                return result.clone();
            }
        }
        let nested = self.dependency_solving.replace(true);
        let initial = self.value_dependencies(value, at, env, &mut HashSet::new());
        if nested {
            return initial;
        }
        // Only consumers of a changed summary need another evaluation. The
        // graph is discovered by resolved dependency queries, not by source calls.
        loop {
            let next = self.dependency_dirty.borrow().iter().next().cloned();
            let Some(query) = next else { break };
            self.dependency_dirty.borrow_mut().remove(&query);
            let substitutions = query.substitutions.iter().copied().collect();
            let previous = self.dependency_current.replace(Some(query.clone()));
            let computed = self.compute_dependencies(
                query.value,
                query.at,
                &substitutions,
                &mut HashSet::new(),
            );
            self.dependency_current.replace(previous);
            self.merge_dependencies(&query, computed);
        }
        self.dependency_solving.set(false);
        self.value_dependencies(value, at, env, &mut HashSet::new())
    }
    fn merge_dependencies(&self, query: &DependencyQuery, incoming: Vec<Target>) -> bool {
        let mut cache = self.dependency_cache.borrow_mut();
        let current = cache.entry(query.clone()).or_default();
        let mut changed = false;
        for mut target in incoming {
            // A loan chain is a set of traversed references with its final
            // reference retained last (permission checks use that final link).
            let mut visited = HashSet::new();
            target.through.reverse();
            target.through.retain(|r| visited.insert(*r));
            target.through.reverse();
            if let Some(old) = current.iter_mut().find(|old| {
                old.root == target.root && old.path == target.path && old.through == target.through
            }) {
                let combined = old.guard.or(&target.guard);
                if combined != old.guard {
                    old.guard = combined;
                    changed = true;
                }
            } else if target.guard.possible() {
                current.push(target);
                changed = true;
            }
        }
        drop(cache);
        if changed {
            if let Some(consumers) = self.dependency_consumers.borrow().get(query) {
                self.dependency_dirty
                    .borrow_mut()
                    .extend(consumers.iter().cloned());
            }
        }
        changed
    }
    fn value_dependencies(
        &self,
        value: ValueId,
        at: ExecutionMomentId,
        env: &Substitution,
        seen: &mut HashSet<ValueId>,
    ) -> Vec<Target> {
        let mut substitutions = env.iter().map(|(b, v)| (*b, *v)).collect::<Vec<_>>();
        substitutions.sort_unstable();
        let query = DependencyQuery {
            value,
            at,
            substitutions,
        };
        if let Some(consumer) = self.dependency_current.borrow().as_ref() {
            self.dependency_consumers
                .borrow_mut()
                .entry(query.clone())
                .or_default()
                .insert(consumer.clone());
        }
        if let Some(result) = self.dependency_cache.borrow().get(&query) {
            return result.clone();
        }
        self.dependency_cache
            .borrow_mut()
            .insert(query.clone(), vec![]);
        let previous = self.dependency_current.replace(Some(query.clone()));
        let result = self.compute_dependencies(value, at, env, seen);
        self.dependency_current.replace(previous);
        self.merge_dependencies(&query, result);
        self.dependency_cache.borrow()[&query].clone()
    }
    fn compute_dependencies(
        &self,
        value: ValueId,
        at: ExecutionMomentId,
        env: &Substitution,
        seen: &mut HashSet<ValueId>,
    ) -> Vec<Target> {
        let v = &self.p.values.entries[value.0 as usize];
        // Substitute formals before consulting their abstract reference node.
        if let ValueDefinition::Parameter(b) = v.definition {
            if let Some(actual) = env.get(&b) {
                return self.value_dependencies(*actual, at, &HashMap::new(), seen);
            }
        }
        if let Some(r) = self.references.get(&value) {
            return self.reference(*r, at, env);
        }
        let summary = &self.p.values.dependency_summaries[v.dependencies.0 as usize];
        let mut result = vec![];
        for d in &summary.dependencies {
            self.requirement(d, at, env, seen, &mut result);
        }
        for d in &summary.guarded {
            let mut targets = vec![];
            self.requirement(&d.requirement, at, env, seen, &mut targets);
            for mut target in targets {
                target.guard = target.guard.and(&self.flow.predicate(d.guard));
                result.push(target);
            }
        }
        // Copy/move provenance retains identity even when a result recipe has no new dependency.
        match &self.p.values.provenance[v.provenance.0 as usize].kind {
            ProvenanceKind::Forward { source, .. } | ProvenanceKind::Move { source, .. } => {
                result.extend(self.value_dependencies(*source, at, env, seen))
            }
            ProvenanceKind::Merge(values) => {
                for source in std::iter::once(&values.first).chain(&values.rest) {
                    for mut t in self.value_dependencies(source.value, at, env, seen) {
                        t.guard = t.guard.and(&self.flow.predicate(source.guard));
                        result.push(t);
                    }
                }
            }
            _ => {}
        }
        let mut unique = HashSet::new();
        result.retain(|target| unique.insert(target.clone()));
        result
    }
    fn requirement(
        &self,
        d: &DependencyRequirement,
        at: ExecutionMomentId,
        env: &Substitution,
        seen: &mut HashSet<ValueId>,
        out: &mut Vec<Target>,
    ) {
        match d {
            DependencyRequirement::CarriedByParameter { binding } => {
                if let Some(actual) = env.get(binding) {
                    out.extend(self.value_dependencies(*actual, at, &HashMap::new(), seen));
                } else {
                    out.push(Target {
                        root: Root::FormalContents(*binding),
                        path: vec![],
                        through: vec![],
                        guard: Guard::yes(),
                    });
                }
            }
            DependencyRequirement::LiveTarget(p) => out.extend(self.place(*p, at, env)),
            DependencyRequirement::LiveReference(r) => out.extend(self.reference(*r, at, env)),
            DependencyRequirement::CarriedByPlace { place, at: read } => {
                let target = self.p.objects.evaluated_places[place.0 as usize].definition;
                for (value, substitutions) in self.prior_writes(target, *read, env) {
                    out.extend(self.value_dependencies(value, *read, &substitutions, seen));
                }
                let p = &self.p.objects.places[self.p.objects.evaluated_places[place.0 as usize]
                    .definition
                    .0 as usize];
                match p.root {
                    PlaceRoot::Binding(b) => {
                        for v in env
                            .get(&b)
                            .copied()
                            .map(|v| vec![v])
                            .unwrap_or_else(|| self.flow.values(b, *read))
                        {
                            out.extend(self.value_dependencies(v, *read, env, seen));
                        }
                    }
                    PlaceRoot::Value(v) => out.extend(self.value_dependencies(v, *read, env, seen)),
                    PlaceRoot::Reference(r) => out.extend(self.reference(r, *read, env)),
                    _ => {}
                }
            }
            DependencyRequirement::CarriedByProjection {
                source,
                position,
                result,
            } => {
                let projection = match position {
                    PositionSelector::Field(field)
                    | PositionSelector::VariantField { field, .. } => {
                        Some(PlaceProjection::Field(*field))
                    }
                    PositionSelector::TupleElement(index) => {
                        Some(PlaceProjection::TupleElement(*index))
                    }
                    PositionSelector::FixedIndex(_) => None,
                    _ => None,
                };
                let selected = projection
                    .map(|projection| {
                        self.component_values(*source, &[projection], at, env, &mut HashSet::new())
                    })
                    .unwrap_or_default();
                if selected.is_empty() {
                    let mut targets = self.value_dependencies(*source, at, env, seen);
                    if self.dependency_free_type(*result, &mut HashSet::new()) {
                        targets.retain(|target| {
                            matches!(
                                target.root,
                                Root::Boundary(_)
                                    | Root::HeldLock(_)
                                    | Root::RequiredLock(_)
                                    | Root::Completion(_)
                            )
                        });
                    }
                    out.extend(targets);
                } else {
                    for selected in selected {
                        out.extend(self.value_dependencies(selected, at, env, seen));
                    }
                }
            }
            DependencyRequirement::NativeResult { source, .. } => {
                out.extend(self.value_dependencies(*source, at, env, seen))
            }
            DependencyRequirement::When { guard, requirement } => {
                let mut targets = vec![];
                self.requirement(requirement, at, env, seen, &mut targets);
                for mut t in targets {
                    t.guard = t.guard.and(&self.flow.predicate(*guard));
                    out.push(t);
                }
            }
            DependencyRequirement::InstantiatedResult {
                function,
                arguments,
            } => {
                let instance = &self.p.declarations.instances[function.0 as usize];
                let mut substitutions = env.clone();
                if let Some(body) = instance.body {
                    for b in &self.p.scopes.entries[self.p.bodies[body.0 as usize].scope.0 as usize]
                        .bindings
                    {
                        if let BindingIntroduction::Parameter { position, .. } =
                            self.p.scopes.bindings[b.0 as usize].introduced
                        {
                            if let Some(v) = arguments.get(position as usize) {
                                substitutions.insert(*b, *v);
                            }
                        }
                    }
                }
                if let Some(NativeReturnRecipe::TaskOutputOfParameter(index)) =
                    instance.result.native
                {
                    if let Some(handle) = arguments.get(index as usize) {
                        for (value, env) in self.task_return_values(*handle, &mut HashSet::new()) {
                            out.extend(self.value_dependencies(value, at, &env, seen));
                        }
                    }
                } else {
                    for result in &instance.result.values {
                        let result_at = match self.p.values.entries[result.value.0 as usize]
                            .definition
                        {
                            ValueDefinition::OperationResult { produced_at, .. }
                            | ValueDefinition::ConditionalResult { produced_at, .. } => produced_at,
                            _ => at,
                        };
                        // Summarize formal origins before applying this call's
                        // actuals. Recursive invocations must not overwrite one
                        // another's parameter environment.
                        let formal =
                            self.value_dependencies(result.value, result_at, &HashMap::new(), seen);
                        for target in formal {
                            if !target.guard.possible() {
                                continue;
                            }
                            if let Root::External(binding) | Root::FormalContents(binding) =
                                target.root
                            {
                                if let Some(actual) = substitutions.get(&binding) {
                                    let actual_targets =
                                        if matches!(target.root, Root::FormalContents(_))
                                            && !target.path.is_empty()
                                        {
                                            let path = target
                                                .path
                                                .strip_suffix(&[Selector::Dereference])
                                                .unwrap_or(&target.path);
                                            Self::projection_path(path)
                                                .map(|path| {
                                                    self.component_values(
                                                        *actual,
                                                        &path,
                                                        at,
                                                        env,
                                                        &mut HashSet::new(),
                                                    )
                                                    .into_iter()
                                                    .flat_map(|value| {
                                                        self.value_dependencies(
                                                            value, at, env, seen,
                                                        )
                                                    })
                                                    .collect::<Vec<_>>()
                                                })
                                                .unwrap_or_else(|| {
                                                    self.value_dependencies(*actual, at, env, seen)
                                                })
                                        } else {
                                            self.value_dependencies(*actual, at, env, seen)
                                        };
                                    for mut actual_target in actual_targets {
                                        actual_target.through.extend(target.through.clone());
                                        if matches!(target.root, Root::External(_)) {
                                            out.extend(self.apply_target_path(
                                                actual_target,
                                                &target.path,
                                                at,
                                                env,
                                            ));
                                        } else {
                                            out.push(actual_target);
                                        }
                                    }
                                    continue;
                                }
                            }
                            out.push(Target {
                                guard: Guard::yes(),
                                ..target
                            });
                        }
                    }
                }
            }
            DependencyRequirement::ContractResult { arguments, .. } => {
                for v in arguments {
                    out.extend(self.value_dependencies(*v, at, env, seen));
                }
            }
            DependencyRequirement::FutureResult { future, .. } => {
                for (value, env) in self.task_return_values(*future, &mut HashSet::new()) {
                    out.extend(self.value_dependencies(value, at, &env, seen));
                }
            }
            DependencyRequirement::ContractFutureResult { future, .. } => {
                out.extend(self.value_dependencies(*future, at, env, seen))
            }
            DependencyRequirement::CallableResult {
                callable,
                arguments,
            } => {
                out.extend(self.value_dependencies(*callable, at, env, seen));
                for v in arguments {
                    out.extend(self.value_dependencies(*v, at, env, seen));
                }
            }
            DependencyRequirement::CapturedField { record, field } => {
                if let Some(c) = self.p.contracts.captures[record.0 as usize]
                    .captures
                    .iter()
                    .find(|c| c.field == *field)
                {
                    out.extend(self.value_dependencies(c.value, at, env, seen));
                }
            }
            DependencyRequirement::LiveStorage(storage) => {
                let storage = &self.p.storage_origins[storage.0 as usize];
                for v in storage
                    .pool
                    .into_iter()
                    .chain(storage.pool_choices.iter().map(|c| c.pool))
                {
                    if matches!(
                        self.p.types.entries[self.p.values.entries[v.0 as usize].ty.0 as usize]
                            .kind,
                        TypeDefinition::Reference { .. }
                    ) {
                        out.extend(self.value_dependencies(v, at, env, seen));
                    } else {
                        out.push(Target {
                            root: Root::Value(v),
                            path: vec![],
                            through: vec![],
                            guard: Guard::yes(),
                        });
                    }
                }
            }
            DependencyRequirement::ConfinedToUncheckedScope(scope) => out.push(Target {
                root: Root::Boundary(*scope),
                path: vec![],
                through: vec![],
                guard: Guard::yes(),
            }),
            DependencyRequirement::ActiveLock(lock) => out.push(Target {
                root: Root::RequiredLock(*lock),
                path: vec![],
                through: vec![],
                guard: Guard::yes(),
            }),
            DependencyRequirement::HoldsLock(lock) => out.push(Target {
                root: Root::HeldLock(*lock),
                path: vec![],
                through: vec![],
                guard: Guard::yes(),
            }),
            DependencyRequirement::BranchCompletion(capability) => out.push(Target {
                root: Root::Completion(*capability),
                path: vec![],
                through: vec![],
                guard: Guard::yes(),
            }),
        }
    }
    /// Instantiate resolved read effects against an object root. The caller
    /// supplies an identity, not a fabricated borrow or a lookup by type name.
    pub fn destructor_reads(
        &self,
        function: FunctionInstanceId,
        receiver: ValueId,
        at: ExecutionMomentId,
    ) -> Vec<Target> {
        type Environment = Vec<(BindingId, Vec<Target>)>;
        let bindings = |function: FunctionInstanceId, args: &[Vec<Target>]| -> Environment {
            self.p.declarations.instances[function.0 as usize]
                .body
                .into_iter()
                .flat_map(|body| {
                    self.p.scopes.entries[self.p.bodies[body.0 as usize].scope.0 as usize]
                        .bindings
                        .iter()
                })
                .filter_map(
                    |binding| match self.p.scopes.bindings[binding.0 as usize].introduced {
                        BindingIntroduction::Parameter { position, .. } => args
                            .get(position as usize)
                            .map(|targets| (*binding, targets.clone())),
                        _ => None,
                    },
                )
                .collect()
        };
        let root = Target {
            root: Root::Value(receiver),
            path: vec![],
            through: vec![],
            guard: Guard::yes(),
        };
        let mut work = vec![(function, bindings(function, &[vec![root]]))];
        let mut visited = HashSet::new();
        let mut reads = vec![];
        while let Some((function, env)) = work.pop() {
            if !visited.insert((function, env.clone())) {
                continue;
            }
            let effects = &self.p.effects
                [self.p.declarations.instances[function.0 as usize].effects.0 as usize];
            for effect in &effects.effects {
                if !self.flow.predicate(effect.guard).possible() {
                    continue;
                }
                let effect_at = match effect.timing {
                    EffectTiming::At(m) => m,
                    _ => at,
                };
                let apply = |targets: Vec<Target>| -> Vec<Target> {
                    targets
                        .into_iter()
                        .flat_map(|target| {
                            if let Root::External(binding) | Root::FormalContents(binding) =
                                target.root
                            {
                                if let Some((_, actuals)) = env.iter().find(|(b, _)| *b == binding)
                                {
                                    return actuals
                                        .iter()
                                        .flat_map(|actual| {
                                            self.apply_target_path(
                                                actual.clone(),
                                                &target.path,
                                                at,
                                                &HashMap::new(),
                                            )
                                        })
                                        .collect();
                                }
                            }
                            vec![target]
                        })
                        .collect()
                };
                match &effect.effect {
                    Effect::Read(read) => {
                        reads.extend(apply(self.place(read.place, effect_at, &HashMap::new())))
                    }
                    Effect::Call(call) => {
                        let args = call
                            .arguments
                            .iter()
                            .map(|arg| {
                                apply(self.dependencies(arg.value, effect_at, &HashMap::new()))
                            })
                            .collect::<Vec<_>>();
                        work.push((call.target, bindings(call.target, &args)));
                    }
                    _ => {}
                }
            }
        }
        let mut unique = HashSet::new();
        reads.retain(|target| unique.insert(target.clone()));
        reads
    }
    pub fn integer(&self, v: ValueId) -> Option<u64> {
        let value = &self.p.values.entries[v.0 as usize];
        match &value.definition {
            ValueDefinition::Constant(c) => match self.p.declarations.constants[c.0 as usize].value
            {
                ConstantValue::Integer(v) => u64::try_from(v).ok(),
                ConstantValue::Unsigned(v) => u64::try_from(v).ok(),
                _ => None,
            },
            ValueDefinition::OperationResult { operation, .. }
            | ValueDefinition::ConditionalResult { operation, .. } => {
                match self.operations.get(operation) {
                    Some(Operation::IntegerLiteral(x)) => match x.value {
                        IntegerConstant::Signed(v) => u64::try_from(v).ok(),
                        IntegerConstant::Unsigned(v) => u64::try_from(v).ok(),
                    },
                    _ => None,
                }
            }
            _ => None,
        }
    }

    pub fn target_entities(&self, target: &Target) -> Vec<EntityId> {
        match target.root {
            Root::Address(address) => vec![EntityId::Address(address)],
            Root::Collection(collection) => vec![EntityId::Collection(collection)],
            Root::Value(value) => self
                .identities_by_value
                .get(&value)
                .into_iter()
                .flatten()
                .map(|identity| identity.entity.clone())
                .collect(),
            Root::Binding(binding) => self
                .entities_by_binding
                .get(&binding)
                .cloned()
                .unwrap_or_default(),
            _ => vec![],
        }
    }
    pub fn overlaps(a: &Target, b: &Target) -> bool {
        // Distinct formal reference parameters are distinct semantic places.
        // Possible aliasing is proved/rejected at the call site where actual
        // roots are available; treating every External root as overlapping
        // makes unrelated parameters conflict inside a symbolic body.
        if a.root != b.root {
            return false;
        }
        for (a, b) in a.path.iter().zip(&b.path) {
            match (a, b) {
                (Selector::Field(a), Selector::Field(b)) if a != b => return false,
                (Selector::Tuple(a), Selector::Tuple(b)) if a != b => return false,
                (Selector::Index(Some(a)), Selector::Index(Some(b))) if a != b => return false,
                (Selector::Range(Some(a), Some(b)), Selector::Range(Some(c), Some(d)))
                    if b <= c || d <= a =>
                {
                    return false;
                }
                _ => {}
            }
        }
        true
    }

    /// Whether a value of this resolved type can carry an ordinary lifetime
    /// dependency. Raw-address confinement and runtime capabilities are kept
    /// separately even for scalar types.
    fn dependency_free_type(&self, ty: TypeId, seen: &mut HashSet<TypeId>) -> bool {
        if !seen.insert(ty) {
            return true;
        }
        match &self.p.types.entries[ty.0 as usize].kind {
            TypeDefinition::Never
            | TypeDefinition::Numeric(_)
            | TypeDefinition::NumericConversionError
            | TypeDefinition::Boolean
            | TypeDefinition::Unit
            | TypeDefinition::InlineUtf8 { .. } => true,
            TypeDefinition::Tuple(parts) => parts
                .iter()
                .all(|part| self.dependency_free_type(*part, seen)),
            TypeDefinition::Array { element, .. } => self.dependency_free_type(*element, seen),
            TypeDefinition::Nominal { .. } => {
                if let Some(record) = self
                    .p
                    .declarations
                    .structs
                    .iter()
                    .find(|item| item.ty == ty)
                {
                    return record.fields.iter().all(|field| {
                        self.dependency_free_type(
                            self.p.declarations.fields[field.0 as usize].ty,
                            seen,
                        )
                    });
                }
                if let Some(enumeration) =
                    self.p.declarations.enums.iter().find(|item| item.ty == ty)
                {
                    return std::iter::once(enumeration.variants.first)
                        .chain(enumeration.variants.rest.iter().copied())
                        .all(|variant| {
                            self.p.declarations.variants[variant.0 as usize]
                                .fields
                                .iter()
                                .all(|field| {
                                    self.dependency_free_type(
                                        self.p.declarations.fields[field.0 as usize].ty,
                                        seen,
                                    )
                                })
                        });
                }
                false
            }
            TypeDefinition::Parameter(_)
            | TypeDefinition::Reference { .. }
            | TypeDefinition::Utf8View
            | TypeDefinition::StrData
            | TypeDefinition::Slice { .. }
            | TypeDefinition::Callable(_)
            | TypeDefinition::Closure { .. }
            | TypeDefinition::Future { .. }
            | TypeDefinition::ContractFuture { .. }
            | TypeDefinition::Allocation { .. }
            | TypeDefinition::GrowingSequence { .. }
            | TypeDefinition::KeyedCollection { .. }
            | TypeDefinition::GrowingString
            | TypeDefinition::ExecutionHandle { .. }
            | TypeDefinition::Pool { .. } => false,
        }
    }
}
impl Facts<'_> {
    /// Follow resolved value/component recipes. This is substitution and graph
    /// traversal, not source lookup; ambiguous positions retain all candidates.
    fn component_values(
        &self,
        value: ValueId,
        path: &[PlaceProjection],
        at: ExecutionMomentId,
        env: &Substitution,
        seen: &mut HashSet<ValueId>,
    ) -> Vec<ValueId> {
        if path.is_empty() {
            return vec![value];
        }
        if !seen.insert(value) {
            return vec![];
        }
        let v = &self.p.values.entries[value.0 as usize];
        let mut out = vec![];
        if let ValueDefinition::Parameter(b) = v.definition {
            if let Some(actual) = env.get(&b) {
                out.extend(self.component_values(*actual, path, at, env, seen));
            }
        }
        let operation = match v.definition {
            ValueDefinition::OperationResult { operation, .. }
            | ValueDefinition::ConditionalResult { operation, .. } => {
                self.operations.get(&operation).copied()
            }
            _ => None,
        };
        let components = match operation {
            Some(Operation::ConstructStruct(x)) => Some(&x.components),
            Some(Operation::ConstructEnum(x)) => Some(&x.components),
            Some(Operation::ConstructTuple(x)) => Some(&x.components),
            Some(Operation::ConstructArray(x)) => Some(&x.components),
            _ => None,
        };
        if let Some(components) = components {
            for c in components {
                let selected = match (&path[0], &c.position) {
                    (PlaceProjection::Field(a), PositionSelector::Field(b)) => a == b,
                    (
                        PlaceProjection::Field(a),
                        PositionSelector::VariantField { field: b, .. },
                    ) => a == b,
                    (PlaceProjection::TupleElement(a), PositionSelector::TupleElement(b)) => a == b,
                    (PlaceProjection::Index(a), PositionSelector::FixedIndex(b)) => {
                        self.integer(*a).is_none_or(|a| a == *b)
                    }
                    _ => true,
                };
                if selected {
                    out.extend(self.component_values(c.value, &path[1..], at, env, seen));
                }
            }
        }
        match &self.p.values.provenance[v.provenance.0 as usize].kind {
            ProvenanceKind::Copy { source, .. }
            | ProvenanceKind::Forward { source, .. }
            | ProvenanceKind::Move { source, .. } => {
                out.extend(self.component_values(*source, path, at, env, seen))
            }
            ProvenanceKind::Merge(values) => {
                for v in std::iter::once(&values.first).chain(&values.rest) {
                    out.extend(self.component_values(v.value, path, at, env, seen));
                }
            }
            ProvenanceKind::CallResult { operation, .. } => {
                let call = self.operations.get(operation).copied();
                let signature = match call {
                    Some(Operation::DirectCall(x)) => Some((x.target, &x.arguments)),
                    Some(Operation::MethodCall(x)) => {
                        if let MethodTarget::Concrete(f) = x.target.target {
                            Some((f, &x.arguments))
                        } else {
                            None
                        }
                    }
                    _ => None,
                };
                if let Some((function, args)) = signature {
                    let arguments = args.iter().map(|a| a.value).collect::<Vec<_>>();
                    let instance = &self.p.declarations.instances[function.0 as usize];
                    if let Some(NativeReturnRecipe::TaskOutputOfParameter(index)) =
                        instance.result.native
                    {
                        if let Some(handle) = arguments.get(index as usize) {
                            out.extend(
                                self.task_return_values(*handle, &mut HashSet::new())
                                    .into_iter()
                                    .flat_map(|(value, substitutions)| {
                                        self.component_values(value, path, at, &substitutions, seen)
                                    }),
                            );
                        }
                    } else {
                        let substitutions = self.result_arguments(function, &arguments, env);
                        for result in &instance.result.values {
                            out.extend(self.component_values(
                                result.value,
                                path,
                                at,
                                &substitutions,
                                seen,
                            ));
                        }
                    }
                }
            }
            _ => {}
        }
        seen.remove(&value);
        out
    }
    fn result_arguments(
        &self,
        function: FunctionInstanceId,
        args: &[ValueId],
        env: &Substitution,
    ) -> Substitution {
        let mut substitutions = env.clone();
        if let Some(body) = self.p.declarations.instances[function.0 as usize].body {
            for b in
                &self.p.scopes.entries[self.p.bodies[body.0 as usize].scope.0 as usize].bindings
            {
                if let BindingIntroduction::Parameter { position, .. } =
                    self.p.scopes.bindings[b.0 as usize].introduced
                {
                    if let Some(v) = args.get(position as usize) {
                        substitutions.insert(*b, *v);
                    }
                }
            }
        }
        substitutions
    }
    fn task_return_values(
        &self,
        value: ValueId,
        seen: &mut HashSet<ValueId>,
    ) -> Vec<(ValueId, Substitution)> {
        if !seen.insert(value) {
            return vec![];
        }
        let v = &self.p.values.entries[value.0 as usize];
        let mut result = vec![];
        let op = match v.definition {
            ValueDefinition::OperationResult { operation, .. }
            | ValueDefinition::ConditionalResult { operation, .. } => {
                self.operations.get(&operation).copied()
            }
            _ => None,
        };
        match op {
            Some(Operation::CreateFuture(future)) => {
                let args = future.arguments.iter().map(|a| a.value).collect::<Vec<_>>();
                let env = self.result_arguments(future.function, &args, &HashMap::new());
                for v in &self.p.declarations.instances[future.function.0 as usize]
                    .result
                    .values
                {
                    result.push((v.value, env.clone()));
                }
            }
            Some(Operation::NativeOperation(x)) => {
                if let NativeOperationKind::RuntimeLaunch { task, .. } = x.kind {
                    result.extend(self.task_return_values(task, seen));
                }
            }
            Some(Operation::CreateClosure(c)) => {
                let record = &self.p.contracts.captures[c.captures.0 as usize];
                if let Some(function) = record.call {
                    for v in &self.p.declarations.instances[function.0 as usize]
                        .result
                        .values
                    {
                        result.push((v.value, HashMap::new()));
                    }
                }
            }
            _ => {}
        }
        match &self.p.values.provenance[v.provenance.0 as usize].kind {
            ProvenanceKind::Forward { source, .. } | ProvenanceKind::Move { source, .. } => {
                result.extend(self.task_return_values(*source, seen))
            }
            ProvenanceKind::Merge(values) => {
                for v in std::iter::once(&values.first).chain(&values.rest) {
                    result.extend(self.task_return_values(v.value, seen));
                }
            }
            _ => {}
        }
        seen.remove(&value);
        result
    }
}
impl Facts<'_> {
    fn effect_writes(
        &self,
        function: FunctionInstanceId,
        args: &[ValueId],
        at: ExecutionMomentId,
        parent: &Substitution,
        active: &mut HashSet<FunctionInstanceId>,
    ) -> Vec<(Vec<Target>, ValueId, Substitution)> {
        if !active.insert(function) {
            return vec![];
        }
        let env = self.result_arguments(function, args, parent);
        let instance = &self.p.declarations.instances[function.0 as usize];
        let mut out = vec![];
        if let Some(NativeReturnRecipe::TaskOutputOfParameter(index)) = instance.result.native {
            if let Some(handle) = args.get(index as usize) {
                for (function, args) in self.task_applications(*handle, &mut HashSet::new()) {
                    out.extend(self.effect_writes(function, &args, at, &env, active));
                }
            }
        }

        for effect in &self.p.effects[instance.effects.0 as usize].effects {
            match &effect.effect {
                Effect::Write(write) => {
                    let moment = match effect.timing {
                        EffectTiming::At(m) => m,
                        _ => at,
                    };
                    out.push((
                        self.place(write.place, moment, &env),
                        write.value,
                        env.clone(),
                    ));
                }
                Effect::Call(call) => {
                    let args = call.arguments.iter().map(|a| a.value).collect::<Vec<_>>();
                    out.extend(self.effect_writes(call.target, &args, at, &env, active));
                }
                Effect::AwaitFuture { future, .. } | Effect::JoinHandle { handle: future } => {
                    for (function, args) in self.task_applications(*future, &mut HashSet::new()) {
                        out.extend(self.effect_writes(function, &args, at, &env, active));
                    }
                }
                _ => {}
            }
        }
        active.remove(&function);
        out
    }
    fn prior_writes(
        &self,
        place: PlaceId,
        at: ExecutionMomentId,
        env: &Substitution,
    ) -> Vec<(ValueId, Substitution)> {
        let targets = self.place(place, at, env);
        let mut out = vec![];
        let body = self.p.execution.execution_moments[at.0 as usize].body;
        for op in &self.p.bodies[body.0 as usize].operations {
            let moment = op.site().execution_moments.first;
            if moment == at
                || !self
                    .flow
                    .path(moment, at, &self.flow.predicate(op.site().guard))
            {
                continue;
            }
            match op {
                Operation::Assign(write) => {
                    let places = self.place(
                        self.p.objects.evaluated_places[write.target.0 as usize].definition,
                        moment,
                        env,
                    );
                    if places
                        .iter()
                        .any(|a| targets.iter().any(|b| Self::overlaps(a, b)))
                    {
                        out.push((write.value, env.clone()));
                    }
                }
                Operation::AwaitValue(wait) => {
                    let received = *wait.site.execution_moments.rest.last().unwrap_or(&moment);
                    if !self
                        .flow
                        .path(received, at, &self.flow.predicate(wait.site.guard))
                    {
                        continue;
                    }
                    for (function, args) in self.task_applications(wait.source, &mut HashSet::new())
                    {
                        for (places, value, substitutions) in
                            self.effect_writes(function, &args, received, env, &mut HashSet::new())
                        {
                            if places
                                .iter()
                                .any(|a| targets.iter().any(|b| Self::overlaps(a, b)))
                            {
                                out.push((value, substitutions));
                            }
                        }
                    }
                }
                Operation::DirectCall(call) => {
                    let args = call.arguments.iter().map(|a| a.value).collect::<Vec<_>>();
                    for (places, value, substitutions) in
                        self.effect_writes(call.target, &args, moment, env, &mut HashSet::new())
                    {
                        if places
                            .iter()
                            .any(|a| targets.iter().any(|b| Self::overlaps(a, b)))
                        {
                            out.push((value, substitutions));
                        }
                    }
                }
                Operation::MethodCall(call) => {
                    if let MethodTarget::Concrete(function) = call.target.target {
                        let args = call.arguments.iter().map(|a| a.value).collect::<Vec<_>>();
                        for (places, value, substitutions) in
                            self.effect_writes(function, &args, moment, env, &mut HashSet::new())
                        {
                            if places
                                .iter()
                                .any(|a| targets.iter().any(|b| Self::overlaps(a, b)))
                            {
                                out.push((value, substitutions));
                            }
                        }
                    }
                }
                _ => {}
            }
        }
        out
    }
}
impl Facts<'_> {
    fn task_applications(
        &self,
        value: ValueId,
        seen: &mut HashSet<ValueId>,
    ) -> Vec<(FunctionInstanceId, Vec<ValueId>)> {
        if !seen.insert(value) {
            return vec![];
        }
        let v = &self.p.values.entries[value.0 as usize];
        let mut out = vec![];
        let op = match v.definition {
            ValueDefinition::OperationResult { operation, .. }
            | ValueDefinition::ConditionalResult { operation, .. } => {
                self.operations.get(&operation).copied()
            }
            _ => None,
        };
        match op {
            Some(Operation::CreateFuture(f)) => {
                out.push((f.function, f.arguments.iter().map(|a| a.value).collect()))
            }
            Some(Operation::NativeOperation(x)) => {
                if let NativeOperationKind::RuntimeLaunch { task, .. } = x.kind {
                    out.extend(self.task_applications(task, seen));
                }
            }
            Some(Operation::CreateClosure(c)) => {
                if let Some(f) = self.p.contracts.captures[c.captures.0 as usize].call {
                    out.push((f, vec![]));
                }
            }
            _ => {}
        }
        match &self.p.values.provenance[v.provenance.0 as usize].kind {
            ProvenanceKind::Forward { source, .. } | ProvenanceKind::Move { source, .. } => {
                out.extend(self.task_applications(*source, seen))
            }
            ProvenanceKind::Merge(values) => {
                for v in std::iter::once(&values.first).chain(&values.rest) {
                    out.extend(self.task_applications(v.value, seen));
                }
            }
            _ => {}
        }
        seen.remove(&value);
        out
    }
}
