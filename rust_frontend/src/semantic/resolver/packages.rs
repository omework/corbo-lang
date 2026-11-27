//! Parsed-package resolution preserves each original source/token/AST unit.
use super::*;

#[derive(Debug)]
pub struct ParsedModule {
    pub package: String,
    /// Module path within the package; files with the same path share a scope.
    pub path: Vec<String>,
    pub file_path: String,
    pub syntax: ast::ParsedUnit,
}
#[derive(Debug)]
pub struct ResolvedPackage {
    pub modules: Vec<ParsedModule>,
    pub logical: LogicalDestinationResult,
    pub warnings: Vec<Diagnostic>,
}
#[derive(Default)]
pub(super) struct SourceState {
    pub(super) imports: HashMap<String, (SymbolId, SyntaxNodeId)>,
    offset: u32,
    pub(super) module: Option<ModuleId>,
    lexical_scopes: HashMap<ast::NodeId, LexicalScopeId>,
    origins: HashMap<ast::NodeId, SourceOriginId>,
    lexical: HashMap<ast::NodeId, LexicalMomentId>,
    coverage: HashMap<ast::NodeId, Vec<SyntaxDisposition>>,
}
impl SourceState {
    pub(super) fn new(offset: u32, module: ModuleId) -> Self {
        Self {
            offset,
            module: Some(module),
            ..Self::default()
        }
    }
}
pub fn resolve_package(
    modules: Vec<ParsedModule>,
) -> std::result::Result<ResolvedPackage, Vec<Diagnostic>> {
    resolve_package_for_target(modules, super::host_target())
}

