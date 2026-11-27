#![cfg(feature = "parser-oracle")]
//! Independent generated expression grammar, fed the same original lexer tokens.
use corbo_frontend::{
    ast::*,
    lexer::{self, Kind},
    parser,
};
use std::path::Path;

#[path = "support/ast_integrity.rs"]
mod ast_integrity;

#[derive(Debug, PartialEq, Eq)]
pub struct OracleContract {
    parameter: String,
    inclusive: bool,
    alternatives: Vec<Vec<OracleContractMethod>>,
}
#[derive(Debug, PartialEq, Eq)]
pub struct OracleContractMethod {
    name: String,
    asynchronous: bool,
    mutable_receiver: Option<bool>,
    result: Option<String>,
}

#[derive(Debug, Clone)]
pub enum OracleToken {
    Identifier(String),
    NumericType(String),
    Integer(String),
    Float(String),
    Text(String),
    Boolean(String),
    Symbol(&'static str),
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OracleNode {
    tag: String,
    start: usize,
    end: usize,
    children: Vec<OracleNode>,
}
impl OracleNode {
    pub fn new(tag: &str, start: usize, end: usize, children: Vec<Self>) -> Self {
        Self {
            tag: tag.to_owned(),
            start,
            end,
            children,
        }
    }
}
pub fn leaf(kind: &str, text: String, start: usize, end: usize) -> OracleNode {
    OracleNode::new(&format!("{kind}:{text}"), start, end, vec![])
}
pub fn binary(op: &str, a: OracleNode, b: OracleNode) -> OracleNode {
    OracleNode::new(&format!("binary:{op}"), a.start, b.end, vec![a, b])
}
pub fn unary(op: &str, start: usize, value: OracleNode) -> OracleNode {
    OracleNode::new(&format!("unary:{op}"), start, value.end, vec![value])
}
pub enum Suffix {
    Call(Vec<OracleNode>, usize),
    Field(String, usize),
    Index(OracleNode, usize),
    Unary(&'static str, usize),
}
pub fn postfix(value: OracleNode, suffix: Suffix) -> OracleNode {
    let start = value.start;
    match suffix {
        Suffix::Call(arguments, end) => OracleNode::new(
            "call",
            start,
            end,
            std::iter::once(value).chain(arguments).collect(),
        ),
        Suffix::Field(name, end) => {
            OracleNode::new(&format!("field:{name}"), start, end, vec![value])
        }
        Suffix::Index(index, end) => OracleNode::new("index", start, end, vec![value, index]),
        Suffix::Unary(op, end) => OracleNode::new(op, start, end, vec![value]),
    }
}
mod generated {
    include!(concat!(env!("OUT_DIR"), "/expressions.rs"));
}
mod declaration_generated {
    include!(concat!(env!("OUT_DIR"), "/declaration_order.rs"));
}
mod block_generated {
    include!(concat!(env!("OUT_DIR"), "/blocks.rs"));
}
mod contract_generated {
    include!(concat!(env!("OUT_DIR"), "/contracts.rs"));
}

pub fn block_sequence(
    block: OracleNode,
    semicolon: Option<usize>,
    mut rest: Vec<OracleNode>,
) -> Vec<OracleNode> {
    let tag = if semicolon.is_none() && rest.is_empty() {
        "result"
    } else {
        "statement"
    };
    let wrapper = OracleNode::new(
        tag,
        block.start,
        semicolon.unwrap_or(block.end),
        vec![block],
    );
    rest.insert(0, wrapper);
    rest
}
pub fn value_sequence(
    value: OracleNode,
    after: Option<(usize, Vec<OracleNode>)>,
) -> Vec<OracleNode> {
    match after {
        None => vec![OracleNode::new(
            "result",
            value.start,
            value.end,
            vec![value],
        )],
        Some((end, mut rest)) => {
            rest.insert(
                0,
                OracleNode::new("statement", value.start, end, vec![value]),
            );
            rest
        }
    }
}

fn syntax_tree(unit: &ParsedUnit, id: NodeId) -> Result<OracleNode, String> {
    let node = &unit.ast.nodes[id.0];
    let start = node.span.start;
    let end = node.span.end;
    let recurse = |id| syntax_tree(unit, id);
    let children = |ids: &[NodeId]| {
        ids.iter()
            .map(|id| recurse(*id))
            .collect::<Result<Vec<_>, _>>()
    };
    let (tag, kids) = match &node.kind {
        NodeKind::Path {
            segments,
            arguments,
        } if arguments.is_empty() => (
            format!(
                "path:{}",
                segments
                    .iter()
                    .map(|r| unit.text(*r))
                    .collect::<Vec<_>>()
                    .join("::")
            ),
            vec![],
        ),
        NodeKind::Type(TypeSyntax::Path {
            segments,
            arguments,
        }) => (
            format!(
                "type:{}",
                segments
                    .iter()
                    .map(|r| unit.text(*r))
                    .collect::<Vec<_>>()
                    .join("::")
            ),
            children(arguments)?,
        ),
        NodeKind::Literal { token } => (format!("literal:{}", unit.text(*token)), vec![]),
        NodeKind::Block {
            statements, result, ..
        } => {
            let mut list = children(statements)?;
            if let Some(id) = result {
                let value = recurse(*id)?;
                list.push(OracleNode::new(
                    "result",
                    value.start,
                    value.end,
                    vec![value],
                ));
            }
            ("block".into(), list)
        }
        NodeKind::ExpressionStatement { expression, .. } => {
            ("statement".into(), vec![recurse(*expression)?])
        }

        NodeKind::Parenthesized { expression } => ("paren".into(), vec![recurse(*expression)?]),
        NodeKind::Tuple { elements } => ("tuple".into(), children(elements)?),
        NodeKind::Array { elements, repeat } => {
            let mut list = children(elements)?;
            if let Some(n) = repeat {
                list.push(recurse(*n)?)
            }
            (
                if repeat.is_some() { "repeat" } else { "array" }.into(),
                list,
            )
        }
        NodeKind::Unary {
            operator,
            mutable,
            operand,
        } => (
            format!(
                "unary:{}{}",
                unit.text(*operator),
                if mutable.is_some() { "mut" } else { "" }
            ),
            vec![recurse(*operand)?],
        ),
        NodeKind::Binary {
            operator,
            left,
            right,
        } => (
            format!("binary:{}", unit.text(*operator)),
            vec![recurse(*left)?, recurse(*right)?],
        ),
        NodeKind::Conversion { value, ty, .. } => {
            ("as".into(), vec![recurse(*value)?, recurse(*ty)?])
        }
        NodeKind::Call { callee, arguments } => {
            let mut list = vec![recurse(*callee)?];
            list.extend(children(arguments)?);
            ("call".into(), list)
        }
        NodeKind::Projection { base, member } => (
            format!("field:{}", unit.text(*member)),
            vec![recurse(*base)?],
        ),
        NodeKind::Index { base, index } => {
            ("index".into(), vec![recurse(*base)?, recurse(*index)?])
        }
        NodeKind::Range { start, end, .. } => {
            let mut list = Vec::new();
            if let Some(n) = start {
                list.push(recurse(*n)?)
            }
            if let Some(n) = end {
                list.push(recurse(*n)?)
            }
            ("range".into(), list)
        }
        NodeKind::Await { value, .. } => ("await".into(), vec![recurse(*value)?]),
        NodeKind::Propagate { value, .. } => ("?".into(), vec![recurse(*value)?]),
        NodeKind::Unwrap { value, .. } => ("!".into(), vec![recurse(*value)?]),
        other => return Err(format!("expression oracle does not cover {other:?}")),
    };
    Ok(OracleNode {
        tag,
        start,
        end,
        children: kids,
    })
}
fn oracle_tokens(
    source: &str,
    tokens: &[lexer::Token],
) -> Vec<Result<(usize, OracleToken, usize), &'static str>> {
    tokens
        .iter()
        .filter(|t| t.kind != Kind::Eof)
        .map(|token| {
            let text = token.text(source);
            let value = match token.kind {
                Kind::Name
                    if matches!(
                        text,
                        "as" | "mut" | "await" | "pub" | "fn" | "struct" | "enum" | "type" | "with"
                    ) =>
                {
                    OracleToken::Symbol(match text {
                        "as" => "as",
                        "mut" => "mut",
                        "await" => "await",
                        "pub" => "pub",
                        "fn" => "fn",
                        "struct" => "struct",
                        "enum" => "enum",
                        "with" => "with",
                        _ => "type",
                    })
                }
                Kind::Name if matches!(text, "true" | "false") => {
                    OracleToken::Boolean(text.to_owned())
                }
                Kind::Name => OracleToken::Identifier(text.to_owned()),
                Kind::Integer => OracleToken::Integer(text.to_owned()),
                Kind::Float => OracleToken::Float(text.to_owned()),
                Kind::Text => OracleToken::Text(text.to_owned()),
                Kind::Punct => OracleToken::Symbol(match text {
                    "+" => "+",
                    "-" => "-",
                    "*" => "*",
                    "/" => "/",
                    "%" => "%",
                    "&" => "&",
                    "|" => "|",
                    "^" => "^",
                    "!" => "!",
                    "~" => "~",
                    "||" => "||",
                    "&&" => "&&",
                    "==" => "==",
                    "!=" => "!=",
                    "<" => "<",
                    "<=" => "<=",
                    ">" => ">",
                    ">=" => ">=",
                    "<<" => "<<",
                    ">>" => ">>",
                    "(" => "(",
                    ")" => ")",
                    "[" => "[",
                    "]" => "]",
                    "." => ".",
                    ".." => "..",
                    "::" => "::",
                    "," => ",",
                    ";" => ";",
                    "?" => "?",
                    "#" => "#",
                    ":" => ":",
                    "{" => "{",
                    "}" => "}",
                    _ => return Err("unsupported expression token"),
                }),
                _ => return Err("outside expression-oracle coverage"),
            };
            Ok((token.span.start, value, token.span.end))
        })
        .collect()
}

// Numeric spellings are terminals only in the expression oracle; the base
// token adapter stays generic for independent declaration/contract grammars.
fn expression_oracle_tokens(
    source: &str,
    tokens: &[lexer::Token],
) -> Vec<Result<(usize, OracleToken, usize), &'static str>> {
    oracle_tokens(source, tokens)
        .into_iter()
        .map(|entry| {
            entry.map(|(start, token, end)| {
                let token = match token {
                    OracleToken::Identifier(name)
                        if matches!(
                            name.as_str(),
                            "i32" | "i64" | "u8" | "u16" | "u32" | "u64" | "usize" | "f32" | "f64"
                        ) =>
                    {
                        OracleToken::NumericType(name)
                    }
                    other => other,
                };
                (start, token, end)
            })
        })
        .collect()
}

#[test]
fn independently_generated_expression_trees_match() {
    let mut cases = [
        "flags & mask == 0",
        "1 + 2 * 3",
        "a - b - c",
        "a << b + 1",
        "a | b ^ c & d",
        "a && b || c",
        "-x as i64 + 1",
        "x as u64 < y",
        "x as T < U >> y",
        "x as T<U>",
        "x as bool",
        "x as &u64",
        "x as [u8; 4]",
        "x as num::U64",
        "x as u64 < U >> y",
        "x as u64 > y",
        "x as u64 <= y",
        "x as u64 >= y",
        "x as u64 == y",
        "x as u64 != y",
        "&mut (*guard).field",
        "(*self).mapper(item)",
        "((callback))(1, 2)",
        "items[i + 1].0",
        "source[..count]",
        "source[start..end]",
        "source[start..]",
        "task.await?",
        "result!",
        "!flag",
        "f()",
        "()",
        "(a,b,c,)",
        "[1,2,3]",
        "[x;4]",
        "[]",
        "a::b(c)",
        "a < b < c",
        "(a + b",
        "f(,)",
        "a +",
        "a..b",
    ]
    .map(str::to_owned)
    .to_vec();
    let ops = [
        "+", "-", "*", "/", "%", "<<", ">>", "&", "^", "|", "==", "!=", "<", ">=", "&&", "||",
    ];
    for ty in [
        "i32", "i64", "u8", "u16", "u32", "u64", "usize", "f32", "f64",
    ] {
        cases.push(format!("x as {ty}"));
    }
    for left in ops {
        for right in ops {
            cases.push(format!("a {left} b {right} c"));
        }
    }
    let mut results = Vec::new();
    let mut differences = Vec::new();
    let mut accepted = 0;
    let mut rejected = 0;
    for source in &cases {
        let tokens = lexer::lex(source).unwrap();
        let expected =
            generated::ExpressionParser::new().parse(expression_oracle_tokens(source, &tokens));
        let actual = parser::parse_expression(source.clone(), tokens);
        let result = match (actual, expected) {
            (Ok(unit), Ok(expected)) => match syntax_tree(&unit, unit.ast.root) {
                Ok(actual) if actual == expected => {
                    accepted += 1;
                    Ok(())
                }
                other => Err(format!("actual {other:?}; expected {expected:?}")),
            },
            (Err(_), Err(_)) => {
                rejected += 1;
                Ok(())
            }
            (actual, expected) => Err(format!(
                "acceptance differs: actual {actual:?}; oracle {expected:?}"
            )),
        };
        let detail = result.err();
        if let Some(d) = &detail {
            differences.push(format!("{source}: {d}"));
        }
        results.push(
            serde_json::json!({"source":source,"matched":detail.is_none(),"difference":detail}),
        );
    }
    let output =
        Path::new(env!("CARGO_MANIFEST_DIR")).join("target/parser-lalrpop-expressions.json");
    std::fs::write(&output,serde_json::to_vec_pretty(&serde_json::json!({"coverage":"expression subset only","cases":cases.len(),"accepted":accepted,"rejected":rejected,"differences":differences.len(),"results":results})).unwrap()).unwrap();
    println!(
        "LALRPOP: {} expressions, {accepted} accepted, {rejected} rejected, {} differences",
        cases.len(),
        differences.len()
    );
    assert!(
        differences.is_empty(),
        "{}; full report {}",
        differences.join("\n"),
        output.display()
    );
}

#[test]
fn declaration_annotation_order_matches_the_written_grammar() {
    let cases = [
        (false, "fn f() {}"),
        (false, "pub fn f() {}"),
        (false, "#(type: T) fn f() {}"),
        (false, "#(type: T) pub fn f() {}"),
        (false, "pub #(type: T) fn f() {}"),
        (false, "#(type: T) pub struct S {}"),
        (false, "pub #(type: T) struct S {}"),
        (false, "#(type: T) pub enum E { V; }"),
        (false, "pub #(type: T) enum E { V; }"),
        (true, "#(type: T) pub fn f() {}"),
        (true, "pub #(type: T) fn f() {}"),
    ];
    let mut rows = Vec::new();
    let mut differences = Vec::new();
    for (method, source) in cases {
        let tokens = lexer::lex(source).unwrap();
        let views = oracle_tokens(source, &tokens);
        let oracle = if method {
            declaration_generated::MethodParser::new()
                .parse(views)
                .is_ok()
        } else {
            declaration_generated::DeclarationParser::new()
                .parse(views)
                .is_ok()
        };
        let actual = if method {
            let source = format!("struct S {{ {source} }}");
            let tokens = lexer::lex(&source).unwrap();
            parser::parse(source, tokens).is_ok()
        } else {
            parser::parse(source.to_owned(), tokens).is_ok()
        };
        if oracle != actual {
            differences.push(format!(
                "{} {source}: written grammar={oracle}, Rust parser={actual}",
                if method { "method" } else { "module" }
            ));
        }
        rows.push(serde_json::json!({"source":source,"context":if method{"method"}else{"module"},"oracle_accepted":oracle,"rust_accepted":actual,"matched":oracle==actual}));
    }
    let output =
        Path::new(env!("CARGO_MANIFEST_DIR")).join("target/parser-lalrpop-declaration-order.json");
    std::fs::write(&output,serde_json::to_vec_pretty(&serde_json::json!({"scope":"written declaration/annotation order subset","cases":cases.len(),"differences":differences.len(),"results":rows})).unwrap()).unwrap();
    println!(
        "Declaration grammar: {} cases, {} differences; {}",
        cases.len(),
        differences.len(),
        output.display()
    );
    assert!(
        differences.is_empty(),
        "{}\nA language decision is required; see {}",
        differences.join("\n"),
        output.display()
    );
}

#[test]
fn block_statement_boundaries_match_the_approved_grammar() {
    let cases = [
        "{}",
        "{ {10} -2 }",
        "{ {10}; -2 }",
        "{ ({10}) -2 }",
        "{ {10} }",
        "{ {1} {2} -3 }",
        "{ 10 -2 }",
        "{ -{10} -2 }",
        "{ {10} 2 }",
        "{ 1 2 }",
    ];
    let mut rows = Vec::new();
    let mut differences = Vec::new();
    for source in cases {
        let tokens = lexer::lex(source).unwrap();
        let expected = block_generated::BlockParser::new().parse(oracle_tokens(source, &tokens));
        let actual = parser::parse_expression(source.to_owned(), tokens);
        let error = match (actual, expected) {
            (Ok(unit), Ok(expected)) => match syntax_tree(&unit, unit.ast.root) {
                Ok(actual) if actual == expected => None,
                other => Some(format!(
                    "AST mismatch: actual {other:?}, oracle {expected:?}"
                )),
            },
            (Err(_), Err(_)) => None,
            (actual, expected) => Some(format!("acceptance mismatch: {actual:?} / {expected:?}")),
        };
        if let Some(e) = &error {
            differences.push(format!("{source}: {e}"));
        }
        rows.push(
            serde_json::json!({"source":source,"matched":error.is_none(),"difference":error}),
        );
    }
    let output = Path::new(env!("CARGO_MANIFEST_DIR")).join("target/parser-lalrpop-blocks.json");
    std::fs::write(&output,serde_json::to_vec_pretty(&serde_json::json!({"scope":"block/statement boundary subset","cases":cases.len(),"differences":differences.len(),"results":rows})).unwrap()).unwrap();
    println!(
        "Block oracle: {} cases, {} differences",
        cases.len(),
        differences.len()
    );
    assert!(differences.is_empty(), "{}", differences.join("\n"));
}

fn contract_oracle_tokens(
    source: &str,
    tokens: &[lexer::Token],
) -> Vec<Result<(usize, OracleToken, usize), &'static str>> {
    oracle_tokens(source, tokens)
        .into_iter()
        .map(|entry| {
            entry.map(|(start, token, end)| {
                let token = match token {
                    OracleToken::Identifier(name) if name == "self" => OracleToken::Symbol("self"),
                    OracleToken::Identifier(name) if name == "async" => {
                        OracleToken::Symbol("async")
                    }
                    other => other,
                };
                (start, token, end)
            })
        })
        .collect()
}

