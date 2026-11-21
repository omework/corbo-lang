"""Check package emission by corboc and optionally require full self-hosting."""

import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

from check_crust_bootstrap import FRONTEND, PACKAGE, ROOT
from check_rust_file_io import PENDING_READ, PENDING_RENAME, PENDING_SEEK
from check_rust_file_io import program as file_io_program


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def emit(compiler, package, destination, stdlib=None):
    command = [compiler, "--emit-package-c", package]
    if stdlib is not None:
        command.extend(["--stdlib-dir", stdlib])
    with destination.open("wb") as output:
        result = subprocess.run(command, stdout=output)
    if result.returncode:
        with destination.open("rb") as output:
            diagnostic = output.read(4096).decode(errors="replace").strip()
        message = f"corboc could not emit {package} (status {result.returncode})"
        if diagnostic:
            message += f"\n{diagnostic}"
        raise RuntimeError(message)


def compile_c(source, binary, ubsan=False):
    flags = (
        ["-O2", "-fsanitize=undefined", "-fno-sanitize-recover=undefined"]
        if ubsan else ["-O0"]
    )
    run([os.environ.get("CC", "cc"), "-std=c11", "-pthread", *flags,
         source, "-lm", "-o", binary])


def check_package(compiler, directory):
    package = directory / "demo"
    source = package / "src"
    (source / "math").mkdir(parents=True)
    (package / "package.toml").write_text('[package]\nname = "demo"\n')
    main = source / "main.crb"
    main.write_text(
        "use demo::math::{double as twice, offset};\n"
        "fn main() { print(twice(20) + offset()); }\n"
    )
    (source / "math" / "numbers.crb").write_text(
        "fn sum(x: i64, y: i64) -> i64 { x + y }\n"
        "pub fn double(x: i64) -> i64 { sum(copy(x), x) }\n"
        "pub fn offset() -> i64 { 2 }\n"
    )
    rust = directory / "demo-rust"
    run([FRONTEND, "build", package, "-o", rust])
    expected = run([rust], capture_output=True)
    assert expected.stdout == b"42\n" and expected.stderr == b""
    generated = directory / "demo.c"
    emit(compiler, package, generated)
    for ubsan in (False, True):
        native = directory / ("demo-ubsan" if ubsan else "demo-native")
        compile_c(generated, native, ubsan)
        actual = run([native], capture_output=True)
        assert (actual.stdout, actual.stderr) == (expected.stdout, expected.stderr)
    for text, diagnostic in (
        ("use demo::math::sum; fn main() {}", 13),
        ("use demo::math::{double as twice, offset as twice}; fn main() {}", 14),
        ("use demo::math::offset; fn offset() -> i64 { 0 } fn main() {}", 14),
    ):
        main.write_text(text)
        result = subprocess.run([compiler, "--emit-package-c", package], capture_output=True)
        assert (result.returncode, result.stdout) == (diagnostic, b""), result
        reference = subprocess.run([FRONTEND, "check", package], capture_output=True)
        assert reference.returncode != 0, reference

    main.write_text(
        "use demo::math::Point as Coordinate;\n"
        "use demo::math as math;\n"
        "fn main() { let point = Coordinate { x: math::value() }; print(point.x); }\n"
    )
    (source / "math" / "numbers.crb").write_text(
        "pub struct Point { x: i64 }\n"
        "pub fn value() -> i64 { 42 }\n"
    )
    run([FRONTEND, "build", package, "-o", rust])
    expected = run([rust], capture_output=True)
    assert expected.stdout == b"42\n" and expected.stderr == b""
    emit(compiler, package, generated)
    native = directory / "record-ubsan"
    compile_c(generated, native, ubsan=True)
    actual = run([native], capture_output=True)
    assert (actual.stdout, actual.stderr) == (expected.stdout, expected.stderr)
    print("Two-module packages matched, including a named type, with three import refusals", flush=True)


def check_process_arguments(compiler, directory):
    package = directory / "arguments"
    source = package / "src"
    source.mkdir(parents=True)
    (package / "package.toml").write_text('[package]\nname = "arguments"\n')
    main = source / "main.crb"
    main.write_text("""use std::env::args;
fn main() -> i32 {
    match args() {
        Ok(arguments) => {
            print(arguments.len());
            if arguments.len() > 0 {
                let first = arguments[0];
                let bytes = first.as_bytes();
                print(bytes.len());
                print(bytes[0]);
            }
            return 0;
        },
        Err(_) => { return 7; },
    };
}
""")
    stdlib = ROOT / "stdlib" / "src"
    reference = directory / "arguments-rust"
    run([FRONTEND, "build", package, "-o", reference])
    generated = directory / "arguments.c"
    emit(compiler, package, generated, stdlib)
    for ubsan in (False, True):
        binary = directory / ("arguments-ubsan" if ubsan else "arguments-native")
        compile_c(generated, binary, ubsan)
        for arguments, status, stdout in (([], 0, b"0\n"), (["hello"], 0, b"1\n5\n104\n"),
                                          ([b"\xff"], 7, b"")):
            want = subprocess.run([reference, *arguments], capture_output=True)
            got = subprocess.run([binary, *arguments], capture_output=True)
            assert (want.returncode, want.stdout, want.stderr) == (status, stdout, b""), want
            assert (got.returncode, got.stdout, got.stderr) == (status, stdout, b""), got

    main.write_text("use std::env::args; fn main() { runtime::process_args(); }\n")
    rejected = subprocess.run([compiler, "--emit-package-c", package, "--stdlib-dir", stdlib], capture_output=True)
    assert rejected.returncode == 8, rejected
    print("Process argument traces and UTF-8 refusal matched Rust", flush=True)


