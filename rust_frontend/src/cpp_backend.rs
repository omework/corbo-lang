//! C++ generation from the verified PostAST and its physical memory plan.
//!
//! `translate` builds a typed C++ IR from `PlannedPostAst`; `emit` only renders
//! that IR. No AST, token or source-text access is permitted in this module.

use crate::{cpp_backend_inventory as inventory, cpp_ir, memory_plan, post_ast::*};
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct CppTranslationUnit {
    pub ir: cpp_ir::TranslationUnit,
    pub source: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CppBackendError {
    InvalidMemoryPlan(String),
    MissingEntryPoint,
    MissingFunctionBody(FunctionInstanceId),
    MissingLayout(TypeId),
    RuntimeSizedLayout(TypeId),
    MissingResultLayout(FunctionInstanceId),
    MissingFieldLayout {
        ty: TypeId,
        field: FieldId,
    },
    MissingPredicateRepresentation(PredicateId),
    MissingConstantRepresentation(ValueId),
    MissingPlaceRepresentation(PlaceId),
    MissingPositionRepresentation {
        ty: TypeId,
        position: PositionSelector,
    },
    MissingOperationRepresentation {
        operation: OperationId,
        representation: &'static str,
    },
    UnlowerableConcreteRepresentation {
        operation: Option<OperationId>,
        representation: &'static str,
    },
    UnsupportedExternalType(TypeId),
}

pub fn emit(program: &PlannedPostAst) -> Result<CppTranslationUnit, Vec<CppBackendError>> {
    let ir = translate(program)?;
    let source = cpp_ir::render(&ir);
    Ok(CppTranslationUnit { ir, source })
}

pub fn translate(
    program: &PlannedPostAst,
) -> Result<cpp_ir::TranslationUnit, Vec<CppBackendError>> {
    Backend::new(program).translate()
}

struct Backend<'a> {
    planned: &'a PlannedPostAst,
    post: &'a PostAst,
    layouts: HashMap<TypeId, &'a TypeLayout>,
    errors: Vec<CppBackendError>,
    current_async: Option<BodyId>,
    cleanup_emission: u64,
}

impl<'a> Backend<'a> {
    fn new(planned: &'a PlannedPostAst) -> Self {
        let post = &planned.checked_flow.semantics.semantics.post_ast;
        let layouts = planned
            .layouts
            .layouts
            .iter()
            .map(|layout| (layout.ty, layout))
            .collect();
        Self {
            planned,
            post,
            layouts,
            errors: Vec::new(),
            current_async: None,
            cleanup_emission: 0,
        }
    }

    fn translate(mut self) -> Result<cpp_ir::TranslationUnit, Vec<CppBackendError>> {
        if let Err(errors) = memory_plan::validate(self.planned) {
            self.errors.extend(
                errors
                    .into_iter()
                    .map(|error| CppBackendError::InvalidMemoryPlan(error.0)),
            );
        }
        let Some(entry) = self.post.entry_point else {
            self.errors.push(CppBackendError::MissingEntryPoint);
            return Err(self.errors);
        };
        self.audit_representation_inventory();

        let mut generated = Vec::new();
        generated.extend(self.runtime_helpers());
        generated.extend(self.type_representations());
        generated.extend(self.function_declarations());
        generated.extend(self.destructor_declarations());
        generated.extend(self.launch_adapters());
        generated.extend(self.function_definitions());
        generated.extend(self.destructor_definitions());

        let mut declarations = self.foreign_headers();
        declarations.extend(self.external_declarations());
        declarations.push(cpp_ir::Declaration::Namespace(cpp_ir::Namespace {
            name: "corbo_generated".to_owned(),
            declarations: generated,
        }));
        if let Some(main) = self.entry_definition(entry) {
            declarations.push(cpp_ir::Declaration::Function(main));
        }
        if !self.errors.is_empty() {
            return Err(self.errors);
        }
        Ok(cpp_ir::TranslationUnit {
            includes: vec![
                cpp_ir::Include::System("bit"),
                cpp_ir::Include::System("cstddef"),
                cpp_ir::Include::System("cstdint"),
                cpp_ir::Include::System("cstring"),
                cpp_ir::Include::System("cmath"),
                cpp_ir::Include::System("limits"),
                cpp_ir::Include::System("type_traits"),
                cpp_ir::Include::System("utility"),
                cpp_ir::Include::Local("corbo_runtime.hpp".to_owned()),
            ],
            declarations,
        })
    }

    /// Audit the complete semantic/physical handoff before emitting code.
    ///
    /// The exhaustive matches live in `cpp_backend_inventory`; this traversal
    /// proves that every representation present in this concrete program has
    /// been classified and that abstract-only forms do not leak into C++.
    fn audit_representation_inventory(&mut self) {
        inventory::planned_handoff(self.planned);
        for ty in &self.post.types.entries {
            let _ = inventory::ty(&ty.kind);
            if let TypeDefinition::Numeric(numeric) = &ty.kind {
                let _ = inventory::numeric(*numeric);
            }
        }
        for constant in &self.post.declarations.constants {
            let _ = inventory::constant(&constant.value);
        }
        for place in &self.post.objects.places {
            let _ = inventory::place_root(&place.root);
            for projection in &place.projections {
                let _ = inventory::place_projection(projection);
            }
        }
        for moment in &self.post.execution.execution_moments {
            let _ = inventory::execution_phase(&moment.phase);
        }
        for instance in &self.post.declarations.instances {
            let _ = inventory::instance_resolution(&instance.resolution);
        }
        for default in &self.post.declarations.defaults {
            let _ = inventory::default_initialization(&default.kind);
        }
        for equality in &self.post.contracts.equality {
            let _ = inventory::equality(&equality.kind);
        }
        for transfer in &self.post.transfers {
            let _ = inventory::transfer(&transfer.mode);
        }
        for predicate in &self.post.execution.predicates {
            let _ = inventory::predicate(&predicate.kind);
        }
        for edge in &self.post.execution.edges {
            let _ = inventory::execution_edge(edge);
        }
        for check in &self.post.runtime_checks {
            let _ = inventory::runtime_check(check);
        }
        for layout in &self.planned.layouts.layouts {
            let size = inventory::layout_size(&layout.size);
            if size.coverage == inventory::Coverage::AbstractOnly {
                self.errors
                    .push(CppBackendError::UnlowerableConcreteRepresentation {
                        operation: None,
                        representation: size.name,
                    });
            }
            if let Some(native) = &layout.native {
                let _ = inventory::native_layout(native);
            }
        }
        for value in &self.planned.storage.values {
            for alternative in
                std::iter::once(&value.alternatives.first).chain(&value.alternatives.rest)
            {
                let _ = inventory::value_storage(&alternative.kind);
                if let ValueStorageKind::None(absence) = &alternative.kind {
                    let _ = inventory::storage_absence(absence);
                }
            }
        }
        for origin in &self.post.storage_origins {
            let _ = inventory::storage_creation(&origin.creation);
        }
        for stack in &self.planned.storage.stacks {
            let _ = inventory::stack_kind(&stack.kind);
            let _ = inventory::memory_budget(&stack.capacity);
        }
        for region in &self.planned.storage.regions {
            let _ = inventory::memory_budget(&region.size);
        }
        for backing in &self.planned.storage.backings {
            let _ = inventory::backing(&backing.kind);
        }
        for cursor in &self.planned.storage.cursors {
            let _ = inventory::cursor(&cursor.kind);
        }
        for exit in &self.planned.cleanup.exits {
            for action in &exit.actions {
                let _ = inventory::cleanup(action);
            }
        }
        for region in &self.planned.foreign.regions {
            for fragment in &region.fragments {
                let _ = inventory::foreign_fragment(fragment);
            }
        }
        for body in &self.post.bodies {
            let _ = inventory::body_owner(&body.owner);
            let concrete = match body.owner {
                BodyOwner::Declaration(_) => false,
                BodyOwner::Instance(instance) => matches!(
                    self.post.declarations.instances[instance.0 as usize].resolution,
                    InstanceResolution::Concrete
                ),
            };
            for operation in &body.operations {
                let entry = inventory::operation(operation);
                if concrete && entry.coverage == inventory::Coverage::AbstractOnly {
                    self.errors
                        .push(CppBackendError::UnlowerableConcreteRepresentation {
                            operation: Some(operation.site().id),
                            representation: entry.name,
                        });
                }
                match operation {
                    Operation::NativeOperation(native) => {
                        let _ = inventory::native_operation(&native.kind);
                        if let NativeOperationKind::Primitive(primitive) = &native.kind {
                            let _ = inventory::primitive(primitive);
                            if let PrimitiveOperation::Runtime { kind, .. } = primitive {
                                let _ = inventory::runtime_primitive(kind);
                            }
                        }
                        if let NativeOperationKind::RuntimeLaunch { kind, .. } = &native.kind {
                            let _ = inventory::runtime_launch(kind);
                        }
                        if let NativeOperationKind::Collection {
                            operation,
                            position: Some(position),
                            ..
                        } = &native.kind
                        {
                            let _ = inventory::collection_operation(operation);
                            let _ = inventory::position(position);
                        } else if let NativeOperationKind::Collection { operation, .. } =
                            &native.kind
                        {
                            let _ = inventory::collection_operation(operation);
                        }
                    }
                    Operation::ForControl(control) => {
                        let _ = inventory::iteration(&control.iteration);
                    }
                    Operation::AwaitValue(awaited) => {
                        let protocol = inventory::await_protocol(&awaited.protocol.protocol);
                        if concrete
                            && protocol.coverage == inventory::Coverage::AbstractOnly
                            && !matches!(
                                awaited.protocol.protocol,
                                AwaitProtocol::ContractMethod {
                                    target: MethodTarget::Concrete(_),
                                    ..
                                }
                            )
                        {
                            self.errors
                                .push(CppBackendError::UnlowerableConcreteRepresentation {
                                    operation: Some(awaited.site.id),
                                    representation: protocol.name,
                                });
                        }
                    }
                    Operation::IndexPlace(index) => {
                        let _ = inventory::index_access(&index.access);
                        if concrete && matches!(index.access, ResolvedIndexAccess::Intrinsic { .. })
                        {
                            self.errors
                                .push(CppBackendError::UnlowerableConcreteRepresentation {
                                    operation: Some(index.site.id),
                                    representation: "IntrinsicIndexAccess",
                                });
                        }
                    }
                    Operation::SliceView(slice) => {
                        let _ = inventory::slice_access(&slice.access);
                        if concrete && matches!(slice.access, ResolvedSliceAccess::Intrinsic { .. })
                        {
                            self.errors
                                .push(CppBackendError::UnlowerableConcreteRepresentation {
                                    operation: Some(slice.site.id),
                                    representation: "IntrinsicSliceAccess",
                                });
                        }
                    }
                    Operation::RuntimeCheckOperation(check) => {
                        let _ = inventory::failure(&check.failure);
                    }
                    Operation::Dereference(value) => {
                        let _ = inventory::dereference(&value.access);
                    }
                    Operation::RepeatArray(value) => {
                        let replication = inventory::replication(&value.replication.strategy);
                        if concrete && replication.coverage == inventory::Coverage::AbstractOnly {
                            self.errors
                                .push(CppBackendError::UnlowerableConcreteRepresentation {
                                    operation: Some(value.site.id),
                                    representation: replication.name,
                                });
                        }
                    }
                    Operation::PropagateResult(value) => {
                        let _ = inventory::error_conversion(&value.conversion);
                    }
                    Operation::PatternMatches(value) => {
                        let _ = inventory::pattern_test(&value.test);
                    }
                    Operation::InitializeDefault(value) if concrete => {
                        if self.default_plan_requires_runtime_binding(value.plan) {
                            self.errors
                                .push(CppBackendError::UnlowerableConcreteRepresentation {
                                    operation: Some(value.site.id),
                                    representation: "IntrinsicDefaultInitialization",
                                });
                        }
                    }
                    Operation::ForeignC(foreign) => {
                        let _ = inventory::foreign_effects(&foreign.effects);
                        for operand in &foreign.operands {
                            let _ = inventory::foreign_operand(&operand.mode);
                        }
                    }
                    Operation::ForeignCpp(foreign) => {
                        let _ = inventory::foreign_effects(&foreign.effects);
                        for operand in &foreign.operands {
                            let _ = inventory::foreign_operand(&operand.mode);
                        }
                    }
                    Operation::ForeignAssembly(foreign) => {
                        let _ = inventory::foreign_effects(&foreign.effects);
                        for operand in &foreign.operands {
                            let _ = inventory::foreign_operand(&operand.mode);
                        }
                    }
                    _ => {}
                }
            }
        }
    }

    fn default_plan_requires_runtime_binding(&self, plan: DefaultPlanId) -> bool {
        match &self.post.declarations.defaults[plan.0 as usize].kind {
            DefaultInitializationKind::Intrinsic(_) => true,
            DefaultInitializationKind::Struct(fields)
            | DefaultInitializationKind::Variant { fields, .. } => fields
                .iter()
                .any(|field| self.default_plan_requires_runtime_binding(field.plan)),
            DefaultInitializationKind::Tuple(elements) => elements
                .iter()
                .any(|element| self.default_plan_requires_runtime_binding(*element)),
            DefaultInitializationKind::Array { element, .. } => {
                self.default_plan_requires_runtime_binding(*element)
            }
            DefaultInitializationKind::EmptyNative | DefaultInitializationKind::Constant(_) => {
                false
            }
        }
    }

    fn foreign_headers(&self) -> Vec<cpp_ir::Declaration> {
        let mut headers = self
            .planned
            .foreign
            .regions
            .iter()
            .flat_map(|region| region.headers.iter().cloned())
            .collect::<Vec<_>>();
        headers.sort();
        headers.dedup();
        headers
            .into_iter()
            .map(|header| {
                let directive = if header.starts_with('<') || header.starts_with('"') {
                    format!("#include {header}")
                } else {
                    format!("#include <{header}>")
                };
                cpp_ir::Declaration::Verbatim(directive)
            })
            .collect()
    }

    fn external_declarations(&mut self) -> Vec<cpp_ir::Declaration> {
        let mut definitions = self
            .post
            .declarations
            .functions
            .iter()
            .filter(|function| matches!(function.body, FunctionImplementation::External { .. }))
            .collect::<Vec<_>>();
        definitions.sort_by_key(|function| function.id.0);
        definitions
            .into_iter()
            .filter_map(|function| {
                let signature = &self.post.declarations.signatures[function.signature.0 as usize];
                let Some(result) = external_type_spelling(
                    &self.post.types.entries[signature.result.0 as usize].kind,
                ) else {
                    self.errors
                        .push(CppBackendError::UnsupportedExternalType(signature.result));
                    return None;
                };
                let mut parameters = Vec::new();
                for parameter in &signature.parameters {
                    let Some(spelling) = external_type_spelling(
                        &self.post.types.entries[parameter.ty.0 as usize].kind,
                    ) else {
                        self.errors
                            .push(CppBackendError::UnsupportedExternalType(parameter.ty));
                        return None;
                    };
                    parameters.push(spelling);
                }
                let symbol = &self.post.symbols.entries[function.symbol.0 as usize].spelling;
                Some(cpp_ir::Declaration::Verbatim(format!(
                    "extern \"C\" {result} {symbol}({});",
                    parameters.join(", ")
                )))
            })
            .collect()
    }

