use crate::{
    lexer::Kind,
    parser::Mode,
    target::{self, Target as BuildTarget},
    tree::{Fact, StaticTree},
};
use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    path::{Path, PathBuf},
    process::Command,
};

type Module = Vec<String>;
type Result<T> = std::result::Result<T, String>;
pub(crate) const TLS_CONNECTION: &str = "__crust_package_tls_connection";
pub(crate) const ITER_ADAPTER: &str = "__crust_package_iter";

struct File {
    path: PathBuf,
    module: Module,
    source: String,
    tree: StaticTree,
}

struct Item {
    internal: String,
    public: bool,
    nominal: bool,
    path: PathBuf,
}

#[derive(Clone, Copy)]
enum Target<'a> {
    Item(&'a Item),
    Module(&'a Module),
}

fn identifier(name: &str) -> bool {
    let mut bytes = name.bytes();
    bytes
        .next()
        .is_some_and(|b| b.is_ascii_alphabetic() || b == b'_')
        && bytes.all(|b| b.is_ascii_alphanumeric() || b == b'_')
        && name != "_"
}

fn files_in(
    dir: &Path,
    module: &Module,
    files: &mut Vec<File>,
    target: &BuildTarget,
) -> Result<()> {
    let entries = fs::read_dir(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
    let mut entries = entries
        .collect::<std::io::Result<Vec<_>>>()
        .map_err(|e| format!("{}: {e}", dir.display()))?;
    entries.sort_by_key(|entry| entry.file_name());
    for entry in entries {
        let path = entry.path();
        let kind = entry
            .file_type()
            .map_err(|e| format!("{}: {e}", path.display()))?;
        if kind.is_dir() {
            let name = entry.file_name().to_string_lossy().into_owned();
            if !identifier(&name) {
                return Err(format!("invalid module directory: {}", path.display()));
            }
            let mut child = module.clone();
            child.push(name);
            files_in(&path, &child, files, target)?;
        } else if kind.is_file() && path.extension().is_some_and(|ext| ext == "crb") {
            let source =
                fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?;
            files.push(parse_file(path, module.clone(), source, target)?);
        }
    }
    Ok(())
}

fn parse_file(path: PathBuf, module: Module, source: String, target: &BuildTarget) -> Result<File> {
    let diagnose =
        |e: crate::Error| format!("{}: byte {}: {}", path.display(), e.offset, e.message);
    let tokens = target::select(
        &source,
        crate::lexer::lex(&source).map_err(diagnose)?,
        target,
    )
    .map_err(diagnose)?;
    let syntax = crate::parser::parse_with_names(&source, &tokens, Mode::Program, &[], true)
        .map_err(diagnose)?;
    let tree = StaticTree::from_syntax(&source, tokens, syntax);
    Ok(File {
        path,
        module,
        source,
        tree,
    })
}

impl File {
    fn word(&self, token: usize) -> &str {
        let span = self.tree.tokens[token].span;
        &self.source[span.start..span.end]
    }

    fn error(&self, token: usize, message: impl std::fmt::Display) -> String {
        format!(
            "{}: byte {}: {message}",
            self.path.display(),
            self.tree.tokens[token].span.start
        )
    }
}

struct Symbols {
    items: BTreeMap<Module, Item>,
    modules: BTreeSet<Module>,
}

impl Symbols {
    fn resolve(&self, path: &[String], from: &[String]) -> Result<Target<'_>> {
        if path.starts_with(&["std".to_owned(), "sys".to_owned()]) && from[0] != "std" {
            return Err(format!("private platform component {}", path.join("::")));
        }
        if path.iter().map(String::as_str).eq(["std", "net", "tcp", "__din_package_socket"])
            && !from.iter().map(String::as_str).eq(["std", "net", "tls", "openssl"])
        {
            return Err(format!("private platform component {}", path.join("::")));
        }
        match (self.items.get(path), self.modules.get(path)) {
            (Some(_), Some(_)) => Err(format!(
                "ambiguous path {}: names both a module and a component",
                path.join("::")
            )),
            (Some(item), None) if item.public || path[..path.len() - 1] == *from => {
                Ok(Target::Item(item))
            }
            (Some(_), None) => Err(format!("private component {}", path.join("::"))),
            (None, Some(module)) => Ok(Target::Module(module)),
            (None, None) => Err(format!("unknown import or component {}", path.join("::"))),
        }
    }
}

type Imports<'a> = BTreeMap<String, (Target<'a>, String)>;

