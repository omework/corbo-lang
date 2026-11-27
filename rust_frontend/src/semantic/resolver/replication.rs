//! Resolve structural duplication once; the later checker decides eligibility.
use super::*;

impl Resolver<'_> {
    pub(super) fn replication_plan(
        &mut self,
        ty: TypeId,
        source: ast::NodeId,
        active: &mut HashSet<TypeId>,
    ) -> Result<StructuralReplicationPlan> {
        self.ensure_nominal(ty, source)?;
        let strategy = if self.primitive(ty) {
            StructuralReplicationStrategy::Primitive
        } else if !active.insert(ty) {
            StructuralReplicationStrategy::Ineligible(
                StructuralReplicationRestriction::RecursiveType,
            )
        } else {
            let drop = self
                .owner_scopes
                .get(&ty)
                .and_then(|scope| self.names[scope.0 as usize].get("drop"))
                .and_then(
                    |symbol| match self.p.symbols.entries[symbol.0 as usize].definition {
                        SymbolDefinition::Function(function) => Some(function),
                        _ => None,
                    },
                );
            let fields = self
                .p
                .declarations
                .structs
                .iter()
                .find(|record| record.ty == ty)
                .map(|record| record.fields.clone());
            let strategy = if let Some(function) = drop {
                StructuralReplicationStrategy::Ineligible(
                    StructuralReplicationRestriction::CustomDestructor(function),
                )
            } else if let Some(fields) = fields {
                let mut plans = Vec::with_capacity(fields.len());
                for field in fields {
                    let field_ty = self.p.declarations.fields[field.0 as usize].ty;
                    plans.push(StructuralFieldReplication {
                        field,
                        plan: self.replication_plan(field_ty, source, active)?,
                    });
                }
                StructuralReplicationStrategy::Struct(plans)
            } else {
                StructuralReplicationStrategy::Ineligible(
                    StructuralReplicationRestriction::NonStructuralType,
                )
            };
            active.remove(&ty);
            strategy
        };
        Ok(StructuralReplicationPlan { ty, strategy })
    }
}
