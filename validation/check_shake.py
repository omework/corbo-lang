"""Check Din SHAKE128 and SHAKE256 against all eight NIST byte-vector files."""

import argparse
import hashlib
import os
from pathlib import Path
import re
import shlex
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from check_crust_bootstrap import FRONTEND, ROOT
from check_sha384_sha512 import FILE_HELPERS

VARIANTS = {128: (168, 1126), 256: (136, 1246)}


def response(archive, width, group):
    return archive.read(f"SHAKE{width}{group}.rsp").decode("ascii").replace("\r\n", "\n")


def message_cases(archive, width, rate, variable_count):
    for group, lengths in (
        ("ShortMsg", range(2 * rate + 1)),
        ("LongMsg", (rate + (rate + 1) * block for block in range(1, 101))),
    ):
        records = re.findall(r"^Len = (\d+)\nMsg = ([a-f0-9]+)\nOutput = ([a-f0-9]+)$",
                             response(archive, width, group), re.M)
        assert [int(bits) for bits, _, _ in records] == [length * 8 for length in lengths]
        for bits, message, digest in records:
            message = bytes.fromhex(message) if int(bits) else b""
            digest = bytes.fromhex(digest)
            assert len(message) * 8 == int(bits) and len(digest) * 8 == width
            yield group, message, digest

    records = re.findall(r"^COUNT = (\d+)\nOutputlen = (\d+)\nMsg = ([a-f0-9]+)\n"
                         r"Output = ([a-f0-9]+)$", response(archive, width, "VariableOut"), re.M)
    assert [int(count) for count, _, _, _ in records] == list(range(variable_count))
    for _, bits, message, digest in records:
        message = bytes.fromhex(message)
        digest = bytes.fromhex(digest)
        assert len(message) * 8 == width and len(digest) * 8 == int(bits)
        yield "VariableOut", message, digest


def monte_cases(archive, width):
    source = response(archive, width, "Monte")
    min_bits, max_bits = map(int, re.findall(r"Output Length \(bits\) = (\d+)\]", source))
    seed, = re.findall(r"^Msg = ([a-f0-9]+)$", source, re.M)
    seed = bytes.fromhex(seed)
    assert len(seed) == 16
    records = re.findall(r"^COUNT = (\d+)\nOutputlen = (\d+)\nOutput = ([a-f0-9]+)$", source, re.M)
    assert [int(count) for count, _, _ in records] == list(range(100))
    digests = []
    for _, bits, output in records:
        digest = bytes.fromhex(output)
        assert len(digest) * 8 == int(bits) and min_bits <= int(bits) <= max_bits
        digests.append(digest)
    return seed, (min_bits + 7) // 8, max_bits // 8, digests


def program(total, max_input, max_output, monte_calls):
    calls = "\n".join(monte_calls)
    return "use std::crypto::sha3::{shake128, shake256};\n" + FILE_HELPERS + f"""
fn compute(variant: u8, input: &[u8], output: &mut [u8]) {{
    if variant == 0 {{ shake128(input, output); }}
    else {{ shake256(input, output); }}
}}

fn check_messages(file: &mut File) -> bool {{
    let mut header: [u8; 5] = [0; 5];
    let mut data: [u8; {max_input}] = [0; {max_input}];
    let mut storage: [u8; {max_output + 2}] = [0; {max_output + 2}];
    let output = &mut storage[..];
    let mut index: usize = 0;
    while index < {total} {{
        if !read_exact(&mut *file, &mut header[..]) {{ return false; }}
        let input_size = ((header[1] as usize) << 8) | (header[2] as usize);
        let output_size = ((header[3] as usize) << 8) | (header[4] as usize);
        if input_size > {max_input} || output_size > {max_output} {{ return false; }}
        if !read_exact(&mut *file, &mut data[..input_size]) {{ return false; }}
        let end = output_size + 1;
        output[0] = 171;
        output[end] = 205;
        compute(header[0], &data[..input_size], &mut output[1..end]);
        if output[0] != 171 || output[end] != 205 {{ return false; }}
        print_bytes(&output[1..end]);
        index = index + 1;
    }}
    true
}}

fn monte(file: &mut File, variant: u8, minimum: usize, maximum: usize) -> bool {{
    let mut message: [u8; 16] = [0; 16];
    let mut output: [u8; {max_output}] = [0; {max_output}];
    if !read_exact(&mut *file, &mut message[..]) {{ return false; }}
    let mut size = copy(maximum);
    let range = maximum - minimum + 1;
    let mut checkpoint: usize = 0;
    while checkpoint < 100 {{
        let mut iteration: usize = 0;
        while iteration < 1000 {{
            compute(copy(variant), &message[..], &mut output[..size]);
            let mut byte: usize = 0;
            while byte < 16 {{
                message[byte] = if byte < size {{ output[byte] }} else {{ 0 }};
                byte = byte + 1;
            }}
            let tail = ((output[size - 2] as usize) << 8) | (output[size - 1] as usize);
            if iteration == 999 {{ print_bytes(&output[..size]); }}
            size = minimum + tail % range;
            iteration = iteration + 1;
        }}
        checkpoint = checkpoint + 1;
    }}
    true
}}

fn check_file(file: &mut File) -> bool {{
    if !check_messages(&mut *file) {{ return false; }}
{calls}
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
"""


