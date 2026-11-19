# Third-party notices

## Go internal/zstd

The native Corbo Zstd entropy-decoding implementation was adapted using
Go 1.24.3's [`internal/zstd`](https://go.googlesource.com/go/+/refs/tags/go1.24.3/src/internal/zstd/)
as a reference. This includes FSE table construction, Huffman weights,
sequence execution and cross-checking the RFC predefined tables.

Copyright 2023 The Go Authors. All rights reserved.

The [BSD-3-Clause license](GO-LICENSE.txt) is retained. Affected Corbo files
carry the combined SPDX expression `(MIT OR Apache-2.0) AND BSD-3-Clause`.
The code was rewritten for Corbo's checked integer arithmetic and bounded,
caller-owned storage; no Go runtime or library is linked.

The full notice also ships in
[`stdlib/THIRD_PARTY_NOTICES.txt`](../../stdlib/THIRD_PARTY_NOTICES.txt), so STD
installations retain it. Include the applicable notices when redistributing
derived sources or binary packages.
