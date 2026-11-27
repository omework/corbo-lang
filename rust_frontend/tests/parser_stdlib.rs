//! Permanent, exhaustive STD discovery: every .crb file must parse, including
//! cfg-excluded branches. No package loader, target selection or verifier.
#[path = "support/ast_integrity.rs"]
mod ast_integrity;
use ast_integrity::audit;
use corbo_frontend::{lexer, parser};
use std::{
    collections::BTreeMap,
    path::{Path, PathBuf},
};

fn sources(root: &Path, files: &mut Vec<PathBuf>) -> std::io::Result<()> {
    for entry in std::fs::read_dir(root)? {
        let entry = entry?;
        let path = entry.path();
        let ty = entry.file_type()?;
        if ty.is_dir() {
            sources(&path, files)?
        } else if ty.is_file() && path.extension().is_some_and(|s| s == "crb") {
            files.push(path)
        }
    }
    Ok(())
}

#[test]
fn entire_standard_library_parses_and_preserves_its_syntax() {
    let manifest = Path::new(env!("CARGO_MANIFEST_DIR"));
    let root = manifest.parent().unwrap().join("stdlib/src");
    let mut files = Vec::new();
    sources(&root, &mut files).unwrap();
    files.sort();
    assert!(
        !files.is_empty(),
        "STD discovery must not silently skip its input"
    );
    let mut rows = Vec::new();
    let mut failures = Vec::new();
    let mut nodes = 0;
    let mut tokens = 0;
    let mut shapes = BTreeMap::<String, usize>::new();
    for path in &files {
        let source = match std::fs::read_to_string(path) {
            Ok(source) => source,
            Err(error) => {
                let error = format!("source read: {error}");
                failures.push(format!("{}: {error}", path.display()));
                rows.push(serde_json::json!({"source":path.strip_prefix(&root).unwrap(),"passed":false,"stage":"input","failure":error}));
                continue;
            }
        };
        let original = source.clone();
        let input = match lexer::lex(&source) {
            Ok(tokens) => tokens,
            Err(error) => {
                let error = format!("lexing: {error:?}");
                failures.push(format!("{}: {error}", path.display()));
                rows.push(serde_json::json!({"source":path.strip_prefix(&root).unwrap(),"passed":false,"stage":"lexer","failure":error}));
                continue;
            }
        };
        let original_tokens = input.clone();
        let result = parser::parse(source, input);
        let (count, mut error) = match result {
            Ok(unit) => {
                let result = if unit.source != original || unit.tokens != original_tokens {
                    Err("original source/token stream changed".into())
                } else {
                    audit(&unit)
                };
                nodes += unit.ast.nodes.len();
                tokens += unit.tokens.len();
                for node in &unit.ast.nodes {
                    let shape = format!("{:?}", std::mem::discriminant(&node.kind));
                    *shapes.entry(shape).or_default() += 1;
                }
                (unit.ast.nodes.len(), result.err())
            }
            Err(e) => {
                let line = original[..e.span.start.min(original.len())]
                    .bytes()
                    .filter(|b| *b == b'\n')
                    .count()
                    + 1;
                (0, Some(format!("{line}: {e:?}")))
            }
        };
        if std::fs::read_to_string(path).ok().as_deref() != Some(original.as_str()) {
            error = Some(format!(
                "{}; source changed during audit",
                error.unwrap_or_default()
            ));
        }
        if let Some(error) = &error {
            failures.push(format!("{}: {error}", path.display()))
        }
        rows.push(serde_json::json!({"source":path.strip_prefix(&root).unwrap(),"source_bytes":original.len(),"tokens":original_tokens.len(),"nodes":count,"passed":error.is_none(),"failure":error}));
    }
    let output = manifest.join("target/parser-stdlib.json");
    std::fs::write(&output,serde_json::to_vec_pretty(&serde_json::json!({"scope":"entire STD syntax and AST integrity; no semantic stages","files":files.len(),"failures":failures.len(),"nodes":nodes,"tokens":tokens,"node_shapes":shapes,"results":rows})).unwrap()).unwrap();
    println!(
        "Entire STD: {} files, {} failures, {tokens} original tokens, {nodes} AST nodes; report {}",
        files.len(),
        failures.len(),
        output.display()
    );
    assert!(
        failures.is_empty(),
        "All failures are recorded in {}:\n{}",
        output.display(),
        failures.join("\n")
    );
}