def check_constants(compiler, directory):
    package = directory / "constants"
    module = package / "src" / "flags"
    module.mkdir(parents=True)
    (package / "package.toml").write_text('[package]\nname = "constants"\n')
    declarations = module / "mode.crb"
    definitions = """pub const DEFAULT: u8 = 1;
pub struct Mode {}
impl Mode {
    const APPEND: u8 = 2;
    const ZERO: i64 = 0;
    const MINIMUM: i64 = -9223372036854775808;
    const ENABLED: bool = true;
    const SCALE: f32 = .5;
}
"""
    declarations.write_text(definitions)
    source = package / "src" / "main.crb"
    program = """use constants::flags::{Mode as Flags, DEFAULT};
const LOCAL: u8 = 4;
fn main() {
    print(1 | Flags::APPEND | DEFAULT | LOCAL);
    print(Flags::MINIMUM);
    print(Flags :: // Associated member
        ENABLED);
    let scaled: f32 = Flags::SCALE;
    print(scaled > 0.0);
    let LOCAL: i64 = 8;
    print(LOCAL);
}
"""
    source.write_text(program)
    reference = directory / "constants-rust"
    run([FRONTEND, "build", package, "-o", reference])
    expected = run([reference], capture_output=True)
    assert (expected.stdout, expected.stderr) == (b"7\n-9223372036854775808\ntrue\ntrue\n8\n", b"")
    generated = directory / "constants.c"
    emit(compiler, package, generated)
    for ubsan in (False, True):
        variant = directory / ("constants-ubsan" if ubsan else "constants-native")
        compile_c(generated, variant, ubsan)
        actual = run([variant], capture_output=True)
        assert (actual.stdout, actual.stderr) == (expected.stdout, expected.stderr)
    for invalid in (
        definitions.replace("APPEND: u8 = 2", "APPEND: u8 = 256"),
        definitions.replace("APPEND: u8 = 2", "APPEND: u8 = true"),
        definitions + "impl Mode { const APPEND: u8 = 0; }",
        definitions + "impl Mode { fn APPEND() -> u8 { 2 } }",
        definitions.replace("pub const DEFAULT", "const DEFAULT"),
    ):
        declarations.write_text(invalid)
        rust = subprocess.run([FRONTEND, "check", package], capture_output=True)
        crust = subprocess.run([compiler, "--emit-package-c", package], capture_output=True)
        assert rust.returncode != 0 and crust.returncode in (8, 13), (rust, crust)
    declarations.write_text(definitions)
    for expression in (
        "Flags::APPEND()", "DEFAULT = 2", "let bad: i64 = Flags::APPEND",
        "print(1 / Flags::ZERO)",
    ):
        source.write_text(program.replace("print(LOCAL);", f"{expression};"))
        rust = subprocess.run([FRONTEND, "check", package], capture_output=True)
        crust = subprocess.run([compiler, "--emit-package-c", package], capture_output=True)
        assert rust.returncode != 0 and crust.returncode == 8, (rust, crust)
    print("Module and associated scalar constants matched Rust with nine refusals", flush=True)


def check_package_file(compiler, directory):
    package = directory / "read-demo"
    source = package / "src"
    source.mkdir(parents=True)
    (package / "package.toml").write_text('[package]\nname = "read_demo"\n')
    main = source / "main.crb"
    main.write_text("""use std::io::{File};
use std::io::{FileMode};
fn main() -> i32 {
    let path: [u8; 5] = [100,97,116,97,0];
    match File::open(&path[..], FileMode::read_only()) {
        Ok(opened) => {
            let mut file = opened;
            let mut output: [u8; 4] = [0; 4];
            match file.read(&mut output[..]) {
                Ok(count) => { print(count); print(output[0]); return 0; },
                Err(_) => { return 2; },
            };
        },
        Err(_) => { return 1; },
    };
}
""")
    reference = directory / "read-rust"
    run([FRONTEND, "build", package, "-o", reference])
    generated = directory / "read.c"
    stdlib = ROOT / "stdlib" / "src"
    emit(compiler, package, generated, stdlib)
    data = directory / "data"
    for ubsan in (False, True):
        binary = directory / ("read-ubsan" if ubsan else "read-native")
        compile_c(generated, binary, ubsan)
        for payload, status, stdout in ((b"abc", 0, b"3\n97\n"), (b"", 0, b"0\n0\n"), (None, 1, b"")):
            if payload is None:
                data.unlink()
            else:
                data.write_bytes(payload)
            want = subprocess.run([reference], cwd=directory, capture_output=True)
            got = subprocess.run([binary], cwd=directory, capture_output=True)
            assert (want.returncode, want.stdout, want.stderr) == (status, stdout, b""), want
            assert (got.returncode, got.stdout, got.stderr) == (status, stdout, b""), got
    main.write_text(main.read_text().replace("let mut file = opened;", "let file = opened;"))
    got = subprocess.run([compiler, "--emit-package-c", package, "--stdlib-dir", stdlib], capture_output=True)
    want = subprocess.run([FRONTEND, "check", package], capture_output=True)
    assert got.returncode == 8 and want.returncode != 0, (got, want)

    main.write_text("use std::sys::unix::native as os_files; fn main() {}\n")
    got = subprocess.run([compiler, "--emit-package-c", package, "--stdlib-dir", stdlib], capture_output=True)
    want = subprocess.run([FRONTEND, "check", package], capture_output=True)
    assert got.returncode == 13 and want.returncode != 0, (got, want)
    print("File reads and refusal to import platform internals matched Rust", flush=True)


