//! Reference syntax parser. It consumes the existing lexer stream exactly once;
//! no declaration table, imported names, target evaluation or inferred types.
use crate::{
    Span,
    ast::*,
    lexer::{Kind, Payload, Token},
};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorClass {
    Syntax,
    InputContract,
    ImplementationLimit,
}

#[derive(Debug)]
pub struct ParseError {
    pub class: ErrorClass,
    pub span: Span,
    pub message: &'static str,
    pub expected: Vec<&'static str>,
    pub found: String,
}

/// Takes ownership of the lexer output without re-lexing or rewriting it.
pub fn parse(source: String, tokens: Vec<Token>) -> Result<ParsedUnit, ParseError> {
    parse_mode(source, tokens, false)
}

/// Parse one expression using the same syntax parser, preserving source/tokens.
pub fn parse_expression(source: String, tokens: Vec<Token>) -> Result<ParsedUnit, ParseError> {
    parse_mode(source, tokens, true)
}

fn parse_mode(
    source: String,
    tokens: Vec<Token>,
    expression: bool,
) -> Result<ParsedUnit, ParseError> {
    validate_stream(&source, &tokens)?;
    let mut parser = Parser {
        source: &source,
        tokens: &tokens,
        index: 0,
        piece: 0,
        last_end: 0,
        nodes: Vec::new(),
        depth: 0,
        unchecked: 0,
    };
    let start = parser.mark();
    let root = if expression {
        let root = parser.expr(0, false)?;
        if !parser.eof() {
            return Err(parser.error("unexpected token after expression", &["EOF"]));
        }
        root
    } else {
        let mut items = Vec::new();
        while !parser.eof() {
            items.push(parser.item(Context::Module)?);
        }
        let root = parser.push(start, NodeKind::Module { items });
        // A module includes leading/trailing trivia, even for an empty file.
        parser.nodes[root.0].span = Span {
            start: 0,
            end: source.len(),
        };
        root
    };
    let ast = Ast {
        nodes: parser.nodes,
        root,
    };
    Ok(ParsedUnit {
        source,
        tokens,
        ast,
    })
}

fn validate_stream(source: &str, tokens: &[Token]) -> Result<(), ParseError> {
    let valid = !tokens.is_empty()
        && tokens.last().is_some_and(|t| {
            t.kind == Kind::Eof
                && t.span
                    == Span {
                        start: source.len(),
                        end: source.len(),
                    }
        })
        && tokens.iter().enumerate().all(|(i, t)| {
            t.span.start <= t.span.end
                && t.span.end <= source.len()
                && source.is_char_boundary(t.span.start)
                && source.is_char_boundary(t.span.end)
                && (i == 0 || tokens[i - 1].span.end <= t.span.start)
                && (i == tokens.len() - 1 || t.kind != Kind::Eof && t.span.start < t.span.end)
        });
    if valid {
        Ok(())
    } else {
        Err(ParseError {
            class: ErrorClass::InputContract,
            span: Span { start: 0, end: 0 },
            message: "invalid source/token handoff",
            expected: vec!["ordered source spans and one final EOF token"],
            found: String::new(),
        })
    }
}

