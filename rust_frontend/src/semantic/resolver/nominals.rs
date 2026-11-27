//! Concrete nominal field specialization. Names and method templates are resolved
//! once; each actual type receives its own field IDs and resolved member types.
use super::*;
impl Resolver<'_> {
    pub(super) fn ensure_nominal(&mut self, ty: TypeId, node: ast::NodeId) -> Result<()> {
        let TypeDefinition::Nominal {
            definition,
            arguments,
            configuration,
        } = self.p.types.entries[ty.0 as usize].kind.clone()
        else {
            return Ok(());
        };
        if self.p.declarations.structs.iter().any(|s| s.ty == ty)
            || self.p.declarations.enums.iter().any(|s| s.ty == ty)
        {
            return Ok(());
        }
        let parameters = self
            .nominal_parameters
            .get(&definition)
            .cloned()
            .unwrap_or_default();
        if parameters.len() != arguments.len() {
            return Err(self.fail(
                node,
                DiagnosticKind::InvalidType,
                "generic nominal type has the wrong number of arguments",
            ));
        }
        let substitutions = parameters
            .iter()
            .copied()
            .zip(arguments.iter().filter_map(|a| {
                if let TypeArgument::Type(ty) = a {
                    Some(*ty)
                } else {
                    None
                }
            }))
            .collect::<HashMap<_, _>>();
        let template = self
            .p
            .declarations
            .structs
            .iter()
            .find(|s| s.symbol == definition)
            .cloned();
        let template_enum = self
            .p
            .declarations
            .enums
            .iter()
            .find(|s| s.symbol == definition)
            .cloned();
        let bare = self.intern(TypeKey::Nominal(definition, vec![]));
        let template_scope = self.owner_scopes[&bare];
        let caller_configuration = self.active_configuration;
        self.active_configuration = configuration;
        let caller_unit = self.current_unit;
        if let Some(unit) = self.type_sources.get(&definition).copied() {
            self.switch_unit(unit);
        }
        let source = self
            .type_nodes
            .get(&definition)
            .copied()
            .unwrap_or(self.syntax.ast.root);
        let parent = self.p.scopes.entries[template_scope.0 as usize]
            .lexical_parent
            .unwrap();
        let scope = self.declaration_scope(source, parent, ScopeContext::Type(ty));
        self.names[scope.0 as usize] = self.names[template_scope.0 as usize].clone();
        let alias = self.anonymous_symbol("Self", scope, SymbolDefinition::Type(ty), source);
        self.names[scope.0 as usize].insert("Self".into(), alias);
        self.owner_scopes.insert(ty, scope);
        if let Some(template) = template {
            let mut fields = vec![];
            for original in template.fields {
                let field = self.specialize_field(original, scope, source, &substitutions)?;
                let name = self.p.symbols.entries
                    [self.p.declarations.fields[field.0 as usize].symbol.0 as usize]
                    .spelling
                    .clone();
                self.names[scope.0 as usize]
                    .insert(name, self.p.declarations.fields[field.0 as usize].symbol);
                fields.push(field);
            }
            self.p.declarations.structs.push(StructDefinition {
                symbol: definition,
                parameters: vec![],
                ty,
                fields,
                methods: template.methods,
            });
        } else if let Some(template) = template_enum {
            let mut variants = vec![];
            for variant in std::iter::once(template.variants.first).chain(template.variants.rest) {
                let original = self.p.declarations.variants[variant.0 as usize].clone();
                let id = VariantId(self.p.declarations.variants.len() as u32);
                let name = self.p.symbols.entries[original.symbol.0 as usize]
                    .spelling
                    .clone();
                let symbol =
                    self.anonymous_symbol(&name, scope, SymbolDefinition::Variant(id), source);
                self.names[scope.0 as usize].insert(name, symbol);
                let fields = original
                    .fields
                    .into_iter()
                    .map(|field| self.specialize_field(field, scope, source, &substitutions))
                    .collect::<Result<Vec<_>>>()?;
                self.p.declarations.variants.push(VariantDefinition {
                    id,
                    template: Some(variant),
                    symbol,
                    owner: ty,
                    fields,
                });
                variants.push(id);
            }
            self.p.declarations.enums.push(EnumDefinition {
                symbol: definition,
                parameters: vec![],
                ty,
                variants: NonEmpty {
                    first: variants[0],
                    rest: variants[1..].to_vec(),
                },
                methods: template.methods,
            });
        } else {
            return Err(self.fail(
                node,
                DiagnosticKind::IncompleteRepresentation,
                "nominal declaration is not populated",
            ));
        }
        self.resolve_contracts(source, &parameters, &substitutions)?;
        self.active_configuration = caller_configuration;
        self.switch_unit(caller_unit);
        Ok(())
    }
    fn specialize_field(
        &mut self,
        field: FieldId,
        scope: ScopeId,
        source: ast::NodeId,
        substitutions: &HashMap<TypeParameterId, TypeId>,
    ) -> Result<FieldId> {
        let original = self.p.declarations.fields[field.0 as usize].clone();
        let id = FieldId(self.p.declarations.fields.len() as u32);
        let name = self.p.symbols.entries[original.symbol.0 as usize]
            .spelling
            .clone();
        let source_type =
            if let Some((written, declaring_scope)) = self.field_sources.get(&field).copied() {
                self.type_syntax(written, declaring_scope)?
            } else {
                self.configured_type(original.ty, self.active_configuration)
            };
        let ty = self.substitute_type(source_type, substitutions);
        let symbol = self.anonymous_symbol(&name, scope, SymbolDefinition::Field(id), source);
        self.p.symbols.entries[symbol.0 as usize].visibility = self.p.symbols.entries
            [original.symbol.0 as usize]
            .visibility
            .clone();
        self.p.declarations.fields.push(FieldDefinition {
            id,
            symbol,
            ty,
            default: original.default,
        });
        if let Some(source) = self.field_sources.get(&field).copied() {
            self.field_sources.insert(id, source);
        }
        Ok(id)
    }
}

