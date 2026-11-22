[Français](ENUM_LAYOUT-fr.md)

# Compact enum storage

Status: accepted design, recorded 2026-11-22. Not implemented.
Scope: compiler memory layout and lowering; no grammar or API change.

## Current implementation

Ordinary nominal enums currently use a tag followed by separate storage for
all variant fields. The generated per-field C unions provide alternate field
names; they do not share storage between variants. Consequently, the layout
includes the payload fields of every variant, although only one is active.
This is a backend layout limitation, independent of EN1/V3 value semantics.

## Retained improvement

Represent an ordinary inline enum as a tag plus one shared payload area.
Each variant with fields has its own layout inside that area. Empty variants
need no payload storage. The shared area accommodates the largest variant
payload and the strongest alignment required by any variant.

Compute the complete enum size using target alignment and padding, including
any existing destruction metadata. Do not add all variant payload sizes.
Tag-width reduction and niche optimizations are not required by this change;
the current backend's tag is 64 bits. No stable serialization or external ABI
is introduced by this decision.

For `Empty`, `Number(i64)` and `Pair(i32, bool)`, a typical 64-bit layout with
no extra destruction metadata becomes a tag followed by a shared 8-byte
payload: 16 bytes overall instead of the current 24 bytes. These sizes depend
on the target ABI, rather than constituting a universal size guarantee.

## Integration still to implement

- [ ] Lower variants to shared storage, with distinct fields inside each variant.
- [ ] Use the same target layout for size/alignment calculations, post-AST
      placement, datastack reservations, arrays, ordinary pool slots and emitted
      C declarations, including the representation exposed to `@c`.
- [ ] Preserve existing construction, copies/moves, pattern access, borrowing,
      active-field equality and once-only destruction. Inactive variant storage
      must not be read or destroyed.
- [ ] Validate the resulting sizes, alignment and directly affected operations
      on the relevant targets when implementation begins.

The pool's internal allocation strategy, including variant-specific storage
where already used, is a separate concern; this decision does not replace it.
No compiler implementation or executable validation was performed for this
recording task.
