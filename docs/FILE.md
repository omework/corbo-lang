[Français](FILE-fr.md)

# File and inline assembly

File I/O is synchronous by default (`std::io::File`); asynchronous I/O is explicit
(`std::io::asyn::File`). FileMode, FilePerm, FileStats and SeekFrom remain in
`std::io`. Async operations run on blocking workers.


The Rust frontend and C backend implement `@unchecked`, `addr`, and
target-sized `usize`. `@asm` supports Linux x86-64 and macOS and Windows on x86-64 and ARM64. Integer `mov` operands are lowered to Intel memory operands or ARM64 loads and stores.
An assembly block must occur inside `@unchecked`.

The standard library exports the same `std::io::File` and `FileError`
on Linux x86-64, macOS, and Windows. Target conditions select the private
platform type. The Unix type owns a POSIX descriptor. The Windows type owns
a native `HANDLE` from `CreateFileW`, reads with `ReadFile`, and closes it with `CloseHandle`. The path is converted from UTF-8 to UTF-16 in bounded stack storage.
Scope exit or explicit `drop(file)` invokes the inner type's destructor.

| Operation | Behavior |
| --- | --- |
| `File::open(path, mode)` | Opens a UTF-8 string path; READ and WRITE combine with CREATE, CREATE_NEW, APPEND, TRUNCATE and SYNC. |
| `File::create(path, mode, perm)` | Opens or creates a UTF-8 string path with a `FilePerm` creation policy; EXCLUSIVE and TRUNCATE remain explicit. |
| `file.read(&mut buffer[..])` | Reads at most the buffer length and returns the number of bytes read. EOF and empty buffers return zero. |
| `file.write(&buffer[..])` | Writes up to the buffer length and returns the number of bytes written. An empty buffer writes zero bytes. |
| `file.read_at(&mut buffer[..], offset)` | Reads at an explicit `u64` byte offset without moving the cursor. EOF and valid empty ranges return zero. |
| `file.write_at(&buffer[..], offset)` | Writes at an explicit offset without moving the cursor; read-only and append modes are rejected. |
| `file.sync_all()` | Requests persistence of this file's contents and metadata; returns synchronization errors. |
| `file.truncate(length)` | Sets the file length without moving its cursor; extension reads as zero bytes. |
| `file.seek(from)` | Sets the current byte position and returns the resulting absolute position as a `u64`. |
| `File::rename(source, destination)` | Renames a path on the same filesystem and replaces an existing destination file when the OS permits it. |
| `file.stats()` | Returns a `FileStats` for the open file. `stats.size()` reports its size in bytes as a `u64`. |
| `File::delete(path)` | Removes the file entry at the path using the platform's deletion rules. |

Sequential `read` and `write` advance the file's current position by the number of bytes
transferred. A caller that requires a complete transfer can retry with the
remaining slice.

