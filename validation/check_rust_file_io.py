"""Exercise the blocking and async File APIs with real files."""
import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from check_rust_assembly import FRONTEND

OPERATIONS = """
ASYNCfn probe() -> Result<u64, FileError> {
    let path: [u8; 9] = [112, 114, 111, 98, 101, 45, 195, 169, 0];
    let data: [u8; 3] = [65, 66, 67];
    let empty: [u8; 0] = [];
    let mut created = match File::create(&path[..], FileMode::read_write(), FilePerm.DefaultMode)WAIT {
        Ok(file) => { file }, Err(error) => { return Err(error); },
    };
    match File::create(&path[..], FileMode::read_write(), FilePerm.DefaultMode)WAIT {
        Ok(file) => { drop(file); return Ok(101); }, Err(error) => { drop(error); },
    };
    let count = match created.write(&empty[..])WAIT {
        Ok(count) => { count }, Err(error) => { return Err(error); },
    };
    if count != 0 { return Ok(102); }
    let count = match created.write(&data[..])WAIT {
        Ok(count) => { count }, Err(error) => { return Err(error); },
    };
    if count != 3 { return Ok(103); }
    let stats = match created.stats()WAIT {
        Ok(stats) => { stats }, Err(error) => { return Err(error); },
    };
    if stats.size() != 3 { return Ok(104); }
    let position = match created.seek(SeekFrom.Start(1))WAIT {
        Ok(position) => { position }, Err(error) => { return Err(error); },
    };
    if position != 1 { return Ok(122); }
    let position = match created.seek(SeekFrom.Current(1))WAIT {
        Ok(position) => { position }, Err(error) => { return Err(error); },
    };
    if position != 2 { return Ok(123); }
    let position = match created.seek(SeekFrom.End(-2))WAIT {
        Ok(position) => { position }, Err(error) => { return Err(error); },
    };
    if position != 1 { return Ok(124); }
    let mut byte: [u8; 1] = [0; 1];
    let count = match created.read(&mut byte[..])WAIT {
        Ok(count) => { count }, Err(error) => { return Err(error); },
    };
    if count != 1 || byte[0] != 66 { return Ok(125); }
    match created.seek(SeekFrom.Start(-1))WAIT {
        Ok(_) => { return Ok(126); }, Err(error) => { drop(error); },
    };
    match created.seek(SeekFrom.Current(-3))WAIT {
        Ok(_) => { return Ok(127); }, Err(error) => { drop(error); },
    };
    let position = match created.seek(SeekFrom.Start(4294967297))WAIT {
        Ok(position) => { position }, Err(error) => { return Err(error); },
    };
    if position != 4294967297 { return Ok(128); }
    let stats = match created.stats()WAIT {
        Ok(stats) => { stats }, Err(error) => { return Err(error); },
    };
    if stats.size() != 3 { return Ok(129); }
    let moved = created;
    drop(moved);

    let renamed: [u8; 8] = [114, 101, 110, 97, 109, 101, 100, 0];
    match File::create(&renamed[..], FileMode::write_only(), FilePerm.DefaultMode)WAIT {
        Ok(file) => { drop(file); }, Err(error) => { return Err(error); },
    };
    match File::rename(&path[..], &renamed[..])WAIT {
        Ok(()) => {}, Err(error) => { return Err(error); },
    };
    let reopened = match File::open(&renamed[..], FileMode::read_only())WAIT {
        Ok(file) => { file }, Err(error) => { return Err(error); },
    };
    let stats = match reopened.stats()WAIT {
        Ok(stats) => { stats }, Err(error) => { return Err(error); },
    };
    if stats.size() != 3 { return Ok(130); }
    drop(reopened);
    match File::rename(&path[..], &renamed[..])WAIT {
        Ok(()) => { return Ok(131); }, Err(error) => { drop(error); },
    };
    let invalid_name: [u8; 1] = [120];
    match File::rename(&renamed[..], &invalid_name[..])WAIT {
        Ok(()) => { return Ok(132); }, Err(error) => { drop(error); },
    };
    match File::rename(&renamed[..], &path[..])WAIT {
        Ok(()) => {}, Err(error) => { return Err(error); },
    };

    let mut readonly = match File::open(&path[..], FileMode::read_only())WAIT {
        Ok(file) => { file }, Err(error) => { return Err(error); },
    };
    match readonly.write(&data[..])WAIT {
        Ok(_) => { return Ok(105); }, Err(error) => { drop(error); },
    };
    drop(readonly);
    let mut reopened = match File::open(&path[..], FileMode::read_write())WAIT {
        Ok(file) => { file }, Err(error) => { return Err(error); },
    };
    let mut output: [u8; 3] = [0; 3];
    let count = match reopened.read(&mut output[..])WAIT {
        Ok(count) => { count }, Err(error) => { return Err(error); },
    };
    if count != 3 || output[0] != 65 || output[2] != 67 { return Ok(106); }
    let count = match reopened.read(&mut output[..])WAIT {
        Ok(count) => { count }, Err(error) => { return Err(error); },
    };
    if count != 0 { return Ok(107); }
    drop(reopened);
    let mut append = match File::open(&path[..], FileMode::write_only() | FileMode::append())WAIT {
        Ok(file) => { file }, Err(error) => { return Err(error); },
    };
    let count = match append.write(&data[..])WAIT {
        Ok(count) => { count }, Err(error) => { return Err(error); },
    };
    if count != 3 { return Ok(113); }
    let stats = match append.stats()WAIT {
        Ok(stats) => { stats }, Err(error) => { return Err(error); },
    };
    if stats.size() != 6 { return Ok(114); }
    drop(append);
    let truncated = match File::open(&path[..], FileMode::write_only() | FileMode::truncate())WAIT {
        Ok(file) => { file }, Err(error) => { return Err(error); },
    };
    let stats = match truncated.stats()WAIT {
        Ok(stats) => { stats }, Err(error) => { return Err(error); },
    };
    if stats.size() != 0 { return Ok(115); }
    drop(truncated);
    match File::delete(&path[..])WAIT {
        Ok(()) => {}, Err(error) => { return Err(error); },
    };
    match File::open(&path[..], FileMode::read_only())WAIT {
        Ok(file) => { drop(file); return Ok(108); }, Err(error) => { drop(error); },
    };
    match File::delete(&path[..])WAIT {
        Ok(()) => { return Ok(109); }, Err(error) => { drop(error); },
    };
    let invalid: [u8; 3] = [97, 0, 0];
    match File::delete(&invalid[..])WAIT {
        Ok(()) => { return Ok(110); },
        Err(error) => { match error {
            FileError.InvalidPath => {},
            FileError.InvalidOptions => { print(-12); },
            FileError.Os { code: code } => { print(code); return Ok(111); },
            LAUNCH_ERROR
        }; },
    };
    match File::create(&path[..], FileMode::write_only(), FilePerm.Perm(0xffffffff))WAIT {
        Err(error) => { match error {
            FileError.InvalidOptions => {},
            FileError.InvalidPath => { return Ok(116); },
            FileError.Os { code: code } => { print(code); return Ok(116); },
            LAUNCH_ERROR
        }; },
        Ok(file) => { drop(file); return Ok(117); },
    };
    let ordinary: [u8; 9] = [111, 114, 100, 105, 110, 97, 114, 121, 0];
    let private: [u8; 8] = [112, 114, 105, 118, 97, 116, 101, 0];
    match File::create(&ordinary[..], FileMode::write_only(), FilePerm.DefaultMode)WAIT {
        Ok(file) => { drop(file); }, Err(error) => { return Err(error); },
    };
    match File::create(&private[..], FileMode::write_only(), FilePerm.Perm(0x180))WAIT {
        Ok(file) => { drop(file); PRIVATE_ACCEPTED },
        Err(error) => { PRIVATE_REFUSED },
    };
    Ok(42)
}
"""

