#!/usr/bin/env python3
"""Check caller-buffered custom, file and TCP streams with either compiler."""

import argparse
from pathlib import Path
import re
import socket
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"
STDLIB = ROOT / "stdlib/src"
IMPORTS = """
use std::io::buffered::{BufReader, BufWriter, BufferedError};
use std::io::{File, FileError};
use std::io::{FileMode, SeekFrom};

fn count_is(result: Result<usize, BufferedError<FileError>>, expected: usize) -> bool {
    match result {
        Ok(count) => { count == expected },
        Err(error) => { drop(error); false },
    }
}
"""
FILE = IMPORTS + """
fn main() -> i32 {
    let path: [u8; 5] = [100, 97, 116, 97, 0];
    let mut file = match File::open(&path[..], FileMode::READ_WRITE) {
        Ok(handle) => { handle }, Err(error) => { drop(error); return 1; },
    };
    let mut scratch: [u8; 4] = [0; 4];
    let mut empty: [u8; 0] = [];
    let data: [u8; 6] = [10, 20, 30, 40, 50, 60];
    let bytes = &data[..];
    {
        let mut writer = BufWriter::new(&mut file, &mut scratch[..]);
        if !count_is(writer.write(&empty[..]), 0) { return 2; }
        if !count_is(writer.write(&bytes[0..6]), 4) { return 3; }
        if !count_is(writer.write(&bytes[4..6]), 2) { return 4; }
        match writer.flush() {
            Ok(()) => {}, Err(error) => { drop(error); return 5; },
        }
        if !count_is(writer.write(&bytes[0..1]), 1) { return 6; }
    }
    match file.seek(SeekFrom.Start(0)) {
        Ok(pos) => { if pos != 0 { return 7; } },
        Err(error) => { drop(error); return 8; },
    }
    let mut out: [u8; 2] = [0; 2];
    {
        let mut reader = BufReader::new(&mut file, &mut scratch[..]);
        if !count_is(reader.read(&mut empty[..]), 0) { return 9; }
        if !count_is(reader.read(&mut out[..1]), 1) || out[0] != 10 || out[1] != 0 { return 10; }
        if !count_is(reader.read(&mut out[..1]), 1) || out[0] != 20 { return 11; }
    }
    {
        let mut reader = BufReader::new(&mut file, &mut empty[..]);
        if !count_is(reader.read(&mut out[..]), 2) { return 12; }
        if out[0] != 50 || out[1] != 60 { return 13; }
        if !count_is(reader.read(&mut out[..]), 0) { return 14; }
    }
    {
        let mut writer = BufWriter::new(&mut file, &mut empty[..]);
        if !count_is(writer.write(&bytes[0..1]), 1) { return 15; }
    }
    let mut readonly = match File::open(&path[..], FileMode::READ_ONLY) {
        Ok(handle) => { handle }, Err(error) => { drop(error); return 16; },
    };
    let mut writer = BufWriter::new(&mut readonly, &mut scratch[..]);
    if !count_is(writer.write(&bytes[0..4]), 4) { return 17; }
    match writer.flush() {
        Ok(()) => { return 18; },
        Err(error) => { match error {
            BufferedError.Stream { error: _ } => {},
            BufferedError.WriteZero => { return 20; },
        } },
    }
    match writer.write(&bytes[4..6]) {
        Ok(n) => { drop(n); return 21; },
        Err(error) => { drop(error); },
    }
    0
}
"""
TCP = "use std::net::ipv4::from_parts;\nuse std::net::tcp::connect;\n" + IMPORTS + """
fn main() -> i32 {
    let mut conn = match connect(from_parts(0x7f000001, TEST_PORT)) {
        Ok(value) => { value }, Err(error) => { drop(error); return 1; },
    };
    let mut scratch: [u8; 4] = [0; 4];
    let mut output: [u8; 1] = [0];
    {
        let mut reader = BufReader::from_tcp(&mut conn, &mut scratch[..]);
        if !count_is(reader.read(&mut output[..]), 1) || output[0] != 97 { return 2; }
        if !count_is(reader.read(&mut output[..]), 1) || output[0] != 98 { return 3; }
        if !count_is(reader.read(&mut output[..]), 0) { return 4; }
    }
    let mut writer = BufWriter::from_tcp(&mut conn, &mut scratch[..]);
    let response: [u8; 2] = [79, 75];
    if !count_is(writer.write(&response[..]), 2) { return 5; }
    match writer.flush() {
        Ok(()) => { 0 }, Err(error) => { drop(error); 6 },
    }
}
"""
MEMORY = """
use std::io::buffered::{BufReader, BufWriter, BufferedError};
struct Memory { value: u8 }
impl Memory {
    fn read(&mut self, buffer: &mut [u8]) -> Result<usize, bool> {
        buffer[0] = (*self).value;
        Ok(1)
    }
    fn write(&mut self, input: &[u8]) -> Result<usize, bool> {
        drop(input);
        Err(true)
    }
}
struct Zero {}
impl Zero {
    fn write(&mut self, input: &[u8]) -> Result<usize, bool> {
        drop(input);
        Ok(0)
    }
}
fn main() -> i32 {
    let mut memory = Memory { value: 9 };
    let mut scratch: [u8; 4] = [0; 4];
    let mut output: [u8; 1] = [0];
    {
        let mut reader = BufReader::new(&mut memory, &mut scratch[..]);
        match reader.read(&mut output[..]) { Ok(count) => { drop(count); }, Err(error) => { drop(error); } }
    }
    print(output[0]);
    {
        let mut writer = BufWriter::new(&mut memory, &mut scratch[..]);
        match writer.write(&output[..]) { Ok(count) => { drop(count); }, Err(error) => { drop(error); } }
        match writer.flush() {
            Ok(()) => {},
            Err(error) => { match error {
                BufferedError.Stream { error: inner } => { print(inner); },
                BufferedError.WriteZero => { print(false); },
            } },
        }
    }
    let mut zero = Zero {};
    let mut writer = BufWriter::new(&mut zero, &mut scratch[..]);
    match writer.write(&output[..]) { Ok(count) => { drop(count); }, Err(error) => { drop(error); } }
    match writer.flush() {
        Ok(()) => {},
        Err(error) => { match error {
            BufferedError.Stream { error: inner } => { print(inner); },
            BufferedError.WriteZero => { print(42); },
        } },
    }
    0
}
"""

