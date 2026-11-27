//! Syntax only: names and written types remain unresolved. The original lexer
//! stream is owned alongside the AST, including source trivia in token gaps.
use crate::{Span, lexer::Token};
use std::ops::Range;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct NodeId(pub usize);

/// A view into one original token. Generic closing brackets can refer to a
/// subspan of >> or >>= without splitting or altering the lexer stream.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TokenRef {
    pub index: usize,
    pub span: Span,
}

#[derive(Debug)]
pub struct ParsedUnit {
    pub source: String,
    pub tokens: Vec<Token>,
    pub ast: Ast,
}

impl ParsedUnit {
    pub fn text(&self, token: TokenRef) -> &str {
        &self.source[token.span.start..token.span.end]
    }
    pub fn node_text(&self, id: NodeId) -> &str {
        let span = self.ast.nodes[id.0].span;
        &self.source[span.start..span.end]
    }
    /// Includes whitespace/comments; node token ranges can overlap, so original
    /// source is recovered from the retained unit, not by concatenating nodes.
    pub fn original_source(&self) -> &str {
        &self.source
    }
}

#[derive(Debug)]
pub struct Ast {
    pub nodes: Vec<Node>,
    pub root: NodeId,
}

#[derive(Debug)]
pub struct Node {
    pub span: Span,
    /// Half-open indices into ParsedUnit.tokens, including partial angle tokens.
    pub tokens: Range<usize>,
    pub kind: NodeKind,
}

#[derive(Debug)]
pub struct Attributes {
    pub annotations: Vec<NodeId>,
    pub public: Option<TokenRef>,
}

#[derive(Debug)]
pub enum TypeSyntax {
    Path {
        segments: Vec<TokenRef>,
        arguments: Vec<NodeId>,
    },
    Reference {
        ampersand: TokenRef,
        mutable: Option<TokenRef>,
        target: NodeId,
    },
    Tuple {
        elements: Vec<NodeId>,
    },
    Array {
        element: NodeId,
        length: NodeId,
    },
    Slice {
        element: NodeId,
    },
    Callable {
        parameters: Vec<NodeId>,
        result: NodeId,
    },
    /// Only inside a structural contract's generic argument list.
    Constrained {
        parameter: TokenRef,
        alternatives: Vec<NodeId>,
    },
}

#[derive(Debug)]
pub enum PatternSyntax {
    Wildcard,
    Binding {
        mutable: Option<TokenRef>,
        name: TokenRef,
    },
    Tuple {
        elements: Vec<NodeId>,
    },
    Variant {
        path: NodeId,
        positional: Option<Vec<NodeId>>,
        fields: Option<Vec<NodeId>>,
    },
    Field {
        name: TokenRef,
        binding: NodeId,
    },
}

#[derive(Debug)]
pub enum AnnotationSyntax {
    Marker,
    Properties {
        entries: Vec<NodeId>,
    },
    TypeContract {
        parameter: TokenRef,
        arguments: Vec<NodeId>,
        with: Option<TokenRef>,
        /// One mode for the complete disjunction; absent means exact matching.
        alternatives: Vec<NodeId>,
        /// Original | tokens between the nonempty alternatives.
        separators: Vec<TokenRef>,
    },
    Branch {
        join: Option<NodeId>,
    },
}

