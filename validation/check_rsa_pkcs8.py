# SPDX-License-Identifier: MIT OR Apache-2.0
"""Check RSA key formats and protected PKCS#8 against OpenSSL with either Din compiler."""

import argparse
import os
from pathlib import Path
import shlex
import subprocess
from tempfile import TemporaryDirectory, TemporaryFile

from check_encoding_pem import FRONTEND, ROOT, binding, run_case


def openssl(args, *command, data=None):
    return subprocess.run([args.openssl, *command], input=data, capture_output=True, check=True).stdout


def fixture(args, key, protected):
    def opens(*command, data=key):
        return openssl(args, *command, data=data)

    private_der = opens("pkcs8", "-topk8", "-nocrypt", "-outform", "DER")
    traditional_der = opens("rsa", "-traditional", "-outform", "DER")
    public_der = opens("pkey", "-pubout", "-outform", "DER")
    raw_public = opens("rsa", "-RSAPublicKey_out", "-outform", "DER")
    formats = {
        "private_p8": private_der,
        "private_p1": traditional_der,
        "private_p8_pem": opens("pkcs8", "-topk8", "-nocrypt"),
        "private_p1_pem": opens("rsa", "-traditional"),
        "public_spki": public_der,
        "public_p1": raw_public,
        "public_spki_pem": opens("pkey", "-pubout"),
        "public_p1_pem": opens("rsa", "-RSAPublicKey_out"),
    }
    if protected:
        for name, prf, flags in (
            ("encrypted_der", "hmacWithSHA256", ["-outform", "DER"]),
            ("encrypted_pem", "hmacWithSHA256", []),
            ("unsupported", "hmacWithSHA512", ["-outform", "DER"]),
        ):
            formats[name] = opens("pkcs8", "-topk8", "-v2", "aes-256-cbc", "-iter", "2049",
                                  "-passout", "pass:fixture", "-v2prf", prf, *flags)
        tampered = bytearray(formats["encrypted_der"])
        iv_header = bytes.fromhex("060960864801650304012a0410")
        # Flip the first plaintext byte through the IV. CBC padding remains valid.
        tampered[tampered.index(iv_header) + len(iv_header)] ^= 1
        formats["altered_iv"] = bytes(tampered)
    formats["trailing_public"] = public_der + b"\0"
    formats["wrong_public_label"] = formats["public_spki_pem"].replace(b"PUBLIC KEY", b"RSA PUBLIC KEY")
    return formats


