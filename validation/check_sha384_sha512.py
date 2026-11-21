"""Check SHA-384 and SHA-512 against the NIST byte-oriented SHA archive."""
import argparse
import hashlib
import os
from pathlib import Path
import shlex
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from check_crust_bootstrap import FRONTEND, ROOT


def nist_cases(source, width, stem):
    for group in ("Short", "Long"):
        name = f"{stem}{group}Msg.rsp"
        for line in source.read(name).decode("ascii").splitlines():
            if line.startswith("Len = "):
                length = int(line[6:])
            elif line.startswith("Msg = "):
                message = bytes.fromhex(line[6:]) if length else b""
            elif line.startswith("MD = "):
                digest = bytes.fromhex(line[5:])
                assert len(message) * 8 == length and len(digest) * 8 == width
                yield message, digest


FILE_HELPERS = """
use std::io::{File};
use std::io::{FileMode};

fn print_bytes(bytes: &[u8]) {
    let mut i: usize = 0;
    while i < bytes.len() {
        print(bytes[i]);
        i = i + 1;
    }
}

fn read_exact(file: &mut File, output: &mut [u8]) -> bool {
    let length = output.len();
    let mut read: usize = 0;
    while read < length {
        match file.read(&mut output[read..length]) {
            Err(error) => { drop(error); return false; },
            Ok(count) => {
                if count == 0 { return false; }
                read = read + count;
            },
        };
    }
    true
}
"""


def program(count384, total, max_size):
    helpers = ["use std::crypto::sha512::{Sha384, Sha512, digest384, digest512};", FILE_HELPERS]
    for width in (384, 512):
        helpers.append(f"""
fn check{width}(input: &[u8]) -> bool {{
    let length = input.len();
    match digest{width}(&input[0..length]) {{
        Err(error) => {{ drop(error); return false; }},
        Ok(digest) => {{ print_bytes(&digest[..]); }},
    }};
    let mut hash = Sha{width}::new();
    match hash.update(&input[0..0]) {{
        Err(error) => {{ drop(error); return false; }},
        Ok(()) => {{}},
    }};
    let mut position: usize = 0;
    while position < length {{
        let next = if length - position < 73 {{ copy(length) }} else {{ position + 73 }};
        match hash.update(&input[position..next]) {{
            Err(error) => {{ drop(error); return false; }},
            Ok(()) => {{}},
        }};
        position = next;
    }}
    let digest = hash.finish();
    print_bytes(&digest[..]);
    true
}}
""")
    helpers.append(f"""
fn check_file(file: &mut File) -> bool {{
    let mut header: [u8; 2] = [0; 2];
    let mut data: [u8; {max_size}] = [0; {max_size}];
    let mut index: usize = 0;
    while index < {total} {{
        if !read_exact(&mut *file, &mut header[..]) {{ return false; }}
        let size = ((header[0] as usize) << 8) | (header[1] as usize);
        if size > {max_size} {{ return false; }}
        if !read_exact(&mut *file, &mut data[..size]) {{ return false; }}
        if index < {count384} {{
            if !check384(&data[..size]) {{ return false; }}
        }} else {{
            if !check512(&data[..size]) {{ return false; }}
        }}
        index = index + 1;
    }}
    true
}}

fn main() {{
    let path: [u8; 12] = [118,101,99,116,111,114,115,46,98,105,110,0];
    match File::open(&path[..], FileMode::read_only()) {{
        Err(error) => {{ drop(error); print(999); }},
        Ok(opened) => {{
            let mut file = opened;
            if !check_file(&mut file) {{ print(999); }}
        }},
    }};
}}
""")
    return "\n".join(helpers)


