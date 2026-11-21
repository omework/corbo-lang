[Français](ASYNC_API-fr.md)

# Synchronous defaults and explicit asynchronous APIs

This is an API/STD organization convention. Grammar, captures, moves, borrowing,
branch lifetimes and destruction retain their existing rules. `main` is synchronous.

| API | Synchronous default | Explicit asynchronous variant |
| --- | --- | --- |
| Files | `std::io::File` | `std::io::asyn::File` |
| Buffered streams | `std::io::buffered::{BufReader, BufWriter}` | `std::io::asyn::buffered::{BufReader, BufWriter}` |
| TCP | `std::net::tcp` | `std::net::asyn::tcp` |
| UDP | `std::net::udp` | `std::net::asyn::udp` |
| Sleep and Timer | `std::time::{sleep, Timer}` | `std::time::asyn::{sleep, Timer}` |
| Mutex | `std::Mutex` | `std::asyn::Mutex` |
| Existing TLS transport | `std::net::tls` | Not implemented |

Shared declarations remain in `std::io::{FileMode, FilePerm, FileStats, SeekFrom}`,
`std::net::{SocketError, Datagram}`, `std::net::ipv4::{Addr, SocketAddr}`, and
`std::time::{Duration, Instant, Error}`. There is no implicit sync/async conversion.
`asyn` operations are awaited explicitly. Setup and in-memory accessors retain
synchronous signatures where appropriate.

Async files and timers use blocking workers. Async sockets use epoll, kqueue or
IOCP. Async mutex waiters park their polling root and are woken through a FIFO
handoff; they do not spin or allocate a blocking worker per lock attempt.

The old `::sync` packages are removed. Compiler file loading uses `std::io::File`.
Native system modules remain implementation details. HTTP parsing keeps its
synchronous reader contract. Scope exit automatically cleans owned resources.

## Mutex ownership

Both mutex variants own `T`. `new(value)` constructs a stable native resource,
`lock(&self)` returns a guard, and guard `get()` / `get_mut()` borrow `T`.
The async variant's `lock()` returns a Future and requires `.await`.
The public acquisition uses a shared reference. The trusted implementation
creates a mutable payload borrow inside `@unchecked`, preserving its target
and lifetime graph; the programmer must implement the promised lock correctly.
Multiple tasks can borrow the mutex, while its lock
contract serializes payload access. The mutex must outlive guards and waiters.

The ordinary `#(lock: on=self, through_result=true)` contract retains protection
through guard destruction. Neither type name has special lock semantics.
Locking is implemented by the STD/runtime; annotations alone do not perform it.

A synchronous guard owns a native-thread lock and is marked
`#(thread: transfer=false)`. It cannot migrate to another thread, including as
live suspended state in a launched Future. An async guard owns logical task
state and can unlock on another worker. Guard destruction releases the lock;
mutex destruction occurs before payload field cleanup. Recursive acquisition
while retaining a guard is rejected by the existing lock contract analysis.

[Validation report](cycles/SYNC_DEFAULT_MUTEX_CYCLE.md).