def check_file_operations(compiler, directory):
    package = directory / "file-operations"
    (package / "src").mkdir(parents=True)
    (package / "package.toml").write_text('[package]\nname = "file_operations"\n')
    source = package / "src/main.crb"
    stdlib = ROOT / "stdlib" / "src"
    for mode in ("sync", "async"):
        source.write_text(file_io_program(asynchronous=mode == "async"))
        reference = directory / f"file-{mode}-rust"
        run([FRONTEND, "build", package, "-o", reference])
        generated = directory / f"file-{mode}.c"
        emit(compiler, package, generated, stdlib)
        for candidate in ("rust", "native", "ubsan"):
            binary = directory / f"file-{mode}-{candidate}"
            if candidate != "rust":
                compile_c(generated, binary, ubsan=candidate == "ubsan")
            workspace = directory / f"file-{mode}-{candidate}-workspace"
            workspace.mkdir()
            result = run([binary], cwd=workspace, capture_output=True, timeout=20)
            assert (result.stdout, result.stderr) == (b"42\n", b""), result
            assert not (workspace / "probe-é").exists()
            assert not (workspace / "renamed").exists()
    for program in (
        PENDING_READ.replace("CONFLICT", "drop(file);"),
        PENDING_READ.replace("CONFLICT", "output[0] = 4;"),
        PENDING_SEEK,
        PENDING_RENAME.replace("CONFLICT", "source"),
        PENDING_RENAME.replace("CONFLICT", "destination"),
    ):
        source.write_text(program)
        rust = subprocess.run([FRONTEND, "check", package], capture_output=True)
        crust = subprocess.run(
            [compiler, "--emit-package-c", package, "--stdlib-dir", stdlib], capture_output=True
        )
        assert rust.returncode != 0 and b"emprunt" in rust.stderr, rust
        assert crust.returncode == 8 and crust.stdout.startswith(b"5\n"), crust
    print("Sync and async File matched, including five pending borrow refusals", flush=True)


def check_self_host(compiler, directory):
    generated = directory / "corboc.c"
    emit(compiler, PACKAGE, generated, ROOT / "stdlib" / "src")
    for ubsan in (False, True):
        candidate = directory / ("corboc-ubsan" if ubsan else "corboc-native")
        compile_c(generated, candidate, ubsan)
        command = [sys.executable, ROOT / "validation" / "check_crust_codegen.py",
                   "--bootstrap", candidate, "--require-parity"]
        if ubsan:
            command.append("--ubsan")
        run(command)


def check_build(compiler, directory, rebuild):
    installation = directory / "compiler installation"
    bin_dir = installation / "bin"
    bin_dir.mkdir(parents=True)
    installed = bin_dir / "corboc"
    shutil.copy2(compiler, installed)
    bundled = installation / "share" / "corbo" / "stdlib" / "src"
    bundled.parent.mkdir(parents=True)
    shutil.copytree(ROOT / "stdlib" / "src", bundled)

    project = directory / "external project"
    (project / "src" / "math").mkdir(parents=True)
    (project / "package.toml").write_text('[package]\nname = "external"\n')
    main = project / "src" / "main.crb"
    main.write_text(
        "use external::math::double;\n"
        "use std::num::min_i64;\n"
        "fn main() { print(min_i64(double(21), 50)); }\n"
    )
    (project / "src" / "math" / "double.crb").write_text(
        "pub fn double(value: i64) -> i64 { copy(value) + value }\n"
    )
    working = directory / "separate working directory"
    working.mkdir()
    alias = working / "corboc-link"
    alias.symlink_to(installed)
    output = working / "-external program"
    command = [alias, "build", project, "-o", output.name]

    built = run(command, cwd=working, capture_output=True)
    assert built.stdout == b"" and built.stderr == b"", built
    result = run([output], cwd=working, capture_output=True)
    assert result.stdout == b"42\n" and result.stderr == b"", result
    original = output.read_bytes()

    failing_tools = directory / "failing C toolchain"
    failing_tools.mkdir()
    fake_cc = failing_tools / "cc"
    fake_cc.write_text("#!/bin/sh\nprintf 'witness: cc failed\\n' >&2\nexit 37\n")
    fake_cc.chmod(0o755)
    failed = subprocess.run(command, cwd=working, capture_output=True,
                            env={**os.environ, "PATH": str(failing_tools)})
    assert (failed.returncode, failed.stdout) == (37, b""), failed
    assert b"witness: cc failed\n" in failed.stderr, failed
    assert output.read_bytes() == original
    assert not list(working.glob(".corboc.*"))

    bundled.rename(bundled.with_name("absent"))
    missing = subprocess.run(command, cwd=working, capture_output=True)
    assert missing.returncode == 11 and b"standard library missing" in missing.stderr, missing
    assert output.read_bytes() == original
    bundled.with_name("absent").rename(bundled)

    valid = main.read_text()
    main.write_text(valid.replace("double(21)", "double(true)"))
    rejected = subprocess.run(command, cwd=working, capture_output=True)
    assert rejected.returncode == 8 and b"package compilation failed" in rejected.stderr, rejected
    assert output.read_bytes() == original and not list(working.glob(".corboc.*"))
    main.write_text(valid)
    print("Installed build compiled an external package with std and preserved output on failure", flush=True)

    check_dependencies(installed, directory, working)

    if rebuild:
        next_compiler = bin_dir / "corboc-next"
        run([installed, "build", PACKAGE, "-o", next_compiler], cwd=working)
        run([next_compiler, "build", project, "-o", output], cwd=working)
        result = run([output], cwd=working, capture_output=True)
        assert result.stdout == b"42\n" and result.stderr == b"", result
        print("corboc rebuilt itself using build, and its successor built the external package", flush=True)