#[derive(Debug)]
pub enum NodeKind {
    Module {
        items: Vec<NodeId>,
    },
    Import {
        path: Vec<TokenRef>,
        entries: Option<Vec<NodeId>>,
        alias: Option<TokenRef>,
    },
    ImportEntry {
        name: TokenRef,
        alias: Option<TokenRef>,
    },
    Function {
        attributes: Attributes,
        asynchronous: Option<TokenRef>,
        abi: Option<TokenRef>,
        name: TokenRef,
        parameters: Vec<NodeId>,
        result: Option<NodeId>,
        body: Option<NodeId>,
    },
    Parameter {
        mutable: Option<TokenRef>,
        reference: Option<TokenRef>,
        name: TokenRef,
        ty: Option<NodeId>,
    },
    Struct {
        attributes: Attributes,
        name: TokenRef,
        generics: Vec<TokenRef>,
        members: Vec<NodeId>,
    },
    Enum {
        attributes: Attributes,
        name: TokenRef,
        generics: Vec<TokenRef>,
        members: Vec<NodeId>,
    },
    Field {
        attributes: Attributes,
        name: TokenRef,
        ty: NodeId,
    },
    Variant {
        name: TokenRef,
        positional: Option<Vec<NodeId>>,
        fields: Option<Vec<NodeId>>,
    },
    Constant {
        attributes: Attributes,
        name: TokenRef,
        ty: NodeId,
        value: NodeId,
    },
    Annotation {
        name: TokenRef,
        syntax: AnnotationSyntax,
    },
    /// A complete nonempty method set within a structural type contract.
    TypeContractAlternative {
        open: TokenRef,
        methods: Vec<NodeId>,
        close: TokenRef,
    },
    Property {
        key: NodeId,
        value: NodeId,
    },
    Size {
        number: TokenRef,
        unit: TokenRef,
    },
    Conditional {
        condition: NodeId,
        items: Vec<NodeId>,
        end: TokenRef,
    },
    Type(TypeSyntax),
    Pattern(PatternSyntax),
    Block {
        annotations: Vec<NodeId>,
        statements: Vec<NodeId>,
        result: Option<NodeId>,
    },
    Let {
        pattern: NodeId,
        ty: Option<NodeId>,
        value: NodeId,
    },
    Assignment {
        target: NodeId,
        operator: TokenRef,
        value: NodeId,
    },
    ExpressionStatement {
        expression: NodeId,
        semicolon: Option<TokenRef>,
    },
    Return {
        keyword: TokenRef,
        value: Option<NodeId>,
    },
    Break {
        keyword: TokenRef,
        value: Option<NodeId>,
    },
    Continue {
        keyword: TokenRef,
    },
    Yield {
        keyword: TokenRef,
    },
    NamedMove {
        keyword: TokenRef,
        name: TokenRef,
    },
    While {
        condition: NodeId,
        body: NodeId,
    },
    For {
        pattern: NodeId,
        source: NodeId,
        body: NodeId,
    },
    Path {
        segments: Vec<TokenRef>,
        arguments: Vec<NodeId>,
    },
    Literal {
        token: TokenRef,
    },
    Parenthesized {
        expression: NodeId,
    },
    Tuple {
        elements: Vec<NodeId>,
    },
    Array {
        elements: Vec<NodeId>,
        repeat: Option<NodeId>,
    },
    Unary {
        operator: TokenRef,
        mutable: Option<TokenRef>,
        operand: NodeId,
    },
    Binary {
        operator: TokenRef,
        left: NodeId,
        right: NodeId,
    },
    Conversion {
        value: NodeId,
        operator: TokenRef,
        ty: NodeId,
    },
    Call {
        callee: NodeId,
        arguments: Vec<NodeId>,
    },
    Projection {
        base: NodeId,
        member: TokenRef,
    },
    Index {
        base: NodeId,
        index: NodeId,
    },
    Range {
        start: Option<NodeId>,
        separator: TokenRef,
        end: Option<NodeId>,
    },
    Await {
        value: NodeId,
        keyword: TokenRef,
    },
    Propagate {
        value: NodeId,
        operator: TokenRef,
    },
    Unwrap {
        value: NodeId,
        operator: TokenRef,
    },
    Construct {
        path: Option<NodeId>,
        fields: Vec<NodeId>,
    },
    FieldInitializer {
        name: TokenRef,
        value: Option<NodeId>,
    },
    Closure {
        moving: Option<TokenRef>,
        parameters: Vec<NodeId>,
        result: Option<NodeId>,
        body: NodeId,
    },
    Async {
        keyword: TokenRef,
        moving: Option<TokenRef>,
        body: NodeId,
    },
    MoveBlock {
        keyword: TokenRef,
        body: NodeId,
    },
    If {
        condition: NodeId,
        yes: NodeId,
        no: Option<NodeId>,
    },
    LetCondition {
        pattern: NodeId,
        value: NodeId,
    },
    Match {
        value: NodeId,
        arms: Vec<NodeId>,
    },
    MatchArm {
        pattern: NodeId,
        body: NodeId,
    },
    Loop {
        body: NodeId,
    },
    Unchecked {
        keyword: TokenRef,
        body: NodeId,
    },
    /// Body, operands and tokenized header live in the existing lexer payload.
    Foreign {
        token: TokenRef,
        /// Parsed include entries point into the original island token. Later
        /// stages consume these references rather than parsing the header again.
        includes: Vec<TokenRef>,
    },
}

