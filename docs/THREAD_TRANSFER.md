[Français](THREAD_TRANSFER-fr.md)

# Thread transfer eligibility

**TR1 — Restricted thread transfer.** Types are eligible to move to another
thread by default. A struct or enum may opt out with a single annotation:

```rust
#(thread: transfer=false)
struct LocalResource {
    token: i64,
}
```

The annotation describes an implementation requirement, such as thread-bound
resource use or destruction. It does not prohibit ordinary moves within the same
thread and does not generate runtime synchronization or thread checks.

Eligibility is structural: an object owning a restricted value is restricted as
well. This includes nested fields, arrays, tuples, enum payloads, owned allocations
and containers. A containing type cannot override an inherited restriction.
Concrete generic specializations retain the annotation and their field facts.
Closure captures are fields of their concrete capture record and follow the same
composition rule. Async state is restricted when it captures a restricted owned
value or retains one across suspension. A restricted result must not be moved
back from a worker thread either.

The compiler rejects a crossing whose owned captures, execution state or results
contain a restricted component. Creating and destroying a local resource wholly
inside one worker is permitted if it never crosses or survives a migratable
suspension. Moving a reference does not move ownership of its target: this
annotation adds no separate Sync-like classification for references. Their
existing N4 lifetime, N5 synchronization and branch-completion checks still apply.
Those checks are independent of transfer eligibility; a lock cannot remove an
owned component's transfer restriction.

The property is derived from representation links after concrete specialization,
not from reserved resource type names. Unknown required proofs remain refusals.
Only `transfer=false` is an explicit annotation form; absence is the default.
The marker is metadata on structs/enums, not a function or block annotation.
