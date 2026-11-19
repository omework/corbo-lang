"""Check the caller-owned codecs and P-256 DER/PEM imports with either compiler."""

import argparse
import base64
import os
from pathlib import Path
import shlex
import subprocess
from tempfile import TemporaryDirectory
import time

from check_tls13_keys import FRONTEND, ROOT, binding


def run_case(args, root, source, label):
    (root / "src/main.crb").write_text(source)
    command = [FRONTEND, "emit-c", root]
    if args.corboc:
        command = [args.corboc.resolve(), "--emit-package-c", root, "--stdlib-dir", ROOT / "stdlib/src"]
    output = subprocess.run(command, capture_output=True)
    assert output.returncode == 0, (label, output.returncode, output.stderr, output.stdout[:400])
    generated = root / "case.c"
    exe = root / "case"
    generated.write_bytes(output.stdout)
    for mode, flags in (
        ("native", ["-O0"]),
        ("UBSan", ["-O2", "-fsanitize=undefined", "-fno-sanitize-recover=all"]),
    ):
        subprocess.run([*shlex.split(args.cc), "-std=c11", "-pthread", *flags, generated,
                        "-lm", "-o", exe], check=True)
        result = subprocess.run([exe], capture_output=True, timeout=30)
        assert result.returncode == 0 and not result.stderr, (label, mode, result.returncode, result.stderr)
        print(f"{mode}: {label}", flush=True)


def codec_source():
    code = ["""
use std::encoding::{hex, base64};
use std::encoding::hex::Error as HexError;
use std::encoding::base64::Error as Base64Error;
fn main() -> i32 {
    let mut buffer: [u8; 514] = [90; 514];
"""]
    return_code = 1
    for name, data in (("empty", b""), ("one", b"f"), ("two", b"fo"), ("three", b"foo"),
                       ("four", b"foob"), ("five", b"fooba"), ("six", b"foobar"),
                       ("all", bytes(range(256)))):
        code.append(binding(name, data))
        for module, expected in (("hex", data.hex().encode()), ("base64", base64.b64encode(data))):
            coded = module + "_" + name
            code.append(binding(coded, expected))
            code.append(f"""
buffer[{len(expected)}] = 90;
let n_{coded} = match {module}::encode(&{name}[..], &mut buffer[..]) {{
    Ok(value) => {{ value }}, Err(error) => {{ drop(error); return {return_code}; }},
}};
let v_{coded} = &buffer[..n_{coded}];
if n_{coded} != {len(expected)} || !v_{coded}.content_eq(&{coded}[..])
   || buffer[{len(expected)}] != 90 {{ return {return_code}; }}
buffer[{len(data)}] = 90;
let m_{coded} = match {module}::decode(&{coded}[..], &mut buffer[..]) {{
    Ok(value) => {{ value }}, Err(error) => {{ drop(error); return {return_code}; }},
}};
let w_{coded} = &buffer[..m_{coded}];
if m_{coded} != {len(data)} || !w_{coded}.content_eq(&{name}[..])
   || buffer[{len(data)}] != 90 {{ return {return_code}; }}
""")
            return_code += 1
    code.append(binding("upper", b"ABcd"))
    code.append("""
match hex::decode(&upper[..], &mut buffer[..]) {
    Ok(value) => { if value != 2 || buffer[0] != 171 || buffer[1] != 205 { return 17; } },
    Err(error) => { drop(error); return 17; },
};
""")
    failures = (
        ("hex", "decode", b"000", 8, "InvalidLength"),
        ("hex", "decode", b"00xx", 8, "InvalidCharacter"),
        ("hex", "decode", b"00ff", 1, "BufferTooSmall"),
        ("hex", "encode", b"aa", 3, "BufferTooSmall"),
        ("base64", "decode", b"Zg", 8, "InvalidLength"),
        ("base64", "decode", b"Zm9v Zg==", 8, "InvalidCharacter"),
        ("base64", "decode", b"Zm9v____", 8, "InvalidCharacter"),
        ("base64", "decode", b"Zm9v=AAA", 8, "InvalidPadding"),
        ("base64", "decode", b"Zm9vZg=A", 8, "InvalidPadding"),
        ("base64", "decode", b"Zm9vZh==", 8, "InvalidPadding"),
        ("base64", "decode", b"Zm9vZm9=", 8, "InvalidPadding"),
        ("base64", "decode", b"Zg==Zm9v", 8, "InvalidPadding"),
        ("base64", "decode", b"Zm9v", 2, "BufferTooSmall"),
        ("base64", "encode", b"foob", 7, "BufferTooSmall"),
    )
    for i, (module, method, invalid, size, variant) in enumerate(failures, 18):
        variants = ["BufferTooSmall", "InvalidLength", "InvalidCharacter"]
        kind = "HexError"
        if module == "base64":
            variants.append("InvalidPadding")
            kind = "Base64Error"
        arms = ", ".join(f"{kind}.{value} => {{ {'' if value == variant else f'return {i};'} }}" for value in variants)
        code.append(binding(f"bad_{i}", invalid))
        code.append(f"""
let mut sentinel_{i}: [u8; 8] = [90; 8];
match {module}::{method}(&bad_{i}[..], &mut sentinel_{i}[..{size}]) {{
    Ok(value) => {{ drop(value); return {i}; }},
    Err(error) => {{ match error {{ {arms}, }}; }},
}};
let mut index_{i}: usize = 0;
while index_{i} < 8 {{
    if sentinel_{i}[index_{i}] != 90 {{ return {i}; }}
    index_{i} = index_{i} + 1;
}}
""")
    return "\n".join(code) + "\n0\n}\n"


