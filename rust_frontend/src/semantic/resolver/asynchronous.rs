//! Inactive future creation is distinct from polling and suspension/resumption.
use super::*;
impl Resolver<'_> {
    pub(super) fn resolve_async_frame(&mut self, function: FunctionInstanceId) -> Result<TypeId> {
        if let Some(frame) = self.p.async_frames.iter().find(|f| f.function == function) {
            return Ok(frame.state_type);
        }
        let body = self.p.declarations.instances[function.0 as usize]
            .body
            .unwrap();
        let source = self.functions[self.p.declarations.instances[function.0 as usize]
            .definition
            .0 as usize]
            .clone();
        let symbol = self.anonymous_symbol(
            "<async-state>",
            source.scope,
            SymbolDefinition::Type(self.unit),
            source.node,
        );
        let state_type = self.intern(TypeKey::Nominal(symbol, vec![]));
        self.p.symbols.entries[symbol.0 as usize].definition = SymbolDefinition::Type(state_type);
        let state_field = FieldId(self.p.declarations.fields.len() as u32);
        let state_symbol = self.anonymous_symbol(
            "<poll-state>",
            source.scope,
            SymbolDefinition::Field(state_field),
            source.node,
        );
        let state_discriminant_type = self.intern(TypeKey::Numeric(NumericType::U64));
        self.p.declarations.fields.push(FieldDefinition {
            id: state_field,
            symbol: state_symbol,
            ty: state_discriminant_type,
            default: FieldDefault::Unavailable,
        });
        // Conservative semantic storage set: every body-local binding is retained.
        // A later liveness analysis may remove slots; no physical layout is selected here.
        let bindings:Vec<_>=self.p.scopes.bindings.iter().filter(|b|
            matches!(self.p.scopes.entries[b.scope.0 as usize].context,ScopeContext::Body(b) if b==body)).cloned().collect();
        let mut slots = vec![];
        for binding in bindings {
            let field = FieldId(self.p.declarations.fields.len() as u32);
            let name = self.p.symbols.entries[binding.symbol.0 as usize]
                .spelling
                .clone();
            let symbol = self.anonymous_symbol(
                &name,
                source.scope,
                SymbolDefinition::Field(field),
                source.node,
            );
            self.p.declarations.fields.push(FieldDefinition {
                id: field,
                symbol,
                ty: binding.ty,
                default: FieldDefault::Unavailable,
            });
            slots.push(AsyncFrameSlot {
                binding: binding.id,
                field,
            });
        }
        self.p.declarations.structs.push(StructDefinition {
            symbol,
            ty: state_type,
            parameters: vec![],
            fields: std::iter::once(state_field)
                .chain(slots.iter().map(|s| s.field))
                .collect(),
            methods: vec![],
        });
        let suspensions = self
            .p
            .execution
            .suspensions
            .iter()
            .filter(|s| self.p.execution.execution_moments[s.suspend.0 as usize].body == body)
            .map(|s| s.id)
            .collect();
        self.p.async_frames.push(AsyncFrame {
            function,
            body,
            state_type,
            state_field,
            slots,
            suspensions,
        });
        Ok(state_type)
    }
    /// Resolved future identity is shared by creation, function-item signatures
    /// and explicit task type syntax. No inactive body is executed here.
    pub(super) fn future_type(&mut self, function: FunctionInstanceId) -> Result<TypeId> {
        let state = self.resolve_async_frame(function)?;
        let body = self.p.declarations.instances[function.0 as usize]
            .body
            .unwrap();
        let signature = self.p.declarations.instances[function.0 as usize].signature;
        let output = self.p.declarations.signatures[signature.0 as usize].result;
        if let Some(ty) = self
            .p
            .types
            .entries
            .iter()
            .find(|t| matches!(t.kind,TypeDefinition::Future{body:b,..}if b==body))
        {
            return Ok(ty.id);
        }
        let ty = TypeId(self.p.types.entries.len() as u32);
        self.p.types.entries.push(ResolvedType {
            id: ty,
            kind: TypeDefinition::Future {
                body,
                result: output,
                state,
            },
        });
        Ok(ty)
    }
    pub(super) fn make_future(
        &mut self,
        n: ast::NodeId,
        function: FunctionInstanceId,
        captures: Option<CaptureRecordId>,
        values: Vec<ValueId>,
    ) -> Result<Expr> {
        let ty = self.future_type(function)?;
        let body = self.p.declarations.instances[function.0 as usize]
            .body
            .unwrap();
        let mut components = values.clone();
        if let Some(record) = captures {
            components.extend(
                self.p.contracts.captures[record.0 as usize]
                    .captures
                    .iter()
                    .map(|c| c.value),
            );
        }
        let site = self.site(n, ExecutionPhase::Compute);
        let dependencies = components
            .iter()
            .flat_map(|v| self.dependencies(*v))
            .collect();
        let result = self.op_value(&site, ty, dependencies);
        self.components.insert(result, components);
        let arguments = values
            .iter()
            .enumerate()
            .map(|(index, value)| CallArgument {
                parameter_index: index as u32,
                value: *value,
                transfer: self.transfer_kind(self.vtype(*value)),
            })
            .collect();
        self.emit(Operation::CreateFuture(CreateFuture {
            site,
            captures,
            function,
            arguments,
            body,
            result,
        }));
        Ok(Expr { value: result })
    }
    pub(super) fn move_block_expression(
        &mut self,
        n: ast::NodeId,
        body: ast::NodeId,
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        let captures = self.capture_record(n, true, &[], body)?;
        let (scope, parent) = self.enter_runtime_scope(body)?;
        let site = self.site(n, ExecutionPhase::Receive);
        let ty = self.p.contracts.captures[captures.0 as usize].ty;
        let parts: Vec<_> = self.p.contracts.captures[captures.0 as usize]
            .captures
            .iter()
            .map(|c| c.value)
            .collect();
        let environment = self.op_value(
            &site,
            ty,
            parts.iter().flat_map(|v| self.dependencies(*v)).collect(),
        );
        self.components.insert(environment, parts);
        self.emit(Operation::EnterMoveBlock(EnterMoveBlock {
            site: site.clone(),
            scope,
            captures,
            environment,
        }));
        self.bind(
            n,
            &format!("<move-environment:{}>", scope.0),
            true,
            environment,
        )?;
        self.bind_capture_environment(captures, &site)?;
        let Some(result) = self.block_contents(body, expected)? else {
            let at = self.ctx().last.unwrap();
            self.ctx_mut().scope = parent;
            return Ok(self.diverged(at));
        };
        self.finish_runtime_scope(body, scope, parent, result)
    }
    pub(super) fn suspension(&mut self, site: &mut OperationSite) -> SuspensionId {
        let poll = site.execution_moments.first;
        let suspend = self.phase(site, ExecutionPhase::Suspend);
        let resume = self.phase(site, ExecutionPhase::Resume);
        let id = SuspensionId(self.p.execution.suspensions.len() as u32);
        let values = self.ctx().bindings.values().copied().collect();
        self.p.execution.suspensions.push(SuspensionPoint {
            id,
            suspend,
            resumptions: NonEmpty {
                first: GuardedMoment {
                    guard: site.guard,
                    moment: resume,
                },
                rest: vec![],
            },
            live_values: values,
            live_places: vec![],
            effects: self.p.declarations.instances[self.ctx().instance.0 as usize].effects,
        });
        // Remove fabricated unconditional poll -> suspend -> resume execution.
        self.p.execution.edges.retain(|edge|!matches!(edge,ExecutionEdge::Sequence(s)if (s.before==poll&&s.after==suspend)||(s.before==suspend&&s.after==resume)));
        self.p
            .execution
            .edges
            .push(ExecutionEdge::Suspend(SuspendEdge {
                from: suspend,
                point: id,
            }));
        self.p
            .execution
            .edges
            .push(ExecutionEdge::Resume(ResumeEdge {
                point: id,
                to: resume,
                guard: site.guard,
            }));
        id
    }
    pub(super) fn require_execution_context(
        &mut self,
        operation: OperationId,
        required: FunctionExecution,
    ) {
        let function = self.ctx().instance;
        let signature = self.p.declarations.instances[function.0 as usize].signature;
        let actual = self.p.declarations.signatures[signature.0 as usize]
            .execution
            .clone();
        self.p
            .obligations
            .execution_context
            .push(ExecutionContextRequirement {
                operation,
                function,
                actual,
                required,
            });
    }
    pub(super) fn yield_statement(&mut self, n: ast::NodeId) -> Result<()> {
        let mut site = self.site(n, ExecutionPhase::Invoke);
        self.require_execution_context(site.id, FunctionExecution::Asynchronous);
        let suspension = self.suspension(&mut site);
        self.p
            .execution
            .edges
            .push(ExecutionEdge::Sequence(SequenceEdge {
                before: site.execution_moments.first,
                after: self.p.execution.suspensions[suspension.0 as usize].suspend,
            }));
        self.emit(Operation::YieldExecution(YieldExecution {
            site,
            suspension,
        }));
        Ok(())
    }
    /// Shared ready/pending transition for Future polling and runtime waits.
    pub(super) fn poll_transition(
        &mut self,
        site: &mut OperationSite,
        ready: PredicateId,
    ) -> (SuspensionId, ExecutionMomentId) {
        let ready_guard = self.predicate(PredicateKind::All(vec![site.guard, ready]));
        let pending = self.predicate(PredicateKind::Not(ready));
        let pending_guard = self.predicate(PredicateKind::All(vec![site.guard, pending]));
        self.require_execution_context(site.id, FunctionExecution::Asynchronous);
        let suspension = self.suspension(site);
        let suspend = self.p.execution.suspensions[suspension.0 as usize].suspend;
        let resume = self.p.execution.suspensions[suspension.0 as usize]
            .resumptions
            .first
            .moment;
        self.ctx_mut().last = None;
        let received = self.phase(site, ExecutionPhase::Receive);
        self.p
            .execution
            .edges
            .push(ExecutionEdge::Conditional(ConditionalEdge {
                from: site.execution_moments.first,
                to: suspend,
                guard: pending_guard,
            }));
        self.p
            .execution
            .edges
            .push(ExecutionEdge::Conditional(ConditionalEdge {
                from: site.execution_moments.first,
                to: received,
                guard: ready_guard,
            }));
        self.p.execution.edges.push(ExecutionEdge::PollRetry {
            from: resume,
            poll: site.execution_moments.first,
            suspension,
        });
        (suspension, received)
    }
    pub(super) fn await_expression(&mut self, n: ast::NodeId, source: ast::NodeId) -> Result<Expr> {
        let source = self.expression(source, None)?.value;
        let (protocol, output, body, function) =
            match self.p.types.entries[self.vtype(source).0 as usize].kind {
                TypeDefinition::Future { body, result, .. } => {
                    let BodyOwner::Instance(function) = self.p.bodies[body.0 as usize].owner else {
                        unreachable!()
                    };
                    (
                        AwaitProtocol::GeneratedFuture { function, body },
                        result,
                        Some(body),
                        Some(function),
                    )
                }
                TypeDefinition::ContractFuture {
                    ref target,
                    signature,
                    result,
                } => (
                    AwaitProtocol::ContractMethod {
                        target: target.clone(),
                        signature,
                    },
                    result,
                    None,
                    None,
                ),
                TypeDefinition::ExecutionHandle {
                    result,
                    asynchronous: true,
                } => {
                    let output = self.result_type(result, self.runtime_error);
                    let signature = self.handle_protocol(self.vtype(source))?.awaiting.unwrap();
                    (
                        AwaitProtocol::Handle { output, signature },
                        output,
                        None,
                        None,
                    )
                }
                _ => {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "await requires a Future or an execution handle",
                    ));
                }
            };
        let mut site = self.site(n, ExecutionPhase::Invoke);
        let ready = self.predicate(PredicateKind::PollReady { source });
        let (suspension, received) = self.poll_transition(&mut site, ready);
        if let Some(body) = body {
            let domain = InstanceDomainId(self.p.execution.instance_domains.len() as u32);
            self.p.execution.instance_domains.push(InstanceDomain {
                id: domain,
                definition: InstanceDomainDefinition::AsyncInstance {
                    parent: self.ctx().domain,
                    task: source,
                },
            });
            let branch = self.p.bodies[body.0 as usize].root_branch;
            let timeline = self.p.execution.branches[branch.0 as usize].timeline;
            let entry = self.p.execution.timelines[timeline.0 as usize]
                .entries
                .first;
            self.p.execution.edges.push(ExecutionEdge::AwaitBody {
                poll: site.execution_moments.first,
                entry,
                instance: domain,
                future: source,
            });
        }
        let abstract_target = match &protocol {
            AwaitProtocol::ContractMethod { target, .. } => Some(target.clone()),
            _ => None,
        };
        let dependencies = if let Some(target) = &abstract_target {
            vec![DependencyRequirement::ContractFutureResult {
                future: source,
                target: target.clone(),
            }]
        } else if let Some(function) = function {
            vec![DependencyRequirement::FutureResult {
                future: source,
                function,
            }]
        } else {
            vec![DependencyRequirement::NativeResult {
                operation: site.id,
                source,
                position: None,
            }]
        };
        let result = self.value(
            output,
            ValueDefinition::OperationResult {
                operation: site.id,
                produced_at: received,
            },
            ProvenanceKind::Constructed(site.id),
            dependencies,
        );
        let effect = if let Some(target) = abstract_target.clone() {
            Effect::AwaitContract {
                future: source,
                target,
            }
        } else if let Some(function) = function {
            Effect::AwaitFuture {
                future: source,
                function,
            }
        } else {
            Effect::JoinHandle { handle: source }
        };
        let effects = self.effects(&site, vec![effect]);
        if function.is_none() && abstract_target.is_none() {
            self.complete_handle(source, site.id, received, site.guard);
        }
        self.emit(Operation::AwaitValue(AwaitValue {
            site,
            source,
            protocol: ResolvedAwait {
                protocol,
                result: output,
                completion: None,
            },
            suspension,
            result,
            effects,
        }));
        self.attach_result_reference(result, n);
        Ok(Expr { value: result })
    }
}
