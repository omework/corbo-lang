mod assembly;
mod placement;
mod regions;

mod flow;
mod generics;

pub mod c_backend;
pub mod lexer;
pub mod package;
pub mod parser;
pub mod tree;
pub mod target;
pub mod verify;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Span {
    pub start: usize,
    pub end: usize,
}

#[derive(Debug)]
pub struct Error {
    pub offset: usize,
    pub message: &'static str,
    pub related_offset: Option<usize>,
}

impl Error {
    pub fn new(offset: usize, message: &'static str) -> Self {
        Self {
            offset,
            message,
            related_offset: None,
        }
    }
}

pub fn frontend(source: &str, mode: parser::Mode) -> Result<tree::StaticTree, Error> {
    frontend_for_target(source, mode, &target::Target::host())
}

pub fn frontend_for_target(source: &str, mode: parser::Mode, target: &target::Target) -> Result<tree::StaticTree, Error> {
    let (tokens, syntax) = parse_for_target(source, mode, target)?;
    let mut tree = tree::StaticTree::from_syntax(source, tokens, syntax);
    tree.target = target.clone();
    Ok(tree)
}

pub fn parse_for_target(
    source: &str,
    mode: parser::Mode,
    target: &target::Target,
) -> Result<(Vec<lexer::Token>, parser::Syntax), Error> {
    let mut tokens = lexer::lex(source)?;
    if matches!(mode, parser::Mode::Program) {
        tokens = target::select(source, tokens, target)?;
    }
    let syntax = parser::parse(source, &tokens, mode)?;
    Ok((tokens, syntax))
}

pub fn verify_package(
    root: &std::path::Path,
    target: &target::Target,
) -> Result<verify::VerifiedProgram, String> {
    let (source, file_range, env_range, socket_wait_ranges, async_io_ranges, opaque_layouts) = package::load_for_verification(root, target)?;
    let mut tree = frontend_for_target(&source, parser::Mode::Program, target)
        .map_err(format_diagnostic)?;
    tree.std_file_range = file_range;
    tree.std_env_range = env_range;
    tree.std_socket_wait_ranges = socket_wait_ranges;
    tree.std_async_io_ranges = async_io_ranges;
    tree.opaque_layouts = opaque_layouts;
    verify::verify(&source, &tree).map_err(format_diagnostic)
}

fn format_diagnostic(error: Error) -> String {
    let mut message = format!("octet {}: {}", error.offset, error.message);
    if let Some(offset) = error.related_offset {
        message.push_str(&format!("\ndéplacement à l’octet {offset}"));
    }
    message
}