impl NodeKind {
    /// Syntactic children only, in field/source order. No bindings are resolved.
    /// Exhaustive matching makes additions to the AST require visitor updates.
    pub fn children(&self) -> Vec<NodeId> {
        let mut out = Vec::new();
        match self {
            Self::Module { items } => out.extend(items),
            Self::Import { entries, .. } => out.extend(entries.iter().flatten()),
            Self::Function {
                attributes,
                parameters,
                result,
                body,
                ..
            } => {
                out.extend(&attributes.annotations);
                out.extend(parameters);
                out.extend(result);
                out.extend(body);
            }
            Self::Parameter { ty, .. } => out.extend(ty),
            Self::Struct {
                attributes,
                members,
                ..
            }
            | Self::Enum {
                attributes,
                members,
                ..
            } => {
                out.extend(&attributes.annotations);
                out.extend(members);
            }
            Self::Field { attributes, ty, .. } => {
                out.extend(&attributes.annotations);
                out.push(*ty);
            }
            Self::Variant {
                positional, fields, ..
            } => {
                out.extend(positional.iter().flatten());
                out.extend(fields.iter().flatten());
            }
            Self::Constant {
                attributes,
                ty,
                value,
                ..
            } => {
                out.extend(&attributes.annotations);
                out.extend([*ty, *value]);
            }
            Self::Annotation { syntax, .. } => match syntax {
                AnnotationSyntax::Marker => {}
                AnnotationSyntax::Properties { entries } => out.extend(entries),
                AnnotationSyntax::TypeContract {
                    arguments,
                    alternatives,
                    ..
                } => {
                    out.extend(arguments);
                    out.extend(alternatives);
                }
                AnnotationSyntax::Branch { join } => out.extend(join),
            },
            Self::TypeContractAlternative { methods, .. } => out.extend(methods),
            Self::Property { key, value } => out.extend([*key, *value]),
            Self::Conditional {
                condition, items, ..
            } => {
                out.push(*condition);
                out.extend(items);
            }
            Self::Type(syntax) => match syntax {
                TypeSyntax::Path { arguments, .. } => out.extend(arguments),
                TypeSyntax::Reference { target, .. } => out.push(*target),
                TypeSyntax::Tuple { elements } => out.extend(elements),
                TypeSyntax::Array { element, length } => out.extend([*element, *length]),
                TypeSyntax::Slice { element } => out.push(*element),
                TypeSyntax::Callable { parameters, result } => {
                    out.extend(parameters);
                    out.push(*result);
                }
                TypeSyntax::Constrained { alternatives, .. } => out.extend(alternatives),
            },
            Self::Pattern(syntax) => match syntax {
                PatternSyntax::Wildcard | PatternSyntax::Binding { .. } => {}
                PatternSyntax::Tuple { elements } => out.extend(elements),
                PatternSyntax::Variant {
                    path,
                    positional,
                    fields,
                } => {
                    out.push(*path);
                    out.extend(positional.iter().flatten());
                    out.extend(fields.iter().flatten());
                }
                PatternSyntax::Field { binding, .. } => out.push(*binding),
            },
            Self::Block {
                annotations,
                statements,
                result,
            } => {
                out.extend(annotations);
                out.extend(statements);
                out.extend(result);
            }
            Self::Let { pattern, ty, value } => {
                out.push(*pattern);
                out.extend(ty);
                out.push(*value);
            }
            Self::Assignment { target, value, .. } => out.extend([*target, *value]),
            Self::ExpressionStatement { expression, .. } | Self::Parenthesized { expression } => {
                out.push(*expression)
            }
            Self::Return { value, .. } | Self::Break { value, .. } => out.extend(value),
            Self::While { condition, body } => out.extend([*condition, *body]),
            Self::For {
                pattern,
                source,
                body,
            } => out.extend([*pattern, *source, *body]),
            Self::Path { arguments, .. } => out.extend(arguments),
            Self::Tuple { elements } => out.extend(elements),
            Self::Array { elements, repeat } => {
                out.extend(elements);
                out.extend(repeat);
            }
            Self::Unary { operand, .. } => out.push(*operand),
            Self::Binary { left, right, .. } => out.extend([*left, *right]),
            Self::Conversion { value, ty, .. } => out.extend([*value, *ty]),
            Self::Call { callee, arguments } => {
                out.push(*callee);
                out.extend(arguments);
            }
            Self::Projection { base, .. } => out.push(*base),
            Self::Index { base, index } => out.extend([*base, *index]),
            Self::Range { start, end, .. } => {
                out.extend(start);
                out.extend(end);
            }
            Self::Await { value, .. }
            | Self::Propagate { value, .. }
            | Self::Unwrap { value, .. } => out.push(*value),
            Self::Construct { path, fields } => {
                out.extend(path);
                out.extend(fields);
            }
            Self::FieldInitializer { value, .. } => out.extend(value),
            Self::Closure {
                parameters,
                result,
                body,
                ..
            } => {
                out.extend(parameters);
                out.extend(result);
                out.push(*body);
            }
            Self::If { condition, yes, no } => {
                out.extend([*condition, *yes]);
                out.extend(no);
            }
            Self::LetCondition { pattern, value } => out.extend([*pattern, *value]),
            Self::Match { value, arms } => {
                out.push(*value);
                out.extend(arms);
            }
            Self::MatchArm { pattern, body } => out.extend([*pattern, *body]),
            Self::Async { body, .. }
            | Self::MoveBlock { body, .. }
            | Self::Loop { body }
            | Self::Unchecked { body, .. } => out.push(*body),
            Self::ImportEntry { .. }
            | Self::Size { .. }
            | Self::Continue { .. }
            | Self::Yield { .. }
            | Self::NamedMove { .. }
            | Self::Literal { .. }
            | Self::Foreign { .. } => {}
        }
        out
    }

