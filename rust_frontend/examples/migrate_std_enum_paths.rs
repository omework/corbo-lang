//! One-shot source migration, not a compiler stage. Resolves declared enum names
//! and import aliases solely to identify edits; the reference parser stays pure.
use corbo_frontend::{
    ast::*,
    lexer::{self, Kind},
    parser,
};
use std::{
    collections::{BTreeMap, BTreeSet},
    path::{Path, PathBuf},
};

fn gather(path: &Path, files: &mut Vec<PathBuf>) {
    for entry in std::fs::read_dir(path).unwrap() {
        let p = entry.unwrap().path();
        if p.is_dir() {
            gather(&p, files)
        } else if p.extension().is_some_and(|s| s == "crb") {
            files.push(p)
        }
    }
}
fn module(root: &Path, path: &Path) -> String {
    std::iter::once("std".to_owned())
        .chain(
            path.parent()
                .unwrap()
                .strip_prefix(root)
                .unwrap()
                .iter()
                .map(|s| s.to_str().unwrap().to_owned()),
        )
        .collect::<Vec<_>>()
        .join("::")
}
fn text(unit: &ParsedUnit, token: TokenRef) -> String {
    unit.text(token).to_owned()
}
fn main() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
    let stdroot = root.join("stdlib/src");
    let mut files = Vec::new();
    gather(&stdroot, &mut files);
    files.sort();
    let mut units = Vec::new();
    let mut declarations: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    let mut symbols: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    let mut imports = Vec::new();
    for path in files {
        let source = std::fs::read_to_string(&path).unwrap();
        let tokens = lexer::lex(&source).unwrap();
        let unit =
            parser::parse(source, tokens).unwrap_or_else(|e| panic!("{}: {e:?}", path.display()));
        let namespace = module(&stdroot, &path);
        for node in &unit.ast.nodes {
            match &node.kind {
                NodeKind::Enum { name, members, .. } => {
                    let full = format!("{namespace}::{}", text(&unit, *name));
                    let variants = declarations.entry(full.clone()).or_default();
                    for id in members {
                        if let NodeKind::Variant { name, .. } = &unit.ast.nodes[id.0].kind {
                            variants.insert(text(&unit, *name));
                        }
                    }
                    symbols.entry(full.clone()).or_default().insert(full);
                }
                NodeKind::Import {
                    path,
                    entries,
                    alias,
                } => {
                    let prefix = path
                        .iter()
                        .map(|r| text(&unit, *r))
                        .collect::<Vec<_>>()
                        .join("::");
                    if let Some(entries) = entries {
                        for id in entries {
                            let NodeKind::ImportEntry { name, alias } = &unit.ast.nodes[id.0].kind
                            else {
                                unreachable!()
                            };
                            imports.push((
                                format!("{namespace}::{}", text(&unit, alias.unwrap_or(*name))),
                                format!("{prefix}::{}", text(&unit, *name)),
                            ));
                        }
                    } else {
                        imports.push((
                            format!(
                                "{namespace}::{}",
                                alias
                                    .map(|r| text(&unit, r))
                                    .unwrap_or_else(|| text(&unit, *path.last().unwrap()))
                            ),
                            prefix,
                        ));
                    }
                }
                _ => {}
            }
        }
        units.push((path, namespace, unit));
    }
    loop {
        let mut changed = false;
        for (alias, target) in &imports {
            if let Some(known) = symbols.get(target).cloned() {
                let s = symbols.entry(alias.clone()).or_default();
                let size = s.len();
                s.extend(known);
                changed |= size != s.len();
            }
        }
        if !changed {
            break;
        }
    }
    let apply = std::env::args().any(|s| s == "--apply");
    let mut report = String::from(
        "# STD enum separator migration\n\nEdits are based on declared enums and import aliases, not capitalization.\n\n",
    );
    let mut edited = 0;
    let mut edits = 0;
    let mut unresolved = Vec::new();
    let mut pending = Vec::new();
    for (path, namespace, unit) in units {
        let mut shadows = BTreeSet::new();
        for node in &unit.ast.nodes {
            match &node.kind {
                NodeKind::Parameter { name, .. }
                | NodeKind::Pattern(PatternSyntax::Binding { name, .. }) => {
                    shadows.insert(text(&unit, *name));
                }
                _ => {}
            }
        }
        let words: Vec<_> = unit.tokens.iter().map(|t| t.text(&unit.source)).collect();
        let mut replacements = Vec::new();
        for i in 1..unit.tokens.len().saturating_sub(1) {
            if words[i] != "."
                || unit.tokens[i - 1].kind != Kind::Name
                || unit.tokens[i + 1].kind != Kind::Name
            {
                continue;
            }
            let mut first = i - 1;
            while first >= 2
                && words[first - 1] == "::"
                && unit.tokens[first - 2].kind == Kind::Name
            {
                first -= 2
            }
            if first > 0 && words[first - 1] == "." {
                continue;
            }
            let type_path = (first..i)
                .step_by(2)
                .map(|j| words[j])
                .collect::<Vec<_>>()
                .join("::");
            let full = if type_path.starts_with("std::") {
                type_path.clone()
            } else {
                format!("{namespace}::{type_path}")
            };
            let Some(enums) = symbols.get(&full) else {
                continue;
            };
            if !enums.iter().all(|name| {
                declarations
                    .get(name)
                    .is_some_and(|set| set.contains(words[i + 1]))
            }) {
                continue;
            }
            if shadows.contains(words[first]) {
                unresolved.push(format!(
                    "{}:{}: shadowed {}",
                    path.display(),
                    unit.tokens[i].span.start,
                    type_path
                ));
                continue;
            }
            let span = unit.tokens[i].span;
            let line = unit.source[..span.start]
                .bytes()
                .filter(|b| *b == b'\n')
                .count()
                + 1;
            replacements.push(span);
            report.push_str(&format!(
                "- {}:{line}: `{type_path}.{}` → `{type_path}::{}`\n",
                path.strip_prefix(root).unwrap().display(),
                words[i + 1],
                words[i + 1]
            ));
        }
        if !replacements.is_empty() {
            edited += 1;
            edits += replacements.len();
            let mut source = unit.source;
            for span in replacements.into_iter().rev() {
                source.replace_range(span.start..span.end, "::")
            }
            pending.push((path, source));
        }
    }
    assert!(
        unresolved.is_empty(),
        "ambiguous migration candidates require investigation: {unresolved:?}"
    );
    report.push_str(&format!(
        "\n{edits} variant separators across {edited} files. Applied: {apply}.\n"
    ));
    std::fs::write(
        root.join("rust_frontend/target/std-enum-separator-migration.md"),
        report,
    )
    .unwrap();
    if apply {
        for (path, source) in pending {
            std::fs::write(path, source).unwrap();
        }
    }
    println!("{edits} declared-enum separator edits in {edited} STD files; applied={apply}");
}
