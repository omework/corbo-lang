//! Differential tests. Only this adapter knows the production token types.
#[path = "support/logos_oracle.rs"]
mod oracle;

use corbo_frontend::lexer::{self, Kind, Payload};
use oracle::{Data, Token};
use std::path::{Path, PathBuf};

fn normalized(token: &lexer::Token) -> Token {
    Token {
        class: match token.kind {
            Kind::Name => "word",
            Kind::Integer => "integer",
            Kind::Float => "float",
            Kind::Text => "text",
            Kind::Punct => "punct",
            Kind::Assembly => "asm",
            Kind::C => "c",
            Kind::Cpp => "cpp",
            Kind::Eof => "eof",
        },
        range: token.span.start..token.span.end,
        data: match &token.payload {
            Payload::Source => Data::Raw,
            Payload::Text(bytes) => Data::Text(bytes.clone()),
            Payload::Foreign(block) => Data::Island {
                header: block.header.start..block.header.end,
                body: block.body.start..block.body.end,
                operands: block.operands.iter().map(|s| s.start..s.end).collect(),
                header_tokens: block.header_tokens.iter().map(normalized).collect(),
            },
        },
    }
}

/// Compare full accepted streams. For errors compare category and require the
/// production byte offset inside the independently identified failing lexeme.
/// Exact diagnostic offsets are covered by the lexer's handwritten unit tests.
fn compare(source: &str) -> Result<(usize, bool), String> {
    match (lexer::lex(source), oracle::scan(source)) {
        (Ok(actual), Ok(expected)) => {
            let observed: Vec<_> = actual.iter().map(normalized).collect();
            if observed != expected {
                let index = observed
                    .iter()
                    .zip(&expected)
                    .position(|(a, b)| a != b)
                    .unwrap_or(observed.len().min(expected.len()));
                return Err(format!(
                    "token {index}: actual {:?}, oracle {:?}",
                    observed.get(index),
                    expected.get(index)
                ));
            }
            Ok((actual.len(), false))
        }
        (Err(actual), Err(expected)) => {
            let category =
                if actual.message.contains("foreign") || actual.message.contains("C++ raw") {
                    "foreign"
                } else if actual.message.contains("hexadecimal") {
                    "number"
                } else if actual.message.contains("unexpected character") {
                    "character"
                } else {
                    "string"
                };
            if category != expected.category
                || !(expected.range.start..=expected.range.end).contains(&actual.offset)
            {
                return Err(format!(
                    "error mismatch: actual {actual:?}; oracle {expected:?}"
                ));
            }
            Ok((0, true))
        }
        (actual, expected) => Err(format!(
            "acceptance mismatch: actual {actual:?}; oracle {expected:?}"
        )),
    }
}

#[test]
fn oracle_matches_handwritten_expectations() {
    let source = "let value = 1..3;";
    let expected = [
        ("word", 0..3),
        ("word", 4..9),
        ("punct", 10..11),
        ("integer", 12..13),
        ("punct", 13..15),
        ("integer", 15..16),
        ("punct", 16..17),
        ("eof", 17..17),
    ];
    let tokens = oracle::scan(source).unwrap();
    assert_eq!(
        tokens
            .iter()
            .map(|t| (t.class, t.range.clone()))
            .collect::<Vec<_>>(),
        expected
    );
    let source = r#""\u00e9\uD83D\uDE00""#;
    assert_eq!(
        oracle::scan(source).unwrap()[0].data,
        Data::Text("é😀".as_bytes().to_vec())
    );
}

#[test]
fn focused_streams_and_errors_agree() {
    let cases = [
        "",
        "// é\nlet a = 42;",
        "slot.0.1 = .5; return .5; 1..3; 1.;",
        "x >>= 2; y >= 3; a <<= 1; mask &= 4; value ^= 2; bits |= 8;",
        "Vector<Vector<i64>> value; async move { value.await? }",
        r#""é\uD83D\uDE00\n\t\/\"\\\b\f\r""#,
        "@asm { mov x0, ${address}\n // }\n ret }",
        r##"@c(includes={"a.h"}) { if (1) { *${address} = '}'; } /* } */ }"##,
        r##"@c++ { auto x = R"tag(} ${ignored})tag"; *${address} = 1; }"##,
        "@c {} @c++ {} @asm {} @c_name @asm_name",
        "0x",
        "$",
        "\"bad\\q\"",
        "\"\\uDC00\"",
        "\"\\uD800\"",
        "\"bad\n\"",
        "\"unfinished",
        "@asm {",
        "@c { /*",
        "@c { \"",
        "@asm { ${}",
        "@asm { ${bad name} }",
    ];
    for source in cases {
        compare(source).unwrap_or_else(|e| panic!("{source:?}: {e}"));
    }
}