    /// Written token views, including keyword flags and foreign header entries.
    pub fn token_refs(&self) -> Vec<TokenRef> {
        let mut out = Vec::new();
        match self {
            Self::Import { path, alias, .. } => {
                out.extend(path);
                out.extend(alias);
            }
            Self::ImportEntry { name, alias } => {
                out.push(*name);
                out.extend(alias);
            }
            Self::Function {
                attributes,
                asynchronous,
                abi,
                name,
                ..
            } => {
                out.extend(attributes.public);
                out.extend(asynchronous);
                out.extend(abi);
                out.push(*name);
            }
            Self::Parameter {
                mutable,
                reference,
                name,
                ..
            } => {
                out.extend(reference);
                out.extend(mutable);
                out.push(*name);
            }
            Self::Struct {
                attributes,
                name,
                generics,
                ..
            }
            | Self::Enum {
                attributes,
                name,
                generics,
                ..
            } => {
                out.extend(attributes.public);
                out.push(*name);
                out.extend(generics);
            }
            Self::Field {
                attributes, name, ..
            }
            | Self::Constant {
                attributes, name, ..
            } => {
                out.extend(attributes.public);
                out.push(*name);
            }
            Self::Variant { name, .. } | Self::FieldInitializer { name, .. } => out.push(*name),
            Self::Annotation { name, syntax } => {
                out.push(*name);
                if let AnnotationSyntax::TypeContract {
                    parameter,
                    with,
                    separators,
                    ..
                } = syntax
                {
                    out.push(*parameter);
                    out.extend(with);
                    out.extend(separators);
                }
            }
            Self::TypeContractAlternative { open, close, .. } => out.extend([*open, *close]),
            Self::Size { number, unit } => out.extend([*number, *unit]),
            Self::Conditional { end, .. } => out.push(*end),
            Self::Type(syntax) => match syntax {
                TypeSyntax::Path { segments, .. } => out.extend(segments),
                TypeSyntax::Reference {
                    ampersand, mutable, ..
                } => {
                    out.push(*ampersand);
                    out.extend(mutable);
                }
                TypeSyntax::Constrained { parameter, .. } => out.push(*parameter),
                TypeSyntax::Tuple { .. }
                | TypeSyntax::Array { .. }
                | TypeSyntax::Slice { .. }
                | TypeSyntax::Callable { .. } => {}
            },
            Self::Pattern(syntax) => match syntax {
                PatternSyntax::Binding { mutable, name } => {
                    out.extend(mutable);
                    out.push(*name);
                }
                PatternSyntax::Field { name, .. } => out.push(*name),
                PatternSyntax::Wildcard
                | PatternSyntax::Tuple { .. }
                | PatternSyntax::Variant { .. } => {}
            },
            Self::Assignment { operator, .. }
            | Self::Binary { operator, .. }
            | Self::Conversion { operator, .. }
            | Self::Propagate { operator, .. }
            | Self::Unwrap { operator, .. } => out.push(*operator),
            Self::ExpressionStatement { semicolon, .. } => out.extend(semicolon),
            Self::Return { keyword, .. }
            | Self::Break { keyword, .. }
            | Self::Continue { keyword }
            | Self::Yield { keyword }
            | Self::Await { keyword, .. }
            | Self::MoveBlock { keyword, .. }
            | Self::Unchecked { keyword, .. } => out.push(*keyword),
            Self::NamedMove { keyword, name } => out.extend([*keyword, *name]),
            Self::Path { segments, .. } => out.extend(segments),
            Self::Literal { token } => out.push(*token),
            Self::Unary {
                operator, mutable, ..
            } => {
                out.push(*operator);
                out.extend(mutable);
            }
            Self::Projection { member, .. } => out.push(*member),
            Self::Range { separator, .. } => out.push(*separator),
            Self::Closure { moving, .. } => out.extend(moving),
            Self::Async {
                keyword, moving, ..
            } => {
                out.push(*keyword);
                out.extend(moving);
            }
            Self::Foreign { token, includes } => {
                out.push(*token);
                out.extend(includes);
            }
            Self::Module { .. }
            | Self::Property { .. }
            | Self::Block { .. }
            | Self::Let { .. }
            | Self::While { .. }
            | Self::For { .. }
            | Self::Parenthesized { .. }
            | Self::Tuple { .. }
            | Self::Array { .. }
            | Self::Call { .. }
            | Self::Index { .. }
            | Self::Construct { .. }
            | Self::If { .. }
            | Self::LetCondition { .. }
            | Self::Match { .. }
            | Self::MatchArm { .. }
            | Self::Loop { .. } => {}
        }
        out
    }
}