def openssl_fixtures(openssl, root):
    def run(*arguments, data=None):
        return subprocess.run([openssl, *arguments], input=data, capture_output=True, check=True).stdout

    pkcs8 = run("genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256")
    key = root / "private.pem"
    key.write_bytes(pkcs8)
    sec1 = run("ec", "-in", key)
    spki = run("pkey", "-in", key, "-pubout")
    certificate = run("req", "-x509", "-new", "-key", key, "-subj", "/CN=localhost", "-days", "2",
                      "-addext", "subjectAltName=DNS:localhost")
    pkcs8_der = run("pkcs8", "-topk8", "-nocrypt", "-in", key, "-outform", "DER")
    sec1_der = run("ec", "-in", key, "-outform", "DER")
    spki_der = run("pkey", "-in", key, "-pubout", "-outform", "DER")
    cert_der = run("x509", "-outform", "DER", data=certificate)
    encrypted = run("pkcs8", "-topk8", "-in", key, "-passout", "pass:temporary")
    wrong_curve = run("genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-384")
    return {
        "private_pem": pkcs8, "legacy_pem": sec1, "public_pem": spki, "cert_pem": certificate,
        "private_der": pkcs8_der, "legacy_der": sec1_der, "public_der": spki_der, "cert_der": cert_der,
        "private_crlf": pkcs8.replace(b"\n", b"\r\n"), "public_cr": spki.replace(b"\n", b"\r"),
        "encrypted_pem": encrypted, "wrong_curve": wrong_curve,
        "duplicated_pem": spki + spki, "wrong_label": pkcs8.replace(b"PRIVATE KEY", b"EC PRIVATE KEY"),
        "bad_public": spki.replace(b"-----END PUBLIC KEY-----", b"-----END PRIVATE KEY-----"),
        "bad_legacy_der": sec1_der[:-1] + bytes([sec1_der[-1] ^ 1]),
        "trailing_der": spki_der + b"\0",
    }


