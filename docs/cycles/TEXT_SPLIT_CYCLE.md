# Borrowed text splitting

## Scope and API

This is a STD API addition, with separate compiler integration for borrowed
UTF-8 descriptors. No grammar production or normative memory rule changed.

`String` and `&str` expose `split(separator: &str) -> std::text::Split`.
`Split::next(&mut self) -> Option<&str>` yields views of the original storage.
The implementation is ordinary Corbo in
[`stdlib/src/text/split.crb`](../../stdlib/src/text/split.crb); the compiler
forwards the native convenience method to that source-defined function.

Empty pieces are retained. Matches do not overlap. An empty separator splits
at Unicode scalar boundaries, with empty pieces at both ends. Exhaustion is
permanent. The descriptor and cursor have fixed size; no piece string or list
is allocated. Literal matching uses a straightforward O(n × m) byte scan in
the worst case, without normalization or grapheme segmentation.

## Compiler integration

The existing checked-value and per-field summary graphs now retain `&str`
storage roots through local bindings, borrowed fields, constructors and
`Option<&str>` results. Returned pieces refer to the text field's external
storage, independently of the mutable iterator cursor. Separator dependencies
remain on the iterator, rather than being attached to each piece.

General text-view lowering preserves evaluated descriptor temporaries, checks
slice bounds and UTF-8 boundaries, and uses byte-pointer casts for the runtime's
opaque descriptor data pointer. Generic inference can resolve the STD split
method's concrete result type. `Iter` can forward `next()` through a borrowed
split source.

A directly related defect was found during validation: `String.push_str`
accepted mutation while a still-used split iterator borrowed the string.
The compiler now invokes the existing exclusive-access conflict analysis for
that mutation; the same program is refused under N5. This is an observed
incorrect acceptance, not evidence of a demonstrated out-of-bounds execution.

## Executed checks

On macOS ARM64, generated C was compiled at O1 with fatal UBSan:

- Twelve successful programs cover empty owned storage, literal and owned
  strings, UTF-8 separators, Unicode-scalar splitting, empty text, overlapping
  candidate matches, missing matches, permanent exhaustion, actual returned
  bytes, a named view, cursor advancement/destruction, separator independence
  and the existing `Iter` wrapper.
- Four programs are refused for premature text destruction, text mutation,
  destruction while a piece remains used, and premature separator destruction.
- Seven existing related compiler cases pass: typed text length, byte-slice
  comparison, a custom buffered sink, borrowed-record forwarding, buffered
  counts, local-reference escape rejection and loan-write rejection.
- The complete README text package executes with stdout `13, 2, 5, 6, 0`.
- The generated STD/runtime reference inventories pass their freshness check.

The active checks are reproducible with:

```sh
python3 validation/check_text_split.py \
  --corboc ../corboc/build/text-split/corboc \
  --keep build/text-split/final

python3 validation/check_documentation.py \
  --corboc ../corboc/build/text-split/corboc \
  --only text --keep build/text-split/readme

python3 scripts/stdlib_docs.py --check
```

The focused runner retains source packages, compiler diagnostics, generated C,
C diagnostics and a completed JSON report. The compiler-side reproduction and
build evidence are recorded in the sibling compiler's
`docs/TEXT_SPLIT_CYCLE.md`.

## Limits

These are functional and directly related regression results, not an independent
safety audit. Linux and Windows execution were not repeated for this portable
API; Windows ARM64 execution remains deferred. The Rust frontend is frozen.
Other text APIs, arbitrary generic compositions and a broader adversarial
campaign are outside this change.

The focused checks select this checkout's STD explicitly. The paired compiler
commit pins the language revision containing this API; its report records the
pinned build validation. Build artifacts and diagnostics remain outside Git.