def exercise(args):
    expected = bytearray()
    fixture = bytearray()
    counts = []
    max_size = 0
    nist_total = 0
    with ZipFile(args.nist_zip) as archive:
        for width in (384, 512):
            oracle = getattr(hashlib, f"sha{width}")
            cases = list(nist_cases(archive, width, f"shabytetestvectors/SHA{width}"))
            assert len(cases) == 257
            nist_total += len(cases)
            for length in (129, 239, 240, 255, 256, 257):
                message = bytes(index % 251 for index in range(length))
                cases.append((message, oracle(message).digest()))
            counts.append(len(cases))
            for message, digest in cases:
                assert oracle(message).digest() == digest
                max_size = max(max_size, len(message))
                fixture.extend(len(message).to_bytes(2, "big"))
                fixture.extend(message)
                expected.extend(digest * 2)

    with TemporaryDirectory() as work:
        root = Path(work)
        (root / "src").mkdir()
        (root / "package.toml").write_text('[package]\nname = "sha512_tests"\n')
        main = root / "src/main.crb"
        main.write_text(program(counts[0], sum(counts), max_size))
        (root / "vectors.bin").write_bytes(fixture)
        command = [FRONTEND, "emit-c", root]
        if args.corboc:
            command = [args.corboc.resolve(), "--emit-package-c", root, "--stdlib-dir", ROOT / "stdlib/src"]
        emitted = subprocess.run(command, capture_output=True)
        assert emitted.returncode == 0, (emitted.returncode, emitted.stderr, emitted.stdout[:500])
        code = root / "witness.c"
        code.write_bytes(emitted.stdout)
        for mode, flags in (
            ("native", ["-O0"]),
            ("UBSan", ["-O2", "-fsanitize=undefined", "-fno-sanitize-recover=all"]),
        ):
            binary = root / "witness"
            subprocess.run([*shlex.split(args.cc), "-std=c11", "-pthread", *flags,
                            code, "-lm", "-o", binary], check=True)
            actual = subprocess.run([binary], cwd=root, capture_output=True, timeout=120, check=True)
            assert not actual.stderr, actual.stderr
            assert list(map(int, actual.stdout.splitlines())) == list(expected), mode
            print(f"{mode}: {nist_total} NIST vectors and 12 boundary cases matched in both modes", flush=True)

        for width in (384, 512):
            for body, rule, diagnostic in (
                ("let hash = Hasher::new(); let state = &hash.state; drop(state);", b"1", b"priv"),
                ("let mut hash = Hasher::new(); drop(hash.finish()); "
                 "let empty: [u8; 0] = []; drop(hash.update(&empty[..]));", b"6", b"d\xc3\xa9plac"),
            ):
                main.write_text(f"use std::crypto::sha512::Sha{width} as Hasher; fn main() {{ {body} }}")
                refused = subprocess.run(command, capture_output=True)
                if args.corboc:
                    assert refused.returncode == 8 and refused.stdout.splitlines()[:1] == [rule], refused
                else:
                    assert refused.returncode != 0 and diagnostic in refused.stderr, refused
        print("Both context layouts and reuse after finish were refused", flush=True)

        # Seed the private counter in a test-only copy so a carry and
        # rejection can be exercised without exabytes of input.
        library = ROOT / "stdlib/src/crypto/sha512"
        kernel = root / "src/kernel"
        kernel.mkdir()
        (kernel / "compression.crb").write_bytes((library / "compression.crb").read_bytes())
        (kernel / "sha512.crb").write_text((library / "sha512.crb").read_text() + """
pub fn check_counter() -> bool {
    let input: [u8; 1] = [99];
    let mut carry = State { words: [0; 8], block: [0; 128],
        bytes_low: U64_MAX, bytes_high: 1 };
    match update_state(&mut carry, &input[..]) {
        Ok(()) => {},
        Err(error) => { drop(error); return false; },
    };
    if carry.bytes_low != 0 || carry.bytes_high != 2 { return false; }

    let mut full = State { words: [42; 8], block: [165; 128],
        bytes_low: U64_MAX, bytes_high: MAX_HIGH_BYTES };
    match update_state(&mut full, &input[..]) {
        Err(error) => { drop(error); },
        Ok(()) => { return false; },
    };
    if full.bytes_low != U64_MAX || full.bytes_high != MAX_HIGH_BYTES { return false; }
    let mut i: u64 = 0;
    while i < 128 {
        if full.block[i] != 165 || full.words[i % 8] != 42 { return false; }
        i = i + 1;
    }
    true
}
""")
        main.write_text("use sha512_tests::kernel::check_counter; fn main() { print(check_counter()); }")
        emitted = subprocess.run(command, capture_output=True)
        assert emitted.returncode == 0, (emitted.returncode, emitted.stderr, emitted.stdout[:500])
        code.write_bytes(emitted.stdout)
        subprocess.run([*shlex.split(args.cc), "-std=c11", "-pthread", "-O2", "-fsanitize=undefined",
                        "-fno-sanitize-recover=all", code, "-lm", "-o", binary], check=True)
        counter = subprocess.run([binary], capture_output=True, timeout=120, check=True)
        assert (counter.stdout.splitlines(), counter.stderr) == ([b"true"], b""), counter
        print("The count carried into the high limb and rejected overflow without mutation", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nist_zip", type=Path)
    parser.add_argument("--corboc", type=Path)
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    exercise(parser.parse_args())


if __name__ == "__main__":
    main()
