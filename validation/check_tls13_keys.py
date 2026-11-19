"""Replay the RFC 8448 §3 TLS 1.3 key schedule with either Din compiler."""

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import shlex
import subprocess
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"
FIXTURE = ROOT / "validation/fixtures/tls13-rfc8448-section3.json"

IMPORTS = """
use std::net::tls::keys::{Transcript, Traffic, KeyError, early_secret, derived_secret,
    handshake_secret, master_secret, traffic_secret, aes128_key, traffic_iv, derive_secret,
    finished_key, finished_verify_data, verify_finished, hkdf_expand_label};
use std::crypto::sha256::digest;

fn emit(bytes: &[u8]) {
    let mut i: usize = 0;
    while i < bytes.len() {
        print(bytes[i]);
        i = i + 1;
    }
}

fn verify_reject(result: Result<(), KeyError>, expected: u8) -> bool {
    match result {
        Ok(()) => { false },
        Err(error) => {
            match error {
                KeyError.InvalidLabel => { expected == 1 },
                KeyError.InvalidContext => { expected == 2 },
                KeyError.InvalidSecret => { expected == 3 },
                KeyError.OutputTooLong => { expected == 4 },
                KeyError.HashFailed => { false },
            }
        },
    }
}

fn check_sentinel(bytes: &[u8]) -> bool {
    let mut i: usize = 0;
    while i < bytes.len() {
        if bytes[i] != 90 { return false; }
        i = i + 1;
    }
    true
}
"""


def binding(name, value):
    return f"let {name}: [u8; {len(value)}] = [{', '.join(map(str, value))}];"


