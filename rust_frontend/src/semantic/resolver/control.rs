//! Resolved branch joins distinguish value-producing paths from terminating paths.
use super::*;
impl Resolver<'_> {
    pub(super) fn unwind_exits(
        &mut self,
        site: &OperationSite,
        kind: ScopeExitKind,
        stop: Option<ScopeId>,
    ) -> (ScopeExitId, Vec<ScopeExitId>) {
        let mut scope = self.ctx().scope;
        let mut exits = vec![];
        loop {
            if Some(scope) == stop
                || !matches!(
                    self.p.scopes.entries[scope.0 as usize].storage,
                    ScopeStorageLink::Runtime(_)
                )
            {
                break;
            }
            exits.push(self.scope_exit(scope, site, kind.clone()));
            let Some(parent) = self.p.scopes.entries[scope.0 as usize].lexical_parent else {
                break;
            };
            scope = parent;
        }
        (exits[0], exits[1..].to_vec())
    }
    pub(super) fn diverged(&mut self, at: ExecutionMomentId) -> Expr {
        let value = self.value(
            self.never,
            ValueDefinition::Diverged { at },
            ProvenanceKind::Diverged(at),
            vec![],
        );
        Expr { value }
    }
    pub(super) fn merge_values(
        &mut self,
        site: OperationSite,
        incoming: NonEmpty<GuardedValue>,
    ) -> Result<ValueId> {
        let ty = self.vtype(incoming.first.value);
        for value in &incoming.rest {
            self.require_type(self.ctx().instruction, self.vtype(value.value), ty)?;
        }
        let result = self.op_value(&site, ty, vec![]);
        let provenance = self.p.values.entries[result.0 as usize].provenance;
        self.p.values.provenance[provenance.0 as usize].kind =
            ProvenanceKind::Merge(incoming.clone());
        let summary = self.p.values.entries[result.0 as usize].dependencies;
        for value in std::iter::once(&incoming.first).chain(&incoming.rest) {
            for mut dependency in self.guarded_dependencies(value.value, value.guard) {
                dependency.guard =
                    self.predicate(PredicateKind::All(vec![value.guard, dependency.guard]));
                self.p.values.dependency_summaries[summary.0 as usize]
                    .guarded
                    .push(dependency);
            }
        }
        let reference_inputs = std::iter::once(&incoming.first)
            .chain(&incoming.rest)
            .cloned()
            .collect::<Vec<_>>();
        self.merge_reference_identities(result, &reference_inputs, &site);
        self.emit(Operation::MergeValue(MergeValue {
            site,
            incoming,
            result,
        }));
        Ok(result)
    }
    pub(super) fn accumulate_context(&mut self, source: &Context) {
        for value in &source.returns {
            if !self
                .ctx()
                .returns
                .iter()
                .any(|v| v.value == value.value && v.guard == value.guard)
            {
                self.ctx_mut().returns.push(value.clone());
            }
        }
        for (index, source) in source.loops.iter().enumerate() {
            for result in &source.results {
                if !self.ctx().loops[index]
                    .results
                    .iter()
                    .any(|v| v.value == result.value && v.guard == result.guard)
                {
                    self.ctx_mut().loops[index].results.push(result.clone());
                }
            }
            for transfer in &source.breaks {
                if !self.ctx().loops[index]
                    .breaks
                    .iter()
                    .any(|v| v.at == transfer.at)
                {
                    self.ctx_mut().loops[index].breaks.push(transfer.clone());
                }
            }
            for transfer in &source.continues {
                if !self.ctx().loops[index]
                    .continues
                    .iter()
                    .any(|v| v.at == transfer.at)
                {
                    self.ctx_mut().loops[index].continues.push(transfer.clone());
                }
            }
        }
    }
    pub(super) fn conditional_expression(
        &mut self,
        n: ast::NodeId,
        condition: ValueId,
        yes: BranchOperand,
        no: BranchOperand,
        expected: Option<TypeId>,
        short: Option<bool>,
    ) -> Result<Expr> {
        let expected = expected
            .or_else(|| match yes {
                BranchOperand::Syntax(node) => self.known_type(node),
                _ => None,
            })
            .or_else(|| match no {
                BranchOperand::Syntax(node) => self.known_type(node),
                _ => None,
            });
        let site = self.site(n, ExecutionPhase::Compute);
        let parent = self.ctx().clone();
        let positive = self.predicate(PredicateKind::Boolean {
            value: condition,
            expected: true,
        });
        let negative = self.predicate(PredicateKind::Boolean {
            value: condition,
            expected: false,
        });
        let yes_guard = self.predicate(PredicateKind::All(vec![parent.guard, positive]));
        let no_guard = self.predicate(PredicateKind::All(vec![parent.guard, negative]));
        self.ctx = Some(self.branch_context(&parent, site.id, yes_guard));
        let yes_branch = self.ctx().branch;
        let yes_first = ExecutionMomentId(self.p.execution.execution_moments.len() as u32);
        let yes_value = self.branch_operand(n, yes, expected)?;
        let yes_context = self.ctx().clone();
        let yes_end = yes_context.last.unwrap();
        self.p.execution.timelines[yes_context.timeline.0 as usize]
            .exits
            .push(yes_end);
        self.p
            .execution
            .edges
            .push(ExecutionEdge::Conditional(ConditionalEdge {
                from: site.execution_moments.first,
                to: yes_first,
                guard: yes_guard,
            }));
        self.ctx = Some(self.branch_context(&parent, site.id, no_guard));
        let no_branch = self.ctx().branch;
        let no_first = ExecutionMomentId(self.p.execution.execution_moments.len() as u32);
        let hint = if self.vtype(yes_value) == self.never {
            expected
        } else {
            Some(self.vtype(yes_value))
        };
        let no_value = self.branch_operand(n, no, hint)?;
        let no_context = self.ctx().clone();
        let no_end = no_context.last.unwrap();
        self.p.execution.timelines[no_context.timeline.0 as usize]
            .exits
            .push(no_end);
        self.p
            .execution
            .edges
            .push(ExecutionEdge::Conditional(ConditionalEdge {
                from: site.execution_moments.first,
                to: no_first,
                guard: no_guard,
            }));
        self.ctx = Some(Context {
            last: None,
            ..parent.clone()
        });
        self.accumulate_context(&yes_context);
        self.accumulate_context(&no_context);
        self.p
            .execution
            .relationships
            .push(BranchRelationship::Exclusive(ExclusiveBranches {
                decision: site.id,
                branches: NonEmpty {
                    first: yes_branch,
                    rest: vec![no_branch],
                },
            }));
        let mut live = vec![];
        if self.vtype(yes_value) != self.never {
            // A nested return, break or other divergence may narrow the paths
            // that actually leave this branch. The resolved exit guard, not
            // the branch-entry guard, is the semantic fact handed to the merge.
            live.push((yes_context.guard, yes_value, yes_end, &yes_context));
        }
        if self.vtype(no_value) != self.never {
            live.push((no_context.guard, no_value, no_end, &no_context));
        }
        if live.is_empty() {
            self.emit(Operation::IfDecision(IfDecision {
                site: site.clone(),
                condition,
                yes: yes_branch,
                no: no_branch,
                merge: None,
            }));
            self.ctx_mut().last = Some(site.execution_moments.first);
            return Ok(self.diverged(site.execution_moments.first));
        }
        let continuation_guard = self.predicate(PredicateKind::Any(
            live.iter().map(|(guard, _, _, _)| *guard).collect(),
        ));
        self.ctx_mut().guard = continuation_guard;
        let merge_site = self.site(n, ExecutionPhase::Receive);
        let merge = merge_site.execution_moments.first;
        let moments = live
            .iter()
            .map(|(guard, _, moment, _)| GuardedMoment {
                guard: *guard,
                moment: *moment,
            })
            .collect::<Vec<_>>();
        self.p
            .execution
            .relationships
            .push(BranchRelationship::Merge(BranchMerge {
                incoming: NonEmpty {
                    first: moments[0].clone(),
                    rest: moments[1..].to_vec(),
                },
                continuation: merge,
            }));
        for (guard, _, from, _) in &live {
            self.p
                .execution
                .edges
                .push(ExecutionEdge::Conditional(ConditionalEdge {
                    from: *from,
                    to: merge,
                    guard: *guard,
                }));
        }
        let values = live
            .iter()
            .map(|(guard, value, _, _)| GuardedValue {
                guard: *guard,
                value: *value,
            })
            .collect::<Vec<_>>();
        let result = self.merge_values(
            merge_site,
            NonEmpty {
                first: values[0].clone(),
                rest: values[1..].to_vec(),
            },
        )?;
        if let Some(expected) = expected {
            self.require_type(n, self.vtype(result), expected)?;
        }
        match short {
            Some(true) => self.emit(Operation::ShortCircuitAnd(ShortCircuitAnd {
                site,
                left: condition,
                conditional_right: yes_branch,
                result,
                merge,
            })),
            Some(false) => self.emit(Operation::ShortCircuitOr(ShortCircuitOr {
                site,
                left: condition,
                conditional_right: no_branch,
                result,
                merge,
            })),
            None => self.emit(Operation::IfDecision(IfDecision {
                site,
                condition,
                yes: yes_branch,
                no: no_branch,
                merge: Some(merge),
            })),
        }
        for (binding, before) in parent.bindings {
            let values = live
                .iter()
                .map(|(guard, _, _, ctx)| GuardedValue {
                    guard: *guard,
                    value: ctx.bindings.get(&binding).copied().unwrap_or(before),
                })
                .collect::<Vec<_>>();
            let first = values[0].value;
            let value = if values.iter().all(|v| v.value == first) {
                first
            } else {
                let site = self.site(n, ExecutionPhase::Receive);
                self.merge_values(
                    site,
                    NonEmpty {
                        first: values[0].clone(),
                        rest: values[1..].to_vec(),
                    },
                )?
            };
            self.ctx_mut().bindings.insert(binding, value);
        }
        Ok(Expr { value: result })
    }
}
