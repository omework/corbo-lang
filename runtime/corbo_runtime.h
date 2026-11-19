/** @file corbo_runtime.h
 * C reference/runtime ABI source. Preserve cleanup-before-release and match the compiler's runtime version.
 */
#ifndef CORBO_RUNTIME_H
#define CORBO_RUNTIME_H
/* SPDX-License-Identifier: MIT OR Apache-2.0 */
#ifndef _WIN32
#ifndef _DEFAULT_SOURCE
#define _DEFAULT_SOURCE
#endif
#ifndef _DARWIN_C_SOURCE
#define _DARWIN_C_SOURCE
#endif
#endif
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdatomic.h>

#define CORBO_RUNTIME_ABI_VERSION 1u

/* Primitive representations use the target C implementation's fixed-width types. */
/** C ABI representation of Corbo i32, using this target's corresponding primitive layout. */
typedef int32_t Corbo_i32;
/** C ABI representation of Corbo i64, using this target's corresponding primitive layout. */
typedef int64_t Corbo_i64;
/** C ABI representation of Corbo u8, using this target's corresponding primitive layout. */
typedef uint8_t Corbo_u8;
/** C ABI representation of Corbo u16, using this target's corresponding primitive layout. */
typedef uint16_t Corbo_u16;
/** C ABI representation of Corbo u32, using this target's corresponding primitive layout. */
typedef uint32_t Corbo_u32;
/** C ABI representation of Corbo u64, using this target's corresponding primitive layout. */
typedef uint64_t Corbo_u64;
/** C ABI representation of Corbo usize, using this target's corresponding primitive layout. */
typedef uintptr_t Corbo_usize;
/** C ABI representation of Corbo bool, using this target's corresponding primitive layout. */
typedef bool Corbo_bool;
/** C ABI representation of Corbo f32, using this target's corresponding primitive layout. */
typedef float Corbo_f32;
/** C ABI representation of Corbo f64, using this target's corresponding primitive layout. */
typedef double Corbo_f64;

/* These are the actual runtime layouts, shared by generated Corbo and C. */
/** Stable descriptor for a bounded growing payload; len counts elements and width is bytes per element. Active descriptors must not move. */
typedef struct Region Region;
/** Reserved virtual address range containing ordered active regions; closed bands are released only when no live region remains. */
typedef struct RegionBand {
    /** base: reserved virtual-memory base. */
    unsigned char *base;
    /** capacity: reserved byte capacity. committed: committed byte boundary. limit: per-region byte limit. */
    size_t capacity, committed, limit;
    /** active: ordered active-region list. */
    Region *active;
    /** parent: parent region-scope link. */
    struct RegionBand *parent;
    /** closed: closed-scope flag. */
    int closed;
} RegionBand;
/** Owned child-region and live-flag link used to clean descendants before their parent storage. */
typedef struct {
    /** region: owned child-region link. */
    Region *region;
    /** slot: address of the child's live-slot flag. */
    int *slot;
} RegionOwner;
/** Stable descriptor for a bounded growing payload; len counts elements and width is bytes per element. Active descriptors must not move. */
struct Region {
    /** data: payload base address. */
    unsigned char *data;
    /** len: live element count. offset: byte offset within its band. bytes: maximum payload byte extent. width: bytes per stored element. */
    size_t len, offset, bytes, width;
    /** next: next active-region link. */
    Region *next;
    /** band: containing band link. */
    RegionBand *band;
    /** owned: recursive child-region cleanup mode. */
    int owned;
};
/** Fixed datastack slot storage partitioned by enum arm, with atomic occupancy bytes for slot claiming. */
typedef struct Pools {
    /** cap: slot count per arm. stride: aligned bytes per slot. arms: enum-arm count. */
    size_t cap, stride, arms;
    /** data: stable slot-storage base. */
    unsigned char *data;
    /** used: atomic occupancy-byte array. */
    _Atomic unsigned char *used;
} Pools;
/** Move-only allocation descriptor carrying the pool, payload, physical index and destructor. C callers must enforce single cleanup responsibility. */
typedef struct Owned {
    /** pool: source pool link, zero after release. */
    Pools *pool;
    /** slot: payload slot address. */
    void *slot;
    /** index: physical slot index. */
    size_t index;
    /** destroy: typed payload destructor callback. */
    void (*destroy)(void *);
} Owned;
/** Stable map entry header containing normalized key bits and a bucket/free-list offset. */
typedef struct {
    /** key: normalized integer key bits. */
    uint64_t key;
    /** next: next bucket-chain or free-list byte offset. */
    size_t next;
} MapEntry;
/** Map descriptor owning a stable byte region, entry width, reusable-slot list and optional value destructor. */
typedef struct {
    /** region: stable entry-storage region. */
    Region region;
    /** width: value byte width. free_slot: free-entry offset list head. */
    size_t width, free_slot;
    /** dispose: value cleanup callback. */
    void (*dispose)(void *);
} RegionalMap;

