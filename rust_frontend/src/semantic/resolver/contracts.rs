//! Structural contracts retain their whole disjunction and resolved method targets.
use super::*;
impl Resolver<'_> {
    pub(super) fn type_annotations(
        &mut self,
        annotations: &[ast::NodeId],
        scope: ScopeId,
        parameters: &mut Vec<TypeParameterId>,
    ) -> Result<Vec<TypeContractId>> {
        // Register the entire parameter set before resolving any requirement signature.
        for annotation in annotations {
            if let NodeKind::Annotation {
                syntax: AnnotationSyntax::TypeContract { parameter, .. },
                ..
            } = self.kind(*annotation)
            {
                let name = self.text(*parameter).to_owned();
                let id = match self.names[scope.0 as usize].get(&name).copied() {
                    Some(symbol) => match self.p.symbols.entries[symbol.0 as usize].definition {
                        SymbolDefinition::TypeParameter(id) => id,
                        _ => {
                            return Err(self.fail(
                                *annotation,
                                DiagnosticKind::DuplicateDeclaration,
                                "type parameter conflicts with an existing declaration",
                            ));
                        }
                    },
                    None => {
                        let id = TypeParameterId(self.p.types.parameters.len() as u32);
                        let symbol = self.declare(
                            *annotation,
                            scope,
                            &name,
                            SymbolDefinition::TypeParameter(id),
                        )?;
                        self.p.types.parameters.push(TypeParameter {
                            id,
                            symbol,
                            constraints: vec![],
                        });
                        self.intern(TypeKey::Parameter(id));
                        id
                    }
                };
                if !parameters.contains(&id) {
                    parameters.push(id);
                }
            }
        }
        let mut result = vec![];
        for annotation in annotations {
            let NodeKind::Annotation {
                syntax:
                    AnnotationSyntax::TypeContract {
                        parameter,
                        arguments,
                        with,
                        alternatives,
                        ..
                    },
                ..
            } = self.kind(*annotation)
            else {
                continue; // effect annotations have a separate producer
            };
            let symbol = self.lookup(scope, self.text(*parameter)).unwrap();
            let SymbolDefinition::TypeParameter(parameter) =
                self.p.symbols.entries[symbol.0 as usize].definition
            else {
                unreachable!()
            };
            let owner = self.intern(TypeKey::Parameter(parameter));
            let mut generic_arguments = vec![];
            for arg in arguments {
                let (name, allowed) = match self.kind(*arg) {
                    NodeKind::Type(TypeSyntax::Constrained {
                        parameter,
                        alternatives,
                    }) => {
                        let mut types = vec![];
                        for ty in alternatives {
                            types.push(self.type_syntax(*ty, scope)?);
                        }
                        (
                            self.text(*parameter).to_owned(),
                            AllowedTypes::OneOf(NonEmpty {
                                first: types[0],
                                rest: types[1..].to_vec(),
                            }),
                        )
                    }
                    NodeKind::Type(TypeSyntax::Path {
                        segments,
                        arguments,
                    }) if segments.len() == 1 && arguments.is_empty() => {
                        (self.text(segments[0]).to_owned(), AllowedTypes::Any)
                    }
                    _ => {
                        return Err(self.fail(
                            *arg,
                            DiagnosticKind::InvalidType,
                            "contract argument must name a declared type parameter",
                        ));
                    }
                };
                let symbol = self.lookup(scope, &name).ok_or_else(|| {
                    self.fail(
                        *arg,
                        DiagnosticKind::UnresolvedName,
                        format!("undefined type parameter '{name}'"),
                    )
                })?;
                let SymbolDefinition::TypeParameter(argument) =
                    self.p.symbols.entries[symbol.0 as usize].definition
                else {
                    return Err(self.fail(
                        *arg,
                        DiagnosticKind::InvalidType,
                        "contract argument is not a type parameter",
                    ));
                };
                generic_arguments.push(ContractTypeArgument {
                    parameter: argument,
                    allowed,
                });
            }
            let mut alternative_ids = vec![];
            for alternative in alternatives {
                let NodeKind::TypeContractAlternative { methods, .. } = self.kind(*alternative)
                else {
                    unreachable!()
                };
                let mut requirements = vec![];
                for method in methods {
                    let NodeKind::Function {
                        name,
                        parameters,
                        result,
                        asynchronous,
                        ..
                    } = self.kind(*method)
                    else {
                        unreachable!()
                    };
                    let mut types = vec![];
                    let mut receiver = ReceiverMode::None;
                    for parameter in parameters {
                        let NodeKind::Parameter {
                            name,
                            ty,
                            reference,
                            mutable,
                        } = self.kind(*parameter)
                        else {
                            unreachable!()
                        };
                        let pty = if let Some(ty) = ty {
                            self.type_syntax(*ty, scope)?
                        } else if reference.is_some() {
                            self.intern(TypeKey::Reference(mutable.is_some(), owner))
                        } else {
                            owner
                        };
                        if self.text(*name) == "self" {
                            receiver = match self.p.types.entries[pty.0 as usize].kind {
                                TypeDefinition::Reference {
                                    target,
                                    permission: ReferencePermission::Mutable,
                                } => ReceiverMode::Mutable(target),
                                TypeDefinition::Reference { target, .. } => {
                                    ReceiverMode::Shared(target)
                                }
                                _ => ReceiverMode::ByValue(pty),
                            };
                        }
                        types.push(pty);
                    }
                    let result = result
                        .map(|ty| self.type_syntax(ty, scope))
                        .transpose()?
                        .unwrap_or(self.unit);
                    let signature = self.signature(
                        types,
                        result,
                        receiver,
                        if asynchronous.is_some() {
                            FunctionExecution::Asynchronous
                        } else {
                            FunctionExecution::Synchronous
                        },
                    );
                    requirements.push(MethodRequirement {
                        name: self.text(*name).to_owned(),
                        signature,
                        origin: self.origin(*method),
                    });
                    self.cover(*method, SyntaxDisposition::ResolvedType(owner));
                }
                let id = ContractAlternativeId(self.p.contracts.alternatives.len() as u32);
                self.p.contracts.alternatives.push(ContractAlternative {
                    id,
                    requirements: NonEmpty {
                        first: requirements[0].clone(),
                        rest: requirements[1..].to_vec(),
                    },
                });
                alternative_ids.push(id);
            }
            let requirement = if alternative_ids.is_empty() {
                TypeRequirement::Unconstrained
            } else {
                TypeRequirement::Alternatives {
                    mode: if with.is_some() {
                        ContractMode::AtLeast
                    } else {
                        ContractMode::Exact
                    },
                    alternatives: NonEmpty {
                        first: alternative_ids[0],
                        rest: alternative_ids[1..].to_vec(),
                    },
                }
            };
            let id = TypeContractId(self.p.contracts.types.len() as u32);
            let origin = self.origin(*annotation);
            self.p.contracts.types.push(StructuralTypeContract {
                id,
                parameter,
                arguments: generic_arguments,
                requirement,
                origin,
            });
            self.p.types.parameters[parameter.0 as usize]
                .constraints
                .push(id);
            self.cover(*annotation, SyntaxDisposition::Declaration(symbol));
            result.push(id);
        }
        Ok(result)
    }
    fn contract_candidates(
        &mut self,
        n: ast::NodeId,
        contract: TypeContractId,
        substitutions: &HashMap<TypeParameterId, TypeId>,
    ) -> Result<
        Vec<(
            ContractAlternativeId,
            HashMap<TypeParameterId, TypeId>,
            Vec<FunctionId>,
        )>,
    > {
        let contract = self.p.contracts.types[contract.0 as usize].clone();
        let Some(actual) = substitutions.get(&contract.parameter).copied() else {
            return Ok(vec![]);
        };
        if matches!(
            self.p.types.entries[actual.0 as usize].kind,
            TypeDefinition::Parameter(_)
        ) {
            return Ok(self
                .symbolic_contract_witnesses(n, contract.id, actual, substitutions)?
                .into_iter()
                .map(|(alternative, inferred, _)| (alternative, inferred, vec![]))
                .collect());
        }
        self.ensure_nominal(actual, n)?;
        let TypeRequirement::Alternatives { mode, alternatives } = contract.requirement else {
            return Ok(vec![]);
        };
        let scope = self.owner_scopes.get(&actual).copied();
        let names = scope
            .map(|s| self.names[s.0 as usize].clone())
            .unwrap_or_default();
        let method_count = names
            .values()
            .filter(|s| {
                matches!(
                    self.p.symbols.entries[s.0 as usize].definition,
                    SymbolDefinition::Function(_)
                )
            })
            .count();
        let mut owner_substitutions = HashMap::new();
        if let TypeDefinition::Nominal {
            definition,
            arguments,
            ..
        } = &self.p.types.entries[actual.0 as usize].kind
        {
            for (param, argument) in self
                .nominal_parameters
                .get(definition)
                .into_iter()
                .flatten()
                .zip(arguments)
            {
                if let TypeArgument::Type(ty) = argument {
                    owner_substitutions.insert(*param, *ty);
                }
            }
        }
        let mut matches = vec![];
        for alternative in std::iter::once(alternatives.first).chain(alternatives.rest) {
            let requirements = self.p.contracts.alternatives[alternative.0 as usize]
                .requirements
                .clone();
            if matches!(mode, ContractMode::Exact) && method_count != 1 + requirements.rest.len() {
                continue;
            }
            let mut inferred = substitutions.clone();
            let mut methods = vec![];
            let mut valid = true;
            for requirement in std::iter::once(requirements.first).chain(requirements.rest) {
                let Some(symbol) = names.get(&requirement.name) else {
                    valid = false;
                    break;
                };
                let SymbolDefinition::Function(function) =
                    self.p.symbols.entries[symbol.0 as usize].definition
                else {
                    valid = false;
                    break;
                };
                let wanted =
                    self.p.declarations.signatures[requirement.signature.0 as usize].clone();
                let found = self.p.declarations.signatures
                    [self.functions[function.0 as usize].signature.0 as usize]
                    .clone();
                if wanted.parameters.len() != found.parameters.len()
                    || std::mem::discriminant(&wanted.execution)
                        != std::mem::discriminant(&found.execution)
                    || std::mem::discriminant(&wanted.receiver)
                        != std::mem::discriminant(&found.receiver)
                {
                    valid = false;
                    break;
                }
                for (wanted, found) in wanted.parameters.iter().zip(&found.parameters) {
                    let found = self.substitute_type(found.ty, &owner_substitutions);
                    if self
                        .infer_substitutions(n, wanted.ty, found, &mut inferred)
                        .is_err()
                    {
                        valid = false;
                        break;
                    }
                }
                let found_result = self.substitute_type(found.result, &owner_substitutions);
                if !valid
                    || self
                        .infer_substitutions(n, wanted.result, found_result, &mut inferred)
                        .is_err()
                {
                    valid = false;
                    break;
                }
                methods.push(function);
            }
            if valid
                && contract
                    .arguments
                    .iter()
                    .all(|argument| match &argument.allowed {
                        AllowedTypes::Any => true,
                        AllowedTypes::OneOf(types) => {
                            inferred.get(&argument.parameter).is_some_and(|actual| {
                                std::iter::once(&types.first)
                                    .chain(&types.rest)
                                    .any(|ty| ty == actual)
                            })
                        }
                    })
            {
                matches.push((alternative, inferred, methods));
            }
        }
        Ok(matches)
    }
    pub(super) fn infer_contract_arguments(
        &mut self,
        n: ast::NodeId,
        parameters: &[TypeParameterId],
        substitutions: &mut HashMap<TypeParameterId, TypeId>,
    ) -> Result<()> {
        loop {
            let before = substitutions.len();
            for parameter in parameters {
                for contract in self.p.types.parameters[parameter.0 as usize]
                    .constraints
                    .clone()
                {
                    let candidates = self.contract_candidates(n, contract, substitutions)?;
                    if let Some((_, first, _)) = candidates.first() {
                        for (parameter, ty) in first {
                            if candidates
                                .iter()
                                .any(|(_, args, _)| args.get(parameter) != Some(ty))
                            {
                                return Err(self.fail(n, DiagnosticKind::InvalidType, "structural contract alternatives infer incompatible type arguments"));
                            }
                            substitutions.insert(*parameter, *ty);
                        }
                    }
                }
            }
            if substitutions.len() == before {
                break;
            }
        }
        Ok(())
    }
    pub(super) fn resolve_contracts(
        &mut self,
        n: ast::NodeId,
        parameters: &[TypeParameterId],
        substitutions: &HashMap<TypeParameterId, TypeId>,
    ) -> Result<Vec<ContractMatchId>> {
        let mut result = vec![];
        for parameter in parameters {
            for contract in self.p.types.parameters[parameter.0 as usize]
                .constraints
                .clone()
            {
                if matches!(
                    self.p.contracts.types[contract.0 as usize].requirement,
                    TypeRequirement::Unconstrained
                ) {
                    continue;
                }
                if matches!(
                    self.p.types.entries[substitutions[parameter].0 as usize].kind,
                    TypeDefinition::Parameter(_)
                ) {
                    let witnesses = self.symbolic_contract_witnesses(
                        n,
                        contract,
                        substitutions[parameter],
                        substitutions,
                    )?;
                    if witnesses.is_empty() {
                        return Err(self.fail(n,DiagnosticKind::InvalidType,"the enclosing type contracts do not supply the callee's required interface"));
                    }
                    let evidence = witnesses
                        .into_iter()
                        .flat_map(|(_, _, evidence)| evidence)
                        .collect();
                    let mut resolved = substitutions
                        .iter()
                        .map(|(parameter, actual)| TypeSubstitution {
                            parameter: *parameter,
                            actual: *actual,
                        })
                        .collect::<Vec<_>>();
                    resolved.sort_by_key(|s| s.parameter.0);
                    self.p
                        .contracts
                        .symbolic_requirements
                        .push(SymbolicContractRequirement {
                            contract,
                            actual: substitutions[parameter],
                            substitutions: resolved,
                            evidence,
                        });
                    continue;
                }
                let candidates = self.contract_candidates(n, contract, substitutions)?;
                if candidates.is_empty() {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "concrete type satisfies no complete structural-contract alternative",
                    ));
                }
                let mut matching = vec![];
                for (alternative, _, functions) in candidates {
                    let mut methods = vec![];
                    for (index, function) in functions.into_iter().enumerate() {
                        let generic = self.p.declarations.functions[function.0 as usize]
                            .type_parameters
                            .clone();
                        let owner = self.functions[function.0 as usize].owner;
                        let actual = substitutions[parameter];
                        let mut args = HashMap::new();
                        if let Some(owner) = owner {
                            self.infer_substitutions(n, owner, actual, &mut args)?;
                        }
                        let actuals = generic
                            .iter()
                            .map(|p| {
                                args.get(p).copied().ok_or_else(|| {
                                    self.fail(
                                        n,
                                        DiagnosticKind::InvalidType,
                                        "contract method has unresolved generic arguments",
                                    )
                                })
                            })
                            .collect::<Result<Vec<_>>>()?;
                        let implementation = self.specialized_instance(function, actuals)?;
                        methods.push(MethodResolution {
                            requirement_index: index as u32,
                            implementation,
                        });
                    }
                    matching.push(AlternativeMatch {
                        alternative,
                        methods: NonEmpty {
                            first: methods[0].clone(),
                            rest: methods[1..].to_vec(),
                        },
                    });
                }
                let id = ContractMatchId(self.p.contracts.matches.len() as u32);
                self.p.contracts.matches.push(ContractMatch {
                    id,
                    contract,
                    actual: substitutions[parameter],
                    matching: NonEmpty {
                        first: matching[0].clone(),
                        rest: matching[1..].to_vec(),
                    },
                });
                result.push(id);
            }
        }
        Ok(result)
    }
}
