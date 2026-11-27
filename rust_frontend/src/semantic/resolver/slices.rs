//! Contiguous array/slice places. The source and each bound are evaluated once.
use super::*;
impl Resolver<'_> {
    pub(super) fn require_integer(&self, n: ast::NodeId, value: ValueId) -> Result<()> {
        if matches!(
            self.p.types.entries[self.vtype(value).0 as usize].kind,
            TypeDefinition::Numeric(
                NumericType::I32
                    | NumericType::I64
                    | NumericType::U8
                    | NumericType::U16
                    | NumericType::U32
                    | NumericType::U64
                    | NumericType::Usize
            )
        ) {
            Ok(())
        } else {
            Err(self.fail(
                n,
                DiagnosticKind::TypeMismatch,
                "sequence index or bound requires an integer",
            ))
        }
    }
    pub(super) fn sequence_info(
        &mut self,
        n: ast::NodeId,
        source: EvaluatedPlaceId,
    ) -> Result<(TypeId, ValueId)> {
        let place = self.p.objects.evaluated_places[source.0 as usize].definition;
        let ty = self.p.objects.places[place.0 as usize].ty;
        let usize_ty = self.intern(TypeKey::Numeric(NumericType::Usize));
        match self.p.types.entries[ty.0 as usize].kind {
            TypeDefinition::Array { element, length } => Ok((
                element,
                self.constant_value(
                    "<array length>",
                    usize_ty,
                    ConstantValue::Unsigned(length as u128),
                ),
            )),
            TypeDefinition::Slice { element } | TypeDefinition::GrowingSequence { element } => {
                let site = self.site(n, ExecutionPhase::Read);
                let result = self.op_value(&site, usize_ty, vec![]);
                self.emit(Operation::SequenceLength(SequenceLength {
                    site,
                    source,
                    result,
                }));
                Ok((element, result))
            }
            TypeDefinition::StrData
            | TypeDefinition::GrowingString
            | TypeDefinition::InlineUtf8 { .. } => {
                let byte = self.intern(TypeKey::Numeric(NumericType::U8));
                let site = self.site(n, ExecutionPhase::Read);
                let result = self.op_value(&site, usize_ty, vec![]);
                self.emit(Operation::SequenceLength(SequenceLength {
                    site,
                    source,
                    result,
                }));
                Ok((byte, result))
            }
            _ => Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                format!(
                    "{} is not contiguous array or slice data",
                    self.type_name(ty)
                ),
            )),
        }
    }
    pub(super) fn slice_place(
        &mut self,
        n: ast::NodeId,
        base: ast::NodeId,
        range: ast::NodeId,
    ) -> Result<EvaluatedPlaceId> {
        let source = self.place_expression(base)?;
        let source = self.deref_place(base, source)?;
        let (element, length) = self.sequence_info(n, source)?;
        let NodeKind::Range { start, end, .. } = self.kind(range) else {
            unreachable!()
        };
        let usize_ty = self.intern(TypeKey::Numeric(NumericType::Usize));
        let start = if let Some(node) = start {
            let value = self.expression(*node, None)?.value;
            self.require_integer(*node, value)?;
            value
        } else {
            self.constant_value("<range start>", usize_ty, ConstantValue::Unsigned(0))
        };
        let end = if let Some(node) = end {
            let value = self.expression(*node, None)?.value;
            self.require_integer(*node, value)?;
            value
        } else {
            length
        };
        let definition = self.p.objects.evaluated_places[source.0 as usize].definition;
        let previous = self.p.objects.places[definition.0 as usize].clone();
        let ty = if matches!(
            self.p.types.entries[previous.ty.0 as usize].kind,
            TypeDefinition::StrData
                | TypeDefinition::GrowingString
                | TypeDefinition::InlineUtf8 { .. }
        ) {
            self.intern(TypeKey::Str)
        } else {
            self.intern(TypeKey::Slice(element))
        };
        let mut projections = previous.projections;
        projections.push(PlaceProjection::Range { start, end });
        let definition = self.place(previous.root, projections, ty);
        let site = self.site(n, ExecutionPhase::Evaluate);
        let result = EvaluatedPlaceId(self.p.objects.evaluated_places.len() as u32);
        self.p.objects.evaluated_places.push(EvaluatedPlace {
            id: result,
            definition,
            produced_by: site.id,
            selectors: vec![start, end],
        });
        let check = CheckId(self.p.runtime_checks.len() as u32);
        self.p
            .runtime_checks
            .push(RuntimeCheck::SliceBounds(SliceBoundsCheck {
                id: check,
                start,
                end,
                length,
            }));
        self.emit(Operation::SlicePlace(SlicePlace {
            site,
            base: source,
            start,
            end,
            element,
            result,
            check,
        }));
        self.cover(range, SyntaxDisposition::ResolvedType(ty));
        Ok(result)
    }
}

