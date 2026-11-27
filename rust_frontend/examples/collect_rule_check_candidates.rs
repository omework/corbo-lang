//! Reproduce a small review corpus without asserting that rejection is a defect.
//! Exit success means collection completed, not that these programs were verified.
use corbo_frontend::{parse_source, post_ast::*, rule_check, semantic};
use serde_json::{Value, json};
use std::path::Path;

/// Keep the original source location when diagnostics refer to synthesized units.
fn location(post: &PostAst, mut origin: SourceOriginId) -> Value {
    loop {
        match &post.origins.origins[origin.0 as usize].role {
            OriginRole::Synthesized { cause, .. } => origin = *cause,
            OriginRole::CompilerProvided { description } => {
                return json!({"compiler_provided": description});
            }
            OriginRole::Written { file, span, .. } => {
                let source = &post.origins.files[file.0 as usize].source;
                let start = (span.start as usize).min(source.len());
                let line = source[..start]
                    .bytes()
                    .filter(|byte| *byte == b'\n')
                    .count()
                    + 1;
                return json!({"line": line, "excerpt": source.lines().nth(line - 1).unwrap_or("")});
            }
        }
    }
}

/// Resolve each self-contained fixture once, then hand that PostAST to the checker.
fn inspect(path: &Path) -> Value {
    let source = std::fs::read_to_string(path).expect("read fixture");
    let file = path.file_name().unwrap().to_string_lossy();
    let syntax = match parse_source(source) {
        Ok(syntax) => syntax,
        Err(error) => {
            return json!({"file": file, "status": "syntax_rejected", "diagnostic": format!("{error:?}")});
        }
    };
    let resolved = match semantic::resolve(syntax) {
        Ok(resolved) => resolved,
        Err(errors) => {
            return json!({"file": file, "status": "semantic_rejected", "diagnostics": errors.iter().map(|error| format!("{error:?}")).collect::<Vec<_>>()});
        }
    };
    match rule_check::verify(resolved.logical) {
        RuleAnalysisResult::Established(_) => {
            json!({"file": file, "status": "checker_established", "full_rule_coverage_claimed": false})
        }
        RuleAnalysisResult::Rejected(rejected) => {
            let post = &rejected.semantics.semantics.post_ast;
            let diagnostics = std::iter::once(&rejected.diagnostics.first).chain(&rejected.diagnostics.rest).map(|diagnostic| json!({
                "rule": format!("{:?}", diagnostic.rule),
                "classification": if diagnostic.established_violation {"reported_violation"} else {"unproved"},
                "message": diagnostic.message,
                "location": location(post, diagnostic.primary),
                "related": diagnostic.related.iter().map(|origin| location(post, *origin)).collect::<Vec<_>>()
            })).collect::<Vec<_>>();
            json!({"file": file, "status": "rejected", "diagnostics": diagnostics})
        }
        RuleAnalysisResult::MissingSemanticInput(incomplete) => json!({
            "file": file, "status": "rejected_unproved", "diagnostics": std::iter::once(&incomplete.missing.first).chain(&incomplete.missing.rest).map(|missing| json!({
                "rule": format!("{:?}", missing.consumer), "missing": format!("{:?}", missing.missing), "location": location(&incomplete.semantics.semantics.post_ast, missing.origin)
            })).collect::<Vec<_>>()
        }),
    }
}

fn main() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/rule_check_review");
    let mut files = std::fs::read_dir(root)
        .unwrap()
        .map(|entry| entry.unwrap().path())
        .filter(|path| path.extension().is_some_and(|extension| extension == "crb"))
        .collect::<Vec<_>>();
    files.sort();
    let cases = files.iter().map(|path| inspect(path)).collect::<Vec<_>>();
    println!("{}", serde_json::to_string_pretty(&json!({
        "purpose": "suspected false-rejection review; observed verdicts are not an acceptance oracle",
        "compiler": "Rust staged frontend and PostAST verifier; legacy checker and backend not invoked",
        "host": {"os": std::env::consts::OS, "arch": std::env::consts::ARCH},
        "cases": cases
    })).unwrap());
}