def check_large_destructor(compiler, directory):
    source = directory / "large-destructor.crb"
    # Put the destructor beyond the range where node IDs resemble scalars.
    # The slice parameter selects the general C emitter.
    source.write_text(
        "fn unused() {\n" + "print(1);\n" * 3517 + "}\n"
        "struct Item { value: i64 }\n"
        "impl Item { fn drop(&mut self) { print((*self).value); } }\n"
        "fn main() { let item = Item { value: 17 }; drop(item); }\n"
        "fn length(input: &[u8]) -> usize { input.len() }\n"
    )
    generated = directory / "large-destructor.c"
    with generated.open("wb") as output:
        run([compiler, "--emit-c", source], stdout=output)
    candidate = directory / "large-destructor"
    compile_c(generated, candidate, ubsan=True)
    result = run([candidate], capture_output=True)
    assert result.stdout == b"17\n" and result.stderr == b"", result
    print("A large destructor node emitted valid C and ran once under UBSan", flush=True)


def check_dependencies(compiler, directory, working):
    def package(folder, name, body, entry="lib.crb"):
        (folder / "src").mkdir(parents=True)
        manifest = folder / "package.toml"
        manifest.write_text(f'[package]\nname = "{name}"\n')
        (folder / "src" / entry).write_text(body)
        return manifest

    def git(folder, *args):
        return run(["git", "-C", folder, *args], capture_output=True, text=True).stdout.strip()

    def commit(folder, message):
        git(folder, "add", ".")
        git(folder, "-c", "user.name=Test", "-c", "user.email=test@example.org", "commit", "-qm", message)
        return git(folder, "rev-parse", "HEAD")

    root = directory / "dependency project"
    program = (
        "use std::num::min_i64; use middle::score; use pinned::value;\n"
        "fn main() { print(min_i64(score(), value())); }\n"
    )
    manifest = package(root, "app", program, "main.crb")
    main = root / "src" / "main.crb"
    leaf = package(directory / "leaf", "leaf", "pub fn value() -> i64 { 45 }")
    middle = package(directory / "middle", "middle", "use leaf::value; pub fn score() -> i64 { value() }")
    middle.write_text(middle.read_text() + '[dependencies]\nleaf = { path = "../leaf" }\n')
    remote = directory / "git repo with spaces"
    pinned = package(remote, "pinned", "use nested::seed; pub fn value() -> i64 { seed() }")
    package(remote / "parts" / "nested", "nested", "pub fn seed() -> i64 { 42 }")
    pinned.write_text(pinned.read_text() + '[dependencies]\nnested = { path = "parts/nested" }\n')
    git(remote, "init", "-q")
    pin = commit(remote, "pinned")
    (remote / "src" / "lib.crb").write_text("pub fn value() -> i64 { 999 }")
    commit(remote, "later")
    baseline = manifest.read_text() + (
        '[dependencies]\nmiddle = { path = "../middle" }\n'
        f'pinned = {{ rev = "{pin.upper()}", git = "../git repo with spaces" }} # exact commit\n'
    )
    manifest.write_text(baseline)
    output = working / "with-dependencies"
    command = [compiler, "build", root, "-o", output]
    built = run(command, cwd=working, capture_output=True,
                env={**os.environ, "GIT_PROTOCOL_FROM_USER": "0", "GIT_DIR": "/does-not-exist"})
    assert built.stdout == b"" and built.stderr == b"", built
    result = run([output], cwd=working, capture_output=True)
    assert result.stdout == b"42\n" and result.stderr == b"", result
    reference = working / "reference-dependencies"
    run([FRONTEND, "build", root, "-o", reference], cwd=working)
    assert run([reference], capture_output=True).stdout == result.stdout
    original = output.read_bytes()

    # The root cannot use a transitive dependency, with or without an import.
    for body, declaration, expected in (
        ("use leaf::value; fn main() {}", baseline, 13),
        ("fn main() { print(leaf::value()); }", baseline, 13),
        (program, baseline.replace(pin.upper(), "main"), 18),
        (program, baseline.replace(pin.upper(), "0" * 40), 19),
        (program, baseline.replace("middle = ", "wrong = "), 17),
        (program, baseline + 'std = { path = "../leaf" }\n', 12),
        (program, baseline.replace('path = "../middle"', 'path = "../middle", rev = "main"'), 12),
    ):
        main.write_text(body)
        manifest.write_text(declaration)
        failed = subprocess.run(command, cwd=working, capture_output=True)
        assert failed.returncode == expected and failed.stderr, failed
        if expected == 13:
            assert b"corboc: package is not a direct dependency: leaf\n" in failed.stderr, failed
        assert output.read_bytes() == original

    main.write_text("fn main() { print(leaf::value()); }")
    manifest.write_text(baseline + 'leaf = { path = "../leaf" }\n')
    direct = working / "with-direct-leaf"
    run([compiler, "build", root, "-o", direct], cwd=working)
    assert run([direct], cwd=working, capture_output=True).stdout == b"45\n"
    main.write_text(program)
    manifest.write_text(baseline)
    leaf_manifest = leaf.read_text()
    leaf.write_text(leaf_manifest + '[dependencies]\napp = { path = "../dependency project" }\n')
    failed = subprocess.run(command, cwd=working, capture_output=True)
    assert failed.returncode == 16 and output.read_bytes() == original, failed
    leaf.write_text(leaf_manifest)

    (remote / "escape").symlink_to(directory / "leaf", target_is_directory=True)
    pinned.write_text(pinned.read_text() + 'leaf = { path = "escape" }\n')
    escape = commit(remote, "path escaping the checkout")
    manifest.write_text(baseline.replace(pin.upper(), escape))
    failed = subprocess.run(command, cwd=working, capture_output=True)
    assert failed.returncode == 20 and output.read_bytes() == original, failed
    assert not list(working.glob(".corboc.*"))
    print("Direct and transitive path dependencies and the pinned Git commit matched Rust; nine refusals passed", flush=True)


