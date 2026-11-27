//! Typed stage boundaries. Each successful stage owns the complete artifact
//! produced by the preceding stage. Physical planning consumes only checked
//! PostAST facts; it never repeats semantic resolution or rule checking.
#![allow(dead_code)]
use super::model::*;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct InferenceVariableId(pub u32);
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct TypeConstraintId(pub u32);
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct EvidenceId(pub u32);
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct DestinationRequirementId(pub u32);
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct ReservationGroupId(pub u32);
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct PhysicalPlanningProofId(pub u32);
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct PhysicalPlacementRequirementId(pub u32);

// ---------- Pass 1: information population, not proof of compliance. ----------
/// Inference variables exist only in this workspace, never in emitted PostAst.
#[derive(Debug, Clone)]
pub struct SemanticPopulationWorkspace<'syntax, Syntax> {
    /// Borrow the already parsed package/units; never reconstruct syntax here.
    pub syntax: &'syntax Syntax,
    pub declarations: Declarations,
    pub symbols: Symbols,
    pub known_types: ResolvedTypes,
    pub pending_bindings: Vec<PendingBinding>,
    pub source_roots: Vec<SourceRoot>,
    pub inference_variables: Vec<InferenceVariable>,
    pub type_constraints: Vec<TypeConstraint>,
    pub name_requests: Vec<NameResolutionRequest>,
    pub call_requests: Vec<CallResolutionRequest>,
    pub origins: SourceOrigins,
}
#[derive(Debug, Clone)]
pub struct SourceRoot {
    pub file: SourceFileId,
    pub syntax_root: SyntaxNodeId,
}
#[derive(Debug, Clone)]
pub struct PendingBinding {
    pub symbol: SymbolId,
    pub scope: ScopeId,
    pub ty: TypeTerm,
    pub source: SyntaxNodeId,
}
#[derive(Debug, Clone)]
pub struct InferenceVariable {
    pub id: InferenceVariableId,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub enum TypeTerm {
    Known(TypeId),
    InferenceVariable(InferenceVariableId),
    Reference {
        permission: ReferencePermission,
        target: Box<TypeTerm>,
    },
    Tuple(Vec<TypeTerm>),
    Array {
        element: Box<TypeTerm>,
        length: u64,
    },
    Slice {
        element: Box<TypeTerm>,
    },
    Callable {
        parameters: Vec<TypeTerm>,
        result: Box<TypeTerm>,
    },
    Application {
        constructor: SymbolId,
        arguments: Vec<InferenceTypeArgument>,
    },
}
#[derive(Debug, Clone)]
pub enum InferenceTypeArgument {
    Type(TypeTerm),
    Integer(u64),
}
#[derive(Debug, Clone)]
pub struct ConstraintOrigin {
    pub id: TypeConstraintId,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub enum TypeConstraint {
    SameType(SameTypeConstraint),
    ExpectedType(ExpectedTypeConstraint),
    LiteralFits(LiteralFitsConstraint),
    ResultJoin(ResultJoinConstraint),
    CallParameter(CallParameterConstraint),
    ReturnType(ReturnTypeConstraint),
    ArrayElement(ArrayElementConstraint),
}
#[derive(Debug, Clone)]
pub struct SameTypeConstraint {
    pub site: ConstraintOrigin,
    pub left: TypeTerm,
    pub right: TypeTerm,
}
#[derive(Debug, Clone)]
pub struct ExpectedTypeConstraint {
    pub site: ConstraintOrigin,
    pub expression: SyntaxNodeId,
    pub expected: TypeTerm,
}
#[derive(Debug, Clone)]
pub struct LiteralFitsConstraint {
    pub site: ConstraintOrigin,
    pub literal: SourceOriginId,
    pub expected: TypeTerm,
}
#[derive(Debug, Clone)]
pub struct ResultJoinConstraint {
    pub site: ConstraintOrigin,
    pub incoming: NonEmpty<GuardedTypeTerm>,
    pub result: TypeTerm,
}
#[derive(Debug, Clone)]
pub struct GuardedTypeTerm {
    pub guard: PredicateId,
    pub ty: TypeTerm,
}
#[derive(Debug, Clone)]
pub struct CallParameterConstraint {
    pub site: ConstraintOrigin,
    pub call: SyntaxNodeId,
    pub parameter: u32,
    pub argument: TypeTerm,
    pub required: TypeTerm,
}
#[derive(Debug, Clone)]
pub struct ReturnTypeConstraint {
    pub site: ConstraintOrigin,
    pub function: FunctionId,
    pub returned: TypeTerm,
    pub required: TypeTerm,
}
#[derive(Debug, Clone)]
pub struct ArrayElementConstraint {
    pub site: ConstraintOrigin,
    pub array: SyntaxNodeId,
    pub element: TypeTerm,
    pub required: TypeTerm,
}
#[derive(Debug, Clone)]
pub struct NameResolutionRequest {
    pub origin: SourceOriginId,
    pub scope: ScopeId,
    pub syntax: SyntaxNodeId,
}
#[derive(Debug, Clone)]
pub struct CallResolutionRequest {
    pub origin: SourceOriginId,
    pub scope: ScopeId,
    pub syntax: SyntaxNodeId,
    pub receiver: Option<TypeTerm>,
}

#[derive(Debug, Clone)]
pub struct SemanticPopulationResult {
    pub post_ast: PostAst,
    pub type_derivations: Vec<TypeDerivation>,
    pub lifetimes: LifetimeFacts,
    pub destinations: DestinationRequirements,
    pub coverage: PopulationCoverage,
}
#[derive(Debug, Clone)]
pub struct TypeDerivation {
    pub value: ValueId,
    pub resolved: TypeId,
    pub origin: SourceOriginId,
    pub reason: TypeDerivationReason,
}
#[derive(Debug, Clone)]
pub enum TypeDerivationReason {
    CaptureField {
        record: CaptureRecordId,
        field: FieldId,
    },
    ExplicitAnnotation(SourceOriginId),
    Parameter(SignatureId),
    CallArgument {
        signature: SignatureId,
        parameter: u32,
    },
    FunctionResult(SignatureId),
    ArrayPeer(ValueId),
    BranchResult(NonEmpty<ValueId>),
    PrimitiveLiteralDefault,
    Substitution {
        parameter: TypeParameterId,
        actual: TypeId,
    },
    Operation(OperationId),
}
#[derive(Debug, Clone)]
pub struct PopulationCoverage {
    pub entries: Vec<SyntaxPopulationEntry>,
}
#[derive(Debug, Clone)]
pub struct SyntaxPopulationEntry {
    pub syntax: SyntaxNodeId,
    pub origin: SourceOriginId,
    pub dispositions: NonEmpty<SyntaxDisposition>,
}
#[derive(Debug, Clone)]
pub enum SyntaxDisposition {
    Declaration(SymbolId),
    Operations(NonEmpty<OperationId>),
    ResolvedType(TypeId),
    ResolvedContract(ResolvedContract),
    Grouping { forwards: SyntaxNodeId },
    ExcludedByTarget { selection: SourceOriginId },
    Boundary(ScopeId),
    Unreachable { after: ExecutionMomentId },
}

// A lifetime is an execution/path relation, not just the source block's extent.
#[derive(Debug, Clone)]
pub struct LifetimeFacts {
    pub definitions: Vec<EntityDefinitionMoment>,
    pub uses: Vec<EntityUseMoment>,
    pub cleanup_candidates: Vec<CleanupCandidate>,
    pub requirements: Vec<LifetimeRequirement>,
    pub deferred_uses: Vec<DeferredUse>,
}
#[derive(Debug, Clone)]
pub struct PlaceOccurrence {
    pub place: PlaceId,
    pub instance: InstanceDomainId,
}
#[derive(Debug, Clone)]
pub struct EntityDefinitionMoment {
    pub entity: EntityOccurrence,
    pub created_at: MomentOccurrence,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub struct EntityUseMoment {
    pub entity: EntityOccurrence,
    pub at: MomentOccurrence,
    pub guard: PredicateId,
    pub access: AccessKind,
}
#[derive(Debug, Clone)]
pub struct CleanupCandidate {
    pub id: CleanupCandidateId,
    pub entity: EntityOccurrence,
    pub owner: Owner,
    pub exit: ScopeExitId,
    pub guard: PredicateId,
}
#[derive(Debug, Clone)]
pub struct LifetimeRequirement {
    pub id: LifetimeRequirementId,
    pub dependent: EntityOccurrence,
    pub required: LifetimeSubject,
    pub uses: NonEmpty<GuardedMoment>,
    pub completion: Vec<CompletionCapabilityId>,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub enum LifetimeSubject {
    Target(PlaceOccurrence),
    Reference {
        reference: ReferenceId,
        instance: InstanceDomainId,
    },
    SourceStorage {
        origin: StorageOriginId,
        instance: InstanceDomainId,
    },
    GuardedLock(LockIdentityId),
    UncheckedBoundary(ScopeId),
}
#[derive(Debug, Clone)]
pub struct DeferredUse {
    pub carried_by: ValueId,
    pub dependency: LifetimeSubject,
    pub completion: CompletionCapabilityId,
    pub outcomes: NonEmpty<GuardedMoment>,
}

// ---------- Logical destinations are complete before language-rule checking. ----------
#[derive(Debug, Clone)]
pub struct LogicalDestinationResult {
    pub semantics: SemanticPopulationResult,
    pub finals: Vec<LogicalFinalDestination>,
    pub physical_requirements: Vec<PhysicalPlacementRequirement>,
    pub priority: Vec<DestinationPriority>,
}
#[derive(Debug, Clone)]
pub struct LogicalFinalDestination {
    pub id: FinalDestinationId,
    pub requirement: DestinationRequirementId,
    pub value: ValueId,
    pub scope: LogicalScope,
    pub cleanup_owner: Owner,
    pub cleanup_exit: LogicalCleanupSite,
    pub guard: PredicateId,
    pub choice: PathChoiceTiming,
    pub address_stability: AddressStabilityRequirement,
}

// ---------- Rule checking consumes complete logical lifetime/destination facts. ----------
#[derive(Debug, Clone)]
pub struct RuleCheckInput {
    pub semantic_facts: LogicalDestinationResult,
    pub analysis: AnalysisRequirements,
}
#[derive(Debug, Clone)]
pub struct AnalysisRequirements {
    pub liveness_queries: Vec<LivenessQuery>,
    pub overlap_queries: Vec<OverlapQuery>,
    pub completion_queries: Vec<CompletionQuery>,
}
#[derive(Debug, Clone)]
pub struct LivenessQuery {
    pub binding: BindingId,
    pub at: MomentOccurrence,
    pub guard: PredicateId,
}
#[derive(Debug, Clone)]
pub struct OverlapQuery {
    pub first: PlaceOccurrence,
    pub second: PlaceOccurrence,
    pub at: MomentOccurrence,
    pub guard: PredicateId,
}
#[derive(Debug, Clone)]
pub struct CompletionQuery {
    pub capability: CompletionCapabilityId,
    pub before: MomentOccurrence,
    pub guard: PredicateId,
}

#[derive(Debug, Clone)]
pub enum RuleAnalysisResult {
    Established(CheckedPostAst),
    Rejected(RejectedSemanticProgram),
    MissingSemanticInput(IncompleteSemanticProgram),
}
#[derive(Debug, Clone)]
pub struct CheckedPostAst {
    pub semantics: LogicalDestinationResult,
    pub derived: ValidationResult,
    pub evidence: Vec<RuleEvidence>,
}
#[derive(Debug, Clone)]
pub struct RejectedSemanticProgram {
    pub semantics: LogicalDestinationResult,
    /// Successful proofs remain inspectable even when another obligation
    /// rejects the program.
    pub derived: ValidationResult,
    pub evidence: Vec<RuleEvidence>,
    pub diagnostics: NonEmpty<RuleDiagnostic>,
}
#[derive(Debug, Clone)]
pub struct IncompleteSemanticProgram {
    pub semantics: LogicalDestinationResult,
    /// Proofs completed before the missing semantic input was encountered.
    pub derived: ValidationResult,
    pub evidence: Vec<RuleEvidence>,
    pub missing: NonEmpty<SemanticGap>,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CoreRule {
    N1,
    N2,
    N3,
    N4,
    N5,
    N6,
    N7,
    N8,
}
#[derive(Debug, Clone)]
pub struct RuleDiagnostic {
    pub message: String,
    pub established_violation: bool,
    pub rule: CoreRule,
    pub obligation: ObligationId,
    pub primary: SourceOriginId,
    pub related: Vec<SourceOriginId>,
}
#[derive(Debug, Clone)]
pub struct SemanticGap {
    pub consumer: CoreRule,
    pub operation: OperationId,
    pub missing: MissingFact,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub enum MissingFact {
    MalformedGraph(String),
    Type(ValueId),
    CallTarget(OperationId),
    Provenance(ValueId),
    EffectSummary(OperationId),
    AccessObligation(OperationId),
    Lifetime(LifetimeRequirementId),
    ExecutionOrder(NonEmpty<ExecutionMomentId>),
}
#[derive(Debug, Clone)]
pub struct RuleEvidence {
    pub id: EvidenceId,
    pub obligation: ObligationId,
    pub premises: Vec<EvidenceId>,
    pub facts: EvidenceFacts,
}
#[derive(Debug, Clone)]
pub enum EvidenceFacts {
    TypeIdentity {
        expected: TypeId,
        actual: TypeId,
    },
    RuntimeCheck {
        check: CheckId,
    },
    TransferMode {
        occurrence: TransferOccurrenceId,
        subject: TransferSubject,
        mode: TransferKind,
    },
    MutationPermission {
        place: PlaceId,
        access: AccessKind,
    },
    StructuralReplication {
        ty: TypeId,
    },
    DependencyPreserved {
        link: DependencyLinkId,
    },
    StoredDependencies {
        value: ValueId,
        destination: PlaceId,
    },
    EscapingDependencies {
        value: ValueId,
    },
    TransferDestination {
        transfer: u32,
    },
    FinalDestination {
        destination: FinalDestinationId,
    },
    DependenciesLiveAtOperation {
        operation: OperationId,
    },
    BranchDependencies {
        call: OperationId,
        capability: CompletionCapabilityId,
    },
    BindingAvailable {
        binding: BindingId,
        at: MomentOccurrence,
        guard: PredicateId,
    },
    MatchExhaustive {
        decision: OperationId,
    },
    AccessCompatible {
        place: PlaceOccurrence,
        access: AccessKind,
        at: MomentOccurrence,
        guard: PredicateId,
    },
    LockAcquisition {
        call: OperationId,
        contract: LockContractId,
    },
    DestructionSequence {
        subject: DestructionSubject,
        at: MomentOccurrence,
        storage: Option<StorageOriginId>,
    },
    DestructorContract {
        destructor: DestructorId,
    },
    ReservedDestructorCall {
        call: OperationId,
        destructor: DestructorId,
    },
    PartialMoveCleanup {
        source: ValueId,
    },
    Ownership {
        entity: EntityOccurrence,
        at: MomentOccurrence,
        owner: Owner,
    },
    LiveTarget {
        requirement: LifetimeRequirementId,
        uses: NonEmpty<GuardedMoment>,
    },
    DisjointPlaces {
        first: PlaceOccurrence,
        second: PlaceOccurrence,
        guard: PredicateId,
    },
    SameLock {
        targets: NonEmpty<PlaceOccurrence>,
        identity: LockIdentityId,
    },
    BranchCompleted {
        capability: CompletionCapabilityId,
        established_at: GuardedMoment,
    },
    LoopInvariant {
        loop_region: LoopRegionId,
        guard: PredicateId,
    },
    LogicalDestination {
        destination: FinalDestinationId,
        cleanup_exit: LogicalCleanupSite,
        guard: PredicateId,
    },
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

// ---------- Transfer facts feed logical resolution; physical plans realize them. ----------
#[derive(Debug, Clone)]
pub struct DestinationRequirements {
    pub transfers: Vec<TransferLink>,
    pub finals: Vec<FinalDestinationRequirement>,
    pub result_contracts: Vec<CallResultStorageContract>,
}
#[derive(Debug, Clone)]
pub struct TransferLink {
    pub source: ValueId,
    pub result: ValueId,
    pub entity: Option<EntityId>,
    pub operation: OperationId,
    pub at: ExecutionMomentId,
    pub guard: PredicateId,
    pub receiver: Owner,
}
#[derive(Debug, Clone)]
pub struct FinalDestinationRequirement {
    pub id: DestinationRequirementId,
    pub value: ValueId,
    pub candidates: NonEmpty<DestinationCandidate>,
    pub construction: ExecutionMomentId,
    pub address_stability: AddressStabilityRequirement,
    pub dependencies: DependencySummaryId,
}
#[derive(Debug, Clone)]
pub struct DestinationCandidate {
    pub scope: LogicalScope,
    pub receiver: Owner,
    pub guard: PredicateId,
    pub cleanup_exit: LogicalCleanupSite,
    pub choice: PathChoiceTiming,
}
#[derive(Debug, Clone)]
pub enum PathChoiceTiming {
    BeforeConstruction { selected_at: ExecutionMomentId },
    AfterConstruction { selected_at: ExecutionMomentId },
    SingleDestination,
}
#[derive(Debug, Clone)]
pub enum AddressStabilityRequirement {
    FixedExisting {
        address: AddressId,
        origin: StorageOriginId,
    },
    ChooseOnceBeforeConstruction,
}
#[derive(Debug, Clone)]
pub struct CallResultStorageContract {
    pub function: FunctionInstanceId,
    pub alternatives: NonEmpty<GuardedResultStorage>,
}
#[derive(Debug, Clone)]
pub struct GuardedResultStorage {
    pub guard: PredicateId,
    pub mode: ResultStorageMode,
}
#[derive(Debug, Clone)]
pub enum ResultStorageMode {
    ConstructIntoCallerReservation {
        result: TypeId,
    },
    TransferExisting {
        value: ValueId,
        origin: StorageOriginId,
    },
}
/// Physical realization constraint, not a postponed N1-N8 proof.
#[derive(Debug, Clone)]
pub struct PhysicalPlacementRequirement {
    pub id: PhysicalPlacementRequirementId,
    pub destination: FinalDestinationId,
    pub kind: PhysicalPlacementRequirementKind,
    pub guard: PredicateId,
    pub origin: SourceOriginId,
}
#[derive(Debug, Clone)]
pub enum PhysicalPlacementRequirementKind {
    StorageMustSurvive(NonEmpty<GuardedMoment>),
    PreserveAddress(AddressId),
    ReserveBeforeScopeEntry(ScopeId),
    CallerProvided { call: OperationId },
    PreserveSourcePool(StorageOriginId),
    RetainUntilCompletion(CompletionCapabilityId),
}
#[derive(Debug, Clone)]
pub struct MemoryPlanningInput {
    pub checked_flow: CheckedPostAst,
    pub layouts: TargetLayoutPlan,
}
#[derive(Debug, Clone)]
pub enum MemoryPlanningResult {
    Planned(PlannedPostAst),
    Rejected(RejectedMemoryPlan),
    MissingPlanInput(IncompleteMemoryPlan),
}
#[derive(Debug, Clone)]
pub struct PlannedPostAst {
    pub layouts: TargetLayoutPlan,
    pub checked_flow: CheckedPostAst,
    pub reservations: Vec<ReservationAssignment>,
    pub sharing: Vec<ExclusiveReservationGroup>,
    pub storage: StoragePlan,
    pub cleanup: CleanupPlan,
    /// Physical state-machine layouts derived from resolved async frames and
    /// target layouts.  Backends consume this table directly and never
    /// reconstruct liveness or frame offsets.
    pub async_states: AsyncStatePlan,
    /// Physical layouts for every operand crossing a foreign boundary.
    pub foreign: ForeignEmissionPlan,
    pub physical_proofs: Vec<PhysicalPlanningProof>,
    pub realization: Vec<PhysicalPlacementEvidence>,
}
#[derive(Debug, Clone)]
pub struct RejectedMemoryPlan {
    pub checked_flow: CheckedPostAst,
    pub layouts: TargetLayoutPlan,
    pub diagnostics: NonEmpty<PhysicalPlanningDiagnostic>,
}
#[derive(Debug, Clone)]
pub struct PhysicalPlanningDiagnostic {
    /// None identifies a physical capacity/layout contradiction rather than
    /// failure to realize one named logical placement requirement.
    pub requirement: Option<PhysicalPlacementRequirementId>,
    pub origin: SourceOriginId,
    pub conflicting_reservations: Vec<StorageReservationId>,
}
#[derive(Debug, Clone)]
pub struct IncompleteMemoryPlan {
    pub checked_flow: CheckedPostAst,
    pub layouts: TargetLayoutPlan,
    pub missing: NonEmpty<MissingPlanInput>,
}
#[derive(Debug, Clone)]
pub enum MissingPlanInput {
    TypeLayout(TypeId),
    PhysicalRequirement(PhysicalPlacementRequirementId),
    RuntimeBinding(IntrinsicId),
}
#[derive(Debug, Clone)]
pub struct ReservationAssignment {
    pub reservation: StorageReservationId,
    pub issuer: ReservationIssuer,
    /// First execution moment at which the reserved address must be usable by
    /// the operation that initializes the value.
    pub initialization_at: ExecutionMomentId,
    /// Moment at which the physical address is made available. Parent/caller
    /// reservations may make it available before `initialization_at`.
    pub reserved_at: ExecutionMomentId,
    /// Moment at which the logical destination (for example a `let` binding)
    /// is established. This can be later than `initialization_at` when the
    /// value is constructed directly in its final storage.
    pub construction_at: ExecutionMomentId,
    pub destination: FinalDestinationId,
    pub origin: StorageOriginId,
}
#[derive(Debug, Clone)]
pub enum ReservationIssuer {
    Parent {
        scope: ScopeId,
        child: ScopeId,
    },
    Caller {
        scope: ScopeId,
        call: OperationId,
        callee: FunctionInstanceId,
    },
    ExistingStorage {
        origin: StorageOriginId,
    },
}
#[derive(Debug, Clone)]
pub struct ExclusiveReservationGroup {
    pub id: ReservationGroupId,
    pub reservation: StorageReservationId,
    pub initializers: NonEmpty<GuardedConstruction>,
    pub exclusivity_evidence: PhysicalPlanningProofId,
    pub compatibility_evidence: PhysicalPlanningProofId,
}
#[derive(Debug, Clone)]
pub struct GuardedConstruction {
    pub value: ValueId,
    pub construction: ExecutionMomentId,
    pub guard: PredicateId,
}
#[derive(Debug, Clone)]
pub struct DestinationPriority {
    pub scope: ScopeId,
    pub attracted_values: Vec<ValueId>,
}
#[derive(Debug, Clone)]
pub struct PhysicalPlacementEvidence {
    pub requirement: PhysicalPlacementRequirementId,
    pub destination: FinalDestinationId,
    pub reservation: StorageReservationId,
    pub semantic_premises: Vec<EvidenceId>,
}
#[derive(Debug, Clone)]
pub struct PhysicalPlanningProof {
    pub id: PhysicalPlanningProofId,
    pub fact: PhysicalPlanningFact,
}
#[derive(Debug, Clone)]
pub enum PhysicalPlanningFact {
    GuardsExclusive {
        first: PredicateId,
        second: PredicateId,
    },
    LayoutsCompatible {
        first: LayoutId,
        second: LayoutId,
    },
}

/// The sole code-generation handoff retains the checked logical semantics
/// under planned.checked_flow.semantics. No pending language-rule proofs.
#[derive(Debug, Clone)]
pub struct LoweringReadyPostAst {
    pub planned: PlannedPostAst,
    /// Concrete functions reachable from the resolved entry point. Abstract
    /// parametric bodies remain in PostAST for checking but are not emitted.
    pub reachable_functions: Vec<FunctionInstanceId>,
    pub async_states: AsyncStatePlan,
    pub foreign: ForeignEmissionPlan,
    pub runtime: RuntimeBindings,
}