fn path_tokens(file: &File, start: usize, end: usize) -> (Module, usize) {
    let mut path = vec![file.word(start).to_owned()];
    let mut next = start + 1;
    while next + 1 < end && file.word(next) == "::" && file.tree.tokens[next + 1].kind == Kind::Name
    {
        path.push(file.word(next + 1).to_owned());
        next += 2;
    }
    (path, next)
}

fn imports<'a>(
    file: &File,
    visible: &BTreeSet<String>,
    symbols: &'a Symbols,
) -> Result<Imports<'a>> {
    let mut imports = BTreeMap::new();
    for &id in &file.tree.syntax.nodes[file.tree.syntax.root.0].children {
        let node = &file.tree.syntax.nodes[id.0];
        if node.kind != "use" {
            continue;
        }
        let (prefix, _) = path_tokens(file, node.start + 1, node.end);
        if !visible.contains(&prefix[0]) {
            return Err(file.error(
                node.start,
                format!(
                    "package {} is not declared as a direct dependency",
                    prefix[0]
                ),
            ));
        }
        let mut add = |path: Module, alias: Option<&str>| -> Result<()> {
            let name = alias.unwrap_or(path.last().unwrap()).to_owned();
            let full_path = path.join("::");
            let target = symbols
                .resolve(&path, &file.module)
                .map_err(|e| file.error(node.start, e))?;
            let mut local = file.module.clone();
            local.push(name.clone());
            if symbols.items.contains_key(&local)
                || matches!(name.as_str(), "print" | "copy" | "drop")
            {
                return Err(file.error(
                    node.start,
                    format!("import {full_path} conflicts with local declaration {name}"),
                ));
            }
            if let Some((_, previous)) = imports.insert(name.clone(), (target, full_path.clone())) {
                return Err(file.error(
                    node.start,
                    format!("import collision for {name}: {previous} and {full_path}"),
                ));
            }
            Ok(())
        };
        if node
            .children
            .first()
            .is_some_and(|id| file.tree.syntax.nodes[id.0].kind == "import member")
        {
            for member in node.children.iter().map(|id| &file.tree.syntax.nodes[id.0]) {
                let mut path = prefix.clone();
                path.push(file.word(member.name.unwrap()).to_owned());
                let alias = member
                    .children
                    .first()
                    .map(|id| file.word(file.tree.syntax.nodes[id.0].name.unwrap()));
                add(path, alias)?;
            }
        } else {
            let alias = node
                .children
                .first()
                .map(|id| file.word(file.tree.syntax.nodes[id.0].name.unwrap()));
            add(prefix, alias)?;
        }
    }
    Ok(imports)
}

