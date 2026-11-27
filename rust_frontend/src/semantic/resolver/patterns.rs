//! Resolve each pattern once, then instantiate its already-resolved extraction
//! plan inside its branch scope. No branch selection/exhaustiveness proof here.
use super::*;
#[derive(Clone)]
pub(super) struct PatternPlan {
    node: ast::NodeId,
    ty: TypeId,
    borrowed: Option<ReferencePermission>,
    kind: PatternKind,
}
#[derive(Clone)]
enum PatternKind {
    Any,
    Unit,
    Binding {
        name: String,
        mutable: bool,
    },
    Tuple(Vec<PatternPlan>),
    Variant {
        variant: VariantId,
        fields: Vec<(FieldId, PatternPlan)>,
    },
}
impl PatternPlan {
    fn test(&self) -> PatternTest {
        let test = match &self.kind {
            PatternKind::Any | PatternKind::Binding { .. } => PatternTest::Any,
            PatternKind::Unit => PatternTest::Unit,
            PatternKind::Tuple(parts) => {
                PatternTest::Tuple(parts.iter().map(|p| p.test()).collect())
            }
            PatternKind::Variant { variant, fields } => PatternTest::Variant {
                variant: *variant,
                fields: fields.iter().map(|(f, p)| (*f, p.test())).collect(),
            },
        };
        if self.borrowed.is_some() {
            PatternTest::Dereference(Box::new(test))
        } else {
            test
        }
    }
}
impl Resolver<'_> {
    pub(super) fn plan_iteration_pattern(
        &mut self,
        node: ast::NodeId,
        ty: TypeId,
    ) -> Result<PatternPlan> {
        // Positional identifiers bind payloads. The syntax AST retains a path
        // shape; this context determines its semantic role without parser lookup.
        if let NodeKind::Pattern(ast::PatternSyntax::Variant {
            path,
            positional: None,
            fields: None,
        }) = self.kind(node)
        {
            if let NodeKind::Path { segments, .. } = self.kind(*path) {
                if segments.len() == 1 {
                    return Ok(PatternPlan {
                        node,
                        ty,
                        borrowed: None,
                        kind: PatternKind::Binding {
                            name: self.text(segments[0]).into(),
                            mutable: false,
                        },
                    });
                }
            }
        }
        self.plan_pattern(node, ty)
    }
    fn plan_pattern(&mut self, node: ast::NodeId, ty: TypeId) -> Result<PatternPlan> {
        let structural = matches!(
            self.kind(node),
            NodeKind::Pattern(
                ast::PatternSyntax::Tuple { .. } | ast::PatternSyntax::Variant { .. }
            )
        );
        let (matched, borrowed) = if structural {
            match self.p.types.entries[ty.0 as usize].kind.clone() {
                TypeDefinition::Reference { target, permission } => (target, Some(permission)),
                _ => (ty, None),
            }
        } else {
            (ty, None)
        };
        let kind = match self.kind(node) {
            NodeKind::Pattern(ast::PatternSyntax::Wildcard) => PatternKind::Any,
            NodeKind::Pattern(ast::PatternSyntax::Binding { name, mutable }) => {
                PatternKind::Binding {
                    name: self.text(*name).into(),
                    mutable: mutable.is_some(),
                }
            }
            NodeKind::Pattern(ast::PatternSyntax::Tuple { elements }) => {
                let types = match self.p.types.entries[matched.0 as usize].kind.clone() {
                    TypeDefinition::Unit if elements.is_empty() => vec![],
                    TypeDefinition::Tuple(types) => types,
                    _ => {
                        return Err(self.fail(
                            node,
                            DiagnosticKind::TypeMismatch,
                            "tuple pattern requires a tuple subject",
                        ));
                    }
                };
                if types.len() != elements.len() {
                    return Err(self.fail(
                        node,
                        DiagnosticKind::TypeMismatch,
                        "tuple pattern arity differs from its subject",
                    ));
                }
                if elements.is_empty() {
                    PatternKind::Unit
                } else {
                    let mut parts = vec![];
                    for (element, ty) in elements.iter().zip(types) {
                        let ty = if let Some(permission) = &borrowed {
                            self.intern(TypeKey::Reference(
                                matches!(permission, ReferencePermission::Mutable),
                                ty,
                            ))
                        } else {
                            ty
                        };
                        parts.push(self.plan_iteration_pattern(*element, ty)?);
                    }
                    PatternKind::Tuple(parts)
                }
            }
            NodeKind::Pattern(ast::PatternSyntax::Variant {
                path,
                positional,
                fields,
            }) => {
                let NodeKind::Path { segments, .. } = self.kind(*path) else {
                    unreachable!()
                };
                let symbol = self.scoped_path(*path, self.ctx().scope, segments)?;
                let SymbolDefinition::Variant(variant) =
                    self.p.symbols.entries[symbol.0 as usize].definition
                else {
                    return Err(self.fail(
                        *path,
                        DiagnosticKind::InvalidType,
                        "pattern path must name an enum variant",
                    ));
                };
                let variant = self.variant_for_type(node, variant, matched)?;
                let definition = self.p.declarations.variants[variant.0 as usize].clone();
                self.require_type(node, matched, definition.owner)?;
                let mut matched_fields = vec![];
                if let Some(patterns) = positional {
                    if patterns.len() != definition.fields.len() {
                        return Err(self.fail(
                            node,
                            DiagnosticKind::TypeMismatch,
                            "variant payload pattern has the wrong arity",
                        ));
                    }
                    matched_fields.extend(
                        definition
                            .fields
                            .iter()
                            .copied()
                            .zip(patterns.iter().copied()),
                    );
                } else if let Some(patterns) = fields {
                    let mut used = HashSet::new();
                    for pattern in patterns {
                        let NodeKind::Pattern(ast::PatternSyntax::Field { name, binding }) =
                            self.kind(*pattern)
                        else {
                            unreachable!()
                        };
                        let field = definition
                            .fields
                            .iter()
                            .copied()
                            .find(|f| {
                                self.p.symbols.entries
                                    [self.p.declarations.fields[f.0 as usize].symbol.0 as usize]
                                    .spelling
                                    == self.text(*name)
                            })
                            .ok_or_else(|| {
                                self.fail(
                                    *pattern,
                                    DiagnosticKind::UnresolvedName,
                                    "variant pattern names an unknown field",
                                )
                            })?;
                        if !used.insert(field) {
                            return Err(self.fail(
                                *pattern,
                                DiagnosticKind::DuplicateDeclaration,
                                "duplicate field in variant pattern",
                            ));
                        }
                        matched_fields.push((field, *binding));
                    }
                } else if !definition.fields.is_empty() {
                    return Err(self.fail(
                        node,
                        DiagnosticKind::TypeMismatch,
                        "variant pattern omits its payload shape",
                    ));
                }
                let mut plans = vec![];
                for (field, node) in matched_fields {
                    let field_ty = self.p.declarations.fields[field.0 as usize].ty;
                    let field_ty = if let Some(permission) = &borrowed {
                        self.intern(TypeKey::Reference(
                            matches!(permission, ReferencePermission::Mutable),
                            field_ty,
                        ))
                    } else {
                        field_ty
                    };
                    plans.push((field, self.plan_iteration_pattern(node, field_ty)?));
                }
                PatternKind::Variant {
                    variant,
                    fields: plans,
                }
            }
            _ => return Err(self.fail(node, DiagnosticKind::InvalidType, "expected a pattern")),
        };
        Ok(PatternPlan {
            node,
            ty,
            borrowed,
            kind,
        })
    }
    pub(super) fn extract_pattern(
        &mut self,
        node: ast::NodeId,
        source: ValueId,
        position: PlaceProjection,
        variant: Option<VariantId>,
        raw_type: TypeId,
        borrowed: Option<&ReferencePermission>,
    ) -> ValueId {
        let site = self.site(node, ExecutionPhase::Read);
        let ty = if let Some(permission) = borrowed {
            self.intern(TypeKey::Reference(
                matches!(permission, ReferencePermission::Mutable),
                raw_type,
            ))
        } else {
            raw_type
        };
        let selector = match position {
            PlaceProjection::Field(field) => PositionSelector::Field(field),
            PlaceProjection::TupleElement(index) => PositionSelector::TupleElement(index),
            _ => unreachable!(),
        };
        let result = if borrowed.is_some() {
            self.op_value(&site, ty, vec![])
        } else {
            self.projected_value(&site, source, selector, ty)
        };
        let reference = if borrowed.is_none() {
            self.references.get(&result).copied()
        } else {
            borrowed.map(|permission| {
                let mut projections = vec![PlaceProjection::Dereference];
                if let Some(variant) = variant {
                    projections.push(PlaceProjection::Variant(variant));
                }
                projections.push(position.clone());
                let place = self.place(PlaceRoot::Value(source), projections, raw_type);
                let id = ReferenceId(self.p.objects.references.len() as u32);
                self.p.objects.references.push(Reference {
                    id,
                    created_in: site.scope,
                    creation: ObjectCreation::At(site.execution_moments.first),
                    initial_owner: Owner::Scope {
                        scope: site.scope,
                        instance: self.ctx().domain,
                    },
                    ty,
                    permission: permission.clone(),
                    formation: ReferenceFormation::Loan,
                    origins: NonEmpty {
                        first: ReferenceOrigin {
                            target: place,
                            parent: self.references.get(&source).copied(),
                            guard: site.guard,
                        },
                        rest: vec![],
                    },
                });
                let entity = EntityId::Reference(id);
                let dependency = DependencyLinkId(self.p.objects.dependencies.len() as u32);
                self.p.objects.dependencies.push(DependencyLink {
                    id: dependency,
                    dependent: entity.clone(),
                    requirement: DependencyRequirement::LiveTarget(place),
                    established: site.execution_moments.first,
                    guard: site.guard,
                });
                self.references.insert(result, id);
                self.value_entities.insert(result, EntityId::Reference(id));
                let dependencies = self.p.values.entries[result.0 as usize].dependencies;
                self.p.values.dependency_summaries[dependencies.0 as usize]
                    .dependencies
                    .push(DependencyRequirement::LiveTarget(place));
                id
            })
        };
        let transfer = if let Some(permission) = borrowed {
            if matches!(permission, ReferencePermission::Mutable) {
                TransferKind::MutableBorrow
            } else {
                TransferKind::SharedBorrow
            }
        } else {
            self.transfer_kind(ty)
        };
        if let (Some(variant), PlaceProjection::Field(field)) = (variant, position.clone()) {
            self.emit(Operation::ExtractVariantField(ExtractVariantField {
                site,
                source,
                variant,
                field,
                result,
                reference,
                transfer,
            }));
        } else if let PlaceProjection::TupleElement(position) = position {
            self.emit(Operation::ExtractTupleField(ExtractTupleField {
                site,
                source,
                position,
                result,
                reference,
                transfer,
            }));
        } else {
            unreachable!()
        }
        result
    }
    pub(super) fn apply_pattern(
        &mut self,
        plan: &PatternPlan,
        value: ValueId,
    ) -> Result<ResolvedPattern> {
        self.require_type(plan.node, self.vtype(value), plan.ty)?;
        self.cover(plan.node, SyntaxDisposition::ResolvedType(plan.ty));
        Ok(match &plan.kind {
            PatternKind::Any => ResolvedPattern::Wildcard,
            PatternKind::Unit => ResolvedPattern::Unit,
            PatternKind::Binding { name, mutable } => {
                let binding = self.bind(plan.node, name, *mutable, value)?;
                ResolvedPattern::Binding {
                    binding,
                    transfer: self.transfer_kind(self.vtype(value)),
                }
            }
            PatternKind::Tuple(parts) => {
                let mut patterns = vec![];
                for (index, part) in parts.iter().enumerate() {
                    let raw = match self.p.types.entries[part.ty.0 as usize].kind {
                        TypeDefinition::Reference { target, .. } if plan.borrowed.is_some() => {
                            target
                        }
                        _ => part.ty,
                    };
                    let element = self.extract_pattern(
                        part.node,
                        value,
                        PlaceProjection::TupleElement(index as u32),
                        None,
                        raw,
                        plan.borrowed.as_ref(),
                    );
                    patterns.push(self.apply_pattern(part, element)?);
                }
                ResolvedPattern::Tuple(patterns)
            }
            PatternKind::Variant { variant, fields } => {
                let mut patterns = vec![];
                for (field, part) in fields {
                    let raw = self.p.declarations.fields[field.0 as usize].ty;
                    let element = self.extract_pattern(
                        part.node,
                        value,
                        PlaceProjection::Field(*field),
                        Some(*variant),
                        raw,
                        plan.borrowed.as_ref(),
                    );
                    patterns.push(PatternField {
                        field: *field,
                        pattern: self.apply_pattern(part, element)?,
                    });
                }
                ResolvedPattern::Variant {
                    variant: *variant,
                    fields: patterns,
                }
            }
        })
    }
    pub(super) fn match_expression(
        &mut self,
        n: ast::NodeId,
        value: ast::NodeId,
        arms: &[ast::NodeId],
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        let subject = self.expression(value, None)?.value;
        let mut plans = vec![];
        for arm in arms {
            let NodeKind::MatchArm { pattern, body } = self.kind(*arm) else {
                unreachable!()
            };
            plans.push((
                self.plan_pattern(*pattern, self.vtype(subject))?,
                Some(*body),
            ));
        }
        self.pattern_branches(n, subject, plans, expected, false)
    }
    pub(super) fn if_let_expression(
        &mut self,
        n: ast::NodeId,
        pattern: ast::NodeId,
        value: ast::NodeId,
        yes: ast::NodeId,
        no: Option<ast::NodeId>,
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        let subject = self.expression(value, None)?.value;
        let plan = self.plan_pattern(pattern, self.vtype(subject))?;
        let wildcard = PatternPlan {
            node: pattern,
            ty: self.vtype(subject),
            borrowed: None,
            kind: PatternKind::Any,
        };
        self.pattern_branches(
            n,
            subject,
            vec![(plan, Some(yes)), (wildcard, no)],
            expected,
            true,
        )
    }
    fn pattern_bindings(pattern: &ResolvedPattern) -> Vec<BindingId> {
        match pattern {
            ResolvedPattern::Binding { binding, .. } => vec![*binding],
            ResolvedPattern::Tuple(parts) => {
                parts.iter().flat_map(Self::pattern_bindings).collect()
            }
            ResolvedPattern::Variant { fields, .. } => fields
                .iter()
                .flat_map(|f| Self::pattern_bindings(&f.pattern))
                .collect(),
            _ => vec![],
        }
    }
    fn pattern_branches(
        &mut self,
        n: ast::NodeId,
        subject: ValueId,
        arms: Vec<(PatternPlan, Option<ast::NodeId>)>,
        expected: Option<TypeId>,
        is_if: bool,
    ) -> Result<Expr> {
        let site = self.site(n, ExecutionPhase::Compute);
        let parent = self.ctx().clone();
        let mut previous = vec![];
        let mut outcomes = vec![];
        let mut resolved_arms = vec![];
        let mut hint = expected;
        for (plan, body) in arms {
            let test = self.predicate(PredicateKind::Pattern {
                subject,
                test: plan.test(),
            });
            let prior = self.predicate(PredicateKind::Any(previous.clone()));
            let not_prior = self.predicate(PredicateKind::Not(prior));
            let guard = self.predicate(PredicateKind::All(vec![parent.guard, test, not_prior]));
            previous.push(test);
            self.ctx = Some(self.branch_context(&parent, site.id, guard));
            let branch = self.ctx().branch;
            let first = ExecutionMomentId(self.p.execution.execution_moments.len() as u32);
            let (value, pattern) = if let Some(body) = body {
                let (value, pattern) =
                    self.block_with_pattern(body, hint, Some((plan, subject)))?;
                (value.value, pattern.unwrap())
            } else {
                let unit = self.site(n, ExecutionPhase::Compute);
                let result = self.op_value(&unit, self.unit, vec![]);
                self.emit(Operation::UnitValue(UnitValue { site: unit, result }));
                (result, ResolvedPattern::Wildcard)
            };
            if hint.is_none() && self.vtype(value) != self.never {
                hint = Some(self.vtype(value));
            }
            let context = self.ctx().clone();
            let end = context.last.unwrap();
            self.p.execution.timelines[context.timeline.0 as usize]
                .exits
                .push(end);
            self.p
                .execution
                .edges
                .push(ExecutionEdge::Conditional(ConditionalEdge {
                    from: site.execution_moments.first,
                    to: first,
                    guard,
                }));
            if !is_if {
                self.p.execution.branches[branch.0 as usize].kind =
                    BranchKind::MatchArm(MatchArmBranch {
                        parent: parent.branch,
                        decision: site.id,
                        variant_guard: guard,
                        bindings: Self::pattern_bindings(&pattern),
                    });
            }
            resolved_arms.push(ResolvedMatchArm {
                pattern,
                branch,
                guard,
            });
            outcomes.push((guard, value, end, context));
        }
        self.ctx = Some(Context {
            last: None,
            ..parent.clone()
        });
        for (_, _, _, context) in &outcomes {
            self.accumulate_context(context);
        }
        let branches = resolved_arms.iter().map(|a| a.branch).collect::<Vec<_>>();
        self.p
            .execution
            .relationships
            .push(BranchRelationship::Exclusive(ExclusiveBranches {
                decision: site.id,
                branches: NonEmpty {
                    first: branches[0],
                    rest: branches[1..].to_vec(),
                },
            }));
        let covered = self.predicate(PredicateKind::Any(previous));
        let unmatched = self.predicate(PredicateKind::Not(covered));
        if !is_if {
            self.p.match_coverage.push(MatchCoverageRequirement {
                decision: site.id,
                subject,
                unmatched,
                origin: site.origin,
            });
        }
        let live = outcomes
            .iter()
            .filter(|(_, value, _, _)| self.vtype(*value) != self.never)
            .collect::<Vec<_>>();
        let merge = if live.is_empty() {
            None
        } else {
            let continuation_guard = self.predicate(PredicateKind::Any(
                live.iter().map(|(guard, _, _, _)| *guard).collect(),
            ));
            self.ctx_mut().guard = continuation_guard;
            let merge = self.site(n, ExecutionPhase::Receive);
            Some(merge)
        };
        let result = if let Some(merge) = &merge {
            let moments = live
                .iter()
                .map(|(guard, _, moment, _)| GuardedMoment {
                    guard: *guard,
                    moment: *moment,
                })
                .collect::<Vec<_>>();
            self.p
                .execution
                .relationships
                .push(BranchRelationship::Merge(BranchMerge {
                    incoming: NonEmpty {
                        first: moments[0].clone(),
                        rest: moments[1..].to_vec(),
                    },
                    continuation: merge.execution_moments.first,
                }));
            for (guard, _, from, _) in &live {
                self.p
                    .execution
                    .edges
                    .push(ExecutionEdge::Conditional(ConditionalEdge {
                        from: *from,
                        to: merge.execution_moments.first,
                        guard: *guard,
                    }));
            }
            let incoming = live
                .iter()
                .map(|(guard, value, _, _)| GuardedValue {
                    guard: *guard,
                    value: *value,
                })
                .collect::<Vec<_>>();
            self.merge_values(
                merge.clone(),
                NonEmpty {
                    first: incoming[0].clone(),
                    rest: incoming[1..].to_vec(),
                },
            )?
        } else {
            self.ctx_mut().last = Some(site.execution_moments.first);
            self.diverged(site.execution_moments.first).value
        };
        for (binding, before) in parent.bindings {
            if live.is_empty() {
                break;
            }
            let incoming = live
                .iter()
                .map(|(guard, _, _, ctx)| GuardedValue {
                    guard: *guard,
                    value: ctx.bindings.get(&binding).copied().unwrap_or(before),
                })
                .collect::<Vec<_>>();
            let first = incoming[0].value;
            let value = if incoming.iter().all(|v| v.value == first) {
                first
            } else {
                let site = self.site(n, ExecutionPhase::Receive);
                self.merge_values(
                    site,
                    NonEmpty {
                        first: incoming[0].clone(),
                        rest: incoming[1..].to_vec(),
                    },
                )?
            };
            self.ctx_mut().bindings.insert(binding, value);
        }
        let continuation = merge.map(|m| m.execution_moments.first);
        if is_if {
            self.emit(Operation::IfLetDecision(IfLetDecision {
                site,
                subject,
                pattern: resolved_arms[0].pattern.clone(),
                yes: resolved_arms[0].branch,
                no: resolved_arms[1].branch,
                merge: continuation,
            }));
        } else {
            self.emit(Operation::MatchDecision(MatchDecision {
                site,
                subject,
                unmatched,
                arms: NonEmpty {
                    first: resolved_arms[0].clone(),
                    rest: resolved_arms[1..].to_vec(),
                },
                merge: continuation,
            }));
        }
        Ok(Expr { value: result })
    }
}