def exercise(args):
    fixture = bytearray()
    seeds = bytearray()
    monte_calls = []
    expected = []
    checkpoints = []
    nist_total = 0
    boundary_total = 0
    max_input = 0
    max_output = 0
    with ZipFile(args.nist_zip) as archive:
        for selector, (width, (rate, variable_count)) in enumerate(VARIANTS.items()):
            oracle = getattr(hashlib, f"shake_{width}")
            cases = list(message_cases(archive, width, rate, variable_count))
            nist_total += len(cases)
            sizes = (0, 1, rate - 1, rate, rate + 1, 2 * rate - 1, 2 * rate, 2 * rate + 1)
            for input_size in sizes:
                message = bytes(i % 251 for i in range(input_size))
                for output_size in sizes:
                    cases.append(("boundary", message, oracle(message).digest(output_size)))
                    boundary_total += 1
            for group, message, digest in cases:
                assert oracle(message).digest(len(digest)) == digest
                max_input = max(max_input, len(message))
                max_output = max(max_output, len(digest))
                fixture.append(selector)
                fixture.extend(len(message).to_bytes(2, "big"))
                fixture.extend(len(digest).to_bytes(2, "big"))
                fixture.extend(message)
                expected.append((width, group, len(message), digest))

            seed, minimum, maximum, digests = monte_cases(archive, width)
            max_output = max(max_output, maximum)
            seeds.extend(seed)
            monte_calls.append(f"    if !monte(&mut *file, {selector}, {minimum}, {maximum}) "
                               "{ return false; }")
            checkpoints.extend((width, "Monte Carlo checkpoint", count, digest)
                               for count, digest in enumerate(digests))

    with TemporaryDirectory() as work:
        root = Path(work)
        (root / "src").mkdir()
        (root / "package.toml").write_text('[package]\nname = "shake_tests"\n')
        main = root / "src/main.crb"
        main.write_text(program(len(expected), max_input, max_output, monte_calls))
        (root / "vectors.bin").write_bytes(fixture + seeds)
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
            values = list(map(int, actual.stdout.splitlines()))
            assert all(0 <= value <= 255 for value in values), "witness reported a failure"
            data = bytes(values)
            position = 0
            for width, group, index, digest in (*expected, *checkpoints):
                end = position + len(digest)
                assert data[position:end] == digest, (mode, width, group, index,
                                                       data[position:end].hex(), digest.hex())
                position = end
            assert position == len(data)
            print(f"{mode}: {nist_total} NIST message/output vectors, "
                  f"{len(checkpoints)} Monte Carlo checkpoints, "
                  f"{boundary_total} boundary cases with unchanged sentinels", flush=True)

        for body, status, diagnostic in (
            ("let mut data: [u8; 16] = [0; 16]; shake128(&data[..], &mut data[..]);",
             9, b"emprunt actif"),
            ("let data: [u8; 16] = [0; 16]; let out: [u8; 32] = [0; 32]; "
             "shake128(&data[..], &out[..]);", 8, b"type incompatible"),
        ):
            main.write_text(f"use std::crypto::sha3::shake128; fn main() {{ {body} }}")
            refused = subprocess.run(command, capture_output=True)
            if args.corboc:
                assert refused.returncode == status, refused
                if status == 8:
                    assert refused.stdout.splitlines()[:1] == [b"1"], refused
            else:
                assert refused.returncode != 0 and diagnostic in refused.stderr, refused
        print("Overlapping input and output and shared output were refused", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nist_zip", type=Path)
    parser.add_argument("--corboc", type=Path)
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    exercise(parser.parse_args())


if __name__ == "__main__":
    main()
