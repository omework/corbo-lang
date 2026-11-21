"""Validate Din's P-256 X.509 profile and TLS interoperability with OpenSSL."""

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import socket
import ssl
import subprocess
from tempfile import TemporaryDirectory, TemporaryFile
import time

from check_tls13_handshake import CLIENT, binding, build, server_case, wait
from check_tls13_keys import FRONTEND, ROOT


@dataclass
class Identity:
    cert: Path
    key: Path
    der: bytes


class Certificates:
    def __init__(self, openssl, directory):
        self.openssl = openssl
        self.directory = directory
        self.serial = 1

    def run(self, *arguments):
        result = subprocess.run([self.openssl, *arguments], capture_output=True)
        assert result.returncode == 0, (arguments, result.stderr)
        return result.stdout

    def create(self, name, subject, extensions, issuer=None, key=None, days=365):
        root = self.directory
        if key is None:
            key = root / f"{name}.key"
            self.run("ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", key)
        csr = root / f"{name}.csr"
        cert = root / f"{name}.pem"
        ext = root / f"{name}.cnf"
        ext.write_text("[x509]\n" + "\n".join(extensions) + "\n")
        self.run("req", "-new", "-key", key, "-subj", f"/CN={subject}", "-out", csr)
        signer = ["-signkey", key] if issuer is None else ["-CA", issuer.cert, "-CAkey", issuer.key]
        self.run("x509", "-req", "-in", csr, *signer, "-out", cert, "-sha256",
                 "-set_serial", str(self.serial), "-days", str(days), "-extfile", ext, "-extensions", "x509")
        self.serial += 1
        return Identity(cert, key, self.run("x509", "-in", cert, "-outform", "DER"))

    def signing_scalar(self, identity):
        text = self.run("ec", "-in", identity.key, "-text", "-noout").decode()
        private = text.split("priv:", 1)[1].split("pub:", 1)[0]
        scalar = bytes.fromhex("".join(re.findall(r"[0-9a-fA-F]{2}", private)))
        assert len(scalar) == 32
        return scalar


def entry(der):
    return len(der).to_bytes(3, "big") + der + bytes(2)


def chain(*certificates):
    return b"".join(entry(der) for der in certificates)


