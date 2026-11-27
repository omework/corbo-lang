//! Complete symbolic initialization/cleanup recipes; no bytes or cleanup order proof.
use super::*;
impl Resolver<'_> {
    pub(super) fn default_plan(
        &mut self,
        n: ast::NodeId,
        ty: TypeId,
        active: &mut HashSet<TypeId>,
    ) -> Result<DefaultPlanId> {
        if let Some(plan) = self.p.declarations.defaults.iter().find(|p| p.ty == ty) {
            return Ok(plan.id);
        }
        self.ensure_nominal(ty, n)?;
        if !active.insert(ty) {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                "recursive type has no finite structural default",
            ));
        }
        let kind = match self.p.types.entries[ty.0 as usize].kind.clone() {
            TypeDefinition::Unit => DefaultInitializationKind::Constant(ConstantValue::Unit),
            TypeDefinition::Boolean => {
                DefaultInitializationKind::Constant(ConstantValue::Boolean(false))
            }
            TypeDefinition::Numeric(NumericType::F32) => {
                DefaultInitializationKind::Constant(ConstantValue::Float32(0))
            }
            TypeDefinition::Numeric(NumericType::F64) => {
                DefaultInitializationKind::Constant(ConstantValue::Float64(0))
            }
            TypeDefinition::Numeric(NumericType::I32 | NumericType::I64) => {
                DefaultInitializationKind::Constant(ConstantValue::Integer(0))
            }
            TypeDefinition::Numeric(_) => {
                DefaultInitializationKind::Constant(ConstantValue::Unsigned(0))
            }
            TypeDefinition::GrowingString
            | TypeDefinition::InlineUtf8 { .. }
            | TypeDefinition::GrowingSequence { .. }
            | TypeDefinition::KeyedCollection { .. } => DefaultInitializationKind::EmptyNative,
            TypeDefinition::Tuple(parts) => {
                let mut plans = vec![];
                for ty in parts {
                    plans.push(self.default_plan(n, ty, active)?);
                }
                DefaultInitializationKind::Tuple(plans)
            }
            TypeDefinition::Array { element, length } => DefaultInitializationKind::Array {
                element: self.default_plan(n, element, active)?,
                count: length,
            },
            TypeDefinition::Nominal { .. } => {
                let fields = self.fields(ty, n)?;
                let mut steps = vec![];
                for field in fields {
                    let definition = self.p.declarations.fields[field.0 as usize].clone();
                    if !self.visible_from(definition.symbol, self.ctx().scope) {
                        return Err(self.fail(
                            n,
                            DiagnosticKind::UnresolvedName,
                            "cannot default-initialize a private field from this module",
                        ));
                    }
                    let plan = self.default_plan(n, definition.ty, active)?;
                    self.p.declarations.fields[field.0 as usize].default =
                        FieldDefault::Resolved(plan);
                    steps.push(FieldDefaultStep { field, plan });
                }
                DefaultInitializationKind::Struct(steps)
            }
            _ => {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    format!(
                        "{} has no defined default initialization",
                        self.type_name(ty)
                    ),
                ));
            }
        };
        active.remove(&ty);
        let id = DefaultPlanId(self.p.declarations.defaults.len() as u32);
        self.p
            .declarations
            .defaults
            .push(DefaultInitializationPlan { id, ty, kind });
        Ok(id)
    }
    pub(super) fn populate_cleanup_components(&mut self, id: DestructorId) -> Result<()> {
        let ty = self.p.contracts.destructors[id.0 as usize].ty;
        self.ensure_nominal(ty, self.syntax.ast.root)?;
        let mut components = vec![];
        if let Some(record) = self.p.declarations.structs.iter().find(|s| s.ty == ty) {
            for field in record.fields.clone() {
                components.push((
                    PredicateId(0),
                    PositionSelector::Field(field),
                    self.p.declarations.fields[field.0 as usize].ty,
                ));
            }
        } else if let Some(enumeration) = self
            .p
            .declarations
            .enums
            .iter()
            .find(|e| e.ty == ty)
            .cloned()
        {
            for variant in
                std::iter::once(enumeration.variants.first).chain(enumeration.variants.rest)
            {
                let guard = self.predicate(PredicateKind::DestructorVariant {
                    destructor: id,
                    variant,
                });
                for field in self.p.declarations.variants[variant.0 as usize]
                    .fields
                    .clone()
                {
                    components.push((
                        guard,
                        PositionSelector::VariantField { variant, field },
                        self.p.declarations.fields[field.0 as usize].ty,
                    ));
                }
            }
        } else {
            match self.p.types.entries[ty.0 as usize].kind.clone() {
                TypeDefinition::Array { element, length } => components.push((
                    PredicateId(0),
                    PositionSelector::AllElements {
                        length: Some(length),
                    },
                    element,
                )),
                TypeDefinition::Tuple(parts) => {
                    for (index, ty) in parts.into_iter().enumerate() {
                        components.push((
                            PredicateId(0),
                            PositionSelector::TupleElement(index as u32),
                            ty,
                        ));
                    }
                }
                TypeDefinition::Closure { captures, .. } => {
                    for capture in self.p.contracts.captures[captures.0 as usize]
                        .captures
                        .clone()
                    {
                        components.push((
                            PredicateId(0),
                            PositionSelector::Field(capture.field),
                            self.p.declarations.fields[capture.field.0 as usize].ty,
                        ));
                    }
                }
                TypeDefinition::GrowingSequence { element } => components.push((
                    PredicateId(0),
                    PositionSelector::AllElements { length: None },
                    element,
                )),
                TypeDefinition::KeyedCollection { key, value } => {
                    components.push((PredicateId(0), PositionSelector::AllKeys, key));
                    components.push((
                        PredicateId(0),
                        PositionSelector::AllElements { length: None },
                        value,
                    ));
                }
                TypeDefinition::Allocation { content } => {
                    components.push((PredicateId(0), PositionSelector::AllocationContent, content))
                }
                TypeDefinition::Future { state, .. } => {
                    components.push((PredicateId(0), PositionSelector::State, state))
                }
                _ => {}
            }
        }
        let mut plans = vec![];
        for (guard, position, ty) in components {
            let destructor = self.destructor(ty)?;
            plans.push(ComponentDestruction {
                guard,
                position,
                destructor,
                dependencies: vec![],
            });
        }
        self.p.contracts.destructors[id.0 as usize].owned_components = plans;
        Ok(())
    }
    pub(super) fn copy_or_drop(
        &mut self,
        n: ast::NodeId,
        drop: bool,
        arguments: &[ast::NodeId],
    ) -> Result<Expr> {
        if arguments.len() != 1 {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "copy/drop requires exactly one value",
            ));
        }
        let source = arguments[0];
        let value = if drop && self.is_place_syntax(source) {
            // Explicit destruction consumes the source place even for a primitive
            // or eligible enum; it must not go through implicit value copying.
            let place = self.place_expression(source)?;
            let previous = self.read_place(source, place)?.value;
            let site = self.site(n, ExecutionPhase::TransferOwnership);
            let value = self.op_value(&site, self.vtype(previous), vec![]);
            self.forward_summaries(previous, value);
            let provenance = self.p.values.entries[value.0 as usize].provenance;
            self.p.values.provenance[provenance.0 as usize].kind = ProvenanceKind::Move {
                source: previous,
                operation: site.id,
            };
            let destination = Owner::Scope {
                scope: site.scope,
                instance: self.ctx().domain,
            };
            self.transfer(value, destination.clone(), &site);
            let effects = self.effects(&site, vec![]);
            self.emit(Operation::MoveValue(MoveValue {
                site,
                source: MoveSource::Place(place),
                result: value,
                value: previous,
                destination,
                effects,
            }));
            value
        } else if !drop && self.is_place_syntax(source) {
            let place = self.place_expression(source)?;
            self.read_place(source, place)?.value
        } else {
            self.expression(source, None)?.value
        };
        if drop {
            let site = self.site(n, ExecutionPhase::Destroy);
            let destructor = self.destructor(self.vtype(value))?;
            let entities = self.value_entities_at(value, site.guard);
            let effects = self.effects(
                &site,
                entities
                    .into_iter()
                    .map(|(_, entity)| Effect::Cleanup(CleanupEffect { entity }))
                    .collect(),
            );
            self.emit(Operation::DropValue(DropValue {
                site,
                value,
                destructor,
                effects,
            }));
            let site = self.site(n, ExecutionPhase::Compute);
            let result = self.op_value(&site, self.unit, vec![]);
            self.emit(Operation::UnitValue(UnitValue { site, result }));
            Ok(Expr { value: result })
        } else {
            if !self.implicit_copy(self.vtype(value)) {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    "explicit copy() requires a primitive, a shared reference, or an eligible enum",
                ));
            }
            let site = self.site(n, ExecutionPhase::Compute);
            let ty = self.vtype(value);
            let dependencies = if self.primitive(ty) {
                self.primitive_constraints(value)
            } else {
                self.dependencies(value)
            };
            let result = self.op_value(&site, ty, dependencies);
            let provenance = self.p.values.entries[result.0 as usize].provenance;
            self.p.values.provenance[provenance.0 as usize].kind = ProvenanceKind::Copy {
                source: value,
                operation: site.id,
            };
            if self.enum_copy(self.vtype(value)) {
                self.emit(Operation::CopyEligibleEnum(CopyEligibleEnum {
                    site: site.clone(),
                    source: value,
                    result,
                }));
            } else {
                self.emit(Operation::CopyPrimitive(CopyPrimitive {
                    site: site.clone(),
                    source: value,
                    result,
                }));
            }
            if self.shared_reference(self.vtype(value)) {
                self.forward_summaries(value, result);
                self.clone_reference_identity(value, result, &site);
            }
            Ok(Expr { value: result })
        }
    }
}
