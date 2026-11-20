[Français](ASYNC_API-fr.md)

# Async-default I/O and explicit blocking APIs

This is an API/STD organization convention. It changes no grammar, capture,
move, borrowing or cleanup rule. `main` remains synchronous. Calling an async
operation creates its existing Future; `.await` remains explicit in async code.

| API | Async default | Explicit blocking |
| --- | --- | --- |
| Files | `std::io::File` | `std::io::sync::File` |
| Buffered streams | `std::io::buffered::{BufReader, BufWriter}` | `std::io::sync::buffered::{BufReader, BufWriter}` |
| TCP | `std::net::tcp` | `std::net::sync::tcp` |
| UDP | `std::net::udp` | `std::net::sync::udp` |
| Sleep and Timer | `std::time::{sleep, Timer}` | `std::time::sync::{sleep, Timer}` |
| Existing TLS transport | Not implemented | `std::net::sync::tls` |

Shared declarations remain independent of the wait strategy:

- `std::io::{FileMode, FilePerm, FileStats, SeekFrom}`.
- `std::net::{SocketError, Datagram}` and `std::net::ipv4::{Addr, SocketAddr}`.
- `std::time::{Duration, Instant, Error}`.

Each File/buffered variant keeps its own error wrapper where worker launch
failure or the stream contract requires it. The options/metadata types are
shared, not separately defined lookalikes. `Instant::remaining()` returns a
nonnegative span until a monotonic deadline; blocking Timer uses this query
rather than accessing another module's private fields.

Async files and timers delegate native waiting to existing blocking workers.
Async sockets retain their epoll/kqueue/IOCP implementation. Synchronous setup
and in-memory accessors keep their established signatures: bind, UDP connect,
addr/peer and timer construction do not become async merely because they are
members of a default async package.

There is no implicit conversion between sync and async calls. Parsing, binary
encoding, cryptography and collection manipulation remain synchronous
computations. The current TLS package is moved intact under sync; an async TLS
transport is not introduced by this cleanup. HTTP keeps its current reader
contract; no unimplemented async parser is claimed.

Former public `asyn` packages are removed rather than retained as parallel
aliases. Use the default packages for async, or explicit sync imports for
blocking code. Internal `std::sys::net::asyn` remains an implementation detail.
Compiler file loading explicitly selects `std::io::sync::File`.

At scope exit, values are cleaned up automatically. Explicit `drop(value)` is
useful when an example intentionally releases a resource early, such as closing
a file before deleting its path on Windows; error-arm boilerplate does not
require explicit destruction.

[Executed integration evidence](cycles/ASYNC_DEFAULT_API_CYCLE.md).
