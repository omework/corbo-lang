//! Physical memory planning for checked PostAST programs.
//!
//! This stage consumes resolved types, logical final destinations and N1-N8
//! evidence. It does not inspect source syntax, resolve a name, infer a type or
//! alter ownership. Fixed values/descriptors use the classic data stack;
//! growing payloads use bounded regions; pool slots remain fixed storage.

use crate::post_ast::*;
use std::collections::{HashMap, HashSet};

/// Compute target layouts and realize every checked logical destination.
pub fn plan(checked: CheckedPostAst) -> MemoryPlanningResult {
    let (layouts, missing) = LayoutBuilder::new(post_ast(&checked)).finish();
    if !missing.is_empty() {
        return MemoryPlanningResult::MissingPlanInput(IncompleteMemoryPlan {
            checked_flow: checked,
            layouts,
            missing: non_empty(missing),
        });
    }
    plan_with_layouts(MemoryPlanningInput {
        checked_flow: checked,
        layouts,
    })
}

/// Plan using an already computed target layout table.
pub fn plan_with_layouts(input: MemoryPlanningInput) -> MemoryPlanningResult {
    Planner::new(input).finish()
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MemoryPlanIntegrityError(pub String);

/// Audit the physical artifact without consulting syntax or repeating any
/// semantic decision. This is also usable by backend handoff tests.
pub fn validate(plan: &PlannedPostAst) -> Result<(), Vec<MemoryPlanIntegrityError>> {
    let mut errors = vec![];
    let pointer = u64::from(
        plan.checked_flow
            .semantics
            .semantics
            .post_ast
            .target
            .pointer_bits
            / 8,
    );
    for (index, layout) in plan.layouts.layouts.iter().enumerate() {
        if layout.id.0 as usize != index {
            errors.push(MemoryPlanIntegrityError(format!(
                "non-canonical layout id {:?}",
                layout.id
            )));
        }
        if let (LayoutSize::Fixed(size), Some(native)) = (&layout.size, &layout.native) {
            let required = native_descriptor_extent(native, pointer);
            if required > *size {
                errors.push(MemoryPlanIntegrityError(format!(
                    "native layout {:?} requires {required} bytes but plans {size}",
                    layout.ty
                )));
            }
        }
    }
    let stack_ids = plan
        .storage
        .stacks
        .iter()
        .map(|stack| stack.id)
        .collect::<HashSet<_>>();
    for (index, reservation) in plan.storage.reservations.iter().enumerate() {
        if reservation.id.0 as usize != index {
            errors.push(MemoryPlanIntegrityError(format!(
                "non-canonical reservation id {:?}",
                reservation.id
            )));
        }
        if reservation.layout.0 as usize >= plan.layouts.layouts.len() {
            errors.push(MemoryPlanIntegrityError(format!(
                "reservation {:?} has no layout",
                reservation.id
            )));
        }
        if !stack_ids.contains(&reservation.stack) {
            errors.push(MemoryPlanIntegrityError(format!(
                "reservation {:?} has no stack",
                reservation.id
            )));
        }
        if reservation.start.0 as usize >= plan.storage.cursors.len()
            || reservation.end.0 as usize >= plan.storage.cursors.len()
        {
            errors.push(MemoryPlanIntegrityError(format!(
                "reservation {:?} has an invalid cursor",
                reservation.id
            )));
        }
    }
    for assignment in &plan.reservations {
        if assignment.reservation.0 as usize >= plan.storage.reservations.len() {
            errors.push(MemoryPlanIntegrityError(format!(
                "assignment for {:?} has no reservation",
                assignment.destination
            )));
        }
        if assignment.destination.0 as usize >= plan.checked_flow.semantics.finals.len() {
            errors.push(MemoryPlanIntegrityError(format!(
                "assignment has unknown destination {:?}",
                assignment.destination
            )));
        }
    }
    if plan.storage.values.len() != post_ast(&plan.checked_flow).values.entries.len() {
        errors.push(MemoryPlanIntegrityError(format!(
            "value-storage table has {} entries for {} values",
            plan.storage.values.len(),
            post_ast(&plan.checked_flow).values.entries.len()
        )));
    }
    for (index, storage) in plan.storage.values.iter().enumerate() {
        if storage.value.0 as usize != index {
            errors.push(MemoryPlanIntegrityError(format!(
                "non-canonical value-storage id {:?}",
                storage.value
            )));
        }
        if storage
            .layout
            .is_some_and(|layout| layout.0 as usize >= plan.layouts.layouts.len())
        {
            errors.push(MemoryPlanIntegrityError(format!(
                "value {:?} has an invalid storage layout",
                storage.value
            )));
        }
    }
    for requirement in &plan.checked_flow.semantics.physical_requirements {
        let count = plan
            .realization
            .iter()
            .filter(|evidence| evidence.requirement == requirement.id)
            .count();
        if count != 1 {
            errors.push(MemoryPlanIntegrityError(format!(
                "physical requirement {:?} has {count} realizations",
                requirement.id
            )));
        }
    }
    for region in &plan.storage.regions {
        if !stack_ids.contains(&region.stack) {
            errors.push(MemoryPlanIntegrityError(format!(
                "region {:?} has no stack",
                region.id
            )));
        }
        if let Some(class) = region.class {
            if plan
                .storage
                .region_classes
                .get(class.0 as usize)
                .is_none_or(|candidate| candidate.stack != region.stack)
            {
                errors.push(MemoryPlanIntegrityError(format!(
                    "region {:?} has an invalid class",
                    region.id
                )));
            }
        }
    }
    for group in &plan.sharing {
        if group.reservation.0 as usize >= plan.storage.reservations.len()
            || group.exclusivity_evidence.0 as usize >= plan.physical_proofs.len()
            || group.compatibility_evidence.0 as usize >= plan.physical_proofs.len()
        {
            errors.push(MemoryPlanIntegrityError(format!(
                "sharing group {:?} has an invalid proof or reservation",
                group.id
            )));
        }
    }
    for cleanup in &plan.cleanup.exits {
        let mut recovery_started = false;
        for action in &cleanup.actions {
            match action {
                CleanupAction::RewindCursor { .. }
                | CleanupAction::ReturnRegion { .. }
                | CleanupAction::RestoreRegionClass { .. } => recovery_started = true,
                CleanupAction::InvokeUserDestructor { .. }
                | CleanupAction::DestroyOwnedComponent { .. }
                | CleanupAction::ReleaseAllocation { .. }
                    if recovery_started =>
                {
                    errors.push(MemoryPlanIntegrityError(format!(
                        "cleanup {:?} destroys after storage recovery",
                        cleanup.exit
                    )));
                }
                _ => {}
            }
        }
    }
    if errors.is_empty() {
        Ok(())
    } else {
        Err(errors)
    }
}

fn native_descriptor_extent(layout: &NativeDescriptorLayout, pointer: u64) -> u64 {
    let last = match layout {
        NativeDescriptorLayout::View {
            pointer: data,
            length,
        } => (*data).max(*length),
        NativeDescriptorLayout::ThinReference { pointer: data } => *data,
        NativeDescriptorLayout::Callable {
            function,
            environment,
        } => (*function).max(*environment),
        NativeDescriptorLayout::Allocation { pool, slot, index } => (*pool).max(*slot).max(*index),
        NativeDescriptorLayout::Region {
            band,
            data,
            index,
            length,
            width,
            maximum,
            destroy,
        } => [*band, *data, *index, *length, *width, *maximum, *destroy]
            .into_iter()
            .max()
            .unwrap_or(0),
        NativeDescriptorLayout::Map {
            entries,
            index,
            value_width,
            value_offset,
            count,
            free_head,
            destroy,
        } => [
            *entries,
            *index,
            *value_width,
            *value_offset,
            *count,
            *free_head,
            *destroy,
        ]
        .into_iter()
        .max()
        .unwrap_or(0),
        NativeDescriptorLayout::InlineUtf8 {
            length,
            data,
            maximum_bytes,
        } => {
            return (*length + pointer).max(*data + *maximum_bytes);
        }
        NativeDescriptorLayout::ExecutionHandle { state } => *state,
        NativeDescriptorLayout::Pool { state } => *state,
        NativeDescriptorLayout::ContractFuture { state, poll } => (*state).max(*poll),
    };
    last.saturating_add(pointer)
}

fn post_ast(checked: &CheckedPostAst) -> &PostAst {
    &checked.semantics.semantics.post_ast
}

fn non_empty<T>(mut values: Vec<T>) -> NonEmpty<T> {
    let first = values.remove(0);
    NonEmpty {
        first,
        rest: values,
    }
}

// -------------------------------------------------------------------------
// Target layouts

struct LayoutBuilder<'a> {
    p: &'a PostAst,
    layouts: Vec<TypeLayout>,
    by_type: HashMap<TypeId, LayoutId>,
    visiting: HashSet<TypeId>,
    missing: Vec<TypeId>,
    pointer: u64,
}

impl<'a> LayoutBuilder<'a> {
    fn new(p: &'a PostAst) -> Self {
        Self {
            p,
            layouts: vec![],
            by_type: HashMap::new(),
            visiting: HashSet::new(),
            missing: vec![],
            pointer: u64::from(p.target.pointer_bits / 8),
        }
    }

    fn finish(mut self) -> (TargetLayoutPlan, Vec<MissingPlanInput>) {
        // Layout every runtime type that appears as a value or storage object.
        // Generic parameters that exist only in declarations are intentionally
        // not forced: concrete instances carry their substituted TypeIds.
        let mut required = HashSet::new();
        required.extend(self.p.values.entries.iter().map(|value| value.ty));
        required.extend(self.p.objects.addresses.iter().map(|address| address.ty));
        required.extend(self.p.async_frames.iter().map(|frame| frame.state_type));
        for collection in &self.p.objects.collections {
            required.insert(collection.ty);
        }
        for ty in required {
            if !matches!(
                self.p.types.entries[ty.0 as usize].kind,
                TypeDefinition::Parameter(_)
            ) {
                self.layout(ty);
            }
        }
        self.missing.sort_by_key(|ty| ty.0);
        self.missing.dedup();
        (
            TargetLayoutPlan {
                layouts: self.layouts,
                abi: self.p.target.abi,
            },
            self.missing
                .into_iter()
                .map(MissingPlanInput::TypeLayout)
                .collect(),
        )
    }

