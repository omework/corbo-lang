"""Exercise native P-256 against RFC vectors with either Din compiler."""

import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"
LIBRARY = ROOT / "stdlib/src/crypto/p256"

# RFC 5903 §8.1
INITIATOR = "C88F01F510D9AC3F70A292DAA2316DE544E9AAB8AFE84049C62A9C57862D1433"
RESPONDER = "C6EF9C5D78AE012A011164ACB397CE2088685D8F06BF9BE0B283AB46476BEE53"
INITIATOR_POINT = ("04DAD0B65394221CF9B051E1FECA5787D098DFE637FC90B9EF945D0C3772581180"
                   "5271A0461CDB8252D61F1C456FA3E59AB1F45B33ACCF5F58389E0577B8990BB3")
RESPONDER_POINT = ("04D12DFB5289C8D4F81208B70270398C342296970A0BCCB74C736FC7554494BF63"
                   "56FBF3CA366CC23E8157854C13C58D6AAC23F046ADA30F8353E74F33039872AB")
SHARED = "D6840F6B42F6EDAFD13116E0E12565202FEF8E9ECE7DCE03812464D04B9442DE"

# RFC 6979 Appendix A.2.5, SHA-256.
SIGNING = "C9AFA9D845BA75166B5C215767B1D6934E50C3DB36E89B127B8A622B120F6721"
SIGNING_POINT = ("0460FED4BA255A9D31C961EB74C6356D68C049B8923B61FA6CE669622E60F29FB6"
                 "7903FE1008B8BC99A41AE9E95628BC64F2F1B20C2D7E9F5177A3C294D4462299")
ORDER = "FFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551"
PRIME = "FFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF"
SAMPLE_DER = ("3046022100EFD48B2AACB6A8FD1140DD9CD45E81D69D2C877B56AAF991C34D0EA84EAF3716"
              "022100F7CB1C942D657C41D436C7A1B6E29F65F3E900DBB9AFF4064DC4AB2F843ACDA8")
TEST_DER = ("3045022100F1ABB023518351CD71D881567B1EA663ED3EFCF6C5132B354F28D3B0B7D38367"
            "0220019F4113742A2B14BD25926B49C649155F267E60D3814B4C0CC84250E46F0083")


def array(name, hex_string):
    data = bytes.fromhex(hex_string)
    return f"let {name}: [u8; {len(data)}] = [{', '.join(map(str, data))}];"


# The key import is private so a caller cannot create an EphemeralKey
# from fixed bytes. Use a test copy of the module for this RFC witness.
ECDHE = """
pub fn rfc_ecdh() -> Result<bool, Error> {
    INITIATOR_BYTES
    RESPONDER_BYTES
    INITIATOR_PUBLIC
    RESPONDER_PUBLIC
    SHARED_BYTES
    let initiator = match ephemeral_from_bytes(&di[..]) {
        Ok(key) => { key },
        Err(error) => { return Err(error); },
    };
    let responder = match ephemeral_from_bytes(&dr[..]) {
        Ok(key) => { key },
        Err(error) => { return Err(error); },
    };
    let initiator_pub = initiator.public_key();
    let responder_pub = responder.public_key();
    let initiator_encoded = initiator_pub.to_sec1_uncompressed();
    let responder_encoded = responder_pub.to_sec1_uncompressed();
    let ie = &initiator_encoded[..];
    if !ie.content_eq(&qi[..]) { return Ok(false); }
    let re = &responder_encoded[..];
    if !re.content_eq(&qr[..]) { return Ok(false); }
    let mut from_initiator: [u8; 32] = [0; 32];
    let mut from_responder: [u8; 32] = [0; 32];
    match initiator.agree(&responder_pub, &mut from_initiator) {
        Ok(()) => {},
        Err(error) => { return Err(error); },
    };
    match responder.agree(&initiator_pub, &mut from_responder) {
        Ok(()) => {},
        Err(error) => { return Err(error); },
    };
    let first = &from_initiator[..];
    let second = &from_responder[..];
    Ok(first.content_eq(&expected[..]) && second.content_eq(&expected[..]))
}
"""
for marker, name, value in (
    ("INITIATOR_BYTES", "di", INITIATOR), ("RESPONDER_BYTES", "dr", RESPONDER),
    ("INITIATOR_PUBLIC", "qi", INITIATOR_POINT), ("RESPONDER_PUBLIC", "qr", RESPONDER_POINT),
    ("SHARED_BYTES", "expected", SHARED),
):
    ECDHE = ECDHE.replace(marker, array(name, value))