impl Resolver<'_> {
    pub(super) fn try_text_slice(
        &mut self,
        n: ast::NodeId,
        source: EvaluatedPlaceId,
        range: ast::NodeId,
    ) -> Result<Expr> {
        let definition = self.p.objects.evaluated_places[source.0 as usize].definition;
        let previous = self.p.objects.places[definition.0 as usize].clone();
        if !matches!(
            self.p.types.entries[previous.ty.0 as usize].kind,
            TypeDefinition::StrData
                | TypeDefinition::GrowingString
                | TypeDefinition::InlineUtf8 { .. }
        ) {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                "try_slice range overload requires UTF-8 text",
            ));
        }
        let (_, length) = self.sequence_info(n, source)?;
        let NodeKind::Range { start, end, .. } = self.kind(range) else {
            unreachable!()
        };
        let usize_ty = self.intern(TypeKey::Numeric(NumericType::Usize));
        let start = if let Some(start) = start {
            let value = self.expression(*start, None)?.value;
            self.require_integer(*start, value)?;
            value
        } else {
            self.constant_value("<slice start>", usize_ty, ConstantValue::Unsigned(0))
        };
        let end = if let Some(end) = end {
            let value = self.expression(*end, None)?.value;
            self.require_integer(*end, value)?;
            value
        } else {
            length
        };
        let text = self.intern(TypeKey::Str);
        let view_type = self.intern(TypeKey::Reference(false, text));
        let output = self.result_type(view_type, self.slice_error);
        self.ensure_nominal(output, n)?;
        let mut projections = previous.projections;
        projections.push(PlaceProjection::Range { start, end });
        let target = self.place(previous.root, projections, text);
        let site = self.site(n, ExecutionPhase::Invoke);
        let valid = self.predicate(PredicateKind::ValidTextRange { source, start, end });
        let view = self.value(
            view_type,
            ValueDefinition::ConditionalResult {
                operation: site.id,
                produced_at: site.execution_moments.first,
                guard: valid,
            },
            ProvenanceKind::Constructed(site.id),
            vec![DependencyRequirement::LiveTarget(target)],
        );
        let reference = ReferenceId(self.p.objects.references.len() as u32);
        self.p.objects.references.push(Reference {
            id: reference,
            ty: view_type,
            created_in: site.scope,
            creation: ObjectCreation::At(site.execution_moments.first),
            initial_owner: Owner::Scope {
                scope: site.scope,
                instance: self.ctx().domain,
            },
            permission: ReferencePermission::Shared,
            formation: ReferenceFormation::Loan,
            origins: NonEmpty {
                first: ReferenceOrigin {
                    target,
                    parent: None,
                    guard: valid,
                },
                rest: vec![],
            },
        });
        self.references.insert(view, reference);
        self.value_entities
            .insert(view, EntityId::Reference(reference));
        let result = self.op_value(&site, output, vec![]);
        let summary = self.p.values.entries[result.0 as usize].dependencies;
        self.p.values.dependency_summaries[summary.0 as usize]
            .guarded
            .push(GuardedDependency {
                guard: valid,
                requirement: DependencyRequirement::LiveTarget(target),
            });
        self.components.insert(result, vec![view]);
        let error = self
            .p
            .declarations
            .enums
            .iter()
            .find(|e| e.ty == self.slice_error)
            .unwrap();
        let out_of_bounds = error.variants.first;
        let not_char_boundary = error.variants.rest[0];
        let result_shape = self
            .p
            .declarations
            .enums
            .iter()
            .find(|enumeration| enumeration.ty == output)
            .expect("result type was materialized above");
        let success = result_shape.variants.first;
        let failure = result_shape.variants.rest[0];
        let success_payload = self.p.declarations.variants[success.0 as usize].fields[0];
        let failure_payload = self.p.declarations.variants[failure.0 as usize].fields[0];
        self.cover(
            range,
            SyntaxDisposition::Operations(NonEmpty {
                first: site.id,
                rest: vec![],
            }),
        );
        self.emit(Operation::TryTextSlice(TryTextSlice {
            site,
            source,
            start,
            end,
            length,
            valid,
            success,
            failure,
            success_payload,
            failure_payload,
            out_of_bounds,
            not_char_boundary,
            view,
            reference,
            result,
        }));
        Ok(Expr { value: result })
    }
}
