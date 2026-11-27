use std::{
    env, fs,
    path::{Path, PathBuf},
};

fn sources(dir: &Path, files: &mut Vec<PathBuf>) {
    for entry in fs::read_dir(dir).expect("read stdlib sources") {
        let entry = entry.expect("read stdlib entry");
        let path = entry.path();
        let kind = entry.file_type().expect("read stdlib entry type");
        if kind.is_dir() {
            sources(&path, files);
        } else if kind.is_file() && path.extension().is_some_and(|ext| ext == "crb") {
            files.push(path);
        }
    }
}

fn main() {
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-env-changed=CORBO_BLOCK_GRAMMAR_AUDIT");
    println!("cargo:rerun-if-env-changed=CORBO_CAST_GRAMMAR_AUDIT");
    #[cfg(feature = "parser-oracle")]
    {
        println!("cargo:rerun-if-changed=tests/oracle");
        // Explicit analysis-only reproducers never select a language policy.
        for (switch, file) in [
            ("CORBO_BLOCK_GRAMMAR_AUDIT", "block_operator.lalrpop"),
            ("CORBO_CAST_GRAMMAR_AUDIT", "cast_comparison.lalrpop"),
        ] {
            if env::var_os(switch).is_some() {
                println!("cargo:rerun-if-changed=../validation/parser_oracle_conflicts");
                lalrpop::Configuration::new()
                    .set_out_dir(env::var("OUT_DIR").unwrap())
                    .process_file(format!("../validation/parser_oracle_conflicts/{file}"))
                    .expect("grammar audit found a conflict; investigate without suppressing it");
            }
        }

        lalrpop::Configuration::new()
            .set_in_dir("tests/oracle")
            .set_out_dir(env::var("OUT_DIR").unwrap())
            .emit_rerun_directives(true)
            .process()
            .expect("independent oracle grammar must generate without unresolved conflicts");
    }

    let root = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").unwrap()).join("../stdlib");
    println!("cargo:rerun-if-changed={}", root.display());
    let mut files = Vec::new();
    sources(&root.join("src"), &mut files);
    files.sort();
    let mut embedded = String::from("&[\n");
    for file in files {
        let name = file
            .strip_prefix(&root)
            .unwrap()
            .iter()
            .map(|part| part.to_str().expect("UTF-8 stdlib path"))
            .collect::<Vec<_>>()
            .join("/");
        embedded.push_str(&format!("    ({name:?}, include_str!({file:?})),\n"));
    }
    embedded.push_str("]\n");
    fs::write(
        PathBuf::from(env::var_os("OUT_DIR").unwrap()).join("stdlib.rs"),
        embedded,
    )
    .expect("write embedded stdlib source list");
}