STORED = """
struct Holder { bytes: &mut [u8] }
fn main() {
    let mut data: [u8; 4] = [0; 4];
    let mut holder = Holder { bytes: &mut data[..] };
    FIRST
    SECOND
}
"""
ACTIVE_READER = IMPORTS + """
fn main() -> i32 {
    let path: [u8; 5] = [100, 97, 116, 97, 0];
    let mut file = match File::open(&path[..], FileMode::READ_ONLY) {
        Ok(handle) => { handle }, Err(error) => { drop(error); return 1; },
    };
    let mut scratch: [u8; 4] = [0; 4];
    let mut out: [u8; 1] = [0];
    let mut reader = BufReader::new(&mut file, &mut scratch[..]);
    REUSE
    if !count_is(reader.read(&mut out[..]), 1) { return 2; }
    0
}
"""
REFUSALS = (
    STORED.replace("FIRST", "let first = &mut *holder.bytes;").replace(
        "SECOND", "let second = &mut *holder.bytes; first[0] = 1; second[0] = 2;"
    ),
    STORED.replace("FIRST", "let moved = holder.bytes;").replace("SECOND", "print(moved[0]);"),
    STORED.replace("FIRST", "let first = &mut *holder.bytes;").replace(
        "SECOND", "drop(holder); first[0] = 42;"
    ),
    ACTIVE_READER.replace("REUSE", "scratch[0] = 42;"),
    ACTIVE_READER.replace(
        "REUSE",
        "match file.seek(SeekFrom.Start(0)) { Ok(n) => { drop(n); }, Err(e) => { drop(e); } }",
    ),
)
SLICE_RESULT = """
struct Holder { bytes: &mut [u8], tag: i64 }
fn hold(bytes: &mut [u8]) -> Holder { Holder { bytes: bytes, tag: 7 } }
fn main() {
    let mut left: [u8; 2] = [0; 2];
    let mut right: [u8; 2] = [0; 2];
    {
        let mut first = hold(&mut left[..]);
        let mut second = hold(&mut right[..]);
        ACCESS
        let a = &mut *first.bytes;
        a[0] = 42;
        left[1] = 11;
        let b = &mut *second.bytes;
        b[0] = 23;
    }
    print(left[0]);
    print(left[1]);
    print(right[0]);
}
"""

