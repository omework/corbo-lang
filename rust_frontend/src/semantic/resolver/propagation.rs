//! Compile-time resolution of builtin Option/Result success, failure and From
//! routes. The two execution paths remain explicit; no rule checker is invoked.
use super::*;
struct SumShape {
    result: bool,
    success: VariantId,
    failure: VariantId,
    payload: FieldId,
    ty: TypeId,
    error: Option<TypeId>,
}
impl Resolver<'_> {
    fn sum_shape(&mut self, n: ast::NodeId, ty: TypeId) -> Result<SumShape> {
        let TypeDefinition::Nominal { definition, .. } = self.p.types.entries[ty.0 as usize].kind
        else {
            return Err(self.fail(
                n,
                DiagnosticKind::TypeMismatch,
                "? and ! require an Option or Result value",
            ));
        };
        let result = if Some(definition) == self.p.well_known.result {
            true
        } else if Some(definition) == self.p.well_known.option {
            false
        } else {
            return Err(self.fail(
                n,
                DiagnosticKind::TypeMismatch,
                "? and ! apply to the builtin Option and Result types",
            ));
        };
        self.ensure_nominal(ty, n)?;
        let definition = self
            .p
            .declarations
            .enums
            .iter()
            .find(|e| e.ty == ty)
            .unwrap();
        let success = definition.variants.first;
        let failure = definition.variants.rest[0];
        let payload = self.p.declarations.variants[success.0 as usize].fields[0];
        let content = self.p.declarations.fields[payload.0 as usize].ty;
        let error = if result {
            Some(
                self.p.declarations.fields
                    [self.p.declarations.variants[failure.0 as usize].fields[0].0 as usize]
                    .ty,
            )
        } else {
            None
        };
        Ok(SumShape {
            result,
            success,
            failure,
            payload,
            ty: content,
            error,
        })
    }
    fn construct_known_variant(
        &mut self,
        n: ast::NodeId,
        variant: VariantId,
        values: Vec<ValueId>,
    ) -> Result<ValueId> {
        let definition = self.p.declarations.variants[variant.0 as usize].clone();
        if values.len() != definition.fields.len() {
            return Err(self.fail(
                n,
                DiagnosticKind::IncompleteRepresentation,
                "resolved constructor payload arity disagrees with its variant",
            ));
        }
        let mut components = vec![];
        for (field, value) in definition.fields.iter().zip(&values) {
            self.require_type(
                n,
                self.vtype(*value),
                self.p.declarations.fields[field.0 as usize].ty,
            )?;
            components.push(ComponentInitialization {
                position: PositionSelector::Field(*field),
                value: *value,
                transfer: self.transfer_kind(self.vtype(*value)),
            });
        }
        let site = self.site(n, ExecutionPhase::Compute);
        let dependencies = values.iter().flat_map(|v| self.dependencies(*v)).collect();
        let result = self.op_value(&site, definition.owner, dependencies);
        self.components.insert(result, values);
        self.materialize_value(
            result,
            Owner::Scope {
                scope: site.scope,
                instance: self.ctx().domain,
            },
            &site,
        );
        self.emit(Operation::ConstructEnum(ConstructEnum {
            site,
            ty: definition.owner,
            variant,
            components,
            result,
        }));
        Ok(result)
    }
    fn error_conversion(
        &mut self,
        n: ast::NodeId,
        inner: TypeId,
        outer: TypeId,
    ) -> Result<ErrorConversion> {
        if inner == outer {
            return Ok(ErrorConversion::Identity);
        }
        self.ensure_nominal(outer, n)?;
        let symbol = self
            .owner_scopes
            .get(&outer)
            .and_then(|scope| self.names[scope.0 as usize].get("from"))
            .copied()
            .ok_or_else(|| {
                self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    format!(
                        "error propagation requires {}::from({}) returning {}",
                        self.type_name(outer),
                        self.type_name(inner),
                        self.type_name(outer)
                    ),
                )
            })?;
        if let SymbolDefinition::Overloads(set) =
            self.p.symbols.entries[symbol.0 as usize].definition
        {
            return self
                .select_from_overload(n, set, inner, Some(outer))
                .map(ErrorConversion::From);
        }
        let SymbolDefinition::Function(function) =
            self.p.symbols.entries[symbol.0 as usize].definition
        else {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "error conversion is not an associated function",
            ));
        };
        let source = self.functions[function.0 as usize].clone();
        if source.parameters.len() != 1
            || !matches!(
                self.p.declarations.signatures[source.signature.0 as usize].receiver,
                ReceiverMode::None
            )
        {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                "error conversion must be an associated from(Inner) function",
            ));
        }
        let mut substitutions = self.nominal_substitutions(n, outer, Some(outer))?;
        self.infer_substitutions(n, source.parameters[0].1, inner, &mut substitutions)?;
        let actual = self.p.declarations.functions[function.0 as usize]
            .type_parameters
            .iter()
            .map(|p| {
                substitutions.get(p).copied().ok_or_else(|| {
                    self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "cannot infer error conversion type parameter",
                    )
                })
            })
            .collect::<Result<Vec<_>>>()?;
        let target = self.specialized_instance(function, actual)?;
        let signature = &self.p.declarations.signatures
            [self.p.declarations.instances[target.0 as usize].signature.0 as usize];
        self.require_type(n, signature.result, outer)?;
        self.require_type(n, signature.parameters[0].ty, inner)?;
        Ok(ErrorConversion::From(target))
    }
    pub(super) fn propagate_expression(
        &mut self,
        n: ast::NodeId,
        value: ast::NodeId,
        unwrap: bool,
    ) -> Result<Expr> {
        let subject = self.expression(value, None)?.value;
        if self.vtype(subject) == self.never {
            return Ok(Expr { value: subject });
        }
        let shape = self.sum_shape(n, self.vtype(subject))?;
        if unwrap {
            let mut site = self.site(n, ExecutionPhase::Read);
            self.phase(&mut site, ExecutionPhase::Receive);
            let check = CheckId(self.p.runtime_checks.len() as u32);
            self.p
                .runtime_checks
                .push(RuntimeCheck::Unwrap(UnwrapCheck {
                    id: check,
                    subject,
                    success_variant: shape.success,
                }));
            let result = self.projected_value(
                &site,
                subject,
                PositionSelector::Field(shape.payload),
                shape.ty,
            );
            let reference = self.references.get(&result).copied();
            self.emit(if shape.result {
                Operation::UnwrapResult(UnwrapResult {
                    site,
                    subject,
                    success_variant: shape.success,
                    result,
                    payload: shape.payload,
                    reference,
                    check,
                })
            } else {
                Operation::UnwrapOption(UnwrapOption {
                    site,
                    subject,
                    some: shape.success,
                    result,
                    payload: shape.payload,
                    reference,
                    check,
                })
            });
            return Ok(Expr { value: result });
        }
        let signature = self.p.declarations.instances[self.ctx().instance.0 as usize].signature;
        let outer_type = self.p.declarations.signatures[signature.0 as usize].result;
        let outer = self.sum_shape(n, outer_type)?;
        if shape.result != outer.result {
            return Err(self.fail(
                n,
                DiagnosticKind::TypeMismatch,
                "? requires the enclosing callable to return the same Option/Result kind",
            ));
        }
        let conversion = if let (Some(inner), Some(outer)) = (shape.error, outer.error) {
            self.error_conversion(n, inner, outer)?
        } else {
            ErrorConversion::Identity
        };
        let site = self.site(n, ExecutionPhase::Read);
        let parent = self.ctx().clone();
        let yes = self.predicate(PredicateKind::Variant {
            value: subject,
            variant: shape.success,
        });
        let no = self.predicate(PredicateKind::Variant {
            value: subject,
            variant: shape.failure,
        });
        let yes_guard = self.predicate(PredicateKind::All(vec![parent.guard, yes]));
        let no_guard = self.predicate(PredicateKind::All(vec![parent.guard, no]));
        self.ctx = Some(self.branch_context(&parent, site.id, yes_guard));
        let success_branch = self.ctx().branch;
        let extraction = self.site(n, ExecutionPhase::Read);
        let success_entry = extraction.execution_moments.first;
        let success = self.projected_value(
            &extraction,
            subject,
            PositionSelector::Field(shape.payload),
            shape.ty,
        );
        let reference = self.references.get(&success).copied();
        let transfer = self.transfer_kind(shape.ty);
        self.emit(Operation::ExtractVariantField(ExtractVariantField {
            site: extraction,
            source: subject,
            variant: shape.success,
            field: shape.payload,
            result: success,
            reference,
            transfer,
        }));
        let success_end = self.ctx().last.unwrap();
        let success_timeline = self.ctx().timeline;
        self.p.execution.timelines[success_timeline.0 as usize]
            .exits
            .push(success_end);
        self.ctx = Some(self.branch_context(&parent, site.id, no_guard));
        let failure_branch = self.ctx().branch;
        let failure_entry = ExecutionMomentId(self.p.execution.execution_moments.len() as u32);
        let mut error_values = vec![];
        if let Some(error_ty) = shape.error {
            let field = self.p.declarations.variants[shape.failure.0 as usize].fields[0];
            let extraction = self.site(n, ExecutionPhase::Read);
            let error = self.projected_value(
                &extraction,
                subject,
                PositionSelector::Field(field),
                error_ty,
            );
            let reference = self.references.get(&error).copied();
            let transfer = self.transfer_kind(error_ty);
            self.emit(Operation::ExtractVariantField(ExtractVariantField {
                site: extraction,
                source: subject,
                variant: shape.failure,
                field,
                result: error,
                reference,
                transfer,
            }));
            let error = if let ErrorConversion::From(target) = conversion {
                let function = self.p.declarations.instances[target.0 as usize].definition;
                self.invoke_concrete(
                    n,
                    self.functions[function.0 as usize].clone(),
                    target,
                    vec![error],
                    0,
                    outer.error,
                )?
                .value
            } else {
                error
            };
            error_values.push(error);
        }
        let failure = self.construct_known_variant(n, outer.failure, error_values)?;
        let return_site = self.site(n, ExecutionPhase::Receive);
        let (exit, outer_exits) = self.unwind_exits(&return_site, ScopeExitKind::Return, None);
        self.ctx_mut().returns.push(GuardedValue {
            guard: no_guard,
            value: failure,
        });
        let function = self.ctx().instance;
        self.return_to_caller(failure, function, &return_site);
        let failure_end = return_site.execution_moments.first;
        self.emit(Operation::ReturnControl(ReturnControl {
            site: return_site,
            function,
            value: failure,
            exit,
            outer_exits,
        }));
        let failure_context = self.ctx().clone();
        self.p.execution.timelines[failure_context.timeline.0 as usize]
            .exits
            .push(failure_end);
        self.ctx = Some(Context {
            last: None,
            guard: yes_guard,
            ..parent
        });
        self.accumulate_context(&failure_context);
        let receive = self.site(n, ExecutionPhase::Receive);
        let continuation = receive.execution_moments.first;
        let result = self.op_value(&receive, shape.ty, vec![]);
        self.forward_summaries(success, result);
        let provenance = self.p.values.entries[result.0 as usize].provenance;
        self.p.values.provenance[provenance.0 as usize].kind = ProvenanceKind::Forward {
            source: success,
            operation: receive.id,
        };
        if let Some(reference) = self.references.get(&success).copied() {
            self.references.insert(result, reference);
            self.value_entities
                .insert(result, EntityId::Reference(reference));
        }
        self.emit(Operation::ForwardResult(ForwardResult {
            site: receive,
            source: success,
            destination: result,
        }));
        for (to, guard) in [(success_entry, yes_guard), (failure_entry, no_guard)] {
            self.p
                .execution
                .edges
                .push(ExecutionEdge::Conditional(ConditionalEdge {
                    from: site.execution_moments.first,
                    to,
                    guard,
                }));
        }
        self.p
            .execution
            .edges
            .push(ExecutionEdge::Conditional(ConditionalEdge {
                from: success_end,
                to: continuation,
                guard: yes_guard,
            }));
        self.p
            .execution
            .relationships
            .push(BranchRelationship::Exclusive(ExclusiveBranches {
                decision: site.id,
                branches: NonEmpty {
                    first: success_branch,
                    rest: vec![failure_branch],
                },
            }));
        self.emit(if shape.result {
            Operation::PropagateResult(PropagateResult {
                site,
                subject,
                success_variant: shape.success,
                failure_variant: shape.failure,
                conversion,
                success: result,
                payload: shape.payload,
                success_branch,
                failure_branch,
                continuation,
                exit,
            })
        } else {
            Operation::PropagateOption(PropagateOption {
                site,
                subject,
                some: shape.success,
                none: shape.failure,
                success: result,
                payload: shape.payload,
                success_branch,
                failure_branch,
                continuation,
                exit,
            })
        });
        Ok(Expr { value: result })
    }
}
