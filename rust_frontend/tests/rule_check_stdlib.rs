//! Permanent whole-STD rule audit, separate from syntax/semantic-population tests.
use corbo_frontend::{parse_source, post_ast::*, rule_check, semantic};
use std::path::{Path, PathBuf};
fn files(root: &Path, out: &mut Vec<PathBuf>) {
    for entry in std::fs::read_dir(root).unwrap() {
        let entry = entry.unwrap();
        let path = entry.path();
        if entry.file_type().unwrap().is_dir() {
            files(&path, out);
        } else if path.extension().is_some_and(|e| e == "crb") {
            out.push(path);
        }
    }
}
fn location(p: &PostAst, mut id: SourceOriginId) -> serde_json::Value {
    loop {
        match &p.origins.origins[id.0 as usize].role {
            OriginRole::Synthesized { cause, .. } => id = *cause,
            OriginRole::Written { file, span, .. } => {
                let f = &p.origins.files[file.0 as usize];
                let start = (span.start as usize).min(f.source.len());
                let line = f.source[..start].bytes().filter(|b| *b == b'\n').count() + 1;
                return serde_json::json!({"file":f.path,"line":line,"excerpt":f.source.lines().nth(line-1).unwrap_or("")});
            }
            OriginRole::CompilerProvided { description } => {
                return serde_json::json!({"compiler_provided":description});
            }
        }
    }
}
#[test]
fn whole_std_rule_obligations() {
    let manifest = Path::new(env!("CARGO_MANIFEST_DIR"));
    let root = manifest.parent().unwrap().join("stdlib/src");
    let mut paths = vec![];
    files(&root, &mut paths);
    paths.sort();
    let modules = paths
        .iter()
        .map(|path| {
            let relative = path.strip_prefix(&root).unwrap();
            semantic::ParsedModule {
                package: "std".into(),
                path: relative
                    .parent()
                    .unwrap()
                    .components()
                    .map(|p| p.as_os_str().to_string_lossy().into_owned())
                    .collect(),
                file_path: path.display().to_string(),
                syntax: parse_source(std::fs::read_to_string(path).unwrap()).unwrap(),
            }
        })
        .collect();
    let selected = std::env::var("CORBO_RULE_AUDIT_TARGET").ok();
    let resolved = if let Some(name) = &selected {
        let (os, architecture) = name
            .split_once('-')
            .expect("target must be os-architecture");
        assert!(matches!(os, "linux" | "macos" | "windows"));
        assert!(matches!(architecture, "aarch64" | "x86_64"));
        semantic::resolve_package_for_target(
            modules,
            TargetDescription {
                os: os.into(),
                family: if os == "windows" { "windows" } else { "unix" }.into(),
                architecture: architecture.into(),
                pointer_bits: 64,
                endian: Endian::Little,
                abi: AbiId(0),
            },
        )
        .unwrap()
    } else {
        semantic::resolve_package(modules).unwrap()
    };
    let p = &resolved.logical.semantics.post_ast;
    let declared = p
        .obligations
        .n1
        .iter()
        .map(|o| (o.site.id, "N1"))
        .chain(p.obligations.n2.iter().map(|o| (o.site.id, "N2")))
        .chain(p.obligations.n3.iter().map(|o| (o.site.id, "N3")))
        .chain(p.obligations.n4.iter().map(|o| (o.site.id, "N4")))
        .chain(p.obligations.n5.iter().map(|o| (o.site.id, "N5")))
        .chain(p.obligations.n6.iter().map(|o| (o.site.id, "N6")))
        .chain(p.obligations.n7.iter().map(|o| (o.site.id, "N7")))
        .chain(p.obligations.n8.iter().map(|o| (o.site.id, "N8")))
        .collect::<std::collections::HashMap<_, _>>();
    let graph = serde_json::json!({"bodies":p.bodies.len(),"operations":p.bodies.iter().map(|body|body.operations.len()).sum::<usize>(),"entities":p.objects.addresses.len()+p.objects.references.len()+p.objects.collections.len(),"logical_destinations":resolved.logical.finals.len()});
    let started = std::time::Instant::now();
    eprintln!("STD semantic population complete; starting PostAST verification");
    let result = rule_check::verify(resolved.logical);
    let evidence = match &result {
        RuleAnalysisResult::Established(r) => &r.evidence,
        RuleAnalysisResult::Rejected(r) => &r.evidence,
        RuleAnalysisResult::MissingSemanticInput(r) => &r.evidence,
    };
    let (status, diagnostics) = match &result {
        RuleAnalysisResult::Established(_) => ("established", vec![]),
        RuleAnalysisResult::Rejected(r) => {
            let p = &r.semantics.semantics.post_ast;
            ("rejected",std::iter::once(&r.diagnostics.first).chain(&r.diagnostics.rest).map(|d|serde_json::json!({"obligation":d.obligation.0,"rule":format!("{:?}",d.rule),"message":d.message,"established_violation":d.established_violation,"location":location(p,d.primary)})).collect::<Vec<_>>())
        }
        RuleAnalysisResult::MissingSemanticInput(r) => {
            let p = &r.semantics.semantics.post_ast;
            ("missing_semantic_input",std::iter::once(&r.missing.first).chain(&r.missing.rest).map(|d|serde_json::json!({"rule":format!("{:?}",d.consumer),"missing":format!("{:?}",d.missing),"location":location(p,d.origin)})).collect())
        }
    };
    let mut rules = serde_json::Map::new();
    for index in 0..8 {
        let name = format!("N{}", index + 1);
        let declared_ids = declared
            .iter()
            .filter_map(|(id, rule)| (*rule == name).then_some(*id))
            .collect::<std::collections::HashSet<_>>();
        let proved = evidence
            .iter()
            .filter(|proof| declared_ids.contains(&proof.obligation))
            .map(|proof| proof.obligation)
            .collect::<std::collections::HashSet<_>>();
        let related = diagnostics
            .iter()
            .filter(|diagnostic| diagnostic["rule"] == name)
            .collect::<Vec<_>>();
        let rejected = related
            .iter()
            .filter_map(|diagnostic| {
                (diagnostic["established_violation"] == true)
                    .then(|| diagnostic["obligation"].as_u64())
                    .flatten()
                    .map(|id| ObligationId(id as u32))
            })
            .filter(|id| declared_ids.contains(id))
            .collect::<std::collections::HashSet<_>>();
        let unproved = related
            .iter()
            .filter_map(|diagnostic| {
                (diagnostic["established_violation"] != true)
                    .then(|| diagnostic["obligation"].as_u64())
                    .flatten()
                    .map(|id| ObligationId(id as u32))
            })
            .filter(|id| declared_ids.contains(id))
            .collect::<std::collections::HashSet<_>>();
        let accounted = proved
            .union(&rejected)
            .copied()
            .collect::<std::collections::HashSet<_>>()
            .union(&unproved)
            .copied()
            .collect::<std::collections::HashSet<_>>();
        rules.insert(
            name,
            serde_json::json!({
                "declared_source_obligations":declared_ids.len(),
                "proved_source_obligations":proved.len(),
                "rejected_source_obligations":rejected.len(),
                "unproved_source_obligations":unproved.len(),
                "unaccounted_source_obligations":declared_ids.len().saturating_sub(accounted.len()),
                "derived_diagnostics":related.len().saturating_sub(rejected.len()+unproved.len()),
                "absence_of_diagnostics_is_proof":false,
            }),
        );
    }
    let obligations_complete = rules.values().all(|rule| {
        rule["unproved_source_obligations"] == 0
            && rule["unaccounted_source_obligations"] == 0
            && rule["derived_diagnostics"] == 0
    });
    let per_file = paths.iter().map(|path| {
        let related = diagnostics.iter().filter(|diagnostic|diagnostic["location"]["file"].as_str() == Some(path.to_str().unwrap())).collect::<Vec<_>>();
        serde_json::json!({"file":path.strip_prefix(&root).unwrap(),"diagnostics":related.len(),"assessment":if related.is_empty(){"no_diagnostic_is_not_a_proof"}else{"rejected_or_unproved"}})
    }).collect::<Vec<_>>();
    let report = serde_json::json!({
        "files":paths.len(),"target":selected.clone().unwrap_or_else(||format!("{}-{}",std::env::consts::OS,std::env::consts::ARCH)),
        "checker_verdict":status,"diagnostics":diagnostics,"by_rule":rules,"per_file":per_file,"graph":graph,
        "rule_check_seconds":started.elapsed().as_secs_f64(),"code_generation_executed":false,
        "acceptance_policy":"All applicable N1–N8 obligations must be proven; no detected violation is not proof",
        "complete_applicability_inventory_supplied":obligations_complete,
        "full_std_compliance_established":status == "established" && obligations_complete,
        "coverage_gap":if obligations_complete {serde_json::Value::Null}else{serde_json::json!("At least one N1–N8 obligation is unproved, unaccounted, or diagnosed outside the canonical obligation ledger.")},
        "scope":"target-selected whole STD through the current PostAST rule verifier; no native execution"
    });
    let output = manifest.join("target").join(
        selected
            .as_ref()
            .map(|name| format!("rule-check-stdlib-{name}.json"))
            .unwrap_or_else(|| "rule-check-stdlib.json".into()),
    );
    std::fs::write(&output, serde_json::to_vec_pretty(&report).unwrap()).unwrap();
    assert_ne!(
        status,
        "missing_semantic_input",
        "report {}",
        output.display()
    );
    assert!(
        obligations_complete,
        "the canonical N1-N8 ledger is incomplete; report {}",
        output.display()
    );
}
