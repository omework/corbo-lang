//! Bound simultaneous region acquisitions in the verified post-AST.

use crate::{
    tree::BindingId,
    verify::{Expr, Function, Instr, Structure, Ty},
};
use std::collections::{HashMap, HashSet};

#[derive(Debug, Default)]
pub(crate) struct RegionPlan {
    pub(crate) slots: usize,
    pub(crate) scope_slots: HashMap<usize, usize>,
    pub(crate) dedicated: HashSet<usize>,
}

#[derive(Clone, Copy, Default)]
struct Demand {
    peak: usize,
    live: usize,
    received: bool,
    escapes: bool,
    breaks: bool,
    separate: bool,
}

impl Demand {
    fn retained(self) -> usize {
        if self.received || self.escapes || self.breaks {
            self.live
        } else {
            0
        }
    }

    fn append(&mut self, nested: Self) {
        if !nested.separate {
            self.peak = self.peak.max(self.live.saturating_add(nested.peak));
            self.live = self.live.saturating_add(nested.retained());
        }
        self.escapes |= nested.escapes;
        self.breaks |= nested.breaks;
    }

    fn branch(left: Self, right: Self) -> Self {
        Self {
            peak: if left.separate { 0 } else { left.peak }.max(if right.separate {
                0
            } else {
                right.peak
            }),
            live: if left.separate { 0 } else { left.retained() }.max(if right.separate {
                0
            } else {
                right.retained()
            }),
            // Retention here refers to a transfer from either arm into the
            // enclosing scope. It need not escape that enclosing scope.
            received: true,
            escapes: left.escapes || right.escapes,
            breaks: left.breaks || right.breaks,
            separate: false,
        }
    }
}

fn acquisition(expr: &Expr) -> bool {
    matches!(
        expr,
        Expr::PoolGrowing(_) | Expr::MapNew | Expr::FutureNew(..) | Expr::NativeStart(..)
    )
}

fn carries_region(ty: Ty, layouts: &[Structure], seen: &mut HashSet<usize>) -> bool {
    match ty {
        Ty::Handle(..) | Ty::Future(_) => true,
        Ty::Allocation(target) => carries_region(target.ty(), layouts, seen),
        Ty::Struct(index) if seen.insert(index) => {
            let layout = &layouts[index];
            layout.growing.is_some()
                || layout
                    .array
                    .is_some_and(|(ty, len)| len != 0 && carries_region(ty, layouts, seen))
                || layout
                    .fields
                    .iter()
                    .chain(layout.variants.iter().flat_map(|(_, fields)| fields))
                    .any(|(_, ty)| carries_region(*ty, layouts, seen))
        }
        _ => false,
    }
}

fn walk(body: &[Instr], visit: &mut impl FnMut(&Instr)) {
    for instruction in body {
        visit(instruction);
        match instruction {
            Instr::Block(nested) => walk(nested, visit),
            Instr::If(_, yes, no) => {
                walk(yes, visit);
                walk(no, visit);
            }
            Instr::Loop {
                condition, body, ..
            } => {
                walk(condition, visit);
                walk(body, visit);
            }
            _ => {}
        }
    }
}

fn callee(instruction: &Instr) -> Option<usize> {
    match instruction {
        Instr::Evaluate(_, Expr::Call(index, _, _)) | Instr::Call(index, _) => Some(*index),
        _ => None,
    }
}

struct Analysis<'a> {
    layouts: &'a [Structure],
    summaries: &'a [Demand],
    plan: &'a mut RegionPlan,
    force_calls: &'a mut Vec<usize>,
    index: usize,
    select: bool,
}

