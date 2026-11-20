# HTTP parsing building blocks

Status: synchronous parsing implemented in the STD and validated with corboc on
macOS ARM64. Async HTTP and serialization remain separate API work.

## Package boundary

`std::net::http` provides HTTP/1.1 parsing and serialization building blocks.
Server acceptance, scheduling, routing and application policy belong in a
separate implementation package. An echo server is the intended first consumer;
this document specifies parsing, not that server or final serialization APIs.

These parser functions are synchronous computations over their reader contract.
An async-reader adapter is not implemented or implied by the async-default
transport convention. A future async parser API needs its own explicit contract;
no trait or implicit sync/async dispatch is introduced.

## Reader contract and parsing functions

The synchronous API uses the existing static structural read contract:

```rust
#(type: E)
#(type: R<E> with {
    fn read(&mut self, buffer: &mut [u8]) -> Result<usize, E>;
})
pub fn request(reader: &mut R) -> Result<Option<Request<R, E>>, ParseError<E>>;

#(type: E)
#(type: R<E> with {
    fn read(&mut self, buffer: &mut [u8]) -> Result<usize, E>;
})
pub fn response(reader: &mut R) -> Result<Option<Response<R, E>>, ParseError<E>>;
```

These signatures are implemented in `stdlib/src/net/http/http.crb`.
`Ok(Some(message))` denotes a complete parsed head. `Ok(None)` denotes EOF before
any message bytes arrive. Incomplete input after a message has begun is an error.
Other error categories include malformed syntax, exceeded bounds, storage
exhaustion and underlying reader errors. The reader's error type E is preserved by `ParseError.Read`; syntax, framing,
EOF and budget failures have distinct variants in the generated API reference.

There is no caller-supplied header-storage slice or runtime Limits argument.
Each returned message owns bounded head storage allocated through Corbo's
existing datastack/region model. Locations can be represented by offsets into
that storage; accessors borrow views when used. Its body reader borrows R, so
normal dependency and cleanup obligations connect the message to the reader.

Request exposes method, target, version and headers. Response exposes version,
status and headers. Repeated headers are preserved. Header values are byte views;
targets are not automatically URL-decoded. `Headers::len()` counts fields; `get(index)` returns an optional borrowed
`Header`, whose `name()` is `&str` and `value()` is `&[u8]`.

## Configurable parsing budgets

The HTTP package declares these public constants, each marked configurable:

```rust
#(configurable)
pub const REQUEST_LINE_MAX_SIZE: usize = 8192;

#(configurable)
pub const HEADER_LINE_MAX_SIZE: usize = 8192;

#(configurable)
pub const HEADERS_MAX_SIZE: usize = 32768;

#(configurable)
pub const HEADER_COUNT_MAX: usize = 100;
```

Sizes count bytes. Individual line limits exclude their terminating CRLF.
The total header budget includes header-line terminators and the final empty
line, excluding the request line. The header count counts fields, including
repeated fields. These independent bounds are enforced while parsing, before
writing outside bounded storage; there is no unbounded fallback allocation.
A compile-time override changes the specialization, not a runtime argument.
The status line currently shares `REQUEST_LINE_MAX_SIZE`. A separate body-budget
API is not introduced: framed bytes are streamed into caller-provided slices.

## Optional streaming bodies and caller responsibilities

Parsing stops after the empty line terminating the head (`\r\n\r\n`).
Constructing or dropping a body reader performs no reads. The optional body
accessor has the proposed shape `body() -> Option<&mut BodyReader<R, E>>`.

A Content-Length declaration supplies a length-bounded body reader; zero yields
an immediately empty reader. Chunked framing supplies a reader that decodes
chunks through its terminator. Bodies are streamed rather than automatically
collected. Reading uses caller-provided output slices. Body readers must not
expose subsequent-message bytes as part of the declared framed body.

Body presence is a header-based indication, not a guarantee that bytes follow.
`response()` receives no originating request context. In particular, a HEAD
response can carry Content-Length without transmitting a body. The caller knows
the request method and must avoid reading that indicated body. Request-dependent
semantics therefore belong to the caller, not an inference promised by this API.
[HTTP/1.1 message-body length](https://www.rfc-editor.org/rfc/rfc9112.html#section-6.3)
defines the framing exceptions; this low-level API must not be described as
fully resolving them without that context. Close-delimited bodies and protocol
handoff details remain a subsequent API step.

The parser must preserve the logical reader position immediately after the
head. If it uses an injected buffered reader, prefetched bytes remain in that
reader and all subsequent reads continue through it. Dropping an unread body
does not drain it or synchronize the connection for another message. The caller
must explicitly finish consuming/discarding the body or close the connection.
No stream resynchronization is promised after a parsing error.

## Complete scoped example

This in-memory reader example is executed by the focused suite; a TCP connection
or another object satisfying the same `read` contract can be injected instead.
It prints method/target byte lengths, body read counts and the final input cursor.
The following `NEXT` bytes remain unread.

```rust
use std::net::http;

struct Input { bytes: [u8; 4096], length: usize, position: usize }
impl Input {
    fn new(text: &str) -> Input {
        let bytes = text.as_bytes();
        let mut input = Input { bytes: [0; 4096], length: bytes.len(), position: 0 };
        let output = &mut input.bytes[..];
        let mut i: usize = 0;
        while i < bytes.len() { output[i] = bytes[i]; i += 1; }
        input
    }

    fn read(&mut self, output: &mut [u8]) -> Result<usize, i32> {
        let bytes = &(*self).bytes[..];
        let at = (*self).position;
        let available = (*self).length - at;
        let capacity = output.len();
        let count: usize = if available < capacity { available } else { capacity };
        let mut i: usize = 0;
        while i < count { output[i] = bytes[at + i]; i += 1; }
        let position = &mut (*self).position;
        *position = at + count;
        Ok(count)
    }
}

fn main() {
    let text = "POST /hello HTTP/1.1\r\nHost: example.com\r\nContent-Length: 5\r\n\r\nhelloNEXT";
    let mut input = Input::new(text);
    #(override:
        std::net::http::REQUEST_LINE_MAX_SIZE = 128,
        std::net::http::HEADER_LINE_MAX_SIZE = 128,
        std::net::http::HEADERS_MAX_SIZE = 512,
        std::net::http::HEADER_COUNT_MAX = 8
    ) {
        let parsed = match http::request(&mut input) {
            Ok(parsed) => { parsed },
            Err(error) => { drop(error); return; },
        };
        let mut request = match parsed {
            Some(request) => { request },
            None => { return; },
        };
        let method=request.method(); let method_bytes=method.as_bytes(); print(method_bytes.len());
        let target=request.target(); let target_bytes=target.as_bytes(); print(target_bytes.len());
        let mut body = match request.body() { Some(body) => { body }, None => { return; }, };
        let mut bytes: [u8; 8] = [0; 8];
        match body.read(&mut bytes[..]) {
            Ok(count) => { print(count); },
            Err(error) => { drop(error); return; },
        }
        print(bytes[0]);
        match body.read(&mut bytes[..]) { Ok(count) => { print(count); }, Err(error) => { drop(error); }, }
    }
    print(input.position);
}
```

[Implementation validation and remaining limits](cycles/HTTP_CONFIGURATION_IMPLEMENTATION_CYCLE.md).
For inherited values, nested overrides and escaped objects, see
[configurable package constants](CONFIGURATION_CONSTANTS.md).