def check_slice_mutability(compiler, directory):
    source = directory / "slices.crb"
    reborrow = (
        "struct Cell { value: i64 }\n"
        "fn take(values: &mut [Cell]) { drop(values); }\n"
        "fn pass(values: &mut [Cell]) { take(&mut values[0..values.len()]); }\n"
        "fn main() {}\n"
    )
    source.write_text(reborrow)
    run([FRONTEND, "check"], input=reborrow.encode())
    result = subprocess.run([compiler, "--verify", source], capture_output=True)
    # Keep the projection check separate from the unfinished slice dataflow.
    assert result.returncode in (0, 9), result

    shared = "fn write(mut view: &[i64]) { view[0] = 42; }\nfn main() {}\n"
    source.write_text(shared)
    reference = subprocess.run([FRONTEND, "check"], input=shared.encode(),
                               capture_output=True)
    assert reference.returncode != 0, reference
    result = subprocess.run([compiler, "--verify", source], capture_output=True)
    assert result.returncode == 8 and result.stdout.startswith(b"5\n"), result

    structural = b"""struct Cell { value: i64 }
fn write(cells: &mut [Cell]) { cells[0] = Cell { value: 42 }; }
fn update(cells: &mut [Cell]) -> i64 {
    write(&mut cells[1..cells.len()]);
    cells[1].value
}
fn main() {
    let mut cells: [Cell; 3] = [Cell { value: 0 }; 3];
    print(update(&mut cells[..]));
    print(cells[1].value);
}
"""
    source.write_bytes(structural)
    reference = directory / "slice-rust"
    run([FRONTEND, "build", "-o", reference], input=structural)
    expected = run([reference], capture_output=True)
    assert (expected.stdout, expected.stderr) == (b"42\n42\n", b"")
    generated = directory / "slice.c"
    with generated.open("wb") as output:
        run([compiler, "--emit-c", source], stdout=output)
    candidate = directory / "slice-ubsan"
    compile_c(generated, candidate, ubsan=True)
    result = run([candidate], capture_output=True)
    assert (result.stdout, result.stderr) == (expected.stdout, expected.stderr)


def check_result(compiler, directory):
    source = directory / "result.crb"
    program = b"""enum Failure { Missing, Invalid { code: i64 } }
fn failure() -> Failure { Failure.Invalid { code: 17 } }
fn unit() -> Result<(), Failure> { Ok(()) }
fn calculate(success: bool) -> Result<i64, Failure> {
    if !success { return Err(failure()); }
    Ok(42)
}
fn forward(value: Result<i64, Failure>) -> Result<i64, Failure> { value }
fn inspect(success: bool) {
    let result = calculate(success);
    match forward(result) {
        Ok(value) => { print(value); },
        Err(error) => {
            match error {
                Failure.Missing => { print(0); },
                Failure.Invalid { code: code } => { print(code); },
            };
        },
    };
}
fn main() {
    inspect(true);
    inspect(false);
    match unit() { Ok(()) => { print(1); }, Err(_) => {}, };
}
"""
    source.write_bytes(program)
    reference = directory / "result-rust"
    run([FRONTEND, "build", "-o", reference], input=program)
    expected = run([reference], capture_output=True)
    assert (expected.stdout, expected.stderr) == (b"42\n17\n1\n", b"")
    generated = directory / "result.c"
    with generated.open("wb") as output:
        run([compiler, "--emit-c", source], stdout=output)
    for ubsan in (False, True):
        candidate = directory / ("result-ubsan" if ubsan else "result-native")
        compile_c(generated, candidate, ubsan)
        actual = run([candidate], capture_output=True)
        assert (actual.stdout, actual.stderr) == (expected.stdout, expected.stderr)
    for case in (
        program.replace(b"Ok(42)", b"Ok(true)"),
        program.replace(b"match forward(result)", b"forward(result); match forward(result)"),
        program.replace(b"Err(_) => {},", b""),
    ):
        source.write_bytes(case)
        rust = subprocess.run([FRONTEND, "check"], input=case, capture_output=True)
        crust = subprocess.run([compiler, "--verify", source], capture_output=True)
        assert rust.returncode != 0 and crust.returncode == 8, (rust, crust)
    print("Result constructors, forwarding, and match agreed with Rust", flush=True)