def program(values, protected):
    code = ["""
use std::crypto::rsa::{public_from_der, private_from_der, public_from_pem, private_from_pem,
    public_to_der, private_to_der, public_to_pem, private_to_pem, public_to_pkcs1_pem,
    private_to_pkcs1_pem, Error as RsaError};
use std::crypto::pkcs8::{encrypt_der, encrypt_pem, decrypt_der, decrypt_pem, Error as Pkcs8Error};

fn dump(input: &[u8]) {
    let number = input.len();
    print(copy(number));
    let mut i: usize = 0;
    while i < number { print(input[i]); i = i + 1; }
}

fn main() -> i32 {
"""]
    code.extend(binding(name, value) for name, value in values.items())
    code += [
        binding("password", b"fixture"),
        binding("wrong_password", b"wrong"),
        """
let mut scratch: [u8; 8192] = [90; 8192];
let mut output: [u8; 8192] = [90; 8192];
""",
    ]
    status = 1

    def check(call, name):
        nonlocal status
        size = len(values[name])
        code.append(f"""
output[{size}] = 90;
let length_{status} = match {call} {{
    Ok(written) => {{ written }}, Err(error) => {{ drop(error); return {status}; }},
}};
let piece_{status} = &output[..length_{status}];
if !piece_{status}.content_eq(&{name}[..]) || output[{size}] != 90 {{ return {status}; }}
""")
        status += 1

    for kind, wrapped, raw in (("public", "public_spki", "public_p1"), ("private", "private_p8", "private_p1")):
        check(f"{kind}_from_der(&{wrapped}[..], &mut output[..])", raw)
        check(f"{kind}_from_der(&{raw}[..], &mut output[..])", raw)
        check(f"{kind}_from_pem(&{wrapped}_pem[..], &mut scratch[..], &mut output[..])", raw)
        check(f"{kind}_from_pem(&{raw}_pem[..], &mut scratch[..], &mut output[..])", raw)
        check(f"{kind}_to_der(&{raw}[..], &mut output[..])", wrapped)
        check(f"{kind}_to_pem(&{raw}[..], &mut scratch[..], &mut output[..])", f"{wrapped}_pem")
        check(f"{kind}_to_pkcs1_pem(&{raw}[..], &mut output[..])", f"{raw}_pem")

    enums = {
        "RsaError": ["InvalidKey", "BufferTooSmall"],
        "Pkcs8Error": ["InvalidPrivateKey", "InvalidEnvelope", "InvalidPasswordOrData", "InvalidIterations",
                       "IterationLimit", "BufferTooSmall", "RandomFailed", "InvalidPasswordLength"],
    }

    def expect_error(call, expected):
        nonlocal status
        enum, wanted = expected.split(".")
        arms = ", ".join(f"{enum}.{v} => {{}}" if v == wanted else f"{enum}.{v} => {{ return {status}; }}"
                         for v in enums[enum])
        code.append(f"""
match {call} {{
    Ok(written) => {{ drop(written); return {status}; }},
    Err(error) => {{ match error {{ {arms}, }}; }},
}};
""")
        status += 1

    code.append("let mut small: [u8; 16] = [90; 16];")
    for call, error in (
        ("public_from_der(&trailing_public[..], &mut small[..])", "RsaError.InvalidKey"),
        ("public_from_pem(&wrong_public_label[..], &mut scratch[..], &mut small[..])", "RsaError.InvalidKey"),
        ("private_from_der(&public_spki[..], &mut small[..])", "RsaError.InvalidKey"),
        ("private_to_der(&private_p1[..], &mut small[..])", "RsaError.BufferTooSmall"),
    ):
        expect_error(call, error)
    code.append("let mut i: usize = 0; while i < 16 { if small[i] != 90 { return 30; } i = i + 1; }")

    if not protected:
        return "\n".join(code + ["0", "}"])

    # CBC opens into a ciphertext-sized prefix and clears the padding bytes.
    for call, reference in (
        ("decrypt_der(&encrypted_der[..], &password[..], 2049, &mut output[..])", "private_p8"),
        ("decrypt_pem(&encrypted_pem[..], &password[..], 2049, &mut scratch[..], &mut output[..])", "private_p8"),
        ("decrypt_der(&ec_protected[..], &password[..], 2049, &mut output[..])", "ec_plain"),
    ):
        size = len(values[reference])
        code.append(f"""
let recovered_{status} = match {call} {{
    Ok(written) => {{ written }}, Err(error) => {{ drop(error); return {status}; }},
}};
let recovered_view_{status} = &output[..recovered_{status}];
if recovered_{status} != {size} || !recovered_view_{status}.content_eq(&{reference}[..]) {{ return {status}; }}
""")
        status += 1

    for call, error in (
        ("decrypt_der(&encrypted_der[..], &password[..], 2048, &mut small[..])", "Pkcs8Error.IterationLimit"),
        ("decrypt_der(&encrypted_der[..], &password[..], 2049, &mut small[..])", "Pkcs8Error.BufferTooSmall"),
        ("decrypt_der(&unsupported[..], &password[..], 2049, &mut small[..])", "Pkcs8Error.InvalidEnvelope"),
        ("encrypt_der(&private_p1[..], &password[..], 2049, &mut small[..])", "Pkcs8Error.InvalidPrivateKey"),
        ("encrypt_der(&private_p8[..], &password[..], 0, &mut small[..])", "Pkcs8Error.InvalidIterations"),
    ):
        expect_error(call, error)
    code.append("i = 0; while i < 16 { if small[i] != 90 { return 40; } i = i + 1; }")

    width = len(values["private_p8"]) // 16 * 16 + 16
    for block, password in [("encrypted_der", "wrong_password"), ("altered_iv", "password")]:
        code.append(f"output[0] = 90; output[{width}] = 90;")
        expect_error(f"decrypt_der(&{block}[..], &{password}[..], 2049, &mut output[..])",
                     "Pkcs8Error.InvalidPasswordOrData")
        code.append(f"""
i = 0; while i < {width} {{ if output[i] != 0 {{ return 42; }} i = i + 1; }}
if output[{width}] != 90 {{ return 42; }}
""")

    for call in (
        "encrypt_der(&private_p8[..], &password[..], 2049, &mut output[..])",
        "encrypt_der(&private_p8[..], &password[..], 2049, &mut output[..])",
        "encrypt_pem(&ec_plain[..], &password[..], 2049, &mut scratch[..], &mut output[..])",
    ):
        code.append(f"""
let encoded_{status} = match {call} {{
    Ok(written) => {{ written }}, Err(error) => {{ drop(error); return {status}; }},
}};
dump(&output[..encoded_{status}]);
""")
        status += 1
    return "\n".join(code + ["0", "}"])


