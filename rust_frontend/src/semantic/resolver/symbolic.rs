//! Parametric bodies use declared interfaces and symbolic type identities.
//! No representative concrete types, rule proofs or executable lowering.
use super::*;
impl Resolver<'_> {
    /// Distinguish an unsolved callee inference variable from a rigid type
    /// parameter already introduced by the enclosing parametric body.
    pub(super) fn type_parameter_occurs(&self, ty: TypeId, parameter: TypeParameterId) -> bool {
        match &self.p.types.entries[ty.0 as usize].kind {
            TypeDefinition::Parameter(p) => *p == parameter,
            TypeDefinition::Reference { target, .. } => {
                self.type_parameter_occurs(*target, parameter)
            }
            TypeDefinition::Tuple(parts) => parts
                .iter()
                .any(|ty| self.type_parameter_occurs(*ty, parameter)),
            TypeDefinition::Allocation { content } => {
                self.type_parameter_occurs(*content, parameter)
            }
            TypeDefinition::ExecutionHandle { result, .. }
            | TypeDefinition::ContractFuture { result, .. } => {
                self.type_parameter_occurs(*result, parameter)
            }
            TypeDefinition::Future { result, state, .. } => {
                self.type_parameter_occurs(*result, parameter)
                    || self.type_parameter_occurs(*state, parameter)
            }
            TypeDefinition::KeyedCollection { key, value } => {
                self.type_parameter_occurs(*key, parameter)
                    || self.type_parameter_occurs(*value, parameter)
            }
            TypeDefinition::Callable(signature) | TypeDefinition::Closure { signature, .. } => {
                let signature = &self.p.declarations.signatures[signature.0 as usize];
                self.type_parameter_occurs(signature.result, parameter)
                    || signature
                        .parameters
                        .iter()
                        .any(|part| self.type_parameter_occurs(part.ty, parameter))
            }
            TypeDefinition::Array { element, .. }
            | TypeDefinition::Slice { element }
            | TypeDefinition::GrowingSequence { element }
            | TypeDefinition::Pool { element } => self.type_parameter_occurs(*element, parameter),
            TypeDefinition::Nominal { arguments, .. } => arguments.iter().any(
                |a| matches!(a,TypeArgument::Type(ty)if self.type_parameter_occurs(*ty,parameter)),
            ),
            _ => false,
        }
    }
    pub(super) fn unbound_for_call(
        &self,
        ty: TypeId,
        substitutions: &HashMap<TypeParameterId, TypeId>,
    ) -> bool {
        match &self.p.types.entries[ty.0 as usize].kind {
            TypeDefinition::Parameter(parameter)=>!substitutions.contains_key(parameter)&&!self.ctx.as_ref().is_some_and(|ctx|ctx.substitutions.contains_key(parameter)||ctx.substitutions.values().any(|ty|self.type_parameter_occurs(*ty,*parameter))),
            TypeDefinition::Reference{target,..}=>self.unbound_for_call(*target,substitutions),
            TypeDefinition::Array{element,..}|TypeDefinition::Slice{element}|TypeDefinition::GrowingSequence{element}|TypeDefinition::Pool{element}=>self.unbound_for_call(*element,substitutions),
            TypeDefinition::Tuple(parts)=>parts.iter().any(|part|self.unbound_for_call(*part,substitutions)),
            TypeDefinition::Nominal{arguments,..}=>arguments.iter().any(|arg|matches!(arg,TypeArgument::Type(ty)if self.unbound_for_call(*ty,substitutions))),
            _=>false,
        }
    }
    pub(super) fn contract_method_call(
        &mut self,
        n: ast::NodeId,
        place: EvaluatedPlaceId,
        ty: TypeId,
        name: &str,
        args: &[ast::NodeId],
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        let TypeDefinition::Parameter(parameter) = self.p.types.entries[ty.0 as usize].kind else {
            unreachable!()
        };
        let mut choices = vec![];
        for contract in self.p.types.parameters[parameter.0 as usize]
            .constraints
            .clone()
        {
            let TypeRequirement::Alternatives { alternatives, .. } = self.p.contracts.types
                [contract.0 as usize]
                .requirement
                .clone()
            else {
                continue;
            };
            let mut complete = true;
            let mut candidates = vec![];
            for alternative in std::iter::once(alternatives.first).chain(alternatives.rest) {
                let required = self.p.contracts.alternatives[alternative.0 as usize]
                    .requirements
                    .clone();
                let found = std::iter::once(required.first)
                    .chain(required.rest)
                    .enumerate()
                    .find(|(_, r)| r.name == name);
                if let Some((index, method)) = found {
                    candidates.push(ContractMethodReference {
                        contract,
                        alternative,
                        requirement_index: index as u32,
                        signature: method.signature,
                    });
                } else {
                    complete = false;
                    break;
                }
            }
            if complete {
                choices.extend(candidates);
            }
        }
        let first = choices.first().cloned().ok_or_else(|| {
            self.fail(
                n,
                DiagnosticKind::UnresolvedName,
                format!(
                    "type parameter has no declared method '{name}' guaranteed by its contracts"
                ),
            )
        })?;
        let shape = self.p.declarations.signatures[first.signature.0 as usize].clone();
        for choice in &choices[1..] {
            let other = &self.p.declarations.signatures[choice.signature.0 as usize];
            if shape.result != other.result
                || shape.parameters.len() != other.parameters.len()
                || !shape
                    .parameters
                    .iter()
                    .zip(&other.parameters)
                    .all(|(a, b)| a.ty == b.ty)
            {
                return Err(self.fail(n,DiagnosticKind::TypeMismatch,"contract alternatives provide different method signatures; no alternative was selected"));
            }
        }
        let receiver = match shape.receiver {
            ReceiverMode::Shared(_) => self.borrow(n, place, false)?,
            ReceiverMode::Mutable(_) => self.borrow(n, place, true)?,
            ReceiverMode::ByValue(_) => self.load(n, place)?,
            ReceiverMode::None => {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidCall,
                    "contract member requires an instance receiver",
                ));
            }
        };
        if shape.parameters.len() != args.len() + 1 {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "contract method argument count differs from its signature",
            ));
        }
        let mut values = vec![receiver.value];
        for (arg, parameter) in args.iter().zip(&shape.parameters[1..]) {
            let value = self.expression(*arg, Some(parameter.ty))?.value;
            self.require_type(*arg, self.vtype(value), parameter.ty)?;
            values.push(value);
        }
        if !matches!(shape.execution, FunctionExecution::Asynchronous) {
            if let Some(expected) = expected {
                self.require_type(n, shape.result, expected)?;
            }
        }
        let target = MethodTarget::ContractAlternatives(NonEmpty {
            first,
            rest: choices.into_iter().skip(1).collect(),
        });
        if matches!(shape.execution, FunctionExecution::Asynchronous) {
            let ty = TypeId(self.p.types.entries.len() as u32);
            self.p.types.entries.push(ResolvedType {
                id: ty,
                kind: TypeDefinition::ContractFuture {
                    target: target.clone(),
                    signature: shape.id,
                    result: shape.result,
                },
            });
            let site = self.site(n, ExecutionPhase::Compute);
            let result = self.op_value(
                &site,
                ty,
                values.iter().flat_map(|v| self.dependencies(*v)).collect(),
            );
            self.components.insert(result, values.clone());
            let arguments = values
                .iter()
                .enumerate()
                .map(|(i, value)| CallArgument {
                    parameter_index: i as u32,
                    value: *value,
                    transfer: self.transfer_kind(self.vtype(*value)),
                })
                .collect();
            self.emit(Operation::CreateContractFuture(CreateContractFuture {
                site,
                target,
                arguments,
                result,
            }));
            return Ok(Expr { value: result });
        }
        let mut site = self.site(n, ExecutionPhase::Invoke);
        self.phase(&mut site, ExecutionPhase::Receive);
        let result = self.op_value(
            &site,
            shape.result,
            vec![DependencyRequirement::ContractResult {
                target: target.clone(),
                arguments: values.clone(),
            }],
        );
        let arguments = values
            .iter()
            .enumerate()
            .map(|(index, value)| CallArgument {
                parameter_index: index as u32,
                value: *value,
                transfer: self.transfer_kind(self.vtype(*value)),
            })
            .collect::<Vec<_>>();
        let effects = self.effects(
            &site,
            vec![Effect::ContractCall {
                target: target.clone(),
                arguments: arguments.clone(),
            }],
        );
        self.emit(Operation::MethodCall(MethodCall {
            site,
            target: ResolvedMethodCall {
                target,
                receiver: receiver.value,
                mode: shape.receiver,
                matched_contract: None,
            },
            arguments: arguments.into_iter().skip(1).collect(),
            result,
            effects,
        }));
        self.attach_result_reference(result, n);
        Ok(Expr { value: result })
    }
}

