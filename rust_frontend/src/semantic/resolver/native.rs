//! Existing compiler-owned types and operations. Dispatch is by resolved identity.
use super::*;
#[derive(Clone, Copy)]
pub(super) enum NativeConstructor {
    Pool,
    Allocation,
    Vector,
    HashMap,
    String,
    Handle(bool),
}
impl Resolver<'_> {
    pub(super) fn install_native_types(&mut self) {
        for (name, constructor) in [
            ("Pool", NativeConstructor::Pool),
            ("A", NativeConstructor::Allocation),
            ("Vector", NativeConstructor::Vector),
            ("HashMap", NativeConstructor::HashMap),
            ("String", NativeConstructor::String),
        ] {
            let symbol = self.compiler_symbol(name, ScopeId(0), SymbolDefinition::Type(self.unit));
            self.native_constructors.insert(symbol, constructor);
        }
        let module = ModuleId(self.p.declarations.modules.len() as u32);
        let scope = self.declaration_scope(
            self.syntax.ast.root,
            ScopeId(0),
            ScopeContext::Module(module),
        );
        self.runtime_scope = scope;
        self.p.declarations.modules.push(ModuleDefinition {
            id: module,
            package: PackageId(0),
            path: vec!["runtime".into()],
            scope,
        });
        self.p.declarations.packages[0].modules.push(module);
        self.compiler_symbol("runtime", ScopeId(0), SymbolDefinition::Module(module));
        for (name, kind) in [
            ("spawn", RuntimeLaunchKind::Spawn),
            ("spawn_blocking", RuntimeLaunchKind::SpawnBlocking),
            ("thread", RuntimeLaunchKind::Thread),
        ] {
            let symbol = self.compiler_symbol(name, scope, SymbolDefinition::Type(self.unit));
            self.runtime_intrinsics.insert(symbol, kind);
        }
        for (name, kind) in [
            ("process_args", RuntimePrimitiveKind::ProcessArgs),
            ("wait_mutex", RuntimePrimitiveKind::WaitMutex),
            ("wait_channel", RuntimePrimitiveKind::WaitChannel),
            ("wait_socket", RuntimePrimitiveKind::WaitSocket),
            ("attach_socket", RuntimePrimitiveKind::AttachSocket),
            ("complete_socket", RuntimePrimitiveKind::CompleteSocket),
        ] {
            self.compiler_symbol(name, scope, SymbolDefinition::RuntimePrimitive(kind));
        }
        for (name, asynchronous) in [("Handle", false), ("AsyncHandle", true)] {
            let symbol = self.compiler_symbol(name, scope, SymbolDefinition::Type(self.unit));
            self.native_constructors
                .insert(symbol, NativeConstructor::Handle(asynchronous));
        }
        let error = self.prelude_enum("<runtime-error>", &[], &[("LaunchFailed", None)]);
        self.names[0].remove("LaunchFailed");
        self.runtime_error = match self.p.symbols.entries[error.0 as usize].definition {
            SymbolDefinition::Type(ty) => ty,
            _ => unreachable!(),
        };
        self.names[scope.0 as usize].insert("Error".into(), error);
        let error = self.prelude_enum("PoolError", &[], &[("Full", None)]);
        self.names[0].remove("Full");
        self.pool_error = match self.p.symbols.entries[error.0 as usize].definition {
            SymbolDefinition::Type(ty) => ty,
            _ => unreachable!(),
        };
        let error = self.prelude_enum(
            "SliceError",
            &[],
            &[("OutOfBounds", None), ("NotCharBoundary", None)],
        );
        self.names[0].remove("OutOfBounds");
        self.names[0].remove("NotCharBoundary");
        self.slice_error = match self.p.symbols.entries[error.0 as usize].definition {
            SymbolDefinition::Type(ty) => ty,
            _ => unreachable!(),
        };
    }
    pub(super) fn native_type(
        &mut self,
        n: ast::NodeId,
        constructor: NativeConstructor,
        args: &[ast::NodeId],
        scope: ScopeId,
        expected: Option<TypeId>,
    ) -> Result<TypeId> {
        if matches!(constructor, NativeConstructor::String) {
            return if args.is_empty() {
                Ok(self.intern(TypeKey::String))
            } else if args.len() == 1 {
                let size = self.integer_constant(args[0], scope)?;
                Ok(self.intern(TypeKey::InlineString(size)))
            } else {
                Err(self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    "String accepts at most one byte-capacity argument",
                ))
            };
        }
        if args.is_empty() {
            if let Some(expected) = expected {
                let valid = matches!(
                    (constructor, &self.p.types.entries[expected.0 as usize].kind),
                    (NativeConstructor::Pool, TypeDefinition::Pool { .. })
                        | (
                            NativeConstructor::Allocation,
                            TypeDefinition::Allocation { .. }
                        )
                        | (
                            NativeConstructor::Vector,
                            TypeDefinition::GrowingSequence { .. }
                        )
                        | (
                            NativeConstructor::HashMap,
                            TypeDefinition::KeyedCollection { .. }
                        )
                        | (
                            NativeConstructor::Handle(_),
                            TypeDefinition::ExecutionHandle { .. }
                        )
                );
                if valid {
                    return Ok(expected);
                }
            }
        }
        let count = if matches!(constructor, NativeConstructor::HashMap) {
            2
        } else {
            1
        };
        if args.len() != count {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                format!("native type requires {count} type argument(s)"),
            ));
        }
        let mut types = vec![];
        for arg in args {
            types.push(self.type_syntax(*arg, scope)?);
        }
        Ok(self.intern(match constructor {
            NativeConstructor::Pool => TypeKey::Pool(types[0]),
            NativeConstructor::Allocation => TypeKey::Allocation(types[0]),
            NativeConstructor::Vector => TypeKey::Vector(types[0]),
            NativeConstructor::HashMap => TypeKey::HashMap(types[0], types[1]),
            NativeConstructor::Handle(a) => TypeKey::Handle(types[0], a),
            NativeConstructor::String => unreachable!(),
        }))
    }
    pub(super) fn native_call(
        &mut self,
        n: ast::NodeId,
        callee: ast::NodeId,
        args: &[ast::NodeId],
        expected: Option<TypeId>,
    ) -> Result<Option<Expr>> {
        match self.kind(callee) {
            NodeKind::Path {
                segments,
                arguments,
            } => {
                if let Ok(symbol) = self.path_symbol(callee, segments) {
                    if let SymbolDefinition::RuntimePrimitive(kind) =
                        self.p.symbols.entries[symbol.0 as usize].definition
                    {
                        return self.runtime_primitive(n, kind, args).map(Some);
                    }
                    if let Some(kind) = self.runtime_intrinsics.get(&symbol).copied() {
                        return self.runtime_launch(n, kind, args).map(Some);
                    }
                }
                if segments.len() < 2 {
                    return Ok(None);
                }
                let symbol = match self.scoped_path(
                    callee,
                    self.ctx().scope,
                    &segments[..segments.len() - 1],
                ) {
                    Ok(symbol) => symbol,
                    Err(_) => return Ok(None),
                };
                if let SymbolDefinition::Type(ty) =
                    self.p.symbols.entries[symbol.0 as usize].definition
                {
                    let name = self.text(*segments.last().unwrap()).to_owned();
                    if let Some(result) = self.primitive_associated(n, ty, &name, args)? {
                        return Ok(Some(result));
                    }
                }
                let Some(constructor) = self.native_constructors.get(&symbol).copied() else {
                    return Ok(None);
                };
                let ty =
                    self.native_type(callee, constructor, arguments, self.ctx().scope, expected)?;
                let name = self.text(*segments.last().unwrap());
                if name != "new" {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidCall,
                        format!("native associated operation '{name}' has no registered signature"),
                    ));
                }
                self.native_new(n, ty, args).map(Some)
            }
            _ => Ok(None),
        }
    }
    pub(super) fn is_native_receiver(&self, ty: TypeId) -> bool {
        match self.p.types.entries[ty.0 as usize].kind {
            TypeDefinition::Reference { target, .. } => self.is_native_receiver(target),
            TypeDefinition::Pool { .. }
            | TypeDefinition::GrowingSequence { .. }
            | TypeDefinition::KeyedCollection { .. }
            | TypeDefinition::GrowingString
            | TypeDefinition::InlineUtf8 { .. }
            | TypeDefinition::Allocation { .. }
            | TypeDefinition::ExecutionHandle { .. } => true,
            _ => false,
        }
    }
    fn native_new(&mut self, n: ast::NodeId, ty: TypeId, args: &[ast::NodeId]) -> Result<Expr> {
        if let TypeDefinition::Pool { element } = self.p.types.entries[ty.0 as usize].kind {
            if args.len() != 1 {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidCall,
                    "Pool::new requires one capacity",
                ));
            }
            let usize_ty = self.intern(TypeKey::Numeric(NumericType::Usize));
            let capacity = self.expression(args[0], Some(usize_ty))?.value;
            let site = self.site(n, ExecutionPhase::Compute);
            let result = self.op_value(&site, ty, vec![]);
            self.materialize_value(
                result,
                Owner::Scope {
                    scope: site.scope,
                    instance: self.ctx().domain,
                },
                &site,
            );
            let EntityId::Address(address) = self.value_entities[&result] else {
                unreachable!()
            };
            let storage = self.p.objects.addresses[address.0 as usize].storage;
            self.emit(Operation::CreatePool(CreatePool {
                site,
                element,
                capacity,
                storage,
                result,
            }));
            return Ok(Expr { value: result });
        }
        if !matches!(
            self.p.types.entries[ty.0 as usize].kind,
            TypeDefinition::GrowingSequence { .. }
                | TypeDefinition::KeyedCollection { .. }
                | TypeDefinition::GrowingString
                | TypeDefinition::InlineUtf8 { .. }
        ) {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "this native type has no public new() constructor",
            ));
        }
        if !args.is_empty() {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "empty collection construction takes no arguments",
            ));
        }
        let site = self.site(n, ExecutionPhase::Compute);
        let result = self.op_value(&site, ty, vec![]);
        self.materialize_value(
            result,
            Owner::Scope {
                scope: site.scope,
                instance: self.ctx().domain,
            },
            &site,
        );
        let EntityId::Address(descriptor) = self.value_entities[&result] else {
            unreachable!()
        };
        let collection = CollectionId(self.p.objects.collections.len() as u32);
        self.p.objects.collections.push(Collection {
            id: collection,
            ty,
            descriptor: CollectionDescriptor::Address(descriptor),
            created_in: site.scope,
            initial_owner: Some(Owner::Scope {
                scope: site.scope,
                instance: self.ctx().domain,
            }),
            constraints: vec![],
        });
        self.p.objects.ownership.push(OwnershipLink {
            entity: EntityId::Collection(collection),
            owner: Owner::Entity(EntityOccurrence {
                entity: EntityId::Address(descriptor),
                instance: self.ctx().domain,
            }),
            scope: site.scope,
            established: site.execution_moments.first,
            guard: site.guard,
        });
        let effects = self.effects(&site, vec![]);
        self.emit(Operation::NativeOperation(NativeOperation {
            site,
            kind: NativeOperationKind::Construct { ty },
            arguments: vec![],
            result,
            effects,
        }));
        Ok(Expr { value: result })
    }
    pub(super) fn native_method(
        &mut self,
        n: ast::NodeId,
        original: EvaluatedPlaceId,
        name: &str,
        args: &[ast::NodeId],
    ) -> Result<Expr> {
        let original_definition = self.p.objects.evaluated_places[original.0 as usize].definition;
        let original_type = self.p.objects.places[original_definition.0 as usize].ty;
        let base = self.deref_place(n, original)?;
        let definition = self.p.objects.evaluated_places[base.0 as usize].definition;
        let ty = self.p.objects.places[definition.0 as usize].ty;
        if matches!(name, "ref" | "mut_ref") {
            if !args.is_empty() {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidCall,
                    "reference helpers take no arguments",
                ));
            }
            let target = if matches!(
                self.p.types.entries[original_type.0 as usize].kind,
                TypeDefinition::Allocation { .. }
            ) {
                base
            } else {
                original
            };
            return self.borrow(n, target, name == "mut_ref");
        }
        if matches!(
            self.p.types.entries[ty.0 as usize].kind,
            TypeDefinition::StrData
        ) {
            if name == "as_bytes" && args.is_empty() {
                let byte = self.intern(TypeKey::Numeric(NumericType::U8));
                let target = self.intern(TypeKey::Slice(byte));
                return self.primitive_view(n, base, target, false);
            }
            if name == "len" && args.is_empty() {
                let (_, value) = self.sequence_info(n, base)?;
                return Ok(Expr { value });
            }
        }
        if name == "try_slice"
            && args.len() == 1
            && matches!(self.kind(args[0]), NodeKind::Range { .. })
        {
            return self.try_text_slice(n, base, args[0]);
        }
        let source = self.read_place(n, original)?.value;
        if let TypeDefinition::ExecutionHandle { asynchronous, .. } =
            self.p.types.entries[ty.0 as usize].kind
        {
            if name != "join" || !args.is_empty() || asynchronous {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidCall,
                    "Handle exposes join(); AsyncHandle is awaited",
                ));
            }
            let protocol = self.handle_protocol(ty)?;
            let instance = protocol.join.unwrap();
            let definition = self.p.declarations.instances[instance.0 as usize].definition;
            let receiver = self.load(n, original)?.value;
            return self.invoke_function(n, definition, Some(receiver), &[], &[], None);
        }
        if let TypeDefinition::Pool { element } = self.p.types.entries[ty.0 as usize].kind {
            if !matches!(name, "new" | "try") || args.len() > 1 {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidCall,
                    "pool allocation accepts zero or one initializer",
                ));
            }
            let content = if let Some(arg) = args.first() {
                self.expression(*arg, Some(element))?.value
            } else {
                self.default_value(n, element)?
            };
            self.require_type(n, self.vtype(content), element)?;
            let allocation_type = self.intern(TypeKey::Allocation(element));
            let output = if name == "try" {
                self.result_type(allocation_type, self.pool_error)
            } else {
                allocation_type
            };
            self.ensure_nominal(output, n)?;
            let site = self.site(n, ExecutionPhase::Receive);
            let result = self.op_value(&site, output, vec![]);
            let success = if name == "try" {
                let enumeration = self
                    .p
                    .declarations
                    .enums
                    .iter()
                    .find(|e| e.ty == output)
                    .unwrap();
                let variant = enumeration.variants.first;
                self.predicate(PredicateKind::Variant {
                    value: result,
                    variant,
                })
            } else {
                site.guard
            };
            let allocation = if name == "try" {
                self.value(
                    allocation_type,
                    ValueDefinition::ConditionalResult {
                        operation: site.id,
                        produced_at: site.execution_moments.first,
                        guard: success,
                    },
                    ProvenanceKind::Constructed(site.id),
                    vec![DependencyRequirement::LiveTarget(definition)],
                )
            } else {
                result
            };
            if name != "try" {
                let summary = self.p.values.entries[result.0 as usize].dependencies;
                self.p.values.dependency_summaries[summary.0 as usize]
                    .dependencies
                    .push(DependencyRequirement::LiveTarget(definition));
            }
            self.components.insert(allocation, vec![content]);
            let success_site = OperationSite {
                guard: success,
                ..site.clone()
            };
            self.materialize_value(
                allocation,
                Owner::Scope {
                    scope: site.scope,
                    instance: self.ctx().domain,
                },
                &success_site,
            );
            if let Some(EntityId::Address(content_address)) =
                self.value_entities.get(&content).cloned()
            {
                let storage = self.p.objects.addresses[content_address.0 as usize].storage;
                if name == "try" {
                    self.p.storage_origins[storage.0 as usize]
                        .pool_choices
                        .push(GuardedPoolOrigin {
                            guard: success,
                            pool: source,
                        });
                } else {
                    self.p.storage_origins[storage.0 as usize].pool = Some(source);
                }
            }
            if name == "try" {
                let result_shape = self
                    .p
                    .declarations
                    .enums
                    .iter()
                    .find(|enumeration| enumeration.ty == output)
                    .expect("result type was materialized above");
                let success_variant = result_shape.variants.first;
                let failure_variant = result_shape.variants.rest[0];
                let success_payload =
                    self.p.declarations.variants[success_variant.0 as usize].fields[0];
                let failure_payload =
                    self.p.declarations.variants[failure_variant.0 as usize].fields[0];
                let pool_full_variant = self
                    .p
                    .declarations
                    .enums
                    .iter()
                    .find(|enumeration| enumeration.ty == self.pool_error)
                    .expect("pool error is a prelude enum")
                    .variants
                    .first;
                self.materialize_value(
                    result,
                    Owner::Scope {
                        scope: site.scope,
                        instance: self.ctx().domain,
                    },
                    &site,
                );
                self.components.insert(result, vec![allocation]);
                if let Some(owner) = self.value_entities.get(&result).cloned() {
                    self.transfer(
                        allocation,
                        Owner::Entity(EntityOccurrence {
                            entity: owner,
                            instance: self.ctx().domain,
                        }),
                        &success_site,
                    );
                }
                let summary = self.p.values.entries[result.0 as usize].dependencies;
                self.p.values.dependency_summaries[summary.0 as usize]
                    .guarded
                    .push(GuardedDependency {
                        guard: success,
                        requirement: DependencyRequirement::LiveTarget(definition),
                    });
                let failure = self.predicate(PredicateKind::Not(success));
                let destructor = self.destructor(element)?;
                let failure_cleanup = ConditionalCleanup {
                    guard: failure,
                    value: content,
                    destructor,
                    at: site.execution_moments.first,
                };
                self.emit(Operation::TryAllocatePoolSlot(TryAllocatePoolSlot {
                    site,
                    pool: source,
                    content,
                    allocation,
                    success,
                    failure_cleanup,
                    result,
                    success_variant,
                    success_payload,
                    failure_variant,
                    failure_payload,
                    pool_full_variant,
                }));
            } else {
                let required =
                    self.constant_value("<one pool slot>", self.integer, ConstantValue::Integer(1));
                let check = CheckId(self.p.runtime_checks.len() as u32);
                self.p.runtime_checks.push(RuntimeCheck::PoolCapacity {
                    id: check,
                    pool: source,
                    required,
                });
                self.emit(Operation::AllocatePoolSlot(AllocatePoolSlot {
                    site,
                    pool: source,
                    content,
                    result,
                    check,
                }));
            }
            return Ok(Expr { value: result });
        }
        self.collection_method(n, base, source, name, args)
    }
    fn collection_method(
        &mut self,
        n: ast::NodeId,
        base: EvaluatedPlaceId,
        source: ValueId,
        name: &str,
        args: &[ast::NodeId],
    ) -> Result<Expr> {
        let definition = self.p.objects.evaluated_places[base.0 as usize].definition;
        let ty = self.p.objects.places[definition.0 as usize].ty;
        let (element, key) = match self.p.types.entries[ty.0 as usize].kind {
            TypeDefinition::GrowingSequence { element } => (element, None),
            TypeDefinition::KeyedCollection { key, value } => (value, Some(key)),
            TypeDefinition::GrowingString | TypeDefinition::InlineUtf8 { .. } => {
                (self.intern(TypeKey::Numeric(NumericType::U8)), None)
            }
            _ => {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidCall,
                    format!("no native collection operation '{name}'"),
                ));
            }
        };
        let descriptor = match self.p.objects.places[definition.0 as usize].root {
            PlaceRoot::Binding(binding)
                if self.p.objects.places[definition.0 as usize]
                    .projections
                    .is_empty() =>
            {
                match self.binding_entities.get(&binding) {
                    Some(EntityId::Address(address)) => CollectionDescriptor::Address(*address),
                    _ => CollectionDescriptor::Place(definition),
                }
            }
            _ => CollectionDescriptor::Place(definition),
        };
        let collection = if let Some(collection) = self.p.objects.collections.iter().find(|c| {
            c.ty == ty
                && match (&c.descriptor, &descriptor) {
                    (CollectionDescriptor::Address(a), CollectionDescriptor::Address(b)) => a == b,
                    (CollectionDescriptor::Place(a), CollectionDescriptor::Place(b)) => a == b,
                    _ => false,
                }
        }) {
            collection.id
        } else {
            let id = CollectionId(self.p.objects.collections.len() as u32);
            let owner = match descriptor {
                CollectionDescriptor::Address(address) => Owner::Entity(EntityOccurrence {
                    entity: EntityId::Address(address),
                    instance: self.ctx().domain,
                }),
                CollectionDescriptor::Place(place) => Owner::BorrowedTarget {
                    place,
                    instance: self.ctx().domain,
                },
            };
            let initial_owner = if matches!(descriptor, CollectionDescriptor::Address(_)) {
                Some(self.binding_owner_for_place(base))
            } else {
                None
            };
            self.p.objects.collections.push(Collection {
                id,
                ty,
                descriptor,
                created_in: self.ctx().scope,
                initial_owner,
                constraints: vec![],
            });
            self.p.objects.ownership.push(OwnershipLink {
                entity: EntityId::Collection(id),
                owner,
                scope: self.ctx().scope,
                established: self.ctx().last.unwrap(),
                guard: self.ctx().guard,
            });
            id
        };
        let usize_ty = self.intern(TypeKey::Numeric(NumericType::Usize));
        let mut values = vec![];
        let mut position = None;
        let (operation, result_type, required) = match name {
            "len" => (CollectionOperationKind::Length, usize_ty, vec![]),
            "clear" => (CollectionOperationKind::Clear, self.unit, vec![]),
            "push" => (CollectionOperationKind::Push, self.unit, vec![element]),
            "pop" => (
                CollectionOperationKind::Pop,
                self.option_type(element),
                vec![],
            ),
            "remove" => {
                if let Some(key) = key {
                    let key = self.intern(TypeKey::Reference(false, key));
                    (
                        CollectionOperationKind::Remove,
                        self.option_type(element),
                        vec![key],
                    )
                } else {
                    (CollectionOperationKind::Remove, element, vec![usize_ty])
                }
            }
            "replace" => (
                CollectionOperationKind::Replace,
                element,
                vec![usize_ty, element],
            ),
            "insert" => {
                if let Some(key) = key {
                    (
                        CollectionOperationKind::Insert,
                        self.option_type(element),
                        vec![key, element],
                    )
                } else {
                    (
                        CollectionOperationKind::Insert,
                        self.unit,
                        vec![usize_ty, element],
                    )
                }
            }
            "get" | "get_mut" => {
                let item = self.intern(TypeKey::Reference(name == "get_mut", element));
                let item = self.option_type(item);
                let input = if let Some(key) = key {
                    self.intern(TypeKey::Reference(false, key))
                } else {
                    usize_ty
                };
                (
                    if name == "get" {
                        CollectionOperationKind::Get
                    } else {
                        CollectionOperationKind::GetMutable
                    },
                    item,
                    vec![input],
                )
            }
            "as_bytes" | "as_slice" => {
                let data = self.intern(TypeKey::Slice(element));
                let view = self.intern(TypeKey::Reference(false, data));
                (CollectionOperationKind::View, view, vec![])
            }
            "as_mut_slice" => {
                let data = self.intern(TypeKey::Slice(element));
                let view = self.intern(TypeKey::Reference(true, data));
                (CollectionOperationKind::MutableView, view, vec![])
            }
            _ => {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidCall,
                    format!("native collection operation '{name}' has no registered signature"),
                ));
            }
        };
        if args.len() != required.len() {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                format!("{name} requires {} argument(s)", required.len()),
            ));
        }
        for (arg, required) in args.iter().zip(required) {
            let value = self.expression(*arg, Some(required))?.value;
            self.require_type(*arg, self.vtype(value), required)?;
            values.push(value);
        }
        if let Some(value) = values.first() {
            if matches!(
                operation,
                CollectionOperationKind::Remove
                    | CollectionOperationKind::Replace
                    | CollectionOperationKind::Insert
                    | CollectionOperationKind::Get
                    | CollectionOperationKind::GetMutable
            ) {
                position = Some(if key.is_some() {
                    PositionSelector::Key(*value)
                } else {
                    PositionSelector::DynamicIndex(*value)
                });
            }
        }
        let site = self.site(n, ExecutionPhase::Invoke);
        let dependencies = if matches!(
            operation,
            CollectionOperationKind::Length
                | CollectionOperationKind::Push
                | CollectionOperationKind::Clear
        ) {
            vec![]
        } else {
            vec![DependencyRequirement::NativeResult {
                operation: site.id,
                source,
                position: position.clone(),
            }]
        };
        let result = self.op_value(&site, result_type, dependencies);
        let mut incoming = vec![];
        if matches!(
            operation,
            CollectionOperationKind::Push
                | CollectionOperationKind::Insert
                | CollectionOperationKind::Replace
        ) {
            if let Some(value) = values.last() {
                for (_, entity) in self.value_entities_at(*value, site.guard) {
                    incoming.push(entity.clone());
                    self.p.objects.ownership.push(OwnershipLink {
                        entity,
                        owner: Owner::Entity(EntityOccurrence {
                            entity: EntityId::Collection(collection),
                            instance: self.ctx().domain,
                        }),
                        scope: site.scope,
                        established: site.execution_moments.first,
                        guard: site.guard,
                    });
                }
            }
        }
        let effects = self.effects(
            &site,
            vec![Effect::Collection(CollectionEffect {
                access: if matches!(
                    operation,
                    CollectionOperationKind::Length | CollectionOperationKind::Get
                ) {
                    AccessKind::Read
                } else if matches!(operation, CollectionOperationKind::View) {
                    AccessKind::SharedBorrow
                } else if matches!(
                    operation,
                    CollectionOperationKind::MutableView | CollectionOperationKind::GetMutable
                ) {
                    AccessKind::MutableBorrow
                } else {
                    AccessKind::Write
                },
                result: Some(result),
                collection,
                position: position
                    .clone()
                    .unwrap_or(PositionSelector::AllElements { length: None }),
                incoming,
                outgoing: vec![],
            })],
        );
        let arguments = values
            .into_iter()
            .enumerate()
            .map(|(i, value)| CallArgument {
                parameter_index: i as u32,
                value,
                transfer: self.transfer_kind(self.vtype(value)),
            })
            .collect();
        self.emit(Operation::NativeOperation(NativeOperation {
            site,
            kind: NativeOperationKind::Collection {
                collection,
                operation,
                position,
            },
            arguments,
            result,
            effects,
        }));
        self.attach_result_reference(result, n);
        Ok(Expr { value: result })
    }
    fn binding_owner_for_place(&self, place: EvaluatedPlaceId) -> Owner {
        let definition = self.p.objects.evaluated_places[place.0 as usize].definition;
        match self.p.objects.places[definition.0 as usize].root {
            PlaceRoot::Binding(binding) => self.binding_owner(binding),
            _ => Owner::Scope {
                scope: self.ctx().scope,
                instance: self.ctx().domain,
            },
        }
    }
    pub(super) fn result_type(&mut self, value: TypeId, error: TypeId) -> TypeId {
        let definition = self.p.well_known.result.unwrap();
        self.intern(TypeKey::Nominal(definition, vec![value, error]))
    }
    fn option_type(&mut self, value: TypeId) -> TypeId {
        let definition = self.p.well_known.option.unwrap();
        self.intern(TypeKey::Nominal(definition, vec![value]))
    }
    pub(super) fn function_item(
        &mut self,
        n: ast::NodeId,
        function: FunctionId,
        explicit: &[ast::NodeId],
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        let generics = self.p.declarations.functions[function.0 as usize]
            .type_parameters
            .clone();
        let mut inferred = HashMap::new();
        for (parameter, argument) in generics.iter().zip(explicit) {
            let ty = self.type_syntax(*argument, self.ctx().scope)?;
            inferred.insert(*parameter, ty);
        }
        let template = self.p.declarations.signatures
            [self.functions[function.0 as usize].signature.0 as usize]
            .clone();
        if let Some(expected) = expected.and_then(|ty| self.callable_signature(ty)) {
            let shape = self.p.declarations.signatures[expected.0.0 as usize].clone();
            for (a, b) in template.parameters.iter().zip(shape.parameters) {
                self.infer_substitutions(n, a.ty, b.ty, &mut inferred)?;
            }
            self.infer_substitutions(n, template.result, shape.result, &mut inferred)?;
        }
        let actual = generics
            .iter()
            .map(|p| {
                inferred.get(p).copied().ok_or_else(|| {
                    self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "function item needs concrete generic arguments",
                    )
                })
            })
            .collect::<Result<Vec<_>>>()?;
        let target = self.specialized_instance(function, actual)?;
        let signature = self.p.declarations.instances[target.0 as usize].signature;
        let shape = self.p.declarations.signatures[signature.0 as usize].clone();
        let result_type = if matches!(shape.execution, FunctionExecution::Asynchronous) {
            self.future_type(target)?
        } else {
            shape.result
        };
        let ty = self.callable_type(shape.parameters.iter().map(|p| p.ty).collect(), result_type);
        let site = self.site(n, ExecutionPhase::Compute);
        let result = self.op_value(&site, ty, vec![]);
        let effects = self.effects(&site, vec![]);
        self.emit(Operation::NativeOperation(NativeOperation {
            site,
            kind: NativeOperationKind::FunctionItem(target),
            arguments: vec![],
            result,
            effects,
        }));
        Ok(Expr { value: result })
    }
    fn runtime_launch(
        &mut self,
        n: ast::NodeId,
        kind: RuntimeLaunchKind,
        args: &[ast::NodeId],
    ) -> Result<Expr> {
        if args.len() != 1 {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "runtime launch requires one task or block",
            ));
        }
        let task = if kind == RuntimeLaunchKind::Thread {
            match self.kind(args[0]) {
                NodeKind::Block { .. } => {
                    self.capturing_expression(args[0], false, &[], None, args[0], None, false)?
                        .value
                }
                NodeKind::MoveBlock { body, .. } => {
                    self.capturing_expression(args[0], true, &[], None, *body, None, false)?
                        .value
                }
                _ => self.expression(args[0], None)?.value,
            }
        } else {
            self.expression(args[0], None)?.value
        };
        let (output, task_function) = match self.p.types.entries[self.vtype(task).0 as usize].kind {
            TypeDefinition::Future { body, result, .. }
                if matches!(
                    kind,
                    RuntimeLaunchKind::Spawn | RuntimeLaunchKind::SpawnBlocking
                ) =>
            {
                let BodyOwner::Instance(function) = self.p.bodies[body.0 as usize].owner else {
                    unreachable!()
                };
                (result, Some(function))
            }
            _ if kind != RuntimeLaunchKind::Spawn => {
                let Some((signature, captures)) = self.callable_signature(self.vtype(task)) else {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "thread/spawn_blocking requires synchronous callable code",
                    ));
                };
                let signature = &self.p.declarations.signatures[signature.0 as usize];
                if !signature.parameters.is_empty() {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidCall,
                        "native thread callable must take no arguments",
                    ));
                }
                (
                    signature.result,
                    captures.and_then(|c| self.p.contracts.captures[c.0 as usize].call),
                )
            }
            _ => {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    "spawn requires a future; use thread or spawn_blocking for synchronous code",
                ));
            }
        };
        let handle_type = self.intern(TypeKey::Handle(
            output,
            kind == RuntimeLaunchKind::SpawnBlocking,
        ));
        let function = self.runtime_launch_instance(n, kind, self.vtype(task), handle_type)?;
        let site = self.site(n, ExecutionPhase::Invoke);
        let result = self.op_value(&site, handle_type, self.dependencies(task));
        if kind == RuntimeLaunchKind::SpawnBlocking {
            self.require_execution_context(site.id, FunctionExecution::Asynchronous);
        }
        let effects = self.effects(&site, vec![Effect::LaunchTask { task, kind }]);
        self.materialize_value(
            result,
            Owner::Scope {
                scope: site.scope,
                instance: self.ctx().domain,
            },
            &site,
        );
        let handle_protocol = self.handle_protocol(handle_type)?;
        let completion = if let Some(join) = handle_protocol.join {
            ResolvedCompletionSelector::Call(join)
        } else {
            ResolvedCompletionSelector::Await(handle_protocol.awaiting.unwrap())
        };
        let branch = BranchContractId(self.p.contracts.branches.len() as u32);
        self.p.contracts.branches.push(BranchContract {
            id: branch,
            function: self.p.declarations.instances[function.0 as usize].definition,
            instance: function,
            completion: CompletionContract::ThroughResult {
                selector: completion,
            },
            effects: task_function
                .map(|f| self.p.declarations.instances[f.0 as usize].effects)
                .unwrap_or(effects),
        });
        self.emit(Operation::NativeOperation(NativeOperation {
            site: site.clone(),
            kind: NativeOperationKind::RuntimeLaunch {
                kind,
                task,
                function,
            },
            arguments: vec![CallArgument {
                parameter_index: 0,
                value: task,
                transfer: TransferKind::Move,
            }],
            result,
            effects,
        }));
        self.apply_branch_contract(n, branch, result, &site)?;
        let (child, domain) = self
            .p
            .contracts
            .applications
            .iter()
            .rev()
            .find_map(|a| match a {
                ContractApplication::Branch {
                    call,
                    child,
                    instance,
                    ..
                } if *call == site.id => Some((*child, *instance)),
                _ => None,
            })
            .expect("launch has a resolved execution branch");
        self.materialize_value(
            task,
            Owner::ExecutionBranch {
                branch: child,
                instance: domain,
            },
            &site,
        );
        Ok(Expr { value: result })
    }
    fn runtime_launch_instance(
        &mut self,
        n: ast::NodeId,
        kind: RuntimeLaunchKind,
        input: TypeId,
        result: TypeId,
    ) -> Result<FunctionInstanceId> {
        let function = FunctionId(self.functions.len() as u32);
        let signature = self.signature(
            vec![input],
            result,
            ReceiverMode::None,
            FunctionExecution::Synchronous,
        );
        let symbol = self.anonymous_symbol(
            "<runtime-launch>",
            self.runtime_scope,
            SymbolDefinition::Function(function),
            n,
        );
        self.p.declarations.functions.push(FunctionDefinition {
            parametric_body: None,
            id: function,
            symbol,
            signature,
            type_parameters: vec![],
            body: FunctionImplementation::Runtime(kind),
            contracts: vec![],
        });
        self.functions.push(FunctionSource {
            unit: self.current_unit,
            node: n,
            scope: self.runtime_scope,
            owner: None,
            signature,
            parameters: vec![("task".into(), input, false)],
            result,
            body: None,
            captures: None,
            infer_result: false,
            annotations: vec![],
            parameter_syntax: vec![None],
            result_syntax: None,
        });
        self.instance(function)
    }
    pub(super) fn handle_protocol(&mut self, ty: TypeId) -> Result<HandleProtocol> {
        if let Some(protocol) = self.p.handle_protocols.iter().find(|p| p.ty == ty) {
            return Ok(protocol.clone());
        }
        let TypeDefinition::ExecutionHandle {
            result,
            asynchronous,
        } = self.p.types.entries[ty.0 as usize].kind
        else {
            unreachable!()
        };
        let output = self.result_type(result, self.runtime_error);
        let protocol = if asynchronous {
            let signature = self.signature(
                vec![ty],
                output,
                ReceiverMode::ByValue(ty),
                FunctionExecution::Asynchronous,
            );
            HandleProtocol {
                ty,
                join: None,
                awaiting: Some(signature),
            }
        } else {
            let scope = self.declaration_scope(
                self.syntax.ast.root,
                self.runtime_scope,
                ScopeContext::Type(ty),
            );
            self.owner_scopes.insert(ty, scope);
            let function = FunctionId(self.functions.len() as u32);
            let signature = self.signature(
                vec![ty],
                output,
                ReceiverMode::ByValue(ty),
                FunctionExecution::Synchronous,
            );
            let symbol = self.compiler_symbol("join", scope, SymbolDefinition::Function(function));
            self.p.declarations.functions.push(FunctionDefinition {
                parametric_body: None,
                id: function,
                symbol,
                signature,
                type_parameters: vec![],
                body: FunctionImplementation::RuntimeJoin,
                contracts: vec![],
            });
            self.functions.push(FunctionSource {
                unit: self.current_unit,
                node: self.syntax.ast.root,
                scope,
                owner: Some(ty),
                signature,
                parameters: vec![("self".into(), ty, false)],
                result: output,
                body: None,
                captures: None,
                infer_result: false,
                annotations: vec![],
                parameter_syntax: vec![None],
                result_syntax: None,
            });
            let join = self.instance(function)?;
            self.p.declarations.instances[join.0 as usize].result.native =
                Some(NativeReturnRecipe::TaskOutputOfParameter(0));
            HandleProtocol {
                ty,
                join: Some(join),
                awaiting: None,
            }
        };
        self.p.handle_protocols.push(protocol.clone());
        Ok(protocol)
    }
    pub(super) fn complete_handle(
        &mut self,
        handle: ValueId,
        call: OperationId,
        at: ExecutionMomentId,
        guard: PredicateId,
    ) {
        for dependency in self.guarded_dependencies(handle, guard) {
            if let DependencyRequirement::BranchCompletion(capability) = dependency.requirement {
                let guard = if dependency.guard == guard {
                    guard
                } else {
                    self.predicate(PredicateKind::All(vec![guard, dependency.guard]))
                };
                self.p
                    .contracts
                    .applications
                    .push(ContractApplication::Completion {
                        call,
                        capability,
                        at,
                        guard,
                    });
            }
        }
    }
}