#[test]
fn carrier_contract_arguments_match_the_written_grammar() {
    let cases = [
        "#(type: T)",
        "#(type: T<V> with { fn get() V; })",
        "#(type: T<V: i64, X> with { fn get() V; })",
        "#(type: T<V, X> with { fn get() V; })",
        "#(type: T<V>)",
        "#(type: T with {})",
        "#(type: T*)",
    ];
    let mut rows = Vec::new();
    let mut differences = Vec::new();
    for annotation in cases {
        let tokens = lexer::lex(annotation).unwrap();
        let oracle = contract_generated::ContractParser::new()
            .parse(contract_oracle_tokens(annotation, &tokens))
            .is_ok();
        let source = format!("{annotation} struct Reader {{}}");
        let tokens = lexer::lex(&source).unwrap();
        let actual = parser::parse(source, tokens).is_ok();
        if oracle != actual {
            differences.push(format!(
                "{annotation}: written grammar={oracle}, parser={actual}"
            ));
        }
        rows.push(serde_json::json!({"source":annotation,"oracle_accepted":oracle,"rust_accepted":actual,"matched":oracle==actual}));
    }
    let output = Path::new(env!("CARGO_MANIFEST_DIR")).join("target/parser-lalrpop-contracts.json");
    std::fs::write(&output,serde_json::to_vec_pretty(&serde_json::json!({"scope":"written carrier-contract argument subset","cases":cases.len(),"differences":differences.len(),"results":rows})).unwrap()).unwrap();
    println!(
        "Contract oracle: {} cases, {} differences",
        cases.len(),
        differences.len()
    );
    assert!(differences.is_empty(), "{}", differences.join("\n"));
}

