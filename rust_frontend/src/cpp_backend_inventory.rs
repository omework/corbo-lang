//! Exhaustive inventory of the semantic and physical representations consumed
//! by C++ generation.
//!
//! This module is deliberately data-oriented. Every enum used by the handoff
//! has one explicit arm, so adding a PostAST or memory-plan variant makes this
//! inventory fail to compile until its backend disposition is chosen.

use crate::post_ast::*;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Coverage {
    /// Produces C++ declarations, statements, expressions or foreign text.
    Emitted,
    /// Realized by the execution graph/timeline rather than at the operation's
    /// lexical position.
    ExecutionGraph,
    /// Consumed by storage, cleanup, async-frame or foreign-boundary planning.
    PhysicalPlan,
    /// A semantic-only fact used to select an already-resolved representation.
    SemanticFact,
    /// Valid only in an abstract parametric body; it must not reach concrete
    /// generation.
    AbstractOnly,
    /// Has no runtime representation by definition.
    NoRuntimeRepresentation,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct InventoryEntry {
    pub name: &'static str,
    pub coverage: Coverage,
}

macro_rules! entry {
    ($name:literal, $coverage:ident) => {
        InventoryEntry {
            name: $name,
            coverage: Coverage::$coverage,
        }
    };
}

pub fn operation(value: &Operation) -> InventoryEntry {
    match value {
        Operation::CreatePool(_) => entry!("CreatePool", Emitted),
        Operation::NativeOperation(_) => entry!("NativeOperation", Emitted),
        Operation::EnterScope(_) => entry!("EnterScope", PhysicalPlan),
        Operation::ExitScope(_) => entry!("ExitScope", PhysicalPlan),
        Operation::EvaluatePlace(_) => entry!("EvaluatePlace", Emitted),
        Operation::ReadValue(_) => entry!("ReadValue", Emitted),
        Operation::InitializeBinding(_) => entry!("InitializeBinding", Emitted),
        Operation::InitializeDefault(_) => entry!("InitializeDefault", Emitted),
        Operation::ReceiveValue(_) => entry!("ReceiveValue", Emitted),
        Operation::ForwardResult(_) => entry!("ForwardResult", Emitted),
        Operation::DiscardResult(_) => entry!("DiscardResult", Emitted),
        Operation::MoveValue(_) => entry!("MoveValue", Emitted),
        Operation::ParametricTransfer(_) => entry!("ParametricTransfer", Emitted),
        Operation::CopyPrimitive(_) => entry!("CopyPrimitive", Emitted),
        Operation::CopyEligibleEnum(_) => entry!("CopyEligibleEnum", Emitted),
        Operation::BorrowShared(_) => entry!("BorrowShared", Emitted),
        Operation::BorrowMutable(_) => entry!("BorrowMutable", Emitted),
        Operation::ReborrowShared(_) => entry!("ReborrowShared", Emitted),
        Operation::ReborrowMutable(_) => entry!("ReborrowMutable", Emitted),
        Operation::Assign(_) => entry!("Assign", ExecutionGraph),
        Operation::AddAssign(_) => entry!("AddAssign", ExecutionGraph),
        Operation::SubtractAssign(_) => entry!("SubtractAssign", ExecutionGraph),
        Operation::MultiplyAssign(_) => entry!("MultiplyAssign", ExecutionGraph),
        Operation::DivideAssign(_) => entry!("DivideAssign", ExecutionGraph),
        Operation::RemainderAssign(_) => entry!("RemainderAssign", ExecutionGraph),
        Operation::BitAndAssign(_) => entry!("BitAndAssign", ExecutionGraph),
        Operation::BitOrAssign(_) => entry!("BitOrAssign", ExecutionGraph),
        Operation::BitXorAssign(_) => entry!("BitXorAssign", ExecutionGraph),
        Operation::ShiftLeftAssign(_) => entry!("ShiftLeftAssign", ExecutionGraph),
        Operation::ShiftRightAssign(_) => entry!("ShiftRightAssign", ExecutionGraph),
        Operation::Add(_) => entry!("Add", Emitted),
        Operation::Subtract(_) => entry!("Subtract", Emitted),
        Operation::Multiply(_) => entry!("Multiply", Emitted),
        Operation::Divide(_) => entry!("Divide", Emitted),
        Operation::Remainder(_) => entry!("Remainder", Emitted),
        Operation::BitAnd(_) => entry!("BitAnd", Emitted),
        Operation::BitOr(_) => entry!("BitOr", Emitted),
        Operation::BitXor(_) => entry!("BitXor", Emitted),
        Operation::ShiftLeft(_) => entry!("ShiftLeft", Emitted),
        Operation::ShiftRight(_) => entry!("ShiftRight", Emitted),
        Operation::Equal(_) => entry!("Equal", Emitted),
        Operation::NotEqual(_) => entry!("NotEqual", Emitted),
        Operation::Less(_) => entry!("Less", Emitted),
        Operation::LessEqual(_) => entry!("LessEqual", Emitted),
        Operation::Greater(_) => entry!("Greater", Emitted),
        Operation::GreaterEqual(_) => entry!("GreaterEqual", Emitted),
        Operation::Negate(_) => entry!("Negate", Emitted),
        Operation::BooleanNot(_) => entry!("BooleanNot", Emitted),
        Operation::BitNot(_) => entry!("BitNot", Emitted),
        Operation::LoopParameter(_) => entry!("LoopParameter", PhysicalPlan),
        Operation::ShortCircuitAnd(_) => entry!("ShortCircuitAnd", ExecutionGraph),
        Operation::ShortCircuitOr(_) => entry!("ShortCircuitOr", ExecutionGraph),
        Operation::IntegerLiteral(_) => entry!("IntegerLiteral", Emitted),
        Operation::FloatLiteral(_) => entry!("FloatLiteral", Emitted),
        Operation::BooleanLiteral(_) => entry!("BooleanLiteral", Emitted),
        Operation::TextLiteral(_) => entry!("TextLiteral", Emitted),
        Operation::UnitValue(_) => entry!("UnitValue", NoRuntimeRepresentation),
        Operation::NumericCast(_) => entry!("NumericCast", Emitted),
        Operation::DirectCall(_) => entry!("DirectCall", Emitted),
        Operation::MethodCall(_) => entry!("MethodCall", Emitted),
        Operation::ExternalCall(_) => entry!("ExternalCall", Emitted),
        Operation::IntrinsicCall(_) => entry!("IntrinsicCall", AbstractOnly),
        Operation::CallableCall(_) => entry!("CallableCall", Emitted),
        Operation::ConstructStruct(_) => entry!("ConstructStruct", Emitted),
        Operation::ConstructEnum(_) => entry!("ConstructEnum", Emitted),
        Operation::ConstructTuple(_) => entry!("ConstructTuple", Emitted),
        Operation::ConstructArray(_) => entry!("ConstructArray", Emitted),
        Operation::RepeatArray(_) => entry!("RepeatArray", Emitted),
        Operation::ExtractTupleField(_) => entry!("ExtractTupleField", Emitted),
        Operation::ExtractVariantField(_) => entry!("ExtractVariantField", Emitted),
        Operation::ProjectField(_) => entry!("ProjectField", Emitted),
        Operation::ProjectTupleField(_) => entry!("ProjectTupleField", Emitted),
        Operation::Dereference(_) => entry!("Dereference", Emitted),
        Operation::IndexPlace(_) => entry!("IndexPlace", Emitted),
        Operation::SequenceLength(_) => entry!("SequenceLength", Emitted),
        Operation::SlicePlace(_) => entry!("SlicePlace", Emitted),
        Operation::SliceView(_) => entry!("SliceView", Emitted),
        Operation::TryTextSlice(_) => entry!("TryTextSlice", Emitted),
        Operation::IfDecision(_) => entry!("IfDecision", ExecutionGraph),
        Operation::IfLetDecision(_) => entry!("IfLetDecision", ExecutionGraph),
        Operation::MatchDecision(_) => entry!("MatchDecision", ExecutionGraph),
        Operation::MergeValue(_) => entry!("MergeValue", PhysicalPlan),
        Operation::LoopControl(_) => entry!("LoopControl", ExecutionGraph),
        Operation::WhileControl(_) => entry!("WhileControl", ExecutionGraph),
        Operation::ForControl(_) => entry!("ForControl", ExecutionGraph),
        Operation::IterationIndex(_) => entry!("IterationIndex", Emitted),
        Operation::PatternMatches(_) => entry!("PatternMatches", Emitted),
        Operation::BreakControl(_) => entry!("BreakControl", ExecutionGraph),
        Operation::ContinueControl(_) => entry!("ContinueControl", ExecutionGraph),
        Operation::ReturnControl(_) => entry!("ReturnControl", ExecutionGraph),
        Operation::PropagateResult(_) => entry!("PropagateResult", ExecutionGraph),
        Operation::PropagateOption(_) => entry!("PropagateOption", ExecutionGraph),
        Operation::UnwrapResult(_) => entry!("UnwrapResult", Emitted),
        Operation::UnwrapOption(_) => entry!("UnwrapOption", Emitted),
        Operation::CreateClosure(_) => entry!("CreateClosure", Emitted),
        Operation::AdaptCallable(_) => entry!("AdaptCallable", Emitted),
        Operation::CreateFuture(_) => entry!("CreateFuture", Emitted),
        Operation::CreateContractFuture(_) => entry!("CreateContractFuture", AbstractOnly),
        Operation::CaptureMove(_) => entry!("CaptureMove", SemanticFact),
        Operation::CaptureCopy(_) => entry!("CaptureCopy", SemanticFact),
        Operation::CaptureParametric(_) => entry!("CaptureParametric", AbstractOnly),
        Operation::EnterMoveBlock(_) => entry!("EnterMoveBlock", SemanticFact),
        Operation::AwaitValue(_) => entry!("AwaitValue", ExecutionGraph),
        Operation::YieldExecution(_) => entry!("YieldExecution", ExecutionGraph),
        Operation::BeginBranch(_) => entry!("BeginBranch", SemanticFact),
        Operation::CompleteBranch(_) => entry!("CompleteBranch", SemanticFact),
        Operation::BeginLockEffect(_) => entry!("BeginLockEffect", SemanticFact),
        Operation::EndLockEffect(_) => entry!("EndLockEffect", SemanticFact),
        Operation::DropValue(_) => entry!("DropValue", Emitted),
        Operation::AdoptOwnedValue(_) => entry!("AdoptOwnedValue", PhysicalPlan),
        Operation::ReleaseOwnedValue(_) => entry!("ReleaseOwnedValue", PhysicalPlan),
        Operation::AllocatePoolSlot(_) => entry!("AllocatePoolSlot", Emitted),
        Operation::TryAllocatePoolSlot(_) => entry!("TryAllocatePoolSlot", Emitted),
        Operation::CreateGrowingStorage(_) => entry!("CreateGrowingStorage", Emitted),
        Operation::GrowStorage(_) => entry!("GrowStorage", Emitted),
        Operation::EnterUnchecked(_) => entry!("EnterUnchecked", SemanticFact),
        Operation::ExitUnchecked(_) => entry!("ExitUnchecked", SemanticFact),
        Operation::AddressOf(_) => entry!("AddressOf", Emitted),
        Operation::ForeignC(_) => entry!("ForeignC", Emitted),
        Operation::ForeignCpp(_) => entry!("ForeignCpp", Emitted),
        Operation::ForeignAssembly(_) => entry!("ForeignAssembly", Emitted),
        Operation::RuntimeCheckOperation(_) => entry!("RuntimeCheckOperation", Emitted),
    }
}

pub fn predicate(value: &PredicateKind) -> InventoryEntry {
    match value {
        PredicateKind::TypeCopiesByValue(_) => entry!("TypeCopiesByValue", AbstractOnly),
        PredicateKind::ValidTextRange { .. } => entry!("ValidTextRange", Emitted),
        PredicateKind::DestructorVariant { .. } => entry!("DestructorVariant", PhysicalPlan),
        PredicateKind::RuntimeReady { .. } => entry!("RuntimeReady", Emitted),
        PredicateKind::PollReady { .. } => entry!("PollReady", Emitted),
        PredicateKind::Pattern { .. } => entry!("Pattern", Emitted),
        PredicateKind::Always => entry!("Always", Emitted),
        PredicateKind::Boolean { .. } => entry!("Boolean", Emitted),
        PredicateKind::Variant { .. } => entry!("Variant", Emitted),
        PredicateKind::All(_) => entry!("All", Emitted),
        PredicateKind::Any(_) => entry!("Any", Emitted),
        PredicateKind::Not(_) => entry!("Not", Emitted),
    }
}

pub fn ty(value: &TypeDefinition) -> InventoryEntry {
    match value {
        TypeDefinition::ContractFuture { .. } => entry!("ContractFuture", AbstractOnly),
        TypeDefinition::Never => entry!("Never", NoRuntimeRepresentation),
        TypeDefinition::Numeric(_) => entry!("Numeric", Emitted),
        TypeDefinition::NumericConversionError => entry!("NumericConversionError", Emitted),
        TypeDefinition::Boolean => entry!("Boolean", Emitted),
        TypeDefinition::Unit => entry!("Unit", NoRuntimeRepresentation),
        TypeDefinition::Utf8View => entry!("Utf8View", Emitted),
        TypeDefinition::StrData => entry!("StrData", NoRuntimeRepresentation),
        TypeDefinition::Nominal { .. } => entry!("Nominal", Emitted),
        TypeDefinition::Reference { .. } => entry!("Reference", Emitted),
        TypeDefinition::Tuple(_) => entry!("Tuple", Emitted),
        TypeDefinition::Array { .. } => entry!("Array", Emitted),
        TypeDefinition::Slice { .. } => entry!("Slice", Emitted),
        TypeDefinition::Callable(_) => entry!("Callable", Emitted),
        TypeDefinition::Closure { .. } => entry!("Closure", Emitted),
        TypeDefinition::Future { .. } => entry!("Future", Emitted),
        TypeDefinition::Allocation { .. } => entry!("Allocation", Emitted),
        TypeDefinition::GrowingSequence { .. } => entry!("GrowingSequence", Emitted),
        TypeDefinition::KeyedCollection { .. } => entry!("KeyedCollection", Emitted),
        TypeDefinition::GrowingString => entry!("GrowingString", Emitted),
        TypeDefinition::InlineUtf8 { .. } => entry!("InlineUtf8", Emitted),
        TypeDefinition::ExecutionHandle { .. } => entry!("ExecutionHandle", Emitted),
        TypeDefinition::Pool { .. } => entry!("Pool", Emitted),
        TypeDefinition::Parameter(_) => entry!("Parameter", AbstractOnly),
    }
}

pub fn native_operation(value: &NativeOperationKind) -> InventoryEntry {
    match value {
        NativeOperationKind::Primitive(_) => entry!("Primitive", Emitted),
        NativeOperationKind::FunctionItem(_) => entry!("FunctionItem", Emitted),
        NativeOperationKind::RuntimeLaunch { .. } => entry!("RuntimeLaunch", Emitted),
        NativeOperationKind::Join { .. } => entry!("Join", Emitted),
        NativeOperationKind::Construct { .. } => entry!("Construct", Emitted),
        NativeOperationKind::Collection { .. } => entry!("Collection", Emitted),
    }
}

pub fn runtime_launch(value: &RuntimeLaunchKind) -> InventoryEntry {
    match value {
        RuntimeLaunchKind::Spawn => entry!("Spawn", Emitted),
        RuntimeLaunchKind::SpawnBlocking => entry!("SpawnBlocking", Emitted),
        RuntimeLaunchKind::Thread => entry!("Thread", Emitted),
    }
}

pub fn collection_operation(value: &CollectionOperationKind) -> InventoryEntry {
    match value {
        CollectionOperationKind::Push => entry!("Push", Emitted),
        CollectionOperationKind::Pop => entry!("Pop", Emitted),
        CollectionOperationKind::Remove => entry!("Remove", Emitted),
        CollectionOperationKind::Replace => entry!("Replace", Emitted),
        CollectionOperationKind::Insert => entry!("Insert", Emitted),
        CollectionOperationKind::Get => entry!("Get", Emitted),
        CollectionOperationKind::GetMutable => entry!("GetMutable", Emitted),
        CollectionOperationKind::Length => entry!("Length", Emitted),
        CollectionOperationKind::Clear => entry!("Clear", Emitted),
        CollectionOperationKind::View => entry!("View", Emitted),
        CollectionOperationKind::MutableView => entry!("MutableView", Emitted),
    }
}

pub fn primitive(value: &PrimitiveOperation) -> InventoryEntry {
    match value {
        PrimitiveOperation::Runtime { .. } => entry!("Runtime", Emitted),
        PrimitiveOperation::View { .. } => entry!("View", Emitted),
        PrimitiveOperation::ValidateUtf8 { .. } => entry!("ValidateUtf8", Emitted),
        PrimitiveOperation::TryNumericConversion { .. } => entry!("TryNumericConversion", Emitted),
    }
}

pub fn runtime_primitive(value: &RuntimePrimitiveKind) -> InventoryEntry {
    match value {
        RuntimePrimitiveKind::ProcessArgs => entry!("ProcessArgs", Emitted),
        RuntimePrimitiveKind::WaitMutex => entry!("WaitMutex", Emitted),
        RuntimePrimitiveKind::WaitChannel => entry!("WaitChannel", Emitted),
        RuntimePrimitiveKind::WaitSocket => entry!("WaitSocket", Emitted),
        RuntimePrimitiveKind::AttachSocket => entry!("AttachSocket", Emitted),
        RuntimePrimitiveKind::CompleteSocket => entry!("CompleteSocket", Emitted),
    }
}

pub fn constant(value: &ConstantValue) -> InventoryEntry {
    match value {
        ConstantValue::Integer(_) => entry!("Integer", Emitted),
        ConstantValue::Unsigned(_) => entry!("Unsigned", Emitted),
        ConstantValue::Float32(_) => entry!("Float32", Emitted),
        ConstantValue::Float64(_) => entry!("Float64", Emitted),
        ConstantValue::Boolean(_) => entry!("Boolean", Emitted),
        ConstantValue::Unit => entry!("Unit", NoRuntimeRepresentation),
        ConstantValue::Utf8(_) => entry!("Utf8", Emitted),
    }
}

pub fn numeric(value: NumericType) -> InventoryEntry {
    match value {
        NumericType::I32 => entry!("I32", Emitted),
        NumericType::I64 => entry!("I64", Emitted),
        NumericType::U8 => entry!("U8", Emitted),
        NumericType::U16 => entry!("U16", Emitted),
        NumericType::U32 => entry!("U32", Emitted),
        NumericType::U64 => entry!("U64", Emitted),
        NumericType::Usize => entry!("Usize", Emitted),
        NumericType::F32 => entry!("F32", Emitted),
        NumericType::F64 => entry!("F64", Emitted),
    }
}

pub fn place_root(value: &PlaceRoot) -> InventoryEntry {
    match value {
        PlaceRoot::Value(_) => entry!("Value", Emitted),
        PlaceRoot::Binding(_) => entry!("Binding", Emitted),
        PlaceRoot::Address(_) => entry!("Address", Emitted),
        PlaceRoot::Reference(_) => entry!("Reference", Emitted),
        PlaceRoot::Collection(_) => entry!("Collection", Emitted),
    }
}

pub fn place_projection(value: &PlaceProjection) -> InventoryEntry {
    match value {
        PlaceProjection::AllocationContent => entry!("AllocationContent", Emitted),
        PlaceProjection::Dereference => entry!("Dereference", Emitted),
        PlaceProjection::Field(_) => entry!("Field", Emitted),
        PlaceProjection::TupleElement(_) => entry!("TupleElement", Emitted),
        PlaceProjection::Variant(_) => entry!("Variant", Emitted),
        PlaceProjection::Index(_) => entry!("Index", Emitted),
        PlaceProjection::Key(_) => entry!("Key", Emitted),
        PlaceProjection::Range { .. } => entry!("Range", Emitted),
    }
}

pub fn pattern_test(value: &PatternTest) -> InventoryEntry {
    match value {
        PatternTest::Any => entry!("Any", Emitted),
        PatternTest::Unit => entry!("Unit", Emitted),
        PatternTest::Dereference(_) => entry!("Dereference", Emitted),
        PatternTest::Tuple(_) => entry!("Tuple", Emitted),
        PatternTest::Variant { .. } => entry!("Variant", Emitted),
    }
}

pub fn foreign_effects(value: &ForeignBoundaryEffects) -> InventoryEntry {
    match value {
        ForeignBoundaryEffects::Declared(_) => entry!("Declared", SemanticFact),
        ForeignBoundaryEffects::UncheckedOpaque { .. } => {
            entry!("UncheckedOpaque", SemanticFact)
        }
    }
}

pub fn instance_resolution(value: &InstanceResolution) -> InventoryEntry {
    match value {
        InstanceResolution::Concrete => entry!("Concrete", Emitted),
        InstanceResolution::Parametric { .. } => entry!("Parametric", AbstractOnly),
    }
}

pub fn body_owner(value: &BodyOwner) -> InventoryEntry {
    match value {
        BodyOwner::Declaration(_) => entry!("Declaration", AbstractOnly),
        BodyOwner::Instance(_) => entry!("Instance", Emitted),
    }
}

pub fn execution_phase(value: &ExecutionPhase) -> InventoryEntry {
    match value {
        ExecutionPhase::Enter => entry!("Enter", ExecutionGraph),
        ExecutionPhase::Evaluate => entry!("Evaluate", ExecutionGraph),
        ExecutionPhase::Read => entry!("Read", ExecutionGraph),
        ExecutionPhase::Compute => entry!("Compute", ExecutionGraph),
        ExecutionPhase::Write => entry!("Write", ExecutionGraph),
        ExecutionPhase::Invoke => entry!("Invoke", ExecutionGraph),
        ExecutionPhase::Receive => entry!("Receive", ExecutionGraph),
        ExecutionPhase::TransferOwnership => entry!("TransferOwnership", ExecutionGraph),
        ExecutionPhase::EstablishEffect => entry!("EstablishEffect", ExecutionGraph),
        ExecutionPhase::Suspend => entry!("Suspend", ExecutionGraph),
        ExecutionPhase::Resume => entry!("Resume", ExecutionGraph),
        ExecutionPhase::Destroy => entry!("Destroy", ExecutionGraph),
        ExecutionPhase::Exit => entry!("Exit", ExecutionGraph),
    }
}

pub fn iteration(value: &ResolvedIteration) -> InventoryEntry {
    match value {
        ResolvedIteration::FixedArray { .. } => entry!("FixedArray", ExecutionGraph),
        ResolvedIteration::BorrowedSlice { .. } => entry!("BorrowedSlice", ExecutionGraph),
        ResolvedIteration::NextMethod { .. } => entry!("NextMethod", ExecutionGraph),
    }
}

pub fn transfer(value: &TransferKind) -> InventoryEntry {
    match value {
        TransferKind::ByTypeParameter(_) => entry!("ByTypeParameter", AbstractOnly),
        TransferKind::Move => entry!("Move", Emitted),
        TransferKind::PrimitiveCopy => entry!("PrimitiveCopy", Emitted),
        TransferKind::EligibleEnumCopy => entry!("EligibleEnumCopy", Emitted),
        TransferKind::SharedBorrow => entry!("SharedBorrow", Emitted),
        TransferKind::MutableBorrow => entry!("MutableBorrow", Emitted),
    }
}

pub fn dereference(value: &ResolvedDereference) -> InventoryEntry {
    match value {
        ResolvedDereference::NativeReference => entry!("NativeReference", Emitted),
        ResolvedDereference::NativeAllocation => entry!("NativeAllocation", Emitted),
        ResolvedDereference::MethodResult { .. } => entry!("MethodResult", Emitted),
    }
}

pub fn index_access(value: &ResolvedIndexAccess) -> InventoryEntry {
    match value {
        ResolvedIndexAccess::Contiguous { .. } => entry!("Contiguous", Emitted),
        ResolvedIndexAccess::Intrinsic { .. } => entry!("Intrinsic", AbstractOnly),
    }
}

pub fn slice_access(value: &ResolvedSliceAccess) -> InventoryEntry {
    match value {
        ResolvedSliceAccess::Contiguous { .. } => entry!("Contiguous", Emitted),
        ResolvedSliceAccess::Intrinsic { .. } => entry!("Intrinsic", AbstractOnly),
    }
}

pub fn equality(value: &EqualityKind) -> InventoryEntry {
    match value {
        EqualityKind::Numeric(_) => entry!("Numeric", Emitted),
        EqualityKind::NumericConversionError => entry!("NumericConversionError", Emitted),
        EqualityKind::Boolean => entry!("Boolean", Emitted),
        EqualityKind::ReferenceIdentity => entry!("ReferenceIdentity", Emitted),
        EqualityKind::SliceIdentity => entry!("SliceIdentity", Emitted),
        EqualityKind::EnumTagAndPayload(_) => entry!("EnumTagAndPayload", Emitted),
    }
}

pub fn replication(value: &StructuralReplicationStrategy) -> InventoryEntry {
    match value {
        StructuralReplicationStrategy::NoDuplication => entry!("NoDuplication", Emitted),
        StructuralReplicationStrategy::Primitive => entry!("Primitive", Emitted),
        StructuralReplicationStrategy::Struct(_) => entry!("Struct", Emitted),
        StructuralReplicationStrategy::Ineligible(_) => entry!("Ineligible", AbstractOnly),
    }
}

pub fn default_initialization(value: &DefaultInitializationKind) -> InventoryEntry {
    match value {
        DefaultInitializationKind::EmptyNative => entry!("EmptyNative", Emitted),
        DefaultInitializationKind::Constant(_) => entry!("Constant", Emitted),
        DefaultInitializationKind::Struct(_) => entry!("Struct", Emitted),
        DefaultInitializationKind::Variant { .. } => entry!("Variant", Emitted),
        DefaultInitializationKind::Tuple(_) => entry!("Tuple", Emitted),
        DefaultInitializationKind::Array { .. } => entry!("Array", Emitted),
        DefaultInitializationKind::Intrinsic(_) => entry!("Intrinsic", AbstractOnly),
    }
}

pub fn error_conversion(value: &ErrorConversion) -> InventoryEntry {
    match value {
        ErrorConversion::Identity => entry!("Identity", Emitted),
        ErrorConversion::From(_) => entry!("From", Emitted),
    }
}

pub fn await_protocol(value: &AwaitProtocol) -> InventoryEntry {
    match value {
        AwaitProtocol::ContractMethod { .. } => entry!("ContractMethod", AbstractOnly),
        AwaitProtocol::Handle { .. } => entry!("Handle", Emitted),
        AwaitProtocol::GeneratedFuture { .. } => entry!("GeneratedFuture", Emitted),
        AwaitProtocol::PollMethod(_) => entry!("PollMethod", Emitted),
    }
}

pub fn runtime_check(value: &RuntimeCheck) -> InventoryEntry {
    match value {
        RuntimeCheck::PoolCapacity { .. } => entry!("PoolCapacity", Emitted),
        RuntimeCheck::IntegerOverflow(_) => entry!("IntegerOverflow", Emitted),
        RuntimeCheck::ZeroDivisor(_) => entry!("ZeroDivisor", Emitted),
        RuntimeCheck::ShiftCount(_) => entry!("ShiftCount", Emitted),
        RuntimeCheck::IndexBounds(_) => entry!("IndexBounds", Emitted),
        RuntimeCheck::SliceBounds(_) => entry!("SliceBounds", Emitted),
        RuntimeCheck::Utf8Boundary(_) => entry!("Utf8Boundary", Emitted),
        RuntimeCheck::ExactConversion(_) => entry!("ExactConversion", Emitted),
        RuntimeCheck::Capacity(_) => entry!("Capacity", Emitted),
        RuntimeCheck::Utf8(_) => entry!("Utf8", Emitted),
        RuntimeCheck::Variant(_) => entry!("Variant", Emitted),
        RuntimeCheck::Unwrap(_) => entry!("Unwrap", Emitted),
    }
}

pub fn failure(value: &FailureContinuation) -> InventoryEntry {
    match value {
        FailureContinuation::Abort { .. } => entry!("Abort", Emitted),
        FailureContinuation::Propagate { .. } => entry!("Propagate", Emitted),
    }
}

pub fn execution_edge(value: &ExecutionEdge) -> InventoryEntry {
    match value {
        ExecutionEdge::Sequence(_) => entry!("Sequence", ExecutionGraph),
        ExecutionEdge::Conditional(_) => entry!("Conditional", ExecutionGraph),
        ExecutionEdge::LoopBack(_) => entry!("LoopBack", ExecutionGraph),
        ExecutionEdge::Call(_) => entry!("Call", SemanticFact),
        ExecutionEdge::Return(_) => entry!("Return", SemanticFact),
        ExecutionEdge::Suspend(_) => entry!("Suspend", ExecutionGraph),
        ExecutionEdge::Resume(_) => entry!("Resume", ExecutionGraph),
        ExecutionEdge::PollRetry { .. } => entry!("PollRetry", ExecutionGraph),
        ExecutionEdge::AwaitBody { .. } => entry!("AwaitBody", ExecutionGraph),
    }
}

pub fn position(value: &PositionSelector) -> InventoryEntry {
    match value {
        PositionSelector::AllocationContent => entry!("AllocationContent", Emitted),
        PositionSelector::AllKeys => entry!("AllKeys", PhysicalPlan),
        PositionSelector::State => entry!("State", PhysicalPlan),
        PositionSelector::AllElements { .. } => entry!("AllElements", PhysicalPlan),
        PositionSelector::VariantField { .. } => entry!("VariantField", Emitted),
        PositionSelector::Field(_) => entry!("Field", Emitted),
        PositionSelector::TupleElement(_) => entry!("TupleElement", Emitted),
        PositionSelector::FixedIndex(_) => entry!("FixedIndex", Emitted),
        PositionSelector::DynamicIndex(_) => entry!("DynamicIndex", Emitted),
        PositionSelector::Key(_) => entry!("Key", Emitted),
        PositionSelector::Range { .. } => entry!("Range", SemanticFact),
        PositionSelector::Symbolic(_) => entry!("Symbolic", AbstractOnly),
    }
}

pub fn native_layout(value: &NativeDescriptorLayout) -> InventoryEntry {
    match value {
        NativeDescriptorLayout::View { .. } => entry!("View", PhysicalPlan),
        NativeDescriptorLayout::ThinReference { .. } => entry!("ThinReference", PhysicalPlan),
        NativeDescriptorLayout::Callable { .. } => entry!("Callable", PhysicalPlan),
        NativeDescriptorLayout::Allocation { .. } => entry!("Allocation", PhysicalPlan),
        NativeDescriptorLayout::Region { .. } => entry!("Region", PhysicalPlan),
        NativeDescriptorLayout::Map { .. } => entry!("Map", PhysicalPlan),
        NativeDescriptorLayout::InlineUtf8 { .. } => entry!("InlineUtf8", PhysicalPlan),
        NativeDescriptorLayout::ExecutionHandle { .. } => entry!("ExecutionHandle", PhysicalPlan),
        NativeDescriptorLayout::Pool { .. } => entry!("Pool", PhysicalPlan),
        NativeDescriptorLayout::ContractFuture { .. } => entry!("ContractFuture", AbstractOnly),
    }
}

pub fn layout_size(value: &LayoutSize) -> InventoryEntry {
    match value {
        LayoutSize::Fixed(_) => entry!("Fixed", PhysicalPlan),
        LayoutSize::FromValue(_) => entry!("FromValue", AbstractOnly),
    }
}

pub fn value_storage(value: &ValueStorageKind) -> InventoryEntry {
    match value {
        ValueStorageKind::Reservation(_) => entry!("Reservation", PhysicalPlan),
        ValueStorageKind::Alias { .. } => entry!("Alias", PhysicalPlan),
        ValueStorageKind::SelectAlias { .. } => entry!("SelectAlias", PhysicalPlan),
        ValueStorageKind::Temporary { .. } => entry!("Temporary", PhysicalPlan),
        ValueStorageKind::Parameter { .. } => entry!("Parameter", PhysicalPlan),
        ValueStorageKind::Capture { .. } => entry!("Capture", PhysicalPlan),
        ValueStorageKind::Constant => entry!("Constant", Emitted),
        ValueStorageKind::None(_) => entry!("None", NoRuntimeRepresentation),
    }
}

pub fn storage_absence(value: &ValueStorageAbsence) -> InventoryEntry {
    match value {
        ValueStorageAbsence::Diverged => entry!("Diverged", NoRuntimeRepresentation),
        ValueStorageAbsence::Never => entry!("Never", NoRuntimeRepresentation),
        ValueStorageAbsence::AbstractType => entry!("AbstractType", AbstractOnly),
        ValueStorageAbsence::UnsizedData => entry!("UnsizedData", NoRuntimeRepresentation),
    }
}

pub fn storage_creation(value: &StorageCreation) -> InventoryEntry {
    match value {
        StorageCreation::Operation(_) => entry!("Operation", PhysicalPlan),
        StorageCreation::Static(_) => entry!("Static", PhysicalPlan),
        StorageCreation::CallerResult(_) => entry!("CallerResult", PhysicalPlan),
    }
}

pub fn backing(value: &BackingStorageKind) -> InventoryEntry {
    match value {
        BackingStorageKind::PoolSlots { .. } => entry!("PoolSlots", PhysicalPlan),
        BackingStorageKind::GrowingRegion { .. } => entry!("GrowingRegion", PhysicalPlan),
    }
}

pub fn stack_kind(value: &DataStackKind) -> InventoryEntry {
    match value {
        DataStackKind::FixedValues => entry!("FixedValues", PhysicalPlan),
        DataStackKind::GrowingRegions => entry!("GrowingRegions", PhysicalPlan),
    }
}

pub fn memory_budget(value: &MemoryBudget) -> InventoryEntry {
    match value {
        MemoryBudget::Explicit(_) => entry!("Explicit", PhysicalPlan),
        MemoryBudget::Inferred(_) => entry!("Inferred", PhysicalPlan),
        MemoryBudget::PlatformDefault => entry!("PlatformDefault", PhysicalPlan),
    }
}

pub fn cursor(value: &CursorExpressionKind) -> InventoryEntry {
    match value {
        CursorExpressionKind::ScopeUpperLimit(_) => entry!("ScopeUpperLimit", PhysicalPlan),
        CursorExpressionKind::IncomingScopeCursor(_) => entry!("IncomingScopeCursor", PhysicalPlan),
        CursorExpressionKind::AdvanceByType { .. } => entry!("AdvanceByType", PhysicalPlan),
        CursorExpressionKind::Align { .. } => entry!("Align", PhysicalPlan),
        CursorExpressionKind::AdvanceFixedBytes { .. } => entry!("AdvanceFixedBytes", PhysicalPlan),
        CursorExpressionKind::AdvancePoolSlots { .. } => entry!("AdvancePoolSlots", PhysicalPlan),
        CursorExpressionKind::AdvanceBytes { .. } => entry!("AdvanceBytes", PhysicalPlan),
        CursorExpressionKind::AdvanceScaledBytes { .. } => {
            entry!("AdvanceScaledBytes", PhysicalPlan)
        }
        CursorExpressionKind::Entry(_) => entry!("Entry", PhysicalPlan),
        CursorExpressionKind::Offset { .. } => entry!("Offset", PhysicalPlan),
        CursorExpressionKind::Merge(_) => entry!("Merge", PhysicalPlan),
    }
}

pub fn cleanup(value: &CleanupAction) -> InventoryEntry {
    match value {
        CleanupAction::InvokeUserDestructor { .. } => entry!("InvokeUserDestructor", Emitted),
        CleanupAction::DestroyOwnedComponent { .. } => entry!("DestroyOwnedComponent", Emitted),
        CleanupAction::ReleaseAllocation { .. } => entry!("ReleaseAllocation", Emitted),
        CleanupAction::RewindCursor { .. } => entry!("RewindCursor", Emitted),
        CleanupAction::ReturnRegion { .. } => entry!("ReturnRegion", Emitted),
        CleanupAction::RestoreRegionClass { .. } => entry!("RestoreRegionClass", Emitted),
    }
}

pub fn foreign_operand(value: &ForeignOperandMode) -> InventoryEntry {
    match value {
        ForeignOperandMode::ScalarValue => entry!("ScalarValue", Emitted),
        ForeignOperandMode::SharedStorage => entry!("SharedStorage", Emitted),
        ForeignOperandMode::MutableStorage => entry!("MutableStorage", Emitted),
    }
}

pub fn foreign_fragment(value: &ForeignFragment) -> InventoryEntry {
    match value {
        ForeignFragment::Text(_) => entry!("Text", Emitted),
        ForeignFragment::Operand(_) => entry!("Operand", Emitted),
    }
}

/// Exhaustively acknowledge every field of the physical handoff. These
/// destructuring patterns intentionally omit `..`: adding a field makes the
/// backend inventory fail to compile until its disposition is reviewed.
pub fn planned_handoff(value: &PlannedPostAst) {
    let PlannedPostAst {
        layouts,
        checked_flow: _,
        reservations,
        sharing,
        storage,
        cleanup,
        async_states,
        foreign,
        physical_proofs,
        realization,
    } = value;
    target_layout_plan(layouts);
    for assignment in reservations {
        reservation_assignment(assignment);
    }
    for group in sharing {
        exclusive_reservation_group(group);
    }
    storage_plan(storage);
    cleanup_plan(cleanup);
    async_state_plan(async_states);
    foreign_plan(foreign);
    for proof in physical_proofs {
        physical_proof(proof);
    }
    for evidence in realization {
        physical_evidence(evidence);
    }
}

fn target_layout_plan(value: &TargetLayoutPlan) {
    let TargetLayoutPlan { layouts, abi: _ } = value;
    for layout in layouts {
        type_layout_record(layout);
    }
}

fn type_layout_record(value: &TypeLayout) {
    let TypeLayout {
        id: _,
        ty: _,
        size,
        alignment: _,
        fields,
        tuple_elements,
        sequence,
        variant,
        native,
    } = value;
    let _ = layout_size(size);
    for field in fields {
        field_layout(field);
    }
    for element in tuple_elements {
        tuple_layout(element);
    }
    if let Some(sequence) = sequence {
        sequence_layout(sequence);
    }
    if let Some(enumeration) = variant {
        enum_layout(enumeration);
    }
    if let Some(native) = native {
        let _ = native_layout(native);
    }
}

fn field_layout(value: &FieldLayout) {
    let FieldLayout {
        field: _,
        byte_offset: _,
        layout: _,
    } = value;
}

fn tuple_layout(value: &TupleElementLayout) {
    let TupleElementLayout {
        position: _,
        byte_offset: _,
        layout: _,
    } = value;
}

fn sequence_layout(value: &SequenceLayout) {
    let SequenceLayout {
        element: _,
        stride: _,
        length: _,
    } = value;
}

fn enum_layout(value: &EnumLayout) {
    let EnumLayout {
        discriminant_bytes: _,
        payload_offset: _,
        variants,
    } = value;
    for variant in variants {
        variant_layout(variant);
    }
}

fn variant_layout(value: &VariantLayout) {
    let VariantLayout {
        variant: _,
        discriminant: _,
        fields,
    } = value;
    for field in fields {
        field_layout(field);
    }
}

fn reservation_assignment(value: &ReservationAssignment) {
    let ReservationAssignment {
        reservation: _,
        issuer,
        initialization_at: _,
        reserved_at: _,
        construction_at: _,
        destination: _,
        origin: _,
    } = value;
    match issuer {
        ReservationIssuer::Parent { scope: _, child: _ } => {}
        ReservationIssuer::Caller {
            scope: _,
            call: _,
            callee: _,
        } => {}
        ReservationIssuer::ExistingStorage { origin: _ } => {}
    }
}

fn exclusive_reservation_group(value: &ExclusiveReservationGroup) {
    let ExclusiveReservationGroup {
        id: _,
        reservation: _,
        initializers,
        exclusivity_evidence: _,
        compatibility_evidence: _,
    } = value;
    guarded_construction(&initializers.first);
    for initializer in &initializers.rest {
        guarded_construction(initializer);
    }
}

fn guarded_construction(value: &GuardedConstruction) {
    let GuardedConstruction {
        value: _,
        construction: _,
        guard: _,
    } = value;
}

fn physical_proof(value: &PhysicalPlanningProof) {
    let PhysicalPlanningProof { id: _, fact } = value;
    match fact {
        PhysicalPlanningFact::GuardsExclusive {
            first: _,
            second: _,
        } => {}
        PhysicalPlanningFact::LayoutsCompatible {
            first: _,
            second: _,
        } => {}
    }
}

fn physical_evidence(value: &PhysicalPlacementEvidence) {
    let PhysicalPlacementEvidence {
        requirement: _,
        destination: _,
        reservation: _,
        semantic_premises: _,
    } = value;
}

fn storage_plan(value: &StoragePlan) {
    let StoragePlan {
        stacks,
        scope_entries,
        regions,
        region_classes,
        origins: _,
        reservations,
        values,
        edge_transfers,
        iteration_counters,
        backings,
        cursors,
        snapshots,
    } = value;
    for stack in stacks {
        data_stack(stack);
    }
    for entry in scope_entries {
        scope_cursor(entry);
    }
    for region in regions {
        region_plan(region);
    }
    for class in region_classes {
        region_class(class);
    }
    for reservation in reservations {
        storage_reservation(reservation);
    }
    for value in values {
        value_storage_plan(value);
    }
    for transfer in edge_transfers {
        edge_transfer(transfer);
    }
    for counter in iteration_counters {
        iteration_counter(counter);
    }
    for backing in backings {
        backing_plan(backing);
    }
    for cursor in cursors {
        cursor_record(cursor);
    }
    for snapshot in snapshots {
        cursor_snapshot(snapshot);
    }
}

fn data_stack(value: &DataStackPlan) {
    let DataStackPlan {
        id: _,
        kind,
        capacity,
    } = value;
    let _ = stack_kind(kind);
    let _ = memory_budget(capacity);
}

fn scope_cursor(value: &ScopeCursorPlan) {
    let ScopeCursorPlan {
        scope: _,
        cursor: _,
    } = value;
}

fn region_plan(value: &RegionPlan) {
    let RegionPlan {
        id: _,
        stack: _,
        class: _,
        size,
        owner: _,
        retained_until: _,
    } = value;
    let _ = memory_budget(size);
}

fn region_class(value: &RegionClassPlan) {
    let RegionClassPlan {
        id: _,
        declaring_scope: _,
        entered_at: _,
        stack: _,
        maximum_bytes: _,
        reserved_slots: _,
    } = value;
}

fn storage_reservation(value: &StorageReservation) {
    let StorageReservation {
        id: _,
        value: _,
        destination: _,
        storage: _,
        layout: _,
        guard: _,
        reserved_at: _,
        stack: _,
        region: _,
        start: _,
        end: _,
        retained_until: _,
    } = value;
}

fn value_storage_plan(value: &ValueStoragePlan) {
    let ValueStoragePlan {
        value: _,
        layout: _,
        alternatives,
    } = value;
    guarded_storage(&alternatives.first);
    for alternative in &alternatives.rest {
        guarded_storage(alternative);
    }
}

fn guarded_storage(value: &GuardedValueStorage) {
    let GuardedValueStorage { guard: _, kind } = value;
    let _ = value_storage(kind);
}

fn edge_transfer(value: &EdgeValueTransfer) {
    let EdgeValueTransfer {
        from: _,
        to: _,
        destination: _,
        source: _,
        guard: _,
    } = value;
}

fn iteration_counter(value: &IterationCounterPlan) {
    let IterationCounterPlan {
        coordinate: _,
        region: _,
        entry_edges,
        back_edges,
    } = value;
    for edge in entry_edges.iter().chain(back_edges) {
        let ExecutionEdgePoint { from: _, to: _ } = edge;
    }
}

fn backing_plan(value: &BackingStoragePlan) {
    let BackingStoragePlan { owner: _, kind } = value;
    let _ = backing(kind);
}

fn cursor_record(value: &CursorExpression) {
    let CursorExpression { id: _, kind } = value;
    let _ = cursor(kind);
}

fn cursor_snapshot(value: &CursorSnapshot) {
    let CursorSnapshot {
        id: _,
        scope: _,
        moment: _,
        cursor: _,
    } = value;
}

fn cleanup_plan(value: &CleanupPlan) {
    let CleanupPlan { exits } = value;
    for exit in exits {
        let ExitCleanup { exit: _, actions } = exit;
        for action in actions {
            let _ = cleanup(action);
        }
    }
}

fn async_state_plan(value: &AsyncStatePlan) {
    let AsyncStatePlan { frames } = value;
    for frame in frames {
        let AsyncFrameLayout {
            body: _,
            ty: _,
            layout: _,
            state_field: _,
            state_offset: _,
            completed_discriminant: _,
            saved,
            transitions,
        } = frame;
        for saved in saved {
            let SavedStateValue {
                value: _,
                field: _,
                byte_offset: _,
                dependencies: _,
            } = saved;
        }
        for transition in transitions {
            let AsyncTransition {
                suspension: _,
                resume: _,
                discriminant: _,
            } = transition;
        }
    }
}

fn foreign_plan(value: &ForeignEmissionPlan) {
    let ForeignEmissionPlan { regions, operands } = value;
    for region in regions {
        let ForeignRegion {
            id: _,
            fragments,
            headers: _,
            origin: _,
        } = region;
        for fragment in fragments {
            let _ = foreign_fragment(fragment);
        }
    }
    for operand in operands {
        let ForeignOperandLayout {
            operand: _,
            region: _,
            value: _,
            layout: _,
        } = operand;
    }
}

/// Non-enum physical records whose fields are consumed as complete records.
pub const PHYSICAL_RECORDS: &[&str] = &[
    "TargetLayoutPlan",
    "TypeLayout",
    "FieldLayout",
    "TupleElementLayout",
    "SequenceLayout",
    "EnumLayout",
    "VariantLayout",
    "StoragePlan",
    "DataStackPlan",
    "ScopeCursorPlan",
    "RegionPlan",
    "RegionClassPlan",
    "StorageReservation",
    "ValueStoragePlan",
    "EdgeValueTransfer",
    "IterationCounterPlan",
    "BackingStoragePlan",
    "CursorExpression",
    "CursorSnapshot",
    "CleanupPlan",
    "ExitCleanup",
    "AsyncStatePlan",
    "AsyncFrameLayout",
    "SavedStateValue",
    "AsyncTransition",
    "ForeignEmissionPlan",
    "ForeignOperandLayout",
];