impl Analysis<'_> {
    fn dedicated(&mut self, body: &[Instr]) {
        walk(body, &mut |instruction| {
            if let Instr::Evaluate(value, expr) = instruction
                && acquisition(expr)
            {
                self.plan.dedicated.insert(value.temp);
            }
            self.force_calls.extend(callee(instruction));
        });
    }

    fn block(
        &mut self,
        body: &[Instr],
        mut available: Option<usize>,
        mut limit: Option<u64>,
    ) -> Demand {
        let mut demand = Demand::default();
        let mut values = HashMap::new();
        let mut bindings = HashMap::<BindingId, usize>::new();
        let mut local = HashSet::new();
        let mut annotations = Vec::new();
        let regional = |ty| carries_region(ty, self.layouts, &mut HashSet::new());
        for instruction in body {
            let site = self.index;
            self.index += 1;
            match instruction {
                Instr::Evaluate(value, expr) if acquisition(expr) => {
                    if self.select && available.is_some_and(|limit| demand.live >= limit) {
                        self.plan.dedicated.insert(value.temp);
                    }
                    if !self.plan.dedicated.contains(&value.temp) {
                        values.insert(value.temp, value.temp);
                        local.insert(value.temp);
                        demand.live = demand.live.saturating_add(1);
                        demand.peak = demand.peak.max(demand.live);
                    }
                    if let Expr::NativeStart(_, captures, retained) = expr {
                        demand.escapes |=
                            *retained || captures.iter().any(|value| regional(value.ty));
                    }
                    if let Expr::FutureNew(_, captures) = expr {
                        demand.escapes |= captures.iter().any(|value| regional(value.ty));
                    }
                }
                Instr::Evaluate(value, Expr::Local(binding)) => {
                    if let Some(&source) = bindings.get(binding) {
                        values.insert(value.temp, source);
                    }
                }
                Instr::Bind(binding, value) => {
                    if let Some(&source) = values.get(&value.temp) {
                        bindings.insert(*binding, source);
                    }
                }
                Instr::Evaluate(value, Expr::FutureSpawn(future, _)) => {
                    demand.escapes = true;
                    if let Some(&source) = values.get(&future.temp) {
                        values.insert(value.temp, source);
                    }
                }
                Instr::DropAllocation(value)
                | Instr::DropMap(value)
                | Instr::Evaluate(
                    _,
                    Expr::Await(value) | Expr::AwaitHandle(value) | Expr::NativeJoin(value),
                ) => {
                    if let Some(source) = values.get(&value.temp)
                        && local.remove(source)
                    {
                        demand.live -= 1;
                    }
                }
                Instr::Receive(_, value) => demand.received |= regional(value.ty),
                Instr::Break(Some((_, value))) => demand.breaks |= regional(value.ty),
                Instr::Return(Some(value)) => demand.escapes |= regional(value.ty),
                Instr::GrowingPush(_, value) | Instr::Evaluate(_, Expr::PoolNew(_, value, _)) => {
                    demand.escapes |= regional(value.ty);
                }
                Instr::RegionScope { count, max_size } => {
                    annotations.push(site);
                    if *count != 0 || limit.is_some_and(|inherited| inherited != *max_size) {
                        available = (*count != 0)
                            .then(|| usize::try_from(*count).ok())
                            .flatten();
                        demand.separate = true;
                    }
                    limit = Some(*max_size);
                }
                Instr::Block(nested) => {
                    let nested = self.block(
                        nested,
                        available.map(|slots| slots.saturating_sub(demand.live)),
                        limit,
                    );
                    demand.append(nested);
                }
                Instr::If(_, yes, no) => {
                    let available = available.map(|limit| limit.saturating_sub(demand.live));
                    let left = self.block(yes, available, limit);
                    let right = self.block(no, available, limit);
                    demand.append(Demand::branch(left, right));
                }
                Instr::Loop {
                    condition, body, ..
                } => {
                    let available = available.map(|limit| limit.saturating_sub(demand.live));
                    let condition_demand = self.block(condition, available, limit);
                    let body_demand = self.block(
                        body,
                        available.map(|slots| slots.saturating_sub(condition_demand.live)),
                        limit,
                    );
                    let mut iteration = condition_demand;
                    // Condition temporaries can still be live in the body.
                    iteration.append(Demand {
                        received: true,
                        ..body_demand
                    });
                    if self.select && iteration.escapes && iteration.live != 0 {
                        self.dedicated(condition);
                        self.dedicated(body);
                    }
                    iteration.received = iteration.breaks;
                    iteration.breaks = false;
                    demand.append(iteration);
                }
                _ => {
                    if let Some(index) = callee(instruction) {
                        demand.append(self.summaries[index]);
                    }
                }
            }
        }
        for site in annotations {
            self.plan.scope_slots.insert(site, demand.peak);
        }
        demand
    }
}