    fn layout(&mut self, ty: TypeId) -> Option<LayoutId> {
        if let Some(id) = self.by_type.get(&ty) {
            return Some(*id);
        }
        if !self.visiting.insert(ty) {
            self.missing.push(ty);
            return None;
        }
        let kind = self.p.types.entries[ty.0 as usize].kind.clone();
        let built = self.build(ty, kind);
        self.visiting.remove(&ty);
        let mut layout = match built {
            Some(layout) => layout,
            None => {
                self.missing.push(ty);
                return None;
            }
        };
        let id = LayoutId(self.layouts.len() as u32);
        layout.id = id;
        self.layouts.push(layout);
        self.by_type.insert(ty, id);
        Some(id)
    }

    fn build(&mut self, ty: TypeId, kind: TypeDefinition) -> Option<TypeLayout> {
        let (size, alignment, fields, tuple_elements, sequence, variant, native) = match kind {
            TypeDefinition::Never | TypeDefinition::Unit => {
                (0, 1, vec![], vec![], None, None, None)
            }
            TypeDefinition::Boolean | TypeDefinition::NumericConversionError => {
                (1, 1, vec![], vec![], None, None, None)
            }
            TypeDefinition::Numeric(numeric) => {
                let bytes = match numeric {
                    NumericType::I32 | NumericType::U32 | NumericType::F32 => 4,
                    NumericType::I64 | NumericType::U64 | NumericType::F64 => 8,
                    NumericType::U8 => 1,
                    NumericType::U16 => 2,
                    NumericType::Usize => self.pointer,
                };
                (bytes, bytes, vec![], vec![], None, None, None)
            }
            TypeDefinition::Utf8View | TypeDefinition::Slice { .. } => (
                self.pointer * 2,
                self.pointer,
                vec![],
                vec![],
                None,
                None,
                Some(NativeDescriptorLayout::View {
                    pointer: 0,
                    length: self.pointer,
                }),
            ),
            TypeDefinition::StrData | TypeDefinition::Parameter(_) => return None,
            TypeDefinition::Reference { target, .. } => {
                let fat = matches!(
                    self.p.types.entries[target.0 as usize].kind,
                    TypeDefinition::Slice { .. } | TypeDefinition::StrData
                );
                if fat {
                    (
                        self.pointer * 2,
                        self.pointer,
                        vec![],
                        vec![],
                        None,
                        None,
                        Some(NativeDescriptorLayout::View {
                            pointer: 0,
                            length: self.pointer,
                        }),
                    )
                } else {
                    (
                        self.pointer,
                        self.pointer,
                        vec![],
                        vec![],
                        None,
                        None,
                        Some(NativeDescriptorLayout::ThinReference { pointer: 0 }),
                    )
                }
            }
            TypeDefinition::Tuple(elements) => {
                let (size, alignment, tuple_elements) = self.tuple_layout(&elements)?;
                (size, alignment, vec![], tuple_elements, None, None, None)
            }
            TypeDefinition::Array { element, length } => {
                let layout_id = self.layout(element)?;
                let layout = self.layouts[layout_id.0 as usize].clone();
                let stride = align_up(fixed_size(&layout)?, layout.alignment)?;
                (
                    stride.checked_mul(length)?,
                    layout.alignment,
                    vec![],
                    vec![],
                    Some(SequenceLayout {
                        element: layout_id,
                        stride,
                        length,
                    }),
                    None,
                    None,
                )
            }
            TypeDefinition::Nominal { .. } => return self.nominal_layout(ty),
            TypeDefinition::Callable(_) => (
                self.pointer * 2,
                self.pointer,
                vec![],
                vec![],
                None,
                None,
                Some(NativeDescriptorLayout::Callable {
                    function: 0,
                    environment: self.pointer,
                }),
            ),
            TypeDefinition::Closure { captures, .. } => {
                let record = &self.p.contracts.captures[captures.0 as usize];
                let environment_id = self.layout(record.ty)?;
                let environment = self.layouts[environment_id.0 as usize].clone();
                (
                    fixed_size(&environment)?,
                    environment.alignment,
                    environment.fields,
                    vec![],
                    None,
                    None,
                    None,
                )
            }
            TypeDefinition::ContractFuture { .. } => (
                self.pointer * 2,
                self.pointer,
                vec![],
                vec![],
                None,
                None,
                Some(NativeDescriptorLayout::ContractFuture {
                    state: 0,
                    poll: self.pointer,
                }),
            ),
            TypeDefinition::Allocation { .. } => (
                self.pointer * 3,
                self.pointer,
                vec![],
                vec![],
                None,
                None,
                Some(NativeDescriptorLayout::Allocation {
                    pool: 0,
                    slot: self.pointer,
                    index: self.pointer * 2,
                }),
            ),
            TypeDefinition::ExecutionHandle { .. } => (
                self.pointer,
                self.pointer,
                vec![],
                vec![],
                None,
                None,
                Some(NativeDescriptorLayout::ExecutionHandle { state: 0 }),
            ),
            TypeDefinition::Future { state, .. } => {
                let layout = self.layout_value(state)?;
                (layout.0, layout.1, vec![], vec![], None, None, None)
            }
            TypeDefinition::GrowingSequence { .. } | TypeDefinition::GrowingString => (
                self.pointer * 7,
                self.pointer,
                vec![],
                vec![],
                None,
                None,
                Some(NativeDescriptorLayout::Region {
                    band: 0,
                    data: self.pointer,
                    index: self.pointer * 2,
                    length: self.pointer * 3,
                    width: self.pointer * 4,
                    maximum: self.pointer * 5,
                    destroy: self.pointer * 6,
                }),
            ),
            TypeDefinition::KeyedCollection { .. } => {
                let region_size = self.pointer * 7;
                (
                    region_size * 2 + self.pointer * 5,
                    self.pointer,
                    vec![],
                    vec![],
                    None,
                    None,
                    Some(NativeDescriptorLayout::Map {
                        entries: 0,
                        index: region_size,
                        value_width: region_size * 2,
                        value_offset: region_size * 2 + self.pointer,
                        count: region_size * 2 + self.pointer * 2,
                        free_head: region_size * 2 + self.pointer * 3,
                        destroy: region_size * 2 + self.pointer * 4,
                    }),
                )
            }
            TypeDefinition::InlineUtf8 { maximum_bytes } => {
                let bytes = self.pointer.checked_add(maximum_bytes)?;
                (
                    align_up(bytes, self.pointer)?,
                    self.pointer,
                    vec![],
                    vec![],
                    None,
                    None,
                    Some(NativeDescriptorLayout::InlineUtf8 {
                        length: 0,
                        data: self.pointer,
                        maximum_bytes,
                    }),
                )
            }
            TypeDefinition::Pool { .. } => (
                self.pointer,
                self.pointer,
                vec![],
                vec![],
                None,
                None,
                Some(NativeDescriptorLayout::Pool { state: 0 }),
            ),
        };
        Some(TypeLayout {
            id: LayoutId(0),
            ty,
            size: LayoutSize::Fixed(size),
            alignment,
            fields,
            tuple_elements,
            sequence,
            variant,
            native,
        })
    }

    fn nominal_layout(&mut self, ty: TypeId) -> Option<TypeLayout> {
        if let Some(definition) = self
            .p
            .declarations
            .structs
            .iter()
            .find(|item| item.ty == ty)
        {
            let mut offset = 0u64;
            let mut alignment = 1u64;
            let mut fields = vec![];
            for field in &definition.fields {
                let field_definition = &self.p.declarations.fields[field.0 as usize];
                let layout_id = self.layout(field_definition.ty)?;
                let layout = &self.layouts[layout_id.0 as usize];
                let field_alignment = layout.alignment;
                let field_size = fixed_size(layout)?;
                offset = align_up(offset, field_alignment)?;
                fields.push(FieldLayout {
                    field: *field,
                    byte_offset: offset,
                    layout: layout_id,
                });
                offset = offset.checked_add(field_size)?;
                alignment = alignment.max(field_alignment);
            }
            return Some(TypeLayout {
                id: LayoutId(0),
                ty,
                size: LayoutSize::Fixed(align_up(offset, alignment)?),
                alignment,
                fields,
                tuple_elements: vec![],
                sequence: None,
                variant: None,
                native: None,
            });
        }
        let definition = self
            .p
            .declarations
            .enums
            .iter()
            .find(|item| item.ty == ty)?;
        let variant_count = 1 + definition.variants.rest.len() as u64;
        let discriminant_bytes = if variant_count <= 0x100 {
            1
        } else if variant_count <= 0x1_0000 {
            2
        } else if variant_count <= 0x1_0000_0000 {
            4
        } else {
            8
        };
        let mut variants = vec![];
        let mut payload_size = 0u64;
        let mut payload_alignment = 1u64;
        for (discriminant, variant_id) in std::iter::once(&definition.variants.first)
            .chain(&definition.variants.rest)
            .enumerate()
        {
            let definition = &self.p.declarations.variants[variant_id.0 as usize];
            let mut size = 0u64;
            let mut alignment = 1u64;
            let mut fields = vec![];
            for field in &definition.fields {
                let field_definition = &self.p.declarations.fields[field.0 as usize];
                let layout_id = self.layout(field_definition.ty)?;
                let layout = &self.layouts[layout_id.0 as usize];
                size = align_up(size, layout.alignment)?;
                fields.push(FieldLayout {
                    field: *field,
                    byte_offset: size,
                    layout: layout_id,
                });
                size = size.checked_add(fixed_size(layout)?)?;
                alignment = alignment.max(layout.alignment);
            }
            size = align_up(size, alignment)?;
            payload_size = payload_size.max(size);
            payload_alignment = payload_alignment.max(alignment);
            variants.push(VariantLayout {
                variant: *variant_id,
                discriminant: discriminant as u64,
                fields,
            });
        }
        let alignment = payload_alignment.max(discriminant_bytes as u64);
        let payload_offset = align_up(discriminant_bytes as u64, payload_alignment)?;
        let size = align_up(payload_offset.checked_add(payload_size)?, alignment)?;
        Some(TypeLayout {
            id: LayoutId(0),
            ty,
            size: LayoutSize::Fixed(size),
            alignment,
            fields: vec![],
            tuple_elements: vec![],
            sequence: None,
            variant: Some(EnumLayout {
                discriminant_bytes,
                payload_offset,
                variants,
            }),
            native: None,
        })
    }

