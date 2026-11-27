//! Final backend handoff construction.
//!
//! This pass consumes a physically planned program and only packages facts
//! that were already resolved by semantic analysis, rule verification and
//! memory planning. It does not inspect source syntax or resolve names/types.

use crate::{memory_plan, post_ast::*};
use std::collections::HashSet;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LoweringPreparationError {
    InvalidMemoryPlan(String),
    MissingEntryBody(FunctionInstanceId),
    MissingLayout(TypeId),
    MissingAsyncSlotValue { body: BodyId, binding: BindingId },
    MissingRuntimeBinding(IntrinsicId),
}

pub fn prepare(planned: PlannedPostAst) -> Result<LoweringReadyPostAst, Vec<LoweringPreparationError>> {
    let mut errors = memory_plan::validate(&planned)
        .err()
        .unwrap_or_default()
        .into_iter()
        .map(|error| LoweringPreparationError::InvalidMemoryPlan(error.0))
        .collect::<Vec<_>>();
    let post = &planned.checked_flow.semantics.semantics.post_ast;
    if let Some(entry) = post.entry_point {
        if post.declarations.instances[entry.0 as usize].body.is_none() {
            errors.push(LoweringPreparationError::MissingEntryBody(entry));
        }
    }
    let used_intrinsics = post
        .bodies
        .iter()
        .flat_map(|body| &body.operations)
        .filter_map(|operation| match operation {
            Operation::IntrinsicCall(call) => Some(call.target),
            _ => None,
        })
        .collect::<HashSet<_>>();
    let runtime = RuntimeBindings { entries: vec![] };
    for intrinsic in used_intrinsics {
        if !runtime.entries.iter().any(|entry| entry.intrinsic == intrinsic) {
            errors.push(LoweringPreparationError::MissingRuntimeBinding(intrinsic));
        }
    }

    if !errors.is_empty() {
        return Err(errors);
    }
    let reachable_functions = reachable_functions(post);
    Ok(LoweringReadyPostAst {
        foreign: planned.foreign.clone(),
        async_states: planned.async_states.clone(),
        runtime,
        reachable_functions,
        planned,
    })
}

fn reachable_functions(post: &PostAst) -> Vec<FunctionInstanceId> {
    let Some(entry) = post.entry_point else { return vec![]; };
    let mut pending = vec![entry];
    let mut seen = HashSet::new();
    while let Some(function) = pending.pop() {
        if !seen.insert(function) { continue; }
        let Some(body) = post.declarations.instances[function.0 as usize].body else { continue; };
        for operation in &post.bodies[body.0 as usize].operations {
            match operation {
                Operation::DirectCall(call) => pending.push(call.target),
                Operation::ExternalCall(call) => pending.push(call.target.function),
                Operation::MethodCall(call) => if let MethodTarget::Concrete(target) = call.target.target { pending.push(target); },
                Operation::CreateFuture(future) => pending.push(future.function),
                Operation::AwaitValue(awaited) => if let AwaitProtocol::GeneratedFuture { function, .. } = awaited.protocol.protocol { pending.push(function); },
                Operation::CreateClosure(closure) => if let Some(target) = post.contracts.captures[closure.captures.0 as usize].call { pending.push(target); },
                Operation::NativeOperation(native) => match native.kind {
                    NativeOperationKind::FunctionItem(target) => pending.push(target),
                    NativeOperationKind::RuntimeLaunch { function, .. } => pending.push(function),
                    _ => {}
                },
                Operation::DiscardResult(drop) | Operation::DropValue(DropValue { destructor: drop, .. }) => {
                    let destructor = match operation { Operation::DiscardResult(value) => value.destructor, Operation::DropValue(value) => value.destructor, _ => unreachable!() };
                    pending.push(post.contracts.destructors[destructor.0 as usize].hook);
                }
                _ => {}
            }
        }
    }
    let mut result = seen.into_iter().collect::<Vec<_>>();
    result.sort_by_key(|function| function.0);
    result
}
