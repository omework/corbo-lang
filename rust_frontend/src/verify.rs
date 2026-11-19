//! Resolve and verify the synchronous scalar subset of the static tree.

use crate::{
    Error,
    flow::Flow,
    parser::{Node, NodeId},
    tree::{BindingId, Fact, StaticTree},
};
use std::collections::HashMap;

mod pipeline;
mod raw_addresses;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Ty {
    Void,
    Bool,
    I32,
    I64,
    U8,
    U16,
    U32,
    U64,
    Usize,
    F32,
    F64,
    Struct(usize),
    Allocation(Referent),
    Pool(usize),
    Handle(usize, bool),
    Future(usize),
    Ref { target: Referent, mutable: bool },
    Slice { element: Referent, mutable: bool },
    Str,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Referent {
    Str,
    Bool,
    I32,
    I64,
    U8,
    U16,
    U32,
    U64,
    Usize,
    F32,
    F64,
    Aggregate(usize),
    Handle(usize, bool),
    Pool(usize),
    Indirect { base: ReferenceBase, modes: u128 },
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ReferenceBase {
    Str,
    Scalar(TyScalar),
    Aggregate(usize),
    Handle(usize, bool),
    Pool(usize),
    AllocationScalar(TyScalar),
    AllocationAggregate(usize),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum TyScalar { Bool, I32, I64, U8, U16, U32, U64, Usize, F32, F64 }

impl TyScalar {
    fn referent(self) -> Referent {
        match self {
            Self::Bool => Referent::Bool, Self::I32 => Referent::I32, Self::I64 => Referent::I64,
            Self::U8 => Referent::U8, Self::U16 => Referent::U16, Self::U32 => Referent::U32,
            Self::U64 => Referent::U64, Self::Usize => Referent::Usize, Self::F32 => Referent::F32, Self::F64 => Referent::F64,
        }
    }
}

impl Referent {
    pub(crate) fn ty(self) -> Ty {
        match self {
            Self::Str => Ty::Str,
            Self::Bool => Ty::Bool,
            Self::I32 => Ty::I32,
            Self::I64 => Ty::I64,
            Self::U8 => Ty::U8,
            Self::U16 => Ty::U16,
            Self::U32 => Ty::U32,
            Self::U64 => Ty::U64,
            Self::Usize => Ty::Usize,
            Self::F32 => Ty::F32,
            Self::F64 => Ty::F64,
            Self::Aggregate(index) => Ty::Struct(index),
            Self::Pool(index) => Ty::Pool(index),
            Self::Handle(layout, asynchronous) => Ty::Handle(layout, asynchronous),
            Self::Indirect { base, modes: 1 } => match base {
                ReferenceBase::Str => Ty::Str,
                ReferenceBase::Scalar(scalar) => scalar.referent().ty(),
                ReferenceBase::Aggregate(index) => Ty::Struct(index),
                ReferenceBase::Pool(index) => Ty::Pool(index),
                ReferenceBase::Handle(layout, asynchronous) => Ty::Handle(layout, asynchronous),
                ReferenceBase::AllocationScalar(scalar) => Ty::Allocation(scalar.referent()),
                ReferenceBase::AllocationAggregate(index) => Ty::Allocation(Self::Aggregate(index)),
            },
            Self::Indirect { base, modes } => Ty::Ref {
                target: Self::canonical(base, modes >> 1),
                mutable: modes & 1 != 0,
            },
        }
    }
    fn encoding(self) -> (ReferenceBase, u128) {
        let scalar = match self {
            Self::Bool => TyScalar::Bool, Self::I32 => TyScalar::I32, Self::I64 => TyScalar::I64,
            Self::U8 => TyScalar::U8, Self::U16 => TyScalar::U16, Self::U32 => TyScalar::U32,
            Self::U64 => TyScalar::U64, Self::Usize => TyScalar::Usize, Self::F32 => TyScalar::F32, Self::F64 => TyScalar::F64,
            Self::Str => return (ReferenceBase::Str, 1),
            Self::Aggregate(index) => return (ReferenceBase::Aggregate(index), 1),
            Self::Pool(index) => return (ReferenceBase::Pool(index), 1),
            Self::Handle(layout, asynchronous) => return (ReferenceBase::Handle(layout, asynchronous), 1),
            Self::Indirect { base, modes } => return (base, modes),
        };
        (ReferenceBase::Scalar(scalar), 1)
    }

    fn canonical(base: ReferenceBase, modes: u128) -> Self {
        if modes == 1 {
            match base {
                ReferenceBase::Str => return Self::Str,
                ReferenceBase::Scalar(scalar) => return scalar.referent(),
                ReferenceBase::Aggregate(index) => return Self::Aggregate(index),
                ReferenceBase::Pool(index) => return Self::Pool(index),
                ReferenceBase::Handle(layout, asynchronous) => return Self::Handle(layout, asynchronous),
                _ => {}
            }
        }
        Self::Indirect { base, modes }
    }

}

impl Ty {
    pub(crate) fn float(self) -> bool {
        matches!(self, Self::F32 | Self::F64)
    }

    pub(crate) fn signed(self) -> bool {
        matches!(self, Self::I32 | Self::I64)
    }

    pub(crate) fn unsigned(self) -> bool {
        matches!(self, Self::U8 | Self::U16 | Self::U32 | Self::U64 | Self::Usize)
    }

    fn integer_bits(self, pointer_width: Option<u32>) -> Option<u32> {
        match self {
            Self::U8 => Some(8),
            Self::U16 => Some(16),
            Self::I32 | Self::U32 => Some(32),
            Self::I64 | Self::U64 => Some(64),
            Self::Usize => pointer_width,
            _ => None,
        }
    }

    fn exact_cast_to(self, target: Self, pointer_width: Option<u32>) -> bool {
        let source_bits = self.integer_bits(pointer_width);
        let target_bits = target.integer_bits(pointer_width);
        match (source_bits, target_bits) {
            (Some(src), Some(dst)) => {
                (!self.signed() || target.signed())
                    && src + u32::from(self.unsigned() && target.signed()) <= dst
            }
            (Some(src), None) if target.float() => {
                let precision = if target == Self::F32 { 24 } else { 53 };
                src - u32::from(self.signed()) <= precision
            }
            _ => self.float() && (self == target || target == Self::F64),
        }
    }

    fn referent(self) -> Option<Referent> {
        match self {
            Self::Str => Some(Referent::Str),
            Self::Struct(index) => Some(Referent::Aggregate(index)),
            Self::Pool(index) => Some(Referent::Pool(index)),
            Self::Handle(layout, asynchronous) => Some(Referent::Handle(layout, asynchronous)),
            Self::Ref { target, mutable } => {
                let (base, modes) = target.encoding();
                (modes <= u128::MAX / 2).then_some(Referent::Indirect {
                    base, modes: (modes << 1) | u128::from(mutable),
                })
            }
            Self::Allocation(target) => {
                let (base, _) = target.encoding();
                let base = match base {
                    ReferenceBase::Scalar(scalar) => ReferenceBase::AllocationScalar(scalar),
                    ReferenceBase::Aggregate(index) => ReferenceBase::AllocationAggregate(index),
                    _ => return None,
                };
                Some(Referent::Indirect { base, modes: 1 })
            }
            _ => self.scalar(),
        }
    }

    pub(crate) fn scalar(self) -> Option<Referent> {
        match self {
            Self::Bool => Some(Referent::Bool),
            Self::I32 => Some(Referent::I32),
            Self::I64 => Some(Referent::I64),
            Self::U8 => Some(Referent::U8),
            Self::U16 => Some(Referent::U16),
            Self::U32 => Some(Referent::U32),
            Self::U64 => Some(Referent::U64),
            Self::Usize => Some(Referent::Usize),
            Self::F32 => Some(Referent::F32),
            Self::F64 => Some(Referent::F64),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct Value {
    pub ty: Ty,
    pub temp: usize,
    pub receiver: bool,
    integer: Option<i128>,
    pub provenance: ValueProvenance,
    pub(crate) dependencies: DependencySummary,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ValueProvenance {
    Expression,
    LocalRead(BindingId),
    LocalMove { binding: BindingId, at: NodeId },
    Received(usize),
    // The incoming values are carried by the Receive and Break edges.
    Merged,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct DependencySummary {
    vector_len: Option<usize>,
    field_lengths: Option<usize>,
    pub(crate) loan: Option<LoanId>,
    // A future or handle can carry different dependencies in its result.
    awaited_loan: Option<LoanId>,
}

impl Value {
    fn finish_evaluation(self, out: &mut [Instr]) -> Self {
        let Some(Instr::Evaluate(result, _)) = out.last_mut() else {
            unreachable!("the value must have just been evaluated");
        };
        debug_assert_eq!(result.temp, self.temp);
        *result = self;
        self
    }
}

#[derive(Debug)]
pub(crate) enum CallKind {
    Ordinary,
    ErrorConversion,
    IoMetadata,
    Pipeline,
}

#[derive(Debug)]
pub(crate) enum Expr {
    Integer(i128),
    Float(String),
    Boolean(bool),
    Local(BindingId),
    Borrow(BindingId),
    Address(Value),
    Slice(Value, usize, Option<Value>),
    GrowingSlice(Value, Ty),
    Subslice(Value, Value, Value),
    SliceLen(Value),
    StrLiteral(Vec<u8>),
    StrBytes(Value),
    ProcessArgs,
    SliceElementAddress(Value, Value),
    SliceElement(Value),
    SliceElementBorrow(Value),
    BorrowField(Value, usize),
    BorrowIndex(Value, Value),
    Reborrow(BindingId),
    Temporary(Value),
    Dereference(BindingId),
    DereferenceValue(Value),
    BorrowThrough(Value),
    Cast(Value),
    Shift(Value, Value, u32, bool),
    Unary(String, Value),
    Binary(String, Value, Value),
    Call(usize, Vec<Value>, CallKind),
    Construct(Vec<(usize, Value)>),
    Variant(usize, Vec<(usize, Value)>),
    IsVariant(Value, usize),
    VariantField(Value, usize, usize),
    TakeVariantField(Value, usize, usize),
    TakeTupleField(Value, usize),
    PoolVariantField(Value, usize, usize, usize),
    BorrowVariantField(Value, usize, usize),
    BorrowPoolVariantField(Value, usize, usize, usize),
    Array(Vec<Value>, bool),
    Pool,
    PoolNew(Value, Value, usize),
    PoolGrowing(Value),
    GrowingLen(Value, Ty),
    GrowingIndex(Value, Value),
    VectorExtract(Value, Option<Value>, Ty),
    MapNew,
    NativeStart(usize, Vec<Value>, bool),
    NativeJoin(Value),
    FutureNew(usize, Vec<Value>),
    FutureSpawn(Value, bool),
    Await(Value),
    AwaitHandle(Value),
    SocketWait(Value, Value),
    SocketCompletion(Value, Value),
    SocketAttach(Value),
    MapInsert(Value, Value, Value),
    MapGet(Value, Value),
    MapRemove(Value, Value, Ty),
    PoolBorrow(BindingId),
    PoolRead(Value),
    PoolTake(Value),
    Index(Value, Value),
    Field(Value, usize),
}

impl Expr {
    pub(crate) fn reads_aggregate_place(&self) -> bool {
        matches!(
            self,
            Self::Dereference(_) | Self::Field(..) | Self::Index(..) | Self::GrowingIndex(..)
        )
    }
}

#[derive(Debug)]
pub(crate) enum Instr {
    Evaluate(Value, Expr),
    Bind(BindingId, Value),
    Write(BindingId, Value),
    WriteThrough(BindingId, Value),
    WriteNested(BindingId, Value),
    WriteIndex(Value, Value, Value),
    WriteSliceElement(Value, Value),
    CheckIndex(Value, usize),
    RegionScope {
        max_size: u64,
        count: u64,
    },
    FreePages,
    Assembly(crate::assembly::Block),
    GrowingPush(Value, Value),
    GrowingText(Value, Vec<u8>),
    Block(Vec<Instr>),
    If(Value, Vec<Instr>, Vec<Instr>),
    Loop {
        condition: Vec<Instr>,
        test: Option<Value>,
        body: Vec<Instr>,
    },
    Reserve(Value),
    Receive(Value, Value),
    Break(Option<(Value, Value)>),
    Continue,
    Yield,
    Print(Value),
    Discard(Value),
    DropAllocation(Value),
    DropOwned(Value),
    DropMap(Value),
    DropHandle(Value),
    Call(usize, Vec<Value>),
    Return(Option<Value>),
}

#[derive(Debug)]
pub(crate) struct Function {
    pub parameters: Vec<(BindingId, Ty)>,
    pub borrowed_parameters: Vec<BindingId>,
    pub result: Ty,
    pub body: Vec<Instr>,
    pub entry: bool,
    pub native: bool,
    pub asynchronous: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Growing {
    Vector(Ty),
    String,
    Map(Ty, Ty),
}

#[derive(Default, Debug)]
pub(crate) struct StackSizes {
    pub(crate) size: Option<u64>,
    pub(crate) region_stack_size: Option<u64>,
    pub(crate) region_size: Option<u64>,
    pub(crate) reclaim_threshold: Option<u64>,
    pub(crate) region_reclaim_threshold: Option<u64>,
}

#[derive(Debug)]
pub(crate) struct Structure {
    pub destructor: Option<usize>,
    pub fields: Vec<(String, Ty)>,
    pub array: Option<(Ty, usize)>,
    pub pool: Option<(Ty, usize)>,
    pub variants: Vec<(String, Vec<(String, Ty)>)>,
    pub growing: Option<Growing>,
}

// Inline children describe where to find the next resource. An allocation
// ends the inline walk: its adopted children are tracked by the runtime.
#[derive(Clone, Copy, Debug)]
pub(crate) enum OwnedResource {
    Slot,
    Map,
    Handle,
    Inline(usize),
}

#[derive(Debug)]
pub(crate) enum Ownership {
    Fields(Vec<(usize, OwnedResource)>),
    Array { element: OwnedResource, len: usize },
    Variants(Vec<Vec<(usize, OwnedResource)>>),
}

impl Ownership {
    fn plan(layouts: &[Structure]) -> Vec<Option<Self>> {
        let resource = |ty| match ty {
            Ty::Allocation(_) => Some(OwnedResource::Slot),
            Ty::Handle(..) => Some(OwnedResource::Handle),
            Ty::Struct(index) if matches!(layouts[index].growing, Some(Growing::Map(..))) => Some(OwnedResource::Map),
            Ty::Struct(index) if owns_resources(ty, layouts) => Some(OwnedResource::Inline(index)),
            _ => None,
        };
        let fields = |fields: &[(String, Ty)]| {
            fields
                .iter()
                .enumerate()
                .rev()
                .filter_map(|(index, (_, ty))| resource(*ty).map(|child| (index, child)))
                .collect()
        };
        layouts
            .iter()
            .enumerate()
            .map(|(index, layout)| {
                if layout.growing.is_some() || !owns_resources(Ty::Struct(index), layouts) {
                    return None;
                }
                Some(if let Some((ty, len)) = layout.array {
                    Self::Array {
                        element: resource(ty).unwrap(),
                        len,
                    }
                } else if !layout.variants.is_empty() {
                    Self::Variants(layout.variants.iter().map(|(_, arm)| fields(arm)).collect())
                } else {
                    Self::Fields(fields(&layout.fields))
                })
            })
            .collect()
    }
}

#[derive(Debug)]
pub struct VerifiedProgram {
    pub(crate) functions: Vec<Function>,
    pub(crate) structures: Vec<Structure>,
    pub(crate) ownership: Vec<Option<Ownership>>,
    pub(crate) placement: crate::placement::Placement,
    pub dependency_summaries: DependencySummaries,
    pub(crate) stack_sizes: StackSizes,
    pub(crate) pointer_width: Option<u32>,
    pub(crate) process_args: bool,
    pub(crate) socket_reactor: Option<[usize; 3]>,
    pub(crate) socket_completion: Option<[usize; 4]>,
    pub requires_openssl: bool,
}

#[derive(Clone)]
struct Signature {
    parameters: Vec<(BindingId, Ty)>,
    result: Ty,
    entry: bool,
    asynchronous: bool,
    body: NodeId,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum State {
    Unavailable,
    Live,
    Moved(NodeId),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Slot {
    vector_len: Option<usize>,
    field_lengths: Option<usize>,
    awaited_loan: Option<LoanId>,
    loan: Option<LoanId>,
    ty: Ty,
    state: State,
}

#[derive(Clone, Copy)]
enum Access {
    Read,
    Move,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct LoanId(usize);

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, PartialOrd, Ord)]
pub struct PathId(usize);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Position {
    TaskOutput,
    TaskWait,
    TaskEffect(usize),
    Field(usize),
    Variant(usize),
    Index(Option<usize>),
    MapEntry(Option<i128>),
}

impl Position {
    fn overlaps(self, other: Self) -> bool {
        self == other
            || matches!(
                (self, other),
                (Self::Index(None), Self::Index(_)) | (Self::Index(_), Self::Index(None))
                    | (Self::MapEntry(None), Self::MapEntry(_))
                    | (Self::MapEntry(_), Self::MapEntry(None))
            )
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
struct ReturnDependency {
    parameter: usize,
    from: PathId,
    at: PathId,
    opaque: bool,
    capture_exclusive: bool,
    pool: bool,
    lock: PathId,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
struct EntryEffect {
    target: usize,
    source: usize,
    path: PathId,
    output: PathId,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Origin {
    pub root: BindingId,
    pub storage: bool,
    pub pool: bool,
    pub parent: Option<BindingId>,
    // Position in the carried value and, for a parameter origin, in the argument.
    pub at: PathId,
    pub from: PathId,
    // Place held in the owner or parent reference by a stored reborrow.
    pub lock: PathId,
    // An unresolved recursive contract can map any input position here.
    pub opaque: bool,
    pub capture_exclusive: bool,
}

#[derive(Debug, Default)]
pub struct DependencySummaries {
    loans: Vec<Vec<Origin>>,
    paths: Vec<Vec<Position>>,
}

impl DependencySummaries {
    pub fn origins(&self, loan: Option<LoanId>) -> &[Origin] {
        loan.map_or(&[], |loan| &self.loans[loan.0])
    }

    pub fn path(&self, id: PathId) -> &[Position] {
        &self.paths[id.0]
    }
}

type Slots = Vec<Option<Slot>>;

#[derive(Default)]
struct LoopEdges {
    breaks: Vec<Slots>,
    continues: Vec<Slots>,
    receiver: Option<usize>,
    result_type: Option<Ty>,
    origins: Vec<Origin>,
    awaited_origins: Vec<Origin>,
    scope: Option<crate::tree::ScopeId>,
}

struct Checker<'a> {
    source: &'a str,
    tree: &'a StaticTree,
    bindings: HashMap<NodeId, BindingId>,
    uses: HashMap<NodeId, BindingId>,
    syntax_parents: HashMap<NodeId, NodeId>,
    moves: HashMap<NodeId, (BindingId, BindingId)>,
    names: HashMap<&'a str, usize>,
    constants: HashMap<&'a str, (Ty, NodeId)>,
    associated_constants: HashMap<(usize, &'a str), (Ty, NodeId)>,
    methods: HashMap<(usize, &'a str), (usize, bool)>,
    conversions: HashMap<usize, Vec<(Ty, usize)>>,
    signatures: Vec<Signature>,
    field_pop_contracts: Vec<Option<usize>>,
    structures: Vec<Structure>,
    structure_names: HashMap<&'a str, usize>,
    options: Vec<(Ty, usize)>,
    native_results: Vec<(Ty, usize)>,
    results: Vec<(Ty, Ty, usize)>,
    native_error: Option<usize>,
    pipeline_stages: HashMap<usize, pipeline::Stage>,
    pipeline_mappers: HashMap<NodeId, (usize, Ty)>,
    pipeline_mapper_waits: HashMap<usize, Vec<(usize, PathId)>>,
    mapper_captures: Vec<BindingId>,
    native_blocks: HashMap<NodeId, usize>,
    generated_functions: Vec<Option<Function>>,
    native_contracts: Vec<Vec<ReturnDependency>>,
    native_entries: Vec<NodeId>,
    slots: Slots,
    flow: Flow,
    loops: Vec<LoopEdges>,
    next_temp: usize,
    dependencies: DependencySummaries,
    vector_field_lengths: Vec<Vec<(usize, usize)>>,
    pending: Vec<Value>,
    contracts: Vec<Vec<ReturnDependency>>,
    entry_contracts: Vec<Option<Vec<EntryEffect>>>,
    wait_contracts: Vec<Vec<(usize, PathId)>>,
    returned_entry_contracts: Vec<Vec<EntryEffect>>,
    returned_entry_effects: Vec<EntryEffect>,
    waited_parameters: Vec<(usize, PathId)>,
    propagation_waits: Option<Vec<(usize, PathId)>>,
    entry_effects: Vec<EntryEffect>,
    deferred_entries: Vec<(LoanId, LoanId)>,
    native_entry_contracts: Vec<Vec<EntryEffect>>,
    native_returned_entries: Vec<Vec<EntryEffect>>,
    parameters: Vec<(BindingId, Ty)>,
    returned: Vec<ReturnDependency>,
    function_result: Ty,
    in_async: bool,
}

pub fn verify(source: &str, tree: &StaticTree) -> Result<VerifiedProgram, Error> {
    if let Some(expansion) = crate::generics::specialize(source, tree)? {
        let mut concrete = crate::frontend_for_target(&expansion.source, crate::parser::Mode::Program, &tree.target)?;
        let relocate = |range: &std::ops::Range<usize>| {
            expansion.offsets[range.start]..expansion.offsets[range.end]
        };
        concrete.std_file_range = relocate(&tree.std_file_range);
        concrete.std_env_range = relocate(&tree.std_env_range);
        concrete.std_socket_wait_ranges = tree.std_socket_wait_ranges.iter().map(relocate).collect();
        concrete.std_async_io_ranges = tree.std_async_io_ranges.iter().map(relocate).collect();
        concrete.opaque_layouts = tree.opaque_layouts.iter().map(|(name, range)| {
            (name.clone(), (relocate(&range.0), range.1))
        }).collect();
        for (generated, original) in &expansion.generated_ranges {
            if tree.std_async_io_ranges.iter().any(|range| range.contains(&original.start)) {
                concrete.std_async_io_ranges.push(generated.clone());
            }
        }
        for (original, name, extent) in &expansion.layouts {
            if let Some((_, message)) = tree.opaque_layouts.get(original) {
                concrete.opaque_layouts.insert(name.clone(), (extent.clone(), *message));
            }
        }
        return verify(&expansion.source, &concrete);
    }
    let mut checker = Checker {
        source,
        tree,
        flow: Flow::build(tree, source),
        loops: Vec::new(),
        bindings: tree
            .bindings
            .iter()
            .enumerate()
            .map(|(index, binding)| (binding.syntax, BindingId(index)))
            .collect(),
        uses: tree
            .points
            .iter()
            .filter_map(|point| match point.fact {
                Fact::Use {
                    binding: Some(binding),
                } => Some((point.syntax, binding)),
                _ => None,
            })
            .collect(),
        syntax_parents: tree
            .syntax
            .nodes
            .iter()
            .enumerate()
            .flat_map(|(index, node)| {
                node.children
                    .iter()
                    .map(move |&child| (child, NodeId(index)))
            })
            .collect(),
        moves: tree
            .points
            .iter()
            .filter_map(|point| match point.fact {
                Fact::NamedMove {
                    source: Some(source),
                    destination,
                } => Some((point.syntax, (source, destination))),
                _ => None,
            })
            .collect(),
        names: HashMap::new(),
        constants: HashMap::new(),
        associated_constants: HashMap::new(),
        methods: HashMap::new(),
        conversions: HashMap::new(),
        signatures: Vec::new(),
        field_pop_contracts: Vec::new(),
        structures: Vec::new(),
        structure_names: HashMap::new(),
        options: Vec::new(),
        native_results: Vec::new(),
        results: Vec::new(),
        native_error: None,
        pipeline_stages: HashMap::new(),
        pipeline_mappers: HashMap::new(),
        pipeline_mapper_waits: HashMap::new(),
        mapper_captures: Vec::new(),
        native_blocks: HashMap::new(),
        generated_functions: Vec::new(),
        native_contracts: Vec::new(),
        native_entries: Vec::new(),
        slots: vec![None; tree.bindings.len()],
        next_temp: 0,
        dependencies: DependencySummaries {
            paths: vec![vec![]],
            ..DependencySummaries::default()
        },
        vector_field_lengths: Vec::new(),
        pending: Vec::new(),
        contracts: Vec::new(),
        entry_contracts: Vec::new(),
        wait_contracts: Vec::new(),
        returned_entry_contracts: Vec::new(),
        returned_entry_effects: Vec::new(),
        waited_parameters: Vec::new(),
        propagation_waits: None,
        entry_effects: Vec::new(),
        deferred_entries: Vec::new(),
        native_entry_contracts: Vec::new(),
        native_returned_entries: Vec::new(),
        parameters: Vec::new(),
        returned: Vec::new(),
        function_result: Ty::Void,
        in_async: false,
    };
    checker.structures()?;
    checker.constants()?;
    checker.signatures()?;
    checker.field_pop_contracts = checker.signatures.iter()
        .map(|signature| if signature.asynchronous { None } else { checker.pop_field_contract(signature) })
        .collect();
    checker.check_raw_addresses()?;
    let mut functions = checker.functions()?;
    functions.extend(checker.generated_functions.drain(..).map(Option::unwrap));
    checker.check_destructor_layouts()?;
    let stack_sizes = checker.stack_sizes()?;
    let mut placement = crate::placement::plan(&functions, &checker.structures, stack_sizes.region_size)?;
    if checker.structures.iter().any(|layout| layout.destructor.is_some()) {
        // Implicit calls are not yet represented in the footprint graph.
        placement.footprint = None;
        placement.worker_footprints.clear();
    }
    let socket_reactor = if tree.std_socket_wait_ranges.is_empty() {
        None
    } else {
        let symbols = ["queue_create", "queue_watch", "queue_wait"];
        let indexes = symbols.map(|name| checker.names.get(format!("__crust_package_socket_{name}").as_str()).copied());
        match indexes {
            [Some(create), Some(watch), Some(wait)] => Some([create, watch, wait]),
            _ => None,
        }
    };
    let socket_completion = if tree.std_socket_wait_ranges.is_empty() {
        None
    } else {
        let symbols = ["completion_create", "completion_attach", "completion_submit", "completion_next"];
        match symbols.map(|name| checker.names.get(format!("__crust_package_socket_{name}").as_str()).copied()) {
            [Some(create), Some(attach), Some(submit), Some(next)] => Some([create, attach, submit, next]),
            _ => None,
        }
    };
    Ok(VerifiedProgram {
        functions,
        ownership: Ownership::plan(&checker.structures),
        structures: checker.structures,
        placement,
        dependency_summaries: checker.dependencies,
        stack_sizes,
        pointer_width: tree.target.pointer_width(),
        process_args: !tree.std_env_range.is_empty(),
        socket_reactor,
        socket_completion,
        requires_openssl: tree.opaque_layouts.contains_key(crate::package::TLS_CONNECTION),
    })
}

impl<'a> Checker<'a> {
    fn node(&self, id: NodeId) -> &'a Node {
        &self.tree.syntax.nodes[id.0]
    }

    fn text(&self, token: usize) -> &'a str {
        let span = self.tree.tokens[token].span;
        &self.source[span.start..span.end]
    }

    fn name(&self, id: NodeId) -> Option<&'a str> {
        self.node(id).name.map(|token| self.text(token))
    }

    fn error(&self, id: NodeId, message: &'static str) -> Error {
        let node = self.node(id);
        let offset = node.asm_operand.map_or(self.tree.tokens[node.start].span.start, |s| s.start);
        Error::new(offset, message)
    }

    fn ty(&mut self, id: NodeId) -> Result<Ty, Error> {
        let node = self.node(id);
        if matches!(self.text(node.start), "&" | "&&") && node.children.len() == 1 {
            let inner = self.node(node.children[0]);
            if self.name(node.children[0]) == Some("str") && inner.children.is_empty()
                && self.text(node.start) == "&" && self.text(node.start + 1) != "mut"
            {
                return Ok(Ty::Str);
            }
            if self.text(inner.start) == "[" && inner.children.len() == 1 {
                if self.text(node.start) == "&&" {
                    return Err(self.error(id, "tranche empruntée imbriquée hors périmètre"));
                }
                let element = self.ty(inner.children[0])?.referent()
                    .ok_or_else(|| self.error(id, "type d’élément de tranche non pris en charge"))?;
                return Ok(Ty::Slice { element, mutable: self.text(node.start + 1) == "mut" });
            }
            let target = self
                .ty(node.children[0])?
                .referent()
                .ok_or_else(|| self.error(id, "type d’emprunt non pris en charge"))?;
            let inner = Ty::Ref { target, mutable: self.text(node.start + 1) == "mut" };
            return if self.text(node.start) == "&&" {
                Ok(Ty::Ref {
                    target: inner.referent().ok_or_else(|| self.error(id, "type d’emprunt trop imbriqué"))?,
                    mutable: false,
                })
            } else {
                Ok(inner)
            };
        }
        if self.text(node.start) == "(" && !node.children.is_empty() {
            let types = node.children.clone().into_iter()
                .map(|id| self.ty(id)).collect::<Result<Vec<_>, Error>>()?;
            return self.tuple_type(id, types);
        }
        if self.text(node.start) == "[" && node.children.len() == 2 {
            let element = self.ty(node.children[0])?;
            let length = self.length(node.children[1])?;
            return self.array_type(id, element, length);
        }
        if matches!(self.name(id), Some("Pool" | "A")) && node.children.len() == 1 {
            let element = self.ty(node.children[0])?;
            let referent = element
                .referent()
                .filter(|_| !matches!(element, Ty::Pool(_) | Ty::Ref { .. } | Ty::Allocation(_)))
                .ok_or_else(|| self.error(id, "élément fixe de pool requis"))?;
            return if self.name(id) == Some("A") {
                Ok(Ty::Allocation(referent))
            } else {
                Ok(Ty::Pool(self.pool_type(element, 0)))
            };
        }
        if self.name(id) == Some("Vector") && node.children.len() == 1 {
            let element = self.ty(node.children[0])?;
            if element.scalar().is_none()
                && !matches!(element, Ty::Ref { .. } | Ty::Allocation(_) | Ty::Handle(..))
                && (!matches!(element, Ty::Struct(_))
                    || self.growing_layout(element).is_some()
                    || self.pool_layout(element).is_some())
            {
                return Err(self.error(id, "élément de vecteur fixe attendu"));
            }
            return Ok(self.growing_type(Growing::Vector(element)));
        }
        if self.name(id) == Some("Result") && node.children.len() == 2 {
            let payload = self.ty(node.children[0])?;
            let error = self.ty(node.children[1])?;
            if matches!(error, Ty::Struct(layout) if Some(layout) == self.native_error) {
                return Ok(self.native_result(payload));
            }
            if matches!(payload, Ty::Pool(_) | Ty::Future(_))
                || matches!(error, Ty::Void | Ty::Pool(_) | Ty::Future(_))
            {
                return Err(self.error(id, "types de Result incompatibles"));
            }
            return Ok(self.result_type(payload, error));
        }
        if self.text(node.start) == "runtime" && self.text(node.start + 2) == "Error" {
            self.native_result(Ty::Void);
            return Ok(Ty::Struct(self.native_error.unwrap()));
        }
        if self.text(node.start) == "runtime"
            && matches!(self.text(node.start + 2), "Handle" | "AsyncHandle")
            && node.children.len() == 1
        {
            let asynchronous = self.text(node.start + 2) == "AsyncHandle";
            let result = self.ty(node.children[0])?;
            return Ok(self.handle_type(result, asynchronous));
        }
        if self.name(id) == Some("HashMap") && node.children.len() == 2 {
            let key = self.ty(node.children[0])?;
            let value = self.ty(node.children[1])?;
            if !(key.signed() || key.unsigned() || key == Ty::Bool)
                || !(value.scalar().is_some() || matches!(value, Ty::Ref { .. } | Ty::Allocation(_))) {
                return Err(self.error(
                    id,
                    "HashMap exige une clé entière ou booléenne et une valeur primitive, empruntée ou allouée",
                ));
            }
            return Ok(self.growing_type(Growing::Map(key, value)));
        }
        if self.name(id) == Some("Option") && node.children.len() == 1 {
            let content = self.ty(node.children[0])?;
            if !option_item_supported(content) {
                return Err(self.error(id, "type d’Option hors périmètre"));
            }
            return Ok(self.option_type(content));
        }
        if self.name(id) == Some("String") && node.children.is_empty() {
            return Ok(self.growing_type(Growing::String));
        }
        if !node.children.is_empty() {
            return Err(self.error(id, "type hors du sous-ensemble vérifié"));
        }
        match self.name(id) {
            Some("i32") => Ok(Ty::I32),
            Some("i64") => Ok(Ty::I64),
            Some("u8") => Ok(Ty::U8),
            Some("u16") => Ok(Ty::U16),
            Some("u32") => Ok(Ty::U32),
            Some("u64") => Ok(Ty::U64),
            Some("usize") => self.usize_type(id),
            Some("f32") => Ok(Ty::F32),
            Some("f64") => Ok(Ty::F64),
            Some("bool") => Ok(Ty::Bool),
            Some("Void") | None
                if self.text(node.start) == "(" || self.name(id) == Some("Void") =>
            {
                Ok(Ty::Void)
            }
            Some(name) if self.structure_names.contains_key(name) => {
                Ok(Ty::Struct(self.structure_names[name]))
            }
            _ => Err(self.error(id, "type hors du sous-ensemble vérifié")),
        }
    }

    fn usize_type(&self, id: NodeId) -> Result<Ty, Error> {
        self.tree.target.pointer_width().map(|_| Ty::Usize)
            .ok_or_else(|| self.error(id, "largeur des pointeurs inconnue pour cette cible"))
    }

    fn length(&self, id: NodeId) -> Result<usize, Error> {
        let text = self.name(id).unwrap_or("");
        let length = if let Some(hex) = text.strip_prefix("0x").or_else(|| text.strip_prefix("0X"))
        {
            usize::from_str_radix(hex, 16)
        } else {
            text.parse::<usize>()
        };
        length.map_err(|_| self.error(id, "longueur fixe hors limites"))
    }

    fn handle_type(&mut self, result: Ty, asynchronous: bool) -> Ty {
        let Ty::Struct(layout) = self.native_result(result) else {
            unreachable!()
        };
        Ty::Handle(layout, asynchronous)
    }

    fn handle_output(&self, layout: usize) -> Ty {
        self.structures[layout].variants[1]
            .1
            .first()
            .map_or(Ty::Void, |field| field.1)
    }

    // Store a handle's result dependencies under its position when it travels
    // inside another value. They become active only after extracting the handle.
    fn append_value_origins(&mut self, origins: &mut Vec<Origin>, value: Value, prefix: &[Position]) {
        self.append_origins(origins, value.dependencies.loan, prefix);
        let mut output = prefix.to_vec();
        output.push(Position::TaskOutput);
        self.append_origins(origins, value.dependencies.awaited_loan, &output);
    }

    fn unpack_output(&mut self, value: &mut Value, origins: Vec<Origin>) {
        let (output, current): (Vec<_>, Vec<_>) = origins.into_iter().partition(|origin| {
            self.dependencies.paths[origin.at.0].first() == Some(&Position::TaskOutput)
                && matches!(value.ty, Ty::Handle(..))
        });
        value.dependencies.loan = (!current.is_empty()).then(|| self.intern(current));
        let output = output.into_iter().map(|mut origin| {
            origin.at = self.path(self.dependencies.paths[origin.at.0][1..].to_vec());
            origin
        }).collect::<Vec<_>>();
        value.dependencies.awaited_loan = (!output.is_empty()).then(|| self.intern(output));
    }

    fn completion_value(
        &mut self,
        layout: usize,
        handle: Value,
        expr: Expr,
        out: &mut Vec<Instr>,
    ) -> Value {
        let mut origins = Vec::new();
        self.append_origins(
            &mut origins,
            handle.dependencies.awaited_loan,
            &[Position::Variant(1), Position::Field(0)],
        );
        let mut value = self.emit(Ty::Struct(layout), expr, out);
        value.dependencies.loan = (!origins.is_empty()).then(|| self.intern(origins));
        value = value.finish_evaluation(out);
        value
    }

    fn result_type(&mut self, payload: Ty, error: Ty) -> Ty {
        if let Some(&(_, _, index)) = self.results.iter().find(|&&(p, e, _)| (p, e) == (payload, error)) {
            return Ty::Struct(index);
        }
        let index = self.structures.len();
        self.structures.push(Structure {
            destructor: None, fields: vec![], array: None, pool: None, growing: None,
            variants: vec![
                ("Err".into(), vec![("error".into(), error)]),
                ("Ok".into(), if payload == Ty::Void { vec![] } else { vec![("value".into(), payload)] }),
            ],
        });
        self.results.push((payload, error, index));
        Ty::Struct(index)
    }

    fn native_result(&mut self, ty: Ty) -> Ty {
        if let Some((_, index)) = self.native_results.iter().find(|(result, _)| *result == ty) {
            return Ty::Struct(*index);
        }
        let error = if let Some(error) = self.native_error {
            error
        } else {
            let error = self.structures.len();
            self.structures.push(Structure {
                destructor: None,
                fields: vec![],
                array: None,
                pool: None,
                growing: None,
                variants: vec![("LaunchFailed".into(), vec![])],
            });
            self.native_error = Some(error);
            error
        };
        let index = self.structures.len();
        self.structures.push(Structure {
            destructor: None,
            fields: vec![],
            array: None,
            pool: None,
            growing: None,
            variants: vec![
                ("Err".into(), vec![("error".into(), Ty::Struct(error))]),
                (
                    "Ok".into(),
                    if ty == Ty::Void {
                        vec![]
                    } else {
                        vec![("value".into(), ty)]
                    },
                ),
            ],
        });
        self.native_results.push((ty, index));
        Ty::Struct(index)
    }

    fn runtime_call(&self, id: NodeId, member: &str) -> bool {
        let node = self.node(id);
        if node.kind != "appel" {
            return false;
        }
        let callee = self.node(node.children[0]);
        callee.kind == "nom qualifié"
            && callee.end == callee.start + 3
            && self.text(callee.start) == "runtime"
            && self.text(callee.start + 2) == member
    }

    fn native_block(&self, id: NodeId) -> Option<NodeId> {
        let launch = self.node(id);
        (self.runtime_call(id, "thread") && launch.children.len() == 2).then(|| launch.children[1])
    }

    fn native_output_loan(&mut self, id: NodeId, index: usize, captures: &[Value]) -> Result<Option<LoanId>, Error> {
        let mut output = Vec::new();
        for dep in self.native_contracts[index].clone() {
            let from = self.dependencies.paths[dep.from.0].clone();
            let at = self.dependencies.paths[dep.at.0].clone();
            let captured = captures[dep.parameter].dependencies;
            let mut origins = if let Some(path) = from.strip_prefix(&[Position::TaskOutput]) {
                self.selected_origins(captured.awaited_loan, path)
            } else {
                self.selected_origins(captured.loan, &from)
            };
            for origin in &mut origins {
                let mut path = at.clone();
                if !dep.opaque {
                    path.extend_from_slice(&self.dependencies.paths[origin.at.0]);
                }
                origin.at = self.path(path);
                origin.opaque |= dep.opaque;
                origin.capture_exclusive |= dep.capture_exclusive;
                if dep.lock != PathId::default() {
                    origin.lock = dep.lock;
                }
            }
            output.extend(origins);
        }
        let effects = self.native_returned_entries[index].clone();
        self.defer_entry_effects(id, &effects, captures, &mut output)?;
        Ok((!output.is_empty()).then(|| self.intern(output)))
    }

    fn native_start(
        &mut self,
        id: NodeId,
        block: NodeId,
        retained: bool,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        if self.node(block).kind != "scope" {
            return Err(self.error(block, "bloc synchrone de thread attendu"));
        }
        let mut entries = Vec::new();
        let mut captures = Vec::new();
        let mut worker_parameters = Vec::new();
        let pending_start = self.pending.len();
        let mut capture_origins = Vec::new();
        for &entry in &self.node(block).children {
            if self.node(entry).kind == "annotation" {
                continue;
            }
            if self.node(entry).kind != "move nommé" {
                break;
            }
            let &(source, destination) = self
                .moves
                .get(&entry)
                .ok_or_else(|| self.error(entry, "source de capture introuvable"))?;
            let ty = self.live_slot(entry, source)?.ty;
            if !async_fixed(ty, &self.structures) {
                return Err(self.error(entry, "type de capture de thread non pris en charge"));
            }
            let value = self.local(entry, source, Access::Move, out)?;
            if self.dependent_handle(ty, value.dependencies.loan)
                || self.has_dependent_handle_output(ty, value.dependencies.awaited_loan)
            {
                return Err(self.error(entry, "un lancement faillible ne peut pas abandonner le handle dépendant capturé"));
            }
            capture_origins.extend(self.origins(value.dependencies.loan).iter().map(|origin| Origin {
                capture_exclusive: origin.capture_exclusive || self.has_exclusive_dependencies(ty),
                ..*origin
            }));
            if value.dependencies.loan.is_some() {
                self.pending.push(value);
            }
            entries.push(entry);
            captures.push(value);
            worker_parameters.push((destination, value.ty));
        }
        self.pending.truncate(pending_start);
        if let Some(&index) = self.native_blocks.get(&block)
            && let Some(function) = &self.generated_functions[index]
        {
            let ty = self.handle_type(function.result, false);
            let awaited_loan = self.native_output_loan(id, index, &captures)?;
            let effects = self.native_entry_contracts[index].clone();
            self.defer_entry_effects(id, &effects, &captures, &mut capture_origins)?;
            let loan = (!capture_origins.is_empty()).then(|| self.intern(capture_origins));
            let mut value = self.emit(
                ty,
                Expr::NativeStart(self.signatures.len() + index, captures, retained),
                out,
            );
            value.dependencies.loan = loan;
            value.dependencies.awaited_loan = awaited_loan;
            value = value.finish_evaluation(out);
            return Ok(value);
        }
        let index = self.generated_functions.len();
        self.generated_functions.push(None);
        self.native_contracts.push(Vec::new());
        self.native_entry_contracts.push(Vec::new());
        self.native_returned_entries.push(Vec::new());
        self.native_blocks.insert(block, index);

        // An isolated thread has its own bindings and cannot refer to a
        // value or a lifetime in the launching function.
        let slots = std::mem::replace(&mut self.slots, vec![None; self.tree.bindings.len()]);
        let loops = std::mem::take(&mut self.loops);
        let next_temp = std::mem::take(&mut self.next_temp);
        let pending = std::mem::take(&mut self.pending);
        let parameters = std::mem::take(&mut self.parameters);
        let returned = std::mem::take(&mut self.returned);
        let entry_effects = std::mem::take(&mut self.entry_effects);
        let waited_parameters = std::mem::take(&mut self.waited_parameters);
        let propagation_waits = self.propagation_waits.take();
        let returned_entry_effects = std::mem::take(&mut self.returned_entry_effects);
        let function_result = std::mem::replace(&mut self.function_result, Ty::Void);
        let saved_entries = std::mem::replace(&mut self.native_entries, entries);
        let in_async = std::mem::replace(&mut self.in_async, false);
        self.parameters.clone_from(&worker_parameters);
        for &(binding, ty) in &worker_parameters {
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
                vector_len: None,
                field_lengths: None,
                awaited_loan: None,
                ty,
                loan,
                state: State::Live,
            });
        }
        let mut body = Vec::new();
        let has_result = self
            .node(block)
            .children
            .last()
            .is_some_and(|&id| self.node(id).kind == "résultat");
        let result = if has_result {
            self.value_arm(block, None, &mut body)
                .and_then(|(_, value)| {
                    let value = value
                        .filter(|value| async_fixed(value.ty, &self.structures))
                        .ok_or_else(|| {
                            self.error(id, "type de résultat de thread non pris en charge")
                        })?;
                    self.record_return(id, value)?;
                    body.push(Instr::Return(Some(value)));
                    Ok(value.ty)
                })
        } else {
            self.block(block, Ty::Void, true, &mut body)
                .map(|continues| {
                    if continues {
                        body.push(Instr::Return(None));
                    }
                    Ty::Void
                })
        };
        self.native_entry_contracts[index] = std::mem::replace(&mut self.entry_effects, entry_effects);
        self.waited_parameters = waited_parameters;
        self.propagation_waits = propagation_waits;
        self.native_returned_entries[index] =
            std::mem::replace(&mut self.returned_entry_effects, returned_entry_effects);
        self.native_entries = saved_entries;
        self.in_async = in_async;
        self.slots = slots;
        self.loops = loops;
        self.next_temp = next_temp;
        self.pending = pending;
        self.parameters = parameters;
        self.native_contracts[index] = std::mem::replace(&mut self.returned, returned);
        self.function_result = function_result;

        let result = result?;
        self.generated_functions[index] = Some(Function {
            borrowed_parameters: Vec::new(),
            parameters: worker_parameters,
            result,
            body,
            entry: false,
            native: true,
            asynchronous: false,
        });
        let ty = self.handle_type(result, false);
        let awaited_loan = self.native_output_loan(id, index, &captures)?;
        let effects = self.native_entry_contracts[index].clone();
        self.defer_entry_effects(id, &effects, &captures, &mut capture_origins)?;
        let loan = (!capture_origins.is_empty()).then(|| self.intern(capture_origins));
        let mut value = self.emit(
            ty,
            Expr::NativeStart(self.signatures.len() + index, captures, retained),
            out,
        );
        value.dependencies.loan = loan;
        value.dependencies.awaited_loan = awaited_loan;
        value = value.finish_evaluation(out);
        Ok(value)
    }

    fn option_type(&mut self, content: Ty) -> Ty {
        if let Some((_, index)) = self.options.iter().find(|(ty, _)| *ty == content) {
            return Ty::Struct(*index);
        }
        let index = self.structures.len();
        self.structures.push(Structure {
            destructor: None,
            fields: vec![],
            array: None,
            pool: None,
            growing: None,
            variants: vec![
                ("None".into(), vec![]),
                ("Some".into(), vec![("value".into(), content)]),
            ],
        });
        self.options.push((content, index));
        Ty::Struct(index)
    }

    fn map_key(&self, id: NodeId) -> Option<i128> {
        if let Some((_, literal)) = self.named_constant(id) {
            return self.map_literal_key(literal);
        }
        let node = self.node(id);
        match node.kind {
            "nom" => {
                let binding = &self.tree.bindings[self.uses.get(&id)?.0];
                if binding.mutable { return None; }
                let init = binding.initializer?;
                // Only syntax known to denote a constant. Do not chase binding aliases.
                if !matches!(self.node(init).kind, "littéral" | "unaire" | "groupe") { return None; }
                self.map_literal_key(init)
            }
            "emprunt" | "groupe" => self.map_key(node.children[0]),
            _ => self.map_literal_key(id),
        }
    }

    fn map_literal_key(&self, id: NodeId) -> Option<i128> {
        let node = self.node(id);
        match node.kind {
            "groupe" => self.map_literal_key(node.children[0]),
            "unaire" if self.name(id) == Some("-") =>
                self.map_literal_key(node.children[0])?.checked_neg(),
            "littéral" => match self.name(id)? {
                "true" => Some(1),
                "false" => Some(0),
                digits => digits.strip_prefix("0x").or_else(|| digits.strip_prefix("0X"))
                    .map_or_else(|| digits.parse().ok(), |hex| i128::from_str_radix(hex, 16).ok()),
            },
            _ => None,
        }
    }

    fn update_map_entry(
        &mut self, id: NodeId, map: BindingId, key: Option<i128>,
        incoming: Option<LoanId>, definite: bool,
    ) -> Result<(), Error> {
        self.check_dependency_scope(id, self.tree.bindings[map.0].scope, incoming)?;
        let slot = self.live_slot(id, map)?;
        let entry = Position::MapEntry(key);
        let mut origins = self.origins(slot.loan).iter().copied().filter(|origin| {
            !(definite && key.is_some() && self.dependencies.paths[origin.at.0].first() == Some(&entry))
        }).collect::<Vec<_>>();
        self.append_origins(&mut origins, incoming, &[entry]);
        self.slots[map.0] = Some(Slot { loan: (!origins.is_empty()).then(|| self.intern(origins)), ..slot });
        Ok(())
    }

    // A call may write through its parameter on only some paths. Preserve
    // the old origins at the call site and add the possible incoming ones.
    fn replace_entry_loan(
        &mut self, id: NodeId, reference: Option<LoanId>, incoming: Option<LoanId>, definite: bool,
    ) -> Result<(), Error> {
        let mut maps = Vec::new();
        let mut parameters = Vec::new();
        for origin in self.origins(reference) {
            match self.dependencies.paths[origin.lock.0].as_slice() {
                [Position::MapEntry(key)] if origin.storage => maps.push((origin.root, *key)),
                _ if !origin.storage => {
                    if let Some(index) = self.parameters.iter().position(|&(binding, ty)| {
                        binding == origin.root && matches!(ty, Ty::Ref { target, mutable: true }
                            if matches!(target.ty(), Ty::Ref { .. }))
                    }) {
                        parameters.push(index);
                    }
                }
                _ => {}
            }
        }
        maps.sort_unstable_by_key(|(binding, key)| (binding.0, *key));
        maps.dedup();
        parameters.sort_unstable();
        parameters.dedup();
        if maps.is_empty() && parameters.is_empty() {
            return Err(self.error(id, "remplacement exige un emprunt d’entrée HashMap"));
        }
        let definite = definite && maps.len() == 1 && parameters.is_empty();
        for (map, key) in maps {
            self.update_map_entry(id, map, key, incoming, definite)?;
        }
        for target in parameters {
            for origin in self.origins(incoming).to_vec() {
                let source = self.parameters.iter().position(|&(binding, _)| {
                    binding == origin.root && !origin.storage
                }).ok_or_else(|| self.error(id, "la référence installée vise une cible locale"))?;
                let effect = EntryEffect { target, source, path: origin.from, output: PathId::default() };
                if !self.entry_effects.contains(&effect) {
                    self.entry_effects.push(effect);
                }
            }
        }
        Ok(())
    }

    fn defer_entry_effects(
        &mut self, id: NodeId, effects: &[EntryEffect], arguments: &[Value], origins: &mut Vec<Origin>,
    ) -> Result<(), Error> {
        for effect in effects {
            let target = arguments[effect.target].dependencies.loan
                .ok_or_else(|| self.error(id, "provenance de l’entrée cible inconnue"))?;
            let path = self.dependencies.paths[effect.path.0].clone();
            let source = self.selected_loan(arguments[effect.source].dependencies.loan, &path)
                .ok_or_else(|| self.error(id, "provenance de la référence installée inconnue"))?;
            let mut found = false;
            for origin in self.origins(Some(target)) {
                if origin.storage && matches!(self.dependencies.paths[origin.lock.0].as_slice(), [Position::MapEntry(_)]) {
                    self.check_dependency_scope(id, self.tree.bindings[origin.root.0].scope, Some(source))?;
                    found = true;
                } else if !origin.storage && self.parameters.iter().any(|&(binding, ty)| {
                    binding == origin.root && matches!(ty, Ty::Ref { target, mutable: true }
                        if matches!(target.ty(), Ty::Ref { .. }))
                }) {
                    found = true;
                }
            }
            if !found {
                return Err(self.error(id, "entrée cible de l’effet différé inconnue"));
            }
            let pair = (target, source);
            let index = self.deferred_entries.iter().position(|item| *item == pair).unwrap_or_else(|| {
                let index = self.deferred_entries.len();
                self.deferred_entries.push(pair);
                index
            });
            let mut position = self.dependencies.paths[effect.output.0].clone();
            position.push(Position::TaskEffect(index));
            let marker = self.path(position);
            origins.extend(self.origins(Some(target)).iter().map(|origin| Origin { at: marker, ..*origin }));
        }
        Ok(())
    }

    fn complete_entry_effects(&mut self, id: NodeId, task: Value) -> Result<(), Error> {
        let mut effects = self.origins(task.dependencies.loan).iter().filter_map(|origin| {
            let path = &self.dependencies.paths[origin.at.0];
            match path.last() {
                Some(Position::TaskEffect(index)) if !path.contains(&Position::TaskOutput) => Some(*index),
                _ => None,
            }
        }).collect::<Vec<_>>();
        for origin in self.origins(task.dependencies.loan).to_vec() {
            let path = &self.dependencies.paths[origin.at.0];
            let waits = match task.ty {
                Ty::Future(_) => path.last() == Some(&Position::TaskWait),
                ty => self.carries_handle(ty) && !path.contains(&Position::TaskOutput),
            };
            if origin.storage || !waits {
                continue;
            }
            if let Some(parameter) = self.parameters.iter().position(|&(binding, ty)| {
                binding == origin.root && self.carries_handle(ty)
            }) {
                let wait = (parameter, origin.from);
                if !self.waited_parameters.contains(&wait) {
                    self.waited_parameters.push(wait);
                }
            }
        }
        effects.sort_unstable();
        effects.dedup();
        for index in effects {
            let (target, source) = self.deferred_entries[index];
            self.replace_entry_loan(id, Some(target), Some(source), false)?;
            self.refresh_entry_reborrows(id, Some(target), Some(source))?;
        }
        Ok(())
    }

    fn refresh_entry_reborrows(
        &mut self, id: NodeId, target: Option<LoanId>, source: Option<LoanId>,
    ) -> Result<(), Error> {
        let mut parents = self.origins(target).iter().filter_map(|origin| origin.parent).collect::<Vec<_>>();
        let mut visited = std::collections::HashSet::new();
        while let Some(parent) = parents.pop() {
            if !visited.insert(parent) { continue; }
            let slot = self.live_slot(id, parent)?;
            let mut origins = self.origins(slot.loan).to_vec();
            parents.extend(origins.iter().filter_map(|origin| origin.parent));
            origins.extend_from_slice(self.origins(source));
            self.slots[parent.0] = Some(Slot {
                loan: (!origins.is_empty()).then(|| self.intern(origins)), ..slot
            });
        }
        Ok(())
    }

    fn map_method(&mut self, id: NodeId, out: &mut Vec<Instr>) -> Result<Value, Error> {
        let children = &self.node(id).children;
        let binding = *self
            .uses
            .get(&children[0])
            .ok_or_else(|| self.error(id, "liaison HashMap attendue"))?;
        let slot = self.live_slot(id, binding)?;
        let Some(Growing::Map(key_type, value_type)) = self.growing_layout(slot.ty) else {
            return Err(self.error(id, "liaison HashMap attendue"));
        };
        let operation = self.name(id).unwrap();
        let writes = operation != "get";
        if writes && !self.tree.bindings[binding.0].mutable {
            return Err(self.error(id, "HashMap mutable attendue"));
        }
        let arity = if operation == "insert" { 3 } else { 2 };
        if children.len() != arity {
            return Err(self.error(id, "nombre d’arguments de HashMap incorrect"));
        }
        let map = self.local(children[0], binding, Access::Read, out)?;
        let borrowed_key = Ty::Ref {
            target: key_type.referent().unwrap(),
            mutable: false,
        };
        let key = self.expression(
            children[1],
            Some(if operation == "insert" {
                key_type
            } else {
                borrowed_key
            }),
            Access::Move,
            out,
        )?;
        let position = Position::MapEntry(key.integer.or_else(|| self.map_key(children[1])));
        let (output, expression, incoming) = match operation {
            "insert" => {
                let incoming = self.expression(children[2], Some(value_type), Access::Move, out)?;
                (value_type, Expr::MapInsert(map, key, incoming), Some(incoming))
            }
            "get" | "get_mut" => {
                let output = Ty::Ref {
                    target: value_type.referent()
                        .ok_or_else(|| self.error(id, "type d’entrée non empruntable"))?,
                    mutable: writes,
                };
                (output, Expr::MapGet(map, key), None)
            }
            "remove" => (value_type, Expr::MapRemove(map, key, value_type), None),
            _ => unreachable!(),
        };
        let slot = self.live_slot(id, binding)?;
        self.access_target(id, binding, writes, false)?;
        let option = self.option_type(output);
        let mut value = self.emit(option, expression, out);
        let mut origins = Vec::new();
        let at = [Position::Variant(1), Position::Field(0)];
        let entries = self.selected_loan(slot.loan, &[position]);
        self.append_origins(&mut origins, entries, &at);
        if matches!(operation, "get" | "get_mut") {
            origins.push(Origin {
                root: binding,
                storage: true,
                pool: false,
                parent: None,
                at: self.path(at.to_vec()),
                from: PathId::default(),
                lock: self.path(vec![position]),
                opaque: false,
                capture_exclusive: false,
            });
        }
        value.dependencies.loan = (!origins.is_empty()).then(|| self.intern(origins));
        value = value.finish_evaluation(out);
        if writes && !matches!(operation, "get_mut") && self.has_dependencies(value_type) {
            let Position::MapEntry(key) = position else { unreachable!() };
            self.update_map_entry(id, binding, key, incoming.and_then(|input| input.dependencies.loan), true)?;
        }
        Ok(value)
    }

    fn growing_type(&mut self, kind: Growing) -> Ty {
        let index = self
            .structures
            .iter()
            .position(|layout| layout.growing == Some(kind))
            .unwrap_or_else(|| {
                let index = self.structures.len();
                self.structures.push(Structure {
                    destructor: None,
                    fields: vec![],
                    array: None,
                    pool: None,
                    variants: vec![],
                    growing: Some(kind),
                });
                index
            });
        Ty::Struct(index)
    }

    fn growing_layout(&self, ty: Ty) -> Option<Growing> {
        if let Ty::Struct(index) = ty {
            self.structures[index].growing
        } else {
            None
        }
    }

    fn growing_handle(&self, node: NodeId) -> Option<(BindingId, Growing)> {
        let binding = *self.uses.get(&node)?;
        let Ty::Allocation(element) = self.slots[binding.0]?.ty else {
            return None;
        };
        self.growing_layout(element.ty())
            .map(|kind| (binding, kind))
    }

    fn vector_field(&self, place: NodeId) -> Option<(BindingId, bool, usize, Ty)> {
        let node = self.node(place);
        if node.kind != "projection" { return None; }
        let mut root = node.children[0];
        while self.node(root).kind == "groupe" {
            root = self.node(root).children[0];
        }
        let borrowed = self.node(root).kind == "indirection";
        let name = if borrowed { self.node(root).children[0] } else { root };
        let binding = *self.uses.get(&name)?;
        let layout = match (borrowed, self.slots[binding.0]?.ty) {
            (true, Ty::Ref { target: Referent::Aggregate(layout), .. })
            | (false, Ty::Struct(layout)) => layout,
            _ => return None,
        };
        let (field, (_, ty)) = self.structures[layout].fields.iter().enumerate()
            .find(|(_, (name, _))| Some(name.as_str()) == self.name(place))?;
        let Ty::Allocation(content) = ty else { return None; };
        let Growing::Vector(element) = self.growing_layout(content.ty())? else { return None; };
        Some((binding, borrowed, field, element))
    }

    fn intern_field_lengths(&mut self, mut lengths: Vec<(usize, usize)>) -> Option<usize> {
        if lengths.is_empty() {
            return None;
        }
        lengths.sort_unstable();
        if let Some(index) = self.vector_field_lengths.iter().position(|existing| *existing == lengths) {
            return Some(index);
        }
        let index = self.vector_field_lengths.len();
        self.vector_field_lengths.push(lengths);
        Some(index)
    }

    fn pop_field_contract(&self, signature: &Signature) -> Option<usize> {
        let [(formal, Ty::Ref { target: Referent::Aggregate(layout), mutable: true })] =
            signature.parameters.as_slice() else { return None; };
        let &[tail] = self.node(signature.body).children.as_slice() else { return None; };
        let tail = self.node(tail);
        if !matches!(tail.kind, "résultat" | "return") { return None; }
        let [call] = tail.children[..] else { return None; };
        if self.node(call).kind != "appel méthode" || self.name(call) != Some("pop") { return None; }
        let [place] = self.node(call).children[..] else { return None; };
        if self.node(place).kind != "projection" { return None; }
        let mut owner = self.node(place).children[0];
        while self.node(owner).kind == "groupe" {
            owner = self.node(owner).children[0];
        }
        if self.node(owner).kind != "indirection"
            || self.uses.get(&self.node(owner).children[0]) != Some(formal) {
            return None;
        }
        self.structures[*layout].fields.iter()
            .position(|(name, _)| Some(name.as_str()) == self.name(place))
    }

    fn precise_field_pop(&self, root: BindingId, field: usize) -> Option<usize> {
        let lengths = self.slots[root.0]?.field_lengths?;
        self.vector_field_lengths[lengths].iter().find_map(|&(position, len)| (position == field).then_some(len))
    }

    fn mutable_record_root(&self, ty: Ty, loan: Option<LoanId>) -> Option<BindingId> {
        if !matches!(ty, Ty::Ref { target: Referent::Aggregate(_), mutable: true }) {
            return None;
        }
        let mut roots = self.origins(loan).iter().filter(|origin| {
            origin.storage && !origin.pool && !origin.opaque
                && origin.at == PathId::default() && origin.from == PathId::default()
        }).map(|origin| origin.root);
        let root = roots.next()?;
        roots.all(|other| other == root).then_some(root)
    }

    fn finish_field_pop(&mut self, root: BindingId, field: usize, len: usize) {
        if len == 0 { return; }
        let selected = [Position::Field(field), Position::Index(Some(len - 1))];
        let slot = self.slots[root.0].unwrap();
        let remaining = self.origins(slot.loan).iter().copied().filter(|origin| {
            let path = &self.dependencies.paths[origin.at.0];
            !path.starts_with(&selected)
        }).collect::<Vec<_>>();
        let mut lengths = self.vector_field_lengths[slot.field_lengths.unwrap()].clone();
        if let Some((_, current)) = lengths.iter_mut().find(|(position, _)| *position == field) {
            *current = len - 1;
        }
        self.slots[root.0] = Some(Slot {
            field_lengths: self.intern_field_lengths(lengths),
            loan: (!remaining.is_empty()).then(|| self.intern(remaining)),
            ..slot
        });
        // References to the container can cache its projected loans, including
        // in several successive iterator stages. Remove only the selected
        // index beneath an exact storage edge to this particular container.
        for binding in 0..self.slots.len() {
            let Some(alias) = self.slots[binding] else { continue; };
            if binding == root.0 || alias.state != State::Live { continue; }
            let origins = self.origins(alias.loan);
            let prefixes = origins.iter().filter(|origin| origin.storage && origin.root == root
                && origin.from == PathId::default() && !origin.pool && !origin.opaque)
                .map(|origin| self.dependencies.paths[origin.at.0].clone())
                .collect::<Vec<_>>();
            if prefixes.is_empty() { continue; }
            let remaining = origins.iter().copied().filter(|origin| {
                let path = &self.dependencies.paths[origin.at.0];
                !prefixes.iter().any(|prefix| path.strip_prefix(prefix.as_slice())
                    .is_some_and(|tail| tail.starts_with(&selected)))
            }).collect::<Vec<_>>();
            if remaining.len() != origins.len() {
                self.slots[binding] = Some(Slot {
                    loan: (!remaining.is_empty()).then(|| self.intern(remaining)),
                    ..alias
                });
            }
        }
    }

    fn growing_method(&mut self, id: NodeId, out: &mut Vec<Instr>) -> Result<(), Error> {
        let children = &self.node(id).children;
        let (binding, kind) = self
            .growing_handle(children[0])
            .ok_or_else(|| self.error(id, "allocation grandissante attendue"))?;
        if !self.tree.bindings[binding.0].mutable {
            return Err(self.error(id, "allocation grandissante mutable attendue"));
        }
        if children.len() != 2 {
            return Err(self.error(id, "un argument attendu"));
        }
        let handle = self.local(children[0], binding, Access::Read, out)?;
        let operation = match (self.name(id), kind) {
            (Some("push"), Growing::Vector(element)) => {
                let value = self.expression(children[1], Some(element), Access::Move, out)?;
                let slot = self.live_slot(id, binding)?;
                let scope = self.tree.bindings[binding.0].scope;
                self.check_dependency_scope(id, scope, value.dependencies.loan)?;
                self.check_dependency_scope(id, scope, value.dependencies.awaited_loan)?;
                let mut origins = self.origins(slot.loan).to_vec();
                self.append_value_origins(&mut origins, value, &[Position::Index(slot.vector_len)]);
                self.slots[binding.0] = Some(Slot {
                    vector_len: slot.vector_len.and_then(|length| length.checked_add(1)),
                    loan: (!origins.is_empty()).then(|| self.intern(origins)),
                    ..slot
                });
                Instr::GrowingPush(handle, value)
            }
            (Some("push_str"), Growing::String) => {
                let node = self.node(children[1]);
                if self.tree.tokens[node.start].kind != crate::lexer::Kind::Text {
                    return Err(self.error(id, "littéral UTF-8 attendu"));
                }
                Instr::GrowingText(handle, crate::lexer::decoded_text(self.text(node.start)))
            }
            _ => return Err(self.error(id, "méthode de croissance hors périmètre")),
        };
        self.live_slot(id, binding)?;
        self.access_target(id, binding, true, false)?;
        out.push(operation);
        Ok(())
    }

    fn vector_extract(&mut self, id: NodeId, out: &mut Vec<Instr>) -> Result<Value, Error> {
        let children = &self.node(id).children;
        if let Some((binding, borrowed, field, element)) = self.vector_field(children[0]) {
            if self.name(id) != Some("pop") || children.len() != 1 || !contains_handle(element, &self.structures) {
                return Err(self.error(id, "pop sur un champ de vecteur de handles attendu"));
            }
            let slot = self.live_slot(id, binding)?;
            let mutable = if borrowed {
                matches!(slot.ty, Ty::Ref { mutable: true, .. })
            } else {
                self.tree.bindings[binding.0].mutable
            };
            if !mutable { return Err(self.error(id, "vecteur mutable attendu")); }
            self.access_projected(id, binding, borrowed, true, &[Position::Field(field)])?;
            let vector = self.projection_value(children[0], Access::Read, out)?;
            let ty = self.option_type(element);
            let mut value = self.emit(ty, Expr::VectorExtract(vector, None, element), out);
            let root = if borrowed { self.mutable_record_root(slot.ty, slot.loan) } else { Some(binding) };
            let exact = root.and_then(|root| self.precise_field_pop(root, field).map(|len| (root, len)));
            let mut origins = match exact {
                Some((_, 0)) => Vec::new(),
                Some((_, len)) => self.selected_origins(vector.dependencies.loan, &[Position::Index(Some(len - 1))]),
                None => self.selected_origins(vector.dependencies.loan, &[Position::Index(None)]),
            };
            for origin in &mut origins {
                let mut path = vec![Position::Variant(1), Position::Field(0)];
                path.extend_from_slice(&self.dependencies.paths[origin.at.0]);
                origin.at = self.path(path);
            }
            self.unpack_output(&mut value, origins);
            if let Some((root, len)) = exact { self.finish_field_pop(root, field, len); }
            return Ok(value.finish_evaluation(out));
        }
        let (binding, Growing::Vector(element)) = self.growing_handle(children[0]).unwrap() else {
            return Err(self.error(id, "vecteur attendu"));
        };
        if !matches!(element, Ty::Allocation(_)) && !contains_handle(element, &self.structures) {
            return Err(self.error(id, "extraction prise en charge pour les allocations et éléments contenant des handles"));
        }
        if !self.tree.bindings[binding.0].mutable {
            return Err(self.error(id, "vecteur mutable attendu"));
        }
        let pop = self.name(id) == Some("pop");
        if children.len() != if pop { 1 } else { 2 } {
            return Err(self.error(id, "nombre d’arguments incorrect"));
        }
        let vector = self.local(children[0], binding, Access::Read, out)?;
        let index = if pop {
            None
        } else {
            let index = self.expression(children[1], None, Access::Read, out)?;
            if !index.ty.signed() && !index.ty.unsigned() {
                return Err(self.error(id, "indice entier attendu"));
            }
            Some(index)
        };
        let slot = self.live_slot(id, binding)?;
        self.access_target(id, binding, true, false)?;
        let position = if pop {
            slot.vector_len.and_then(|length| length.checked_sub(1))
        } else {
            match index.and_then(|index| index.integer) {
                Some(index) => Some(usize::try_from(index)
                    .map_err(|_| self.error(id, "indice hors du vecteur"))?),
                None if slot.vector_len == Some(1) => Some(0),
                None => None,
            }
        };
        let dependent = self.dependent_handle(slot.ty, slot.loan);
        if !pop && dependent && (position.is_none() || slot.vector_len.is_none()) {
            return Err(self.error(id, "l’extraction doit identifier la case du handle dépendant"));
        }
        if let Some((position, length)) = position.zip(slot.vector_len) && position >= length {
            return Err(self.error(id, "indice hors du vecteur"));
        }
        let ty = if pop { self.option_type(element) } else { element };
        let mut result = self.emit(ty, Expr::VectorExtract(vector, index, element), out);
        if self.has_dependencies(element) {
            let mut selected = Vec::new();
            let mut remaining = Vec::new();
            for mut origin in self.origins(slot.loan).to_vec() {
                let path = self.dependencies.paths[origin.at.0].clone();
                let Some((&Position::Index(previous), rest)) = path.split_first() else {
                    remaining.push(origin);
                    continue;
                };
                if position.is_none() || previous.is_none() || position == previous {
                    let mut output = if pop { vec![Position::Variant(1), Position::Field(0)] } else { vec![] };
                    output.extend_from_slice(rest);
                    selected.push(Origin { at: self.path(output), ..origin });
                }
                if slot.vector_len == Some(1) {
                    continue;
                }
                if let Some((position, previous)) = position.zip(previous) {
                    if position == previous {
                        continue;
                    }
                    if position < previous {
                        let mut path = vec![Position::Index(Some(previous - 1))];
                        path.extend_from_slice(rest);
                        origin.at = self.path(path);
                    }
                } else {
                    let mut path = vec![Position::Index(None)];
                    path.extend_from_slice(rest);
                    origin.at = self.path(path);
                }
                remaining.push(origin);
            }
            self.unpack_output(&mut result, selected);
            self.slots[binding.0] = Some(Slot {
                vector_len: slot.vector_len.map(|length| length.saturating_sub(1)),
                loan: (!remaining.is_empty()).then(|| self.intern(remaining)),
                ..slot
            });
            result = result.finish_evaluation(out);
        }
        Ok(result)
    }

    fn pool_layout(&self, ty: Ty) -> Option<(Ty, usize)> {
        match ty {
            Ty::Struct(index) | Ty::Pool(index) => self.structures[index].pool,
            _ => None,
        }
    }

    fn pool_new(&mut self, id: NodeId, out: &mut Vec<Instr>) -> Result<Value, Error> {
        let children = &self.node(id).children;

        let binding = *self
            .uses
            .get(&children[0])
            .ok_or_else(|| self.error(id, "liaison de pool requise"))?;
        let slot = self.live_slot(id, binding)?;
        let (pool, element, mut origins) = match slot.ty {
            Ty::Ref {
                target: Referent::Pool(index),
                mutable: true,
            } => {
                self.access_reference(id, binding, true)?;
                let origins = self
                    .origins(slot.loan)
                    .iter()
                    .map(|origin| Origin {
                        root: origin.root,
                        pool: true,
                        parent: None,
                        ..*origin
                    })
                    .collect::<Vec<_>>();
                (
                    self.local(children[0], binding, Access::Read, out)?,
                    self.structures[index].pool.unwrap().0,
                    origins,
                )
            }
            ty => {
                let (element, _) = self
                    .pool_layout(ty)
                    .ok_or_else(|| self.error(id, "pool fixe mutable attendu"))?;
                if !self.tree.bindings[binding.0].mutable {
                    return Err(self.error(id, "new exige un pool mutable"));
                }
                self.access_target(id, binding, true, false)?;
                let generic = self.pool_type(element, 0);
                let ty = Ty::Ref {
                    target: Referent::Pool(generic),
                    mutable: true,
                };
                let pool = self.emit(ty, Expr::PoolBorrow(binding), out);
                (
                    pool,
                    element,
                    vec![Origin {
                        root: binding,
                        storage: true,
                        pool: true,
                        parent: None,
                        at: PathId::default(),
                        from: PathId::default(),
                        lock: PathId::default(),
                        opaque: false,
                        capture_exclusive: false,
                    }],
                )
            }
        };
        if let Some(growing) = self.growing_layout(element) {
            if children.len() != 1 {
                return Err(self.error(id, "construction vide attendue"));
            }
            let mut value = self.emit(
                Ty::Allocation(element.referent().unwrap()),
                Expr::PoolGrowing(pool),
                out,
            );
            value.dependencies.vector_len = matches!(growing, Growing::Vector(_)).then_some(0);
            value.dependencies.loan = Some(self.intern(origins));
            value = value.finish_evaluation(out);
            return Ok(value);
        }
        let variants = match element {
            Ty::Struct(index) => self.structures[index].variants.len(),
            _ => 0,
        };
        let init = match &children[1..] {
            [] => self.default_value(id, element, out)?,
            [arg] if self.node(*arg).kind == "construction"
                && let Ty::Struct(index) = element
                && self.structures[index].variants.is_empty()
                && self.name(*arg).and_then(|name| self.structure_names.get(name)) == Some(&index) =>
                self.construct_fields(*arg, index, None, &self.node(*arg).children, true, out)?,
            [arg] if !matches!(self.node(*arg).kind, "champ" | "initialiseur pool") =>
                self.expression(*arg, Some(element), Access::Move, out)?,
            args => {
                let Ty::Struct(index) = element else {
                    return Err(self.error(id, "initialiseur de structure attendu"));
                };
                if variants != 0 || self.structures[index].array.is_some()
                    || self.structures[index].pool.is_some()
                {
                    return Err(self.error(id, "initialiseur de structure attendu"));
                }
                let fields = match args {
                    [arg] if self.node(*arg).kind == "initialiseur pool" => &self.node(*arg).children,
                    _ => args,
                };
                self.construct_fields(id, index, None, fields, true, out)?
            }
        };
        if contains_handle(init.ty, &self.structures) {
            self.append_value_origins(&mut origins, init, &[Position::Field(0)]);
        } else {
            origins.extend_from_slice(self.origins(init.dependencies.loan));
        }
        self.live_slot(id, binding)?;
        match slot.ty {
            Ty::Ref { .. } => self.access_reference(id, binding, true)?,
            _ => self.access_target(id, binding, true, false)?,
        }
        let mut value = self.emit(
            Ty::Allocation(element.referent().unwrap()),
            Expr::PoolNew(pool, init, variants),
            out,
        );
        value.dependencies.loan = Some(self.intern(origins));
        value = value.finish_evaluation(out);
        Ok(value)
    }

    fn pool(&mut self, id: NodeId, out: &mut Vec<Instr>) -> Result<Value, Error> {
        let node = self.node(id);
        let argument = self.node(node.children[0]);
        let [element] = argument.children.as_slice() else {
            return Err(self.error(id, "un seul type d’élément est requis"));
        };
        let element = self.ty(*element)?;
        let capacity = self.length(node.children[1])?;
        if matches!(self.growing_layout(element), Some(Growing::Map(..))) {
            return Err(self.error(id, "utiliser HashMap::new pour créer la table"));
        }
        if matches!(element, Ty::Void | Ty::Ref { .. } | Ty::Allocation(_)) || capacity == 0 {
            return Err(self.error(id, "pool exige un élément fixe et une capacité positive"));
        }
        let index = self.pool_type(element, capacity);
        Ok(self.emit(Ty::Struct(index), Expr::Pool, out))
    }

    fn pool_type(&mut self, element: Ty, capacity: usize) -> usize {
        let shape = (element, capacity);
        let index = self
            .structures
            .iter()
            .position(|layout| layout.pool == Some(shape))
            .unwrap_or_else(|| {
                let index = self.structures.len();
                self.structures.push(Structure {
                    destructor: None,
                    fields: vec![],
                    array: None,
                    pool: Some(shape),
                    variants: vec![],
                    growing: None,
                });
                index
            });
        index
    }

    fn array_type(&mut self, id: NodeId, element: Ty, length: usize) -> Result<Ty, Error> {
        if matches!(
            element,
            Ty::Void | Ty::Pool(_) | Ty::Future(_)
        ) || self.pool_layout(element).is_some()
            || self.growing_layout(element).is_some()
        {
            return Err(self.error(id, "élément avec dépendance ou sans stockage"));
        }
        let shape = (element, length);
        let index = self
            .structures
            .iter()
            .position(|layout| layout.array == Some(shape))
            .unwrap_or_else(|| {
                let index = self.structures.len();
                self.structures.push(Structure {
                    destructor: None,
                    fields: vec![],
                    array: Some(shape),
                    pool: None,
                    variants: vec![],
                    growing: None,
                });
                index
            });
        Ok(Ty::Struct(index))
    }

    fn fields(&mut self, id: NodeId) -> Result<Vec<(String, Ty)>, Error> {
        let mut fields = Vec::new();
        for (position, &field) in self.node(id).children.iter().enumerate() {
            let name = if self.node(field).kind == "champ positionnel" {
                position.to_string()
            } else {
                self.name(field).unwrap().to_owned()
            };
            if fields
                .iter()
                .any(|(previous, _): &(String, Ty)| *previous == name)
            {
                return Err(self.error(field, "champ dupliqué"));
            }
            let ty = self.ty(self.node(field).children[0])?;
            if matches!(ty, Ty::Void | Ty::Pool(_))
                || self.growing_layout(ty).is_some()
            {
                return Err(self.error(field, "champ avec dépendance ou sans stockage"));
            }
            fields.push((name, ty));
        }
        Ok(fields)
    }

    fn structures(&mut self) -> Result<(), Error> {
        let declarations = self
            .node(self.tree.syntax.root)
            .children
            .iter()
            .copied()
            .filter(|&id| matches!(self.node(id).kind, "struct" | "enum"))
            .collect::<Vec<_>>();
        for (index, &id) in declarations.iter().enumerate() {
            if self
                .structure_names
                .insert(self.name(id).unwrap(), index)
                .is_some()
            {
                return Err(self.error(id, "type nominal dupliqué"));
            }
            self.structures.push(Structure {
                destructor: None,
                fields: vec![],
                array: None,
                pool: None,
                variants: vec![],
                growing: None,
            });
        }
        for (index, &id) in declarations.iter().enumerate() {
            if self.node(id).kind == "struct" {
                self.structures[index].fields = self.fields(id)?;
            } else {
                let mut variants = Vec::new();
                for &variant in &self.node(id).children {
                    let name = self.name(variant).unwrap();
                    if variants
                        .iter()
                        .any(|(previous, _): &(String, _)| previous == name)
                    {
                        return Err(self.error(variant, "variante dupliquée"));
                    }
                    variants.push((name.to_owned(), self.fields(variant)?));
                }
                self.structures[index].variants = variants;
            }
        }
        let mut states = vec![0; self.structures.len()];
        for index in 0..states.len() {
            if !layout_acyclic(index, &self.structures, &mut states) {
                return Err(Error::new(0, "type fixe récursif sans indirection"));
            }
        }
        Ok(())
    }

    fn size_bytes(&self, property: NodeId) -> Result<u64, Error> {
        let literal = self.node(property).children[0];
        let unit = match self.text(self.node(literal).end) {
            "K" => 1 << 10,
            "M" => 1 << 20,
            "G" => 1 << 30,
            _ => unreachable!(),
        };
        self.name(literal)
            .unwrap()
            .parse::<u64>()
            .ok()
            .and_then(|number| number.checked_mul(unit))
            .ok_or_else(|| self.error(property, "taille de datastack hors limites"))
    }

    fn stack_sizes(&self) -> Result<StackSizes, Error> {
        let mut sizes = StackSizes::default();
        for &id in &self.node(self.tree.syntax.root).children {
            if self.node(id).kind != "annotation" || self.name(id) != Some("datastack") {
                continue;
            }
            for &property in &self.node(id).children {
                let target = match self.name(property) {
                    Some("size") => &mut sizes.size,
                    Some("region_stack_size") => &mut sizes.region_stack_size,
                    Some("region_size") => &mut sizes.region_size,
                    Some("reclaim_threshold") => &mut sizes.reclaim_threshold,
                    Some("region_reclaim_threshold") => &mut sizes.region_reclaim_threshold,
                    _ => unreachable!(),
                };
                *target = Some(self.size_bytes(property)?);
            }
        }
        Ok(sizes)
    }

    fn region_scope(&self, id: NodeId, out: &mut Vec<Instr>) -> Result<bool, Error> {
        if self.node(id).kind == "annotation" && self.name(id) == Some("free_pages") {
            out.push(Instr::FreePages);
            return Ok(true);
        }
        if self.node(id).kind != "annotation" || self.name(id) != Some("stack_region") {
            return Ok(false);
        }
        let children = &self.node(id).children;
        let max_size = self.size_bytes(children[0])?;
        let count = if let Some(&property) = children.get(1) {
            self.name(self.node(property).children[0])
                .unwrap()
                .parse()
                .map_err(|_| self.error(property, "nombre de régions hors limites"))?
        } else {
            0
        };
        out.push(Instr::RegionScope { max_size, count });
        Ok(true)
    }

    fn constant_value(&mut self, declaration: NodeId) -> Result<(Ty, NodeId), Error> {
        let annotation = self.node(declaration).children[0];
        let value = self.node(declaration).children[1];
        let ty = self.ty(annotation)?;
        if ty.scalar().is_none() {
            return Err(self.error(annotation, "type scalaire attendu pour la constante"));
        }
        self.expression(value, Some(ty), Access::Read, &mut Vec::new())?;
        Ok((ty, value))
    }

    fn constants(&mut self) -> Result<(), Error> {
        for item in self.node(self.tree.syntax.root).children.clone() {
            let name = self.name(item);
            match self.node(item).kind {
                "const" => {
                    let name = name.unwrap();
                    if matches!(name, "main" | "print" | "copy" | "drop") {
                        return Err(self.error(item, "nom de constante réservé"));
                    }
                    let constant = self.constant_value(item)?;
                    if self.constants.insert(name, constant).is_some() {
                        return Err(self.error(item, "constante dupliquée"));
                    }
                }
                "impl" => {
                    let layout = *self.structure_names.get(name.unwrap())
                        .ok_or_else(|| self.error(item, "type déclaré attendu pour impl"))?;
                    for member in self.node(item).children.clone() {
                        if self.node(member).kind != "const" { continue; }
                        let name = self.name(member).unwrap();
                        if name == "drop" || self.structures[layout].fields.iter().any(|(field, _)| field == name) {
                            return Err(self.error(member, "nom de constante associée en conflit"));
                        }
                        let constant = self.constant_value(member)?;
                        if self.associated_constants.insert((layout, name), constant).is_some() {
                            return Err(self.error(member, "constante associée dupliquée"));
                        }
                    }
                }
                _ => {}
            }
        }
        Ok(())
    }

    fn named_constant(&self, id: NodeId) -> Option<(Ty, NodeId)> {
        let node = self.node(id);
        match node.kind {
            "nom" if !self.uses.contains_key(&id) => self.constants.get(self.name(id)?).copied(),
            "nom qualifié" if node.children.is_empty() && node.end == node.start + 3 => {
                let owner = *self.structure_names.get(self.text(node.start))?;
                self.associated_constants.get(&(owner, self.text(node.start + 2))).copied()
            }
            _ => None,
        }
    }

    fn signatures(&mut self) -> Result<(), Error> {
        let root = self.node(self.tree.syntax.root);
        for &id in &root.children {
            let node = self.node(id);
            if matches!(node.kind, "struct" | "enum" | "impl" | "const")
                || node.kind == "annotation" && self.name(id) == Some("datastack")
            {
                continue;
            }
            if !matches!(node.kind, "fn" | "async fn") {
                return Err(self.error(id, "déclaration hors du sous-ensemble vérifié"));
            }
            let name = self
                .name(id)
                .ok_or_else(|| self.error(id, "fonction sans nom"))?;
            if matches!(name, "print" | "copy" | "drop")
                || self.constants.contains_key(name)
                || self.names.insert(name, self.signatures.len()).is_some()
            {
                return Err(self.error(id, "nom de fonction réservé ou dupliqué"));
            }
            let mut parameters = Vec::new();
            let mut result = Ty::Void;
            let mut body = None;
            for &child in &node.children {
                let member = self.node(child);
                match member.kind {
                    "paramètre" => {
                        let binding = *self
                            .bindings
                            .get(&child)
                            .ok_or_else(|| self.error(child, "paramètre sans liaison"))?;
                        if parameters.iter().any(|(id, _): &(BindingId, Ty)| {
                            self.tree.bindings[id.0].name == self.tree.bindings[binding.0].name
                        }) {
                            return Err(self.error(child, "paramètre dupliqué"));
                        }
                        if self.text(member.start) == "&" {
                            return Err(self
                                .error(child, "paramètre emprunté hors du sous-ensemble vérifié"));
                        }
                        let ty = member
                            .children
                            .first()
                            .ok_or_else(|| self.error(child, "type de paramètre requis"))?;
                        let ty = self.ty(*ty)?;
                        if matches!(ty, Ty::Void | Ty::Pool(_)) {
                            return Err(self.error(child, "paramètre sans valeur transmissible"));
                        }
                        parameters.push((binding, ty));
                    }
                    "type" => result = self.ty(child)?,
                    "scope" => body = Some(child),
                    _ => return Err(self.error(child, "annotation hors du sous-ensemble vérifié")),
                }
            }
            if matches!(result, Ty::Pool(_)) {
                return Err(self.error(id, "un pool se passe uniquement par emprunt"));
            }
            let asynchronous = node.kind == "async fn";
            if asynchronous
                && (name == "main"
                    || result != Ty::Void && !async_fixed(result, &self.structures)
                    || parameters.iter().any(|(_, ty)| !async_fixed(*ty, &self.structures)))
            {
                return Err(self.error(
                    id,
                    "async exige des captures et résultats fixes pris en charge",
                ));
            }
            let entry = name == "main";
            if entry && (!parameters.is_empty() || !matches!(result, Ty::Void | Ty::I32)) {
                return Err(self.error(id, "main exige zéro paramètre et un résultat Void ou i32"));
            }
            self.signatures.push(Signature {
                parameters,
                result,
                entry,
                asynchronous,
                body: body.ok_or_else(|| self.error(id, "corps de fonction requis"))?,
            });
        }
        let implementations = root.children.clone();
        for id in implementations {
            if self.node(id).kind != "impl" { continue; }
            let layout = *self.structure_names.get(self.name(id).unwrap())
                .ok_or_else(|| self.error(id, "type déclaré attendu pour impl"))?;
            for method in self.node(id).children.clone() {
                if self.node(method).kind == "const" { continue; }
                let children = self.node(method).children.clone();
                let asynchronous = self.node(method).kind == "async fn";
                if self.name(method) != Some("drop") {
                    let name = self.name(method).unwrap();
                    let mut parameters = Vec::new();
                    let mut result = Ty::Void;
                    let mut body = None;
                    let mut receiver = false;
                    for child in children {
                        let member = self.node(child);
                        match member.kind {
                            "paramètre" if self.name(child) == Some("self") => {
                                if !parameters.is_empty() {
                                    return Err(self.error(child, "le receveur doit être le premier paramètre"));
                                }
                                let ty = match member.children.as_slice() {
                                    [] if self.text(member.start) == "&" => Ty::Ref {
                                        target: Referent::Aggregate(layout),
                                        mutable: self.text(member.start + 1) == "mut",
                                    },
                                    [annotation] if self.ty(*annotation)? == Ty::Struct(layout) => Ty::Struct(layout),
                                    _ => return Err(self.error(child, "le type de self doit correspondre au type de impl")),
                                };
                                receiver = true;
                                parameters.push((self.bindings[&child], ty));
                            }
                            "paramètre" => {
                                let ty = self.ty(member.children[0])?;
                                if matches!(ty, Ty::Void | Ty::Pool(_)) {
                                    return Err(self.error(child, "paramètre sans valeur transmissible"));
                                }
                                let binding = self.bindings[&child];
                                if parameters.iter().any(|&(previous, _)| {
                                    self.tree.bindings[previous.0].name == self.tree.bindings[binding.0].name
                                }) {
                                    return Err(self.error(child, "paramètre dupliqué"));
                                }
                                parameters.push((binding, ty));
                            }
                            "type" => result = self.ty(child)?,
                            "scope" => body = Some(child),
                            _ => return Err(self.error(child, "annotation de méthode hors périmètre")),
                        }
                    }
                    if matches!(result, Ty::Pool(_)) {
                        return Err(self.error(method, "un pool se passe uniquement par emprunt"));
                    }
                    if asynchronous && (result != Ty::Void && !async_fixed(result, &self.structures)
                        || parameters.iter().any(|(_, ty)| !async_fixed(*ty, &self.structures)))
                    {
                        return Err(self.error(method, "async exige des captures et résultats fixes pris en charge"));
                    }
                    if self.associated_constants.contains_key(&(layout, name))
                        || self.structures[layout].fields.iter().any(|(field, _)| field == name)
                    {
                        return Err(self.error(method, "nom de méthode en conflit"));
                    }
                    let index = self.signatures.len();
                    if name == "from" && !asynchronous && !receiver && result == Ty::Struct(layout)
                        && let [(_, input)] = parameters.as_slice()
                    {
                        if self.methods.contains_key(&(layout, name)) {
                            return Err(self.error(method, "nom de méthode en conflit"));
                        }
                        let conversions = self.conversions.entry(layout).or_default();
                        if conversions.iter().any(|&(source, _)| source == *input) {
                            return Err(self.error(method, "surcharge from dupliquée pour le même type source"));
                        }
                        conversions.push((*input, index));
                    } else if (name == "from" && self.conversions.contains_key(&layout))
                        || self.methods.insert((layout, name), (index, receiver)).is_some()
                    {
                        return Err(self.error(method, "nom de méthode en conflit"));
                    }
                    self.signatures.push(Signature {
                        parameters, result, entry: false, asynchronous,
                        body: body.ok_or_else(|| self.error(method, "corps de méthode requis"))?,
                    });
                    continue;
                }
                let [receiver, tail @ ..] = children.as_slice() else {
                    return Err(self.error(method, "signature attendue : fn drop(&mut self) -> Void"));
                };
                let result_ok = match tail {
                    [_] => true,
                    [result, _] if self.node(*result).kind == "type" => self.ty(*result)? == Ty::Void,
                    _ => false,
                };
                if asynchronous || self.node(*receiver).kind != "paramètre"
                    || self.name(*receiver) != Some("self")
                    || self.text(self.node(*receiver).start) != "&"
                    || self.text(self.node(*receiver).start + 1) != "mut"
                    || !self.node(*receiver).children.is_empty()
                    || !result_ok || self.node(*tail.last().unwrap()).kind != "scope"
                {
                    return Err(self.error(method, "signature attendue : fn drop(&mut self) -> Void"));
                }
                if self.structures[layout].destructor.replace(self.signatures.len()).is_some() {
                    return Err(self.error(method, "destructeur dupliqué"));
                }
                self.signatures.push(Signature {
                    parameters: vec![(self.bindings[receiver], Ty::Ref {
                        target: Referent::Aggregate(layout), mutable: true,
                    })],
                    result: Ty::Void, entry: false, asynchronous: false, body: *tail.last().unwrap(),
                });
            }
        }
        if !self.names.contains_key("main") {
            return Err(self.error(self.tree.syntax.root, "fonction main requise"));
        }
        Ok(())
    }

    fn check_destructor_layouts(&self) -> Result<(), Error> {
        if self.structures.iter().any(|layout| matches!(layout.growing,
            Some(Growing::Vector(element)) if inline_destructor(element, &self.structures))) {
            return Err(Error::new(0, "destructeur personnalisé dans un vecteur hors périmètre"));
        }
        Ok(())
    }

    fn function_groups(&self) -> Vec<(Vec<usize>, bool)> {
        fn visit(index: usize, calls: &[Vec<usize>], seen: &mut [bool], order: &mut Vec<usize>) {
            if std::mem::replace(&mut seen[index], true) {
                return;
            }
            for &callee in &calls[index] {
                visit(callee, calls, seen, order);
            }
            order.push(index);
        }

        let calls = self.signatures.iter().map(|signature| {
            let mut nodes = vec![signature.body];
            let mut callees = Vec::new();
            while let Some(id) = nodes.pop() {
                let node = self.node(id);
                if node.kind == "appel" {
                    if let Some(callee) = self.function_index(id) {
                        callees.push(callee);
                    } else if self.iter_constructor(id) {
                        callees.extend(self.methods.iter().filter_map(|(&(_, name), &(index, receiver))| {
                            (receiver && name == "next").then_some(index)
                        }));
                    } else if let Some(layout) = self.explicit_conversion_target(id) {
                        callees.extend(self.conversions[&layout].iter().map(|&(_, index)| index));
                    }
                } else if node.kind == "appel méthode" {
                    callees.extend(self.methods.iter().filter_map(|(&(_, name), &(index, receiver))| {
                        (receiver && self.name(id) == Some(name)).then_some(index)
                    }));
                } else if node.kind == "propagation"
                    && let Some((layout, true)) = self.propagation_layout(signature.result)
                    && let Ty::Struct(error) = self.structures[layout].variants[0].1[0].1
                    && let Some(conversions) = self.conversions.get(&error)
                {
                    callees.extend(conversions.iter().map(|&(_, index)| index));
                }
                nodes.extend(&node.children);
            }
            callees
        }).collect::<Vec<_>>();
        let mut seen = vec![false; calls.len()];
        let mut order = Vec::new();
        for index in 0..calls.len() {
            visit(index, &calls, &mut seen, &mut order);
        }
        let mut incoming = vec![Vec::new(); calls.len()];
        for (caller, targets) in calls.iter().enumerate() {
            for &callee in targets {
                incoming[callee].push(caller);
            }
        }
        seen.fill(false);
        let mut groups = Vec::new();
        for index in order.into_iter().rev() {
            if seen[index] {
                continue;
            }
            let mut group = Vec::new();
            visit(index, &incoming, &mut seen, &mut group);
            let cyclic = group.len() > 1 || calls[index].contains(&index);
            groups.push((group, cyclic));
        }
        groups.reverse();
        groups
    }

    fn functions(&mut self) -> Result<Vec<Function>, Error> {
        // Until a body has supplied its contract, every compatible reference
        // parameter is a possible return origin. This is also the initial
        // approximation for a mutually recursive group.
        let output_path = self.path(vec![Position::TaskOutput]);
        self.contracts = self.signatures.iter().map(|signature| {
            let mut dependencies = Vec::new();
            for (parameter, &(_, ty)) in signature.parameters.iter().enumerate() {
                if !self.has_dependencies(ty) { continue; }
                let dependency = ReturnDependency {
                    parameter, from: PathId::default(), at: PathId::default(),
                    opaque: true, capture_exclusive: true,
                    pool: false,
                    lock: PathId::default(),
                };
                if self.carries_handle(signature.result) {
                    continue;
                }
                dependencies.push(dependency);
                let input_handle = matches!(ty, Ty::Handle(layout, _) if self.has_dependencies(self.handle_output(layout)));
                if input_handle {
                    dependencies.push(ReturnDependency { from: output_path, ..dependency });
                }
            }
            dependencies
        }).collect();
        let mut bodies = (0..self.signatures.len()).map(|_| None).collect::<Vec<_>>();
        self.entry_contracts = vec![None; self.signatures.len()];
        self.wait_contracts = vec![Vec::new(); self.signatures.len()];
        self.returned_entry_contracts = vec![Vec::new(); self.signatures.len()];
        for (group, cyclic) in self.function_groups() {
            let mut seen = Vec::new();
            loop {
                let generated_count = self.generated_functions.len();
                let mut changed = false;
                for &index in &group {
                    bodies[index] = Some(self.function(self.signatures[index].clone())?);
                    self.entry_effects.sort_unstable();
                    if !self.carries_handle(self.function_result) {
                        for (parameter, path) in &mut self.waited_parameters {
                            if matches!(self.parameters[*parameter].1, Ty::Struct(_) | Ty::Handle(..)) {
                                *path = PathId::default();
                            }
                        }
                    }
                    self.waited_parameters.sort_unstable();
                    self.waited_parameters.dedup();
                    self.returned_entry_effects.sort_unstable();
                    changed |= self.contracts[index] != self.returned
                        || self.entry_contracts[index].as_ref() != Some(&self.entry_effects)
                        || self.wait_contracts[index] != self.waited_parameters
                        || self.returned_entry_contracts[index] != self.returned_entry_effects;
                    self.contracts[index] = self.returned.clone();
                    self.entry_contracts[index] = Some(self.entry_effects.clone());
                    self.wait_contracts[index] = self.waited_parameters.clone();
                    self.returned_entry_contracts[index] = self.returned_entry_effects.clone();
                }
                if !cyclic || !changed {
                    break;
                }
                let contracts = group.iter().map(|&index| (
                    self.contracts[index].clone(), self.entry_contracts[index].clone(),
                    self.wait_contracts[index].clone(), self.returned_entry_contracts[index].clone(),
                )).collect::<Vec<_>>();
                if seen.contains(&contracts) || seen.len() == 64 {
                    return Err(self.error(self.signatures[group[0]].body,
                        "le contrat du cycle récursif ne se stabilise pas"));
                }
                seen.push(contracts);
                // Generated bodies may depend on the contracts being solved.
                // Rebuild those introduced in this pass before rechecking the cycle.
                self.native_blocks.retain(|_, index| *index < generated_count);
                let first_rolled_back = self.signatures.len() + generated_count;
                self.pipeline_mappers.retain(|_, (index, _)| *index < first_rolled_back);
                self.pipeline_mapper_waits.retain(|index, _| *index < first_rolled_back);
                self.generated_functions.truncate(generated_count);
                self.native_contracts.truncate(generated_count);
                self.native_entry_contracts.truncate(generated_count);
                self.native_returned_entries.truncate(generated_count);
            }
        }
        Ok(bodies.into_iter().map(Option::unwrap).collect())
    }

    fn function(&mut self, signature: Signature) -> Result<Function, Error> {
        self.slots.fill(None);
        self.next_temp = 0;
        self.parameters.clone_from(&signature.parameters);
        self.returned.clear();
        self.entry_effects.clear();
        self.waited_parameters.clear();
        self.propagation_waits = None;
        self.returned_entry_effects.clear();
        self.function_result = signature.result;
        self.in_async = signature.asynchronous;
        for &(binding, ty) in &signature.parameters {
            let awaited_loan = if matches!(ty, Ty::Handle(layout, _) if self.has_dependencies(self.handle_output(layout)))
            {
                let from = self.path(vec![Position::TaskOutput]);
                Some(self.intern(vec![Origin {
                    root: binding,
                    storage: false,
                    pool: false,
                    parent: None,
                    at: PathId::default(),
                    from,
                    lock: PathId::default(),
                    opaque: false,
                    capture_exclusive: false,
                }]))
            } else {
                None
            };
            self.slots[binding.0] = Some(Slot {
                vector_len: None,
                field_lengths: None,
                awaited_loan,
                ty,
                loan: self.has_dependencies(ty).then(|| {
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
                }),
                state: State::Live,
            });
        }
        let mut body = Vec::new();
        if self.block(signature.body, signature.result, true, &mut body)? {
            if signature.result != Ty::Void {
                return Err(self.error(signature.body, "un chemin termine sans résultat"));
            }
            body.push(Instr::Return(None));
        }
        if let Some(waits) = self.propagation_waits.take() {
            self.waited_parameters.retain(|wait| waits.contains(wait));
        }
        let body_offset = self.tree.tokens[self.node(signature.body).start].span.start;
        let std_io = self.tree.std_async_io_ranges.iter().any(|range| range.contains(&body_offset));
        if signature.asynchronous && !async_region_body(&body, &self.structures, std_io) {
            return Err(self.error(signature.body, "le prototype async accepte ici les opérations fixes et les collections locales prises en charge"));
        }
        Ok(Function {
            parameters: signature.parameters,
            borrowed_parameters: Vec::new(),
            result: signature.result,
            body,
            entry: signature.entry,
            native: false,
            asynchronous: signature.asynchronous,
        })
    }

    fn carries_handle(&self, ty: Ty) -> bool {
        contains_handle(ty, &self.structures)
            || matches!(ty, Ty::Allocation(content) if contains_handle(content.ty(), &self.structures)
                || matches!(self.growing_layout(content.ty()), Some(Growing::Vector(element))
                    if contains_handle(element, &self.structures)))
    }

    fn requires_wait(&self, ty: Ty) -> bool {
        self.carries_handle(ty) || match ty {
            Ty::Future(function) => self.signatures[function].parameters.iter()
                .any(|(_, ty)| self.carries_handle(*ty)),
            _ => false,
        }
    }

    fn handle_origin(&self, ty: Ty, path: &[Position]) -> bool {
        let ty = match ty {
            Ty::Allocation(content) => {
                return match path {
                    [Position::Field(0), rest @ ..] if contains_handle(content.ty(), &self.structures) =>
                        self.handle_origin(content.ty(), rest),
                    [Position::Index(_), ..] => self.handle_origin(content.ty(), path),
                    _ => false,
                };
            }
            _ => ty,
        };
        let Ty::Struct(index) = ty else { return matches!(ty, Ty::Handle(..)) };
        let layout = &self.structures[index];
        let projected = match path {
            [Position::Field(field), rest @ ..] =>
                layout.fields.get(*field).map(|(_, ty)| (*ty, rest)),
            [Position::Variant(tag), Position::Field(field), rest @ ..] =>
                layout.variants.get(*tag).and_then(|(_, fields)| fields.get(*field))
                    .map(|(_, ty)| (*ty, rest)),
            [Position::Index(_), rest @ ..] => layout.array.map(|(ty, _)| (ty, rest))
                .or_else(|| match layout.growing {
                    Some(Growing::Vector(ty)) => Some((ty, rest)),
                    _ => None,
                }),
            _ => None,
        };
        projected.map_or_else(
            || contains_handle(ty, &self.structures),
            |(ty, rest)| self.handle_origin(ty, rest),
        )
    }

    fn dependent_handle(&self, ty: Ty, loan: Option<LoanId>) -> bool {
        self.origins(loan).iter().any(|origin| match ty {
            Ty::Future(_) => self.requires_wait(ty),
            _ => {
                let path = &self.dependencies.paths[origin.at.0];
                self.handle_origin(ty, path)
                    || (path.is_empty() && !origin.storage && !origin.pool && self.carries_handle(ty))
            }
        })
    }

    fn has_dependent_handle_output(&self, ty: Ty, loan: Option<LoanId>) -> bool {
        matches!(ty, Ty::Handle(layout, _) if self.dependent_handle(self.handle_output(layout), loan))
    }

    fn check_thread_exit(
        &self,
        id: NodeId,
        exits: impl Fn(crate::tree::ScopeId) -> bool,
    ) -> Result<(), Error> {
        if self.slots.iter().enumerate().any(|(index, slot)| {
            slot.is_some_and(|slot| {
                (self.dependent_handle(slot.ty, slot.loan)
                    || self.has_dependent_handle_output(slot.ty, slot.awaited_loan))
                    && !matches!(slot.state, State::Moved(_))
                    && exits(self.tree.bindings[index].scope)
            })
        }) {
            return Err(self.error(
                id,
                "le handle à captures dépendantes doit être joint avant cette sortie",
            ));
        }
        Ok(())
    }

    fn in_scope(&self, parent: crate::tree::ScopeId, mut child: crate::tree::ScopeId) -> bool {
        loop {
            if parent == child {
                return true;
            }
            let Some(next) = self.tree.scopes[child.0].parent else {
                return false;
            };
            child = next;
        }
    }

    fn block(
        &mut self,
        id: NodeId,
        result: Ty,
        function_body: bool,
        out: &mut Vec<Instr>,
    ) -> Result<bool, Error> {
        let mut continues = true;
        for &statement in &self.node(id).children {
            if !continues {
                break;
            }
            if self.region_scope(statement, out)? {
                continue;
            }
            continues = self.statement(statement, result, function_body, out)?;
        }
        self.check_thread_exit(id, |scope| self.tree.scopes[scope.0].syntax == id)?;
        for scope in self.tree.scopes.iter().filter(|scope| scope.syntax == id) {
            for binding in &scope.bindings {
                self.slots[binding.0] = None;
            }
        }
        Ok(continues)
    }

    fn statement(
        &mut self,
        id: NodeId,
        result: Ty,
        function_body: bool,
        out: &mut Vec<Instr>,
    ) -> Result<bool, Error> {
        let node = self.node(id);
        let children = &node.children;
        match node.kind {
            "unchecked" => {
                let mut body = Vec::new();
                let continues = self.block(children[0], result, false, &mut body)?;
                out.push(Instr::Block(body));
                return Ok(continues);
            }
            "asm" => {
                let abi = self.tree.target.assembly_abi()
                    .ok_or_else(|| self.error(id, "@asm indisponible pour cette cible"))?;
                let token = self.tree.tokens[node.start].span;
                let block = crate::assembly::lower(
                    abi, &self.source[token.start..token.end], token.start, |index, write| {
                        let operand = children[index];
                        let binding = *self.uses.get(&operand)
                            .ok_or_else(|| self.error(operand, "liaison assembleur inconnue"))?;
                        let ty = self.live_slot(operand, binding)?.ty;
                        self.access_target(id, binding, write, false)?;
                        if write && !self.tree.bindings[binding.0].mutable {
                            return Err(self.error(operand, "sortie assembleur exige une liaison mutable"));
                        }
                        Ok((binding, ty))
                    },
                )?;
                out.push(Instr::Assembly(block));
            }
            "tuple let" => {
                let (expected, expression, names) = if self.node(children[0]).kind == "type" {
                    (Some(self.ty(children[0])?), children[1], &children[2..])
                } else {
                    (None, children[0], &children[1..])
                };
                let tuple = self.expression(expression, expected, Access::Move, out)?;
                let fields = self.tuple_fields(tuple.ty)
                    .filter(|fields| fields.len() == names.len())
                    .ok_or_else(|| self.error(id, "tuple pattern arity mismatch"))?.to_vec();
                let mut seen = std::collections::HashSet::new();
                for (position, (&name, (_, ty))) in names.iter().zip(fields).enumerate() {
                    if !seen.insert(self.name(name).unwrap()) {
                        return Err(self.error(name, "duplicate tuple binding"));
                    }
                    let mut value = self.emit(ty, Expr::TakeTupleField(tuple, position), out);
                    let origins = self.selected_origins(tuple.dependencies.loan, &[Position::Field(position)]);
                    self.unpack_output(&mut value, origins);
                    let value = value.finish_evaluation(out);
                    let binding = self.bindings[&name];
                    self.bind_value(name, binding, value)?;
                    out.push(Instr::Bind(binding, value));
                }
            }
            "liaison" => {
                let binding = self.bindings[&id];
                let expected = if children.len() == 2 {
                    Some(self.ty(children[0])?)
                } else {
                    None
                };
                let value =
                    self.expression(*children.last().unwrap(), expected, Access::Move, out)?;
                self.bind_value(id, binding, value)?;
                out.push(Instr::Bind(binding, value));
            }
            "move nommé" => {
                if self.native_entries.contains(&id) {
                    return Ok(true);
                }
                let &(source, destination) = self
                    .moves
                    .get(&id)
                    .ok_or_else(|| self.error(id, "source de move inconnue"))?;
                let value = self.local(id, source, Access::Move, out)?;
                self.bind_value(id, destination, value)?;
                out.push(Instr::Bind(destination, value));
            }
            "affectation" => {
                if self.name(id) != Some("=") {
                    self.compound_assignment(id, children[0], children[1], out)?;
                    return Ok(true);
                }
                let place = children[0];
                if self.node(place).kind == "indice" {
                    let children = &self.node(place).children;
                    let base = children[0];
                    let row = (self.node(base).kind == "indice").then(|| self.node(base).children[0]);
                    let slice = row.unwrap_or(base);
                    let binding = *self
                        .uses
                        .get(&slice)
                        .ok_or_else(|| self.error(place, "liaison de tableau requise"))?;
                    if let Some(Ty::Slice { mutable, .. }) = self.known_type(slice) {
                        if !mutable {
                            return Err(self.error(place, "écriture dans une tranche partagée"));
                        }
                        let (element, address) = if row.is_some() {
                            let (row_type, row_address) = self.slice_element_address(base, out)?;
                            let (ty, length) = self.array_layout(base, row_type.ty())?;
                            let referent = ty.referent()
                                .ok_or_else(|| self.error(place, "élément de ligne hors périmètre"))?;
                            let mut owner = self.emit(Ty::Ref { target: row_type, mutable: true },
                                Expr::SliceElementBorrow(row_address), out);
                            owner.dependencies.loan = row_address.dependencies.loan;
                            let index = self.index_after_owner(children[1], length, owner, out)?;
                            let mut address = self.emit(Ty::Ref { target: referent, mutable: true },
                                Expr::BorrowIndex(owner, index), out);
                            address.dependencies.loan = row_address.dependencies.loan;
                            (referent, address)
                        } else {
                            self.slice_element_address(place, out)?
                        };
                        let ty = element.ty();
                        if !structurally_replicable(ty, &self.structures) || self.has_dependencies(ty) {
                            return Err(self.error(place, "remplacement d’un élément de tranche hors périmètre"));
                        }
                        let slot = self.live_slot(place, binding)?;
                        self.access_reference(place, binding, true)?;
                        let origins = self.origins(address.dependencies.loan).iter()
                            .map(|origin| Origin { parent: Some(binding), ..*origin })
                            .collect();
                        let loan = Some(self.intern(origins));
                        let pending = self.pending.len();
                        self.pending.push(Value {
                            ty: slot.ty,
                            dependencies: DependencySummary { loan, ..address.dependencies },
                            ..address
                        });
                        let value = self.expression(node.children[1], Some(ty), Access::Move, out);
                        self.pending.truncate(pending);
                        let value = value?;
                        self.live_slot(place, binding)?;
                        self.access_reference(id, binding, true)?;
                        out.push(Instr::WriteSliceElement(address, value));
                        return Ok(true);
                    }
                    if row.is_some() {
                        return Err(self.error(place, "liaison de tableau requise"));
                    }
                    if !self.tree.bindings[binding.0].mutable {
                        return Err(self.error(place, "tableau immuable"));
                    }
                    let owner = self.local(children[0], binding, Access::Read, out)?;
                    let (element, length) = self.array_layout(place, owner.ty)?;
                    if element.scalar().is_none()
                        && (!matches!(element, Ty::Struct(_)) || owns_resources(element, &self.structures))
                    {
                        return Err(self.error(place, "écriture d’un élément de tableau hors périmètre"));
                    }
                    let index = self.index_after_owner(children[1], length, owner, out)?;
                    let value =
                        self.expression(node.children[1], Some(element), Access::Move, out)?;
                    self.live_slot(place, binding)?;
                    let position = Position::Index(index.integer.and_then(|n| usize::try_from(n).ok()));
                    self.access_projected_at(id, binding, false, true, true, &[position])?;
                    if self.has_dependencies(element) {
                        let slot = self.live_slot(id, binding)?;
                        let scope = self.tree.bindings[binding.0].scope;
                        self.check_dependency_scope(id, scope, value.dependencies.loan)?;
                        let position = Position::Index(index.integer.and_then(|n| usize::try_from(n).ok()));
                        let mut origins = self.origins(slot.loan).iter().copied()
                            .filter(|origin| !matches!(position, Position::Index(Some(_)))
                                || self.dependencies.paths[origin.at.0].first() != Some(&position))
                            .collect::<Vec<_>>();
                        self.append_origins(&mut origins, value.dependencies.loan, &[position]);
                        self.slots[binding.0] = Some(Slot {
                            loan: (!origins.is_empty()).then(|| self.intern(origins)),
                            ..slot
                        });
                    }
                    out.push(Instr::WriteIndex(owner, index, value));
                    return Ok(true);
                }
                if self.node(place).kind == "indirection" {
                    let source = self.node(place).children[0];
                    if self.node(source).kind == "indirection" {
                        let (reference, outer) = self.dereference(source, true)?;
                        let Ty::Ref { target, mutable: true } = outer.ty() else {
                            return Err(self.error(place, "écriture exige deux références mutables"));
                        };
                        if target.ty().scalar().is_none() {
                            return Err(self.error(place, "écriture imbriquée exige une cible primitive"));
                        }
                        let value = self.expression(node.children[1], Some(target.ty()), Access::Move, out)?;
                        self.dereference(source, true)?;
                        if value.ty == Ty::Usize && value.dependencies.loan.is_some() {
                            return Err(self.error(id, "écriture indirecte d’une adresse suivie hors périmètre"));
                        }
                        out.push(Instr::WriteNested(reference, value));
                        return Ok(true);
                    }
                    let (reference, target) = self.dereference(place, true)?;
                    if matches!(target.ty(), Ty::Ref { .. }) {
                        let loan = self.live_slot(place, reference)?.loan;
                        let value = self.expression(children[1], Some(target.ty()), Access::Move, out)?;
                        self.dereference(place, true)?;
                        self.replace_entry_loan(place, loan, value.dependencies.loan, true)?;
                        let mut origins = self.origins(loan).to_vec();
                        origins.extend_from_slice(self.origins(value.dependencies.loan));
                        let slot = self.live_slot(place, reference)?;
                        self.slots[reference.0] = Some(Slot {
                            loan: (!origins.is_empty()).then(|| self.intern(origins)),
                            ..slot
                        });
                        out.push(Instr::WriteThrough(reference, value));
                        return Ok(true);
                    }
                    if target.ty().scalar().is_none() {
                        return Err(
                            self.error(id, "remplacement d’un agrégat emprunté hors périmètre")
                        );
                    }
                    let value =
                        self.expression(children[1], Some(target.ty()), Access::Move, out)?;
                    self.live_slot(place, reference)?;
                    if value.ty == Ty::Usize && value.dependencies.loan.is_some() {
                        return Err(self.error(id, "écriture indirecte d’une adresse suivie hors périmètre"));
                    }
                    out.push(Instr::WriteThrough(reference, value));
                    return Ok(true);
                }
                let binding = *self
                    .uses
                    .get(&place)
                    .ok_or_else(|| self.error(place, "place locale requise"))?;
                let slot = self.slots[binding.0]
                    .ok_or_else(|| self.error(place, "liaison non initialisée"))?;
                if !self.tree.bindings[binding.0].mutable {
                    return Err(self.error(place, "affectation à une liaison immuable"));
                }
                if slot.ty.scalar().is_none() {
                    return Err(self.error(
                        place,
                        "réaffectation de référence hors du sous-ensemble vérifié",
                    ));
                }
                let value = self.expression(children[1], Some(slot.ty), Access::Move, out)?;
                self.access_target(id, binding, true, true)?;
                self.bind_value(id, binding, value)?;
                out.push(Instr::Write(binding, value));
            }
            "yield" if self.in_async => out.push(Instr::Yield),
            "while" => {
                return self
                    .loop_effect(id, result, None, out)
                    .map(|(continues, _)| continues);
            }
            "break" | "continue" => {
                let Some(edges) = self.loops.last() else {
                    return Err(self.error(id, "sortie hors d’une boucle"));
                };
                let receiver = edges.receiver;
                let expected = edges.result_type;
                if node.kind == "continue" {
                    let scope = edges.scope;
                    self.check_thread_exit(id, |binding_scope| {
                        scope.is_some_and(|scope| self.in_scope(scope, binding_scope))
                    })?;
                    self.loops
                        .last_mut()
                        .unwrap()
                        .continues
                        .push(self.slots.clone());
                    out.push(Instr::Continue);
                } else {
                    let assignment = match (receiver, children.first()) {
                        (None, None) => None,
                        (Some(temp), Some(&expression)) => {
                            let value = self.expression(expression, expected, Access::Move, out)?;
                            if self.pool_layout(value.ty).is_some() {
                                return Err(self.error(
                                    id,
                                    "résultat de boucle avec pool ou allocation hors périmètre",
                                ));
                            }
                            let origins = self.origins(value.dependencies.loan).to_vec();
                            let awaited_origins = self.origins(value.dependencies.awaited_loan).to_vec();
                            let edges = self.loops.last_mut().unwrap();
                            edges.awaited_origins.extend(awaited_origins);
                            edges.result_type = Some(value.ty);
                            edges.origins.extend(origins);
                            Some((
                                Value {
                                    ty: value.ty,
                                    temp,
                                    receiver: true,
                                    integer: None,
                                    provenance: ValueProvenance::Merged,
                                    dependencies: DependencySummary::default(),
                                },
                                value,
                            ))
                        }
                        (Some(_), None) => {
                            return Err(
                                self.error(id, "break sans valeur pour une boucle à résultat")
                            );
                        }
                        (None, Some(_)) => {
                            return Err(self.error(id, "break avec valeur sans receveur"));
                        }
                    };
                    let scope = self.loops.last().unwrap().scope;
                    self.check_thread_exit(id, |binding_scope| {
                        scope.is_some_and(|scope| self.in_scope(scope, binding_scope))
                    })?;
                    self.loops
                        .last_mut()
                        .unwrap()
                        .breaks
                        .push(self.slots.clone());
                    out.push(Instr::Break(assignment));
                }
                return Ok(false);
            }
            "résultat" if function_body && result == Ty::Void => {
                return self.effect(children[0], result, out);
            }
            "return" | "résultat" if node.kind == "return" || function_body => {
                let value = match (result, children.first()) {
                    (Ty::Void, None) => None,
                    (Ty::Void, Some(_)) | (_, None) => {
                        return Err(self.error(id, "valeur de retour incompatible"));
                    }
                    (ty, Some(expression)) => {
                        Some(self.expression(*expression, Some(ty), Access::Move, out)?)
                    }
                };
                if let Some(value) = value {
                    self.record_return(id, value)?;
                }
                self.check_thread_exit(id, |_| true)?;
                out.push(Instr::Return(value));
                return Ok(false);
            }
            "instruction" | "résultat" => return self.effect(children[0], result, out),
            _ => return Err(self.error(id, "instruction hors du sous-ensemble vérifié")),
        }
        Ok(true)
    }

    fn effect(&mut self, id: NodeId, result: Ty, out: &mut Vec<Instr>) -> Result<bool, Error> {
        if self.node(id).kind == "propagation" {
            if self.propagate(id, out)?.is_some() {
                return Err(self.error(id, "le résultat de ? exige un receveur ou un drop explicite"));
            }
            return Ok(true);
        }
        if self.node(id).kind == "await" {
            let value = self.await_future(id, out)?;
            if value.ty != Ty::Void {
                return Err(self.error(
                    id,
                    "le résultat de .await exige un receveur ou un drop explicite",
                ));
            }
            return Ok(true);
        }
        if self.runtime_call(id, "spawn") || self.runtime_call(id, "spawn_blocking") {
            let value = self.expression(id, None, Access::Move, out)?;
            if value.dependencies.loan.is_some() {
                return Err(self.error(
                    id,
                    "un handle à captures dépendantes ne peut pas être abandonné",
                ));
            }
            out.push(Instr::DropHandle(value));
            return Ok(true);
        }
        if let Some(block) = self.native_block(id) {
            let value = self.native_start(id, block, true, out)?;
            if value.dependencies.loan.is_some() {
                return Err(self.error(
                    id,
                    "un handle à captures dépendantes ne peut pas être abandonné",
                ));
            }
            out.push(Instr::DropHandle(value));
            return Ok(true);
        }
        let node = self.node(id);
        match node.kind {
            "scope" => {
                let mut body = Vec::new();
                let continues = self.block(id, result, false, &mut body)?;
                out.push(Instr::Block(body));
                return Ok(continues);
            }
            "loop" => {
                return self
                    .loop_effect(id, result, None, out)
                    .map(|(continues, _)| continues);
            }
            "if" => {
                let condition =
                    self.expression(node.children[0], Some(Ty::Bool), Access::Read, out)?;
                let before = self.slots.clone();
                let mut yes = Vec::new();
                let yes_continues = self.block(node.children[1], result, false, &mut yes)?;
                let yes_slots = std::mem::replace(&mut self.slots, before.clone());
                let mut no = Vec::new();
                let no_continues = match node.children.get(2).copied() {
                    Some(branch) if self.node(branch).kind == "scope" => {
                        self.block(branch, result, false, &mut no)?
                    }
                    Some(branch) => self.effect(branch, result, &mut no)?,
                    None => true,
                };
                let no_slots = self.slots.clone();
                let continuing = [
                    yes_continues.then_some(&yes_slots),
                    no_continues.then_some(&no_slots),
                ];
                self.slots = self
                    .merge_slots(&before, continuing.into_iter().flatten())
                    .unwrap_or(before);
                out.push(Instr::If(condition, yes, no));
                return Ok(yes_continues || no_continues);
            }
            "match" => {
                return self
                    .enum_match(id, result, None, out)
                    .map(|(continues, _)| continues);
            }
            "appel méthode" if self.name(id) == Some("collect") && self.pipeline_candidate(node.children[0]) => {
                self.iter_collect(id, out)?;
                return Ok(true);
            }
            "appel méthode" if matches!(self.name(id), Some("push" | "push_str")) => {
                self.growing_method(id, out)?;
                return Ok(true);
            }
            "appel méthode" => {
                let (callee, values, result, _, _) = self.call(id, out)?;
                if result != Ty::Void || self.signatures[callee].asynchronous {
                    return Err(self.error(id, "le résultat de la méthode exige un receveur ou un drop explicite"));
                }
                out.push(Instr::Call(callee, values));
            }
            "appel" => {
                let callee = node.children[0];
                if self.node(callee).kind != "nom" || self.uses.contains_key(&callee) {
                    return Err(self.error(id, "appel indirect hors du sous-ensemble vérifié"));
                }
                let arguments = &node.children[1..];
                match self.name(callee) {
                    Some("print") => {
                        if arguments.len() != 1 {
                            return Err(self.error(id, "print exige un argument"));
                        }
                        let value = self.expression(arguments[0], None, Access::Read, out)?;
                        if value.ty.scalar().is_none() {
                            return Err(self.error(id, "print exige une valeur scalaire"));
                        }
                        out.push(Instr::Print(value));
                    }
                    Some("drop") => {
                        if arguments.len() != 1 {
                            return Err(self.error(id, "drop exige un argument"));
                        }
                        let candidate = self.uses.get(&arguments[0]).copied();
                        let pool = candidate
                            .and_then(|binding| self.slots[binding.0])
                            .is_some_and(|slot| self.pool_layout(slot.ty).is_some());
                        let value = if pool {
                            let binding = candidate.unwrap();
                            let slot = self.live_slot(id, binding)?;
                            if self.slots.iter().flatten().any(|value| {
                                (owns_pool_slots(value.ty, &self.structures)
                                    || contains_handle(value.ty, &self.structures)
                                    || matches!(value.ty, Ty::Future(_)))
                                    && !matches!(value.state, State::Moved(_))
                                    && self
                                        .origins(value.loan)
                                        .iter()
                                        .any(|origin| origin.root == binding)
                            }) {
                                return Err(self.error(id, "le pool porte encore une allocation"));
                            }
                            self.access_target(id, binding, true, false)?;
                            if self.pending.iter().any(|value| {
                                (owns_pool_slots(value.ty, &self.structures)
                                    || contains_handle(value.ty, &self.structures)
                                    || matches!(value.ty, Ty::Future(_)))
                                    && self
                                        .origins(value.dependencies.loan)
                                        .iter()
                                        .any(|origin| origin.root == binding)
                            }) {
                                return Err(self.error(id, "le pool porte encore une allocation"));
                            }
                            let value = self.local(arguments[0], binding, Access::Read, out)?;
                            self.slots[binding.0] = Some(Slot {
                                state: State::Moved(id),
                                ..slot
                            });
                            value
                        } else {
                            self.expression(arguments[0], None, Access::Move, out)?
                        };
                        if self.dependent_handle(value.ty, value.dependencies.loan)
                            || self.has_dependent_handle_output(value.ty, value.dependencies.awaited_loan)
                        {
                            return Err(self.error(id, "un handle à captures dépendantes ne peut pas être abandonné"));
                        }
                        if matches!(value.ty, Ty::Allocation(_)) {
                            out.push(Instr::DropAllocation(value));
                        } else if matches!(value.ty, Ty::Handle(..) | Ty::Future(_)) {
                            out.push(Instr::DropHandle(value));
                        } else if owns_resources(value.ty, &self.structures) {
                            out.push(Instr::DropOwned(value));
                        } else if matches!(self.growing_layout(value.ty), Some(Growing::Map(..))) {
                            out.push(Instr::DropMap(value));
                        } else {
                            out.push(Instr::Discard(value));
                        }
                    }
                    Some(name)
                        if self.names.get(name).is_some_and(|&index| {
                            !self.signatures[index].asynchronous
                                && self.signatures[index].result == Ty::Void
                        }) =>
                    {
                        let (callee, values, _, _, _) = self.call(id, out)?;
                        out.push(Instr::Call(callee, values));
                    }
                    _ => {
                        return Err(
                            self.error(id, "appel sans receveur hors du sous-ensemble vérifié")
                        );
                    }
                }
            }
            _ => return Err(self.error(id, "effet hors du sous-ensemble vérifié")),
        }
        Ok(true)
    }

    fn loop_effect(
        &mut self,
        id: NodeId,
        result: Ty,
        receiver: Option<Option<Ty>>,
        out: &mut Vec<Instr>,
    ) -> Result<(bool, Option<Value>), Error> {
        let node = self.node(id);
        let body_id = *node.children.last().unwrap();
        let initial = self.slots.clone();
        let expected = receiver
            .flatten()
            .or_else(|| receiver.and_then(|_| self.loop_result_type(body_id)));
        let temp = receiver.map(|_| {
            let temp = self.next_temp;
            self.next_temp += 1;
            temp
        });
        let saved_temp = self.next_temp;
        let mut head = initial.clone();
        loop {
            self.slots.clone_from(&head);
            self.next_temp = saved_temp;
            let mut condition = Vec::new();
            let test = if node.kind == "while" {
                Some(self.expression(
                    node.children[0],
                    Some(Ty::Bool),
                    Access::Read,
                    &mut condition,
                )?)
            } else {
                None
            };
            let false_edge = test.map(|_| self.slots.clone());
            self.loops.push(LoopEdges {
                receiver: temp,
                result_type: expected,
                scope: self
                    .tree
                    .scopes
                    .iter()
                    .position(|scope| scope.syntax == id || scope.syntax == body_id)
                    .map(crate::tree::ScopeId),
                ..LoopEdges::default()
            });
            let mut body = Vec::new();
            let body_result = self.block(body_id, result, false, &mut body);
            let mut edges = self.loops.pop().unwrap();
            if body_result? {
                edges.continues.push(self.slots.clone());
            }
            let next_head = self
                .merge_slots(&initial, std::iter::once(&initial).chain(&edges.continues))
                .unwrap();
            if next_head == head {
                let exit = self.merge_slots(&initial, false_edge.iter().chain(&edges.breaks));
                let continues = exit.is_some();
                let value = if let Some(temp) = temp {
                    let ty = edges.result_type.filter(|_| continues).ok_or_else(|| {
                        self.error(id, "aucun break ne fournit la valeur de la boucle")
                    })?;
                    if edges.origins.iter().any(|origin| {
                        initial[origin.root.0].is_none()
                            || origin
                                .parent
                                .is_some_and(|parent| initial[parent.0].is_none())
                    }) {
                        return Err(self.error(id, "l’emprunt ne survit pas à la sortie de boucle"));
                    }
                    let loan = (!edges.origins.is_empty()).then(|| self.intern(edges.origins));
                    let awaited_loan = (!edges.awaited_origins.is_empty())
                        .then(|| self.intern(edges.awaited_origins));
                    let value = Value {
                        ty,
                        temp,
                        receiver: true,
                        integer: None,
                        provenance: ValueProvenance::Merged,
                        dependencies: DependencySummary { loan, awaited_loan, ..Default::default() },
                    };
                    out.push(Instr::Reserve(value));
                    Some(value)
                } else {
                    None
                };
                self.slots = exit.unwrap_or(initial);
                out.push(Instr::Loop {
                    condition,
                    test,
                    body,
                });
                return Ok((continues, value));
            }
            head = next_head;
        }
    }

    fn emit(&mut self, ty: Ty, expression: Expr, out: &mut Vec<Instr>) -> Value {
        let value = Value {
            ty,
            temp: self.next_temp,
            receiver: false,
            provenance: match expression {
                Expr::Local(binding) => ValueProvenance::LocalRead(binding),
                _ => ValueProvenance::Expression,
            },
            dependencies: DependencySummary::default(),
            integer: if let Expr::Integer(number) = expression {
                Some(number)
            } else {
                None
            },
        };
        self.next_temp += 1;
        out.push(Instr::Evaluate(value, expression));
        value
    }

    fn intern(&mut self, mut origins: Vec<Origin>) -> LoanId {
        origins.sort_by_key(|origin| {
            (
                origin.root.0,
                origin.storage,
                origin.pool,
                origin.parent.map(|parent| parent.0),
                origin.at,
                origin.from,
                origin.lock,
                origin.opaque,
                origin.capture_exclusive,
            )
        });
        origins.dedup();
        if let Some(index) = self.dependencies.loans.iter().position(|previous| *previous == origins) {
            return LoanId(index);
        }
        let id = LoanId(self.dependencies.loans.len());
        self.dependencies.loans.push(origins);
        id
    }

    fn origins(&self, loan: Option<LoanId>) -> &[Origin] {
        self.dependencies.origins(loan)
    }

    fn has_dependencies(&self, ty: Ty) -> bool {
        match ty {
            Ty::Ref { .. } | Ty::Slice { .. } | Ty::Str | Ty::Allocation(_) | Ty::Handle(..) | Ty::Usize => true,
            Ty::Struct(index) => {
                let layout = &self.structures[index];
                layout.growing.is_some_and(|growing| match growing {
                    Growing::Vector(element) => self.has_dependencies(element),
                    Growing::Map(_, value) => self.has_dependencies(value),
                    Growing::String => false,
                }) || layout
                    .fields
                    .iter()
                    .chain(layout.variants.iter().flat_map(|(_, fields)| fields))
                    .any(|(_, ty)| self.has_dependencies(*ty))
                    || layout
                        .array
                        .is_some_and(|(element, _)| self.has_dependencies(element))
            }
            _ => false,
        }
    }

    fn has_exclusive_dependencies(&self, ty: Ty) -> bool {
        let mut pending = vec![ty];
        let mut visited = std::collections::HashSet::new();
        while let Some(ty) = pending.pop() {
            match ty {
                Ty::Ref { mutable: true, .. } | Ty::Slice { mutable: true, .. } => return true,
                Ty::Allocation(element) => pending.push(element.ty()),
                Ty::Struct(index) if visited.insert(index) => {
                    let layout = &self.structures[index];
                    if let Some(Growing::Vector(element) | Growing::Map(_, element)) = layout.growing {
                        pending.push(element);
                    }
                    if let Some((element, _)) = layout.array {
                        pending.push(element);
                    }
                    pending.extend(
                        layout
                            .fields
                            .iter()
                            .chain(layout.variants.iter().flat_map(|(_, fields)| fields))
                            .map(|(_, ty)| *ty),
                    );
                }
                _ => {}
            }
        }
        false
    }

    fn merge_slots<'b>(
        &mut self,
        base: &Slots,
        paths: impl IntoIterator<Item = &'b Slots>,
    ) -> Option<Slots> {
        let mut paths = paths.into_iter();
        let first = paths.next()?;
        let mut result = base
            .iter()
            .zip(first)
            .map(|(base, current)| base.and(*current))
            .collect::<Slots>();
        for path in paths {
            for (slot, incoming) in result.iter_mut().zip(path) {
                if let (Some(current), Some(incoming)) = (slot, incoming) {
                    if current.vector_len != incoming.vector_len {
                        current.vector_len = None;
                    }
                    if current.field_lengths != incoming.field_lengths {
                        current.field_lengths = None;
                    }
                    if current.loan != incoming.loan {
                        let mut origins = self.origins(current.loan).to_vec();
                        origins.extend_from_slice(self.origins(incoming.loan));
                        current.loan = (!origins.is_empty()).then(|| self.intern(origins));
                    }
                    if current.awaited_loan != incoming.awaited_loan {
                        let mut origins = self.origins(current.awaited_loan).to_vec();
                        origins.extend_from_slice(self.origins(incoming.awaited_loan));
                        current.awaited_loan = (!origins.is_empty()).then(|| self.intern(origins));
                    }
                    if current.state != incoming.state
                        && !matches!((current.state, incoming.state), (State::Moved(_), State::Moved(_)))
                    {
                        current.state = State::Unavailable;
                    }
                }
            }
        }
        Some(result)
    }

    fn path(&mut self, positions: Vec<Position>) -> PathId {
        if let Some(index) = self.dependencies.paths.iter().position(|path| *path == positions) {
            return PathId(index);
        }
        let id = PathId(self.dependencies.paths.len());
        self.dependencies.paths.push(positions);
        id
    }

    fn selected_origins(&mut self, loan: Option<LoanId>, selector: &[Position]) -> Vec<Origin> {
        let mut selected = Vec::new();
        for mut origin in self.origins(loan).to_vec() {
            let path = self.dependencies.paths[origin.at.0].clone();
            if !path
                .iter()
                .zip(selector)
                .all(|(&left, &right)| left.overlaps(right))
            {
                continue;
            }
            if path.len() >= selector.len() {
                origin.at = self.path(path[selector.len()..].to_vec());
            } else {
                if !origin.storage && !origin.pool && !origin.opaque {
                    let mut source = self.dependencies.paths[origin.from.0].clone();
                    source.extend_from_slice(&selector[path.len()..]);
                    origin.from = self.path(source);
                }
                origin.at = PathId::default();
            }
            selected.push(origin);
        }
        selected
    }

    fn selected_loan(&mut self, loan: Option<LoanId>, selector: &[Position]) -> Option<LoanId> {
        let origins = self.selected_origins(loan, selector);
        (!origins.is_empty()).then(|| self.intern(origins))
    }

    // A shared reference stored in the source can point outside the source's
    // storage. Its target can then be shared by successive calls to next.
    fn shared_dependency_at(&self, ty: Ty, path: &[Position]) -> bool {
        matches!(self.dependency_type_at(ty, path),
            Some(Ty::Ref { mutable: false, .. } | Ty::Slice { mutable: false, .. } | Ty::Str))
    }

    fn dependency_type_at(&self, ty: Ty, path: &[Position]) -> Option<Ty> {
        if path.is_empty() {
            return Some(ty);
        }
        let layout = match ty {
            Ty::Ref { target, .. } | Ty::Allocation(target) => return self.dependency_type_at(target.ty(), path),
            Ty::Struct(layout) => &self.structures[layout],
            _ => return None,
        };
        let field = match path {
            [Position::Field(field), rest @ ..] =>
                layout.fields.get(*field).map(|(_, ty)| (*ty, rest)),
            [Position::Variant(tag), Position::Field(field), rest @ ..] =>
                layout.variants.get(*tag).and_then(|(_, fields)| fields.get(*field))
                    .map(|(_, ty)| (*ty, rest)),
            [Position::Index(_), rest @ ..] => layout.array.map(|(ty, _)| (ty, rest)).or_else(|| match layout.growing {
                Some(Growing::Vector(ty)) => Some((ty, rest)),
                _ => None,
            }),
            _ => None,
        };
        field.and_then(|(ty, rest)| self.dependency_type_at(ty, rest))
    }

    fn returned_argument_origins(
        &mut self, ty: Ty, loan: Option<LoanId>, selector: &[Position], moved_handle: bool,
    ) -> Vec<Origin> {
        let entry = moved_handle && selector.iter().any(|position| matches!(position, Position::Index(_)))
            && matches!(self.dependency_type_at(ty, selector), Some(Ty::Handle(..)));
        let precise = !selector.is_empty() && self.shared_dependency_at(ty, selector)
            && self.origins(loan).iter().any(|origin| {
                let path = &self.dependencies.paths[origin.at.0];
                !origin.opaque && path.len() >= selector.len()
                    && path.iter().zip(selector).all(|(&left, &right)| left.overlaps(right))
            });
        let loan = if precise || entry {
            // The selected shared reference carries its own target. The
            // container's storage only supplied the reference descriptor.
            let origins = self.origins(loan).iter().copied().filter(|origin| {
                !origin.storage || origin.opaque || origin.capture_exclusive || (!entry && origin.pool)
                    || self.dependencies.paths[origin.at.0].len() >= selector.len()
            }).collect();
            Some(self.intern(origins))
        } else {
            loan
        };
        self.selected_origins(loan, selector)
    }

    fn append_origins(
        &mut self,
        origins: &mut Vec<Origin>,
        loan: Option<LoanId>,
        prefix: &[Position],
    ) {
        for mut origin in self.origins(loan).to_vec() {
            let mut path = prefix.to_vec();
            path.extend_from_slice(&self.dependencies.paths[origin.at.0]);
            origin.at = self.path(path);
            origins.push(origin);
        }
    }

    fn union_loans(&mut self, loans: impl IntoIterator<Item = Option<LoanId>>) -> Option<LoanId> {
        let mut loans = loans.into_iter().flatten();
        let first = loans.next()?;
        let mut distinct = loans.filter(|&loan| loan != first).peekable();
        if distinct.peek().is_none() {
            return (!self.origins(Some(first)).is_empty()).then_some(first);
        }
        let origins = std::iter::once(first)
            .chain(distinct)
            .flat_map(|loan| self.origins(Some(loan)).iter().copied())
            .collect::<Vec<_>>();
        (!origins.is_empty()).then(|| self.intern(origins))
    }

    fn merge_dependencies(
        &mut self,
        values: impl Iterator<Item = Value> + Clone,
    ) -> DependencySummary {
        DependencySummary {
            vector_len: None,
            field_lengths: None,
            loan: self.union_loans(values.clone().map(|value| value.dependencies.loan)),
            awaited_loan: self.union_loans(values.map(|value| value.dependencies.awaited_loan)),
        }
    }

    fn record_return(&mut self, id: NodeId, value: Value) -> Result<(), Error> {
        if value.dependencies.loan.is_none()
            && value.dependencies.awaited_loan.is_none()
            && !matches!(value.ty, Ty::Ref { .. })
        {
            return Ok(());
        }
        let mut parameters = Vec::new();
        let origins = self
            .origins(value.dependencies.loan)
            .iter()
            .copied()
            .map(|origin| (origin, false))
            .chain(
                self.origins(value.dependencies.awaited_loan)
                    .iter()
                    .copied()
                    .map(|origin| (origin, true)),
            )
            .collect::<Vec<_>>();
        for (origin, output) in origins {
            if let Some((Position::TaskEffect(index), prefix)) = self.dependencies.paths[origin.at.0].split_last() {
                let mut position = prefix.to_vec();
                if output { position.insert(0, Position::TaskOutput); }
                let (target, source) = self.deferred_entries[*index];
                let output = self.path(position);
                let targets = self.origins(Some(target)).iter().filter_map(|origin| {
                    self.parameters.iter().position(|&(binding, ty)| {
                        binding == origin.root && !origin.storage && matches!(ty, Ty::Ref { target, mutable: true }
                            if matches!(target.ty(), Ty::Ref { .. }))
                    })
                }).collect::<Vec<_>>();
                if targets.is_empty() {
                    return Err(self.error(id, "la tâche retournée modifie une entrée locale"));
                }
                for target in targets {
                    for origin in self.origins(Some(source)).to_vec() {
                        let source = self.parameters.iter().position(|&(binding, _)| {
                            binding == origin.root && !origin.storage
                        }).ok_or_else(|| self.error(id, "la référence installée vise une cible locale"))?;
                        let effect = EntryEffect { target, source, path: origin.from, output };
                        if !self.returned_entry_effects.contains(&effect) {
                            self.returned_entry_effects.push(effect);
                        }
                    }
                }
                continue;
            }
            if self.dependencies.paths[origin.at.0].iter().any(|position| matches!(position, Position::TaskEffect(_))) {
                return Err(self.error(id, "résultat imbriqué à remplacement différé hors périmètre"));
            }
            let index = self
                .parameters
                .iter()
                .position(|&(binding, ty)| {
                    binding == origin.root && !origin.storage && self.has_dependencies(ty)
                })
                .ok_or_else(|| self.error(id, "la référence retournée vise une cible locale"))?;
            let at = if output {
                let mut path = vec![Position::TaskOutput];
                path.extend_from_slice(&self.dependencies.paths[origin.at.0]);
                self.path(path)
            } else {
                origin.at
            };
            parameters.push(ReturnDependency {
                parameter: index,
                from: origin.from,
                at,
                opaque: origin.opaque,
                capture_exclusive: origin.capture_exclusive,
                pool: origin.pool,
                lock: origin.lock,
            });
        }
        if parameters.is_empty() {
            return Err(self.error(id, "provenance du retour emprunté inconnue"));
        }
        self.returned.extend(parameters);
        self.returned.sort_unstable();
        self.returned.dedup();
        Ok(())
    }

    fn survives(&self, mut destination: crate::tree::ScopeId, binding: BindingId) -> bool {
        let source = self.tree.bindings[binding.0].scope;
        loop {
            if destination == source {
                return true;
            }
            let Some(parent) = self.tree.scopes[destination.0].parent else {
                return false;
            };
            destination = parent;
        }
    }

    fn check_dependency_scope(
        &self,
        id: NodeId,
        scope: crate::tree::ScopeId,
        loan: Option<LoanId>,
    ) -> Result<(), Error> {
        if self.origins(loan).iter().any(|origin| {
            !self.survives(scope, origin.root)
                || origin
                    .parent
                    .is_some_and(|parent| !self.survives(scope, parent))
        }) {
            return Err(self.error(
                id,
                "la référence survivrait à sa cible ou à son emprunt parent",
            ));
        }
        Ok(())
    }

    fn bind_value(&mut self, id: NodeId, binding: BindingId, value: Value) -> Result<(), Error> {
        let scope = self.tree.bindings[binding.0].scope;
        self.check_dependency_scope(id, scope, value.dependencies.loan)?;
        self.check_dependency_scope(id, scope, value.dependencies.awaited_loan)?;
        self.slots[binding.0] = Some(Slot {
            vector_len: value.dependencies.vector_len,
            field_lengths: value.dependencies.field_lengths,
            awaited_loan: value.dependencies.awaited_loan,
            loan: value.dependencies.loan,
            ty: value.ty,
            state: State::Live,
        });
        Ok(())
    }

    fn live_slot(&self, id: NodeId, binding: BindingId) -> Result<Slot, Error> {
        let slot =
            self.slots[binding.0].ok_or_else(|| self.error(id, "liaison non initialisée"))?;
        match slot.state {
            State::Live => Ok(slot),
            State::Moved(point) => {
                let mut error = self.error(id, "liaison déjà déplacée");
                error.related_offset = Some(self.tree.tokens[self.node(point).start].span.start);
                Err(error)
            }
            State::Unavailable => Err(self.error(id, "liaison indisponible sur un chemin")),
        }
    }

    fn conflicting_loan(
        &self,
        id: NodeId,
        exclusive: bool,
        write: bool,
        overlaps: impl Fn(Origin) -> bool,
    ) -> bool {
        let matches_loan = |ty, origin: Origin| {
            !(owns_pool_slots(ty, &self.structures) && origin.pool)
                && (exclusive
                    || if matches!(ty, Ty::Future(_))
                        || self.handle_origin(ty, &self.dependencies.paths[origin.at.0]) {
                        origin.capture_exclusive || !origin.storage
                    } else {
                        self.has_exclusive_dependencies(ty)
                    })
                && overlaps(origin)
        };
        self.slots.iter().enumerate().any(|(index, slot)| {
            slot.is_some_and(|slot| {
                !matches!(slot.state, State::Moved(_))
                    && self.origins(slot.loan).iter().any(|&origin| {
                        matches_loan(slot.ty, origin)
                            && (matches!(slot.ty, Ty::Future(_)) && self.requires_wait(slot.ty)
                                || self.handle_origin(slot.ty, &self.dependencies.paths[origin.at.0])
                                || inline_destructor(slot.ty, &self.structures)
                                || matches!(slot.ty, Ty::Allocation(ty) if inline_destructor(ty.ty(), &self.structures))
                                || self.flow.live_at(id, BindingId(index), write, |use_id| {
                                    self.projection_uses_origin(use_id, slot.ty, origin.at)
                                }))
                    })
            })
        }) || self.pending.iter().any(|value| {
            self.origins(value.dependencies.loan)
                .iter()
                .any(|&origin| matches_loan(value.ty, origin))
        })
    }

    fn projection_uses_origin(&self, mut id: NodeId, mut ty: Ty, at: PathId) -> bool {
        for &position in &self.dependencies.paths[at.0] {
            let selector = loop {
                let Some(&parent) = self.syntax_parents.get(&id) else {
                    return true;
                };
                let node = self.node(parent);
                if node.children.first() != Some(&id) {
                    return true;
                }
                id = parent;
                if node.kind == "groupe" {
                    continue;
                }
                if node.kind == "indirection" {
                    ty = match ty {
                        Ty::Ref { target, .. } | Ty::Allocation(target) => target.ty(),
                        _ => return true,
                    };
                    continue;
                }
                let Ty::Struct(layout) = ty else { return true };
                let layout = &self.structures[layout];
                break match node.kind {
                    "projection" => {
                        let Some((field, (_, target))) = layout
                            .fields
                            .iter()
                            .enumerate()
                            .find(|(_, (name, _))| Some(name.as_str()) == self.name(parent))
                        else {
                            return true;
                        };
                        ty = *target;
                        Position::Field(field)
                    }
                    "indice" => {
                        let Some((target, _)) = layout.array else {
                            return true;
                        };
                        ty = target;
                        let index = node.children[1];
                        let index = (self.node(index).kind == "littéral")
                            .then(|| self.length(index).ok())
                            .flatten();
                        Position::Index(index)
                    }
                    _ => return true,
                };
            };
            if !position.overlaps(selector) {
                return false;
            }
        }
        true
    }

    fn access_target(
        &self,
        id: NodeId,
        binding: BindingId,
        exclusive: bool,
        write: bool,
    ) -> Result<(), Error> {
        if self.conflicting_loan(id, exclusive, write, |origin| {
            origin.root == binding && origin.storage
        }) {
            return Err(self.error(id, "accès incompatible avec un emprunt actif"));
        }
        Ok(())
    }

    fn access_reference(
        &self,
        id: NodeId,
        binding: BindingId,
        exclusive: bool,
    ) -> Result<(), Error> {
        if self.conflicting_loan(id, exclusive, false, |origin| {
            self.has_parent(origin, binding)
        }) {
            return Err(self.error(id, "accès incompatible avec un réemprunt actif"));
        }
        Ok(())
    }

    fn has_parent(&self, origin: Origin, binding: BindingId) -> bool {
        // Parents precede their children. Reference reassignment is excluded
        // in this subset, so a chain cannot be redirected into itself.
        let mut pending = origin.parent.into_iter().collect::<Vec<_>>();
        let mut visited = std::collections::HashSet::new();
        while let Some(parent) = pending.pop() {
            if parent == binding {
                return true;
            }
            if visited.insert(parent) {
                pending.extend(
                    self.origins(self.slots[parent.0].and_then(|slot| slot.loan))
                        .iter()
                        .filter_map(|origin| origin.parent),
                );
            }
        }
        false
    }

    fn reborrow(
        &mut self,
        id: NodeId,
        binding: BindingId,
        mutable: bool,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let slot = self.live_slot(id, binding)?;
        let Ty::Ref {
            target,
            mutable: parent_mutable,
        } = slot.ty
        else {
            return Err(self.error(id, "référence requise pour le réemprunt"));
        };
        if mutable && !parent_mutable {
            return Err(self.error(id, "réemprunt mutable d’une référence partagée"));
        }
        self.access_target(id, binding, mutable, false)?;
        self.access_reference(id, binding, mutable)?;
        let origins = self
            .origins(slot.loan)
            .iter()
            .map(|origin| Origin {
                root: origin.root,
                storage: origin.storage,
                pool: origin.pool,
                parent: Some(binding),
                ..*origin
            })
            .collect();
        let mut value = self.emit(Ty::Ref { target, mutable }, Expr::Reborrow(binding), out);
        value.dependencies.loan = Some(self.intern(origins));
        value = value.finish_evaluation(out);
        Ok(value)
    }

    fn dereference(&self, id: NodeId, write: bool) -> Result<(BindingId, Referent), Error> {
        let source = self.node(id).children[0];
        let reference = *self
            .uses
            .get(&source)
            .ok_or_else(|| self.error(id, "référence locale nommée requise"))?;
        let slot = self.live_slot(id, reference)?;
        let Ty::Ref { target, mutable } = slot.ty else {
            return Err(self.error(id, "une référence est requise pour le déréférencement"));
        };
        if write && !mutable {
            return Err(self.error(id, "écriture par une référence partagée"));
        }
        self.access_target(id, reference, write, false)?;
        self.access_reference(id, reference, write)?;
        Ok((reference, target))
    }

    fn local(
        &mut self,
        id: NodeId,
        binding: BindingId,
        access: Access,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let slot = self.live_slot(id, binding)?;
        let exclusive = matches!(access, Access::Move);
        if exclusive && self.mapper_captures.contains(&binding) {
            return Err(self.error(id, "map doit conserver ses captures pour les appels suivants"));
        }
        if exclusive && self.pool_layout(slot.ty).is_some() {
            return Err(self.error(id, "un pool reste dans son scope de création"));
        }
        if matches!(slot.ty, Ty::Ref { .. } | Ty::Slice { .. }) {
            self.access_target(id, binding, exclusive, false)?;
            self.access_reference(id, binding, exclusive)?;
        } else {
            self.access_target(id, binding, exclusive, false)?;
        }
        if matches!(access, Access::Move) {
            self.slots[binding.0] = Some(Slot {
                state: State::Moved(id),
                ..slot
            });
        }
        let mut value = self.emit(slot.ty, Expr::Local(binding), out);
        value.dependencies = DependencySummary {
            vector_len: slot.vector_len,
            field_lengths: slot.field_lengths,
            loan: slot.loan,
            awaited_loan: slot.awaited_loan,
        };
        if exclusive {
            value.provenance = ValueProvenance::LocalMove { binding, at: id };
        }
        Ok(value.finish_evaluation(out))
    }

    fn call_entry_effects(&self, index: usize) -> Vec<EntryEffect> {
        let signature = &self.signatures[index];
        self.entry_contracts[index].clone().unwrap_or_else(|| {
            let mut effects = Vec::new();
            for (target, &(_, ty)) in signature.parameters.iter().enumerate() {
                let Ty::Ref { target: referent, mutable: true } = ty else { continue };
                let incoming = referent.ty();
                if !matches!(incoming, Ty::Ref { .. }) { continue; }
                for (source, &(_, ty)) in signature.parameters.iter().enumerate() {
                    if ty == incoming {
                        effects.push(EntryEffect {
                            target, source, path: PathId::default(), output: PathId::default(),
                        })
                    }
                }
            }
            effects
        })
    }

    fn call_waits(&self, index: usize) -> Vec<(usize, PathId)> {
        let signature = &self.signatures[index];
        if self.entry_contracts[index].is_some() || self.carries_handle(signature.result) {
            return self.wait_contracts[index].clone();
        }
        signature.parameters.iter().enumerate().filter_map(|(parameter, &(_, ty))| {
            self.carries_handle(ty).then_some((parameter, PathId::default()))
        }).collect()
    }

    fn qualified_method(&self, id: NodeId) -> Option<(usize, &'a str)> {
        let callee = self.node(self.node(id).children[0]);
        if callee.kind == "nom qualifié" && callee.children.is_empty() && callee.end == callee.start + 3 {
            let layout = *self.structure_names.get(self.text(callee.start))?;
            Some((layout, self.text(callee.start + 2)))
        } else {
            None
        }
    }

    fn explicit_conversion_target(&self, id: NodeId) -> Option<usize> {
        let (layout, name) = self.qualified_method(id)?;
        (name == "from" && self.conversions.contains_key(&layout)).then_some(layout)
    }

    fn numeric_literal(&self, id: NodeId) -> bool {
        let node = self.node(id);
        match (node.kind, node.children.as_slice()) {
            ("groupe", [child]) => self.numeric_literal(*child),
            ("unaire", [child]) if self.name(id) == Some("-") => self.numeric_literal(*child),
            ("littéral", _) => matches!(
                self.tree.tokens[node.start].kind,
                crate::lexer::Kind::Integer | crate::lexer::Kind::Float
            ),
            _ => false,
        }
    }

    fn function_index(&self, id: NodeId) -> Option<usize> {
        let callee = self.node(id).children[0];
        let node = self.node(callee);
        match node.kind {
            "nom" if !self.uses.contains_key(&callee) => self.names.get(self.name(callee)?).copied(),
            "nom qualifié" => {
                let method = self.qualified_method(id)?;
                let &(index, receiver) = self.methods.get(&method)?;
                (!receiver).then_some(index)
            }
            _ => None,
        }
    }

    fn call(
        &mut self,
        id: NodeId,
        out: &mut Vec<Instr>,
    ) -> Result<(usize, Vec<Value>, Ty, Option<LoanId>, Option<LoanId>), Error> {
        let node = self.node(id);
        if node.kind == "appel" && let Some(layout) = self.explicit_conversion_target(id) {
            let [_, argument] = node.children.as_slice() else {
                return Err(self.error(id, "from exige un seul argument"));
            };
            let candidates = &self.conversions[&layout];
            // Preserve contextual typing of numeric literals for an unambiguous signature.
            let expected = match candidates.as_slice() {
                [(input, _)] if self.numeric_literal(*argument) => Some(*input),
                _ => None,
            };
            let argument = self.expression(*argument, expected, Access::Move, out)?;
            let target = Ty::Struct(layout);
            let index = self.conversion(argument.ty, target)
                .ok_or_else(|| self.error(id, "aucune surcharge from pour ce type source"))?;
            let arguments = vec![argument];
            let (loan, awaited) = self.call_effects(id, index, &arguments)?;
            return Ok((index, arguments, target, loan, awaited));
        }
        let (index, arguments, receiver) = if node.kind == "appel méthode" {
            let base = node.children[0];
            let binding = *self.uses.get(&base)
                .ok_or_else(|| self.error(base, "liaison locale attendue comme receveur"))?;
            let layout = match self.live_slot(base, binding)?.ty {
                Ty::Struct(layout) | Ty::Ref { target: Referent::Aggregate(layout), .. } => layout,
                _ => return Err(self.error(base, "structure attendue comme receveur")),
            };
            let &(index, true) = self.methods.get(&(layout, self.name(id).unwrap()))
                .ok_or_else(|| self.error(id, "méthode inconnue"))? else {
                    return Err(self.error(id, "appel associé attendu"));
                };
            (index, node.children.as_slice(), Some(binding))
        } else {
            let index = self.function_index(id)
                .ok_or_else(|| self.error(id, "fonction inconnue ou appel indirect"))?;
            (index, &node.children[1..], None)
        };
        let signature = self.signatures[index].clone();
        if signature.entry {
            return Err(self.error(id, "main ne peut être appelé dans ce sous-ensemble"));
        }
        if arguments.len() != signature.parameters.len() {
            return Err(self.error(id, "nombre d’arguments incompatible"));
        }
        let start = self.pending.len();
        let inputs = arguments;
        let mut arguments = Vec::new();
        let preparation = (|| {
            for (position, (&argument, (_, ty))) in inputs.iter()
                .zip(signature.parameters.iter().copied()).enumerate()
            {
                let value = if let (Some(binding), Ty::Ref { mutable, .. }) =
                    (receiver.filter(|_| position == 0), ty)
                {
                    let slot = self.live_slot(argument, binding)?;
                    if matches!(slot.ty, Ty::Ref { .. }) {
                        self.reborrow(argument, binding, mutable, out)?
                    } else {
                        if mutable && !self.tree.bindings[binding.0].mutable {
                            return Err(self.error(argument, "receveur mutable attendu"));
                        }
                        self.access_target(argument, binding, mutable, false)?;
                        let mut value = self.emit(ty, Expr::Borrow(binding), out);
                        let mut origins = self.origins(slot.loan).to_vec();
                        origins.push(Origin {
                            root: binding, storage: true, pool: false, parent: None,
                            at: PathId::default(), from: PathId::default(), lock: PathId::default(),
                            opaque: false, capture_exclusive: false,
                        });
                        value.dependencies.loan = Some(self.intern(origins));
                        value.finish_evaluation(out)
                    }
                } else if let Ty::Ref { mutable, .. } = ty {
                    if let Some(&binding) = self.uses.get(&argument) {
                        self.reborrow(argument, binding, mutable, out)?
                    } else {
                        self.expression(argument, Some(ty), Access::Move, out)?
                    }
                } else {
                    self.expression(argument, Some(ty), Access::Move, out)?
                };
                if value.ty != ty {
                    return Err(self.error(argument, "type d’argument incompatible"));
                }
                if value.dependencies.loan.is_some() {
                    self.pending.push(value);
                }
                arguments.push(value);
            }
            Ok(())
        })();
        self.pending.truncate(start);
        preparation?;
        let (loan, awaited) = self.call_effects(id, index, &arguments)?;
        Ok((index, arguments, signature.result, loan, awaited))
    }

    fn call_effects(
        &mut self, id: NodeId, index: usize, arguments: &[Value],
    ) -> Result<(Option<LoanId>, Option<LoanId>), Error> {
        let signature = self.signatures[index].clone();
        let pop = self.field_pop_contracts[index]
            .zip(arguments.first().and_then(|argument| self.mutable_record_root(argument.ty, argument.dependencies.loan)))
            .and_then(|(field, root)| self.precise_field_pop(root, field).map(|len| (root, field, len)));
        let waits = self.call_waits(index);
        if !signature.asynchronous {
            for effect in self.call_entry_effects(index) {
                let source = arguments[effect.source];
                let path = self.dependencies.paths[effect.path.0].clone();
                let loan = self.selected_loan(source.dependencies.loan, &path);
                let target = arguments[effect.target].dependencies.loan;
                self.replace_entry_loan(id, target, loan, false)?;
                self.refresh_entry_reborrows(id, target, loan)?;
            }
        }
        for (parameter, path) in waits {
            if !signature.asynchronous {
                let mut handle = arguments[parameter];
                let path = self.dependencies.paths[path.0].clone();
                handle.dependencies.loan = self.selected_loan(handle.dependencies.loan, &path);
                self.complete_entry_effects(id, handle)?;
            }
        }
        let mut awaited = Vec::new();
        let loan = if self.has_dependencies(signature.result) {
            let mut origins = Vec::new();
            for dependency in self.contracts[index].clone() {
                let pool_parameter = matches!(
                    signature.parameters[dependency.parameter].1,
                    Ty::Ref {
                        target: Referent::Pool(_),
                        ..
                    }
                );
                let selector = self.dependencies.paths[dependency.from.0].clone();
                let prefix = self.dependencies.paths[dependency.at.0].clone();
                let arg = arguments[dependency.parameter];
                let (source, selector) =
                    if let Some(path) = selector.strip_prefix(&[Position::TaskOutput]) {
                        (arg.dependencies.awaited_loan, path)
                    } else {
                        (arg.dependencies.loan, selector.as_slice())
                    };
                let (destination, prefix) =
                    if let Some(path) = prefix.strip_prefix(&[Position::TaskOutput]) {
                        (&mut awaited, path)
                    } else {
                        (&mut origins, prefix.as_slice())
                    };
                let moved_handle = self.handle_origin(signature.result, prefix);
                let concrete_selector = match pop {
                    Some((_, field, 0)) if dependency.parameter == 0
                        && selector.starts_with(&[Position::Field(field), Position::Index(None)]) => continue,
                    Some((_, field, len)) if dependency.parameter == 0
                        && selector.starts_with(&[Position::Field(field), Position::Index(None)]) => {
                        let mut path = selector.to_vec();
                        path[1] = Position::Index(Some(len - 1));
                        path
                    }
                    _ => selector.to_vec(),
                };
                for mut origin in self.returned_argument_origins(arg.ty, source, &concrete_selector, moved_handle) {
                    if dependency.pool
                        || (matches!(signature.result, Ty::Allocation(_))
                            && (origin.pool || pool_parameter))
                    {
                        origin.pool = true;
                        origin.parent = None;
                    }
                    let mut path = prefix.to_vec();
                    if !dependency.opaque {
                        path.extend_from_slice(&self.dependencies.paths[origin.at.0]);
                    }
                    origin.opaque |= dependency.opaque;
                    origin.capture_exclusive |= dependency.capture_exclusive;
                    if dependency.lock != PathId::default() { origin.lock = dependency.lock; }
                    origin.at = self.path(path);
                    destination.push(origin);
                }
            }
            for mut effect in self.returned_entry_contracts[index].clone() {
                let path = self.dependencies.paths[effect.output.0].clone();
                if let Some(path) = path.strip_prefix(&[Position::TaskOutput]) {
                    effect.output = self.path(path.to_vec());
                    self.defer_entry_effects(id, &[effect], arguments, &mut awaited)?;
                } else {
                    self.defer_entry_effects(id, &[effect], arguments, &mut origins)?;
                }
            }
            if origins.is_empty() && matches!(signature.result, Ty::Ref { .. } | Ty::Allocation(_))
                && !(self.entry_contracts[index].is_none() && self.carries_handle(signature.result))
            {
                return Err(self.error(id, "provenance de l’appel emprunté inconnue"));
            }
            (!origins.is_empty()).then(|| self.intern(origins))
        } else {
            None
        };
        let awaited = (!awaited.is_empty()).then(|| self.intern(awaited));
        if let Some((root, field, len)) = pop {
            self.finish_field_pop(root, field, len);
        } else {
            for &argument in arguments {
                if let Some(root) = self.mutable_record_root(argument.ty, argument.dependencies.loan)
                    && let Some(slot) = &mut self.slots[root.0]
                {
                    slot.field_lengths = None;
                }
            }
        }
        Ok((loan, awaited))
    }

    // Both built-in envelopes have the success variant at tag 1.
    fn propagation_layout(&self, ty: Ty) -> Option<(usize, bool)> {
        let Ty::Struct(layout) = ty else { return None };
        if self.results.iter().any(|&(_, _, candidate)| candidate == layout)
            || self.native_results.iter().any(|&(_, candidate)| candidate == layout)
        {
            Some((layout, true))
        } else if self.options.iter().any(|&(_, candidate)| candidate == layout) {
            Some((layout, false))
        } else {
            None
        }
    }

    fn conversion(&self, source: Ty, destination: Ty) -> Option<usize> {
        let Ty::Struct(layout) = destination else { return None };
        self.conversions.get(&layout)?.iter().find_map(|&(input, index)| (input == source).then_some(index))
    }

    fn propagate(&mut self, id: NodeId, out: &mut Vec<Instr>) -> Result<Option<Value>, Error> {
        let operand = self.node(id).children[0];
        let subject = self.expression(operand, None, Access::Move, out)?;
        let (layout, is_result) = self.propagation_layout(subject.ty)
            .ok_or_else(|| self.error(id, "? exige une valeur Result ou Option"))?;
        let (result_layout, _) = self.propagation_layout(self.function_result)
            .filter(|&(_, result)| result == is_result)
            .ok_or_else(|| self.error(id, "? exige un retour de la même famille : Result ou Option"))?;
        let test = self.emit(Ty::Bool, Expr::IsVariant(subject, 0), out);

        let mut early = Vec::new();
        let success_slots = self.slots.clone();
        let success_waits = self.waited_parameters.len();
        let failure = if is_result {
            let inner = self.structures[layout].variants[0].1[0].1;
            let outer = self.structures[result_layout].variants[0].1[0].1;
            let error = self.take_propagation_payload(subject, 0, inner, &mut early);
            if inner == outer {
                Some(error)
            } else {
                let convert = self.conversion(inner, outer)
                    .ok_or_else(|| self.error(id, "? exige une fonction associée Outer::from(Inner) -> Outer"))?;
                let (loan, awaited_loan) = self.call_effects(id, convert, &[error])?;
                let mut converted = self.emit(outer, Expr::Call(convert, vec![error], CallKind::ErrorConversion), &mut early);
                converted.dependencies.loan = loan;
                converted.dependencies.awaited_loan = awaited_loan;
                Some(converted.finish_evaluation(&mut early))
            }
        } else {
            None
        };
        let returned = self.wrap_payload(self.function_result, 0, failure, &mut early);
        self.record_return(id, returned)?;
        self.check_thread_exit(id, |_| true)?;
        if self.pending.iter().any(|value| {
            self.dependent_handle(value.ty, value.dependencies.loan)
                || self.has_dependent_handle_output(value.ty, value.dependencies.awaited_loan)
        }) {
            return Err(self.error(id, "le handle à captures dépendantes doit être joint avant cette sortie"));
        }
        early.push(Instr::Return(Some(returned)));
        // A wait established on the continuing path alone cannot be promised to callers.
        if let Some(guaranteed) = &mut self.propagation_waits {
            guaranteed.retain(|wait| self.waited_parameters.contains(wait));
        } else {
            self.propagation_waits = Some(self.waited_parameters.clone());
        }
        self.slots = success_slots;
        self.waited_parameters.truncate(success_waits);
        out.push(Instr::If(test, early, Vec::new()));

        Ok(self.structures[layout].variants[1].1.first().map(|&(_, ty)| ty)
            .map(|ty| self.take_propagation_payload(subject, 1, ty, out)))
    }

    fn take_propagation_payload(
        &mut self, subject: Value, tag: usize, ty: Ty, out: &mut Vec<Instr>,
    ) -> Value {
        let extract = if matches!(ty, Ty::Struct(_) | Ty::Allocation(_) | Ty::Handle(..)) {
            Expr::TakeVariantField(subject, tag, 0)
        } else {
            Expr::VariantField(subject, tag, 0)
        };
        let mut value = self.emit(ty, extract, out);
        self.variant_payload_dependencies(subject, &[Position::Variant(tag), Position::Field(0)], &mut value);
        value.finish_evaluation(out)
    }

    fn variant_payload_dependencies(&mut self, subject: Value, selector: &[Position], value: &mut Value) {
        if !self.has_dependencies(value.ty) {
            return;
        }
        let mut origins = self.selected_origins(subject.dependencies.loan, selector);
        if let Ty::Handle(layout, _) = value.ty
            && self.has_dependencies(self.handle_output(layout))
        {
            for mut origin in origins.clone() {
                if !origin.storage && !origin.opaque && origin.at == PathId::default() {
                    let mut from = self.dependencies.paths[origin.from.0].clone();
                    from.push(Position::TaskOutput);
                    origin.from = self.path(from);
                    origin.at = self.path(vec![Position::TaskOutput]);
                    origins.push(origin);
                }
            }
        }
        self.unpack_output(value, origins);
    }

    fn wrap_payload(&mut self, ty: Ty, tag: usize, payload: Option<Value>, out: &mut Vec<Instr>) -> Value {
        let mut value = self.emit(ty, Expr::Variant(tag, payload.into_iter().map(|item| (0, item)).collect()), out);
        if let Some(payload) = payload {
            let mut origins = Vec::new();
            self.append_value_origins(&mut origins, payload, &[Position::Variant(tag), Position::Field(0)]);
            value.dependencies.loan = (!origins.is_empty()).then(|| self.intern(origins));
        }
        value.finish_evaluation(out)
    }

    fn value_arm(
        &mut self,
        id: NodeId,
        expected: Option<Ty>,
        out: &mut Vec<Instr>,
    ) -> Result<(bool, Option<Value>), Error> {
        if self.node(id).kind == "if" {
            return self
                .conditional_value(id, expected, out)
                .map(|value| (true, Some(value)));
        }
        let mut result = None;
        let mut continues = true;
        for &statement in &self.node(id).children {
            if !continues {
                break;
            }
            if self.region_scope(statement, out)? {
                continue;
            }
            let node = self.node(statement);
            if node.kind == "résultat" {
                result = Some(self.expression(node.children[0], expected, Access::Move, out)?);
                break;
            }
            continues = self.statement(statement, self.function_result, false, out)?;
        }
        self.check_thread_exit(id, |scope| self.tree.scopes[scope.0].syntax == id)?;
        for scope in self.tree.scopes.iter().filter(|scope| scope.syntax == id) {
            for binding in &scope.bindings {
                self.slots[binding.0] = None;
            }
        }
        if let Some(value) = result
            && self.origins(value.dependencies.loan).iter()
                .chain(self.origins(value.dependencies.awaited_loan)).any(|origin| {
                (self.slots[origin.root.0].is_none()
                    && !(!origin.storage
                        && self
                            .parameters
                            .iter()
                            .any(|&(binding, _)| binding == origin.root)))
                    || origin
                        .parent
                        .is_some_and(|parent| self.slots[parent.0].is_none()
                            && !(!origin.storage && self.parameters.iter().any(|&(binding, _)| binding == parent)))
            })
        {
            return Err(self.error(id, "la dépendance ne survit pas à la sortie du bloc"));
        }
        if continues && result.is_none() {
            return Err(self.error(id, "un chemin du bloc ne fournit pas de résultat"));
        }
        Ok((continues, result))
    }

    fn value_receiver(&mut self, id: NodeId, value: Value) -> Result<Value, Error> {
        if self.pool_layout(value.ty).is_some() {
            return Err(self.error(
                id,
                "un pool ou une allocation ne traverse pas cette frontière",
            ));
        }
        let receiver = Value {
            temp: self.next_temp,
            receiver: true,
            integer: None,
            provenance: ValueProvenance::Received(value.temp),
            ..value
        };
        self.next_temp += 1;
        Ok(receiver)
    }

    fn enum_match(
        &mut self,
        id: NodeId,
        result: Ty,
        expected: Option<Option<Ty>>,
        out: &mut Vec<Instr>,
    ) -> Result<(bool, Option<Value>), Error> {
        let node = self.node(id);
        let subject_node = self.node(node.children[0]);
        let explicit_borrow = subject_node.kind == "emprunt";
        let mutable_pool = explicit_borrow && self.text(subject_node.start + 1) == "mut";
        let pool_handle = explicit_borrow
            .then(|| self.uses.get(&subject_node.children[0]).copied())
            .flatten()
            .filter(|binding| {
                self.slots[binding.0].is_some_and(|slot| matches!(slot.ty, Ty::Allocation(_)))
            });
        let borrowed_binding = self.uses.get(&node.children[0]).copied().filter(|binding| {
            self.slots[binding.0].is_some_and(|slot| matches!(slot.ty, Ty::Ref { .. }))
        });
        let subject = if let Some(binding) = pool_handle {
            if mutable_pool && !self.tree.bindings[binding.0].mutable {
                return Err(self.error(id, "match mutable d’une allocation immuable"));
            }
            self.access_target(id, binding, mutable_pool, false)?;
            self.local(node.children[0], binding, Access::Read, out)?
        } else if let Some(binding) = borrowed_binding {
            self.reborrow(node.children[0], binding, false, out)?
        } else {
            self.expression(node.children[0], None, Access::Move, out)?
        };
        let (nominal, borrowed) = match subject.ty {
            Ty::Allocation(element) if pool_handle.is_some() => (element.ty(), Some(mutable_pool)),
            Ty::Ref {
                target: Referent::Aggregate(layout),
                mutable,
            } => (Ty::Struct(layout), Some(mutable)),
            ty => (ty, None),
        };
        let Ty::Struct(layout) = nominal else {
            return Err(self.error(id, "enum attendu pour match"));
        };
        if borrowed.is_none() && inline_destructor(subject.ty, &self.structures)
            && !self.results.iter().any(|&(_, _, index)| index == layout)
            && !self.native_results.iter().any(|&(_, index)| index == layout)
        {
            return Err(self.error(id, "match par valeur sur un type à destructeur personnalisé hors périmètre"));
        }
        let variants = self.structures[layout].variants.clone();
        if variants.is_empty() {
            return Err(self.error(id, "enum attendu pour match"));
        }
        if variants.len() == 1 {
            // A unit arm needs no tag load, but evaluating the subject still has effects.
            out.push(Instr::Discard(subject));
        }
        // A directly matched pop is the last operation on this vector.
        // Its None edge proves that no indexed dependencies remain.
        let popped_vector = out.last().and_then(|instruction| match instruction {
            Instr::Evaluate(value, Expr::VectorExtract(vector, None, _)) if value.temp == subject.temp => {
                match vector.provenance {
                    ValueProvenance::LocalRead(binding) => Some(binding),
                    _ => None,
                }
            }
            _ => None,
        });
        let before = self.slots.clone();
        let mut seen = vec![false; variants.len()];
        let mut arms = Vec::new();
        let mut continuing = Vec::new();
        let mut result_type = expected.flatten();
        for &arm in &node.children[1..] {
            self.slots.clone_from(&before);
            let pattern = self.node(arm).children[0];
            let block = self.node(arm).children[1];
            let option_pattern = self.options.iter().any(|&(_, index)| index == layout);
            let result_pattern = self
                .native_results
                .iter()
                .any(|&(_, index)| index == layout)
                || self.results.iter().any(|&(_, _, index)| index == layout);
            let positional_pattern = self.node(pattern).kind == "motif variante positionnelle";
            let tuple_pattern = option_pattern || result_pattern || positional_pattern;
            let (nominal, tag) = if result_pattern {
                match self.name(pattern) {
                    Some("Err") if self.node(pattern).children.len() == 1 => (layout, 0),
                    Some("Ok") if self.node(pattern).children.len() == 1 => (layout, 1),
                    _ => return Err(self.error(pattern, "motif Ok ou Err attendu")),
                }
            } else if option_pattern {
                match self.name(pattern) {
                    Some("None") if self.node(pattern).children.is_empty() => (layout, 0),
                    Some("Some") if self.node(pattern).children.len() == 1 => (layout, 1),
                    _ => return Err(self.error(pattern, "motif Some ou None attendu")),
                }
            } else {
                self.variant(pattern)
                    .ok_or_else(|| self.error(pattern, "motif de variante attendu"))?
            };
            if nominal != layout || seen[tag] {
                return Err(self.error(pattern, "variante incompatible ou répétée"));
            }
            seen[tag] = true;
            if option_pattern && tag == 0 && let Some(binding) = popped_vector {
                let slot = self.live_slot(pattern, binding)?;
                let origins = self.origins(slot.loan).iter().copied().filter(|origin| {
                    !matches!(self.dependencies.paths[origin.at.0].first(), Some(Position::Index(_)))
                }).collect::<Vec<_>>();
                self.slots[binding.0] = Some(Slot {
                    vector_len: Some(0),
                    loan: (!origins.is_empty()).then(|| self.intern(origins)),
                    ..slot
                });
            }
            let fields = &variants[tag].1;
            if !option_pattern && !result_pattern
                && (positional_pattern != Self::positional_fields(fields)
                    || positional_pattern && self.node(pattern).children.len() != fields.len())
            {
                return Err(self.error(pattern, "motif incompatible avec les champs positionnels de la variante"));
            }
            let mut arm_body = Vec::new();
            let mut bound_fields = std::collections::BTreeSet::new();
            let mut bound_owner = false;
            let mut moved_fields = std::collections::BTreeSet::new();
            for (position, &field) in self.node(pattern).children.iter().enumerate() {
                if result_pattern && fields.is_empty() {
                    if self.node(field).kind == "motif unité" || self.name(field) == Some("_") {
                        continue;
                    }
                    return Err(self.error(field, "motif unité attendu"));
                }
                let (index, ty) = if tuple_pattern {
                    (position, fields[position].1)
                } else {
                    fields
                        .iter()
                        .enumerate()
                        .find_map(|(index, (name, ty))| {
                            (Some(name.as_str()) == self.name(field)).then_some((index, *ty))
                        })
                        .ok_or_else(|| self.error(field, "champ inconnu dans le motif"))?
                };
                if !bound_fields.insert(index) {
                    return Err(self.error(field, "champ de motif répété"));
                }
                let binder = if tuple_pattern {
                    field
                } else {
                    self.node(field).children[0]
                };
                if self.name(binder) == Some("_") {
                    continue;
                }
                let binding = *self
                    .bindings
                    .get(&binder)
                    .ok_or_else(|| self.error(binder, "liaison du champ attendue"))?;
                let selector = [Position::Variant(tag), Position::Field(index)];
                let borrow_field = matches!(ty, Ty::Struct(_)) && borrowed.is_some()
                    || borrowed == Some(true) && ty.scalar().is_some();
                let expression = match (pool_handle.is_some(), borrow_field) {
                    (true, true) => Expr::BorrowPoolVariantField(subject, layout, tag, index),
                    (true, false) => Expr::PoolVariantField(subject, layout, tag, index),
                    (false, true) => Expr::BorrowVariantField(subject, tag, index),
                    (false, false)
                        if matches!(ty, Ty::Struct(_)) && (result_pattern || option_pattern || contains_handle(ty, &self.structures)) =>
                    {
                        Expr::TakeVariantField(subject, tag, index)
                    }
                    (false, false) => Expr::VariantField(subject, tag, index),
                };
                if borrowed.is_some() && contains_handle(ty, &self.structures) && !borrow_field {
                    return Err(self.error(field, "déplacement de handle depuis un agrégat emprunté"));
                }
                let ty = if borrow_field {
                    Ty::Ref {
                        target: ty.referent().unwrap(),
                        mutable: borrowed.unwrap(),
                    }
                } else {
                    if !((option_pattern || result_pattern || matches!(ty, Ty::Handle(..)) || contains_handle(ty, &self.structures)) && borrowed.is_none())
                        && !matches!(ty, Ty::Ref { mutable: false, .. })
                        && ty.scalar().is_none()
                    {
                        return Err(self.error(field, "ce champ exige un motif emprunté"));
                    }
                    ty
                };
                let mut value = self.emit(ty, expression, &mut arm_body);
                if borrow_field {
                    let mut origins = self.selected_origins(subject.dependencies.loan, &selector);
                    if let Some(root) = pool_handle {
                        origins.push(Origin {
                            root,
                            storage: true,
                            pool: false,
                            parent: None,
                            at: PathId::default(),
                            from: PathId::default(),
                            lock: PathId::default(),
                            opaque: false,
                            capture_exclusive: false,
                        });
                    }
                    value.dependencies.loan = (!origins.is_empty()).then(|| self.intern(origins));
                } else {
                    self.variant_payload_dependencies(subject, &selector, &mut value);
                }
                let value = value.finish_evaluation(&mut arm_body);
                if owns_resources(value.ty, &self.structures) {
                    bound_owner = true;
                    moved_fields.insert(index);
                }
                self.bind_value(binder, binding, value)?;
                arm_body.push(Instr::Bind(binding, value));
            }
            if borrowed.is_none() && contains_handle(subject.ty, &self.structures) {
                for (field, (_, ty)) in fields.iter().enumerate() {
                    if !contains_handle(*ty, &self.structures) || moved_fields.contains(&field) {
                        continue;
                    }
                    let loan = self.selected_loan(subject.dependencies.loan, &[Position::Variant(tag), Position::Field(field)]);
                    if self.dependent_handle(*ty, loan) {
                        return Err(self.error(pattern, "un handle à captures dépendantes ne peut pas être abandonné"));
                    }
                }
            }
            if borrowed.is_none() && !bound_owner && owns_resources(subject.ty, &self.structures) {
                arm_body.push(Instr::DropOwned(subject));
            }
            let (continues, value) = if expected.is_some() {
                self.value_arm(block, result_type, &mut arm_body)?
            } else {
                (self.block(block, result, false, &mut arm_body)?, None)
            };
            if let Some(value) = value {
                result_type = Some(value.ty);
            }
            if continues {
                continuing.push(self.slots.clone());
            }
            arms.push((tag, arm_body, value));
        }
        if seen.contains(&false) {
            return Err(self.error(id, "match non exhaustif"));
        }
        self.slots = self
            .merge_slots(&before, continuing.iter())
            .unwrap_or(before);
        let receiver = if expected.is_some() {
            let value = arms
                .iter()
                .find_map(|(_, _, value)| *value)
                .ok_or_else(|| self.error(id, "aucun bras ne fournit de résultat"))?;
            let mut receiver = self.value_receiver(id, value)?;
            receiver.provenance = ValueProvenance::Merged;
            receiver.dependencies =
                self.merge_dependencies(arms.iter().filter_map(|(_, _, value)| *value));
            out.push(Instr::Reserve(receiver));
            Some(receiver)
        } else {
            None
        };
        let mut alternative = Vec::new();
        for (tag, mut arm, value) in arms.into_iter().rev() {
            if let (Some(receiver), Some(value)) = (receiver, value) {
                arm.push(Instr::Receive(receiver, value));
            }
            if alternative.is_empty() {
                alternative.push(Instr::Block(arm));
            } else {
                let mut branch = Vec::new();
                let test = self.emit(Ty::Bool, Expr::IsVariant(subject, tag), &mut branch);
                branch.push(Instr::If(test, arm, alternative));
                alternative = branch;
            }
        }
        out.extend(alternative);
        Ok((!continuing.is_empty(), receiver))
    }

    fn finish_scalar_binary(
        &mut self, id: NodeId, rhs: NodeId, operator: &str, left: Value, right: Value,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let comparison = matches!(operator, "==" | "!=" | "<" | ">" | "<=" | ">=");
        if matches!(operator, "&" | "|" | "^") && !(left.ty.signed() || left.ty.unsigned()) {
            return Err(self.error(id, "opération bit à bit exige des entiers"));
        }
        if left.ty.scalar().is_none()
            || left.ty == Ty::Bool && !matches!(operator, "==" | "!=")
        {
            return Err(self.error(id, "opérande entier requis"));
        }
        let ty = if comparison { Ty::Bool } else { left.ty };
        if matches!(operator, "/" | "%")
            && (right.integer == Some(0)
                || (right.ty.float() && self.float_zero(rhs)))
        {
            return Err(self.error(id, "division par zéro"));
        }
        if !comparison && let (Some(lhs), Some(rhs)) = (left.integer, right.integer) {
            if operator == "/"
                && lhs
                    == match left.ty {
                        Ty::I32 => i32::MIN as i128,
                        Ty::I64 => i64::MIN as i128,
                        _ => i128::MIN,
                    }
                && rhs == -1
            {
                return Err(self.error(id, "division hors limites"));
            }
            let number = match operator {
                "+" => lhs.checked_add(rhs),
                "-" => lhs.checked_sub(rhs),
                "*" => lhs.checked_mul(rhs),
                "/" => lhs.checked_div(rhs),
                "%" => lhs.checked_rem(rhs),
                "&" => Some(lhs & rhs),
                "|" => Some(lhs | rhs),
                "^" => Some(lhs ^ rhs),
                _ => unreachable!(),
            }
            .ok_or_else(|| self.error(id, "résultat entier hors limites"))?;
            out.push(Instr::Discard(left));
            out.push(Instr::Discard(right));
            return self.checked_integer(id, ty, number, out);
        }
        let mut value = self.emit(ty, Expr::Binary(operator.to_owned(), left, right), out);
        if ty == Ty::Usize {
            value.dependencies.loan = self.union_loans(
                [left.dependencies.loan, right.dependencies.loan].into_iter(),
            );
            value = value.finish_evaluation(out);
        }
        Ok(value)
    }

    fn compound_assignment(
        &mut self, id: NodeId, place: NodeId, rhs: NodeId, out: &mut Vec<Instr>,
    ) -> Result<(), Error> {
        let operator = match self.name(id) {
            Some(">") => ">>",
            Some(op) => op.strip_suffix('=').unwrap(),
            None => unreachable!(),
        };
        let shift = matches!(operator, "<<" | ">>");
        let mut root = place;
        while matches!(self.node(root).kind, "indice" | "projection" | "groupe") {
            root = self.node(root).children[0];
        }
        let borrowed = self.node(root).kind == "indirection";
        let mut name = root;
        while self.node(name).kind == "indirection" {
            name = self.node(name).children[0];
        }
        let binding = *self.uses.get(&name)
            .ok_or_else(|| self.error(place, "place locale requise"))?;
        let slot = self.live_slot(place, binding)?;
        let via_slice = !borrowed && matches!(slot.ty, Ty::Slice { .. });
        if borrowed || via_slice {
            if !matches!(slot.ty, Ty::Ref { mutable: true, .. } | Ty::Slice { mutable: true, .. }) {
                return Err(self.error(place, "écriture par une référence partagée"));
            }
        } else if !self.tree.bindings[binding.0].mutable {
            return Err(self.error(place, "affectation à une liaison immuable"));
        }

        let local = self.node(place).kind == "nom";
        let address = if local {
            None
        } else if place == root && borrowed {
            if self.node(self.node(place).children[0]).kind == "indirection" {
                let inner = self.expression(self.node(place).children[0], None, Access::Read, out)?;
                let Ty::Ref { target, mutable: true } = inner.ty else {
                    return Err(self.error(place, "écriture exige deux références mutables"));
                };
                let mut address = self.emit(Ty::Ref { target, mutable: false }, Expr::Temporary(inner), out);
                address.dependencies.loan = inner.dependencies.loan;
                Some(address.finish_evaluation(out))
            } else {
                self.dereference(place, false)?;
                Some(self.reborrow(place, binding, false, out)?)
            }
        } else if matches!(self.node(place).kind, "projection" | "indice") {
            Some(self.borrow_projection(place, false, true, out)?)
        } else {
            return Err(self.error(place, "place modifiable requise"));
        };
        let target = if let Some(address) = address {
            let Ty::Ref { target, .. } = address.ty else { unreachable!() };
            target
        } else {
            slot.ty.scalar().ok_or_else(|| self.error(place, "place scalaire requise"))?
        };
        let ty = target.ty();
        if ty.scalar().is_none() || ty == Ty::Bool {
            return Err(self.error(place, "place numérique requise"));
        }
        let left = if let Some(address) = address {
            let mut left = self.emit(ty, Expr::DereferenceValue(address), out);
            if ty == Ty::Usize {
                left.dependencies.loan = address.dependencies.loan;
            }
            left.finish_evaluation(out)
        } else {
            self.local(place, binding, Access::Read, out)?
        };

        // A shared reservation permits reads while preventing mutations and moves.
        let mut origins = self.origins(address.and_then(|address| address.dependencies.loan)).to_vec();
        let lock = origins.iter().find(|origin| {
            if borrowed || via_slice { origin.parent == Some(binding) }
            else { origin.root == binding && origin.storage }
        }).map_or(PathId::default(), |origin| origin.lock);
        if local || borrowed || via_slice {
            origins.push(Origin {
                root: binding, storage: true, pool: false, parent: None,
                at: PathId::default(), from: PathId::default(), lock: PathId::default(),
                opaque: false, capture_exclusive: false,
            });
        }
        let pending = self.pending.len();
        let loan = Some(self.intern(origins));
        self.pending.push(Value {
            ty: Ty::Ref { target, mutable: false },
            dependencies: DependencySummary { loan, ..DependencySummary::default() },
            ..left
        });
        let right = self.expression(rhs, (!shift).then_some(ty), Access::Read, out);
        self.pending.truncate(pending);
        let right = right?;
        if borrowed || via_slice {
            self.access_target(id, binding, false, false)?;
        }
        self.access_projected_at(id, binding, borrowed || via_slice, true, true, &self.dependencies.paths[lock.0])?;
        let value = if shift {
            self.finish_shift(id, rhs, operator == "<<", left, right, out)?
        } else {
            self.finish_scalar_binary(id, rhs, operator, left, right, out)?
        };
        if let Some(address) = address {
            if value.ty == Ty::Usize && value.dependencies.loan.is_some() {
                return Err(self.error(id, "écriture indirecte d’une adresse suivie hors périmètre"));
            }
            out.push(Instr::WriteSliceElement(address, value));
        } else {
            self.bind_value(id, binding, value)?;
            out.push(Instr::Write(binding, value));
        }
        Ok(())
    }

    fn shift(&mut self, id: NodeId, expected: Option<Ty>, out: &mut Vec<Instr>) -> Result<Value, Error> {
        let leftward = self.operator(id) == "<<";
        let children = &self.node(id).children;
        let left = self.expression(children[0], expected, Access::Read, out)?;
        let pending = self.pending.len();
        self.pending.push(left);
        let right = self.expression(children[1], None, Access::Read, out);
        self.pending.truncate(pending);
        self.finish_shift(id, children[1], leftward, left, right?, out)
    }

    fn finish_shift(
        &mut self, id: NodeId, rhs: NodeId, leftward: bool, left: Value, right: Value,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let bits = left.ty.integer_bits(self.tree.target.pointer_width())
            .ok_or_else(|| self.error(id, "le décalage exige des entiers"))?;
        if !(right.ty.signed() || right.ty.unsigned()) {
            return Err(self.error(id, "le décalage exige un nombre entier de positions"));
        }
        if right.integer.is_some_and(|n| !(0..i128::from(bits)).contains(&n)) {
            return Err(self.error(rhs, "nombre de positions de décalage hors limites"));
        }
        if let (Some(value), Some(count)) = (left.integer, right.integer) {
            out.push(Instr::Discard(left));
            out.push(Instr::Discard(right));
            let result = if leftward { value * (1_i128 << count) } else { value >> count };
            return self.checked_integer(id, left.ty, result, out);
        }

        let mut value = self.emit(left.ty, Expr::Shift(left, right, bits, leftward), out);
        if left.ty == Ty::Usize || !leftward {
            value.dependencies.loan = self.union_loans(
                [left.dependencies.loan, right.dependencies.loan].into_iter(),
            );
        }
        Ok(value.finish_evaluation(out))
    }

    fn short_circuit(&mut self, id: NodeId, out: &mut Vec<Instr>) -> Result<Value, Error> {
        let children = &self.node(id).children;
        let is_or = self.operator(id) == "||";
        let left = self.expression(children[0], Some(Ty::Bool), Access::Read, out)?;
        let before = self.slots.clone();
        let waited_before = self.waited_parameters.len();
        let mut evaluate = Vec::new();
        let right = self.expression(children[1], Some(Ty::Bool), Access::Read, &mut evaluate)?;
        // The skipped path cannot establish a wait for the caller.
        self.waited_parameters.truncate(waited_before);
        let after = std::mem::replace(&mut self.slots, before.clone());
        self.slots = self.merge_slots(&before, [&before, &after]).unwrap();
        let mut receiver = self.value_receiver(id, left)?;
        receiver.provenance = ValueProvenance::Merged;
        evaluate.push(Instr::Receive(receiver, right));
        let mut skip = Vec::new();
        let skipped = self.emit(Ty::Bool, Expr::Boolean(is_or), &mut skip);
        skip.push(Instr::Receive(receiver, skipped));
        let (yes, no) = if is_or { (skip, evaluate) } else { (evaluate, skip) };
        out.push(Instr::Reserve(receiver));
        out.push(Instr::If(left, yes, no));
        Ok(receiver)
    }

    fn conditional_value(
        &mut self,
        id: NodeId,
        expected: Option<Ty>,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let node = self.node(id);
        let alternative = *node
            .children
            .get(2)
            .ok_or_else(|| self.error(id, "un if à résultat exige else"))?;
        let condition = self.expression(node.children[0], Some(Ty::Bool), Access::Read, out)?;
        let before = self.slots.clone();
        let mut yes = Vec::new();
        let (yes_continues, yes_result) = self.value_arm(node.children[1], expected, &mut yes)?;
        let yes_slots = std::mem::replace(&mut self.slots, before.clone());
        let mut no = Vec::new();
        let (no_continues, no_result) = self.value_arm(
            alternative,
            expected.or(yes_result.map(|value| value.ty)),
            &mut no,
        )?;
        let value = yes_result
            .or(no_result)
            .ok_or_else(|| self.error(id, "aucun bras ne fournit de résultat"))?;
        let mut receiver = self.value_receiver(id, value)?;
        receiver.provenance = ValueProvenance::Merged;
        receiver.dependencies = self.merge_dependencies(yes_result.into_iter().chain(no_result));
        if let Some(value) = yes_result {
            yes.push(Instr::Receive(receiver, value));
        }
        if let Some(value) = no_result {
            no.push(Instr::Receive(receiver, value));
        }
        let no_slots = self.slots.clone();
        let paths = [
            yes_continues.then_some(&yes_slots),
            no_continues.then_some(&no_slots),
        ];
        self.slots = self
            .merge_slots(&before, paths.into_iter().flatten())
            .unwrap_or(before);
        out.push(Instr::Reserve(receiver));
        out.push(Instr::If(condition, yes, no));
        Ok(receiver)
    }

    fn variant(&self, id: NodeId) -> Option<(usize, usize)> {
        let node = self.node(id);
        let (layout, name) = if self.text(node.start) == "runtime"
            && self.text(node.start + 2) == "Error"
            && self.text(node.start + 3) == "."
        {
            (self.native_error?, self.text(node.start + 4))
        } else {
            if self.text(node.start + 1) != "." {
                return None;
            }
            (
                *self.structure_names.get(self.text(node.start))?,
                self.text(node.start + 2),
            )
        };
        let tag = self.structures[layout]
            .variants
            .iter()
            .position(|(candidate, _)| candidate == name)?;
        Some((layout, tag))
    }

    fn positional_fields(fields: &[(String, Ty)]) -> bool {
        fields.first().is_some_and(|(name, _)| name == "0")
    }

    fn variant_call(&self, id: NodeId) -> Option<(usize, usize)> {
        let node = self.node(id);
        if node.kind != "appel méthode"
            || self.node(node.children[0]).kind != "nom"
            || self.uses.contains_key(&node.children[0])
        {
            return None;
        }
        self.variant(id)
    }

    fn construct_variant_unit(&mut self, id: NodeId, out: &mut Vec<Instr>) -> Result<Value, Error> {
        let (layout, tag) = self.variant(id).unwrap();
        if !self.structures[layout].variants[tag].1.is_empty() {
            return Err(self.error(id, "champs de variante requis"));
        }
        Ok(self.emit(Ty::Struct(layout), Expr::Variant(tag, vec![]), out))
    }

    fn construct(&mut self, id: NodeId, out: &mut Vec<Instr>) -> Result<Value, Error> {
        let variant = self.variant(id);
        let index = variant
            .map(|(index, _)| index)
            .or_else(|| {
                self.name(id)
                    .and_then(|name| self.structure_names.get(name))
                    .copied()
                    .filter(|&index| self.structures[index].variants.is_empty())
            })
            .ok_or_else(|| self.error(id, "construction de type fixe attendue"))?;
        self.construct_fields(id, index, variant, &self.node(id).children, false, out)
    }

    fn default_value(&mut self, id: NodeId, ty: Ty, out: &mut Vec<Instr>) -> Result<Value, Error> {
        let expression = match ty {
            Ty::Bool => Expr::Boolean(false),
            ty if ty.signed() || ty.unsigned() => Expr::Integer(0),
            Ty::F32 => Expr::Float("0.0f".into()),
            Ty::F64 => Expr::Float("0.0".into()),
            Ty::Struct(index) if self.structures[index].variants.is_empty()
                && self.structures[index].array.is_none()
                && self.structures[index].pool.is_none()
                && self.structures[index].growing.is_none() =>
                return self.construct_fields(id, index, None, &[], true, out),
            _ => return Err(self.error(id, "initialiseur explicite requis pour ce type")),
        };
        Ok(self.emit(ty, expression, out))
    }

    fn check_fields_visible(&self, id: NodeId, layout: usize) -> Result<(), Error> {
        let offset = self.tree.tokens[self.node(id).start].span.start;
        if self.structure_names.get("__crust_package_opaque_file") == Some(&layout)
            && !self.tree.std_file_range.contains(&offset)
        {
            return Err(self.error(id, "représentation privée de std::io::File"));
        }
        for (name, (range, diagnostic)) in &self.tree.opaque_layouts {
            if self.structure_names.get(name.as_str()) == Some(&layout) && !range.contains(&offset) {
                return Err(self.error(id, diagnostic));
            }
        }
        Ok(())
    }

    fn construct_fields(
        &mut self, id: NodeId, index: usize, variant: Option<(usize, usize)>,
        inputs: &[NodeId], defaults: bool, out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        self.check_fields_visible(id, index)?;
        let fields = variant
            .map_or(&self.structures[index].fields, |(_, tag)| {
                &self.structures[index].variants[tag].1
            })
            .clone();
        let positional = self.variant_call(id).is_some();
        if variant.is_some()
            && (positional != Self::positional_fields(&fields)
                || positional && inputs.len() != fields.len())
        {
            return Err(self.error(id, "construction incompatible avec les champs positionnels de la variante"));
        }
        let mut initializers = Vec::new();
        let pending = self.pending.len();
        for (position, &field) in inputs.iter().enumerate() {
            let node = self.node(field);
            if variant.is_some() && node.kind == "nom" {
                continue;
            }
            let (position, ty, input) = if positional {
                (position, fields[position].1, field)
            } else {
                if node.kind != "champ" {
                    return Err(self.error(id, "initialiseur de champ attendu"));
                }
                fields.iter().enumerate()
                    .find_map(|(position, (name, ty))| {
                        (Some(name.as_str()) == self.name(field))
                            .then_some((position, *ty, node.children[0]))
                    })
                    .ok_or_else(|| self.error(field, "champ inconnu"))?
            };
            if initializers.iter().any(|(index, _)| *index == position) {
                return Err(self.error(field, "champ initialisé plusieurs fois"));
            }
            let value = self.expression(input, Some(ty), Access::Move, out)?;
            if value.dependencies.loan.is_some() {
                self.pending.push(value);
            }
            initializers.push((position, value));
        }
        if defaults {
            for (position, (_, ty)) in fields.iter().enumerate() {
                if !initializers.iter().any(|(index, _)| *index == position) {
                    initializers.push((position, self.default_value(id, *ty, out)?));
                }
            }
        }
        self.pending.truncate(pending);
        if initializers.len() != fields.len() {
            return Err(self.error(id, "initialisation partielle"));
        }
        let expression = match variant {
            Some((_, tag)) => Expr::Variant(tag, initializers),
            None => Expr::Construct(initializers),
        };
        let fields = match &expression {
            Expr::Construct(fields) | Expr::Variant(_, fields) => fields,
            _ => unreachable!(),
        };
        let mut origins = Vec::new();
        let mut lengths = Vec::new();
        for &(field, value) in fields {
            let mut prefix = Vec::new();
            if let Some((_, tag)) = variant {
                prefix.push(Position::Variant(tag));
            }
            prefix.push(Position::Field(field));
            self.append_value_origins(&mut origins, value, &prefix);
            if variant.is_none() && let Some(len) = value.dependencies.vector_len {
                lengths.push((field, len));
            }
        }
        let loan = (!origins.is_empty()).then(|| self.intern(origins));
        let mut value = self.emit(Ty::Struct(index), expression, out);
        value.dependencies.loan = loan;
        value.dependencies.field_lengths = self.intern_field_lengths(lengths);
        value = value.finish_evaluation(out);
        Ok(value)
    }

    fn tuple_fields(&self, ty: Ty) -> Option<&[(String, Ty)]> {
        let Ty::Struct(index) = ty else { return None };
        let fields = &self.structures[index].fields;
        fields.first().is_some_and(|(name, _)| name == "0").then_some(fields)
    }

    fn tuple_type(&mut self, id: NodeId, types: Vec<Ty>) -> Result<Ty, Error> {
        if types.iter().any(|&ty| matches!(ty, Ty::Void | Ty::Pool(_) | Ty::Future(_))
            || self.pool_layout(ty).is_some() || self.growing_layout(ty).is_some())
        {
            return Err(self.error(id, "unsupported inline tuple element"));
        }
        let fields = types.into_iter().enumerate()
            .map(|(position, ty)| (position.to_string(), ty)).collect::<Vec<_>>();
        let index = self.structures.iter().position(|layout| layout.fields == fields)
            .unwrap_or_else(|| {
                let index = self.structures.len();
                self.structures.push(Structure {
                    fields, array: None, pool: None, variants: vec![], growing: None, destructor: None,
                });
                index
            });
        Ok(Ty::Struct(index))
    }

    fn tuple(&mut self, id: NodeId, expected: Option<Ty>, out: &mut Vec<Instr>) -> Result<Value, Error> {
        let elements = self.node(id).children.clone();
        let expected_fields = expected.map(|ty| {
            self.tuple_fields(ty).filter(|fields| fields.len() == elements.len())
                .ok_or_else(|| self.error(id, "tuple type or arity mismatch")).map(<[_]>::to_vec)
        }).transpose()?;
        let pending = self.pending.len();
        let result = (|| {
            let mut values = Vec::new();
            let mut origins = Vec::new();
            for (position, element) in elements.into_iter().enumerate() {
                let expected = expected_fields.as_ref().map(|fields| fields[position].1);
                let value = self.expression(element, expected, Access::Move, out)?;
                self.append_value_origins(&mut origins, value, &[Position::Field(position)]);
                self.pending.push(value);
                values.push((position, value));
            }
            let ty = self.tuple_type(id, values.iter().map(|(_, value)| value.ty).collect())?;
            let mut value = self.emit(ty, Expr::Construct(values), out);
            value.dependencies.loan = (!origins.is_empty()).then(|| self.intern(origins));
            Ok(value.finish_evaluation(out))
        })();
        self.pending.truncate(pending);
        result
    }

    fn array_layout(&self, id: NodeId, ty: Ty) -> Result<(Ty, usize), Error> {
        if let Ty::Struct(layout) = ty
            && let Some(array) = self.structures[layout].array
        {
            return Ok(array);
        }
        Err(self.error(id, "tableau fixe attendu"))
    }

    fn array_index(
        &mut self,
        id: NodeId,
        length: usize,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let index = self.expression(id, None, Access::Read, out)?;
        if !(index.ty.signed() || index.ty.unsigned()) {
            return Err(self.error(id, "indice entier attendu"));
        }
        if index
            .integer
            .is_some_and(|value| value < 0 || value >= length as i128)
        {
            return Err(self.error(id, "indice hors du tableau"));
        }
        out.push(Instr::CheckIndex(index, length));
        Ok(index)
    }

    fn index_after_owner(
        &mut self,
        id: NodeId,
        length: usize,
        owner: Value,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let pending = self.pending.len();
        if owner.dependencies.loan.is_some() {
            self.pending.push(owner);
        }
        let index = self.array_index(id, length, out);
        self.pending.truncate(pending);
        index
    }

    fn array(
        &mut self,
        id: NodeId,
        expected: Option<Ty>,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let node = self.node(id);
        let repeat = node.kind == "tableau répété";
        let length = if repeat {
            self.length(node.children[1])?
        } else {
            node.children.len()
        };
        let expected_array = expected.and_then(|ty| match ty {
            Ty::Struct(index) => self.structures[index].array,
            _ => None,
        });
        if expected_array.is_some_and(|(_, count)| count != length) {
            return Err(self.error(id, "longueur de tableau incompatible"));
        }
        let inputs = if repeat {
            &node.children[..1]
        } else {
            &node.children[..]
        };
        let mut element = expected_array
            .map(|(ty, _)| ty)
            .or_else(|| inputs.iter().find_map(|&input| self.known_type(input)));
        let mut values = Vec::new();
        let pending = self.pending.len();
        for &input in inputs {
            let value = self.expression(input, element, Access::Move, out)?;
            element = Some(value.ty);
            if value.dependencies.loan.is_some() {
                self.pending.push(value);
            }
            values.push(value);
        }
        self.pending.truncate(pending);
        let element =
            element.ok_or_else(|| self.error(id, "type d’élément requis pour le tableau vide"))?;
        if repeat
            && (length > 1 && !structurally_replicable(element, &self.structures)
                || length == 0 && owns_resources(element, &self.structures))
        {
            return Err(self.error(id, "répétition exige une valeur réplicable"));
        }
        let ty = self.array_type(id, element, length)?;
        if repeat && length == 0 {
            out.push(Instr::Discard(values.remove(0)));
        }
        let mut origins = Vec::new();
        for (index, value) in values.iter().enumerate() {
            self.append_value_origins(
                &mut origins, *value, &[Position::Index((!repeat).then_some(index))],
            );
        }
        let loan = (!origins.is_empty()).then(|| self.intern(origins));
        let mut value = self.emit(ty, Expr::Array(values, repeat && length > 1), out);
        value.dependencies.loan = loan;
        value = value.finish_evaluation(out);
        Ok(value)
    }

    // Evaluate one projection chain without reading the entire aggregate. The
    // index expressions still use the ordinary verifier and run left to right.
    fn stored_place(
        &mut self,
        id: NodeId,
        root: NodeId,
        base: Value,
        path: &mut Vec<Position>,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        if id == root {
            return Ok(base);
        }
        let node = self.node(id);
        let owner = self.stored_place(node.children[0], root, base, path, out)?;
        let (ty, expression, position) = match node.kind {
            "groupe" => return Ok(owner),
            "indice" => {
                if let Ty::Allocation(content) = owner.ty
                    && let Some(Growing::Vector(element)) = self.growing_layout(content.ty())
                {
                    let index = self.expression(node.children[1], None, Access::Read, out)?;
                    if !(index.ty.signed() || index.ty.unsigned()) {
                        return Err(self.error(id, "indice entier attendu"));
                    }
                    if let Some(&binding) = self.uses.get(&root) {
                        self.live_slot(id, binding)?;
                    }
                    path.push(Position::Index(
                        index.integer.and_then(|i| usize::try_from(i).ok()),
                    ));
                    let mut value = self.emit(element, Expr::GrowingIndex(owner, index), out);
                    if self.has_dependencies(element) {
                        value.dependencies.loan = self.selected_loan(owner.dependencies.loan, &[*path.last().unwrap()]);
                        value = value.finish_evaluation(out);
                    }
                    return Ok(value);
                }
                let (element, length) = self.array_layout(id, owner.ty)?;
                let index = self.index_after_owner(node.children[1], length, owner, out)?;
                let position =
                    Position::Index(index.integer.and_then(|value| usize::try_from(value).ok()));
                (element, Expr::Index(owner, index), position)
            }
            "projection" => {
                let Ty::Struct(layout) = owner.ty else {
                    return Err(self.error(id, "structure attendue"));
                };
                self.check_fields_visible(id, layout)?;
                let (field, ty) = self.structures[layout]
                    .fields
                    .iter()
                    .enumerate()
                    .find_map(|(field, (name, ty))| {
                        (Some(name.as_str()) == self.name(id)).then_some((field, *ty))
                    })
                    .ok_or_else(|| self.error(id, "champ inconnu"))?;
                (ty, Expr::Field(owner, field), Position::Field(field))
            }
            _ => return Err(self.error(id, "projection de référence stockée attendue")),
        };
        path.push(position);
        let mut value = self.emit(ty, expression, out);
        if self.has_dependencies(ty) {
            value.dependencies.loan = self.selected_loan(owner.dependencies.loan, &[position]);
            value = value.finish_evaluation(out);
        }
        Ok(value)
    }

    fn projection_root(&self, mut id: NodeId) -> NodeId {
        while matches!(self.node(id).kind, "projection" | "indice" | "groupe")
            && !(self.node(id).kind == "projection" && self.variant(id).is_some())
        {
            let node = self.node(id);
            if node.kind == "indice" && self.uses.get(&node.children[0])
                .and_then(|binding| self.slots[binding.0])
                .is_some_and(|slot| matches!(slot.ty, Ty::Slice { .. }))
            {
                break;
            }
            id = node.children[0];
        }
        id
    }

    fn access_projected(
        &self,
        id: NodeId,
        binding: BindingId,
        borrowed: bool,
        mutable: bool,
        path: &[Position],
    ) -> Result<(), Error> {
        self.access_projected_at(id, binding, borrowed, mutable, false, path)
    }

    fn access_projected_at(
        &self, id: NodeId, binding: BindingId, borrowed: bool, mutable: bool, write: bool,
        path: &[Position],
    ) -> Result<(), Error> {
        self.live_slot(id, binding)?;
        if self.conflicting_loan(id, mutable, write, |origin| {
            let same_owner = if borrowed {
                self.has_parent(origin, binding)
            } else {
                origin.root == binding && origin.storage
            };
            same_owner
                && (origin.parent.is_some_and(|parent| parent != binding)
                    || self.dependencies.paths[origin.lock.0]
                        .iter()
                        .zip(path)
                        .all(|(&left, &right)| left.overlaps(right)))
        }) {
            return Err(self.error(id, "accès à une place incompatible avec un emprunt actif"));
        }
        Ok(())
    }

    fn projection_value(
        &mut self,
        id: NodeId,
        access: Access,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let root = self.projection_root(id);
        let borrowed = self.node(root).kind == "indirection";
        let name = if borrowed {
            self.node(root).children[0]
        } else {
            root
        };
        let binding = self.uses.get(&name).copied().and_then(|binding| {
            let ty = self.slots[binding.0]?.ty;
            match (borrowed, ty) {
                (
                    true,
                    Ty::Ref {
                        target: Referent::Aggregate(layout),
                        ..
                    },
                ) => Some((binding, Ty::Struct(layout))),
                (false, Ty::Struct(_)) => Some((binding, ty)),
                _ => None,
            }
        });
        let base = if let Some((binding, ty)) = binding {
            let loan = self.live_slot(root, binding)?.loan;
            let expr = if borrowed {
                Expr::Dereference(binding)
            } else {
                Expr::Local(binding)
            };
            let mut value = self.emit(ty, expr, out);
            value.dependencies.loan = loan;
            value = value.finish_evaluation(out);
            value
        } else {
            self.expression(root, None, Access::Read, out)?
        };
        let mut path = Vec::new();
        let value = self.stored_place(id, root, base, &mut path, out)?;
        if let Some((binding, _)) = binding {
            self.access_projected(id, binding, borrowed, false, &path)?;
        }
        if matches!(access, Access::Move) {
            match value.ty {
                Ty::Struct(_) | Ty::Allocation(_) | Ty::Handle(..) => {
                    return Err(self.error(id, "déplacement partiel interdit"));
                }
                Ty::Ref { mutable: true, .. } | Ty::Slice { mutable: true, .. } => {
                    return Err(
                        self.error(id, "réemprunt explicite de la référence stockée requis")
                    );
                }
                _ => {}
            }
        }
        Ok(value)
    }

    fn reborrow_stored(
        &mut self,
        id: NodeId,
        place: NodeId,
        mutable: bool,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let root = self.projection_root(place);
        let borrowed = self.node(root).kind == "indirection";
        let name = if borrowed {
            self.node(root).children[0]
        } else {
            root
        };
        let binding = *self
            .uses
            .get(&name)
            .ok_or_else(|| self.error(id, "liaison agrégée locale requise"))?;
        let slot = self.live_slot(id, binding)?;
        let (ty, expression) = if borrowed {
            let Ty::Ref {
                target: Referent::Aggregate(layout),
                mutable: exclusive,
            } = slot.ty
            else {
                return Err(self.error(id, "agrégat emprunté attendu"));
            };
            if mutable && !exclusive {
                return Err(self.error(id, "réemprunt mutable depuis un agrégat partagé"));
            }
            (Ty::Struct(layout), Expr::Dereference(binding))
        } else {
            if mutable && !self.tree.bindings[binding.0].mutable {
                return Err(self.error(id, "réemprunt mutable depuis un agrégat immuable"));
            }
            (slot.ty, Expr::Local(binding))
        };
        let mut base = self.emit(ty, expression, out);
        base.dependencies.loan = slot.loan;
        base = base.finish_evaluation(out);
        let mut path = Vec::new();
        let source = self.stored_place(place, root, base, &mut path, out)?;
        let (ty, exclusive) = match source.ty {
            Ty::Ref { target, mutable: exclusive } => (Ty::Ref { target, mutable }, exclusive),
            Ty::Slice { element, mutable: exclusive } => (Ty::Slice { element, mutable }, exclusive),
            _ => return Err(self.error(id, "référence stockée attendue")),
        };
        if mutable && !exclusive {
            return Err(self.error(id, "réemprunt mutable d’une référence partagée"));
        }
        self.access_projected(id, binding, borrowed, mutable, &path)?;
        let lock = self.path(path);
        let mut origins = self.origins(source.dependencies.loan).to_vec();
        if borrowed {
            for origin in &mut origins {
                origin.parent = Some(binding);
                origin.lock = lock;
            }
        } else {
            origins.push(Origin {
                root: binding,
                storage: true,
                pool: false,
                parent: None,
                at: PathId::default(),
                from: PathId::default(),
                lock,
                opaque: false,
                capture_exclusive: false,
            });
        }
        let mut value = self.emit(ty, Expr::Temporary(source), out);
        value.dependencies.loan = Some(self.intern(origins));
        value = value.finish_evaluation(out);
        Ok(value)
    }

    fn borrow_projection(
        &mut self,
        id: NodeId,
        mutable: bool,
        prepare_assignment: bool,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        if self.node(id).kind == "indice" {
            let base = self.node(id).children[0];
            if let Some(Ty::Slice { mutable: exclusive, .. }) = self.known_type(base) {
                let binding = *self.uses.get(&base)
                    .ok_or_else(|| self.error(base, "liaison de tranche requise pour le réemprunt"))?;
                if mutable && !exclusive {
                    return Err(self.error(id, "réemprunt mutable d’une tranche partagée"));
                }
                let (target, address) = self.slice_element_address(id, out)?;
                self.live_slot(id, binding)?;
                self.access_reference(id, binding, mutable)?;
                let origins = self.origins(address.dependencies.loan).iter()
                    .map(|origin| Origin { parent: Some(binding), ..*origin })
                    .collect();
                let mut value = self.emit(Ty::Ref { target, mutable }, Expr::SliceElementBorrow(address), out);
                value.dependencies.loan = Some(self.intern(origins));
                return Ok(value.finish_evaluation(out));
            }
        }
        let mut root = id;
        while matches!(self.node(root).kind, "projection" | "indice" | "groupe") {
            root = self.node(root).children[0];
        }
        let dereference = self.node(root).kind == "indirection";
        let name = if dereference {
            self.node(root).children[0]
        } else {
            root
        };
        let binding = *self
            .uses
            .get(&name)
            .ok_or_else(|| self.error(id, "racine locale requise pour emprunter cette place"))?;
        let slot = self.live_slot(id, binding)?;
        let check_root = |checker: &Self| {
            if dereference {
                checker.dereference(root, mutable).map(|_| ())
            } else {
                checker.access_target(id, binding, mutable, false)
            }
        };
        let node = self.node(id);
        let mut path = Vec::new();
        let projected = prepare_assignment || dereference;
        let owner = if !projected {
            if !dereference && mutable && !self.tree.bindings[binding.0].mutable {
                return Err(self.error(id, "emprunt mutable d’une liaison immuable"));
            }
            check_root(self)?;
            self.expression(node.children[0], None, Access::Read, out)?
        } else {
            // Addressing one projection must allow disjoint reborrows.
            let (base_ty, expression) = if dereference {
                let Ty::Ref { target, mutable: exclusive } = slot.ty else {
                    return Err(self.error(id, "une référence est requise pour le déréférencement"));
                };
                if mutable && !exclusive {
                    return Err(self.error(id, "réemprunt mutable depuis un agrégat partagé"));
                }
                self.access_target(id, binding, false, false)?;
                (target.ty(), Expr::Dereference(binding))
            } else {
                (slot.ty, Expr::Local(binding))
            };
            let mut base = self.emit(base_ty, expression, out);
            base.dependencies.loan = slot.loan;
            let base = base.finish_evaluation(out);
            self.stored_place(node.children[0], root, base, &mut path, out)?
        };
        let (ty, expression, position) = if node.kind == "indice" {
            let (element, length) = self.array_layout(id, owner.ty)?;
            let index = self.index_after_owner(node.children[1], length, owner, out)?;
            let position = Position::Index(index.integer.and_then(|n| usize::try_from(n).ok()));
            (element, Expr::BorrowIndex(owner, index), position)
        } else {
            let Ty::Struct(layout) = owner.ty else {
                return Err(self.error(id, "structure attendue"));
            };
            self.check_fields_visible(id, layout)?;
            let (field, ty) = self.structures[layout]
                .fields
                .iter()
                .enumerate()
                .find_map(|(field, (name, ty))| {
                    (Some(name.as_str()) == self.name(id)).then_some((field, *ty))
                })
                .ok_or_else(|| self.error(id, "champ inconnu"))?;
            (ty, Expr::BorrowField(owner, field), Position::Field(field))
        };
        let lock = if projected {
            path.push(position);
            self.access_projected(id, binding, dereference, mutable, &path)?;
            self.path(path)
        } else {
            check_root(self)?;
            PathId::default()
        };
        let mut origins = self.origins(slot.loan).to_vec();
        if dereference {
            for origin in &mut origins {
                origin.parent = Some(binding);
                if origin.lock == PathId::default() {
                    origin.lock = lock;
                }
            }
        } else {
            origins.push(Origin {
                root: binding, storage: true, pool: false, parent: None,
                at: PathId::default(), from: PathId::default(), lock,
                opaque: false, capture_exclusive: false,
            });
        }
        let target = ty
            .referent()
            .ok_or_else(|| self.error(id, "place non empruntable"))?;
        let mut value = self.emit(Ty::Ref { target, mutable }, expression, out);
        value.dependencies.loan = Some(self.intern(origins));
        value = value.finish_evaluation(out);
        Ok(value)
    }

    fn await_future(&mut self, id: NodeId, out: &mut Vec<Instr>) -> Result<Value, Error> {
        if !self.in_async {
            return Err(self.error(id, ".await exige un contexte async"));
        }
        let operand = self.node(id).children[0];
        let future = self.expression(operand, None, Access::Move, out)?;
        self.complete_entry_effects(id, future)?;
        if let Ty::Handle(layout, true) = future.ty {
            return Ok(self.completion_value(layout, future, Expr::AwaitHandle(future), out));
        }
        let Ty::Future(function) = future.ty else {
            return Err(self.error(id, ".await attend une Future dans ce backend"));
        };
        let ty = self.signatures[function].result;
        let mut value = self.emit(ty, Expr::Await(future), out);
        self.unpack_output(&mut value, self.origins(future.dependencies.awaited_loan).to_vec());
        value = value.finish_evaluation(out);
        Ok(value)
    }

    fn subslice(
        &mut self, id: NodeId, base: NodeId, bounds: &[NodeId], mutable: bool,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let [start, end] = *bounds else {
            return Err(self.error(id, "deux bornes explicites requises pour la sous-tranche"));
        };
        let binding = *self.uses.get(&base)
            .ok_or_else(|| self.error(base, "liaison de tranche requise pour le réemprunt"))?;
        let slice = self.expression(base, None, Access::Read, out)?;
        let Ty::Slice { element, mutable: exclusive } = slice.ty else { unreachable!() };
        if mutable && !exclusive {
            return Err(self.error(id, "réemprunt mutable d’une tranche partagée"));
        }
        let pending = self.pending.len();
        self.pending.push(slice);
        let range = (|| {
            let start = self.expression(start, None, Access::Read, out)?;
            let end = self.expression(end, None, Access::Read, out)?;
            Ok::<_, Error>((start, end))
        })();
        self.pending.truncate(pending);
        let (start, end) = range?;
        for bound in [start, end] {
            if !(bound.ty.signed() || bound.ty.unsigned()) {
                return Err(self.error(id, "borne entière attendue"));
            }
        }
        if [start, end].iter().any(|bound| bound.integer.is_some_and(|n| n < 0))
            || start.integer.zip(end.integer).is_some_and(|(lo, hi)| lo > hi)
        {
            return Err(self.error(id, "bornes de sous-tranche invalides"));
        }
        self.live_slot(id, binding)?;
        self.access_reference(id, binding, mutable)?;
        let origins = self.origins(slice.dependencies.loan).iter()
            .map(|origin| Origin { parent: Some(binding), ..*origin }).collect();
        let mut value = self.emit(Ty::Slice { element, mutable }, Expr::Subslice(slice, start, end), out);
        value.dependencies.loan = Some(self.intern(origins));
        Ok(value.finish_evaluation(out))
    }

    fn slice_element_address(&mut self, id: NodeId, out: &mut Vec<Instr>) -> Result<(Referent, Value), Error> {
        let children = &self.node(id).children;
        let ty = self.usize_type(id)?;
        let slice = self.expression(children[0], None, Access::Read, out)?;
        let pending = self.pending.len();
        let Ty::Slice { element, .. } = slice.ty else {
            return Err(self.error(id, "tranche attendue"));
        };
        self.pending.push(slice);
        let index = self.expression(children[1], None, Access::Read, out);
        self.pending.truncate(pending);
        let index = index?;
        if !(index.ty.signed() || index.ty.unsigned()) {
            return Err(self.error(id, "indice entier attendu"));
        }
        let mut address = self.emit(ty, Expr::SliceElementAddress(slice, index), out);
        address.dependencies.loan = slice.dependencies.loan;
        Ok((element, address.finish_evaluation(out)))
    }

    fn future_value(
        &mut self,
        id: NodeId,
        function: usize,
        arguments: Vec<Value>,
        result_ty: Ty,
        result_loan: Option<LoanId>,
        result_output: Option<LoanId>,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let mut result = Vec::new();
        self.append_origins(&mut result, result_loan, &[]);
        if matches!(result_ty, Ty::Handle(..)) {
            self.append_origins(&mut result, result_output, &[Position::TaskOutput]);
        }
        let awaited_loan = (!result.is_empty()).then(|| self.intern(result));
        let mut origins = arguments
            .iter()
            .flat_map(|value| {
                self.origins(value.dependencies.loan).iter().map(|origin| Origin {
                    capture_exclusive: origin.capture_exclusive
                        || self.has_exclusive_dependencies(value.ty),
                    ..*origin
                })
            })
            .collect::<Vec<_>>();
        origins.retain(|origin| {
            !self.dependencies.paths[origin.at.0].iter().any(|p| matches!(p, Position::TaskEffect(_)))
        });
        for (parameter, path) in self.call_waits(function) {
            let selector = self.dependencies.paths[path.0].clone();
            for mut origin in self.selected_origins(arguments[parameter].dependencies.loan, &selector) {
                let positions = &self.dependencies.paths[origin.at.0];
                if let Some(Position::TaskEffect(index)) = positions.last().copied()
                    && !positions.contains(&Position::TaskOutput)
                {
                    origin.at = self.path(vec![Position::TaskEffect(index)]);
                    origins.push(origin);
                } else if !origin.storage && !positions.contains(&Position::TaskOutput) {
                    origin.at = self.path(vec![Position::TaskWait]);
                    origins.push(origin);
                }
            }
        }
        let effects = self.call_entry_effects(function);
        self.defer_entry_effects(id, &effects, &arguments, &mut origins)?;
        let loan = (!origins.is_empty()).then(|| self.intern(origins));
        let mut value = self.emit(
            Ty::Future(function),
            Expr::FutureNew(function, arguments),
            out,
        );
        value.dependencies.loan = loan;
        value.dependencies.awaited_loan = awaited_loan;
        value = value.finish_evaluation(out);
        Ok(value)
    }

    fn expression(
        &mut self,
        id: NodeId,
        expected: Option<Ty>,
        access: Access,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        if let Some((ty, literal)) = self.named_constant(id) {
            let value = self.expression(literal, Some(ty), Access::Read, out)?;
            return self.coerce(id, value, expected, out);
        }
        if self.node(id).kind == "appel" && self.named_constant(self.node(id).children[0]).is_some() {
            return Err(self.error(id, "une constante ne peut pas être appelée"));
        }
        if self.runtime_call(id, "wait_socket") {
            let offset = self.tree.tokens[self.node(id).start].span.start;
            if !self.in_async || !self.tree.std_socket_wait_ranges.iter().any(|range| range.contains(&offset))
                || self.node(id).children.len() != 3
            {
                return Err(self.error(id, "attente de socket réservée au réacteur de std"));
            }
            let socket = self.expression(self.node(id).children[1], Some(Ty::U64), Access::Read, out)?;
            let direction = self.expression(self.node(id).children[2], Some(Ty::Bool), Access::Read, out)?;
            return Ok(self.emit(Ty::I64, Expr::SocketWait(socket, direction), out));
        }
        if self.runtime_call(id, "complete_socket") {
            let offset = self.tree.tokens[self.node(id).start].span.start;
            if !self.in_async || !self.tree.std_socket_wait_ranges.iter().any(|range| range.contains(&offset))
                || self.node(id).children.len() != 3
            {
                return Err(self.error(id, "attente de socket réservée au réacteur de std"));
            }
            let socket = self.expression(self.node(id).children[1], Some(Ty::U64), Access::Read, out)?;
            let request = self.expression(self.node(id).children[2], Some(Ty::Usize), Access::Read, out)?;
            return Ok(self.emit(Ty::I64, Expr::SocketCompletion(socket, request), out));
        }
        if self.runtime_call(id, "attach_socket") {
            let offset = self.tree.tokens[self.node(id).start].span.start;
            if !self.tree.std_socket_wait_ranges.iter().any(|range| range.contains(&offset))
                || self.node(id).children.len() != 2
            {
                return Err(self.error(id, "association de socket réservée au réacteur de std"));
            }
            let socket = self.expression(self.node(id).children[1], Some(Ty::U64), Access::Read, out)?;
            return Ok(self.emit(Ty::I64, Expr::SocketAttach(socket), out));
        }
        if self.runtime_call(id, "process_args") {
            let trusted = self.names.get("__crust_package_env_args").is_some_and(|&index| {
                let body = self.node(self.signatures[index].body);
                body.children.len() == 1 && self.node(body.children[0]).children == [id]
            });
            let offset = self.tree.tokens[self.node(id).start].span.start;
            if !trusted || !self.tree.std_env_range.contains(&offset) || self.node(id).children.len() != 1 {
                return Err(self.error(id, "accès aux arguments réservé à std::env"));
            }
            return Ok(self.emit(self.function_result, Expr::ProcessArgs, out));
        }
        if self.node(id).kind == "await" {
            let value = self.await_future(id, out)?;
            if value.ty == Ty::Void {
                return Err(self.error(id, ".await ne produit pas de valeur ici"));
            }
            return self.coerce(id, value, expected, out);
        }
        if self.node(id).kind == "appel" {
            let node = self.node(id);
            let blocking = self.runtime_call(id, "spawn_blocking");
            if blocking || self.runtime_call(id, "spawn") {
                if blocking != self.in_async {
                    return Err(self.error(
                        id,
                        "spawn est synchrone, spawn_blocking exige un contexte async",
                    ));
                }
                if node.children.len() != 2 {
                    return Err(self.error(id, "le lancement attend une Future"));
                }
                let future = self.expression(node.children[1], None, Access::Move, out)?;
                let Ty::Future(function) = future.ty else {
                    return Err(self.error(id, "Future attendue"));
                };
                if self.dependent_handle(future.ty, future.dependencies.loan) {
                    return Err(self.error(
                        id,
                        "un lancement faillible ne peut pas abandonner le handle dépendant capturé",
                    ));
                }
                let ty = self.handle_type(self.signatures[function].result, blocking);
                let mut value = self.emit(ty, Expr::FutureSpawn(future, blocking), out);
                value.dependencies.loan = future.dependencies.loan;
                value.dependencies.awaited_loan = future.dependencies.awaited_loan;
                value = value.finish_evaluation(out);
                return self.coerce(id, value, expected, out);
            }
        }
        if let Some(block) = self.native_block(id) {
            let value = self.native_start(id, block, true, out)?;
            return self.coerce(id, value, expected, out);
        }
        if self.node(id).kind == "appel méthode" && self.name(id) == Some("join") {
            let [receiver] = self.node(id).children.as_slice() else {
                return Err(self.error(id, "join ne prend aucun argument"));
            };
            let handle = if let Some(block) = self.native_block(*receiver) {
                self.native_start(*receiver, block, false, out)?
            } else {
                self.expression(*receiver, None, Access::Move, out)?
            };
            let Ty::Handle(layout, false) = handle.ty else {
                return Err(self.error(id, "handle de thread attendu"));
            };
            if self.in_async {
                return Err(self.error(id, "join exige un contexte synchrone"));
            }
            self.complete_entry_effects(id, handle)?;
            let value = self.completion_value(layout, handle, Expr::NativeJoin(handle), out);
            return self.coerce(id, value, expected, out);
        }
        let node = self.node(id);
        let children = &node.children;
        let value = match node.kind {
            "propagation" => self.propagate(id, out)?
                .ok_or_else(|| self.error(id, "? ne produit pas de valeur ici"))?,
            "nom" if self.name(id) == Some("None") && !self.uses.contains_key(&id)
                && matches!(expected.and_then(|ty| self.propagation_layout(ty)), Some((_, false))) =>
            {
                self.wrap_payload(expected.unwrap(), 0, None, out)
            }
            "scope" => {
                let mut nested = Vec::new();
                let (_, value) = self.value_arm(id, expected, &mut nested)?;
                let value =
                    value.ok_or_else(|| self.error(id, "le bloc ne fournit aucun résultat"))?;
                let receiver = self.value_receiver(id, value)?;
                nested.push(Instr::Receive(receiver, value));
                out.push(Instr::Reserve(receiver));
                out.push(Instr::Block(nested));
                receiver
            }
            "match" => self
                .enum_match(id, self.function_result, Some(expected), out)?
                .1
                .unwrap(),
            "if" => self.conditional_value(id, expected, out)?,
            "tuple" => self.tuple(id, expected, out)?,
            "construction" => self.construct(id, out)?,
            "appel méthode" if let Some(variant @ (layout, _)) = self.variant_call(id) =>
                self.construct_fields(id, layout, Some(variant), &children[1..], false, out)?,
            "pool" => self.pool(id, out)?,
            "tableau" | "tableau répété" => self.array(id, expected, out)?,
            "projection" if self.variant(id).is_some() => self.construct_variant_unit(id, out)?,
            "indice" if self.growing_handle(children[0]).is_some() => {
                let (binding, kind) = self.growing_handle(children[0]).unwrap();
                let Growing::Vector(element) = kind else {
                    return Err(self.error(id, "lecture indexée réservée au vecteur"));
                };
                if contains_handle(element, &self.structures) {
                    return Err(self.error(id, "utiliser remove ou pop pour déplacer un handle de vecteur"));
                }
                let handle = self.local(children[0], binding, Access::Read, out)?;
                let index = self.expression(children[1], None, Access::Read, out)?;
                if !(index.ty.signed() || index.ty.unsigned()) {
                    return Err(self.error(id, "indice entier attendu"));
                }
                self.live_slot(id, binding)?;
                if matches!(
                    element,
                    Ty::Struct(_) | Ty::Allocation(_) | Ty::Ref { mutable: true, .. }
                ) && matches!(access, Access::Move)
                {
                    return Err(self.error(id, "déplacement partiel depuis un vecteur interdit"));
                }
                let mut value = self.emit(element, Expr::GrowingIndex(handle, index), out);
                if self.has_dependencies(element) {
                    let position =
                        Position::Index(index.integer.and_then(|i| usize::try_from(i).ok()));
                    value.dependencies.loan = self.selected_loan(handle.dependencies.loan, &[position]);
                    value = value.finish_evaluation(out);
                }
                value
            }
            "indice" if matches!(self.known_type(children[0]), Some(Ty::Slice { .. })) => {
                let (element, address) = self.slice_element_address(id, out)?;
                let ty = element.ty();
                if ty != Ty::Str && ty.scalar().is_none() && matches!(access, Access::Move) {
                    return Err(self.error(id, "déplacement depuis une place empruntée"));
                }
                let mut value = self.emit(ty, Expr::SliceElement(address), out);
                if self.has_dependencies(ty) {
                    value.dependencies.loan = address.dependencies.loan;
                }
                value.finish_evaluation(out)
            }
            "indice" | "projection" => self.projection_value(id, access, out)?,
            "loop" => self
                .loop_effect(id, self.function_result, Some(expected), out)?
                .1
                .unwrap(),
            "nom" => {
                let binding = *self
                    .uses
                    .get(&id)
                    .ok_or_else(|| self.error(id, "liaison inconnue"))?;
                self.local(id, binding, access, out)?
            }
            "emprunt" => {
                if self.node(children[0]).kind == "indice" {
                    let place = self.node(children[0]);
                    let index = self.node(place.children[1]);
                    if index.kind == "plage" {
                        let root = place.children[0];
                        let mutable = self.text(node.start + 1) == "mut";
                        if matches!(self.known_type(root), Some(Ty::Slice { .. })) {
                            if index.name == Some(index.start) {
                                return Err(self.error(id, "deux bornes explicites requises pour la sous-tranche"));
                            }
                            let value = self.subslice(id, root, &index.children, mutable, out)?;
                            return self.coerce(id, value, expected, out);
                        }
                        if let Some((binding, Growing::Vector(element))) = self.growing_handle(root) {
                            if index.name != Some(index.start) || !index.children.is_empty() {
                                return Err(self.error(id, "tranche complète de vecteur attendue"));
                            }
                            if self.has_dependencies(element) || inline_destructor(element, &self.structures) {
                                return Err(self.error(id, "élément de tranche de vecteur avec dépendances hors périmètre"));
                            }
                            if mutable && !self.tree.bindings[binding.0].mutable {
                                return Err(self.error(id, "vecteur mutable attendu pour la tranche"));
                            }
                            let referent = element.referent()
                                .ok_or_else(|| self.error(id, "type d’élément de tranche non pris en charge"))?;
                            self.access_target(id, binding, mutable, false)?;
                            let handle = self.local(root, binding, Access::Read, out)?;
                            let mut view = self.emit(Ty::Slice { element: referent, mutable },
                                Expr::GrowingSlice(handle, element), out);
                            view.dependencies.loan = Some(self.intern(vec![Origin {
                                root: binding, storage: true, pool: false, parent: None,
                                at: PathId::default(), from: PathId::default(), lock: PathId::default(),
                                opaque: false, capture_exclusive: false,
                            }]));
                            let view = view.finish_evaluation(out);
                            return self.coerce(id, view, expected, out);
                        }
                        if index.name != Some(index.start) {
                            return Err(self.error(id, "borne inférieure de tranche hors périmètre"));
                        }
                        let binding = self.uses.get(&root).copied();
                        let (array_ty, projected) = if let Some(binding) = binding {
                            (self.live_slot(id, binding)?.ty, None)
                        } else if matches!(self.node(root).kind, "projection" | "indice") {
                            let base = self.borrow_projection(root, mutable, true, out)?;
                            let Ty::Ref { target, .. } = base.ty else { unreachable!() };
                            (target.ty(), Some(base))
                        } else {
                            return Err(self.error(id, "place de tableau attendue"));
                        };
                        let (element, length) = self.array_layout(id, array_ty)?;
                        let element = element.referent()
                            .ok_or_else(|| self.error(id, "type d’élément de tranche non pris en charge"))?;
                        let end = if let Some(&end) = index.children.first() {
                            let expected = if self.known_type(end).is_none()
                                && self.node(end).kind == "littéral"
                            {
                                Some(self.usize_type(end)?)
                            } else {
                                None
                            };
                            let pending = self.pending.len();
                            if let Some(projected) = projected {
                                self.pending.push(projected);
                            }
                            let value = self.expression(end, expected, Access::Read, out);
                            self.pending.truncate(pending);
                            let value = value?;
                            if !(value.ty.signed() || value.ty.unsigned()) {
                                return Err(self.error(end, "borne entière attendue"));
                            }
                            if value.integer.is_some_and(|n| n < 0 || n > length as i128) {
                                return Err(self.error(end, "borne de tranche hors du tableau"));
                            }
                            Some(value)
                        } else {
                            None
                        };
                        let (base, loan) = if let Some(binding) = binding {
                            if mutable && !self.tree.bindings[binding.0].mutable {
                                return Err(self.error(id, "tableau mutable attendu pour la tranche"));
                            }
                            self.access_target(id, binding, mutable, false)?;
                            let base = self.local(root, binding, Access::Read, out)?;
                            let mut origins = self.origins(self.live_slot(id, binding)?.loan).to_vec();
                            origins.push(Origin {
                                root: binding, storage: true, pool: false, parent: None,
                                at: PathId::default(), from: PathId::default(), lock: PathId::default(),
                                opaque: false, capture_exclusive: false,
                            });
                            (base, Some(self.intern(origins)))
                        } else {
                            let base = projected.unwrap();
                            (base, base.dependencies.loan)
                        };
                        let mut slice = self.emit(
                            Ty::Slice { element, mutable },
                            Expr::Slice(base, length, end),
                            out,
                        );
                        slice.dependencies.loan = loan;
                        return self.coerce(id, slice.finish_evaluation(out), expected, out);
                    }
                }
                let mutable = self.text(node.start + 1) == "mut";
                if self.node(children[0]).kind == "indirection" {
                    let parent = self.node(children[0]).children[0];
                    if self.node(parent).kind == "indirection" {
                        let (binding, outer) = self.dereference(parent, mutable)?;
                        let Ty::Ref { target, mutable: inner } = outer.ty() else {
                            return Err(self.error(id, "référence interne attendue"));
                        };
                        if mutable && !inner {
                            return Err(self.error(id, "réemprunt mutable d’une référence partagée"));
                        }
                        let reference = self.expression(parent, None, Access::Read, out)?;
                        let mut value = self.emit(Ty::Ref { target, mutable }, Expr::BorrowThrough(reference), out);
                        let origins = self.origins(reference.dependencies.loan).iter().map(|origin| Origin {
                            parent: Some(binding), ..*origin
                        }).collect();
                        value.dependencies.loan = Some(self.intern(origins));
                        return self.coerce(id, value.finish_evaluation(out), expected, out);
                    }

                    if matches!(self.node(parent).kind, "projection" | "indice" | "groupe") {
                        let value = self.reborrow_stored(id, parent, mutable, out)?;
                        return self.coerce(id, value, expected, out);
                    }
                    let binding = *self
                        .uses
                        .get(&parent)
                        .ok_or_else(|| self.error(id, "référence parente nommée requise"))?;
                    let value = self.reborrow(id, binding, mutable, out)?;
                    return self.coerce(id, value, expected, out);
                }
                if matches!(self.node(children[0]).kind, "projection" | "indice") {
                    let value = self.borrow_projection(children[0], mutable, false, out)?;
                    return self.coerce(id, value, expected, out);
                }
                let binding = *self
                    .uses
                    .get(&children[0])
                    .ok_or_else(|| self.error(id, "place locale requise pour l’emprunt"))?;
                let slot = self.live_slot(id, binding)?;
                let pool = self
                    .pool_layout(slot.ty)
                    .map(|(element, _)| self.pool_type(element, 0));
                let target = match pool {
                    Some(index) => Referent::Pool(index),
                    None => slot
                        .ty
                        .referent()
                        .ok_or_else(|| self.error(id, "type d’emprunt non pris en charge"))?,
                };
                if matches!(slot.ty, Ty::Ref { .. }) {
                    self.access_reference(id, binding, mutable)?;
                }
                if mutable && !self.tree.bindings[binding.0].mutable {
                    return Err(self.error(id, "emprunt mutable d’une liaison immuable"));
                }
                self.access_target(id, binding, mutable, false)?;
                let expression = if pool.is_some() {
                    Expr::PoolBorrow(binding)
                } else {
                    Expr::Borrow(binding)
                };
                let mut value = self.emit(Ty::Ref { target, mutable }, expression, out);
                let mut origins = self.origins(slot.loan).to_vec();
                origins.push(Origin {
                    root: binding,
                    storage: true,
                    pool: false,
                    parent: None,
                    at: PathId::default(),
                    from: PathId::default(),
                    lock: PathId::default(),
                    opaque: false,
                    capture_exclusive: false,
                });
                value.dependencies.loan = Some(self.intern(origins));
                value = value.finish_evaluation(out);
                value
            }
            "appel méthode"
                if matches!(self.name(id), Some("len" | "byte_len"))
                    && self.growing_handle(children[0]).is_some() =>
            {
                let (binding, kind) = self.growing_handle(children[0]).unwrap();
                let element = match (self.name(id), kind) {
                    (Some("len"), Growing::Vector(element)) => element,
                    (Some("byte_len"), Growing::String) => Ty::U8,
                    _ => return Err(self.error(id, "mesure de longueur incompatible")),
                };
                if children.len() != 1 {
                    return Err(self.error(id, "aucun argument attendu"));
                }
                let handle = self.local(children[0], binding, Access::Read, out)?;
                self.emit(Ty::U64, Expr::GrowingLen(handle, element), out)
            }
            "appel méthode" if matches!(self.name(id), Some("pop" | "remove"))
                && (self.growing_handle(children[0]).is_some() || self.vector_field(children[0]).is_some()) =>
                self.vector_extract(id, out)?,
            "appel méthode" if self.name(id) == Some("as_bytes")
                && self.known_type(children[0]) == Some(Ty::Str) =>
            {
                if children.len() != 1 { return Err(self.error(id, "as_bytes ne prend aucun argument")); }
                let text = self.expression(children[0], Some(Ty::Str), Access::Read, out)?;
                let ty = Ty::Slice { element: Referent::U8, mutable: false };
                let mut view = self.emit(ty, Expr::StrBytes(text), out);
                view.dependencies.loan = text.dependencies.loan;
                view.finish_evaluation(out)
            }
            "appel méthode" if self.name(id) == Some("content_eq")
                && matches!(self.known_type(children[0]), Some(Ty::Slice { .. })) =>
            {
                let [left, right] = children.as_slice() else {
                    return Err(self.error(id, "content_eq exige un argument"));
                };
                let function = self.names.get("__crust_package_byte_content_eq").copied()
                    .ok_or_else(|| self.error(id, "content_eq exige la bibliothèque standard"))?;
                let left = self.expression(*left, None, Access::Read, out)?;
                let pending = self.pending.len();
                self.pending.push(left);
                let right = self.expression(*right, None, Access::Read, out);
                self.pending.truncate(pending);
                let right = right?;
                if ![left, right].iter().all(|value| matches!(value.ty, Ty::Slice { element: Referent::U8, .. })) {
                    return Err(self.error(id, "content_eq exige deux tranches d’octets"));
                }
                self.emit(Ty::Bool, Expr::Call(function, vec![left, right], CallKind::Ordinary), out)
            }
            "appel méthode" if self.name(id) == Some("len")
                && matches!(self.known_type(children[0]), Some(Ty::Slice { .. })) =>
            {
                if children.len() != 1 { return Err(self.error(id, "len ne prend aucun argument")); }
                let slice = self.expression(children[0], None, Access::Read, out)?;
                self.emit(Ty::Usize, Expr::SliceLen(slice), out)
            }
            "appel méthode" if self.name(id) == Some("new")
                && self.uses.get(&children[0]).and_then(|binding| self.slots[binding.0])
                    .is_some_and(|slot| self.pool_layout(slot.ty).is_some()
                        || matches!(slot.ty, Ty::Ref { target: Referent::Pool(_), .. })) =>
                self.pool_new(id, out)?,
            "indirection"
                if self
                    .uses
                    .get(&children[0])
                    .copied()
                    .and_then(|binding| self.slots[binding.0])
                    .is_some_and(|slot| matches!(slot.ty, Ty::Allocation(_))) =>
            {
                let binding = self.uses[&children[0]];
                let Ty::Allocation(element) = self.live_slot(id, binding)?.ty else {
                    unreachable!()
                };
                let ty = element.ty();
                if contains_handle(ty, &self.structures) && matches!(access, Access::Move) {
                    let allocation = self.local(children[0], binding, Access::Move, out)?;
                    let mut value = self.emit(ty, Expr::PoolTake(allocation), out);
                    let payload = self.origins(allocation.dependencies.loan).iter().copied()
                        .filter(|origin| {
                            let path = &self.dependencies.paths[origin.at.0];
                            path.first() == Some(&Position::Field(0))
                                || (path.is_empty() && !origin.storage && !origin.pool)
                        })
                        .collect::<Vec<_>>();
                    let loan = (!payload.is_empty()).then(|| self.intern(payload));
                    let origins = self.selected_origins(loan, &[Position::Field(0)]);
                    self.unpack_output(&mut value, origins);
                    return Ok(value.finish_evaluation(out));
                }
                let handle = self.local(children[0], binding, Access::Read, out)?;
                if self.growing_layout(ty).is_some() {
                    return Err(self.error(id, "utiliser les méthodes du contenu grandissant"));
                }
                if let Ty::Struct(index) = ty {
                    if !self.structures[index].variants.is_empty() || matches!(access, Access::Move)
                    {
                        return Err(self
                            .error(id, "lecture par valeur d’un agrégat de pool hors périmètre"));
                    }
                }
                let mut value = self.emit(ty, Expr::PoolRead(handle), out);
                if self.has_dependencies(ty) {
                    value.dependencies.loan = handle.dependencies.loan;
                    value = value.finish_evaluation(out);
                }
                value
            }
            "indirection" if self.node(children[0]).kind == "indirection" => {
                let input = self.expression(children[0], None, Access::Read, out)?;
                if let Ty::Allocation(target) = input.ty {
                    if target.ty().scalar().is_none() {
                        return Err(self.error(id, "lecture d’un contenu scalaire attendue"));
                    }
                    let mut value = self.emit(target.ty(), Expr::PoolRead(input), out);
                    if target.ty() == Ty::Usize {
                        value.dependencies.loan = input.dependencies.loan;
                        value = value.finish_evaluation(out);
                    }
                    return self.coerce(id, value, expected, out);
                }
                let Ty::Ref { target, .. } = input.ty else {
                    return Err(self.error(id, "référence requise pour le déréférencement"));
                };
                if target.ty().scalar().is_none() && matches!(access, Access::Move) {
                    return Err(self.error(id, "déplacement depuis une place empruntée"));
                }
                let mut result = self.emit(target.ty(), Expr::DereferenceValue(input), out);
                if self.has_dependencies(result.ty) {
                    result.dependencies.loan = input.dependencies.loan;
                    result = result.finish_evaluation(out);
                }
                result
            }
            "indirection" if matches!(self.node(children[0]).kind, "indice" | "projection") => {
                let handle = self.expression(children[0], None, Access::Read, out)?;
                if let Ty::Ref { target, .. } = handle.ty
                    && target.ty().scalar().is_some()
                {
                    let mut value = self.emit(target.ty(), Expr::DereferenceValue(handle), out);
                    if target.ty() == Ty::Usize {
                        value.dependencies.loan = handle.dependencies.loan;
                        value = value.finish_evaluation(out);
                    }
                    return self.coerce(id, value, expected, out);
                }
                let Ty::Allocation(content) = handle.ty else {
                    return Err(self.error(id, "allocation attendue dans la case"));
                };
                if content.ty().scalar().is_none() {
                    return Err(self.error(id, "lecture d’un contenu scalaire attendue"));
                }
                let mut value = self.emit(content.ty(), Expr::PoolRead(handle), out);
                if content.ty() == Ty::Usize {
                    value.dependencies.loan = handle.dependencies.loan;
                    value = value.finish_evaluation(out);
                }
                value
            }
            "indirection" => {
                let (reference, target) = self.dereference(id, false)?;
                if matches!(target, Referent::Pool(_)) {
                    return Err(self.error(id, "utiliser le pool à travers sa référence"));
                }
                if matches!(target.ty(), Ty::Struct(_) | Ty::Allocation(_) | Ty::Ref { .. }) && matches!(access, Access::Move) {
                    return Err(self.error(id, "déplacement d’un agrégat emprunté"));
                }
                let mut value = self.emit(target.ty(), Expr::Dereference(reference), out);
                if self.has_dependencies(target.ty()) {
                    value.dependencies.loan = self.live_slot(id, reference)?.loan;
                    value = value.finish_evaluation(out);
                }
                value
            }
            "littéral" if matches!(self.name(id), Some("true" | "false")) => {
                self.emit(Ty::Bool, Expr::Boolean(self.name(id) == Some("true")), out)
            }
            "littéral" if self.tree.tokens[node.start].kind == crate::lexer::Kind::Text => {
                self.emit(Ty::Str, Expr::StrLiteral(crate::lexer::decoded_text(self.text(node.start))), out)
            }
            "littéral" => self.integer(id, false, expected, out)?,
            "groupe" if children.len() == 1 => {
                self.expression(children[0], expected, access, out)?
            }
            "unaire" if self.name(id) == Some("-") && self.node(children[0]).kind == "littéral" => {
                self.integer(children[0], true, expected, out)?
            }
            "unaire" if matches!(self.name(id), Some("-" | "!" | "~")) => {
                let operator = self.name(id).unwrap();
                let hint = if operator == "!" {
                    Some(Ty::Bool)
                } else {
                    expected
                };
                let operand = self.expression(children[0], hint, Access::Read, out)?;
                if operator == "~" && !(operand.ty.signed() || operand.ty.unsigned()) {
                    return Err(self.error(id, "~ bit à bit exige un entier"));
                }
                if operator == "-" && !(operand.ty.signed() || operand.ty.float()) {
                    return Err(self.error(id, "opérande entier requis"));
                }
                if operator == "-"
                    && let Some(value) = operand.integer
                {
                    out.push(Instr::Discard(operand));
                    return self.checked_integer(id, operand.ty, -value, out);
                }
                let mut value = self.emit(operand.ty, Expr::Unary(operator.to_owned(), operand), out);
                value.dependencies.loan = operand.dependencies.loan;
                value.finish_evaluation(out)
            }
            "binaire" if self.operator(id) == "as" => {
                let input = self.expression(children[0], None, Access::Read, out)?;
                let target = self.ty(children[1])?;
                if !input.ty.exact_cast_to(target, self.tree.target.pointer_width()) {
                    return Err(self.error(id, "as exige une conversion exacte pour tout le type source"));
                }
                let mut value = self.emit(target, Expr::Cast(input), out);
                value.integer = input.integer.filter(|_| target.signed() || target.unsigned());
                value.dependencies.loan = input.dependencies.loan;
                value.finish_evaluation(out)
            }
            "binaire" if matches!(self.operator(id), "<<" | ">>") => self.shift(id, expected, out)?,
            "binaire" if matches!(self.operator(id), "&&" | "||") => self.short_circuit(id, out)?,
            "binaire" => {
                let operator = self.operator(id);
                let comparison = matches!(operator, "==" | "!=" | "<" | ">" | "<=" | ">=");
                if !comparison && !matches!(operator, "+" | "-" | "*" | "/" | "%" | "&" | "|" | "^") {
                    return Err(self.error(id, "opérateur hors du sous-ensemble vérifié"));
                }
                let hint = if comparison { None } else { expected };
                let hint = hint
                    .or_else(|| self.known_type(children[0]))
                    .or_else(|| self.known_type(children[1]));
                let left = self.expression(children[0], hint, Access::Read, out)?;
                if let Ty::Slice { element, .. } = left.ty {
                    if !matches!(operator, "==" | "!=") {
                        return Err(self.error(id, "seuls == et != comparent les tranches"));
                    }
                    let pending = self.pending.len();
                    self.pending.push(left);
                    let right = self.expression(children[1], None, Access::Read, out);
                    self.pending.truncate(pending);
                    let right = right?;
                    if !matches!(right.ty, Ty::Slice { element: other, .. } if other == element) {
                        return Err(self.error(id, "tranches de même type d’élément attendues"));
                    }
                    let value = self.emit(Ty::Bool, Expr::Binary(operator.to_owned(), left, right), out);
                    return self.coerce(id, value, expected, out);
                }
                let right = self.expression(children[1], Some(left.ty), Access::Read, out)?;
                self.finish_scalar_binary(id, children[1], operator, left, right, out)?
            }
            "appel"
                if self.node(children[0]).kind == "nom qualifié"
                    && self.name(children[0]) == Some("new")
                    && self.text(self.node(children[0]).start) == "HashMap" =>
            {
                if children.len() != 1 {
                    return Err(self.error(id, "HashMap::new ne prend aucun argument"));
                }
                let ty = self.ty(self.node(children[0]).children[0])?;
                self.emit(ty, Expr::MapNew, out)
            }
            "appel méthode"
                if matches!(self.name(id), Some("insert" | "get" | "get_mut" | "remove"))
                    && self.uses.get(&children[0]).and_then(|binding| self.slots[binding.0])
                        .is_some_and(|slot| matches!(self.growing_layout(slot.ty), Some(Growing::Map(..)))) =>
            {
                self.map_method(id, out)?
            }
            "appel" if self.node(children[0]).kind == "nom"
                && self.name(children[0]) == Some("addr")
                && !self.uses.contains_key(&children[0]) =>
            {
                if children.len() != 2 {
                    return Err(self.error(id, "addr exige une référence"));
                }
                let ty = self.usize_type(id)?;
                let argument = self.node(children[1]);
                if argument.kind == "emprunt" && self.node(argument.children[0]).kind == "indice" {
                    let place = self.node(argument.children[0]);
                    let base = place.children[0];
                    if let Some(Ty::Slice { mutable, .. }) = self.known_type(base) {
                        if self.text(argument.start + 1) == "mut" && !mutable {
                            return Err(self.error(id, "tranche mutable attendue"));
                        }
                        let (_, address) = self.slice_element_address(argument.children[0], out)?;
                        return self.coerce(id, address, expected, out);
                    }
                }
                let reference = self.expression(children[1], None, Access::Read, out)?;
                if !matches!(reference.ty, Ty::Ref { .. }) {
                    return Err(self.error(id, "addr exige une référence"));
                }
                let mut address = self.emit(ty, Expr::Address(reference), out);
                address.dependencies.loan = reference.dependencies.loan;
                address.finish_evaluation(out)
            }
            "appel"
                if self.node(children[0]).kind == "nom"
                    && self.name(children[0]) == Some("copy")
                    && !self.uses.contains_key(&children[0]) =>
            {
                if children.len() != 2 || self.node(children[1]).kind != "nom" {
                    return Err(self.error(id, "copy exige une liaison primitive"));
                }
                let value = self.expression(children[1], expected, Access::Read, out)?;
                if value.ty.scalar().is_none() {
                    return Err(self.error(id, "copy exige une liaison primitive"));
                }
                value
            }
            "appel" if self.node(children[0]).kind == "nom"
                && matches!(self.name(children[0]), Some("Ok" | "Err" | "Some"))
                && !self.uses.contains_key(&children[0])
                && !self.names.contains_key(self.name(children[0]).unwrap()) =>
            {
                let name = self.name(children[0]).unwrap();
                let is_result = name != "Some";
                let (layout, _) = expected.and_then(|ty| self.propagation_layout(ty))
                    .filter(|&(_, result)| result == is_result)
                    .ok_or_else(|| self.error(id, if is_result {
                        "type Result attendu pour Ok ou Err"
                    } else {
                        "type Option attendu pour Some"
                    }))?;
                let tag = usize::from(name != "Err");
                let fields = &self.structures[layout].variants[tag].1;
                let argument = match (fields.as_slice(), &children[1..]) {
                    ([(_, ty)], [child]) => Some(self.expression(*child, Some(*ty), Access::Move, out)?),
                    ([], [child]) if self.node(*child).kind == "groupe"
                        && self.node(*child).children.is_empty() => None,
                    ([], [child]) if self.node(*child).kind == "propagation" => {
                        if self.propagate(*child, out)?.is_some() {
                            return Err(self.error(*child, "charge de Result incompatible"));
                        }
                        None
                    }
                    _ => return Err(self.error(id, "charge de Result incompatible")),
                };
                self.wrap_payload(Ty::Struct(layout), tag, argument, out)
            }
            "appel" if self.iter_constructor(id) => self.iter_new(id, out)?,
            "appel méthode" if self.name(id) == Some("map") && self.pipeline_candidate(children[0]) =>
                self.iter_map(id, out)?,
            "appel méthode" if self.name(id) == Some("next") && self.is_pipeline(children[0]) =>
                self.iter_next(id, out)?,
            "appel" | "appel méthode" => {
                let (callee, arguments, ty, loan, awaited_loan) = self.call(id, out)?;
                if self.signatures[callee].asynchronous {
                    let value = self.future_value(id, callee, arguments, ty, loan, awaited_loan, out)?;
                    return self.coerce(id, value, expected, out);
                }
                if ty == Ty::Void {
                    return Err(self.error(id, "appel Void utilisé comme valeur"));
                }
                let offset = self.tree.tokens[self.node(self.signatures[callee].body).start].span.start;
                let method_metadata = node.kind == "appel méthode"
                    && matches!(self.name(id), Some("addr" | "peer" | "port" | "ipv4_bits" | "count" | "sender" | "size"))
                    && (self.tree.std_file_range.contains(&offset)
                        || self.tree.std_async_io_ranges.iter().any(|range| range.contains(&offset)));
                let file_mode = node.kind == "appel"
                    && self.tree.std_file_range.contains(&offset)
                    && self.qualified_method(id).is_some_and(|(_, name)|
                        matches!(name, "read_only" | "write_only" | "read_write" | "append" | "truncate"));
                let metadata = method_metadata || file_mode;
                let kind = if metadata { CallKind::IoMetadata } else { CallKind::Ordinary };
                let mut value = self.emit(ty, Expr::Call(callee, arguments, kind), out);
                value.dependencies.loan = loan;
                value.dependencies.awaited_loan = awaited_loan;
                value = value.finish_evaluation(out);
                value
            }
            _ => return Err(self.error(id, "expression hors du sous-ensemble vérifié")),
        };
        self.coerce(id, value, expected, out)
    }

    fn coerce(
        &mut self,
        id: NodeId,
        value: Value,
        expected: Option<Ty>,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        if expected.is_some_and(|expected| {
            expected != value.ty && !reference_compatible(value.ty, expected)
        }) {
            return Err(self.error(id, "type incompatible"));
        }
        if let Some(expected) = expected
            && expected != value.ty
        {
            let mut narrowed = self.emit(expected, Expr::Temporary(value), out);
            narrowed.dependencies.loan = value.dependencies.loan;
            narrowed = narrowed.finish_evaluation(out);
            return Ok(narrowed);
        }
        Ok(value)
    }

    fn operator(&self, id: NodeId) -> &'a str {
        let index = self.node(id).name.unwrap();
        let span = self.tree.tokens[index].span;
        let next = self.tree.tokens[index + 1].span;
        if self.text(index) == ">" && span.end == next.start && matches!(self.text(index + 1), "=" | ">") {
            return &self.source[span.start..next.end];
        }
        self.text(index)
    }

    fn known_type(&mut self, id: NodeId) -> Option<Ty> {
        if let Some((ty, _)) = self.named_constant(id) { return Some(ty); }
        let node = self.node(id);
        match node.kind {
            "binaire" if matches!(self.operator(id), "<<" | ">>") => self.known_type(node.children[0]),
            "binaire" if self.operator(id) == "as" => self.ty(node.children[1]).ok(),
            "nom" => self.uses.get(&id).copied().and_then(|binding| {
                self.slots[binding.0].map(|slot| slot.ty).or_else(|| {
                    self.tree.bindings[binding.0]
                        .ty
                        .and_then(|ty| self.ty(ty).ok())
                })
            }),
            "groupe" | "unaire" if node.children.len() == 1 => self.known_type(node.children[0]),
            "appel" if self.node(node.children[0]).kind == "nom"
                && self.name(node.children[0]) == Some("addr") => self.usize_type(id).ok(),
            "appel méthode" if let Some((layout, _)) = self.variant_call(id) => Some(Ty::Struct(layout)),
            "appel" if let Some(layout) = self.explicit_conversion_target(id) => Some(Ty::Struct(layout)),
            "appel" => self.function_index(id)
                .map(|i| {
                    if self.signatures[i].asynchronous {
                        Ty::Future(i)
                    } else {
                        self.signatures[i].result
                    }
                }),
            "await" => match self.known_type(node.children[0])? {
                Ty::Future(index) => Some(self.signatures[index].result),
                Ty::Handle(layout, true) => Some(Ty::Struct(layout)),
                _ => None,
            },
            "propagation" => {
                let ty = self.known_type(node.children[0])?;
                let (layout, _) = self.propagation_layout(ty)?;
                Some(self.structures[layout].variants[1].1.first().map_or(Ty::Void, |field| field.1))
            }
            "littéral" if matches!(self.name(id), Some("true" | "false")) => Some(Ty::Bool),
            "littéral" if self.tree.tokens[node.start].kind == crate::lexer::Kind::Text => Some(Ty::Str),
            _ => None,
        }
    }

    fn loop_result_type(&mut self, body: NodeId) -> Option<Ty> {
        let mut candidates = Vec::new();
        let mut pending = vec![body];
        while let Some(id) = pending.pop() {
            let node = self.node(id);
            match node.kind {
                "loop" | "while" | "closure" => {}
                "break" => {
                    if let Some(ty) = node
                        .children
                        .first()
                        .and_then(|&value| self.known_type(value))
                    {
                        if !candidates.contains(&ty) {
                            candidates.push(ty);
                        }
                    }
                }
                _ => pending.extend(&node.children),
            }
        }
        if candidates.len() != 1 || candidates[0] == Ty::Void {
            return None;
        }
        candidates.first().copied()
    }

    fn float_zero(&self, id: NodeId) -> bool {
        if let Some((_, literal)) = self.named_constant(id) {
            return self.float_zero(literal);
        }
        let node = self.node(id);
        match node.kind {
            "groupe" => node.children.first().is_some_and(|&id| self.float_zero(id)),
            "unaire" if self.name(id) == Some("-") => self.float_zero(node.children[0]),
            "littéral" if self.tree.tokens[node.start].kind == crate::lexer::Kind::Float => self
                .name(id)
                .unwrap()
                .parse::<f64>()
                .is_ok_and(|value| value == 0.0),
            _ => false,
        }
    }

    fn integer(
        &mut self,
        id: NodeId,
        negative: bool,
        expected: Option<Ty>,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let text = self
            .name(id)
            .ok_or_else(|| self.error(id, "entier attendu"))?;
        if self.tree.tokens[self.node(id).start].kind == crate::lexer::Kind::Float {
            let ty = expected.unwrap_or(Ty::F64);
            if !ty.float() || text.contains(['e', 'E']) {
                return Err(self.error(id, "littéral flottant incompatible"));
            }
            let significand_nonzero = text.bytes().any(|byte| matches!(byte, b'1'..=b'9'));
            let parsed = if ty == Ty::F32 {
                text.parse::<f32>().ok().map(f64::from)
            } else {
                text.parse::<f64>().ok()
            };
            if !parsed
                .is_some_and(|value| value.is_finite() && (value != 0.0 || !significand_nonzero))
            {
                return Err(self.error(id, "littéral flottant hors limites"));
            }
            let literal = if text.contains('.') {
                text.to_owned()
            } else {
                format!("{text}.0")
            };
            let sign = if negative { "-" } else { "" };
            let suffix = if ty == Ty::F32 { "f" } else { "" };
            return Ok(self.emit(ty, Expr::Float(format!("{sign}{literal}{suffix}")), out));
        }
        let absolute = match text.strip_prefix("0x").or_else(|| text.strip_prefix("0X")) {
            Some(digits) => i128::from_str_radix(digits, 16),
            None => text.parse::<i128>(),
        }
        .map_err(|_| self.error(id, "entier attendu ou hors limites"))?;
        let number = if negative { -absolute } else { absolute };
        self.checked_integer(id, expected.unwrap_or(Ty::I64), number, out)
    }

    fn checked_integer(
        &mut self,
        id: NodeId,
        ty: Ty,
        number: i128,
        out: &mut Vec<Instr>,
    ) -> Result<Value, Error> {
        let value = match ty {
            Ty::I32 => i32::try_from(number).is_ok(),
            Ty::I64 => i64::try_from(number).is_ok(),
            Ty::U8 => u8::try_from(number).is_ok(),
            Ty::U16 => u16::try_from(number).is_ok(),
            Ty::U32 => u32::try_from(number).is_ok(),
            Ty::U64 => u64::try_from(number).is_ok(),
            Ty::Usize => match self.tree.target.pointer_width() {
                Some(32) => u32::try_from(number).is_ok(),
                Some(64) => u64::try_from(number).is_ok(),
                _ => false,
            },
            _ => false,
        };
        if !value {
            return Err(self.error(id, "littéral entier incompatible ou hors limites"));
        }
        Ok(self.emit(ty, Expr::Integer(number), out))
    }
}

pub(crate) fn layout_dependencies(layout: &Structure) -> impl Iterator<Item = usize> + '_ {
    layout
        .fields
        .iter()
        .chain(layout.variants.iter().flat_map(|(_, fields)| fields))
        .map(|(_, ty)| *ty)
        .chain(layout.array.or(layout.pool).map(|(element, _)| element))
        .filter_map(|ty| match ty {
            Ty::Struct(index) => Some(index),
            _ => None,
        })
}

fn layout_acyclic(index: usize, layouts: &[Structure], states: &mut [u8]) -> bool {
    match states[index] {
        1 => return false,
        2 => return true,
        _ => {}
    }
    states[index] = 1;
    if !layout_dependencies(&layouts[index]).all(|child| layout_acyclic(child, layouts, states)) {
        return false;
    }
    states[index] = 2;
    true
}

// Only bindings present in the receiving scope can cross its control edge.
// References cannot be reassigned in this subset, so their origin is invariant.

fn capture_type(ty: Ty) -> bool {
    ty.scalar().is_some() || matches!(ty, Ty::Ref { target, .. } if target.ty().scalar().is_some())
}

pub(crate) fn owns_pool_slots(ty: Ty, layouts: &[Structure]) -> bool {
    match ty {
        Ty::Allocation(_) => true,
        Ty::Struct(index) => {
            let layout = &layouts[index];
            matches!(layout.growing, Some(Growing::Map(_, Ty::Allocation(_))))
                || layout
                .fields
                .iter()
                .chain(layout.variants.iter().flat_map(|(_, fields)| fields))
                .any(|(_, ty)| owns_pool_slots(*ty, layouts))
                || layout
                    .array
                    .is_some_and(|(ty, len)| len != 0 && owns_pool_slots(ty, layouts))
        }
        _ => false,
    }
}

pub(crate) fn contains_handle(ty: Ty, layouts: &[Structure]) -> bool {
    match ty {
        Ty::Handle(..) => true,
        Ty::Struct(index) => {
            let layout = &layouts[index];
            layout.fields.iter().chain(layout.variants.iter().flat_map(|(_, fields)| fields))
                .any(|(_, ty)| contains_handle(*ty, layouts))
                || layout.array.is_some_and(|(ty, len)| len != 0 && contains_handle(ty, layouts))
        }
        _ => false,
    }
}

pub(crate) fn inline_destructor(ty: Ty, layouts: &[Structure]) -> bool {
    let Ty::Struct(index) = ty else { return false };
    let layout = &layouts[index];
    layout.destructor.is_some()
        || layout.fields.iter().chain(layout.variants.iter().flat_map(|(_, fields)| fields))
            .any(|(_, ty)| inline_destructor(*ty, layouts))
        || layout.array.is_some_and(|(ty, len)| len != 0 && inline_destructor(ty, layouts))
}

fn structurally_replicable(ty: Ty, layouts: &[Structure]) -> bool {
    if ty.scalar().is_some() {
        return true;
    }
    let Ty::Struct(index) = ty else { return false };
    let layout = &layouts[index];
    layout.destructor.is_none()
        && layout.array.is_none()
        && layout.pool.is_none()
        && layout.growing.is_none()
        && layout.variants.is_empty()
        && layout.fields.iter().all(|(_, field)| structurally_replicable(*field, layouts))
}

fn option_item_supported(ty: Ty) -> bool {
    !matches!(ty, Ty::Void | Ty::Pool(_) | Ty::Future(_))
}

fn owns_resources(ty: Ty, layouts: &[Structure]) -> bool {
    match ty {
        Ty::Allocation(_) | Ty::Handle(..) => true,
        Ty::Struct(index) => {
            let layout = &layouts[index];
            layout.destructor.is_some() || matches!(layout.growing, Some(Growing::Map(..)))
                || layout.fields.iter()
                    .chain(layout.variants.iter().flat_map(|(_, fields)| fields))
                    .any(|(_, ty)| owns_resources(*ty, layouts))
                || layout.array.is_some_and(|(ty, len)| len != 0 && owns_resources(ty, layouts))
        }
        _ => false,
    }
}

fn async_fixed(ty: Ty, layouts: &[Structure]) -> bool {
    capture_type(ty)
        || match ty {
            Ty::Allocation(_) | Ty::Handle(..) | Ty::Slice { .. } => true,
            Ty::Ref {
                target: Referent::Aggregate(_) | Referent::Pool(_) | Referent::Indirect { .. },
                ..
            } => true,
            Ty::Struct(index) => {
                let layout = &layouts[index];
                matches!(layout.growing, Some(Growing::Map(..))) || layout.pool.is_none()
                    && layout.growing.is_none()
                    && layout
                        .fields
                        .iter()
                        .chain(layout.variants.iter().flat_map(|(_, fields)| fields))
                        .all(|(_, ty)| async_fixed(*ty, layouts))
                    && layout.array.is_none_or(|(ty, _)| async_fixed(ty, layouts))
            }
            _ => false,
        }
}

fn async_region_body(body: &[Instr], layouts: &[Structure], std_io: bool) -> bool {
    let local = |ty: Ty| {
        async_fixed(ty, layouts)
            || match ty {
                Ty::Future(_) | Ty::Handle(_, true) => true,
                Ty::Struct(index) => layouts[index].pool.is_some(),
                Ty::Allocation(Referent::Aggregate(index)) => match layouts[index].growing {
                    Some(Growing::Vector(element)) => async_fixed(element, layouts),
                    Some(Growing::String) => true,
                    _ => false,
                },
                _ => false,
            }
    };
    body.iter().all(|instruction| match instruction {
        Instr::Evaluate(value, expression) => match expression {
            Expr::Call(_, _, CallKind::Ordinary) if std_io => local(value.ty),
            Expr::MapNew | Expr::MapGet(..) | Expr::MapInsert(..) | Expr::MapRemove(..) => true,
            Expr::PoolBorrow(_)
            | Expr::Await(_)
            | Expr::AwaitHandle(_)
            | Expr::SocketWait(..)
            | Expr::SocketCompletion(..)
            | Expr::FutureSpawn(_, true) => true,
            Expr::FutureNew(..)
            | Expr::Call(_, _, CallKind::ErrorConversion)
            | Expr::Call(_, _, CallKind::IoMetadata)
            | Expr::Call(_, _, CallKind::Pipeline)
            | Expr::Construct(_)
            | Expr::Variant(..)
            | Expr::Array(..)
            | Expr::Field(..)
            | Expr::Index(..)
            | Expr::IsVariant(..)
            | Expr::VariantField(..)
            | Expr::TakeVariantField(..)
            | Expr::TakeTupleField(..)
            | Expr::PoolNew(..)
            | Expr::PoolTake(..)
            | Expr::PoolRead(..)
            | Expr::BorrowField(..)
            | Expr::BorrowIndex(..)
            | Expr::BorrowVariantField(..) => local(value.ty),
            Expr::Pool
            | Expr::PoolGrowing(_)
            | Expr::GrowingLen(..)
            | Expr::VectorExtract(..)
            | Expr::GrowingIndex(..)
            | Expr::Integer(_)
            | Expr::Float(_)
            | Expr::Boolean(_)
            | Expr::Local(_)
            | Expr::Temporary(_)
            | Expr::Dereference(_)
            | Expr::DereferenceValue(_)
            | Expr::Address(_)
            | Expr::Slice(..)
            | Expr::GrowingSlice(..)
            | Expr::Subslice(..)
            | Expr::SliceLen(_)
            | Expr::SliceElementAddress(..)
            | Expr::SliceElement(_)
            | Expr::SliceElementBorrow(_)
            | Expr::BorrowThrough(_)
            | Expr::Borrow(_)
            | Expr::Reborrow(_)
            | Expr::Shift(..)
            | Expr::Cast(_)
            | Expr::Unary(..)
            | Expr::Binary(..) => local(value.ty),
            _ => false,
        },
        Instr::Bind(_, value)
        | Instr::Write(_, value)
        | Instr::WriteThrough(_, value)
        | Instr::WriteNested(_, value)
        | Instr::WriteSliceElement(_, value)
        | Instr::WriteIndex(_, _, value)
        | Instr::Print(value)
        | Instr::Reserve(value)
        | Instr::Discard(value)
        | Instr::DropAllocation(value)
        | Instr::DropOwned(value) => local(value.ty),
        Instr::Receive(receiver, value) => local(receiver.ty) && local(value.ty),
        Instr::Block(body) => async_region_body(body, layouts, std_io),
        Instr::If(_, yes, no) => async_region_body(yes, layouts, std_io) && async_region_body(no, layouts, std_io),
        Instr::Loop {
            condition, body, ..
        } => async_region_body(condition, layouts, std_io) && async_region_body(body, layouts, std_io),
        Instr::Break(_)
        | Instr::Continue
        | Instr::Return(_)
        | Instr::FreePages
        | Instr::RegionScope { .. }
        | Instr::GrowingPush(..)
        | Instr::GrowingText(..) | Instr::DropMap(_) => true,
        Instr::Call(_, arguments) if std_io => arguments.iter().all(|value| local(value.ty)),
        Instr::Yield | Instr::CheckIndex(..) | Instr::Assembly(_) => true,
        Instr::DropHandle(value) => matches!(value.ty, Ty::Future(_) | Ty::Handle(_, true)),
        _ => false,
    })
}

fn reference_compatible(actual: Ty, expected: Ty) -> bool {
    matches!((actual, expected),
        (Ty::Ref { target: left, mutable: source }, Ty::Ref { target: right, mutable: destination })
        if left == right && (source || !destination))
}
