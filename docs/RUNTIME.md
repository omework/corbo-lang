# Corbo runtime source reference

Generated from source documentation. Do not edit this reference by hand.

These are internal runtime entry points, not ordinary public Corbo APIs.
Raw addresses require live, aligned storage and the documented synchronization.
The [runtime guide](../runtime/corbo/README.md) explains the checked/unchecked boundary.
The [C ABI](../runtime/corbo_runtime.h) and [C reference](../runtime/README.md) retain their source comments.

Regenerate with `python3 scripts/stdlib_docs.py --runtime > docs/RUNTIME.md`.

## Modules

- [`runtime::api`](#runtimeapi)
- [`runtime::channel`](#runtimechannel)
- [`runtime::channel_primitives`](#runtimechannel_primitives)
- [`runtime::collections`](#runtimecollections)
- [`runtime::completion`](#runtimecompletion)
- [`runtime::completion_primitives`](#runtimecompletion_primitives)
- [`runtime::memory`](#runtimememory)
- [`runtime::metrics`](#runtimemetrics)
- [`runtime::mutex`](#runtimemutex)
- [`runtime::mutex_primitives`](#runtimemutex_primitives)
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


## `runtime::channel`

Bounded FIFO channel policy, native waits and persistent async registrations.

### `channel_create`

[channel.crb:5](../runtime/corbo/channel.crb#L5)

```rust
fn channel_create(capacity:usize,width:usize)->usize
```

Reserves fixed-capacity ring storage; a zero capacity is not a rendezvous channel.

### `channel_wake_one`

[channel.crb:17](../runtime/corbo/channel.crb#L17)

```rust
fn channel_wake_one(raw:usize,side:usize)
```

Selects one FIFO waiter, preserving its registration until its next poll.
task_enqueue only schedules: it never polls inline while this lock is held.

### `channel_unlink`

[channel.crb:35](../runtime/corbo/channel.crb#L35)

```rust
fn channel_unlink(task:usize)
```

Unlinks a queued/notified wait record before its task storage can be reclaimed.
caller holds task_lock; forwarding a notification avoids leaving ready work asleep.

### `channel_send`

[channel.crb:54](../runtime/corbo/channel.crb#L54)

```rust
fn channel_send(raw:usize,input:usize,epoch:usize,blocking:bool)->i64
```

Returns 0 after moving bytes, 1 for full, 2 for closed; records the observed epoch.

### `channel_receive`

[channel.crb:71](../runtime/corbo/channel.crb#L71)

```rust
fn channel_receive(raw:usize,output:usize,epoch:usize,blocking:bool)->i64
```

Returns 0 with a moved value, 1 for empty/open, 2 for closed/drained.

### `channel_close`

[channel.crb:90](../runtime/corbo/channel.crb#L90)

```rust
fn channel_close(raw:usize)
```

Closes once and wakes both sides; queued values remain available to receivers.

### `channel_poll`

[channel.crb:102](../runtime/corbo/channel.crb#L102)

```rust
fn channel_poll(task:usize,raw:usize,epoch:u64,sending:bool)->bool
```

Polls an epoch-based registration atomically with the readiness predicate.

### `channel_detach`

[channel.crb:121](../runtime/corbo/channel.crb#L121)

```rust
fn channel_detach(task:usize)
```

Called before releasing every Future frame; no waiter may retain its address.

### `channel_destroy`

[channel.crb:129](../runtime/corbo/channel.crb#L129)

```rust
fn channel_destroy(raw:usize)
```

Frees a closed, drained channel after all borrowed users and registrations have ended.


## `runtime::channel_primitives`

Native addresses, memory copies and scheduler-lock operations for bounded channels.

### `channel_allocate`

[channel_primitives.crb:5](../runtime/corbo/channel_primitives.crb#L5)

```rust
fn channel_allocate()->usize
```

Allocates metadata; payload storage is initialized separately under the runtime lock.

### `channel_storage`

[channel_primitives.crb:11](../runtime/corbo/channel_primitives.crb#L11)

```rust
fn channel_storage(raw:usize,capacity:usize,width:usize)
```

Creates a detached managed region retained by the channel until destruction.

### `channel_free`

[channel_primitives.crb:21](../runtime/corbo/channel_primitives.crb#L21)

```rust
fn channel_free(raw:usize)
```

Releases detached payload storage before its stable metadata.

### `channel_metadata_size`

[channel_primitives.crb:30](../runtime/corbo/channel_primitives.crb#L30)

```rust
fn channel_metadata_size()->usize
```

Exact extent of the stable channel control block.

### `channel_epoch_write`

[channel_primitives.crb:36](../runtime/corbo/channel_primitives.crb#L36)

```rust
fn channel_epoch_write(pointer:usize,value:u64)
```

Stores the observed epoch independently of pointer width.

### `channel_lock`

[channel_primitives.crb:40](../runtime/corbo/channel_primitives.crb#L40)

```rust
fn channel_lock()
```

Acquires the short scheduler lock even in a program without launched workers.

### `channel_unlock`

[channel_primitives.crb:42](../runtime/corbo/channel_primitives.crb#L42)

```rust
fn channel_unlock()
```

Releases the channel/scheduler state lock.

### `channel_condition_wait`

[channel_primitives.crb:44](../runtime/corbo/channel_primitives.crb#L44)

```rust
fn channel_condition_wait()
```

Atomically parks a native thread, releasing and reacquiring task_lock.

### `channel_broadcast`

[channel_primitives.crb:46](../runtime/corbo/channel_primitives.crb#L46)

```rust
fn channel_broadcast()
```

Wakes native condition waiters; the caller holds task_lock.

### `channel_get_capacity`

[channel_primitives.crb:48](../runtime/corbo/channel_primitives.crb#L48)

```rust
fn channel_get_capacity(raw:usize)->usize
```

Reads the channel's capacity; caller holds task_lock.

### `channel_set_capacity`

[channel_primitives.crb:54](../runtime/corbo/channel_primitives.crb#L54)

```rust
fn channel_set_capacity(raw:usize,value:usize)
```

Updates the channel's capacity; caller holds task_lock.

### `channel_get_width`

[channel_primitives.crb:56](../runtime/corbo/channel_primitives.crb#L56)

```rust
fn channel_get_width(raw:usize)->usize
```

Reads the channel's width; caller holds task_lock.

### `channel_set_width`

[channel_primitives.crb:62](../runtime/corbo/channel_primitives.crb#L62)

```rust
fn channel_set_width(raw:usize,value:usize)
```

Updates the channel's width; caller holds task_lock.

### `channel_get_count`

[channel_primitives.crb:64](../runtime/corbo/channel_primitives.crb#L64)

```rust
fn channel_get_count(raw:usize)->usize
```

Reads the channel's count; caller holds task_lock.

### `channel_set_count`

[channel_primitives.crb:70](../runtime/corbo/channel_primitives.crb#L70)

```rust
fn channel_set_count(raw:usize,value:usize)
```

Updates the channel's count; caller holds task_lock.

### `channel_get_head`

[channel_primitives.crb:72](../runtime/corbo/channel_primitives.crb#L72)

```rust
fn channel_get_head(raw:usize)->usize
```

Reads the channel's head; caller holds task_lock.

### `channel_set_head`

[channel_primitives.crb:78](../runtime/corbo/channel_primitives.crb#L78)

```rust
fn channel_set_head(raw:usize,value:usize)
```

Updates the channel's head; caller holds task_lock.

### `channel_get_epoch`

[channel_primitives.crb:80](../runtime/corbo/channel_primitives.crb#L80)

```rust
fn channel_get_epoch(raw:usize)->u64
```

Reads the channel's epoch; caller holds task_lock.

### `channel_set_epoch`

[channel_primitives.crb:86](../runtime/corbo/channel_primitives.crb#L86)

```rust
fn channel_set_epoch(raw:usize,value:u64)
```

Updates the channel's epoch; caller holds task_lock.

### `channel_get_closed`

[channel_primitives.crb:88](../runtime/corbo/channel_primitives.crb#L88)

```rust
fn channel_get_closed(raw:usize)->bool
```

Reads the channel's closed; caller holds task_lock.

### `channel_set_closed`

[channel_primitives.crb:94](../runtime/corbo/channel_primitives.crb#L94)

```rust
fn channel_set_closed(raw:usize,value:bool)
```

Updates the channel's closed; caller holds task_lock.

### `channel_get_heads`

[channel_primitives.crb:96](../runtime/corbo/channel_primitives.crb#L96)

```rust
fn channel_get_heads(raw:usize,side:usize)->usize
```

Reads one side's heads pointer; side 0 receives, side 1 sends.

### `channel_set_heads`

[channel_primitives.crb:102](../runtime/corbo/channel_primitives.crb#L102)

```rust
fn channel_set_heads(raw:usize,side:usize,value:usize)
```

Updates one side's heads pointer under task_lock.

### `channel_get_tails`

[channel_primitives.crb:104](../runtime/corbo/channel_primitives.crb#L104)

```rust
fn channel_get_tails(raw:usize,side:usize)->usize
```

Reads one side's tails pointer; side 0 receives, side 1 sends.

### `channel_set_tails`

[channel_primitives.crb:110](../runtime/corbo/channel_primitives.crb#L110)

```rust
fn channel_set_tails(raw:usize,side:usize,value:usize)
```

Updates one side's tails pointer under task_lock.

### `channel_slot`

[channel_primitives.crb:112](../runtime/corbo/channel_primitives.crb#L112)

```rust
fn channel_slot(raw:usize,index:usize)->usize
```

Addresses one aligned slot in the channel's fixed ring.

### `channel_waiting`

[channel_primitives.crb:118](../runtime/corbo/channel_primitives.crb#L118)

```rust
fn channel_waiting(task:usize)->bool
```

Reads whether an existing task wait record belongs to a channel.

### `channel_mark`

[channel_primitives.crb:124](../runtime/corbo/channel_primitives.crb#L124)

```rust
fn channel_mark(task:usize,value:bool)
```

Marks a task's intrusive record as channel-owned.


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

[memory.crb:44](../runtime/corbo/memory.crb#L44)

```rust
fn push(size:usize,alignment:usize,count:usize)->usize
```

Reserves count aligned fixed-size elements at the current cursor; checks multiplication, alignment and capacity before advancing.

### `release`

[memory.crb:66](../runtime/corbo/memory.crb#L66)

```rust
fn release()
```

Unmaps the calling thread's fixed datastack after its values and workers have been cleaned up.

### `take`

[memory.crb:73](../runtime/corbo/memory.crb#L73)

```rust
fn take(used:usize,count:usize)->usize
```

Finds the first free flag in a count-element slot bitmap, marks it used and returns its index; exhaustion terminates.

### `magnitude`

[memory.crb:87](../runtime/corbo/memory.crb#L87)

```rust
fn magnitude(value:i64)->usize
```

Returns an unsigned magnitude without overflowing on the minimum signed 64-bit integer.

### `numeric`

[memory.crb:94](../runtime/corbo/memory.crb#L94)

```rust
fn numeric(op:i64,left:i64,right:i64)->i64
```

Evaluates the selected signed integer operation with the reference runtime's overflow and zero-divisor failures.

### `region_default_capacity`

[memory.crb:143](../runtime/corbo/memory.crb#L143)

```rust
fn region_default_capacity()->usize
```

Computes the region-stack byte budget from OS memory and CPU information, bounded by PTRDIFF_MAX.

### `region_metadata`

[memory.crb:168](../runtime/corbo/memory.crb#L168)

```rust
fn region_metadata()->usize
```

Maps zero-initialized RegionBand metadata independently of storage whose scope may end first.

### `region_reserve`

[memory.crb:176](../runtime/corbo/memory.crb#L176)

```rust
fn region_reserve(band:usize,bytes:usize,maximum:usize)
```

Reserves a virtual address range for a band and records its capacity and per-region limit; commits no payload yet.

### `region_release_band`

[memory.crb:190](../runtime/corbo/memory.crb#L190)

```rust
fn region_release_band(band:usize)
```

Unmaps an empty band and its separately mapped metadata when applicable; no active region may remain.

### `region_stride`

[memory.crb:199](../runtime/corbo/memory.crb#L199)

```rust
fn region_stride(bytes:usize)->usize
```

Rounds a region width to max_align_t with checked size arithmetic.

### `region_enter`

[memory.crb:207](../runtime/corbo/memory.crb#L207)

```rust
fn region_enter(bytes:usize,count:usize,inferred:usize)
```

Creates a child region scope with the explicit or inferred count; the caller holds the runtime lock.

### `region_restore`

[memory.crb:239](../runtime/corbo/memory.crb#L239)

```rust
fn region_restore(mark:usize)
```

Closes region scopes back to mark, releasing only empty bands so transferred live regions survive; requires the lock.

### `region_new`

[memory.crb:250](../runtime/corbo/memory.crb#L250)

```rust
fn region_new(region:usize,width:usize,owned:i32,dedicated:bool)
```

Links a stable descriptor into an available band or a dedicated band; owned regions store child-region cleanup links. Requires the runtime lock.

### `region_drop`

[memory.crb:314](../runtime/corbo/memory.crb#L314)

```rust
fn region_drop(region:usize)
```

Destroys owned child regions before unlinking this region and releasing an empty closed band; requires the runtime lock.

### `region_add`

[memory.crb:340](../runtime/corbo/memory.crb#L340)

```rust
fn region_add(region:usize)->usize
```

Commits pages as needed and returns one new element slot; terminates at the region limit. Requires the runtime lock.

### `region_release`

[memory.crb:361](../runtime/corbo/memory.crb#L361)

```rust
fn region_release()
```

Releases the global region band after its live values have been destroyed.

### `new_pool`

[memory.crb:368](../runtime/corbo/memory.crb#L368)

```rust
fn new_pool(slots:usize,bytes:usize,arms:usize)->usize
```

Allocates a pool descriptor, atomic occupancy bytes and fixed slots on the datastack; validates sizes and arm counts.

### `pool_try_take`

[memory.crb:390](../runtime/corbo/memory.crb#L390)

```rust
fn pool_try_take(out:usize,pool:usize,arm:usize)->bool
```

Claims and zeroes a free slot; returns false without changing the pool if full.

### `pool_take`

[memory.crb:411](../runtime/corbo/memory.crb#L411)

```rust
fn pool_take(out:usize,pool:usize,arm:usize)
```

Claims a free slot or terminates if the selected arm is full.

### `put`

[memory.crb:415](../runtime/corbo/memory.crb#L415)

```rust
fn put(value:usize)
```

Calls a live allocation's typed cleanup callback before releasing its pool slot, then clears the descriptor's pool link.

### `value_region_new`

[memory.crb:429](../runtime/corbo/memory.crb#L429)

```rust
fn value_region_new(region:usize,width:usize,owned:i32,dedicated:bool)
```

Initializes a region while holding the shared runtime lock; the descriptor must remain at a stable address.

### `value_region_add`

[memory.crb:435](../runtime/corbo/memory.crb#L435)

```rust
fn value_region_add(region:usize)->usize
```

Appends one region slot under the runtime lock and returns its address.

### `value_region_drop`

[memory.crb:442](../runtime/corbo/memory.crb#L442)

```rust
fn value_region_drop(region:usize)
```

Unlinks and releases a region under the runtime lock after owned child cleanup.

### `scoped_region_enter`

[memory.crb:448](../runtime/corbo/memory.crb#L448)

```rust
fn scoped_region_enter(bytes:usize,count:usize,inferred:usize)
```

Enters a region scope under the runtime lock using explicit and inferred slot budgets.

### `scoped_region_restore`

[memory.crb:454](../runtime/corbo/memory.crb#L454)

```rust
fn scoped_region_restore(mark:usize)
```

Restores the saved region-scope mark under the runtime lock while preserving live transferred regions.

### `destroy_region`

[memory.crb:460](../runtime/corbo/memory.crb#L460)

```rust
fn destroy_region(pointer:usize)
```

Cleanup-callback adapter for a region descriptor; releases its payload through the synchronized region path.

### `dispose_owned`

[memory.crb:464](../runtime/corbo/memory.crb#L464)

```rust
fn dispose_owned(pointer:usize)
```

Cleanup-callback adapter that destroys and releases the Owned descriptor at pointer.


## `runtime::metrics`

Process-wide atomic accounting for managed storage, independent of OS RSS.

### `memory_cursor`

[metrics.crb:5](../runtime/corbo/metrics.crb#L5)

```rust
fn memory_cursor(next:usize)
```

Changes the fixed cursor after cleanup and removes retired pool bookkeeping.

### `corbo_memory_stats`

[metrics.crb:17](../runtime/corbo/metrics.crb#L17)

```rust
fn corbo_memory_stats(out:usize)
```

Samples atomic counters; concurrent fields may describe adjacent instants.


## `runtime::mutex`

Synchronous thread-owned guards and asynchronous FIFO task ownership.

### `mutex_create`

[mutex.crb:5](../runtime/corbo/mutex.crb#L5)

```rust
fn mutex_create(asynchronous:bool)->usize
```

Creates stable native state without copying an initialized native lock on Corbo moves.

### `mutex_acquire`

[mutex.crb:11](../runtime/corbo/mutex.crb#L11)

```rust
fn mutex_acquire(raw:usize)
```

Acquires the blocking variant; the guard is bound to this native thread.

### `mutex_handoff`

[mutex.crb:14](../runtime/corbo/mutex.crb#L14)

```rust
fn mutex_handoff(raw:usize)
```

Publishes one reserved waiter and wakes its root; caller holds task_lock.

### `mutex_poll`

[mutex.crb:33](../runtime/corbo/mutex.crb#L33)

```rust
fn mutex_poll(child:usize,raw:usize)->bool
```

Polls once: acquire, consume a handoff, or park the root without a lost wakeup.

### `mutex_release`

[mutex.crb:64](../runtime/corbo/mutex.crb#L64)

```rust
fn mutex_release(raw:usize)
```

Releases a guard; async ownership can finish on a different worker thread.

### `mutex_detach`

[mutex.crb:73](../runtime/corbo/mutex.crb#L73)

```rust
fn mutex_detach(child:usize)
```

Unlinks dropped waiting state or hands an abandoned reservation to its successor.

### `mutex_destroy`

[mutex.crb:101](../runtime/corbo/mutex.crb#L101)

```rust
fn mutex_destroy(raw:usize)
```

Destroys the underlying resource after checked guard/waiter lifetimes have ended.


## `runtime::mutex_primitives`

Typed native mutex operations and accesses to stable scheduler-owned wait records.

### `mutex_allocate`

[mutex_primitives.crb:5](../runtime/corbo/mutex_primitives.crb#L5)

```rust
fn mutex_allocate(asynchronous:bool)->usize
```

Allocates stable native mutex metadata; constructor failure is reported as zero.

### `size_mutex_state`

[mutex_primitives.crb:18](../runtime/corbo/mutex_primitives.crb#L18)

```rust
fn size_mutex_state()->usize
```

Returns the exact native metadata extent on this platform.

### `mutex_native_lock`

[mutex_primitives.crb:24](../runtime/corbo/mutex_primitives.crb#L24)

```rust
fn mutex_native_lock(raw:usize)
```

Blocks on a native mutex and records the acquiring thread for guard cleanup.

### `mutex_native_unlock`

[mutex_primitives.crb:31](../runtime/corbo/mutex_primitives.crb#L31)

```rust
fn mutex_native_unlock(raw:usize)
```

Releases a synchronous guard only on its acquiring thread.

### `mutex_native_destroy`

[mutex_primitives.crb:38](../runtime/corbo/mutex_primitives.crb#L38)

```rust
fn mutex_native_destroy(raw:usize)
```

Destroys unlocked native metadata after all guard/waiter references have ended.

### `g_mutex_head`

[mutex_primitives.crb:48](../runtime/corbo/mutex_primitives.crb#L48)

```rust
fn g_mutex_head(raw:usize)->usize
```

Reads CorboMutexState.head; caller holds the scheduler lock for shared queue fields.

### `s_mutex_head`

[mutex_primitives.crb:54](../runtime/corbo/mutex_primitives.crb#L54)

```rust
fn s_mutex_head(raw:usize,value:usize)
```

Updates CorboMutexState.head; caller holds the scheduler lock for shared queue fields.

### `g_mutex_tail`

[mutex_primitives.crb:59](../runtime/corbo/mutex_primitives.crb#L59)

```rust
fn g_mutex_tail(raw:usize)->usize
```

Reads CorboMutexState.tail; caller holds the scheduler lock for shared queue fields.

### `s_mutex_tail`

[mutex_primitives.crb:65](../runtime/corbo/mutex_primitives.crb#L65)

```rust
fn s_mutex_tail(raw:usize,value:usize)
```

Updates CorboMutexState.tail; caller holds the scheduler lock for shared queue fields.

### `g_mutex_reservation`

[mutex_primitives.crb:70](../runtime/corbo/mutex_primitives.crb#L70)

```rust
fn g_mutex_reservation(raw:usize)->usize
```

Reads CorboMutexState.reservation; caller holds the scheduler lock for shared queue fields.

### `s_mutex_reservation`

[mutex_primitives.crb:76](../runtime/corbo/mutex_primitives.crb#L76)

```rust
fn s_mutex_reservation(raw:usize,value:usize)
```

Updates CorboMutexState.reservation; caller holds the scheduler lock for shared queue fields.

### `g_mutex_held`

[mutex_primitives.crb:81](../runtime/corbo/mutex_primitives.crb#L81)

```rust
fn g_mutex_held(raw:usize)->bool
```

Reads CorboMutexState.held; caller holds the scheduler lock for shared queue fields.

### `s_mutex_held`

[mutex_primitives.crb:87](../runtime/corbo/mutex_primitives.crb#L87)

```rust
fn s_mutex_held(raw:usize,value:bool)
```

Updates CorboMutexState.held; caller holds the scheduler lock for shared queue fields.

### `g_mutex_asynchronous`

[mutex_primitives.crb:92](../runtime/corbo/mutex_primitives.crb#L92)

```rust
fn g_mutex_asynchronous(raw:usize)->bool
```

Reads CorboMutexState.asynchronous; caller holds the scheduler lock for shared queue fields.

### `s_mutex_asynchronous`

[mutex_primitives.crb:98](../runtime/corbo/mutex_primitives.crb#L98)

```rust
fn s_mutex_asynchronous(raw:usize,value:bool)
```

Updates CorboMutexState.asynchronous; caller holds the scheduler lock for shared queue fields.

### `g_mutex_next`

[mutex_primitives.crb:103](../runtime/corbo/mutex_primitives.crb#L103)

```rust
fn g_mutex_next(raw:usize)->usize
```

Reads Task.mutex_next; caller holds the scheduler lock for shared queue fields.

### `s_mutex_next`

[mutex_primitives.crb:109](../runtime/corbo/mutex_primitives.crb#L109)

```rust
fn s_mutex_next(raw:usize,value:usize)
```

Updates Task.mutex_next; caller holds the scheduler lock for shared queue fields.

### `g_mutex_owner`

[mutex_primitives.crb:114](../runtime/corbo/mutex_primitives.crb#L114)

```rust
fn g_mutex_owner(raw:usize)->usize
```

Reads Task.mutex_owner; caller holds the scheduler lock for shared queue fields.

### `s_mutex_owner`

[mutex_primitives.crb:120](../runtime/corbo/mutex_primitives.crb#L120)

```rust
fn s_mutex_owner(raw:usize,value:usize)
```

Updates Task.mutex_owner; caller holds the scheduler lock for shared queue fields.

### `g_mutex_reserved`

[mutex_primitives.crb:125](../runtime/corbo/mutex_primitives.crb#L125)

```rust
fn g_mutex_reserved(raw:usize)->bool
```

Reads Task.mutex_reserved; caller holds the scheduler lock for shared queue fields.

### `s_mutex_reserved`

[mutex_primitives.crb:131](../runtime/corbo/mutex_primitives.crb#L131)

```rust
fn s_mutex_reserved(raw:usize,value:bool)
```

Updates Task.mutex_reserved; caller holds the scheduler lock for shared queue fields.


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

[primitives.crb:54](../runtime/corbo/primitives.crb#L54)

```rust
fn a_Region_len(pointer:usize)->usize
```

Returns the address of live element count in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Region_offset`

[primitives.crb:63](../runtime/corbo/primitives.crb#L63)

```rust
fn g_Region_offset(pointer:usize)->usize
```

Reads byte offset within its band in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Region_offset`

[primitives.crb:72](../runtime/corbo/primitives.crb#L72)

```rust
fn s_Region_offset(pointer:usize, value:usize)
```

Writes byte offset within its band in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Region_offset`

[primitives.crb:80](../runtime/corbo/primitives.crb#L80)

```rust
fn a_Region_offset(pointer:usize)->usize
```

Returns the address of byte offset within its band in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Region_bytes`

[primitives.crb:89](../runtime/corbo/primitives.crb#L89)

```rust
fn g_Region_bytes(pointer:usize)->usize
```

Reads maximum payload byte extent in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Region_bytes`

[primitives.crb:98](../runtime/corbo/primitives.crb#L98)

```rust
fn s_Region_bytes(pointer:usize, value:usize)
```

Writes maximum payload byte extent in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Region_bytes`

[primitives.crb:106](../runtime/corbo/primitives.crb#L106)

```rust
fn a_Region_bytes(pointer:usize)->usize
```

Returns the address of maximum payload byte extent in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Region_width`

[primitives.crb:115](../runtime/corbo/primitives.crb#L115)

```rust
fn g_Region_width(pointer:usize)->usize
```

Reads bytes per stored element in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Region_width`

[primitives.crb:124](../runtime/corbo/primitives.crb#L124)

```rust
fn s_Region_width(pointer:usize, value:usize)
```

Writes bytes per stored element in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Region_width`

[primitives.crb:132](../runtime/corbo/primitives.crb#L132)

```rust
fn a_Region_width(pointer:usize)->usize
```

Returns the address of bytes per stored element in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Region_next`

[primitives.crb:141](../runtime/corbo/primitives.crb#L141)

```rust
fn g_Region_next(pointer:usize)->usize
```

Reads next active-region link in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Region_next`

[primitives.crb:150](../runtime/corbo/primitives.crb#L150)

```rust
fn s_Region_next(pointer:usize, value:usize)
```

Writes next active-region link in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Region_next`

[primitives.crb:158](../runtime/corbo/primitives.crb#L158)

```rust
fn a_Region_next(pointer:usize)->usize
```

Returns the address of next active-region link in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Region_band`

[primitives.crb:167](../runtime/corbo/primitives.crb#L167)

```rust
fn g_Region_band(pointer:usize)->usize
```

Reads containing band link in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Region_band`

[primitives.crb:176](../runtime/corbo/primitives.crb#L176)

```rust
fn s_Region_band(pointer:usize, value:usize)
```

Writes containing band link in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Region_band`

[primitives.crb:184](../runtime/corbo/primitives.crb#L184)

```rust
fn a_Region_band(pointer:usize)->usize
```

Returns the address of containing band link in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Region_owned`

[primitives.crb:193](../runtime/corbo/primitives.crb#L193)

```rust
fn g_Region_owned(pointer:usize)->i32
```

Reads recursive child-region cleanup mode in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Region_owned`

[primitives.crb:202](../runtime/corbo/primitives.crb#L202)

```rust
fn s_Region_owned(pointer:usize, value:i32)
```

Writes recursive child-region cleanup mode in a live Region ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_Region`

[primitives.crb:209](../runtime/corbo/primitives.crb#L209)

```rust
fn size_Region()->usize
```

Returns the C ABI size in bytes of Region on this target.

### `align_Region`

[primitives.crb:217](../runtime/corbo/primitives.crb#L217)

```rust
fn align_Region()->usize
```

Returns the required C ABI alignment of Region on this target.

### `g_RegionBand_base`

[primitives.crb:226](../runtime/corbo/primitives.crb#L226)

```rust
fn g_RegionBand_base(pointer:usize)->usize
```

Reads reserved virtual-memory base in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionBand_base`

[primitives.crb:235](../runtime/corbo/primitives.crb#L235)

```rust
fn s_RegionBand_base(pointer:usize, value:usize)
```

Writes reserved virtual-memory base in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionBand_base`

[primitives.crb:243](../runtime/corbo/primitives.crb#L243)

```rust
fn a_RegionBand_base(pointer:usize)->usize
```

Returns the address of reserved virtual-memory base in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionBand_capacity`

[primitives.crb:252](../runtime/corbo/primitives.crb#L252)

```rust
fn g_RegionBand_capacity(pointer:usize)->usize
```

Reads reserved byte capacity in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionBand_capacity`

[primitives.crb:261](../runtime/corbo/primitives.crb#L261)

```rust
fn s_RegionBand_capacity(pointer:usize, value:usize)
```

Writes reserved byte capacity in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionBand_capacity`

[primitives.crb:269](../runtime/corbo/primitives.crb#L269)

```rust
fn a_RegionBand_capacity(pointer:usize)->usize
```

Returns the address of reserved byte capacity in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionBand_committed`

[primitives.crb:278](../runtime/corbo/primitives.crb#L278)

```rust
fn g_RegionBand_committed(pointer:usize)->usize
```

Reads committed byte boundary in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionBand_committed`

[primitives.crb:287](../runtime/corbo/primitives.crb#L287)

```rust
fn s_RegionBand_committed(pointer:usize, value:usize)
```

Writes committed byte boundary in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionBand_committed`

[primitives.crb:295](../runtime/corbo/primitives.crb#L295)

```rust
fn a_RegionBand_committed(pointer:usize)->usize
```

Returns the address of committed byte boundary in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionBand_limit`

[primitives.crb:304](../runtime/corbo/primitives.crb#L304)

```rust
fn g_RegionBand_limit(pointer:usize)->usize
```

Reads per-region byte limit in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionBand_limit`

[primitives.crb:313](../runtime/corbo/primitives.crb#L313)

```rust
fn s_RegionBand_limit(pointer:usize, value:usize)
```

Writes per-region byte limit in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionBand_limit`

[primitives.crb:321](../runtime/corbo/primitives.crb#L321)

```rust
fn a_RegionBand_limit(pointer:usize)->usize
```

Returns the address of per-region byte limit in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionBand_active`

[primitives.crb:330](../runtime/corbo/primitives.crb#L330)

```rust
fn g_RegionBand_active(pointer:usize)->usize
```

Reads ordered active-region list in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionBand_active`

[primitives.crb:339](../runtime/corbo/primitives.crb#L339)

```rust
fn s_RegionBand_active(pointer:usize, value:usize)
```

Writes ordered active-region list in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionBand_active`

[primitives.crb:347](../runtime/corbo/primitives.crb#L347)

```rust
fn a_RegionBand_active(pointer:usize)->usize
```

Returns the address of ordered active-region list in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionBand_parent`

[primitives.crb:356](../runtime/corbo/primitives.crb#L356)

```rust
fn g_RegionBand_parent(pointer:usize)->usize
```

Reads parent region-scope link in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionBand_parent`

[primitives.crb:365](../runtime/corbo/primitives.crb#L365)

```rust
fn s_RegionBand_parent(pointer:usize, value:usize)
```

Writes parent region-scope link in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionBand_parent`

[primitives.crb:373](../runtime/corbo/primitives.crb#L373)

```rust
fn a_RegionBand_parent(pointer:usize)->usize
```

Returns the address of parent region-scope link in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionBand_closed`

[primitives.crb:382](../runtime/corbo/primitives.crb#L382)

```rust
fn g_RegionBand_closed(pointer:usize)->i32
```

Reads closed-scope flag in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionBand_closed`

[primitives.crb:391](../runtime/corbo/primitives.crb#L391)

```rust
fn s_RegionBand_closed(pointer:usize, value:i32)
```

Writes closed-scope flag in a live RegionBand ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_RegionBand`

[primitives.crb:398](../runtime/corbo/primitives.crb#L398)

```rust
fn size_RegionBand()->usize
```

Returns the C ABI size in bytes of RegionBand on this target.

### `align_RegionBand`

[primitives.crb:406](../runtime/corbo/primitives.crb#L406)

```rust
fn align_RegionBand()->usize
```

Returns the required C ABI alignment of RegionBand on this target.

### `g_Pools_cap`

[primitives.crb:415](../runtime/corbo/primitives.crb#L415)

```rust
fn g_Pools_cap(pointer:usize)->usize
```

Reads slot count per arm in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Pools_cap`

[primitives.crb:424](../runtime/corbo/primitives.crb#L424)

```rust
fn s_Pools_cap(pointer:usize, value:usize)
```

Writes slot count per arm in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Pools_cap`

[primitives.crb:432](../runtime/corbo/primitives.crb#L432)

```rust
fn a_Pools_cap(pointer:usize)->usize
```

Returns the address of slot count per arm in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Pools_stride`

[primitives.crb:441](../runtime/corbo/primitives.crb#L441)

```rust
fn g_Pools_stride(pointer:usize)->usize
```

Reads aligned bytes per slot in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Pools_stride`

[primitives.crb:450](../runtime/corbo/primitives.crb#L450)

```rust
fn s_Pools_stride(pointer:usize, value:usize)
```

Writes aligned bytes per slot in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Pools_stride`

[primitives.crb:458](../runtime/corbo/primitives.crb#L458)

```rust
fn a_Pools_stride(pointer:usize)->usize
```

Returns the address of aligned bytes per slot in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Pools_arms`

[primitives.crb:467](../runtime/corbo/primitives.crb#L467)

```rust
fn g_Pools_arms(pointer:usize)->usize
```

Reads enum-arm count in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Pools_arms`

[primitives.crb:476](../runtime/corbo/primitives.crb#L476)

```rust
fn s_Pools_arms(pointer:usize, value:usize)
```

Writes enum-arm count in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Pools_arms`

[primitives.crb:484](../runtime/corbo/primitives.crb#L484)

```rust
fn a_Pools_arms(pointer:usize)->usize
```

Returns the address of enum-arm count in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Pools_data`

[primitives.crb:493](../runtime/corbo/primitives.crb#L493)

```rust
fn g_Pools_data(pointer:usize)->usize
```

Reads stable slot-storage base in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Pools_data`

[primitives.crb:502](../runtime/corbo/primitives.crb#L502)

```rust
fn s_Pools_data(pointer:usize, value:usize)
```

Writes stable slot-storage base in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Pools_data`

[primitives.crb:510](../runtime/corbo/primitives.crb#L510)

```rust
fn a_Pools_data(pointer:usize)->usize
```

Returns the address of stable slot-storage base in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Pools_used`

[primitives.crb:519](../runtime/corbo/primitives.crb#L519)

```rust
fn g_Pools_used(pointer:usize)->usize
```

Reads atomic occupancy-byte array in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Pools_used`

[primitives.crb:528](../runtime/corbo/primitives.crb#L528)

```rust
fn s_Pools_used(pointer:usize, value:usize)
```

Writes atomic occupancy-byte array in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Pools_used`

[primitives.crb:536](../runtime/corbo/primitives.crb#L536)

```rust
fn a_Pools_used(pointer:usize)->usize
```

Returns the address of atomic occupancy-byte array in a live Pools ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_Pools`

[primitives.crb:544](../runtime/corbo/primitives.crb#L544)

```rust
fn size_Pools()->usize
```

Returns the C ABI size in bytes of Pools on this target.

### `align_Pools`

[primitives.crb:552](../runtime/corbo/primitives.crb#L552)

```rust
fn align_Pools()->usize
```

Returns the required C ABI alignment of Pools on this target.

### `g_Owned_pool`

[primitives.crb:561](../runtime/corbo/primitives.crb#L561)

```rust
fn g_Owned_pool(pointer:usize)->usize
```

Reads source pool link, zero after release in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Owned_pool`

[primitives.crb:570](../runtime/corbo/primitives.crb#L570)

```rust
fn s_Owned_pool(pointer:usize, value:usize)
```

Writes source pool link, zero after release in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Owned_pool`

[primitives.crb:578](../runtime/corbo/primitives.crb#L578)

```rust
fn a_Owned_pool(pointer:usize)->usize
```

Returns the address of source pool link, zero after release in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Owned_slot`

[primitives.crb:587](../runtime/corbo/primitives.crb#L587)

```rust
fn g_Owned_slot(pointer:usize)->usize
```

Reads payload slot address in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Owned_slot`

[primitives.crb:596](../runtime/corbo/primitives.crb#L596)

```rust
fn s_Owned_slot(pointer:usize, value:usize)
```

Writes payload slot address in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Owned_slot`

[primitives.crb:604](../runtime/corbo/primitives.crb#L604)

```rust
fn a_Owned_slot(pointer:usize)->usize
```

Returns the address of payload slot address in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Owned_index`

[primitives.crb:613](../runtime/corbo/primitives.crb#L613)

```rust
fn g_Owned_index(pointer:usize)->usize
```

Reads physical slot index in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Owned_index`

[primitives.crb:622](../runtime/corbo/primitives.crb#L622)

```rust
fn s_Owned_index(pointer:usize, value:usize)
```

Writes physical slot index in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Owned_index`

[primitives.crb:630](../runtime/corbo/primitives.crb#L630)

```rust
fn a_Owned_index(pointer:usize)->usize
```

Returns the address of physical slot index in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Owned_destroy`

[primitives.crb:639](../runtime/corbo/primitives.crb#L639)

```rust
fn g_Owned_destroy(pointer:usize)->usize
```

Reads typed payload destructor callback in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Owned_destroy`

[primitives.crb:648](../runtime/corbo/primitives.crb#L648)

```rust
fn s_Owned_destroy(pointer:usize, value:usize)
```

Writes typed payload destructor callback in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Owned_destroy`

[primitives.crb:656](../runtime/corbo/primitives.crb#L656)

```rust
fn a_Owned_destroy(pointer:usize)->usize
```

Returns the address of typed payload destructor callback in a live Owned ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_Owned`

[primitives.crb:664](../runtime/corbo/primitives.crb#L664)

```rust
fn size_Owned()->usize
```

Returns the C ABI size in bytes of Owned on this target.

### `align_Owned`

[primitives.crb:672](../runtime/corbo/primitives.crb#L672)

```rust
fn align_Owned()->usize
```

Returns the required C ABI alignment of Owned on this target.

### `g_RegionOwner_region`

[primitives.crb:681](../runtime/corbo/primitives.crb#L681)

```rust
fn g_RegionOwner_region(pointer:usize)->usize
```

Reads owned child-region link in a live RegionOwner ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionOwner_region`

[primitives.crb:690](../runtime/corbo/primitives.crb#L690)

```rust
fn s_RegionOwner_region(pointer:usize, value:usize)
```

Writes owned child-region link in a live RegionOwner ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionOwner_region`

[primitives.crb:698](../runtime/corbo/primitives.crb#L698)

```rust
fn a_RegionOwner_region(pointer:usize)->usize
```

Returns the address of owned child-region link in a live RegionOwner ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionOwner_slot`

[primitives.crb:707](../runtime/corbo/primitives.crb#L707)

```rust
fn g_RegionOwner_slot(pointer:usize)->usize
```

Reads address of the child's live-slot flag in a live RegionOwner ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionOwner_slot`

[primitives.crb:716](../runtime/corbo/primitives.crb#L716)

```rust
fn s_RegionOwner_slot(pointer:usize, value:usize)
```

Writes address of the child's live-slot flag in a live RegionOwner ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionOwner_slot`

[primitives.crb:724](../runtime/corbo/primitives.crb#L724)

```rust
fn a_RegionOwner_slot(pointer:usize)->usize
```

Returns the address of address of the child's live-slot flag in a live RegionOwner ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_RegionOwner`

[primitives.crb:732](../runtime/corbo/primitives.crb#L732)

```rust
fn size_RegionOwner()->usize
```

Returns the C ABI size in bytes of RegionOwner on this target.

### `align_RegionOwner`

[primitives.crb:740](../runtime/corbo/primitives.crb#L740)

```rust
fn align_RegionOwner()->usize
```

Returns the required C ABI alignment of RegionOwner on this target.

### `a_RegionalMap_region`

[primitives.crb:749](../runtime/corbo/primitives.crb#L749)

```rust
fn a_RegionalMap_region(pointer:usize)->usize
```

Returns the address of stable entry-storage region in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionalMap_width`

[primitives.crb:758](../runtime/corbo/primitives.crb#L758)

```rust
fn g_RegionalMap_width(pointer:usize)->usize
```

Reads value byte width in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionalMap_width`

[primitives.crb:767](../runtime/corbo/primitives.crb#L767)

```rust
fn s_RegionalMap_width(pointer:usize, value:usize)
```

Writes value byte width in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionalMap_width`

[primitives.crb:775](../runtime/corbo/primitives.crb#L775)

```rust
fn a_RegionalMap_width(pointer:usize)->usize
```

Returns the address of value byte width in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionalMap_free_slot`

[primitives.crb:784](../runtime/corbo/primitives.crb#L784)

```rust
fn g_RegionalMap_free_slot(pointer:usize)->usize
```

Reads free-entry offset list head in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionalMap_free_slot`

[primitives.crb:793](../runtime/corbo/primitives.crb#L793)

```rust
fn s_RegionalMap_free_slot(pointer:usize, value:usize)
```

Writes free-entry offset list head in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionalMap_free_slot`

[primitives.crb:801](../runtime/corbo/primitives.crb#L801)

```rust
fn a_RegionalMap_free_slot(pointer:usize)->usize
```

Returns the address of free-entry offset list head in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_RegionalMap_dispose`

[primitives.crb:810](../runtime/corbo/primitives.crb#L810)

```rust
fn g_RegionalMap_dispose(pointer:usize)->usize
```

Reads value cleanup callback in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_RegionalMap_dispose`

[primitives.crb:819](../runtime/corbo/primitives.crb#L819)

```rust
fn s_RegionalMap_dispose(pointer:usize, value:usize)
```

Writes value cleanup callback in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_RegionalMap_dispose`

[primitives.crb:827](../runtime/corbo/primitives.crb#L827)

```rust
fn a_RegionalMap_dispose(pointer:usize)->usize
```

Returns the address of value cleanup callback in a live RegionalMap ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_RegionalMap`

[primitives.crb:835](../runtime/corbo/primitives.crb#L835)

```rust
fn size_RegionalMap()->usize
```

Returns the C ABI size in bytes of RegionalMap on this target.

### `align_RegionalMap`

[primitives.crb:843](../runtime/corbo/primitives.crb#L843)

```rust
fn align_RegionalMap()->usize
```

Returns the required C ABI alignment of RegionalMap on this target.

### `g_MapEntry_key`

[primitives.crb:852](../runtime/corbo/primitives.crb#L852)

```rust
fn g_MapEntry_key(pointer:usize)->u64
```

Reads normalized integer key bits in a live MapEntry ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_MapEntry_key`

[primitives.crb:861](../runtime/corbo/primitives.crb#L861)

```rust
fn s_MapEntry_key(pointer:usize, value:u64)
```

Writes normalized integer key bits in a live MapEntry ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_MapEntry_next`

[primitives.crb:869](../runtime/corbo/primitives.crb#L869)

```rust
fn g_MapEntry_next(pointer:usize)->usize
```

Reads next bucket-chain or free-list byte offset in a live MapEntry ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_MapEntry_next`

[primitives.crb:878](../runtime/corbo/primitives.crb#L878)

```rust
fn s_MapEntry_next(pointer:usize, value:usize)
```

Writes next bucket-chain or free-list byte offset in a live MapEntry ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_MapEntry_next`

[primitives.crb:886](../runtime/corbo/primitives.crb#L886)

```rust
fn a_MapEntry_next(pointer:usize)->usize
```

Returns the address of next bucket-chain or free-list byte offset in a live MapEntry ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_MapEntry`

[primitives.crb:894](../runtime/corbo/primitives.crb#L894)

```rust
fn size_MapEntry()->usize
```

Returns the C ABI size in bytes of MapEntry on this target.

### `align_MapEntry`

[primitives.crb:902](../runtime/corbo/primitives.crb#L902)

```rust
fn align_MapEntry()->usize
```

Returns the required C ABI alignment of MapEntry on this target.

### `g_Task_pc`

[primitives.crb:911](../runtime/corbo/primitives.crb#L911)

```rust
fn g_Task_pc(pointer:usize)->usize
```

Reads resume-state program counter in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_pc`

[primitives.crb:920](../runtime/corbo/primitives.crb#L920)

```rust
fn s_Task_pc(pointer:usize, value:usize)
```

Writes resume-state program counter in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_pc`

[primitives.crb:928](../runtime/corbo/primitives.crb#L928)

```rust
fn a_Task_pc(pointer:usize)->usize
```

Returns the address of resume-state program counter in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_poll`

[primitives.crb:937](../runtime/corbo/primitives.crb#L937)

```rust
fn g_Task_poll(pointer:usize)->usize
```

Reads typed poll/clear callback in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_poll`

[primitives.crb:946](../runtime/corbo/primitives.crb#L946)

```rust
fn s_Task_poll(pointer:usize, value:usize)
```

Writes typed poll/clear callback in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_poll`

[primitives.crb:954](../runtime/corbo/primitives.crb#L954)

```rust
fn a_Task_poll(pointer:usize)->usize
```

Returns the address of typed poll/clear callback in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_next`

[primitives.crb:963](../runtime/corbo/primitives.crb#L963)

```rust
fn g_Task_next(pointer:usize)->usize
```

Reads ready-queue next link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_next`

[primitives.crb:972](../runtime/corbo/primitives.crb#L972)

```rust
fn s_Task_next(pointer:usize, value:usize)
```

Writes ready-queue next link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_next`

[primitives.crb:980](../runtime/corbo/primitives.crb#L980)

```rust
fn a_Task_next(pointer:usize)->usize
```

Returns the address of ready-queue next link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_failed`

[primitives.crb:989](../runtime/corbo/primitives.crb#L989)

```rust
fn g_Task_failed(pointer:usize)->bool
```

Reads launch-failure flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_failed`

[primitives.crb:998](../runtime/corbo/primitives.crb#L998)

```rust
fn s_Task_failed(pointer:usize, value:bool)
```

Writes launch-failure flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_done`

[primitives.crb:1006](../runtime/corbo/primitives.crb#L1006)

```rust
fn g_Task_done(pointer:usize)->bool
```

Reads completion-publication flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_done`

[primitives.crb:1015](../runtime/corbo/primitives.crb#L1015)

```rust
fn s_Task_done(pointer:usize, value:bool)
```

Writes completion-publication flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_abandoned`

[primitives.crb:1023](../runtime/corbo/primitives.crb#L1023)

```rust
fn g_Task_abandoned(pointer:usize)->bool
```

Reads worker-owned final-cleanup flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_abandoned`

[primitives.crb:1032](../runtime/corbo/primitives.crb#L1032)

```rust
fn s_Task_abandoned(pointer:usize, value:bool)
```

Writes worker-owned final-cleanup flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_discard`

[primitives.crb:1040](../runtime/corbo/primitives.crb#L1040)

```rust
fn g_Task_discard(pointer:usize)->usize
```

Reads typed abandoned-task cleanup callback in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_discard`

[primitives.crb:1049](../runtime/corbo/primitives.crb#L1049)

```rust
fn s_Task_discard(pointer:usize, value:usize)
```

Writes typed abandoned-task cleanup callback in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_discard`

[primitives.crb:1057](../runtime/corbo/primitives.crb#L1057)

```rust
fn a_Task_discard(pointer:usize)->usize
```

Returns the address of typed abandoned-task cleanup callback in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_root`

[primitives.crb:1066](../runtime/corbo/primitives.crb#L1066)

```rust
fn g_Task_root(pointer:usize)->usize
```

Reads outer polling-root link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_root`

[primitives.crb:1075](../runtime/corbo/primitives.crb#L1075)

```rust
fn s_Task_root(pointer:usize, value:usize)
```

Writes outer polling-root link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_root`

[primitives.crb:1083](../runtime/corbo/primitives.crb#L1083)

```rust
fn a_Task_root(pointer:usize)->usize
```

Returns the address of outer polling-root link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_waiter`

[primitives.crb:1092](../runtime/corbo/primitives.crb#L1092)

```rust
fn g_Task_waiter(pointer:usize)->usize
```

Reads dependent polling-root link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_waiter`

[primitives.crb:1101](../runtime/corbo/primitives.crb#L1101)

```rust
fn s_Task_waiter(pointer:usize, value:usize)
```

Writes dependent polling-root link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_waiter`

[primitives.crb:1109](../runtime/corbo/primitives.crb#L1109)

```rust
fn a_Task_waiter(pointer:usize)->usize
```

Returns the address of dependent polling-root link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_io_ready`

[primitives.crb:1118](../runtime/corbo/primitives.crb#L1118)

```rust
fn g_Task_io_ready(pointer:usize)->bool
```

Reads readiness-publication flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_io_ready`

[primitives.crb:1127](../runtime/corbo/primitives.crb#L1127)

```rust
fn s_Task_io_ready(pointer:usize, value:bool)
```

Writes readiness-publication flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_io_registered`

[primitives.crb:1135](../runtime/corbo/primitives.crb#L1135)

```rust
fn g_Task_io_registered(pointer:usize)->bool
```

Reads active-wait registration flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_io_registered`

[primitives.crb:1144](../runtime/corbo/primitives.crb#L1144)

```rust
fn s_Task_io_registered(pointer:usize, value:bool)
```

Writes active-wait registration flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_io_socket`

[primitives.crb:1152](../runtime/corbo/primitives.crb#L1152)

```rust
fn g_Task_io_socket(pointer:usize)->u64
```

Reads native socket identifier in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_io_socket`

[primitives.crb:1161](../runtime/corbo/primitives.crb#L1161)

```rust
fn s_Task_io_socket(pointer:usize, value:u64)
```

Writes native socket identifier in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_io_write`

[primitives.crb:1169](../runtime/corbo/primitives.crb#L1169)

```rust
fn g_Task_io_write(pointer:usize)->bool
```

Reads write-interest selector in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_io_write`

[primitives.crb:1178](../runtime/corbo/primitives.crb#L1178)

```rust
fn s_Task_io_write(pointer:usize, value:bool)
```

Writes write-interest selector in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_io_next`

[primitives.crb:1186](../runtime/corbo/primitives.crb#L1186)

```rust
fn g_Task_io_next(pointer:usize)->usize
```

Reads intrusive readiness-waiter link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_io_next`

[primitives.crb:1195](../runtime/corbo/primitives.crb#L1195)

```rust
fn s_Task_io_next(pointer:usize, value:usize)
```

Writes intrusive readiness-waiter link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_io_next`

[primitives.crb:1203](../runtime/corbo/primitives.crb#L1203)

```rust
fn a_Task_io_next(pointer:usize)->usize
```

Returns the address of intrusive readiness-waiter link in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_io_token`

[primitives.crb:1212](../runtime/corbo/primitives.crb#L1212)

```rust
fn g_Task_io_token(pointer:usize)->usize
```

Reads readiness-generation token in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_io_token`

[primitives.crb:1221](../runtime/corbo/primitives.crb#L1221)

```rust
fn s_Task_io_token(pointer:usize, value:usize)
```

Writes readiness-generation token in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_Task_io_token`

[primitives.crb:1229](../runtime/corbo/primitives.crb#L1229)

```rust
fn a_Task_io_token(pointer:usize)->usize
```

Returns the address of readiness-generation token in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_io_error`

[primitives.crb:1238](../runtime/corbo/primitives.crb#L1238)

```rust
fn g_Task_io_error(pointer:usize)->i64
```

Reads recorded platform I/O status in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_io_error`

[primitives.crb:1247](../runtime/corbo/primitives.crb#L1247)

```rust
fn s_Task_io_error(pointer:usize, value:i64)
```

Writes recorded platform I/O status in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_waiting`

[primitives.crb:1255](../runtime/corbo/primitives.crb#L1255)

```rust
fn g_Task_waiting(pointer:usize)->bool
```

Reads dependency-wait predicate in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_waiting`

[primitives.crb:1264](../runtime/corbo/primitives.crb#L1264)

```rust
fn s_Task_waiting(pointer:usize, value:bool)
```

Writes dependency-wait predicate in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_parked`

[primitives.crb:1272](../runtime/corbo/primitives.crb#L1272)

```rust
fn g_Task_parked(pointer:usize)->bool
```

Reads removed-from-ready-queue flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_parked`

[primitives.crb:1281](../runtime/corbo/primitives.crb#L1281)

```rust
fn s_Task_parked(pointer:usize, value:bool)
```

Writes removed-from-ready-queue flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_Task_blocking`

[primitives.crb:1289](../runtime/corbo/primitives.crb#L1289)

```rust
fn g_Task_blocking(pointer:usize)->bool
```

Reads dedicated blocking-worker flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_Task_blocking`

[primitives.crb:1298](../runtime/corbo/primitives.crb#L1298)

```rust
fn s_Task_blocking(pointer:usize, value:bool)
```

Writes dedicated blocking-worker flag in a live Task ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_Task`

[primitives.crb:1305](../runtime/corbo/primitives.crb#L1305)

```rust
fn size_Task()->usize
```

Returns the C ABI size in bytes of Task on this target.

### `align_Task`

[primitives.crb:1313](../runtime/corbo/primitives.crb#L1313)

```rust
fn align_Task()->usize
```

Returns the required C ABI alignment of Task on this target.

### `a_TaskState_task`

[primitives.crb:1322](../runtime/corbo/primitives.crb#L1322)

```rust
fn a_TaskState_task(pointer:usize)->usize
```

Returns the address of scheduler header at offset zero in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskState_value`

[primitives.crb:1331](../runtime/corbo/primitives.crb#L1331)

```rust
fn a_TaskState_value(pointer:usize)->usize
```

Returns the address of inline scalar result storage in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_TaskState_payload`

[primitives.crb:1340](../runtime/corbo/primitives.crb#L1340)

```rust
fn g_TaskState_payload(pointer:usize)->usize
```

Reads aggregate result address in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskState_payload`

[primitives.crb:1349](../runtime/corbo/primitives.crb#L1349)

```rust
fn s_TaskState_payload(pointer:usize, value:usize)
```

Writes aggregate result address in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskState_payload`

[primitives.crb:1357](../runtime/corbo/primitives.crb#L1357)

```rust
fn a_TaskState_payload(pointer:usize)->usize
```

Returns the address of aggregate result address in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_TaskState_region`

[primitives.crb:1366](../runtime/corbo/primitives.crb#L1366)

```rust
fn g_TaskState_region(pointer:usize)->usize
```

Reads frame-storage region link in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskState_region`

[primitives.crb:1375](../runtime/corbo/primitives.crb#L1375)

```rust
fn s_TaskState_region(pointer:usize, value:usize)
```

Writes frame-storage region link in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskState_region`

[primitives.crb:1383](../runtime/corbo/primitives.crb#L1383)

```rust
fn a_TaskState_region(pointer:usize)->usize
```

Returns the address of frame-storage region link in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_TaskState_own_region`

[primitives.crb:1392](../runtime/corbo/primitives.crb#L1392)

```rust
fn g_TaskState_own_region(pointer:usize)->bool
```

Reads separate region-descriptor ownership flag in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskState_own_region`

[primitives.crb:1401](../runtime/corbo/primitives.crb#L1401)

```rust
fn s_TaskState_own_region(pointer:usize, value:bool)
```

Writes separate region-descriptor ownership flag in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_TaskState_dispose`

[primitives.crb:1409](../runtime/corbo/primitives.crb#L1409)

```rust
fn g_TaskState_dispose(pointer:usize)->usize
```

Reads typed capture/result cleanup callback in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskState_dispose`

[primitives.crb:1418](../runtime/corbo/primitives.crb#L1418)

```rust
fn s_TaskState_dispose(pointer:usize, value:usize)
```

Writes typed capture/result cleanup callback in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskState_dispose`

[primitives.crb:1426](../runtime/corbo/primitives.crb#L1426)

```rust
fn a_TaskState_dispose(pointer:usize)->usize
```

Returns the address of typed capture/result cleanup callback in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskState_classic`

[primitives.crb:1435](../runtime/corbo/primitives.crb#L1435)

```rust
fn a_TaskState_classic(pointer:usize)->usize
```

Returns the address of suspended thread-local datastack context in a live TaskState ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_TaskState`

[primitives.crb:1443](../runtime/corbo/primitives.crb#L1443)

```rust
fn size_TaskState()->usize
```

Returns the C ABI size in bytes of TaskState on this target.

### `align_TaskState`

[primitives.crb:1451](../runtime/corbo/primitives.crb#L1451)

```rust
fn align_TaskState()->usize
```

Returns the required C ABI alignment of TaskState on this target.

### `g_TaskValue_state`

[primitives.crb:1460](../runtime/corbo/primitives.crb#L1460)

```rust
fn g_TaskValue_state(pointer:usize)->usize
```

Reads execution frame address in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskValue_state`

[primitives.crb:1469](../runtime/corbo/primitives.crb#L1469)

```rust
fn s_TaskValue_state(pointer:usize, value:usize)
```

Writes execution frame address in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskValue_state`

[primitives.crb:1477](../runtime/corbo/primitives.crb#L1477)

```rust
fn a_TaskValue_state(pointer:usize)->usize
```

Returns the address of execution frame address in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_TaskValue_storage`

[primitives.crb:1486](../runtime/corbo/primitives.crb#L1486)

```rust
fn g_TaskValue_storage(pointer:usize)->usize
```

Reads owned backing-region link in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskValue_storage`

[primitives.crb:1495](../runtime/corbo/primitives.crb#L1495)

```rust
fn s_TaskValue_storage(pointer:usize, value:usize)
```

Writes owned backing-region link in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskValue_storage`

[primitives.crb:1503](../runtime/corbo/primitives.crb#L1503)

```rust
fn a_TaskValue_storage(pointer:usize)->usize
```

Returns the address of owned backing-region link in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_TaskValue_poll`

[primitives.crb:1512](../runtime/corbo/primitives.crb#L1512)

```rust
fn g_TaskValue_poll(pointer:usize)->usize
```

Reads frame-specific poll callback in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskValue_poll`

[primitives.crb:1521](../runtime/corbo/primitives.crb#L1521)

```rust
fn s_TaskValue_poll(pointer:usize, value:usize)
```

Writes frame-specific poll callback in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskValue_poll`

[primitives.crb:1529](../runtime/corbo/primitives.crb#L1529)

```rust
fn a_TaskValue_poll(pointer:usize)->usize
```

Returns the address of frame-specific poll callback in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_TaskValue_native`

[primitives.crb:1538](../runtime/corbo/primitives.crb#L1538)

```rust
fn g_TaskValue_native(pointer:usize)->bool
```

Reads native-worker ownership selector in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskValue_native`

[primitives.crb:1547](../runtime/corbo/primitives.crb#L1547)

```rust
fn s_TaskValue_native(pointer:usize, value:bool)
```

Writes native-worker ownership selector in a live TaskValue ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_TaskValue`

[primitives.crb:1554](../runtime/corbo/primitives.crb#L1554)

```rust
fn size_TaskValue()->usize
```

Returns the C ABI size in bytes of TaskValue on this target.

### `align_TaskValue`

[primitives.crb:1562](../runtime/corbo/primitives.crb#L1562)

```rust
fn align_TaskValue()->usize
```

Returns the required C ABI alignment of TaskValue on this target.

### `g_TaskCompletion_ok`

[primitives.crb:1571](../runtime/corbo/primitives.crb#L1571)

```rust
fn g_TaskCompletion_ok(pointer:usize)->bool
```

Reads successful-launch/completion flag in a live TaskCompletion ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_TaskCompletion_ok`

[primitives.crb:1580](../runtime/corbo/primitives.crb#L1580)

```rust
fn s_TaskCompletion_ok(pointer:usize, value:bool)
```

Writes successful-launch/completion flag in a live TaskCompletion ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_TaskCompletion_value`

[primitives.crb:1588](../runtime/corbo/primitives.crb#L1588)

```rust
fn a_TaskCompletion_value(pointer:usize)->usize
```

Returns the address of moved scalar result bits in a live TaskCompletion ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_TaskCompletion`

[primitives.crb:1596](../runtime/corbo/primitives.crb#L1596)

```rust
fn size_TaskCompletion()->usize
```

Returns the C ABI size in bytes of TaskCompletion on this target.

### `align_TaskCompletion`

[primitives.crb:1604](../runtime/corbo/primitives.crb#L1604)

```rust
fn align_TaskCompletion()->usize
```

Returns the required C ABI alignment of TaskCompletion on this target.

### `g_ClassicStack_base`

[primitives.crb:1613](../runtime/corbo/primitives.crb#L1613)

```rust
fn g_ClassicStack_base(pointer:usize)->usize
```

Reads saved fixed-stack base in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_ClassicStack_base`

[primitives.crb:1622](../runtime/corbo/primitives.crb#L1622)

```rust
fn s_ClassicStack_base(pointer:usize, value:usize)
```

Writes saved fixed-stack base in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_ClassicStack_base`

[primitives.crb:1630](../runtime/corbo/primitives.crb#L1630)

```rust
fn a_ClassicStack_base(pointer:usize)->usize
```

Returns the address of saved fixed-stack base in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_ClassicStack_cursor`

[primitives.crb:1639](../runtime/corbo/primitives.crb#L1639)

```rust
fn g_ClassicStack_cursor(pointer:usize)->usize
```

Reads saved next free byte offset in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_ClassicStack_cursor`

[primitives.crb:1648](../runtime/corbo/primitives.crb#L1648)

```rust
fn s_ClassicStack_cursor(pointer:usize, value:usize)
```

Writes saved next free byte offset in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_ClassicStack_cursor`

[primitives.crb:1656](../runtime/corbo/primitives.crb#L1656)

```rust
fn a_ClassicStack_cursor(pointer:usize)->usize
```

Returns the address of saved next free byte offset in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_ClassicStack_limit`

[primitives.crb:1665](../runtime/corbo/primitives.crb#L1665)

```rust
fn g_ClassicStack_limit(pointer:usize)->usize
```

Reads saved fixed-stack capacity in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_ClassicStack_limit`

[primitives.crb:1674](../runtime/corbo/primitives.crb#L1674)

```rust
fn s_ClassicStack_limit(pointer:usize, value:usize)
```

Writes saved fixed-stack capacity in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_ClassicStack_limit`

[primitives.crb:1682](../runtime/corbo/primitives.crb#L1682)

```rust
fn a_ClassicStack_limit(pointer:usize)->usize
```

Returns the address of saved fixed-stack capacity in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_ClassicStack_committed`

[primitives.crb:1691](../runtime/corbo/primitives.crb#L1691)

```rust
fn g_ClassicStack_committed(pointer:usize)->usize
```

Reads saved committed-byte boundary in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_ClassicStack_committed`

[primitives.crb:1700](../runtime/corbo/primitives.crb#L1700)

```rust
fn s_ClassicStack_committed(pointer:usize, value:usize)
```

Writes saved committed-byte boundary in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_ClassicStack_committed`

[primitives.crb:1708](../runtime/corbo/primitives.crb#L1708)

```rust
fn a_ClassicStack_committed(pointer:usize)->usize
```

Returns the address of saved committed-byte boundary in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_ClassicStack_page_size`

[primitives.crb:1717](../runtime/corbo/primitives.crb#L1717)

```rust
fn g_ClassicStack_page_size(pointer:usize)->usize
```

Reads saved OS page size in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_ClassicStack_page_size`

[primitives.crb:1726](../runtime/corbo/primitives.crb#L1726)

```rust
fn s_ClassicStack_page_size(pointer:usize, value:usize)
```

Writes saved OS page size in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_ClassicStack_page_size`

[primitives.crb:1734](../runtime/corbo/primitives.crb#L1734)

```rust
fn a_ClassicStack_page_size(pointer:usize)->usize
```

Returns the address of saved OS page size in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_ClassicStack_mapped_size`

[primitives.crb:1743](../runtime/corbo/primitives.crb#L1743)

```rust
fn g_ClassicStack_mapped_size(pointer:usize)->usize
```

Reads saved mapping extent in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_ClassicStack_mapped_size`

[primitives.crb:1752](../runtime/corbo/primitives.crb#L1752)

```rust
fn s_ClassicStack_mapped_size(pointer:usize, value:usize)
```

Writes saved mapping extent in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_ClassicStack_mapped_size`

[primitives.crb:1760](../runtime/corbo/primitives.crb#L1760)

```rust
fn a_ClassicStack_mapped_size(pointer:usize)->usize
```

Returns the address of saved mapping extent in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_ClassicStack_band`

[primitives.crb:1769](../runtime/corbo/primitives.crb#L1769)

```rust
fn g_ClassicStack_band(pointer:usize)->usize
```

Reads saved region-scope link in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_ClassicStack_band`

[primitives.crb:1778](../runtime/corbo/primitives.crb#L1778)

```rust
fn s_ClassicStack_band(pointer:usize, value:usize)
```

Writes saved region-scope link in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_ClassicStack_band`

[primitives.crb:1786](../runtime/corbo/primitives.crb#L1786)

```rust
fn a_ClassicStack_band(pointer:usize)->usize
```

Returns the address of saved region-scope link in a live ClassicStack ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_ClassicStack`

[primitives.crb:1794](../runtime/corbo/primitives.crb#L1794)

```rust
fn size_ClassicStack()->usize
```

Returns the C ABI size in bytes of ClassicStack on this target.

### `align_ClassicStack`

[primitives.crb:1802](../runtime/corbo/primitives.crb#L1802)

```rust
fn align_ClassicStack()->usize
```

Returns the required C ABI alignment of ClassicStack on this target.

### `a_NativeBox_region`

[primitives.crb:1811](../runtime/corbo/primitives.crb#L1811)

```rust
fn a_NativeBox_region(pointer:usize)->usize
```

Returns the address of embedded frame region at offset zero in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_NativeBox_state`

[primitives.crb:1820](../runtime/corbo/primitives.crb#L1820)

```rust
fn g_NativeBox_state(pointer:usize)->usize
```

Reads native frame address in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_NativeBox_state`

[primitives.crb:1829](../runtime/corbo/primitives.crb#L1829)

```rust
fn s_NativeBox_state(pointer:usize, value:usize)
```

Writes native frame address in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_NativeBox_state`

[primitives.crb:1837](../runtime/corbo/primitives.crb#L1837)

```rust
fn a_NativeBox_state(pointer:usize)->usize
```

Returns the address of native frame address in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_NativeBox_run`

[primitives.crb:1846](../runtime/corbo/primitives.crb#L1846)

```rust
fn g_NativeBox_run(pointer:usize)->usize
```

Reads native frame run callback in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_NativeBox_run`

[primitives.crb:1855](../runtime/corbo/primitives.crb#L1855)

```rust
fn s_NativeBox_run(pointer:usize, value:usize)
```

Writes native frame run callback in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_NativeBox_run`

[primitives.crb:1863](../runtime/corbo/primitives.crb#L1863)

```rust
fn a_NativeBox_run(pointer:usize)->usize
```

Returns the address of native frame run callback in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_NativeBox_abandoned`

[primitives.crb:1872](../runtime/corbo/primitives.crb#L1872)

```rust
fn g_NativeBox_abandoned(pointer:usize)->bool
```

Reads worker-owned cleanup flag in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_NativeBox_abandoned`

[primitives.crb:1881](../runtime/corbo/primitives.crb#L1881)

```rust
fn s_NativeBox_abandoned(pointer:usize, value:bool)
```

Writes worker-owned cleanup flag in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_NativeBox_dispose`

[primitives.crb:1889](../runtime/corbo/primitives.crb#L1889)

```rust
fn g_NativeBox_dispose(pointer:usize)->usize
```

Reads capture/result cleanup callback in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_NativeBox_dispose`

[primitives.crb:1898](../runtime/corbo/primitives.crb#L1898)

```rust
fn s_NativeBox_dispose(pointer:usize, value:usize)
```

Writes capture/result cleanup callback in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_NativeBox_dispose`

[primitives.crb:1906](../runtime/corbo/primitives.crb#L1906)

```rust
fn a_NativeBox_dispose(pointer:usize)->usize
```

Returns the address of capture/result cleanup callback in a live NativeBox ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_NativeBox`

[primitives.crb:1914](../runtime/corbo/primitives.crb#L1914)

```rust
fn size_NativeBox()->usize
```

Returns the C ABI size in bytes of NativeBox on this target.

### `align_NativeBox`

[primitives.crb:1922](../runtime/corbo/primitives.crb#L1922)

```rust
fn align_NativeBox()->usize
```

Returns the required C ABI alignment of NativeBox on this target.

### `g_CorboStackMark_position`

[primitives.crb:1931](../runtime/corbo/primitives.crb#L1931)

```rust
fn g_CorboStackMark_position(pointer:usize)->usize
```

Reads saved fixed-stack byte cursor in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_CorboStackMark_position`

[primitives.crb:1940](../runtime/corbo/primitives.crb#L1940)

```rust
fn s_CorboStackMark_position(pointer:usize, value:usize)
```

Writes saved fixed-stack byte cursor in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_CorboStackMark_position`

[primitives.crb:1948](../runtime/corbo/primitives.crb#L1948)

```rust
fn a_CorboStackMark_position(pointer:usize)->usize
```

Returns the address of saved fixed-stack byte cursor in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_CorboStackMark_stack`

[primitives.crb:1957](../runtime/corbo/primitives.crb#L1957)

```rust
fn g_CorboStackMark_stack(pointer:usize)->usize
```

Reads originating stack identity in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_CorboStackMark_stack`

[primitives.crb:1966](../runtime/corbo/primitives.crb#L1966)

```rust
fn s_CorboStackMark_stack(pointer:usize, value:usize)
```

Writes originating stack identity in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_CorboStackMark_stack`

[primitives.crb:1974](../runtime/corbo/primitives.crb#L1974)

```rust
fn a_CorboStackMark_stack(pointer:usize)->usize
```

Returns the address of originating stack identity in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_CorboStackMark_region_scope`

[primitives.crb:1983](../runtime/corbo/primitives.crb#L1983)

```rust
fn g_CorboStackMark_region_scope(pointer:usize)->usize
```

Reads saved region-scope marker in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_CorboStackMark_region_scope`

[primitives.crb:1992](../runtime/corbo/primitives.crb#L1992)

```rust
fn s_CorboStackMark_region_scope(pointer:usize, value:usize)
```

Writes saved region-scope marker in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_CorboStackMark_region_scope`

[primitives.crb:2000](../runtime/corbo/primitives.crb#L2000)

```rust
fn a_CorboStackMark_region_scope(pointer:usize)->usize
```

Returns the address of saved region-scope marker in a live CorboStackMark ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_CorboStackMark`

[primitives.crb:2008](../runtime/corbo/primitives.crb#L2008)

```rust
fn size_CorboStackMark()->usize
```

Returns the C ABI size in bytes of CorboStackMark on this target.

### `align_CorboStackMark`

[primitives.crb:2016](../runtime/corbo/primitives.crb#L2016)

```rust
fn align_CorboStackMark()->usize
```

Returns the required C ABI alignment of CorboStackMark on this target.

### `g_CorboStackInfo_position`

[primitives.crb:2025](../runtime/corbo/primitives.crb#L2025)

```rust
fn g_CorboStackInfo_position(pointer:usize)->usize
```

Reads next free fixed-stack byte offset in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_CorboStackInfo_position`

[primitives.crb:2034](../runtime/corbo/primitives.crb#L2034)

```rust
fn s_CorboStackInfo_position(pointer:usize, value:usize)
```

Writes next free fixed-stack byte offset in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_CorboStackInfo_position`

[primitives.crb:2042](../runtime/corbo/primitives.crb#L2042)

```rust
fn a_CorboStackInfo_position(pointer:usize)->usize
```

Returns the address of next free fixed-stack byte offset in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_CorboStackInfo_committed`

[primitives.crb:2051](../runtime/corbo/primitives.crb#L2051)

```rust
fn g_CorboStackInfo_committed(pointer:usize)->usize
```

Reads committed fixed-stack bytes in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_CorboStackInfo_committed`

[primitives.crb:2060](../runtime/corbo/primitives.crb#L2060)

```rust
fn s_CorboStackInfo_committed(pointer:usize, value:usize)
```

Writes committed fixed-stack bytes in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_CorboStackInfo_committed`

[primitives.crb:2068](../runtime/corbo/primitives.crb#L2068)

```rust
fn a_CorboStackInfo_committed(pointer:usize)->usize
```

Returns the address of committed fixed-stack bytes in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `g_CorboStackInfo_capacity`

[primitives.crb:2077](../runtime/corbo/primitives.crb#L2077)

```rust
fn g_CorboStackInfo_capacity(pointer:usize)->usize
```

Reads reserved fixed-stack byte capacity in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `s_CorboStackInfo_capacity`

[primitives.crb:2086](../runtime/corbo/primitives.crb#L2086)

```rust
fn s_CorboStackInfo_capacity(pointer:usize, value:usize)
```

Writes reserved fixed-stack byte capacity in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `a_CorboStackInfo_capacity`

[primitives.crb:2094](../runtime/corbo/primitives.crb#L2094)

```rust
fn a_CorboStackInfo_capacity(pointer:usize)->usize
```

Returns the address of reserved fixed-stack byte capacity in a live CorboStackInfo ABI object.
Caller supplies valid aligned storage and any required lock; this binding performs no borrow checking.

### `size_CorboStackInfo`

[primitives.crb:2102](../runtime/corbo/primitives.crb#L2102)

```rust
fn size_CorboStackInfo()->usize
```

Returns the C ABI size in bytes of CorboStackInfo on this target.

### `align_CorboStackInfo`

[primitives.crb:2110](../runtime/corbo/primitives.crb#L2110)

```rust
fn align_CorboStackInfo()->usize
```

Returns the required C ABI alignment of CorboStackInfo on this target.

### `get_base`

[primitives.crb:2119](../runtime/corbo/primitives.crb#L2119)

```rust
fn get_base()->usize
```

Reads the current thread's fixed-stack base address.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_base`

[primitives.crb:2128](../runtime/corbo/primitives.crb#L2128)

```rust
fn set_base(value:usize)
```

Updates the current thread's fixed-stack base address.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_cursor`

[primitives.crb:2136](../runtime/corbo/primitives.crb#L2136)

```rust
fn get_cursor()->usize
```

Reads the current thread's next free fixed-stack byte offset.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_cursor`

[primitives.crb:2145](../runtime/corbo/primitives.crb#L2145)

```rust
fn set_cursor(value:usize)
```

Updates the current thread's next free fixed-stack byte offset.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_limit`

[primitives.crb:2153](../runtime/corbo/primitives.crb#L2153)

```rust
fn get_limit()->usize
```

Reads the current thread's fixed-stack byte capacity.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_limit`

[primitives.crb:2162](../runtime/corbo/primitives.crb#L2162)

```rust
fn set_limit(value:usize)
```

Updates the current thread's fixed-stack byte capacity.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_committed`

[primitives.crb:2170](../runtime/corbo/primitives.crb#L2170)

```rust
fn get_committed()->usize
```

Reads the current thread's committed fixed-stack byte boundary.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_committed`

[primitives.crb:2179](../runtime/corbo/primitives.crb#L2179)

```rust
fn set_committed(value:usize)
```

Updates the current thread's committed fixed-stack byte boundary.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_page_size`

[primitives.crb:2187](../runtime/corbo/primitives.crb#L2187)

```rust
fn get_page_size()->usize
```

Reads the current thread's OS page size.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_page_size`

[primitives.crb:2196](../runtime/corbo/primitives.crb#L2196)

```rust
fn set_page_size(value:usize)
```

Updates the current thread's OS page size.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_mapped_size`

[primitives.crb:2204](../runtime/corbo/primitives.crb#L2204)

```rust
fn get_mapped_size()->usize
```

Reads the current thread's reserved mapping extent.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_mapped_size`

[primitives.crb:2213](../runtime/corbo/primitives.crb#L2213)

```rust
fn set_mapped_size(value:usize)
```

Updates the current thread's reserved mapping extent.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_global_fixed_budget`

[primitives.crb:2221](../runtime/corbo/primitives.crb#L2221)

```rust
fn get_global_fixed_budget()->usize
```

Reads the configured per-thread fixed-stack byte budget.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_global_fixed_budget`

[primitives.crb:2230](../runtime/corbo/primitives.crb#L2230)

```rust
fn set_global_fixed_budget(value:usize)
```

Updates the configured per-thread fixed-stack byte budget.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_global_budget`

[primitives.crb:2238](../runtime/corbo/primitives.crb#L2238)

```rust
fn get_global_budget()->usize
```

Reads the configured region-stack byte budget.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_global_budget`

[primitives.crb:2247](../runtime/corbo/primitives.crb#L2247)

```rust
fn set_global_budget(value:usize)
```

Updates the configured region-stack byte budget.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_global_limit`

[primitives.crb:2255](../runtime/corbo/primitives.crb#L2255)

```rust
fn get_global_limit()->usize
```

Reads the configured default region byte limit.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_global_limit`

[primitives.crb:2264](../runtime/corbo/primitives.crb#L2264)

```rust
fn set_global_limit(value:usize)
```

Updates the configured default region byte limit.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_current_band`

[primitives.crb:2272](../runtime/corbo/primitives.crb#L2272)

```rust
fn get_current_band()->usize
```

Reads the current thread's region-scope band link.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_current_band`

[primitives.crb:2281](../runtime/corbo/primitives.crb#L2281)

```rust
fn set_current_band(value:usize)
```

Updates the current thread's region-scope band link.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_fixed_reclaim_threshold`

[primitives.crb:2289](../runtime/corbo/primitives.crb#L2289)

```rust
fn get_fixed_reclaim_threshold()->usize
```

Reads the fixed-stack page-reclamation byte threshold.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_fixed_reclaim_threshold`

[primitives.crb:2298](../runtime/corbo/primitives.crb#L2298)

```rust
fn set_fixed_reclaim_threshold(value:usize)
```

Updates the fixed-stack page-reclamation byte threshold.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_region_reclaim_threshold`

[primitives.crb:2306](../runtime/corbo/primitives.crb#L2306)

```rust
fn get_region_reclaim_threshold()->usize
```

Reads the region page-reclamation byte threshold.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_region_reclaim_threshold`

[primitives.crb:2315](../runtime/corbo/primitives.crb#L2315)

```rust
fn set_region_reclaim_threshold(value:usize)
```

Updates the region page-reclamation byte threshold.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_task_worker_count`

[primitives.crb:2323](../runtime/corbo/primitives.crb#L2323)

```rust
fn get_task_worker_count()->usize
```

Reads the number of started poll workers.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_task_worker_count`

[primitives.crb:2332](../runtime/corbo/primitives.crb#L2332)

```rust
fn set_task_worker_count(value:usize)
```

Updates the number of started poll workers.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_task_head`

[primitives.crb:2340](../runtime/corbo/primitives.crb#L2340)

```rust
fn get_task_head()->usize
```

Reads the ready-queue head task.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_task_head`

[primitives.crb:2349](../runtime/corbo/primitives.crb#L2349)

```rust
fn set_task_head(value:usize)
```

Updates the ready-queue head task.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_task_tail`

[primitives.crb:2357](../runtime/corbo/primitives.crb#L2357)

```rust
fn get_task_tail()->usize
```

Reads the ready-queue tail link address.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_task_tail`

[primitives.crb:2366](../runtime/corbo/primitives.crb#L2366)

```rust
fn set_task_tail(value:usize)
```

Updates the ready-queue tail link address.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_task_active`

[primitives.crb:2374](../runtime/corbo/primitives.crb#L2374)

```rust
fn get_task_active()->usize
```

Reads the number of unfinished scheduled tasks.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_task_active`

[primitives.crb:2383](../runtime/corbo/primitives.crb#L2383)

```rust
fn set_task_active(value:usize)
```

Updates the number of unfinished scheduled tasks.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_native_count`

[primitives.crb:2391](../runtime/corbo/primitives.crb#L2391)

```rust
fn get_native_count()->usize
```

Reads the number of unfinished native/blocking workers.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_native_count`

[primitives.crb:2400](../runtime/corbo/primitives.crb#L2400)

```rust
fn set_native_count(value:usize)
```

Updates the number of unfinished native/blocking workers.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_socket_waiters`

[primitives.crb:2408](../runtime/corbo/primitives.crb#L2408)

```rust
fn get_socket_waiters()->usize
```

Reads the intrusive socket-waiter head.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_socket_waiters`

[primitives.crb:2417](../runtime/corbo/primitives.crb#L2417)

```rust
fn set_socket_waiters(value:usize)
```

Updates the intrusive socket-waiter head.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_socket_serial`

[primitives.crb:2425](../runtime/corbo/primitives.crb#L2425)

```rust
fn get_socket_serial()->usize
```

Reads the current readiness-generation counter.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_socket_serial`

[primitives.crb:2434](../runtime/corbo/primitives.crb#L2434)

```rust
fn set_socket_serial(value:usize)
```

Updates the current readiness-generation counter.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_completion_port`

[primitives.crb:2442](../runtime/corbo/primitives.crb#L2442)

```rust
fn get_completion_port()->usize
```

Reads the native completion-port handle.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_completion_port`

[primitives.crb:2451](../runtime/corbo/primitives.crb#L2451)

```rust
fn set_completion_port(value:usize)
```

Updates the native completion-port handle.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_task_attempted`

[primitives.crb:2459](../runtime/corbo/primitives.crb#L2459)

```rust
fn get_task_attempted()->bool
```

Reads whether poll-worker initialization was attempted.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_task_attempted`

[primitives.crb:2468](../runtime/corbo/primitives.crb#L2468)

```rust
fn set_task_attempted(value:bool)
```

Updates whether poll-worker initialization was attempted.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_task_stopping`

[primitives.crb:2476](../runtime/corbo/primitives.crb#L2476)

```rust
fn get_task_stopping()->bool
```

Reads whether poll workers must stop after draining.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_task_stopping`

[primitives.crb:2485](../runtime/corbo/primitives.crb#L2485)

```rust
fn set_task_stopping(value:bool)
```

Updates whether poll workers must stop after draining.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_socket_queue`

[primitives.crb:2493](../runtime/corbo/primitives.crb#L2493)

```rust
fn get_socket_queue()->i64
```

Reads the native readiness-queue descriptor.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_socket_queue`

[primitives.crb:2502](../runtime/corbo/primitives.crb#L2502)

```rust
fn set_socket_queue(value:i64)
```

Updates the native readiness-queue descriptor.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_socket_init_error`

[primitives.crb:2510](../runtime/corbo/primitives.crb#L2510)

```rust
fn get_socket_init_error()->i64
```

Reads the recorded readiness initialization status.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_socket_init_error`

[primitives.crb:2519](../runtime/corbo/primitives.crb#L2519)

```rust
fn set_socket_init_error(value:i64)
```

Updates the recorded readiness initialization status.
Synchronize shared access; thread-local state belongs to the current execution context.

### `get_completion_init_error`

[primitives.crb:2527](../runtime/corbo/primitives.crb#L2527)

```rust
fn get_completion_init_error()->i64
```

Reads the recorded completion-port initialization status.
Synchronize shared access; thread-local state belongs to the current execution context.

### `set_completion_init_error`

[primitives.crb:2536](../runtime/corbo/primitives.crb#L2536)

```rust
fn set_completion_init_error(value:i64)
```

Updates the recorded completion-port initialization status.
Synchronize shared access; thread-local state belongs to the current execution context.

### `global_band_address`

[primitives.crb:2543](../runtime/corbo/primitives.crb#L2543)

```rust
fn global_band_address()->usize
```

Returns the stable address of the shared fallback region band, without creating a loan or extending a lifetime.

### `head_address`

[primitives.crb:2551](../runtime/corbo/primitives.crb#L2551)

```rust
fn head_address()->usize
```

Returns the scheduler queue-head link address for locked tail-link maintenance.

### `worker_address`

[primitives.crb:2559](../runtime/corbo/primitives.crb#L2559)

```rust
fn worker_address(index:usize)->usize
```

Returns the address of a poll-worker pthread_t slot; index must be inside the fixed worker array.

### `read_word`

[primitives.crb:2567](../runtime/corbo/primitives.crb#L2567)

```rust
fn read_word(pointer:usize)->usize
```

Loads one uintptr_t from a live, suitably aligned address; the caller must provide valid storage.

### `write_word`

[primitives.crb:2575](../runtime/corbo/primitives.crb#L2575)

```rust
fn write_word(pointer:usize, value:usize)
```

Stores one uintptr_t into live, aligned, writable storage; performs no ownership or synchronization checks.

### `read_byte`

[primitives.crb:2582](../runtime/corbo/primitives.crb#L2582)

```rust
fn read_byte(pointer:usize)->usize
```

Loads one byte from a live readable address without a Corbo bounds check.

### `write_byte`

[primitives.crb:2590](../runtime/corbo/primitives.crb#L2590)

```rust
fn write_byte(pointer:usize, value:usize)
```

Stores the low byte of value into a live writable address.

### `read_integer`

[primitives.crb:2597](../runtime/corbo/primitives.crb#L2597)

```rust
fn read_integer(pointer:usize)->usize
```

Loads one C int from live, aligned storage used by region-owner flags.

### `write_integer`

[primitives.crb:2605](../runtime/corbo/primitives.crb#L2605)

```rust
fn write_integer(pointer:usize, value:usize)
```

Stores one C int into live, aligned, writable flag storage.

### `memory_zero`

[primitives.crb:2612](../runtime/corbo/primitives.crb#L2612)

```rust
fn memory_zero(pointer:usize, bytes:usize)
```

Zeroes bytes of valid writable storage; the range must not contain resources needing destruction.

### `memory_copy`

[primitives.crb:2619](../runtime/corbo/primitives.crb#L2619)

```rust
fn memory_copy(destination:usize, source:usize, bytes:usize)
```

Copies bytes between valid nonoverlapping ranges; ownership effects are managed by the calling algorithm.

### `memory_move`

[primitives.crb:2626](../runtime/corbo/primitives.crb#L2626)

```rust
fn memory_move(destination:usize, source:usize, bytes:usize)
```

Moves bytes between valid ranges, allowing overlap; the caller updates element ownership and length.

### `max_size`

[primitives.crb:2633](../runtime/corbo/primitives.crb#L2633)

```rust
fn max_size()->usize
```

Returns the largest target uintptr_t value used for checked size arithmetic.

### `max_difference`

[primitives.crb:2641](../runtime/corbo/primitives.crb#L2641)

```rust
fn max_difference()->usize
```

Returns PTRDIFF_MAX, the largest supported positive object-address difference.

### `max_alignment`

[primitives.crb:2649](../runtime/corbo/primitives.crb#L2649)

```rust
fn max_alignment()->usize
```

Returns alignof(max_align_t) for fixed slots and map entry layout.

### `wrapping_multiply`

[primitives.crb:2657](../runtime/corbo/primitives.crb#L2657)

```rust
fn wrapping_multiply(left:u64, right:u64)->u64
```

Multiplies machine words with unsigned wrapping for the map hash mixer.

### `os_page_size`

[primitives.crb:2665](../runtime/corbo/primitives.crb#L2665)

```rust
fn os_page_size()->usize
```

Queries the target OS virtual-memory page size.

### `os_available_pages`

[primitives.crb:2677](../runtime/corbo/primitives.crb#L2677)

```rust
fn os_available_pages()->i64
```

Queries available physical-memory pages on Unix; nonpositive results require the documented fallback.

### `os_physical_pages`

[primitives.crb:2691](../runtime/corbo/primitives.crb#L2691)

```rust
fn os_physical_pages()->i64
```

Queries total physical-memory pages as a Unix sizing fallback.

### `os_cpus`

[primitives.crb:2703](../runtime/corbo/primitives.crb#L2703)

```rust
fn os_cpus()->usize
```

Queries the OS processor count used to divide default memory budgets.

### `os_reserve`

[primitives.crb:2715](../runtime/corbo/primitives.crb#L2715)

```rust
fn os_reserve(bytes:usize)->usize
```

Reserves a virtual address range without committing its full payload; returns zero on platform failure.

### `os_metadata`

[primitives.crb:2727](../runtime/corbo/primitives.crb#L2727)

```rust
fn os_metadata(bytes:usize)->usize
```

Maps writable zero-initialized metadata pages and returns zero on failure.

### `os_commit`

[primitives.crb:2739](../runtime/corbo/primitives.crb#L2739)

```rust
fn os_commit(pointer:usize, bytes:usize)->bool
```

Makes the supplied page range readable/writable through the target OS; reports success.

### `os_unmap`

[primitives.crb:2751](../runtime/corbo/primitives.crb#L2751)

```rust
fn os_unmap(pointer:usize, bytes:usize)
```

Releases an OS mapping using its original address and byte extent.

### `os_decommit`

[primitives.crb:2762](../runtime/corbo/primitives.crb#L2762)

```rust
fn os_decommit(pointer:usize, bytes:usize)->bool
```

Returns physical backing for complete unused pages while preserving the reserved address range; reports success.

### `fault`

[primitives.crb:2774](../runtime/corbo/primitives.crb#L2774)

```rust
fn fault(code:usize)
```

Terminates with the selected reference-runtime diagnostic for invalid storage, slots or bounds.

### `os_abort`

[primitives.crb:2781](../runtime/corbo/primitives.crb#L2781)

```rust
fn os_abort()
```

Terminates immediately for an impossible worker/pthread contract violation.

### `atomic_claim`

[primitives.crb:2788](../runtime/corbo/primitives.crb#L2788)

```rust
fn atomic_claim(pointer:usize)->bool
```

Atomically changes an unoccupied pool-slot byte to occupied and reports whether this caller claimed it.

### `atomic_clear`

[primitives.crb:2796](../runtime/corbo/primitives.crb#L2796)

```rust
fn atomic_clear(pointer:usize)
```

Publishes a pool slot as free after its destructor has completed.

### `atomic_init_slot`

[primitives.crb:2803](../runtime/corbo/primitives.crb#L2803)

```rust
fn atomic_init_slot(pointer:usize)
```

Initializes an occupancy byte before any thread may access the pool.

### `call_drop`

[primitives.crb:2810](../runtime/corbo/primitives.crb#L2810)

```rust
fn call_drop(callback:usize, pointer:usize)
```

Calls a void(void*) payload destructor; function and payload addresses must satisfy that exact ABI.

### `call_dispose`

[primitives.crb:2817](../runtime/corbo/primitives.crb#L2817)

```rust
fn call_dispose(callback:usize, pointer:usize, completed:bool)
```

Calls a task-state cleanup callback with the completion flag controlling capture/result cleanup.

### `call_poll`

[primitives.crb:2824](../runtime/corbo/primitives.crb#L2824)

```rust
fn call_poll(callback:usize, pointer:usize, failed:bool)->bool
```

Calls a bool(Task*,bool) poll/clear callback and returns its completion result.

### `lock`

[primitives.crb:2832](../runtime/corbo/primitives.crb#L2832)

```rust
fn lock()
```

Acquires the shared runtime/scheduler mutex; callers must not already hold this nonrecursive lock.

### `unlock`

[primitives.crb:2841](../runtime/corbo/primitives.crb#L2841)

```rust
fn unlock()
```

Releases the shared mutex held by this thread.

### `condition_wait`

[primitives.crb:2850](../runtime/corbo/primitives.crb#L2850)

```rust
fn condition_wait()
```

Atomically releases the held runtime mutex while waiting, then reacquires it; callers recheck their predicate.

### `broadcast`

[primitives.crb:2859](../runtime/corbo/primitives.crb#L2859)

```rust
fn broadcast()
```

Wakes condition waiters so they can recheck state protected by the runtime mutex.

### `thread_create`

[primitives.crb:2868](../runtime/corbo/primitives.crb#L2868)

```rust
fn thread_create(slot:usize, entry:usize, argument:usize)->i32
```

Starts a joinable platform thread using a correctly typed entry callback and caller-provided identifier storage.

### `thread_detached`

[primitives.crb:2876](../runtime/corbo/primitives.crb#L2876)

```rust
fn thread_detached(entry:usize, argument:usize)->i32
```

Starts a detached platform worker with native thread attributes and returns the pthread status.

### `thread_join`

[primitives.crb:2884](../runtime/corbo/primitives.crb#L2884)

```rust
fn thread_join(slot:usize)->i32
```

Joins a platform worker by identifier; failure violates the runtime shutdown contract.

### `thread_detach`

[primitives.crb:2892](../runtime/corbo/primitives.crb#L2892)

```rust
fn thread_detach(slot:usize)
```

Detaches a platform thread identifier when its lifetime is managed independently.

### `unsigned_bits`

[primitives.crb:2906](../runtime/corbo/primitives.crb#L2906)

```rust
fn unsigned_bits(value:i64)->usize
```

Reinterprets a signed integer as unsigned bits, including negative values.

### `signed_bits`

[primitives.crb:2908](../runtime/corbo/primitives.crb#L2908)

```rust
fn signed_bits(value:usize)->i64
```

Reinterprets an unsigned word as signed bits without an exact-conversion requirement.

### `size_TaskResult`

[primitives.crb:2910](../runtime/corbo/primitives.crb#L2910)

```rust
fn size_TaskResult()->usize
```

Returns the C ABI size in bytes of TaskResult on this target.

### `socket_waiters_address`

[primitives.crb:2912](../runtime/corbo/primitives.crb#L2912)

```rust
fn socket_waiters_address()->usize
```

Returns the stable address of the waiter-list head for locked intrusive-list updates.

### `temporary_thread_slot`

[primitives.crb:2914](../runtime/corbo/primitives.crb#L2914)

```rust
fn temporary_thread_slot()->usize
```

Returns thread-local scratch storage for a detached thread identifier.

### `call_task_drop`

[primitives.crb:2916](../runtime/corbo/primitives.crb#L2916)

```rust
fn call_task_drop(callback:usize,pointer:usize)
```

Calls a void(Task*) task destructor through its exact function-pointer type.

### `os_windows`

[primitives.crb:2918](../runtime/corbo/primitives.crb#L2918)

```rust
fn os_windows()->bool
```

Reports whether the selected C target is Windows for platform-specific capacity policy.

### `os_available_bytes`

[primitives.crb:2924](../runtime/corbo/primitives.crb#L2924)

```rust
fn os_available_bytes()->usize
```

Queries available Windows physical bytes; returns UINTPTR_MAX if the OS query fails.

### `set_cursor_untracked`

[primitives.crb:2931](../runtime/corbo/primitives.crb#L2931)

```rust
fn set_cursor_untracked(value:usize)
```

Assigns a restored execution cursor without counting the context as a new allocation.

### `metric_add`

[primitives.crb:2933](../runtime/corbo/primitives.crb#L2933)

```rust
fn metric_add(counter:usize,bytes:usize)
```

Adds a successful byte transition to one global atomic metric.

### `metric_sub`

[primitives.crb:2935](../runtime/corbo/primitives.crb#L2935)

```rust
fn metric_sub(counter:usize,bytes:usize)
```

Subtracts a completed byte transition from one global atomic metric.

### `metric_read`

[primitives.crb:2937](../runtime/corbo/primitives.crb#L2937)

```rust
fn metric_read(counter:usize)->usize
```

Reads one metric without reading another thread's mutable storage.

### `metric_pool`

[primitives.crb:2943](../runtime/corbo/primitives.crb#L2943)

```rust
fn metric_pool()->usize
```

Returns the current execution context's newest pool descriptor.

### `metric_pool_register`

[primitives.crb:2949](../runtime/corbo/primitives.crb#L2949)

```rust
fn metric_pool_register(pool:usize)
```

Registers a completed pool, its cursor end and live-slot counter.

### `metric_pool_pop`

[primitives.crb:2956](../runtime/corbo/primitives.crb#L2956)

```rust
fn metric_pool_pop(next:usize)->usize
```

Removes the newest pool and returns its unused payload byte count before cursor rewind.

### `metric_pool_after`

[primitives.crb:2968](../runtime/corbo/primitives.crb#L2968)

```rust
fn metric_pool_after(next:usize)->bool
```

Returns whether the newest pool extends beyond the next fixed-stack cursor.

### `metric_pool_live`

[primitives.crb:2974](../runtime/corbo/primitives.crb#L2974)

```rust
fn metric_pool_live(pool:usize,claim:bool)
```

Records a claimed or released slot; the occupancy bitmap remains authoritative for allocation.

### `metric_context_save`

[primitives.crb:2981](../runtime/corbo/primitives.crb#L2981)

```rust
fn metric_context_save(out:usize)
```

Saves the metric pool chain with its suspended fixed-stack context.

### `metric_context_restore`

[primitives.crb:2983](../runtime/corbo/primitives.crb#L2983)

```rust
fn metric_context_restore(next:usize)
```

Restores an existing chain without counting its storage twice.

### `metric_snapshot`

[primitives.crb:2985](../runtime/corbo/primitives.crb#L2985)

```rust
fn metric_snapshot(out:usize,reserved:usize,committed:usize,occupied:usize)
```

Writes the public C snapshot layout; the caller supplies valid result storage.


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

[reclaim.crb:21](../runtime/corbo/reclaim.crb#L21)

```rust
fn reclaim_band(band:usize,force:bool)
```

Computes the last live byte across active regions before considering complete tail pages for reclamation.

### `reclaim_scope`

[reclaim.crb:34](../runtime/corbo/reclaim.crb#L34)

```rust
fn reclaim_scope(force:bool)
```

Reclaims unused fixed/region tail pages using the configured thresholds or force, without releasing live storage.

### `release_pages`

[reclaim.crb:60](../runtime/corbo/reclaim.crb#L60)

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

[values.crb:23](../runtime/corbo/values.crb#L23)

```rust
fn make_task_in(out:usize,region:usize,size:usize,poll:usize,dedicated:bool)
```

Places inactive task state in a region and fills out with its state, storage and typed poll callback; caller holds the lock.

### `task_metadata`

[values.crb:34](../runtime/corbo/values.crb#L34)

```rust
fn task_metadata(bytes:usize)->usize
```

Maps separate runtime metadata of the requested byte size; terminates if the OS cannot provide it.

### `task_unmap`

[values.crb:42](../runtime/corbo/values.crb#L42)

```rust
fn task_unmap(pointer:usize,bytes:usize)
```

Unmaps a metadata address with the original mapping byte count after its users finish.

### `make_task`

[values.crb:46](../runtime/corbo/values.crb#L46)

```rust
fn make_task(out:usize,size:usize,poll:usize)
```

Creates inactive future storage under the runtime lock and records ownership of its separate region descriptor.

### `release_future`

[values.crb:54](../runtime/corbo/values.crb#L54)

```rust
fn release_future(state:usize,completed:bool,taken:bool)
```

Cleans an untaken result or inactive captures, releases frame storage, and unmaps separately owned metadata.

### `task_abandoned`

[values.crb:71](../runtime/corbo/values.crb#L71)

```rust
fn task_abandoned(task:usize)
```

Releases a completed abandoned task, including its untaken result.

### `start_task`

[values.crb:75](../runtime/corbo/values.crb#L75)

```rust
fn start_task(value:usize)
```

Schedules a TaskValue using its poll function and the abandoned-task cleanup callback.

### `discard_handle`

[values.crb:79](../runtime/corbo/values.crb#L79)

```rust
fn discard_handle(value:usize)
```

Marks an active execution abandoned or releases a completed one; native executions use their separate ownership path.

### `join_task`

[values.crb:99](../runtime/corbo/values.crb#L99)

```rust
fn join_task(out:usize,value:usize)
```

Waits for completion, writes a scalar completion descriptor to out and releases the consumed handle's storage.

### `join_task_into`

[values.crb:111](../runtime/corbo/values.crb#L111)

```rust
fn join_task_into(value:usize,out:usize,bytes:usize)->bool
```

Waits for completion and moves a successful aggregate payload into caller storage; returns false on launch failure.

### `discard_future`

[values.crb:126](../runtime/corbo/values.crb#L126)

```rust
fn discard_future(value:usize)
```

Destroys captures and storage of a nonempty inactive future descriptor.


## C ABI and comparison sources

These declarations describe the C boundary/reference, not new checked-language APIs.

### `runtime/async/channel.c.inc`

- [`CorboChannelState`](../runtime/async/channel.c.inc#L5): Stable queue descriptor; all mutable fields require task_lock.

- [`storage`](../runtime/async/channel.c.inc#L7): Dedicated managed payload storage.

- [`capacity,width,count,head`](../runtime/async/channel.c.inc#L9): Fixed capacity, descriptor width, queued count and oldest ring index.

- [`epoch`](../runtime/async/channel.c.inc#L11): Readiness change sequence, protected by task_lock.

- [`closed`](../runtime/async/channel.c.inc#L13): Prevents sends while permitting queued values to drain.

- [`heads,tails`](../runtime/async/channel.c.inc#L15): Receive/send FIFO registration queues.

- [`channel_wake_one`](../runtime/async/channel.c.inc#L18): Select one registered task; task_lock is held and polling never occurs inline.

- [`channel_unlink`](../runtime/async/channel.c.inc#L28): Remove a persistent wait record before freeing its frame, forwarding a notification.

- [`channel_create`](../runtime/async/channel.c.inc#L41): Reserve a finite byte ring in a detached managed region.

- [`channel_send`](../runtime/async/channel.c.inc#L57): Move one complete typed descriptor into the ring, or leave it untouched on failure.

- [`channel_receive`](../runtime/async/channel.c.inc#L69): Move the oldest descriptor out; closed channels drain before signaling exhaustion.

- [`channel_close`](../runtime/async/channel.c.inc#L81): Close once and wake both waiting senders and receivers.

- [`channel_poll`](../runtime/async/channel.c.inc#L90): Check the epoch and register under the same lock, closing the lost-wakeup window.

- [`channel_detach`](../runtime/async/channel.c.inc#L100): Unregister before frame reclamation.

- [`channel_destroy`](../runtime/async/channel.c.inc#L102): Release drained storage only after all borrowed users have ended.

### `runtime/async/completion.c.inc`

- [`completion_events`](../runtime/async/completion.c.inc#L10): Receives per-operation completion records and resumes their task roots under the scheduler lock.

- [`completion_initialize`](../runtime/async/completion.c.inc#L36): Creates the completion port and its event thread once, recording initialization errors.

- [`corbo_socket_attach`](../runtime/async/completion.c.inc#L52): Associates a socket with the runtime completion port and returns the platform status.

- [`corbo_socket_complete`](../runtime/async/completion.c.inc#L59): Submits or observes one operation-specific completion request and coordinates its task wakeup without sharing request state.

### `runtime/async/mutex.c.inc`

- [`CorboMutexState`](../runtime/async/mutex.c.inc#L6): Native mutex storage; its address remains stable until the owner is destroyed.

- [`gate`](../runtime/async/mutex.c.inc#L8): gate: native mutex, held through synchronous guard ownership only.

- [`owner`](../runtime/async/mutex.c.inc#L10): owner: thread which acquired the synchronous guard.

- [`asynchronous`](../runtime/async/mutex.c.inc#L12): asynchronous: chooses logical task ownership instead of native guard ownership.

- [`held`](../runtime/async/mutex.c.inc#L14): held: logical async lock state, protected by task_lock.

- [`head,tail`](../runtime/async/mutex.c.inc#L16): head: first queued waiter. tail: FIFO insertion point.

- [`reservation`](../runtime/async/mutex.c.inc#L18): reservation: waiter receiving a release-to-next handoff.

- [`mutex_create`](../runtime/async/mutex.c.inc#L21): Creates stable OS-backed mutex metadata; no native lock is moved.

- [`mutex_acquire`](../runtime/async/mutex.c.inc#L32): Acquires a blocking native-thread-bound guard.

- [`mutex_handoff`](../runtime/async/mutex.c.inc#L34): Reserves the FIFO successor; caller holds task_lock.

- [`mutex_poll`](../runtime/async/mutex.c.inc#L40): Acquires or parks one persistent task wait record.

- [`mutex_release`](../runtime/async/mutex.c.inc#L48): Releases native-thread ownership or hands logical ownership to a waiter.

- [`mutex_detach`](../runtime/async/mutex.c.inc#L53): Removes a pending wait before its frame storage is reclaimed.

- [`mutex_destroy`](../runtime/async/mutex.c.inc#L59): Destroys unlocked metadata only after its guards and waiters have ended.

### `runtime/async/readiness.c.inc`

- [`socket_interest`](../runtime/async/readiness.c.inc#L12): Combines active reader/writer interests for one socket generation; caller holds the scheduler lock.

- [`socket_signal`](../runtime/async/readiness.c.inc#L21): Publishes a socket readiness/error to one waiter and resumes its parked root; caller holds the scheduler lock.

- [`socket_dispatch`](../runtime/async/readiness.c.inc#L45): Detaches matching waiters, publishes readiness and rearms remaining interests; ignores stale generation tokens.

- [`socket_events`](../runtime/async/readiness.c.inc#L65): Waits on the platform readiness queue and dispatches returned events under the scheduler lock.

- [`socket_initialize`](../runtime/async/readiness.c.inc#L73): Creates the readiness queue and its detached event thread once; records initialization failure for future waits.

- [`corbo_socket_wait`](../runtime/async/readiness.c.inc#L89): Registers one task wait for socket readability or writability without losing an intervening wake; returns readiness or a platform error.

### `runtime/async/scheduler.c.inc`

- [`task_publish`](../runtime/async/scheduler.c.inc#L6): Publishes completion and wakes or enqueues a waiting root exactly through the locked scheduler transition.

- [`task_await`](../runtime/async/scheduler.c.inc#L20): Registers the current root as child's waiter if unfinished; returns whether completion was already visible under the lock.

- [`task_poll_worker`](../runtime/async/scheduler.c.inc#L33): Consumes queued tasks, polls outside the lock, then publishes, parks or requeues them; releases its thread-local stack on exit.

- [`task_spawn_with`](../runtime/async/scheduler.c.inc#L63): Initializes a task and starts poll workers once; enqueues it or records launch failure and clears captures if no worker starts.

- [`task_spawn`](../runtime/async/scheduler.c.inc#L85): Schedules a task without an abandonment callback; its caller must preserve the frame through completion.

- [`task_join`](../runtime/async/scheduler.c.inc#L89): Blocks the current thread on the scheduler condition until the task is done.

- [`task_end`](../runtime/async/scheduler.c.inc#L95): Drains active scheduled tasks, signals shutdown and joins every poll worker.

### `runtime/async/task_header.c.inc`

- [`Task`](../runtime/async/task_header.c.inc#L8): Intrusive execution header shared by generated frames and the scheduler. Queue, completion and waiter transitions require task_lock.

- [`Task`](../runtime/async/task_header.c.inc#L10): Intrusive execution header shared by generated frames and the scheduler. Queue, completion and waiter transitions require task_lock.

- [`pc`](../runtime/async/task_header.c.inc#L12): pc: resume-state program counter.

- [`poll`](../runtime/async/task_header.c.inc#L14): poll: typed poll/clear callback.

- [`next`](../runtime/async/task_header.c.inc#L16): next: ready-queue next link.

- [`failed`](../runtime/async/task_header.c.inc#L18): failed: launch-failure flag.

- [`done`](../runtime/async/task_header.c.inc#L20): done: completion-publication flag.

- [`abandoned`](../runtime/async/task_header.c.inc#L22): abandoned: worker-owned final-cleanup flag.

- [`discard`](../runtime/async/task_header.c.inc#L24): discard: typed abandoned-task cleanup callback.

- [`root,waiter`](../runtime/async/task_header.c.inc#L26): root: outer polling-root link. waiter: dependent polling-root link.

- [`io_ready,io_registered`](../runtime/async/task_header.c.inc#L28): io_ready: readiness-publication flag. io_registered: active-wait registration flag.

- [`io_socket`](../runtime/async/task_header.c.inc#L30): io_socket: native socket identifier.

- [`io_write`](../runtime/async/task_header.c.inc#L32): io_write: write-interest selector.

- [`io_next`](../runtime/async/task_header.c.inc#L34): io_next: intrusive readiness-waiter link.

- [`io_token`](../runtime/async/task_header.c.inc#L36): io_token: readiness-generation token.

- [`io_error`](../runtime/async/task_header.c.inc#L38): io_error: recorded platform I/O status.

- [`waiting,parked,blocking`](../runtime/async/task_header.c.inc#L40): waiting: dependency-wait predicate. parked: removed-from-ready-queue flag. blocking: dedicated blocking-worker flag.

- [`mutex_next`](../runtime/async/task_header.c.inc#L42): mutex_next: next waiter in a mutex FIFO, protected by task_lock.

- [`mutex_owner`](../runtime/async/task_header.c.inc#L44): mutex_owner: logical async mutex currently retaining this waiter.

- [`mutex_reserved`](../runtime/async/task_header.c.inc#L46): mutex_reserved: release handed this waiter the next acquisition.

- [`channel_wait`](../runtime/async/task_header.c.inc#L48): Distinguishes channel registration from the reused mutex wait fields.

- [`task_enqueue`](../runtime/async/task_header.c.inc#L60): Links a task at the queue tail; caller holds the scheduler lock and the task is not already queued.

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

- [`metric_pools`](../runtime/async/values.c.inc#L34): metric_pools: suspended fixed-stack pool accounting chain.

- [`swap_classic`](../runtime/async/values.c.inc#L37): Installs next as the thread-local fixed-stack/region context and returns the previous context for later restoration.

- [`TaskState`](../runtime/async/values.c.inc#L42): Task header at offset zero plus result, frame-region ownership, cleanup callback and saved storage context.

- [`task`](../runtime/async/values.c.inc#L44): task: scheduler header at offset zero.

- [`value`](../runtime/async/values.c.inc#L46): value: inline scalar result storage.

- [`payload`](../runtime/async/values.c.inc#L48): payload: aggregate result address.

- [`region`](../runtime/async/values.c.inc#L50): region: frame-storage region link.

- [`own_region`](../runtime/async/values.c.inc#L52): own_region: separate region-descriptor ownership flag.

- [`dispose`](../runtime/async/values.c.inc#L54): dispose: typed capture/result cleanup callback.

- [`classic`](../runtime/async/values.c.inc#L56): classic: suspended thread-local datastack context.

- [`TaskValue`](../runtime/async/values.c.inc#L59): Future/handle descriptor linking an execution frame, backing region, typed poll callback and native-worker mode.

- [`state`](../runtime/async/values.c.inc#L61): state: execution frame address.

- [`storage`](../runtime/async/values.c.inc#L63): storage: owned backing-region link.

- [`poll`](../runtime/async/values.c.inc#L65): poll: frame-specific poll callback.

- [`native`](../runtime/async/values.c.inc#L67): native: native-worker ownership selector.

- [`TaskCompletion`](../runtime/async/values.c.inc#L70): Success flag and inline scalar result moved out by join_task.

- [`ok`](../runtime/async/values.c.inc#L72): ok: successful-launch/completion flag.

- [`value`](../runtime/async/values.c.inc#L74): value: moved scalar result bits.

- [`make_task_in`](../runtime/async/values.c.inc#L77): Returns an inactive task descriptor backed by the supplied stable region; caller holds the runtime lock.

- [`release_native`](../runtime/async/values.c.inc#L81): Releases a completed native execution, destroying its result only when it was not transferred to the caller.

- [`abandon_native`](../runtime/async/values.c.inc#L83): Transfers final cleanup of a running native frame to its worker; completed frames are released immediately.

- [`task_metadata`](../runtime/async/values.c.inc#L85): Maps separate runtime metadata of the requested byte size; terminates if the OS cannot provide it.

- [`task_unmap`](../runtime/async/values.c.inc#L93): Unmaps a metadata address with the original mapping byte count after its users finish.

- [`make_task`](../runtime/async/values.c.inc#L101): Returns an inactive task descriptor backed by a region and separately owned metadata.

- [`release_future`](../runtime/async/values.c.inc#L106): Cleans an untaken result or inactive captures, releases frame storage, and unmaps separately owned metadata.

- [`task_abandoned`](../runtime/async/values.c.inc#L112): Releases a completed abandoned task, including its untaken result.

- [`start_task`](../runtime/async/values.c.inc#L114): Schedules a TaskValue using its poll function and the abandoned-task cleanup callback.

- [`discard_handle`](../runtime/async/values.c.inc#L116): Marks an active execution abandoned or releases a completed one; native executions use their separate ownership path.

- [`join_task`](../runtime/async/values.c.inc#L121): Waits for completion, returns a scalar completion descriptor and releases consumed handle storage.

- [`join_task_into`](../runtime/async/values.c.inc#L124): Waits for completion and moves a successful aggregate payload into caller storage; returns false on launch failure.

- [`discard_future`](../runtime/async/values.c.inc#L128): Destroys captures and storage of a nonempty inactive future descriptor.

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

- [`Task`](../runtime/corbo/corbo_runtime_abi.h#L31): Intrusive execution header shared by generated frames and the scheduler. Queue, completion and waiter transitions require task_lock.

- [`Task`](../runtime/corbo/corbo_runtime_abi.h#L33): Intrusive execution header shared by generated frames and the scheduler. Queue, completion and waiter transitions require task_lock.

- [`pc`](../runtime/corbo/corbo_runtime_abi.h#L35): pc: resume-state program counter.

- [`poll`](../runtime/corbo/corbo_runtime_abi.h#L37): poll: typed poll/clear callback.

- [`next`](../runtime/corbo/corbo_runtime_abi.h#L39): next: ready-queue next link.

- [`failed`](../runtime/corbo/corbo_runtime_abi.h#L41): failed: launch-failure flag.

- [`done`](../runtime/corbo/corbo_runtime_abi.h#L43): done: completion-publication flag.

- [`abandoned`](../runtime/corbo/corbo_runtime_abi.h#L45): abandoned: worker-owned final-cleanup flag.

- [`discard`](../runtime/corbo/corbo_runtime_abi.h#L47): discard: typed abandoned-task cleanup callback.

- [`root,waiter`](../runtime/corbo/corbo_runtime_abi.h#L49): root: outer polling-root link. waiter: dependent polling-root link.

- [`io_ready,io_registered`](../runtime/corbo/corbo_runtime_abi.h#L51): io_ready: readiness-publication flag. io_registered: active-wait registration flag.

- [`io_socket`](../runtime/corbo/corbo_runtime_abi.h#L53): io_socket: native socket identifier.

- [`io_write`](../runtime/corbo/corbo_runtime_abi.h#L55): io_write: write-interest selector.

- [`io_next`](../runtime/corbo/corbo_runtime_abi.h#L57): io_next: intrusive readiness-waiter link.

- [`io_token`](../runtime/corbo/corbo_runtime_abi.h#L59): io_token: readiness-generation token.

- [`io_error`](../runtime/corbo/corbo_runtime_abi.h#L61): io_error: recorded platform I/O status.

- [`waiting,parked,blocking`](../runtime/corbo/corbo_runtime_abi.h#L63): waiting: dependency-wait predicate. parked: removed-from-ready-queue flag. blocking: dedicated blocking-worker flag.

- [`mutex_next`](../runtime/corbo/corbo_runtime_abi.h#L65): mutex_next: next waiter in a mutex FIFO, protected by task_lock.

- [`mutex_owner`](../runtime/corbo/corbo_runtime_abi.h#L67): mutex_owner: logical async mutex currently retaining this waiter.

- [`mutex_reserved`](../runtime/corbo/corbo_runtime_abi.h#L69): mutex_reserved: release handed this waiter the next acquisition.

- [`channel_wait`](../runtime/corbo/corbo_runtime_abi.h#L72): Distinguishes channel registration from the reused mutex wait fields.

- [`CorboMutexState`](../runtime/corbo/corbo_runtime_abi.h#L75): Native mutex storage; its address remains stable until the owner is destroyed.

- [`gate`](../runtime/corbo/corbo_runtime_abi.h#L77): gate: native mutex, held through synchronous guard ownership only.

- [`owner`](../runtime/corbo/corbo_runtime_abi.h#L79): owner: thread which acquired the synchronous guard.

- [`asynchronous`](../runtime/corbo/corbo_runtime_abi.h#L81): asynchronous: chooses logical task ownership instead of native guard ownership.

- [`held`](../runtime/corbo/corbo_runtime_abi.h#L83): held: logical async lock state, protected by task_lock.

- [`head,tail`](../runtime/corbo/corbo_runtime_abi.h#L85): head: first queued waiter. tail: FIFO insertion point.

- [`reservation`](../runtime/corbo/corbo_runtime_abi.h#L87): reservation: waiter receiving a release-to-next handoff.

- [`CorboChannelState`](../runtime/corbo/corbo_runtime_abi.h#L91): Bounded erased storage; the STD retains typed ownership and destructor dispatch.

- [`storage`](../runtime/corbo/corbo_runtime_abi.h#L93): Dedicated queue region, independent of the constructor's scope.

- [`capacity,width,count,head`](../runtime/corbo/corbo_runtime_abi.h#L95): Capacity and descriptor width; live count and oldest ring position.

- [`epoch`](../runtime/corbo/corbo_runtime_abi.h#L97): Readiness change counter, protected with all queue fields by task_lock.

- [`closed`](../runtime/corbo/corbo_runtime_abi.h#L99): Once closed, sends fail and receivers only drain existing values.

- [`heads,tails`](../runtime/corbo/corbo_runtime_abi.h#L101): Intrusive receive/send queues; task records outlive their registrations.

- [`TaskResult`](../runtime/corbo/corbo_runtime_abi.h#L113): Inline scalar result union; the generated frame contract determines the active member.

- [`k1`](../runtime/corbo/corbo_runtime_abi.h#L115): k1: Result storage for i32.

- [`k2`](../runtime/corbo/corbo_runtime_abi.h#L117): k2: Result storage for i64.

- [`k3`](../runtime/corbo/corbo_runtime_abi.h#L119): k3: Result storage for bool.

- [`k4`](../runtime/corbo/corbo_runtime_abi.h#L121): k4: Result storage for u8.

- [`k5`](../runtime/corbo/corbo_runtime_abi.h#L123): k5: Result storage for u16.

- [`k6`](../runtime/corbo/corbo_runtime_abi.h#L125): k6: Result storage for u32.

- [`k7`](../runtime/corbo/corbo_runtime_abi.h#L127): k7: Result storage for u64.

- [`k8`](../runtime/corbo/corbo_runtime_abi.h#L129): k8: Result storage for f32.

- [`k9`](../runtime/corbo/corbo_runtime_abi.h#L131): k9: Result storage for f64.

- [`ClassicStack`](../runtime/corbo/corbo_runtime_abi.h#L134): Saved thread-local fixed-stack mapping and region-scope context for task suspension/resumption.

- [`base`](../runtime/corbo/corbo_runtime_abi.h#L136): base: saved fixed-stack base.

- [`cursor,limit,committed,page_size,mapped_size`](../runtime/corbo/corbo_runtime_abi.h#L138): cursor: saved next free byte offset. limit: saved fixed-stack capacity. committed: saved committed-byte boundary. page_size: saved OS page size. mapped_size: saved mapping extent.

- [`band`](../runtime/corbo/corbo_runtime_abi.h#L140): band: saved region-scope link.

- [`metric_pools`](../runtime/corbo/corbo_runtime_abi.h#L142): metric_pools: suspended fixed-stack pool accounting chain.

- [`TaskState`](../runtime/corbo/corbo_runtime_abi.h#L145): Task header at offset zero plus result, frame-region ownership, cleanup callback and saved storage context.

- [`task`](../runtime/corbo/corbo_runtime_abi.h#L147): task: scheduler header at offset zero.

- [`value`](../runtime/corbo/corbo_runtime_abi.h#L149): value: inline scalar result storage.

- [`payload`](../runtime/corbo/corbo_runtime_abi.h#L151): payload: aggregate result address.

- [`region`](../runtime/corbo/corbo_runtime_abi.h#L153): region: frame-storage region link.

- [`own_region`](../runtime/corbo/corbo_runtime_abi.h#L155): own_region: separate region-descriptor ownership flag.

- [`dispose`](../runtime/corbo/corbo_runtime_abi.h#L157): dispose: typed capture/result cleanup callback.

- [`classic`](../runtime/corbo/corbo_runtime_abi.h#L159): classic: suspended thread-local datastack context.

- [`TaskValue`](../runtime/corbo/corbo_runtime_abi.h#L162): Future/handle descriptor linking an execution frame, backing region, typed poll callback and native-worker mode.

- [`state`](../runtime/corbo/corbo_runtime_abi.h#L164): state: execution frame address.

- [`storage`](../runtime/corbo/corbo_runtime_abi.h#L166): storage: owned backing-region link.

- [`poll`](../runtime/corbo/corbo_runtime_abi.h#L168): poll: frame-specific poll callback.

- [`native`](../runtime/corbo/corbo_runtime_abi.h#L170): native: native-worker ownership selector.

- [`TaskCompletion`](../runtime/corbo/corbo_runtime_abi.h#L173): Success flag and inline scalar result moved out by join_task.

- [`ok`](../runtime/corbo/corbo_runtime_abi.h#L175): ok: successful-launch/completion flag.

- [`value`](../runtime/corbo/corbo_runtime_abi.h#L177): value: moved scalar result bits.

- [`NativeBox`](../runtime/corbo/corbo_runtime_abi.h#L180): Worker metadata with its Region prefix at offset zero; abandonment can transfer final cleanup to the worker.

- [`region`](../runtime/corbo/corbo_runtime_abi.h#L182): region: embedded frame region at offset zero.

- [`state`](../runtime/corbo/corbo_runtime_abi.h#L184): state: native frame address.

- [`run`](../runtime/corbo/corbo_runtime_abi.h#L186): run: native frame run callback.

- [`abandoned`](../runtime/corbo/corbo_runtime_abi.h#L188): abandoned: worker-owned cleanup flag.

- [`dispose`](../runtime/corbo/corbo_runtime_abi.h#L190): dispose: capture/result cleanup callback.

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

- [`metric_previous`](../runtime/corbo_runtime.h#L89): Metrics chain belongs to the allocating fixed-stack context.

- [`metric_end`](../runtime/corbo_runtime.h#L91): metric_end: fixed-stack cursor immediately after pool creation.

- [`metric_live`](../runtime/corbo_runtime.h#L93): metric_live: claimed slots, updated atomically across sharing threads.

- [`Owned`](../runtime/corbo_runtime.h#L96): Move-only allocation descriptor carrying the pool, payload, physical index and destructor. C callers must enforce single cleanup responsibility.

- [`pool`](../runtime/corbo_runtime.h#L98): pool: source pool link, zero after release.

- [`slot`](../runtime/corbo_runtime.h#L100): slot: payload slot address.

- [`index`](../runtime/corbo_runtime.h#L102): index: physical slot index.

- [`destroy`](../runtime/corbo_runtime.h#L104): destroy: typed payload destructor callback.

- [`MapEntry`](../runtime/corbo_runtime.h#L107): Stable map entry header containing normalized key bits and a bucket/free-list offset.

- [`key`](../runtime/corbo_runtime.h#L109): key: normalized integer key bits.

- [`next`](../runtime/corbo_runtime.h#L111): next: next bucket-chain or free-list byte offset.

- [`RegionalMap`](../runtime/corbo_runtime.h#L114): Map descriptor owning a stable byte region, entry width, reusable-slot list and optional value destructor.

- [`region`](../runtime/corbo_runtime.h#L116): region: stable entry-storage region.

- [`width,free_slot`](../runtime/corbo_runtime.h#L118): width: value byte width. free_slot: free-entry offset list head.

- [`dispose`](../runtime/corbo_runtime.h#L120): dispose: value cleanup callback.

- [`CorboRegion`](../runtime/corbo_runtime.h#L124): Public C alias of the stable Region descriptor; payload ownership rules are unchanged.

- [`CorboVector`](../runtime/corbo_runtime.h#L126): Public C vector storage descriptor; element-specific cleanup remains the caller/generated code's responsibility.

- [`CorboString`](../runtime/corbo_runtime.h#L128): Public C UTF-8 string storage descriptor; unchecked C mutations must preserve the string contract.

- [`CorboPool`](../runtime/corbo_runtime.h#L130): Public C alias for fixed slot storage; the source datastack must outlive its allocations.

- [`CorboAllocation`](../runtime/corbo_runtime.h#L132): Public C allocation descriptor. Copying it in C does not transfer or duplicate cleanup responsibility.

- [`CorboHashMap`](../runtime/corbo_runtime.h#L134): Public C map descriptor with stable entry addresses and optional element cleanup.

- [`CorboStackMark`](../runtime/corbo_runtime.h#L137): Saved cursor, stack identity and region-scope mark; rewind is valid only after dependent resources and workers are cleaned up.

- [`position`](../runtime/corbo_runtime.h#L139): position: saved fixed-stack byte cursor.

- [`stack`](../runtime/corbo_runtime.h#L141): stack: originating stack identity.

- [`region_scope`](../runtime/corbo_runtime.h#L143): region_scope: saved region-scope marker.

- [`CorboStackInfo`](../runtime/corbo_runtime.h#L146): Snapshot of the current fixed-stack cursor, committed bytes and reserved capacity.

- [`position,committed,capacity`](../runtime/corbo_runtime.h#L148): position: next free fixed-stack byte offset. committed: committed fixed-stack bytes. capacity: reserved fixed-stack byte capacity.

- [`CorboMemoryStats`](../runtime/corbo_runtime.h#L152): Process-wide Corbo-managed datastack and region byte counters.

- [`reserved`](../runtime/corbo_runtime.h#L154): Reserved virtual-address bytes, including committed pages.

- [`committed`](../runtime/corbo_runtime.h#L156): Committed pages; this is not process RSS.

- [`occupied`](../runtime/corbo_runtime.h#L158): Fixed cursor spans and live region payloads, excluding free pool slots.

- [`corbo_memory_stats`](../runtime/corbo_runtime.h#L161): Samples concurrency-safe counters; fields may represent adjacent instants.

- [`corbo_runtime_abi_version`](../runtime/corbo_runtime.h#L165): Returns the experimental C ABI version; clients must use the matching runtime header.

- [`corbo_runtime_init`](../runtime/corbo_runtime.h#L167): Initializes C-owned runtime storage with optional fixed-stack, region-stack and region-width budgets; repeated initialization terminates.

- [`corbo_runtime_shutdown`](../runtime/corbo_runtime.h#L169): Releases the calling thread's C-owned runtime after all live resources and workers have been cleaned up; a stopped runtime is a no-op.

- [`corbo_datastack_alloc`](../runtime/corbo_runtime.h#L173): Allocates count aligned elements on the calling thread's initialized stack; invalid size/alignment or exhaustion terminates.

- [`corbo_datastack_mark`](../runtime/corbo_runtime.h#L175): Returns a mark containing the current cursor, stack identity and region-scope marker.

- [`corbo_datastack_info`](../runtime/corbo_runtime.h#L177): Returns the current cursor, committed-byte boundary and fixed-stack capacity.

- [`corbo_datastack_rewind`](../runtime/corbo_runtime.h#L180): Restores a mark from this stack after caller cleanup; rejects foreign or forward marks and preserves live transferred regions.

- [`corbo_free_pages`](../runtime/corbo_runtime.h#L182): Requests immediate reclamation of complete unused pages without changing live values or their reserved address ranges.

- [`corbo_pool_create`](../runtime/corbo_runtime.h#L185): Creates fixed slots for each enum arm on the current datastack; zero element width or invalid capacity terminates.

- [`corbo_pool_take`](../runtime/corbo_runtime.h#L187): Claims a free slot in arm and returns its allocation descriptor; invalid arms or exhaustion terminate.

- [`corbo_allocation_data`](../runtime/corbo_runtime.h#L189): Returns an allocation's payload address without transferring ownership or extending its lifetime.

- [`corbo_allocation_drop`](../runtime/corbo_runtime.h#L192): Destroys a live allocation before releasing its slot and clears its pool link; a cleared descriptor is harmless.

- [`corbo_region_enter`](../runtime/corbo_runtime.h#L195): Enters a local region scope with the requested maximum region size and count budget.

- [`corbo_region_new`](../runtime/corbo_runtime.h#L197): Initializes a stable caller-owned region descriptor for element_size bytes per item; dedicated selects independent band storage.

- [`corbo_region_push`](../runtime/corbo_runtime.h#L199): Appends one uninitialized region element and returns its address; region exhaustion terminates.

- [`corbo_region_drop`](../runtime/corbo_runtime.h#L201): Destroys child-region links, releases payload storage and zeroes the caller's region descriptor.

- [`corbo_map_new`](../runtime/corbo_runtime.h#L204): Maps a map descriptor and initializes its stable region storage with an optional element cleanup callback.

- [`corbo_map_get`](../runtime/corbo_runtime.h#L206): Returns the stored value address for key, or zero when absent; the map retains ownership.

- [`corbo_map_insert`](../runtime/corbo_runtime.h#L208): Moves incoming bytes into a stable entry. Returns true and moves the replaced bytes into previous when the key exists.

- [`corbo_map_remove`](../runtime/corbo_runtime.h#L210): Unlinks key and moves its value into previous; returns false without writing when absent and indexes the freed slot for reuse.

- [`corbo_map_drop`](../runtime/corbo_runtime.h#L212): Clears the caller's map pointer, destroys remaining values with dispose, then releases payload and descriptor storage.

### `runtime/memory/datastack.c.inc`

- [`memory_cursor`](../runtime/memory/datastack.c.inc#L20): Rewinds fixed storage after cleanup; retire pool holes before its pages can be reused.

- [`reserve`](../runtime/memory/datastack.c.inc#L30): Reserves the calling thread's fixed datastack, initializes page metadata and commits storage on demand.

- [`push`](../runtime/memory/datastack.c.inc#L55): Reserves count aligned fixed-size elements at the current cursor; checks multiplication, alignment and capacity before advancing.

- [`release`](../runtime/memory/datastack.c.inc#L74): Unmaps the calling thread's fixed datastack after its values and workers have been cleaned up.

- [`take`](../runtime/memory/datastack.c.inc#L83): Finds the first free flag in a count-element slot bitmap, marks it used and returns its index; exhaustion terminates.

- [`numeric`](../runtime/memory/datastack.c.inc#L91): Evaluates the selected signed integer operation with the reference runtime's overflow and zero-divisor failures.

- [`region_error`](../runtime/memory/datastack.c.inc#L107): Reports an invalid or exhausted region operation and terminates the process.

- [`region_default_capacity`](../runtime/memory/datastack.c.inc#L112): Computes the region-stack byte budget from OS memory and CPU information, bounded by PTRDIFF_MAX.

- [`region_metadata`](../runtime/memory/datastack.c.inc#L134): Maps zero-initialized RegionBand metadata independently of storage whose scope may end first.

- [`region_reserve`](../runtime/memory/datastack.c.inc#L145): Reserves a virtual address range for a band and records its capacity and per-region limit; commits no payload yet.

- [`region_release_band`](../runtime/memory/datastack.c.inc#L161): Unmaps an empty band and its separately mapped metadata when applicable; no active region may remain.

- [`region_stride`](../runtime/memory/datastack.c.inc#L179): Rounds a region width to max_align_t with checked size arithmetic.

- [`region_enter`](../runtime/memory/datastack.c.inc#L185): Creates a child region scope with the explicit or inferred count; the caller holds the runtime lock.

- [`region_restore`](../runtime/memory/datastack.c.inc#L198): Closes region scopes back to mark, releasing only empty bands so transferred live regions survive; requires the lock.

- [`region_new`](../runtime/memory/datastack.c.inc#L207): Links a stable descriptor into an available band or a dedicated band; owned regions store child-region cleanup links. Requires the runtime lock.

- [`region_drop`](../runtime/memory/datastack.c.inc#L239): Destroys owned child regions before unlinking this region and releasing an empty closed band; requires the runtime lock.

- [`region_add`](../runtime/memory/datastack.c.inc#L257): Commits pages as needed and returns one new element slot; terminates at the region limit. Requires the runtime lock.

### `runtime/memory/metrics_storage.h`

- [`memory_metric_add`](../runtime/memory/metrics_storage.h#L11): Add a successful storage transition without inspecting another thread's stack.

- [`memory_metric_sub`](../runtime/memory/metrics_storage.h#L15): Remove bytes after their storage transition; never sample mutable descriptors.

- [`memory_metric_read`](../runtime/memory/metrics_storage.h#L19): Sample one atomic counter without stopping workers.

### `runtime/memory/pools.c.inc`

- [`destroy_region`](../runtime/memory/pools.c.inc#L6): Cleanup-callback adapter for a region descriptor; releases its payload through the synchronized region path.

- [`storage_error`](../runtime/memory/pools.c.inc#L8): Reports fixed datastack exhaustion or an invalid storage operation and terminates the process.

- [`new_pool`](../runtime/memory/pools.c.inc#L10): Allocates a pool descriptor, atomic occupancy bytes and fixed slots on the datastack; validates sizes and arm counts.

- [`pool_try_take`](../runtime/memory/pools.c.inc#L15): Atomically claims and zeroes a slot; full pools return false without mutation.

- [`pool_take`](../runtime/memory/pools.c.inc#L18): Claims a free slot; exhaustion terminates.

- [`put`](../runtime/memory/pools.c.inc#L20): Calls a live allocation's typed cleanup callback before releasing its pool slot, then clears the descriptor's pool link.

- [`dispose_owned`](../runtime/memory/pools.c.inc#L22): Cleanup-callback adapter that destroys and releases the Owned descriptor at pointer.

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

- [`corbo_memory_stats`](../runtime/runtime_api.c.inc#L95): Samples managed-storage counters atomically; fields may represent adjacent instants.