    fn runtime_helpers(&self) -> Vec<cpp_ir::Declaration> {
        let representation = r#"static inline std::size_t corbo_align_size(std::size_t value, std::size_t alignment) {
    const std::size_t mask = alignment - 1;
    return (value + mask) & ~mask;
}
static inline std::size_t corbo_max_size(std::size_t left, std::size_t right) {
    return left > right ? left : right;
}
static inline void corbo_store_pointer(void* destination, void* pointer) {
    std::memcpy(destination, &pointer, sizeof(pointer));
}
static inline void* corbo_load_pointer(const void* source) {
    void* pointer = nullptr;
    std::memcpy(&pointer, source, sizeof(pointer));
    return pointer;
}
static inline std::uint64_t corbo_read_discriminant(const void* value, std::size_t bytes) {
    std::uint64_t result = 0;
    std::memcpy(&result, value, bytes);
    return result;
}
static inline void corbo_write_discriminant(void* value, std::size_t bytes, std::uint64_t discriminant) {
    std::memcpy(value, &discriminant, bytes);
}
struct corbo_generated_view { const std::uint8_t* data; std::size_t length; };
static inline bool corbo_valid_text_range(const void* raw, std::size_t start, std::size_t end) {
    const auto* view = reinterpret_cast<const corbo_generated_view*>(raw);
    if (start > end || end > view->length) return false;
    const bool start_boundary = start == view->length || (view->data[start] & 0xc0u) != 0x80u;
    const bool end_boundary = end == view->length || (view->data[end] & 0xc0u) != 0x80u;
    return start_boundary && end_boundary;
}
static inline bool corbo_valid_text_boundary(const void* raw, std::size_t boundary) {
    const auto* view = reinterpret_cast<const corbo_generated_view*>(raw);
    return boundary <= view->length && (boundary == view->length || (view->data[boundary] & 0xc0u) != 0x80u);
}
static inline bool corbo_task_await_value(void* raw, void* output, std::size_t bytes, corbo_context* context) {
    auto* child = reinterpret_cast<corbo_task_value*>(raw)->state;
    if (!corbo_task_await(child, context, &context->task->child_waiter)) return false;
    if (child->failed) corbo_fail("corbo: awaited task failed");
    if (bytes != 0) std::memcpy(output, child->result, bytes);
    return true;
}"#;
        let checks = r#"template <typename Target, typename Source>
static inline bool corbo_can_exact_numeric(Source source) {
    if constexpr (std::is_integral_v<Source> && std::is_integral_v<Target>) {
        if (!std::in_range<Target>(source)) return false;
    } else if constexpr (std::is_floating_point_v<Source>) {
        if (!std::isfinite(source)) return false;
        const long double value = static_cast<long double>(source);
        if (value < static_cast<long double>(std::numeric_limits<Target>::lowest()) || value > static_cast<long double>(std::numeric_limits<Target>::max())) return false;
    }
    const Target converted = static_cast<Target>(source);
    return static_cast<Source>(converted) == source;
}
template <typename Target, typename Source>
static inline bool corbo_exact_numeric(Source source, Target* output) {
    if (!corbo_can_exact_numeric<Target>(source)) return false;
    *output = static_cast<Target>(source);
    return true;
}
template <typename T> static inline bool corbo_add_valid(T a, T b) {
    if constexpr (std::is_unsigned_v<T>) return a <= std::numeric_limits<T>::max() - b;
    if (b > 0) return a <= std::numeric_limits<T>::max() - b;
    if (b < 0) return a >= std::numeric_limits<T>::lowest() - b;
    return true;
}
template <typename T> static inline bool corbo_sub_valid(T a, T b) {
    if constexpr (std::is_unsigned_v<T>) return a >= b;
    if (b > 0) return a >= std::numeric_limits<T>::lowest() + b;
    if (b < 0) return a <= std::numeric_limits<T>::max() + b;
    return true;
}
template <typename T> static inline bool corbo_mul_valid(T a, T b) {
    if (a == 0 || b == 0) return true;
    if constexpr (std::is_unsigned_v<T>) return a <= std::numeric_limits<T>::max() / b;
    if (a == T(-1)) return b != std::numeric_limits<T>::lowest();
    if (b == T(-1)) return a != std::numeric_limits<T>::lowest();
    if (a > 0) return b > 0 ? a <= std::numeric_limits<T>::max() / b : b >= std::numeric_limits<T>::lowest() / a;
    return b > 0 ? a >= std::numeric_limits<T>::lowest() / b : a >= std::numeric_limits<T>::max() / b;
}
template <typename T> static inline bool corbo_neg_valid(T value) {
    if constexpr (std::is_unsigned_v<T>) return value == 0;
    return value != std::numeric_limits<T>::lowest();
}
template <typename T> static inline bool corbo_div_valid(T left, T right) {
    return right != 0 && (!std::is_signed_v<T> || left != std::numeric_limits<T>::lowest() || right != T(-1));
}
static inline bool corbo_utf8_bytes_valid(const unsigned char* data, std::size_t length) {
    std::size_t at = 0;
    while (at < length) {
        const unsigned char first = data[at++];
        if (first < 0x80u) continue;
        std::size_t extra = first >= 0xc2u && first <= 0xdfu ? 1 : first >= 0xe0u && first <= 0xefu ? 2 : first >= 0xf0u && first <= 0xf4u ? 3 : 99;
        if (extra == 99 || extra > length - at) return false;
        if (extra >= 1 && (data[at] & 0xc0u) != 0x80u) return false;
        if (extra >= 2 && (data[at + 1] & 0xc0u) != 0x80u) return false;
        if (extra == 3 && (data[at + 2] & 0xc0u) != 0x80u) return false;
        if (extra >= 2 && ((first == 0xe0u && data[at] < 0xa0u) || (first == 0xedu && data[at] >= 0xa0u))) return false;
        if (extra == 3 && ((first == 0xf0u && data[at] < 0x90u) || (first == 0xf4u && data[at] >= 0x90u))) return false;
        at += extra;
    }
    return true;
}"#;
        vec![
            cpp_ir::Declaration::Verbatim(representation.to_owned()),
            cpp_ir::Declaration::Verbatim(checks.to_owned()),
        ]
    }

    /// Exhaustive type mapping. ABI size/alignment comes only from the plan.
    fn type_representations(&mut self) -> Vec<cpp_ir::Declaration> {
        let mut declarations = Vec::new();
        let planned_types = self
            .planned
            .layouts
            .layouts
            .iter()
            .map(|layout| layout.ty)
            .collect::<Vec<_>>();
        for ty in planned_types {
            let resolved = &self.post.types.entries[ty.0 as usize];
            let name = type_name(resolved.id);
            let declaration = match &resolved.kind {
                TypeDefinition::Numeric(number) => {
                    Some(cpp_ir::Declaration::TypeAlias(cpp_ir::TypeAlias {
                        name,
                        target: numeric_type(*number),
                    }))
                }
                TypeDefinition::Boolean => {
                    Some(cpp_ir::Declaration::TypeAlias(cpp_ir::TypeAlias {
                        name,
                        target: cpp_ir::Type::Bool,
                    }))
                }
                TypeDefinition::Never | TypeDefinition::Parameter(_) | TypeDefinition::StrData => {
                    None
                }
                TypeDefinition::ContractFuture { .. }
                | TypeDefinition::NumericConversionError
                | TypeDefinition::Unit
                | TypeDefinition::Utf8View
                | TypeDefinition::Nominal { .. }
                | TypeDefinition::Reference { .. }
                | TypeDefinition::Tuple(_)
                | TypeDefinition::Array { .. }
                | TypeDefinition::Slice { .. }
                | TypeDefinition::Callable(_)
                | TypeDefinition::Closure { .. }
                | TypeDefinition::Future { .. }
                | TypeDefinition::Allocation { .. }
                | TypeDefinition::GrowingSequence { .. }
                | TypeDefinition::KeyedCollection { .. }
                | TypeDefinition::GrowingString
                | TypeDefinition::InlineUtf8 { .. }
                | TypeDefinition::ExecutionHandle { .. }
                | TypeDefinition::Pool { .. } => self.layout_record(resolved.id),
            };
            if let Some(declaration) = declaration {
                declarations.push(declaration);
            }
        }
        declarations
    }

    fn layout_record(&mut self, ty: TypeId) -> Option<cpp_ir::Declaration> {
        let Some(layout) = self.layouts.get(&ty).copied() else {
            self.errors.push(CppBackendError::MissingLayout(ty));
            return None;
        };
        let LayoutSize::Fixed(size) = layout.size else {
            self.errors.push(CppBackendError::RuntimeSizedLayout(ty));
            return None;
        };
        Some(cpp_ir::Declaration::Record(cpp_ir::Record {
            name: type_name(ty),
            alignment: Some(layout.alignment),
            fields: vec![cpp_ir::Field {
                name: "storage".to_owned(),
                ty: cpp_ir::Type::Array {
                    element: Box::new(cpp_ir::Type::Unsigned { bits: 8 }),
                    length: size.max(1),
                },
                initializer: None,
            }],
        }))
    }

    fn function_declarations(&self) -> Vec<cpp_ir::Declaration> {
        let mut declarations = Vec::new();
        for instance in self.post.declarations.instances.iter().filter(|value| {
            value.body.is_some() && matches!(value.resolution, InstanceResolution::Concrete)
        }) {
            let body = instance.body.expect("filtered body");
            if self.async_frame(body).is_some() {
                declarations.push(cpp_ir::Declaration::Function(async_poll_shell(
                    instance.id,
                    None,
                )));
            } else {
                declarations.push(cpp_ir::Declaration::Function(function_shell(
                    instance.id,
                    None,
                )));
            }
        }
        declarations
    }

    fn launch_adapters(&self) -> Vec<cpp_ir::Declaration> {
        let mut declarations = Vec::new();
        for operation in self
            .post
            .bodies
            .iter()
            .filter(|body| self.concrete_body(body))
            .flat_map(|body| &body.operations)
        {
            let Operation::NativeOperation(native) = operation else {
                continue;
            };
            let NativeOperationKind::RuntimeLaunch { task, .. } = &native.kind else {
                continue;
            };
            let task_ty = self.post.values.entries[task.0 as usize].ty;
            let source = match self.post.types.entries[task_ty.0 as usize].kind {
                TypeDefinition::Closure { captures, .. } => {
                    let Some(target) = self.post.contracts.captures[captures.0 as usize].call
                    else {
                        continue;
                    };
                    format!("{}(output, arguments, state);", function_name(target))
                }
                TypeDefinition::Callable(_) => format!(
                    "void* function = corbo_load_pointer(state);\n    void* environment = corbo_load_pointer(reinterpret_cast<unsigned char*>(state) + sizeof(void*));\n    reinterpret_cast<void (*)(void*, void**, void*)>(function)(output, arguments, environment);"
                ),
                _ => continue,
            };
            declarations.push(cpp_ir::Declaration::Verbatim(format!(
                "static bool corbo_launch_poll_{}(void* state, void* output, corbo_context*) {{\n    void* arguments[1] = {{}};\n    {}\n    return true;\n}}",
                native.site.id.0,
                source,
            )));
        }
        declarations
    }

    fn function_definitions(&mut self) -> Vec<cpp_ir::Declaration> {
        let bodies = self.post.bodies.clone();
        let mut declarations = Vec::new();
        for body in bodies {
            let BodyOwner::Instance(instance) = body.owner else {
                continue;
            };
            if !matches!(
                self.post.declarations.instances[instance.0 as usize].resolution,
                InstanceResolution::Concrete
            ) {
                continue;
            }
            let is_async = self.async_frame(body.id).is_some();
            self.current_async = is_async.then_some(body.id);
            let mut function = self.function(instance, &body);
            if is_async {
                function.name = async_poll_name(instance);
                function.result = cpp_ir::Type::Bool;
                function.parameters = async_poll_shell(instance, None).parameters;
            }
            self.current_async = None;
            declarations.push(cpp_ir::Declaration::Function(function));
        }
        declarations
    }

    fn concrete_body(&self, body: &FunctionBody) -> bool {
        match body.owner {
            BodyOwner::Instance(instance) => matches!(
                self.post.declarations.instances[instance.0 as usize].resolution,
                InstanceResolution::Concrete
            ),
            BodyOwner::Declaration(_) => false,
        }
    }

    fn destructor_declarations(&self) -> Vec<cpp_ir::Declaration> {
        self.post
            .contracts
            .destructors
            .iter()
            .filter(|destructor| self.layouts.contains_key(&destructor.ty))
            .map(|destructor| {
                cpp_ir::Declaration::Function(cpp_ir::Function {
                    linkage: cpp_ir::Linkage::Internal,
                    result: cpp_ir::Type::Void,
                    name: destructor_name(destructor.id),
                    parameters: vec![cpp_ir::Parameter {
                        ty: cpp_ir::Type::Void.pointer_to(true),
                        name: "value".to_owned(),
                    }],
                    body: None,
                })
            })
            .collect()
    }

    fn destructor_definitions(&mut self) -> Vec<cpp_ir::Declaration> {
        let destructors = self
            .post
            .contracts
            .destructors
            .clone()
            .into_iter()
            .filter(|destructor| self.layouts.contains_key(&destructor.ty))
            .collect::<Vec<_>>();
        destructors
            .into_iter()
            .map(|destructor| {
                let mut statements = self.call_hook_at(
                    cpp_ir::Expression::Name("value".to_owned()),
                    destructor.hook,
                    format!("drop_arguments_type_{}", destructor.id.0),
                );
                statements.extend(self.destroy_type_body(&destructor));
                cpp_ir::Declaration::Function(cpp_ir::Function {
                    linkage: cpp_ir::Linkage::Internal,
                    result: cpp_ir::Type::Void,
                    name: destructor_name(destructor.id),
                    parameters: vec![cpp_ir::Parameter {
                        ty: cpp_ir::Type::Void.pointer_to(true),
                        name: "value".to_owned(),
                    }],
                    body: Some(cpp_ir::Block { statements }),
                })
            })
            .collect()
    }

    fn destroy_type_body(&mut self, destructor: &DestructorDefinition) -> Vec<cpp_ir::Statement> {
        let raw = cpp_ir::Expression::Name("value".to_owned());
        match self.post.types.entries[destructor.ty.0 as usize].kind {
            TypeDefinition::GrowingSequence { .. } | TypeDefinition::GrowingString => {
                return vec![expression_call(
                    "corbo_region_drop",
                    vec![reinterpret_pointer("corbo_region", raw)],
                )];
            }
            TypeDefinition::KeyedCollection { .. } => {
                return vec![expression_call(
                    "corbo_map_drop",
                    vec![reinterpret_pointer("corbo_map", raw)],
                )];
            }
            TypeDefinition::Pool { .. } => {
                return vec![expression_call(
                    "corbo_pool_drop",
                    vec![reinterpret_pointer("corbo_pool", raw)],
                )];
            }
            TypeDefinition::Allocation { .. } => {
                let mut statements = Vec::new();
                if let Some(component) = destructor
                    .owned_components
                    .iter()
                    .find(|component| component.position == PositionSelector::AllocationContent)
                {
                    let layout = self.layouts.get(&destructor.ty).copied();
                    if let Some(NativeDescriptorLayout::Allocation { slot, .. }) =
                        layout.and_then(|layout| layout.native.clone())
                    {
                        statements.push(expression_call(
                            &destructor_name(component.destructor),
                            vec![cpp_ir::Expression::Call {
                                callee: Box::new(cpp_ir::Expression::Name(
                                    "corbo_load_pointer".to_owned(),
                                )),
                                arguments: vec![byte_offset(
                                    cpp_ir::Expression::Name("value".to_owned()),
                                    slot,
                                )],
                            }],
                        ));
                    }
                }
                statements.push(expression_call(
                    "corbo_allocation_drop",
                    vec![reinterpret_pointer("corbo_allocation", raw)],
                ));
                return statements;
            }
            _ => {}
        }

        let mut statements = Vec::new();
        for component in &destructor.owned_components {
            if let PositionSelector::AllElements { length } = component.position {
                let Some(sequence) = self
                    .layouts
                    .get(&destructor.ty)
                    .and_then(|layout| layout.sequence.clone())
                else {
                    self.errors
                        .push(CppBackendError::MissingPositionRepresentation {
                            ty: destructor.ty,
                            position: component.position.clone(),
                        });
                    continue;
                };
                let count = length.unwrap_or(sequence.length);
                let index = format!(
                    "destroy_index_{}_{}",
                    destructor.id.0, component.destructor.0
                );
                statements.push(cpp_ir::Statement::Declare {
                    ty: cpp_ir::Type::Size,
                    name: index.clone(),
                    initializer: Some(cpp_ir::Expression::Unsigned(0)),
                });
                statements.push(cpp_ir::Statement::While {
                    condition: cpp_ir::Expression::Binary {
                        operator: cpp_ir::BinaryOperator::Less,
                        left: Box::new(cpp_ir::Expression::Name(index.clone())),
                        right: Box::new(cpp_ir::Expression::Unsigned(count as u128)),
                    },
                    body: cpp_ir::Block {
                        statements: vec![
                            expression_call(
                                &destructor_name(component.destructor),
                                vec![cpp_ir::Expression::ByteOffset {
                                    base: Box::new(cpp_ir::Expression::Name("value".to_owned())),
                                    bytes: Box::new(cpp_ir::Expression::Binary {
                                        operator: cpp_ir::BinaryOperator::Multiply,
                                        left: Box::new(cpp_ir::Expression::Name(index.clone())),
                                        right: Box::new(cpp_ir::Expression::Unsigned(
                                            sequence.stride as u128,
                                        )),
                                    }),
                                }],
                            ),
                            cpp_ir::Statement::Assign {
                                destination: cpp_ir::Expression::Name(index.clone()),
                                source: cpp_ir::Expression::Binary {
                                    operator: cpp_ir::BinaryOperator::Add,
                                    left: Box::new(cpp_ir::Expression::Name(index.clone())),
                                    right: Box::new(cpp_ir::Expression::Unsigned(1)),
                                },
                            },
                        ],
                    },
                });
                continue;
            }
            if matches!(component.position, PositionSelector::AllKeys) {
                // Keyed collections own their payloads through `corbo_map`.
                // `corbo_map_drop` invokes the planned payload destructor for
                // every live key before releasing both regions.
                continue;
            }
            let Some(offset) = self.component_offset(
                destructor.ty,
                match component.position {
                    PositionSelector::VariantField { variant, .. } => Some(variant),
                    _ => None,
                },
                &component.position,
            ) else {
                continue;
            };
            let call = expression_call(
                &destructor_name(component.destructor),
                vec![byte_offset(
                    cpp_ir::Expression::Name("value".to_owned()),
                    offset,
                )],
            );
            statements.push(self.destructor_guard(component.guard, destructor.ty, call));
        }
        statements
    }

    fn destructor_guard(
        &mut self,
        guard: PredicateId,
        ty: TypeId,
        statement: cpp_ir::Statement,
    ) -> cpp_ir::Statement {
        match self.post.execution.predicates[guard.0 as usize].kind {
            PredicateKind::Always => statement,
            PredicateKind::DestructorVariant { variant, .. } => {
                let Some(layout) = self.layouts.get(&ty).copied() else {
                    self.errors.push(CppBackendError::MissingLayout(ty));
                    return statement;
                };
                let Some(enumeration) = &layout.variant else {
                    self.errors
                        .push(CppBackendError::MissingPredicateRepresentation(guard));
                    return statement;
                };
                let discriminant = enumeration
                    .variants
                    .iter()
                    .find(|candidate| candidate.variant == variant)
                    .map(|candidate| candidate.discriminant)
                    .unwrap_or(u64::MAX);
                cpp_ir::Statement::If {
                    condition: cpp_ir::Expression::Binary {
                        operator: cpp_ir::BinaryOperator::Equal,
                        left: Box::new(cpp_ir::Expression::Call {
                            callee: Box::new(cpp_ir::Expression::Name(
                                "corbo_read_discriminant".to_owned(),
                            )),
                            arguments: vec![
                                cpp_ir::Expression::Name("value".to_owned()),
                                cpp_ir::Expression::Unsigned(
                                    enumeration.discriminant_bytes as u128,
                                ),
                            ],
                        }),
                        right: Box::new(cpp_ir::Expression::Unsigned(discriminant as u128)),
                    },
                    then_block: cpp_ir::Block {
                        statements: vec![statement],
                    },
                    else_block: None,
                }
            }
            _ => cpp_ir::Statement::If {
                condition: self.predicate(guard),
                then_block: cpp_ir::Block {
                    statements: vec![statement],
                },
                else_block: None,
            },
        }
    }

    fn function(&mut self, instance: FunctionInstanceId, body: &FunctionBody) -> cpp_ir::Function {
        let mut statements = Vec::new();
        for storage in &self.planned.storage.values {
            if storage.layout.is_some() {
                statements.push(cpp_ir::Statement::Declare {
                    ty: cpp_ir::Type::Void.pointer_to(true),
                    name: value_name(storage.value),
                    initializer: Some(cpp_ir::Expression::Null),
                });
            }
        }
        for binding in self.bindings_for_body(body.id) {
            statements.push(cpp_ir::Statement::Declare {
                ty: cpp_ir::Type::Void.pointer_to(true),
                name: binding_name(binding.id),
                initializer: Some(cpp_ir::Expression::Null),
            });
        }
        for evaluated in &self.post.objects.evaluated_places {
            if body
                .operations
                .iter()
                .any(|operation| operation.site().id == evaluated.produced_by)
            {
                statements.push(cpp_ir::Statement::Declare {
                    ty: cpp_ir::Type::Void.pointer_to(true),
                    name: evaluated_name(evaluated.id),
                    initializer: Some(cpp_ir::Expression::Null),
                });
            }
        }
        let scope_ids = self
            .scopes_for_body(body.id)
            .into_iter()
            .map(|scope| scope.id)
            .collect::<Vec<_>>();
        for scope in scope_ids {
            let initializer = if matches!(
                self.post.scopes.entries[scope.0 as usize].entry,
                ScopeEntry::Child { .. }
            ) {
                // The physical entry expression may depend on values produced
                // before EnterScope.  Evaluate it at that resolved event, not
                // at function prologue time.
                cpp_ir::Expression::Unsigned(0)
            } else {
                self.scope_entry_cursor(scope)
            };
            statements.push(cpp_ir::Statement::Declare {
                ty: cpp_ir::Type::Size,
                name: scope_cursor_name(scope),
                initializer: Some(initializer),
            });
        }
        for counter in &self.planned.storage.iteration_counters {
            let used = body.operations.iter().any(|operation| {
                matches!(operation, Operation::IterationIndex(index) if index.coordinate == counter.coordinate)
            });
            if used {
                statements.push(cpp_ir::Statement::Declare {
                    ty: cpp_ir::Type::Size,
                    name: iteration_name(counter.coordinate),
                    initializer: Some(cpp_ir::Expression::Unsigned(0)),
                });
            }
        }
        for operation in &body.operations {
            if let Operation::AwaitValue(value) = operation {
                statements.push(cpp_ir::Statement::Declare {
                    ty: cpp_ir::Type::Bool,
                    name: await_ready_name(value.source),
                    initializer: Some(cpp_ir::Expression::Boolean(false)),
                });
            }
        }
        for class in self
            .planned
            .storage
            .region_classes
            .iter()
            .filter(|class| self.scope_belongs_to_body(class.declaring_scope, body.id))
        {
            statements.push(cpp_ir::Statement::Declare {
                ty: cpp_ir::Type::Named("corbo_region_band".to_owned()).pointer_to(true),
                name: region_mark_name(class.id),
                initializer: Some(cpp_ir::Expression::Null),
            });
        }
        statements.extend(self.bind_external_storage(instance, body));
        let entry_timeline = self.post.execution.branches[body.root_branch.0 as usize].timeline;
        let entry = self.post.execution.timelines[entry_timeline.0 as usize]
            .entries
            .first;
        if let Some(frame) = self.async_frame(body.id).cloned() {
            let mut cases = vec![cpp_ir::SwitchCase {
                value: 0,
                body: cpp_ir::Block {
                    statements: vec![cpp_ir::Statement::Goto(moment_label(entry))],
                },
            }];
            cases.extend(
                frame
                    .transitions
                    .iter()
                    .map(|transition| cpp_ir::SwitchCase {
                        value: transition.discriminant,
                        body: cpp_ir::Block {
                            statements: vec![cpp_ir::Statement::Goto(moment_label(
                                transition.resume,
                            ))],
                        },
                    }),
            );
            statements.push(cpp_ir::Statement::Switch {
                value: self.async_state_discriminant(&frame),
                cases,
                default: Some(cpp_ir::Block {
                    statements: vec![cpp_ir::Statement::Return(Some(
                        cpp_ir::Expression::Boolean(true),
                    ))],
                }),
            });
        } else {
            statements.push(cpp_ir::Statement::Goto(moment_label(entry)));
        }
        let moments = self
            .post
            .execution
            .execution_moments
            .iter()
            .filter(|moment| moment.body == body.id)
            .cloned()
            .collect::<Vec<_>>();
        for moment in moments {
            statements.push(cpp_ir::Statement::Label(moment_label(moment.id)));
            statements.extend(self.enter_region_classes(moment.id));
            statements.extend(self.storage_at(moment.id));
            let operation = body
                .operations
                .iter()
                .find(|operation| operation.site().id == moment.operation)
                .cloned();
            if let Some(operation) = operation {
                statements.extend(self.operation_at(&operation, moment.id));
            }
            statements.extend(self.route(&moment));
        }
        statements.push(cpp_ir::Statement::Return(
            self.current_async
                .map(|_| cpp_ir::Expression::Boolean(true)),
        ));
        function_shell(instance, Some(cpp_ir::Block { statements }))
    }

    fn bind_external_storage(
        &mut self,
        instance: FunctionInstanceId,
        body: &FunctionBody,
    ) -> Vec<cpp_ir::Statement> {
        let mut statements = Vec::new();
        if let Some(frame) = self
            .current_async
            .and_then(|body| self.async_frame(body))
            .cloned()
        {
            for saved in &frame.saved {
                let pointer = byte_offset(
                    cpp_ir::Expression::Name("state".to_owned()),
                    saved.byte_offset,
                );
                statements.push(cpp_ir::Statement::Assign {
                    destination: cpp_ir::Expression::Name(value_name(saved.value)),
                    source: pointer.clone(),
                });
                if let Some(binding) = self.post.scopes.bindings.iter().find(|binding| {
                    matches!(self.post.values.provenance[self.post.values.entries[saved.value.0 as usize].provenance.0 as usize].kind,
                        ProvenanceKind::Binding(candidate) if candidate == binding.id)
                        || matches!(self.post.values.entries[saved.value.0 as usize].definition,
                            ValueDefinition::Parameter(candidate) if candidate == binding.id)
                }) {
                    statements.push(cpp_ir::Statement::Assign {
                        destination: cpp_ir::Expression::Name(binding_name(binding.id)),
                        source: pointer,
                    });
                }
            }
        }
        let signature = &self.post.declarations.signatures[self.post.declarations.instances
            [instance.0 as usize]
            .signature
            .0 as usize];
        for storage in &self.planned.storage.values {
            let value = &self.post.values.entries[storage.value.0 as usize];
            for alternative in
                std::iter::once(&storage.alternatives.first).chain(&storage.alternatives.rest)
            {
                match alternative.kind {
                    ValueStorageKind::Parameter { binding } => {
                        if self.current_async.is_some() {
                            continue;
                        }
                        let position = signature.parameters.iter().position(|parameter| {
                            matches!(parameter.identity, ParameterIdentity::Named { binding: candidate, .. } if candidate == binding)
                        });
                        if let Some(position) = position {
                            statements.push(cpp_ir::Statement::Assign {
                                destination: cpp_ir::Expression::Name(value_name(value.id)),
                                source: cpp_ir::Expression::Index {
                                    base: Box::new(cpp_ir::Expression::Name(
                                        "arguments".to_owned(),
                                    )),
                                    index: Box::new(cpp_ir::Expression::Unsigned(position as u128)),
                                },
                            });
                            statements.push(cpp_ir::Statement::Assign {
                                destination: cpp_ir::Expression::Name(binding_name(binding)),
                                source: cpp_ir::Expression::Name(value_name(value.id)),
                            });
                        }
                    }
                    ValueStorageKind::Capture { record, field } => {
                        if body.environment == Some(record) {
                            let record_ty = self.post.contracts.captures[record.0 as usize].ty;
                            if let Some(offset) = self.field_offset(record_ty, field) {
                                let address = byte_offset(
                                    cpp_ir::Expression::Name("environment".to_owned()),
                                    offset,
                                );
                                statements.push(cpp_ir::Statement::Assign {
                                    destination: cpp_ir::Expression::Name(value_name(value.id)),
                                    source: address,
                                });
                                if let Some(binding) = self.post.scopes.bindings.iter().find(|binding| {
                                    matches!(binding.introduced, BindingIntroduction::Capture { record: candidate, field: candidate_field } if candidate == record && candidate_field == field)
                                    && self.scope_belongs_to_body(binding.scope, body.id)
                                }) {
                                    statements.push(cpp_ir::Statement::Assign {
                                        destination: cpp_ir::Expression::Name(binding_name(binding.id)),
                                        source: cpp_ir::Expression::Name(value_name(value.id)),
                                    });
                                }
                            }
                        }
                    }
                    ValueStorageKind::Constant => {
                        statements.extend(self.bind_constant(value));
                    }
                    ValueStorageKind::Reservation(_)
                    | ValueStorageKind::Alias { .. }
                    | ValueStorageKind::SelectAlias { .. }
                    | ValueStorageKind::Temporary { .. }
                    | ValueStorageKind::None(_) => {}
                }
            }
        }
        statements
    }

    fn storage_at(&mut self, moment: ExecutionMomentId) -> Vec<cpp_ir::Statement> {
        let mut statements = Vec::new();
        for storage in &self.planned.storage.values {
            for alternative in
                std::iter::once(&storage.alternatives.first).chain(&storage.alternatives.rest)
            {
                match alternative.kind {
                    ValueStorageKind::Alias { source, bound_at } if bound_at == moment => {
                        let assignment = cpp_ir::Statement::Assign {
                            destination: cpp_ir::Expression::Name(value_name(storage.value)),
                            source: cpp_ir::Expression::Name(value_name(source)),
                        };
                        statements.push(self.guarded(alternative.guard, assignment));
                        continue;
                    }
                    ValueStorageKind::SelectAlias {
                        predicate,
                        when_true,
                        when_false,
                        bound_at,
                    } if bound_at == moment => {
                        let assignment = cpp_ir::Statement::Assign {
                            destination: cpp_ir::Expression::Name(value_name(storage.value)),
                            source: cpp_ir::Expression::Conditional {
                                condition: Box::new(self.predicate(predicate)),
                                when_true: Box::new(cpp_ir::Expression::Name(value_name(
                                    when_true,
                                ))),
                                when_false: Box::new(cpp_ir::Expression::Name(value_name(
                                    when_false,
                                ))),
                            },
                        };
                        statements.push(self.guarded(alternative.guard, assignment));
                        continue;
                    }
                    _ => {}
                }
                let allocation = match alternative.kind {
                    ValueStorageKind::Temporary {
                        start,
                        end,
                        allocated_at,
                        ..
                    } if allocated_at == moment => Some((start, end)),
                    ValueStorageKind::Reservation(reservation) => self
                        .planned
                        .reservations
                        .iter()
                        .find(|assignment| {
                            assignment.reservation == reservation
                                && assignment.reserved_at == moment
                                && self
                                    .planned
                                    .checked_flow
                                    .semantics
                                    .finals
                                    .iter()
                                    .find(|final_| final_.id == assignment.destination)
                                    .is_some_and(|final_| final_.value == storage.value)
                        })
                        .map(|_| {
                            let plan = &self.planned.storage.reservations[reservation.0 as usize];
                            (plan.start, plan.end)
                        }),
                    _ => None,
                };
                let Some((start, end)) = allocation else {
                    continue;
                };
                let start = self.cursor_expression(start);
                let end = self.cursor_expression(end);
                let binding = cpp_ir::Statement::Assign {
                    destination: cpp_ir::Expression::Name(value_name(storage.value)),
                    source: cpp_ir::Expression::ByteOffset {
                        base: Box::new(cpp_ir::Expression::Member {
                            base: Box::new(cpp_ir::Expression::Name(
                                "corbo_fixed_stack".to_owned(),
                            )),
                            member: "base".to_owned(),
                            through_pointer: false,
                        }),
                        bytes: Box::new(start),
                    },
                };
                statements.push(self.guarded(alternative.guard, binding));
                statements.push(cpp_ir::Statement::Expression(cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name(
                        "corbo_datastack_commit".to_owned(),
                    )),
                    arguments: vec![
                        cpp_ir::Expression::Unary {
                            operator: cpp_ir::UnaryOperator::AddressOf,
                            operand: Box::new(cpp_ir::Expression::Name(
                                "corbo_fixed_stack".to_owned(),
                            )),
                        },
                        end.clone(),
                    ],
                }));
                statements.push(cpp_ir::Statement::Assign {
                    destination: cpp_ir::Expression::Member {
                        base: Box::new(cpp_ir::Expression::Name("corbo_fixed_stack".to_owned())),
                        member: "cursor".to_owned(),
                        through_pointer: false,
                    },
                    source: cpp_ir::Expression::Call {
                        callee: Box::new(cpp_ir::Expression::Name("corbo_max_size".to_owned())),
                        arguments: vec![
                            cpp_ir::Expression::Member {
                                base: Box::new(cpp_ir::Expression::Name(
                                    "corbo_fixed_stack".to_owned(),
                                )),
                                member: "cursor".to_owned(),
                                through_pointer: false,
                            },
                            end,
                        ],
                    },
                });
            }
        }
        statements
    }

    fn guarded(&mut self, guard: PredicateId, statement: cpp_ir::Statement) -> cpp_ir::Statement {
        if matches!(
            self.post.execution.predicates[guard.0 as usize].kind,
            PredicateKind::Always
        ) {
            statement
        } else {
            cpp_ir::Statement::If {
                condition: self.predicate(guard),
                then_block: cpp_ir::Block {
                    statements: vec![statement],
                },
                else_block: None,
            }
        }
    }

    /// Exhaustive operation gate. Implemented representations produce typed
    /// C++ IR; missing ones fail compilation and can never be silently skipped.
    fn operation(&mut self, operation: &Operation) -> Vec<cpp_ir::Statement> {
        // This call is deliberately retained: adding a PostAST operation must
        // update the exhaustive backend inventory before this module compiles.
        let _representation = inventory::operation(operation);
        match operation {
            Operation::CreatePool(value) => self.create_pool(value),
            Operation::NativeOperation(value) => self.native_operation(value),
            Operation::CreateClosure(value) => self.create_closure(value),
            Operation::AdaptCallable(value) => self.adapt_callable(value),
            Operation::CallableCall(value) => self.call_callable(value),
            Operation::CreateFuture(value) => self.create_future(value),
            Operation::IntegerLiteral(value) => vec![cpp_ir::Statement::Assign {
                destination: self.typed_value(value.result),
                source: match value.value {
                    IntegerConstant::Signed(number) => cpp_ir::Expression::Signed(number),
                    IntegerConstant::Unsigned(number) => cpp_ir::Expression::Unsigned(number),
                },
            }],
            Operation::FloatLiteral(value) => vec![cpp_ir::Statement::Assign {
                destination: self.typed_value(value.result),
                source: match value.value {
                    FloatConstant::F32Bits(bits) => cpp_ir::Expression::FloatBits {
                        bits: bits as u64,
                        width: 32,
                    },
                    FloatConstant::F64Bits(bits) => {
                        cpp_ir::Expression::FloatBits { bits, width: 64 }
                    }
                },
            }],
            Operation::BooleanLiteral(value) => vec![cpp_ir::Statement::Assign {
                destination: self.typed_value(value.result),
                source: cpp_ir::Expression::Boolean(value.value),
            }],
            Operation::CopyPrimitive(value) => self.copy_value(value.result, value.source),
            Operation::CopyEligibleEnum(value) => self.copy_value(value.result, value.source),
            Operation::MoveValue(value) => self.materialize_transfer(value.result, value.value),
            Operation::ForwardResult(value) => {
                self.materialize_transfer(value.destination, value.source)
            }
            Operation::ParametricTransfer(value) => self.materialize_parametric_transfer(value),
            Operation::MergeValue(value) => self.materialize_guarded_transfers(
                value.result,
                &std::iter::once(value.incoming.first.clone())
                    .chain(value.incoming.rest.clone())
                    .collect::<Vec<_>>(),
            ),
            Operation::LoopParameter(value) => {
                // Stable loop storage is populated by the physical transfers
                // attached to incoming execution edges.
                vec![cpp_ir::Statement::Assign {
                    destination: cpp_ir::Expression::Name(binding_name(value.binding)),
                    source: cpp_ir::Expression::Name(value_name(value.result)),
                }]
            }
            Operation::ReceiveValue(value) => {
                let mut statements = self.materialize_transfer(value.result, value.source);
                statements.push(cpp_ir::Statement::Assign {
                    destination: cpp_ir::Expression::Name(binding_name(value.receiver)),
                    source: cpp_ir::Expression::Name(value_name(value.result)),
                });
                statements
            }
            Operation::InitializeBinding(value) => vec![cpp_ir::Statement::Assign {
                destination: cpp_ir::Expression::Name(binding_name(value.binding)),
                source: cpp_ir::Expression::Name(value_name(value.value)),
            }],
            Operation::InitializeDefault(value) => self.initialize_default(value),
            Operation::DiscardResult(value) => vec![expression_call(
                &destructor_name(value.destructor),
                vec![cpp_ir::Expression::Name(value_name(value.value))],
            )],
            Operation::ReadValue(value) => {
                self.copy_from_pointer(value.result, evaluated_name(value.source))
            }
            Operation::EvaluatePlace(value) => match self.place_address(value.place) {
                Some(address) => vec![cpp_ir::Statement::Assign {
                    destination: cpp_ir::Expression::Name(evaluated_name(value.result)),
                    source: address,
                }],
                None => Vec::new(),
            },
            Operation::Assign(value) => self.copy_to_pointer(value.target, value.value),
            Operation::BorrowShared(value) => self.store_reference(value.result, value.source),
            Operation::BorrowMutable(value) => self.store_reference(value.result, value.source),
            Operation::ReborrowShared(value) => self.store_reference(value.result, value.source),
            Operation::ReborrowMutable(value) => self.store_reference(value.result, value.source),
            Operation::Add(value) => self.binary(
                value.result,
                value.left,
                value.right,
                cpp_ir::BinaryOperator::Add,
            ),
            Operation::Subtract(value) => self.binary(
                value.result,
                value.left,
                value.right,
                cpp_ir::BinaryOperator::Subtract,
            ),
            Operation::Multiply(value) => self.binary(
                value.result,
                value.left,
                value.right,
                cpp_ir::BinaryOperator::Multiply,
            ),
            Operation::Divide(value) => self.binary(
                value.result,
                value.left,
                value.right,
                cpp_ir::BinaryOperator::Divide,
            ),
            Operation::Remainder(value) => self.binary(
                value.result,
                value.left,
                value.right,
                cpp_ir::BinaryOperator::Remainder,
            ),
            Operation::BitAnd(value) => self.binary(
                value.result,
                value.left,
                value.right,
                cpp_ir::BinaryOperator::BitAnd,
            ),
            Operation::BitOr(value) => self.binary(
                value.result,
                value.left,
                value.right,
                cpp_ir::BinaryOperator::BitOr,
            ),
            Operation::BitXor(value) => self.binary(
                value.result,
                value.left,
                value.right,
                cpp_ir::BinaryOperator::BitXor,
            ),
            Operation::ShiftLeft(value) => self.binary(
                value.result,
                value.left,
                value.right,
                cpp_ir::BinaryOperator::ShiftLeft,
            ),
            Operation::ShiftRight(value) => self.binary(
                value.result,
                value.left,
                value.right,
                cpp_ir::BinaryOperator::ShiftRight,
            ),
            Operation::Less(value) => self.binary(
                value.result,
                value.left,
                value.right,
                cpp_ir::BinaryOperator::Less,
            ),
            Operation::LessEqual(value) => self.binary(
                value.result,
                value.left,
                value.right,
                cpp_ir::BinaryOperator::LessEqual,
            ),
            Operation::Greater(value) => self.binary(
                value.result,
                value.left,
                value.right,
                cpp_ir::BinaryOperator::Greater,
            ),
            Operation::GreaterEqual(value) => self.binary(
                value.result,
                value.left,
                value.right,
                cpp_ir::BinaryOperator::GreaterEqual,
            ),
            Operation::Equal(value) => self.resolved_equality(
                value.result,
                value.left,
                value.right,
                value.comparison,
                false,
            ),
            Operation::NotEqual(value) => self.resolved_equality(
                value.result,
                value.left,
                value.right,
                value.comparison,
                true,
            ),
            Operation::Negate(value) => {
                self.unary(value.result, value.operand, cpp_ir::UnaryOperator::Negate)
            }
            Operation::BooleanNot(value) => self.unary(
                value.result,
                value.operand,
                cpp_ir::UnaryOperator::LogicalNot,
            ),
            Operation::BitNot(value) => {
                self.unary(value.result, value.operand, cpp_ir::UnaryOperator::BitNot)
            }
            Operation::PatternMatches(value) => vec![cpp_ir::Statement::Assign {
                destination: self.typed_value(value.result),
                source: self.pattern_test(value.subject, &value.test),
            }],
            Operation::IterationIndex(value) => vec![cpp_ir::Statement::Assign {
                destination: self.typed_value(value.result),
                source: cpp_ir::Expression::Name(iteration_name(value.coordinate)),
            }],
            Operation::NumericCast(value) => vec![cpp_ir::Statement::Assign {
                destination: self.typed_value(value.result),
                source: cpp_ir::Expression::Cast {
                    ty: numeric_type(value.target),
                    value: Box::new(self.typed_value(value.source)),
                },
            }],
            Operation::TextLiteral(value) => self.text_literal(value),
            Operation::ShortCircuitAnd(_) | Operation::ShortCircuitOr(_) => Vec::new(),
            Operation::ProjectField(value) => {
                self.project_field(value.base, value.field, value.result)
            }
            Operation::ProjectTupleField(value) => {
                self.project_tuple(value.base, value.position, value.result)
            }
            Operation::IndexPlace(value) => self.index_place(value),
            Operation::SequenceLength(value) => self.sequence_length(value),
            Operation::SlicePlace(value) => self.slice_place(value),
            Operation::SliceView(value) => self.slice_view(value),
            Operation::TryTextSlice(value) => self.try_text_slice(value),
            Operation::Dereference(value) => vec![cpp_ir::Statement::Assign {
                destination: cpp_ir::Expression::Name(evaluated_name(value.result)),
                source: cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                    arguments: vec![cpp_ir::Expression::Name(value_name(value.source))],
                },
            }],
            Operation::ConstructStruct(value) => {
                self.construct(value.result, value.ty, None, &value.components)
            }
            Operation::ConstructTuple(value) => {
                self.construct(value.result, value.ty, None, &value.components)
            }
            Operation::ConstructArray(value) => {
                self.construct(value.result, value.ty, None, &value.components)
            }
            Operation::ConstructEnum(value) => self.construct(
                value.result,
                value.ty,
                Some(value.variant),
                &value.components,
            ),
            Operation::RepeatArray(value) => self.repeat_array(value),
            Operation::ExtractTupleField(value) => self.extract_tuple(value),
            Operation::ExtractVariantField(value) => self.extract_variant(value),
            Operation::DirectCall(value) => {
                self.call_function(value.site.id, value.target, &value.arguments, value.result)
            }
            Operation::ExternalCall(value) => self.call_external(value),
            Operation::IntrinsicCall(value) => self.call_intrinsic(value),
            Operation::MethodCall(value) => match value.target.target {
                MethodTarget::Concrete(target) => {
                    let definition = self.post.declarations.instances[target.0 as usize].definition;
                    if matches!(
                        self.post.declarations.functions[definition.0 as usize].body,
                        FunctionImplementation::RuntimeJoin
                    ) {
                        self.join_value(value.site.id, value.result, value.target.receiver)
                    } else {
                        self.call_function(value.site.id, target, &value.arguments, value.result)
                    }
                }
                _ => {
                    self.errors
                        .push(CppBackendError::MissingOperationRepresentation {
                            operation: value.site.id,
                            representation: "non-concrete MethodCall",
                        });
                    Vec::new()
                }
            },
            Operation::ReturnControl(value) => {
                let mut statements = self.copy_value_to_expression(
                    cpp_ir::Expression::Name("output".to_owned()),
                    value.value,
                );
                statements.extend(self.cleanup(value.exit));
                for exit in &value.outer_exits {
                    statements.extend(self.cleanup(*exit));
                }
                if let Some(frame) = self.current_async.and_then(|body| self.async_frame(body)) {
                    statements.push(expression_call(
                        "corbo_write_discriminant",
                        vec![
                            byte_offset(
                                cpp_ir::Expression::Name("state".to_owned()),
                                frame.state_offset,
                            ),
                            cpp_ir::Expression::Unsigned(8),
                            cpp_ir::Expression::Unsigned(frame.completed_discriminant as u128),
                        ],
                    ));
                    statements.push(cpp_ir::Statement::Return(Some(
                        cpp_ir::Expression::Boolean(true),
                    )));
                } else {
                    statements.push(cpp_ir::Statement::Return(None));
                }
                statements
            }
            Operation::BreakControl(value) => {
                self.control_exit_cleanup(value.exit, &value.outer_exits)
            }
            Operation::ContinueControl(value) => {
                self.control_exit_cleanup(value.exit, &value.outer_exits)
            }
            Operation::PropagateResult(value) => self.propagate_result(value),
            Operation::PropagateOption(value) => self.propagate_option(value),
            Operation::UnwrapResult(value) => self.unwrap_variant(
                value.subject,
                value.success_variant,
                value.payload,
                value.result,
                value.reference.is_some(),
            ),
            Operation::UnwrapOption(value) => self.unwrap_variant(
                value.subject,
                value.some,
                value.payload,
                value.result,
                value.reference.is_some(),
            ),
            Operation::DropValue(value) => vec![expression_call(
                &destructor_name(value.destructor),
                vec![cpp_ir::Expression::Name(value_name(value.value))],
            )],
            Operation::AllocatePoolSlot(value) => {
                self.allocate_pool_slot(value.pool, value.content, value.result)
            }
            Operation::TryAllocatePoolSlot(value) => self.try_allocate_pool_slot(value),
            Operation::CreateGrowingStorage(value) => self.create_growing_storage(value),
            Operation::GrowStorage(value) => self.grow_storage(value),
            Operation::AddressOf(value) => vec![cpp_ir::Statement::Assign {
                destination: self.typed_value(value.result),
                source: cpp_ir::Expression::ReinterpretCast {
                    ty: cpp_ir::Type::Size,
                    value: Box::new(cpp_ir::Expression::Name(evaluated_name(value.source))),
                },
            }],
            Operation::ForeignC(value) => {
                self.foreign_region(value.region, &value.operands, &value.outputs, false)
            }
            Operation::ForeignCpp(value) => {
                self.foreign_region(value.region, &value.operands, &value.outputs, false)
            }
            Operation::ForeignAssembly(value) => {
                self.foreign_region(value.region, &value.operands, &value.outputs, true)
            }
            Operation::RuntimeCheckOperation(value) => self.runtime_check(value),
            Operation::EnterScope(value) => vec![cpp_ir::Statement::Assign {
                destination: cpp_ir::Expression::Name(scope_cursor_name(value.scope)),
                source: self.scope_entry_cursor(value.scope),
            }],
            Operation::CreateContractFuture(value) => {
                self.errors
                    .push(CppBackendError::MissingOperationRepresentation {
                        operation: value.site.id,
                        representation: "abstract contract future reached concrete C++ emission",
                    });
                Vec::new()
            }
            Operation::UnitValue(_)
            | Operation::AddAssign(_)
            | Operation::SubtractAssign(_)
            | Operation::MultiplyAssign(_)
            | Operation::DivideAssign(_)
            | Operation::RemainderAssign(_)
            | Operation::BitAndAssign(_)
            | Operation::BitOrAssign(_)
            | Operation::BitXorAssign(_)
            | Operation::ShiftLeftAssign(_)
            | Operation::ShiftRightAssign(_)
            | Operation::IfDecision(_)
            | Operation::IfLetDecision(_)
            | Operation::MatchDecision(_)
            | Operation::LoopControl(_)
            | Operation::WhileControl(_)
            | Operation::ForControl(_)
            | Operation::BeginBranch(_)
            | Operation::CompleteBranch(_)
            | Operation::BeginLockEffect(_)
            | Operation::EndLockEffect(_)
            | Operation::EnterUnchecked(_)
            | Operation::ExitUnchecked(_)
            | Operation::CaptureMove(_)
            | Operation::CaptureCopy(_)
            | Operation::CaptureParametric(_)
            | Operation::EnterMoveBlock(_)
            | Operation::AwaitValue(_)
            | Operation::YieldExecution(_)
            | Operation::AdoptOwnedValue(_)
            | Operation::ReleaseOwnedValue(_) => Vec::new(),
            Operation::ExitScope(value) => self.cleanup(value.exit),
        }
    }

    fn control_exit_cleanup(
        &mut self,
        exit: ScopeExitId,
        outer_exits: &[ScopeExitId],
    ) -> Vec<cpp_ir::Statement> {
        let mut statements = self.cleanup(exit);
        for outer in outer_exits {
            statements.extend(self.cleanup(*outer));
        }
        statements
    }

    fn operation_at(
        &mut self,
        operation: &Operation,
        moment: ExecutionMomentId,
    ) -> Vec<cpp_ir::Statement> {
        match operation {
            Operation::YieldExecution(value) => {
                let point = &self.post.execution.suspensions[value.suspension.0 as usize];
                if moment != point.suspend {
                    return Vec::new();
                }
                let mut statements = self.set_async_state(value.suspension);
                statements.push(cpp_ir::Statement::Return(Some(
                    cpp_ir::Expression::Boolean(false),
                )));
                statements
            }
            Operation::AwaitValue(value) => {
                let point = &self.post.execution.suspensions[value.suspension.0 as usize];
                if moment == value.site.execution_moments.first {
                    return self.poll_await(value);
                }
                if moment == point.suspend {
                    let mut statements = self.set_async_state(value.suspension);
                    statements.push(cpp_ir::Statement::Return(Some(
                        cpp_ir::Expression::Boolean(false),
                    )));
                    return statements;
                }
                Vec::new()
            }
            Operation::AddAssign(value) => self.compound_assignment_at(
                value.previous,
                value.computed,
                value.target,
                value.operand,
                &value.phases,
                cpp_ir::BinaryOperator::Add,
                moment,
            ),
            Operation::SubtractAssign(value) => self.compound_assignment_at(
                value.previous,
                value.computed,
                value.target,
                value.operand,
                &value.phases,
                cpp_ir::BinaryOperator::Subtract,
                moment,
            ),
            Operation::MultiplyAssign(value) => self.compound_assignment_at(
                value.previous,
                value.computed,
                value.target,
                value.operand,
                &value.phases,
                cpp_ir::BinaryOperator::Multiply,
                moment,
            ),
            Operation::DivideAssign(value) => self.compound_assignment_at(
                value.previous,
                value.computed,
                value.target,
                value.operand,
                &value.phases,
                cpp_ir::BinaryOperator::Divide,
                moment,
            ),
            Operation::RemainderAssign(value) => self.compound_assignment_at(
                value.previous,
                value.computed,
                value.target,
                value.operand,
                &value.phases,
                cpp_ir::BinaryOperator::Remainder,
                moment,
            ),
            Operation::BitAndAssign(value) => self.compound_assignment_at(
                value.previous,
                value.computed,
                value.target,
                value.operand,
                &value.phases,
                cpp_ir::BinaryOperator::BitAnd,
                moment,
            ),
            Operation::BitOrAssign(value) => self.compound_assignment_at(
                value.previous,
                value.computed,
                value.target,
                value.operand,
                &value.phases,
                cpp_ir::BinaryOperator::BitOr,
                moment,
            ),
            Operation::BitXorAssign(value) => self.compound_assignment_at(
                value.previous,
                value.computed,
                value.target,
                value.operand,
                &value.phases,
                cpp_ir::BinaryOperator::BitXor,
                moment,
            ),
            Operation::ShiftLeftAssign(value) => self.compound_assignment_at(
                value.previous,
                value.computed,
                value.target,
                value.operand,
                &value.phases,
                cpp_ir::BinaryOperator::ShiftLeft,
                moment,
            ),
            Operation::ShiftRightAssign(value) => self.compound_assignment_at(
                value.previous,
                value.computed,
                value.target,
                value.operand,
                &value.phases,
                cpp_ir::BinaryOperator::ShiftRight,
                moment,
            ),
            Operation::Assign(value) => {
                if value.replacement.write_after == moment {
                    self.copy_to_pointer(value.target, value.value)
                } else {
                    Vec::new()
                }
            }
            _ => {
                let produced_at = self
                    .post
                    .values
                    .entries
                    .iter()
                    .filter_map(|value| match value.definition {
                        ValueDefinition::OperationResult {
                            operation: candidate,
                            produced_at,
                        }
                        | ValueDefinition::ConditionalResult {
                            operation: candidate,
                            produced_at,
                            ..
                        } if candidate == operation.site().id => Some(produced_at),
                        _ => None,
                    })
                    .min_by_key(|candidate| candidate.0);
                let emit_at = produced_at.unwrap_or(operation.site().execution_moments.first);
                if emit_at == moment {
                    self.operation(operation)
                } else {
                    Vec::new()
                }
            }
        }
    }

    fn compound_assignment_at(
        &mut self,
        previous: ValueId,
        computed: ValueId,
        target: EvaluatedPlaceId,
        operand: ValueId,
        phases: &ReadModifyWriteMoments,
        operator: cpp_ir::BinaryOperator,
        moment: ExecutionMomentId,
    ) -> Vec<cpp_ir::Statement> {
        if moment == phases.read_previous {
            return self.copy_from_pointer(previous, evaluated_name(target));
        }
        if moment == phases.compute {
            return self.binary(computed, previous, operand, operator);
        }
        if moment == phases.write {
            return self.copy_to_pointer(target, computed);
        }
        Vec::new()
    }

    fn initialize_default(&mut self, value: &InitializeDefault) -> Vec<cpp_ir::Statement> {
        self.default_into(
            cpp_ir::Expression::Name(value_name(value.result)),
            value.plan,
        )
    }

    fn default_into(
        &mut self,
        destination: cpp_ir::Expression,
        plan: DefaultPlanId,
    ) -> Vec<cpp_ir::Statement> {
        let plan = self.post.declarations.defaults[plan.0 as usize].clone();
        let mut statements = Vec::new();
        match plan.kind {
            DefaultInitializationKind::EmptyNative => {
                statements.push(cpp_ir::Statement::ZeroBytes {
                    destination,
                    bytes: cpp_ir::Expression::Unsigned(self.fixed_size(plan.ty) as u128),
                })
            }
            DefaultInitializationKind::Constant(value) => {
                if let Some(expression) = constant_expression(&value) {
                    statements.push(cpp_ir::Statement::Assign {
                        destination: self.typed_at(destination, plan.ty),
                        source: expression,
                    });
                } else if let ConstantValue::Utf8(bytes) = value {
                    statements.extend(self.store_utf8_descriptor(destination, plan.ty, bytes));
                }
            }
            DefaultInitializationKind::Struct(fields) => {
                statements.push(cpp_ir::Statement::ZeroBytes {
                    destination: destination.clone(),
                    bytes: cpp_ir::Expression::Unsigned(self.fixed_size(plan.ty) as u128),
                });
                for field in fields {
                    if let Some(offset) = self.field_offset(plan.ty, field.field) {
                        statements.extend(
                            self.default_into(byte_offset(destination.clone(), offset), field.plan),
                        );
                    }
                }
            }
            DefaultInitializationKind::Variant { variant, fields } => {
                statements.push(cpp_ir::Statement::ZeroBytes {
                    destination: destination.clone(),
                    bytes: cpp_ir::Expression::Unsigned(self.fixed_size(plan.ty) as u128),
                });
                statements.extend(self.write_variant_tag(destination.clone(), plan.ty, variant));
                for field in fields {
                    let position = PositionSelector::VariantField {
                        variant,
                        field: field.field,
                    };
                    if let Some(offset) = self.component_offset(plan.ty, Some(variant), &position) {
                        statements.extend(
                            self.default_into(byte_offset(destination.clone(), offset), field.plan),
                        );
                    }
                }
            }
            DefaultInitializationKind::Tuple(elements) => {
                statements.push(cpp_ir::Statement::ZeroBytes {
                    destination: destination.clone(),
                    bytes: cpp_ir::Expression::Unsigned(self.fixed_size(plan.ty) as u128),
                });
                let layout = self.layouts.get(&plan.ty).copied();
                for (index, element) in elements.into_iter().enumerate() {
                    if let Some(offset) = layout.and_then(|layout| {
                        layout
                            .tuple_elements
                            .iter()
                            .find(|candidate| candidate.position == index as u32)
                            .map(|candidate| candidate.byte_offset)
                    }) {
                        statements.extend(
                            self.default_into(byte_offset(destination.clone(), offset), element),
                        );
                    }
                }
            }
            DefaultInitializationKind::Array { element, count } => {
                let element_ty = self.post.declarations.defaults[element.0 as usize].ty;
                let stride = self.fixed_size(element_ty);
                for index in 0..count {
                    statements.extend(
                        self.default_into(
                            byte_offset(destination.clone(), index * stride),
                            element,
                        ),
                    );
                }
            }
            DefaultInitializationKind::Intrinsic(intrinsic) => {
                statements.push(expression_call(
                    &intrinsic_name(intrinsic),
                    vec![destination, cpp_ir::Expression::Null],
                ));
            }
        }
        statements
    }

    fn typed_at(&self, address: cpp_ir::Expression, ty: TypeId) -> cpp_ir::Expression {
        cpp_ir::Expression::Unary {
            operator: cpp_ir::UnaryOperator::Dereference,
            operand: Box::new(cpp_ir::Expression::ReinterpretCast {
                ty: cpp_ir::Type::Named(type_name(ty)).pointer_to(true),
                value: Box::new(address),
            }),
        }
    }

    fn text_literal(&mut self, value: &TextLiteral) -> Vec<cpp_ir::Statement> {
        self.store_utf8_descriptor(
            cpp_ir::Expression::Name(value_name(value.result)),
            self.post.values.entries[value.result.0 as usize].ty,
            value.utf8.clone(),
        )
    }

    fn store_utf8_descriptor(
        &mut self,
        destination: cpp_ir::Expression,
        ty: TypeId,
        bytes: Vec<u8>,
    ) -> Vec<cpp_ir::Statement> {
        let Some(NativeDescriptorLayout::View { pointer, length }) = self
            .layouts
            .get(&ty)
            .and_then(|layout| layout.native.clone())
        else {
            self.errors.push(CppBackendError::MissingLayout(ty));
            return Vec::new();
        };
        vec![
            expression_call(
                "corbo_store_pointer",
                vec![
                    byte_offset(destination.clone(), pointer),
                    cpp_ir::Expression::ReinterpretCast {
                        ty: cpp_ir::Type::Void.pointer_to(true),
                        value: Box::new(cpp_ir::Expression::StringLiteral(bytes.clone())),
                    },
                ],
            ),
            cpp_ir::Statement::Assign {
                destination: self.size_at(byte_offset(destination, length)),
                source: cpp_ir::Expression::Unsigned(bytes.len() as u128),
            },
        ]
    }

    fn call_intrinsic(&mut self, value: &IntrinsicCall) -> Vec<cpp_ir::Statement> {
        let arguments = format!("intrinsic_arguments_{}", value.site.id.0);
        let mut statements = self.prepare_arguments(&arguments, &value.arguments);
        statements.push(expression_call(
            &intrinsic_name(value.target),
            vec![
                cpp_ir::Expression::Name(value_name(value.result)),
                cpp_ir::Expression::Name(arguments),
            ],
        ));
        statements
    }

    fn write_variant_tag(
        &mut self,
        destination: cpp_ir::Expression,
        ty: TypeId,
        variant: VariantId,
    ) -> Vec<cpp_ir::Statement> {
        let Some(enumeration) = self
            .layouts
            .get(&ty)
            .and_then(|layout| layout.variant.clone())
        else {
            self.errors.push(CppBackendError::MissingLayout(ty));
            return Vec::new();
        };
        let Some(discriminant) = enumeration
            .variants
            .iter()
            .find(|candidate| candidate.variant == variant)
            .map(|candidate| candidate.discriminant)
        else {
            self.errors
                .push(CppBackendError::MissingOperationRepresentation {
                    operation: OperationId(u32::MAX),
                    representation: "variant discriminant layout",
                });
            return Vec::new();
        };
        vec![expression_call(
            "corbo_write_discriminant",
            vec![
                destination,
                cpp_ir::Expression::Unsigned(enumeration.discriminant_bytes as u128),
                cpp_ir::Expression::Unsigned(discriminant as u128),
            ],
        )]
    }

    fn try_text_slice(&mut self, value: &TryTextSlice) -> Vec<cpp_ir::Statement> {
        let mut view = Vec::new();
        let Some(base) = self.contiguous_data(
            value.source,
            self.post.values.entries[value.view.0 as usize].ty,
        ) else {
            return Vec::new();
        };
        let view_ty = self.post.values.entries[value.view.0 as usize].ty;
        let Some(NativeDescriptorLayout::View { pointer, length }) = self
            .layouts
            .get(&view_ty)
            .and_then(|layout| layout.native.clone())
        else {
            self.errors.push(CppBackendError::MissingLayout(view_ty));
            return Vec::new();
        };
        view.push(expression_call(
            "corbo_store_pointer",
            vec![
                byte_offset(cpp_ir::Expression::Name(value_name(value.view)), pointer),
                byte_offset(base, 0),
            ],
        ));
        view.push(cpp_ir::Statement::Assign {
            destination: self.size_at(byte_offset(
                cpp_ir::Expression::Name(value_name(value.view)),
                length,
            )),
            source: cpp_ir::Expression::Binary {
                operator: cpp_ir::BinaryOperator::Subtract,
                left: Box::new(self.typed_value(value.end)),
                right: Box::new(self.typed_value(value.start)),
            },
        });
        let result_ty = self.post.values.entries[value.result.0 as usize].ty;
        let result = cpp_ir::Expression::Name(value_name(value.result));
        let success_offset = self.component_offset(
            result_ty,
            Some(value.success),
            &PositionSelector::VariantField {
                variant: value.success,
                field: value.success_payload,
            },
        );
        let failure_offset = self.component_offset(
            result_ty,
            Some(value.failure),
            &PositionSelector::VariantField {
                variant: value.failure,
                field: value.failure_payload,
            },
        );
        let (Some(success_offset), Some(failure_offset)) = (success_offset, failure_offset) else {
            return Vec::new();
        };
        let error_ty = self.post.declarations.fields[value.failure_payload.0 as usize].ty;
        let mut success = self.write_variant_tag(result.clone(), result_ty, value.success);
        success.push(cpp_ir::Statement::CopyBytes {
            destination: byte_offset(result.clone(), success_offset),
            source: cpp_ir::Expression::Name(value_name(value.view)),
            bytes: cpp_ir::Expression::Unsigned(self.fixed_size(view_ty) as u128),
        });
        let error_address = byte_offset(result.clone(), failure_offset);
        let out_of_bounds = cpp_ir::Expression::Binary {
            operator: cpp_ir::BinaryOperator::LogicalOr,
            left: Box::new(cpp_ir::Expression::Binary {
                operator: cpp_ir::BinaryOperator::Greater,
                left: Box::new(self.typed_value(value.start)),
                right: Box::new(self.typed_value(value.end)),
            }),
            right: Box::new(cpp_ir::Expression::Binary {
                operator: cpp_ir::BinaryOperator::Greater,
                left: Box::new(self.typed_value(value.end)),
                right: Box::new(self.typed_value(value.length)),
            }),
        };
        let mut failure = self.write_variant_tag(result.clone(), result_ty, value.failure);
        failure.push(cpp_ir::Statement::ZeroBytes {
            destination: error_address.clone(),
            bytes: cpp_ir::Expression::Unsigned(self.fixed_size(error_ty) as u128),
        });
        failure.push(cpp_ir::Statement::If {
            condition: out_of_bounds,
            then_block: cpp_ir::Block {
                statements: self.write_variant_tag(
                    error_address.clone(),
                    error_ty,
                    value.out_of_bounds,
                ),
            },
            else_block: Some(cpp_ir::Block {
                statements: self.write_variant_tag(
                    error_address,
                    error_ty,
                    value.not_char_boundary,
                ),
            }),
        });
        view.push(cpp_ir::Statement::If {
            condition: self.predicate(value.valid),
            then_block: cpp_ir::Block {
                statements: success,
            },
            else_block: Some(cpp_ir::Block {
                statements: failure,
            }),
        });
        view
    }

    fn unwrap_variant(
        &mut self,
        subject: ValueId,
        variant: VariantId,
        field: FieldId,
        result: ValueId,
        reference: bool,
    ) -> Vec<cpp_ir::Statement> {
        let ty = self.post.values.entries[subject.0 as usize].ty;
        let Some(offset) = self.component_offset(
            ty,
            Some(variant),
            &PositionSelector::VariantField { variant, field },
        ) else {
            return Vec::new();
        };
        self.extract_at(result, subject, offset, reference)
    }

    fn propagate_result(&mut self, _value: &PropagateResult) -> Vec<cpp_ir::Statement> {
        // Extraction, conversion, early ReturnControl and success forwarding
        // are separate resolved operations on the two explicit branches.
        Vec::new()
    }

    fn propagate_option(&mut self, _value: &PropagateOption) -> Vec<cpp_ir::Statement> {
        Vec::new()
    }

    fn allocate_pool_slot(
        &mut self,
        pool: ValueId,
        content: ValueId,
        result: ValueId,
    ) -> Vec<cpp_ir::Statement> {
        let content_ty = self.post.values.entries[content.0 as usize].ty;
        let result_ty = self.post.values.entries[result.0 as usize].ty;
        let Some(NativeDescriptorLayout::Allocation { slot, .. }) = self
            .layouts
            .get(&result_ty)
            .and_then(|layout| layout.native.clone())
        else {
            self.errors.push(CppBackendError::MissingLayout(result_ty));
            return Vec::new();
        };
        vec![
            cpp_ir::Statement::If {
                condition: cpp_ir::Expression::Unary {
                    operator: cpp_ir::UnaryOperator::LogicalNot,
                    operand: Box::new(cpp_ir::Expression::Call {
                        callee: Box::new(cpp_ir::Expression::Name("corbo_pool_take".to_owned())),
                        arguments: vec![
                            reinterpret_pointer(
                                "corbo_pool",
                                cpp_ir::Expression::Name(value_name(pool)),
                            ),
                            reinterpret_pointer(
                                "corbo_allocation",
                                cpp_ir::Expression::Name(value_name(result)),
                            ),
                        ],
                    }),
                },
                then_block: cpp_ir::Block {
                    statements: vec![expression_call(
                        "corbo_fail",
                        vec![cpp_ir::Expression::StringLiteral(
                            b"corbo: pool capacity exceeded".to_vec(),
                        )],
                    )],
                },
                else_block: None,
            },
            cpp_ir::Statement::CopyBytes {
                destination: cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                    arguments: vec![byte_offset(
                        cpp_ir::Expression::Name(value_name(result)),
                        slot,
                    )],
                },
                source: cpp_ir::Expression::Name(value_name(content)),
                bytes: cpp_ir::Expression::Unsigned(self.fixed_size(content_ty) as u128),
            },
        ]
    }

    fn try_allocate_pool_slot(&mut self, value: &TryAllocatePoolSlot) -> Vec<cpp_ir::Statement> {
        let result_ty = self.post.values.entries[value.result.0 as usize].ty;
        let allocation_ty = self.post.values.entries[value.allocation.0 as usize].ty;
        let content_ty = self.post.values.entries[value.content.0 as usize].ty;
        let ready = runtime_ready_name(value.site.id);
        let Some(NativeDescriptorLayout::Allocation { slot, .. }) = self
            .layouts
            .get(&allocation_ty)
            .and_then(|layout| layout.native.clone())
        else {
            self.errors
                .push(CppBackendError::MissingLayout(allocation_ty));
            return Vec::new();
        };
        let mut statements = vec![cpp_ir::Statement::Assign {
            destination: cpp_ir::Expression::Name(ready.clone()),
            source: cpp_ir::Expression::Call {
                callee: Box::new(cpp_ir::Expression::Name("corbo_pool_take".to_owned())),
                arguments: vec![
                    reinterpret_pointer(
                        "corbo_pool",
                        cpp_ir::Expression::Name(value_name(value.pool)),
                    ),
                    reinterpret_pointer(
                        "corbo_allocation",
                        cpp_ir::Expression::Name(value_name(value.allocation)),
                    ),
                ],
            },
        }];
        let success_offset = self.component_offset(
            result_ty,
            Some(value.success_variant),
            &PositionSelector::VariantField {
                variant: value.success_variant,
                field: value.success_payload,
            },
        );
        let failure_offset = self.component_offset(
            result_ty,
            Some(value.failure_variant),
            &PositionSelector::VariantField {
                variant: value.failure_variant,
                field: value.failure_payload,
            },
        );
        let (Some(success_offset), Some(failure_offset)) = (success_offset, failure_offset) else {
            return statements;
        };
        let mut success = vec![cpp_ir::Statement::CopyBytes {
            destination: cpp_ir::Expression::Call {
                callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                arguments: vec![byte_offset(
                    cpp_ir::Expression::Name(value_name(value.allocation)),
                    slot,
                )],
            },
            source: cpp_ir::Expression::Name(value_name(value.content)),
            bytes: cpp_ir::Expression::Unsigned(self.fixed_size(content_ty) as u128),
        }];
        success.extend(self.write_variant_tag(
            cpp_ir::Expression::Name(value_name(value.result)),
            result_ty,
            value.success_variant,
        ));
        success.push(cpp_ir::Statement::CopyBytes {
            destination: byte_offset(
                cpp_ir::Expression::Name(value_name(value.result)),
                success_offset,
            ),
            source: cpp_ir::Expression::Name(value_name(value.allocation)),
            bytes: cpp_ir::Expression::Unsigned(self.fixed_size(allocation_ty) as u128),
        });
        let error_ty = self.post.declarations.fields[value.failure_payload.0 as usize].ty;
        let mut failure = self.write_variant_tag(
            cpp_ir::Expression::Name(value_name(value.result)),
            result_ty,
            value.failure_variant,
        );
        let error = byte_offset(
            cpp_ir::Expression::Name(value_name(value.result)),
            failure_offset,
        );
        failure.push(cpp_ir::Statement::ZeroBytes {
            destination: error.clone(),
            bytes: cpp_ir::Expression::Unsigned(self.fixed_size(error_ty) as u128),
        });
        failure.extend(self.write_variant_tag(error, error_ty, value.pool_full_variant));
        failure.push(expression_call(
            &destructor_name(value.failure_cleanup.destructor),
            vec![cpp_ir::Expression::Name(value_name(
                value.failure_cleanup.value,
            ))],
        ));
        statements.push(cpp_ir::Statement::If {
            condition: cpp_ir::Expression::Name(ready),
            then_block: cpp_ir::Block {
                statements: success,
            },
            else_block: Some(cpp_ir::Block {
                statements: failure,
            }),
        });
        statements
    }

    fn create_growing_storage(&mut self, value: &CreateGrowingStorage) -> Vec<cpp_ir::Statement> {
        let Some(descriptor) = self.value_for_entity(&EntityId::Address(value.descriptor)) else {
            self.errors
                .push(CppBackendError::MissingOperationRepresentation {
                    operation: value.site.id,
                    representation: "CreateGrowingStorage descriptor",
                });
            return Vec::new();
        };
        let descriptor_ty = self.post.values.entries[descriptor.0 as usize].ty;
        let width = match self.post.types.entries[descriptor_ty.0 as usize].kind {
            TypeDefinition::GrowingSequence { element } => self.fixed_size(element),
            TypeDefinition::GrowingString => 1,
            _ => {
                self.errors
                    .push(CppBackendError::MissingOperationRepresentation {
                        operation: value.site.id,
                        representation: "CreateGrowingStorage non-region descriptor",
                    });
                return Vec::new();
            }
        };
        let mut statements = vec![expression_call(
            "corbo_region_init",
            vec![
                reinterpret_pointer(
                    "corbo_region",
                    cpp_ir::Expression::Name(value_name(descriptor)),
                ),
                cpp_ir::Expression::Unsigned(width as u128),
                cpp_ir::Expression::Null,
            ],
        )];
        statements.extend(self.materialize_transfer(value.result, descriptor));
        statements
    }

    fn grow_storage(&mut self, value: &GrowStorage) -> Vec<cpp_ir::Statement> {
        let collection = self.post.objects.collections[value.collection.0 as usize].clone();
        let descriptor = match collection.descriptor {
            CollectionDescriptor::Address(address) => self
                .value_for_entity(&EntityId::Address(address))
                .map(|value| cpp_ir::Expression::Name(value_name(value))),
            CollectionDescriptor::Place(place) => self.place_address(place),
        };
        let Some(descriptor) = descriptor else {
            self.errors
                .push(CppBackendError::MissingOperationRepresentation {
                    operation: value.site.id,
                    representation: "GrowStorage collection descriptor",
                });
            return Vec::new();
        };
        let width = match self.post.types.entries[collection.ty.0 as usize].kind {
            TypeDefinition::GrowingSequence { element } => self.fixed_size(element),
            TypeDefinition::GrowingString => 1,
            _ => {
                self.errors
                    .push(CppBackendError::MissingOperationRepresentation {
                        operation: value.site.id,
                        representation: "GrowStorage non-region collection",
                    });
                return Vec::new();
            }
        };
        let count = if width == 1 {
            self.typed_value(value.required_bytes)
        } else {
            cpp_ir::Expression::Binary {
                operator: cpp_ir::BinaryOperator::Divide,
                left: Box::new(cpp_ir::Expression::Binary {
                    operator: cpp_ir::BinaryOperator::Add,
                    left: Box::new(self.typed_value(value.required_bytes)),
                    right: Box::new(cpp_ir::Expression::Unsigned((width - 1) as u128)),
                }),
                right: Box::new(cpp_ir::Expression::Unsigned(width as u128)),
            }
        };
        vec![cpp_ir::Statement::Expression(cpp_ir::Expression::Call {
            callee: Box::new(cpp_ir::Expression::Name("corbo_region_append".to_owned())),
            arguments: vec![reinterpret_pointer("corbo_region", descriptor), count],
        })]
    }

    fn foreign_region(
        &mut self,
        region: ForeignRegionId,
        operands: &[ForeignOperand],
        outputs: &[ForeignWriteback],
        assembly: bool,
    ) -> Vec<cpp_ir::Statement> {
        let Some(region) = self
            .planned
            .foreign
            .regions
            .iter()
            .find(|candidate| candidate.id == region)
        else {
            self.errors
                .push(CppBackendError::MissingOperationRepresentation {
                    operation: OperationId(u32::MAX),
                    representation: "foreign region plan",
                });
            return Vec::new();
        };
        let by_id = operands
            .iter()
            .map(|operand| (operand.id, operand))
            .collect::<HashMap<_, _>>();
        let mut body = String::new();
        for fragment in &region.fragments {
            match fragment {
                ForeignFragment::Text(text) => body.push_str(text),
                ForeignFragment::Operand(id) => {
                    let Some(operand) = by_id.get(id).copied() else {
                        continue;
                    };
                    if assembly {
                        body.push_str(&format!("%[corbo_{}]", id.0));
                    } else {
                        body.push_str(&foreign_operand_expression(operand));
                    }
                }
            }
        }
        let foreign = if assembly {
            let inputs = operands
                .iter()
                .map(|operand| {
                    format!(
                        "[corbo_{}] \"r\" ({})",
                        operand.id.0,
                        foreign_operand_expression(operand)
                    )
                })
                .collect::<Vec<_>>()
                .join(", ");
            format!("asm volatile(R\"corbo({body})corbo\" : : {inputs} : \"memory\", \"cc\");")
        } else {
            body
        };
        let mut statements = vec![cpp_ir::Statement::Verbatim(foreign)];
        for output in outputs {
            statements.extend(self.copy_from_pointer(output.result, evaluated_name(output.place)));
        }
        statements
    }

    fn runtime_check(&mut self, value: &RuntimeCheckOperation) -> Vec<cpp_ir::Statement> {
        let check = self.post.runtime_checks[value.requirement.0 as usize].clone();
        let Some(condition) = self.runtime_check_condition(&check) else {
            self.errors
                .push(CppBackendError::MissingOperationRepresentation {
                    operation: value.site.id,
                    representation: "runtime check condition",
                });
            return Vec::new();
        };
        let mut failure = match value.failure {
            FailureContinuation::Abort { .. } => vec![expression_call(
                "corbo_fail",
                vec![cpp_ir::Expression::StringLiteral(
                    b"corbo: runtime check failed".to_vec(),
                )],
            )],
            FailureContinuation::Propagate { value, exit } => {
                let mut statements = self
                    .copy_value_to_expression(cpp_ir::Expression::Name("output".to_owned()), value);
                statements.extend(self.cleanup(exit));
                if self.current_async.is_some() {
                    statements.push(cpp_ir::Statement::Return(Some(
                        cpp_ir::Expression::Boolean(true),
                    )));
                } else {
                    statements.push(cpp_ir::Statement::Return(None));
                }
                statements
            }
        };
        if failure.is_empty() {
            return Vec::new();
        }
        vec![cpp_ir::Statement::If {
            condition: cpp_ir::Expression::Unary {
                operator: cpp_ir::UnaryOperator::LogicalNot,
                operand: Box::new(condition),
            },
            then_block: cpp_ir::Block {
                statements: std::mem::take(&mut failure),
            },
            else_block: None,
        }]
    }

    fn runtime_check_condition(&mut self, check: &RuntimeCheck) -> Option<cpp_ir::Expression> {
        let less = |left, right| cpp_ir::Expression::Binary {
            operator: cpp_ir::BinaryOperator::Less,
            left: Box::new(left),
            right: Box::new(right),
        };
        let less_equal = |left, right| cpp_ir::Expression::Binary {
            operator: cpp_ir::BinaryOperator::LessEqual,
            left: Box::new(left),
            right: Box::new(right),
        };
        match check {
            RuntimeCheck::ZeroDivisor(check) => Some(cpp_ir::Expression::Binary {
                operator: cpp_ir::BinaryOperator::NotEqual,
                left: Box::new(self.typed_value(check.divisor)),
                right: Box::new(cpp_ir::Expression::Unsigned(0)),
            }),
            RuntimeCheck::ShiftCount(check) => Some(less(
                self.typed_value(check.count),
                cpp_ir::Expression::Unsigned(check.width as u128),
            )),
            RuntimeCheck::IndexBounds(check) => Some(less(
                self.typed_value(check.index),
                self.typed_value(check.length),
            )),
            RuntimeCheck::SliceBounds(check) => Some(cpp_ir::Expression::Binary {
                operator: cpp_ir::BinaryOperator::LogicalAnd,
                left: Box::new(less_equal(
                    self.typed_value(check.start),
                    self.typed_value(check.end),
                )),
                right: Box::new(less_equal(
                    self.typed_value(check.end),
                    self.typed_value(check.length),
                )),
            }),
            RuntimeCheck::Utf8Boundary(check) => Some(cpp_ir::Expression::Call {
                callee: Box::new(cpp_ir::Expression::Name(
                    "corbo_valid_text_boundary".to_owned(),
                )),
                arguments: vec![
                    cpp_ir::Expression::Name(evaluated_name(check.source)),
                    self.typed_value(check.boundary),
                ],
            }),
            RuntimeCheck::Variant(check) => self.variant_condition(check.subject, check.variant),
            RuntimeCheck::Unwrap(check) => {
                self.variant_condition(check.subject, check.success_variant)
            }
            RuntimeCheck::PoolCapacity { pool, required, .. } => Some(cpp_ir::Expression::Call {
                callee: Box::new(cpp_ir::Expression::Name("corbo_pool_can_take".to_owned())),
                arguments: vec![
                    reinterpret_pointer("corbo_pool", cpp_ir::Expression::Name(value_name(*pool))),
                    self.typed_value(*required),
                ],
            }),
            RuntimeCheck::IntegerOverflow(check) => self.integer_overflow_condition(check),
            RuntimeCheck::ExactConversion(check) => {
                let TypeDefinition::Numeric(target) =
                    self.post.types.entries[check.target.0 as usize].kind
                else {
                    return None;
                };
                Some(cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name(format!(
                        "corbo_can_exact_numeric<{}>",
                        numeric_spelling(target)
                    ))),
                    arguments: vec![self.typed_value(check.value)],
                })
            }
            RuntimeCheck::Capacity(check) => {
                let descriptor = self.storage_value(check.storage)?;
                Some(cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name(
                        "corbo_region_can_append".to_owned(),
                    )),
                    arguments: vec![
                        reinterpret_pointer(
                            "corbo_region",
                            cpp_ir::Expression::Name(value_name(descriptor)),
                        ),
                        self.typed_value(check.required),
                    ],
                })
            }
            RuntimeCheck::Utf8(check) => {
                let (pointer, length) = self.view_parts(check.bytes)?;
                Some(cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name(
                        "corbo_utf8_bytes_valid".to_owned(),
                    )),
                    arguments: vec![reinterpret_pointer("const unsigned char", pointer), length],
                })
            }
        }
    }

    fn integer_overflow_condition(
        &mut self,
        check: &IntegerOverflowCheck,
    ) -> Option<cpp_ir::Expression> {
        let operation = self
            .post
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .find(|operation| operation.site().id == check.operation)?;
        let call = |name: &str, arguments: Vec<cpp_ir::Expression>| {
            Some(cpp_ir::Expression::Call {
                callee: Box::new(cpp_ir::Expression::Name(name.to_owned())),
                arguments,
            })
        };
        match operation {
            Operation::Add(value) => call(
                "corbo_add_valid",
                vec![self.typed_value(value.left), self.typed_value(value.right)],
            ),
            Operation::Subtract(value) => call(
                "corbo_sub_valid",
                vec![self.typed_value(value.left), self.typed_value(value.right)],
            ),
            Operation::Multiply(value) => call(
                "corbo_mul_valid",
                vec![self.typed_value(value.left), self.typed_value(value.right)],
            ),
            Operation::Divide(value) => call(
                "corbo_div_valid",
                vec![self.typed_value(value.left), self.typed_value(value.right)],
            ),
            Operation::Remainder(value) => call(
                "corbo_div_valid",
                vec![self.typed_value(value.left), self.typed_value(value.right)],
            ),
            Operation::Negate(value) => {
                call("corbo_neg_valid", vec![self.typed_value(value.operand)])
            }
            Operation::AddAssign(value) => call(
                "corbo_add_valid",
                vec![
                    self.typed_value(value.previous),
                    self.typed_value(value.operand),
                ],
            ),
            Operation::SubtractAssign(value) => call(
                "corbo_sub_valid",
                vec![
                    self.typed_value(value.previous),
                    self.typed_value(value.operand),
                ],
            ),
            Operation::MultiplyAssign(value) => call(
                "corbo_mul_valid",
                vec![
                    self.typed_value(value.previous),
                    self.typed_value(value.operand),
                ],
            ),
            Operation::DivideAssign(value) => call(
                "corbo_div_valid",
                vec![
                    self.typed_value(value.previous),
                    self.typed_value(value.operand),
                ],
            ),
            Operation::RemainderAssign(value) => call(
                "corbo_div_valid",
                vec![
                    self.typed_value(value.previous),
                    self.typed_value(value.operand),
                ],
            ),
            _ => None,
        }
    }

    fn storage_value(&self, storage: StorageOriginId) -> Option<ValueId> {
        self.post.values.entries.iter().find_map(|value| {
            let placement = &self.post.values.placement_summaries[value.placement.0 as usize];
            placement.origins.contains(&storage).then_some(value.id)
        })
    }

    fn view_parts(&mut self, value: ValueId) -> Option<(cpp_ir::Expression, cpp_ir::Expression)> {
        let ty = self.post.values.entries[value.0 as usize].ty;
        let Some(NativeDescriptorLayout::View { pointer, length }) = self
            .layouts
            .get(&ty)
            .and_then(|layout| layout.native.clone())
        else {
            self.errors.push(CppBackendError::MissingLayout(ty));
            return None;
        };
        let raw = cpp_ir::Expression::Name(value_name(value));
        Some((
            cpp_ir::Expression::Call {
                callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                arguments: vec![byte_offset(raw.clone(), pointer)],
            },
            self.typed_at(byte_offset(raw, length), self.usize_type()?),
        ))
    }

    fn usize_type(&self) -> Option<TypeId> {
        self.post
            .types
            .entries
            .iter()
            .find(|ty| matches!(ty.kind, TypeDefinition::Numeric(NumericType::Usize)))
            .map(|ty| ty.id)
    }

    fn variant_condition(
        &mut self,
        subject: ValueId,
        variant: VariantId,
    ) -> Option<cpp_ir::Expression> {
        let ty = self.post.values.entries[subject.0 as usize].ty;
        let layout = self.layouts.get(&ty)?.variant.as_ref()?;
        let variant = layout
            .variants
            .iter()
            .find(|candidate| candidate.variant == variant)?;
        Some(cpp_ir::Expression::Binary {
            operator: cpp_ir::BinaryOperator::Equal,
            left: Box::new(cpp_ir::Expression::Call {
                callee: Box::new(cpp_ir::Expression::Name(
                    "corbo_read_discriminant".to_owned(),
                )),
                arguments: vec![
                    cpp_ir::Expression::Name(value_name(subject)),
                    cpp_ir::Expression::Unsigned(layout.discriminant_bytes as u128),
                ],
            }),
            right: Box::new(cpp_ir::Expression::Unsigned(variant.discriminant as u128)),
        })
    }

    fn create_pool(&mut self, value: &CreatePool) -> Vec<cpp_ir::Statement> {
        let backing = self.planned.storage.backings.iter().find_map(|backing| {
            if backing.owner != value.result {
                return None;
            }
            match &backing.kind {
                BackingStorageKind::PoolSlots {
                    state_start,
                    slots_start,
                    occupancy_start,
                    free_slots_start,
                    ..
                } => Some((
                    *state_start,
                    *slots_start,
                    *occupancy_start,
                    *free_slots_start,
                )),
                BackingStorageKind::GrowingRegion { .. } => None,
            }
        });
        let Some((state, slots, occupancy, free_slots)) = backing else {
            self.errors
                .push(CppBackendError::MissingOperationRepresentation {
                    operation: value.site.id,
                    representation: "CreatePool without planned backing",
                });
            return Vec::new();
        };
        let element_size = self.fixed_size(value.element);
        vec![expression_call(
            "corbo_pool_init_planned",
            vec![
                reinterpret_pointer(
                    "corbo_pool",
                    cpp_ir::Expression::Name(value_name(value.result)),
                ),
                reinterpret_pointer("corbo_pool_state", self.stack_address(state)),
                reinterpret_pointer("std::uint8_t", self.stack_address(slots)),
                reinterpret_pointer("std::uint8_t", self.stack_address(occupancy)),
                reinterpret_pointer("std::size_t", self.stack_address(free_slots)),
                self.typed_value(value.capacity),
                cpp_ir::Expression::Unsigned(element_size as u128),
                cpp_ir::Expression::Null,
            ],
        )]
    }

    fn native_operation(&mut self, value: &NativeOperation) -> Vec<cpp_ir::Statement> {
        match &value.kind {
            NativeOperationKind::Construct { ty } => self.construct_native(value, *ty),
            NativeOperationKind::FunctionItem(function) => {
                let layout = self
                    .layouts
                    .get(&self.post.values.entries[value.result.0 as usize].ty)
                    .copied();
                let Some(NativeDescriptorLayout::Callable {
                    function: function_offset,
                    environment,
                }) = layout.and_then(|layout| layout.native.clone())
                else {
                    self.errors
                        .push(CppBackendError::MissingOperationRepresentation {
                            operation: value.site.id,
                            representation: "FunctionItem without callable layout",
                        });
                    return Vec::new();
                };
                vec![
                    expression_call(
                        "corbo_store_pointer",
                        vec![
                            byte_offset(
                                cpp_ir::Expression::Name(value_name(value.result)),
                                function_offset,
                            ),
                            cpp_ir::Expression::ReinterpretCast {
                                ty: cpp_ir::Type::Void.pointer_to(true),
                                value: Box::new(cpp_ir::Expression::Name(function_name(*function))),
                            },
                        ],
                    ),
                    expression_call(
                        "corbo_store_pointer",
                        vec![
                            byte_offset(
                                cpp_ir::Expression::Name(value_name(value.result)),
                                environment,
                            ),
                            cpp_ir::Expression::Null,
                        ],
                    ),
                ]
            }
            NativeOperationKind::Primitive(primitive) => self.primitive_operation(value, primitive),
            NativeOperationKind::RuntimeLaunch {
                kind,
                task,
                function,
            } => self.runtime_launch(value, *kind, *task, *function),
            NativeOperationKind::Join { handle } => {
                self.join_value(value.site.id, value.result, *handle)
            }
            NativeOperationKind::Collection {
                collection,
                operation,
                position,
            } => self.collection_operation(value, *collection, *operation, position.as_ref()),
        }
    }

    fn collection_operation(
        &mut self,
        value: &NativeOperation,
        collection: CollectionId,
        operation: CollectionOperationKind,
        _position: Option<&PositionSelector>,
    ) -> Vec<cpp_ir::Statement> {
        let collection_data = self.post.objects.collections[collection.0 as usize].clone();
        let descriptor = match collection_data.descriptor {
            CollectionDescriptor::Address(address) => self
                .value_for_entity(&EntityId::Address(address))
                .map(|value| cpp_ir::Expression::Name(value_name(value))),
            CollectionDescriptor::Place(place) => self.place_address(place),
        };
        let Some(descriptor) = descriptor else {
            self.errors
                .push(CppBackendError::MissingOperationRepresentation {
                    operation: value.site.id,
                    representation: "collection descriptor",
                });
            return Vec::new();
        };
        match self.post.types.entries[collection_data.ty.0 as usize].kind {
            TypeDefinition::GrowingSequence { element } => {
                self.vector_operation(value, descriptor, element, operation)
            }
            TypeDefinition::GrowingString => {
                let byte = self
                    .post
                    .types
                    .entries
                    .iter()
                    .find(|ty| matches!(ty.kind, TypeDefinition::Numeric(NumericType::U8)))
                    .map(|ty| ty.id);
                let Some(byte) = byte else {
                    self.errors
                        .push(CppBackendError::MissingOperationRepresentation {
                            operation: value.site.id,
                            representation: "u8 type for String collection",
                        });
                    return Vec::new();
                };
                self.vector_operation(value, descriptor, byte, operation)
            }
            TypeDefinition::KeyedCollection {
                key,
                value: element,
            } => self.map_operation(value, descriptor, key, element, operation),
            _ => {
                self.errors
                    .push(CppBackendError::MissingOperationRepresentation {
                        operation: value.site.id,
                        representation: "collection operation on non-collection type",
                    });
                Vec::new()
            }
        }
    }

    fn runtime_launch(
        &mut self,
        operation: &NativeOperation,
        kind: RuntimeLaunchKind,
        task: ValueId,
        _function: FunctionInstanceId,
    ) -> Vec<cpp_ir::Statement> {
        let task_ty = self.post.values.entries[task.0 as usize].ty;
        let handle_ty = self.post.values.entries[operation.result.0 as usize].ty;
        let Some(NativeDescriptorLayout::ExecutionHandle { state }) = self
            .layouts
            .get(&handle_ty)
            .and_then(|layout| layout.native.clone())
        else {
            self.errors.push(CppBackendError::MissingLayout(handle_ty));
            return Vec::new();
        };
        let Some(task_layout) = self.layouts.get(&task_ty).copied() else {
            self.errors.push(CppBackendError::MissingLayout(task_ty));
            return Vec::new();
        };
        let LayoutSize::Fixed(state_bytes) = task_layout.size else {
            self.errors
                .push(CppBackendError::RuntimeSizedLayout(task_ty));
            return Vec::new();
        };
        let (output_ty, poll) = match self.post.types.entries[task_ty.0 as usize].kind {
            TypeDefinition::Future { body, result, .. } => {
                let Some(frame) = self
                    .post
                    .async_frames
                    .iter()
                    .find(|frame| frame.body == body)
                else {
                    self.errors
                        .push(CppBackendError::MissingOperationRepresentation {
                            operation: operation.site.id,
                            representation: "runtime launch future frame",
                        });
                    return Vec::new();
                };
                (result, async_poll_name(frame.function))
            }
            TypeDefinition::Closure { signature, .. } => (
                self.post.declarations.signatures[signature.0 as usize].result,
                format!("corbo_launch_poll_{}", operation.site.id.0),
            ),
            TypeDefinition::Callable(signature) => (
                self.post.declarations.signatures[signature.0 as usize].result,
                format!("corbo_launch_poll_{}", operation.site.id.0),
            ),
            _ => {
                self.errors
                    .push(CppBackendError::MissingOperationRepresentation {
                        operation: operation.site.id,
                        representation: "runtime launch task type",
                    });
                return Vec::new();
            }
        };
        let output_bytes = self.fixed_size(output_ty);
        let destroy = self
            .post
            .contracts
            .destructors
            .iter()
            .find(|destructor| destructor.ty == task_ty)
            .map(|destructor| cpp_ir::Expression::Name(destructor_name(destructor.id)))
            .unwrap_or(cpp_ir::Expression::Null);
        let local = format!("launched_task_{}", operation.site.id.0);
        let mut statements = vec![cpp_ir::Statement::Declare {
            ty: cpp_ir::Type::Named("corbo_task".to_owned()).pointer_to(true),
            name: local.clone(),
            initializer: Some(cpp_ir::Expression::Call {
                callee: Box::new(cpp_ir::Expression::Name(
                    "corbo_task_from_future".to_owned(),
                )),
                arguments: vec![
                    cpp_ir::Expression::Name(value_name(task)),
                    cpp_ir::Expression::Unsigned(state_bytes as u128),
                    cpp_ir::Expression::Unsigned(task_layout.alignment as u128),
                    cpp_ir::Expression::Unsigned(output_bytes as u128),
                    cpp_ir::Expression::Name(poll),
                    destroy,
                ],
            }),
        }];
        statements.push(expression_call(
            "corbo_store_pointer",
            vec![
                byte_offset(
                    cpp_ir::Expression::Name(value_name(operation.result)),
                    state,
                ),
                cpp_ir::Expression::Name(local.clone()),
            ],
        ));
        statements.push(expression_call(
            match kind {
                RuntimeLaunchKind::Spawn => "corbo_task_spawn",
                RuntimeLaunchKind::SpawnBlocking | RuntimeLaunchKind::Thread => "corbo_task_thread",
            },
            vec![cpp_ir::Expression::Name(local)],
        ));
        statements
    }

    fn join_value(
        &mut self,
        operation: OperationId,
        result: ValueId,
        handle: ValueId,
    ) -> Vec<cpp_ir::Statement> {
        let handle_ty = self.post.values.entries[handle.0 as usize].ty;
        let TypeDefinition::ExecutionHandle {
            result: output_ty, ..
        } = self.post.types.entries[handle_ty.0 as usize].kind
        else {
            self.errors
                .push(CppBackendError::MissingOperationRepresentation {
                    operation,
                    representation: "join of non-handle",
                });
            return Vec::new();
        };
        let Some(NativeDescriptorLayout::ExecutionHandle { state }) = self
            .layouts
            .get(&handle_ty)
            .and_then(|layout| layout.native.clone())
        else {
            self.errors.push(CppBackendError::MissingLayout(handle_ty));
            return Vec::new();
        };
        let Some((ok, ok_field, error, error_field)) = self.result_shape(result, output_ty) else {
            return Vec::new();
        };
        let result_ty = self.post.values.entries[result.0 as usize].ty;
        let Some(ok_offset) = self.component_offset(
            result_ty,
            Some(ok),
            &PositionSelector::VariantField {
                variant: ok,
                field: ok_field,
            },
        ) else {
            return Vec::new();
        };
        let Some(error_offset) = self.component_offset(
            result_ty,
            Some(error),
            &PositionSelector::VariantField {
                variant: error,
                field: error_field,
            },
        ) else {
            return Vec::new();
        };
        let task = format!("joined_task_{}", operation.0);
        let result = cpp_ir::Expression::Name(value_name(result));
        let mut statements = vec![cpp_ir::Statement::Declare {
            ty: cpp_ir::Type::Named("corbo_task".to_owned()).pointer_to(true),
            name: task.clone(),
            initializer: Some(cpp_ir::Expression::ReinterpretCast {
                ty: cpp_ir::Type::Named("corbo_task".to_owned()).pointer_to(true),
                value: Box::new(cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                    arguments: vec![byte_offset(
                        cpp_ir::Expression::Name(value_name(handle)),
                        state,
                    )],
                }),
            }),
        }];
        statements.push(expression_call(
            "corbo_task_join",
            vec![cpp_ir::Expression::Name(task.clone())],
        ));
        let mut success = self.write_variant_tag(result.clone(), result_ty, ok);
        success.push(cpp_ir::Statement::CopyBytes {
            destination: byte_offset(result.clone(), ok_offset),
            source: cpp_ir::Expression::Member {
                base: Box::new(cpp_ir::Expression::Name(task.clone())),
                member: "result".to_owned(),
                through_pointer: true,
            },
            bytes: cpp_ir::Expression::Unsigned(self.fixed_size(output_ty) as u128),
        });
        let error_ty = self.post.declarations.fields[error_field.0 as usize].ty;
        let error_variant = self
            .post
            .declarations
            .variants
            .iter()
            .find(|variant| variant.owner == error_ty)
            .map(|variant| variant.id);
        let mut failure = self.write_variant_tag(result.clone(), result_ty, error);
        if let Some(error_variant) = error_variant {
            failure.extend(self.write_variant_tag(
                byte_offset(result.clone(), error_offset),
                error_ty,
                error_variant,
            ));
        }
        statements.push(cpp_ir::Statement::If {
            condition: cpp_ir::Expression::Member {
                base: Box::new(cpp_ir::Expression::Name(task.clone())),
                member: "failed".to_owned(),
                through_pointer: true,
            },
            then_block: cpp_ir::Block {
                statements: failure,
            },
            else_block: Some(cpp_ir::Block {
                statements: success,
            }),
        });
        statements.push(expression_call(
            "corbo_task_release",
            vec![cpp_ir::Expression::Name(task)],
        ));
        statements
    }

    fn result_shape(
        &mut self,
        result: ValueId,
        success_ty: TypeId,
    ) -> Option<(VariantId, FieldId, VariantId, FieldId)> {
        let ty = self.post.values.entries[result.0 as usize].ty;
        let mut variants = self
            .post
            .declarations
            .variants
            .iter()
            .filter(|variant| variant.owner == ty && variant.fields.len() == 1);
        let first = variants.next()?;
        let second = variants.next()?;
        let first_ty = self.post.declarations.fields[first.fields[0].0 as usize].ty;
        if first_ty == success_ty {
            Some((first.id, first.fields[0], second.id, second.fields[0]))
        } else {
            Some((second.id, second.fields[0], first.id, first.fields[0]))
        }
    }

    fn primitive_operation(
        &mut self,
        operation: &NativeOperation,
        primitive: &PrimitiveOperation,
    ) -> Vec<cpp_ir::Statement> {
        match primitive {
            PrimitiveOperation::View {
                source,
                target: _,
                mutable: _,
            } => {
                let result_ty = self.post.values.entries[operation.result.0 as usize].ty;
                match self
                    .layouts
                    .get(&result_ty)
                    .and_then(|layout| layout.native.clone())
                {
                    Some(NativeDescriptorLayout::ThinReference { pointer }) => {
                        vec![expression_call(
                            "corbo_store_pointer",
                            vec![
                                byte_offset(
                                    cpp_ir::Expression::Name(value_name(operation.result)),
                                    pointer,
                                ),
                                cpp_ir::Expression::Name(evaluated_name(*source)),
                            ],
                        )]
                    }
                    Some(NativeDescriptorLayout::View { .. }) => {
                        vec![cpp_ir::Statement::CopyBytes {
                            destination: cpp_ir::Expression::Name(value_name(operation.result)),
                            source: cpp_ir::Expression::Name(evaluated_name(*source)),
                            bytes: cpp_ir::Expression::Unsigned(self.fixed_size(result_ty) as u128),
                        }]
                    }
                    _ => {
                        self.errors.push(CppBackendError::MissingLayout(result_ty));
                        Vec::new()
                    }
                }
            }
            PrimitiveOperation::TryNumericConversion { source, target } => {
                self.try_numeric_conversion(operation, *source, *target)
            }
            PrimitiveOperation::ValidateUtf8 { bytes, error } => {
                self.validate_utf8(operation, *bytes, *error)
            }
            PrimitiveOperation::Runtime {
                kind,
                suspension,
                process_args_errors,
            } => self.runtime_primitive(operation, *kind, *suspension, *process_args_errors),
        }
    }

    fn try_numeric_conversion(
        &mut self,
        operation: &NativeOperation,
        source: ValueId,
        target: TypeId,
    ) -> Vec<cpp_ir::Statement> {
        let source_ty = self.post.values.entries[source.0 as usize].ty;
        let Some((ok, ok_field, error, _error_field)) = self.result_shape(operation.result, target)
        else {
            return Vec::new();
        };
        let result_ty = self.post.values.entries[operation.result.0 as usize].ty;
        let Some(ok_offset) = self.component_offset(
            result_ty,
            Some(ok),
            &PositionSelector::VariantField {
                variant: ok,
                field: ok_field,
            },
        ) else {
            return Vec::new();
        };
        let result = cpp_ir::Expression::Name(value_name(operation.result));
        let target_cpp = cpp_type_spelling(&self.post.types.entries[target.0 as usize].kind);
        let source_cpp = cpp_type_spelling(&self.post.types.entries[source_ty.0 as usize].kind);
        let exact = cpp_ir::Expression::Call {
            callee: Box::new(cpp_ir::Expression::Name(format!(
                "corbo_exact_numeric<{target_cpp}, {source_cpp}>"
            ))),
            arguments: vec![
                self.typed_value(source),
                cpp_ir::Expression::ReinterpretCast {
                    ty: cpp_ir::Type::Named(type_name(target)).pointer_to(true),
                    value: Box::new(byte_offset(result.clone(), ok_offset)),
                },
            ],
        };
        vec![cpp_ir::Statement::If {
            condition: exact,
            then_block: cpp_ir::Block {
                statements: self.write_variant_tag(result.clone(), result_ty, ok),
            },
            else_block: Some(cpp_ir::Block {
                statements: self.write_variant_tag(result, result_ty, error),
            }),
        }]
    }

    fn validate_utf8(
        &mut self,
        operation: &NativeOperation,
        bytes: ValueId,
        error_ty: TypeId,
    ) -> Vec<cpp_ir::Statement> {
        let bytes_ty = self.post.values.entries[bytes.0 as usize].ty;
        let Some(NativeDescriptorLayout::View { pointer, length }) = self
            .layouts
            .get(&bytes_ty)
            .and_then(|layout| layout.native.clone())
        else {
            self.errors.push(CppBackendError::MissingLayout(bytes_ty));
            return Vec::new();
        };
        let Some((ok, ok_field, error, error_field)) =
            self.result_shape_by_error(operation.result, error_ty)
        else {
            return Vec::new();
        };
        let result_ty = self.post.values.entries[operation.result.0 as usize].ty;
        let Some(ok_offset) = self.component_offset(
            result_ty,
            Some(ok),
            &PositionSelector::VariantField {
                variant: ok,
                field: ok_field,
            },
        ) else {
            return Vec::new();
        };
        let result = cpp_ir::Expression::Name(value_name(operation.result));
        let data = cpp_ir::Expression::Call {
            callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
            arguments: vec![byte_offset(
                cpp_ir::Expression::Name(value_name(bytes)),
                pointer,
            )],
        };
        let count = self.size_at(byte_offset(
            cpp_ir::Expression::Name(value_name(bytes)),
            length,
        ));
        let valid = cpp_ir::Expression::Call {
            callee: Box::new(cpp_ir::Expression::Name(
                "corbo_utf8_bytes_valid".to_owned(),
            )),
            arguments: vec![data.clone(), count.clone()],
        };
        let success_ty = self.post.declarations.fields[ok_field.0 as usize].ty;
        let Some(NativeDescriptorLayout::View {
            pointer: view_pointer,
            length: view_length,
        }) = self
            .layouts
            .get(&success_ty)
            .and_then(|layout| layout.native.clone())
        else {
            self.errors.push(CppBackendError::MissingLayout(success_ty));
            return Vec::new();
        };
        let mut yes = self.write_variant_tag(result.clone(), result_ty, ok);
        yes.push(expression_call(
            "corbo_store_pointer",
            vec![byte_offset(result.clone(), ok_offset + view_pointer), data],
        ));
        yes.push(cpp_ir::Statement::Assign {
            destination: self.size_at(byte_offset(result.clone(), ok_offset + view_length)),
            source: count,
        });
        let mut no = self.write_variant_tag(result.clone(), result_ty, error);
        no.push(cpp_ir::Statement::ZeroBytes {
            destination: byte_offset(
                result,
                self.component_offset(
                    result_ty,
                    Some(error),
                    &PositionSelector::VariantField {
                        variant: error,
                        field: error_field,
                    },
                )
                .unwrap_or(0),
            ),
            bytes: cpp_ir::Expression::Unsigned(self.fixed_size(error_ty) as u128),
        });
        vec![cpp_ir::Statement::If {
            condition: valid,
            then_block: cpp_ir::Block { statements: yes },
            else_block: Some(cpp_ir::Block { statements: no }),
        }]
    }

    fn result_shape_by_error(
        &mut self,
        result: ValueId,
        error_ty: TypeId,
    ) -> Option<(VariantId, FieldId, VariantId, FieldId)> {
        let ty = self.post.values.entries[result.0 as usize].ty;
        let mut variants = self
            .post
            .declarations
            .variants
            .iter()
            .filter(|variant| variant.owner == ty && variant.fields.len() == 1);
        let first = variants.next()?;
        let second = variants.next()?;
        let first_ty = self.post.declarations.fields[first.fields[0].0 as usize].ty;
        if first_ty == error_ty {
            Some((second.id, second.fields[0], first.id, first.fields[0]))
        } else {
            Some((first.id, first.fields[0], second.id, second.fields[0]))
        }
    }

    fn runtime_primitive(
        &mut self,
        operation: &NativeOperation,
        kind: RuntimePrimitiveKind,
        suspension: Option<SuspensionId>,
        process_args_errors: Option<(VariantId, VariantId)>,
    ) -> Vec<cpp_ir::Statement> {
        let argument = |index: usize| operation.arguments.get(index).map(|value| value.value);
        if kind == RuntimePrimitiveKind::ProcessArgs {
            return self.process_args(operation, process_args_errors);
        }
        let waiter = cpp_ir::Expression::Unary {
            operator: cpp_ir::UnaryOperator::AddressOf,
            operand: Box::new(cpp_ir::Expression::Member {
                base: Box::new(cpp_ir::Expression::Member {
                    base: Box::new(cpp_ir::Expression::Name("context".to_owned())),
                    member: "task".to_owned(),
                    through_pointer: true,
                }),
                member: "child_waiter".to_owned(),
                through_pointer: true,
            }),
        };
        let waker = cpp_ir::Expression::Member {
            base: Box::new(cpp_ir::Expression::Name("context".to_owned())),
            member: "waker".to_owned(),
            through_pointer: true,
        };
        let mut ready = None;
        let mut statements = Vec::new();
        match kind {
            RuntimePrimitiveKind::WaitMutex => {
                let Some(raw) = argument(0) else {
                    return Vec::new();
                };
                ready = Some(cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name("corbo_mutex_poll".to_owned())),
                    arguments: vec![self.typed_value(raw), waiter, waker],
                });
            }
            RuntimePrimitiveKind::WaitChannel => {
                let (Some(raw), Some(epoch), Some(sending)) =
                    (argument(0), argument(1), argument(2))
                else {
                    return Vec::new();
                };
                ready = Some(cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name("corbo_channel_poll".to_owned())),
                    arguments: vec![
                        self.typed_value(raw),
                        waiter,
                        waker,
                        self.typed_value(epoch),
                        self.typed_value(sending),
                    ],
                });
            }
            RuntimePrimitiveKind::WaitSocket => {
                let (Some(socket), Some(write)) = (argument(0), argument(1)) else {
                    return Vec::new();
                };
                ready = Some(cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name("corbo_socket_poll".to_owned())),
                    arguments: vec![
                        self.typed_value(socket),
                        waiter,
                        waker,
                        self.typed_value(write),
                    ],
                });
            }
            RuntimePrimitiveKind::AttachSocket => {
                let Some(socket) = argument(0) else {
                    return Vec::new();
                };
                statements.push(cpp_ir::Statement::Assign {
                    destination: self.typed_value(operation.result),
                    source: cpp_ir::Expression::Call {
                        callee: Box::new(cpp_ir::Expression::Name(
                            "corbo_socket_attach".to_owned(),
                        )),
                        arguments: vec![self.typed_value(socket)],
                    },
                });
            }
            RuntimePrimitiveKind::CompleteSocket => {
                let (Some(socket), Some(address)) = (argument(0), argument(1)) else {
                    return Vec::new();
                };
                ready = Some(cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name("corbo_socket_complete".to_owned())),
                    arguments: vec![
                        self.typed_value(socket),
                        self.typed_value(address),
                        cpp_ir::Expression::Name("context".to_owned()),
                        waiter,
                        cpp_ir::Expression::Unary {
                            operator: cpp_ir::UnaryOperator::AddressOf,
                            operand: Box::new(self.typed_value(operation.result)),
                        },
                    ],
                });
            }
            RuntimePrimitiveKind::ProcessArgs => unreachable!(),
        }
        if let Some(ready) = ready {
            let ready_name = runtime_ready_name(operation.site.id);
            statements.push(cpp_ir::Statement::Assign {
                destination: cpp_ir::Expression::Name(ready_name.clone()),
                source: ready,
            });
            if !matches!(kind, RuntimePrimitiveKind::CompleteSocket) {
                statements.push(cpp_ir::Statement::Assign {
                    destination: self.typed_value(operation.result),
                    source: cpp_ir::Expression::Signed(0),
                });
            }
            if let Some(suspension) = suspension {
                let mut suspend = self.set_async_state(suspension);
                suspend.push(cpp_ir::Statement::Return(Some(
                    cpp_ir::Expression::Boolean(false),
                )));
                statements.push(cpp_ir::Statement::If {
                    condition: cpp_ir::Expression::Unary {
                        operator: cpp_ir::UnaryOperator::LogicalNot,
                        operand: Box::new(cpp_ir::Expression::Name(ready_name)),
                    },
                    then_block: cpp_ir::Block {
                        statements: suspend,
                    },
                    else_block: None,
                });
            }
        }
        statements
    }

    fn process_args(
        &mut self,
        operation: &NativeOperation,
        errors: Option<(VariantId, VariantId)>,
    ) -> Vec<cpp_ir::Statement> {
        let Some((invalid_utf8, unavailable)) = errors else {
            self.errors
                .push(CppBackendError::MissingOperationRepresentation {
                    operation: operation.site.id,
                    representation: "resolved process argument error variants",
                });
            return Vec::new();
        };
        let error_ty = self.post.declarations.variants[invalid_utf8.0 as usize].owner;
        let Some((ok, ok_field, error, error_field)) =
            self.result_shape_by_error(operation.result, error_ty)
        else {
            return Vec::new();
        };
        let result_ty = self.post.values.entries[operation.result.0 as usize].ty;
        let Some(ok_offset) = self.component_offset(
            result_ty,
            Some(ok),
            &PositionSelector::VariantField {
                variant: ok,
                field: ok_field,
            },
        ) else {
            return Vec::new();
        };
        let Some(error_offset) = self.component_offset(
            result_ty,
            Some(error),
            &PositionSelector::VariantField {
                variant: error,
                field: error_field,
            },
        ) else {
            return Vec::new();
        };
        let success_ty = self.post.declarations.fields[ok_field.0 as usize].ty;
        let Some(NativeDescriptorLayout::View { pointer, length }) = self
            .layouts
            .get(&success_ty)
            .and_then(|layout| layout.native.clone())
        else {
            self.errors.push(CppBackendError::MissingLayout(success_ty));
            return Vec::new();
        };
        let result = cpp_ir::Expression::Name(value_name(operation.result));
        let payload = byte_offset(result.clone(), ok_offset);
        let mut success = self.write_variant_tag(result.clone(), result_ty, ok);
        success.push(expression_call(
            "corbo_store_pointer",
            vec![
                byte_offset(payload.clone(), pointer),
                cpp_ir::Expression::Member {
                    base: Box::new(cpp_ir::Expression::Name("corbo_arguments".to_owned())),
                    member: "data".to_owned(),
                    through_pointer: false,
                },
            ],
        ));
        success.push(cpp_ir::Statement::Assign {
            destination: self.size_at(byte_offset(payload, length)),
            source: cpp_ir::Expression::Member {
                base: Box::new(cpp_ir::Expression::Name("corbo_arguments".to_owned())),
                member: "len".to_owned(),
                through_pointer: false,
            },
        });
        let error_payload = byte_offset(result.clone(), error_offset);
        let mut failure = self.write_variant_tag(result.clone(), result_ty, error);
        failure.push(cpp_ir::Statement::If {
            condition: cpp_ir::Expression::Binary {
                operator: cpp_ir::BinaryOperator::Equal,
                left: Box::new(cpp_ir::Expression::Member {
                    base: Box::new(cpp_ir::Expression::Name("corbo_arguments".to_owned())),
                    member: "status".to_owned(),
                    through_pointer: false,
                }),
                right: Box::new(cpp_ir::Expression::Unsigned(1)),
            },
            then_block: cpp_ir::Block {
                statements: self.write_variant_tag(error_payload.clone(), error_ty, invalid_utf8),
            },
            else_block: Some(cpp_ir::Block {
                statements: self.write_variant_tag(error_payload, error_ty, unavailable),
            }),
        });
        vec![cpp_ir::Statement::If {
            condition: cpp_ir::Expression::Binary {
                operator: cpp_ir::BinaryOperator::Equal,
                left: Box::new(cpp_ir::Expression::Member {
                    base: Box::new(cpp_ir::Expression::Name("corbo_arguments".to_owned())),
                    member: "status".to_owned(),
                    through_pointer: false,
                }),
                right: Box::new(cpp_ir::Expression::Unsigned(0)),
            },
            then_block: cpp_ir::Block {
                statements: success,
            },
            else_block: Some(cpp_ir::Block {
                statements: failure,
            }),
        }]
    }

    fn vector_operation(
        &mut self,
        operation: &NativeOperation,
        descriptor: cpp_ir::Expression,
        element: TypeId,
        kind: CollectionOperationKind,
    ) -> Vec<cpp_ir::Statement> {
        let region = reinterpret_pointer("corbo_region", descriptor.clone());
        let argument = |index: usize| operation.arguments.get(index).map(|value| value.value);
        match kind {
            CollectionOperationKind::Length => vec![cpp_ir::Statement::Assign {
                destination: self.typed_value(operation.result),
                source: cpp_ir::Expression::Member {
                    base: Box::new(region),
                    member: "len".to_owned(),
                    through_pointer: true,
                },
            }],
            CollectionOperationKind::Clear => {
                vec![expression_call("corbo_region_clear", vec![region])]
            }
            CollectionOperationKind::Push => {
                let Some(input) = argument(0) else {
                    return Vec::new();
                };
                vec![cpp_ir::Statement::CopyBytes {
                    destination: cpp_ir::Expression::Call {
                        callee: Box::new(cpp_ir::Expression::Name(
                            "corbo_region_append".to_owned(),
                        )),
                        arguments: vec![region, cpp_ir::Expression::Unsigned(1)],
                    },
                    source: cpp_ir::Expression::Name(value_name(input)),
                    bytes: cpp_ir::Expression::Unsigned(self.fixed_size(element) as u128),
                }]
            }
            CollectionOperationKind::Pop => {
                let present = format!("collection_present_{}", operation.site.id.0);
                let Some((some, some_field, none)) = self.option_shape(operation.result) else {
                    return Vec::new();
                };
                let result_ty = self.post.values.entries[operation.result.0 as usize].ty;
                let Some(payload_offset) = self.component_offset(
                    result_ty,
                    Some(some),
                    &PositionSelector::VariantField {
                        variant: some,
                        field: some_field,
                    },
                ) else {
                    return Vec::new();
                };
                let result = cpp_ir::Expression::Name(value_name(operation.result));
                let mut statements = vec![cpp_ir::Statement::Declare {
                    ty: cpp_ir::Type::Bool,
                    name: present.clone(),
                    initializer: Some(cpp_ir::Expression::Call {
                        callee: Box::new(cpp_ir::Expression::Name("vector_pop".to_owned())),
                        arguments: vec![region, byte_offset(result.clone(), payload_offset)],
                    }),
                }];
                statements.push(cpp_ir::Statement::If {
                    condition: cpp_ir::Expression::Name(present),
                    then_block: cpp_ir::Block {
                        statements: self.write_variant_tag(result.clone(), result_ty, some),
                    },
                    else_block: Some(cpp_ir::Block {
                        statements: self.write_variant_tag(result, result_ty, none),
                    }),
                });
                statements
            }
            CollectionOperationKind::Remove => {
                let Some(index) = argument(0) else {
                    return Vec::new();
                };
                vec![expression_call(
                    "vector_remove",
                    vec![
                        region,
                        self.typed_value(index),
                        cpp_ir::Expression::Name(value_name(operation.result)),
                    ],
                )]
            }
            CollectionOperationKind::Replace => {
                let (Some(index), Some(input)) = (argument(0), argument(1)) else {
                    return Vec::new();
                };
                vec![expression_call(
                    "vector_replace",
                    vec![
                        region,
                        self.typed_value(index),
                        cpp_ir::Expression::Name(value_name(input)),
                        cpp_ir::Expression::Name(value_name(operation.result)),
                    ],
                )]
            }
            CollectionOperationKind::Insert => {
                let (Some(index), Some(input)) = (argument(0), argument(1)) else {
                    return Vec::new();
                };
                vec![expression_call(
                    "vector_insert",
                    vec![
                        region,
                        self.typed_value(index),
                        cpp_ir::Expression::Name(value_name(input)),
                    ],
                )]
            }
            CollectionOperationKind::Get | CollectionOperationKind::GetMutable => {
                let Some(index) = argument(0) else {
                    return Vec::new();
                };
                let pointer = cpp_ir::Expression::ByteOffset {
                    base: Box::new(cpp_ir::Expression::Member {
                        base: Box::new(region.clone()),
                        member: "data".to_owned(),
                        through_pointer: true,
                    }),
                    bytes: Box::new(cpp_ir::Expression::Binary {
                        operator: cpp_ir::BinaryOperator::Multiply,
                        left: Box::new(self.typed_value(index)),
                        right: Box::new(cpp_ir::Expression::Unsigned(
                            self.fixed_size(element) as u128
                        )),
                    }),
                };
                let in_bounds = cpp_ir::Expression::Binary {
                    operator: cpp_ir::BinaryOperator::Less,
                    left: Box::new(self.typed_value(index)),
                    right: Box::new(cpp_ir::Expression::Member {
                        base: Box::new(region),
                        member: "len".to_owned(),
                        through_pointer: true,
                    }),
                };
                self.optional_reference(operation.result, pointer, in_bounds)
            }
            CollectionOperationKind::View | CollectionOperationKind::MutableView => {
                self.write_view_from_region(operation.result, region)
            }
        }
    }

    fn map_operation(
        &mut self,
        operation: &NativeOperation,
        descriptor: cpp_ir::Expression,
        _key: TypeId,
        _element: TypeId,
        kind: CollectionOperationKind,
    ) -> Vec<cpp_ir::Statement> {
        let map = reinterpret_pointer("corbo_map", descriptor);
        let argument = |index: usize| operation.arguments.get(index).map(|value| value.value);
        match kind {
            CollectionOperationKind::Length => vec![cpp_ir::Statement::Assign {
                destination: self.typed_value(operation.result),
                source: cpp_ir::Expression::Member {
                    base: Box::new(map),
                    member: "count".to_owned(),
                    through_pointer: true,
                },
            }],
            CollectionOperationKind::Clear => vec![expression_call("corbo_map_clear", vec![map])],
            CollectionOperationKind::Get | CollectionOperationKind::GetMutable => {
                let Some(key) = argument(0) else {
                    return Vec::new();
                };
                let pointer = cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name("corbo_map_get".to_owned())),
                    arguments: vec![map, self.map_key(key)],
                };
                let present = cpp_ir::Expression::Binary {
                    operator: cpp_ir::BinaryOperator::NotEqual,
                    left: Box::new(pointer.clone()),
                    right: Box::new(cpp_ir::Expression::Null),
                };
                self.optional_reference(operation.result, pointer, present)
            }
            CollectionOperationKind::Remove => {
                let Some(key) = argument(0) else {
                    return Vec::new();
                };
                self.map_optional_payload(operation, map, key, None, "corbo_map_remove")
            }
            CollectionOperationKind::Insert => {
                let (Some(key), Some(input)) = (argument(0), argument(1)) else {
                    return Vec::new();
                };
                self.map_optional_payload(operation, map, key, Some(input), "corbo_map_insert")
            }
            CollectionOperationKind::Push
            | CollectionOperationKind::Pop
            | CollectionOperationKind::Replace
            | CollectionOperationKind::View
            | CollectionOperationKind::MutableView => {
                self.errors
                    .push(CppBackendError::MissingOperationRepresentation {
                        operation: operation.site.id,
                        representation: "invalid keyed collection operation",
                    });
                Vec::new()
            }
        }
    }

    fn option_shape(&mut self, result: ValueId) -> Option<(VariantId, FieldId, VariantId)> {
        let ty = self.post.values.entries[result.0 as usize].ty;
        let variants = self
            .post
            .declarations
            .variants
            .iter()
            .filter(|variant| variant.owner == ty)
            .collect::<Vec<_>>();
        let some = variants.iter().find(|variant| variant.fields.len() == 1)?;
        let none = variants.iter().find(|variant| variant.fields.is_empty())?;
        Some((some.id, some.fields[0], none.id))
    }

    fn optional_reference(
        &mut self,
        result: ValueId,
        pointer: cpp_ir::Expression,
        present: cpp_ir::Expression,
    ) -> Vec<cpp_ir::Statement> {
        let Some((some, field, none)) = self.option_shape(result) else {
            return Vec::new();
        };
        let result_ty = self.post.values.entries[result.0 as usize].ty;
        let Some(offset) = self.component_offset(
            result_ty,
            Some(some),
            &PositionSelector::VariantField {
                variant: some,
                field,
            },
        ) else {
            return Vec::new();
        };
        let result_address = cpp_ir::Expression::Name(value_name(result));
        let mut yes = self.write_variant_tag(result_address.clone(), result_ty, some);
        yes.push(expression_call(
            "corbo_store_pointer",
            vec![byte_offset(result_address.clone(), offset), pointer],
        ));
        vec![cpp_ir::Statement::If {
            condition: present,
            then_block: cpp_ir::Block { statements: yes },
            else_block: Some(cpp_ir::Block {
                statements: self.write_variant_tag(result_address, result_ty, none),
            }),
        }]
    }

    fn map_optional_payload(
        &mut self,
        operation: &NativeOperation,
        map: cpp_ir::Expression,
        key: ValueId,
        input: Option<ValueId>,
        function: &str,
    ) -> Vec<cpp_ir::Statement> {
        let Some((some, field, none)) = self.option_shape(operation.result) else {
            return Vec::new();
        };
        let result_ty = self.post.values.entries[operation.result.0 as usize].ty;
        let Some(offset) = self.component_offset(
            result_ty,
            Some(some),
            &PositionSelector::VariantField {
                variant: some,
                field,
            },
        ) else {
            return Vec::new();
        };
        let result = cpp_ir::Expression::Name(value_name(operation.result));
        let mut arguments = vec![map, self.map_key(key)];
        if let Some(input) = input {
            arguments.push(cpp_ir::Expression::Name(value_name(input)));
        }
        arguments.push(byte_offset(result.clone(), offset));
        let present = format!("collection_present_{}", operation.site.id.0);
        let mut statements = vec![cpp_ir::Statement::Declare {
            ty: cpp_ir::Type::Bool,
            name: present.clone(),
            initializer: Some(cpp_ir::Expression::Call {
                callee: Box::new(cpp_ir::Expression::Name(function.to_owned())),
                arguments,
            }),
        }];
        statements.push(cpp_ir::Statement::If {
            condition: cpp_ir::Expression::Name(present),
            then_block: cpp_ir::Block {
                statements: self.write_variant_tag(result.clone(), result_ty, some),
            },
            else_block: Some(cpp_ir::Block {
                statements: self.write_variant_tag(result, result_ty, none),
            }),
        });
        statements
    }

    fn map_key(&self, reference: ValueId) -> cpp_ir::Expression {
        let reference_ty = self.post.values.entries[reference.0 as usize].ty;
        let target = match self.post.types.entries[reference_ty.0 as usize].kind {
            TypeDefinition::Reference { target, .. } => target,
            _ => return self.typed_value(reference),
        };
        cpp_ir::Expression::Cast {
            ty: cpp_ir::Type::Unsigned { bits: 64 },
            value: Box::new(cpp_ir::Expression::Unary {
                operator: cpp_ir::UnaryOperator::Dereference,
                operand: Box::new(cpp_ir::Expression::ReinterpretCast {
                    ty: cpp_ir::Type::Named(type_name(target)).pointer_to(false),
                    value: Box::new(cpp_ir::Expression::Call {
                        callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                        arguments: vec![cpp_ir::Expression::Name(value_name(reference))],
                    }),
                }),
            }),
        }
    }

    fn write_view_from_region(
        &mut self,
        result: ValueId,
        region: cpp_ir::Expression,
    ) -> Vec<cpp_ir::Statement> {
        let ty = self.post.values.entries[result.0 as usize].ty;
        let Some(NativeDescriptorLayout::View { pointer, length }) = self
            .layouts
            .get(&ty)
            .and_then(|layout| layout.native.clone())
        else {
            self.errors.push(CppBackendError::MissingLayout(ty));
            return Vec::new();
        };
        let destination = cpp_ir::Expression::Name(value_name(result));
        vec![
            expression_call(
                "corbo_store_pointer",
                vec![
                    byte_offset(destination.clone(), pointer),
                    cpp_ir::Expression::Member {
                        base: Box::new(region.clone()),
                        member: "data".to_owned(),
                        through_pointer: true,
                    },
                ],
            ),
            cpp_ir::Statement::Assign {
                destination: self.size_at(byte_offset(destination, length)),
                source: cpp_ir::Expression::Member {
                    base: Box::new(region),
                    member: "len".to_owned(),
                    through_pointer: true,
                },
            },
        ]
    }

    fn construct_native(&mut self, value: &NativeOperation, ty: TypeId) -> Vec<cpp_ir::Statement> {
        let destination = cpp_ir::Expression::Name(value_name(value.result));
        match self.post.types.entries[ty.0 as usize].kind {
            TypeDefinition::GrowingSequence { element } => vec![expression_call(
                "corbo_region_init",
                vec![
                    reinterpret_pointer("corbo_region", destination),
                    cpp_ir::Expression::Unsigned(self.fixed_size(element) as u128),
                    self.destructor_callback(element),
                ],
            )],
            TypeDefinition::GrowingString => vec![expression_call(
                "corbo_region_init",
                vec![
                    reinterpret_pointer("corbo_region", destination),
                    cpp_ir::Expression::Unsigned(1),
                    cpp_ir::Expression::Null,
                ],
            )],
            TypeDefinition::KeyedCollection { value: element, .. } => {
                let layout = self.layouts.get(&element).copied();
                let Some(layout) = layout else {
                    self.errors.push(CppBackendError::MissingLayout(element));
                    return Vec::new();
                };
                vec![expression_call(
                    "corbo_map_init",
                    vec![
                        reinterpret_pointer("corbo_map", destination),
                        cpp_ir::Expression::Unsigned(self.fixed_size(element) as u128),
                        cpp_ir::Expression::Unsigned(layout.alignment as u128),
                        self.destructor_callback(element),
                    ],
                )]
            }
            TypeDefinition::InlineUtf8 { .. } => vec![cpp_ir::Statement::ZeroBytes {
                destination,
                bytes: cpp_ir::Expression::Unsigned(self.fixed_size(ty) as u128),
            }],
            _ => {
                self.errors
                    .push(CppBackendError::MissingOperationRepresentation {
                        operation: value.site.id,
                        representation: "Construct for non-native type",
                    });
                Vec::new()
            }
        }
    }

    fn destructor_callback(&self, ty: TypeId) -> cpp_ir::Expression {
        self.post
            .contracts
            .destructors
            .iter()
            .find(|destructor| destructor.ty == ty)
            .map(|destructor| cpp_ir::Expression::Name(destructor_name(destructor.id)))
            .unwrap_or(cpp_ir::Expression::Null)
    }

    fn stack_address(&mut self, cursor: CursorExpressionId) -> cpp_ir::Expression {
        cpp_ir::Expression::ByteOffset {
            base: Box::new(cpp_ir::Expression::Member {
                base: Box::new(cpp_ir::Expression::Name("corbo_fixed_stack".to_owned())),
                member: "base".to_owned(),
                through_pointer: false,
            }),
            bytes: Box::new(self.cursor_expression(cursor)),
        }
    }

    fn enter_region_classes(&self, moment: ExecutionMomentId) -> Vec<cpp_ir::Statement> {
        self.planned
            .storage
            .region_classes
            .iter()
            .filter(|class| class.entered_at == moment)
            .map(|class| cpp_ir::Statement::Assign {
                destination: cpp_ir::Expression::Name(region_mark_name(class.id)),
                source: cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name("corbo_region_enter".to_owned())),
                    arguments: vec![
                        cpp_ir::Expression::Unsigned(class.maximum_bytes as u128),
                        cpp_ir::Expression::Unsigned(class.reserved_slots.unwrap_or(0) as u128),
                    ],
                },
            })
            .collect()
    }

    fn cleanup(&mut self, exit: ScopeExitId) -> Vec<cpp_ir::Statement> {
        let Some(plan) = self
            .planned
            .cleanup
            .exits
            .iter()
            .find(|plan| plan.exit == exit)
        else {
            return Vec::new();
        };
        let actions = plan.actions.clone();
        let mut statements = Vec::new();
        for action in actions {
            match action {
                CleanupAction::InvokeUserDestructor { value, function } => {
                    statements.extend(self.call_destructor_hook(value, function));
                }
                CleanupAction::DestroyOwnedComponent {
                    value,
                    position,
                    destructor,
                } => {
                    let ty = self.post.values.entries[value.0 as usize].ty;
                    if matches!(
                        position,
                        PositionSelector::AllElements { .. } | PositionSelector::AllKeys
                    ) {
                        // The planned regional release invokes the runtime
                        // callback for every live owned element.
                        continue;
                    }
                    if position == PositionSelector::AllocationContent {
                        let slot = self
                            .layouts
                            .get(&ty)
                            .and_then(|layout| match layout.native {
                                Some(NativeDescriptorLayout::Allocation { slot, .. }) => Some(slot),
                                _ => None,
                            });
                        if let Some(slot) = slot {
                            statements.push(expression_call(
                                &destructor_name(destructor),
                                vec![cpp_ir::Expression::Call {
                                    callee: Box::new(cpp_ir::Expression::Name(
                                        "corbo_load_pointer".to_owned(),
                                    )),
                                    arguments: vec![byte_offset(
                                        cpp_ir::Expression::Name(value_name(value)),
                                        slot,
                                    )],
                                }],
                            ));
                        } else {
                            self.errors
                                .push(CppBackendError::MissingPositionRepresentation {
                                    ty,
                                    position,
                                });
                        }
                        continue;
                    }
                    if let Some(offset) = self.component_offset(ty, None, &position) {
                        statements.push(expression_call(
                            &destructor_name(destructor),
                            vec![byte_offset(
                                cpp_ir::Expression::Name(value_name(value)),
                                offset,
                            )],
                        ));
                    }
                }
                CleanupAction::ReleaseAllocation { address, .. } => {
                    if let Some(value) = self.value_for_entity(&EntityId::Address(address)) {
                        statements.push(expression_call(
                            "corbo_allocation_drop",
                            vec![reinterpret_pointer(
                                "corbo_allocation",
                                cpp_ir::Expression::Name(value_name(value)),
                            )],
                        ));
                    }
                }
                CleanupAction::RewindCursor { snapshot, .. } => {
                    let cursor = self.planned.storage.snapshots[snapshot.0 as usize].cursor;
                    statements.push(expression_call(
                        "corbo_stack_restore",
                        vec![self.cursor_expression(cursor)],
                    ));
                }
                CleanupAction::ReturnRegion { region, .. } => {
                    statements.extend(self.release_region(region));
                }
                CleanupAction::RestoreRegionClass { class, .. } => {
                    statements.push(expression_call(
                        "corbo_region_restore",
                        vec![cpp_ir::Expression::Name(region_mark_name(class))],
                    ));
                }
            }
        }
        statements
    }

    fn call_destructor_hook(
        &mut self,
        value: ValueId,
        function: FunctionInstanceId,
    ) -> Vec<cpp_ir::Statement> {
        let emission = self.cleanup_emission;
        self.cleanup_emission += 1;
        self.call_hook_at(
            cpp_ir::Expression::Name(value_name(value)),
            function,
            format!("drop_arguments_{}_{}_{}", value.0, function.0, emission),
        )
    }

    fn call_hook_at(
        &self,
        value: cpp_ir::Expression,
        function: FunctionInstanceId,
        arguments: String,
    ) -> Vec<cpp_ir::Statement> {
        if self.post.declarations.instances[function.0 as usize]
            .body
            .is_none()
        {
            return Vec::new();
        }
        vec![
            cpp_ir::Statement::Declare {
                ty: cpp_ir::Type::Array {
                    element: Box::new(cpp_ir::Type::Void.pointer_to(true)),
                    length: 1,
                },
                name: arguments.clone(),
                initializer: None,
            },
            cpp_ir::Statement::Assign {
                destination: cpp_ir::Expression::Index {
                    base: Box::new(cpp_ir::Expression::Name(arguments.clone())),
                    index: Box::new(cpp_ir::Expression::Unsigned(0)),
                },
                source: value,
            },
            expression_call(
                &function_name(function),
                vec![
                    cpp_ir::Expression::Null,
                    cpp_ir::Expression::Name(arguments),
                    cpp_ir::Expression::Null,
                ],
            ),
        ]
    }

    fn release_region(&mut self, region: RegionId) -> Vec<cpp_ir::Statement> {
        let owner = self.planned.storage.backings.iter().find_map(|backing| {
            matches!(backing.kind, BackingStorageKind::GrowingRegion { region: candidate } if candidate == region)
                .then_some(backing.owner)
        });
        let Some(owner) = owner else {
            self.errors.push(CppBackendError::InvalidMemoryPlan(format!(
                "region {:?} has no owning descriptor",
                region
            )));
            return Vec::new();
        };
        let ty = self.post.values.entries[owner.0 as usize].ty;
        let (function, runtime_ty) = match self.post.types.entries[ty.0 as usize].kind {
            TypeDefinition::GrowingSequence { .. } | TypeDefinition::GrowingString => {
                ("corbo_region_drop", "corbo_region")
            }
            TypeDefinition::KeyedCollection { .. } => ("corbo_map_drop", "corbo_map"),
            _ => {
                self.errors.push(CppBackendError::InvalidMemoryPlan(format!(
                    "region {:?} belongs to non-growing value {:?}",
                    region, owner
                )));
                return Vec::new();
            }
        };
        vec![expression_call(
            function,
            vec![reinterpret_pointer(
                runtime_ty,
                cpp_ir::Expression::Name(value_name(owner)),
            )],
        )]
    }

    fn fixed_size(&mut self, ty: TypeId) -> u64 {
        let Some(layout) = self.layouts.get(&ty).copied() else {
            self.errors.push(CppBackendError::MissingLayout(ty));
            return 0;
        };
        match layout.size {
            LayoutSize::Fixed(size) => size,
            LayoutSize::FromValue(_) => {
                self.errors.push(CppBackendError::RuntimeSizedLayout(ty));
                0
            }
        }
    }

    fn construct(
        &mut self,
        result: ValueId,
        ty: TypeId,
        variant: Option<VariantId>,
        components: &[ComponentInitialization],
    ) -> Vec<cpp_ir::Statement> {
        let size = self.fixed_size(ty);
        let mut statements = vec![cpp_ir::Statement::ZeroBytes {
            destination: cpp_ir::Expression::Name(value_name(result)),
            bytes: cpp_ir::Expression::Unsigned(size as u128),
        }];
        if let Some(variant) = variant {
            let Some(layout) = self.layouts.get(&ty).copied() else {
                return statements;
            };
            let Some(enumeration) = &layout.variant else {
                self.errors
                    .push(CppBackendError::MissingPositionRepresentation {
                        ty,
                        position: PositionSelector::VariantField {
                            variant,
                            field: FieldId(u32::MAX),
                        },
                    });
                return statements;
            };
            let discriminant = enumeration
                .variants
                .iter()
                .find(|candidate| candidate.variant == variant)
                .map(|candidate| candidate.discriminant)
                .unwrap_or(u64::MAX);
            statements.push(expression_call(
                "corbo_write_discriminant",
                vec![
                    cpp_ir::Expression::Name(value_name(result)),
                    cpp_ir::Expression::Unsigned(enumeration.discriminant_bytes as u128),
                    cpp_ir::Expression::Unsigned(discriminant as u128),
                ],
            ));
        }
        for component in components {
            let Some(offset) = self.component_offset(ty, variant, &component.position) else {
                continue;
            };
            let component_ty = self.post.values.entries[component.value.0 as usize].ty;
            statements.push(cpp_ir::Statement::CopyBytes {
                destination: byte_offset(cpp_ir::Expression::Name(value_name(result)), offset),
                source: cpp_ir::Expression::Name(value_name(component.value)),
                bytes: cpp_ir::Expression::Unsigned(self.fixed_size(component_ty) as u128),
            });
        }
        statements
    }

    fn component_offset(
        &mut self,
        ty: TypeId,
        variant: Option<VariantId>,
        position: &PositionSelector,
    ) -> Option<u64> {
        let Some(layout) = self.layouts.get(&ty).copied() else {
            self.errors.push(CppBackendError::MissingLayout(ty));
            return None;
        };
        let offset = match position {
            PositionSelector::Field(field) => layout
                .fields
                .iter()
                .find(|candidate| candidate.field == *field)
                .map(|field| field.byte_offset),
            PositionSelector::TupleElement(position) => layout
                .tuple_elements
                .iter()
                .find(|candidate| candidate.position == *position)
                .map(|element| element.byte_offset),
            PositionSelector::FixedIndex(index) => layout
                .sequence
                .as_ref()
                .map(|sequence| sequence.stride.saturating_mul(*index)),
            PositionSelector::VariantField { variant, field } => {
                layout.variant.as_ref().and_then(|enumeration| {
                    enumeration
                        .variants
                        .iter()
                        .find(|candidate| candidate.variant == *variant)
                        .and_then(|variant| {
                            variant
                                .fields
                                .iter()
                                .find(|candidate| candidate.field == *field)
                        })
                        .map(|field| enumeration.payload_offset + field.byte_offset)
                })
            }
            PositionSelector::State => Some(0),
            PositionSelector::AllocationContent
            | PositionSelector::AllKeys
            | PositionSelector::AllElements { .. }
            | PositionSelector::DynamicIndex(_)
            | PositionSelector::Key(_)
            | PositionSelector::Range { .. }
            | PositionSelector::Symbolic(_) => None,
        }
        .or_else(|| {
            variant.and_then(|variant| {
                if let PositionSelector::Field(field) = position {
                    layout.variant.as_ref().and_then(|enumeration| {
                        enumeration
                            .variants
                            .iter()
                            .find(|candidate| candidate.variant == variant)
                            .and_then(|variant| {
                                variant
                                    .fields
                                    .iter()
                                    .find(|candidate| candidate.field == *field)
                            })
                            .map(|field| enumeration.payload_offset + field.byte_offset)
                    })
                } else {
                    None
                }
            })
        });
        if offset.is_none() {
            self.errors
                .push(CppBackendError::MissingPositionRepresentation {
                    ty,
                    position: position.clone(),
                });
        }
        offset
    }

    fn repeat_array(&mut self, value: &RepeatArray) -> Vec<cpp_ir::Statement> {
        let ty = self.post.values.entries[value.result.0 as usize].ty;
        let Some(sequence) = self
            .layouts
            .get(&ty)
            .and_then(|layout| layout.sequence.clone())
        else {
            self.errors.push(CppBackendError::MissingLayout(ty));
            return Vec::new();
        };
        let element_ty = self.post.values.entries[value.seed.0 as usize].ty;
        let mut body = Vec::new();
        body.push(cpp_ir::Statement::CopyBytes {
            destination: cpp_ir::Expression::ByteOffset {
                base: Box::new(cpp_ir::Expression::Name(value_name(value.result))),
                bytes: Box::new(cpp_ir::Expression::Binary {
                    operator: cpp_ir::BinaryOperator::Multiply,
                    left: Box::new(cpp_ir::Expression::Name(format!(
                        "repeat_index_{}",
                        value.site.id.0
                    ))),
                    right: Box::new(cpp_ir::Expression::Unsigned(sequence.stride as u128)),
                }),
            },
            source: cpp_ir::Expression::Name(value_name(value.seed)),
            bytes: cpp_ir::Expression::Unsigned(self.fixed_size(element_ty) as u128),
        });
        vec![cpp_ir::Statement::Verbatim(format!(
            "for (std::size_t repeat_index_{} = 0; repeat_index_{} < {}; ++repeat_index_{}) {{\n    std::memcpy(reinterpret_cast<unsigned char*>({}) + repeat_index_{} * {}, {}, {});\n}}",
            value.site.id.0,
            value.site.id.0,
            value.count,
            value.site.id.0,
            value_name(value.result),
            value.site.id.0,
            sequence.stride,
            value_name(value.seed),
            self.fixed_size(element_ty)
        ))]
    }

    fn extract_tuple(&mut self, value: &ExtractTupleField) -> Vec<cpp_ir::Statement> {
        let source_ty = self.post.values.entries[value.source.0 as usize].ty;
        let Some(element) = self
            .layouts
            .get(&source_ty)
            .and_then(|layout| {
                layout
                    .tuple_elements
                    .iter()
                    .find(|element| element.position == value.position)
            })
            .cloned()
        else {
            self.errors
                .push(CppBackendError::MissingPositionRepresentation {
                    ty: source_ty,
                    position: PositionSelector::TupleElement(value.position),
                });
            return Vec::new();
        };
        self.extract_at(
            value.result,
            value.source,
            element.byte_offset,
            value.reference.is_some(),
        )
    }

    fn extract_variant(&mut self, value: &ExtractVariantField) -> Vec<cpp_ir::Statement> {
        let source_ty = self.post.values.entries[value.source.0 as usize].ty;
        let position = PositionSelector::VariantField {
            variant: value.variant,
            field: value.field,
        };
        let Some(offset) = self.component_offset(source_ty, Some(value.variant), &position) else {
            return Vec::new();
        };
        self.extract_at(
            value.result,
            value.source,
            offset,
            value.reference.is_some(),
        )
    }

    fn extract_at(
        &mut self,
        result: ValueId,
        source: ValueId,
        offset: u64,
        reference: bool,
    ) -> Vec<cpp_ir::Statement> {
        let address = byte_offset(cpp_ir::Expression::Name(value_name(source)), offset);
        if reference {
            vec![expression_call(
                "corbo_store_pointer",
                vec![cpp_ir::Expression::Name(value_name(result)), address],
            )]
        } else {
            let ty = self.post.values.entries[result.0 as usize].ty;
            vec![cpp_ir::Statement::CopyBytes {
                destination: cpp_ir::Expression::Name(value_name(result)),
                source: address,
                bytes: cpp_ir::Expression::Unsigned(self.fixed_size(ty) as u128),
            }]
        }
    }

    fn call_function(
        &mut self,
        operation: OperationId,
        target: FunctionInstanceId,
        arguments: &[CallArgument],
        result: ValueId,
    ) -> Vec<cpp_ir::Statement> {
        let name = format!("arguments_{}", operation.0);
        let mut statements = vec![cpp_ir::Statement::Declare {
            ty: cpp_ir::Type::Array {
                element: Box::new(cpp_ir::Type::Void.pointer_to(true)),
                length: arguments.len().max(1) as u64,
            },
            name: name.clone(),
            initializer: None,
        }];
        for argument in arguments {
            statements.push(cpp_ir::Statement::Assign {
                destination: cpp_ir::Expression::Index {
                    base: Box::new(cpp_ir::Expression::Name(name.clone())),
                    index: Box::new(cpp_ir::Expression::Unsigned(
                        argument.parameter_index as u128,
                    )),
                },
                source: cpp_ir::Expression::Name(value_name(argument.value)),
            });
        }
        statements.push(expression_call(
            &function_name(target),
            vec![
                cpp_ir::Expression::Name(value_name(result)),
                cpp_ir::Expression::Name(name),
                cpp_ir::Expression::Null,
            ],
        ));
        statements
    }

    fn call_external(&mut self, value: &ExternalCall) -> Vec<cpp_ir::Statement> {
        let instance = &self.post.declarations.instances[value.target.function.0 as usize];
        let definition = &self.post.declarations.functions[instance.definition.0 as usize];
        let signature = &self.post.declarations.signatures[instance.signature.0 as usize];
        let symbol = self.post.symbols.entries[definition.symbol.0 as usize]
            .spelling
            .clone();
        let arguments = value
            .arguments
            .iter()
            .map(|argument| self.typed_value(argument.value))
            .collect::<Vec<_>>();
        let call = cpp_ir::Expression::Call {
            callee: Box::new(cpp_ir::Expression::Name(symbol)),
            arguments,
        };
        if matches!(
            self.post.types.entries[signature.result.0 as usize].kind,
            TypeDefinition::Unit
        ) {
            vec![cpp_ir::Statement::Expression(call)]
        } else {
            vec![cpp_ir::Statement::Assign {
                destination: self.typed_value(value.result),
                source: call,
            }]
        }
    }

    fn create_future(&mut self, value: &CreateFuture) -> Vec<cpp_ir::Statement> {
        let Some(frame) = self.async_frame(value.body).cloned() else {
            self.errors
                .push(CppBackendError::MissingOperationRepresentation {
                    operation: value.site.id,
                    representation: "CreateFuture without planned async frame",
                });
            return Vec::new();
        };
        let mut statements = vec![cpp_ir::Statement::ZeroBytes {
            destination: cpp_ir::Expression::Name(value_name(value.result)),
            bytes: cpp_ir::Expression::Unsigned(
                self.fixed_size(self.post.values.entries[value.result.0 as usize].ty) as u128,
            ),
        }];
        let signature = &self.post.declarations.signatures[self.post.declarations.instances
            [value.function.0 as usize]
            .signature
            .0 as usize];
        for argument in &value.arguments {
            let Some(parameter) = signature.parameters.get(argument.parameter_index as usize)
            else {
                continue;
            };
            let ParameterIdentity::Named { binding, .. } = parameter.identity else {
                continue;
            };
            let Some(saved) = frame.saved.iter().find(|saved| {
                matches!(self.post.values.entries[saved.value.0 as usize].definition,
                    ValueDefinition::Parameter(candidate) if candidate == binding)
            }) else {
                continue;
            };
            let bytes = self.fixed_size(self.post.values.entries[argument.value.0 as usize].ty);
            if bytes != 0 {
                statements.push(cpp_ir::Statement::CopyBytes {
                    destination: byte_offset(
                        cpp_ir::Expression::Name(value_name(value.result)),
                        saved.byte_offset,
                    ),
                    source: cpp_ir::Expression::Name(value_name(argument.value)),
                    bytes: cpp_ir::Expression::Unsigned(bytes as u128),
                });
            }
        }
        if let Some(record) = value.captures {
            for capture in &self.post.contracts.captures[record.0 as usize].captures {
                let Some(binding) = self.post.scopes.bindings.iter().find(|binding| {
                    matches!(binding.introduced, BindingIntroduction::Capture { record: candidate, field }
                        if candidate == record && field == capture.field)
                }) else { continue; };
                let Some(saved) = frame.saved.iter().find(|saved| {
                    matches!(self.post.values.provenance[self.post.values.entries[saved.value.0 as usize].provenance.0 as usize].kind,
                        ProvenanceKind::Binding(candidate) if candidate == binding.id)
                }) else { continue; };
                let bytes = self.fixed_size(self.post.values.entries[capture.value.0 as usize].ty);
                if bytes != 0 {
                    statements.push(cpp_ir::Statement::CopyBytes {
                        destination: byte_offset(
                            cpp_ir::Expression::Name(value_name(value.result)),
                            saved.byte_offset,
                        ),
                        source: cpp_ir::Expression::Name(value_name(capture.value)),
                        bytes: cpp_ir::Expression::Unsigned(bytes as u128),
                    });
                }
            }
        }
        statements
    }

    fn poll_await(&mut self, value: &AwaitValue) -> Vec<cpp_ir::Statement> {
        let ready = match &value.protocol.protocol {
            AwaitProtocol::GeneratedFuture { function, .. } => cpp_ir::Expression::Call {
                callee: Box::new(cpp_ir::Expression::Name(async_poll_name(*function))),
                arguments: vec![
                    cpp_ir::Expression::Name(value_name(value.source)),
                    cpp_ir::Expression::Name(value_name(value.result)),
                    cpp_ir::Expression::Name("context".to_owned()),
                ],
            },
            AwaitProtocol::ContractMethod { target, .. } => {
                let MethodTarget::Concrete(function) = target else {
                    self.errors
                        .push(CppBackendError::MissingOperationRepresentation {
                            operation: value.site.id,
                            representation: "abstract contract await in concrete backend",
                        });
                    return Vec::new();
                };
                cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name(function_name(*function))),
                    arguments: vec![
                        cpp_ir::Expression::Name(value_name(value.result)),
                        cpp_ir::Expression::Null,
                        cpp_ir::Expression::Name(value_name(value.source)),
                    ],
                }
            }
            AwaitProtocol::Handle { .. } => cpp_ir::Expression::Call {
                callee: Box::new(cpp_ir::Expression::Name(
                    "corbo_task_await_value".to_owned(),
                )),
                arguments: vec![
                    cpp_ir::Expression::Name(value_name(value.source)),
                    cpp_ir::Expression::Name(value_name(value.result)),
                    cpp_ir::Expression::Unsigned(self.fixed_size(value.protocol.result) as u128),
                    cpp_ir::Expression::Name("context".to_owned()),
                ],
            },
            AwaitProtocol::PollMethod(function) => cpp_ir::Expression::Call {
                callee: Box::new(cpp_ir::Expression::Name(function_name(*function))),
                arguments: vec![
                    cpp_ir::Expression::Name(value_name(value.result)),
                    cpp_ir::Expression::Null,
                    cpp_ir::Expression::Name(value_name(value.source)),
                ],
            },
        };
        vec![cpp_ir::Statement::Assign {
            destination: cpp_ir::Expression::Name(await_ready_name(value.source)),
            source: ready,
        }]
    }

    fn create_closure(&mut self, value: &CreateClosure) -> Vec<cpp_ir::Statement> {
        let record = &self.post.contracts.captures[value.captures.0 as usize];
        let Some(layout) = self.layouts.get(&record.ty).copied() else {
            self.errors.push(CppBackendError::MissingLayout(record.ty));
            return Vec::new();
        };
        let mut statements = Vec::new();
        for capture in &record.captures {
            let Some(field) = layout
                .fields
                .iter()
                .find(|field| field.field == capture.field)
            else {
                self.errors.push(CppBackendError::MissingFieldLayout {
                    ty: record.ty,
                    field: capture.field,
                });
                continue;
            };
            statements.push(cpp_ir::Statement::CopyBytes {
                destination: byte_offset(
                    cpp_ir::Expression::Name(value_name(value.result)),
                    field.byte_offset,
                ),
                source: cpp_ir::Expression::Name(value_name(capture.value)),
                bytes: cpp_ir::Expression::Unsigned(
                    self.fixed_size(self.post.declarations.fields[capture.field.0 as usize].ty)
                        as u128,
                ),
            });
        }
        statements
    }

    fn adapt_callable(&mut self, value: &AdaptCallable) -> Vec<cpp_ir::Statement> {
        let result_ty = self.post.values.entries[value.result.0 as usize].ty;
        let Some(NativeDescriptorLayout::Callable {
            function,
            environment,
        }) = self
            .layouts
            .get(&result_ty)
            .and_then(|layout| layout.native.clone())
        else {
            self.errors.push(CppBackendError::MissingLayout(result_ty));
            return Vec::new();
        };
        let (source, source_ty) = self.callable_value_address(value.source);
        match self.post.types.entries[source_ty.0 as usize].kind {
            TypeDefinition::Closure { captures, .. } => {
                let record = &self.post.contracts.captures[captures.0 as usize];
                let Some(target) = record.call else {
                    self.errors
                        .push(CppBackendError::MissingOperationRepresentation {
                            operation: value.site.id,
                            representation: "closure without resolved call target",
                        });
                    return Vec::new();
                };
                vec![
                    expression_call(
                        "corbo_store_pointer",
                        vec![
                            byte_offset(
                                cpp_ir::Expression::Name(value_name(value.result)),
                                function,
                            ),
                            cpp_ir::Expression::ReinterpretCast {
                                ty: cpp_ir::Type::Void.pointer_to(true),
                                value: Box::new(cpp_ir::Expression::Name(function_name(target))),
                            },
                        ],
                    ),
                    expression_call(
                        "corbo_store_pointer",
                        vec![
                            byte_offset(
                                cpp_ir::Expression::Name(value_name(value.result)),
                                environment,
                            ),
                            source,
                        ],
                    ),
                ]
            }
            TypeDefinition::Callable(_) => vec![cpp_ir::Statement::CopyBytes {
                destination: cpp_ir::Expression::Name(value_name(value.result)),
                source,
                bytes: cpp_ir::Expression::Unsigned(self.fixed_size(result_ty) as u128),
            }],
            _ => {
                self.errors
                    .push(CppBackendError::MissingOperationRepresentation {
                        operation: value.site.id,
                        representation: "AdaptCallable source type",
                    });
                Vec::new()
            }
        }
    }

    fn call_callable(&mut self, value: &CallableCall) -> Vec<cpp_ir::Statement> {
        let arguments_name = format!("arguments_{}", value.site.id.0);
        let mut statements = self.prepare_arguments(&arguments_name, &value.arguments);
        let (source, source_ty) = self.callable_value_address(value.target.callable);
        let (callee, environment) = match self.post.types.entries[source_ty.0 as usize].kind {
            TypeDefinition::Closure { captures, .. } => {
                let record = &self.post.contracts.captures[captures.0 as usize];
                let Some(target) = record.call else {
                    self.errors
                        .push(CppBackendError::MissingOperationRepresentation {
                            operation: value.site.id,
                            representation: "closure without resolved call target",
                        });
                    return statements;
                };
                (cpp_ir::Expression::Name(function_name(target)), source)
            }
            TypeDefinition::Callable(_) => {
                let Some(NativeDescriptorLayout::Callable {
                    function,
                    environment,
                }) = self
                    .layouts
                    .get(&source_ty)
                    .and_then(|layout| layout.native.clone())
                else {
                    self.errors.push(CppBackendError::MissingLayout(source_ty));
                    return statements;
                };
                let function_pointer = cpp_ir::Type::FunctionPointer {
                    result: Box::new(cpp_ir::Type::Void),
                    parameters: vec![
                        cpp_ir::Type::Void.pointer_to(true),
                        cpp_ir::Type::Void.pointer_to(true).pointer_to(true),
                        cpp_ir::Type::Void.pointer_to(true),
                    ],
                };
                (
                    cpp_ir::Expression::ReinterpretCast {
                        ty: function_pointer,
                        value: Box::new(cpp_ir::Expression::Call {
                            callee: Box::new(cpp_ir::Expression::Name(
                                "corbo_load_pointer".to_owned(),
                            )),
                            arguments: vec![byte_offset(source.clone(), function)],
                        }),
                    },
                    cpp_ir::Expression::Call {
                        callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                        arguments: vec![byte_offset(source, environment)],
                    },
                )
            }
            _ => {
                self.errors
                    .push(CppBackendError::MissingOperationRepresentation {
                        operation: value.site.id,
                        representation: "CallableCall target type",
                    });
                return statements;
            }
        };
        statements.push(cpp_ir::Statement::Expression(cpp_ir::Expression::Call {
            callee: Box::new(callee),
            arguments: vec![
                cpp_ir::Expression::Name(value_name(value.result)),
                cpp_ir::Expression::Name(arguments_name),
                environment,
            ],
        }));
        statements
    }

    fn prepare_arguments(&self, name: &str, arguments: &[CallArgument]) -> Vec<cpp_ir::Statement> {
        let mut statements = vec![cpp_ir::Statement::Declare {
            ty: cpp_ir::Type::Array {
                element: Box::new(cpp_ir::Type::Void.pointer_to(true)),
                length: arguments.len().max(1) as u64,
            },
            name: name.to_owned(),
            initializer: None,
        }];
        for argument in arguments {
            statements.push(cpp_ir::Statement::Assign {
                destination: cpp_ir::Expression::Index {
                    base: Box::new(cpp_ir::Expression::Name(name.to_owned())),
                    index: Box::new(cpp_ir::Expression::Unsigned(
                        argument.parameter_index as u128,
                    )),
                },
                source: cpp_ir::Expression::Name(value_name(argument.value)),
            });
        }
        statements
    }

    fn callable_value_address(&self, value: ValueId) -> (cpp_ir::Expression, TypeId) {
        let ty = self.post.values.entries[value.0 as usize].ty;
        match self.post.types.entries[ty.0 as usize].kind {
            TypeDefinition::Reference { target, .. } => (
                cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                    arguments: vec![cpp_ir::Expression::Name(value_name(value))],
                },
                target,
            ),
            _ => (cpp_ir::Expression::Name(value_name(value)), ty),
        }
    }

    fn copy_value(&mut self, destination: ValueId, source: ValueId) -> Vec<cpp_ir::Statement> {
        self.copy_value_to_expression(cpp_ir::Expression::Name(value_name(destination)), source)
    }

    fn materialize_transfer(
        &mut self,
        destination: ValueId,
        source: ValueId,
    ) -> Vec<cpp_ir::Statement> {
        let aliases_existing_storage = self
            .planned
            .storage
            .values
            .get(destination.0 as usize)
            .is_some_and(|storage| {
                std::iter::once(&storage.alternatives.first)
                    .chain(&storage.alternatives.rest)
                    .all(|alternative| {
                        matches!(
                            alternative.kind,
                            ValueStorageKind::Alias { .. } | ValueStorageKind::SelectAlias { .. }
                        )
                    })
            });
        if aliases_existing_storage {
            return Vec::new();
        }
        let ty = self.post.values.entries[source.0 as usize].ty;
        if self.fixed_size(ty) == 0 {
            return Vec::new();
        }
        vec![cpp_ir::Statement::If {
            condition: cpp_ir::Expression::Binary {
                operator: cpp_ir::BinaryOperator::NotEqual,
                left: Box::new(cpp_ir::Expression::Name(value_name(destination))),
                right: Box::new(cpp_ir::Expression::Name(value_name(source))),
            },
            then_block: cpp_ir::Block {
                statements: vec![cpp_ir::Statement::CopyBytes {
                    destination: cpp_ir::Expression::Name(value_name(destination)),
                    source: cpp_ir::Expression::Name(value_name(source)),
                    bytes: cpp_ir::Expression::Unsigned(self.fixed_size(ty) as u128),
                }],
            },
            else_block: None,
        }]
    }

    fn materialize_guarded_transfers(
        &mut self,
        destination: ValueId,
        incoming: &[GuardedValue],
    ) -> Vec<cpp_ir::Statement> {
        let mut statements = Vec::new();
        for incoming in incoming {
            for statement in self.materialize_transfer(destination, incoming.value) {
                statements.push(self.guarded(incoming.guard, statement));
            }
        }
        statements
    }

    fn materialize_parametric_transfer(
        &mut self,
        transfer: &ParametricTransfer,
    ) -> Vec<cpp_ir::Statement> {
        let when_true = self.materialize_transfer(transfer.result, transfer.copied);
        let when_false = self.materialize_transfer(transfer.result, transfer.moved);
        if when_true.is_empty() && when_false.is_empty() {
            return Vec::new();
        }
        vec![cpp_ir::Statement::If {
            condition: self.predicate(transfer.copies),
            then_block: cpp_ir::Block {
                statements: when_true,
            },
            else_block: Some(cpp_ir::Block {
                statements: when_false,
            }),
        }]
    }

    fn copy_value_to_expression(
        &mut self,
        destination: cpp_ir::Expression,
        source: ValueId,
    ) -> Vec<cpp_ir::Statement> {
        let ty = self.post.values.entries[source.0 as usize].ty;
        if self.fixed_size(ty) == 0 {
            return Vec::new();
        }
        vec![cpp_ir::Statement::CopyBytes {
            destination,
            source: cpp_ir::Expression::Name(value_name(source)),
            bytes: cpp_ir::Expression::Unsigned(self.fixed_size(ty) as u128),
        }]
    }

    fn copy_from_pointer(
        &mut self,
        destination: ValueId,
        source: String,
    ) -> Vec<cpp_ir::Statement> {
        let ty = self.post.values.entries[destination.0 as usize].ty;
        if self.fixed_size(ty) == 0 {
            return Vec::new();
        }
        vec![cpp_ir::Statement::CopyBytes {
            destination: cpp_ir::Expression::Name(value_name(destination)),
            source: cpp_ir::Expression::Name(source),
            bytes: cpp_ir::Expression::Unsigned(self.fixed_size(ty) as u128),
        }]
    }

    fn copy_to_pointer(
        &mut self,
        destination: EvaluatedPlaceId,
        source: ValueId,
    ) -> Vec<cpp_ir::Statement> {
        let ty = self.post.values.entries[source.0 as usize].ty;
        if self.fixed_size(ty) == 0 {
            return Vec::new();
        }
        vec![cpp_ir::Statement::CopyBytes {
            destination: cpp_ir::Expression::Name(evaluated_name(destination)),
            source: cpp_ir::Expression::Name(value_name(source)),
            bytes: cpp_ir::Expression::Unsigned(self.fixed_size(ty) as u128),
        }]
    }

    fn store_reference(
        &mut self,
        destination: ValueId,
        source: EvaluatedPlaceId,
    ) -> Vec<cpp_ir::Statement> {
        vec![expression_call(
            "corbo_store_pointer",
            vec![
                cpp_ir::Expression::Name(value_name(destination)),
                cpp_ir::Expression::Name(evaluated_name(source)),
            ],
        )]
    }

    fn binary(
        &self,
        result: ValueId,
        left: ValueId,
        right: ValueId,
        operator: cpp_ir::BinaryOperator,
    ) -> Vec<cpp_ir::Statement> {
        vec![cpp_ir::Statement::Assign {
            destination: self.typed_value(result),
            source: cpp_ir::Expression::Binary {
                operator,
                left: Box::new(self.typed_value(left)),
                right: Box::new(self.typed_value(right)),
            },
        }]
    }

    fn unary(
        &self,
        result: ValueId,
        operand: ValueId,
        operator: cpp_ir::UnaryOperator,
    ) -> Vec<cpp_ir::Statement> {
        vec![cpp_ir::Statement::Assign {
            destination: self.typed_value(result),
            source: cpp_ir::Expression::Unary {
                operator,
                operand: Box::new(self.typed_value(operand)),
            },
        }]
    }

    fn resolved_equality(
        &mut self,
        result: ValueId,
        left: ValueId,
        right: ValueId,
        plan: EqualityPlanId,
        invert: bool,
    ) -> Vec<cpp_ir::Statement> {
        let Some(mut comparison) = self.equality_expression(
            plan,
            cpp_ir::Expression::Name(value_name(left)),
            cpp_ir::Expression::Name(value_name(right)),
        ) else {
            return Vec::new();
        };
        if invert {
            comparison = cpp_ir::Expression::Unary {
                operator: cpp_ir::UnaryOperator::LogicalNot,
                operand: Box::new(comparison),
            };
        }
        vec![cpp_ir::Statement::Assign {
            destination: self.typed_value(result),
            source: comparison,
        }]
    }

    fn equality_expression(
        &mut self,
        plan: EqualityPlanId,
        left: cpp_ir::Expression,
        right: cpp_ir::Expression,
    ) -> Option<cpp_ir::Expression> {
        let plan = self.post.contracts.equality[plan.0 as usize].clone();
        let equal = |left, right| cpp_ir::Expression::Binary {
            operator: cpp_ir::BinaryOperator::Equal,
            left: Box::new(left),
            right: Box::new(right),
        };
        let and = |left, right| cpp_ir::Expression::Binary {
            operator: cpp_ir::BinaryOperator::LogicalAnd,
            left: Box::new(left),
            right: Box::new(right),
        };
        let or = |left, right| cpp_ir::Expression::Binary {
            operator: cpp_ir::BinaryOperator::LogicalOr,
            left: Box::new(left),
            right: Box::new(right),
        };
        match plan.kind {
            EqualityKind::Numeric(_)
            | EqualityKind::NumericConversionError
            | EqualityKind::Boolean => Some(equal(
                self.typed_at(left, plan.ty),
                self.typed_at(right, plan.ty),
            )),
            EqualityKind::ReferenceIdentity => Some(equal(
                cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                    arguments: vec![left],
                },
                cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                    arguments: vec![right],
                },
            )),
            EqualityKind::SliceIdentity => {
                let Some(NativeDescriptorLayout::View { pointer, length }) = self
                    .layouts
                    .get(&plan.ty)
                    .and_then(|layout| layout.native.clone())
                else {
                    self.errors.push(CppBackendError::MissingLayout(plan.ty));
                    return None;
                };
                let pointer_equal = equal(
                    cpp_ir::Expression::Call {
                        callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                        arguments: vec![byte_offset(left.clone(), pointer)],
                    },
                    cpp_ir::Expression::Call {
                        callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                        arguments: vec![byte_offset(right.clone(), pointer)],
                    },
                );
                let usize_ty = self.usize_type()?;
                Some(and(
                    pointer_equal,
                    equal(
                        self.typed_at(byte_offset(left, length), usize_ty),
                        self.typed_at(byte_offset(right, length), usize_ty),
                    ),
                ))
            }
            EqualityKind::EnumTagAndPayload(variants) => {
                let layout = self.layouts.get(&plan.ty)?.variant.clone()?;
                let left_tag = cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name(
                        "corbo_read_discriminant".to_owned(),
                    )),
                    arguments: vec![
                        left.clone(),
                        cpp_ir::Expression::Unsigned(layout.discriminant_bytes as u128),
                    ],
                };
                let right_tag = cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name(
                        "corbo_read_discriminant".to_owned(),
                    )),
                    arguments: vec![
                        right.clone(),
                        cpp_ir::Expression::Unsigned(layout.discriminant_bytes as u128),
                    ],
                };
                let mut result = equal(left_tag.clone(), right_tag);
                for variant in variants {
                    let discriminant = layout
                        .variants
                        .iter()
                        .find(|candidate| candidate.variant == variant.variant)?
                        .discriminant;
                    let mut fields_equal = cpp_ir::Expression::Boolean(true);
                    for field in variant.fields {
                        let offset = self.component_offset(
                            plan.ty,
                            Some(variant.variant),
                            &PositionSelector::VariantField {
                                variant: variant.variant,
                                field: field.field,
                            },
                        )?;
                        let comparison = self.equality_expression(
                            field.comparison,
                            byte_offset(left.clone(), offset),
                            byte_offset(right.clone(), offset),
                        )?;
                        fields_equal = and(fields_equal, comparison);
                    }
                    let not_this_variant = cpp_ir::Expression::Binary {
                        operator: cpp_ir::BinaryOperator::NotEqual,
                        left: Box::new(left_tag.clone()),
                        right: Box::new(cpp_ir::Expression::Unsigned(discriminant as u128)),
                    };
                    result = and(result, or(not_this_variant, fields_equal));
                }
                Some(result)
            }
        }
    }

    fn place_address(&mut self, place: PlaceId) -> Option<cpp_ir::Expression> {
        let place_data = self.post.objects.places[place.0 as usize].clone();
        let (mut address, mut ty) = match place_data.root {
            PlaceRoot::Value(value) => (
                cpp_ir::Expression::Name(value_name(value)),
                self.post.values.entries[value.0 as usize].ty,
            ),
            PlaceRoot::Binding(binding) => (
                cpp_ir::Expression::Name(binding_name(binding)),
                self.post.scopes.bindings[binding.0 as usize].ty,
            ),
            PlaceRoot::Address(address) => {
                let value = self.value_for_entity(&EntityId::Address(address))?;
                (
                    cpp_ir::Expression::Name(value_name(value)),
                    self.post.objects.addresses[address.0 as usize].ty,
                )
            }
            PlaceRoot::Reference(reference) => {
                let value = self.value_for_entity(&EntityId::Reference(reference))?;
                let reference_ty = self.post.objects.references[reference.0 as usize].ty;
                let target = match self.post.types.entries[reference_ty.0 as usize].kind {
                    TypeDefinition::Reference { target, .. } => target,
                    _ => {
                        self.errors
                            .push(CppBackendError::MissingPlaceRepresentation(place));
                        return None;
                    }
                };
                (
                    cpp_ir::Expression::Call {
                        callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                        arguments: vec![cpp_ir::Expression::Name(value_name(value))],
                    },
                    target,
                )
            }
            PlaceRoot::Collection(collection) => {
                let descriptor = self.post.objects.collections[collection.0 as usize]
                    .descriptor
                    .clone();
                match descriptor {
                    CollectionDescriptor::Address(address) => {
                        let value = self.value_for_entity(&EntityId::Address(address))?;
                        (
                            cpp_ir::Expression::Name(value_name(value)),
                            self.post.objects.collections[collection.0 as usize].ty,
                        )
                    }
                    CollectionDescriptor::Place(place) => {
                        let address = self.place_address(place)?;
                        (
                            address,
                            self.post.objects.collections[collection.0 as usize].ty,
                        )
                    }
                }
            }
        };
        let mut selected_variant = None;
        for projection in place_data.projections {
            match projection {
                PlaceProjection::Dereference | PlaceProjection::AllocationContent => {
                    let pointer_offset = match self.post.types.entries[ty.0 as usize].kind {
                        TypeDefinition::Reference { .. } => 0,
                        TypeDefinition::Allocation { .. } => self
                            .layouts
                            .get(&ty)
                            .and_then(|layout| match layout.native {
                                Some(NativeDescriptorLayout::Allocation { slot, .. }) => Some(slot),
                                _ => None,
                            })
                            .unwrap_or_else(|| {
                                self.errors
                                    .push(CppBackendError::MissingPlaceRepresentation(place));
                                0
                            }),
                        _ => 0,
                    };
                    address = cpp_ir::Expression::Call {
                        callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                        arguments: vec![byte_offset(address, pointer_offset)],
                    };
                    ty = match self.post.types.entries[ty.0 as usize].kind {
                        TypeDefinition::Reference { target, .. } => target,
                        TypeDefinition::Allocation { content } => content,
                        _ => {
                            self.errors
                                .push(CppBackendError::MissingPlaceRepresentation(place));
                            return None;
                        }
                    };
                }
                PlaceProjection::Field(field) => {
                    let layout = self.layouts.get(&ty).copied()?;
                    let field_layout = if let Some(variant) = selected_variant {
                        layout
                            .variant
                            .as_ref()
                            .and_then(|enumeration| {
                                enumeration
                                    .variants
                                    .iter()
                                    .find(|candidate| candidate.variant == variant)
                            })
                            .and_then(|variant| {
                                variant
                                    .fields
                                    .iter()
                                    .find(|candidate| candidate.field == field)
                            })
                    } else {
                        layout
                            .fields
                            .iter()
                            .find(|candidate| candidate.field == field)
                    };
                    let Some(field_layout) = field_layout else {
                        self.errors
                            .push(CppBackendError::MissingFieldLayout { ty, field });
                        return None;
                    };
                    let offset = layout
                        .variant
                        .as_ref()
                        .filter(|_| selected_variant.is_some())
                        .map(|enumeration| enumeration.payload_offset)
                        .unwrap_or(0)
                        + field_layout.byte_offset;
                    address = cpp_ir::Expression::ByteOffset {
                        base: Box::new(address),
                        bytes: Box::new(cpp_ir::Expression::Unsigned(offset as u128)),
                    };
                    ty = self.planned.layouts.layouts[field_layout.layout.0 as usize].ty;
                    selected_variant = None;
                }
                PlaceProjection::TupleElement(position) => {
                    let Some(element) = self
                        .layouts
                        .get(&ty)
                        .and_then(|layout| {
                            layout
                                .tuple_elements
                                .iter()
                                .find(|element| element.position == position)
                        })
                        .cloned()
                    else {
                        self.errors
                            .push(CppBackendError::MissingPlaceRepresentation(place));
                        return None;
                    };
                    address = cpp_ir::Expression::ByteOffset {
                        base: Box::new(address),
                        bytes: Box::new(cpp_ir::Expression::Unsigned(element.byte_offset as u128)),
                    };
                    ty = self.planned.layouts.layouts[element.layout.0 as usize].ty;
                }
                PlaceProjection::Variant(variant) => selected_variant = Some(variant),
                PlaceProjection::Index(index) => {
                    let (base, element, stride) = self.indexed_storage(address, ty, place)?;
                    address = cpp_ir::Expression::ByteOffset {
                        base: Box::new(base),
                        bytes: Box::new(cpp_ir::Expression::Binary {
                            operator: cpp_ir::BinaryOperator::Multiply,
                            left: Box::new(self.typed_value(index)),
                            right: Box::new(cpp_ir::Expression::Unsigned(stride as u128)),
                        }),
                    };
                    ty = element;
                }
                PlaceProjection::Range { start, .. } => {
                    let (base, element, stride) = self.indexed_storage(address, ty, place)?;
                    address = cpp_ir::Expression::ByteOffset {
                        base: Box::new(base),
                        bytes: Box::new(cpp_ir::Expression::Binary {
                            operator: cpp_ir::BinaryOperator::Multiply,
                            left: Box::new(self.typed_value(start)),
                            right: Box::new(cpp_ir::Expression::Unsigned(stride as u128)),
                        }),
                    };
                    ty = element;
                }
                PlaceProjection::Key(_) => {
                    self.errors
                        .push(CppBackendError::MissingPlaceRepresentation(place));
                    return None;
                }
            }
        }
        Some(address)
    }

    fn value_for_entity(&mut self, entity: &EntityId) -> Option<ValueId> {
        let value = self
            .post
            .objects
            .value_entities
            .iter()
            .find(|identity| &identity.entity == entity)
            .map(|identity| identity.value);
        if value.is_none() {
            self.errors
                .push(CppBackendError::MissingPlaceRepresentation(PlaceId(
                    u32::MAX,
                )));
        }
        value
    }

    fn indexed_storage(
        &mut self,
        address: cpp_ir::Expression,
        ty: TypeId,
        place: PlaceId,
    ) -> Option<(cpp_ir::Expression, TypeId, u64)> {
        let (base, element) = match self.post.types.entries[ty.0 as usize].kind {
            TypeDefinition::Array { element, .. } => (address, element),
            TypeDefinition::Slice { element } | TypeDefinition::GrowingSequence { element } => (
                cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                    arguments: vec![address],
                },
                element,
            ),
            _ => {
                self.errors
                    .push(CppBackendError::MissingPlaceRepresentation(place));
                return None;
            }
        };
        let stride = self.fixed_size(element);
        Some((base, element, stride))
    }

    fn index_place(&mut self, value: &IndexPlace) -> Vec<cpp_ir::Statement> {
        let ResolvedIndexAccess::Contiguous { element } = value.access else {
            self.errors
                .push(CppBackendError::MissingOperationRepresentation {
                    operation: value.site.id,
                    representation: "intrinsic IndexPlace",
                });
            return Vec::new();
        };
        let Some(base) = self.contiguous_data(value.base, element) else {
            return Vec::new();
        };
        let stride = self.fixed_size(element);
        vec![cpp_ir::Statement::Assign {
            destination: cpp_ir::Expression::Name(evaluated_name(value.result)),
            source: cpp_ir::Expression::ByteOffset {
                base: Box::new(base),
                bytes: Box::new(cpp_ir::Expression::Binary {
                    operator: cpp_ir::BinaryOperator::Multiply,
                    left: Box::new(self.typed_value(value.index)),
                    right: Box::new(cpp_ir::Expression::Unsigned(stride as u128)),
                }),
            },
        }]
    }

    fn slice_place(&mut self, value: &SlicePlace) -> Vec<cpp_ir::Statement> {
        let Some(base) = self.contiguous_data(value.base, value.element) else {
            return Vec::new();
        };
        let stride = self.fixed_size(value.element);
        vec![cpp_ir::Statement::Assign {
            destination: cpp_ir::Expression::Name(evaluated_name(value.result)),
            source: cpp_ir::Expression::ByteOffset {
                base: Box::new(base),
                bytes: Box::new(cpp_ir::Expression::Binary {
                    operator: cpp_ir::BinaryOperator::Multiply,
                    left: Box::new(self.typed_value(value.start)),
                    right: Box::new(cpp_ir::Expression::Unsigned(stride as u128)),
                }),
            },
        }]
    }

    fn slice_view(&mut self, value: &SliceView) -> Vec<cpp_ir::Statement> {
        let ResolvedSliceAccess::Contiguous { element } = value.access else {
            self.errors
                .push(CppBackendError::MissingOperationRepresentation {
                    operation: value.site.id,
                    representation: "intrinsic SliceView",
                });
            return Vec::new();
        };
        let Some(base) = self.contiguous_data(value.base, element) else {
            return Vec::new();
        };
        let ty = self.post.values.entries[value.result.0 as usize].ty;
        let Some(NativeDescriptorLayout::View { pointer, length }) = self
            .layouts
            .get(&ty)
            .and_then(|layout| layout.native.clone())
        else {
            self.errors.push(CppBackendError::MissingLayout(ty));
            return Vec::new();
        };
        let stride = self.fixed_size(element);
        let data = cpp_ir::Expression::ByteOffset {
            base: Box::new(base),
            bytes: Box::new(cpp_ir::Expression::Binary {
                operator: cpp_ir::BinaryOperator::Multiply,
                left: Box::new(self.typed_value(value.start)),
                right: Box::new(cpp_ir::Expression::Unsigned(stride as u128)),
            }),
        };
        vec![
            expression_call(
                "corbo_store_pointer",
                vec![
                    byte_offset(cpp_ir::Expression::Name(value_name(value.result)), pointer),
                    data,
                ],
            ),
            cpp_ir::Statement::Assign {
                destination: self.size_at(byte_offset(
                    cpp_ir::Expression::Name(value_name(value.result)),
                    length,
                )),
                source: cpp_ir::Expression::Binary {
                    operator: cpp_ir::BinaryOperator::Subtract,
                    left: Box::new(self.typed_value(value.end)),
                    right: Box::new(self.typed_value(value.start)),
                },
            },
        ]
    }

    fn sequence_length(&mut self, value: &SequenceLength) -> Vec<cpp_ir::Statement> {
        let source_ty = self.evaluated_type(value.source);
        let descriptor = cpp_ir::Expression::Name(evaluated_name(value.source));
        let length = match self.post.types.entries[source_ty.0 as usize].kind {
            TypeDefinition::Array { length, .. } => cpp_ir::Expression::Unsigned(length as u128),
            TypeDefinition::GrowingSequence { .. } | TypeDefinition::GrowingString => {
                let Some(NativeDescriptorLayout::Region { length, .. }) = self
                    .layouts
                    .get(&source_ty)
                    .and_then(|layout| layout.native.clone())
                else {
                    self.errors.push(CppBackendError::MissingLayout(source_ty));
                    return Vec::new();
                };
                self.size_at(byte_offset(descriptor, length))
            }
            TypeDefinition::InlineUtf8 { .. } => {
                let Some(NativeDescriptorLayout::InlineUtf8 { length, .. }) = self
                    .layouts
                    .get(&source_ty)
                    .and_then(|layout| layout.native.clone())
                else {
                    self.errors.push(CppBackendError::MissingLayout(source_ty));
                    return Vec::new();
                };
                self.size_at(byte_offset(descriptor, length))
            }
            TypeDefinition::Slice { .. } | TypeDefinition::StrData | TypeDefinition::Utf8View => {
                let Some((view, view_ty)) = self.root_descriptor(value.source) else {
                    return Vec::new();
                };
                let Some(NativeDescriptorLayout::View { length, .. }) = self
                    .layouts
                    .get(&view_ty)
                    .and_then(|layout| layout.native.clone())
                else {
                    self.errors.push(CppBackendError::MissingLayout(view_ty));
                    return Vec::new();
                };
                self.size_at(byte_offset(view, length))
            }
            _ => {
                self.errors
                    .push(CppBackendError::MissingOperationRepresentation {
                        operation: value.site.id,
                        representation: "SequenceLength for non-contiguous type",
                    });
                return Vec::new();
            }
        };
        vec![cpp_ir::Statement::Assign {
            destination: self.typed_value(value.result),
            source: length,
        }]
    }

    fn contiguous_data(
        &mut self,
        source: EvaluatedPlaceId,
        _element: TypeId,
    ) -> Option<cpp_ir::Expression> {
        let ty = self.evaluated_type(source);
        let address = cpp_ir::Expression::Name(evaluated_name(source));
        match self.post.types.entries[ty.0 as usize].kind {
            TypeDefinition::Array { .. }
            | TypeDefinition::Slice { .. }
            | TypeDefinition::StrData => Some(address),
            TypeDefinition::GrowingSequence { .. } | TypeDefinition::GrowingString => {
                let data = match self
                    .layouts
                    .get(&ty)
                    .and_then(|layout| layout.native.clone())
                {
                    Some(NativeDescriptorLayout::Region { data, .. }) => data,
                    _ => {
                        self.errors.push(CppBackendError::MissingLayout(ty));
                        return None;
                    }
                };
                Some(cpp_ir::Expression::Call {
                    callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                    arguments: vec![byte_offset(address, data)],
                })
            }
            TypeDefinition::InlineUtf8 { .. } => {
                let data = match self
                    .layouts
                    .get(&ty)
                    .and_then(|layout| layout.native.clone())
                {
                    Some(NativeDescriptorLayout::InlineUtf8 { data, .. }) => data,
                    _ => {
                        self.errors.push(CppBackendError::MissingLayout(ty));
                        return None;
                    }
                };
                Some(byte_offset(address, data))
            }
            _ => {
                self.errors
                    .push(CppBackendError::MissingPlaceRepresentation(
                        self.post.objects.evaluated_places[source.0 as usize].definition,
                    ));
                None
            }
        }
    }

    fn root_descriptor(
        &mut self,
        source: EvaluatedPlaceId,
    ) -> Option<(cpp_ir::Expression, TypeId)> {
        let place_id = self.post.objects.evaluated_places[source.0 as usize].definition;
        let place = &self.post.objects.places[place_id.0 as usize];
        match place.root {
            PlaceRoot::Value(value) => Some((
                cpp_ir::Expression::Name(value_name(value)),
                self.post.values.entries[value.0 as usize].ty,
            )),
            PlaceRoot::Binding(binding) => Some((
                cpp_ir::Expression::Name(binding_name(binding)),
                self.post.scopes.bindings[binding.0 as usize].ty,
            )),
            PlaceRoot::Address(address) => {
                let value = self.value_for_entity(&EntityId::Address(address))?;
                Some((
                    cpp_ir::Expression::Name(value_name(value)),
                    self.post.objects.addresses[address.0 as usize].ty,
                ))
            }
            PlaceRoot::Reference(reference) => {
                let value = self.value_for_entity(&EntityId::Reference(reference))?;
                Some((
                    cpp_ir::Expression::Name(value_name(value)),
                    self.post.objects.references[reference.0 as usize].ty,
                ))
            }
            PlaceRoot::Collection(_) => {
                self.errors
                    .push(CppBackendError::MissingPlaceRepresentation(place_id));
                None
            }
        }
    }

    fn size_at(&self, address: cpp_ir::Expression) -> cpp_ir::Expression {
        cpp_ir::Expression::Unary {
            operator: cpp_ir::UnaryOperator::Dereference,
            operand: Box::new(cpp_ir::Expression::ReinterpretCast {
                ty: cpp_ir::Type::Size.pointer_to(true),
                value: Box::new(address),
            }),
        }
    }

    fn project_field(
        &mut self,
        base: EvaluatedPlaceId,
        field: FieldId,
        result: EvaluatedPlaceId,
    ) -> Vec<cpp_ir::Statement> {
        let base_ty = self.evaluated_type(base);
        let Some(offset) = self.field_offset(base_ty, field) else {
            return Vec::new();
        };
        vec![cpp_ir::Statement::Assign {
            destination: cpp_ir::Expression::Name(evaluated_name(result)),
            source: byte_offset(cpp_ir::Expression::Name(evaluated_name(base)), offset),
        }]
    }

    fn project_tuple(
        &mut self,
        base: EvaluatedPlaceId,
        position: u32,
        result: EvaluatedPlaceId,
    ) -> Vec<cpp_ir::Statement> {
        let base_ty = self.evaluated_type(base);
        let Some(element) = self.layouts.get(&base_ty).and_then(|layout| {
            layout
                .tuple_elements
                .iter()
                .find(|element| element.position == position)
        }) else {
            self.errors
                .push(CppBackendError::MissingPlaceRepresentation(
                    self.post.objects.evaluated_places[base.0 as usize].definition,
                ));
            return Vec::new();
        };
        vec![cpp_ir::Statement::Assign {
            destination: cpp_ir::Expression::Name(evaluated_name(result)),
            source: byte_offset(
                cpp_ir::Expression::Name(evaluated_name(base)),
                element.byte_offset,
            ),
        }]
    }

    fn evaluated_type(&self, evaluated: EvaluatedPlaceId) -> TypeId {
        let place = self.post.objects.evaluated_places[evaluated.0 as usize].definition;
        self.post.objects.places[place.0 as usize].ty
    }

    fn bindings_for_body(&self, body: BodyId) -> Vec<&Binding> {
        self.post
            .scopes
            .bindings
            .iter()
            .filter(|binding| self.scope_belongs_to_body(binding.scope, body))
            .collect()
    }

    fn scopes_for_body(&self, body: BodyId) -> Vec<&Scope> {
        self.post
            .scopes
            .entries
            .iter()
            .filter(|scope| self.scope_belongs_to_body(scope.id, body))
            .collect()
    }

    fn scope_belongs_to_body(&self, mut scope: ScopeId, body: BodyId) -> bool {
        loop {
            match self.post.scopes.entries[scope.0 as usize].context {
                ScopeContext::Body(candidate)
                | ScopeContext::Unreachable {
                    body: candidate, ..
                } => {
                    return candidate == body;
                }
                _ => match self.post.scopes.entries[scope.0 as usize].lexical_parent {
                    Some(parent) => scope = parent,
                    None => return false,
                },
            }
        }
    }

    fn field_offset(&mut self, ty: TypeId, field: FieldId) -> Option<u64> {
        let Some(layout) = self.layouts.get(&ty).copied() else {
            self.errors.push(CppBackendError::MissingLayout(ty));
            return None;
        };
        let Some(field_layout) = layout
            .fields
            .iter()
            .find(|candidate| candidate.field == field)
        else {
            self.errors
                .push(CppBackendError::MissingFieldLayout { ty, field });
            return None;
        };
        Some(field_layout.byte_offset)
    }

    fn bind_constant(&mut self, value: &Value) -> Vec<cpp_ir::Statement> {
        let constant = match &value.definition {
            ValueDefinition::Constant(id) => self.post.declarations.constants[id.0 as usize]
                .value
                .clone(),
            ValueDefinition::ConfiguredConstant { value, .. } => value.clone(),
            _ => return Vec::new(),
        };
        let initializer = match constant {
            ConstantValue::Integer(number) => Some(cpp_ir::Expression::Signed(number)),
            ConstantValue::Unsigned(number) => Some(cpp_ir::Expression::Unsigned(number)),
            ConstantValue::Float32(bits) => Some(cpp_ir::Expression::FloatBits {
                bits: bits as u64,
                width: 32,
            }),
            ConstantValue::Float64(bits) => Some(cpp_ir::Expression::FloatBits { bits, width: 64 }),
            ConstantValue::Boolean(value) => Some(cpp_ir::Expression::Boolean(value)),
            ConstantValue::Unit => None,
            ConstantValue::Utf8(bytes) => {
                return self.store_utf8_descriptor(
                    cpp_ir::Expression::Name(value_name(value.id)),
                    value.ty,
                    bytes,
                );
            }
        };
        let local = format!("constant_{}", value.id.0);
        vec![
            cpp_ir::Statement::Declare {
                ty: cpp_ir::Type::Named(type_name(value.ty)),
                name: local.clone(),
                initializer,
            },
            cpp_ir::Statement::Assign {
                destination: cpp_ir::Expression::Name(value_name(value.id)),
                source: cpp_ir::Expression::Unary {
                    operator: cpp_ir::UnaryOperator::AddressOf,
                    operand: Box::new(cpp_ir::Expression::Name(local)),
                },
            },
        ]
    }

    fn cursor_expression(&mut self, id: CursorExpressionId) -> cpp_ir::Expression {
        let expression = self.planned.storage.cursors[id.0 as usize].clone();
        match expression.kind {
            CursorExpressionKind::ScopeUpperLimit(_) => cpp_ir::Expression::Member {
                base: Box::new(cpp_ir::Expression::Name("corbo_fixed_stack".to_owned())),
                member: "capacity".to_owned(),
                through_pointer: false,
            },
            CursorExpressionKind::IncomingScopeCursor(scope) => {
                cpp_ir::Expression::Name(scope_cursor_name(scope))
            }
            CursorExpressionKind::AdvanceByType { base, ty } => {
                let Some(layout) = self.layouts.get(&ty).copied() else {
                    self.errors.push(CppBackendError::MissingLayout(ty));
                    return cpp_ir::Expression::Unsigned(0);
                };
                let LayoutSize::Fixed(size) = layout.size else {
                    self.errors.push(CppBackendError::RuntimeSizedLayout(ty));
                    return cpp_ir::Expression::Unsigned(0);
                };
                cpp_ir::Expression::Binary {
                    operator: cpp_ir::BinaryOperator::Add,
                    left: Box::new(cpp_ir::Expression::Call {
                        callee: Box::new(cpp_ir::Expression::Name("corbo_align_size".to_owned())),
                        arguments: vec![
                            self.cursor_expression(base),
                            cpp_ir::Expression::Unsigned(layout.alignment as u128),
                        ],
                    }),
                    right: Box::new(cpp_ir::Expression::Unsigned(size as u128)),
                }
            }
            CursorExpressionKind::Align { base, alignment } => cpp_ir::Expression::Call {
                callee: Box::new(cpp_ir::Expression::Name("corbo_align_size".to_owned())),
                arguments: vec![
                    self.cursor_expression(base),
                    cpp_ir::Expression::Unsigned(alignment as u128),
                ],
            },
            CursorExpressionKind::AdvanceFixedBytes { base, bytes } => cpp_ir::Expression::Binary {
                operator: cpp_ir::BinaryOperator::Add,
                left: Box::new(self.cursor_expression(base)),
                right: Box::new(cpp_ir::Expression::Unsigned(bytes as u128)),
            },
            CursorExpressionKind::AdvancePoolSlots {
                base,
                element,
                count,
            } => {
                let Some(layout) = self.layouts.get(&element).copied() else {
                    self.errors.push(CppBackendError::MissingLayout(element));
                    return cpp_ir::Expression::Unsigned(0);
                };
                let LayoutSize::Fixed(size) = layout.size else {
                    self.errors
                        .push(CppBackendError::RuntimeSizedLayout(element));
                    return cpp_ir::Expression::Unsigned(0);
                };
                cpp_ir::Expression::Binary {
                    operator: cpp_ir::BinaryOperator::Add,
                    left: Box::new(cpp_ir::Expression::Call {
                        callee: Box::new(cpp_ir::Expression::Name("corbo_align_size".to_owned())),
                        arguments: vec![
                            self.cursor_expression(base),
                            cpp_ir::Expression::Unsigned(layout.alignment as u128),
                        ],
                    }),
                    right: Box::new(cpp_ir::Expression::Binary {
                        operator: cpp_ir::BinaryOperator::Multiply,
                        left: Box::new(cpp_ir::Expression::Unsigned(size as u128)),
                        right: Box::new(self.typed_value(count)),
                    }),
                }
            }
            CursorExpressionKind::AdvanceBytes { base, bytes }
            | CursorExpressionKind::Offset { base, bytes } => cpp_ir::Expression::Binary {
                operator: cpp_ir::BinaryOperator::Add,
                left: Box::new(self.cursor_expression(base)),
                right: Box::new(self.typed_value(bytes)),
            },
            CursorExpressionKind::AdvanceScaledBytes { base, count, width } => {
                cpp_ir::Expression::Binary {
                    operator: cpp_ir::BinaryOperator::Add,
                    left: Box::new(self.cursor_expression(base)),
                    right: Box::new(cpp_ir::Expression::Binary {
                        operator: cpp_ir::BinaryOperator::Multiply,
                        left: Box::new(self.typed_value(count)),
                        right: Box::new(cpp_ir::Expression::Unsigned(width as u128)),
                    }),
                }
            }
            CursorExpressionKind::Entry(snapshot) => {
                self.cursor_expression(self.planned.storage.snapshots[snapshot.0 as usize].cursor)
            }
            CursorExpressionKind::Merge(guarded) => {
                let mut incoming = std::iter::once(&guarded.first).chain(&guarded.rest).rev();
                let last = incoming.next().expect("NonEmpty cursor merge");
                let mut result = self.cursor_expression(last.cursor);
                for alternative in incoming {
                    result = cpp_ir::Expression::Conditional {
                        condition: Box::new(self.predicate(alternative.guard)),
                        when_true: Box::new(self.cursor_expression(alternative.cursor)),
                        when_false: Box::new(result),
                    };
                }
                result
            }
        }
    }

    fn scope_entry_cursor(&mut self, scope: ScopeId) -> cpp_ir::Expression {
        let Some(entry) = self
            .planned
            .storage
            .scope_entries
            .iter()
            .find(|entry| entry.scope == scope)
        else {
            return cpp_ir::Expression::Unsigned(0);
        };
        let cursor = entry.cursor;
        if matches!(
            self.planned.storage.cursors[cursor.0 as usize].kind,
            CursorExpressionKind::IncomingScopeCursor(candidate) if candidate == scope
        ) && matches!(
            self.post.scopes.entries[scope.0 as usize].entry,
            ScopeEntry::BodyRoot { .. }
        ) {
            cpp_ir::Expression::Member {
                base: Box::new(cpp_ir::Expression::Name("corbo_fixed_stack".to_owned())),
                member: "cursor".to_owned(),
                through_pointer: false,
            }
        } else {
            self.cursor_expression(cursor)
        }
    }

    fn typed_value(&self, value: ValueId) -> cpp_ir::Expression {
        let ty = self.post.values.entries[value.0 as usize].ty;
        cpp_ir::Expression::Unary {
            operator: cpp_ir::UnaryOperator::Dereference,
            operand: Box::new(cpp_ir::Expression::ReinterpretCast {
                ty: cpp_ir::Type::Named(type_name(ty)).pointer_to(true),
                value: Box::new(cpp_ir::Expression::Name(value_name(value))),
            }),
        }
    }

    fn async_frame(&self, body: BodyId) -> Option<&AsyncFrameLayout> {
        self.planned
            .async_states
            .frames
            .iter()
            .find(|frame| frame.body == body)
    }

    fn async_state_discriminant(&self, frame: &AsyncFrameLayout) -> cpp_ir::Expression {
        cpp_ir::Expression::Call {
            callee: Box::new(cpp_ir::Expression::Name(
                "corbo_read_discriminant".to_owned(),
            )),
            arguments: vec![
                byte_offset(
                    cpp_ir::Expression::Name("state".to_owned()),
                    frame.state_offset,
                ),
                cpp_ir::Expression::Unsigned(8),
            ],
        }
    }

    fn set_async_state(&self, suspension: SuspensionId) -> Vec<cpp_ir::Statement> {
        let Some(frame) = self.current_async.and_then(|body| self.async_frame(body)) else {
            return Vec::new();
        };
        let Some(transition) = frame
            .transitions
            .iter()
            .find(|value| value.suspension == suspension)
        else {
            return Vec::new();
        };
        vec![expression_call(
            "corbo_write_discriminant",
            vec![
                byte_offset(
                    cpp_ir::Expression::Name("state".to_owned()),
                    frame.state_offset,
                ),
                cpp_ir::Expression::Unsigned(8),
                cpp_ir::Expression::Unsigned(transition.discriminant as u128),
            ],
        )]
    }

    fn predicate(&mut self, id: PredicateId) -> cpp_ir::Expression {
        let predicate = self.post.execution.predicates[id.0 as usize].kind.clone();
        match predicate {
            PredicateKind::Always => cpp_ir::Expression::Boolean(true),
            PredicateKind::Boolean { value, expected } => {
                let value = self.typed_value(value);
                if expected {
                    value
                } else {
                    cpp_ir::Expression::Unary {
                        operator: cpp_ir::UnaryOperator::LogicalNot,
                        operand: Box::new(value),
                    }
                }
            }
            PredicateKind::All(predicates) => {
                self.combine_predicates(predicates, cpp_ir::BinaryOperator::LogicalAnd, true)
            }
            PredicateKind::Any(predicates) => {
                self.combine_predicates(predicates, cpp_ir::BinaryOperator::LogicalOr, false)
            }
            PredicateKind::Not(predicate) => cpp_ir::Expression::Unary {
                operator: cpp_ir::UnaryOperator::LogicalNot,
                operand: Box::new(self.predicate(predicate)),
            },
            PredicateKind::Variant { value, variant } => self.variant_predicate(value, variant),
            PredicateKind::Pattern { subject, test } => self.pattern_test(subject, &test),
            PredicateKind::TypeCopiesByValue(_) => {
                self.errors
                    .push(CppBackendError::MissingPredicateRepresentation(id));
                cpp_ir::Expression::Boolean(false)
            }
            PredicateKind::ValidTextRange { source, start, end } => cpp_ir::Expression::Call {
                callee: Box::new(cpp_ir::Expression::Name(
                    "corbo_valid_text_range".to_owned(),
                )),
                arguments: vec![
                    cpp_ir::Expression::Name(evaluated_name(source)),
                    self.typed_value(start),
                    self.typed_value(end),
                ],
            },
            PredicateKind::PollReady { source } => {
                cpp_ir::Expression::Name(await_ready_name(source))
            }
            PredicateKind::RuntimeReady { operation } => {
                cpp_ir::Expression::Name(runtime_ready_name(operation))
            }
            PredicateKind::DestructorVariant { .. } => {
                self.errors
                    .push(CppBackendError::MissingPredicateRepresentation(id));
                cpp_ir::Expression::Boolean(false)
            }
        }
    }

    fn pattern_test(&mut self, value: ValueId, test: &PatternTest) -> cpp_ir::Expression {
        let ty = self.post.values.entries[value.0 as usize].ty;
        self.pattern_at(cpp_ir::Expression::Name(value_name(value)), ty, test, value)
    }

    fn pattern_at(
        &mut self,
        address: cpp_ir::Expression,
        ty: TypeId,
        test: &PatternTest,
        subject: ValueId,
    ) -> cpp_ir::Expression {
        match test {
            PatternTest::Any | PatternTest::Unit => cpp_ir::Expression::Boolean(true),
            PatternTest::Dereference(inner) => {
                let target = match self.post.types.entries[ty.0 as usize].kind {
                    TypeDefinition::Reference { target, .. } => target,
                    TypeDefinition::Allocation { content } => content,
                    _ => {
                        self.errors
                            .push(CppBackendError::MissingPredicateRepresentation(
                                PredicateId(u32::MAX),
                            ));
                        return cpp_ir::Expression::Boolean(false);
                    }
                };
                let pointer_offset = match self
                    .layouts
                    .get(&ty)
                    .and_then(|layout| layout.native.clone())
                {
                    Some(NativeDescriptorLayout::Allocation { slot, .. }) => slot,
                    _ => 0,
                };
                self.pattern_at(
                    cpp_ir::Expression::Call {
                        callee: Box::new(cpp_ir::Expression::Name("corbo_load_pointer".to_owned())),
                        arguments: vec![byte_offset(address, pointer_offset)],
                    },
                    target,
                    inner,
                    subject,
                )
            }
            PatternTest::Tuple(parts) => {
                let Some(layout) = self.layouts.get(&ty).copied() else {
                    self.errors.push(CppBackendError::MissingLayout(ty));
                    return cpp_ir::Expression::Boolean(false);
                };
                let elements = layout.tuple_elements.clone();
                let expressions = parts
                    .iter()
                    .enumerate()
                    .filter_map(|(position, part)| {
                        let element = elements
                            .iter()
                            .find(|element| element.position == position as u32)?;
                        let element_ty = self.planned.layouts.layouts[element.layout.0 as usize].ty;
                        Some(self.pattern_at(
                            byte_offset(address.clone(), element.byte_offset),
                            element_ty,
                            part,
                            subject,
                        ))
                    })
                    .collect();
                combine_expressions(expressions, cpp_ir::BinaryOperator::LogicalAnd, true)
            }
            PatternTest::Variant { variant, fields } => {
                let Some(layout) = self.layouts.get(&ty).copied() else {
                    self.errors.push(CppBackendError::MissingLayout(ty));
                    return cpp_ir::Expression::Boolean(false);
                };
                let Some(enumeration) = layout.variant.clone() else {
                    self.errors
                        .push(CppBackendError::MissingPredicateRepresentation(
                            PredicateId(u32::MAX),
                        ));
                    return cpp_ir::Expression::Boolean(false);
                };
                let Some(variant_layout) = enumeration
                    .variants
                    .iter()
                    .find(|candidate| candidate.variant == *variant)
                    .cloned()
                else {
                    self.errors
                        .push(CppBackendError::MissingPredicateRepresentation(
                            PredicateId(u32::MAX),
                        ));
                    return cpp_ir::Expression::Boolean(false);
                };
                let mut expressions = vec![cpp_ir::Expression::Binary {
                    operator: cpp_ir::BinaryOperator::Equal,
                    left: Box::new(cpp_ir::Expression::Call {
                        callee: Box::new(cpp_ir::Expression::Name(
                            "corbo_read_discriminant".to_owned(),
                        )),
                        arguments: vec![
                            address.clone(),
                            cpp_ir::Expression::Unsigned(enumeration.discriminant_bytes as u128),
                        ],
                    }),
                    right: Box::new(cpp_ir::Expression::Unsigned(
                        variant_layout.discriminant as u128,
                    )),
                }];
                for (field, test) in fields {
                    let Some(field_layout) = variant_layout
                        .fields
                        .iter()
                        .find(|candidate| candidate.field == *field)
                    else {
                        self.errors
                            .push(CppBackendError::MissingFieldLayout { ty, field: *field });
                        continue;
                    };
                    expressions.push(self.pattern_at(
                        byte_offset(
                            address.clone(),
                            enumeration.payload_offset + field_layout.byte_offset,
                        ),
                        self.planned.layouts.layouts[field_layout.layout.0 as usize].ty,
                        test,
                        subject,
                    ));
                }
                combine_expressions(expressions, cpp_ir::BinaryOperator::LogicalAnd, true)
            }
        }
    }

    fn combine_predicates(
        &mut self,
        predicates: Vec<PredicateId>,
        operator: cpp_ir::BinaryOperator,
        empty: bool,
    ) -> cpp_ir::Expression {
        predicates
            .into_iter()
            .map(|predicate| self.predicate(predicate))
            .reduce(|left, right| cpp_ir::Expression::Binary {
                operator,
                left: Box::new(left),
                right: Box::new(right),
            })
            .unwrap_or(cpp_ir::Expression::Boolean(empty))
    }

    fn variant_predicate(&mut self, value: ValueId, variant: VariantId) -> cpp_ir::Expression {
        let ty = self.post.values.entries[value.0 as usize].ty;
        let Some(layout) = self.layouts.get(&ty).copied() else {
            self.errors.push(CppBackendError::MissingLayout(ty));
            return cpp_ir::Expression::Boolean(false);
        };
        let Some(enumeration) = &layout.variant else {
            self.errors
                .push(CppBackendError::MissingPredicateRepresentation(
                    PredicateId(0),
                ));
            return cpp_ir::Expression::Boolean(false);
        };
        let discriminant = enumeration
            .variants
            .iter()
            .find(|candidate| candidate.variant == variant)
            .map(|candidate| candidate.discriminant)
            .unwrap_or(u64::MAX);
        cpp_ir::Expression::Binary {
            operator: cpp_ir::BinaryOperator::Equal,
            left: Box::new(cpp_ir::Expression::Call {
                callee: Box::new(cpp_ir::Expression::Name(
                    "corbo_read_discriminant".to_owned(),
                )),
                arguments: vec![
                    cpp_ir::Expression::Name(value_name(value)),
                    cpp_ir::Expression::Unsigned(enumeration.discriminant_bytes as u128),
                ],
            }),
            right: Box::new(cpp_ir::Expression::Unsigned(discriminant as u128)),
        }
    }

    fn route(&mut self, moment: &ExecutionMoment) -> Vec<cpp_ir::Statement> {
        let mut statements = Vec::new();
        let mut has_conditional = false;
        let mut has_unconditional = false;
        for edge in &self.post.execution.edges {
            match edge {
                ExecutionEdge::Sequence(edge) if edge.before == moment.id => {
                    has_unconditional = true;
                    statements.extend(self.route_to(edge.before, edge.after));
                }
                ExecutionEdge::Conditional(edge) if edge.from == moment.id => {
                    has_conditional = true;
                    let mut routed = self.route_to(edge.from, edge.to);
                    statements.push(cpp_ir::Statement::If {
                        condition: self.predicate(edge.guard),
                        then_block: cpp_ir::Block {
                            statements: std::mem::take(&mut routed),
                        },
                        else_block: None,
                    });
                }
                ExecutionEdge::LoopBack(edge) if edge.from == moment.id => {
                    has_unconditional = true;
                    statements.extend(self.route_to(edge.from, edge.to));
                }
                ExecutionEdge::Resume(edge) if edge.to == moment.id => {}
                ExecutionEdge::PollRetry { from, poll, .. } if *from == moment.id => {
                    has_unconditional = true;
                    statements.push(cpp_ir::Statement::Goto(moment_label(*poll)));
                }
                ExecutionEdge::Call(_)
                | ExecutionEdge::Return(_)
                | ExecutionEdge::Suspend(_)
                | ExecutionEdge::AwaitBody { .. }
                | ExecutionEdge::Sequence(_)
                | ExecutionEdge::Conditional(_)
                | ExecutionEdge::LoopBack(_)
                | ExecutionEdge::Resume(_)
                | ExecutionEdge::PollRetry { .. } => {}
            }
        }
        if has_conditional && !has_unconditional {
            // Conditional successors are complete in the verified execution
            // graph. Keep the generated C++ graph closed: lexical label order
            // must never become an implicit successor when no guard matches.
            statements.push(expression_call(
                "corbo_fail",
                vec![cpp_ir::Expression::StringLiteral(
                    b"corbo: execution graph has no matching edge".to_vec(),
                )],
            ));
        }
        statements
    }

    fn route_to(
        &mut self,
        from: ExecutionMomentId,
        to: ExecutionMomentId,
    ) -> Vec<cpp_ir::Statement> {
        let transfers = self
            .planned
            .storage
            .edge_transfers
            .iter()
            .filter(|transfer| transfer.from == from && transfer.to == to)
            .cloned()
            .collect::<Vec<_>>();
        let mut statements = Vec::new();
        for counter in &self.planned.storage.iteration_counters {
            if counter
                .entry_edges
                .iter()
                .any(|edge| edge.from == from && edge.to == to)
            {
                statements.push(cpp_ir::Statement::Assign {
                    destination: cpp_ir::Expression::Name(iteration_name(counter.coordinate)),
                    source: cpp_ir::Expression::Unsigned(0),
                });
            }
            if counter
                .back_edges
                .iter()
                .any(|edge| edge.from == from && edge.to == to)
            {
                statements.push(cpp_ir::Statement::Assign {
                    destination: cpp_ir::Expression::Name(iteration_name(counter.coordinate)),
                    source: cpp_ir::Expression::Binary {
                        operator: cpp_ir::BinaryOperator::Add,
                        left: Box::new(cpp_ir::Expression::Name(iteration_name(
                            counter.coordinate,
                        ))),
                        right: Box::new(cpp_ir::Expression::Unsigned(1)),
                    },
                });
            }
        }
        for transfer in transfers {
            for statement in self.materialize_transfer(transfer.destination, transfer.source) {
                statements.push(self.guarded(transfer.guard, statement));
            }
        }
        statements.push(cpp_ir::Statement::Goto(moment_label(to)));
        statements
    }

    fn entry_definition(&mut self, entry: FunctionInstanceId) -> Option<cpp_ir::Function> {
        let instance = &self.post.declarations.instances[entry.0 as usize];
        if instance.body.is_none() {
            self.errors
                .push(CppBackendError::MissingFunctionBody(entry));
            return None;
        }
        let signature = &self.post.declarations.signatures[instance.signature.0 as usize];
        let result_size = match self
            .layouts
            .get(&signature.result)
            .map(|layout| &layout.size)
        {
            Some(LayoutSize::Fixed(size)) => (*size).max(1),
            _ => {
                self.errors
                    .push(CppBackendError::MissingResultLayout(entry));
                return None;
            }
        };
        let fixed = self.stack_budget(DataStackKind::FixedValues);
        let regions = self.stack_budget(DataStackKind::GrowingRegions);
        Some(cpp_ir::Function {
            linkage: cpp_ir::Linkage::External,
            result: cpp_ir::Type::Signed { bits: 32 },
            name: "main".to_owned(),
            parameters: vec![
                cpp_ir::Parameter {
                    ty: cpp_ir::Type::Signed { bits: 32 },
                    name: "argc".to_owned(),
                },
                cpp_ir::Parameter {
                    ty: cpp_ir::Type::Char.pointer_to(true).pointer_to(true),
                    name: "argv".to_owned(),
                },
            ],
            body: Some(cpp_ir::Block {
                statements: vec![
                    expression_call(
                        "corbo_stack_open",
                        vec![cpp_ir::Expression::Unsigned(fixed as u128)],
                    ),
                    expression_call(
                        "corbo_regions_configure",
                        vec![
                            cpp_ir::Expression::Unsigned(regions as u128),
                            cpp_ir::Expression::Unsigned(self.region_size() as u128),
                        ],
                    ),
                    expression_call(
                        "corbo_process_args_setup",
                        vec![
                            cpp_ir::Expression::Name("argc".to_owned()),
                            cpp_ir::Expression::Name("argv".to_owned()),
                        ],
                    ),
                    cpp_ir::Statement::Declare {
                        ty: cpp_ir::Type::Array {
                            element: Box::new(cpp_ir::Type::Unsigned { bits: 8 }),
                            length: result_size,
                        },
                        name: "result".to_owned(),
                        initializer: None,
                    },
                    expression_call(
                        &format!("corbo_generated::{}", function_name(entry)),
                        vec![
                            cpp_ir::Expression::Name("result".to_owned()),
                            cpp_ir::Expression::Null,
                            cpp_ir::Expression::Null,
                        ],
                    ),
                    expression_call("corbo_regions_close", Vec::new()),
                    expression_call("corbo_stack_close", Vec::new()),
                    cpp_ir::Statement::Return(Some(cpp_ir::Expression::Signed(0))),
                ],
            }),
        })
    }

    fn stack_budget(&self, kind: DataStackKind) -> u64 {
        self.planned
            .storage
            .stacks
            .iter()
            .find(|stack| std::mem::discriminant(&stack.kind) == std::mem::discriminant(&kind))
            .map(|stack| match stack.capacity {
                MemoryBudget::Explicit(bytes) | MemoryBudget::Inferred(bytes) => bytes,
                MemoryBudget::PlatformDefault => 0,
            })
            .unwrap_or(0)
    }

    fn region_size(&self) -> u64 {
        self.planned
            .storage
            .regions
            .iter()
            .filter_map(|region| match region.size {
                MemoryBudget::Explicit(bytes) | MemoryBudget::Inferred(bytes) => Some(bytes),
                MemoryBudget::PlatformDefault => None,
            })
            .max()
            .unwrap_or(0)
    }
}