impl Resolver<'_> {
    pub(super) fn parametric_transfer(
        &mut self,
        n: ast::NodeId,
        place: EvaluatedPlaceId,
        source: ValueId,
        ty: TypeId,
    ) -> Result<Expr> {
        let site = self.site(n, ExecutionPhase::Receive);
        let copies = self.predicate(PredicateKind::TypeCopiesByValue(ty));
        let copy_guard = self.predicate(PredicateKind::All(vec![site.guard, copies]));
        let not_copy = self.predicate(PredicateKind::Not(copies));
        let move_guard = self.predicate(PredicateKind::All(vec![site.guard, not_copy]));
        let copied = self.value(
            ty,
            ValueDefinition::ConditionalResult {
                operation: site.id,
                produced_at: site.execution_moments.first,
                guard: copy_guard,
            },
            ProvenanceKind::Constructed(site.id),
            self.primitive_constraints(source),
        );
        let copy_site = OperationSite {
            guard: copy_guard,
            ..site.clone()
        };
        self.materialize_value(
            copied,
            Owner::Scope {
                scope: site.scope,
                instance: self.ctx().domain,
            },
            &copy_site,
        );
        let moved = self.value(
            ty,
            ValueDefinition::ConditionalResult {
                operation: site.id,
                produced_at: site.execution_moments.first,
                guard: move_guard,
            },
            ProvenanceKind::Move {
                source,
                operation: site.id,
            },
            self.dependencies(source),
        );
        let move_site = OperationSite {
            guard: move_guard,
            ..site.clone()
        };
        self.transfer(
            moved,
            Owner::Scope {
                scope: site.scope,
                instance: self.ctx().domain,
            },
            &move_site,
        );
        let result = self.op_value(&site, ty, vec![]);
        let provenance = self.p.values.entries[result.0 as usize].provenance;
        self.p.values.provenance[provenance.0 as usize].kind = ProvenanceKind::Merge(NonEmpty {
            first: GuardedValue {
                guard: copy_guard,
                value: copied,
            },
            rest: vec![GuardedValue {
                guard: move_guard,
                value: moved,
            }],
        });
        let summary = self.p.values.entries[result.0 as usize].dependencies;
        let copy_dependencies = self.guarded_dependencies(copied, copy_guard);
        self.p.values.dependency_summaries[summary.0 as usize]
            .guarded
            .extend(copy_dependencies);
        let dependencies = self.guarded_dependencies(moved, move_guard);
        self.p.values.dependency_summaries[summary.0 as usize]
            .guarded
            .extend(dependencies);
        self.emit(Operation::ParametricTransfer(ParametricTransfer {
            site,
            source: place,
            value: source,
            ty,
            copies,
            copied,
            moved,
            result,
        }));
        Ok(Expr { value: result })
    }
}

