//! Verification of already-resolved scalar/check operands. This evaluates facts;
//! it does not infer types or select operators/conversions.
use super::*;
impl Checker<'_> {
    fn known_integer(&self, value: ValueId, seen: &mut HashSet<ValueId>) -> Option<i128> {
        if !seen.insert(value) {
            return None;
        }
        let v = &self.p.values.entries[value.0 as usize];
        let constant = match v.definition {
            ValueDefinition::Constant(c) => {
                Some(&self.p.declarations.constants[c.0 as usize].value)
            }
            ValueDefinition::ConfiguredConstant { ref value, .. } => Some(value),
            _ => None,
        };
        let result = if let Some(c) = constant {
            match c {
                ConstantValue::Integer(n) => Some(*n),
                ConstantValue::Unsigned(n) => i128::try_from(*n).ok(),
                _ => None,
            }
        } else {
            match &self.p.values.provenance[v.provenance.0 as usize].kind {
                ProvenanceKind::Copy { source, .. }
                | ProvenanceKind::Forward { source, .. }
                | ProvenanceKind::Move { source, .. } => self.known_integer(*source, seen),
                ProvenanceKind::PlaceRead {
                    root_value: Some(source),
                    ..
                } => self.known_integer(*source, seen),
                ProvenanceKind::Merge(values) => {
                    let mut all = std::iter::once(&values.first)
                        .chain(&values.rest)
                        .map(|v| self.known_integer(v.value, &mut seen.clone()));
                    let first = all.next().flatten();
                    if all.all(|n| n == first) { first } else { None }
                }
                _ => {
                    let operation = match v.definition {
                        ValueDefinition::OperationResult { operation, .. }
                        | ValueDefinition::ConditionalResult { operation, .. } => {
                            self.facts.operations.get(&operation).copied()
                        }
                        _ => None,
                    };
                    operation.and_then(|op| {
                        macro_rules! binary {
                            ($x:expr,$method:ident) => {{
                                let a = self.known_integer($x.left, &mut seen.clone())?;
                                let b = self.known_integer($x.right, &mut seen.clone())?;
                                a.$method(b)
                            }};
                        }
                        match op {
                            Operation::IntegerLiteral(x) => match x.value {
                                IntegerConstant::Signed(n) => Some(n),
                                IntegerConstant::Unsigned(n) => i128::try_from(n).ok(),
                            },
                            Operation::CopyPrimitive(x) => self.known_integer(x.source, seen),
                            Operation::Add(x) => binary!(x, checked_add),
                            Operation::Subtract(x) => binary!(x, checked_sub),
                            Operation::Multiply(x) => binary!(x, checked_mul),
                            Operation::Divide(x) => binary!(x, checked_div),
                            Operation::Remainder(x) => binary!(x, checked_rem),
                            Operation::Negate(x) => {
                                self.known_integer(x.operand, seen)?.checked_neg()
                            }
                            Operation::NumericCast(x) => self.known_integer(x.source, seen),
                            Operation::SequenceLength(x) => {
                                let place = &self.p.objects.places[self.p.objects.evaluated_places
                                    [x.source.0 as usize]
                                    .definition
                                    .0
                                    as usize];
                                match self.p.types.entries[place.ty.0 as usize].kind {
                                    TypeDefinition::Array { length, .. } => Some(length as i128),
                                    _ => None,
                                }
                            }
                            _ => None,
                        }
                    })
                }
            }
        };
        seen.remove(&value);
        result
    }
    fn int(&self, v: ValueId) -> Option<i128> {
        self.known_integer(v, &mut HashSet::new())
    }
    fn within(&self, ty: TypeId, n: i128) -> bool {
        match self.p.types.entries[ty.0 as usize].kind {
            TypeDefinition::Numeric(NumericType::I32) => i32::try_from(n).is_ok(),
            TypeDefinition::Numeric(NumericType::I64) => i64::try_from(n).is_ok(),
            TypeDefinition::Numeric(NumericType::U8) => u8::try_from(n).is_ok(),
            TypeDefinition::Numeric(NumericType::U16) => u16::try_from(n).is_ok(),
            TypeDefinition::Numeric(NumericType::U32) => u32::try_from(n).is_ok(),
            TypeDefinition::Numeric(NumericType::U64) => u64::try_from(n).is_ok(),
            TypeDefinition::Numeric(NumericType::Usize) => {
                n >= 0 && (n as u128) < (1u128 << self.p.target.pointer_bits)
            }
            _ => true,
        }
    }
    pub(super) fn check_runtime_requirements(&mut self) {
        for obligation in self.p.obligations.n1.clone() {
            let InitializationAndTypeRequirement::RuntimeCheck { check: id } =
                obligation.requirement
            else {
                continue;
            };
            let Some(check) = self.p.runtime_checks.iter().find(|check| match check {
                RuntimeCheck::ZeroDivisor(check) => check.id == id,
                RuntimeCheck::ShiftCount(check) => check.id == id,
                RuntimeCheck::IndexBounds(check) => check.id == id,
                RuntimeCheck::SliceBounds(check) => check.id == id,
                RuntimeCheck::IntegerOverflow(check) => check.id == id,
                RuntimeCheck::ExactConversion(check) => check.id == id,
                RuntimeCheck::Utf8Boundary(check) => check.id == id,
                RuntimeCheck::Capacity(check) => check.id == id,
                RuntimeCheck::Utf8(check) => check.id == id,
                RuntimeCheck::Variant(check) => check.id == id,
                RuntimeCheck::Unwrap(check) => check.id == id,
                RuntimeCheck::PoolCapacity { id: found, .. } => *found == id,
            }) else {
                let site = self.site_at(obligation.site.moment);
                self.unproved_obligation(
                    obligation.site.id,
                    CoreRule::N1,
                    &site,
                    "the declared runtime-check requirement is missing from PostAST",
                );
                continue;
            };
            let valid = match check {
                RuntimeCheck::ZeroDivisor(c) => self.int(c.divisor).map(|n| n != 0),
                RuntimeCheck::ShiftCount(c) => {
                    self.int(c.count).map(|n| n >= 0 && n < i128::from(c.width))
                }
                RuntimeCheck::IndexBounds(c) => self
                    .int(c.index)
                    .zip(self.int(c.length))
                    .map(|(i, n)| i >= 0 && i < n),
                RuntimeCheck::SliceBounds(c) => self
                    .int(c.start)
                    .zip(self.int(c.end))
                    .zip(self.int(c.length))
                    .map(|((a, b), n)| a >= 0 && a <= b && b <= n),
                RuntimeCheck::IntegerOverflow(c) => {
                    let result = self
                        .facts
                        .operations
                        .get(&c.operation)
                        .and_then(|o| match o {
                            Operation::Add(x) => Some(x.result),
                            Operation::Subtract(x) => Some(x.result),
                            Operation::Multiply(x) => Some(x.result),
                            Operation::Divide(x) => Some(x.result),
                            Operation::Remainder(x) => Some(x.result),
                            Operation::Negate(x) => Some(x.result),
                            _ => None,
                        });
                    result
                        .and_then(|v| self.int(v))
                        .map(|n| self.within(c.ty, n))
                }
                RuntimeCheck::ExactConversion(c) => {
                    self.int(c.value).map(|n| self.within(c.target, n))
                }
                RuntimeCheck::Utf8Boundary(_)
                | RuntimeCheck::Capacity(_)
                | RuntimeCheck::Utf8(_)
                | RuntimeCheck::Variant(_)
                | RuntimeCheck::Unwrap(_)
                | RuntimeCheck::PoolCapacity { .. } => None,
            };
            let site = self.site_at(obligation.site.moment);
            if !self.guard(&site).possible() {
                self.prove_obligation(
                    obligation.site.id,
                    EvidenceFacts::RuntimeCheck { check: id },
                );
                continue;
            }
            if valid == Some(false) {
                self.reject_obligation(
                    obligation.site.id,
                    CoreRule::N1,
                    &site,
                    "statically known check fails: bound, divisor, overflow or conversion is invalid",
                    vec![],
                );
                continue;
            }
            let failure = self
                .p
                .bodies
                .iter()
                .flat_map(|b| &b.operations)
                .find_map(|o| {
                    if let Operation::RuntimeCheckOperation(x) = o {
                        (x.requirement == id).then(|| x.failure.clone())
                    } else {
                        None
                    }
                })
                .unwrap_or(FailureContinuation::Abort {
                    origin: site.origin,
                });
            // Runtime checks remain explicit even when proven constant-safe;
            // a later optimization may consume proof evidence to remove them.
            self.derived
                .checks
                .push(CheckDisposition::Runtime { check: id, failure });
            self.prove_obligation(
                obligation.site.id,
                EvidenceFacts::RuntimeCheck { check: id },
            );
        }
    }
}
