# File text paths and combinable modes

Public `std::io::File` and `std::io::asyn::File` now accept `&str` in open,
create, rename and delete. Paths exclude NUL; bounded native storage adds it.
Empty paths, embedded NUL and paths longer than 32767 UTF-8 bytes are rejected.

READ and WRITE are independent bits. CREATE preserves existing contents unless
TRUNCATE is requested. EXCLUSIVE requires CREATE; CREATE_NEW combines them.
APPEND and TRUNCATE require WRITE. SYNC requests the platform's synchronous-write
flag. Compatibility READ_ONLY/WRITE_ONLY/READ_WRITE spellings remain available.
The private native access ABI remains unchanged: the public wrapper translates
access bits before making system calls.

The focused sync/async scenario checks Unicode names, create/reopen preservation,
exclusive collision, append, malformed paths/modes, rename/delete and an
independent byte oracle. It includes positioned reads that preserve the cursor.
Unix additionally exercises explicit owner-read/write creation permissions.

| Target | Sync and async result |
| --- | --- |
| macOS ARM64 | Executed, fatal UBSan |
| macOS x86-64 | Executed, fatal UBSan |
| Linux x86-64 | Executed in Docker, fatal UBSan |
| Windows x86-64 | Executed under Wine |
| Windows ARM64 | Compiled and linked; execution deferred |

Wine's filesystem reports ERROR_NOT_SUPPORTED for exact ACL verification. This
cycle uses default Windows creation permissions and does not claim exact ACL
validation on physical Windows. The permission policy itself was not changed.
Cross-target emitters run on the host; they are not native compiler binaries.

The related positioned-I/O suite also passes sync and async on the host under
fatal UBSan, retaining its invalid-lifetime rejection. The frozen Rust frontend
was not modified or replayed. No broader safety proof is claimed.

Reproduce with `python3 validation/check_file_text_modes.py --compiler /path/to/corboc
--out build/file-text-modes/host --ubsan`. Target compiler/runner overrides are
available through --cc, --runner, --windows and --compile-only.
Machine-readable outcomes: [results](../../validation/file-text-modes-results.json).
