//! Direct syntax-stage tests: never call the legacy frontend or its verifier.
use corbo_frontend::{ast::*, lexer, parser};
use std::path::Path;

fn parse(source: &str) -> ParsedUnit {
    let tokens = lexer::lex(source).unwrap();
    parser::parse(source.to_owned(), tokens).unwrap_or_else(|error| panic!("{error:#?}\n{source}"))
}
fn reject(source: &str) {
    let tokens = lexer::lex(source).unwrap();
    assert!(
        parser::parse(source.to_owned(), tokens).is_err(),
        "{source}"
    );
}

#[test]
fn retains_original_source_and_entire_token_stream() {
    let source = "// é\r\nfn main() { let x = \"\\u0061\"; /* not a Corbo comment */ }";
    // A simpler syntax-valid source: trivia and decoded spelling must coexist.
    let source = source.replace(" /* not a Corbo comment */", " // trailing comment\n");
    let tokens = lexer::lex(&source).unwrap();
    let original = tokens.clone();
    let unit = parser::parse(source.clone(), tokens).unwrap();
    assert_eq!(unit.original_source(), source);
    assert_eq!(unit.tokens, original);
    for node in &unit.ast.nodes {
        assert!(node.span.start <= node.span.end && node.span.end <= unit.source.len());
        assert!(node.tokens.start <= node.tokens.end && node.tokens.end <= unit.tokens.len());
    }
    assert_eq!(unit.node_text(unit.ast.root), source);
}

#[test]
fn names_and_types_stay_unresolved() {
    let unit = parse("fn f(x: NotDeclared) Missing { let y: Other = false; ghost.private() }");
    assert!(
        unit.ast
            .nodes
            .iter()
            .any(|n| matches!(&n.kind, NodeKind::Type(TypeSyntax::Path { .. })))
    );
    // Constructor recognition must not depend on declaration order/capitalization.
    parse("fn f() { lower_case { unknown: true } }");
    parse("fn f() { Later { x: 1 } } struct Later { x: i64; }");
}

#[test]
fn operator_grouping_and_assignment_roles_are_explicit() {
    let unit = parse("fn f() { value.field >>= flags & mask == 0; }");
    let (target, op, value) = unit
        .ast
        .nodes
        .iter()
        .find_map(|n| {
            if let NodeKind::Assignment {
                target,
                operator,
                value,
            } = n.kind
            {
                Some((target, operator, value))
            } else {
                None
            }
        })
        .unwrap();
    assert_eq!(unit.text(op), ">>=");
    assert!(matches!(
        unit.ast.nodes[target.0].kind,
        NodeKind::Projection { .. }
    ));
    let NodeKind::Binary { operator, left, .. } = unit.ast.nodes[value.0].kind else {
        panic!("comparison expected")
    };
    assert_eq!(unit.text(operator), "==");
    let NodeKind::Binary { operator, .. } = unit.ast.nodes[left.0].kind else {
        panic!("bitwise operand expected")
    };
    assert_eq!(unit.text(operator), "&");
    reject("fn f() { a < b < c; }");
}

#[test]
fn generic_closers_do_not_rewrite_the_lexer_output() {
    let source = "fn f(v: Box<Box<i64>>) { let x: Box<Box<i64>>=v; }";
    let tokens = lexer::lex(source).unwrap();
    let original = tokens.clone();
    let unit = parser::parse(source.to_owned(), tokens).unwrap();
    assert_eq!(unit.tokens, original);
    assert!(unit.tokens.iter().any(|t| t.text(source) == ">>="));
}

#[test]
fn constructors_headers_closures_and_async_use_the_agreed_syntax() {
    let unit = parse(
        "fn f() { let a = points.new({}); let b = points.try({ x, y: 2 }); let c = points.new(Point { x }); if (point { x }).valid() { yield; } let task = async move { missing.await! }; let map = move |x: i64| i64 { x + 1 }; ((*self).mapper)(2); }",
    );
    assert!(
        unit.ast
            .nodes
            .iter()
            .any(|n| matches!(n.kind, NodeKind::Construct { path: None, .. }))
    );
    assert!(unit.ast.nodes.iter().any(|n| matches!(
        n.kind,
        NodeKind::Async {
            moving: Some(_),
            ..
        }
    )));
    reject("fn f() { if Point { x: 1 }.valid() { } }");
    reject("fn f() { let t = move async { 1 }; }");
    reject("fn f() -> i64 { 1 }");
    reject("fn f() { let x = points.new({ calculate() }); }");
}