pub(crate) fn plan(
    functions: &[Function],
    layouts: &[Structure],
    default_limit: Option<u64>,
) -> Vec<RegionPlan> {
    let mut calls = vec![Vec::new(); functions.len()];
    for (function, callees) in functions.iter().zip(&mut calls) {
        walk(&function.body, &mut |instruction| {
            callees.extend(callee(instruction))
        });
    }
    let mut force = recursive_reach(&calls);
    let recursive = force.clone();
    let mut ordered_calls = calls.clone();
    for &index in &recursive {
        ordered_calls[index].clear();
    }
    ordered_calls.push((0..functions.len()).collect());
    let order = crate::placement::footprint_order(functions.len(), &ordered_calls)
        .expect("recursive region sites were isolated");
    let mut plans = (0..functions.len())
        .map(|_| RegionPlan::default())
        .collect::<Vec<_>>();
    let mut forced = HashSet::new();
    for select in [true, false] {
        while let Some(index) = force.pop() {
            if forced.insert(index) {
                walk(&functions[index].body, &mut |instruction| {
                    if let Instr::Evaluate(value, expr) = instruction
                        && acquisition(expr)
                    {
                        plans[index].dedicated.insert(value.temp);
                    }
                });
                force.extend(&calls[index]);
            }
        }
        let mut summaries = vec![Demand::default(); functions.len()];
        for &index in &order[..order.len() - 1] {
            let mut analysis = Analysis {
                layouts,
                summaries: &summaries,
                plan: &mut plans[index],
                force_calls: &mut force,
                index: 0,
                select,
            };
            let function = &functions[index];
            let limit = if function.entry { default_limit } else { None };
            let mut demand = analysis.block(&function.body, None, limit);
            if select && demand.peak == usize::MAX {
                analysis.dedicated(&function.body);
            }
            // The return and adoption flags are the ways new regions can
            // remain in the caller's context. A Receive alone is local.
            demand.received = false;
            // Recursive code may retain a region passed by its caller.
            demand.escapes |= recursive.contains(&index);
            analysis.plan.slots = demand.peak;
            summaries[index] = demand;
        }
    }
    plans
}

// Every recursive cycle contains a DFS back edge. Allocations in that cycle
// and in its callees may be repeated at an unknown call depth.
fn recursive_reach(calls: &[Vec<usize>]) -> Vec<usize> {
    let mut states = vec![0; calls.len()];
    let mut recursive = Vec::new();
    for root in 0..calls.len() {
        if states[root] != 0 {
            continue;
        }
        let mut pending = vec![(root, false)];
        while let Some((index, exit)) = pending.pop() {
            if exit {
                states[index] = 2;
                continue;
            }
            match states[index] {
                2 => continue,
                1 => {
                    recursive.push(index);
                    continue;
                }
                _ => {}
            }
            states[index] = 1;
            pending.push((index, true));
            pending.extend(calls[index].iter().map(|&callee| (callee, false)));
        }
    }
    let mut reached = HashSet::new();
    let mut pending = recursive;
    while let Some(index) = pending.pop() {
        if reached.insert(index) {
            pending.extend(&calls[index]);
        }
    }
    reached.into_iter().collect()
}
