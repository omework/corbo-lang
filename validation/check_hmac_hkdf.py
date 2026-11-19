"""Check Din HMAC-SHA-256 and HKDF-SHA-256 against RFC vectors."""
import argparse
import hashlib
import hmac
import os
from pathlib import Path
import shlex
import subprocess
from tempfile import TemporaryDirectory

from check_crust_bootstrap import FRONTEND, ROOT


# RFC 4231 sections 4.2 to 4.8. Case 5 publishes a 16-byte prefix.
HMAC = (
    (bytes([0x0B]) * 20, b"Hi There",
     "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"),
    (b"Jefe", bytes.fromhex("7768617420646f2079612077616e7420666f72206e6f7468696e673f"),
     "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"),
    (bytes([0xAA]) * 20, bytes([0xDD]) * 50,
     "773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe"),
    (bytes(range(1, 26)), bytes([0xCD]) * 50,
     "82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b"),
    (bytes([0x0C]) * 20, bytes.fromhex("546573742057697468205472756e636174696f6e"),
     "a3b6167473100ee06e0c796c2955552b"),
    (bytes([0xAA]) * 131,
     bytes.fromhex("54657374205573696e67204c6172676572205468616e20426c6f636b2d53697a"
                   "65204b6579202d2048617368204b6579204669727374"),
     "60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54"),
    (bytes([0xAA]) * 131,
     bytes.fromhex("5468697320697320612074657374207573696e672061206c6172676572207468"
                   "616e20626c6f636b2d73697a65206b657920616e642061206c61726765722074"
                   "68616e20626c6f636b2d73697a6520646174612e20546865206b6579206e6565"
                   "647320746f20626520686173686564206265666f7265206265696e6720757365"
                   "642062792074686520484d414320616c676f726974686d2e"),
     "9b09ffa71b942fcb27635fbcd5b0e944bfdc63644f0713938a7f51535c3a35e2"),
)

# RFC 5869 Appendix A.1 to A.3.
HKDF = (
    (bytes([11]) * 22, bytes(range(13)), bytes(range(240, 250)),
     "077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5",
     "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865"),
    (bytes(range(80)), bytes(range(0x60, 0xB0)), bytes(range(0xB0, 0x100)),
     "06a6b88c5853361a06104c9ceb35b45cef760014904671014a193f40c15fc244",
     "b11e398dc80327a1c8e7f78c596a49344f012eda2d4efad8a050cc4c19afa97c"
     "59045a99cac7827271cb41c65e590e09da3275600c2f09b8367793a9aca3db71"
     "cc30c58179ec3e87c14c01d5c1f3434f1d87"),
    (bytes([11]) * 22, b"", b"",
     "19ef24a32c717b167f33a91d6f648bdf96596776afdb6377ac434c1c293ccb04",
     "8da4e775a563c18f715f802a063c5a31b8a11f5c5ee1879ec3454e5f3c738d2d9d201395faa4b61a96c8"),
)


def array(name, data):
    return f"let {name}: [u8; {len(data)}] = [{','.join(map(str, data))}];"


