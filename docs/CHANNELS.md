# Bounded channels

`std::sync::channel::Channel<T>` blocks a native thread while waiting.
`std::sync::asyn::channel::Channel<T>` suspends a Future instead. Neither channel
creates a worker or starts a task by itself.

Both variants expose the same ownership-oriented interface:

```rust
fn new(capacity: usize) -> Channel<T>
fn close(&self)

// Synchronous variant:
fn send(&self, value: T) -> Result<(), SendError<T>>
fn recv(&self) -> Option<T>

// Asynchronous variant:
async fn send(&self, value: T) -> Result<(), SendError<T>>
async fn recv(&self) -> Option<T>
```

Capacity must be greater than zero. It bounds the number of queued values;
zero-capacity rendezvous channels are not part of this API. Queue storage uses
a dedicated managed region, inherits the active region-size limit, and remains
owned by the channel when the channel moves. Exhausting the region budget uses
the runtime's existing allocation-failure behavior. No unbounded queue or
fallback general-purpose heap is introduced.

A successful send transfers the value into the queue. Receiving transfers the
oldest value to the receiver. On failure, `SendError.Closed { value }` returns
the original value to the caller. Ordinary primitive-copy semantics still
apply to primitive arguments. The channel destructor closes the channel,
destroys every remaining queued value exactly once, and releases its storage.

`close()` is synchronous and idempotent in both namespaces. It wakes waiting
senders and receivers. Senders receive their unsent values back; receivers drain
already queued values before receiving `None`. There is no separate sender or
receiver endpoint count: a consumer waiting for `None` needs an explicit close.
Scope cleanup normally destroys the channel; explicit `drop()` is unnecessary
unless early destruction is intended.

The channel's shared methods carry lock contracts; runtime queue state is
protected by a short scheduler mutex. The channel must survive every borrowed
user and outstanding async operation, under the existing lifetime and branch
rules. A lock does not relax thread-transfer restrictions.

## Payload support

The current checked API admits primitives and self-contained fixed-layout
structs/enums, including owned values with user destructors. Values marked
`#(thread: transfer=false)`, including restrictions inherited through owned
fields, are refused as channel payloads.

Borrowed payloads and payloads requiring external pool, region or task
provenance are not yet admitted. Their lifetime dependencies cannot be hidden
inside the erased queue. Such programs are refused rather than treated as a
new lifetime exception. This is a compiler integration limit, not a prohibition
on adding dependency-aware channel support later.

## Wait registrations

A pending async operation owns a private wait Future whose stable task header
contains its registration. Queue readiness and registration use the same mutex
and an observed change epoch: a send/receive/close between checking readiness
and registering causes an immediate retry. Waking selects a FIFO registration
and schedules its root without polling under the lock. A notified task may
still need to retry; messages are FIFO, but strict acquisition fairness is not
promised.

Frame cleanup removes pending registrations, forwarding a selected notification
when necessary. No channel wait queue retains a pointer into a reclaimed frame.
Sync condition waits release the same mutex atomically while sleeping. The C
reference runtime implements the same transitions as the readable Corbo runtime.

See the [complete example](../examples/features/channels/src/main.crb) and
[validation report](cycles/CHANNELS_CYCLE.md).
