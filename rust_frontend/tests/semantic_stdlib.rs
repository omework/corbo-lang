//! Whole-package audit of the NEW staged frontend. Intentionally separate from
//! parser-only coverage and from the legacy verifier/backend integration tests.
//! Run explicitly; a semantic failure is reported as a failure, never a skipped file.
use corbo_frontend::{lexer, parser, post_ast::*, semantic};
use std::path::{Path, PathBuf};

fn discover(root: &Path, files: &mut Vec<PathBuf>) {
    for entry in std::fs::read_dir(root).unwrap() {
        let entry = entry.unwrap();
        let path = entry.path();
        if entry.file_type().unwrap().is_dir() {
            discover(&path, files);
        } else if path.extension().is_some_and(|extension| extension == "crb") {
            files.push(path);
        }
    }
}

#[test]
fn entire_std_through_the_staged_frontend() {
    let targets = [
        ("linux", "unix", "x86_64"),
        ("linux", "unix", "aarch64"),
        ("macos", "unix", "aarch64"),
        ("macos", "unix", "x86_64"),
        ("windows", "windows", "x86_64"),
        ("windows", "windows", "aarch64"),
    ];
    let selected = std::env::var("CORBO_SEMANTIC_AUDIT_TARGET").ok();
    let mut reports = vec![];
    let mut failures = vec![];
    for (os, family, arch) in targets {
        if selected
            .as_ref()
            .is_some_and(|target| target != &format!("{os}-{arch}"))
        {
            continue;
        }
        let target = TargetDescription {
            os: os.into(),
            family: family.into(),
            architecture: arch.into(),
            pointer_bits: 64,
            endian: Endian::Little,
            abi: AbiId(0),
        };
        let report = audit_target(target);
        if report["semantic_resolution"] != "passed" {
            failures.push(format!("{os}-{arch}: {}", report["diagnostics"]));
        }
        reports.push(report);
    }
    assert!(
        !reports.is_empty(),
        "unknown requested semantic audit target"
    );
    let output = Path::new(env!("CARGO_MANIFEST_DIR")).join("target/semantic-stdlib-matrix.json");
    std::fs::write(&output,serde_json::to_vec_pretty(&serde_json::json!({"targets":reports,"failures":failures.len(),"rule_checker_executed":false,"code_generation_executed":false})).unwrap()).unwrap();
    assert!(failures.is_empty(), "{}", failures.join("\n"));
}

