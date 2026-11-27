//! Wrapper dereference uses the same instance resolution as ordinary method calls.
use super::*;
impl Resolver<'_> {
    pub(super) fn dereference_method(
        &mut self,
        n: ast::NodeId,
        place: EvaluatedPlaceId,
        mutable: bool,
    ) -> Result<(ValueId, ResolvedDereference)> {
        let definition = self.p.objects.evaluated_places[place.0 as usize].definition;
        let ty = self.p.objects.places[definition.0 as usize].ty;
        self.ensure_nominal(ty, n)?;
        let name = if mutable { "mut_ref" } else { "ref" };
        let symbol = self
            .owner_scopes
            .get(&ty)
            .and_then(|scope| self.names[scope.0 as usize].get(name))
            .copied()
            .ok_or_else(|| {
                self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    format!(
                        "{} cannot be dereferenced: missing {name}()",
                        self.type_name(ty)
                    ),
                )
            })?;
        let SymbolDefinition::Function(function) =
            self.p.symbols.entries[symbol.0 as usize].definition
        else {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "dereference member is not a method",
            ));
        };
        let mode = self.p.declarations.signatures
            [self.functions[function.0 as usize].signature.0 as usize]
            .receiver
            .clone();
        let receiver = match mode {
            ReceiverMode::Shared(_) => self.borrow(n, place, false)?.value,
            ReceiverMode::Mutable(_) => self.borrow(n, place, true)?.value,
            _ => {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidCall,
                    "dereference method must borrow its receiver",
                ));
            }
        };
        let value = self
            .invoke_function(n, function, Some(receiver), &[], &[], None)?
            .value;
        let TypeDefinition::Reference { permission, .. } = self.p.types.entries
            [self.vtype(value).0 as usize]
            .kind
            .clone()
        else {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                "dereference method must return a reference",
            ));
        };
        if mutable && !matches!(permission, ReferencePermission::Mutable) {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                "mut_ref() must return a mutable reference",
            ));
        }
        let operation = match self.p.values.entries[value.0 as usize].definition {
            ValueDefinition::OperationResult { operation, .. } => operation,
            _ => unreachable!(),
        };
        let target = self.p.bodies[self.ctx().body.0 as usize]
            .operations
            .iter()
            .find_map(|op| match op {
                Operation::MethodCall(call) if call.site.id == operation => {
                    match call.target.target {
                        MethodTarget::Concrete(target) => Some(target),
                        _ => None,
                    }
                }
                _ => None,
            })
            .expect("invoke_function emits a resolved method call");
        Ok((
            value,
            ResolvedDereference::MethodResult {
                function: target,
                permission,
            },
        ))
    }
}