MULTIPLE_SLICE_FIELDS = """
struct Views { left: &mut [u8], right: &mut [u8] }
fn views(left: &mut [u8], right: &mut [u8]) -> Views {
    Views { right: right, left: left }
}
fn main() {
    let mut left: [u8; 2] = [0; 2];
    let mut right: [u8; 2] = [0; 2];
    {
        let initial = views(&mut left[..], &mut RIGHT[..]);
        let mut result = initial;
        BEFORE_LEFT
        let first = &mut *result.left;
        first[0] = 42;
        left[1] = 11;
        BEFORE_RIGHT
        let second = &mut *result.right;
        second[0] = 23;
    }
    print(left[0]);
    print(left[1]);
    print(right[0]);
}
"""

ESCAPING_SLICE = """
struct Holder { bytes: &mut [u8] }
fn invalid() -> Holder {
    let mut scratch: [u8; 2] = [0; 2];
    Holder { bytes: &mut scratch[..] }
}
fn main() {}
"""


def source(root, text):
    (root / "src/main.crb").write_text(text)


def asynchronous(program):
    tcp = "TEST_PORT" in program
    program = program.replace("std::io::buffered", "std::io::asyn::buffered")
    program = program.replace("use std::io::{File, FileError};\nuse std::io::{FileMode, SeekFrom};",
                              "use std::io::{FileMode, SeekFrom};\nuse std::io::asyn::{File, FileError};")
    program = program.replace("std::net::tcp", "std::net::asyn::tcp")
    program = program.replace("File::open(&path[..], FileMode::READ_WRITE)",
                              "File::open(&path[..], FileMode::READ_WRITE).await")
    program = program.replace("File::open(&path[..], FileMode::READ_ONLY)",
                              "File::open(&path[..], FileMode::READ_ONLY).await")
    if tcp:
        program = program.replace("connect(from_parts(0x7f000001, TEST_PORT))", "connect(address).await")
        program = "use std::net::ipv4::SocketAddr;\n" + program
    program = program.replace("file.seek(SeekFrom.Start(0))", "file.seek(SeekFrom.Start(0)).await")
    program = re.sub(r"\b(reader|writer)\.(read|write|flush)\([^()]*\)", r"\g<0>.await", program)
    program = re.sub(r"\bBuf(Reader|Writer)::(new|from_tcp)\([^()]*\)", r"\g<0>.await", program)
    program = re.sub(
        r"count_is\(((?:reader|writer)\.[^(]+\([^()]*\)\.await), ([0-9]+)\)",
        r"(match \1 { Ok(count) => { count == \2 }, Err(error) => { drop(error); false }, })",
        program,
    )
    # Keep each awaited result match as a statement before its boolean test.
    # This exercises buffering independently of match expressions nested in !/||.
    check_index = 0
    def lift_count(match):
        nonlocal check_index
        check_index += 1
        return f"let count_check_{check_index} = {match.group(1)};\n        if !count_check_{check_index}"
    program = re.sub(r"if !\((match [^\n]*?, \})\)", lift_count, program)
    parameter = "address: SocketAddr" if tcp else ""
    argument = "from_parts(0x7f000001, TEST_PORT)" if tcp else ""
    return program.replace("fn main() -> i32", f"async fn probe({parameter}) -> i32") + """
fn main() -> i32 {
    let handle = runtime::spawn(probe(PROBE_ARGUMENT));
    match handle.join() {
        Ok(status) => { status }, Err(error) => { drop(error); 99 },
    }
}
""".replace("PROBE_ARGUMENT", argument)