fn lower(
    file: &File,
    visible: &BTreeSet<String>,
    symbols: &Symbols,
    output: &mut String,
) -> Result<()> {
    let imports = imports(file, visible, symbols)?;
    let mut names = imports
        .iter()
        .filter_map(|(name, (target, _))| {
            matches!(target, Target::Item(item) if item.nominal).then_some(name.clone())
        })
        .collect::<Vec<_>>();
    names.extend(symbols.items.iter().filter_map(|(path, item)| {
        (item.nominal && (item.public || path[..path.len() - 1] == file.module))
            .then(|| path.last().unwrap().clone())
    }));
    let syntax = crate::parser::parse_with_names(
        &file.source,
        &file.tree.tokens,
        Mode::Program,
        &names,
        false,
    )
    .map_err(|e| format!("{}: byte {}: {}", file.path.display(), e.offset, e.message))?;
    let resolved_tree = StaticTree::from_syntax(&file.source, file.tree.tokens.clone(), syntax);
    let syntax = &resolved_tree.syntax;
    let mut edits = BTreeMap::new();
    let span = |token: usize| file.tree.tokens[token].span;
    for &id in &syntax.nodes[syntax.root.0].children {
        let node = &syntax.nodes[id.0];
        if node.kind == "use" {
            edits.insert(span(node.start).start, (span(node.end - 1).end, ""));
        } else if matches!(node.kind, "fn" | "async fn" | "extern" | "struct" | "enum" | "const") {
            let token = node.name.unwrap();
            let mut path = file.module.clone();
            path.push(file.word(token).to_owned());
            let internal = &symbols.items[&path].internal;
            edits.insert(span(token).start, (span(token).end, internal.as_str()));
            if node.public {
                if let Some(public) = (node.start..token).find(|&token| file.word(token) == "pub") {
                    edits.insert(span(public).start, (span(public).end, ""));
                }
            }
        }
    }
    let locals = resolved_tree
        .points
        .iter()
        .filter_map(|point| {
            matches!(point.fact, Fact::Use { binding: Some(_) }).then_some(point.syntax)
        })
        .collect::<std::collections::HashSet<_>>();
    for (index, node) in syntax.nodes.iter().enumerate() {
        if !matches!(
            node.kind,
            "nom" | "nom qualifié" | "type" | "construction" | "motif variante" | "motif variante positionnelle" | "impl"
        ) || file.tree.tokens[node.start].kind != Kind::Name
            || locals.contains(&crate::parser::NodeId(index))
        {
            continue;
        }
        let path_start = if node.kind == "impl" { node.start + 1 } else { node.start };
        let (mut path, mut end) = path_tokens(file, path_start, node.end);
        // Resolve the type prefix of Type::associated before checking the
        // method signature in the flattened program.
        if node.kind == "nom qualifié" && node.children.is_empty() && path.len() >= 2 {
            let mut prefix = path[..path.len() - 1].to_vec();
            if prefix.len() == 1 {
                if let Some((Target::Item(item), _)) = imports.get(&prefix[0]) {
                    if item.nominal {
                        path.pop();
                        end -= 2;
                    }
                } else {
                    let mut local = file.module.clone();
                    local.append(&mut prefix);
                    if symbols.items.get(&local).is_some_and(|item| item.nominal) {
                        path.pop();
                        end -= 2;
                    }
                }
            } else {
                let qualified = match imports.get(&prefix[0]) {
                    Some((Target::Module(module), _)) => {
                        let mut qualified = (*module).clone();
                        qualified.extend_from_slice(&prefix[1..]);
                        qualified
                    }
                    _ => prefix,
                };
                if symbols.items.get(&qualified).is_some_and(|item| item.nominal) {
                    path.pop();
                    end -= 2;
                }
            }
        }
        if edits
            .range(..=span(path_start).start)
            .next_back()
            .is_some_and(|(_, (end, _))| *end > span(path_start).start)
        {
            continue;
        }
        let target = if path.len() == 1 {
            match imports.get(&path[0]) {
                Some((Target::Item(item), _)) => Some(*item),
                Some((Target::Module(_), _)) => {
                    return Err(file.error(node.start, "module requires a component"));
                }
                None => {
                    let mut local = file.module.clone();
                    local.extend(path);
                    symbols.items.get(&local)
                }
            }
        } else {
            let qualified = if let Some((Target::Module(module), _)) = imports.get(&path[0]) {
                let mut qualified = (*module).clone();
                qualified.extend_from_slice(&path[1..]);
                Some(qualified)
            } else if visible.contains(&path[0]) {
                Some(path)
            } else if path[0] == "runtime"
                || matches!(
                    path[0].as_str(),
                    "bool"
                        | "i32"
                        | "i64"
                        | "u8"
                        | "u16"
                        | "u32"
                        | "u64"
                        | "usize"
                        | "f32"
                        | "f64"
                        | "str"
                        | "char"
                        | "NumericConversionError"
                        | "Mutex"
                        | "AsyncMutex"
                        | "String"
                        | "HashMap"
                        | "Vector"
                        | "Option"
                        | "Result"
                        | "A"
                        | "Pool"
                        | "Iter"
                )
            {
                None
            } else {
                return Err(file.error(node.start, format!("unknown qualifier {}", path[0])));
            };
            match qualified {
                Some(path) => match symbols
                    .resolve(&path, &file.module)
                    .map_err(|e| file.error(node.start, e))?
                {
                    Target::Item(item) => Some(item),
                    Target::Module(_) => {
                        return Err(file.error(node.start, "module requires a component"));
                    }
                },
                None => None,
            }
        };
        if let Some(item) = target {
            edits.insert(span(path_start).start, (span(end - 1).end, &item.internal));
        }
    }
    let mut cursor = 0;
    for (start, (end, replacement)) in edits {
        append_tokens(file, cursor, start, output);
        output.push_str(replacement);
        cursor = end;
    }
    append_tokens(file, cursor, file.source.len(), output);
    output.push('\n');
    Ok(())
}

