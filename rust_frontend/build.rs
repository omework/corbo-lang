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