fn function_shell(instance: FunctionInstanceId, body: Option<cpp_ir::Block>) -> cpp_ir::Function {
    cpp_ir::Function {
        linkage: cpp_ir::Linkage::Internal,
        result: cpp_ir::Type::Void,
        name: function_name(instance),
        parameters: vec![
            cpp_ir::Parameter {
                ty: cpp_ir::Type::Void.pointer_to(true),
                name: "output".to_owned(),
            },
            cpp_ir::Parameter {
                ty: cpp_ir::Type::Void.pointer_to(true).pointer_to(true),
                name: "arguments".to_owned(),
            },
            cpp_ir::Parameter {
                ty: cpp_ir::Type::Void.pointer_to(true),
                name: "environment".to_owned(),
            },
        ],
        body,
    }
}

fn async_poll_shell(instance: FunctionInstanceId, body: Option<cpp_ir::Block>) -> cpp_ir::Function {
    cpp_ir::Function {
        linkage: cpp_ir::Linkage::Internal,
        result: cpp_ir::Type::Bool,
        name: async_poll_name(instance),
        parameters: vec![
            cpp_ir::Parameter {
                ty: cpp_ir::Type::Void.pointer_to(true),
                name: "state".to_owned(),
            },
            cpp_ir::Parameter {
                ty: cpp_ir::Type::Void.pointer_to(true),
                name: "output".to_owned(),
            },
            cpp_ir::Parameter {
                ty: cpp_ir::Type::Named("corbo_context".to_owned()).pointer_to(true),
                name: "context".to_owned(),
            },
        ],
        body,
    }
}