    fn tuple_layout(&mut self, types: &[TypeId]) -> Option<(u64, u64, Vec<TupleElementLayout>)> {
        let mut size = 0u64;
        let mut alignment = 1u64;
        let mut elements = vec![];
        for (position, ty) in types.iter().copied().enumerate() {
            let layout_id = self.layout(ty)?;
            let layout = &self.layouts[layout_id.0 as usize];
            size = align_up(size, layout.alignment)?;
            elements.push(TupleElementLayout {
                position: position as u32,
                byte_offset: size,
                layout: layout_id,
            });
            size = size.checked_add(fixed_size(layout)?)?;
            alignment = alignment.max(layout.alignment);
        }
        Some((align_up(size, alignment)?, alignment, elements))
    }

    fn layout_value(&mut self, ty: TypeId) -> Option<(u64, u64)> {
        let id = self.layout(ty)?;
        let layout = &self.layouts[id.0 as usize];
        Some((fixed_size(layout)?, layout.alignment))
    }
}

fn fixed_size(layout: &TypeLayout) -> Option<u64> {
    match layout.size {
        LayoutSize::Fixed(size) => Some(size),
        LayoutSize::FromValue(_) => None,
    }
}

fn align_up(value: u64, alignment: u64) -> Option<u64> {
    let mask = alignment.checked_sub(1)?;
    value.checked_add(mask).map(|value| value & !mask)
}

// -------------------------------------------------------------------------
// Reservations, regions, cursors and cleanup

struct Planner {
    input: MemoryPlanningInput,
    layouts: HashMap<TypeId, LayoutId>,
    cursors: Vec<CursorExpression>,
    scope_cursors: HashMap<ScopeId, CursorExpressionId>,
    body_cursors: HashMap<BodyId, CursorExpressionId>,
    physical_scope_started: HashSet<ScopeId>,
    scope_entries: Vec<ScopeCursorPlan>,
    reservations: Vec<StorageReservation>,
    value_storage: Vec<ValueStoragePlan>,
    edge_transfers: Vec<EdgeValueTransfer>,
    iteration_counters: Vec<IterationCounterPlan>,
    assignments: Vec<ReservationAssignment>,
    sharing: Vec<ExclusiveReservationGroup>,
    physical_proofs: Vec<PhysicalPlanningProof>,
    realization: Vec<PhysicalPlacementEvidence>,
    regions: Vec<RegionPlan>,
    region_classes: Vec<RegionClassPlan>,
    dedicated_region_stacks: Vec<(DataStackId, ScopeId)>,
    backings: Vec<BackingStoragePlan>,
    missing: Vec<MissingPlanInput>,
    diagnostics: Vec<PhysicalPlanningDiagnostic>,
    fixed_known_bytes: u64,
    fixed_bound_known: bool,
}

impl Planner {
    fn new(input: MemoryPlanningInput) -> Self {
        let p = post_ast(&input.checked_flow);
        let layouts = input
            .layouts
            .layouts
            .iter()
            .map(|layout| (layout.ty, layout.id))
            .collect();
        let cursors = p.cursor_expressions.clone();
        let scope_entries = p
            .scopes
            .storage
            .iter()
            .map(|storage| {
                // The semantic scope cursor records the storage identities
                // materialized while resolving the program. It is evidence
                // for placement, not an already-allocated physical prefix.
                // Physical planning starts at the scope-entry snapshot and
                // lays every reservation and temporary exactly once.
                let scope = &p.scopes.entries[storage.scope.0 as usize];
                let cursor = match scope.entry {
                    ScopeEntry::Child { parent_cursor, .. } => {
                        p.cursor_snapshots[parent_cursor.0 as usize].cursor
                    }
                    _ => p.cursor_snapshots[storage.entry.0 as usize].cursor,
                };
                ScopeCursorPlan {
                    scope: storage.scope,
                    cursor,
                }
            })
            .collect::<Vec<_>>();
        let scope_cursors = scope_entries
            .iter()
            .map(|entry| (entry.scope, entry.cursor))
            .collect::<HashMap<_, _>>();
        let body_cursors = p
            .bodies
            .iter()
            .map(|body| (body.id, scope_cursors[&body.scope]))
            .collect();
        let physical_scope_started = p.bodies.iter().map(|body| body.scope).collect();
        Self {
            input,
            layouts,
            cursors,
            scope_cursors,
            body_cursors,
            physical_scope_started,
            scope_entries,
            reservations: vec![],
            value_storage: vec![],
            edge_transfers: vec![],
            iteration_counters: vec![],
            assignments: vec![],
            sharing: vec![],
            physical_proofs: vec![],
            realization: vec![],
            regions: vec![],
            region_classes: vec![],
            dedicated_region_stacks: vec![],
            backings: vec![],
            missing: vec![],
            diagnostics: vec![],
            fixed_known_bytes: 0,
            fixed_bound_known: true,
        }
    }

    fn finish(mut self) -> MemoryPlanningResult {
        self.reserve_destinations();
        self.plan_value_storage();
        self.finalize_scope_entries();
        self.plan_edge_transfers();
        self.plan_iteration_counters();
        self.realize_requirements();
        self.validate_capacities();
        if !self.missing.is_empty() {
            self.missing.sort_by_key(missing_key);
            self.missing.dedup_by_key(|missing| missing_key(missing));
            return MemoryPlanningResult::MissingPlanInput(IncompleteMemoryPlan {
                checked_flow: self.input.checked_flow,
                layouts: self.input.layouts,
                missing: non_empty(self.missing),
            });
        }
        if !self.diagnostics.is_empty() {
            return MemoryPlanningResult::Rejected(RejectedMemoryPlan {
                checked_flow: self.input.checked_flow,
                layouts: self.input.layouts,
                diagnostics: non_empty(self.diagnostics),
            });
        }
        let cleanup = self.cleanup_plan();
        let async_states = self.async_state_plan();
        let foreign = self.foreign_emission_plan();
        let stacks = self.stack_plans();
        let p = post_ast(&self.input.checked_flow);
        let storage = StoragePlan {
            stacks,
            scope_entries: self.scope_entries,
            regions: self.regions,
            region_classes: self.region_classes,
            origins: p.storage_origins.iter().map(|origin| origin.id).collect(),
            reservations: self.reservations,
            values: self.value_storage,
            edge_transfers: self.edge_transfers,
            iteration_counters: self.iteration_counters,
            backings: self.backings,
            cursors: self.cursors,
            snapshots: p.cursor_snapshots.clone(),
        };
        MemoryPlanningResult::Planned(PlannedPostAst {
            layouts: self.input.layouts,
            checked_flow: self.input.checked_flow,
            reservations: self.assignments,
            sharing: self.sharing,
            storage,
            cleanup,
            async_states,
            foreign,
            physical_proofs: self.physical_proofs,
            realization: self.realization,
        })
    }

    /// Resolve the complete physical async-frame contract while both the
    /// semantic frame inventory and target layouts are available.  This is a
    /// memory-plan result: code generation must not repeat the liveness or
    /// field-offset analysis.
    fn async_state_plan(&mut self) -> AsyncStatePlan {
        let p = post_ast(&self.input.checked_flow);
        let mut frames = Vec::new();
        for frame in &p.async_frames {
            let Some(&layout) = self.layouts.get(&frame.state_type) else {
                self.missing
                    .push(MissingPlanInput::TypeLayout(frame.state_type));
                continue;
            };
            let physical = &self.input.layouts.layouts[layout.0 as usize];
            let Some(state_offset) = physical
                .fields
                .iter()
                .find(|field| field.field == frame.state_field)
                .map(|field| field.byte_offset)
            else {
                self.missing
                    .push(MissingPlanInput::TypeLayout(frame.state_type));
                continue;
            };
            let mut saved = Vec::new();
            for slot in &frame.slots {
                let value = p.values.entries.iter().map(|value| value.id).find(|value| {
                    matches!(p.values.entries[value.0 as usize].definition,
                        ValueDefinition::Parameter(binding) if binding == slot.binding)
                        || matches!(p.values.provenance[p.values.entries[value.0 as usize].provenance.0 as usize].kind,
                            ProvenanceKind::Binding(binding) if binding == slot.binding)
                });
                let Some(value) = value else {
                    continue;
                };
                let Some(byte_offset) = physical
                    .fields
                    .iter()
                    .find(|field| field.field == slot.field)
                    .map(|field| field.byte_offset)
                else {
                    self.missing
                        .push(MissingPlanInput::TypeLayout(frame.state_type));
                    continue;
                };
                saved.push(SavedStateValue {
                    value,
                    field: slot.field,
                    byte_offset,
                    dependencies: p.values.entries[value.0 as usize].dependencies,
                });
            }
            let transitions = frame
                .suspensions
                .iter()
                .enumerate()
                .flat_map(|(index, suspension)| {
                    let point = &p.execution.suspensions[suspension.0 as usize];
                    std::iter::once(&point.resumptions.first)
                        .chain(&point.resumptions.rest)
                        .map(move |resume| AsyncTransition {
                            suspension: *suspension,
                            resume: resume.moment,
                            discriminant: index as u64 + 1,
                        })
                })
                .collect();
            frames.push(AsyncFrameLayout {
                body: frame.body,
                ty: frame.state_type,
                layout,
                state_field: frame.state_field,
                state_offset,
                completed_discriminant: frame.suspensions.len() as u64 + 1,
                saved,
                transitions,
            });
        }
        AsyncStatePlan { frames }
    }

    fn foreign_emission_plan(&mut self) -> ForeignEmissionPlan {
        let p = post_ast(&self.input.checked_flow);
        let mut seen = HashSet::new();
        let mut operands = Vec::new();
        for body in &p.bodies {
            for operation in &body.operations {
                let (region, entries): (ForeignRegionId, &[ForeignOperand]) = match operation {
                    Operation::ForeignC(value) => (value.region, &value.operands),
                    Operation::ForeignCpp(value) => (value.region, &value.operands),
                    Operation::ForeignAssembly(value) => (value.region, &value.operands),
                    _ => continue,
                };
                for operand in entries {
                    if !seen.insert(operand.id) {
                        continue;
                    }
                    let Some(&layout) = self.layouts.get(&operand.ty) else {
                        self.missing.push(MissingPlanInput::TypeLayout(operand.ty));
                        continue;
                    };
                    operands.push(ForeignOperandLayout {
                        operand: operand.id,
                        region,
                        value: operand.value,
                        layout,
                    });
                }
            }
        }
        ForeignEmissionPlan {
            regions: p.foreign_regions.clone(),
            operands,
        }
    }

