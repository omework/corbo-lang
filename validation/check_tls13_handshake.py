"""Exercise the native Din TLS 1.3 client and server against OpenSSL."""

import argparse
import os
from pathlib import Path
import pty
import re
import selectors
import shlex
import socket
import ssl
import subprocess
from tempfile import TemporaryDirectory, TemporaryFile

from check_tls13_keys import ROOT, FRONTEND, binding

IMPORTS = """
use std::net::sync::tls::{client_handshake, client_handshake_x509, server_handshake,
    server_handshake_chain, HandshakeError};
use std::crypto::p256::{PublicKey, SigningKey};
use std::net::sync::tcp::{connect, Listener};
use std::net::ipv4::{Addr, SocketAddr};

fn handshake_error(error: HandshakeError) -> i32 {
    match error {
        HandshakeError.BufferTooSmall => { 11 },
        HandshakeError.Transport => { 12 },
        HandshakeError.Protocol => { 13 },
        HandshakeError.Authentication => { 14 },
        HandshakeError.Crypto => { 15 },
    }
}
"""

CLIENT = """
let mut socket = match connect(SocketAddr::new(Addr::new(127, 0, 0, 1), PORT)) {
    Ok(value) => { value },
    Err(error) => { drop(error); return 1; },
};
POINT
let peer = match PublicKey::from_sec1_uncompressed(&point[..]) {
    Ok(value) => { value },
    Err(error) => { drop(error); return 2; },
};
let mut session = match client_handshake(&mut socket, &certificate[..], &peer,
                                         &mut wire[..], &mut fragment[..], &mut message[..]) {
    Ok(value) => { value },
    Err(error) => { return handshake_error(error); },
};
let ping: [u8; 4] = [80, 73, 78, 71];
match session.write_application(&mut socket, &ping[..], &mut fragment[..], &mut wire[..]) {
    Ok(()) => {},
    Err(error) => { return handshake_error(error); },
};
match session.read_application(&mut socket, &mut wire[..], &mut fragment[..]) {
    Ok(size) => {
        if size != 4 || fragment[0] != 80 || fragment[1] != 79
           || fragment[2] != 78 || fragment[3] != 71 { return 4; }
    },
    Err(error) => { return handshake_error(error); },
};
match session.shutdown(&mut socket, &mut fragment[..], &mut wire[..]) {
    Ok(()) => {},
    Err(error) => { return handshake_error(error); },
};
match session.read_application(&mut socket, &mut wire[..], &mut fragment[..]) {
    Ok(size) => { if size != 0 { return 5; } },
    Err(error) => { return handshake_error(error); },
};
"""

SERVER = """
let mut listener = match Listener::bind(SocketAddr::new(Addr::new(127, 0, 0, 1), 0), None) {
    Ok(value) => { value },
    Err(error) => { drop(error); return 1; },
};
let local = listener.addr();
print(local.port());
let mut socket = match listener.accept() {
    Ok(value) => { value },
    Err(error) => { drop(error); return 2; },
};
SCALAR
let key = match SigningKey::from_bytes(&scalar) {
    Ok(value) => { value },
    Err(error) => { drop(error); return 3; },
};
let mut session = match server_handshake(&mut socket, &certificate[..], &key,
                                         &mut wire[..], &mut fragment[..], &mut message[..]) {
    Ok(value) => { value },
    Err(error) => { return handshake_error(error); },
};
match session.read_application(&mut socket, &mut wire[..], &mut fragment[..]) {
    Ok(size) => {
        if size != 4 || fragment[0] != 80 || fragment[1] != 73
           || fragment[2] != 78 || fragment[3] != 71 { return 4; }
    },
    Err(error) => { return handshake_error(error); },
};
let pong: [u8; 4] = [80, 79, 78, 71];
match session.write_application(&mut socket, &pong[..], &mut fragment[..], &mut wire[..]) {
    Ok(()) => {},
    Err(error) => { return handshake_error(error); },
};
match session.shutdown(&mut socket, &mut fragment[..], &mut wire[..]) {
    Ok(()) => {},
    Err(error) => { return handshake_error(error); },
};
"""


