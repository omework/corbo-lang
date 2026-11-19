"""Check the RFC 9106 Argon2id vector and the 64 MiB local workspace."""

import argparse
import os
from pathlib import Path
import shlex
import subprocess
from tempfile import TemporaryDirectory

from check_crust_bootstrap import FRONTEND, ROOT

CASES = (
    ("rfc", 32, "32K", "0d640df58d78766c08c037a34a8b53c9d01ef0452d75b65eb52520e96b01e659"),
    ("regional", 65536, "64M", "fedd802b86b17230843c6d3f025c81d3f472fbf9daaf26897fa88844732167ec"),
    ("rounded", 33, "33K", "ac674a5b0c3b645c408773ab9e4f85dd6fac23e3344957fd19522bf33da883"
     "852638fab45ccd7643b1c04b75bc6bdef7121083e626a189e37d6fbf5306118af245a5ac9864ffd8df68"),
)

REGION_PROBE = """
fn main() {
    #(stack_region: max_size=1K, count=1) {
        let mut buffers = pool<Vector<[u64; 128]>>(1);
        let mut work = buffers.new();
        let first: [u64; 128] = [0; 128];
        work.push(first);
        BODY
    }
}
"""


def check_region_limit(command, main, cc, code, binary, corboc):
    for body in (
        "let view = &mut work[..]; let extra: [u64; 128] = [0; 128]; "
        "work.push(extra); print(view.len());",
        "let view = &mut work[..]; drop(work); print(view.len());",
    ):
        main.write_text(REGION_PROBE.replace("BODY", body))
        refused = subprocess.run(command, capture_output=True)
        if corboc:
            assert refused.returncode == 8 and refused.stdout.splitlines()[:1] == [b"5"], refused
        else:
            assert refused.returncode != 0 and b"emprunt actif" in refused.stderr, refused

    main.write_text(REGION_PROBE.replace("BODY", "let extra: [u64; 128] = [0; 128]; work.push(extra);"))
    emitted = subprocess.run(command, capture_output=True, check=True)
    code.write_bytes(emitted.stdout)
    subprocess.run([*shlex.split(cc), "-std=c11", "-pthread", "-O0", code, "-lm", "-o", binary],
                   check=True)
    actual = subprocess.run([binary], capture_output=True, timeout=30)
    assert actual.returncode == 1 and b"limite de la datastack" in actual.stderr, actual
    print("Growth and destruction rejected during a live mutable borrow; the region cap traps")


def witness(name, blocks, region, size):
    test_inputs = ""
    call = "derive(&password[..], &salt[..], params, &mut work[..], &mut output[..])"
    if name == "rfc":
        test_inputs = "let secret: [u8; 8] = [3; 8]; let associated: [u8; 12] = [4; 12];"
        call = ("derive_internal(&password[..], &salt[..], &secret[..], "
                "&associated[..], params, &mut work[..], &mut output[..])")
    return f"""
fn main() {{
    let password: [u8; 32] = [1; 32];
    let salt: [u8; 16] = [2; 16];
    {test_inputs}
    let mut output: [u8; {size}] = [0; {size}];
    #(stack_region: max_size={region}, count=1) {{
        let mut buffers = pool<Vector<[u64; 128]>>(1);
        let mut work = buffers.new();
        let mut i: u64 = 0;
        while i < {blocks} {{
            let block: [u64; 128] = [7; 128];
            work.push(block);
            i = i + 1;
        }}
        let params = Params {{ passes: 3, lanes: 4 }};
        match {call} {{
            Ok(()) => {{}},
            Err(error) => {{ drop(error); print(999); return; }},
        }};
        let view = &work[..];
        let used = view.len() / 16 * 16;
        if view.len() != {blocks} {{ print(999); return; }}
        let mut row: usize = 0;
        while row < view.len() {{
            let expected: u64 = if row < used {{ 0 }} else {{ 7 }};
            let mut word: usize = 0;
            while word < 128 {{
                if view[row][word] != expected {{ print(999); return; }}
                word = word + 1;
            }}
            row = row + 1;
        }}
    }}
    let mut i: usize = 0;
    while i < {size} {{ print(output[i]); i = i + 1; }}
}}
"""


def exercise(args):
    library = ROOT / "stdlib/src/crypto/argon2id"
    with TemporaryDirectory() as work:
        root = Path(work)
        (root / "src/case").mkdir(parents=True)
        (root / "package.toml").write_text('[package]\nname = "argon2id_tests"\n')
        main = root / "src/main.crb"
        main.write_text("use argon2id_tests::case::run; fn main() { run(); }")
        command = [FRONTEND, "emit-c", root]
        if args.corboc:
            command = [args.corboc.resolve(), "--emit-package-c", root, "--stdlib-dir", ROOT / "stdlib/src"]
        code, binary = root / "witness.c", root / "witness"
        for name, blocks, region, hex_digest in CASES:
            expected = bytes.fromhex(hex_digest)
            body = witness(name, blocks, region, len(expected))
            body = body.replace("fn main()", "pub fn run()", 1)
            if name == "rfc":
                # Inject the witness into a local copy of the module to supply
                # RFC 9106's secret and associated data through the private API.
                (root / "src/case/argon2id.crb").write_text(
                    (library / "argon2id.crb").read_text() + body)
                (root / "src/case/blake2b.crb").write_bytes(
                    (library / "blake2b.crb").read_bytes())
            else:
                (root / "src/case/blake2b.crb").unlink(missing_ok=True)
                (root / "src/case/argon2id.crb").write_text(
                    "use std::crypto::argon2id::{Params, derive};\n" + body)
            output = subprocess.run(command, capture_output=True)
            assert output.returncode == 0, (name, output.returncode, output.stderr, output.stdout[:400])
            code.write_bytes(output.stdout)
            for mode, flags in (
                ("native", ["-O0"]),
                ("UBSan", ["-O2", "-fsanitize=undefined", "-fno-sanitize-recover=all"]),
            ):
                subprocess.run([*shlex.split(args.cc), "-std=c11", "-pthread", *flags,
                                code, "-lm", "-o", binary], check=True)
                actual = subprocess.run([binary], capture_output=True, timeout=240, check=True)
                assert not actual.stderr, (name, mode, actual.stderr)
                assert list(map(int, actual.stdout.splitlines())) == list(expected), (
                    name, mode, actual.stdout[:512])
                print(f"{mode} {name}: tag and entire workspace matched", flush=True)
        (root / "src/case/argon2id.crb").unlink()
        check_region_limit(command, main, args.cc, code, binary, args.corboc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corboc", type=Path)
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    exercise(parser.parse_args())


if __name__ == "__main__":
    main()
