//! Lexical configuration is part of specialization identity, never mutable globals.
use super::*;
impl Resolver<'_> {
    pub(super) fn configured_type(&mut self, ty: TypeId, configuration: ConfigurationId) -> TypeId {
        if configuration == ConfigurationId(0) {
            return ty;
        }
        match self.p.types.entries[ty.0 as usize].kind.clone() {
            TypeDefinition::Nominal {
                definition,
                arguments,
                configuration: old,
            } => {
                if old == configuration {
                    return ty;
                }
                let arguments: Vec<_> = arguments
                    .into_iter()
                    .map(|a| match a {
                        TypeArgument::Type(ty) => {
                            TypeArgument::Type(self.configured_type(ty, configuration))
                        }
                        other => other,
                    })
                    .collect();
                if let Some(existing)=self.p.types.entries.iter().find(|t|matches!(&t.kind,TypeDefinition::Nominal{definition:d,arguments:a,configuration:c}if *d==definition&&*c==configuration&&a==&arguments)){return existing.id;}
                let id = TypeId(self.p.types.entries.len() as u32);
                self.p.types.entries.push(ResolvedType {
                    id,
                    kind: TypeDefinition::Nominal {
                        definition,
                        arguments,
                        configuration,
                    },
                });
                id
            }
            TypeDefinition::Reference { target, permission } => {
                let target = self.configured_type(target, configuration);
                self.intern(TypeKey::Reference(
                    matches!(permission, ReferencePermission::Mutable),
                    target,
                ))
            }
            TypeDefinition::Array { element, length } => {
                let element = self.configured_type(element, configuration);
                self.intern(TypeKey::Array(element, length))
            }
            TypeDefinition::Slice { element } => {
                let element = self.configured_type(element, configuration);
                self.intern(TypeKey::Slice(element))
            }
            TypeDefinition::Tuple(parts) => {
                let parts = parts
                    .into_iter()
                    .map(|p| self.configured_type(p, configuration))
                    .collect();
                self.intern(TypeKey::Tuple(parts))
            }
            _ => ty,
        }
    }
    pub(super) fn override_value(&self, id: ConstantId) -> Option<ConstantValue> {
        let mut environment = Some(self.active_configuration);
        while let Some(config) = environment {
            let config = &self.p.contracts.environments[config.0 as usize];
            if let Some((_, value)) = config.replacements.iter().find(|(c, _)| *c == id) {
                return Some(value.clone());
            }
            environment = config.parent;
        }
        None
    }
    pub(super) fn install_override(&mut self, n: ast::NodeId, scope: ScopeId) -> Result<()> {
        let NodeKind::Annotation {
            syntax: AnnotationSyntax::Properties { entries },
            ..
        } = self.kind(n)
        else {
            unreachable!()
        };
        let mut replacements = vec![];
        for entry in entries {
            let NodeKind::Property { key, value } = self.kind(*entry) else {
                unreachable!()
            };
            let NodeKind::Path { segments, .. } = self.kind(*key) else {
                unreachable!()
            };
            let symbol = self.scoped_path(*key, scope, segments)?;
            let SymbolDefinition::Constant(constant) =
                self.p.symbols.entries[symbol.0 as usize].definition
            else {
                return Err(self.fail(
                    *key,
                    DiagnosticKind::InvalidType,
                    "override target is not a constant",
                ));
            };
            let definition = &self.p.declarations.constants[constant.0 as usize];
            if !definition.configurable {
                return Err(self.fail(
                    *key,
                    DiagnosticKind::InvalidType,
                    "only configurable constants can be overridden",
                ));
            }
            if replacements
                .iter()
                .any(|(previous, _)| *previous == constant)
            {
                return Err(self.fail(
                    *key,
                    DiagnosticKind::DuplicateDeclaration,
                    "duplicate override of the same constant identity",
                ));
            }
            let ty = definition.ty;
            let value = self.constant_expression(*value, ty, scope)?;
            replacements.push((constant, value));
        }
        replacements.sort_by_key(|(id, _)| id.0);
        let parent = self.active_configuration;
        let id = if let Some(environment) = self
            .p
            .contracts
            .environments
            .iter()
            .find(|e| e.parent == Some(parent) && e.replacements == replacements)
        {
            environment.id
        } else {
            let id = ConfigurationId(self.p.contracts.environments.len() as u32);
            self.p
                .contracts
                .environments
                .push(ConfigurationEnvironment {
                    id,
                    parent: Some(parent),
                    replacements: replacements.clone(),
                });
            id
        };
        let origin = self.origin(n);
        for (constant, value) in replacements {
            self.p.contracts.configuration.push(ResolvedConfiguration {
                scope,
                constant,
                value,
                origin,
            });
        }
        self.active_configuration = id;
        self.p.scopes.entries[scope.0 as usize].configuration = id;
        self.cover(n, SyntaxDisposition::Boundary(scope));
        Ok(())
    }
}
