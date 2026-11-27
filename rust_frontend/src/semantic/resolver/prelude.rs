//! Compiler-defined Option/Result identities. Recognition uses SymbolId, never
//! user type spelling; all generated declarations carry CompilerProvided origins.
use super::*;
impl Resolver<'_> {
    pub(super) fn compiler_symbol(
        &mut self,
        name: &str,
        scope: ScopeId,
        definition: SymbolDefinition,
    ) -> SymbolId {
        let id = SymbolId(self.p.symbols.entries.len() as u32);
        let origin = self.builtin_origin(name);
        self.p.symbols.entries.push(Symbol {
            id,
            spelling: name.into(),
            declaring_scope: scope,
            origin,
            visibility: Visibility::Public,
            definition,
        });
        self.names[scope.0 as usize].insert(name.into(), id);
        id
    }
    pub(super) fn install_prelude(&mut self) {
        let option = self.prelude_enum("Option", &["T"], &[("Some", Some(0)), ("None", None)]);
        let result = self.prelude_enum("Result", &["T", "E"], &[("Ok", Some(0)), ("Err", Some(1))]);
        self.p.well_known = WellKnownTypes {
            option: Some(option),
            result: Some(result),
        };
    }
    pub(super) fn prelude_enum(
        &mut self,
        name: &str,
        parameters: &[&str],
        variants: &[(&str, Option<usize>)],
    ) -> SymbolId {
        let symbol = self.compiler_symbol(name, ScopeId(0), SymbolDefinition::Type(self.unit));
        let ty = self.intern(TypeKey::Nominal(symbol, vec![]));
        self.p.symbols.entries[symbol.0 as usize].definition = SymbolDefinition::Type(ty);
        let scope =
            self.declaration_scope(self.syntax.ast.root, ScopeId(0), ScopeContext::Type(ty));
        self.owner_scopes.insert(ty, scope);
        self.names[scope.0 as usize].insert("Self".into(), symbol);
        let mut type_parameters = vec![];
        let mut types = vec![];
        for name in parameters {
            let id = TypeParameterId(self.p.types.parameters.len() as u32);
            let symbol = self.compiler_symbol(name, scope, SymbolDefinition::TypeParameter(id));
            self.p.types.parameters.push(TypeParameter {
                id,
                symbol,
                constraints: vec![],
            });
            type_parameters.push(id);
            types.push(self.intern(TypeKey::Parameter(id)));
        }
        self.nominal_parameters
            .insert(symbol, type_parameters.clone());
        let mut ids = vec![];
        for (name, payload) in variants {
            let id = VariantId(self.p.declarations.variants.len() as u32);
            let variant_symbol = self.compiler_symbol(name, scope, SymbolDefinition::Variant(id));
            self.names[0].insert((*name).into(), variant_symbol);
            let fields = if let Some(parameter) = payload {
                let field = FieldId(self.p.declarations.fields.len() as u32);
                let field_symbol = self.compiler_symbol(
                    &format!("{name}.0"),
                    scope,
                    SymbolDefinition::Field(field),
                );
                self.p.declarations.fields.push(FieldDefinition {
                    id: field,
                    symbol: field_symbol,
                    ty: types[*parameter],
                    default: FieldDefault::Unavailable,
                });
                vec![field]
            } else {
                vec![]
            };
            self.p.declarations.variants.push(VariantDefinition {
                id,
                template: None,
                symbol: variant_symbol,
                owner: ty,
                fields,
            });
            ids.push(id);
        }
        self.p.declarations.enums.push(EnumDefinition {
            symbol,
            parameters: type_parameters,
            ty,
            variants: NonEmpty {
                first: ids[0],
                rest: ids[1..].to_vec(),
            },
            methods: vec![],
        });
        symbol
    }
}
