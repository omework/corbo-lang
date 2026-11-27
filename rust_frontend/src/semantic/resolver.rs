mod annotations;
mod asynchronous;
mod callables;
mod configuration;
mod constants;
mod contracts;
mod control;
mod dereference;
mod foreign;
mod initialization;
mod iteration;
mod native;
mod nominals;
mod overloads;
mod packages;
mod patterns;
mod prelude;
mod primitives;
mod propagation;
mod replication;
mod slices;
mod symbolic;
mod unreachable;
mod values;
use crate::{
    Span,
    ast::{self, AnnotationSyntax, NodeKind, TypeSyntax},
    post_ast::*,
};
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DiagnosticKind {
    UnresolvedName,
    UnreachableStatement,
    DuplicateDeclaration,
    TypeMismatch,
    InvalidType,
    InvalidCall,
    ImplementationLimit,
    IncompleteRepresentation,
}
#[derive(Debug, Clone)]
pub struct Diagnostic {
    pub file: SourceFileId,
    pub kind: DiagnosticKind,
    pub span: Span,
    pub message: String,
    pub related: Vec<Span>,
}
#[derive(Debug)]
pub struct ResolvedProgram {
    pub syntax: ast::ParsedUnit,
    pub logical: LogicalDestinationResult,
    /// Non-blocking diagnostics for source proven unreachable.
    pub warnings: Vec<Diagnostic>,
}
type Result<T> = std::result::Result<T, Diagnostic>;

pub fn resolve(syntax: ast::ParsedUnit) -> std::result::Result<ResolvedProgram, Vec<Diagnostic>> {
    let target = host_target();
    let result = Resolver::new(&syntax, target)
        .and_then(|mut r| {
            let logical = r.run()?;
            Ok((logical, r.warnings))
        })
        .and_then(|(logical, warnings)| {
            super::validate_population(&logical).map_err(|errors| Diagnostic {
                file: SourceFileId(0),
                kind: DiagnosticKind::IncompleteRepresentation,
                span: syntax.ast.nodes[syntax.ast.root.0].span,
                message: errors
                    .into_iter()
                    .map(|e| e.0)
                    .collect::<Vec<_>>()
                    .join("; "),
                related: vec![],
            })?;
            Ok((logical, warnings))
        });
    result
        .map(|(logical, warnings)| ResolvedProgram {
            syntax,
            logical,
            warnings,
        })
        .map_err(|error| vec![error])
}

fn host_target() -> TargetDescription {
    TargetDescription {
        os: std::env::consts::OS.into(),
        family: std::env::consts::FAMILY.into(),
        architecture: std::env::consts::ARCH.into(),
        pointer_bits: usize::BITS as u16,
        endian: if cfg!(target_endian = "little") {
            Endian::Little
        } else {
            Endian::Big
        },
        abi: AbiId(0),
    }
}

pub use packages::{ParsedModule, ResolvedPackage, resolve_package, resolve_package_for_target};

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
enum TypeKey {
    NumericConversionError,
    Never,
    Numeric(NumericType),
    Bool,
    Unit,
    Str,
    Reference(bool, TypeId),
    Tuple(Vec<TypeId>),
    Array(TypeId, u64),
    Slice(TypeId),
    Nominal(SymbolId, Vec<TypeId>),
    Parameter(TypeParameterId),
    Callable(SignatureId),
    Pool(TypeId),
    Allocation(TypeId),
    Vector(TypeId),
    HashMap(TypeId, TypeId),
    String,
    InlineString(u64),
    Handle(TypeId, bool),
}
#[derive(Clone)]
struct FunctionSource {
    unit: usize,
    node: ast::NodeId,
    scope: ScopeId,
    owner: Option<TypeId>,
    signature: SignatureId,
    parameters: Vec<(String, TypeId, bool)>,
    result: TypeId,
    body: Option<ast::NodeId>,
    captures: Option<CaptureRecordId>,
    infer_result: bool,
    annotations: Vec<ast::NodeId>,
    parameter_syntax: Vec<Option<ast::NodeId>>,
    result_syntax: Option<ast::NodeId>,
}
#[derive(Clone, Copy)]
enum BranchOperand {
    Syntax(ast::NodeId),
    Boolean(bool),
    Unit,
}
#[derive(Clone)]
struct Expr {
    value: ValueId,
}
#[derive(Clone)]
struct Context {
    unit: usize,
    body: BodyId,
    function: FunctionId,
    instance: FunctionInstanceId,
    substitutions: HashMap<TypeParameterId, TypeId>,
    return_type: Option<TypeId>,
    scope: ScopeId,
    branch: BranchId,
    timeline: TimelineId,
    domain: InstanceDomainId,
    guard: PredicateId,
    last: Option<ExecutionMomentId>,
    parent_anchor: Option<ExecutionMomentId>,
    instruction: ast::NodeId,
    bindings: HashMap<BindingId, ValueId>,
    returns: Vec<GuardedValue>,
    loops: Vec<LoopContext>,
    unchecked: Vec<ScopeId>,
}
#[derive(Clone)]
struct LoopContext {
    region: LoopRegionId,
    outer_scope: ScopeId,
    result_type: Option<TypeId>,
    results: Vec<GuardedValue>,
    breaks: Vec<LoopTransfer>,
    continues: Vec<LoopTransfer>,
}
#[derive(Clone)]
struct LoopTransfer {
    at: ExecutionMomentId,
    guard: PredicateId,
    bindings: HashMap<BindingId, ValueId>,
}

struct Resolver<'a> {
    current_unit: usize,
    units: Vec<&'a ast::ParsedUnit>,
    source_states: Vec<packages::SourceState>,
    prepared_package: bool,
    active_configuration: ConfigurationId,
    configured_constants: HashMap<(ConfigurationId, ConstantId), ConstantValue>,
    field_sources: HashMap<FieldId, (ast::NodeId, ScopeId)>,
    native_constructors: HashMap<SymbolId, native::NativeConstructor>,
    runtime_intrinsics: HashMap<SymbolId, RuntimeLaunchKind>,
    runtime_scope: ScopeId,
    runtime_error: TypeId,
    pool_error: TypeId,
    slice_error: TypeId,
    type_sources: HashMap<SymbolId, usize>,
    syntax: &'a ast::ParsedUnit,
    p: PostAst,
    warnings: Vec<Diagnostic>,
    names: Vec<HashMap<String, SymbolId>>,
    constant_sources: HashMap<ConstantId, (ast::NodeId, ScopeId, usize)>,
    constant_active: HashSet<(ConfigurationId, ConstantId)>,
    constant_done: HashSet<ConstantId>,
    lexical_scopes: HashMap<ast::NodeId, LexicalScopeId>,
    origins: HashMap<ast::NodeId, SourceOriginId>,
    lexical: HashMap<ast::NodeId, LexicalMomentId>,
    coverage: HashMap<ast::NodeId, Vec<SyntaxDisposition>>,
    type_ids: HashMap<TypeKey, TypeId>,
    type_nodes: HashMap<SymbolId, ast::NodeId>,
    owner_scopes: HashMap<TypeId, ScopeId>,
    nominal_parameters: HashMap<SymbolId, Vec<TypeParameterId>>,
    functions: Vec<FunctionSource>,
    function_symbols: HashMap<SymbolId, FunctionId>,
    instances: HashMap<(FunctionId, Vec<TypeId>, ConfigurationId), FunctionInstanceId>,
    binding_entities: HashMap<BindingId, EntityId>,
    value_entities: HashMap<ValueId, EntityId>,
    references: HashMap<ValueId, ReferenceId>,
    address_targets: HashMap<ValueId, Vec<PlaceId>>,
    components: HashMap<ValueId, Vec<ValueId>>,
    address_values: Vec<ValueId>,
    ctx: Option<Context>,
    next_operation: u32,
    transfers: Vec<TransferLink>,
    lifetime_uses: Vec<EntityUseMoment>,
    lifetime_requirements: Vec<LifetimeRequirement>,
    type_derivations: Vec<TypeDerivation>,
    unit: TypeId,
    never: TypeId,
    boolean: TypeId,
    integer: TypeId,
    zero: ValueId,
}

