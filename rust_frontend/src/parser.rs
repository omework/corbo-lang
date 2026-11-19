use crate::{
    Error,
    lexer::{Kind, Token},
};
use std::collections::HashSet;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct NodeId(pub usize);

#[derive(Clone, Copy, Debug)]
pub enum Mode {
    Program,
    Block,
    Signature,
}

#[derive(Debug)]
pub struct Node {
    pub public: bool,
    pub asm_operand: Option<crate::Span>,
    pub kind: &'static str,
    pub start: usize,
    pub end: usize,
    pub name: Option<usize>,
    pub children: Vec<NodeId>,
}

#[derive(Debug)]
pub struct Syntax {
    pub nodes: Vec<Node>,
    pub root: NodeId,
}

pub fn parse(source: &str, tokens: &[Token], mode: Mode) -> Result<Syntax, Error> {
    parse_with_names(source, tokens, mode, &[], false)
}

pub(crate) fn parse_with_names(
    source: &str,
    tokens: &[Token],
    mode: Mode,
    imported_names: &[String],
    discovering_package: bool,
) -> Result<Syntax, Error> {
    let names = tokens
        .windows(2)
        .filter_map(|pair| {
            let word = &source[pair[0].span.start..pair[0].span.end];
            (word == "struct" || word == "enum")
                .then(|| &source[pair[1].span.start..pair[1].span.end])
        })
        .chain(imported_names.iter().map(String::as_str))
        .collect();
    let mut p = Parser {
        source,
        tokens,
        i: 0,
        nodes: Vec::new(),
        names,
        depth: 0,
        unchecked_depth: 0,
        empty_constructor: true,
        discovering_package,
    };
    let children = match mode {
        Mode::Program => {
            let mut declarations = Vec::new();
            if p.word() == "#" && p.word_at(p.i + 1) == "(" && p.word_at(p.i + 2) == "datastack" {
                declarations.push(p.datastack_annotation()?);
            }
            while !p.eof() {
                declarations.push(if p.word() == "use" { p.import()? } else { p.item(false)? });
            }
            declarations
        }
        Mode::Signature => vec![p.item(true)?],
        Mode::Block => p.statements("")?,
    };
    if !p.eof() {
        return Err(p.error("tokens après la fin de la construction"));
    }
    let root = p.node("programme", 0, None, children);
    Ok(Syntax {
        nodes: p.nodes,
        root,
    })
}

type Res<T> = Result<T, Error>;

struct Parser<'a> {
    source: &'a str,
    tokens: &'a [Token],
    i: usize,
    nodes: Vec<Node>,
    names: HashSet<&'a str>,
    depth: usize,
    unchecked_depth: usize,
    empty_constructor: bool,
    discovering_package: bool,
}