def check_scalar_options(compiler, directory):
    source = directory / "scalar_option.crb"
    generated = directory / "scalar_option.c"
    program = b"""fn forward(value: Option<i32>) -> Option<i32> { value }
fn number(value: Option<i32>) -> i32 {
    let value = forward(value);
    let n = match value { Some(n) => { n }, None => { return 42; }, };
    n
}
fn limit(value: Option<i32>) -> i32 {
    let limit = match value { Some(n) => { n }, None => { 2147483647 }, };
    limit
}
fn main() {
    let signed: i32 = -7;
    let backlog: Option<i32> = Some(signed);
    print(number(backlog));
    print(number(None));
    print(limit(None));
}
"""
    source.write_bytes(program)
    with generated.open("wb") as output:
        run([compiler, "--emit-c", source], stdout=output)
    for ubsan in (False, True):
        candidate = directory / ("option-ubsan" if ubsan else "option-native")
        compile_c(generated, candidate, ubsan)
        actual = run([candidate], capture_output=True)
        assert (actual.stdout, actual.stderr) == (b"-7\n42\n2147483647\n", b"")
    for case in (
        program.replace(b"Some(signed)", b"Some(true)"),
        program.replace(b"print(number(None));", b"print(number(backlog));"),
        program.replace(b", None => { return 42; }", b""),
    ):
        source.write_bytes(case)
        rust = subprocess.run([FRONTEND, "check"], input=case, capture_output=True)
        crust = subprocess.run([compiler, "--verify", source], capture_output=True)
        assert rust.returncode != 0 and crust.returncode == 8, (rust, crust)
    print("Scalar Option arguments, returns and match passed with three refusals", flush=True)


def check_result_destruction(compiler, directory):
    program = b"""struct Resource { value: i64 }
impl Resource {
    fn drop(&mut self) { print((*self).value); }
}
fn start(value: i64) -> Result<Resource, Resource> {
    if value < 0 { return Err(Resource { value: value }); }
    Ok(Resource { value: value })
}
fn forward(result: Result<Resource, Resource>) -> Result<Resource, Resource> { result }
fn process() {
    let result = start(10);
    let moved = forward(result);
    match moved {
        Ok(resource) => { print(5); drop(resource); },
        Err(_) => {},
    };
    match start(16) {
        Ok(_) => { print(6); },
        Err(_) => {},
    };
    let unused = start(-22);
}
fn main() { process(); }
"""
    source = directory / "owned-result.crb"
    source.write_bytes(program)
    reference = directory / "owned-result-rust"
    run([FRONTEND, "build", "-o", reference], input=program)
    expected = run([reference], capture_output=True)
    assert (expected.stdout, expected.stderr) == (b"5\n10\n16\n6\n-22\n", b"")
    generated = directory / "owned-result.c"
    with generated.open("wb") as output:
        run([compiler, "--emit-c", source], stdout=output)
    for ubsan in (False, True):
        candidate = directory / ("owned-result-ubsan" if ubsan else "owned-result-native")
        compile_c(generated, candidate, ubsan)
        actual = run([candidate], capture_output=True)
        assert (actual.stdout, actual.stderr) == (expected.stdout, expected.stderr)
    print("Owned result payloads were destroyed once after forwarding, match, and scope exit", flush=True)


def check_async_results(compiler, directory):
    program = b"""struct Resource { value: i64 }
impl Resource {
    fn drop(&mut self) { print((*self).value); }
}

async fn owned(value: i64) -> Result<Resource, Resource> {
    if value < 0 { return Err(Resource { value: value }); }
    Ok(Resource { value: value })
}

async fn operation(success: bool) -> Result<u64, i64> {
    yield;
    if success { return Ok(42); }
    Err(-7)
}

async fn caller() {
    let first = operation(true).await;
    match first {
        Ok(value) => { print(value); },
        Err(error) => { print(error); },
    };
    let worker = runtime::spawn_blocking(operation(false));
    let completion = worker.await;
    match completion {
        Ok(result) => { match result {
            Ok(value) => { print(value); },
            Err(error) => { print(error); },
        }; },
        Err(error) => { drop(error); print(-100); },
    };
    drop(owned(10).await);
    let worker = runtime::spawn_blocking(owned(-20));
    drop(worker.await);
}

fn main() {
    let task = runtime::spawn(caller());
    drop(task.join());
    let worker = runtime::spawn(operation(true));
    match worker.join() {
        Ok(result) => { match result {
            Ok(value) => { print(value); },
            Err(error) => { print(error); },
        }; },
        Err(error) => { drop(error); print(-101); },
    };
    let worker = runtime::spawn(owned(30));
    drop(worker.join());
}
"""
    source = directory / "async-results.crb"
    source.write_bytes(program)
    reference = directory / "async-results-rust"
    run([FRONTEND, "build", "-o", reference], input=program)
    expected = run([reference], capture_output=True)
    assert (expected.stdout, expected.stderr) == (b"42\n-7\n10\n-20\n42\n30\n", b"")
    generated = directory / "async-results.c"
    with generated.open("wb") as output:
        run([compiler, "--emit-c", source], stdout=output)
    for ubsan in (False, True):
        candidate = directory / ("async-results-ubsan" if ubsan else "async-results-native")
        compile_c(generated, candidate, ubsan)
        actual = run([candidate], capture_output=True)
        assert (actual.stdout, actual.stderr) == (expected.stdout, expected.stderr)
    bad = program.replace(b"return Ok(42);", b"return Ok(true);")
    source.write_bytes(bad)
    rust = subprocess.run([FRONTEND, "check"], input=bad, capture_output=True)
    crust = subprocess.run([compiler, "--verify", source], capture_output=True)
    assert rust.returncode != 0 and crust.returncode == 8, (rust, crust)
    print("Async Result awaits, joins, and owned payload cleanup matched Rust", flush=True)