fn async_poll_name(instance: FunctionInstanceId) -> String {
    format!("corbo_poll_function_{}", instance.0)
}

fn expression_call(name: &str, arguments: Vec<cpp_ir::Expression>) -> cpp_ir::Statement {
    cpp_ir::Statement::Expression(cpp_ir::Expression::Call {
        callee: Box::new(cpp_ir::Expression::Name(name.to_owned())),
        arguments,
    })
}

fn numeric_type(number: NumericType) -> cpp_ir::Type {
    match number {
        NumericType::I32 => cpp_ir::Type::Signed { bits: 32 },
        NumericType::I64 => cpp_ir::Type::Signed { bits: 64 },
        NumericType::U8 => cpp_ir::Type::Unsigned { bits: 8 },
        NumericType::U16 => cpp_ir::Type::Unsigned { bits: 16 },
        NumericType::U32 => cpp_ir::Type::Unsigned { bits: 32 },
        NumericType::U64 => cpp_ir::Type::Unsigned { bits: 64 },
        NumericType::Usize => cpp_ir::Type::Size,
        NumericType::F32 => cpp_ir::Type::Float { bits: 32 },
        NumericType::F64 => cpp_ir::Type::Float { bits: 64 },
    }
}

fn type_name(ty: TypeId) -> String {
    format!("corbo_type_{}", ty.0)
}
fn value_name(value: ValueId) -> String {
    format!("value_{}", value.0)
}
fn await_ready_name(value: ValueId) -> String {
    format!("await_ready_{}", value.0)
}
fn runtime_ready_name(operation: OperationId) -> String {
    format!("runtime_ready_{}", operation.0)
}
fn binding_name(binding: BindingId) -> String {
    format!("binding_{}", binding.0)
}
fn evaluated_name(place: EvaluatedPlaceId) -> String {
    format!("evaluated_{}", place.0)
}
fn scope_cursor_name(scope: ScopeId) -> String {
    format!("scope_cursor_{}", scope.0)
}
fn moment_label(moment: ExecutionMomentId) -> String {
    format!("moment_{}", moment.0)
}

