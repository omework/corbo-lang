"""Validate the Din TLS 1.3 record layer against RFC 8448 §3."""

import argparse
import json
import os
from pathlib import Path
import pty
import selectors
import shlex
import socket
import subprocess
from tempfile import TemporaryDirectory
import time

from check_tls13_keys import ROOT, FRONTEND, FIXTURE, binding
from check_tls13_handshake import published_port

MODULE = "std::net::tls::record"
LIBRARY = ROOT / "stdlib/src/net/sync/tls/record/record.crb"
RECORDS = ROOT / "validation/fixtures/tls13-records-rfc8448-section3.json"
ERRORS = ("BufferTooSmall", "RecordOverflow", "InvalidRecord", "AuthenticationFailed",
          "WrongDirection", "KeyLimit", "Closed", "Failed", "Transport", "Truncated")


def error_arms(expected, code):
    return ", ".join(f"Error.{variant} => {{ {'return ' + str(code) + ';' if variant != expected else ''} }}"
                     for variant in ERRORS) + ","

IMPORTS = f"""
use {MODULE}::{{RecordCipher, Error, encode_plaintext, decode_plaintext,
    HANDSHAKE, APPLICATION_DATA, ALERT}};
"""


def fixture(path):
    return {name: bytes.fromhex(value) for name, value in json.loads(path.read_text()).items()
            if name != "source"}


