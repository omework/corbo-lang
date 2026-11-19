# SPDX-License-Identifier: MIT OR Apache-2.0
"""Run the standard library crypto and native TLS validation suites."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
CASES = {
    "system_random": (None, ["--ubsan"]),
    "rust_sha256": (None, []),
    "aes_gcm": ("din-nist-gcm.zip", []),
    "p256": (None, []),
    "encoding_pem": (None, []),
    "crypto_serialization": (None, []),
    "rsa_pkcs8": (None, []),
    "hmac_hkdf": (None, []),
    "hmac_hkdf384": ("din-wycheproof-hkdf384.json", []),
    "sha384_sha512": ("din-nist-sha-byte.zip", []),
    "sha3": ("din-nist-sha3-byte.zip", []),
    "shake": ("din-nist-shake-byte.zip", []),
    "argon2id": (None, []),
    "tls13_keys": (None, []),
    "tls13_record": (None, ["--tcp"]),
    "tls13_handshake": (None, []),
    "x509": (None, ["--tcp"]),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--corboc", type=Path, help="use this self-hosted compiler")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--only", choices=CASES, action="append")
    parser.add_argument("--rsa-timeout", type=float, default=45)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")

    cases = args.only or list(CASES)
    for name in cases:
        fixture, _ = CASES[name]
        if fixture and not (args.fixtures / fixture).is_file():
            parser.error(f"missing fixture for {name}: {args.fixtures / fixture}")
    args.logs.mkdir(parents=True, exist_ok=True)

    def run(name):
        fixture, options = CASES[name]
        command = [sys.executable, ROOT / "validation" / f"check_{name}.py"]
        if fixture:
            command.append((args.fixtures / fixture).resolve())
        command.extend(options)
        if args.corboc:
            command.extend(["--corboc", args.corboc.resolve()])
        if name == "rsa_pkcs8":
            command.extend(["--timeout", str(args.rsa_timeout)])
        path = args.logs / f"{name}.log"
        with path.open("w") as log:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        print(f"{name}: {'PASS' if result.returncode == 0 else 'FAIL'} ({path})", flush=True)
        return result.returncode == 0

    with ThreadPoolExecutor(max_workers=args.jobs) as jobs:
        results = list(jobs.map(run, cases))
    print(f"{sum(results)}/{len(results)} suites passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