mod range_call_generated {
    include!(concat!(env!("OUT_DIR"), "/range_call.rs"));
}

#[test]
fn range_method_arguments_have_independent_ast_evidence() {
    let cases = [
        "a.try_slice(..)",
        "a.try_slice(1..)",
        "a.try_slice(..end)",
        "a.try_slice(start..end)",
        "a.try_slice(1..2..3)",
        "a.try_slice(..,)",
    ];
    let mut rows = vec![];
    for source in cases {
        let tokens = lexer::lex(source).unwrap();
        let oracle = range_call_generated::CallParser::new().parse(oracle_tokens(source, &tokens));
        let actual = parser::parse_expression(source.to_owned(), tokens);
        let matched = match (&actual, &oracle) {
            (Ok(unit), Ok(expected)) => syntax_tree(unit, unit.ast.root).as_ref() == Ok(expected),
            (Err(_), Err(_)) => true,
            _ => false,
        };
        rows.push(serde_json::json!({"source":source,"matched":matched}));
        assert!(matched, "{source}: parser={actual:?}, oracle={oracle:?}");
    }
    let output =
        Path::new(env!("CARGO_MANIFEST_DIR")).join("target/parser-lalrpop-range-call.json");
    std::fs::write(output,serde_json::to_vec_pretty(&serde_json::json!({"scope":"try_slice range calls with simple endpoints","cases":cases.len(),"results":rows})).unwrap()).unwrap();
}

