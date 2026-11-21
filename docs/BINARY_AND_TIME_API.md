[Français](BINARY_AND_TIME_API-fr.md)

# Binary encoding and monotonic time

These are STD APIs using the existing language mechanisms, not new core safety
rules. The [generated reference](STDLIB.md) lists their documented source APIs.
The [integration report](cycles/BINARY_TIME_BOUNDED_CYCLE.md) separates executed
evidence from untested paths and platform limitations.

## `std::encoding::binary`

Read and write primitives using caller-provided slices. Multi-byte operations
are named `read_TYPE_le`, `read_TYPE_be`, `write_TYPE_le`, and `write_TYPE_be`:
byte order is always explicit and never defaults to the host order.

- Fixed-width types: `u16`, `u32`, `u64`, `i32`, `i64`, `f32`, `f64`.
- Single-byte operations: `read_u8` / `write_u8`, `read_bool` / `write_bool`.
- `usize` has `_le` / `_be` operations on supported 64-bit targets. Prefer
  fixed-width types for a portable disk/network format.
- Reads take `&[u8]` and return `Result<T, Error>`. Writes take `(value: T,
  output: &mut [u8])` and return `Result<usize, Error>` containing bytes written.
- Each operation uses the first width bytes; trailing bytes are untouched.
- `Error.BufferTooSmall` reports insufficient input/output. Short writes leave
  output unchanged. `Error.InvalidBoolean` rejects any bool byte other than 0/1.
- Signed encodings are two's complement; float encoding transfers IEEE-754
  representation bits rather than numerically converting them.

```rust
use std::encoding::binary;

fn main() {
    let mut bytes: [u8; 8] = [0; 8];
    match binary::write_u32_be(16909060, &mut bytes[..]) {
        Ok(written) => { print(written); },
        Err(error) => { drop(error); return; },
    }
    match binary::read_u32_le(&bytes[..]) {
        Ok(value) => { print(value); },
        Err(error) => { drop(error); },
    }
}
```

This writes `01 02 03 04`, then reads those bytes as little-endian, producing
`67305985`. Struct serialization remains separate: native padding/layout does
not silently define a disk format. There is no hidden output allocation.

## Shared time values — `std::time`

`Duration` stores a nonnegative span in nanoseconds. Construct it with
`Duration::from_nanos(u64)`, `from_millis(u64)` or `from_secs(u64)`;
`as_nanos(&self) -> u64` reads it. Arithmetic overflow follows the existing
checked-integer failure behavior; these are ordinary owned values, not a new
implicit Copy category.

`Instant::now() -> Result<Instant, Error>` reads a monotonic clock.
`instant.after(duration) -> Instant` constructs a deadline, and
`instant.elapsed() -> Result<Duration, Error>` measures elapsed time.
`instant.remaining()` returns the span until a deadline, saturating at zero.
These timestamps have no wall-clock epoch or portable serialization meaning.
The bounded nanosecond representation and native clock resolution apply.

## Blocking waits — `std::time`

`Timer::after(duration) -> Result<Timer, Error>` or `Timer::at(instant) -> Timer`
constructs a deadline. `timer.wait() -> Result<(), Error>` blocks the calling
thread; the same timer can be waited repeatedly. Past deadlines complete without
another native sleep. `sleep(duration) -> Result<(), Error>` is the blocking
convenience function. Waiting rechecks the monotonic deadline after interruptions
and early wakes, splitting native waits into chunks of at most sixty seconds.

Backends use native assembly calls: CLOCK_MONOTONIC/nanosleep on Linux/macOS,
and QueryPerformanceCounter/Frequency plus Sleep on Windows. Counter scaling
avoids overflowing the fractional multiplication. Long spans/timestamps still
must fit the `u64` nanosecond representation. Errors are `ClockFailure`,
`WaitFailure`, and `LaunchFailed` (for async worker creation).

## Async waits — `std::time::asyn`

`sleep(duration)` and `Timer::wait(&self)` are async functions returning
`Result<(), std::time::Error>`. `Timer::after` and `Timer::at` construct the async
wrapper with the same deadline meaning as their blocking counterparts.

```rust
use std::time::Duration;
use std::time;

async fn work() -> i64 {
    match time::sleep(Duration::from_millis(2)).await {
        Ok(()) => { 42 },
        Err(error) => { drop(error); -1 },
    }
}

fn main() {
    let execution = runtime::spawn(work());
    match execution.join() {
        Ok(value) => { print(value); },
        Err(error) => { drop(error); },
    }
}
```

The caller task suspends; executor/poller threads do not sleep. This initial
implementation uses the existing `spawn_blocking` worker mechanism, with one
worker per active wait rather than a shared timer reactor. A timer borrowed by
an async wait must remain alive through that wait. Launch failure is mapped to
`Error.LaunchFailed`; ordinary runtime completion/cleanup remains in force.

Wall-clock dates, calendar operations, periodic intervals and timer cancellation
are outside this API. No new primitive or runtime scheduler interface was added.
