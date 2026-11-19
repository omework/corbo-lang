"""Check the four SHA-3 variants against the NIST byte-oriented SHA-3 archive."""

import argparse
import hashlib
import os
from pathlib import Path
import shlex
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from check_crust_bootstrap import FRONTEND, ROOT
from check_sha384_sha512 import FILE_HELPERS, nist_cases

RATES = {224: 144, 256: 136, 384: 104, 512: 72}


def monte_carlo(archive, width):
    lines = archive.read(f"SHA3_{width}Monte.rsp").decode("ascii").splitlines()
    seed, = (bytes.fromhex(line[7:]) for line in lines if line.startswith("Seed = "))
    counts = [int(line[8:]) for line in lines if line.startswith("COUNT = ")]
    checkpoints = [bytes.fromhex(line[5:]) for line in lines if line.startswith("MD = ")]
    assert counts == list(range(100)) and len(checkpoints) == len(counts)
    assert all(len(digest) == width // 8 for digest in [seed, *checkpoints])
    return seed, checkpoints


def program(total, max_size):
    imports = ", ".join(f"Sha3_{width}, digest{width}" for width in RATES)
    parts = [f"use std::crypto::sha3::{{{imports}}};", FILE_HELPERS]
    dispatch = []
    monte_calls = []
    for selector, width in enumerate(RATES):
        size = width // 8
        parts.append(f"""
fn check{width}(input: &[u8]) {{
    let length = input.len();
    let direct = digest{width}(&input[0..length]);
    print_bytes(&direct[..]);
    let mut hash = Sha3_{width}::new();
    hash.update(&input[0..0]);
    let mut position: usize = 0;
    while position < length {{
        let next = if length - position < 31 {{ copy(length) }} else {{ position + 31 }};
        hash.update(&input[position..next]);
        position = next;
    }}
    let streamed = hash.finish();
    print_bytes(&streamed[..]);
}}

fn monte{width}(file: &mut File) -> bool {{
    let mut digest: [u8; {size}] = [0; {size}];
    if !read_exact(&mut *file, &mut digest[..]) {{ return false; }}
    let mut checkpoint: usize = 0;
    while checkpoint < 100 {{
        let mut iteration: usize = 0;
        while iteration < 1000 {{
            let next = digest{width}(&digest[..]);
            let mut byte: usize = 0;
            while byte < {size} {{
                digest[byte] = next[byte];
                byte = byte + 1;
            }}
            iteration = iteration + 1;
        }}
        print_bytes(&digest[..]);
        checkpoint = checkpoint + 1;
    }}
    true
}}
""")
        dispatch.append(f"if variant == {selector} {{ check{width}(&data[..size]); }}")
        monte_calls.append(f"    if !monte{width}(&mut *file) {{ return false; }}")
    branches = " else ".join([*dispatch, "{ return false; }"])
    monte = "\n".join(monte_calls)
    parts.append(f"""
fn check_file(file: &mut File) -> bool {{
    let mut header: [u8; 3] = [0; 3];
    let mut data: [u8; {max_size}] = [0; {max_size}];
    let mut index: usize = 0;
    while index < {total} {{
        if !read_exact(&mut *file, &mut header[..]) {{ return false; }}
        let size = ((header[1] as usize) << 8) | (header[2] as usize);
        if size > {max_size} {{ return false; }}
        if !read_exact(&mut *file, &mut data[..size]) {{ return false; }}
        let variant = header[0];
        {branches}
        index = index + 1;
    }}
{monte}
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
    return "\n".join(parts)


def exercise(args):
    expected = []
    fixture = bytearray()
    monte_seeds = bytearray()
    monte_expected = []
    max_size = 0
    nist_total = 0
    boundary_total = 0
    with ZipFile(args.nist_zip) as archive:
        for selector, (width, rate) in enumerate(RATES.items()):
            oracle = getattr(hashlib, f"sha3_{width}")
            cases = list(nist_cases(archive, width, f"SHA3_{width}"))
            assert [len(message) for message, _ in cases] == [
                *range(rate + 1),
                *(rate + (rate + 1) * block for block in range(1, 101)),
            ]
            nist_total += len(cases)
            for length in (rate - 1, rate, rate + 1, 2 * rate - 1, 2 * rate, 2 * rate + 1):
                message = bytes(index % 251 for index in range(length))
                cases.append((message, oracle(message).digest()))
                boundary_total += 1
            for message, digest in cases:
                assert oracle(message).digest() == digest
                max_size = max(max_size, len(message))
                fixture.append(selector)
                fixture.extend(len(message).to_bytes(2, "big"))
                fixture.extend(message)
                expected.extend(((width, len(message), "one-shot", digest),
                                 (width, len(message), "streaming", digest)))
            seed, checkpoints = monte_carlo(archive, width)
            monte_seeds.extend(seed)
            for count, digest in enumerate(checkpoints):
                monte_expected.append((width, count, "Monte Carlo checkpoint", digest))
    total = nist_total + boundary_total
    fixture.extend(monte_seeds)
    expected.extend(monte_expected)

    with TemporaryDirectory() as work:
        root = Path(work)
        (root / "src").mkdir()
        (root / "package.toml").write_text('[package]\nname = "sha3_tests"\n')
        main = root / "src/main.crb"
        main.write_text(program(total, max_size))
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
            actual = subprocess.run([binary], cwd=root, capture_output=True, timeout=180, check=True)
            assert not actual.stderr, actual.stderr
            data = bytes(map(int, actual.stdout.splitlines()))
            position = 0
            for width, index, kind, digest in expected:
                end = position + len(digest)
                assert data[position:end] == digest, (mode, width, index, kind,
                                                       data[position:end].hex(), digest.hex())
                position = end
            assert position == len(data)
            print(f"{mode}: {nist_total} NIST messages and {boundary_total} boundary cases "
                  f"(one-shot and streaming), plus {len(monte_expected)} NIST Monte Carlo checkpoints",
                  flush=True)

        for width in RATES:
            for body, rule, diagnostic in (
                ("let hash = Hasher::new(); let state = &hash.state; drop(state);", b"1", b"priv"),
                ("let mut hash = Hasher::new(); drop(hash.finish()); "
                 "let empty: [u8; 0] = []; hash.update(&empty[..]);", b"6", b"d\xc3\xa9plac"),
            ):
                main.write_text(f"use std::crypto::sha3::Sha3_{width} as Hasher; fn main() {{ {body} }}")
                refused = subprocess.run(command, capture_output=True)
                if args.corboc:
                    assert refused.returncode == 8 and refused.stdout.splitlines()[:1] == [rule], refused
                else:
                    assert refused.returncode != 0 and diagnostic in refused.stderr, refused
        print("External layout access and reuse after finish refused for all four variants", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nist_zip", type=Path)
    parser.add_argument("--corboc", type=Path)
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    exercise(parser.parse_args())


if __name__ == "__main__":
    main()