/** Public C alias of the stable Region descriptor; payload ownership rules are unchanged. */
typedef Region CorboRegion;
/** Public C vector storage descriptor; element-specific cleanup remains the caller/generated code's responsibility. */
typedef Region CorboVector;
/** Public C UTF-8 string storage descriptor; unchecked C mutations must preserve the string contract. */
typedef Region CorboString;
/** Public C alias for fixed slot storage; the source datastack must outlive its allocations. */
typedef Pools CorboPool;
/** Public C allocation descriptor. Copying it in C does not transfer or duplicate cleanup responsibility. */
typedef Owned CorboAllocation;
/** Public C map descriptor with stable entry addresses and optional element cleanup. */
typedef RegionalMap CorboHashMap;

/** Saved cursor, stack identity and region-scope mark; rewind is valid only after dependent resources and workers are cleaned up. */
typedef struct {
    /** position: saved fixed-stack byte cursor. */
    size_t position;
    /** stack: originating stack identity. */
    const void *stack;
    /** region_scope: saved region-scope marker. */
    void *region_scope;
} CorboStackMark;
/** Snapshot of the current fixed-stack cursor, committed bytes and reserved capacity. */
typedef struct {
    /** position: next free fixed-stack byte offset. committed: committed fixed-stack bytes. capacity: reserved fixed-stack byte capacity. */
    size_t position, committed, capacity;
} CorboStackInfo;

/* Call init/shutdown only when C owns the runtime. Generated Corbo main does it. */
/** Returns the experimental C ABI version; clients must use the matching runtime header. */
unsigned corbo_runtime_abi_version(void);
/** Initializes C-owned runtime storage with optional fixed-stack, region-stack and region-width budgets; repeated initialization terminates. */
void corbo_runtime_init(size_t fixed_size, size_t region_stack_size, size_t region_size);
/** Releases the calling thread's C-owned runtime after all live resources and workers have been cleaned up; a stopped runtime is a no-op. */
void corbo_runtime_shutdown(void);

/* Allocation uses the calling thread's current Corbo datastack. */
/** Allocates count aligned elements on the calling thread's initialized stack; invalid size/alignment or exhaustion terminates. */
void *corbo_datastack_alloc(size_t element_size, size_t alignment, size_t count);
/** Returns a mark containing the current cursor, stack identity and region-scope marker. */
CorboStackMark corbo_datastack_mark(void);
/** Returns the current cursor, committed-byte boundary and fixed-stack capacity. */
CorboStackInfo corbo_datastack_info(void);
/* The caller must clean surviving resources/threads before rewinding storage. */
/** Restores a mark from this stack after caller cleanup; rejects foreign or forward marks and preserves live transferred regions. */
void corbo_datastack_rewind(CorboStackMark mark);
/** Requests immediate reclamation of complete unused pages without changing live values or their reserved address ranges. */
void corbo_free_pages(void);

/** Creates fixed slots for each enum arm on the current datastack; zero element width or invalid capacity terminates. */
CorboPool *corbo_pool_create(size_t slots, size_t element_size, size_t arms);
/** Claims a free slot in arm and returns its allocation descriptor; invalid arms or exhaustion terminate. */
CorboAllocation corbo_pool_take(CorboPool *pool, size_t arm);
/** Returns an allocation's payload address without transferring ownership or extending its lifetime. */
void *corbo_allocation_data(const CorboAllocation *allocation);
/* Consumes the descriptor: calls its destroy callback once, releases the slot. */
/** Destroys a live allocation before releasing its slot and clears its pool link; a cleared descriptor is harmless. */
void corbo_allocation_drop(CorboAllocation *allocation);

/** Enters a local region scope with the requested maximum region size and count budget. */
void corbo_region_enter(size_t max_size, size_t count);
/** Initializes a stable caller-owned region descriptor for element_size bytes per item; dedicated selects independent band storage. */
void corbo_region_new(CorboRegion *region, size_t element_size, bool dedicated);
/** Appends one uninitialized region element and returns its address; region exhaustion terminates. */
void *corbo_region_push(CorboRegion *region);
/** Destroys child-region links, releases payload storage and zeroes the caller's region descriptor. */
void corbo_region_drop(CorboRegion *region);

/** Maps a map descriptor and initializes its stable region storage with an optional element cleanup callback. */
CorboHashMap *corbo_map_new(size_t element_size, void (*dispose)(void *));
/** Returns the stored value address for key, or zero when absent; the map retains ownership. */
void *corbo_map_get(CorboHashMap *map, uint64_t key);
/** Moves incoming bytes into a stable entry. Returns true and moves the replaced bytes into previous when the key exists. */
bool corbo_map_insert(CorboHashMap *map, uint64_t key, const void *value, void *previous);
/** Unlinks key and moves its value into previous; returns false without writing when absent and indexes the freed slot for reuse. */
bool corbo_map_remove(CorboHashMap *map, uint64_t key, void *previous);
/** Clears the caller's map pointer, destroys remaining values with dispose, then releases payload and descriptor storage. */
void corbo_map_drop(CorboHashMap **map);

/* C performs no Corbo moves or borrowing checks. Ordinary C copies/aliases,
 * retained addresses, thread lifetime, synchronization, descriptor relocation
 * and cleanup are the caller's responsibility. Do not free datastack addresses
 * with free(). Region descriptors must stay at a stable address while active.
 * Match this header to the runtime/compiler version; this is an experimental ABI.
 */
#endif