impl Resolver<'_> {
    /// Every possible provided disjunct must entail a required disjunct. Retain
    /// all witnesses; never choose a representative type or first alternative.
    pub(super) fn symbolic_contract_witnesses(
        &mut self,
        n: ast::NodeId,
        required: TypeContractId,
        actual: TypeId,
        substitutions: &HashMap<TypeParameterId, TypeId>,
    ) -> Result<
        Vec<(
            ContractAlternativeId,
            HashMap<TypeParameterId, TypeId>,
            Vec<SymbolicContractEvidence>,
        )>,
    > {
        let TypeDefinition::Parameter(parameter) = self.p.types.entries[actual.0 as usize].kind
        else {
            return Ok(vec![]);
        };
        let TypeRequirement::Alternatives {
            mode: required_mode,
            alternatives: required_alternatives,
        } = self.p.contracts.types[required.0 as usize]
            .requirement
            .clone()
        else {
            return Ok(vec![]);
        };
        let required_alternatives = std::iter::once(required_alternatives.first)
            .chain(required_alternatives.rest)
            .collect::<Vec<_>>();
        let mut all = vec![];
        for provided in self.p.types.parameters[parameter.0 as usize]
            .constraints
            .clone()
        {
            let TypeRequirement::Alternatives {
                mode: provided_mode,
                alternatives,
            } = self.p.contracts.types[provided.0 as usize]
                .requirement
                .clone()
            else {
                continue;
            };
            if matches!(required_mode, ContractMode::Exact)
                && !matches!(provided_mode, ContractMode::Exact)
            {
                continue;
            }
            let mut witnesses = vec![];
            let mut complete = true;
            for available in std::iter::once(alternatives.first).chain(alternatives.rest) {
                let supplied = self.p.contracts.alternatives[available.0 as usize]
                    .requirements
                    .clone();
                let supplied = std::iter::once(supplied.first)
                    .chain(supplied.rest)
                    .collect::<Vec<_>>();
                let mut branch = vec![];
                for desired in &required_alternatives {
                    let wanted = self.p.contracts.alternatives[desired.0 as usize]
                        .requirements
                        .clone();
                    let wanted = std::iter::once(wanted.first)
                        .chain(wanted.rest)
                        .collect::<Vec<_>>();
                    if matches!(required_mode, ContractMode::Exact)
                        && wanted.len() != supplied.len()
                    {
                        continue;
                    }
                    let mut inferred = substitutions.clone();
                    let mut methods = vec![];
                    let mut valid = true;
                    for method in &wanted {
                        let Some((index, found)) = supplied
                            .iter()
                            .enumerate()
                            .find(|(_, found)| found.name == method.name)
                        else {
                            valid = false;
                            break;
                        };
                        let want =
                            self.p.declarations.signatures[method.signature.0 as usize].clone();
                        let have =
                            self.p.declarations.signatures[found.signature.0 as usize].clone();
                        if want.parameters.len() != have.parameters.len()
                            || std::mem::discriminant(&want.receiver)
                                != std::mem::discriminant(&have.receiver)
                            || std::mem::discriminant(&want.execution)
                                != std::mem::discriminant(&have.execution)
                        {
                            valid = false;
                            break;
                        }
                        for (a, b) in want.parameters.iter().zip(&have.parameters) {
                            if self
                                .infer_substitutions(n, a.ty, b.ty, &mut inferred)
                                .is_err()
                            {
                                valid = false;
                                break;
                            }
                        }
                        if !valid
                            || self
                                .infer_substitutions(n, want.result, have.result, &mut inferred)
                                .is_err()
                        {
                            valid = false;
                            break;
                        }
                        methods.push(ContractMethodReference {
                            contract: provided,
                            alternative: available,
                            requirement_index: index as u32,
                            signature: found.signature,
                        });
                    }
                    if valid {
                        branch.push((
                            *desired,
                            inferred,
                            vec![SymbolicContractEvidence {
                                provided,
                                provided_alternative: available,
                                required_alternative: *desired,
                                methods,
                            }],
                        ));
                    }
                }
                if branch.is_empty() {
                    complete = false;
                    break;
                }
                witnesses.extend(branch);
            }
            if complete {
                all.extend(witnesses);
            }
        }
        Ok(all)
    }
}
