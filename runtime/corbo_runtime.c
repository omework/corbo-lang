/** @file corbo_runtime.c
 * C reference/runtime ABI source. Preserve cleanup-before-release and match the compiler's runtime version.
 */
/* SPDX-License-Identifier: MIT OR Apache-2.0
 * Standalone C memory runtime. Generated Corbo embeds the same implementation. */
#include "corbo_runtime.h"
#include <string.h>
#include "memory/datastack.c.inc"
#include "collections/vector.c.inc"
#include "memory/region_release.c.inc"
#define value_region_new region_new
#define value_region_add region_add
#define value_region_drop region_drop
#include "memory/pools.c.inc"
#include "collections/vector_owned.c.inc"
#include "collections/hashmap.c.inc"
#define CORBO_THREADED 0
#include "memory/reclaim.c.inc"
#include "runtime_api.c.inc"
