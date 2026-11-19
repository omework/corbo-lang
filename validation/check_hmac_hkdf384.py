"""Check HMAC-SHA-384 and HKDF-SHA-384 against RFC 4231 and Wycheproof."""
import argparse
import hmac
import json
import os
from pathlib import Path

from check_hmac_hkdf import HMAC, array, expand_reference, run_witness


# RFC 4231 gives both SHA-256 and SHA-384 outputs for these inputs.
HMAC384 = (
    "afd03944d84895626b0825f4ab46907f15f9dadbe4101ec682aa034c7cebc59c"
    "faea9ea9076ede7f4af152e8b2fa9cb6",
    "af45d2e376484031617f78d2b58a6b1b9c7ef464f5a01b47e42ec3736322445e"
    "8e2240ca5e69e2c78b3239ecfab21649",
    "88062608d3e6ad8a0aa2ace014c8a86f0aa635d947ac9febe83ef4e55966144b"
    "2a5ab39dc13814b94e3ab6e101a34f27",
    "3e8a69b7783c25851933ab6290af6ca77a9981480850009cc5577c6e1f573b4e"
    "6801dd23c4a7d679ccf8a386c674cffb",
    "3abf34c3503b2a23a46efc619baef897",
    "4ece084485813e9088d2c63a041bc5b44f9ef1012a2b588f3cd11f05033ac4c6"
    "0c2ef6ab4030fe8296248df163f44952",
    "6617178e941f020d351e2f254e8fd32c602420feb0b8fb9adccebb82461e99c5"
    "a678cc31e799176d3860e6110c46523e",
)

PROGRAM = """
use std::crypto::sha384::{hmac, hkdf_extract, hkdf_expand, KdfError};

fn print_bytes(bytes: &[u8]) {
    let mut i: usize = 0;
    while i < bytes.len() {
        print(bytes[i]);
        i = i + 1;
    }
}

fn derive(prk: &[u8], info: &[u8], output: &mut [u8]) {
    let n = output.len();
    match hkdf_expand(prk, info, &mut output[0..n]) {
        Ok(()) => { print_bytes(&output[0..n]); },
        Err(error) => { drop(error); print(999); },
    };
}

fn refused(prk: &[u8], info: &[u8], output: &mut [u8], too_long: bool) {
    let n = output.len();
    match hkdf_expand(prk, info, &mut output[0..n]) {
        Ok(()) => { print(999); },
        Err(error) => {
            match error {
                KdfError.OutputTooLong => { if !too_long { print(999); } },
                KdfError.InvalidPrkLength => { if too_long { print(999); } },
                KdfError.InputTooLong => { print(999); },
            };
        },
    };
    print_bytes(&output[0..n]);
}

fn main() {
"""


def witness(cases):
    expected = bytearray()
    code = [PROGRAM]
    for (key, message, _), value in zip(HMAC, HMAC384, strict=True):
        tag = bytes.fromhex(value)
        assert hmac.digest(key, message, "sha384")[:len(tag)] == tag
        expected.extend(tag)
        code.extend(("{", array("key", key), array("message", message), f"""
    match hmac(&key[..], &message[..]) {{
        Ok(tag) => {{ print_bytes(&tag[..{len(tag)}]); }},
        Err(error) => {{ drop(error); print(999); }},
    }};
}}"""))

    for case in cases:
        ikm, salt, info = (bytes.fromhex(case[field]) for field in ("ikm", "salt", "info"))
        n = case["size"]
        prk = hmac.digest(salt, ikm, "sha384")
        code.extend(("{", array("ikm", ikm), array("salt", salt), array("info", info)))
        if case["result"] == "valid":
            okm = bytes.fromhex(case["okm"])
            assert expand_reference(prk, info, n, "sha384") == okm
            expected.extend(prk + okm)
            check = "derive(&prk[..], &info[..], &mut output[..]);"
        else:
            assert case["result"] == "invalid" and n > 12240
            expected.extend(prk + bytes([165]) * n)
            check = "refused(&prk[..], &info[..], &mut output[..], true);"
        code.append(f"""
    let mut output: [u8; {n}] = [165; {n}];
    match hkdf_extract(&salt[..], &ikm[..]) {{
        Err(error) => {{ drop(error); print(999); }},
        Ok(prk) => {{
            print_bytes(&prk[..]);
            {check}
        }},
    }};
}}""")

    prk = bytes(range(129))
    info = b"din-keys"
    code.extend((array("prk", prk), array("info", info)))
    for n in (0, 47, 48, 49, 12240):
        expected.extend(expand_reference(prk, info, n, "sha384"))
        code.append(f"""{{
    let mut output: [u8; {n}] = [0; {n}];
    derive(&prk[..], &info[..], &mut output[..]);
}}""")
    code.append("""
    let mut short_prk_output: [u8; 48] = [165; 48];
    refused(&prk[..47], &info[..], &mut short_prk_output[..], false);
}
""")
    expected.extend(bytes([165]) * 48)
    return "\n".join(code), expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wycheproof_json", type=Path)
    parser.add_argument("--corboc", type=Path)
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    args = parser.parse_args()
    vectors = json.loads(args.wycheproof_json.read_text())
    assert vectors["algorithm"] == "HKDF-SHA-384"
    cases = [case for group in vectors["testGroups"] for case in group["tests"]]
    assert len(cases) == vectors["numberOfTests"] and cases
    source, expected = witness(cases)
    run_witness(args, source, expected,
                f"7 HMAC RFC cases, {len(cases)} HKDF Wycheproof cases, and HKDF bounds passed")


if __name__ == "__main__":
    main()