def pem_source(data, now):
    header = """
use std::crypto::p256::{SigningKey, PublicKey, Error as KeyError};
use std::crypto::x509::{Certificate, PublicKey as CertificateKey, CertificateError};

fn main() -> i32 {
    let mut scratch: [u8; 2048] = [90; 2048];
    let message: [u8; 4] = [84, 101, 115, 116];
    let name: [u8; 9] = [108,111,99,97,108,104,111,115,116];
    let mut signature: [u8; 72] = [0; 72];
"""
    code = [header, *[binding(name, value) for name, value in data.items()]]

    def take(name, call, rc):
        code.append(f"""let {name} = match {call} {{
            Ok(value) => {{ value }}, Err(error) => {{ drop(error); return {rc}; }},
        }};""")

    take("private_key", "SigningKey::from_pem(&private_pem[..], &mut scratch[..])", 1)
    code.append("let public = private_key.public_key(); let expected = public.to_sec1_uncompressed();")
    for i, (name, call) in enumerate((
        ("legacy", "SigningKey::from_pem(&legacy_pem[..], &mut scratch[..])"),
        ("crlf", "SigningKey::from_pem(&private_crlf[..], &mut scratch[..])"),
        ("pkcs8_der", "SigningKey::from_der(&private_der[..])"),
        ("sec1_der", "SigningKey::from_der(&legacy_der[..])"),
    ), 2):
        take(name, call, i)
        code.append(f"""let point_{name} = {name}.public_key();
        let bytes_{name} = point_{name}.to_sec1_uncompressed();
        let view_{name} = &bytes_{name}[..];
        if !view_{name}.content_eq(&expected[..]) {{ return {i}; }}""")
    for i, (name, call) in enumerate((
        ("spki_pem", "PublicKey::from_pem(&public_pem[..], &mut scratch[..])"),
        ("spki_cr", "PublicKey::from_pem(&public_cr[..], &mut scratch[..])"),
        ("spki_der", "PublicKey::from_der(&public_der[..])"),
    ), 6):
        take(name, call, i)
        code.append(f"""let bytes_{name} = {name}.to_sec1_uncompressed();
        let view_{name} = &bytes_{name}[..];
        if !view_{name}.content_eq(&expected[..]) {{ return {i}; }}""")

    take("cert", f"Certificate::from_pem(&cert_pem[..], &mut scratch[..], {now})", 9)
    take("cert_key", "cert.public_key()", 10)
    code.append("""let cert_len = cert.der_len();
    let decoded_cert = &scratch[..cert_len];
    if !decoded_cert.content_eq(&cert_der[..]) { return 11; }""")
    take("cert_name", "cert.matches_dns_name(&scratch[..cert_len], &name[..])", 11)
    code.append("if !cert_name { return 11; }")
    take("wrapped_key", "CertificateKey::from_pem(&public_pem[..], &mut scratch[..])", 12)
    take("wrapped_der", "CertificateKey::from_der(&public_der[..])", 13)
    take("used", "private_key.sign_sha256(&message[..], &mut signature)", 14)
    for i, key in enumerate(("cert_key", "wrapped_key", "wrapped_der"), 15):
        take(f"ok_{i}", f"{key}.verify_ecdsa_sha256(&message[..], &signature[..used])", i)
        code.append(f"if !ok_{i} {{ return {i}; }}")

    for i, call in enumerate((
        "SigningKey::from_pem(&encrypted_pem[..], &mut scratch[..])",
        "SigningKey::from_pem(&wrong_curve[..], &mut scratch[..])",
        "SigningKey::from_pem(&wrong_label[..], &mut scratch[..])",
        "SigningKey::from_der(&bad_legacy_der[..])",
        "PublicKey::from_pem(&duplicated_pem[..], &mut scratch[..])",
        "PublicKey::from_pem(&bad_public[..], &mut scratch[..])",
        "PublicKey::from_der(&trailing_der[..])",
        f"Certificate::from_pem(&public_pem[..], &mut scratch[..], {now})",
        f"Certificate::from_pem(&cert_pem[..], &mut scratch[..], {now + 3 * 86400})",
    ), 18):
        code.append(f"""match {call} {{
            Ok(value) => {{ drop(value); return {i}; }}, Err(error) => {{ drop(error); }},
        }};""")
    code.append("""
let mut tiny: [u8; 2] = [90; 2];
match SigningKey::from_pem(&private_pem[..], &mut tiny[..]) {
    Ok(key) => { drop(key); return 27; },
    Err(error) => {
        match error {
            KeyError.BufferTooSmall => {},
            KeyError.RandomFailed => { return 27; },
            KeyError.InvalidPrivateKey => { return 27; },
            KeyError.InvalidPublicKey => { return 27; },
            KeyError.InvalidSignature => { return 27; },
            KeyError.InputTooLong => { return 27; },
        };
    },
};
if tiny[0] != 90 || tiny[1] != 90 { return 28; }
0
}
""")
    return "\n".join(code)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--corboc", type=Path)
    cli.add_argument("--cc", default=os.environ.get("CC", "cc"))
    cli.add_argument("--openssl", default="openssl")
    args = cli.parse_args()
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "src").mkdir()
        (root / "package.toml").write_text('[package]\nname = "encoding_tests"\n')
        run_case(args, root, codec_source(), "Hex and Base64 vectors, invalid inputs and buffer sentinels")
        data = openssl_fixtures(args.openssl, root)
        run_case(args, root, pem_source(data, int(time.time()) + 1), "OpenSSL P-256 keys and X.509 DER/PEM imports")


if __name__ == "__main__":
    main()