def record_witness(keys, records):
    code = [IMPORTS, "fn main() -> i32 {"]
    checks = []

    def data(name, value):
        code.append(binding(name, value))

    def fail_if(condition, description):
        checks.append(description)
        code.append(f"if {condition} {{ return {len(checks)}; }}")

    def take(name, call):
        checks.append(name)
        code.append(f"""let {name} = match {call} {{
            Ok(value) => {{ value }},
            Err(error) => {{ drop(error); return {len(checks)}; }},
        }};""")

    def must_error(call, variant):
        checks.append(variant)
        position = len(checks)
        code.append(f"""match {call} {{
            Ok(value) => {{ drop(value); return {position}; }},
            Err(error) => {{
                match error {{
                    {error_arms(variant, position)}
                }};
            }},
        }};""")

    code.append("let mut wire: [u8; 16406] = [90; 16406];")
    code.append("let mut scratch: [u8; 16385] = [90; 16385];")
    code.append("let mut plain: [u8; 16385] = [90; 16385];")
    for side in ("client", "server"):
        name = f"{side}_hello"
        data(name, keys[name])
        data(f"{name}_wire", records[name])
        initial = str(side == "client").lower()
        take(f"{name}_size", f"encode_plaintext(HANDSHAKE, {initial}, &{name}[..], &mut wire[..])")
        code.append(f"let {name}_fragment = &wire[..{name}_size];")
        fail_if(f"!{name}_fragment.content_eq(&{name}_wire[..])", name + " wire bytes")
        take(f"{name}_decoded", f"decode_plaintext(&{name}_wire[..])")
        fail_if(f"{name}_decoded.kind() != HANDSHAKE || {name}_decoded.len() != {len(keys[name])}",
                name + " content metadata")

    def initialize(prefix, key, iv):
        data(f"{prefix}_key", key)
        data(f"{prefix}_iv", iv)
        code.append(f"let mut {prefix}_tx = RecordCipher::writer(&{prefix}_key, &{prefix}_iv);")
        code.append(f"let mut {prefix}_rx = RecordCipher::reader(&{prefix}_key, &{prefix}_iv);")

    def protected(prefix, name, kind, content):
        data(f"{name}_content", content)
        data(f"{name}_wire", records[name])
        if kind == "ALERT":
            take(f"{name}_length", f"{prefix}_tx.seal_close_notify(&mut scratch[..], &mut wire[..])")
        else:
            take(f"{name}_length", f"{prefix}_tx.seal({kind}, &{name}_content[..], 0, &mut scratch[..], &mut wire[..])")
        code.append(f"let {name}_fragment = &wire[..{name}_length];")
        fail_if(f"!{name}_fragment.content_eq(&{name}_wire[..])", name + " protected bytes")
        take(f"{name}_decoded", f"{prefix}_rx.open(&{name}_wire[..], &mut plain[..])")
        fail_if(f"{name}_decoded.kind() != {kind} || {name}_decoded.len() != {len(content)}",
                name + " content metadata")
        code.append(f"let {name}_decoded_bytes = &plain[..{name}_decoded.len()];")
        fail_if(f"!{name}_decoded_bytes.content_eq(&{name}_content[..])", name + " plaintext")
        if kind == "ALERT":
            fail_if(f"!{name}_decoded.is_close_notify()", name + " close")
            must_error(f"{prefix}_tx.seal_close_notify(&mut scratch[..], &mut wire[..])", "Closed")
            must_error(f"{prefix}_rx.open(&{name}_wire[..], &mut plain[..])", "Closed")

    for side in ("server", "client"):
        initialize(f"{side}_hs", keys[f"{side}_hs_key"], keys[f"{side}_hs_iv"])
    server_handshake = b"".join(keys[name] for name in ("encrypted_extensions", "certificate",
                                "certificate_verify", "server_finished_message"))
    protected("server_hs", "server_handshake", "HANDSHAKE", server_handshake)
    protected("client_hs", "client_finished", "HANDSHAKE", keys["client_finished_message"])

    for side in ("server", "client"):
        initialize(f"{side}_ap", keys[f"{side}_ap_key"], keys[f"{side}_ap_iv"])
    protected("server_ap", "server_ticket", "HANDSHAKE", records["ticket_content"])
    for side in ("client", "server"):
        protected(f"{side}_ap", f"{side}_application", "APPLICATION_DATA", bytes(range(50)))
        protected(f"{side}_ap", f"{side}_close", "ALERT", b"\x01\x00")

    code.append("let mut tx = RecordCipher::writer(&client_ap_key, &client_ap_iv);")
    code.append("let mut rx = RecordCipher::reader(&client_ap_key, &client_ap_iv);")
    data("content", b"A\x00B\x00")
    must_error("tx.seal(APPLICATION_DATA, &content[..], 3, &mut scratch[..7], &mut wire[..])", "BufferTooSmall")
    must_error("tx.seal(APPLICATION_DATA, &content[..], 16381, &mut scratch[..], &mut wire[..])", "RecordOverflow")
    must_error("rx.seal(APPLICATION_DATA, &content[..], 0, &mut scratch[..], &mut wire[..])", "WrongDirection")
    take("padded_len", "tx.seal(APPLICATION_DATA, &content[..], 3, &mut scratch[..], &mut wire[..])")
    fail_if("padded_len != 29", "padded length")
    must_error("rx.open(&wire[..padded_len], &mut plain[..7])", "BufferTooSmall")
    take("padded", "rx.open(&wire[..padded_len], &mut plain[..])")
    fail_if("padded.len() != 4 || plain[0] != 65 || plain[2] != 66 || plain[3] != 0", "trailing zero in content")
    take("empty_len", "tx.seal(APPLICATION_DATA, &content[..0], 0, &mut scratch[..], &mut wire[..])")
    take("empty", "rx.open(&wire[..empty_len], &mut plain[..])")
    fail_if("empty.len() != 0 || empty.kind() != APPLICATION_DATA", "empty application record")

    code.append("let full: [u8; 16384] = [65; 16384];")
    take("full_len", "tx.seal(APPLICATION_DATA, &full[..], 0, &mut scratch[..], &mut wire[..])")
    fail_if("full_len != 16406", "full record occupied the bounded buffers")
    take("full_record", "rx.open(&wire[..full_len], &mut plain[..])")
    fail_if("full_record.len() != 16384 || plain[0] != 65 || plain[16383] != 65", "full record round trip")

    data("tampered", records["client_application"][:-1] + bytes([records["client_application"][-1] ^ 1]))
    code.append("let mut bad = RecordCipher::reader(&client_ap_key, &client_ap_iv);")
    code.append("let mut sentinel: [u8; 64] = [90; 64];")
    must_error("bad.open(&tampered[..], &mut sentinel[..])", "AuthenticationFailed")
    fail_if("sentinel[0] != 90 || sentinel[50] != 90", "failed tag does not expose plaintext")
    must_error("bad.open(&client_application_wire[..], &mut sentinel[..])", "Failed")
    code.append("let mut overflow = RecordCipher::reader(&client_ap_key, &client_ap_iv);")
    data("oversized", bytes.fromhex("1703034012"))
    must_error("overflow.open(&oversized[..], &mut plain[..])", "RecordOverflow")
    code.extend(("0", "}"))
    return "\n".join(code), checks


TCP_SOURCE = IMPORTS + f"""
use {MODULE}::{{read_record, write_record}};
use std::net::ipv4::{{Addr, SocketAddr}};
use std::net::tcp::Listener;

fn main() -> i32 {{
    let address = SocketAddr::new(Addr::new(127, 0, 0, 1), 0);
    let mut listener = match Listener::bind(address, None) {{
        Ok(value) => {{ value }},
        Err(error) => {{ drop(error); return 1; }},
    }};
    let bound_address = listener.addr();
    print(bound_address.port());
    let mut socket = match listener.accept() {{
        Ok(value) => {{ value }},
        Err(error) => {{ drop(error); return 2; }},
    }};
    KEY_BINDINGS
    let mut wire: [u8; 256] = [0; 256];
    let mut plain: [u8; 128] = [0; 128];
    let mut scratch: [u8; 256] = [0; 256];
    BODY
    0
}}
"""

