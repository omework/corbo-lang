//! Trusted foreign boundaries. Foreign text remains opaque after lexical scanning.
use super::*;
impl Resolver<'_> {
    pub(super) fn unchecked_expression(
        &mut self,
        n: ast::NodeId,
        body: ast::NodeId,
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        let scope = ScopeId(self.names.len() as u32);
        let site = self.site(n, ExecutionPhase::Enter);
        self.emit(Operation::EnterUnchecked(EnterUnchecked { site, scope }));
        self.ctx_mut().unchecked.push(scope);
        let result = self.block_expression(body, expected)?;
        self.ctx_mut().unchecked.pop();
        if self.vtype(result.value) == self.never {
            return Ok(result);
        }
        let site = self.site(n, ExecutionPhase::Exit);
        self.emit(Operation::ExitUnchecked(ExitUnchecked { site, scope }));
        Ok(result)
    }
    pub(super) fn address_expression(
        &mut self,
        n: ast::NodeId,
        args: &[ast::NodeId],
    ) -> Result<Expr> {
        let boundary = self.ctx().unchecked.last().copied().ok_or_else(|| {
            self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "addr() is only available inside @unchecked",
            )
        })?;
        if args.len() != 1 {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "addr() requires one addressable value",
            ));
        }
        let source = self.place_expression(args[0])?;
        let definition = self.p.objects.evaluated_places[source.0 as usize].definition;
        let place = self.p.objects.places[definition.0 as usize].clone();
        let targets = match place.root {
            PlaceRoot::Value(value) => self
                .references
                .get(&value)
                .copied()
                .map(|reference| {
                    let reference = &self.p.objects.references[reference.0 as usize];
                    std::iter::once(reference.origins.first.target)
                        .chain(reference.origins.rest.iter().map(|origin| origin.target))
                        .collect::<Vec<_>>()
                })
                .unwrap_or_else(|| vec![definition]),
            _ => vec![definition],
        };
        let ty = self.intern(TypeKey::Numeric(NumericType::Usize));
        let site = self.site(n, ExecutionPhase::Compute);
        let result = self.op_value(
            &site,
            ty,
            vec![DependencyRequirement::ConfinedToUncheckedScope(boundary)],
        );
        self.emit(Operation::AddressOf(AddressOf {
            site,
            source,
            result,
            boundary,
        }));
        self.address_targets.insert(result, targets);
        Ok(Expr { value: result })
    }

    fn foreign_address_targets(&self, value: ValueId, seen: &mut HashSet<ValueId>) -> Vec<PlaceId> {
        if !seen.insert(value) {
            return vec![];
        }
        if let Some(targets) = self.address_targets.get(&value) {
            return targets.clone();
        }
        match self.p.values.provenance
            [self.p.values.entries[value.0 as usize].provenance.0 as usize]
            .kind
        {
            ProvenanceKind::Copy { source, .. }
            | ProvenanceKind::Forward { source, .. }
            | ProvenanceKind::Move { source, .. } => self.foreign_address_targets(source, seen),
            _ => vec![],
        }
    }
    pub(super) fn foreign_expression(
        &mut self,
        n: ast::NodeId,
        token: ast::TokenRef,
        includes: &[ast::TokenRef],
    ) -> Result<Expr> {
        let boundary = self.ctx().unchecked.last().copied().ok_or_else(|| {
            self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "foreign blocks require an enclosing @unchecked boundary",
            )
        })?;
        let crate::lexer::Payload::Foreign(block) = &self.syntax.tokens[token.index].payload else {
            unreachable!()
        };
        let kind = self.syntax.tokens[token.index].kind;
        let mut operands = vec![];
        let mut fragments = vec![];
        let mut cursor = block.body.start;
        let mut writebacks: Vec<(Option<BindingId>, EvaluatedPlaceId, Option<ValueId>, TypeId)> =
            vec![];
        for span in &block.operands {
            let spelling = &self.syntax.source[span.start..span.end];
            let symbol = self
                .lookup(self.ctx().scope, spelling)
                .ok_or_else(|| Diagnostic {
                    file: SourceFileId(self.current_unit as u32),
                    kind: DiagnosticKind::UnresolvedName,
                    span: *span,
                    message: format!("cannot resolve foreign operand '{spelling}'"),
                    related: vec![],
                })?;
            let SymbolDefinition::Binding(binding) =
                self.p.symbols.entries[symbol.0 as usize].definition
            else {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    "foreign operand must name a value binding",
                ));
            };
            let definition = self.p.scopes.bindings[binding.0 as usize].clone();
            let value = self.ctx().bindings[&binding];
            let place = self.place(PlaceRoot::Binding(binding), vec![], definition.ty);
            let place = self.evaluated_place(n, place, vec![]);
            let mode = if definition.mutable {
                writebacks.push((Some(binding), place, Some(value), definition.ty));
                ForeignOperandMode::MutableStorage
            } else if self.primitive(definition.ty) {
                ForeignOperandMode::ScalarValue
            } else {
                ForeignOperandMode::SharedStorage
            };
            for target in self.foreign_address_targets(value, &mut HashSet::new()) {
                let target_place = self.p.objects.places[target.0 as usize].clone();
                let target = self.evaluated_place(n, target, vec![]);
                let (binding, previous) = match target_place.root {
                    PlaceRoot::Binding(binding) if target_place.projections.is_empty() => {
                        (Some(binding), self.ctx().bindings.get(&binding).copied())
                    }
                    _ => (None, None),
                };
                writebacks.push((binding, target, previous, target_place.ty));
            }
            let id = ForeignOperandId(operands.len() as u32);
            fragments.push(ForeignFragment::Text(
                self.syntax.source[cursor..span.start - 2].to_owned(),
            ));
            fragments.push(ForeignFragment::Operand(id));
            cursor = span.end + 1;
            operands.push(ForeignOperand {
                id,
                place,
                mode,
                spelling: spelling.into(),
                value,
                ty: definition.ty,
                origin: self.origin(n),
            });
        }
        fragments.push(ForeignFragment::Text(
            self.syntax.source[cursor..block.body.end].to_owned(),
        ));
        let mut headers = vec![];
        for entry in includes {
            let header = block
                .header_tokens
                .iter()
                .find(|t| t.span == entry.span)
                .ok_or_else(|| {
                    self.fail(
                        n,
                        DiagnosticKind::IncompleteRepresentation,
                        "foreign include token is missing from lexical payload",
                    )
                })?;
            let crate::lexer::Payload::Text(bytes) = &header.payload else {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    "foreign includes must be text literals",
                ));
            };
            let header = String::from_utf8(bytes.clone()).map_err(|_| {
                self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    "foreign include path is not UTF-8",
                )
            })?;
            if !headers.contains(&header) {
                headers.push(header);
            }
        }
        let region = ForeignRegionId(self.p.foreign_regions.len() as u32);
        let origin = self.origin(n);
        self.p.foreign_regions.push(ForeignRegion {
            id: region,
            fragments,
            headers,
            origin,
        });
        let mut site = self.site(n, ExecutionPhase::Invoke);
        let written = self.phase(&mut site, ExecutionPhase::EstablishEffect);
        let mut outputs = vec![];
        let mut seen_writebacks = HashSet::new();
        for (binding, place, previous, ty) in writebacks {
            let definition = self.p.objects.evaluated_places[place.0 as usize].definition;
            if !seen_writebacks.insert(definition) {
                continue;
            }
            let value = self.value(
                ty,
                ValueDefinition::OperationResult {
                    operation: site.id,
                    produced_at: written,
                },
                ProvenanceKind::Constructed(site.id),
                previous
                    .map(|previous| self.dependencies(previous))
                    .unwrap_or_default(),
            );
            if let Some(binding) = binding {
                self.ctx_mut().bindings.insert(binding, value);
            }
            outputs.push(ForeignWriteback {
                place,
                result: value,
            });
        }
        let available = self.phase(&mut site, ExecutionPhase::Receive);
        let result = self.value(
            self.unit,
            ValueDefinition::OperationResult {
                operation: site.id,
                produced_at: available,
            },
            ProvenanceKind::Constructed(site.id),
            vec![],
        );
        let effects = ForeignBoundaryEffects::UncheckedOpaque {
            enclosing_scope: boundary,
        };
        self.emit(match kind {
            crate::lexer::Kind::C => Operation::ForeignC(ForeignC {
                site,
                region,
                operands,
                outputs,
                result,
                effects,
            }),
            crate::lexer::Kind::Cpp => Operation::ForeignCpp(ForeignCpp {
                site,
                region,
                operands,
                outputs,
                result,
                effects,
            }),
            crate::lexer::Kind::Assembly => Operation::ForeignAssembly(ForeignAssembly {
                site,
                region,
                operands,
                outputs,
                result,
                effects,
            }),
            _ => unreachable!(),
        });
        Ok(Expr { value: result })
    }
}