PUBLIC_WITNESS = """
use std::crypto::p256::{EphemeralKey, SigningKey, PublicKey, Error, verify_sha256};

fn check_signature(key: &SigningKey, public_key: &PublicKey, message: &[u8],
                   expected: &[u8]) -> bool {
    let mut buffer: [u8; 72] = [90; 72];
    let size = message.len();
    let used = match key.sign_sha256(&message[0..size], &mut buffer) {
        Ok(count) => { count },
        Err(error) => { drop(error); return false; },
    };
    if used != expected.len() { return false; }
    if used < 72 && buffer[used] != 90 { return false; }
    let actual = &buffer[..used];
    if !actual.content_eq(&expected[0..used]) { return false; }
    match verify_sha256(public_key, &message[0..size], &expected[0..used]) {
        Ok(valid) => { valid },
        Err(error) => { drop(error); false },
    }
}

fn rejects_point(bytes: &[u8]) -> bool {
    let size = bytes.len();
    match PublicKey::from_sec1_uncompressed(&bytes[0..size]) {
        Ok(key) => { drop(key); false },
        Err(error) => {
            match error {
                Error.InvalidPublicKey => { true },
                Error.InvalidPrivateKey => { false },
                Error.InvalidSignature => { false },
                Error.InputTooLong => { false },
                Error.RandomFailed => { false },
                Error.BufferTooSmall => { false },
            }
        },
    }
}

fn rejects_scalar(bytes: &[u8; 32]) -> bool {
    let mut raw: [u8; 32] = [0; 32];
    let mut i: usize = 0;
    while i < 32 { raw[i] = (*bytes)[i]; i = i + 1; }
    match SigningKey::from_bytes(&raw) {
        Ok(key) => { drop(key); false },
        Err(error) => {
            match error {
                Error.InvalidPrivateKey => { true },
                Error.InvalidPublicKey => { false },
                Error.InvalidSignature => { false },
                Error.InputTooLong => { false },
                Error.RandomFailed => { false },
                Error.BufferTooSmall => { false },
            }
        },
    }
}

fn rejects_signature(key: &PublicKey, bytes: &[u8]) -> bool {
    let message: [u8; 6] = [115, 97, 109, 112, 108, 101];
    let size = bytes.len();
    match verify_sha256(key, &message[..], &bytes[0..size]) {
        Ok(valid) => { drop(valid); false },
        Err(error) => {
            match error {
                Error.InvalidSignature => { true },
                Error.InvalidPublicKey => { false },
                Error.InvalidPrivateKey => { false },
                Error.InputTooLong => { false },
                Error.RandomFailed => { false },
                Error.BufferTooSmall => { false },
            }
        },
    }
}

fn generated_agreement() -> bool {
    let a = match EphemeralKey::generate() {
        Ok(key) => { key },
        Err(error) => { drop(error); return false; },
    };
    let b = match EphemeralKey::generate() {
        Ok(key) => { key },
        Err(error) => { drop(error); return false; },
    };
    let ap = a.public_key();
    let bp = b.public_key();
    let bytes = ap.to_sec1_uncompressed();
    let imported = match PublicKey::from_sec1_uncompressed(&bytes[..]) {
        Ok(key) => { key },
        Err(error) => { drop(error); return false; },
    };
    let mut ab: [u8; 32] = [0; 32];
    let mut ba: [u8; 32] = [0; 32];
    match a.agree(&bp, &mut ab) {
        Ok(()) => {},
        Err(error) => { drop(error); return false; },
    };
    match b.agree(&imported, &mut ba) {
        Ok(()) => {},
        Err(error) => { drop(error); return false; },
    };
    let left = &ab[..];
    left.content_eq(&ba[..])
}

fn generated_signature() -> bool {
    let key = match SigningKey::generate() {
        Ok(key) => { key },
        Err(error) => { drop(error); return false; },
    };
    let public_key = key.public_key();
    let empty: [u8; 0] = [];
    let mut output: [u8; 72] = [0; 72];
    let size = match key.sign_sha256(&empty[..], &mut output) {
        Ok(used) => { used },
        Err(error) => { drop(error); return false; },
    };
    match verify_sha256(&public_key, &empty[..], &output[..size]) {
        Ok(valid) => { valid },
        Err(error) => { drop(error); false },
    }
}
"""