TCP_BODY = """
let mut reader = RecordCipher::reader(&client_key, &client_iv);
let mut writer = RecordCipher::writer(&server_key, &server_iv);
let initial_size = match read_record(&mut socket, &mut wire[..]) {
    Ok(count) => { count },
    Err(error) => { drop(error); return 3; },
};
match decode_plaintext(&wire[..initial_size]) {
    Ok(record) => { if record.kind() != HANDSHAKE || record.len() != 196 { return 4; } },
    Err(error) => { drop(error); return 5; },
};
SERVER_HELLO
let invalid_header: [u8; 5] = [23, 3, 3, 64, 18];
match write_record(&mut socket, &invalid_header[..]) {
    Ok(()) => { return 20; },
    Err(error) => { match error { RAW_OVERFLOW_ARMS }; },
};
match write_record(&mut socket, &server_hello[..]) {
    Ok(()) => {},
    Err(error) => { drop(error); return 6; },
};
TICKET_BINDING
match writer.send_record(&mut socket, HANDSHAKE, &ticket[..], 0, &mut scratch[..], &mut wire[..]) {
    Ok(()) => {},
    Err(error) => { drop(error); return 19; },
};
let received = match reader.receive_record(&mut socket, &mut wire[..], &mut plain[..]) {
    Ok(record) => { record },
    Err(error) => { drop(error); return 7; },
};
if received.kind() != APPLICATION_DATA || received.len() != 50 || plain[49] != 49 { return 8; }
match writer.send_record(&mut socket, APPLICATION_DATA, &plain[..received.len()], 0, &mut scratch[..], &mut wire[..]) {
    Ok(()) => {},
    Err(error) => { drop(error); return 9; },
};
match reader.receive_record(&mut socket, &mut wire[..], &mut plain[..]) {
    Ok(record) => { if !record.is_close_notify() { return 10; } },
    Err(error) => { drop(error); return 11; },
};
match reader.receive_record(&mut socket, &mut wire[..], &mut plain[..]) {
    Ok(record) => { drop(record); return 12; },
    Err(error) => {
        match error { CLOSED_ARMS };
    },
};
match writer.close_notify(&mut socket, &mut scratch[..], &mut wire[..]) {
    Ok(()) => {},
    Err(error) => { drop(error); return 14; },
};
"""

TRUNCATED_BODY = """
let mut reader = RecordCipher::reader(&client_key, &client_iv);
match reader.receive_record(&mut socket, &mut wire[..], &mut plain[..]) {
    Ok(record) => { drop(record); return 15; },
    Err(error) => {
        match error { TRUNCATED_ARMS };
    },
};
match reader.receive_record(&mut socket, &mut wire[..], &mut plain[..]) {
    Ok(record) => { drop(record); return 17; },
    Err(error) => {
        match error { FAILED_ARMS };
    },
};
"""


def compile_case(args, package, source, flags):
    (package / "src/main.crb").write_text(source)
    if args.corboc:
        command = [args.corboc.resolve(), "--emit-package-c", package, "--stdlib-dir", ROOT / "stdlib/src"]
    else:
        command = [FRONTEND, "emit-c", package]
    emitted = subprocess.run(command, capture_output=True)
    assert emitted.returncode == 0, (emitted.returncode, emitted.stderr, emitted.stdout[:300])
    code, binary = package / "witness.c", package / "witness"
    code.write_bytes(emitted.stdout)
    subprocess.run([*shlex.split(args.cc), "-std=c11", "-pthread", *flags, code, "-lm",
                    "-o", binary], check=True)
    return binary


def check_private(args, package):
    source = """
use std::net::tls::record::RecordCipher;
fn main() {
    let key: [u8; 16] = [0; 16];
    let iv: [u8; 12] = [0; 12];
    let mut writer = RecordCipher::writer(&key, &iv);
    let sequence = &mut writer.sequence;
    *sequence = 0;
}
"""
    (package / "src/main.crb").write_text(source)
    if args.corboc:
        command = [args.corboc.resolve(), "--emit-package-c", package, "--stdlib-dir", ROOT / "stdlib/src"]
        rejected = subprocess.run(command, capture_output=True)
        assert rejected.returncode == 8 and b"private field" in rejected.stderr, rejected
    else:
        rejected = subprocess.run([FRONTEND, "emit-c", package], capture_output=True)
        assert rejected.returncode != 0 and b"priv" in rejected.stderr, rejected
    print("The compiler rejected external access to the nonce counter", flush=True)


def fragmented_send(peer, wire):
    for offset in range(0, len(wire), 3):
        peer.sendall(wire[offset:offset + 3])
        time.sleep(0.001)


