# Native compression

`std::compression::gzip` and `std::compression::zstd` are implemented in Corbo.
They do not call zlib, libzstd, a command-line tool or a C compression bridge.
The reference libraries are used only by the interoperability tests.

## API

```rust
// std::compression::gzip
pub struct Params { level: u32 }
fn Params::new() -> Params // level 6

pub fn compress(input: &[u8], output: &mut [u8], params: &Params,
                workspace: &mut [u64]) -> Result<usize, Error>
pub fn decompress(input: &[u8], output: &mut [u8]) -> Result<usize, Error>

// std::compression::zstd
pub struct Params { level: u32, checksum: bool }
fn Params::new() -> Params // level 3, checksum true

pub fn compress(input: &[u8], output: &mut [u8], params: &Params,
                workspace: &mut [u64]) -> Result<usize, Error>
pub fn decompress(input: &[u8], output: &mut [u8],
                  workspace: &mut [u8]) -> Result<usize, Error>
```

Success returns the number of bytes written. Inputs and workspace are not
retained. An error may leave a partial output prefix; discard that prefix.
The caller's output length is a hard bound on decompressed data.

Both encoders require **36864 `u64` words (288 KiB)** of workspace. Gzip level
zero does not use workspace and accepts an empty slice. Zstd decoding requires
**131072 bytes (128 KiB)** of literal workspace. Decoders also use fixed local
entropy tables. There is no general-purpose heap allocation in these codecs.

### Parameters

- Gzip: level `0` emits stored blocks; levels `1` through `9` control bounded
  LZ77 chain-search effort. Levels 4–9 also compare a dynamic-Huffman literal candidate against the existing fixed/stored candidate.
- Zstd: levels `1` through `22` control bounded LZ77 chain-search effort; `0`
  selects level `3`. `checksum` enables the standard content checksum.

These are the native encoders' effort settings. They do not promise the same
compression ratio or bytes as a reference library at the same numeric level.

## Complete example

```rust
use std::compression::gzip;

fn main() -> i32 {
    let input: [u8; 12] = [97; 12];
    let mut compressed: [u8; 128] = [0; 128];
    let mut decoded: [u8; 12] = [0; 12];
    let mut workspace: [u64; 36864] = [0; 36864];
    let params = gzip::Params::new();

    let count = match gzip::compress(
        &input[..], &mut compressed[..], &params, &mut workspace[..]
    ) {
        Ok(value) => { value },
        Err(error) => { drop(error); return 1; },
    };
    let restored = match gzip::decompress(&compressed[..count], &mut decoded[..]) {
        Ok(value) => { value },
        Err(error) => { drop(error); return 2; },
    };
    print(restored);
    0
}
```

## Coverage and boundaries

Gzip decoding supports stored, fixed-Huffman and dynamic-Huffman DEFLATE,
optional member headers, header CRC, trailer CRC-32, size validation and
concatenated members. Its compressor emits deterministic headers with zero
modification time and no filename/comment.

Zstd decoding supports raw, RLE and compressed blocks; Huffman literals,
FSE sequence tables and repeat modes; repeated offsets; known and unknown
content sizes; checksums; concatenated and skippable frames. The dictionary APIs accept raw-content and formatted dictionaries, including their entropy tables and repeated offsets. Dictionaries are borrowed, not copied or trained by this API.

The Zstd encoder compares LZ77 sequences, raw blocks and compressed Huffman literals. Huffman encoding uses direct weights (at most 128 explicit weights), with one or four literal streams; unsupported or unprofitable trees fall back to the existing encoder. Sequence tables remain RLE encoded; general FSE sequence/weight encoding is not implemented. This is an encoder optimization limit, not a decoder-format limit.

Errors include `InvalidParams`, `WorkspaceTooSmall`, `BufferTooSmall`,
`InvalidData`, `TruncatedInput` and `ChecksumMismatch`; Zstd also provides
`DictionaryRequired`, `DictionaryMismatch` and `InvalidDictionary`.
Streaming additionally reports `InvalidState` and `FrameTooLarge`.

## Zstd dictionaries

```rust
pub fn compress_with_dictionary(input: &[u8], output: &mut [u8], params: &Params,
    workspace: &mut [u64], dictionary: &[u8]) -> Result<usize, Error>
pub fn decompress_with_dictionary(input: &[u8], output: &mut [u8],
    workspace: &mut [u8], dictionary: &[u8]) -> Result<usize, Error>
```

An empty dictionary means no dictionary. A nonempty raw-content dictionary
must contain at least eight bytes. A formatted dictionary must have valid
entropy tables, a nonzero ID and valid repeat offsets. A frame requiring an
absent dictionary returns `DictionaryRequired`; a different ID returns
`DictionaryMismatch`; malformed dictionary metadata returns `InvalidDictionary`.
The encoder uses up to the last 32 KiB of dictionary content as match history.
It writes the formatted ID, but does not reuse dictionary entropy tables to
encode blocks. The decoder loads those tables for frames produced by other
encoders. Dictionary training remains an external operation.

