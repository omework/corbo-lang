//! Iteration resolves its source once and reuses ordinary scopes, calls and places.
use super::*;

pub(super) struct IterationInput {
    pub source: ValueId,
    pub binding: BindingId,
    pub pattern: ast::NodeId,
}
pub(super) struct IterationHeader {
    pub condition: ValueId,
    pub protocol: ResolvedIteration,
    selection: IterationSelection,
}
enum IterationSelection {
    Indexed {
        base: EvaluatedPlaceId,
        index: ValueId,
        element: TypeId,
        permission: Option<ReferencePermission>,
    },
    Next {
        subject: ValueId,
        variant: VariantId,
        field: FieldId,
        payload: TypeId,
    },
}
impl Resolver<'_> {
    pub(super) fn for_statement(
        &mut self,
        n: ast::NodeId,
        pattern: ast::NodeId,
        source: ast::NodeId,
        body: ast::NodeId,
    ) -> Result<bool> {
        let (scope, parent) = self.enter_runtime_scope(n)?;
        let value = self.expression(source, None)?.value;
        if self.vtype(value) == self.never {
            self.ctx_mut().scope = parent;
            return Ok(false);
        }
        // This compiler-generated binding cannot collide with a source identifier.
        // It makes the loop-source owner and cleanup boundary explicit.
        let binding = self.bind(n, &format!("<for-source:{}>", scope.0), true, value)?;
        let input = IterationInput {
            source: value,
            binding,
            pattern,
        };
        let result = self.loop_expression(n, None, body, Some(self.unit), Some(input))?;
        self.finish_runtime_scope(n, scope, parent, result)?;
        Ok(true)
    }
    pub(super) fn iteration_header(
        &mut self,
        n: ast::NodeId,
        input: &IterationInput,
        region: LoopRegionId,
        coordinate: IterationVariableId,
    ) -> Result<IterationHeader> {
        let ty = self.p.scopes.bindings[input.binding.0 as usize].ty;
        let root = self.place(PlaceRoot::Binding(input.binding), vec![], ty);
        let source_place = self.evaluated_place(n, root, vec![]);
        let (data_type, permission) = match self.p.types.entries[ty.0 as usize].kind.clone() {
            TypeDefinition::Reference { target, permission } => (target, Some(permission)),
            _ => (ty, None),
        };
        if matches!(
            self.p.types.entries[data_type.0 as usize].kind,
            TypeDefinition::Array { .. } | TypeDefinition::Slice { .. }
        ) {
            let base = self.deref_place(n, source_place)?;
            let (element, length) = self.sequence_info(n, base)?;
            let usize_ty = self.intern(TypeKey::Numeric(NumericType::Usize));
            let site = self.site(n, ExecutionPhase::Read);
            let index = self.op_value(&site, usize_ty, vec![]);
            self.emit(Operation::IterationIndex(IterationIndex {
                site,
                region,
                coordinate,
                result: index,
            }));
            let site = self.site(n, ExecutionPhase::Compute);
            let condition = self.op_value(&site, self.boolean, vec![]);
            self.emit(Operation::Less(Less {
                site,
                domain: NumericType::Usize,
                left: index,
                right: length,
                result: condition,
                checks: vec![],
            }));
            let protocol = match (
                &permission,
                &self.p.types.entries[data_type.0 as usize].kind,
            ) {
                (Some(permission), _) => ResolvedIteration::BorrowedSlice {
                    length,
                    element,
                    permission: permission.clone(),
                },
                (None, TypeDefinition::Array { length, .. }) => ResolvedIteration::FixedArray {
                    length: *length,
                    element,
                    transfer: self.transfer_kind(element),
                },
                _ => {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "unsized slice data must be borrowed before iteration",
                    ));
                }
            };
            return Ok(IterationHeader {
                condition,
                protocol,
                selection: IterationSelection::Indexed {
                    base,
                    index,
                    element,
                    permission,
                },
            });
        }
        let place = self.deref_place(n, source_place)?;
        let definition = self.p.objects.evaluated_places[place.0 as usize].definition;
        let target_type = self.p.objects.places[definition.0 as usize].ty;
        self.ensure_nominal(target_type, n)?;
        let symbol = self
            .owner_scopes
            .get(&target_type)
            .and_then(|scope| self.names[scope.0 as usize].get("next"))
            .copied()
            .ok_or_else(|| {
                self.fail(n, DiagnosticKind::InvalidType,
                "for source must be an array, borrowed slice, or provide next(&mut self) Option<T>")
            })?;
        let SymbolDefinition::Function(function) =
            self.p.symbols.entries[symbol.0 as usize].definition
        else {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "iterator next member is not a method",
            ));
        };
        if !matches!(
            self.p.declarations.signatures
                [self.functions[function.0 as usize].signature.0 as usize]
                .receiver,
            ReceiverMode::Mutable(_)
        ) {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "iterator next() must take &mut self",
            ));
        }
        let receiver = self.borrow(n, place, true)?.value;
        let subject = self
            .invoke_function(n, function, Some(receiver), &[], &[], None)?
            .value;
        let option_type = self.vtype(subject);
        self.ensure_nominal(option_type, n)?;
        if !matches!(self.p.types.entries[option_type.0 as usize].kind,
            TypeDefinition::Nominal { definition, .. } if Some(definition) == self.p.well_known.option)
        {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                "iterator next() must return Option<T>",
            ));
        }
        let enumeration = self
            .p
            .declarations
            .enums
            .iter()
            .find(|e| e.ty == option_type)
            .unwrap();
        let variants: Vec<_> = std::iter::once(enumeration.variants.first)
            .chain(enumeration.variants.rest.iter().copied())
            .collect();
        let some = variants
            .iter()
            .copied()
            .find(|variant| {
                !self.p.declarations.variants[variant.0 as usize]
                    .fields
                    .is_empty()
            })
            .unwrap();
        let none = variants
            .into_iter()
            .find(|variant| *variant != some)
            .unwrap();
        let field = self.p.declarations.variants[some.0 as usize].fields[0];
        let payload = self.p.declarations.fields[field.0 as usize].ty;
        let operation = match self.p.values.entries[subject.0 as usize].definition {
            ValueDefinition::OperationResult { operation, .. } => operation,
            _ => unreachable!(),
        };
        let method = self.p.bodies[self.ctx().body.0 as usize]
            .operations
            .iter()
            .find_map(|op| match op {
                Operation::MethodCall(call) if call.site.id == operation => {
                    match call.target.target {
                        MethodTarget::Concrete(instance) => Some(instance),
                        _ => None,
                    }
                }
                _ => None,
            })
            .unwrap();
        let site = self.site(n, ExecutionPhase::Compute);
        let condition = self.op_value(&site, self.boolean, vec![]);
        self.emit(Operation::PatternMatches(PatternMatches {
            site,
            subject,
            test: PatternTest::Variant {
                variant: some,
                fields: vec![(field, PatternTest::Any)],
            },
            result: condition,
        }));
        Ok(IterationHeader {
            condition,
            protocol: ResolvedIteration::NextMethod {
                method,
                option_type,
                some,
                none,
                payload,
                matched_contract: None,
            },
            selection: IterationSelection::Next {
                subject,
                variant: some,
                field,
                payload,
            },
        })
    }
    pub(super) fn iteration_item(
        &mut self,
        n: ast::NodeId,
        _input: &IterationInput,
        header: &IterationHeader,
    ) -> Result<ValueId> {
        match &header.selection {
            IterationSelection::Indexed {
                base,
                index,
                element,
                permission,
            } => {
                let definition = self.p.objects.evaluated_places[base.0 as usize].definition;
                let base_definition = self.p.objects.places[definition.0 as usize].clone();
                let mut projections = base_definition.projections;
                projections.push(PlaceProjection::Index(*index));
                let place = self.place(base_definition.root, projections, *element);
                let site = self.site(n, ExecutionPhase::Evaluate);
                let result = EvaluatedPlaceId(self.p.objects.evaluated_places.len() as u32);
                self.p.objects.evaluated_places.push(EvaluatedPlace {
                    id: result,
                    definition: place,
                    produced_by: site.id,
                    selectors: vec![*index],
                });
                let length = match &header.protocol {
                    ResolvedIteration::BorrowedSlice { length, .. } => *length,
                    ResolvedIteration::FixedArray { length, .. } => {
                        let ty = self.vtype(*index);
                        self.constant_value(
                            "<for length>",
                            ty,
                            ConstantValue::Unsigned(*length as u128),
                        )
                    }
                    _ => unreachable!(),
                };
                let check = CheckId(self.p.runtime_checks.len() as u32);
                self.p
                    .runtime_checks
                    .push(RuntimeCheck::IndexBounds(IndexBoundsCheck {
                        id: check,
                        index: *index,
                        length,
                    }));
                self.emit(Operation::IndexPlace(IndexPlace {
                    site,
                    base: *base,
                    index: *index,
                    access: ResolvedIndexAccess::Contiguous { element: *element },
                    result,
                    check,
                }));
                match permission {
                    Some(permission) => Ok(self
                        .borrow(
                            n,
                            result,
                            matches!(permission, ReferencePermission::Mutable),
                        )?
                        .value),
                    None => Ok(self.load(n, result)?.value),
                }
            }
            IterationSelection::Next {
                subject,
                variant,
                field,
                payload,
            } => Ok(self.extract_pattern(
                n,
                *subject,
                PlaceProjection::Field(*field),
                Some(*variant),
                *payload,
                None,
            )),
        }
    }
    pub(super) fn iteration_bindings(pattern: &ResolvedPattern, bindings: &mut Vec<BindingId>) {
        match pattern {
            ResolvedPattern::Binding { binding, .. } => bindings.push(*binding),
            ResolvedPattern::Tuple(parts) => {
                for part in parts {
                    Self::iteration_bindings(part, bindings);
                }
            }
            ResolvedPattern::Variant { fields, .. } => {
                for field in fields {
                    Self::iteration_bindings(&field.pattern, bindings);
                }
            }
            _ => {}
        }
    }
}