def certificate_cases(c, root, intermediate, leaf):
    ca_usage = ["basicConstraints=critical,CA:TRUE", "keyUsage=critical,keyCertSign,cRLSign"]
    leaf_usage = ["basicConstraints=critical,CA:FALSE", "keyUsage=critical,digitalSignature",
                  "extendedKeyUsage=serverAuth"]
    san = "subjectAltName=DNS:localhost"
    trusted_chain = leaf.der + intermediate.der
    wrong_root = c.create("wrong-root", "Din test root", ca_usage)
    limited_root = c.create("limited-root", "Din test root",
                            ["basicConstraints=critical,CA:TRUE,pathlen:0", ca_usage[1]], key=root.key)
    no_ca = c.create("not-ca", "Din test intermediate",
                     ["basicConstraints=critical,CA:FALSE", ca_usage[1]], issuer=root, key=intermediate.key)
    wrong_ca_ku = c.create("wrong-ca-ku", "Din test intermediate",
                           [ca_usage[0], "keyUsage=critical,digitalSignature"], issuer=root, key=intermediate.key)

    cn_only = c.create("cn-only", "localhost", leaf_usage, issuer=intermediate)
    wildcard = c.create("wildcard", "unused", [*leaf_usage, "subjectAltName=DNS:*.example.test"], issuer=intermediate)
    wrong_eku = c.create("wrong-eku", "localhost", [*leaf_usage[:2], "extendedKeyUsage=clientAuth", san],
                         issuer=intermediate)
    wrong_ku = c.create("wrong-ku", "localhost", [leaf_usage[0], "keyUsage=critical,keyAgreement", leaf_usage[2], san],
                        issuer=intermediate)
    unknown = c.create("unknown", "localhost", [*leaf_usage, san, "1.2.3.4=critical,DER:05:00"], issuer=intermediate)
    constrained = c.create("constrained", "Din test intermediate",
                           [*ca_usage, "nameConstraints=critical,permitted;DNS:.example.test"],
                           issuer=root, key=intermediate.key)
    long_lived = c.create("long-lived", "localhost", [*leaf_usage, san],
                          issuer=intermediate, days=12000)
    altered = leaf.der[:-1] + bytes([leaf.der[-1] ^ 1])
    cases = [
        ("valid ordered chain", trusted_chain, root.der, b"localhost", 0, 0),
        ("explicit root in chain and DNS case folding", trusted_chain + root.der, root.der, b"LOCALHOST", 0, 0),
        ("wildcard matches one label", (wildcard.der + intermediate.der), root.der, b"api.example.test", 0, 0),
        ("wildcard rejects multiple labels", (wildcard.der + intermediate.der), root.der, b"a.b.example.test", 0, 5),
        ("wildcard rejects bare suffix", (wildcard.der + intermediate.der), root.der, b"example.test", 0, 5),
        ("GeneralizedTime notAfter", (long_lived.der + intermediate.der), root.der, b"localhost", 0, 0),
        ("wrong DNS SAN", trusted_chain, root.der, b"other.example", 0, 5),
        ("CN is not a SAN", (cn_only.der + intermediate.der), root.der, b"localhost", 0, 5),
        ("expired leaf", trusted_chain, root.der, b"localhost", 86400 * 3, 2),
        ("not yet valid", trusted_chain, root.der, b"localhost", -86400, 2),
        ("untrusted root with same distinguished name", trusted_chain, wrong_root.der, b"localhost", 0, 4),
        ("missing intermediate", leaf.der, root.der, b"localhost", 0, 4),
        ("altered ECDSA signature", (altered + intermediate.der), root.der, b"localhost", 0, 4),
        ("wrong order", (intermediate.der + leaf.der), root.der, b"localhost", 0, 3),
        ("invalid CA", (leaf.der + no_ca.der), root.der, b"localhost", 0, 3),
        ("CA without keyCertSign", (leaf.der + wrong_ca_ku.der), root.der, b"localhost", 0, 3),
        ("path length exceeded", trusted_chain, limited_root.der, b"localhost", 0, 3),
        ("leaf without digitalSignature", (wrong_ku.der + intermediate.der), root.der, b"localhost", 0, 3),
        ("leaf EKU clientAuth", (wrong_eku.der + intermediate.der), root.der, b"localhost", 0, 3),
        ("unknown critical extension", (unknown.der + intermediate.der), root.der, b"localhost", 0, 1),
        ("unsupported name constraints fail closed", (leaf.der + constrained.der), root.der, b"localhost", 0, 1),
        ("truncated DER chain", trusted_chain[:-1], root.der, b"localhost", 0, 1),
        ("trailing bytes in certificate DER", (leaf.der + b"\0" + intermediate.der), root.der, b"localhost", 0, 1),
        ("IP literal requires another identity profile", trusted_chain, root.der, b"127.0.0.1", 0, 5),
    ]
    return cases, wrong_root


def plain_cases(args, package, cases, now, flags):
    prefix = """
use std::crypto::x509::{validate_server_chain, CertificateError};
fn result_code(chain: &[u8], anchor: &[u8], name: &[u8], now: i64) -> i32 {
    match validate_server_chain(&chain[0..chain.len()], &anchor[0..anchor.len()], &name[0..name.len()], now) {
        Ok(key) => { drop(key); 0 },
        Err(error) => {
            match error {
                CertificateError.InvalidCertificate => { 1 },
                CertificateError.BufferTooSmall => { 6 },
                CertificateError.InvalidTime => { 2 },
                CertificateError.WrongUsage => { 3 },
                CertificateError.UntrustedChain => { 4 },
                CertificateError.NameMismatch => { 5 },
            }
        },
    }
}
"""
    code = []
    calls = []
    for i, (_, presented, anchor, name, offset, _) in enumerate(cases):
        code.append(f"fn case_{i}() -> i32 {{")
        code.extend([binding("presented", presented), binding("anchor", anchor), binding("name", name)])
        code.append(f"result_code(&presented[..], &anchor[..], &name[..], {now + offset})\n}}")
        calls.append(f"print(case_{i}());")
    # build() adds the standard test main; supply this suite's helper functions separately.
    binary = build(args, package, "\n".join(calls), b"", flags, helpers=prefix + "\n".join(code))
    result = subprocess.run([binary], capture_output=True, check=True, timeout=30)
    assert not result.stderr, result.stderr
    actual = list(map(int, result.stdout.splitlines()))
    assert len(actual) == len(cases), actual
    for found, (label, _, _, _, _, expected) in zip(actual, cases):
        assert found == expected, (label, found, expected)
    print(f"{len(cases)} certificate and hostname cases passed", flush=True)