    /// Freeze the physical cursor inherited by each runtime child scope only
    /// after every reservation, temporary and compiler-owned backing in its
    /// parent has been planned.  Semantic cursor snapshots intentionally do
    /// not include storage introduced by physical planning and therefore
    /// cannot be emitted as final runtime addresses.
    fn finalize_scope_entries(&mut self) {
        let scopes = self
            .scope_entries
            .iter()
            .map(|entry| entry.scope)
            .collect::<Vec<_>>();
        for scope in scopes {
            if !self.physical_scope_started.contains(&scope) {
                self.begin_physical_scope(scope);
            }
        }
    }

    /// Assign every resolved value to a physical source. This is deliberately
    /// complete: later code generation is forbidden from inventing locals.
    fn plan_value_storage(&mut self) {
        let values = post_ast(&self.input.checked_flow).values.entries.clone();
        for value in values {
            let ty = value.ty;
            let kind = &post_ast(&self.input.checked_flow).types.entries[ty.0 as usize].kind;
            let absence = match kind {
                TypeDefinition::Never => Some(ValueStorageAbsence::Never),
                TypeDefinition::Parameter(_) => Some(ValueStorageAbsence::AbstractType),
                TypeDefinition::StrData => Some(ValueStorageAbsence::UnsizedData),
                _ => None,
            };
            if let Some(reason) = absence {
                self.value_storage.push(ValueStoragePlan {
                    value: value.id,
                    layout: None,
                    alternatives: NonEmpty {
                        first: GuardedValueStorage {
                            guard: PredicateId(0),
                            kind: ValueStorageKind::None(reason),
                        },
                        rest: vec![],
                    },
                });
                continue;
            }

            // Caller parameters, closure captures and immutable constants are
            // physical sources supplied outside this body.  A logical final
            // destination may retain their value, but it must never replace
            // that external source with a body-local reservation.
            let external = match value.definition {
                ValueDefinition::Parameter(binding) => {
                    Some(ValueStorageKind::Parameter { binding })
                }
                ValueDefinition::CaptureField { record, field } => {
                    Some(ValueStorageKind::Capture { record, field })
                }
                ValueDefinition::Constant(_) | ValueDefinition::ConfiguredConstant { .. } => {
                    Some(ValueStorageKind::Constant)
                }
                _ => None,
            };
            if let Some(kind) = external {
                let Some(layout) = self.layouts.get(&ty).copied() else {
                    self.missing.push(MissingPlanInput::TypeLayout(ty));
                    continue;
                };
                self.value_storage.push(ValueStoragePlan {
                    value: value.id,
                    layout: Some(layout),
                    alternatives: NonEmpty {
                        first: GuardedValueStorage {
                            guard: PredicateId(0),
                            kind,
                        },
                        rest: vec![],
                    },
                });
                continue;
            }

            let Some(layout) = self.layouts.get(&ty).copied() else {
                self.missing.push(MissingPlanInput::TypeLayout(ty));
                continue;
            };
            let mut reserved = self
                .assignments
                .iter()
                .filter_map(|assignment| {
                    let final_ = self
                        .input
                        .checked_flow
                        .semantics
                        .finals
                        .iter()
                        .find(|final_| final_.id == assignment.destination)?;
                    (final_.value == value.id).then_some(GuardedValueStorage {
                        guard: final_.guard,
                        kind: ValueStorageKind::Reservation(assignment.reservation),
                    })
                })
                .collect::<Vec<_>>();
            if reserved.len() == 1 {
                // A single physical destination is not a runtime choice. Its
                // cleanup/path guard may depend on values produced later and
                // must never guard the availability of the address itself.
                reserved[0].guard = PredicateId(0);
            } else if reserved.first().is_some_and(|first| {
                let ValueStorageKind::Reservation(reservation) = first.kind else {
                    return false;
                };
                reserved.iter().all(|candidate| {
                    matches!(candidate.kind, ValueStorageKind::Reservation(other) if other == reservation)
                })
            }) {
                // Mutually exclusive logical destinations that share one
                // reservation also have one unconditional physical address.
                reserved.truncate(1);
                reserved[0].guard = PredicateId(0);
            }
            if let Some((first, rest)) = reserved.split_first() {
                self.value_storage.push(ValueStoragePlan {
                    value: value.id,
                    layout: Some(layout),
                    alternatives: NonEmpty {
                        first: first.clone(),
                        rest: rest.to_vec(),
                    },
                });
                continue;
            }

            if let Some(alternatives) = self.alias_storage(&value) {
                self.value_storage.push(ValueStoragePlan {
                    value: value.id,
                    layout: Some(layout),
                    alternatives,
                });
                continue;
            }

            let (guard, storage) = match value.definition {
                ValueDefinition::Parameter(_)
                | ValueDefinition::CaptureField { .. }
                | ValueDefinition::Constant(_)
                | ValueDefinition::ConfiguredConstant { .. } => {
                    unreachable!("external value storage is selected before reservations")
                }
                ValueDefinition::Diverged { .. } => (
                    PredicateId(0),
                    ValueStorageKind::None(ValueStorageAbsence::Diverged),
                ),
                ValueDefinition::ConditionalResult {
                    operation,
                    produced_at,
                    guard,
                } => {
                    let scope = self.operation_scope(operation);
                    (guard, self.temporary_value(scope, produced_at, ty, layout))
                }
                ValueDefinition::OperationResult {
                    operation,
                    produced_at,
                } => {
                    let site = self.operation_site(operation);
                    let (guard, allocated_at) = self
                        .loop_parameter_entry(operation)
                        .map(|entry| (PredicateId(0), entry))
                        .unwrap_or((site.guard, produced_at));
                    (
                        guard,
                        self.temporary_value(site.scope, allocated_at, ty, layout),
                    )
                }
            };
            self.value_storage.push(ValueStoragePlan {
                value: value.id,
                layout: Some(layout),
                alternatives: NonEmpty {
                    first: GuardedValueStorage {
                        guard,
                        kind: storage,
                    },
                    rest: vec![],
                },
            });
        }
    }

    fn alias_storage(&self, value: &Value) -> Option<NonEmpty<GuardedValueStorage>> {
        let operation = match value.definition {
            ValueDefinition::OperationResult { operation, .. }
            | ValueDefinition::ConditionalResult { operation, .. } => operation,
            _ => return None,
        };
        let operation = post_ast(&self.input.checked_flow)
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .find(|candidate| candidate.site().id == operation)?;
        let alternatives = match operation {
            Operation::MoveValue(moved) if moved.result == value.id => vec![GuardedValueStorage {
                guard: moved.site.guard,
                kind: ValueStorageKind::Alias {
                    source: moved.value,
                    bound_at: moved.site.execution_moments.first,
                },
            }],
            Operation::ReceiveValue(received) if received.result == value.id => {
                vec![GuardedValueStorage {
                    guard: received.site.guard,
                    kind: ValueStorageKind::Alias {
                        source: received.source,
                        bound_at: received.site.execution_moments.first,
                    },
                }]
            }
            Operation::ForwardResult(forwarded) if forwarded.destination == value.id => {
                vec![GuardedValueStorage {
                    guard: forwarded.site.guard,
                    kind: ValueStorageKind::Alias {
                        source: forwarded.source,
                        bound_at: forwarded.site.execution_moments.first,
                    },
                }]
            }
            Operation::ParametricTransfer(transfer) if transfer.result == value.id => {
                vec![GuardedValueStorage {
                    guard: transfer.site.guard,
                    kind: ValueStorageKind::SelectAlias {
                        predicate: transfer.copies,
                        when_true: transfer.copied,
                        when_false: transfer.moved,
                        bound_at: transfer.site.execution_moments.first,
                    },
                }]
            }
            Operation::MergeValue(merged) if merged.result == value.id => {
                std::iter::once(&merged.incoming.first)
                    .chain(&merged.incoming.rest)
                    .map(|incoming| GuardedValueStorage {
                        guard: incoming.guard,
                        kind: ValueStorageKind::Alias {
                            source: incoming.value,
                            bound_at: merged.site.execution_moments.first,
                        },
                    })
                    .collect()
            }
            // Loop parameters require stable storage whose contents are
            // updated on incoming execution edges. Treating them as guarded
            // aliases would evaluate a back-edge predicate on first entry.
            Operation::LoopParameter(_) => return None,
            _ => return None,
        };
        let (first, rest) = alternatives.split_first()?;
        Some(NonEmpty {
            first: first.clone(),
            rest: rest.to_vec(),
        })
    }

    fn plan_edge_transfers(&mut self) {
        let p = post_ast(&self.input.checked_flow);
        for body in &p.bodies {
            for operation in &body.operations {
                let Operation::LoopParameter(parameter) = operation else {
                    continue;
                };
                let header = p
                    .execution
                    .edges
                    .iter()
                    .find_map(|edge| match edge {
                        ExecutionEdge::LoopBack(edge) if edge.region == parameter.region => {
                            Some(edge.to)
                        }
                        _ => None,
                    })
                    .unwrap_or(parameter.site.execution_moments.first);
                for edge in &p.execution.edges {
                    let (from, to, loop_back) = match edge {
                        ExecutionEdge::Sequence(edge) if edge.after == header => {
                            (edge.before, edge.after, false)
                        }
                        ExecutionEdge::Conditional(edge) if edge.to == header => {
                            (edge.from, edge.to, false)
                        }
                        ExecutionEdge::LoopBack(edge)
                            if edge.to == header && edge.region == parameter.region =>
                        {
                            (edge.from, edge.to, true)
                        }
                        _ => continue,
                    };
                    if loop_back {
                        self.edge_transfers
                            .extend(parameter.back_edges.iter().map(|incoming| {
                                EdgeValueTransfer {
                                    from,
                                    to,
                                    destination: parameter.result,
                                    source: incoming.value,
                                    guard: incoming.guard,
                                }
                            }));
                    } else {
                        self.edge_transfers.push(EdgeValueTransfer {
                            from,
                            to,
                            destination: parameter.result,
                            source: parameter.initial,
                            guard: PredicateId(0),
                        });
                    }
                }
            }
        }
    }

    fn loop_parameter_entry(&self, operation: OperationId) -> Option<ExecutionMomentId> {
        let p = post_ast(&self.input.checked_flow);
        let parameter = p.bodies.iter().flat_map(|body| &body.operations).find_map(
            |candidate| match candidate {
                Operation::LoopParameter(parameter) if parameter.site.id == operation => {
                    Some(parameter)
                }
                _ => None,
            },
        )?;
        let header = p.execution.edges.iter().find_map(|edge| match edge {
            ExecutionEdge::LoopBack(edge) if edge.region == parameter.region => Some(edge.to),
            _ => None,
        })?;
        p.execution.edges.iter().find_map(|edge| match edge {
            ExecutionEdge::Sequence(edge) if edge.after == header => Some(edge.before),
            ExecutionEdge::Conditional(edge) if edge.to == header => Some(edge.from),
            _ => None,
        })
    }

