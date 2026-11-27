//! Resolved value projection recipes. These retain field identity and provenance
//! through calls even when the selected runtime payload is not statically known.
use super::*;
impl Resolver<'_> {
    pub(super) fn projected_value(
        &mut self,
        site: &OperationSite,
        source: ValueId,
        position: PositionSelector,
        ty: TypeId,
    ) -> ValueId {
        let produced_at = site
            .execution_moments
            .rest
            .last()
            .copied()
            .unwrap_or(site.execution_moments.first);
        let value = self.value(
            ty,
            ValueDefinition::OperationResult {
                operation: site.id,
                produced_at,
            },
            ProvenanceKind::Projection {
                source,
                position: position.clone(),
                operation: site.id,
            },
            vec![DependencyRequirement::CarriedByProjection {
                source,
                position: position.clone(),
                result: ty,
            }],
        );
        if let TypeDefinition::Reference { target, permission } =
            self.p.types.entries[ty.0 as usize].kind.clone()
        {
            let projection = match position {
                PositionSelector::Field(field) => PlaceProjection::Field(field),
                PositionSelector::TupleElement(index) => PlaceProjection::TupleElement(index),
                PositionSelector::FixedIndex(index) => {
                    let usize_ty = self.intern(TypeKey::Numeric(NumericType::Usize));
                    let index = self.constant_value(
                        "<projection index>",
                        usize_ty,
                        ConstantValue::Unsigned(index as u128),
                    );
                    PlaceProjection::Index(index)
                }
                _ => return value,
            };
            let target_place = self.place(
                PlaceRoot::Value(source),
                vec![projection, PlaceProjection::Dereference],
                target,
            );
            let id = ReferenceId(self.p.objects.references.len() as u32);
            self.p.objects.references.push(Reference {
                id,
                created_in: site.scope,
                creation: ObjectCreation::At(produced_at),
                initial_owner: Owner::Scope {
                    scope: site.scope,
                    instance: self.ctx().domain,
                },
                ty,
                permission,
                formation: ReferenceFormation::Loan,
                origins: NonEmpty {
                    first: ReferenceOrigin {
                        target: target_place,
                        parent: None,
                        guard: site.guard,
                    },
                    rest: vec![],
                },
            });
            self.references.insert(value, id);
            self.value_entities.insert(value, EntityId::Reference(id));
        }
        value
    }
}
