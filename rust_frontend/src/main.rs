use corbo_frontend::{
    frontend,
    parser::Mode,
    tree::{Fact, StaticTree},
};
use std::{
    io::{self, BufRead, Read, Write},
    process::ExitCode,
};

fn summary(tree: &StaticTree, source: &str) -> String {
    let lexemes = tree
        .tokens
        .iter()
        .filter(|token| token.span.start != token.span.end)
        .map(|token| encode_hex(&source.as_bytes()[token.span.start..token.span.end]))
        .collect::<Vec<_>>()
        .join(",");
    let mut scopes = Vec::new();
    for scope in &tree.scopes[1..] {
        let node = &tree.syntax.nodes[scope.syntax.0];
        if node.kind == "scope" || matches!(node.kind, "loop" | "while" | "bras") {
            let start = if node.kind == "scope" {
                node.children
                    .first()
                    .and_then(|child| {
                        let child = &tree.syntax.nodes[child.0];
                        (child.kind == "annotation").then_some(child.end)
                    })
                    .unwrap_or(node.start)
            } else {
                node.start
            };
            let line = source[..tree.tokens[start].span.start]
                .bytes()
                .filter(|b| *b == b'\n')
                .count()
                + 1;
            scopes.push(format!("{}:{line}", scope.parent.unwrap().0));
        }
    }
    let facts = tree
        .points
        .iter()
        .filter_map(|point| match point.fact {
            Fact::NamedMove { .. } => Some("move"),
            Fact::Pool { .. } => Some("pool"),
            Fact::Borrow { .. } => Some("borrow"),
            Fact::AddressCandidate { .. } => Some("address"),
            _ => None,
        })
        .collect::<Vec<_>>()
        .join(",");
    let bindings = tree
        .bindings
        .iter()
        .filter(|binding| tree.syntax.nodes[binding.syntax.0].kind == "liaison")
        .map(|binding| binding.name.as_str())
        .collect::<Vec<_>>()
        .join(",");
    let moves = tree
        .points
        .iter()
        .filter_map(|point| {
            let Fact::NamedMove {
                source,
                destination,
            } = point.fact
            else {
                return None;
            };
            let target = &tree.bindings[destination.0];
            let origin = source
                .map(|id| tree.bindings[id.0].scope.0.to_string())
                .unwrap_or_default();
            Some(format!("{}:{origin}:{}", target.name, target.scope.0))
        })
        .collect::<Vec<_>>()
        .join(",");
    format!(
        "OK\t{lexemes}\t{}\t{bindings}\t{facts}\t{moves}",
        scopes.join(",")
    )
}

fn encode_hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn decode_hex(text: &str) -> Option<String> {
    if !text.len().is_multiple_of(2) || !text.is_ascii() {
        return None;
    }
    let bytes = (0..text.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&text[i..i + 2], 16).ok())
        .collect::<Option<Vec<_>>>()?;
    String::from_utf8(bytes).ok()
}

fn mode(text: &str) -> Option<Mode> {
    match text {
        "program" => Some(Mode::Program),
        "block" => Some(Mode::Block),
        "signature" => Some(Mode::Signature),
        _ => None,
    }
}

fn token_summary(source: &str) -> String {
    use corbo_frontend::lexer::{Kind, lex};

    match lex(source) {
        Ok(tokens) => {
            let tokens = tokens
                .iter()
                .map(|token| {
                    let class = match token.kind {
                        Kind::Eof => 0,
                        Kind::Name => 1,
                        Kind::Integer => 2,
                        Kind::Float => 3,
                        Kind::Text => 4,
                        Kind::Punct => 5,
                        Kind::Assembly => 6,
                    };
                    format!("{class}:{}:{}", token.span.start, token.span.end)
                })
                .collect::<Vec<_>>()
                .join(",");
            format!("OK\t{tokens}")
        }
        Err(error) => format!("ERR\t{}\t{}", error.offset, error.message),
    }
}

