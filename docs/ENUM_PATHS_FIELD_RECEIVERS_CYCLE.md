# Enum paths and field method receivers

The preferred enum variant spelling is `Enum::Variant`, for construction,
`match` and `if let`. Dot spelling remains accepted for compatibility. Payload
copy/move and borrowing rules are unchanged. Associated functions retain their
qualified-call meaning. The grammar, English/French rule documents, README
variants and enum feature example reflect this spelling.

The active corboc compiler also resolves methods on nested field receivers,
including `self.tracker.lock().await`. It retains ordinary owner/borrow and
lock-result dependencies. An implicit method receiver is an ordinary tracked
borrow; it does not copy the owning field. Async frames can retain a receiver
pointer while a supported argument awaits.

The compiler repository owns the implementation and detailed report
`docs/ENUM_PATHS_FIELD_RECEIVERS_CYCLE.md`. Its focused validation executes three
fixtures under fatal UBSan and checks five diagnostic/lifetime refusals. Existing
enum and semantic diagnostic regressions pass. The host is macOS ARM64; this
compiler change did not replay the OS/runtime platform matrix. Windows ARM64
execution remains deferred. The frozen Rust frontend, STD and runtime are unchanged.