def public_witness():
    cases = []
    statements = [array("d", SIGNING), array("q", SIGNING_POINT),
                  array("sample", b"sample".hex()), array("test", b"test".hex()),
                  array("sample_der", SAMPLE_DER), array("test_der", TEST_DER), """
    let key = match SigningKey::from_bytes(&d) {
        Ok(key) => { key },
        Err(error) => { drop(error); print(0); return 1; },
    };
    let public_key = match PublicKey::from_sec1_uncompressed(&q[..]) {
        Ok(key) => { key },
        Err(error) => { drop(error); print(0); return 1; },
    };
    let derived = key.public_key();
    let sec1 = derived.to_sec1_uncompressed();
    let roundtrip = public_key.to_sec1_uncompressed();
    let original = &q[..];
    """]
    def record(label, expression):
        cases.append(label)
        statements.append(f"if {expression} {{ print({len(cases)}); }} else {{ print(0); }}")

    record("SEC1 byte-exact derivation and roundtrip", "original.content_eq(&sec1[..]) && original.content_eq(&roundtrip[..])")
    record("RFC 6979 sample (two DER sign-padding bytes)", "check_signature(&key, &public_key, &sample[..], &sample_der[..])")
    record("RFC 6979 test (one DER sign-padding byte)", "check_signature(&key, &public_key, &test[..], &test_der[..])")
    statements.append("""
    let wrong = match verify_sha256(&public_key, &test[..], &sample_der[..]) {
        Ok(valid) => { !valid },
        Err(error) => { drop(error); false },
    };
    """)
    record("valid DER over a different message returns false", "wrong")
    points = {
        "infinity": "00", "compressed": "02" + SIGNING_POINT[2:66],
        "truncated point": SIGNING_POINT[:-2], "trailing point byte": SIGNING_POINT + "00",
        "wrong SEC1 prefix": "06" + SIGNING_POINT[2:], "off-curve point": SIGNING_POINT[:-2] + "98",
        "x equals field modulus": "04" + PRIME + SIGNING_POINT[66:],
        "y equals field modulus": SIGNING_POINT[:66] + PRIME,
    }
    for i, (label, data) in enumerate(points.items()):
        statements.append(array(f"point_{i}", data))
        record(label, f"rejects_point(&point_{i}[..])")
    for i, (label, data) in enumerate((("zero scalar", "00" * 32), ("scalar equals group order", ORDER))):
        statements.append(array(f"scalar_{i}", data))
        record(label, f"rejects_scalar(&scalar_{i})")
    signatures = {
        "truncated DER": SAMPLE_DER[:-2], "trailing DER byte": SAMPLE_DER + "00",
        "wrong sequence tag": "31" + SAMPLE_DER[2:],
        "wrong INTEGER tag": SAMPLE_DER[:4] + "03" + SAMPLE_DER[6:],
        "negative INTEGER": "30450220" + SAMPLE_DER[10:],
        "nonminimal INTEGER": "300702020001020101",
        "zero INTEGER": "3006020100020101",
        "zero-length INTEGER": "3006020002020001",
        "long-form DER length": "308106020101020101",
        "r equal to order": "3026022100" + ORDER + "020101",
        "s equal to order": "3026020101022100" + ORDER,
    }
    for i, (label, data) in enumerate(signatures.items()):
        statements.append(array(f"signature_{i}", data))
        record(label, f"rejects_signature(&public_key, &signature_{i}[..])")
    record("OS-generated ECDHE keys agree", "generated_agreement()")
    record("OS-generated signing key signs and verifies", "generated_signature()")
    return PUBLIC_WITNESS + "\nfn main() -> i32 {\n" + "\n".join(statements) + "\n    0\n}\n", cases