fn iteration_name(iteration: IterationVariableId) -> String {
    format!("iteration_{}", iteration.0)
}
fn function_name(function: FunctionInstanceId) -> String {
    format!("corbo_function_{}", function.0)
}
fn destructor_name(destructor: DestructorId) -> String {
    format!("corbo_destructor_{}", destructor.0)
}
fn region_mark_name(class: RegionClassId) -> String {
    format!("region_mark_{}", class.0)
}

fn byte_offset(base: cpp_ir::Expression, bytes: u64) -> cpp_ir::Expression {
    cpp_ir::Expression::ByteOffset {
        base: Box::new(base),
        bytes: Box::new(cpp_ir::Expression::Unsigned(bytes as u128)),
    }
}

fn reinterpret_pointer(name: &str, value: cpp_ir::Expression) -> cpp_ir::Expression {
    cpp_ir::Expression::ReinterpretCast {
        ty: cpp_ir::Type::Named(name.to_owned()).pointer_to(true),
        value: Box::new(value),
    }
}

fn combine_expressions(
    expressions: Vec<cpp_ir::Expression>,
    operator: cpp_ir::BinaryOperator,
    empty: bool,
) -> cpp_ir::Expression {
    expressions
        .into_iter()
        .reduce(|left, right| cpp_ir::Expression::Binary {
            operator,
            left: Box::new(left),
            right: Box::new(right),
        })
        .unwrap_or(cpp_ir::Expression::Boolean(empty))
}

