//! Specialize the first iterator adapters using the ordinary aggregate, call and
//! loan representations. No dynamic dispatch or per-item allocation is needed.

use super::*;

#[derive(Clone, Copy, PartialEq, Eq)]
pub(super) enum Stage {
    Iter {
        source: Ty,
        next: usize,
        item: Ty,
    },
    Owned {
        source: Ty,
        next: usize,
        item: Ty,
    },
    Map {
        previous: usize,
        mapper: usize,
        input: Ty,
        item: Ty,
    },
}

impl Stage {
    fn item(self) -> Ty {
        match self {
            Self::Iter { item, .. } | Self::Owned { item, .. } | Self::Map { item, .. } => item,
        }
    }

    fn field(self) -> (&'static str, Ty) {
        match self {
            Self::Iter { source, .. } | Self::Owned { source, .. } => ("@source", source),
            Self::Map { previous, .. } => ("@previous", Ty::Struct(previous)),
        }
    }
}

impl Checker<'_> {
    pub(super) fn iter_constructor(&self, id: NodeId) -> bool {
        let call = self.node(id);
        if call.kind != "appel" {
            return false;
        }
        let callee = self.node(call.children[0]);
        callee.kind == "nom qualifié"
            && callee.end == callee.start + 3
            && matches!(
                self.text(callee.start),
                "Iter" | crate::package::ITER_ADAPTER
            )
            && self.text(callee.start + 2) == "new"
            && !self.structure_names.contains_key(self.text(callee.start))
    }

    pub(super) fn is_pipeline(&self, mut id: NodeId) -> bool {
        loop {
            let node = self.node(id);
            match node.kind {
                "groupe" => id = node.children[0],
                "appel méthode" if self.name(id) == Some("map") => id = node.children[0],
                "nom" => {
                    return self
                        .uses
                        .get(&id)
                        .and_then(|binding| self.slots[binding.0])
                        .is_some_and(|slot| {
                            matches!(slot.ty,
                            Ty::Struct(layout) if self.pipeline_stages.contains_key(&layout))
                        });
                }
                _ => return self.iter_constructor(id),
            }
        }
    }

    pub(super) fn pipeline_candidate(&self, mut id: NodeId) -> bool {
        if self.is_pipeline(id) {
            return true;
        }
        while self.node(id).kind == "groupe" {
            id = self.node(id).children[0];
        }
        if self.node(id).kind == "appel méthode" && self.name(id) == Some("map") {
            return self.pipeline_candidate(self.node(id).children[0]);
        }
        let ty = if self.node(id).kind == "nom" {
            self.uses
                .get(&id)
                .and_then(|binding| self.slots[binding.0])
                .map(|slot| slot.ty)
        } else if self.node(id).kind == "appel" {
            let callee = self.node(self.node(id).children[0]);
            if callee.kind == "nom qualifié" {
                let owner = &self.source[self.tree.tokens[callee.start].span.start
                    ..self.tree.tokens[callee.start].span.end];
                let method = &self.source[self.tree.tokens[callee.end - 1].span.start
                    ..self.tree.tokens[callee.end - 1].span.end];
                self.structure_names
                    .get(owner)
                    .and_then(|layout| self.methods.get(&(*layout, method)))
                    .map(|(index, _)| self.signatures[*index].result)
            } else {
                self.name(self.node(id).children[0])
                    .and_then(|name| self.names.get(name))
                    .map(|&index| self.signatures[index].result)
            }
        } else {
            None
        };
        matches!(ty, Some(Ty::Struct(layout)) if self.methods.contains_key(&(layout, "next"))
            && !self.methods.contains_key(&(layout, "map")) && !self.methods.contains_key(&(layout, "collect")))
    }

    fn own_pipeline_source(
        &mut self,
        id: NodeId,
        value: Value,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let Ty::Struct(layout) = value.ty else {
            return Err(self.error(id, "source itérable attendue"));
        };
        if self.pipeline_stages.contains_key(&layout) {
            return Ok(value);
        }
        let Some(&(next, true)) = self.methods.get(&(layout, "next")) else {
            return Err(self.error(id, "next(&mut self) requis"));
        };
        let signature = &self.signatures[next];
        let expected = Ty::Ref {
            target: Referent::Aggregate(layout),
            mutable: true,
        };
        if signature.asynchronous
            || !matches!(signature.parameters.as_slice(), [(_, ty)] if *ty == expected)
        {
            return Err(self.error(id, "next(&mut self) synchrone requis"));
        }
        let item = self
            .options
            .iter()
            .find_map(|&(item, option)| (signature.result == Ty::Struct(option)).then_some(item))
            .ok_or_else(|| self.error(id, "next doit retourner Option<T>"))?;
        Ok(self.pipeline_stage(
            Stage::Owned {
                source: value.ty,
                next,
                item,
            },
            vec![value],
            out,
        ))
    }

    fn pipeline_stage(&mut self, stage: Stage, fields: Vec<Value>, out: &mut Vec<Instr>) -> Value {
        let layout = self
            .pipeline_stages
            .iter()
            .find_map(|(&layout, &other)| (stage == other).then_some(layout))
            .unwrap_or_else(|| {
                let layout = self.structures.len();
                let (name, ty) = stage.field();
                let mut layout_fields = vec![(name.into(), ty)];
                layout_fields.extend(
                    fields
                        .iter()
                        .skip(1)
                        .enumerate()
                        .map(|(index, value)| (format!("@capture{index}"), value.ty)),
                );
                self.structures.push(Structure {
                    destructor: None,
                    fields: layout_fields,
                    array: None,
                    pool: None,
                    variants: vec![],
                    growing: None,
                });
                self.pipeline_stages.insert(layout, stage);
                layout
            });
        let mut origins = Vec::new();
        for (index, &field) in fields.iter().enumerate() {
            self.append_value_origins(&mut origins, field, &[Position::Field(index)]);
        }
        let mut value = self.emit(
            Ty::Struct(layout),
            Expr::Construct(fields.into_iter().enumerate().collect()),
            out,
        );
        value.dependencies.loan = (!origins.is_empty()).then(|| self.intern(origins));
        value.finish_evaluation(out)
    }

    pub(super) fn iter_new(&mut self, id: NodeId, out: &mut Vec<Instr>) -> Result<Value, Error> {
        let [_, argument] = self.node(id).children.as_slice() else {
            return Err(self.error(id, "Iter::new exige une source &mut"));
        };
        let source = self.expression(*argument, None, Access::Move, out)?;
        let Ty::Ref {
            target: Referent::Aggregate(layout),
            mutable: true,
        } = source.ty
        else {
            return Err(self.error(*argument, "Iter::new exige une source &mut"));
        };
        let Some(&(next, true)) = self.methods.get(&(layout, "next")) else {
            return Err(self.error(
                *argument,
                "la source doit définir next(&mut self) -> Option<T>",
            ));
        };
        let signature = &self.signatures[next];
        let item = self
            .options
            .iter()
            .find_map(|&(item, option)| (signature.result == Ty::Struct(option)).then_some(item));
        let Some(item) = item.filter(|ty| option_item_supported(*ty)) else {
            return Err(self.error(*argument, "next doit retourner Option<T>"));
        };
        if signature.asynchronous
            || !matches!(signature.parameters[..], [(_, ty)] if ty == source.ty)
        {
            return Err(self.error(
                *argument,
                "la source doit définir next(&mut self) -> Option<T>",
            ));
        }
        Ok(self.pipeline_stage(
            Stage::Iter {
                source: source.ty,
                next,
                item,
            },
            vec![source],
            out,
        ))
    }

    fn compile_mapper(
        &mut self,
        id: NodeId,
        input: Ty,
        captures: &[(BindingId, Ty)],
    ) -> Result<(usize, Ty), Error> {
        let closure = self.node(id);
        if closure.kind != "closure" {
            return Err(self.error(id, "map exige une closure littérale"));
        }
        let [parameter, tail @ .., body] = closure.children.as_slice() else {
            return Err(self.error(id, "map exige une closure à un paramètre"));
        };
        let (parameter, body) = (*parameter, *body);
        if self.node(parameter).kind != "paramètre"
            || tail.len() > 1
            || tail
                .first()
                .is_some_and(|&node| self.node(node).kind != "type")
        {
            return Err(self.error(id, "map exige une closure à un paramètre"));
        }
        let [parameter_type] = self.node(parameter).children.as_slice() else {
            return Err(self.error(parameter, "le paramètre de map doit avoir un type"));
        };
        if self.ty(*parameter_type)? != input {
            return Err(self.error(
                parameter,
                "le paramètre de map doit avoir le type de l’item",
            ));
        }
        let binding = self.bindings[&parameter];
        let result_type = tail
            .first()
            .copied()
            .map(|node| self.ty(node))
            .transpose()?;
        if let Some(&(function, item)) = self.pipeline_mappers.get(&id) {
            return Ok((function, item));
        }

        // Captures are aliases into the stage for each invocation. The
        // generated function owns its ordinary item argument.
        let mut formal = vec![(binding, input)];
        formal.extend_from_slice(captures);
        let captured = captures
            .iter()
            .map(|&(binding, _)| binding)
            .collect::<Vec<_>>();
        let slots = std::mem::replace(&mut self.slots, vec![None; self.tree.bindings.len()]);
        let loops = std::mem::take(&mut self.loops);
        let pending = std::mem::take(&mut self.pending);
        let parameters = std::mem::replace(&mut self.parameters, formal.clone());
        let aliases = std::mem::replace(&mut self.mapper_captures, captured.clone());
        let returned = std::mem::take(&mut self.returned);
        let entries = std::mem::take(&mut self.entry_effects);
        let returned_entries = std::mem::take(&mut self.returned_entry_effects);
        let waited = std::mem::take(&mut self.waited_parameters);
        let propagation = self.propagation_waits.take();
        let native_entries = std::mem::take(&mut self.native_entries);
        let next_temp = std::mem::take(&mut self.next_temp);
        let function_result =
            std::mem::replace(&mut self.function_result, result_type.unwrap_or(Ty::Void));
        let in_async = std::mem::replace(&mut self.in_async, false);
        for &(binding, ty) in &formal {
            let loan = self.has_dependencies(ty).then(|| {
                self.intern(vec![Origin {
                    root: binding,
                    storage: false,
                    pool: false,
                    parent: None,
                    at: PathId::default(),
                    from: PathId::default(),
                    lock: PathId::default(),
                    opaque: false,
                    capture_exclusive: false,
                }])
            });
            self.slots[binding.0] = Some(Slot {
                ty,
                state: State::Live,
                loan,
                awaited_loan: None,
                vector_len: None,
                field_lengths: None,
            });
        }
        let mut instructions = Vec::new();
        let checked = (|| {
            let (_, value) = self.value_arm(body, result_type, &mut instructions)?;
            if let Some(value) = value {
                self.record_return(id, value)?;
                instructions.push(Instr::Return(Some(value)));
            }
            Ok(value.map(|value| value.ty))
        })();

        self.slots = slots;
        self.loops = loops;
        self.pending = pending;
        self.parameters = parameters;
        self.mapper_captures = aliases;
        let mapper_returns = std::mem::replace(&mut self.returned, returned);
        let mapper_entries = std::mem::replace(&mut self.entry_effects, entries);
        let mapper_returned_entries =
            std::mem::replace(&mut self.returned_entry_effects, returned_entries);
        let mapper_waits = std::mem::replace(&mut self.waited_parameters, waited);

        self.propagation_waits = propagation;
        self.native_entries = native_entries;
        self.next_temp = next_temp;
        self.function_result = function_result;
        self.in_async = in_async;

        let item = checked?
            .or(result_type)
            .filter(|ty| option_item_supported(*ty))
            .ok_or_else(|| self.error(body, "map exige un résultat"))?;
        let function = self.signatures.len() + self.generated_functions.len();
        self.generated_functions.push(Some(Function {
            parameters: formal,
            borrowed_parameters: captured,
            result: item,
            body: instructions,
            entry: false,
            native: false,
            asynchronous: false,
        }));
        self.native_contracts.push(mapper_returns);
        self.native_entry_contracts.push(mapper_entries);
        self.native_returned_entries.push(mapper_returned_entries);
        self.pipeline_mapper_waits.insert(function, mapper_waits);
        self.pipeline_mappers.insert(id, (function, item));
        Ok((function, item))
    }

    pub(super) fn iter_map(&mut self, id: NodeId, out: &mut Vec<Instr>) -> Result<Value, Error> {
        let [base, mapper] = self.node(id).children[..] else {
            return Err(self.error(id, "map exige une closure"));
        };
        let prior = self.expression(base, None, Access::Move, out)?;
        let prior = self.own_pipeline_source(base, prior, out)?;
        let Ty::Struct(previous) = prior.ty else {
            unreachable!()
        };
        let input = self.pipeline_stages[&previous].item();
        let bindings = self
            .tree
            .captures
            .iter()
            .filter(|capture| capture.closure == mapper)
            .map(|capture| capture.source)
            .collect::<Vec<_>>();
        let moves_captures = self.name(mapper) == Some("move");
        let mut captures = Vec::new();
        let mut fields = vec![prior];
        for binding in bindings {
            let access = if moves_captures {
                Access::Move
            } else {
                if self.live_slot(mapper, binding)?.ty.scalar().is_none() {
                    return Err(self.error(mapper, "une capture non primitive exige move"));
                }
                Access::Read
            };
            let value = self.local(mapper, binding, access, out)?;
            if value.ty.referent().is_none() {
                return Err(self.error(mapper, "type de capture de map hors périmètre"));
            }
            captures.push((binding, value.ty));
            fields.push(value);
        }
        let (mapper, item) = self.compile_mapper(mapper, input, &captures)?;
        Ok(self.pipeline_stage(
            Stage::Map {
                previous,
                mapper,
                input,
                item,
            },
            fields,
            out,
        ))
    }

    pub(super) fn iter_next(&mut self, id: NodeId, out: &mut Vec<Instr>) -> Result<Value, Error> {
        let [mut base] = self.node(id).children[..] else {
            return Err(self.error(id, "next ne prend pas d’argument"));
        };
        while self.node(base).kind == "groupe" {
            base = self.node(base).children[0];
        }
        let stage = if let Some(&binding) = self.uses.get(&base) {
            if !self.tree.bindings[binding.0].mutable {
                return Err(self.error(base, "next exige un receveur mutable"));
            }
            self.access_target(base, binding, true, false)?;
            self.access_reference(base, binding, true)?;
            self.local(base, binding, Access::Read, out)?
        } else {
            self.expression(base, None, Access::Move, out)?
        };
        let Ty::Struct(layout) = stage.ty else {
            unreachable!()
        };
        self.pipeline_next(id, layout, stage, self.uses.get(&base).copied(), out)
    }

    fn pipeline_next(
        &mut self,
        id: NodeId,
        layout: usize,
        stage: Value,
        parent: Option<BindingId>,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        match self.pipeline_stages[&layout] {
            Stage::Iter { source, next, .. } => {
                let mut reference = self.emit(source, Expr::Field(stage, 0), out);
                let mut origins =
                    self.selected_origins(stage.dependencies.loan, &[Position::Field(0)]);
                if let Some(parent) = parent {
                    for origin in &mut origins {
                        origin.parent = Some(parent);
                    }
                }
                reference.dependencies.loan = (!origins.is_empty()).then(|| self.intern(origins));
                let reference = reference.finish_evaluation(out);
                let (loan, awaited_loan) = self.call_effects(id, next, &[reference])?;
                let mut result = self.emit(
                    self.signatures[next].result,
                    Expr::Call(next, vec![reference], CallKind::Pipeline),
                    out,
                );
                result.dependencies.loan = loan;
                result.dependencies.awaited_loan = awaited_loan;
                Ok(result.finish_evaluation(out))
            }
            Stage::Owned {
                source: Ty::Struct(source),
                next,
                ..
            } => {
                let ty = Ty::Ref {
                    target: Referent::Aggregate(source),
                    mutable: true,
                };
                let mut reference = self.emit(ty, Expr::BorrowField(stage, 0), out);
                let mut origins =
                    self.selected_origins(stage.dependencies.loan, &[Position::Field(0)]);
                if let Some(parent) = parent {
                    for origin in &mut origins {
                        origin.parent = Some(parent);
                    }
                }
                reference.dependencies.loan = (!origins.is_empty()).then(|| self.intern(origins));
                let reference = reference.finish_evaluation(out);
                let (loan, awaited_loan) = self.call_effects(id, next, &[reference])?;
                let mut result = self.emit(
                    self.signatures[next].result,
                    Expr::Call(next, vec![reference], CallKind::Pipeline),
                    out,
                );
                result.dependencies.loan = loan;
                result.dependencies.awaited_loan = awaited_loan;
                Ok(result.finish_evaluation(out))
            }
            Stage::Owned { .. } => unreachable!("owned sources have record layouts"),
            Stage::Map {
                previous,
                mapper,
                input,
                item,
            } => {
                let target = Referent::Aggregate(previous);
                let mut previous_ref = self.emit(
                    Ty::Ref {
                        target,
                        mutable: true,
                    },
                    Expr::BorrowField(stage, 0),
                    out,
                );
                previous_ref.dependencies.loan =
                    self.selected_loan(stage.dependencies.loan, &[Position::Field(0)]);
                let previous_ref = previous_ref.finish_evaluation(out);
                let option = self.pipeline_next(id, previous, previous_ref, parent, out)?;
                let present = self.emit(Ty::Bool, Expr::IsVariant(option, 1), out);
                let ty = self.option_type(item);
                let mut yes = Vec::new();
                let argument = self.take_propagation_payload(option, 1, input, &mut yes);
                let mut arguments = vec![argument];
                let captured = self.generated_functions[mapper - self.signatures.len()]
                    .as_ref()
                    .unwrap()
                    .parameters[1..]
                    .to_vec();
                for (index, (_, ty)) in captured.into_iter().enumerate() {
                    let field = index + 1;
                    let mut capture = self.emit(
                        Ty::Ref {
                            target: ty.referent().unwrap(),
                            mutable: true,
                        },
                        Expr::BorrowField(stage, field),
                        &mut yes,
                    );
                    capture.dependencies.loan =
                        self.selected_loan(stage.dependencies.loan, &[Position::Field(field)]);
                    arguments.push(capture.finish_evaluation(&mut yes));
                }
                let mapped = self.apply_mapper(id, mapper, item, arguments, &mut yes)?;
                let some = self.wrap_payload(ty, 1, Some(mapped), &mut yes);
                let mut receiver = self.value_receiver(id, some)?;
                receiver.provenance = ValueProvenance::Merged;
                yes.push(Instr::Receive(receiver, some));
                let mut no = Vec::new();
                let none = self.wrap_payload(ty, 0, None, &mut no);
                no.push(Instr::Receive(receiver, none));
                out.push(Instr::Reserve(receiver));
                out.push(Instr::If(present, yes, no));
                Ok(receiver)
            }
        }
    }

    fn apply_mapper(
        &mut self,
        id: NodeId,
        mapper: usize,
        item: Ty,
        arguments: Vec<Value>,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let index = mapper - self.signatures.len();
        for effect in self.native_entry_contracts[index].clone() {
            let path = self.dependencies.paths[effect.path.0].clone();
            let source = self.selected_loan(arguments[effect.source].dependencies.loan, &path);
            let target = arguments[effect.target].dependencies.loan;
            self.replace_entry_loan(id, target, source, false)?;
            self.refresh_entry_reborrows(id, target, source)?;
        }
        for (parameter, path) in self.pipeline_mapper_waits[&mapper].clone() {
            let mut handle = arguments[parameter];
            let path = self.dependencies.paths[path.0].clone();
            handle.dependencies.loan = self.selected_loan(handle.dependencies.loan, &path);
            self.complete_entry_effects(id, handle)?;
        }
        let loan = self.native_output_loan(id, index, &arguments)?;
        let origins = self.origins(loan).to_vec();
        let mut result = self.emit(item, Expr::Call(mapper, arguments, CallKind::Pipeline), out);
        self.unpack_output(&mut result, origins);
        Ok(result.finish_evaluation(out))
    }

    pub(super) fn iter_collect(&mut self, id: NodeId, out: &mut Vec<Instr>) -> Result<(), Error> {
        let [base, destination] = self.node(id).children[..] else {
            return Err(self.error(id, "collect exige un Vector emprunté en &mut"));
        };
        let stage = self.expression(base, None, Access::Move, out)?;
        let stage = self.own_pipeline_source(base, stage, out)?;
        let Ty::Struct(layout) = stage.ty else {
            unreachable!()
        };
        if self.dependent_handle(stage.ty, stage.dependencies.loan) {
            return Err(self.error(
                id,
                "collect abandonnerait une tâche capturée par le pipeline",
            ));
        }
        let item = self.pipeline_stages[&layout].item();
        let pending = self.pending.len();
        self.pending.push(stage);
        let target = self.collect_destination(destination, item, out);
        self.pending.truncate(pending);
        let target = target?;
        let mut body = Vec::new();
        let option = self.pipeline_next(id, layout, stage, None, &mut body)?;
        let present = self.emit(Ty::Bool, Expr::IsVariant(option, 1), &mut body);
        let mut some = Vec::new();
        let item = self.take_propagation_payload(option, 1, item, &mut some);
        self.collect_dependencies(id, stage, target, item)?;
        some.push(Instr::GrowingPush(target, item));
        body.push(Instr::If(present, some, vec![Instr::Break(None)]));
        out.push(Instr::Loop {
            condition: Vec::new(),
            test: None,
            body,
        });
        if owns_resources(stage.ty, &self.structures) {
            out.push(Instr::DropOwned(stage));
        }
        Ok(())
    }

    fn collect_dependencies(
        &mut self,
        id: NodeId,
        stage: Value,
        target: Value,
        item: Value,
    ) -> Result<(), Error> {
        // A loop must be able to acquire the next source loan even if the
        // vector retains everything it received on its previous iterations.
        let retained = self.origins(item.dependencies.loan);
        if retained
            .iter()
            .filter(|origin| origin.storage && !origin.pool)
            .any(|item_origin| {
                self.origins(stage.dependencies.loan)
                    .iter()
                    .any(|source_origin| {
                        source_origin.storage
                            && source_origin.root == item_origin.root
                            && (item_origin.opaque
                                || item_origin.capture_exclusive
                                || self.has_exclusive_dependencies(item.ty)
                                || self.handle_origin(
                                    item.ty,
                                    &self.dependencies.paths[item_origin.at.0],
                                )
                                || source_origin.opaque
                                || !self.shared_dependency_at(
                                    stage.ty,
                                    &self.dependencies.paths[source_origin.at.0],
                                ))
                    })
            })
        {
            return Err(self.error(
                id,
                "collect retient un emprunt incompatible avec le prochain next",
            ));
        }
        if let ValueProvenance::LocalRead(binding) = target.provenance {
            let slot = self.live_slot(id, binding)?;
            let scope = self.tree.bindings[binding.0].scope;
            self.check_dependency_scope(id, scope, item.dependencies.loan)?;
            self.check_dependency_scope(id, scope, item.dependencies.awaited_loan)?;
            let mut origins = self.origins(slot.loan).to_vec();
            self.append_value_origins(&mut origins, item, &[Position::Index(None)]);
            let loan = (!origins.is_empty()).then(|| self.intern(origins));
            self.slots[binding.0] = Some(Slot {
                loan,
                vector_len: None,
                ..slot
            });
        } else if item.dependencies.loan.is_some()
            || item.dependencies.awaited_loan.is_some()
            || owns_resources(item.ty, &self.structures)
        {
            return Err(self.error(
                id,
                "collect exige ici un vecteur dont la liaison de destination est connue",
            ));
        }
        Ok(())
    }

    fn collect_destination(
        &mut self,
        id: NodeId,
        item: Ty,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let node = self.node(id);
        // An explicitly borrowed owning handle can use the same descriptor
        // and append instruction as Vector.push.
        if node.kind == "emprunt" && self.text(node.start + 1) == "mut" {
            let mut base = node.children[0];
            if self.node(base).kind == "indirection" {
                base = self.node(base).children[0];
            }
            if let Some((binding, Growing::Vector(element))) = self.growing_handle(base) {
                if element != item || !self.tree.bindings[binding.0].mutable {
                    return Err(self.error(id, "collect exige un Vector mutable du type des items"));
                }
                self.access_target(base, binding, true, false)?;
                let handle = self.local(base, binding, Access::Read, out)?;
                self.slots[binding.0].as_mut().unwrap().vector_len = None;
                return Ok(handle);
            }
        }
        let target = if let Some(&binding) = self.uses.get(&id) {
            self.reborrow(id, binding, true, out)?
        } else {
            self.expression(id, None, Access::Move, out)?
        };
        let Ty::Ref {
            target: Referent::Aggregate(layout),
            mutable: true,
        } = target.ty
        else {
            return Err(self.error(id, "collect exige un Vector emprunté en &mut"));
        };
        if self.structures[layout].growing != Some(Growing::Vector(item)) {
            return Err(self.error(id, "collect exige un Vector mutable du type des items"));
        }
        for origin in self.origins(target.dependencies.loan).to_vec() {
            if let Some(slot) = &mut self.slots[origin.root.0] {
                slot.vector_len = None;
            }
        }
        Ok(target)
    }
}
