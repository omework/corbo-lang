/** @file vector.c.inc
 * C reference/runtime ABI source. Preserve cleanup-before-release and match the compiler's runtime version.
 */
/** Appends a child-region/slot link for recursive cleanup; the child descriptor and slot flag must remain valid. */
void region_push_owned(Region *r, Region *item, int *slot) {
    *(RegionOwner *)region_add(r) = (RegionOwner){ item, slot };
}
/** Appends a byte or machine-word scalar according to the region element width. */
void region_push(Region *r, long long value) {
    unsigned char *element = region_add(r);
    if (r->width == 1) *element = (unsigned char)value;
    else *(long long *)element = value;
}
/** Appends a row of machine words from caller storage; the source must cover the region element width. */
void region_push_row(Region *r, const long long *row) {
    long long *element = (long long *)region_add(r);
    for (size_t i = 0; i < r->width / sizeof(*row); ++i) element[i] = row[i];
}
/** Reads a signed word in a checked row/field position; invalid positions terminate. */
long long region_read_row(Region *r, size_t index, size_t field) {
    if (index >= r->len || field >= r->width / sizeof(long long)) region_error();
    return ((long long *)(r->data + index * r->width))[field];
}
/** Appends count bytes through checked element growth; source must contain count readable bytes. */
void region_append(Region *r, const unsigned char *data, size_t count) {
    if (count > r->bytes - r->len) region_error();
    for (size_t i = 0; i < count; ++i) region_push(r, data[i]);
}
/** Reads a checked byte or machine-word element and returns its signed bit representation. */
long long region_read(Region *r, size_t index) {
    if (index >= r->len) region_error();
    return r->width == 1 ? r->data[index] : ((long long *)r->data)[index];
}
