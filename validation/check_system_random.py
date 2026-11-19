"""Check the system RNG buffer contract and the error path in Din."""

import argparse
import os
from pathlib import Path
import shlex
import subprocess
from tempfile import TemporaryDirectory

from check_crust_bootstrap import FRONTEND, ROOT

SYSTEM_PROGRAM = """
use std::crypto::random::fill;

fn main() {
    let mut left: [u8; 515] = [165; 515];
    let mut right: [u8; 515] = [165; 515];
    let first = &mut left[..];
    match fill(&mut first[1..514]) {
        Ok(()) => {},
        Err(error) => { drop(error); print(false); return; },
    };
    match fill(&mut first[1..1]) {
        Ok(()) => {},
        Err(error) => { drop(error); print(false); return; },
    };
    let second = &mut right[..];
    match fill(&mut second[1..514]) {
        Ok(()) => {},
        Err(error) => { drop(error); print(false); return; },
    };
    let mut i: usize = 1;
    let mut first_chunk = false;
    let mut second_chunk = false;
    while i < 257 {
        if first[i] != second[i] { first_chunk = true; }
        i = i + 1;
    }
    while i < 513 {
        if first[i] != second[i] { second_chunk = true; }
        i = i + 1;
    }
    print(first_chunk && second_chunk && first[0] == 165 && first[514] == 165
        && second[0] == 165 && second[514] == 165);
}
"""

MOCK_BACKEND = """
fn interrupted(code: i64) -> bool { code == -4 }

fn read_random(output: &mut [u8]) -> (i64, usize) {
    let length = output.len();
    if length == 0 || length > 256 { return (-99, 0); }
    let mode = output[0];
    if mode == 1 {
        output[0] = 2;
        return (-4, 0);
    }
    if mode == 2 {
        output[0] = 9;
        return (0, 1);
    }
    if mode == 3 { return (-13, 0); }
    if mode == 4 { return (0, 0); }
    if mode == 5 { return (0, 257); }
    let mut offset: usize = 0;
    while offset < length {
        output[offset] = 9;
        offset = offset + 1;
    }
    return (0, length);
}
"""

MOCK_PROGRAM = """
fn accepted(output: &mut [u8]) -> bool {
    match fill(output) {
        Ok(()) => { true },
        Err(error) => { drop(error); false },
    }
}

fn error_code(output: &mut [u8]) -> i64 {
    match fill(output) {
        Ok(()) => { 0 },
        Err(error) => {
            match error {
                RandomError.Os { code: code } => { code },
                RandomError.InvalidCount => { -100 },
            }
        },
    }
}

fn main() {
    let mut retry: [u8; 515] = [0; 515];
    retry[0] = 1;
    print(accepted(&mut retry[..]));
    let mut i: usize = 0;
    while i < 515 {
        if retry[i] != 9 { print(false); return; }
        i = i + 1;
    }
    let mut empty: [u8; 0] = [];
    print(accepted(&mut empty[..]));

    let mut denied: [u8; 3] = [2, 3, 7];
    print(error_code(&mut denied[..]));
    print(denied[0] == 9 && denied[1] == 3 && denied[2] == 7);
    let mut zero: [u8; 1] = [4];
    print(error_code(&mut zero[..]));
    let mut excessive: [u8; 1] = [5];
    print(error_code(&mut excessive[..]));
}
"""

SHARED_OUTPUT = """
use std::crypto::random::fill;
fn main() {
    let output: [u8; 16] = [0; 16];
    drop(fill(&output[..]));
}
"""


def exercise(args):
    compiler = shlex.split(args.compiler_runner)
    cc = shlex.split(args.cc)
    runner = shlex.split(args.runner)
    windows = "windows" in args.target if args.target else os.name == "nt"
    with TemporaryDirectory(dir=args.work_dir) as directory:
        root = Path(directory)
        (root / "src").mkdir()
        (root / "package.toml").write_text('[package]\nname = "random_probe"\n')
        main = root / "src/main.crb"
        command = [FRONTEND, "emit-c", root]
        if args.corboc:
            command = compiler + [args.corboc.resolve(), "--emit-package-c", root,
                                  "--stdlib-dir", ROOT / "stdlib/src"]
        elif args.target:
            command += ["--target", args.target]

        cases = [("system", SYSTEM_PROGRAM, "true")]
        if not args.system_only:
            wrapper = (ROOT / "stdlib/src/crypto/random/random.crb").read_text()
            public = "pub enum" + wrapper.split("pub enum", 1)[1]
            cases.append(("mocked", MOCK_BACKEND + public + MOCK_PROGRAM,
                          "true\ntrue\n-13\ntrue\n-100\n-100"))
        for name, program, expected in cases:
            main.write_text(program)
            emitted = subprocess.run(command, capture_output=True, timeout=90)
            assert emitted.returncode == 0, (name, emitted.returncode, emitted.stderr, emitted.stdout[:300])
            source = root / "witness.c"
            source.write_bytes(emitted.stdout)
            binary = root / ("witness.exe" if windows else "witness")
            configs = [("O0", []), ("O2", [])]
            if args.ubsan:
                configs[1] = ("O2", ["-fsanitize=undefined", "-fno-sanitize-recover=all"])
            for opt, flags in configs:
                libraries = ["-lbcrypt", "-lws2_32", "-ladvapi32"] if windows else []
                subprocess.run([*cc, "-std=c11", "-pthread", f"-{opt}", *flags, source,
                                "-lm", *libraries, "-o", binary], check=True, timeout=120)
                if args.link_only:
                    print(f"{name} {opt}: linked", flush=True)
                    continue
                result = subprocess.run([*runner, binary], capture_output=True, text=True, timeout=60)
                assert (result.returncode, result.stdout.strip()) == (0, expected), (name, opt, result)
                print(f"{name} {opt}: passed", flush=True)

        main.write_text(SHARED_OUTPUT)
        refused = subprocess.run(command, capture_output=True, timeout=90)
        if args.corboc:
            assert refused.returncode == 8 and refused.stdout.splitlines()[:1] == [b"1"], refused
        else:
            assert refused.returncode != 0 and b"type incompatible" in refused.stderr, refused
        print("Shared output refused", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default="")
    parser.add_argument("--corboc", type=Path)
    parser.add_argument("--compiler-runner", default="")
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    parser.add_argument("--runner", default="")
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--link-only", action="store_true")
    parser.add_argument("--system-only", action="store_true")
    parser.add_argument("--ubsan", action="store_true")
    exercise(parser.parse_args())


if __name__ == "__main__":
    main()
