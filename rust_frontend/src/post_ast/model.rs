//! Canonical typed PostAST data. Populated by semantic resolution.
//! No rule checker, physical memory planner or C++ emitter lives here.
//! Architecture: docs/architecture/POST_AST_APPROACH.md.
#![allow(dead_code)]

/// A grammar requirement with at least one member; not a proof of validity.
#[derive(Clone, Debug)]
pub struct NonEmpty<T> {
    pub first: T,
    pub rest: Vec<T>,
}

/// Distinct identifier types prevent accidental cross-table substitution.

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct PackageId(pub u32);
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ConfigurationId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ModuleId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct SourceFileId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct SyntaxNodeId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct SourceOriginId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct SymbolId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct TypeId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct TypeParameterId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct FieldId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct VariantId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct FunctionId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct FunctionInstanceId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct SignatureId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct AbiId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ConstantId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct BodyId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ScopeId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ScopeExitId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct BindingId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ValueId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct PlaceId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct EvaluatedPlaceId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct AddressId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ReferenceId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct CollectionId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct OwnershipLinkId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct CleanupCandidateId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct PositionId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ProvenanceId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct DependencySummaryId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct PlacementSummaryId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct StorageOriginId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct OperationId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct TimelineId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct LexicalMomentId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ExecutionMomentId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct BranchId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct PredicateId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct LoopRegionId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct SuspensionId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct InstanceDomainId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct EffectSummaryId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct TypeContractId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ContractAlternativeId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ContractMatchId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct BranchContractId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct CompletionCapabilityId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct LockContractId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct LockIdentityId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ThreadContractId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct CaptureRecordId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct DestructorId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct CheckId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ObligationId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ProofId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct LayoutId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct StorageReservationId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct DataStackId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct RegionId(pub u32);
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct RegionClassId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct CursorExpressionId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct CursorSnapshotId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ScopeStorageId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ForeignRegionId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct IntrinsicId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct RuntimeEntryId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct TransferOccurrenceId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct DependencyLinkId(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct LifetimeRequirementId(pub u32);

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct FinalDestinationId(pub u32);

/// The resolved semantic source shared by validation and subsequent planning.
#[derive(Debug, Clone)]
pub struct PostAst {
    pub specification: SpecificationIdentity,
    pub target: TargetDescription,
    /// Executable package entry selected by semantic resolution. Backends must
    /// never recover it by matching the spelling `main` again.
    pub entry_point: Option<FunctionInstanceId>,
    pub origins: SourceOrigins,
    pub declarations: Declarations,
    pub symbols: Symbols,
    pub types: ResolvedTypes,
    pub scopes: Scopes,
    pub objects: Objects,
    pub storage_origins: Vec<StorageOrigin>,
    pub cursor_expressions: Vec<CursorExpression>,
    pub cursor_snapshots: Vec<CursorSnapshot>,
    pub datastacks: Vec<LogicalDataStack>,
    pub async_frames: Vec<AsyncFrame>,
    pub handle_protocols: Vec<HandleProtocol>,
    pub values: Values,
    pub execution: ExecutionGraph,
    pub contracts: Contracts,
    pub bodies: Vec<FunctionBody>,
    pub effects: Vec<EffectSummary>,
    /// Canonical inventory of every resolved semantic transfer. N3 consumes
    /// these occurrences; it never rediscovers transfers from source syntax.
    pub transfers: Vec<ResolvedTransferOccurrence>,
    pub obligations: RuleObligations,
    pub runtime_checks: Vec<RuntimeCheck>,
    pub foreign_regions: Vec<ForeignRegion>,
    /// Diagnosed source excluded by a proven control-flow terminator. It has no executable values.
    pub unreachable_source: UnreachableSource,
    pub match_coverage: Vec<MatchCoverageRequirement>,
    pub well_known: WellKnownTypes,
}

#[derive(Debug, Clone)]
pub struct SpecificationIdentity {
    pub grammar_fingerprint: String,
    pub rules_revision: String,
}

#[derive(Debug, Clone)]
pub struct TargetDescription {
    pub os: String,
    pub family: String,
    pub architecture: String,
    pub pointer_bits: u16,
    pub endian: Endian,
    pub abi: AbiId,
}
#[derive(Debug, Clone)]
pub enum Endian {
    Little,
    Big,
}
#[derive(Debug, Clone)]
pub struct ByteSpan {
    pub start: u32,
    pub end: u32,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct LexicalScopeId(pub u32);
#[derive(Debug, Clone)]
pub struct LexicalScope {
    pub id: LexicalScopeId,
    pub file: SourceFileId,
    pub parent: Option<LexicalScopeId>,
    pub span: ByteSpan,
}
#[derive(Debug, Clone)]
pub struct SourceOrigins {
    pub files: Vec<SourceFile>,
    pub origins: Vec<SourceOrigin>,
    pub lexical_scopes: Vec<LexicalScope>,
}
#[derive(Debug, Clone)]
pub struct SourceFile {
    pub id: SourceFileId,
    pub path: String,
    pub source: String,
}
#[derive(Debug, Clone)]
pub struct SourceOrigin {
    pub id: SourceOriginId,
    pub role: OriginRole,
}
#[derive(Debug, Clone)]
pub enum OriginRole {
    Written {
        file: SourceFileId,
        syntax: SyntaxNodeId,
        span: ByteSpan,
        lexical: LexicalMomentId,
    },
    Synthesized {
        cause: SourceOriginId,
        reason: SynthesisReason,
        lexical: LexicalMomentId,
    },
    /// Compiler-provided definitions have no invented source instruction.
    CompilerProvided { description: String },
}
#[derive(Debug, Clone)]
pub enum SynthesisReason {
    DefaultField,
    ImplicitPrimitiveCopy,
    ImplicitEnumCopy,
    ScopeExitCleanup,
    PatternExtraction,
    CallableCapture,
    ResultForwarding,
    ContractEffect,
    RuntimeCheck,
    ImplicitUnit,
    SuspensionStorage,
}

// ---------- Timelines and moments: mandatory, not reconstructed later. ----------
#[derive(Debug, Clone)]
pub struct ExecutionGraph {
    pub timelines: Vec<Timeline>,
    pub lexical_moments: Vec<LexicalMoment>,
    pub execution_moments: Vec<ExecutionMoment>,
    pub branches: Vec<Branch>,
    pub relationships: Vec<BranchRelationship>,
    pub edges: Vec<ExecutionEdge>,
    pub predicates: Vec<PathPredicate>,
    pub loops: Vec<LoopRegion>,
    pub suspensions: Vec<SuspensionPoint>,
    pub instance_domains: Vec<InstanceDomain>,
    pub iteration_variables: Vec<IterationVariable>,
}
#[derive(Debug, Clone)]
pub struct Timeline {
    pub id: TimelineId,
    pub branch: BranchId,
    /// Written order only. Does not establish execution precedence.
    pub lexical_order: Vec<LexicalMomentId>,
    /// Event membership. Vec position is NOT execution order.
    pub execution_moments: Vec<ExecutionMomentId>,
    pub entries: NonEmpty<ExecutionMomentId>,
    pub exits: Vec<ExecutionMomentId>,
}
#[derive(Debug, Clone)]
pub struct LexicalMoment {
    pub id: LexicalMomentId,
    pub container: LexicalContainer,
    pub scope: LexicalScopeId,
    pub ordinal_in_container: u32,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub enum LexicalContainer {
    Module(ModuleId),
    TypeDefinition(TypeId),
    FunctionBody(BodyId),
    FunctionDefinition(FunctionId),
    ConstantExpression(ConstantId),
    Contract(TypeContractId),
}

#[derive(Debug, Clone)]
pub struct ExecutionMoment {
    pub id: ExecutionMomentId,
    pub instance: InstanceDomainId,
    pub body: BodyId,
    pub timeline: TimelineId,
    pub branch: BranchId,
    pub lexical: LexicalMomentId,
    pub operation: OperationId,
    pub phase: ExecutionPhase,
    pub guard: PredicateId,
}
#[derive(Debug, Clone)]
pub enum ExecutionPhase {
    Enter,
    Evaluate,
    Read,
    Compute,
    Write,
    Invoke,
    Receive,
    TransferOwnership,
    EstablishEffect,
    Suspend,
    Resume,
    Destroy,
    Exit,
}

/// A hierarchical coordinate: the parent-linked context supplies loop/call/
/// task steps; moment identifies the event within that context. Not a number.
#[derive(Debug, Clone)]
pub struct MomentOccurrence {
    pub moment: ExecutionMomentId,
    pub context: InstanceDomainId,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct IterationVariableId(pub u32);
#[derive(Debug, Clone)]
pub struct IterationVariable {
    pub id: IterationVariableId,
    pub region: LoopRegionId,
}
/// Known only when this occurrence's iteration is statically established.
/// A known total iteration count does not itself enumerate the occurrences.
#[derive(Debug, Clone)]
pub enum IterationCoordinate {
    Known(u64),
    Symbolic(IterationVariableId),
}
#[derive(Debug, Clone)]
pub struct IterationMoment {
    pub region: LoopRegionId,
    pub iteration: IterationCoordinate,
}
#[derive(Debug, Clone)]
pub struct InstanceDomain {
    pub id: InstanceDomainId,
    pub definition: InstanceDomainDefinition,
}
#[derive(Debug, Clone)]
pub enum InstanceDomainDefinition {
    Root {
        body: BodyId,
    },
    Call {
        parent: InstanceDomainId,
        call: OperationId,
        callee: BodyId,
    },
    Iteration {
        parent: InstanceDomainId,
        moment: IterationMoment,
    },
    Concurrent {
        parent: InstanceDomainId,
        branch: BranchId,
    },
    AsyncInstance {
        parent: InstanceDomainId,
        task: ValueId,
    },
}
#[derive(Debug, Clone)]
pub struct Branch {
    pub id: BranchId,
    pub timeline: TimelineId,
    pub kind: BranchKind,
}
#[derive(Debug, Clone)]
pub enum BranchKind {
    Root(RootBranch),
    Conditional(ConditionalBranch),
    MatchArm(MatchArmBranch),
    Concurrent(ConcurrentBranch),
}
#[derive(Debug, Clone)]
pub struct RootBranch {
    pub body: BodyId,
}
#[derive(Debug, Clone)]
pub struct ConditionalBranch {
    pub parent: BranchId,
    pub decision: OperationId,
    pub guard: PredicateId,
}
#[derive(Debug, Clone)]
pub struct MatchArmBranch {
    pub parent: BranchId,
    pub decision: OperationId,
    pub variant_guard: PredicateId,
    pub bindings: Vec<BindingId>,
}
#[derive(Debug, Clone)]
pub struct ConcurrentBranch {
    pub parent: BranchId,
    pub start: OperationId,
    pub contract: BranchContractId,
    pub completion: CompletionCapabilityId,
}
#[derive(Debug, Clone)]
pub enum BranchRelationship {
    Exclusive(ExclusiveBranches),
    Fork(BranchFork),
    Merge(BranchMerge),
    Completion(BranchCompletion),
}
#[derive(Debug, Clone)]
pub struct ExclusiveBranches {
    pub decision: OperationId,
    pub branches: NonEmpty<BranchId>,
}
#[derive(Debug, Clone)]
pub struct BranchFork {
    pub parent: BranchId,
    pub child: BranchId,
    pub parent_moment: ExecutionMomentId,
    pub child_entry: ExecutionMomentId,
}
#[derive(Debug, Clone)]
pub struct BranchMerge {
    pub incoming: NonEmpty<GuardedMoment>,
    pub continuation: ExecutionMomentId,
}
#[derive(Debug, Clone)]
pub struct BranchCompletion {
    pub branch: BranchId,
    pub established_by: CompletionCapabilityId,
    pub completing_event: ExecutionMomentId,
    pub continuation: ExecutionMomentId,
    pub outcome: PredicateId,
}
#[derive(Debug, Clone)]
pub struct GuardedMoment {
    pub guard: PredicateId,
    pub moment: ExecutionMomentId,
}
#[derive(Debug, Clone)]
pub enum ExecutionEdge {
    Sequence(SequenceEdge),
    Conditional(ConditionalEdge),
    LoopBack(LoopBackEdge),
    Call(CallEdge),
    Return(ReturnEdge),
    Suspend(SuspendEdge),
    Resume(ResumeEdge),
    PollRetry {
        from: ExecutionMomentId,
        poll: ExecutionMomentId,
        suspension: SuspensionId,
    },
    AwaitBody {
        poll: ExecutionMomentId,
        entry: ExecutionMomentId,
        instance: InstanceDomainId,
        future: ValueId,
    },
}
#[derive(Debug, Clone)]
pub struct SequenceEdge {
    pub before: ExecutionMomentId,
    pub after: ExecutionMomentId,
}
#[derive(Debug, Clone)]
pub struct ConditionalEdge {
    pub from: ExecutionMomentId,
    pub to: ExecutionMomentId,
    pub guard: PredicateId,
}
#[derive(Debug, Clone)]
pub struct LoopBackEdge {
    pub from: ExecutionMomentId,
    pub to: ExecutionMomentId,
    pub region: LoopRegionId,
}
#[derive(Debug, Clone)]
pub struct CallEdge {
    pub call: ExecutionMomentId,
    pub callee_entry: ExecutionMomentId,
    pub instance: InstanceDomainId,
}
#[derive(Debug, Clone)]
pub struct ReturnEdge {
    pub callee_exit: ExecutionMomentId,
    pub continuation: ExecutionMomentId,
    pub instance: InstanceDomainId,
}
#[derive(Debug, Clone)]
pub struct SuspendEdge {
    pub from: ExecutionMomentId,
    pub point: SuspensionId,
}
#[derive(Debug, Clone)]
pub struct ResumeEdge {
    pub point: SuspensionId,
    pub to: ExecutionMomentId,
    pub guard: PredicateId,
}
#[derive(Debug, Clone)]
pub struct PathPredicate {
    pub id: PredicateId,
    pub kind: PredicateKind,
}
#[derive(Debug, Clone)]
pub enum PredicateKind {
    TypeCopiesByValue(TypeId),
    ValidTextRange {
        source: EvaluatedPlaceId,
        start: ValueId,
        end: ValueId,
    },
    DestructorVariant {
        destructor: DestructorId,
        variant: VariantId,
    },
    RuntimeReady {
        operation: OperationId,
    },
    PollReady {
        source: ValueId,
    },
    Pattern {
        subject: ValueId,
        test: PatternTest,
    },
    Always,
    Boolean {
        value: ValueId,
        expected: bool,
    },
    Variant {
        value: ValueId,
        variant: VariantId,
    },
    All(Vec<PredicateId>),
    Any(Vec<PredicateId>),
    Not(PredicateId),
}
#[derive(Debug, Clone)]
pub struct LoopRegion {
    pub id: LoopRegionId,
    pub branch: BranchId,
    pub header: ExecutionMomentId,
    pub body_entry: ExecutionMomentId,
    pub continue_target: ExecutionMomentId,
    pub break_target: ExecutionMomentId,
    pub instance: InstanceDomainId,
}
#[derive(Debug, Clone)]
pub struct SuspensionPoint {
    pub id: SuspensionId,
    pub suspend: ExecutionMomentId,
    pub resumptions: NonEmpty<GuardedMoment>,
    pub live_values: Vec<ValueId>,
    pub live_places: Vec<EvaluatedPlaceId>,
    pub effects: EffectSummaryId,
}

// ---------- Declarations, symbols and resolved types. ----------
#[derive(Debug, Clone)]
pub struct Declarations {
    pub defaults: Vec<DefaultInitializationPlan>,
    pub native_bindings: Vec<NativeTypeBinding>,
    pub native_namespaces: Vec<NativeNamespaceBinding>,
    pub imports: Vec<ResolvedImport>,
    pub packages: Vec<PackageDefinition>,
    pub modules: Vec<ModuleDefinition>,
    pub functions: Vec<FunctionDefinition>,
    pub overloads: Vec<FunctionOverloadSet>,
    pub instances: Vec<FunctionInstance>,
    pub structs: Vec<StructDefinition>,
    pub enums: Vec<EnumDefinition>,
    pub constants: Vec<ConstantDefinition>,
    pub fields: Vec<FieldDefinition>,
    pub variants: Vec<VariantDefinition>,
    pub signatures: Vec<Signature>,
    pub compile_time_selections: Vec<TargetSelection>,
}
#[derive(Debug, Clone)]
pub struct PackageDefinition {
    pub name: String,
    pub id: PackageId,
    pub modules: Vec<ModuleId>,
}
#[derive(Debug, Clone)]
pub struct ModuleDefinition {
    pub path: Vec<String>,
    pub id: ModuleId,
    pub package: PackageId,
    pub scope: ScopeId,
}
#[derive(Debug, Clone)]
pub struct Symbols {
    pub entries: Vec<Symbol>,
    pub aliases: Vec<SymbolAlias>,
}
#[derive(Debug, Clone)]
pub struct Symbol {
    pub id: SymbolId,
    pub spelling: String,
    pub declaring_scope: ScopeId,
    pub origin: SourceOriginId,
    pub visibility: Visibility,
    pub definition: SymbolDefinition,
}
#[derive(Debug, Clone)]
pub enum Visibility {
    Private,
    Public,
}
#[derive(Debug, Clone)]
pub enum SymbolDefinition {
    RuntimePrimitive(RuntimePrimitiveKind),
    Overloads(OverloadSetId),
    Binding(BindingId),
    DiagnosticBinding(DiagnosticBindingId),
    Function(FunctionId),
    Type(TypeId),
    Constant(ConstantId),
    Field(FieldId),
    Variant(VariantId),
    Module(ModuleId),
    TypeParameter(TypeParameterId),
}
#[derive(Debug, Clone)]
pub struct SymbolAlias {
    pub symbol: SymbolId,
    pub target: SymbolId,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub struct FunctionDefinition {
    pub parametric_body: Option<FunctionInstanceId>,
    pub id: FunctionId,
    pub symbol: SymbolId,
    pub signature: SignatureId,
    pub type_parameters: Vec<TypeParameterId>,
    pub body: FunctionImplementation,
    pub contracts: Vec<ResolvedContract>,
}
#[derive(Debug, Clone)]
pub enum FunctionImplementation {
    Runtime(RuntimeLaunchKind),
    RuntimeJoin,
    ParametricDestructor {
        ty: TypeId,
    },
    EmptyDestructor {
        ty: TypeId,
    },
    Template {
        origin: SourceOriginId,
        syntax: SyntaxNodeId,
    },
    Defined(BodyId),
    External {
        abi: AbiId,
    },
    Intrinsic(IntrinsicId),
}
#[derive(Debug, Clone)]
pub struct FunctionInstance {
    pub resolution: InstanceResolution,
    pub configuration: ConfigurationId,
    pub id: FunctionInstanceId,
    pub contract_matches: Vec<ContractMatchId>,
    pub contracts: Vec<ResolvedContract>,
    /// Concrete body belongs to this specialization, never to a shared template.
    pub body: Option<BodyId>,
    pub definition: FunctionId,
    pub substitutions: Vec<TypeSubstitution>,
    pub signature: SignatureId,
    pub effects: EffectSummaryId,
    /// Reserved before resolving the body; recursive applications link here by instance ID.
    pub result: FunctionResultSummary,
}
#[derive(Debug, Clone)]
pub struct FunctionResultSummary {
    pub native: Option<NativeReturnRecipe>,
    pub values: Vec<GuardedValue>,
    pub dependencies: DependencySummaryId,
}
#[derive(Debug, Clone)]
pub struct TypeSubstitution {
    pub parameter: TypeParameterId,
    pub actual: TypeId,
}
#[derive(Debug, Clone)]
pub struct Signature {
    pub id: SignatureId,
    pub receiver: ReceiverMode,
    pub parameters: Vec<ParameterDefinition>,
    pub result: TypeId,
    pub execution: FunctionExecution,
}
#[derive(Debug, Clone)]
pub enum FunctionExecution {
    Synchronous,
    Asynchronous,
}
#[derive(Debug, Clone)]
pub enum ReceiverMode {
    None,
    ByValue(TypeId),
    Shared(TypeId),
    Mutable(TypeId),
}
#[derive(Debug, Clone)]
pub struct ParameterDefinition {
    pub identity: ParameterIdentity,
    pub ty: TypeId,
}
#[derive(Debug, Clone)]
pub enum ParameterIdentity {
    Named {
        symbol: SymbolId,
        binding: BindingId,
    },
    Anonymous,
}
#[derive(Debug, Clone)]
pub struct StructDefinition {
    pub symbol: SymbolId,
    pub parameters: Vec<TypeParameterId>,
    pub ty: TypeId,
    pub fields: Vec<FieldId>,
    pub methods: Vec<FunctionId>,
}
#[derive(Debug, Clone)]
pub struct EnumDefinition {
    pub symbol: SymbolId,
    pub parameters: Vec<TypeParameterId>,
    pub ty: TypeId,
    pub variants: NonEmpty<VariantId>,
    pub methods: Vec<FunctionId>,
}
#[derive(Debug, Clone)]
pub struct FieldDefinition {
    pub id: FieldId,
    pub symbol: SymbolId,
    pub ty: TypeId,
    pub default: FieldDefault,
}
#[derive(Debug, Clone)]
pub enum FieldDefault {
    Resolved(DefaultPlanId),
    Unavailable,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct DefaultPlanId(pub u32);
#[derive(Debug, Clone)]
pub struct DefaultInitializationPlan {
    pub id: DefaultPlanId,
    pub ty: TypeId,
    pub kind: DefaultInitializationKind,
}
#[derive(Debug, Clone)]
pub enum DefaultInitializationKind {
    EmptyNative,
    Constant(ConstantValue),
    Struct(Vec<FieldDefaultStep>),
    Variant {
        variant: VariantId,
        fields: Vec<FieldDefaultStep>,
    },
    Tuple(Vec<DefaultPlanId>),
    Array {
        element: DefaultPlanId,
        count: u64,
    },
    Intrinsic(IntrinsicId),
}
#[derive(Debug, Clone)]
pub struct FieldDefaultStep {
    pub field: FieldId,
    pub plan: DefaultPlanId,
}

#[derive(Debug, Clone)]
pub struct VariantDefinition {
    pub id: VariantId,
    pub template: Option<VariantId>,
    pub symbol: SymbolId,
    pub owner: TypeId,
    pub fields: Vec<FieldId>,
}
#[derive(Debug, Clone)]
pub struct ConstantDefinition {
    pub id: ConstantId,
    pub symbol: SymbolId,
    pub ty: TypeId,
    pub value: ConstantValue,
    pub configurable: bool,
}
#[derive(Debug, Clone)]
pub enum IntegerConstant {
    Signed(i128),
    Unsigned(u128),
}
#[derive(Debug, Clone)]
pub enum FloatConstant {
    F32Bits(u32),
    F64Bits(u64),
}

#[derive(Debug, Clone, PartialEq)]
pub enum ConstantValue {
    Integer(i128),
    Unsigned(u128),
    Float32(u32),
    Float64(u64),
    Boolean(bool),
    Utf8(Vec<u8>),
    Unit,
}
#[derive(Debug, Clone)]
pub struct TargetSelection {
    pub origin: SourceOriginId,
    pub selected: Vec<SourceOriginId>,
    pub excluded: Vec<SourceOriginId>,
}
#[derive(Debug, Clone)]
pub struct ResolvedTypes {
    pub entries: Vec<ResolvedType>,
    pub parameters: Vec<TypeParameter>,
}
#[derive(Debug, Clone)]
pub struct TypeParameter {
    pub id: TypeParameterId,
    pub symbol: SymbolId,
    pub constraints: Vec<TypeContractId>,
}
#[derive(Debug, Clone)]
pub struct ResolvedType {
    pub id: TypeId,
    pub kind: TypeDefinition,
}
#[derive(Debug, Clone)]
pub enum TypeDefinition {
    ContractFuture {
        target: MethodTarget,
        signature: SignatureId,
        result: TypeId,
    },
    /// Internal control-flow bottom, with no runtime data or layout.
    Never,
    Numeric(NumericType),
    /// Compiler-provided failure carrier for exact numeric try_from.
    NumericConversionError,
    Boolean,
    Unit,
    Utf8View,
    /// Unsized UTF-8 data targeted by an explicit &str reference.
    StrData,
    Nominal {
        configuration: ConfigurationId,
        definition: SymbolId,
        arguments: Vec<TypeArgument>,
    },
    Reference {
        permission: ReferencePermission,
        target: TypeId,
    },
    Tuple(Vec<TypeId>),
    Array {
        element: TypeId,
        length: u64,
    },
    Slice {
        element: TypeId,
    },
    Callable(SignatureId),
    Closure {
        signature: SignatureId,
        captures: CaptureRecordId,
    },
    Future {
        body: BodyId,
        result: TypeId,
        state: TypeId,
    },
    Allocation {
        content: TypeId,
    },
    GrowingSequence {
        element: TypeId,
    },
    KeyedCollection {
        key: TypeId,
        value: TypeId,
    },
    GrowingString,
    InlineUtf8 {
        maximum_bytes: u64,
    },
    ExecutionHandle {
        result: TypeId,
        asynchronous: bool,
    },
    Pool {
        element: TypeId,
    },
    Parameter(TypeParameterId),
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TypeArgument {
    Type(TypeId),
    Integer(u64),
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum NumericType {
    I32,
    I64,
    U8,
    U16,
    U32,
    U64,
    Usize,
    F32,
    F64,
}
#[derive(Debug, Clone)]
pub enum ReferencePermission {
    Shared,
    Mutable,
}

// ---------- Scopes, addresses, references, collections and values. ----------
#[derive(Debug, Clone)]
pub struct Scopes {
    pub entries: Vec<Scope>,
    pub bindings: Vec<Binding>,
    pub exits: Vec<ScopeExit>,
    pub storage: Vec<ScopeStorage>,
}
#[derive(Debug, Clone)]
pub struct Scope {
    pub configuration: ConfigurationId,
    pub id: ScopeId,
    pub lexical_scope: LexicalScopeId,
    pub lexical_parent: Option<ScopeId>,
    /// Trusted boundary enclosing this scope. Checked ownership and borrowing
    /// do not reinterpret operations performed inside it, while confinement
    /// obligations still prevent raw capabilities from escaping.
    pub unchecked_boundary: Option<ScopeId>,
    pub children: Vec<ScopeId>,
    pub context: ScopeContext,
    pub entry: ScopeEntry,
    pub exits: Vec<ScopeExitId>,
    pub bindings: Vec<BindingId>,
    pub storage: ScopeStorageLink,
}
#[derive(Debug, Clone)]
pub enum ScopeStorageLink {
    DeclarationOnly,
    Runtime(ScopeStorageId),
}
#[derive(Debug, Clone)]
pub enum ScopeContext {
    Unreachable {
        body: BodyId,
        after: ExecutionMomentId,
    },
    Module(ModuleId),
    Type(TypeId),
    Body(BodyId),
}
#[derive(Debug, Clone)]
pub enum ScopeEntry {
    Unreachable {
        lexical: LexicalMomentId,
        after: ExecutionMomentId,
    },
    /// Non-executing declaration context: do not invent a runtime event.
    DeclarationRoot { lexical: LexicalMomentId },
    BodyRoot {
        lexical: LexicalMomentId,
        execution: ExecutionMomentId,
    },
    Child {
        parent: ScopeId,
        parent_lexical_moment: LexicalMomentId,
        parent_execution_moment: ExecutionMomentId,
        parent_cursor: CursorSnapshotId,
        entry: ExecutionMomentId,
    },
}
#[derive(Debug, Clone)]
pub struct ScopeExit {
    pub id: ScopeExitId,
    pub scope: ScopeId,
    pub event: ExecutionMomentId,
    pub guard: PredicateId,
    pub kind: ScopeExitKind,
}
#[derive(Debug, Clone)]
pub enum ScopeExitKind {
    Normal,
    Return,
    Break(LoopRegionId),
    Continue(LoopRegionId),
    Propagate,
    RuntimeFailure,
}
#[derive(Debug, Clone)]
pub struct Binding {
    pub id: BindingId,
    pub symbol: SymbolId,
    pub ty: TypeId,
    pub scope: ScopeId,
    pub mutable: bool,
    pub introduced: BindingIntroduction,
}
#[derive(Debug, Clone)]
pub enum BindingIntroduction {
    Capture {
        record: CaptureRecordId,
        field: FieldId,
    },
    Parameter {
        function: FunctionId,
        position: u32,
    },
    At(ExecutionMomentId),
}
#[derive(Debug, Clone)]
pub struct ScopeStorage {
    pub id: ScopeStorageId,
    pub scope: ScopeId,
    pub entry: CursorSnapshotId,
    pub relative_cursor: CursorExpressionId,
    pub upper_limit: CursorExpressionId,
    pub stack: DataStackId,
    pub region: Option<RegionId>,
}
#[derive(Debug, Clone)]
pub struct ValueEntityIdentity {
    pub value: ValueId,
    pub entity: EntityId,
    pub guard: PredicateId,
}
#[derive(Debug, Clone)]
pub struct Objects {
    pub value_entities: Vec<ValueEntityIdentity>,
    pub addresses: Vec<Address>,
    pub references: Vec<Reference>,
    pub collections: Vec<Collection>,
    pub ownership: Vec<OwnershipLink>,
    pub dependencies: Vec<DependencyLink>,
    pub membership: Vec<CollectionLink>,
    pub places: Vec<Place>,
    pub evaluated_places: Vec<EvaluatedPlace>,
}
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum EntityId {
    Address(AddressId),
    Reference(ReferenceId),
    Collection(CollectionId),
}
#[derive(Debug, Clone)]
pub struct EntityOccurrence {
    pub entity: EntityId,
    pub instance: InstanceDomainId,
}
#[derive(Debug, Clone)]
pub struct Address {
    pub created_in: ScopeId,
    pub initial_owner: Owner,
    pub id: AddressId,
    pub ty: TypeId,
    pub creation: ObjectCreation,
    pub storage: StorageOriginId,
}
#[derive(Debug, Clone)]
pub enum ObjectCreation {
    Static(SourceOriginId),
    At(ExecutionMomentId),
}
#[derive(Debug, Clone)]
pub struct Reference {
    pub created_in: ScopeId,
    pub creation: ObjectCreation,
    pub initial_owner: Owner,
    pub id: ReferenceId,
    pub ty: TypeId,
    pub permission: ReferencePermission,
    /// A flow alias carries one of the guarded references reaching a control-
    /// flow join. It does not establish an additional loan of its own.
    pub formation: ReferenceFormation,
    pub origins: NonEmpty<ReferenceOrigin>,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReferenceFormation {
    Loan,
    FlowAlias,
}
#[derive(Debug, Clone)]
pub struct ReferenceOrigin {
    pub target: PlaceId,
    pub parent: Option<ReferenceId>,
    pub guard: PredicateId,
}
#[derive(Debug, Clone)]
pub struct Collection {
    pub created_in: ScopeId,
    pub initial_owner: Option<Owner>,
    pub id: CollectionId,
    pub ty: TypeId,
    pub descriptor: CollectionDescriptor,
    pub constraints: Vec<CollectionConstraint>,
}
#[derive(Debug, Clone)]
pub enum CollectionDescriptor {
    Address(AddressId),
    Place(PlaceId),
}
#[derive(Debug, Clone)]
pub enum CollectionConstraint {
    FixedCapacity {
        capacity: ValueId,
        element: TypeId,
    },
    FixedLength(u64),
    LengthValue(ValueId),
    MaximumBytes(ValueId),
    ActiveVariant {
        guard: PredicateId,
        variant: VariantId,
    },
}
#[derive(Debug, Clone)]
pub enum Owner {
    /// The runtime owns an executing task independently of the observer handle.
    ExecutionBranch {
        branch: BranchId,
        instance: InstanceDomainId,
    },
    BorrowedTarget {
        place: PlaceId,
        instance: InstanceDomainId,
    },
    FunctionResult {
        function: FunctionInstanceId,
        instance: InstanceDomainId,
    },
    Binding {
        binding: BindingId,
        instance: InstanceDomainId,
    },
    Entity(EntityOccurrence),
    Scope {
        scope: ScopeId,
        instance: InstanceDomainId,
    },
}
#[derive(Debug, Clone)]
pub struct OwnershipLink {
    pub entity: EntityId,
    pub owner: Owner,
    pub scope: ScopeId,
    pub established: ExecutionMomentId,
    pub guard: PredicateId,
}
#[derive(Debug, Clone)]
pub struct DependencyLink {
    pub id: DependencyLinkId,
    pub dependent: EntityId,
    pub requirement: DependencyRequirement,
    pub established: ExecutionMomentId,
    pub guard: PredicateId,
}
#[derive(Debug, Clone)]
pub enum DependencyRequirement {
    /// Symbolic contents of an owned formal parameter. Instantiating a result
    /// substitutes the actual value's dependencies, not the formal's stack slot.
    CarriedByParameter {
        binding: BindingId,
    },
    ContractFutureResult {
        future: ValueId,
        target: MethodTarget,
    },
    ContractResult {
        target: MethodTarget,
        arguments: Vec<ValueId>,
    },
    /// Contents read at this event; later consumers follow resolved write/alias
    /// facts, never field names or the original constructor's stale contents.
    CarriedByPlace {
        place: EvaluatedPlaceId,
        at: ExecutionMomentId,
    },
    When {
        guard: PredicateId,
        requirement: Box<DependencyRequirement>,
    },
    NativeResult {
        operation: OperationId,
        source: ValueId,
        position: Option<PositionSelector>,
    },
    FutureResult {
        future: ValueId,
        function: FunctionInstanceId,
    },
    CapturedField {
        record: CaptureRecordId,
        field: FieldId,
    },
    CallableResult {
        callable: ValueId,
        arguments: Vec<ValueId>,
    },
    CarriedByProjection {
        source: ValueId,
        position: PositionSelector,
        result: TypeId,
    },
    /// A fully resolved substitution, not a request to resolve a call again.
    InstantiatedResult {
        function: FunctionInstanceId,
        arguments: Vec<ValueId>,
    },
    LiveTarget(PlaceId),
    LiveStorage(StorageOriginId),
    LiveReference(ReferenceId),
    ActiveLock(LockIdentityId),
    BranchCompletion(CompletionCapabilityId),
    HoldsLock(LockIdentityId),
    ConfinedToUncheckedScope(ScopeId),
}
#[derive(Debug, Clone)]
pub struct CollectionLink {
    pub collection: CollectionId,
    pub position: PositionSelector,
    pub relation: CollectionRelation,
    pub established: ExecutionMomentId,
    pub guard: PredicateId,
}
#[derive(Debug, Clone)]
pub enum CollectionRelation {
    Owns(EntityId),
    ContainsReference(ReferenceId),
    Borrows(PlaceId),
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PositionSelector {
    AllocationContent,
    AllKeys,
    State,
    AllElements { length: Option<u64> },
    VariantField { variant: VariantId, field: FieldId },
    Field(FieldId),
    TupleElement(u32),
    FixedIndex(u64),
    DynamicIndex(ValueId),
    Key(ValueId),
    Range { start: ValueId, end: ValueId },
    Symbolic(PositionId),
}
#[derive(Debug, Clone)]
pub struct Place {
    pub id: PlaceId,
    pub root: PlaceRoot,
    pub projections: Vec<PlaceProjection>,
    pub ty: TypeId,
}
#[derive(Debug, Clone)]
pub enum PlaceRoot {
    /// A resolved value with symbolic identity (for example a call result reference).
    Value(ValueId),
    Binding(BindingId),
    Address(AddressId),
    Reference(ReferenceId),
    Collection(CollectionId),
}
#[derive(Debug, Clone)]
pub enum PlaceProjection {
    AllocationContent,
    Dereference,
    Field(FieldId),
    TupleElement(u32),
    Variant(VariantId),
    Index(ValueId),
    Key(ValueId),
    Range { start: ValueId, end: ValueId },
}
#[derive(Debug, Clone)]
pub struct EvaluatedPlace {
    pub id: EvaluatedPlaceId,
    pub definition: PlaceId,
    pub produced_by: OperationId,
    pub selectors: Vec<ValueId>,
}
#[derive(Debug, Clone)]
pub struct Values {
    pub entries: Vec<Value>,
    pub provenance: Vec<Provenance>,
    pub dependency_summaries: Vec<DependencySummary>,
    pub placement_summaries: Vec<PlacementSummary>,
}
#[derive(Debug, Clone)]
pub struct Value {
    pub id: ValueId,
    pub ty: TypeId,
    pub definition: ValueDefinition,
    pub provenance: ProvenanceId,
    pub dependencies: DependencySummaryId,
    pub placement: PlacementSummaryId,
}
#[derive(Debug, Clone)]
pub enum ValueDefinition {
    ConditionalResult {
        operation: OperationId,
        produced_at: ExecutionMomentId,
        guard: PredicateId,
    },
    /// No value was produced; control terminated at this already-existing event.
    Diverged {
        at: ExecutionMomentId,
    },
    Parameter(BindingId),
    CaptureField {
        record: CaptureRecordId,
        field: FieldId,
    },
    Constant(ConstantId),
    ConfiguredConstant {
        constant: ConstantId,
        configuration: ConfigurationId,
        value: ConstantValue,
    },
    OperationResult {
        operation: OperationId,
        produced_at: ExecutionMomentId,
    },
}
#[derive(Debug, Clone)]
pub struct Provenance {
    pub id: ProvenanceId,
    pub kind: ProvenanceKind,
}
#[derive(Debug, Clone)]
pub enum ProvenanceKind {
    /// A snapshot at the read event, not a stale constructor-component alias.
    PlaceRead {
        place: EvaluatedPlaceId,
        root_value: Option<ValueId>,
        operation: OperationId,
    },
    Projection {
        source: ValueId,
        position: PositionSelector,
        operation: OperationId,
    },
    Diverged(ExecutionMomentId),
    Constant(ConstantId),
    Binding(BindingId),
    Constructed(OperationId),
    Move {
        source: ValueId,
        operation: OperationId,
    },
    /// A new value whose scalar/eligible-enum contents come from `source`.
    /// Unlike `Forward`, this does not preserve ownership or alias identity;
    /// only the dependency summary explicitly attached to the copied value is
    /// retained.
    Copy {
        source: ValueId,
        operation: OperationId,
    },
    Forward {
        source: ValueId,
        operation: OperationId,
    },
    Merge(NonEmpty<GuardedValue>),
    LoopParameter(OperationId),
    CallResult {
        operation: OperationId,
        effects: EffectSummaryId,
    },
}
#[derive(Debug, Clone)]
pub struct GuardedValue {
    pub guard: PredicateId,
    pub value: ValueId,
}
#[derive(Debug, Clone)]
pub struct DependencySummary {
    pub id: DependencySummaryId,
    pub dependencies: Vec<DependencyRequirement>,
    pub guarded: Vec<GuardedDependency>,
    pub deferred_result: Vec<GuardedDependency>,
}
#[derive(Debug, Clone)]
pub struct GuardedDependency {
    pub guard: PredicateId,
    pub requirement: DependencyRequirement,
}
#[derive(Debug, Clone)]
pub struct PlacementSummary {
    pub id: PlacementSummaryId,
    pub origins: Vec<StorageOriginId>,
    pub destinations: Vec<GuardedDestination>,
}
#[derive(Debug, Clone)]
pub enum LogicalScope {
    ExecutionBranch(BranchId),
    BorrowedTarget(PlaceId),
    Local(ScopeId),
    CallerResult(FunctionInstanceId),
}
#[derive(Debug, Clone)]
pub enum LogicalCleanupSite {
    ExecutionBranchEnd(BranchId),
    BorrowedTarget(PlaceId),
    NoReachableExit(ScopeId),
    Exit(ScopeExitId),
    CallerResult(FunctionInstanceId),
}
#[derive(Debug, Clone)]
pub struct GuardedDestination {
    pub guard: PredicateId,
    pub scope: LogicalScope,
    pub binding: Option<BindingId>,
}

// ---------- Contracts and effect summaries: resolved once. ----------
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct EqualityPlanId(pub u32);
#[derive(Debug, Clone)]
pub struct EqualityPlan {
    pub id: EqualityPlanId,
    pub ty: TypeId,
    pub kind: EqualityKind,
}
#[derive(Debug, Clone)]
pub enum EqualityKind {
    Numeric(NumericType),
    /// Compiler-provided failure carrier for exact numeric try_from.
    NumericConversionError,
    Boolean,
    ReferenceIdentity,
    SliceIdentity,
    EnumTagAndPayload(Vec<VariantEquality>),
}
#[derive(Debug, Clone)]
pub struct VariantEquality {
    pub variant: VariantId,
    pub fields: Vec<FieldEquality>,
}
#[derive(Debug, Clone)]
pub struct FieldEquality {
    pub field: FieldId,
    pub comparison: EqualityPlanId,
}

#[derive(Debug, Clone)]
pub struct Contracts {
    pub symbolic_requirements: Vec<SymbolicContractRequirement>,
    pub equality: Vec<EqualityPlan>,
    pub memory_configuration: Vec<MemoryConfiguration>,
    pub types: Vec<StructuralTypeContract>,
    pub alternatives: Vec<ContractAlternative>,
    pub matches: Vec<ContractMatch>,
    pub branches: Vec<BranchContract>,
    pub completions: Vec<CompletionCapability>,
    pub locks: Vec<LockContract>,
    pub threads: Vec<ThreadTransferContract>,
    pub captures: Vec<CaptureRecord>,
    pub destructors: Vec<DestructorDefinition>,
    pub configuration: Vec<ResolvedConfiguration>,
    pub type_effects: Vec<TypeEffectContracts>,
    pub applications: Vec<ContractApplication>,
    pub lock_identities: Vec<LockIdentity>,
    pub environments: Vec<ConfigurationEnvironment>,
}
#[derive(Debug, Clone)]
pub enum ResolvedContract {
    Type(TypeContractId),
    Branch(BranchContractId),
    Lock(LockContractId),
    Thread(ThreadContractId),
}
#[derive(Debug, Clone)]
pub struct StructuralTypeContract {
    pub arguments: Vec<ContractTypeArgument>,
    pub id: TypeContractId,
    pub parameter: TypeParameterId,
    pub requirement: TypeRequirement,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub struct ContractTypeArgument {
    pub parameter: TypeParameterId,
    pub allowed: AllowedTypes,
}
#[derive(Debug, Clone)]
pub enum AllowedTypes {
    Any,
    OneOf(NonEmpty<TypeId>),
}
#[derive(Debug, Clone)]
pub enum TypeRequirement {
    Unconstrained,
    Alternatives {
        mode: ContractMode,
        alternatives: NonEmpty<ContractAlternativeId>,
    },
}
#[derive(Debug, Clone)]
pub enum ContractMode {
    AtLeast,
    Exact,
}
#[derive(Debug, Clone)]
pub struct ContractAlternative {
    pub id: ContractAlternativeId,
    pub requirements: NonEmpty<MethodRequirement>,
}
#[derive(Debug, Clone)]
pub struct MethodRequirement {
    pub name: String,
    pub signature: SignatureId,
    pub origin: SourceOriginId,
}
/// Records the entire matching set; does not silently choose the first branch.
#[derive(Debug, Clone)]
pub struct ContractMatch {
    pub id: ContractMatchId,
    pub contract: TypeContractId,
    pub actual: TypeId,
    pub matching: NonEmpty<AlternativeMatch>,
}
#[derive(Debug, Clone)]
pub struct AlternativeMatch {
    pub alternative: ContractAlternativeId,
    pub methods: NonEmpty<MethodResolution>,
}
#[derive(Debug, Clone)]
pub struct MethodResolution {
    pub requirement_index: u32,
    pub implementation: FunctionInstanceId,
}
#[derive(Debug, Clone)]
pub struct BranchContract {
    pub instance: FunctionInstanceId,
    pub id: BranchContractId,
    pub function: FunctionId,
    pub completion: CompletionContract,
    pub effects: EffectSummaryId,
}
#[derive(Debug, Clone)]
pub enum CompletionContract {
    Unspecified,
    ThroughResult {
        selector: ResolvedCompletionSelector,
    },
}
#[derive(Debug, Clone)]
pub enum ResolvedCompletionSelector {
    Call(FunctionInstanceId),
    Await(SignatureId),
}
#[derive(Debug, Clone)]
pub struct CompletionCapability {
    pub id: CompletionCapabilityId,
    pub branch: BranchId,
    pub carrier: CompletionCarrier,
    pub established_at: Vec<GuardedMoment>,
}
#[derive(Debug, Clone)]
pub enum CompletionCarrier {
    Result(ValueId),
    Unspecified,
}

#[derive(Debug, Clone)]
pub struct LockContract {
    pub id: LockContractId,
    pub subject: ResolvedSubject,
    pub duration: LockDuration,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub enum ResolvedSubject {
    Receiver,
    Parameter(u32),
    ResultField(Vec<FieldId>),
}
#[derive(Debug, Clone)]
pub enum LockDuration {
    ThroughCall,
    ThroughResult,
}
#[derive(Debug, Clone)]
pub struct ThreadTransferContract {
    pub id: ThreadContractId,
    pub ty: TypeId,
    pub declared_forbidden: bool,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub struct CaptureRecord {
    pub id: CaptureRecordId,
    pub call: Option<FunctionInstanceId>,
    pub moving: bool,
    pub ty: TypeId,
    pub captures: Vec<Capture>,
}
#[derive(Debug, Clone)]
pub struct Capture {
    pub field: FieldId,
    pub source: BindingId,
    pub value: ValueId,
    pub mode: CaptureMode,
    pub creation: ExecutionMomentId,
}
#[derive(Debug, Clone)]
pub enum CaptureMode {
    ByTypeParameter(TypeId),
    Move,
    PrimitiveCopy,
    EligibleEnumCopy,
    SharedReferenceCopy,
}
#[derive(Debug, Clone)]
pub struct DestructorDefinition {
    pub id: DestructorId,
    pub ty: TypeId,
    pub hook: FunctionInstanceId,
    pub owned_components: Vec<ComponentDestruction>,
}
#[derive(Debug, Clone)]
pub struct ComponentDestruction {
    pub guard: PredicateId,
    pub position: PositionSelector,
    pub destructor: DestructorId,
    pub dependencies: Vec<PositionSelector>,
}
#[derive(Debug, Clone)]
pub struct ResolvedConfiguration {
    pub scope: ScopeId,
    pub constant: ConstantId,
    pub value: ConstantValue,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub enum MemoryConfiguration {
    DataStack(DataStackConfiguration),
    Region(RegionConfiguration),
    FreePages(FreePagesRequest),
    AsyncPool(AsyncPoolCapacity),
}
#[derive(Debug, Clone)]
pub struct DataStackConfiguration {
    pub origin: SourceOriginId,
    pub fixed_size: BudgetRequest,
    pub region_stack_size: BudgetRequest,
    pub region_size: BudgetRequest,
    pub reclaim_threshold: BudgetRequest,
    pub region_reclaim_threshold: BudgetRequest,
}
#[derive(Debug, Clone)]
pub enum BudgetRequest {
    Explicit(u64),
    InferThenDefault,
}
#[derive(Debug, Clone)]
pub struct RegionConfiguration {
    pub scope: ScopeId,
    pub maximum_bytes: u64,
    pub count: Option<u64>,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub struct FreePagesRequest {
    pub scope: ScopeId,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub struct AsyncPoolCapacity {
    pub function: FunctionInstanceId,
    pub capacity: u64,
    pub origin: SourceOriginId,
}

#[derive(Debug, Clone)]
pub struct EffectSummary {
    pub id: EffectSummaryId,
    pub effects: Vec<GuardedEffect>,
}
#[derive(Debug, Clone)]
pub struct GuardedEffect {
    pub guard: PredicateId,
    pub effect: Effect,
    pub timing: EffectTiming,
}
#[derive(Debug, Clone)]
pub enum EffectTiming {
    At(ExecutionMomentId),
    CallEntry,
    CallReturn,
    AfterCompletion(CompletionCapabilityId),
}
#[derive(Debug, Clone)]
pub enum Effect {
    AwaitContract {
        future: ValueId,
        target: MethodTarget,
    },
    ContractCall {
        target: MethodTarget,
        arguments: Vec<CallArgument>,
    },
    LaunchTask {
        task: ValueId,
        kind: RuntimeLaunchKind,
    },
    JoinHandle {
        handle: ValueId,
    },
    AwaitFuture {
        future: ValueId,
        function: FunctionInstanceId,
    },
    InvokeCallable {
        callable: ValueId,
        signature: SignatureId,
        arguments: Vec<CallArgument>,
    },
    Call(CallEffect),
    Read(ReadEffect),
    Write(WriteEffect),
    Move(MoveEffect),
    Borrow(BorrowEffect),
    Collection(CollectionEffect),
    Branch(BranchEffect),
    Lock(LockEffect),
    Cleanup(CleanupEffect),
}
#[derive(Debug, Clone)]
pub struct CallEffect {
    pub target: FunctionInstanceId,
    pub arguments: Vec<CallArgument>,
}
#[derive(Debug, Clone)]
pub struct ReadEffect {
    pub place: PlaceId,
}
#[derive(Debug, Clone)]
pub struct WriteEffect {
    pub value: ValueId,
    pub place: PlaceId,
    pub value_dependencies: DependencySummaryId,
}
#[derive(Debug, Clone)]
pub struct MoveEffect {
    pub entity: EntityId,
    pub from: Owner,
    pub to: Owner,
}
#[derive(Debug, Clone)]
pub struct BorrowEffect {
    pub reference: ReferenceId,
    pub target: PlaceId,
}
#[derive(Debug, Clone)]
pub struct CollectionEffect {
    pub access: AccessKind,
    pub result: Option<ValueId>,
    pub collection: CollectionId,
    pub position: PositionSelector,
    pub incoming: Vec<EntityId>,
    pub outgoing: Vec<EntityId>,
}
#[derive(Debug, Clone)]
pub struct BranchEffect {
    pub branch: BranchId,
    pub completion: CompletionCapabilityId,
}
#[derive(Debug, Clone)]
pub struct LockEffect {
    pub lock: LockIdentityId,
    pub subject: PlaceId,
    pub duration: LockDuration,
}
#[derive(Debug, Clone)]
pub struct CleanupEffect {
    pub entity: EntityId,
}

// ---------- Executable units: each operation has its own Rust type. ----------
#[derive(Debug, Clone)]
pub struct FunctionBody {
    pub environment: Option<CaptureRecordId>,
    pub id: BodyId,
    pub owner: BodyOwner,
    pub scope: ScopeId,
    pub root_branch: BranchId,
    pub operations: Vec<Operation>,
}
#[derive(Debug, Clone)]
pub enum BodyOwner {
    Declaration(FunctionId),
    Instance(FunctionInstanceId),
}
#[derive(Debug, Clone)]
pub struct OperationSite {
    pub id: OperationId,
    pub body: BodyId,
    pub scope: ScopeId,
    pub branch: BranchId,
    pub timeline: TimelineId,
    pub lexical_moment: LexicalMomentId,
    pub execution_moments: NonEmpty<ExecutionMomentId>,
    pub origin: SourceOriginId,
    pub guard: PredicateId,
}

#[derive(Debug, Clone)]
pub struct EnterScope {
    pub site: OperationSite,
    pub scope: ScopeId,
    pub cursor: CursorSnapshotId,
}

#[derive(Debug, Clone)]
pub struct ExitScope {
    pub site: OperationSite,
    pub exit: ScopeExitId,
}

#[derive(Debug, Clone)]
pub struct EvaluatePlace {
    pub site: OperationSite,
    pub place: PlaceId,
    pub result: EvaluatedPlaceId,
}

#[derive(Debug, Clone)]
pub struct ReadValue {
    pub site: OperationSite,
    pub source: EvaluatedPlaceId,
    pub result: ValueId,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct InitializeDefault {
    pub site: OperationSite,
    pub plan: DefaultPlanId,
    pub result: ValueId,
}
#[derive(Debug, Clone)]
pub struct InitializeBinding {
    pub site: OperationSite,
    pub binding: BindingId,
    pub value: ValueId,
}

#[derive(Debug, Clone)]
pub struct ReceiveValue {
    pub site: OperationSite,
    pub receiver: BindingId,
    pub source: ValueId,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct ForwardResult {
    pub site: OperationSite,
    pub source: ValueId,
    pub destination: ValueId,
}

#[derive(Debug, Clone)]
pub struct DiscardResult {
    pub site: OperationSite,
    pub value: ValueId,
    pub destructor: DestructorId,
}

#[derive(Debug, Clone)]
pub struct MoveValue {
    pub site: OperationSite,
    pub source: MoveSource,
    pub result: ValueId,
    pub value: ValueId,
    pub destination: Owner,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub enum MoveSource {
    Binding(BindingId),
    Place(EvaluatedPlaceId),
    Value(ValueId),
}

#[derive(Debug, Clone)]
pub struct CopyPrimitive {
    pub site: OperationSite,
    pub source: ValueId,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct CopyEligibleEnum {
    pub site: OperationSite,
    pub source: ValueId,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct BorrowShared {
    pub site: OperationSite,
    pub source: EvaluatedPlaceId,
    pub reference: ReferenceId,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct BorrowMutable {
    pub site: OperationSite,
    pub source: EvaluatedPlaceId,
    pub reference: ReferenceId,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct ReborrowShared {
    pub site: OperationSite,
    pub parent: ReferenceId,
    pub source: EvaluatedPlaceId,
    pub reference: ReferenceId,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct ReborrowMutable {
    pub site: OperationSite,
    pub parent: ReferenceId,
    pub source: EvaluatedPlaceId,
    pub reference: ReferenceId,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct Assign {
    pub site: OperationSite,
    pub target: EvaluatedPlaceId,
    pub value: ValueId,
    pub replacement: ReplacementPlan,
}

#[derive(Debug, Clone)]
pub struct AddAssign {
    pub site: OperationSite,
    pub previous: ValueId,
    pub computed: ValueId,
    pub phases: ReadModifyWriteMoments,
    pub target: EvaluatedPlaceId,
    pub operand: ValueId,
    pub domain: NumericType,
    pub checks: Vec<CheckId>,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct SubtractAssign {
    pub site: OperationSite,
    pub previous: ValueId,
    pub computed: ValueId,
    pub phases: ReadModifyWriteMoments,
    pub target: EvaluatedPlaceId,
    pub operand: ValueId,
    pub domain: NumericType,
    pub checks: Vec<CheckId>,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct MultiplyAssign {
    pub site: OperationSite,
    pub previous: ValueId,
    pub computed: ValueId,
    pub phases: ReadModifyWriteMoments,
    pub target: EvaluatedPlaceId,
    pub operand: ValueId,
    pub domain: NumericType,
    pub checks: Vec<CheckId>,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct DivideAssign {
    pub site: OperationSite,
    pub previous: ValueId,
    pub computed: ValueId,
    pub phases: ReadModifyWriteMoments,
    pub target: EvaluatedPlaceId,
    pub operand: ValueId,
    pub domain: NumericType,
    pub checks: Vec<CheckId>,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct RemainderAssign {
    pub site: OperationSite,
    pub previous: ValueId,
    pub computed: ValueId,
    pub phases: ReadModifyWriteMoments,
    pub target: EvaluatedPlaceId,
    pub operand: ValueId,
    pub domain: NumericType,
    pub checks: Vec<CheckId>,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct BitAndAssign {
    pub site: OperationSite,
    pub previous: ValueId,
    pub computed: ValueId,
    pub phases: ReadModifyWriteMoments,
    pub target: EvaluatedPlaceId,
    pub operand: ValueId,
    pub domain: NumericType,
    pub checks: Vec<CheckId>,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct BitOrAssign {
    pub site: OperationSite,
    pub previous: ValueId,
    pub computed: ValueId,
    pub phases: ReadModifyWriteMoments,
    pub target: EvaluatedPlaceId,
    pub operand: ValueId,
    pub domain: NumericType,
    pub checks: Vec<CheckId>,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct BitXorAssign {
    pub site: OperationSite,
    pub previous: ValueId,
    pub computed: ValueId,
    pub phases: ReadModifyWriteMoments,
    pub target: EvaluatedPlaceId,
    pub operand: ValueId,
    pub domain: NumericType,
    pub checks: Vec<CheckId>,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct ShiftLeftAssign {
    pub site: OperationSite,
    pub previous: ValueId,
    pub computed: ValueId,
    pub phases: ReadModifyWriteMoments,
    pub target: EvaluatedPlaceId,
    pub operand: ValueId,
    pub domain: NumericType,
    pub checks: Vec<CheckId>,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct ShiftRightAssign {
    pub site: OperationSite,
    pub previous: ValueId,
    pub computed: ValueId,
    pub phases: ReadModifyWriteMoments,
    pub target: EvaluatedPlaceId,
    pub operand: ValueId,
    pub domain: NumericType,
    pub checks: Vec<CheckId>,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct Add {
    pub site: OperationSite,
    pub domain: NumericType,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct Subtract {
    pub site: OperationSite,
    pub domain: NumericType,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct Multiply {
    pub site: OperationSite,
    pub domain: NumericType,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct Divide {
    pub site: OperationSite,
    pub domain: NumericType,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct Remainder {
    pub site: OperationSite,
    pub domain: NumericType,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct BitAnd {
    pub site: OperationSite,
    pub domain: NumericType,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct BitOr {
    pub site: OperationSite,
    pub domain: NumericType,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct BitXor {
    pub site: OperationSite,
    pub domain: NumericType,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct ShiftLeft {
    pub site: OperationSite,
    pub domain: NumericType,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct ShiftRight {
    pub site: OperationSite,
    pub domain: NumericType,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct Equal {
    pub site: OperationSite,
    pub comparison: EqualityPlanId,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct NotEqual {
    pub site: OperationSite,
    pub comparison: EqualityPlanId,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct Less {
    pub site: OperationSite,
    pub domain: NumericType,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct LessEqual {
    pub site: OperationSite,
    pub domain: NumericType,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct Greater {
    pub site: OperationSite,
    pub domain: NumericType,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct GreaterEqual {
    pub site: OperationSite,
    pub domain: NumericType,
    pub left: ValueId,
    pub right: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct Negate {
    pub site: OperationSite,
    pub domain: NumericType,
    pub operand: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct BooleanNot {
    pub site: OperationSite,
    pub operand: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct BitNot {
    pub site: OperationSite,
    pub domain: NumericType,
    pub operand: ValueId,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct LoopParameter {
    pub site: OperationSite,
    pub region: LoopRegionId,
    pub binding: BindingId,
    pub initial: ValueId,
    pub back_edges: Vec<GuardedValue>,
    pub result: ValueId,
}
#[derive(Debug, Clone)]
pub struct ShortCircuitAnd {
    pub site: OperationSite,
    pub left: ValueId,
    pub conditional_right: BranchId,
    pub result: ValueId,
    pub merge: ExecutionMomentId,
}

#[derive(Debug, Clone)]
pub struct ShortCircuitOr {
    pub site: OperationSite,
    pub left: ValueId,
    pub conditional_right: BranchId,
    pub result: ValueId,
    pub merge: ExecutionMomentId,
}

#[derive(Debug, Clone)]
pub struct IntegerLiteral {
    pub site: OperationSite,
    pub value: IntegerConstant,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct FloatLiteral {
    pub site: OperationSite,
    pub value: FloatConstant,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct BooleanLiteral {
    pub site: OperationSite,
    pub value: bool,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct TextLiteral {
    pub site: OperationSite,
    pub storage: AddressId,
    pub reference: ReferenceId,
    pub utf8: Vec<u8>,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct UnitValue {
    pub site: OperationSite,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct NumericCast {
    pub site: OperationSite,
    pub source: ValueId,
    pub target: NumericType,
    pub result: ValueId,
    pub check: CheckId,
}

#[derive(Debug, Clone)]
pub struct DirectCall {
    pub site: OperationSite,
    pub target: FunctionInstanceId,
    pub arguments: Vec<CallArgument>,
    pub result: ValueId,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct MethodCall {
    pub site: OperationSite,
    pub target: ResolvedMethodCall,
    pub arguments: Vec<CallArgument>,
    pub result: ValueId,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct ExternalCall {
    pub site: OperationSite,
    pub target: ResolvedExternalCall,
    pub arguments: Vec<CallArgument>,
    pub result: ValueId,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct IntrinsicCall {
    pub site: OperationSite,
    pub target: IntrinsicId,
    pub arguments: Vec<CallArgument>,
    pub result: ValueId,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct CallableCall {
    pub site: OperationSite,
    pub target: ResolvedCallableCall,
    pub arguments: Vec<CallArgument>,
    pub result: ValueId,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct ConstructStruct {
    pub site: OperationSite,
    pub ty: TypeId,
    pub components: Vec<ComponentInitialization>,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct ConstructEnum {
    pub site: OperationSite,
    pub ty: TypeId,
    pub variant: VariantId,
    pub components: Vec<ComponentInitialization>,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct ConstructTuple {
    pub site: OperationSite,
    pub ty: TypeId,
    pub components: Vec<ComponentInitialization>,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct ConstructArray {
    pub site: OperationSite,
    pub ty: TypeId,
    pub components: Vec<ComponentInitialization>,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct RepeatArray {
    pub site: OperationSite,
    pub seed: ValueId,
    pub count: u64,
    pub replication: StructuralReplicationPlan,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct ExtractTupleField {
    pub site: OperationSite,
    pub source: ValueId,
    pub position: u32,
    pub result: ValueId,
    pub reference: Option<ReferenceId>,
    pub transfer: TransferKind,
}

#[derive(Debug, Clone)]
pub struct ExtractVariantField {
    pub site: OperationSite,
    pub source: ValueId,
    pub variant: VariantId,
    pub field: FieldId,
    pub result: ValueId,
    pub reference: Option<ReferenceId>,
    pub transfer: TransferKind,
}

#[derive(Debug, Clone)]
pub struct ProjectField {
    pub site: OperationSite,
    pub base: EvaluatedPlaceId,
    pub field: FieldId,
    pub result: EvaluatedPlaceId,
}

#[derive(Debug, Clone)]
pub struct ProjectTupleField {
    pub site: OperationSite,
    pub base: EvaluatedPlaceId,
    pub position: u32,
    pub result: EvaluatedPlaceId,
}

#[derive(Debug, Clone)]
pub struct Dereference {
    pub site: OperationSite,
    pub effects: EffectSummaryId,
    pub source: ValueId,
    pub access: ResolvedDereference,
    pub result: EvaluatedPlaceId,
}

#[derive(Debug, Clone)]
pub struct IndexPlace {
    pub site: OperationSite,
    pub access: ResolvedIndexAccess,
    pub base: EvaluatedPlaceId,
    pub index: ValueId,
    pub result: EvaluatedPlaceId,
    pub check: CheckId,
}

#[derive(Debug, Clone)]
pub struct SequenceLength {
    pub site: OperationSite,
    pub source: EvaluatedPlaceId,
    pub result: ValueId,
}
#[derive(Debug, Clone)]
pub struct SlicePlace {
    pub site: OperationSite,
    pub base: EvaluatedPlaceId,
    pub start: ValueId,
    pub end: ValueId,
    pub element: TypeId,
    pub result: EvaluatedPlaceId,
    pub check: CheckId,
}
#[derive(Debug, Clone)]
pub struct TryTextSlice {
    pub site: OperationSite,
    pub source: EvaluatedPlaceId,
    pub start: ValueId,
    pub end: ValueId,
    pub length: ValueId,
    pub valid: PredicateId,
    pub success: VariantId,
    pub failure: VariantId,
    pub success_payload: FieldId,
    pub failure_payload: FieldId,
    pub out_of_bounds: VariantId,
    pub not_char_boundary: VariantId,
    pub view: ValueId,
    pub reference: ReferenceId,
    pub result: ValueId,
}
#[derive(Debug, Clone)]
pub struct SliceView {
    pub site: OperationSite,
    pub reference: ReferenceId,
    pub access: ResolvedSliceAccess,
    pub base: EvaluatedPlaceId,
    pub start: ValueId,
    pub end: ValueId,
    pub permission: ReferencePermission,
    pub result: ValueId,
    pub checks: Vec<CheckId>,
}

#[derive(Debug, Clone)]
pub struct IfDecision {
    pub site: OperationSite,
    pub condition: ValueId,
    pub yes: BranchId,
    pub no: BranchId,
    pub merge: Option<ExecutionMomentId>,
}

#[derive(Debug, Clone)]
pub struct IfLetDecision {
    pub site: OperationSite,
    pub subject: ValueId,
    pub pattern: ResolvedPattern,
    pub yes: BranchId,
    pub no: BranchId,
    pub merge: Option<ExecutionMomentId>,
}

#[derive(Debug, Clone)]
pub struct MatchDecision {
    pub site: OperationSite,
    pub subject: ValueId,
    pub unmatched: PredicateId,
    pub arms: NonEmpty<ResolvedMatchArm>,
    pub merge: Option<ExecutionMomentId>,
}

#[derive(Debug, Clone)]
pub struct MergeValue {
    pub site: OperationSite,
    pub incoming: NonEmpty<GuardedValue>,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct LoopControl {
    pub site: OperationSite,
    pub region: LoopRegionId,
}

#[derive(Debug, Clone)]
pub struct WhileControl {
    pub site: OperationSite,
    pub region: LoopRegionId,
    pub condition: ValueId,
}

#[derive(Debug, Clone)]
pub struct IterationIndex {
    pub site: OperationSite,
    pub region: LoopRegionId,
    pub coordinate: IterationVariableId,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct PatternMatches {
    pub site: OperationSite,
    pub subject: ValueId,
    pub test: PatternTest,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct ForControl {
    pub site: OperationSite,
    pub region: LoopRegionId,
    pub source: ValueId,
    pub iteration: ResolvedIteration,
    pub pattern: ResolvedPattern,
    pub bindings: Vec<BindingId>,
}

#[derive(Debug, Clone)]
pub struct BreakControl {
    pub site: OperationSite,
    pub region: LoopRegionId,
    pub value: ValueId,
    pub exit: ScopeExitId,
    pub outer_exits: Vec<ScopeExitId>,
}

#[derive(Debug, Clone)]
pub struct ContinueControl {
    pub site: OperationSite,
    pub region: LoopRegionId,
    pub exit: ScopeExitId,
    pub outer_exits: Vec<ScopeExitId>,
}

#[derive(Debug, Clone)]
pub struct ReturnControl {
    pub site: OperationSite,
    pub function: FunctionInstanceId,
    pub value: ValueId,
    pub exit: ScopeExitId,
    pub outer_exits: Vec<ScopeExitId>,
}

#[derive(Debug, Clone)]
pub struct PropagateResult {
    pub site: OperationSite,
    pub subject: ValueId,
    pub success_variant: VariantId,
    pub failure_variant: VariantId,
    pub conversion: ErrorConversion,
    pub success: ValueId,
    pub payload: FieldId,
    pub success_branch: BranchId,
    pub failure_branch: BranchId,
    pub continuation: ExecutionMomentId,
    pub exit: ScopeExitId,
}

#[derive(Debug, Clone)]
pub struct PropagateOption {
    pub site: OperationSite,
    pub subject: ValueId,
    pub some: VariantId,
    pub none: VariantId,
    pub success: ValueId,
    pub payload: FieldId,
    pub success_branch: BranchId,
    pub failure_branch: BranchId,
    pub continuation: ExecutionMomentId,
    pub exit: ScopeExitId,
}

#[derive(Debug, Clone)]
pub struct UnwrapResult {
    pub site: OperationSite,
    pub subject: ValueId,
    pub success_variant: VariantId,
    pub result: ValueId,
    pub payload: FieldId,
    pub reference: Option<ReferenceId>,
    pub check: CheckId,
}

#[derive(Debug, Clone)]
pub struct UnwrapOption {
    pub site: OperationSite,
    pub subject: ValueId,
    pub some: VariantId,
    pub result: ValueId,
    pub payload: FieldId,
    pub reference: Option<ReferenceId>,
    pub check: CheckId,
}

#[derive(Debug, Clone)]
pub struct AdaptCallable {
    pub site: OperationSite,
    pub source: ValueId,
    pub signature: SignatureId,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct CreateClosure {
    pub site: OperationSite,
    pub captures: CaptureRecordId,
    pub body: BodyId,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct CreateFuture {
    pub site: OperationSite,
    pub captures: Option<CaptureRecordId>,
    pub function: FunctionInstanceId,
    pub arguments: Vec<CallArgument>,
    pub body: BodyId,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct CaptureMove {
    pub site: OperationSite,
    pub record: CaptureRecordId,
    pub source: BindingId,
    pub field: FieldId,
    pub value: ValueId,
}

#[derive(Debug, Clone)]
pub struct CaptureCopy {
    pub site: OperationSite,
    pub record: CaptureRecordId,
    pub source: BindingId,
    pub field: FieldId,
    pub value: ValueId,
}

#[derive(Debug, Clone)]
pub struct EnterMoveBlock {
    pub site: OperationSite,
    pub scope: ScopeId,
    pub captures: CaptureRecordId,
    pub environment: ValueId,
}

#[derive(Debug, Clone)]
pub struct AwaitValue {
    pub site: OperationSite,
    pub source: ValueId,
    pub protocol: ResolvedAwait,
    pub suspension: SuspensionId,
    pub result: ValueId,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct YieldExecution {
    pub site: OperationSite,
    pub suspension: SuspensionId,
}

#[derive(Debug, Clone)]
pub struct BeginBranch {
    pub site: OperationSite,
    pub child: BranchId,
    pub contract: BranchContractId,
    pub capability: CompletionCapabilityId,
}

#[derive(Debug, Clone)]
pub struct CompleteBranch {
    pub site: OperationSite,
    pub capability: CompletionCapabilityId,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct BeginLockEffect {
    pub site: OperationSite,
    pub contract: LockContractId,
    pub identity: LockIdentityId,
    pub target: PlaceId,
}

#[derive(Debug, Clone)]
pub struct EndLockEffect {
    pub site: OperationSite,
    pub identity: LockIdentityId,
}

#[derive(Debug, Clone)]
pub struct DropValue {
    pub site: OperationSite,
    pub value: ValueId,
    pub destructor: DestructorId,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct AdoptOwnedValue {
    pub site: OperationSite,
    pub collection: CollectionId,
    pub position: PositionSelector,
    pub value: ValueId,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct ReleaseOwnedValue {
    pub site: OperationSite,
    pub collection: CollectionId,
    pub position: PositionSelector,
    pub result: ValueId,
    pub effects: EffectSummaryId,
}

#[derive(Debug, Clone)]
pub struct NativeOperation {
    pub site: OperationSite,
    pub kind: NativeOperationKind,
    pub arguments: Vec<CallArgument>,
    pub result: ValueId,
    pub effects: EffectSummaryId,
}
#[derive(Debug, Clone)]
pub enum NativeOperationKind {
    Primitive(PrimitiveOperation),
    FunctionItem(FunctionInstanceId),
    RuntimeLaunch {
        kind: RuntimeLaunchKind,
        task: ValueId,
        function: FunctionInstanceId,
    },
    Join {
        handle: ValueId,
    },
    Construct {
        ty: TypeId,
    },
    Collection {
        collection: CollectionId,
        operation: CollectionOperationKind,
        position: Option<PositionSelector>,
    },
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RuntimeLaunchKind {
    Spawn,
    SpawnBlocking,
    Thread,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CollectionOperationKind {
    Push,
    Pop,
    Remove,
    Replace,
    Insert,
    Get,
    GetMutable,
    Length,
    Clear,
    View,
    MutableView,
}
#[derive(Debug, Clone)]
pub struct CreatePool {
    pub site: OperationSite,
    pub element: TypeId,
    pub capacity: ValueId,
    pub storage: StorageOriginId,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct AllocatePoolSlot {
    pub site: OperationSite,
    pub pool: ValueId,
    pub content: ValueId,
    pub result: ValueId,
    pub check: CheckId,
}

#[derive(Debug, Clone)]
pub struct TryAllocatePoolSlot {
    pub allocation: ValueId,
    pub success: PredicateId,
    pub failure_cleanup: ConditionalCleanup,
    pub site: OperationSite,
    pub pool: ValueId,
    pub content: ValueId,
    pub result: ValueId,
    pub success_variant: VariantId,
    pub success_payload: FieldId,
    pub failure_variant: VariantId,
    pub failure_payload: FieldId,
    pub pool_full_variant: VariantId,
}

#[derive(Debug, Clone)]
pub struct CreateGrowingStorage {
    pub site: OperationSite,
    pub descriptor: AddressId,
    pub configuration: ScopeStorageId,
    pub result: ValueId,
}

#[derive(Debug, Clone)]
pub struct GrowStorage {
    pub site: OperationSite,
    pub collection: CollectionId,
    pub required_bytes: ValueId,
    pub check: CheckId,
}

#[derive(Debug, Clone)]
pub struct EnterUnchecked {
    pub site: OperationSite,
    pub scope: ScopeId,
}

#[derive(Debug, Clone)]
pub struct ExitUnchecked {
    pub site: OperationSite,
    pub scope: ScopeId,
}

#[derive(Debug, Clone)]
pub struct AddressOf {
    pub site: OperationSite,
    pub source: EvaluatedPlaceId,
    pub result: ValueId,
    pub boundary: ScopeId,
}

#[derive(Debug, Clone)]
pub struct ForeignC {
    pub site: OperationSite,
    pub outputs: Vec<ForeignWriteback>,
    pub region: ForeignRegionId,
    pub operands: Vec<ForeignOperand>,
    pub result: ValueId,
    pub effects: ForeignBoundaryEffects,
}

#[derive(Debug, Clone)]
pub struct ForeignCpp {
    pub site: OperationSite,
    pub outputs: Vec<ForeignWriteback>,
    pub region: ForeignRegionId,
    pub operands: Vec<ForeignOperand>,
    pub result: ValueId,
    pub effects: ForeignBoundaryEffects,
}

#[derive(Debug, Clone)]
pub struct ForeignAssembly {
    pub site: OperationSite,
    pub outputs: Vec<ForeignWriteback>,
    pub region: ForeignRegionId,
    pub operands: Vec<ForeignOperand>,
    pub result: ValueId,
    pub effects: ForeignBoundaryEffects,
}

#[derive(Debug, Clone)]
pub struct RuntimeCheckOperation {
    pub site: OperationSite,
    pub requirement: CheckId,
    pub failure: FailureContinuation,
}

#[derive(Debug, Clone)]
pub enum Operation {
    CreatePool(CreatePool),
    NativeOperation(NativeOperation),
    EnterScope(EnterScope),
    ExitScope(ExitScope),
    EvaluatePlace(EvaluatePlace),
    ReadValue(ReadValue),
    InitializeBinding(InitializeBinding),
    InitializeDefault(InitializeDefault),
    ReceiveValue(ReceiveValue),
    ForwardResult(ForwardResult),
    DiscardResult(DiscardResult),
    MoveValue(MoveValue),
    ParametricTransfer(ParametricTransfer),
    CopyPrimitive(CopyPrimitive),
    CopyEligibleEnum(CopyEligibleEnum),
    BorrowShared(BorrowShared),
    BorrowMutable(BorrowMutable),
    ReborrowShared(ReborrowShared),
    ReborrowMutable(ReborrowMutable),
    Assign(Assign),
    AddAssign(AddAssign),
    SubtractAssign(SubtractAssign),
    MultiplyAssign(MultiplyAssign),
    DivideAssign(DivideAssign),
    RemainderAssign(RemainderAssign),
    BitAndAssign(BitAndAssign),
    BitOrAssign(BitOrAssign),
    BitXorAssign(BitXorAssign),
    ShiftLeftAssign(ShiftLeftAssign),
    ShiftRightAssign(ShiftRightAssign),
    Add(Add),
    Subtract(Subtract),
    Multiply(Multiply),
    Divide(Divide),
    Remainder(Remainder),
    BitAnd(BitAnd),
    BitOr(BitOr),
    BitXor(BitXor),
    ShiftLeft(ShiftLeft),
    ShiftRight(ShiftRight),
    Equal(Equal),
    NotEqual(NotEqual),
    Less(Less),
    LessEqual(LessEqual),
    Greater(Greater),
    GreaterEqual(GreaterEqual),
    Negate(Negate),
    BooleanNot(BooleanNot),
    BitNot(BitNot),
    LoopParameter(LoopParameter),
    ShortCircuitAnd(ShortCircuitAnd),
    ShortCircuitOr(ShortCircuitOr),
    IntegerLiteral(IntegerLiteral),
    FloatLiteral(FloatLiteral),
    BooleanLiteral(BooleanLiteral),
    TextLiteral(TextLiteral),
    UnitValue(UnitValue),
    NumericCast(NumericCast),
    DirectCall(DirectCall),
    MethodCall(MethodCall),
    ExternalCall(ExternalCall),
    IntrinsicCall(IntrinsicCall),
    CallableCall(CallableCall),
    ConstructStruct(ConstructStruct),
    ConstructEnum(ConstructEnum),
    ConstructTuple(ConstructTuple),
    ConstructArray(ConstructArray),
    RepeatArray(RepeatArray),
    ExtractTupleField(ExtractTupleField),
    ExtractVariantField(ExtractVariantField),
    ProjectField(ProjectField),
    ProjectTupleField(ProjectTupleField),
    Dereference(Dereference),
    IndexPlace(IndexPlace),
    SequenceLength(SequenceLength),
    SlicePlace(SlicePlace),
    SliceView(SliceView),
    TryTextSlice(TryTextSlice),
    IfDecision(IfDecision),
    IfLetDecision(IfLetDecision),
    MatchDecision(MatchDecision),
    MergeValue(MergeValue),
    LoopControl(LoopControl),
    WhileControl(WhileControl),
    ForControl(ForControl),
    IterationIndex(IterationIndex),
    PatternMatches(PatternMatches),
    BreakControl(BreakControl),
    ContinueControl(ContinueControl),
    ReturnControl(ReturnControl),
    PropagateResult(PropagateResult),
    PropagateOption(PropagateOption),
    UnwrapResult(UnwrapResult),
    UnwrapOption(UnwrapOption),
    CreateClosure(CreateClosure),
    AdaptCallable(AdaptCallable),
    CreateFuture(CreateFuture),
    CreateContractFuture(CreateContractFuture),
    CaptureMove(CaptureMove),
    CaptureCopy(CaptureCopy),
    CaptureParametric(CaptureParametric),
    EnterMoveBlock(EnterMoveBlock),
    AwaitValue(AwaitValue),
    YieldExecution(YieldExecution),
    BeginBranch(BeginBranch),
    CompleteBranch(CompleteBranch),
    BeginLockEffect(BeginLockEffect),
    EndLockEffect(EndLockEffect),
    DropValue(DropValue),
    AdoptOwnedValue(AdoptOwnedValue),
    ReleaseOwnedValue(ReleaseOwnedValue),
    AllocatePoolSlot(AllocatePoolSlot),
    TryAllocatePoolSlot(TryAllocatePoolSlot),
    CreateGrowingStorage(CreateGrowingStorage),
    GrowStorage(GrowStorage),
    EnterUnchecked(EnterUnchecked),
    ExitUnchecked(ExitUnchecked),
    AddressOf(AddressOf),
    ForeignC(ForeignC),
    ForeignCpp(ForeignCpp),
    ForeignAssembly(ForeignAssembly),
    RuntimeCheckOperation(RuntimeCheckOperation),
}

#[derive(Debug, Clone)]
pub struct ReadModifyWriteMoments {
    pub read_previous: ExecutionMomentId,
    pub compute: ExecutionMomentId,
    pub write: ExecutionMomentId,
}
#[derive(Debug, Clone)]
pub struct ReplacementPlan {
    pub previous: ValueId,
    pub cleanup: DestructorId,
    pub write_after: ExecutionMomentId,
}
#[derive(Debug, Clone)]
pub struct CallArgument {
    pub parameter_index: u32,
    pub value: ValueId,
    pub transfer: TransferKind,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TransferKind {
    ByTypeParameter(TypeId),
    Move,
    PrimitiveCopy,
    EligibleEnumCopy,
    SharedBorrow,
    MutableBorrow,
}

#[derive(Debug, Clone)]
pub struct ResolvedTransferOccurrence {
    pub id: TransferOccurrenceId,
    pub operation: OperationId,
    pub moment: ExecutionMomentId,
    pub origin: SourceOriginId,
    pub role: TransferRole,
    pub subject: TransferSubject,
    pub ty: TypeId,
    pub mode: TransferKind,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TransferRole {
    Operation,
    Argument(u32),
    Component(PositionSelector),
    ExtractedValue,
    Capture(FieldId),
    PatternBinding(BindingId),
    IterationElement,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TransferSubject {
    Value(ValueId),
    Binding(BindingId),
    IterationSource(ValueId),
}
#[derive(Debug, Clone)]
pub struct ResolvedMethodCall {
    pub target: MethodTarget,
    pub receiver: ValueId,
    pub mode: ReceiverMode,
    pub matched_contract: Option<ContractMatchId>,
}
#[derive(Debug, Clone)]
pub enum MethodTarget {
    ContractAlternatives(NonEmpty<ContractMethodReference>),
    Concrete(FunctionInstanceId),
    ContractRequirement {
        contract: TypeContractId,
        alternative: ContractAlternativeId,
        requirement_index: u32,
        signature: SignatureId,
    },
}
#[derive(Debug, Clone)]
pub struct ResolvedExternalCall {
    pub function: FunctionInstanceId,
    pub abi: AbiId,
}
#[derive(Debug, Clone)]
pub struct ResolvedCallableCall {
    pub callable: ValueId,
    pub signature: SignatureId,
    pub mode: ReceiverMode,
}
#[derive(Debug, Clone)]
pub struct ComponentInitialization {
    pub position: PositionSelector,
    pub value: ValueId,
    pub transfer: TransferKind,
}
#[derive(Debug, Clone)]
pub struct StructuralReplicationPlan {
    pub ty: TypeId,
    pub strategy: StructuralReplicationStrategy,
}
#[derive(Debug, Clone)]
pub enum StructuralReplicationStrategy {
    /// Zero or one destination: no duplication is requested.
    NoDuplication,
    Primitive,
    Struct(Vec<StructuralFieldReplication>),
    /// Resolved eligibility evidence for the later rule checker, not a proof.
    Ineligible(StructuralReplicationRestriction),
}
#[derive(Debug, Clone)]
pub struct StructuralFieldReplication {
    pub field: FieldId,
    pub plan: StructuralReplicationPlan,
}
#[derive(Debug, Clone)]
pub enum StructuralReplicationRestriction {
    CustomDestructor(FunctionId),
    NonStructuralType,
    RecursiveType,
}
#[derive(Debug, Clone)]
pub enum ResolvedDereference {
    NativeReference,
    NativeAllocation,
    /// The call has already been emitted. This operation only dereferences its result.
    MethodResult {
        function: FunctionInstanceId,
        permission: ReferencePermission,
    },
}
#[derive(Debug, Clone)]
pub enum ResolvedIndexAccess {
    Contiguous {
        element: TypeId,
    },
    Intrinsic {
        target: IntrinsicId,
        effects: EffectSummaryId,
    },
}
#[derive(Debug, Clone)]
pub enum ResolvedSliceAccess {
    Contiguous {
        element: TypeId,
    },
    Intrinsic {
        target: IntrinsicId,
        effects: EffectSummaryId,
    },
}

#[derive(Debug, Clone)]
pub struct ResolvedMatchArm {
    pub pattern: ResolvedPattern,
    pub branch: BranchId,
    pub guard: PredicateId,
}
#[derive(Debug, Clone)]
pub enum ResolvedPattern {
    Wildcard,
    Unit,
    Binding {
        binding: BindingId,
        transfer: TransferKind,
    },
    Tuple(Vec<ResolvedPattern>),
    Variant {
        variant: VariantId,
        fields: Vec<PatternField>,
    },
}
#[derive(Debug, Clone)]
pub struct PatternField {
    pub field: FieldId,
    pub pattern: ResolvedPattern,
}
#[derive(Debug, Clone)]
pub enum ResolvedIteration {
    FixedArray {
        length: u64,
        element: TypeId,
        transfer: TransferKind,
    },
    BorrowedSlice {
        length: ValueId,
        element: TypeId,
        permission: ReferencePermission,
    },
    NextMethod {
        method: FunctionInstanceId,
        option_type: TypeId,
        some: VariantId,
        none: VariantId,
        payload: TypeId,
        matched_contract: Option<ContractMatchId>,
    },
}
#[derive(Debug, Clone)]
pub enum ErrorConversion {
    Identity,
    From(FunctionInstanceId),
}
#[derive(Debug, Clone)]
pub enum AwaitProtocol {
    ContractMethod {
        target: MethodTarget,
        signature: SignatureId,
    },
    Handle {
        output: TypeId,
        signature: SignatureId,
    },
    GeneratedFuture {
        function: FunctionInstanceId,
        body: BodyId,
    },
    PollMethod(FunctionInstanceId),
}
#[derive(Debug, Clone)]
pub struct ResolvedAwait {
    pub protocol: AwaitProtocol,
    pub result: TypeId,
    pub completion: Option<CompletionCapabilityId>,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ForeignOperandId(pub u32);
#[derive(Debug, Clone)]
pub struct ForeignWriteback {
    pub place: EvaluatedPlaceId,
    pub result: ValueId,
}
#[derive(Debug, Clone)]
pub enum ForeignOperandMode {
    ScalarValue,
    SharedStorage,
    MutableStorage,
}
#[derive(Debug, Clone)]
pub struct ForeignOperand {
    pub place: EvaluatedPlaceId,
    pub mode: ForeignOperandMode,
    pub id: ForeignOperandId,
    pub spelling: String,
    pub value: ValueId,
    pub ty: TypeId,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub enum ForeignBoundaryEffects {
    Declared(EffectSummaryId),
    UncheckedOpaque { enclosing_scope: ScopeId },
}
#[derive(Debug, Clone)]
pub struct ForeignRegion {
    pub id: ForeignRegionId,
    /// Already separated using lexer operand spans; no interpolation reparse.
    pub fragments: Vec<ForeignFragment>,
    pub headers: Vec<String>,
    pub origin: SourceOriginId,
}

// ---------- Rule obligations and derived validation results are distinct. ----------
#[derive(Debug, Clone)]
pub enum ForeignFragment {
    Text(String),
    Operand(ForeignOperandId),
}

#[derive(Debug, Clone)]
pub struct ObligationSite {
    pub id: ObligationId,
    pub operation: OperationId,
    pub moment: ExecutionMomentId,
    pub guard: PredicateId,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub struct RuleObligations {
    pub execution_context: Vec<ExecutionContextRequirement>,
    pub n1: Vec<InitializationAndTypeObligation>,
    pub n2: Vec<UniqueCleanupOwnerObligation>,
    pub n3: Vec<TransferAndMutationObligation>,
    pub n4: Vec<LifetimeObligation>,
    pub n5: Vec<AccessCompatibilityObligation>,
    pub n6: Vec<PathValidityObligation>,
    pub n7: Vec<DestructionObligation>,
    pub n8: Vec<BoundaryContractObligation>,
}
/// Facts for a later N8 check, not a proof or a semantic-resolution rejection.
#[derive(Debug, Clone)]
pub struct ExecutionContextRequirement {
    pub operation: OperationId,
    pub function: FunctionInstanceId,
    pub actual: FunctionExecution,
    pub required: FunctionExecution,
}
#[derive(Debug, Clone)]
pub struct InitializationAndTypeObligation {
    pub site: ObligationSite,
    pub requirement: InitializationAndTypeRequirement,
}
#[derive(Debug, Clone)]
pub enum InitializationAndTypeRequirement {
    TypeIdentity {
        value: ValueId,
        expected: TypeId,
        actual: TypeId,
    },
    RuntimeCheck {
        check: CheckId,
    },
}
#[derive(Debug, Clone)]
pub struct UniqueCleanupOwnerObligation {
    pub site: ObligationSite,
    /// Exact resolved ownership transition whose uniqueness must be proved.
    pub link: OwnershipLinkId,
    pub entity: EntityId,
}
#[derive(Debug, Clone)]
pub struct TransferAndMutationObligation {
    pub site: ObligationSite,
    pub requirement: TransferAndMutationRequirement,
}
#[derive(Debug, Clone)]
pub enum TransferAndMutationRequirement {
    Transfer {
        occurrence: TransferOccurrenceId,
        subject: TransferSubject,
        ty: TypeId,
        mode: TransferKind,
    },
    MutationPermission {
        target: EvaluatedPlaceId,
        access: AccessKind,
    },
    StructuralReplication {
        plan: StructuralReplicationPlan,
    },
}
#[derive(Debug, Clone)]
pub struct LifetimeObligation {
    pub site: ObligationSite,
    pub requirement: LifetimeProofRequirement,
}
#[derive(Debug, Clone)]
pub enum LifetimeProofRequirement {
    /// Exact resolved dependency whose lifetime/preservation must be proved.
    DependencyLink {
        link: DependencyLinkId,
        /// Present when the dependency has an immediate outlives subject.
        /// Symbolic carried dependencies are proved preserved by their link.
        lifetime: Option<LifetimeRequirementId>,
    },
    StoredValue {
        target: EvaluatedPlaceId,
        value: ValueId,
    },
    EscapingValue {
        value: ValueId,
    },
    TransferDestination {
        transfer: u32,
    },
    FinalDestination {
        destination: FinalDestinationId,
    },
    OperationDependencies {
        operation: OperationId,
        value: Option<ValueId>,
        source: Option<EvaluatedPlaceId>,
    },
    BranchDependencies {
        call: OperationId,
        task: ValueId,
        capability: CompletionCapabilityId,
    },
}
#[derive(Debug, Clone)]
pub struct AccessCompatibilityObligation {
    pub site: ObligationSite,
    pub requirement: AccessCompatibilityRequirement,
}
#[derive(Debug, Clone)]
pub enum AccessCompatibilityRequirement {
    PlaceAccess {
        place: PlaceId,
        access: AccessKind,
        lock: Option<LockIdentityId>,
    },
    LockAcquisition {
        call: OperationId,
        contract: LockContractId,
    },
}
#[derive(Debug, Clone)]
pub enum AccessKind {
    Move,
    Read,
    Write,
    SharedBorrow,
    MutableBorrow,
    Destroy,
    Reclaim,
}
#[derive(Debug, Clone)]
pub struct PathValidityObligation {
    pub site: ObligationSite,
    pub requirement: PathValidityRequirement,
}
#[derive(Debug, Clone)]
pub enum PathValidityRequirement {
    BindingAvailable {
        binding: BindingId,
    },
    MatchExhaustive {
        decision: OperationId,
        subject: ValueId,
        unmatched: PredicateId,
    },
}
#[derive(Debug, Clone)]
pub struct DestructionObligation {
    pub site: ObligationSite,
    pub requirement: DestructionRequirement,
}

#[derive(Debug, Clone)]
pub enum DestructionRequirement {
    /// The candidate must be destroyed on every path, either explicitly before
    /// this exit or by the verified cleanup sequence at the exit.
    CleanupCandidate {
        candidate: CleanupCandidateId,
        subject: DestructionSubject,
        storage: Option<StorageOriginId>,
    },
    /// The operation referenced by `site` is the explicit destruction.
    ExplicitDrop {
        value: ValueId,
        destructor: DestructorId,
        subject: DestructionSubject,
        storage: Option<StorageOriginId>,
    },
    /// A declared destructor has the synchronous `drop(&mut self)` contract
    /// and returns unit.
    DestructorContract { destructor: DestructorId },
    /// User code must not call a destructor hook directly.
    ReservedDestructorCall {
        call: OperationId,
        destructor: DestructorId,
    },
    PartialMoveCleanup {
        source: ValueId,
        transfer: TransferKind,
    },
}
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum DestructionSubject {
    Value(ValueId),
    Entity(EntityId),
}
#[derive(Debug, Clone)]
pub struct BoundaryContractObligation {
    pub site: ObligationSite,
    pub requirement: BoundaryContractRequirement,
}
#[derive(Debug, Clone)]
pub enum BoundaryContractRequirement {
    CallContract {
        call: OperationId,
        effects: EffectSummaryId,
    },
    ExecutionContext {
        operation: OperationId,
        function: FunctionInstanceId,
        actual: FunctionExecution,
        required: FunctionExecution,
    },
    ThreadTransfer {
        call: OperationId,
        task: ValueId,
        ty: TypeId,
    },
}
#[derive(Debug, Clone)]
pub struct ValidationResult {
    pub condition_nodes: Vec<VerifiedConditionNode>,
    pub cleanup: Vec<VerifiedExitCleanup>,
    pub proofs: Vec<Proof>,
    pub binding_states: Vec<BindingStateAtMoment>,
    pub ownership_states: Vec<OwnershipStateAtMoment>,
    pub checks: Vec<CheckDisposition>,
}
#[derive(Debug, Clone)]
pub struct Proof {
    pub id: ProofId,
    pub obligation: ObligationId,
    pub premises: Vec<ProofId>,
}
#[derive(Debug, Clone)]
pub struct BindingStateAtMoment {
    pub condition: VerifiedPathCondition,
    pub binding: BindingId,
    pub at: MomentOccurrence,
    pub guard: PredicateId,
    pub state: BindingState,
}
#[derive(Debug, Clone)]
pub enum BindingState {
    Uninitialized,
    Available(ValueId),
    Moved {
        at: ExecutionMomentId,
        destination: Owner,
    },
    Destroyed {
        at: ExecutionMomentId,
    },
}
#[derive(Debug, Clone)]
pub struct OwnershipStateAtMoment {
    pub condition: VerifiedPathCondition,
    pub entity: EntityOccurrence,
    pub at: MomentOccurrence,
    pub guard: PredicateId,
    pub owner: Owner,
    pub scope: ScopeId,
}
#[derive(Debug, Clone)]
pub enum RuntimeCheck {
    PoolCapacity {
        id: CheckId,
        pool: ValueId,
        required: ValueId,
    },
    IntegerOverflow(IntegerOverflowCheck),
    ZeroDivisor(ZeroDivisorCheck),
    ShiftCount(ShiftCountCheck),
    IndexBounds(IndexBoundsCheck),
    SliceBounds(SliceBoundsCheck),
    Utf8Boundary(Utf8BoundaryCheck),
    ExactConversion(ExactConversionCheck),
    Capacity(CapacityCheck),
    Utf8(Utf8Check),
    Variant(VariantCheck),
    Unwrap(UnwrapCheck),
}
#[derive(Debug, Clone)]
pub struct IntegerOverflowCheck {
    pub id: CheckId,
    pub operation: OperationId,
    pub ty: TypeId,
}
#[derive(Debug, Clone)]
pub struct ZeroDivisorCheck {
    pub id: CheckId,
    pub divisor: ValueId,
}
#[derive(Debug, Clone)]
pub struct ShiftCountCheck {
    pub id: CheckId,
    pub count: ValueId,
    pub width: u16,
}
#[derive(Debug, Clone)]
pub struct IndexBoundsCheck {
    pub id: CheckId,
    pub index: ValueId,
    pub length: ValueId,
}
#[derive(Debug, Clone)]
pub struct Utf8BoundaryCheck {
    pub id: CheckId,
    pub source: EvaluatedPlaceId,
    pub boundary: ValueId,
}
#[derive(Debug, Clone)]
pub struct SliceBoundsCheck {
    pub id: CheckId,
    pub start: ValueId,
    pub end: ValueId,
    pub length: ValueId,
}
#[derive(Debug, Clone)]
pub struct ExactConversionCheck {
    pub id: CheckId,
    pub value: ValueId,
    pub target: TypeId,
}
#[derive(Debug, Clone)]
pub struct CapacityCheck {
    pub id: CheckId,
    pub storage: StorageOriginId,
    pub required: ValueId,
}
#[derive(Debug, Clone)]
pub struct Utf8Check {
    pub id: CheckId,
    pub bytes: ValueId,
}
#[derive(Debug, Clone)]
pub struct VariantCheck {
    pub id: CheckId,
    pub subject: ValueId,
    pub variant: VariantId,
}
#[derive(Debug, Clone)]
pub struct UnwrapCheck {
    pub id: CheckId,
    pub subject: ValueId,
    pub success_variant: VariantId,
}
#[derive(Debug, Clone)]
pub enum CheckDisposition {
    Proven {
        check: CheckId,
        proof: ProofId,
    },
    Runtime {
        check: CheckId,
        failure: FailureContinuation,
    },
}
#[derive(Debug, Clone)]
pub enum FailureContinuation {
    Abort { origin: SourceOriginId },
    Propagate { value: ValueId, exit: ScopeExitId },
}

// ---------- Enrichment plans consume PostAst; they never redo resolution. ----------
// Phase envelopes are defined once in post_ast_passes.rs. This file contains
// the shared semantic payload and plan data; no competing forward pipeline.
#[derive(Debug, Clone)]
pub struct TargetLayoutPlan {
    pub layouts: Vec<TypeLayout>,
    pub abi: AbiId,
}
#[derive(Debug, Clone)]
pub struct TypeLayout {
    pub id: LayoutId,
    pub ty: TypeId,
    pub size: LayoutSize,
    pub alignment: u64,
    pub fields: Vec<FieldLayout>,
    /// Physical offsets of tuple elements. These are planned here so a
    /// backend never repeats ABI alignment decisions.
    pub tuple_elements: Vec<TupleElementLayout>,
    /// Physical stride/length of a fixed array, when this type is an array.
    pub sequence: Option<SequenceLayout>,
    pub variant: Option<EnumLayout>,
    /// Exact compiler-owned descriptor layout, when the runtime value is a
    /// native descriptor rather than a user aggregate. Backends consume these
    /// offsets and must not reconstruct them from a type name or convention.
    pub native: Option<NativeDescriptorLayout>,
}
#[derive(Debug, Clone)]
pub enum NativeDescriptorLayout {
    View {
        pointer: u64,
        length: u64,
    },
    ThinReference {
        pointer: u64,
    },
    Callable {
        function: u64,
        environment: u64,
    },
    /// Exact `corbo_allocation` ABI from `runtime/cpp/pools.hpp`.
    Allocation {
        pool: u64,
        slot: u64,
        index: u64,
    },
    /// Exact `corbo_region` ABI from `runtime/cpp/regions.hpp`.
    Region {
        band: u64,
        data: u64,
        index: u64,
        length: u64,
        width: u64,
        maximum: u64,
        destroy: u64,
    },
    /// Exact `corbo_map` ABI from `runtime/cpp/maps.hpp`.
    Map {
        entries: u64,
        index: u64,
        value_width: u64,
        value_offset: u64,
        count: u64,
        free_head: u64,
        destroy: u64,
    },
    InlineUtf8 {
        length: u64,
        data: u64,
        maximum_bytes: u64,
    },
    /// Exact `corbo_task_value` ABI from `runtime/cpp/tasks.hpp`.
    ExecutionHandle {
        state: u64,
    },
    /// Exact `corbo_pool` ABI from `runtime/cpp/pools.hpp`.
    Pool {
        state: u64,
    },
    ContractFuture {
        state: u64,
        poll: u64,
    },
}
#[derive(Debug, Clone)]
pub struct TupleElementLayout {
    pub position: u32,
    pub byte_offset: u64,
    pub layout: LayoutId,
}
#[derive(Debug, Clone)]
pub struct SequenceLayout {
    pub element: LayoutId,
    pub stride: u64,
    pub length: u64,
}
#[derive(Debug, Clone)]
pub enum LayoutSize {
    Fixed(u64),
    FromValue(ValueId),
}
#[derive(Debug, Clone)]
pub struct FieldLayout {
    pub field: FieldId,
    pub byte_offset: u64,
    pub layout: LayoutId,
}
#[derive(Debug, Clone)]
pub struct EnumLayout {
    pub discriminant_bytes: u8,
    pub payload_offset: u64,
    pub variants: Vec<VariantLayout>,
}
#[derive(Debug, Clone)]
pub struct VariantLayout {
    pub variant: VariantId,
    pub discriminant: u64,
    pub fields: Vec<FieldLayout>,
}
#[derive(Debug, Clone)]
pub struct StoragePlan {
    pub stacks: Vec<DataStackPlan>,
    /// Physical cursor inherited when each runtime scope is entered.
    pub scope_entries: Vec<ScopeCursorPlan>,
    pub regions: Vec<RegionPlan>,
    pub region_classes: Vec<RegionClassPlan>,
    pub origins: Vec<StorageOriginId>,
    pub reservations: Vec<StorageReservation>,
    /// Complete physical source for every resolved value. Code generation
    /// must consume this table and may not invent C++ locals or storage.
    pub values: Vec<ValueStoragePlan>,
    /// Physical value transfers attached to already-resolved execution edges.
    /// Loop-carried values use these transfers so code generation never
    /// evaluates a back-edge predicate before the first loop iteration.
    pub edge_transfers: Vec<EdgeValueTransfer>,
    /// Planned control counters for symbolic `for` iteration coordinates.
    pub iteration_counters: Vec<IterationCounterPlan>,
    pub backings: Vec<BackingStoragePlan>,
    /// Complete physical cursor expressions. The backend follows these
    /// directly and never reconstructs stack arithmetic.
    pub cursors: Vec<CursorExpression>,
    pub snapshots: Vec<CursorSnapshot>,
}

#[derive(Debug, Clone, Copy)]
pub struct ScopeCursorPlan {
    pub scope: ScopeId,
    pub cursor: CursorExpressionId,
}

#[derive(Debug, Clone)]
pub struct EdgeValueTransfer {
    pub from: ExecutionMomentId,
    pub to: ExecutionMomentId,
    pub destination: ValueId,
    pub source: ValueId,
    pub guard: PredicateId,
}

#[derive(Debug, Clone)]
pub struct IterationCounterPlan {
    pub coordinate: IterationVariableId,
    pub region: LoopRegionId,
    pub entry_edges: Vec<ExecutionEdgePoint>,
    pub back_edges: Vec<ExecutionEdgePoint>,
}

#[derive(Debug, Clone, Copy)]
pub struct ExecutionEdgePoint {
    pub from: ExecutionMomentId,
    pub to: ExecutionMomentId,
}

#[derive(Debug, Clone)]
pub struct ValueStoragePlan {
    pub value: ValueId,
    pub layout: Option<LayoutId>,
    pub alternatives: NonEmpty<GuardedValueStorage>,
}

#[derive(Debug, Clone)]
pub struct GuardedValueStorage {
    pub guard: PredicateId,
    pub kind: ValueStorageKind,
}

#[derive(Debug, Clone)]
pub enum ValueStorageKind {
    /// Durable storage selected by final-destination planning.
    Reservation(StorageReservationId),
    /// The value is another resolved name for the same physical bytes.
    Alias {
        source: ValueId,
        bound_at: ExecutionMomentId,
    },
    /// Parametric transfer selects one of two already-planned physical values.
    SelectAlias {
        predicate: PredicateId,
        when_true: ValueId,
        when_false: ValueId,
        bound_at: ExecutionMomentId,
    },
    /// Ephemeral fixed value in the scope's planned datastack range.
    Temporary {
        scope: ScopeId,
        stack: DataStackId,
        start: CursorExpressionId,
        end: CursorExpressionId,
        allocated_at: ExecutionMomentId,
    },
    /// Storage is supplied by the caller according to the resolved signature.
    Parameter { binding: BindingId },
    /// Storage is a field of the resolved closure environment.
    Capture {
        record: CaptureRecordId,
        field: FieldId,
    },
    /// Immutable bytes are emitted from the resolved constant value.
    Constant,
    /// The semantic value has no runtime representation.
    None(ValueStorageAbsence),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ValueStorageAbsence {
    Diverged,
    Never,
    AbstractType,
    UnsizedData,
}
#[derive(Debug, Clone)]
pub struct StorageOrigin {
    pub id: StorageOriginId,
    pub creation: StorageCreation,
    pub pool: Option<ValueId>,
    pub pool_choices: Vec<GuardedPoolOrigin>,
}
#[derive(Debug, Clone)]
pub enum StorageCreation {
    Operation(OperationId),
    Static(SourceOriginId),
    CallerResult(FunctionInstanceId),
}
#[derive(Debug, Clone)]
pub struct LogicalDataStack {
    pub id: DataStackId,
    pub kind: DataStackKind,
}
#[derive(Debug, Clone)]
pub struct StorageReservation {
    pub id: StorageReservationId,
    pub value: ValueId,
    pub destination: ScopeId,
    pub storage: StorageOriginId,
    pub layout: LayoutId,
    pub guard: PredicateId,
    pub reserved_at: ExecutionMomentId,
    /// Cursor range selected by the planner. Construction initializes this
    /// already-reserved range; moves keep the same range and storage origin.
    pub stack: DataStackId,
    pub region: Option<RegionId>,
    pub start: CursorExpressionId,
    pub end: CursorExpressionId,
    pub retained_until: Vec<CompletionCapabilityId>,
}
#[derive(Debug, Clone)]
pub struct BackingStoragePlan {
    pub owner: ValueId,
    pub kind: BackingStorageKind,
}
#[derive(Debug, Clone)]
pub enum BackingStorageKind {
    /// Pool slots are fixed-size storage on the classic data stack.
    PoolSlots {
        element: TypeId,
        capacity: ValueId,
        stack: DataStackId,
        state_start: CursorExpressionId,
        state_end: CursorExpressionId,
        slots_start: CursorExpressionId,
        slots_end: CursorExpressionId,
        occupancy_start: CursorExpressionId,
        occupancy_end: CursorExpressionId,
        free_slots_start: CursorExpressionId,
        free_slots_end: CursorExpressionId,
    },
    /// Growing collection bytes live in a bounded region. The descriptor
    /// itself remains in its ordinary fixed-value reservation.
    GrowingRegion { region: RegionId },
}
#[derive(Debug, Clone)]
pub struct DataStackPlan {
    pub id: DataStackId,
    pub kind: DataStackKind,
    pub capacity: MemoryBudget,
}
#[derive(Debug, Clone)]
pub enum DataStackKind {
    FixedValues,
    GrowingRegions,
}
#[derive(Debug, Clone)]
pub enum MemoryBudget {
    Explicit(u64),
    Inferred(u64),
    PlatformDefault,
}
#[derive(Debug, Clone)]
pub struct RegionPlan {
    pub id: RegionId,
    pub stack: DataStackId,
    pub class: Option<RegionClassId>,
    pub size: MemoryBudget,
    pub owner: ScopeId,
    pub retained_until: Vec<CompletionCapabilityId>,
}
#[derive(Debug, Clone)]
pub struct RegionClassPlan {
    pub id: RegionClassId,
    pub declaring_scope: ScopeId,
    /// Exact event at which the runtime band becomes current.
    pub entered_at: ExecutionMomentId,
    pub stack: DataStackId,
    pub maximum_bytes: u64,
    pub reserved_slots: Option<u64>,
}
#[derive(Debug, Clone)]
pub struct CursorExpression {
    pub id: CursorExpressionId,
    pub kind: CursorExpressionKind,
}
#[derive(Debug, Clone)]
pub enum CursorExpressionKind {
    ScopeUpperLimit(ScopeId),
    IncomingScopeCursor(ScopeId),
    AdvanceByType {
        base: CursorExpressionId,
        ty: TypeId,
    },
    /// Align a cursor without allocating. The result is a physical address
    /// boundary chosen by the planner, not by code generation.
    Align {
        base: CursorExpressionId,
        alignment: u64,
    },
    /// Advance over a compiler/runtime-owned fixed ABI record.
    AdvanceFixedBytes {
        base: CursorExpressionId,
        bytes: u64,
    },
    /// Advance over a fixed-slot pool area. The element layout and count are
    /// already resolved; no later stage reinterprets the source expression.
    AdvancePoolSlots {
        base: CursorExpressionId,
        element: TypeId,
        count: ValueId,
    },
    AdvanceBytes {
        base: CursorExpressionId,
        bytes: ValueId,
    },
    /// Advance by a runtime count times a target ABI width.
    AdvanceScaledBytes {
        base: CursorExpressionId,
        count: ValueId,
        width: u64,
    },
    Entry(CursorSnapshotId),
    Offset {
        base: CursorExpressionId,
        bytes: ValueId,
    },
    Merge(NonEmpty<GuardedCursor>),
}
#[derive(Debug, Clone)]
pub struct GuardedCursor {
    pub guard: PredicateId,
    pub cursor: CursorExpressionId,
}
#[derive(Debug, Clone)]
pub struct CursorSnapshot {
    pub id: CursorSnapshotId,
    pub scope: ScopeId,
    pub moment: ExecutionMomentId,
    pub cursor: CursorExpressionId,
}
#[derive(Debug, Clone)]
pub struct CleanupPlan {
    pub exits: Vec<ExitCleanup>,
}
#[derive(Debug, Clone)]
pub struct ExitCleanup {
    pub exit: ScopeExitId,
    pub actions: Vec<CleanupAction>,
}
#[derive(Debug, Clone)]
pub enum CleanupAction {
    InvokeUserDestructor {
        value: ValueId,
        function: FunctionInstanceId,
    },
    DestroyOwnedComponent {
        value: ValueId,
        position: PositionSelector,
        destructor: DestructorId,
    },
    ReleaseAllocation {
        address: AddressId,
        storage: StorageOriginId,
    },
    RewindCursor {
        snapshot: CursorSnapshotId,
        after: Vec<CompletionCapabilityId>,
    },
    ReturnRegion {
        region: RegionId,
        after: Vec<CompletionCapabilityId>,
    },
    /// Restore the parent band once, after all regions in this class have
    /// released their slots.
    RestoreRegionClass {
        class: RegionClassId,
        after: Vec<CompletionCapabilityId>,
    },
}
#[derive(Debug, Clone)]
pub struct AsyncStatePlan {
    pub frames: Vec<AsyncFrameLayout>,
}
#[derive(Debug, Clone)]
pub struct AsyncFrameLayout {
    pub body: BodyId,
    pub ty: TypeId,
    pub layout: LayoutId,
    /// Compiler-owned field containing the poll-state discriminant. Its
    /// physical offset is fixed by the target layout pass.
    pub state_field: FieldId,
    pub state_offset: u64,
    pub completed_discriminant: u64,
    pub saved: Vec<SavedStateValue>,
    pub transitions: Vec<AsyncTransition>,
}
#[derive(Debug, Clone)]
pub struct SavedStateValue {
    pub value: ValueId,
    pub field: FieldId,
    pub byte_offset: u64,
    pub dependencies: DependencySummaryId,
}
#[derive(Debug, Clone)]
pub struct AsyncTransition {
    pub suspension: SuspensionId,
    pub resume: ExecutionMomentId,
    pub discriminant: u64,
}
#[derive(Debug, Clone)]
pub struct ForeignEmissionPlan {
    pub regions: Vec<ForeignRegion>,
    pub operands: Vec<ForeignOperandLayout>,
}
#[derive(Debug, Clone)]
pub struct ForeignOperandLayout {
    pub operand: ForeignOperandId,
    pub region: ForeignRegionId,
    pub value: ValueId,
    pub layout: LayoutId,
}
#[derive(Debug, Clone)]
pub struct RuntimeBindings {
    pub entries: Vec<RuntimeBinding>,
}
#[derive(Debug, Clone)]
pub struct RuntimeBinding {
    pub intrinsic: IntrinsicId,
    pub implementation: RuntimeEntryId,
    pub signature: SignatureId,
    pub abi: AbiId,
}

impl Operation {
    pub fn site(&self) -> &OperationSite {
        match self {
            Self::CreatePool(operation) => &operation.site,
            Self::NativeOperation(operation) => &operation.site,
            Self::EnterScope(operation) => &operation.site,
            Self::ExitScope(operation) => &operation.site,
            Self::EvaluatePlace(operation) => &operation.site,
            Self::ReadValue(operation) => &operation.site,
            Self::InitializeBinding(operation) => &operation.site,
            Self::InitializeDefault(operation) => &operation.site,
            Self::ReceiveValue(operation) => &operation.site,
            Self::ForwardResult(operation) => &operation.site,
            Self::DiscardResult(operation) => &operation.site,
            Self::MoveValue(operation) => &operation.site,
            Self::ParametricTransfer(operation) => &operation.site,
            Self::CopyPrimitive(operation) => &operation.site,
            Self::CopyEligibleEnum(operation) => &operation.site,
            Self::BorrowShared(operation) => &operation.site,
            Self::BorrowMutable(operation) => &operation.site,
            Self::ReborrowShared(operation) => &operation.site,
            Self::ReborrowMutable(operation) => &operation.site,
            Self::Assign(operation) => &operation.site,
            Self::AddAssign(operation) => &operation.site,
            Self::SubtractAssign(operation) => &operation.site,
            Self::MultiplyAssign(operation) => &operation.site,
            Self::DivideAssign(operation) => &operation.site,
            Self::RemainderAssign(operation) => &operation.site,
            Self::BitAndAssign(operation) => &operation.site,
            Self::BitOrAssign(operation) => &operation.site,
            Self::BitXorAssign(operation) => &operation.site,
            Self::ShiftLeftAssign(operation) => &operation.site,
            Self::ShiftRightAssign(operation) => &operation.site,
            Self::Add(operation) => &operation.site,
            Self::Subtract(operation) => &operation.site,
            Self::Multiply(operation) => &operation.site,
            Self::Divide(operation) => &operation.site,
            Self::Remainder(operation) => &operation.site,
            Self::BitAnd(operation) => &operation.site,
            Self::BitOr(operation) => &operation.site,
            Self::BitXor(operation) => &operation.site,
            Self::ShiftLeft(operation) => &operation.site,
            Self::ShiftRight(operation) => &operation.site,
            Self::Equal(operation) => &operation.site,
            Self::NotEqual(operation) => &operation.site,
            Self::Less(operation) => &operation.site,
            Self::LessEqual(operation) => &operation.site,
            Self::Greater(operation) => &operation.site,
            Self::GreaterEqual(operation) => &operation.site,
            Self::Negate(operation) => &operation.site,
            Self::BooleanNot(operation) => &operation.site,
            Self::BitNot(operation) => &operation.site,
            Self::LoopParameter(operation) => &operation.site,
            Self::ShortCircuitAnd(operation) => &operation.site,
            Self::ShortCircuitOr(operation) => &operation.site,
            Self::IntegerLiteral(operation) => &operation.site,
            Self::FloatLiteral(operation) => &operation.site,
            Self::BooleanLiteral(operation) => &operation.site,
            Self::TextLiteral(operation) => &operation.site,
            Self::UnitValue(operation) => &operation.site,
            Self::NumericCast(operation) => &operation.site,
            Self::DirectCall(operation) => &operation.site,
            Self::MethodCall(operation) => &operation.site,
            Self::ExternalCall(operation) => &operation.site,
            Self::IntrinsicCall(operation) => &operation.site,
            Self::CallableCall(operation) => &operation.site,
            Self::ConstructStruct(operation) => &operation.site,
            Self::ConstructEnum(operation) => &operation.site,
            Self::ConstructTuple(operation) => &operation.site,
            Self::ConstructArray(operation) => &operation.site,
            Self::RepeatArray(operation) => &operation.site,
            Self::ExtractTupleField(operation) => &operation.site,
            Self::ExtractVariantField(operation) => &operation.site,
            Self::ProjectField(operation) => &operation.site,
            Self::ProjectTupleField(operation) => &operation.site,
            Self::Dereference(operation) => &operation.site,
            Self::IndexPlace(operation) => &operation.site,
            Self::SequenceLength(operation) => &operation.site,
            Self::SlicePlace(operation) => &operation.site,
            Self::SliceView(operation) => &operation.site,
            Self::TryTextSlice(operation) => &operation.site,
            Self::IfDecision(operation) => &operation.site,
            Self::IfLetDecision(operation) => &operation.site,
            Self::MatchDecision(operation) => &operation.site,
            Self::MergeValue(operation) => &operation.site,
            Self::LoopControl(operation) => &operation.site,
            Self::WhileControl(operation) => &operation.site,
            Self::ForControl(operation) => &operation.site,
            Self::IterationIndex(operation) => &operation.site,
            Self::PatternMatches(operation) => &operation.site,
            Self::BreakControl(operation) => &operation.site,
            Self::ContinueControl(operation) => &operation.site,
            Self::ReturnControl(operation) => &operation.site,
            Self::PropagateResult(operation) => &operation.site,
            Self::PropagateOption(operation) => &operation.site,
            Self::UnwrapResult(operation) => &operation.site,
            Self::UnwrapOption(operation) => &operation.site,
            Self::CreateClosure(operation) => &operation.site,
            Self::AdaptCallable(operation) => &operation.site,
            Self::CreateFuture(operation) => &operation.site,
            Self::CreateContractFuture(operation) => &operation.site,
            Self::CaptureMove(operation) => &operation.site,
            Self::CaptureCopy(operation) => &operation.site,
            Self::CaptureParametric(operation) => &operation.site,
            Self::EnterMoveBlock(operation) => &operation.site,
            Self::AwaitValue(operation) => &operation.site,
            Self::YieldExecution(operation) => &operation.site,
            Self::BeginBranch(operation) => &operation.site,
            Self::CompleteBranch(operation) => &operation.site,
            Self::BeginLockEffect(operation) => &operation.site,
            Self::EndLockEffect(operation) => &operation.site,
            Self::DropValue(operation) => &operation.site,
            Self::AdoptOwnedValue(operation) => &operation.site,
            Self::ReleaseOwnedValue(operation) => &operation.site,
            Self::AllocatePoolSlot(operation) => &operation.site,
            Self::TryAllocatePoolSlot(operation) => &operation.site,
            Self::CreateGrowingStorage(operation) => &operation.site,
            Self::GrowStorage(operation) => &operation.site,
            Self::EnterUnchecked(operation) => &operation.site,
            Self::ExitUnchecked(operation) => &operation.site,
            Self::AddressOf(operation) => &operation.site,
            Self::ForeignC(operation) => &operation.site,
            Self::ForeignCpp(operation) => &operation.site,
            Self::ForeignAssembly(operation) => &operation.site,
            Self::RuntimeCheckOperation(operation) => &operation.site,
        }
    }
}

/// Explicit diagnostic-domain data; these records are not executable PostAST units.
#[derive(Debug, Clone)]
pub struct UnreachableSource {
    pub statements: Vec<UnreachableStatement>,
    pub bindings: Vec<DiagnosticBinding>,
    pub names: Vec<UnreachableNameUse>,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct DiagnosticBindingId(pub u32);
#[derive(Debug, Clone)]
pub struct DiagnosticBinding {
    pub id: DiagnosticBindingId,
    pub symbol: SymbolId,
    pub scope: ScopeId,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub struct UnreachableStatement {
    pub syntax: SyntaxNodeId,
    pub origin: SourceOriginId,
    pub lexical: LexicalMomentId,
    pub scope: ScopeId,
    pub after: ExecutionMomentId,
}
#[derive(Debug, Clone)]
pub struct UnreachableNameUse {
    pub origin: SourceOriginId,
    pub span: ByteSpan,
    pub scope: ScopeId,
    pub resolution: UnreachableNameResolution,
}
#[derive(Debug, Clone)]
pub enum UnreachableNameResolution {
    Resolved(SymbolId),
    Undefined { spelling: String },
}

#[derive(Debug, Clone)]
pub enum PatternTest {
    Any,
    Unit,
    Dereference(Box<PatternTest>),
    Tuple(Vec<PatternTest>),
    Variant {
        variant: VariantId,
        fields: Vec<(FieldId, PatternTest)>,
    },
}
#[derive(Debug, Clone)]
pub struct MatchCoverageRequirement {
    pub decision: OperationId,
    pub subject: ValueId,
    pub unmatched: PredicateId,
    pub origin: SourceOriginId,
}

#[derive(Debug, Clone)]
pub struct WellKnownTypes {
    pub option: Option<SymbolId>,
    pub result: Option<SymbolId>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct OverloadSetId(pub u32);
#[derive(Debug, Clone)]
pub struct FunctionOverloadSet {
    pub id: OverloadSetId,
    pub symbol: SymbolId,
    pub members: Vec<FunctionId>,
}

/// Semantic frame slots; these are not offsets or a physical frame allocation.
#[derive(Debug, Clone)]
pub struct AsyncFrame {
    pub function: FunctionInstanceId,
    pub body: BodyId,
    pub state_type: TypeId,
    /// Compiler-owned state-machine field, distinct from user bindings.
    pub state_field: FieldId,
    pub slots: Vec<AsyncFrameSlot>,
    pub suspensions: Vec<SuspensionId>,
}
#[derive(Debug, Clone)]
pub struct AsyncFrameSlot {
    pub binding: BindingId,
    pub field: FieldId,
}

#[derive(Debug, Clone)]
pub struct TypeEffectContracts {
    pub ty: TypeId,
    pub contracts: Vec<ResolvedContract>,
}
#[derive(Debug, Clone)]
pub struct LockIdentity {
    pub id: LockIdentityId,
    pub receiver: ValueId,
    pub targets: Vec<ReferenceOrigin>,
}
#[derive(Debug, Clone)]
pub enum ContractApplication {
    Lock {
        call: OperationId,
        contract: LockContractId,
        identity: LockIdentityId,
        begins: ExecutionMomentId,
        ends: Option<ExecutionMomentId>,
        carried_by: Option<ValueId>,
    },
    Branch {
        call: OperationId,
        contract: BranchContractId,
        capability: CompletionCapabilityId,
        child: BranchId,
        instance: InstanceDomainId,
    },
    Completion {
        call: OperationId,
        capability: CompletionCapabilityId,
        at: ExecutionMomentId,
        guard: PredicateId,
    },
}

#[derive(Debug, Clone)]
pub struct ConfigurationEnvironment {
    pub id: ConfigurationId,
    pub parent: Option<ConfigurationId>,
    pub replacements: Vec<(ConstantId, ConstantValue)>,
}

#[derive(Debug, Clone)]
pub enum NativeReturnRecipe {
    TaskOutputOfParameter(u32),
}
#[derive(Debug, Clone)]
pub struct HandleProtocol {
    pub ty: TypeId,
    pub join: Option<FunctionInstanceId>,
    pub awaiting: Option<SignatureId>,
}

#[derive(Debug, Clone)]
pub struct NativeTypeBinding {
    pub symbol: SymbolId,
    pub compiler_symbol: SymbolId,
    pub origin: SourceOriginId,
}

#[derive(Debug, Clone)]
pub struct ResolvedImport {
    pub file: SourceFileId,
    pub scope: ScopeId,
    pub local_name: String,
    pub target: SymbolId,
    pub origin: SourceOriginId,
}

#[derive(Debug, Clone)]
pub struct ConditionalCleanup {
    pub guard: PredicateId,
    pub value: ValueId,
    pub destructor: DestructorId,
    pub at: ExecutionMomentId,
}
#[derive(Debug, Clone)]
pub struct GuardedPoolOrigin {
    pub guard: PredicateId,
    pub pool: ValueId,
}

/// Compiler-owned primitive operations, resolved before downstream stages.
#[derive(Debug, Clone)]
pub enum PrimitiveOperation {
    Runtime {
        kind: RuntimePrimitiveKind,
        suspension: Option<SuspensionId>,
        /// Compiler-runtime status mapping resolved once for process_args.
        /// Status 1 is invalid UTF-8 and status 2 is unavailable.
        process_args_errors: Option<(VariantId, VariantId)>,
    },
    View {
        source: EvaluatedPlaceId,
        target: TypeId,
        mutable: bool,
    },
    ValidateUtf8 {
        bytes: ValueId,
        error: TypeId,
    },
    TryNumericConversion {
        source: ValueId,
        target: TypeId,
    },
}

/// Existing compiler/runtime entry points with a resolved, typed signature.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RuntimePrimitiveKind {
    ProcessArgs,
    WaitMutex,
    WaitChannel,
    WaitSocket,
    AttachSocket,
    CompleteSocket,
}

/// A source namespace explicitly exposes compiler-owned runtime declarations.
#[derive(Debug, Clone)]
pub struct NativeNamespaceBinding {
    pub module: ModuleId,
    pub compiler_scope: ScopeId,
    pub symbols: Vec<SymbolId>,
}

/// A parametric instance retains real type parameters, never sample types.
#[derive(Debug, Clone)]
pub enum InstanceResolution {
    Concrete,
    Parametric { parameters: Vec<TypeParameterId> },
}
#[derive(Debug, Clone)]
pub struct ContractMethodReference {
    pub contract: TypeContractId,
    pub alternative: ContractAlternativeId,
    pub requirement_index: u32,
    pub signature: SignatureId,
}
#[derive(Debug, Clone)]
pub struct SymbolicContractRequirement {
    pub contract: TypeContractId,
    pub actual: TypeId,
    pub substitutions: Vec<TypeSubstitution>,
    pub evidence: Vec<SymbolicContractEvidence>,
}

/// Inactive future returned by a statically contracted async method. Its
/// concrete implementation/state layout is supplied by generic instantiation.
#[derive(Debug, Clone)]
pub struct CreateContractFuture {
    pub site: OperationSite,
    pub target: MethodTarget,
    pub arguments: Vec<CallArgument>,
    pub result: ValueId,
}

/// Compile-time copy/move alternatives for an abstract type, with guarded
/// ownership identities. This is not a runtime language branch.
#[derive(Debug, Clone)]
pub struct ParametricTransfer {
    pub site: OperationSite,
    pub source: EvaluatedPlaceId,
    pub value: ValueId,
    pub ty: TypeId,
    pub copies: PredicateId,
    pub copied: ValueId,
    pub moved: ValueId,
    pub result: ValueId,
}

/// Resolution-time implication witness between declared contract alternatives.
/// Consumers follow method IDs/signatures instead of matching method names again.
#[derive(Debug, Clone)]
pub struct SymbolicContractEvidence {
    pub provided: TypeContractId,
    pub provided_alternative: ContractAlternativeId,
    pub required_alternative: ContractAlternativeId,
    pub methods: Vec<ContractMethodReference>,
}

#[derive(Debug, Clone)]
pub struct CaptureParametric {
    pub site: OperationSite,
    pub record: CaptureRecordId,
    pub source: BindingId,
    pub field: FieldId,
    pub value: ValueId,
    pub ty: TypeId,
    pub moving: bool,
}

/// Logical destruction order established before physical reclamation planning.
#[derive(Debug, Clone)]
pub struct VerifiedExitCleanup {
    pub exit: ScopeExitId,
    pub steps: Vec<VerifiedDestructionStep>,
}
#[derive(Debug, Clone)]
pub enum VerifiedDestructionStep {
    /// Full destruction of an owned component whose identity is relative to
    /// its parent. The guard is evaluated in that parent's destructor context.
    OwnedComponent {
        parent: EntityId,
        position: PositionSelector,
        destructor: DestructorId,
        component_guard: PredicateId,
        condition: VerifiedPathCondition,
    },
    Hook {
        entity: EntityId,
        destructor: DestructorId,
        guard: PredicateId,
        condition: VerifiedPathCondition,
    },
    EndLifetime {
        entity: EntityId,
        /// Exact semantic cleanup candidates whose remaining paths are closed
        /// by this end-of-lifetime step.
        candidates: Vec<CleanupCandidateId>,
        guard: PredicateId,
        condition: VerifiedPathCondition,
    },
}

/// A derived path condition over resolved identities. Consumers do not rebuild
/// the control-flow proof or resolve source expressions to interpret it.
#[derive(Debug, Clone)]
pub struct VerifiedPathCondition {
    pub root: VerifiedConditionId,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct VerifiedConditionId(pub u32);
#[derive(Debug, Clone)]
pub enum VerifiedConditionNode {
    False,
    True,
    Decision {
        atom: VerifiedConditionAtom,
        when_false: VerifiedConditionId,
        when_true: VerifiedConditionId,
    },
}
#[derive(Debug, Clone)]
pub enum VerifiedConditionAtom {
    Boolean(ValueId),
    Variant(ValueId, VariantId),
    VariantPath(ValueId, Vec<u64>, VariantId),
    Predicate(PredicateId),
    Copies(TypeId),
}
