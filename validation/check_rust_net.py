"""Compile and run Din TCP and UDP socket witnesses against an independent loopback peer."""
import argparse
import os
from pathlib import Path
from queue import Empty, Queue
import shlex
import socket
import subprocess
import tempfile
from threading import Thread

from check_rust_assembly import FRONTEND
from check_crust_bootstrap import ROOT

PROGRAM = """
use std::net::tcp;
use std::net::udp;
use std::net::SocketError;
use std::net::ipv4::{Addr, SocketAddr};

fn loopback(port: u16) -> SocketAddr {
    SocketAddr::new(Addr::new(127, 0, 0, 1), port)
}

fn exchange_tcp(mut connection: tcp::Connection) -> Result<usize, SocketError> {
    let mut empty: [u8; 0] = [];
    let count = match connection.read(&mut empty[..]) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    if count != 0 { return Ok(0); }
    let count = match connection.write(&empty[..]) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    if count != 0 { return Ok(0); }
    let mut buffer: [u8; 1] = [0];
    let count = match connection.read(&mut buffer[..]) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    if count != 1 { return Ok(0); }
    print(buffer[0]);
    connection.write(&buffer[..])
}

fn tcp_probe() -> Result<bool, SocketError> {
    let explicit = match tcp::Listener::bind(loopback(0), Some(4)) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    drop(explicit);
    let mut listener = match tcp::Listener::bind(loopback(0), None) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    let bound = listener.addr();
    print(bound.port());
    let mut connection = match listener.accept() {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    let remote = connection.peer();
    if remote.ipv4_bits() != 0x7f000001 || remote.port() == 0 { return Ok(false); }
    drop(listener);
    let mut buffer: [u8; 1] = [0];
    let count = match connection.read(&mut buffer[..]) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    if count != 1 { return Ok(false); }
    print(buffer[0]);
    let count = match connection.write(&buffer[..]) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    if count != 1 { return Ok(false); }
    let count = match connection.read(&mut buffer[..]) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    if count != 0 { return Ok(false); }
    drop(connection);

    let peer = match tcp::connect(loopback(TCP_PORT)) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    match exchange_tcp(peer) {
        Ok(count) => { Ok(count == 1) },
        Err(error) => { Err(error) },
    }
}

fn udp_probe() -> Result<bool, SocketError> {
    let mut listener = match udp::Listener::bind(loopback(0)) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    let bound = listener.addr();
    print(bound.port());

    let mut empty: [u8; 0] = [];
    let packet = match listener.recv(&mut empty[..]) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    if packet.count() != 0 { return Ok(false); }
    let sender = packet.sender();
    if sender.port() == 0 { return Ok(false); }
    print(21);
    match listener.recv(&mut empty[..]) {
        Err(error) => { match error { SocketError.DatagramTooLarge => { print(22); }, SocketError.AddressInUse => { return Ok(false); }, SocketError.ConnectionRefused => { return Ok(false); }, SocketError.Os { code: _ } => { return Ok(false); }, } },
        Ok(_) => { return Ok(false); },
    }

    let mut buffer: [u8; 2] = [0, 0];
    match listener.recv(&mut buffer[..]) {
        Err(error) => { match error { SocketError.DatagramTooLarge => { print(20); }, SocketError.AddressInUse => { return Ok(false); }, SocketError.ConnectionRefused => { return Ok(false); }, SocketError.Os { code: _ } => { return Ok(false); }, } },
        Ok(_) => { return Ok(false); },
    }
    let packet = match listener.recv(&mut buffer[..]) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    print(packet.count());
    let sender = packet.sender();
    print(sender.ipv4_bits());
    let count = match listener.send(&buffer[..], sender) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    if count != 2 { return Ok(false); }

    let mut connection = match udp::connect(loopback(UDP_PORT)) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    let count = match connection.send(&empty[..]) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    if count != 0 { return Ok(false); }
    let count = match connection.recv(&mut buffer[..]) {
        Ok(value) => { value },
        Err(error) => { return Err(error); },
    };
    if count != 2 { return Ok(false); }
    print(buffer[0]);
    print(buffer[1]);

    // Reuse each ephemeral port after moving and destroying its owner.
    let mut attempts: i64 = 0;
    while attempts < 128 {
        let opened = match udp::Listener::bind(loopback(0)) {
            Ok(value) => { value },
            Err(error) => { return Err(error); },
        };
        let moved = opened;
        let address = moved.addr();
        let port = address.port();
        match udp::Listener::bind(loopback(copy(port))) {
            Err(error) => { match error { SocketError.AddressInUse => {  }, SocketError.DatagramTooLarge => { return Ok(false); }, SocketError.ConnectionRefused => { return Ok(false); }, SocketError.Os { code: _ } => { return Ok(false); }, } },
            Ok(_) => { return Ok(false); },
        }
        drop(moved);
        let rebound = match udp::Listener::bind(loopback(port)) {
            Ok(value) => { value },
            Err(error) => { return Err(error); },
        };
        drop(rebound);
        attempts += 1;
    }
    Ok(true)
}

fn main() -> i32 {
    match SocketAddr::parse("127.0.0.1:65535") {
        Ok(address) => {
            if address.ipv4_bits() != 0x7f000001 || address.port() != 65535 { return 1; }
        },
        Err(_) => { return 1; },
    }
    match SocketAddr::parse("127.0.0.256:80") {
        Ok(_) => { return 2; },
        Err(_) => {},
    }
    match tcp_probe() {
        Ok(valid) => { if !valid { return 3; } },
        Err(_) => { return 3; },
    }
    match udp_probe() {
        Ok(valid) => { if !valid { return 4; } },
        Err(error) => {
            match error {
                SocketError.Os { code: code } => { print(code); },
                SocketError.DatagramTooLarge => { print(31); },
                SocketError.AddressInUse => { print(32); },
                SocketError.ConnectionRefused => { print(33); },
            }
            return 4;
        },
    }
    0
}
"""
# Enable a rendezvous on stdout without changing the generated socket operations.
UNBUFFERED_MAIN = """
#undef main
int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    return crust_net_probe_main(MAIN_ARGUMENTS);
}
"""


