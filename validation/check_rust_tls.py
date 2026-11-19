"""Exercise Din TLS 1.3 client and server against Python's TLS socket API."""
import argparse
import os
from pathlib import Path
import pty
import selectors
import socket
import ssl
import subprocess
from tempfile import TemporaryDirectory

from check_crust_bootstrap import FRONTEND

IMPORTS = """
use std::net::tls::openssl as tls;
use std::net::tls::openssl::TlsError;
use std::net::tcp;
use std::net::ipv4::{Addr, SocketAddr};

fn loopback(port: u16) -> SocketAddr {
    SocketAddr::new(Addr::new(127, 0, 0, 1), port)
}
"""
CLIENT = IMPORTS + """
fn main() -> i32 {
    let socket = match tcp::connect(loopback(PORT)) {
        Ok(value) => { value },
        Err(_) => { return 10; },
    };
    HOST
    TRUST
    let mut connection = match tls::connect(socket, &hostname[..], &trust[..]) {
        Ok(value) => { value },
        Err(error) => {
            match error {
                TlsError.PeerVerificationFailed => { return 11; },
                TlsError.InvalidInput => { return 12; },
                TlsError.ConfigurationFailed => { return 12; },
                TlsError.HandshakeFailed => { return 12; },
                TlsError.TransportFailed => { return 12; },
            };
        },
    };
    let request: [u8; 1] = [65];
    match connection.write(&request[..]) {
        Ok(count) => { if count != 1 { return 13; } },
        Err(_) => { return 14; },
    };
    let mut response: [u8; 1] = [0];
    match connection.read(&mut response[..]) {
        Ok(count) => { if count != 1 || response[0] != 66 { return 15; } },
        Err(_) => { return 16; },
    };
    match connection.read(&mut response[..]) {
        Ok(count) => { if count != 0 { return 17; } },
        Err(_) => {
            match connection.read(&mut response[..]) {
                Ok(_) => { return 19; },
                Err(_) => { return 18; },
            };
        },
    };
    match connection.close() {
        Ok(()) => { 0 },
        Err(_) => { 20 },
    }
}
"""
SERVER = IMPORTS + """
fn main() -> i32 {
    let mut listener = match tcp::Listener::bind(loopback(0), None) {
        Ok(value) => { value },
        Err(_) => { return 30; },
    };
    let local = listener.addr();
    print(local.port());
    let socket = match listener.accept() {
        Ok(value) => { value },
        Err(_) => { return 31; },
    };
    CERT
    KEY
    let mut connection = match tls::accept(socket, &certificate[..], &key[..]) {
        Ok(value) => { value },
        Err(_) => { return 32; },
    };
    let mut buffer: [u8; 1] = [0];
    match connection.read(&mut buffer[..]) {
        Ok(count) => { if count != 1 || buffer[0] != 65 { return 33; } },
        Err(_) => { return 34; },
    };
    match connection.write(&buffer[..]) {
        Ok(count) => { if count != 1 { return 35; } },
        Err(_) => { return 36; },
    };
    match connection.close() {
        Ok(()) => { 0 },
        Err(_) => { 37 },
    }
}
"""


def bytes_binding(name, text):
    data = text.encode() + b"\0"
    return f"let {name}: [u8; {len(data)}] = [{','.join(map(str, data))}];"


def issue_certificate(root, command, label):
    subprocess.run(
        [command, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", f"{label}.key", "-out", f"{label}.pem", "-days", "1",
         "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost"],
        cwd=root, capture_output=True, check=True,
    )


def build(root, source, library, sanitize):
    (root / "src/main.crb").write_text(source)
    binary = root / "probe"
    if not sanitize:
        env = dict(os.environ, DIN_OPENSSL_LIB_DIR=str(library))
        subprocess.run([FRONTEND, "build", root, "-o", binary], env=env, check=True)
    else:
        emitted = subprocess.check_output([FRONTEND, "emit-c", root])
        subprocess.run(
            [os.environ.get("CC", "cc"), "-std=c11", "-pthread", "-x", "c", "-",
             "-O2", "-fsanitize=undefined", "-fno-sanitize-recover=all",
             "-L", library, "-lssl", "-lcrypto", "-lm", "-o", binary],
            input=emitted, check=True,
        )
    return binary


def wait(process, expected):
    stdout, stderr = process.communicate(timeout=10)
    assert (process.returncode, stdout or b"", stderr) == (expected, b"", b""), (
        process.returncode, stdout, stderr
    )


