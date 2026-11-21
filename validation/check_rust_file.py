"""Build and exercise the packaged std::io::File API on a supported target."""
import argparse
from pathlib import Path
import os

if os.name != "nt":
    import resource
import shlex
import subprocess
import tempfile

from check_rust_assembly import FRONTEND, LINUX64

PROGRAM = """
use std::io::{File, FileError};
use std::io::{FileMode};

fn main() {
    let path: [u8; 7] = [105, 110, 46, 116, 120, 116, 0];
    match File::open(&path[..], FileMode::read_only()) {
        Ok(opened) => {
            let mut file = opened;
            let mut empty: [u8; 0] = [];
            match file.read(&mut empty[..]) {
                Ok(count) => { print(count); },
                Err(error) => { drop(error); print(-1); },
            }
            let mut buffer: [u8; 2] = [0, 0];
            match file.read(&mut buffer[..]) {
                Ok(count) => { print(count); print(buffer[0]); print(buffer[1]); },
                Err(error) => { drop(error); print(-2); },
            }
            match file.read(&mut buffer[..]) {
                Ok(count) => { print(count); },
                Err(error) => { drop(error); print(-3); },
            }
        },
        Err(error) => { drop(error); print(-4); },
    }

    // Keep the descriptor limit low when running this witness. Repeated
    // successful opens then demonstrate scope cleanup after each move.
    let mut iteration: i64 = 0;
    while iteration < 128 {
        match File::open(&path[..], FileMode::read_only()) {
            Ok(opened) => { let moved = opened; },
            Err(error) => { drop(error); print(-8); return; },
        }
        iteration = iteration + 1;
    }

    let invalid: [u8; 1] = [120];
    match File::open(&invalid[..], FileMode::read_only()) {
        Ok(file) => { drop(file); print(-5); },
        Err(error) => {
            match error {
                FileError.InvalidPath => { print(10); },
                FileError.InvalidOptions => { print(-12); },
                FileError.Os { code: code } => { print(code); },
            }
        },
    }
    let missing: [u8; 8] = [109, 105, 115, 115, 105, 110, 103, 0];
    match File::open(&missing[..], FileMode::read_only()) {
        Ok(file) => { drop(file); print(-6); },
        Err(error) => {
            match error {
                FileError.InvalidPath => { print(-7); },
                FileError.InvalidOptions => { print(-12); },
                FileError.Os { code: code } => { print(code); },
            }
        },
    }
}
"""
EXPECTED = "0\n2\n65\n66\n0\n10\n-2\n"


# Instrument only the witness. The shim calls the real Win32 API and checks
# that each closed handle is invalid immediately after the call.
WINDOWS_CLOSE_CHECK = r"""
#include <windows.h>

static unsigned closed_handles;

BOOL WINAPI crust_probe_close(HANDLE handle) {
    DWORD flags;
    if (!CloseHandle(handle) ||
        GetHandleInformation(handle, &flags) ||
        GetLastError() != ERROR_INVALID_HANDLE)
        exit(90);
    ++closed_handles;
    return TRUE;
}

int main(int argc, char **argv) {
    int result = crust_probe_main(argc, argv);
    if (result != 0 || closed_handles != 129)
        return 91;
    printf("closed=%u\n", closed_handles);
    return 0;
}
"""


def instrument_windows_close(source):
    assert source.count("CloseHandle") == 1
    assert source.count("int main(int argc, char **argv) {") == 1
    return (source.replace("CloseHandle", "crust_probe_close")
                  .replace("int main(int argc, char **argv)", "static int crust_probe_main(int argc, char **argv)")
            + WINDOWS_CLOSE_CHECK)


def limit_descriptors():
    _, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, hard))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=LINUX64)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--binaries", type=Path)
    parser.add_argument("--runner", action="append", default=[],
                        help="Runner executable or argument. Repeat for each argument.")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "package.toml").write_text('[package]\nname = "file_probe"\n')
        entry = root / "src/main.crb"
        entry.parent.mkdir()
        entry.write_text(PROGRAM)
        generated = subprocess.run([FRONTEND, "emit-c", root, "--target", args.target],
                                   text=True, capture_output=True, timeout=15)
        assert generated.returncode == 0, generated.stderr
        source = root / "probe.c"
        windows = "windows" in args.target
        witnesses = (args.binaries or root).resolve()
        witnesses.mkdir(parents=True, exist_ok=True)
        (witnesses / "in.txt").write_bytes(b"AB")
        variants = [("probe", generated.stdout, EXPECTED)]
        if windows:
            variants.append(("close-probe", instrument_windows_close(generated.stdout),
                             EXPECTED + "closed=129\n"))
        for name, code, expected in variants:
            source.write_text(code)
            for opt in ("O0", "O2"):
                binary = witnesses / (f"{name}-{opt}.exe" if windows else f"{name}-{opt}")
                subprocess.run([*shlex.split(args.cc), "-std=c11", "-Wall", "-Wextra",
                                "-Werror", f"-{opt}", source, *(["-lws2_32", "-ladvapi32"] if windows else []),
                                "-o", binary], check=True)
                if not args.binaries or args.runner:
                    options = {}
                    if not windows and os.name != "nt":
                        options["preexec_fn"] = limit_descriptors
                    result = subprocess.run([*args.runner, binary], cwd=witnesses, text=True,
                                            capture_output=True, timeout=45, **options)
                    assert (result.returncode, result.stdout) == (0, expected), result
                    print(f"{binary.name}: {result.stdout.strip().replace(chr(10), ', ')}")

        for target in ("aarch64-apple-darwin", "x86_64-apple-darwin", "x86_64-pc-windows-gnu", "aarch64-pc-windows-msvc"):
            selected = subprocess.run([FRONTEND, "emit-c", root, "--target", target],
                                      text=True, capture_output=True, timeout=15)
            assert selected.returncode == 0, selected.stderr
            assert ("CreateFileW" if "windows" in target else "_open") in selected.stdout
            assert "crust_file_open(" not in selected.stdout

        refusals = [
            (LINUX64, "use std::io::File; fn main() { let f = File { fd: 0 }; drop(f); }",
             "représentation privée"),
            (LINUX64, "use std::io::File; fn main() { let mut p = pool<File>(1); let f = p.new(); drop(f); }",
             "représentation privée"),
            (LINUX64, "use std::sys::unix::linux::x86_64::close; fn main() {}",
             "private platform component"),
            ("aarch64-unknown-linux-gnu", PROGRAM, "unknown import or component std::io::File"),
            ("x86_64-unknown-linux-gnux32", PROGRAM, "unknown import or component std::io::File"),
            (LINUX64, "fn main() { let b: [u8; 1] = [0]; let s = &mut b[..]; print(s.len()); }",
             "tableau mutable attendu"),
            (LINUX64, "fn main() { let mut b: [u8; 1] = [0]; let s = &mut b[..]; print(b[0]); print(s.len()); }",
             "emprunt actif"),
        ]
        for target, program, diagnostic in refusals:
            entry.write_text(program)
            result = subprocess.run([FRONTEND, "check", root, "--target", target],
                                    text=True, capture_output=True, timeout=15)
            assert result.returncode != 0 and diagnostic in result.stderr, result.stderr
    print(f"File C witnesses compiled at -O0 and -O2, {len(refusals)} refusals confirmed")
    if not args.binaries or args.runner:
        print("Executions validated empty, bounded, EOF and error paths")


if __name__ == "__main__":
    main()