#[test]
fn foreign_payloads_are_consumed_without_relexing() {
    let unit = parse(
        "fn f() { @unchecked { @c(includes={\"stdint.h\"}) { *${address} = 1; } @c++ { auto v = 2; } @asm { ret } } }",
    );
    assert_eq!(
        unit.ast
            .nodes
            .iter()
            .filter(|n| matches!(n.kind, NodeKind::Foreign { .. }))
            .count(),
        3
    );
    reject("fn f() { @c { int x = 1; } }");
}

#[test]
fn annotations_and_excluded_branches_are_retained_not_evaluated() {
    let unit = parse(
        "#(datastack: size=4G) #(if: target.os == \"unknown\") use absent::Type; #(endif) #(type: T) #(lock) pub struct Reader<T> { #(configurable) const N: usize = 2; value: T; #(lock: on=self, through_result=true) pub fn read(&self) &T { &self.value } }",
    );
    assert!(
        unit.ast
            .nodes
            .iter()
            .any(|n| matches!(n.kind, NodeKind::Conditional { .. }))
    );
    assert!(
        unit.ast
            .nodes
            .iter()
            .any(|n| matches!(n.kind, NodeKind::Import { .. }))
    );
    assert!(
        unit.ast
            .nodes
            .iter()
            .any(|n| matches!(n.kind, NodeKind::Annotation { .. }))
    );
}

#[test]
fn dispatcher_builds_syntax_without_verifying_its_names() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
    let path = root.parent().unwrap().join("subdb/src/dispatcher.crb");
    if !path.exists() {
        eprintln!("dispatcher not present; external input not exercised");
        return;
    }
    let source = std::fs::read_to_string(&path).unwrap();
    let unit = parse(&source);
    assert_eq!(unit.source, source);
    assert!(
        unit.ast
            .nodes
            .iter()
            .any(|n| matches!(n.kind, NodeKind::For { .. }))
    );
    println!(
        "dispatcher: {} bytes, {} original tokens, {} syntax nodes",
        source.len(),
        unit.tokens.len(),
        unit.ast.nodes.len()
    );
}

fn gather_sources(root: &Path, files: &mut Vec<std::path::PathBuf>) {
    if !root.is_dir() {
        return;
    }
    for entry in std::fs::read_dir(root).unwrap() {
        let path = entry.unwrap().path();
        if path.is_dir() {
            gather_sources(&path, files)
        } else if path.extension().is_some_and(|s| s == "crb") {
            files.push(path)
        }
    }
}

#[test]
fn source_corpus_syntax_inventory() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
    let parent = root.parent().unwrap();
    let mut files = Vec::new();
    for directory in [
        root.join("stdlib"),
        root.join("runtime"),
        root.join("examples"),
        parent.join("corboc/src"),
        parent.join("subdb/src"),
    ] {
        gather_sources(&directory, &mut files)
    }
    files.sort();
    files.dedup();
    let manifest: serde_json::Value = serde_json::from_str(
        &std::fs::read_to_string(root.join("validation/parser_known_syntax_rejections.json"))
            .unwrap(),
    )
    .unwrap();
    let historical = manifest["rejections"].as_array().unwrap();
    let mut results = Vec::new();
    let mut errors = Vec::new();
    let mut rejected = 0;
    let mut nodes = 0;
    for path in &files {
        let source = std::fs::read_to_string(path).unwrap();
        let tokens = lexer::lex(&source).unwrap();
        let reviewed = historical.iter().find(|entry| {
            let base = if entry["root"].as_str() == Some("subdb") {
                root.parent().unwrap().join("subdb")
            } else {
                root.to_path_buf()
            };
            path.strip_prefix(base).ok().and_then(|p| p.to_str()) == entry["input"].as_str()
        });
        match parser::parse(source.clone(), tokens) {
            Ok(unit) => {
                assert_eq!(unit.source, source);
                nodes += unit.ast.nodes.len();
                if reviewed.is_some() {
                    errors.push(format!(
                        "{}: a reviewed syntax rejection now parses; investigate",
                        path.display()
                    ));
                }
                results.push(
                    serde_json::json!({"input":path,"accepted":true,"nodes":unit.ast.nodes.len()}),
                );
            }
            Err(error) => {
                rejected += 1;
                let fingerprint = source.bytes().fold(0xcbf29ce484222325u64, |hash, byte| {
                    (hash ^ u64::from(byte)).wrapping_mul(0x100000001b3)
                });
                let expected = reviewed.is_some_and(|entry| {
                    entry["offset"].as_u64() == Some(error.span.start as u64)
                        && entry["found"].as_str() == Some(error.found.as_str())
                        && entry["source_fnv1a64"].as_str()
                            == Some(format!("{fingerprint:016x}").as_str())
                });
                if !expected {
                    errors.push(format!(
                        "{}:{}: {} (found {:?})",
                        path.display(),
                        error.span.start,
                        error.message,
                        error.found
                    ));
                }
                results.push(serde_json::json!({"input":path,"accepted":false,"reviewed_syntax_rejection":expected,
                    "reason":reviewed.map(|entry|&entry["reason"]),"offset":error.span.start,"message":error.message,
                    "found":error.found,"expected":error.expected}));
            }
        }
    }
    let output = root.join("rust_frontend/target/parser-corpus.json");
    std::fs::write(&output,serde_json::to_vec_pretty(&serde_json::json!({"stage":"syntax only; not external-oracle parity","files":files.len(),"accepted":files.len()-rejected,"rejected":rejected,"unexpected_differences":errors.len(),"nodes":nodes,"results":results})).unwrap()).unwrap();
    println!(
        "Parser corpus: {} accepted / {} files, {} rejected, {nodes} syntax nodes",
        files.len() - rejected,
        files.len(),
        rejected
    );
    assert!(
        errors.is_empty(),
        "{} syntax differences require investigation; full report {}\n{}",
        errors.len(),
        output.display(),
        errors
            .iter()
            .take(15)
            .cloned()
            .collect::<Vec<_>>()
            .join("\n")
    );
}