fn syntax_summary(source: &str) -> Result<String, corbo_frontend::Error> {
    use corbo_frontend::{parse_for_target, target};
    use std::fmt::Write as _;

    let (tokens, syntax) = parse_for_target(source, Mode::Program, &target::Target::host())?;
    let mut output = String::from("OK");
    let mut pending = vec![(syntax.root, 0)];
    let mut position = 0;
    while let Some((id, parent)) = pending.pop() {
        let node = &syntax.nodes[id.0];
        let (start, end) = if id == syntax.root {
            (0, source.len())
        } else if let Some(operand) = node.asm_operand {
            (operand.start, operand.end)
        } else {
            (tokens[node.start].span.start, tokens[node.end - 1].span.end)
        };
        let (name_start, name_end) = node.name
            .map(|index| {
                let span = tokens[index].span;
                let end = if node.kind == "affectation" && &source[span.start..span.end] == ">" {
                    tokens[index + 2].span.end
                } else {
                    span.end
                };
                (span.start, end)
            })
            .unwrap_or((0, 0));
        let kind = node.kind;
        let public = u8::from(node.public);
        write!(output, "\t{kind}:{parent}:{start}:{end}:{name_start}:{name_end}:{public}").unwrap();
        pending.extend(node.children.iter().rev().map(|&child| (child, position)));
        position += 1;
    }
    Ok(output)
}

fn batch() -> io::Result<()> {
    let mut output = io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let line = line?;
        if let Some(text) = line.strip_prefix("lex\t") {
            match decode_hex(text) {
                Some(source) => writeln!(output, "{}", token_summary(&source))?,
                None => writeln!(output, "ERR\t0\trequête invalide")?,
            }
            continue;
        }
        if let Some(text) = line.strip_prefix("ast\t") {
            match decode_hex(text).as_deref().map(syntax_summary) {
                Some(Ok(syntax)) => writeln!(output, "{syntax}")?,
                Some(Err(error)) => writeln!(output, "ERR\t{}\t{}", error.offset, error.message)?,
                None => writeln!(output, "ERR\t0\trequête invalide")?,
            }
            continue;
        }
        if let Some(text) = line.strip_prefix("verify\t") {
            match decode_hex(text) {
                Some(source) => {
                    let result = frontend(&source, Mode::Program).and_then(|tree| {
                        corbo_frontend::verify::verify(&source, &tree)
                    });
                    match result {
                        Ok(_) => writeln!(output, "OK")?,
                        Err(error) => writeln!(output, "ERR\t{}\t{}", error.offset, error.message)?,
                    }
                }
                None => writeln!(output, "ERR\t0\trequête invalide")?,
            }
            continue;
        }
        let input = line
            .split_once('\t')
            .and_then(|(kind, text)| Some((mode(kind)?, decode_hex(text)?)));
        match input {
            Some((mode, source)) => match frontend(&source, mode) {
                Ok(tree) => writeln!(output, "{}", summary(&tree, &source))?,
                Err(error) => writeln!(output, "ERR\t{}\t{}", error.offset, error.message)?,
            },
            None => writeln!(output, "ERR\t0\trequête invalide")?,
        }
    }
    output.flush()
}

fn build_executable(
    program: &corbo_frontend::verify::VerifiedProgram,
    path: &std::path::Path,
) -> Result<(), String> {
    use std::process::{Command, Stdio};

    let compiler = std::env::var_os("CC").unwrap_or_else(|| "cc".into());
    let mut command = Command::new(compiler);
    command.args(["-std=c11", "-pthread", "-x", "c", "-"]).arg("-lm");
    if cfg!(windows) {
        command.args(["-lws2_32", "-ladvapi32", "-lbcrypt"]);
    }
    if program.requires_openssl {
        if let Some(directory) = std::env::var_os("DIN_OPENSSL_LIB_DIR") {
            command.arg("-L").arg(directory);
        }
        command.args(["-lssl", "-lcrypto"]);
    }
    let mut child = command
        .arg("-o")
        .arg(path)
        .stdin(Stdio::piped())
        .spawn()
        .map_err(|error| format!("could not start the C compiler: {error}"))?;
    let generated = corbo_frontend::c_backend::emit_c(program);
    let written = child.stdin.take().unwrap().write_all(generated.as_bytes());
    let status = child.wait().map_err(|error| format!("C compiler wait failed: {error}"))?;
    if !status.success() {
        return Err(format!("C compilation failed ({status})"));
    }
    written.map_err(|error| format!("could not write generated C: {error}"))
}