fn append_tokens(file: &File, start: usize, end: usize, output: &mut String) {
    let tokens = &file.tree.tokens;
    let first = tokens.partition_point(|token| token.span.start < start);
    let mut previous = start;
    for token in tokens[first..]
        .iter()
        .take_while(|token| token.span.start < end)
    {
        if token.span.start > previous {
            output.push(' ');
        }
        output.push_str(&file.source[token.span.start..token.span.end]);
        previous = token.span.end;
    }
    if previous < end {
        output.push(' ');
    }
}

#[derive(Clone, PartialEq, Eq, PartialOrd, Ord)]
enum Source {
    Local(PathBuf),
    Git { url: String, rev: String },
}

struct Package {
    visible: BTreeSet<String>,
    files: Vec<File>,
}

#[derive(Default)]
struct Loader {
    packages: Vec<Package>,
    names: BTreeMap<String, Source>,
    loading: BTreeSet<Source>,
    checkouts: Vec<tempfile::TempDir>,
}

fn manifest(text: &str, path: &Path) -> Result<(String, toml::Table)> {
    let table: toml::Table = text
        .parse()
        .map_err(|e| format!("{}: {e}", path.display()))?;
    let name = table
        .get("package")
        .and_then(|pkg| pkg.get("name"))
        .and_then(toml::Value::as_str)
        .filter(|name| identifier(name))
        .ok_or_else(|| format!("{}: expected a valid [package].name", path.display()))?;
    let dependencies = match table.get("dependencies") {
        Some(value) => value
            .as_table()
            .cloned()
            .ok_or_else(|| format!("{}: [dependencies] must be a table", path.display()))?,
        None => toml::Table::new(),
    };
    Ok((name.to_owned(), dependencies))
}

fn local_root(path: &Path) -> Result<PathBuf> {
    path.canonicalize()
        .map_err(|e| format!("{}: {e}", path.display()))
}

fn dependency(value: &toml::Value, root: &Path, confinement: Option<&Path>) -> Result<Source> {
    let table = value
        .as_table()
        .ok_or("expected { path = ... } or { git = ..., rev = ... }")?;
    let field = |key| {
        table
            .get(key)
            .and_then(toml::Value::as_str)
            .filter(|s| !s.is_empty())
    };
    if let (1, Some(path)) = (table.len(), field("path")) {
        let path = local_root(&root.join(path))?;
        if confinement.is_some_and(|checkout| !path.starts_with(checkout)) {
            return Err("path dependency escapes its pinned Git checkout".into());
        }
        return Ok(Source::Local(path));
    }
    if let (2, Some(url), Some(rev)) = (table.len(), field("git"), field("rev")) {
        if !matches!(rev.len(), 40 | 64) || !rev.bytes().all(|b| b.is_ascii_hexdigit()) {
            return Err("rev must be a full Git commit ID".into());
        }
        let url = if url.contains("://") || url.contains(':') {
            url.to_owned()
        } else {
            let path = local_root(&root.join(url))?;
            if confinement.is_some_and(|checkout| !path.starts_with(checkout)) {
                return Err("local Git dependency escapes its pinned Git checkout".into());
            }
            path.to_string_lossy().into_owned()
        };
        return Ok(Source::Git {
            url,
            rev: rev.to_ascii_lowercase(),
        });
    }
    Err("expected exactly path, or git and rev".into())
}