SYNC_MAIN = """
fn main() { match probe() {
    Ok(value) => { print(value); }, Err(error) => { match error {
        FileError.InvalidPath => { print(97); },
        FileError.InvalidOptions => { print(99); },
        FileError.Os { code: code } => { print(code); },
        LAUNCH_ERROR
    }; },
}; }
"""
ASYNC_MAIN = """
fn main() { let task = runtime::spawn(probe()); match task.join() {
    Ok(result) => { match result {
        Ok(value) => { print(value); }, Err(error) => { match error {
        FileError.InvalidPath => { print(97); },
        FileError.InvalidOptions => { print(99); },
        FileError.Os { code: code } => { print(code); },
        LAUNCH_ERROR
    }; },
    }; },
    Err(error) => { drop(error); print(98); },
}; }
"""

PENDING_READ = """
use std::io::{File, FileError};
async fn probe(mut file: File) {
    let mut output: [u8; 1] = [0; 1];
    let pending = file.read(&mut output[..]);
    CONFLICT
    drop(pending.await);
}
fn main() {}
"""


PENDING_SEEK = """
use std::io::SeekFrom;
use std::io::File;
async fn probe(mut file: File) {
    let pending = file.seek(SeekFrom.Start(0));
    drop(file);
    drop(pending.await);
}
fn main() {}
"""

PENDING_RENAME = """
use std::io::File;
async fn probe() {
    let mut source: [u8; 2] = [97, 0];
    let mut destination: [u8; 2] = [98, 0];
    let pending = File::rename(&source[..], &destination[..]);
    CONFLICT[0] = 99;
    drop(pending.await);
}
fn main() {}
"""