## Bounded streaming

Both codecs expose `Encoder` and `Decoder` with the same processing protocol:

```rust
fn process(&mut self, input: &[u8], output: &mut [u8], finish: bool)
    -> Result<usize, Error> // output bytes written
fn consumed(&self) -> usize // input accepted by the last successful call
fn finished(&self) -> bool  // EOF and all output drained
fn reset(&mut self)         // discard pending data; retain buffers/options
```

Constructors take explicit scalar options and borrow the caller's storage:

```rust
// gzip
fn Encoder::new(level: u32, staging: &mut [u8], pending: &mut [u8],
    workspace: &mut [u64]) -> Encoder
fn Decoder::new(encoded: &mut [u8], decoded: &mut [u8]) -> Decoder

// zstd; pass an empty dictionary slice to disable dictionaries
fn Encoder::new(level: u32, checksum: bool, staging: &mut [u8],
    pending: &mut [u8], workspace: &mut [u64], dictionary: &[u8]) -> Encoder
fn Decoder::new(encoded: &mut [u8], decoded: &mut [u8],
    workspace: &mut [u8], dictionary: &[u8]) -> Decoder
```

The encoder emits one independent Gzip member or Zstd frame per staging chunk.
Its pending buffer needs at least `2 * staging.len() + 128` bytes; staging
must be nonempty and at most `u32::MAX` bytes. The workspace requirement is
unchanged. Unlimited *total* input can be processed through concatenated
bounded frames. History resets between these frames, so chunk size affects
compression ratio.

The decoder buffers and validates **one whole frame** before releasing its
bytes. `encoded` and `decoded` are explicit maximum-frame budgets; this is
not an arbitrary-frame sliding-window decoder. An encoded frame exceeding
its budget returns `FrameTooLarge`; decoded data exceeding its budget returns
`BufferTooSmall`. Gzip can reparse a partial member when more bytes arrive;
very small input fragments can therefore increase CPU cost.

For every successful call, consume exactly `consumed()` input bytes and use
only the returned output prefix. Re-submit unconsumed input. Set `finish=true`
on the final input suffix and keep calling with empty input until `finished()`.
An empty output is permitted and applies backpressure. EOF is latched only
when all supplied input has been accepted; later nonempty input returns
`InvalidState`. A truncated stream at EOF is an error. Codec failures are
sticky until reset. On any error, discard that call's output; earlier
successful output remains usable. Dropping a codec never flushes it.

```rust
use std::compression::gzip;

fn main() -> i32 {
    let input: [u8; 12] = [97; 12];
    let mut staging: [u8; 32] = [0; 32];
    let mut pending: [u8; 192] = [0; 192];
    let mut workspace: [u64; 36864] = [0; 36864];
    let mut codec = gzip::Encoder::new(
        6, &mut staging[..], &mut pending[..], &mut workspace[..]
    );
    let mut output: [u8; 256] = [0; 256];
    let written = match codec.process(&input[..], &mut output[..], true) {
        Ok(count) => { count },
        Err(error) => { drop(error); return 1; },
    };
    // This output is large enough to drain the complete member in one call.
    let accepted = codec.consumed();
    let done = codec.finished();
    print(accepted);
    print(written);
    print(done);
    0
}
```

## Compression improvement evidence

On the deterministic 4096-byte weighted input in the targeted validation:

| Codec | Before entropy candidate | With entropy candidate |
| --- | ---: | ---: |
| Gzip, level 6 | 1297 bytes | 1000 bytes |
| Zstd, level 6 | 4110 bytes | 874 bytes |

These are measured fixture sizes, not a general ratio or speed guarantee.
Both outputs are independently decoded by reference implementations. Native
round trips cover dynamic DEFLATE and one/four-stream Zstd Huffman literals.

## Sources and validation

- [Gzip implementation](../stdlib/src/compression/gzip/gzip.crb)
- [Zstd implementation](../stdlib/src/compression/zstd/)
- [Focused interoperability checks](../validation/check_compression.py)
- [RFC 1951: DEFLATE](https://www.rfc-editor.org/rfc/rfc1951.html)
- [RFC 1952: Gzip](https://www.rfc-editor.org/rfc/rfc1952.html)
- [RFC 8878: Zstandard](https://www.rfc-editor.org/rfc/rfc8878.html)

Zstd entropy decoding was adapted to Corbo using Go's `internal/zstd` reference;
its additional [BSD license and notice](third-party/GO-LICENSE.txt) are retained.
See the cycle report for executed results and platform limitations.
