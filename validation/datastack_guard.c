#include "rust_frontend/src/datastack.c"
#include <stdbool.h>
#include <string.h>
#include "rust_frontend/src/region_storage.c"

int main(int argc, char **argv) {
    if (argc != 4)
        return 2;
    size_t page = (size_t)sysconf(_SC_PAGESIZE);
    size_t limit = strcmp(argv[2], "aligned") == 0 ? page : page - _Alignof(max_align_t);
    bool fixed = strcmp(argv[1], "fixed") == 0;
    CrustGrowing region;
    volatile unsigned char *data;
    if (fixed) {
        crust_set_capacity(limit);
        data = crust_push(1, 1, limit);
    } else {
        crust_regions_configure(limit, limit, 1);
        region = crust_region_take();
        data = crust_region_data(&region);
    }
    data[limit - 1] = 42;
    if (data[limit - 1] != 42)
        return 3;
    if (strcmp(argv[3], "read") == 0)
        return data[page];
    if (strcmp(argv[3], "write") == 0)
        data[page] = 42;
    if (strcmp(argv[3], "overflow") == 0) {
        if (fixed)
            crust_push(1, 1, 1);
        else {
            region.used = limit;
            crust_region_append(&region, "x", 1);
        }
        return 4;
    }
    if (fixed)
        crust_guarded_unmap(crust_stack, limit);
    else {
        crust_region_release(&region);
        crust_region_restore(NULL);
        crust_region_destroy(crust_region_global);
    }
    return 0;
}
