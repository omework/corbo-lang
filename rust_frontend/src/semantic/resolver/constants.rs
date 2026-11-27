//! Constant dependency resolution and arithmetic. Consumes parsed expressions only.
use super::*;
impl Resolver<'_> {
    pub(super) fn resolve_constant(&mut self, id: ConstantId) -> Result<ConstantValue> {
        if let Some(value) = self.override_value(id) {
            return Ok(value);
        }
        if let Some(value) = self
            .configured_constants
            .get(&(self.active_configuration, id))
        {
            return Ok(value.clone());
        }
        if self.active_configuration == ConfigurationId(0) && self.constant_done.contains(&id) {
            return Ok(self.p.declarations.constants[id.0 as usize].value.clone());
        }
        let Some((node, scope, unit)) = self.constant_sources.get(&id).copied() else {
            return Ok(self.p.declarations.constants[id.0 as usize].value.clone());
        };
        let caller_unit = self.current_unit;
        self.switch_unit(unit);
        if !self.constant_active.insert((self.active_configuration, id)) {
            return Err(self.fail(
                node,
                DiagnosticKind::InvalidType,
                "cyclic constant dependency",
            ));
        }
        let NodeKind::Constant { value, .. } = self.kind(node) else {
            unreachable!()
        };
        let ty = self.p.declarations.constants[id.0 as usize].ty;
        let result = self.constant_expression(*value, ty, scope)?;
        if self.active_configuration == ConfigurationId(0) {
            self.p.declarations.constants[id.0 as usize].value = result.clone();
        }
        self.configured_constants
            .insert((self.active_configuration, id), result.clone());
        self.constant_active
            .remove(&(self.active_configuration, id));
        self.constant_done.insert(id);
        self.switch_unit(caller_unit);
        Ok(result)
    }
    pub(super) fn integer_constant(&mut self, n: ast::NodeId, scope: ScopeId) -> Result<u64> {
        let value = if let NodeKind::Literal { token } = self.kind(n) {
            let text = self.text(*token);
            if let Some(hex) = text.strip_prefix("0x").or_else(|| text.strip_prefix("0X")) {
                u64::from_str_radix(hex, 16).ok()
            } else {
                text.parse::<u64>().ok()
            }
        } else if let NodeKind::Path { segments, .. } = self.kind(n) {
            let symbol = self.scoped_path(n, scope, segments)?;
            let SymbolDefinition::Constant(id) =
                self.p.symbols.entries[symbol.0 as usize].definition
            else {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    "array length must name an integer constant",
                ));
            };
            match self.resolve_constant(id)? {
                ConstantValue::Unsigned(v) => u64::try_from(v).ok(),
                ConstantValue::Integer(v) => u64::try_from(v).ok(),
                _ => None,
            }
        } else {
            None
        };
        value.ok_or_else(|| {
            self.fail(
                n,
                DiagnosticKind::InvalidType,
                "expected a nonnegative compile-time integer fitting u64",
            )
        })
    }
    fn bounded_constant(
        &self,
        n: ast::NodeId,
        ty: TypeId,
        value: ConstantValue,
    ) -> Result<ConstantValue> {
        let valid = match (&self.p.types.entries[ty.0 as usize].kind, &value) {
            (TypeDefinition::Numeric(domain), ConstantValue::Integer(v)) => {
                let (min, max) = match domain {
                    NumericType::I32 => (i32::MIN as i128, i32::MAX as i128),
                    NumericType::I64 => (i64::MIN as i128, i64::MAX as i128),
                    NumericType::U8 => (0, u8::MAX as i128),
                    NumericType::U16 => (0, u16::MAX as i128),
                    NumericType::U32 => (0, u32::MAX as i128),
                    NumericType::U64 => (0, u64::MAX as i128),
                    NumericType::Usize => (
                        0,
                        if self.p.target.pointer_bits == 32 {
                            u32::MAX as i128
                        } else {
                            u64::MAX as i128
                        },
                    ),
                    _ => {
                        return Err(self.fail(
                            n,
                            DiagnosticKind::TypeMismatch,
                            "integer constant requires an integer type",
                        ));
                    }
                };
                *v >= min && *v <= max
            }
            (TypeDefinition::Boolean, ConstantValue::Boolean(_)) => true,
            (TypeDefinition::Reference { target, .. }, ConstantValue::Utf8(_)) => matches!(
                self.p.types.entries[target.0 as usize].kind,
                TypeDefinition::StrData
            ),
            (TypeDefinition::Numeric(NumericType::F32), ConstantValue::Float32(v)) => {
                f32::from_bits(*v).is_finite()
            }
            (TypeDefinition::Numeric(NumericType::F64), ConstantValue::Float64(v)) => {
                f64::from_bits(*v).is_finite()
            }
            _ => false,
        };
        if valid {
            Ok(value)
        } else {
            Err(self.fail(
                n,
                DiagnosticKind::TypeMismatch,
                format!("constant does not fit {}", self.type_name(ty)),
            ))
        }
    }
    pub(super) fn constant_expression(
        &mut self,
        n: ast::NodeId,
        ty: TypeId,
        scope: ScopeId,
    ) -> Result<ConstantValue> {
        let value = match self.kind(n) {
            NodeKind::Literal { token } => {
                let text = self.text(*token);
                match &self.p.types.entries[ty.0 as usize].kind {
                    TypeDefinition::Boolean => match text {
                        "true" => ConstantValue::Boolean(true),
                        "false" => ConstantValue::Boolean(false),
                        _ => {
                            return Err(self.fail(
                                n,
                                DiagnosticKind::TypeMismatch,
                                "expected a bool constant",
                            ));
                        }
                    },
                    TypeDefinition::Reference { .. } => match &self.syntax.tokens[token.index]
                        .payload
                    {
                        crate::lexer::Payload::Text(bytes) => ConstantValue::Utf8(bytes.clone()),
                        _ => {
                            return Err(self.fail(
                                n,
                                DiagnosticKind::TypeMismatch,
                                "expected a text constant",
                            ));
                        }
                    },
                    TypeDefinition::Numeric(NumericType::F32) => ConstantValue::Float32(
                        text.parse::<f32>()
                            .map_err(|_| {
                                self.fail(n, DiagnosticKind::TypeMismatch, "invalid f32 constant")
                            })?
                            .to_bits(),
                    ),
                    TypeDefinition::Numeric(NumericType::F64) => ConstantValue::Float64(
                        text.parse::<f64>()
                            .map_err(|_| {
                                self.fail(n, DiagnosticKind::TypeMismatch, "invalid f64 constant")
                            })?
                            .to_bits(),
                    ),
                    TypeDefinition::Numeric(_) => {
                        ConstantValue::Integer(self.integer_constant(n, scope)? as i128)
                    }
                    _ => {
                        return Err(self.fail(
                            n,
                            DiagnosticKind::InvalidType,
                            "constants require a primitive or &str type",
                        ));
                    }
                }
            }
            NodeKind::Parenthesized { expression } => {
                return self.constant_expression(*expression, ty, scope);
            }
            NodeKind::Path { segments, .. } => {
                let symbol = self.scoped_path(n, scope, segments)?;
                let SymbolDefinition::Constant(id) =
                    self.p.symbols.entries[symbol.0 as usize].definition
                else {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidType,
                        "constant expression names a non-constant",
                    ));
                };
                self.require_type(n, self.p.declarations.constants[id.0 as usize].ty, ty)?;
                self.resolve_constant(id)?
            }
            NodeKind::Unary {
                operator, operand, ..
            } if self.text(*operator) == "-" => {
                // Apply sign before checking the type bound, including i64::MIN.
                let operand = if matches!(self.kind(*operand),NodeKind::Literal{token} if self.syntax.tokens[token.index].kind==crate::lexer::Kind::Integer)
                {
                    ConstantValue::Integer(self.integer_constant(*operand, scope)? as i128)
                } else {
                    self.constant_expression(*operand, ty, scope)?
                };
                match operand {
                    ConstantValue::Integer(v) => ConstantValue::Integer(-v),
                    ConstantValue::Unsigned(v) => ConstantValue::Integer(-(v as i128)),
                    ConstantValue::Float32(v) => {
                        ConstantValue::Float32((-f32::from_bits(v)).to_bits())
                    }
                    ConstantValue::Float64(v) => {
                        ConstantValue::Float64((-f64::from_bits(v)).to_bits())
                    }
                    _ => {
                        return Err(self.fail(
                            n,
                            DiagnosticKind::TypeMismatch,
                            "negation requires a numeric constant",
                        ));
                    }
                }
            }
            NodeKind::Binary {
                operator,
                left,
                right,
            } => {
                let op = self.text(*operator);
                let a = self.constant_expression(*left, ty, scope)?;
                let b = self.constant_expression(*right, ty, scope)?;
                self.constant_binary(n, op, a, b)?
            }
            NodeKind::Call { callee, arguments } => {
                let NodeKind::Path { segments, .. } = self.kind(*callee) else {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidCall,
                        "only min/max are allowed in constant expressions",
                    ));
                };
                let name = if segments.len() == 1 {
                    self.text(segments[0])
                } else {
                    ""
                };
                if !matches!(name, "min" | "max") || arguments.len() != 2 {
                    return Err(self.fail(
                        n,
                        DiagnosticKind::InvalidCall,
                        "constant min/max requires two arguments",
                    ));
                }
                let a = self.constant_expression(arguments[0], ty, scope)?;
                let b = self.constant_expression(arguments[1], ty, scope)?;
                self.constant_binary(n, name, a, b)?
            }
            _ => {
                return Err(self.fail(
                    n,
                    DiagnosticKind::InvalidType,
                    "expression is not in the constant-expression grammar",
                ));
            }
        };
        self.bounded_constant(n, ty, value)
    }
    fn constant_binary(
        &self,
        n: ast::NodeId,
        op: &str,
        a: ConstantValue,
        b: ConstantValue,
    ) -> Result<ConstantValue> {
        let error = || {
            self.fail(
                n,
                DiagnosticKind::InvalidType,
                "constant arithmetic overflow, zero divisor, or invalid operand",
            )
        };
        match (a, b) {
            (ConstantValue::Integer(a), ConstantValue::Integer(b)) => Ok(ConstantValue::Integer(
                match op {
                    "+" => a.checked_add(b),
                    "-" => a.checked_sub(b),
                    "*" => a.checked_mul(b),
                    "/" => a.checked_div(b),
                    "%" => a.checked_rem(b),
                    "min" => Some(a.min(b)),
                    "max" => Some(a.max(b)),
                    _ => None,
                }
                .ok_or_else(error)?,
            )),
            (ConstantValue::Float32(a), ConstantValue::Float32(b)) => {
                let (a, b) = (f32::from_bits(a), f32::from_bits(b));
                if matches!(op, "/" | "%") && b == 0.0 {
                    return Err(error());
                }
                Ok(ConstantValue::Float32(
                    match op {
                        "+" => a + b,
                        "-" => a - b,
                        "*" => a * b,
                        "/" => a / b,
                        "%" => a % b,
                        "min" => a.min(b),
                        "max" => a.max(b),
                        _ => return Err(error()),
                    }
                    .to_bits(),
                ))
            }
            (ConstantValue::Float64(a), ConstantValue::Float64(b)) => {
                let (a, b) = (f64::from_bits(a), f64::from_bits(b));
                if matches!(op, "/" | "%") && b == 0.0 {
                    return Err(error());
                }
                Ok(ConstantValue::Float64(
                    match op {
                        "+" => a + b,
                        "-" => a - b,
                        "*" => a * b,
                        "/" => a / b,
                        "%" => a % b,
                        "min" => a.min(b),
                        "max" => a.max(b),
                        _ => return Err(error()),
                    }
                    .to_bits(),
                ))
            }
            _ => Err(error()),
        }
    }
}
