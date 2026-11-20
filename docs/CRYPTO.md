# Crypto and TLS

## Coverage

| Area | Covered | Missing or awaiting validation |
| --- | --- | --- |
| AES | AES-128-GCM and AES-256-GCM with caller-owned buffers and detached tags. The library also provides AES-256-CBC with PKCS#7 padding for private-key containers. | AES-192, in-place and streaming APIs, and GCM nonce generation or reuse tracking. |
| AES-GCM backends | Portable Corbo, ARM64 AES and PMULL, and x86-64 AES-NI and PCLMULQDQ. Both compilers passed the portable and CPU-selected paths on Linux x86-64 and on Windows x86-64 under Wine. | Native Windows and side-channel analysis. |
| Hashes and key derivation | SHA-256, SHA-384, SHA-512, SHA-3, and legacy MD5 checksums with one-shot and streaming APIs. SHAKE128 and SHAKE256 with caller-provided output. HMAC and HKDF over SHA-256 and SHA-384, PBKDF2-HMAC-SHA-256, and Argon2id. | SHA-256 SHA-NI execution on x86-64. |
| System randomness | `std::crypto::random::fill` writes into a caller-owned byte slice using the Linux kernel, macOS, or Windows RNG. Both compilers exercised the Linux x86-64 backend and the Windows x86-64 backend under Wine. | Native Windows execution. |
| P-256 | ECDHE, deterministic ECDSA with SHA-256, SEC1 uncompressed public keys, and strict DER signatures in Corbo. Both compilers passed the same suite on macOS ARM64, Linux x86-64, and Windows x86-64 under Wine. | Timing and secret-erasure guarantees. |
| Encoding and serialization | Hex, Base64, and PEM with caller-supplied output. DER and PEM import and serialization for P-256 and two-prime RSA keys and existing P-256 X.509 certificates. Password-protected PKCS#8 with PBES2, PBKDF2-HMAC-SHA-256 and AES-256-CBC. | Additional PBES2 cipher and PRF combinations, PEM bundles, X.509 issuance, and RSA signing and verification. |
| TLS | Native blocking TLS 1.3 in Corbo with P-256, ordered X.509 chains, and DNS SAN verification against an explicit trust anchor. The OpenSSL wrapper remains available with the Rust frontend. | Additional PKIX algorithms and constraints, platform trust stores, broader handshake coverage, and async TLS. |

## Platform validation

Run `python3 validation/check_crypto_stack.py --fixtures VECTORS --logs LOGS`
for the Rust frontend. Add `--corboc PATH` for the self-hosted compiler.
The runner uses the C compiler selected by `CC` and writes a log for
each suite. The fixture directory contains the NIST archives
`din-nist-gcm.zip`, `din-nist-sha-byte.zip`, `din-nist-sha3-byte.zip`, and
`din-nist-shake-byte.zip`, plus `din-wycheproof-hkdf384.json` from the
pinned corpus linked below. The SHA-384/512, SHA-3, and SHAKE suites
read their fixtures through `std::io::sync::File` with both compilers on Linux
and Windows x86-64.

