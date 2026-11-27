//! Annotation contracts describe effects; they never synthesize a lock implementation.
use super::*;
impl Resolver<'_> {
    fn annotation_name(&self, n: ast::NodeId) -> &str {
        let NodeKind::Annotation { name, .. } = self.kind(n) else {
            unreachable!()
        };
        self.text(*name)
    }
    fn properties(&self, n: ast::NodeId) -> Vec<ast::NodeId> {
        match self.kind(n) {
            NodeKind::Annotation {
                syntax: AnnotationSyntax::Properties { entries },
                ..
            } => entries.clone(),
            _ => vec![],
        }
    }
    fn property_key(&self, n: ast::NodeId) -> String {
        self.syntax.node_text(n).to_owned()
    }
    fn property_bool(&self, n: ast::NodeId) -> Result<bool> {
        match self.syntax.node_text(n) {
            "true" => Ok(true),
            "false" => Ok(false),
            _ => Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                "annotation property requires true or false",
            )),
        }
    }
    fn size_bytes(&self, n: ast::NodeId) -> Result<u64> {
        let NodeKind::Size { number, unit } = self.kind(n) else {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                "memory budget requires a positive integer followed by K, M or G",
            ));
        };
        let number = self.text(*number).parse::<u64>().ok().filter(|n| *n > 0);
        let factor = match self.text(*unit) {
            "K" => 1024,
            "M" => 1024 * 1024,
            "G" => 1024 * 1024 * 1024,
            _ => 0,
        };
        number
            .and_then(|n| n.checked_mul(factor))
            .filter(|_| factor != 0)
            .ok_or_else(|| {
                self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    "memory budget overflows u64 or has an invalid unit",
                )
            })
    }
    pub(super) fn memory_annotation(&mut self, n: ast::NodeId, scope: ScopeId) -> Result<()> {
        let name = self.annotation_name(n).to_owned();
        let origin = self.origin(n);
        let properties = self.properties(n);
        let mut values = HashMap::new();
        for property in properties {
            let NodeKind::Property { key, value } = self.kind(property) else {
                unreachable!()
            };
            let key = self.property_key(*key);
            if values.insert(key.clone(), *value).is_some() {
                return Err(self.fail(
                    property,
                    DiagnosticKind::DuplicateDeclaration,
                    format!("duplicate annotation property '{key}'"),
                ));
            }
        }
        match name.as_str() {
            "datastack" => {
                let budget = |this: &Self, name: &str| -> Result<BudgetRequest> {
                    values
                        .get(name)
                        .map(|n| this.size_bytes(*n).map(BudgetRequest::Explicit))
                        .unwrap_or(Ok(BudgetRequest::InferThenDefault))
                };
                let configuration = DataStackConfiguration {
                    origin,
                    fixed_size: budget(self, "size")?,
                    region_stack_size: budget(self, "region_stack_size")?,
                    region_size: budget(self, "region_size")?,
                    reclaim_threshold: budget(self, "reclaim_threshold")?,
                    region_reclaim_threshold: budget(self, "region_reclaim_threshold")?,
                };
                self.p
                    .contracts
                    .memory_configuration
                    .push(MemoryConfiguration::DataStack(configuration));
            }
            "stack_region" => {
                let max = *values.get("max_size").ok_or_else(|| {
                    self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "stack_region requires max_size",
                    )
                })?;
                let maximum_bytes = self.size_bytes(max)?;
                let count = values
                    .get("count")
                    .map(|n| self.integer_constant(*n, scope))
                    .transpose()?;
                self.p
                    .contracts
                    .memory_configuration
                    .push(MemoryConfiguration::Region(RegionConfiguration {
                        scope,
                        maximum_bytes,
                        count,
                        origin,
                    }));
            }
            "free_pages" => {
                self.p
                    .contracts
                    .memory_configuration
                    .push(MemoryConfiguration::FreePages(FreePagesRequest {
                        scope,
                        origin,
                    }))
            }
            "override" => return self.override_annotation(n, scope, &values),
            "directive" => return self.async_pool_annotation(n, scope, &values),
            _ => {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    format!("annotation '{name}' is not valid in this context"),
                ));
            }
        }
        self.cover(n, SyntaxDisposition::Boundary(scope));
        Ok(())
    }
    pub(super) fn type_effect_annotations(&mut self, n: ast::NodeId, ty: TypeId) -> Result<()> {
        let attributes = match self.kind(n) {
            NodeKind::Struct { attributes, .. } | NodeKind::Enum { attributes, .. } => attributes,
            _ => unreachable!(),
        };
        let mut contracts = vec![];
        for annotation in &attributes.annotations {
            match self.annotation_name(*annotation) {
                "type" => {}
                "thread" => {
                    let properties = self.properties(*annotation);
                    let property = properties[0];
                    let NodeKind::Property { value, .. } = self.kind(property) else {
                        unreachable!()
                    };
                    let forbidden = !self.property_bool(*value)?;
                    let id = ThreadContractId(self.p.contracts.threads.len() as u32);
                    let origin = self.origin(*annotation);
                    self.p.contracts.threads.push(ThreadTransferContract {
                        id,
                        ty,
                        declared_forbidden: forbidden,
                        origin,
                    });
                    contracts.push(ResolvedContract::Thread(id));
                }
                "lock" => {
                    let methods = self
                        .p
                        .declarations
                        .structs
                        .iter()
                        .find(|s| s.ty == ty)
                        .map(|s| s.methods.clone())
                        .unwrap_or_default();
                    for function in methods {
                        let definition = &self.p.declarations.functions[function.0 as usize];
                        let signature =
                            &self.p.declarations.signatures[definition.signature.0 as usize];
                        if matches!(
                            self.p.symbols.entries[definition.symbol.0 as usize].visibility,
                            Visibility::Public
                        ) && !matches!(signature.receiver, ReceiverMode::None)
                        {
                            let annotation = *annotation;
                            self.functions[function.0 as usize]
                                .annotations
                                .push(annotation);
                        }
                    }
                }
                name => {
                    return Err(self.fail(
                        *annotation,
                        DiagnosticKind::InvalidType,
                        format!("unsupported type annotation '{name}'"),
                    ));
                }
            }
        }
        self.p
            .contracts
            .type_effects
            .push(TypeEffectContracts { ty, contracts });
        Ok(())
    }
    pub(super) fn resolve_function_effect_annotations(
        &mut self,
        instance: FunctionInstanceId,
    ) -> Result<()> {
        if !self.p.declarations.instances[instance.0 as usize]
            .contracts
            .is_empty()
        {
            return Ok(());
        }
        let function = self.p.declarations.instances[instance.0 as usize].definition;
        let source = self.functions[function.0 as usize].clone();
        let signature = self.p.declarations.signatures[self.p.declarations.instances
            [instance.0 as usize]
            .signature
            .0 as usize]
            .clone();
        let mut contracts = vec![];
        for annotation in source.annotations {
            match self.kind(annotation) {
                NodeKind::Annotation {
                    syntax: AnnotationSyntax::TypeContract { .. },
                    ..
                } => {}
                NodeKind::Annotation {
                    syntax: AnnotationSyntax::Branch { join },
                    ..
                } => {
                    let completion = if let Some(join) = join {
                        match self.kind(*join) {
                            NodeKind::Await { .. } => CompletionContract::ThroughResult {
                                selector: ResolvedCompletionSelector::Await(
                                    self.p.declarations.instances[instance.0 as usize].signature,
                                ),
                            },
                            NodeKind::Call { callee, arguments } if arguments.is_empty() => {
                                let NodeKind::Projection { member, .. } = self.kind(*callee) else {
                                    unreachable!()
                                };
                                let name = self.text(*member).to_owned();
                                self.ensure_nominal(signature.result, annotation)?;
                                let symbol = self
                                    .owner_scopes
                                    .get(&signature.result)
                                    .and_then(|s| self.names[s.0 as usize].get(&name))
                                    .copied()
                                    .ok_or_else(|| {
                                        self.fail(
                                            annotation,
                                            DiagnosticKind::InvalidType,
                                            format!(
                                                "branch result has no completion method '{name}'"
                                            ),
                                        )
                                    })?;
                                let SymbolDefinition::Function(method) =
                                    self.p.symbols.entries[symbol.0 as usize].definition
                                else {
                                    return Err(self.fail(
                                        annotation,
                                        DiagnosticKind::InvalidCall,
                                        "branch completion member is not a method",
                                    ));
                                };
                                let mut inferred = HashMap::new();
                                if let Some(owner) = self.functions[method.0 as usize].owner {
                                    self.infer_substitutions(
                                        annotation,
                                        owner,
                                        signature.result,
                                        &mut inferred,
                                    )?;
                                }
                                let parameters = self.p.declarations.functions[method.0 as usize]
                                    .type_parameters
                                    .clone();
                                let actual = parameters
                                    .iter()
                                    .map(|p| {
                                        inferred.get(p).copied().ok_or_else(|| {
                                            self.fail(
                                                annotation,
                                                DiagnosticKind::InvalidType,
                                                "completion method has unresolved type parameters",
                                            )
                                        })
                                    })
                                    .collect::<Result<Vec<_>>>()?;
                                let target = self.specialized_instance(method, actual)?;
                                let method_signature =
                                    &self.p.declarations.signatures[self.p.declarations.instances
                                        [target.0 as usize]
                                        .signature
                                        .0
                                        as usize];
                                if method_signature.parameters.len() != 1
                                    || matches!(method_signature.receiver, ReceiverMode::None)
                                {
                                    return Err(self.fail(
                                        annotation,
                                        DiagnosticKind::InvalidType,
                                        "branch completion method must take only its receiver",
                                    ));
                                }
                                CompletionContract::ThroughResult {
                                    selector: ResolvedCompletionSelector::Call(target),
                                }
                            }
                            _ => {
                                return Err(self.fail(
                                    annotation,
                                    DiagnosticKind::InvalidType,
                                    "branch join must select result.method() or result.await",
                                ));
                            }
                        }
                    } else {
                        CompletionContract::Unspecified
                    };
                    let id = BranchContractId(self.p.contracts.branches.len() as u32);
                    self.p.contracts.branches.push(BranchContract {
                        id,
                        instance,
                        function,
                        completion,
                        effects: self.p.declarations.instances[instance.0 as usize].effects,
                    });
                    contracts.push(ResolvedContract::Branch(id));
                }
                NodeKind::Annotation { .. } if self.annotation_name(annotation) == "lock" => {
                    if matches!(signature.receiver, ReceiverMode::None) {
                        return Err(self.fail(
                            annotation,
                            DiagnosticKind::InvalidType,
                            "lock contract requires an instance receiver",
                        ));
                    }
                    let mut duration = LockDuration::ThroughCall;
                    for property in self.properties(annotation) {
                        let NodeKind::Property { key, value } = self.kind(property) else {
                            unreachable!()
                        };
                        if self.property_key(*key) == "through_result"
                            && self.property_bool(*value)?
                        {
                            duration = LockDuration::ThroughResult;
                        }
                    }
                    let id = LockContractId(self.p.contracts.locks.len() as u32);
                    let origin = self.origin(annotation);
                    self.p.contracts.locks.push(LockContract {
                        id,
                        subject: ResolvedSubject::Receiver,
                        duration,
                        origin,
                    });
                    contracts.push(ResolvedContract::Lock(id));
                }
                _ => {
                    return Err(self.fail(
                        annotation,
                        DiagnosticKind::InvalidType,
                        "annotation is not valid on a function",
                    ));
                }
            }
        }
        self.p.declarations.instances[instance.0 as usize].contracts = contracts;
        Ok(())
    }
    pub(super) fn apply_call_contracts(
        &mut self,
        n: ast::NodeId,
        function: FunctionInstanceId,
        arguments: &[ValueId],
        result: ValueId,
        site: &OperationSite,
    ) -> Result<()> {
        let received = *site
            .execution_moments
            .rest
            .last()
            .unwrap_or(&site.execution_moments.first);
        for contract in self.p.declarations.instances[function.0 as usize]
            .contracts
            .clone()
        {
            match contract {
                ResolvedContract::Lock(contract) => {
                    let receiver = arguments[0];
                    let identity = LockIdentityId(self.p.contracts.lock_identities.len() as u32);
                    let targets = self
                        .references
                        .get(&receiver)
                        .map(|r| {
                            let origins = &self.p.objects.references[r.0 as usize].origins;
                            std::iter::once(&origins.first)
                                .chain(&origins.rest)
                                .cloned()
                                .collect()
                        })
                        .unwrap_or_default();
                    self.p.contracts.lock_identities.push(LockIdentity {
                        id: identity,
                        receiver,
                        targets,
                    });
                    let retained = matches!(
                        self.p.contracts.locks[contract.0 as usize].duration,
                        LockDuration::ThroughResult
                    );
                    self.p
                        .contracts
                        .applications
                        .push(ContractApplication::Lock {
                            call: site.id,
                            contract,
                            identity,
                            begins: site.execution_moments.first,
                            ends: if retained { None } else { Some(received) },
                            carried_by: if retained { Some(result) } else { None },
                        });
                    if retained {
                        let summary = self.p.values.entries[result.0 as usize].dependencies;
                        self.p.values.dependency_summaries[summary.0 as usize]
                            .dependencies
                            .push(DependencyRequirement::HoldsLock(identity));
                    }
                }
                ResolvedContract::Branch(contract) => {
                    self.apply_branch_contract(n, contract, result, site)?
                }
                _ => {}
            }
        }
        if let Some(receiver) = arguments.first() {
            for dependency in self.dependencies(*receiver) {
                if let DependencyRequirement::BranchCompletion(capability) = dependency {
                    let branch = self.p.contracts.completions[capability.0 as usize].branch;
                    let BranchKind::Concurrent(concurrent) =
                        &self.p.execution.branches[branch.0 as usize].kind
                    else {
                        continue;
                    };
                    let completion =
                        &self.p.contracts.branches[concurrent.contract.0 as usize].completion;
                    if matches!(completion,CompletionContract::ThroughResult{selector:ResolvedCompletionSelector::Call(target)}if *target==function)
                    {
                        self.p
                            .contracts
                            .applications
                            .push(ContractApplication::Completion {
                                call: site.id,
                                capability,
                                at: received,
                                guard: site.guard,
                            });
                    }
                }
            }
        }
        Ok(())
    }
    pub(super) fn apply_branch_contract(
        &mut self,
        n: ast::NodeId,
        contract: BranchContractId,
        result: ValueId,
        call: &OperationSite,
    ) -> Result<()> {
        let parent = self.ctx().clone();
        let child = BranchId(self.p.execution.branches.len() as u32);
        let timeline = TimelineId(self.p.execution.timelines.len() as u32);
        let capability = CompletionCapabilityId(self.p.contracts.completions.len() as u32);
        let domain = InstanceDomainId(self.p.execution.instance_domains.len() as u32);
        self.p.execution.instance_domains.push(InstanceDomain {
            id: domain,
            definition: InstanceDomainDefinition::Concurrent {
                parent: parent.domain,
                branch: child,
            },
        });
        self.p.execution.branches.push(Branch {
            id: child,
            timeline,
            kind: BranchKind::Concurrent(ConcurrentBranch {
                parent: parent.branch,
                start: call.id,
                contract,
                completion: capability,
            }),
        });
        let entry = ExecutionMomentId(self.p.execution.execution_moments.len() as u32);
        self.p.execution.timelines.push(Timeline {
            id: timeline,
            branch: child,
            lexical_order: vec![],
            execution_moments: vec![],
            entries: NonEmpty {
                first: entry,
                rest: vec![],
            },
            exits: vec![],
        });
        self.ctx = Some(Context {
            branch: child,
            timeline,
            domain,
            last: None,
            ..parent.clone()
        });
        let site = self.site(n, ExecutionPhase::EstablishEffect);
        self.emit(Operation::BeginBranch(BeginBranch {
            site: site.clone(),
            child,
            contract,
            capability,
        }));
        self.p
            .execution
            .relationships
            .push(BranchRelationship::Fork(BranchFork {
                parent: parent.branch,
                child,
                parent_moment: call.execution_moments.first,
                child_entry: entry,
            }));
        self.p.contracts.completions.push(CompletionCapability {
            id: capability,
            branch: child,
            carrier: CompletionCarrier::Result(result),
            established_at: vec![],
        });
        self.p
            .contracts
            .applications
            .push(ContractApplication::Branch {
                call: call.id,
                contract,
                capability,
                child,
                instance: domain,
            });
        self.ctx = Some(parent);
        let summary = self.p.values.entries[result.0 as usize].dependencies;
        self.p.values.dependency_summaries[summary.0 as usize]
            .dependencies
            .push(DependencyRequirement::BranchCompletion(capability));
        Ok(())
    }
    fn override_annotation(
        &mut self,
        n: ast::NodeId,
        scope: ScopeId,
        values: &HashMap<String, ast::NodeId>,
    ) -> Result<()> {
        // Implemented through resolved environment identities below, not mutable global constants.
        let _ = values;
        self.install_override(n, scope)
    }
    fn async_pool_annotation(
        &mut self,
        n: ast::NodeId,
        scope: ScopeId,
        values: &HashMap<String, ast::NodeId>,
    ) -> Result<()> {
        let table = *values.get("async_pool_sizes").ok_or_else(|| {
            self.fail(
                n,
                DiagnosticKind::InvalidType,
                "directive requires async_pool_sizes",
            )
        })?;
        let NodeKind::Module { items } = self.kind(table) else {
            return Err(self.fail(
                table,
                DiagnosticKind::InvalidType,
                "async_pool_sizes requires a capacity map",
            ));
        };
        for item in items {
            let NodeKind::Property { key, value } = self.kind(*item) else {
                unreachable!()
            };
            let NodeKind::Path { segments, .. } = self.kind(*key) else {
                unreachable!()
            };
            let symbol = self.scoped_path(*key, scope, segments)?;
            let SymbolDefinition::Function(function) =
                self.p.symbols.entries[symbol.0 as usize].definition
            else {
                return Err(self.fail(
                    *key,
                    DiagnosticKind::InvalidType,
                    "async capacity path must name a function",
                ));
            };
            let target = self.instance(function)?;
            let capacity = self.integer_constant(*value, scope)?;
            let origin = self.origin(*item);
            self.p
                .contracts
                .memory_configuration
                .push(MemoryConfiguration::AsyncPool(AsyncPoolCapacity {
                    function: target,
                    capacity,
                    origin,
                }));
        }
        self.cover(n, SyntaxDisposition::Boundary(scope));
        Ok(())
    }
}