    fn plan_iteration_counters(&mut self) {
        let p = post_ast(&self.input.checked_flow);
        let used = p
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .filter_map(|operation| match operation {
                Operation::IterationIndex(index) => Some(index.coordinate),
                _ => None,
            })
            .collect::<std::collections::HashSet<_>>();
        for variable in &p.execution.iteration_variables {
            if !used.contains(&variable.id) {
                continue;
            }
            let Some(header) = p.execution.edges.iter().find_map(|edge| match edge {
                ExecutionEdge::LoopBack(edge) if edge.region == variable.region => Some(edge.to),
                _ => None,
            }) else {
                continue;
            };
            let mut entry_edges = Vec::new();
            let mut back_edges = Vec::new();
            for edge in &p.execution.edges {
                match edge {
                    ExecutionEdge::Sequence(edge) if edge.after == header => {
                        entry_edges.push(ExecutionEdgePoint {
                            from: edge.before,
                            to: edge.after,
                        });
                    }
                    ExecutionEdge::Conditional(edge) if edge.to == header => {
                        entry_edges.push(ExecutionEdgePoint {
                            from: edge.from,
                            to: edge.to,
                        });
                    }
                    ExecutionEdge::LoopBack(edge)
                        if edge.to == header && edge.region == variable.region =>
                    {
                        back_edges.push(ExecutionEdgePoint {
                            from: edge.from,
                            to: edge.to,
                        });
                    }
                    _ => {}
                }
            }
            self.iteration_counters.push(IterationCounterPlan {
                coordinate: variable.id,
                region: variable.region,
                entry_edges,
                back_edges,
            });
        }
    }

    fn temporary_value(
        &mut self,
        scope: ScopeId,
        allocated_at: ExecutionMomentId,
        ty: TypeId,
        layout: LayoutId,
    ) -> ValueStorageKind {
        self.begin_physical_scope(scope);
        let start = self.body_cursor(scope);
        let end = self.cursor(CursorExpressionKind::AdvanceByType { base: start, ty });
        self.advance_body_cursor(scope, end);
        match self.input.layouts.layouts[layout.0 as usize].size {
            LayoutSize::Fixed(bytes) => {
                let alignment = self.input.layouts.layouts[layout.0 as usize].alignment;
                self.fixed_known_bytes = align_up(self.fixed_known_bytes, alignment)
                    .unwrap_or(u64::MAX)
                    .saturating_add(bytes);
            }
            LayoutSize::FromValue(_) => self.fixed_bound_known = false,
        }
        ValueStorageKind::Temporary {
            scope,
            stack: self.fixed_stack(),
            start,
            end,
            allocated_at,
        }
    }

    fn operation_site(&self, operation: OperationId) -> OperationSite {
        post_ast(&self.input.checked_flow)
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .find(|candidate| candidate.site().id == operation)
            .map(|candidate| candidate.site().clone())
            .expect("resolved value operation is present in PostAST")
    }

    fn operation_scope(&self, operation: OperationId) -> ScopeId {
        self.operation_site(operation).scope
    }

    fn reserve_destinations(&mut self) {
        let finals = self.input.checked_flow.semantics.finals.clone();
        for final_ in finals {
            let p = post_ast(&self.input.checked_flow);
            let ty = p.values.entries[final_.value.0 as usize].ty;
            let Some(layout) = self.layouts.get(&ty).copied() else {
                self.missing.push(MissingPlanInput::TypeLayout(ty));
                continue;
            };
            let destination_scope = self
                .shared_destination_scope(final_.value)
                .unwrap_or_else(|| self.logical_destination_scope(&final_));
            if let Some(existing) =
                self.compatible_exclusive_reservation(&final_, layout, destination_scope)
            {
                self.assign_existing_shared(&final_, existing);
                continue;
            }
            let Some((_address, origin)) = self.address_and_origin(final_.value, final_.guard)
            else {
                // Copy-only scalar values do not own storage identities and do
                // not need a durable reservation. Final destinations are
                // otherwise expected to identify an address.
                continue;
            };
            let construction = self.construction(final_.requirement);
            let initialization = self.initialization(final_.value, construction);
            let (reserved_at, issuer) =
                self.issuer(&final_, destination_scope, initialization, origin);
            self.begin_physical_scope(destination_scope);
            let start = self.body_cursor(destination_scope);
            let end = self.cursor(CursorExpressionKind::AdvanceByType { base: start, ty });
            self.advance_body_cursor(destination_scope, end);
            let id = StorageReservationId(self.reservations.len() as u32);
            let fixed_size = self.input.layouts.layouts[layout.0 as usize].size.clone();
            match fixed_size {
                LayoutSize::Fixed(bytes) => {
                    let alignment = self.input.layouts.layouts[layout.0 as usize].alignment;
                    self.fixed_known_bytes = align_up(self.fixed_known_bytes, alignment)
                        .unwrap_or(u64::MAX)
                        .saturating_add(bytes)
                }
                LayoutSize::FromValue(_) => self.fixed_bound_known = false,
            }
            self.reservations.push(StorageReservation {
                id,
                value: final_.value,
                destination: destination_scope,
                storage: origin,
                layout,
                guard: final_.guard,
                reserved_at,
                stack: self.fixed_stack(),
                region: None,
                start,
                end,
                retained_until: vec![],
            });
            self.assignments.push(ReservationAssignment {
                reservation: id,
                issuer,
                initialization_at: initialization,
                reserved_at,
                construction_at: construction,
                destination: final_.id,
                origin,
            });
            self.plan_backing(final_.value, ty, destination_scope, id, end);
        }
    }

    fn compatible_exclusive_reservation(
        &self,
        final_: &LogicalFinalDestination,
        layout: LayoutId,
        destination_scope: ScopeId,
    ) -> Option<StorageReservationId> {
        self.assignments.iter().find_map(|assignment| {
            let prior = self
                .input
                .checked_flow
                .semantics
                .finals
                .iter()
                .find(|candidate| candidate.id == assignment.destination)?;
            let reservation = &self.reservations[assignment.reservation.0 as usize];
            let same_value = prior.value == final_.value;
            let compatible_lifetime = if same_value {
                reservation.destination == destination_scope
            } else {
                same_scope(&prior.scope, &final_.scope)
                    && same_owner(&prior.cleanup_owner, &final_.cleanup_owner)
                    && same_cleanup(&prior.cleanup_exit, &final_.cleanup_exit)
            };
            (reservation.layout == layout
                && compatible_lifetime
                && guards_exclusive(
                    post_ast(&self.input.checked_flow),
                    prior.guard,
                    final_.guard,
                ))
            .then_some(reservation.id)
        })
    }

    /// Values whose final receiver depends on a later branch need one address
    /// that is already valid at construction. Reserving in the nearest common
    /// lexical ancestor is always safe; paths selected before construction may
    /// later be optimized back to separate branch-local reservations.
    fn shared_destination_scope(&self, value: ValueId) -> Option<ScopeId> {
        let finals = self
            .input
            .checked_flow
            .semantics
            .finals
            .iter()
            .filter(|candidate| candidate.value == value)
            .collect::<Vec<_>>();
        if finals.len() < 2 {
            return None;
        }
        let mut scope = self.logical_destination_scope(finals[0]);
        for final_ in finals.iter().skip(1) {
            scope = self.common_lexical_ancestor(scope, self.logical_destination_scope(final_))?;
        }
        Some(scope)
    }

    fn logical_destination_scope(&self, final_: &LogicalFinalDestination) -> ScopeId {
        match final_.scope {
            LogicalScope::Local(scope) => scope,
            _ => {
                let p = post_ast(&self.input.checked_flow);
                self.address_and_origin(final_.value, final_.guard)
                    .map(|(address, _)| p.objects.addresses[address.0 as usize].created_in)
                    .unwrap_or_else(|| {
                        let moment = self.construction(final_.requirement);
                        let operation = p.execution.execution_moments[moment.0 as usize].operation;
                        self.operation_site(operation).scope
                    })
            }
        }
    }

    fn common_lexical_ancestor(&self, left: ScopeId, right: ScopeId) -> Option<ScopeId> {
        let p = post_ast(&self.input.checked_flow);
        let mut left_ancestors = std::collections::HashSet::new();
        let mut current = Some(left);
        while let Some(scope) = current {
            left_ancestors.insert(scope);
            current = p.scopes.entries[scope.0 as usize].lexical_parent;
        }
        let mut current = Some(right);
        while let Some(scope) = current {
            if left_ancestors.contains(&scope) {
                return Some(scope);
            }
            current = p.scopes.entries[scope.0 as usize].lexical_parent;
        }
        None
    }

    fn assign_existing_shared(
        &mut self,
        final_: &LogicalFinalDestination,
        reservation: StorageReservationId,
    ) {
        let prior_assignment = self
            .assignments
            .iter()
            .find(|assignment| assignment.reservation == reservation)
            .cloned()
            .unwrap();
        let prior = self
            .input
            .checked_flow
            .semantics
            .finals
            .iter()
            .find(|candidate| candidate.id == prior_assignment.destination)
            .cloned()
            .unwrap();
        let construction = self.construction(final_.requirement);
        let initialization = self.initialization(final_.value, construction);
        let destination_scope = self.reservations[reservation.0 as usize].destination;
        let (reserved_at, issuer) = self.issuer(
            final_,
            destination_scope,
            initialization,
            prior_assignment.origin,
        );
        let exclusive = self.physical_proof(PhysicalPlanningFact::GuardsExclusive {
            first: prior.guard,
            second: final_.guard,
        });
        let layout = self.reservations[reservation.0 as usize].layout;
        let compatible = self.physical_proof(PhysicalPlanningFact::LayoutsCompatible {
            first: layout,
            second: layout,
        });
        if let Some(group) = self
            .sharing
            .iter_mut()
            .find(|group| group.reservation == reservation)
        {
            group.initializers.rest.push(GuardedConstruction {
                value: final_.value,
                construction,
                guard: final_.guard,
            });
        } else {
            self.sharing.push(ExclusiveReservationGroup {
                id: ReservationGroupId(self.sharing.len() as u32),
                reservation,
                initializers: NonEmpty {
                    first: GuardedConstruction {
                        value: prior.value,
                        construction: prior_assignment.initialization_at,
                        guard: prior.guard,
                    },
                    rest: vec![GuardedConstruction {
                        value: final_.value,
                        construction: initialization,
                        guard: final_.guard,
                    }],
                },
                exclusivity_evidence: exclusive,
                compatibility_evidence: compatible,
            });
        }
        self.assignments.push(ReservationAssignment {
            reservation,
            issuer,
            initialization_at: initialization,
            reserved_at,
            construction_at: construction,
            destination: final_.id,
            origin: prior_assignment.origin,
        });
    }