def compile_c(root, text, optimization, corboc=None):
    source(root, text)
    command = [FRONTEND, "emit-c", root] if corboc is None else [
        corboc, "--emit-package-c", root, "--stdlib-dir", STDLIB
    ]
    generated = subprocess.check_output(command)
    c_path = root / "probe.c"
    c_path.write_bytes(generated)
    binary = root / "probe"
    subprocess.run(
        ["cc", "-std=c11", "-pthread", optimization, "-fsanitize=undefined",
         "-fno-sanitize-recover=all", c_path, "-lm", "-o", binary],
        check=True, cwd=root,
    )
    return binary


def test_memory(root, run_async, corboc):
    program = MEMORY
    if run_async:
        program = program.replace("fn read(&mut self", "async fn read(&mut self")
        program = program.replace("fn write(&mut self", "async fn write(&mut self")
        program = program.replace("        buffer[0]", "        yield;\n        buffer[0]")
        program = asynchronous(program)
    for optimization in ("-O0", "-O2"):
        binary = compile_c(root, program, optimization, corboc)
        assert subprocess.check_output([binary], cwd=root, timeout=10) == b"9\ntrue\n42\n"
    print("Custom streams preserve bool errors and report WriteZero")


def test_file(root, run_async, corboc):
    data = root / "data"
    program = asynchronous(FILE) if run_async else FILE
    for optimization in ("-O0", "-O2"):
        data.write_bytes(b"")
        binary = compile_c(root, program, optimization, corboc)
        subprocess.run([binary], check=True, cwd=root, timeout=10)
        assert data.read_bytes() == bytes((10, 20, 30, 40, 50, 60, 10))

    # N5 permits a sequential scratch-buffer write before the reader runs.
    # Other refusals include lifetime errors and conservative coverage limits.
    if corboc:
        binary = compile_c(root, REFUSALS[3], "-O1", corboc)
        subprocess.run([binary], check=True, cwd=root, timeout=10)
    refusals = REFUSALS[:3] + REFUSALS[4:] if corboc else REFUSALS
    if run_async:
        for reuse in ("out[0] = 2;", "scratch[0] = 2;", "drop(reader);"):
            pending = ACTIVE_READER.replace(
                "REUSE",
                "let pending = reader.read(&mut out[..]); " + reuse,
            ).replace(
                "if !count_is(reader.read(&mut out[..]), 1) { return 2; }",
                "match pending.await { Ok(n) => { drop(n); }, Err(e) => { drop(e); } }",
            )
            program = asynchronous(pending).replace(
                "reader.read(&mut out[..]).await;", "reader.read(&mut out[..]);"
            )
            if corboc and reuse != "drop(reader);":
                # The Future is inactive until await; these sequential writes
                # do not overlap its execution. The reader must still survive.
                binary = compile_c(root, program, "-O1", corboc)
                subprocess.run([binary], check=True, cwd=root, timeout=10)
            else:
                refusals += (program,)
    for program in refusals:
        source(root, program)
        assert_borrow_refused(root, corboc)
    print(f"File buffering and {len(refusals)} borrow refusals passed")


def test_tcp(root, run_async, corboc):
    base = TCP.replace("BufferedError<FileError>", "BufferedError<SocketError>")
    base = "use std::net::SocketError;\n" + base
    program = asynchronous(base) if run_async else base
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(10)
        for optimization in ("-O0", "-O2"):
            binary = compile_c(root, program.replace("TEST_PORT", str(listener.getsockname()[1])),
                               optimization, corboc)
            with subprocess.Popen([binary], cwd=root) as client:
                try:
                    connection, _ = listener.accept()
                    with connection:
                        connection.settimeout(10)
                        connection.sendall(b"ab")
                        connection.shutdown(socket.SHUT_WR)
                        response = bytearray()
                        while chunk := connection.recv(16):
                            response.extend(chunk)
                        assert response == b"OK", response
                    assert client.wait(timeout=10) == 0
                finally:
                    if client.poll() is None:
                        client.kill()
    print("TCP buffered read and flushed response matched the independent peer")