#[derive(Clone, Copy)]
struct Mark {
    token: usize,
    byte: usize,
}
#[derive(Clone, Copy)]
enum Context {
    Module,
    Struct,
    Enum,
}
struct Parser<'a> {
    source: &'a str,
    tokens: &'a [Token],
    index: usize,
    piece: usize,
    last_end: usize,
    nodes: Vec<Node>,
    depth: usize,
    unchecked: usize,
}
type ResultNode = Result<NodeId, ParseError>;
impl Parser<'_> {
    fn word(&self) -> &str {
        let s = self.tokens[self.index].span;
        &self.source[s.start + self.piece..s.end]
    }
    fn peek(&self, n: usize) -> &str {
        self.tokens
            .get(self.index + n)
            .map_or("", |t| &self.source[t.span.start..t.span.end])
    }
    fn eof(&self) -> bool {
        self.tokens[self.index].kind == Kind::Eof
    }
    fn mark(&self) -> Mark {
        Mark {
            token: self.index,
            byte: self.tokens[self.index].span.start + self.piece,
        }
    }
    fn reference(&self) -> TokenRef {
        TokenRef {
            index: self.index,
            span: Span {
                start: self.mark().byte,
                end: self.tokens[self.index].span.end,
            },
        }
    }
    fn advance(&mut self) -> TokenRef {
        let r = self.reference();
        self.last_end = r.span.end;
        if !self.eof() {
            self.index += 1;
            self.piece = 0;
        }
        r
    }
    fn eat(&mut self, text: &str) -> Option<TokenRef> {
        (self.word() == text && !self.eof()).then(|| self.advance())
    }
    fn error(&self, message: &'static str, expected: &[&'static str]) -> ParseError {
        ParseError {
            class: ErrorClass::Syntax,
            span: self.reference().span,
            message,
            expected: expected.to_vec(),
            found: self.word().to_owned(),
        }
    }
    fn expect(&mut self, text: &'static str) -> Result<TokenRef, ParseError> {
        self.eat(text)
            .ok_or_else(|| self.error("unexpected token", &[text]))
    }
    fn ident(&mut self) -> Result<TokenRef, ParseError> {
        if self.tokens[self.index].kind != Kind::Name
            || matches!(
                self.word(),
                "_" | "fn"
                    | "struct"
                    | "enum"
                    | "const"
                    | "let"
                    | "if"
                    | "else"
                    | "match"
                    | "loop"
                    | "while"
                    | "for"
                    | "in"
                    | "return"
                    | "break"
                    | "continue"
                    | "yield"
                    | "as"
                    | "true"
                    | "false"
                    | "async"
                    | "move"
                    | "mut"
                    | "pub"
                    | "use"
                    | "extern"
            )
        {
            return Err(self.error("expected an identifier", &["identifier"]));
        }
        Ok(self.advance())
    }
    fn push(&mut self, start: Mark, kind: NodeKind) -> NodeId {
        let id = NodeId(self.nodes.len());
        self.nodes.push(Node {
            span: Span {
                start: start.byte,
                end: self.last_end.max(start.byte),
            },
            tokens: start.token..self.index + usize::from(self.piece > 0),
            kind,
        });
        id
    }
    fn start_of(&self, id: NodeId) -> Mark {
        let n = &self.nodes[id.0];
        Mark {
            token: n.tokens.start,
            byte: n.span.start,
        }
    }
    fn nested(&mut self, f: impl FnOnce(&mut Self) -> ResultNode) -> ResultNode {
        if self.depth >= 256 {
            let mut e = self.error("parser nesting limit reached", &[]);
            e.class = ErrorClass::ImplementationLimit;
            return Err(e);
        }
        self.depth += 1;
        let result = f(self);
        self.depth -= 1;
        result
    }
    fn empty_attributes() -> Attributes {
        Attributes {
            annotations: Vec::new(),
            public: None,
        }
    }
    fn attributes(&mut self) -> Result<Attributes, ParseError> {
        let mut annotations = Vec::new();
        while self.word() == "#" && self.peek(2) != "if" {
            annotations.push(self.annotation()?);
        }
        Ok(Attributes {
            annotations,
            public: self.eat("pub"),
        })
    }
    fn comma_end(&mut self, end: &'static str) -> Result<bool, ParseError> {
        if self.eat(end).is_some() {
            return Ok(true);
        }
        self.expect(",")?;
        Ok(self.eat(end).is_some())
    }
    fn angle_close(&mut self) -> Result<TokenRef, ParseError> {
        // The original longest-match token remains unchanged in ParsedUnit.
        if matches!(self.word(), ">" | ">>" | ">=" | ">>=") {
            let mut r = self.reference();
            r.span.end = r.span.start + 1;
            self.last_end = r.span.end;
            self.piece += 1;
            if self.tokens[self.index].span.start + self.piece == self.tokens[self.index].span.end {
                self.index += 1;
                self.piece = 0;
            }
            Ok(r)
        } else {
            Err(self.error("expected a generic closing bracket", &[">"]))
        }
    }
    fn generic_parameters(&mut self) -> Result<Vec<TokenRef>, ParseError> {
        let mut names = Vec::new();
        if self.eat("<").is_none() {
            return Ok(names);
        }
        loop {
            names.push(self.ident()?);
            if self.eat(",").is_none() {
                self.angle_close()?;
                break;
            }
            if self.word().starts_with('>') {
                self.angle_close()?;
                break;
            }
        }
        Ok(names)
    }
    fn item(&mut self, context: Context) -> ResultNode {
        if matches!(context, Context::Module)
            && self.word() == "#"
            && matches!(self.peek(2), "datastack" | "directive")
        {
            return self.annotation();
        }
        if self.word() == "#" && self.peek(2) == "if" {
            return self.conditional(context);
        }
        let start = self.mark();
        let attrs = self.attributes()?;
        if matches!(context, Context::Module) && self.eat("use").is_some() {
            if attrs.public.is_some() || !attrs.annotations.is_empty() {
                return Err(self.error("use cannot have declaration attributes", &[]));
            }
            return self.import(start);
        }
        if self.word() == "const" {
            return self.constant(start, attrs);
        }
        let asynchronous = self.eat("async");
        let abi = if self.eat("extern").is_some() {
            if self.tokens[self.index].kind != Kind::Text {
                return Err(self.error("expected an ABI string", &["\"C\""]));
            }
            Some(self.advance())
        } else {
            None
        };
        if self.eat("fn").is_some() {
            return self.function(start, attrs, asynchronous, abi, false);
        }
        if asynchronous.is_some() || abi.is_some() {
            return Err(self.error("expected a function declaration", &["fn"]));
        }
        let record = self.eat("struct").is_some();
        let enumeration = !record && self.eat("enum").is_some();
        if record || enumeration {
            let name = self.ident()?;
            let generics = self.generic_parameters()?;
            self.expect("{")?;
            let mut members = Vec::new();
            while self.word() != "}" && !self.eof() {
                members.push(self.item(if record {
                    Context::Struct
                } else {
                    Context::Enum
                })?)
            }
            self.expect("}")?;
            return Ok(self.push(
                start,
                if record {
                    NodeKind::Struct {
                        attributes: attrs,
                        name,
                        generics,
                        members,
                    }
                } else {
                    NodeKind::Enum {
                        attributes: attrs,
                        name,
                        generics,
                        members,
                    }
                },
            ));
        }
        match context {
            Context::Struct => {
                let name = self.ident()?;
                self.expect(":")?;
                let ty = self.ty()?;
                self.expect(";")?;
                Ok(self.push(
                    start,
                    NodeKind::Field {
                        attributes: attrs,
                        name,
                        ty,
                    },
                ))
            }
            Context::Enum => {
                if attrs.public.is_some() || !attrs.annotations.is_empty() {
                    return Err(
                        self.error("attributes do not prefix this variant", &["fn", "const"])
                    );
                }
                let name = self.ident()?;
                let mut positional = None;
                let mut fields = None;
                if self.eat("(").is_some() {
                    let mut values = vec![self.ty()?];
                    while !self.comma_end(")")? {
                        values.push(self.ty()?)
                    }
                    positional = Some(values)
                } else if self.eat("{").is_some() {
                    let mut values = Vec::new();
                    while self.word() != "}" {
                        values.push(self.item(Context::Struct)?)
                    }
                    self.expect("}")?;
                    fields = Some(values)
                }
                self.expect(";")?;
                Ok(self.push(
                    start,
                    NodeKind::Variant {
                        name,
                        positional,
                        fields,
                    },
                ))
            }
            Context::Module => {
                if !attrs.annotations.is_empty() && attrs.public.is_none() {
                    Ok(self.push(
                        start,
                        NodeKind::Module {
                            items: attrs.annotations,
                        },
                    ))
                } else {
                    Err(self.error(
                        "expected a module declaration",
                        &["use", "fn", "struct", "enum", "const"],
                    ))
                }
            }
        }
    }
    fn import(&mut self, start: Mark) -> ResultNode {
        let mut path = vec![self.ident()?];
        let mut entries = None;
        while self.eat("::").is_some() {
            if self.eat("{").is_some() {
                let mut list = Vec::new();
                loop {
                    let mark = self.mark();
                    let name = self.ident()?;
                    let alias = if self.eat("as").is_some() {
                        Some(self.ident()?)
                    } else {
                        None
                    };
                    list.push(self.push(mark, NodeKind::ImportEntry { name, alias }));
                    if self.comma_end("}")? {
                        break;
                    }
                }
                entries = Some(list);
                break;
            } else {
                path.push(self.ident()?);
            }
        }
        let alias = if self.eat("as").is_some() {
            Some(self.ident()?)
        } else {
            None
        };
        self.expect(";")?;
        Ok(self.push(
            start,
            NodeKind::Import {
                path,
                entries,
                alias,
            },
        ))
    }
    fn conditional(&mut self, context: Context) -> ResultNode {
        let start = self.mark();
        self.expect("#")?;
        self.expect("(")?;
        self.expect("if")?;
        self.expect(":")?;
        let condition = self.expr(0, false)?;
        self.expect(")")?;
        let mut items = Vec::new();
        while !(self.word() == "#" && self.peek(2) == "endif") && !self.eof() {
            items.push(self.item(context)?)
        }
        self.expect("#")?;
        self.expect("(")?;
        let end = self.expect("endif")?;
        self.expect(")")?;
        Ok(self.push(
            start,
            NodeKind::Conditional {
                condition,
                items,
                end,
            },
        ))
    }
    fn constant(&mut self, start: Mark, attributes: Attributes) -> ResultNode {
        self.expect("const")?;
        let name = self.ident()?;
        self.expect(":")?;
        let ty = self.ty()?;
        self.expect("=")?;
        let value = self.expr(0, false)?;
        self.expect(";")?;
        Ok(self.push(
            start,
            NodeKind::Constant {
                attributes,
                name,
                ty,
                value,
            },
        ))
    }
    fn function(
        &mut self,
        start: Mark,
        attributes: Attributes,
        asynchronous: Option<TokenRef>,
        abi: Option<TokenRef>,
        signature: bool,
    ) -> ResultNode {
        let name = self.ident()?;
        self.expect("(")?;
        let mut parameters = Vec::new();
        if self.eat(")").is_none() {
            loop {
                parameters.push(self.parameter()?);
                if self.comma_end(")")? {
                    break;
                }
            }
        }
        let result = if self.type_starts() {
            Some(self.ty()?)
        } else {
            None
        };
        let body = if signature || abi.is_some() {
            self.expect(";")?;
            None
        } else {
            Some(self.block()?)
        };
        Ok(self.push(
            start,
            NodeKind::Function {
                attributes,
                asynchronous,
                abi,
                name,
                parameters,
                result,
                body,
            },
        ))
    }
    fn parameter(&mut self) -> ResultNode {
        let start = self.mark();
        let reference = self.eat("&");
        let mutable = self.eat("mut");
        let name = self.ident()?;
        let is_self = &self.source[name.span.start..name.span.end] == "self";
        let ty = if self.eat(":").is_some() {
            Some(self.ty()?)
        } else if is_self {
            None
        } else {
            return Err(self.error("parameter type is required", &[":"]));
        };
        if reference.is_some() && !is_self {
            return Err(self.error("receiver reference syntax requires self", &["self"]));
        }
        Ok(self.push(
            start,
            NodeKind::Parameter {
                mutable,
                reference,
                name,
                ty,
            },
        ))
    }
    fn type_starts(&self) -> bool {
        matches!(self.word(), "&" | "&&" | "[" | "(" | "fn")
            || self.tokens[self.index].kind == Kind::Name
                && !matches!(self.word(), "move" | "async")
    }
    fn ty(&mut self) -> ResultNode {
        self.nested(|p| p.type_inner())
    }
    fn type_inner(&mut self) -> ResultNode {
        let start = self.mark();
        let syntax = if matches!(self.word(), "&" | "&&") {
            let mut ampersand = self.reference();
            ampersand.span.end = ampersand.span.start + 1;
            self.last_end = ampersand.span.end;
            self.piece += 1;
            if self.tokens[self.index].span.start + self.piece == self.tokens[self.index].span.end {
                self.index += 1;
                self.piece = 0;
            }

            let mutable = self.eat("mut");
            let target = self.ty()?;
            TypeSyntax::Reference {
                ampersand,
                mutable,
                target,
            }
        } else if self.eat("[").is_some() {
            let element = self.ty()?;
            if self.eat(";").is_some() {
                let length = self.expr(0, false)?;
                self.expect("]")?;
                TypeSyntax::Array { element, length }
            } else {
                self.expect("]")?;
                TypeSyntax::Slice { element }
            }
        } else if self.eat("(").is_some() {
            let mut elements = Vec::new();
            if self.eat(")").is_none() {
                elements.push(self.ty()?);
                self.expect(",")?;
                if self.word() != ")" {
                    loop {
                        elements.push(self.ty()?);
                        if self.comma_end(")")? {
                            break;
                        }
                    }
                } else {
                    return Err(
                        self.error("singleton tuple types are not in the grammar", &["type"])
                    );
                }
            }
            TypeSyntax::Tuple { elements }
        } else if self.eat("fn").is_some() {
            self.expect("(")?;
            let mut parameters = Vec::new();
            if self.eat(")").is_none() {
                loop {
                    parameters.push(self.ty()?);
                    if self.comma_end(")")? {
                        break;
                    }
                }
            }
            let result = self.ty()?;
            TypeSyntax::Callable { parameters, result }
        } else {
            let segments = self.path_segments()?;
            let arguments = self.type_arguments()?;
            TypeSyntax::Path {
                segments,
                arguments,
            }
        };
        Ok(self.push(start, NodeKind::Type(syntax)))
    }
    fn path_segments(&mut self) -> Result<Vec<TokenRef>, ParseError> {
        let mut segments = vec![self.ident()?];
        while self.word() == "::" && self.peek(1) != "{" {
            self.advance();
            segments.push(self.ident()?)
        }
        Ok(segments)
    }
    fn type_arguments(&mut self) -> Result<Vec<NodeId>, ParseError> {
        let mut args = Vec::new();
        if self.eat("<").is_none() {
            return Ok(args);
        }
        loop {
            if self.tokens[self.index].kind == Kind::Integer {
                let start = self.mark();
                let token = self.advance();
                args.push(self.push(start, NodeKind::Literal { token }))
            } else {
                args.push(self.ty()?)
            }
            if self.eat(",").is_none() {
                self.angle_close()?;
                break;
            }
        }
        Ok(args)
    }
    fn contract_arguments(&mut self) -> Result<Vec<NodeId>, ParseError> {
        if self.eat("<").is_none() {
            return Ok(Vec::new());
        }
        let start = self.mark();
        let parameter = self.ident()?;
        let argument = if self.eat(":").is_some() {
            let mut alternatives = vec![self.ty()?];
            while self.eat(",").is_some() {
                alternatives.push(self.ty()?)
            }
            self.push(
                start,
                NodeKind::Type(TypeSyntax::Constrained {
                    parameter,
                    alternatives,
                }),
            )
        } else {
            self.push(
                start,
                NodeKind::Type(TypeSyntax::Path {
                    segments: vec![parameter],
                    arguments: vec![],
                }),
            )
        };
        self.angle_close()?;
        Ok(vec![argument])
    }

    fn annotation(&mut self) -> ResultNode {
        let start = self.mark();
        self.expect("#")?;
        self.expect("(")?;
        let name = self.ident()?;
        let tag = &self.source[name.span.start..name.span.end];
        let syntax = match tag {
            "configurable" | "free_pages" => AnnotationSyntax::Marker,
            "type" => {
                self.expect(":")?;
                let parameter = self.ident()?;
                let arguments = self.contract_arguments()?;
                let with = self.eat("with");
                let mut alternatives = Vec::new();
                let mut separators = Vec::new();
                if self.word() == "{" {
                    alternatives.push(self.contract_alternative()?);
                    while let Some(separator) = self.eat("|") {
                        separators.push(separator);
                        if self.word() == "with" {
                            return Err(self.error(
                                "with applies to the whole contract; place it before the first branch",
                                &["{"],
                            ));
                        }
                        alternatives.push(self.contract_alternative()?);
                    }
                } else if with.is_some() || !arguments.is_empty() {
                    return Err(self.error(
                        "contract arguments or with require a method contract",
                        &["{"],
                    ));
                } else if self.word() == "|" {
                    return Err(self.error("OR requires a method contract before |", &["{"]));
                }
                if self.word() == "||" {
                    return Err(self.error(
                        "use | between type-contract alternatives, not ||",
                        &["|", ")"],
                    ));
                }
                AnnotationSyntax::TypeContract {
                    parameter,
                    arguments,
                    with,
                    alternatives,
                    separators,
                }
            }
            "branch" => {
                let join = if self.eat(":").is_some() {
                    self.expect("join")?;
                    self.expect("=")?;
                    Some(self.expr(0, false)?)
                } else {
                    None
                };
                AnnotationSyntax::Branch { join }
            }
            "lock" if self.word() == ")" => AnnotationSyntax::Marker,
            "lock" | "thread" | "datastack" | "stack_region" | "override" | "directive" => {
                self.expect(":")?;
                let mut entries = Vec::new();
                if self.word() != ")" {
                    loop {
                        let mark = self.mark();
                        let segments = self.path_segments()?;
                        let key = self.push(
                            mark,
                            NodeKind::Path {
                                segments,
                                arguments: vec![],
                            },
                        );
                        self.expect("=")?;
                        let value = if self.tokens[self.index].kind == Kind::Integer
                            && matches!(self.peek(1), "K" | "M" | "G")
                        {
                            let mark = self.mark();
                            let number = self.advance();
                            let unit = self.advance();
                            self.push(mark, NodeKind::Size { number, unit })
                        } else if tag == "directive" && self.eat("{").is_some() {
                            let mark = self.mark();
                            let mut fields = Vec::new();
                            if self.eat("}").is_none() {
                                loop {
                                    let m = self.mark();
                                    let segments = self.path_segments()?;
                                    let key = self.push(
                                        m,
                                        NodeKind::Path {
                                            segments,
                                            arguments: vec![],
                                        },
                                    );
                                    self.expect(":")?;
                                    let value = self.expr(0, false)?;
                                    fields.push(self.push(m, NodeKind::Property { key, value }));
                                    if self.comma_end("}")? {
                                        break;
                                    }
                                }
                            }
                            self.push(mark, NodeKind::Module { items: fields })
                        } else {
                            self.expr(0, false)?
                        };
                        entries.push(self.push(mark, NodeKind::Property { key, value }));
                        if self.eat(",").is_none() {
                            break;
                        }
                        if self.word() == ")" {
                            break;
                        }
                    }
                }
                AnnotationSyntax::Properties { entries }
            }
            _ => {
                return Err(self.error(
                    "unknown annotation",
                    &[
                        "type",
                        "branch",
                        "lock",
                        "thread",
                        "configurable",
                        "override",
                        "datastack",
                        "stack_region",
                        "free_pages",
                        "directive",
                    ],
                ));
            }
        };
        self.expect(")")?;
        Ok(self.push(start, NodeKind::Annotation { name, syntax }))
    }
    fn contract_alternative(&mut self) -> ResultNode {
        let start = self.mark();
        let open = self.expect("{")?;
        if self.word() == "}" {
            return Err(self.error("method contract requires at least one signature", &["fn"]));
        }
        let mut methods = Vec::new();
        while self.word() != "}" {
            let mark = self.mark();
            let attrs = Self::empty_attributes();
            let asynchronous = self.eat("async");
            self.expect("fn")?;
            methods.push(self.function(mark, attrs, asynchronous, None, true)?);
        }
        let close = self.expect("}")?;
        Ok(self.push(
            start,
            NodeKind::TypeContractAlternative {
                open,
                methods,
                close,
            },
        ))
    }

    fn block(&mut self) -> ResultNode {
        self.nested(|p| p.block_inner())
    }
    fn block_inner(&mut self) -> ResultNode {
        let start = self.mark();
        let mut annotations = Vec::new();
        while self.word() == "#" {
            annotations.push(self.annotation()?)
        }
        self.expect("{")?;
        let mut statements = Vec::new();
        let mut result = None;
        while self.word() != "}" && !self.eof() {
            if let Some(statement) = self.special_statement()? {
                statements.push(statement);
                continue;
            }
            let mark = self.mark();
            // A bare block-form at statement start is self-contained. A
            // parenthesized block, assignment RHS or call argument still uses
            // ordinary expression parsing and may participate in operators.
            let expression = if self.starts_block_statement() {
                self.nested(|p| p.primary(false))?
            } else {
                self.expr(0, false)?
            };
            if let Some(operator) = self.assignment_operator() {
                if !self.assignment_target_shape(expression) {
                    let node = &self.nodes[expression.0];
                    return Err(ParseError {
                        class: ErrorClass::Syntax,
                        span: node.span,
                        message: "assignment requires a name, dereference, field or indexed target",
                        expected: vec!["assignment_left_expression"],
                        found: self.source[node.span.start..node.span.end].to_owned(),
                    });
                }
                let value = self.expr(0, false)?;
                self.expect(";")?;
                // Distinct target/value roles; no inferred mutability or place validity.
                statements.push(self.push(
                    mark,
                    NodeKind::Assignment {
                        target: expression,
                        operator,
                        value,
                    },
                ));
            } else if let Some(semicolon) = self.eat(";") {
                statements.push(self.push(
                    mark,
                    NodeKind::ExpressionStatement {
                        expression,
                        semicolon: Some(semicolon),
                    },
                ))
            } else if self.word() == "}" {
                result = Some(expression);
                break;
            } else if self.block_like(expression) {
                statements.push(self.push(
                    mark,
                    NodeKind::ExpressionStatement {
                        expression,
                        semicolon: None,
                    },
                ))
            } else {
                return Err(self.error("expected a statement terminator", &[";", "}"]));
            }
        }
        self.expect("}")?;
        Ok(self.push(
            start,
            NodeKind::Block {
                annotations,
                statements,
                result,
            },
        ))
    }
    fn starts_block_statement(&self) -> bool {
        matches!(self.word(), "{" | "#" | "if" | "match" | "loop" | "@")
            || self.word() == "move" && matches!(self.peek(1), "{" | "#")
            || matches!(
                self.tokens[self.index].kind,
                Kind::Assembly | Kind::C | Kind::Cpp
            )
    }

    fn block_like(&self, id: NodeId) -> bool {
        matches!(
            self.nodes[id.0].kind,
            NodeKind::Block { .. }
                | NodeKind::If { .. }
                | NodeKind::Match { .. }
                | NodeKind::Loop { .. }
                | NodeKind::MoveBlock { .. }
                | NodeKind::Unchecked { .. }
                | NodeKind::Foreign { .. }
        )
    }
    // This recognizes the grammatical shape of a place, not whether it exists,
    // is mutable, or remains alive. Calls can occur inside a final projection,
    // index or dereference without consulting their signatures.
    fn assignment_target_shape(&self, id: NodeId) -> bool {
        match &self.nodes[id.0].kind {
            NodeKind::Path {
                segments,
                arguments,
            } => segments.len() == 1 && arguments.is_empty(),
            NodeKind::Parenthesized { expression } => self.assignment_target_shape(*expression),
            NodeKind::Unary { operator, .. } => {
                &self.source[operator.span.start..operator.span.end] == "*"
            }
            NodeKind::Projection { .. } => true,
            NodeKind::Index { index, .. } => {
                !matches!(self.nodes[index.0].kind, NodeKind::Range { .. })
            }
            _ => false,
        }
    }

    fn assignment_operator(&mut self) -> Option<TokenRef> {
        if matches!(
            self.word(),
            "=" | "+=" | "-=" | "*=" | "/=" | "%=" | "&=" | "|=" | "^=" | "<<=" | ">>="
        ) {
            Some(self.advance())
        } else {
            None
        }
    }
    fn special_statement(&mut self) -> Result<Option<NodeId>, ParseError> {
        let start = self.mark();
        let node = if self.eat("let").is_some() {
            let pattern = self.binding_pattern()?;
            let ty = if self.eat(":").is_some() {
                Some(self.ty()?)
            } else {
                None
            };
            self.expect("=")?;
            let value = self.expr(0, false)?;
            self.expect(";")?;
            self.push(start, NodeKind::Let { pattern, ty, value })
        } else if matches!(self.word(), "return" | "break") {
            let keyword = self.advance();
            let value = if self.word() == ";" {
                None
            } else {
                Some(self.expr(0, false)?)
            };
            self.expect(";")?;
            let kind = if &self.source[keyword.span.start..keyword.span.end] == "return" {
                NodeKind::Return { keyword, value }
            } else {
                NodeKind::Break { keyword, value }
            };
            self.push(start, kind)
        } else if matches!(self.word(), "continue" | "yield") {
            let keyword = self.advance();
            self.expect(";")?;
            let kind = if &self.source[keyword.span.start..keyword.span.end] == "continue" {
                NodeKind::Continue { keyword }
            } else {
                NodeKind::Yield { keyword }
            };
            self.push(start, kind)
        } else if self.word() == "move"
            && self
                .tokens
                .get(self.index + 1)
                .is_some_and(|t| t.kind == Kind::Name)
            && self.peek(2) == ";"
        {
            let keyword = self.advance();
            let name = self.ident()?;
            self.expect(";")?;
            self.push(start, NodeKind::NamedMove { keyword, name })
        } else if self.eat("while").is_some() {
            let condition = self.expr(0, true)?;
            let body = self.block()?;
            self.push(start, NodeKind::While { condition, body })
        } else if self.eat("for").is_some() {
            let pattern = self.binding_pattern()?;
            self.expect("in")?;
            let source = self.expr(0, true)?;
            let body = self.block()?;
            self.push(
                start,
                NodeKind::For {
                    pattern,
                    source,
                    body,
                },
            )
        } else {
            return Ok(None);
        };
        Ok(Some(node))
    }
    fn binding_pattern(&mut self) -> ResultNode {
        let start = self.mark();
        if self.eat("(").is_some() {
            let mut elements = vec![self.binding_pattern()?];
            self.expect(",")?;
            elements.push(self.binding_pattern()?);
            while !self.comma_end(")")? {
                elements.push(self.binding_pattern()?)
            }
            return Ok(self.push(start, NodeKind::Pattern(PatternSyntax::Tuple { elements })));
        }
        let mutable = self.eat("mut");
        if self.eat("_").is_some() {
            return Ok(self.push(start, NodeKind::Pattern(PatternSyntax::Wildcard)));
        }
        let name = self.ident()?;
        Ok(self.push(
            start,
            NodeKind::Pattern(PatternSyntax::Binding { mutable, name }),
        ))
    }
    fn pattern(&mut self) -> ResultNode {
        self.nested(|p| p.pattern_inner())
    }
    fn pattern_inner(&mut self) -> ResultNode {
        let start = self.mark();
        if self.eat("_").is_some() {
            return Ok(self.push(start, NodeKind::Pattern(PatternSyntax::Wildcard)));
        }
        if self.eat("(").is_some() {
            let mut elements = Vec::new();
            if self.eat(")").is_none() {
                loop {
                    elements.push(self.pattern()?);
                    if self.comma_end(")")? {
                        break;
                    }
                }
            }
            return Ok(self.push(start, NodeKind::Pattern(PatternSyntax::Tuple { elements })));
        }
        let mut segments = vec![self.ident()?];
        while self.word() == "::" {
            self.advance();
            segments.push(self.ident()?)
        }
        let path = self.push(
            start,
            NodeKind::Path {
                segments,
                arguments: vec![],
            },
        );
        let mut positional = None;
        let mut fields = None;
        if self.eat("(").is_some() {
            let mut list = vec![self.pattern()?];
            while !self.comma_end(")")? {
                list.push(self.pattern()?)
            }
            positional = Some(list)
        } else if self.eat("{").is_some() {
            let mut list = Vec::new();
            if self.eat("}").is_none() {
                loop {
                    let mark = self.mark();
                    let name = self.ident()?;
                    self.expect(":")?;
                    let binding = self.binding_pattern()?;
                    list.push(self.push(
                        mark,
                        NodeKind::Pattern(PatternSyntax::Field { name, binding }),
                    ));
                    if self.comma_end("}")? {
                        break;
                    }
                }
            }
            fields = Some(list)
        }
        Ok(self.push(
            start,
            NodeKind::Pattern(PatternSyntax::Variant {
                path,
                positional,
                fields,
            }),
        ))
    }
    fn binding_power(&self) -> Option<u8> {
        Some(match self.word() {
            "||" => 1,
            "&&" => 2,
            "==" | "!=" | "<" | "<=" | ">" | ">=" => 3,
            "|" => 4,
            "^" => 5,
            "&" => 6,
            "<<" | ">>" => 7,
            "+" | "-" => 8,
            "*" | "/" | "%" => 9,
            "as" => 10,
            _ => return None,
        })
    }
    fn expr(&mut self, min: u8, header: bool) -> ResultNode {
        self.nested(|p| p.expression(min, header))
    }
    fn expression(&mut self, min: u8, header: bool) -> ResultNode {
        let start = self.mark();
        let mut left = if matches!(self.word(), "-" | "!" | "~" | "*" | "&") {
            let operator = self.advance();
            let mutable = if &self.source[operator.span.start..operator.span.end] == "&" {
                self.eat("mut")
            } else {
                None
            };
            let operand = self.expr(11, header)?;
            self.push(
                start,
                NodeKind::Unary {
                    operator,
                    mutable,
                    operand,
                },
            )
        } else {
            let primary = self.primary(header)?;
            self.postfix(primary)?
        };
        let mut compared = false;
        while let Some(power) = self.binding_power() {
            if power < min {
                break;
            }
            if power == 3 && compared {
                return Err(self.error("comparison chaining requires explicit parentheses", &[]));
            }
            compared |= power == 3;
            let operator = self.advance();
            left = if &self.source[operator.span.start..operator.span.end] == "as" {
                let ty = self.numeric_cast_type()?;
                self.push(
                    start,
                    NodeKind::Conversion {
                        value: left,
                        operator,
                        ty,
                    },
                )
            } else {
                let right = self.expr(power + 1, header)?;
                self.push(
                    start,
                    NodeKind::Binary {
                        operator,
                        left,
                        right,
                    },
                )
            };
        }
        Ok(left)
    }
    // Cast targets are numeric terminals in the grammar, not arbitrary named
    // types. Do not consult a type table or consume following comparison tokens.
    fn numeric_cast_type(&mut self) -> ResultNode {
        if !matches!(
            self.word(),
            "i32" | "i64" | "u8" | "u16" | "u32" | "u64" | "usize" | "f32" | "f64"
        ) {
            return Err(self.error("expected a numeric type after as", &["numeric type"]));
        }
        let start = self.mark();
        let name = self.advance();
        Ok(self.push(
            start,
            NodeKind::Type(TypeSyntax::Path {
                segments: vec![name],
                arguments: vec![],
            }),
        ))
    }

    fn postfix(&mut self, mut value: NodeId) -> ResultNode {
        let start = self.start_of(value);
        loop {
            if let Some(operator) = self.eat("?") {
                value = self.push(start, NodeKind::Propagate { value, operator })
            } else if let Some(operator) = self.eat("!") {
                value = self.push(start, NodeKind::Unwrap { value, operator })
            } else if self.eat("(").is_some() {
                let inferred = match &self.nodes[value.0].kind {
                    NodeKind::Projection { member, .. } => matches!(
                        &self.source[member.span.start..member.span.end],
                        "new" | "try"
                    ),
                    _ => false,
                };
                let range_argument = matches!(&self.nodes[value.0].kind,
                    NodeKind::Projection { member, .. }
                        if &self.source[member.span.start..member.span.end] == "try_slice");
                let arguments = if range_argument && self.word() != ")" {
                    // The written suffix production selects a range when ..
                    // occurs. Keep an ordinary argument otherwise; no receiver
                    // type or method lookup participates in this choice.
                    let checkpoint = (self.index, self.piece, self.last_end, self.nodes.len());
                    match self.range(")") {
                        Ok(argument)
                            if matches!(self.nodes[argument.0].kind, NodeKind::Range { .. }) =>
                        {
                            self.expect(")")?;
                            vec![argument]
                        }
                        _ => {
                            self.restore(checkpoint);
                            self.arguments(inferred)?
                        }
                    }
                } else {
                    self.arguments(inferred)?
                };
                value = self.push(
                    start,
                    NodeKind::Call {
                        callee: value,
                        arguments,
                    },
                )
            } else if self.eat(".").is_some() {
                if let Some(keyword) = self.eat("await") {
                    value = self.push(start, NodeKind::Await { value, keyword })
                } else {
                    let member = if self.tokens[self.index].kind == Kind::Integer
                        && self.word().bytes().all(|b| b.is_ascii_digit())
                    {
                        self.advance()
                    } else {
                        self.ident()?
                    };
                    value = self.push(
                        start,
                        NodeKind::Projection {
                            base: value,
                            member,
                        },
                    )
                }
            } else if self.eat("[").is_some() {
                let index = self.range("]")?;
                self.expect("]")?;
                value = self.push(start, NodeKind::Index { base: value, index })
            } else {
                break;
            }
        }
        Ok(value)
    }
    fn arguments(&mut self, inferred: bool) -> Result<Vec<NodeId>, ParseError> {
        let mut args = Vec::new();
        if self.eat(")").is_some() {
            return Ok(args);
        }
        loop {
            args.push(if inferred && self.word() == "{" {
                let start = self.mark();
                let fields = self.initializer_fields()?;
                self.push(start, NodeKind::Construct { path: None, fields })
            } else {
                self.expr(0, false)?
            });
            if self.comma_end(")")? {
                break;
            }
        }
        Ok(args)
    }
    fn range(&mut self, close: &str) -> ResultNode {
        let start = self.mark();
        let first = if self.word() == ".." {
            None
        } else {
            Some(self.expr(0, false)?)
        };
        if let Some(separator) = self.eat("..") {
            let end = if self.word() == close || self.word() == "," {
                None
            } else {
                Some(self.expr(0, false)?)
            };
            Ok(self.push(
                start,
                NodeKind::Range {
                    start: first,
                    separator,
                    end,
                },
            ))
        } else {
            first.ok_or_else(|| self.error("expected index or range", &["expression", ".."]))
        }
    }
    fn initializer_fields(&mut self) -> Result<Vec<NodeId>, ParseError> {
        self.expect("{")?;
        let mut fields = Vec::new();
        if self.eat("}").is_some() {
            return Ok(fields);
        }
        loop {
            let start = self.mark();
            let name = self.ident()?;
            let value = if self.eat(":").is_some() {
                Some(self.expr(0, false)?)
            } else {
                None
            };
            fields.push(self.push(start, NodeKind::FieldInitializer { name, value }));
            if self.comma_end("}")? {
                break;
            }
        }
        Ok(fields)
    }
    fn primary(&mut self, header: bool) -> ResultNode {
        let start = self.mark();
        if self.eat("if").is_some() {
            let condition = if self.eat("let").is_some() {
                let mark = self.mark();
                let pattern = self.pattern()?;
                self.expect("=")?;
                let value = self.expr(0, true)?;
                self.push(mark, NodeKind::LetCondition { pattern, value })
            } else {
                self.expr(0, true)?
            };
            let yes = self.block()?;
            let no = if self.eat("else").is_some() {
                Some(if self.word() == "if" {
                    self.primary(false)?
                } else {
                    self.block()?
                })
            } else {
                None
            };
            return Ok(self.push(start, NodeKind::If { condition, yes, no }));
        }
        if self.eat("match").is_some() {
            let value = self.expr(0, true)?;
            self.expect("{")?;
            let mut arms = Vec::new();
            if self.word() == "}" {
                return Err(self.error("match requires at least one arm", &["pattern"]));
            }
            loop {
                let mark = self.mark();
                let pattern = self.pattern()?;
                self.expect("=>")?;
                let body = self.block()?;
                arms.push(self.push(mark, NodeKind::MatchArm { pattern, body }));
                if self.comma_end("}")? {
                    break;
                }
            }
            return Ok(self.push(start, NodeKind::Match { value, arms }));
        }
        if self.eat("loop").is_some() {
            let body = self.block()?;
            return Ok(self.push(start, NodeKind::Loop { body }));
        }
        if let Some(keyword) = self.eat("async") {
            let moving = self.eat("move");
            let body = self.block()?;
            return Ok(self.push(
                start,
                NodeKind::Async {
                    keyword,
                    moving,
                    body,
                },
            ));
        }
        let moving = self.eat("move");
        if matches!(self.word(), "|" | "||") {
            let mut parameters = Vec::new();
            if self.eat("||").is_none() {
                self.expect("|")?;
                parameters.push(self.parameter()?);
                while self.eat(",").is_some() {
                    if self.word() == "|" {
                        break;
                    }
                    parameters.push(self.parameter()?)
                }
                self.expect("|")?;
            }
            let result = if self.type_starts() {
                Some(self.ty()?)
            } else {
                None
            };
            let body = self.block()?;
            return Ok(self.push(
                start,
                NodeKind::Closure {
                    moving,
                    parameters,
                    result,
                    body,
                },
            ));
        }
        if let Some(keyword) = moving {
            let body = self.block()?;
            return Ok(self.push(start, NodeKind::MoveBlock { keyword, body }));
        }
        if self.word() == "{" || self.word() == "#" {
            return self.block();
        }
        if self.eat("@").is_some() {
            let keyword = self.expect("unchecked")?;
            self.unchecked += 1;
            let body = self.block();
            self.unchecked -= 1;
            return Ok(self.push(
                start,
                NodeKind::Unchecked {
                    keyword,
                    body: body?,
                },
            ));
        }
        if matches!(
            self.tokens[self.index].kind,
            Kind::Assembly | Kind::C | Kind::Cpp
        ) {
            if self.unchecked == 0 {
                return Err(self.error("foreign blocks must be inside @unchecked", &["@unchecked"]));
            }
            let includes = self.validate_foreign_header()?;
            let token = self.advance();
            return Ok(self.push(start, NodeKind::Foreign { token, includes }));
        }
        if self.eat("(").is_some() {
            let mut elements = Vec::new();
            if self.eat(")").is_some() {
                return Ok(self.push(start, NodeKind::Tuple { elements }));
            }
            let expression = self.expr(0, false)?;
            if self.eat(")").is_some() {
                return Ok(self.push(start, NodeKind::Parenthesized { expression }));
            }
            self.expect(",")?;
            elements.push(expression);
            elements.push(self.expr(0, false)?);
            while !self.comma_end(")")? {
                elements.push(self.expr(0, false)?)
            }
            return Ok(self.push(start, NodeKind::Tuple { elements }));
        }
        if self.eat("[").is_some() {
            let mut elements = Vec::new();
            let mut repeat = None;
            if self.eat("]").is_none() {
                elements.push(self.expr(0, false)?);
                if self.eat(";").is_some() {
                    repeat = Some(self.expr(0, false)?);
                    self.expect("]")?;
                } else {
                    while !self.comma_end("]")? {
                        elements.push(self.expr(0, false)?);
                    }
                }
            }
            return Ok(self.push(start, NodeKind::Array { elements, repeat }));
        }
        if matches!(
            self.tokens[self.index].kind,
            Kind::Integer | Kind::Float | Kind::Text
        ) || matches!(self.word(), "true" | "false")
        {
            let token = self.advance();
            return Ok(self.push(start, NodeKind::Literal { token }));
        }
        let segments = self.path_segments()?;
        let mut arguments = Vec::new();
        let mut segments = segments;
        if self.word() == "<" {
            let checkpoint = (self.index, self.piece, self.last_end, self.nodes.len());
            if let Ok(args) = self.type_arguments() {
                if self.eat("::").is_some() {
                    segments.push(self.ident()?);
                    arguments = args;
                } else {
                    self.restore(checkpoint)
                }
            } else {
                self.restore(checkpoint)
            }
        }
        let path = self.push(
            start,
            NodeKind::Path {
                segments,
                arguments,
            },
        );
        if !header && self.word() == "{" {
            let fields = self.initializer_fields()?;
            Ok(self.push(
                start,
                NodeKind::Construct {
                    path: Some(path),
                    fields,
                },
            ))
        } else {
            Ok(path)
        }
    }
    fn restore(&mut self, c: (usize, usize, usize, usize)) {
        self.index = c.0;
        self.piece = c.1;
        self.last_end = c.2;
        self.nodes.truncate(c.3);
    }
    fn validate_foreign_header(&self) -> Result<Vec<TokenRef>, ParseError> {
        let Payload::Foreign(block) = &self.tokens[self.index].payload else {
            return Err(self.error("missing lexical foreign payload", &[]));
        };
        let tokens = &block.header_tokens;
        let mut i = 0;
        let text = |i: usize| {
            tokens
                .get(i)
                .map_or("", |t| &self.source[t.span.start..t.span.end])
        };
        if text(i).is_empty() {
            return Ok(Vec::new());
        }
        if self.tokens[self.index].kind == Kind::Assembly {
            return Err(self.error("@asm does not take header options", &["{"]));
        }
        for expected in ["(", "includes", "=", "{"] {
            if text(i) != expected {
                return Err(self.error("invalid foreign includes header", &[expected]));
            }
            i += 1;
        }
        let mut includes = Vec::new();
        if text(i) != "}" {
            loop {
                if tokens.get(i).is_none_or(|t| t.kind != Kind::Text) {
                    return Err(self.error("header include must be a string", &["string"]));
                }
                includes.push(TokenRef {
                    index: self.index,
                    span: tokens[i].span,
                });
                i += 1;
                if text(i) != "," {
                    break;
                }
                i += 1;
                if text(i) == "}" {
                    break;
                }
            }
        }
        for expected in ["}", ")", ""] {
            if text(i) != expected {
                return Err(self.error("invalid foreign includes header", &[expected]));
            }
            i += 1;
        }
        Ok(includes)
    }
}
