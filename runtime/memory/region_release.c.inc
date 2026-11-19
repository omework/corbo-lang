/** @file region_release.c.inc
 * C reference/runtime ABI source. Preserve cleanup-before-release and match the compiler's runtime version.
 */
/** Releases the global region band after its live values have been destroyed. */
static void region_release(void) {
    if (global_band.base) region_release_band(&global_band);
}