def create_identity(openssl, root):
    key = root / "key.pem"
    cert = root / "cert.pem"
    subprocess.run([openssl, "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", key],
                   check=True, capture_output=True)
    subprocess.run([openssl, "req", "-new", "-x509", "-key", key, "-out", cert,
                    "-subj", "/CN=localhost", "-days", "1", "-addext", "subjectAltName=DNS:localhost"],
                   check=True, capture_output=True)
    der = subprocess.check_output([openssl, "x509", "-in", cert, "-outform", "DER"])
    details = subprocess.check_output([openssl, "ec", "-in", key, "-text", "-noout"],
                                      stderr=subprocess.DEVNULL, text=True)
    private = details.split("priv:", 1)[1].split("pub:", 1)[0]
    public = details.split("pub:", 1)[1].split("ASN1 OID:", 1)[0]
    scalar = bytes.fromhex("".join(re.findall(r"[0-9a-fA-F]{2}", private)))
    point = bytes.fromhex("".join(re.findall(r"[0-9a-fA-F]{2}", public)))
    assert len(scalar) == 32 and len(point) == 65 and point[0] == 4
    return cert, key, der, scalar, point


def build(args, package, body, certificate, flags, helpers=""):
    source = IMPORTS + helpers + "\nfn main() -> i32 {\n" + binding("certificate", certificate) + """
        let mut wire: [u8; 16406] = [0; 16406];
        let mut fragment: [u8; 16385] = [0; 16385];
        let mut message: [u8; 32768] = [0; 32768];
    """ + body + "\n0\n}"
    (package / "src/main.crb").write_text(source)
    if args.corboc:
        command = [args.corboc.resolve(), "--emit-package-c", package, "--stdlib-dir", ROOT / "stdlib/src"]
    else:
        command = [FRONTEND, "emit-c", package]
    emitted = subprocess.run(command, capture_output=True)
    assert emitted.returncode == 0, (emitted.returncode, emitted.stderr, emitted.stdout[:400])
    code, binary = package / "witness.c", package / "witness"
    code.write_bytes(emitted.stdout)
    subprocess.run([*shlex.split(args.cc), "-std=c11", "-pthread", *flags, code, "-lm", "-o", binary],
                   check=True)
    return binary


def peer_timeout(seconds):
    return seconds * float(os.environ.get("DIN_TLS_TIMEOUT_SCALE", "1"))


def wait(child, expected, errors):
    child.wait(timeout=peer_timeout(15))
    errors.seek(0)
    error = errors.read()
    assert child.returncode == expected and not error, (child.returncode, expected, error)


def readable(stream):
    with selectors.DefaultSelector() as selector:
        selector.register(stream, selectors.EVENT_READ)
        assert selector.select(timeout=peer_timeout(10)), "peer was silent"


def published_port(stream):
    # Wine can write terminal cursor controls before the witness's first line.
    line = re.sub(rb"\x1b\[\?25[hl]", b"", stream.readline()).strip()
    return int(line)


def client_case(args, package, identity, flags, wrong_pin=False, wrong_key=None):
    cert, key, der, _, point = identity
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.set_ecdh_curve("prime256v1")
    context.num_tickets = 0
    context.load_cert_chain(cert, key)
    with socket.create_server(("127.0.0.1", 0)) as listener:
        listener.settimeout(10)
        body = CLIENT.replace("PORT", str(listener.getsockname()[1]))
        body = body.replace("POINT", binding("point", point if wrong_key is None else wrong_key))
        if wrong_pin:
            der = der[:-1] + bytes([der[-1] ^ 1])
        rejects_peer = wrong_pin or wrong_key is not None
        binary = build(args, package, body, der, flags)
        with (TemporaryFile() as errors,
              subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=errors) as child):
            try:
                with listener.accept()[0] as raw:
                    raw.settimeout(10)
                    try:
                        with context.wrap_socket(raw, server_side=True) as peer:
                            assert not rejects_peer
                            assert peer.cipher()[0] == "TLS_AES_128_GCM_SHA256"
                            assert peer.recv(4) == b"PING"
                            peer.sendall(b"PONG")
                            peer.unwrap().close()
                    except (ssl.SSLError, ConnectionResetError):
                        if not rejects_peer:
                            wait(child, 0, errors)
                            raise
                wait(child, 14 if rejects_peer else 0, errors)
            finally:
                if child.poll() is None:
                    child.kill()


