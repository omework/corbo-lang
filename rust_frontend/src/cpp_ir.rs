//! Typed C++ representation used by the C++ backend.
//!
//! This module contains no Corbo semantic resolution. `cpp_backend` is the
//! only producer and may construct these nodes solely from `PostAst` and the
//! physical memory plan carried by `PlannedPostAst`.

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TranslationUnit {
    pub includes: Vec<Include>,
    pub declarations: Vec<Declaration>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Include {
    System(&'static str),
    Local(String),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Declaration {
    Namespace(Namespace),
    TypeAlias(TypeAlias),
    Record(Record),
    Function(Function),
    Verbatim(String),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Namespace {
    pub name: String,
    pub declarations: Vec<Declaration>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TypeAlias {
    pub name: String,
    pub target: Type,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Record {
    pub name: String,
    pub alignment: Option<u64>,
    pub fields: Vec<Field>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Field {
    pub name: String,
    pub ty: Type,
    pub initializer: Option<Expression>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Function {
    pub linkage: Linkage,
    pub result: Type,
    pub name: String,
    pub parameters: Vec<Parameter>,
    pub body: Option<Block>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Linkage {
    External,
    Internal,
    Inline,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Parameter {
    pub ty: Type,
    pub name: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Type {
    Void,
    Bool,
    Char,
    Signed {
        bits: u16,
    },
    Unsigned {
        bits: u16,
    },
    Float {
        bits: u16,
    },
    Size,
    Named(String),
    Pointer {
        mutable: bool,
        pointee: Box<Type>,
    },
    Array {
        element: Box<Type>,
        length: u64,
    },
    FunctionPointer {
        result: Box<Type>,
        parameters: Vec<Type>,
    },
}

impl Type {
    pub fn pointer_to(self, mutable: bool) -> Self {
        Self::Pointer {
            mutable,
            pointee: Box::new(self),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Block {
    pub statements: Vec<Statement>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Statement {
    Block(Block),
    Declare {
        ty: Type,
        name: String,
        initializer: Option<Expression>,
    },
    Expression(Expression),
    Assign {
        destination: Expression,
        source: Expression,
    },
    CopyBytes {
        destination: Expression,
        source: Expression,
        bytes: Expression,
    },
    ZeroBytes {
        destination: Expression,
        bytes: Expression,
    },
    If {
        condition: Expression,
        then_block: Block,
        else_block: Option<Block>,
    },
    While {
        condition: Expression,
        body: Block,
    },
    Switch {
        value: Expression,
        cases: Vec<SwitchCase>,
        default: Option<Block>,
    },
    Label(String),
    Goto(String),
    Return(Option<Expression>),
    Break,
    Continue,
    Verbatim(String),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SwitchCase {
    pub value: u64,
    pub body: Block,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Expression {
    Name(String),
    Boolean(bool),
    Signed(i128),
    Unsigned(u128),
    FloatBits {
        bits: u64,
        width: u16,
    },
    Null,
    StringLiteral(Vec<u8>),
    Unary {
        operator: UnaryOperator,
        operand: Box<Expression>,
    },
    Binary {
        operator: BinaryOperator,
        left: Box<Expression>,
        right: Box<Expression>,
    },
    Call {
        callee: Box<Expression>,
        arguments: Vec<Expression>,
    },
    Cast {
        ty: Type,
        value: Box<Expression>,
    },
    ReinterpretCast {
        ty: Type,
        value: Box<Expression>,
    },
    SizeOf(Type),
    ByteOffset {
        base: Box<Expression>,
        bytes: Box<Expression>,
    },
    Member {
        base: Box<Expression>,
        member: String,
        through_pointer: bool,
    },
    Index {
        base: Box<Expression>,
        index: Box<Expression>,
    },
    Conditional {
        condition: Box<Expression>,
        when_true: Box<Expression>,
        when_false: Box<Expression>,
    },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UnaryOperator {
    AddressOf,
    Dereference,
    Negate,
    LogicalNot,
    BitNot,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BinaryOperator {
    Add,
    Subtract,
    Multiply,
    Divide,
    Remainder,
    BitAnd,
    BitOr,
    BitXor,
    ShiftLeft,
    ShiftRight,
    Equal,
    NotEqual,
    Less,
    LessEqual,
    Greater,
    GreaterEqual,
    LogicalAnd,
    LogicalOr,
}

pub fn render(unit: &TranslationUnit) -> String {
    let mut renderer = Renderer {
        output: String::new(),
        indentation: 0,
    };
    renderer.translation_unit(unit);
    renderer.output
}

struct Renderer {
    output: String,
    indentation: usize,
}

impl Renderer {
    fn translation_unit(&mut self, unit: &TranslationUnit) {
        for include in &unit.includes {
            match include {
                Include::System(path) => self.line(&format!("#include <{path}>")),
                Include::Local(path) => self.line(&format!("#include \"{path}\"")),
            }
        }
        self.line("");
        for declaration in &unit.declarations {
            self.declaration(declaration);
        }
    }

    fn declaration(&mut self, declaration: &Declaration) {
        match declaration {
            Declaration::Namespace(namespace) => {
                self.line(&format!("namespace {} {{", namespace.name));
                self.indentation += 1;
                for declaration in &namespace.declarations {
                    self.declaration(declaration);
                }
                self.indentation -= 1;
                self.line(&format!("}} // namespace {}", namespace.name));
            }
            Declaration::TypeAlias(alias) => {
                self.line(&format!(
                    "using {} = {};",
                    alias.name,
                    self.ty(&alias.target, None)
                ));
            }
            Declaration::Record(record) => {
                let alignment = record
                    .alignment
                    .map(|value| format!("alignas({value}) "))
                    .unwrap_or_default();
                self.line(&format!("struct {alignment}{} {{", record.name));
                self.indentation += 1;
                for field in &record.fields {
                    let initializer = field
                        .initializer
                        .as_ref()
                        .map(|value| format!(" = {}", self.expression(value)))
                        .unwrap_or_default();
                    self.line(&format!(
                        "{}{};",
                        self.ty(&field.ty, Some(&field.name)),
                        initializer
                    ));
                }
                self.indentation -= 1;
                self.line("};");
            }
            Declaration::Function(function) => self.function(function),
            Declaration::Verbatim(source) => {
                for line in source.lines() {
                    self.line(line);
                }
            }
        }
    }

    fn function(&mut self, function: &Function) {
        let linkage = match function.linkage {
            Linkage::External => "",
            Linkage::Internal => "static ",
            Linkage::Inline => "static inline ",
        };
        let parameters = function
            .parameters
            .iter()
            .map(|parameter| self.ty(&parameter.ty, Some(&parameter.name)))
            .collect::<Vec<_>>()
            .join(", ");
        let head = format!(
            "{linkage}{} {}({parameters})",
            self.ty(&function.result, None),
            function.name
        );
        match &function.body {
            None => self.line(&format!("{head};")),
            Some(body) => {
                self.line(&format!("{head} {{"));
                self.indentation += 1;
                self.block_contents(body);
                self.indentation -= 1;
                self.line("}");
            }
        }
    }

    fn block_contents(&mut self, block: &Block) {
        for statement in &block.statements {
            self.statement(statement);
        }
    }

    fn statement(&mut self, statement: &Statement) {
        match statement {
            Statement::Block(block) => {
                self.line("{");
                self.indentation += 1;
                self.block_contents(block);
                self.indentation -= 1;
                self.line("}");
            }
            Statement::Declare {
                ty,
                name,
                initializer,
            } => {
                let initializer = initializer
                    .as_ref()
                    .map(|value| format!(" = {}", self.expression(value)))
                    .unwrap_or_default();
                self.line(&format!("{}{};", self.ty(ty, Some(name)), initializer));
            }
            Statement::Expression(expression) => {
                self.line(&format!("{};", self.expression(expression)))
            }
            Statement::Assign {
                destination,
                source,
            } => self.line(&format!(
                "{} = {};",
                self.expression(destination),
                self.expression(source)
            )),
            Statement::CopyBytes {
                destination,
                source,
                bytes,
            } => self.line(&format!(
                "std::memcpy({}, {}, {});",
                self.expression(destination),
                self.expression(source),
                self.expression(bytes)
            )),
            Statement::ZeroBytes { destination, bytes } => self.line(&format!(
                "std::memset({}, 0, {});",
                self.expression(destination),
                self.expression(bytes)
            )),
            Statement::If {
                condition,
                then_block,
                else_block,
            } => {
                self.line(&format!("if ({}) {{", self.expression(condition)));
                self.indentation += 1;
                self.block_contents(then_block);
                self.indentation -= 1;
                if let Some(else_block) = else_block {
                    self.line("} else {");
                    self.indentation += 1;
                    self.block_contents(else_block);
                    self.indentation -= 1;
                }
                self.line("}");
            }
            Statement::While { condition, body } => {
                self.line(&format!("while ({}) {{", self.expression(condition)));
                self.indentation += 1;
                self.block_contents(body);
                self.indentation -= 1;
                self.line("}");
            }
            Statement::Switch {
                value,
                cases,
                default,
            } => {
                self.line(&format!("switch ({}) {{", self.expression(value)));
                self.indentation += 1;
                for case in cases {
                    self.line(&format!("case {}:", case.value));
                    self.indentation += 1;
                    self.block_contents(&case.body);
                    self.indentation -= 1;
                }
                if let Some(default) = default {
                    self.line("default:");
                    self.indentation += 1;
                    self.block_contents(default);
                    self.indentation -= 1;
                }
                self.indentation -= 1;
                self.line("}");
            }
            Statement::Label(name) => {
                self.indentation = self.indentation.saturating_sub(1);
                self.line(&format!("{name}:"));
                self.indentation += 1;
            }
            Statement::Goto(name) => self.line(&format!("goto {name};")),
            Statement::Return(value) => match value {
                Some(value) => self.line(&format!("return {};", self.expression(value))),
                None => self.line("return;"),
            },
            Statement::Break => self.line("break;"),
            Statement::Continue => self.line("continue;"),
            Statement::Verbatim(source) => {
                for line in source.lines() {
                    self.line(line);
                }
            }
        }
    }

    fn expression(&self, expression: &Expression) -> String {
        match expression {
            Expression::Name(name) => name.clone(),
            Expression::Boolean(value) => value.to_string(),
            Expression::Signed(value) => value.to_string(),
            Expression::Unsigned(value) => format!("{value}u"),
            Expression::FloatBits { bits, width } => match width {
                32 => format!("std::bit_cast<float>(std::uint32_t{{{bits}}})"),
                64 => format!("std::bit_cast<double>(std::uint64_t{{{bits}}})"),
                _ => unreachable!("PostAST only defines f32 and f64"),
            },
            Expression::Null => "nullptr".to_owned(),
            Expression::StringLiteral(bytes) => {
                let escaped = bytes
                    .iter()
                    .map(|byte| format!("\\x{byte:02x}"))
                    .collect::<String>();
                format!("\"{escaped}\"")
            }
            Expression::Unary { operator, operand } => {
                let operator = match operator {
                    UnaryOperator::AddressOf => "&",
                    UnaryOperator::Dereference => "*",
                    UnaryOperator::Negate => "-",
                    UnaryOperator::LogicalNot => "!",
                    UnaryOperator::BitNot => "~",
                };
                format!("({operator}{})", self.expression(operand))
            }
            Expression::Binary {
                operator,
                left,
                right,
            } => {
                let operator = match operator {
                    BinaryOperator::Add => "+",
                    BinaryOperator::Subtract => "-",
                    BinaryOperator::Multiply => "*",
                    BinaryOperator::Divide => "/",
                    BinaryOperator::Remainder => "%",
                    BinaryOperator::BitAnd => "&",
                    BinaryOperator::BitOr => "|",
                    BinaryOperator::BitXor => "^",
                    BinaryOperator::ShiftLeft => "<<",
                    BinaryOperator::ShiftRight => ">>",
                    BinaryOperator::Equal => "==",
                    BinaryOperator::NotEqual => "!=",
                    BinaryOperator::Less => "<",
                    BinaryOperator::LessEqual => "<=",
                    BinaryOperator::Greater => ">",
                    BinaryOperator::GreaterEqual => ">=",
                    BinaryOperator::LogicalAnd => "&&",
                    BinaryOperator::LogicalOr => "||",
                };
                format!(
                    "({} {operator} {})",
                    self.expression(left),
                    self.expression(right)
                )
            }
            Expression::Call { callee, arguments } => format!(
                "{}({})",
                self.expression(callee),
                arguments
                    .iter()
                    .map(|argument| self.expression(argument))
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
            Expression::Cast { ty, value } => {
                format!(
                    "static_cast<{}>({})",
                    self.ty(ty, None),
                    self.expression(value)
                )
            }
            Expression::ReinterpretCast { ty, value } => format!(
                "reinterpret_cast<{}>({})",
                self.ty(ty, None),
                self.expression(value)
            ),
            Expression::SizeOf(ty) => format!("sizeof({})", self.ty(ty, None)),
            Expression::ByteOffset { base, bytes } => format!(
                "(reinterpret_cast<unsigned char*>({}) + {})",
                self.expression(base),
                self.expression(bytes)
            ),
            Expression::Member {
                base,
                member,
                through_pointer,
            } => format!(
                "{}{}{}",
                self.expression(base),
                if *through_pointer { "->" } else { "." },
                member
            ),
            Expression::Index { base, index } => {
                format!("{}[{}]", self.expression(base), self.expression(index))
            }
            Expression::Conditional {
                condition,
                when_true,
                when_false,
            } => format!(
                "({} ? {} : {})",
                self.expression(condition),
                self.expression(when_true),
                self.expression(when_false)
            ),
        }
    }

    fn ty(&self, ty: &Type, name: Option<&str>) -> String {
        let name = name.unwrap_or("");
        match ty {
            Type::Void => format!("void{}", if name.is_empty() { "" } else { " " }) + name,
            Type::Bool => format!("bool{}", if name.is_empty() { "" } else { " " }) + name,
            Type::Char => format!("char{}", if name.is_empty() { "" } else { " " }) + name,
            Type::Signed { bits } => {
                format!("std::int{bits}_t{}", if name.is_empty() { "" } else { " " }) + name
            }
            Type::Unsigned { bits } => {
                format!(
                    "std::uint{bits}_t{}",
                    if name.is_empty() { "" } else { " " }
                ) + name
            }
            Type::Float { bits: 32 } => {
                format!("float{}", if name.is_empty() { "" } else { " " }) + name
            }
            Type::Float { bits: 64 } => {
                format!("double{}", if name.is_empty() { "" } else { " " }) + name
            }
            Type::Float { bits } => panic!("unsupported C++ float width {bits}"),
            Type::Size => format!("std::size_t{}", if name.is_empty() { "" } else { " " }) + name,
            Type::Named(value) => {
                format!("{value}{}", if name.is_empty() { "" } else { " " }) + name
            }
            Type::Pointer { mutable, pointee } => {
                let pointee = self.ty(pointee, None);
                let qualifier = if *mutable { "" } else { "const " };
                if name.is_empty() {
                    format!("{qualifier}{pointee}*")
                } else {
                    format!("{qualifier}{pointee}* {name}")
                }
            }
            Type::Array { element, length } => {
                if name.is_empty() {
                    format!("{}[{length}]", self.ty(element, None))
                } else {
                    format!("{} {name}[{length}]", self.ty(element, None))
                }
            }
            Type::FunctionPointer { result, parameters } => {
                let parameters = parameters
                    .iter()
                    .map(|parameter| self.ty(parameter, None))
                    .collect::<Vec<_>>()
                    .join(", ");
                format!("{} (*{name})({parameters})", self.ty(result, None))
            }
        }
    }

    fn line(&mut self, value: &str) {
        for _ in 0..self.indentation {
            self.output.push_str("    ");
        }
        self.output.push_str(value);
        self.output.push('\n');
    }
}
