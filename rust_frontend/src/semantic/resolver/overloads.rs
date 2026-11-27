//! The sole declaration-overloading exception: associated from(Inner) Outer.
use super::*;
impl Resolver<'_> {
    pub(super) fn register_from_overload(
        &mut self,
        n: ast::NodeId,
        scope: ScopeId,
        symbol: SymbolId,
        function: FunctionId,
        owner: TypeId,
        previous: Option<SymbolId>,
    ) -> Result<()> {
        let Some(previous) = previous else {
            return Ok(());
        };
        let mut members = match self.p.symbols.entries[previous.0 as usize].definition {
            SymbolDefinition::Function(previous) => vec![previous],
            SymbolDefinition::Overloads(set) => self.p.declarations.overloads[set.0 as usize]
                .members
                .clone(),
            _ => {
                return Err(self.fail(
                    n,
                    DiagnosticKind::DuplicateDeclaration,
                    "from conflicts with a non-function member",
                ));
            }
        };
        let signature = &self.p.declarations.signatures
            [self.functions[function.0 as usize].signature.0 as usize];
        if !matches!(signature.receiver, ReceiverMode::None)
            || signature.parameters.len() != 1
            || signature.result != owner
        {
            return Err(self.fail(
                n,
                DiagnosticKind::DuplicateDeclaration,
                "only associated from(Inner) Self functions may be overloaded",
            ));
        }
        let source = signature.parameters[0].ty;
        for previous in &members {
            let sig = &self.p.declarations.signatures
                [self.functions[previous.0 as usize].signature.0 as usize];
            if !matches!(sig.receiver, ReceiverMode::None)
                || sig.parameters.len() != 1
                || sig.result != owner
                || sig.parameters[0].ty == source
            {
                let mut error = self.fail(
                    n,
                    DiagnosticKind::DuplicateDeclaration,
                    "duplicate from source type or incompatible from overload signature",
                );
                error
                    .related
                    .push(self.syntax.ast.nodes[self.functions[previous.0 as usize].node.0].span);
                return Err(error);
            }
        }
        members.push(function);
        match self.p.symbols.entries[previous.0 as usize].definition {
            SymbolDefinition::Overloads(set) => {
                self.p.declarations.overloads[set.0 as usize].members = members
            }
            _ => {
                let set = OverloadSetId(self.p.declarations.overloads.len() as u32);
                let namespace = SymbolId(self.p.symbols.entries.len() as u32);
                let origin = self.builtin_origin("associated from overload set");
                self.p.symbols.entries.push(Symbol {
                    id: namespace,
                    spelling: "from".into(),
                    declaring_scope: scope,
                    origin,
                    visibility: self.p.symbols.entries[symbol.0 as usize].visibility.clone(),
                    definition: SymbolDefinition::Overloads(set),
                });
                self.p.declarations.overloads.push(FunctionOverloadSet {
                    id: set,
                    symbol: namespace,
                    members,
                });
                self.names[scope.0 as usize].insert("from".into(), namespace);
            }
        }
        Ok(())
    }
    pub(super) fn select_from_overload(
        &mut self,
        n: ast::NodeId,
        set: OverloadSetId,
        source_type: TypeId,
        expected: Option<TypeId>,
    ) -> Result<FunctionInstanceId> {
        let candidates = self.p.declarations.overloads[set.0 as usize]
            .members
            .clone();
        let mut matches = vec![];
        for function in candidates {
            let source = self.functions[function.0 as usize].clone();
            let mut substitutions = HashMap::new();
            if let Some(expected) = expected {
                if self
                    .infer_substitutions(n, source.result, expected, &mut substitutions)
                    .is_err()
                {
                    continue;
                }
            }
            if self
                .infer_substitutions(n, source.parameters[0].1, source_type, &mut substitutions)
                .is_err()
            {
                continue;
            }
            let parameters = &self.p.declarations.functions[function.0 as usize].type_parameters;
            let Some(actual) = parameters
                .iter()
                .map(|p| substitutions.get(p).copied())
                .collect::<Option<Vec<_>>>()
            else {
                continue;
            };
            let ty = self.substitute_type(source.parameters[0].1, &substitutions);
            if ty != source_type {
                continue;
            }
            matches.push((function, actual));
        }
        if matches.len() != 1 {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                format!(
                    "from requires exactly one overload for {}; found {}",
                    self.type_name(source_type),
                    matches.len()
                ),
            ));
        }
        let (function, actual) = matches.pop().unwrap();
        self.specialized_instance(function, actual)
    }
}
