# Feature example cleanup

Scope: documentation/runnable examples only. No grammar, language rule,
compiler, STD or runtime implementation changed. All 38 feature examples and
README setup/API fragments were reviewed. English/French runnable code blocks
match their tracked sources. Complete examples remain focused on one mechanism.

## Changes

- Let scope-exit cleanup destroy unused error payloads. `_error` marks intentional
  ignoring, without repetitive explicit drop calls.
- Keep File in an inner block before path deletion, for blocking, async and
  buffered examples. Keep BufWriter.flush explicit: destruction does not flush.
- Replace drop-wrapped primitive results with ordinary checked calls.
- Handle thread join success/failure explicitly rather than dropping its Result
  and continuing as if launch had succeeded.
- Give HashMap.insert's previous-value result a `_previous` receiver.
- Consolidate duplicate time imports and add spacing to dense blocks.
- Retain explicit drop only where the code illustrates pool-slot reuse or
  destructor ordering. Retain named intermediate values, buffers, explicit
  references and contracts where they explain the feature or existing API.

## Executed evidence

Fourteen changed programs pass independently with active corboc on macOS ARM64,
O1 and fatal UBSan: async, async_file, async_time, binary, blocking, bounded_text,
buffered, compression, encoding, file, map, network, threads and time.
Their expected stdout remains unchanged. The runner also checks English
README/source synchronization; all 38 French blocks were checked separately.

A preliminary bare `values.insert(copy(key), 42);` was rejected with status 8
and diagnostic `8 / 87`. Binding `_previous` passes. This documents the current
receiver requirement for that call; this cleanup does not change the checker
or claim general support for discarding every returned aggregate as a statement.
The failed preliminary attempt and successful retry are both retained in the
[machine-readable record](EXAMPLE_CLEANUP_RESULTS.json).

Four other examples received spacing-only edits (arrays, closures, control,
destruction); they were source-reviewed and synchronized, not re-executed.
Unchanged examples were reviewed, not rerun. No full compiler suite,
self-reconstruction, platform campaign or independent audit was performed.
Earlier platform evidence is not extended by this documentation-only pass.

Reproduce an affected example from the language checkout:

```sh
python3 validation/check_documentation.py \
  --corboc ../corboc/build/async-default/bin/corboc \
  --only buffered --keep build/example-cleanup/buffered
```

Use another changed example name for its focused execution. No open language
arbitration remains in this documentation task.
