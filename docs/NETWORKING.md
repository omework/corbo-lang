# TCP and UDP sockets

For the HTTP/1.1 parsing building blocks above these transports, see
[HTTP parsing](HTTP.md). Parsers remain synchronous computations; they do not
change the transport namespace convention.

`std::net::asyn::{tcp, udp}` are asynchronous; `std::net::{tcp, udp}`
are blocking. Endpoint accessors, bind and UDP connect keep their existing
synchronous setup behavior. Blocking-only TLS lives in `std::net::tls`.

## Blocking API

The STD provides the blocking IPv4 APIs in `std::net::tcp`
and `std::net::udp`. The caller supplies data buffers. The blocking
implementations use the address, backlog, error, and operation contracts
described below.

| Type | Creation | Operations |
| --- | --- | --- |
| `tcp::Connection` | `tcp::connect(address)` or a listener's `accept()` | `read(&mut [u8])`, `write(&[u8])`, `addr()`, `peer()` |
| `tcp::Listener` | `bind(address, Option<i32>)` | `accept()`, `addr()` |
| `udp::Connection` | `udp::connect(address)` | `send(&[u8])`, `recv(&mut [u8])`, `addr()`, `peer()` |
| `udp::Listener` | `bind(address)` | `send(&[u8], destination)`, `recv(&mut [u8])`, `addr()` |

A receive into an empty UDP slice uses one scratch byte internally where
the native receive needs a buffer to return the sender address. The
public receive limit is still zero bytes.

The platform is selected at compile time. The implementations cover
Linux x86-64, macOS ARM64 and x86-64, and Windows ARM64 and x86-64.
When linking emitted C manually on Windows with a GNU-compatible
driver, pass `-lws2_32`.

## API contracts

The async API is available in
`std::net::asyn::tcp` and `std::net::asyn::udp`, each with its own
`Connection` and `Listener` types. The four modules use
`std::net::SocketError`.

### Addresses and binding

Both APIs use the address types from `std::net::ipv4`. An `Addr`
represents an IPv4 address. A `SocketAddr` combines an `Addr` and a
`u16` port. `bind` and `connect` take a `SocketAddr`.
Callers parse text explicitly, for example
`SocketAddr::parse("127.0.0.1:8080")`. When the components are already
available, `SocketAddr::new(Addr::new(127, 0, 0, 1), 8080)` constructs
the address directly from four `u8` octets and the port.

`addr()` returns the local socket address. A listener bound to port `0`
reports the port assigned by the system through `listener.addr()`.
On a connection, `peer()` returns the remote socket address. These
accessors are synchronous in both variants. An unconnected UDP listener
gets the remote address from each received datagram.

In both TCP modules, `Listener::bind(address, backlog)` is synchronous.
It creates the socket, binds the local address, and calls `listen` before
returning the listener. The system manages the queue of connections waiting
to be accepted. The application controls how many accepted connections it
processes concurrently.