def exercise_client(root, library, sanitize):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(root / "server.pem", root / "server.key")
    for host, trust, mode, expected in (
        ("localhost", "server.pem", "close", 0),
        ("localhost", "server.pem", "truncate", 18),
        ("wrong.example", "server.pem", "reject", 11),
        ("localhost", "other.pem", "reject", 11),
        ("localhost", "server.pem", "legacy", 12),
    ):
        context.maximum_version = ssl.TLSVersion.TLSv1_2 if mode == "legacy" else ssl.TLSVersion.TLSv1_3
        with socket.create_server(("127.0.0.1", 0)) as listener:
            listener.settimeout(10)
            source = CLIENT.replace("PORT", str(listener.getsockname()[1])).replace(
                "HOST", bytes_binding("hostname", host)
            ).replace("TRUST", bytes_binding("trust", trust))
            binary = build(root, source, library, sanitize)
            with subprocess.Popen([binary], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
                try:
                    raw, _ = listener.accept()
                    with raw:
                        raw.settimeout(10)
                        if mode in ("reject", "legacy"):
                            try:
                                context.wrap_socket(raw, server_side=True).close()
                            except ssl.SSLError:
                                pass
                            else:
                                raise AssertionError(f"handshake unexpectedly succeeded for {mode}")
                        else:
                            with context.wrap_socket(raw, server_side=True) as peer:
                                assert peer.version() == "TLSv1.3"
                                assert peer.recv(1) == b"A"
                                peer.sendall(b"B")
                                if mode == "truncate":
                                    socket.close(peer.detach())
                                else:
                                    peer.unwrap().close()
                    wait(proc, expected)
                finally:
                    if proc.poll() is None:
                        proc.kill()


def exercise_server(root, library, sanitize):
    source = SERVER.replace("CERT", bytes_binding("certificate", "server.pem")).replace(
        "KEY", bytes_binding("key", "server.key")
    )
    binary = build(root, source, library, sanitize)
    context = ssl.create_default_context(cafile=str(root / "server.pem"))
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    master, slave = pty.openpty()
    with os.fdopen(master, "rb") as output, os.fdopen(slave, "wb") as terminal:
        with subprocess.Popen([binary], cwd=root, stdout=terminal, stderr=subprocess.PIPE) as proc:
            terminal.close()
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(output, selectors.EVENT_READ)
                    assert selector.select(timeout=10), "Din server did not report its listening port"
                port = int(output.readline())
                with socket.create_connection(("127.0.0.1", port), timeout=10) as raw:
                    with context.wrap_socket(raw, server_hostname="localhost") as peer:
                        assert peer.version() == "TLSv1.3"
                        peer.sendall(b"A")
                        assert peer.recv(1) == b"A"
                        assert peer.recv(1) == b""
                wait(proc, 0)
            finally:
                if proc.poll() is None:
                    proc.kill()


def exercise_privacy(root):
    (root / "src/main.crb").write_text(
        "use std::{net as network}; fn unused(session: network::tls::openssl::Connection) { drop(session); } fn main() {}"
    )
    subprocess.run([FRONTEND, "check", root], check=True)
    for program in (
        "use std::net::tcp::__din_package_socket; fn main() {}",
        "use std::net::tcp as tcp; fn main() { tcp::__din_package_socket(); }",
        "use std::net::tls::openssl::Connection; fn main() { let forged = Connection {}; drop(forged); }",
    ):
        (root / "src/main.crb").write_text(program)
        result = subprocess.run([FRONTEND, "check", root], capture_output=True)
        assert result.returncode and b"priv" in result.stderr, result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openssl-lib-dir", type=Path, required=True)
    parser.add_argument("--openssl", default="openssl")
    args = parser.parse_args()
    with TemporaryDirectory() as work:
        root = Path(work)
        (root / "src").mkdir()
        (root / "package.toml").write_text('[package]\nname = "tls_probe"\n')
        issue_certificate(root, args.openssl, "server")
        issue_certificate(root, args.openssl, "other")
        for sanitize in (False, True):
            exercise_client(root, args.openssl_lib_dir, sanitize)
            exercise_server(root, args.openssl_lib_dir, sanitize)
            print(f"TLS client and server passed ({'UBSan' if sanitize else 'native'})", flush=True)
        exercise_privacy(root)
        print("TLS ownership and socket descriptor boundaries refused external access")


if __name__ == "__main__":
    main()