fn contract_type_text(unit: &ParsedUnit, id: NodeId) -> Result<String, String> {
    match &unit.ast.nodes[id.0].kind {
        NodeKind::Type(TypeSyntax::Path {
            segments,
            arguments,
        }) => {
            let mut name = segments
                .iter()
                .map(|t| unit.text(*t))
                .collect::<Vec<_>>()
                .join("::");
            if !arguments.is_empty() {
                let arguments = arguments
                    .iter()
                    .map(|id| contract_type_text(unit, *id))
                    .collect::<Result<Vec<_>, _>>()?;
                name.push_str(&format!("<{}>", arguments.join(",")));
            }
            Ok(name)
        }
        NodeKind::Type(TypeSyntax::Reference {
            mutable, target, ..
        }) => Ok(format!(
            "&{}{}",
            if mutable.is_some() { "mut " } else { "" },
            contract_type_text(unit, *target)?
        )),
        other => Err(format!("contract type oracle does not cover {other:?}")),
    }
}
fn contract_tree(unit: &ParsedUnit) -> Result<OracleContract, String> {
    for node in &unit.ast.nodes {
        let NodeKind::Annotation {
            syntax:
                AnnotationSyntax::TypeContract {
                    parameter,
                    with,
                    alternatives,
                    separators,
                    ..
                },
            ..
        } = &node.kind
        else {
            continue;
        };
        if unit.text(*parameter) != "I" {
            continue;
        }
        if separators.len() != alternatives.len().saturating_sub(1)
            || separators.iter().any(|s| unit.text(*s) != "|")
        {
            return Err("invalid OR separator handoff".into());
        }
        let mut branches = Vec::new();
        for branch in alternatives {
            let NodeKind::TypeContractAlternative {
                methods,
                open,
                close,
            } = &unit.ast.nodes[branch.0].kind
            else {
                return Err("missing contract-alternative node".into());
            };
            if unit.text(*open) != "{" || unit.text(*close) != "}" {
                return Err("branch delimiters not retained".into());
            }
            let mut signatures = Vec::new();
            for method in methods {
                let NodeKind::Function {
                    name,
                    asynchronous,
                    parameters,
                    result,
                    body,
                    ..
                } = &unit.ast.nodes[method.0].kind
                else {
                    return Err("method signature node expected".into());
                };
                if body.is_some() {
                    return Err("a requirement must not have a body".into());
                }
                let receiver = match parameters.as_slice() {
                    [] => None,
                    [id] => match &unit.ast.nodes[id.0].kind {
                        NodeKind::Parameter {
                            name,
                            reference: Some(_),
                            mutable,
                            ty: None,
                        } if unit.text(*name) == "self" => Some(mutable.is_some()),
                        other => return Err(format!("receiver oracle does not cover {other:?}")),
                    },
                    _ => return Err("receiver oracle does not cover ordinary parameters".into()),
                };
                signatures.push(OracleContractMethod {
                    name: unit.text(*name).to_owned(),
                    asynchronous: asynchronous.is_some(),
                    mutable_receiver: receiver,
                    result: result.map(|id| contract_type_text(unit, id)).transpose()?,
                });
            }
            branches.push(signatures);
        }
        return Ok(OracleContract {
            parameter: unit.text(*parameter).to_owned(),
            inclusive: with.is_some(),
            alternatives: branches,
        });
    }
    Err("no I contract annotation".into())
}