def require_bytes(peer, expected):
    received = bytearray()
    while len(received) < len(expected):
        fragment = peer.recv(len(expected) - len(received))
        assert fragment, (len(received), len(expected))
        received.extend(fragment)
    assert received == expected, (received.hex(), expected.hex())


def limit_transport_calls(package, source):
    module = package / "src/short_record"
    module.mkdir()
    record = LIBRARY.read_text()
    read = "match socket.read(&mut wire[at..end]) {"
    write = "match socket.write(&wire[at..size]) {"
    assert record.count(read) == record.count(write) == 1
    record = record.replace(read, """
            let limit: usize = if end - at > 2 { at + 2 } else { copy(end) };
            match socket.read(&mut wire[at..limit]) {""")
    record = record.replace(write, """
            let limit: usize = if size - at > 3 { at + 3 } else { copy(size) };
            match socket.write(&wire[at..limit]) {""")
    (module / "record.crb").write_text(record)
    return source.replace(MODULE, "record_tests::short_record")


def tcp_case(binary, records, incomplete):
    master, slave = pty.openpty()
    with (os.fdopen(master, "rb") as output, os.fdopen(slave, "wb") as terminal,
          subprocess.Popen([binary], stdout=terminal, stderr=subprocess.PIPE) as child):
        terminal.close()
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(output, selectors.EVENT_READ)
                assert selector.select(timeout=10), "Din did not report its listening port"
            port = published_port(output)
            with socket.create_connection(("127.0.0.1", port), timeout=5) as peer:
                if incomplete is not None:
                    fragmented_send(peer, incomplete)
                    peer.shutdown(socket.SHUT_WR)
                else:
                    fragmented_send(peer, records["client_hello"])
                    require_bytes(peer, records["server_hello"])
                    require_bytes(peer, records["server_ticket"])
                    fragmented_send(peer, records["client_application"])
                    require_bytes(peer, records["server_application"])
                    fragmented_send(peer, records["client_close"])
                    require_bytes(peer, records["server_close"])
            _, error = child.communicate(timeout=10)
            assert child.returncode == 0 and not error, (child.returncode, error)
        finally:
            if child.poll() is None:
                child.kill()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--corboc", type=Path)
    cli.add_argument("--cc", default=os.environ.get("CC", "cc"))
    cli.add_argument("--tcp", action="store_true", help="also exercise local TCP sockets")
    args = cli.parse_args()
    keys, records = fixture(FIXTURE), fixture(RECORDS)
    with TemporaryDirectory() as temporary:
        package = Path(temporary)
        (package / "src").mkdir()
        (package / "package.toml").write_text('[package]\nname = "record_tests"\n')
        source, checks = record_witness(keys, records)
        for mode, flags in (
            ("native", ["-O0"]),
            ("UBSan", ["-O2", "-fsanitize=undefined", "-fno-sanitize-recover=all"]),
        ):
            binary = compile_case(args, package, source, flags)
            result = subprocess.run([binary], capture_output=True, timeout=30)
            failure = checks[result.returncode - 1] if 0 < result.returncode <= len(checks) else ""
            assert result.returncode == 0 and not result.stderr, (result.returncode, failure, result.stderr)
            print(f"{mode}: {len(checks)} record checks passed", flush=True)
            if args.tcp:
                key_bindings = "\n".join(binding(f"{side}_{material}", keys[f"{side}_ap_{material}"])
                                         for side in ("client", "server") for material in ("key", "iv"))
                tcp = TCP_SOURCE.replace("KEY_BINDINGS", key_bindings)
                body = TCP_BODY.replace("SERVER_HELLO", binding("server_hello", records["server_hello"]))
                body = body.replace("TICKET_BINDING", binding("ticket", records["ticket_content"]))
                body = body.replace("CLOSED_ARMS", error_arms("Closed", 13))
                body = body.replace("RAW_OVERFLOW_ARMS", error_arms("RecordOverflow", 21))
                binary = compile_case(args, package, tcp.replace("BODY", body), flags)
                tcp_case(binary, records, None)
                truncated = TRUNCATED_BODY.replace("TRUNCATED_ARMS", error_arms("Truncated", 16))
                truncated = truncated.replace("FAILED_ARMS", error_arms("Failed", 18))
                binary = compile_case(args, package, tcp.replace("BODY", truncated), flags)
                for incomplete in (b"", records["client_application"][:3], records["client_application"][:20]):
                    tcp_case(binary, records, incomplete)
                source_with_short_io = limit_transport_calls(package, tcp.replace("BODY", body))
                binary = compile_case(args, package, source_with_short_io, flags)
                tcp_case(binary, records, None)
                (package / "src/short_record/record.crb").unlink()
                (package / "src/short_record").rmdir()
                print(f"{mode}: fragmented TCP, forced short I/O, close_notify, and three truncations passed", flush=True)
        check_private(args, package)


if __name__ == "__main__":
    main()