fn constant_expression(value: &ConstantValue) -> Option<cpp_ir::Expression> {
    match value {
        ConstantValue::Integer(value) => Some(cpp_ir::Expression::Signed(*value)),
        ConstantValue::Unsigned(value) => Some(cpp_ir::Expression::Unsigned(*value)),
        ConstantValue::Float32(bits) => Some(cpp_ir::Expression::FloatBits {
            bits: u64::from(*bits),
            width: 32,
        }),
        ConstantValue::Float64(bits) => Some(cpp_ir::Expression::FloatBits {
            bits: *bits,
            width: 64,
        }),
        ConstantValue::Boolean(value) => Some(cpp_ir::Expression::Boolean(*value)),
        ConstantValue::Utf8(_) | ConstantValue::Unit => None,
    }
}

fn intrinsic_name(intrinsic: IntrinsicId) -> String {
    format!("corbo_intrinsic_{}", intrinsic.0)
}

fn foreign_operand_expression(operand: &ForeignOperand) -> String {
    match operand.mode {
        ForeignOperandMode::ScalarValue => format!(
            "(*reinterpret_cast<corbo_type_{}*>(value_{}))",
            operand.ty.0, operand.value.0
        ),
        ForeignOperandMode::SharedStorage | ForeignOperandMode::MutableStorage => {
            format!("value_{}", operand.value.0)
        }
    }
}