def expand_reference(secret, label, context, length):
    full_label = b"tls13 " + label
    info = length.to_bytes(2, "big") + bytes([len(full_label)]) + full_label
    info += bytes([len(context)]) + context
    last = b""
    output = bytearray()
    for counter in range(1, (length + 31) // 32 + 1):
        last = hmac.digest(secret, last + info + bytes([counter]), "sha256")
        output.extend(last)
    return bytes(output[:length])


def witness(trace):
    code = ["fn main() -> i32 {", "let mut transcript = Transcript::new();"]
    checks = []

    def data(name, value=None):
        code.append(binding(name, trace[name] if value is None else value))

    def take(name, expression):
        code.append(f"""let {name} = match {expression} {{
            Ok(value) => {{ value }},
            Err(error) => {{ drop(error); return 1; }},
        }};""")

    def checked_update(expression):
        code.append(f"""match {expression} {{
            Ok(()) => {{}},
            Err(error) => {{ drop(error); return 2; }},
        }};""")

    def check(name, expression, expected=None, result=True):
        if result:
            take(name, expression)
        else:
            code.append(f"let {name} = {expression};")
        code.append(f"emit(&{name}[..]);")
        checks.append((name, trace[name] if expected is None else expected))

    def flag(name, condition):
        code.append(f"if {condition} {{ print(1); }} else {{ print(0); }}")
        checks.append((name, b"\x01"))

    def append(name, split=None):
        data(name)
        parts = [f"&{name}[..]"]
        if split is not None:
            code.append(f"let {name}_view = &{name}[..];")
            parts = [f"&{name}_view[0..{split}]", f"&{name}_view[{split}..{len(trace[name])}]"]
        for part in parts:
            checked_update(f"transcript.append({part})")

    check("empty_hash", "transcript.digest()", result=False)
    check("early", "early_secret()")
    check("early_derived", "derived_secret(&early[..])")
    data("shared")
    append("client_hello", split=3)
    append("server_hello")
    check("hello_hash", "transcript.digest()", result=False)
    check("handshake", "handshake_secret(&early[..], &shared[..])")
    for side in ("client", "server"):
        check(f"{side}_hs_traffic",
              f"traffic_secret(&handshake[..], &hello_hash[..], Traffic.{side.title()}Handshake)")
        check(f"{side}_hs_key", f"aes128_key(&{side}_hs_traffic[..])")
        check(f"{side}_hs_iv", f"traffic_iv(&{side}_hs_traffic[..])")
    check("handshake_derived", "derived_secret(&handshake[..])")
    check("master", "master_secret(&handshake[..])")

    append("encrypted_extensions")
    append("certificate", split=64)
    append("certificate_verify")
    handshake_messages = ("client_hello", "server_hello", "encrypted_extensions", "certificate",
                          "certificate_verify")
    before_server = hashlib.sha256(b"".join(trace[name] for name in handshake_messages)).digest()
    check("before_server_finished", "transcript.digest()", before_server, result=False)

    for side, snapshot in (("server", "before_server_finished"), ("client", "server_finished_hash")):
        check(f"{side}_finished_key", f"finished_key(&{side}_hs_traffic[..])")
        check(f"{side}_finished_data", f"finished_verify_data(&{side}_hs_traffic[..], &{snapshot}[..])")
        # Verify bytes from the published message, independent of the generated tag.
        data(f"{side}_expected", trace[f"{side}_finished_data"])
        take(f"{side}_valid", f"verify_finished(&{side}_hs_traffic[..], &{snapshot}[..], &{side}_expected[..])")
        flag(f"{side}_finished_accepted", f"{side}_valid")
        if side == "server":
            for suffix, index in (("first", 0), ("last", 31)):
                damaged = bytearray(trace["server_finished_data"])
                damaged[index] ^= 1
                data(f"damaged_{suffix}", damaged)
                take(f"verified_{suffix}", f"verify_finished(&server_hs_traffic[..], &{snapshot}[..], &damaged_{suffix}[..])")
                flag(f"changed_{suffix}_byte_rejected", f"!verified_{suffix}")
            take("short_verified", f"verify_finished(&server_hs_traffic[..], &{snapshot}[..], &server_expected[..31])")
            flag("short_finished_rejected", "!short_verified")
        append(f"{side}_finished_message")
        check(f"{side}_finished_hash", "transcript.digest()", result=False)

    for side in ("client", "server"):
        check(f"{side}_ap_traffic",
              f"traffic_secret(&master[..], &server_finished_hash[..], Traffic.{side.title()}Application)")
        check(f"{side}_ap_key", f"aes128_key(&{side}_ap_traffic[..])")
        check(f"{side}_ap_iv", f"traffic_iv(&{side}_ap_traffic[..])")
    for name, label, snapshot in (
        ("exporter_master", b"exp master", "server_finished_hash"),
        ("resumption_master", b"res master", "client_finished_hash"),
    ):
        data(f"{name}_label", label)
        check(name, f"derive_secret(&master[..], &{name}_label[..], &{snapshot}[..])")
    data("ticket_label", b"resumption")
    data("ticket_nonce", bytes(2))
    code.append("let mut ticket_psk: [u8; 32] = [0; 32];")
    checked_update("hkdf_expand_label(&resumption_master[..], &ticket_label[..], &ticket_nonce[..], &mut ticket_psk[..])")
    code.append("emit(&ticket_psk[..]);")
    checks.append(("ticket_psk", trace["ticket_psk"]))

    label, context = bytes(range(249)), bytes(range(255))
    data("long_label", label)
    data("long_context", context)
    code.append("let mut large: [u8; 8161] = [90; 8161];")
    for size in (0, 256, 8160):
        checked_update(f"hkdf_expand_label(&master[..], &long_label[..], &long_context[..], &mut large[..{size}])")
        boundary_hash = hashlib.sha256(expand_reference(trace["master"], label, context, size)).digest()
        check(f"expanded_{size}_hash", f"digest(&large[..{size}])", boundary_hash)
        flag(f"output_boundary_{size}", f"large[{size}] == 90")
    code.append("let mut sentinel: [u8; 8161] = [90; 8161];")
    data("bad_label", bytes(250))
    data("bad_context", bytes(256))
    for name, arguments, error in (
        ("empty_label", "&master[..], &long_label[..0], &long_context[..], &mut sentinel[..32]", 1),
        ("long_label", "&master[..], &bad_label[..], &long_context[..], &mut sentinel[..32]", 1),
        ("long_context", "&master[..], &long_label[..], &bad_context[..], &mut sentinel[..32]", 2),
        ("short_secret", "&master[..31], &long_label[..], &long_context[..], &mut sentinel[..32]", 3),
        ("large_output", "&master[..], &long_label[..], &long_context[..], &mut sentinel[..]", 4),
    ):
        code.append(f"let rejected_{name} = hkdf_expand_label({arguments});")
        flag(f"{name}_rejected", f"verify_reject(rejected_{name}, {error})")
        flag(f"{name}_output_untouched", "check_sentinel(&sentinel[..])")
    code.extend(("0", "}"))
    return IMPORTS + "\n".join(code) + "\n", checks


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--corboc", type=Path)
    cli.add_argument("--cc", default=os.environ.get("CC", "cc"))
    args = cli.parse_args()
    fixture = json.loads(FIXTURE.read_text())
    fixture.pop("source")
    trace = {name: bytes.fromhex(value) for name, value in fixture.items()}
    source, expected = witness(trace)
    with TemporaryDirectory() as temporary:
        package = Path(temporary)
        (package / "src").mkdir()
        (package / "package.toml").write_text('[package]\nname = "tls_keys_tests"\n')
        (package / "src/main.crb").write_text(source)
        command = [FRONTEND, "emit-c", package]
        if args.corboc:
            command = [args.corboc.resolve(), "--emit-package-c", package, "--stdlib-dir", ROOT / "stdlib/src"]
        emitted = subprocess.run(command, capture_output=True)
        assert emitted.returncode == 0, (emitted.returncode, emitted.stderr, emitted.stdout[:400])
        generated = package / "witness.c"
        binary = package / "witness"
        generated.write_bytes(emitted.stdout)
        for mode, flags in (
            ("native", ["-O0"]),
            ("UBSan", ["-O2", "-fsanitize=undefined", "-fno-sanitize-recover=all"]),
        ):
            subprocess.run([*shlex.split(args.cc), "-std=c11", "-pthread", *flags, generated,
                            "-lm", "-o", binary], check=True)
            result = subprocess.run([binary], capture_output=True, check=True, timeout=90)
            assert not result.stderr, result.stderr
            output = bytes(map(int, result.stdout.splitlines()))
            offset = 0
            for name, value in expected:
                found = output[offset:offset + len(value)]
                assert found == value, (mode, name, found.hex(), value.hex())
                offset += len(value)
            assert offset == len(output), (mode, offset, len(output))
            print(f"{mode}: {len(expected)} TLS 1.3 key schedule checks passed", flush=True)


if __name__ == "__main__":
    main()