impl Resolver<'_> {
    pub(super) fn variant_substitutions(
        &mut self,
        n: ast::NodeId,
        variant: VariantId,
        expected: Option<TypeId>,
    ) -> Result<HashMap<TypeParameterId, TypeId>> {
        let owner = self.p.declarations.variants[variant.0 as usize].owner;
        self.nominal_substitutions(n, owner, expected)
    }
    pub(super) fn nominal_substitutions(
        &mut self,
        n: ast::NodeId,
        owner: TypeId,
        expected: Option<TypeId>,
    ) -> Result<HashMap<TypeParameterId, TypeId>> {
        let TypeDefinition::Nominal {
            definition,
            arguments,
            ..
        } = self.p.types.entries[owner.0 as usize].kind.clone()
        else {
            unreachable!()
        };
        let parameters = self
            .nominal_parameters
            .get(&definition)
            .cloned()
            .unwrap_or_default();
        let mut substitutions = HashMap::new();
        for parameter in &parameters {
            if let Some(actual) = self.ctx().substitutions.get(parameter) {
                substitutions.insert(*parameter, *actual);
            }
        }
        if parameters.len() == arguments.len() {
            for (parameter, argument) in parameters.iter().zip(arguments) {
                if let TypeArgument::Type(actual) = argument {
                    substitutions.insert(*parameter, actual);
                }
            }
        }
        if let Some(expected) = expected {
            let TypeDefinition::Nominal {
                definition: actual,
                arguments,
                ..
            } = self.p.types.entries[expected.0 as usize].kind.clone()
            else {
                return Err(self.fail(
                    n,
                    DiagnosticKind::TypeMismatch,
                    "enum construction requires the expected enum type",
                ));
            };
            if actual != definition {
                return Err(self.fail(
                    n,
                    DiagnosticKind::TypeMismatch,
                    "enum constructor belongs to a different type",
                ));
            }
            for (parameter, argument) in parameters.iter().zip(arguments) {
                if let TypeArgument::Type(actual) = argument {
                    substitutions.insert(*parameter, actual);
                }
            }
        }
        let path = match self.kind(n) {
            NodeKind::Call { callee, .. } => Some(*callee),
            NodeKind::Construct { path, .. } => *path,
            NodeKind::Path { .. } => Some(n),
            _ => None,
        };
        if let Some(path) = path {
            if let NodeKind::Path { arguments, .. } = self.kind(path) {
                if !arguments.is_empty() {
                    if arguments.len() != parameters.len() {
                        return Err(self.fail(
                            n,
                            DiagnosticKind::InvalidType,
                            "enum generic argument count is incorrect",
                        ));
                    }
                    for (parameter, argument) in parameters.iter().zip(arguments) {
                        let ty = self.type_syntax(*argument, self.ctx().scope)?;
                        substitutions.insert(*parameter, ty);
                    }
                }
            }
        }
        Ok(substitutions)
    }
    pub(super) fn specialized_variant(
        &mut self,
        n: ast::NodeId,
        variant: VariantId,
        substitutions: &HashMap<TypeParameterId, TypeId>,
    ) -> Result<VariantId> {
        let owner = self.p.declarations.variants[variant.0 as usize].owner;
        let TypeDefinition::Nominal { definition, .. } =
            self.p.types.entries[owner.0 as usize].kind.clone()
        else {
            unreachable!()
        };
        let parameters = self
            .nominal_parameters
            .get(&definition)
            .cloned()
            .unwrap_or_default();
        if parameters.is_empty() {
            return Ok(variant);
        }
        let arguments=parameters.iter().map(|p|substitutions.get(p).copied().ok_or_else(||self.fail(n,DiagnosticKind::InvalidType,format!("cannot infer enum type argument '{}' for '{}' in function '{}'; return context {}; supply a type annotation or explicit arguments",self.p.symbols.entries[self.p.types.parameters[p.0 as usize].symbol.0 as usize].spelling,self.p.symbols.entries[definition.0 as usize].spelling,self.p.symbols.entries[self.p.declarations.functions[self.ctx().function.0 as usize].symbol.0 as usize].spelling,self.ctx().return_type.map(|ty|self.type_name(ty)).unwrap_or_else(||"inferred".into()))))).collect::<Result<Vec<_>>>()?;
        let actual = self.intern(TypeKey::Nominal(definition, arguments));
        self.variant_for_type(n, variant, actual)
    }
    pub(super) fn variant_for_type(
        &mut self,
        n: ast::NodeId,
        variant: VariantId,
        actual: TypeId,
    ) -> Result<VariantId> {
        let original = self.p.declarations.variants[variant.0 as usize].clone();
        if original.owner == actual {
            return Ok(variant);
        }
        let (
            TypeDefinition::Nominal { definition: a, .. },
            TypeDefinition::Nominal { definition: b, .. },
        ) = (
            &self.p.types.entries[original.owner.0 as usize].kind,
            &self.p.types.entries[actual.0 as usize].kind,
        )
        else {
            return Err(self.fail(
                n,
                DiagnosticKind::TypeMismatch,
                "pattern subject is not the variant's enum",
            ));
        };
        if a != b {
            return Err(self.fail(
                n,
                DiagnosticKind::TypeMismatch,
                "variant belongs to a different enum",
            ));
        }
        let template = original.template.unwrap_or(variant);
        self.ensure_nominal(actual, n)?;
        self.p
            .declarations
            .variants
            .iter()
            .find(|v| v.owner == actual && v.template == Some(template))
            .map(|v| v.id)
            .ok_or_else(|| {
                self.fail(
                    n,
                    DiagnosticKind::IncompleteRepresentation,
                    "concrete variant specialization is missing",
                )
            })
    }
}