The `backlog` argument has type `Option<i32>`. `Some(n)` passes the signed
value directly to the system, which applies its own limits and interprets
special values such as `0` and `-1`. `None` requests the system maximum.
On the three supported platforms, `i32::MAX` represents this request. Linux
and macOS cap it at the configured maximum, and Winsock interprets it as
`SOMAXCONN`.
[Linux](https://raw.githubusercontent.com/torvalds/linux/master/net/socket.c) ·
[macOS](https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/bsd/kern/uipc_socket.c) ·
[Winsock header](https://raw.githubusercontent.com/microsoft/win32metadata/main/generation/WinSDK/RecompiledIdlHeaders/um/WinSock2.h)

UDP `Listener::bind(address)` is also synchronous. A bind failure caused
by an address conflict is reported as `AddressInUse` across protocols,
variants, and platforms.

### TCP

TCP exposes `connect` as a function of the protocol module in both APIs.
The result contains a connection from that module.

```rust
// std::net::tcp
pub fn connect(address: SocketAddr) -> Result<Connection, SocketError>

// std::net::asyn::tcp
pub async fn connect(address: SocketAddr) -> Result<Connection, SocketError>
```

The blocking `tcp::connect(address)` waits on the calling thread.
With the async module imported as `tcp`, `tcp::connect(address).await`
suspends the task if the connection is still being established. It
returns `Ok(connection)` when the system confirms the connection or
`Err(error)` if the attempt fails. A refusal is reported as
`ConnectionRefused` in either variant.

`listener.accept().await` suspends the task while no client is ready.
The runtime can run other tasks on that thread. In either variant, a
successful `accept` returns a `Connection` that owns its socket
independently of the listener.

Both TCP variants expose `read(&mut [u8])` and `write(&[u8])`. `read`
reports the number of bytes written into the slice. `write` reports the
number of bytes accepted by the system. Both counts can be smaller than
the length of the slice. TCP delivers an ordered byte stream. The
application defines any message boundaries and repeats `write` with the
remaining bytes when it needs to send a complete message.

- A `read` with a nonempty slice returns `Ok(0)` at end of stream. In the
  async variant it suspends when there are no bytes to read and the stream
  is still open. The received bytes are available in `buffer[..count]`
  after a successful read.
- A `write` with a nonempty slice reports at least one byte on success.
  In the async variant it suspends if the system cannot accept any bytes yet.
- A `read` or `write` with an empty slice returns `Ok(0)` immediately.

### UDP

`udp::connect(destination)` is synchronous in both UDP modules and returns
a `Result<Connection, SocketError>` directly. Success means the local socket
is configured with the specified peer. `Connection.send(&[u8])` sends to
that peer, and `Connection.recv(&mut [u8])` receives datagrams from that
peer only and returns the byte count on success.
`Listener.send(&[u8], destination)` takes a `SocketAddr`, and
`Listener.recv(&mut [u8])` returns a `Datagram` with the number of bytes
written in `count()` and the sender's `SocketAddr` in `sender()`.

`send` submits one whole datagram, including when the slice is empty.
`Ok(n)` reports the full length accepted by the system. In the async
variant, `send` suspends if the system cannot yet accept the datagram.

`recv` receives one datagram per call. The async variant suspends until
a datagram is available or an error occurs. A datagram that fits is
reported as a success, including an exact fit. A datagram that exceeds
the size of the slice is consumed and reported as `DatagramTooLarge`.
The next `recv` reads the next datagram. With an empty slice, `recv`
still waits for a datagram. An empty datagram succeeds with a count of
zero, and any nonempty datagram is consumed with `DatagramTooLarge`.
On a listener, a successful receive of an empty datagram includes the
sender's address.

### Buffers and socket ownership

The caller provides the slices for `read`, `write`, `recv`, and `send`
and chooses their size. The network library uses the supplied slice
directly, including across a suspension. Read and receive operations
borrow the destination mutably. Write and send operations borrow the
source for reading. The borrow covers the operation until completion.

A socket has one owner. Moving the owner transfers the responsibility for
closing the socket. Destroying the owner closes it.

On an async TCP `Connection`, `split()` borrows the connection and returns
two views, a `ReadHalf` for `read` and a `WriteHalf` for `write`. The views
use the same system socket and have separate state for each direction.
The connection remains the sole owner. Both views can be moved into
separate tasks when the compiler can prove that the connection survives
both tasks. The compiler rejects a move or destruction of the connection
while either task can still use its view. Destroying a view releases its
borrow. The connection can be destroyed and its socket closed after both
borrows end.

### Async socket backends

An async `read` captures the connection and destination slice in its
Future. The runtime wakes the task that is awaiting the Future. On
Linux and macOS the Future attempts a nonblocking receive in `poll`.
When it would block, `epoll` or `kqueue`, respectively, reports readiness
so the task can retry. On Windows the Future submits an overlapped
`WSARecv` and resumes on IOCP completion. The destination buffer and
overlapped request retain their addresses until the kernel completes
the request. Platform bindings use `@asm`.

On Unix, TCP connect, accept, read, write, and UDP receive and send use
nonblocking sockets. A socket registers one notification at a time per
direction. The runtime removes that registration before waking the task.
Linux explicitly removes a delivered one-shot epoll interest. macOS
uses a one-shot kqueue filter.

On Windows each socket is associated with IOCP once. TCP connect and
accept submit `ConnectEx` and `AcceptEx`. TCP and UDP transfer operations
submit overlapped Winsock requests. The original task resumes after
the completion packet arrives, including when a successful submission
completes immediately. The request and the caller's buffer remain live
until then. The scheduler uses the same park and wake transition as
task completion, including notifications that arrive before parking.
[ConnectEx](https://learn.microsoft.com/en-us/windows/win32/api/mswsock/nf-mswsock-lpfn_connectex)
· [AcceptEx](https://learn.microsoft.com/en-us/windows/win32/api/mswsock/nf-mswsock-acceptex)

The active self-hosted `corboc` builds both variants, including
`SocketAddr::parse(&str)` and the `Option<i32>` TCP backlog. See the
cycle report for the environments exercised.
[Validation report](cycles/CORE_COMPOSITION_CYCLE.md#async-tcp-udp-and-socket-wakeups)
· [Blocking network with corboc](cycles/CORE_COMPOSITION_CYCLE.md#scalar-option-and-blocking-network-with-corboc)