fn cpp_type_spelling(ty: &TypeDefinition) -> &'static str {
    match ty {
        TypeDefinition::Numeric(NumericType::I32) => "std::int32_t",
        TypeDefinition::Numeric(NumericType::I64) => "std::int64_t",
        TypeDefinition::Numeric(NumericType::U8) => "std::uint8_t",
        TypeDefinition::Numeric(NumericType::U16) => "std::uint16_t",
        TypeDefinition::Numeric(NumericType::U32) => "std::uint32_t",
        TypeDefinition::Numeric(NumericType::U64) => "std::uint64_t",
        TypeDefinition::Numeric(NumericType::Usize) => "std::size_t",
        TypeDefinition::Numeric(NumericType::F32) => "float",
        TypeDefinition::Numeric(NumericType::F64) => "double",
        TypeDefinition::Boolean => "bool",
        TypeDefinition::Unit => "void",
        _ => "void",
    }
}

fn external_type_spelling(ty: &TypeDefinition) -> Option<&'static str> {
    match ty {
        TypeDefinition::Numeric(_) | TypeDefinition::Boolean | TypeDefinition::Unit => {
            Some(cpp_type_spelling(ty))
        }
        _ => None,
    }
}

fn numeric_spelling(ty: NumericType) -> &'static str {
    match ty {
        NumericType::I32 => "std::int32_t",
        NumericType::I64 => "std::int64_t",
        NumericType::U8 => "std::uint8_t",
        NumericType::U16 => "std::uint16_t",
        NumericType::U32 => "std::uint32_t",
        NumericType::U64 => "std::uint64_t",
        NumericType::Usize => "std::size_t",
        NumericType::F32 => "float",
        NumericType::F64 => "double",
    }
}