def server_case(args, package, identity, flags, chain=False):
    cert, _, der, scalar, _ = identity
    body = SERVER.replace("SCALAR", binding("scalar", scalar))
    if chain:
        body = body.replace("server_handshake(", "server_handshake_chain(")
    binary = build(args, package, body, der, flags)
    master, slave = pty.openpty()
    with (os.fdopen(master, "rb") as output, os.fdopen(slave, "wb") as terminal,
          TemporaryFile() as errors, subprocess.Popen([binary], stdout=terminal, stderr=errors) as child):
        terminal.close()
        try:
            readable(output)
            port = published_port(output)
            command = [args.openssl, "s_client", "-connect", f"127.0.0.1:{port}", "-tls1_3",
                       "-groups", "P-256", "-sigalgs", "ecdsa_secp256r1_sha256",
                       "-ciphersuites", "TLS_AES_128_GCM_SHA256", "-CAfile", cert,
                       "-verify_hostname", "localhost", "-verify_return_error", "-quiet"]
            with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE) as peer:
                try:
                    peer.stdin.write(b"PING")
                    peer.stdin.flush()
                    readable(peer.stdout)
                    actual = peer.stdout.read(4)
                    if actual != b"PONG":
                        _, error = peer.communicate(timeout=10)
                        wait(child, 0, errors)
                        raise AssertionError((actual, error))
                    wait(child, 0, errors)
                    _, error = peer.communicate(timeout=10)
                    assert peer.returncode == 0, (peer.returncode, error)
                finally:
                    if peer.poll() is None:
                        peer.kill()
        finally:
            if child.poll() is None:
                child.kill()
    return binary


def out_of_order(binary):
    master, slave = pty.openpty()
    with (os.fdopen(master, "rb") as output, os.fdopen(slave, "wb") as terminal,
          TemporaryFile() as errors, subprocess.Popen([binary], stdout=terminal, stderr=errors) as child):
        terminal.close()
        try:
            readable(output)
            port = published_port(output)
            with socket.create_connection(("127.0.0.1", port), timeout=10) as peer:
                peer.sendall(bytes.fromhex("160301002414000020") + bytes(32))
                peer.shutdown(socket.SHUT_WR)
                wait(child, 13, errors)
        finally:
            if child.poll() is None:
                child.kill()


def check_private(args, package):
    source = """
use std::net::sync::tls::Session;
fn peek(session: &Session) { let state = &(*session).writer; drop(state); }
fn main() {}
"""
    (package / "src/main.crb").write_text(source)
    if args.corboc:
        command = [args.corboc.resolve(), "--emit-package-c", package, "--stdlib-dir", ROOT / "stdlib/src"]
        rejected = subprocess.run(command, capture_output=True)
        assert rejected.returncode == 8 and b"private field" in rejected.stderr, rejected
    else:
        rejected = subprocess.run([FRONTEND, "emit-c", package], capture_output=True)
        assert rejected.returncode != 0 and b"priv" in rejected.stderr, rejected
    print("Session traffic state is private", flush=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--corboc", type=Path)
    cli.add_argument("--cc", default=os.environ.get("CC", "cc"))
    cli.add_argument("--openssl", default="openssl")
    args = cli.parse_args()
    with TemporaryDirectory() as temporary:
        package = Path(temporary)
        (package / "src").mkdir()
        (package / "package.toml").write_text('[package]\nname = "tls_handshake_tests"\n')
        identity = create_identity(args.openssl, package)
        other = package / "other"
        other.mkdir()
        wrong_key = create_identity(args.openssl, other)[-1]
        for mode, flags in (
            ("native", ["-O0"]),
            ("UBSan", ["-O2", "-fsanitize=undefined", "-fno-sanitize-recover=all"]),
        ):
            client_case(args, package, identity, flags)
            print(f"{mode}: Din client completed an OpenSSL handshake and exchanged application data", flush=True)
            server = server_case(args, package, identity, flags)
            print(f"{mode}: Din server completed an OpenSSL handshake and exchanged application data", flush=True)
            out_of_order(server)
            client_case(args, package, identity, flags, wrong_pin=True)
            client_case(args, package, identity, flags, wrong_key=wrong_key)
            print(f"{mode}: rejected out-of-order Finished, mismatched certificate and wrong verification key", flush=True)
        check_private(args, package)


if __name__ == "__main__":
    main()