/// Target facts are supplied before declaration/import selection. No code is emitted.
pub fn resolve_package_for_target(
    modules: Vec<ParsedModule>,
    target: TargetDescription,
) -> std::result::Result<ResolvedPackage, Vec<Diagnostic>> {
    if modules.is_empty() {
        return Err(vec![Diagnostic {
            file: SourceFileId(0),
            kind: DiagnosticKind::InvalidType,
            span: Span { start: 0, end: 0 },
            message: "a parsed package requires at least one source unit".into(),
            related: vec![],
        }]);
    }
    let result = (|| -> Result<_> {
        let mut r = Resolver::new(&modules[0].syntax, target)?;
        r.units = modules.iter().map(|m| &m.syntax).collect();
        let mut offset = r.units[0].ast.nodes.len() as u32;
        for unit in 1..modules.len() {
            r.source_states.push(SourceState::new(offset, ModuleId(0)));
            offset += r.units[unit].ast.nodes.len() as u32;
            r.p.origins.files.push(SourceFile {
                id: SourceFileId(unit as u32),
                path: modules[unit].file_path.clone(),
                source: modules[unit].syntax.source.clone(),
            });
            r.switch_unit(unit);
            r.source_scopes(r.syntax.ast.root, None);
        }
        r.p.origins.files[0].path = modules[0].file_path.clone();
        r.switch_unit(0);
        let mut roots = HashMap::new();
        let mut paths: HashMap<(String, Vec<String>), ModuleId> = HashMap::new();
        for unit in 0..modules.len() {
            r.switch_unit(unit);
            let input = &modules[unit];
            let root = if let Some(root) = roots.get(&input.package).copied() {
                root
            } else {
                let package = PackageId(r.p.declarations.packages.len() as u32);
                r.p.declarations.packages.push(PackageDefinition {
                    id: package,
                    name: input.package.clone(),
                    modules: vec![],
                });
                let module = r.package_module(package, vec![], ScopeId(0));
                let symbol = r.module_symbol(&input.package, module, ScopeId(0));
                r.names[0].insert(input.package.clone(), symbol);
                roots.insert(input.package.clone(), module);
                paths.insert((input.package.clone(), vec![]), module);
                module
            };
            let package = r.p.declarations.modules[root.0 as usize].package;
            let mut parent = root;
            for depth in 1..=input.path.len() {
                let path = input.path[..depth].to_vec();
                parent = if let Some(module) =
                    paths.get(&(input.package.clone(), path.clone())).copied()
                {
                    module
                } else {
                    let scope = r.p.declarations.modules[parent.0 as usize].scope;
                    let module = r.package_module(package, path.clone(), scope);
                    let symbol = r.module_symbol(&path[depth - 1], module, scope);
                    r.names[scope.0 as usize].insert(path[depth - 1].clone(), symbol);
                    paths.insert((input.package.clone(), path), module);
                    module
                };
            }
            r.source_states[unit].module = Some(parent);
        }
        r.prepared_package = true;
        // Type identities precede imports/signatures. Imports are resolved to a
        // fixed point before signatures, then completed after function declaration.
        for unit in 0..modules.len() {
            r.switch_unit(unit);
            let scope = r.current_module_scope();
            let NodeKind::Module { items } = r.kind(r.syntax.ast.root) else {
                unreachable!()
            };
            r.declare_types(items, scope)?;
        }
        r.bind_std_native_declarations(&modules)?;
        r.package_imports(false)?;
        for unit in 0..modules.len() {
            r.switch_unit(unit);
            let scope = r.current_module_scope();
            let NodeKind::Module { items } = r.kind(r.syntax.ast.root) else {
                unreachable!()
            };
            r.collect(items, scope, None)?;
        }
        r.package_imports(true)?;
        r.switch_unit(0);
        let logical = r.run()?;
        super::super::validate_population(&logical).map_err(|e| Diagnostic {
            file: SourceFileId(0),
            kind: DiagnosticKind::IncompleteRepresentation,
            span: Span { start: 0, end: 0 },
            message: format!("{e:?}"),
            related: vec![],
        })?;
        Ok((logical, r.warnings))
    })();
    result
        .map(|(logical, warnings)| ResolvedPackage {
            modules,
            logical,
            warnings,
        })
        .map_err(|e| vec![e])
}
impl<'a> Resolver<'a> {
    pub(super) fn syntax_id(&self, n: ast::NodeId) -> SyntaxNodeId {
        SyntaxNodeId(self.source_states[self.current_unit].offset + n.0 as u32)
    }
    pub(super) fn switch_unit(&mut self, unit: usize) {
        if self.current_unit == unit {
            return;
        }
        let old = &mut self.source_states[self.current_unit];
        old.lexical_scopes = std::mem::take(&mut self.lexical_scopes);
        old.origins = std::mem::take(&mut self.origins);
        old.lexical = std::mem::take(&mut self.lexical);
        old.coverage = std::mem::take(&mut self.coverage);
        let state = &mut self.source_states[unit];
        self.lexical_scopes = std::mem::take(&mut state.lexical_scopes);
        self.origins = std::mem::take(&mut state.origins);
        self.lexical = std::mem::take(&mut state.lexical);
        self.coverage = std::mem::take(&mut state.coverage);
        self.current_unit = unit;
        self.syntax = self.units[unit];
    }
    fn current_module_scope(&self) -> ScopeId {
        self.p.declarations.modules
            [self.source_states[self.current_unit].module.unwrap().0 as usize]
            .scope
    }
    fn package_module(
        &mut self,
        package: PackageId,
        path: Vec<String>,
        parent: ScopeId,
    ) -> ModuleId {
        let id = ModuleId(self.p.declarations.modules.len() as u32);
        let scope = self.declaration_scope(self.syntax.ast.root, parent, ScopeContext::Module(id));
        self.p.declarations.modules.push(ModuleDefinition {
            id,
            package,
            path,
            scope,
        });
        self.p.declarations.packages[package.0 as usize]
            .modules
            .push(id);
        id
    }
    fn module_symbol(&mut self, name: &str, module: ModuleId, scope: ScopeId) -> SymbolId {
        let id = SymbolId(self.p.symbols.entries.len() as u32);
        let origin = self.builtin_origin("parsed package namespace");
        self.p.symbols.entries.push(Symbol {
            id,
            spelling: name.into(),
            declaring_scope: scope,
            origin,
            visibility: Visibility::Public,
            definition: SymbolDefinition::Module(module),
        });
        id
    }
    pub(super) fn module_for_scope(&self, mut scope: ScopeId) -> ModuleId {
        loop {
            if let ScopeContext::Module(module) = self.p.scopes.entries[scope.0 as usize].context {
                return module;
            }
            let Some(parent) = self.p.scopes.entries[scope.0 as usize].lexical_parent else {
                return ModuleId(0);
            };
            scope = parent;
        }
    }
    pub(super) fn visible_from(&self, symbol: SymbolId, scope: ScopeId) -> bool {
        let symbol = &self.p.symbols.entries[symbol.0 as usize];
        matches!(symbol.visibility, Visibility::Public)
            || self.module_for_scope(symbol.declaring_scope) == self.module_for_scope(scope)
    }
    fn import_nodes(&self, n: ast::NodeId, out: &mut Vec<ast::NodeId>) -> Result<()> {
        match self.kind(n) {
            NodeKind::Import { .. } => out.push(n),
            NodeKind::Module { items } => {
                for item in items {
                    self.import_nodes(*item, out)?;
                }
            }
            NodeKind::Conditional {
                condition, items, ..
            } => {
                if self.target_condition(*condition)? {
                    for item in items {
                        self.import_nodes(*item, out)?;
                    }
                }
            }
            _ => {}
        }
        Ok(())
    }
    fn bind_std_native_declarations(&mut self, modules: &[ParsedModule]) -> Result<()> {
        let runtime_exports = self.names[self.runtime_scope.0 as usize].clone();
        let runtime_modules: Vec<_> = self
            .p
            .declarations
            .modules
            .iter()
            .filter(|m| {
                self.p.declarations.packages[m.package.0 as usize].name == "std"
                    && m.path == ["runtime"]
            })
            .map(|m| (m.id, m.scope))
            .collect();
        for (module, scope) in runtime_modules {
            let mut symbols = vec![];
            for (name, symbol) in &runtime_exports {
                if self.names[scope.0 as usize]
                    .insert(name.clone(), *symbol)
                    .is_some()
                {
                    return Err(self.fail(
                        self.syntax.ast.root,
                        DiagnosticKind::DuplicateDeclaration,
                        "source namespace conflicts with a compiler runtime export",
                    ));
                }
                symbols.push(*symbol);
            }
            symbols.sort_by_key(|s| s.0);
            self.p
                .declarations
                .native_namespaces
                .push(NativeNamespaceBinding {
                    module,
                    compiler_scope: self.runtime_scope,
                    symbols,
                });
        }
        for (unit, input) in modules.iter().enumerate() {
            if input.package != "std" || !input.path.is_empty() {
                continue;
            }
            self.switch_unit(unit);
            let scope = self.current_module_scope();
            for (name, compiler_name) in [
                ("Pool", "Pool"),
                ("Vector", "Vector"),
                ("HashMap", "HashMap"),
                ("String", "String"),
                ("BoundedString", "String"),
                ("PoolError", "PoolError"),
            ] {
                let Some(symbol) = self.names[scope.0 as usize].get(name).copied() else {
                    continue;
                };
                let compiler_symbol = self.names[0][compiler_name];
                if let Some(constructor) = self.native_constructors.get(&compiler_symbol).copied() {
                    self.native_constructors.insert(symbol, constructor);
                } else {
                    self.p.symbols.entries[symbol.0 as usize].definition = self.p.symbols.entries
                        [compiler_symbol.0 as usize]
                        .definition
                        .clone();
                }
                if !self
                    .p
                    .declarations
                    .native_bindings
                    .iter()
                    .any(|b| b.symbol == symbol)
                {
                    let origin = self.p.symbols.entries[symbol.0 as usize].origin;
                    self.p.declarations.native_bindings.push(NativeTypeBinding {
                        symbol,
                        compiler_symbol,
                        origin,
                    });
                }
            }
            if !self.names[scope.0 as usize].contains_key("A") {
                let allocation = self.names[0]["A"];
                self.names[scope.0 as usize].insert("A".into(), allocation);
            }
        }
        Ok(())
    }
    fn package_imports(&mut self, strict: bool) -> Result<()> {
        let mut pending = vec![];
        for unit in 0..self.units.len() {
            self.switch_unit(unit);
            let mut nodes = vec![];
            self.import_nodes(self.syntax.ast.root, &mut nodes)?;
            pending.extend(nodes.into_iter().map(|n| (unit, n)));
        }
        loop {
            let before = pending.len();
            let mut remaining = vec![];
            for (unit, node) in pending {
                self.switch_unit(unit);
                let scope = self.current_module_scope();
                if !self.import_node(node, scope)? {
                    remaining.push((unit, node));
                }
            }
            if remaining.is_empty() {
                return Ok(());
            }
            if remaining.len() == before {
                if strict {
                    let (unit, node) = remaining[0];
                    self.switch_unit(unit);
                    return Err(self.fail(
                        node,
                        DiagnosticKind::UnresolvedName,
                        "cannot resolve imported component in the supplied parsed package",
                    ));
                }
                return Ok(());
            }
            pending = remaining;
        }
    }
    pub(super) fn file_import(&self, scope: ScopeId, name: &str) -> Option<SymbolId> {
        if self.prepared_package && scope == self.current_module_scope() {
            self.source_states[self.current_unit]
                .imports
                .get(name)
                .map(|v| v.0)
        } else {
            None
        }
    }
    fn import_node(&mut self, n: ast::NodeId, scope: ScopeId) -> Result<bool> {
        let NodeKind::Import {
            path,
            entries,
            alias,
        } = self.kind(n)
        else {
            unreachable!()
        };
        let imports = if let Some(entries) = entries {
            let mut result = vec![];
            for entry in entries {
                let NodeKind::ImportEntry { name, alias } = self.kind(*entry) else {
                    unreachable!()
                };
                let mut full = path.clone();
                full.push(*name);
                result.push((full, *alias));
            }
            result
        } else {
            vec![(path.clone(), *alias)]
        };
        let mut resolved: Vec<(String, SymbolId)> = vec![];
        let mut complete = true;
        let syntax = self.syntax_id(n);
        for (path, alias) in imports {
            let symbol = match self.scoped_path(n, scope, &path) {
                Ok(symbol) => symbol,
                Err(error) => {
                    if error.message.contains("private") {
                        return Err(error);
                    }
                    complete = false;
                    continue;
                }
            };
            if !self.visible_from(symbol, scope) {
                return Err(self.fail(
                    n,
                    DiagnosticKind::UnresolvedName,
                    "imported component is private to its declaring module",
                ));
            }
            let name = self.text(alias.unwrap_or(*path.last().unwrap())).to_owned();
            let previous = self.names[scope.0 as usize]
                .get(&name)
                .copied()
                .or_else(|| {
                    self.source_states[self.current_unit]
                        .imports
                        .get(&name)
                        .filter(|(_, node)| *node != syntax)
                        .map(|(symbol, _)| *symbol)
                })
                .or_else(|| {
                    resolved
                        .iter()
                        .find(|(alias, _)| alias == &name)
                        .map(|(_, symbol)| *symbol)
                });
            if let Some(previous) = previous {
                let mut error = self.fail(
                    n,
                    DiagnosticKind::DuplicateDeclaration,
                    format!("import '{name}' conflicts with another declaration or import"),
                );
                if let OriginRole::Written { ref span, .. } = self.p.origins.origins
                    [self.p.symbols.entries[previous.0 as usize].origin.0 as usize]
                    .role
                {
                    error.related.push(Span {
                        start: span.start as usize,
                        end: span.end as usize,
                    });
                }
                return Err(error);
            }
            resolved.push((name, symbol));
        }
        for (name, symbol) in resolved {
            let already = self.source_states[self.current_unit]
                .imports
                .contains_key(&name);
            self.source_states[self.current_unit]
                .imports
                .insert(name.clone(), (symbol, syntax));
            if !already {
                let origin = self.origin(n);
                self.p.declarations.imports.push(ResolvedImport {
                    file: SourceFileId(self.current_unit as u32),
                    scope,
                    local_name: name,
                    target: symbol,
                    origin,
                });
            }
            self.cover(n, SyntaxDisposition::Declaration(symbol));
        }
        Ok(complete)
    }
}
