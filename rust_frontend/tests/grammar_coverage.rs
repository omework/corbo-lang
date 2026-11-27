//! Actual-EBNF derivations, not a manually maintained list of parser examples.
#[path = "support/ast_integrity.rs"]
mod ast_integrity;
#[path = "support/ebnf.rs"]
mod ebnf;
use corbo_frontend::{lexer, parser};
use ebnf::{Form, Grammar, Recognizer};
use std::path::Path;

#[test]
fn generated_grammar_inventory_and_parser_comparison() {
    let manifest = Path::new(env!("CARGO_MANIFEST_DIR"));
    let source = std::fs::read_to_string(manifest.join("../CORE_GRAMMAR.ebnf")).unwrap();
    let grammar = Grammar::read(&source);
    assert!(
        grammar.undefined().is_empty(),
        "undefined lexical/grammar symbols: {:?}",
        grammar.undefined()
    );
    let costs = grammar.costs();
    let contexts = grammar.contexts();
    let oracle = Recognizer::new(&grammar);
    let mut rows = vec![];
    let mut cases = vec![];
    let mut differences = vec![];
    let mut mutations = vec![];
    for (name, root) in &grammar.rules {
        let Some(context) = contexts.get(name) else {
            rows.push(serde_json::json!({"production":name,"status":"unreachable from programme","offset":grammar.positions[*root]}));
            continue;
        };
        let goals = std::iter::once(None).chain(grammar.goals(*root).into_iter().map(Some));
        let mut count = 0;
        let mut failures = 0;
        for goal in goals {
            let fragments = grammar.program_tokens(name, goal, &costs, context);
            assert!(
                oracle.accepts(&fragments),
                "generator emitted a non-derivation for {name} {goal:?}"
            );
            let generated = Grammar::render(&fragments);
            count += 1;
            let result = lexer::lex(&generated)
                .map_err(|e| format!("lexer: {e:?}"))
                .and_then(|tokens| {
                    let original = tokens.clone();
                    parser::parse(generated.clone(), tokens)
                        .map_err(|e| format!("parser: {e:?}"))
                        .and_then(|unit| {
                            if unit.tokens != original || unit.source != generated {
                                return Err("source/token handoff changed".into());
                            }
                            ast_integrity::audit(&unit)
                                .map_err(|error| format!("AST integrity: {error}"))
                        })
                });
            let failure = result.err();
            if let Some(error) = &failure {
                failures += 1;
                differences.push(format!("{name} {goal:?}: {error}\n{generated}"));
            }
            let feature=goal.map(|(node,variant)|serde_json::json!({"offset":grammar.positions[node],"kind":match grammar.nodes[node]{Form::Alternative(_)=>"alternative",Form::Optional(_)=>"optional",Form::Repeat(_)=>"repeat",_=>unreachable!()},"choice_or_count":variant}));
            cases.push(serde_json::json!({"production":name,"feature":feature,"source":generated,"parser_accepted":failure.is_none(),"failure":failure}));
        }
        // Remove one structural terminal at a time from each minimal witness.
        // The chart oracle decides validity before the production parser runs.
        let baseline = grammar.program_tokens(name, None, &costs, context);
        if !baseline
            .iter()
            .any(|t| matches!(t.as_str(), "@asm" | "@c" | "@c++" | "${"))
        {
            for at in 0..baseline.len() {
                if !matches!(
                    baseline[at].as_str(),
                    ";" | "," | ":" | ")" | "}" | "]" | ">" | "=" | "=>"
                ) {
                    continue;
                }
                let mut changed = baseline.clone();
                let removed = changed.remove(at);
                let expected = oracle.accepts(&changed);
                let mutated = Grammar::render(&changed);
                let actual = lexer::lex(&mutated)
                    .ok()
                    .and_then(|tokens| parser::parse(mutated.clone(), tokens).ok())
                    .is_some();
                if actual != expected {
                    differences.push(format!("mutation of {name}: removed {removed:?}; oracle={expected}, parser={actual}\n{mutated}"));
                }
                mutations.push(serde_json::json!({"production":name,"removed":removed,"source":mutated,"oracle_accepted":expected,"parser_accepted":actual}));
            }
        }
        rows.push(serde_json::json!({"production":name,"status":"generated","offset":grammar.positions[*root],"cases":count,"differences":failures}));
    }
    let output = manifest.join("target/parser-grammar-coverage.json");
    std::fs::write(&output,serde_json::to_vec_pretty(&serde_json::json!({"scope":"bounded actual-EBNF derivations; not full AST/oracle conformance","grammar_fingerprint_fnv64":format!("{:016x}",source.bytes().fold(0xcbf29ce484222325u64,|hash,byte|(hash ^ u64::from(byte)).wrapping_mul(0x100000001b3))),"productions":grammar.rules.len(),"unique_programs":cases.iter().filter_map(|r|r["source"].as_str()).collect::<std::collections::BTreeSet<_>>().len(),"reachable":contexts.len(),"cases":cases.len(),"differences":differences.len(),"inventory":rows,"results":cases,"mutations":mutations,"oracle":"independent chart recognizer over EBNF terminal fragments; lexical and prose constraints are separate"})).unwrap()).unwrap();
    println!(
        "Mutations: {} comparisons, {} oracle-rejected",
        mutations.len(),
        mutations
            .iter()
            .filter(|r| r["oracle_accepted"] == false)
            .count()
    );
    println!(
        "Grammar: {} productions, {} reachable, {} generated cases, {} differences; {}",
        grammar.rules.len(),
        contexts.len(),
        cases.len(),
        differences.len(),
        output.display()
    );
    assert_eq!(
        contexts.len(),
        grammar.rules.len(),
        "unreachable productions must be reviewed; see {}",
        output.display()
    );
    assert!(
        differences.is_empty(),
        "{}\nComplete inventory: {}",
        differences
            .iter()
            .take(12)
            .cloned()
            .collect::<Vec<_>>()
            .join("\n"),
        output.display()
    );
}

