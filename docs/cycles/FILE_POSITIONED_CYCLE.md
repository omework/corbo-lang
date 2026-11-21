# Positioned File I/O

Date: 2026-11-22. API/STD extension using existing grammar and verifier.
No core rule, runtime primitive or Rust-frontend change.

## Delivered

- Shared-receiver read_at/write_at for sync and async File; caller-owned buffers,
  u64 offsets, partial counts and preserved sequential cursor.
- Common signed-range validation and explicit access/append-mode checks.
- Unix pread/pwrite assembly, retrying EINTR; Linux x86-64 pread64/pwrite64 syscalls.
- Windows ordinary HANDLE plus an owned OVERLAPPED companion, opened together;
  distinct per-request completion events and GetOverlappedResult completion.
  Failed companion creation closes the primary; drop closes both handles.
- Async uses existing blocking workers and retained file/buffer dependencies.

## Executed evidence

Both witnesses return 42 and independently produce exactly `abcZXY`. They cover
positioned read/write, sequential operations before/after, high-offset EOF,
empty buffers, invalid ranges, read-only/write-only/append restrictions,
rename while open, use after rename, and scope cleanup after an ownership move.

- macOS ARM64: current installed corboc emission, fatal UBSan, sync and async.
- macOS x86-64 and Linux x86-64 Docker: fatal UBSan, sync and async.
- Windows x86-64 Wine: sync and async. Witness-only native interposition requires
  four owned companion handles and four completion events to be closed; real
  Win32 calls are used, including the EOF path and cleanup after a move.
- Windows ARM64: both complete witness executables compile/link; execution is
  deferred by the existing user decision.
- One focused rejection: dropping File before awaiting its retained read_at
  Future is rejected (status 8, rule 5).

The first Windows design reopened the positioned handle on every request. The
rename witness exposed FileNotFound under Wine after rename. Holding the
OVERLAPPED companion from open time fixed the witness and avoids later pathname
and permission rechecks. The first Linux harness mounted /tmp while compilation
used its /private/tmp canonical path; fixed the harness and reran.

Target executables are emitted by host-running test-only variants of current
corboc, selecting the corresponding target and its existing assembly/register
behavior. They are not native target compiler builds. No broad corpus, new
adversarial audit, or general safety proof is claimed. Wine is not physical
Windows; Windows ARM64 execution remains deferred. EINTR retry is implemented
but signal injection was not performed. Transfer counts were small; no forced
short-write, disk-full or IOCP fault-injection campaign was run. Windows opening
requires a reopenable OVERLAPPED-capable file; special devices were not tested.

## Reproduction

```sh
python3 validation/check_file_positioned.py --compiler ../corboc/build/check/install/bin/corboc --ubsan
```

For test-only target emitters, see corboc's `validation/create_target_emitter.py`.
Use `--cc`, `--runner`, `--windows` and `--compile-only` on the validator for the
target's native toolchain/runner. JSON evidence: FILE_POSITIONED_RESULTS.json.
