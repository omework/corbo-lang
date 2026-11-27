//! Typed intrinsic boundaries for primitive representations. No source rewriting.
use super::*;
impl Resolver<'_> {
    pub(super) fn primitive_view(
        &mut self,
        n: ast::NodeId,
        source: EvaluatedPlaceId,
        target: TypeId,
        mutable: bool,
    ) -> Result<Expr> {
        let definition = self.p.objects.evaluated_places[source.0 as usize].definition;
        let ty = self.intern(TypeKey::Reference(mutable, target));
        let site = self.site(n, ExecutionPhase::Compute);
        let result = self.op_value(
            &site,
            ty,
            vec![DependencyRequirement::LiveTarget(definition)],
        );
        let effects = self.effects(&site, vec![Effect::Read(ReadEffect { place: definition })]);
        self.emit(Operation::NativeOperation(NativeOperation {
            site,
            kind: NativeOperationKind::Primitive(PrimitiveOperation::View {
                source,
                target,
                mutable,
            }),
            arguments: vec![],
            result,
            effects,
        }));
        self.attach_result_reference(result, n);
        Ok(Expr { value: result })
    }
    fn library_type(
        &self,
        n: ast::NodeId,
        package: &str,
        module: &[&str],
        name: &str,
    ) -> Result<TypeId> {
        let owner = self.p.declarations.modules.iter().find(|m| {
            self.p.declarations.packages[m.package.0 as usize].name == package
                && m.path.iter().map(String::as_str).eq(module.iter().copied())
        });
        let symbol = owner
            .and_then(|m| self.names[m.scope.0 as usize].get(name))
            .copied()
            .ok_or_else(|| {
                self.fail(
                    n,
                    DiagnosticKind::UnresolvedName,
                    format!(
                        "primitive signature requires {package}::{}::{name}",
                        module.join("::")
                    ),
                )
            })?;
        match self.p.symbols.entries[symbol.0 as usize].definition {
            SymbolDefinition::Type(ty) => Ok(ty),
            _ => Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                "primitive error declaration is not a type",
            )),
        }
    }
    pub(super) fn primitive_associated(
        &mut self,
        n: ast::NodeId,
        ty: TypeId,
        name: &str,
        args: &[ast::NodeId],
    ) -> Result<Option<Expr>> {
        if matches!(
            self.p.types.entries[ty.0 as usize].kind,
            TypeDefinition::StrData
        ) && name == "from_utf8"
        {
            if args.len() != 1 {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidCall,
                    "str::from_utf8 requires one byte slice",
                ));
            }
            let byte = self.intern(TypeKey::Numeric(NumericType::U8));
            let slice = self.intern(TypeKey::Slice(byte));
            let input = self.intern(TypeKey::Reference(false, slice));
            let bytes = self.expression(args[0], Some(input))?.value;
            self.require_type(n, self.vtype(bytes), input)?;
            let error = self.library_type(n, "std", &["text"], "Utf8Error")?;
            let view = self.intern(TypeKey::Reference(false, ty));
            let output = self.result_type(view, error);
            let site = self.site(n, ExecutionPhase::Compute);
            let result = self.op_value(&site, output, self.dependencies(bytes));
            let effects = self.effects(&site, vec![]);
            self.emit(Operation::NativeOperation(NativeOperation {
                site,
                kind: NativeOperationKind::Primitive(PrimitiveOperation::ValidateUtf8 {
                    bytes,
                    error,
                }),
                arguments: vec![CallArgument {
                    parameter_index: 0,
                    value: bytes,
                    transfer: TransferKind::Move,
                }],
                result,
                effects,
            }));
            return Ok(Some(Expr { value: result }));
        }
        if matches!(
            self.p.types.entries[ty.0 as usize].kind,
            TypeDefinition::Numeric(_)
        ) && name == "try_from"
        {
            if args.len() != 1 {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidCall,
                    "numeric try_from requires exactly one numeric operand",
                ));
            }
            let source = self.expression(args[0], None)?.value;
            if !matches!(
                self.p.types.entries[self.vtype(source).0 as usize].kind,
                TypeDefinition::Numeric(_)
            ) {
                return Err(self.fail(
                    n,
                    DiagnosticKind::TypeMismatch,
                    "numeric try_from requires a numeric source",
                ));
            }
            let error = self.intern(TypeKey::NumericConversionError);
            let output = self.result_type(ty, error);
            let site = self.site(n, ExecutionPhase::Compute);
            let result = self.op_value(&site, output, self.primitive_constraints(source));
            let effects = self.effects(&site, vec![]);
            self.emit(Operation::NativeOperation(NativeOperation {
                site,
                kind: NativeOperationKind::Primitive(PrimitiveOperation::TryNumericConversion {
                    source,
                    target: ty,
                }),
                arguments: vec![CallArgument {
                    parameter_index: 0,
                    value: source,
                    transfer: TransferKind::PrimitiveCopy,
                }],
                result,
                effects,
            }));
            return Ok(Some(Expr { value: result }));
        }
        Ok(None)
    }
}