#[test]
fn five_randomly_selected_std_modules_build_ast() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
    let manifest: serde_json::Value = serde_json::from_str(
        &std::fs::read_to_string(root.join("validation/parser_std_sample.json")).unwrap(),
    )
    .unwrap();
    let mut rows = Vec::new();
    let mut errors = Vec::new();
    let mut files = 0;
    for module in manifest["modules"].as_array().unwrap() {
        for relative in module["files"].as_array().unwrap() {
            let path = root.join("stdlib/src").join(relative.as_str().unwrap());
            let source = std::fs::read_to_string(&path).unwrap();
            let tokens = lexer::lex(&source).unwrap();
            let token_count = tokens.len();
            files += 1;
            match parser::parse(source.clone(), tokens) {
                Ok(unit) => {
                    assert_eq!(unit.source, source);
                    rows.push(serde_json::json!({"module":module["module"],"source":relative,"accepted":true,"tokens":token_count,"nodes":unit.ast.nodes.len()}));
                    println!(
                        "{} / {}: {token_count} tokens, {} AST nodes",
                        module["module"],
                        relative,
                        unit.ast.nodes.len()
                    );
                }
                Err(error) => {
                    errors.push(format!("{}: {error:?}", path.display()));
                    rows.push(serde_json::json!({"module":module["module"],"source":relative,"accepted":false,"offset":error.span.start,"message":error.message}));
                }
            }
        }
    }
    let report = serde_json::json!({"seed":manifest["seed"],"modules":5,"files":files,"failures":errors.len(),"results":rows,"scope":"syntax-only parse; not full LALRPOP parity"});
    std::fs::write(
        root.join("rust_frontend/target/parser-std-sample-results.json"),
        serde_json::to_vec_pretty(&report).unwrap(),
    )
    .unwrap();
    assert!(errors.is_empty(), "{}", errors.join("\n"));
}

#[test]
fn nested_reference_types_and_foreign_headers_are_parsed_once() {
    let source = "fn f(x: &&Thing) { @unchecked { @c(includes={\"a.h\",\"b.h\"}) { } } }";
    let tokens = lexer::lex(source).unwrap();
    let original = tokens.clone();
    let unit = parser::parse(source.to_owned(), tokens).unwrap();
    assert_eq!(unit.tokens, original);
    assert_eq!(
        unit.ast
            .nodes
            .iter()
            .filter(|n| matches!(n.kind, NodeKind::Type(TypeSyntax::Reference { .. })))
            .count(),
        2
    );
    let includes = unit
        .ast
        .nodes
        .iter()
        .find_map(|n| {
            if let NodeKind::Foreign { includes, .. } = &n.kind {
                Some(includes)
            } else {
                None
            }
        })
        .unwrap();
    assert_eq!(
        includes.iter().map(|r| unit.text(*r)).collect::<Vec<_>>(),
        ["\"a.h\"", "\"b.h\""]
    );
}

