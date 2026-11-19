//! Plan storage for verified fixed values and follow address-bearing identities.

use crate::{
    Error,
    tree::BindingId,
    verify::{Expr, Function, Instr, Structure, Ty, Value, ValueProvenance},
};
use std::{
    collections::{BTreeMap, BTreeSet, HashMap, HashSet, VecDeque},
    rc::Rc,
};

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
enum Origin {
    Fresh(usize),
    Parameter(usize),
}

#[derive(Default, Debug, PartialEq, Eq)]
struct Contract {
    fresh: bool,
    parameters: BTreeSet<usize>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Destination {
    Slot { slot: usize, scope: Option<(usize, u8)> },
    Caller(usize),
    FrameResult,
}

#[derive(Debug)]
pub(crate) struct Reservation {
    pub(crate) slot: usize,
    pub(crate) ty: Ty,
    pub(crate) width: usize,
}

#[derive(Debug, Default)]
pub(crate) struct FunctionPlacement {
    pub(crate) regions: crate::regions::RegionPlan,
    pub(crate) caller_slots: usize,
    summaries: PlacementSummaries,
    pub(crate) before: BTreeMap<usize, Vec<Reservation>>,
    pub(crate) parameters: Vec<(BindingId, Ty)>,
    pub(crate) asynchronous: bool,
    pub(crate) frame_values: BTreeMap<usize, Ty>,
    pub(crate) frame_binding_aliases: BTreeSet<usize>,
    // The backend persists all of these across polls; liveness can narrow the set later.
    pub(crate) frame_temps: BTreeMap<usize, (Ty, bool)>,
    pub(crate) frame_receivers: Vec<Value>,
    pub(crate) suspension_sites: Vec<usize>,
    pub(crate) frame_scope_sites: Vec<usize>,
    pub(crate) value_aliases: HashMap<usize, ValueDestination>,
    pub(crate) pool_initializers: HashMap<usize, Vec<(usize, Value)>>,
    pub(crate) values_before: BTreeMap<usize, Vec<ValueReservation>>,
}

type StorageOrigins = HashMap<usize, BTreeSet<Origin>>;

#[derive(Debug, Default)]
struct PlacementSummaries {
    origins: StorageOrigins,
    destinations: HashMap<usize, Destination>,
}

impl FunctionPlacement {
    pub(crate) fn construction_destination(&self, value: Value) -> Option<Destination> {
        self.summaries.destinations.get(&value.temp).copied()
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub(crate) enum ValueDestination {
    Caller,
    Receiver(usize),
}

#[derive(Debug)]
pub(crate) enum ValueReservation {
    Binding(BindingId, Ty, Option<BindingStorage>),
    Receiver(Value),
    CallResult(Value),
}

#[derive(Clone, Copy, Debug)]
pub(crate) enum BindingStorage {
    Caller,
    Binding(BindingId),
    Receiver(usize),
    CallResult(usize),
}

impl ValueReservation {
    pub(crate) fn storage(&self, placement: &FunctionPlacement) -> Option<Ty> {
        match self {
            Self::Binding(_, ty, storage) => storage.is_none().then_some(*ty),
            Self::Receiver(value) | Self::CallResult(value) => {
                (!placement.value_aliases.contains_key(&value.temp)
                    && !(placement.asynchronous && value.ty.scalar().is_some()))
                    .then_some(value.ty)
            }
        }
    }
}

#[derive(Debug)]
pub(crate) enum FootprintStep {
    Reserve(Ty, usize),
    Scope(Vec<FootprintStep>),
    Branch([Vec<FootprintStep>; 2]),
    Loop(Vec<FootprintStep>),
    Grow(Ty, usize),
    MapGrow(Ty),
    Thread(usize),
    Call(usize),
}

#[derive(Debug)]
pub(crate) struct Footprint {
    pub(crate) entry: usize,
    pub(crate) order: Vec<usize>,
    pub(crate) steps: Rc<Vec<Vec<FootprintStep>>>,
}

#[derive(Debug)]
pub(crate) struct Placement {
    pub(crate) functions: Vec<FunctionPlacement>,
    pub(crate) footprint: Option<Footprint>,
    pub(crate) worker_footprints: BTreeMap<usize, Footprint>,
}

#[derive(Clone, Debug)]
struct Site {
    instruction: usize,
    ancestors: Vec<(usize, u8)>,
}

impl Site {
    fn dominates(&self, other: &Self) -> bool {
        self.instruction < other.instruction && other.ancestors.starts_with(&self.ancestors)
    }

    fn exclusive(&self, other: &Self) -> bool {
        self.ancestors
            .iter()
            .zip(&other.ancestors)
            .find(|(left, right)| left != right)
            .is_some_and(|(left, right)| left.0 == right.0)
    }

    fn common(&self, other: &Self) -> Self {
        let shared = self
            .ancestors
            .iter()
            .zip(&other.ancestors)
            .take_while(|(a, b)| a == b)
            .count();
        let left = self
            .ancestors
            .get(shared)
            .map(|entry| entry.0)
            .unwrap_or(self.instruction);
        let right = other
            .ancestors
            .get(shared)
            .map(|entry| entry.0)
            .unwrap_or(other.instruction);
        Self {
            instruction: left.min(right),
            ancestors: self.ancestors[..shared].to_vec(),
        }
    }
}

struct Inventory<'a> {
    instructions: Vec<(&'a Instr, Site)>,
    bindings: HashMap<BindingId, Value>,
    parameters: HashMap<BindingId, usize>,
    receives: BTreeMap<usize, Vec<usize>>,
    reserve_sites: BTreeMap<usize, Site>,
}

impl<'a> Inventory<'a> {
    fn new(function: &'a Function) -> Self {
        let mut inventory = Self {
            instructions: vec![],
            bindings: HashMap::new(),
            parameters: function
                .parameters
                .iter()
                .enumerate()
                .map(|(index, (id, _))| (*id, index))
                .collect(),
            receives: BTreeMap::new(),
            reserve_sites: BTreeMap::new(),
        };
        inventory.visit(&function.body, &mut vec![]);
        inventory
    }

    fn visit(&mut self, body: &'a [Instr], ancestors: &mut Vec<(usize, u8)>) {
        for instruction in body {
            let index = self.instructions.len();
            let site = Site {
                instruction: index,
                ancestors: ancestors.clone(),
            };
            self.instructions.push((instruction, site.clone()));
            match instruction {
                Instr::Bind(binding, value) if aggregate(*value) => {
                    self.bindings.insert(*binding, *value);
                }
                Instr::Receive(receiver, value) | Instr::Break(Some((receiver, value)))
                    if aggregate(*value) =>
                {
                    let source = match receiver.provenance {
                        ValueProvenance::Received(source) => {
                            debug_assert_eq!(source, value.temp);
                            source
                        }
                        ValueProvenance::Merged => value.temp,
                        _ => unreachable!("a receiver must record its provenance"),
                    };
                    self.receives.entry(receiver.temp).or_default().push(source);
                }
                Instr::Reserve(value) => {
                    self.reserve_sites.insert(value.temp, site);
                }
                Instr::If(_, yes, no) => {
                    ancestors.push((index, 0));
                    self.visit(yes, ancestors);
                    ancestors.pop();
                    ancestors.push((index, 1));
                    self.visit(no, ancestors);
                    ancestors.pop();
                }
                Instr::Block(body) => {
                    ancestors.push((index, 0));
                    self.visit(body, ancestors);
                    ancestors.pop();
                }
                Instr::Loop {
                    condition, body, ..
                } => {
                    ancestors.push((index, 0));
                    self.visit(condition, ancestors);
                    self.visit(body, ancestors);
                    ancestors.pop();
                }
                _ => {}
            }
        }
    }

    fn origins(&self, contracts: &[Contract]) -> StorageOrigins {
        let mut origins = StorageOrigins::new();
        let mut consumers = HashMap::<usize, Vec<usize>>::new();
        for &(instruction, _) in &self.instructions {
            let Instr::Evaluate(value, expr) = instruction else {
                continue;
            };
            if !aggregate(*value) {
                continue;
            }
            let entry = origins.entry(value.temp).or_default();
            match expr {
                Expr::Construct(_)
                | Expr::Variant(..) | Expr::ProcessArgs
                | Expr::Array(..)
                | Expr::Pool
                | Expr::MapNew
                | Expr::Await(..)
                | Expr::AwaitHandle(..)
                | Expr::TakeVariantField(..)
                | Expr::TakeTupleField(..)
                | Expr::NativeJoin(..)
                | Expr::MapInsert(..)
                | Expr::MapGet(..)
                | Expr::MapRemove(..)
                | Expr::PoolTake(..)
                | Expr::VectorExtract(..) => {
                    entry.insert(Origin::Fresh(value.temp));
                }
                Expr::Local(_) => {
                    let (ValueProvenance::LocalRead(binding)
                    | ValueProvenance::LocalMove { binding, .. }) = value.provenance else {
                        unreachable!("a local evaluation must record its binding");
                    };
                    if let Some(source) = self.bindings.get(&binding) {
                        consumers.entry(source.temp).or_default().push(value.temp);
                    } else if let Some(&parameter) = self.parameters.get(&binding) {
                        entry.insert(Origin::Parameter(parameter));
                    }
                }
                Expr::Call(function, args, _) => {
                    let contract = &contracts[*function];
                    if contract.fresh {
                        entry.insert(Origin::Fresh(value.temp));
                    }
                    for &index in &contract.parameters {
                        consumers.entry(args[index].temp).or_default().push(value.temp);
                    }
                }
                _ => {}
            }
        }

        for (&receiver, sources) in &self.receives {
            origins.entry(receiver).or_default();
            for &source in sources {
                consumers.entry(source).or_default().push(receiver);
            }
        }

        // Propagate each new fact once across each edge. A receiver can reuse
        // the origins already reduced at the source, even across nested scopes.
        let mut pending = origins
            .iter()
            .flat_map(|(&temp, roots)| roots.iter().map(move |&root| (temp, root)))
            .collect::<VecDeque<_>>();
        while let Some((temp, root)) = pending.pop_front() {
            for &consumer in consumers.get(&temp).into_iter().flatten() {
                if origins.entry(consumer).or_default().insert(root) {
                    pending.push_back((consumer, root));
                }
            }
        }
        origins
    }

    fn returns(&self, origins: &StorageOrigins) -> BTreeSet<Origin> {
        self.instructions
            .iter()
            .filter_map(|(instruction, _)| match instruction {
                Instr::Return(Some(value)) if aggregate(*value) => origins.get(&value.temp),
                _ => None,
            })
            .flatten()
            .copied()
            .collect()
    }
}

fn aggregate(value: Value) -> bool {
    matches!(value.ty, Ty::Struct(_))
}

pub(crate) fn plan(functions: &[Function], layouts: &[Structure], region_size: Option<u64>) -> Result<Placement, Error> {
    let inventories = functions.iter().map(Inventory::new).collect::<Vec<_>>();
    let mut contracts = functions
        .iter()
        .map(|_| Contract::default())
        .collect::<Vec<_>>();
    let summaries = loop {
        let summaries = inventories
            .iter()
            .map(|inventory| inventory.origins(&contracts))
            .collect::<Vec<_>>();
        let next = inventories
            .iter()
            .zip(&summaries)
            .map(|(inventory, summary)| {
                let mut contract = Contract::default();
                for origin in inventory.returns(summary) {
                    match origin {
                        Origin::Fresh(_) => contract.fresh = true,
                        Origin::Parameter(index) => {
                            contract.parameters.insert(index);
                        }
                    }
                }
                contract
            })
            .collect::<Vec<_>>();
        if next == contracts {
            break summaries;
        }
        contracts = next;
    };
    let mut placements = functions
        .iter()
        .zip(&inventories)
        .zip(summaries)
        .map(|((function, inventory), origins)| place_function(function, inventory, origins))
        .collect::<Vec<_>>();
    dimension(&inventories, &mut placements)?;
    for (placement, regions) in placements.iter_mut().zip(crate::regions::plan(functions, layouts, region_size)) {
        placement.regions = regions;
    }
    let (footprint, worker_footprints) = footprints(functions, &placements);
    Ok(Placement {
        functions: placements,
        footprint,
        worker_footprints,
    })
}

fn footprints(
    functions: &[Function],
    placements: &[FunctionPlacement],
) -> (Option<Footprint>, BTreeMap<usize, Footprint>) {
    let mut calls = vec![Vec::new(); functions.len()];
    let steps = Rc::new(
        functions
            .iter()
            .zip(placements)
            .zip(&mut calls)
            .map(|((function, placement), calls)| {
                let mut steps = placement
                    .parameters
                    .iter()
                    .map(|&(_, ty)| FootprintStep::Reserve(ty, 1))
                    .collect::<Vec<_>>();
                steps.extend(footprint_body(&function.body, placement, &mut 0, calls));
                steps
            })
            .collect(),
    );
    let footprint = |entry| {
        Some(Footprint {
            entry,
            order: footprint_order(entry, &calls)?,
            steps: Rc::clone(&steps),
        })
    };
    let main = functions
        .iter()
        .position(|function| function.entry)
        .and_then(footprint);
    let workers = functions
        .iter()
        .enumerate()
        .filter(|(_, function)| function.native || function.asynchronous)
        .filter_map(|(index, _)| footprint(index).map(|bound| (index, bound)))
        .collect();
    (main, workers)
}

pub(crate) fn footprint_order(entry: usize, calls: &[Vec<usize>]) -> Option<Vec<usize>> {
    // Postorder over the reachable call graph. A reachable cycle lacks a
    // finite call-depth proof, so use the runtime default for this program.
    let mut states = vec![0; calls.len()];
    let mut pending = vec![(entry, false)];
    let mut order = Vec::new();
    while let Some((function, expanded)) = pending.pop() {
        if expanded {
            states[function] = 2;
            order.push(function);
            continue;
        }
        match states[function] {
            2 => continue,
            1 => return None,
            _ => {}
        }
        states[function] = 1;
        pending.push((function, true));
        pending.extend(calls[function].iter().map(|&callee| (callee, false)));
    }
    Some(order)
}

fn footprint_body(
    body: &[Instr],
    placement: &FunctionPlacement,
    instruction: &mut usize,
    calls: &mut Vec<usize>,
) -> Vec<FootprintStep> {
    let mut steps = Vec::new();
    for item in body {
        let index = *instruction;
        *instruction += 1;
        steps.extend(
            placement
                .before
                .get(&index)
                .into_iter()
                .flatten()
                .map(|reservation| FootprintStep::Reserve(reservation.ty, reservation.width)),
        );
        steps.extend(
            placement
                .values_before
                .get(&index)
                .into_iter()
                .flatten()
                .filter_map(|reservation| reservation.storage(placement))
                .map(|ty| FootprintStep::Reserve(ty, 1)),
        );
        match item {
            Instr::Evaluate(_, Expr::Call(callee, _, _)) | Instr::Call(callee, _) => {
                steps.push(FootprintStep::Call(*callee));
                calls.push(*callee);
            }
            Instr::Block(nested) => {
                steps.push(FootprintStep::Scope(footprint_body(
                    nested,
                    placement,
                    instruction,
                    calls,
                )));
            }
            Instr::If(_, yes, no) => {
                steps.push(FootprintStep::Branch([
                    footprint_body(yes, placement, instruction, calls),
                    footprint_body(no, placement, instruction, calls),
                ]));
            }
            Instr::Loop {
                condition, body, ..
            } => {
                let mut iteration = footprint_body(condition, placement, instruction, calls);
                iteration.extend(footprint_body(body, placement, instruction, calls));
                steps.push(FootprintStep::Loop(iteration));
            }
            Instr::Evaluate(_, Expr::FutureNew(function, _)) => {
                steps.push(FootprintStep::Thread(*function))
            }
            Instr::Evaluate(_, Expr::NativeStart(worker, _, _)) => {
                steps.push(FootprintStep::Thread(*worker))
            }
            Instr::Evaluate(_, Expr::MapInsert(_, _, value)) => {
                steps.push(FootprintStep::MapGrow(value.ty))
            }
            Instr::GrowingPush(_, value) => steps.push(FootprintStep::Grow(value.ty, 1)),
            Instr::GrowingText(_, bytes) => steps.push(FootprintStep::Grow(Ty::U8, bytes.len())),
            _ => {}
        }
    }
    steps
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum GrowthUnit {
    Element(Ty),
    MapEntry(Ty),
    ThreadFrame(usize),
}

pub(crate) fn region_growth(footprint: &Footprint) -> Option<Vec<(GrowthUnit, usize)>> {
    let mut bounds = vec![Some(Vec::new()); footprint.steps.len()];
    for &index in &footprint.order {
        bounds[index] = growth_steps(&footprint.steps[index], &bounds);
    }
    bounds[footprint.entry].take()
}

fn growth_steps(
    steps: &[FootprintStep],
    bounds: &[Option<Vec<(GrowthUnit, usize)>>],
) -> Option<Vec<(GrowthUnit, usize)>> {
    let mut result = Vec::<(GrowthUnit, usize)>::new();
    for step in steps {
        let growth = match step {
            FootprintStep::Reserve(..) => continue,
            FootprintStep::Call(index) => bounds[*index].clone()?,
            FootprintStep::Scope(steps) => growth_steps(steps, bounds)?,
            FootprintStep::Branch([left, right]) => {
                let mut growth = growth_steps(left, bounds)?;
                for (unit, count) in growth_steps(right, bounds)? {
                    if let Some((_, previous)) = growth.iter_mut().find(|(existing, _)| *existing == unit) {
                        *previous = (*previous).max(count);
                    } else {
                        growth.push((unit, count));
                    }
                }
                growth
            }
            FootprintStep::Loop(steps) => {
                let iteration = growth_steps(steps, bounds)?;
                if iteration.iter().any(|(unit, _)| !matches!(unit, GrowthUnit::ThreadFrame(_))) {
                    return None;
                }
                iteration
            }
            FootprintStep::Thread(worker) => vec![(GrowthUnit::ThreadFrame(*worker), 1)],
            FootprintStep::MapGrow(ty) => vec![(GrowthUnit::MapEntry(*ty), 1)],
            FootprintStep::Grow(ty, count) => vec![(GrowthUnit::Element(*ty), *count)],
        };
        for (unit, count) in growth {
            if count == 0 {
                continue;
            }
            if let Some((_, previous)) = result.iter_mut().find(|(existing, _)| *existing == unit) {
                *previous = previous.checked_add(count)?;
            } else {
                result.push((unit, count));
            }
        }
    }
    Some(result)
}

fn final_value_destination(
    mut destination: ValueDestination,
    aliases: &HashMap<usize, ValueDestination>,
) -> ValueDestination {
    while let ValueDestination::Receiver(temp) = destination {
        let Some(&next) = aliases.get(&temp) else { break };
        destination = next;
    }
    destination
}

fn scalar_binding_storage(
    inventory: &Inventory<'_>,
    call_results: &BTreeSet<usize>,
    aliases: &mut HashMap<usize, ValueDestination>,
    has_caller_slot: bool,
) -> HashMap<BindingId, BindingStorage> {
    let mut storage = HashMap::new();
    let mut local_bindings = HashMap::new();
    let mut moves = HashMap::<BindingId, Vec<usize>>::new();
    let mut call_sites = HashMap::new();
    let mut reassigned = HashSet::new();
    for &(instruction, ref site) in &inventory.instructions {
        match instruction {
            Instr::Bind(binding, value) if value.ty.scalar().is_some() => {
                if value.receiver {
                    storage.insert(*binding, BindingStorage::Receiver(value.temp));
                } else if call_results.contains(&value.temp) {
                    storage.insert(*binding, BindingStorage::CallResult(value.temp));
                }
                local_bindings.insert(*binding, (*value, site));
            }
            Instr::Write(binding, _) => {
                reassigned.insert(*binding);
            }
            Instr::Assembly(block) => {
                reassigned.extend(block.operands.iter().filter(|op| op.written).map(|op| op.binding));
            }
            Instr::Evaluate(value, _) if value.ty.scalar().is_some() => {
                if call_results.contains(&value.temp) {
                    call_sites.insert(value.temp, site);
                }
                if let ValueProvenance::LocalMove { binding, .. } = value.provenance {
                    moves.entry(binding).or_default().push(value.temp);
                }
            }
            _ => {}
        }
    }

    let mut transfers = HashMap::<BindingId, Vec<(usize, ValueDestination)>>::new();
    let mut incoming = HashMap::<usize, usize>::new();
    let mut sources = Vec::new();
    for &(instruction, _) in &inventory.instructions {
        let (destination, value) = match instruction {
            Instr::Receive(receiver, value) | Instr::Break(Some((receiver, value))) => {
                *incoming.entry(receiver.temp).or_default() += 1;
                (ValueDestination::Receiver(receiver.temp), value)
            }
            Instr::Return(Some(value)) if has_caller_slot => (ValueDestination::Caller, value),
            _ => continue,
        };
        if value.ty.scalar().is_some()
            && let ValueProvenance::LocalMove { binding, .. } = value.provenance
        {
            let transfers = transfers.entry(binding).or_default();
            if transfers.is_empty() {
                sources.push(binding);
            }
            transfers.push((value.temp, destination));
        }
    }

    let mut promoted = HashMap::<ValueDestination, Vec<&Site>>::new();
    // Outer consumers appear after their sources. Resolve their aliases before
    // considering an inner receiver that feeds them.
    for binding in sources.into_iter().rev() {
        let outgoing = &transfers[&binding];
        if reassigned.contains(&binding) || moves[&binding].len() != outgoing.len() {
            continue;
        }
        let destinations = outgoing.iter()
            .map(|&(_, target)| final_value_destination(target, aliases))
            .collect::<HashSet<_>>();
        let mut redirects = Vec::new();
        let destination = if destinations.len() == 1 {
            *destinations.iter().next().unwrap()
        } else {
            // A shared address must be visible to every receiver. The caller
            // slot is visible throughout the function.
            let Some(destination) = destinations.iter().copied().find(|&candidate| {
                destinations.iter().all(|&other| match (candidate, other) {
                    (left, right) if left == right => true,
                    (ValueDestination::Caller, _) => true,
                    (ValueDestination::Receiver(left), ValueDestination::Receiver(right)) => {
                        inventory.reserve_sites[&left].dominates(&inventory.reserve_sites[&right])
                    }
                    (_, ValueDestination::Caller) => false,
                })
            }) else {
                continue;
            };
            // A receiver with an independent incoming value may already use
            // its slot before this transfer.
            for &(_, target) in outgoing {
                if let ValueDestination::Receiver(temp) = target
                    && final_value_destination(target, aliases) != destination
                    && incoming.get(&temp) == Some(&1)
                    && !aliases.contains_key(&temp)
                {
                    redirects.push(temp);
                }
            }
            if destinations.len() != redirects.len() + 1 {
                continue;
            }
            destination
        };
        let mut chain = Vec::new();
        let mut current = binding;
        while let Some(&(initial, binding_site)) = local_bindings.get(&current) {
            let construction_site = if initial.receiver {
                &inventory.reserve_sites[&initial.temp]
            } else {
                call_sites.get(&initial.temp).copied().unwrap_or(binding_site)
            };
            if let ValueDestination::Receiver(receiver) = destination
                && !inventory.reserve_sites[&receiver].dominates(construction_site)
            {
                break;
            }
            chain.push((current, initial, construction_site));
            let ValueProvenance::LocalMove { binding: source, .. } = initial.provenance else {
                break;
            };
            if reassigned.contains(&source)
                || moves.get(&source).is_none_or(|moves| moves.as_slice() != [initial.temp])
            {
                break;
            }
            current = source;
        }
        let Some(&(_, _, construction_site)) = chain.last() else {
            continue;
        };
        let previous = promoted.entry(destination).or_default();
        if !previous.iter().all(|site| site.exclusive(construction_site)) {
            continue;
        }
        previous.push(construction_site);
        for temp in redirects {
            aliases.insert(temp, destination);
        }
        for (binding, initial, _) in chain {
            if storage.contains_key(&binding) {
                aliases.insert(initial.temp, destination);
            } else {
                let location = match destination {
                    ValueDestination::Caller => BindingStorage::Caller,
                    ValueDestination::Receiver(temp) => BindingStorage::Receiver(temp),
                };
                storage.insert(binding, location);
            }
        }
    }

    // If no outer reservation is available, a moved scalar can keep its
    // existing address while the source's storage scope still encloses it.
    for &(instruction, ref site) in &inventory.instructions {
        let Instr::Bind(binding, value) = instruction else { continue };
        let ValueProvenance::LocalMove { binding: source, .. } = value.provenance else {
            continue;
        };
        if !storage.contains_key(binding)
            && !reassigned.contains(&source)
            && moves.get(&source).is_some_and(|moves| moves.as_slice() == [value.temp])
            && local_bindings.get(&source).is_some_and(|(_, source_site)| source_site.dominates(site))
        {
            storage.insert(*binding, BindingStorage::Binding(source));
        }
    }
    storage
}

fn place_function(
    function: &Function,
    inventory: &Inventory<'_>,
    origins: StorageOrigins,
) -> FunctionPlacement {
    // A fresh literal immediately consumed by PoolNew has no observable
    // intermediate address. Its inputs have already been evaluated.
    let pool_initializers = inventory.instructions.windows(2).filter_map(|pair| {
        match (pair[0].0, pair[1].0) {
            (Instr::Evaluate(value, Expr::Construct(fields)),
             Instr::Evaluate(_, Expr::PoolNew(_, init, 0)))
                if value.temp == init.temp => Some((value.temp, fields.clone())),
            _ => None,
        }
    }).collect::<HashMap<_, _>>();
    let mut slots = BTreeMap::<usize, (Ty, Site)>::new();
    for &(instruction, ref site) in &inventory.instructions {
        if let Instr::Evaluate(value, _) = instruction
            && origins
                .get(&value.temp)
                .is_some_and(|origins| origins.contains(&Origin::Fresh(value.temp)))
        {
            if !pool_initializers.contains_key(&value.temp) {
                slots.insert(value.temp, (value.ty, site.clone()));
            }
        }
    }
    let mut placement = FunctionPlacement {
        asynchronous: function.asynchronous,
        pool_initializers,
        parameters: function
            .parameters
            .iter()
            .copied()
            .filter(|(_, ty)| !function.asynchronous && !matches!(ty, Ty::Struct(_)))
            .collect(),
        summaries: PlacementSummaries {
            origins,
            ..PlacementSummaries::default()
        },
        ..FunctionPlacement::default()
    };
    if function.asynchronous {
        for &(instruction, ref site) in &inventory.instructions {
            match instruction {
                Instr::Evaluate(value, expr) => {
                    if matches!(expr, Expr::Await(_) | Expr::AwaitHandle(_) | Expr::SocketWait(..) | Expr::SocketCompletion(..)) {
                        placement.suspension_sites.push(site.instruction);
                    }
                    if value.ty != Ty::Void && !placement.pool_initializers.contains_key(&value.temp) {
                        placement
                            .frame_temps
                            .insert(value.temp, (value.ty, expr.reads_aggregate_place()));
                    }
                }
                Instr::Reserve(value) => {
                    placement.frame_receivers.push(*value);
                }
                Instr::Yield => placement.suspension_sites.push(site.instruction),
                Instr::Block(_) | Instr::If(..) | Instr::Loop { .. } => {
                    placement.frame_scope_sites.push(site.instruction);
                }
                _ => {}
            }
        }
        placement.frame_values.extend(
            function
                .parameters
                .iter()
                .map(|(binding, ty)| (binding.0, *ty)),
        );
    }
    let call_results = inventory
        .instructions
        .iter()
        .filter_map(|&(instruction, _)| match instruction {
            Instr::Evaluate(value, Expr::Call(..)) => Some(value.temp),
            Instr::Evaluate(value, Expr::Await(_)) if value.ty.scalar().is_some() => Some(value.temp),
            _ => None,
        })
        .collect::<BTreeSet<_>>();
    let is_slot =
        |value: Value| !aggregate(value) && (value.receiver || call_results.contains(&value.temp));
    for &(instruction, _) in &inventory.instructions {
        match instruction {
            Instr::Receive(receiver, value) | Instr::Break(Some((receiver, value)))
                if is_slot(*value) =>
            {
                placement
                    .value_aliases
                    .insert(value.temp, ValueDestination::Receiver(receiver.temp));
            }
            Instr::Return(Some(value))
                if !function.entry && is_slot(*value) && (!function.asynchronous || value.ty.scalar().is_some()) =>
            {
                placement
                    .value_aliases
                    .insert(value.temp, ValueDestination::Caller);
            }
            _ => {}
        }
    }
    let mut scalar_bindings = scalar_binding_storage(
        inventory,
        &call_results,
        &mut placement.value_aliases,
        !function.entry,
    );
    for &(instruction, ref site) in &inventory.instructions {
        let reservation = match instruction {
            Instr::Bind(binding, value) if function.asynchronous => {
                placement.frame_values.insert(binding.0, value.ty);
                let Some(storage) = scalar_bindings.remove(binding) else { continue };
                placement.frame_binding_aliases.insert(binding.0);
                ValueReservation::Binding(*binding, value.ty, Some(storage))
            }
            Instr::Bind(binding, value) if !aggregate(*value) => {
                ValueReservation::Binding(*binding, value.ty, scalar_bindings.remove(binding))
            }
            Instr::Reserve(value) if !aggregate(*value) => ValueReservation::Receiver(*value),
            Instr::Evaluate(value, _) if !aggregate(*value) && call_results.contains(&value.temp) => {
                ValueReservation::CallResult(*value)
            }
            _ => continue,
        };
        placement
            .values_before
            .entry(site.instruction)
            .or_default()
            .push(reservation);
    }
    if slots.is_empty() {
        return placement;
    }

    let origins = &placement.summaries.origins;
    for &(instruction, ref site) in &inventory.instructions {
        let receiver_site = match instruction {
            Instr::Receive(receiver, _) | Instr::Break(Some((receiver, _))) => {
                inventory.reserve_sites.get(&receiver.temp)
            }
            _ => None,
        };
        let values = match instruction {
            Instr::Evaluate(value, _)
            | Instr::Bind(_, value)
            | Instr::Discard(value)
            | Instr::Reserve(value)
            | Instr::Return(Some(value))
            | Instr::Receive(_, value)
            | Instr::Break(Some((_, value))) => Some(*value),
            _ => None,
        };
        if let Some(value) = values.filter(|&value| aggregate(value)) {
            for origin in origins.get(&value.temp).into_iter().flatten() {
                if let Origin::Fresh(temp) = origin {
                    if let Some((_, location)) = slots.get_mut(temp) {
                        *location = location.common(receiver_site.unwrap_or(site));
                    }
                }
            }
        }
    }

    let fresh = slots.keys().copied().collect::<BTreeSet<_>>();
    let mut conflicts = BTreeSet::new();
    coexists(&function.body, &fresh, BTreeSet::new(), &mut conflicts);
    let returned = inventory
        .returns(origins)
        .into_iter()
        .filter_map(|origin| match origin {
            Origin::Fresh(temp) => Some(temp),
            _ => None,
        })
        .collect::<BTreeSet<_>>();
    let mut caller_groups = Vec::<BTreeSet<usize>>::new();
    for &temp in &returned {
        // A synchronous callee can require several contiguous caller slots.
        // A Future has a single result object in its frame.
        if function.asynchronous && call_results.contains(&temp) {
            continue;
        }
        let candidate = BTreeSet::from([temp]);
        if let Some(group) = caller_groups
            .iter_mut()
            .find(|group| exclusive(group, &candidate, &conflicts))
        {
            group.insert(temp);
        } else if !function.asynchronous || caller_groups.is_empty() {
            caller_groups.push(candidate);
        }
    }
    let placed_results = caller_groups.iter().flatten().copied().collect::<BTreeSet<_>>();
    if !function.asynchronous {
        placement.caller_slots = caller_groups.len();
    }
    for (group, temps) in caller_groups.iter().enumerate() {
        let destination = if function.asynchronous {
            Destination::FrameResult
        } else {
            Destination::Caller(group)
        };
        for &temp in temps {
            placement.summaries.destinations.insert(temp, destination);
        }
    }

    let mut groups = fresh
        .difference(&placed_results)
        .map(|&temp| BTreeSet::from([temp]))
        .collect::<Vec<_>>();
    let mut candidates_by_receiver = Vec::new();
    let mut scope_values = BTreeMap::<_, BTreeSet<usize>>::new();
    for &receiver in inventory.receives.keys() {
        let candidates = origins
            .get(&receiver)
            .into_iter()
            .flatten()
            .filter_map(|origin| match origin {
                Origin::Fresh(temp) if !placed_results.contains(temp) => Some(*temp),
                _ => None,
            })
            .collect::<BTreeSet<_>>();
        if candidates.len() < 2 {
            continue;
        }
        let common = candidates.iter().map(|temp| slots[temp].1.clone())
            .reduce(|left, right| left.common(&right)).unwrap();
        let scope = common.ancestors.last().copied();
        scope_values.entry(scope).or_default().extend(&candidates);
        candidates_by_receiver.push((scope, receiver, candidates));
    }
    // Allocate sharing opportunities first in the scopes with the most
    // eligible values. Keep the already selected groups intact.
    candidates_by_receiver.sort_by_key(|(scope, receiver, _)| {
        (std::cmp::Reverse(scope_values[scope].len()), *receiver)
    });
    for (_, _, candidates) in candidates_by_receiver {
        let mut selected = Vec::new();
        let mut combined = BTreeSet::new();
        for (index, group) in groups.iter().enumerate() {
            if group.is_subset(&candidates) && exclusive(&combined, group, &conflicts) {
                selected.push(index);
                combined.extend(group);
            }
        }
        if selected.len() < 2 {
            continue;
        }
        for index in selected.into_iter().rev() {
            groups.remove(index);
        }
        groups.push(combined);
    }

    for group in groups {
        let slot = *group.first().unwrap();
        let (ty, mut site) = slots[&slot].clone();
        for &temp in &group {
            debug_assert_eq!(ty, slots[&temp].0);
            site = site.common(&slots[&temp].1);
        }
        let destination = Destination::Slot {
            slot,
            scope: site.ancestors.last().copied(),
        };
        for temp in group {
            placement.summaries.destinations.insert(temp, destination);
        }
        placement
            .before
            .entry(site.instruction)
            .or_default()
            .push(Reservation { slot, ty, width: 0 });
    }
    placement
}

fn dimension(
    inventories: &[Inventory<'_>],
    functions: &mut [FunctionPlacement],
) -> Result<(), Error> {
    let producers = inventories
        .iter()
        .map(|inventory| {
            inventory
                .instructions
                .iter()
                .filter_map(|(instruction, _)| match instruction {
                    Instr::Evaluate(
                        value,
                        Expr::Construct(_)
                        | Expr::Variant(..) | Expr::ProcessArgs
                        | Expr::Array(..)
                        | Expr::Pool
                        | Expr::MapNew
                        | Expr::Await(..)
                        | Expr::AwaitHandle(..)
                        | Expr::TakeVariantField(..)
                        | Expr::TakeTupleField(..)
                        | Expr::NativeJoin(..)
                        | Expr::MapInsert(..)
                        | Expr::MapGet(..)
                        | Expr::MapRemove(..)
                        | Expr::PoolTake(..)
                        | Expr::VectorExtract(..),
                    ) => Some((value.temp, None)),
                    Instr::Evaluate(value, Expr::Call(callee, _, _)) if aggregate(*value) => {
                        Some((value.temp, Some(*callee)))
                    }
                    _ => None,
                })
                .collect::<HashMap<_, _>>()
        })
        .collect::<Vec<_>>();
    let width = |producer: Option<usize>, capacities: &[usize]| {
        producer.map_or(1, |callee| capacities[callee])
    };
    let mut capacities = vec![0; functions.len()];
    let mut output_widths = Vec::new();
    // A finite maximum can be attained on a dependency path without
    // repeating a function. A strictly increasing recursive requirement
    // cannot be assigned a fixed set of caller slots.
    for round in 0..=functions.len() {
        output_widths = functions
            .iter()
            .zip(&producers)
            .map(|(function, producers)| {
                let mut groups = vec![0; function.caller_slots];
                for (&temp, destination) in &function.summaries.destinations {
                    if let Destination::Caller(index) = *destination {
                        groups[index] = groups[index].max(width(producers[&temp], &capacities));
                    }
                }
                groups
            })
            .collect();
        let next = output_widths
            .iter()
            .map(|groups| {
                groups
                    .iter()
                    .try_fold(0usize, |sum, &width| sum.checked_add(width))
            })
            .collect::<Option<Vec<_>>>()
            .ok_or_else(|| Error::new(0, "taille des emplacements de retour hors limites"))?;
        if next == capacities {
            break;
        }
        if round == functions.len() {
            return Err(Error::new(
                0,
                "nombre d’emplacements de retour récursifs non borné",
            ));
        }
        capacities = next;
    }
    for (index, function) in functions.iter_mut().enumerate() {
        let mut offset = 0;
        let offsets = output_widths[index]
            .iter()
            .map(|&width| {
                let base = offset;
                offset += width;
                base
            })
            .collect::<Vec<_>>();
        let mut slots = HashMap::<usize, usize>::new();
        for (&temp, destination) in &mut function.summaries.destinations {
            match destination {
                Destination::Caller(group) => *group = offsets[*group],
                Destination::FrameResult => {},
                Destination::Slot { slot, .. } => {
                    let size = slots.entry(*slot).or_default();
                    *size = (*size).max(width(producers[index][&temp], &capacities));
                }
            }
        }
        for reservation in function.before.values_mut().flatten() {
            reservation.width = slots[&reservation.slot];
        }
        function.caller_slots = capacities[index];
    }
    Ok(())
}

fn exclusive(
    left: &BTreeSet<usize>,
    right: &BTreeSet<usize>,
    conflicts: &BTreeSet<(usize, usize)>,
) -> bool {
    left.iter().all(|&a| {
        right
            .iter()
            .all(|&b| a == b || !conflicts.contains(&(a.min(b), a.max(b))))
    })
}

fn coexists(
    body: &[Instr],
    fresh: &BTreeSet<usize>,
    mut seen: BTreeSet<usize>,
    conflicts: &mut BTreeSet<(usize, usize)>,
) -> Option<BTreeSet<usize>> {
    for instruction in body {
        match instruction {
            Instr::Evaluate(value, _) if fresh.contains(&value.temp) => {
                conflicts.extend(
                    seen.iter()
                        .map(|&other| (other.min(value.temp), other.max(value.temp))),
                );
                seen.insert(value.temp);
            }
            Instr::Block(nested) => seen = coexists(nested, fresh, seen, conflicts)?,
            Instr::If(_, yes, no) => {
                let yes = coexists(yes, fresh, seen.clone(), conflicts);
                let no = coexists(no, fresh, seen, conflicts);
                if yes.is_none() && no.is_none() {
                    return None;
                }
                seen = yes.into_iter().chain(no).flatten().collect();
            }
            Instr::Loop {
                condition, body, ..
            } => {
                // Producers from distinct iterations may coexist. Include every
                // producer in a loop when comparing it to other producers there.
                let mut loop_fresh = BTreeSet::new();
                collect_fresh(condition, fresh, &mut loop_fresh);
                collect_fresh(body, fresh, &mut loop_fresh);
                for &temp in &loop_fresh {
                    conflicts.extend(
                        seen.iter()
                            .chain(&loop_fresh)
                            .map(|&other| (other.min(temp), other.max(temp))),
                    );
                }
                seen.extend(loop_fresh);
            }
            Instr::Return(_) | Instr::Break(_) | Instr::Continue => return None,
            _ => {}
        }
    }
    Some(seen)
}

fn collect_fresh(body: &[Instr], fresh: &BTreeSet<usize>, out: &mut BTreeSet<usize>) {
    for instruction in body {
        match instruction {
            Instr::Evaluate(value, _) if fresh.contains(&value.temp) => {
                out.insert(value.temp);
            }
            Instr::If(_, yes, no) => {
                collect_fresh(yes, fresh, out);
                collect_fresh(no, fresh, out);
            }
            Instr::Block(body) => collect_fresh(body, fresh, out),
            Instr::Loop {
                condition, body, ..
            } => {
                collect_fresh(condition, fresh, out);
                collect_fresh(body, fresh, out);
            }
            _ => {}
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        frontend,
        parser::Mode,
        verify::{Position, verify},
    };

    #[test]
    fn reuses_summaries_after_nested_receives() {
        let source = r#"
            struct Boite { nombre: A<i64> }
            fn main() {
                let mut nombres = pool<i64>(1);
                let recu = {
                    { let boite = Boite { nombre: nombres.new(7) }; boite }
                };
                drop(recu);
            }
        "#;
        let tree = frontend(source, Mode::Program).unwrap();
        let program = verify(source, &tree).unwrap();
        let inventory = Inventory::new(&program.functions[0]);
        let binding = |name| {
            BindingId(tree.bindings.iter().position(|b| b.name == name).unwrap())
        };
        let boite = inventory.bindings[&binding("boite")];
        let recu = inventory.bindings[&binding("recu")];
        let local_move = inventory
            .instructions
            .iter()
            .find_map(|(instruction, _)| match instruction {
                Instr::Evaluate(value, Expr::Local(id)) if *id == binding("boite") => Some(*value),
                _ => None,
            })
            .unwrap();
        assert!(matches!(
            local_move.provenance,
            ValueProvenance::LocalMove { binding: id, .. } if id == binding("boite")
        ));
        let ValueProvenance::Received(inner) = recu.provenance else {
            panic!("recu should link to the inner receiver");
        };
        assert_eq!(inventory.receives[&inner], [local_move.temp]);
        assert_eq!(recu.dependencies, boite.dependencies);
        assert_eq!(recu.dependencies, local_move.dependencies);
        let origins = program.dependency_summaries.origins(recu.dependencies.loan);
        assert_eq!(origins.len(), 1);
        assert_eq!(origins[0].root, binding("nombres"));
        assert!(origins[0].pool);
        assert_eq!(
            program.dependency_summaries.path(origins[0].at),
            [Position::Field(0)]
        );

        let placement = &program.placement.functions[0];
        let roots = &placement.summaries.origins;
        assert_eq!(roots[&recu.temp], BTreeSet::from([Origin::Fresh(boite.temp)]));
        assert_eq!(roots[&recu.temp], roots[&inner]);
        assert!(matches!(
            placement.construction_destination(boite),
            Some(Destination::Slot { scope: None, .. })
        ));
    }

    #[test]
    fn retains_all_sources_at_a_branch_join() {
        let source = r#"
            struct Boite { nombre: A<i64> }
            fn main() {
                let mut a = pool<i64>(1);
                let mut b = pool<i64>(1);
                let recu = if true {
                    Boite { nombre: a.new(7) }
                } else {
                    Boite { nombre: b.new(8) }
                };
                drop(recu);
            }
        "#;
        let tree = frontend(source, Mode::Program).unwrap();
        let program = verify(source, &tree).unwrap();
        let inventory = Inventory::new(&program.functions[0]);
        let binding = |name| {
            BindingId(tree.bindings.iter().position(|b| b.name == name).unwrap())
        };
        let recu = inventory.bindings[&binding("recu")];
        assert_eq!(recu.provenance, ValueProvenance::Merged);
        assert_eq!(inventory.receives[&recu.temp].len(), 2);
        let origins = program.dependency_summaries.origins(recu.dependencies.loan);
        assert_eq!(
            origins.iter().map(|origin| origin.root.0).collect::<BTreeSet<_>>(),
            BTreeSet::from([binding("a").0, binding("b").0])
        );
        let summaries = &program.placement.functions[0].summaries;
        let roots = &summaries.origins[&recu.temp];
        assert_eq!(roots.len(), 2);
        let mut destinations = roots.iter().map(|origin| match origin {
            Origin::Fresh(temp) => summaries.destinations[temp],
            Origin::Parameter(_) => panic!("the branch constructs its result"),
        });
        assert_eq!(destinations.next(), destinations.next());
    }
}