fn output_program(
    command: &str,
    program: &corbo_frontend::verify::VerifiedProgram,
    output: Option<&std::path::Path>,
) -> ExitCode {
    match command {
        "emit-c" => print!("{}", corbo_frontend::c_backend::emit_c(program)),
        "build" => {
            if let Err(error) = build_executable(program, output.unwrap()) {
                eprintln!("{error}");
                return ExitCode::FAILURE;
            }
        }
        _ => {}
    }
    ExitCode::SUCCESS
}

fn main() -> ExitCode {
    let mut args = std::env::args().skip(1);
    let arg = args.next().unwrap_or_else(|| "program".to_owned());
    let mut target = corbo_frontend::target::Target::host();
    let mut root = None;
    let mut explicit_target = false;
    let mut output = None;
    while let Some(option) = args.next() {
        if option == "-o" && arg == "build" && output.is_none() {
            let Some(path) = args.next() else {
                eprintln!("-o requires an executable path");
                return ExitCode::FAILURE;
            };
            output = Some(std::path::PathBuf::from(path));
        } else if option == "--target" && !explicit_target && arg != "--batch" {
            explicit_target = true;
            let Some(triple) = args.next() else {
                eprintln!("--target requires a target triple");
                return ExitCode::FAILURE;
            };
            match corbo_frontend::target::Target::from_triple(&triple) {
                Ok(value) => target = value,
                Err(error) => {
                    eprintln!("{error}");
                    return ExitCode::FAILURE;
                }
            }
        } else if !option.starts_with('-')
            && matches!(arg.as_str(), "check" | "emit-c" | "build")
            && root.is_none()
        {
            root = Some(option);
        } else {
            eprintln!("unexpected argument: {option}");
            return ExitCode::FAILURE;
        }
    }
    if arg == "--batch" {
        return if batch().is_ok() {
            ExitCode::SUCCESS
        } else {
            ExitCode::FAILURE
        };
    }
    if arg == "build" && (output.is_none() || explicit_target) {
        eprintln!("usage: corbo-frontend build [package-dir] -o <executable> (host target)");
        return ExitCode::FAILURE;
    }
    if matches!(arg.as_str(), "check" | "emit-c" | "build") {
        if let Some(root) = root {
            return match corbo_frontend::verify_package(std::path::Path::new(&root), &target) {
                Ok(program) => output_program(&arg, &program, output.as_deref()),
                Err(error) => {
                    eprintln!("{error}");
                    ExitCode::FAILURE
                }
            };
        }
        let mut source = String::new();
        if let Err(error) = io::stdin().read_to_string(&mut source) {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
        let result = corbo_frontend::frontend_for_target(&source, Mode::Program, &target)
            .and_then(|tree| corbo_frontend::verify::verify(&source, &tree));
        return match result {
            Ok(program) => output_program(&arg, &program, output.as_deref()),
            Err(error) => {
                eprintln!("octet {}: {}", error.offset, error.message);
                if let Some(offset) = error.related_offset {
                    eprintln!("déplacement à l’octet {offset}");
                }
                ExitCode::FAILURE
            }
        };
    }
    let Some(mode) = mode(&arg) else {
        eprintln!(
            "usage: corbo-frontend [program|block|signature|--batch] or [check|emit-c] [package-dir] [--target TRIPLE] or build [package-dir] -o <executable>"
        );
        return ExitCode::FAILURE;
    };
    let mut source = String::new();
    if let Err(error) = io::stdin().read_to_string(&mut source) {
        eprintln!("{error}");
        return ExitCode::FAILURE;
    }
    match corbo_frontend::frontend_for_target(&source, mode, &target) {
        Ok(tree) => {
            println!("{tree:#?}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("octet {}: {}", error.offset, error.message);
            ExitCode::FAILURE
        }
    }
}