def check(args, root, values, bits, protected):
    (root / "src/main.crb").write_text(program(values, protected))
    command = [FRONTEND, "emit-c", root]
    if args.corboc:
        command = [args.corboc.resolve(), "--emit-package-c", root, "--stdlib-dir", ROOT / "stdlib/src"]
    generated = subprocess.run(command, capture_output=True)
    assert generated.returncode == 0, (generated.returncode, generated.stderr, generated.stdout[:150])
    path = root / "check.c"
    path.write_bytes(generated.stdout)
    binary = root / "check"
    for mode, flags in (
        ("native", ["-O0"]),
        ("UBSan", ["-O2", "-fsanitize=undefined", "-fno-sanitize-recover=all"]),
    ):
        subprocess.run([*shlex.split(args.cc), "-std=c11", "-pthread", *flags,
                        path, "-lm", "-o", binary], check=True)
        with TemporaryFile() as output, TemporaryFile() as errors:
            result = subprocess.run([binary], cwd=root, stdout=output, stderr=errors, timeout=args.timeout)
            output.seek(0)
            errors.seek(0)
            stdout, stderr = output.read(), errors.read()
        assert result.returncode == 0 and not stderr, (bits, mode, result.returncode, stderr)
        if protected:
            integers = list(map(int, stdout.splitlines()))
            encrypted = []
            for _ in range(3):
                length, *integers = integers
                encrypted.append(bytes(integers[:length]))
                integers = integers[length:]
            assert not integers and encrypted[0] != encrypted[1]
            for block, fmt, expected in zip(encrypted, ["DER", "DER", "PEM"],
                                            [values["private_p8"]] * 2 + [values["ec_plain"]]):
                unencrypted = openssl(args, "pkey", "-inform", fmt, "-passin", "pass:fixture", data=block)
                canonical = openssl(args, "pkcs8", "-topk8", "-nocrypt", "-outform", "DER", data=unencrypted)
                assert canonical == expected, (bits, mode, fmt)
        print(f"{mode}: RSA-{bits} DER/PEM" + (" and encrypted RSA/P-256 PKCS#8" if protected else ""), flush=True)


def cbc_source(args):
    key, iv = bytes(range(32)), bytes(range(16))
    code = ["use std::crypto::aes::{cbc_encrypt_padded, cbc_decrypt_padded};",
            "fn main() -> i32 {", binding("key", key), binding("iv", iv),
            "let mut output: [u8; 65] = [90; 65];"]
    for index, size in enumerate((0, 16, 17, 48), 1):
        data = bytes(range(size))
        expected = openssl(args, "enc", "-aes-256-cbc", "-K", key.hex(), "-iv", iv.hex(), data=data)
        code.extend([binding(f"plain_{index}", data), binding(f"cipher_{index}", expected), f"""
let encrypted_{index} = match cbc_encrypt_padded(&key, &iv, &plain_{index}[..], &mut output[..]) {{
    Ok(n) => {{ n }}, Err(error) => {{ drop(error); return {index}; }},
}};
let ciphertext_{index} = &output[..encrypted_{index}];
if !ciphertext_{index}.content_eq(&cipher_{index}[..]) {{ return {index}; }}
let recovered_{index} = match cbc_decrypt_padded(&key, &iv, &cipher_{index}[..], &mut output[..]) {{
    Ok(n) => {{ n }}, Err(error) => {{ drop(error); return {index}; }},
}};
let plaintext_{index} = &output[..recovered_{index}];
if !plaintext_{index}.content_eq(&plain_{index}[..]) || output[{len(expected) - 1}] != 0 || output[64] != 90 {{
    return {index};
}}
"""])
    return "\n".join(code + ["0", "}"])


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--corboc", type=Path)
    cli.add_argument("--openssl", default="openssl")
    cli.add_argument("--cc", default=os.environ.get("CC", "cc"))
    cli.add_argument("--timeout", type=float, default=45, help="seconds per generated witness run")
    args = cli.parse_args()
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "src").mkdir()
        (root / "package.toml").write_text('[package]\nname = "rsa_pkcs8_tests"\n')
        run_case(args, root, cbc_source(args), "AES-256-CBC padding and OpenSSL vectors")
        for bits in (2048, 4096):
            key = openssl(args, "genpkey", "-algorithm", "RSA", "-pkeyopt", f"rsa_keygen_bits:{bits}")
            protected = bits == 2048
            values = fixture(args, key, protected)
            if protected:
                ec = openssl(args, "genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256")
                values["ec_plain"] = openssl(args, "pkcs8", "-topk8", "-nocrypt", "-outform", "DER", data=ec)
                values["ec_protected"] = openssl(args, "pkcs8", "-topk8", "-v2", "aes-256-cbc", "-v2prf",
                                                 "hmacWithSHA256", "-iter", "37", "-outform", "DER",
                                                 "-passout", "pass:fixture", data=ec)
            check(args, root, values, bits, protected)


if __name__ == "__main__":
    main()
