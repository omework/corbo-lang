# SPDX-License-Identifier: MIT OR Apache-2.0
"""Compare MD5 and PBKDF2 with hashlib and P-256/X.509 serialization with OpenSSL."""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import time

from check_encoding_pem import FRONTEND, ROOT, binding, openssl_fixtures, run_case


def hash_source():
    source = ["""
use std::crypto::md5::{Md5, digest};
use std::crypto::pbkdf2::{derive_sha256, Error as KdfError};

fn check_md5(data: &[u8], expected: &[u8]) -> bool {
    let size = data.len();
    let digest_bytes = digest(&data[0..size]);
    let direct = &digest_bytes[..];
    if !direct.content_eq(&expected[0..expected.len()]) { return false; }

    let mut hash = Md5::new();
    hash.update(&data[0..0]);
    let mut at: usize = 0;
    while at < size {
        let next = if size - at < 17 { copy(size) } else { at + 17 };
        hash.update(&data[at..next]);
        at = next;
    }
    let streamed = hash.finish();
    let view = &streamed[..];
    view.content_eq(&expected[0..expected.len()])
}

fn main() -> i32 {
"""]
    vectors = [
        (b"", "d41d8cd98f00b204e9800998ecf8427e"),
        (b"a", "0cc175b9c0f1b6a831c399e269772661"),
        (b"abc", "900150983cd24fb0d6963f7d28e17f72"),
        (b"message digest", "f96b697d7cb7938d525a2f31aaf161d0"),
        (b"abcdefghijklmnopqrstuvwxyz", "c3fcd3d76192e4007dfb496cca67e13b"),
        (b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", "d174ab98d277d9f5a5611c2c9f419d9f"),
        (b"1234567890" * 8, "57edf4a22be3c955ac49da2e2107b67a"),
    ]
    for size in (55, 56, 57, 63, 64, 65, 127, 128, 129):
        data = bytes(range(size))
        vectors.append((data, hashlib.md5(data, usedforsecurity=False).hexdigest()))
    for i, (data, digest) in enumerate(vectors, 1):
        source.extend([
            binding(f"input_{i}", data),
            binding(f"digest_{i}", bytes.fromhex(digest)),
            f"if !check_md5(&input_{i}[..], &digest_{i}[..]) {{ return {i}; }}",
        ])

    cases = [
        (b"passwd", b"salt", 1, 64),
        (b"password", b"salt", 2, 32),
        (b"", b"", 19, 1),
        (b"p\0ass\0word", b"sa\0lt", 4096, 49),
        (bytes(range(100)), bytes(range(78)), 3, 97),
        (b"password", b"salt", 1, 8193),
    ]
    for i, (password, salt, rounds, size) in enumerate(cases, 20):
        result = hashlib.pbkdf2_hmac("sha256", password, salt, rounds, size)
        if i == 20:
            assert result.hex() == (
                "55ac046e56e3089fec1691c22544b605f94185216dde0465e68b9d57c20dacbc"
                "49ca9cccf179b645991664b39d77ef317c71b845b1e30bd509112041d3a19783"
            )
        tail = max(0, size - 65)
        source.extend([
            binding(f"password_{i}", password),
            binding(f"salt_{i}", salt),
            binding(f"expected_{i}", result[tail:]),
            f"""
let mut result_{i}: [u8; {size + 1}] = [90; {size + 1}];
match derive_sha256(&password_{i}[..], &salt_{i}[..], {rounds}, &mut result_{i}[..{size}]) {{
    Ok(()) => {{}}, Err(error) => {{ drop(error); return {i}; }},
}};
let result_view_{i} = &result_{i}[..];
let actual_{i} = &result_view_{i}[{tail}..{size}];
if !actual_{i}.content_eq(&expected_{i}[..]) || result_{i}[{size}] != 90 {{ return {i}; }}
""",
        ])

    source.append("""
let mut sentinel: [u8; 4] = [90; 4];
match derive_sha256(&input_1[..], &input_1[..], 0, &mut sentinel[..]) {
    Ok(()) => { return 26; },
    Err(error) => {
        match error {
            KdfError.InvalidIterations => {},
            KdfError.InvalidOutputLength => { return 26; },
            KdfError.InputTooLong => { return 26; },
        };
    },
};
match derive_sha256(&input_1[..], &input_1[..], 1, &mut sentinel[..0]) {
    Ok(()) => { return 27; },
    Err(error) => {
        match error {
            KdfError.InvalidOutputLength => {},
            KdfError.InvalidIterations => { return 27; },
            KdfError.InputTooLong => { return 27; },
        };
    },
};
let unchanged = &sentinel[..];
let expected: [u8; 4] = [90; 4];
if !unchanged.content_eq(&expected[..]) { return 28; }
0
}
""")
    return "\n".join(source)


def serialization_source(fixtures, now):
    source = ["""
use std::crypto::p256::{SigningKey, PublicKey, Error as KeyError};
use std::crypto::x509::{Certificate, CertificateError};
use std::encoding::pem::{encode, Error as PemError};

fn main() -> i32 {
    let mut output: [u8; 2048] = [90; 2048];
"""]
    for label in ("private_der", "legacy_der", "public_der", "cert_der",
                  "private_pem", "legacy_pem", "public_pem", "cert_pem"):
        source.append(binding(label, fixtures[label]))
    source.extend([
        binding("bad_label", b"X\n-----END PRIVATE KEY"),
        binding("wrong_cert", bytes([0]) + fixtures["cert_der"][1:]),
    ])

    def take(name, expr, status):
        source.append(f"""
let {name} = match {expr} {{
    Ok(value) => {{ value }}, Err(error) => {{ drop(error); return {status}; }},
}};
""")

    take("private_key", "SigningKey::from_der(&private_der[..])", 1)
    take("public_key", "PublicKey::from_der(&public_der[..])", 2)
    take("cert", f"Certificate::from_der(&cert_der[..], {now})", 3)
    take("wrapped_key", "cert.public_key()", 4)

    for i, (expr, reference) in enumerate([
        ("private_key.to_der", "private_der"),
        ("private_key.to_sec1_der", "legacy_der"),
        ("private_key.to_pem", "private_pem"),
        ("private_key.to_sec1_pem", "legacy_pem"),
        ("public_key.to_der", "public_der"),
        ("public_key.to_pem", "public_pem"),
        ("wrapped_key.to_der", "public_der"),
        ("wrapped_key.to_pem", "public_pem"),
        ("cert.to_der", "cert_der"),
        ("cert.to_pem", "cert_pem"),
    ], 5):
        size = len(fixtures[reference])
        input_argument = "&cert_der[..], " if expr.startswith("cert.") else ""
        source.append(f"output[{size}] = 90;")
        take(f"length_{i}", f"{expr}({input_argument}&mut output[..{size}])", i)
        source.append(f"""
let view_{i} = &output[..length_{i}];
if length_{i} != {size} || !view_{i}.content_eq(&{reference}[..]) || output[{size}] != 90 {{
    return {i};
}}
""")

    failures = [
        ("private_key.to_der(&mut tiny[..])", "KeyError.BufferTooSmall"),
        ("private_key.to_sec1_der(&mut tiny[..])", "KeyError.BufferTooSmall"),
        ("private_key.to_pem(&mut tiny[..])", "KeyError.BufferTooSmall"),
        ("private_key.to_sec1_pem(&mut tiny[..])", "KeyError.BufferTooSmall"),
        ("public_key.to_der(&mut tiny[..])", "KeyError.BufferTooSmall"),
        ("public_key.to_pem(&mut tiny[..])", "KeyError.BufferTooSmall"),
        ("cert.to_der(&cert_der[..], &mut tiny[..])", "CertificateError.BufferTooSmall"),
        ("cert.to_pem(&cert_der[..], &mut tiny[..])", "CertificateError.BufferTooSmall"),
        ("cert.to_der(&wrong_cert[..], &mut tiny[..])", "CertificateError.InvalidCertificate"),
        ("cert.to_pem(&wrong_cert[..], &mut tiny[..])", "CertificateError.InvalidCertificate"),
        ("encode(&public_der[..], &bad_label[..], &mut tiny[..])", "PemError.InvalidEnvelope"),
    ]
    source.append("let mut tiny: [u8; 16] = [90; 16];")
    error_variants = {
        "KeyError": ["BufferTooSmall", "RandomFailed", "InvalidPrivateKey", "InvalidPublicKey",
                     "InvalidSignature", "InputTooLong"],
        "CertificateError": ["BufferTooSmall", "InvalidCertificate", "InvalidTime",
                             "WrongUsage", "UntrustedChain", "NameMismatch"],
        "PemError": ["InvalidEnvelope", "InvalidBase64", "BufferTooSmall"],
    }
    for i, (call, error) in enumerate(failures, 15):
        error_type, expected = error.split(".")
        arms = ", ".join(f"{error_type}.{variant} => {{}}" if variant == expected
                         else f"{error_type}.{variant} => {{ return {i}; }}"
                         for variant in error_variants[error_type])
        source.append(f"""
match {call} {{
    Ok(written) => {{ drop(written); return {i}; }},
    Err(error) => {{
        match error {{ {arms}, }};
    }},
}};
""")
    source.append("""
let sentinel = &tiny[..];
let expected: [u8; 16] = [90; 16];
if !sentinel.content_eq(&expected[..]) { return 26; }
0
}
""")
    return "\n".join(source)


def standalone_key_source():
    return """
use std::crypto::p256::SigningKey;
fn main() -> i32 {
    let scalar: [u8; 32] = [1; 32];
    let mut buffer: [u8; 138] = [0; 138];
    let key = match SigningKey::from_bytes(&scalar) {
        Ok(value) => { value }, Err(error) => { drop(error); return 1; },
    };
    let size = match key.to_der(&mut buffer[..]) {
        Ok(value) => { value }, Err(error) => { drop(error); return 2; },
    };
    match SigningKey::from_der(&buffer[..size]) {
        Ok(value) => { drop(value); 0 }, Err(error) => { drop(error); 3 },
    }
}
"""


def refuse_private_md5_layout(args, root):
    (root / "src/main.crb").write_text("""
use std::crypto::md5::Md5;
fn main() {
    let invalid = Md5 { state: [0; 4], block: [0; 64], bytes: 0 };
    drop(invalid);
}
""")
    command = [FRONTEND, "check", root]
    if args.corboc:
        command = [args.corboc.resolve(), "--emit-package-c", root, "--stdlib-dir", ROOT / "stdlib/src"]
    outcome = subprocess.run(command, capture_output=True)
    if args.corboc:
        assert outcome.returncode == 8 and outcome.stdout.splitlines()[:1] == [b"1"], outcome
    else:
        assert outcome.returncode == 1 and "représentation privée" in outcome.stderr.decode(), outcome
    print("Private MD5 state rejected", flush=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--corboc", type=Path)
    cli.add_argument("--cc", default=os.environ.get("CC", "cc"))
    cli.add_argument("--openssl", default="openssl")
    args = cli.parse_args()
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "src").mkdir()
        (root / "package.toml").write_text('[package]\nname = "crypto_serialization_tests"\n')
        run_case(args, root, hash_source(), "MD5 and PBKDF2-HMAC-SHA-256")
        fixtures = openssl_fixtures(args.openssl, root)
        run_case(args, root, serialization_source(fixtures, int(time.time()) + 1),
                 "P-256 and X.509 DER/PEM serialization against OpenSSL")
        run_case(args, root, standalone_key_source(), "P-256 key round trip without an X.509 import")
        refuse_private_md5_layout(args, root)


if __name__ == "__main__":
    main()