impl Resolver<'_> {
    pub(super) fn runtime_primitive(
        &mut self,
        n: ast::NodeId,
        kind: RuntimePrimitiveKind,
        args: &[ast::NodeId],
    ) -> Result<Expr> {
        let usize_ty = self.intern(TypeKey::Numeric(NumericType::Usize));
        let u64_ty = self.intern(TypeKey::Numeric(NumericType::U64));
        let i64_ty = self.intern(TypeKey::Numeric(NumericType::I64));
        let mut process_args_errors = None;
        let (parameters, output, suspends) = match kind {
            RuntimePrimitiveKind::ProcessArgs => {
                let str_ty = self.intern(TypeKey::Str);
                let view = self.intern(TypeKey::Reference(false, str_ty));
                let slice = self.intern(TypeKey::Slice(view));
                let arguments = self.intern(TypeKey::Reference(false, slice));
                let error = self.library_type(n, "std", &["env"], "ArgsError")?;
                let variants = self
                    .p
                    .declarations
                    .variants
                    .iter()
                    .filter(|variant| variant.owner == error)
                    .map(|variant| {
                        (
                            self.p.symbols.entries[variant.symbol.0 as usize]
                                .spelling
                                .as_str(),
                            variant.id,
                        )
                    })
                    .collect::<Vec<_>>();
                let invalid_utf8 = variants
                    .iter()
                    .find_map(|(name, variant)| (*name == "InvalidUtf8").then_some(*variant));
                let unavailable = variants
                    .iter()
                    .find_map(|(name, variant)| (*name == "Unavailable").then_some(*variant));
                let (Some(invalid_utf8), Some(unavailable)) = (invalid_utf8, unavailable) else {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidCall,
                        "std::env::ArgsError must define InvalidUtf8 and Unavailable",
                    ));
                };
                process_args_errors = Some((invalid_utf8, unavailable));
                (vec![], self.result_type(arguments, error), false)
            }
            RuntimePrimitiveKind::WaitMutex => (vec![usize_ty], i64_ty, true),
            RuntimePrimitiveKind::WaitChannel => {
                (vec![usize_ty, u64_ty, self.boolean], i64_ty, true)
            }
            RuntimePrimitiveKind::WaitSocket => (vec![u64_ty, self.boolean], i64_ty, true),
            RuntimePrimitiveKind::AttachSocket => (vec![u64_ty], i64_ty, false),
            RuntimePrimitiveKind::CompleteSocket => (vec![u64_ty, usize_ty], i64_ty, true),
        };
        if args.len() != parameters.len() {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "runtime primitive argument count differs from its signature",
            ));
        }
        let mut values = vec![];
        for (index, (arg, ty)) in args.iter().zip(parameters).enumerate() {
            let value = self.expression(*arg, Some(ty))?.value;
            self.require_type(*arg, self.vtype(value), ty)?;
            values.push(CallArgument {
                parameter_index: index as u32,
                value,
                transfer: self.transfer_kind(ty),
            });
        }
        let mut site = self.site(n, ExecutionPhase::Invoke);
        let suspension = if suspends {
            let ready = self.predicate(PredicateKind::RuntimeReady { operation: site.id });
            let (suspension, _) = self.poll_transition(&mut site, ready);
            Some(suspension)
        } else {
            None
        };
        let result = self.op_value(&site, output, vec![]);
        let effects = self.effects(&site, vec![]);
        self.emit(Operation::NativeOperation(NativeOperation {
            site,
            kind: NativeOperationKind::Primitive(PrimitiveOperation::Runtime {
                kind,
                suspension,
                process_args_errors,
            }),
            arguments: values,
            result,
            effects,
        }));
        Ok(Expr { value: result })
    }
}

impl Resolver<'_> {
    /// Existing compiler-known primitive-method adapters resolve to an ordinary
    /// STD function once; downstream consumers see a normal concrete call.
    pub(super) fn byte_content_equal(
        &mut self,
        n: ast::NodeId,
        receiver: EvaluatedPlaceId,
        args: &[ast::NodeId],
    ) -> Result<Expr> {
        if args.len() != 1 {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "content_eq requires one byte slice",
            ));
        }
        let module = self
            .p
            .declarations
            .modules
            .iter()
            .find(|m| {
                self.p.declarations.packages[m.package.0 as usize].name == "std"
                    && m.path == ["bytes"]
            })
            .ok_or_else(|| {
                self.fail(
                    n,
                    DiagnosticKind::UnresolvedName,
                    "content_eq requires std::bytes",
                )
            })?;
        let symbol = *self.names[module.scope.0 as usize]
            .get("content_eq")
            .ok_or_else(|| {
                self.fail(
                    n,
                    DiagnosticKind::UnresolvedName,
                    "STD content_eq implementation is missing",
                )
            })?;
        let SymbolDefinition::Function(function) =
            self.p.symbols.entries[symbol.0 as usize].definition
        else {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "STD content_eq binding is not a function",
            ));
        };
        let instance = self.instance(function)?;
        let signature = self.p.declarations.instances[instance.0 as usize].signature;
        let shape = self.p.declarations.signatures[signature.0 as usize].clone();
        let first = self.borrow(n, receiver, false)?.value;
        self.require_type(n, self.vtype(first), shape.parameters[0].ty)?;
        let second = self
            .expression(args[0], Some(shape.parameters[1].ty))?
            .value;
        self.require_type(n, self.vtype(second), shape.parameters[1].ty)?;
        self.invoke_concrete(
            n,
            self.functions[function.0 as usize].clone(),
            instance,
            vec![first, second],
            0,
            Some(self.boolean),
        )
    }
}
