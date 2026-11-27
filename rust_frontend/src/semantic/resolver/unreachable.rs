//! Non-executing source diagnostics. Reuses the resolver's symbol lookup; it does
//! not fabricate typed values, execution moments or owners for undefined names.
use super::*;
impl Resolver<'_> {
    fn unreachable_scope(
        &mut self,
        node: ast::NodeId,
        parent: ScopeId,
        after: ExecutionMomentId,
    ) -> ScopeId {
        let scope = ScopeId(self.names.len() as u32);
        let lexical = self.lexical_moment(
            node,
            LexicalContainer::FunctionDefinition(self.ctx().function),
        );
        self.p.scopes.entries.push(Scope {
            configuration: self.active_configuration,
            id: scope,
            lexical_scope: self.lexical_scopes[&node],
            lexical_parent: Some(parent),
            unchecked_boundary: self.ctx().unchecked.last().copied(),
            children: vec![],
            context: ScopeContext::Unreachable {
                body: self.ctx().body,
                after,
            },
            entry: ScopeEntry::Unreachable { lexical, after },
            exits: vec![],
            bindings: vec![],
            storage: ScopeStorageLink::DeclarationOnly,
        });
        self.p.scopes.entries[parent.0 as usize]
            .children
            .push(scope);
        self.names.push(HashMap::new());
        scope
    }
    pub(super) fn unreachable_tail(
        &mut self,
        block: ast::NodeId,
        statements: &[ast::NodeId],
        tail: Option<ast::NodeId>,
        after: ExecutionMomentId,
    ) {
        if statements.is_empty() && tail.is_none() {
            return;
        }
        let scope = self.unreachable_scope(block, self.ctx().scope, after);
        let cause = self.p.execution.execution_moments[after.0 as usize].lexical_origin(&self.p);
        let related = match &self.p.origins.origins[cause.0 as usize].role {
            OriginRole::Written { span, .. } => vec![Span {
                start: span.start as usize,
                end: span.end as usize,
            }],
            _ => vec![],
        };
        for node in statements.iter().copied().chain(tail) {
            self.ctx_mut().instruction = node;
            let origin = self.origin(node);
            let lexical = self.lexical[&node];
            self.p
                .unreachable_source
                .statements
                .push(UnreachableStatement {
                    syntax: self.syntax_id(node),
                    origin,
                    lexical,
                    scope,
                    after,
                });
            self.warnings.push(Diagnostic {
                file: SourceFileId(self.current_unit as u32),
                kind: DiagnosticKind::UnreachableStatement,
                span: self.syntax.ast.nodes[node.0].span,
                message: "unreachable statement".into(),
                related: related.clone(),
            });
            self.unreachable_walk(node, scope, after);
        }
    }
    fn diagnostic_binding(&mut self, node: ast::NodeId, name: ast::TokenRef, scope: ScopeId) {
        let id = DiagnosticBindingId(self.p.unreachable_source.bindings.len() as u32);
        let origin = self.origin(node);
        let symbol = self.anonymous_symbol(
            self.text(name),
            scope,
            SymbolDefinition::DiagnosticBinding(id),
            node,
        );
        self.p.unreachable_source.bindings.push(DiagnosticBinding {
            id,
            symbol,
            scope,
            origin,
        });
        let spelling = self.text(name).to_owned();
        self.names[scope.0 as usize].insert(spelling, symbol);
    }
    fn unreachable_pattern(&mut self, node: ast::NodeId, scope: ScopeId, after: ExecutionMomentId) {
        self.cover(node, SyntaxDisposition::Unreachable { after });
        match self.kind(node) {
            NodeKind::Pattern(ast::PatternSyntax::Binding { name, .. }) => {
                self.diagnostic_binding(node, *name, scope)
            }
            NodeKind::Pattern(ast::PatternSyntax::Variant {
                path,
                positional,
                fields,
            }) => {
                self.unreachable_walk(*path, scope, after);
                for child in positional.iter().flatten().chain(fields.iter().flatten()) {
                    self.unreachable_pattern(*child, scope, after);
                }
            }
            NodeKind::Pattern(ast::PatternSyntax::Tuple { elements }) => {
                for child in elements {
                    self.unreachable_pattern(*child, scope, after);
                }
            }
            NodeKind::Pattern(ast::PatternSyntax::Field { binding, .. }) => {
                self.unreachable_pattern(*binding, scope, after)
            }
            _ => {}
        }
    }
    fn unreachable_path(&mut self, node: ast::NodeId, path: &[ast::TokenRef], scope: ScopeId) {
        let Some(first) = path.first() else {
            return;
        };
        let last = path.last().unwrap();
        let span = Span {
            start: first.span.start,
            end: last.span.end,
        };
        let resolution = match self.scoped_path(node, scope, path) {
            Ok(symbol) => UnreachableNameResolution::Resolved(symbol),
            Err(mut diagnostic) => {
                diagnostic.span = span;
                diagnostic.message = if diagnostic.kind == DiagnosticKind::UnresolvedName {
                    format!(
                        "undefined name '{}' (in unreachable code)",
                        &self.syntax.source[span.start..span.end]
                    )
                } else {
                    format!("{} (in unreachable code)", diagnostic.message)
                };
                self.warnings.push(diagnostic);
                UnreachableNameResolution::Undefined {
                    spelling: self.syntax.source[span.start..span.end].to_owned(),
                }
            }
        };
        let origin = self.origin(node);
        self.p.unreachable_source.names.push(UnreachableNameUse {
            origin,
            span: ByteSpan {
                start: span.start as u32,
                end: span.end as u32,
            },
            scope,
            resolution,
        });
    }
    fn unreachable_walk(&mut self, node: ast::NodeId, scope: ScopeId, after: ExecutionMomentId) {
        self.cover(node, SyntaxDisposition::Unreachable { after });
        match self.kind(node) {
            NodeKind::Path {
                segments,
                arguments,
            }
            | NodeKind::Type(TypeSyntax::Path {
                segments,
                arguments,
            }) => {
                self.unreachable_path(node, segments, scope);
                for arg in arguments {
                    self.unreachable_walk(*arg, scope, after);
                }
            }
            NodeKind::Let { pattern, ty, value } => {
                if let Some(ty) = ty {
                    self.unreachable_walk(*ty, scope, after);
                }
                self.unreachable_walk(*value, scope, after);
                self.unreachable_pattern(*pattern, scope, after);
            }
            NodeKind::Block {
                annotations,
                statements,
                result,
            } => {
                let scope = self.unreachable_scope(node, scope, after);
                for child in annotations.iter().chain(statements).copied().chain(*result) {
                    self.unreachable_walk(child, scope, after);
                }
            }
            NodeKind::Closure {
                parameters,
                result,
                body,
                ..
            } => {
                let scope = self.unreachable_scope(node, scope, after);
                for parameter in parameters {
                    let NodeKind::Parameter { name, ty, .. } = self.kind(*parameter) else {
                        unreachable!()
                    };
                    if let Some(ty) = ty {
                        self.unreachable_walk(*ty, scope, after);
                    }
                    self.diagnostic_binding(*parameter, *name, scope);
                }
                if let Some(ty) = result {
                    self.unreachable_walk(*ty, scope, after);
                }
                self.unreachable_walk(*body, scope, after);
            }
            NodeKind::For {
                pattern,
                source,
                body,
            } => {
                self.unreachable_walk(*source, scope, after);
                let scope = self.unreachable_scope(node, scope, after);
                self.unreachable_pattern(*pattern, scope, after);
                self.unreachable_walk(*body, scope, after);
            }
            NodeKind::MatchArm { pattern, body } => {
                let scope = self.unreachable_scope(node, scope, after);
                self.unreachable_pattern(*pattern, scope, after);
                self.unreachable_walk(*body, scope, after);
            }
            NodeKind::If { condition, yes, no } => {
                if let NodeKind::LetCondition { pattern, value } = self.kind(*condition) {
                    self.unreachable_walk(*value, scope, after);
                    let yes_scope = self.unreachable_scope(*yes, scope, after);
                    self.unreachable_pattern(*pattern, yes_scope, after);
                    self.unreachable_walk(*yes, yes_scope, after);
                } else {
                    self.unreachable_walk(*condition, scope, after);
                    self.unreachable_walk(*yes, scope, after);
                }
                if let Some(no) = no {
                    self.unreachable_walk(*no, scope, after);
                }
            }
            NodeKind::FieldInitializer { name, value: None } => {
                self.unreachable_path(node, &[*name], scope)
            }
            NodeKind::NamedMove { name, .. } => self.unreachable_path(node, &[*name], scope),
            NodeKind::Foreign { token, .. } => {
                let crate::lexer::Payload::Foreign(block) =
                    &self.syntax.tokens[token.index].payload
                else {
                    unreachable!()
                };
                for span in &block.operands {
                    self.unreachable_path(
                        node,
                        &[ast::TokenRef {
                            index: token.index,
                            span: *span,
                        }],
                        scope,
                    );
                }
            }
            NodeKind::Pattern(_) => self.unreachable_pattern(node, scope, after),
            _ => {
                for child in self.kind(node).children() {
                    self.unreachable_walk(child, scope, after);
                }
            }
        }
    }
}