def port(sock):
    return sock.getsockname()[1]


def exercise(command, tcp_server, udp_peer):
    limits = {}
    if not Path(command[0]).name.endswith("wine") and os.name != "nt":
        from check_rust_file import limit_descriptors
        limits["preexec_fn"] = limit_descriptors
    with subprocess.Popen(command, **limits, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0) as proc:
        lines = Queue()

        def collect_output():
            for line in proc.stdout:
                lines.put(line)
            lines.put(None)

        def number():
            try:
                line = lines.get(timeout=15)
            except Empty as error:
                raise AssertionError("probe produced no output") from error
            assert line is not None, f"probe exited with {proc.wait(timeout=5)}: {proc.stderr.read()}"
            return int(line)

        reader = Thread(target=collect_output, daemon=True)
        reader.start()
        try:
            with socket.create_connection(("127.0.0.1", number()), timeout=15) as client:
                client.sendall(b"A")
                assert number() == 65
                assert client.recv(1) == b"A"
                client.shutdown(socket.SHUT_WR)
            accepted, _ = tcp_server.accept()
            with accepted:
                accepted.settimeout(15)
                accepted.sendall(b"B")
                assert number() == 66
                assert accepted.recv(1) == b"B"
            target = ("127.0.0.1", number())
            udp_peer.sendto(b"", target)
            assert number() == 21
            udp_peer.sendto(b"X", target)
            assert number() == 22
            udp_peer.sendto(b"oversize", target)
            assert number() == 20
            udp_peer.sendto(b"OK", target)
            assert number() == 2
            assert number() == 0x7f000001
            assert udp_peer.recvfrom(32) == (b"OK", target)
            empty, sender = udp_peer.recvfrom(32)
            assert empty == b""
            udp_peer.sendto(b"XY", sender)
            assert (number(), number()) == (88, 89)
            assert proc.wait(timeout=45) == 0, proc.stderr.read()
        finally:
            if proc.poll() is None:
                proc.kill()
            reader.join(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target")
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--frontend", type=Path, default=FRONTEND)
    parser.add_argument("--corboc", type=Path)
    parser.add_argument("--runner", nargs="+", default=[])
    parser.add_argument("--compile-only", action="store_true")
    parser.add_argument("--ubsan", action="store_true")
    args = parser.parse_args()
    if args.corboc and args.target:
        parser.error("--corboc uses the compiler's host target")
    flags = ["--target", args.target] if args.target else []
    windows = "windows" in args.target if args.target else os.name == "nt"
    with tempfile.TemporaryDirectory(prefix="din-net-") as work:
        root = Path(work)
        (root / "src").mkdir()
        (root / "package.toml").write_text('[package]\nname = "socket_probe"\n')
        entry = root / "src/main.crb"
        generated = root / "socket.c"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_server, \
                socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_peer:
            if not args.compile_only:
                for peer in (tcp_server, udp_peer):
                    peer.bind(("127.0.0.1", 0))
                    peer.settimeout(15)
                tcp_server.listen(2)
            entry.write_text(PROGRAM.replace("TCP_PORT", str(port(tcp_server)))
                                    .replace("UDP_PORT", str(port(udp_peer))))
            emit = ([args.corboc, "--emit-package-c", root, "--stdlib-dir", ROOT / "stdlib/src"]
                    if args.corboc else [args.frontend, "emit-c", root, *flags])
            emitted = subprocess.run(emit, capture_output=True, text=True)
            assert emitted.returncode == 0, (emitted.returncode, emitted.stderr, emitted.stdout[:300])
            args_in_main = "" if "int main(void)" in emitted.stdout else "argc, argv"
            harness = UNBUFFERED_MAIN.replace("MAIN_ARGUMENTS", args_in_main)
            if not args_in_main:
                harness = harness.replace("int main(int argc, char **argv)", "int main(void)")
            generated.write_text("#define main crust_net_probe_main\n" + emitted.stdout + harness)
            for opt in ("-O0", "-O2"):
                executable = root / ("socket.exe" if windows else "socket")
                sanitizer = ["-fsanitize=undefined", "-fno-sanitize-recover=all"] if args.ubsan else []
                libraries = ["-lws2_32"] if windows else []
                subprocess.run([*shlex.split(args.cc), "-std=c11", "-Wall", "-Wextra", "-Werror",
                                opt, *sanitizer, generated, *libraries, "-o", executable], check=True)
                if not args.compile_only:
                    exercise([*args.runner, executable], tcp_server, udp_peer)
                print(f"{args.target or 'host'} {opt}: {'linked' if args.compile_only else 'TCP and UDP traces matched'}")
        for source in (
            "use std::net::tcp::Connection; fn main() { let forged = Connection {}; drop(forged); }",
            "use std::net::udp::Listener; fn main() { let mut p = pool<Listener>(1); let forged = p.new(); drop(forged); }",
            "use std::net::tcp::Connection; struct Wrapper { connection: Connection } "
            "fn main() { let mut p = pool<Wrapper>(1); let forged = p.new(); drop(forged); }",
        ):
            entry.write_text(source)
            command = emit if args.corboc else [args.frontend, "check", root, *flags]
            refusal = subprocess.run(command, capture_output=True, text=True)
            if args.corboc:
                assert refusal.returncode in (8, 9), refusal
            else:
                assert refusal.returncode and "représentation privée" in refusal.stderr, refusal


if __name__ == "__main__":
    main()
