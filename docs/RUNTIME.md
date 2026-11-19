# Corbo runtime source reference

Generated from source documentation. Do not edit this reference by hand.

These are internal runtime entry points, not ordinary public Corbo APIs.
Raw addresses require live, aligned storage and the documented synchronization.
The [runtime guide](../runtime/corbo/README.md) explains the checked/unchecked boundary.
The [C ABI](../runtime/corbo_runtime.h) and [C reference](../runtime/README.md) retain their source comments.

Regenerate with `python3 scripts/stdlib_docs.py --runtime > docs/RUNTIME.md`.

## Modules

- [`runtime::api`](#runtimeapi)
- [`runtime::collections`](#runtimecollections)
- [`runtime::completion`](#runtimecompletion)
- [`runtime::completion_primitives`](#runtimecompletion_primitives)
- [`runtime::memory`](#runtimememory)
- [`runtime::primitives`](#runtimeprimitives)
- [`runtime::readiness`](#runtimereadiness)
- [`runtime::reclaim`](#runtimereclaim)
- [`runtime::scheduler`](#runtimescheduler)
- [`runtime::socket_primitives`](#runtimesocket_primitives)
- [`runtime::thread_primitives`](#runtimethread_primitives)
- [`runtime::threads`](#runtimethreads)
- [`runtime::values`](#runtimevalues)

## `runtime::api`

C ABI policy entry points. Aggregate argument/result marshalling is isolated in exports.py.

### `corbo_runtime_init`

[api.crb:4](../runtime/corbo/api.crb#L4)

```rust
fn corbo_runtime_init(fixed:usize,regions:usize,region:usize)
```

Initializes C-owned runtime storage with optional fixed-stack, region-stack and region-width budgets; repeated initialization terminates.

### `corbo_runtime_shutdown`

[api.crb:19](../runtime/corbo/api.crb#L19)

```rust
fn corbo_runtime_shutdown()
```

Releases the calling thread's C-owned runtime after all live resources and workers have been cleaned up; a stopped runtime is a no-op.

### `corbo_datastack_alloc`

[api.crb:34](../runtime/corbo/api.crb#L34)

```rust
fn corbo_datastack_alloc(size:usize,alignment:usize,count:usize)->usize
```

Allocates count aligned elements on the calling thread's initialized stack; invalid size/alignment or exhaustion terminates.

### `corbo_datastack_mark`

[api.crb:41](../runtime/corbo/api.crb#L41)

```rust
fn corbo_datastack_mark(out:usize)
```

Writes the current cursor, stack identity and region-scope marker to caller-provided CorboStackMark storage.

### `corbo_datastack_info`

[api.crb:47](../runtime/corbo/api.crb#L47)

```rust
fn corbo_datastack_info(out:usize)
```

Writes current cursor, committed bytes and fixed-stack capacity to caller-provided CorboStackInfo storage.

### `corbo_datastack_rewind`

[api.crb:53](../runtime/corbo/api.crb#L53)

```rust
fn corbo_datastack_rewind(mark:usize)
```

Restores a mark from this stack after caller cleanup; rejects foreign or forward marks and preserves live transferred regions.

### `corbo_pool_create`

[api.crb:63](../runtime/corbo/api.crb#L63)

```rust
fn corbo_pool_create(slots:usize,size:usize,arms:usize)->usize
```

Creates fixed slots for each enum arm on the current datastack; zero element width or invalid capacity terminates.

### `corbo_pool_take`

[api.crb:70](../runtime/corbo/api.crb#L70)

```rust
fn corbo_pool_take(out:usize,pool:usize,arm:usize)
```

Claims a slot in the selected arm and writes an allocation descriptor to out; invalid arms or exhaustion terminate.

### `corbo_region_new`

[api.crb:77](../runtime/corbo/api.crb#L77)

```rust
fn corbo_region_new(region:usize,size:usize,dedicated:bool)
```

Initializes a stable caller-owned region descriptor for element_size bytes per item; dedicated selects independent band storage.

### `corbo_region_drop`

[api.crb:84](../runtime/corbo/api.crb#L84)

```rust
fn corbo_region_drop(region:usize)
```

Destroys child-region links, releases payload storage and zeroes the caller's region descriptor.

### `corbo_runtime_abi_version`

[api.crb:89](../runtime/corbo/api.crb#L89)

```rust
fn corbo_runtime_abi_version()->u32
```

Returns the experimental C ABI version; clients must use the matching runtime header.

### `corbo_free_pages`

[api.crb:93](../runtime/corbo/api.crb#L93)

```rust
fn corbo_free_pages()
```

Requests immediate reclamation of complete unused pages without changing live values or their reserved address ranges.

### `corbo_allocation_data`

[api.crb:97](../runtime/corbo/api.crb#L97)

```rust
fn corbo_allocation_data(allocation:usize)->usize
```

Returns an allocation's payload address without transferring ownership or extending its lifetime.

### `corbo_allocation_drop`

[api.crb:101](../runtime/corbo/api.crb#L101)

```rust
fn corbo_allocation_drop(allocation:usize)
```

Destroys a live allocation before releasing its slot and clears its pool link; a cleared descriptor is harmless.

### `corbo_region_enter`

[api.crb:105](../runtime/corbo/api.crb#L105)

```rust
fn corbo_region_enter(maximum:usize,count:usize)
```

Enters a local region scope with the requested maximum region size and count budget.

### `corbo_region_push`

[api.crb:109](../runtime/corbo/api.crb#L109)

```rust
fn corbo_region_push(region:usize)->usize
```

Appends one uninitialized region element and returns its address; region exhaustion terminates.

### `corbo_map_new`

[api.crb:113](../runtime/corbo/api.crb#L113)

```rust
fn corbo_map_new(size:usize,dispose:usize)->usize
```

Maps a map descriptor and initializes its stable region storage with an optional element cleanup callback.

### `corbo_map_get`

[api.crb:117](../runtime/corbo/api.crb#L117)

```rust
fn corbo_map_get(map:usize,key:u64)->usize
```

Returns the stored value address for key, or zero when absent; the map retains ownership.

### `corbo_map_insert`

[api.crb:121](../runtime/corbo/api.crb#L121)

```rust
fn corbo_map_insert(map:usize,key:u64,incoming:usize,previous:usize)->bool
```

Moves incoming bytes into a stable entry. Returns true and moves the replaced bytes into previous when the key exists.

### `corbo_map_remove`

[api.crb:125](../runtime/corbo/api.crb#L125)

```rust
fn corbo_map_remove(map:usize,key:u64,previous:usize)->bool
```

Unlinks key and moves its value into previous; returns false without writing when absent and indexes the freed slot for reuse.

### `corbo_map_drop`

[api.crb:129](../runtime/corbo/api.crb#L129)

```rust
fn corbo_map_drop(map:usize)
```

Clears the caller's map pointer, destroys remaining values with dispose, then releases payload and descriptor storage.


## `runtime::collections`

Vector movement and map slot reuse preserve the same element ownership callbacks as the C reference.

### `region_push_owned`

[collections.crb:4](../runtime/corbo/collections.crb#L4)

```rust
fn region_push_owned(region:usize,item:usize,slot:usize)
```

Appends a child-region/slot link for recursive cleanup; the child descriptor and slot flag must remain valid.

### `region_push`

[collections.crb:10](../runtime/corbo/collections.crb#L10)

```rust
fn region_push(region:usize,value:i64)
```

Appends a byte or machine-word scalar according to the region element width.

### `region_push_row`

[collections.crb:19](../runtime/corbo/collections.crb#L19)

```rust
fn region_push_row(region:usize,row:usize)
```

Appends a row of machine words from caller storage; the source must cover the region element width.

### `region_read_row`

[collections.crb:28](../runtime/corbo/collections.crb#L28)

```rust
fn region_read_row(region:usize,index:usize,field:usize)->i64
```

Reads a signed word in a checked row/field position; invalid positions terminate.

### `region_append`

[collections.crb:35](../runtime/corbo/collections.crb#L35)

```rust
fn region_append(region:usize,data:usize,count:usize)
```

Appends count bytes through checked element growth; source must contain count readable bytes.

### `region_read`

[collections.crb:46](../runtime/corbo/collections.crb#L46)

```rust
fn region_read(region:usize,index:usize)->i64
```

Reads a checked byte or machine-word element and returns its signed bit representation.

### `value_region_append`

[collections.crb:58](../runtime/corbo/collections.crb#L58)

```rust
fn value_region_append(region:usize,data:usize,count:usize)
```

Grows byte storage through the synchronized path, then copies a readable source range into the new tail.

### `vector_remove`

[collections.crb:71](../runtime/corbo/collections.crb#L71)

```rust
fn vector_remove(region:usize,index:u64,out:usize)
```

Moves the selected element into out and shifts the remaining tail; out must hold one element and index must be live.

### `vector_pop`

[collections.crb:83](../runtime/corbo/collections.crb#L83)

```rust
fn vector_pop(region:usize,out:usize)->bool
```

Moves the last element into out and shortens the region; returns false without writing when empty.

### `destroy_owned_region`

[collections.crb:93](../runtime/corbo/collections.crb#L93)

```rust
fn destroy_owned_region(region:usize)
```

Destroys pooled elements from the last slot to the first, then releases the vector's region.

### `map_align`

[collections.crb:102](../runtime/corbo/collections.crb#L102)

```rust
fn map_align(bytes:usize)->usize
```

Rounds a map header or entry width to max_align_t, terminating on overflow.

### `map_new`

[collections.crb:110](../runtime/corbo/collections.crb#L110)

```rust
fn map_new(width:usize,dispose:usize)->usize
```

Maps a map descriptor and initializes its stable region storage with an optional element cleanup callback.

### `map_extend`

[collections.crb:122](../runtime/corbo/collections.crb#L122)

```rust
fn map_extend(map:usize,bytes:usize)
```

Commits additional bytes in a map region without moving existing entries; capacity failure terminates.

### `map_link`

[collections.crb:132](../runtime/corbo/collections.crb#L132)

```rust
fn map_link(map:usize,key:u64)->usize
```

Returns the bucket-chain link containing key or the insertion link at its end; bucket storage must be initialized.

### `map_get`

[collections.crb:147](../runtime/corbo/collections.crb#L147)

```rust
fn map_get(map:usize,key:u64)->usize
```

Returns the stored value address for key, or zero when absent; the map retains ownership.

### `map_insert`

[collections.crb:160](../runtime/corbo/collections.crb#L160)

```rust
fn map_insert(map:usize,key:u64,incoming:usize,previous:usize)->bool
```

Moves incoming bytes into a stable entry. Returns true and moves the replaced bytes into previous when the key exists.

### `map_remove`

[collections.crb:195](../runtime/corbo/collections.crb#L195)

```rust
fn map_remove(map:usize,key:u64,previous:usize)->bool
```

Unlinks key and moves its value into previous; returns false without writing when absent and indexes the freed slot for reuse.

### `map_drop`

[collections.crb:214](../runtime/corbo/collections.crb#L214)

```rust
fn map_drop(slot:usize)
```

Clears the caller's map pointer, destroys remaining values with dispose, then releases payload and descriptor storage.


## `runtime::completion`

Each request keeps its task link until dequeue; clear that link before publishing readiness.

### `completion_events`

[completion.crb:4](../runtime/corbo/completion.crb#L4)

```rust
fn completion_events(unused:usize)->usize
```

Receives per-operation completion records and resumes their task roots under the scheduler lock.

### `completion_initialize`

[completion.crb:40](../runtime/corbo/completion.crb#L40)

```rust
fn completion_initialize()
```

Creates the completion port and its event thread once, recording initialization errors.

### `corbo_socket_attach`

[completion.crb:56](../runtime/corbo/completion.crb#L56)

```rust
fn corbo_socket_attach(descriptor:u64)->i64
```

Associates a socket with the runtime completion port and returns the platform status.

### `corbo_socket_complete`

[completion.crb:65](../runtime/corbo/completion.crb#L65)

```rust
fn corbo_socket_complete(child:usize,descriptor:u64,address:usize,out:usize)->bool
```

Submits or observes one operation-specific completion request and coordinates its task wakeup without sharing request state.


## `runtime::completion_primitives`

Typed bindings to target completion ports; operation storage must remain stable until completion.

### `once_completion`

[completion_primitives.crb:6](../runtime/corbo/completion_primitives.crb#L6)

```rust
fn once_completion()
```

Runs completion-port initialization once with pthread_once.

### `pointer_completion_events`

[completion_primitives.crb:14](../runtime/corbo/completion_primitives.crb#L14)

```rust
fn pointer_completion_events()->usize
```

Returns the completion_events callback address for the matching native ABI.
The caller must invoke it through the exact declared function-pointer type.

### `completion_create`

[completion_primitives.crb:22](../runtime/corbo/completion_primitives.crb#L22)

```rust
fn completion_create()->usize
```

Creates the target completion-port object, returning the platform handle/error encoding.

### `completion_next`

[completion_primitives.crb:30](../runtime/corbo/completion_primitives.crb#L30)

```rust
fn completion_next(port:usize)->usize
```

Waits for the next operation-specific completion record through the target ABI.

### `completion_attach`

[completion_primitives.crb:38](../runtime/corbo/completion_primitives.crb#L38)

```rust
fn completion_attach(port:usize, descriptor:u64)->i64
```

Associates a native socket handle with a completion port through the target ABI.

### `completion_submit`

[completion_primitives.crb:46](../runtime/corbo/completion_primitives.crb#L46)

```rust
fn completion_submit(address:usize)->i64
```

Passes a stable operation descriptor to the target completion submission primitive.

### `completion_close`

[completion_primitives.crb:54](../runtime/corbo/completion_primitives.crb#L54)

```rust
fn completion_close(port:usize)
```

Closes the native completion port after failed initialization.


## `runtime::memory`

Stable-address storage, aligned cursor allocation and intrusive region ownership.
Region descriptors remain fixed while linked; closed bands survive until their last region drops.

### `rounded`

[memory.crb:6](../runtime/corbo/memory.crb#L6)

```rust
fn rounded(bytes:usize)->usize
```

Rounds a byte count up to the OS page size; terminates if rounding would overflow.

### `storage_error`

[memory.crb:11](../runtime/corbo/memory.crb#L11)

```rust
fn storage_error()
```

Reports fixed datastack exhaustion or an invalid storage operation and terminates the process.

### `region_error`

[memory.crb:15](../runtime/corbo/memory.crb#L15)

```rust
fn region_error()
```

Reports an invalid or exhausted region operation and terminates the process.

### `reserve`

[memory.crb:19](../runtime/corbo/memory.crb#L19)

```rust
fn reserve(bytes:u64)
```

Reserves the calling thread's fixed datastack, initializes page metadata and commits storage on demand.

### `push`

[memory.crb:43](../runtime/corbo/memory.crb#L43)

```rust
fn push(size:usize,alignment:usize,count:usize)->usize
```

Reserves count aligned fixed-size elements at the current cursor; checks multiplication, alignment and capacity before advancing.

### `release`

[memory.crb:64](../runtime/corbo/memory.crb#L64)

```rust
fn release()
```

Unmaps the calling thread's fixed datastack after its values and workers have been cleaned up.

### `take`

[memory.crb:68](../runtime/corbo/memory.crb#L68)

```rust
fn take(used:usize,count:usize)->usize
```

Finds the first free flag in a count-element slot bitmap, marks it used and returns its index; exhaustion terminates.

### `magnitude`

[memory.crb:82](../runtime/corbo/memory.crb#L82)

```rust
fn magnitude(value:i64)->usize
```

Returns an unsigned magnitude without overflowing on the minimum signed 64-bit integer.

### `numeric`

[memory.crb:89](../runtime/corbo/memory.crb#L89)

```rust
fn numeric(op:i64,left:i64,right:i64)->i64
```

Evaluates the selected signed integer operation with the reference runtime's overflow and zero-divisor failures.

### `region_default_capacity`

[memory.crb:138](../runtime/corbo/memory.crb#L138)

```rust
fn region_default_capacity()->usize
```

Computes the region-stack byte budget from OS memory and CPU information, bounded by PTRDIFF_MAX.

### `region_metadata`

[memory.crb:163](../runtime/corbo/memory.crb#L163)

```rust
fn region_metadata()->usize
```

Maps zero-initialized RegionBand metadata independently of storage whose scope may end first.

### `region_reserve`

[memory.crb:171](../runtime/corbo/memory.crb#L171)

```rust
fn region_reserve(band:usize,bytes:usize,maximum:usize)
```

Reserves a virtual address range for a band and records its capacity and per-region limit; commits no payload yet.

### `region_release_band`

[memory.crb:184](../runtime/corbo/memory.crb#L184)

```rust
fn region_release_band(band:usize)
```

Unmaps an empty band and its separately mapped metadata when applicable; no active region may remain.

### `region_stride`

[memory.crb:191](../runtime/corbo/memory.crb#L191)

```rust
fn region_stride(bytes:usize)->usize
```

Rounds a region width to max_align_t with checked size arithmetic.

### `region_enter`

[memory.crb:199](../runtime/corbo/memory.crb#L199)

```rust
fn region_enter(bytes:usize,count:usize,inferred:usize)
```

Creates a child region scope with the explicit or inferred count; the caller holds the runtime lock.

### `region_restore`

[memory.crb:231](../runtime/corbo/memory.crb#L231)

```rust
fn region_restore(mark:usize)
```

Closes region scopes back to mark, releasing only empty bands so transferred live regions survive; requires the lock.

### `region_new`

[memory.crb:242](../runtime/corbo/memory.crb#L242)

```rust
fn region_new(region:usize,width:usize,owned:i32,dedicated:bool)
```

Links a stable descriptor into an available band or a dedicated band; owned regions store child-region cleanup links. Requires the runtime lock.

### `region_drop`

[memory.crb:305](../runtime/corbo/memory.crb#L305)

```rust
fn region_drop(region:usize)
```

Destroys owned child regions before unlinking this region and releasing an empty closed band; requires the runtime lock.

### `region_add`

[memory.crb:330](../runtime/corbo/memory.crb#L330)

```rust
fn region_add(region:usize)->usize
```

Commits pages as needed and returns one new element slot; terminates at the region limit. Requires the runtime lock.

### `region_release`

[memory.crb:350](../runtime/corbo/memory.crb#L350)

```rust
fn region_release()
```

Releases the global region band after its live values have been destroyed.

### `new_pool`

[memory.crb:357](../runtime/corbo/memory.crb#L357)

```rust
fn new_pool(slots:usize,bytes:usize,arms:usize)->usize
```

Allocates a pool descriptor, atomic occupancy bytes and fixed slots on the datastack; validates sizes and arm counts.

### `pool_take`

[memory.crb:377](../runtime/corbo/memory.crb#L377)

```rust
fn pool_take(out:usize,pool:usize,arm:usize)
```

Atomically claims a free slot in the requested arm, zeroes it and writes an Owned descriptor to out; exhaustion terminates.

### `put`

[memory.crb:396](../runtime/corbo/memory.crb#L396)

```rust
fn put(value:usize)
```

Calls a live allocation's typed cleanup callback before releasing its pool slot, then clears the descriptor's pool link.

### `value_region_new`

[memory.crb:408](../runtime/corbo/memory.crb#L408)

```rust
fn value_region_new(region:usize,width:usize,owned:i32,dedicated:bool)
```

Initializes a region while holding the shared runtime lock; the descriptor must remain at a stable address.

### `value_region_add`

[memory.crb:414](../runtime/corbo/memory.crb#L414)

```rust
fn value_region_add(region:usize)->usize
```

Appends one region slot under the runtime lock and returns its address.

### `value_region_drop`

[memory.crb:421](../runtime/corbo/memory.crb#L421)

```rust
fn value_region_drop(region:usize)
```

Unlinks and releases a region under the runtime lock after owned child cleanup.

### `scoped_region_enter`

[memory.crb:427](../runtime/corbo/memory.crb#L427)

```rust
fn scoped_region_enter(bytes:usize,count:usize,inferred:usize)
```

Enters a region scope under the runtime lock using explicit and inferred slot budgets.

### `scoped_region_restore`

[memory.crb:433](../runtime/corbo/memory.crb#L433)

```rust
fn scoped_region_restore(mark:usize)
```

Restores the saved region-scope mark under the runtime lock while preserving live transferred regions.

### `destroy_region`

[memory.crb:439](../runtime/corbo/memory.crb#L439)

```rust
fn destroy_region(pointer:usize)
```

Cleanup-callback adapter for a region descriptor; releases its payload through the synchronized region path.

### `dispose_owned`

[memory.crb:443](../runtime/corbo/memory.crb#L443)

```rust
fn dispose_owned(pointer:usize)
```

Cleanup-callback adapter that destroys and releases the Owned descriptor at pointer.


## `runtime::primitives`

Unchecked C ABI field access, atomics, OS mappings and typed callbacks.
All raw addresses must remain live and aligned; callers provide ownership and locking.

### `g_Region_data`

[primitives.crb:8](../runtime/corbo/primitives.crb#L8)

```rust
fn g_Region_data(pointer:usize)->usize
```

Reads payload base address in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Region_data`

[primitives.crb:17](../runtime/corbo/primitives.crb#L17)

```rust
fn s_Region_data(pointer:usize, value:usize)
```

Writes payload base address in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Region_data`

[primitives.crb:25](../runtime/corbo/primitives.crb#L25)

```rust
fn a_Region_data(pointer:usize)->usize
```

Returns the address of payload base address in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Region_len`

[primitives.crb:34](../runtime/corbo/primitives.crb#L34)

```rust
fn g_Region_len(pointer:usize)->usize
```

Reads live element count in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Region_len`

[primitives.crb:43](../runtime/corbo/primitives.crb#L43)

```rust
fn s_Region_len(pointer:usize, value:usize)
```

Writes live element count in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Region_len`

[primitives.crb:51](../runtime/corbo/primitives.crb#L51)

```rust
fn a_Region_len(pointer:usize)->usize
```

Returns the address of live element count in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Region_offset`

[primitives.crb:60](../runtime/corbo/primitives.crb#L60)

```rust
fn g_Region_offset(pointer:usize)->usize
```

Reads byte offset within its band in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Region_offset`

[primitives.crb:69](../runtime/corbo/primitives.crb#L69)

```rust
fn s_Region_offset(pointer:usize, value:usize)
```

Writes byte offset within its band in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Region_offset`

[primitives.crb:77](../runtime/corbo/primitives.crb#L77)

```rust
fn a_Region_offset(pointer:usize)->usize
```

Returns the address of byte offset within its band in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Region_bytes`

[primitives.crb:86](../runtime/corbo/primitives.crb#L86)

```rust
fn g_Region_bytes(pointer:usize)->usize
```

Reads maximum payload byte extent in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Region_bytes`

[primitives.crb:95](../runtime/corbo/primitives.crb#L95)

```rust
fn s_Region_bytes(pointer:usize, value:usize)
```

Writes maximum payload byte extent in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Region_bytes`

[primitives.crb:103](../runtime/corbo/primitives.crb#L103)

```rust
fn a_Region_bytes(pointer:usize)->usize
```

Returns the address of maximum payload byte extent in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Region_width`

[primitives.crb:112](../runtime/corbo/primitives.crb#L112)

```rust
fn g_Region_width(pointer:usize)->usize
```

Reads bytes per stored element in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Region_width`

[primitives.crb:121](../runtime/corbo/primitives.crb#L121)

```rust
fn s_Region_width(pointer:usize, value:usize)
```

Writes bytes per stored element in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Region_width`

[primitives.crb:129](../runtime/corbo/primitives.crb#L129)

```rust
fn a_Region_width(pointer:usize)->usize
```

Returns the address of bytes per stored element in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Region_next`

[primitives.crb:138](../runtime/corbo/primitives.crb#L138)

```rust
fn g_Region_next(pointer:usize)->usize
```

Reads next active-region link in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Region_next`

[primitives.crb:147](../runtime/corbo/primitives.crb#L147)

```rust
fn s_Region_next(pointer:usize, value:usize)
```

Writes next active-region link in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Region_next`

[primitives.crb:155](../runtime/corbo/primitives.crb#L155)

```rust
fn a_Region_next(pointer:usize)->usize
```

Returns the address of next active-region link in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Region_band`

[primitives.crb:164](../runtime/corbo/primitives.crb#L164)

```rust
fn g_Region_band(pointer:usize)->usize
```

Reads containing band link in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Region_band`

[primitives.crb:173](../runtime/corbo/primitives.crb#L173)

```rust
fn s_Region_band(pointer:usize, value:usize)
```

Writes containing band link in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Region_band`

[primitives.crb:181](../runtime/corbo/primitives.crb#L181)

```rust
fn a_Region_band(pointer:usize)->usize
```

Returns the address of containing band link in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Region_owned`

[primitives.crb:190](../runtime/corbo/primitives.crb#L190)

```rust
fn g_Region_owned(pointer:usize)->i32
```

Reads recursive child-region cleanup mode in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Region_owned`

[primitives.crb:199](../runtime/corbo/primitives.crb#L199)

```rust
fn s_Region_owned(pointer:usize, value:i32)
```

Writes recursive child-region cleanup mode in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_Region`

[primitives.crb:206](../runtime/corbo/primitives.crb#L206)

```rust
fn size_Region()->usize
```

Returns the C ABI size in bytes of Region on this target.

### `align_Region`

[primitives.crb:214](../runtime/corbo/primitives.crb#L214)

```rust
fn align_Region()->usize
```

Returns the required C ABI alignment of Region on this target.

### `g_RegionBand_base`

[primitives.crb:223](../runtime/corbo/primitives.crb#L223)

```rust
fn g_RegionBand_base(pointer:usize)->usize
```

Reads reserved virtual-memory base in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionBand_base`

[primitives.crb:232](../runtime/corbo/primitives.crb#L232)

```rust
fn s_RegionBand_base(pointer:usize, value:usize)
```

Writes reserved virtual-memory base in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionBand_base`

[primitives.crb:240](../runtime/corbo/primitives.crb#L240)

```rust
fn a_RegionBand_base(pointer:usize)->usize
```

Returns the address of reserved virtual-memory base in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionBand_capacity`

[primitives.crb:249](../runtime/corbo/primitives.crb#L249)

```rust
fn g_RegionBand_capacity(pointer:usize)->usize
```

Reads reserved byte capacity in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionBand_capacity`

[primitives.crb:258](../runtime/corbo/primitives.crb#L258)

```rust
fn s_RegionBand_capacity(pointer:usize, value:usize)
```

Writes reserved byte capacity in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionBand_capacity`

[primitives.crb:266](../runtime/corbo/primitives.crb#L266)

```rust
fn a_RegionBand_capacity(pointer:usize)->usize
```

Returns the address of reserved byte capacity in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionBand_committed`

[primitives.crb:275](../runtime/corbo/primitives.crb#L275)

```rust
fn g_RegionBand_committed(pointer:usize)->usize
```

Reads committed byte boundary in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionBand_committed`

[primitives.crb:284](../runtime/corbo/primitives.crb#L284)

```rust
fn s_RegionBand_committed(pointer:usize, value:usize)
```

Writes committed byte boundary in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionBand_committed`

[primitives.crb:292](../runtime/corbo/primitives.crb#L292)

```rust
fn a_RegionBand_committed(pointer:usize)->usize
```

Returns the address of committed byte boundary in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionBand_limit`

[primitives.crb:301](../runtime/corbo/primitives.crb#L301)

```rust
fn g_RegionBand_limit(pointer:usize)->usize
```

Reads per-region byte limit in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionBand_limit`

[primitives.crb:310](../runtime/corbo/primitives.crb#L310)

```rust
fn s_RegionBand_limit(pointer:usize, value:usize)
```

Writes per-region byte limit in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionBand_limit`

[primitives.crb:318](../runtime/corbo/primitives.crb#L318)

```rust
fn a_RegionBand_limit(pointer:usize)->usize
```

Returns the address of per-region byte limit in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionBand_active`

[primitives.crb:327](../runtime/corbo/primitives.crb#L327)

```rust
fn g_RegionBand_active(pointer:usize)->usize
```

Reads ordered active-region list in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionBand_active`

[primitives.crb:336](../runtime/corbo/primitives.crb#L336)

```rust
fn s_RegionBand_active(pointer:usize, value:usize)
```

Writes ordered active-region list in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionBand_active`

[primitives.crb:344](../runtime/corbo/primitives.crb#L344)

```rust
fn a_RegionBand_active(pointer:usize)->usize
```

Returns the address of ordered active-region list in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionBand_parent`

[primitives.crb:353](../runtime/corbo/primitives.crb#L353)

```rust
fn g_RegionBand_parent(pointer:usize)->usize
```

Reads parent region-scope link in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionBand_parent`

[primitives.crb:362](../runtime/corbo/primitives.crb#L362)

```rust
fn s_RegionBand_parent(pointer:usize, value:usize)
```

Writes parent region-scope link in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionBand_parent`

[primitives.crb:370](../runtime/corbo/primitives.crb#L370)

```rust
fn a_RegionBand_parent(pointer:usize)->usize
```

Returns the address of parent region-scope link in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionBand_closed`

[primitives.crb:379](../runtime/corbo/primitives.crb#L379)

```rust
fn g_RegionBand_closed(pointer:usize)->i32
```

Reads closed-scope flag in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionBand_closed`

[primitives.crb:388](../runtime/corbo/primitives.crb#L388)

```rust
fn s_RegionBand_closed(pointer:usize, value:i32)
```

Writes closed-scope flag in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_RegionBand`

[primitives.crb:395](../runtime/corbo/primitives.crb#L395)

```rust
fn size_RegionBand()->usize
```

Returns the C ABI size in bytes of RegionBand on this target.

### `align_RegionBand`

[primitives.crb:403](../runtime/corbo/primitives.crb#L403)

```rust
fn align_RegionBand()->usize
```

Returns the required C ABI alignment of RegionBand on this target.

### `g_Pools_cap`

[primitives.crb:412](../runtime/corbo/primitives.crb#L412)

```rust
fn g_Pools_cap(pointer:usize)->usize
```

Reads slot count per arm in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Pools_cap`

[primitives.crb:421](../runtime/corbo/primitives.crb#L421)

```rust
fn s_Pools_cap(pointer:usize, value:usize)
```

Writes slot count per arm in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Pools_cap`

[primitives.crb:429](../runtime/corbo/primitives.crb#L429)

```rust
fn a_Pools_cap(pointer:usize)->usize
```

Returns the address of slot count per arm in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Pools_stride`

[primitives.crb:438](../runtime/corbo/primitives.crb#L438)

```rust
fn g_Pools_stride(pointer:usize)->usize
```

Reads aligned bytes per slot in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Pools_stride`

[primitives.crb:447](../runtime/corbo/primitives.crb#L447)

```rust
fn s_Pools_stride(pointer:usize, value:usize)
```

Writes aligned bytes per slot in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Pools_stride`

[primitives.crb:455](../runtime/corbo/primitives.crb#L455)

```rust
fn a_Pools_stride(pointer:usize)->usize
```

Returns the address of aligned bytes per slot in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Pools_arms`

[primitives.crb:464](../runtime/corbo/primitives.crb#L464)

```rust
fn g_Pools_arms(pointer:usize)->usize
```

Reads enum-arm count in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Pools_arms`

[primitives.crb:473](../runtime/corbo/primitives.crb#L473)

```rust
fn s_Pools_arms(pointer:usize, value:usize)
```

Writes enum-arm count in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Pools_arms`

[primitives.crb:481](../runtime/corbo/primitives.crb#L481)

```rust
fn a_Pools_arms(pointer:usize)->usize
```

Returns the address of enum-arm count in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Pools_data`

[primitives.crb:490](../runtime/corbo/primitives.crb#L490)

```rust
fn g_Pools_data(pointer:usize)->usize
```

Reads stable slot-storage base in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Pools_data`

[primitives.crb:499](../runtime/corbo/primitives.crb#L499)

```rust
fn s_Pools_data(pointer:usize, value:usize)
```

Writes stable slot-storage base in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Pools_data`

[primitives.crb:507](../runtime/corbo/primitives.crb#L507)

```rust
fn a_Pools_data(pointer:usize)->usize
```

Returns the address of stable slot-storage base in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Pools_used`

[primitives.crb:516](../runtime/corbo/primitives.crb#L516)

```rust
fn g_Pools_used(pointer:usize)->usize
```

Reads atomic occupancy-byte array in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Pools_used`

[primitives.crb:525](../runtime/corbo/primitives.crb#L525)

```rust
fn s_Pools_used(pointer:usize, value:usize)
```

Writes atomic occupancy-byte array in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Pools_used`

[primitives.crb:533](../runtime/corbo/primitives.crb#L533)

```rust
fn a_Pools_used(pointer:usize)->usize
```

Returns the address of atomic occupancy-byte array in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_Pools`

[primitives.crb:541](../runtime/corbo/primitives.crb#L541)

```rust
fn size_Pools()->usize
```

Returns the C ABI size in bytes of Pools on this target.

### `align_Pools`

[primitives.crb:549](../runtime/corbo/primitives.crb#L549)

```rust
fn align_Pools()->usize
```

Returns the required C ABI alignment of Pools on this target.

### `g_Owned_pool`

[primitives.crb:558](../runtime/corbo/primitives.crb#L558)

```rust
fn g_Owned_pool(pointer:usize)->usize
```

Reads source pool link, zero after release in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Owned_pool`

[primitives.crb:567](../runtime/corbo/primitives.crb#L567)

```rust
fn s_Owned_pool(pointer:usize, value:usize)
```

Writes source pool link, zero after release in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Owned_pool`

[primitives.crb:575](../runtime/corbo/primitives.crb#L575)

```rust
fn a_Owned_pool(pointer:usize)->usize
```

Returns the address of source pool link, zero after release in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Owned_slot`

[primitives.crb:584](../runtime/corbo/primitives.crb#L584)

```rust
fn g_Owned_slot(pointer:usize)->usize
```

Reads payload slot address in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Owned_slot`

[primitives.crb:593](../runtime/corbo/primitives.crb#L593)

```rust
fn s_Owned_slot(pointer:usize, value:usize)
```

Writes payload slot address in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Owned_slot`

[primitives.crb:601](../runtime/corbo/primitives.crb#L601)

```rust
fn a_Owned_slot(pointer:usize)->usize
```

Returns the address of payload slot address in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Owned_index`

[primitives.crb:610](../runtime/corbo/primitives.crb#L610)

```rust
fn g_Owned_index(pointer:usize)->usize
```

Reads physical slot index in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Owned_index`

[primitives.crb:619](../runtime/corbo/primitives.crb#L619)

```rust
fn s_Owned_index(pointer:usize, value:usize)
```

Writes physical slot index in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Owned_index`

[primitives.crb:627](../runtime/corbo/primitives.crb#L627)

```rust
fn a_Owned_index(pointer:usize)->usize
```

Returns the address of physical slot index in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Owned_destroy`

[primitives.crb:636](../runtime/corbo/primitives.crb#L636)

```rust
fn g_Owned_destroy(pointer:usize)->usize
```

Reads typed payload destructor callback in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Owned_destroy`

[primitives.crb:645](../runtime/corbo/primitives.crb#L645)

```rust
fn s_Owned_destroy(pointer:usize, value:usize)
```

Writes typed payload destructor callback in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Owned_destroy`

[primitives.crb:653](../runtime/corbo/primitives.crb#L653)

```rust
fn a_Owned_destroy(pointer:usize)->usize
```

Returns the address of typed payload destructor callback in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_Owned`

[primitives.crb:661](../runtime/corbo/primitives.crb#L661)

```rust
fn size_Owned()->usize
```

Returns the C ABI size in bytes of Owned on this target.

### `align_Owned`

[primitives.crb:669](../runtime/corbo/primitives.crb#L669)

```rust
fn align_Owned()->usize
```

Returns the required C ABI alignment of Owned on this target.

### `g_RegionOwner_region`

[primitives.crb:678](../runtime/corbo/primitives.crb#L678)

```rust
fn g_RegionOwner_region(pointer:usize)->usize
```

Reads owned child-region link in a live RegionOwner ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionOwner_region`

[primitives.crb:687](../runtime/corbo/primitives.crb#L687)

```rust
fn s_RegionOwner_region(pointer:usize, value:usize)
```

Writes owned child-region link in a live RegionOwner ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionOwner_region`

[primitives.crb:695](../runtime/corbo/primitives.crb#L695)

```rust
fn a_RegionOwner_region(pointer:usize)->usize
```

Returns the address of owned child-region link in a live RegionOwner ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionOwner_slot`

[primitives.crb:704](../runtime/corbo/primitives.crb#L704)

```rust
fn g_RegionOwner_slot(pointer:usize)->usize
```

Reads address of the child's live-slot flag in a live RegionOwner ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionOwner_slot`

[primitives.crb:713](../runtime/corbo/primitives.crb#L713)

```rust
fn s_RegionOwner_slot(pointer:usize, value:usize)
```

Writes address of the child's live-slot flag in a live RegionOwner ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionOwner_slot`

[primitives.crb:721](../runtime/corbo/primitives.crb#L721)

```rust
fn a_RegionOwner_slot(pointer:usize)->usize
```

Returns the address of address of the child's live-slot flag in a live RegionOwner ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_RegionOwner`

[primitives.crb:729](../runtime/corbo/primitives.crb#L729)

```rust
fn size_RegionOwner()->usize
```

Returns the C ABI size in bytes of RegionOwner on this target.

### `align_RegionOwner`

[primitives.crb:737](../runtime/corbo/primitives.crb#L737)

```rust
fn align_RegionOwner()->usize
```

Returns the required C ABI alignment of RegionOwner on this target.

### `a_RegionalMap_region`

[primitives.crb:746](../runtime/corbo/primitives.crb#L746)

```rust
fn a_RegionalMap_region(pointer:usize)->usize
```

Returns the address of stable entry-storage region in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionalMap_width`

[primitives.crb:755](../runtime/corbo/primitives.crb#L755)

```rust
fn g_RegionalMap_width(pointer:usize)->usize
```

Reads value byte width in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionalMap_width`

[primitives.crb:764](../runtime/corbo/primitives.crb#L764)

```rust
fn s_RegionalMap_width(pointer:usize, value:usize)
```

Writes value byte width in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionalMap_width`

[primitives.crb:772](../runtime/corbo/primitives.crb#L772)

```rust
fn a_RegionalMap_width(pointer:usize)->usize
```

Returns the address of value byte width in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionalMap_free_slot`

[primitives.crb:781](../runtime/corbo/primitives.crb#L781)

```rust
fn g_RegionalMap_free_slot(pointer:usize)->usize
```

Reads free-entry offset list head in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionalMap_free_slot`

[primitives.crb:790](../runtime/corbo/primitives.crb#L790)

```rust
fn s_RegionalMap_free_slot(pointer:usize, value:usize)
```

Writes free-entry offset list head in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionalMap_free_slot`

[primitives.crb:798](../runtime/corbo/primitives.crb#L798)

```rust
fn a_RegionalMap_free_slot(pointer:usize)->usize
```

Returns the address of free-entry offset list head in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionalMap_dispose`

[primitives.crb:807](../runtime/corbo/primitives.crb#L807)

```rust
fn g_RegionalMap_dispose(pointer:usize)->usize
```

Reads value cleanup callback in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionalMap_dispose`

[primitives.crb:816](../runtime/corbo/primitives.crb#L816)

```rust
fn s_RegionalMap_dispose(pointer:usize, value:usize)
```

Writes value cleanup callback in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionalMap_dispose`

[primitives.crb:824](../runtime/corbo/primitives.crb#L824)

```rust
fn a_RegionalMap_dispose(pointer:usize)->usize
```

Returns the address of value cleanup callback in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_RegionalMap`

[primitives.crb:832](../runtime/corbo/primitives.crb#L832)

```rust
fn size_RegionalMap()->usize
```

Returns the C ABI size in bytes of RegionalMap on this target.

### `align_RegionalMap`

[primitives.crb:840](../runtime/corbo/primitives.crb#L840)

```rust
fn align_RegionalMap()->usize
```

Returns the required C ABI alignment of RegionalMap on this target.

### `g_MapEntry_key`

[primitives.crb:849](../runtime/corbo/primitives.crb#L849)

```rust
fn g_MapEntry_key(pointer:usize)->u64
```

Reads normalized integer key bits in a live MapEntry ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_MapEntry_key`

[primitives.crb:858](../runtime/corbo/primitives.crb#L858)

```rust
fn s_MapEntry_key(pointer:usize, value:u64)
```

Writes normalized integer key bits in a live MapEntry ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_MapEntry_next`

[primitives.crb:866](../runtime/corbo/primitives.crb#L866)

```rust
fn g_MapEntry_next(pointer:usize)->usize
```

Reads next bucket-chain or free-list byte offset in a live MapEntry ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_MapEntry_next`

[primitives.crb:875](../runtime/corbo/primitives.crb#L875)

```rust
fn s_MapEntry_next(pointer:usize, value:usize)
```

Writes next bucket-chain or free-list byte offset in a live MapEntry ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_MapEntry_next`

[primitives.crb:883](../runtime/corbo/primitives.crb#L883)

```rust
fn a_MapEntry_next(pointer:usize)->usize
```

Returns the address of next bucket-chain or free-list byte offset in a live MapEntry ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_MapEntry`

[primitives.crb:891](../runtime/corbo/primitives.crb#L891)

```rust
fn size_MapEntry()->usize
```

Returns the C ABI size in bytes of MapEntry on this target.

### `align_MapEntry`

[primitives.crb:899](../runtime/corbo/primitives.crb#L899)

```rust
fn align_MapEntry()->usize
```

Returns the required C ABI alignment of MapEntry on this target.

### `g_Task_pc`

[primitives.crb:908](../runtime/corbo/primitives.crb#L908)

```rust
fn g_Task_pc(pointer:usize)->usize
```

Reads resume-state program counter in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_pc`

[primitives.crb:917](../runtime/corbo/primitives.crb#L917)

```rust
fn s_Task_pc(pointer:usize, value:usize)
```

Writes resume-state program counter in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_pc`

[primitives.crb:925](../runtime/corbo/primitives.crb#L925)

```rust
fn a_Task_pc(pointer:usize)->usize
```

Returns the address of resume-state program counter in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_poll`

[primitives.crb:934](../runtime/corbo/primitives.crb#L934)

```rust
fn g_Task_poll(pointer:usize)->usize
```

Reads typed poll/clear callback in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_poll`

[primitives.crb:943](../runtime/corbo/primitives.crb#L943)

```rust
fn s_Task_poll(pointer:usize, value:usize)
```

Writes typed poll/clear callback in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_poll`

[primitives.crb:951](../runtime/corbo/primitives.crb#L951)

```rust
fn a_Task_poll(pointer:usize)->usize
```

Returns the address of typed poll/clear callback in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_next`

[primitives.crb:960](../runtime/corbo/primitives.crb#L960)

```rust
fn g_Task_next(pointer:usize)->usize
```

Reads ready-queue next link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_next`

[primitives.crb:969](../runtime/corbo/primitives.crb#L969)

```rust
fn s_Task_next(pointer:usize, value:usize)
```

Writes ready-queue next link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_next`

[primitives.crb:977](../runtime/corbo/primitives.crb#L977)

```rust
fn a_Task_next(pointer:usize)->usize
```

Returns the address of ready-queue next link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_failed`

[primitives.crb:986](../runtime/corbo/primitives.crb#L986)

```rust
fn g_Task_failed(pointer:usize)->bool
```

Reads launch-failure flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_failed`

[primitives.crb:995](../runtime/corbo/primitives.crb#L995)

```rust
fn s_Task_failed(pointer:usize, value:bool)
```

Writes launch-failure flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_done`

[primitives.crb:1003](../runtime/corbo/primitives.crb#L1003)

```rust
fn g_Task_done(pointer:usize)->bool
```

Reads completion-publication flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_done`

[primitives.crb:1012](../runtime/corbo/primitives.crb#L1012)

```rust
fn s_Task_done(pointer:usize, value:bool)
```

Writes completion-publication flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_abandoned`

[primitives.crb:1020](../runtime/corbo/primitives.crb#L1020)

```rust
fn g_Task_abandoned(pointer:usize)->bool
```

Reads worker-owned final-cleanup flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_abandoned`

[primitives.crb:1029](../runtime/corbo/primitives.crb#L1029)

```rust
fn s_Task_abandoned(pointer:usize, value:bool)
```

Writes worker-owned final-cleanup flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_discard`

[primitives.crb:1037](../runtime/corbo/primitives.crb#L1037)

```rust
fn g_Task_discard(pointer:usize)->usize
```

Reads typed abandoned-task cleanup callback in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_discard`

[primitives.crb:1046](../runtime/corbo/primitives.crb#L1046)

```rust
fn s_Task_discard(pointer:usize, value:usize)
```

Writes typed abandoned-task cleanup callback in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_discard`

[primitives.crb:1054](../runtime/corbo/primitives.crb#L1054)

```rust
fn a_Task_discard(pointer:usize)->usize
```

Returns the address of typed abandoned-task cleanup callback in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_root`

[primitives.crb:1063](../runtime/corbo/primitives.crb#L1063)

```rust
fn g_Task_root(pointer:usize)->usize
```

Reads outer polling-root link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_root`

[primitives.crb:1072](../runtime/corbo/primitives.crb#L1072)

```rust
fn s_Task_root(pointer:usize, value:usize)
```

Writes outer polling-root link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_root`

[primitives.crb:1080](../runtime/corbo/primitives.crb#L1080)

```rust
fn a_Task_root(pointer:usize)->usize
```

Returns the address of outer polling-root link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_waiter`

[primitives.crb:1089](../runtime/corbo/primitives.crb#L1089)

```rust
fn g_Task_waiter(pointer:usize)->usize
```

Reads dependent polling-root link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_waiter`

[primitives.crb:1098](../runtime/corbo/primitives.crb#L1098)

```rust
fn s_Task_waiter(pointer:usize, value:usize)
```

Writes dependent polling-root link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_waiter`

[primitives.crb:1106](../runtime/corbo/primitives.crb#L1106)

```rust
fn a_Task_waiter(pointer:usize)->usize
```

Returns the address of dependent polling-root link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_io_ready`

[primitives.crb:1115](../runtime/corbo/primitives.crb#L1115)

```rust
fn g_Task_io_ready(pointer:usize)->bool
```

Reads readiness-publication flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_io_ready`

[primitives.crb:1124](../runtime/corbo/primitives.crb#L1124)

```rust
fn s_Task_io_ready(pointer:usize, value:bool)
```

Writes readiness-publication flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_io_registered`

[primitives.crb:1132](../runtime/corbo/primitives.crb#L1132)

```rust
fn g_Task_io_registered(pointer:usize)->bool
```

Reads active-wait registration flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_io_registered`

[primitives.crb:1141](../runtime/corbo/primitives.crb#L1141)

```rust
fn s_Task_io_registered(pointer:usize, value:bool)
```

Writes active-wait registration flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_io_socket`

[primitives.crb:1149](../runtime/corbo/primitives.crb#L1149)

```rust
fn g_Task_io_socket(pointer:usize)->u64
```

Reads native socket identifier in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_io_socket`

[primitives.crb:1158](../runtime/corbo/primitives.crb#L1158)

```rust
fn s_Task_io_socket(pointer:usize, value:u64)
```

Writes native socket identifier in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_io_write`

[primitives.crb:1166](../runtime/corbo/primitives.crb#L1166)

```rust
fn g_Task_io_write(pointer:usize)->bool
```

Reads write-interest selector in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_io_write`

[primitives.crb:1175](../runtime/corbo/primitives.crb#L1175)

```rust
fn s_Task_io_write(pointer:usize, value:bool)
```

Writes write-interest selector in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_io_next`

[primitives.crb:1183](../runtime/corbo/primitives.crb#L1183)

```rust
fn g_Task_io_next(pointer:usize)->usize
```

Reads intrusive readiness-waiter link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_io_next`

[primitives.crb:1192](../runtime/corbo/primitives.crb#L1192)

```rust
fn s_Task_io_next(pointer:usize, value:usize)
```

Writes intrusive readiness-waiter link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_io_next`

[primitives.crb:1200](../runtime/corbo/primitives.crb#L1200)

```rust
fn a_Task_io_next(pointer:usize)->usize
```

Returns the address of intrusive readiness-waiter link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_io_token`

[primitives.crb:1209](../runtime/corbo/primitives.crb#L1209)

```rust
fn g_Task_io_token(pointer:usize)->usize
```

Reads readiness-generation token in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_io_token`

[primitives.crb:1218](../runtime/corbo/primitives.crb#L1218)

```rust
fn s_Task_io_token(pointer:usize, value:usize)
```

Writes readiness-generation token in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_io_token`

[primitives.crb:1226](../runtime/corbo/primitives.crb#L1226)

```rust
fn a_Task_io_token(pointer:usize)->usize
```

Returns the address of readiness-generation token in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_io_error`

[primitives.crb:1235](../runtime/corbo/primitives.crb#L1235)

```rust
fn g_Task_io_error(pointer:usize)->i64
```

Reads recorded platform I/O status in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_io_error`

[primitives.crb:1244](../runtime/corbo/primitives.crb#L1244)

```rust
fn s_Task_io_error(pointer:usize, value:i64)
```

Writes recorded platform I/O status in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_waiting`

[primitives.crb:1252](../runtime/corbo/primitives.crb#L1252)

```rust
fn g_Task_waiting(pointer:usize)->bool
```

Reads dependency-wait predicate in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_waiting`

[primitives.crb:1261](../runtime/corbo/primitives.crb#L1261)

```rust
fn s_Task_waiting(pointer:usize, value:bool)
```

Writes dependency-wait predicate in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_parked`

[primitives.crb:1269](../runtime/corbo/primitives.crb#L1269)

```rust
fn g_Task_parked(pointer:usize)->bool
```

Reads removed-from-ready-queue flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_parked`

[primitives.crb:1278](../runtime/corbo/primitives.crb#L1278)

```rust
fn s_Task_parked(pointer:usize, value:bool)
```

Writes removed-from-ready-queue flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_blocking`

[primitives.crb:1286](../runtime/corbo/primitives.crb#L1286)

```rust
fn g_Task_blocking(pointer:usize)->bool
```

Reads dedicated blocking-worker flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_blocking`

[primitives.crb:1295](../runtime/corbo/primitives.crb#L1295)

```rust
fn s_Task_blocking(pointer:usize, value:bool)
```

Writes dedicated blocking-worker flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_Task`

[primitives.crb:1302](../runtime/corbo/primitives.crb#L1302)

```rust
fn size_Task()->usize
```

Returns the C ABI size in bytes of Task on this target.

### `align_Task`

[primitives.crb:1310](../runtime/corbo/primitives.crb#L1310)

```rust
fn align_Task()->usize
```

Returns the required C ABI alignment of Task on this target.

### `a_TaskState_task`

[primitives.crb:1319](../runtime/corbo/primitives.crb#L1319)

```rust
fn a_TaskState_task(pointer:usize)->usize
```

Returns the address of scheduler header at offset zero in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskState_value`

[primitives.crb:1328](../runtime/corbo/primitives.crb#L1328)

```rust
fn a_TaskState_value(pointer:usize)->usize
```

Returns the address of inline scalar result storage in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_TaskState_payload`

[primitives.crb:1337](../runtime/corbo/primitives.crb#L1337)

```rust
fn g_TaskState_payload(pointer:usize)->usize
```

Reads aggregate result address in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskState_payload`

[primitives.crb:1346](../runtime/corbo/primitives.crb#L1346)

```rust
fn s_TaskState_payload(pointer:usize, value:usize)
```

Writes aggregate result address in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskState_payload`

[primitives.crb:1354](../runtime/corbo/primitives.crb#L1354)

```rust
fn a_TaskState_payload(pointer:usize)->usize
```

Returns the address of aggregate result address in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_TaskState_region`

[primitives.crb:1363](../runtime/corbo/primitives.crb#L1363)

```rust
fn g_TaskState_region(pointer:usize)->usize
```

Reads frame-storage region link in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskState_region`

[primitives.crb:1372](../runtime/corbo/primitives.crb#L1372)

```rust
fn s_TaskState_region(pointer:usize, value:usize)
```

Writes frame-storage region link in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskState_region`

[primitives.crb:1380](../runtime/corbo/primitives.crb#L1380)

```rust
fn a_TaskState_region(pointer:usize)->usize
```

Returns the address of frame-storage region link in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_TaskState_own_region`

[primitives.crb:1389](../runtime/corbo/primitives.crb#L1389)

```rust
fn g_TaskState_own_region(pointer:usize)->bool
```

Reads separate region-descriptor ownership flag in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskState_own_region`

[primitives.crb:1398](../runtime/corbo/primitives.crb#L1398)

```rust
fn s_TaskState_own_region(pointer:usize, value:bool)
```

Writes separate region-descriptor ownership flag in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_TaskState_dispose`

[primitives.crb:1406](../runtime/corbo/primitives.crb#L1406)

```rust
fn g_TaskState_dispose(pointer:usize)->usize
```

Reads typed capture/result cleanup callback in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskState_dispose`

[primitives.crb:1415](../runtime/corbo/primitives.crb#L1415)

```rust
fn s_TaskState_dispose(pointer:usize, value:usize)
```

Writes typed capture/result cleanup callback in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskState_dispose`

[primitives.crb:1423](../runtime/corbo/primitives.crb#L1423)

```rust
fn a_TaskState_dispose(pointer:usize)->usize
```

Returns the address of typed capture/result cleanup callback in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskState_classic`

[primitives.crb:1432](../runtime/corbo/primitives.crb#L1432)

```rust
fn a_TaskState_classic(pointer:usize)->usize
```

Returns the address of suspended thread-local datastack context in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_TaskState`

[primitives.crb:1440](../runtime/corbo/primitives.crb#L1440)

```rust
fn size_TaskState()->usize
```

Returns the C ABI size in bytes of TaskState on this target.

### `align_TaskState`

[primitives.crb:1448](../runtime/corbo/primitives.crb#L1448)

```rust
fn align_TaskState()->usize
```

Returns the required C ABI alignment of TaskState on this target.

### `g_TaskValue_state`

[primitives.crb:1457](../runtime/corbo/primitives.crb#L1457)

```rust
fn g_TaskValue_state(pointer:usize)->usize
```

Reads execution frame address in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskValue_state`

[primitives.crb:1466](../runtime/corbo/primitives.crb#L1466)

```rust
fn s_TaskValue_state(pointer:usize, value:usize)
```

Writes execution frame address in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskValue_state`

[primitives.crb:1474](../runtime/corbo/primitives.crb#L1474)

```rust
fn a_TaskValue_state(pointer:usize)->usize
```

Returns the address of execution frame address in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_TaskValue_storage`

[primitives.crb:1483](../runtime/corbo/primitives.crb#L1483)

```rust
fn g_TaskValue_storage(pointer:usize)->usize
```

Reads owned backing-region link in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskValue_storage`

[primitives.crb:1492](../runtime/corbo/primitives.crb#L1492)

```rust
fn s_TaskValue_storage(pointer:usize, value:usize)
```

Writes owned backing-region link in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskValue_storage`

[primitives.crb:1500](../runtime/corbo/primitives.crb#L1500)

```rust
fn a_TaskValue_storage(pointer:usize)->usize
```

Returns the address of owned backing-region link in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_TaskValue_poll`

[primitives.crb:1509](../runtime/corbo/primitives.crb#L1509)

```rust
fn g_TaskValue_poll(pointer:usize)->usize
```

Reads frame-specific poll callback in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskValue_poll`

[primitives.crb:1518](../runtime/corbo/primitives.crb#L1518)

```rust
fn s_TaskValue_poll(pointer:usize, value:usize)
```

Writes frame-specific poll callback in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskValue_poll`

[primitives.crb:1526](../runtime/corbo/primitives.crb#L1526)

```rust
fn a_TaskValue_poll(pointer:usize)->usize
```

Returns the address of frame-specific poll callback in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_TaskValue_native`

[primitives.crb:1535](../runtime/corbo/primitives.crb#L1535)

```rust
fn g_TaskValue_native(pointer:usize)->bool
```

Reads native-worker ownership selector in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskValue_native`

[primitives.crb:1544](../runtime/corbo/primitives.crb#L1544)

```rust
fn s_TaskValue_native(pointer:usize, value:bool)
```

Writes native-worker ownership selector in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_TaskValue`

[primitives.crb:1551](../runtime/corbo/primitives.crb#L1551)

```rust
fn size_TaskValue()->usize
```

Returns the C ABI size in bytes of TaskValue on this target.

### `align_TaskValue`

[primitives.crb:1559](../runtime/corbo/primitives.crb#L1559)

```rust
fn align_TaskValue()->usize
```

Returns the required C ABI alignment of TaskValue on this target.

### `g_TaskCompletion_ok`

[primitives.crb:1568](../runtime/corbo/primitives.crb#L1568)

```rust
fn g_TaskCompletion_ok(pointer:usize)->bool
```

Reads successful-launch/completion flag in a live TaskCompletion ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskCompletion_ok`

[primitives.crb:1577](../runtime/corbo/primitives.crb#L1577)

```rust
fn s_TaskCompletion_ok(pointer:usize, value:bool)
```

Writes successful-launch/completion flag in a live TaskCompletion ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskCompletion_value`

[primitives.crb:1585](../runtime/corbo/primitives.crb#L1585)

```rust
fn a_TaskCompletion_value(pointer:usize)->usize
```

Returns the address of moved scalar result bits in a live TaskCompletion ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_TaskCompletion`

[primitives.crb:1593](../runtime/corbo/primitives.crb#L1593)

```rust
fn size_TaskCompletion()->usize
```

Returns the C ABI size in bytes of TaskCompletion on this target.

### `align_TaskCompletion`

[primitives.crb:1601](../runtime/corbo/primitives.crb#L1601)

```rust
fn align_TaskCompletion()->usize
```

Returns the required C ABI alignment of TaskCompletion on this target.

### `g_ClassicStack_base`

[primitives.crb:1610](../runtime/corbo/primitives.crb#L1610)

```rust
fn g_ClassicStack_base(pointer:usize)->usize
```

Reads saved fixed-stack base in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_ClassicStack_base`

[primitives.crb:1619](../runtime/corbo/primitives.crb#L1619)

```rust
fn s_ClassicStack_base(pointer:usize, value:usize)
```

Writes saved fixed-stack base in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_ClassicStack_base`

[primitives.crb:1627](../runtime/corbo/primitives.crb#L1627)

```rust
fn a_ClassicStack_base(pointer:usize)->usize
```

Returns the address of saved fixed-stack base in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_ClassicStack_cursor`

[primitives.crb:1636](../runtime/corbo/primitives.crb#L1636)

```rust
fn g_ClassicStack_cursor(pointer:usize)->usize
```

Reads saved next free byte offset in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_ClassicStack_cursor`

[primitives.crb:1645](../runtime/corbo/primitives.crb#L1645)

```rust
fn s_ClassicStack_cursor(pointer:usize, value:usize)
```

Writes saved next free byte offset in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_ClassicStack_cursor`

[primitives.crb:1653](../runtime/corbo/primitives.crb#L1653)

```rust
fn a_ClassicStack_cursor(pointer:usize)->usize
```

Returns the address of saved next free byte offset in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_ClassicStack_limit`

[primitives.crb:1662](../runtime/corbo/primitives.crb#L1662)

```rust
fn g_ClassicStack_limit(pointer:usize)->usize
```

Reads saved fixed-stack capacity in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_ClassicStack_limit`

[primitives.crb:1671](../runtime/corbo/primitives.crb#L1671)

```rust
fn s_ClassicStack_limit(pointer:usize, value:usize)
```

Writes saved fixed-stack capacity in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_ClassicStack_limit`

[primitives.crb:1679](../runtime/corbo/primitives.crb#L1679)

```rust
fn a_ClassicStack_limit(pointer:usize)->usize
```

Returns the address of saved fixed-stack capacity in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_ClassicStack_committed`

[primitives.crb:1688](../runtime/corbo/primitives.crb#L1688)

```rust
fn g_ClassicStack_committed(pointer:usize)->usize
```

Reads saved committed-byte boundary in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_ClassicStack_committed`

[primitives.crb:1697](../runtime/corbo/primitives.crb#L1697)

```rust
fn s_ClassicStack_committed(pointer:usize, value:usize)
```

Writes saved committed-byte boundary in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_ClassicStack_committed`

[primitives.crb:1705](../runtime/corbo/primitives.crb#L1705)

```rust
fn a_ClassicStack_committed(pointer:usize)->usize
```

Returns the address of saved committed-byte boundary in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_ClassicStack_page_size`

[primitives.crb:1714](../runtime/corbo/primitives.crb#L1714)

```rust
fn g_ClassicStack_page_size(pointer:usize)->usize
```

Reads saved OS page size in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_ClassicStack_page_size`

[primitives.crb:1723](../runtime/corbo/primitives.crb#L1723)

```rust
fn s_ClassicStack_page_size(pointer:usize, value:usize)
```

Writes saved OS page size in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_ClassicStack_page_size`

[primitives.crb:1731](../runtime/corbo/primitives.crb#L1731)

```rust
fn a_ClassicStack_page_size(pointer:usize)->usize
```

Returns the address of saved OS page size in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_ClassicStack_mapped_size`

[primitives.crb:1740](../runtime/corbo/primitives.crb#L1740)

```rust
fn g_ClassicStack_mapped_size(pointer:usize)->usize
```

Reads saved mapping extent in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_ClassicStack_mapped_size`

[primitives.crb:1749](../runtime/corbo/primitives.crb#L1749)

```rust
fn s_ClassicStack_mapped_size(pointer:usize, value:usize)
```

Writes saved mapping extent in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_ClassicStack_mapped_size`

[primitives.crb:1757](../runtime/corbo/primitives.crb#L1757)

```rust
fn a_ClassicStack_mapped_size(pointer:usize)->usize
```

Returns the address of saved mapping extent in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_ClassicStack_band`

[primitives.crb:1766](../runtime/corbo/primitives.crb#L1766)

```rust
fn g_ClassicStack_band(pointer:usize)->usize
```

Reads saved region-scope link in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_ClassicStack_band`

[primitives.crb:1775](../runtime/corbo/primitives.crb#L1775)

```rust
fn s_ClassicStack_band(pointer:usize, value:usize)
```

Writes saved region-scope link in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_ClassicStack_band`

[primitives.crb:1783](../runtime/corbo/primitives.crb#L1783)

```rust
fn a_ClassicStack_band(pointer:usize)->usize
```

Returns the address of saved region-scope link in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_ClassicStack`

[primitives.crb:1791](../runtime/corbo/primitives.crb#L1791)

```rust
fn size_ClassicStack()->usize
```

Returns the C ABI size in bytes of ClassicStack on this target.

### `align_ClassicStack`

[primitives.crb:1799](../runtime/corbo/primitives.crb#L1799)

```rust
fn align_ClassicStack()->usize
```

Returns the required C ABI alignment of ClassicStack on this target.

### `a_NativeBox_region`

[primitives.crb:1808](../runtime/corbo/primitives.crb#L1808)

```rust
fn a_NativeBox_region(pointer:usize)->usize
```

Returns the address of embedded frame region at offset zero in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_NativeBox_state`

[primitives.crb:1817](../runtime/corbo/primitives.crb#L1817)

```rust
fn g_NativeBox_state(pointer:usize)->usize
```

Reads native frame address in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_NativeBox_state`

[primitives.crb:1826](../runtime/corbo/primitives.crb#L1826)

```rust
fn s_NativeBox_state(pointer:usize, value:usize)
```

Writes native frame address in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_NativeBox_state`

[primitives.crb:1834](../runtime/corbo/primitives.crb#L1834)

```rust
fn a_NativeBox_state(pointer:usize)->usize
```

Returns the address of native frame address in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_NativeBox_run`

[primitives.crb:1843](../runtime/corbo/primitives.crb#L1843)

```rust
fn g_NativeBox_run(pointer:usize)->usize
```

Reads native frame run callback in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_NativeBox_run`

[primitives.crb:1852](../runtime/corbo/primitives.crb#L1852)

```rust
fn s_NativeBox_run(pointer:usize, value:usize)
```

Writes native frame run callback in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_NativeBox_run`

[primitives.crb:1860](../runtime/corbo/primitives.crb#L1860)

```rust
fn a_NativeBox_run(pointer:usize)->usize
```

Returns the address of native frame run callback in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_NativeBox_abandoned`

[primitives.crb:1869](../runtime/corbo/primitives.crb#L1869)

```rust
fn g_NativeBox_abandoned(pointer:usize)->bool
```

Reads worker-owned cleanup flag in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_NativeBox_abandoned`

[primitives.crb:1878](../runtime/corbo/primitives.crb#L1878)

```rust
fn s_NativeBox_abandoned(pointer:usize, value:bool)
```

Writes worker-owned cleanup flag in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_NativeBox_dispose`

[primitives.crb:1886](../runtime/corbo/primitives.crb#L1886)

```rust
fn g_NativeBox_dispose(pointer:usize)->usize
```

Reads capture/result cleanup callback in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_NativeBox_dispose`

[primitives.crb:1895](../runtime/corbo/primitives.crb#L1895)

```rust
fn s_NativeBox_dispose(pointer:usize, value:usize)
```

Writes capture/result cleanup callback in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_NativeBox_dispose`

[primitives.crb:1903](../runtime/corbo/primitives.crb#L1903)

```rust
fn a_NativeBox_dispose(pointer:usize)->usize
```

Returns the address of capture/result cleanup callback in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_NativeBox`

[primitives.crb:1911](../runtime/corbo/primitives.crb#L1911)

```rust
fn size_NativeBox()->usize
```

Returns the C ABI size in bytes of NativeBox on this target.

### `align_NativeBox`

[primitives.crb:1919](../runtime/corbo/primitives.crb#L1919)

```rust
fn align_NativeBox()->usize
```

Returns the required C ABI alignment of NativeBox on this target.

### `g_CorboStackMark_position`

[primitives.crb:1928](../runtime/corbo/primitives.crb#L1928)

```rust
fn g_CorboStackMark_position(pointer:usize)->usize
```

Reads saved fixed-stack byte cursor in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_CorboStackMark_position`

[primitives.crb:1937](../runtime/corbo/primitives.crb#L1937)

```rust
fn s_CorboStackMark_position(pointer:usize, value:usize)
```

Writes saved fixed-stack byte cursor in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_CorboStackMark_position`

[primitives.crb:1945](../runtime/corbo/primitives.crb#L1945)

```rust
fn a_CorboStackMark_position(pointer:usize)->usize
```

Returns the address of saved fixed-stack byte cursor in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_CorboStackMark_stack`

[primitives.crb:1954](../runtime/corbo/primitives.crb#L1954)

```rust
fn g_CorboStackMark_stack(pointer:usize)->usize
```

Reads originating stack identity in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_CorboStackMark_stack`

[primitives.crb:1963](../runtime/corbo/primitives.crb#L1963)

```rust
fn s_CorboStackMark_stack(pointer:usize, value:usize)
```

Writes originating stack identity in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_CorboStackMark_stack`

[primitives.crb:1971](../runtime/corbo/primitives.crb#L1971)

```rust
fn a_CorboStackMark_stack(pointer:usize)->usize
```

Returns the address of originating stack identity in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_CorboStackMark_region_scope`

[primitives.crb:1980](../runtime/corbo/primitives.crb#L1980)

```rust
fn g_CorboStackMark_region_scope(pointer:usize)->usize
```

Reads saved region-scope marker in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_CorboStackMark_region_scope`

[primitives.crb:1989](../runtime/corbo/primitives.crb#L1989)

```rust
fn s_CorboStackMark_region_scope(pointer:usize, value:usize)
```

Writes saved region-scope marker in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_CorboStackMark_region_scope`

[primitives.crb:1997](../runtime/corbo/primitives.crb#L1997)

```rust
fn a_CorboStackMark_region_scope(pointer:usize)->usize
```

Returns the address of saved region-scope marker in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_CorboStackMark`

[primitives.crb:2005](../runtime/corbo/primitives.crb#L2005)

```rust
fn size_CorboStackMark()->usize
```

Returns the C ABI size in bytes of CorboStackMark on this target.

### `align_CorboStackMark`

[primitives.crb:2013](../runtime/corbo/primitives.crb#L2013)

```rust
fn align_CorboStackMark()->usize
```

Returns the required C ABI alignment of CorboStackMark on this target.

### `g_CorboStackInfo_position`

[primitives.crb:2022](../runtime/corbo/primitives.crb#L2022)

```rust
fn g_CorboStackInfo_position(pointer:usize)->usize
```

Reads next free fixed-stack byte offset in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_CorboStackInfo_position`

[primitives.crb:2031](../runtime/corbo/primitives.crb#L2031)

```rust
fn s_CorboStackInfo_position(pointer:usize, value:usize)
```

Writes next free fixed-stack byte offset in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_CorboStackInfo_position`

[primitives.crb:2039](../runtime/corbo/primitives.crb#L2039)

```rust
fn a_CorboStackInfo_position(pointer:usize)->usize
```

Returns the address of next free fixed-stack byte offset in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_CorboStackInfo_committed`

[primitives.crb:2048](../runtime/corbo/primitives.crb#L2048)

```rust
fn g_CorboStackInfo_committed(pointer:usize)->usize
```

Reads committed fixed-stack bytes in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_CorboStackInfo_committed`

[primitives.crb:2057](../runtime/corbo/primitives.crb#L2057)

```rust
fn s_CorboStackInfo_committed(pointer:usize, value:usize)
```

Writes committed fixed-stack bytes in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_CorboStackInfo_committed`

[primitives.crb:2065](../runtime/corbo/primitives.crb#L2065)

```rust
fn a_CorboStackInfo_committed(pointer:usize)->usize
```

Returns the address of committed fixed-stack bytes in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_CorboStackInfo_capacity`

[primitives.crb:2074](../runtime/corbo/primitives.crb#L2074)

```rust
fn g_CorboStackInfo_capacity(pointer:usize)->usize
```

Reads reserved fixed-stack byte capacity in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_CorboStackInfo_capacity`

[primitives.crb:2083](../runtime/corbo/primitives.crb#L2083)

```rust
fn s_CorboStackInfo_capacity(pointer:usize, value:usize)
```

Writes reserved fixed-stack byte capacity in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_CorboStackInfo_capacity`

[primitives.crb:2091](../runtime/corbo/primitives.crb#L2091)

```rust
fn a_CorboStackInfo_capacity(pointer:usize)->usize
```

Returns the address of reserved fixed-stack byte capacity in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_CorboStackInfo`

[primitives.crb:2099](../runtime/corbo/primitives.crb#L2099)

```rust
fn size_CorboStackInfo()->usize
```

Returns the C ABI size in bytes of CorboStackInfo on this target.

### `align_CorboStackInfo`

[primitives.crb:2107](../runtime/corbo/primitives.crb#L2107)

```rust
fn align_CorboStackInfo()->usize
```

Returns the required C ABI alignment of CorboStackInfo on this target.

### `get_base`

[primitives.crb:2116](../runtime/corbo/primitives.crb#L2116)

```rust
fn get_base()->usize
```

Reads the current thread's fixed-stack base address.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_base`

[primitives.crb:2125](../runtime/corbo/primitives.crb#L2125)

```rust
fn set_base(value:usize)
```

Updates the current thread's fixed-stack base address.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_cursor`

[primitives.crb:2133](../runtime/corbo/primitives.crb#L2133)

```rust
fn get_cursor()->usize
```

Reads the current thread's next free fixed-stack byte offset.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_cursor`

[primitives.crb:2142](../runtime/corbo/primitives.crb#L2142)

```rust
fn set_cursor(value:usize)
```

Updates the current thread's next free fixed-stack byte offset.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_limit`

[primitives.crb:2150](../runtime/corbo/primitives.crb#L2150)

```rust
fn get_limit()->usize
```

Reads the current thread's fixed-stack byte capacity.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_limit`

[primitives.crb:2159](../runtime/corbo/primitives.crb#L2159)

```rust
fn set_limit(value:usize)
```

Updates the current thread's fixed-stack byte capacity.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_committed`

[primitives.crb:2167](../runtime/corbo/primitives.crb#L2167)

```rust
fn get_committed()->usize
```

Reads the current thread's committed fixed-stack byte boundary.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_committed`

[primitives.crb:2176](../runtime/corbo/primitives.crb#L2176)

```rust
fn set_committed(value:usize)
```

Updates the current thread's committed fixed-stack byte boundary.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_page_size`

[primitives.crb:2184](../runtime/corbo/primitives.crb#L2184)

```rust
fn get_page_size()->usize
```

Reads the current thread's OS page size.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_page_size`

[primitives.crb:2193](../runtime/corbo/primitives.crb#L2193)

```rust
fn set_page_size(value:usize)
```

Updates the current thread's OS page size.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_mapped_size`

[primitives.crb:2201](../runtime/corbo/primitives.crb#L2201)

```rust
fn get_mapped_size()->usize
```

Reads the current thread's reserved mapping extent.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_mapped_size`

[primitives.crb:2210](../runtime/corbo/primitives.crb#L2210)

```rust
fn set_mapped_size(value:usize)
```

Updates the current thread's reserved mapping extent.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_global_fixed_budget`

[primitives.crb:2218](../runtime/corbo/primitives.crb#L2218)

```rust
fn get_global_fixed_budget()->usize
```

Reads the configured per-thread fixed-stack byte budget.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_global_fixed_budget`

[primitives.crb:2227](../runtime/corbo/primitives.crb#L2227)

```rust
fn set_global_fixed_budget(value:usize)
```

Updates the configured per-thread fixed-stack byte budget.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_global_budget`

[primitives.crb:2235](../runtime/corbo/primitives.crb#L2235)

```rust
fn get_global_budget()->usize
```

Reads the configured region-stack byte budget.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_global_budget`

[primitives.crb:2244](../runtime/corbo/primitives.crb#L2244)

```rust
fn set_global_budget(value:usize)
```

Updates the configured region-stack byte budget.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_global_limit`

[primitives.crb:2252](../runtime/corbo/primitives.crb#L2252)

```rust
fn get_global_limit()->usize
```

Reads the configured default region byte limit.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_global_limit`

[primitives.crb:2261](../runtime/corbo/primitives.crb#L2261)

```rust
fn set_global_limit(value:usize)
```

Updates the configured default region byte limit.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_current_band`

[primitives.crb:2269](../runtime/corbo/primitives.crb#L2269)

```rust
fn get_current_band()->usize
```

Reads the current thread's region-scope band link.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_current_band`

[primitives.crb:2278](../runtime/corbo/primitives.crb#L2278)

```rust
fn set_current_band(value:usize)
```

Updates the current thread's region-scope band link.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_fixed_reclaim_threshold`

[primitives.crb:2286](../runtime/corbo/primitives.crb#L2286)

```rust
fn get_fixed_reclaim_threshold()->usize
```

Reads the fixed-stack page-reclamation byte threshold.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_fixed_reclaim_threshold`

[primitives.crb:2295](../runtime/corbo/primitives.crb#L2295)

```rust
fn set_fixed_reclaim_threshold(value:usize)
```

Updates the fixed-stack page-reclamation byte threshold.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_region_reclaim_threshold`

[primitives.crb:2303](../runtime/corbo/primitives.crb#L2303)

```rust
fn get_region_reclaim_threshold()->usize
```

Reads the region page-reclamation byte threshold.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_region_reclaim_threshold`

[primitives.crb:2312](../runtime/corbo/primitives.crb#L2312)

```rust
fn set_region_reclaim_threshold(value:usize)
```

Updates the region page-reclamation byte threshold.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_task_worker_count`

[primitives.crb:2320](../runtime/corbo/primitives.crb#L2320)

```rust
fn get_task_worker_count()->usize
```

Reads the number of started poll workers.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_task_worker_count`

[primitives.crb:2329](../runtime/corbo/primitives.crb#L2329)

```rust
fn set_task_worker_count(value:usize)
```

Updates the number of started poll workers.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_task_head`

[primitives.crb:2337](../runtime/corbo/primitives.crb#L2337)

```rust
fn get_task_head()->usize
```

Reads the ready-queue head task.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_task_head`

[primitives.crb:2346](../runtime/corbo/primitives.crb#L2346)

```rust
fn set_task_head(value:usize)
```

Updates the ready-queue head task.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_task_tail`

[primitives.crb:2354](../runtime/corbo/primitives.crb#L2354)

```rust
fn get_task_tail()->usize
```

Reads the ready-queue tail link address.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_task_tail`

[primitives.crb:2363](../runtime/corbo/primitives.crb#L2363)

```rust
fn set_task_tail(value:usize)
```

Updates the ready-queue tail link address.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_task_active`

[primitives.crb:2371](../runtime/corbo/primitives.crb#L2371)

```rust
fn get_task_active()->usize
```

Reads the number of unfinished scheduled tasks.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_task_active`

[primitives.crb:2380](../runtime/corbo/primitives.crb#L2380)

```rust
fn set_task_active(value:usize)
```

Updates the number of unfinished scheduled tasks.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_native_count`

[primitives.crb:2388](../runtime/corbo/primitives.crb#L2388)

```rust
fn get_native_count()->usize
```

Reads the number of unfinished native/blocking workers.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_native_count`

[primitives.crb:2397](../runtime/corbo/primitives.crb#L2397)

```rust
fn set_native_count(value:usize)
```

Updates the number of unfinished native/blocking workers.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_socket_waiters`

[primitives.crb:2405](../runtime/corbo/primitives.crb#L2405)

```rust
fn get_socket_waiters()->usize
```

Reads the intrusive socket-waiter head.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_socket_waiters`

[primitives.crb:2414](../runtime/corbo/primitives.crb#L2414)

```rust
fn set_socket_waiters(value:usize)
```

Updates the intrusive socket-waiter head.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_socket_serial`

[primitives.crb:2422](../runtime/corbo/primitives.crb#L2422)

```rust
fn get_socket_serial()->usize
```

Reads the current readiness-generation counter.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_socket_serial`

[primitives.crb:2431](../runtime/corbo/primitives.crb#L2431)

```rust
fn set_socket_serial(value:usize)
```

Updates the current readiness-generation counter.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_completion_port`

[primitives.crb:2439](../runtime/corbo/primitives.crb#L2439)

```rust
fn get_completion_port()->usize
```

Reads the native completion-port handle.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_completion_port`

[primitives.crb:2448](../runtime/corbo/primitives.crb#L2448)

```rust
fn set_completion_port(value:usize)
```

Updates the native completion-port handle.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_task_attempted`

[primitives.crb:2456](../runtime/corbo/primitives.crb#L2456)

```rust
fn get_task_attempted()->bool
```

Reads whether poll-worker initialization was attempted.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_task_attempted`

[primitives.crb:2465](../runtime/corbo/primitives.crb#L2465)

```rust
fn set_task_attempted(value:bool)
```

Updates whether poll-worker initialization was attempted.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_task_stopping`

[primitives.crb:2473](../runtime/corbo/primitives.crb#L2473)

```rust
fn get_task_stopping()->bool
```

Reads whether poll workers must stop after draining.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_task_stopping`

[primitives.crb:2482](../runtime/corbo/primitives.crb#L2482)

```rust
fn set_task_stopping(value:bool)
```

Updates whether poll workers must stop after draining.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_socket_queue`

[primitives.crb:2490](../runtime/corbo/primitives.crb#L2490)

```rust
fn get_socket_queue()->i64
```

Reads the native readiness-queue descriptor.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_socket_queue`

[primitives.crb:2499](../runtime/corbo/primitives.crb#L2499)

```rust
fn set_socket_queue(value:i64)
```

Updates the native readiness-queue descriptor.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_socket_init_error`

[primitives.crb:2507](../runtime/corbo/primitives.crb#L2507)

```rust
fn get_socket_init_error()->i64
```

Reads the recorded readiness initialization status.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_socket_init_error`

[primitives.crb:2516](../runtime/corbo/primitives.crb#L2516)

```rust
fn set_socket_init_error(value:i64)
```

Updates the recorded readiness initialization status.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_completion_init_error`

[primitives.crb:2524](../runtime/corbo/primitives.crb#L2524)

```rust
fn get_completion_init_error()->i64
```

Reads the recorded completion-port initialization status.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_completion_init_error`

[primitives.crb:2533](../runtime/corbo/primitives.crb#L2533)

```rust
fn set_completion_init_error(value:i64)
```

Updates the recorded completion-port initialization status.
Synchronize shared access; thread-local state belongs to the current execution context.

### `global_band_address`

[primitives.crb:2540](../runtime/corbo/primitives.crb#L2540)

```rust
fn global_band_address()->usize
```

Returns the stable address of the shared fallback region band, without creating a loan or extending a lifetime.

### `head_address`

[primitives.crb:2548](../runtime/corbo/primitives.crb#L2548)

```rust
fn head_address()->usize
```

Returns the scheduler queue-head link address for locked tail-link maintenance.

### `worker_address`

[primitives.crb:2556](../runtime/corbo/primitives.crb#L2556)

```rust
fn worker_address(index:usize)->usize
```

Returns the address of a poll-worker pthread_t slot; index must be inside the fixed worker array.

### `read_word`

[primitives.crb:2564](../runtime/corbo/primitives.crb#L2564)

```rust
fn read_word(pointer:usize)->usize
```

Loads one uintptr_t from a live, suitably aligned address; the caller must provide valid storage.

### `write_word`

[primitives.crb:2572](../runtime/corbo/primitives.crb#L2572)

```rust
fn write_word(pointer:usize, value:usize)
```

Stores one uintptr_t into live, aligned, writable storage; performs no ownership or synchronization checks.

### `read_byte`

[primitives.crb:2579](../runtime/corbo/primitives.crb#L2579)

```rust
fn read_byte(pointer:usize)->usize
```

Loads one byte from a live readable address without a Corbo bounds check.

### `write_byte`

[primitives.crb:2587](../runtime/corbo/primitives.crb#L2587)

```rust
fn write_byte(pointer:usize, value:usize)
```

Stores the low byte of value into a live writable address.

### `read_integer`

[primitives.crb:2594](../runtime/corbo/primitives.crb#L2594)

```rust
fn read_integer(pointer:usize)->usize
```

Loads one C int from live, aligned storage used by region-owner flags.

### `write_integer`

[primitives.crb:2602](../runtime/corbo/primitives.crb#L2602)

```rust
fn write_integer(pointer:usize, value:usize)
```

Stores one C int into live, aligned, writable flag storage.

### `memory_zero`

[primitives.crb:2609](../runtime/corbo/primitives.crb#L2609)

```rust
fn memory_zero(pointer:usize, bytes:usize)
```

Zeroes bytes of valid writable storage; the range must not contain resources needing destruction.

### `memory_copy`

[primitives.crb:2616](../runtime/corbo/primitives.crb#L2616)

```rust
fn memory_copy(destination:usize, source:usize, bytes:usize)
```

Copies bytes between valid nonoverlapping ranges; ownership effects are managed by the calling algorithm.

### `memory_move`

[primitives.crb:2623](../runtime/corbo/primitives.crb#L2623)

```rust
fn memory_move(destination:usize, source:usize, bytes:usize)
```

Moves bytes between valid ranges, allowing overlap; the caller updates element ownership and length.

### `max_size`

[primitives.crb:2630](../runtime/corbo/primitives.crb#L2630)

```rust
fn max_size()->usize
```

Returns the largest target uintptr_t value used for checked size arithmetic.

### `max_difference`

[primitives.crb:2638](../runtime/corbo/primitives.crb#L2638)

```rust
fn max_difference()->usize
```

Returns PTRDIFF_MAX, the largest supported positive object-address difference.

### `max_alignment`

[primitives.crb:2646](../runtime/corbo/primitives.crb#L2646)

```rust
fn max_alignment()->usize
```

Returns alignof(max_align_t) for fixed slots and map entry layout.

### `wrapping_multiply`

[primitives.crb:2654](../runtime/corbo/primitives.crb#L2654)

```rust
fn wrapping_multiply(left:u64, right:u64)->u64
```

Multiplies machine words with unsigned wrapping for the map hash mixer.

### `os_page_size`

[primitives.crb:2662](../runtime/corbo/primitives.crb#L2662)

```rust
fn os_page_size()->usize
```

Queries the target OS virtual-memory page size.

### `os_available_pages`

[primitives.crb:2674](../runtime/corbo/primitives.crb#L2674)

```rust
fn os_available_pages()->i64
```

Queries available physical-memory pages on Unix; nonpositive results require the documented fallback.

### `os_physical_pages`

[primitives.crb:2688](../runtime/corbo/primitives.crb#L2688)

```rust
fn os_physical_pages()->i64
```

Queries total physical-memory pages as a Unix sizing fallback.

### `os_cpus`

[primitives.crb:2700](../runtime/corbo/primitives.crb#L2700)

```rust
fn os_cpus()->usize
```

Queries the OS processor count used to divide default memory budgets.

### `os_reserve`

[primitives.crb:2712](../runtime/corbo/primitives.crb#L2712)

```rust
fn os_reserve(bytes:usize)->usize
```

Reserves a virtual address range without committing its full payload; returns zero on platform failure.

### `os_metadata`

[primitives.crb:2724](../runtime/corbo/primitives.crb#L2724)

```rust
fn os_metadata(bytes:usize)->usize
```

Maps writable zero-initialized metadata pages and returns zero on failure.

### `os_commit`

[primitives.crb:2736](../runtime/corbo/primitives.crb#L2736)

```rust
fn os_commit(pointer:usize, bytes:usize)->bool
```

Makes the supplied page range readable/writable through the target OS; reports success.

### `os_unmap`

[primitives.crb:2748](../runtime/corbo/primitives.crb#L2748)

```rust
fn os_unmap(pointer:usize, bytes:usize)
```

Releases an OS mapping using its original address and byte extent.

### `os_decommit`

[primitives.crb:2759](../runtime/corbo/primitives.crb#L2759)

```rust
fn os_decommit(pointer:usize, bytes:usize)->bool
```

Returns physical backing for complete unused pages while preserving the reserved address range; reports success.

### `fault`

[primitives.crb:2771](../runtime/corbo/primitives.crb#L2771)

```rust
fn fault(code:usize)
```

Terminates with the selected reference-runtime diagnostic for invalid storage, slots or bounds.

### `os_abort`

[primitives.crb:2778](../runtime/corbo/primitives.crb#L2778)

```rust
fn os_abort()
```

Terminates immediately for an impossible worker/pthread contract violation.

### `atomic_claim`

[primitives.crb:2785](../runtime/corbo/primitives.crb#L2785)

```rust
fn atomic_claim(pointer:usize)->bool
```

Atomically changes an unoccupied pool-slot byte to occupied and reports whether this caller claimed it.

### `atomic_clear`

[primitives.crb:2793](../runtime/corbo/primitives.crb#L2793)

```rust
fn atomic_clear(pointer:usize)
```

Publishes a pool slot as free after its destructor has completed.

### `atomic_init_slot`

[primitives.crb:2800](../runtime/corbo/primitives.crb#L2800)

```rust
fn atomic_init_slot(pointer:usize)
```

Initializes an occupancy byte before any thread may access the pool.

### `call_drop`

[primitives.crb:2807](../runtime/corbo/primitives.crb#L2807)

```rust
fn call_drop(callback:usize, pointer:usize)
```

Calls a void(void*) payload destructor; function and payload addresses must satisfy that exact ABI.

### `call_dispose`

[primitives.crb:2814](../runtime/corbo/primitives.crb#L2814)

```rust
fn call_dispose(callback:usize, pointer:usize, completed:bool)
```

Calls a task-state cleanup callback with the completion flag controlling capture/result cleanup.

### `call_poll`

[primitives.crb:2821](../runtime/corbo/primitives.crb#L2821)

```rust
fn call_poll(callback:usize, pointer:usize, failed:bool)->bool
```

Calls a bool(Task*,bool) poll/clear callback and returns its completion result.

### `lock`

[primitives.crb:2829](../runtime/corbo/primitives.crb#L2829)

```rust
fn lock()
```

Acquires the shared runtime/scheduler mutex; callers must not already hold this nonrecursive lock.

### `unlock`

[primitives.crb:2838](../runtime/corbo/primitives.crb#L2838)

```rust
fn unlock()
```

Releases the shared mutex held by this thread.

### `condition_wait`

[primitives.crb:2847](../runtime/corbo/primitives.crb#L2847)

```rust
fn condition_wait()
```

Atomically releases the held runtime mutex while waiting, then reacquires it; callers recheck their predicate.

### `broadcast`

[primitives.crb:2856](../runtime/corbo/primitives.crb#L2856)

```rust
fn broadcast()
```

Wakes condition waiters so they can recheck state protected by the runtime mutex.

### `thread_create`

[primitives.crb:2865](../runtime/corbo/primitives.crb#L2865)

```rust
fn thread_create(slot:usize, entry:usize, argument:usize)->i32
```

Starts a joinable platform thread using a correctly typed entry callback and caller-provided identifier storage.

### `thread_detached`

[primitives.crb:2873](../runtime/corbo/primitives.crb#L2873)

```rust
fn thread_detached(entry:usize, argument:usize)->i32
```

Starts a detached platform worker with native thread attributes and returns the pthread status.

### `thread_join`

[primitives.crb:2881](../runtime/corbo/primitives.crb#L2881)

```rust
fn thread_join(slot:usize)->i32
```

Joins a platform worker by identifier; failure violates the runtime shutdown contract.

### `thread_detach`

[primitives.crb:2889](../runtime/corbo/primitives.crb#L2889)

```rust
fn thread_detach(slot:usize)
```

Detaches a platform thread identifier when its lifetime is managed independently.

### `unsigned_bits`

[primitives.crb:2903](../runtime/corbo/primitives.crb#L2903)

```rust
fn unsigned_bits(value:i64)->usize
```

Reinterprets a signed integer as unsigned bits, including negative values.

### `signed_bits`

[primitives.crb:2905](../runtime/corbo/primitives.crb#L2905)

```rust
fn signed_bits(value:usize)->i64
```

Reinterprets an unsigned word as signed bits without an exact-conversion requirement.

### `size_TaskResult`

[primitives.crb:2907](../runtime/corbo/primitives.crb#L2907)

```rust
fn size_TaskResult()->usize
```

Returns the C ABI size in bytes of TaskResult on this target.

### `socket_waiters_address`

[primitives.crb:2909](../runtime/corbo/primitives.crb#L2909)

```rust
fn socket_waiters_address()->usize
```

Returns the stable address of the waiter-list head for locked intrusive-list updates.

### `temporary_thread_slot`

[primitives.crb:2911](../runtime/corbo/primitives.crb#L2911)

```rust
fn temporary_thread_slot()->usize
```

Returns thread-local scratch storage for a detached thread identifier.

### `call_task_drop`

[primitives.crb:2913](../runtime/corbo/primitives.crb#L2913)

```rust
fn call_task_drop(callback:usize,pointer:usize)
```

Calls a void(Task*) task destructor through its exact function-pointer type.

### `os_windows`

[primitives.crb:2915](../runtime/corbo/primitives.crb#L2915)

```rust
fn os_windows()->bool
```

Reports whether the selected C target is Windows for platform-specific capacity policy.

### `os_available_bytes`

[primitives.crb:2921](../runtime/corbo/primitives.crb#L2921)

```rust
fn os_available_bytes()->usize
```

Queries available Windows physical bytes; returns UINTPTR_MAX if the OS query fails.


## `runtime::readiness`

Descriptor cohorts carry generations; detach before wakeup so resumed tasks can release their frames.

### `socket_interest`

[readiness.crb:4](../runtime/corbo/readiness.crb#L4)

```rust
fn socket_interest(token:usize)->usize
```

Combines active reader/writer interests for one socket generation; caller holds the scheduler lock.

### `socket_signal`

[readiness.crb:20](../runtime/corbo/readiness.crb#L20)

```rust
fn socket_signal(token:usize,mask:usize,status:i64)
```

Publishes a socket readiness/error to one waiter and resumes its parked root; caller holds the scheduler lock.

### `socket_dispatch`

[readiness.crb:54](../runtime/corbo/readiness.crb#L54)

```rust
fn socket_dispatch(event:usize)
```

Detaches matching waiters, publishes readiness and rearms remaining interests; ignores stale generation tokens.

### `socket_events`

[readiness.crb:81](../runtime/corbo/readiness.crb#L81)

```rust
fn socket_events(unused:usize)->usize
```

Waits on the platform readiness queue and dispatches returned events under the scheduler lock.

### `socket_initialize`

[readiness.crb:93](../runtime/corbo/readiness.crb#L93)

```rust
fn socket_initialize()
```

Creates the readiness queue and its detached event thread once; records initialization failure for future waits.

### `corbo_socket_wait`

[readiness.crb:112](../runtime/corbo/readiness.crb#L112)

```rust
fn corbo_socket_wait(child:usize,descriptor:u64,write:bool,out:usize)->bool
```

Registers one task wait for socket readability or writability without losing an intervening wake; returns readiness or a platform error.


## `runtime::reclaim`

Only complete pages beyond the last live byte may be returned to the OS.

### `reclaim_after`

[reclaim.crb:4](../runtime/corbo/reclaim.crb#L4)

```rust
fn reclaim_after(start:usize,live:usize,done_slot:usize,threshold:usize,force:bool)
```

Returns complete unused pages beyond live to the OS when forced or above threshold; updates committed only on success.

### `reclaim_band`

[reclaim.crb:20](../runtime/corbo/reclaim.crb#L20)

```rust
fn reclaim_band(band:usize,force:bool)
```

Computes the last live byte across active regions before considering complete tail pages for reclamation.

### `reclaim_scope`

[reclaim.crb:33](../runtime/corbo/reclaim.crb#L33)

```rust
fn reclaim_scope(force:bool)
```

Reclaims unused fixed/region tail pages using the configured thresholds or force, without releasing live storage.

### `release_pages`

[reclaim.crb:58](../runtime/corbo/reclaim.crb#L58)

```rust
fn release_pages(start:usize,size:usize)->bool
```

Requests OS decommit/discard for a page range; reports whether the platform operation succeeded.


## `runtime::scheduler`

Queue and park/publication transitions run under the scheduler lock.
Poll bodies and destruction callbacks run outside that lock.

### `task_enqueue`

[scheduler.crb:5](../runtime/corbo/scheduler.crb#L5)

```rust
fn task_enqueue(task:usize)
```

Links a task at the queue tail; caller holds the scheduler lock and the task is not already queued.

### `task_publish`

[scheduler.crb:11](../runtime/corbo/scheduler.crb#L11)

```rust
fn task_publish(task:usize)
```

Publishes completion and wakes or enqueues a waiting root exactly through the locked scheduler transition.

### `task_await`

[scheduler.crb:26](../runtime/corbo/scheduler.crb#L26)

```rust
fn task_await(child:usize,current:usize)->bool
```

Registers the current root as child's waiter if unfinished; returns whether completion was already visible under the lock.

### `task_poll_worker`

[scheduler.crb:43](../runtime/corbo/scheduler.crb#L43)

```rust
fn task_poll_worker(unused:usize)->usize
```

Consumes queued tasks, polls outside the lock, then publishes, parks or requeues them; releases its thread-local stack on exit.

### `task_spawn_with`

[scheduler.crb:89](../runtime/corbo/scheduler.crb#L89)

```rust
fn task_spawn_with(task:usize,poll:usize,discard:usize)
```

Initializes a task and starts poll workers once; enqueues it or records launch failure and clears captures if no worker starts.

### `task_spawn`

[scheduler.crb:118](../runtime/corbo/scheduler.crb#L118)

```rust
fn task_spawn(task:usize,poll:usize)
```

Schedules a task without an abandonment callback; its caller must preserve the frame through completion.

### `task_join`

[scheduler.crb:122](../runtime/corbo/scheduler.crb#L122)

```rust
fn task_join(task:usize)
```

Blocks the current thread on the scheduler condition until the task is done.

### `task_end`

[scheduler.crb:130](../runtime/corbo/scheduler.crb#L130)

```rust
fn task_end()
```

Drains active scheduled tasks, signals shutdown and joins every poll worker.


## `runtime::socket_primitives`

Typed bindings to the target readiness queue; Corbo owns waiter state and dispatch policy.

### `once_socket`

[socket_primitives.crb:6](../runtime/corbo/socket_primitives.crb#L6)

```rust
fn once_socket()
```

Runs readiness initialization once with pthread_once; callers observe its recorded queue/error state.

### `pointer_socket_events`

[socket_primitives.crb:14](../runtime/corbo/socket_primitives.crb#L14)

```rust
fn pointer_socket_events()->usize
```

Returns the socket_events callback address for the matching native ABI.
The caller must invoke it through the exact declared function-pointer type.

### `queue_create`

[socket_primitives.crb:22](../runtime/corbo/socket_primitives.crb#L22)

```rust
fn queue_create()->i64
```

Calls the target readiness-queue primitive and returns its descriptor or negative error.

### `queue_wait`

[socket_primitives.crb:30](../runtime/corbo/socket_primitives.crb#L30)

```rust
fn queue_wait(queue:i64)->usize
```

Obtains the next platform readiness token; event meanings are interpreted by the Corbo dispatcher.

### `queue_watch`

[socket_primitives.crb:38](../runtime/corbo/socket_primitives.crb#L38)

```rust
fn queue_watch(queue:i64, descriptor:u64, mask:usize, token:usize)->i64
```

Installs or updates a descriptor's combined readiness mask and generation token through the target ABI.

### `queue_close`

[socket_primitives.crb:46](../runtime/corbo/socket_primitives.crb#L46)

```rust
fn queue_close(queue:i64)
```

Closes the native readiness-queue descriptor after failed initialization.


## `runtime::thread_primitives`

Addresses of correctly typed worker callbacks used by native thread bindings.

### `pointer_task_poll_worker`

[thread_primitives.crb:5](../runtime/corbo/thread_primitives.crb#L5)

```rust
fn pointer_task_poll_worker()->usize
```

Returns the task_poll_worker callback address for the matching native ABI.
The caller must invoke it through the exact declared function-pointer type.

### `pointer_native_run`

[thread_primitives.crb:13](../runtime/corbo/thread_primitives.crb#L13)

```rust
fn pointer_native_run()->usize
```

Returns the native_run callback address for the matching native ABI.
The caller must invoke it through the exact declared function-pointer type.

### `pointer_run_blocking`

[thread_primitives.crb:21](../runtime/corbo/thread_primitives.crb#L21)

```rust
fn pointer_run_blocking()->usize
```

Returns the run_blocking callback address for the matching native ABI.
The caller must invoke it through the exact declared function-pointer type.

### `pointer_task_abandoned`

[thread_primitives.crb:29](../runtime/corbo/thread_primitives.crb#L29)

```rust
fn pointer_task_abandoned()->usize
```

Returns the task_abandoned callback address for the matching native ABI.
The caller must invoke it through the exact declared function-pointer type.


## `runtime::threads`

Native and blocking workers preserve launch-failure, abandonment and drain ordering.

### `native_box`

[threads.crb:4](../runtime/corbo/threads.crb#L4)

```rust
fn native_box()->usize
```

Maps native-worker metadata whose lifetime can extend beyond its launching scope.

### `native_release`

[threads.crb:12](../runtime/corbo/threads.crb#L12)

```rust
fn native_release(box:usize)
```

Releases a native worker's region and metadata; its frame must no longer be in use.

### `worker_regions`

[threads.crb:17](../runtime/corbo/threads.crb#L17)

```rust
fn worker_regions()
```

Establishes the worker's region scope from the configured budget before executing its frame.

### `native_run`

[threads.crb:30](../runtime/corbo/threads.crb#L30)

```rust
fn native_run(box:usize)->usize
```

Runs a native frame on its worker datastack, publishes completion and handles abandoned-result cleanup before decrementing the active count.

### `make_native`

[threads.crb:56](../runtime/corbo/threads.crb#L56)

```rust
fn make_native(out:usize,size:usize,run:usize,dispose:usize)
```

Constructs an inactive native execution descriptor with its frame, run callback and cleanup callback.

### `start_native`

[threads.crb:67](../runtime/corbo/threads.crb#L67)

```rust
fn start_native(value:usize)
```

Starts a detached worker or records LaunchFailed and destroys the unexecuted captures; publication uses the runtime lock.

### `release_native`

[threads.crb:84](../runtime/corbo/threads.crb#L84)

```rust
fn release_native(value:usize,taken:bool)
```

Releases a completed native execution, destroying its result only when it was not transferred to the caller.

### `abandon_native`

[threads.crb:95](../runtime/corbo/threads.crb#L95)

```rust
fn abandon_native(value:usize)
```

Transfers final cleanup of a running native frame to its worker; completed frames are released immediately.

### `dispose_handle_value`

[threads.crb:111](../runtime/corbo/threads.crb#L111)

```rust
fn dispose_handle_value(value:usize)
```

Discards the execution stored at value and clears its storage link to prevent repeated cleanup.

### `destroy_task_region`

[threads.crb:116](../runtime/corbo/threads.crb#L116)

```rust
fn destroy_task_region(region:usize)
```

Discards every stored handle from last to first before releasing the containing region.

### `run_blocking`

[threads.crb:125](../runtime/corbo/threads.crb#L125)

```rust
fn run_blocking(task:usize)->usize
```

Polls a blocking execution on its dedicated worker, waits for dependencies, publishes completion and releases worker storage.

### `start_blocking`

[threads.crb:153](../runtime/corbo/threads.crb#L153)

```rust
fn start_blocking(value:usize)
```

Launches a blocking worker for a TaskValue; on launch failure, clears captures and publishes a completed failed state.

### `native_drain`

[threads.crb:172](../runtime/corbo/threads.crb#L172)

```rust
fn native_drain()
```

Waits under the condition variable until native/blocking executions and scheduled tasks have all finished.


## `runtime::values`

Task descriptors preserve separate state, storage, result and cleanup responsibilities.

### `swap_classic`

[values.crb:4](../runtime/corbo/values.crb#L4)

```rust
fn swap_classic(out:usize,next:usize)
```

Saves the current thread-local fixed-stack/region context in out and installs next for a resumed task.

### `make_task_in`

[values.crb:21](../runtime/corbo/values.crb#L21)

```rust
fn make_task_in(out:usize,region:usize,size:usize,poll:usize,dedicated:bool)
```

Places inactive task state in a region and fills out with its state, storage and typed poll callback; caller holds the lock.

### `task_metadata`

[values.crb:32](../runtime/corbo/values.crb#L32)

```rust
fn task_metadata(bytes:usize)->usize
```

Maps separate runtime metadata of the requested byte size; terminates if the OS cannot provide it.

### `task_unmap`

[values.crb:40](../runtime/corbo/values.crb#L40)

```rust
fn task_unmap(pointer:usize,bytes:usize)
```

Unmaps a metadata address with the original mapping byte count after its users finish.

### `make_task`

[values.crb:44](../runtime/corbo/values.crb#L44)

```rust
fn make_task(out:usize,size:usize,poll:usize)
```

Creates inactive future storage under the runtime lock and records ownership of its separate region descriptor.

### `release_future`

[values.crb:52](../runtime/corbo/values.crb#L52)

```rust
fn release_future(state:usize,completed:bool,taken:bool)
```

Cleans an untaken result or inactive captures, releases frame storage, and unmaps separately owned metadata.

### `task_abandoned`

[values.crb:67](../runtime/corbo/values.crb#L67)

```rust
fn task_abandoned(task:usize)
```

Releases a completed abandoned task, including its untaken result.

### `start_task`

[values.crb:71](../runtime/corbo/values.crb#L71)

```rust
fn start_task(value:usize)
```

Schedules a TaskValue using its poll function and the abandoned-task cleanup callback.

### `discard_handle`

[values.crb:75](../runtime/corbo/values.crb#L75)

```rust
fn discard_handle(value:usize)
```

Marks an active execution abandoned or releases a completed one; native executions use their separate ownership path.

### `join_task`

[values.crb:95](../runtime/corbo/values.crb#L95)

```rust
fn join_task(out:usize,value:usize)
```

Waits for completion, writes a scalar completion descriptor to out and releases the consumed handle's storage.

### `join_task_into`

[values.crb:107](../runtime/corbo/values.crb#L107)

```rust
fn join_task_into(value:usize,out:usize,bytes:usize)->bool
```

Waits for completion and moves a successful aggregate payload into caller storage; returns false on launch failure.

### `discard_future`

[values.crb:122](../runtime/corbo/values.crb#L122)

```rust
fn discard_future(value:usize)
```

Destroys captures and storage of a nonempty inactive future descriptor.


## C ABI and comparison sources

These declarations describe the C boundary/reference, not new checked-language APIs.

### `runtime/async/completion.c.inc`

- [`completion_events`](../runtime/async/completion.c.inc#L10): Receives per-operation completion records and resumes their task roots under the scheduler lock.

- [`completion_initialize`](../runtime/async/completion.c.inc#L36): Creates the completion port and its event thread once, recording initialization errors.

- [`corbo_socket_attach`](../runtime/async/completion.c.inc#L52): Associates a socket with the runtime completion port and returns the platform status.

- [`corbo_socket_complete`](../runtime/async/completion.c.inc#L59): Submits or observes one operation-specific completion request and coordinates its task wakeup without sharing request state.

### `runtime/async/readiness.c.inc`

- [`socket_interest`](../runtime/async/readiness.c.inc#L12): Combines active reader/writer interests for one socket generation; caller holds the scheduler lock.

- [`socket_signal`](../runtime/async/readiness.c.inc#L21): Publishes a socket readiness/error to one waiter and resumes its parked root; caller holds the scheduler lock.

- [`socket_dispatch`](../runtime/async/readiness.c.inc#L45): Detaches matching waiters, publishes readiness and rearms remaining interests; ignores stale generation tokens.

- [`socket_events`](../runtime/async/readiness.c.inc#L65): Waits on the platform readiness queue and dispatches returned events under the scheduler lock.

- [`socket_initialize`](../runtime/async/readiness.c.inc#L73): Creates the readiness queue and its detached event thread once; records initialization failure for future waits.

- [`corbo_socket_wait`](../runtime/async/readiness.c.inc#L89): Registers one task wait for socket readability or writability without losing an intervening wake; returns readiness or a platform error.

### `runtime/async/scheduler.c.inc`

- [`Task`](../runtime/async/scheduler.c.inc#L8): Intrusive execution header shared by generated frames and the scheduler. Queue, completion and waiter transitions require task_lock.

- [`Task`](../runtime/async/scheduler.c.inc#L10): Intrusive execution header shared by generated frames and the scheduler. Queue, completion and waiter transitions require task_lock.

- [`pc`](../runtime/async/scheduler.c.inc#L12): pc: resume-state program counter.

- [`poll`](../runtime/async/scheduler.c.inc#L14): poll: typed poll/clear callback.

- [`next`](../runtime/async/scheduler.c.inc#L16): next: ready-queue next link.

- [`failed`](../runtime/async/scheduler.c.inc#L18): failed: launch-failure flag.

- [`done`](../runtime/async/scheduler.c.inc#L20): done: completion-publication flag.

- [`abandoned`](../runtime/async/scheduler.c.inc#L22): abandoned: worker-owned final-cleanup flag.

- [`discard`](../runtime/async/scheduler.c.inc#L24): discard: typed abandoned-task cleanup callback.

- [`root,waiter`](../runtime/async/scheduler.c.inc#L26): root: outer polling-root link. waiter: dependent polling-root link.

- [`io_ready,io_registered`](../runtime/async/scheduler.c.inc#L28): io_ready: readiness-publication flag. io_registered: active-wait registration flag.

- [`io_socket`](../runtime/async/scheduler.c.inc#L30): io_socket: native socket identifier.

- [`io_write`](../runtime/async/scheduler.c.inc#L32): io_write: write-interest selector.

- [`io_next`](../runtime/async/scheduler.c.inc#L34): io_next: intrusive readiness-waiter link.

- [`io_token`](../runtime/async/scheduler.c.inc#L36): io_token: readiness-generation token.

- [`io_error`](../runtime/async/scheduler.c.inc#L38): io_error: recorded platform I/O status.

- [`waiting,parked,blocking`](../runtime/async/scheduler.c.inc#L40): waiting: dependency-wait predicate. parked: removed-from-ready-queue flag. blocking: dedicated blocking-worker flag.

- [`task_enqueue`](../runtime/async/scheduler.c.inc#L52): Links a task at the queue tail; caller holds the scheduler lock and the task is not already queued.

- [`task_publish`](../runtime/async/scheduler.c.inc#L59): Publishes completion and wakes or enqueues a waiting root exactly through the locked scheduler transition.

- [`task_await`](../runtime/async/scheduler.c.inc#L73): Registers the current root as child's waiter if unfinished; returns whether completion was already visible under the lock.

- [`task_poll_worker`](../runtime/async/scheduler.c.inc#L86): Consumes queued tasks, polls outside the lock, then publishes, parks or requeues them; releases its thread-local stack on exit.

- [`task_spawn_with`](../runtime/async/scheduler.c.inc#L116): Initializes a task and starts poll workers once; enqueues it or records launch failure and clears captures if no worker starts.

- [`task_spawn`](../runtime/async/scheduler.c.inc#L138): Schedules a task without an abandonment callback; its caller must preserve the frame through completion.

- [`task_join`](../runtime/async/scheduler.c.inc#L142): Blocks the current thread on the scheduler condition until the task is done.

- [`task_end`](../runtime/async/scheduler.c.inc#L148): Drains active scheduled tasks, signals shutdown and joins every poll worker.

### `runtime/async/threads.c.inc`

- [`NativeBox`](../runtime/async/threads.c.inc#L5): Worker metadata with its Region prefix at offset zero; abandonment can transfer final cleanup to the worker.

- [`region`](../runtime/async/threads.c.inc#L7): region: embedded frame region at offset zero.

- [`state`](../runtime/async/threads.c.inc#L9): state: native frame address.

- [`run`](../runtime/async/threads.c.inc#L11): run: native frame run callback.

- [`abandoned`](../runtime/async/threads.c.inc#L13): abandoned: worker-owned cleanup flag.

- [`dispose`](../runtime/async/threads.c.inc#L15): dispose: capture/result cleanup callback.

- [`native_box`](../runtime/async/threads.c.inc#L21): Maps native-worker metadata whose lifetime can extend beyond its launching scope.

- [`native_release`](../runtime/async/threads.c.inc#L34): Releases a native worker's region and metadata; its frame must no longer be in use.

- [`worker_regions`](../runtime/async/threads.c.inc#L44): Establishes the worker's region scope from the configured budget before executing its frame.

- [`native_run`](../runtime/async/threads.c.inc#L48): Runs a native frame on its worker datastack, publishes completion and handles abandoned-result cleanup before decrementing the active count.

- [`make_native`](../runtime/async/threads.c.inc#L70): Returns an inactive native execution descriptor with frame, run callback and cleanup callback.

- [`start_native`](../runtime/async/threads.c.inc#L83): Starts a detached worker or records LaunchFailed and destroys the unexecuted captures; publication uses the runtime lock.

- [`release_native`](../runtime/async/threads.c.inc#L101): Releases a completed native execution, destroying its result only when it was not transferred to the caller.

- [`abandon_native`](../runtime/async/threads.c.inc#L107): Transfers final cleanup of a running native frame to its worker; completed frames are released immediately.

- [`value_region_new`](../runtime/async/threads.c.inc#L117): Initializes a region while holding the shared runtime lock; the descriptor must remain at a stable address.

- [`value_region_add`](../runtime/async/threads.c.inc#L120): Appends one region slot under the runtime lock and returns its address.

- [`value_region_drop`](../runtime/async/threads.c.inc#L123): Unlinks and releases a region under the runtime lock after owned child cleanup.

- [`dispose_handle_value`](../runtime/async/threads.c.inc#L126): Discards the execution stored at value and clears its storage link to prevent repeated cleanup.

- [`destroy_task_region`](../runtime/async/threads.c.inc#L128): Discards every stored handle from last to first before releasing the containing region.

- [`scoped_region_enter`](../runtime/async/threads.c.inc#L131): Enters a region scope under the runtime lock using explicit and inferred slot budgets.

- [`scoped_region_restore`](../runtime/async/threads.c.inc#L134): Restores the saved region-scope mark under the runtime lock while preserving live transferred regions.

- [`run_blocking`](../runtime/async/threads.c.inc#L137): Polls a blocking execution on its dedicated worker, waits for dependencies, publishes completion and releases worker storage.

- [`start_blocking`](../runtime/async/threads.c.inc#L160): Launches a blocking worker for a TaskValue; on launch failure, clears captures and publishes a completed failed state.

- [`native_drain`](../runtime/async/threads.c.inc#L182): Waits under the condition variable until native/blocking executions and scheduled tasks have all finished.

### `runtime/async/values.c.inc`

- [`TaskResult`](../runtime/async/values.c.inc#L5): Inline scalar result union; the generated frame contract determines the active member.

- [`k1`](../runtime/async/values.c.inc#L7): k1: Result storage for i32.

- [`k2`](../runtime/async/values.c.inc#L9): k2: Result storage for i64.

- [`k3`](../runtime/async/values.c.inc#L11): k3: Result storage for bool.

- [`k4`](../runtime/async/values.c.inc#L13): k4: Result storage for u8.

- [`k5`](../runtime/async/values.c.inc#L15): k5: Result storage for u16.

- [`k6`](../runtime/async/values.c.inc#L17): k6: Result storage for u32.

- [`k7`](../runtime/async/values.c.inc#L19): k7: Result storage for u64.

- [`k8`](../runtime/async/values.c.inc#L21): k8: Result storage for f32.

- [`k9`](../runtime/async/values.c.inc#L23): k9: Result storage for f64.

- [`ClassicStack`](../runtime/async/values.c.inc#L26): Saved thread-local fixed-stack mapping and region-scope context for task suspension/resumption.

- [`base`](../runtime/async/values.c.inc#L28): base: saved fixed-stack base.

- [`cursor,limit,committed,page_size,mapped_size`](../runtime/async/values.c.inc#L30): cursor: saved next free byte offset. limit: saved fixed-stack capacity. committed: saved committed-byte boundary. page_size: saved OS page size. mapped_size: saved mapping extent.

- [`band`](../runtime/async/values.c.inc#L32): band: saved region-scope link.

- [`swap_classic`](../runtime/async/values.c.inc#L35): Installs next as the thread-local fixed-stack/region context and returns the previous context for later restoration.

- [`TaskState`](../runtime/async/values.c.inc#L40): Task header at offset zero plus result, frame-region ownership, cleanup callback and saved storage context.

- [`task`](../runtime/async/values.c.inc#L42): task: scheduler header at offset zero.

- [`value`](../runtime/async/values.c.inc#L44): value: inline scalar result storage.

- [`payload`](../runtime/async/values.c.inc#L46): payload: aggregate result address.

- [`region`](../runtime/async/values.c.inc#L48): region: frame-storage region link.

- [`own_region`](../runtime/async/values.c.inc#L50): own_region: separate region-descriptor ownership flag.

- [`dispose`](../runtime/async/values.c.inc#L52): dispose: typed capture/result cleanup callback.

- [`classic`](../runtime/async/values.c.inc#L54): classic: suspended thread-local datastack context.

- [`TaskValue`](../runtime/async/values.c.inc#L57): Future/handle descriptor linking an execution frame, backing region, typed poll callback and native-worker mode.

- [`state`](../runtime/async/values.c.inc#L59): state: execution frame address.

- [`storage`](../runtime/async/values.c.inc#L61): storage: owned backing-region link.

- [`poll`](../runtime/async/values.c.inc#L63): poll: frame-specific poll callback.

- [`native`](../runtime/async/values.c.inc#L65): native: native-worker ownership selector.

- [`TaskCompletion`](../runtime/async/values.c.inc#L68): Success flag and inline scalar result moved out by join_task.

- [`ok`](../runtime/async/values.c.inc#L70): ok: successful-launch/completion flag.

- [`value`](../runtime/async/values.c.inc#L72): value: moved scalar result bits.

- [`make_task_in`](../runtime/async/values.c.inc#L75): Returns an inactive task descriptor backed by the supplied stable region; caller holds the runtime lock.

- [`release_native`](../runtime/async/values.c.inc#L79): Releases a completed native execution, destroying its result only when it was not transferred to the caller.

- [`abandon_native`](../runtime/async/values.c.inc#L81): Transfers final cleanup of a running native frame to its worker; completed frames are released immediately.

- [`task_metadata`](../runtime/async/values.c.inc#L83): Maps separate runtime metadata of the requested byte size; terminates if the OS cannot provide it.

- [`task_unmap`](../runtime/async/values.c.inc#L91): Unmaps a metadata address with the original mapping byte count after its users finish.

- [`make_task`](../runtime/async/values.c.inc#L99): Returns an inactive task descriptor backed by a region and separately owned metadata.

- [`release_future`](../runtime/async/values.c.inc#L104): Cleans an untaken result or inactive captures, releases frame storage, and unmaps separately owned metadata.

- [`task_abandoned`](../runtime/async/values.c.inc#L108): Releases a completed abandoned task, including its untaken result.

- [`start_task`](../runtime/async/values.c.inc#L110): Schedules a TaskValue using its poll function and the abandoned-task cleanup callback.

- [`discard_handle`](../runtime/async/values.c.inc#L112): Marks an active execution abandoned or releases a completed one; native executions use their separate ownership path.

- [`join_task`](../runtime/async/values.c.inc#L117): Waits for completion, returns a scalar completion descriptor and releases consumed handle storage.

- [`join_task_into`](../runtime/async/values.c.inc#L120): Waits for completion and moves a successful aggregate payload into caller storage; returns false on launch failure.

- [`discard_future`](../runtime/async/values.c.inc#L124): Destroys captures and storage of a nonempty inactive future descriptor.

### `runtime/collections/hashmap.c.inc`

- [`map_align`](../runtime/collections/hashmap.c.inc#L7): Rounds a map header or entry width to max_align_t, terminating on overflow.

- [`map_new`](../runtime/collections/hashmap.c.inc#L14): Maps a map descriptor and initializes its stable region storage with an optional element cleanup callback.

- [`map_extend`](../runtime/collections/hashmap.c.inc#L29): Commits additional bytes in a map region without moving existing entries; capacity failure terminates.

- [`map_link`](../runtime/collections/hashmap.c.inc#L37): Returns the bucket-chain link containing key or the insertion link at its end; bucket storage must be initialized.

- [`map_get`](../runtime/collections/hashmap.c.inc#L51): Returns the stored value address for key, or zero when absent; the map retains ownership.

- [`map_insert`](../runtime/collections/hashmap.c.inc#L58): Moves incoming bytes into a stable entry. Returns true and moves the replaced bytes into previous when the key exists.

- [`map_remove`](../runtime/collections/hashmap.c.inc#L88): Unlinks key and moves its value into previous; returns false without writing when absent and indexes the freed slot for reuse.

- [`map_drop`](../runtime/collections/hashmap.c.inc#L103): Clears the caller's map pointer, destroys remaining values with dispose, then releases payload and descriptor storage.

### `runtime/collections/vector.c.inc`

- [`region_push_owned`](../runtime/collections/vector.c.inc#L5): Appends a child-region/slot link for recursive cleanup; the child descriptor and slot flag must remain valid.

- [`region_push`](../runtime/collections/vector.c.inc#L9): Appends a byte or machine-word scalar according to the region element width.

- [`region_push_row`](../runtime/collections/vector.c.inc#L15): Appends a row of machine words from caller storage; the source must cover the region element width.

- [`region_read_row`](../runtime/collections/vector.c.inc#L20): Reads a signed word in a checked row/field position; invalid positions terminate.

- [`region_append`](../runtime/collections/vector.c.inc#L25): Appends count bytes through checked element growth; source must contain count readable bytes.

- [`region_read`](../runtime/collections/vector.c.inc#L30): Reads a checked byte or machine-word element and returns its signed bit representation.

### `runtime/collections/vector_owned.c.inc`

- [`value_region_append`](../runtime/collections/vector_owned.c.inc#L5): Grows byte storage through the synchronized path, then copies a readable source range into the new tail.

- [`vector_remove`](../runtime/collections/vector_owned.c.inc#L9): Moves the selected element into out and shifts the remaining tail; out must hold one element and index must be live.

- [`vector_pop`](../runtime/collections/vector_owned.c.inc#L14): Moves the last element into out and shortens the region; returns false without writing when empty.

- [`destroy_owned_region`](../runtime/collections/vector_owned.c.inc#L17): Destroys pooled elements from the last slot to the first, then releases the vector's region.

### `runtime/corbo/corbo_runtime_abi.h`

- [`Task`](../runtime/corbo/corbo_runtime_abi.h#L30): Intrusive execution header shared by generated frames and the scheduler. Queue, completion and waiter transitions require task_lock.

- [`Task`](../runtime/corbo/corbo_runtime_abi.h#L32): Intrusive execution header shared by generated frames and the scheduler. Queue, completion and waiter transitions require task_lock.

- [`pc`](../runtime/corbo/corbo_runtime_abi.h#L34): pc: resume-state program counter.

- [`poll`](../runtime/corbo/corbo_runtime_abi.h#L36): poll: typed poll/clear callback.

- [`next`](../runtime/corbo/corbo_runtime_abi.h#L38): next: ready-queue next link.

- [`failed`](../runtime/corbo/corbo_runtime_abi.h#L40): failed: launch-failure flag.

- [`done`](../runtime/corbo/corbo_runtime_abi.h#L42): done: completion-publication flag.

- [`abandoned`](../runtime/corbo/corbo_runtime_abi.h#L44): abandoned: worker-owned final-cleanup flag.

- [`discard`](../runtime/corbo/corbo_runtime_abi.h#L46): discard: typed abandoned-task cleanup callback.

- [`root,waiter`](../runtime/corbo/corbo_runtime_abi.h#L48): root: outer polling-root link. waiter: dependent polling-root link.

- [`io_ready,io_registered`](../runtime/corbo/corbo_runtime_abi.h#L50): io_ready: readiness-publication flag. io_registered: active-wait registration flag.

- [`io_socket`](../runtime/corbo/corbo_runtime_abi.h#L52): io_socket: native socket identifier.

- [`io_write`](../runtime/corbo/corbo_runtime_abi.h#L54): io_write: write-interest selector.

- [`io_next`](../runtime/corbo/corbo_runtime_abi.h#L56): io_next: intrusive readiness-waiter link.

- [`io_token`](../runtime/corbo/corbo_runtime_abi.h#L58): io_token: readiness-generation token.

- [`io_error`](../runtime/corbo/corbo_runtime_abi.h#L60): io_error: recorded platform I/O status.

- [`waiting,parked,blocking`](../runtime/corbo/corbo_runtime_abi.h#L62): waiting: dependency-wait predicate. parked: removed-from-ready-queue flag. blocking: dedicated blocking-worker flag.

- [`TaskResult`](../runtime/corbo/corbo_runtime_abi.h#L74): Inline scalar result union; the generated frame contract determines the active member.

- [`k1`](../runtime/corbo/corbo_runtime_abi.h#L76): k1: Result storage for i32.

- [`k2`](../runtime/corbo/corbo_runtime_abi.h#L78): k2: Result storage for i64.

- [`k3`](../runtime/corbo/corbo_runtime_abi.h#L80): k3: Result storage for bool.

- [`k4`](../runtime/corbo/corbo_runtime_abi.h#L82): k4: Result storage for u8.

- [`k5`](../runtime/corbo/corbo_runtime_abi.h#L84): k5: Result storage for u16.

- [`k6`](../runtime/corbo/corbo_runtime_abi.h#L86): k6: Result storage for u32.

- [`k7`](../runtime/corbo/corbo_runtime_abi.h#L88): k7: Result storage for u64.

- [`k8`](../runtime/corbo/corbo_runtime_abi.h#L90): k8: Result storage for f32.

- [`k9`](../runtime/corbo/corbo_runtime_abi.h#L92): k9: Result storage for f64.

- [`ClassicStack`](../runtime/corbo/corbo_runtime_abi.h#L95): Saved thread-local fixed-stack mapping and region-scope context for task suspension/resumption.

- [`base`](../runtime/corbo/corbo_runtime_abi.h#L97): base: saved fixed-stack base.

- [`cursor,limit,committed,page_size,mapped_size`](../runtime/corbo/corbo_runtime_abi.h#L99): cursor: saved next free byte offset. limit: saved fixed-stack capacity. committed: saved committed-byte boundary. page_size: saved OS page size. mapped_size: saved mapping extent.

- [`band`](../runtime/corbo/corbo_runtime_abi.h#L101): band: saved region-scope link.

- [`TaskState`](../runtime/corbo/corbo_runtime_abi.h#L104): Task header at offset zero plus result, frame-region ownership, cleanup callback and saved storage context.

- [`task`](../runtime/corbo/corbo_runtime_abi.h#L106): task: scheduler header at offset zero.

- [`value`](../runtime/corbo/corbo_runtime_abi.h#L108): value: inline scalar result storage.

- [`payload`](../runtime/corbo/corbo_runtime_abi.h#L110): payload: aggregate result address.

- [`region`](../runtime/corbo/corbo_runtime_abi.h#L112): region: frame-storage region link.

- [`own_region`](../runtime/corbo/corbo_runtime_abi.h#L114): own_region: separate region-descriptor ownership flag.

- [`dispose`](../runtime/corbo/corbo_runtime_abi.h#L116): dispose: typed capture/result cleanup callback.

- [`classic`](../runtime/corbo/corbo_runtime_abi.h#L118): classic: suspended thread-local datastack context.

- [`TaskValue`](../runtime/corbo/corbo_runtime_abi.h#L121): Future/handle descriptor linking an execution frame, backing region, typed poll callback and native-worker mode.

- [`state`](../runtime/corbo/corbo_runtime_abi.h#L123): state: execution frame address.

- [`storage`](../runtime/corbo/corbo_runtime_abi.h#L125): storage: owned backing-region link.

- [`poll`](../runtime/corbo/corbo_runtime_abi.h#L127): poll: frame-specific poll callback.

- [`native`](../runtime/corbo/corbo_runtime_abi.h#L129): native: native-worker ownership selector.

- [`TaskCompletion`](../runtime/corbo/corbo_runtime_abi.h#L132): Success flag and inline scalar result moved out by join_task.

- [`ok`](../runtime/corbo/corbo_runtime_abi.h#L134): ok: successful-launch/completion flag.

- [`value`](../runtime/corbo/corbo_runtime_abi.h#L136): value: moved scalar result bits.

- [`NativeBox`](../runtime/corbo/corbo_runtime_abi.h#L139): Worker metadata with its Region prefix at offset zero; abandonment can transfer final cleanup to the worker.

- [`region`](../runtime/corbo/corbo_runtime_abi.h#L141): region: embedded frame region at offset zero.

- [`state`](../runtime/corbo/corbo_runtime_abi.h#L143): state: native frame address.

- [`run`](../runtime/corbo/corbo_runtime_abi.h#L145): run: native frame run callback.

- [`abandoned`](../runtime/corbo/corbo_runtime_abi.h#L147): abandoned: worker-owned cleanup flag.

- [`dispose`](../runtime/corbo/corbo_runtime_abi.h#L149): dispose: capture/result cleanup callback.

### `runtime/corbo_runtime.h`

- [`Corbo_i32`](../runtime/corbo_runtime.h#L24): C ABI representation of Corbo i32, using this target's corresponding primitive layout.

- [`Corbo_i64`](../runtime/corbo_runtime.h#L26): C ABI representation of Corbo i64, using this target's corresponding primitive layout.

- [`Corbo_u8`](../runtime/corbo_runtime.h#L28): C ABI representation of Corbo u8, using this target's corresponding primitive layout.

- [`Corbo_u16`](../runtime/corbo_runtime.h#L30): C ABI representation of Corbo u16, using this target's corresponding primitive layout.

- [`Corbo_u32`](../runtime/corbo_runtime.h#L32): C ABI representation of Corbo u32, using this target's corresponding primitive layout.

- [`Corbo_u64`](../runtime/corbo_runtime.h#L34): C ABI representation of Corbo u64, using this target's corresponding primitive layout.

- [`Corbo_usize`](../runtime/corbo_runtime.h#L36): C ABI representation of Corbo usize, using this target's corresponding primitive layout.

- [`Corbo_bool`](../runtime/corbo_runtime.h#L38): C ABI representation of Corbo bool, using this target's corresponding primitive layout.

- [`Corbo_f32`](../runtime/corbo_runtime.h#L40): C ABI representation of Corbo f32, using this target's corresponding primitive layout.

- [`Corbo_f64`](../runtime/corbo_runtime.h#L42): C ABI representation of Corbo f64, using this target's corresponding primitive layout.

- [`Region`](../runtime/corbo_runtime.h#L46): Stable descriptor for a bounded growing payload; len counts elements and width is bytes per element. Active descriptors must not move.

- [`RegionBand`](../runtime/corbo_runtime.h#L48): Reserved virtual address range containing ordered active regions; closed bands are released only when no live region remains.

- [`base`](../runtime/corbo_runtime.h#L50): base: reserved virtual-memory base.

- [`capacity,committed,limit`](../runtime/corbo_runtime.h#L52): capacity: reserved byte capacity. committed: committed byte boundary. limit: per-region byte limit.

- [`active`](../runtime/corbo_runtime.h#L54): active: ordered active-region list.

- [`parent`](../runtime/corbo_runtime.h#L56): parent: parent region-scope link.

- [`closed`](../runtime/corbo_runtime.h#L58): closed: closed-scope flag.

- [`RegionOwner`](../runtime/corbo_runtime.h#L61): Owned child-region and live-flag link used to clean descendants before their parent storage.

- [`region`](../runtime/corbo_runtime.h#L63): region: owned child-region link.

- [`slot`](../runtime/corbo_runtime.h#L65): slot: address of the child's live-slot flag.

- [`Region`](../runtime/corbo_runtime.h#L68): Stable descriptor for a bounded growing payload; len counts elements and width is bytes per element. Active descriptors must not move.

- [`data`](../runtime/corbo_runtime.h#L70): data: payload base address.

- [`len,offset,bytes,width`](../runtime/corbo_runtime.h#L72): len: live element count. offset: byte offset within its band. bytes: maximum payload byte extent. width: bytes per stored element.

- [`next`](../runtime/corbo_runtime.h#L74): next: next active-region link.

- [`band`](../runtime/corbo_runtime.h#L76): band: containing band link.

- [`owned`](../runtime/corbo_runtime.h#L78): owned: recursive child-region cleanup mode.

- [`Pools`](../runtime/corbo_runtime.h#L81): Fixed datastack slot storage partitioned by enum arm, with atomic occupancy bytes for slot claiming.

- [`cap,stride,arms`](../runtime/corbo_runtime.h#L83): cap: slot count per arm. stride: aligned bytes per slot. arms: enum-arm count.

- [`data`](../runtime/corbo_runtime.h#L85): data: stable slot-storage base.

- [`used`](../runtime/corbo_runtime.h#L87): used: atomic occupancy-byte array.

- [`Owned`](../runtime/corbo_runtime.h#L90): Move-only allocation descriptor carrying the pool, payload, physical index and destructor. C callers must enforce single cleanup responsibility.

- [`pool`](../runtime/corbo_runtime.h#L92): pool: source pool link, zero after release.

- [`slot`](../runtime/corbo_runtime.h#L94): slot: payload slot address.

- [`index`](../runtime/corbo_runtime.h#L96): index: physical slot index.

- [`destroy`](../runtime/corbo_runtime.h#L98): destroy: typed payload destructor callback.

- [`MapEntry`](../runtime/corbo_runtime.h#L101): Stable map entry header containing normalized key bits and a bucket/free-list offset.

- [`key`](../runtime/corbo_runtime.h#L103): key: normalized integer key bits.

- [`next`](../runtime/corbo_runtime.h#L105): next: next bucket-chain or free-list byte offset.

- [`RegionalMap`](../runtime/corbo_runtime.h#L108): Map descriptor owning a stable byte region, entry width, reusable-slot list and optional value destructor.

- [`region`](../runtime/corbo_runtime.h#L110): region: stable entry-storage region.

- [`width,free_slot`](../runtime/corbo_runtime.h#L112): width: value byte width. free_slot: free-entry offset list head.

- [`dispose`](../runtime/corbo_runtime.h#L114): dispose: value cleanup callback.

- [`CorboRegion`](../runtime/corbo_runtime.h#L118): Public C alias of the stable Region descriptor; payload ownership rules are unchanged.

- [`CorboVector`](../runtime/corbo_runtime.h#L120): Public C vector storage descriptor; element-specific cleanup remains the caller/generated code's responsibility.

- [`CorboString`](../runtime/corbo_runtime.h#L122): Public C UTF-8 string storage descriptor; unchecked C mutations must preserve the string contract.

- [`CorboPool`](../runtime/corbo_runtime.h#L124): Public C alias for fixed slot storage; the source datastack must outlive its allocations.

- [`CorboAllocation`](../runtime/corbo_runtime.h#L126): Public C allocation descriptor. Copying it in C does not transfer or duplicate cleanup responsibility.

- [`CorboHashMap`](../runtime/corbo_runtime.h#L128): Public C map descriptor with stable entry addresses and optional element cleanup.

- [`CorboStackMark`](../runtime/corbo_runtime.h#L131): Saved cursor, stack identity and region-scope mark; rewind is valid only after dependent resources and workers are cleaned up.

- [`position`](../runtime/corbo_runtime.h#L133): position: saved fixed-stack byte cursor.

- [`stack`](../runtime/corbo_runtime.h#L135): stack: originating stack identity.

- [`region_scope`](../runtime/corbo_runtime.h#L137): region_scope: saved region-scope marker.

- [`CorboStackInfo`](../runtime/corbo_runtime.h#L140): Snapshot of the current fixed-stack cursor, committed bytes and reserved capacity.

- [`position,committed,capacity`](../runtime/corbo_runtime.h#L142): position: next free fixed-stack byte offset. committed: committed fixed-stack bytes. capacity: reserved fixed-stack byte capacity.

- [`corbo_runtime_abi_version`](../runtime/corbo_runtime.h#L147): Returns the experimental C ABI version; clients must use the matching runtime header.

- [`corbo_runtime_init`](../runtime/corbo_runtime.h#L149): Initializes C-owned runtime storage with optional fixed-stack, region-stack and region-width budgets; repeated initialization terminates.

- [`corbo_runtime_shutdown`](../runtime/corbo_runtime.h#L151): Releases the calling thread's C-owned runtime after all live resources and workers have been cleaned up; a stopped runtime is a no-op.

- [`corbo_datastack_alloc`](../runtime/corbo_runtime.h#L155): Allocates count aligned elements on the calling thread's initialized stack; invalid size/alignment or exhaustion terminates.

- [`corbo_datastack_mark`](../runtime/corbo_runtime.h#L157): Returns a mark containing the current cursor, stack identity and region-scope marker.

- [`corbo_datastack_info`](../runtime/corbo_runtime.h#L159): Returns the current cursor, committed-byte boundary and fixed-stack capacity.

- [`corbo_datastack_rewind`](../runtime/corbo_runtime.h#L162): Restores a mark from this stack after caller cleanup; rejects foreign or forward marks and preserves live transferred regions.

- [`corbo_free_pages`](../runtime/corbo_runtime.h#L164): Requests immediate reclamation of complete unused pages without changing live values or their reserved address ranges.

- [`corbo_pool_create`](../runtime/corbo_runtime.h#L167): Creates fixed slots for each enum arm on the current datastack; zero element width or invalid capacity terminates.

- [`corbo_pool_take`](../runtime/corbo_runtime.h#L169): Claims a free slot in arm and returns its allocation descriptor; invalid arms or exhaustion terminate.

- [`corbo_allocation_data`](../runtime/corbo_runtime.h#L171): Returns an allocation's payload address without transferring ownership or extending its lifetime.

- [`corbo_allocation_drop`](../runtime/corbo_runtime.h#L174): Destroys a live allocation before releasing its slot and clears its pool link; a cleared descriptor is harmless.

- [`corbo_region_enter`](../runtime/corbo_runtime.h#L177): Enters a local region scope with the requested maximum region size and count budget.

- [`corbo_region_new`](../runtime/corbo_runtime.h#L179): Initializes a stable caller-owned region descriptor for element_size bytes per item; dedicated selects independent band storage.

- [`corbo_region_push`](../runtime/corbo_runtime.h#L181): Appends one uninitialized region element and returns its address; region exhaustion terminates.

- [`corbo_region_drop`](../runtime/corbo_runtime.h#L183): Destroys child-region links, releases payload storage and zeroes the caller's region descriptor.

- [`corbo_map_new`](../runtime/corbo_runtime.h#L186): Maps a map descriptor and initializes its stable region storage with an optional element cleanup callback.

- [`corbo_map_get`](../runtime/corbo_runtime.h#L188): Returns the stored value address for key, or zero when absent; the map retains ownership.

- [`corbo_map_insert`](../runtime/corbo_runtime.h#L190): Moves incoming bytes into a stable entry. Returns true and moves the replaced bytes into previous when the key exists.

- [`corbo_map_remove`](../runtime/corbo_runtime.h#L192): Unlinks key and moves its value into previous; returns false without writing when absent and indexes the freed slot for reuse.

- [`corbo_map_drop`](../runtime/corbo_runtime.h#L194): Clears the caller's map pointer, destroys remaining values with dispose, then releases payload and descriptor storage.

### `runtime/memory/datastack.c.inc`

- [`reserve`](../runtime/memory/datastack.c.inc#L20): Reserves the calling thread's fixed datastack, initializes page metadata and commits storage on demand.

- [`push`](../runtime/memory/datastack.c.inc#L44): Reserves count aligned fixed-size elements at the current cursor; checks multiplication, alignment and capacity before advancing.

- [`release`](../runtime/memory/datastack.c.inc#L62): Unmaps the calling thread's fixed datastack after its values and workers have been cleaned up.

- [`take`](../runtime/memory/datastack.c.inc#L70): Finds the first free flag in a count-element slot bitmap, marks it used and returns its index; exhaustion terminates.

- [`numeric`](../runtime/memory/datastack.c.inc#L78): Evaluates the selected signed integer operation with the reference runtime's overflow and zero-divisor failures.

- [`region_error`](../runtime/memory/datastack.c.inc#L94): Reports an invalid or exhausted region operation and terminates the process.

- [`region_default_capacity`](../runtime/memory/datastack.c.inc#L99): Computes the region-stack byte budget from OS memory and CPU information, bounded by PTRDIFF_MAX.

- [`region_metadata`](../runtime/memory/datastack.c.inc#L121): Maps zero-initialized RegionBand metadata independently of storage whose scope may end first.

- [`region_reserve`](../runtime/memory/datastack.c.inc#L132): Reserves a virtual address range for a band and records its capacity and per-region limit; commits no payload yet.

- [`region_release_band`](../runtime/memory/datastack.c.inc#L147): Unmaps an empty band and its separately mapped metadata when applicable; no active region may remain.

- [`region_stride`](../runtime/memory/datastack.c.inc#L163): Rounds a region width to max_align_t with checked size arithmetic.

- [`region_enter`](../runtime/memory/datastack.c.inc#L169): Creates a child region scope with the explicit or inferred count; the caller holds the runtime lock.

- [`region_restore`](../runtime/memory/datastack.c.inc#L182): Closes region scopes back to mark, releasing only empty bands so transferred live regions survive; requires the lock.

- [`region_new`](../runtime/memory/datastack.c.inc#L191): Links a stable descriptor into an available band or a dedicated band; owned regions store child-region cleanup links. Requires the runtime lock.

- [`region_drop`](../runtime/memory/datastack.c.inc#L223): Destroys owned child regions before unlinking this region and releasing an empty closed band; requires the runtime lock.

- [`region_add`](../runtime/memory/datastack.c.inc#L240): Commits pages as needed and returns one new element slot; terminates at the region limit. Requires the runtime lock.

### `runtime/memory/pools.c.inc`

- [`destroy_region`](../runtime/memory/pools.c.inc#L6): Cleanup-callback adapter for a region descriptor; releases its payload through the synchronized region path.

- [`storage_error`](../runtime/memory/pools.c.inc#L8): Reports fixed datastack exhaustion or an invalid storage operation and terminates the process.

- [`new_pool`](../runtime/memory/pools.c.inc#L10): Allocates a pool descriptor, atomic occupancy bytes and fixed slots on the datastack; validates sizes and arm counts.

- [`pool_take`](../runtime/memory/pools.c.inc#L15): Claims a free slot in the requested arm, zeroes it and returns an Owned descriptor; exhaustion terminates.

- [`put`](../runtime/memory/pools.c.inc#L19): Calls a live allocation's typed cleanup callback before releasing its pool slot, then clears the descriptor's pool link.

- [`dispose_owned`](../runtime/memory/pools.c.inc#L21): Cleanup-callback adapter that destroys and releases the Owned descriptor at pointer.

### `runtime/memory/reclaim.c.inc`

- [`release_pages`](../runtime/memory/reclaim.c.inc#L8): Requests OS decommit/discard for a page range; reports whether the platform operation succeeded.

- [`reclaim_after`](../runtime/memory/reclaim.c.inc#L19): Returns complete unused pages beyond live to the OS when forced or above threshold; updates committed only on success.

- [`reclaim_band`](../runtime/memory/reclaim.c.inc#L29): Computes the last live byte across active regions before considering complete tail pages for reclamation.

- [`reclaim_scope`](../runtime/memory/reclaim.c.inc#L39): Reclaims unused fixed/region tail pages using the configured thresholds or force, without releasing live storage.

### `runtime/memory/region_release.c.inc`

- [`region_release`](../runtime/memory/region_release.c.inc#L5): Releases the global region band after its live values have been destroyed.

### `runtime/runtime_api.c.inc`

- [`corbo_runtime_abi_version`](../runtime/runtime_api.c.inc#L6): Returns the experimental C ABI version; clients must use the matching runtime header.

- [`corbo_runtime_init`](../runtime/runtime_api.c.inc#L8): Initializes C-owned runtime storage with optional fixed-stack, region-stack and region-width budgets; repeated initialization terminates.

- [`corbo_runtime_shutdown`](../runtime/runtime_api.c.inc#L15): Releases the calling thread's C-owned runtime after all live resources and workers have been cleaned up; a stopped runtime is a no-op.

- [`corbo_datastack_alloc`](../runtime/runtime_api.c.inc#L22): Allocates count aligned elements on the calling thread's initialized stack; invalid size/alignment or exhaustion terminates.

- [`corbo_datastack_mark`](../runtime/runtime_api.c.inc#L28): Returns a mark containing the current cursor, stack identity and region-scope marker.

- [`corbo_datastack_info`](../runtime/runtime_api.c.inc#L32): Returns the current cursor, committed-byte boundary and fixed-stack capacity.

- [`corbo_datastack_rewind`](../runtime/runtime_api.c.inc#L36): Restores a mark from this stack after caller cleanup; rejects foreign or forward marks and preserves live transferred regions.

- [`corbo_free_pages`](../runtime/runtime_api.c.inc#L47): Requests immediate reclamation of complete unused pages without changing live values or their reserved address ranges.

- [`corbo_pool_create`](../runtime/runtime_api.c.inc#L49): Creates fixed slots for each enum arm on the current datastack; zero element width or invalid capacity terminates.

- [`corbo_pool_take`](../runtime/runtime_api.c.inc#L54): Claims a free slot in arm and returns its allocation descriptor; invalid arms or exhaustion terminate.

- [`corbo_allocation_data`](../runtime/runtime_api.c.inc#L59): Returns an allocation's payload address without transferring ownership or extending its lifetime.

- [`corbo_allocation_drop`](../runtime/runtime_api.c.inc#L61): Destroys a live allocation before releasing its slot and clears its pool link; a cleared descriptor is harmless.

- [`corbo_region_enter`](../runtime/runtime_api.c.inc#L63): Enters a local region scope with the requested maximum region size and count budget.

- [`corbo_region_new`](../runtime/runtime_api.c.inc#L73): Initializes a stable caller-owned region descriptor for element_size bytes per item; dedicated selects independent band storage.

- [`corbo_region_push`](../runtime/runtime_api.c.inc#L78): Appends one uninitialized region element and returns its address; region exhaustion terminates.

- [`corbo_region_drop`](../runtime/runtime_api.c.inc#L80): Destroys child-region links, releases payload storage and zeroes the caller's region descriptor.

- [`corbo_map_new`](../runtime/runtime_api.c.inc#L82): Maps a map descriptor and initializes its stable region storage with an optional element cleanup callback.

- [`corbo_map_get`](../runtime/runtime_api.c.inc#L84): Returns the stored value address for key, or zero when absent; the map retains ownership.

- [`corbo_map_insert`](../runtime/runtime_api.c.inc#L86): Moves incoming bytes into a stable entry. Returns true and moves the replaced bytes into previous when the key exists.

- [`corbo_map_remove`](../runtime/runtime_api.c.inc#L90): Unlinks key and moves its value into previous; returns false without writing when absent and indexes the freed slot for reuse.

- [`corbo_map_drop`](../runtime/runtime_api.c.inc#L92): Clears the caller's map pointer, destroys remaining values with dispose, then releases payload and descriptor storage.