fn empty_post_ast(target: TargetDescription, source: String) -> PostAst {
    PostAst {
        specification: SpecificationIdentity {
            grammar_fingerprint: format!(
                "{:016x}",
                include_str!("../../../CORE_GRAMMAR.ebnf")
                    .bytes()
                    .fold(0xcbf29ce484222325u64, |h, b| (h ^ u64::from(b))
                        .wrapping_mul(0x100000001b3))
            ),
            rules_revision: "LANGUAGE_RULES.md:N1-N8; semantic population only".into(),
        },
        target,
        entry_point: None,
        origins: SourceOrigins {
            files: vec![SourceFile {
                id: SourceFileId(0),
                path: "<input>".into(),
                source,
            }],
            origins: vec![],
            lexical_scopes: vec![],
        },
        declarations: Declarations {
            defaults: vec![],
            native_bindings: vec![],
            native_namespaces: vec![],
            imports: vec![],
            packages: vec![],
            modules: vec![],
            functions: vec![],
            overloads: vec![],
            instances: vec![],
            structs: vec![],
            enums: vec![],
            constants: vec![],
            fields: vec![],
            variants: vec![],
            signatures: vec![],
            compile_time_selections: vec![],
        },
        symbols: Symbols {
            entries: vec![],
            aliases: vec![],
        },
        types: ResolvedTypes {
            entries: vec![],
            parameters: vec![],
        },
        scopes: Scopes {
            entries: vec![],
            bindings: vec![],
            exits: vec![],
            storage: vec![],
        },
        objects: Objects {
            value_entities: vec![],
            addresses: vec![],
            references: vec![],
            collections: vec![],
            ownership: vec![],
            dependencies: vec![],
            membership: vec![],
            places: vec![],
            evaluated_places: vec![],
        },
        storage_origins: vec![],
        cursor_expressions: vec![],
        cursor_snapshots: vec![],
        datastacks: vec![
            LogicalDataStack {
                id: DataStackId(0),
                kind: DataStackKind::FixedValues,
            },
            LogicalDataStack {
                id: DataStackId(1),
                kind: DataStackKind::GrowingRegions,
            },
        ],
        values: Values {
            entries: vec![],
            provenance: vec![],
            dependency_summaries: vec![],
            placement_summaries: vec![],
        },
        execution: ExecutionGraph {
            timelines: vec![],
            lexical_moments: vec![],
            execution_moments: vec![],
            branches: vec![],
            relationships: vec![],
            edges: vec![],
            predicates: vec![PathPredicate {
                id: PredicateId(0),
                kind: PredicateKind::Always,
            }],
            loops: vec![],
            suspensions: vec![],
            instance_domains: vec![],
            iteration_variables: vec![],
        },
        contracts: Contracts {
            symbolic_requirements: vec![],
            equality: vec![],
            memory_configuration: vec![],
            types: vec![],
            alternatives: vec![],
            matches: vec![],
            branches: vec![],
            completions: vec![],
            locks: vec![],
            threads: vec![],
            captures: vec![],
            destructors: vec![],
            configuration: vec![],
            type_effects: vec![],
            applications: vec![],
            lock_identities: vec![],
            environments: vec![ConfigurationEnvironment {
                id: ConfigurationId(0),
                parent: None,
                replacements: vec![],
            }],
        },
        bodies: vec![],
        effects: vec![],
        transfers: vec![],
        obligations: RuleObligations {
            execution_context: vec![],
            n1: vec![],
            n2: vec![],
            n3: vec![],
            n4: vec![],
            n5: vec![],
            n6: vec![],
            n7: vec![],
            n8: vec![],
        },
        runtime_checks: vec![],
        foreign_regions: vec![],
        match_coverage: vec![],
        async_frames: vec![],
        handle_protocols: vec![],
        well_known: WellKnownTypes {
            option: None,
            result: None,
        },
        unreachable_source: UnreachableSource {
            statements: vec![],
            bindings: vec![],
            names: vec![],
        },
    }
}
impl<'a> Resolver<'a> {
    fn kind(&self, n: ast::NodeId) -> &'a NodeKind {
        &self.syntax.ast.nodes[n.0].kind
    }
    fn text(&self, t: ast::TokenRef) -> &'a str {
        self.syntax.text(t)
    }
    fn fail(&self, n: ast::NodeId, kind: DiagnosticKind, message: impl Into<String>) -> Diagnostic {
        Diagnostic {
            file: SourceFileId(self.current_unit as u32),
            kind,
            span: self.syntax.ast.nodes[n.0].span,
            message: message.into(),
            related: vec![],
        }
    }

    fn ctx(&self) -> &Context {
        self.ctx.as_ref().expect("executable resolution context")
    }
    fn ctx_mut(&mut self) -> &mut Context {
        self.ctx.as_mut().expect("executable resolution context")
    }
    fn new(syntax: &'a ast::ParsedUnit, target: TargetDescription) -> Result<Self> {
        let mut r = Self {
            current_unit: 0,
            units: vec![syntax],
            source_states: vec![packages::SourceState::new(0, ModuleId(0))],
            prepared_package: false,
            active_configuration: ConfigurationId(0),
            configured_constants: HashMap::new(),
            field_sources: HashMap::new(),
            native_constructors: HashMap::new(),
            runtime_intrinsics: HashMap::new(),
            runtime_scope: ScopeId(0),
            runtime_error: TypeId(0),
            pool_error: TypeId(0),
            slice_error: TypeId(0),
            type_sources: HashMap::new(),
            syntax,
            p: empty_post_ast(target, syntax.source.clone()),
            warnings: vec![],
            names: vec![],
            constant_sources: HashMap::new(),
            constant_active: HashSet::new(),
            constant_done: HashSet::new(),
            lexical_scopes: HashMap::new(),
            origins: HashMap::new(),
            lexical: HashMap::new(),
            coverage: HashMap::new(),
            type_ids: HashMap::new(),
            type_nodes: HashMap::new(),
            owner_scopes: HashMap::new(),
            nominal_parameters: HashMap::new(),
            functions: vec![],
            function_symbols: HashMap::new(),
            instances: HashMap::new(),
            binding_entities: HashMap::new(),
            value_entities: HashMap::new(),
            references: HashMap::new(),
            address_targets: HashMap::new(),
            components: HashMap::new(),
            address_values: vec![],
            ctx: None,
            next_operation: 0,
            transfers: vec![],
            lifetime_uses: vec![],
            lifetime_requirements: vec![],
            type_derivations: vec![],
            unit: TypeId(0),
            never: TypeId(0),
            boolean: TypeId(0),
            integer: TypeId(0),
            zero: ValueId(0),
        };
        r.source_scopes(syntax.ast.root, None);
        let root_lex = r.lexical_moment(syntax.ast.root, LexicalContainer::Module(ModuleId(0)));
        r.p.scopes.entries.push(Scope {
            configuration: ConfigurationId(0),
            id: ScopeId(0),
            lexical_scope: r.lexical_scopes[&syntax.ast.root],
            lexical_parent: None,
            unchecked_boundary: None,
            children: vec![],
            context: ScopeContext::Module(ModuleId(0)),
            entry: ScopeEntry::DeclarationRoot { lexical: root_lex },
            exits: vec![],
            bindings: vec![],
            storage: ScopeStorageLink::DeclarationOnly,
        });
        r.names.push(HashMap::new());
        r.p.declarations.packages.push(PackageDefinition {
            name: "<input>".into(),
            id: PackageId(0),
            modules: vec![ModuleId(0)],
        });
        r.p.declarations.modules.push(ModuleDefinition {
            path: vec![],
            id: ModuleId(0),
            package: PackageId(0),
            scope: ScopeId(0),
        });
        r.never = r.intern(TypeKey::Never);
        r.unit = r.intern(TypeKey::Unit);
        r.boolean = r.intern(TypeKey::Bool);
        for (name, kind) in [
            ("i32", NumericType::I32),
            ("i64", NumericType::I64),
            ("u8", NumericType::U8),
            ("u16", NumericType::U16),
            ("u32", NumericType::U32),
            ("u64", NumericType::U64),
            ("usize", NumericType::Usize),
            ("f32", NumericType::F32),
            ("f64", NumericType::F64),
        ] {
            let ty = r.intern(TypeKey::Numeric(kind));
            if name == "i64" {
                r.integer = ty;
            }
            r.builtin_type(name, ty);
        }
        let numeric_error = r.intern(TypeKey::NumericConversionError);
        r.builtin_type("NumericConversionError", numeric_error);
        r.builtin_type("bool", r.boolean);
        r.builtin_type("Void", r.unit);
        let string = r.intern(TypeKey::Str);
        r.builtin_type("str", string);
        let usize_type = r.intern(TypeKey::Numeric(NumericType::Usize));
        r.zero = r.constant_value("<zero>", usize_type, ConstantValue::Unsigned(0));
        r.install_prelude();
        r.install_native_types();
        Ok(r)
    }
    fn source_scopes(&mut self, n: ast::NodeId, parent: Option<LexicalScopeId>) {
        let creates = matches!(
            self.kind(n),
            NodeKind::Module { .. }
                | NodeKind::Struct { .. }
                | NodeKind::Enum { .. }
                | NodeKind::Function { .. }
                | NodeKind::Block { .. }
        );
        let scope = if creates || parent.is_none() {
            let id = LexicalScopeId(self.p.origins.lexical_scopes.len() as u32);
            let span = self.syntax.ast.nodes[n.0].span;
            self.p.origins.lexical_scopes.push(LexicalScope {
                id,
                file: SourceFileId(self.current_unit as u32),
                parent,
                span: ByteSpan {
                    start: span.start as u32,
                    end: span.end as u32,
                },
            });
            id
        } else {
            parent.unwrap()
        };
        self.lexical_scopes.insert(n, scope);
        let children = self.kind(n).children();
        for child in children {
            self.source_scopes(child, Some(scope));
        }
    }
    fn lexical_moment(&mut self, n: ast::NodeId, container: LexicalContainer) -> LexicalMomentId {
        if let Some(id) = self.lexical.get(&n) {
            return *id;
        }
        let id = LexicalMomentId(self.p.execution.lexical_moments.len() as u32);
        let ordinal = self.syntax.ast.nodes[n.0].span.start as u32;
        self.p.execution.lexical_moments.push(LexicalMoment {
            id,
            container,
            scope: self.lexical_scopes[&n],
            ordinal_in_container: ordinal,
            origin: SourceOriginId(self.p.origins.origins.len() as u32),
        });
        let span = self.syntax.ast.nodes[n.0].span;
        let origin = SourceOriginId(self.p.origins.origins.len() as u32);
        self.p.origins.origins.push(SourceOrigin {
            id: origin,
            role: OriginRole::Written {
                file: SourceFileId(self.current_unit as u32),
                syntax: self.syntax_id(n),
                span: ByteSpan {
                    start: span.start as u32,
                    end: span.end as u32,
                },
                lexical: id,
            },
        });
        self.origins.insert(n, origin);
        self.lexical.insert(n, id);
        id
    }
    fn origin(&mut self, n: ast::NodeId) -> SourceOriginId {
        if let Some(id) = self.origins.get(&n) {
            return *id;
        }
        let (instruction, container) = self
            .ctx
            .as_ref()
            .filter(|c| c.unit == self.current_unit)
            .map(|c| {
                (
                    c.instruction,
                    LexicalContainer::FunctionDefinition(c.function),
                )
            })
            .unwrap_or((n, LexicalContainer::Module(ModuleId(0))));
        let lex = self.lexical_moment(instruction, container);
        if let Some(id) = self.origins.get(&n) {
            return *id;
        }
        let id = SourceOriginId(self.p.origins.origins.len() as u32);
        let span = self.syntax.ast.nodes[n.0].span;
        self.p.origins.origins.push(SourceOrigin {
            id,
            role: OriginRole::Written {
                file: SourceFileId(self.current_unit as u32),
                syntax: self.syntax_id(n),
                span: ByteSpan {
                    start: span.start as u32,
                    end: span.end as u32,
                },
                lexical: lex,
            },
        });
        self.origins.insert(n, id);
        id
    }
    fn cover(&mut self, n: ast::NodeId, role: SyntaxDisposition) {
        self.coverage.entry(n).or_default().push(role);
    }
    fn builtin_origin(&mut self, name: &str) -> SourceOriginId {
        let id = SourceOriginId(self.p.origins.origins.len() as u32);
        self.p.origins.origins.push(SourceOrigin {
            id,
            role: OriginRole::CompilerProvided {
                description: name.into(),
            },
        });
        id
    }
    fn builtin_type(&mut self, name: &str, ty: TypeId) {
        let origin = self.builtin_origin(name);
        let id = SymbolId(self.p.symbols.entries.len() as u32);
        self.p.symbols.entries.push(Symbol {
            id,
            spelling: name.into(),
            declaring_scope: ScopeId(0),
            origin,
            visibility: Visibility::Public,
            definition: SymbolDefinition::Type(ty),
        });
        self.names[0].insert(name.into(), id);
    }
    fn declare(
        &mut self,
        n: ast::NodeId,
        scope: ScopeId,
        name: &str,
        definition: SymbolDefinition,
    ) -> Result<SymbolId> {
        if let Some(previous) = self.names[scope.0 as usize].get(name) {
            let mut e = self.fail(
                n,
                DiagnosticKind::DuplicateDeclaration,
                format!("duplicate declaration '{name}'"),
            );
            if let OriginRole::Written { ref span, .. } = self.p.origins.origins
                [self.p.symbols.entries[previous.0 as usize].origin.0 as usize]
                .role
            {
                e.related.push(Span {
                    start: span.start as usize,
                    end: span.end as usize,
                });
            }
            return Err(e);
        }
        let origin = self.origin(n);
        let id = SymbolId(self.p.symbols.entries.len() as u32);
        self.p.symbols.entries.push(Symbol {
            id,
            spelling: name.into(),
            declaring_scope: scope,
            origin,
            visibility: Visibility::Private,
            definition,
        });
        self.names[scope.0 as usize].insert(name.into(), id);
        self.cover(n, SyntaxDisposition::Declaration(id));
        Ok(id)
    }
    fn lookup(&self, mut scope: ScopeId, name: &str) -> Option<SymbolId> {
        loop {
            if let Some(symbol) = self.file_import(scope, name) {
                return Some(symbol);
            }
            if let Some(id) = self.names[scope.0 as usize].get(name) {
                // Instance members require an explicit receiver. They do not
                // shadow file/module functions during bare lexical lookup.
                let instance_member = matches!(
                    self.p.scopes.entries[scope.0 as usize].context,
                    ScopeContext::Type(_)
                ) && match self.p.symbols.entries[id.0 as usize].definition {
                    SymbolDefinition::Field(_) => true,
                    SymbolDefinition::Function(function) => self
                        .functions
                        .get(function.0 as usize)
                        .is_some_and(|source| {
                            !matches!(
                                self.p.declarations.signatures[source.signature.0 as usize]
                                    .receiver,
                                ReceiverMode::None
                            )
                        }),
                    _ => false,
                };
                if !instance_member {
                    return Some(*id);
                }
            }
            scope = self.p.scopes.entries[scope.0 as usize].lexical_parent?;
        }
    }
    fn intern(&mut self, key: TypeKey) -> TypeId {
        if let Some(id) = self.type_ids.get(&key) {
            return *id;
        }
        let id = TypeId(self.p.types.entries.len() as u32);
        let kind = match &key {
            TypeKey::NumericConversionError => TypeDefinition::NumericConversionError,
            TypeKey::Never => TypeDefinition::Never,
            TypeKey::Numeric(n) => TypeDefinition::Numeric(*n),
            TypeKey::Bool => TypeDefinition::Boolean,
            TypeKey::Unit => TypeDefinition::Unit,
            TypeKey::Str => TypeDefinition::StrData,
            TypeKey::Reference(m, t) => TypeDefinition::Reference {
                permission: if *m {
                    ReferencePermission::Mutable
                } else {
                    ReferencePermission::Shared
                },
                target: *t,
            },
            TypeKey::Tuple(t) => TypeDefinition::Tuple(t.clone()),
            TypeKey::Array(t, n) => TypeDefinition::Array {
                element: *t,
                length: *n,
            },
            TypeKey::Slice(t) => TypeDefinition::Slice { element: *t },
            TypeKey::Nominal(s, args) => TypeDefinition::Nominal {
                configuration: ConfigurationId(0),
                definition: *s,
                arguments: args.iter().copied().map(TypeArgument::Type).collect(),
            },
            TypeKey::Parameter(p) => TypeDefinition::Parameter(*p),
            TypeKey::Callable(s) => TypeDefinition::Callable(*s),
            TypeKey::Pool(element) => TypeDefinition::Pool { element: *element },
            TypeKey::Allocation(content) => TypeDefinition::Allocation { content: *content },
            TypeKey::Vector(element) => TypeDefinition::GrowingSequence { element: *element },
            TypeKey::HashMap(key, value) => TypeDefinition::KeyedCollection {
                key: *key,
                value: *value,
            },
            TypeKey::String => TypeDefinition::GrowingString,
            TypeKey::InlineString(maximum_bytes) => TypeDefinition::InlineUtf8 {
                maximum_bytes: *maximum_bytes,
            },
            TypeKey::Handle(result, asynchronous) => TypeDefinition::ExecutionHandle {
                result: *result,
                asynchronous: *asynchronous,
            },
        };
        self.p.types.entries.push(ResolvedType { id, kind });
        self.type_ids.insert(key, id);
        id
    }
    fn type_name(&self, ty: TypeId) -> String {
        match &self.p.types.entries[ty.0 as usize].kind {
            TypeDefinition::Numeric(n) => format!("{n:?}").to_lowercase(),
            TypeDefinition::Boolean => "bool".into(),
            TypeDefinition::Unit => "()".into(),
            TypeDefinition::StrData => "str".into(),
            TypeDefinition::Reference { permission, target } => format!(
                "&{}{}",
                if matches!(permission, ReferencePermission::Mutable) {
                    "mut "
                } else {
                    ""
                },
                self.type_name(*target)
            ),
            TypeDefinition::Tuple(t) => format!(
                "({})",
                t.iter()
                    .map(|t| self.type_name(*t))
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
            TypeDefinition::Array { element, length } => {
                format!("[{}; {length}]", self.type_name(*element))
            }
            TypeDefinition::Slice { element } => format!("[{}]", self.type_name(*element)),
            TypeDefinition::Nominal {
                definition,
                arguments,
                ..
            } => {
                let name = &self.p.symbols.entries[definition.0 as usize].spelling;
                if arguments.is_empty() {
                    name.clone()
                } else {
                    format!(
                        "{}<{}>",
                        name,
                        arguments
                            .iter()
                            .map(|argument| match argument {
                                TypeArgument::Type(ty) => self.type_name(*ty),
                                TypeArgument::Integer(n) => n.to_string(),
                            })
                            .collect::<Vec<_>>()
                            .join(", ")
                    )
                }
            }
            TypeDefinition::Parameter(p) => self.p.symbols.entries
                [self.p.types.parameters[p.0 as usize].symbol.0 as usize]
                .spelling
                .clone(),
            _ => format!("type#{}", ty.0),
        }
    }
    fn require_type(&self, n: ast::NodeId, actual: TypeId, expected: TypeId) -> Result<()> {
        if actual == expected || actual == self.never {
            Ok(())
        } else {
            Err(self.fail(
                n,
                DiagnosticKind::TypeMismatch,
                format!(
                    "expected {}, found {}",
                    self.type_name(expected),
                    self.type_name(actual)
                ),
            ))
        }
    }
    fn declaration_scope(
        &mut self,
        n: ast::NodeId,
        parent: ScopeId,
        context: ScopeContext,
    ) -> ScopeId {
        let id = ScopeId(self.names.len() as u32);
        let lex = self.lexical_moment(n, LexicalContainer::Module(self.module_for_scope(parent)));
        self.p.scopes.entries.push(Scope {
            configuration: self.active_configuration,
            id,
            lexical_scope: self.lexical_scopes[&n],
            lexical_parent: Some(parent),
            unchecked_boundary: None,
            children: vec![],
            context,
            entry: ScopeEntry::DeclarationRoot { lexical: lex },
            exits: vec![],
            bindings: vec![],
            storage: ScopeStorageLink::DeclarationOnly,
        });
        self.p.scopes.entries[parent.0 as usize].children.push(id);
        self.names.push(HashMap::new());
        id
    }
    fn constant_value(&mut self, name: &str, ty: TypeId, value: ConstantValue) -> ValueId {
        let origin = self.builtin_origin(name);
        let symbol = SymbolId(self.p.symbols.entries.len() as u32);
        let constant = ConstantId(self.p.declarations.constants.len() as u32);
        self.p.symbols.entries.push(Symbol {
            id: symbol,
            spelling: name.into(),
            declaring_scope: ScopeId(0),
            origin,
            visibility: Visibility::Private,
            definition: SymbolDefinition::Constant(constant),
        });
        self.p.declarations.constants.push(ConstantDefinition {
            id: constant,
            symbol,
            ty,
            value,
            configurable: false,
        });
        self.value(
            ty,
            ValueDefinition::Constant(constant),
            ProvenanceKind::Constant(constant),
            vec![],
        )
    }
    fn value(
        &mut self,
        ty: TypeId,
        definition: ValueDefinition,
        provenance: ProvenanceKind,
        dependencies: Vec<DependencyRequirement>,
    ) -> ValueId {
        let id = ValueId(self.p.values.entries.len() as u32);
        let prov = ProvenanceId(self.p.values.provenance.len() as u32);
        let deps = DependencySummaryId(self.p.values.dependency_summaries.len() as u32);
        let placement = PlacementSummaryId(self.p.values.placement_summaries.len() as u32);
        self.p.values.provenance.push(Provenance {
            id: prov,
            kind: provenance,
        });
        self.p.values.dependency_summaries.push(DependencySummary {
            id: deps,
            dependencies,
            guarded: vec![],
            deferred_result: vec![],
        });
        self.p.values.placement_summaries.push(PlacementSummary {
            id: placement,
            origins: vec![],
            destinations: vec![],
        });
        let (origin, reason) = match &definition {
            ValueDefinition::Diverged { at } => {
                let moment = &self.p.execution.execution_moments[at.0 as usize];
                (
                    moment.lexical_origin(&self.p),
                    TypeDerivationReason::Operation(moment.operation),
                )
            }
            ValueDefinition::OperationResult {
                operation,
                produced_at,
            }
            | ValueDefinition::ConditionalResult {
                operation,
                produced_at,
                ..
            } => {
                let origin = self.p.execution.execution_moments[produced_at.0 as usize]
                    .lexical_origin(&self.p);
                (origin, TypeDerivationReason::Operation(*operation))
            }
            ValueDefinition::Parameter(binding) => {
                let symbol = self.p.scopes.bindings[binding.0 as usize].symbol;
                let function = self.ctx().function;
                (
                    self.p.symbols.entries[symbol.0 as usize].origin,
                    TypeDerivationReason::Parameter(self.functions[function.0 as usize].signature),
                )
            }
            ValueDefinition::CaptureField { record, field } => {
                let symbol = self.p.declarations.fields[field.0 as usize].symbol;
                (
                    self.p.symbols.entries[symbol.0 as usize].origin,
                    TypeDerivationReason::CaptureField {
                        record: *record,
                        field: *field,
                    },
                )
            }
            ValueDefinition::Constant(c)
            | ValueDefinition::ConfiguredConstant { constant: c, .. } => {
                let symbol = self.p.declarations.constants[c.0 as usize].symbol;
                let origin = self.p.symbols.entries[symbol.0 as usize].origin;
                (origin, TypeDerivationReason::ExplicitAnnotation(origin))
            }
        };
        self.p.values.entries.push(Value {
            id,
            ty,
            definition,
            provenance: prov,
            dependencies: deps,
            placement,
        });
        self.type_derivations.push(TypeDerivation {
            value: id,
            resolved: ty,
            origin,
            reason,
        });
        id
    }
    fn op_value(
        &mut self,
        site: &OperationSite,
        ty: TypeId,
        deps: Vec<DependencyRequirement>,
    ) -> ValueId {
        self.value(
            ty,
            ValueDefinition::OperationResult {
                operation: site.id,
                produced_at: site.execution_moments.first,
            },
            ProvenanceKind::Constructed(site.id),
            deps,
        )
    }
    fn vtype(&self, value: ValueId) -> TypeId {
        self.p.values.entries[value.0 as usize].ty
    }
    fn primitive_constraints(&self, value: ValueId) -> Vec<DependencyRequirement> {
        self.dependencies(value)
            .into_iter()
            .filter_map(Self::primitive_requirement)
            .collect()
    }
    fn primitive_requirement(requirement: DependencyRequirement) -> Option<DependencyRequirement> {
        match requirement {
            DependencyRequirement::When { guard, requirement } => {
                Self::primitive_requirement(*requirement).map(|requirement| {
                    DependencyRequirement::When {
                        guard,
                        requirement: Box::new(requirement),
                    }
                })
            }
            kept @ (DependencyRequirement::ConfinedToUncheckedScope(_)
            | DependencyRequirement::InstantiatedResult { .. }
            | DependencyRequirement::CarriedByProjection { .. }
            | DependencyRequirement::CapturedField { .. }
            | DependencyRequirement::CallableResult { .. }
            | DependencyRequirement::FutureResult { .. }
            | DependencyRequirement::NativeResult { .. }) => Some(kept),
            _ => None,
        }
    }
    fn dependencies(&self, value: ValueId) -> Vec<DependencyRequirement> {
        let summary = &self.p.values.dependency_summaries
            [self.p.values.entries[value.0 as usize].dependencies.0 as usize];
        let mut dependencies = summary.dependencies.clone();
        dependencies.extend(
            summary
                .guarded
                .iter()
                .map(|dependency| DependencyRequirement::When {
                    guard: dependency.guard,
                    requirement: Box::new(dependency.requirement.clone()),
                }),
        );
        dependencies
    }
    fn forward_summaries(&mut self, source: ValueId, result: ValueId) {
        let previous = self.p.values.entries[source.0 as usize].clone();
        self.p.values.entries[result.0 as usize].dependencies = previous.dependencies;
        self.p.values.entries[result.0 as usize].placement = previous.placement;
        if let Some(parts) = self.components.get(&source).cloned() {
            self.components.insert(result, parts);
        }
    }
    fn guarded_dependencies(&self, value: ValueId, guard: PredicateId) -> Vec<GuardedDependency> {
        let summary = &self.p.values.dependency_summaries
            [self.p.values.entries[value.0 as usize].dependencies.0 as usize];
        let mut result = summary
            .dependencies
            .iter()
            .cloned()
            .map(|requirement| GuardedDependency { guard, requirement })
            .collect::<Vec<_>>();
        result.extend(summary.guarded.iter().cloned());
        result
    }
    // A transfer is a semantic event, not a proof that its source was available.
    fn value_entities_at(
        &self,
        value: ValueId,
        guard: PredicateId,
    ) -> Vec<(PredicateId, EntityId)> {
        if let Some(entity) = self.value_entities.get(&value) {
            let guard = match self.p.values.entries[value.0 as usize].definition {
                ValueDefinition::ConditionalResult { guard, .. } => guard,
                _ => guard,
            };
            return vec![(guard, entity.clone())];
        }
        match &self.p.values.provenance
            [self.p.values.entries[value.0 as usize].provenance.0 as usize]
            .kind
        {
            ProvenanceKind::Merge(incoming) => std::iter::once(&incoming.first)
                .chain(&incoming.rest)
                .flat_map(|v| self.value_entities_at(v.value, v.guard))
                .collect(),
            ProvenanceKind::Move { source, .. } | ProvenanceKind::Forward { source, .. } => {
                self.value_entities_at(*source, guard)
            }
            _ => vec![],
        }
    }
    fn transfer(&mut self, value: ValueId, destination: Owner, site: &OperationSite) {
        let entities = self.value_entities_at(value, site.guard);
        if entities.is_empty() {
            self.transfers.push(TransferLink {
                source: value,
                result: value,
                entity: None,
                operation: site.id,
                at: site.execution_moments.first,
                guard: site.guard,
                receiver: destination,
            });
        } else {
            for (origin_guard, entity) in entities {
                let guard = if origin_guard == site.guard {
                    site.guard
                } else {
                    self.predicate(PredicateKind::All(vec![site.guard, origin_guard]))
                };
                self.p.objects.ownership.push(OwnershipLink {
                    entity: entity.clone(),
                    owner: destination.clone(),
                    scope: site.scope,
                    established: site.execution_moments.first,
                    guard,
                });
                self.transfers.push(TransferLink {
                    source: value,
                    result: value,
                    entity: Some(entity),
                    operation: site.id,
                    at: site.execution_moments.first,
                    guard,
                    receiver: destination.clone(),
                });
            }
        }
    }
    fn return_to_caller(
        &mut self,
        value: ValueId,
        function: FunctionInstanceId,
        site: &OperationSite,
    ) {
        self.transfer(
            value,
            Owner::FunctionResult {
                function,
                instance: self.ctx().domain,
            },
            site,
        );
    }
    fn site(&mut self, n: ast::NodeId, phase: ExecutionPhase) -> OperationSite {
        let origin = self.origin(n);
        let c = self.ctx().clone();
        let lexical = self.p.origins.origins[origin.0 as usize].role.clone();
        let lex = match lexical {
            OriginRole::Written { lexical, .. } | OriginRole::Synthesized { lexical, .. } => {
                lexical
            }
            _ => unreachable!(),
        };
        let op = OperationId(self.next_operation);
        self.next_operation += 1;
        let moment = ExecutionMomentId(self.p.execution.execution_moments.len() as u32);
        self.p.execution.execution_moments.push(ExecutionMoment {
            id: moment,
            instance: c.domain,
            body: c.body,
            timeline: c.timeline,
            branch: c.branch,
            lexical: lex,
            operation: op,
            phase,
            guard: c.guard,
        });
        self.p.execution.timelines[c.timeline.0 as usize]
            .execution_moments
            .push(moment);
        if !self.p.execution.timelines[c.timeline.0 as usize]
            .lexical_order
            .contains(&lex)
        {
            self.p.execution.timelines[c.timeline.0 as usize]
                .lexical_order
                .push(lex);
        }
        if let Some(last) = c.last {
            self.p
                .execution
                .edges
                .push(ExecutionEdge::Sequence(SequenceEdge {
                    before: last,
                    after: moment,
                }));
        }
        self.ctx_mut().last = Some(moment);
        self.cover(
            n,
            SyntaxDisposition::Operations(NonEmpty {
                first: op,
                rest: vec![],
            }),
        );
        OperationSite {
            id: op,
            body: c.body,
            scope: c.scope,
            branch: c.branch,
            timeline: c.timeline,
            lexical_moment: lex,
            execution_moments: NonEmpty {
                first: moment,
                rest: vec![],
            },
            origin,
            guard: c.guard,
        }
    }
    fn emit(&mut self, operation: Operation) {
        let body = operation.site().body;
        self.p.bodies[body.0 as usize].operations.push(operation);
    }
    fn effects(&mut self, site: &OperationSite, effects: Vec<Effect>) -> EffectSummaryId {
        let facts = effects
            .into_iter()
            .map(|effect| GuardedEffect {
                guard: site.guard,
                effect,
                timing: EffectTiming::At(site.execution_moments.first),
            })
            .collect::<Vec<_>>();
        let id = EffectSummaryId(self.p.effects.len() as u32);
        self.p.effects.push(EffectSummary {
            id,
            effects: facts.clone(),
        });
        if let Some(context) = &self.ctx {
            let summary = self.p.declarations.instances[context.instance.0 as usize].effects;
            self.p.effects[summary.0 as usize].effects.extend(facts);
        }
        id
    }
    fn type_syntax(&mut self, n: ast::NodeId, scope: ScopeId) -> Result<TypeId> {
        let ty = match self.kind(n) {
            NodeKind::Type(TypeSyntax::Path {
                segments,
                arguments,
            }) => {
                let name = self.text(segments[0]);
                let symbol = self.scoped_path(n, scope, segments)?;
                if let Some(constructor) = self.native_constructors.get(&symbol).copied() {
                    let ty = self.native_type(n, constructor, arguments, scope, None)?;
                    self.cover(n, SyntaxDisposition::ResolvedType(ty));
                    return Ok(ty);
                }
                if let SymbolDefinition::Function(function) =
                    self.p.symbols.entries[symbol.0 as usize].definition
                {
                    let source = self.functions[function.0 as usize].clone();
                    if !matches!(
                        self.p.declarations.signatures[source.signature.0 as usize].execution,
                        FunctionExecution::Asynchronous
                    ) {
                        return Err(self.fail(
                            n,
                            DiagnosticKind::InvalidType,
                            "only an async function name denotes a task type",
                        ));
                    }
                    let mut actual = vec![];
                    for argument in arguments {
                        actual.push(self.type_syntax(*argument, scope)?);
                    }
                    let instance = self.specialized_instance(function, actual)?;
                    let ty = self.future_type(instance)?;
                    self.cover(n, SyntaxDisposition::ResolvedType(ty));
                    return Ok(ty);
                }
                let ty = match self.p.symbols.entries[symbol.0 as usize].definition {
                    SymbolDefinition::Type(t) => t,
                    SymbolDefinition::TypeParameter(p) => self.intern(TypeKey::Parameter(p)),
                    _ => {
                        return Err(self.fail(
                            n,
                            DiagnosticKind::InvalidType,
                            format!("'{name}' does not name a type"),
                        ));
                    }
                };
                if arguments.is_empty() {
                    ty
                } else {
                    let mut args = vec![];
                    for arg in arguments {
                        args.push(self.type_syntax(*arg, scope)?);
                    }
                    match self.p.types.entries[ty.0 as usize].kind {
                        TypeDefinition::Nominal { definition, .. } => {
                            self.intern(TypeKey::Nominal(definition, args))
                        }
                        _ => {
                            return Err(self.fail(
                                n,
                                DiagnosticKind::InvalidType,
                                "type does not take generic arguments",
                            ));
                        }
                    }
                }
            }
            NodeKind::Type(TypeSyntax::Reference {
                mutable, target, ..
            }) => {
                let target = self.type_syntax(*target, scope)?;
                self.intern(TypeKey::Reference(mutable.is_some(), target))
            }
            NodeKind::Type(TypeSyntax::Tuple { elements }) => {
                let mut types = vec![];
                for e in elements {
                    types.push(self.type_syntax(*e, scope)?);
                }
                if types.is_empty() {
                    self.unit
                } else {
                    self.intern(TypeKey::Tuple(types))
                }
            }
            NodeKind::Type(TypeSyntax::Array { element, length }) => {
                let element = self.type_syntax(*element, scope)?;
                let length = self.integer_constant(*length, scope)?;
                self.intern(TypeKey::Array(element, length))
            }
            NodeKind::Type(TypeSyntax::Slice { element }) => {
                let element = self.type_syntax(*element, scope)?;
                self.intern(TypeKey::Slice(element))
            }
            NodeKind::Type(TypeSyntax::Callable { parameters, result }) => {
                let mut types = vec![];
                for p in parameters {
                    types.push(self.type_syntax(*p, scope)?);
                }
                let result = self.type_syntax(*result, scope)?;
                self.callable_type(types, result)
            }
            _ => {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    "expected written type syntax",
                ));
            }
        };
        let substitutions = self
            .ctx
            .as_ref()
            .map(|c| c.substitutions.clone())
            .unwrap_or_default();
        let ty = self.substitute_type(ty, &substitutions);
        let ty = self.configured_type(ty, self.active_configuration);
        self.cover(n, SyntaxDisposition::ResolvedType(ty));
        Ok(ty)
    }
    fn signature(
        &mut self,
        types: Vec<TypeId>,
        result: TypeId,
        receiver: ReceiverMode,
        execution: FunctionExecution,
    ) -> SignatureId {
        let id = SignatureId(self.p.declarations.signatures.len() as u32);
        self.p.declarations.signatures.push(Signature {
            id,
            receiver,
            parameters: types
                .into_iter()
                .map(|ty| ParameterDefinition {
                    identity: ParameterIdentity::Anonymous,
                    ty,
                })
                .collect(),
            result,
            execution,
        });
        id
    }
    fn declare_types(&mut self, items: &[ast::NodeId], scope: ScopeId) -> Result<()> {
        // Reserve constant symbols before fields or values inspect their dependencies.
        for n in items {
            if let NodeKind::Constant {
                name,
                ty,
                attributes,
                ..
            } = self.kind(*n)
            {
                let ty = self.type_syntax(*ty, scope)?;
                let id = ConstantId(self.p.declarations.constants.len() as u32);
                let symbol =
                    self.declare(*n, scope, self.text(*name), SymbolDefinition::Constant(id))?;
                self.p.symbols.entries[symbol.0 as usize].visibility =
                    if attributes.public.is_some() {
                        Visibility::Public
                    } else {
                        Visibility::Private
                    };
                self.p.declarations.constants.push(ConstantDefinition { id, symbol, ty, value: ConstantValue::Unit,
                    configurable: attributes.annotations.iter().any(|a| matches!(self.kind(*a), NodeKind::Annotation { name, .. } if self.text(*name) == "configurable")) });
                self.constant_sources
                    .insert(id, (*n, scope, self.current_unit));
            }
        }
        for n in items {
            match self.kind(*n) {
                NodeKind::Struct { name, .. } | NodeKind::Enum { name, .. } => {
                    let symbol = self.declare(
                        *n,
                        scope,
                        self.text(*name),
                        SymbolDefinition::Type(self.unit),
                    )?;
                    let public = match self.kind(*n) {
                        NodeKind::Struct { attributes, .. } | NodeKind::Enum { attributes, .. } => {
                            attributes.public.is_some()
                        }
                        _ => false,
                    };
                    self.p.symbols.entries[symbol.0 as usize].visibility = if public {
                        Visibility::Public
                    } else {
                        Visibility::Private
                    };
                    let ty = self.intern(TypeKey::Nominal(symbol, vec![]));
                    self.p.symbols.entries[symbol.0 as usize].definition =
                        SymbolDefinition::Type(ty);
                    self.type_nodes.insert(symbol, *n);
                    self.type_sources.insert(symbol, self.current_unit);
                    let inner = self.declaration_scope(*n, scope, ScopeContext::Type(ty));
                    self.names[inner.0 as usize].insert("Self".into(), symbol);
                    self.owner_scopes.insert(ty, inner);
                    let (generics, members) = match self.kind(*n) {
                        NodeKind::Struct {
                            generics, members, ..
                        }
                        | NodeKind::Enum {
                            generics, members, ..
                        } => (generics, members),
                        _ => unreachable!(),
                    };
                    let mut owner_parameters = vec![];
                    for generic in generics {
                        let parameter = TypeParameterId(self.p.types.parameters.len() as u32);
                        let symbol = self.declare(
                            *n,
                            inner,
                            self.text(*generic),
                            SymbolDefinition::TypeParameter(parameter),
                        )?;
                        self.p.types.parameters.push(TypeParameter {
                            id: parameter,
                            symbol,
                            constraints: vec![],
                        });
                        self.intern(TypeKey::Parameter(parameter));
                        owner_parameters.push(parameter);
                    }
                    let annotations = match self.kind(*n) {
                        NodeKind::Struct { attributes, .. } | NodeKind::Enum { attributes, .. } => {
                            attributes.annotations.clone()
                        }
                        _ => unreachable!(),
                    };
                    self.type_annotations(&annotations, inner, &mut owner_parameters)?;
                    self.nominal_parameters
                        .insert(symbol, owner_parameters.clone());
                    if !owner_parameters.is_empty() {
                        let arguments = owner_parameters
                            .iter()
                            .map(|p| self.intern(TypeKey::Parameter(*p)))
                            .collect();
                        let inherited = self.intern(TypeKey::Nominal(symbol, arguments));
                        self.owner_scopes.insert(inherited, inner);
                        let alias = self.anonymous_symbol(
                            "Self",
                            inner,
                            SymbolDefinition::Type(inherited),
                            *n,
                        );
                        self.names[inner.0 as usize].insert("Self".into(), alias);
                    }
                    self.declare_types(members, inner)?;
                }
                NodeKind::Conditional {
                    condition, items, ..
                } => {
                    if self.target_condition(*condition)? {
                        self.declare_types(items, scope)?;
                    }
                }
                _ => {}
            }
        }
        Ok(())
    }
    fn target_condition(&self, n: ast::NodeId) -> Result<bool> {
        match self.kind(n) {
            NodeKind::Binary {
                operator,
                left,
                right,
            } => {
                let op = self.text(*operator);
                if op == "&&" {
                    return Ok(self.target_condition(*left)? && self.target_condition(*right)?);
                }
                if op == "||" {
                    return Ok(self.target_condition(*left)? || self.target_condition(*right)?);
                }
                if op != "==" {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "target conditions require ==, && or ||",
                    ));
                }
                let NodeKind::Projection { base, member } = self.kind(*left) else {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "expected a target property",
                    ));
                };
                let NodeKind::Path { segments, .. } = self.kind(*base) else {
                    return Err(self.fail(n, DiagnosticKind::InvalidType, "expected target"));
                };
                if segments.len() != 1 || self.text(segments[0]) != "target" {
                    return Err(self.fail(n, DiagnosticKind::InvalidType, "expected target"));
                }
                let expected = match self.kind(*right) {
                    NodeKind::Literal { token } => match &self.syntax.tokens[token.index].payload {
                        crate::lexer::Payload::Text(bytes) => bytes.as_slice(),
                        _ => {
                            return Err(self.fail(
                                *right,
                                DiagnosticKind::InvalidType,
                                "target value must be text",
                            ));
                        }
                    },
                    _ => {
                        return Err(self.fail(
                            *right,
                            DiagnosticKind::InvalidType,
                            "target value must be text",
                        ));
                    }
                };
                let target = &self.p.target;
                let actual = match self.text(*member) {
                    "os" => target.os.clone(),
                    "family" => target.family.clone(),
                    "arch" => target.architecture.clone(),
                    "endian" => {
                        if matches!(target.endian, Endian::Little) {
                            "little".into()
                        } else {
                            "big".into()
                        }
                    }
                    "pointer_width" => target.pointer_bits.to_string(),
                    _ => {
                        return Err(self.fail(
                            n,
                            DiagnosticKind::InvalidType,
                            "unknown target property",
                        ));
                    }
                };
                Ok(actual.as_bytes() == expected)
            }
            _ => Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                "invalid target selection condition",
            )),
        }
    }
    fn collect(
        &mut self,
        items: &[ast::NodeId],
        scope: ScopeId,
        owner: Option<TypeId>,
    ) -> Result<()> {
        for n in items {
            if let NodeKind::Struct { name, .. } | NodeKind::Enum { name, .. } = self.kind(*n) {
                if let Some(symbol) = self.names[scope.0 as usize].get(self.text(*name)).copied() {
                    if self
                        .p
                        .declarations
                        .native_bindings
                        .iter()
                        .any(|b| b.symbol == symbol)
                    {
                        self.cover(*n, SyntaxDisposition::Declaration(symbol));
                        continue;
                    }
                }
            }
            match self.kind(*n) {
                NodeKind::Struct { name, members, .. } => {
                    let symbol = self.lookup(scope, self.text(*name)).unwrap();
                    let SymbolDefinition::Type(ty) =
                        self.p.symbols.entries[symbol.0 as usize].definition
                    else {
                        unreachable!()
                    };
                    let inner = self.owner_scopes[&ty];
                    let mut fields = vec![];
                    for child in members {
                        if let NodeKind::Field {
                            name,
                            ty: written,
                            attributes,
                        } = self.kind(*child)
                        {
                            let field_ty = self.type_syntax(*written, inner)?;
                            let id = FieldId(self.p.declarations.fields.len() as u32);
                            let sym = self.declare(
                                *child,
                                inner,
                                self.text(*name),
                                SymbolDefinition::Field(id),
                            )?;
                            self.p.symbols.entries[sym.0 as usize].visibility =
                                if attributes.public.is_some() {
                                    Visibility::Public
                                } else {
                                    Visibility::Private
                                };
                            self.p.declarations.fields.push(FieldDefinition {
                                id,
                                symbol: sym,
                                ty: field_ty,
                                default: FieldDefault::Unavailable,
                            });
                            self.field_sources.insert(id, (*written, inner));
                            fields.push(id);
                        }
                    }
                    self.p.declarations.structs.push(StructDefinition {
                        symbol,
                        parameters: self
                            .nominal_parameters
                            .get(&symbol)
                            .cloned()
                            .unwrap_or_default(),
                        ty,
                        fields,
                        methods: vec![],
                    });
                    let self_symbol = self.names[inner.0 as usize]["Self"];
                    let SymbolDefinition::Type(self_type) =
                        self.p.symbols.entries[self_symbol.0 as usize].definition
                    else {
                        unreachable!()
                    };
                    self.collect(members, inner, Some(self_type))?;
                    self.type_effect_annotations(*n, ty)?;
                }
                NodeKind::Enum { name, members, .. } => {
                    let symbol = self.lookup(scope, self.text(*name)).unwrap();
                    let SymbolDefinition::Type(ty) =
                        self.p.symbols.entries[symbol.0 as usize].definition
                    else {
                        unreachable!()
                    };
                    let inner = self.owner_scopes[&ty];
                    let mut variants = vec![];
                    for child in members {
                        if let NodeKind::Variant {
                            name,
                            positional,
                            fields,
                        } = self.kind(*child)
                        {
                            let id = VariantId(self.p.declarations.variants.len() as u32);
                            let sym = self.declare(
                                *child,
                                inner,
                                self.text(*name),
                                SymbolDefinition::Variant(id),
                            )?;
                            let mut payload = vec![];
                            if let Some(types) = positional {
                                for (index, written) in types.iter().enumerate() {
                                    let field_ty = self.type_syntax(*written, inner)?;
                                    let field = FieldId(self.p.declarations.fields.len() as u32);
                                    let fsym = self.anonymous_symbol(
                                        &format!("{}.{index}", self.text(*name)),
                                        inner,
                                        SymbolDefinition::Field(field),
                                        *child,
                                    );
                                    self.p.declarations.fields.push(FieldDefinition {
                                        id: field,
                                        symbol: fsym,
                                        ty: field_ty,
                                        default: FieldDefault::Unavailable,
                                    });
                                    self.field_sources.insert(field, (*written, inner));
                                    payload.push(field);
                                }
                            }
                            if let Some(fields) = fields {
                                for field in fields {
                                    let NodeKind::Field {
                                        name, ty: written, ..
                                    } = self.kind(*field)
                                    else {
                                        return Err(self.fail(
                                            *field,
                                            DiagnosticKind::InvalidType,
                                            "variant payload must be a field",
                                        ));
                                    };
                                    let ty = self.type_syntax(*written, inner)?;
                                    let id = FieldId(self.p.declarations.fields.len() as u32);
                                    let sym = self.anonymous_symbol(
                                        self.text(*name),
                                        inner,
                                        SymbolDefinition::Field(id),
                                        *field,
                                    );
                                    self.p.declarations.fields.push(FieldDefinition {
                                        id,
                                        symbol: sym,
                                        ty,
                                        default: FieldDefault::Unavailable,
                                    });
                                    self.field_sources.insert(id, (*written, inner));
                                    payload.push(id);
                                }
                            }
                            self.p.symbols.entries[sym.0 as usize].visibility =
                                self.p.symbols.entries[symbol.0 as usize].visibility.clone();
                            // Variant payloads are part of the variant's public
                            // constructor/pattern contract, not private struct fields.
                            for field in &payload {
                                let field_symbol =
                                    self.p.declarations.fields[field.0 as usize].symbol;
                                self.p.symbols.entries[field_symbol.0 as usize].visibility =
                                    self.p.symbols.entries[sym.0 as usize].visibility.clone();
                            }
                            self.p.declarations.variants.push(VariantDefinition {
                                id,
                                template: None,
                                symbol: sym,
                                owner: ty,
                                fields: payload,
                            });
                            variants.push(id);
                        }
                    }
                    let mut variants = variants.into_iter();
                    let first = variants.next().ok_or_else(|| {
                        self.fail(
                            *n,
                            DiagnosticKind::InvalidType,
                            "enum requires at least one variant",
                        )
                    })?;
                    self.p.declarations.enums.push(EnumDefinition {
                        symbol,
                        parameters: self
                            .nominal_parameters
                            .get(&symbol)
                            .cloned()
                            .unwrap_or_default(),
                        ty,
                        variants: NonEmpty {
                            first,
                            rest: variants.collect(),
                        },
                        methods: vec![],
                    });
                    let self_symbol = self.names[inner.0 as usize]["Self"];
                    let SymbolDefinition::Type(self_type) =
                        self.p.symbols.entries[self_symbol.0 as usize].definition
                    else {
                        unreachable!()
                    };
                    self.collect(members, inner, Some(self_type))?;
                    self.type_effect_annotations(*n, ty)?;
                }
                NodeKind::Function {
                    name,
                    parameters,
                    result,
                    body,
                    asynchronous,
                    abi,
                    attributes,
                } => {
                    let id = FunctionId(self.functions.len() as u32);
                    let previous = self.names[scope.0 as usize].get(self.text(*name)).copied();
                    let sym = if previous.is_some() && owner.is_some() && self.text(*name) == "from"
                    {
                        self.anonymous_symbol("from", scope, SymbolDefinition::Function(id), *n)
                    } else {
                        self.declare(*n, scope, self.text(*name), SymbolDefinition::Function(id))?
                    };
                    self.p.symbols.entries[sym.0 as usize].visibility =
                        if attributes.public.is_some() {
                            Visibility::Public
                        } else {
                            Visibility::Private
                        };
                    let inner = self.declaration_scope(
                        *n,
                        scope,
                        ScopeContext::Module(self.module_for_scope(scope)),
                    );
                    let mut type_parameters = owner
                        .and_then(|ty| match self.p.types.entries[ty.0 as usize].kind {
                            TypeDefinition::Nominal { definition, .. } => {
                                self.nominal_parameters.get(&definition).cloned()
                            }
                            _ => None,
                        })
                        .unwrap_or_default();
                    let type_contracts = self.type_annotations(
                        &attributes.annotations,
                        inner,
                        &mut type_parameters,
                    )?;
                    let mut params = vec![];
                    let mut parameter_defs = vec![];
                    let mut receiver = ReceiverMode::None;
                    for (position, param) in parameters.iter().enumerate() {
                        let NodeKind::Parameter {
                            name,
                            ty,
                            reference,
                            mutable,
                        } = self.kind(*param)
                        else {
                            unreachable!()
                        };
                        let name = self.text(*name).to_owned();
                        let pty = if let Some(written) = ty {
                            self.type_syntax(*written, inner)?
                        } else {
                            let own = owner.ok_or_else(|| {
                                self.fail(
                                    *param,
                                    DiagnosticKind::InvalidType,
                                    "self requires an enclosing type",
                                )
                            })?;
                            if reference.is_some() {
                                self.intern(TypeKey::Reference(mutable.is_some(), own))
                            } else {
                                own
                            }
                        };
                        if name == "self" {
                            receiver = match &self.p.types.entries[pty.0 as usize].kind {
                                TypeDefinition::Reference { permission, target } => {
                                    if matches!(permission, ReferencePermission::Mutable) {
                                        ReceiverMode::Mutable(*target)
                                    } else {
                                        ReceiverMode::Shared(*target)
                                    }
                                }
                                _ => ReceiverMode::ByValue(pty),
                            };
                        }
                        let binding = BindingId(self.p.scopes.bindings.len() as u32);
                        let symbol =
                            self.declare(*param, inner, &name, SymbolDefinition::Binding(binding))?;
                        self.p.scopes.bindings.push(Binding {
                            id: binding,
                            symbol,
                            ty: pty,
                            scope: inner,
                            mutable: mutable.is_some(),
                            introduced: BindingIntroduction::Parameter {
                                function: id,
                                position: position as u32,
                            },
                        });
                        self.p.scopes.entries[inner.0 as usize]
                            .bindings
                            .push(binding);
                        params.push((name, pty, mutable.is_some()));
                        parameter_defs.push(ParameterDefinition {
                            identity: ParameterIdentity::Named { symbol, binding },
                            ty: pty,
                        });
                    }
                    let result_ty = if let Some(ty) = result {
                        self.type_syntax(*ty, inner)?
                    } else {
                        self.unit
                    };
                    let sig = SignatureId(self.p.declarations.signatures.len() as u32);
                    self.p.declarations.signatures.push(Signature {
                        id: sig,
                        receiver,
                        parameters: parameter_defs,
                        result: result_ty,
                        execution: if asynchronous.is_some() {
                            FunctionExecution::Asynchronous
                        } else {
                            FunctionExecution::Synchronous
                        },
                    });
                    self.functions.push(FunctionSource {
                        unit: self.current_unit,
                        node: *n,
                        scope: inner,
                        owner,
                        signature: sig,
                        parameters: params,
                        result: result_ty,
                        body: *body,
                        captures: None,
                        infer_result: false,
                        annotations: attributes.annotations.clone(),
                        parameter_syntax: parameters
                            .iter()
                            .map(|p| match self.kind(*p) {
                                NodeKind::Parameter { ty, .. } => *ty,
                                _ => None,
                            })
                            .collect(),
                        result_syntax: *result,
                    });
                    self.function_symbols.insert(sym, id);
                    let implementation = if abi.is_some() {
                        FunctionImplementation::External { abi: AbiId(0) }
                    } else {
                        FunctionImplementation::Template {
                            origin: self.origin(*n),
                            syntax: self.syntax_id(*n),
                        }
                    };
                    self.p.declarations.functions.push(FunctionDefinition {
                        parametric_body: None,
                        id,
                        symbol: sym,
                        signature: sig,
                        type_parameters,
                        body: implementation,
                        contracts: type_contracts
                            .into_iter()
                            .map(ResolvedContract::Type)
                            .collect(),
                    });
                    if self.text(*name) == "from" && owner.is_some() {
                        self.register_from_overload(*n, scope, sym, id, owner.unwrap(), previous)?;
                    }
                    if let Some(owner) = owner {
                        if let Some(definition) =
                            self.p.declarations.structs.iter_mut().find(|s| {
                                self.owner_scopes.get(&s.ty) == self.owner_scopes.get(&owner)
                            })
                        {
                            definition.methods.push(id);
                        }
                        if let Some(definition) =
                            self.p.declarations.enums.iter_mut().find(|s| {
                                self.owner_scopes.get(&s.ty) == self.owner_scopes.get(&owner)
                            })
                        {
                            definition.methods.push(id);
                        }
                    }
                }
                NodeKind::Conditional {
                    condition, items, ..
                } => {
                    let selected = self.target_condition(*condition)?;
                    let origin = self.origin(*n);
                    let mut selected_origins = vec![];
                    let mut excluded = vec![];
                    for child in items {
                        let o = self.origin(*child);
                        if selected {
                            selected_origins.push(o);
                        } else {
                            excluded.push(o);
                            self.cover(
                                *child,
                                SyntaxDisposition::ExcludedByTarget { selection: origin },
                            );
                        }
                    }
                    self.p
                        .declarations
                        .compile_time_selections
                        .push(TargetSelection {
                            origin,
                            selected: selected_origins,
                            excluded,
                        });
                    if selected {
                        self.collect(items, scope, owner)?;
                    }
                }
                NodeKind::Field { .. } | NodeKind::Variant { .. } => {}
                NodeKind::Constant { name, .. } => {
                    let symbol = self.lookup(scope, self.text(*name)).unwrap();
                    let SymbolDefinition::Constant(id) =
                        self.p.symbols.entries[symbol.0 as usize].definition
                    else {
                        unreachable!()
                    };
                    self.resolve_constant(id)?;
                    self.cover(*n, SyntaxDisposition::Declaration(symbol));
                }
                NodeKind::Import { .. } => {
                    if !self.prepared_package {
                        return Err(self.fail(
                            *n,
                            DiagnosticKind::UnresolvedName,
                            "import requires parsed package/module inputs",
                        ));
                    }
                }
                NodeKind::Annotation { .. } => self.memory_annotation(*n, scope)?,
                _ => {
                    return Err(self.fail(
                        *n,
                        DiagnosticKind::InvalidType,
                        format!(
                            "{} is not a declaration",
                            super::grammar::construct_name(self.kind(*n))
                        ),
                    ));
                }
            }
        }
        Ok(())
    }
    fn anonymous_symbol(
        &mut self,
        name: &str,
        scope: ScopeId,
        definition: SymbolDefinition,
        n: ast::NodeId,
    ) -> SymbolId {
        let origin = self.origin(n);
        let id = SymbolId(self.p.symbols.entries.len() as u32);
        self.p.symbols.entries.push(Symbol {
            id,
            spelling: name.into(),
            declaring_scope: scope,
            origin,
            visibility: Visibility::Private,
            definition,
        });
        id
    }
    fn substitute_type(
        &mut self,
        ty: TypeId,
        substitutions: &HashMap<TypeParameterId, TypeId>,
    ) -> TypeId {
        match self.p.types.entries[ty.0 as usize].kind.clone() {
            TypeDefinition::Parameter(p) => substitutions.get(&p).copied().unwrap_or(ty),
            TypeDefinition::Reference { permission, target } => {
                let target = self.substitute_type(target, substitutions);
                self.intern(TypeKey::Reference(
                    matches!(permission, ReferencePermission::Mutable),
                    target,
                ))
            }
            TypeDefinition::Callable(signature) => {
                let shape = self.p.declarations.signatures[signature.0 as usize].clone();
                let parameters = shape
                    .parameters
                    .iter()
                    .map(|p| self.substitute_type(p.ty, substitutions))
                    .collect();
                let result = self.substitute_type(shape.result, substitutions);
                self.callable_type(parameters, result)
            }
            TypeDefinition::Pool { element } => {
                let element = self.substitute_type(element, substitutions);
                self.intern(TypeKey::Pool(element))
            }
            TypeDefinition::Allocation { content } => {
                let content = self.substitute_type(content, substitutions);
                self.intern(TypeKey::Allocation(content))
            }
            TypeDefinition::GrowingSequence { element } => {
                let element = self.substitute_type(element, substitutions);
                self.intern(TypeKey::Vector(element))
            }
            TypeDefinition::KeyedCollection { key, value } => {
                let key = self.substitute_type(key, substitutions);
                let value = self.substitute_type(value, substitutions);
                self.intern(TypeKey::HashMap(key, value))
            }
            TypeDefinition::ExecutionHandle {
                result,
                asynchronous,
            } => {
                let result = self.substitute_type(result, substitutions);
                self.intern(TypeKey::Handle(result, asynchronous))
            }
            TypeDefinition::Tuple(parts) => {
                let parts = parts
                    .into_iter()
                    .map(|p| self.substitute_type(p, substitutions))
                    .collect();
                self.intern(TypeKey::Tuple(parts))
            }
            TypeDefinition::Array { element, length } => {
                let element = self.substitute_type(element, substitutions);
                self.intern(TypeKey::Array(element, length))
            }
            TypeDefinition::Slice { element } => {
                let element = self.substitute_type(element, substitutions);
                self.intern(TypeKey::Slice(element))
            }
            TypeDefinition::Nominal {
                definition,
                arguments,
                configuration,
            } => {
                let arguments = arguments
                    .into_iter()
                    .map(|arg| match arg {
                        TypeArgument::Type(ty) => self.substitute_type(ty, substitutions),
                        _ => unreachable!(),
                    })
                    .collect();
                let template = self.intern(TypeKey::Nominal(definition, arguments));
                self.configured_type(template, configuration)
            }
            _ => ty,
        }
    }
    fn has_parameters(&self, ty: TypeId) -> bool {
        match &self.p.types.entries[ty.0 as usize].kind {
            TypeDefinition::Parameter(_) => true,
            TypeDefinition::Reference { target, .. } => self.has_parameters(*target),
            TypeDefinition::Array { element, .. } | TypeDefinition::Slice { element } => {
                self.has_parameters(*element)
            }
            TypeDefinition::Tuple(parts) => parts.iter().any(|p| self.has_parameters(*p)),
            TypeDefinition::Pool { element } | TypeDefinition::GrowingSequence { element } => {
                self.has_parameters(*element)
            }
            TypeDefinition::Allocation { content } => self.has_parameters(*content),
            TypeDefinition::ExecutionHandle { result, .. } => self.has_parameters(*result),
            TypeDefinition::KeyedCollection { key, value } => {
                self.has_parameters(*key) || self.has_parameters(*value)
            }
            TypeDefinition::Callable(signature) => {
                let signature = &self.p.declarations.signatures[signature.0 as usize];
                self.has_parameters(signature.result)
                    || signature
                        .parameters
                        .iter()
                        .any(|p| self.has_parameters(p.ty))
            }
            TypeDefinition::Nominal { arguments, .. } => arguments
                .iter()
                .any(|arg| matches!(arg,TypeArgument::Type(ty)if self.has_parameters(*ty))),
            _ => false,
        }
    }
    fn infer_substitutions(
        &self,
        node: ast::NodeId,
        formal: TypeId,
        actual: TypeId,
        substitutions: &mut HashMap<TypeParameterId, TypeId>,
    ) -> Result<()> {
        match (
            &self.p.types.entries[formal.0 as usize].kind,
            &self.p.types.entries[actual.0 as usize].kind,
        ) {
            (TypeDefinition::Parameter(p), _) => {
                if let Some(previous) = substitutions.insert(*p, actual) {
                    self.require_type(node, actual, previous)?;
                }
            }
            (
                TypeDefinition::Reference {
                    permission: a,
                    target: f,
                },
                TypeDefinition::Reference {
                    permission: b,
                    target: v,
                },
            ) if std::mem::discriminant(a) == std::mem::discriminant(b) => {
                self.infer_substitutions(node, *f, *v, substitutions)?
            }
            (TypeDefinition::Pool { element: a }, TypeDefinition::Pool { element: b })
            | (
                TypeDefinition::GrowingSequence { element: a },
                TypeDefinition::GrowingSequence { element: b },
            )
            | (
                TypeDefinition::Allocation { content: a },
                TypeDefinition::Allocation { content: b },
            ) => self.infer_substitutions(node, *a, *b, substitutions)?,
            (
                TypeDefinition::ExecutionHandle {
                    result: a,
                    asynchronous: aa,
                },
                TypeDefinition::ExecutionHandle {
                    result: b,
                    asynchronous: ba,
                },
            ) if aa == ba => self.infer_substitutions(node, *a, *b, substitutions)?,
            (
                TypeDefinition::KeyedCollection { key: a, value: av },
                TypeDefinition::KeyedCollection { key: b, value: bv },
            ) => {
                self.infer_substitutions(node, *a, *b, substitutions)?;
                self.infer_substitutions(node, *av, *bv, substitutions)?;
            }
            (TypeDefinition::Tuple(a), TypeDefinition::Tuple(b)) if a.len() == b.len() => {
                for (f, v) in a.iter().zip(b) {
                    self.infer_substitutions(node, *f, *v, substitutions)?;
                }
            }
            (
                TypeDefinition::Array {
                    element: a,
                    length: al,
                },
                TypeDefinition::Array {
                    element: b,
                    length: bl,
                },
            ) if al == bl => self.infer_substitutions(node, *a, *b, substitutions)?,
            (TypeDefinition::Slice { element: a }, TypeDefinition::Slice { element: b }) => {
                self.infer_substitutions(node, *a, *b, substitutions)?
            }
            (
                TypeDefinition::Nominal {
                    definition: a,
                    arguments: ap,
                    ..
                },
                TypeDefinition::Nominal {
                    definition: b,
                    arguments: bp,
                    ..
                },
            ) if a == b && ap.len() == bp.len() => {
                for (a, b) in ap.iter().zip(bp) {
                    if let (TypeArgument::Type(a), TypeArgument::Type(b)) = (a, b) {
                        self.infer_substitutions(node, *a, *b, substitutions)?;
                    }
                }
            }
            _ if self.callable_signature(formal).is_some()
                && self.callable_signature(actual).is_some() =>
            {
                let (f, _) = self.callable_signature(formal).unwrap();
                let (a, _) = self.callable_signature(actual).unwrap();
                let f = &self.p.declarations.signatures[f.0 as usize];
                let a = &self.p.declarations.signatures[a.0 as usize];
                if f.parameters.len() != a.parameters.len() {
                    return Err(self.fail(
                        node,
                        DiagnosticKind::TypeMismatch,
                        "callable signatures have different arity",
                    ));
                }
                for (f, a) in f.parameters.iter().zip(&a.parameters) {
                    self.infer_substitutions(node, f.ty, a.ty, substitutions)?;
                }
                self.infer_substitutions(node, f.result, a.result, substitutions)?;
            }
            _ => self.require_type(node, actual, formal)?,
        }
        Ok(())
    }
    fn empty_dependency_summary(&mut self) -> DependencySummaryId {
        let id = DependencySummaryId(self.p.values.dependency_summaries.len() as u32);
        self.p.values.dependency_summaries.push(DependencySummary {
            id,
            dependencies: vec![],
            guarded: vec![],
            deferred_result: vec![],
        });
        id
    }
    fn instance(&mut self, function: FunctionId) -> Result<FunctionInstanceId> {
        self.specialized_instance(function, vec![])
    }
    fn specialized_instance(
        &mut self,
        function: FunctionId,
        actual: Vec<TypeId>,
    ) -> Result<FunctionInstanceId> {
        let key = (function, actual.clone(), self.active_configuration);
        if let Some(id) = self.instances.get(&key) {
            return Ok(*id);
        }
        let mut source = self.functions[function.0 as usize].clone();
        let caller_unit = self.current_unit;
        let caller_configuration = self.active_configuration;
        self.switch_unit(source.unit);
        let parameters = self.p.declarations.functions[function.0 as usize]
            .type_parameters
            .clone();
        if parameters.len() != actual.len() {
            return Err(self.fail(
                source.node,
                DiagnosticKind::InvalidType,
                "generic function needs concrete substitutions",
            ));
        }
        let substitutions = parameters
            .iter()
            .copied()
            .zip(actual.iter().copied())
            .collect::<HashMap<_, _>>();
        let mut concrete_parameters = vec![];
        for (index, (name, ty, mutable)) in source.parameters.clone().into_iter().enumerate() {
            let ty = if let Some(written) = source.parameter_syntax.get(index).copied().flatten() {
                self.type_syntax(written, source.scope)?
            } else {
                self.configured_type(ty, self.active_configuration)
            };
            let ty = self.substitute_type(ty, &substitutions);
            concrete_parameters.push((name, ty, mutable));
        }
        source.parameters = concrete_parameters;
        let result_type = if let Some(written) = source.result_syntax {
            self.type_syntax(written, source.scope)?
        } else {
            self.configured_type(source.result, self.active_configuration)
        };
        source.result = self.substitute_type(result_type, &substitutions);
        let template = self.p.declarations.signatures[source.signature.0 as usize].clone();
        let receiver = match template.receiver {
            ReceiverMode::Shared(t) => {
                let ty = self.substitute_type(t, &substitutions);
                ReceiverMode::Shared(self.configured_type(ty, self.active_configuration))
            }
            ReceiverMode::Mutable(t) => {
                let ty = self.substitute_type(t, &substitutions);
                ReceiverMode::Mutable(self.configured_type(ty, self.active_configuration))
            }
            ReceiverMode::ByValue(t) => {
                let ty = self.substitute_type(t, &substitutions);
                ReceiverMode::ByValue(self.configured_type(ty, self.active_configuration))
            }
            ReceiverMode::None => ReceiverMode::None,
        };
        source.signature = self.signature(
            source.parameters.iter().map(|p| p.1).collect(),
            source.result,
            receiver,
            template.execution,
        );

        let id = FunctionInstanceId(self.p.declarations.instances.len() as u32);
        let effects = EffectSummaryId(self.p.effects.len() as u32);
        self.p.effects.push(EffectSummary {
            id: effects,
            effects: vec![],
        });
        let result_summary = self.empty_dependency_summary();
        self.p.declarations.instances.push(FunctionInstance {
            resolution: if actual.iter().any(|ty| self.has_parameters(*ty)) {
                InstanceResolution::Parametric {
                    parameters: parameters.clone(),
                }
            } else {
                InstanceResolution::Concrete
            },
            configuration: self.active_configuration,
            id,
            body: None,
            contract_matches: vec![],
            contracts: vec![],
            result: FunctionResultSummary {
                native: None,
                values: vec![],
                dependencies: result_summary,
            },
            definition: function,
            substitutions: parameters
                .iter()
                .copied()
                .zip(actual)
                .map(|(parameter, actual)| TypeSubstitution { parameter, actual })
                .collect(),
            signature: source.signature,
            effects,
        });
        self.instances.insert(key, id);
        let matches = self.resolve_contracts(source.node, &parameters, &substitutions)?;
        self.p.declarations.instances[id.0 as usize].contract_matches = matches;
        let Some(body_node) = source.body else {
            self.resolve_function_effect_annotations(id)?;
            self.switch_unit(caller_unit);
            return Ok(id);
        };
        let old = self.ctx.take();
        let body = BodyId(self.p.bodies.len() as u32);
        let scope = ScopeId(self.names.len() as u32);
        let branch = BranchId(self.p.execution.branches.len() as u32);
        let timeline = TimelineId(self.p.execution.timelines.len() as u32);
        let domain = InstanceDomainId(self.p.execution.instance_domains.len() as u32);
        let entry = ExecutionMomentId(self.p.execution.execution_moments.len() as u32);
        self.p.execution.instance_domains.push(InstanceDomain {
            id: domain,
            definition: InstanceDomainDefinition::Root { body },
        });
        self.p.execution.branches.push(Branch {
            id: branch,
            timeline,
            kind: BranchKind::Root(RootBranch { body }),
        });
        self.p.execution.timelines.push(Timeline {
            id: timeline,
            branch,
            lexical_order: vec![],
            execution_moments: vec![],
            entries: NonEmpty {
                first: entry,
                rest: vec![],
            },
            exits: vec![],
        });
        self.p.bodies.push(FunctionBody {
            id: body,
            owner: BodyOwner::Instance(id),
            environment: source.captures,
            scope,
            root_branch: branch,
            operations: vec![],
        });
        self.names.push(HashMap::new());
        self.ctx = Some(Context {
            unit: self.current_unit,
            body,
            function,
            instance: id,
            substitutions,
            return_type: if source.infer_result {
                None
            } else {
                Some(source.result)
            },
            scope,
            branch,
            timeline,
            domain,
            guard: PredicateId(0),
            last: None,
            parent_anchor: None,
            instruction: body_node,
            bindings: HashMap::new(),
            returns: vec![],
            loops: vec![],
            unchecked: vec![],
        });
        let site = self.site(body_node, ExecutionPhase::Enter);
        let storage = self.scope_storage(scope, site.execution_moments.first);
        self.p.scopes.entries.push(Scope {
            configuration: self.active_configuration,
            id: scope,
            lexical_scope: self.lexical_scopes[&body_node],
            lexical_parent: Some(source.scope),
            unchecked_boundary: None,
            children: vec![],
            context: ScopeContext::Body(body),
            entry: ScopeEntry::BodyRoot {
                lexical: site.lexical_moment,
                execution: site.execution_moments.first,
            },
            exits: vec![],
            bindings: vec![],
            storage: ScopeStorageLink::Runtime(storage),
        });
        self.p.scopes.entries[source.scope.0 as usize]
            .children
            .push(scope);
        let cursor = self.p.scopes.storage[storage.0 as usize].entry;
        self.emit(Operation::EnterScope(EnterScope {
            site: site.clone(),
            scope,
            cursor,
        }));
        self.p.declarations.instances[id.0 as usize].body = Some(body);
        for (position, (name, ty, mutable)) in source.parameters.iter().enumerate() {
            let binding = BindingId(self.p.scopes.bindings.len() as u32);
            let sym =
                self.anonymous_symbol(name, scope, SymbolDefinition::Binding(binding), source.node);
            self.names[scope.0 as usize].insert(name.clone(), sym);
            self.p.scopes.bindings.push(Binding {
                id: binding,
                symbol: sym,
                ty: *ty,
                scope,
                mutable: *mutable,
                introduced: BindingIntroduction::Parameter {
                    function,
                    position: position as u32,
                },
            });
            self.p.scopes.entries[scope.0 as usize]
                .bindings
                .push(binding);
            let value = self.value(
                *ty,
                ValueDefinition::Parameter(binding),
                ProvenanceKind::Binding(binding),
                vec![],
            );
            if !(self.primitive(*ty) || self.enum_copy(*ty))
                && !matches!(
                    self.p.types.entries[ty.0 as usize].kind,
                    TypeDefinition::Reference { .. }
                )
            {
                let summary = self.p.values.entries[value.0 as usize].dependencies;
                self.p.values.dependency_summaries[summary.0 as usize]
                    .dependencies
                    .push(DependencyRequirement::CarriedByParameter { binding });
            }
            self.ctx_mut().bindings.insert(binding, value);
            self.materialize_binding(binding, value, &site);
            if let TypeDefinition::Reference { permission, target } =
                self.p.types.entries[ty.0 as usize].kind.clone()
            {
                let reference = ReferenceId(self.p.objects.references.len() as u32);
                let referent = self.place(
                    PlaceRoot::Binding(binding),
                    vec![PlaceProjection::Dereference],
                    target,
                );
                let owner = self.binding_owner(binding);
                self.p.objects.references.push(Reference {
                    creation: ObjectCreation::At(site.execution_moments.first),
                    created_in: scope,
                    initial_owner: owner,
                    id: reference,
                    ty: *ty,
                    permission,
                    formation: ReferenceFormation::Loan,
                    origins: NonEmpty {
                        first: ReferenceOrigin {
                            target: referent,
                            parent: None,
                            guard: PredicateId(0),
                        },
                        rest: vec![],
                    },
                });
                self.references.insert(value, reference);
                self.value_entities
                    .insert(value, EntityId::Reference(reference));
                self.binding_entities
                    .insert(binding, EntityId::Reference(reference));
                let summary = self.p.values.entries[value.0 as usize].dependencies;
                self.p.values.dependency_summaries[summary.0 as usize]
                    .dependencies
                    .push(DependencyRequirement::LiveTarget(referent));
            }
        }
        if let Some(record) = source.captures {
            self.bind_capture_environment(record, &site)?;
        }
        let mut signature = self.p.declarations.signatures[source.signature.0 as usize].clone();
        signature.id = SignatureId(self.p.declarations.signatures.len() as u32);
        signature.parameters = self.p.scopes.entries[scope.0 as usize]
            .bindings
            .iter()
            .filter(|binding| {
                matches!(
                    self.p.scopes.bindings[binding.0 as usize].introduced,
                    BindingIntroduction::Parameter { .. }
                )
            })
            .map(|binding| {
                let definition = &self.p.scopes.bindings[binding.0 as usize];
                ParameterDefinition {
                    identity: ParameterIdentity::Named {
                        symbol: definition.symbol,
                        binding: *binding,
                    },
                    ty: definition.ty,
                }
            })
            .collect();
        self.p.declarations.instances[id.0 as usize].signature = signature.id;
        self.p.declarations.signatures.push(signature);
        let tail = self.block_contents(body_node, self.ctx().return_type)?;
        if let Some(tail) = tail {
            self.resolve_return_type(body_node, self.vtype(tail.value))?;
            let return_site = self.site(body_node, ExecutionPhase::Receive);
            let exit = self.scope_exit(scope, &return_site, ScopeExitKind::Return);
            self.ctx_mut().returns.push(GuardedValue {
                guard: return_site.guard,
                value: tail.value,
            });
            self.return_to_caller(tail.value, id, &return_site);
            self.emit(Operation::ReturnControl(ReturnControl {
                site: return_site,
                function: id,
                value: tail.value,
                exit,
                outer_exits: vec![],
            }));
        }
        let final_context = self.ctx.take().unwrap();
        if source.infer_result {
            let inferred = final_context
                .returns
                .first()
                .map(|v| self.vtype(v.value))
                .unwrap_or(self.never);
            for result in &final_context.returns {
                self.require_type(source.node, self.vtype(result.value), inferred)?;
            }
            let signature = self.p.declarations.instances[id.0 as usize].signature;
            self.p.declarations.signatures[signature.0 as usize].result = inferred;
        }
        let return_effects = final_context
            .returns
            .iter()
            .flat_map(|r| self.guarded_dependencies(r.value, r.guard))
            .collect::<Vec<_>>();
        // Save exact return dependency summaries for instantiation at calls.
        self.p.values.dependency_summaries[result_summary.0 as usize].guarded =
            return_effects.clone();
        self.p.declarations.instances[id.0 as usize].result.values = final_context.returns.clone();

        if let Some(last) = final_context.last {
            if self
                .p
                .scopes
                .exits
                .iter()
                .any(|e| e.scope == scope && e.event == last)
                && self.p.execution.execution_moments[last.0 as usize].timeline == timeline
            {
                self.p.execution.timelines[timeline.0 as usize]
                    .exits
                    .push(last);
            }
        }
        if matches!(
            self.p.declarations.signatures[source.signature.0 as usize].execution,
            FunctionExecution::Asynchronous
        ) {
            self.resolve_async_frame(id)?;
        }
        self.resolve_function_effect_annotations(id)?;
        self.ctx = old;
        self.active_configuration = caller_configuration;
        self.switch_unit(caller_unit);
        Ok(id)
    }
    fn binding_owner(&self, binding: BindingId) -> Owner {
        Owner::Binding {
            binding,
            instance: self.ctx().domain,
        }
    }
    fn scope_storage(&mut self, scope: ScopeId, moment: ExecutionMomentId) -> ScopeStorageId {
        let incoming = CursorExpressionId(self.p.cursor_expressions.len() as u32);
        self.p.cursor_expressions.push(CursorExpression {
            id: incoming,
            kind: CursorExpressionKind::IncomingScopeCursor(scope),
        });
        let snapshot = CursorSnapshotId(self.p.cursor_snapshots.len() as u32);
        self.p.cursor_snapshots.push(CursorSnapshot {
            id: snapshot,
            scope,
            moment,
            cursor: incoming,
        });
        let limit = CursorExpressionId(self.p.cursor_expressions.len() as u32);
        self.p.cursor_expressions.push(CursorExpression {
            id: limit,
            kind: CursorExpressionKind::ScopeUpperLimit(scope),
        });
        let id = ScopeStorageId(self.p.scopes.storage.len() as u32);
        self.p.scopes.storage.push(ScopeStorage {
            id,
            scope,
            entry: snapshot,
            relative_cursor: incoming,
            upper_limit: limit,
            stack: DataStackId(0),
            region: None,
        });
        id
    }
    fn scope_exit(
        &mut self,
        scope: ScopeId,
        site: &OperationSite,
        kind: ScopeExitKind,
    ) -> ScopeExitId {
        let id = ScopeExitId(self.p.scopes.exits.len() as u32);
        self.p.scopes.exits.push(ScopeExit {
            id,
            scope,
            event: site.execution_moments.first,
            guard: site.guard,
            kind,
        });
        self.p.scopes.entries[scope.0 as usize].exits.push(id);
        id
    }
    fn place(&mut self, root: PlaceRoot, projections: Vec<PlaceProjection>, ty: TypeId) -> PlaceId {
        let id = PlaceId(self.p.objects.places.len() as u32);
        self.p.objects.places.push(Place {
            id,
            root,
            projections,
            ty,
        });
        id
    }
    fn evaluated_place(
        &mut self,
        n: ast::NodeId,
        place: PlaceId,
        selectors: Vec<ValueId>,
    ) -> EvaluatedPlaceId {
        let site = self.site(n, ExecutionPhase::Evaluate);
        let id = EvaluatedPlaceId(self.p.objects.evaluated_places.len() as u32);
        self.p.objects.evaluated_places.push(EvaluatedPlace {
            id,
            definition: place,
            produced_by: site.id,
            selectors,
        });
        self.emit(Operation::EvaluatePlace(EvaluatePlace {
            site,
            place,
            result: id,
        }));
        id
    }
    fn materialize_binding(&mut self, binding: BindingId, value: ValueId, site: &OperationSite) {
        let owner = self.binding_owner(binding);
        self.materialize_value(value, owner, site);
        if let Some(entity) = self.value_entities.get(&value).cloned() {
            self.binding_entities.insert(binding, entity);
        }
    }
    fn materialize_value(&mut self, value: ValueId, owner: Owner, site: &OperationSite) {
        if !self.value_entities.contains_key(&value)
            && !self.value_entities_at(value, site.guard).is_empty()
        {
            self.transfer(value, owner, site);
            return;
        }
        let entity = if let Some(entity) = self.value_entities.get(&value) {
            entity.clone()
        } else {
            let id = AddressId(self.p.objects.addresses.len() as u32);
            let storage = StorageOriginId(self.p.storage_origins.len() as u32);
            self.p.storage_origins.push(StorageOrigin {
                id: storage,
                creation: StorageCreation::Operation(site.id),
                pool: None,
                pool_choices: vec![],
            });
            self.address_values.push(value);
            if let ScopeStorageLink::Runtime(storage) =
                self.p.scopes.entries[site.scope.0 as usize].storage
            {
                let base = self.p.scopes.storage[storage.0 as usize].relative_cursor;
                let cursor = CursorExpressionId(self.p.cursor_expressions.len() as u32);
                self.p.cursor_expressions.push(CursorExpression {
                    id: cursor,
                    kind: CursorExpressionKind::AdvanceByType {
                        base,
                        ty: self.vtype(value),
                    },
                });
                self.p.scopes.storage[storage.0 as usize].relative_cursor = cursor;
            }
            self.p.objects.addresses.push(Address {
                created_in: site.scope,
                initial_owner: owner.clone(),
                id,
                ty: self.vtype(value),
                creation: ObjectCreation::At(site.execution_moments.first),
                storage,
            });
            let place_summary = self.p.values.entries[value.0 as usize].placement;
            self.p.values.placement_summaries[place_summary.0 as usize]
                .origins
                .push(storage);
            EntityId::Address(id)
        };
        self.value_entities.insert(value, entity.clone());
        if let Some(parts) = self.components.get(&value).cloned() {
            for part in parts {
                for (component_guard, component) in self.value_entities_at(part, site.guard) {
                    let guard = if component_guard == site.guard {
                        site.guard
                    } else {
                        self.predicate(PredicateKind::All(vec![component_guard, site.guard]))
                    };
                    self.p.objects.ownership.push(OwnershipLink {
                        entity: component,
                        owner: Owner::Entity(EntityOccurrence {
                            entity: entity.clone(),
                            instance: self.ctx().domain,
                        }),
                        scope: site.scope,
                        established: site.execution_moments.first,
                        guard,
                    });
                }
            }
        }
        self.p.objects.ownership.push(OwnershipLink {
            entity: entity.clone(),
            owner: owner.clone(),
            scope: site.scope,
            established: site.execution_moments.first,
            guard: site.guard,
        });
        for fact in self.guarded_dependencies(value, site.guard) {
            let id = DependencyLinkId(self.p.objects.dependencies.len() as u32);
            self.p.objects.dependencies.push(DependencyLink {
                id,
                dependent: entity.clone(),
                requirement: fact.requirement,
                established: site.execution_moments.first,
                guard: fact.guard,
            });
        }
    }
    fn bind(
        &mut self,
        n: ast::NodeId,
        name: &str,
        mutable: bool,
        value: ValueId,
    ) -> Result<BindingId> {
        let scope = self.ctx().scope;
        let ty = self.vtype(value);
        let id = BindingId(self.p.scopes.bindings.len() as u32);
        let symbol = if self.names[scope.0 as usize]
            .get(name)
            .is_some_and(|symbol| {
                matches!(
                    self.p.symbols.entries[symbol.0 as usize].definition,
                    SymbolDefinition::Binding(_)
                )
            }) {
            // Shadow only the lexical spelling. Earlier bindings retain their
            // identities, references, ownership and end-of-scope cleanup.
            let symbol = self.anonymous_symbol(name, scope, SymbolDefinition::Binding(id), n);
            self.names[scope.0 as usize].insert(name.into(), symbol);
            self.cover(n, SyntaxDisposition::Declaration(symbol));
            symbol
        } else {
            self.declare(n, scope, name, SymbolDefinition::Binding(id))?
        };
        let site = self.site(n, ExecutionPhase::Write);
        self.p.scopes.bindings.push(Binding {
            id,
            symbol,
            ty,
            scope,
            mutable,
            introduced: BindingIntroduction::At(site.execution_moments.first),
        });
        self.p.scopes.entries[scope.0 as usize].bindings.push(id);
        self.ctx_mut().bindings.insert(id, value);
        self.materialize_binding(id, value, &site);
        let dependencies = self.p.values.entries[value.0 as usize].dependencies;
        self.transfers.push(TransferLink {
            source: value,
            result: value,
            entity: self.value_entities.get(&value).cloned(),
            operation: site.id,
            at: site.execution_moments.first,
            guard: site.guard,
            receiver: self.binding_owner(id),
        });
        let _ = dependencies;
        self.emit(Operation::InitializeBinding(InitializeBinding {
            site,
            binding: id,
            value,
        }));
        Ok(id)
    }
    fn primitive(&self, ty: TypeId) -> bool {
        matches!(
            self.p.types.entries[ty.0 as usize].kind,
            TypeDefinition::Numeric(_) | TypeDefinition::Boolean | TypeDefinition::Unit
        )
    }
    fn shared_reference(&self, ty: TypeId) -> bool {
        matches!(
            self.p.types.entries[ty.0 as usize].kind,
            TypeDefinition::Reference {
                permission: ReferencePermission::Shared,
                ..
            }
        )
    }
    fn implicit_copy(&self, ty: TypeId) -> bool {
        self.primitive(ty) || self.enum_copy(ty) || self.shared_reference(ty)
    }
    fn enum_copy(&self, ty: TypeId) -> bool {
        self.p
            .declarations
            .enums
            .iter()
            .find(|e| e.ty == ty)
            .is_some_and(|e| {
                std::iter::once(&e.variants.first)
                    .chain(&e.variants.rest)
                    .all(|v| {
                        self.p.declarations.variants[v.0 as usize]
                            .fields
                            .iter()
                            .all(|f| self.primitive(self.p.declarations.fields[f.0 as usize].ty))
                    })
            })
    }
    /// Enum copy eligibility depends on whether abstract payloads become primitives.
    /// Keep that compile-time decision symbolic rather than classifying it as a move.
    fn parametric_copy(&self, ty: TypeId) -> bool {
        if matches!(
            self.p.types.entries[ty.0 as usize].kind,
            TypeDefinition::Parameter(_)
        ) {
            return true;
        }
        self.p
            .declarations
            .enums
            .iter()
            .find(|e| e.ty == ty)
            .is_some_and(|e| {
                let fields = std::iter::once(&e.variants.first)
                    .chain(&e.variants.rest)
                    .flat_map(|v| &self.p.declarations.variants[v.0 as usize].fields)
                    .map(|f| self.p.declarations.fields[f.0 as usize].ty)
                    .collect::<Vec<_>>();
                fields.iter().any(|f| {
                    matches!(
                        self.p.types.entries[f.0 as usize].kind,
                        TypeDefinition::Parameter(_)
                    )
                }) && fields.iter().all(|f| {
                    self.primitive(*f)
                        || matches!(
                            self.p.types.entries[f.0 as usize].kind,
                            TypeDefinition::Parameter(_)
                        )
                })
            })
    }
    fn transfer_kind(&self, ty: TypeId) -> TransferKind {
        if self.parametric_copy(ty) {
            TransferKind::ByTypeParameter(ty)
        } else if self.primitive(ty) || self.shared_reference(ty) {
            TransferKind::PrimitiveCopy
        } else if self.enum_copy(ty) {
            TransferKind::EligibleEnumCopy
        } else {
            TransferKind::Move
        }
    }
    fn block_contents(&mut self, n: ast::NodeId, expected: Option<TypeId>) -> Result<Option<Expr>> {
        let NodeKind::Block {
            annotations,
            statements,
            result,
        } = self.kind(n)
        else {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                "function body must be a block",
            ));
        };
        for annotation in annotations {
            self.memory_annotation(*annotation, self.ctx().scope)?;
        }
        for (index, statement) in statements.iter().enumerate() {
            self.ctx_mut().instruction = *statement;
            if !self.statement(*statement)? {
                let after = self.ctx().last.expect("terminator has an execution moment");
                self.unreachable_tail(n, &statements[index + 1..], *result, after);
                return Ok(None);
            }
        }
        if let Some(result) = result {
            self.ctx_mut().instruction = *result;
            let expression = self.expression(*result, expected)?;
            if self.vtype(expression.value) == self.never {
                Ok(None)
            } else {
                Ok(Some(expression))
            }
        } else {
            let site = self.site(n, ExecutionPhase::Compute);
            let result = self.op_value(&site, self.unit, vec![]);
            self.emit(Operation::UnitValue(UnitValue { site, result }));
            Ok(Some(Expr { value: result }))
        }
    }
    fn expression(&mut self, n: ast::NodeId, expected: Option<TypeId>) -> Result<Expr> {
        let expression = self.expression_inner(n, expected)?;
        self.adapt_callable(n, expression, expected)
    }
    fn expression_inner(&mut self, n: ast::NodeId, expected: Option<TypeId>) -> Result<Expr> {
        match self.kind(n) {
            NodeKind::Literal { token } => {
                let text = self.text(*token);
                let ty = if text == "true" || text == "false" {
                    self.boolean
                } else if self.syntax.tokens[token.index].kind == crate::lexer::Kind::Text {
                    let str_ty = self.intern(TypeKey::Str);
                    self.intern(TypeKey::Reference(false, str_ty))
                } else if self.syntax.tokens[token.index].kind == crate::lexer::Kind::Float {
                    match expected {
                        Some(t)
                            if matches!(
                                self.p.types.entries[t.0 as usize].kind,
                                TypeDefinition::Numeric(NumericType::F32 | NumericType::F64)
                            ) =>
                        {
                            t
                        }
                        _ => self.intern(TypeKey::Numeric(NumericType::F64)),
                    }
                } else {
                    match expected {
                        Some(t)
                            if matches!(
                                self.p.types.entries[t.0 as usize].kind,
                                TypeDefinition::Numeric(
                                    NumericType::I32
                                        | NumericType::I64
                                        | NumericType::U8
                                        | NumericType::U16
                                        | NumericType::U32
                                        | NumericType::U64
                                        | NumericType::Usize
                                )
                            ) =>
                        {
                            t
                        }
                        _ => self.integer,
                    }
                };
                let site = self.site(n, ExecutionPhase::Compute);
                let result = self.op_value(&site, ty, vec![]);
                let operation = match self.p.types.entries[ty.0 as usize].kind.clone() {
                    TypeDefinition::Boolean => Operation::BooleanLiteral(BooleanLiteral {
                        site,
                        value: text == "true",
                        result,
                    }),
                    TypeDefinition::Numeric(NumericType::F32) => {
                        let value = text.parse::<f32>().map_err(|_| {
                            self.fail(n, DiagnosticKind::InvalidType, "invalid f32 literal")
                        })?;
                        if !value.is_finite()
                            || value == 0.0 && text.chars().any(|c| matches!(c, '1'..='9'))
                        {
                            return Err(self.fail(
                                n,
                                DiagnosticKind::InvalidType,
                                "float literal is out of range",
                            ));
                        }
                        Operation::FloatLiteral(FloatLiteral {
                            site,
                            value: FloatConstant::F32Bits(value.to_bits()),
                            result,
                        })
                    }
                    TypeDefinition::Numeric(NumericType::F64) => {
                        let value = text.parse::<f64>().map_err(|_| {
                            self.fail(n, DiagnosticKind::InvalidType, "invalid f64 literal")
                        })?;
                        if !value.is_finite()
                            || value == 0.0 && text.chars().any(|c| matches!(c, '1'..='9'))
                        {
                            return Err(self.fail(
                                n,
                                DiagnosticKind::InvalidType,
                                "float literal is out of range",
                            ));
                        }
                        Operation::FloatLiteral(FloatLiteral {
                            site,
                            value: FloatConstant::F64Bits(value.to_bits()),
                            result,
                        })
                    }
                    TypeDefinition::Numeric(domain) => {
                        let unsigned = self.integer_constant(n, self.ctx().scope)? as u128;
                        let max = match domain {
                            NumericType::I32 => i32::MAX as u128,
                            NumericType::I64 => i64::MAX as u128,
                            NumericType::U8 => u8::MAX as u128,
                            NumericType::U16 => u16::MAX as u128,
                            NumericType::U32 => u32::MAX as u128,
                            NumericType::U64 => u64::MAX as u128,
                            NumericType::Usize => {
                                if self.p.target.pointer_bits == 32 {
                                    u32::MAX as u128
                                } else {
                                    u64::MAX as u128
                                }
                            }
                            _ => {
                                return Err(self.fail(
                                    n,
                                    DiagnosticKind::TypeMismatch,
                                    "integer literal requires an integer type",
                                ));
                            }
                        };
                        if unsigned > max {
                            return Err(self.fail(
                                n,
                                DiagnosticKind::TypeMismatch,
                                format!("literal does not fit {}", self.type_name(ty)),
                            ));
                        }
                        Operation::IntegerLiteral(IntegerLiteral {
                            site,
                            value: IntegerConstant::Unsigned(unsigned),
                            result,
                        })
                    }
                    TypeDefinition::Reference { .. } => {
                        let crate::lexer::Payload::Text(utf8) =
                            &self.syntax.tokens[token.index].payload
                        else {
                            unreachable!()
                        };
                        let bytes = utf8.clone();
                        let TypeDefinition::Reference { target, .. } =
                            self.p.types.entries[ty.0 as usize].kind
                        else {
                            unreachable!()
                        };
                        let storage = StorageOriginId(self.p.storage_origins.len() as u32);
                        self.p.storage_origins.push(StorageOrigin {
                            id: storage,
                            creation: StorageCreation::Static(site.origin),
                            pool: None,
                            pool_choices: vec![],
                        });
                        let address = AddressId(self.p.objects.addresses.len() as u32);
                        self.address_values.push(result);
                        self.p.objects.addresses.push(Address {
                            id: address,
                            ty: target,
                            created_in: ScopeId(0),
                            initial_owner: Owner::Scope {
                                scope: ScopeId(0),
                                instance: self.ctx().domain,
                            },
                            creation: ObjectCreation::Static(site.origin),
                            storage,
                        });
                        let place = self.place(PlaceRoot::Address(address), vec![], target);
                        let reference = ReferenceId(self.p.objects.references.len() as u32);
                        let owner = Owner::Scope {
                            scope: site.scope,
                            instance: self.ctx().domain,
                        };
                        self.p.objects.references.push(Reference {
                            id: reference,
                            created_in: site.scope,
                            creation: ObjectCreation::At(site.execution_moments.first),
                            initial_owner: owner,
                            ty,
                            permission: ReferencePermission::Shared,
                            formation: ReferenceFormation::Loan,
                            origins: NonEmpty {
                                first: ReferenceOrigin {
                                    target: place,
                                    parent: None,
                                    guard: site.guard,
                                },
                                rest: vec![],
                            },
                        });
                        self.references.insert(result, reference);
                        self.value_entities
                            .insert(result, EntityId::Reference(reference));
                        let dependencies = self.p.values.entries[result.0 as usize].dependencies;
                        self.p.values.dependency_summaries[dependencies.0 as usize]
                            .dependencies
                            .push(DependencyRequirement::LiveTarget(place));
                        Operation::TextLiteral(TextLiteral {
                            site,
                            storage: address,
                            reference,
                            utf8: bytes,
                            result,
                        })
                    }
                    _ => unreachable!(),
                };
                self.emit(operation);
                if let Some(expected) = expected {
                    self.require_type(n, ty, expected)?;
                }
                Ok(Expr { value: result })
            }
            NodeKind::Parenthesized { expression } => {
                self.cover(
                    n,
                    SyntaxDisposition::Grouping {
                        forwards: self.syntax_id(*expression),
                    },
                );
                self.expression(*expression, expected)
            }
            NodeKind::Tuple { elements } => {
                let expected_elements =
                    expected.and_then(|ty| match &self.p.types.entries[ty.0 as usize].kind {
                        TypeDefinition::Tuple(types) => Some(types.clone()),
                        _ => None,
                    });
                let mut values = vec![];
                for (index, e) in elements.iter().enumerate() {
                    values.push(
                        self.expression(
                            *e,
                            expected_elements
                                .as_ref()
                                .and_then(|v| v.get(index))
                                .copied(),
                        )?
                        .value,
                    );
                }
                let ty = if values.is_empty() {
                    self.unit
                } else {
                    self.intern(TypeKey::Tuple(
                        values.iter().map(|v| self.vtype(*v)).collect(),
                    ))
                };
                let site = self.site(n, ExecutionPhase::Compute);
                let dependencies = values.iter().flat_map(|v| self.dependencies(*v)).collect();
                let result = self.op_value(&site, ty, dependencies);
                let components = values
                    .iter()
                    .enumerate()
                    .map(|(index, v)| ComponentInitialization {
                        position: PositionSelector::TupleElement(index as u32),
                        value: *v,
                        transfer: self.transfer_kind(self.vtype(*v)),
                    })
                    .collect();
                self.emit(Operation::ConstructTuple(ConstructTuple {
                    site,
                    ty,
                    components,
                    result,
                }));
                self.components.insert(result, values);
                Ok(Expr { value: result })
            }
            NodeKind::Array { elements, repeat } => {
                let hint = expected
                    .and_then(|ty| match self.p.types.entries[ty.0 as usize].kind {
                        TypeDefinition::Array { element, .. } => Some(element),
                        _ => None,
                    })
                    .or_else(|| elements.iter().find_map(|node| self.known_type(*node)));
                let mut values = vec![];
                let mut element_ty = hint;
                for e in elements {
                    let v = self.expression(*e, element_ty)?.value;
                    if let Some(required) = element_ty {
                        self.require_type(*e, self.vtype(v), required)?;
                    }
                    element_ty = Some(self.vtype(v));
                    values.push(v);
                }
                let element = element_ty.ok_or_else(|| {
                    self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "an empty array requires an element type annotation",
                    )
                })?;
                let length = if let Some(count) = repeat {
                    self.integer_constant(*count, self.ctx().scope)?
                } else {
                    values.len() as u64
                };
                let ty = self.intern(TypeKey::Array(element, length));
                let site = self.site(n, ExecutionPhase::Compute);
                let dependencies = if length == 0 {
                    vec![]
                } else {
                    values.iter().flat_map(|v| self.dependencies(*v)).collect()
                };
                let result = self.op_value(&site, ty, dependencies);
                if repeat.is_some() {
                    let seed = values[0];
                    let replication = if length <= 1 {
                        StructuralReplicationPlan {
                            ty: element,
                            strategy: StructuralReplicationStrategy::NoDuplication,
                        }
                    } else {
                        self.replication_plan(element, n, &mut HashSet::new())?
                    };
                    self.emit(Operation::RepeatArray(RepeatArray {
                        site,
                        seed,
                        count: length,
                        replication,
                        result,
                    }));
                } else {
                    let components = values
                        .iter()
                        .enumerate()
                        .map(|(i, v)| ComponentInitialization {
                            position: PositionSelector::FixedIndex(i as u64),
                            value: *v,
                            transfer: self.transfer_kind(element),
                        })
                        .collect();
                    self.emit(Operation::ConstructArray(ConstructArray {
                        site,
                        ty,
                        components,
                        result,
                    }));
                }
                // Empty repetitions evaluate the seed but do not own it.
                if length != 0 {
                    self.components.insert(result, values);
                }
                if let Some(e) = expected {
                    self.require_type(n, ty, e)?;
                }
                Ok(Expr { value: result })
            }
            NodeKind::Path {
                segments,
                arguments,
            } => {
                let name = self.text(*segments.last().unwrap());
                let symbol = self.path_symbol(n, segments)?;
                match self.p.symbols.entries[symbol.0 as usize].definition {
                    SymbolDefinition::Binding(_) => {
                        let place = self.place_expression(n)?;
                        self.load(n, place)
                    }
                    SymbolDefinition::Constant(c) => {
                        let ty = self.p.declarations.constants[c.0 as usize].ty;
                        let resolved_constant = self.resolve_constant(c)?;
                        let value = self.value(
                            ty,
                            ValueDefinition::ConfiguredConstant {
                                constant: c,
                                configuration: self.active_configuration,
                                value: resolved_constant,
                            },
                            ProvenanceKind::Constant(c),
                            vec![],
                        );
                        Ok(Expr { value })
                    }
                    SymbolDefinition::Variant(_) => {
                        self.variant_expression(n, segments, &[], expected)
                    }
                    SymbolDefinition::Function(function) => {
                        self.function_item(n, function, arguments, expected)
                    }
                    _ => Err(self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        format!("'{name}' is not a value"),
                    )),
                }
            }
            NodeKind::Projection { .. } | NodeKind::Index { .. } => {
                let place = self.place_expression(n)?;
                self.load(n, place)
            }
            NodeKind::Unary {
                operator,
                mutable,
                operand,
            } => {
                let op = self.text(*operator);
                if op == "&" {
                    let place = self.place_with_permission(*operand, mutable.is_some())?;
                    return self.borrow(n, place, mutable.is_some());
                }
                if op == "*" {
                    let place = self.place_expression(n)?;
                    return self.load(n, place);
                }
                if op == "-"
                    && matches!(self.kind(*operand), NodeKind::Literal { token } if self.syntax.tokens[token.index].kind == crate::lexer::Kind::Integer)
                {
                    let magnitude = self.integer_constant(*operand, self.ctx().scope)? as i128;
                    let ty = expected
                        .filter(|ty| {
                            matches!(
                                self.p.types.entries[ty.0 as usize].kind,
                                TypeDefinition::Numeric(
                                    NumericType::I32
                                        | NumericType::I64
                                        | NumericType::U8
                                        | NumericType::U16
                                        | NumericType::U32
                                        | NumericType::U64
                                        | NumericType::Usize
                                )
                            )
                        })
                        .unwrap_or(self.integer);
                    let minimum = match self.p.types.entries[ty.0 as usize].kind {
                        TypeDefinition::Numeric(NumericType::I32) => i32::MIN as i128,
                        TypeDefinition::Numeric(NumericType::I64) => i64::MIN as i128,
                        _ => 0,
                    };
                    if -magnitude < minimum {
                        return Err(self.fail(
                            n,
                            DiagnosticKind::TypeMismatch,
                            format!("signed literal does not fit {}", self.type_name(ty)),
                        ));
                    }
                    let site = self.site(n, ExecutionPhase::Compute);
                    let result = self.op_value(&site, ty, vec![]);
                    self.emit(Operation::IntegerLiteral(IntegerLiteral {
                        site,
                        value: IntegerConstant::Signed(-magnitude),
                        result,
                    }));
                    return Ok(Expr { value: result });
                }
                let operand = self.expression(*operand, expected)?;
                let ty = self.vtype(operand.value);
                if op == "!" {
                    self.require_type(n, ty, self.boolean)?;
                }
                let site = self.site(n, ExecutionPhase::Compute);
                let result = self.op_value(&site, ty, self.dependencies(operand.value));
                let domain = match self.p.types.entries[ty.0 as usize].kind {
                    TypeDefinition::Numeric(d) => Some(d),
                    _ => None,
                };
                let operation = match op {
                    "!" => Operation::BooleanNot(BooleanNot {
                        site,
                        operand: operand.value,
                        result,
                        checks: vec![],
                    }),
                    "-" => Operation::Negate(Negate {
                        site,
                        domain: domain.ok_or_else(|| {
                            self.fail(
                                n,
                                DiagnosticKind::TypeMismatch,
                                "negation requires a numeric operand",
                            )
                        })?,
                        operand: operand.value,
                        result,
                        checks: vec![],
                    }),
                    "~" => Operation::BitNot(BitNot {
                        site,
                        domain: domain.ok_or_else(|| {
                            self.fail(
                                n,
                                DiagnosticKind::TypeMismatch,
                                "bitwise not requires an integer operand",
                            )
                        })?,
                        operand: operand.value,
                        result,
                        checks: vec![],
                    }),
                    _ => {
                        return Err(self.fail(
                            n,
                            DiagnosticKind::InvalidType,
                            "unknown unary operator",
                        ));
                    }
                };
                self.emit(operation);
                Ok(Expr { value: result })
            }
            NodeKind::Binary {
                operator,
                left,
                right,
            } => self.binary(n, self.text(*operator), *left, *right, expected),
            NodeKind::Conversion { value, ty, .. } => {
                let value = self.expression(*value, None)?.value;
                let target = self.type_syntax(*ty, self.ctx().scope)?;
                let TypeDefinition::Numeric(domain) = self.p.types.entries[target.0 as usize].kind
                else {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "as requires a numeric target",
                    ));
                };
                if !matches!(
                    self.p.types.entries[self.vtype(value).0 as usize].kind,
                    TypeDefinition::Numeric(_)
                ) {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::TypeMismatch,
                        "as requires a numeric source",
                    ));
                }
                let site = self.site(n, ExecutionPhase::Compute);
                let result = self.op_value(&site, target, self.dependencies(value));
                let check = CheckId(self.p.runtime_checks.len() as u32);
                self.p
                    .runtime_checks
                    .push(RuntimeCheck::ExactConversion(ExactConversionCheck {
                        id: check,
                        value,
                        target,
                    }));
                self.emit(Operation::NumericCast(NumericCast {
                    site,
                    source: value,
                    target: domain,
                    result,
                    check,
                }));
                Ok(Expr { value: result })
            }
            NodeKind::Block { .. } => self.block_expression(n, expected),
            NodeKind::If { condition, yes, no } => {
                self.if_expression(n, *condition, *yes, *no, expected)
            }
            NodeKind::Call { callee, arguments } => self.call(n, *callee, arguments, expected),
            NodeKind::Construct { path, fields } => self.construct(n, *path, fields, expected),
            NodeKind::Loop { body } => self.loop_expression(n, None, *body, expected, None),
            NodeKind::Match { value, arms } => self.match_expression(n, *value, arms, expected),
            NodeKind::Unchecked { body, .. } => self.unchecked_expression(n, *body, expected),
            NodeKind::Foreign { token, includes } => self.foreign_expression(n, *token, includes),
            NodeKind::Propagate { value, .. } => self.propagate_expression(n, *value, false),
            NodeKind::Unwrap { value, .. } => self.propagate_expression(n, *value, true),
            NodeKind::Await { value, .. } => self.await_expression(n, *value),
            NodeKind::Closure {
                moving,
                parameters,
                result,
                body,
            } => self.capturing_expression(
                n,
                moving.is_some(),
                parameters,
                *result,
                *body,
                expected,
                false,
            ),
            NodeKind::Async { moving, body, .. } => {
                self.capturing_expression(n, moving.is_some(), &[], None, *body, expected, true)
            }
            NodeKind::MoveBlock { body, .. } => self.move_block_expression(n, *body, expected),
            NodeKind::Module { .. }
            | NodeKind::Import { .. }
            | NodeKind::ImportEntry { .. }
            | NodeKind::Function { .. }
            | NodeKind::Parameter { .. }
            | NodeKind::Struct { .. }
            | NodeKind::Enum { .. }
            | NodeKind::Field { .. }
            | NodeKind::Variant { .. }
            | NodeKind::Constant { .. }
            | NodeKind::Annotation { .. }
            | NodeKind::TypeContractAlternative { .. }
            | NodeKind::Property { .. }
            | NodeKind::Size { .. }
            | NodeKind::Conditional { .. }
            | NodeKind::Type(_)
            | NodeKind::Pattern(_)
            | NodeKind::Let { .. }
            | NodeKind::Assignment { .. }
            | NodeKind::ExpressionStatement { .. }
            | NodeKind::Return { .. }
            | NodeKind::Break { .. }
            | NodeKind::Continue { .. }
            | NodeKind::Yield { .. }
            | NodeKind::NamedMove { .. }
            | NodeKind::While { .. }
            | NodeKind::For { .. }
            | NodeKind::Range { .. }
            | NodeKind::FieldInitializer { .. }
            | NodeKind::LetCondition { .. }
            | NodeKind::MatchArm { .. } => Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                format!(
                    "{} is contextual syntax, not a standalone value expression",
                    super::grammar::construct_name(self.kind(n))
                ),
            )),
        }
    }
    /// Collect concrete type evidence without evaluating operands or emitting
    /// operations. Literal constraints can flow through nested expression shapes.
    fn known_type(&self, n: ast::NodeId) -> Option<TypeId> {
        match self.kind(n) {
            NodeKind::Path { segments, .. } => {
                let symbol = self.path_symbol(n, segments).ok()?;
                match self.p.symbols.entries[symbol.0 as usize].definition {
                    SymbolDefinition::Binding(b) => Some(self.p.scopes.bindings[b.0 as usize].ty),
                    SymbolDefinition::Constant(c) => {
                        Some(self.p.declarations.constants[c.0 as usize].ty)
                    }
                    _ => None,
                }
            }
            NodeKind::Parenthesized { expression } => self.known_type(*expression),
            NodeKind::Block {
                result: Some(result),
                ..
            } => self.known_type(*result),
            NodeKind::Binary {
                operator,
                left,
                right,
            } => {
                if matches!(
                    self.text(*operator),
                    "==" | "!=" | "<" | "<=" | ">" | ">=" | "&&" | "||"
                ) {
                    Some(self.boolean)
                } else {
                    self.known_type(*left).or_else(|| self.known_type(*right))
                }
            }
            NodeKind::Unary {
                operator, operand, ..
            } => {
                let ty = self.known_type(*operand)?;
                match self.text(*operator) {
                    "*" => match self.p.types.entries[ty.0 as usize].kind {
                        TypeDefinition::Reference { target, .. } => Some(target),
                        TypeDefinition::Allocation { content } => Some(content),
                        _ => None,
                    },
                    "-" | "~" => Some(ty),
                    "!" => Some(self.boolean),
                    _ => None,
                }
            }
            NodeKind::Conversion { ty, .. } => {
                let NodeKind::Type(TypeSyntax::Path {
                    segments,
                    arguments,
                }) = self.kind(*ty)
                else {
                    return None;
                };
                if !arguments.is_empty() {
                    return None;
                }
                let symbol = self.scoped_path(*ty, self.ctx().scope, segments).ok()?;
                match self.p.symbols.entries[symbol.0 as usize].definition {
                    SymbolDefinition::Type(ty) => Some(ty),
                    _ => None,
                }
            }
            NodeKind::Projection { base, member } => {
                let mut ty = self.known_type(*base)?;
                while let TypeDefinition::Reference { target, .. } =
                    self.p.types.entries[ty.0 as usize].kind
                {
                    ty = target;
                }
                let name = self.text(*member);
                if let TypeDefinition::Tuple(parts) = &self.p.types.entries[ty.0 as usize].kind {
                    return parts.get(name.parse::<usize>().ok()?).copied();
                }
                self.p
                    .declarations
                    .structs
                    .iter()
                    .find(|s| s.ty == ty)?
                    .fields
                    .iter()
                    .find_map(|id| {
                        let field = &self.p.declarations.fields[id.0 as usize];
                        (self.p.symbols.entries[field.symbol.0 as usize].spelling == name)
                            .then_some(field.ty)
                    })
            }
            NodeKind::Index { base, index }
                if !matches!(self.kind(*index), NodeKind::Range { .. }) =>
            {
                let mut ty = self.known_type(*base)?;
                while let TypeDefinition::Reference { target, .. } =
                    self.p.types.entries[ty.0 as usize].kind
                {
                    ty = target;
                }
                match self.p.types.entries[ty.0 as usize].kind {
                    TypeDefinition::Array { element, .. }
                    | TypeDefinition::Slice { element }
                    | TypeDefinition::GrowingSequence { element } => Some(element),
                    _ => None,
                }
            }
            _ => None,
        }
    }
    fn is_place_syntax(&self, n: ast::NodeId) -> bool {
        match self.kind(n) {
            NodeKind::Path { .. } | NodeKind::Projection { .. } | NodeKind::Index { .. } => true,
            NodeKind::Parenthesized { expression } => self.is_place_syntax(*expression),
            NodeKind::Unary { operator, .. } => self.text(*operator) == "*",
            _ => false,
        }
    }
    fn place_expression(&mut self, n: ast::NodeId) -> Result<EvaluatedPlaceId> {
        self.place_with_permission(n, false)
    }
    fn place_with_permission(&mut self, n: ast::NodeId, mutable: bool) -> Result<EvaluatedPlaceId> {
        match self.kind(n) {
            NodeKind::Path { segments, .. } if segments.len() == 1 => {
                let name = self.text(segments[0]);
                let symbol = self.lookup(self.ctx().scope, name).ok_or_else(|| {
                    self.fail(
                        n,
                        DiagnosticKind::UnresolvedName,
                        format!("cannot resolve place '{name}'"),
                    )
                })?;
                let SymbolDefinition::Binding(binding) =
                    self.p.symbols.entries[symbol.0 as usize].definition
                else {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "expression is not an addressable binding",
                    ));
                };
                let ty = self.p.scopes.bindings[binding.0 as usize].ty;
                let place = self.place(PlaceRoot::Binding(binding), vec![], ty);
                Ok(self.evaluated_place(n, place, vec![]))
            }
            NodeKind::Parenthesized { expression } => {
                self.place_with_permission(*expression, mutable)
            }
            NodeKind::Unary {
                operator, operand, ..
            } if self.text(*operator) == "*" => {
                // Dereference reads a reference descriptor; it does not move it.
                let (value, access) = if self.is_place_syntax(*operand) {
                    let place = self.place_with_permission(*operand, mutable)?;
                    let definition = self.p.objects.evaluated_places[place.0 as usize].definition;
                    let ty = self.p.objects.places[definition.0 as usize].ty;
                    if let TypeDefinition::Allocation { content } =
                        self.p.types.entries[ty.0 as usize].kind
                    {
                        let value = self.read_place(*operand, place)?.value;
                        let target = self.place(
                            PlaceRoot::Value(value),
                            vec![PlaceProjection::AllocationContent],
                            content,
                        );
                        let site = self.site(n, ExecutionPhase::Evaluate);
                        let result = EvaluatedPlaceId(self.p.objects.evaluated_places.len() as u32);
                        self.p.objects.evaluated_places.push(EvaluatedPlace {
                            id: result,
                            definition: target,
                            produced_by: site.id,
                            selectors: vec![],
                        });
                        let effects = self.effects(&site, vec![]);
                        self.emit(Operation::Dereference(Dereference {
                            site,
                            source: value,
                            access: ResolvedDereference::NativeAllocation,
                            result,
                            effects,
                        }));
                        return Ok(result);
                    }
                    if matches!(
                        self.p.types.entries[ty.0 as usize].kind,
                        TypeDefinition::Reference { .. }
                    ) {
                        (
                            self.read_place(*operand, place)?.value,
                            ResolvedDereference::NativeReference,
                        )
                    } else {
                        self.dereference_method(n, place, mutable)?
                    }
                } else {
                    let value = self.expression(*operand, None)?.value;
                    (value, ResolvedDereference::NativeReference)
                };
                let ty = self.vtype(value);
                let TypeDefinition::Reference { target, .. } =
                    self.p.types.entries[ty.0 as usize].kind
                else {
                    return Err(self.fail(n, DiagnosticKind::InvalidType,
                        "dereference requires a reference or a ref()/mut_ref() method returning one"));
                };
                let reference = *self.references.get(&value).ok_or_else(|| {
                    self.fail(
                        n,
                        DiagnosticKind::IncompleteRepresentation,
                        "reference origin missing",
                    )
                })?;
                let place = self.place(PlaceRoot::Reference(reference), vec![], target);
                let site = self.site(n, ExecutionPhase::Evaluate);
                let result = EvaluatedPlaceId(self.p.objects.evaluated_places.len() as u32);
                self.p.objects.evaluated_places.push(EvaluatedPlace {
                    id: result,
                    definition: place,
                    produced_by: site.id,
                    selectors: vec![],
                });
                let effects = self.effects(&site, vec![]);
                self.emit(Operation::Dereference(Dereference {
                    site,
                    effects,
                    source: value,
                    access,
                    result,
                }));
                Ok(result)
            }
            NodeKind::Projection { base, member } => {
                let base = self.place_with_permission(*base, mutable)?;
                let base = self.deref_place(n, base)?;
                let definition = self.p.objects.evaluated_places[base.0 as usize].definition;
                let p = self.p.objects.places[definition.0 as usize].clone();
                let name = self.text(*member);
                let (projection, ty, field) = if let TypeDefinition::Tuple(elements) =
                    &self.p.types.entries[p.ty.0 as usize].kind
                {
                    let index = name.parse::<usize>().map_err(|_| {
                        self.fail(
                            n,
                            DiagnosticKind::InvalidType,
                            "tuple projection requires an integer field",
                        )
                    })?;
                    let ty = *elements.get(index).ok_or_else(|| {
                        self.fail(n, DiagnosticKind::InvalidType, "tuple field does not exist")
                    })?;
                    (PlaceProjection::TupleElement(index as u32), ty, None)
                } else {
                    let fields = self.fields(p.ty, n)?;
                    let field = fields
                        .into_iter()
                        .find(|f| {
                            self.p.symbols.entries
                                [self.p.declarations.fields[f.0 as usize].symbol.0 as usize]
                                .spelling
                                == name
                        })
                        .ok_or_else(|| {
                            self.fail(
                                n,
                                DiagnosticKind::UnresolvedName,
                                format!("type {} has no field '{name}'", self.type_name(p.ty)),
                            )
                        })?;
                    if !self.visible_from(
                        self.p.declarations.fields[field.0 as usize].symbol,
                        self.ctx().scope,
                    ) {
                        return Err(self.fail(
                            n,
                            DiagnosticKind::UnresolvedName,
                            "field is private to its declaring module",
                        ));
                    }
                    (
                        PlaceProjection::Field(field),
                        self.p.declarations.fields[field.0 as usize].ty,
                        Some(field),
                    )
                };
                let mut projections = p.projections;
                projections.push(projection);
                let place = self.place(p.root, projections, ty);
                let site = self.site(n, ExecutionPhase::Evaluate);
                let result = EvaluatedPlaceId(self.p.objects.evaluated_places.len() as u32);
                self.p.objects.evaluated_places.push(EvaluatedPlace {
                    id: result,
                    definition: place,
                    produced_by: site.id,
                    selectors: vec![],
                });
                if let Some(field) = field {
                    self.emit(Operation::ProjectField(ProjectField {
                        site,
                        base,
                        field,
                        result,
                    }));
                } else {
                    self.emit(Operation::ProjectTupleField(ProjectTupleField {
                        site,
                        base,
                        position: name.parse().unwrap(),
                        result,
                    }));
                }
                Ok(result)
            }
            NodeKind::Index { base, index } => {
                if matches!(self.kind(*index), NodeKind::Range { .. }) {
                    return self.slice_place(n, *base, *index);
                }
                let base = self.place_with_permission(*base, mutable)?;
                let base = self.deref_place(n, base)?;
                let definition = self.p.objects.evaluated_places[base.0 as usize].definition;
                let p = self.p.objects.places[definition.0 as usize].clone();
                let (element, length) = self.sequence_info(n, base)?;
                let index_node = *index;
                let index = self.expression(index_node, None)?.value;
                self.require_integer(index_node, index)?;
                let mut projections = p.projections;
                projections.push(PlaceProjection::Index(index));
                let place = self.place(p.root, projections, element);
                let site = self.site(n, ExecutionPhase::Evaluate);
                let result = EvaluatedPlaceId(self.p.objects.evaluated_places.len() as u32);
                self.p.objects.evaluated_places.push(EvaluatedPlace {
                    id: result,
                    definition: place,
                    produced_by: site.id,
                    selectors: vec![index],
                });
                let check = CheckId(self.p.runtime_checks.len() as u32);
                self.p
                    .runtime_checks
                    .push(RuntimeCheck::IndexBounds(IndexBoundsCheck {
                        id: check,
                        index,
                        length,
                    }));
                self.emit(Operation::IndexPlace(IndexPlace {
                    site,
                    access: ResolvedIndexAccess::Contiguous { element },
                    base,
                    index,
                    result,
                    check,
                }));
                Ok(result)
            }
            _ => {
                let value = self.expression(n, None)?.value;
                let site = self.site(n, ExecutionPhase::Receive);
                self.materialize_value(
                    value,
                    Owner::Scope {
                        scope: site.scope,
                        instance: self.ctx().domain,
                    },
                    &site,
                );
                let place = self.place(PlaceRoot::Value(value), vec![], self.vtype(value));
                let result = EvaluatedPlaceId(self.p.objects.evaluated_places.len() as u32);
                self.p.objects.evaluated_places.push(EvaluatedPlace {
                    id: result,
                    definition: place,
                    produced_by: site.id,
                    selectors: vec![],
                });
                self.emit(Operation::EvaluatePlace(EvaluatePlace {
                    site,
                    place,
                    result,
                }));
                Ok(result)
            }
        }
    }
    fn fields(&mut self, ty: TypeId, n: ast::NodeId) -> Result<Vec<FieldId>> {
        self.ensure_nominal(ty, n)?;
        self.p
            .declarations
            .structs
            .iter()
            .find(|s| s.ty == ty)
            .map(|s| s.fields.clone())
            .ok_or_else(|| {
                self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    format!("{} does not have struct fields", self.type_name(ty)),
                )
            })
    }
    fn deref_place(
        &mut self,
        n: ast::NodeId,
        mut place: EvaluatedPlaceId,
    ) -> Result<EvaluatedPlaceId> {
        loop {
            let definition = self.p.objects.evaluated_places[place.0 as usize].definition;
            let old = self.p.objects.places[definition.0 as usize].clone();
            if let TypeDefinition::Reference { target, .. } =
                self.p.types.entries[old.ty.0 as usize].kind
            {
                let mut projections = old.projections;
                projections.push(PlaceProjection::Dereference);
                let id = self.place(old.root, projections, target);
                place = self.evaluated_place(n, id, vec![]);
            } else if let TypeDefinition::Allocation { content } =
                self.p.types.entries[old.ty.0 as usize].kind
            {
                let mut projections = old.projections;
                projections.push(PlaceProjection::AllocationContent);
                let id = self.place(old.root, projections, content);
                place = self.evaluated_place(n, id, vec![]);
            } else {
                return Ok(place);
            }
        }
    }
    fn read_place(&mut self, n: ast::NodeId, place: EvaluatedPlaceId) -> Result<Expr> {
        let definition = self.p.objects.evaluated_places[place.0 as usize].definition;
        let p = self.p.objects.places[definition.0 as usize].clone();
        self.ensure_nominal(p.ty, n)?;
        if matches!(
            self.p.types.entries[p.ty.0 as usize].kind,
            TypeDefinition::Slice { .. } | TypeDefinition::StrData
        ) {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                "unsized slice data requires an explicit & or &mut borrow",
            ));
        }
        let binding = match p.root {
            PlaceRoot::Binding(b) => Some(b),
            _ => None,
        };
        let base_value = binding.and_then(|b| self.ctx().bindings.get(&b).copied());
        let mut dependencies = base_value.map(|v| self.dependencies(v)).unwrap_or_default();
        if let PlaceRoot::Reference(r) = p.root {
            dependencies.extend(
                std::iter::once(self.p.objects.references[r.0 as usize].origins.first.target)
                    .chain(
                        self.p.objects.references[r.0 as usize]
                            .origins
                            .rest
                            .iter()
                            .map(|o| o.target),
                    )
                    .map(DependencyRequirement::LiveTarget),
            );
        }
        let site = self.site(n, ExecutionPhase::Read);
        let result = self.op_value(
            &site,
            p.ty,
            if self.primitive(p.ty) || self.enum_copy(p.ty) {
                dependencies
                    .into_iter()
                    .filter_map(Self::primitive_requirement)
                    .collect()
            } else {
                dependencies
            },
        );
        let effects = self.effects(&site, vec![Effect::Read(ReadEffect { place: definition })]);
        self.emit(Operation::ReadValue(ReadValue {
            site: site.clone(),
            source: place,
            result,
            effects,
        }));
        if let PlaceRoot::Reference(reference) = p.root {
            self.lifetime_uses.push(EntityUseMoment {
                entity: EntityOccurrence {
                    entity: EntityId::Reference(reference),
                    instance: self.ctx().domain,
                },
                at: MomentOccurrence {
                    moment: site.execution_moments.first,
                    context: self.ctx().domain,
                },
                guard: site.guard,
                access: AccessKind::Read,
            });
        }
        if let Some(binding) = binding {
            if let Some(entity) = self.binding_entities.get(&binding).cloned() {
                self.lifetime_uses.push(EntityUseMoment {
                    entity: EntityOccurrence {
                        entity: entity.clone(),
                        instance: self.ctx().domain,
                    },
                    at: MomentOccurrence {
                        moment: site.execution_moments.first,
                        context: self.ctx().domain,
                    },
                    guard: site.guard,
                    access: AccessKind::Read,
                });
                if p.projections.is_empty() && !(self.primitive(p.ty) || self.enum_copy(p.ty)) {
                    self.value_entities.insert(result, entity);
                    if let Some(old) = base_value {
                        if let Some(reference) = self.references.get(&old).copied() {
                            self.references.insert(result, reference);
                        }
                    }
                }
            }
            let obligation = self.obligation_site(&site);
            self.p.obligations.n6.push(PathValidityObligation {
                site: obligation,
                requirement: PathValidityRequirement::BindingAvailable { binding },
            });
        }
        let provenance = self.p.values.entries[result.0 as usize].provenance;
        self.p.values.provenance[provenance.0 as usize].kind = ProvenanceKind::PlaceRead {
            place,
            root_value: base_value.or_else(|| match p.root {
                PlaceRoot::Value(value) => Some(value),
                _ => None,
            }),
            operation: site.id,
        };
        if let Some(source) = base_value.filter(|_| p.projections.is_empty()) {
            let provenance = self.p.values.entries[result.0 as usize].provenance;
            self.p.values.provenance[provenance.0 as usize].kind =
                if self.primitive(p.ty) || self.enum_copy(p.ty) {
                    ProvenanceKind::Copy {
                        source,
                        operation: site.id,
                    }
                } else {
                    ProvenanceKind::Forward {
                        source,
                        operation: site.id,
                    }
                };
            if !(self.primitive(p.ty) || self.enum_copy(p.ty)) {
                self.p.values.entries[result.0 as usize].dependencies =
                    self.p.values.entries[source.0 as usize].dependencies;
            }
        }
        if !(self.primitive(p.ty) || self.enum_copy(p.ty)) {
            let summary = self.p.values.entries[result.0 as usize].dependencies;
            self.p.values.dependency_summaries[summary.0 as usize]
                .dependencies
                .push(DependencyRequirement::CarriedByPlace {
                    place,
                    at: site.execution_moments.first,
                });
        }
        if !self.references.contains_key(&result) {
            if let TypeDefinition::Reference { target, permission } =
                self.p.types.entries[p.ty.0 as usize].kind.clone()
            {
                let mut projections = p.projections;
                projections.push(PlaceProjection::Dereference);
                let target = self.place(p.root, projections, target);
                let reference = ReferenceId(self.p.objects.references.len() as u32);
                self.p.objects.references.push(Reference {
                    id: reference,
                    ty: p.ty,
                    created_in: site.scope,
                    creation: ObjectCreation::At(site.execution_moments.first),
                    initial_owner: Owner::Scope {
                        scope: site.scope,
                        instance: self.ctx().domain,
                    },
                    permission,
                    formation: ReferenceFormation::Loan,
                    origins: NonEmpty {
                        first: ReferenceOrigin {
                            target,
                            parent: None,
                            guard: site.guard,
                        },
                        rest: vec![],
                    },
                });
                self.references.insert(result, reference);
                self.value_entities
                    .insert(result, EntityId::Reference(reference));
            }
        }
        Ok(Expr { value: result })
    }
    fn load(&mut self, n: ast::NodeId, place: EvaluatedPlaceId) -> Result<Expr> {
        let result = self.read_place(n, place)?.value;
        let definition = self.p.objects.evaluated_places[place.0 as usize].definition;
        let p = self.p.objects.places[definition.0 as usize].clone();
        if matches!(self.transfer_kind(p.ty), TransferKind::ByTypeParameter(_)) {
            return self.parametric_transfer(n, place, result, p.ty);
        }
        let result = if self.implicit_copy(p.ty) {
            let copy = self.site(n, ExecutionPhase::Compute);
            let copied = self.op_value(
                &copy,
                p.ty,
                if self.shared_reference(p.ty) {
                    self.dependencies(result)
                } else {
                    self.primitive_constraints(result)
                },
            );
            if self.enum_copy(p.ty) {
                self.emit(Operation::CopyEligibleEnum(CopyEligibleEnum {
                    site: copy.clone(),
                    source: result,
                    result: copied,
                }));
            } else {
                self.emit(Operation::CopyPrimitive(CopyPrimitive {
                    site: copy.clone(),
                    source: result,
                    result: copied,
                }));
            }
            if self.shared_reference(p.ty) {
                self.forward_summaries(result, copied);
                self.clone_reference_identity(result, copied, &copy);
            }
            copied
        } else {
            let moving = self.site(n, ExecutionPhase::Receive);
            let moved = self.op_value(&moving, p.ty, vec![]);
            self.forward_summaries(result, moved);
            let provenance = self.p.values.entries[moved.0 as usize].provenance;
            self.p.values.provenance[provenance.0 as usize].kind = ProvenanceKind::Move {
                source: result,
                operation: moving.id,
            };
            if let Some(entity) = self.value_entities.get(&result).cloned() {
                self.value_entities.insert(moved, entity);
            }
            if let Some(reference) = self.references.get(&result).copied() {
                self.references.insert(moved, reference);
            }
            let destination = Owner::Scope {
                scope: moving.scope,
                instance: self.ctx().domain,
            };
            self.transfer(moved, destination.clone(), &moving);
            let effects = self.effects(&moving, vec![]);
            self.emit(Operation::MoveValue(MoveValue {
                site: moving,
                source: MoveSource::Place(place),
                result: moved,
                value: result,
                destination,
                effects,
            }));
            moved
        };
        Ok(Expr { value: result })
    }
    fn borrow(&mut self, n: ast::NodeId, place: EvaluatedPlaceId, mutable: bool) -> Result<Expr> {
        let definition = self.p.objects.evaluated_places[place.0 as usize].definition;
        let target = self.p.objects.places[definition.0 as usize].ty;
        let ty = self.intern(TypeKey::Reference(mutable, target));
        let site = self.site(n, ExecutionPhase::Compute);
        let reference = ReferenceId(self.p.objects.references.len() as u32);
        let result = self.op_value(
            &site,
            ty,
            vec![DependencyRequirement::LiveTarget(definition)],
        );
        let entity = EntityId::Reference(reference);
        let owner = Owner::Scope {
            scope: site.scope,
            instance: self.ctx().domain,
        };
        let parent = match self.p.objects.places[definition.0 as usize].root {
            PlaceRoot::Reference(r) => Some(r),
            _ => None,
        };
        self.p.objects.references.push(Reference {
            creation: ObjectCreation::At(site.execution_moments.first),
            id: reference,
            created_in: site.scope,
            initial_owner: owner.clone(),
            ty,
            permission: if mutable {
                ReferencePermission::Mutable
            } else {
                ReferencePermission::Shared
            },
            formation: ReferenceFormation::Loan,
            origins: NonEmpty {
                first: ReferenceOrigin {
                    target: definition,
                    parent,
                    guard: site.guard,
                },
                rest: vec![],
            },
        });
        let dependency = DependencyLinkId(self.p.objects.dependencies.len() as u32);
        self.p.objects.dependencies.push(DependencyLink {
            id: dependency,
            dependent: entity.clone(),
            requirement: DependencyRequirement::LiveTarget(definition),
            established: site.execution_moments.first,
            guard: site.guard,
        });
        self.references.insert(result, reference);
        self.value_entities.insert(result, entity.clone());
        self.p.objects.ownership.push(OwnershipLink {
            entity: entity.clone(),
            owner,
            scope: site.scope,
            established: site.execution_moments.first,
            guard: site.guard,
        });
        if let PlaceRoot::Binding(binding) = self.p.objects.places[definition.0 as usize].root {
            let obligation = self.obligation_site(&site);
            self.p.obligations.n6.push(PathValidityObligation {
                site: obligation,
                requirement: PathValidityRequirement::BindingAvailable { binding },
            });
        }
        let slice = self
            .p
            .bodies
            .iter()
            .flat_map(|b| &b.operations)
            .find_map(|o| match o {
                Operation::SlicePlace(s) if s.result == place => Some(s.clone()),
                _ => None,
            });
        if let Some(slice) = slice {
            let mut checks = vec![slice.check];
            if matches!(
                self.p.types.entries[target.0 as usize].kind,
                TypeDefinition::StrData
            ) {
                for boundary in [slice.start, slice.end] {
                    let id = CheckId(self.p.runtime_checks.len() as u32);
                    self.p
                        .runtime_checks
                        .push(RuntimeCheck::Utf8Boundary(Utf8BoundaryCheck {
                            id,
                            source: slice.base,
                            boundary,
                        }));
                    checks.push(id);
                }
            }
            self.emit(Operation::SliceView(SliceView {
                site,
                reference,
                access: ResolvedSliceAccess::Contiguous {
                    element: slice.element,
                },
                base: slice.base,
                start: slice.start,
                end: slice.end,
                permission: if mutable {
                    ReferencePermission::Mutable
                } else {
                    ReferencePermission::Shared
                },
                result,
                checks,
            }));
        } else if mutable {
            self.emit(Operation::BorrowMutable(BorrowMutable {
                site,
                source: place,
                reference,
                result,
            }));
        } else {
            self.emit(Operation::BorrowShared(BorrowShared {
                site,
                source: place,
                reference,
                result,
            }));
        }
        Ok(Expr { value: result })
    }
    fn obligation_site(&self, site: &OperationSite) -> ObligationSite {
        let count = self.p.obligations.n1.len()
            + self.p.obligations.n2.len()
            + self.p.obligations.n3.len()
            + self.p.obligations.n4.len()
            + self.p.obligations.n5.len()
            + self.p.obligations.n6.len()
            + self.p.obligations.n7.len()
            + self.p.obligations.n8.len();
        ObligationSite {
            id: ObligationId(count as u32),
            operation: site.id,
            moment: site.execution_moments.first,
            guard: site.guard,
            origin: site.origin,
        }
    }
    fn obligation_site_at(&self, moment: ExecutionMomentId) -> ObligationSite {
        let event = &self.p.execution.execution_moments[moment.0 as usize];
        let operation = self.p.bodies[event.body.0 as usize]
            .operations
            .iter()
            .find(|operation| operation.site().id == event.operation)
            .expect("execution moment must retain its semantic operation");
        let mut site = self.obligation_site(operation.site());
        site.moment = moment;
        site
    }
    fn populate_ownership_and_cleanup_obligations(
        &mut self,
        cleanup_candidates: &[CleanupCandidate],
    ) {
        for (index, ownership) in self.p.objects.ownership.clone().into_iter().enumerate() {
            let site = self.obligation_site_at(ownership.established);
            self.p.obligations.n2.push(UniqueCleanupOwnerObligation {
                site,
                link: OwnershipLinkId(index as u32),
                entity: ownership.entity,
            });
        }
        for candidate in cleanup_candidates {
            let event = self.p.scopes.exits[candidate.exit.0 as usize].event;
            let storage = match candidate.entity.entity {
                EntityId::Address(address) => {
                    Some(self.p.objects.addresses[address.0 as usize].storage)
                }
                EntityId::Collection(collection) => {
                    match self.p.objects.collections[collection.0 as usize].descriptor {
                        CollectionDescriptor::Address(address) => {
                            Some(self.p.objects.addresses[address.0 as usize].storage)
                        }
                        CollectionDescriptor::Place(_) => None,
                    }
                }
                EntityId::Reference(_) => None,
            };
            let site = self.obligation_site_at(event);
            self.p.obligations.n7.push(DestructionObligation {
                site,
                requirement: DestructionRequirement::CleanupCandidate {
                    candidate: candidate.id,
                    subject: DestructionSubject::Entity(candidate.entity.entity.clone()),
                    storage,
                },
            });
        }
        let drops = self
            .p
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .filter_map(|operation| match operation {
                Operation::DropValue(drop) => Some(drop.clone()),
                _ => None,
            })
            .collect::<Vec<_>>();
        for drop in drops {
            let subject = self
                .value_entities
                .get(&drop.value)
                .cloned()
                .map(DestructionSubject::Entity)
                .unwrap_or(DestructionSubject::Value(drop.value));
            let storage = match &subject {
                DestructionSubject::Entity(EntityId::Address(address)) => {
                    Some(self.p.objects.addresses[address.0 as usize].storage)
                }
                _ => None,
            };
            let site = self.obligation_site(&drop.site);
            self.p.obligations.n7.push(DestructionObligation {
                site,
                requirement: DestructionRequirement::ExplicitDrop {
                    value: drop.value,
                    destructor: drop.destructor,
                    subject,
                    storage,
                },
            });
        }

        let destructor_contracts = self
            .p
            .contracts
            .destructors
            .iter()
            .filter_map(|destructor| {
                let hook = &self.p.declarations.instances[destructor.hook.0 as usize];
                let body = hook.body?;
                let operation = self.p.bodies[body.0 as usize].operations.first()?;
                Some((operation.site().clone(), destructor.id))
            })
            .collect::<Vec<_>>();
        for (site, destructor) in destructor_contracts {
            let site = self.obligation_site(&site);
            self.p.obligations.n7.push(DestructionObligation {
                site,
                requirement: DestructionRequirement::DestructorContract { destructor },
            });
        }

        let reserved_calls = self
            .p
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .filter_map(|operation| {
                let function = match operation {
                    Operation::DirectCall(call) => Some(call.target),
                    Operation::ExternalCall(call) => Some(call.target.function),
                    Operation::MethodCall(call) => match call.target.target {
                        MethodTarget::Concrete(function) => Some(function),
                        _ => None,
                    },
                    _ => None,
                }?;
                let instance = &self.p.declarations.instances[function.0 as usize];
                let destructor = self.p.contracts.destructors.iter().find(|destructor| {
                    self.p.declarations.instances[destructor.hook.0 as usize].definition
                        == instance.definition
                })?;
                Some((operation.site().clone(), destructor.id))
            })
            .collect::<Vec<_>>();
        for (site, destructor) in reserved_calls {
            let call = site.id;
            let site = self.obligation_site(&site);
            self.p.obligations.n7.push(DestructionObligation {
                site,
                requirement: DestructionRequirement::ReservedDestructorCall { call, destructor },
            });
        }

        let partial_moves = self
            .p
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .filter_map(|operation| {
                let (source, transfer) = match operation {
                    Operation::ExtractVariantField(extraction) => {
                        (extraction.source, extraction.transfer.clone())
                    }
                    Operation::ExtractTupleField(extraction) => {
                        (extraction.source, extraction.transfer.clone())
                    }
                    _ => return None,
                };
                matches!(
                    transfer,
                    TransferKind::Move | TransferKind::ByTypeParameter(_)
                )
                .then(|| (operation.site().clone(), source, transfer))
            })
            .collect::<Vec<_>>();
        for (site, source, transfer) in partial_moves {
            let site = self.obligation_site(&site);
            self.p.obligations.n7.push(DestructionObligation {
                site,
                requirement: DestructionRequirement::PartialMoveCleanup { source, transfer },
            });
        }
    }

    /// Declare N1 applicability from the canonical type derivation attached to
    /// every operation-produced value. The checker compares resolved TypeIds;
    /// it never reconstructs inference from source syntax.
    fn populate_operation_type_obligations(&mut self) {
        fn operation_has_check(operation: &Operation, id: CheckId) -> bool {
            macro_rules! checks {
                ($operation:expr) => {
                    $operation.checks.contains(&id)
                };
            }
            match operation {
                Operation::IndexPlace(operation) => operation.check == id,
                Operation::SlicePlace(operation) => operation.check == id,
                Operation::NumericCast(operation) => operation.check == id,
                Operation::RuntimeCheckOperation(operation) => operation.requirement == id,
                Operation::UnwrapResult(operation) => operation.check == id,
                Operation::UnwrapOption(operation) => operation.check == id,
                Operation::Add(operation) => checks!(operation),
                Operation::Subtract(operation) => checks!(operation),
                Operation::Multiply(operation) => checks!(operation),
                Operation::Divide(operation) => checks!(operation),
                Operation::Remainder(operation) => checks!(operation),
                Operation::ShiftLeft(operation) => checks!(operation),
                Operation::ShiftRight(operation) => checks!(operation),
                Operation::Negate(operation) => checks!(operation),
                Operation::SliceView(operation) => checks!(operation),
                Operation::AddAssign(operation) => checks!(operation),
                Operation::SubtractAssign(operation) => checks!(operation),
                Operation::MultiplyAssign(operation) => checks!(operation),
                Operation::DivideAssign(operation) => checks!(operation),
                Operation::RemainderAssign(operation) => checks!(operation),
                Operation::ShiftLeftAssign(operation) => checks!(operation),
                Operation::ShiftRightAssign(operation) => checks!(operation),
                Operation::GrowStorage(operation) => operation.check == id,
                Operation::AllocatePoolSlot(operation) => operation.check == id,
                _ => false,
            }
        }
        let sites = self
            .p
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .map(|operation| (operation.site().id, operation.site().clone()))
            .collect::<HashMap<_, _>>();
        let derivations = self.type_derivations.clone();
        for derivation in derivations {
            let TypeDerivationReason::Operation(operation) = derivation.reason else {
                continue;
            };
            let Some(site) = sites.get(&operation) else {
                continue;
            };
            let actual = self.p.values.entries[derivation.value.0 as usize].ty;
            let obligation = self.obligation_site(site);
            self.p.obligations.n1.push(InitializationAndTypeObligation {
                site: obligation,
                requirement: InitializationAndTypeRequirement::TypeIdentity {
                    value: derivation.value,
                    expected: derivation.resolved,
                    actual,
                },
            });
        }
        let operations = self
            .p
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .cloned()
            .collect::<Vec<_>>();
        let mut declared = self
            .p
            .obligations
            .n1
            .iter()
            .filter_map(|obligation| match obligation.requirement {
                InitializationAndTypeRequirement::TypeIdentity {
                    value,
                    expected,
                    actual,
                } => Some((obligation.site.operation, value, expected, actual)),
                InitializationAndTypeRequirement::RuntimeCheck { .. } => None,
            })
            .collect::<HashSet<_>>();
        for operation in &operations {
            let mut identities = vec![];
            match operation {
                Operation::InitializeBinding(operation) => identities.push((
                    operation.value,
                    self.p.scopes.bindings[operation.binding.0 as usize].ty,
                    self.p.values.entries[operation.value.0 as usize].ty,
                )),
                Operation::ReceiveValue(operation) => identities.push((
                    operation.result,
                    self.p.scopes.bindings[operation.receiver.0 as usize].ty,
                    self.p.values.entries[operation.result.0 as usize].ty,
                )),
                Operation::DirectCall(_) | Operation::ExternalCall(_) => {
                    let (target, arguments, result) = match operation {
                        Operation::DirectCall(call) => (call.target, &call.arguments, call.result),
                        Operation::ExternalCall(call) => {
                            (call.target.function, &call.arguments, call.result)
                        }
                        _ => unreachable!(),
                    };
                    let signature = self.p.declarations.instances[target.0 as usize].signature;
                    let signature = &self.p.declarations.signatures[signature.0 as usize];
                    for argument in arguments {
                        if let Some(parameter) =
                            signature.parameters.get(argument.parameter_index as usize)
                        {
                            identities.push((
                                argument.value,
                                parameter.ty,
                                self.p.values.entries[argument.value.0 as usize].ty,
                            ));
                        }
                    }
                    if matches!(signature.execution, FunctionExecution::Synchronous) {
                        identities.push((
                            result,
                            signature.result,
                            self.p.values.entries[result.0 as usize].ty,
                        ));
                    }
                }
                Operation::MethodCall(call) => {
                    if let MethodTarget::Concrete(target) = call.target.target {
                        let signature = self.p.declarations.instances[target.0 as usize].signature;
                        let signature = &self.p.declarations.signatures[signature.0 as usize];
                        for argument in &call.arguments {
                            if let Some(parameter) =
                                signature.parameters.get(argument.parameter_index as usize)
                            {
                                identities.push((
                                    argument.value,
                                    parameter.ty,
                                    self.p.values.entries[argument.value.0 as usize].ty,
                                ));
                            }
                        }
                        if matches!(signature.execution, FunctionExecution::Synchronous) {
                            identities.push((
                                call.result,
                                signature.result,
                                self.p.values.entries[call.result.0 as usize].ty,
                            ));
                        }
                    }
                }
                _ => {}
            }
            for (value, expected, actual) in identities {
                if declared.insert((operation.site().id, value, expected, actual)) {
                    let site = self.obligation_site(operation.site());
                    self.p.obligations.n1.push(InitializationAndTypeObligation {
                        site,
                        requirement: InitializationAndTypeRequirement::TypeIdentity {
                            value,
                            expected,
                            actual,
                        },
                    });
                }
            }
        }
        for check in &self.p.runtime_checks.clone() {
            let id = match check {
                RuntimeCheck::ZeroDivisor(check) => check.id,
                RuntimeCheck::ShiftCount(check) => check.id,
                RuntimeCheck::IndexBounds(check) => check.id,
                RuntimeCheck::SliceBounds(check) => check.id,
                RuntimeCheck::IntegerOverflow(check) => check.id,
                RuntimeCheck::ExactConversion(check) => check.id,
                RuntimeCheck::Utf8Boundary(check) => check.id,
                RuntimeCheck::Capacity(check) => check.id,
                RuntimeCheck::Utf8(check) => check.id,
                RuntimeCheck::Variant(check) => check.id,
                RuntimeCheck::Unwrap(check) => check.id,
                RuntimeCheck::PoolCapacity { id, .. } => *id,
            };
            let Some(operation) = operations
                .iter()
                .find(|operation| operation_has_check(operation, id))
            else {
                continue;
            };
            let site = self.obligation_site(operation.site());
            self.p.obligations.n1.push(InitializationAndTypeObligation {
                site,
                requirement: InitializationAndTypeRequirement::RuntimeCheck { check: id },
            });
        }
    }

    /// Build the canonical inventory of every transfer mode already resolved
    /// in PostAST. N3 obligations reference these exact occurrences; neither
    /// the checker nor later stages walk syntax to rediscover them.
    fn populate_transfer_obligations(&mut self) {
        type Candidate = (
            OperationSite,
            ExecutionMomentId,
            TransferRole,
            TransferSubject,
            TypeId,
            TransferKind,
        );

        fn pattern_candidates(
            pattern: &ResolvedPattern,
            site: &OperationSite,
            bindings: &[Binding],
            out: &mut Vec<Candidate>,
        ) {
            match pattern {
                ResolvedPattern::Binding { binding, transfer } => out.push((
                    site.clone(),
                    site.execution_moments.first,
                    TransferRole::PatternBinding(*binding),
                    TransferSubject::Binding(*binding),
                    bindings[binding.0 as usize].ty,
                    transfer.clone(),
                )),
                ResolvedPattern::Tuple(parts) => {
                    for part in parts {
                        pattern_candidates(part, site, bindings, out);
                    }
                }
                ResolvedPattern::Variant { fields, .. } => {
                    for field in fields {
                        pattern_candidates(&field.pattern, site, bindings, out);
                    }
                }
                ResolvedPattern::Wildcard | ResolvedPattern::Unit => {}
            }
        }

        fn argument_candidates(
            arguments: &[CallArgument],
            site: &OperationSite,
            values: &Values,
            out: &mut Vec<Candidate>,
        ) {
            for argument in arguments {
                out.push((
                    site.clone(),
                    site.execution_moments.first,
                    TransferRole::Argument(argument.parameter_index),
                    TransferSubject::Value(argument.value),
                    values.entries[argument.value.0 as usize].ty,
                    argument.transfer.clone(),
                ));
            }
        }

        fn component_candidates(
            components: &[ComponentInitialization],
            site: &OperationSite,
            values: &Values,
            out: &mut Vec<Candidate>,
        ) {
            for component in components {
                out.push((
                    site.clone(),
                    site.execution_moments.first,
                    TransferRole::Component(component.position.clone()),
                    TransferSubject::Value(component.value),
                    values.entries[component.value.0 as usize].ty,
                    component.transfer.clone(),
                ));
            }
        }

        let mut candidates = vec![];
        for operation in self.p.bodies.iter().flat_map(|body| &body.operations) {
            let site = operation.site().clone();
            let moment = site.execution_moments.first;
            match operation {
                Operation::MoveValue(value) => candidates.push((
                    site,
                    moment,
                    TransferRole::Operation,
                    TransferSubject::Value(value.value),
                    self.p.values.entries[value.value.0 as usize].ty,
                    TransferKind::Move,
                )),
                Operation::CopyPrimitive(value) => candidates.push((
                    site,
                    moment,
                    TransferRole::Operation,
                    TransferSubject::Value(value.source),
                    self.p.values.entries[value.source.0 as usize].ty,
                    TransferKind::PrimitiveCopy,
                )),
                Operation::CopyEligibleEnum(value) => candidates.push((
                    site,
                    moment,
                    TransferRole::Operation,
                    TransferSubject::Value(value.source),
                    self.p.values.entries[value.source.0 as usize].ty,
                    TransferKind::EligibleEnumCopy,
                )),
                Operation::ParametricTransfer(value) => candidates.push((
                    site,
                    moment,
                    TransferRole::Operation,
                    TransferSubject::Value(value.value),
                    value.ty,
                    TransferKind::ByTypeParameter(value.ty),
                )),
                Operation::DirectCall(call) => {
                    argument_candidates(&call.arguments, &site, &self.p.values, &mut candidates)
                }
                Operation::MethodCall(call) => {
                    argument_candidates(&call.arguments, &site, &self.p.values, &mut candidates)
                }
                Operation::ExternalCall(call) => {
                    argument_candidates(&call.arguments, &site, &self.p.values, &mut candidates)
                }
                Operation::IntrinsicCall(call) => {
                    argument_candidates(&call.arguments, &site, &self.p.values, &mut candidates)
                }
                Operation::CallableCall(call) => {
                    argument_candidates(&call.arguments, &site, &self.p.values, &mut candidates)
                }
                Operation::NativeOperation(call) => {
                    argument_candidates(&call.arguments, &site, &self.p.values, &mut candidates)
                }
                Operation::CreateFuture(call) => {
                    argument_candidates(&call.arguments, &site, &self.p.values, &mut candidates)
                }
                Operation::CreateContractFuture(call) => {
                    argument_candidates(&call.arguments, &site, &self.p.values, &mut candidates)
                }
                Operation::ConstructStruct(value) => {
                    component_candidates(&value.components, &site, &self.p.values, &mut candidates)
                }
                Operation::ConstructEnum(value) => {
                    component_candidates(&value.components, &site, &self.p.values, &mut candidates)
                }
                Operation::ConstructTuple(value) => {
                    component_candidates(&value.components, &site, &self.p.values, &mut candidates)
                }
                Operation::ConstructArray(value) => {
                    component_candidates(&value.components, &site, &self.p.values, &mut candidates)
                }
                Operation::ExtractTupleField(value) => candidates.push((
                    site,
                    moment,
                    TransferRole::ExtractedValue,
                    TransferSubject::Value(value.result),
                    self.p.values.entries[value.result.0 as usize].ty,
                    value.transfer.clone(),
                )),
                Operation::ExtractVariantField(value) => candidates.push((
                    site,
                    moment,
                    TransferRole::ExtractedValue,
                    TransferSubject::Value(value.result),
                    self.p.values.entries[value.result.0 as usize].ty,
                    value.transfer.clone(),
                )),
                Operation::CaptureMove(value) => candidates.push((
                    site,
                    moment,
                    TransferRole::Capture(value.field),
                    TransferSubject::Value(value.value),
                    self.p.values.entries[value.value.0 as usize].ty,
                    TransferKind::Move,
                )),
                Operation::CaptureCopy(value) => {
                    let ty = self.p.values.entries[value.value.0 as usize].ty;
                    candidates.push((
                        site,
                        moment,
                        TransferRole::Capture(value.field),
                        TransferSubject::Value(value.value),
                        ty,
                        self.transfer_kind(ty),
                    ));
                }
                Operation::CaptureParametric(value) => candidates.push((
                    site,
                    moment,
                    TransferRole::Capture(value.field),
                    TransferSubject::Value(value.value),
                    value.ty,
                    TransferKind::ByTypeParameter(value.ty),
                )),
                Operation::IfLetDecision(decision) => pattern_candidates(
                    &decision.pattern,
                    &site,
                    &self.p.scopes.bindings,
                    &mut candidates,
                ),
                Operation::MatchDecision(decision) => {
                    for arm in std::iter::once(&decision.arms.first).chain(&decision.arms.rest) {
                        pattern_candidates(
                            &arm.pattern,
                            &site,
                            &self.p.scopes.bindings,
                            &mut candidates,
                        );
                    }
                }
                Operation::ForControl(control) => {
                    pattern_candidates(
                        &control.pattern,
                        &site,
                        &self.p.scopes.bindings,
                        &mut candidates,
                    );
                    if let ResolvedIteration::FixedArray {
                        element, transfer, ..
                    } = &control.iteration
                    {
                        candidates.push((
                            site,
                            moment,
                            TransferRole::IterationElement,
                            TransferSubject::IterationSource(control.source),
                            *element,
                            transfer.clone(),
                        ));
                    }
                }
                _ => {}
            }
        }

        for (site, moment, role, subject, ty, mode) in candidates {
            let id = TransferOccurrenceId(self.p.transfers.len() as u32);
            self.p.transfers.push(ResolvedTransferOccurrence {
                id,
                operation: site.id,
                moment,
                origin: site.origin,
                role,
                subject: subject.clone(),
                ty,
                mode: mode.clone(),
            });
            let mut obligation = self.obligation_site(&site);
            obligation.moment = moment;
            self.p.obligations.n3.push(TransferAndMutationObligation {
                site: obligation,
                requirement: TransferAndMutationRequirement::Transfer {
                    occurrence: id,
                    subject,
                    ty,
                    mode,
                },
            });
        }

        let repetitions = self
            .p
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .filter_map(|operation| match operation {
                Operation::RepeatArray(repetition) => {
                    Some((repetition.site.clone(), repetition.replication.clone()))
                }
                _ => None,
            })
            .collect::<Vec<_>>();
        for (site, plan) in repetitions {
            let obligation = self.obligation_site(&site);
            self.p.obligations.n3.push(TransferAndMutationObligation {
                site: obligation,
                requirement: TransferAndMutationRequirement::StructuralReplication { plan },
            });
        }
    }

    /// Link every resolved dependency to one exact N4 obligation. Direct
    /// outlives requirements receive a canonical LifetimeRequirement; symbolic
    /// carried dependencies remain explicit links whose preservation is proved
    /// without inventing a concrete target.
    fn populate_lifetime_obligations(&mut self, finals: &[LogicalFinalDestination]) {
        fn subject(
            requirement: &DependencyRequirement,
            instance: InstanceDomainId,
        ) -> Option<LifetimeSubject> {
            match requirement {
                DependencyRequirement::LiveTarget(place) => {
                    Some(LifetimeSubject::Target(PlaceOccurrence {
                        place: *place,
                        instance,
                    }))
                }
                DependencyRequirement::LiveStorage(origin) => {
                    Some(LifetimeSubject::SourceStorage {
                        origin: *origin,
                        instance,
                    })
                }
                DependencyRequirement::LiveReference(reference) => {
                    Some(LifetimeSubject::Reference {
                        reference: *reference,
                        instance,
                    })
                }
                DependencyRequirement::ActiveLock(lock)
                | DependencyRequirement::HoldsLock(lock) => {
                    Some(LifetimeSubject::GuardedLock(*lock))
                }
                DependencyRequirement::ConfinedToUncheckedScope(scope) => {
                    Some(LifetimeSubject::UncheckedBoundary(*scope))
                }
                DependencyRequirement::When { requirement, .. } => subject(requirement, instance),
                _ => None,
            }
        }

        for link in self.p.objects.dependencies.clone() {
            let event = self.p.execution.execution_moments[link.established.0 as usize].clone();
            let requirement = subject(&link.requirement, event.instance).map(|required| {
                let id = LifetimeRequirementId(self.lifetime_requirements.len() as u32);
                self.lifetime_requirements.push(LifetimeRequirement {
                    id,
                    dependent: EntityOccurrence {
                        entity: link.dependent.clone(),
                        instance: event.instance,
                    },
                    required,
                    uses: NonEmpty {
                        first: GuardedMoment {
                            guard: link.guard,
                            moment: link.established,
                        },
                        rest: vec![],
                    },
                    completion: vec![],
                    origin: event.lexical_origin(&self.p),
                });
                id
            });
            let site = self.obligation_site_at(link.established);
            self.p.obligations.n4.push(LifetimeObligation {
                site,
                requirement: LifetimeProofRequirement::DependencyLink {
                    link: link.id,
                    lifetime: requirement,
                },
            });
        }

        let operation_requirements = self
            .p
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .filter_map(|operation| match operation {
                Operation::Assign(assign) => Some((
                    assign.site.clone(),
                    LifetimeProofRequirement::StoredValue {
                        target: assign.target,
                        value: assign.value,
                    },
                )),
                Operation::ReturnControl(returned) => Some((
                    returned.site.clone(),
                    LifetimeProofRequirement::EscapingValue {
                        value: returned.value,
                    },
                )),
                _ => None,
            })
            .collect::<Vec<_>>();
        for (site, requirement) in operation_requirements {
            let obligation = self.obligation_site(&site);
            self.p.obligations.n4.push(LifetimeObligation {
                site: obligation,
                requirement,
            });
        }

        let dependency_uses = self
            .p
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .filter_map(|operation| {
                let (value, source) = match operation {
                    Operation::ReadValue(read) => (Some(read.result), Some(read.source)),
                    Operation::BorrowShared(borrow) => (Some(borrow.result), Some(borrow.source)),
                    Operation::BorrowMutable(borrow) => (Some(borrow.result), Some(borrow.source)),
                    Operation::ReturnControl(returned) => (Some(returned.value), None),
                    _ => return None,
                };
                Some((operation.site().clone(), value, source))
            })
            .collect::<Vec<_>>();
        for (site, value, source) in dependency_uses {
            let obligation = self.obligation_site(&site);
            self.p.obligations.n4.push(LifetimeObligation {
                site: obligation,
                requirement: LifetimeProofRequirement::OperationDependencies {
                    operation: site.id,
                    value,
                    source,
                },
            });
        }

        let operations = self
            .p
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .map(|operation| (operation.site().id, operation))
            .collect::<HashMap<_, _>>();
        let branch_requirements = self
            .p
            .contracts
            .applications
            .iter()
            .filter_map(|application| {
                let ContractApplication::Branch {
                    call, capability, ..
                } = application
                else {
                    return None;
                };
                let operation = operations.get(call).copied()?;
                let Operation::NativeOperation(native) = operation else {
                    return None;
                };
                let NativeOperationKind::RuntimeLaunch { task, .. } = native.kind else {
                    return None;
                };
                Some((native.site.clone(), *call, task, *capability))
            })
            .collect::<Vec<_>>();
        for (site, call, task, capability) in branch_requirements {
            let obligation = self.obligation_site(&site);
            self.p.obligations.n4.push(LifetimeObligation {
                site: obligation,
                requirement: LifetimeProofRequirement::BranchDependencies {
                    call,
                    task,
                    capability,
                },
            });
        }

        for index in 0..self.transfers.len() {
            let transfer = &self.transfers[index];
            let site = self.obligation_site_at(transfer.at);
            self.p.obligations.n4.push(LifetimeObligation {
                site,
                requirement: LifetimeProofRequirement::TransferDestination {
                    transfer: index as u32,
                },
            });
        }

        for destination in finals {
            let definition = &self.p.values.entries[destination.value.0 as usize].definition;
            let moment = match definition {
                ValueDefinition::OperationResult { produced_at, .. }
                | ValueDefinition::ConditionalResult { produced_at, .. } => *produced_at,
                ValueDefinition::Parameter(_)
                | ValueDefinition::Constant(_)
                | ValueDefinition::ConfiguredConstant { .. }
                | ValueDefinition::CaptureField { .. }
                | ValueDefinition::Diverged { .. } => continue,
            };
            let site = self.obligation_site_at(moment);
            self.p.obligations.n4.push(LifetimeObligation {
                site,
                requirement: LifetimeProofRequirement::FinalDestination {
                    destination: destination.id,
                },
            });
        }
    }

    /// Declare one N5 obligation for each distinct resolved place access. Place
    /// identity and access mode are semantic facts; the checker only proves
    /// compatibility between these declared accesses.
    fn populate_access_obligations(&mut self) {
        let snapshots = self
            .p
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .filter_map(|operation| match operation {
                Operation::Assign(assign) => Some(assign.replacement.previous),
                _ => None,
            })
            .collect::<HashSet<_>>();
        let mut accesses = vec![];
        for operation in self.p.bodies.iter().flat_map(|body| &body.operations) {
            let mut add =
                |evaluated: EvaluatedPlaceId, access: AccessKind, moment: ExecutionMomentId| {
                    accesses.push((
                        operation.site().clone(),
                        moment,
                        evaluated,
                        self.p.objects.evaluated_places[evaluated.0 as usize].definition,
                        access,
                    ));
                };
            let first = operation.site().execution_moments.first;
            match operation {
                Operation::ReadValue(read) if !snapshots.contains(&read.result) => {
                    add(read.source, AccessKind::Read, first)
                }
                Operation::BorrowShared(borrow) => {
                    add(borrow.source, AccessKind::SharedBorrow, first)
                }
                Operation::BorrowMutable(borrow) => {
                    add(borrow.source, AccessKind::MutableBorrow, first)
                }
                Operation::ReborrowShared(borrow) => {
                    add(borrow.source, AccessKind::SharedBorrow, first)
                }
                Operation::ReborrowMutable(borrow) => {
                    add(borrow.source, AccessKind::MutableBorrow, first)
                }
                Operation::Assign(assign) => add(assign.target, AccessKind::Write, first),
                Operation::MoveValue(moved) => {
                    if let MoveSource::Place(place) = moved.source {
                        add(place, AccessKind::Move, first);
                    }
                }
                Operation::SliceView(view) => add(
                    view.base,
                    if matches!(view.permission, ReferencePermission::Mutable) {
                        AccessKind::MutableBorrow
                    } else {
                        AccessKind::SharedBorrow
                    },
                    first,
                ),
                Operation::SequenceLength(length) => add(length.source, AccessKind::Read, first),
                Operation::ForeignC(foreign) => {
                    for operand in &foreign.operands {
                        add(
                            operand.place,
                            if matches!(operand.mode, ForeignOperandMode::MutableStorage) {
                                AccessKind::Write
                            } else {
                                AccessKind::Read
                            },
                            first,
                        );
                    }
                    for output in &foreign.outputs {
                        add(output.place, AccessKind::Write, first);
                    }
                }
                Operation::ForeignCpp(foreign) => {
                    for operand in &foreign.operands {
                        add(
                            operand.place,
                            if matches!(operand.mode, ForeignOperandMode::MutableStorage) {
                                AccessKind::Write
                            } else {
                                AccessKind::Read
                            },
                            first,
                        );
                    }
                    for output in &foreign.outputs {
                        add(output.place, AccessKind::Write, first);
                    }
                }
                Operation::ForeignAssembly(foreign) => {
                    for operand in &foreign.operands {
                        add(
                            operand.place,
                            if matches!(operand.mode, ForeignOperandMode::MutableStorage) {
                                AccessKind::Write
                            } else {
                                AccessKind::Read
                            },
                            first,
                        );
                    }
                    for output in &foreign.outputs {
                        add(output.place, AccessKind::Write, first);
                    }
                }
                Operation::AddAssign(assign) => {
                    add(assign.target, AccessKind::Read, assign.phases.read_previous);
                    add(assign.target, AccessKind::Write, assign.phases.write);
                }
                Operation::SubtractAssign(assign) => {
                    add(assign.target, AccessKind::Read, assign.phases.read_previous);
                    add(assign.target, AccessKind::Write, assign.phases.write);
                }
                Operation::MultiplyAssign(assign) => {
                    add(assign.target, AccessKind::Read, assign.phases.read_previous);
                    add(assign.target, AccessKind::Write, assign.phases.write);
                }
                Operation::DivideAssign(assign) => {
                    add(assign.target, AccessKind::Read, assign.phases.read_previous);
                    add(assign.target, AccessKind::Write, assign.phases.write);
                }
                Operation::RemainderAssign(assign) => {
                    add(assign.target, AccessKind::Read, assign.phases.read_previous);
                    add(assign.target, AccessKind::Write, assign.phases.write);
                }
                Operation::BitAndAssign(assign) => {
                    add(assign.target, AccessKind::Read, assign.phases.read_previous);
                    add(assign.target, AccessKind::Write, assign.phases.write);
                }
                Operation::BitOrAssign(assign) => {
                    add(assign.target, AccessKind::Read, assign.phases.read_previous);
                    add(assign.target, AccessKind::Write, assign.phases.write);
                }
                Operation::BitXorAssign(assign) => {
                    add(assign.target, AccessKind::Read, assign.phases.read_previous);
                    add(assign.target, AccessKind::Write, assign.phases.write);
                }
                Operation::ShiftLeftAssign(assign) => {
                    add(assign.target, AccessKind::Read, assign.phases.read_previous);
                    add(assign.target, AccessKind::Write, assign.phases.write);
                }
                Operation::ShiftRightAssign(assign) => {
                    add(assign.target, AccessKind::Read, assign.phases.read_previous);
                    add(assign.target, AccessKind::Write, assign.phases.write);
                }
                _ => {}
            }
        }
        let mut seen = HashSet::new();
        for (site, moment, evaluated, place, access) in accesses {
            if !seen.insert((site.id, place, std::mem::discriminant(&access))) {
                continue;
            }
            if matches!(access, AccessKind::Write | AccessKind::MutableBorrow) {
                let mut obligation = self.obligation_site(&site);
                obligation.moment = moment;
                self.p.obligations.n3.push(TransferAndMutationObligation {
                    site: obligation,
                    requirement: TransferAndMutationRequirement::MutationPermission {
                        target: evaluated,
                        access: access.clone(),
                    },
                });
            }
            let mut obligation = self.obligation_site(&site);
            obligation.moment = moment;
            self.p.obligations.n5.push(AccessCompatibilityObligation {
                site: obligation,
                requirement: AccessCompatibilityRequirement::PlaceAccess {
                    place,
                    access,
                    lock: None,
                },
            });
        }

        let lock_acquisitions = self
            .p
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .filter_map(|operation| {
                let function = match operation {
                    Operation::DirectCall(call) => Some(call.target),
                    Operation::ExternalCall(call) => Some(call.target.function),
                    Operation::MethodCall(call) => match call.target.target {
                        MethodTarget::Concrete(function) => Some(function),
                        _ => None,
                    },
                    _ => None,
                }?;
                let instance = &self.p.declarations.instances[function.0 as usize];
                let contracts = instance
                    .contracts
                    .iter()
                    .filter_map(|contract| match contract {
                        ResolvedContract::Lock(contract) => Some(*contract),
                        _ => None,
                    })
                    .collect::<Vec<_>>();
                (!contracts.is_empty()).then(|| (operation.site().clone(), contracts))
            })
            .collect::<Vec<_>>();
        for (site, contracts) in lock_acquisitions {
            for contract in contracts {
                let call = site.id;
                let site = self.obligation_site(&site);
                self.p.obligations.n5.push(AccessCompatibilityObligation {
                    site,
                    requirement: AccessCompatibilityRequirement::LockAcquisition { call, contract },
                });
            }
        }
    }

    /// Declare N8 for every typed operation that crosses a resolved call,
    /// runtime, task-completion, or declared foreign boundary. The effect
    /// summary is already canonical PostAST data.
    fn populate_boundary_obligations(&mut self) {
        let boundaries = self
            .p
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .filter_map(|operation| {
                let effects = match operation {
                    Operation::DirectCall(call) => Some(call.effects),
                    Operation::MethodCall(call) => Some(call.effects),
                    Operation::ExternalCall(call) => Some(call.effects),
                    Operation::IntrinsicCall(call) => Some(call.effects),
                    Operation::CallableCall(call) => Some(call.effects),
                    Operation::NativeOperation(call) => Some(call.effects),
                    Operation::AwaitValue(awaited) => Some(awaited.effects),
                    Operation::CompleteBranch(completion) => Some(completion.effects),
                    Operation::ForeignC(foreign) => match foreign.effects {
                        ForeignBoundaryEffects::Declared(effects) => Some(effects),
                        ForeignBoundaryEffects::UncheckedOpaque { .. } => None,
                    },
                    Operation::ForeignCpp(foreign) => match foreign.effects {
                        ForeignBoundaryEffects::Declared(effects) => Some(effects),
                        ForeignBoundaryEffects::UncheckedOpaque { .. } => None,
                    },
                    Operation::ForeignAssembly(foreign) => match foreign.effects {
                        ForeignBoundaryEffects::Declared(effects) => Some(effects),
                        ForeignBoundaryEffects::UncheckedOpaque { .. } => None,
                    },
                    _ => None,
                }?;
                Some((operation.site().clone(), effects))
            })
            .collect::<Vec<_>>();
        for (site, effects) in boundaries {
            let obligation = self.obligation_site(&site);
            self.p.obligations.n8.push(BoundaryContractObligation {
                site: obligation,
                requirement: BoundaryContractRequirement::CallContract {
                    call: site.id,
                    effects,
                },
            });
        }
        for context in self.p.obligations.execution_context.clone() {
            let site = self
                .p
                .bodies
                .iter()
                .flat_map(|body| &body.operations)
                .find(|operation| operation.site().id == context.operation)
                .map(|operation| operation.site().clone());
            let Some(site) = site else {
                continue;
            };
            let obligation = self.obligation_site(&site);
            self.p.obligations.n8.push(BoundaryContractObligation {
                site: obligation,
                requirement: BoundaryContractRequirement::ExecutionContext {
                    operation: context.operation,
                    function: context.function,
                    actual: context.actual,
                    required: context.required,
                },
            });
        }
        let branch_transfers = self
            .p
            .contracts
            .applications
            .iter()
            .filter_map(|application| {
                let ContractApplication::Branch { call, .. } = application else {
                    return None;
                };
                let operation = self
                    .p
                    .bodies
                    .iter()
                    .flat_map(|body| &body.operations)
                    .find(|operation| operation.site().id == *call)?;
                let Operation::NativeOperation(native) = operation else {
                    return None;
                };
                let NativeOperationKind::RuntimeLaunch { task, .. } = native.kind else {
                    return None;
                };
                Some((
                    operation.site().clone(),
                    task,
                    self.p.values.entries[task.0 as usize].ty,
                ))
            })
            .collect::<Vec<_>>();
        for (site, task, ty) in branch_transfers {
            let call = site.id;
            let site = self.obligation_site(&site);
            self.p.obligations.n8.push(BoundaryContractObligation {
                site,
                requirement: BoundaryContractRequirement::ThreadTransfer { call, task, ty },
            });
        }
    }

    /// Declare the complete N6 applicability inventory for match decisions.
    /// Coverage is resolved by the semantic pass; verification only proves
    /// that the already-resolved unmatched predicate is unreachable.
    fn populate_match_coverage_obligations(&mut self) {
        for coverage in self.p.match_coverage.clone() {
            let site = self
                .p
                .bodies
                .iter()
                .flat_map(|body| &body.operations)
                .find(|operation| operation.site().id == coverage.decision)
                .map(|operation| operation.site().clone());
            let Some(site) = site else {
                continue;
            };
            let obligation = self.obligation_site(&site);
            self.p.obligations.n6.push(PathValidityObligation {
                site: obligation,
                requirement: PathValidityRequirement::MatchExhaustive {
                    decision: coverage.decision,
                    subject: coverage.subject,
                    unmatched: coverage.unmatched,
                },
            });
        }
    }
    fn binary(
        &mut self,
        n: ast::NodeId,
        op: &str,
        left: ast::NodeId,
        right: ast::NodeId,
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        if matches!(op, "&&" | "||") {
            return self.short_circuit(n, op, left, right);
        }
        let hint = self
            .known_type(left)
            .or_else(|| {
                if matches!(op, "<<" | ">>") {
                    None
                } else {
                    self.known_type(right)
                }
            })
            .or(expected.filter(|t| *t != self.boolean));
        let left = self.expression(left, hint)?.value;
        let shifting = matches!(op, "<<" | ">>");
        let right = self
            .expression(
                right,
                if shifting {
                    None
                } else {
                    Some(self.vtype(left))
                },
            )?
            .value;
        if shifting {
            self.require_integer(n, left)?;
            self.require_integer(n, right)?;
        } else {
            self.require_type(n, self.vtype(right), self.vtype(left))?;
        }
        let ty = self.vtype(left);
        let comparison = matches!(op, "==" | "!=" | "<" | "<=" | ">" | ">=");
        let domain = match self.p.types.entries[ty.0 as usize].kind {
            TypeDefinition::Numeric(d) => Some(d),
            _ => None,
        };
        if domain.is_none() && !matches!(op, "==" | "!=") {
            return Err(self.fail(
                n,
                DiagnosticKind::TypeMismatch,
                "arithmetic/ordering requires numeric operands",
            ));
        }
        let site = self.site(n, ExecutionPhase::Compute);
        let mut constraints = self.primitive_constraints(left);
        constraints.extend(self.primitive_constraints(right));
        let result = self.op_value(
            &site,
            if comparison { self.boolean } else { ty },
            if comparison { vec![] } else { constraints },
        );
        let checks = self.arithmetic_checks(op, &site, ty, right)?;
        macro_rules! numeric {
            ($kind:ident) => {
                Operation::$kind($kind {
                    site: site.clone(),
                    domain: domain.unwrap(),
                    left,
                    right,
                    result,
                    checks: checks.clone(),
                })
            };
        }
        let operation = match op {
            "+" => numeric!(Add),
            "-" => numeric!(Subtract),
            "*" => numeric!(Multiply),
            "/" => numeric!(Divide),
            "%" => numeric!(Remainder),
            "&" => numeric!(BitAnd),
            "|" => numeric!(BitOr),
            "^" => numeric!(BitXor),
            "<<" => numeric!(ShiftLeft),
            ">>" => numeric!(ShiftRight),
            "<" => numeric!(Less),
            "<=" => numeric!(LessEqual),
            ">" => numeric!(Greater),
            ">=" => numeric!(GreaterEqual),
            "==" | "!=" => {
                let comparison = self.equality(ty, n)?;
                if op == "==" {
                    Operation::Equal(Equal {
                        site: site.clone(),
                        comparison,
                        left,
                        right,
                        result,
                        checks,
                    })
                } else {
                    Operation::NotEqual(NotEqual {
                        site: site.clone(),
                        comparison,
                        left,
                        right,
                        result,
                        checks,
                    })
                }
            }
            _ => return Err(self.fail(n, DiagnosticKind::InvalidType, "unknown binary operator")),
        };
        self.emit(operation);
        Ok(Expr { value: result })
    }
    fn equality(&mut self, ty: TypeId, n: ast::NodeId) -> Result<EqualityPlanId> {
        if let Some(p) = self.p.contracts.equality.iter().find(|p| p.ty == ty) {
            return Ok(p.id);
        }
        let kind = match self.p.types.entries[ty.0 as usize].kind {
            TypeDefinition::Numeric(d) => EqualityKind::Numeric(d),
            TypeDefinition::Boolean => EqualityKind::Boolean,
            TypeDefinition::Reference { target, .. } => {
                if matches!(
                    self.p.types.entries[target.0 as usize].kind,
                    TypeDefinition::Slice { .. } | TypeDefinition::StrData
                ) {
                    EqualityKind::SliceIdentity
                } else {
                    EqualityKind::ReferenceIdentity
                }
            }
            _ => {
                let Some(definition) = self
                    .p
                    .declarations
                    .enums
                    .iter()
                    .find(|e| e.ty == ty)
                    .cloned()
                else {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::TypeMismatch,
                        format!("{} has no built-in equality operation", self.type_name(ty)),
                    ));
                };
                let mut variants = vec![];
                for variant in
                    std::iter::once(definition.variants.first).chain(definition.variants.rest)
                {
                    let mut fields = vec![];
                    for field in self.p.declarations.variants[variant.0 as usize]
                        .fields
                        .clone()
                    {
                        let comparison =
                            self.equality(self.p.declarations.fields[field.0 as usize].ty, n)?;
                        fields.push(FieldEquality { field, comparison });
                    }
                    variants.push(VariantEquality { variant, fields });
                }
                EqualityKind::EnumTagAndPayload(variants)
            }
        };
        let id = EqualityPlanId(self.p.contracts.equality.len() as u32);
        self.p
            .contracts
            .equality
            .push(EqualityPlan { id, ty, kind });
        Ok(id)
    }
    fn arithmetic_checks(
        &mut self,
        op: &str,
        site: &OperationSite,
        ty: TypeId,
        right: ValueId,
    ) -> Result<Vec<CheckId>> {
        let mut checks = vec![];
        let domain = match self.p.types.entries[ty.0 as usize].kind {
            TypeDefinition::Numeric(d) => d,
            _ => return Ok(checks),
        };
        let integer = !matches!(domain, NumericType::F32 | NumericType::F64);
        if matches!(op, "&" | "|" | "^" | "<<" | ">>") && !integer {
            return Err(Diagnostic {
                file: SourceFileId(self.current_unit as u32),
                kind: DiagnosticKind::TypeMismatch,
                span: Span { start: 0, end: 0 },
                message: "bitwise operators require integers".into(),
                related: vec![],
            });
        }
        if integer && matches!(op, "+" | "-" | "*" | "/") {
            let id = CheckId(self.p.runtime_checks.len() as u32);
            self.p
                .runtime_checks
                .push(RuntimeCheck::IntegerOverflow(IntegerOverflowCheck {
                    id,
                    operation: site.id,
                    ty,
                }));
            checks.push(id);
        }
        if matches!(op, "/" | "%") {
            let id = CheckId(self.p.runtime_checks.len() as u32);
            self.p
                .runtime_checks
                .push(RuntimeCheck::ZeroDivisor(ZeroDivisorCheck {
                    id,
                    divisor: right,
                }));
            checks.push(id);
        }
        if matches!(op, "<<" | ">>") {
            let width = match domain {
                NumericType::U8 => 8,
                NumericType::U16 => 16,
                NumericType::I32 | NumericType::U32 => 32,
                NumericType::I64 | NumericType::U64 => 64,
                NumericType::Usize => self.p.target.pointer_bits,
                _ => unreachable!(),
            };
            let id = CheckId(self.p.runtime_checks.len() as u32);
            self.p
                .runtime_checks
                .push(RuntimeCheck::ShiftCount(ShiftCountCheck {
                    id,
                    count: right,
                    width,
                }));
            checks.push(id);
        }
        Ok(checks)
    }
    fn phase(&mut self, site: &mut OperationSite, phase: ExecutionPhase) -> ExecutionMomentId {
        let id = ExecutionMomentId(self.p.execution.execution_moments.len() as u32);
        self.p.execution.execution_moments.push(ExecutionMoment {
            id,
            instance: self.ctx().domain,
            body: site.body,
            timeline: site.timeline,
            branch: site.branch,
            lexical: site.lexical_moment,
            operation: site.id,
            phase,
            guard: site.guard,
        });
        self.p.execution.timelines[site.timeline.0 as usize]
            .execution_moments
            .push(id);
        if let Some(before) = self.ctx().last {
            self.p
                .execution
                .edges
                .push(ExecutionEdge::Sequence(SequenceEdge { before, after: id }));
        }
        self.ctx_mut().last = Some(id);
        site.execution_moments.rest.push(id);
        id
    }
    fn statement(&mut self, n: ast::NodeId) -> Result<bool> {
        match self.kind(n) {
            NodeKind::Let { pattern, ty, value } => {
                let expected = ty
                    .map(|t| self.type_syntax(t, self.ctx().scope))
                    .transpose()?;
                let value = self.expression(*value, expected)?.value;
                if self.vtype(value) == self.never {
                    return Ok(false);
                }
                if let Some(required) = expected {
                    self.require_type(n, self.vtype(value), required)?;
                }
                self.bind_pattern(*pattern, value)?;
                Ok(true)
            }
            NodeKind::ExpressionStatement { expression, .. } => {
                let value = self.expression(*expression, None)?.value;
                if self.vtype(value) == self.never {
                    return Ok(false);
                }
                let site = self.site(n, ExecutionPhase::Destroy);
                let destructor = self.destructor(self.vtype(value))?;
                self.emit(Operation::DiscardResult(DiscardResult {
                    site,
                    value,
                    destructor,
                }));
                Ok(true)
            }
            NodeKind::Assignment {
                target,
                operator,
                value,
            } => {
                let place = self.place_with_permission(*target, true)?;
                let def = self.p.objects.evaluated_places[place.0 as usize].definition;
                let ty = self.p.objects.places[def.0 as usize].ty;
                let op = self.text(*operator);
                if op == "=" {
                    // Snapshot the previous value from the already-evaluated target.
                    // In particular a field replacement must not destroy the new RHS.
                    let previous = self.read_place(*target, place)?.value;
                    let value = self.expression(*value, Some(ty))?.value;
                    let site = self.site(n, ExecutionPhase::Write);
                    let destructor = self.destructor(ty)?;
                    let replacement = ReplacementPlan {
                        previous,
                        cleanup: destructor,
                        write_after: site.execution_moments.first,
                    };
                    self.record_write(place, value, &site);
                    self.emit(Operation::Assign(Assign {
                        site,
                        target: place,
                        value,
                        replacement,
                    }));
                } else {
                    let old = self.load(*target, place)?.value;
                    let mut site = self.site(n, ExecutionPhase::Read);
                    let read_previous = site.execution_moments.first;
                    let shifting = matches!(op, "<<=" | ">>=");
                    let operand = self
                        .expression(*value, if shifting { None } else { Some(ty) })?
                        .value;
                    if shifting {
                        self.require_integer(n, operand)?;
                    } else {
                        self.require_type(n, self.vtype(operand), ty)?;
                    }
                    let TypeDefinition::Numeric(domain) = self.p.types.entries[ty.0 as usize].kind
                    else {
                        return Err(self.fail(
                            n,
                            DiagnosticKind::TypeMismatch,
                            "compound assignment requires a numeric destination",
                        ));
                    };
                    let binary = op.strip_suffix('=').unwrap();
                    let checks = self.arithmetic_checks(binary, &site, ty, operand)?;
                    let compute = self.phase(&mut site, ExecutionPhase::Compute);
                    let computed = self.value(
                        ty,
                        ValueDefinition::OperationResult {
                            operation: site.id,
                            produced_at: compute,
                        },
                        ProvenanceKind::Constructed(site.id),
                        vec![],
                    );
                    let write = self.phase(&mut site, ExecutionPhase::Write);
                    let effects = self.record_write(place, computed, &site);
                    let phases = ReadModifyWriteMoments {
                        read_previous,
                        compute,
                        write,
                    };
                    macro_rules! assign {
                        ($kind:ident) => {
                            Operation::$kind($kind {
                                site: site.clone(),
                                previous: old,
                                computed,
                                phases: phases.clone(),
                                target: place,
                                operand,
                                domain,
                                checks: checks.clone(),
                                effects,
                            })
                        };
                    }
                    let operation = match op {
                        "+=" => assign!(AddAssign),
                        "-=" => assign!(SubtractAssign),
                        "*=" => assign!(MultiplyAssign),
                        "/=" => assign!(DivideAssign),
                        "%=" => assign!(RemainderAssign),
                        "&=" => assign!(BitAndAssign),
                        "|=" => assign!(BitOrAssign),
                        "^=" => assign!(BitXorAssign),
                        "<<=" => assign!(ShiftLeftAssign),
                        ">>=" => assign!(ShiftRightAssign),
                        _ => {
                            return Err(self.fail(
                                n,
                                DiagnosticKind::InvalidType,
                                "unknown compound assignment",
                            ));
                        }
                    };
                    self.emit(operation);
                }
                Ok(true)
            }
            NodeKind::Return { value, .. } => {
                let result_ty = self.ctx().return_type;
                let value = if let Some(value) = value {
                    self.expression(*value, result_ty)?.value
                } else {
                    let site = self.site(n, ExecutionPhase::Compute);
                    let result = self.op_value(&site, self.unit, vec![]);
                    self.emit(Operation::UnitValue(UnitValue { site, result }));
                    result
                };
                self.resolve_return_type(n, self.vtype(value))?;
                let site = self.site(n, ExecutionPhase::Receive);
                let (exit, outer_exits) = self.unwind_exits(&site, ScopeExitKind::Return, None);
                self.ctx_mut().returns.push(GuardedValue {
                    guard: site.guard,
                    value,
                });
                let function = self.ctx().instance;
                self.return_to_caller(value, function, &site);
                self.emit(Operation::ReturnControl(ReturnControl {
                    site,
                    function,
                    value,
                    exit,
                    outer_exits,
                }));
                Ok(false)
            }
            NodeKind::Yield { .. } => {
                self.yield_statement(n)?;
                Ok(true)
            }
            NodeKind::NamedMove { name, .. } => {
                let scope = self.ctx().scope;
                let parent = self.p.scopes.entries[scope.0 as usize]
                    .lexical_parent
                    .ok_or_else(|| {
                        self.fail(
                            n,
                            DiagnosticKind::UnresolvedName,
                            "named move has no enclosing source scope",
                        )
                    })?;
                let name = self.text(*name).to_owned();
                let symbol = self.lookup(parent, &name).ok_or_else(|| {
                    self.fail(
                        n,
                        DiagnosticKind::UnresolvedName,
                        format!("cannot resolve captured binding '{name}'"),
                    )
                })?;
                let SymbolDefinition::Binding(binding) =
                    self.p.symbols.entries[symbol.0 as usize].definition
                else {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "named move requires a variable",
                    ));
                };
                let source = self.p.scopes.bindings[binding.0 as usize].clone();
                let place = self.place(PlaceRoot::Binding(binding), vec![], source.ty);
                let evaluated = self.evaluated_place(n, place, vec![]);
                let value = self.load(n, evaluated)?.value;
                self.bind(n, &name, source.mutable, value)?;
                Ok(true)
            }
            NodeKind::For {
                pattern,
                source,
                body,
            } => self.for_statement(n, *pattern, *source, *body),
            NodeKind::While { condition, body } => {
                let result = self.loop_expression(n, Some(*condition), *body, None, None)?;
                Ok(self.vtype(result.value) != self.never)
            }
            NodeKind::Break { value, .. } => {
                let region = self
                    .ctx()
                    .loops
                    .last()
                    .ok_or_else(|| {
                        self.fail(
                            n,
                            DiagnosticKind::InvalidType,
                            "break requires an enclosing loop",
                        )
                    })?
                    .region;
                let value = if let Some(value) = value {
                    self.expression(*value, self.ctx().loops.last().unwrap().result_type)?
                        .value
                } else {
                    let site = self.site(n, ExecutionPhase::Compute);
                    let result = self.op_value(&site, self.unit, vec![]);
                    self.emit(Operation::UnitValue(UnitValue { site, result }));
                    result
                };
                let site = self.site(n, ExecutionPhase::Exit);
                let stop = self.ctx().loops.last().unwrap().outer_scope;
                let (exit, outer_exits) =
                    self.unwind_exits(&site, ScopeExitKind::Break(region), Some(stop));
                self.ctx_mut()
                    .loops
                    .last_mut()
                    .unwrap()
                    .results
                    .push(GuardedValue {
                        guard: site.guard,
                        value,
                    });
                let transfer = LoopTransfer {
                    at: site.execution_moments.first,
                    guard: site.guard,
                    bindings: self.ctx().bindings.clone(),
                };
                self.ctx_mut()
                    .loops
                    .last_mut()
                    .unwrap()
                    .breaks
                    .push(transfer);
                self.emit(Operation::BreakControl(BreakControl {
                    site,
                    value,
                    region,
                    exit,
                    outer_exits,
                }));
                Ok(false)
            }
            NodeKind::Continue { .. } => {
                let region = self
                    .ctx()
                    .loops
                    .last()
                    .ok_or_else(|| {
                        self.fail(
                            n,
                            DiagnosticKind::InvalidType,
                            "continue requires an enclosing loop",
                        )
                    })?
                    .region;
                let site = self.site(n, ExecutionPhase::Exit);
                let stop = self.ctx().loops.last().unwrap().outer_scope;
                let (exit, outer_exits) =
                    self.unwind_exits(&site, ScopeExitKind::Continue(region), Some(stop));
                let to = self.p.execution.loops[region.0 as usize].continue_target;
                self.p
                    .execution
                    .edges
                    .push(ExecutionEdge::LoopBack(LoopBackEdge {
                        from: site.execution_moments.first,
                        to,
                        region,
                    }));
                let transfer = LoopTransfer {
                    at: site.execution_moments.first,
                    guard: site.guard,
                    bindings: self.ctx().bindings.clone(),
                };
                self.ctx_mut()
                    .loops
                    .last_mut()
                    .unwrap()
                    .continues
                    .push(transfer);
                self.emit(Operation::ContinueControl(ContinueControl {
                    site,
                    region,
                    exit,
                    outer_exits,
                }));
                Ok(false)
            }
            _ => Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                format!(
                    "{} is not a statement",
                    super::grammar::construct_name(self.kind(n))
                ),
            )),
        }
    }
    fn bind_pattern(&mut self, n: ast::NodeId, value: ValueId) -> Result<()> {
        match self.kind(n) {
            NodeKind::Pattern(ast::PatternSyntax::Binding { mutable, name }) => {
                self.bind(n, self.text(*name), mutable.is_some(), value)?;
                Ok(())
            }
            NodeKind::Pattern(ast::PatternSyntax::Tuple { elements }) => {
                let TypeDefinition::Tuple(types) = self.p.types.entries
                    [self.vtype(value).0 as usize]
                    .kind
                    .clone()
                else {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::TypeMismatch,
                        "tuple pattern requires a tuple value",
                    ));
                };
                if elements.len() != types.len() {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::TypeMismatch,
                        "tuple pattern arity differs from the value",
                    ));
                }
                let mut pattern_names = HashSet::new();
                for element in elements {
                    if let NodeKind::Pattern(ast::PatternSyntax::Binding { name, .. }) =
                        self.kind(*element)
                    {
                        if !pattern_names.insert(self.text(*name)) {
                            return Err(self.fail(
                                *element,
                                DiagnosticKind::DuplicateDeclaration,
                                "duplicate binding in one tuple pattern",
                            ));
                        }
                    }
                }
                for (index, (element, ty)) in elements.iter().zip(types).enumerate() {
                    let site = self.site(*element, ExecutionPhase::Read);
                    let result = self.projected_value(
                        &site,
                        value,
                        PositionSelector::TupleElement(index as u32),
                        ty,
                    );
                    let transfer = self.transfer_kind(ty);
                    self.emit(Operation::ExtractTupleField(ExtractTupleField {
                        site,
                        source: value,
                        position: index as u32,
                        result,
                        reference: self.references.get(&result).copied(),
                        transfer,
                    }));
                    self.bind_pattern(*element, result)?;
                }
                Ok(())
            }
            _ => Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                "unsupported binding pattern",
            )),
        }
    }
    fn record_write(
        &mut self,
        place: EvaluatedPlaceId,
        value: ValueId,
        site: &OperationSite,
    ) -> EffectSummaryId {
        let mut write_site = site.clone();
        write_site.execution_moments = NonEmpty {
            first: *site
                .execution_moments
                .rest
                .last()
                .unwrap_or(&site.execution_moments.first),
            rest: vec![],
        };
        let site = &write_site;
        let p = self.p.objects.places[self.p.objects.evaluated_places[place.0 as usize]
            .definition
            .0 as usize]
            .clone();
        if let PlaceRoot::Binding(binding) = p.root {
            if p.projections.is_empty() {
                self.ctx_mut().bindings.insert(binding, value);
                if !self.primitive(p.ty) {
                    self.materialize_binding(binding, value, site);
                }
                self.transfers.push(TransferLink {
                    source: value,
                    result: value,
                    entity: self.value_entities.get(&value).cloned(),
                    operation: site.id,
                    at: *site
                        .execution_moments
                        .rest
                        .last()
                        .unwrap_or(&site.execution_moments.first),
                    guard: site.guard,
                    receiver: self.binding_owner(binding),
                });
            }
        }
        let effects = self.effects(
            site,
            vec![Effect::Write(WriteEffect {
                place: p.id,
                value,
                value_dependencies: self.p.values.entries[value.0 as usize].dependencies,
            })],
        );
        effects
    }
    fn destructor(&mut self, ty: TypeId) -> Result<DestructorId> {
        if let Some(d) = self.p.contracts.destructors.iter().find(|d| d.ty == ty) {
            return Ok(d.id);
        }
        self.ensure_nominal(ty, self.syntax.ast.root)?;
        let user = self
            .owner_scopes
            .get(&ty)
            .and_then(|s| self.names[s.0 as usize].get("drop"))
            .copied();
        if let Some(symbol) = user {
            let SymbolDefinition::Function(function) =
                self.p.symbols.entries[symbol.0 as usize].definition
            else {
                unreachable!()
            };
            let mut inferred = HashMap::new();
            if let Some(owner) = self.functions[function.0 as usize].owner {
                self.infer_substitutions(self.syntax.ast.root, owner, ty, &mut inferred)?;
            }
            let generic = self.p.declarations.functions[function.0 as usize]
                .type_parameters
                .clone();
            let actual = generic
                .iter()
                .map(|p| {
                    inferred.get(p).copied().ok_or_else(|| {
                        self.fail(
                            self.syntax.ast.root,
                            DiagnosticKind::InvalidType,
                            "destructor has unresolved owner arguments",
                        )
                    })
                })
                .collect::<Result<Vec<_>>>()?;
            let old_configuration = self.active_configuration;
            if let TypeDefinition::Nominal { configuration, .. } =
                self.p.types.entries[ty.0 as usize].kind
            {
                self.active_configuration = configuration;
            }
            let hook = self.specialized_instance(function, actual)?;
            self.active_configuration = old_configuration;
            let signature = &self.p.declarations.signatures
                [self.p.declarations.instances[hook.0 as usize].signature.0 as usize];
            if !matches!(signature.receiver,ReceiverMode::Mutable(target)if target==ty)
                || signature.parameters.len() != 1
                || signature.result != self.unit
            {
                return Err(self.fail(
                    self.syntax.ast.root,
                    DiagnosticKind::InvalidType,
                    "destructor must have signature fn drop(&mut self)",
                ));
            }
            let id = DestructorId(self.p.contracts.destructors.len() as u32);
            self.p.contracts.destructors.push(DestructorDefinition {
                id,
                ty,
                hook,
                owned_components: vec![],
            });
            self.populate_cleanup_components(id)?;
            return Ok(id);
        }
        let function = FunctionId(self.p.declarations.functions.len() as u32);
        let origin = self.builtin_origin("default empty destructor");
        let symbol = SymbolId(self.p.symbols.entries.len() as u32);
        self.p.symbols.entries.push(Symbol {
            id: symbol,
            spelling: format!("<drop:{}>", ty.0),
            declaring_scope: ScopeId(0),
            origin,
            visibility: Visibility::Private,
            definition: SymbolDefinition::Function(function),
        });
        let receiver_type = self.intern(TypeKey::Reference(true, ty));
        let signature = self.signature(
            vec![receiver_type],
            self.unit,
            ReceiverMode::Mutable(ty),
            FunctionExecution::Synchronous,
        );
        self.p.declarations.functions.push(FunctionDefinition {
            parametric_body: None,
            id: function,
            symbol,
            signature,
            type_parameters: vec![],
            body: if matches!(
                self.p.types.entries[ty.0 as usize].kind,
                TypeDefinition::Parameter(_)
            ) {
                FunctionImplementation::ParametricDestructor { ty }
            } else {
                FunctionImplementation::EmptyDestructor { ty }
            },
            contracts: vec![],
        });
        self.functions.push(FunctionSource {
            unit: self.current_unit,
            node: self.syntax.ast.root,
            scope: ScopeId(0),
            owner: Some(ty),
            signature,
            parameters: vec![("self".into(), receiver_type, true)],
            result: self.unit,
            body: None,
            captures: None,
            infer_result: false,
            annotations: vec![],
            parameter_syntax: vec![None],
            result_syntax: None,
        });
        let hook = FunctionInstanceId(self.p.declarations.instances.len() as u32);
        let effects = EffectSummaryId(self.p.effects.len() as u32);
        self.p.effects.push(EffectSummary {
            id: effects,
            effects: vec![],
        });
        let result_summary = self.empty_dependency_summary();
        self.p.declarations.instances.push(FunctionInstance {
            resolution: if self.has_parameters(ty) {
                InstanceResolution::Parametric { parameters: vec![] }
            } else {
                InstanceResolution::Concrete
            },
            configuration: self.active_configuration,
            id: hook,
            body: None,
            contract_matches: vec![],
            contracts: vec![],
            result: FunctionResultSummary {
                native: None,
                values: vec![],
                dependencies: result_summary,
            },
            definition: function,
            substitutions: vec![],
            signature,
            effects,
        });
        let id = DestructorId(self.p.contracts.destructors.len() as u32);
        self.p.contracts.destructors.push(DestructorDefinition {
            id,
            ty,
            hook,
            owned_components: vec![],
        });
        self.populate_cleanup_components(id)?;
        Ok(id)
    }
    fn path_symbol(&self, n: ast::NodeId, segments: &[ast::TokenRef]) -> Result<SymbolId> {
        self.scoped_path(n, self.ctx().scope, segments)
    }
    fn scoped_path(
        &self,
        n: ast::NodeId,
        scope: ScopeId,
        segments: &[ast::TokenRef],
    ) -> Result<SymbolId> {
        let from_scope = scope;
        let first = segments
            .first()
            .ok_or_else(|| self.fail(n, DiagnosticKind::UnresolvedName, "empty path"))?;
        let mut symbol = self.lookup(scope, self.text(*first)).ok_or_else(|| {
            self.fail(
                n,
                DiagnosticKind::UnresolvedName,
                format!("cannot resolve '{}'", self.text(*first)),
            )
        })?;
        for segment in &segments[1..] {
            let member_scope = match self.p.symbols.entries[symbol.0 as usize].definition {
                SymbolDefinition::Type(ty) => self.owner_scopes.get(&ty).copied(),
                SymbolDefinition::Module(module) => {
                    Some(self.p.declarations.modules[module.0 as usize].scope)
                }
                _ => None,
            }
            .ok_or_else(|| {
                self.fail(
                    n,
                    DiagnosticKind::UnresolvedName,
                    "path prefix has no type/module members",
                )
            })?;
            let scope = member_scope;
            symbol = *self.names[scope.0 as usize]
                .get(self.text(*segment))
                .ok_or_else(|| {
                    self.fail(
                        n,
                        DiagnosticKind::UnresolvedName,
                        format!("cannot resolve member '{}'", self.text(*segment)),
                    )
                })?;
        }
        if !self.visible_from(symbol, from_scope) {
            return Err(self.fail(
                n,
                DiagnosticKind::UnresolvedName,
                "component is private to its declaring module",
            ));
        }
        Ok(symbol)
    }
    fn call(
        &mut self,
        n: ast::NodeId,
        callee: ast::NodeId,
        arguments: &[ast::NodeId],
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        if matches!(self.kind(callee),NodeKind::Path { segments, .. } if segments.len()==1 && self.text(segments[0])=="addr")
        {
            return self.address_expression(n, arguments);
        }
        if let NodeKind::Path { segments, .. } = self.kind(callee) {
            if segments.len() == 1 && matches!(self.text(segments[0]), "drop" | "copy") {
                return self.copy_or_drop(n, self.text(segments[0]) == "drop", arguments);
            }
        }
        if let Some(result) = self.native_call(n, callee, arguments, expected)? {
            return Ok(result);
        }
        let (function, receiver) = match self.kind(callee) {
            NodeKind::Path { segments, .. } => {
                let symbol = self.path_symbol(callee, segments)?;
                match self.p.symbols.entries[symbol.0 as usize].definition {
                    SymbolDefinition::Function(function) => (function, None),
                    SymbolDefinition::Overloads(set) => {
                        if arguments.len() != 1 {
                            return Err(self.fail(
                                n,
                                DiagnosticKind::InvalidCall,
                                "from overloads require one argument",
                            ));
                        }
                        let argument = self.expression(arguments[0], None)?.value;
                        let target =
                            self.select_from_overload(n, set, self.vtype(argument), expected)?;
                        let definition =
                            self.p.declarations.instances[target.0 as usize].definition;
                        return self.invoke_concrete(
                            n,
                            self.functions[definition.0 as usize].clone(),
                            target,
                            vec![argument],
                            0,
                            expected,
                        );
                    }
                    SymbolDefinition::Variant(_) => {
                        return self.variant_expression(n, segments, arguments, expected);
                    }
                    SymbolDefinition::Binding(_) => {
                        return self.callable_invocation(n, callee, arguments, expected);
                    }
                    _ => {
                        return Err(self.fail(
                            n,
                            DiagnosticKind::InvalidCall,
                            "resolved name is not callable",
                        ));
                    }
                }
            }
            NodeKind::Projection { base, member } => {
                let name = self.text(*member);
                let original = self.place_expression(*base)?;
                let place = self.deref_place(*base, original)?;
                let ty = self.p.objects.places[self.p.objects.evaluated_places[place.0 as usize]
                    .definition
                    .0 as usize]
                    .ty;
                let original_type = self.p.objects.places[self.p.objects.evaluated_places
                    [original.0 as usize]
                    .definition
                    .0 as usize]
                    .ty;
                if self.is_native_receiver(original_type)
                    || matches!(
                        self.p.types.entries[ty.0 as usize].kind,
                        TypeDefinition::StrData
                    )
                {
                    return self.native_method(n, original, name, arguments);
                }
                if name == "content_eq"
                    && matches!(self.p.types.entries[ty.0 as usize].kind,TypeDefinition::Slice{element} if matches!(self.p.types.entries[element.0 as usize].kind,TypeDefinition::Numeric(NumericType::U8)))
                {
                    return self.byte_content_equal(n, place, arguments);
                }
                if matches!(
                    self.p.types.entries[ty.0 as usize].kind,
                    TypeDefinition::Parameter(_)
                ) {
                    return self.contract_method_call(n, place, ty, name, arguments, expected);
                }
                self.ensure_nominal(ty, n)?;
                let symbol = self
                    .owner_scopes
                    .get(&ty)
                    .and_then(|scope| self.names[scope.0 as usize].get(name))
                    .copied();
                if symbol.is_none() && name == "try_slice" && arguments.len() == 1 {
                    if matches!(self.kind(arguments[0]), NodeKind::Range { .. }) {
                        return self.try_text_slice(n, place, arguments[0]);
                    }
                }
                if symbol.is_none() && name == "len" && arguments.is_empty() {
                    let (_, value) = self.sequence_info(n, place)?;
                    return Ok(Expr { value });
                }
                if symbol.is_none() && matches!(name, "ref" | "mut_ref") {
                    if !arguments.is_empty() {
                        return Err(self.fail(
                            n,
                            DiagnosticKind::InvalidCall,
                            "reference helpers take no arguments",
                        ));
                    }
                    return self.borrow(n, original, name == "mut_ref");
                }
                let symbol = symbol.ok_or_else(|| {
                    self.fail(
                        n,
                        DiagnosticKind::UnresolvedName,
                        format!("{} has no method '{name}'", self.type_name(ty)),
                    )
                })?;
                if !self.visible_from(symbol, self.ctx().scope) {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::UnresolvedName,
                        "member is private to its declaring module",
                    ));
                }
                if let SymbolDefinition::Field(field) =
                    self.p.symbols.entries[symbol.0 as usize].definition
                {
                    let parent = self.p.objects.places[self.p.objects.evaluated_places
                        [place.0 as usize]
                        .definition
                        .0 as usize]
                        .clone();
                    let mut projections = parent.projections;
                    projections.push(PlaceProjection::Field(field));
                    let ty = self.p.declarations.fields[field.0 as usize].ty;
                    let field_place = self.place(parent.root, projections, ty);
                    let evaluated = self.evaluated_place(callee, field_place, vec![]);
                    return self.invoke_callable_place(n, evaluated, arguments, expected);
                }
                let SymbolDefinition::Function(function) =
                    self.p.symbols.entries[symbol.0 as usize].definition
                else {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidCall,
                        "member is not callable",
                    ));
                };
                let receiver = match self.p.declarations.signatures
                    [self.functions[function.0 as usize].signature.0 as usize]
                    .receiver
                {
                    ReceiverMode::Shared(_) => self.borrow(*base, place, false)?,
                    ReceiverMode::Mutable(_) => self.borrow(*base, place, true)?,
                    ReceiverMode::ByValue(_) => self.load(*base, place)?,
                    ReceiverMode::None => {
                        return Err(self.fail(
                            n,
                            DiagnosticKind::InvalidCall,
                            "associated function must be called through its type",
                        ));
                    }
                };
                (function, Some(receiver.value))
            }
            _ => return self.callable_invocation(n, callee, arguments, expected),
        };
        let explicit = match self.kind(callee) {
            NodeKind::Path { arguments, .. } => arguments.clone(),
            _ => vec![],
        };
        self.invoke_function(n, function, receiver, &explicit, arguments, expected)
    }
    fn invoke_function(
        &mut self,
        n: ast::NodeId,
        function: FunctionId,
        receiver: Option<ValueId>,
        explicit: &[ast::NodeId],
        arguments: &[ast::NodeId],
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        let source = self.functions[function.0 as usize].clone();
        let offset = usize::from(receiver.is_some());
        if source.parameters.len() != arguments.len() + offset {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                format!(
                    "expected {} arguments, found {}",
                    source.parameters.len().saturating_sub(offset),
                    arguments.len()
                ),
            ));
        }
        let generic_parameters = self.p.declarations.functions[function.0 as usize]
            .type_parameters
            .clone();
        let mut substitutions = HashMap::new();
        if !explicit.is_empty() {
            if explicit.len() != generic_parameters.len() {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    "explicit generic argument count differs from the function's type parameters",
                ));
            }
            for (parameter, argument) in generic_parameters.iter().zip(explicit) {
                let ty = self.type_syntax(*argument, self.ctx().scope)?;
                substitutions.insert(*parameter, ty);
            }
        }
        if let Some(receiver) = receiver {
            let actual = self.vtype(receiver);
            let nominal = match self.p.types.entries[actual.0 as usize].kind {
                TypeDefinition::Reference { target, .. } => target,
                _ => actual,
            };
            if let (
                Some(owner),
                TypeDefinition::Nominal {
                    definition,
                    arguments,
                    ..
                },
            ) = (
                source.owner,
                self.p.types.entries[nominal.0 as usize].kind.clone(),
            ) {
                if matches!(self.p.types.entries[owner.0 as usize].kind,TypeDefinition::Nominal{definition:d,..}if d==definition)
                {
                    for (parameter, argument) in
                        self.nominal_parameters[&definition].iter().zip(arguments)
                    {
                        if let TypeArgument::Type(ty) = argument {
                            substitutions.insert(*parameter, ty);
                        }
                    }
                }
            }
            self.infer_substitutions(n, source.parameters[0].1, actual, &mut substitutions)?;
        }
        if let (Some(expected), false) = (expected, generic_parameters.is_empty()) {
            self.infer_substitutions(n, source.result, expected, &mut substitutions)?;
        }
        let mut values = receiver.into_iter().collect::<Vec<_>>();
        for (index, arg) in arguments.iter().enumerate() {
            let formal = source.parameters[index + offset].1;
            let required = self.substitute_type(formal, &substitutions);
            let context = if self.unbound_for_call(required, &substitutions) {
                None
            } else {
                Some(required)
            };
            let value = self.expression(*arg, context)?.value;
            self.infer_substitutions(*arg, formal, self.vtype(value), &mut substitutions)?;
            let required = self.substitute_type(formal, &substitutions);
            let value = self
                .adapt_callable(*arg, Expr { value }, Some(required))?
                .value;
            self.require_type(*arg, self.vtype(value), required)?;
            values.push(value);
        }
        self.infer_contract_arguments(n, &generic_parameters, &mut substitutions)?;
        let actual = generic_parameters
            .iter()
            .map(|parameter| {
                substitutions.get(parameter).copied().ok_or_else(|| {
                    self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "cannot infer generic type parameter from arguments or expected result",
                    )
                })
            })
            .collect::<Result<Vec<_>>>()?;
        let caller_configuration = self.active_configuration;
        if let Some(receiver) = receiver {
            let ty = self.vtype(receiver);
            let ty = match self.p.types.entries[ty.0 as usize].kind {
                TypeDefinition::Reference { target, .. } => target,
                _ => ty,
            };
            if let TypeDefinition::Nominal { configuration, .. } =
                self.p.types.entries[ty.0 as usize].kind
            {
                self.active_configuration = configuration;
            }
        }
        let target = self.specialized_instance(function, actual)?;
        self.active_configuration = caller_configuration;
        let signature = self.p.declarations.instances[target.0 as usize].signature;
        if matches!(
            self.p.declarations.signatures[signature.0 as usize].execution,
            FunctionExecution::Asynchronous
        ) {
            self.make_future(n, target, None, values)
        } else {
            self.invoke_concrete(n, source, target, values, offset, expected)
        }
    }
    fn invoke_concrete(
        &mut self,
        n: ast::NodeId,
        source: FunctionSource,
        target: FunctionInstanceId,
        values: Vec<ValueId>,
        offset: usize,
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        let function = self.p.declarations.instances[target.0 as usize].definition;
        let signature = self.p.declarations.instances[target.0 as usize].signature;
        let mut source = source;
        source.signature = signature;
        source.result = self.p.declarations.signatures[signature.0 as usize].result;
        let mut site = self.site(n, ExecutionPhase::Invoke);
        if matches!(
            self.p.declarations.functions[function.0 as usize].body,
            FunctionImplementation::RuntimeJoin
        ) {
            self.require_execution_context(site.id, FunctionExecution::Synchronous);
        }
        let received = self.phase(&mut site, ExecutionPhase::Receive);
        let dependencies = vec![DependencyRequirement::InstantiatedResult {
            function: target,
            arguments: values.clone(),
        }];
        let result = self.value(
            source.result,
            ValueDefinition::OperationResult {
                operation: site.id,
                produced_at: received,
            },
            ProvenanceKind::CallResult {
                operation: site.id,
                effects: self.p.declarations.instances[target.0 as usize].effects,
            },
            dependencies,
        );
        self.p.values.provenance[self.p.values.entries[result.0 as usize].provenance.0 as usize]
            .kind = ProvenanceKind::CallResult {
            operation: site.id,
            effects: self.p.declarations.instances[target.0 as usize].effects,
        };
        let args: Vec<CallArgument> = values
            .iter()
            .enumerate()
            .map(|(index, value)| CallArgument {
                parameter_index: index as u32,
                value: *value,
                transfer: self.transfer_kind(self.vtype(*value)),
            })
            .collect();
        let effects = self.effects(
            &site,
            vec![Effect::Call(CallEffect {
                target,
                arguments: args.clone(),
            })],
        );
        if let Some(receiver) = values.first().copied().filter(|_| offset == 1) {
            let mode = self.p.declarations.signatures[source.signature.0 as usize]
                .receiver
                .clone();
            self.emit(Operation::MethodCall(MethodCall {
                site: site.clone(),
                target: ResolvedMethodCall {
                    target: MethodTarget::Concrete(target),
                    receiver,
                    mode,
                    matched_contract: None,
                },
                arguments: args,
                result,
                effects,
            }));
        } else if matches!(
            self.p.declarations.functions[function.0 as usize].body,
            FunctionImplementation::External { .. }
        ) {
            self.emit(Operation::ExternalCall(ExternalCall {
                site: site.clone(),
                target: ResolvedExternalCall {
                    function: target,
                    abi: AbiId(0),
                },
                arguments: args,
                result,
                effects,
            }));
        } else {
            self.emit(Operation::DirectCall(DirectCall {
                site: site.clone(),
                target,
                arguments: args,
                result,
                effects,
            }));
        }
        if let Some(body) = self
            .p
            .bodies
            .iter()
            .find(|b| matches!(b.owner,BodyOwner::Instance(i) if i==target))
        {
            let domain = InstanceDomainId(self.p.execution.instance_domains.len() as u32);
            self.p.execution.instance_domains.push(InstanceDomain {
                id: domain,
                definition: InstanceDomainDefinition::Call {
                    parent: self.ctx().domain,
                    call: site.id,
                    callee: body.id,
                },
            });
            let entry = self.p.execution.timelines[self.p.execution.branches
                [body.root_branch.0 as usize]
                .timeline
                .0 as usize]
                .entries
                .first;
            self.p.execution.edges.push(ExecutionEdge::Call(CallEdge {
                call: site.execution_moments.first,
                callee_entry: entry,
                instance: domain,
            }));
            self.p.execution.edges.retain(|edge| !matches!(edge, ExecutionEdge::Sequence(e) if e.before == site.execution_moments.first && e.after == received));
            let exits = self.p.execution.timelines[self.p.execution.branches
                [body.root_branch.0 as usize]
                .timeline
                .0 as usize]
                .exits
                .clone();
            for callee_exit in exits {
                self.p
                    .execution
                    .edges
                    .push(ExecutionEdge::Return(ReturnEdge {
                        callee_exit,
                        continuation: received,
                        instance: domain,
                    }));
            }
        }
        self.apply_call_contracts(n, target, &values, result, &site)?;
        if let Some(t) = expected {
            self.require_type(n, source.result, t)?;
        }
        // A result reference retains its concrete target origins from the summary.
        if let TypeDefinition::Reference { permission, .. } =
            self.p.types.entries[source.result.0 as usize].kind.clone()
        {
            let targets = self
                .dependencies(result)
                .into_iter()
                .filter_map(|d| {
                    if let DependencyRequirement::LiveTarget(place) = d {
                        Some(place)
                    } else {
                        None
                    }
                })
                .collect::<Vec<_>>();
            let mut targets = targets;
            if targets.is_empty() {
                let TypeDefinition::Reference { target, .. } =
                    self.p.types.entries[source.result.0 as usize].kind
                else {
                    unreachable!()
                };
                targets.push(self.place(
                    PlaceRoot::Value(result),
                    vec![PlaceProjection::Dereference],
                    target,
                ));
            }
            if let Some(first) = targets.first().copied() {
                let id = ReferenceId(self.p.objects.references.len() as u32);
                self.p.objects.references.push(Reference {
                    creation: ObjectCreation::At(received),
                    id,
                    ty: source.result,
                    created_in: site.scope,
                    initial_owner: Owner::Scope {
                        scope: site.scope,
                        instance: self.ctx().domain,
                    },
                    permission,
                    formation: ReferenceFormation::Loan,
                    origins: NonEmpty {
                        first: ReferenceOrigin {
                            target: first,
                            parent: None,
                            guard: site.guard,
                        },
                        rest: targets[1..]
                            .iter()
                            .map(|target| ReferenceOrigin {
                                target: *target,
                                parent: None,
                                guard: site.guard,
                            })
                            .collect(),
                    },
                });
                self.references.insert(result, id);
                self.value_entities.insert(result, EntityId::Reference(id));
            }
        }
        Ok(Expr { value: result })
    }
    fn construct(
        &mut self,
        n: ast::NodeId,
        path: Option<ast::NodeId>,
        fields: &[ast::NodeId],
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        let (mut ty, mut variant, mut required) = if let Some(path) = path {
            let NodeKind::Path { segments, .. } = self.kind(path) else {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    "constructor must name a type or variant",
                ));
            };
            let symbol = self.path_symbol(n, segments)?;
            match self.p.symbols.entries[symbol.0 as usize].definition {
                SymbolDefinition::Type(ty) => {
                    let substitutions = self.ctx().substitutions.clone();
                    let ty = self.substitute_type(ty, &substitutions);
                    let ty = self.configured_type(ty, self.active_configuration);
                    (ty, None, self.fields(ty, n)?)
                }
                SymbolDefinition::Variant(variant) => {
                    let definition = &self.p.declarations.variants[variant.0 as usize];
                    (definition.owner, Some(variant), definition.fields.clone())
                }
                _ => {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "initializer must name a type or enum variant",
                    ));
                }
            }
        } else {
            let ty = expected.ok_or_else(|| {
                self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    "an inferred initializer needs a contextual type",
                )
            })?;
            (ty, None, self.fields(ty, n)?)
        };
        let mut substitutions = self.nominal_substitutions(n, ty, expected)?;
        let mut supplied = HashMap::new();
        for field in fields {
            let NodeKind::FieldInitializer { name, value } = self.kind(*field) else {
                unreachable!()
            };
            let name = self.text(*name);
            let id = required
                .iter()
                .copied()
                .find(|id| {
                    self.p.symbols.entries
                        [self.p.declarations.fields[id.0 as usize].symbol.0 as usize]
                        .spelling
                        == name
                })
                .ok_or_else(|| {
                    self.fail(
                        *field,
                        DiagnosticKind::UnresolvedName,
                        format!("unknown field '{name}'"),
                    )
                })?;
            if supplied.contains_key(&id) {
                return Err(self.fail(
                    *field,
                    DiagnosticKind::DuplicateDeclaration,
                    format!("field '{name}' specified twice"),
                ));
            }
            if !self.visible_from(
                self.p.declarations.fields[id.0 as usize].symbol,
                self.ctx().scope,
            ) {
                return Err(self.fail(
                    *field,
                    DiagnosticKind::UnresolvedName,
                    "cannot initialize a private field from this module",
                ));
            }
            let formal_type = self.p.declarations.fields[id.0 as usize].ty;
            let required_type = self.substitute_type(formal_type, &substitutions);
            let value = if let Some(value) = value {
                let hint = if self.unbound_for_call(required_type, &substitutions) {
                    None
                } else {
                    Some(required_type)
                };
                self.expression(*value, hint)?.value
            } else {
                let symbol = self.lookup(self.ctx().scope, name).ok_or_else(|| {
                    self.fail(
                        *field,
                        DiagnosticKind::UnresolvedName,
                        format!("cannot resolve shorthand field '{name}'"),
                    )
                })?;
                let SymbolDefinition::Binding(binding) =
                    self.p.symbols.entries[symbol.0 as usize].definition
                else {
                    return Err(self.fail(
                        *field,
                        DiagnosticKind::InvalidType,
                        "shorthand does not name a binding",
                    ));
                };
                let place = self.place(
                    PlaceRoot::Binding(binding),
                    vec![],
                    self.p.scopes.bindings[binding.0 as usize].ty,
                );
                let evaluated = self.evaluated_place(*field, place, vec![]);
                self.load(*field, evaluated)?.value
            };
            self.infer_substitutions(*field, formal_type, self.vtype(value), &mut substitutions)?;
            let required_type = self.substitute_type(formal_type, &substitutions);
            self.require_type(*field, self.vtype(value), required_type)?;
            supplied.insert(id, value);
        }
        if let TypeDefinition::Nominal { definition, .. } =
            self.p.types.entries[ty.0 as usize].kind.clone()
        {
            let parameters = self
                .nominal_parameters
                .get(&definition)
                .cloned()
                .unwrap_or_default();
            if !parameters.is_empty() {
                self.infer_contract_arguments(n, &parameters, &mut substitutions)?;
                let arguments = parameters
                    .iter()
                    .map(|p| {
                        substitutions.get(p).copied().ok_or_else(|| {
                            self.fail(
                                n,
                                DiagnosticKind::InvalidType,
                                "cannot infer constructor type argument from fields or annotation",
                            )
                        })
                    })
                    .collect::<Result<Vec<_>>>()?;
                let template = self.intern(TypeKey::Nominal(definition, arguments));
                let actual = self.configured_type(template, self.active_configuration);
                self.ensure_nominal(actual, n)?;
                let actual_fields = if let Some(old_variant) = variant {
                    let concrete = self.variant_for_type(n, old_variant, actual)?;
                    variant = Some(concrete);
                    self.p.declarations.variants[concrete.0 as usize]
                        .fields
                        .clone()
                } else {
                    self.fields(actual, n)?
                };
                let mut mapped = HashMap::new();
                for (original, actual) in required.iter().zip(&actual_fields) {
                    if let Some(value) = supplied.remove(original) {
                        mapped.insert(*actual, value);
                    }
                }
                supplied = mapped;
                required = actual_fields;
                ty = actual;
            }
        }
        if let Some(expected) = expected {
            self.require_type(n, ty, expected)?;
        }
        let mut components = vec![];
        let mut values = vec![];
        for field in required {
            let value = if let Some(v) = supplied.remove(&field) {
                v
            } else {
                self.default_value(n, self.p.declarations.fields[field.0 as usize].ty)?
            };
            values.push(value);
            components.push(ComponentInitialization {
                position: PositionSelector::Field(field),
                value,
                transfer: self.transfer_kind(self.vtype(value)),
            });
        }
        let site = self.site(n, ExecutionPhase::Compute);
        let dependencies = values.iter().flat_map(|v| self.dependencies(*v)).collect();
        let result = self.op_value(&site, ty, dependencies);
        self.components.insert(result, values);
        self.materialize_value(
            result,
            Owner::Scope {
                scope: site.scope,
                instance: self.ctx().domain,
            },
            &site,
        );
        if let Some(variant) = variant {
            self.emit(Operation::ConstructEnum(ConstructEnum {
                site,
                ty,
                variant,
                components,
                result,
            }));
        } else {
            self.emit(Operation::ConstructStruct(ConstructStruct {
                site,
                ty,
                components,
                result,
            }));
        }
        Ok(Expr { value: result })
    }
    fn default_value(&mut self, n: ast::NodeId, ty: TypeId) -> Result<ValueId> {
        let plan = self.default_plan(n, ty, &mut HashSet::new())?;
        let site = self.site(n, ExecutionPhase::Compute);
        let result = self.op_value(&site, ty, vec![]);
        self.emit(Operation::InitializeDefault(InitializeDefault {
            site,
            plan,
            result,
        }));
        Ok(result)
    }
    fn variant_expression(
        &mut self,
        n: ast::NodeId,
        segments: &[ast::TokenRef],
        arguments: &[ast::NodeId],
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        let symbol = self.path_symbol(n, segments)?;
        let SymbolDefinition::Variant(variant) =
            self.p.symbols.entries[symbol.0 as usize].definition
        else {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidType,
                "path does not name a variant",
            ));
        };
        let def = self.p.declarations.variants[variant.0 as usize].clone();
        if def.fields.len() != arguments.len() {
            return Err(self.fail(
                n,
                DiagnosticKind::InvalidCall,
                "variant payload arity mismatch",
            ));
        }
        let mut substitutions = self.variant_substitutions(n, variant, expected)?;
        let mut components = vec![];
        let mut values = vec![];
        for (field, arg) in def.fields.iter().zip(arguments) {
            let formal = self.p.declarations.fields[field.0 as usize].ty;
            let contextual = self.substitute_type(formal, &substitutions);
            let hint = if self.unbound_for_call(contextual, &substitutions) {
                None
            } else {
                Some(contextual)
            };
            let value = self.expression(*arg, hint)?.value;
            self.infer_substitutions(*arg, formal, self.vtype(value), &mut substitutions)?;
            values.push(value);
        }
        let variant = self.specialized_variant(n, variant, &substitutions)?;
        let def = self.p.declarations.variants[variant.0 as usize].clone();
        for (field, value) in def.fields.iter().zip(&values) {
            self.require_type(
                n,
                self.vtype(*value),
                self.p.declarations.fields[field.0 as usize].ty,
            )?;
            components.push(ComponentInitialization {
                position: PositionSelector::Field(*field),
                value: *value,
                transfer: self.transfer_kind(self.vtype(*value)),
            });
        }
        if let Some(t) = expected {
            self.require_type(n, def.owner, t)?;
        }
        let site = self.site(n, ExecutionPhase::Compute);
        let dependencies = values.iter().flat_map(|v| self.dependencies(*v)).collect();
        let result = self.op_value(&site, def.owner, dependencies);
        self.components.insert(result, values);
        self.materialize_value(
            result,
            Owner::Scope {
                scope: site.scope,
                instance: self.ctx().domain,
            },
            &site,
        );
        self.emit(Operation::ConstructEnum(ConstructEnum {
            site,
            ty: def.owner,
            variant,
            components,
            result,
        }));
        Ok(Expr { value: result })
    }
    fn block_expression(&mut self, n: ast::NodeId, expected: Option<TypeId>) -> Result<Expr> {
        self.block_with_pattern(n, expected, None)
            .map(|(expression, _)| expression)
    }
    fn block_with_pattern(
        &mut self,
        n: ast::NodeId,
        expected: Option<TypeId>,
        pattern: Option<(patterns::PatternPlan, ValueId)>,
    ) -> Result<(Expr, Option<ResolvedPattern>)> {
        let (scope, parent) = self.enter_runtime_scope(n)?;
        let resolved_pattern = pattern
            .map(|(plan, value)| self.apply_pattern(&plan, value))
            .transpose()?;
        let Some(result) = self.block_contents(n, expected)? else {
            let at = self.ctx().last.expect("terminating block has an event");
            self.ctx_mut().scope = parent;
            self.active_configuration = self.p.scopes.entries[parent.0 as usize].configuration;
            return Ok((self.diverged(at), resolved_pattern));
        };
        let value = self.finish_runtime_scope(n, scope, parent, result)?;
        Ok((value, resolved_pattern))
    }
    fn enter_runtime_scope(&mut self, n: ast::NodeId) -> Result<(ScopeId, ScopeId)> {
        let parent = self.ctx().scope;
        let parent_last = self.ctx().last.or(self.ctx().parent_anchor);
        let scope = ScopeId(self.names.len() as u32);
        let site = self.site(n, ExecutionPhase::Enter);
        let storage = self.scope_storage(scope, site.execution_moments.first);
        let parent_cursor = match self.p.scopes.entries[parent.0 as usize].storage {
            ScopeStorageLink::Runtime(id) => {
                let cursor = self.p.scopes.storage[id.0 as usize].relative_cursor;
                let snapshot = CursorSnapshotId(self.p.cursor_snapshots.len() as u32);
                self.p.cursor_snapshots.push(CursorSnapshot {
                    id: snapshot,
                    scope: parent,
                    moment: parent_last.unwrap_or(site.execution_moments.first),
                    cursor,
                });
                snapshot
            }
            _ => {
                return Err(self.fail(
                    n,
                    DiagnosticKind::IncompleteRepresentation,
                    "runtime parent storage missing",
                ));
            }
        };
        self.p.scopes.entries.push(Scope {
            configuration: self.active_configuration,
            id: scope,
            lexical_scope: self.lexical_scopes[&n],
            lexical_parent: Some(parent),
            unchecked_boundary: self.ctx().unchecked.last().copied(),
            children: vec![],
            context: ScopeContext::Body(self.ctx().body),
            entry: ScopeEntry::Child {
                parent,
                parent_lexical_moment: site.lexical_moment,
                parent_execution_moment: parent_last.unwrap_or(site.execution_moments.first),
                parent_cursor,
                entry: site.execution_moments.first,
            },
            exits: vec![],
            bindings: vec![],
            storage: ScopeStorageLink::Runtime(storage),
        });
        self.p.scopes.entries[parent.0 as usize]
            .children
            .push(scope);
        self.names.push(HashMap::new());
        self.ctx_mut().scope = scope;
        let cursor = self.p.scopes.storage[storage.0 as usize].entry;
        self.emit(Operation::EnterScope(EnterScope {
            site: OperationSite { scope, ..site },
            scope,
            cursor,
        }));
        self.cover(n, SyntaxDisposition::Boundary(scope));
        Ok((scope, parent))
    }
    fn finish_runtime_scope(
        &mut self,
        n: ast::NodeId,
        scope: ScopeId,
        parent: ScopeId,
        result: Expr,
    ) -> Result<Expr> {
        let receive = self.site(n, ExecutionPhase::Receive);
        let value = self.op_value(
            &receive,
            self.vtype(result.value),
            self.dependencies(result.value),
        );
        self.p.values.provenance[self.p.values.entries[value.0 as usize].provenance.0 as usize]
            .kind = ProvenanceKind::Forward {
            source: result.value,
            operation: receive.id,
        };
        if let Some(entity) = self.value_entities.get(&result.value).cloned() {
            self.value_entities.insert(value, entity);
        }
        if let Some(r) = self.references.get(&result.value).copied() {
            self.references.insert(value, r);
        }
        self.forward_summaries(result.value, value);
        if let Some(entity) = self.value_entities.get(&value).cloned() {
            self.p.objects.ownership.push(OwnershipLink {
                entity,
                owner: Owner::Scope {
                    scope: parent,
                    instance: self.ctx().domain,
                },
                scope: parent,
                established: receive.execution_moments.first,
                guard: receive.guard,
            });
        }
        self.transfers.push(TransferLink {
            source: result.value,
            result: value,
            entity: self.value_entities.get(&value).cloned(),
            operation: receive.id,
            at: receive.execution_moments.first,
            guard: receive.guard,
            receiver: Owner::Scope {
                scope: parent,
                instance: self.ctx().domain,
            },
        });
        self.emit(Operation::ForwardResult(ForwardResult {
            site: receive,
            source: result.value,
            destination: value,
        }));
        let exit_site = self.site(n, ExecutionPhase::Exit);
        let exit = self.scope_exit(scope, &exit_site, ScopeExitKind::Normal);
        self.emit(Operation::ExitScope(ExitScope {
            site: exit_site,
            exit,
        }));
        self.ctx_mut().scope = parent;
        self.active_configuration = self.p.scopes.entries[parent.0 as usize].configuration;
        Ok(Expr { value })
    }
    fn predicate(&mut self, kind: PredicateKind) -> PredicateId {
        let id = PredicateId(self.p.execution.predicates.len() as u32);
        self.p.execution.predicates.push(PathPredicate { id, kind });
        id
    }
    fn branch_context(
        &mut self,
        parent: &Context,
        decision: OperationId,
        guard: PredicateId,
    ) -> Context {
        let branch = BranchId(self.p.execution.branches.len() as u32);
        let timeline = TimelineId(self.p.execution.timelines.len() as u32);
        let first = ExecutionMomentId(self.p.execution.execution_moments.len() as u32);
        self.p.execution.branches.push(Branch {
            id: branch,
            timeline,
            kind: BranchKind::Conditional(ConditionalBranch {
                parent: parent.branch,
                decision,
                guard,
            }),
        });
        self.p.execution.timelines.push(Timeline {
            id: timeline,
            branch,
            lexical_order: vec![],
            execution_moments: vec![],
            entries: NonEmpty {
                first,
                rest: vec![],
            },
            exits: vec![],
        });
        let mut child = parent.clone();
        child.branch = branch;
        child.timeline = timeline;
        child.guard = guard;
        child.last = None;
        child.parent_anchor = parent.last.or(parent.parent_anchor);
        child
    }
    fn if_expression(
        &mut self,
        n: ast::NodeId,
        condition: ast::NodeId,
        yes: ast::NodeId,
        no: Option<ast::NodeId>,
        expected: Option<TypeId>,
    ) -> Result<Expr> {
        if let NodeKind::LetCondition { pattern, value } = self.kind(condition) {
            return self.if_let_expression(n, *pattern, *value, yes, no, expected);
        }
        let condition_node = condition;
        let condition = self.expression(condition, Some(self.boolean))?.value;
        self.require_type(condition_node, self.vtype(condition), self.boolean)?;
        self.conditional_expression(
            n,
            condition,
            BranchOperand::Syntax(yes),
            no.map(BranchOperand::Syntax).unwrap_or(BranchOperand::Unit),
            expected,
            None,
        )
    }
    fn branch_operand(
        &mut self,
        n: ast::NodeId,
        operand: BranchOperand,
        expected: Option<TypeId>,
    ) -> Result<ValueId> {
        match operand {
            BranchOperand::Syntax(node) => Ok(self.expression(node, expected)?.value),
            BranchOperand::Boolean(value) => {
                let site = self.site(n, ExecutionPhase::Compute);
                let result = self.op_value(&site, self.boolean, vec![]);
                self.emit(Operation::BooleanLiteral(BooleanLiteral {
                    site,
                    value,
                    result,
                }));
                Ok(result)
            }
            BranchOperand::Unit => {
                let site = self.site(n, ExecutionPhase::Compute);
                let result = self.op_value(&site, self.unit, vec![]);
                self.emit(Operation::UnitValue(UnitValue { site, result }));
                Ok(result)
            }
        }
    }
    fn short_circuit(
        &mut self,
        n: ast::NodeId,
        op: &str,
        left: ast::NodeId,
        right: ast::NodeId,
    ) -> Result<Expr> {
        let condition = self.expression(left, Some(self.boolean))?.value;
        self.require_type(left, self.vtype(condition), self.boolean)?;
        let and = op == "&&";
        let (yes, no) = if and {
            (BranchOperand::Syntax(right), BranchOperand::Boolean(false))
        } else {
            (BranchOperand::Boolean(true), BranchOperand::Syntax(right))
        };
        self.conditional_expression(n, condition, yes, no, Some(self.boolean), Some(and))
    }
    fn loop_expression(
        &mut self,
        n: ast::NodeId,
        condition: Option<ast::NodeId>,
        body: ast::NodeId,
        expected: Option<TypeId>,
        iteration: Option<iteration::IterationInput>,
    ) -> Result<Expr> {
        let parent = self.ctx().clone();
        let header_site = self.site(n, ExecutionPhase::Enter);
        let header = header_site.execution_moments.first;
        let region = LoopRegionId(self.p.execution.loops.len() as u32);
        let variable = IterationVariableId(self.p.execution.iteration_variables.len() as u32);
        self.p
            .execution
            .iteration_variables
            .push(IterationVariable {
                id: variable,
                region,
            });
        let domain = InstanceDomainId(self.p.execution.instance_domains.len() as u32);
        self.p.execution.instance_domains.push(InstanceDomain {
            id: domain,
            definition: InstanceDomainDefinition::Iteration {
                parent: parent.domain,
                moment: IterationMoment {
                    region,
                    iteration: IterationCoordinate::Symbolic(variable),
                },
            },
        });
        self.p.execution.loops.push(LoopRegion {
            id: region,
            branch: parent.branch,
            header,
            body_entry: header,
            continue_target: header,
            break_target: header,
            instance: domain,
        });
        self.ctx_mut().domain = domain;
        let mut loop_parameters = Vec::new();
        let mut bindings = parent
            .bindings
            .iter()
            .map(|(b, v)| (*b, *v))
            .collect::<Vec<_>>();
        bindings.sort_by_key(|(b, _)| b.0);
        for (binding, initial) in bindings {
            let site = self.site(n, ExecutionPhase::Receive);
            let result = self.op_value(&site, self.vtype(initial), vec![]);
            let provenance = self.p.values.entries[result.0 as usize].provenance;
            self.p.values.provenance[provenance.0 as usize].kind =
                ProvenanceKind::LoopParameter(site.id);
            let dependencies = self.p.values.entries[result.0 as usize].dependencies;
            self.p.values.dependency_summaries[dependencies.0 as usize].guarded =
                self.guarded_dependencies(initial, parent.guard);
            self.merge_reference_identities(
                result,
                &[GuardedValue {
                    guard: parent.guard,
                    value: initial,
                }],
                &site,
            );
            self.ctx_mut().bindings.insert(binding, result);
            loop_parameters.push(LoopParameter {
                site,
                region,
                binding,
                initial,
                back_edges: vec![],
                result,
            });
        }
        let iteration_entry = loop_parameters
            .first()
            .map(|p| p.site.execution_moments.first)
            .unwrap_or(ExecutionMomentId(
                self.p.execution.execution_moments.len() as u32
            ));
        self.p.execution.loops[region.0 as usize].continue_target = iteration_entry;
        let iteration_header = iteration
            .as_ref()
            .map(|input| self.iteration_header(n, input, region, variable))
            .transpose()?;
        let condition_value = if let Some(header) = &iteration_header {
            Some(header.condition)
        } else {
            condition
                .map(|c| {
                    let value = self.expression(c, Some(self.boolean))?;
                    self.require_type(c, self.vtype(value.value), self.boolean)?;
                    Ok(value)
                })
                .transpose()?
                .map(|e| e.value)
        };
        let before_body = self.ctx().last.unwrap();
        let guard = if let Some(value) = condition_value {
            let positive = self.predicate(PredicateKind::Boolean {
                value,
                expected: true,
            });
            self.predicate(PredicateKind::All(vec![parent.guard, positive]))
        } else {
            parent.guard
        };
        self.ctx_mut().guard = guard;
        self.ctx_mut().domain = domain;
        self.ctx_mut().loops.push(LoopContext {
            region,
            outer_scope: parent.scope,
            result_type: expected,
            results: vec![],
            breaks: vec![],
            continues: vec![],
        });
        let body_entry = ExecutionMomentId(self.p.execution.execution_moments.len() as u32);
        self.ctx_mut().parent_anchor = Some(before_body);
        self.ctx_mut().last = None;
        let (body_value, iteration_pattern) =
            if let (Some(input), Some(header)) = (&iteration, &iteration_header) {
                let (scope, parent_scope) = self.enter_runtime_scope(body)?;
                let item = self.iteration_item(n, input, header)?;
                let plan = self.plan_iteration_pattern(input.pattern, self.vtype(item))?;
                let pattern = self.apply_pattern(&plan, item)?;
                let value = if let Some(result) = self.block_contents(body, None)? {
                    self.finish_runtime_scope(body, scope, parent_scope, result)?
                } else {
                    let at = self.ctx().last.unwrap();
                    self.ctx_mut().scope = parent_scope;
                    self.diverged(at)
                };
                (value, Some(pattern))
            } else {
                (self.block_expression(body, None)?, None)
            };
        self.p
            .execution
            .edges
            .push(ExecutionEdge::Conditional(ConditionalEdge {
                from: before_body,
                to: body_entry,
                guard,
            }));
        let body_end = self.ctx().last.unwrap();
        self.p.execution.loops[region.0 as usize].body_entry = body_entry;
        let loop_context = self.ctx_mut().loops.pop().unwrap();
        let child_context = self.ctx().clone();
        let mut continuing = loop_context.continues.clone();
        if self.vtype(body_value.value) != self.never {
            self.p
                .execution
                .edges
                .push(ExecutionEdge::LoopBack(LoopBackEdge {
                    from: body_end,
                    to: iteration_entry,
                    region,
                }));
            continuing.push(LoopTransfer {
                at: body_end,
                guard,
                bindings: self.ctx().bindings.clone(),
            });
        }
        for parameter in &mut loop_parameters {
            for path in &continuing {
                let back = path
                    .bindings
                    .get(&parameter.binding)
                    .copied()
                    .unwrap_or(parameter.result);
                parameter.back_edges.push(GuardedValue {
                    guard: path.guard,
                    value: back,
                });
                let dependencies = self.p.values.entries[parameter.result.0 as usize].dependencies;
                let facts = self.guarded_dependencies(back, path.guard);
                self.p.values.dependency_summaries[dependencies.0 as usize]
                    .guarded
                    .extend(facts);
            }
            let reference_inputs = parameter.back_edges.clone();
            self.merge_reference_identities(parameter.result, &reference_inputs, &parameter.site);
            self.emit(Operation::LoopParameter(parameter.clone()));
        }
        self.ctx = Some(Context {
            last: None,
            ..parent.clone()
        });
        self.accumulate_context(&child_context);
        if let (Some(input), Some(header), Some(pattern)) =
            (&iteration, &iteration_header, iteration_pattern)
        {
            let mut bindings = vec![];
            Self::iteration_bindings(&pattern, &mut bindings);
            self.emit(Operation::ForControl(ForControl {
                site: header_site.clone(),
                region,
                source: input.source,
                iteration: header.protocol.clone(),
                pattern,
                bindings,
            }));
        } else if let Some(value) = condition_value {
            self.emit(Operation::WhileControl(WhileControl {
                site: header_site.clone(),
                region,
                condition: value,
            }));
        } else {
            self.emit(Operation::LoopControl(LoopControl {
                site: header_site.clone(),
                region,
            }));
        }
        if condition_value.is_none() && loop_context.breaks.is_empty() {
            self.ctx_mut().last = Some(header);
            return Ok(self.diverged(header));
        }
        let exit_site = self.site(n, ExecutionPhase::Exit);
        let exit = exit_site.execution_moments.first;
        self.p.execution.loops[region.0 as usize].break_target = exit;
        let mut exit_paths = vec![];
        if let Some(value) = condition_value {
            let negative = self.predicate(PredicateKind::Boolean {
                value,
                expected: false,
            });
            let exit_guard = self.predicate(PredicateKind::All(vec![parent.guard, negative]));
            self.p
                .execution
                .edges
                .push(ExecutionEdge::Conditional(ConditionalEdge {
                    from: before_body,
                    to: exit,
                    guard: exit_guard,
                }));
            exit_paths.push((exit_guard, before_body));
        }
        for path in &loop_context.breaks {
            self.p
                .execution
                .edges
                .push(ExecutionEdge::Conditional(ConditionalEdge {
                    from: path.at,
                    to: exit,
                    guard: path.guard,
                }));
            exit_paths.push((path.guard, path.at));
        }
        let moments = exit_paths
            .iter()
            .map(|(guard, moment)| GuardedMoment {
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
                continuation: exit,
            }));
        let result = if condition_value.is_none() {
            let incoming = NonEmpty {
                first: loop_context.results[0].clone(),
                rest: loop_context.results[1..].to_vec(),
            };
            let result = self.merge_values(exit_site, incoming)?;
            if let Some(expected) = expected {
                self.require_type(n, self.vtype(result), expected)?;
            }
            result
        } else {
            let result = self.op_value(&exit_site, self.unit, vec![]);
            self.emit(Operation::UnitValue(UnitValue {
                site: exit_site,
                result,
            }));
            result
        };
        for parameter in &loop_parameters {
            let mut incoming = vec![];
            if condition_value.is_some() {
                incoming.push(GuardedValue {
                    guard: exit_paths[0].0,
                    value: parameter.result,
                });
            }
            for path in &loop_context.breaks {
                incoming.push(GuardedValue {
                    guard: path.guard,
                    value: path
                        .bindings
                        .get(&parameter.binding)
                        .copied()
                        .unwrap_or(parameter.result),
                });
            }
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
            self.ctx_mut().bindings.insert(parameter.binding, value);
        }
        Ok(Expr { value: result })
    }
    fn run(&mut self) -> Result<LogicalDestinationResult> {
        let NodeKind::Module { items } = self.kind(self.syntax.ast.root) else {
            return Err(self.fail(
                self.syntax.ast.root,
                DiagnosticKind::InvalidType,
                "expected a module",
            ));
        };
        if !self.prepared_package {
            self.declare_types(items, ScopeId(0))?;
            self.collect(items, ScopeId(0), None)?;
        }
        let declared = self.functions.len();
        for index in 0..declared {
            let parameters = self.p.declarations.functions[index].type_parameters.clone();
            let actual = parameters
                .iter()
                .map(|p| self.intern(TypeKey::Parameter(*p)))
                .collect();
            let instance = self.specialized_instance(FunctionId(index as u32), actual)?;
            if !parameters.is_empty() {
                self.p.declarations.functions[index].parametric_body = Some(instance);
            }
        }
        self.resolve_entry_point()?;
        // Recursive call edges can target bodies whose exits were not populated at call creation.
        let call_edges = self
            .p
            .execution
            .edges
            .iter()
            .filter_map(|edge| match edge {
                ExecutionEdge::Call(call) => Some(call.clone()),
                _ => None,
            })
            .collect::<Vec<_>>();
        for call in call_edges {
            let callee_body = self.p.execution.execution_moments[call.callee_entry.0 as usize].body;
            let operation = self.p.execution.execution_moments[call.call.0 as usize].operation;
            let continuation = self
                .p
                .bodies
                .iter()
                .flat_map(|b| &b.operations)
                .find(|o| o.site().id == operation)
                .and_then(|o| o.site().execution_moments.rest.last())
                .copied();
            if let Some(continuation) = continuation {
                for exit in self.p.scopes.exits.iter().filter(|exit| {
                    matches!(exit.kind, ScopeExitKind::Return)
                        && self.p.execution.execution_moments[exit.event.0 as usize].body
                            == callee_body
                }) {
                    if !self.p.execution.edges.iter().any(|edge| matches!(edge, ExecutionEdge::Return(r) if r.callee_exit == exit.event && r.instance == call.instance)) {
                        self.p.execution.edges.push(ExecutionEdge::Return(ReturnEdge { callee_exit: exit.event, continuation, instance: call.instance }));
                    }
                }
            }
        }
        let mut constants = self.constant_sources.keys().copied().collect::<Vec<_>>();
        constants.sort_by_key(|id| id.0);
        for constant in constants {
            self.resolve_constant(constant)?;
        }
        let mut address_index = 0;
        while address_index < self.p.objects.addresses.len() {
            let ty = self.p.objects.addresses[address_index].ty;
            self.destructor(ty)?;
            address_index += 1;
        }
        let mut lexical_order = (0..self.p.execution.lexical_moments.len()).collect::<Vec<_>>();
        lexical_order.sort_by_key(|i| {
            let m = &self.p.execution.lexical_moments[*i];
            (m.scope.0, m.ordinal_in_container)
        });
        let mut ordinals = HashMap::new();
        for index in lexical_order {
            let moment = &mut self.p.execution.lexical_moments[index];
            let ordinal = ordinals.entry(moment.scope).or_insert(0);
            moment.ordinal_in_container = *ordinal;
            *ordinal += 1;
        }
        for timeline in &mut self.p.execution.timelines {
            timeline.lexical_order.sort_by_key(|id| {
                let moment = &self.p.execution.lexical_moments[id.0 as usize];
                (moment.scope.0, moment.ordinal_in_container)
            });
        }
        for application in self.p.contracts.applications.clone() {
            if let ContractApplication::Completion {
                capability,
                at,
                guard,
                ..
            } = application
            {
                let points =
                    &mut self.p.contracts.completions[capability.0 as usize].established_at;
                if !points.iter().any(|p| p.moment == at && p.guard == guard) {
                    points.push(GuardedMoment { moment: at, guard });
                }
            }
        }
        self.finish_logical_destinations()
    }

    /// Select the executable entry while names, modules and signatures are
    /// still semantic facts. Later stages receive only the selected instance.
    fn resolve_entry_point(&mut self) -> Result<()> {
        let primary_package = self
            .source_states
            .first()
            .and_then(|state| state.module)
            .map(|module| self.p.declarations.modules[module.0 as usize].package);
        let mut candidates = vec![];
        for definition in &self.p.declarations.functions {
            let symbol = &self.p.symbols.entries[definition.symbol.0 as usize];
            if symbol.spelling != "main" {
                continue;
            }
            let module = self.module_for_scope(symbol.declaring_scope);
            let module = &self.p.declarations.modules[module.0 as usize];
            if Some(module.package) != primary_package || !module.path.is_empty() {
                continue;
            }
            let signature = &self.p.declarations.signatures[definition.signature.0 as usize];
            if !signature.parameters.is_empty()
                || !matches!(signature.execution, FunctionExecution::Synchronous)
            {
                continue;
            }
            candidates.extend(
                self.p
                    .declarations
                    .instances
                    .iter()
                    .filter(|instance| instance.definition == definition.id)
                    .map(|instance| instance.id),
            );
        }
        candidates.sort_by_key(|id| id.0);
        candidates.dedup();
        if candidates.len() > 1 {
            return Err(self.fail(
                self.syntax.ast.root,
                DiagnosticKind::DuplicateDeclaration,
                "the executable package has more than one resolved main entry",
            ));
        }
        self.p.entry_point = candidates.first().copied();
        Ok(())
    }
    fn reachable(&self, from: ExecutionMomentId, to: ExecutionMomentId) -> bool {
        if from == to {
            return true;
        }
        let mut seen = HashSet::new();
        let mut pending = vec![from];
        while let Some(moment) = pending.pop() {
            if !seen.insert(moment) {
                continue;
            }
            for edge in &self.p.execution.edges {
                let candidate = match edge {
                    ExecutionEdge::Sequence(e) if e.before == moment => Some(e.after),
                    ExecutionEdge::Conditional(e) if e.from == moment => Some(e.to),
                    _ => None,
                };
                if let Some(next) = candidate {
                    if next == to {
                        return true;
                    }
                    pending.push(next);
                }
            }
        }
        false
    }
    fn terminal_owners(
        &mut self,
        entity: EntityId,
        visiting: &mut HashSet<EntityId>,
    ) -> Vec<OwnershipLink> {
        if !visiting.insert(entity.clone()) {
            return vec![];
        }
        let owners = self
            .p
            .objects
            .ownership
            .iter()
            .enumerate()
            .filter(|(_, o)| o.entity == entity)
            .map(|(index, link)| (index, link.clone()))
            .collect::<Vec<_>>();
        let mut result = vec![];
        for (index, link) in &owners {
            let later_guards = owners
                .iter()
                .filter(|(later, other)| {
                    later > index
                        && (other.established == link.established
                            || self.reachable(link.established, other.established))
                })
                .map(|(_, other)| other.guard)
                .collect::<Vec<_>>();
            if later_guards.contains(&link.guard) || later_guards.contains(&PredicateId(0)) {
                continue;
            }
            let mut link = link.clone();
            if !later_guards.is_empty() {
                let later = self.predicate(PredicateKind::Any(later_guards));
                let remaining = self.predicate(PredicateKind::Not(later));
                link.guard = self.predicate(PredicateKind::All(vec![link.guard, remaining]));
            }
            if let Owner::Entity(parent) = &link.owner {
                for mut owner in self.terminal_owners(parent.entity.clone(), visiting) {
                    owner.guard = self.predicate(PredicateKind::All(vec![link.guard, owner.guard]));
                    result.push(owner);
                }
            } else {
                result.push(link);
            }
        }
        visiting.remove(&entity);
        result
    }
    fn cleanup_routes(
        &mut self,
        link: &OwnershipLink,
    ) -> Vec<(LogicalScope, LogicalCleanupSite, PredicateId)> {
        let scope = match &link.owner {
            Owner::BorrowedTarget { place, .. } => {
                return vec![(
                    LogicalScope::BorrowedTarget(*place),
                    LogicalCleanupSite::BorrowedTarget(*place),
                    link.guard,
                )];
            }
            Owner::ExecutionBranch { branch, .. } => {
                return vec![(
                    LogicalScope::ExecutionBranch(*branch),
                    LogicalCleanupSite::ExecutionBranchEnd(*branch),
                    link.guard,
                )];
            }
            Owner::FunctionResult { function, .. } => {
                return vec![(
                    LogicalScope::CallerResult(*function),
                    LogicalCleanupSite::CallerResult(*function),
                    link.guard,
                )];
            }
            Owner::Binding { binding, .. } => self.p.scopes.bindings[binding.0 as usize].scope,
            Owner::Scope { scope, .. } => *scope,
            _ => return vec![],
        };
        let exits = self.p.scopes.entries[scope.0 as usize].exits.clone();
        if exits.is_empty() {
            return vec![(
                LogicalScope::Local(scope),
                LogicalCleanupSite::NoReachableExit(scope),
                link.guard,
            )];
        }
        exits
            .into_iter()
            .map(|exit| {
                let exit_guard = self.p.scopes.exits[exit.0 as usize].guard;
                let guard = self.predicate(PredicateKind::All(vec![link.guard, exit_guard]));
                (
                    LogicalScope::Local(scope),
                    LogicalCleanupSite::Exit(exit),
                    guard,
                )
            })
            .collect()
    }
    fn finish_logical_destinations(&mut self) -> Result<LogicalDestinationResult> {
        let mut finals = vec![];
        let mut requirements = vec![];
        let mut physical = vec![];
        let addresses = self.p.objects.addresses.clone();
        for address in &addresses {
            if matches!(address.creation, ObjectCreation::Static(_)) {
                continue;
            }
            let owners = self.terminal_owners(EntityId::Address(address.id), &mut HashSet::new());
            for link in &owners {
                let routes = self.cleanup_routes(link);
                for (scope, cleanup_exit, guard) in routes {
                    let value = self.address_values[address.id.0 as usize];
                    let id = DestinationRequirementId(requirements.len() as u32);
                    let construction = match address.creation {
                        ObjectCreation::At(m) => m,
                        ObjectCreation::Static(_) => continue,
                    };
                    let dependencies = self.p.values.entries[value.0 as usize].dependencies;
                    let candidate = DestinationCandidate {
                        scope: scope.clone(),
                        receiver: link.owner.clone(),
                        guard,
                        cleanup_exit: cleanup_exit.clone(),
                        choice: PathChoiceTiming::SingleDestination,
                    };
                    requirements.push(FinalDestinationRequirement {
                        id,
                        value,
                        candidates: NonEmpty {
                            first: candidate,
                            rest: vec![],
                        },
                        construction,
                        address_stability:
                            AddressStabilityRequirement::ChooseOnceBeforeConstruction,
                        dependencies,
                    });
                    let destination = FinalDestinationId(finals.len() as u32);
                    finals.push(LogicalFinalDestination {
                        id: destination,
                        requirement: id,
                        value,
                        scope: scope.clone(),
                        cleanup_owner: link.owner.clone(),
                        cleanup_exit,
                        guard,
                        choice: PathChoiceTiming::SingleDestination,
                        address_stability:
                            AddressStabilityRequirement::ChooseOnceBeforeConstruction,
                    });
                    if let LogicalScope::Local(scope) = scope {
                        if scope != address.created_in {
                            physical.push(PhysicalPlacementRequirement {
                                id: PhysicalPlacementRequirementId(physical.len() as u32),
                                destination,
                                kind: PhysicalPlacementRequirementKind::ReserveBeforeScopeEntry(
                                    address.created_in,
                                ),
                                guard,
                                origin: self.p.execution.execution_moments[construction.0 as usize]
                                    .lexical_origin(&self.p),
                            });
                        }
                    }
                }
            }
        }
        let mut priority = vec![];
        for final_ in &finals {
            if let LogicalScope::Local(scope) = final_.scope {
                if let Some(p) = priority
                    .iter_mut()
                    .find(|p: &&mut DestinationPriority| p.scope == scope)
                {
                    if !p.attracted_values.contains(&final_.value) {
                        p.attracted_values.push(final_.value);
                    }
                } else {
                    priority.push(DestinationPriority {
                        scope,
                        attracted_values: vec![final_.value],
                    });
                }
            }
        }
        priority.sort_by_key(|p| std::cmp::Reverse(p.attracted_values.len()));
        let mut coverage = vec![];
        for unit in 0..self.units.len() {
            self.switch_unit(unit);
            let pending_coverage = std::mem::take(&mut self.coverage);
            for (n, entries) in pending_coverage {
                let mut entries = entries.into_iter();
                if let Some(first) = entries.next() {
                    let origin = self.origin(n);
                    coverage.push(SyntaxPopulationEntry {
                        syntax: self.syntax_id(n),
                        origin,
                        dispositions: NonEmpty {
                            first,
                            rest: entries.collect(),
                        },
                    });
                }
            }
        }
        coverage.sort_by_key(|e| e.syntax.0);
        let mut definitions = vec![];
        let mut cleanup_candidates = vec![];
        for address in &self.p.objects.addresses {
            if let ObjectCreation::At(moment) = address.creation {
                let event = &self.p.execution.execution_moments[moment.0 as usize];
                let instance = event.instance;
                definitions.push(EntityDefinitionMoment {
                    entity: EntityOccurrence {
                        entity: EntityId::Address(address.id),
                        instance,
                    },
                    created_at: MomentOccurrence {
                        moment,
                        context: instance,
                    },
                    origin: event.lexical_origin(&self.p),
                });
            }
        }
        for reference in &self.p.objects.references {
            if let ObjectCreation::At(moment) = reference.creation {
                let event = &self.p.execution.execution_moments[moment.0 as usize];
                definitions.push(EntityDefinitionMoment {
                    entity: EntityOccurrence {
                        entity: EntityId::Reference(reference.id),
                        instance: event.instance,
                    },
                    created_at: MomentOccurrence {
                        moment,
                        context: event.instance,
                    },
                    origin: event.lexical_origin(&self.p),
                });
            }
        }
        self.populate_lifetime_obligations(&finals);
        for requirement in &mut self.lifetime_requirements {
            for usage in &self.lifetime_uses {
                if usage.entity.entity == requirement.dependent.entity
                    && !requirement
                        .uses
                        .rest
                        .iter()
                        .any(|m| m.moment == usage.at.moment)
                {
                    requirement.uses.rest.push(GuardedMoment {
                        guard: usage.guard,
                        moment: usage.at.moment,
                    });
                }
            }
        }
        for final_ in &finals {
            if let LogicalCleanupSite::Exit(exit) = final_.cleanup_exit {
                if let Some(entity) = self.value_entities.get(&final_.value).cloned() {
                    let instance = match &final_.cleanup_owner {
                        Owner::Binding { instance, .. }
                        | Owner::Scope { instance, .. }
                        | Owner::FunctionResult { instance, .. }
                        | Owner::BorrowedTarget { instance, .. }
                        | Owner::ExecutionBranch { instance, .. } => *instance,
                        Owner::Entity(e) => e.instance,
                    };
                    cleanup_candidates.push(CleanupCandidate {
                        id: CleanupCandidateId(cleanup_candidates.len() as u32),
                        entity: EntityOccurrence { entity, instance },
                        owner: final_.cleanup_owner.clone(),
                        exit,
                        guard: final_.guard,
                    });
                }
            }
        }
        for final_ in &finals {
            let placement = self.p.values.entries[final_.value.0 as usize].placement;
            let binding = match final_.cleanup_owner {
                Owner::Binding { binding, .. } => Some(binding),
                _ => None,
            };
            self.p.values.placement_summaries[placement.0 as usize]
                .destinations
                .push(GuardedDestination {
                    guard: final_.guard,
                    scope: final_.scope.clone(),
                    binding,
                });
        }
        self.populate_transfer_obligations();
        self.populate_operation_type_obligations();
        self.populate_access_obligations();
        self.populate_boundary_obligations();
        self.populate_match_coverage_obligations();
        self.populate_ownership_and_cleanup_obligations(&cleanup_candidates);
        let result_contracts: Vec<CallResultStorageContract> = self
            .p
            .declarations
            .instances
            .iter()
            .filter_map(|function| {
                let alternatives = function
                    .result
                    .values
                    .iter()
                    .map(|v| {
                        let source = self
                            .value_entities_at(v.value, v.guard)
                            .into_iter()
                            .find_map(|(_, e)| match e {
                                EntityId::Address(a)
                                    if matches!(
                                        self.p.values.entries
                                            [self.address_values[a.0 as usize].0 as usize]
                                            .definition,
                                        ValueDefinition::Parameter(_)
                                    ) =>
                                {
                                    Some(self.p.objects.addresses[a.0 as usize].storage)
                                }
                                _ => None,
                            });
                        GuardedResultStorage {
                            guard: v.guard,
                            mode: match source {
                                Some(origin) => ResultStorageMode::TransferExisting {
                                    value: v.value,
                                    origin,
                                },
                                None => ResultStorageMode::ConstructIntoCallerReservation {
                                    result: self.vtype(v.value),
                                },
                            },
                        }
                    })
                    .collect::<Vec<_>>();
                let first = alternatives.first()?.clone();
                Some(CallResultStorageContract {
                    function: function.id,
                    alternatives: NonEmpty {
                        first,
                        rest: alternatives[1..].to_vec(),
                    },
                })
            })
            .collect();
        // A newly constructed call result is physically supplied by its
        // caller. This is a planning requirement derived from the already
        // resolved call target/result identity; the planner never rediscovers
        // it from syntax or function names.
        let calls = self
            .p
            .bodies
            .iter()
            .flat_map(|body| &body.operations)
            .filter_map(|operation| match operation {
                Operation::DirectCall(call) => {
                    Some((call.site.id, call.target, call.result, call.site.origin))
                }
                Operation::MethodCall(call) => match call.target.target {
                    MethodTarget::Concrete(target) => {
                        Some((call.site.id, target, call.result, call.site.origin))
                    }
                    MethodTarget::ContractAlternatives(_)
                    | MethodTarget::ContractRequirement { .. } => None,
                },
                Operation::ExternalCall(call) => Some((
                    call.site.id,
                    call.target.function,
                    call.result,
                    call.site.origin,
                )),
                _ => None,
            })
            .collect::<Vec<_>>();
        for (call, target, result, origin) in calls {
            let constructs = result_contracts
                .iter()
                .find(|contract: &&CallResultStorageContract| contract.function == target)
                .is_some_and(|contract| {
                    std::iter::once(&contract.alternatives.first)
                        .chain(&contract.alternatives.rest)
                        .any(|alternative| {
                            matches!(
                                alternative.mode,
                                ResultStorageMode::ConstructIntoCallerReservation { .. }
                            )
                        })
                });
            if !constructs {
                continue;
            }
            let result_entity = self.value_entities.get(&result).cloned();
            for destination in &finals {
                let same_identity = destination.value == result
                    || result_entity.as_ref().is_some_and(|entity| {
                        self.value_entities.get(&destination.value) == Some(entity)
                    });
                if same_identity
                    && !physical.iter().any(|requirement| {
                        requirement.destination == destination.id
                            && matches!(
                                requirement.kind,
                                PhysicalPlacementRequirementKind::CallerProvided {
                                    call: candidate
                                } if candidate == call
                            )
                    })
                {
                    physical.push(PhysicalPlacementRequirement {
                        id: PhysicalPlacementRequirementId(physical.len() as u32),
                        destination: destination.id,
                        kind: PhysicalPlacementRequirementKind::CallerProvided { call },
                        guard: destination.guard,
                        origin,
                    });
                }
            }
        }
        for index in 0..self.p.values.entries.len() {
            let value = ValueId(index as u32);
            for (guard, entity) in self.value_entities_at(value, PredicateId(0)) {
                self.p.objects.value_entities.push(ValueEntityIdentity {
                    value,
                    entity,
                    guard,
                });
            }
        }
        let target = self.p.target.clone();
        let p = std::mem::replace(&mut self.p, empty_post_ast(target, String::new()));
        let semantic = SemanticPopulationResult {
            post_ast: p,
            type_derivations: std::mem::take(&mut self.type_derivations),
            lifetimes: LifetimeFacts {
                definitions,
                uses: std::mem::take(&mut self.lifetime_uses),
                cleanup_candidates,
                requirements: std::mem::take(&mut self.lifetime_requirements),
                deferred_uses: vec![],
            },
            destinations: DestinationRequirements {
                transfers: std::mem::take(&mut self.transfers),
                finals: requirements,
                result_contracts,
            },
            coverage: PopulationCoverage { entries: coverage },
        };
        Ok(LogicalDestinationResult {
            semantics: semantic,
            finals,
            physical_requirements: physical,
            priority,
        })
    }
}
impl ExecutionMoment {
    fn lexical_origin(&self, p: &PostAst) -> SourceOriginId {
        p.execution.lexical_moments[self.lexical.0 as usize].origin
    }
}