Both compilers completed the client and server handshake against
OpenSSL on Linux x86-64 and with Windows x86-64 executables under Wine.
The [platform cycle report](cycles/CORE_COMPOSITION_CYCLE.md#linux-and-windows-crypto-stack)
records the configurations and remaining validation.

## Hex, Base64 and PEM

`std::encoding::{hex, base64}` each expose `encode` and `decode`.
They take an input `&[u8]` and an output `&mut [u8]`. `Ok(n)` gives
the number of bytes written at the start of the output slice. An error
leaves the output unchanged. Hex encodes with lowercase digits and
decodes either case. `base64::decode` requires the standard alphabet,
canonical padding and no whitespace. `base64::decode_wrapped` also
accepts ASCII spaces, tabs, CR and LF. [RFC 4648](https://www.rfc-editor.org/rfc/rfc4648.html)

| Parser | PEM label | DER contents |
| --- | --- | --- |
| `p256::SigningKey::from_pem(input, scratch)` | `PRIVATE KEY`, `EC PRIVATE KEY` | Unencrypted PKCS#8 `PrivateKeyInfo` or SEC1 `ECPrivateKey` |
| `p256::PublicKey::from_pem(input, scratch)` and `x509::PublicKey::from_pem(input, scratch)` | `PUBLIC KEY` | P-256 `SubjectPublicKeyInfo` with an uncompressed point |
| `x509::Certificate::from_pem(input, scratch, now)` | `CERTIFICATE` | An X.509 certificate with a P-256 public key, parsed at the supplied Unix time |

Each PEM parser takes one block and decodes it into the caller's scratch
slice before calling the DER parser. Supply space for the full DER.
Once decoded, the DER remains in scratch even if parsing fails. When
importing a signing key, treat scratch as private key material. The
certificate parser checks the same constraints as `from_der`. Use
`&scratch[..certificate.der_len()]` for operations that need the backing
DER, such as `matches_dns_name`.
[RFC 7468](https://www.rfc-editor.org/rfc/rfc7468.html),
[RFC 5915](https://www.rfc-editor.org/rfc/rfc5915.html).

```sh
python3 validation/check_encoding_pem.py
python3 validation/check_encoding_pem.py --corboc /path/to/corboc
```

### Serializing keys and certificates

`std::encoding::pem::encode(der, label, output)` wraps a nonempty DER
slice in one PEM block with Base64 lines of up to 64 characters. The
typed methods choose the corresponding labels and write into slices
provided by the caller.

| Object | DER | PEM |
| --- | --- | --- |
| `p256::SigningKey` | `to_der(output)` for PKCS#8 or `to_sec1_der(output)` for SEC1 | `to_pem(output)` for PRIVATE KEY or `to_sec1_pem(output)` for EC PRIVATE KEY |
| `p256::PublicKey`, `x509::PublicKey` | `to_der(output)` for SubjectPublicKeyInfo | `to_pem(output)` for PUBLIC KEY |
| `x509::Certificate` | `to_der(original_der, output)` keeps the original signed bytes | `to_pem(original_der, output)` wraps the original DER in a CERTIFICATE block |

Use the returned length to write only the serialized prefix with
`std::io::sync::File`. The certificate methods verify that the original DER
matches the certificate fingerprint before writing. Private key output is
unencrypted. The caller supplies storage and decides how to protect it.

### RSA key containers

`std::crypto::rsa` reads public keys in PKCS#1 and SubjectPublicKeyInfo
(SPKI), and two-prime private keys in PKCS#1 and version-zero PKCS#8
without attributes.
The `public_from_der`, `private_from_der`, `public_from_pem`, and
`private_from_pem` functions place validated PKCS#1 DER in the caller's
output. PEM imports also take separate DER scratch.

`public_to_der` wraps a PKCS#1 public key in SPKI. `private_to_der` wraps
a PKCS#1 private key in an unencrypted PKCS#8 PrivateKeyInfo.
`public_to_pem` and `private_to_pem` produce `PUBLIC KEY` and `PRIVATE KEY`
with caller-provided DER scratch. Use `public_to_pkcs1_pem` and
`private_to_pkcs1_pem` for the traditional `RSA PUBLIC KEY` and
`RSA PRIVATE KEY` labels. The codec checks framing, positive canonical
integers, and the supported algorithm and key version. Mathematical key
validation and RSA operations remain outside this codec.
[RFC 8017 Appendix A](https://www.rfc-editor.org/rfc/rfc8017.html#appendix-A).

### Password-protected PKCS#8

`std::crypto::pkcs8::{encrypt_der, encrypt_pem, decrypt_der, decrypt_pem}`
transforms version-zero PrivateKeyInfo bytes without attributes. It supports PBES2 with
PBKDF2-HMAC-SHA-256, AES-256-CBC, and PKCS#7 padding. PEM uses the
`ENCRYPTED PRIVATE KEY` label and takes caller-owned DER scratch. The
same API works for an RSA or a P-256 PrivateKeyInfo.

Encryption generates a fresh 16-byte salt and 16-byte IV and takes an
explicit nonzero iteration count. Decryption takes a maximum accepted
iteration count and checks it before deriving a key. Supply output
space for the full ciphertext length. A wrong password, invalid padding,
or malformed decrypted PrivateKeyInfo clears the written prefix. CBC
provides no authentication. Successfully decrypted bytes are ready for
the corresponding algorithm's key parser. [RFC 8018 §6.2](https://www.rfc-editor.org/rfc/rfc8018.html#section-6.2).

```sh
python3 validation/check_rsa_pkcs8.py
python3 validation/check_rsa_pkcs8.py --corboc /path/to/corboc
```

## MD5 and PBKDF2

`std::crypto::md5::digest` returns a 16-byte checksum. Use
`Md5::new()`, `update(bytes)`, and `finish()` to hash successive chunks.
MD5 is for interoperability where collision resistance is unnecessary.
[RFC 1321](https://www.rfc-editor.org/rfc/rfc1321.html),
[RFC 6151](https://www.rfc-editor.org/rfc/rfc6151.html).

`std::crypto::pbkdf2::derive_sha256(password, salt, iterations, output)`
fills the output with PBKDF2-HMAC-SHA-256. The caller supplies a nonzero
iteration count and a nonempty output slice. Argon2id is available for
memory-hard password hashing. [RFC 8018 §5.2](https://www.rfc-editor.org/rfc/rfc8018.html#section-5.2).

```sh
python3 validation/check_crypto_serialization.py
python3 validation/check_crypto_serialization.py --corboc /path/to/corboc
```

## Native TLS 1.3 checklist

The first milestone is a blocking TCP handshake with `secp256r1`,
`ecdsa_secp256r1_sha256`, and `TLS_AES_128_GCM_SHA256`. Use a controlled
P-256 certificate chain for interoperability tests. The existing OpenSSL
wrapper can serve as a reference peer while the native path is developed.

- [x] System randomness with Linux, macOS, and Windows backends.
- [x] P-256 key agreement, ECDSA with SHA-256, and SEC1/DER encoding.
- [x] AES-128-GCM, SHA-256, HMAC-SHA-256, and HKDF-SHA-256. AES-256-GCM
  and the SHA-384 primitives also exist for a second cipher suite.
- [x] TLS transcript, `HKDF-Expand-Label`, traffic key derivation, and
  `Finished`. Both compilers matched [RFC 8448 §3](https://www.rfc-editor.org/rfc/rfc8448.html#section-3).
- [x] TLS record framing and protection with caller-supplied buffers, partial
  TCP reads and writes, directional sequence numbers, AEAD usage limits,
  authenticated decryption, and `close_notify`.
- [x] Client and server handshake state machines, extension negotiation,
  and `CertificateVerify` for the first P-256 profile. Both roles passed
  against OpenSSL with the Rust frontend and `corboc`.
- [x] Certificate authentication for the P-256 profile with DER parsing,
  an explicit trust anchor, ordered path validation, and DNS SAN verification.
  [RFC 5280 §6](https://www.rfc-editor.org/rfc/rfc5280.html#section-6),
  [RFC 9525 §6](https://www.rfc-editor.org/rfc/rfc9525.html#section-6).

The general-purpose conformance work also includes RSA-PSS/SHA-256 for
`CertificateVerify` and certificates, RSA PKCS#1 v1.5/SHA-256 verification
for certificates, and the mandatory extensions and protocol behavior,
including `HelloRetryRequest` and `KeyUpdate`. X25519,
`TLS_AES_256_GCM_SHA384`, and `TLS_CHACHA20_POLY1305_SHA256` are recommended.
[RFC 9846 §9](https://datatracker.ietf.org/doc/html/rfc9846#section-9),
[RFC 9846 §4.7.3](https://datatracker.ietf.org/doc/html/rfc9846#section-4.7.3).

Security validation remains open for generated code that handles secrets,
constant-time checks of authentication values, and erasure of keys and
temporary secrets. P-256 execution evidence currently covers macOS ARM64.

### Native key derivation

`std::net::sync::tls::keys` implements the SHA-256 key schedule for
`TLS_AES_128_GCM_SHA256`. It links independently of the OpenSSL wrapper.

- `Transcript::append` takes handshake bytes in wire order, including
  handshake headers, with record headers stripped. `digest()` snapshots
  the hash while leaving the transcript available for the next fragment.
- `early_secret`, `handshake_secret`, and `master_secret` implement the
  initial full handshake with a 32-byte ECDHE secret. `traffic_secret`
  selects the client or server traffic label for the handshake or
  application stage. `aes128_key` and `traffic_iv` derive its record material.
- `hkdf_expand_label` adds the `tls13 ` prefix and writes into a
  caller-owned slice. `finished_verify_data` and `verify_finished` use the
  transcript hash immediately before the corresponding `Finished`.

The handshake state machine will decide which messages enter the transcript
and when, including the synthetic `message_hash` for `HelloRetryRequest`.
[TLS key schedule and transcript](https://datatracker.ietf.org/doc/html/rfc9846#section-7.1)

```sh
python3 validation/check_tls13_keys.py
python3 validation/check_tls13_keys.py --corboc /path/to/corboc
```

### Native record layer

`std::net::sync::tls::record` encodes the cleartext handshake records
and protects records with AES-128-GCM. It borrows buffers from the caller.
Allocate up to 16,406 bytes for a complete protected wire record and
16,385 bytes for scratch or decrypted content. Smaller buffers are valid
when they fit the record being processed.

- Use `RecordCipher::reader` and `RecordCipher::writer` with the key and
  IV for each direction and traffic phase. Each object starts at sequence
  zero. The writer stops after `2^24` records under one key and returns
  `KeyLimit`. The handshake layer will manage `KeyUpdate` and key replacement.
- `seal` and `open` process one complete record in memory. On successful
  `open`, the application content occupies the first `record.len()` bytes
  of the plaintext buffer. The metadata also exposes its type and closure
  status. An invalid tag leaves the plaintext buffer unchanged.
- `send_record` and `receive_record` loop until the full record has been
  transferred. `close_notify` sends the authenticated closure alert. An
  incoming `close_notify` closes only the read direction, leaving the
  writer available to send its own alert. EOF before a closure alert or
  inside a record is `Truncated`. After a partial transport failure or
  framing error, terminate the connection and discard both directions.

Record protection and closure follow [RFC 9846 §§5–6](https://datatracker.ietf.org/doc/html/rfc9846#section-5).
The handshake will enforce when cleartext records and compatibility
ChangeCipherSpec records are permitted and coordinate closure of both
directions after a fatal alert.

```sh
python3 validation/check_tls13_record.py --tcp
python3 validation/check_tls13_record.py --tcp --corboc /path/to/corboc
```

### Native blocking handshake

`std::net::sync::tls` provides `client_handshake_x509` and
`server_handshake_chain` for a full TLS 1.3 handshake with P-256 ECDHE,
`ecdsa_secp256r1_sha256`, and `TLS_AES_128_GCM_SHA256`.
Both functions borrow an established TCP connection and three buffers.
Provide at least 16,406 bytes for the wire buffer, 16,385 bytes for
record fragments, and enough space for the largest handshake message,
with a minimum of 256 bytes.

- The client takes the expected DNS name, a trusted DER CA certificate,
  and the current Unix time in seconds. It sends the name in SNI and
  validates the chain and DNS SAN before using the leaf public key to
  verify `CertificateVerify`. The original `client_handshake` takes an
  exact DER leaf and its provisioned public key for explicit pinning.
- The server takes a leaf-first TLS `certificate_list` and the leaf's
  P-256 signing key. Each entry is a three-byte big-endian certificate
  length, the DER bytes, and two zero bytes for the extension length.
  `server_handshake` accepts one DER certificate directly. Both server
  entry points verify the client's `Finished` before returning a session.
- `tls::Certificate::from_message` decodes a complete Certificate
  handshake message. It exposes the request context length and the DER
  and extension byte ranges for each entry in the caller's message.
  For server authentication, the current profile requires an empty
  request context and empty entry extensions.
- The resulting `Session` uses separate application traffic keys for
  each direction. Call `write_application`, `read_application`, and
  `shutdown` with the same TCP connection. `read_application` returns
  zero on an authenticated `close_notify`.

Client authentication, `HelloRetryRequest`, post-handshake negotiation,
and fatal-alert mapping are open. Close the underlying TCP connection on
handshake or session error.
[TLS 1.3 handshake and authentication](https://datatracker.ietf.org/doc/html/rfc9846#section-4).

```sh
python3 validation/check_tls13_handshake.py
python3 validation/check_tls13_handshake.py --corboc /path/to/corboc
```

### X.509 certification paths and server identity

`std::crypto::x509::Certificate::from_der(der, now)` parses a certificate
at the supplied Unix time. The value owns its metadata, fingerprint,
and encoded public key. `public_key()` returns an `x509::PublicKey`.
`matches_dns_name(der, name)` and `verify_issued_by(der, issuer, issuer_der)`
check the fingerprints of the supplied DER before consulting the metadata.

`std::crypto::x509::validate_server_chain` validates up to eight
concatenated DER certificates in order, with the leaf first and an
optional copy of the supplied anchor last. The TLS parser passes the
individual DER ranges directly to X.509 path validation. All certificates use P-256 public keys and ECDSA
with SHA-256. Validation checks DER framing, certificate signatures,
issuer and subject names, validity periods, CA Basic Constraints and path
length, and applicable Key Usage and Extended Key Usage. Issuer names
are compared as encoded DER. Unsupported critical extensions and
unsupported path constraints are rejected.

The reference DNS name uses ASCII labels. Verification uses DNS SANs,
with ASCII case folding and a wildcard restricted to one complete
left-most label. Common Name fallback and IP SAN matching are outside
this profile. The anchor and time come from the caller. General path
building, platform trust stores, revocation, and processing of Name
Constraints and certificate policies are open.
[RFC 5280 §6](https://datatracker.ietf.org/doc/html/rfc5280#section-6),
[RFC 9525 §6](https://datatracker.ietf.org/doc/html/rfc9525#section-6).

```sh
python3 validation/check_x509.py --tcp
python3 validation/check_x509.py --tcp --corboc /path/to/corboc
```

## System randomness

`std::crypto::random::fill(output: &mut [u8]) -> Result<(), RandomError>`
fills the entire byte slice on success. An empty slice succeeds without
calling the OS. On failure some bytes may already have been written.
Discard the output whenever the function returns an error.

```rust
use std::crypto::random::fill;

fn main() {
    let mut nonce: [u8; 32] = [0; 32];
    match fill(&mut nonce[..]) {
        Ok(()) => { print(true); },
        Err(error) => { drop(error); print(false); },
    };
}
```

Calls request up to 256 bytes at a time. Linux uses `getrandom` with
flags zero, macOS uses `getentropy`, and Windows uses
`BCryptGenRandom` with the system-preferred RNG. Linux can block until
the kernel RNG is ready. The function resumes short reads and retries
interrupted Unix calls. `RandomError.Os { code }` carries a negative
Unix errno or a signed Windows NTSTATUS. `RandomError.InvalidCount`
reports a zero or oversized successful read count. Windows builds
link the system BCrypt import library.

```sh
python3 validation/check_system_random.py --ubsan
python3 validation/check_system_random.py --ubsan --corboc /path/to/corboc
```

## P-256

`std::crypto::p256` shares finite-field, scalar, and Jacobian point
arithmetic between ECDHE and ECDSA.

- `EphemeralKey::generate()` draws a private scalar from the OS RNG.
  `agree(self, &peer, &mut shared)` consumes the key and writes the
  32-byte, big-endian shared x-coordinate. A TLS implementation
  passes that value to its key schedule.
- `SigningKey::generate()` uses the same scalar sampling.
  `SigningKey::from_bytes(&private)` accepts a 32-byte big-endian
  scalar in `[1, n)`. Both private key types expose `public_key()`.
- `PublicKey::from_sec1_uncompressed(bytes)` accepts exactly 65 bytes
  starting with `0x04`. Coordinates must be below the field modulus
  and satisfy the curve equation. `to_sec1_uncompressed()` emits the
  same format.
- `sign_sha256(message, &mut output)` uses deterministic RFC 6979
  nonces. The caller supplies a 72-byte buffer, receives the length of
  the DER signature, and retains the original bytes beyond that length.
  `verify_sha256(&key, message, signature)` returns `Ok(false)` for
  a signature mismatch and `Err(Error.InvalidSignature)` for invalid
  DER or out-of-range scalars.

The implementation has functional validation on macOS ARM64. The
generated code has no established constant-time guarantee, and private
keys and temporary secrets have no guaranteed erasure. See the
[P-256 validation report](cycles/CORE_COMPOSITION_CYCLE.md#native-p-256).

```sh
python3 validation/check_p256.py
python3 validation/check_p256.py --corboc /path/to/corboc
```

## AES-GCM

`std::crypto::aes` exposes `AES128GCM::new(&key)` and
`AES256GCM::new(&key)` for 16- and 32-byte keys. The private context stores
a fixed-size expanded key. The caller supplies the nonce, associated data,
and both message buffers. The nonce has 12 bytes and the detached tag has
16 bytes.

- `seal(&nonce, aad, plaintext, ciphertext)` requires equal message
  lengths and returns the tag.
- `open(&nonce, aad, ciphertext, &tag, plaintext)` checks the full tag
  before writing any plaintext. A rejected operation leaves the
  destination unchanged.

The caller must use a unique nonce for each message sealed under a key,
including across separate contexts. The implementation checks the GCM
message and associated-data bounds before accessing the buffers. See
[NIST SP 800-38D](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-38d.pdf).

The portable path computes the AES S-box with fixed field operations
and multiplies GHASH coefficients with masks and fixed loops. ARM64 uses
`AESE`, `AESMC`, `PMULL` and `PMULL2`. x86-64 uses AES-NI and
`PCLMULQDQ`. The constructor chooses the accelerated path when the CPU
advertises both capabilities. Key expansion, padding, GHASH reduction and
tag verification are shared Corbo code. AES-GCM builds without OpenSSL.

Download the official [NIST GCM vectors](https://csrc.nist.gov/Projects/cryptographic-algorithm-validation-program/cavp-testing-block-cipher-modes#GCMVS)
and run the same witness with either compiler.

```sh
python3 validation/check_aes_gcm.py /path/to/gcmtestvectors.zip
python3 validation/check_aes_gcm.py /path/to/gcmtestvectors.zip --corboc /path/to/corboc
```

## SHA-256

`std::crypto::sha256` implements SHA-256 in Corbo. `digest(&input[..])`
returns `Result<[u8; 32], HashError>`. For streaming, create a
`Sha256::new()`, call `update` with each slice, then call `finish()` to
consume the hasher and return the 32 digest bytes. The state and partial
block have fixed size. The overflow check runs before an update changes
either one.

Corbo computes the message schedule and padding. The kernel uses the SHA
instructions on macOS ARM64 and on x86-64 when the CPU exposes SHA-NI,
SSSE3, and SSE4.1. `Sha256::portable()` selects the Corbo round function
directly, and `hardware_accelerated()` reports the selected path. SHA-256
programs link without OpenSSL.

```sh
python3 validation/check_rust_sha256.py
python3 validation/check_rust_sha256.py --corboc /path/to/corboc
```

On macOS ARM64, both compilers run the one-shot and streaming API. The
call to `finish` moves the context and makes its original binding
unavailable. Both compilers restrict direct access to the context layout
to the file that defines it. Callers create contexts with `Sha256::new()`
or `Sha256::portable()` and access them through their methods.

## SHA-384 and SHA-512

`std::crypto::sha512` exports `Sha384`, `Sha512`, `digest384`, and
`digest512`. Both contexts expose `new()`, `update(&bytes[..])`, and a
consuming `finish()`. The digests have 48 and 64 bytes respectively.

The two variants share the Corbo compression function, the 128-byte
buffer, and the padding with a 128-bit bit-length field. They use
distinct initial states, as specified by
[FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final).

Download the [NIST byte-oriented SHA vectors](https://csrc.nist.gov/Projects/Cryptographic-Algorithm-Validation-Program/Secure-Hashing#TestVectors)
to run the short and long message corpus with either compiler.

```sh
python3 validation/check_sha384_sha512.py /path/to/shabytetestvectors.zip
python3 validation/check_sha384_sha512.py /path/to/shabytetestvectors.zip --corboc /path/to/corboc
```

## SHA-3

`std::crypto::sha3` implements the four fixed-output SHA-3 variants specified in
[FIPS 202](https://csrc.nist.gov/pubs/fips/202/final). They share the Keccak
permutation, byte absorption, padding, and digest serialization in Corbo.
Each context and its scratch space have fixed size.

| Streaming context | One-shot function | Bytes per absorption block | Digest bytes |
| --- | --- | ---: | ---: |
| `Sha3_224` | `digest224` | 144 | 28 |
| `Sha3_256` | `digest256` | 136 | 32 |
| `Sha3_384` | `digest384` | 104 | 48 |
| `Sha3_512` | `digest512` | 72 | 64 |

Each context starts with `new()`, accepts byte slices through `update()`,
and is consumed by `finish()`, which returns a fixed-size byte array.
The state tracks the position in the current absorption block. Updating
doesn't need a total byte counter or a fallible length check.

```rust
use std::crypto::sha3::{Sha3_256, digest256};

fn main() {
    let bytes: [u8; 3] = [97, 98, 99];
    let input = &bytes[..];
    let direct = digest256(&input[0..3]);
    let mut hash = Sha3_256::new();
    hash.update(&input[0..1]);
    hash.update(&input[1..3]);
    let streamed = hash.finish();
    let expected = &direct[..];
    print(expected.content_eq(&streamed[..]));
}
```

Download the [NIST byte-oriented SHA-3 archive](https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Algorithm-Validation-Program/documents/sha3/sha-3bytetestvectors.zip)
to run the short, long, and Monte Carlo tests with either compiler.

```sh
python3 validation/check_sha3.py /path/to/sha-3bytetestvectors.zip
python3 validation/check_sha3.py /path/to/sha-3bytetestvectors.zip --corboc /path/to/corboc
```

## SHAKE128 and SHAKE256

`std::crypto::sha3` also exports two one-shot extendable-output functions.

```rust
use std::crypto::sha3::shake128;

fn main() {
    let message: [u8; 3] = [97, 98, 99];
    let mut output: [u8; 200] = [0; 200];
    shake128(&message[..], &mut output[..]);
    print(output[0]);
}
```

Both `shake128(input: &[u8], output: &mut [u8])` and
`shake256(input: &[u8], output: &mut [u8])` fill exactly the output slice.
An empty output slice is valid. The sponge retains a fixed-size state,
and each call starts at the beginning of the output stream for that
message. SHAKE shares the Keccak permutation with SHA-3 and uses the
SHAKE domain suffix and absorption rates specified in
[FIPS 202](https://csrc.nist.gov/pubs/fips/202/final).

Download the [NIST byte-oriented SHAKE archive](https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Algorithm-Validation-Program/documents/sha3/shakebytetestvectors.zip)
to run the short, long, variable-output, and Monte Carlo tests.

```sh
python3 validation/check_shake.py /path/to/shakebytetestvectors.zip
python3 validation/check_shake.py /path/to/shakebytetestvectors.zip --corboc /path/to/corboc
```

## HMAC-SHA-256 and HKDF-SHA-256

These operations use the incremental SHA-256 implementation in
`std::crypto::sha256`. The only scratch buffers have fixed size.

- `hmac(key, message)` returns the full 32-byte authentication tag.
  It hashes keys longer than one SHA-256 block before computing the tag.
- `hkdf_extract(salt, input_key_material)` returns a 32-byte
  pseudorandom key. An empty salt uses the RFC default.
- `hkdf_expand(prk, info, &mut output[..])` derives exactly the number
  of bytes requested by the output slice. It accepts pseudorandom keys
  of at least 32 bytes and outputs of at most 8,160 bytes. The function
  checks the lengths before writing to the destination.

```sh
python3 validation/check_hmac_hkdf.py
python3 validation/check_hmac_hkdf.py --corboc /path/to/corboc
```

## HMAC-SHA-384 and HKDF-SHA-384

`std::crypto::sha384` exposes the same `hmac`, `hkdf_extract`, and
`hkdf_expand` functions over the existing incremental SHA-384
implementation. HMAC and Extract return 48 bytes. Expand accepts a PRK
of at least 48 bytes and writes up to 12,240 bytes directly into the
caller's slice. A short PRK or oversized destination is rejected
before writing.

The validation harness uses the SHA-384 outputs from
[RFC 4231](https://www.rfc-editor.org/rfc/rfc4231.html#section-4) and
the pinned [Wycheproof HKDF-SHA-384 corpus](https://github.com/C2SP/wycheproof/blob/b61843a9a5115bb758134b6a1f5d5e502d445342/testvectors_v1/hkdf_sha384_test.json).

```sh
python3 validation/check_hmac_hkdf384.py /path/to/hkdf_sha384_test.json
python3 validation/check_hmac_hkdf384.py /path/to/hkdf_sha384_test.json --corboc /path/to/corboc
```

## Argon2id

`std::crypto::argon2id` exposes `Params { passes, lanes }` and
`derive(password, salt, params, work, output) -> Result<(), Error>`.
The function accepts a mutable slice of `[u64; 128]` blocks. Each block
occupies 1 KiB, so the length of the slice sets the memory parameter.
The output is a mutable byte slice and its length sets the tag size.
The implementation processes the lanes sequentially.

```rust
use std::crypto::argon2id::{Params, derive};

fn main() {
    let password: [u8; 7] = [101, 120, 101, 109, 112, 108, 101];
    // Example salt. Generate a unique random salt for a real password.
    let salt: [u8; 16] = [
        31, 209, 50, 7, 94, 165, 201, 13,
        77, 224, 103, 151, 60, 182, 41, 248,
    ];
    let mut tag: [u8; 32] = [0; 32];

    #(stack_region: max_size=64M, count=1)
    {
        let mut buffers = Pool<Vector<[u64; 128]>>::new(1);
        let mut work = buffers.new();
        let mut count: usize = 0;
        while count < 65536 {
            let block: [u64; 128] = [0; 128];
            work.push(block);
            count = count + 1;
        }
        let params = Params { passes: 3, lanes: 4 };
        match derive(&password[..], &salt[..], params, &mut work[..], &mut tag[..]) {
            Ok(()) => {},
            Err(error) => { drop(error); print(false); return; },
        };
    }
    print(true);
}
```

The region limits the vector payload to 65,536 blocks and the vector
starts empty. The mutable slice covers its initialized elements. Each
successful call clears the used work blocks before returning. When
the supplied length is not a multiple of four times the lane count,
the original length is included in the hash and the unused trailing
blocks are left intact. The password and salt are borrowed. The
public entry point uses empty optional secret and associated-data
fields. [RFC 9106](https://www.rfc-editor.org/rfc/rfc9106.html#section-3)

```sh
python3 validation/check_argon2id.py
python3 validation/check_argon2id.py --corboc /path/to/corboc
```

## OpenSSL TLS backend

`std::net::sync::tls::openssl` provides blocking TLS 1.3 over
`std::net::sync::tcp`. This implementation uses OpenSSL 3 on macOS ARM64.
The Rust-built compiler links the provider when the package imports
`std::net::sync::tls::openssl`. Set `DIN_OPENSSL_LIB_DIR` if the library directory is
outside the linker's search path.

```sh
DIN_OPENSSL_LIB_DIR=/opt/homebrew/opt/openssl@3/lib \
  build/rust_frontend/debug/corbo-frontend build ./my-package -o ./my-program
```

For `emit-c` builds, pass `-lssl -lcrypto` to the C linker and add the
provider directory with `-L` as needed.

```rust
use std::net::sync::tls::openssl as tls;
use std::net::sync::tcp;

fn secure(
    socket: tcp::Connection,
    hostname: &[u8],
    trust_file: &[u8],
) -> Result<tls::Connection, tls::TlsError> {
    tls::connect(socket, hostname, trust_file)
}
```

- `tls::connect(socket, hostname, trust_file)` takes ownership of an
  established TCP connection. It sends the hostname in SNI and verifies
  the peer certificate chain against the supplied PEM trust file and
  the certificate identity against the hostname.
- `tls::accept(socket, certificate, private_key)` takes an accepted TCP
  socket and performs the server handshake using a PEM certificate chain
  and unencrypted PEM private key. Paths and hostnames use byte slices
  with a single trailing NUL.
- `connection.read(&mut buffer[..])` and `connection.write(&buffer[..])`
  report the number of bytes transferred. A nonempty read returns zero
  after a clean TLS end of stream. A TCP disconnect without a TLS alert
  reports `TransportFailed`.
- `connection.close()` consumes the connection and sends the TLS close
  alert. Scope exit frees the TLS session and closes its TCP socket.
  A failed handshake also releases the supplied TCP socket.

The caller supplies the application buffers. OpenSSL allocates its own
handshake, certificate, and record storage. This release has no guaranteed
per-connection memory bound. Hybrid key exchange policy and asynchronous
connections remain open.

The self-hosted `corboc` verifier currently reports an unsupported
by-value receiver for `Connection.close()`. Use the Rust-built frontend
for this package.

The test uses locally generated certificates and independent Python TLS peers.

```sh
python3 validation/check_rust_tls.py \
  --openssl-lib-dir /opt/homebrew/opt/openssl@3/lib \
  --openssl /opt/homebrew/opt/openssl@3/bin/openssl
```