def check_internal_expressions(compiler, directory):
    program = b"""struct Item { value: i64 }
fn number(item: &Item) -> i64 { (*item).value }
fn twice(item: &Item) -> i64 { number(item) + number(item) }
fn first(items: &[Item]) -> i64 { twice(&items[0]) }
fn print_number(value: u64) { print(value); }
fn nonzero(value: u8) -> bool { value != 0 }
fn count(source: &[u8]) -> usize {
    let mut at: usize = 0;
    while at < source.len() && nonzero(source[at]) { at = at + 1; }
    at
}
fn positions(flag: bool, first: u64, second: u64) {
    let (x, y) = if flag { (first, second) } else { (second, first) };
    print_number(if flag { 0 } else { x });
    print(y);
}
fn calculation(flag: bool, valid: bool) -> i64 {
    let count = if flag { if !valid { return -9; } 9 } else { 0 };
    count
}
fn reuse(flag: bool) -> u64 {
    let mut value: u64 = 0;
    if flag {
        let item = Counter { prior: value };
        value = item.prior + 1;
    }
    value
}
struct Counter { prior: u64 }
fn pair(flag: bool) -> (i64, bool) {
    let value = if flag { return (6, true); } else { 7 };
    (value, false)
}
fn select_pair(values: &mut [i64], flag: bool) -> (i64, bool) {
    values[0] = 21;
    (values[0], flag)
}
fn statement_loop(stop: u64) -> bool {
    let mut current: u64 = 0;
    loop {
        if current == stop { return true; }
        current = current + 1;
    }
    false
}
fn nested(outer: bool, inner: bool, value: u64) -> u64 {
    let number = if outer {
        let selected = if inner { value } else { 0 };
        selected + 1
    } else { 0 };
    number
}
fn main() {
    let row = [Item { value: 21 }; 2];
    print(first(&row[..]));
    positions(true, 1, 2);
    positions(false, 1, 2);
    print(calculation(true, false));
    print(calculation(true, true));
    let bytes: [u8; 3] = [9, 5, 0];
    print(count(&bytes[..]));
    print(reuse(false));
    print(reuse(true));
    let (a, b) = pair(true);
    print(a); print(b);
    let (x, y) = pair(false);
    print(x); print(y);
    let mut values: [i64; 1] = [0];
    let (selected, flag) = if x > 2 {
        select_pair(&mut values[..], true)
    } else {
        select_pair(&mut values[..], false)
    };
    print(selected); print(flag); print(values[0]);
    print(statement_loop(2));
    print(nested(true, true, 8));
    print(nested(true, false, 8));
    print(nested(false, false, 8));
    let mut seen = [false; 524289];
    seen[524288] = true;
    print(seen[0]);
    print(seen[524288]);
}
"""
    reference = directory / "expressions-rust"
    run([FRONTEND, "build", "-o", reference], input=program)
    expected = run([reference], capture_output=True)
    assert (expected.stdout, expected.stderr) == (
        b"42\n0\n2\n2\n1\n-9\n9\n2\n0\n1\n6\ntrue\n7\nfalse\n21\ntrue\n21\ntrue\n9\n1\n0\nfalse\ntrue\n", b""
    )
    source = directory / "expressions.crb"
    source.write_bytes(program)
    generated = directory / "expressions.c"
    with generated.open("wb") as output:
        run([compiler, "--emit-c", source], stdout=output)
    for ubsan in (False, True):
        candidate = directory / ("expressions-ubsan" if ubsan else "expressions-native")
        compile_c(generated, candidate, ubsan)
        actual = run([candidate], capture_output=True)
        assert (actual.stdout, actual.stderr) == (expected.stdout, expected.stderr)
    for case in (
        program.replace(b"print(y);", b"print(x); print(y);"),
        program.replace(b"(first, second)", b"(first, first)"),
        program.replace(b"twice(&items[0])", b"twice(&items[0].value)"),
        program.replace(b"return -9;", b"return false;"),
    ):
        source.write_bytes(case)
        rust = subprocess.run([FRONTEND, "check"], input=case, capture_output=True)
        crust = subprocess.run([compiler, "--verify", source], capture_output=True)
        assert rust.returncode != 0 and crust.returncode == 8, (rust, crust)
    print("Conditional moves and shared record arguments agreed with Rust", flush=True)


