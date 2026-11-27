//! Closure environments and callable interfaces are resolved here, never downstream.
use super::*;
impl Resolver<'_> {
    pub(super) fn resolve_return_type(&mut self, n: ast::NodeId, actual: TypeId) -> Result<()> {
        if let Some(expected) = self.ctx().return_type {
            self.require_type(n, actual, expected)
        } else {
            self.ctx_mut().return_type = Some(actual);
            Ok(())
        }
    }
    fn local_pattern_names(&self, n: ast::NodeId, names: &mut HashSet<String>) {
        match self.kind(n) {
            NodeKind::Pattern(ast::PatternSyntax::Binding { name, .. }) => {
                names.insert(self.text(*name).to_owned());
            }
            NodeKind::Pattern(ast::PatternSyntax::Variant {
                path,
                positional: None,
                fields: None,
            }) => {
                if let NodeKind::Path { segments, .. } = self.kind(*path) {
                    if segments.len() == 1 {
                        names.insert(self.text(segments[0]).to_owned());
                    }
                }
            }
            _ => {
                for child in self.kind(n).children() {
                    self.local_pattern_names(child, names);
                }
            }
        }
    }
    fn capture_uses(
        &self,
        n: ast::NodeId,
        local: &mut HashSet<String>,
        captures: &mut Vec<BindingId>,
    ) {
        match self.kind(n) {
            NodeKind::Type(_) | NodeKind::Annotation { .. } | NodeKind::Pattern(_) => {}
            NodeKind::Path { segments, .. } if segments.len() == 1 => {
                let name = self.text(segments[0]);
                if !local.contains(name) {
                    if let Some(symbol) = self.lookup(self.ctx().scope, name) {
                        if let SymbolDefinition::Binding(binding) =
                            self.p.symbols.entries[symbol.0 as usize].definition
                        {
                            if !captures.contains(&binding) {
                                captures.push(binding);
                            }
                        }
                    }
                }
            }
            NodeKind::Let { pattern, value, .. } => {
                self.capture_uses(*value, local, captures);
                self.local_pattern_names(*pattern, local);
            }
            NodeKind::Block {
                statements, result, ..
            } => {
                let mut block = local.clone();
                for statement in statements {
                    self.capture_uses(*statement, &mut block, captures);
                }
                if let Some(result) = result {
                    self.capture_uses(*result, &mut block, captures);
                }
            }
            NodeKind::For {
                pattern,
                source,
                body,
            } => {
                self.capture_uses(*source, local, captures);
                let mut body_names = local.clone();
                self.local_pattern_names(*pattern, &mut body_names);
                self.capture_uses(*body, &mut body_names, captures);
            }
            NodeKind::MatchArm { pattern, body } => {
                let mut names = local.clone();
                self.local_pattern_names(*pattern, &mut names);
                self.capture_uses(*body, &mut names, captures);
            }
            NodeKind::If { condition, yes, no } => {
                let mut names = local.clone();
                if let NodeKind::LetCondition { pattern, value } = self.kind(*condition) {
                    self.capture_uses(*value, local, captures);
                    self.local_pattern_names(*pattern, &mut names);
                } else {
                    self.capture_uses(*condition, local, captures);
                }
                self.capture_uses(*yes, &mut names, captures);
                if let Some(no) = no {
                    self.capture_uses(*no, &mut local.clone(), captures);
                }
            }
            NodeKind::Closure {
                parameters, body, ..
            } => {
                let mut names = local.clone();
                for parameter in parameters {
                    if let NodeKind::Parameter { name, .. } = self.kind(*parameter) {
                        names.insert(self.text(*name).to_owned());
                    }
                }
                self.capture_uses(*body, &mut names, captures);
            }
            NodeKind::FieldInitializer { name, value: None } => {
                let name = self.text(*name);
                if !local.contains(name) {
                    if let Some(symbol) = self.lookup(self.ctx().scope, name) {
                        if let SymbolDefinition::Binding(binding) =
                            self.p.symbols.entries[symbol.0 as usize].definition
                        {
                            if !captures.contains(&binding) {
                                captures.push(binding);
                            }
                        }
                    }
                }
            }
            _ => {
                for child in self.kind(n).children() {
                    self.capture_uses(child, &mut local.clone(), captures);
                }
            }
        }
    }
    pub(super) fn capture_record(
        &mut self,
        n: ast::NodeId,
        moving: bool,
        parameters: &[ast::NodeId],
        body: ast::NodeId,
    ) -> Result<CaptureRecordId> {
        let mut locals = HashSet::new();
        for parameter in parameters {
            if let NodeKind::Parameter { name, .. } = self.kind(*parameter) {
                locals.insert(self.text(*name).to_owned());
            }
        }
        let mut used = vec![];
        self.capture_uses(body, &mut locals, &mut used);
        let scope = self.ctx().scope;
        let symbol = self.anonymous_symbol(
            "<capture-environment>",
            scope,
            SymbolDefinition::Type(self.unit),
            n,
        );
        let ty = self.intern(TypeKey::Nominal(symbol, vec![]));
        self.p.symbols.entries[symbol.0 as usize].definition = SymbolDefinition::Type(ty);
        let record = CaptureRecordId(self.p.contracts.captures.len() as u32);
        self.p.contracts.captures.push(CaptureRecord {
            id: record,
            ty,
            call: None,
            moving,
            captures: vec![],
        });
        let mut fields = vec![];
        for source in used {
            let binding = self.p.scopes.bindings[source.0 as usize].clone();
            let name = self.p.symbols.entries[binding.symbol.0 as usize]
                .spelling
                .clone();
            let field = FieldId(self.p.declarations.fields.len() as u32);
            let symbol = self.anonymous_symbol(&name, scope, SymbolDefinition::Field(field), n);
            self.p.declarations.fields.push(FieldDefinition {
                id: field,
                symbol,
                ty: binding.ty,
                default: FieldDefault::Unavailable,
            });
            fields.push(field);
            let definition = self.place(PlaceRoot::Binding(source), vec![], binding.ty);
            let place = self.evaluated_place(n, definition, vec![]);
            let shared = matches!(
                self.p.types.entries[binding.ty.0 as usize].kind,
                TypeDefinition::Reference {
                    permission: ReferencePermission::Shared,
                    ..
                }
            );
            let (value, mode) = if shared {
                let original = self.read_place(n, place)?.value;
                let site = self.site(n, ExecutionPhase::Receive);
                let value = self.op_value(&site, binding.ty, self.dependencies(original));
                self.forward_summaries(original, value);
                self.clone_reference_identity(original, value, &site);
                self.emit(Operation::CaptureCopy(CaptureCopy {
                    site,
                    record,
                    source,
                    field,
                    value,
                }));
                (value, CaptureMode::SharedReferenceCopy)
            } else {
                let value = self.load(n, place)?.value;
                let site = self.site(n, ExecutionPhase::TransferOwnership);
                let mode = if matches!(
                    self.transfer_kind(binding.ty),
                    TransferKind::ByTypeParameter(_)
                ) {
                    CaptureMode::ByTypeParameter(binding.ty)
                } else if self.primitive(binding.ty) {
                    CaptureMode::PrimitiveCopy
                } else if self.enum_copy(binding.ty) {
                    CaptureMode::EligibleEnumCopy
                } else {
                    CaptureMode::Move
                };
                if matches!(mode, CaptureMode::ByTypeParameter(_)) {
                    self.emit(Operation::CaptureParametric(CaptureParametric {
                        site,
                        record,
                        source,
                        field,
                        value,
                        ty: binding.ty,
                        moving,
                    }));
                } else if matches!(mode, CaptureMode::Move) {
                    self.emit(Operation::CaptureMove(CaptureMove {
                        site,
                        record,
                        source,
                        field,
                        value,
                    }));
                } else {
                    self.emit(Operation::CaptureCopy(CaptureCopy {
                        site,
                        record,
                        source,
                        field,
                        value,
                    }));
                }
                (value, mode)
            };
            let creation = self.ctx().last.unwrap();
            self.p.contracts.captures[record.0 as usize]
                .captures
                .push(Capture {
                    field,
                    source,
                    value,
                    mode,
                    creation,
                });
        }
        self.p.declarations.structs.push(StructDefinition {
            symbol,
            ty,
            parameters: vec![],
            fields,
            methods: vec![],
        });
        Ok(record)
    }
    pub(super) fn clone_reference_identity(
        &mut self,
        source: ValueId,
        value: ValueId,
        site: &OperationSite,
    ) {
        if let Some(reference) = self.references.get(&source).copied() {
            let mut definition = self.p.objects.references[reference.0 as usize].clone();
            definition.id = ReferenceId(self.p.objects.references.len() as u32);
            definition.ty = self.vtype(value);
            definition.initial_owner = Owner::Scope {
                scope: site.scope,
                instance: self.ctx().domain,
            };
            definition.creation = ObjectCreation::At(site.execution_moments.first);
            definition.created_in = site.scope;
            self.references.insert(value, definition.id);
            self.value_entities
                .insert(value, EntityId::Reference(definition.id));
            self.p.objects.references.push(definition);
        }
    }

    /// Give a control-flow result one stable reference identity whose guarded
    /// origins are the reference values reaching that result. Consumers must
    /// not reconstruct this relation from the source branches later.
    pub(super) fn merge_reference_identities(
        &mut self,
        value: ValueId,
        incoming: &[GuardedValue],
        site: &OperationSite,
    ) {
        let TypeDefinition::Reference { permission, .. } = self.p.types.entries
            [self.vtype(value).0 as usize]
            .kind
            .clone()
        else {
            return;
        };

        let existing = self.references.get(&value).copied();
        let mut origins = Vec::new();
        for incoming in incoming {
            let Some(source) = self.references.get(&incoming.value).copied() else {
                continue;
            };
            if Some(source) == existing {
                continue;
            }
            let definition = self.p.objects.references[source.0 as usize].clone();
            for origin in std::iter::once(definition.origins.first).chain(definition.origins.rest) {
                let guard = self.predicate(PredicateKind::All(vec![incoming.guard, origin.guard]));
                origins.push(ReferenceOrigin {
                    target: origin.target,
                    parent: Some(source),
                    guard,
                });
            }
        }
        if origins.is_empty() {
            return;
        }

        if let Some(reference) = existing {
            let definition = &mut self.p.objects.references[reference.0 as usize];
            for origin in origins {
                if !std::iter::once(&definition.origins.first)
                    .chain(&definition.origins.rest)
                    .any(|old| {
                        old.target == origin.target
                            && old.parent == origin.parent
                            && old.guard == origin.guard
                    })
                {
                    definition.origins.rest.push(origin);
                }
            }
            return;
        }

        let mut origins = origins.into_iter();
        let first = origins.next().expect("origins are non-empty");
        let reference = ReferenceId(self.p.objects.references.len() as u32);
        self.p.objects.references.push(Reference {
            id: reference,
            ty: self.vtype(value),
            created_in: site.scope,
            creation: ObjectCreation::At(site.execution_moments.first),
            initial_owner: Owner::Scope {
                scope: site.scope,
                instance: self.ctx().domain,
            },
            permission,
            formation: ReferenceFormation::FlowAlias,
            origins: NonEmpty {
                first,
                rest: origins.collect(),
            },
        });
        self.references.insert(value, reference);
        self.value_entities
            .insert(value, EntityId::Reference(reference));
    }
    pub(super) fn bind_capture_environment(
        &mut self,
        record: CaptureRecordId,
        site: &OperationSite,
    ) -> Result<()> {
        for capture in self.p.contracts.captures[record.0 as usize]
            .captures
            .clone()
        {
            let source = self.p.scopes.bindings[capture.source.0 as usize].clone();
            let name = self.p.symbols.entries[source.symbol.0 as usize]
                .spelling
                .clone();
            let binding = BindingId(self.p.scopes.bindings.len() as u32);
            let scope = self.ctx().scope;
            let symbol = self.declare(
                self.ctx().instruction,
                scope,
                &name,
                SymbolDefinition::Binding(binding),
            )?;
            self.p.scopes.bindings.push(Binding {
                id: binding,
                symbol,
                ty: source.ty,
                scope,
                mutable: source.mutable,
                introduced: BindingIntroduction::Capture {
                    record,
                    field: capture.field,
                },
            });
            self.p.scopes.entries[scope.0 as usize]
                .bindings
                .push(binding);
            let value = self.value(
                source.ty,
                ValueDefinition::CaptureField {
                    record,
                    field: capture.field,
                },
                ProvenanceKind::Binding(binding),
                vec![DependencyRequirement::CapturedField {
                    record,
                    field: capture.field,
                }],
            );
            self.ctx_mut().bindings.insert(binding, value);
            if let TypeDefinition::Reference { target, permission } =
                self.p.types.entries[source.ty.0 as usize].kind.clone()
            {
                let place = self.place(
                    PlaceRoot::Binding(binding),
                    vec![PlaceProjection::Dereference],
                    target,
                );
                let reference = ReferenceId(self.p.objects.references.len() as u32);
                self.p.objects.references.push(Reference {
                    id: reference,
                    ty: source.ty,
                    permission,
                    formation: ReferenceFormation::Loan,
                    created_in: scope,
                    creation: ObjectCreation::At(site.execution_moments.first),
                    initial_owner: self.binding_owner(binding),
                    origins: NonEmpty {
                        first: ReferenceOrigin {
                            target: place,
                            parent: None,
                            guard: site.guard,
                        },
                        rest: vec![],
                    },
                });
                self.references.insert(value, reference);
                self.binding_entities
                    .insert(binding, EntityId::Reference(reference));
            }
        }
        Ok(())
    }
    pub(super) fn capturing_expression(
        &mut self,
        n: ast::NodeId,
        moving: bool,
        parameters: &[ast::NodeId],
        result: Option<ast::NodeId>,
        body: ast::NodeId,
        _expected: Option<TypeId>,
        asynchronous: bool,
    ) -> Result<Expr> {
        let record = self.capture_record(n, moving, parameters, body)?;
        let scope = self.declaration_scope(
            n,
            self.ctx().scope,
            ScopeContext::Module(self.module_for_scope(self.ctx().scope)),
        );
        let mut params = vec![];
        for parameter in parameters {
            let NodeKind::Parameter {
                name,
                ty: Some(ty),
                mutable,
                ..
            } = self.kind(*parameter)
            else {
                unreachable!()
            };
            params.push((
                self.text(*name).to_owned(),
                self.type_syntax(*ty, scope)?,
                mutable.is_some(),
            ));
        }
        let result_type = result
            .map(|ty| self.type_syntax(ty, scope))
            .transpose()?
            .unwrap_or(self.never);
        let signature = self.signature(
            params.iter().map(|p| p.1).collect(),
            result_type,
            ReceiverMode::None,
            if asynchronous {
                FunctionExecution::Asynchronous
            } else {
                FunctionExecution::Synchronous
            },
        );
        let mut symbolic_types = params.iter().map(|p| p.1).collect::<Vec<_>>();
        symbolic_types.push(result_type);
        symbolic_types.extend(
            self.p.contracts.captures[record.0 as usize]
                .captures
                .iter()
                .map(|c| self.p.declarations.fields[c.field.0 as usize].ty),
        );
        let free_parameters = self
            .p
            .types
            .parameters
            .iter()
            .filter(|p| {
                symbolic_types
                    .iter()
                    .any(|ty| self.type_parameter_occurs(*ty, p.id))
            })
            .map(|p| p.id)
            .collect::<Vec<_>>();
        let function = FunctionId(self.p.declarations.functions.len() as u32);
        assert_eq!(function.0 as usize, self.functions.len());
        let symbol = self.anonymous_symbol(
            "<closure-call>",
            scope,
            SymbolDefinition::Function(function),
            n,
        );
        let origin = self.origin(n);
        self.p.declarations.functions.push(FunctionDefinition {
            parametric_body: None,
            id: function,
            symbol,
            signature,
            type_parameters: free_parameters.clone(),
            body: FunctionImplementation::Template {
                origin,
                syntax: self.syntax_id(n),
            },
            contracts: vec![],
        });
        self.functions.push(FunctionSource {
            unit: self.current_unit,
            node: n,
            scope,
            owner: None,
            signature,
            parameters: params,
            result: result_type,
            body: Some(body),
            captures: Some(record),
            infer_result: result.is_none(),
            annotations: vec![],
            parameter_syntax: parameters
                .iter()
                .map(|p| match self.kind(*p) {
                    NodeKind::Parameter { ty, .. } => *ty,
                    _ => None,
                })
                .collect(),
            result_syntax: result,
        });
        let actual = free_parameters
            .iter()
            .map(|p| self.intern(TypeKey::Parameter(*p)))
            .collect();
        let call = self.specialized_instance(function, actual)?;
        if !free_parameters.is_empty() {
            self.p.declarations.functions[function.0 as usize].parametric_body = Some(call);
        }
        self.p.contracts.captures[record.0 as usize].call = Some(call);
        if asynchronous {
            return self.make_future(n, call, Some(record), vec![]);
        }
        let signature = self.p.declarations.instances[call.0 as usize].signature;
        let ty = TypeId(self.p.types.entries.len() as u32);
        self.p.types.entries.push(ResolvedType {
            id: ty,
            kind: TypeDefinition::Closure {
                signature,
                captures: record,
            },
        });
        let site = self.site(n, ExecutionPhase::Compute);
        let captures: Vec<_> = self.p.contracts.captures[record.0 as usize]
            .captures
            .iter()
            .map(|c| c.value)
            .collect();
        let dependencies = captures
            .iter()
            .flat_map(|v| self.dependencies(*v))
            .collect();
        let result = self.op_value(&site, ty, dependencies);
        self.components.insert(result, captures);
        let body = self.p.declarations.instances[call.0 as usize].body.unwrap();
        self.emit(Operation::CreateClosure(CreateClosure {
            site,
            captures: record,
            body,
            result,
        }));
        Ok(Expr { value: result })
    }
    pub(super) fn callable_type(&mut self, parameters: Vec<TypeId>, result: TypeId) -> TypeId {
        if let Some(ty) = self.p.types.entries.iter().find(|ty| {
            if let TypeDefinition::Callable(signature) = ty.kind {
                let signature = &self.p.declarations.signatures[signature.0 as usize];
                signature.result == result
                    && signature.parameters.len() == parameters.len()
                    && signature
                        .parameters
                        .iter()
                        .zip(&parameters)
                        .all(|(a, b)| a.ty == *b)
            } else {
                false
            }
        }) {
            return ty.id;
        }
        let signature = self.signature(
            parameters,
            result,
            ReceiverMode::None,
            FunctionExecution::Synchronous,
        );
        self.intern(TypeKey::Callable(signature))
    }
    pub(super) fn callable_signature(
        &self,
        ty: TypeId,
    ) -> Option<(SignatureId, Option<CaptureRecordId>)> {
        match self.p.types.entries[ty.0 as usize].kind {
            TypeDefinition::Callable(signature) => Some((signature, None)),
            TypeDefinition::Closure {
                signature,
                captures,
            } => Some((signature, Some(captures))),
            _ => None,
        }
    }
    fn same_call_signature(&self, a: SignatureId, b: SignatureId) -> bool {
        let a = &self.p.declarations.signatures[a.0 as usize];
        let b = &self.p.declarations.signatures[b.0 as usize];
        a.result == b.result
            && a.parameters.len() == b.parameters.len()
            && a.parameters
                .iter()
                .zip(&b.parameters)
                .all(|(a, b)| a.ty == b.ty)
            && std::mem::discriminant(&a.execution) == std::mem::discriminant(&b.execution)
    }
    pub(super) fn adapt_callable(
        &mut self,
        n: ast::NodeId,
        expression: Expr,
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        let Some(expected) = expected else {
            return Ok(expression);
        };
        let actual = self.vtype(expression.value);
        if actual == expected || actual == self.never {
            return Ok(expression);
        }
        let (a, b) = match (
            &self.p.types.entries[actual.0 as usize].kind,
            &self.p.types.entries[expected.0 as usize].kind,
        ) {
            (
                TypeDefinition::Reference {
                    target: a,
                    permission: ap,
                },
                TypeDefinition::Reference {
                    target: b,
                    permission: bp,
                },
            ) if std::mem::discriminant(ap) == std::mem::discriminant(bp) => (*a, *b),
            _ => (actual, expected),
        };
        let (Some((a, _)), Some((b, _))) = (self.callable_signature(a), self.callable_signature(b))
        else {
            return Ok(expression);
        };
        if !self.same_call_signature(a, b) {
            return Err(self.fail(
                n,
                DiagnosticKind::TypeMismatch,
                "callable parameter or result signature differs from the expected fn type",
            ));
        }
        // No implicit borrow: source and target must have the same reference shape.
        if matches!(
            self.p.types.entries[actual.0 as usize].kind,
            TypeDefinition::Reference { .. }
        ) != matches!(
            self.p.types.entries[expected.0 as usize].kind,
            TypeDefinition::Reference { .. }
        ) {
            return Err(self.fail(
                n,
                DiagnosticKind::TypeMismatch,
                "passing a callable by reference requires an explicit borrow",
            ));
        }
        let site = self.site(n, ExecutionPhase::Receive);
        let result = self.op_value(&site, expected, self.dependencies(expression.value));
        self.forward_summaries(expression.value, result);
        self.clone_reference_identity(expression.value, result, &site);
        self.emit(Operation::AdaptCallable(AdaptCallable {
            site,
            source: expression.value,
            signature: b,
            result,
        }));
        Ok(Expr { value: result })
    }
    pub(super) fn callable_invocation(
        &mut self,
        n: ast::NodeId,
        callee: ast::NodeId,
        arguments: &[ast::NodeId],
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        let (callable, mode) = if self.is_place_syntax(callee) {
            let original = self.place_expression(callee)?;
            return self.invoke_callable_place(n, original, arguments, expected);
        } else {
            let value = self.expression(callee, None)?.value;
            (value, ReceiverMode::ByValue(self.vtype(value)))
        };
        self.invoke_callable_value(n, callable, mode, arguments, expected)
    }
    pub(super) fn invoke_callable_place(
        &mut self,
        n: ast::NodeId,
        original: EvaluatedPlaceId,
        arguments: &[ast::NodeId],
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        let definition = self.p.objects.evaluated_places[original.0 as usize].definition;
        let place = self.p.objects.places[definition.0 as usize].clone();
        let mode = match self.p.types.entries[place.ty.0 as usize].kind {
            TypeDefinition::Reference {
                target,
                permission: ReferencePermission::Mutable,
            } => ReceiverMode::Mutable(target),
            TypeDefinition::Reference { target, .. } => ReceiverMode::Shared(target),
            _ => match place.root {
                PlaceRoot::Binding(binding)
                    if self.p.scopes.bindings[binding.0 as usize].mutable =>
                {
                    ReceiverMode::Mutable(place.ty)
                }
                _ => ReceiverMode::Shared(place.ty),
            },
        };
        let place = self.deref_place(n, original)?;
        let callable = self.read_place(n, place)?.value;
        self.invoke_callable_value(n, callable, mode, arguments, expected)
    }
    fn invoke_callable_value(
        &mut self,
        n: ast::NodeId,
        callable: ValueId,
        mode: ReceiverMode,
        arguments: &[ast::NodeId],
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        let (signature, _) = self
            .callable_signature(self.vtype(callable))
            .ok_or_else(|| {
                self.fail(
                    n,
                    DiagnosticKind::InvalidCall,
                    "expression has no callable signature",
                )
            })?;
        let shape = self.p.declarations.signatures[signature.0 as usize].clone();
        if shape.parameters.len() != arguments.len() {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "callable argument count differs from its signature",
            ));
        }
        let mut args = vec![];
        for (index, (argument, parameter)) in arguments.iter().zip(&shape.parameters).enumerate() {
            let value = self.expression(*argument, Some(parameter.ty))?.value;
            self.require_type(*argument, self.vtype(value), parameter.ty)?;
            args.push(CallArgument {
                parameter_index: index as u32,
                value,
                transfer: self.transfer_kind(parameter.ty),
            });
        }
        if let Some(expected) = expected {
            self.require_type(n, shape.result, expected)?;
        }
        let mut site = self.site(n, ExecutionPhase::Invoke);
        self.phase(&mut site, ExecutionPhase::Receive);
        let result = self.op_value(
            &site,
            shape.result,
            vec![DependencyRequirement::CallableResult {
                callable,
                arguments: args.iter().map(|a| a.value).collect(),
            }],
        );
        let effects = self.effects(
            &site,
            vec![Effect::InvokeCallable {
                callable,
                signature,
                arguments: args.clone(),
            }],
        );
        self.emit(Operation::CallableCall(CallableCall {
            site,
            target: ResolvedCallableCall {
                callable,
                signature,
                mode,
            },
            arguments: args,
            result,
            effects,
        }));
        self.attach_result_reference(result, n);
        Ok(Expr { value: result })
    }
    pub(super) fn attach_result_reference(&mut self, value: ValueId, _n: ast::NodeId) {
        if let TypeDefinition::Reference { target, permission } = self.p.types.entries
            [self.vtype(value).0 as usize]
            .kind
            .clone()
        {
            let ValueDefinition::OperationResult { produced_at, .. } =
                self.p.values.entries[value.0 as usize].definition
            else {
                unreachable!()
            };
            let scope = self.ctx().scope;
            let place = self.place(
                PlaceRoot::Value(value),
                vec![PlaceProjection::Dereference],
                target,
            );
            let reference = ReferenceId(self.p.objects.references.len() as u32);
            self.p.objects.references.push(Reference {
                id: reference,
                ty: self.vtype(value),
                permission,
                formation: ReferenceFormation::Loan,
                created_in: scope,
                creation: ObjectCreation::At(produced_at),
                initial_owner: Owner::Scope {
                    scope,
                    instance: self.ctx().domain,
                },
                origins: NonEmpty {
                    first: ReferenceOrigin {
                        target: place,
                        parent: None,
                        guard: self.ctx().guard,
                    },
                    rest: vec![],
                },
            });
            self.references.insert(value, reference);
            self.value_entities
                .insert(value, EntityId::Reference(reference));
        }
    }
}