def expand_reference(prk, info, size, algorithm="sha256"):
    block_size = hashlib.new(algorithm).digest_size
    block = b""
    result = bytearray()
    for counter in range(1, (size + block_size - 1) // block_size + 1):
        block = hmac.digest(prk, block + info + bytes([counter]), algorithm)
        result.extend(block)
    return bytes(result[:size])


def witness():
    expected = bytearray()
    code = ["""
use std::crypto::sha256::{hmac, hkdf_extract, hkdf_expand, KdfError};

fn print_bytes(bytes: &[u8]) {
    let mut i: usize = 0;
    while i < bytes.len() {
        print(bytes[i]);
        i = i + 1;
    }
}

fn expand_and_print(prk: &[u8], info: &[u8], output: &mut [u8]) {
    let n = output.len();
    match hkdf_expand(prk, info, &mut output[0..n]) {
        Ok(()) => { print_bytes(&output[0..n]); },
        Err(error) => { drop(error); print(999); },
    };
}

fn main() {
"""]
    for key, message, value in HMAC:
        tag = bytes.fromhex(value)
        assert hmac.digest(key, message, "sha256")[:len(tag)] == tag
        expected += tag
        code.extend(("{", array("key", key), array("message", message), f"""
    match hmac(&key[..], &message[..]) {{
        Ok(tag) => {{ print_bytes(&tag[..{len(tag)}]); }},
        Err(error) => {{ drop(error); print(999); }},
    }};
}}"""))

    for input_material, salt, info, extracted, derived in HKDF:
        prk = bytes.fromhex(extracted)
        okm = bytes.fromhex(derived)
        assert hmac.digest(salt, input_material, "sha256") == prk
        assert expand_reference(prk, info, len(okm)) == okm
        expected += prk + okm
        code.extend(("{", array("input", input_material), array("salt", salt), array("info", info), f"""
    let mut output: [u8; {len(okm)}] = [0; {len(okm)}];
    match hkdf_extract(&salt[..], &input[..]) {{
        Err(error) => {{ drop(error); print(999); }},
        Ok(prk) => {{
            print_bytes(&prk[..]);
            expand_and_print(&prk[..], &info[..], &mut output[..]);
        }},
    }};
}}"""))

    # A 64-byte PRK is valid. Exercise zero, partial, complete and
    # two-block output, then the 255-block counter boundary.
    prk = bytes(range(64))
    info = b"din-keys"
    code.extend((array("prk", prk), array("info", info)))
    for n in (0, 31, 32, 33, 8160):
        expected += expand_reference(prk, info, n)
        code.append(f"""{{
    let mut output: [u8; {n}] = [0; {n}];
    expand_and_print(&prk[..], &info[..], &mut output[..]);
}}""")
    code.append("""
    let mut oversized: [u8; 8161] = [165; 8161];
    match hkdf_expand(&prk[..], &info[..], &mut oversized[..]) {
        Ok(()) => { print(999); },
        Err(error) => {
            match error {
                KdfError.OutputTooLong => {},
                KdfError.InvalidPrkLength => { print(999); },
                KdfError.InputTooLong => { print(999); },
            };
        },
    };
    print_bytes(&oversized[..]);

    let mut small: [u8; 32] = [165; 32];
    match hkdf_expand(&prk[..31], &info[..], &mut small[..]) {
        Ok(()) => { print(999); },
        Err(error) => {
            match error {
                KdfError.InvalidPrkLength => {},
                KdfError.OutputTooLong => { print(999); },
                KdfError.InputTooLong => { print(999); },
            };
        },
    };
    print_bytes(&small[..]);
}
""")
    expected.extend(bytes([165]) * (8161 + 32))
    return "\n".join(code), expected


def run_witness(args, source, expected, summary):
    with TemporaryDirectory() as work:
        root = Path(work)
        (root / "src").mkdir()
        (root / "package.toml").write_text('[package]\nname = "hmac_hkdf_tests"\n')
        (root / "src/main.crb").write_text(source)
        command = [FRONTEND, "emit-c", root]
        if args.corboc:
            command = [args.corboc.resolve(), "--emit-package-c", root, "--stdlib-dir", ROOT / "stdlib/src"]
        result = subprocess.run(command, capture_output=True)
        assert result.returncode == 0, (result.returncode, result.stderr, result.stdout[:500])
        code = root / "witness.c"
        code.write_bytes(result.stdout)
        for mode, flags in (
            ("native", ["-O0"]),
            ("UBSan", ["-O2", "-fsanitize=undefined", "-fno-sanitize-recover=all"]),
        ):
            binary = root / "witness"
            subprocess.run([*shlex.split(args.cc), "-std=c11", "-pthread", *flags,
                            code, "-lm", "-o", binary], check=True)
            actual = subprocess.run([binary], capture_output=True, timeout=60, check=True)
            assert actual.stderr == b"", actual.stderr
            assert list(map(int, actual.stdout.splitlines())) == list(expected), mode
            print(f"{mode}: {summary}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corboc", type=Path)
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    args = parser.parse_args()
    source, expected = witness()
    run_witness(args, source, expected,
                "7 HMAC and 3 HKDF RFC cases, HKDF bounds and untouched error buffers passed")


if __name__ == "__main__":
    main()