def execute(command, package, cc, cases):
    emitted = subprocess.run(command, capture_output=True)
    assert emitted.returncode == 0, (emitted.returncode, emitted.stderr, emitted.stdout[:400])
    code = package / "witness.c"
    binary = package / "witness"
    code.write_bytes(emitted.stdout)
    for mode, flags in (
        ("native", ["-O0"]),
        ("UBSan", ["-O2", "-fsanitize=undefined", "-fno-sanitize-recover=all"]),
    ):
        subprocess.run([*shlex.split(cc), "-std=c11", "-pthread", *flags, code, "-lm",
                        "-o", binary], check=True)
        result = subprocess.run([binary], capture_output=True, check=True, timeout=90)
        assert not result.stderr, result.stderr
        results = list(map(int, result.stdout.splitlines()))
        assert results == list(range(1, len(cases) + 1)), (
            mode, results, [label for i, label in enumerate(cases, 1) if i not in results])
        count = "1 check" if len(cases) == 1 else f"{len(cases)} checks"
        print(f"{mode}: {count} passed ({cases[0]})", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corboc", type=Path)
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    args = parser.parse_args()
    with TemporaryDirectory() as work:
        package = Path(work)
        source = package / "src"
        source.mkdir()
        (package / "package.toml").write_text('[package]\nname = "p256_tests"\n')
        main_path = source / "main.crb"
        command = [FRONTEND, "emit-c", package]
        if args.corboc:
            command = [args.corboc.resolve(), "--emit-package-c", package, "--stdlib-dir", ROOT / "stdlib/src"]
        witness, labels = public_witness()
        main_path.write_text(witness)
        execute(command, package, args.cc, labels)
        main_path.write_text("""
use p256_tests::case::rfc_ecdh;
fn main() {
    match rfc_ecdh() {
        Ok(valid) => { if valid { print(1); } else { print(0); } },
        Err(error) => { drop(error); print(0); },
    };
}
""")
        copied = source / "case"
        shutil.copytree(LIBRARY, copied)
        with (copied / "p256.crb").open("a") as module:
            module.write(ECDHE)
        execute(command, package, args.cc, ["RFC 5903 public keys and shared secret in both directions"])
        shutil.rmtree(copied)

        for name, field, size in (("EphemeralKey", "secret", 8), ("SigningKey", "secret", 8),
                                   ("PublicKey", "point", 24)):
            for construct in (
                f"let forged = {name} {{ {field}: [0; {size}] }};",
                f"let mut keys = pool<{name}>(1); let forged = keys.new();",
            ):
                main_path.write_text(f"use std::crypto::p256::{name};\n"
                                     f"fn main() {{ {construct} drop(forged); }}\n")
                refused = subprocess.run(command, capture_output=True)
                if args.corboc:
                    assert refused.returncode == 8 and b"private field" in refused.stderr, refused
                else:
                    assert refused.returncode != 0 and b"priv" in refused.stderr, refused
        print("Private layouts: direct construction and pool defaults refused", flush=True)


if __name__ == "__main__":
    main()