    fn plan_backing(
        &mut self,
        value: ValueId,
        ty: TypeId,
        scope: ScopeId,
        reservation: StorageReservationId,
        descriptor_end: CursorExpressionId,
    ) {
        let kind = post_ast(&self.input.checked_flow).types.entries[ty.0 as usize]
            .kind
            .clone();
        match kind {
            TypeDefinition::Pool { element } => {
                let capacity = post_ast(&self.input.checked_flow)
                    .bodies
                    .iter()
                    .flat_map(|body| &body.operations)
                    .find_map(|op| {
                        if let Operation::CreatePool(pool) = op {
                            (pool.result == value).then_some(pool.capacity)
                        } else {
                            None
                        }
                    });
                let Some(capacity) = capacity else {
                    return;
                };
                let known_capacity = constant_u64(post_ast(&self.input.checked_flow), capacity);
                let pointer = u64::from(post_ast(&self.input.checked_flow).target.pointer_bits / 8);
                // `corbo_pool_state` is four pointers, five size_t values and
                // one destructor pointer on every supported target ABI.
                let state_bytes = pointer * 10;
                let state_start = self.cursor(CursorExpressionKind::Align {
                    base: descriptor_end,
                    alignment: pointer,
                });
                let state_end = self.cursor(CursorExpressionKind::AdvanceFixedBytes {
                    base: state_start,
                    bytes: state_bytes,
                });
                let element_alignment = self
                    .layouts
                    .get(&element)
                    .map(|layout| self.input.layouts.layouts[layout.0 as usize].alignment)
                    .unwrap_or(1);
                let slots_start = self.cursor(CursorExpressionKind::Align {
                    base: state_end,
                    alignment: element_alignment,
                });
                let slots_end = self.cursor(CursorExpressionKind::AdvancePoolSlots {
                    base: slots_start,
                    element,
                    count: capacity,
                });
                let occupancy_end = self.cursor(CursorExpressionKind::AdvanceBytes {
                    base: slots_end,
                    bytes: capacity,
                });
                let free_slots_start = self.cursor(CursorExpressionKind::Align {
                    base: occupancy_end,
                    alignment: pointer,
                });
                let free_slots_end = self.cursor(CursorExpressionKind::AdvanceScaledBytes {
                    base: free_slots_start,
                    count: capacity,
                    width: pointer,
                });
                self.advance_body_cursor(scope, free_slots_end);
                self.backings.push(BackingStoragePlan {
                    owner: value,
                    kind: BackingStorageKind::PoolSlots {
                        element,
                        capacity,
                        stack: self.fixed_stack(),
                        state_start,
                        state_end,
                        slots_start,
                        slots_end,
                        occupancy_start: slots_end,
                        occupancy_end,
                        free_slots_start,
                        free_slots_end,
                    },
                });
                if let (Some(count), Some(layout)) =
                    (known_capacity, self.layouts.get(&element).copied())
                {
                    if let Some(size) = fixed_size(&self.input.layouts.layouts[layout.0 as usize]) {
                        let alignment = self.input.layouts.layouts[layout.0 as usize].alignment;
                        let stride = align_up(size, alignment).unwrap_or(u64::MAX);
                        self.fixed_known_bytes = self
                            .fixed_known_bytes
                            .saturating_add(state_bytes)
                            .saturating_add(stride.saturating_mul(count))
                            .saturating_add(count)
                            .saturating_add(pointer.saturating_mul(count))
                            .saturating_add(element_alignment.saturating_sub(1))
                            .saturating_add(pointer.saturating_sub(1));
                    }
                } else {
                    self.fixed_bound_known = false;
                }
            }
            TypeDefinition::GrowingSequence { .. }
            | TypeDefinition::KeyedCollection { .. }
            | TypeDefinition::GrowingString => {
                let region = RegionId(self.regions.len() as u32);
                let destination = self
                    .assignments
                    .iter()
                    .find(|assignment| assignment.reservation == reservation)
                    .map(|assignment| assignment.destination)
                    .unwrap();
                let retained_until = self
                    .input
                    .checked_flow
                    .semantics
                    .physical_requirements
                    .iter()
                    .filter_map(|requirement| {
                        (requirement.destination == destination)
                            .then(|| match requirement.kind {
                                PhysicalPlacementRequirementKind::RetainUntilCompletion(
                                    capability,
                                ) => Some(capability),
                                _ => None,
                            })
                            .flatten()
                    })
                    .collect();
                let (stack, size, class) = self.region_placement(scope, value);
                self.regions.push(RegionPlan {
                    id: region,
                    stack,
                    class,
                    size,
                    owner: scope,
                    retained_until,
                });
                self.reservations[reservation.0 as usize].region = Some(region);
                self.reservations[reservation.0 as usize].retained_until =
                    self.regions[region.0 as usize].retained_until.clone();
                self.backings.push(BackingStoragePlan {
                    owner: value,
                    kind: BackingStorageKind::GrowingRegion { region },
                });
            }
            _ => {}
        }
    }

    fn realize_requirements(&mut self) {
        let requirements = self
            .input
            .checked_flow
            .semantics
            .physical_requirements
            .clone();
        for requirement in requirements {
            let Some(assignment) = self
                .assignments
                .iter()
                .find(|assignment| assignment.destination == requirement.destination)
            else {
                self.missing
                    .push(MissingPlanInput::PhysicalRequirement(requirement.id));
                continue;
            };
            if !self.requirement_satisfied(&requirement, assignment) {
                self.diagnostics.push(PhysicalPlanningDiagnostic {
                    requirement: Some(requirement.id),
                    origin: requirement.origin,
                    conflicting_reservations: vec![assignment.reservation],
                });
                continue;
            }
            let premises = self
                .input
                .checked_flow
                .evidence
                .iter()
                .filter_map(|evidence| match evidence.facts {
                    EvidenceFacts::FinalDestination { destination }
                        if destination == requirement.destination =>
                    {
                        Some(evidence.id)
                    }
                    _ => None,
                })
                .collect();
            self.realization.push(PhysicalPlacementEvidence {
                requirement: requirement.id,
                destination: requirement.destination,
                reservation: assignment.reservation,
                semantic_premises: premises,
            });
        }
    }

    fn validate_capacities(&mut self) {
        let p = post_ast(&self.input.checked_flow);
        let Some(configuration) = p.contracts.memory_configuration.iter().find_map(|item| {
            if let MemoryConfiguration::DataStack(configuration) = item {
                Some(configuration.clone())
            } else {
                None
            }
        }) else {
            return;
        };
        if let BudgetRequest::Explicit(limit) = configuration.fixed_size {
            if self.fixed_bound_known && self.fixed_known_bytes > limit {
                self.diagnostics.push(PhysicalPlanningDiagnostic {
                    requirement: None,
                    origin: configuration.origin,
                    conflicting_reservations: self.reservations.iter().map(|r| r.id).collect(),
                });
            }
        }
        if let BudgetRequest::Explicit(limit) = configuration.region_stack_size {
            let known = self
                .regions
                .iter()
                .filter(|region| region.class.is_none())
                .try_fold(0u64, |total, region| match region.size {
                    MemoryBudget::Explicit(bytes) | MemoryBudget::Inferred(bytes) => {
                        total.checked_add(bytes)
                    }
                    MemoryBudget::PlatformDefault => None,
                });
            if known.is_some_and(|known| known > limit) {
                self.diagnostics.push(PhysicalPlanningDiagnostic {
                    requirement: None,
                    origin: configuration.origin,
                    conflicting_reservations: self
                        .reservations
                        .iter()
                        .filter(|reservation| reservation.region.is_some())
                        .map(|reservation| reservation.id)
                        .collect(),
                });
            }
        }
    }

    fn requirement_satisfied(
        &self,
        requirement: &PhysicalPlacementRequirement,
        assignment: &ReservationAssignment,
    ) -> bool {
        let reservation = &self.reservations[assignment.reservation.0 as usize];
        match requirement.kind {
            PhysicalPlacementRequirementKind::StorageMustSurvive(_) => true,
            PhysicalPlacementRequirementKind::PreserveAddress(address) => {
                let p = post_ast(&self.input.checked_flow);
                reservation.storage == p.objects.addresses[address.0 as usize].storage
            }
            PhysicalPlacementRequirementKind::ReserveBeforeScopeEntry(child) => matches!(
                assignment.issuer,
                ReservationIssuer::Parent { child: candidate, .. } if candidate == child
            ),
            PhysicalPlacementRequirementKind::CallerProvided { call } => matches!(
                assignment.issuer,
                ReservationIssuer::Caller { call: candidate, .. } if candidate == call
            ),
            PhysicalPlacementRequirementKind::PreserveSourcePool(storage) => {
                reservation.storage == storage && assignment.origin == storage
            }
            PhysicalPlacementRequirementKind::RetainUntilCompletion(capability) => {
                reservation.retained_until.contains(&capability)
            }
        }
    }

