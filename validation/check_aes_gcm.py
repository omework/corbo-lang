"""Check both AES-GCM sizes against the NIST CAVP GCM response archive."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from check_crust_bootstrap import FRONTEND, ROOT


def vectors(archive, per_group):
    with ZipFile(archive) as source:
        for width in (128, 256):
            for operation in ("EncryptExtIV", "Decrypt"):
                groups = {}
                params = {}
                for line in source.read(f"gcm{operation}{width}.rsp").decode("ascii").splitlines():
                    if line.startswith("["):
                        label, value = line[1:-1].split(" = ")
                        params[label] = int(value)
                    elif line.startswith("Count"):
                        group = tuple(params[key] for key in ("Keylen", "IVlen", "PTlen", "AADlen", "Taglen"))
                        rows = groups.setdefault(group, [])
                        record = {}
                        rows.append(record)
                    elif line == "FAIL":
                        record["FAIL"] = True
                    elif " = " in line and not line.startswith("#"):
                        key, value = line.split(" = ")
                        record[key] = bytes.fromhex(value)
                for (_, iv, _, _, tag), rows in groups.items():
                    if iv == 96 and tag == 128:
                        for failed in (False, True):
                            matching = [row for row in rows if ("FAIL" in row) == failed]
                            for row in matching[:per_group]:
                                yield width, operation, row


def array(name, data):
    return f"let {name}: [u8; {len(data)}] = [{','.join(map(str, data))}];"


def program(cases, module):
    yield f"use {module}::{{AES128GCM, AES256GCM, Error}};"
    yield """
fn equal(left: &[u8], right: &[u8]) -> bool {
    let size = left.len();
    if size != right.len() { return false; }
    let mut i: usize = 0;
    while i < size {
        if left[i] != right[i] { return false; }
        i = i + 1;
    }
    true
}

fn authentication_failed(result: Result<(), Error>) -> bool {
    match result {
        Err(error) => {
            match error {
                Error.AuthenticationFailed => { true },
                Error.LengthMismatch => { false },
                Error.InputTooLong => { false },
            }
        },
        Ok(()) => { false },
    }
}
"""
    for index, (width, operation, row) in enumerate(cases):
        failed = "FAIL" in row
        n = len(row["CT"])
        yield f"fn vector_{index}() -> bool {{"
        for variable, field in (("key", "Key"), ("nonce", "IV"), ("aad", "AAD"), ("encrypted", "CT"), ("tag", "Tag")):
            yield "    " + array(variable, row[field])
        yield f"    let cipher = AES{width}GCM::new(&key);"
        yield f"    let mut clear: [u8; {n}] = [165; {n}];"
        if failed:
            yield "    let result = cipher.open(&nonce, &aad[..], &encrypted[..], &tag, &mut clear[..]);"
            yield "    if !authentication_failed(result) { return false; }"
        else:
            yield "    " + array("expected", row["PT"])
            yield """    match cipher.open(&nonce, &aad[..], &encrypted[..], &tag, &mut clear[..]) {
        Ok(()) => {},
        Err(error) => { drop(error); return false; },
    };
    if !equal(&clear[..], &expected[..]) { return false; }"""
            if operation == "EncryptExtIV":
                yield f"    let mut output: [u8; {n}] = [165; {n}];"
                yield """    match cipher.seal(&nonce, &aad[..], &expected[..], &mut output[..]) {
        Ok(actual) => { if !equal(&actual[..], &tag[..]) { return false; } },
        Err(error) => { drop(error); return false; },
    };
    if !equal(&output[..], &encrypted[..]) { return false; }"""
            yield "    " + array("invalid", row["Tag"][:-1] + bytes([row["Tag"][-1] ^ 1]))
            yield f"    let mut clear: [u8; {n}] = [165; {n}];"
            yield "    let rejected = cipher.open(&nonce, &aad[..], &encrypted[..], &invalid, &mut clear[..]);"
            yield "    if !authentication_failed(rejected) { return false; }"
        yield f"    let sentinel: [u8; {n}] = [165; {n}];"
        yield "    equal(&clear[..], &sentinel[..])"
        yield "}"
    yield """