#[test]
fn chart_oracle_handles_nullable_left_recursion_and_invalid_neighbors() {
    let grammar = Grammar::read("programme = sequence ; sequence = sequence, \"a\" | [ \"b\" ] ;");
    let oracle = Recognizer::new(&grammar);
    for (tokens, accepted) in [
        (vec![], true),
        (vec!["a"], true),
        (vec!["b"], true),
        (vec!["b", "a", "a"], true),
        (vec!["a", "b"], false),
        (vec!["b", "b"], false),
        (vec!["c"], false),
    ] {
        let input = tokens.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        assert_eq!(oracle.accepts(&input), accepted, "{tokens:?}");
    }
}

#[test]
fn type_contract_or_is_derivable_from_the_written_grammar() {
    let manifest = Path::new(env!("CARGO_MANIFEST_DIR"));
    let source = std::fs::read_to_string(manifest.join("../CORE_GRAMMAR.ebnf")).unwrap();
    let grammar = Grammar::read(&source);
    assert!(grammar.undefined().is_empty());
    let root = grammar.rules["contrat_type"];
    let repeated_or = grammar
        .descendants(root)
        .into_iter()
        .find(|id| {
            if let Form::Repeat(child) = &grammar.nodes[*id] {
                grammar
                    .descendants(*child)
                    .iter()
                    .any(|child| matches!(&grammar.nodes[*child],Form::Terminal(text) if text=="|"))
            } else {
                false
            }
        })
        .expect("contract alternative repetition");
    let costs = grammar.costs();
    let contexts = grammar.contexts();
    let oracle = Recognizer::new(&grammar);
    for extra_branches in [1, 2] {
        let tokens = grammar.program_tokens(
            "contrat_type",
            Some((repeated_or, extra_branches)),
            &costs,
            &contexts["contrat_type"],
        );
        assert_eq!(
            tokens.iter().filter(|t| t.as_str() == "|").count(),
            extra_branches
        );
        assert!(oracle.accepts(&tokens));
        let first_body = tokens.iter().position(|t| t == "{").unwrap();
        let mut with_mode = tokens.clone();
        with_mode.insert(first_body, "with".to_owned());
        assert!(
            oracle.accepts(&with_mode),
            "one with applies to the whole list"
        );
        for valid in [&tokens, &with_mode] {
            let mut repeated = valid.clone();
            let after_or = repeated.iter().position(|t| t == "|").unwrap() + 1;
            repeated.insert(after_or, "with".to_owned());
            assert!(!oracle.accepts(&repeated), "with cannot be placed after OR");
        }
        let mut dangling = tokens.clone();
        let end = dangling.iter().position(|t| t == "|").unwrap() + 1;
        let mut depth = 0;
        let close = dangling
            .iter()
            .enumerate()
            .skip(1)
            .find_map(|(index, token)| {
                match token.as_str() {
                    "(" => depth += 1,
                    ")" => {
                        depth -= 1;
                        if depth == 0 {
                            return Some(index);
                        }
                    }
                    _ => {}
                }
                None
            })
            .expect("annotation closing parenthesis");
        dangling.drain(end..close);
        let mut empty = dangling.clone();
        empty.splice(end..end, ["{".to_owned(), "}".to_owned()]);
        assert!(
            !oracle.accepts(&empty),
            "empty method block is not a contract branch"
        );
        assert!(
            !oracle.accepts(&dangling),
            "empty/dangling OR branch must be rejected"
        );
    }
}