#[test]
fn enum_separators_do_not_introduce_name_resolution_in_parsing() {
    let unit = parse(
        "enum E { Empty; Data(i64); Named { value: i64; }; } fn f(object: Unknown) { let a = E::Empty; let b = E::Data(1); let c = E::Named { value: 2 }; match a { E::Empty => { () }, _ => { () } } object.field; object.method(); E.Empty; E.Data(1); }",
    );
    // Even with an enum declaration in this file, dotted value expressions
    // remain unresolved projections/calls. Their rejection belongs to resolution.
    assert!(unit.ast.nodes.iter().any(|node| match &node.kind {
        NodeKind::Projection { member, .. } => unit.text(*member) == "Empty",
        _ => false,
    }));
    reject("fn f() { match value { E.Empty => { () } } }");
    reject("fn f() { let e = E.Named { value: 1 }; }");
}

#[test]
fn assignment_targets_allow_calls_only_with_a_place_shape() {
    for target in [
        "*get_target()",
        "items.mut_ref()[index]",
        "get_object().field",
        "(*get_target()).field",
        "(value)",
        "values[calculate_index()]",
        "**get_pointer()",
    ] {
        let source = format!("fn f() {{ {target} = 7; }}");
        let unit = parse(&source);
        assert!(
            unit.ast
                .nodes
                .iter()
                .any(|n| matches!(n.kind, NodeKind::Assignment { .. })),
            "{source}"
        );
    }
    // Invalid types/permissions are deliberately not decided by parsing.
    parse("fn f() { *42 = 7; }");
    for target in [
        "a+b",
        "7",
        "get_target()",
        "&value",
        "value as i64",
        "values[..]",
    ] {
        reject(&format!("fn f() {{ {target} = 7; }}"));
    }
}

#[test]
fn bare_blocks_end_statements_before_following_operators() {
    let unit = parse("fn sample() i64 { { 10 } -2 }");
    let body = unit
        .ast
        .nodes
        .iter()
        .find_map(|n| {
            if let NodeKind::Function { body: Some(id), .. } = n.kind {
                Some(id)
            } else {
                None
            }
        })
        .unwrap();
    let NodeKind::Block {
        statements,
        result: Some(tail),
        ..
    } = &unit.ast.nodes[body.0].kind
    else {
        panic!("body")
    };
    assert_eq!(statements.len(), 1);
    assert!(matches!(
        unit.ast.nodes[tail.0].kind,
        NodeKind::Unary { .. }
    ));
    assert_eq!(unit.node_text(*tail), "-2");
    for source in [
        "fn f() { ({ 10 }) -2 }",
        "fn f() { let value = { 10 } -2; }",
        "fn f() { return { 10 } -2; }",
    ] {
        let unit = parse(source);
        assert!(
            unit.ast
                .nodes
                .iter()
                .any(|n| matches!(n.kind, NodeKind::Binary { .. })),
            "{source}"
        );
    }
    parse("fn f() { { 10 } }");
    parse("fn f() { if flag { 10 } else { 20 } -2 }");
    parse("fn f() { { 10 }; -2 }");
}

#[test]
fn structural_contract_argument_syntax_follows_its_own_production() {
    parse("#(type: T<V: i64, bool> with { fn get() V; }) struct S {}");
    // Normal generic types still allow multiple arguments.
    parse("struct S<A, B> { value: Pair<A, B>; }");
    for contract in [
        "#(type: T<V, X> with { fn get() V; })",
        "#(type: T<V>)",
        "#(type: T with {})",
        "#(type: T*)",
    ] {
        reject(&format!("{contract} struct S {{}}"));
    }
}

#[test]
fn casts_have_numeric_targets_without_consuming_comparisons() {
    for ty in [
        "i32", "i64", "u8", "u16", "u32", "u64", "usize", "f32", "f64",
    ] {
        let source = format!("fn f() {{ x as {ty} < y }}");
        let unit = parse(&source);
        let conversion = unit
            .ast
            .nodes
            .iter()
            .find_map(|n| match n.kind {
                NodeKind::Conversion { ty, .. } => Some(ty),
                _ => None,
            })
            .unwrap();
        assert_eq!(unit.node_text(conversion), ty);
        assert!(
            unit.ast
                .nodes
                .iter()
                .any(|n| matches!(n.kind, NodeKind::Binary { .. }))
        );
    }
    for target in ["T", "T<U>", "bool", "&u64", "[u8; 4]", "num::U64"] {
        let source = format!("fn f() {{ x as {target} }}");
        let tokens = lexer::lex(&source).unwrap();
        let error = parser::parse(source, tokens).unwrap_err();
        assert_eq!(error.class, parser::ErrorClass::Syntax);
        assert_eq!(error.message, "expected a numeric type after as");
    }
}