fn length_errors() -> bool {
    let key: [u8; 16] = [0; 16];
    let nonce: [u8; 12] = [0; 12];
    let tag: [u8; 16] = [0; 16];
    let data: [u8; 1] = [0];
    let aad: [u8; 0] = [];
    let mut output: [u8; 2] = [165; 2];
    let cipher = AES128GCM::new(&key);
    match cipher.seal(&nonce, &aad[..], &data[..], &mut output[..]) {
        Err(error) => {
            match error {
                Error.LengthMismatch => {},
                Error.AuthenticationFailed => { return false; },
                Error.InputTooLong => { return false; },
            };
        },
        Ok(tag) => { drop(tag); return false; },
    };
    if output[0] != 165 || output[1] != 165 { return false; }
    match cipher.open(&nonce, &aad[..], &data[..], &tag, &mut output[..]) {
        Err(error) => {
            match error {
                Error.LengthMismatch => {},
                Error.AuthenticationFailed => { return false; },
                Error.InputTooLong => { return false; },
            };
        },
        Ok(()) => { return false; },
    };
    output[0] == 165 && output[1] == 165
}
"""
    yield "fn main() {"
    yield "    print(length_errors());"
    for index in range(len(cases)):
        yield f"    print(vector_{index}());"
    yield "}"


def emit(args, root, code):
    if args.corboc:
        command = [args.corboc, "--emit-package-c", root, "--stdlib-dir", ROOT / "stdlib/src"]
    else:
        command = [FRONTEND, "emit-c", root]
        if args.target:
            command += ["--target", args.target]
    with code.open("wb") as output:
        result = subprocess.run(command, stdout=output, check=False)
    if result.returncode:
        raise AssertionError((result.returncode, code.read_bytes()[:500]))


def execute(args, code, flags):
    binary = code.with_suffix(".exe")
    subprocess.run([*shlex.split(args.cc), "-std=c11", "-pthread", *flags,
                    code, "-lm", "-o", binary], check=True)
    run = subprocess.run([*shlex.split(args.runner), binary],
                         capture_output=True, timeout=120, check=True)
    assert not run.stderr, run.stderr
    return run.stdout.splitlines()


def exercise(args):
    cases = list(vectors(args.nist_zip, args.per_group))
    assert {width for width, _, _ in cases} == {128, 256}
    with TemporaryDirectory(dir=args.tmp_dir) as work:
        root = Path(work)
        (root / "src").mkdir()
        (root / "package.toml").write_text('[package]\nname = "aes_validation"\n')
        main = root / "src/main.crb"
        code = root / "gcm.c"
        library = ROOT / "stdlib/src/crypto/aes"
        # A package-local copy lets the harness query the exact dispatch
        # predicate and force portable execution without a public test API.
        kernels = root / "src/kernel"
        kernels.mkdir()
        (kernels / "hardware.crb").write_text(
            (library / "hardware.crb").read_text()
            + "\npub fn detected() -> bool { hardware_available() }\n"
        )
        (kernels / "aes.crb").write_bytes((library / "aes.crb").read_bytes())
        main.write_text("use aes_validation::kernel::detected; fn main() { print(detected()); }")
        emit(args, root, code)
        detected, = execute(args, code, ["-O0"])
        assert detected in (b"true", b"false"), detected
        if args.require_hardware:
            assert detected == b"true", "the target did not select its accelerated AES-GCM kernels"

        for backend, module in (("auto", "std::crypto::aes"), ("portable", "aes_validation::kernel")):
            if backend == "portable":
                (kernels / "ghash.crb").write_bytes((library / "ghash.crb").read_bytes())
                source = (library / "gcm.crb").read_text()
                selector = "accelerated: hardware_available()"
                assert source.count(selector) == 2
                (kernels / "gcm.crb").write_text(source.replace(selector, "accelerated: false"))
            main.write_text("\n".join(program(cases, module)))
            emit(args, root, code)
            for name, flags in (
                ("native", ["-O0"]),
                ("UBSan", ["-O2", "-fsanitize=undefined", "-fno-sanitize-recover=all"]),
            ):
                result = execute(args, code, flags)
                assert len(result) == len(cases) + 1, (backend, name, len(result))
                failures = [index - 1 for index, line in enumerate(result) if line != b"true"]
                assert not failures, (backend, name, failures)
                print(f"{args.target or 'host'} {backend} {name}: {len(cases)} NIST vectors, "
                      f"tag and size failures left output intact; detected={detected.decode()}", flush=True)

        for width in (128, 256):
            main.write_text(f"""
use std::crypto::aes::AES{width}GCM as Cipher;
fn main() {{
    let fake = Cipher {{ schedule: [0; 240], accelerated: true }};
    drop(fake);
}}
""")
            if args.corboc:
                command = [args.corboc, "--emit-package-c", root, "--stdlib-dir", ROOT / "stdlib/src"]
                refused = subprocess.run(command, capture_output=True, text=True)
                assert refused.returncode == 8 and refused.stdout.splitlines()[:1] == ["1"], refused
            else:
                command = [FRONTEND, "check", root] + (["--target", args.target] if args.target else [])
                refused = subprocess.run(command, capture_output=True, text=True)
                assert refused.returncode and "représentation privée" in refused.stderr, refused
        print("Both expanded key layouts refused external construction", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nist_zip", type=Path)
    parser.add_argument("--per-group", type=int, default=1)
    parser.add_argument("--target")
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    parser.add_argument("--runner", default="")
    parser.add_argument("--corboc", type=Path)
    parser.add_argument("--tmp-dir", type=Path)
    parser.add_argument("--require-hardware", action="store_true")
    args = parser.parse_args()
    if args.per_group < 1:
        parser.error("--per-group must be positive")
    if args.corboc and args.target:
        parser.error("--corboc selects its native target")
    if args.corboc:
        args.corboc = args.corboc.resolve()
    exercise(args)


if __name__ == "__main__":
    main()
