//! Per-body execution graphs and guarded reaching definitions. No lexical-order CFG.
use super::guards::{Atom, Guard, all};
use crate::post_ast::*;
use std::{
    collections::{BTreeMap, HashMap, HashSet, VecDeque},
    rc::Rc,
};
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(super) enum State {
    Uninitialized,
    Available(ValueId),
    Moved(ExecutionMomentId),
    Destroyed(ExecutionMomentId),
}
pub(super) type BindingStates = BTreeMap<State, Guard>;
pub(super) struct Flow {
    paths: std::cell::RefCell<HashMap<(ExecutionMomentId, ExecutionMomentId, Guard), bool>>,
    ancestors: std::cell::RefCell<HashMap<ExecutionMomentId, Rc<HashMap<ExecutionMomentId, u32>>>>,
    occurrence_paths: std::cell::RefCell<
        HashMap<
            (
                ExecutionMomentId,
                ExecutionMomentId,
                ExecutionMomentId,
                Guard,
            ),
            bool,
        >,
    >,
    pub predicates: Vec<Guard>,
    iteration_regions: HashMap<ExecutionMomentId, HashSet<LoopRegionId>>,
    iteration_backedges: HashMap<(ExecutionMomentId, ExecutionMomentId), LoopRegionId>,
    /// Predicates evaluated in a symbolic loop occurrence do not describe a
    /// stable fact after that loop exits. They are existentially forgotten at
    /// the exit boundary; outer predicates remain intact.
    loop_exit_atoms: HashMap<ExecutionMomentId, HashSet<Atom>>,
    states: std::cell::RefCell<HashMap<(BindingId, ExecutionMomentId), BindingStates>>,
    initial: HashMap<(BodyId, BindingId), State>,
    entries: HashSet<ExecutionMomentId>,
    changes: HashMap<(ExecutionMomentId, BindingId), Vec<(State, Guard)>>,
    predecessors: HashMap<ExecutionMomentId, Vec<(ExecutionMomentId, Guard, bool)>>,
    bodies: Vec<BodyId>,
    relevant_conditions: HashMap<BindingId, HashSet<Atom>>,
    pub reachable: HashMap<ExecutionMomentId, Guard>,
    pub edges: HashMap<ExecutionMomentId, Vec<(ExecutionMomentId, Guard, bool)>>,
}
impl Flow {
    pub fn new(p: &PostAst) -> Self {
        let predicates = all(p);
        let iteration_regions: HashMap<ExecutionMomentId, HashSet<LoopRegionId>> = p
            .execution
            .execution_moments
            .iter()
            .map(|event| {
                let mut context = event.instance;
                let mut regions = HashSet::new();
                loop {
                    context = match &p.execution.instance_domains[context.0 as usize].definition {
                        InstanceDomainDefinition::Iteration { parent, moment } => {
                            regions.insert(moment.region);
                            *parent
                        }
                        InstanceDomainDefinition::Call { parent, .. }
                        | InstanceDomainDefinition::Concurrent { parent, .. }
                        | InstanceDomainDefinition::AsyncInstance { parent, .. } => *parent,
                        InstanceDomainDefinition::Root { .. } => break,
                    };
                }
                (event.id, regions)
            })
            .collect();
        let value_moment = |value: ValueId| match p.values.entries[value.0 as usize].definition {
            ValueDefinition::OperationResult { produced_at, .. }
            | ValueDefinition::ConditionalResult { produced_at, .. }
            | ValueDefinition::Diverged { at: produced_at } => Some(produced_at),
            _ => None,
        };
        let mut loop_exit_atoms: HashMap<ExecutionMomentId, HashSet<Atom>> = HashMap::new();
        for loop_ in &p.execution.loops {
            let mut local = predicates
                .iter()
                .flat_map(Guard::support)
                .filter(|atom| {
                    let value = match atom {
                        Atom::Boolean(value)
                        | Atom::Variant(value, _)
                        | Atom::VariantPath(value, _, _) => Some(*value),
                        _ => None,
                    };
                    value
                        .and_then(value_moment)
                        .and_then(|moment| iteration_regions.get(&moment))
                        .is_some_and(|regions| regions.contains(&loop_.id))
                })
                .collect::<HashSet<_>>();
            // The header condition is evaluated before the symbolic iteration
            // instance is entered. It is nevertheless local to that loop and
            // must not constrain definitions after the exit merge.
            for operation in p.bodies.iter().flat_map(|body| &body.operations) {
                if let Operation::WhileControl(control) = operation {
                    if control.region == loop_.id {
                        local.extend(
                            p.execution
                                .predicates
                                .iter()
                                .filter(|predicate| {
                                    matches!(predicate.kind, PredicateKind::Boolean { value, .. } if value == control.condition)
                                })
                                .flat_map(|predicate| {
                                    predicates[predicate.id.0 as usize].support()
                                }),
                        );
                    }
                }
            }
            loop_exit_atoms
                .entry(loop_.break_target)
                .or_default()
                .extend(local);
        }
        let mut result = Self {
            paths: Default::default(),
            ancestors: Default::default(),
            occurrence_paths: Default::default(),
            predicates: predicates.clone(),
            iteration_regions,
            iteration_backedges: p
                .execution
                .edges
                .iter()
                .filter_map(|edge| match edge {
                    ExecutionEdge::LoopBack(edge) => Some(((edge.from, edge.to), edge.region)),
                    _ => None,
                })
                .collect(),
            loop_exit_atoms,
            states: Default::default(),
            initial: HashMap::new(),
            entries: HashSet::new(),
            changes: HashMap::new(),
            predecessors: HashMap::new(),
            bodies: p
                .execution
                .execution_moments
                .iter()
                .map(|event| event.body)
                .collect(),
            relevant_conditions: HashMap::new(),
            reachable: HashMap::new(),
            edges: HashMap::new(),
        };
        let mut edge = |from: ExecutionMomentId, to: ExecutionMomentId, g: Guard, back: bool| {
            if p.execution.execution_moments[from.0 as usize].body
                == p.execution.execution_moments[to.0 as usize].body
            {
                result.edges.entry(from).or_default().push((to, g, back));
            }
        };
        for e in &p.execution.edges {
            match e {
                ExecutionEdge::Sequence(e) => edge(e.before, e.after, Guard::yes(), false),
                ExecutionEdge::Conditional(e) => {
                    edge(e.from, e.to, predicates[e.guard.0 as usize].clone(), false)
                }
                ExecutionEdge::LoopBack(e) => edge(e.from, e.to, Guard::yes(), true),
                ExecutionEdge::PollRetry { from, poll, .. } => {
                    edge(*from, *poll, Guard::yes(), true)
                }
                _ => {}
            }
        }
        // Summaries connect already-resolved call instances to their return
        // continuations. Build the relation once instead of rescanning edges.
        let mut returns: HashMap<InstanceDomainId, Vec<ExecutionMomentId>> = HashMap::new();
        let mut resumes: HashMap<SuspensionId, Vec<ExecutionMomentId>> = HashMap::new();
        for e in &p.execution.edges {
            match e {
                ExecutionEdge::Return(r) => {
                    returns.entry(r.instance).or_default().push(r.continuation)
                }
                ExecutionEdge::Resume(r) => resumes.entry(r.point).or_default().push(r.to),
                _ => {}
            }
        }
        for e in &p.execution.edges {
            match e {
                ExecutionEdge::Call(c) => {
                    for to in returns.get(&c.instance).into_iter().flatten() {
                        edge(c.call, *to, Guard::yes(), false);
                    }
                }
                ExecutionEdge::Suspend(s) => {
                    for to in resumes.get(&s.point).into_iter().flatten() {
                        edge(s.from, *to, Guard::yes(), false);
                    }
                }
                _ => {}
            }
        }
        for (from, edges) in &result.edges {
            for (to, guard, back) in edges {
                result
                    .predecessors
                    .entry(*to)
                    .or_default()
                    .push((*from, guard.clone(), *back));
            }
        }
        let parameters = p
            .values
            .entries
            .iter()
            .filter_map(|value| match value.definition {
                ValueDefinition::Parameter(binding) => Some((binding, value.id)),
                _ => None,
            })
            .collect::<HashMap<_, _>>();
        let captures = p
            .values
            .entries
            .iter()
            .filter_map(|value| match value.definition {
                ValueDefinition::CaptureField { record, field } => {
                    Some(((record, field), value.id))
                }
                _ => None,
            })
            .collect::<HashMap<_, _>>();
        for body in &p.bodies {
            let ScopeEntry::BodyRoot {
                execution: entry, ..
            } = p.scopes.entries[body.scope.0 as usize].entry
            else {
                continue;
            };
            result.entries.insert(entry);
            for binding in &p.scopes.entries[body.scope.0 as usize].bindings {
                let initial = match p.scopes.bindings[binding.0 as usize].introduced {
                    BindingIntroduction::Parameter { .. } => parameters.get(binding).copied(),
                    BindingIntroduction::Capture { record, field } => {
                        captures.get(&(record, field)).copied()
                    }
                    _ => None,
                };
                if let Some(value) = initial {
                    result
                        .initial
                        .insert((body.id, *binding), State::Available(value));
                }
            }
            result.reachable.insert(entry, Guard::yes());
            let mut queue = VecDeque::from([entry]);
            let mut queued = HashSet::from([entry]);
            while let Some(moment) = queue.pop_front() {
                queued.remove(&moment);
                let event = &p.execution.execution_moments[moment.0 as usize];
                let path = result.reachable[&moment].and(&result.predicate(event.guard));
                for (to, guard, back) in result.edges.get(&moment).into_iter().flatten() {
                    let mut next = path.and(guard);
                    if !next.possible() {
                        continue;
                    }
                    if let Some(local) = result.loop_exit_atoms.get(to) {
                        let keep = next
                            .support()
                            .difference(local)
                            .cloned()
                            .collect::<HashSet<_>>();
                        next = next.project(&keep);
                    }
                    let next = if *back { Guard::yes() } else { next };
                    let old = result.reachable.entry(*to).or_default();
                    let new = old.or(&next);
                    if *old != new {
                        *old = new;
                        if queued.insert(*to) {
                            queue.push_back(*to);
                        }
                    }
                }
            }
            for operation in &body.operations {
                let site = operation.site();
                let last = *site
                    .execution_moments
                    .rest
                    .last()
                    .unwrap_or(&site.execution_moments.first);
                let guard = result.predicate(site.guard);
                let mut add = |binding, state, guard| {
                    result
                        .changes
                        .entry((last, binding))
                        .or_default()
                        .push((state, guard));
                };
                match operation {
                    Operation::InitializeBinding(x) => {
                        add(x.binding, State::Available(x.value), guard)
                    }
                    Operation::ReceiveValue(x) => {
                        add(x.receiver, State::Available(x.result), guard)
                    }
                    Operation::MoveValue(x) => match x.source {
                        MoveSource::Binding(binding) => add(binding, State::Moved(last), guard),
                        MoveSource::Place(place) => {
                            let place =
                                &p.objects.places[p.objects.evaluated_places[place.0 as usize]
                                    .definition
                                    .0 as usize];
                            if place.projections.is_empty() {
                                if let PlaceRoot::Binding(binding) = place.root {
                                    add(binding, State::Moved(last), guard);
                                }
                            }
                        }
                        _ => {}
                    },
                    Operation::ParametricTransfer(x) => {
                        let place = &p.objects.places
                            [p.objects.evaluated_places[x.source.0 as usize].definition.0 as usize];
                        if place.projections.is_empty() {
                            if let PlaceRoot::Binding(binding) = place.root {
                                add(
                                    binding,
                                    State::Moved(last),
                                    guard.and(&predicates[x.copies.0 as usize].not()),
                                );
                            }
                        }
                    }
                    Operation::Assign(x) => {
                        let place = &p.objects.places
                            [p.objects.evaluated_places[x.target.0 as usize].definition.0 as usize];
                        if place.projections.is_empty() {
                            if let PlaceRoot::Binding(binding) = place.root {
                                add(binding, State::Available(x.value), guard);
                            }
                        }
                    }
                    Operation::ExitScope(x) => {
                        let scope = p.scopes.exits[x.exit.0 as usize].scope;
                        // Body termination is a lifetime boundary, not a reaching
                        // definition propagated to a subsequent call instance.
                        // Its cleanup is checked by the lifecycle consumers.
                        if scope != body.scope {
                            for binding in &p.scopes.entries[scope.0 as usize].bindings {
                                add(*binding, State::Destroyed(last), guard.clone());
                            }
                        }
                    }
                    _ => {}
                }
            }
        }
        for ((_, binding), changes) in &result.changes {
            for (_, condition) in changes {
                result
                    .relevant_conditions
                    .entry(*binding)
                    .or_default()
                    .extend(condition.support());
            }
        }
        result
    }
    pub fn path(&self, from: ExecutionMomentId, to: ExecutionMomentId, guard: &Guard) -> bool {
        let key = (from, to, guard.clone());
        if let Some(found) = self.paths.borrow().get(&key) {
            return *found;
        }
        let result = self.compute_path(from, to, guard, None);
        self.paths.borrow_mut().insert(key, result);
        result
    }
    pub fn path_in_occurrence(
        &self,
        origin: ExecutionMomentId,
        from: ExecutionMomentId,
        to: ExecutionMomentId,
        guard: &Guard,
    ) -> bool {
        let key = (origin, from, to, guard.clone());
        if let Some(answer) = self.occurrence_paths.borrow().get(&key) {
            return *answer;
        }
        let answer = self.compute_path(from, to, guard, Some(origin));
        self.occurrence_paths.borrow_mut().insert(key, answer);
        answer
    }
    fn ancestors_of(&self, target: ExecutionMomentId) -> Rc<HashMap<ExecutionMomentId, u32>> {
        if let Some(ancestors) = self.ancestors.borrow().get(&target) {
            return ancestors.clone();
        }
        let mut ancestors = HashMap::new();
        let mut pending = VecDeque::from([(target, 0)]);
        while let Some((moment, distance)) = pending.pop_front() {
            if let std::collections::hash_map::Entry::Vacant(entry) = ancestors.entry(moment) {
                entry.insert(distance);
                pending.extend(
                    self.predecessors
                        .get(&moment)
                        .into_iter()
                        .flatten()
                        .map(|(previous, _, _)| (*previous, distance + 1)),
                );
            }
        }
        let ancestors = Rc::new(ancestors);
        self.ancestors
            .borrow_mut()
            .insert(target, ancestors.clone());
        ancestors
    }
    fn compute_path(
        &self,
        from: ExecutionMomentId,
        to: ExecutionMomentId,
        guard: &Guard,
        origin: Option<ExecutionMomentId>,
    ) -> bool {
        if self.bodies[from.0 as usize] != self.bodies[to.0 as usize] {
            return false;
        }
        let ancestors = self.ancestors_of(to);
        if !ancestors.contains_key(&from) {
            return false;
        }
        let mut queue = vec![(from, guard.clone())];
        let mut seen: HashMap<_, Guard> = HashMap::new();
        while let Some((at, g)) = queue.pop() {
            if at == to && g.possible() {
                return true;
            }
            let old = seen.entry(at).or_default();
            if g.implies(old) {
                continue;
            }
            *old = old.or(&g);
            let mut successors = self
                .edges
                .get(&at)
                .into_iter()
                .flatten()
                .filter(|(next, _, _)| ancestors.contains_key(next))
                .collect::<Vec<_>>();
            successors.sort_by_key(|(next, _, _)| std::cmp::Reverse(ancestors[next]));
            for (next, path, back) in successors {
                if origin.is_some_and(|origin| {
                    self.iteration_backedges
                        .get(&(at, *next))
                        .is_some_and(|region| {
                            self.iteration_regions
                                .get(&origin)
                                .is_some_and(|regions| regions.contains(region))
                        })
                }) {
                    continue;
                }
                if !ancestors.contains_key(next) {
                    continue;
                }
                let g = g.and(path);
                if g.possible() {
                    queue.push((*next, if *back { Guard::yes() } else { g }));
                }
            }
        }
        false
    }
    pub fn predicate(&self, id: PredicateId) -> Guard {
        self.predicates[id.0 as usize].clone()
    }
    /// Guarded reaching definitions for one binding. Walking predecessors stops
    /// at the first applicable update on each path; cyclic paths use a worklist.
    pub fn binding_states(&self, binding: BindingId, at: ExecutionMomentId) -> BindingStates {
        if let Some(states) = self.states.borrow().get(&(binding, at)) {
            return states.clone();
        }
        let relevant = self
            .relevant_conditions
            .get(&binding)
            .cloned()
            .unwrap_or_default();
        let mut projected: HashMap<Guard, Guard> = HashMap::new();
        let mut project = |guard: Guard| {
            projected
                .entry(guard.clone())
                .or_insert_with(|| guard.project(&relevant))
                .clone()
        };
        let forget = |guard: Guard, forgotten: &[Atom]| {
            if forgotten.is_empty() {
                return guard;
            }
            let forgotten = forgotten.iter().cloned().collect::<HashSet<_>>();
            let keep = guard
                .support()
                .difference(&forgotten)
                .cloned()
                .collect::<HashSet<_>>();
            guard.project(&keep)
        };
        let mut answer: BindingStates = BTreeMap::new();
        let mut seen: HashMap<(ExecutionMomentId, Vec<Atom>), Guard> = HashMap::new();
        let mut pending = VecDeque::from([(at, Guard::yes(), Vec::<Atom>::new())]);
        while let Some((moment, guard, forgotten)) = pending.pop_front() {
            let old = seen.entry((moment, forgotten.clone())).or_default();
            if guard.implies(old) {
                continue;
            }
            *old = old.or(&guard);
            if self.entries.contains(&moment) {
                let state = self
                    .initial
                    .get(&(self.bodies[moment.0 as usize], binding))
                    .cloned()
                    .unwrap_or(State::Uninitialized);
                let old = answer.entry(state).or_default();
                *old = old.or(&forget(guard.clone(), &forgotten));
            }
            for (previous, edge_guard, back) in self.predecessors.get(&moment).into_iter().flatten()
            {
                let mut next_forgotten = forgotten.clone();
                if let Some(local) = self.loop_exit_atoms.get(&moment) {
                    next_forgotten.extend(local.iter().cloned());
                    next_forgotten.sort();
                    next_forgotten.dedup();
                }
                let mut remaining = guard.and(&project(edge_guard.clone()));
                if *back && remaining.possible() {
                    remaining = Guard::yes();
                }
                remaining = remaining.and(&project(
                    self.reachable.get(previous).cloned().unwrap_or_default(),
                ));
                for (state, condition) in self
                    .changes
                    .get(&(*previous, binding))
                    .into_iter()
                    .flatten()
                {
                    let active = remaining.and(condition);
                    if active.possible() {
                        let old = answer.entry(state.clone()).or_default();
                        *old = old.or(&forget(active, &next_forgotten));
                    }
                    remaining = remaining.and(&condition.not());
                }
                if remaining.possible() {
                    pending.push_back((*previous, remaining, next_forgotten));
                }
            }
        }
        self.states
            .borrow_mut()
            .insert((binding, at), answer.clone());
        answer
    }
    pub fn values(&self, binding: BindingId, at: ExecutionMomentId) -> Vec<ValueId> {
        self.binding_states(binding, at)
            .into_iter()
            .filter_map(|(state, guard)| match state {
                State::Available(value) if guard.possible() => Some(value),
                _ => None,
            })
            .collect()
    }
}
impl Flow {
    /// A required completion must dominate each surviving path, not merely be
    /// reachable on some path. Barrier guards retain success/failure distinctions.
    pub fn path_avoiding(
        &self,
        from: ExecutionMomentId,
        to: ExecutionMomentId,
        guard: &Guard,
        barriers: &HashMap<ExecutionMomentId, Guard>,
    ) -> bool {
        if self.bodies[from.0 as usize] != self.bodies[to.0 as usize] {
            return false;
        }
        let ancestors = self.ancestors_of(to);
        if !ancestors.contains_key(&from) {
            return false;
        }
        let mut queue = VecDeque::from([(from, guard.clone(), false)]);
        let mut seen: HashMap<_, Guard> = HashMap::new();
        while let Some((at, mut g, later_occurrence)) = queue.pop_front() {
            if !later_occurrence {
                if let Some(stop) = barriers.get(&at) {
                    g = g.and(&stop.not());
                }
            }
            if !g.possible() {
                continue;
            }
            if at == to {
                return true;
            }
            let old = seen.entry((at, later_occurrence)).or_default();
            if g.implies(old) {
                continue;
            }
            *old = old.or(&g);
            for (next, path, back) in self.edges.get(&at).into_iter().flatten() {
                if !ancestors.contains_key(next) {
                    continue;
                }
                let g = g.and(path);
                if g.possible() {
                    let later_occurrence = later_occurrence
                        || self
                            .iteration_backedges
                            .get(&(at, *next))
                            .is_some_and(|region| {
                                self.iteration_regions
                                    .get(&from)
                                    .is_some_and(|regions| regions.contains(region))
                            });
                    queue.push_back((
                        *next,
                        if *back { Guard::yes() } else { g },
                        later_occurrence,
                    ));
                }
            }
        }
        false
    }
}
