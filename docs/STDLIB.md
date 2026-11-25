# Corbo standard library reference

Generated from source documentation. Do not edit this reference by hand.

Public declarations and their target conditions are listed below.
Implementation fields are shown for context; listing them does not grant public field access.
Internal and platform helpers are documented in the linked source files.
Compiler-backed collection methods are described in the [collection API guide](COLLECTIONS_API.md).

Regenerate with `python3 scripts/stdlib_docs.py > docs/STDLIB.md`.

## Modules

- [`runtime::metrics`](#runtimemetrics)
- [`std`](#std)
- [`std::collections`](#stdcollections)
- [`std::compression::gzip`](#stdcompressiongzip)
- [`std::compression::zstd`](#stdcompressionzstd)
- [`std::crypto::aes`](#stdcryptoaes)
- [`std::crypto::argon2id`](#stdcryptoargon2id)
- [`std::crypto::md5`](#stdcryptomd5)
- [`std::crypto::p256`](#stdcryptop256)
- [`std::crypto::pbkdf2`](#stdcryptopbkdf2)
- [`std::crypto::pkcs8`](#stdcryptopkcs8)
- [`std::crypto::random`](#stdcryptorandom)
- [`std::crypto::rsa`](#stdcryptorsa)
- [`std::crypto::sha256`](#stdcryptosha256)
- [`std::crypto::sha3`](#stdcryptosha3)
- [`std::crypto::sha384`](#stdcryptosha384)
- [`std::crypto::sha512`](#stdcryptosha512)
- [`std::crypto::x509`](#stdcryptox509)
- [`std::encoding::base64`](#stdencodingbase64)
- [`std::encoding::binary`](#stdencodingbinary)
- [`std::encoding::der`](#stdencodingder)
- [`std::encoding::hex`](#stdencodinghex)
- [`std::encoding::pem`](#stdencodingpem)
- [`std::env`](#stdenv)
- [`std::io`](#stdio)
- [`std::io::asyn`](#stdioasyn)
- [`std::io::asyn::buffered`](#stdioasynbuffered)
- [`std::io::buffered`](#stdiobuffered)
- [`std::iter`](#stditer)
- [`std::net`](#stdnet)
- [`std::net::asyn::tcp`](#stdnetasyntcp)
- [`std::net::asyn::udp`](#stdnetasynudp)
- [`std::net::http`](#stdnethttp)
- [`std::net::ipv4`](#stdnetipv4)
- [`std::net::tcp`](#stdnettcp)
- [`std::net::tls`](#stdnettls)
- [`std::net::tls::keys`](#stdnettlskeys)
- [`std::net::tls::openssl`](#stdnettlsopenssl)
- [`std::net::tls::record`](#stdnettlsrecord)
- [`std::net::udp`](#stdnetudp)
- [`std::num`](#stdnum)
- [`std::sync`](#stdsync)
- [`std::sync::asyn`](#stdsyncasyn)
- [`std::sync::asyn::channel`](#stdsyncasynchannel)
- [`std::sync::channel`](#stdsyncchannel)
- [`std::text`](#stdtext)
- [`std::time`](#stdtime)
- [`std::time::asyn`](#stdtimeasyn)

## `runtime::metrics`

Concurrency-safe process-wide Corbo storage counters; excludes process RSS.

### `MemoryStats`

[metrics.crb:5](../stdlib/src/runtime/metrics/metrics.crb#L5)

```rust
pub struct MemoryStats
```

Byte counts for managed fixed datastacks, pool storage and growing regions.

Members:

- [`reserved_bytes`](../stdlib/src/runtime/metrics/metrics.crb#L7) (implementation field): Reserved virtual address bytes; committed storage is a subset.
- [`committed_bytes`](../stdlib/src/runtime/metrics/metrics.crb#L9) (implementation field): Committed managed pages, not physical resident memory.
- [`occupied_bytes`](../stdlib/src/runtime/metrics/metrics.crb#L11) (implementation field): Fixed cursor spans plus live region payload, excluding unused pool slots.

### `MemoryStats::reserved`

[metrics.crb:14](../stdlib/src/runtime/metrics/metrics.crb#L14)

```rust
fn reserved(&self) usize
```

Returns sampled reserved virtual address bytes.

### `MemoryStats::committed`

[metrics.crb:16](../stdlib/src/runtime/metrics/metrics.crb#L16)

```rust
fn committed(&self) usize
```

Returns sampled committed managed pages in bytes, independently of OS RSS.

### `MemoryStats::occupied`

[metrics.crb:18](../stdlib/src/runtime/metrics/metrics.crb#L18)

```rust
fn occupied(&self) usize
```

Returns sampled occupied bytes, excluding unused pool slots.

### `memory_stats`

[metrics.crb:22](../stdlib/src/runtime/metrics/metrics.crb#L22)

```rust
pub fn memory_stats() MemoryStats
```

Samples atomic counters without pausing workers. Fields may reflect adjacent instants.


## `std`

Root STD exports for the existing native collection types.
Files in this directory belong to `std`, so import with `use std::{Pool, PoolError, Vector, HashMap, String};`.
These declarations bind compiler-provided types, not empty record layouts.
Storage, operations and dependency tracking retain their existing native implementation.

### `Vector`

[collections.crb:15](../stdlib/src/collections.crb#L15)

```rust
pub struct Vector<T>
```

A contiguous, region-backed sequence of owned values of type T, initially empty.
`Vector::new()` creates a standalone descriptor for values and references;
its payload uses the construction scope's region and owns element cleanup.
Retained references preserve their lifetime/access dependencies. Pool construction remains
available as `Pool<Vector<T>>::new(...).new()` and returns A<Vector<T>>.

### `HashMap`

[collections.crb:20](../stdlib/src/collections.crb#L20)

```rust
pub struct HashMap<K, V>
```

A region-backed map with integer or boolean keys and stable entry storage.
`insert` moves its arguments; `get` and `get_mut` borrow values by borrowed key.

### `String`

[collections.crb:27](../stdlib/src/collections.crb#L27)

```rust
pub struct String
```

An owned, region-backed UTF-8 string with the existing String operations.
`String::new()` creates a standalone descriptor, with bytes in a region.
Pool construction remains available; borrowed views retain their owner.
`split(separator)` returns `std::text::Split`, yielding borrowed `&str` pieces.

### `Pool`

[collections.crb:33](../stdlib/src/collections.crb#L33)

```rust
pub struct Pool<T>
```

Fixed-capacity typed slot storage on the datastack; allocations retain its lifetime.
`Pool<T>::new(capacity)` creates storage; `new` allocates or terminates on exhaustion.
`try` returns `Result<A<T>, PoolError>` and consumes its supplied value on both paths.

### `PoolError`

[collections.crb:37](../stdlib/src/collections.crb#L37)

```rust
pub enum PoolError
```

Recoverable failure to allocate a slot in an existing typed pool.

Members:

- [`Full`](../stdlib/src/collections.crb#L39) (variant): No free slot remains in the selected enum arm (or ordinary element pool).

### `BoundedStringError`

[collections.crb:43](../stdlib/src/collections.crb#L43)

```rust
pub enum BoundedStringError
```

Reports content exceeding a bounded inline string's byte capacity.

Members:

- [`TooLong`](../stdlib/src/collections.crb#L45) (variant): The full UTF-8 input does not fit; the destination remains unchanged.

### `BoundedString`

[collections.crb:51](../stdlib/src/collections.crb#L51)

```rust
pub struct BoundedString<N>
```

Fixed-layout template selected by String<N>; length plus N inline bytes.
Import std::String to make the bounded spelling available to a package.
No field is writable outside this STD module; constructors retain UTF-8.

Members:

- [`length`](../stdlib/src/collections.crb#L53) (implementation field): Current UTF-8 byte count, always no greater than N.
- [`data`](../stdlib/src/collections.crb#L55) (implementation field): Inline storage; unused bytes are zeroed by construction and set.

### `BoundedString::new`

[collections.crb:58](../stdlib/src/collections.crb#L58)

```rust
fn new() BoundedString<N>
```

Constructs an empty inline string without an allocation.

### `BoundedString::try_from`

[collections.crb:62](../stdlib/src/collections.crb#L62)

```rust
fn try_from(text: &str) Result<BoundedString<N>, BoundedStringError>
```

Copies a complete UTF-8 input or returns TooLong without truncation.

### `BoundedString::capacity`

[collections.crb:70](../stdlib/src/collections.crb#L70)

```rust
fn capacity(&self) usize
```

Returns the compile-time byte capacity.

### `BoundedString::len`

[collections.crb:72](../stdlib/src/collections.crb#L72)

```rust
fn len(&self) usize
```

Returns the current byte length, not a character count.

### `BoundedString::set`

[collections.crb:74](../stdlib/src/collections.crb#L74)

```rust
fn set(&mut self, text: &str) Result<(), BoundedStringError>
```

Replaces the content, retaining the old value if the input is too long.

### `BoundedString::as_str`

[collections.crb:93](../stdlib/src/collections.crb#L93)

```rust
fn as_str(&self) Result<&str, Utf8Error>
```

Borrows validated UTF-8 text without allocating or copying its payload.

### `BoundedString::as_bytes`

[collections.crb:98](../stdlib/src/collections.crb#L98)

```rust
fn as_bytes(&self) &[u8]
```

Borrows the used bytes; mutation and moves respect the ordinary loan rules.


## `std::collections`

Standalone UTF-8 strings with datastack descriptors and region-backed bytes.

### `StringValue`

[string_value.crb:7](../stdlib/src/collections/string_value.crb#L7)

```rust
pub struct StringValue
```

Owns a growing UTF-8 byte region without a user-facing allocation pool.
Moves transfer cleanup; shared views retain a borrow of this descriptor.

Members:

- [`raw`](../stdlib/src/collections/string_value.crb#L9) (implementation field): Stable runtime region registration, retained across descriptor moves.
- [`anchor`](../stdlib/src/collections/string_value.crb#L11) (implementation field): Zero-sized lifetime anchor for shared views into the owned payload.

### `StringValue::new`

[string_value.crb:14](../stdlib/src/collections/string_value.crb#L14)

```rust
pub fn new() StringValue
```

Creates an empty string under the current growing-region policy.

### `StringValue::byte_len`

[string_value.crb:20](../stdlib/src/collections/string_value.crb#L20)

```rust
pub fn byte_len(&self) usize
```

Returns the encoded byte length, which can differ from character count.

### `StringValue::is_empty`

[string_value.crb:30](../stdlib/src/collections/string_value.crb#L30)

```rust
pub fn is_empty(&self) bool
```

Reports whether this string contains no bytes.

### `StringValue::push_str`

[string_value.crb:34](../stdlib/src/collections/string_value.crb#L34)

```rust
pub fn push_str(&mut self, text: &str)
```

Appends valid UTF-8 bytes by copy; the argument remains borrowed.
Growth enforces the region's byte limit and reserves mutable access.

### `StringValue::as_bytes`

[string_value.crb:44](../stdlib/src/collections/string_value.crb#L44)

```rust
pub fn as_bytes(&self) &[u8]
```

Borrows the initialized bytes. The unchecked pointer substitution keeps
the ordinary self-borrow established through the zero-sized anchor.

### `StringValue::as_str`

[string_value.crb:56](../stdlib/src/collections/string_value.crb#L56)

```rust
pub fn as_str(&self) &str
```

Borrows UTF-8 text. Construction and append maintain the UTF-8 invariant.

### `StringValue::split`

[string_value.crb:64](../stdlib/src/collections/string_value.crb#L64)

```rust
pub fn split(&self, separator: &str) Split
```

Returns an allocation-free iterator borrowing this string and separator.

### `StringValue::drop`

[string_value.crb:70](../stdlib/src/collections/string_value.crb#L70)

```rust
pub fn drop(&mut self)
```

Releases the regional payload before its stable registration, once.


Standalone vector descriptors and region-backed data. The compiler selects
this ordinary owned object for bare Vector<T>; pooled Vector payloads retain
their existing representation. Element moves and retained dependencies are tracked by the compiler.

### `VectorValue`

[vector_value.crb:9](../stdlib/src/collections/vector_value.crb#L9)

```rust
pub struct VectorValue<T>
```

Owns one stable region registration. The movable fixed-size descriptor stays
in the datastack; its payload uses the construction scope's growing region.

Members:

- [`raw`](../stdlib/src/collections/vector_value.crb#L11) (implementation field): Private runtime registration; moving the object transfers its cleanup.

### `VectorValue::new`

[vector_value.crb:14](../stdlib/src/collections/vector_value.crb#L14)

```rust
pub fn new() VectorValue<T>
```

Creates an empty region-backed vector without a user-facing pool.

### `VectorValue::len`

[vector_value.crb:20](../stdlib/src/collections/vector_value.crb#L20)

```rust
pub fn len(&self) usize
```

Returns the number of initialized elements.

### `VectorValue::is_empty`

[vector_value.crb:30](../stdlib/src/collections/vector_value.crb#L30)

```rust
pub fn is_empty(&self) bool
```

Reports whether the vector contains no initialized elements.

### `VectorValue::push`

[vector_value.crb:33](../stdlib/src/collections/vector_value.crb#L33)

```rust
pub fn push(&mut self, value: T)
```

Appends a moved value, enforcing the retained region budget.

### `VectorValue::pop`

[vector_value.crb:47](../stdlib/src/collections/vector_value.crb#L47)

```rust
pub fn pop(&mut self) Option<T>
```

Removes and returns the last element, or None when empty.

### `VectorValue::clear`

[vector_value.crb:57](../stdlib/src/collections/vector_value.crb#L57)

```rust
pub fn clear(&mut self)
```

Destroys remaining elements before reclaiming the region's cursor.

### `VectorValue::drop`

[vector_value.crb:72](../stdlib/src/collections/vector_value.crb#L72)

```rust
pub fn drop(&mut self)
```

Destroys remaining elements, then releases region and registration once.


## `std::compression::gzip`

Native RFC 1952 Gzip with RFC 1951 DEFLATE and caller-owned buffers.

### `Error`

[gzip.crb:5](../stdlib/src/compression/gzip/gzip.crb#L5)

```rust
pub enum Error
```

Reports invalid parameters, bounded storage exhaustion, malformed input or checksum failure.

Members:

- [`InvalidParams`](../stdlib/src/compression/gzip/gzip.crb#L7) (variant): A parameter is outside this algorithm's supported bounds.
- [`WorkspaceTooSmall`](../stdlib/src/compression/gzip/gzip.crb#L9) (variant): The caller-provided scratch buffer cannot hold the required working state.
- [`BufferTooSmall`](../stdlib/src/compression/gzip/gzip.crb#L11) (variant): The caller-provided output buffer cannot hold the result.
- [`InvalidData`](../stdlib/src/compression/gzip/gzip.crb#L13) (variant): The encoded input violates the format or a supported codec constraint.
- [`TruncatedInput`](../stdlib/src/compression/gzip/gzip.crb#L15) (variant): The encoded input ends before a required field or frame is complete.
- [`ChecksumMismatch`](../stdlib/src/compression/gzip/gzip.crb#L17) (variant): The computed checksum differs from the encoded checksum.
- [`InvalidState`](../stdlib/src/compression/gzip/gzip.crb#L19) (variant): The operation is incompatible with the current streaming state.
- [`FrameTooLarge`](../stdlib/src/compression/gzip/gzip.crb#L21) (variant): The frame exceeds the caller's explicit storage budget.

### `Params`

[gzip.crb:25](../stdlib/src/compression/gzip/gzip.crb#L25)

```rust
pub struct Params
```

Controls match-search effort. Level zero stores bytes; levels one through nine compress.

Members:

- [`level`](../stdlib/src/compression/gzip/gzip.crb#L27) (implementation field): Requested compression effort level; constructors validate the supported range.

### `Params::new`

[gzip.crb:30](../stdlib/src/compression/gzip/gzip.crb#L30)

```rust
fn new() Params
```

Uses level six. Levels express this encoder's search effort, not another library's byte output.

### `compress`

[gzip.crb:201](../stdlib/src/compression/gzip/gzip.crb#L201)

```rust
pub fn compress(input: &[u8], output: &mut [u8], params: &Params, workspace: &mut [u64]) Result<usize, Error>
```

Compresses one complete Gzip member. The workspace requires 36864 u64 words for levels 1–9.
Output may contain a partial member on an error; input and workspace are never retained.

### `decompress`

[gzip.crb:428](../stdlib/src/compression/gzip/gzip.crb#L428)

```rust
pub fn decompress(input: &[u8], output: &mut [u8]) Result<usize, Error>
```

Decompresses concatenated members. Errors may leave a partial output prefix.


Bounded, caller-buffered streaming with explicit backpressure and frame budgets.

### `Encoder`

[stream.crb:9](../stdlib/src/compression/gzip/stream.crb#L9)

```rust
pub struct Encoder
```

Encodes bounded chunks as concatenated standard frames; owns no heap storage.
Call process until finished. Destruction discards pending bytes without flushing.

Members:

- [`input`](../stdlib/src/compression/gzip/stream.crb#L11) (implementation field): Caller-owned frame input storage, borrowed for streaming operation.
- [`pending`](../stdlib/src/compression/gzip/stream.crb#L13) (implementation field): Caller-owned encoded-output storage awaiting draining.
- [`workspace`](../stdlib/src/compression/gzip/stream.crb#L15) (implementation field): Caller-owned codec scratch storage; required length is checked before use.
- [`level`](../stdlib/src/compression/gzip/stream.crb#L17) (implementation field): Requested compression effort level; constructors validate the supported range.
- [`used`](../stdlib/src/compression/gzip/stream.crb#L19) (implementation field): Number of bytes currently accumulated in input/pending storage.
- [`count`](../stdlib/src/compression/gzip/stream.crb#L21) (implementation field): Number of valid pending-output bytes.
- [`next`](../stdlib/src/compression/gzip/stream.crb#L23) (implementation field): Offset of the next pending byte to drain.
- [`ending`](../stdlib/src/compression/gzip/stream.crb#L25) (implementation field): Records the caller's end-of-input request.
- [`done`](../stdlib/src/compression/gzip/stream.crb#L27) (implementation field): Records that the current frame has been completely emitted/decoded.
- [`seen`](../stdlib/src/compression/gzip/stream.crb#L29) (implementation field): Tracks whether input/progress has been observed for this frame.
- [`failed`](../stdlib/src/compression/gzip/stream.crb#L31) (implementation field): Sticky failure state; subsequent operations must follow the API's failure/reset contract.
- [`last_read`](../stdlib/src/compression/gzip/stream.crb#L33) (implementation field): Number of input bytes consumed by the latest streaming operation.

### `Encoder::consumed`

[stream.crb:36](../stdlib/src/compression/gzip/stream.crb#L36)

```rust
fn consumed(&self)usize
```

Returns the input accepted by the last successful process call; re-submit the remaining suffix.

### `Encoder::finished`

[stream.crb:38](../stdlib/src/compression/gzip/stream.crb#L38)

```rust
fn finished(&self)bool
```

Reports EOF after all pending output has been drained.

### `Encoder::new`

[stream.crb:42](../stdlib/src/compression/gzip/stream.crb#L42)

```rust
fn new(level:u32, input: &mut [u8], pending: &mut [u8], workspace: &mut [u64]) Encoder
```

Borrows staging, pending-output and match-search buffers; snapshots the scalar options.
Pending needs 2*staging.len()+128 bytes.

### `Encoder::reset`

[stream.crb:49](../stdlib/src/compression/gzip/stream.crb#L49)

```rust
fn reset(&mut self)
```

Reuses the borrowed buffers and parameters for a fresh stream, discarding pending bytes.

### `Encoder::process`

[stream.crb:57](../stdlib/src/compression/gzip/stream.crb#L57)

```rust
fn process(&mut self, input: &[u8], output: &mut [u8], finish: bool) Result<usize, Error>
```

Returns output bytes written. consumed() reports accepted input; re-submit its remaining suffix.
finish marks EOF only once all supplied input is accepted; an empty output can apply backpressure.

### `Decoder`

[stream.crb:97](../stdlib/src/compression/gzip/stream.crb#L97)

```rust
pub struct Decoder
```

Buffers one complete encoded and decoded frame before exposing its validated output.
The two borrowed buffers are hard per-frame budgets, not an unbounded-history window.

Members:

- [`encoded`](../stdlib/src/compression/gzip/stream.crb#L99) (implementation field): Caller-owned storage for a bounded encoded frame.
- [`decoded`](../stdlib/src/compression/gzip/stream.crb#L101) (implementation field): Caller-owned storage for the bounded decoded frame.
- [`used`](../stdlib/src/compression/gzip/stream.crb#L103) (implementation field): Number of bytes currently accumulated in input/pending storage.
- [`count`](../stdlib/src/compression/gzip/stream.crb#L105) (implementation field): Number of valid pending-output bytes.
- [`next`](../stdlib/src/compression/gzip/stream.crb#L107) (implementation field): Offset of the next pending byte to drain.
- [`ending`](../stdlib/src/compression/gzip/stream.crb#L109) (implementation field): Records the caller's end-of-input request.
- [`done`](../stdlib/src/compression/gzip/stream.crb#L111) (implementation field): Records that the current frame has been completely emitted/decoded.
- [`seen`](../stdlib/src/compression/gzip/stream.crb#L113) (implementation field): Tracks whether input/progress has been observed for this frame.
- [`failed`](../stdlib/src/compression/gzip/stream.crb#L115) (implementation field): Sticky failure state; subsequent operations must follow the API's failure/reset contract.
- [`last_read`](../stdlib/src/compression/gzip/stream.crb#L117) (implementation field): Number of input bytes consumed by the latest streaming operation.

### `Decoder::consumed`

[stream.crb:120](../stdlib/src/compression/gzip/stream.crb#L120)

```rust
fn consumed(&self)usize
```

Returns the input accepted by the last successful process call.

### `Decoder::finished`

[stream.crb:122](../stdlib/src/compression/gzip/stream.crb#L122)

```rust
fn finished(&self)bool
```

Reports EOF after all validated output has been drained.

### `Decoder::new`

[stream.crb:125](../stdlib/src/compression/gzip/stream.crb#L125)

```rust
fn new(encoded:&mut [u8], decoded:&mut [u8] ) Decoder
```

Borrows maximum-frame storage; Zstandard additionally needs its 128 KiB literal workspace.

### `Decoder::reset`

[stream.crb:131](../stdlib/src/compression/gzip/stream.crb#L131)

```rust
fn reset(&mut self)
```

Starts a new stream with the same storage and dictionary, discarding pending data.

### `Decoder::process`

[stream.crb:138](../stdlib/src/compression/gzip/stream.crb#L138)

```rust
fn process(&mut self,input:&[u8],output:&mut [u8],finish:bool)Result<usize,Error>
```

Returns validated output bytes written; consumed() reports accepted input.
Frame, checksum or state errors require reset or destruction; a truncated prefix waits for more input.


## `std::compression::zstd`

Native greedy LZ77 Zstandard encoding with raw literals and RLE sequence tables.

### `compress`

[encode.crb:59](../stdlib/src/compression/zstd/encode.crb#L59)

```rust
pub fn compress(input: &[u8], output: &mut [u8], params: &Params, workspace: &mut [u64]) Result<usize, Error>
```

Compresses one Zstandard frame. Workspace requires 36864 u64 words; no heap allocation occurs.
Levels 1–22 control native chain-search effort; zero selects level three. Partial output may remain on errors.

### `compress_with_dictionary`

[encode.crb:65](../stdlib/src/compression/zstd/encode.crb#L65)

```rust
pub fn compress_with_dictionary(input: &[u8], output: &mut [u8], params: &Params, workspace: &mut [u64], dictionary: &[u8]) Result<usize, Error>
```

Compresses with borrowed raw or formatted dictionary history; writes the dictionary ID when present.


Bounded, caller-buffered streaming with explicit backpressure and frame budgets.

### `Encoder`

[stream.crb:9](../stdlib/src/compression/zstd/stream.crb#L9)

```rust
pub struct Encoder
```

Encodes bounded chunks as concatenated standard frames; owns no heap storage.
Call process until finished. Destruction discards pending bytes without flushing.

Members:

- [`input`](../stdlib/src/compression/zstd/stream.crb#L11) (implementation field): Caller-owned frame input storage, borrowed for streaming operation.
- [`pending`](../stdlib/src/compression/zstd/stream.crb#L13) (implementation field): Caller-owned encoded-output storage awaiting draining.
- [`workspace`](../stdlib/src/compression/zstd/stream.crb#L15) (implementation field): Caller-owned codec scratch storage; required length is checked before use.
- [`level`](../stdlib/src/compression/zstd/stream.crb#L17) (implementation field): Requested compression effort level; constructors validate the supported range.
- [`checksum`](../stdlib/src/compression/zstd/stream.crb#L19) (implementation field): Whether the encoded frame includes its content checksum.
- [`dictionary`](../stdlib/src/compression/zstd/stream.crb#L21) (implementation field): Borrowed optional dictionary bytes; they must outlive the codec.
- [`used`](../stdlib/src/compression/zstd/stream.crb#L23) (implementation field): Number of bytes currently accumulated in input/pending storage.
- [`count`](../stdlib/src/compression/zstd/stream.crb#L25) (implementation field): Number of valid pending-output bytes.
- [`next`](../stdlib/src/compression/zstd/stream.crb#L27) (implementation field): Offset of the next pending byte to drain.
- [`ending`](../stdlib/src/compression/zstd/stream.crb#L29) (implementation field): Records the caller's end-of-input request.
- [`done`](../stdlib/src/compression/zstd/stream.crb#L31) (implementation field): Records that the current frame has been completely emitted/decoded.
- [`seen`](../stdlib/src/compression/zstd/stream.crb#L33) (implementation field): Tracks whether input/progress has been observed for this frame.
- [`failed`](../stdlib/src/compression/zstd/stream.crb#L35) (implementation field): Sticky failure state; subsequent operations must follow the API's failure/reset contract.
- [`last_read`](../stdlib/src/compression/zstd/stream.crb#L37) (implementation field): Number of input bytes consumed by the latest streaming operation.

### `Encoder::consumed`

[stream.crb:40](../stdlib/src/compression/zstd/stream.crb#L40)

```rust
fn consumed(&self)usize
```

Returns the input accepted by the last successful process call; re-submit the remaining suffix.

### `Encoder::finished`

[stream.crb:42](../stdlib/src/compression/zstd/stream.crb#L42)

```rust
fn finished(&self)bool
```

Reports EOF after all pending output has been drained.

### `Encoder::new`

[stream.crb:46](../stdlib/src/compression/zstd/stream.crb#L46)

```rust
fn new(level:u32, checksum:bool, input: &mut [u8], pending: &mut [u8], workspace: &mut [u64], dictionary:&[u8]) Encoder
```

Borrows staging, pending-output and match-search buffers; snapshots the scalar options.
Pending needs 2*staging.len()+128 bytes. Zstandard also borrows its dictionary (empty means none).

### `Encoder::reset`

[stream.crb:52](../stdlib/src/compression/zstd/stream.crb#L52)

```rust
fn reset(&mut self)
```

Reuses the borrowed buffers and parameters for a fresh stream, discarding pending bytes.

### `Encoder::process`

[stream.crb:60](../stdlib/src/compression/zstd/stream.crb#L60)

```rust
fn process(&mut self, input: &[u8], output: &mut [u8], finish: bool) Result<usize, Error>
```

Returns output bytes written. consumed() reports accepted input; re-submit its remaining suffix.
finish marks EOF only once all supplied input is accepted; an empty output can apply backpressure.

### `Decoder`

[stream.crb:100](../stdlib/src/compression/zstd/stream.crb#L100)

```rust
pub struct Decoder
```

Buffers one complete encoded and decoded frame before exposing its validated output.
The two borrowed buffers are hard per-frame budgets, not an unbounded-history window.

Members:

- [`encoded`](../stdlib/src/compression/zstd/stream.crb#L102) (implementation field): Caller-owned storage for a bounded encoded frame.
- [`decoded`](../stdlib/src/compression/zstd/stream.crb#L104) (implementation field): Caller-owned storage for the bounded decoded frame.
- [`workspace`](../stdlib/src/compression/zstd/stream.crb#L106) (implementation field): Caller-owned codec scratch storage; required length is checked before use.
- [`dictionary`](../stdlib/src/compression/zstd/stream.crb#L108) (implementation field): Borrowed optional dictionary bytes; they must outlive the codec.
- [`used`](../stdlib/src/compression/zstd/stream.crb#L110) (implementation field): Number of bytes currently accumulated in input/pending storage.
- [`count`](../stdlib/src/compression/zstd/stream.crb#L112) (implementation field): Number of valid pending-output bytes.
- [`next`](../stdlib/src/compression/zstd/stream.crb#L114) (implementation field): Offset of the next pending byte to drain.
- [`ending`](../stdlib/src/compression/zstd/stream.crb#L116) (implementation field): Records the caller's end-of-input request.
- [`done`](../stdlib/src/compression/zstd/stream.crb#L118) (implementation field): Records that the current frame has been completely emitted/decoded.
- [`seen`](../stdlib/src/compression/zstd/stream.crb#L120) (implementation field): Tracks whether input/progress has been observed for this frame.
- [`failed`](../stdlib/src/compression/zstd/stream.crb#L122) (implementation field): Sticky failure state; subsequent operations must follow the API's failure/reset contract.
- [`last_read`](../stdlib/src/compression/zstd/stream.crb#L124) (implementation field): Number of input bytes consumed by the latest streaming operation.

### `Decoder::consumed`

[stream.crb:127](../stdlib/src/compression/zstd/stream.crb#L127)

```rust
fn consumed(&self)usize
```

Returns the input accepted by the last successful process call.

### `Decoder::finished`

[stream.crb:129](../stdlib/src/compression/zstd/stream.crb#L129)

```rust
fn finished(&self)bool
```

Reports EOF after all validated output has been drained.

### `Decoder::new`

[stream.crb:132](../stdlib/src/compression/zstd/stream.crb#L132)

```rust
fn new(encoded:&mut [u8], decoded:&mut [u8] ,workspace:&mut [u8],dictionary:&[u8]) Decoder
```

Borrows maximum-frame storage; Zstandard additionally needs its 128 KiB literal workspace.

### `Decoder::reset`

[stream.crb:137](../stdlib/src/compression/zstd/stream.crb#L137)

```rust
fn reset(&mut self)
```

Starts a new stream with the same storage and dictionary, discarding pending data.

### `Decoder::process`

[stream.crb:144](../stdlib/src/compression/zstd/stream.crb#L144)

```rust
fn process(&mut self,input:&[u8],output:&mut [u8],finish:bool)Result<usize,Error>
```

Returns validated output bytes written; consumed() reports accepted input.
Frame, checksum or state errors require reset or destruction; a truncated prefix waits for more input.


Native RFC 8878 Zstandard frames with caller-owned output and workspace.

### `Error`

[zstd.crb:8](../stdlib/src/compression/zstd/zstd.crb#L8)

```rust
pub enum Error
```

Reports invalid options, bounded storage exhaustion, malformed frames, checksum failure or dictionary requirements.

Members:

- [`InvalidParams`](../stdlib/src/compression/zstd/zstd.crb#L10) (variant): A parameter is outside this algorithm's supported bounds.
- [`WorkspaceTooSmall`](../stdlib/src/compression/zstd/zstd.crb#L12) (variant): The caller-provided scratch buffer cannot hold the required working state.
- [`BufferTooSmall`](../stdlib/src/compression/zstd/zstd.crb#L14) (variant): The caller-provided output buffer cannot hold the result.
- [`InvalidData`](../stdlib/src/compression/zstd/zstd.crb#L16) (variant): The encoded input violates the format or a supported codec constraint.
- [`TruncatedInput`](../stdlib/src/compression/zstd/zstd.crb#L18) (variant): The encoded input ends before a required field or frame is complete.
- [`ChecksumMismatch`](../stdlib/src/compression/zstd/zstd.crb#L20) (variant): The computed checksum differs from the encoded checksum.
- [`DictionaryRequired`](../stdlib/src/compression/zstd/zstd.crb#L22) (variant): The frame requires a dictionary that was not supplied.
- [`InvalidDictionary`](../stdlib/src/compression/zstd/zstd.crb#L24) (variant): The supplied dictionary encoding is invalid or unsupported.
- [`DictionaryMismatch`](../stdlib/src/compression/zstd/zstd.crb#L26) (variant): The supplied dictionary identity does not match the frame.
- [`InvalidState`](../stdlib/src/compression/zstd/zstd.crb#L28) (variant): The operation is incompatible with the current streaming state.
- [`FrameTooLarge`](../stdlib/src/compression/zstd/zstd.crb#L30) (variant): The frame exceeds the caller's explicit storage budget.

### `Params`

[zstd.crb:34](../stdlib/src/compression/zstd/zstd.crb#L34)

```rust
pub struct Params
```

Controls native match-search effort and whether a content checksum is emitted.

Members:

- [`level`](../stdlib/src/compression/zstd/zstd.crb#L36) (implementation field): Requested compression effort level; constructors validate the supported range.
- [`checksum`](../stdlib/src/compression/zstd/zstd.crb#L38) (implementation field): Whether the encoded frame includes its content checksum.

### `Params::new`

[zstd.crb:41](../stdlib/src/compression/zstd/zstd.crb#L41)

```rust
fn new() Params
```

Uses search level three and includes a content checksum.

### `decompress`

[zstd.crb:200](../stdlib/src/compression/zstd/zstd.crb#L200)

```rust
pub fn decompress(input: &[u8], output: &mut [u8], workspace: &mut [u8]) Result<usize, Error>
```

Decompresses concatenated/skippable frames with a caller-owned literal workspace of at least 128 KiB.
Dictionary-dependent frames report DictionaryRequired. Errors may leave a partial output prefix.

### `decompress_with_dictionary`

[zstd.crb:206](../stdlib/src/compression/zstd/zstd.crb#L206)

```rust
pub fn decompress_with_dictionary(input: &[u8], output: &mut [u8], workspace: &mut [u8], dictionary_bytes: &[u8]) Result<usize, Error>
```

Decodes frames with a borrowed raw or formatted dictionary. No dictionary bytes are retained.


## `std::crypto::aes`

Padded AES-256-CBC for interoperable private-key containers.

### `CbcError`

[cbc.crb:5](../stdlib/src/crypto/aes/cbc.crb#L5)

```rust
pub enum CbcError
```

Reports insufficient storage, invalid ciphertext length, or invalid CBC padding.

Members:

- [`BufferTooSmall`](../stdlib/src/crypto/aes/cbc.crb#L7) (variant): The caller-provided output buffer cannot hold the result.
- [`InvalidCiphertext`](../stdlib/src/crypto/aes/cbc.crb#L9) (variant): The ciphertext length or padding is invalid.

### `cbc_encrypt_padded`

[cbc.crb:88](../stdlib/src/crypto/aes/cbc.crb#L88)

```rust
pub fn cbc_encrypt_padded(key: &[u8; 32], iv: &[u8; 16], input: &[u8], output: &mut [u8]) Result<usize, CbcError>
```

Encrypts bytes with AES-256-CBC and PKCS#7 padding and returns the ciphertext length.

### `cbc_decrypt_padded`

[cbc.crb:126](../stdlib/src/crypto/aes/cbc.crb#L126)

```rust
pub fn cbc_decrypt_padded(key: &[u8; 32], iv: &[u8; 16], input: &[u8], output: &mut [u8]) Result<usize, CbcError>
```

Decrypts padded AES-256-CBC. Invalid padding clears the decrypted region of output.
On success, the returned length excludes the padding.


AES-128-GCM and AES-256-GCM with detached tags and caller-provided output.

### `Error`

[gcm.crb:5](../stdlib/src/crypto/aes/gcm.crb#L5)

```rust
pub enum Error
```

Reports a length mismatch, an input limit violation, or a failed authentication tag.

Members:

- [`LengthMismatch`](../stdlib/src/crypto/aes/gcm.crb#L7) (variant): Input/output lengths violate the operation's fixed-size contract.
- [`InputTooLong`](../stdlib/src/crypto/aes/gcm.crb#L9) (variant): Input length exceeds the algorithm's supported counter or encoding limit.
- [`AuthenticationFailed`](../stdlib/src/crypto/aes/gcm.crb#L11) (variant): Authentication failed; the operation must not expose unauthenticated plaintext.

### `AES128GCM`

[gcm.crb:15](../stdlib/src/crypto/aes/gcm.crb#L15)

```rust
pub struct AES128GCM
```

Holds the expanded key and backend choice for AES-128-GCM.

Members:

- [`schedule`](../stdlib/src/crypto/aes/gcm.crb#L17) (implementation field): Expanded AES round-key storage; unused tail bytes accommodate the larger key schedule.
- [`accelerated`](../stdlib/src/crypto/aes/gcm.crb#L19) (implementation field): Whether this instance uses the available hardware compression/encryption path.

### `AES128GCM::new`

[gcm.crb:22](../stdlib/src/crypto/aes/gcm.crb#L22)

```rust
fn new(key: &[u8; 16]) AES128GCM
```

Builds a GCM context from a 16-byte AES key.

### `AES128GCM::seal`

[gcm.crb:36](../stdlib/src/crypto/aes/gcm.crb#L36)

```rust
fn seal(&self, nonce: &[u8; 12], aad: &[u8], plaintext: &[u8], ciphertext: &mut [u8]) Result<[u8; 16], Error>
```

Encrypts into a ciphertext buffer the same size as the plaintext and returns the detached tag.
Use a unique 12-byte nonce for every message under the same key.

### `AES128GCM::open`

[gcm.crb:44](../stdlib/src/crypto/aes/gcm.crb#L44)

```rust
fn open(&self, nonce: &[u8; 12], aad: &[u8], ciphertext: &[u8], tag: &[u8; 16], plaintext: &mut [u8]) Result<(), Error>
```

Authenticates the ciphertext and associated data before writing plaintext. Authentication failure leaves the output unchanged.

### `AES256GCM`

[gcm.crb:53](../stdlib/src/crypto/aes/gcm.crb#L53)

```rust
pub struct AES256GCM
```

Holds the expanded key and backend choice for AES-256-GCM.

Members:

- [`schedule`](../stdlib/src/crypto/aes/gcm.crb#L55) (implementation field): Expanded AES round-key storage; unused tail bytes accommodate the larger key schedule.
- [`accelerated`](../stdlib/src/crypto/aes/gcm.crb#L57) (implementation field): Whether this instance uses the available hardware compression/encryption path.

### `AES256GCM::new`

[gcm.crb:60](../stdlib/src/crypto/aes/gcm.crb#L60)

```rust
fn new(key: &[u8; 32]) AES256GCM
```

Builds a GCM context from a 32-byte AES key.

### `AES256GCM::seal`

[gcm.crb:74](../stdlib/src/crypto/aes/gcm.crb#L74)

```rust
fn seal(&self, nonce: &[u8; 12], aad: &[u8], plaintext: &[u8], ciphertext: &mut [u8]) Result<[u8; 16], Error>
```

Encrypts into a ciphertext buffer the same size as the plaintext and returns the detached tag.
Use a unique 12-byte nonce for every message under the same key.

### `AES256GCM::open`

[gcm.crb:82](../stdlib/src/crypto/aes/gcm.crb#L82)

```rust
fn open(&self, nonce: &[u8; 12], aad: &[u8], ciphertext: &[u8], tag: &[u8; 16], plaintext: &mut [u8]) Result<(), Error>
```

Authenticates the ciphertext and associated data before writing plaintext. Authentication failure leaves the output unchanged.


## `std::crypto::argon2id`

Argon2id version 1.3 with caller-provided memory blocks and output storage.

### `Params`

[argon2id.crb:5](../stdlib/src/crypto/argon2id/argon2id.crb#L5)

```rust
pub struct Params
```

Sets the number of passes and lanes. The workspace supplied to `derive` sets the memory cost.

Members:

- [`passes`](../stdlib/src/crypto/argon2id/argon2id.crb#L7) (implementation field): Argon2 time-cost iteration count.
- [`lanes`](../stdlib/src/crypto/argon2id/argon2id.crb#L9) (implementation field): Configured Argon2 parallel lane count.

### `Error`

[argon2id.crb:13](../stdlib/src/crypto/argon2id/argon2id.crb#L13)

```rust
pub enum Error
```

Reports invalid parameters, insufficient workspace, or incompatible input or output lengths.

Members:

- [`InvalidParams`](../stdlib/src/crypto/argon2id/argon2id.crb#L15) (variant): A parameter is outside this algorithm's supported bounds.
- [`InvalidMemory`](../stdlib/src/crypto/argon2id/argon2id.crb#L17) (variant): The supplied Argon2 memory blocks do not meet the configured parameters.
- [`InvalidOutput`](../stdlib/src/crypto/argon2id/argon2id.crb#L19) (variant): The requested Argon2 output length is invalid.
- [`InputTooLong`](../stdlib/src/crypto/argon2id/argon2id.crb#L21) (variant): Input length exceeds the algorithm's supported counter or encoding limit.

### `derive`

[argon2id.crb:361](../stdlib/src/crypto/argon2id/argon2id.crb#L361)

```rust
pub fn derive(password: &[u8], salt: &[u8], params: Params, work: &mut [[u64; 128]], output: &mut [u8]) Result<(), Error>
```

Derives the requested Argon2id output using the supplied workspace and parameters.


## `std::crypto::md5`

MD5 checksums for compatibility with formats that require RFC 1321.

### `Md5`

[md5.crb:11](../stdlib/src/crypto/md5/md5.crb#L11)

```rust
pub struct Md5
```

Streaming state for a legacy 16-byte MD5 checksum.

Members:

- [`state`](../stdlib/src/crypto/md5/md5.crb#L13) (implementation field): Internal chaining or sponge state retained between updates.
- [`block`](../stdlib/src/crypto/md5/md5.crb#L15) (implementation field): Pending input block; update compresses full blocks before reusing this storage.
- [`bytes`](../stdlib/src/crypto/md5/md5.crb#L17) (implementation field): Total input bytes incorporated by this hash instance.

### `Md5::new`

[md5.crb:20](../stdlib/src/crypto/md5/md5.crb#L20)

```rust
fn new() Md5
```

Creates a hasher with the standard MD5 initial state.

### `Md5::update`

[md5.crb:29](../stdlib/src/crypto/md5/md5.crb#L29)

```rust
fn update(&mut self, input: &[u8])
```

Absorbs input bytes and compresses full blocks as they become available.

### `Md5::finish`

[md5.crb:49](../stdlib/src/crypto/md5/md5.crb#L49)

```rust
fn finish(mut self: Md5) [u8; 16]
```

Consumes the state, adds MD5 padding and returns the checksum.

### `digest`

[md5.crb:163](../stdlib/src/crypto/md5/md5.crb#L163)

```rust
pub fn digest(input: &[u8]) [u8; 16]
```

Computes a 16-byte MD5 checksum for interoperability.


## `std::crypto::p256`

DER and PEM serialization for P-256 signing keys and public keys.

### `spki_point_offset`

[key_der.crb:21](../stdlib/src/crypto/p256/key_der.crb#L21)

```rust
pub fn spki_point_offset(input: &[u8], start: u64, end: u64) u64
```

Returns the SEC1 point offset inside P-256 SubjectPublicKeyInfo, or zero on invalid framing.


P-256 key generation, ephemeral key agreement and deterministic ECDSA.

### `Error`

[p256.crb:9](../stdlib/src/crypto/p256/p256.crb#L9)

```rust
pub enum Error
```

Reports invalid keys or signatures, input limits, output capacity or system entropy errors.

Members:

- [`BufferTooSmall`](../stdlib/src/crypto/p256/p256.crb#L11) (variant): The caller-provided output buffer cannot hold the result.
- [`RandomFailed`](../stdlib/src/crypto/p256/p256.crb#L13) (variant): The system random source could not provide the required bytes.
- [`InvalidPrivateKey`](../stdlib/src/crypto/p256/p256.crb#L15) (variant): The encoded/private scalar material is invalid for this key format.
- [`InvalidPublicKey`](../stdlib/src/crypto/p256/p256.crb#L17) (variant): The public point/key encoding is invalid or outside the supported curve.
- [`InvalidSignature`](../stdlib/src/crypto/p256/p256.crb#L19) (variant): The signature encoding or scalar values are invalid.
- [`InputTooLong`](../stdlib/src/crypto/p256/p256.crb#L21) (variant): Input length exceeds the algorithm's supported counter or encoding limit.

### `EphemeralKey`

[p256.crb:25](../stdlib/src/crypto/p256/p256.crb#L25)

```rust
pub struct EphemeralKey
```

Holds a private P-256 scalar for one consuming ECDHE agreement.

Members:

- [`secret`](../stdlib/src/crypto/p256/p256.crb#L27) (implementation field): Private scalar limbs; never expose these through a public borrowed view.

### `EphemeralKey::generate`

[p256.crb:30](../stdlib/src/crypto/p256/p256.crb#L30)

```rust
fn generate() Result<EphemeralKey, Error>
```

Creates a key using a private scalar sampled from system entropy.

### `EphemeralKey::public_key`

[p256.crb:40](../stdlib/src/crypto/p256/p256.crb#L40)

```rust
fn public_key(&self) PublicKey
```

Derives the public point corresponding to this private scalar.

### `EphemeralKey::agree`

[p256.crb:46](../stdlib/src/crypto/p256/p256.crb#L46)

```rust
fn agree(self: EphemeralKey, peer: &PublicKey, output: &mut [u8; 32]) Result<(), Error>
```

Consumes the ephemeral key and writes the 32-byte ECDHE shared secret.

### `SigningKey`

[p256.crb:66](../stdlib/src/crypto/p256/p256.crb#L66)

```rust
pub struct SigningKey
```

Holds a P-256 private scalar used to derive a public key and sign messages.

Members:

- [`secret`](../stdlib/src/crypto/p256/p256.crb#L68) (implementation field): Private scalar limbs; never expose these through a public borrowed view.

### `SigningKey::generate`

[p256.crb:71](../stdlib/src/crypto/p256/p256.crb#L71)

```rust
fn generate() Result<SigningKey, Error>
```

Creates a key using a private scalar sampled from system entropy.

### `SigningKey::from_bytes`

[p256.crb:81](../stdlib/src/crypto/p256/p256.crb#L81)

```rust
fn from_bytes(input: &[u8; 32]) Result<SigningKey, Error>
```

Imports a 32-byte big-endian private scalar after checking its range.

### `SigningKey::public_key`

[p256.crb:101](../stdlib/src/crypto/p256/p256.crb#L101)

```rust
fn public_key(&self) PublicKey
```

Derives the public point corresponding to this private scalar.

### `SigningKey::sign_sha256`

[p256.crb:107](../stdlib/src/crypto/p256/p256.crb#L107)

```rust
fn sign_sha256(&self, message: &[u8], output: &mut [u8; 72]) Result<usize, Error>
```

Signs a message with deterministic ECDSA and writes the DER signature.

### `SigningKey::from_der`

[p256.crb:126](../stdlib/src/crypto/p256/p256.crb#L126)

```rust
fn from_der(input: &[u8]) Result<SigningKey, Error>
```

Imports a P-256 signing key from unencrypted PKCS#8 or SEC1 DER.

### `SigningKey::from_pem`

[p256.crb:137](../stdlib/src/crypto/p256/p256.crb#L137)

```rust
fn from_pem(input: &[u8], scratch: &mut [u8]) Result<SigningKey, Error>
```

Imports one PRIVATE KEY or EC PRIVATE KEY block. The scratch buffer retains private DER.

### `SigningKey::to_der`

[p256.crb:165](../stdlib/src/crypto/p256/p256.crb#L165)

```rust
fn to_der(&self, output: &mut [u8]) Result<usize, Error>
```

Writes an unencrypted PKCS#8 PrivateKeyInfo and returns its DER length.

### `SigningKey::to_sec1_der`

[p256.crb:178](../stdlib/src/crypto/p256/p256.crb#L178)

```rust
fn to_sec1_der(&self, output: &mut [u8]) Result<usize, Error>
```

Writes an unencrypted SEC1 ECPrivateKey and returns its DER length.

### `SigningKey::to_pem`

[p256.crb:185](../stdlib/src/crypto/p256/p256.crb#L185)

```rust
fn to_pem(&self, output: &mut [u8]) Result<usize, Error>
```

Writes a PRIVATE KEY PEM block containing an unencrypted PKCS#8 key.

### `SigningKey::to_sec1_pem`

[p256.crb:196](../stdlib/src/crypto/p256/p256.crb#L196)

```rust
fn to_sec1_pem(&self, output: &mut [u8]) Result<usize, Error>
```

Writes an EC PRIVATE KEY PEM block containing an unencrypted SEC1 key.

### `PublicKey`

[p256.crb:208](../stdlib/src/crypto/p256/p256.crb#L208)

```rust
pub struct PublicKey
```

Holds a validated P-256 curve point.

Members:

- [`point`](../stdlib/src/crypto/p256/p256.crb#L210) (implementation field): Encoded internal elliptic-curve point representation.

### `PublicKey::from_sec1_uncompressed`

[p256.crb:213](../stdlib/src/crypto/p256/p256.crb#L213)

```rust
fn from_sec1_uncompressed(input: &[u8]) Result<PublicKey, Error>
```

Parses a 65-byte SEC1 point and checks its coordinates and curve equation.

### `PublicKey::to_sec1_uncompressed`

[p256.crb:234](../stdlib/src/crypto/p256/p256.crb#L234)

```rust
fn to_sec1_uncompressed(&self) [u8; 65]
```

Serializes the public point in uncompressed SEC1 form.

### `PublicKey::from_der`

[p256.crb:242](../stdlib/src/crypto/p256/p256.crb#L242)

```rust
fn from_der(input: &[u8]) Result<PublicKey, Error>
```

Imports a P-256 SubjectPublicKeyInfo with an uncompressed point.

### `PublicKey::from_pem`

[p256.crb:252](../stdlib/src/crypto/p256/p256.crb#L252)

```rust
fn from_pem(input: &[u8], scratch: &mut [u8]) Result<PublicKey, Error>
```

Decodes one PUBLIC KEY block into scratch and imports its P-256 public point.

### `PublicKey::to_der`

[p256.crb:269](../stdlib/src/crypto/p256/p256.crb#L269)

```rust
fn to_der(&self, output: &mut [u8]) Result<usize, Error>
```

Writes a DER SubjectPublicKeyInfo with an uncompressed P-256 point.

### `PublicKey::to_pem`

[p256.crb:284](../stdlib/src/crypto/p256/p256.crb#L284)

```rust
fn to_pem(&self, output: &mut [u8]) Result<usize, Error>
```

Writes a PUBLIC KEY PEM block with a P-256 SubjectPublicKeyInfo.

### `verify_sha256`

[p256.crb:362](../stdlib/src/crypto/p256/p256.crb#L362)

```rust
pub fn verify_sha256(key: &PublicKey, message: &[u8], signature: &[u8]) Result<bool, Error>
```

Verifies a DER-encoded P-256 ECDSA signature over a SHA-256 message digest.


## `std::crypto::pbkdf2`

PBKDF2 using HMAC-SHA-256 with caller-owned output.

### `Error`

[pbkdf2.crb:7](../stdlib/src/crypto/pbkdf2/pbkdf2.crb#L7)

```rust
pub enum Error
```

Reports zero iterations, a length outside the PBKDF2 output range, or an oversized input.

Members:

- [`InvalidIterations`](../stdlib/src/crypto/pbkdf2/pbkdf2.crb#L9) (variant): The derivation iteration count is invalid.
- [`InvalidOutputLength`](../stdlib/src/crypto/pbkdf2/pbkdf2.crb#L11) (variant): The derivation output length is invalid.
- [`InputTooLong`](../stdlib/src/crypto/pbkdf2/pbkdf2.crb#L13) (variant): Input length exceeds the algorithm's supported counter or encoding limit.

### `derive_sha256`

[pbkdf2.crb:18](../stdlib/src/crypto/pbkdf2/pbkdf2.crb#L18)

```rust
pub fn derive_sha256(password: &[u8], salt: &[u8], iterations: u32, output: &mut [u8]) Result<(), Error>
```

Derives output.len() bytes with PBKDF2-HMAC-SHA-256. The caller sets the salt and iteration count.
Parameter errors leave the output unchanged.


## `std::crypto::pkcs8`

Password-protected PKCS#8 with PBES2, PBKDF2-HMAC-SHA-256 and AES-256-CBC.

### `Error`

[pkcs8.crb:12](../stdlib/src/crypto/pkcs8/pkcs8.crb#L12)

```rust
pub enum Error
```

Reports a malformed or unsupported container, bad password, work limit, storage, or entropy error.

Members:

- [`InvalidPrivateKey`](../stdlib/src/crypto/pkcs8/pkcs8.crb#L14) (variant): The encoded/private scalar material is invalid for this key format.
- [`InvalidEnvelope`](../stdlib/src/crypto/pkcs8/pkcs8.crb#L16) (variant): The PEM/DER container is malformed or uses an unsupported envelope.
- [`InvalidPasswordOrData`](../stdlib/src/crypto/pkcs8/pkcs8.crb#L18) (variant): Password-based authentication/decryption failed or the decrypted encoding is invalid.
- [`InvalidIterations`](../stdlib/src/crypto/pkcs8/pkcs8.crb#L20) (variant): The derivation iteration count is invalid.
- [`IterationLimit`](../stdlib/src/crypto/pkcs8/pkcs8.crb#L22) (variant): The encoded PBKDF2 work factor exceeds the caller's allowed limit.
- [`BufferTooSmall`](../stdlib/src/crypto/pkcs8/pkcs8.crb#L24) (variant): The caller-provided output buffer cannot hold the result.
- [`RandomFailed`](../stdlib/src/crypto/pkcs8/pkcs8.crb#L26) (variant): The system random source could not provide the required bytes.
- [`InvalidPasswordLength`](../stdlib/src/crypto/pkcs8/pkcs8.crb#L28) (variant): The password length is outside the accepted bounds.

### `decrypt_der`

[pkcs8.crb:173](../stdlib/src/crypto/pkcs8/pkcs8.crb#L173)

```rust
pub fn decrypt_der(input: &[u8], password: &[u8], max_iterations: u32, output: &mut [u8]) Result<usize, Error>
```

Decrypts an EncryptedPrivateKeyInfo DER block to version-zero PrivateKeyInfo DER.
Output must fit the ciphertext length. Invalid password or plaintext clears the written prefix.
The caller sets the maximum accepted PBKDF2 iteration count.

### `encrypt_der`

[pkcs8.crb:245](../stdlib/src/crypto/pkcs8/pkcs8.crb#L245)

```rust
pub fn encrypt_der(input: &[u8], password: &[u8], iterations: u32, output: &mut [u8]) Result<usize, Error>
```

Protects version-zero PrivateKeyInfo DER using a fresh random salt and IV.
The caller selects a nonzero iteration count and supplies the output buffer.

### `encrypt_pem`

[pkcs8.crb:286](../stdlib/src/crypto/pkcs8/pkcs8.crb#L286)

```rust
pub fn encrypt_pem(input: &[u8], password: &[u8], iterations: u32, scratch: &mut [u8], output: &mut [u8]) Result<usize, Error>
```

Encrypts a PrivateKeyInfo into ENCRYPTED PRIVATE KEY PEM using DER scratch.

### `decrypt_pem`

[pkcs8.crb:299](../stdlib/src/crypto/pkcs8/pkcs8.crb#L299)

```rust
pub fn decrypt_pem(input: &[u8], password: &[u8], max_iterations: u32, scratch: &mut [u8], output: &mut [u8]) Result<usize, Error>
```

Decodes ENCRYPTED PRIVATE KEY PEM into DER scratch, then decrypts into output.


## `std::crypto::random`

System entropy with platform dispatch and retry for interrupted reads.

### `RandomError`

[random.crb:22](../stdlib/src/crypto/random/random.crb#L22)

```rust
pub enum RandomError
```

Reports an OS entropy error or an invalid byte count from the backend.

Members:

- [`Os`](../stdlib/src/crypto/random/random.crb#L24) (variant): Preserves the native operating-system error code in code.
- [`Os.code`](../stdlib/src/crypto/random/random.crb#L26) (implementation field): Native operating-system status code preserved by this error.
- [`InvalidCount`](../stdlib/src/crypto/random/random.crb#L29) (variant): The OS returned an invalid byte count.

### `fill`

[random.crb:35](../stdlib/src/crypto/random/random.crb#L35)

```rust
pub fn fill(output: &mut [u8]) Result<(), RandomError>
```

Fills the caller's buffer with system random bytes. A failure can leave a partially filled buffer.


## `std::crypto::rsa`

RSA key container conversion with caller-owned PKCS#1 DER and output buffers.

### `Error`

[rsa.crb:9](../stdlib/src/crypto/rsa/rsa.crb#L9)

```rust
pub enum Error
```

Reports invalid RSA key syntax or insufficient output or PEM scratch storage.

Members:

- [`InvalidKey`](../stdlib/src/crypto/rsa/rsa.crb#L11) (variant): The key container or required integer components are invalid.
- [`BufferTooSmall`](../stdlib/src/crypto/rsa/rsa.crb#L13) (variant): The caller-provided output buffer cannot hold the result.

### `public_from_der`

[rsa.crb:88](../stdlib/src/crypto/rsa/rsa.crb#L88)

```rust
pub fn public_from_der(input: &[u8], output: &mut [u8]) Result<usize, Error>
```

Imports a PKCS#1 or SPKI RSA public key and writes canonical PKCS#1 DER.

### `private_from_der`

[rsa.crb:93](../stdlib/src/crypto/rsa/rsa.crb#L93)

```rust
pub fn private_from_der(input: &[u8], output: &mut [u8]) Result<usize, Error>
```

Imports a PKCS#1 or unencrypted PKCS#8 RSA private key and writes canonical PKCS#1 DER.

### `public_to_der`

[rsa.crb:129](../stdlib/src/crypto/rsa/rsa.crb#L129)

```rust
pub fn public_to_der(pkcs1: &[u8], output: &mut [u8]) Result<usize, Error>
```

Wraps a PKCS#1 RSA public key in DER SubjectPublicKeyInfo.

### `private_to_der`

[rsa.crb:134](../stdlib/src/crypto/rsa/rsa.crb#L134)

```rust
pub fn private_to_der(pkcs1: &[u8], output: &mut [u8]) Result<usize, Error>
```

Wraps a PKCS#1 RSA private key in unencrypted DER PrivateKeyInfo.

### `public_from_pem`

[rsa.crb:166](../stdlib/src/crypto/rsa/rsa.crb#L166)

```rust
pub fn public_from_pem(input: &[u8], scratch: &mut [u8], output: &mut [u8]) Result<usize, Error>
```

Reads PUBLIC KEY or RSA PUBLIC KEY PEM and writes canonical PKCS#1 DER.

### `private_from_pem`

[rsa.crb:173](../stdlib/src/crypto/rsa/rsa.crb#L173)

```rust
pub fn private_from_pem(input: &[u8], scratch: &mut [u8], output: &mut [u8]) Result<usize, Error>
```

Reads PRIVATE KEY or RSA PRIVATE KEY PEM and writes canonical PKCS#1 DER.

### `public_to_pem`

[rsa.crb:188](../stdlib/src/crypto/rsa/rsa.crb#L188)

```rust
pub fn public_to_pem(pkcs1: &[u8], scratch: &mut [u8], output: &mut [u8]) Result<usize, Error>
```

Writes a PUBLIC KEY PEM block using caller-owned DER scratch.

### `private_to_pem`

[rsa.crb:197](../stdlib/src/crypto/rsa/rsa.crb#L197)

```rust
pub fn private_to_pem(pkcs1: &[u8], scratch: &mut [u8], output: &mut [u8]) Result<usize, Error>
```

Writes an unencrypted PRIVATE KEY PEM block using caller-owned DER scratch.

### `public_to_pkcs1_pem`

[rsa.crb:206](../stdlib/src/crypto/rsa/rsa.crb#L206)

```rust
pub fn public_to_pkcs1_pem(pkcs1: &[u8], output: &mut [u8]) Result<usize, Error>
```

Writes an RSA PUBLIC KEY PEM block containing the supplied PKCS#1 key.

### `private_to_pkcs1_pem`

[rsa.crb:214](../stdlib/src/crypto/rsa/rsa.crb#L214)

```rust
pub fn private_to_pkcs1_pem(pkcs1: &[u8], output: &mut [u8]) Result<usize, Error>
```

Writes an unencrypted RSA PRIVATE KEY PEM block containing the supplied PKCS#1 key.


## `std::crypto::sha256`

HKDF extract and expand using HMAC-SHA-256.

### `KdfError`

[hkdf.crb:5](../stdlib/src/crypto/sha256/hkdf.crb#L5)

```rust
pub enum KdfError
```

Reports an oversized HKDF result, a short pseudorandom key, or an input length limit.

Members:

- [`OutputTooLong`](../stdlib/src/crypto/sha256/hkdf.crb#L7) (variant): Requested output exceeds the derivation's algorithmic limit.
- [`InvalidPrkLength`](../stdlib/src/crypto/sha256/hkdf.crb#L9) (variant): The pseudorandom key length does not meet this HKDF API's requirement.
- [`InputTooLong`](../stdlib/src/crypto/sha256/hkdf.crb#L11) (variant): Input length exceeds the algorithm's supported counter or encoding limit.

### `hkdf_extract`

[hkdf.crb:15](../stdlib/src/crypto/sha256/hkdf.crb#L15)

```rust
pub fn hkdf_extract(salt: &[u8], input_key_material: &[u8]) Result<[u8; 32], HashError>
```

Derives a pseudorandom key from salt and input key material using HMAC.

### `hkdf_expand`

[hkdf.crb:23](../stdlib/src/crypto/sha256/hkdf.crb#L23)

```rust
pub fn hkdf_expand(prk: &[u8], info: &[u8], output: &mut [u8]) Result<(), KdfError>
```

Fills the output with derived key material using the pseudorandom key and context.
The pseudorandom key needs at least 32 bytes and the output can hold up to 8160 bytes.


HMAC authentication using SHA-256.

### `hmac_parts`

[hmac.crb:7](../stdlib/src/crypto/sha256/hmac.crb#L7)

```rust
pub fn hmac_parts(key: &[u8], prefix: &[u8], message: &[u8], suffix: &[u8]) Result<[u8; 32], HashError>
```

Computes HMAC over the concatenation of its input fragments.

### `hmac`

[hmac.crb:70](../stdlib/src/crypto/sha256/hmac.crb#L70)

```rust
pub fn hmac(key: &[u8], message: &[u8]) Result<[u8; 32], HashError>
```

Computes the HMAC authentication tag of a message with the supplied key.


Streaming and one-shot SHA-256 hashing.

### `HashError`

[sha256.crb:8](../stdlib/src/crypto/sha256/sha256.crb#L8)

```rust
pub enum HashError
```

Reports that the input length exceeds the SHA-256 limit.

Members:

- [`InputTooLong`](../stdlib/src/crypto/sha256/sha256.crb#L10) (variant): Input length exceeds the algorithm's supported counter or encoding limit.

### `Sha256`

[sha256.crb:14](../stdlib/src/crypto/sha256/sha256.crb#L14)

```rust
pub struct Sha256
```

Holds SHA-256 chaining state, byte count and pending block.

Members:

- [`state`](../stdlib/src/crypto/sha256/sha256.crb#L16) (implementation field): Internal chaining or sponge state retained between updates.
- [`block`](../stdlib/src/crypto/sha256/sha256.crb#L18) (implementation field): Pending input block; update compresses full blocks before reusing this storage.
- [`bytes`](../stdlib/src/crypto/sha256/sha256.crb#L20) (implementation field): Total input bytes incorporated by this hash instance.
- [`accelerated`](../stdlib/src/crypto/sha256/sha256.crb#L22) (implementation field): Whether this instance uses the available hardware compression/encryption path.

### `Sha256::portable`

[sha256.crb:25](../stdlib/src/crypto/sha256/sha256.crb#L25)

```rust
fn portable() Sha256
```

Creates a fresh SHA-256 hasher that uses portable compression.

### `Sha256::new`

[sha256.crb:36](../stdlib/src/crypto/sha256/sha256.crb#L36)

```rust
fn new() Sha256
```

Creates a fresh SHA-256 hasher and selects an available compression backend.

### `Sha256::hardware_accelerated`

[sha256.crb:44](../stdlib/src/crypto/sha256/sha256.crb#L44)

```rust
fn hardware_accelerated(&self) bool
```

Reports whether this hasher uses the hardware compression path.

### `Sha256::snapshot`

[sha256.crb:47](../stdlib/src/crypto/sha256/sha256.crb#L47)

```rust
fn snapshot(&self) [u8; 32]
```

Computes the digest of the bytes seen so far while keeping the hasher available.

### `Sha256::update`

[sha256.crb:69](../stdlib/src/crypto/sha256/sha256.crb#L69)

```rust
fn update(&mut self, input: &[u8]) Result<(), HashError>
```

Feeds a byte slice into the hash, compressing full blocks and retaining the remainder.

### `Sha256::finish`

[sha256.crb:92](../stdlib/src/crypto/sha256/sha256.crb#L92)

```rust
fn finish(mut self: Sha256) [u8; 32]
```

Consumes the hasher and returns its 32-byte digest after padding the message.

### `digest`

[sha256.crb:138](../stdlib/src/crypto/sha256/sha256.crb#L138)

```rust
pub fn digest(input: &[u8]) Result<[u8; 32], HashError>
```

Computes a SHA-256 digest in one call.


## `std::crypto::sha3`

The Keccak sponge and streaming SHA3-224, SHA3-256, SHA3-384 and SHA3-512.

### `Sha3_224`

[sha3.crb:24](../stdlib/src/crypto/sha3/sha3.crb#L24)

```rust
pub struct Sha3_224
```

Streaming SHA3-224 sponge with a 28-byte digest.

Members:

- [`state`](../stdlib/src/crypto/sha3/sha3.crb#L26) (implementation field): Internal chaining or sponge state retained between updates.

### `Sha3_224::new`

[sha3.crb:29](../stdlib/src/crypto/sha3/sha3.crb#L29)

```rust
fn new() Sha3_224
```

Creates an empty streaming hasher for this SHA-3 variant.

### `Sha3_224::update`

[sha3.crb:35](../stdlib/src/crypto/sha3/sha3.crb#L35)

```rust
fn update(&mut self, input: &[u8])
```

Absorbs the input into this variant's sponge.

### `Sha3_224::finish`

[sha3.crb:40](../stdlib/src/crypto/sha3/sha3.crb#L40)

```rust
fn finish(mut self: Sha3_224) [u8; 28]
```

Consumes the hasher and returns the fixed-length digest.

### `Sha3_256`

[sha3.crb:47](../stdlib/src/crypto/sha3/sha3.crb#L47)

```rust
pub struct Sha3_256
```

Streaming SHA3-256 sponge with a 32-byte digest.

Members:

- [`state`](../stdlib/src/crypto/sha3/sha3.crb#L49) (implementation field): Internal chaining or sponge state retained between updates.

### `Sha3_256::new`

[sha3.crb:52](../stdlib/src/crypto/sha3/sha3.crb#L52)

```rust
fn new() Sha3_256
```

Creates an empty streaming hasher for this SHA-3 variant.

### `Sha3_256::update`

[sha3.crb:58](../stdlib/src/crypto/sha3/sha3.crb#L58)

```rust
fn update(&mut self, input: &[u8])
```

Absorbs the input into this variant's sponge.

### `Sha3_256::finish`

[sha3.crb:63](../stdlib/src/crypto/sha3/sha3.crb#L63)

```rust
fn finish(mut self: Sha3_256) [u8; 32]
```

Consumes the hasher and returns the fixed-length digest.

### `Sha3_384`

[sha3.crb:70](../stdlib/src/crypto/sha3/sha3.crb#L70)

```rust
pub struct Sha3_384
```

Streaming SHA3-384 sponge with a 48-byte digest.

Members:

- [`state`](../stdlib/src/crypto/sha3/sha3.crb#L72) (implementation field): Internal chaining or sponge state retained between updates.

### `Sha3_384::new`

[sha3.crb:75](../stdlib/src/crypto/sha3/sha3.crb#L75)

```rust
fn new() Sha3_384
```

Creates an empty streaming hasher for this SHA-3 variant.

### `Sha3_384::update`

[sha3.crb:81](../stdlib/src/crypto/sha3/sha3.crb#L81)

```rust
fn update(&mut self, input: &[u8])
```

Absorbs the input into this variant's sponge.

### `Sha3_384::finish`

[sha3.crb:86](../stdlib/src/crypto/sha3/sha3.crb#L86)

```rust
fn finish(mut self: Sha3_384) [u8; 48]
```

Consumes the hasher and returns the fixed-length digest.

### `Sha3_512`

[sha3.crb:93](../stdlib/src/crypto/sha3/sha3.crb#L93)

```rust
pub struct Sha3_512
```

Streaming SHA3-512 sponge with a 64-byte digest.

Members:

- [`state`](../stdlib/src/crypto/sha3/sha3.crb#L95) (implementation field): Internal chaining or sponge state retained between updates.

### `Sha3_512::new`

[sha3.crb:98](../stdlib/src/crypto/sha3/sha3.crb#L98)

```rust
fn new() Sha3_512
```

Creates an empty streaming hasher for this SHA-3 variant.

### `Sha3_512::update`

[sha3.crb:104](../stdlib/src/crypto/sha3/sha3.crb#L104)

```rust
fn update(&mut self, input: &[u8])
```

Absorbs the input into this variant's sponge.

### `Sha3_512::finish`

[sha3.crb:109](../stdlib/src/crypto/sha3/sha3.crb#L109)

```rust
fn finish(mut self: Sha3_512) [u8; 64]
```

Consumes the hasher and returns the fixed-length digest.

### `digest224`

[sha3.crb:185](../stdlib/src/crypto/sha3/sha3.crb#L185)

```rust
pub fn digest224(input: &[u8]) [u8; 28]
```

Computes a 28-byte SHA3-224 digest.

### `digest256`

[sha3.crb:192](../stdlib/src/crypto/sha3/sha3.crb#L192)

```rust
pub fn digest256(input: &[u8]) [u8; 32]
```

Computes a 32-byte SHA3-256 digest.

### `digest384`

[sha3.crb:199](../stdlib/src/crypto/sha3/sha3.crb#L199)

```rust
pub fn digest384(input: &[u8]) [u8; 48]
```

Computes a 48-byte SHA3-384 digest.

### `digest512`

[sha3.crb:206](../stdlib/src/crypto/sha3/sha3.crb#L206)

```rust
pub fn digest512(input: &[u8]) [u8; 64]
```

Computes a 64-byte SHA3-512 digest.


SHAKE128 and SHAKE256 extendable output using the shared Keccak sponge.

### `shake128`

[shake.crb:20](../stdlib/src/crypto/sha3/shake.crb#L20)

```rust
pub fn shake128(input: &[u8], output: &mut [u8])
```

Fills the caller's output with SHAKE128 bytes.

### `shake256`

[shake.crb:25](../stdlib/src/crypto/sha3/shake.crb#L25)

```rust
pub fn shake256(input: &[u8], output: &mut [u8])
```

Fills the caller's output with SHAKE256 bytes.


## `std::crypto::sha384`

HKDF extract and expand using HMAC-SHA-384.

### `KdfError`

[hkdf.crb:7](../stdlib/src/crypto/sha384/hkdf.crb#L7)

```rust
pub enum KdfError
```

Reports an oversized HKDF result, a short pseudorandom key, or an input length limit.

Members:

- [`OutputTooLong`](../stdlib/src/crypto/sha384/hkdf.crb#L9) (variant): Requested output exceeds the derivation's algorithmic limit.
- [`InvalidPrkLength`](../stdlib/src/crypto/sha384/hkdf.crb#L11) (variant): The pseudorandom key length does not meet this HKDF API's requirement.
- [`InputTooLong`](../stdlib/src/crypto/sha384/hkdf.crb#L13) (variant): Input length exceeds the algorithm's supported counter or encoding limit.

### `hkdf_extract`

[hkdf.crb:17](../stdlib/src/crypto/sha384/hkdf.crb#L17)

```rust
pub fn hkdf_extract(salt: &[u8], input_key_material: &[u8]) Result<[u8; 48], HashError>
```

Derives a pseudorandom key from salt and input key material using HMAC.

### `hkdf_expand`

[hkdf.crb:25](../stdlib/src/crypto/sha384/hkdf.crb#L25)

```rust
pub fn hkdf_expand(prk: &[u8], info: &[u8], output: &mut [u8]) Result<(), KdfError>
```

Fills the output with derived key material using the pseudorandom key and context.
The pseudorandom key needs at least 48 bytes and the output can hold up to 12240 bytes.


HMAC authentication using SHA-384.

### `hmac`

[hmac.crb:72](../stdlib/src/crypto/sha384/hmac.crb#L72)

```rust
pub fn hmac(key: &[u8], message: &[u8]) Result<[u8; 48], HashError>
```

Computes the HMAC authentication tag of a message with the supplied key.


## `std::crypto::sha512`

Streaming SHA-384 and SHA-512 with shared buffering and compression.

### `HashError`

[sha512.crb:9](../stdlib/src/crypto/sha512/sha512.crb#L9)

```rust
pub enum HashError
```

Reports that the input exceeds the hash's message length limit.

Members:

- [`InputTooLong`](../stdlib/src/crypto/sha512/sha512.crb#L11) (variant): Input length exceeds the algorithm's supported counter or encoding limit.

### `Sha384`

[sha512.crb:27](../stdlib/src/crypto/sha512/sha512.crb#L27)

```rust
pub struct Sha384
```

Streaming SHA-384 state with its distinct initial values and 48-byte digest.

Members:

- [`state`](../stdlib/src/crypto/sha512/sha512.crb#L29) (implementation field): Internal chaining or sponge state retained between updates.

### `Sha384::new`

[sha512.crb:32](../stdlib/src/crypto/sha512/sha512.crb#L32)

```rust
fn new() Sha384
```

Creates a fresh hasher with this variant's initial chaining values.

### `Sha384::update`

[sha512.crb:44](../stdlib/src/crypto/sha512/sha512.crb#L44)

```rust
fn update(&mut self, input: &[u8]) Result<(), HashError>
```

Adds input bytes and checks the maximum message length.

### `Sha384::finish`

[sha512.crb:49](../stdlib/src/crypto/sha512/sha512.crb#L49)

```rust
fn finish(mut self: Sha384) [u8; 48]
```

Consumes the hasher and returns the digest for this variant.

### `Sha512`

[sha512.crb:56](../stdlib/src/crypto/sha512/sha512.crb#L56)

```rust
pub struct Sha512
```

Streaming SHA-512 state with a 64-byte digest.

Members:

- [`state`](../stdlib/src/crypto/sha512/sha512.crb#L58) (implementation field): Internal chaining or sponge state retained between updates.

### `Sha512::new`

[sha512.crb:61](../stdlib/src/crypto/sha512/sha512.crb#L61)

```rust
fn new() Sha512
```

Creates a fresh hasher with this variant's initial chaining values.

### `Sha512::update`

[sha512.crb:73](../stdlib/src/crypto/sha512/sha512.crb#L73)

```rust
fn update(&mut self, input: &[u8]) Result<(), HashError>
```

Adds input bytes and checks the maximum message length.

### `Sha512::finish`

[sha512.crb:78](../stdlib/src/crypto/sha512/sha512.crb#L78)

```rust
fn finish(mut self: Sha512) [u8; 64]
```

Consumes the hasher and returns the digest for this variant.

### `digest384`

[sha512.crb:184](../stdlib/src/crypto/sha512/sha512.crb#L184)

```rust
pub fn digest384(input: &[u8]) Result<[u8; 48], HashError>
```

Computes a 48-byte SHA-384 digest.

### `digest512`

[sha512.crb:193](../stdlib/src/crypto/sha512/sha512.crb#L193)

```rust
pub fn digest512(input: &[u8]) Result<[u8; 64], HashError>
```

Computes a 64-byte SHA-512 digest.


## `std::crypto::x509`

X.509 certificate parsing, issued-by checks and ordered P-256 server path validation.

### `CertificateError`

[certificate.crb:11](../stdlib/src/crypto/x509/certificate.crb#L11)

```rust
pub enum CertificateError
```

Reports certificate encoding, time, usage, trust, DNS or buffer errors.

Members:

- [`BufferTooSmall`](../stdlib/src/crypto/x509/certificate.crb#L13) (variant): The caller-provided output buffer cannot hold the result.
- [`InvalidCertificate`](../stdlib/src/crypto/x509/certificate.crb#L15) (variant): The certificate encoding is malformed or outside the supported profile.
- [`InvalidTime`](../stdlib/src/crypto/x509/certificate.crb#L17) (variant): The certificate is not valid at the supplied time.
- [`WrongUsage`](../stdlib/src/crypto/x509/certificate.crb#L19) (variant): The certificate constraints do not permit the requested purpose.
- [`UntrustedChain`](../stdlib/src/crypto/x509/certificate.crb#L21) (variant): No acceptable chain to the supplied trust anchor was established.
- [`NameMismatch`](../stdlib/src/crypto/x509/certificate.crb#L23) (variant): The certificate identity does not match the requested server name.

### `Certificate`

[certificate.crb:171](../stdlib/src/crypto/x509/certificate.crb#L171)

```rust
pub struct Certificate
```

Owns parsed certificate metadata, a DER fingerprint and an encoded public point.

Members:

- [`parsed`](../stdlib/src/crypto/x509/certificate.crb#L173) (implementation field): Validated DER offsets and certificate properties used by this certificate wrapper.
- [`fingerprint`](../stdlib/src/crypto/x509/certificate.crb#L175) (implementation field): SHA-256 certificate fingerprint binding the wrapper to its original DER bytes.
- [`encoded_key`](../stdlib/src/crypto/x509/certificate.crb#L177) (implementation field): Uncompressed SEC1 P-256 public-key bytes extracted from the certificate.

### `Certificate::from_der`

[certificate.crb:180](../stdlib/src/crypto/x509/certificate.crb#L180)

```rust
fn from_der(input: &[u8], now: i64) Result<Certificate, CertificateError>
```

Parses one DER certificate and validates its time window at the supplied Unix time.

### `Certificate::from_pem`

[certificate.crb:208](../stdlib/src/crypto/x509/certificate.crb#L208)

```rust
fn from_pem(input: &[u8], scratch: &mut [u8], now: i64) Result<Certificate, CertificateError>
```

Decodes one CERTIFICATE block into scratch and parses its DER at the supplied Unix time.

### `Certificate::der_len`

[certificate.crb:225](../stdlib/src/crypto/x509/certificate.crb#L225)

```rust
fn der_len(&self) u64
```

Returns the exact DER length for slicing the caller's original or decoded bytes.

### `Certificate::to_der`

[certificate.crb:231](../stdlib/src/crypto/x509/certificate.crb#L231)

```rust
fn to_der(&self, input: &[u8], output: &mut [u8]) Result<usize, CertificateError>
```

Verifies the caller's backing DER and writes its original signed bytes to output.

### `Certificate::to_pem`

[certificate.crb:244](../stdlib/src/crypto/x509/certificate.crb#L244)

```rust
fn to_pem(&self, input: &[u8], output: &mut [u8]) Result<usize, CertificateError>
```

Verifies the backing DER and writes it in a CERTIFICATE PEM block.

### `Certificate::public_key`

[certificate.crb:256](../stdlib/src/crypto/x509/certificate.crb#L256)

```rust
fn public_key(&self) Result<PublicKey, CertificateError>
```

Returns a validated P-256 verification key from the certificate's encoded public point.

### `Certificate::matches_dns_name`

[certificate.crb:267](../stdlib/src/crypto/x509/certificate.crb#L267)

```rust
fn matches_dns_name(&self, input: &[u8], name: &[u8]) Result<bool, CertificateError>
```

Checks a reference DNS name against the certificate's DNS SANs using its original DER.

### `Certificate::verify_issued_by`

[certificate.crb:279](../stdlib/src/crypto/x509/certificate.crb#L279)

```rust
fn verify_issued_by(&self, input: &[u8], issuer: &Certificate, issuer_der: &[u8]) Result<bool, CertificateError>
```

Checks the original DER of both certificates, then verifies the issuer name and signature.

### `PublicKey`

[certificate.crb:293](../stdlib/src/crypto/x509/certificate.crb#L293)

```rust
pub struct PublicKey
```

Wraps the P-256 verification key used by the X.509 profile.

Members:

- [`p256`](../stdlib/src/crypto/x509/certificate.crb#L295) (implementation field): Owned parsed P-256 verification key.

### `PublicKey::from_p256_sec1`

[certificate.crb:298](../stdlib/src/crypto/x509/certificate.crb#L298)

```rust
fn from_p256_sec1(encoded: &[u8]) Result<PublicKey, CertificateError>
```

Checks and wraps a P-256 public point encoded in uncompressed SEC1 form.

### `PublicKey::from_der`

[certificate.crb:309](../stdlib/src/crypto/x509/certificate.crb#L309)

```rust
fn from_der(input: &[u8]) Result<PublicKey, CertificateError>
```

Imports a P-256 SubjectPublicKeyInfo for X.509 signature verification.

### `PublicKey::from_pem`

[certificate.crb:320](../stdlib/src/crypto/x509/certificate.crb#L320)

```rust
fn from_pem(input: &[u8], scratch: &mut [u8]) Result<PublicKey, CertificateError>
```

Imports one PEM PUBLIC KEY block using caller-owned scratch.

### `PublicKey::to_der`

[certificate.crb:341](../stdlib/src/crypto/x509/certificate.crb#L341)

```rust
fn to_der(&self, output: &mut [u8]) Result<usize, CertificateError>
```

Writes the public key as DER SubjectPublicKeyInfo and returns the bytes written.

### `PublicKey::to_pem`

[certificate.crb:350](../stdlib/src/crypto/x509/certificate.crb#L350)

```rust
fn to_pem(&self, output: &mut [u8]) Result<usize, CertificateError>
```

Writes the public key as one PUBLIC KEY PEM block and returns the bytes written.

### `PublicKey::verify_ecdsa_sha256`

[certificate.crb:359](../stdlib/src/crypto/x509/certificate.crb#L359)

```rust
fn verify_ecdsa_sha256(&self, message: &[u8], signature: &[u8]) Result<bool, CertificateError>
```

Verifies a DER ECDSA signature over the SHA-256 digest of the supplied message.

### `validate_server_path`

[certificate.crb:441](../stdlib/src/crypto/x509/certificate.crb#L441)

```rust
pub fn validate_server_path(chain: &[u8], ranges: &[u64; 16], count: u64, anchor: &[u8], hostname: &[u8], now: i64) Result<PublicKey, CertificateError>
```

Validates ranged DER entries in a leaf-first chain and returns the verified DNS server key.

### `validate_server_chain`

[certificate.crb:481](../stdlib/src/crypto/x509/certificate.crb#L481)

```rust
pub fn validate_server_chain(chain: &[u8], anchor: &[u8], hostname: &[u8], now: i64) Result<PublicKey, CertificateError>
```

Validates up to eight concatenated DER certificates against the trust anchor and DNS name.


X.509 DNS identity matching and certificate validity time parsing.

### `valid_dns_name`

[identity.crb:12](../stdlib/src/crypto/x509/identity.crb#L12)

```rust
pub fn valid_dns_name(name: &[u8]) bool
```

Checks the syntax and size bounds of a reference DNS name.


## `std::encoding::base64`

Standard Base64 encoding with canonical padding and caller-owned buffers.

### `Error`

[base64.crb:5](../stdlib/src/encoding/base64/base64.crb#L5)

```rust
pub enum Error
```

Reports an undersized output or invalid Base64 length, alphabet, or padding.

Members:

- [`BufferTooSmall`](../stdlib/src/encoding/base64/base64.crb#L7) (variant): The caller-provided output buffer cannot hold the result.
- [`InvalidLength`](../stdlib/src/encoding/base64/base64.crb#L9) (variant): The input length is incompatible with this encoding.
- [`InvalidCharacter`](../stdlib/src/encoding/base64/base64.crb#L11) (variant): An input byte is outside the encoding alphabet.
- [`InvalidPadding`](../stdlib/src/encoding/base64/base64.crb#L13) (variant): The Base64 padding or unused tail bits are invalid.

### `encode`

[base64.crb:37](../stdlib/src/encoding/base64/base64.crb#L37)

```rust
pub fn encode(input: &[u8], output: &mut [u8]) Result<usize, Error>
```

Writes standard padded Base64 and returns the bytes written. A short output is left unchanged.

### `decode`

[base64.crb:119](../stdlib/src/encoding/base64/base64.crb#L119)

```rust
pub fn decode(input: &[u8], output: &mut [u8]) Result<usize, Error>
```

Decodes canonical padded Base64 without whitespace. Errors leave the output unchanged.

### `decode_wrapped`

[base64.crb:125](../stdlib/src/encoding/base64/base64.crb#L125)

```rust
pub fn decode_wrapped(input: &[u8], output: &mut [u8]) Result<usize, Error>
```

Decodes canonical Base64 while allowing ASCII spaces, tabs, CR and LF.


## `std::encoding::binary`

Explicit byte-order conversion of primitive values using caller-owned slices.
Operations use the first width bytes and leave trailing bytes unchanged.
Float encodings preserve IEEE-754 bits, including signed zero and NaN payloads.

### `Error`

[binary.crb:7](../stdlib/src/encoding/binary/binary.crb#L7)

```rust
pub enum Error
```

Reports insufficient bytes or a noncanonical boolean encoding.

Members:

- [`BufferTooSmall`](../stdlib/src/encoding/binary/binary.crb#L9) (variant): The input or output slice contains fewer than the required bytes.
- [`InvalidBoolean`](../stdlib/src/encoding/binary/binary.crb#L11) (variant): A boolean byte is neither zero nor one.

### `read_u8`

[binary.crb:15](../stdlib/src/encoding/binary/binary.crb#L15)

```rust
pub fn read_u8(input: &[u8]) Result<u8, Error>
```

Reads 1 bytes as u8.

### `write_u8`

[binary.crb:22](../stdlib/src/encoding/binary/binary.crb#L22)

```rust
pub fn write_u8(value: u8, output: &mut [u8]) Result<usize, Error>
```

Writes 1 bytes of u8; short-buffer errors leave output unchanged.

### `read_u16_le`

[binary.crb:31](../stdlib/src/encoding/binary/binary.crb#L31)

```rust
pub fn read_u16_le(input: &[u8]) Result<u16, Error>
```

Reads 2 bytes as u16 in le order.

### `write_u16_le`

[binary.crb:47](../stdlib/src/encoding/binary/binary.crb#L47)

```rust
pub fn write_u16_le(value: u16, output: &mut [u8]) Result<usize, Error>
```

Writes 2 bytes of u16; short-buffer errors leave output unchanged.

### `read_u16_be`

[binary.crb:64](../stdlib/src/encoding/binary/binary.crb#L64)

```rust
pub fn read_u16_be(input: &[u8]) Result<u16, Error>
```

Reads 2 bytes as u16 in be order.

### `write_u16_be`

[binary.crb:80](../stdlib/src/encoding/binary/binary.crb#L80)

```rust
pub fn write_u16_be(value: u16, output: &mut [u8]) Result<usize, Error>
```

Writes 2 bytes of u16; short-buffer errors leave output unchanged.

### `read_u32_le`

[binary.crb:97](../stdlib/src/encoding/binary/binary.crb#L97)

```rust
pub fn read_u32_le(input: &[u8]) Result<u32, Error>
```

Reads 4 bytes as u32 in le order.

### `write_u32_le`

[binary.crb:113](../stdlib/src/encoding/binary/binary.crb#L113)

```rust
pub fn write_u32_le(value: u32, output: &mut [u8]) Result<usize, Error>
```

Writes 4 bytes of u32; short-buffer errors leave output unchanged.

### `read_u32_be`

[binary.crb:130](../stdlib/src/encoding/binary/binary.crb#L130)

```rust
pub fn read_u32_be(input: &[u8]) Result<u32, Error>
```

Reads 4 bytes as u32 in be order.

### `write_u32_be`

[binary.crb:146](../stdlib/src/encoding/binary/binary.crb#L146)

```rust
pub fn write_u32_be(value: u32, output: &mut [u8]) Result<usize, Error>
```

Writes 4 bytes of u32; short-buffer errors leave output unchanged.

### `read_u64_le`

[binary.crb:163](../stdlib/src/encoding/binary/binary.crb#L163)

```rust
pub fn read_u64_le(input: &[u8]) Result<u64, Error>
```

Reads 8 bytes as u64 in le order.

### `write_u64_le`

[binary.crb:179](../stdlib/src/encoding/binary/binary.crb#L179)

```rust
pub fn write_u64_le(value: u64, output: &mut [u8]) Result<usize, Error>
```

Writes 8 bytes of u64; short-buffer errors leave output unchanged.

### `read_u64_be`

[binary.crb:196](../stdlib/src/encoding/binary/binary.crb#L196)

```rust
pub fn read_u64_be(input: &[u8]) Result<u64, Error>
```

Reads 8 bytes as u64 in be order.

### `write_u64_be`

[binary.crb:212](../stdlib/src/encoding/binary/binary.crb#L212)

```rust
pub fn write_u64_be(value: u64, output: &mut [u8]) Result<usize, Error>
```

Writes 8 bytes of u64; short-buffer errors leave output unchanged.

### `read_i32_le`

[binary.crb:309](../stdlib/src/encoding/binary/binary.crb#L309)

```rust
pub fn read_i32_le(input: &[u8]) Result<i32, Error>
```

Reads the 4-byte i32 representation in le order.

### `write_i32_le`

[binary.crb:314](../stdlib/src/encoding/binary/binary.crb#L314)

```rust
pub fn write_i32_le(value: i32, output: &mut [u8]) Result<usize, Error>
```

Writes the 4-byte i32 representation in le order.

### `read_i32_be`

[binary.crb:319](../stdlib/src/encoding/binary/binary.crb#L319)

```rust
pub fn read_i32_be(input: &[u8]) Result<i32, Error>
```

Reads the 4-byte i32 representation in be order.

### `write_i32_be`

[binary.crb:324](../stdlib/src/encoding/binary/binary.crb#L324)

```rust
pub fn write_i32_be(value: i32, output: &mut [u8]) Result<usize, Error>
```

Writes the 4-byte i32 representation in be order.

### `read_i64_le`

[binary.crb:409](../stdlib/src/encoding/binary/binary.crb#L409)

```rust
pub fn read_i64_le(input: &[u8]) Result<i64, Error>
```

Reads the 8-byte i64 representation in le order.

### `write_i64_le`

[binary.crb:414](../stdlib/src/encoding/binary/binary.crb#L414)

```rust
pub fn write_i64_le(value: i64, output: &mut [u8]) Result<usize, Error>
```

Writes the 8-byte i64 representation in le order.

### `read_i64_be`

[binary.crb:419](../stdlib/src/encoding/binary/binary.crb#L419)

```rust
pub fn read_i64_be(input: &[u8]) Result<i64, Error>
```

Reads the 8-byte i64 representation in be order.

### `write_i64_be`

[binary.crb:424](../stdlib/src/encoding/binary/binary.crb#L424)

```rust
pub fn write_i64_be(value: i64, output: &mut [u8]) Result<usize, Error>
```

Writes the 8-byte i64 representation in be order.

### `read_f32_le`

[binary.crb:509](../stdlib/src/encoding/binary/binary.crb#L509)

```rust
pub fn read_f32_le(input: &[u8]) Result<f32, Error>
```

Reads the 4-byte f32 representation in le order.

### `write_f32_le`

[binary.crb:514](../stdlib/src/encoding/binary/binary.crb#L514)

```rust
pub fn write_f32_le(value: f32, output: &mut [u8]) Result<usize, Error>
```

Writes the 4-byte f32 representation in le order.

### `read_f32_be`

[binary.crb:519](../stdlib/src/encoding/binary/binary.crb#L519)

```rust
pub fn read_f32_be(input: &[u8]) Result<f32, Error>
```

Reads the 4-byte f32 representation in be order.

### `write_f32_be`

[binary.crb:524](../stdlib/src/encoding/binary/binary.crb#L524)

```rust
pub fn write_f32_be(value: f32, output: &mut [u8]) Result<usize, Error>
```

Writes the 4-byte f32 representation in be order.

### `read_f64_le`

[binary.crb:609](../stdlib/src/encoding/binary/binary.crb#L609)

```rust
pub fn read_f64_le(input: &[u8]) Result<f64, Error>
```

Reads the 8-byte f64 representation in le order.

### `write_f64_le`

[binary.crb:614](../stdlib/src/encoding/binary/binary.crb#L614)

```rust
pub fn write_f64_le(value: f64, output: &mut [u8]) Result<usize, Error>
```

Writes the 8-byte f64 representation in le order.

### `read_f64_be`

[binary.crb:619](../stdlib/src/encoding/binary/binary.crb#L619)

```rust
pub fn read_f64_be(input: &[u8]) Result<f64, Error>
```

Reads the 8-byte f64 representation in be order.

### `write_f64_be`

[binary.crb:624](../stdlib/src/encoding/binary/binary.crb#L624)

```rust
pub fn write_f64_be(value: f64, output: &mut [u8]) Result<usize, Error>
```

Writes the 8-byte f64 representation in be order.

### `read_bool`

[binary.crb:629](../stdlib/src/encoding/binary/binary.crb#L629)

```rust
pub fn read_bool(input: &[u8]) Result<bool, Error>
```

Reads canonical bool encoding; rejects bytes other than zero and one.

### `write_bool`

[binary.crb:636](../stdlib/src/encoding/binary/binary.crb#L636)

```rust
pub fn write_bool(value: bool, output: &mut [u8]) Result<usize, Error>
```

Writes one byte: zero for false, one for true.

Available when `target.pointer_width == "64"`.

### `read_usize_le`

[binary.crb:644](../stdlib/src/encoding/binary/binary.crb#L644)

```rust
pub fn read_usize_le(input: &[u8]) Result<usize, Error>
```

Reads a pointer-width unsigned integer on supported 64-bit targets; prefer fixed widths on disk.

### `write_usize_le`

[binary.crb:649](../stdlib/src/encoding/binary/binary.crb#L649)

```rust
pub fn write_usize_le(value: usize, output: &mut [u8]) Result<usize, Error>
```

Writes a pointer-width unsigned integer on supported 64-bit targets.

### `read_usize_be`

[binary.crb:654](../stdlib/src/encoding/binary/binary.crb#L654)

```rust
pub fn read_usize_be(input: &[u8]) Result<usize, Error>
```

Reads a pointer-width unsigned integer on supported 64-bit targets; prefer fixed widths on disk.

### `write_usize_be`

[binary.crb:659](../stdlib/src/encoding/binary/binary.crb#L659)

```rust
pub fn write_usize_be(value: usize, output: &mut [u8]) Result<usize, Error>
```

Writes a pointer-width unsigned integer on supported 64-bit targets.


Byte-order namespaces with static conversion methods and no hidden allocation.
NativeEndian is selected at compilation through target.endian.

### `LittleEndian`

[orders.crb:6](../stdlib/src/encoding/binary/orders.crb#L6)

```rust
pub struct LittleEndian
```

Converts primitive values using least-significant-byte-first encoding.

### `LittleEndian::read_u8`

[orders.crb:8](../stdlib/src/encoding/binary/orders.crb#L8)

```rust
pub fn read_u8(input: &[u8]) Result<u8, Error>
```

Reads u8 from the start of the caller-provided slice.

### `LittleEndian::write_u8`

[orders.crb:13](../stdlib/src/encoding/binary/orders.crb#L13)

```rust
pub fn write_u8(value: u8, output: &mut [u8]) Result<usize, Error>
```

Writes u8; short-buffer errors leave the output unchanged.

### `LittleEndian::read_u16`

[orders.crb:18](../stdlib/src/encoding/binary/orders.crb#L18)

```rust
pub fn read_u16(input: &[u8]) Result<u16, Error>
```

Reads u16 from the start of the caller-provided slice.

### `LittleEndian::write_u16`

[orders.crb:23](../stdlib/src/encoding/binary/orders.crb#L23)

```rust
pub fn write_u16(value: u16, output: &mut [u8]) Result<usize, Error>
```

Writes u16; short-buffer errors leave the output unchanged.

### `LittleEndian::read_u32`

[orders.crb:28](../stdlib/src/encoding/binary/orders.crb#L28)

```rust
pub fn read_u32(input: &[u8]) Result<u32, Error>
```

Reads u32 from the start of the caller-provided slice.

### `LittleEndian::write_u32`

[orders.crb:33](../stdlib/src/encoding/binary/orders.crb#L33)

```rust
pub fn write_u32(value: u32, output: &mut [u8]) Result<usize, Error>
```

Writes u32; short-buffer errors leave the output unchanged.

### `LittleEndian::read_u64`

[orders.crb:38](../stdlib/src/encoding/binary/orders.crb#L38)

```rust
pub fn read_u64(input: &[u8]) Result<u64, Error>
```

Reads u64 from the start of the caller-provided slice.

### `LittleEndian::write_u64`

[orders.crb:43](../stdlib/src/encoding/binary/orders.crb#L43)

```rust
pub fn write_u64(value: u64, output: &mut [u8]) Result<usize, Error>
```

Writes u64; short-buffer errors leave the output unchanged.

### `LittleEndian::read_i32`

[orders.crb:48](../stdlib/src/encoding/binary/orders.crb#L48)

```rust
pub fn read_i32(input: &[u8]) Result<i32, Error>
```

Reads i32 from the start of the caller-provided slice.

### `LittleEndian::write_i32`

[orders.crb:53](../stdlib/src/encoding/binary/orders.crb#L53)

```rust
pub fn write_i32(value: i32, output: &mut [u8]) Result<usize, Error>
```

Writes i32; short-buffer errors leave the output unchanged.

### `LittleEndian::read_i64`

[orders.crb:58](../stdlib/src/encoding/binary/orders.crb#L58)

```rust
pub fn read_i64(input: &[u8]) Result<i64, Error>
```

Reads i64 from the start of the caller-provided slice.

### `LittleEndian::write_i64`

[orders.crb:63](../stdlib/src/encoding/binary/orders.crb#L63)

```rust
pub fn write_i64(value: i64, output: &mut [u8]) Result<usize, Error>
```

Writes i64; short-buffer errors leave the output unchanged.

### `LittleEndian::read_f32`

[orders.crb:68](../stdlib/src/encoding/binary/orders.crb#L68)

```rust
pub fn read_f32(input: &[u8]) Result<f32, Error>
```

Reads f32 from the start of the caller-provided slice.

### `LittleEndian::write_f32`

[orders.crb:73](../stdlib/src/encoding/binary/orders.crb#L73)

```rust
pub fn write_f32(value: f32, output: &mut [u8]) Result<usize, Error>
```

Writes f32; short-buffer errors leave the output unchanged.

### `LittleEndian::read_f64`

[orders.crb:78](../stdlib/src/encoding/binary/orders.crb#L78)

```rust
pub fn read_f64(input: &[u8]) Result<f64, Error>
```

Reads f64 from the start of the caller-provided slice.

### `LittleEndian::write_f64`

[orders.crb:83](../stdlib/src/encoding/binary/orders.crb#L83)

```rust
pub fn write_f64(value: f64, output: &mut [u8]) Result<usize, Error>
```

Writes f64; short-buffer errors leave the output unchanged.

### `LittleEndian::read_bool`

[orders.crb:88](../stdlib/src/encoding/binary/orders.crb#L88)

```rust
pub fn read_bool(input: &[u8]) Result<bool, Error>
```

Reads bool from the start of the caller-provided slice.

### `LittleEndian::write_bool`

[orders.crb:93](../stdlib/src/encoding/binary/orders.crb#L93)

```rust
pub fn write_bool(value: bool, output: &mut [u8]) Result<usize, Error>
```

Writes bool; short-buffer errors leave the output unchanged.

Available when `target.pointer_width == "64"`.

### `LittleEndian::read_usize`

[orders.crb:99](../stdlib/src/encoding/binary/orders.crb#L99)

```rust
pub fn read_usize(input: &[u8]) Result<usize, Error>
```

Reads usize from the start of the caller-provided slice.

### `LittleEndian::write_usize`

[orders.crb:104](../stdlib/src/encoding/binary/orders.crb#L104)

```rust
pub fn write_usize(value: usize, output: &mut [u8]) Result<usize, Error>
```

Writes usize; short-buffer errors leave the output unchanged.

### `BigEndian`

[orders.crb:112](../stdlib/src/encoding/binary/orders.crb#L112)

```rust
pub struct BigEndian
```

Converts primitive values using most-significant-byte-first encoding.

### `BigEndian::read_u8`

[orders.crb:114](../stdlib/src/encoding/binary/orders.crb#L114)

```rust
pub fn read_u8(input: &[u8]) Result<u8, Error>
```

Reads u8 from the start of the caller-provided slice.

### `BigEndian::write_u8`

[orders.crb:119](../stdlib/src/encoding/binary/orders.crb#L119)

```rust
pub fn write_u8(value: u8, output: &mut [u8]) Result<usize, Error>
```

Writes u8; short-buffer errors leave the output unchanged.

### `BigEndian::read_u16`

[orders.crb:124](../stdlib/src/encoding/binary/orders.crb#L124)

```rust
pub fn read_u16(input: &[u8]) Result<u16, Error>
```

Reads u16 from the start of the caller-provided slice.

### `BigEndian::write_u16`

[orders.crb:129](../stdlib/src/encoding/binary/orders.crb#L129)

```rust
pub fn write_u16(value: u16, output: &mut [u8]) Result<usize, Error>
```

Writes u16; short-buffer errors leave the output unchanged.

### `BigEndian::read_u32`

[orders.crb:134](../stdlib/src/encoding/binary/orders.crb#L134)

```rust
pub fn read_u32(input: &[u8]) Result<u32, Error>
```

Reads u32 from the start of the caller-provided slice.

### `BigEndian::write_u32`

[orders.crb:139](../stdlib/src/encoding/binary/orders.crb#L139)

```rust
pub fn write_u32(value: u32, output: &mut [u8]) Result<usize, Error>
```

Writes u32; short-buffer errors leave the output unchanged.

### `BigEndian::read_u64`

[orders.crb:144](../stdlib/src/encoding/binary/orders.crb#L144)

```rust
pub fn read_u64(input: &[u8]) Result<u64, Error>
```

Reads u64 from the start of the caller-provided slice.

### `BigEndian::write_u64`

[orders.crb:149](../stdlib/src/encoding/binary/orders.crb#L149)

```rust
pub fn write_u64(value: u64, output: &mut [u8]) Result<usize, Error>
```

Writes u64; short-buffer errors leave the output unchanged.

### `BigEndian::read_i32`

[orders.crb:154](../stdlib/src/encoding/binary/orders.crb#L154)

```rust
pub fn read_i32(input: &[u8]) Result<i32, Error>
```

Reads i32 from the start of the caller-provided slice.

### `BigEndian::write_i32`

[orders.crb:159](../stdlib/src/encoding/binary/orders.crb#L159)

```rust
pub fn write_i32(value: i32, output: &mut [u8]) Result<usize, Error>
```

Writes i32; short-buffer errors leave the output unchanged.

### `BigEndian::read_i64`

[orders.crb:164](../stdlib/src/encoding/binary/orders.crb#L164)

```rust
pub fn read_i64(input: &[u8]) Result<i64, Error>
```

Reads i64 from the start of the caller-provided slice.

### `BigEndian::write_i64`

[orders.crb:169](../stdlib/src/encoding/binary/orders.crb#L169)

```rust
pub fn write_i64(value: i64, output: &mut [u8]) Result<usize, Error>
```

Writes i64; short-buffer errors leave the output unchanged.

### `BigEndian::read_f32`

[orders.crb:174](../stdlib/src/encoding/binary/orders.crb#L174)

```rust
pub fn read_f32(input: &[u8]) Result<f32, Error>
```

Reads f32 from the start of the caller-provided slice.

### `BigEndian::write_f32`

[orders.crb:179](../stdlib/src/encoding/binary/orders.crb#L179)

```rust
pub fn write_f32(value: f32, output: &mut [u8]) Result<usize, Error>
```

Writes f32; short-buffer errors leave the output unchanged.

### `BigEndian::read_f64`

[orders.crb:184](../stdlib/src/encoding/binary/orders.crb#L184)

```rust
pub fn read_f64(input: &[u8]) Result<f64, Error>
```

Reads f64 from the start of the caller-provided slice.

### `BigEndian::write_f64`

[orders.crb:189](../stdlib/src/encoding/binary/orders.crb#L189)

```rust
pub fn write_f64(value: f64, output: &mut [u8]) Result<usize, Error>
```

Writes f64; short-buffer errors leave the output unchanged.

### `BigEndian::read_bool`

[orders.crb:194](../stdlib/src/encoding/binary/orders.crb#L194)

```rust
pub fn read_bool(input: &[u8]) Result<bool, Error>
```

Reads bool from the start of the caller-provided slice.

### `BigEndian::write_bool`

[orders.crb:199](../stdlib/src/encoding/binary/orders.crb#L199)

```rust
pub fn write_bool(value: bool, output: &mut [u8]) Result<usize, Error>
```

Writes bool; short-buffer errors leave the output unchanged.

Available when `target.pointer_width == "64"`.

### `BigEndian::read_usize`

[orders.crb:205](../stdlib/src/encoding/binary/orders.crb#L205)

```rust
pub fn read_usize(input: &[u8]) Result<usize, Error>
```

Reads usize from the start of the caller-provided slice.

### `BigEndian::write_usize`

[orders.crb:210](../stdlib/src/encoding/binary/orders.crb#L210)

```rust
pub fn write_usize(value: usize, output: &mut [u8]) Result<usize, Error>
```

Writes usize; short-buffer errors leave the output unchanged.

### `NativeEndian`

[orders.crb:218](../stdlib/src/encoding/binary/orders.crb#L218)

```rust
pub struct NativeEndian
```

Uses the compilation target byte order; prefer explicit order for stored formats.

Available when `target.endian == "little"`.

### `NativeEndian::read_u8`

[orders.crb:221](../stdlib/src/encoding/binary/orders.crb#L221)

```rust
pub fn read_u8(input: &[u8]) Result<u8, Error>
```

Reads u8 from the start of the caller-provided slice.

### `NativeEndian::write_u8`

[orders.crb:226](../stdlib/src/encoding/binary/orders.crb#L226)

```rust
pub fn write_u8(value: u8, output: &mut [u8]) Result<usize, Error>
```

Writes u8; short-buffer errors leave the output unchanged.

### `NativeEndian::read_u16`

[orders.crb:231](../stdlib/src/encoding/binary/orders.crb#L231)

```rust
pub fn read_u16(input: &[u8]) Result<u16, Error>
```

Reads u16 from the start of the caller-provided slice.

### `NativeEndian::write_u16`

[orders.crb:236](../stdlib/src/encoding/binary/orders.crb#L236)

```rust
pub fn write_u16(value: u16, output: &mut [u8]) Result<usize, Error>
```

Writes u16; short-buffer errors leave the output unchanged.

### `NativeEndian::read_u32`

[orders.crb:241](../stdlib/src/encoding/binary/orders.crb#L241)

```rust
pub fn read_u32(input: &[u8]) Result<u32, Error>
```

Reads u32 from the start of the caller-provided slice.

### `NativeEndian::write_u32`

[orders.crb:246](../stdlib/src/encoding/binary/orders.crb#L246)

```rust
pub fn write_u32(value: u32, output: &mut [u8]) Result<usize, Error>
```

Writes u32; short-buffer errors leave the output unchanged.

### `NativeEndian::read_u64`

[orders.crb:251](../stdlib/src/encoding/binary/orders.crb#L251)

```rust
pub fn read_u64(input: &[u8]) Result<u64, Error>
```

Reads u64 from the start of the caller-provided slice.

### `NativeEndian::write_u64`

[orders.crb:256](../stdlib/src/encoding/binary/orders.crb#L256)

```rust
pub fn write_u64(value: u64, output: &mut [u8]) Result<usize, Error>
```

Writes u64; short-buffer errors leave the output unchanged.

### `NativeEndian::read_i32`

[orders.crb:261](../stdlib/src/encoding/binary/orders.crb#L261)

```rust
pub fn read_i32(input: &[u8]) Result<i32, Error>
```

Reads i32 from the start of the caller-provided slice.

### `NativeEndian::write_i32`

[orders.crb:266](../stdlib/src/encoding/binary/orders.crb#L266)

```rust
pub fn write_i32(value: i32, output: &mut [u8]) Result<usize, Error>
```

Writes i32; short-buffer errors leave the output unchanged.

### `NativeEndian::read_i64`

[orders.crb:271](../stdlib/src/encoding/binary/orders.crb#L271)

```rust
pub fn read_i64(input: &[u8]) Result<i64, Error>
```

Reads i64 from the start of the caller-provided slice.

### `NativeEndian::write_i64`

[orders.crb:276](../stdlib/src/encoding/binary/orders.crb#L276)

```rust
pub fn write_i64(value: i64, output: &mut [u8]) Result<usize, Error>
```

Writes i64; short-buffer errors leave the output unchanged.

### `NativeEndian::read_f32`

[orders.crb:281](../stdlib/src/encoding/binary/orders.crb#L281)

```rust
pub fn read_f32(input: &[u8]) Result<f32, Error>
```

Reads f32 from the start of the caller-provided slice.

### `NativeEndian::write_f32`

[orders.crb:286](../stdlib/src/encoding/binary/orders.crb#L286)

```rust
pub fn write_f32(value: f32, output: &mut [u8]) Result<usize, Error>
```

Writes f32; short-buffer errors leave the output unchanged.

### `NativeEndian::read_f64`

[orders.crb:291](../stdlib/src/encoding/binary/orders.crb#L291)

```rust
pub fn read_f64(input: &[u8]) Result<f64, Error>
```

Reads f64 from the start of the caller-provided slice.

### `NativeEndian::write_f64`

[orders.crb:296](../stdlib/src/encoding/binary/orders.crb#L296)

```rust
pub fn write_f64(value: f64, output: &mut [u8]) Result<usize, Error>
```

Writes f64; short-buffer errors leave the output unchanged.

### `NativeEndian::read_bool`

[orders.crb:301](../stdlib/src/encoding/binary/orders.crb#L301)

```rust
pub fn read_bool(input: &[u8]) Result<bool, Error>
```

Reads bool from the start of the caller-provided slice.

### `NativeEndian::write_bool`

[orders.crb:306](../stdlib/src/encoding/binary/orders.crb#L306)

```rust
pub fn write_bool(value: bool, output: &mut [u8]) Result<usize, Error>
```

Writes bool; short-buffer errors leave the output unchanged.

Available when `target.endian == "little"` and `target.pointer_width == "64"`.

### `NativeEndian::read_usize`

[orders.crb:312](../stdlib/src/encoding/binary/orders.crb#L312)

```rust
pub fn read_usize(input: &[u8]) Result<usize, Error>
```

Reads usize from the start of the caller-provided slice.

### `NativeEndian::write_usize`

[orders.crb:317](../stdlib/src/encoding/binary/orders.crb#L317)

```rust
pub fn write_usize(value: usize, output: &mut [u8]) Result<usize, Error>
```

Writes usize; short-buffer errors leave the output unchanged.

Available when `target.endian == "big"`.

### `NativeEndian::read_u8`

[orders.crb:326](../stdlib/src/encoding/binary/orders.crb#L326)

```rust
pub fn read_u8(input: &[u8]) Result<u8, Error>
```

Reads u8 from the start of the caller-provided slice.

### `NativeEndian::write_u8`

[orders.crb:331](../stdlib/src/encoding/binary/orders.crb#L331)

```rust
pub fn write_u8(value: u8, output: &mut [u8]) Result<usize, Error>
```

Writes u8; short-buffer errors leave the output unchanged.

### `NativeEndian::read_u16`

[orders.crb:336](../stdlib/src/encoding/binary/orders.crb#L336)

```rust
pub fn read_u16(input: &[u8]) Result<u16, Error>
```

Reads u16 from the start of the caller-provided slice.

### `NativeEndian::write_u16`

[orders.crb:341](../stdlib/src/encoding/binary/orders.crb#L341)

```rust
pub fn write_u16(value: u16, output: &mut [u8]) Result<usize, Error>
```

Writes u16; short-buffer errors leave the output unchanged.

### `NativeEndian::read_u32`

[orders.crb:346](../stdlib/src/encoding/binary/orders.crb#L346)

```rust
pub fn read_u32(input: &[u8]) Result<u32, Error>
```

Reads u32 from the start of the caller-provided slice.

### `NativeEndian::write_u32`

[orders.crb:351](../stdlib/src/encoding/binary/orders.crb#L351)

```rust
pub fn write_u32(value: u32, output: &mut [u8]) Result<usize, Error>
```

Writes u32; short-buffer errors leave the output unchanged.

### `NativeEndian::read_u64`

[orders.crb:356](../stdlib/src/encoding/binary/orders.crb#L356)

```rust
pub fn read_u64(input: &[u8]) Result<u64, Error>
```

Reads u64 from the start of the caller-provided slice.

### `NativeEndian::write_u64`

[orders.crb:361](../stdlib/src/encoding/binary/orders.crb#L361)

```rust
pub fn write_u64(value: u64, output: &mut [u8]) Result<usize, Error>
```

Writes u64; short-buffer errors leave the output unchanged.

### `NativeEndian::read_i32`

[orders.crb:366](../stdlib/src/encoding/binary/orders.crb#L366)

```rust
pub fn read_i32(input: &[u8]) Result<i32, Error>
```

Reads i32 from the start of the caller-provided slice.

### `NativeEndian::write_i32`

[orders.crb:371](../stdlib/src/encoding/binary/orders.crb#L371)

```rust
pub fn write_i32(value: i32, output: &mut [u8]) Result<usize, Error>
```

Writes i32; short-buffer errors leave the output unchanged.

### `NativeEndian::read_i64`

[orders.crb:376](../stdlib/src/encoding/binary/orders.crb#L376)

```rust
pub fn read_i64(input: &[u8]) Result<i64, Error>
```

Reads i64 from the start of the caller-provided slice.

### `NativeEndian::write_i64`

[orders.crb:381](../stdlib/src/encoding/binary/orders.crb#L381)

```rust
pub fn write_i64(value: i64, output: &mut [u8]) Result<usize, Error>
```

Writes i64; short-buffer errors leave the output unchanged.

### `NativeEndian::read_f32`

[orders.crb:386](../stdlib/src/encoding/binary/orders.crb#L386)

```rust
pub fn read_f32(input: &[u8]) Result<f32, Error>
```

Reads f32 from the start of the caller-provided slice.

### `NativeEndian::write_f32`

[orders.crb:391](../stdlib/src/encoding/binary/orders.crb#L391)

```rust
pub fn write_f32(value: f32, output: &mut [u8]) Result<usize, Error>
```

Writes f32; short-buffer errors leave the output unchanged.

### `NativeEndian::read_f64`

[orders.crb:396](../stdlib/src/encoding/binary/orders.crb#L396)

```rust
pub fn read_f64(input: &[u8]) Result<f64, Error>
```

Reads f64 from the start of the caller-provided slice.

### `NativeEndian::write_f64`

[orders.crb:401](../stdlib/src/encoding/binary/orders.crb#L401)

```rust
pub fn write_f64(value: f64, output: &mut [u8]) Result<usize, Error>
```

Writes f64; short-buffer errors leave the output unchanged.

### `NativeEndian::read_bool`

[orders.crb:406](../stdlib/src/encoding/binary/orders.crb#L406)

```rust
pub fn read_bool(input: &[u8]) Result<bool, Error>
```

Reads bool from the start of the caller-provided slice.

### `NativeEndian::write_bool`

[orders.crb:411](../stdlib/src/encoding/binary/orders.crb#L411)

```rust
pub fn write_bool(value: bool, output: &mut [u8]) Result<usize, Error>
```

Writes bool; short-buffer errors leave the output unchanged.

Available when `target.endian == "big"` and `target.pointer_width == "64"`.

### `NativeEndian::read_usize`

[orders.crb:417](../stdlib/src/encoding/binary/orders.crb#L417)

```rust
pub fn read_usize(input: &[u8]) Result<usize, Error>
```

Reads usize from the start of the caller-provided slice.

### `NativeEndian::write_usize`

[orders.crb:422](../stdlib/src/encoding/binary/orders.crb#L422)

```rust
pub fn write_usize(value: usize, output: &mut [u8]) Result<usize, Error>
```

Writes usize; short-buffer errors leave the output unchanged.


## `std::encoding::der`

Bounds-checked DER framing and validation of common ASN.1 values.

### `Der`

[der.crb:6](../stdlib/src/encoding/der/der.crb#L6)

```rust
pub struct Der
```

Holds the content and end offsets of a DER element. End zero denotes malformed input.

Members:

- [`body`](../stdlib/src/encoding/der/der.crb#L8) (implementation field): Start of the parsed DER value body.
- [`end`](../stdlib/src/encoding/der/der.crb#L10) (implementation field): Exclusive end of the parsed DER value.

### `invalid_der`

[der.crb:14](../stdlib/src/encoding/der/der.crb#L14)

```rust
pub fn invalid_der() Der
```

Returns the sentinel for a malformed or missing DER element.

### `der`

[der.crb:17](../stdlib/src/encoding/der/der.crb#L17)

```rust
pub fn der(input: &[u8], at: u64, limit: u64, tag: u8) Der
```

Parses one element with the expected tag and a canonical definite length within the supplied limit.

### `bytes_equal`

[der.crb:40](../stdlib/src/encoding/der/der.crb#L40)

```rust
pub fn bytes_equal(a: &[u8], b: &[u8]) bool
```

Compares the length and contents of two byte slices.

### `uint_valid`

[der.crb:52](../stdlib/src/encoding/der/der.crb#L52)

```rust
pub fn uint_valid(input: &[u8], start: u64, end: u64) bool
```

Checks that a byte range is a minimally encoded nonnegative DER integer.

### `oid_valid`

[der.crb:59](../stdlib/src/encoding/der/der.crb#L59)

```rust
pub fn oid_valid(input: &[u8], start: u64, end: u64) bool
```

Checks the base-128 component encoding and termination of a DER object identifier.

### `der_header_size`

[der.crb:73](../stdlib/src/encoding/der/der.crb#L73)

```rust
pub fn der_header_size(length: u64) u64
```

Returns the width of a DER tag and definite length, or zero when the length exceeds 32 bits.

### `der_octet`

[der.crb:83](../stdlib/src/encoding/der/der.crb#L83)

```rust
pub fn der_octet(word: u64, shift: u64) u8
```

Returns the octet at the supplied position of a word.

### `write_der_header`

[der.crb:97](../stdlib/src/encoding/der/der.crb#L97)

```rust
pub fn write_der_header(tag: u8, length: u64, output: &mut [u8]) u64
```

Writes a DER header and returns its width, or zero when the header cannot fit.

### `copy_der`

[der.crb:115](../stdlib/src/encoding/der/der.crb#L115)

```rust
pub fn copy_der(input: &[u8], output: &mut [u8]) usize
```

Copies a byte slice into caller-owned storage, returning zero on insufficient capacity.


## `std::encoding::hex`

Hexadecimal encoding and decoding into caller-owned buffers.

### `Error`

[hex.crb:5](../stdlib/src/encoding/hex/hex.crb#L5)

```rust
pub enum Error
```

Reports an undersized output, an odd input length, or a non-hexadecimal digit.

Members:

- [`BufferTooSmall`](../stdlib/src/encoding/hex/hex.crb#L7) (variant): The caller-provided output buffer cannot hold the result.
- [`InvalidLength`](../stdlib/src/encoding/hex/hex.crb#L9) (variant): The input length is incompatible with this encoding.
- [`InvalidCharacter`](../stdlib/src/encoding/hex/hex.crb#L11) (variant): An input byte is outside the encoding alphabet.

### `encode`

[hex.crb:29](../stdlib/src/encoding/hex/hex.crb#L29)

```rust
pub fn encode(input: &[u8], output: &mut [u8]) Result<usize, Error>
```

Writes lowercase hexadecimal and returns the bytes written. Errors leave the output unchanged.

### `decode`

[hex.crb:42](../stdlib/src/encoding/hex/hex.crb#L42)

```rust
pub fn decode(input: &[u8], output: &mut [u8]) Result<usize, Error>
```

Decodes an even number of hexadecimal digits in either case. Errors leave the output unchanged.


## `std::encoding::pem`

Labelled PEM encoding and decoding with caller-owned buffers.

### `Error`

[pem.crb:8](../stdlib/src/encoding/pem/pem.crb#L8)

```rust
pub enum Error
```

Reports a malformed PEM envelope, invalid Base64, or an undersized output buffer.

Members:

- [`InvalidEnvelope`](../stdlib/src/encoding/pem/pem.crb#L10) (variant): The PEM/DER container is malformed or uses an unsupported envelope.
- [`InvalidBase64`](../stdlib/src/encoding/pem/pem.crb#L12) (variant): The PEM body is not valid Base64.
- [`BufferTooSmall`](../stdlib/src/encoding/pem/pem.crb#L14) (variant): The caller-provided output buffer cannot hold the result.

### `decode`

[pem.crb:40](../stdlib/src/encoding/pem/pem.crb#L40)

```rust
pub fn decode(input: &[u8], label: &[u8], output: &mut [u8]) Result<usize, Error>
```

Decodes one nonempty PEM block with the expected label and returns the DER byte count.

### `encode`

[pem.crb:126](../stdlib/src/encoding/pem/pem.crb#L126)

```rust
pub fn encode(input: &[u8], label: &[u8], output: &mut [u8]) Result<usize, Error>
```

Writes one PEM block with 64 Base64 characters per full line and returns the bytes written.
The input must be nonempty. Labels use uppercase ASCII letters and digits with single spaces or hyphens between groups.
Invalid input or insufficient capacity leaves the output unchanged.


## `std::env`

Access to the current process arguments.

### `ArgsError`

[args.crb:5](../stdlib/src/env/args.crb#L5)

```rust
pub enum ArgsError
```

Reports failures encountered while obtaining a process argument.

Members:

- [`InvalidUtf8`](../stdlib/src/env/args.crb#L7) (variant): A process argument is not valid UTF-8.
- [`Unavailable`](../stdlib/src/env/args.crb#L9) (variant): The process argument source is unavailable.

### `args`

[args.crb:13](../stdlib/src/env/args.crb#L13)

```rust
pub fn args() Result<&[&str], ArgsError>
```

Returns the current process argument list supplied by the executable entry point.


## `std::io`

Portable blocking file I/O, open modes, permissions and seek origins.

Available when `target.os == "linux" && target.arch == "x86_64" && target.pointer_width == "64" || target.os == "macos" && target.arch == "aarch64" || target.os == "macos" && target.arch == "x86_64" || target.os == "windows" && target.arch == "aarch64" || target.os == "windows" && target.arch == "x86_64"`.

### `File`

[file.crb:13](../stdlib/src/io/file.crb#L13)

```rust
pub struct File
```

Owns an open file and closes the platform handle when destroyed.

Members:

- [`inner`](../stdlib/src/io/file.crb#L15) (implementation field): Owned platform-specific object used to dispatch this portable wrapper's operations.
- [`mode`](../stdlib/src/io/file.crb#L17) (implementation field): Original access/append flags, retained for positioned-operation validation.

### `File::open`

[file.crb:21](../stdlib/src/io/file.crb#L21)

```rust
fn open(path: &str, mode: i64) Result<File, FileError>
```

Opens a UTF-8 path with independent OR-combined FileMode flags.
CREATE uses default creation permissions; no trailing NUL is required.

### `File::create`

[file.crb:27](../stdlib/src/io/file.crb#L27)

```rust
fn create(path: &str, mode: i64, perm: FilePerm) Result<File, FileError>
```

Opens or creates a UTF-8 path with explicit creation permissions.
CREATE is implied; TRUNCATE and EXCLUSIVE remain explicit flags.

### `File::read`

[file.crb:39](../stdlib/src/io/file.crb#L39)

```rust
fn read(&mut self, buffer: &mut [u8]) Result<usize, FileError>
```

Reads into the caller's slice and returns the bytes copied. An empty buffer returns zero.

### `File::write`

[file.crb:48](../stdlib/src/io/file.crb#L48)

```rust
fn write(&mut self, buffer: &[u8]) Result<usize, FileError>
```

Writes bytes from the caller's slice and returns the number accepted, which may be less than its length.

### `File::read_at`

[file.crb:58](../stdlib/src/io/file.crb#L58)

```rust
fn read_at(&self, buffer: &mut [u8], offset: u64) Result<usize, FileError>
```

Reads into the caller's buffer at offset without moving the cursor; short transfers are allowed.
Rejects unrepresentable ranges and write-only mode. Valid empty ranges return zero.

### `File::write_at`

[file.crb:73](../stdlib/src/io/file.crb#L73)

```rust
fn write_at(&self, buffer: &[u8], offset: u64) Result<usize, FileError>
```

Writes from the caller's buffer at offset without moving the cursor; short transfers are allowed.
Rejects unrepresentable ranges and read-only/append modes. Valid empty ranges return zero.

### `File::seek`

[file.crb:87](../stdlib/src/io/file.crb#L87)

```rust
fn seek(&mut self, from: SeekFrom) Result<u64, FileError>
```

Moves the file cursor relative to the supplied origin and returns its new absolute position.

### `File::sync_all`

[file.crb:105](../stdlib/src/io/file.crb#L105)

```rust
fn sync_all(&mut self) Result<(), FileError>
```

Persists this file's contents/metadata; does not sync a parent directory or create a transaction.

### `File::truncate`

[file.crb:114](../stdlib/src/io/file.crb#L114)

```rust
fn truncate(&mut self, length: u64) Result<(), FileError>
```

Sets the file length, preserving the cursor. Sizes beyond i64::MAX are invalid.

### `File::stats`

[file.crb:124](../stdlib/src/io/file.crb#L124)

```rust
fn stats(&self) Result<FileStats, FileError>
```

Returns a snapshot of file metadata from its open handle.

### `File::rename`

[file.crb:133](../stdlib/src/io/file.crb#L133)

```rust
fn rename(source: &str, destination: &str) Result<(), FileError>
```

Renames a file from the source path to the destination path using platform semantics.

### `File::delete`

[file.crb:148](../stdlib/src/io/file.crb#L148)

```rust
fn delete(path: &str) Result<(), FileError>
```

Removes the file named by the supplied path.

### `FileError`

[file.crb:162](../stdlib/src/io/file.crb#L162)

```rust
pub enum FileError
```

Reports invalid path or options, or an error code from the operating system.

Members:

- [`InvalidPath`](../stdlib/src/io/file.crb#L164) (variant): The supplied path violates the platform path-input contract.
- [`InvalidOptions`](../stdlib/src/io/file.crb#L166) (variant): The requested open-mode combination is invalid.
- [`Os`](../stdlib/src/io/file.crb#L168) (variant): Preserves the native operating-system error code in code.
- [`Os.code`](../stdlib/src/io/file.crb#L170) (implementation field): Native operating-system status code preserved by this error.


Shared file metadata, permissions and modes for sync and async I/O.

### `FileStats`

[options.crb:5](../stdlib/src/io/options.crb#L5)

```rust
pub struct FileStats
```

Holds the metadata returned by the file API, including its size.

Members:

- [`size_bytes`](../stdlib/src/io/options.crb#L7) (implementation field): File length reported by the platform in bytes.

### `FileStats::size`

[options.crb:10](../stdlib/src/io/options.crb#L10)

```rust
fn size(&self) u64
```

Returns the file size in bytes captured by the stats operation.

### `FilePerm`

[options.crb:16](../stdlib/src/io/options.crb#L16)

```rust
pub enum FilePerm
```

Selects platform-default permissions or explicit permission bits for creation.

Members:

- [`DefaultMode`](../stdlib/src/io/options.crb#L18) (variant): Uses the documented platform default permissions for creation.
- [`Perm`](../stdlib/src/io/options.crb#L20) (variant): Requests explicit Unix-style permission bits; unsupported platform behavior is reported by the API.

### `SeekFrom`

[options.crb:24](../stdlib/src/io/options.crb#L24)

```rust
pub enum SeekFrom
```

Specifies a byte offset from the start, current position, or end of the file.

Members:

- [`Start`](../stdlib/src/io/options.crb#L26) (variant): Seeks to the supplied absolute byte offset.
- [`Current`](../stdlib/src/io/options.crb#L28) (variant): Seeks by a signed byte displacement from the current position.
- [`End`](../stdlib/src/io/options.crb#L30) (variant): Seeks by a signed byte displacement from the file end.

### `FileMode`

[options.crb:34](../stdlib/src/io/options.crb#L34)

```rust
pub struct FileMode
```

Provides the access modes and flags accepted by file open and create.

### `FileMode::READ`

[options.crb:37](../stdlib/src/io/options.crb#L37)

```rust
const READ: i64 = 1
```

Enables reading; combine with WRITE for read/write access.

### `FileMode::WRITE`

[options.crb:39](../stdlib/src/io/options.crb#L39)

```rust
const WRITE: i64 = 2
```

Enables writing; combine with READ, CREATE, APPEND or TRUNCATE.

### `FileMode::CREATE`

[options.crb:41](../stdlib/src/io/options.crb#L41)

```rust
const CREATE: i64 = 16
```

Creates the file if it is absent, without replacing existing contents.

### `FileMode::EXCLUSIVE`

[options.crb:43](../stdlib/src/io/options.crb#L43)

```rust
const EXCLUSIVE: i64 = 32
```

Requires CREATE and fails atomically when the path already exists.

### `FileMode::CREATE_NEW`

[options.crb:45](../stdlib/src/io/options.crb#L45)

```rust
const CREATE_NEW: i64 = 48
```

Creates a new file exclusively; equivalent to CREATE | EXCLUSIVE.

### `FileMode::SYNC`

[options.crb:47](../stdlib/src/io/options.crb#L47)

```rust
const SYNC: i64 = 64
```

Requests synchronous completion of file writes at the OS boundary.

### `FileMode::READ_ONLY`

[options.crb:49](../stdlib/src/io/options.crb#L49)

```rust
const READ_ONLY: i64 = 1
```

Compatibility spelling for READ.

### `FileMode::WRITE_ONLY`

[options.crb:51](../stdlib/src/io/options.crb#L51)

```rust
const WRITE_ONLY: i64 = 2
```

Opens the file for writing only.

### `FileMode::READ_WRITE`

[options.crb:53](../stdlib/src/io/options.crb#L53)

```rust
const READ_WRITE: i64 = 3
```

Allows both reading and writing.

### `FileMode::APPEND`

[options.crb:55](../stdlib/src/io/options.crb#L55)

```rust
const APPEND: i64 = 4
```

Requests that writes append to the file.

### `FileMode::TRUNCATE`

[options.crb:57](../stdlib/src/io/options.crb#L57)

```rust
const TRUNCATE: i64 = 8
```

Requests that an existing file be truncated on open.

### `FileMode::read_only`

[options.crb:60](../stdlib/src/io/options.crb#L60)

```rust
fn read_only() i64
```

Returns the mode for read-only access.

### `FileMode::write_only`

[options.crb:62](../stdlib/src/io/options.crb#L62)

```rust
fn write_only() i64
```

Returns the mode for write-only access.

### `FileMode::read_write`

[options.crb:64](../stdlib/src/io/options.crb#L64)

```rust
fn read_write() i64
```

Returns the mode for read and write access.

### `FileMode::append`

[options.crb:66](../stdlib/src/io/options.crb#L66)

```rust
fn append() i64
```

Returns the append flag to combine with a writable access mode.

### `FileMode::truncate`

[options.crb:68](../stdlib/src/io/options.crb#L68)

```rust
fn truncate() i64
```

Returns the truncate flag to combine with a writable access mode.


## `std::io::asyn`

Asynchronous file operations dispatched to the runtime's blocking workers.

Available when `target.os == "linux" && target.arch == "x86_64" && target.pointer_width == "64" || target.os == "macos" && target.arch == "aarch64" || target.os == "macos" && target.arch == "x86_64" || target.os == "windows" && target.arch == "aarch64" || target.os == "windows" && target.arch == "x86_64"`.

### `File`

[file.crb:8](../stdlib/src/io/asyn/file.crb#L8)

```rust
pub struct File
```

Owns a blocking file handle and exposes operations that await worker completion.

Members:

- [`inner`](../stdlib/src/io/asyn/file.crb#L10) (implementation field): Owned platform-specific object used to dispatch this portable wrapper's operations.

### `File::open`

[file.crb:13](../stdlib/src/io/asyn/file.crb#L13)

```rust
async fn open(path: &str, mode: i64) Result<File, FileError>
```

Awaits opening an existing file with the selected mode. The path is UTF-8 without a trailing NUL.

### `File::create`

[file.crb:18](../stdlib/src/io/asyn/file.crb#L18)

```rust
async fn create(path: &str, mode: i64, perm: FilePerm) Result<File, FileError>
```

Awaits opening or creating a file with the selected mode and permissions. The path is UTF-8 without a trailing NUL.

### `File::read`

[file.crb:23](../stdlib/src/io/asyn/file.crb#L23)

```rust
async fn read(&mut self, buffer: &mut [u8]) Result<usize, FileError>
```

Awaits a read into the caller's buffer and returns the actual byte count.

### `File::write`

[file.crb:39](../stdlib/src/io/asyn/file.crb#L39)

```rust
async fn write(&mut self, buffer: &[u8]) Result<usize, FileError>
```

Awaits a write from the caller's buffer and returns the actual byte count.

### `File::read_at`

[file.crb:55](../stdlib/src/io/asyn/file.crb#L55)

```rust
async fn read_at(&self, buffer: &mut [u8], offset: u64) Result<usize, FileError>
```

Awaits a positioned read, preserving the cursor and retaining file/buffer borrows until completion.

### `File::write_at`

[file.crb:74](../stdlib/src/io/asyn/file.crb#L74)

```rust
async fn write_at(&self, buffer: &[u8], offset: u64) Result<usize, FileError>
```

Awaits a positioned write, preserving the cursor and retaining file/buffer borrows until completion.

### `File::seek`

[file.crb:93](../stdlib/src/io/asyn/file.crb#L93)

```rust
async fn seek(&mut self, from: SeekFrom) Result<u64, FileError>
```

Awaits moving the file cursor and returns the new absolute byte offset.

### `File::sync_all`

[file.crb:108](../stdlib/src/io/asyn/file.crb#L108)

```rust
async fn sync_all(&mut self) Result<(), FileError>
```

Awaits sync_all on a blocking worker, retaining mutable permission and the file dependency.

### `File::truncate`

[file.crb:123](../stdlib/src/io/asyn/file.crb#L123)

```rust
async fn truncate(&mut self, length: u64) Result<(), FileError>
```

Awaits truncate on a blocking worker, retaining mutable permission and the file dependency.

### `File::stats`

[file.crb:138](../stdlib/src/io/asyn/file.crb#L138)

```rust
async fn stats(&self) Result<FileStats, FileError>
```

Awaits a snapshot of the open file's metadata.

### `File::rename`

[file.crb:153](../stdlib/src/io/asyn/file.crb#L153)

```rust
async fn rename(source: &str, destination: &str) Result<(), FileError>
```

Awaits moving a filesystem entry to a different path.

### `File::delete`

[file.crb:167](../stdlib/src/io/asyn/file.crb#L167)

```rust
async fn delete(path: &str) Result<(), FileError>
```

Awaits removing a file by path.

### `FileError`

[file.crb:183](../stdlib/src/io/asyn/file.crb#L183)

```rust
pub enum FileError
```

Reports file errors or the runtime's failure to launch a worker.

Members:

- [`InvalidPath`](../stdlib/src/io/asyn/file.crb#L185) (variant): The supplied path violates the platform path-input contract.
- [`InvalidOptions`](../stdlib/src/io/asyn/file.crb#L187) (variant): The requested open-mode combination is invalid.
- [`Os`](../stdlib/src/io/asyn/file.crb#L189) (variant): Preserves the native operating-system error code in code.
- [`Os.code`](../stdlib/src/io/asyn/file.crb#L191) (implementation field): Native operating-system status code preserved by this error.
- [`LaunchFailed`](../stdlib/src/io/asyn/file.crb#L194) (variant): The runtime could not launch the blocking worker.


## `std::io::asyn::buffered`

Asynchronous buffered byte streams with caller-provided storage.

Available when `target.os == "linux" && target.arch == "x86_64" && target.pointer_width == "64" || target.os == "macos" && target.arch == "aarch64" || target.os == "macos" && target.arch == "x86_64" || target.os == "windows" && target.arch == "aarch64" || target.os == "windows" && target.arch == "x86_64"`.

### `BufferedError`

[buffered.crb:8](../stdlib/src/io/asyn/buffered/buffered.crb#L8)

```rust
pub enum BufferedError<E>
```

Preserves the stream's error type and reports writes that make no progress.

Members:

- [`Stream`](../stdlib/src/io/asyn/buffered/buffered.crb#L10) (variant): Wraps the underlying stream error without changing its type.
- [`Stream.error`](../stdlib/src/io/asyn/buffered/buffered.crb#L12) (implementation field): Underlying stream error retained with its original type.
- [`WriteZero`](../stdlib/src/io/asyn/buffered/buffered.crb#L15) (variant): A nonempty write made no progress.

### `BufReader`

[buffered.crb:23](../stdlib/src/io/asyn/buffered/buffered.crb#L23)

```rust
pub struct BufReader<T, E>
```

Reads ahead from a borrowed byte stream into a borrowed buffer.

Members:

- [`stream`](../stdlib/src/io/asyn/buffered/buffered.crb#L25) (implementation field): Exclusively borrowed underlying stream; it must outlive this buffered wrapper.
- [`buffer`](../stdlib/src/io/asyn/buffered/buffered.crb#L27) (implementation field): Caller-owned mutable scratch storage borrowed for the wrapper lifetime.
- [`start`](../stdlib/src/io/asyn/buffered/buffered.crb#L29) (implementation field): Offset of the next unread/unsent buffered byte.
- [`end`](../stdlib/src/io/asyn/buffered/buffered.crb#L31) (implementation field): Exclusive end of the valid buffered byte range.

### `BufReader::new`

[buffered.crb:34](../stdlib/src/io/asyn/buffered/buffered.crb#L34)

```rust
async fn new(stream: &mut T, buffer: &mut [u8]) BufReader<T, E>
```

Borrows the constrained stream and buffer. An empty buffer uses direct reads.

### `BufReader::from_tcp`

[buffered.crb:39](../stdlib/src/io/asyn/buffered/buffered.crb#L39)

```rust
async fn from_tcp(stream: &mut T, buffer: &mut [u8]) BufReader<T, E>
```

Borrows the TCP connection and buffer. An empty buffer uses direct reads.

### `BufReader::read`

[buffered.crb:45](../stdlib/src/io/asyn/buffered/buffered.crb#L45)

```rust
async fn read(&mut self, output: &mut [u8]) Result<usize, BufferedError<E>>
```

Reads into the output, returning the bytes copied. Dropping the reader
discards unread buffered bytes. The underlying stream has already consumed them.

### `BufWriter`

[buffered.crb:90](../stdlib/src/io/asyn/buffered/buffered.crb#L90)

```rust
pub struct BufWriter<T, E>
```

Holds pending output in a borrowed buffer. Call `flush()` to write it to the stream.

Members:

- [`stream`](../stdlib/src/io/asyn/buffered/buffered.crb#L92) (implementation field): Exclusively borrowed underlying stream; it must outlive this buffered wrapper.
- [`buffer`](../stdlib/src/io/asyn/buffered/buffered.crb#L94) (implementation field): Caller-owned mutable scratch storage borrowed for the wrapper lifetime.
- [`start`](../stdlib/src/io/asyn/buffered/buffered.crb#L96) (implementation field): Offset of the next unread/unsent buffered byte.
- [`end`](../stdlib/src/io/asyn/buffered/buffered.crb#L98) (implementation field): Exclusive end of the valid buffered byte range.

### `BufWriter::new`

[buffered.crb:101](../stdlib/src/io/asyn/buffered/buffered.crb#L101)

```rust
async fn new(stream: &mut T, buffer: &mut [u8]) BufWriter<T, E>
```

Borrows the constrained stream and buffer. An empty buffer uses direct writes.

### `BufWriter::from_tcp`

[buffered.crb:106](../stdlib/src/io/asyn/buffered/buffered.crb#L106)

```rust
async fn from_tcp(stream: &mut T, buffer: &mut [u8]) BufWriter<T, E>
```

Borrows the TCP connection and buffer. An empty buffer uses direct writes.

### `BufWriter::write`

[buffered.crb:112](../stdlib/src/io/asyn/buffered/buffered.crb#L112)

```rust
async fn write(&mut self, input: &[u8]) Result<usize, BufferedError<E>>
```

Accepts a prefix of the input and returns the number accepted.
Flushes previously buffered bytes when the buffer is already full.

### `BufWriter::flush`

[buffered.crb:152](../stdlib/src/io/asyn/buffered/buffered.crb#L152)

```rust
async fn flush(&mut self) Result<(), BufferedError<E>>
```

Writes pending bytes to the stream. After an error, retrying starts at the
first byte the stream has yet to accept. Destruction discards pending bytes.


## `std::io::buffered`

Buffered blocking byte streams with caller-provided storage.

Available when `target.os == "linux" && target.arch == "x86_64" && target.pointer_width == "64" || target.os == "macos" && target.arch == "aarch64" || target.os == "macos" && target.arch == "x86_64" || target.os == "windows" && target.arch == "aarch64" || target.os == "windows" && target.arch == "x86_64"`.

### `BufferedError`

[buffered.crb:8](../stdlib/src/io/buffered/buffered.crb#L8)

```rust
pub enum BufferedError<E>
```

Preserves the stream's error type and reports writes that make no progress.

Members:

- [`Stream`](../stdlib/src/io/buffered/buffered.crb#L10) (variant): Wraps the underlying stream error without changing its type.
- [`Stream.error`](../stdlib/src/io/buffered/buffered.crb#L12) (implementation field): Underlying stream error retained with its original type.
- [`WriteZero`](../stdlib/src/io/buffered/buffered.crb#L15) (variant): A nonempty write made no progress.

### `BufReader`

[buffered.crb:23](../stdlib/src/io/buffered/buffered.crb#L23)

```rust
pub struct BufReader<T, E>
```

Reads ahead from a borrowed byte stream into a borrowed buffer.

Members:

- [`stream`](../stdlib/src/io/buffered/buffered.crb#L25) (implementation field): Exclusively borrowed underlying stream; it must outlive this buffered wrapper.
- [`buffer`](../stdlib/src/io/buffered/buffered.crb#L27) (implementation field): Caller-owned mutable scratch storage borrowed for the wrapper lifetime.
- [`start`](../stdlib/src/io/buffered/buffered.crb#L29) (implementation field): Offset of the next unread/unsent buffered byte.
- [`end`](../stdlib/src/io/buffered/buffered.crb#L31) (implementation field): Exclusive end of the valid buffered byte range.

### `BufReader::new`

[buffered.crb:34](../stdlib/src/io/buffered/buffered.crb#L34)

```rust
fn new(stream: &mut T, buffer: &mut [u8]) BufReader<T, E>
```

Borrows the constrained stream and buffer. An empty buffer uses direct reads.

### `BufReader::from_tcp`

[buffered.crb:39](../stdlib/src/io/buffered/buffered.crb#L39)

```rust
fn from_tcp(stream: &mut T, buffer: &mut [u8]) BufReader<T, E>
```

Borrows the TCP connection and buffer. An empty buffer uses direct reads.

### `BufReader::read`

[buffered.crb:45](../stdlib/src/io/buffered/buffered.crb#L45)

```rust
fn read(&mut self, output: &mut [u8]) Result<usize, BufferedError<E>>
```

Reads into the output, returning the bytes copied. Dropping the reader
discards unread buffered bytes. The underlying stream has already consumed them.

### `BufWriter`

[buffered.crb:90](../stdlib/src/io/buffered/buffered.crb#L90)

```rust
pub struct BufWriter<T, E>
```

Holds pending output in a borrowed buffer. Call `flush()` to write it to the stream.

Members:

- [`stream`](../stdlib/src/io/buffered/buffered.crb#L92) (implementation field): Exclusively borrowed underlying stream; it must outlive this buffered wrapper.
- [`buffer`](../stdlib/src/io/buffered/buffered.crb#L94) (implementation field): Caller-owned mutable scratch storage borrowed for the wrapper lifetime.
- [`start`](../stdlib/src/io/buffered/buffered.crb#L96) (implementation field): Offset of the next unread/unsent buffered byte.
- [`end`](../stdlib/src/io/buffered/buffered.crb#L98) (implementation field): Exclusive end of the valid buffered byte range.

### `BufWriter::new`

[buffered.crb:101](../stdlib/src/io/buffered/buffered.crb#L101)

```rust
fn new(stream: &mut T, buffer: &mut [u8]) BufWriter<T, E>
```

Borrows the constrained stream and buffer. An empty buffer uses direct writes.

### `BufWriter::from_tcp`

[buffered.crb:106](../stdlib/src/io/buffered/buffered.crb#L106)

```rust
fn from_tcp(stream: &mut T, buffer: &mut [u8]) BufWriter<T, E>
```

Borrows the TCP connection and buffer. An empty buffer uses direct writes.

### `BufWriter::write`

[buffered.crb:112](../stdlib/src/io/buffered/buffered.crb#L112)

```rust
fn write(&mut self, input: &[u8]) Result<usize, BufferedError<E>>
```

Accepts a prefix of the input and returns the number accepted.
Flushes previously buffered bytes when the buffer is already full.

### `BufWriter::flush`

[buffered.crb:152](../stdlib/src/io/buffered/buffered.crb#L152)

```rust
fn flush(&mut self) Result<(), BufferedError<E>>
```

Writes pending bytes to the stream. After an error, retrying starts at the
first byte the stream has yet to accept. Destruction discards pending bytes.


## `std::iter`

Statically constrained iteration over an explicitly borrowed source.

### `Iter`

[iter.crb:9](../stdlib/src/iter/iter.crb#L9)

```rust
pub struct Iter<T, V>
```

Borrows a source mutably without implying uniqueness. The source must outlive the iterator.

Members:

- [`source`](../stdlib/src/iter/iter.crb#L11) (implementation field): Exclusively borrowed source; it must remain valid for the complete iterator lifetime.

### `Iter::new`

[iter.crb:14](../stdlib/src/iter/iter.crb#L14)

```rust
fn new(source: &mut T) Iter<T, V>
```

Captures the source reference when the iterator is constructed.

### `Iter::next`

[iter.crb:19](../stdlib/src/iter/iter.crb#L19)

```rust
fn next(&mut self) Option<V>
```

Requests one item through the source's statically resolved method.

### `Iter::collect`

[iter.crb:26](../stdlib/src/iter/iter.crb#L26)

```rust
fn collect(mut self: Iter<T, V>, destination: &mut D)
```

Consumes this chain and appends its remaining items to the destination.

### `Map`

[iter.crb:41](../stdlib/src/iter/iter.crb#L41)

```rust
pub struct Map<T, V, X>
```

Owns its predecessor and mapper. Items retain their ordinary dependencies.

Members:

- [`previous`](../stdlib/src/iter/iter.crb#L43) (implementation field): Owned preceding pipeline stage; dropping this stage also cleans up that predecessor.
- [`mapper`](../stdlib/src/iter/iter.crb#L45) (implementation field): Stored transformation/predicate/reduction function and its captured state.

### `Map::next`

[iter.crb:48](../stdlib/src/iter/iter.crb#L48)

```rust
fn next(&mut self) Option<X>
```

Advances the predecessor once and transforms the yielded item.

### `Map::collect`

[iter.crb:57](../stdlib/src/iter/iter.crb#L57)

```rust
fn collect(mut self: Map<T, V, X>, destination: &mut D)
```

Consumes this chain and appends its remaining items to the destination.

### `Filter`

[iter.crb:71](../stdlib/src/iter/iter.crb#L71)

```rust
pub struct Filter<T, V>
```

Owns its predecessor and predicate; rejected items are destroyed normally.

Members:

- [`previous`](../stdlib/src/iter/iter.crb#L73) (implementation field): Owned preceding pipeline stage; dropping this stage also cleans up that predecessor.
- [`mapper`](../stdlib/src/iter/iter.crb#L75) (implementation field): Stored transformation/predicate/reduction function and its captured state.

### `Filter::next`

[iter.crb:78](../stdlib/src/iter/iter.crb#L78)

```rust
fn next(&mut self) Option<V>
```

Returns the next accepted item. The predicate borrows it for this call.

### `Filter::collect`

[iter.crb:93](../stdlib/src/iter/iter.crb#L93)

```rust
fn collect(mut self: Filter<T, V>, destination: &mut D)
```

Consumes this chain and appends its remaining items to the destination.

### `Reduce`

[iter.crb:107](../stdlib/src/iter/iter.crb#L107)

```rust
pub struct Reduce<T, V>
```

Reduces a source once, using its first item as the initial accumulator.

Members:

- [`previous`](../stdlib/src/iter/iter.crb#L109) (implementation field): Owned preceding pipeline stage; dropping this stage also cleans up that predecessor.
- [`mapper`](../stdlib/src/iter/iter.crb#L111) (implementation field): Stored transformation/predicate/reduction function and its captured state.
- [`finished`](../stdlib/src/iter/iter.crb#L113) (implementation field): Records that this reduction has already consumed its source and must yield no more items.

### `Reduce::next`

[iter.crb:116](../stdlib/src/iter/iter.crb#L116)

```rust
fn next(&mut self) Option<V>
```

Consumes the remaining source and yields at most one accumulated item.

### `Reduce::remaining`

[iter.crb:127](../stdlib/src/iter/iter.crb#L127)

```rust
fn remaining(&mut self, mut accumulator: V) V
```

Folds the remainder into an existing accumulator without fabricating a default.

### `Reduce::collect`

[iter.crb:139](../stdlib/src/iter/iter.crb#L139)

```rust
fn collect(mut self: Reduce<T, V>, destination: &mut D)
```

Consumes this chain and appends its remaining items to the destination.

### `iter`

[iter.crb:153](../stdlib/src/iter/iter.crb#L153)

```rust
pub fn iter(source: &mut T) Iter<T, V>
```

Builds an iterator with explicit mutable permission and a dependency on its source.


## `std::net`

Shared socket errors and metadata for incoming UDP datagrams.

Available when `target.os == "linux" && target.arch == "x86_64" && target.pointer_width == "64" || target.os == "macos" && target.arch == "aarch64" || target.os == "macos" && target.arch == "x86_64" || target.os == "windows" && target.arch == "aarch64" || target.os == "windows" && target.arch == "x86_64"`.

### `SocketError`

[socket.crb:17](../stdlib/src/net/socket.crb#L17)

```rust
pub enum SocketError
```

Reports platform errors and socket conditions such as an occupied address or an oversized datagram.

Members:

- [`Os`](../stdlib/src/net/socket.crb#L19) (variant): Preserves the native operating-system error code in code.
- [`Os.code`](../stdlib/src/net/socket.crb#L21) (implementation field): Native operating-system status code preserved by this error.
- [`AddressInUse`](../stdlib/src/net/socket.crb#L24) (variant): The requested local endpoint is already in use.
- [`ConnectionRefused`](../stdlib/src/net/socket.crb#L26) (variant): The remote endpoint refused the connection.
- [`DatagramTooLarge`](../stdlib/src/net/socket.crb#L28) (variant): The received datagram exceeded the supplied buffer and was consumed.

### `Datagram`

[socket.crb:32](../stdlib/src/net/socket.crb#L32)

```rust
pub struct Datagram
```

Stores the received datagram's byte count and sender address.

Members:

- [`size`](../stdlib/src/net/socket.crb#L34) (implementation field): Number of received datagram payload bytes.
- [`peer`](../stdlib/src/net/socket.crb#L36) (implementation field): Packed sender IPv4 address and port, decoded by the public peer accessor.

### `Datagram::count`

[socket.crb:39](../stdlib/src/net/socket.crb#L39)

```rust
fn count(&self) usize
```

Returns how many payload bytes were received.

### `Datagram::sender`

[socket.crb:42](../stdlib/src/net/socket.crb#L42)

```rust
fn sender(&self) SocketAddr
```

Returns the datagram's source IPv4 address and port.

### `datagram`

[socket.crb:51](../stdlib/src/net/socket.crb#L51)

```rust
pub fn datagram(size: u64, peer: u64) Datagram
```

Creates metadata for the byte count and sender returned by a receive operation.


## `std::net::asyn::tcp`

Asynchronous IPv4 TCP connections, listeners and borrowed stream halves.

Available when `target.os == "linux" && target.arch == "x86_64" && target.pointer_width == "64" || target.os == "macos" && target.arch == "aarch64" || target.os == "macos" && target.arch == "x86_64" || target.os == "windows" && target.arch == "aarch64" || target.os == "windows" && target.arch == "x86_64"`.

### `Connection`

[socket.crb:12](../stdlib/src/net/asyn/tcp/socket.crb#L12)

```rust
pub struct Connection
```

Owns the socket used by asynchronous TCP reads and writes.

Members:

- [`__din_package_socket`](../stdlib/src/net/asyn/tcp/socket.crb#L14) (implementation field): Owned native socket storage; the connection/listener closes it on destruction.
- [`local_address`](../stdlib/src/net/asyn/tcp/socket.crb#L16) (implementation field): Cached local IPv4 endpoint, including any OS-assigned port.
- [`remote_address`](../stdlib/src/net/asyn/tcp/socket.crb#L18) (implementation field): Cached remote IPv4 endpoint.
- [`read_descriptor`](../stdlib/src/net/asyn/tcp/socket.crb#L20) (implementation field): Descriptor view reserved for the read half; the connection retains closure responsibility.
- [`write_descriptor`](../stdlib/src/net/asyn/tcp/socket.crb#L22) (implementation field): Descriptor view reserved for the write half; the connection retains closure responsibility.

### `Connection::split`

[socket.crb:25](../stdlib/src/net/asyn/tcp/socket.crb#L25)

```rust
fn split(&mut self) (ReadHalf, WriteHalf)
```

Borrows separate read and write views from the connection, which still owns the socket.

### `Connection::addr`

[socket.crb:32](../stdlib/src/net/asyn/tcp/socket.crb#L32)

```rust
fn addr(&self) SocketAddr
```

Returns the local IPv4 address and port, including a port assigned by the OS.

### `Connection::peer`

[socket.crb:38](../stdlib/src/net/asyn/tcp/socket.crb#L38)

```rust
fn peer(&self) SocketAddr
```

Returns the remote IPv4 address and port associated with the connection.

### `Connection::write`

[socket.crb:44](../stdlib/src/net/asyn/tcp/socket.crb#L44)

```rust
async fn write(&mut self, buffer: &[u8]) Result<usize, SocketError>
```

Awaits a write from the borrowed slice and returns the actual byte count.

### `Connection::read`

[socket.crb:51](../stdlib/src/net/asyn/tcp/socket.crb#L51)

```rust
async fn read(&mut self, buffer: &mut [u8]) Result<usize, SocketError>
```

Awaits bytes into the borrowed output slice. Zero indicates EOF when the slice is nonempty.

### `ReadHalf`

[socket.crb:59](../stdlib/src/net/asyn/tcp/socket.crb#L59)

```rust
pub struct ReadHalf
```

Borrows the portion of a TCP connection needed to read without owning its socket.

Members:

- [`descriptor`](../stdlib/src/net/asyn/tcp/socket.crb#L61) (implementation field): Borrowed native descriptor view; its owning connection must outlive this half.

### `ReadHalf::read`

[socket.crb:64](../stdlib/src/net/asyn/tcp/socket.crb#L64)

```rust
async fn read(&mut self, buffer: &mut [u8]) Result<usize, SocketError>
```

Awaits bytes into the borrowed output slice. Zero indicates EOF when the slice is nonempty.

### `WriteHalf`

[socket.crb:71](../stdlib/src/net/asyn/tcp/socket.crb#L71)

```rust
pub struct WriteHalf
```

Borrows the portion of a TCP connection needed to write without owning its socket.

Members:

- [`descriptor`](../stdlib/src/net/asyn/tcp/socket.crb#L73) (implementation field): Borrowed native descriptor view; its owning connection must outlive this half.

### `WriteHalf::write`

[socket.crb:76](../stdlib/src/net/asyn/tcp/socket.crb#L76)

```rust
async fn write(&mut self, buffer: &[u8]) Result<usize, SocketError>
```

Awaits a write from the borrowed slice and returns the actual byte count.

### `Listener`

[socket.crb:85](../stdlib/src/net/asyn/tcp/socket.crb#L85)

```rust
pub struct Listener
```

Owns a nonblocking listening socket for asynchronous accepts.

Members:

- [`__din_package_socket`](../stdlib/src/net/asyn/tcp/socket.crb#L87) (implementation field): Owned native socket storage; the connection/listener closes it on destruction.
- [`local_address`](../stdlib/src/net/asyn/tcp/socket.crb#L89) (implementation field): Cached local IPv4 endpoint, including any OS-assigned port.

### `Listener::bind`

[socket.crb:92](../stdlib/src/net/asyn/tcp/socket.crb#L92)

```rust
fn bind(address: SocketAddr, backlog: Option<i32>) Result<Listener, SocketError>
```

Binds a TCP listener and prepares its native socket for asynchronous accepts.

### `Listener::addr`

[socket.crb:112](../stdlib/src/net/asyn/tcp/socket.crb#L112)

```rust
fn addr(&self) SocketAddr
```

Returns the local IPv4 address and port, including a port assigned by the OS.

### `Listener::accept`

[socket.crb:118](../stdlib/src/net/asyn/tcp/socket.crb#L118)

```rust
async fn accept(&mut self) Result<Connection, SocketError>
```

Awaits an incoming TCP connection and returns its owned socket wrapper.

### `connect`

[socket.crb:147](../stdlib/src/net/asyn/tcp/socket.crb#L147)

```rust
pub async fn connect(address: SocketAddr) Result<Connection, SocketError>
```

Awaits a nonblocking TCP connection to the supplied endpoint.


## `std::net::asyn::udp`

Asynchronous IPv4 UDP I/O with synchronous socket setup.

Available when `target.os == "linux" && target.arch == "x86_64" && target.pointer_width == "64" || target.os == "macos" && target.arch == "aarch64" || target.os == "macos" && target.arch == "x86_64" || target.os == "windows" && target.arch == "aarch64" || target.os == "windows" && target.arch == "x86_64"`.

### `Connection`

[socket.crb:12](../stdlib/src/net/asyn/udp/socket.crb#L12)

```rust
pub struct Connection
```

Owns a UDP socket prepared for asynchronous I/O with an associated peer.

Members:

- [`__din_package_socket`](../stdlib/src/net/asyn/udp/socket.crb#L14) (implementation field): Owned native socket storage; the connection/listener closes it on destruction.
- [`local_address`](../stdlib/src/net/asyn/udp/socket.crb#L16) (implementation field): Cached local IPv4 endpoint, including any OS-assigned port.
- [`remote_address`](../stdlib/src/net/asyn/udp/socket.crb#L18) (implementation field): Cached remote IPv4 endpoint.

### `Connection::addr`

[socket.crb:21](../stdlib/src/net/asyn/udp/socket.crb#L21)

```rust
fn addr(&self) SocketAddr
```

Returns the local IPv4 address and port, including a port assigned by the OS.

### `Connection::peer`

[socket.crb:27](../stdlib/src/net/asyn/udp/socket.crb#L27)

```rust
fn peer(&self) SocketAddr
```

Returns the remote IPv4 address and port associated with the connection.

### `Connection::send`

[socket.crb:33](../stdlib/src/net/asyn/udp/socket.crb#L33)

```rust
async fn send(&mut self, buffer: &[u8]) Result<usize, SocketError>
```

Awaits transmission of one complete datagram to the connected peer, including an empty datagram.

### `Connection::recv`

[socket.crb:40](../stdlib/src/net/asyn/udp/socket.crb#L40)

```rust
async fn recv(&mut self, buffer: &mut [u8]) Result<usize, SocketError>
```

Awaits one datagram from the connected peer. An oversized payload is consumed and reported.

### `Listener`

[socket.crb:52](../stdlib/src/net/asyn/udp/socket.crb#L52)

```rust
pub struct Listener
```

Owns a bound UDP socket prepared for asynchronous addressed I/O.

Members:

- [`__din_package_socket`](../stdlib/src/net/asyn/udp/socket.crb#L54) (implementation field): Owned native socket storage; the connection/listener closes it on destruction.
- [`local_address`](../stdlib/src/net/asyn/udp/socket.crb#L56) (implementation field): Cached local IPv4 endpoint, including any OS-assigned port.

### `Listener::bind`

[socket.crb:59](../stdlib/src/net/asyn/udp/socket.crb#L59)

```rust
fn bind(address: SocketAddr) Result<Listener, SocketError>
```

Binds the supplied endpoint and prepares the socket for asynchronous I/O.

### `Listener::addr`

[socket.crb:75](../stdlib/src/net/asyn/udp/socket.crb#L75)

```rust
fn addr(&self) SocketAddr
```

Returns the local IPv4 address and port, including a port assigned by the OS.

### `Listener::recv`

[socket.crb:81](../stdlib/src/net/asyn/udp/socket.crb#L81)

```rust
async fn recv(&mut self, buffer: &mut [u8]) Result<Datagram, SocketError>
```

Awaits one datagram and its sender address. An oversized payload is consumed and reported.

### `Listener::send`

[socket.crb:87](../stdlib/src/net/asyn/udp/socket.crb#L87)

```rust
async fn send(&mut self, buffer: &[u8], destination: SocketAddr) Result<usize, SocketError>
```

Awaits transmission of one complete datagram to the supplied destination, including an empty datagram.

### `connect`

[socket.crb:95](../stdlib/src/net/asyn/udp/socket.crb#L95)

```rust
pub fn connect(address: SocketAddr) Result<Connection, SocketError>
```

Associates a UDP socket with a peer and prepares it for asynchronous I/O.


## `std::net::http`

Bounded HTTP/1.x heads and optional framed bodies over structural readers.
Response body indication follows headers; the caller handles HEAD/context.

### `REQUEST_LINE_MAX_SIZE`

[http.crb:8](../stdlib/src/net/http/http.crb#L8)

```rust
pub const REQUEST_LINE_MAX_SIZE: usize = 8192
```

Maximum request/status-line bytes, excluding CRLF.

### `HEADER_LINE_MAX_SIZE`

[http.crb:11](../stdlib/src/net/http/http.crb#L11)

```rust
pub const HEADER_LINE_MAX_SIZE: usize = 8192
```

Maximum individual header or chunk-line bytes, excluding CRLF.

### `HEADERS_MAX_SIZE`

[http.crb:14](../stdlib/src/net/http/http.crb#L14)

```rust
pub const HEADERS_MAX_SIZE: usize = 32768
```

Maximum complete header/trailer section bytes, including CRLF terminators.

### `HEADER_COUNT_MAX`

[http.crb:17](../stdlib/src/net/http/http.crb#L17)

```rust
pub const HEADER_COUNT_MAX: usize = 100
```

Maximum number of header/trailer fields, counting repeated fields.

### `ParseError`

[http.crb:21](../stdlib/src/net/http/http.crb#L21)

```rust
pub enum ParseError<E>
```

Parsing failures retain transport errors and distinguish budgets from syntax.

Members:

- [`Read`](../stdlib/src/net/http/http.crb#L23) (variant): Original reader error.
- [`Read.error`](../stdlib/src/net/http/http.crb#L25) (implementation field): Transport-specific error value.
- [`UnexpectedEof`](../stdlib/src/net/http/http.crb#L28) (variant): EOF occurred inside a head or a framed body.
- [`InvalidStartLine`](../stdlib/src/net/http/http.crb#L30) (variant): Invalid request/status line or unsupported HTTP version.
- [`InvalidHeader`](../stdlib/src/net/http/http.crb#L32) (variant): Invalid field syntax or obsolete line folding.
- [`LineTooLong`](../stdlib/src/net/http/http.crb#L34) (variant): A request/status/header/chunk line exceeds its selected bound.
- [`HeadersTooLarge`](../stdlib/src/net/http/http.crb#L36) (variant): The complete header/trailer section exceeds its selected bound.
- [`TooManyHeaders`](../stdlib/src/net/http/http.crb#L38) (variant): Too many header/trailer fields.
- [`InvalidFraming`](../stdlib/src/net/http/http.crb#L40) (variant): Ambiguous, unsupported or malformed body framing.
- [`InvalidChunk`](../stdlib/src/net/http/http.crb#L42) (variant): Malformed chunk size or delimiter.
- [`InvalidReadCount`](../stdlib/src/net/http/http.crb#L44) (variant): The reader returned a count larger than its output slice.

### `Version`

[http.crb:48](../stdlib/src/net/http/http.crb#L48)

```rust
pub enum Version
```

Versions accepted by this HTTP/1.x parser.

Members:

- [`Http10`](../stdlib/src/net/http/http.crb#L50) (variant): HTTP/1.0.
- [`Http11`](../stdlib/src/net/http/http.crb#L52) (variant): HTTP/1.1.

### `Header`

[http.crb:56](../stdlib/src/net/http/http.crb#L56)

```rust
pub struct Header
```

A field view borrows its message's header storage; duplicates stay distinct.

Members:

- [`name`](../stdlib/src/net/http/http.crb#L58) (implementation field): ASCII field name, preserving its spelling.
- [`value`](../stdlib/src/net/http/http.crb#L60) (implementation field): Field value bytes with surrounding SP/HTAB removed.

### `Header::name`

[http.crb:63](../stdlib/src/net/http/http.crb#L63)

```rust
fn name(&self) &str
```

Returns the validated ASCII field name.

### `Header::value`

[http.crb:65](../stdlib/src/net/http/http.crb#L65)

```rust
fn value(&self) &[u8]
```

Borrows the original field value bytes, without UTF-8 interpretation.

### `Headers`

[http.crb:71](../stdlib/src/net/http/http.crb#L71)

```rust
pub struct Headers
```

Owns bounded raw header bytes; traversal needs no separately allocated index.

Members:

- [`bytes`](../stdlib/src/net/http/http.crb#L73) (implementation field): Parsed lines retain CRLF to permit offset-based traversal.
- [`used`](../stdlib/src/net/http/http.crb#L75) (implementation field): Number of populated bytes, including the final empty line.
- [`count`](../stdlib/src/net/http/http.crb#L77) (implementation field): Number of fields, including duplicates.

### `Headers::len`

[http.crb:80](../stdlib/src/net/http/http.crb#L80)

```rust
fn len(&self) usize
```

Number of header fields; repeated names each count once.

### `Headers::get`

[http.crb:82](../stdlib/src/net/http/http.crb#L82)

```rust
fn get(&self, index: usize) Option<Header>
```

Returns the field at an ordinal, preserving repeats and arrival order.

### `BodyReader`

[http.crb:206](../stdlib/src/net/http/http.crb#L206)

```rust
pub struct BodyReader<R, E>
```

Borrows a reader and exposes only declared body bytes; dropping never drains.

Members:

- [`source`](../stdlib/src/net/http/http.crb#L208) (implementation field): Injected reader, retained for this message's body lifetime.
- [`mode`](../stdlib/src/net/http/http.crb#L210) (implementation field): Zero: absent; one: Content-Length; two: chunked.
- [`remaining`](../stdlib/src/net/http/http.crb#L212) (implementation field): Unread bytes in the current fixed-length body or chunk.
- [`delimiter`](../stdlib/src/net/http/http.crb#L214) (implementation field): A nonfinal chunk has been consumed and its CRLF is pending.
- [`finished`](../stdlib/src/net/http/http.crb#L216) (implementation field): The declared body has ended.

### `BodyReader::new`

[http.crb:219](../stdlib/src/net/http/http.crb#L219)

```rust
fn new(reader: &mut R) BodyReader<R, E>
```

Captures the reader without performing transport access.

### `BodyReader::one`

[http.crb:224](../stdlib/src/net/http/http.crb#L224)

```rust
fn one(&mut self) Result<Option<u8>, ParseError<E>>
```

Reads exactly one logical byte, preserving any buffered-reader lookahead.

### `BodyReader::line`

[http.crb:237](../stdlib/src/net/http/http.crb#L237)

```rust
fn line(&mut self, output: &mut [u8]) Result<Option<usize>, ParseError<E>>
```

Reads one strict CRLF line without copying its terminator into output.

### `BodyReader::headers`

[http.crb:263](../stdlib/src/net/http/http.crb#L263)

```rust
fn headers(&mut self) Result<Headers, ParseError<E>>
```

Reads a bounded section into owned storage, retaining repeated field lines.

### `BodyReader::read`

[http.crb:290](../stdlib/src/net/http/http.crb#L290)

```rust
fn read(&mut self, output: &mut [u8]) Result<usize, ParseError<E>>
```

Reads a body prefix; empty output causes no transport access.

### `Request`

[http.crb:347](../stdlib/src/net/http/http.crb#L347)

```rust
pub struct Request<R, E>
```

Owns request-head bytes and a reader-dependent optional body descriptor.

Members:

- [`line`](../stdlib/src/net/http/http.crb#L349) (implementation field): Request line bytes, excluding CRLF.
- [`method_end`](../stdlib/src/net/http/http.crb#L351) (implementation field): End of the method token.
- [`target_end`](../stdlib/src/net/http/http.crb#L353) (implementation field): End of the request target.
- [`protocol`](../stdlib/src/net/http/http.crb#L355) (implementation field): Parsed protocol version.
- [`fields`](../stdlib/src/net/http/http.crb#L357) (implementation field): Owned header section.
- [`body_reader`](../stdlib/src/net/http/http.crb#L359) (implementation field): Optional body's framing state and reader dependency.

### `Request::method`

[http.crb:362](../stdlib/src/net/http/http.crb#L362)

```rust
fn method(&self) &str
```

Returns the method as a borrowed ASCII text view, including extensions.

### `Request::target`

[http.crb:364](../stdlib/src/net/http/http.crb#L364)

```rust
fn target(&self) &str
```

Returns the unmodified request target as a borrowed ASCII text view.

### `Request::version`

[http.crb:366](../stdlib/src/net/http/http.crb#L366)

```rust
fn version(&self) &Version
```

Returns the protocol version without transferring its storage.

### `Request::headers`

[http.crb:368](../stdlib/src/net/http/http.crb#L368)

```rust
fn headers(&self) &Headers
```

Borrows owned headers, retaining repeats.

### `Request::body`

[http.crb:370](../stdlib/src/net/http/http.crb#L370)

```rust
fn body(&mut self) Option<&mut BodyReader<R, E>>
```

Borrows the optional framed body; this operation itself performs no reads.

### `Response`

[http.crb:380](../stdlib/src/net/http/http.crb#L380)

```rust
pub struct Response<R, E>
```

Owns response-head bytes; the caller supplies request-dependent semantics.

Members:

- [`line`](../stdlib/src/net/http/http.crb#L382) (implementation field): Status line bytes, excluding CRLF.
- [`line_length`](../stdlib/src/net/http/http.crb#L384) (implementation field): Populated status-line bytes.
- [`code`](../stdlib/src/net/http/http.crb#L386) (implementation field): Three-digit status code.
- [`protocol`](../stdlib/src/net/http/http.crb#L388) (implementation field): Parsed protocol version.
- [`fields`](../stdlib/src/net/http/http.crb#L390) (implementation field): Owned header section.
- [`body_reader`](../stdlib/src/net/http/http.crb#L392) (implementation field): Header-indicated body, which must not be read for a HEAD response.

### `Response::status`

[http.crb:395](../stdlib/src/net/http/http.crb#L395)

```rust
fn status(&self) u16
```

Returns the status code.

### `Response::reason`

[http.crb:397](../stdlib/src/net/http/http.crb#L397)

```rust
fn reason(&self) &[u8]
```

Returns reason-phrase octets without imposing UTF-8.

### `Response::version`

[http.crb:399](../stdlib/src/net/http/http.crb#L399)

```rust
fn version(&self) &Version
```

Returns the parsed protocol version.

### `Response::headers`

[http.crb:401](../stdlib/src/net/http/http.crb#L401)

```rust
fn headers(&self) &Headers
```

Borrows the response header section.

### `Response::body`

[http.crb:403](../stdlib/src/net/http/http.crb#L403)

```rust
fn body(&mut self) Option<&mut BodyReader<R, E>>
```

Returns a header-indicated body; caller handles HEAD and exchange context.

### `request`

[http.crb:428](../stdlib/src/net/http/http.crb#L428)

```rust
pub fn request(reader: &mut R) Result<Option<Request<R, E>>, ParseError<E>>
```

Parses one request head, without prefetching body or next-request bytes.

### `response`

[http.crb:456](../stdlib/src/net/http/http.crb#L456)

```rust
pub fn response(reader: &mut R) Result<Option<Response<R, E>>, ParseError<E>>
```

Parses one response head; a declared body is an indication, not HEAD context.


## `std::net::ipv4`

IPv4 addresses and socket endpoints with dotted-decimal parsing.

### `Addr`

[address.crb:5](../stdlib/src/net/ipv4/address.crb#L5)

```rust
pub struct Addr
```

Stores an IPv4 address as four packed octets.

Members:

- [`bits`](../stdlib/src/net/ipv4/address.crb#L7) (implementation field): IPv4 address bits in the representation used by from_parts and octet accessors.

### `Addr::new`

[address.crb:10](../stdlib/src/net/ipv4/address.crb#L10)

```rust
fn new(a: u8, b: u8, c: u8, d: u8) Addr
```

Packs four IPv4 octets in network order.

### `SocketAddr`

[address.crb:16](../stdlib/src/net/ipv4/address.crb#L16)

```rust
pub struct SocketAddr
```

Pairs a packed IPv4 address with a 16-bit port.

Members:

- [`bits`](../stdlib/src/net/ipv4/address.crb#L18) (implementation field): IPv4 address bits in the representation used by from_parts and octet accessors.
- [`port_number`](../stdlib/src/net/ipv4/address.crb#L20) (implementation field): Transport port number, including zero before OS port allocation.

### `SocketAddr::new`

[address.crb:23](../stdlib/src/net/ipv4/address.crb#L23)

```rust
fn new(ip: Addr, port: u16) SocketAddr
```

Pairs an IPv4 address with the supplied port number.

### `SocketAddr::ipv4_bits`

[address.crb:28](../stdlib/src/net/ipv4/address.crb#L28)

```rust
fn ipv4_bits(&self) u32
```

Returns the address with the first IPv4 octet in the high byte.

### `SocketAddr::port`

[address.crb:31](../stdlib/src/net/ipv4/address.crb#L31)

```rust
fn port(&self) u16
```

Returns the socket endpoint's port number.

### `SocketAddr::parse`

[address.crb:34](../stdlib/src/net/ipv4/address.crb#L34)

```rust
fn parse(text: &str) Result<SocketAddr, ParseError>
```

Parses an IPv4 endpoint written as four decimal octets, a colon and a decimal port.

### `ParseError`

[address.crb:71](../stdlib/src/net/ipv4/address.crb#L71)

```rust
pub enum ParseError
```

Reports invalid IPv4 endpoint syntax or an out-of-range address component.

Members:

- [`InvalidAddress`](../stdlib/src/net/ipv4/address.crb#L73) (variant): The IPv4 address or port text is malformed or out of range.

### `from_parts`

[address.crb:79](../stdlib/src/net/ipv4/address.crb#L79)

```rust
pub fn from_parts(ip: u32, port: u16) SocketAddr
```

Constructs a socket endpoint from packed IPv4 bits and a port.


## `std::net::tcp`

Blocking IPv4 TCP connections and listeners over the platform socket API.

Available when `target.os == "linux" && target.arch == "x86_64" && target.pointer_width == "64" || target.os == "macos" && target.arch == "aarch64" || target.os == "macos" && target.arch == "x86_64" || target.os == "windows" && target.arch == "aarch64" || target.os == "windows" && target.arch == "x86_64"`.

### `Connection`

[socket.crb:10](../stdlib/src/net/tcp/socket.crb#L10)

```rust
pub struct Connection
```

Owns a connected IPv4 TCP socket.

Members:

- [`__din_package_socket`](../stdlib/src/net/tcp/socket.crb#L12) (implementation field): Owned native socket storage; the connection/listener closes it on destruction.
- [`local_address`](../stdlib/src/net/tcp/socket.crb#L14) (implementation field): Cached local IPv4 endpoint, including any OS-assigned port.
- [`remote_address`](../stdlib/src/net/tcp/socket.crb#L16) (implementation field): Cached remote IPv4 endpoint.

### `Connection::addr`

[socket.crb:19](../stdlib/src/net/tcp/socket.crb#L19)

```rust
fn addr(&self) SocketAddr
```

Returns the local IPv4 address and port, including a port assigned by the OS.

### `Connection::peer`

[socket.crb:25](../stdlib/src/net/tcp/socket.crb#L25)

```rust
fn peer(&self) SocketAddr
```

Returns the remote IPv4 address and port associated with the connection.

### `Connection::write`

[socket.crb:31](../stdlib/src/net/tcp/socket.crb#L31)

```rust
fn write(&mut self, buffer: &[u8]) Result<usize, SocketError>
```

Writes bytes from the caller's slice and returns the number accepted, which may be less than its length.

### `Connection::read`

[socket.crb:38](../stdlib/src/net/tcp/socket.crb#L38)

```rust
fn read(&mut self, buffer: &mut [u8]) Result<usize, SocketError>
```

Reads into the caller's slice and returns the bytes copied. An empty buffer returns zero.

### `Listener`

[socket.crb:46](../stdlib/src/net/tcp/socket.crb#L46)

```rust
pub struct Listener
```

Owns a TCP listening socket and accepts incoming connections.

Members:

- [`__din_package_socket`](../stdlib/src/net/tcp/socket.crb#L48) (implementation field): Owned native socket storage; the connection/listener closes it on destruction.
- [`local_address`](../stdlib/src/net/tcp/socket.crb#L50) (implementation field): Cached local IPv4 endpoint, including any OS-assigned port.

### `Listener::bind`

[socket.crb:53](../stdlib/src/net/tcp/socket.crb#L53)

```rust
fn bind(address: SocketAddr, backlog: Option<i32>) Result<Listener, SocketError>
```

Binds and listens at the supplied endpoint. Use port zero for an assigned port and None for the system maximum backlog.

### `Listener::addr`

[socket.crb:70](../stdlib/src/net/tcp/socket.crb#L70)

```rust
fn addr(&self) SocketAddr
```

Returns the local IPv4 address and port, including a port assigned by the OS.

### `Listener::accept`

[socket.crb:76](../stdlib/src/net/tcp/socket.crb#L76)

```rust
fn accept(&mut self) Result<Connection, SocketError>
```

Blocks until it can return an owned accepted TCP connection or an error.

### `connect`

[socket.crb:101](../stdlib/src/net/tcp/socket.crb#L101)

```rust
pub fn connect(address: SocketAddr) Result<Connection, SocketError>
```

Establishes a blocking TCP connection to the supplied endpoint.


## `std::net::tls`

TLS 1.3 handshake framing, extensions and Certificate message encoding.

### `Certificate`

[codec.crb:287](../stdlib/src/net/tls/codec.crb#L287)

```rust
pub struct Certificate
```

Stores the byte ranges of a parsed TLS Certificate message in the caller's input.

Members:

- [`context_size`](../stdlib/src/net/tls/codec.crb#L289) (implementation field): Byte length of the TLS Certificate request context.
- [`entries`](../stdlib/src/net/tls/codec.crb#L291) (implementation field): Number of parsed certificate-list entries.
- [`der_ranges`](../stdlib/src/net/tls/codec.crb#L293) (implementation field): Start/end offsets of the bounded certificate DER entries.
- [`extension_ranges`](../stdlib/src/net/tls/codec.crb#L295) (implementation field): Start/end offsets of each certificate entry's extensions.

### `Certificate::from_message`

[codec.crb:298](../stdlib/src/net/tls/codec.crb#L298)

```rust
fn from_message(input: &[u8]) Result<Certificate, HandshakeError>
```

Parses a complete TLS Certificate handshake message and records the ranges in it.

### `Certificate::context_length`

[codec.crb:312](../stdlib/src/net/tls/codec.crb#L312)

```rust
fn context_length(&self) u64
```

Returns the request context length in bytes.

### `Certificate::context_range`

[codec.crb:315](../stdlib/src/net/tls/codec.crb#L315)

```rust
fn context_range(&self) (u64, u64)
```

Returns the start and exclusive end of the request context.

### `Certificate::count`

[codec.crb:320](../stdlib/src/net/tls/codec.crb#L320)

```rust
fn count(&self) u64
```

Returns the number of certificate entries in the handshake message.

### `Certificate::der_range`

[codec.crb:323](../stdlib/src/net/tls/codec.crb#L323)

```rust
fn der_range(&self, index: u64) (u64, u64)
```

Returns the start and exclusive end of the DER bytes for an entry.

### `Certificate::extensions_range`

[codec.crb:329](../stdlib/src/net/tls/codec.crb#L329)

```rust
fn extensions_range(&self, index: u64) (u64, u64)
```

Returns the start and exclusive end of the encoded extensions for an entry.

### `Certificate::supports_server_certificate`

[codec.crb:335](../stdlib/src/net/tls/codec.crb#L335)

```rust
fn supports_server_certificate(&self) bool
```

Checks the request context and entry extensions for the supported server profile.

### `Certificate::server_key`

[codec.crb:348](../stdlib/src/net/tls/codec.crb#L348)

```rust
fn server_key(&self, input: &[u8], anchor: &[u8], hostname: &[u8], now: i64) Result<X509PublicKey, HandshakeError>
```

Checks the received certificate against a configured pin and obtains the associated public key.


Client and server handshake state machines for the blocking P-256 TLS 1.3 profile.

Available when `target.os == "linux" && target.arch == "x86_64" && target.pointer_width == "64" || target.os == "macos" && target.arch == "aarch64" || target.os == "macos" && target.arch == "x86_64" || target.os == "windows" && target.arch == "aarch64" || target.os == "windows" && target.arch == "x86_64"`.

### `Session`

[handshake.crb:14](../stdlib/src/net/tls/handshake.crb#L14)

```rust
pub struct Session
```

Holds the read and write ciphers established by a successful TLS handshake.

Members:

- [`reader`](../stdlib/src/net/tls/handshake.crb#L16) (implementation field): Owned inbound record cipher established by the handshake.
- [`writer`](../stdlib/src/net/tls/handshake.crb#L18) (implementation field): Owned outbound record cipher established by the handshake.

### `Session::write_application`

[handshake.crb:21](../stdlib/src/net/tls/handshake.crb#L21)

```rust
fn write_application(&mut self, socket: &mut Connection, content: &[u8], fragment: &mut [u8], wire: &mut [u8]) Result<(), HandshakeError>
```

Protects and sends an application record on the original TCP connection.

### `Session::read_application`

[handshake.crb:33](../stdlib/src/net/tls/handshake.crb#L33)

```rust
fn read_application(&mut self, socket: &mut Connection, wire: &mut [u8], output: &mut [u8]) Result<u64, HandshakeError>
```

Receives and authenticates an application record, or returns zero on authenticated closure.

### `Session::shutdown`

[handshake.crb:53](../stdlib/src/net/tls/handshake.crb#L53)

```rust
fn shutdown(&mut self, socket: &mut Connection, fragment: &mut [u8], wire: &mut [u8]) Result<(), HandshakeError>
```

Sends the authenticated TLS close_notify alert.

### `client_handshake`

[handshake.crb:167](../stdlib/src/net/tls/handshake.crb#L167)

```rust
pub fn client_handshake(socket: &mut Connection, pin: &[u8], peer_key: &PublicKey, wire: &mut [u8], fragment: &mut [u8], message: &mut [u8]) Result<Session, HandshakeError>
```

Runs the client handshake using a configured leaf certificate and public key pin.

### `client_handshake_x509`

[handshake.crb:178](../stdlib/src/net/tls/handshake.crb#L178)

```rust
pub fn client_handshake_x509(socket: &mut Connection, hostname: &[u8], anchor: &[u8], now: i64, wire: &mut [u8], fragment: &mut [u8], message: &mut [u8]) Result<Session, HandshakeError>
```

Runs the client handshake with an explicit trust anchor and DNS identity check.

### `server_handshake`

[handshake.crb:360](../stdlib/src/net/tls/handshake.crb#L360)

```rust
pub fn server_handshake(socket: &mut Connection, certificate: &[u8], signing_key: &SigningKey, wire: &mut [u8], fragment: &mut [u8], message: &mut [u8]) Result<Session, HandshakeError>
```

Runs the server handshake with one DER certificate and its signing key.

### `server_handshake_chain`

[handshake.crb:368](../stdlib/src/net/tls/handshake.crb#L368)

```rust
pub fn server_handshake_chain(socket: &mut Connection, chain: &[u8], signing_key: &SigningKey, wire: &mut [u8], fragment: &mut [u8], message: &mut [u8]) Result<Session, HandshakeError>
```

Runs the server handshake with a framed leaf-first certificate list and its signing key.


Handshake message transport across TCP and TLS record boundaries.

### `HandshakeError`

[transport.crb:5](../stdlib/src/net/tls/transport.crb#L5)

```rust
pub enum HandshakeError
```

Reports TLS handshake framing, negotiation, authentication or I/O failures.

Members:

- [`BufferTooSmall`](../stdlib/src/net/tls/transport.crb#L7) (variant): The caller-provided output buffer cannot hold the result.
- [`Transport`](../stdlib/src/net/tls/transport.crb#L9) (variant): The underlying TCP transport operation failed.
- [`Protocol`](../stdlib/src/net/tls/transport.crb#L11) (variant): The handshake message or negotiation violates the supported TLS profile.
- [`Authentication`](../stdlib/src/net/tls/transport.crb#L13) (variant): The peer's handshake authentication failed.
- [`Crypto`](../stdlib/src/net/tls/transport.crb#L15) (variant): An underlying cryptographic operation failed.


## `std::net::tls::keys`

TLS 1.3 SHA-256 transcript and key schedule for TLS_AES_128_GCM_SHA256.

### `KeyError`

[keys.crb:7](../stdlib/src/net/tls/keys/keys.crb#L7)

```rust
pub enum KeyError
```

Reports an invalid key schedule input, hash failure or output length error.

Members:

- [`InvalidLabel`](../stdlib/src/net/tls/keys/keys.crb#L9) (variant): The TLS HKDF label exceeds its encoded length limit.
- [`InvalidContext`](../stdlib/src/net/tls/keys/keys.crb#L11) (variant): The TLS HKDF context exceeds its encoded length limit.
- [`InvalidSecret`](../stdlib/src/net/tls/keys/keys.crb#L13) (variant): The supplied TLS secret has an invalid size.
- [`OutputTooLong`](../stdlib/src/net/tls/keys/keys.crb#L15) (variant): Requested output exceeds the derivation's algorithmic limit.
- [`HashFailed`](../stdlib/src/net/tls/keys/keys.crb#L17) (variant): The underlying transcript/HMAC operation failed.

### `Traffic`

[keys.crb:21](../stdlib/src/net/tls/keys/keys.crb#L21)

```rust
pub enum Traffic
```

Selects the role and handshake or application phase of a traffic secret.

Members:

- [`ClientHandshake`](../stdlib/src/net/tls/keys/keys.crb#L23) (variant): Selects client handshake traffic secrets.
- [`ServerHandshake`](../stdlib/src/net/tls/keys/keys.crb#L25) (variant): Selects server handshake traffic secrets.
- [`ClientApplication`](../stdlib/src/net/tls/keys/keys.crb#L27) (variant): Selects client application traffic secrets.
- [`ServerApplication`](../stdlib/src/net/tls/keys/keys.crb#L29) (variant): Selects server application traffic secrets.

### `Transcript`

[keys.crb:33](../stdlib/src/net/tls/keys/keys.crb#L33)

```rust
pub struct Transcript
```

Accumulates the ordered handshake bytes in a streaming SHA-256 state.

Members:

- [`hash`](../stdlib/src/net/tls/keys/keys.crb#L35) (implementation field): Streaming handshake transcript hash; record headers are not appended.

### `Transcript::new`

[keys.crb:38](../stdlib/src/net/tls/keys/keys.crb#L38)

```rust
fn new() Transcript
```

Starts an empty handshake transcript.

### `Transcript::append`

[keys.crb:46](../stdlib/src/net/tls/keys/keys.crb#L46)

```rust
fn append(&mut self, message: &[u8]) Result<(), KeyError>
```

Adds handshake bytes in protocol order without record headers.

### `Transcript::digest`

[keys.crb:56](../stdlib/src/net/tls/keys/keys.crb#L56)

```rust
fn digest(&self) [u8; 32]
```

Returns a snapshot of the current transcript hash.

### `hkdf_expand_label`

[keys.crb:78](../stdlib/src/net/tls/keys/keys.crb#L78)

```rust
pub fn hkdf_expand_label(secret: &[u8], label: &[u8], context: &[u8], output: &mut [u8]) Result<(), KeyError>
```

Derives output using the TLS 1.3 label prefix and serialized length and context.

### `early_secret`

[keys.crb:139](../stdlib/src/net/tls/keys/keys.crb#L139)

```rust
pub fn early_secret() Result<[u8; 32], KeyError>
```

Derives the initial TLS early secret without a configured PSK.

### `derive_secret`

[keys.crb:145](../stdlib/src/net/tls/keys/keys.crb#L145)

```rust
pub fn derive_secret(secret: &[u8], label: &[u8], transcript_hash: &[u8]) Result<[u8; 32], KeyError>
```

Derives a 32-byte secret from the given label and transcript hash.

### `derived_secret`

[keys.crb:153](../stdlib/src/net/tls/keys/keys.crb#L153)

```rust
pub fn derived_secret(secret: &[u8]) Result<[u8; 32], KeyError>
```

Derives the intermediate secret used as salt for the next extraction step.

### `handshake_secret`

[keys.crb:165](../stdlib/src/net/tls/keys/keys.crb#L165)

```rust
pub fn handshake_secret(early: &[u8], shared: &[u8]) Result<[u8; 32], KeyError>
```

Mixes the ECDHE shared secret into the key schedule.

### `master_secret`

[keys.crb:176](../stdlib/src/net/tls/keys/keys.crb#L176)

```rust
pub fn master_secret(handshake: &[u8]) Result<[u8; 32], KeyError>
```

Derives the master secret for application traffic and subsequent derivations.

### `traffic_secret`

[keys.crb:187](../stdlib/src/net/tls/keys/keys.crb#L187)

```rust
pub fn traffic_secret(secret: &[u8], transcript_hash: &[u8], traffic: Traffic) Result<[u8; 32], KeyError>
```

Derives the requested client or server traffic secret for the selected phase.

### `aes128_key`

[keys.crb:201](../stdlib/src/net/tls/keys/keys.crb#L201)

```rust
pub fn aes128_key(traffic: &[u8]) Result<[u8; 16], KeyError>
```

Derives the 16-byte record encryption key from a traffic secret.

### `traffic_iv`

[keys.crb:213](../stdlib/src/net/tls/keys/keys.crb#L213)

```rust
pub fn traffic_iv(traffic: &[u8]) Result<[u8; 12], KeyError>
```

Derives the 12-byte static record IV from a traffic secret.

### `finished_key`

[keys.crb:225](../stdlib/src/net/tls/keys/keys.crb#L225)

```rust
pub fn finished_key(handshake_traffic: &[u8]) Result<[u8; 32], KeyError>
```

Derives the key for Finished authentication.

### `finished_verify_data`

[keys.crb:233](../stdlib/src/net/tls/keys/keys.crb#L233)

```rust
pub fn finished_verify_data(handshake_traffic: &[u8], transcript_hash: &[u8]) Result<[u8; 32], KeyError>
```

Computes Finished verify_data over the transcript before Finished.

### `verify_finished`

[keys.crb:247](../stdlib/src/net/tls/keys/keys.crb#L247)

```rust
pub fn verify_finished(handshake_traffic: &[u8], transcript_hash: &[u8], received: &[u8]) Result<bool, KeyError>
```

Checks received verify_data against the expected Finished authentication value.


## `std::net::tls::openssl`

Blocking TLS connection wrapper over the OpenSSL backend.

Available when `target.os == "macos" && target.arch == "aarch64"`.

### `TlsError`

[connection.crb:9](../stdlib/src/net/tls/openssl/connection.crb#L9)

```rust
pub enum TlsError
```

Reports context, handshake, peer verification or TLS I/O failures.

Members:

- [`InvalidInput`](../stdlib/src/net/tls/openssl/connection.crb#L11) (variant): Input does not meet this TLS backend's parameter contract.
- [`ConfigurationFailed`](../stdlib/src/net/tls/openssl/connection.crb#L13) (variant): The TLS backend could not construct its configuration.
- [`PeerVerificationFailed`](../stdlib/src/net/tls/openssl/connection.crb#L15) (variant): The peer certificate/identity verification failed.
- [`HandshakeFailed`](../stdlib/src/net/tls/openssl/connection.crb#L17) (variant): The TLS handshake failed.
- [`TransportFailed`](../stdlib/src/net/tls/openssl/connection.crb#L19) (variant): The TLS backend reported an underlying transport failure.

### `Connection`

[connection.crb:23](../stdlib/src/net/tls/openssl/connection.crb#L23)

```rust
pub struct Connection
```

Owns the TLS session and its underlying TCP connection.

Members:

- [`socket`](../stdlib/src/net/tls/openssl/connection.crb#L25) (implementation field): Owned underlying TCP connection; it outlives the TLS session cleanup.
- [`session`](../stdlib/src/net/tls/openssl/connection.crb#L27) (implementation field): Owned native OpenSSL session address; used only by this optional backend.
- [`failed`](../stdlib/src/net/tls/openssl/connection.crb#L29) (implementation field): Sticky failure state; subsequent operations must follow the API's failure/reset contract.

### `Connection::read`

[connection.crb:32](../stdlib/src/net/tls/openssl/connection.crb#L32)

```rust
fn read(&mut self, destination: &mut [u8]) Result<usize, TlsError>
```

Reads authenticated application data into the caller's slice.

### `Connection::write`

[connection.crb:45](../stdlib/src/net/tls/openssl/connection.crb#L45)

```rust
fn write(&mut self, source: &[u8]) Result<usize, TlsError>
```

Sends application bytes and returns the count accepted by the TLS session.

### `Connection::close`

[connection.crb:59](../stdlib/src/net/tls/openssl/connection.crb#L59)

```rust
fn close(self: Connection) Result<(), TlsError>
```

Consumes the connection and requests a TLS shutdown.

### `Connection::drop`

[connection.crb:66](../stdlib/src/net/tls/openssl/connection.crb#L66)

```rust
fn drop(&mut self)
```

Frees the OpenSSL session before the underlying TCP connection is destroyed.

### `connect`

[connection.crb:73](../stdlib/src/net/tls/openssl/connection.crb#L73)

```rust
pub fn connect(socket: TcpConnection, hostname: &[u8], trust_file: &[u8]) Result<Connection, TlsError>
```

Consumes a connected TCP socket and performs TLS with a NUL-terminated hostname and trust path.

### `accept`

[connection.crb:96](../stdlib/src/net/tls/openssl/connection.crb#L96)

```rust
pub fn accept(socket: TcpConnection, certificate: &[u8], private_key: &[u8]) Result<Connection, TlsError>
```

Consumes a connected TCP socket and performs TLS with NUL-terminated certificate and key paths.


## `std::net::tls::record`

TLS 1.3 record framing, authenticated encryption and blocking TCP transport.

### `HANDSHAKE`

[record.crb:7](../stdlib/src/net/tls/record/record.crb#L7)

```rust
pub const HANDSHAKE: u8 = 22
```

TLS handshake content type.

### `APPLICATION_DATA`

[record.crb:9](../stdlib/src/net/tls/record/record.crb#L9)

```rust
pub const APPLICATION_DATA: u8 = 23
```

TLS application data content type.

### `ALERT`

[record.crb:11](../stdlib/src/net/tls/record/record.crb#L11)

```rust
pub const ALERT: u8 = 21
```

TLS alert content type.

### `CHANGE_CIPHER_SPEC`

[record.crb:13](../stdlib/src/net/tls/record/record.crb#L13)

```rust
pub const CHANGE_CIPHER_SPEC: u8 = 20
```

TLS compatibility ChangeCipherSpec content type.

### `Error`

[record.crb:33](../stdlib/src/net/tls/record/record.crb#L33)

```rust
pub enum Error
```

Reports TLS framing, size, authentication, cipher state or transport failures.

Members:

- [`BufferTooSmall`](../stdlib/src/net/tls/record/record.crb#L35) (variant): The caller-provided output buffer cannot hold the result.
- [`RecordOverflow`](../stdlib/src/net/tls/record/record.crb#L37) (variant): The record exceeds the supported TLS size limit.
- [`InvalidRecord`](../stdlib/src/net/tls/record/record.crb#L39) (variant): The TLS record encoding or content type is invalid.
- [`AuthenticationFailed`](../stdlib/src/net/tls/record/record.crb#L41) (variant): Authentication failed; the operation must not expose unauthenticated plaintext.
- [`WrongDirection`](../stdlib/src/net/tls/record/record.crb#L43) (variant): The cipher was used for the opposite traffic direction.
- [`KeyLimit`](../stdlib/src/net/tls/record/record.crb#L45) (variant): The traffic key's record sequence limit has been reached.
- [`Closed`](../stdlib/src/net/tls/record/record.crb#L47) (variant): This traffic direction is already closed.
- [`Failed`](../stdlib/src/net/tls/record/record.crb#L49) (variant): The cipher is in a sticky failed state.
- [`Transport`](../stdlib/src/net/tls/record/record.crb#L51) (variant): The underlying TCP transport operation failed.
- [`Truncated`](../stdlib/src/net/tls/record/record.crb#L53) (variant): The transport closed before the complete record arrived.

### `Record`

[record.crb:57](../stdlib/src/net/tls/record/record.crb#L57)

```rust
pub struct Record
```

Describes authenticated content and closure status after opening a record.

Members:

- [`content_type`](../stdlib/src/net/tls/record/record.crb#L59) (implementation field): Authenticated inner TLS content type.
- [`length`](../stdlib/src/net/tls/record/record.crb#L61) (implementation field): Number of authenticated plaintext bytes.
- [`closing`](../stdlib/src/net/tls/record/record.crb#L63) (implementation field): Whether this record contains authenticated close_notify.

### `Record::kind`

[record.crb:66](../stdlib/src/net/tls/record/record.crb#L66)

```rust
fn kind(&self) u8
```

Returns the authenticated inner content type.

### `Record::len`

[record.crb:68](../stdlib/src/net/tls/record/record.crb#L68)

```rust
fn len(&self) u64
```

Returns the number of content bytes in the plaintext buffer.

### `Record::is_close_notify`

[record.crb:70](../stdlib/src/net/tls/record/record.crb#L70)

```rust
fn is_close_notify(&self) bool
```

Reports whether the authenticated record closes the receive direction.

### `RecordCipher`

[record.crb:75](../stdlib/src/net/tls/record/record.crb#L75)

```rust
pub struct RecordCipher
```

Holds the key, IV, sequence and state for one record direction.

Members:

- [`aes`](../stdlib/src/net/tls/record/record.crb#L77) (implementation field): Owned AES-GCM key schedule for this traffic direction.
- [`iv`](../stdlib/src/net/tls/record/record.crb#L79) (implementation field): Per-direction IV used with the record sequence number.
- [`sequence`](../stdlib/src/net/tls/record/record.crb#L81) (implementation field): Next record sequence number; key limits are checked before further use.
- [`sending`](../stdlib/src/net/tls/record/record.crb#L83) (implementation field): True for a writer, false for a reader; direction-specific operations validate it.
- [`status`](../stdlib/src/net/tls/record/record.crb#L85) (implementation field): Internal cipher state encoding active, closed or failed operation.

### `RecordCipher::writer`

[record.crb:88](../stdlib/src/net/tls/record/record.crb#L88)

```rust
fn writer(key: &[u8; 16], iv: &[u8; 12]) RecordCipher
```

Creates an outbound record cipher from a traffic key and static IV.

### `RecordCipher::reader`

[record.crb:90](../stdlib/src/net/tls/record/record.crb#L90)

```rust
fn reader(key: &[u8; 16], iv: &[u8; 12]) RecordCipher
```

Creates an inbound record cipher from a traffic key and static IV.

### `RecordCipher::seal`

[record.crb:94](../stdlib/src/net/tls/record/record.crb#L94)

```rust
fn seal(&mut self, kind: u8, content: &[u8], padding: usize, scratch: &mut [u8], wire: &mut [u8]) Result<usize, Error>
```

Encrypts one TLS record into caller-owned wire storage with optional padding.

### `RecordCipher::open`

[record.crb:131](../stdlib/src/net/tls/record/record.crb#L131)

```rust
fn open(&mut self, wire: &[u8], plaintext: &mut [u8]) Result<Record, Error>
```

Authenticates and decrypts a complete TLS record into caller-owned storage.

### `RecordCipher::seal_close_notify`

[record.crb:181](../stdlib/src/net/tls/record/record.crb#L181)

```rust
fn seal_close_notify(&mut self, scratch: &mut [u8], wire: &mut [u8]) Result<usize, Error>
```

Builds a protected close_notify record and closes the write direction.

Available when `target.os == "linux" && target.arch == "x86_64" && target.pointer_width == "64" || target.os == "macos" && target.arch == "aarch64" || target.os == "macos" && target.arch == "x86_64" || target.os == "windows" && target.arch == "aarch64" || target.os == "windows" && target.arch == "x86_64"`.

### `RecordCipher::send_record`

[record.crb:190](../stdlib/src/net/tls/record/record.crb#L190)

```rust
fn send_record(&mut self, socket: &mut Connection, kind: u8, content: &[u8], padding: usize, scratch: &mut [u8], wire: &mut [u8]) Result<(), Error>
```

Protects and sends one record using the caller's wire and scratch buffers.

### `RecordCipher::receive_record`

[record.crb:207](../stdlib/src/net/tls/record/record.crb#L207)

```rust
fn receive_record(&mut self, socket: &mut Connection, wire: &mut [u8], plaintext: &mut [u8]) Result<Record, Error>
```

Reads and authenticates one TLS record using caller-owned buffers.

### `RecordCipher::close_notify`

[record.crb:226](../stdlib/src/net/tls/record/record.crb#L226)

```rust
fn close_notify(&mut self, socket: &mut Connection, scratch: &mut [u8], wire: &mut [u8]) Result<(), Error>
```

Sends a protected closure alert over TCP and marks the write direction closed.

### `encode_plaintext`

[record.crb:337](../stdlib/src/net/tls/record/record.crb#L337)

```rust
pub fn encode_plaintext(kind: u8, initial_client_hello: bool, content: &[u8], wire: &mut [u8]) Result<usize, Error>
```

Writes a cleartext TLS record for a supported handshake message.

### `decode_plaintext`

[record.crb:353](../stdlib/src/net/tls/record/record.crb#L353)

```rust
pub fn decode_plaintext(wire: &[u8]) Result<Record, Error>
```

Validates the supplied cleartext record and returns its metadata.

Available when `target.os == "linux" && target.arch == "x86_64" && target.pointer_width == "64" || target.os == "macos" && target.arch == "aarch64" || target.os == "macos" && target.arch == "x86_64" || target.os == "windows" && target.arch == "aarch64" || target.os == "windows" && target.arch == "x86_64"`.

### `read_record`

[record.crb:392](../stdlib/src/net/tls/record/record.crb#L392)

```rust
pub fn read_record(socket: &mut Connection, wire: &mut [u8]) Result<usize, Error>
```

Reads one full framed record, handling partial TCP reads.

### `write_record`

[record.crb:410](../stdlib/src/net/tls/record/record.crb#L410)

```rust
pub fn write_record(socket: &mut Connection, wire: &[u8]) Result<(), Error>
```

Writes all record bytes, handling short TCP writes.


## `std::net::udp`

Blocking IPv4 UDP sockets for connected or addressed datagram I/O.

Available when `target.os == "linux" && target.arch == "x86_64" && target.pointer_width == "64" || target.os == "macos" && target.arch == "aarch64" || target.os == "macos" && target.arch == "x86_64" || target.os == "windows" && target.arch == "aarch64" || target.os == "windows" && target.arch == "x86_64"`.

### `Connection`

[socket.crb:10](../stdlib/src/net/udp/socket.crb#L10)

```rust
pub struct Connection
```

Owns a UDP socket associated with one remote endpoint.

Members:

- [`__din_package_socket`](../stdlib/src/net/udp/socket.crb#L12) (implementation field): Owned native socket storage; the connection/listener closes it on destruction.
- [`local_address`](../stdlib/src/net/udp/socket.crb#L14) (implementation field): Cached local IPv4 endpoint, including any OS-assigned port.
- [`remote_address`](../stdlib/src/net/udp/socket.crb#L16) (implementation field): Cached remote IPv4 endpoint.

### `Connection::addr`

[socket.crb:19](../stdlib/src/net/udp/socket.crb#L19)

```rust
fn addr(&self) SocketAddr
```

Returns the local IPv4 address and port, including a port assigned by the OS.

### `Connection::peer`

[socket.crb:25](../stdlib/src/net/udp/socket.crb#L25)

```rust
fn peer(&self) SocketAddr
```

Returns the remote IPv4 address and port associated with the connection.

### `Connection::send`

[socket.crb:31](../stdlib/src/net/udp/socket.crb#L31)

```rust
fn send(&mut self, buffer: &[u8]) Result<usize, SocketError>
```

Sends a complete datagram to the connected peer, including an empty datagram.

### `Connection::recv`

[socket.crb:38](../stdlib/src/net/udp/socket.crb#L38)

```rust
fn recv(&mut self, buffer: &mut [u8]) Result<usize, SocketError>
```

Receives one datagram from the connected peer. An oversized payload is consumed and reported.

### `Listener`

[socket.crb:50](../stdlib/src/net/udp/socket.crb#L50)

```rust
pub struct Listener
```

Owns a bound UDP socket that can receive from and send to arbitrary endpoints.

Members:

- [`__din_package_socket`](../stdlib/src/net/udp/socket.crb#L52) (implementation field): Owned native socket storage; the connection/listener closes it on destruction.
- [`local_address`](../stdlib/src/net/udp/socket.crb#L54) (implementation field): Cached local IPv4 endpoint, including any OS-assigned port.

### `Listener::bind`

[socket.crb:57](../stdlib/src/net/udp/socket.crb#L57)

```rust
fn bind(address: SocketAddr) Result<Listener, SocketError>
```

Binds a UDP socket to the supplied local endpoint. Use port zero for an assigned port.

### `Listener::addr`

[socket.crb:70](../stdlib/src/net/udp/socket.crb#L70)

```rust
fn addr(&self) SocketAddr
```

Returns the local IPv4 address and port, including a port assigned by the OS.

### `Listener::recv`

[socket.crb:76](../stdlib/src/net/udp/socket.crb#L76)

```rust
fn recv(&mut self, buffer: &mut [u8]) Result<Datagram, SocketError>
```

Receives one datagram with sender metadata. An oversized payload is consumed and reported.

### `Listener::send`

[socket.crb:82](../stdlib/src/net/udp/socket.crb#L82)

```rust
fn send(&mut self, buffer: &[u8], destination: SocketAddr) Result<usize, SocketError>
```

Sends a complete datagram to the supplied destination, including an empty datagram.

### `connect`

[socket.crb:90](../stdlib/src/net/udp/socket.crb#L90)

```rust
pub fn connect(address: SocketAddr) Result<Connection, SocketError>
```

Associates a UDP socket with the specified peer without a transport handshake.


## `std::num`

Minimum selection for signed 64-bit integers.

### `min_i64`

[min.crb:5](../stdlib/src/num/min.crb#L5)

```rust
pub fn min_i64(left: i64, right: i64) i64
```

Returns the smaller of two signed 64-bit values.


## `std::sync`

Blocking mutexes with native-thread-bound guards.

### `Mutex`

[mutex.crb:6](../stdlib/src/sync/mutex.crb#L6)

```rust
pub struct Mutex<T>
```

Owns a value and a stable native synchronization resource.

Members:

- [`raw`](../stdlib/src/sync/mutex.crb#L8) (implementation field): Native synchronization handle; never copied as a native mutex object.
- [`value`](../stdlib/src/sync/mutex.crb#L10) (implementation field): Owned payload cleaned after the mutex's own destructor.

### `Mutex::new`

[mutex.crb:13](../stdlib/src/sync/mutex.crb#L13)

```rust
fn new(value: T) Mutex<T>
```

Takes ownership of the payload and constructs its synchronization resource.

### `Mutex::lock`

[mutex.crb:19](../stdlib/src/sync/mutex.crb#L19)

```rust
fn lock(&self) MutexGuard<T>
```

Blocks this thread until it acquires the native mutex.

### `Mutex::drop`

[mutex.crb:28](../stdlib/src/sync/mutex.crb#L28)

```rust
fn drop(&mut self)
```

Destroys unlocked native state; checked borrows keep active guards/waiters alive.

### `MutexGuard`

[mutex.crb:34](../stdlib/src/sync/mutex.crb#L34)

```rust
pub struct MutexGuard<T>
```

Holds the lock until destruction and borrows its owner's payload.

Members:

- [`raw`](../stdlib/src/sync/mutex.crb#L36) (implementation field): Borrowed native resource identity; the payload borrow retains its owner.
- [`data`](../stdlib/src/sync/mutex.crb#L38) (implementation field): Mutable payload access under the retained lock contract.

### `MutexGuard::ref`

[mutex.crb:41](../stdlib/src/sync/mutex.crb#L41)

```rust
fn ref(&self) &T
```

Borrows the protected value for reading.

### `MutexGuard::mut_ref`

[mutex.crb:43](../stdlib/src/sync/mutex.crb#L43)

```rust
fn mut_ref(&mut self) &mut T
```

Reborrows the protected value with mutation permission.

### `MutexGuard::drop`

[mutex.crb:45](../stdlib/src/sync/mutex.crb#L45)

```rust
fn drop(&mut self)
```

Releases ownership before the guard's reference fields are discarded.


## `std::sync::asyn`

Task-owned FIFO mutexes; waiting parks a task and guards may cross workers.

### `Mutex`

[mutex.crb:6](../stdlib/src/sync/asyn/mutex.crb#L6)

```rust
pub struct Mutex<T>
```

Owns a value and a stable native synchronization resource.

Members:

- [`raw`](../stdlib/src/sync/asyn/mutex.crb#L8) (implementation field): Native synchronization handle; never copied as a native mutex object.
- [`value`](../stdlib/src/sync/asyn/mutex.crb#L10) (implementation field): Owned payload cleaned after the mutex's own destructor.

### `Mutex::new`

[mutex.crb:13](../stdlib/src/sync/asyn/mutex.crb#L13)

```rust
fn new(value: T) Mutex<T>
```

Takes ownership of the payload and constructs its synchronization resource.

### `Mutex::lock`

[mutex.crb:19](../stdlib/src/sync/asyn/mutex.crb#L19)

```rust
async fn lock(&self) MutexGuard<T>
```

Suspends until logical ownership is handed to this task.

### `Mutex::drop`

[mutex.crb:28](../stdlib/src/sync/asyn/mutex.crb#L28)

```rust
fn drop(&mut self)
```

Destroys unlocked native state; checked borrows keep active guards/waiters alive.

### `MutexGuard`

[mutex.crb:34](../stdlib/src/sync/asyn/mutex.crb#L34)

```rust
pub struct MutexGuard<T>
```

Holds the lock until destruction and borrows its owner's payload.

Members:

- [`raw`](../stdlib/src/sync/asyn/mutex.crb#L36) (implementation field): Borrowed native resource identity; the payload borrow retains its owner.
- [`data`](../stdlib/src/sync/asyn/mutex.crb#L38) (implementation field): Mutable payload access under the retained lock contract.

### `MutexGuard::ref`

[mutex.crb:41](../stdlib/src/sync/asyn/mutex.crb#L41)

```rust
fn ref(&self) &T
```

Borrows the protected value for reading.

### `MutexGuard::mut_ref`

[mutex.crb:43](../stdlib/src/sync/asyn/mutex.crb#L43)

```rust
fn mut_ref(&mut self) &mut T
```

Reborrows the protected value with mutation permission.

### `MutexGuard::drop`

[mutex.crb:45](../stdlib/src/sync/asyn/mutex.crb#L45)

```rust
fn drop(&mut self)
```

Releases ownership before the guard's reference fields are discarded.


## `std::sync::asyn::channel`

Bounded FIFO channels. Queue values are owned until received or destroyed.

### `SendError`

[channel.crb:6](../stdlib/src/sync/asyn/channel/channel.crb#L6)

```rust
pub enum SendError<T>
```

A failed send returns ownership of the original value.

Members:

- [`Closed`](../stdlib/src/sync/asyn/channel/channel.crb#L8) (variant): The channel was closed before the value could enter its queue.
- [`Closed.value`](../stdlib/src/sync/asyn/channel/channel.crb#L10) (implementation field): Value whose ownership was not transferred into the queue.

### `Channel`

[channel.crb:16](../stdlib/src/sync/asyn/channel/channel.crb#L16)

```rust
pub struct Channel<T>
```

Owns a fixed-capacity queue; borrowed users must end before destruction.

Members:

- [`raw`](../stdlib/src/sync/asyn/channel/channel.crb#L18) (implementation field): Stable native metadata and managed ring-storage identity.

### `Channel::new`

[channel.crb:21](../stdlib/src/sync/asyn/channel/channel.crb#L21)

```rust
fn new(capacity: usize) Channel<T>
```

Reserves a nonzero maximum number of queued values; the queue never grows beyond it.

### `Channel::send`

[channel.crb:30](../stdlib/src/sync/asyn/channel/channel.crb#L30)

```rust
async fn send(&self, value: T) Result<(), SendError<T>>
```

Moves a value into the queue; a closed channel returns the unsent value.

### `Channel::recv`

[channel.crb:48](../stdlib/src/sync/asyn/channel/channel.crb#L48)

```rust
async fn recv(&self) Option<T>
```

Receives in FIFO order; closed queues drain before returning None.

### `Channel::close`

[channel.crb:62](../stdlib/src/sync/asyn/channel/channel.crb#L62)

```rust
fn close(&self)
```

Prevents future sends and wakes waiting producers and consumers.

### `Channel::drop`

[channel.crb:68](../stdlib/src/sync/asyn/channel/channel.crb#L68)

```rust
fn drop(&mut self)
```

Closes, destroys each queued value once, then releases bounded storage.


## `std::sync::channel`

Bounded FIFO channels. Queue values are owned until received or destroyed.

### `SendError`

[channel.crb:6](../stdlib/src/sync/channel/channel.crb#L6)

```rust
pub enum SendError<T>
```

A failed send returns ownership of the original value.

Members:

- [`Closed`](../stdlib/src/sync/channel/channel.crb#L8) (variant): The channel was closed before the value could enter its queue.
- [`Closed.value`](../stdlib/src/sync/channel/channel.crb#L10) (implementation field): Value whose ownership was not transferred into the queue.

### `Channel`

[channel.crb:16](../stdlib/src/sync/channel/channel.crb#L16)

```rust
pub struct Channel<T>
```

Owns a fixed-capacity queue; borrowed users must end before destruction.

Members:

- [`raw`](../stdlib/src/sync/channel/channel.crb#L18) (implementation field): Stable native metadata and managed ring-storage identity.

### `Channel::new`

[channel.crb:21](../stdlib/src/sync/channel/channel.crb#L21)

```rust
fn new(capacity: usize) Channel<T>
```

Reserves a nonzero maximum number of queued values; the queue never grows beyond it.

### `Channel::send`

[channel.crb:30](../stdlib/src/sync/channel/channel.crb#L30)

```rust
fn send(&self, value: T) Result<(), SendError<T>>
```

Moves a value into the queue; a closed channel returns the unsent value.

### `Channel::recv`

[channel.crb:45](../stdlib/src/sync/channel/channel.crb#L45)

```rust
fn recv(&self) Option<T>
```

Receives in FIFO order; closed queues drain before returning None.

### `Channel::close`

[channel.crb:56](../stdlib/src/sync/channel/channel.crb#L56)

```rust
fn close(&self)
```

Prevents future sends and wakes waiting producers and consumers.

### `Channel::drop`

[channel.crb:62](../stdlib/src/sync/channel/channel.crb#L62)

```rust
fn drop(&mut self)
```

Closes, destroys each queued value once, then releases bounded storage.


## `std::text`

Allocation-free splitting of UTF-8 text into borrowed views.

### `Split`

[split.crb:6](../stdlib/src/text/split.crb#L6)

```rust
pub struct Split
```

A forward iterator over non-overlapping literal separator matches.
Pieces borrow the original text; no piece owns or copies its bytes.

Members:

- [`text`](../stdlib/src/text/split.crb#L8) (implementation field): Original UTF-8 storage, retained independently of the iterator cursor.
- [`separator`](../stdlib/src/text/split.crb#L10) (implementation field): Literal separator; its storage must remain valid while matching continues.
- [`position`](../stdlib/src/text/split.crb#L12) (implementation field): Byte offset of the next unconsumed piece.
- [`finished`](../stdlib/src/text/split.crb#L14) (implementation field): Records exhaustion, including the final empty piece after a trailing match.
- [`empty_started`](../stdlib/src/text/split.crb#L16) (implementation field): Records whether an empty separator has yielded its leading empty piece.

### `Split::next`

[split.crb:20](../stdlib/src/text/split.crb#L20)

```rust
fn next(&mut self) Option<&str>
```

Returns the next UTF-8 view, or None after exhaustion.
Returned pieces depend on the original text, independently of this cursor.

### `split`

[split.crb:73](../stdlib/src/text/split.crb#L73)

```rust
pub fn split(text: &str, separator: &str) Split
```

Borrows text and its separator and constructs a fixed-size iterator descriptor.
Empty pieces are preserved. An empty separator splits at Unicode scalar boundaries.


Error type for checked, zero-copy byte-to-text conversion.

### `Utf8Error`

[utf8.crb:5](../stdlib/src/text/utf8.crb#L5)

```rust
pub enum Utf8Error
```

Reports invalid UTF-8 without replacing or copying input bytes.

Members:

- [`InvalidEncoding`](../stdlib/src/text/utf8.crb#L7) (variant): Input contains an invalid, overlong, surrogate or incomplete sequence.


## `std::time`

Monotonic durations, instants and deadline waits; no wall-clock/calendar semantics.

### `Error`

[time.crb:6](../stdlib/src/time/time.crb#L6)

```rust
pub enum Error
```

Reports clock, sleep or asynchronous worker-launch failure.

Members:

- [`ClockFailure`](../stdlib/src/time/time.crb#L8) (variant): The system monotonic clock could not be read.
- [`WaitFailure`](../stdlib/src/time/time.crb#L10) (variant): The system sleep call failed for a reason other than interruption.
- [`LaunchFailed`](../stdlib/src/time/time.crb#L12) (variant): The asynchronous runtime could not start the blocking worker.

### `Duration`

[time.crb:16](../stdlib/src/time/time.crb#L16)

```rust
pub struct Duration
```

A nonnegative span with nanosecond units and checked arithmetic.

Members:

- [`nanos`](../stdlib/src/time/time.crb#L18) (implementation field): Span in nanoseconds; private so constructors define the representation.

### `Duration::from_nanos`

[time.crb:21](../stdlib/src/time/time.crb#L21)

```rust
fn from_nanos(nanos: u64) Duration
```

Constructs a span from nanoseconds.

### `Duration::from_millis`

[time.crb:23](../stdlib/src/time/time.crb#L23)

```rust
fn from_millis(millis: u64) Duration
```

Constructs a span from milliseconds; integer overflow follows checked arithmetic.

### `Duration::from_secs`

[time.crb:25](../stdlib/src/time/time.crb#L25)

```rust
fn from_secs(seconds: u64) Duration
```

Constructs a span from seconds; integer overflow follows checked arithmetic.

### `Duration::as_nanos`

[time.crb:27](../stdlib/src/time/time.crb#L27)

```rust
fn as_nanos(&self) u64
```

Returns the span in nanoseconds without changing it.

### `Instant`

[time.crb:31](../stdlib/src/time/time.crb#L31)

```rust
pub struct Instant
```

An opaque monotonic timestamp; not a date or portable serialized timestamp.

Members:

- [`ticks`](../stdlib/src/time/time.crb#L33) (implementation field): Platform clock expressed in nanoseconds; clock resolution remains platform-specific.

### `Instant::now`

[time.crb:36](../stdlib/src/time/time.crb#L36)

```rust
fn now() Result<Instant, Error>
```

Reads the current monotonic timestamp.

### `Instant::after`

[time.crb:42](../stdlib/src/time/time.crb#L42)

```rust
fn after(&self, duration: Duration) Instant
```

Returns an instant after this one; addition uses checked integer arithmetic.

### `Instant::elapsed`

[time.crb:46](../stdlib/src/time/time.crb#L46)

```rust
fn elapsed(&self) Result<Duration, Error>
```

Measures time since this instant, saturating a backward platform reading at zero.

### `Instant::remaining`

[time.crb:53](../stdlib/src/time/time.crb#L53)

```rust
fn remaining(&self) Result<Duration, Error>
```

Measures the remaining span until this instant, saturating past deadlines at zero.

### `Timer`

[time.crb:66](../stdlib/src/time/time.crb#L66)

```rust
pub struct Timer
```

A reusable monotonic deadline; waiting does not consume it.

Members:

- [`deadline`](../stdlib/src/time/time.crb#L68) (implementation field): Absolute monotonic timestamp of the deadline.

### `Timer::after`

[time.crb:71](../stdlib/src/time/time.crb#L71)

```rust
fn after(duration: Duration) Result<Timer, Error>
```

Creates a timer that becomes ready after the given span.

### `Timer::at`

[time.crb:77](../stdlib/src/time/time.crb#L77)

```rust
fn at(deadline: Instant) Timer
```

Creates a timer for an existing monotonic deadline.

### `Timer::wait`

[time.crb:79](../stdlib/src/time/time.crb#L79)

```rust
fn wait(&self) Result<(), Error>
```

Blocks this thread until the deadline, retrying interruptions and early wakes.

### `sleep`

[time.crb:93](../stdlib/src/time/time.crb#L93)

```rust
pub fn sleep(duration: Duration) Result<(), Error>
```

Blocks the current thread for at least the given monotonic span.


## `std::time::asyn`

Async deadline waits using shared monotonic values.

### `sleep`

[asyn.crb:13](../stdlib/src/time/asyn/asyn.crb#L13)

```rust
pub async fn sleep(duration: Duration) Result<(), Error>
```

Suspends this task for a span without blocking an executor thread.

### `Timer`

[asyn.crb:22](../stdlib/src/time/asyn/asyn.crb#L22)

```rust
pub struct Timer
```

Owns a reusable deadline whose waits suspend the calling task.

Members:

- [`inner`](../stdlib/src/time/asyn/asyn.crb#L24) (implementation field): Shared deadline state borrowed until the worker wait completes.

### `Timer::after`

[asyn.crb:27](../stdlib/src/time/asyn/asyn.crb#L27)

```rust
fn after(duration: Duration) Result<Timer, Error>
```

Creates an asynchronous timer after the supplied span.

### `Timer::at`

[asyn.crb:32](../stdlib/src/time/asyn/asyn.crb#L32)

```rust
fn at(deadline: Instant) Timer
```

Creates an asynchronous timer at an existing monotonic instant.

### `Timer::wait`

[asyn.crb:37](../stdlib/src/time/asyn/asyn.crb#L37)

```rust
async fn wait(&self) Result<(), Error>
```

Suspends until the deadline; the timer outlives its borrowed worker wait.