def program(asynchronous, expect_acl_rejection=False):
    module = "std::io" if asynchronous else "std::io::sync"
    private_refused = """match error {
        FileError.InvalidPath => { return Ok(118); },
        FileError.InvalidOptions => { return Ok(119); },
        FileError.Os { code: code } => {
            if code != -50 { return Ok(120); }
        },
        LAUNCH_ERROR
    };""" if expect_acl_rejection else "return Err(error);"
    needs_io = OPERATIONS.replace("PRIVATE_ACCEPTED", "return Ok(121);" if expect_acl_rejection else "")
    needs_io = needs_io.replace("PRIVATE_REFUSED", private_refused)
    launch_error = "FileError.LaunchFailed => { return Ok(112); }," if asynchronous else ""
    main = ASYNC_MAIN if asynchronous else SYNC_MAIN
    return (
        f"use {module}::{{File, FileError}};\nuse std::io::sync::{{FileMode, FilePerm, SeekFrom}};\n"
        + needs_io.replace("ASYNC", "async " if asynchronous else "")
        .replace("WAIT", ".await" if asynchronous else "")
        .replace("LAUNCH_ERROR", launch_error)
        + main.replace("LAUNCH_ERROR", "FileError.LaunchFailed => { print(96); }," if asynchronous else "")
    )


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--target")
    cli.add_argument("--cc", default="cc")
    cli.add_argument("--runner", action="append", default=[])
    cli.add_argument("--binaries", type=Path)
    cli.add_argument("--ubsan", action="store_true")
    cli.add_argument("--expect-acl-rejection", action="store_true",
                     help="Windows test volume replaces the requested ACL")
    args = cli.parse_args()
    target = ["--target", args.target] if args.target else []
    windows = "windows" in args.target if args.target else os.name == "nt"
    if args.expect_acl_rejection and not windows:
        cli.error("--expect-acl-rejection requires a Windows target")
    libraries = ["-lws2_32", "-ladvapi32"] if windows else []
    darwin = ("apple" in args.target if args.target else sys.platform == "darwin")
    sanitizer = ["-fsanitize=undefined", "-fno-sanitize-recover=all"] if args.ubsan else []
    with tempfile.TemporaryDirectory() as work:
        root = Path(work)
        if darwin:
            subprocess.run(["chmod", "+a", "everyone allow read,file_inherit", root], check=True)
        (root / "src").mkdir()
        (root / "package.toml").write_text('[package]\nname = "file_io_probe"\n')
        main_source = root / "src/main.crb"
        generated = root / "probe.c"
        for asynchronous in (False, True):
            mode = "async" if asynchronous else "sync"
            main_source.write_text(program(asynchronous, args.expect_acl_rejection))
            emitted = subprocess.run([FRONTEND, "emit-c", root, *target], capture_output=True, text=True)
            assert emitted.returncode == 0, emitted.stderr
            generated.write_text(emitted.stdout)
            for opt in ("O0", "O2"):
                output = (args.binaries or root).resolve()
                output.mkdir(parents=True, exist_ok=True)
                binary = output / (f"{mode}-{opt}" + (".exe" if windows else ""))
                subprocess.run([*shlex.split(args.cc), "-std=c11", "-Wall", "-Wextra", "-Werror",
                                "-pthread", f"-{opt}", *sanitizer, generated, *libraries,
                                "-o", binary], check=True)
                if not args.binaries or args.runner:
                    run = subprocess.run([*args.runner, binary], cwd=root, timeout=20,
                                         capture_output=True, text=True,
                                         **({"umask": 0o022} if os.name != "nt" else {}))
                    assert (run.returncode, run.stdout, run.stderr) == (0, "42\n", ""), (mode, run)
                    assert not (root / "probe-é").exists()
                    assert not (root / "renamed").exists()
                    ordinary, private = root / "ordinary", root / "private"
                    if args.expect_acl_rejection:
                        assert private.stat().st_size == 0
                    if not windows:
                        assert ordinary.stat().st_mode & 0o777 == 0o644
                        assert private.stat().st_mode & 0o777 == 0o600
                    if darwin:
                        # The default file inherits the ACE. The explicit ACL
                        # must suppress it at creation, even with mode 0600.
                        def acl(path):
                            return subprocess.check_output(["ls", "-lde", path], text=True)
                        assert "inherited allow read" in acl(ordinary)
                        assert "inherited allow read" not in acl(private)
                    ordinary.unlink()
                    private.unlink()
                print(f"{mode} -{opt}: {'linked' if args.binaries and not args.runner else 'passed'}")
        for conflict in ("drop(file);", "output[0] = 4;"):
            main_source.write_text(PENDING_READ.replace("CONFLICT", conflict))
            refused = subprocess.run([FRONTEND, "check", root, *target], capture_output=True, text=True)
            assert refused.returncode != 0 and "emprunt" in refused.stderr, (conflict, refused)
        print("Pending read refused early close and destination write")
        for source in (
            PENDING_SEEK,
            PENDING_RENAME.replace("CONFLICT", "source"),
            PENDING_RENAME.replace("CONFLICT", "destination"),
        ):
            main_source.write_text(source)
            refused = subprocess.run([FRONTEND, "check", root, *target], capture_output=True, text=True)
            assert refused.returncode != 0 and "emprunt" in refused.stderr, refused
        print("Pending seek and rename refused early close and path writes")
        main_source.write_text("use std::io::File; fn main() { let file = File {}; drop(file); }")
        refused = subprocess.run([FRONTEND, "check", root, *target], capture_output=True, text=True)
        assert refused.returncode != 0 and "représentation privée" in refused.stderr, refused
        print("Async File layout is private")


if __name__ == "__main__":
    main()