#[test]
fn generated_or_contracts_match_the_parser() {
    let mut cases = Vec::new();
    for branches in [1, 2, 3, 5] {
        for with_mode in [true, false] {
            let bodies = (0..branches)
                .map(|index| {
                    let mutable = if index % 2 == 1 { "mut " } else { "" };
                    format!("{{\n    fn next(&mut self) Option<&{mutable}T>;\n    fn reset(&mut self);\n}}")
                })
                .collect::<Vec<_>>()
                .join(" |\n");
            let with = if with_mode { "with " } else { "" };
            cases.push((format!("#(type: I {with}{bodies})"), true));
        }
    }
    let body = "{ fn next(&mut self) Option<&T>; fn reset(&mut self); }";
    let branch = format!("with {body}");
    for details in [
        format!("{branch} |"),
        format!("| {branch}"),
        format!("{branch} | {{}}"),
        format!("{branch} || {body}"),
        format!("{branch} | with {body}"),
        format!("{body} | with {body}"),
        format!("{branch} | I {body}"),
    ] {
        cases.push((format!("#(type: I {details})"), false));
    }
    let mut rows = vec![];
    let mut differences = vec![];
    let case_dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("target/parser-or-contract-cases");
    std::fs::create_dir_all(&case_dir).unwrap();
    for (index, (annotation, valid)) in cases.iter().enumerate() {
        let annotation_tokens = lexer::lex(annotation).unwrap();
        let expected_tree = contract_generated::ContractParser::new()
            .parse(contract_oracle_tokens(annotation, &annotation_tokens));
        let oracle = expected_tree.is_ok();
        assert_eq!(
            oracle, *valid,
            "oracle does not match the approved case: {annotation}"
        );
        let source = format!("#(type: T)\n{annotation}\nfn sample() {{}}\n");
        let case_path = case_dir.join(format!(
            "case-{:02}-{}.crb",
            index + 1,
            if *valid { "valid" } else { "invalid" }
        ));
        std::fs::write(&case_path, &source).unwrap();
        let result = parser::parse(source.clone(), lexer::lex(&source).unwrap());
        let actual = result.is_ok();
        let tree_error = if let (Ok(unit), Ok(expected)) = (&result, &expected_tree) {
            ast_integrity::audit(unit)
                .err()
                .or_else(|| match contract_tree(unit) {
                    Ok(actual) if &actual == expected => None,
                    actual => Some(format!(
                        "contract AST differs: actual={actual:?}, expected={expected:?}"
                    )),
                })
        } else {
            None
        };
        let detail = result
            .err()
            .map(|error| format!("{error:?}"))
            .or(tree_error);
        if actual != oracle || detail.is_some() && actual {
            differences.push(format!(
                "{annotation}: grammar={oracle}, parser={actual}: {detail:?}"
            ));
        }
        rows.push(serde_json::json!({"case_file":case_path,"source":source,"grammar_accepted":oracle,"parser_accepted":actual,"diagnostic":detail,"matched":actual==oracle && (!actual || detail.is_none()),"ast_compared":actual && oracle}));
    }
    let output =
        Path::new(env!("CARGO_MANIFEST_DIR")).join("target/parser-lalrpop-or-contracts.json");
    std::fs::write(&output,serde_json::to_vec_pretty(&serde_json::json!({"scope":"OR contract syntax only; no semantic matching","cases":cases.len(),"differences":differences.len(),"results":rows})).unwrap()).unwrap();
    println!(
        "OR contracts: {} cases, {} differences; {}",
        cases.len(),
        differences.len(),
        output.display()
    );
    assert!(differences.is_empty(), "{}", differences.join("\n"));
}