fn audit_target(target: TargetDescription) -> serde_json::Value {
    let manifest = Path::new(env!("CARGO_MANIFEST_DIR"));
    let root = manifest.parent().unwrap().join("stdlib/src");
    let mut paths = vec![];
    discover(&root, &mut paths);
    paths.sort();
    assert!(!paths.is_empty());
    let mut modules = vec![];
    let mut rows = vec![];
    let mut failed_syntax = 0;
    for path in &paths {
        let relative = path.strip_prefix(&root).unwrap();
        let source = std::fs::read_to_string(path).unwrap();
        let tokens = match lexer::lex(&source) {
            Ok(tokens) => tokens,
            Err(error) => {
                rows.push(serde_json::json!({"file":relative,"lexer":"failed","diagnostic":format!("{error:?}")}));
                failed_syntax += 1;
                continue;
            }
        };
        let token_count = tokens.len();
        let original_tokens = tokens.clone();
        let original_source = source.clone();
        match parser::parse(source, tokens) {
            Ok(syntax) => {
                assert_eq!(syntax.source, original_source);
                assert_eq!(syntax.tokens, original_tokens);
                rows.push(serde_json::json!({"file":relative,"lexer":"passed","parser":"passed","tokens":token_count,"nodes":syntax.ast.nodes.len()}));
                modules.push(semantic::ParsedModule {
                    package: "std".into(),
                    path: relative
                        .parent()
                        .unwrap()
                        .components()
                        .map(|part| part.as_os_str().to_string_lossy().into_owned())
                        .collect(),
                    file_path: path.display().to_string(),
                    syntax,
                });
            }
            Err(error) => {
                rows.push(serde_json::json!({"file":relative,"lexer":"passed","parser":"failed","diagnostic":format!("{error:?}")}));
                failed_syntax += 1;
            }
        }
    }
    // Keep file IDs aligned with the package input; never resolve files alone
    // with absent imports or flatten/reparse their preserved syntax.
    let locations: Vec<_> = modules
        .iter()
        .map(|module| (module.file_path.clone(), module.syntax.source.clone()))
        .collect();
    let (semantic_status, diagnostics, counts) = if failed_syntax == 0 {
        match semantic::resolve_package_for_target(modules, target.clone()) {
            Ok(resolved) => {
                semantic::validate_population(&resolved.logical).unwrap();
                let post = &resolved.logical.semantics.post_ast;
                for definition in &post.declarations.functions {
                    if !definition.type_parameters.is_empty()
                        && matches!(definition.body, FunctionImplementation::Template { .. })
                    {
                        let id = definition
                            .parametric_body
                            .expect("generic definition needs a canonical symbolic body");
                        let instance = &post.declarations.instances[id.0 as usize];
                        assert_eq!(instance.definition, definition.id);
                        assert!(instance.body.is_some());
                        assert!(matches!(
                            instance.resolution,
                            InstanceResolution::Parametric { .. }
                        ));
                    }
                }

                (
                    "passed",
                    vec![],
                    serde_json::json!({"bodies":post.bodies.len(),"types":post.types.entries.len(),"values":post.values.entries.len(),"execution_moments":post.execution.execution_moments.len(),"function_definitions":post.declarations.functions.len(),"function_instances":post.declarations.instances.len(),"symbolically_resolved_definitions":post.declarations.functions.iter().filter(|f|f.parametric_body.is_some()).count(),"generic_templates":post.declarations.functions.iter().filter(|f|!f.type_parameters.is_empty()).count()}),
                )
            }
            Err(errors) => {
                let diagnostics=errors.iter().map(|error|{
                    let (file,source)=&locations[error.file.0 as usize];
                    let start=error.span.start.min(source.len());
                    let line=source[..start].bytes().filter(|byte|*byte==b'\n').count()+1;
                    let column=start-source[..start].rfind('\n').map_or(0,|position|position+1)+1;
                    let excerpt=source.lines().nth(line-1).unwrap_or("");
                    serde_json::json!({"file":file,"line":line,"column":column,"kind":format!("{:?}",error.kind),"message":error.message,"excerpt":excerpt})
                }).collect::<Vec<_>>();
                ("failed", diagnostics, serde_json::Value::Null)
            }
        }
    } else {
        ("blocked_by_syntax", vec![], serde_json::Value::Null)
    };
    let output = manifest.join(format!(
        "target/semantic-stdlib-{}-{}.json",
        target.os, target.architecture
    ));
    let report = serde_json::json!({
        "scope":"entire STD as one parsed package through lexer, parser, semantic resolution and structural PostAST integrity",
        "target":{"os":target.os,"arch":target.architecture},
        "files":paths.len(),"syntax_failures":failed_syntax,"semantic_resolution":semantic_status,
        "diagnostics":diagnostics,"counts":counts,"sources":rows,
        "rule_checker_executed":false,"physical_planner_executed":false,"code_generation_executed":false,
        "coverage_note":"Resolution is fail-fast. Every generic source body is resolved with its real symbolic parameters; concrete specializations are not enumerated."
    });
    std::fs::write(&output, serde_json::to_vec_pretty(&report).unwrap()).unwrap();
    println!(
        "STD: {} files; {failed_syntax} syntax failures; semantic resolution {semantic_status}; report {}",
        paths.len(),
        output.display()
    );
    if target.os == std::env::consts::OS && target.architecture == std::env::consts::ARCH {
        std::fs::write(
            manifest.join("target/semantic-stdlib.json"),
            serde_json::to_vec_pretty(&report).unwrap(),
        )
        .unwrap();
    }
    report
}

/// Independently inventory the requested field/method collisions across all
/// source types, including platform-specific files not selected on this host.
#[test]
fn std_has_no_direct_field_method_name_collisions() {
    use corbo_frontend::ast::NodeKind;
    use std::collections::BTreeSet;
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .join("stdlib/src");
    let mut paths = vec![];
    discover(&root, &mut paths);
    paths.sort();
    let mut collisions = vec![];
    for path in paths {
        let unit = corbo_frontend::parse_source(std::fs::read_to_string(&path).unwrap()).unwrap();
        for node in &unit.ast.nodes {
            let (name, members) = match &node.kind {
                NodeKind::Struct { name, members, .. } | NodeKind::Enum { name, members, .. } => {
                    (name, members)
                }
                _ => continue,
            };
            let fields: BTreeSet<_> = members
                .iter()
                .filter_map(|id| match &unit.ast.nodes[id.0].kind {
                    NodeKind::Field { name, .. } => Some(unit.text(*name)),
                    _ => None,
                })
                .collect();
            for member in members {
                if let NodeKind::Function { name: method, .. } = &unit.ast.nodes[member.0].kind {
                    if fields.contains(unit.text(*method)) {
                        collisions.push(format!(
                            "{}: {}.{}",
                            path.display(),
                            unit.text(*name),
                            unit.text(*method)
                        ));
                    }
                }
            }
        }
    }
    assert!(collisions.is_empty(), "{}", collisions.join("\n"));
}