fn git(dir: &Path, args: &[&str]) -> Result<String> {
    let mut command = Command::new("git");
    for (key, _) in std::env::vars_os() {
        if key.to_string_lossy().starts_with("GIT_") {
            command.env_remove(key);
        }
    }
    let output = command
        .current_dir(dir)
        .env("GIT_TERMINAL_PROMPT", "0")
        .env("GIT_CONFIG_NOSYSTEM", "1")
        .env("GIT_CONFIG_GLOBAL", "/dev/null")
        .args([
            "-c",
            "protocol.allow=never",
            "-c",
            "protocol.https.allow=always",
            "-c",
            "protocol.ssh.allow=always",
            "-c",
            "protocol.file.allow=always",
            "-c",
            "core.hooksPath=/dev/null",
        ])
        .args(args)
        .output()
        .map_err(|e| format!("cannot run git: {e}"))?;
    if !output.status.success() {
        return Err(format!(
            "git {} failed: {}",
            args[0],
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    Ok(String::from_utf8_lossy(&output.stdout).trim().to_owned())
}

impl Loader {
    fn load(
        &mut self,
        source: Source,
        expected: Option<&str>,
        inherited: Option<&Path>,
        target: &BuildTarget,
    ) -> Result<()> {
        if self.loading.contains(&source) {
            return Err(format!(
                "dependency cycle involving {}",
                expected.unwrap_or("the root package")
            ));
        }
        if let Some((name, _)) = self.names.iter().find(|(_, loaded)| **loaded == source) {
            return if expected.is_none_or(|expected| expected == name) {
                Ok(())
            } else {
                Err(format!(
                    "expected package {}, found {name}",
                    expected.unwrap()
                ))
            };
        }
        let mut confinement = inherited.map(Path::to_owned);
        let root = match &source {
            Source::Local(path) => path.clone(),
            Source::Git { url, rev } => {
                let checkout = tempfile::tempdir().map_err(|e| e.to_string())?;
                let dir = checkout.path();
                let format = if rev.len() == 64 {
                    "--object-format=sha256"
                } else {
                    "--object-format=sha1"
                };
                git(dir, &["init", "--quiet", "--template=", format])?;
                git(
                    dir,
                    &["fetch", "--quiet", "--depth=1", "--no-tags", "--", url, rev],
                )?;
                if git(dir, &["rev-parse", "FETCH_HEAD"])? != *rev
                    || git(dir, &["cat-file", "-t", rev])? != "commit"
                {
                    return Err(format!(
                        "Git revision {rev} did not resolve to the requested commit"
                    ));
                }
                git(dir, &["checkout", "--quiet", "--detach", rev])?;
                let dir = local_root(dir)?;
                confinement = Some(dir.clone());
                self.checkouts.push(checkout);
                dir
            }
        };
        let path = root.join("package.toml");
        let text = fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?;
        let (name, dependencies) = manifest(&text, &path)?;
        if matches!(name.as_str(), "std" | "runtime") {
            return Err(format!("{}: reserved package name {name}", path.display()));
        }
        if let Some(expected) = expected
            && expected != name
        {
            return Err(format!(
                "{}: expected package {expected}, found {name}",
                path.display()
            ));
        }
        if self.names.insert(name.clone(), source.clone()).is_some() {
            return Err(format!("package {name} is provided by multiple sources"));
        }
        self.loading.insert(source.clone());
        let mut visible = BTreeSet::from([name.clone(), "std".to_owned()]);
        let mut files = Vec::new();
        let src = root.join("src");
        let entry = src.join("main.crb");
        if let Some(checkout) = &confinement {
            for input in [&path, &src] {
                if !local_root(input)?.starts_with(checkout) {
                    return Err(format!(
                        "{} escapes its pinned Git checkout",
                        input.display()
                    ));
                }
            }
        }
        files_in(&src, &vec![name.clone()], &mut files, target)?;
        if expected.is_none() {
            files.sort_by_key(|file| (file.path != entry, file.path.clone()));
        }
        self.packages.push(Package {
            visible: BTreeSet::new(),
            files,
        });
        let package = self.packages.len() - 1;
        for (key, value) in dependencies {
            if !identifier(&key) || matches!(key.as_str(), "std" | "runtime") || key == name {
                return Err(format!("{}: invalid dependency name {key}", path.display()));
            }
            let input = dependency(&value, &root, confinement.as_deref())
                .map_err(|e| format!("{}: dependency {key}: {e}", path.display()))?;
            self.load(input, Some(&key), confinement.as_deref(), target)
                .map_err(|e| format!("dependency {key}: {e}"))?;
            visible.insert(key);
        }
        self.packages[package].visible = visible;
        self.loading.remove(&source);
        Ok(())
    }
}

pub fn load(root: &Path) -> Result<String> {
    load_for_target(root, &BuildTarget::host())
}

pub fn load_for_target(root: &Path, target: &BuildTarget) -> Result<String> {
    load_with_std_range(root, target).map(|(source, _, _)| source)
}

pub fn load_with_std_range(root: &Path, target: &BuildTarget) -> Result<(String, std::ops::Range<usize>, std::ops::Range<usize>)> {
    let (source, file_range, env_range, _, _, _) = load_for_verification(root, target)?;
    Ok((source, file_range, env_range))
}

pub(crate) type OpaqueLayouts = BTreeMap<String, (std::ops::Range<usize>, &'static str)>;
type SourceRange = std::ops::Range<usize>;

pub(crate) fn load_for_verification(
    root: &Path,
    target: &BuildTarget,
) -> Result<(String, SourceRange, SourceRange, Vec<SourceRange>, Vec<SourceRange>, OpaqueLayouts)> {
    let root = local_root(root)?;
    let entry = root.join("src/main.crb");
    let mut loader = Loader::default();
    loader.load(Source::Local(root), None, None, target)?;
    let std_manifest = Path::new("stdlib/package.toml");
    let (name, dependencies) = manifest(include_str!("../../stdlib/package.toml"), std_manifest)?;
    if name != "std" || !dependencies.is_empty() {
        return Err("bundled standard library must be named std and have no dependencies".into());
    }
    let sources: &[(&str, &str)] = include!(concat!(env!("OUT_DIR"), "/stdlib.rs"));
    let uses_crypto = loader.packages.iter().flat_map(|package| &package.files).any(|file| {
        let qualified = file.tree.tokens.windows(3).enumerate().any(|(i, _)| {
            file.word(i) == "std" && file.word(i + 1) == "::" && file.word(i + 2) == "crypto"
        });
        qualified || file.tree.syntax.nodes[file.tree.syntax.root.0].children.iter().any(|&id| {
            let node = &file.tree.syntax.nodes[id.0];
            node.kind == "use" && file.word(node.start + 1) == "std"
                && file.word(node.start + 3) == "{"
                && node.children.iter().any(|&child| {
                    let member = &file.tree.syntax.nodes[child.0];
                    member.kind == "import member" && file.word(member.name.unwrap()) == "crypto"
                })
        })
    });
    let mentions_module = |component: &str| loader.packages.iter().flat_map(|package| &package.files)
        .any(|file| {
            file.tree.tokens.windows(2).enumerate().any(|(i, _)| {
                file.word(i) == "::" && file.word(i + 1) == component
            }) || file.tree.syntax.nodes.iter().any(|node| {
                node.kind == "import member" && file.word(node.name.unwrap()) == component
            })
        });
    let mentions_tls = mentions_module("tls");
    let mentions_openssl = mentions_tls && mentions_module("openssl");
    let files = sources
        .iter()
        .filter(|(path, _)| {
            (!path.starts_with("src/crypto/") || uses_crypto || mentions_tls)
                && (!path.starts_with("src/net/tls/") || mentions_tls)
                && (!path.starts_with("src/net/tls/openssl/") || mentions_openssl)
        })
        .map(|&(path, source)| {
            let mut module = vec![name.clone()];
            module.extend(
                path.split('/')
                    .skip(1)
                    .take_while(|part| !part.ends_with(".crb"))
                    .map(str::to_owned),
            );
            parse_file(
                Path::new("stdlib").join(path),
                module,
                source.to_owned(),
                target,
            )
        })
        .collect::<Result<Vec<_>>>()?;
    loader.packages.push(Package {
        visible: BTreeSet::from([name]),
        files,
    });
    let mut symbols = Symbols {
        items: BTreeMap::new(),
        modules: BTreeSet::new(),
    };
    let mut has_main = false;
    for file in loader.packages.iter().flat_map(|package| &package.files) {
        for depth in 1..=file.module.len() {
            symbols.modules.insert(file.module[..depth].to_vec());
        }
        if file.tree.tokens.iter().enumerate().any(|(i, token)| {
            token.kind == Kind::Name && file.word(i).starts_with("__crust_package_")
        }) {
            return Err(format!(
                "{}: reserved compiler name prefix __crust_package_",
                file.path.display()
            ));
        }
        for &id in &file.tree.syntax.nodes[file.tree.syntax.root.0].children {
            let node = &file.tree.syntax.nodes[id.0];
            if node.kind == "annotation"
                && file.word(node.name.unwrap()) == "datastack"
                && file.path != entry
            {
                return Err(file.error(
                    node.start,
                    "datastack configuration belongs in src/main.crb",
                ));
            }
            if !matches!(node.kind, "fn" | "async fn" | "extern" | "struct" | "enum" | "const") {
                continue;
            }
            let local = file.word(node.name.unwrap());
            if matches!(local, "print" | "copy" | "drop") {
                return Err(file.error(node.start, format!("reserved component name {local}")));
            }
            let is_main = file.path == entry && local == "main";
            if local == "main" && file.module.len() == 1 && file.path != entry {
                return Err(file.error(node.start, "main must be in the executable src/main.crb"));
            }
            if is_main {
                if file.path != entry || node.kind != "fn" {
                    return Err(file.error(
                        node.start,
                        "main must be a synchronous function in src/main.crb",
                    ));
                }
                has_main = true;
            }
            let mut path = file.module.clone();
            path.push(local.to_owned());
            let internal = if is_main {
                "main".to_owned()
            } else if path.iter().map(String::as_str).eq(["std", "iter", "Iter"]) {
                ITER_ADAPTER.to_owned()
            } else if path.iter().map(String::as_str).eq(["std", "io", "File"]) {
                "__crust_package_opaque_file".to_owned()
            } else if path.iter().map(String::as_str).eq(["std", "net", "tls", "openssl", "Connection"]) {
                TLS_CONNECTION.to_owned()
            } else if path.iter().map(String::as_str).eq(["std", "env", "args"]) {
                "__crust_package_env_args".to_owned()
            } else if path.iter().map(String::as_str).eq(["std", "bytes", "content_eq"]) {
                "__crust_package_byte_content_eq".to_owned()
            } else if file.module.iter().map(String::as_str).eq(["std", "sys", "net", "reactor"])
                && matches!(local, "queue_create" | "queue_watch" | "queue_wait" |
                    "completion_create" | "completion_attach" | "completion_submit" | "completion_next")
            {
                format!("__crust_package_socket_{local}")
            } else {
                format!("__crust_package_{}", symbols.items.len())
            };
            let item = Item {
                internal,
                public: node.public,
                nominal: matches!(node.kind, "struct" | "enum"),
                path: file.path.clone(),
            };
            if let Some(previous) = symbols.items.insert(path.clone(), item) {
                return Err(file.error(
                    node.start,
                    format!(
                        "duplicate component {} also in {}",
                        path.join("::"),
                        previous.path.display()
                    ),
                ));
            }
        }
    }
    if !has_main {
        return Err(format!(
            "{}: missing synchronous main function",
            entry.display()
        ));
    }
    let mut source = String::new();
    let mut file_range = 0..0;
    let mut env_range = 0..0;
    let mut socket_wait_ranges = Vec::new();
    let mut async_io_ranges = Vec::new();
    let mut opaque_layouts = BTreeMap::new();
    for package in &loader.packages {
        for file in &package.files {
            let start = source.len();
            lower(file, &package.visible, &symbols, &mut source)?;
            if file.module.iter().map(String::as_str).eq(["std", "io"]) {
                file_range = start..source.len();
            } else if file.module.iter().map(String::as_str).eq(["std", "env"]) {
                env_range = start..source.len();
            } else if file.module.iter().map(String::as_str).eq(["std", "sys", "net", "reactor"]) {
                socket_wait_ranges.push(start..source.len());
            } else {
                let module = file.module.iter().map(String::as_str).collect::<Vec<_>>();
                if matches!(module.as_slice(), ["std", "io", "asyn", ..] | ["std", "sys", "net", "asyn"] | ["std", "net", ..]) {
                    async_io_ranges.push(start..source.len());
                }
                let label = match module.as_slice() {
                    ["std", "io", "asyn"] => "représentation privée de std::io::asyn",
                    ["std", "net", "asyn", "tcp"] => "représentation privée de std::net::asyn::tcp",
                    ["std", "net", "asyn", "udp"] => "représentation privée de std::net::asyn::udp",
                    ["std", "net", "tcp"] => "représentation privée de std::net::tcp",
                    ["std", "net", "udp"] => "représentation privée de std::net::udp",
                    ["std", "sys", "net"] => "représentation privée de std::sys::net",
                    ["std", "net", "tls", "openssl"] => "représentation privée de std::net::tls::openssl",
                    ["std", "crypto", "aes"] => "représentation privée de std::crypto::aes",
                    ["std", "crypto", "md5"] => "représentation privée de std::crypto::md5",
                    ["std", "crypto", "sha256"] => "représentation privée de std::crypto::sha256",
                    ["std", "crypto", "sha512"] => "représentation privée de std::crypto::sha512",
                    ["std", "crypto", "sha3"] => "représentation privée de std::crypto::sha3",
                    ["std", "net", "tls"] => "représentation privée de std::net::tls",
                    ["std", "net", "tls", "record"] => "représentation privée de std::net::tls::record",
                    ["std", "crypto", "x509"] => "représentation privée de std::crypto::x509",
                    ["std", "crypto", "p256"] => "représentation privée de std::crypto::p256",
                    _ => continue,
                };
                for name in ["File", "Connection", "Listener", "PlatformSocket", "ReadHalf", "WriteHalf", "Md5", "Sha256", "Sha384", "Sha512", "Sha3_224", "Sha3_256", "Sha3_384", "Sha3_512", "AES128GCM", "AES256GCM", "EphemeralKey", "SigningKey", "PublicKey", "RecordCipher", "Session", "Certificate"] {
                    let mut symbol = file.module.clone();
                    symbol.push(name.to_owned());
                    if let Some(item) = symbols.items.get(&symbol)
                        && item.path == file.path
                    {
                        opaque_layouts.insert(item.internal.clone(), (start..source.len(), label));
                    }
                }
            }
        }
    }
    Ok((source, file_range, env_range, socket_wait_ranges, async_io_ranges, opaque_layouts))
}