def check_value_receivers(compiler, directory):
    source = directory / "value-receiver.crb"
    structure = """struct Packet { bytes: u8 }
    impl Packet {
        fn read(self: Packet, extra: u8) -> u8 { self.bytes + extra }
        fn close(self: Packet) {}
        fn keep(self: Packet) -> Packet { self }
        fn drop(&mut self) { print((*self).bytes); }
    }
    """
    array_structure = """struct Frame { bytes: [u8; 2], id: u8 }
    enum Failure { Empty }
    impl Frame {
        fn finish(mut self: Frame) -> [u8; 2] {
            let first = &mut self.bytes[0];
            *first = 42;
            let output: [u8; 2] = [self.bytes[0], self.bytes[1]];
            output
        }
        fn drop(&mut self) { print((*self).id); }
    }
    fn take(frame: Frame) -> Result<[u8; 2], Failure> { Ok(frame.finish()) }
    fn empty() -> Result<[u16; 3], Failure> { Err(Failure.Empty) }
    """
    frame = "let frame = Frame { bytes: [0; 2], id: 11 };"
    cases = (
        (structure, "let packet = Packet { bytes: 40 }; print(packet.read(2));"
         "let second = Packet { bytes: 5 }; let kept: Packet = second.keep();"
         "print(6); kept.close();", b"40\n42\n6\n5\n"),
        (structure, "let packet = Packet { bytes: 40 }; print(packet.read(2)); print(packet.bytes);", None),
        (structure, "let packet = Packet { bytes: 40 }; let view = &packet; print(view.read(2));", None),
        (structure, "let packet = Packet { bytes: 40 }; let view = &packet;"
         "print(packet.read(2)); print((*view).bytes);", None),
        (structure, "let packet = Packet { bytes: 40 }; print(packet.read(packet.bytes));", None),
        (structure, "let mut packet = Packet { bytes: 40 }; packet.drop();", None),
        (array_structure, frame +
         "match take(frame) { Ok(bytes) => { print(bytes[0]); }, Err(_) => {}, };"
         "match empty() { Ok(bytes) => { print(bytes[0]); }, Err(_) => { print(0); }, };", b"11\n42\n0\n"),
        (array_structure, frame + "drop(frame.finish()); print(frame.id);", None),
        (array_structure, frame + "let view = &frame; drop(frame.finish()); print((*view).id);", None),
        (array_structure.replace("-> [u8; 2]", "-> [u8; 1]"), frame + "drop(frame.finish());", None),
    )
    for declarations, body, expected in cases:
        text = declarations + "fn main() { " + body + " }"
        source.write_text(text)
        for name, command in (
            ("rust", [FRONTEND, "emit-c"]),
            ("crust", [compiler, "--emit-c", source]),
        ):
            emitted = subprocess.run(command, input=text.encode(), capture_output=True)
            if expected is None:
                assert (emitted.returncode == 8 if name == "crust" else emitted.returncode != 0), (name, body, emitted)
                continue
            assert emitted.returncode == 0, (name, body, emitted)
            generated = directory / f"value-receiver-{name}.c"
            generated.write_bytes(emitted.stdout)
            binary = directory / f"value-receiver-{name}"
            compile_c(generated, binary, ubsan=True)
            executed = run([binary], capture_output=True)
            assert (executed.stdout, executed.stderr) == (expected, b""), executed
    print("Value receivers moved and ran their destructors once in both compilers under UBSan", flush=True)


def check_positional_variants(compiler, directory):
    package = directory / "positional-variants"
    kinds = package / "src/kinds"
    kinds.mkdir(parents=True)
    (package / "package.toml").write_text('[package]\nname = "positional"\n')
    (kinds / "kinds.crb").write_text(
        "pub enum Settings { DefaultMode, Pair(u32, i64), Named { number: i64 } }\n"
    )
    source = package / "src/main.crb"
    valid = """use positional::kinds::Settings as Value;
fn first() -> u32 { print(10); 42 }
fn second() -> i64 { print(20); -7 }
fn main() {
    let options = Value.Pair(first(), second());
    match options {
        Value.DefaultMode => { print(0); },
        Value.Pair(a, b) => { print(a); print(b); },
        Value.Named { number: number } => { print(number); },
    };
}
"""
    source.write_text(valid)
    generated = directory / "positional.c"
    crust = directory / "positional-crust"
    rust = directory / "positional-rust"
    run([FRONTEND, "build", package, "-o", rust])
    emit(compiler, package, generated, ROOT / "stdlib" / "src")
    compile_c(generated, crust, ubsan=True)
    for binary in (rust, crust):
        assert run([binary], capture_output=True).stdout == b"10\n20\n42\n-7\n"

    for old, new in [
        ("Pair(first(), second())", "Pair(first())"),
        ("Pair(first(), second())", "Pair(second(), first())"),
        ("Pair(a, b) => { print(a); print(b); }", "Pair(a) => { print(a); }"),
        ("Pair(a, b) => { print(a); print(b); }", "Pair { a: a, b: b } => { print(a); print(b); }"),
    ]:
        source.write_text(valid.replace(old, new))
        want = subprocess.run([FRONTEND, "check", package], capture_output=True)
        got = subprocess.run([compiler, "--emit-package-c", package,
                              "--stdlib-dir", ROOT / "stdlib" / "src"], capture_output=True)
        assert want.returncode != 0 and got.returncode == 8, (new, want, got)
    print("Positional variants matched Rust for construction order, destructuring and four refusals", flush=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--bootstrap", type=Path)
    cli.add_argument("--self-host", action="store_true")
    cli.add_argument("--rebuild", action="store_true", help="rebuild the compiler using corboc build")
    args = cli.parse_args()
    with tempfile.TemporaryDirectory(prefix="corboc-package-") as temporary:
        directory = Path(temporary)
        compiler = args.bootstrap.resolve() if args.bootstrap else directory / "corboc-stage1"
        if args.bootstrap is None:
            run([FRONTEND, "build", PACKAGE, "-o", compiler])
        try:
            check_package(compiler, directory)
            check_constants(compiler, directory)
            check_process_arguments(compiler, directory)
            check_package_file(compiler, directory)
            check_file_operations(compiler, directory)
            check_positional_variants(compiler, directory)
            check_slice_mutability(compiler, directory)
            check_result(compiler, directory)
            check_scalar_options(compiler, directory)
            check_result_destruction(compiler, directory)
            check_async_results(compiler, directory)
            check_internal_expressions(compiler, directory)
            check_value_receivers(compiler, directory)
            check_large_destructor(compiler, directory)
            if sys.platform == "darwin" and platform.machine() == "arm64":
                check_build(compiler, directory, args.rebuild)
            elif args.rebuild:
                cli.exit(1, "--rebuild requires the macOS ARM64 build driver\n")
            if args.self_host:
                check_self_host(compiler, directory)
        except RuntimeError as error:
            cli.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