def typed_certificates(args, package, leaf, issuer, signature, now, flags):
    helpers = """
use std::crypto::x509::{Certificate as X509Certificate, PublicKey as X509PublicKey};
use std::net::tls::Certificate as TlsCertificate;
"""
    body = "\n".join((binding("issuer_der", issuer.der), binding("name", b"LOCALHOST"),
                     binding("signed_message", b"Din certificate test"), binding("signature", signature)))
    body += """
let cert = match X509Certificate::from_der(&certificate[..], NOW) {
    Ok(value) => { value }, Err(error) => { drop(error); return 1; },
};
let issuer = match X509Certificate::from_der(&issuer_der[..], NOW) {
    Ok(value) => { value }, Err(error) => { drop(error); return 2; },
};
match cert.matches_dns_name(&certificate[..], &name[..]) {
    Ok(valid) => { if !valid { return 3; } }, Err(error) => { drop(error); return 4; },
};
match cert.matches_dns_name(&issuer_der[..], &name[..]) {
    Ok(valid) => { drop(valid); return 5; }, Err(error) => { drop(error); },
};
match cert.verify_issued_by(&certificate[..], &issuer, &issuer_der[..]) {
    Ok(valid) => { if !valid { return 6; } }, Err(error) => { drop(error); return 7; },
};
let key: X509PublicKey = match cert.public_key() {
    Ok(value) => { value }, Err(error) => { drop(error); return 8; },
};
match key.verify_ecdsa_sha256(&signed_message[..], &signature[..]) {
    Ok(valid) => { if !valid { return 9; } }, Err(error) => { drop(error); return 10; },
};
let frame: [u8; 20] = [11,0,0,16,1,42,0,0,11,0,0,1,48,0,5,0,5,0,1,9];
let tls = match TlsCertificate::from_message(&frame[..]) {
    Ok(value) => { value }, Err(error) => { drop(error); return 11; },
};
let (start, end) = tls.der_range(0);
let (ext_start, ext_end) = tls.extensions_range(0);
let (ctx_start, ctx_end) = tls.context_range();
if tls.count() != 1 || tls.context_length() != 1 || start != 12 || end != 13 {
    return 12;
}
if ctx_start != 5 || ctx_end != 6 || ext_start != 15 || ext_end != 20
   || tls.supports_server_certificate() { return 13; }
match TlsCertificate::from_message(&frame[..19]) {
    Ok(value) => { drop(value); return 14; }, Err(error) => { drop(error); },
};
""".replace("NOW", str(now))
    binary = build(args, package, body, leaf.der, flags, helpers=helpers)
    result = subprocess.run([binary], capture_output=True, timeout=30)
    assert result.returncode == 0 and not result.stderr, (result.returncode, result.stderr)
    print("Typed X.509 and TLS certificate APIs passed", flush=True)


def din_client(args, package, chain_file, leaf, anchor, hostname, now, flags, rejected=False):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.set_ecdh_curve("prime256v1")
    context.num_tickets = 0
    context.load_cert_chain(chain_file, leaf.key)
    seen_names = []
    context.set_servername_callback(lambda _sock, name, _context: seen_names.append(name))
    with socket.create_server(("127.0.0.1", 0)) as listener:
        listener.settimeout(10)
        body = CLIENT[:CLIENT.index("POINT")] + binding("hostname", hostname.encode()) + "\n"
        tail = CLIENT[CLIENT.index("let mut session"):]
        tail = tail.replace("client_handshake(&mut socket, &certificate[..], &peer,",
                            f"client_handshake_x509(&mut socket, &hostname[..], &certificate[..], {now},")
        body = body.replace("PORT", str(listener.getsockname()[1])) + tail
        binary = build(args, package, body, anchor, flags)
        with (TemporaryFile() as errors,
              subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=errors) as child):
            try:
                with listener.accept()[0] as raw:
                    raw.settimeout(10)
                    try:
                        with context.wrap_socket(raw, server_side=True) as peer:
                            assert not rejected
                            assert peer.cipher()[0] == "TLS_AES_128_GCM_SHA256"
                            assert peer.recv(4) == b"PING"
                            peer.sendall(b"PONG")
                            peer.unwrap().close()
                    except (ssl.SSLError, ConnectionResetError):
                        if not rejected:
                            wait(child, 0, errors)
                            raise
                wait(child, 14 if rejected else 0, errors)
                assert seen_names == [hostname], seen_names
            finally:
                if child.poll() is None:
                    child.kill()