#[test]
fn dispatcher_matches_logos() {
    let project = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
    let path = std::env::var_os("CORBO_LEXER_CASE")
        .map(PathBuf::from)
        .unwrap_or_else(|| project.parent().unwrap().join("subdb/src/dispatcher.crb"));
    if !path.exists() && std::env::var_os("CORBO_LEXER_CASE").is_none() {
        eprintln!("dispatcher comparison skipped: set CORBO_LEXER_CASE to its path");
        return;
    }
    let source = std::fs::read_to_string(&path).expect("read requested lexer input");
    let (count, rejected) = compare(&source).unwrap_or_else(|e| panic!("{}: {e}", path.display()));
    assert!(
        !rejected,
        "dispatcher must be lexically accepted by both lexers"
    );
    let output = project.join("rust_frontend/target/lexer-logos-dispatcher.json");
    let tokens = oracle::scan(&source).unwrap();
    let report = serde_json::json!({
        "input": path, "source_bytes": source.len(), "tokens_including_eof": count,
        "matched": true, "stage": "lexer only", "oracle": "Logos + serde_json",
        "tokens": tokens.iter().map(|t| serde_json::json!({
            "kind":t.class, "start":t.range.start, "end":t.range.end,
            "text":&source[t.range.clone()]
        })).collect::<Vec<_>>()
    });
    std::fs::write(&output, serde_json::to_vec_pretty(&report).unwrap()).unwrap();
    assert_eq!(
        std::fs::read_to_string(&path).unwrap(),
        source,
        "source file changed during comparison"
    );
    println!(
        "{}: {} bytes; {count} tokens including EOF match Logos; report {}",
        path.display(),
        source.len(),
        output.display()
    );
}

fn source_files(root: &Path, files: &mut Vec<PathBuf>) {
    if !root.is_dir() {
        return;
    }
    for entry in std::fs::read_dir(root).unwrap() {
        let path = entry.unwrap().path();
        if path.is_dir() {
            source_files(&path, files);
        } else if path.extension().is_some_and(|extension| extension == "crb") {
            files.push(path);
        }
    }
}

#[test]
fn source_corpus_matches_logos() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
    let siblings = root.parent().unwrap();
    let mut files = Vec::new();
    for directory in [
        root.join("stdlib"),
        root.join("runtime"),
        root.join("examples"),
        siblings.join("corboc/src"),
        siblings.join("subdb/src"),
    ] {
        source_files(&directory, &mut files);
    }
    files.sort();
    files.dedup();
    let mut rows = Vec::new();
    let mut differences = Vec::new();
    let mut accepted = 0;
    let mut rejected = 0;
    let mut token_count = 0;
    let mut bytes = 0;
    for path in &files {
        let source = std::fs::read_to_string(path).unwrap();
        bytes += source.len();
        let result = compare(&source);
        let (matched, tokens, lexical_error, detail) = match result {
            Ok((tokens, error)) => {
                if error {
                    rejected += 1;
                } else {
                    accepted += 1;
                }
                token_count += tokens;
                (true, tokens, error, None)
            }
            Err(detail) => {
                differences.push(format!("{}: {detail}", path.display()));
                (false, 0, false, Some(detail))
            }
        };
        // Lightweight input identity for reproducing a comparison, not a
        // cryptographic integrity claim or part of either lexer.
        let fingerprint = source.bytes().fold(0xcbf29ce484222325u64, |value, byte| {
            (value ^ u64::from(byte)).wrapping_mul(0x100000001b3)
        });
        rows.push(serde_json::json!({"input":path,"source_bytes":source.len(),
            "source_fnv1a64":format!("{fingerprint:016x}"),"matched":matched,
            "tokens_including_eof":tokens,"lexical_error":lexical_error,"difference":detail}));
    }
    let output = root.join("rust_frontend/target/lexer-logos-corpus.json");
    let report = serde_json::json!({"stage":"lexer only","files":files.len(),
        "accepted":accepted,"rejected":rejected,"differences":differences.len(),
        "source_bytes":bytes,"tokens_including_eof":token_count,"results":rows});
    std::fs::write(&output, serde_json::to_vec_pretty(&report).unwrap()).unwrap();
    println!(
        "{} sources: {accepted} accepted, {rejected} rejected, {} differences; {token_count} tokens; report {}",
        files.len(),
        differences.len(),
        output.display()
    );
    assert!(
        differences.is_empty(),
        "{} lexer differences (all recorded in {}):\n{}",
        differences.len(),
        output.display(),
        differences
            .iter()
            .take(10)
            .cloned()
            .collect::<Vec<_>>()
            .join("\n")
    );
}
