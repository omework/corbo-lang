"""Compare Din's native SHA-256 with hashlib on the requested target."""
import argparse
import hashlib
import os
from pathlib import Path
import platform
import shlex
import subprocess
from tempfile import TemporaryDirectory

from check_crust_bootstrap import FRONTEND, ROOT

PROGRAM = """
use std::crypto::sha256::{Sha256, HashError, digest};

fn print_digest(result: Result<[u8; 32], HashError>) {
    match result {
        Ok(bytes) => {
            let mut at: usize = 0;
            while at < 32 {
                print(bytes[at]);
                at = at + 1;
            }
        },
        Err(_) => { print(999); },
    };
}

fn stream(mut context: Sha256, sample: &[u8], chunk: usize) -> Result<[u8; 32], HashError> {
    match context.update(&sample[0..0]) {
        Ok(()) => {},
        Err(error) => { return Err(error); },
    };
    let length = sample.len();
    let mut position: usize = 0;
    while position < length {
        let remaining = length - position;
        let next = if remaining < chunk { copy(length) } else { position + chunk };
        match context.update(&sample[position..next]) {
            Ok(()) => {},
            Err(error) => { return Err(error); },
        };
        position = next;
    }
    Ok(context.finish())
}

fn sample(bytes: &[u8], chunk: usize) {
    let length = bytes.len();
    print_digest(digest(&bytes[0..length]));
    let portable = Sha256::portable();
    let automatic = Sha256::new();
    print_digest(stream(portable, &bytes[0..length], copy(chunk)));
    print_digest(stream(automatic, &bytes[0..length], chunk));
}

fn main() {
    let hardware = Sha256::new();
    print(hardware.hardware_accelerated());
    let abc: [u8; 3] = [97,98,99];
    sample(&abc[..], 1);
    let bytes: [u8; 257] = [VALUES];
    CHECKS
}
"""

CASES = (
    (0, 1), (1, 1), (55, 17), (56, 55), (57, 56), (63, 7), (64, 63),
    (65, 64), (119, 31), (120, 57), (127, 16), (128, 3), (129, 65), (257, 67),
)


def exercise(args):
    data = bytes((73 * i + 31) % 256 for i in range(257))
    source = PROGRAM.replace("VALUES", ",".join(map(str, data))).replace(
        "CHECKS", "\n".join(f"sample(&bytes[..{length}], {chunk});" for length, chunk in CASES),
    )
    expected = b"".join(hashlib.sha256(value).digest() * 3 for value in (
        b"abc", *(data[:length] for length, _ in CASES)
    ))
    with TemporaryDirectory() as work:
        root = Path(work)
        (root / "src").mkdir()
        (root / "package.toml").write_text('[package]\nname = "sha256_tests"\n')
        (root / "src/main.crb").write_text(source)
        target = ["--target", args.target] if args.target else []
        code = root / "sha256.c"
        emit = [args.corboc, "--emit-package-c", root, "--stdlib-dir", ROOT / "stdlib/src"] if args.corboc else [
            FRONTEND, "emit-c", root, *target,
        ]
        code.write_bytes(subprocess.check_output(emit))
        for mode, flags in (
            ("native", ["-O0"]),
            ("UBSan", ["-O2", "-fsanitize=undefined", "-fno-sanitize-recover=all"]),
        ):
            binary = root / "sha256"
            subprocess.run(
                [*shlex.split(args.cc), "-std=c11", "-pthread", *flags, code, "-lm", "-o", binary],
                check=True,
            )
            result = subprocess.run([*shlex.split(args.runner), binary], capture_output=True, timeout=60, check=True)
            dispatch, *values = result.stdout.splitlines()
            assert dispatch in (b"true", b"false") and result.stderr == b"", result
            if args.require_hardware:
                assert dispatch == b"true", "SHA-256 instructions were not selected"
            assert bytes(map(int, values)) == expected, (args.target, mode)
            print(f"{args.target or 'host'} {mode}: {len(CASES) + 1} vectors matched in three modes; hardware={dispatch.decode()}", flush=True)
        verifier = emit if args.corboc else [FRONTEND, "check", root, *target]
        main = root / "src/main.crb"
        fields = "{ state: [0; 8], block: [0; 64], bytes: 0, accelerated: false }"
        main.write_text(f"""
struct Sha256 {{ state: [u64; 8], block: [u8; 64], bytes: u64, accelerated: bool }}
fn main() {{
    let local = Sha256 {fields};
    print(local.bytes);
}}
""")
        # The restriction follows the resolved standard type, even when a
        # different type uses the same name and field spellings.
        subprocess.run(verifier, check=True, capture_output=True)
        for imports, program, diagnostic, rule in (
            ("Sha256", "let hash = Sha256::new(); drop(hash.finish()); print(hash.hardware_accelerated());",
             "déplacée", "6"),
            ("Sha256", f"let forged = Sha256 {fields}; drop(forged);", "privée", "1"),
            ("Sha256 as Hash", f"let forged = Hash {fields}; drop(forged);", "privée", "1"),
            ("Sha256", "let hash = Sha256::new(); print(hash.bytes);", "privée", "1"),
            ("Sha256", "let mut hash = Sha256::new(); let bytes = &mut hash.bytes; *bytes = 0;", "privée", "1"),
            ("Sha256", "let mut slots = pool<Sha256>(1); let hash = slots.new(); drop(hash);", "privée", "1"),
        ):
            main.write_text(f"use std::crypto::sha256::{imports}; fn main() {{ {program} }}")
            refused = subprocess.run(verifier, capture_output=True, text=True)
            if args.corboc:
                assert refused.returncode == 8 and refused.stdout.splitlines()[:1] == [rule], (program, refused)
                if diagnostic == "privée" and platform.system() == "Darwin" and platform.machine() == "arm64":
                    assert "private field layout" in refused.stderr, (program, refused)
            else:
                assert refused.returncode and diagnostic in refused.stderr, (program, refused.stderr)
        print("Receiver reuse and external construction, projection, and borrowing refused", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target")
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    parser.add_argument("--runner", default="")
    parser.add_argument("--require-hardware", action="store_true")
    parser.add_argument("--corboc", type=Path, help="use the self-hosted compiler on its native target")
    args = parser.parse_args()
    if args.corboc and args.target:
        parser.error("--corboc already selects the compiler's native target")
    if args.corboc:
        args.corboc = args.corboc.resolve()
    exercise(args)


if __name__ == "__main__":
    main()