def private_layouts(args, package):
    command = [FRONTEND, "emit-c", package]
    if args.corboc:
        command = [args.corboc.resolve(), "--emit-package-c", package,
                   "--stdlib-dir", ROOT / "stdlib/src"]
    for module, name, field in (
        ("std::crypto::x509", "Certificate", "fingerprint"),
        ("std::crypto::x509", "PublicKey", "p256"),
        ("std::net::tls", "Certificate", "der_ranges"),
    ):
        (package / "src/main.crb").write_text(f"""
use {module}::{name};
fn inspect(value: &{name}) {{ let member = &(*value).{field}; drop(member); }}
fn main() {{}}
""")
        rejected = subprocess.run(command, capture_output=True)
        assert rejected.returncode != 0 and b"priv" in rejected.stderr, (name, rejected)
    print("All three certificate and key layouts are private", flush=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--corboc", type=Path)
    cli.add_argument("--cc", default=os.environ.get("CC", "cc"))
    cli.add_argument("--openssl", default="openssl")
    cli.add_argument("--tcp", action="store_true", help="also run both TLS roles against OpenSSL")
    args = cli.parse_args()
    with TemporaryDirectory() as directory:
        package = Path(directory)
        (package / "src").mkdir()
        (package / "package.toml").write_text('[package]\nname = "x509_tests"\n')
        c = Certificates(args.openssl, package)
        root = c.create("root", "Din test root",
                        ["basicConstraints=critical,CA:TRUE,pathlen:2", "keyUsage=critical,keyCertSign,cRLSign"])
        intermediate = c.create("intermediate", "Din test intermediate",
                                ["basicConstraints=critical,CA:TRUE,pathlen:0", "keyUsage=critical,keyCertSign,cRLSign"],
                                issuer=root)
        leaf = c.create("leaf", "localhost",
                        ["basicConstraints=critical,CA:FALSE", "keyUsage=critical,digitalSignature",
                         "extendedKeyUsage=serverAuth", "subjectAltName=DNS:localhost"], issuer=intermediate, days=2)
        chain_pem = package / "chain.pem"
        chain_pem.write_bytes(leaf.cert.read_bytes() + intermediate.cert.read_bytes())
        cases, wrong_root = certificate_cases(c, root, intermediate, leaf)
        now = int(time.time()) + 1
        payload = package / "signed-message"
        payload.write_bytes(b"Din certificate test")
        signature = c.run("dgst", "-sha256", "-sign", leaf.key, payload)
        c.run("verify", "-purpose", "sslserver", "-verify_hostname", "localhost",
              "-attime", str(now), "-CAfile", root.cert, "-untrusted", intermediate.cert, leaf.cert)
        for mode, flags in (
            ("native", ["-O0"]),
            ("UBSan", ["-O2", "-fsanitize=undefined", "-fno-sanitize-recover=all"]),
        ):
            print(mode, flush=True)
            plain_cases(args, package, cases, now, flags)
            typed_certificates(args, package, leaf, intermediate, signature, now, flags)
            if args.tcp:
                din_client(args, package, chain_pem, leaf, root.der, "localhost", now, flags)
                din_client(args, package, chain_pem, leaf, root.der, "wrong.example", now, flags, rejected=True)
                din_client(args, package, chain_pem, leaf, wrong_root.der, "localhost", now, flags, rejected=True)
                din_client(args, package, chain_pem, leaf, root.der, "localhost", now + 86400 * 3, flags, rejected=True)
                server_case(args, package, (root.cert, leaf.key, chain(leaf.der, intermediate.der),
                                           c.signing_scalar(leaf), None), flags, chain=True)
                print("Both TLS roles interoperate with OpenSSL, including SNI and chain/hostname rejection", flush=True)
        private_layouts(args, package)


if __name__ == "__main__":
    main()