    fn cleanup_plan(&self) -> CleanupPlan {
        let p = post_ast(&self.input.checked_flow);
        let mut exits = vec![];
        for verified in &self.input.checked_flow.derived.cleanup {
            let mut actions = vec![];
            for step in &verified.steps {
                match step {
                    VerifiedDestructionStep::OwnedComponent {
                        parent,
                        position,
                        destructor,
                        ..
                    } => {
                        if let Some(value) = value_for_entity(p, parent) {
                            actions.push(CleanupAction::DestroyOwnedComponent {
                                value,
                                position: position.clone(),
                                destructor: *destructor,
                            });
                        }
                    }
                    VerifiedDestructionStep::Hook {
                        entity, destructor, ..
                    } => {
                        if let (Some(value), Some(definition)) = (
                            value_for_entity(p, entity),
                            p.contracts
                                .destructors
                                .iter()
                                .find(|item| item.id == *destructor),
                        ) {
                            actions.push(CleanupAction::InvokeUserDestructor {
                                value,
                                function: definition.hook,
                            });
                        }
                    }
                    VerifiedDestructionStep::EndLifetime { entity, .. } => {
                        if let EntityId::Address(address) = entity {
                            let definition = &p.objects.addresses[address.0 as usize];
                            if matches!(
                                p.types.entries[definition.ty.0 as usize].kind,
                                TypeDefinition::Allocation { .. }
                            ) {
                                actions.push(CleanupAction::ReleaseAllocation {
                                    address: *address,
                                    storage: definition.storage,
                                });
                            }
                        }
                    }
                }
            }
            let exit = &p.scopes.exits[verified.exit.0 as usize];
            let after = self
                .regions
                .iter()
                .filter(|region| region.owner == exit.scope)
                .flat_map(|region| region.retained_until.iter().copied())
                .collect::<Vec<_>>();
            if let Some(storage) = p
                .scopes
                .storage
                .iter()
                .find(|storage| storage.scope == exit.scope)
            {
                actions.push(CleanupAction::RewindCursor {
                    snapshot: storage.entry,
                    after: after.clone(),
                });
            }
            for region in self
                .regions
                .iter()
                .filter(|region| region.owner == exit.scope)
            {
                actions.push(CleanupAction::ReturnRegion {
                    region: region.id,
                    after: region.retained_until.clone(),
                });
            }
            for class in self
                .region_classes
                .iter()
                .filter(|class| class.declaring_scope == exit.scope)
            {
                let after = self
                    .regions
                    .iter()
                    .filter(|region| region.class == Some(class.id))
                    .flat_map(|region| region.retained_until.iter().copied())
                    .collect();
                actions.push(CleanupAction::RestoreRegionClass {
                    class: class.id,
                    after,
                });
            }
            exits.push(ExitCleanup {
                exit: verified.exit,
                actions,
            });
        }
        CleanupPlan { exits }
    }

    fn stack_plans(&self) -> Vec<DataStackPlan> {
        let p = post_ast(&self.input.checked_flow);
        let configuration = p
            .contracts
            .memory_configuration
            .iter()
            .find_map(|configuration| {
                if let MemoryConfiguration::DataStack(configuration) = configuration {
                    Some(configuration)
                } else {
                    None
                }
            });
        let fixed = configuration
            .map(|configuration| {
                budget(
                    &configuration.fixed_size,
                    self.fixed_bound_known.then_some(self.fixed_known_bytes),
                )
            })
            .unwrap_or_else(|| {
                inferred_or_default(self.fixed_bound_known.then_some(self.fixed_known_bytes))
            });
        let all_region_sizes = self
            .regions
            .iter()
            .filter(|region| region.class.is_none())
            .map(|region| match region.size {
                MemoryBudget::Explicit(bytes) | MemoryBudget::Inferred(bytes) => Some(bytes),
                MemoryBudget::PlatformDefault => None,
            })
            .collect::<Option<Vec<_>>>();
        let inferred_region_stack = all_region_sizes.map(|sizes| {
            sizes
                .into_iter()
                .fold(0u64, |total, bytes| total.saturating_add(bytes))
        });
        let regional = configuration
            .map(|configuration| budget(&configuration.region_stack_size, inferred_region_stack))
            .unwrap_or_else(|| inferred_or_default(inferred_region_stack));
        let mut plans = p
            .datastacks
            .iter()
            .map(|stack| DataStackPlan {
                id: stack.id,
                kind: stack.kind.clone(),
                capacity: match stack.kind {
                    DataStackKind::FixedValues => fixed.clone(),
                    DataStackKind::GrowingRegions => regional.clone(),
                },
            })
            .collect::<Vec<_>>();
        for (stack, scope) in &self.dedicated_region_stacks {
            let class = self
                .region_classes
                .iter()
                .find(|class| class.stack == *stack && class.declaring_scope == *scope)
                .unwrap();
            let used = self
                .regions
                .iter()
                .filter(|region| region.stack == *stack)
                .count() as u64;
            let slots = class.reserved_slots.unwrap_or(used.max(1));
            plans.push(DataStackPlan {
                id: *stack,
                kind: DataStackKind::GrowingRegions,
                capacity: MemoryBudget::Explicit(class.maximum_bytes.saturating_mul(slots)),
            });
        }
        plans
    }

    fn region_placement(
        &mut self,
        scope: ScopeId,
        value: ValueId,
    ) -> (DataStackId, MemoryBudget, Option<RegionClassId>) {
        if let Some(configuration) = self.local_region_configuration(scope).cloned() {
            let class = self.region_class(&configuration);
            return (
                self.region_classes[class.0 as usize].stack,
                MemoryBudget::Explicit(configuration.maximum_bytes),
                Some(class),
            );
        }
        (self.region_stack(), self.global_region_budget(value), None)
    }

    fn local_region_configuration(&self, scope: ScopeId) -> Option<&RegionConfiguration> {
        let p = post_ast(&self.input.checked_flow);
        let mut current = Some(scope);
        while let Some(scope) = current {
            if let Some(configuration) = p.contracts.memory_configuration.iter().find_map(|item| {
                if let MemoryConfiguration::Region(region) = item {
                    (region.scope == scope).then_some(region)
                } else {
                    None
                }
            }) {
                return Some(configuration);
            }
            current = p.scopes.entries[scope.0 as usize].lexical_parent;
        }
        None
    }

    fn region_class(&mut self, configuration: &RegionConfiguration) -> RegionClassId {
        for class in self
            .region_classes
            .iter()
            .filter(|class| class.declaring_scope == configuration.scope)
        {
            let occupied = self
                .regions
                .iter()
                .filter(|region| region.class == Some(class.id))
                .count() as u64;
            if class
                .reserved_slots
                .is_none_or(|reserved| occupied < reserved)
            {
                return class.id;
            }
        }
        let p = post_ast(&self.input.checked_flow);
        let stack =
            DataStackId(p.datastacks.len() as u32 + self.dedicated_region_stacks.len() as u32);
        self.dedicated_region_stacks
            .push((stack, configuration.scope));
        let id = RegionClassId(self.region_classes.len() as u32);
        self.region_classes.push(RegionClassPlan {
            id,
            declaring_scope: configuration.scope,
            entered_at: scope_entry_moment(p, configuration.scope),
            stack,
            maximum_bytes: configuration.maximum_bytes,
            reserved_slots: configuration.count,
        });
        id
    }

    fn global_region_budget(&self, value: ValueId) -> MemoryBudget {
        let p = post_ast(&self.input.checked_flow);
        if let Some(bytes) = collection_maximum(p, value) {
            return MemoryBudget::Inferred(bytes);
        }
        if let Some(configuration) = p.contracts.memory_configuration.iter().find_map(|item| {
            if let MemoryConfiguration::DataStack(configuration) = item {
                Some(configuration)
            } else {
                None
            }
        }) {
            return budget(&configuration.region_size, None);
        }
        MemoryBudget::PlatformDefault
    }

    fn construction(&self, requirement: DestinationRequirementId) -> ExecutionMomentId {
        self.input
            .checked_flow
            .semantics
            .semantics
            .destinations
            .finals
            .iter()
            .find(|candidate| candidate.id == requirement)
            .map(|candidate| candidate.construction)
            .unwrap()
    }

    fn initialization(
        &self,
        value: ValueId,
        destination_construction: ExecutionMomentId,
    ) -> ExecutionMomentId {
        match post_ast(&self.input.checked_flow).values.entries[value.0 as usize].definition {
            ValueDefinition::OperationResult { produced_at, .. }
            | ValueDefinition::ConditionalResult { produced_at, .. } => produced_at,
            ValueDefinition::Parameter(_)
            | ValueDefinition::CaptureField { .. }
            | ValueDefinition::Constant(_)
            | ValueDefinition::ConfiguredConstant { .. }
            | ValueDefinition::Diverged { .. } => destination_construction,
        }
    }

    fn issuer(
        &self,
        final_: &LogicalFinalDestination,
        destination_scope: ScopeId,
        initialization: ExecutionMomentId,
        origin: StorageOriginId,
    ) -> (ExecutionMomentId, ReservationIssuer) {
        let requirements = &self.input.checked_flow.semantics.physical_requirements;
        if let Some((child, at)) = requirements.iter().find_map(|requirement| {
            if requirement.destination != final_.id {
                return None;
            }
            if let PhysicalPlacementRequirementKind::ReserveBeforeScopeEntry(child) =
                requirement.kind
            {
                let p = post_ast(&self.input.checked_flow);
                let at = p
                    .scopes
                    .storage
                    .iter()
                    .find(|storage| storage.scope == child)
                    .map(|storage| p.cursor_snapshots[storage.entry.0 as usize].moment)?;
                Some((child, at))
            } else {
                None
            }
        }) {
            return (
                at,
                ReservationIssuer::Parent {
                    scope: destination_scope,
                    child,
                },
            );
        }
        if let Some((call, callee)) = requirements.iter().find_map(|requirement| {
            if requirement.destination != final_.id {
                return None;
            }
            if let PhysicalPlacementRequirementKind::CallerProvided { call } = requirement.kind {
                let p = post_ast(&self.input.checked_flow);
                let callee = operation_callee(p, call)?;
                Some((call, callee))
            } else {
                None
            }
        }) {
            return (
                initialization,
                ReservationIssuer::Caller {
                    scope: destination_scope,
                    call,
                    callee,
                },
            );
        }
        (
            initialization,
            ReservationIssuer::ExistingStorage { origin },
        )
    }

    fn address_and_origin(
        &self,
        value: ValueId,
        guard: PredicateId,
    ) -> Option<(AddressId, StorageOriginId)> {
        let p = post_ast(&self.input.checked_flow);
        let address = p
            .objects
            .value_entities
            .iter()
            .find_map(|identity| {
                (identity.value == value
                    && (identity.guard == guard || identity.guard == PredicateId(0)))
                .then_some(&identity.entity)
                .and_then(|entity| match entity {
                    EntityId::Address(address) => Some(*address),
                    _ => None,
                })
            })
            .or_else(|| {
                p.objects.value_entities.iter().find_map(|identity| {
                    (identity.value == value)
                        .then_some(&identity.entity)
                        .and_then(|entity| match entity {
                            EntityId::Address(address) => Some(*address),
                            _ => None,
                        })
                })
            })?;
        Some((address, p.objects.addresses[address.0 as usize].storage))
    }