Use `SeekFrom.Start(offset)` for an absolute position, `SeekFrom.Current(offset)`
for an offset from the current position, or `SeekFrom.End(offset)` for an
offset from the end. Each offset is an `i64`. A negative absolute position
returns `InvalidOptions`. A seek beyond the end leaves the file length
intact. The OS reports failures such as a position before the beginning or
a non-seekable handle. [Linux lseek](https://man7.org/linux/man-pages/man2/lseek.2.html) · [Windows SetFilePointerEx](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfilepointerex)

Rename validates both paths before calling the OS. A move across filesystems
returns an OS error. [Linux rename](https://man7.org/linux/man-pages/man2/rename.2.html) · [Windows MoveFileExW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw)

Combine `FileMode::READ` and `FileMode::WRITE` with `|`. At least one is
required. `APPEND` and `TRUNCATE` require WRITE; `EXCLUSIVE` requires CREATE.
`CREATE_NEW` combines CREATE and EXCLUSIVE. Unknown flags and permission bits
outside the nine supported bits return `InvalidOptions`.
The access mode applies to the returned handle. The creation policy
applies to future access to the file.

- `FilePerm.DefaultMode` uses the platform's defaults. Linux and macOS request mode `0666` subject to the process creation mask and directory policy. Windows inherits the parent directory's ACL.
- `FilePerm.Perm(0x180)` requests owner read and write access (`0600` in octal). Linux masks the inherited POSIX ACL or applies the process creation mask. macOS supplies an empty ACL that blocks inheritance and applies the creation mask to the mode bits. Windows sets a protected ACL at creation, using the effective account, its primary group, and Everyone for the three classes of data access. [Linux creation mask](https://man7.org/linux/man-pages/man2/umask.2.html) · [macOS ACL inheritance](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_authorization.c) · [Windows security descriptor flags](https://learn.microsoft.com/en-us/windows/win32/secauthz/security-descriptor-control)

With explicit permissions, the library checks the access information on
the resulting handle before returning it. A filesystem that reports a
broader Unix mode or a different Windows ACL causes creation to return
an OS error. An error from that check can leave an empty file at the path.

`std::io::asyn::File` exposes the same operations with `.await`. It runs file
operations on the runtime's blocking workers. Its `FileError` adds
`LaunchFailed`. Pending operations keep the file and any borrowed buffer or
path alive until completion. `FileStats` is shared by the two APIs and lives
in `std::io`, alongside `FileMode`, `FilePerm`, and `SeekFrom`.

The portable API accepts UTF-8 `&str` paths and adds the native terminator internally.
Empty paths, embedded NUL bytes and paths over 32767 bytes return `InvalidPath`. OS errors use `Os { code }` with a negative errno on Unix and a negated Win32 error on Windows. Linux uses kernel syscalls, macOS calls libSystem, and Windows calls Win32, all from `@asm`.

- `@unchecked { ... }` marks code whose effects beyond Corbo's static analysis are the developer's responsibility. Ordinary Corbo checks still apply within the block. If assembly hands a buffer address to another thread, the developer must keep the buffer valid until that thread's last access, even after the block exits.
- `@asm { ... }` contains target assembly only. An operand written `${name}` refers to a Corbo binding in scope. The instructions express the transfers explicitly. For example, `mov rdi, ${address}` reads the binding's value and `mov ${raw}, rax` writes to the mutable binding.
- `usize` is an unsigned primitive with the pointer width of the compilation target. The compiler obtains that width from the same target configuration used by `#(if: ...)`. It is available without a target annotation.
- In the example, `addr` exposes a byte's address as a `usize`. The verifier retains the reference origin through supported Corbo operations, including a use as an assembly operand. The block author is responsible for the lifetime of accesses performed after the block exits.

## Positioned I/O

Both `std::io::File` and `std::io::asyn::File` expose:

```rust
fn read_at(&self, buffer: &mut [u8], offset: u64) -> Result<usize, FileError>
fn write_at(&self, buffer: &[u8], offset: u64) -> Result<usize, FileError>
```

The async versions are `async fn` and their calls require `.await`. The receiver
uses `&self`: neither operation reads or changes the sequential cursor. A short
transfer is valid; callers requiring the whole slice must advance both the slice
and explicit offset. Reading at/beyond EOF returns zero. Empty buffers return
zero when their offset is valid. The requested offset and end must fit in `i64`;
unrepresentable ranges return `InvalidOptions` before I/O. Write-only reads,
read-only writes and positioned writes in append mode return `InvalidOptions`.
Append mode is rejected because it can override the offset of Unix `pwrite`.

Unix uses `pread`/`pwrite` (Linux x86-64 direct pread64/pwrite64 syscalls), retrying
EINTR. Windows File owns its ordinary cursor-bearing HANDLE **and one OVERLAPPED
companion**, created with `ReOpenFile` immediately when the file opens. Failed
companion creation closes the ordinary handle before returning an error. This
keeps the original access intent and file identity across rename, without
reopening by path on each request. Both handles close on File destruction. Windows File therefore requires a
reopenable file that supports OVERLAPPED I/O; opening a special device that
cannot provide this companion can return an OS error.
Each positioned request uses a distinct completion event and a live OVERLAPPED
structure, calls ReadFile/WriteFile, waits with GetOverlappedResult when needed,
and closes its event after completion, including EOF/error paths. Ordinary
read/write/seek continue to use the original handle.

Async positioned methods use the existing blocking-worker dispatch. The file
and buffer borrows remain retained until the worker finishes; this does not
introduce an IOCP-based async-file implementation. Write completion does not
replace `sync_all()` for persistence.

[Focused validation](cycles/FILE_POSITIONED_CYCLE.md).

### Raw address confinement

The accepted rule reserves `addr(reference)` for code inside an `@unchecked`
block. The resulting raw address is confined to the block where it is created.
Returning it, assigning it to an outer binding, or putting it in a value that
leaves the block is rejected. Copying it, casting it to an integer such as
`usize`, or wrapping it in an aggregate preserves this restriction. Ordinary
numeric values, such as a byte count returned by a system call, can leave the
block. In checked code, `usize` is an ordinary unsigned integer of the target's
pointer width.

The rule governs what Corbo code can carry across the boundary. If opaque
assembly or an external call retains an address, the block author remains
responsible for keeping its target valid until the last external access.

Both compilers check this boundary. The standard library takes raw addresses
within the blocks that use them in the file, socket, reactor, system randomness,
cryptographic assembly, and OpenSSL code.

## Passing operands to assembly

An input `${name}` supplies the value of the Corbo binding. An explicit
`mov ${raw}, rax` writes the result back to the mutable binding `raw`.
In the x86-64 lowering described here, the backend places these operands
in fixed slots and reserves `r12` as their base in a separate assembly routine. Each operand resolves to a
fixed offset from `r12`, which the assembly leaves intact. The slots stay
addressable as `push` and `pop` change `rsp`. ARM64 uses `x19` as the stable base. Calls inside a block follow the target ABI, including stack alignment and Windows x86-64 shadow space. The backend must also make
room for the saves, including protecting any compiler data that would
otherwise occupy the stack space used by the pushes.

The assembly restores the stack pointer, flags, and the registers it modifies
before returning to Corbo, as shown below. The call boundary also lets the C compiler account for caller-saved registers. It stores the result in its output slot before
restoring `rax`. Restoring registers preserves the memory effects of the
system call.

The backend initializes the operand slots from the Corbo bindings before
the call and copies the slots written by `mov` back after the call. Each
binding has one slot. A transfer between two Corbo operands uses an
intermediate register.

The backend conservatively assumes that `@asm` can read and write accessible
memory. The default needs no effect annotation. For example, it must make
prior writes to the path visible before `open` and account for changes to
the buffer before a subsequent Corbo read. `@unchecked` puts responsibility
for the validity and bounds of those accesses on the block author.

`addr(&buffer[0])` obtains the numeric address of the first byte. A shared
and a mutable reference to that byte produce the same address. The permission
to write the slice is expressed by `buffer: &mut [u8]` in the signature of
`read`. The system call receives the address and the byte length separately.
The empty-buffer check runs before taking the address.

## Linux x86-64 example

The buffer length is the read budget. An empty buffer and end of file both
return `Ok(0)`.

```rust
use std::io::{File, FileError};
use std::io::{FileMode};

fn main() {
    let path = "in.txt";

    match File::open(&path[..], FileMode::read_only()) {
        Ok(opened) => {
            let mut file = opened;
            let mut buffer: [u8; 8] = [0; 8];

            match file.read(&mut buffer[..]) {
                Ok(count) => { print(count); },
                Err(error) => {
                    match error {
                        FileError.InvalidPath => { print(-1); },
                        FileError.InvalidOptions => { print(-2); },
                        FileError.Os { code: code } => { print(code); },
                    }
                },
            }
        },
        Err(error) => {
            match error {
                FileError.InvalidPath => { print(-1); },
                FileError.InvalidOptions => { print(-2); },
                FileError.Os { code: code } => { print(code); },
            }
        },
    }
}
```

The [blocking API](../stdlib/src/io/file.crb) and
[Unix File](../stdlib/src/sys/unix/file.crb) and
[Linux x86-64 syscalls](../stdlib/src/sys/unix/linux/x86_64/file.crb)
are written in Corbo. [Windows File](../stdlib/src/sys/win/file.crb)
owns its handle and uses the [Win32 assembly backend](../stdlib/src/sys/win/native/file.crb). See also the [macOS assembly backend](../stdlib/src/sys/unix/native/file.crb).


## Persistence and explicit tail repair

Both File APIs expose `sync_all()` and `truncate(length: u64)`. The explicit
async API runs them on blocking workers; the default synchronous API
executes them directly. Lengths above `i64::MAX` return `InvalidOptions` before
calling the OS. A failed truncation is returned as an error. The current cursor
is preserved even when it lies beyond the new end.

Linux uses `fsync` and `ftruncate`; interrupted calls are retried. macOS uses
`fsync` followed by `F_FULLFSYNC`, and `ftruncate`. Windows uses
`FlushFileBuffers` and `SetFileInformationByHandle(FileEndOfFileInfo)`, preserving
the file pointer. These calls request OS/device persistence; they are not an
absolute guarantee against every hardware or filesystem failure.

Synchronizing a file does **not** establish durability of a newly created or
renamed parent-directory entry. A durable publication protocol must provision
its directory entries or add an appropriate directory synchronization step.
`truncate` does not itself synchronize: call `sync_all()` when the chosen
persistence protocol requires it.

[Focused validation](cycles/FILE_DURABILITY_SUBDB_CYCLE.md) records the executed
sync/async cases and platform limits.

## String paths and independent mode flags

All portable File path parameters (`open`, `create`, `rename`, `delete`) accept
`&str`, in both `std::io` and `std::io::asyn`. Supply normal UTF-8 text without
an appended NUL. The API uses bounded internal syscall storage, rejects empty
paths and embedded NUL bytes, and supports at most 32767 UTF-8 bytes per path.
The private `std::sys` layer retains its NUL-terminated byte ABI.

```rust
let file = File::open("journal.wal", FileMode::READ | FileMode::WRITE | FileMode::CREATE)?;
```

READ and WRITE are independent bits. READ_ONLY, WRITE_ONLY and READ_WRITE remain
aliases. CREATE preserves an existing file; TRUNCATE explicitly clears it.
CREATE_NEW is CREATE | EXCLUSIVE and fails atomically if the path exists.
EXCLUSIVE without CREATE, an empty access mode, unknown flags, or write-only
behaviors without WRITE return InvalidOptions. APPEND and TRUNCATE may combine.
SYNC requests synchronous OS writes. `create(path, flags, perm)` adds CREATE and
uses explicit/default permissions; it does not silently request exclusivity or
truncation. Use CREATE_NEW when creating private key material exclusively.

Unix maps these controls to open flags; Windows uses the corresponding
CreateFile dispositions and WRITE_THROUGH. Native handles remain non-inheritable.
[Unix flags](https://man7.org/linux/man-pages/man2/open.2.html),
[Windows dispositions and flags](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew).
