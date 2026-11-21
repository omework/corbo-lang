# File persistence APIs for Subdb

## Scope

API/STD change: add sync and async `File.sync_all()` and `truncate(u64)` using
existing language and worker mechanisms. No normative rule or Rust frontend
change. Subdb also exposed a separate corboc error-propagation cleanup defect;
that compiler change and its regression are tracked in the compiler repository.

## Implementation

Linux x86-64 uses fsync/ftruncate syscalls and retries EINTR. macOS ARM64/x86-64
uses fsync followed by F_FULLFSYNC, plus ftruncate. Windows ARM64/x86-64 uses
FlushFileBuffers and SetFileInformationByHandle(FileEndOfFileInfo); truncation
does not reposition the handle. Owned platform wrappers preserve normal drop
behavior. Async File delegates to the existing blocking workers.

Both public APIs reject lengths above i64::MAX. Extension is zero-filled by the
OS. Truncation does not synchronize automatically. File synchronization does
not establish durability of new directory entries; deployment/provisioning or
a future directory API must handle that separately.

## Executed evidence

Each of `validation/fixtures/file_durability` and `file_durability_async`
produces six true results: cursor preserved after shrink, cursor preserved after
extension, preserved prefix plus zero-filled extension, zero-length truncation
and synchronization, oversized-length rejection, read-only truncation rejection.

| Target | Sync | Async |
| --- | --- | --- |
| macOS ARM64 | Executed, O1/fatal UBSan | Executed, O1/fatal UBSan |
| macOS x86-64 | Executed, O1/fatal UBSan | Executed, O1/fatal UBSan |
| Linux x86-64 | Executed in linux/amd64 container | Executed in linux/amd64 container |
| Windows x86-64 | Executed under Wine | Executed under Wine |
| Windows ARM64 | Compiled only | Compiled only |

Nonhost code was emitted using temporary host emitters configured with the
existing target-specific selections, then compiled using cc/Zig. This is not a
new public cross-compilation facility. Exact results are retained in
`validation/file-durability-results.json`. STD/runtime source documentation
coverage and generated-reference freshness pass with `scripts/stdlib_docs.py --check`.

These executions do not simulate power failure, validate storage-controller
firmware, or prove every filesystem's persistence guarantees. Windows ARM64
execution remains deferred by user decision. Linux ARM64 File is not added by
this change.