    fn scope_body(&self, mut scope: ScopeId) -> BodyId {
        let p = post_ast(&self.input.checked_flow);
        loop {
            let entry = &p.scopes.entries[scope.0 as usize];
            if matches!(entry.entry, ScopeEntry::BodyRoot { .. }) {
                return match entry.context {
                    ScopeContext::Body(body) | ScopeContext::Unreachable { body, .. } => body,
                    _ => panic!("runtime body root must identify its body"),
                };
            }
            scope = entry
                .lexical_parent
                .expect("runtime child scope must have a body root");
        }
    }

    fn body_cursor(&self, scope: ScopeId) -> CursorExpressionId {
        self.body_cursors[&self.scope_body(scope)]
    }

    fn advance_body_cursor(&mut self, scope: ScopeId, cursor: CursorExpressionId) {
        let body = self.scope_body(scope);
        self.body_cursors.insert(body, cursor);
        self.scope_cursors.insert(scope, cursor);
    }

    fn begin_physical_scope(&mut self, scope: ScopeId) {
        if !self.physical_scope_started.insert(scope) {
            return;
        }
        let cursor = self.body_cursor(scope);
        self.scope_cursors.insert(scope, cursor);
        if let Some(entry) = self
            .scope_entries
            .iter_mut()
            .find(|entry| entry.scope == scope)
        {
            entry.cursor = cursor;
        }
    }

    fn cursor(&mut self, kind: CursorExpressionKind) -> CursorExpressionId {
        let id = CursorExpressionId(self.cursors.len() as u32);
        self.cursors.push(CursorExpression { id, kind });
        id
    }

    fn fixed_stack(&self) -> DataStackId {
        post_ast(&self.input.checked_flow)
            .datastacks
            .iter()
            .find(|stack| matches!(stack.kind, DataStackKind::FixedValues))
            .unwrap()
            .id
    }

    fn region_stack(&self) -> DataStackId {
        post_ast(&self.input.checked_flow)
            .datastacks
            .iter()
            .find(|stack| matches!(stack.kind, DataStackKind::GrowingRegions))
            .unwrap()
            .id
    }

    fn physical_proof(&mut self, fact: PhysicalPlanningFact) -> PhysicalPlanningProofId {
        let id = PhysicalPlanningProofId(self.physical_proofs.len() as u32);
        self.physical_proofs
            .push(PhysicalPlanningProof { id, fact });
        id
    }
}

fn scope_entry_moment(p: &PostAst, scope: ScopeId) -> ExecutionMomentId {
    match p.scopes.entries[scope.0 as usize].entry {
        ScopeEntry::Unreachable { after, .. } => after,
        ScopeEntry::BodyRoot { execution, .. } => execution,
        ScopeEntry::Child { entry, .. } => entry,
        ScopeEntry::DeclarationRoot { .. } => {
            panic!("declaration scope cannot own a runtime region class")
        }
    }
}

fn budget(request: &BudgetRequest, inferred: Option<u64>) -> MemoryBudget {
    match request {
        BudgetRequest::Explicit(bytes) => MemoryBudget::Explicit(*bytes),
        BudgetRequest::InferThenDefault => inferred_or_default(inferred),
    }
}

fn inferred_or_default(inferred: Option<u64>) -> MemoryBudget {
    inferred
        .map(MemoryBudget::Inferred)
        .unwrap_or(MemoryBudget::PlatformDefault)
}

fn missing_key(missing: &MissingPlanInput) -> (u8, u32) {
    match missing {
        MissingPlanInput::TypeLayout(id) => (0, id.0),
        MissingPlanInput::PhysicalRequirement(id) => (1, id.0),
        MissingPlanInput::RuntimeBinding(id) => (2, id.0),
    }
}

fn collection_maximum(p: &PostAst, value: ValueId) -> Option<u64> {
    let address = p.objects.value_entities.iter().find_map(|identity| {
        (identity.value == value)
            .then(|| match identity.entity {
                EntityId::Address(address) => Some(address),
                _ => None,
            })
            .flatten()
    })?;
    let collection = p.objects.collections.iter().find(|collection| {
        matches!(collection.descriptor, CollectionDescriptor::Address(candidate) if candidate == address)
    })?;
    collection
        .constraints
        .iter()
        .find_map(|constraint| match constraint {
            CollectionConstraint::MaximumBytes(value) => constant_u64(p, *value),
            _ => None,
        })
}

fn constant_u64(p: &PostAst, value: ValueId) -> Option<u64> {
    let value = &p.values.entries[value.0 as usize];
    let constant = match value.definition {
        ValueDefinition::Constant(id) => p.declarations.constants[id.0 as usize].value.clone(),
        ValueDefinition::ConfiguredConstant { ref value, .. } => value.clone(),
        _ => return None,
    };
    match constant {
        ConstantValue::Integer(value) if value >= 0 => u64::try_from(value).ok(),
        ConstantValue::Unsigned(value) => u64::try_from(value).ok(),
        _ => None,
    }
}

fn value_for_entity(p: &PostAst, entity: &EntityId) -> Option<ValueId> {
    p.objects
        .value_entities
        .iter()
        .find(|identity| &identity.entity == entity)
        .map(|identity| identity.value)
}

fn operation_callee(p: &PostAst, operation: OperationId) -> Option<FunctionInstanceId> {
    p.bodies
        .iter()
        .flat_map(|body| &body.operations)
        .find_map(|candidate| {
            if candidate.site().id != operation {
                return None;
            }
            match candidate {
                Operation::DirectCall(call) => Some(call.target),
                Operation::MethodCall(call) => match call.target.target {
                    MethodTarget::Concrete(instance) => Some(instance),
                    MethodTarget::ContractAlternatives(_)
                    | MethodTarget::ContractRequirement { .. } => None,
                },
                _ => None,
            }
        })
}

fn same_scope(first: &LogicalScope, second: &LogicalScope) -> bool {
    match (first, second) {
        (LogicalScope::Local(a), LogicalScope::Local(b)) => a == b,
        (LogicalScope::ExecutionBranch(a), LogicalScope::ExecutionBranch(b)) => a == b,
        (LogicalScope::BorrowedTarget(a), LogicalScope::BorrowedTarget(b)) => a == b,
        (LogicalScope::CallerResult(a), LogicalScope::CallerResult(b)) => a == b,
        _ => false,
    }
}

fn same_cleanup(first: &LogicalCleanupSite, second: &LogicalCleanupSite) -> bool {
    match (first, second) {
        (LogicalCleanupSite::ExecutionBranchEnd(a), LogicalCleanupSite::ExecutionBranchEnd(b)) => {
            a == b
        }
        (LogicalCleanupSite::BorrowedTarget(a), LogicalCleanupSite::BorrowedTarget(b)) => a == b,
        (LogicalCleanupSite::NoReachableExit(a), LogicalCleanupSite::NoReachableExit(b)) => a == b,
        (LogicalCleanupSite::Exit(a), LogicalCleanupSite::Exit(b)) => a == b,
        (LogicalCleanupSite::CallerResult(a), LogicalCleanupSite::CallerResult(b)) => a == b,
        _ => false,
    }
}

fn same_owner(first: &Owner, second: &Owner) -> bool {
    match (first, second) {
        (
            Owner::ExecutionBranch {
                branch: a,
                instance: ai,
            },
            Owner::ExecutionBranch {
                branch: b,
                instance: bi,
            },
        ) => a == b && ai == bi,
        (
            Owner::BorrowedTarget {
                place: a,
                instance: ai,
            },
            Owner::BorrowedTarget {
                place: b,
                instance: bi,
            },
        ) => a == b && ai == bi,
        (
            Owner::FunctionResult {
                function: a,
                instance: ai,
            },
            Owner::FunctionResult {
                function: b,
                instance: bi,
            },
        ) => a == b && ai == bi,
        (
            Owner::Binding {
                binding: a,
                instance: ai,
            },
            Owner::Binding {
                binding: b,
                instance: bi,
            },
        ) => a == b && ai == bi,
        (Owner::Entity(a), Owner::Entity(b)) => a.entity == b.entity && a.instance == b.instance,
        (
            Owner::Scope {
                scope: a,
                instance: ai,
            },
            Owner::Scope {
                scope: b,
                instance: bi,
            },
        ) => a == b && ai == bi,
        _ => false,
    }
}

fn guards_exclusive(p: &PostAst, first: PredicateId, second: PredicateId) -> bool {
    if predicate_is_not(p, first, second) || predicate_is_not(p, second, first) {
        return true;
    }
    let first_booleans = conjunctive_booleans(p, first);
    let second_booleans = conjunctive_booleans(p, second);
    if first_booleans.iter().any(|(value, expected)| {
        second_booleans
            .iter()
            .any(|(other, other_expected)| value == other && expected != other_expected)
    }) {
        return true;
    }
    let first_terms = predicate_terms(p, first);
    let second_terms = predicate_terms(p, second);
    first_terms.iter().any(|a| {
        second_terms
            .iter()
            .any(|b| predicate_is_not(p, *a, *b) || predicate_is_not(p, *b, *a))
    })
}

/// Return boolean facts that must all hold for this guard. A multi-arm `Any`
/// cannot be reduced to a conjunction and therefore produces no claim.
fn conjunctive_booleans(p: &PostAst, predicate: PredicateId) -> Vec<(ValueId, bool)> {
    match &p.execution.predicates[predicate.0 as usize].kind {
        PredicateKind::Always => vec![],
        PredicateKind::Boolean { value, expected } => vec![(*value, *expected)],
        PredicateKind::All(terms) => {
            let mut output = vec![];
            for term in terms {
                output.extend(conjunctive_booleans(p, *term));
            }
            output
        }
        PredicateKind::Any(terms) if terms.len() == 1 => conjunctive_booleans(p, terms[0]),
        PredicateKind::Not(inner) => match &p.execution.predicates[inner.0 as usize].kind {
            PredicateKind::Boolean { value, expected } => vec![(*value, !*expected)],
            _ => vec![],
        },
        _ => vec![],
    }
}

fn predicate_is_not(p: &PostAst, candidate: PredicateId, target: PredicateId) -> bool {
    matches!(
        p.execution.predicates[candidate.0 as usize].kind,
        PredicateKind::Not(inner) if inner == target
    )
}

fn predicate_terms(p: &PostAst, predicate: PredicateId) -> Vec<PredicateId> {
    match &p.execution.predicates[predicate.0 as usize].kind {
        PredicateKind::All(terms) => terms.clone(),
        _ => vec![predicate],
    }
}
