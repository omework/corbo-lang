[Français](RUNTIME_METRICS-fr.md)

# Runtime memory metrics

`runtime::metrics::memory_stats() -> MemoryStats` returns a process-wide sample
of Corbo-managed fixed datastacks and growing region payload storage. The package
is supplied with the STD under `stdlib/src/runtime/metrics/`; ordinary imports and
qualified names work. Its three `usize` accessors report bytes:

- `reserved()`: page-rounded virtual-address ranges reserved for fixed stacks and
  region bands. Committed pages are included in this number.
- `committed()`: pages currently committed/access-enabled within those ranges.
  This is not physical resident memory or process RSS.
- `occupied()`: fixed cursor spans (including alignment and pool bookkeeping),
  minus unused pool slot payloads, plus active region lengths times element widths.
  Thus dropping a pooled allocation reduces occupancy without releasing the pool's
  reserved or committed pages. Cursor rewind retires both the span and its pool facts.

```rust
use runtime::metrics::{MemoryStats, memory_stats};

fn main() {
    let stats: MemoryStats = memory_stats();
    print(stats.reserved());
    print(stats.committed());
    print(stats.occupied());
}
```

The counters aggregate active and suspended fixed stacks across threads and shared
region bands. Task context switches preserve accounting rather than treating a
restored cursor as a new allocation. Region growth, pop/remove, cleanup and page
reclamation update the corresponding counters. The implementation maintains five
atomic counters from cursor and pool/region transitions; reads allocate no memory,
walk no mutable descriptors and acquire no global mutex. Updates add atomic traffic
to those transitions.

Each field is sampled independently. During concurrent allocation or cleanup,
fields can describe adjacent instants; cross-field inequalities and differences
between samples are meaningful only once the relevant workers are quiescent.
Occupied-byte subtraction saturates at zero when independent samples straddle an
update. Metrics are observations, not lifetime or synchronization guarantees.

This counts managed datastack mappings and their region payloads. It excludes
OS thread stacks, registers/native C locals, foreign allocations and separately
mapped scheduler/reactor bookkeeping. Regions with unused capacity retain reserved
space, and committed pages can outlive their occupied payload until reclamation.
The C API exposes the same counters as `corbo_memory_stats()`, returning
`CorboMemoryStats`. The pool/context bookkeeping layout change advances the
experimental C ABI to version 2: rebuild C consumers against the matching header
and runtime. Corboc's current release installation is not changed automatically.

## Focused validation

`python3 scripts/validate_runtime_metrics.py --compiler ../corboc/build/memory-metrics/corboc`
runs eight Corbo observations and the same exact-counter/concurrent-reader C ABI
witness against both the C reference and compiled Corbo runtime, with O1/fatal
UBSan. Each C ABI witness exercises three workers performing 30,000 total slot
claim/release cycles while another thread samples counters; final quiescent
counters return to zero. API checks cover pool holes, vector push/pop, scope
rewind and async suspension. The API witness additionally runs on macOS x86-64,
Linux x86-64 and Windows x86-64 under Wine; Windows ARM64 compiles only.
Host execution is macOS ARM64. No TSan run, performance benchmark or general
concurrency proof is claimed. Results are in `validation/runtime_metrics/`.