impl<'a> Parser<'a> {
    fn word_at(&self, i: usize) -> &'a str {
        self.tokens
            .get(i)
            .map_or("", |t| &self.source[t.span.start..t.span.end])
    }
    fn word(&self) -> &'a str {
        self.word_at(self.i)
    }
    fn eof(&self) -> bool {
        self.tokens[self.i].kind == Kind::Eof
    }
    fn error(&self, msg: &'static str) -> Error {
        Error::new(self.tokens[self.i].span.start, msg)
    }
    fn eat(&mut self, s: &str) -> bool {
        if !self.eof() && self.word() == s {
            self.i += 1;
            true
        } else {
            false
        }
    }
    fn expect(&mut self, s: &'static str) -> Res<()> {
        if self.eat(s) {
            Ok(())
        } else {
            Err(self.error(s))
        }
    }
    fn name(&mut self) -> Res<usize> {
        if self.tokens[self.i].kind != Kind::Name {
            return Err(self.error("nom attendu"));
        }
        let i = self.i;
        self.i += 1;
        Ok(i)
    }
    fn declaration_name(&mut self, allow_self: bool) -> Res<usize> {
        let token = self.name()?;
        let word = self.word_at(token);
        if word == "self" && allow_self {
            return Ok(token);
        }
        if matches!(
            word,
            "_" | "runtime"
                | "self"
                | "fn"
                | "struct"
                | "enum"
                | "impl"
                | "const"
                | "let"
                | "mut"
                | "if"
                | "else"
                | "match"
                | "loop"
                | "while"
                | "return"
                | "break"
                | "continue"
                | "as"
                | "true"
                | "false"
                | "bool"
                | "Void"
                | "i32"
                | "i64"
                | "u8"
                | "u16"
                | "u32"
                | "u64"
                | "usize"
                | "addr"
                | "f32"
                | "f64"
                | "str"
                | "char"
                | "String"
                | "NumericConversionError"
                | "A"
                | "Pool"
                | "Vector"
                | "Option"
                | "Result"
                | "Mutex"
                | "AsyncMutex"
                | "HashMap"
        ) {
            return Err(Error::new(self.tokens[token].span.start, "nom réservé"));
        }
        Ok(token)
    }
    fn node(
        &mut self,
        kind: &'static str,
        start: usize,
        name: Option<usize>,
        children: Vec<NodeId>,
    ) -> NodeId {
        let id = NodeId(self.nodes.len());
        self.nodes.push(Node {
            public: false,
            asm_operand: None,
            kind,
            start,
            end: self.i,
            name,
            children,
        });
        id
    }
    fn nested<T>(&mut self, f: impl FnOnce(&mut Self) -> Res<T>) -> Res<T> {
        if self.depth >= 128 {
            return Err(self.error("imbrication syntaxique trop profonde"));
        }
        self.depth += 1;
        let result = f(self);
        self.depth -= 1;
        result
    }
    fn list(
        &mut self,
        close: &'static str,
        mut item: impl FnMut(&mut Self) -> Res<NodeId>,
    ) -> Res<Vec<NodeId>> {
        let mut result = Vec::new();
        while self.word() != close {
            result.push(item(self)?);
            if !self.eat(",") {
                break;
            }
        }
        self.expect(close)?;
        Ok(result)
    }
    fn path(&mut self) -> Res<usize> {
        let start = self.name()?;
        while self.eat("::") {
            self.name()?;
        }
        Ok(start)
    }
    fn annotation(&mut self) -> Res<NodeId> {
        self.parse_annotation(false)
    }

    fn datastack_annotation(&mut self) -> Res<NodeId> {
        self.parse_annotation(true)
    }

    fn parse_annotation(&mut self, global: bool) -> Res<NodeId> {
        let start = self.i;
        self.expect("#")?;
        self.expect("(")?;
        let name = self.name()?;
        let mut properties = Vec::new();
        match self.word_at(name) {
            "datastack" => {
                if !global {
                    return Err(self.error("annotation datastack attendue en tête du programme"));
                }
                self.expect(":")?;
                let mut seen = HashSet::new();
                if self.word() != ")" {
                    loop {
                        let property = self.i;
                        let name = self.word();
                        if !matches!(name, "size" | "region_stack_size" | "region_size" | "reclaim_threshold" | "region_reclaim_threshold") {
                            return Err(self.error("propriété de datastack inconnue"));
                        }
                        if !seen.insert(name) {
                            return Err(self.error("propriété de datastack répétée"));
                        }
                        self.i += 1;
                        self.expect("=")?;
                        let digits = self.word();
                        if digits.is_empty()
                            || !digits.bytes().all(|digit| digit.is_ascii_digit())
                            || digits.bytes().all(|digit| digit == b'0')
                        {
                            return Err(
                                self.error("taille de datastack décimale positive attendue")
                            );
                        }
                        let size = self.integer()?;
                        if !matches!(self.word(), "K" | "M" | "G") {
                            return Err(self.error("unité K, M ou G attendue"));
                        }
                        self.i += 1;
                        properties.push(self.node(
                            "taille de datastack",
                            property,
                            Some(property),
                            vec![size],
                        ));
                        if !self.eat(",") {
                            break;
                        }
                    }
                }
            }
            "free_pages" => {}
            "stack_region" => {
                self.expect(":")?;
                let property = self.i;
                self.expect("max_size")?;
                self.expect("=")?;
                let size = self.positive_decimal()?;
                if !matches!(self.word(), "K" | "M" | "G") {
                    return Err(self.error("unité K, M ou G attendue"));
                }
                self.i += 1;
                properties.push(self.node(
                    "taille de datastack",
                    property,
                    Some(property),
                    vec![size],
                ));
                if self.eat(",") {
                    let property = self.i;
                    self.expect("count")?;
                    self.expect("=")?;
                    let count = self.positive_decimal()?;
                    properties.push(self.node(
                        "nombre de régions",
                        property,
                        Some(property),
                        vec![count],
                    ));
                }
            }
            "directive" => {
                self.expect(":")?;
                let property = self.i;
                if self.eat("async_pool_sizes") {
                    self.expect("=")?;
                    self.expect("{")?;
                    let entries = self.list("}", |p| {
                        let start = p.i;
                        let key = p.path()?;
                        p.expect(":")?;
                        let capacity = p.integer()?;
                        Ok(p.node("capacité", start, Some(key), vec![capacity]))
                    })?;
                    if entries.is_empty() {
                        return Err(self.error("capacité attendue"));
                    }
                    properties.push(self.node("capacités", property, Some(property), entries));
                } else {
                    self.expect("stack_region_max_size")?;
                    self.expect("=")?;
                    let digits = self.word();
                    if digits.is_empty()
                        || !digits.bytes().all(|b| b.is_ascii_digit())
                        || digits.bytes().all(|b| b == b'0')
                    {
                        return Err(self.error("taille de région positive attendue"));
                    }
                    let size = self.integer()?;
                    if !matches!(self.word(), "K" | "M" | "G") {
                        return Err(self.error("unité K, M ou G attendue"));
                    }
                    self.i += 1;
                    properties.push(self.node("région", property, Some(property), vec![size]));
                }
            }
            "type" => {
                self.expect(":")?;
                let carrier = self.name()?;
                if self.eat("*") {
                    properties.push(self.node("type libre", carrier, Some(carrier), vec![]));
                } else {
                    if self.eat("<") {
                    let parameter = self.name()?;
                    let mut alternatives = Vec::new();
                    if self.eat(":") {
                        alternatives.push(self.ty()?);
                        while self.eat(",") {
                            alternatives.push(self.ty()?);
                        }
                    }
                    self.expect(">")?;
                    properties.push(self.node(
                        "paramètre de type",
                        parameter,
                        Some(parameter),
                        alternatives,
                    ));
                    }
                    let with = self.eat("with");
                    self.expect("{")?;
                    let mut methods = Vec::new();
                    while !self.eat("}") {
                        let start = self.i;
                        let asynchronous = self.eat("async");
                        self.expect("fn")?;
                        methods.push(self.function(start, vec![], asynchronous, false, true, true)?);
                        self.expect(";")?;
                    }
                    if methods.is_empty() {
                        return Err(self.error("exigence de méthode attendue"));
                    }
                    properties.push(self.node(
                        if with { "type avec" } else { "type exact" },
                        carrier,
                        Some(carrier),
                        methods,
                    ));
                }
            }
            "lock" => {
                self.expect(":")?;
                self.expect("on")?;
                self.expect("=")?;
                let target = self.i;
                self.expect("self")?;
                let through = self.eat(",");
                if through {
                    self.expect("through_result")?;
                    self.expect("=")?;
                    self.expect("true")?;
                }
                properties.push(self.node(
                    if through {
                        "verrou lié au résultat"
                    } else {
                        "verrou"
                    },
                    target,
                    Some(target),
                    vec![],
                ));
            }
            "branch" => {
                if self.eat(":") {
                    self.expect("join")?;
                    self.expect("=")?;
                    self.expect("result")?;
                    self.expect(".")?;
                    let end = self.name()?;
                    if self.word_at(end) != "await" {
                        self.expect("(")?;
                        self.expect(")")?;
                    }
                    properties.push(self.node("fin de branche", end, Some(end), vec![]));
                }
            }
            _ => return Err(self.error("annotation inconnue")),
        }
        self.expect(")")?;
        Ok(self.node("annotation", start, Some(name), properties))
    }
    fn item(&mut self, signature: bool) -> Res<NodeId> {
        let start = self.i;
        let public = self.eat("pub");
        let node = self.declaration(signature)?;
        if public && !matches!(self.nodes[node.0].kind, "fn" | "async fn" | "extern" | "struct" | "enum" | "const") {
            return Err(self.error("pub exige une fonction, un type nommé ou une constante"));
        }
        if public && self.nodes[node.0].public { return Err(self.error("pub répété")); }
        self.nodes[node.0].public |= public;
        self.nodes[node.0].start = start;
        Ok(node)
    }

    fn import(&mut self) -> Res<NodeId> {
        let start = self.i;
        self.expect("use")?;
        let path = self.name()?;
        self.expect("::")?;
        loop {
            if self.eat("{") {
                let members = self.list("}", |p| {
                    let start = p.i;
                    let name = p.name()?;
                    let alias = p.import_alias()?;
                    Ok(p.node("import member", start, Some(name), alias))
                })?;
                if members.is_empty() {
                    return Err(self.error("empty import group"));
                }
                self.expect(";")?;
                return Ok(self.node("use", start, Some(path), members));
            }
            self.name()?;
            if !self.eat("::") {
                let alias = self.import_alias()?;
                self.expect(";")?;
                return Ok(self.node("use", start, Some(path), alias));
            }
        }
    }

    fn import_alias(&mut self) -> Res<Vec<NodeId>> {
        if !self.eat("as") {
            return Ok(vec![]);
        }
        let name = self.declaration_name(false)?;
        Ok(vec![self.node("import alias", name, Some(name), vec![])])
    }

    fn declaration(&mut self, signature: bool) -> Res<NodeId> {
        let start = self.i;
        let mut annotations = Vec::new();
        while self.word() == "#" {
            let annotation = self.annotation()?;
            let tag = self.nodes[annotation.0].name.unwrap();
            if matches!(self.word_at(tag), "stack_region" | "free_pages") {
                return Err(self.error("annotation de bloc attendue avant les accolades"));
            }
            if self.word_at(tag) == "datastack" {
                return Err(self.error("annotation datastack attendue en tête du programme"));
            }
            if self.word_at(tag) == "directive" {
                if annotations.is_empty() {
                    return Ok(annotation);
                }
                return Err(self.error("directive après contrat"));
            }
            annotations.push(annotation);
        }
        let public = self.eat("pub");
        let asynchronous = self.eat("async");
        let external = self.eat("extern");
        if external {
            self.expect("\"C\"")?;
        }
        if self.eat("fn") {
            let function = self.function(start, annotations, asynchronous, external, signature, false)?;
            self.nodes[function.0].public = public;
            return Ok(function);
        }
        if !asynchronous && !external && self.eat("struct") {
            if annotations.iter().any(|id| self.nodes[id.0].name.is_none_or(|name| self.word_at(name) != "type")) {
                return Err(self.error("seuls les contrats de type peuvent annoter une struct"));
            }
            let name = self.declaration_name(false)?;
            annotations.extend(self.generic_parameters()?);
            annotations.extend(self.fields(true)?);
            let record = self.node("struct", start, Some(name), annotations);
            self.nodes[record.0].public = public;
            return Ok(record);
        }
        if !asynchronous && !external && self.eat("enum") {
            if annotations.iter().any(|id| self.nodes[id.0].name.is_none_or(|name| self.word_at(name) != "type")) {
                return Err(self.error("seuls les contrats de type peuvent annoter une enum"));
            }
            let name = self.declaration_name(false)?;
            annotations.extend(self.generic_parameters()?);
            self.expect("{")?;
            let variants = self.list("}", |p| {
                let start = p.i;
                let name = p.declaration_name(false)?;
                let fields = if p.word() == "{" { p.fields(true)? }
                else if p.eat("(") {
                    if p.word() == ")" { return Err(p.error("type positionnel attendu")); }
                    p.list(")", |p| {
                        let start = p.i;
                        let ty = p.ty()?;
                        Ok(p.node("champ positionnel", start, None, vec![ty]))
                    })?
                } else { vec![] };
                Ok(p.node("variante", start, Some(name), fields))
            })?;
            if variants.is_empty() { return Err(self.error("enum vide")); }
            annotations.extend(variants);
            let enumeration = self.node("enum", start, Some(name), annotations);
            self.nodes[enumeration.0].public = public;
            return Ok(enumeration);
        }
        if asynchronous || external || !annotations.is_empty() {
            return Err(self.error("fn attendu"));
        }
        if self.eat("const") {
            return self.constant(start);
        }
        if self.eat("impl") {
            let name = self.path()?;
            let mut methods = self.generic_parameters()?;
            self.expect("{")?;
            while !self.eat("}") {
                let start = self.i;
                if self.eat("const") {
                    methods.push(self.constant(start)?);
                    continue;
                }
                let mut annotations = Vec::new();
                if self.word() == "#" {
                    annotations.push(self.annotation()?);
                }
                let asynchronous = self.eat("async");
                self.expect("fn")?;
                methods.push(self.function(start, annotations, asynchronous, false, false, true)?);
            }
            return Ok(self.node("impl", start, Some(name), methods));
        }
        Err(self.error("déclaration attendue"))
    }
    fn generic_parameters(&mut self) -> Res<Vec<NodeId>> {
        if !self.eat("<") { return Ok(vec![]); }
        let mut seen = HashSet::new();
        let parameters = self.list(">", |p| {
            let name = p.declaration_name(false)?;
            if !seen.insert(p.word_at(name)) { return Err(p.error("paramètre de type répété")); }
            Ok(p.node("type libre", name, Some(name), vec![]))
        })?;
        if parameters.is_empty() { return Err(self.error("paramètre de type attendu")); }
        Ok(parameters)
    }

    fn constant(&mut self, start: usize) -> Res<NodeId> {
        let name = self.declaration_name(false)?;
        self.expect(":")?;
        let ty = self.ty()?;
        self.expect("=")?;
        let literal_start = self.i;
        let negative = self.eat("-");
        let literal = self.i;
        if !(matches!(self.tokens[literal].kind, Kind::Integer | Kind::Float)
            || !negative && matches!(self.word(), "true" | "false"))
        {
            return Err(self.error("littéral scalaire attendu pour la constante"));
        }
        self.i += 1;
        let value = self.node("littéral", literal, Some(literal), vec![]);
        let value = if negative {
            self.node("unaire", literal_start, Some(literal_start), vec![value])
        } else {
            value
        };
        self.expect(";")?;
        Ok(self.node("const", start, Some(name), vec![ty, value]))
    }

    fn function(
        &mut self,
        start: usize,
        mut children: Vec<NodeId>,
        asynchronous: bool,
        external: bool,
        signature: bool,
        method: bool,
    ) -> Res<NodeId> {
        let name = if method && self.word() == "addr" {
            self.name()?
        } else {
            self.declaration_name(false)?
        };
        self.expect("(")?;
        children.extend(self.list(")", Self::parameter)?);
        if self.eat("->") {
            children.push(self.ty()?);
        }
        if external {
            self.expect(";")?;
        } else if !signature {
            children.push(self.block()?);
        }
        Ok(self.node(
            if external {
                "extern"
            } else if asynchronous {
                "async fn"
            } else {
                "fn"
            },
            start,
            Some(name),
            children,
        ))
    }
    fn parameter(&mut self) -> Res<NodeId> {
        let start = self.i;
        let reference = self.eat("&");
        self.eat("mut");
        let name = self.declaration_name(true)?;
        let mut children = Vec::new();
        if !reference || self.word_at(name) != "self" {
            self.expect(":")?;
            children.push(self.ty()?);
        }
        Ok(self.node("paramètre", start, Some(name), children))
    }
    fn ty(&mut self) -> Res<NodeId> {
        self.nested(|p| {
            let start = p.i;
            let mut children = Vec::new();
            let name;
            if p.eat("&") || p.eat("&&") {
                p.eat("mut");
                children.push(p.ty()?);
                name = None;
            } else if p.eat("[") {
                children.push(p.ty()?);
                if p.eat(";") {
                    children.push(p.integer()?);
                }
                p.expect("]")?;
                name = None;
            } else if p.eat("(") {
                children = p.list(")", Self::ty)?;
                if children.len() == 1 {
                    return Err(p.error("tuple type requires at least two elements"));
                }
                name = None;
            } else if p.eat("fn") {
                p.expect("(")?;
                children.extend(p.list(")", Self::ty)?);
                p.expect("->")?;
                children.push(p.ty()?);
                name = Some(start);
            } else {
                name = Some(p.path()?);
                if p.word() == "<" {
                    children = p.type_arguments()?;
                }
            }
            Ok(p.node("type", start, name, children))
        })
    }
    fn type_arguments(&mut self) -> Res<Vec<NodeId>> {
        self.expect("<")?;
        let mut arguments = vec![self.ty()?];
        while self.eat(",") {
            arguments.push(self.ty()?);
        }
        self.expect(">")?;
        Ok(arguments)
    }

    fn positive_decimal(&mut self) -> Res<NodeId> {
        let digits = self.word();
        if digits.is_empty()
            || !digits.bytes().all(|digit| digit.is_ascii_digit())
            || digits.bytes().all(|digit| digit == b'0')
        {
            return Err(self.error("entier décimal strictement positif attendu"));
        }
        self.integer()
    }
    fn integer(&mut self) -> Res<NodeId> {
        let start = self.i;
        if self.tokens[start].kind != Kind::Integer {
            return Err(self.error("entier attendu"));
        }
        self.i += 1;
        Ok(self.node("littéral", start, Some(start), vec![]))
    }
    fn fields(&mut self, types: bool) -> Res<Vec<NodeId>> {
        self.expect("{")?;
        self.named_fields("}", types)
    }
    fn named_fields(&mut self, close: &'static str, types: bool) -> Res<Vec<NodeId>> {
        self.list(close, |p| {
            let start = p.i;
            let name = p.name()?;
            p.expect(":")?;
            let value = if types { p.ty()? } else { p.expr(0, false)? };
            Ok(p.node("champ", start, Some(name), vec![value]))
        })
    }
    fn block(&mut self) -> Res<NodeId> {
        self.nested(|p| {
            let start = p.i;
            let mut children = Vec::new();
            if p.word() == "#" {
                let annotation = p.annotation()?;
                let region = p.nodes[annotation.0].name.is_some_and(|name| p.word_at(name) == "stack_region");
                children.push(annotation);
                if region && p.word() == "#" && p.word_at(p.i + 2) == "free_pages" {
                    children.push(p.annotation()?);
                }
            }
            p.expect("{")?;
            children.extend(p.statements("}")?);
            p.expect("}")?;
            Ok(p.node("scope", start, None, children))
        })
    }
    fn statements(&mut self, close: &'static str) -> Res<Vec<NodeId>> {
        let mut children = Vec::new();
        let mut imports = true;
        while self.word() != close && !self.eof() {
            let statement = self.statement(imports, close)?;
            imports &= self.nodes[statement.0].kind == "move nommé";
            children.push(statement);
        }
        Ok(children)
    }
    fn statement(&mut self, imports: bool, close: &str) -> Res<NodeId> {
        let start = self.i;
        if self.tokens[self.i].kind == Kind::Assembly {
            if self.unchecked_depth == 0 {
                return Err(self.error("@asm exige un bloc @unchecked"));
            }
            let span = self.tokens[self.i].span;
            let template = &self.source[span.start..span.end];
            let body = template.find('{').unwrap() + 1;
            let mut operands = Vec::new();
            let mut line_start = span.start + body;
            for line in template[body..template.len() - 1].split_inclusive('\n') {
                let code = line.split_once("//").map_or(line, |(code, _)| code);
                for (offset, _) in code.match_indices("${") {
                    let name = &code[offset + 2..];
                    let name_len = name.find('}').unwrap();
                    let start_byte = line_start + offset + 2;
                    let node = self.node("opérande asm", start, None, vec![]);
                    self.nodes[node.0].asm_operand = Some(crate::Span {
                        start: start_byte,
                        end: start_byte + name_len,
                    });
                    operands.push(node);
                }
                line_start += line.len();
            }
            self.i += 1;
            return Ok(self.node("asm", start, None, operands));
        }
        if self.eat("@") {
            self.expect("unchecked")?;
            if self.word() != "{" {
                return Err(self.error("@unchecked exige un bloc délimité"));
            }
            self.unchecked_depth += 1;
            let block = self.block();
            self.unchecked_depth -= 1;
            return Ok(self.node("unchecked", start, None, vec![block?]));
        }
        if self.eat("let") {
            if self.eat("(") {
                let bindings = self.list(")", |p| {
                    let start = p.i;
                    p.eat("mut");
                    let name = p.declaration_name(false)?;
                    Ok(p.node("tuple binding", start, Some(name), vec![]))
                })?;
                if bindings.len() < 2 {
                    return Err(self.error("tuple pattern requires at least two bindings"));
                }
                let mut children = Vec::new();
                if self.eat(":") {
                    children.push(self.ty()?);
                }
                self.expect("=")?;
                children.push(self.expr(0, false)?);
                self.expect(";")?;
                children.extend(bindings);
                return Ok(self.node("tuple let", start, None, children));
            }
            self.eat("mut");
            let name = self.declaration_name(false)?;
            let mut children = Vec::new();
            if self.eat(":") {
                children.push(self.ty()?);
            }
            self.expect("=")?;
            children.push(self.expr(0, false)?);
            self.expect(";")?;
            return Ok(self.node("liaison", start, Some(name), children));
        }
        if self.word() == "move" && self.word_at(start + 2) == ";" {
            if !imports {
                return Err(self.error("move nommé réservé à l’entrée du bloc"));
            }
            self.i += 1;
            let name = self.name()?;
            self.expect(";")?;
            return Ok(self.node("move nommé", start, Some(name), vec![]));
        }
        let control = self.word();
        if matches!(control, "return" | "break" | "continue" | "yield") {
            self.i += 1;
            let mut children = Vec::new();
            if matches!(control, "return" | "break") && self.word() != ";" {
                children.push(self.expr(0, false)?);
            }
            self.expect(";")?;
            let kind = match control {
                "return" => "return",
                "break" => "break",
                "continue" => "continue",
                _ => "yield",
            };
            return Ok(self.node(kind, start, None, children));
        }
        if self.eat("while") {
            let (test, body) = self.test_and_block()?;
            return Ok(self.node("while", start, None, vec![test, body]));
        }
        let left = self.expr(0, false)?;
        let width = self.assignment_width();
        if width != 0 {
            let op = self.i;
            self.i += width;
            let right = self.expr(0, false)?;
            self.expect(";")?;
            return Ok(self.node("affectation", start, Some(op), vec![left, right]));
        }
        if self.eat(";") {
            return Ok(self.node("instruction", start, None, vec![left]));
        }
        if self.word() == close || self.eof() {
            return Ok(self.node("résultat", start, None, vec![left]));
        }
        if matches!(
            self.nodes[left.0].kind,
            "scope" | "if" | "match" | "loop" | "move bloc" | "unsafe"
        ) {
            return Ok(self.node("instruction", start, None, vec![left]));
        }
        Err(self.error("point-virgule attendu"))
    }
    fn expr(&mut self, min: u8, before_block: bool) -> Res<NodeId> {
        self.nested(|p| p.expression(min, before_block))
    }
    fn assignment_width(&self) -> usize {
        if matches!(self.word(), "=" | "+=" | "-=" | "*=" | "/=" | "%=" | "&=" | "|=" | "^=" | "<<=") {
            return 1;
        }
        if self.word() == ">" && self.word_at(self.i + 1) == ">" && self.word_at(self.i + 2) == "="
            && self.tokens[self.i].span.end == self.tokens[self.i + 1].span.start
            && self.tokens[self.i + 1].span.end == self.tokens[self.i + 2].span.start
        {
            return 3;
        }
        0
    }

    fn operator(&self) -> Option<(u8, usize)> {
        let word = self.word();
        if word == ">" && self.assignment_width() == 3 {
            return None;
        }
        if word == ">"
            && self
                .tokens
                .get(self.i + 1)
                .is_some_and(|t| self.tokens[self.i].span.end == t.span.start)
        {
            match self.word_at(self.i + 1) {
                ">" => return Some((7, 2)),
                "=" => return Some((6, 2)),
                _ => {}
            }
        }
        Some((
            match word {
                "||" => 1,
                "&&" => 2,
                "|" => 3,
                "^" => 4,
                "&" => 5,
                "==" | "!=" | "<" | ">" | "<=" => 6,
                "<<" => 7,
                "+" | "-" => 8,
                "*" | "/" | "%" => 9,
                "as" => 10,
                _ => return None,
            },
            1,
        ))
    }
    fn expression(&mut self, min: u8, before_block: bool) -> Res<NodeId> {
        let start = self.i;
        let mut left = if matches!(self.word(), "&" | "*" | "-" | "!" | "~") {
            let op = self.i;
            self.i += 1;
            if self.word_at(op) == "&" {
                self.eat("mut");
            }
            let operand = self.expr(11, before_block)?;
            let kind = match self.word_at(op) {
                "&" => "emprunt",
                "*" => "indirection",
                _ => "unaire",
            };
            self.node(kind, start, Some(op), vec![operand])
        } else {
            self.primary(before_block)?
        };
        loop {
            if self.eat("?") {
                left = self.node("propagation", start, Some(self.i - 1), vec![left]);
            } else if self.eat("(") {
                let args = self.list(")", |p| p.expr(0, false))?;
                let mut children = vec![left];
                children.extend(args);
                left = self.node("appel", start, None, children);
            } else if self.eat(".") {
                let member = self.name()?;
                if self.word_at(member) == "await" {
                    left = self.node("await", start, Some(member), vec![left]);
                } else if self.eat("(") {
                    let mut children = vec![left];
                    if self.word_at(member) == "new" && self.word() == "{"
                        && (self.word_at(self.i + 1) == "}" || self.word_at(self.i + 2) == ":")
                    {
                        let start = self.i;
                        let fields = self.fields(false)?;
                        self.expect(")")?;
                        children.push(self.node("initialiseur pool", start, None, fields));
                    } else if self.word_at(self.i + 1) == ":" {
                        children.extend(self.named_fields(")", false)?);
                    } else {
                        children.extend(self.list(")", |p| {
                            if p.word_at(member) == "try_slice" {
                                p.range()
                            } else {
                                p.expr(0, false)
                            }
                        })?);
                    }
                    left = self.node("appel méthode", start, Some(member), children);
                } else if self.word() == "{" && self.is_constructor(left, before_block) {
                    let mut children = vec![left];
                    children.extend(self.fields(false)?);
                    left = self.node("construction", start, Some(member), children);
                } else {
                    left = self.node("projection", start, Some(member), vec![left]);
                }
            } else if self.eat("[") {
                let index = self.range()?;
                self.expect("]")?;
                left = self.node("indice", start, None, vec![left, index]);
            } else {
                break;
            }
        }
        let mut compared = false;
        while let Some((binding, width)) = self.operator() {
            if binding < min {
                break;
            }
            if binding == 6 && compared {
                return Err(self.error("comparaison chaînée"));
            }
            compared |= binding == 6;
            let op = self.i;
            self.i += width;
            let right = if self.word_at(op) == "as" {
                self.ty()?
            } else {
                self.expr(binding + 1, before_block)?
            };
            left = self.node("binaire", start, Some(op), vec![left, right]);
        }
        Ok(left)
    }
    fn range(&mut self) -> Res<NodeId> {
        let start = self.i;
        let mut bounds = Vec::new();
        if self.word() != ".." {
            bounds.push(self.expr(0, false)?);
        }
        let separator = self.i;
        if !self.eat("..") {
            return Ok(bounds[0]);
        }
        if !matches!(self.word(), "]" | ")" | ",") {
            bounds.push(self.expr(0, false)?);
        }
        Ok(self.node("plage", start, Some(separator), bounds))
    }
    fn test_and_block(&mut self) -> Res<(NodeId, NodeId)> {
        let start = self.i;
        let checkpoint = self.nodes.len();
        if let Ok(test) = self.expr(0, true) {
            if matches!(self.word(), "{" | "#") {
                return Ok((test, self.block()?));
            }
        }
        self.i = start;
        self.nodes.truncate(checkpoint);
        let previous = std::mem::replace(&mut self.empty_constructor, false);
        let test = self.expr(0, true);
        self.empty_constructor = previous;
        Ok((test?, self.block()?))
    }
    fn is_constructor(&self, base: NodeId, before_block: bool) -> bool {
        let node = &self.nodes[base.0];
        let nominal = node.name.is_some_and(|i| {
            let mut last = i;
            while self.word_at(last + 1) == "::" && last + 2 < node.end {
                last += 2;
            }
            self.names.contains(self.word_at(last))
                || self
                    .word_at(last)
                    .starts_with(|c: char| c.is_ascii_uppercase())
        });
        (nominal || self.discovering_package
            && matches!(node.kind, "nom" | "nom qualifié")
            && (!before_block || self.word_at(self.i + 2) == ":"))
            && (!before_block
                || self.word_at(self.i + 2) == ":"
                || self.empty_constructor && self.word_at(self.i + 1) == "}")
    }
    fn primary(&mut self, before_block: bool) -> Res<NodeId> {
        let start = self.i;
        if self.eat("if") {
            let (test, yes) = self.test_and_block()?;
            let mut children = vec![test, yes];
            if self.eat("else") {
                children.push(if self.word() == "if" {
                    self.nested(|p| p.primary(false))?
                } else {
                    self.block()?
                });
            }
            return Ok(self.node("if", start, None, children));
        }
        if self.eat("match") {
            let subject = self.expr(0, true)?;
            self.expect("{")?;
            let arms = self.list("}", |p| {
                let start = p.i;
                let pattern = p.pattern()?;
                p.expect("=>")?;
                let body = p.block()?;
                Ok(p.node("bras", start, None, vec![pattern, body]))
            })?;
            if arms.is_empty() {
                return Err(self.error("match vide"));
            }
            let mut children = vec![subject];
            children.extend(arms);
            return Ok(self.node("match", start, None, children));
        }
        if self.eat("loop") || self.eat("unsafe") {
            let block = self.block()?;
            return Ok(self.node(
                if self.word_at(start) == "loop" {
                    "loop"
                } else {
                    "unsafe"
                },
                start,
                None,
                vec![block],
            ));
        }
        let moving = self.eat("move");
        if matches!(self.word(), "|" | "||") {
            let mut children = Vec::new();
            if self.eat("|") {
                children.extend(self.list("|", Self::parameter)?);
                if children.is_empty() {
                    return Err(self.error("utiliser || pour une closure sans paramètres"));
                }
            } else {
                self.i += 1;
            }
            if self.eat("->") {
                children.push(self.ty()?);
            }
            children.push(self.block()?);
            return Ok(self.node("closure", start, moving.then_some(start), children));
        }
        if moving {
            let block = self.block()?;
            return Ok(self.node("move bloc", start, Some(start), vec![block]));
        }
        if matches!(self.word(), "{" | "#") {
            return self.block();
        }
        if self.eat("(") {
            let mut children = Vec::new();
            let mut kind = "groupe";
            if self.word() != ")" {
                children.push(self.expr(0, false)?);
                if self.eat(",") {
                    kind = "tuple";
                    children.extend(self.list(")", |p| p.expr(0, false))?);
                    if children.len() < 2 {
                        return Err(self.error("tuple requires at least two elements"));
                    }
                    return Ok(self.node(kind, start, None, children));
                }
            }
            self.expect(")")?;
            return Ok(self.node(kind, start, None, children));
        }
        if self.eat("[") {
            let mut values = Vec::new();
            let mut repeat = false;
            if self.word() != "]" {
                values.push(self.expr(0, false)?);
                repeat = self.eat(";");
                if repeat {
                    values.push(self.integer()?);
                } else {
                    while self.eat(",") && self.word() != "]" {
                        values.push(self.expr(0, false)?);
                    }
                }
            }
            self.expect("]")?;
            return Ok(self.node(
                if repeat {
                    "tableau répété"
                } else {
                    "tableau"
                },
                start,
                None,
                values,
            ));
        }
        if matches!(
            self.tokens[start].kind,
            Kind::Integer | Kind::Float | Kind::Text
        ) || matches!(self.word(), "true" | "false")
        {
            self.i += 1;
            return Ok(self.node("littéral", start, Some(start), vec![]));
        }
        let name = self.path()?;
        if self.word() == "<" {
            let path_end = self.i;
            let checkpoint = self.nodes.len();
            if let Ok(arguments) = self.type_arguments() {
                if path_end == start + 1 && self.word_at(name) == "pool" && self.word() == "(" {
                    let ty = self.node("type", start, Some(name), arguments);
                    self.expect("(")?;
                    let size = self.integer()?;
                    self.expect(")")?;
                    return Ok(self.node("pool", start, Some(name), vec![ty, size]));
                }
                if self.word() == "::"
                    && self.tokens.get(self.i + 1).is_some_and(|token| token.kind == Kind::Name)
                    && self.word_at(self.i + 2) == "("
                {
                    let ty = self.node("type", start, Some(name), arguments);
                    self.expect("::")?;
                    let member = self.name()?;
                    return Ok(self.node("nom qualifié", start, Some(member), vec![ty]));
                }
            }
            // A bare < still belongs to the infix expression parser.
            self.i = path_end;
            self.nodes.truncate(checkpoint);
        }
        let kind = if self.i - start == 1 {
            "nom"
        } else {
            "nom qualifié"
        };
        let base = self.node(kind, start, Some(name), vec![]);
        if self.word() == "{" && self.is_constructor(base, before_block) {
            let fields = self.fields(false)?;
            return Ok(self.node("construction", start, Some(name), fields));
        }
        Ok(base)
    }
    fn pattern(&mut self) -> Res<NodeId> {
        self.nested(|p| {
            let start = p.i;
            if p.eat("(") {
                p.expect(")")?;
                return Ok(p.node("motif unité", start, None, vec![]));
            }
            let name = p.path()?;
            let mut children = Vec::new();
            let kind = if p.eat(".") {
                p.name()?;
                if p.eat("(") {
                    if p.word() == ")" {
                        return Err(p.error("motif positionnel attendu"));
                    }
                    children = p.list(")", |p| {
                        let binding = p.name()?;
                        Ok(p.node("motif nom", binding, Some(binding), vec![]))
                    })?;
                    return Ok(p.node("motif variante positionnelle", start, Some(name), children));
                }
                if p.eat("{") {
                    children = p.list("}", |p| {
                        let start = p.i;
                        let field = p.name()?;
                        p.expect(":")?;
                        let binding = p.name()?;
                        let value = p.node("motif nom", binding, Some(binding), vec![]);
                        Ok(p.node("motif champ", start, Some(field), vec![value]))
                    })?;
                }
                "motif variante"
            } else if p.eat("(") {
                children.push(p.pattern()?);
                p.expect(")")?;
                "motif appel"
            } else {
                "motif nom"
            };
            Ok(p.node(kind, start, Some(name), children))
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn named_types_and_qualified_calls_share_generic_syntax() {
        let source = "
            struct Point { x: i64 }
            fn main() {
                let p: Point = MonType::new();
                let m = HashMap<i64, Point>::new();
                let n: geo::Boite<Option<Point>> = geo::Boite<Option<Point>>::new();
                let comparison = 1 < 2 && 3 > 2;
            }
        ";
        let tree = crate::frontend(source, Mode::Program).unwrap();
        let callees = tree.syntax.nodes.iter().filter_map(|node| {
            (node.kind == "appel").then(|| &tree.syntax.nodes[node.children[0].0])
        }).collect::<Vec<_>>();
        assert_eq!(callees.len(), 3);
        assert!(callees.iter().all(|node| node.kind == "nom qualifié"));
        assert!(callees[0].children.is_empty());
        for callee in &callees[1..] {
            assert_eq!(callee.children.len(), 1);
            assert_eq!(tree.syntax.nodes[callee.children[0].0].kind, "type");
        }

        for source in [
            "fn main() { let x: MonType<> = 0; }",
            "fn main() { let x: MonType<i64,> = 0; }",
            "fn main() { let x = MonType<i64>::new; }",
        ] {
            assert!(crate::frontend(source, Mode::Program).is_err(), "{source}");
        }
    }
}