def assert_borrow_refused(root, corboc):
    if corboc is None:
        rejected = subprocess.run([FRONTEND, "check", root], capture_output=True, text=True)
        assert rejected.returncode == 1 and ("emprunt" in rejected.stderr or "cible" in rejected.stderr), rejected
    else:
        entry = root / "src/main.crb"
        command = [corboc, "--emit-package-c", root, "--stdlib-dir", STDLIB] if "use std::" in entry.read_text() else [
            corboc, "--verify", entry
        ]
        rejected = subprocess.run(command, capture_output=True, text=True)
        assert rejected.returncode == 8 and rejected.stdout.splitlines()[:1] in (["4"], ["5"]), rejected


def test_slice_result(root, corboc, run_async):
    program = SLICE_RESULT
    if run_async:
        program = program.replace("fn hold(", "async fn hold(")
        program = program.replace("fn main() {", "fn main() -> i32 {")
        program = program.replace("hold(&mut left[..]);", "hold(&mut left[..]).await;")
        program = program.replace("hold(&mut right[..]);", "hold(&mut right[..]).await;")
        program = program.replace("print(right[0]);", "print(right[0]);\n    0")
        program = asynchronous(program)
    for optimization in ("-O0", "-O2"):
        binary = compile_c(root, program.replace("ACCESS", ""), optimization, corboc)
        assert subprocess.check_output([binary], cwd=root, timeout=10) == b"42\n11\n23\n"
    for refused in (program.replace("ACCESS", "left[0] = 1;"), ESCAPING_SLICE):
        source(root, refused)
        assert_borrow_refused(root, corboc)
    print("Two borrowed-slice results preserve their own provenance and reject escaping loans")



def test_multiple_slice_fields(root, corboc):
    def program(right="right", before_left="", before_right=""):
        return (MULTIPLE_SLICE_FIELDS.replace("BEFORE_LEFT", before_left)
                .replace("BEFORE_RIGHT", before_right).replace("RIGHT", right))

    named_arguments = program().replace(
        "let initial = views(&mut left[..], &mut right[..]);",
        "let left_view = &mut left[..];\n"
        "        let right_view = &mut right[..];\n"
        "        let initial = views(left_view, right_view);",
    )
    escaping_right = program().split("fn main()", 1)[0] + """
fn invalid(left: &mut [u8]) -> Views {
    let mut scratch: [u8; 2] = [0; 2];
    views(left, &mut scratch[..])
}
fn main() {}
"""
    for accepted in (program(), named_arguments):
        for optimization in ("-O0", "-O2"):
            binary = compile_c(root, accepted, optimization, corboc)
            assert subprocess.check_output([binary], cwd=root, timeout=10) == b"42\n11\n23\n"
    for refused in (
        program(before_left="left[0] = 1;"),
        program(before_right="right[0] = 1;"),
        program(right="left"),
        escaping_right,
    ):
        source(root, refused)
        assert_borrow_refused(root, corboc)
    print("Two slice fields retain distinct roots across a move and reject overlapping accesses")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    group = cli.add_mutually_exclusive_group()
    group.add_argument("--tcp", action="store_true", help="run the TCP loopback check instead of File")
    group.add_argument("--memory", action="store_true", help="exercise user-defined streams and their error type")
    group.add_argument("--slice-result", action="store_true", help="check a returned record with a slice")
    cli.add_argument("--async", action="store_true", dest="run_async", help="exercise the async adapters")
    cli.add_argument("--corboc", type=Path, help="use this self-hosted compiler")
    args = cli.parse_args()
    with tempfile.TemporaryDirectory(prefix="corbo-buffered-io-") as work:
        root = Path(work)
        (root / "src").mkdir()
        (root / "package.toml").write_text('[package]\nname = "buffered_probe"\n')
        corboc = args.corboc.resolve() if args.corboc else None
        if args.slice_result:
            test_slice_result(root, corboc, args.run_async)
            if not args.run_async:
                test_multiple_slice_fields(root, corboc)
        elif args.memory:
            test_memory(root, args.run_async, corboc)
        else:
            (test_tcp if args.tcp else test_file)(root, args.run_async, corboc)


if __name__ == "__main__":
    main()
